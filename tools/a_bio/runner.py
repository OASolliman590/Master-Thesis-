"""A-BIO route orchestration. The outcome-free route never loads outcomes."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from typing import Any

from tools.a_bulk.core import validate_dataset_identifiers
from tools.a_cohorts import core as cohort_core
from tools.a_cohorts.view import (
    CohortMetadata,
    MeasurementRepresentation,
    _normalise_cancer_row,
    cohort_metadata,
    normalise_drug_class,
)
from tools.a_meta.provenance import is_locked_study, known_cohort_ids
from .paths import (
    absolute_path,
    preflight_tree,
    reject_symlink_components,
    validate_contained_path,
    validate_single_component,
    write_immutable_bytes,
)
from .enrichment import MetaRankingContract, build_meta_ranking, run_meta_fgsea


class OutcomeGuardError(ValueError):
    """A real-cohort outcome route was requested before release."""


class AdjustedAnalysisUnavailable(ValueError):
    """Adjusted analyses are locked until clinical sets and missingness rules are signed."""


@dataclass(frozen=True)
class LoadedCohort:
    metadata: CohortMetadata
    expression_path: Path
    clinical_path: Path
    clinical_rows: list[dict[str, str]]
    data_classification: str
    manifest_path: Path
    manifest_sha256: str
    output_sha256: dict[str, str]
    clinical_columns_read: tuple[str, ...]
    source_inputs_sha256: dict[str, str]
    checks: dict[str, str]


_SYNTHETIC_PRODUCER = "tools.a_bio.synthetic_fixture"
_SYNTHETIC_MANIFEST_KIND = "cohort_input"
_IDENTITY_COLUMN = "patient_id"
_BULK_CLINICAL_COLUMNS = (
    "drug_class", "treatment_class", "batch", "batch_id", "processing_batch",
    "seq_batch", "biopsy", "biopsy_site", "site", "tissue_site", "specimen_site",
)
_OUTCOME_COLUMNS = {
    "orr": ("raw_orr", "orr", "endpoint_definition"),
    "clinical_benefit": ("raw_clinical_benefit", "clinical_benefit", "endpoint_definition"),
    "source_label": (
        "treatment_outcome", "raw_clinical_benefit", "raw_orr",
        "clinical_benefit", "orr", "endpoint_definition",
    ),
}
_ENDPOINT_FAMILIES = {"orr", "clinical_benefit", "source_label"}
A_BIO_FAMILIES = (
    "panel", "m5m6_gene", "gene", "pathway", "panel_coverage90",
    "pathway_coverage90", "pathway_common", "targeted_subset",
)
SYNTHESIS_STRATA = (
    "per_cancer", "per_drug_class", "melanoma_cancer_drug", "across_cancers",
)
AVAILABILITY_COLUMNS = (
    "cohort_id", "unit_family", "status", "reason", "unit_count", "scorable_unit_count",
)
COVERAGE_COLUMNS = (
    "cohort_id", "unit_family", "unit", "n_found", "n_total", "complete", "scorable",
    "missing", "fixed_subset", "reason", "sensitivity_label",
)
BULK_COLUMNS = (
    "cohort_id", "endpoint_family", "endpoint_definition_id", "stratum", "stage", "collection",
    "status", "reason", "sample_count", "input_sample_count", "excluded_treatment_count",
    "analysis_sample_count", "response_exclusion_counts", "ranking_contract_id", "ranked_gene_count",
)
SYNTHESIS_STATUS_COLUMNS = ("stratum", "status", "summary_rows", "reason")


def load_cohort_materialization(
    cohort_id: str,
    *,
    runtime: Path | str | None = None,
    route: str,
    synthetic_manifest: Path | str | None = None,
    allow_outcomes: bool = False,
) -> LoadedCohort:
    """Read simple tables without invoking packet-opening loader validation."""
    if runtime is not None:
        reject_symlink_components(runtime, label="Cohort runtime")
    if synthetic_manifest is not None:
        reject_symlink_components(synthetic_manifest, label="Synthetic provenance")
    if route not in {"outcome-free", "outcomes"}:
        raise ValueError("A-BIO route must be outcome-free or outcomes")
    if route == "outcome-free" and allow_outcomes:
        raise ValueError("The outcome-free route does not accept outcome release")

    cohort_id = validate_single_component(str(cohort_id), label="Cohort identifier")
    validate_dataset_identifiers(cohort_id)

    if synthetic_manifest is not None:
        _reject_known_real_identifiers((cohort_id,))
        runtime_path = absolute_path(_runtime_root(runtime), label="Cohort runtime")
        expected_manifest = runtime_path / cohort_id / "simple" / "manifest.json"
        manifest_path = validate_contained_path(
            runtime_path, synthetic_manifest, label="Cohort materialization", must_exist=True,
        )
        expected_manifest = validate_contained_path(
            runtime_path, expected_manifest, label="Cohort materialization", must_exist=True,
        )
        if manifest_path != expected_manifest:
            raise ValueError("synthetic manifest is outside the expected cohort path")
        manifest = _read_json(manifest_path)
        _validate_synthetic_input_manifest(manifest, cohort_id)
        _reject_manifest_real_identifiers(manifest)
        classification = "synthetic"
        metadata = _synthetic_metadata(cohort_id, manifest.get("metadata"))
    else:
        if route == "outcomes" and not allow_outcomes:
            raise OutcomeGuardError(
                "Real outcome routes require an explicit release; no cohort or clinical input was read"
            )
        metadata = cohort_metadata(cohort_id)
        classification = "real"
        runtime_path = absolute_path(_runtime_root(runtime), label="Cohort runtime")
        manifest_path = runtime_path / cohort_id / "simple" / "manifest.json"
        manifest_path = validate_contained_path(
            runtime_path, manifest_path, label="Cohort materialization", must_exist=True,
        )
        manifest = _read_json(manifest_path)
        if manifest.get("cohort") != cohort_id or manifest.get("loader_version") != cohort_core.VERSION:
            raise ValueError("simple materialization manifest is stale")
    output_dir = runtime_path / cohort_id / "simple"
    output_dir = validate_contained_path(
        runtime_path, output_dir, label="Cohort materialization", must_exist=True,
    )
    if manifest_path != output_dir / "manifest.json":
        raise ValueError("materialization manifest is outside the expected cohort path")

    expected_outputs = set(cohort_core.expected_output_names(cohort_id))
    output_hashes = manifest.get("outputs_sha256", manifest.get("output_sha256"))
    if not isinstance(output_hashes, dict) or set(output_hashes) != expected_outputs:
        raise ValueError("simple materialization output hash inventory is incomplete")
    verified_hashes = {}
    for name, expected_hash in output_hashes.items():
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("simple materialization output path is invalid")
        output_path = output_dir / name
        validate_contained_path(
            runtime_path, output_path, label="Cohort materialization output", must_exist=True,
        )
        actual_hash = _sha256_file(output_path)
        if not isinstance(expected_hash, str) or actual_hash != expected_hash:
            raise ValueError("simple materialization output hash mismatch")
        verified_hashes[name] = actual_hash
    source_inputs = _source_inventory_from_manifest(manifest)

    patient_count = manifest.get("patients")
    if isinstance(patient_count, bool) or not isinstance(patient_count, int) or patient_count < 1:
        raise ValueError("simple materialization patient count is invalid")
    expression_path = output_dir / "expression.tsv"
    clinical_path = output_dir / "clinical.tsv"
    expression_samples = _expression_sample_ids(expression_path)
    clinical_rows, columns_read = _read_named_clinical_columns(
        clinical_path, _clinical_columns(metadata, route), metadata,
    )
    clinical_samples = [row[_IDENTITY_COLUMN] for row in clinical_rows]
    if (
        len(clinical_samples) != patient_count
        or len(set(clinical_samples)) != len(clinical_samples)
        or not clinical_samples
        or expression_samples != clinical_samples
    ):
        raise ValueError("expression and clinical identities do not align")

    return LoadedCohort(
        metadata=metadata,
        expression_path=expression_path,
        clinical_path=clinical_path,
        clinical_rows=clinical_rows,
        data_classification=classification,
        manifest_path=manifest_path,
        manifest_sha256=_sha256_file(manifest_path),
        output_sha256=verified_hashes,
        clinical_columns_read=columns_read,
        source_inputs_sha256=source_inputs,
        checks={
            "signed_eligibility": "passed" if classification == "real" else "not_applicable_synthetic",
            "materialization_paths": "passed",
            "output_hashes": "passed",
            "patient_expression_alignment": "passed",
            "ingestion_packet": "not_opened",
            "source_input_hashes": "not_revalidated_without_packet_access",
        },
    )


def _clinical_columns(metadata: CohortMetadata, route: str) -> tuple[str, ...]:
    selected = {_IDENTITY_COLUMN, *_BULK_CLINICAL_COLUMNS}
    if str(metadata.cohort_id).casefold() == "gse176307":
        selected.add("sample_id")
    if route == "outcomes":
        for family in metadata.endpoint_families:
            selected.update(_OUTCOME_COLUMNS[family])
        if metadata.cancer == "multi":
            selected.add("cancer")
    return tuple(sorted(selected))


def _read_named_clinical_columns(path: Path, requested: Sequence[str], metadata):
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t")
        header = next(reader, None)
        if not header or len(set(header)) != len(header) or _IDENTITY_COLUMN not in header:
            raise ValueError("clinical table has an invalid named-column header")
        selected = tuple(name for name in header if name in requested)
        if _IDENTITY_COLUMN not in selected:
            raise ValueError("clinical table is missing patient identity")
        indexes = {name: header.index(name) for name in selected}
        rows = []
        for raw in reader:
            if len(raw) != len(header):
                raise ValueError("clinical table row width differs from its header")
            item = {name: raw[indexes[name]] for name in selected}
            patient_id = item[_IDENTITY_COLUMN]
            drug_field = next((name for name in ("drug_class", "treatment_class") if name in item), None)
            raw_drug = item.get(drug_field, "") if drug_field else ""
            uniform = metadata.uniform_drug_class
            try:
                drug_class = normalise_drug_class(raw_drug)
            except ValueError:
                if raw_drug.strip().upper() not in {"", "UNKNOWN", "ICI"} or uniform is None:
                    raise ValueError("clinical table contains an unmapped drug class") from None
                drug_class = uniform
            if uniform is not None and drug_class != uniform:
                raise ValueError("clinical drug class contradicts signed uniform cohort metadata")
            projected = {_IDENTITY_COLUMN: patient_id, "drug_class_normalised": drug_class}
            for name in _BULK_CLINICAL_COLUMNS:
                if name in item and name not in {"drug_class", "treatment_class"}:
                    projected[name] = item[name]
            if "biopsy_site" not in projected and "biopsy" in projected:
                projected["biopsy_site"] = projected.pop("biopsy")
            if metadata.cancer == "multi" and "cancer" in item:
                projected["cancer_normalised"] = _normalise_cancer_row(item["cancer"])
            for name in requested:
                if name in item and name not in _BULK_CLINICAL_COLUMNS and name != _IDENTITY_COLUMN:
                    projected[name] = item[name]
            rows.append(projected)
    return rows, selected


def _expression_sample_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        header = next(csv.reader(stream, delimiter="\t"), None)
    if not header or len(header) < 2 or not header[0]:
        raise ValueError("expression matrix has no sample columns")
    samples = header[1:]
    if any(not sample for sample in samples) or len(samples) != len(set(samples)):
        raise ValueError("expression sample identities are empty or duplicated")
    return samples


def _synthetic_metadata(cohort_id: str, raw: Any) -> CohortMetadata:
    if not isinstance(raw, dict):
        raise ValueError("synthetic cohort metadata is missing")
    representation = raw.get("representation")
    if not isinstance(representation, dict):
        raise ValueError("synthetic measurement representation is missing")
    endpoint_families = raw.get("endpoint_families")
    if (
        not isinstance(endpoint_families, list)
        or not endpoint_families
        or len(set(endpoint_families)) != len(endpoint_families)
        or not set(endpoint_families).issubset(_ENDPOINT_FAMILIES)
    ):
        raise ValueError("synthetic endpoint family declaration is invalid")
    cancer = str(raw.get("cancer", ""))
    platform = str(representation.get("platform", ""))
    unit = str(representation.get("unit", ""))
    transform = str(representation.get("transform", ""))
    feature_id = str(representation.get("feature_id", ""))
    uniform_drug_class = raw.get("uniform_drug_class")
    allowed = {
        "cancer": {"melanoma", "lung", "kidney", "bladder", "gastric", "liver", "head_and_neck", "multi"},
        "platform": {"rnaseq", "microarray", "nanostring", "targeted_rna"},
        "unit": {"counts", "tpm", "fpkm", "rpkm", "probe_intensity", "normalised_counts", "cpm"},
        "transform": {"linear", "log2", "log2p1", "other"},
        "feature_id": {"symbol", "ensembl", "entrez", "probe"},
        "drug_class": {None, "ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4", "OTHER_EXCLUDED"},
    }
    if cancer not in allowed["cancer"] or any(
        value not in allowed[key]
        for key, value in (("platform", platform), ("unit", unit), ("transform", transform), ("feature_id", feature_id))
    ) or uniform_drug_class not in allowed["drug_class"]:
        raise ValueError("synthetic cohort metadata contains an uncontrolled value")
    expected_engine = "deseq2" if unit == "counts" else "limma"
    if raw.get("de_engine") != expected_engine or (expected_engine == "deseq2" and transform != "linear"):
        raise ValueError("synthetic DE engine does not match its representation")
    return CohortMetadata(
        cohort_id=cohort_id,
        cancer=cancer,
        representation=MeasurementRepresentation(
            platform=platform, unit=unit, transform=transform, feature_id=feature_id,
        ),
        de_engine=expected_engine,
        endpoint_families=tuple(endpoint_families),
        uniform_drug_class=uniform_drug_class,
    )


def _validate_synthetic_input_manifest(manifest: Any, cohort_id: str) -> None:
    if (
        not isinstance(manifest, dict)
        or manifest.get("manifest_version") != 1
        or manifest.get("producer") != _SYNTHETIC_PRODUCER
        or manifest.get("kind") != _SYNTHETIC_MANIFEST_KIND
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("invented_source") != "All rows and expression values were invented for software tests."
        or manifest.get("cohort_id") != cohort_id
    ):
        raise ValueError("synthetic input requires matching invented provenance")
    if not isinstance(manifest.get("outputs_sha256"), dict):
        raise ValueError("synthetic input manifest has no output hashes")


def _manifest_identity_values(manifest: dict[str, Any]) -> tuple[str, ...]:
    fields = (
        "cohort", "cohort_id", "dataset", "dataset_id", "source_cohort",
        "source_cohort_id", "source_dataset", "source_dataset_id", "study_id",
    )
    return tuple(str(manifest.get(name, "")) for name in fields if manifest.get(name))


def _source_inventory_from_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("source_inputs_sha256", manifest.get("input_files", {}))
    if not isinstance(raw, dict):
        raise ValueError("simple materialization source inventory is malformed")
    inventory = {}
    for name, value in raw.items():
        key = str(name).replace("\\", "/")
        candidate = Path(key)
        windows_candidate = PureWindowsPath(key)
        digest = value.get("sha256") if isinstance(value, dict) else value
        if (
            not key or candidate.is_absolute() or windows_candidate.is_absolute()
            or bool(windows_candidate.drive) or ".." in candidate.parts
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError("simple materialization source inventory has an unsafe path or hash")
        inventory[key] = digest
    return dict(sorted(inventory.items()))


def _reject_known_real_identifiers(values: Sequence[str]) -> None:
    known = {"".join(char for char in value.casefold() if char.isalnum()) for value in known_cohort_ids()}
    for value in values:
        token = "".join(char for char in str(value).casefold() if char.isalnum())
        if is_locked_study(value) or any(identifier and identifier in token for identifier in known):
            raise ValueError("known cohort identifiers are not synthetic")


def _reject_manifest_real_identifiers(manifest: dict[str, Any]) -> None:
    _reject_known_real_identifiers(_manifest_identity_values(manifest))
    cohort_ids = manifest.get("cohort_ids", ())
    if isinstance(cohort_ids, list):
        _reject_known_real_identifiers(tuple(str(value) for value in cohort_ids))


def _read_json(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("cohort materialization manifest is unavailable or malformed") from error
    if not isinstance(value, dict):
        raise ValueError("cohort materialization manifest must be a JSON object")
    return value


def _runtime_root(runtime: Path | str | None) -> Path:
    if runtime is not None:
        return Path(runtime).expanduser()
    return Path(os.environ.get("THESIS_RUNTIME", cohort_core.RUNTIME)).expanduser()


def _require_safe_path(root: Path, path: Path) -> None:
    validate_contained_path(root, path, label="Cohort materialization", must_exist=True)


def _sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    route: str,
    *,
    cohorts: Sequence[str],
    runtime: Path | str | None = None,
    results: Path | str | None = None,
    synthetic_manifests: Sequence[Path | str] = (),
    allow_outcomes: bool = False,
    adjusted: bool = False,
    packet_free_assay_mapping: Path | str | None = None,
    packet_free_assay_mapping_sha256: str | None = None,
    meta_ranking_contract: MetaRankingContract | None = None,
    retention_dir: Path | str | None = None,
    runner=None,
) -> dict[str, Any]:
    """Run one A-BIO route over the selected cohorts.

    The route implementations are kept behind this public entry point so the
    CLI and tests exercise the same preflight and provenance boundary.
    """
    if adjusted:
        raise AdjustedAnalysisUnavailable(
            "Adjusted models are unavailable: clinical adjustment sets and missingness rules are not frozen"
        )
    for value, label in (
        (runtime, "Cohort runtime"),
        (results, "A-BIO results"),
        (retention_dir, "A-BIO private work"),
        (packet_free_assay_mapping, "Packet-free assay mapping"),
    ):
        if value is not None:
            reject_symlink_components(value, label=label)
    for manifest in synthetic_manifests:
        reject_symlink_components(manifest, label="Synthetic provenance")
    if retention_dir is not None:
        preflight_tree(retention_dir, label="A-BIO private work")
    if route not in {"outcome-free", "outcomes"}:
        raise ValueError("A-BIO route must be outcome-free or outcomes")
    if not cohorts or any(not str(cohort).strip() for cohort in cohorts):
        raise ValueError("At least one cohort identifier is required")
    if route == "outcome-free" and allow_outcomes:
        raise ValueError("The outcome-free route does not accept outcome release")
    if meta_ranking_contract is not None and not isinstance(meta_ranking_contract, MetaRankingContract):
        raise ValueError("A-BIO post-meta enrichment needs an explicit MetaRankingContract")
    if route == "outcome-free" and meta_ranking_contract is not None:
        raise ValueError("Meta-ranking contracts apply only to the outcomes route")
    if (packet_free_assay_mapping is None) != (packet_free_assay_mapping_sha256 is None):
        raise ValueError("Packet-free assay mapping and its expected hash must be supplied together")

    cohort_ids = tuple(str(cohort).strip() for cohort in cohorts)
    if len(set(cohort_ids)) != len(cohort_ids):
        raise ValueError("Cohort identifiers must be unique")
    for cohort in cohort_ids:
        validate_single_component(cohort, label="Cohort identifier")
        validate_dataset_identifiers(cohort)

    result_base = _results_root(results)
    preflight_tree(result_base / "A" / "a_bio" / route, label="A-BIO result")

    if synthetic_manifests:
        _reject_known_real_identifiers(cohort_ids)
    synthetic_index = _synthetic_manifest_index(synthetic_manifests, cohort_ids, runtime)
    real_cohorts = set(cohort_ids) - set(synthetic_index)
    if route == "outcomes" and real_cohorts and not allow_outcomes:
        raise OutcomeGuardError(
            "Real outcome routes require an explicit release; no cohort or clinical input was read"
        )
    if route == "outcomes" and real_cohorts and synthetic_index:
        raise ValueError("A-BIO synthesis cannot mix real and invented cohorts")

    loaded: dict[str, LoadedCohort] = {}
    load_failures: dict[str, str] = {}
    for cohort in cohort_ids:
        try:
            loaded[cohort] = load_cohort_materialization(
                cohort,
                runtime=runtime,
                route=route,
                synthetic_manifest=synthetic_index.get(cohort),
                allow_outcomes=allow_outcomes,
            )
        except (OSError, ValueError, RuntimeError) as error:
            load_failures[cohort] = _safe_error_code(error)

    return _run_outcome_free(
        cohort_ids, loaded, load_failures, results=result_base,
        runtime=runtime,
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
        retention_dir=retention_dir,
        runner=runner,
    ) if route == "outcome-free" else _run_outcomes(
        cohort_ids, loaded, load_failures,
        runtime=runtime,
        results=result_base,
        allow_outcomes=allow_outcomes,
        packet_free_assay_mapping=packet_free_assay_mapping,
        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
        meta_ranking_contract=meta_ranking_contract,
        retention_dir=retention_dir,
        runner=runner,
    )


def _synthetic_manifest_index(
    paths: Sequence[Path | str],
    cohort_ids: Sequence[str],
    runtime: Path | str | None,
) -> dict[str, Path]:
    runtime_path = absolute_path(_runtime_root(runtime), label="Cohort runtime")
    expected_paths = {
        Path(os.path.abspath(runtime_path / cohort_id / "simple" / "manifest.json")): cohort_id
        for cohort_id in cohort_ids
    }
    result = {}
    for value in paths:
        path = Path(value).expanduser()
        cohort_id = expected_paths.get(Path(os.path.abspath(path)))
        if cohort_id is None:
            raise ValueError("synthetic manifest is outside the expected cohort path")
        if cohort_id in result:
            raise ValueError("duplicate synthetic cohort manifest")
        result[cohort_id] = validate_contained_path(
            runtime_path, path, label="Synthetic manifest", must_exist=True,
        )
    return result


def _retention_root(run_root: Path, retention_dir: Path | str | None) -> Path:
    """Choose a private sibling workspace excluded from the public run tree."""
    selected = (
        Path(retention_dir).expanduser()
        if retention_dir is not None
        else run_root.with_name(f".{run_root.name}.work")
    )
    private_work = absolute_path(selected, label="A-BIO private work")
    public_root = absolute_path(run_root, label="A-BIO run result")
    if (
        private_work == public_root
        or private_work.is_relative_to(public_root)
        or public_root.is_relative_to(private_work)
    ):
        raise ValueError("A-BIO private work must be separate from the public run tree")
    return preflight_tree(private_work, label="A-BIO private work")


def _run_outcome_free(
    cohort_ids, loaded, load_failures, *, results, runtime,
    packet_free_assay_mapping, packet_free_assay_mapping_sha256, retention_dir, runner,
):
    from tools.a_bulk.core import BulkDataset, analyse as analyse_bulk
    from tools.a_meta.features import (
        AVAILABLE_PANEL_IDS,
        _panel_definitions,
        build_feature_table,
        write_symbol_expression_projection,
    )

    result_base = _results_root(results)
    code_hashes = _code_hashes()
    input_records = _input_records(cohort_ids, loaded, load_failures)
    input_records["analysis_contracts"] = {
        "packet_free_assay_mapping_sha256": packet_free_assay_mapping_sha256 or "",
        "mapping_reference_inputs": _mapping_reference_inputs(runtime),
    }
    run_id = _run_id("outcome-free", cohort_ids, input_records, code_hashes)
    run_root = result_base / "A" / "a_bio" / "outcome-free" / run_id
    existing = _preflight_existing_run(
        result_base, run_root, "outcome-free", run_id, input_records, code_hashes,
    )
    if existing is not None:
        return existing
    preflight_tree(run_root, label="A-BIO run result")
    private_work = _retention_root(run_root, retention_dir)
    cohort_results = []

    for cohort_id in cohort_ids:
        view = loaded.get(cohort_id)
        if view is None:
            cohort_results.append({
                "cohort_id": cohort_id,
                "status": "unavailable",
                "reason": load_failures.get(cohort_id, "materialization_unavailable"),
                "checks": _unchecked_materialization_checks(),
                "completed_stages": [],
                "clinical_columns_read": [],
            })
            continue

        cohort_root = run_root / "cohorts" / cohort_id
        projected_clinical = _write_projected_clinical(view, cohort_root / "bulk-input/clinical.tsv")
        dataset = BulkDataset(
            paper="A",
            dataset_id=cohort_id,
            metadata=view.metadata,
            expression_path=view.expression_path,
            clinical_rows=view.clinical_rows,
            clinical_path=projected_clinical,
            sample_id_field="patient_id",
            data_classification=view.data_classification,
        )
        stage_summaries = {}
        stage_status = {}
        failed_stage = ""
        for stage in ("qc", "pca"):
            try:
                stage_summaries[stage] = analyse_bulk(
                    dataset,
                    stage,
                    paper="A",
                    results=run_root / "bulk",
                    allow_outcomes=False,
                    runner=runner,
                    retention_dir=private_work,
                )
                stage_status[stage] = {"status": "complete", "reason": ""}
            except (OSError, ValueError, RuntimeError) as error:
                failed_stage = stage
                stage_status[stage] = {"status": "failed", "reason": _safe_error_code(error)}
                break
        panel_mapping = {}
        if not failed_stage:
            try:
                targeted_platform = str(view.metadata.representation.platform).casefold() in {
                    "targeted_rna", "nanostring",
                }
                panel_definitions = _panel_definitions(AVAILABLE_PANEL_IDS)
                if targeted_platform:
                    panel_table = build_feature_table(
                        view,
                        "panel",
                        runtime=runtime,
                        panels=panel_definitions,
                        packet_free_assay_mapping=packet_free_assay_mapping,
                        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
                        retention_dir=private_work,
                    )
                    mapping_metadata = panel_table.metadata.get("identifier_mapping", {})
                    mapping_content = panel_table
                else:
                    gene_table = build_feature_table(
                        view,
                        "gene",
                        runtime=runtime,
                        packet_free_assay_mapping=packet_free_assay_mapping,
                        packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
                        retention_dir=private_work,
                    )
                    expression_projection = cohort_root / "panel-input/expression.tsv"
                    panel_mapping = write_symbol_expression_projection(
                        gene_table,
                        expression_projection,
                        [str(row["patient_id"]) for row in view.clinical_rows],
                    )
                    mapping_metadata = gene_table.metadata.get("identifier_mapping", {})
                    mapping_content = gene_table
                _write_tsv(
                    cohort_root / "panel-input/symbol_mapping.tsv",
                    [
                        {
                            "symbol": symbol,
                            "source_feature_id": details.get("source_feature_id", ""),
                            "mapping_status": details.get("status", "unmapped"),
                            "mapping_method": details.get("method", ""),
                        }
                        for symbol, details in sorted(
                            mapping_metadata.get("source_mapping_by_symbol", {}).items()
                        )
                    ],
                    ("symbol", "source_feature_id", "mapping_status", "mapping_method"),
                )
                panel_mapping.update({
                    "identifier_mapping_rule": mapping_metadata.get("rule", ""),
                    "alias_table_sha256": mapping_metadata.get("alias_table_sha256", ""),
                    "gene_alias_addendum_sha256": mapping_metadata.get("gene_alias_addendum_sha256", ""),
                    "pinned_gene_info_sha256": mapping_content.metadata.get("pinned_gene_info_sha256", ""),
                    "symbol_mapping_sha256": _sha256_file(cohort_root / "panel-input/symbol_mapping.tsv"),
                    "source_inputs_sha256": mapping_content.metadata.get("source_inputs_sha256", {}),
                })
                if targeted_platform:
                    methods = panel_table.metadata.get("method_id_by_unit", {})
                    panel_mapping["panel_availability"] = [
                        {
                            "panel_id": panel_id,
                            "method_id": methods.get(panel_id, f"CUSTOM_MEAN_{panel_id}"),
                            "status": "available" if panel_table.coverage[panel_id]["complete"] else "unavailable",
                            "reason": "" if panel_table.coverage[panel_id]["complete"] else "strict_main_coverage_incomplete",
                            "n_found": panel_table.coverage[panel_id]["n_found"],
                            "n_total": panel_table.coverage[panel_id]["n_total"],
                        }
                        for panel_id in AVAILABLE_PANEL_IDS
                    ]
                    panel_metadata = view.metadata
                    panel_expression = view.expression_path
                else:
                    panel_metadata = replace(
                        view.metadata,
                        representation=replace(
                            view.metadata.representation,
                            unit=("normalised_counts" if view.metadata.representation.unit == "counts"
                                  else view.metadata.representation.unit),
                            transform="log2",
                            feature_id="symbol",
                        ),
                        de_engine="limma",
                    )
                    panel_expression = expression_projection
                panel_dataset = BulkDataset(
                    paper="A",
                    dataset_id=cohort_id,
                    metadata=panel_metadata,
                    expression_path=panel_expression,
                    clinical_rows=view.clinical_rows,
                    clinical_path=projected_clinical,
                    sample_id_field="patient_id",
                    data_classification=view.data_classification,
                    panel_definitions=panel_definitions,
                )
                stage_summaries["panels"] = analyse_bulk(
                    panel_dataset,
                    "panels",
                    paper="A",
                    results=run_root / "bulk",
                    allow_outcomes=False,
                    runner=runner,
                    retention_dir=private_work,
                    panel_features=panel_table if targeted_platform else None,
                )
                stage_status["panels"] = {"status": "complete", "reason": ""}
            except (OSError, ValueError, RuntimeError) as error:
                stage_status["panels"] = {"status": "unavailable", "reason": _safe_error_code(error)}
                failed_stage = "panels"
        else:
            stage_status["panels"] = {
                "status": "unavailable",
                "reason": "dependency_not_attempted",
            }
        cohort_results.append({
            "cohort_id": cohort_id,
            "status": "partial" if failed_stage else "complete",
            "reason": f"bulk_stage_unavailable:{failed_stage}" if failed_stage else "",
            "patient_count": len(view.clinical_rows),
            "clinical_columns_read": list(view.clinical_columns_read),
            "checks": view.checks,
            "completed_stages": sorted(stage_summaries),
            "stage_summaries": stage_summaries,
            "stage_status": stage_status,
            "panel_mapping": panel_mapping,
        })

    summary = {
        "schema_version": 1,
        "route": "outcome-free",
        "run_id": run_id,
        "status": "complete" if all(row["status"] == "complete" for row in cohort_results) else "partial",
        "outcome_payload_access": "none",
        "cohorts": cohort_results,
        "limitation": "This route reports cohort QC, PCA, and within-study panel correlations only.",
    }
    _write_json(run_root / "summary.json", summary)
    manifest = {
        "schema_version": 1,
        "route": "outcome-free",
        "run_id": run_id,
        "data_classification": _classification_summary(loaded),
        "outcome_payload_access": "none",
        "input_sha256": input_records,
        "source_inputs_sha256": {
            cohort: dict(view.source_inputs_sha256) for cohort, view in sorted(loaded.items())
        },
        "code_sha256": code_hashes,
        "cohorts": [
            {
                key: row[key] for key in (
                    "cohort_id", "status", "reason", "clinical_columns_read", "checks",
                    "completed_stages", "patient_count", "stage_status", "panel_mapping",
                ) if key in row
            }
            for row in cohort_results
        ],
        "output_sha256": _collect_output_hashes(run_root, exclude={"manifest.json"}),
        "fraction_family": "unavailable pending the signed quanTIseq pin (N15)",
        "cibersortx": "not run",
    }
    _write_json(run_root / "manifest.json", manifest)
    return summary


def _run_post_meta_fgsea(
    loaded,
    effects,
    synthesis_summaries,
    mapping_by_unit,
    *,
    contract,
    results,
    retention_dir,
    runner,
):
    from tools.a_bulk.core import BulkDataset
    from tools.a_meta.endpoint_definitions import endpoint_is_per_study_only

    output_rows = []
    endpoint_definitions = sorted({
        (str(row.get("endpoint_family", "")), str(row.get("endpoint_definition_id", "")))
        for row in effects
        if row.get("endpoint_family") and row.get("endpoint_definition_id")
    })
    base_view = next(iter(loaded.values()), None)

    for stratum in SYNTHESIS_STRATA:
        summaries = synthesis_summaries.get(stratum, [])
        for endpoint, definition_id in endpoint_definitions:
            reason = ""
            if endpoint_is_per_study_only(definition_id, endpoint):
                contexts = [(None, [])]
                skip_reason = "source_binary_per_study_only"
                status = "not_applicable"
            else:
                candidate = [
                    dict(row) for row in summaries
                    if str(row.get("unit_family", "")) == "gene"
                    and str(row.get("endpoint_family", "")) == endpoint
                    and str(row.get("endpoint_definition_id", "")) == definition_id
                ]
                context_fields = ("stratum_type", "stratum", "cancer", "drug_class_stratum", "stage")
                context_keys = set()
                for row in candidate:
                    context_ok = (
                        stratum == "across_cancers"
                        and row.get("stage") == "stage2_across_cancers"
                    ) or (
                        stratum == "per_cancer"
                        and row.get("stratum_type") == "cancer"
                        and row.get("stage") == "within_cancer"
                    ) or (
                        stratum == "per_drug_class"
                        and row.get("stratum_type") == "drug_class"
                        and row.get("stage") == "per_drug_class"
                    ) or (
                        stratum == "melanoma_cancer_drug"
                        and row.get("stratum_type") == "cancer_drug"
                        and row.get("stage") == "melanoma_cancer_drug"
                    )
                    if context_ok:
                        context_keys.add(tuple(str(row.get(field, "")) for field in context_fields))
                context_keys = sorted(context_keys)
                if context_keys:
                    contexts = [
                        (key, [row for row in candidate
                               if tuple(str(row.get(field, "")) for field in context_fields) == key])
                        for key in context_keys
                    ]
                else:
                    contexts = [(None, candidate)]
                skip_reason = ""
                status = ""

            for context, scoped in contexts:
                if context is None:
                    context_id = "all"
                else:
                    context_id = "_".join(
                        re.sub(r"[^A-Za-z0-9_.-]+", "_", value) or "empty"
                        for value in context
                    )
                stage_result = None
                if not skip_reason and base_view is not None:
                    dataset = BulkDataset(
                        paper="A",
                        dataset_id=str(base_view.metadata.cohort_id),
                        metadata=base_view.metadata,
                        expression_path=base_view.expression_path,
                        clinical_rows=base_view.clinical_rows,
                        clinical_path=base_view.clinical_path,
                        sample_id_field="patient_id",
                        data_classification=base_view.data_classification,
                    )
                    result_root = (
                        Path(results) / stratum / endpoint / definition_id / context_id
                    )
                    try:
                        stage_result = run_meta_fgsea(
                            dataset,
                            scoped,
                            mapping_by_unit,
                            endpoint_family=endpoint,
                            endpoint_definition_id=definition_id,
                            stratum=stratum,
                            context_id=context_id,
                            contract=contract,
                            results=result_root,
                            retention_dir=retention_dir,
                            runner=runner,
                        )
                    except (OSError, ValueError, RuntimeError) as error:
                        stage_result = {
                            "status": "failed",
                            "reason": _safe_error_code(error),
                        }
                elif not skip_reason:
                    stage_result = {
                        "status": "unavailable", "reason": "no_validated_cohorts",
                    }

                if skip_reason:
                    current_status, reason = status, skip_reason
                    ranked_count = ""
                    contract_id = ""
                    collections = ("hallmark", "reactome")
                else:
                    current_status = str(stage_result.get("status", "unavailable"))
                    reason = str(stage_result.get("reason", ""))
                    ranked_count = stage_result.get("ranked_gene_count", "")
                    contract_id = contract.contract_id if contract is not None else ""
                    collections = tuple(stage_result.get("collections", ())) or ("hallmark", "reactome")

                for collection in collections:
                    collection_result = (
                        stage_result.get("collections", {}).get(collection, {})
                        if isinstance(stage_result, dict) else {}
                    )
                    collection_status = str(collection_result.get("status", current_status))
                    collection_reason = reason
                    if current_status == "complete" and collection_status == "complete":
                        collection_reason = ""
                    output_rows.append({
                        "cohort_id": "meta",
                        "endpoint_family": endpoint,
                        "endpoint_definition_id": definition_id,
                        "stratum": f"{stratum}:{context_id}",
                        "stage": "meta_fgsea",
                        "collection": collection,
                        "status": collection_status,
                        "reason": collection_reason,
                        "sample_count": "",
                        "input_sample_count": "",
                        "excluded_treatment_count": "",
                        "analysis_sample_count": "",
                        "response_exclusion_counts": "{}",
                        "ranking_contract_id": contract_id,
                        "ranked_gene_count": ranked_count,
                    })
    return output_rows


def _summarize_meta_fgsea_status(rows):
    if not rows:
        return {"status": "unavailable", "reason": "no_eligible_endpoint_definitions"}
    statuses = {str(row.get("status", "unavailable")) for row in rows}
    reasons = sorted({str(row.get("reason", "")) for row in rows if row.get("reason")})
    if statuses == {"complete", "not_applicable"} or statuses == {"complete"}:
        status = "complete"
    elif statuses == {"not_applicable"}:
        status = "not_applicable"
    else:
        status = "partial" if "complete" in statuses else "unavailable"
    return {"status": status, "reasons": reasons, "stage_rows": len(rows)}


def _family_unavailable_reason(view, family: str, targeted_studies: set[str]) -> str:
    platform = str(view.metadata.representation.platform).casefold()
    targeted = platform in {"targeted_rna", "nanostring"}
    if family == "gene" and targeted:
        return "targeted_platform_excluded_from_gene_family"
    if family in {"pathway", "pathway_coverage90", "pathway_common"} and targeted:
        return "targeted_platform_excluded_from_pathway_families"
    if family == "targeted_subset":
        if not targeted:
            return "non_targeted_platform"
        if str(view.metadata.cohort_id) not in targeted_studies:
            return "cohort_not_in_signed_targeted_subset"
    return ""


def _feature_bundle_manifest(view, tables, output_hashes, effect_hashes, *, classification):
    from tools.a_meta.provenance import SYNTHETIC_FIXTURE_PRODUCER

    manifest = {
        "data_classification": classification,
        "cohort": str(view.metadata.cohort_id),
        "cohort_ids": [str(view.metadata.cohort_id)],
        "outputs_sha256": output_hashes,
        "effect_input_sha256": effect_hashes,
        "feature_metadata": {
            family: _feature_metadata_summary(table.metadata)
            for family, table in tables.items()
        },
        "patient_identifier_policy": "zero-based row index only in feature tables",
    }
    if classification == "synthetic":
        manifest.update({
            "producer": SYNTHETIC_FIXTURE_PRODUCER,
            "manifest_version": 1,
            "kind": "feature_bundle",
        })
    return manifest


def _feature_metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    retained = (
        "score_rule", "source_scale_rule", "coverage_policy", "sensitivity_label",
        "source_gene_sets_sha256", "source_gene_sets_collection",
        "common_gene_table_sha256", "method_id_by_unit", "custom_method_ids",
        "m5m6_gene_units", "claim_scope", "scale_rule", "alias_table_sha256",
    )
    summary = {key: metadata[key] for key in retained if key in metadata}
    mapping = metadata.get("identifier_mapping")
    if isinstance(mapping, dict):
        statuses = mapping.get("mapping_status_by_symbol", {})
        methods = mapping.get("mapping_method_by_symbol", {})
        summary["identifier_mapping"] = {
            "source_identifier_type": mapping.get("source_identifier_type", ""),
            "rule": mapping.get("rule", ""),
            "mapping_status_counts": _value_counts(statuses.values()),
            "mapping_method_counts": _value_counts(methods.values()),
            "unmapped_or_ambiguous_source_row_count": len(
                mapping.get("unmapped_or_ambiguous_source_rows", ())
            ),
            "alias_table_sha256": mapping.get("alias_table_sha256", ""),
            "gene_alias_addendum_sha256": mapping.get("gene_alias_addendum_sha256", ""),
            "pinned_gene_info_sha256": metadata.get("pinned_gene_info_sha256", ""),
            "source_inputs_sha256": metadata.get("source_inputs_sha256", {}),
        }
    return summary


def _value_counts(values):
    counts = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _effect_manifest(path: Path, rows, cohort_ids: Sequence[str], classification: str) -> dict[str, Any]:
    from tools.a_meta.provenance import (
        SYNTHETIC_FIXTURE_PRODUCER,
        canonical_sha256,
        effect_rows_payload,
    )

    output_hashes = {path.name: _sha256_file(path)}
    manifest = {
        "data_classification": classification,
        "cohort_ids": sorted(set(cohort_ids)),
        "outputs_sha256": output_hashes,
        "effect_rows_sha256": canonical_sha256(effect_rows_payload(rows)),
        "adjustment": "unadjusted only",
    }
    if len(set(cohort_ids)) == 1:
        manifest["cohort"] = next(iter(set(cohort_ids)))
    if classification == "synthetic":
        manifest.update({
            "producer": SYNTHETIC_FIXTURE_PRODUCER,
            "manifest_version": 1,
            "kind": "effect_table",
        })
    return manifest


def _write_projected_clinical(view: LoadedCohort, path: Path) -> Path:
    columns = [_IDENTITY_COLUMN]
    columns.extend(sorted({key for row in view.clinical_rows for key in row if key != _IDENTITY_COLUMN}))
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=columns, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(view.clinical_rows)
        content = stream.getvalue().encode("utf-8")
    return write_immutable_bytes(path.parent, path, content, label="projected clinical input")


def _input_records(cohort_ids, loaded, failures):
    records = {}
    for cohort_id in cohort_ids:
        view = loaded.get(cohort_id)
        if view is None:
            records[cohort_id] = {
                "status": "unavailable",
                "reason": failures.get(cohort_id, "materialization_unavailable"),
            }
        else:
            records[cohort_id] = {
                "status": "available",
                "data_classification": view.data_classification,
                "materialization_manifest": view.manifest_sha256,
                "outputs_sha256": dict(view.output_sha256),
                "source_inputs_sha256": dict(view.source_inputs_sha256),
                "clinical_columns_read": list(view.clinical_columns_read),
            }
    return records


def _mapping_reference_inputs(runtime) -> dict[str, dict[str, str]]:
    from tools.a_scoring.core import GENE_INFO_SHA256, gene_info_path

    runtime_root = absolute_path(_runtime_root(runtime), label="Cohort runtime")
    path = validate_contained_path(
        runtime_root,
        gene_info_path(runtime_root),
        label="Pinned mapping reference",
        must_exist=False,
    )
    observed = _sha256_file(path) if path.is_file() else ""
    return {
        "ncbi_gene_info": {
            "expected_sha256": GENE_INFO_SHA256,
            "observed_sha256": observed,
        },
    }


def _run_id(route: str, cohort_ids: Sequence[str], inputs: dict[str, Any], code_hashes: dict[str, str]) -> str:
    payload = json.dumps(
        {"route": route, "cohorts": list(cohort_ids), "inputs": inputs, "code": code_hashes},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _results_root(results: Path | str | None) -> Path:
    selected = results or os.environ.get("THESIS_RESULTS") or (cohort_core.ROOT.parent / "results")
    return absolute_path(selected, label="A-BIO results")


def _preflight_existing_run(result_base, run_root, route, run_id, input_records, code_hashes):
    target = validate_contained_path(
        result_base, run_root, label="A-BIO run result", must_exist=False,
    )
    if not target.exists():
        return None
    if not target.is_dir():
        raise FileExistsError("A-BIO result destination is not a directory")
    entries = list(target.iterdir())
    if not entries:
        return None
    manifest_path = target / "manifest.json"
    summary_path = target / "summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        raise FileExistsError("Refusing to reuse or overwrite an incomplete A-BIO result")
    manifest = _read_json(manifest_path)
    if (
        manifest.get("route") != route
        or manifest.get("run_id") != run_id
        or manifest.get("input_sha256") != input_records
        or manifest.get("code_sha256") != code_hashes
    ):
        raise FileExistsError("Existing A-BIO result identity differs")
    outputs = _collect_output_hashes(target, exclude={"manifest.json"})
    if outputs != manifest.get("output_sha256"):
        raise FileExistsError("Existing A-BIO result output hashes differ")
    summary = _read_json(summary_path)
    if summary.get("route") != route or summary.get("run_id") != run_id:
        raise FileExistsError("Existing A-BIO summary identity differs")
    return summary


def _code_hashes() -> dict[str, str]:
    root = cohort_core.ROOT
    candidates = (
        "tools/a_bio/__init__.py", "tools/a_bio/runner.py", "tools/a_bio/__main__.py",
        "tools/a_bio/enrichment.py", "tools/a_bio/paths.py",
        "tools/a_bulk/core.py", "tools/a_cohorts/view.py", "tools/a_cohorts/core.py",
        "tools/a_meta/features.py", "tools/a_meta/effects.py", "tools/a_meta/synthesis.py",
        "tools/a_meta/provenance.py", "tools/a_meta/frozen.py", "tools/a_meta/endpoint_definitions.py",
        "tools/a_meta/random_streams.py", "tools/a_meta/r_manifest.py", "tools/a_scoring/core.py",
        "tools/a_p2/build.py", "tools/r_bridge/__init__.py",
        "r/scripts/bulk_qc_pca.R", "r/scripts/de_limma.R",
        "r/scripts/de_deseq2.R", "r/scripts/fgsea_rank.R", "r/scripts/singscore.R",
        "r/scripts/meta_rma.R", "r/scripts/random_streams.R", "r/renv.lock",
        "docs/cohorts/REGISTRY.tsv", "docs/cohorts/REPRESENTATION.tsv",
        "docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv",
        "docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv",
        "specs/A/NUMERICAL_FREEZE_REGISTER.tsv",
        "specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv",
        "specs/amendments/2026-11-04-numerical-freeze/hallmark_2026.1.Hs.gmt",
        "specs/amendments/2026-11-04-numerical-freeze/reactome_2026.1.Hs.gmt",
        "specs/amendments/2026-11-04-panel-coverage/gene_aliases_addendum.tsv",
        "specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json",
        "tools/a_dav/field_maps/gse176307.json",
    )
    return {
        relative: _sha256_file(root / relative)
        for relative in candidates
        if (root / relative).is_file()
    }


def _collect_output_hashes(root: Path, *, exclude: set[str]) -> dict[str, str]:
    if not root.exists():
        return {}
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("A-BIO output tree contains a symlink")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                outputs[relative] = _sha256_file(path)
    return outputs


def _classification_summary(loaded: dict[str, LoadedCohort]) -> str:
    classifications = {view.data_classification for view in loaded.values()}
    if len(classifications) == 1:
        return next(iter(classifications))
    return "mixed" if classifications else "unknown"


def _unchecked_materialization_checks() -> dict[str, str]:
    return {
        "signed_eligibility": "not_checked",
        "materialization_paths": "not_checked",
        "output_hashes": "not_checked",
        "patient_expression_alignment": "not_checked",
        "ingestion_packet": "not_opened",
        "source_input_hashes": "not_revalidated_without_packet_access",
    }


def _safe_error_code(error: BaseException) -> str:
    message = str(error).casefold()
    reason_code = getattr(error, "reason_code", "")
    if isinstance(reason_code, str) and re.fullmatch(r"[a-z0-9_]+", reason_code):
        return reason_code
    if "not attempted" in message or "dependency_not_attempted" in message:
        return "dependency_not_attempted"
    if "rank" in message and any(token in message for token in ("design", "confounded", "full rank")):
        return "rank_deficient_design"
    if any(token in message for token in ("unsupported", "representation is not", "requires a linear", "requires non-count")):
        return "unsupported_units"
    if any(token in message for token in ("mapping", "ambiguous", "unmapped", "coverage", "membership", "overlap", "missing gene")):
        return "mapping_or_coverage_unavailable"
    if any(token in message for token in ("eligible", "responder and non-responder", "r and nr")):
        return "no_eligible_patients"
    if isinstance(error, FileNotFoundError):
        return "missing_source"
    if "hash" in message:
        return "hash_validation_failed"
    if "align" in message or "identity" in message:
        return "identity_validation_failed"
    if isinstance(error, PermissionError):
        return "source_not_readable"
    return f"{type(error).__name__}".casefold()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    write_immutable_bytes(path.parent, path, rendered.encode("utf-8"), label="A-BIO output")


def _write_tsv(path: Path, rows, columns: Sequence[str]) -> None:
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
        content = stream.getvalue().encode("utf-8")
    write_immutable_bytes(path.parent, path, content, label="A-BIO output")


def _read_tsv_rows(path: Path | str) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("TSV source has no named columns")
        return [dict(row) for row in reader]


def _run_outcomes(
    cohort_ids, loaded, load_failures, *, runtime, results, allow_outcomes,
    packet_free_assay_mapping, packet_free_assay_mapping_sha256,
    meta_ranking_contract, retention_dir, runner,
):
    from tools import a_meta
    from tools.a_bulk.core import BulkDataset, analyse as analyse_bulk, endpoint_definition_views
    from tools.a_meta.effects import EFFECT_COLUMNS, study_effects
    from tools.a_meta.features import (
        TARGETED_SUBSET_STUDIES,
        build_feature_table,
        map_de_ranking_to_symbols,
        write_feature_table,
    )
    from tools.a_meta.frozen import HALLMARK_GMT, REACTOME_GMT
    from tools.a_meta.provenance import (
        SYNTHETIC_FIXTURE_PRODUCER,
        canonical_sha256,
        effect_input_payload,
        effect_rows_payload,
        write_synthetic_fixture_manifest,
    )
    from tools.a_meta.synthesis import (
        SUBGROUP_COLUMNS,
        SYNTHESIS_COLUMNS,
        synthesize,
    )

    result_base = _results_root(results)
    code_hashes = _code_hashes()
    input_records = _input_records(cohort_ids, loaded, load_failures)
    input_records["analysis_contracts"] = {
        "packet_free_assay_mapping_sha256": packet_free_assay_mapping_sha256 or "",
        "mapping_reference_inputs": _mapping_reference_inputs(runtime),
        "meta_ranking": (
            None if meta_ranking_contract is None else {
                "contract_id": meta_ranking_contract.contract_id,
                "statistic": meta_ranking_contract.statistic,
            }
        ),
    }
    run_id = _run_id("outcomes", cohort_ids, input_records, code_hashes)
    run_root = result_base / "A" / "a_bio" / "outcomes" / run_id
    existing = _preflight_existing_run(
        result_base, run_root, "outcomes", run_id, input_records, code_hashes,
    )
    if existing is not None:
        return existing
    preflight_tree(run_root, label="A-BIO run result")
    private_work = _retention_root(run_root, retention_dir)
    availability_rows = []
    coverage_rows = []
    cohort_results = []
    all_effect_rows = []
    bulk_rows = []
    synthesis_rows = []
    synthesis_metadata = {}
    synthesis_summaries = {}
    gene_mapping_by_unit = {}
    meta_fgsea_rows = []
    any_failure = False

    for cohort_id in cohort_ids:
        view = loaded.get(cohort_id)
        if view is None:
            any_failure = True
            for family in (*A_BIO_FAMILIES, "fraction"):
                availability_rows.append({
                    "cohort_id": cohort_id,
                    "unit_family": family,
                    "status": "unavailable",
                    "reason": load_failures.get(cohort_id, "materialization_unavailable"),
                    "unit_count": 0,
                    "scorable_unit_count": 0,
                })
            cohort_results.append({
                "cohort_id": cohort_id,
                "status": "unavailable",
                "reason": load_failures.get(cohort_id, "materialization_unavailable"),
                "clinical_columns_read": [],
                "checks": _unchecked_materialization_checks(),
                "completed_families": [],
            })
            continue

        cohort_root = run_root / "cohorts" / cohort_id
        feature_root = cohort_root / "features"
        effect_rows = []
        tables = {}
        family_failures = []
        for family in A_BIO_FAMILIES:
            unavailable_reason = _family_unavailable_reason(view, family, TARGETED_SUBSET_STUDIES)
            if unavailable_reason:
                availability_rows.append({
                    "cohort_id": cohort_id,
                    "unit_family": family,
                    "status": "unavailable",
                    "reason": unavailable_reason,
                    "unit_count": 0,
                    "scorable_unit_count": 0,
                })
                continue
            try:
                table = build_feature_table(
                    view,
                    family,
                    runtime=runtime,
                    r_out_dir=feature_root / f"R-singscore-{family}",
                    packet_free_assay_mapping=packet_free_assay_mapping,
                    packet_free_assay_mapping_sha256=packet_free_assay_mapping_sha256,
                    retention_dir=private_work,
                    runner=runner,
                )
                tables[family] = table
                if family == "gene":
                    mapping = table.metadata.get("identifier_mapping", {})
                    for unit, status in mapping.get("mapping_status_by_symbol", {}).items():
                        current = gene_mapping_by_unit.get(unit)
                        source_mapping = {
                            "cohort_id": cohort_id,
                            "status": status,
                            "source_feature_id": mapping.get("source_feature_by_symbol", {}).get(unit, ""),
                            "method": mapping.get("mapping_method_by_symbol", {}).get(unit, ""),
                        }
                        if current is None:
                            current = {
                                "status": status,
                                "source_mappings": [],
                            }
                            gene_mapping_by_unit[unit] = current
                        elif current["status"] != status:
                            current["status"] = "ambiguous"
                        current["source_mappings"].append(source_mapping)
                    source_mapping = mapping.get("source_mapping_by_symbol", {})
                    _write_tsv(
                        feature_root / "gene_mapping.tsv",
                        [
                            {
                                "unit": unit,
                                "source_feature_id": details.get("source_feature_id", ""),
                                "mapping_status": details.get("status", "unmapped"),
                                "mapping_method": details.get("method", ""),
                            }
                            for unit, details in sorted(source_mapping.items())
                        ],
                        ("unit", "source_feature_id", "mapping_status", "mapping_method"),
                    )
                write_feature_table(table, feature_root / f"{family}.tsv")
                for unit, details in table.coverage.items():
                    coverage_rows.append({
                        "cohort_id": cohort_id,
                        "unit_family": family,
                        "unit": unit,
                        "n_found": details.get("n_found", ""),
                        "n_total": details.get("n_total", ""),
                        "complete": str(bool(details.get("complete", False))).lower(),
                        "scorable": str(bool(details.get("scorable", details.get("complete", True)))).lower(),
                        "missing": ";".join(details.get("missing", ())),
                        "fixed_subset": ";".join(details.get("fixed_subset", ())),
                        "reason": details.get("reason", ""),
                        "sensitivity_label": details.get("sensitivity_label", table.metadata.get("sensitivity_label", "")),
                    })
                availability_rows.append({
                    "cohort_id": cohort_id,
                    "unit_family": family,
                    "status": "available",
                    "reason": "",
                    "unit_count": len(table.values_by_unit),
                    "scorable_unit_count": sum(
                        1 for details in table.coverage.values()
                        if details.get("scorable", details.get("complete", True))
                    ) if table.coverage else len(table.values_by_unit),
                })
            except (OSError, ValueError, RuntimeError) as error:
                family_failures.append(family)
                any_failure = True
                availability_rows.append({
                    "cohort_id": cohort_id,
                    "unit_family": family,
                    "status": "failed",
                    "reason": _safe_error_code(error),
                    "unit_count": 0,
                    "scorable_unit_count": 0,
                })

        availability_rows.append({
            "cohort_id": cohort_id,
            "unit_family": "fraction",
            "status": "unavailable",
            "reason": "A-COMP family is outside W2; quanTIseq pin N15 remains open",
            "unit_count": 0,
            "scorable_unit_count": 0,
        })

        feature_manifest_path = feature_root / "manifest.json"
        feature_root.mkdir(parents=True, exist_ok=True)
        feature_hashes = {
            f"{family}.tsv": _sha256_file(feature_root / f"{family}.tsv")
            for family in tables
        }
        if (feature_root / "gene_mapping.tsv").is_file():
            feature_hashes["gene_mapping.tsv"] = _sha256_file(feature_root / "gene_mapping.tsv")
        effect_hashes = {
            family: canonical_sha256(effect_input_payload(view, table))
            for family, table in tables.items()
        }
        feature_manifest = _feature_bundle_manifest(
            view,
            tables,
            feature_hashes,
            effect_hashes,
            classification=view.data_classification,
        )
        _write_json(feature_manifest_path, feature_manifest)

        module_outcomes_allowed = bool(allow_outcomes and view.data_classification == "real")
        for family, table in tables.items():
            try:
                for endpoint in view.metadata.endpoint_families:
                    effect_rows.extend(study_effects(
                        view,
                        table,
                        endpoint,
                        by_drug_class=True,
                        allow_outcomes=module_outcomes_allowed,
                        provenance_manifest=feature_manifest_path,
                    ))
            except (OSError, ValueError, RuntimeError) as error:
                family_failures.append(family)
                any_failure = True
                availability_rows.append({
                    "cohort_id": cohort_id,
                    "unit_family": family,
                    "status": "failed",
                    "reason": f"effect_estimation:{_safe_error_code(error)}",
                    "unit_count": len(table.values_by_unit),
                    "scorable_unit_count": 0,
                })

        _write_tsv(cohort_root / "effects.tsv", effect_rows, EFFECT_COLUMNS)
        per_cohort_effect_manifest = _effect_manifest(
            cohort_root / "effects.tsv", effect_rows, [cohort_id], view.data_classification
        )
        _write_json(cohort_root / "effects.manifest.json", per_cohort_effect_manifest)
        all_effect_rows.extend(effect_rows)

        endpoint_status = []
        endpoint_failures = []
        for endpoint in view.metadata.endpoint_families:
            try:
                definition_views = endpoint_definition_views(
                    view,
                    endpoint,
                    results=run_root / "bulk-projections",
                    allow_outcomes=module_outcomes_allowed,
                )
            except (OSError, ValueError, RuntimeError) as error:
                reason = _safe_error_code(error)
                endpoint_failures.append(f"{endpoint}:endpoint_view")
                any_failure = True
                for stage, collection in (("de", ""), ("fgsea", "hallmark"), ("fgsea", "reactome")):
                    bulk_rows.append({
                        "cohort_id": cohort_id, "endpoint_family": endpoint,
                        "endpoint_definition_id": "unmapped", "stratum": "per_study",
                        "stage": stage, "collection": collection,
                        "status": "failed" if stage == "de" else "unavailable",
                        "reason": reason if stage == "de" else f"dependency_not_attempted:{reason}",
                        "sample_count": "", "input_sample_count": "",
                        "excluded_treatment_count": "", "analysis_sample_count": "",
                        "response_exclusion_counts": "{}", "ranking_contract_id": "",
                        "ranked_gene_count": "",
                    })
                continue

            for endpoint_view in definition_views:
                definition_id = endpoint_view.endpoint_definition_id
                endpoint_root = (
                    run_root / "bulk-endpoints" / cohort_id / endpoint / definition_id
                )
                common_row = {
                    "cohort_id": cohort_id,
                    "endpoint_family": endpoint,
                    "endpoint_definition_id": definition_id,
                    "stratum": "per_study",
                    "input_sample_count": endpoint_view.input_sample_count,
                    "excluded_treatment_count": endpoint_view.excluded_treatment_count,
                    "analysis_sample_count": endpoint_view.analysis_sample_count,
                    "response_exclusion_counts": json.dumps(
                        dict(endpoint_view.excluded_response_counts),
                        sort_keys=True, separators=(",", ":"),
                    ),
                    "ranking_contract_id": "",
                    "ranked_gene_count": "",
                }
                if endpoint_view.unavailable_reason:
                    reason = endpoint_view.unavailable_reason
                    any_failure = True
                    endpoint_failures.append(f"{endpoint}:{definition_id}:de")
                    bulk_rows.append({
                        **common_row, "stage": "de", "collection": "",
                        "status": "unavailable", "reason": reason,
                        "sample_count": endpoint_view.analysis_sample_count,
                    })
                    for collection in ("hallmark", "reactome"):
                        bulk_rows.append({
                            **common_row, "stage": "fgsea", "collection": collection,
                            "status": "unavailable",
                            "reason": f"dependency_not_attempted:{reason}",
                            "sample_count": endpoint_view.analysis_sample_count,
                        })
                    continue

                try:
                    de_summary = analyse_bulk(
                        endpoint_view.dataset,
                        "de",
                        paper="A",
                        endpoint=endpoint,
                        results=endpoint_root / "de",
                        allow_outcomes=module_outcomes_allowed,
                        retention_dir=private_work,
                        runner=runner,
                    )
                    sample_count = de_summary.get("stages", {}).get("de", {}).get(
                        "sample_count", endpoint_view.analysis_sample_count,
                    )
                    bulk_rows.append({
                        **common_row, "stage": "de", "collection": "",
                        "status": "complete", "reason": "", "sample_count": sample_count,
                    })
                except (OSError, ValueError, RuntimeError) as error:
                    reason = _safe_error_code(error)
                    any_failure = True
                    endpoint_failures.append(f"{endpoint}:{definition_id}:de")
                    bulk_rows.append({
                        **common_row, "stage": "de", "collection": "",
                        "status": "failed", "reason": reason, "sample_count": "",
                    })
                    for collection in ("hallmark", "reactome"):
                        bulk_rows.append({
                            **common_row, "stage": "fgsea", "collection": collection,
                            "status": "unavailable",
                            "reason": f"dependency_not_attempted:{reason}",
                            "sample_count": "",
                        })
                    continue

                try:
                    from tools.a_bulk.core import output_dir as bulk_output_dir
                    de_path = bulk_output_dir(endpoint_view.dataset, endpoint_root / "de") / "de/bridge/de.tsv"
                    de_rows = _read_tsv_rows(de_path)
                    gene_table = tables.get("gene")
                    if gene_table is None:
                        raise ValueError("A-META genome-wide gene mapping is unavailable")
                    ranking, mapping_rows, mapping_counts = map_de_ranking_to_symbols(
                        de_rows,
                        gene_table.metadata.get("identifier_mapping", {}),
                    )
                    mapping_root = endpoint_root / "de-mapping"
                    _write_tsv(
                        mapping_root / "de_symbol_mapping.tsv",
                        mapping_rows,
                        ("source_feature_id", "symbol", "mapping_method", "mapping_status"),
                    )
                    ranking_path = mapping_root / "de_symbol_ranking.tsv"
                    _write_tsv(ranking_path, ranking, ("gene", "statistic"))
                    for collection, gene_sets in (("hallmark", HALLMARK_GMT), ("reactome", REACTOME_GMT)):
                        try:
                            gsea_summary = analyse_bulk(
                                endpoint_view.dataset,
                                "gsea",
                                paper="A",
                                endpoint=endpoint,
                                results=endpoint_root / "fgsea" / collection,
                                gene_sets=gene_sets,
                                gene_set_id_type="symbol",
                                ranking_path=ranking_path,
                                ranking_id_type="symbol",
                                ranking_contract_id="A_BIO_PER_STUDY_DE_STATISTIC_V1",
                                allow_outcomes=module_outcomes_allowed,
                                retention_dir=private_work,
                                runner=runner,
                            )
                            bulk_rows.append({
                                **common_row, "stage": "fgsea", "collection": collection,
                                "status": "complete", "reason": "",
                                "sample_count": sample_count,
                                "ranking_contract_id": "A_BIO_PER_STUDY_DE_STATISTIC_V1",
                                "ranked_gene_count": len(ranking),
                            })
                        except (OSError, ValueError, RuntimeError) as error:
                            reason = _safe_error_code(error)
                            any_failure = True
                            endpoint_failures.append(f"{endpoint}:{definition_id}:fgsea:{collection}")
                            bulk_rows.append({
                                **common_row, "stage": "fgsea", "collection": collection,
                                "status": "unavailable", "reason": reason,
                                "sample_count": sample_count,
                                "ranking_contract_id": "A_BIO_PER_STUDY_DE_STATISTIC_V1",
                                "ranked_gene_count": len(ranking),
                            })
                    endpoint_status.append((endpoint, definition_id))
                except (OSError, ValueError, RuntimeError) as error:
                    reason = _safe_error_code(error)
                    any_failure = True
                    endpoint_failures.append(f"{endpoint}:{definition_id}:mapping")
                    for collection in ("hallmark", "reactome"):
                        if not any(
                            row.get("endpoint_definition_id") == definition_id
                            and row.get("endpoint_family") == endpoint
                            and row.get("stage") == "fgsea"
                            and row.get("collection") == collection
                            and row.get("cohort_id") == cohort_id
                            for row in bulk_rows
                        ):
                            bulk_rows.append({
                                **common_row, "stage": "fgsea", "collection": collection,
                                "status": "unavailable",
                                "reason": f"dependency_not_attempted:{reason}",
                                "sample_count": sample_count,
                            })

        cohort_results.append({
            "cohort_id": cohort_id,
            "status": "partial" if family_failures or endpoint_failures else "complete",
            "reason": "module_stage_failed" if family_failures or endpoint_failures else "",
            "patient_count": len(view.clinical_rows),
            "clinical_columns_read": list(view.clinical_columns_read),
            "checks": view.checks,
            "completed_families": sorted(tables),
            "endpoint_families": list(view.metadata.endpoint_families),
            "completed_endpoint_definitions": [list(item) for item in endpoint_status],
            "failed_stages": sorted(endpoint_failures),
        })

    effects_path = run_root / "effects.tsv"
    _write_tsv(effects_path, all_effect_rows, EFFECT_COLUMNS)
    classifications = {view.data_classification for view in loaded.values()}
    if classifications == {"synthetic"}:
        effect_manifest_path = run_root / "effects.manifest.json"
        write_synthetic_fixture_manifest(
            effect_manifest_path,
            kind="effect_table",
            payload=effect_rows_payload(all_effect_rows),
            cohort_ids=sorted({str(row["study"]) for row in all_effect_rows if row.get("study")}),
            output_path=effects_path,
        )
        effect_manifest = _read_json(effect_manifest_path)
    else:
        effect_manifest_path = run_root / "effects.manifest.json"
        effect_manifest = _effect_manifest(
            effects_path,
            all_effect_rows,
            sorted({str(row["study"]) for row in all_effect_rows if row.get("study")}),
            "real",
        )
        _write_json(effect_manifest_path, effect_manifest)

    if loaded and all_effect_rows:
        for stratum in SYNTHESIS_STRATA:
            synthesis_dir = run_root / "synthesis" / stratum
            try:
                if classifications == {"synthetic"}:
                    result = synthesize(
                        effects_path,
                        stratum,
                        output_dir=synthesis_dir,
                        allow_outcomes=False,
                        provenance_manifest=effect_manifest_path,
                        retention_dir=private_work,
                        runner=runner,
                    )
                else:
                    result = synthesize(
                        all_effect_rows,
                        stratum,
                        output_dir=synthesis_dir,
                        allow_outcomes=allow_outcomes,
                        retention_dir=private_work,
                        runner=runner,
                    )
                synthesis_path = synthesis_dir / "synthesis.tsv"
                subgroup_path = synthesis_dir / "subgroups.tsv"
                _write_tsv(synthesis_path, result.summaries, SYNTHESIS_COLUMNS)
                _write_tsv(subgroup_path, result.subgroup_tests, SUBGROUP_COLUMNS)
                summary = {
                    "stratum": stratum,
                    "status": "complete",
                    "summary_rows": len(result.summaries),
                    "subgroup_rows": len(result.subgroup_tests),
                    "metadata": result.metadata,
                    "r_manifest": result.r_manifest,
                    "outputs_sha256": {
                        synthesis_path.name: _sha256_file(synthesis_path),
                        subgroup_path.name: _sha256_file(subgroup_path),
                    },
                }
                _write_json(synthesis_dir / "manifest.json", summary)
                synthesis_rows.append({
                    "stratum": stratum, "status": "complete",
                    "summary_rows": len(result.summaries), "reason": "",
                })
                synthesis_metadata[stratum] = result.metadata
                synthesis_summaries[stratum] = result.summaries
            except (OSError, ValueError, RuntimeError) as error:
                any_failure = True
                synthesis_rows.append({
                    "stratum": stratum, "status": "failed",
                    "summary_rows": 0, "reason": _safe_error_code(error),
                })
    else:
        reason = "no_validated_cohorts" if not loaded else "no_per_study_effect_rows"
        for stratum in SYNTHESIS_STRATA:
            synthesis_rows.append({
                "stratum": stratum,
                "status": "unavailable",
                "summary_rows": 0,
                "reason": reason,
            })

    meta_fgsea_rows = _run_post_meta_fgsea(
        loaded,
        all_effect_rows,
        synthesis_summaries,
        gene_mapping_by_unit,
        contract=meta_ranking_contract,
        results=run_root / "post_meta_fgsea",
        retention_dir=private_work,
        runner=runner,
    )
    if any(row["status"] not in {"complete", "not_applicable"} for row in meta_fgsea_rows):
        any_failure = True
    bulk_rows.extend(meta_fgsea_rows)

    _write_tsv(run_root / "availability.tsv", availability_rows, AVAILABILITY_COLUMNS)
    _write_tsv(run_root / "coverage.tsv", coverage_rows, COVERAGE_COLUMNS)
    _write_tsv(run_root / "bulk_stages.tsv", bulk_rows, BULK_COLUMNS)
    _write_tsv(run_root / "synthesis_status.tsv", synthesis_rows, SYNTHESIS_STATUS_COLUMNS)
    summary = {
        "schema_version": 1,
        "route": "outcomes",
        "run_id": run_id,
        "status": "partial" if any_failure or load_failures else "complete",
        "data_classification": _classification_summary(loaded),
        "cohorts": cohort_results,
        "family_order": list(A_BIO_FAMILIES),
        "endpoint_families": sorted({
            endpoint for view in loaded.values() for endpoint in view.metadata.endpoint_families
        }),
        "synthesis_strata": list(SYNTHESIS_STRATA),
        "synthesis": synthesis_rows,
        "post_meta_enrichment": _summarize_meta_fgsea_status(meta_fgsea_rows),
        "fraction_family": "unavailable pending the signed quanTIseq pin (N15)",
        "cibersortx": "not run",
        "biological_evidence": False,
    }
    _write_json(run_root / "summary.json", summary)
    manifest = {
        "schema_version": 1,
        "route": "outcomes",
        "run_id": run_id,
        "data_classification": _classification_summary(loaded),
        "outcome_payload_access": "synthetic_only" if classifications == {"synthetic"} else "authorized_for_real_route",
        "input_sha256": input_records,
        "source_inputs_sha256": {
            cohort: dict(view.source_inputs_sha256) for cohort, view in sorted(loaded.items())
        },
        "code_sha256": code_hashes,
        "cohorts": [
            {
                key: row[key] for key in (
                    "cohort_id", "status", "reason", "clinical_columns_read", "checks",
                    "patient_count", "completed_families", "endpoint_families",
                    "completed_endpoint_definitions", "failed_stages",
                ) if key in row
            }
            for row in cohort_results
        ],
        "feature_families": list(A_BIO_FAMILIES),
        "fraction_family": "unavailable pending the signed quanTIseq pin (N15)",
        "targeted_subset": "per study only; synthesis module excludes pooling and FDR",
        "source_label": "per study only under the endpoint-definition contract",
        "synthesis_strata": synthesis_metadata,
        "post_meta_enrichment": _summarize_meta_fgsea_status(meta_fgsea_rows),
        "output_sha256": _collect_output_hashes(run_root, exclude={"manifest.json"}),
        "biological_evidence": False if classifications == {"synthetic"} else None,
        "cibersortx": "not run",
    }
    _write_json(run_root / "manifest.json", manifest)
    return summary
