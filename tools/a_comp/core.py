"""Paper A composition workflow with an explicit N15 release gate."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import shutil
import sys
from collections import defaultdict
from importlib import metadata as package_metadata
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Sequence

from tools.a_meta.effects import study_effects
from tools.a_meta.features import (
    AVAILABLE_PANEL_IDS,
    build_feature_table,
    external_feature_table,
    _panel_definitions,
)
from tools.a_meta.provenance import (
    SYNTHETIC_FIXTURE_PRODUCER,
    canonical_sha256,
    effect_input_payload,
    effect_rows_payload,
    file_sha256,
    is_locked_study,
    known_cohort_ids,
    write_synthetic_fixture_manifest,
)
from tools.a_meta.synthesis import synthesize
from tools.a_scoring import cyt as frozen_cyt
from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]
R_SCRIPT = ROOT / "r/R/a_comp.R"
N15_PROPOSAL = ROOT / "docs/decisions/A_COMP_N15_PROPOSED_20261106.md"

ALLOWED_COHORTS = (
    "riaz_gse91061",
    "hugo_gse78220",
    "gse168204",
    "liu2019",
    "gide2019",
    "vanallen2015",
    "gse135222",
    "gse176307",
    "kim2018",
    "gse145996",
    "gse165278",
    "gse218989",
)

EXPECTED_PACKAGE_VERSIONS = {
    "immunedeconv": "2.1.4",
    "quantiseqr": "1.20.0",
    "limSolve": "2.0.3",
}
EXPECTED_R_VERSION = "4.6.1"
EXPECTED_BIOCONDUCTOR_VERSION = "3.23"
EXPECTED_REFERENCE_SHA256 = {
    "TIL10_signature.txt": "76aababc370c143705ee895f094a45eb168b87b10f30783bdcedbe4c4c0fecf9",
    "TIL10_mRNA_scaling.txt": "c7fa748a99c8f3e377924a7b35bed3000243966ee42beab7efac444940eecbd2",
    "TIL10_rmgenes.txt": "b05906748450b71d1a7b912ba3e351e2614052d99c2ba0670ff66510bac886f4",
    "TIL10_TCGA_aberrant_immune_genes.txt": "5182b9441fd03119da12a83ad932b9053cf73c62edc4028d55360ca3ad347fc3",
    "HGNC_genenames_20170418.txt.gz": "7bc6bd20dc57a696ca22dc603ef7f046c45e3e72ab591cea8857268dfb4f6b7e",
}

FRACTION_CELL_TYPES = (
    "B cell",
    "Macrophage M1",
    "Macrophage M2",
    "Monocyte",
    "Neutrophil",
    "NK cell",
    "T cell CD4+ (non-regulatory)",
    "T cell CD8+",
    "T cell regulatory (Tregs)",
    "Myeloid dendritic cell",
    "Other",
)
WEAK_CELL_TYPES = {"B cell", "Macrophage M2", "T cell regulatory (Tregs)"}
FRACTION_SUM_TOLERANCE = 1e-6
FRACTION_RANGE_TOLERANCE = 1e-6
PROPOSED_COVERAGE_FLOOR = 0.90
PANEL_SCORE_METHOD = "CUSTOM_MEAN"
CYT_METHOD_ID = "CYT_SQRT_TPM_GZMA_PRF1_NO_OFFSET"
FRACTION_METHOD_ID = "QUANTISEQR_1.20.0_TIL10_LSEI"
SYNTHETIC_ANALYSIS_MANIFEST_KIND = "a_comp_analysis_inputs"
SYNTHETIC_AUC_MANIFEST_KIND = "a_comp_incremental_auc_input"
SYNTHETIC_PANEL_MANIFEST_KIND = "a_comp_panel_definitions"
ANALYSIS_STRATA = (
    "per_cancer", "per_drug_class", "melanoma_cancer_drug", "across_cancers",
)
CLINICAL_INPUT_COLUMNS = (
    "study_id", "sample_id", "cancer", "drug_class", "orr_label",
    "clinical_benefit_label", "source_label", "orr_definition",
    "clinical_benefit_definition", "source_label_definition",
)
SYNTHETIC_ENDPOINT_DEFINITION_COLUMNS = {
    "orr": "orr_definition",
    "clinical_benefit": "clinical_benefit_definition",
    "source_label": "source_label_definition",
}
SYNTHETIC_ENDPOINT_DEFINITIONS = {
    "orr": "ORR: CR/PR versus SD/PD; original best.resp category retained.",
    "clinical_benefit": "DCB/NDB",
    "source_label": (
        "SOURCE_BINARY; responder/progressor source labels retained; "
        "SOFT does not define this as RECIST."
    ),
}
SYNTHETIC_ENDPOINT_LABEL_COLUMNS = {
    "orr": "orr_label",
    "clinical_benefit": "clinical_benefit_label",
    "source_label": "source_label",
}
SYNTHETIC_ENDPOINT_LABEL_CODES = {
    "orr": {"CR": 1, "PR": 1, "SD": 0, "PD": 0},
    "clinical_benefit": {"DCB": 1, "NDB": 0},
    "source_label": {"Responder": 1, "Progressor": 0},
}
FRACTION_INPUT_COLUMNS = ("study_id", "sample_id", "cell_type", "fraction")
INPUT_SCHEMA = "A_COMP_SYNTHETIC_ANALYSIS_INPUTS_V1"
SYNTHETIC_AUC_COLUMNS = (
    "study_id", "sample_id", "orr", "clinical_benefit", "source_label",
    "CYT", "synthetic_weighted_gep18",
    *(f"fraction__{cell}" for cell in FRACTION_CELL_TYPES),
)
PROTECTED_PATH_MARKERS = ("imvigor", "braun", "ingestionpacket", "freshingest")


class ACompError(ValueError):
    """A composition input, provenance, or analysis contract was invalid."""


class N15PinError(ACompError):
    """N15 is not signed with a complete, matching method pin."""


def _validate_synthetic_endpoint_inputs(clinical_rows: Sequence[Mapping]) -> dict:
    """Validate the fixed invented endpoint definitions and encode supported labels."""
    if not clinical_rows:
        raise ACompError("Synthetic clinical input has no endpoint rows")

    definitions = {}
    outcomes_by_sample: dict[str, dict[str, int]] = defaultdict(dict)
    for family, definition_column in SYNTHETIC_ENDPOINT_DEFINITION_COLUMNS.items():
        expected_definition = SYNTHETIC_ENDPOINT_DEFINITIONS[family]
        for row in clinical_rows:
            if definition_column not in row:
                raise ACompError(f"missing required invented endpoint definition column {definition_column}")
            observed_definition = row[definition_column]
            if observed_definition is None or not str(observed_definition).strip():
                raise ACompError(f"missing invented endpoint definition in {definition_column}")
            if observed_definition != expected_definition:
                raise ACompError(f"unsupported invented endpoint definition in {definition_column}")
        definitions[family] = clinical_rows[0][definition_column]

    for family, label_column in SYNTHETIC_ENDPOINT_LABEL_COLUMNS.items():
        label_codes = SYNTHETIC_ENDPOINT_LABEL_CODES[family]
        for row in clinical_rows:
            sample_id = str(row.get("sample_id", "")).strip()
            if not sample_id:
                raise ACompError("synthetic endpoint row is missing sample_id")
            if label_column not in row:
                raise ACompError(f"missing required invented endpoint label column {label_column}")
            raw_label = row[label_column]
            if raw_label is None or not str(raw_label).strip():
                raise ACompError(f"missing invented endpoint label in {label_column} for {sample_id}")
            label = str(raw_label).strip()
            if label not in label_codes:
                raise ACompError(f"unsupported invented endpoint label in {label_column} for {sample_id}")
            outcomes_by_sample[sample_id][family] = label_codes[label]

    return {"definitions": definitions, "outcomes_by_sample": dict(outcomes_by_sample)}


class _SyntheticAuthorization:
    __slots__ = ("classification", "purpose")

    def __init__(self):
        self.classification = "synthetic"
        self.purpose = "invented-only A-COMP software demonstration"


def _identity_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _known_real_alias(value: object) -> bool:
    token = _identity_token(value)
    if not token:
        return False
    known = {_identity_token(item) for item in known_cohort_ids()}
    return (
        is_locked_study(value)
        or any(marker in token for marker in ("imvigor", "braun"))
        or any(item and (item == token or item in token) for item in known)
    )


def _guard_external_paths(paths: Mapping[str, Path | str], *, data_classification: str) -> dict[str, Path]:
    """Check original and resolved path ancestry before opening any external file."""
    classification = str(data_classification).casefold()
    if classification not in {"real", "synthetic"}:
        raise ACompError("external path admission requires real or synthetic classification")
    known = {_identity_token(item) for item in known_cohort_ids()}
    protected = known - {_identity_token(item) for item in ALLOWED_COHORTS}
    checked: dict[str, Path] = {}
    for label, raw_path in paths.items():
        original = Path(raw_path).expanduser()
        if not original.is_absolute():
            original = ROOT / original
        original = Path(os.path.abspath(str(original)))
        for candidate in _path_ancestry(original):
            if candidate.is_symlink():
                raise ACompError(f"{label} path has symlink ancestry")
        resolved = original.resolve(strict=False)
        for candidate in _path_ancestry(resolved):
            if candidate.is_symlink():
                raise ACompError(f"{label} resolved path has symlink ancestry")
        components = {_identity_token(part) for part in (*original.parts, *resolved.parts)}
        if any(
            marker in component
            for marker in PROTECTED_PATH_MARKERS
            for component in components
        ) or any(component.startswith("ingest-") for component in components):
            raise ACompError(f"{label} path is inside an ingestion or protected-family path")
        blocked_ids = known if classification == "synthetic" else protected
        if any(identifier and any(identifier in component for component in components) for identifier in blocked_ids):
            raise ACompError(f"{label} path contains a real or protected cohort identity")
        checked[label] = resolved
    return checked


def _path_ancestry(path: Path) -> list[Path]:
    return [*reversed(path.parents), path]


def _snapshot_verified_files(
    paths: Mapping[str, Path],
    expected_hashes: Mapping[str, str],
    snapshot_dir: Path,
    *,
    data_classification: str,
) -> dict[str, Path]:
    """Copy admitted inputs to stable private files and verify the copied bytes."""
    checked = _guard_external_paths(
        {**paths, "snapshot_dir": snapshot_dir},
        data_classification=data_classification,
    )
    private_dir = checked.pop("snapshot_dir")
    private_dir.mkdir(parents=True, exist_ok=True)
    snapshots = {}
    for role, source in checked.items():
        expected = str(expected_hashes.get(role, ""))
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ACompError(f"{role} input is missing a SHA256 declaration")
        if not source.is_file() or source.is_symlink():
            raise ACompError(f"{role} input must be a regular file")
        if file_sha256(source) != expected:
            raise ACompError(f"{role} input hash does not match its admission record")
        suffix = source.suffix if source.suffix else ".bin"
        destination = private_dir / f"{role}_{expected[:16]}{suffix}"
        _guard_external_paths({f"{role} snapshot": destination}, data_classification=data_classification)
        if destination.exists():
            if destination.is_symlink() or not destination.is_file() or file_sha256(destination) != expected:
                raise ACompError(f"{role} verified snapshot already exists with different bytes")
        else:
            with source.open("rb") as input_stream, destination.open("xb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
            if file_sha256(destination) != expected:
                raise ACompError(f"{role} snapshot hash differs from its admission record")
        snapshots[role] = destination
    return snapshots


def _write_synthetic_manifest(
    path: Path,
    *,
    kind: str,
    declaration: Mapping,
    cohort_ids: Sequence[str],
) -> dict:
    """Use A-META's synthetic-fixture producer and bind the declaration itself."""
    result = write_synthetic_fixture_manifest(
        path,
        kind=kind,
        payload=dict(declaration),
        cohort_ids=cohort_ids,
    )
    result["declaration"] = dict(declaration)
    _write_json(path, result)
    return result


def _verify_synthetic_manifest(manifest: Mapping, *, kind: str) -> dict:
    if (
        manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER
        or manifest.get("manifest_version") != 1
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != kind
    ):
        raise ACompError("synthetic input requires the matching A-META fixture provenance record")
    declaration = manifest.get("declaration")
    if not isinstance(declaration, Mapping) or canonical_sha256(declaration) != manifest.get("payload_sha256"):
        raise ACompError("synthetic fixture declaration hash does not match its provenance record")
    declared_ids = [str(item) for item in manifest.get("cohort_ids", ())]
    if not declared_ids or len(declared_ids) != len(set(declared_ids)):
        raise ACompError("synthetic provenance requires unique cohort identities")
    if any(_known_real_alias(value) for value in declared_ids):
        raise ACompError("synthetic provenance cannot authorize known real or protected cohort aliases")
    declaration_ids = [str(item) for item in declaration.get("cohort_ids", ())]
    if len(declaration_ids) != len(set(declaration_ids)) or set(declaration_ids) != set(declared_ids):
        raise ACompError("synthetic declaration and provenance cohort identities differ")
    return dict(declaration)


def _write_analysis_input_manifest(
    manifest_path: Path,
    *,
    inputs: Mapping[str, Path],
    cohorts: Sequence[Mapping],
) -> dict:
    ids = [str(row["study_id"]) for row in cohorts]
    representation = {
        "platform": "rnaseq", "unit": "TPM", "transform": "unlogged",
        "feature_id": "gene_symbol", "full_source": True,
        "route_id": "INVENTED_FULL_SOURCE_TPM_V1",
        "data_classification": "synthetic",
        "source_identity": "invented gene-symbol TPM fixture; not a cohort export",
    }
    declaration = {
        "schema": INPUT_SCHEMA,
        "data_classification": "synthetic",
        "cohort_ids": sorted(ids),
        "input_sha256": {role: file_sha256(path) for role, path in sorted(inputs.items())},
        "input_names": {role: path.name for role, path in sorted(inputs.items())},
        "representation": representation,
        "cohorts": [dict(row) for row in cohorts],
        "clinical_columns": list(CLINICAL_INPUT_COLUMNS),
        "fraction_columns": list(FRACTION_INPUT_COLUMNS),
    }
    return _write_synthetic_manifest(
        manifest_path,
        kind=SYNTHETIC_ANALYSIS_MANIFEST_KIND,
        declaration=declaration,
        cohort_ids=ids,
    )


def _read_exact_tsv(path: Path, columns: Sequence[str], *, label: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ACompError(f"{label} is empty") from None
        if tuple(header) != tuple(columns):
            raise ACompError(f"{label} columns must exactly match the named read boundary")
        rows = []
        for row in reader:
            if len(row) != len(header):
                raise ACompError(f"{label} row has the wrong number of columns")
            rows.append(dict(zip(header, row)))
        return rows


def _read_identity_columns(path: Path, columns: Sequence[str], *, label: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ACompError(f"{label} is empty") from None
        indexes = {name: header.index(name) for name in columns if name in header}
        if tuple(indexes) != tuple(columns):
            raise ACompError(f"{label} identity columns are missing or reordered")
        if label == "clinical input" and tuple(header) != CLINICAL_INPUT_COLUMNS:
            raise ACompError("clinical input columns must exactly match the named read boundary")
        if label == "fraction input" and tuple(header) != FRACTION_INPUT_COLUMNS:
            raise ACompError("fraction input columns must exactly match the named read boundary")
        rows = []
        for row in reader:
            if len(row) != len(header):
                raise ACompError(f"{label} row has the wrong number of columns")
            rows.append({name: row[indexes[name]] for name in columns})
        return rows


def _read_tpm_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as stream:
        try:
            header = next(csv.reader(stream, delimiter="\t"))
        except StopIteration:
            raise ACompError("TPM matrix is empty") from None
    if len(header) < 2 or header[0] != "gene_symbol":
        raise ACompError("TPM matrix must have an exact gene_symbol header")
    sample_ids = header[1:]
    if any(not value.startswith("invented_") for value in sample_ids):
        raise ACompError("Synthetic TPM sample identities must be explicitly invented")
    if len(sample_ids) != len(set(sample_ids)) or any(_known_real_alias(value) for value in sample_ids):
        raise ACompError("Synthetic TPM sample identities are duplicated or protected")
    return sample_ids


def classify_input(
    *,
    cohort_id: str,
    data_classification: str,
    representation: Mapping,
) -> str:
    """Check data class and representation before any cohort table is opened."""
    cohort = str(cohort_id).strip()
    classification = str(data_classification).strip().casefold()
    if not cohort:
        raise ACompError("A-COMP requires a declared cohort identifier")
    if classification == "synthetic":
        if _known_real_alias(cohort) or _identity_token(cohort) in {
            _identity_token(value) for value in ALLOWED_COHORTS
        }:
            raise ACompError("synthetic bypass refuses known real cohort identifiers")
        _validate_tpm_representation(representation, allow_invented_source=True)
        return "synthetic"
    if classification != "real":
        raise ACompError("data classification must be real or synthetic")
    _require_real_cohort(cohort)
    _validate_tpm_representation(representation, allow_invented_source=False)
    return "real"


def validate_tpm_matrix(
    *,
    genes: Sequence[str],
    sample_ids: Sequence[str],
    values: Sequence[Sequence[float]],
    representation: Mapping,
) -> None:
    """Validate a declared full-source unlogged gene-symbol TPM matrix."""
    _validate_tpm_representation(
        representation,
        allow_invented_source=representation.get("data_classification") == "synthetic",
    )
    gene_ids = [str(value).strip() for value in genes]
    samples = [str(value).strip() for value in sample_ids]
    if not gene_ids or not samples:
        raise ACompError("TPM matrix requires genes and samples")
    if any(not value for value in gene_ids) or len(gene_ids) != len(set(gene_ids)):
        raise ACompError("TPM matrix has an empty or duplicate gene key")
    if any(not value for value in samples) or len(samples) != len(set(samples)):
        raise ACompError("TPM matrix has an empty or duplicate sample key")
    if len(values) != len(gene_ids):
        raise ACompError("TPM matrix dimensions do not match the declared gene keys")
    for row in values:
        if len(row) != len(samples):
            raise ACompError("TPM matrix dimensions do not match the declared sample keys")
        for value in row:
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ACompError("TPM values must be numeric and finite") from None
            if not math.isfinite(number):
                raise ACompError("TPM values must be finite")
            if number < 0:
                raise ACompError("TPM values must be non-negative")
    declared_n_features = representation.get("n_features")
    declared_n_samples = representation.get("n_samples")
    if declared_n_features is not None and int(declared_n_features) != len(gene_ids):
        raise ACompError("TPM manifest feature count does not match the matrix")
    if declared_n_samples is not None and int(declared_n_samples) != len(samples):
        raise ACompError("TPM manifest sample count does not match the matrix")


def validate_fraction_rows(
    rows: Sequence[Mapping],
    *,
    expected_sample_ids: Sequence[str],
    tolerance: float = FRACTION_SUM_TOLERANCE,
) -> None:
    """Check the ten immune types plus Other without altering fraction values."""
    expected_samples = [str(value) for value in expected_sample_ids]
    if not expected_samples or len(expected_samples) != len(set(expected_samples)):
        raise ACompError("Expected fraction sample IDs must be unique and non-empty")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ACompError("Fraction sum tolerance must be finite and non-negative")
    by_sample: dict[str, dict[str, float]] = defaultdict(dict)
    first_seen_samples = []
    for row in rows:
        sample = str(row.get("sample_id", ""))
        cell = str(row.get("cell_type", ""))
        if not sample or not cell:
            raise ACompError("Fraction rows require sample_id and cell_type")
        if sample not in by_sample:
            first_seen_samples.append(sample)
        if cell in by_sample[sample]:
            raise ACompError("Fraction output contains duplicate sample/cell-type keys")
        if cell not in FRACTION_CELL_TYPES:
            raise ACompError(f"Fraction output contains an unknown cell type: {cell}")
        try:
            value = float(row.get("fraction"))
        except (TypeError, ValueError):
            raise ACompError("Fraction values must be numeric and finite") from None
        if not math.isfinite(value):
            raise ACompError("Fraction values must be finite")
        if value < -FRACTION_RANGE_TOLERANCE or value > 1 + FRACTION_RANGE_TOLERANCE:
            raise ACompError("Fraction value is outside the admissible range")
        by_sample[sample][cell] = value
    if first_seen_samples != expected_samples:
        raise ACompError("Fraction output sample order does not match the TPM input")
    expected_cells = set(FRACTION_CELL_TYPES)
    for sample in expected_samples:
        cell_values = by_sample.get(sample, {})
        if set(cell_values) != expected_cells:
            raise ACompError("Fraction output is missing required cell types")
        if abs(math.fsum(cell_values.values()) - 1.0) > tolerance:
            raise ACompError("Fraction sum is outside the declared numerical tolerance")


def validate_sample_alignment(
    expression_sample_ids: Sequence[str],
    *,
    clinical_sample_ids: Sequence[str],
    fraction_sample_ids: Sequence[str],
    score_sample_ids: Sequence[str],
) -> None:
    """Require exact sample identity, order, and coverage across analysis inputs."""
    expected = [str(value) for value in expression_sample_ids]
    if not expected or len(expected) != len(set(expected)):
        raise ACompError("Expression sample coverage must be unique and non-empty")
    sources = {
        "clinical": [str(value) for value in clinical_sample_ids],
        "fraction": [str(value) for value in fraction_sample_ids],
        "score": [str(value) for value in score_sample_ids],
    }
    for label, sample_ids in sources.items():
        if len(sample_ids) != len(expected) or set(sample_ids) != set(expected):
            raise ACompError(f"{label} sample coverage does not match expression coverage")
        if sample_ids != expected:
            raise ACompError(f"{label} samples must have identical sample order")


def verify_reference_report(report: Mapping) -> None:
    """Require the parent-verified R, Bioconductor, package, and reference pins."""
    if str(report.get("r_version")) != EXPECTED_R_VERSION:
        raise ACompError("R version mismatch")
    if str(report.get("bioconductor_version")) != EXPECTED_BIOCONDUCTOR_VERSION:
        raise ACompError("Bioconductor version mismatch")
    actual_packages = report.get("package_versions")
    if not isinstance(actual_packages, Mapping):
        raise ACompError("R provenance is missing package versions")
    for package, expected in EXPECTED_PACKAGE_VERSIONS.items():
        if str(actual_packages.get(package, "")) != expected:
            raise ACompError(f"package version mismatch: {package}")
    actual_references = report.get("reference_files")
    if isinstance(actual_references, Sequence) and not isinstance(actual_references, (str, bytes)):
        actual_references = {
            str(row.get("file")): str(row.get("sha256"))
            for row in actual_references
            if isinstance(row, Mapping)
        }
    if not isinstance(actual_references, Mapping):
        raise ACompError("R provenance is missing reference hashes")
    for name, expected in EXPECTED_REFERENCE_SHA256.items():
        if str(actual_references.get(name, "")) != expected:
            raise ACompError(f"reference hash mismatch: {name}")


def require_analysis_contract(contract: Mapping | None, *, data_classification: str) -> None:
    """Keep the two unresolved real-analysis choices closed."""
    if data_classification != "real":
        return
    if not isinstance(contract, Mapping) or contract.get("status") != "SIGNED":
        raise ACompError(
            "real A-COMP analysis is blocked: A-COMP bootstrap stream/refit/evaluation "
            "contract and published weighted GEP scoring contract are unresolved"
        )
    if contract.get("bootstrap_contract") != "SIGNED_A_COMP_BOOTSTRAP_CONTRACT":
        raise ACompError("signed A-COMP bootstrap stream/refit/evaluation contract is missing")
    if contract.get("gep_score_id") != "PUBLISHED_WEIGHTED_GEP18" or not contract.get("gep_weight_sha256"):
        raise ACompError("published weighted GEP scoring contract is missing")


def run_real_deconvolution(
    *,
    cohort_id: str,
    pin_path: Path,
    expression_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> dict:
    """Run outcome-free deconvolution only after N15 and all input checks pass."""
    _require_real_cohort(cohort_id)
    checked = _guard_external_paths(
        {
            "N15 pin": pin_path,
            "TPM expression": expression_path,
            "input manifest": manifest_path,
            "output": output_dir,
        },
        data_classification="real",
    )
    pin = _read_n15_pin(checked["N15 pin"])
    _validate_signed_pin(pin)
    raise ACompError(
        "real A-COMP source admission is not implemented; a signed N15 pin alone "
        "does not authorize a real loader or cohort execution"
    )


def analyze_real_request(
    *,
    cohort_id: str,
    pin_path: Path,
    expression_path: Path,
    clinical_path: Path,
    analysis_contract_path: Path | None,
    output_dir: Path,
) -> dict:
    """Refuse real outcome-linked analyses until user-owned scientific gates close."""
    _require_real_cohort(cohort_id)
    paths = {
        "N15 pin": pin_path,
        "TPM expression": expression_path,
        "clinical input": clinical_path,
        "output": output_dir,
    }
    if analysis_contract_path is not None:
        paths["A-COMP analysis contract"] = analysis_contract_path
    checked = _guard_external_paths(paths, data_classification="real")
    pin = _read_n15_pin(checked["N15 pin"])
    _validate_signed_pin(pin)
    if analysis_contract_path is None or not checked["A-COMP analysis contract"].is_file():
        require_analysis_contract(None, data_classification="real")
    contract = _read_json(checked["A-COMP analysis contract"], "A-COMP analysis contract")
    require_analysis_contract(contract, data_classification="real")
    raise ACompError(
        "real A-COMP analysis is not released: the source loader, bootstrap contract, "
        "published weighted GEP contract, and A-META outcome guard remain open"
    )


def run_synthetic_demo(output_dir: Path) -> dict:
    """Generate an invented quanTIseq fixture, then call the reusable analyzer."""
    output = Path(output_dir).expanduser().absolute()
    _guard_external_paths({"synthetic output": output}, data_classification="synthetic")
    if output.exists() and any(output.iterdir()):
        raise ACompError("Synthetic output directory already contains files; choose a fresh path")
    output.mkdir(parents=True, exist_ok=True)
    private = output / ".private"
    preflight = _run_reference_preflight(
        private / "r_outputs" / "preflight",
        retention_dir=private / "bridge_retention" / "preflight",
    )
    verify_reference_report(preflight)

    panel_path = output / "panel_definitions.tsv"
    _write_panel_definitions(panel_path)
    study_ids = [
        "invented_cohort_01", "invented_cohort_02",
        "invented_cohort_03", "invented_cohort_04",
    ]
    panel_manifest_path = private / "provenance" / "panel_definitions.json"
    panel_declaration = {
        "schema": "A_COMP_PANEL_DEFINITIONS_V1",
        "input_sha256": {"panel_definitions": file_sha256(panel_path)},
        "cohort_ids": study_ids,
    }
    _write_synthetic_manifest(
        panel_manifest_path,
        kind=SYNTHETIC_PANEL_MANIFEST_KIND,
        declaration=panel_declaration,
        cohort_ids=study_ids,
    )
    panel_inputs = _snapshot_verified_files(
        {"panel_definitions": panel_path, "panel_manifest": panel_manifest_path},
        {
            "panel_definitions": panel_declaration["input_sha256"]["panel_definitions"],
            "panel_manifest": file_sha256(panel_manifest_path),
        },
        private / "verified_inputs" / "panel",
        data_classification="synthetic",
    )
    deconvolution = run_r(
        R_SCRIPT,
        panel_inputs,
        {
            "project_root": str(ROOT),
            "operation": "synthetic_demo",
            "expected_outputs": [
                "tpm.tsv", "sample_groups.tsv", "fractions.tsv", "coverage.tsv",
                "quantiseq_run.json",
            ],
        },
        private / "r_outputs" / "synthetic_demo",
        retention_dir=private / "bridge_retention" / "synthetic_demo",
    )
    sample_groups = _read_tsv(deconvolution.outputs["sample_groups.tsv"])
    r_fraction_rows = _read_tsv(deconvolution.outputs["fractions.tsv"])
    fraction_rows = [
        {
            "study_id": row["study_id"], "sample_id": row["sample_id"],
            "cell_type": row["cell_type"], "fraction": row["fraction"],
        }
        for row in r_fraction_rows
    ]
    for source_name, public_name in (
        ("tpm.tsv", "tpm.tsv"),
        ("coverage.tsv", "coverage.tsv"),
        ("quantiseq_run.json", "quantiseq_run.json"),
    ):
        _copy_or_verify(deconvolution.outputs[source_name], output / public_name)
    _write_tsv(output / "clinical.tsv", sample_groups)
    _write_tsv(output / "fractions.tsv", fraction_rows)
    cohorts = _cohort_declarations(sample_groups)
    input_paths = {
        "expression": output / "tpm.tsv",
        "clinical": output / "clinical.tsv",
        "fractions": output / "fractions.tsv",
    }
    input_manifest_path = output / "analysis_input_manifest.json"
    _write_analysis_input_manifest(input_manifest_path, inputs=input_paths, cohorts=cohorts)
    analysis = analyze_synthetic_inputs(
        expression_path=input_paths["expression"],
        clinical_path=input_paths["clinical"],
        fractions_path=input_paths["fractions"],
        manifest_path=input_manifest_path,
        output_dir=output,
        preflight_report=preflight,
        extra_r_manifests=(deconvolution.manifest,),
    )
    summary = {
        **analysis,
        "status": "synthetic-software-demonstration",
        "data_classification": "synthetic",
        "biological_validation": False,
        "cohort_ids": sorted(row["study_id"] for row in cohorts),
        "cancers": sorted({str(row["cancer"]) for row in cohorts}),
        "drug_classes": sorted({str(row["drug_class"]) for row in cohorts}),
        "quantiseq": {
            "method": "lsei", "signature": "TIL10", "tumor": True,
            "arrays": False, "scale_mrna": True, "rm_genes": None,
            "rna_rm_genes_behavior": "packaged default removal list",
            "tumour_exclusions": "packaged aberrant immune-gene list",
        },
        "r_version": preflight["r_version"],
        "bioconductor_version": preflight["bioconductor_version"],
        "package_versions": dict(EXPECTED_PACKAGE_VERSIONS),
        "reference_files": dict(EXPECTED_REFERENCE_SHA256),
        "synthesis_strata": list(ANALYSIS_STRATA),
        "incremental_auc_method": "SYNTHETIC_WEIGHTED_GEP18_DEMO",
        "incremental_auc_is_published_gep": False,
        "bootstrap": {
            "contract_id": "a_comp_synthetic_demo_v2",
            "draws_in": "R",
            "repetitions": 40,
            "model_refit": False,
            "evaluation": "paired outcome-stratified resample of fixed full-synthetic-data predictions",
            "interpretation": "invented machinery demonstration only",
        },
        "second_check": {
            "stream": "second_check",
            "reported_only": True,
            "replaced_main_result": False,
            "outcome_based_rerun": False,
            "endpoint_flag_rule": "report-only; flag if either 95% interval endpoint shifts by more than 0.01 AUROC",
        },
        "cibersortx": "not run",
        "deferred_real_gates": [
            "N15 user signature",
            "real A-COMP source loader/admission",
            "A-COMP bootstrap stream/refit/evaluation contract",
            "published weighted GEP coefficients and normalization contract",
            "real outcome release under the existing A-META guard",
        ],
    }
    _write_json(output / "synthetic_summary.json", summary)
    artifact_manifest = _read_json(output / "artifact_manifest.json", "A-COMP artifact manifest")
    artifact_manifest["public_products"] = _public_artifact_hashes(output)
    _write_json(output / "artifact_manifest.json", artifact_manifest)
    return summary


def analyze_synthetic_inputs(
    *,
    expression_path: Path,
    clinical_path: Path,
    fractions_path: Path,
    manifest_path: Path,
    output_dir: Path,
    preflight_report: Mapping | None = None,
    extra_r_manifests: Sequence[Mapping] = (),
) -> dict:
    """Analyze admitted invented TPM, named clinical columns, and fractions."""
    output = Path(output_dir).expanduser().absolute()
    paths = _guard_external_paths(
        {
            "expression": expression_path, "clinical": clinical_path,
            "fractions": fractions_path, "input manifest": manifest_path,
            "output": output,
        },
        data_classification="synthetic",
    )
    output.mkdir(parents=True, exist_ok=True)
    private = output / ".private"
    _guard_external_paths({"private analysis": private}, data_classification="synthetic")
    private.mkdir(parents=True, exist_ok=True)

    manifest_source_hash = file_sha256(paths["input manifest"])
    manifest_snapshot = _snapshot_verified_files(
        {"input_manifest": paths["input manifest"]},
        {"input_manifest": manifest_source_hash},
        private / "verified_inputs" / "analysis_manifest",
        data_classification="synthetic",
    )["input_manifest"]
    manifest = _read_json(manifest_snapshot, "synthetic A-COMP input manifest")
    declaration = _verify_synthetic_manifest(manifest, kind=SYNTHETIC_ANALYSIS_MANIFEST_KIND)
    if declaration.get("schema") != INPUT_SCHEMA or declaration.get("data_classification") != "synthetic":
        raise ACompError("Synthetic A-COMP input declaration has an unsupported schema or classification")
    cohort_ids = [str(value) for value in manifest.get("cohort_ids", ())]
    cohort_declarations = declaration.get("cohorts")
    if not isinstance(cohort_declarations, list):
        raise ACompError("Synthetic input manifest requires explicit cancer and drug metadata")
    cohort_map = {}
    for row in cohort_declarations:
        if not isinstance(row, Mapping) or set(row) != {"study_id", "cancer", "drug_class"}:
            raise ACompError("Synthetic cohort declarations require study_id, cancer, and drug_class")
        study = str(row["study_id"])
        cancer = str(row["cancer"]).strip().casefold()
        drug = str(row["drug_class"]).strip()
        if not study.startswith("invented_") or _known_real_alias(study) or not cancer or drug not in {
            "ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4"
        }:
            raise ACompError("Synthetic cohort metadata contains an invalid identity, cancer, or drug class")
        cohort_map[study] = {"study_id": study, "cancer": cancer, "drug_class": drug}
    if len(cohort_map) != len(cohort_declarations) or set(cohort_map) != set(cohort_ids):
        raise ACompError("Synthetic cohort metadata and provenance identities differ")
    if set(str(value) for value in declaration.get("cohort_ids", ())) != set(cohort_ids):
        raise ACompError("Synthetic input declaration and provenance cohort identities differ")

    input_hashes = declaration.get("input_sha256")
    input_names = declaration.get("input_names")
    if not isinstance(input_hashes, Mapping) or set(input_hashes) != {"expression", "clinical", "fractions"}:
        raise ACompError("Synthetic input manifest must bind expression, clinical, and fractions files")
    if not isinstance(input_names, Mapping):
        raise ACompError("Synthetic input manifest is missing input names")
    for role in ("expression", "clinical", "fractions"):
        if Path(paths[role]).name != str(input_names.get(role, "")):
            raise ACompError(f"{role} path does not match its declared synthetic input identity")
        if file_sha256(paths[role]) != str(input_hashes[role]):
            raise ACompError(f"{role} input hash does not match the synthetic manifest")

    snapshots = _snapshot_verified_files(
        {role: paths[role] for role in ("expression", "clinical", "fractions")},
        input_hashes,
        private / "verified_inputs" / canonical_sha256(declaration)[:16],
        data_classification="synthetic",
    )
    representation = declaration.get("representation")
    if not isinstance(representation, Mapping):
        raise ACompError("Synthetic TPM representation is missing")
    _validate_tpm_representation(representation, allow_invented_source=True)
    sample_ids = _read_tpm_header(snapshots["expression"])

    clinical_identity = _read_identity_columns(
        snapshots["clinical"], ("study_id", "sample_id"), label="clinical input"
    )
    fraction_identity = _read_identity_columns(
        snapshots["fractions"], ("study_id", "sample_id"), label="fraction input"
    )
    observed_cohorts = {str(row["study_id"]) for row in clinical_identity}
    if observed_cohorts != set(cohort_ids) or any(_known_real_alias(value) for value in observed_cohorts):
        raise ACompError("Synthetic clinical study identities contradict provenance or name a known cohort")
    for row in clinical_identity:
        if row["study_id"] not in cohort_map or row["sample_id"] not in sample_ids:
            raise ACompError("Synthetic clinical rows contain an undeclared study or sample")
        if not row["sample_id"].startswith("invented_") or _known_real_alias(row["sample_id"]):
            raise ACompError("Synthetic clinical sample identity is not explicitly invented")
    for row in fraction_identity:
        if row["study_id"] not in cohort_map or row["sample_id"] not in sample_ids:
            raise ACompError("Synthetic fraction rows contain an undeclared study or sample")
        if not row["sample_id"].startswith("invented_") or _known_real_alias(row["sample_id"]):
            raise ACompError("Synthetic fraction sample identity is not explicitly invented")
    if [row["sample_id"] for row in clinical_identity] != sample_ids:
        raise ACompError("Clinical sample order does not match the TPM input order")
    study_for_sample = {row["sample_id"]: row["study_id"] for row in clinical_identity}
    if len(study_for_sample) != len(clinical_identity):
        raise ACompError("Synthetic clinical sample keys are duplicated")
    for row in fraction_identity:
        if study_for_sample.get(row["sample_id"]) != row["study_id"]:
            raise ACompError("Fraction study/sample identity differs from the clinical table")

    genes, expression_sample_ids, matrix = read_tpm_matrix(snapshots["expression"], representation)
    if expression_sample_ids != sample_ids:
        raise ACompError("TPM sample identities changed after boundary validation")
    clinical_table = _read_exact_tsv(
        snapshots["clinical"], CLINICAL_INPUT_COLUMNS, label="clinical input"
    )
    fraction_table = _read_exact_tsv(
        snapshots["fractions"], FRACTION_INPUT_COLUMNS, label="fraction input"
    )
    if len(clinical_table) != len(sample_ids):
        raise ACompError("Clinical input must contain one named row per TPM sample")
    endpoint_inputs = _validate_synthetic_endpoint_inputs(clinical_table)
    fraction_sample_order = list(dict.fromkeys(row["sample_id"] for row in fraction_table))
    if fraction_sample_order != sample_ids:
        raise ACompError("Fraction sample coverage/order does not match the TPM input")
    for row in clinical_table:
        cohort = cohort_map[row["study_id"]]
        if row["cancer"].casefold() != cohort["cancer"] or row["drug_class"] != cohort["drug_class"]:
            raise ACompError("Clinical cancer/drug metadata differs from its declared study metadata")
    validate_fraction_rows(
        fraction_table,
        expected_sample_ids=sample_ids,
        tolerance=FRACTION_SUM_TOLERANCE,
    )
    fraction_by_sample: dict[str, dict[str, float]] = defaultdict(dict)
    for row in fraction_table:
        fraction_by_sample[row["sample_id"]][row["cell_type"]] = float(row["fraction"])

    if preflight_report is None:
        preflight_report = _run_reference_preflight(
            private / "r_outputs" / "preflight",
            retention_dir=private / "bridge_retention" / "preflight",
        )
    verify_reference_report(preflight_report)

    groups_by_study: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in clinical_table:
        groups_by_study[row["study_id"]].append(row)
    all_effects: list[dict] = []
    all_correlations: list[dict] = []
    auc_input_rows: list[dict] = []
    panel_coverage_rows: list[dict] = []
    study_ranks = {study: index for index, study in enumerate(sorted(groups_by_study), 1)}
    for study_id in sorted(groups_by_study):
        study_rows = groups_by_study[study_id]
        local_samples = [row["sample_id"] for row in study_rows]
        sample_index = {sample: sample_ids.index(sample) for sample in local_samples}
        local_matrix = [
            [row[sample_index[sample]] for sample in local_samples]
            for row in matrix
        ]
        view_path = private / "analysis_views" / f"study_{study_ranks[study_id]:02d}_tpm.tsv"
        _write_matrix(view_path, genes, local_samples, local_matrix)
        base_clinical_rows = [
            {
                "patient_id": row["sample_id"], "sample_id": row["sample_id"],
                "raw_orr": row["orr_label"],
                "raw_clinical_benefit": row["clinical_benefit_label"],
                "treatment_outcome": row["source_label"],
                "drug_class": row["drug_class"],
                "orr_definition": row["orr_definition"],
                "clinical_benefit_definition": row["clinical_benefit_definition"],
                "source_label_definition": row["source_label_definition"],
            }
            for row in study_rows
        ]
        cohort = cohort_map[study_id]
        metadata = SimpleNamespace(
            cohort_id=study_id,
            cancer=cohort["cancer"],
            uniform_drug_class=cohort["drug_class"],
            endpoint_families=("orr", "clinical_benefit", "source_label"),
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol"
            ),
        )
        view = SimpleNamespace(metadata=metadata, expression_path=view_path, clinical_rows=base_clinical_rows)
        fraction_feature_rows = [
            {"patient_row": index, "unit": cell, "value": fraction_by_sample[sample][cell]}
            for index, sample in enumerate(local_samples)
            for cell in FRACTION_CELL_TYPES
        ]
        fraction_features = external_feature_table(
            fraction_feature_rows, cohort_id=study_id, expected_patients=len(local_samples)
        )
        fraction_features.metadata["method_id_by_unit"] = {
            cell: FRACTION_METHOD_ID for cell in FRACTION_CELL_TYPES
        }
        for endpoint_family in SYNTHETIC_ENDPOINT_DEFINITION_COLUMNS:
            endpoint_rows = [
                dict(row, endpoint_definition=endpoint_inputs["definitions"][endpoint_family])
                for row in base_clinical_rows
            ]
            endpoint_view = SimpleNamespace(
                metadata=metadata, expression_path=view_path, clinical_rows=endpoint_rows
            )
            effect_manifest = private / "provenance" / (
                f"study_{study_ranks[study_id]:02d}_{endpoint_family}_effects.json"
            )
            write_synthetic_fixture_manifest(
                effect_manifest,
                kind="study_effects_input",
                payload=effect_input_payload(endpoint_view, fraction_features),
                cohort_ids=(study_id,),
            )
            all_effects.extend(
                study_effects(
                    endpoint_view, fraction_features, endpoint_family,
                    provenance_manifest=effect_manifest,
                )
            )

        panel_features = build_feature_table(view, "panel")
        gene_features = build_feature_table(view, "gene")
        panel_coverage_rows.extend(
            {
                "study": study_id, "panel": panel,
                "method_id": panel_features.metadata["method_id_by_unit"].get(panel, ""),
                **details,
            }
            for panel, details in panel_features.coverage.items()
        )
        validate_sample_alignment(
            local_samples,
            clinical_sample_ids=[row["sample_id"] for row in study_rows],
            fraction_sample_ids=[sample for sample in local_samples if sample in fraction_by_sample],
            score_sample_ids=local_samples,
        )
        tpm_by_gene = {gene: values for gene, values in zip(genes, matrix)}
        if "GZMA" not in tpm_by_gene or "PRF1" not in tpm_by_gene:
            raise ACompError("qualified CYT requires both GZMA and PRF1 in the full TPM matrix")
        cyt_values = [
            frozen_cyt(
                float(tpm_by_gene["GZMA"][sample_index[sample]]),
                float(tpm_by_gene["PRF1"][sample_index[sample]]),
            )
            for sample in local_samples
        ]
        score_values = {
            panel: list(panel_features.values_by_unit[panel])
            for panel in AVAILABLE_PANEL_IDS
        }
        score_values["CYT"] = cyt_values
        all_correlations.extend(
            _study_correlations(
                study_id=study_id,
                sample_ids=local_samples,
                fractions={sample: fraction_by_sample[sample] for sample in local_samples},
                scores=score_values,
                panel_features=panel_features,
            )
        )

        gep_members = _panel_definitions(("AYERS_GEP_18",))["AYERS_GEP_18"]
        gep_weights = {gene: index + 1 for index, gene in enumerate(gep_members)}
        weight_total = math.fsum(gep_weights.values())
        invented_gep = [
            math.fsum(
                weight / weight_total * float(gene_features.values_by_unit[gene][row_index])
                for gene, weight in gep_weights.items()
            )
            for row_index in range(len(local_samples))
        ]
        for row_index, clinical in enumerate(study_rows):
            encoded_outcomes = endpoint_inputs["outcomes_by_sample"][clinical["sample_id"]]
            auc_input_rows.append({
                "study_id": study_id,
                "sample_id": clinical["sample_id"],
                "orr": encoded_outcomes["orr"],
                "clinical_benefit": encoded_outcomes["clinical_benefit"],
                "source_label": encoded_outcomes["source_label"],
                "CYT": cyt_values[row_index],
                "synthetic_weighted_gep18": invented_gep[row_index],
                **{
                    f"fraction__{cell}": fraction_by_sample[clinical["sample_id"]][cell]
                    for cell in FRACTION_CELL_TYPES
                },
            })

    strata_summaries = []
    strata_subgroups = []
    endpoint_partitions = sorted({
        (str(row["unit_family"]), str(row["endpoint_family"]), str(row["endpoint_definition_id"]))
        for row in all_effects
    })
    for partition_number, (unit_family, endpoint_family, definition_id) in enumerate(endpoint_partitions, 1):
        partition = [
            row for row in all_effects
            if row["unit_family"] == unit_family
            and row["endpoint_family"] == endpoint_family
            and row["endpoint_definition_id"] == definition_id
        ]
        partition_studies = sorted({str(row["study"]) for row in partition})
        effect_manifest = private / "provenance" / f"effect_partition_{partition_number:02d}.json"
        write_synthetic_fixture_manifest(
            effect_manifest,
            kind="effect_rows",
            payload=effect_rows_payload(partition),
            cohort_ids=partition_studies,
        )
        for stratum in ANALYSIS_STRATA:
            synthesis_result = synthesize(
                partition,
                stratum,
                output_dir=private / "synthesis" / f"partition_{partition_number:02d}" / stratum,
                provenance_manifest=effect_manifest,
                retention_dir=(
                    private / "bridge_retention" / "synthesis"
                    / f"partition_{partition_number:02d}" / stratum
                ),
            )
            strata_summaries.extend(
                dict(row, requested_stratum=stratum, requested_unit_family=unit_family,
                     requested_endpoint_family=endpoint_family,
                     requested_endpoint_definition_id=definition_id)
                for row in synthesis_result.summaries
            )
            strata_subgroups.extend(
                dict(row, requested_stratum=stratum, requested_unit_family=unit_family,
                     requested_endpoint_family=endpoint_family,
                     requested_endpoint_definition_id=definition_id)
                for row in synthesis_result.subgroup_tests
            )

    auc_path = private / "synthetic_incremental_auc.tsv"
    _write_tsv(auc_path, auc_input_rows)
    auc_cohort_ids = sorted(groups_by_study)
    auc_declaration = {
        "schema": "A_COMP_SYNTHETIC_AUC_INPUT_V1",
        "input_sha256": {"auc_input": file_sha256(auc_path)},
        "cohort_ids": auc_cohort_ids,
        "clinical_columns": ["study_id", "sample_id", "orr", "clinical_benefit", "source_label"],
        "input_columns": list(SYNTHETIC_AUC_COLUMNS),
    }
    auc_manifest_path = private / "provenance" / "synthetic_incremental_auc.json"
    _write_synthetic_manifest(
        auc_manifest_path,
        kind=SYNTHETIC_AUC_MANIFEST_KIND,
        declaration=auc_declaration,
        cohort_ids=auc_cohort_ids,
    )
    auc_inputs = _snapshot_verified_files(
        {"auc_input": auc_path, "auc_manifest": auc_manifest_path},
        {
            "auc_input": auc_declaration["input_sha256"]["auc_input"],
            "auc_manifest": file_sha256(auc_manifest_path),
        },
        private / "verified_inputs" / "incremental_auc",
        data_classification="synthetic",
    )
    auc_result = run_r(
        R_SCRIPT,
        auc_inputs,
        {
            "project_root": str(ROOT),
            "operation": "synthetic_incremental_auc",
            "bootstrap_repetitions": 40,
            "primary_synthetic_seed": 20261110,
            "second_check_repetitions": 40,
            "second_check_stream": "second_check",
            "second_check_task_id": "a_comp_synthetic_demo_v2",
            "expected_outputs": [
                "incremental_auc.tsv", "bootstrap_assignments.tsv", "bootstrap_receipt.json",
                "auc_predictions.tsv",
            ],
        },
        private / "r_outputs" / "incremental_auc",
        retention_dir=private / "bridge_retention" / "incremental_auc",
    )
    auc_rows = _read_tsv(auc_result.outputs["incremental_auc.tsv"])
    correlation_summaries = _summarize_correlations(all_correlations)
    _write_tsv(output / "fraction_effects.tsv", all_effects)
    _write_tsv(output / "fraction_synthesis.tsv", strata_summaries)
    _write_tsv(output / "fraction_subgroup_tests.tsv", strata_subgroups)
    _write_tsv(output / "panel_correlations.tsv", all_correlations)
    _write_tsv(output / "panel_correlation_summary.tsv", correlation_summaries)
    _write_tsv(output / "panel_coverage.tsv", panel_coverage_rows)
    _copy_or_verify(auc_result.outputs["incremental_auc.tsv"], output / "incremental_auc.tsv")
    _copy_or_verify(auc_result.outputs["bootstrap_assignments.tsv"], output / "bootstrap_assignments.tsv")
    _copy_or_verify(auc_result.outputs["bootstrap_receipt.json"], output / "bootstrap_receipt.json")
    _copy_or_verify(auc_result.outputs["auc_predictions.tsv"], output / "auc_predictions.tsv")
    _copy_or_verify(snapshots["expression"], output / "tpm.tsv")
    _copy_or_verify(snapshots["clinical"], output / "clinical.tsv")
    _copy_or_verify(snapshots["fractions"], output / "fractions.tsv")
    _copy_or_verify(manifest_snapshot, output / "analysis_input_manifest.json")
    summary = {
        "status": "synthetic-analysis-software-demonstration",
        "data_classification": "synthetic",
        "biological_validation": False,
        "cohort_ids": auc_cohort_ids,
        "fraction_rows": len(fraction_table),
        "effect_rows": len(all_effects),
        "synthesis_rows": len(strata_summaries),
        "synthesis_subgroup_rows": len(strata_subgroups),
        "synthesis_strata": list(ANALYSIS_STRATA),
        "endpoint_partitions": [
            {"unit_family": unit_family, "family": family, "definition_id": definition}
            for unit_family, family, definition in endpoint_partitions
        ],
        "correlation_rows": len(all_correlations),
        "correlation_summary_rows": len(correlation_summaries),
        "incremental_auc_rows": len(auc_rows),
        "incremental_auc_method": "SYNTHETIC_WEIGHTED_GEP18_DEMO",
        "incremental_auc_is_published_gep": False,
        "bootstrap": {
            "contract_id": "a_comp_synthetic_demo_v2",
            "draws_in": "R",
            "repetitions": 40,
            "model_refit": False,
            "paired_evaluation": "same sorted sample row indices for baseline and augmented predictions",
        },
        "second_check": {
            "stream": "second_check",
            "reported_only": True,
            "replaced_main_result": False,
            "outcome_based_rerun": False,
            "flag_rule": "flag if either 95% interval endpoint shifts by more than 0.01 AUROC",
        },
        "cibersortx": "not run",
        "input_manifest_sha256": file_sha256(manifest_snapshot),
    }
    _write_json(output / "analysis_summary.json", summary)
    _write_enclosing_manifest(
        output,
        input_manifest_path=output / "analysis_input_manifest.json",
        preflight_report=preflight_report,
        additional_r_manifests=(*extra_r_manifests, auc_result.manifest),
    )
    return summary


def read_tpm_matrix(path: Path, representation: Mapping) -> tuple[list[str], list[str], list[list[float]]]:
    genes: list[str] = []
    matrix: list[list[float]] = []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ACompError("TPM matrix is empty") from None
        if len(header) < 2 or header[0].casefold() not in {"gene", "gene_symbol"}:
            raise ACompError("TPM matrix requires a gene_symbol column and sample columns")
        sample_ids = header[1:]
        for line_number, row in enumerate(reader, 2):
            if len(row) != len(header):
                raise ACompError(f"TPM row {line_number} has the wrong number of values")
            genes.append(row[0])
            try:
                matrix.append([float(value) for value in row[1:]])
            except ValueError:
                raise ACompError(f"TPM row {line_number} contains a non-numeric value") from None
    validate_tpm_matrix(genes=genes, sample_ids=sample_ids, values=matrix, representation=representation)
    return genes, sample_ids, matrix


def _validate_tpm_representation(representation: Mapping, *, allow_invented_source: bool) -> None:
    if not isinstance(representation, Mapping):
        raise ACompError("TPM representation declaration is missing")
    platform = str(representation.get("platform", "")).casefold()
    unit = str(representation.get("unit", "")).casefold()
    transform = str(representation.get("transform", "")).casefold()
    feature_id = str(representation.get("feature_id", "")).casefold()
    if platform != "rnaseq":
        raise ACompError("A-COMP accepts RNA-seq inputs only")
    if unit != "tpm":
        raise ACompError("A-COMP requires TPM input")
    if transform not in {"unlogged", "linear"}:
        raise ACompError("A-COMP requires unlogged linear TPM input")
    if feature_id not in {"gene_symbol", "symbol"}:
        raise ACompError("A-COMP requires gene-symbol feature identifiers")
    if representation.get("full_source") is not True:
        raise ACompError("A-COMP requires a declared full-source TPM representation")
    route_id = str(representation.get("route_id", "")).strip()
    if not route_id:
        raise ACompError("A-COMP requires a declared TPM source route")
    if not allow_invented_source and route_id.startswith("INVENTED_"):
        raise ACompError("real data cannot use an invented TPM source route")


def _require_real_cohort(cohort_id: str) -> None:
    cohort = str(cohort_id).strip()
    if is_locked_study(cohort):
        raise ACompError("IMvigor210 is the locked final test and is refused by A-COMP")
    if cohort not in ALLOWED_COHORTS:
        raise ACompError("real A-COMP input is outside the signed 12-cohort RNA-seq set")


def _run_reference_preflight(output_dir: Path, *, retention_dir: Path) -> dict:
    result = run_r(
        R_SCRIPT,
        {},
        {
            "project_root": str(ROOT),
            "operation": "preflight",
            "expected_outputs": ["reference_report.json"],
        },
        Path(output_dir),
        retention_dir=Path(retention_dir),
    )
    report = _read_json(result.outputs["reference_report.json"], "R reference report")
    report["r_version"] = result.manifest["r_version"]
    report["bioconductor_version"] = result.manifest["bioconductor_version"]
    report["package_versions"] = {
        name: result.manifest["package_versions"].get(name, "")
        for name in EXPECTED_PACKAGE_VERSIONS
    }
    report["_bridge_manifest"] = result.manifest
    return report


def _read_n15_pin(path: Path) -> dict:
    pin_path = Path(path)
    if not pin_path.is_file():
        raise N15PinError("N15 pin document is missing")
    text = pin_path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match is None:
        raise N15PinError("N15 document has no machine-readable JSON pin contract")
    try:
        result = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise N15PinError("N15 JSON pin contract is malformed") from error
    return result


def _validate_signed_pin(pin: Mapping) -> None:
    status = str(pin.get("status", "UNKNOWN"))
    if status != "SIGNED":
        raise N15PinError(f"N15 pin status is {status}; real A-COMP operations require SIGNED")
    signature = pin.get("signature")
    if not isinstance(signature, Mapping) or not signature.get("signed_by") or not signature.get("signed_on"):
        raise N15PinError("N15 signature record is incomplete")
    contract = {
        key: value for key, value in pin.items()
        if key not in {"status", "signature", "contract_sha256"}
    }
    contract_payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    contract_sha256 = hashlib.sha256(contract_payload.encode("utf-8")).hexdigest()
    if pin.get("contract_sha256") != contract_sha256:
        raise N15PinError("N15 contract hash does not match its signed content")
    software = pin.get("software", {})
    if software.get("r") != EXPECTED_R_VERSION or software.get("bioconductor") != EXPECTED_BIOCONDUCTOR_VERSION:
        raise N15PinError("N15 runtime version does not match the locked environment")
    if software.get("packages") != EXPECTED_PACKAGE_VERSIONS:
        raise N15PinError("N15 package versions do not match the locked environment")
    if pin.get("reference_files") != EXPECTED_REFERENCE_SHA256:
        raise N15PinError("N15 reference hashes do not match installed locked files")
    input_policy = pin.get("input_policy", {})
    required_input_policy = {
        "cohorts": list(ALLOWED_COHORTS),
        "platform": "RNA-seq",
        "unit": "TPM",
        "transform": "unlogged linear",
        "feature_id": "HGNC gene symbol",
        "full_source": True,
        "arrays": False,
        "protected_final_test": "refuse",
        "other_platforms": "refuse",
    }
    if input_policy != required_input_policy:
        raise N15PinError("N15 input policy is incomplete or does not match the signed cohort scope")
    method = pin.get("method", {})
    if method != {
        "wrapper": "immunedeconv::deconvolute",
        "method": "quantiseq",
        "signature_matrix": "TIL10",
        "native_method": "lsei",
        "tumor": True,
        "arrays": False,
        "scale_mrna": True,
        "rmgenes": None,
        "rm_genes": None,
        "rna_rm_genes_behavior": "packaged default noisy-gene removal",
        "tumor_exclusions": "packaged aberrant immune-gene list",
    }:
        raise N15PinError("N15 quanTIseq method/options are incomplete")
    qc = pin.get("coverage_qc", {})
    if qc.get("post_exclusion_coverage_floor") != PROPOSED_COVERAGE_FLOOR:
        raise N15PinError("N15 coverage policy does not match the implemented proposal")
    if qc.get("coverage_floor_source") != "project proposal; not a quanTIseq default":
        raise N15PinError("N15 must label the coverage floor as a project proposal")
    if qc.get("fraction_sum_tolerance") != FRACTION_SUM_TOLERANCE:
        raise N15PinError("N15 fraction-sum tolerance does not match the implementation")
    if qc.get("fraction_range_tolerance") != FRACTION_RANGE_TOLERANCE:
        raise N15PinError("N15 fraction-range tolerance does not match the implementation")


def _validate_input_manifest(manifest: Mapping, expression_path: Path, cohort_id: str) -> None:
    if manifest.get("cohort_id") != cohort_id:
        raise ACompError("TPM manifest cohort ID does not match the requested cohort")
    declared_hash = str(manifest.get("expression_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", declared_hash):
        raise ACompError("TPM manifest is missing an expression SHA256")
    if _file_sha256(expression_path) != declared_hash:
        raise ACompError("TPM expression hash mismatch")


def _require_scratch_output(path: Path) -> None:
    scratch = (ROOT / ".scratch").resolve()
    destination = path.expanduser().absolute().resolve()
    if not destination.is_relative_to(scratch):
        raise ACompError("Real A-COMP outputs must be written under repository .scratch/")


def _write_panel_definitions(path: Path) -> None:
    definitions = _panel_definitions(AVAILABLE_PANEL_IDS)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("panel", "gene_symbol"))
        for panel in AVAILABLE_PANEL_IDS:
            for gene in definitions[panel]:
                writer.writerow((panel, gene))


def _cohort_declarations(sample_groups: Sequence[Mapping]) -> list[dict[str, str]]:
    grouped: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in sample_groups:
        study = str(row.get("study_id", ""))
        cancer = str(row.get("cancer", "")).strip().casefold()
        drug_class = str(row.get("drug_class", "")).strip()
        if not study.startswith("invented_") or _known_real_alias(study) or not cancer or not drug_class:
            raise ACompError("Synthetic fixture cohort metadata is incomplete or protected")
        grouped[study].add((cancer, drug_class))
    if not grouped or any(len(values) != 1 for values in grouped.values()):
        raise ACompError("Each synthetic study must have one declared cancer and drug class")
    return [
        {"study_id": study, "cancer": next(iter(values))[0], "drug_class": next(iter(values))[1]}
        for study, values in sorted(grouped.items())
    ]


def _study_correlations(*, study_id, sample_ids, fractions, scores, panel_features) -> list[dict]:
    validate_sample_alignment(
        sample_ids,
        clinical_sample_ids=sample_ids,
        fraction_sample_ids=list(fractions),
        score_sample_ids=sample_ids,
    )
    expected_scores = (*AVAILABLE_PANEL_IDS, "CYT")
    if set(scores) != set(expected_scores):
        raise ACompError("Correlation analysis requires all eleven locked panels and CYT")
    for name, values in scores.items():
        if len(values) != len(sample_ids):
            raise ACompError(f"Score coverage differs from sample order for {name}")
    rows = []
    for cell in FRACTION_CELL_TYPES:
        fraction_values = [float(fractions[sample][cell]) for sample in sample_ids]
        for score_id in expected_scores:
            score_values = scores[score_id]
            details = panel_features.coverage.get(score_id) if score_id in panel_features.coverage else None
            method_id = panel_features.metadata.get("method_id_by_unit", {}).get(score_id, CYT_METHOD_ID if score_id == "CYT" else "")
            if score_id != "CYT" and (details is None or details.get("complete") is not True):
                rows.append({
                    "study": study_id, "cell_type": cell, "score_id": score_id,
                    "score_method_id": method_id, "n": 0, "rho": None,
                    "status": "unavailable_incomplete_fixed_panel_coverage",
                })
                continue
            if any(value is None or not math.isfinite(float(value)) for value in score_values):
                rows.append({
                    "study": study_id, "cell_type": cell, "score_id": score_id,
                    "score_method_id": method_id, "n": 0, "rho": None,
                    "status": "unavailable_nonfinite_or_missing_score",
                })
                continue
            numeric_scores = [float(value) for value in score_values]
            if len(set(numeric_scores)) < 2 or len(set(fraction_values)) < 2:
                rho, status = None, "not_estimable_constant_vector"
            else:
                rho = _spearman(fraction_values, numeric_scores)
                status = "ok" if math.isfinite(rho) else "not_estimable"
                if not math.isfinite(rho):
                    rho = None
            rows.append({
                "study": study_id, "cell_type": cell, "score_id": score_id,
                "score_method_id": method_id, "n": len(sample_ids),
                "rho": rho, "status": status,
            })
    return rows


def _spearman(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute Spearman rho with average ranks for ties, without a new package."""
    if len(left) != len(right) or len(left) < 2:
        raise ACompError("Spearman inputs must have the same length of at least two")

    def average_ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: (values[index], index))
        ranks = [0.0] * len(values)
        position = 0
        while position < len(order):
            end = position + 1
            while end < len(order) and values[order[end]] == values[order[position]]:
                end += 1
            average = ((position + 1) + end) / 2
            for offset in range(position, end):
                ranks[order[offset]] = average
            position = end
        return ranks

    left_ranks = average_ranks(left)
    right_ranks = average_ranks(right)
    left_mean = math.fsum(left_ranks) / len(left_ranks)
    right_mean = math.fsum(right_ranks) / len(right_ranks)
    covariance = math.fsum(
        (left_rank - left_mean) * (right_rank - right_mean)
        for left_rank, right_rank in zip(left_ranks, right_ranks)
    )
    left_sum_squares = math.fsum((rank - left_mean) ** 2 for rank in left_ranks)
    right_sum_squares = math.fsum((rank - right_mean) ** 2 for rank in right_ranks)
    denominator = math.sqrt(left_sum_squares * right_sum_squares)
    return covariance / denominator if denominator else math.nan


def _summarize_correlations(rows: Sequence[Mapping]) -> list[dict]:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row.get("status") == "ok" and row.get("rho") is not None:
            groups[(str(row["cell_type"]), str(row["score_id"]))].append(float(row["rho"]))
    result = []
    for (cell, score), values in sorted(groups.items()):
        ordered = sorted(values)
        middle = len(ordered) // 2
        median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        result.append({
            "cell_type": cell,
            "score_id": score,
            "n_studies": len(values),
            "median_study_rho": median,
            "minimum_study_rho": min(values),
            "maximum_study_rho": max(values),
            "summary_type": "descriptive median and range of within-study correlations; no raw pooling",
        })
    return result


def _write_matrix(path: Path, genes: Sequence[str], sample_ids: Sequence[str], matrix: Sequence[Sequence[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *sample_ids])
        for gene, values in zip(genes, matrix):
            writer.writerow([gene, *values])


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _write_tsv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path, label: str) -> dict:
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ACompError(f"Could not read {label}: {error}") from error
    if not isinstance(result, dict):
        raise ACompError(f"{label} must be a JSON object")
    return result


def _write_json(path: Path, value: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_artifact(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(Path(source).read_bytes())


def _copy_or_verify(source: Path, target: Path) -> None:
    """Publish one verified file without overwriting a conflicting product."""
    source_path = Path(source)
    target_path = Path(target).expanduser().absolute()
    _guard_external_paths({"published artifact": target_path}, data_classification="synthetic")
    if not source_path.is_file() or source_path.is_symlink():
        raise ACompError("A-COMP source product must be a regular file")
    expected = file_sha256(source_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        if target_path.is_symlink() or not target_path.is_file() or file_sha256(target_path) != expected:
            raise ACompError("A-COMP product already exists with different bytes")
        return
    with source_path.open("rb") as input_stream, target_path.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream)
    if file_sha256(target_path) != expected:
        raise ACompError("Published A-COMP product hash differs from its source")


def _public_artifact_hashes(output_dir: Path) -> dict[str, str]:
    """Inventory public files while excluding private snapshots and bridge stages."""
    output = Path(output_dir)
    hashes = {}
    for path in sorted(output.rglob("*")):
        relative = path.relative_to(output)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink():
            raise ACompError("Public A-COMP products cannot be symlinks")
        if path.is_file() and relative.as_posix() != "artifact_manifest.json":
            hashes[relative.as_posix()] = file_sha256(path)
    return hashes


def _source_identity(paths: Sequence[str]) -> dict[str, str]:
    identities = {}
    for relative in paths:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ACompError(f"A-COMP computation identity file is missing or unsafe: {relative}")
        identities[relative] = file_sha256(path)
    return identities


def _r_manifest_identity(manifest: Mapping, *, role: str) -> dict:
    config = manifest.get("config", {})
    operation = str(config.get("operation", role)) if isinstance(config, Mapping) else role
    return {
        "role": role,
        "operation": operation,
        "script": "r/R/a_comp.R",
        "script_sha256": str(manifest.get("script_sha256", "")),
        "config_sha256": canonical_sha256(config),
        "input_sha256": dict(manifest.get("input_sha256", {})),
        "output_sha256": dict(manifest.get("output_sha256", {})),
        "r_version": str(manifest.get("r_version", "")),
        "bioconductor_version": str(manifest.get("bioconductor_version", "")),
        "package_versions": dict(manifest.get("package_versions", {})),
        "manifest_sha256": canonical_sha256(manifest),
    }


def _write_enclosing_manifest(
    output_dir: Path,
    *,
    input_manifest_path: Path,
    preflight_report: Mapping,
    additional_r_manifests: Sequence[Mapping] = (),
    accepted_pin_path: Path | None = None,
) -> dict:
    """Bind declarations, implementation identities, R receipts, and public products."""
    output = Path(output_dir).expanduser().absolute()
    checked = _guard_external_paths(
        {"A-COMP output": output, "input declaration": input_manifest_path},
        data_classification="synthetic",
    )
    if accepted_pin_path is not None:
        checked.update(_guard_external_paths(
            {"accepted N15 pin": accepted_pin_path}, data_classification="synthetic"
        ))
    declaration_manifest = _read_json(checked["input declaration"], "A-COMP input declaration")
    declaration = _verify_synthetic_manifest(
        declaration_manifest, kind=SYNTHETIC_ANALYSIS_MANIFEST_KIND
    )
    if declaration.get("schema") != INPUT_SCHEMA:
        raise ACompError("Artifact manifest requires the supported A-COMP input declaration")

    code_identity = _source_identity((
        "tools/a_comp/core.py",
        "tools/a_comp/__main__.py",
        "r/R/a_comp.R",
        "r/R/bridge.R",
        "r/R/random_streams.R",
        "tools/a_meta/features.py",
        "tools/a_meta/effects.py",
        "tools/a_meta/synthesis.py",
        "tools/a_meta/endpoint_definitions.py",
        "tools/a_meta/provenance.py",
        "tools/a_meta/r_manifest.py",
        "tools/a_scoring/core.py",
        "tools/r_bridge/__init__.py",
    ))
    lock_identity = _source_identity((
        "r/renv.lock",
        "tools/a_dav/requirements-synthetic.txt",
    ))
    bridge_manifest = preflight_report.get("_bridge_manifest", {})
    r_manifests = []
    if isinstance(bridge_manifest, Mapping) and bridge_manifest:
        r_manifests.append(_r_manifest_identity(bridge_manifest, role="reference_preflight"))
    for index, manifest in enumerate(additional_r_manifests, 1):
        r_manifests.append(_r_manifest_identity(manifest, role=f"a_comp_run_{index:02d}"))
    r_packages = dict(preflight_report.get("package_versions", {}))
    report_references = preflight_report.get("reference_files", {})
    if isinstance(report_references, Sequence) and not isinstance(report_references, (str, bytes)):
        report_references = {
            str(row.get("file")): str(row.get("sha256"))
            for row in report_references if isinstance(row, Mapping)
        }
    config = {
        "analysis_strata": list(ANALYSIS_STRATA),
        "fraction_sum_tolerance": FRACTION_SUM_TOLERANCE,
        "fraction_range_tolerance": FRACTION_RANGE_TOLERANCE,
        "proposed_coverage_floor": PROPOSED_COVERAGE_FLOOR,
        "panel_score_method": PANEL_SCORE_METHOD,
        "cyt_method_id": CYT_METHOD_ID,
        "fraction_method_id": FRACTION_METHOD_ID,
        "synthetic_auc_contract": "a_comp_synthetic_demo_v2",
        "synthetic_auc_repetitions": 40,
        "synthetic_auc_primary_seed": 20261110,
        "synthetic_auc_second_check_repetitions": 40,
        "synthetic_auc_second_check_stream": "second_check",
        "synthetic_auc_second_check_task_id": "a_comp_synthetic_demo_v2",
        "synthetic_auc_model_refit": False,
    }
    accepted_pin_sha256 = (
        file_sha256(checked["accepted N15 pin"])
        if accepted_pin_path is not None else None
    )
    manifest = {
        "manifest_schema": "A_COMP_ARTIFACT_MANIFEST_V1",
        "status": "SYNTHETIC_SOFTWARE_EVIDENCE_ONLY",
        "data_classification": "synthetic",
        "biological_validation": False,
        "input_declaration": {
            "kind": str(declaration_manifest.get("kind", "")),
            "sha256": file_sha256(checked["input declaration"]),
            "payload_sha256": str(declaration_manifest.get("payload_sha256", "")),
            "cohort_ids": sorted(str(value) for value in declaration.get("cohort_ids", ())),
            "input_sha256": dict(declaration.get("input_sha256", {})),
            "representation": dict(declaration.get("representation", {})),
            "source_identity": str(declaration.get("representation", {}).get("source_identity", "")),
        },
        "n15": {
            "accepted_pin_sha256": accepted_pin_sha256,
            "proposal_status": "PROPOSED_UNSIGNED",
            "proposal_sha256": file_sha256(N15_PROPOSAL),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "code_sha256": code_identity,
            "lock_sha256": lock_identity,
        },
        "r": {
            "version": str(preflight_report.get("r_version", "")),
            "bioconductor_version": str(preflight_report.get("bioconductor_version", "")),
            "package_versions": r_packages,
            "reference_files": dict(report_references),
            "source_sha256": {
                name: code_identity[name]
                for name in ("r/R/a_comp.R", "r/R/bridge.R", "r/R/random_streams.R")
            },
            "runs": r_manifests,
        },
        "scoring": {
            "cyt_method_id": CYT_METHOD_ID,
            "custom_panel_ids": list(AVAILABLE_PANEL_IDS),
            "custom_panel_scoring": "A-META locked panel scorer",
            "weighted_gep18": "invented synthetic-only score; not the published GEP",
            "scoring_source_sha256": code_identity["tools/a_scoring/core.py"],
        },
        "config": config,
        "config_sha256": canonical_sha256(config),
        "public_products": _public_artifact_hashes(output),
        "private_snapshots_and_bridge_stages": "excluded from public product inventory",
    }
    _write_json(output / "artifact_manifest.json", manifest)
    return manifest


def all_sample_ids_from_groups(rows: Sequence[Mapping]) -> list[str]:
    return [str(row["sample_id"]) for row in rows]


def _study_for_sample(sample_id: str, sample_groups: Sequence[Mapping]) -> str:
    for row in sample_groups:
        if row.get("sample_id") == sample_id:
            return str(row["study_id"])
    raise ACompError("Sample is absent from the synthetic cohort map")
