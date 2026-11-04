"""Per-cohort, per-patient feature tables on each cohort's own scale."""
from __future__ import annotations

import csv
import gzip
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from tools import a_scoring
from tools.a_scoring import panel_scores


GENE_ALIAS_ADDENDUM_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/amendments/2026-11-04-panel-coverage/gene_aliases_addendum.tsv"
)
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
_UNIT_FAMILIES = {"gene", "panel", "panel_coverage90", "pathway", "fraction"}
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
        raise ValueError("Feature family must be gene, panel, panel_coverage90, pathway, or fraction")
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

    panel_definitions = (
        {name: tuple(members) for name, members in panels.items()}
        if panels is not None
        else a_scoring.core.panel_definitions(AVAILABLE_PANEL_IDS)
    )
    genes = _gene_table(
        view,
        runtime=runtime,
        gene_map=gene_map,
        gtf_path=gtf_path,
        probe_map=probe_map,
        target_symbols=_resolution_targets(panel_definitions),
    )
    if family == "gene":
        return genes
    if family == "panel":
        return _panel_table(view, genes, panel_definitions)
    return _panel_coverage90_table(view, genes, panel_definitions)


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
            if row.get("unit_family") and row["unit_family"] != unit_family:
                continue
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


def _gene_table(view, *, runtime, gene_map, gtf_path, probe_map, target_symbols=None) -> FeatureTable:
    salmon_tpm = view.metadata.cohort_id == "gse176307"
    source_inputs_sha256 = {}
    if salmon_tpm:
        (
            feature_ids,
            sample_columns,
            matrix,
            source_inputs_sha256,
            patients_with_tpm_assay,
        ) = _gse176307_salmon_tpm(view, runtime)
    else:
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
    effective_feature_id = "symbol" if salmon_tpm else representation.feature_id
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
    elif salmon_tpm:
        logged = [
            [math.log2(value + 1.0) if value is not None else None for value in row]
            for row in matrix
        ]
        scale_rule = "log2(TPM+1); official GSE176307 Salmon TPM"
        effective_feature_id = _gse176307_feature_id(feature_ids)
    else:
        scale_rule, logged = _study_scale(matrix, representation)
    probe_counts = None
    dropped_unmapped = 0
    duplicate_gene_counts = None
    target_symbols = tuple(target_symbols or _resolution_targets())
    if representation.platform == "microarray" and representation.feature_id == "probe":
        mapping_path = Path(probe_map) if probe_map is not None else Path(view.expression_path).parent / "probe_to_gene.tsv"
        mapping = _probe_mapping(mapping_path)
        custom_map = _load_gene_map(gene_map)
        reference = _gene_reference(runtime)
        source_symbols = [
            _probe_source_symbol(mapping.get(probe), custom_map, reference)
            for probe in feature_ids
        ]
        canonical = _canonicalize_symbols(
            source_symbols,
            target_symbols,
            runtime=runtime,
            reference=reference,
            allow_multiple_synonyms=True,
        )
        selected = _collapse_probes(feature_ids, logged, canonical)
        feature_ids, logged, probe_counts, dropped_unmapped = selected
        feature_ids, logged = _ensure_unique_genes(feature_ids, logged)
    else:
        custom_map = _load_gene_map(gene_map)
        reference = _gene_reference(runtime)
        source_symbols = _source_symbols(
            feature_ids,
            effective_feature_id,
            custom_map=custom_map,
            reference=reference,
        )
        feature_ids = _canonicalize_symbols(
            source_symbols,
            target_symbols,
            runtime=runtime,
            reference=reference,
        )
        feature_ids, logged, duplicate_gene_counts, duplicate_gene_symbols = _collapse_duplicate_genes(
            feature_ids, logged
        )

    values_by_unit = {unit: list(values) for unit, values in zip(feature_ids, logged)}
    metadata = {"scale_rule": scale_rule, "representation": {
        "platform": "rnaseq" if salmon_tpm else representation.platform,
        "unit": "tpm" if salmon_tpm else representation.unit,
        "transform": "linear" if salmon_tpm else representation.transform,
        "feature_id": effective_feature_id,
    }}
    if salmon_tpm:
        metadata.update({
            "source_route": "official Salmon TPM via the A-P2 GSE176307 assay mapping",
            "source_inputs_sha256": source_inputs_sha256,
            "patients_with_tpm_assay": patients_with_tpm_assay,
            "patients_without_tpm_assay": len(view.clinical_rows) - patients_with_tpm_assay,
        })
    if probe_counts is not None:
        metadata["probe_rule"] = "highest mean expression across all samples; ties use probe ID order"
        metadata["probe_counts"] = probe_counts
        metadata["unmapped_probes"] = dropped_unmapped
    if duplicate_gene_counts is not None:
        metadata["duplicate_gene_rule"] = (
            "highest mean expression across measured samples; ties use source row order"
            if salmon_tpm
            else "highest mean expression across all samples; ties use source row order"
        )
        metadata["duplicate_gene_counts"] = duplicate_gene_counts
        metadata["duplicate_gene_symbols"] = duplicate_gene_symbols
    if custom_map:
        metadata["gene_map_rows"] = len(custom_map)
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


def _panel_coverage90_table(
    view,
    genes: FeatureTable,
    panels: Mapping[str, Sequence[str]],
) -> FeatureTable:
    gene_values = genes.values_by_unit
    scores_by_unit: dict[str, list[float | None]] = {}
    coverage: dict[str, dict] = {}
    for unit, members in panels.items():
        if not members:
            raise ValueError(f"Panel {unit} has no members")
        member_coverage = _panel_member_coverage(gene_values, members)
        missing = member_coverage["missing"]
        n_found = member_coverage["n_found"]
        coverage_met = _coverage90_met(n_found, len(members))
        unit_scores = []
        for patient_row in range(genes.n_patients):
            if not coverage_met:
                unit_scores.append(None)
                continue
            expression = {
                gene: gene_values[gene][patient_row]
                for gene in members
                if gene in gene_values and gene_values[gene][patient_row] is not None
            }
            if not _coverage90_met(len(expression), len(members)):
                unit_scores.append(None)
                continue
            scores, _ = panel_scores(expression, {unit: members}, require_complete=False)
            unit_scores.append(scores[unit])
        scores_by_unit[unit] = unit_scores
        coverage[unit] = {
            "n_found": n_found,
            "n_total": len(members),
            "missing": missing,
            "complete": coverage_met,
            "full_coverage": not missing,
        }
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="panel_coverage90",
        values_by_unit=scores_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": (
                "tools.a_scoring.panel_scores; unweighted mean with require_complete=False "
                "only after study-level and per-patient 90% coverage rules pass"
            ),
            "source_scale_rule": genes.metadata["scale_rule"],
            "coverage_policy": (
                "at least 90% of panel members available after alias resolution in the study "
                "and in each scored patient row"
            ),
            "sensitivity_label": "panel_coverage90 sensitivity",
        },
    )


def _coverage90_met(n_found: int, n_total: int) -> bool:
    if n_total <= 0 or n_found < 0 or n_found > n_total:
        raise ValueError("Panel coverage counts are invalid")
    return n_found * 10 >= n_total * 9


def _panel_member_coverage(gene_values, members):
    missing = [gene for gene in members if gene not in gene_values]
    return {"n_found": len(members) - len(missing), "missing": missing}


def _gse176307_sources(view, runtime):
    """Resolve the frozen GSE176307 assay map and source identities for A-META."""
    from tools.a_p2 import build as a_p2_build

    clinical_rows = view.clinical_rows
    patient_ids = [str(row.get("patient_id", "")) for row in clinical_rows]
    if any(not patient_id for patient_id in patient_ids) or len(set(patient_ids)) != len(patient_ids):
        raise ValueError("GSE176307 cohort-view row identities must be present and unique")

    source_inputs = {}
    assay_by_patient = a_p2_build.gse_mapping(clinical_rows, source_inputs, runtime)
    runtime_root = a_p2_build._runtime_path(runtime)
    matrix_path = a_p2_build.source(
        runtime_root / "gse176307/store_tpm/objects/c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894",
        source_inputs,
        runtime,
    )
    source_hashes = {Path(name).name: digest for name, digest in source_inputs.items()}
    return patient_ids, assay_by_patient, matrix_path, source_hashes


def _gse176307_source_hashes(view, runtime):
    """Return current GSE176307 source identities without reading the TPM matrix."""
    return _gse176307_sources(view, runtime)[3]


def _gse176307_salmon_tpm(view, runtime):
    """Read GSE176307 Salmon TPM through A-P2's frozen assay mapping."""
    from tools.a_p2 import build as a_p2_build

    patient_ids, assay_by_patient, matrix_path, source_hashes = _gse176307_sources(view, runtime)
    selected_patients = [patient_id for patient_id in patient_ids if patient_id in assay_by_patient]
    selected_assays = [assay_by_patient[patient_id] for patient_id in selected_patients]
    feature_ids, measured = a_p2_build.matrix(matrix_path, selected_assays, runtime=runtime)
    if any(len(values) != len(selected_patients) for values in measured):
        raise ValueError("GSE176307 TPM columns do not match the existing assay mapping")
    patient_column = {patient_id: index for index, patient_id in enumerate(selected_patients)}
    aligned = [
        [values[patient_column[patient_id]] if patient_id in patient_column else None for patient_id in patient_ids]
        for values in measured
    ]
    return feature_ids, patient_ids, aligned, source_hashes, len(selected_patients)


def _gse176307_feature_id(feature_ids: Sequence[str]) -> str:
    ensembl = [str(feature).split(".", 1)[0].startswith("ENSG") for feature in feature_ids]
    if ensembl and all(ensembl):
        return "ensembl"
    if any(ensembl):
        raise ValueError("GSE176307 Salmon TPM matrix mixes Ensembl IDs and symbols")
    return "symbol"


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
    if not feature_ids:
        raise ValueError("Expression matrix has no features")
    return feature_ids, header[1:], matrix


def _probe_mapping(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError("Probe-level array requires its cohort probe-to-gene map")
    rows = _read_tsv(path)
    mapping = {}
    for row in rows:
        probe = str(row.get("probe_id", "")).strip()
        gene = str(row.get("gene_symbol", "")).strip()
        entrez = str(row.get("entrez_id", "")).strip()
        if not probe or probe in mapping:
            raise ValueError("Probe map contains an empty or duplicate probe")
        if gene.casefold() in {"na", "null", "---"}:
            gene = ""
        if entrez.casefold() in {"na", "null", "---"}:
            entrez = ""
        if gene or entrez:
            mapping[probe] = {"gene_symbol": gene, "entrez_id": entrez}
    return mapping


def _collapse_probes(feature_ids, matrix, canonical_features):
    probes_by_gene: dict[str, list[tuple[float, str, list[float]]]] = {}
    unmapped = 0
    for probe, values, gene in zip(feature_ids, matrix, canonical_features):
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


def _resolution_targets(panel_definitions=None):
    definitions = panel_definitions or a_scoring.core.panel_definitions(AVAILABLE_PANEL_IDS)
    return tuple(sorted({gene for members in definitions.values() for gene in members} | {"GZMA", "PRF1"}))


@lru_cache(maxsize=4)
def _gene_reference(runtime):
    """Load the pinned Entrez and synonym maps plus its Ensembl crosswalk."""
    info_path = a_scoring.gene_info_path(runtime)
    if not info_path.is_file():
        return {"by_id": {}, "synonyms": {}, "ensembl": {}}
    runtime_root = a_scoring.core._runtime_path(runtime).expanduser().resolve()
    by_id, synonyms = a_scoring.core._gene_info(str(info_path.resolve()), str(runtime_root))
    ensembl_candidates: dict[str, set[str]] = {}
    with gzip.open(info_path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            symbol = row["Symbol"]
            for xref in row.get("dbXrefs", "").split("|"):
                if not xref.startswith("Ensembl:"):
                    continue
                ensembl_id = xref.split(":", 1)[1].split(".", 1)[0]
                if ensembl_id:
                    ensembl_candidates.setdefault(ensembl_id, set()).add(symbol)
    ensembl = {
        ensembl_id: next(iter(symbols))
        for ensembl_id, symbols in ensembl_candidates.items()
        if len(symbols) == 1
    }
    return {"by_id": by_id, "synonyms": synonyms, "ensembl": ensembl}


@lru_cache(maxsize=1)
def _gene_alias_addendum() -> dict[str, str]:
    mapping = {}
    with GENE_ALIAS_ADDENDUM_PATH.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not {"source_id", "registry_symbol"}.issubset(reader.fieldnames):
            raise ValueError("Gene alias addendum requires source_id and registry_symbol columns")
        for row in reader:
            source_id = str(row.get("source_id", "")).strip().split(".", 1)[0]
            symbol = str(row.get("registry_symbol", "")).strip()
            if not source_id or not symbol or source_id in mapping:
                raise ValueError("Gene alias addendum contains an empty or duplicate mapping")
            mapping[source_id] = symbol
    return mapping


def _source_symbols(feature_ids, feature_id, *, custom_map, reference):
    key_type = str(feature_id).casefold()
    known_symbols = set(reference["by_id"].values()) | set(reference["synonyms"])
    for values in reference["synonyms"].values():
        known_symbols.update(values)
    aliases = a_scoring.core._frozen_aliases(str(a_scoring.core.ALIAS_TABLE_PATH))
    known_symbols.update(aliases)
    known_symbols.update(aliases.values())
    result = []
    for feature in feature_ids:
        source = str(feature).strip()
        if key_type == "entrez":
            result.append(
                reference["by_id"].get(source)
                or custom_map.get(source)
                or "ENTREZ:" + source
            )
        elif key_type == "ensembl":
            base = source.split(".", 1)[0]
            if base.startswith("ENS"):
                result.append(
                    _gene_alias_addendum().get(base)
                    or reference["ensembl"].get(base)
                    or custom_map.get(source)
                    or custom_map.get(base)
                    or "ENSEMBL:" + base
                )
            else:
                # Some signed sources declare Ensembl keys but retain symbols.
                result.append(custom_map.get(source, source))
        else:
            symbol = custom_map.get(source, source)
            if key_type in {"symbol", "probe"}:
                prefix, separator, suffix = symbol.rpartition("_")
                if separator and suffix.isdigit() and prefix in known_symbols:
                    symbol = prefix
            result.append(symbol)
    return result


def _probe_source_symbol(mapping_row, custom_map, reference):
    if not mapping_row:
        return ""
    entrez = mapping_row.get("entrez_id", "").strip()
    if entrez:
        symbol = reference["by_id"].get(entrez) or custom_map.get(entrez)
        if symbol:
            return symbol
    return mapping_row.get("gene_symbol", "").strip()


def _canonicalize_symbols(
    symbols,
    targets,
    *,
    runtime,
    reference,
    allow_multiple_synonyms=False,
):
    aliases = a_scoring.core._frozen_aliases(str(a_scoring.core.ALIAS_TABLE_PATH))
    normalized = [aliases.get(str(symbol), str(symbol)) if symbol else "" for symbol in symbols]
    unique_symbols = list(dict.fromkeys(symbol for symbol in normalized if symbol))
    resolved_targets = {}
    if unique_symbols and targets:
        indexes, _coverage = a_scoring.resolve(
            unique_symbols,
            targets,
            runtime=runtime,
            aliases=aliases,
            synonyms=reference["synonyms"],
            gene_symbols=reference["by_id"],
        )
        resolved_targets = {unique_symbols[index]: target for target, index in indexes.items()}

        # `resolve` deliberately reports a target missing if several different
        # source synonyms could match it. Probe arrays have multiple probes by
        # design, so resolve each synonym alone and let the outcome-blind probe
        # collapse choose one representative for that target.
        if allow_multiple_synonyms:
            for target, target_synonyms in reference["synonyms"].items():
                if target not in targets or target in resolved_targets.values():
                    continue
                candidates = sorted(set(unique_symbols) & set(target_synonyms))
                for candidate in candidates:
                    candidate_indexes, _ = a_scoring.resolve(
                        [candidate],
                        [target],
                        runtime=runtime,
                        aliases=aliases,
                        synonyms=reference["synonyms"],
                        gene_symbols=reference["by_id"],
                    )
                    if target in candidate_indexes:
                        resolved_targets[candidate] = target

    return [resolved_targets.get(symbol, symbol) if symbol else None for symbol in normalized]


def _ensure_unique_genes(feature_ids, matrix):
    positions = {}
    for index, feature in enumerate(feature_ids):
        positions.setdefault(feature, []).append(index)
    duplicates = [feature for feature, indices in positions.items() if len(indices) > 1]
    if duplicates:
        raise ValueError("Gene identifier mapping is not one-to-one")
    return feature_ids, matrix


def _collapse_duplicate_genes(feature_ids, matrix):
    """Retain one outcome-blind representative for each canonical gene row."""
    genes: dict[str, list[tuple[float, int, list[float | None]]]] = {}
    for row_index, (gene, values) in enumerate(zip(feature_ids, matrix)):
        if not gene:
            continue
        measured = [value for value in values if value is not None]
        mean_expression = math.fsum(measured) / len(measured) if measured else -math.inf
        genes.setdefault(gene, []).append((mean_expression, row_index, values))
    chosen = []
    duplicate_groups = 0
    duplicate_rows = 0
    duplicate_symbols = []
    for gene in sorted(genes):
        candidates = genes[gene]
        if len(candidates) > 1:
            duplicate_groups += 1
            duplicate_rows += len(candidates) - 1
            duplicate_symbols.append(gene)
        # The source row order is a deterministic tie break and never reads labels.
        chosen.append((gene, sorted(candidates, key=lambda row: (-row[0], row[1]))[0][2]))
    counts = {
        "input_rows": len(feature_ids),
        "genes": len(chosen),
        "duplicate_gene_groups": duplicate_groups,
        "duplicate_rows_removed": duplicate_rows,
    }
    return [gene for gene, _ in chosen], [values for _, values in chosen], counts, duplicate_symbols


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
