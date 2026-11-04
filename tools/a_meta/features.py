"""Per-cohort, per-patient feature tables on each cohort's own scale."""
from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from tools import a_scoring
from tools.a_scoring import panel_scores


# The currently materialised A programme registry has ten complete memberships.
# The Hallmark IFN-gamma membership is deliberately not fabricated here: its
# separate pre-outcome freeze is still required.
AVAILABLE_PANEL_IDS = (
    "P_ANTIGEN_PRESENTATION",
    "AYERS_GEP_18",
    "HOPE_18",
    "M0_EXTRA_ANTIGEN_PRESENTATION",
    "M1_MOBILITY",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
    "M5_CHECKPOINT_CANDIDATES",
    "M6_EPIGENETIC_REGULATORS",
)
_UNIT_FAMILIES = {"gene", "panel", "pathway", "fraction"}
_FORBIDDEN_IDENTIFIER_COLUMNS = {"patient_id", "sample_id", "patient", "sample"}


@dataclass(frozen=True)
class FeatureTable:
    """Feature vectors indexed by zero-based cohort row, with no patient IDs."""

    cohort_id: str
    unit_family: str
    values_by_unit: dict[str, list[float | None]]
    n_patients: int
    coverage: dict[str, dict] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def records(self) -> list[dict]:
        """Materialize the long table form for small callers and tests."""
        return [
            {"patient_row": patient_row, "unit": unit, "value": value, "unit_family": self.unit_family}
            for unit, values in self.values_by_unit.items()
            for patient_row, value in enumerate(values)
        ]


def build_feature_table(
    view,
    family: str,
    *,
    runtime: Path | str | None = None,
    gene_sets: Path | str | None = None,
    external: Sequence[Mapping] | None = None,
    panels: Mapping[str, Sequence[str]] | None = None,
    gene_map: Mapping[str, str] | Path | str | None = None,
    gtf_path: Path | str | None = None,
    probe_map: Path | str | None = None,
    r_out_dir: Path | str | None = None,
    runner=None,
) -> FeatureTable:
    """Build gene, panel, singscore pathway, or external fraction features.

    Every returned table uses zero-based `patient_row` values aligned to the
    validated CohortView order. Real patient and sample identifiers are not
    copied into the returned or serialized feature rows.
    """
    family = family.casefold()
    if family not in _UNIT_FAMILIES:
        raise ValueError("Feature family must be gene, panel, pathway, or fraction")
    if family == "fraction":
        if external is None:
            raise ValueError("Fraction features require an external patient table")
        return external_feature_table(
            external,
            cohort_id=view.metadata.cohort_id,
            expected_patients=len(view.clinical_rows),
        )
    if family == "pathway":
        if gene_sets is None:
            raise ValueError("Pathway features require a gene-set file")
        return _pathway_features(
            view,
            gene_sets,
            runtime=runtime,
            gene_map=gene_map,
            gtf_path=gtf_path,
            probe_map=probe_map,
            r_out_dir=r_out_dir,
            runner=runner,
        )

    genes = _gene_table(
        view,
        runtime=runtime,
        gene_map=gene_map,
        gtf_path=gtf_path,
        probe_map=probe_map,
    )
    if family == "gene":
        return genes

    panel_definitions = (
        {name: tuple(members) for name, members in panels.items()}
        if panels is not None
        else a_scoring.core.panel_definitions(AVAILABLE_PANEL_IDS)
    )
    return _panel_table(view, genes, panel_definitions)


def external_feature_table(
    rows: Sequence[Mapping],
    *,
    cohort_id: str,
    expected_patients: int | None = None,
    unit_family: str = "fraction",
) -> FeatureTable:
    """Adapt an external per-patient table using row indices, never identifiers."""
    if unit_family not in _UNIT_FAMILIES:
        raise ValueError("Unsupported external feature family")
    if not isinstance(cohort_id, str) or not cohort_id:
        raise ValueError("External features require a cohort identifier")
    values_by_unit: dict[str, list[float | None]] = {}
    seen: set[tuple[int, str]] = set()
    row_indexes = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ValueError("External feature rows must be mappings")
        if _FORBIDDEN_IDENTIFIER_COLUMNS & {str(key).casefold() for key in raw}:
            raise ValueError("External feature table cannot contain patient or sample identifiers")
        patient_row = _as_patient_row(raw.get("patient_row"))
        unit = str(raw.get("unit", "")).strip()
        if not unit:
            raise ValueError("External feature unit is empty")
        key = (patient_row, unit)
        if key in seen:
            raise ValueError("Duplicate patient-row/unit in external feature table")
        seen.add(key)
        row_indexes.add(patient_row)
        value = _numeric_or_missing(raw.get("value"))
        if expected_patients is not None and patient_row >= expected_patients:
            raise ValueError("External feature row index is outside the cohort")
        values_by_unit.setdefault(unit, [None] * (expected_patients or 0))
        if len(values_by_unit[unit]) <= patient_row:
            values_by_unit[unit].extend([None] * (patient_row + 1 - len(values_by_unit[unit])))
        values_by_unit[unit][patient_row] = value
    n_patients = expected_patients if expected_patients is not None else (max(row_indexes) + 1 if row_indexes else 0)
    if expected_patients is not None and any(index >= expected_patients for index in row_indexes):
        raise ValueError("External feature row index is outside the cohort")
    for values in values_by_unit.values():
        if len(values) < n_patients:
            values.extend([None] * (n_patients - len(values)))
    return FeatureTable(
        cohort_id=cohort_id,
        unit_family=unit_family,
        values_by_unit=values_by_unit,
        n_patients=n_patients,
        metadata={"scale_rule": "source_scale", "input_kind": "external_patient_table"},
    )


def read_external_feature_table(
    path: Path | str,
    *,
    cohort_id: str,
    expected_patients: int | None = None,
    unit_family: str = "fraction",
) -> FeatureTable:
    """Read a patient-row/unit/value TSV for the generic feature interface."""
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not {"patient_row", "unit", "value"}.issubset(reader.fieldnames):
            raise ValueError("External table requires patient_row, unit, and value columns")
        return external_feature_table(
            list(reader),
            cohort_id=cohort_id,
            expected_patients=expected_patients,
            unit_family=unit_family,
        )


def write_feature_table(table: FeatureTable, path: Path | str) -> None:
    """Write a wide patient-row table without patient or sample identifiers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    units = sorted(table.values_by_unit)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["patient_row", *units])
        for patient_row in range(table.n_patients):
            writer.writerow([
                patient_row,
                *[table.values_by_unit[unit][patient_row] for unit in units],
            ])


def read_feature_table(
    path: Path | str,
    *,
    cohort_id: str,
    unit_family: str,
    n_patients: int,
    coverage_path: Path | str | None = None,
    metadata: Mapping | None = None,
) -> FeatureTable:
    """Read a wide feature table written by :func:`write_feature_table`."""
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Feature table is empty") from None
        if len(header) < 2 or header[0] != "patient_row" or len(set(header[1:])) != len(header) - 1:
            raise ValueError("Feature table must have a unique unit header after patient_row")
        values_by_unit = {unit: [] for unit in header[1:]}
        for expected_row, row in enumerate(reader):
            if len(row) != len(header) or _as_patient_row(row[0]) != expected_row:
                raise ValueError("Feature table rows are not in contiguous cohort order")
            for unit, value in zip(header[1:], row[1:]):
                values_by_unit[unit].append(_numeric_or_missing(value))
    actual_rows = expected_row + 1 if "expected_row" in locals() else 0
    if actual_rows != n_patients:
        raise ValueError("Feature table row count differs from cohort size")
    coverage = {}
    if coverage_path is not None and Path(coverage_path).is_file():
        for row in _read_tsv(Path(coverage_path)):
            coverage[row["unit"]] = {
                "n_found": int(row["n_found"]),
                "n_total": int(row["n_total"]),
                "missing": [gene for gene in row.get("missing", "").split(",") if gene],
                "complete": row["complete"].casefold() == "true",
            }
    return FeatureTable(
        cohort_id=cohort_id,
        unit_family=unit_family,
        values_by_unit=values_by_unit,
        n_patients=n_patients,
        coverage=coverage,
        metadata=dict(metadata or {}),
    )


def _gene_table(view, *, runtime, gene_map, gtf_path, probe_map) -> FeatureTable:
    feature_ids, sample_columns, matrix = _read_expression(view.expression_path)
    if len(sample_columns) != len(view.clinical_rows):
        raise ValueError("Expression columns do not align with cohort-view rows")
    row_identities = [str(row.get("patient_id", "")) for row in view.clinical_rows]
    if any(row_identities):
        if any(not identity for identity in row_identities) or len(set(row_identities)) != len(row_identities):
            raise ValueError("Cohort-view row identities must be present and unique")
        if len(set(sample_columns)) != len(sample_columns) or set(sample_columns) != set(row_identities):
            raise ValueError("Expression samples do not match cohort-view row identities")
        expression_column = {identity: index for index, identity in enumerate(sample_columns)}
        aligned_columns = [expression_column[identity] for identity in row_identities]
        matrix = [[values[index] for index in aligned_columns] for values in matrix]
    representation = view.metadata.representation
    effective_feature_id = representation.feature_id
    recount3_dropped = 0
    recount3_used = False
    if (
        gtf_path is not None
        and str(representation.platform).casefold() == "rnaseq"
        and str(representation.unit).casefold() == "counts"
        and str(representation.transform).casefold() == "linear"
    ):
        feature_ids, tpm, recount3_dropped = a_scoring.recount3_to_tpm(
            feature_ids, matrix, gtf_path
        )
        logged = a_scoring.log2p1(tpm)
        scale_rule = "log2(TPM+1); recount3 GTF gene lengths"
        effective_feature_id = "symbol"
        recount3_used = True
    else:
        scale_rule, logged = _study_scale(matrix, representation)
    probe_counts = None
    dropped_unmapped = 0
    if representation.platform == "microarray" and representation.feature_id == "probe":
        mapping_path = Path(probe_map) if probe_map is not None else Path(view.expression_path).parent / "probe_to_gene.tsv"
        mapping = _probe_mapping(mapping_path)
        selected = _collapse_probes(feature_ids, logged, mapping)
        feature_ids, logged, probe_counts, dropped_unmapped = selected
        feature_ids = _canonical_gene_ids(
            feature_ids,
            "symbol",
            runtime=runtime,
            gene_map={},
        )
        feature_ids, logged = _ensure_unique_genes(feature_ids, logged)
    else:
        mapping = _load_gene_map(gene_map)
        feature_ids = _canonical_gene_ids(
            feature_ids,
            effective_feature_id,
            runtime=runtime,
            gene_map=mapping,
        )
        feature_ids, logged = _ensure_unique_genes(feature_ids, logged)

    values_by_unit = {unit: list(values) for unit, values in zip(feature_ids, logged)}
    metadata = {"scale_rule": scale_rule, "representation": {
        "platform": representation.platform,
        "unit": representation.unit,
        "transform": representation.transform,
        "feature_id": representation.feature_id,
    }}
    if probe_counts is not None:
        metadata["probe_rule"] = "highest mean expression across all samples; ties use probe ID order"
        metadata["probe_counts"] = probe_counts
        metadata["unmapped_probes"] = dropped_unmapped
    if mapping:
        metadata["gene_map_rows"] = len(mapping)
    if recount3_used:
        metadata["recount3_non_primary_dropped"] = recount3_dropped
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="gene",
        values_by_unit=values_by_unit,
        n_patients=len(view.clinical_rows),
        metadata=metadata,
    )


def _panel_table(view, genes: FeatureTable, panels: Mapping[str, Sequence[str]]) -> FeatureTable:
    gene_values = genes.values_by_unit
    gene_order = list(gene_values)
    scores_by_unit: dict[str, list[float | None]] = {}
    coverage: dict[str, dict] = {}
    for unit, members in panels.items():
        unit_scores = []
        unit_coverage = None
        for patient_row in range(genes.n_patients):
            expression = {
                gene: gene_values[gene][patient_row]
                for gene in gene_order
                if gene_values[gene][patient_row] is not None
            }
            scores, patient_coverage = panel_scores(expression, {unit: members}, require_complete=True)
            unit_scores.append(scores[unit])
            if unit_coverage is None:
                unit_coverage = patient_coverage[unit]
        scores_by_unit[unit] = unit_scores
        complete = bool(unit_coverage and unit_coverage["complete"])
        coverage[unit] = {
            "n_found": int(unit_coverage["n_found"]) if unit_coverage else 0,
            "n_total": int(unit_coverage["n_total"]) if unit_coverage else len(members),
            "missing": list(unit_coverage["missing"]) if unit_coverage else list(members),
            "complete": complete,
        }
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="panel",
        values_by_unit=scores_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": "tools.a_scoring.panel_scores; unweighted mean; complete coverage only",
            "source_scale_rule": genes.metadata["scale_rule"],
        },
    )


def _pathway_features(view, gene_sets, *, runtime, gene_map, gtf_path, probe_map, r_out_dir, runner):
    from .r_manifest import run_r_sanitised

    genes = _gene_table(
        view,
        runtime=runtime,
        gene_map=gene_map,
        gtf_path=gtf_path,
        probe_map=probe_map,
    )
    gene_set_path = Path(gene_sets).expanduser().resolve(strict=True)
    output_dir = Path(r_out_dir) if r_out_dir is not None else Path(view.expression_path).parent / "singscore-stage"
    matrix_path = output_dir.parent / (output_dir.name + ".expression.tsv")
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    _write_expression_matrix(matrix_path, genes)
    script = Path(__file__).resolve().parents[2] / "r/scripts/singscore.R"
    result = run_r_sanitised(
        script,
        {"expression": matrix_path, "gene_sets": gene_set_path},
        {"expected_outputs": ["scores.tsv", "coverage.tsv"]},
        output_dir,
        script_id="r/scripts/singscore.R",
        runner=runner,
    )
    score_records = _read_tsv(result.outputs["scores.tsv"])
    coverage_rows = _read_tsv(result.outputs["coverage.tsv"])
    values_by_unit = {}
    for row in score_records:
        patient_row = _as_patient_row(row["patient_row"])
        values_by_unit.setdefault(row["unit"], [None] * genes.n_patients)[patient_row] = _numeric_or_missing(row["value"])
    coverage = {
        row["unit"]: {
            "n_found": int(row["n_found"]),
            "n_total": int(row["n_total"]),
            "missing": [gene for gene in row["missing_genes"].split(",") if gene],
            "complete": row["complete"].casefold() == "true",
        }
        for row in coverage_rows
    }
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="pathway",
        values_by_unit=values_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": "singscore simpleScore; gene sets supplied by caller",
            "source_scale_rule": genes.metadata["scale_rule"],
            "coverage_policy": "complete gene-set membership required; incomplete sets receive missing scores",
            "r_manifest": result.manifest,
        },
    )


def _study_scale(matrix, representation):
    platform = str(representation.platform).casefold()
    unit = str(representation.unit).casefold()
    transform = str(representation.transform).casefold()
    if platform == "rnaseq" and unit in {"tpm", "fpkm", "rpkm"} and transform == "linear":
        logged = a_scoring.log2p1(matrix, representation)
        return "log2(TPM+1)", logged
    if platform == "rnaseq" and unit == "counts" and transform == "linear":
        return "log2(CPM+1)", _log2_cpm(matrix)
    return "source_scale", matrix


def _log2_cpm(matrix):
    if not matrix:
        return []
    n_samples = len(matrix[0])
    totals = [0.0] * n_samples
    for row in matrix:
        for index, value in enumerate(row):
            if value < 0 or not float(value).is_integer():
                raise ValueError("Count representation must contain non-negative integers")
            totals[index] += value
    if any(total <= 0 for total in totals):
        raise ValueError("Count library has a zero total")
    return [
        [math.log2(value / totals[index] * 1_000_000.0 + 1.0) for index, value in enumerate(row)]
        for row in matrix
    ]


def _read_expression(path: Path | str) -> tuple[list[str], list[str], list[list[float]]]:
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Expression matrix is empty") from None
        if len(header) < 2 or header[0].casefold() not in {"gene", "feature", "feature_id"}:
            raise ValueError("Expression matrix must have a feature column and patient columns")
        if len(header[1:]) != len(set(header[1:])):
            raise ValueError("Expression matrix contains duplicate patient columns")
        feature_ids, matrix = [], []
        for row in reader:
            if len(row) != len(header) or not row[0]:
                raise ValueError("Expression matrix row is malformed")
            try:
                values = [float(value) for value in row[1:]]
            except ValueError:
                raise ValueError("Expression matrix contains non-numeric values") from None
            if any(not math.isfinite(value) for value in values):
                raise ValueError("Expression matrix contains non-finite values")
            feature_ids.append(row[0])
            matrix.append(values)
    if not feature_ids or len(feature_ids) != len(set(feature_ids)):
        raise ValueError("Expression matrix has no features or duplicate feature IDs")
    return feature_ids, header[1:], matrix


def _probe_mapping(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError("Probe-level array requires its cohort probe-to-gene map")
    rows = _read_tsv(path)
    mapping = {}
    for row in rows:
        probe = str(row.get("probe_id", "")).strip()
        gene = str(row.get("gene_symbol", "")).strip()
        if not probe or probe in mapping:
            raise ValueError("Probe map contains an empty or duplicate probe")
        if gene and gene.casefold() not in {"na", "null", "---"}:
            mapping[probe] = gene
    return mapping


def _collapse_probes(feature_ids, matrix, mapping):
    probes_by_gene: dict[str, list[tuple[float, str, list[float]]]] = {}
    unmapped = 0
    for probe, values in zip(feature_ids, matrix):
        gene = mapping.get(probe)
        if not gene:
            unmapped += 1
            continue
        probes_by_gene.setdefault(gene, []).append((math.fsum(values) / len(values), probe, values))
    chosen = []
    for gene in sorted(probes_by_gene):
        # Mean expression is outcome-blind; lexical probe order resolves exact ties.
        chosen.append((gene, sorted(probes_by_gene[gene], key=lambda row: (-row[0], row[1]))[0][2]))
    counts = {
        "probes": len(feature_ids),
        "mapped_probes": len(feature_ids) - unmapped,
        "genes": len(chosen),
        "collapsed_probes": len(feature_ids) - unmapped - len(chosen),
    }
    return [gene for gene, _ in chosen], [values for _, values in chosen], counts, unmapped


def _load_gene_map(gene_map) -> dict[str, str]:
    if gene_map is None:
        return {}
    if isinstance(gene_map, Mapping):
        return {str(key): str(value) for key, value in gene_map.items() if value}
    rows = _read_tsv(Path(gene_map))
    mapping = {}
    for row in rows:
        source = row.get("source_id") or row.get("gene_id") or row.get("ensembl") or row.get("entrez_id")
        symbol = row.get("symbol") or row.get("gene_symbol")
        if source and symbol:
            mapping[str(source)] = str(symbol)
    return mapping


def _canonical_gene_ids(feature_ids, feature_id, *, runtime, gene_map):
    mapping = dict(gene_map)
    key_type = str(feature_id).casefold()
    if key_type == "entrez":
        runtime_path = a_scoring.gene_info_path(runtime)
        if runtime_path.is_file():
            root = a_scoring.core._runtime_path(runtime).expanduser().resolve()
            by_id, _ = a_scoring.core._gene_info(str(runtime_path.resolve()), str(root))
            mapping = {**by_id, **mapping}
    if key_type == "probe" and not mapping:
        raise ValueError("Probe features require a probe-to-gene map")
    aliases = a_scoring.core._frozen_aliases(str(a_scoring.core.ALIAS_TABLE_PATH))
    result = []
    for feature in feature_ids:
        source = str(feature)
        target = source
        if key_type == "ensembl":
            base = source.split(".", 1)[0]
            target = mapping.get(source, mapping.get(base, "ENSEMBL:" + base))
        elif key_type == "entrez":
            target = mapping.get(source, "ENTREZ:" + source)
        elif key_type == "symbol":
            target = aliases.get(source, source)
        else:
            target = mapping.get(source, source)
        result.append(str(target))
    return result


def _ensure_unique_genes(feature_ids, matrix):
    positions = {}
    for index, feature in enumerate(feature_ids):
        positions.setdefault(feature, []).append(index)
    duplicates = [feature for feature, indices in positions.items() if len(indices) > 1]
    if duplicates:
        raise ValueError("Gene identifier mapping is not one-to-one")
    return feature_ids, matrix


def _write_expression_matrix(path: Path, table: FeatureTable) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *[str(index) for index in range(table.n_patients)]])
        for gene in sorted(table.values_by_unit):
            gene_values = table.values_by_unit[gene]
            if any(value is None for value in gene_values):
                continue
            writer.writerow([gene, *gene_values])


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _as_patient_row(value) -> int:
    try:
        index = int(value)
    except (TypeError, ValueError):
        raise ValueError("External feature table requires an integer patient_row") from None
    if index < 0 or str(value).strip() != str(index):
        raise ValueError("External feature patient_row must be a non-negative integer")
    return index


def _numeric_or_missing(value):
    if value is None or (isinstance(value, str) and value.strip().casefold() in {"", "na", "nan"}):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("External feature value must be numeric or missing") from None
    if not math.isfinite(result):
        raise ValueError("External feature value must be finite or missing")
    return result
