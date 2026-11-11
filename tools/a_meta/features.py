"""Per-cohort, per-patient feature tables on each cohort's own scale."""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from tools import a_scoring
from tools.a_scoring import panel_scores
from .frozen import (
    COMMON_GENE_TABLE,
    FROZEN_ALIASES,
    HALLMARK_GMT,
    file_sha256,
    membership_sha256,
    read_common_gene_sets,
    read_frozen_aliases,
    read_hallmark_gene_sets,
    read_identifier_proposals,
)
from .provenance import known_cohort_ids


GENE_ALIAS_ADDENDUM_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/amendments/2026-11-04-panel-coverage/gene_aliases_addendum.tsv"
)
# These eleven A-BIO memberships are fixed by the signed numerical freeze.
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
    "HALLMARK_INTERFERON_GAMMA_RESPONSE",
)
_UNIT_FAMILIES = {
    "gene", "m5m6_gene", "panel", "panel_coverage90", "pathway",
    "pathway_coverage90", "pathway_common", "targeted_subset", "fraction",
}
_PATHWAY_FAMILIES = {"pathway", "pathway_coverage90", "pathway_common"}
_SENSITIVITY_FAMILIES = {
    "panel_coverage90", "pathway_coverage90", "pathway_common", "targeted_subset",
}
TARGETED_SUBSET_STUDIES = {"gse136961", "gse93157", "gse140901", "gse159067"}
SENSITIVITY_LABEL = "sensitivity only; does not support claims alone"
PANEL_METHOD_IDS = {panel: f"CUSTOM_MEAN_{panel}" for panel in AVAILABLE_PANEL_IDS}
_FORBIDDEN_IDENTIFIER_COLUMNS = {"patient_id", "sample_id", "patient", "sample"}
_GSE176307_TPM_SHA256 = "c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894"
_GSE176307_KEY_SHA256 = "cfe452ec72c99f2c84216bb25fe291b4c78028e53b8a8189acbd5c9ed7db919b"
_GSE176307_SOFT_SHA256 = "ea242fbb98aa104c384a97a3d1f0baaa938031e91a5a3872b065982d73b1bf72"


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


class FeatureUnavailableError(ValueError):
    """A typed, patient-free reason that an A-META feature route cannot run."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


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
    common_gene_table: Path | str | None = None,
    test_only_gene_sets: bool = False,
    packet_free_assay_mapping: Path | str | None = None,
    packet_free_assay_mapping_sha256: str | None = None,
    retention_dir: Path | str | None = None,
    runner=None,
) -> FeatureTable:
    """Build gene, panel, singscore pathway, or external fraction features.

    Every returned table uses zero-based `patient_row` values aligned to the
    validated CohortView order. Real patient and sample identifiers are not
    copied into the returned or serialized feature rows.
    """
    family = family.casefold()
    if family not in _UNIT_FAMILIES:
        raise ValueError("Unsupported A-BIO feature family")
    cohort_id = str(view.metadata.cohort_id).casefold()
    if test_only_gene_sets and family not in _PATHWAY_FAMILIES:
        raise ValueError("test_only_gene_sets only applies to pathway feature families")
    if test_only_gene_sets and (
        cohort_id in known_cohort_ids()
        or getattr(view, "data_classification", "") == "real"
    ):
        raise ValueError("test_only_gene_sets is restricted to synthetic, unregistered cohorts")
    platform = str(view.metadata.representation.platform).casefold()
    targeted = platform in {"targeted_rna", "nanostring"}
    if family == "gene" and targeted:
        raise ValueError("The gene family excludes targeted_rna and nanostring platforms")
    if family in _PATHWAY_FAMILIES and targeted:
        raise ValueError("Pathway families exclude targeted_rna and nanostring platforms")
    if family == "targeted_subset" and (
        not targeted or cohort_id not in TARGETED_SUBSET_STUDIES
    ):
        raise ValueError("targeted_subset is restricted to the four signed targeted studies")
    if family == "fraction":
        if external is None:
            raise ValueError("Fraction features require an external patient table")
        return external_feature_table(
            external,
            cohort_id=view.metadata.cohort_id,
            expected_patients=len(view.clinical_rows),
        )
    if cohort_id == "gse176307":
        if packet_free_assay_mapping is None:
            raise FeatureUnavailableError(
                "gse176307_packet_free_assay_mapping_missing",
                "GSE176307 feature analysis needs a verified packet-free assay mapping",
            )
        if not packet_free_assay_mapping_sha256 or not re.fullmatch(
            r"[0-9a-f]{64}", str(packet_free_assay_mapping_sha256)
        ):
            raise FeatureUnavailableError(
                "gse176307_packet_free_assay_mapping_unverified",
                "GSE176307 packet-free assay mapping requires an expected SHA-256",
            )
    _gene_alias_addendum()
    if family in _PATHWAY_FAMILIES:
        return _pathway_features(
            view,
            family,
            gene_sets=gene_sets,
            common_gene_table=common_gene_table,
            test_only_gene_sets=test_only_gene_sets,
            runtime=runtime,
            gene_map=gene_map,
            gtf_path=gtf_path,
            probe_map=probe_map,
            packet_free_assay_mapping=packet_free_assay_mapping,
            packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
            r_out_dir=r_out_dir,
            retention_dir=retention_dir,
            runner=runner,
        )

    if family == "m5m6_gene":
        focused_panels = a_scoring.core.panel_definitions(
            ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
        )
        aliases = read_frozen_aliases()
        focused_panels = {
            name: tuple(aliases.get(gene, gene) for gene in members)
            for name, members in focused_panels.items()
        }
        genes = _gene_table(
            view, runtime=runtime, gene_map=gene_map, gtf_path=gtf_path,
            probe_map=probe_map,
            target_symbols=_resolution_targets(focused_panels),
            packet_free_assay_mapping=packet_free_assay_mapping,
            packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
        )
        return _focused_gene_table(genes, focused_panels)
    if family == "targeted_subset":
        aliases = read_frozen_aliases()
        memberships = read_hallmark_gene_sets(aliases=aliases)
        genes = _gene_table(
            view, runtime=runtime, gene_map=gene_map, gtf_path=gtf_path,
            probe_map=probe_map,
            target_symbols=tuple(sorted({gene for members in memberships.values() for gene in members})),
            packet_free_assay_mapping=packet_free_assay_mapping,
            packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
        )
        return _targeted_subset_table(view, genes, memberships)
    panel_definitions = (
        {name: tuple(members) for name, members in panels.items()}
        if panels is not None
        else _panel_definitions(AVAILABLE_PANEL_IDS)
    )
    genes = _gene_table(
        view,
        runtime=runtime,
        gene_map=gene_map,
        gtf_path=gtf_path,
        probe_map=probe_map,
        target_symbols=(None if family == "gene" else _resolution_targets(panel_definitions)),
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
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
        metadata={
            "scale_rule": "source_scale",
            "input_kind": "external_patient_table",
            "method_id_by_unit": {unit: "EXTERNAL_SOURCE_SCALE" for unit in values_by_unit},
        },
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
                "scorable": row.get("scorable", "true").casefold() == "true",
                "reason": row.get("reason", ""),
                "fixed_subset": [gene for gene in row.get("fixed_subset", "").split(";") if gene],
            }
    return FeatureTable(
        cohort_id=cohort_id,
        unit_family=unit_family,
        values_by_unit=values_by_unit,
        n_patients=n_patients,
        coverage=coverage,
        metadata=dict(metadata or {}),
    )


def _gene_table(
    view, *, runtime, gene_map, gtf_path, probe_map, target_symbols=None,
    packet_free_assay_mapping=None, packet_free_assay_mapping_sha256=None,
) -> FeatureTable:
    salmon_tpm = view.metadata.cohort_id == "gse176307"
    source_inputs_sha256 = {}
    if salmon_tpm:
        (
            feature_ids,
            sample_columns,
            matrix,
            source_inputs_sha256,
            patients_with_tpm_assay,
        ) = _gse176307_salmon_tpm(
            view, runtime,
            packet_free_assay_mapping=packet_free_assay_mapping,
            packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
        )
    else:
        feature_ids, sample_columns, matrix = _read_expression(view.expression_path)
    reference_path = a_scoring.gene_info_path(runtime)
    reference_sha256 = file_sha256(reference_path) if reference_path.is_file() else ""
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
    source_feature_ids = list(feature_ids)
    probe_counts = None
    dropped_unmapped = 0
    duplicate_gene_counts = None
    mapping_method_by_unit: dict[str, str] = {}
    source_feature_by_unit: dict[str, str] = {}
    mapping_status_by_unit: dict[str, str] = {}
    mapping_unavailable = []
    target_symbols = tuple(target_symbols) if target_symbols is not None else ()
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
        feature_ids, logged, probe_counts, dropped_unmapped, selected_sources = _collapse_probes(
            feature_ids, logged, canonical, return_source_ids=True,
        )
        for unit, source_id in zip(feature_ids, selected_sources):
            source_feature_by_unit[unit] = source_id
            mapping_status_by_unit[unit] = "mapped"
            mapping_method_by_unit[unit] = "cohort_probe_annotation"
        selected_source_ids = set(selected_sources)
        for source_id, canonical_symbol in zip(source_feature_ids, canonical):
            if source_id in selected_source_ids:
                continue
            status = "ambiguous" if canonical_symbol is None else "unmapped"
            mapping_unavailable.append({"source_feature_id": source_id, "status": status})
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
        canonical = _canonicalize_symbols(
            source_symbols,
            target_symbols,
            runtime=runtime,
            reference=reference,
        )
        feature_ids, logged, duplicate_gene_counts, duplicate_gene_symbols, selected_sources = _collapse_duplicate_genes(
            canonical, logged, source_feature_ids=source_feature_ids, return_source_ids=True,
        )
        for unit, source_id in zip(feature_ids, selected_sources):
            source_feature_by_unit[unit] = source_id
            status = "unmapped" if _is_unmapped_identifier(unit) else "mapped"
            mapping_status_by_unit[unit] = status
            mapping_method_by_unit[unit] = _mapping_method(
                source_id, unit, effective_feature_id,
                custom_map=custom_map, reference=reference,
            )
        selected_source_ids = set(selected_sources)
        for source_id, source_symbol, canonical_symbol in zip(source_feature_ids, source_symbols, canonical):
            if source_id in selected_source_ids:
                continue
            if canonical_symbol is None:
                status = "ambiguous" if _is_ambiguous_ensembl(source_id, effective_feature_id, reference) else "unmapped"
                mapping_unavailable.append({"source_feature_id": source_id, "status": status})

    values_by_unit = {unit: list(values) for unit, values in zip(feature_ids, logged)}
    metadata = {"scale_rule": scale_rule, "representation": {
        "platform": "rnaseq" if salmon_tpm else representation.platform,
        "unit": "tpm" if salmon_tpm else representation.unit,
        "transform": "linear" if salmon_tpm else representation.transform,
        "feature_id": effective_feature_id,
    }, "pinned_gene_info_sha256": reference_sha256}
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
    metadata["identifier_mapping"] = {
        "source_identifier_type": effective_feature_id,
        "rule": "frozen aliases, frozen gene alias addendum, pinned Entrez/Ensembl reference, cohort probe map, and outcome-blind duplicate collapse",
        "source_feature_by_symbol": source_feature_by_unit,
        "mapping_status_by_symbol": mapping_status_by_unit,
        "mapping_method_by_symbol": mapping_method_by_unit,
        "source_mapping_by_symbol": {
            unit: {
                "source_feature_id": source_feature_by_unit[unit],
                "status": mapping_status_by_unit[unit],
                "method": mapping_method_by_unit[unit],
            }
            for unit in source_feature_by_unit
        },
        "unmapped_or_ambiguous_source_rows": mapping_unavailable,
        "alias_table_sha256": file_sha256(FROZEN_ALIASES),
        "gene_alias_addendum_sha256": file_sha256(GENE_ALIAS_ADDENDUM_PATH),
    }
    if recount3_used:
        metadata["recount3_non_primary_dropped"] = recount3_dropped
    metadata["m5m6_gene_units"] = sorted(_m5m6_gene_units())
    metadata["method_id_by_unit"] = {unit: "GENE_STUDY_SCALE" for unit in values_by_unit}
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
        for patient_row in range(genes.n_patients):
            expression = {
                gene: gene_values[gene][patient_row]
                for gene in gene_order
                if gene_values[gene][patient_row] is not None
            }
            scores, patient_coverage = panel_scores(expression, {unit: members}, require_complete=True)
            unit_scores.append(scores[unit])
        scores_by_unit[unit] = unit_scores
        member_coverage = _panel_member_coverage(gene_values, members)
        complete = member_coverage["n_found"] == len(members)
        coverage[unit] = {
            "n_found": member_coverage["n_found"],
            "n_total": len(members),
            "missing": member_coverage["missing"],
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
            "method_id_by_unit": {unit: PANEL_METHOD_IDS.get(unit, f"CUSTOM_MEAN_{unit}") for unit in panels},
            "custom_method_ids": {unit: PANEL_METHOD_IDS.get(unit, f"CUSTOM_MEAN_{unit}") for unit in panels},
            "identifier_mapping": dict(genes.metadata.get("identifier_mapping", {})),
            "pinned_gene_info_sha256": genes.metadata.get("pinned_gene_info_sha256", ""),
            "source_inputs_sha256": dict(genes.metadata.get("source_inputs_sha256", {})),
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
        fixed_subset = tuple(gene for gene in members if gene in gene_values and any(
            value is not None for value in gene_values[gene]
        )) if coverage_met else ()
        unit_scores = []
        for patient_row in range(genes.n_patients):
            if not coverage_met:
                unit_scores.append(None)
                continue
            expression = {
                gene: gene_values[gene][patient_row]
                for gene in fixed_subset
                if gene_values[gene][patient_row] is not None
            }
            if len(expression) != len(fixed_subset):
                unit_scores.append(None)
                continue
            scores, _ = panel_scores(expression, {unit: fixed_subset}, require_complete=True)
            unit_scores.append(scores[unit])
        scores_by_unit[unit] = unit_scores
        coverage[unit] = {
            "n_found": n_found,
            "n_total": len(members),
            "missing": missing,
            "complete": coverage_met,
            "full_coverage": not missing,
            "fixed_subset": list(fixed_subset),
            "scorable": coverage_met,
        }
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="panel_coverage90",
        values_by_unit=scores_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": "tools.a_scoring.panel_scores; unweighted mean over one fixed study subset",
            "source_scale_rule": genes.metadata["scale_rule"],
            "coverage_policy": (
                "one fixed study subset of at least 90% of members; a patient missing any "
                "fixed-subset member receives NA"
            ),
            "sensitivity_label": SENSITIVITY_LABEL,
            "method_id_by_unit": {unit: PANEL_METHOD_IDS.get(unit, f"CUSTOM_MEAN_{unit}") for unit in panels},
            "custom_method_ids": {unit: PANEL_METHOD_IDS.get(unit, f"CUSTOM_MEAN_{unit}") for unit in panels},
        },
    )


def _coverage90_met(n_found: int, n_total: int) -> bool:
    if n_total <= 0 or n_found < 0 or n_found > n_total:
        raise ValueError("Panel coverage counts are invalid")
    return n_found * 10 >= n_total * 9


def _panel_member_coverage(gene_values, members):
    missing = [
        gene for gene in members
        if gene not in gene_values or not any(value is not None for value in gene_values[gene])
    ]
    return {"n_found": len(members) - len(missing), "missing": missing}


def read_gse176307_packet_free_assay_mapping(
    path: Path | str,
    *,
    expected_sha256: str,
    clinical_rows: Sequence[Mapping],
) -> tuple[dict[str, str], dict[str, object]]:
    """Verify a separately supplied patient-to-assay map without opening a packet."""
    mapping_path = Path(path).expanduser()
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256 or "")):
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_unverified",
            "GSE176307 packet-free assay mapping requires an expected SHA-256",
        )
    _reject_mapping_symlink_ancestry(mapping_path)
    try:
        actual_sha256 = file_sha256(mapping_path)
    except (OSError, ValueError):
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_missing",
            "GSE176307 packet-free assay mapping is unavailable",
        ) from None
    if actual_sha256 != expected_sha256:
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_hash_mismatch",
            "GSE176307 packet-free assay mapping hash differs",
        )
    try:
        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_schema_invalid",
            "GSE176307 packet-free assay mapping is malformed",
        ) from None
    expected_source_hashes = {
        "salmon_tpm": _GSE176307_TPM_SHA256,
        "sample_assay_key": _GSE176307_KEY_SHA256,
        "geo_family_soft": _GSE176307_SOFT_SHA256,
    }
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("cohort_id") != "gse176307"
        or payload.get("source_inputs_sha256") != expected_source_hashes
        or not isinstance(payload.get("rows"), list)
    ):
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_schema_invalid",
            "GSE176307 packet-free assay mapping does not match the frozen schema or source identities",
        )
    clinical_by_patient = {}
    for row in clinical_rows:
        patient_id = str(row.get("patient_id", ""))
        sample_id = str(row.get("sample_id", ""))
        if not patient_id or not sample_id or patient_id in clinical_by_patient:
            raise FeatureUnavailableError(
                "gse176307_packet_free_assay_mapping_identity_mismatch",
                "GSE176307 clinical rows need unique patient and GEO sample identities",
            )
        clinical_by_patient[patient_id] = sample_id
    by_patient: dict[str, str] = {}
    assays: set[str] = set()
    for row in payload["rows"]:
        if not isinstance(row, dict) or set(row) != {"patient_id", "sample_id", "tpm_assay_sample_id"}:
            raise FeatureUnavailableError(
                "gse176307_packet_free_assay_mapping_schema_invalid",
                "GSE176307 packet-free assay mapping rows need exact identity columns",
            )
        patient_id = str(row.get("patient_id", ""))
        sample_id = str(row.get("sample_id", ""))
        assay_id = str(row.get("tpm_assay_sample_id", ""))
        if (
            not patient_id or not sample_id or not assay_id
            or patient_id in by_patient or assay_id in assays
            or clinical_by_patient.get(patient_id) != sample_id
        ):
            raise FeatureUnavailableError(
                "gse176307_packet_free_assay_mapping_identity_mismatch",
                "GSE176307 packet-free assay mapping has a duplicate or mismatched patient/sample pair",
            )
        by_patient[patient_id] = assay_id
        assays.add(assay_id)
    if not by_patient:
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_identity_mismatch",
            "GSE176307 packet-free assay mapping contains no matched patients",
        )
    return by_patient, {
        "mapping_sha256": actual_sha256,
        "source_inputs_sha256": expected_source_hashes,
        "mapped_patient_count": len(by_patient),
    }


def _reject_mapping_symlink_ancestry(path: Path) -> None:
    from tools.a_bio.paths import reject_symlink_components

    try:
        reject_symlink_components(path, label="GSE176307 packet-free assay mapping")
    except (OSError, ValueError):
        raise FeatureUnavailableError(
            "gse176307_packet_free_assay_mapping_path_unsafe",
            "GSE176307 packet-free assay mapping path contains a forbidden component or symlink",
        ) from None


def _gse176307_sources(
    view, runtime, *, packet_free_assay_mapping=None, packet_free_assay_mapping_sha256=None,
):
    """Resolve TPM source identities without calling packet-opening A-P2 mapping."""
    from tools.a_p2 import build as a_p2_build

    clinical_rows = view.clinical_rows
    patient_ids = [str(row.get("patient_id", "")) for row in clinical_rows]
    if any(not patient_id for patient_id in patient_ids) or len(set(patient_ids)) != len(patient_ids):
        raise ValueError("GSE176307 cohort-view row identities must be present and unique")
    assay_by_patient, mapping_identity = read_gse176307_packet_free_assay_mapping(
        packet_free_assay_mapping,
        expected_sha256=packet_free_assay_mapping_sha256,
        clinical_rows=clinical_rows,
    )
    source_inputs = {}
    runtime_root = a_p2_build._runtime_path(runtime)
    base = runtime_root / "gse176307"
    matrix_path = a_p2_build.source(
        base / "store_tpm/objects" / _GSE176307_TPM_SHA256,
        source_inputs,
        runtime,
    )
    key_path = a_p2_build.source(
        base / "store_tpm/objects" / _GSE176307_KEY_SHA256,
        source_inputs,
        runtime,
    )
    soft_path = a_p2_build.source(
        base / "store/objects" / _GSE176307_SOFT_SHA256,
        source_inputs,
        runtime,
    )
    source_hashes = {
        "salmon_tpm": a_p2_build.sha256(matrix_path),
        "sample_assay_key": a_p2_build.sha256(key_path),
        "geo_family_soft": a_p2_build.sha256(soft_path),
        "packet_free_assay_mapping": mapping_identity["mapping_sha256"],
    }
    for role, expected in mapping_identity["source_inputs_sha256"].items():
        if source_hashes[role] != expected:
            raise FeatureUnavailableError("source_hash_mismatch", "Pinned GSE176307 source hash differs")
    return patient_ids, assay_by_patient, matrix_path, source_hashes


def _gse176307_source_hashes(
    view, runtime, *, packet_free_assay_mapping=None, packet_free_assay_mapping_sha256=None,
):
    """Return pinned source identities without reading the TPM matrix."""
    return _gse176307_sources(
        view, runtime,
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
    )[3]


def _gse176307_salmon_tpm(
    view, runtime, *, packet_free_assay_mapping=None, packet_free_assay_mapping_sha256=None,
):
    """Read GSE176307 Salmon TPM through the verified packet-free assay map."""
    from tools.a_p2 import build as a_p2_build

    patient_ids, assay_by_patient, matrix_path, source_hashes = _gse176307_sources(
        view, runtime,
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
    )
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


def _pathway_features(
    view,
    family,
    *,
    gene_sets,
    common_gene_table,
    test_only_gene_sets,
    runtime,
    gene_map,
    gtf_path,
    probe_map,
    packet_free_assay_mapping,
    packet_free_assay_mapping_sha256,
    r_out_dir,
    retention_dir,
    runner,
):
    from .r_manifest import run_r_sanitised

    aliases = read_frozen_aliases()
    gene_set_path = Path(gene_sets).expanduser().resolve(strict=True) if gene_sets is not None else HALLMARK_GMT
    memberships = read_hallmark_gene_sets(
        gene_set_path,
        aliases=aliases,
        test_only=test_only_gene_sets,
    )
    common_path = None
    common_memberships = None
    if family == "pathway_common":
        common_path = Path(common_gene_table).expanduser().resolve(strict=True) if common_gene_table else COMMON_GENE_TABLE
        common_memberships = read_common_gene_sets(common_path, aliases=aliases)

    genes = _gene_table(
        view,
        runtime=runtime,
        gene_map=gene_map,
        gtf_path=gtf_path,
        probe_map=probe_map,
        target_symbols=tuple(sorted({gene for members in memberships.values() for gene in members})),
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
    )
    output_dir = Path(r_out_dir) if r_out_dir is not None else Path(view.expression_path).parent / "singscore-stage"
    matrix_path = output_dir.parent / (output_dir.name + ".expression.tsv")
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    _write_expression_matrix(matrix_path, genes)
    script = Path(__file__).resolve().parents[2] / "r/scripts/singscore.R"
    inputs = {
        "expression": matrix_path,
        "gene_sets": gene_set_path,
        "aliases": FROZEN_ALIASES,
    }
    config = {
        "family": family,
        "test_only_gene_sets": bool(test_only_gene_sets),
        "gene_set_sha256": file_sha256(gene_set_path),
        "common_gene_table_sha256": "",
        "minimum_common_membership": 10,
    }
    if common_path is not None:
        inputs["common_gene_table"] = common_path
        config["common_gene_table_sha256"] = file_sha256(common_path)
    result = run_r_sanitised(
        script,
        inputs,
        {**config, "expected_outputs": ["scores.tsv", "coverage.tsv"]},
        output_dir,
        script_id="r/scripts/singscore.R",
        runner=runner,
        retention_dir=retention_dir,
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
            "missing": [gene for gene in row.get("missing_genes", "").split(";") if gene],
            "complete": row["complete"].casefold() == "true",
            "scorable": row.get("scorable", "true").casefold() == "true",
            "reason": row.get("reason", ""),
            "fixed_subset": [gene for gene in row.get("fixed_subset", "").split(";") if gene],
        }
        for row in coverage_rows
    }
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family=f"test_only_{family}" if test_only_gene_sets else family,
        values_by_unit=values_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": "singscore simpleScore; tiesMethod=min; knownDirection=TRUE; default centring",
            "source_scale_rule": genes.metadata["scale_rule"],
            "coverage_policy": (
                "complete Hallmark membership required" if family == "pathway" else
                "fixed study subset with at least 90% coverage; patients missing a subset gene receive NA"
                if family == "pathway_coverage90" else
                "fixed hashed common-gene membership; every common gene is required"
            ),
            "sensitivity_label": SENSITIVITY_LABEL if family in _SENSITIVITY_FAMILIES else "",
            "source_gene_sets_sha256": file_sha256(gene_set_path),
            "source_gene_sets_collection": "hallmark_test_only" if test_only_gene_sets else "hallmark_2026.1.Hs",
            "common_gene_table_sha256": file_sha256(common_path) if common_path is not None else "",
            "membership_sha256": {
                unit: membership_sha256(tuple(sorted(members)))
                for unit, members in (common_memberships or memberships).items()
            },
            "method_id_by_unit": {
                unit: "SINGSCORE_TEST_ONLY_GENE_SETS" if test_only_gene_sets else "SINGSCORE_HALLMARK_2026_1"
                for unit in memberships
            },
            "test_only_gene_sets": bool(test_only_gene_sets),
            "r_manifest": result.manifest,
        },
    )


def _targeted_subset_table(view, genes: FeatureTable, memberships) -> FeatureTable:
    values_by_unit: dict[str, list[float | None]] = {}
    coverage: dict[str, dict] = {}
    method_ids = {}
    for unit, members in memberships.items():
        available = tuple(
            gene for gene in members
            if gene in genes.values_by_unit and any(
                value is not None for value in genes.values_by_unit[gene]
            )
        )
        missing = [gene for gene in members if gene not in available]
        scores: list[float | None] = []
        for patient_row in range(genes.n_patients):
            row = {
                gene: genes.values_by_unit[gene][patient_row]
                for gene in available
                if genes.values_by_unit[gene][patient_row] is not None
            }
            if not available or len(row) != len(available):
                scores.append(None)
            else:
                scores.append(sum(float(row[gene]) for gene in available) / len(available))
        values_by_unit[unit] = scores
        coverage[unit] = {
            "n_found": len(available),
            "n_total": len(members),
            "missing": missing,
            "complete": bool(available),
            "scorable": bool(available),
            "fixed_subset": list(available),
        }
        method_ids[unit] = "CUSTOM_MEAN_TARGETED_SUBSET"
    return FeatureTable(
        cohort_id=view.metadata.cohort_id,
        unit_family="targeted_subset",
        values_by_unit=values_by_unit,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            "score_rule": "unweighted mean of the fixed Hallmark members measured in this study",
            "coverage_policy": "fixed study subset; a patient missing any subset member receives NA",
            "sensitivity_label": SENSITIVITY_LABEL,
            "source_gene_sets_sha256": file_sha256(HALLMARK_GMT),
            "source_gene_sets_collection": "hallmark_2026.1.Hs",
            "method_id_by_unit": method_ids,
        },
    )


def _focused_gene_table(genes: FeatureTable, panels: Mapping[str, Sequence[str]]) -> FeatureTable:
    units = tuple(dict.fromkeys(gene for members in panels.values() for gene in members))
    values = {
        unit: list(genes.values_by_unit.get(unit, [None] * genes.n_patients))
        for unit in units
    }
    coverage = {
        unit: {
            "n_found": int(unit in genes.values_by_unit and any(value is not None for value in genes.values_by_unit[unit])),
            "n_total": 1,
            "missing": [] if unit in genes.values_by_unit and any(value is not None for value in genes.values_by_unit[unit]) else [unit],
            "complete": unit in genes.values_by_unit and any(value is not None for value in genes.values_by_unit[unit]),
        }
        for unit in units
    }
    return FeatureTable(
        cohort_id=genes.cohort_id,
        unit_family="m5m6_gene",
        values_by_unit=values,
        n_patients=genes.n_patients,
        coverage=coverage,
        metadata={
            **genes.metadata,
            "method_id_by_unit": {unit: "GENE_STUDY_SCALE" for unit in units},
            "m5m6_gene_units": list(units),
            "claim_scope": "only m5m6_gene supports claims about M5 and M6 genes",
        },
    )


def _study_scale(matrix, representation):
    platform = str(representation.platform).casefold()
    unit = str(representation.unit).casefold()
    transform = str(representation.transform).casefold()
    if platform == "rnaseq" and unit in {"tpm", "fpkm", "rpkm"} and transform == "linear":
        logged = [
            [math.log2(value + 1.0) if value is not None else None for value in row]
            for row in matrix
        ] if unit == "tpm" else a_scoring.log2p1(matrix, representation)
        return "log2(TPM+1)", logged
    if platform == "rnaseq" and unit == "counts" and transform == "linear":
        if any(value is None for row in matrix for value in row):
            raise ValueError("Count matrices cannot contain missing values before CPM scaling")
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
                values = [
                    None if value.strip().casefold() in {"", "na", "nan"} else float(value)
                    for value in row[1:]
                ]
            except ValueError:
                raise ValueError("Expression matrix contains non-numeric values") from None
            if any(value is not None and not math.isfinite(value) for value in values):
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


def _collapse_probes(feature_ids, matrix, canonical_features, *, return_source_ids=False):
    probes_by_gene: dict[str, list[tuple[float, str, list[float]]]] = {}
    unmapped = 0
    for probe, values, gene in zip(feature_ids, matrix, canonical_features):
        if not gene:
            unmapped += 1
            continue
        measured = [value for value in values if value is not None]
        mean_expression = math.fsum(measured) / len(measured) if measured else -math.inf
        probes_by_gene.setdefault(gene, []).append((mean_expression, probe, values))
    chosen = []
    for gene in sorted(probes_by_gene):
        # Mean expression is outcome-blind; lexical probe order resolves exact ties.
        row = sorted(probes_by_gene[gene], key=lambda item: (-item[0], item[1]))[0]
        chosen.append((gene, row[2], row[1]))
    counts = {
        "probes": len(feature_ids),
        "mapped_probes": len(feature_ids) - unmapped,
        "genes": len(chosen),
        "collapsed_probes": len(feature_ids) - unmapped - len(chosen),
    }
    result = ([gene for gene, _, _ in chosen], [values for _, values, _ in chosen], counts, unmapped)
    return (*result, [source_id for _, _, source_id in chosen]) if return_source_ids else result


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
    definitions = panel_definitions or _panel_definitions(AVAILABLE_PANEL_IDS)
    aliases = read_frozen_aliases()
    return tuple(sorted({
        aliases.get(gene, gene)
        for members in definitions.values()
        for gene in members
    } | {"GZMA", "PRF1"}))


def _panel_definitions(panel_ids=AVAILABLE_PANEL_IDS):
    selected = tuple(panel_ids)
    panel_definitions = a_scoring.core.panel_definitions(
        tuple(panel for panel in selected if panel != "HALLMARK_INTERFERON_GAMMA_RESPONSE")
    )
    if "HALLMARK_INTERFERON_GAMMA_RESPONSE" in selected:
        aliases = read_frozen_aliases()
        hallmark = read_hallmark_gene_sets(aliases=aliases)
        panel_definitions["HALLMARK_INTERFERON_GAMMA_RESPONSE"] = hallmark[
            "HALLMARK_INTERFERON_GAMMA_RESPONSE"
        ]
    return {panel: panel_definitions[panel] for panel in selected}


def _m5m6_gene_units():
    focused = a_scoring.core.panel_definitions(
        ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
    )
    aliases = read_frozen_aliases()
    return {
        aliases.get(gene, gene)
        for members in focused.values()
        for gene in members
    }


@lru_cache(maxsize=4)
def _gene_reference(runtime):
    """Load the pinned Entrez and synonym maps plus its Ensembl crosswalk."""
    info_path = a_scoring.gene_info_path(runtime)
    if not info_path.is_file():
        return {"by_id": {}, "synonyms": {}, "ensembl": {}, "ambiguous_ensembl": frozenset()}
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
    ambiguous_ensembl = frozenset(
        ensembl_id for ensembl_id, symbols in ensembl_candidates.items() if len(symbols) > 1
    )
    return {
        "by_id": by_id, "synonyms": synonyms, "ensembl": ensembl,
        "ambiguous_ensembl": ambiguous_ensembl,
    }


def _is_unmapped_identifier(value: str) -> bool:
    return str(value).startswith(("ENSEMBL:", "ENTREZ:", "PROBE:"))


def _is_ambiguous_ensembl(source_feature_id: str, feature_id_type: str, reference) -> bool:
    return (
        str(feature_id_type).casefold() == "ensembl"
        and str(source_feature_id).split(".", 1)[0] in reference.get("ambiguous_ensembl", ())
    )


def _mapping_method(source_feature_id, symbol, feature_id_type, *, custom_map, reference):
    source = str(source_feature_id).strip()
    feature_type = str(feature_id_type).casefold()
    if source in custom_map:
        return "explicit_gene_map"
    if feature_type == "ensembl":
        base = source.split(".", 1)[0]
        if base in _gene_alias_addendum():
            return "frozen_gene_alias_addendum"
        if base in reference.get("ensembl", {}):
            return "pinned_entrez_ensembl_crosswalk"
        return "unmapped_ensembl"
    if feature_type == "entrez":
        return "pinned_entrez_gene_info" if source in reference.get("by_id", {}) else "unmapped_entrez"
    if feature_type == "probe":
        return "cohort_probe_annotation"
    aliases = a_scoring.core._frozen_aliases(str(a_scoring.core.ALIAS_TABLE_PATH))
    if aliases.get(source, source) != source:
        return "frozen_symbol_alias"
    return "source_symbol"


@lru_cache(maxsize=1)
def _gene_alias_addendum() -> dict[str, str]:
    proposals = read_identifier_proposals()
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
    for proposal in proposals:
        if mapping.get(proposal["source_id"]) != proposal["registry_symbol"]:
            raise ValueError("Gene alias addendum does not contain every signed Hallmark proposal")
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


def map_de_ranking_to_symbols(
    de_rows: Sequence[Mapping],
    identifier_mapping: Mapping,
) -> tuple[list[dict[str, object]], list[dict[str, str]], dict[str, int]]:
    """Map one study's declared DE statistic through A-META's selected feature rows."""
    mappings = identifier_mapping.get("source_mapping_by_symbol", {})
    if not isinstance(mappings, Mapping):
        raise ValueError("DE ranking needs A-META identifier mapping provenance")
    by_source = {}
    for symbol, raw in mappings.items():
        if not isinstance(raw, Mapping):
            raise ValueError("A-META source mapping inventory is malformed")
        source_id = str(raw.get("source_feature_id", ""))
        status = str(raw.get("status", ""))
        if not source_id or source_id in by_source:
            raise ValueError("A-META source mapping is missing or not one-to-one")
        by_source[source_id] = (str(symbol), status, str(raw.get("method", "")))

    ranked = []
    mapping_rows = []
    counts = {"mapped": 0, "ambiguous": 0, "unmapped": 0, "missing_statistic": 0}
    seen_symbols = set()
    for raw in de_rows:
        source_id = str(raw.get("gene", ""))
        resolved = by_source.get(source_id)
        if resolved is None:
            mapping_rows.append({
                "source_feature_id": source_id,
                "symbol": "",
                "mapping_method": "no_selected_a_meta_feature",
                "mapping_status": "unmapped",
            })
            counts["unmapped"] += 1
            continue
        symbol, status, method = resolved
        if status != "mapped":
            safe_status = status if status in {"ambiguous", "unmapped"} else "unmapped"
            mapping_rows.append({
                "source_feature_id": source_id,
                "symbol": symbol,
                "mapping_method": method,
                "mapping_status": safe_status,
            })
            counts[safe_status] += 1
            continue
        value = _numeric_or_missing(raw.get("statistic"))
        if value is None:
            mapping_rows.append({
                "source_feature_id": source_id,
                "symbol": symbol,
                "mapping_method": method,
                "mapping_status": "missing_statistic",
            })
            counts["missing_statistic"] += 1
            continue
        if symbol in seen_symbols:
            raise ValueError("DE symbol mapping produced a duplicate ranked gene")
        seen_symbols.add(symbol)
        ranked.append({"gene": symbol, "statistic": value})
        mapping_rows.append({
            "source_feature_id": source_id,
            "symbol": symbol,
            "mapping_method": method,
            "mapping_status": "mapped",
        })
        counts["mapped"] += 1
    ranked.sort(key=lambda row: str(row["gene"]))
    return ranked, mapping_rows, counts


def write_symbol_expression_projection(
    table: FeatureTable,
    path: Path | str,
    sample_ids: Sequence[str],
) -> dict[str, int]:
    """Write mapped A-META rows in the cohort order expected by A-BULK panels."""
    if len(sample_ids) != table.n_patients or len(set(sample_ids)) != len(sample_ids):
        raise ValueError("Symbol projection sample identities do not match the feature rows")
    mapping = table.metadata.get("identifier_mapping", {})
    status_by_symbol = mapping.get("mapping_status_by_symbol", {})
    selected = [
        unit for unit in sorted(table.values_by_unit)
        if status_by_symbol.get(unit) == "mapped"
    ]
    unmapped = sum(status != "mapped" for status in status_by_symbol.values())
    content_rows = [["gene", *[str(value) for value in sample_ids]]]
    for unit in selected:
        values = table.values_by_unit[unit]
        if len(values) != table.n_patients:
            raise ValueError("Feature vector length differs from cohort size")
        content_rows.append([
            unit,
            *["NA" if value is None else _number_text(value) for value in values],
        ])
    output = io.StringIO(newline="")
    csv.writer(output, delimiter="\t", lineterminator="\n").writerows(content_rows)
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Symbol expression projection path contains an escaping component")
    _reject_mapping_symlink_ancestry(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_mapping_symlink_ancestry(path)
    content = output.getvalue().encode("utf-8")
    if path.exists():
        if path.is_dir() or path.read_bytes() != content:
            raise FileExistsError("Refusing to replace a different symbol expression projection")
        return {"mapped_gene_count": len(selected), "unmapped_gene_count": unmapped}
    with path.open("xb") as stream:
        stream.write(content)
    return {"mapped_gene_count": len(selected), "unmapped_gene_count": unmapped}


def _number_text(value) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Mapped symbol expression values must be finite or missing")
    return format(number, ".15g")


def _collapse_duplicate_genes(feature_ids, matrix, *, source_feature_ids=None, return_source_ids=False):
    """Retain one outcome-blind representative for each canonical gene row."""
    genes: dict[str, list[tuple[float, int, list[float | None]]]] = {}
    selected_source_ids = list(source_feature_ids) if source_feature_ids is not None else list(feature_ids)
    if len(selected_source_ids) != len(feature_ids):
        raise ValueError("Source feature identifiers do not align with expression rows")
    for row_index, (gene, values) in enumerate(zip(feature_ids, matrix)):
        if not gene:
            continue
        measured = [value for value in values if value is not None]
        mean_expression = math.fsum(measured) / len(measured) if measured else -math.inf
        genes.setdefault(gene, []).append((mean_expression, row_index, values, selected_source_ids[row_index]))
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
        chosen.append((gene, sorted(candidates, key=lambda row: (-row[0], row[1]))[0][2:4]))
    counts = {
        "input_rows": len(feature_ids),
        "genes": len(chosen),
        "duplicate_gene_groups": duplicate_groups,
        "duplicate_rows_removed": duplicate_rows,
    }
    result = ([gene for gene, _ in chosen], [values for _, (values, _) in chosen], counts, duplicate_symbols)
    return (*result, [source_id for _, (_, source_id) in chosen]) if return_source_ids else result


def _write_expression_matrix(path: Path, table: FeatureTable) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *[str(index) for index in range(table.n_patients)]])
        for gene in sorted(table.values_by_unit):
            gene_values = table.values_by_unit[gene]
            if not any(value is not None for value in gene_values):
                continue
            writer.writerow([gene, *["NA" if value is None else value for value in gene_values]])


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
