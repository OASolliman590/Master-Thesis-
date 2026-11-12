"""Outcome-free presentation of the existing Paper A Lin pseudobulk products."""

from __future__ import annotations

import csv
import hashlib
from functools import lru_cache
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np
import pandas as pd


HALLMARK_IFNG = "HALLMARK_INTERFERON_GAMMA_RESPONSE"
SC1_PANEL_IDS = (
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
    HALLMARK_IFNG,
)
BASE_PANEL_IDS = SC1_PANEL_IDS[:-1]
LIN_COMPARTMENTS = (
    "T/NK",
    "B/plasma",
    "myeloid",
    "fibroblast/stromal",
    "endothelial",
    "malignant/epithelial",
)
SAFE_CLINICAL_COLUMNS = (
    "profile_id", "patient_id", "sample_id", "cohort", "study", "cancer",
    "treatment", "compartment", "n_cells", "total_umis", "reason", "library_size",
    "eligible", "status", "baseline",
)
AGGREGATE_COLUMNS = (
    "study", "compartment", "gene", "status", "n_donors", "n_gene_donors",
    "median_log2_cpm_plus1", "q1_log2_cpm_plus1", "q3_log2_cpm_plus1",
    "median_cpm", "median_percent_cells_detected", "detection_limit_tag",
)
QUALITY_COLUMNS = ("cohort", "count_layer", "fractional_values", "assessment")
COMPARTMENT_QC_COLUMNS = ("cohort", "compartment", "profiles", "eligible_donors", "na_profiles")
RESTRICTED_OUTPUT = "pcahawley_per_patient_expression.tsv"
ALLOWED_PRODUCT_CODE = frozenset({
    "r/scripts/sc_lin_pseudobulk.R",
    "r/R/sc_lin.R",
    "tools/sc/cli.py",
    "tools/sc/lin_cohort_map.tsv",
    "tools/sc/lin_compartment_map.tsv",
    "tools/a_scoring/core.py",
})
ALLOWED_PRODUCT_OUTPUTS = {
    "pseudobulk": frozenset({"clinical.tsv", "expression.tsv"}),
    "compartments": frozenset({
        "compartment_expression.tsv", "compartment_qc.tsv", "compartment_dotplot.png",
    }),
    "qc": frozenset({"data_quality.tsv"}),
}


@dataclass(frozen=True)
class LinProducts:
    clinical: pd.DataFrame
    expression: pd.DataFrame
    aggregate_expression: pd.DataFrame
    compartment_qc: pd.DataFrame
    data_quality: pd.DataFrame
    cohort_scope: pd.DataFrame
    source_hashes: pd.DataFrame
    input_sha256: dict[str, str]
    producer_revision: str | None = None


@lru_cache(maxsize=1)
def panel_definitions_for_sc1() -> dict[str, tuple[str, ...]]:
    """Load the signed panels and Hallmark set with only frozen aliases applied."""
    from tools.a_meta.frozen import read_frozen_aliases, read_hallmark_gene_sets
    from tools.a_scoring.core import panel_definitions

    aliases = read_frozen_aliases()
    base = panel_definitions(BASE_PANEL_IDS)
    hallmark = read_hallmark_gene_sets(aliases=aliases)[HALLMARK_IFNG]
    definitions = {
        panel_id: tuple(_canonical_gene(gene, aliases) for gene in base[panel_id])
        for panel_id in BASE_PANEL_IDS
    }
    definitions[HALLMARK_IFNG] = hallmark
    if tuple(definitions) != SC1_PANEL_IDS or any(
        len(members) != len(set(members)) for members in definitions.values()
    ):
        raise ValueError("Signed SC-1 panel membership is malformed")
    return definitions


def _canonical_gene(gene: str, aliases: dict[str, str]) -> str:
    current = str(gene)
    seen = set()
    while current in aliases:
        if current in seen:
            raise ValueError("Frozen gene aliases contain a cycle")
        seen.add(current)
        current = str(aliases[current])
    return current


def _apply_frozen_gene_aliases(expression: pd.DataFrame) -> pd.DataFrame:
    from tools.a_meta.frozen import read_frozen_aliases

    aliases = read_frozen_aliases()
    expression = expression.copy()
    original = expression.index.astype(str)
    mapped = [_canonical_gene(gene, aliases) for gene in original]
    if len(mapped) != len(set(mapped)):
        raise ValueError("SC expression identities collide after frozen gene alias resolution")
    expression.index = mapped
    return expression


def _canonical_gene_names(genes) -> list[str]:
    from tools.a_meta.frozen import read_frozen_aliases

    aliases = read_frozen_aliases()
    return [_canonical_gene(str(gene), aliases) for gene in genes]


def _reject_protected_path(path: Path | str) -> None:
    raw = str(path)
    original = Path(path).expanduser()
    candidates = (raw, str(original.absolute()), str(original.resolve(strict=False)))
    for candidate in candidates:
        for component in re.split(r"[\\/]+", candidate):
            token = re.sub(r"[^a-z0-9]", "", component.casefold())
            if "imvigor210" in token or "ingestionpacketjson" in token:
                raise ValueError("SC product paths cannot reference forbidden protected paths")


def _reject_symlink_components(path: Path | str) -> Path:
    _reject_protected_path(path)
    original = Path(path).expanduser()
    if not original.is_absolute():
        original = Path.cwd() / original
    current = Path(original.anchor)
    for part in original.parts[1:]:
        if part in {"", "."}:
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            raise ValueError(f"SC product paths cannot contain symlinks: {current.name}")
    return original


def _normalized_manifest_name(value: object) -> str:
    original = str(value)
    posix = PurePosixPath(original.replace("\\", "/"))
    windows = PureWindowsPath(original)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        raise ValueError("SC-1 manifest paths must be relative and cannot traverse directories")
    normalized = posix.as_posix().casefold()
    return normalized.removeprefix("./")


def _is_restricted_output(value: object, resolved_path: Path | None = None) -> bool:
    normalized = _normalized_manifest_name(value)
    if PurePosixPath(normalized).name == RESTRICTED_OUTPUT.casefold():
        return True
    return resolved_path is not None and resolved_path.name.casefold() == RESTRICTED_OUTPUT.casefold()


def _sha256(path: Path) -> str:
    _reject_symlink_components(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_producer_revision(revision: str) -> str:
    """Accept only a full immutable commit ID present in the local repository."""
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise ValueError("SC-1 producer revision must be a full 40-character commit ID")
    repository = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            [
                "git", "--no-replace-objects", "-C", str(repository), "rev-parse", "--verify", "--end-of-options",
                f"{revision}^{{commit}}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("SC-1 producer revision is absent or does not resolve to a commit") from error
    resolved = result.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", resolved) or resolved != revision.lower():
        raise ValueError("SC-1 producer revision must resolve to the exact immutable commit ID")
    return resolved


def _git_blob_sha256(revision: str, code_name: str) -> str:
    """Hash an allowlisted code blob through read-only Git object access."""
    if code_name not in ALLOWED_PRODUCT_CODE:
        raise ValueError("SC-1 producer blob is outside the allowed A product code set")
    repository = Path(__file__).resolve().parents[2]
    try:
        tree_entry = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repository), "ls-tree", "-z", revision, "--", code_name],
            check=True,
            capture_output=True,
        ).stdout
        entries = [entry for entry in tree_entry.split(b"\0") if entry]
        if len(entries) != 1:
            raise ValueError(f"SC-1 producer revision is missing allowlisted source blob: {code_name}")
        metadata, path = entries[0].split(b"\t", 1)
        mode, object_type, _object_id = metadata.decode("ascii").split()
        if path.decode("utf-8") != code_name or mode not in {"100644", "100755"} or object_type != "blob":
            raise ValueError(f"SC-1 producer source is not a regular allowlisted blob: {code_name}")
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repository), "cat-file", "blob", f"{revision}:{code_name}"],
            check=True,
            capture_output=True,
        )
    except ValueError:
        raise
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"SC-1 producer revision is missing allowlisted source blob: {code_name}") from error
    return hashlib.sha256(result.stdout).hexdigest()


def _validate_artifact_manifest(
    manifest_path: Path,
    *,
    atlas: str,
    paper: str,
    unit: str | None = None,
    profile_thresholds: bool = False,
    thresholds: bool = False,
    required_outputs: tuple[str, ...] = (),
    allowed_outputs: frozenset[str] | None = None,
    producer_revision: str | None = None,
    verified_code_hashes: dict[str, str] | None = None,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    _reject_symlink_components(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid SC-1 product manifest: {manifest_path.name}") from error
    if manifest.get("atlas") != atlas or manifest.get("paper") != paper:
        raise ValueError(f"SC-1 product atlas/paper mismatch in {manifest_path.parent.name}")
    if unit and manifest.get("unit") != unit:
        raise ValueError(f"SC-1 product unit mismatch in {manifest_path.parent.name}")
    if profile_thresholds and (
        manifest.get("minimum_cells") != 15 or manifest.get("minimum_umis") != 5_000
    ):
        raise ValueError(f"SC-1 profile thresholds differ from the signed rules in {manifest_path.parent.name}")
    if thresholds and (
        manifest.get("minimum_cells") != 15
        or manifest.get("minimum_umis") != 5_000
        or manifest.get("minimum_donors_to_show") != 5
    ):
        raise ValueError(f"SC-1 source thresholds differ from the signed rules in {manifest_path.parent.name}")
    inputs = manifest.get("input_sha256")
    if not isinstance(inputs, dict) or not inputs or any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in inputs.values()
    ):
        raise ValueError(f"SC-1 product input hashes are invalid in {manifest_path.parent.name}")
    code = manifest.get("code", [])
    if not isinstance(code, list) or not code:
        raise ValueError(f"SC-1 product code hashes are missing in {manifest_path.parent.name}")
    code_names = set()
    for reference in code:
        if not isinstance(reference, dict):
            raise ValueError("SC-1 code references must be named product code files")
        relative = Path(str(reference.get("path", "")))
        expected = str(reference.get("sha256", ""))
        code_name = relative.as_posix()
        if (
            relative.is_absolute() or ".." in relative.parts
            or code_name not in ALLOWED_PRODUCT_CODE
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            raise ValueError("SC-1 code references must use the allowed A product files and SHA256 hashes")
        if code_name in code_names:
            raise ValueError("SC-1 product code references must be unique")
        code_names.add(code_name)
        source = Path(__file__).resolve().parents[2] / relative
        _reject_symlink_components(source)
        if producer_revision is None:
            actual_code_hash = _sha256(source) if source.is_file() else ""
        else:
            if verified_code_hashes is not None and code_name in verified_code_hashes:
                actual_code_hash = verified_code_hashes[code_name]
            else:
                try:
                    actual_code_hash = _git_blob_sha256(producer_revision, code_name)
                except ValueError as error:
                    raise ValueError(f"SC-1 code hash is stale or unverifiable: {relative.as_posix()}") from error
                if verified_code_hashes is not None:
                    verified_code_hashes[code_name] = actual_code_hash
        if actual_code_hash != expected:
            raise ValueError(f"SC-1 code hash is stale or unverifiable: {relative.as_posix()}")
    if code_names != ALLOWED_PRODUCT_CODE:
        raise ValueError("SC-1 code references do not cover the allowed A product implementation set")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or not set(required_outputs).issubset(outputs):
        raise ValueError(f"SC-1 product output hashes are missing in {manifest_path.parent.name}")

    def reject_absolute_values(value: Any, key: str = "") -> None:
        if key in {"script_path", "r_library", "config", "session_info"}:
            raise ValueError("SC-1 published manifests cannot contain runtime paths or session details")
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                reject_absolute_values(child_value, str(child_key))
        elif isinstance(value, list):
            for item in value:
                reject_absolute_values(item, key)
        elif isinstance(value, str) and value.startswith("/"):
            raise ValueError("SC-1 published manifests cannot contain absolute paths")

    reject_absolute_values(manifest)
    hashed_outputs: list[dict[str, str]] = []
    for name, expected in outputs.items():
        normalized = _normalized_manifest_name(name)
        if _is_restricted_output(name):
            continue
        if normalized not in (allowed_outputs or frozenset()):
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise ValueError("SC-1 allowed output hashes must be SHA256 values")
        output = manifest_path.parent / normalized
        _reject_symlink_components(output)
        if _is_restricted_output(name, output.resolve(strict=False)):
            raise ValueError("SC-1 output path resolves to a restricted Paper B product")
        if not output.is_file() or _sha256(output) != expected:
            raise ValueError(f"SC-1 product output hash mismatch: {manifest_path.parent.name}/{name}")
        hashed_outputs.append({"source": f"{manifest_path.parent.name}/{normalized}", "sha256": str(expected)})
    hashed_outputs.append({
        "source": f"{manifest_path.parent.name}/manifest.json",
        "sha256": _sha256(manifest_path),
    })
    return {str(key): str(value) for key, value in inputs.items()}, hashed_outputs


def _read_expression_profiles(path: Path, profile_ids: list[str]) -> pd.DataFrame:
    _reject_symlink_components(path)
    with path.open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream, delimiter="\t"), [])
    if not header or header[0] != "gene" or len(header) != len(set(header)):
        raise ValueError(f"SC-1 expression header is invalid in {path.parent.name}")
    if not set(profile_ids).issubset(header[1:]):
        raise ValueError(f"SC-1 expression columns do not cover safe profiles in {path.parent.name}")
    selected_columns = ["gene", *profile_ids]
    expression = pd.read_csv(
        path, sep="\t", usecols=selected_columns, index_col="gene", na_values=["NA"],
    )
    expression = expression.loc[:, profile_ids]
    if expression.index.astype(str).duplicated().any():
        raise ValueError(f"SC-1 expression gene identities are duplicated in {path.parent.name}")
    return _apply_frozen_gene_aliases(expression)


def read_lin_products(
    atlas_dir: Path | str,
    *,
    producer_revision: str | None = None,
) -> LinProducts:
    """Read checked Paper A products with explicit outcome-free clinical columns."""
    atlas_dir = _reject_symlink_components(Path(atlas_dir).expanduser())
    if atlas_dir.name != "sc_lin2026":
        raise ValueError("SC-1 presentation accepts only the Paper A Lin atlas product directory")
    if producer_revision is not None:
        producer_revision = _resolve_producer_revision(producer_revision)
    verified_code_hashes: dict[str, str] = {}
    cohort_scope_path = Path(__file__).resolve().parents[2] / "docs/cohorts/SINGLE_CELL_LIN2026_COHORTS.tsv"
    cohort_scope = pd.read_csv(
        cohort_scope_path, sep="\t", usecols=["cohort", "paper_A_SC1"], dtype=str,
    )
    cohort_scope = cohort_scope[cohort_scope["paper_A_SC1"].str.strip().str.casefold().eq("yes")].copy()
    if cohort_scope["cohort"].duplicated().any():
        raise ValueError("SC-1 signed cohort scope contains duplicate studies")
    map_path = Path(__file__).with_name("lin_cohort_map.tsv")
    cancer_map = pd.read_csv(map_path, sep="\t", usecols=["cohort", "cancer"], dtype=str)
    cohort_scope = cohort_scope.merge(cancer_map, on="cohort", how="left", validate="one_to_one")
    if cohort_scope["cancer"].isna().any():
        raise ValueError("SC-1 cohort cancer metadata are incomplete")

    clinical_parts: list[pd.DataFrame] = []
    expression_parts: list[pd.DataFrame] = []
    input_identity: dict[str, str] | None = None
    output_hashes: list[dict[str, str]] = []
    seen_profiles: set[str] = set()
    pseudobulk_root = atlas_dir / "pseudobulk"
    for compartment in LIN_COMPARTMENTS:
        slug = re.sub(r"[^a-z0-9]+", "_", compartment.casefold()).strip("_")
        directory = pseudobulk_root / slug
        clinical_path = directory / "clinical.tsv"
        expression_path = directory / "expression.tsv"
        manifest_path = directory / "manifest.json"
        for path in (clinical_path, expression_path, manifest_path):
            _reject_symlink_components(path)
        if not all(path.is_file() for path in (clinical_path, expression_path, manifest_path)):
            raise FileNotFoundError(f"SC-1 pseudobulk products are incomplete for {compartment}")
        inputs, hashed = _validate_artifact_manifest(
            manifest_path,
            atlas="lin2026_atlas",
            paper="A",
            unit="patient",
            profile_thresholds=True,
            thresholds=False,
            required_outputs=("clinical.tsv", "expression.tsv"),
            allowed_outputs=ALLOWED_PRODUCT_OUTPUTS["pseudobulk"],
            producer_revision=producer_revision,
            verified_code_hashes=verified_code_hashes,
        )
        if input_identity is None:
            input_identity = inputs
        elif inputs != input_identity:
            raise ValueError("SC-1 pseudobulk manifests do not share one input identity")
        output_hashes.extend(hashed)
        clinical = pd.read_csv(
            clinical_path,
            sep="\t",
            usecols=list(SAFE_CLINICAL_COLUMNS),
            dtype=str,
            keep_default_na=False,
        )
        if clinical["profile_id"].astype(str).duplicated().any():
            raise ValueError(f"SC-1 clinical profile IDs are duplicated for {compartment}")
        if not clinical["compartment"].astype(str).eq(compartment).all():
            raise ValueError(f"SC-1 clinical compartment differs from its product directory: {compartment}")
        if not clinical["study"].astype(str).eq(clinical["cohort"].astype(str)).all():
            raise ValueError(f"SC-1 cohort and study metadata disagree for {compartment}")
        profile_ids = clinical["profile_id"].astype(str).tolist()
        expression = _read_expression_profiles(expression_path, profile_ids)
        duplicate_profiles = seen_profiles.intersection(profile_ids)
        if duplicate_profiles:
            raise ValueError("An SC-1 profile occurs in more than one compartment")
        seen_profiles.update(profile_ids)
        clinical_parts.append(clinical)
        expression_parts.append(expression)

    clinical = pd.concat(clinical_parts, ignore_index=True, sort=False)
    clinical = clinical[clinical["cohort"].isin(set(cohort_scope["cohort"]))].copy()
    cancer_by_cohort = cohort_scope.set_index("cohort")["cancer"].to_dict()
    clinical["cancer_from_catalog"] = clinical["cohort"].map(cancer_by_cohort)
    if clinical["cancer_from_catalog"].isna().any() or not (
        clinical["cancer"].astype(str) == clinical["cancer_from_catalog"].astype(str)
    ).all():
        raise ValueError("SC-1 clinical cancer metadata differ from the signed cohort catalog")
    if clinical[["cohort", "patient_id", "sample_id"]].astype(str).eq("").any().any():
        raise ValueError("SC-1 clinical patient/specimen metadata are incomplete")
    patient_samples = clinical.groupby(["cohort", "patient_id"], dropna=False)["sample_id"].nunique()
    if (patient_samples > 1).any():
        raise ValueError("SC-1 requires one baseline specimen per patient and study")
    ordered_profile_ids = clinical["profile_id"].astype(str).tolist()
    expression = pd.concat(expression_parts, axis=1, sort=False)
    expression = expression.loc[:, ordered_profile_ids]

    compartments_dir = atlas_dir / "compartments"
    compartments_manifest = compartments_dir / "manifest.json"
    for path in (
        compartments_manifest,
        compartments_dir / "compartment_expression.tsv",
        compartments_dir / "compartment_qc.tsv",
    ):
        _reject_symlink_components(path)
    compartment_inputs, aggregate_hashes = _validate_artifact_manifest(
        compartments_manifest,
        atlas="lin2026_atlas", paper="A", unit="patient", thresholds=True,
        required_outputs=("compartment_expression.tsv", "compartment_qc.tsv"),
        allowed_outputs=ALLOWED_PRODUCT_OUTPUTS["compartments"],
        producer_revision=producer_revision,
        verified_code_hashes=verified_code_hashes,
    )
    if compartment_inputs != input_identity:
        raise ValueError("SC-1 aggregate and pseudobulk products do not share one input identity")
    output_hashes.extend(aggregate_hashes)
    aggregate = pd.read_csv(
        compartments_dir / "compartment_expression.tsv",
        sep="\t", usecols=list(AGGREGATE_COLUMNS), dtype={"study": str, "compartment": str, "gene": str},
    )
    aggregate["gene"] = _canonical_gene_names(aggregate["gene"].astype(str))
    compartment_qc = pd.read_csv(
        compartments_dir / "compartment_qc.tsv",
        sep="\t", usecols=list(COMPARTMENT_QC_COLUMNS), dtype={"cohort": str, "compartment": str},
    )
    qc_dir = atlas_dir / "qc"
    qc_manifest = qc_dir / "manifest.json"
    _reject_symlink_components(qc_manifest)
    _reject_symlink_components(qc_dir / "data_quality.tsv")
    qc_inputs, quality_hashes = _validate_artifact_manifest(
        qc_manifest, atlas="lin2026_atlas", paper="A",
        required_outputs=("data_quality.tsv",),
        allowed_outputs=ALLOWED_PRODUCT_OUTPUTS["qc"],
        producer_revision=producer_revision,
        verified_code_hashes=verified_code_hashes,
    )
    if qc_inputs != input_identity:
        raise ValueError("SC-1 raw-count QC and pseudobulk products do not share one input identity")
    output_hashes.extend(quality_hashes)
    data_quality = pd.read_csv(
        qc_dir / "data_quality.tsv", sep="\t", usecols=list(QUALITY_COLUMNS), dtype=str,
    )
    return LinProducts(
        clinical=clinical.drop(columns=["cancer_from_catalog"]),
        expression=expression,
        aggregate_expression=aggregate,
        compartment_qc=compartment_qc,
        data_quality=data_quality,
        cohort_scope=cohort_scope,
        source_hashes=pd.DataFrame(output_hashes, columns=["source", "sha256"]),
        input_sha256=input_identity or {},
        producer_revision=producer_revision,
    )


def _truthy(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().casefold() in {"true", "1", "yes"}


def _ici_only(treatment: str) -> bool:
    from .sc3 import _drug_class

    return _drug_class(str(treatment)) in {"ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4"}


def _profile_groups(clinical: pd.DataFrame, expression: pd.DataFrame):
    protected = {"response", "response_metric", "outcome_label", "endpoint_family", "res_metric"}
    if protected & set(clinical.columns):
        raise ValueError("SC-1 presentation clinical input includes protected outcome columns")
    required = {
        "profile_id", "patient_id", "sample_id", "cohort", "cancer", "compartment",
        "treatment", "baseline", "eligible", "status", "reason", "n_cells", "total_umis",
        "library_size",
    }
    missing = required - set(clinical.columns)
    if missing:
        raise ValueError(f"SC-1 presentation clinical input is missing safe metadata: {sorted(missing)}")
    frame = clinical.copy()
    for column in ("profile_id", "patient_id", "sample_id", "cohort", "compartment"):
        frame[column] = frame[column].astype("string").fillna("").str.strip()
        if frame[column].eq("").any():
            raise ValueError(f"SC-1 presentation requires non-empty {column} values")
    if frame["profile_id"].duplicated().any():
        raise ValueError("SC-1 presentation profile IDs must be unique")
    if expression.index.astype(str).duplicated().any() or expression.columns.astype(str).duplicated().any():
        raise ValueError("SC-1 presentation expression identities must be unique")
    profile_ids = frame["profile_id"].astype(str).tolist()
    if list(expression.columns.astype(str)) != profile_ids:
        raise ValueError("SC-1 expression columns do not align with safe clinical profiles")
    samples = frame.groupby(["cohort", "patient_id"], dropna=False)["sample_id"].nunique()
    if (samples > 1).any():
        raise ValueError("SC-1 presentation requires one baseline specimen per patient and study")
    frame["eligible"] = frame["eligible"].map(_truthy)
    frame["baseline"] = frame["baseline"].map(_truthy)
    for column in ("n_cells", "total_umis", "library_size"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["treatment"] = frame["treatment"].astype("string").fillna("")
    if (~frame["baseline"]).any():
        raise ValueError("SC-1 presentation products must contain baseline profiles only")
    if (~frame["treatment"].map(_ici_only)).any():
        raise ValueError("SC-1 presentation products must contain ICI-only profiles")
    valid = frame[frame["eligible"]]
    if (
        valid["n_cells"].isna().any()
        or valid["total_umis"].isna().any()
        or valid["library_size"].isna().any()
        or (valid["n_cells"] < 15).any()
        or (valid["total_umis"] < 5_000).any()
        or (valid["library_size"] < 5_000).any()
    ):
        raise ValueError("Eligible SC-1 profiles do not meet the signed 15-cell/5,000-UMI thresholds")
    return frame


def summarize_profiles(clinical: pd.DataFrame, expression: pd.DataFrame) -> pd.DataFrame:
    """Summarize supported donor profiles without averaging gene-level medians."""
    frame = _profile_groups(clinical, expression)
    definitions = panel_definitions_for_sc1()
    focused = {
        gene: panel_id
        for panel_id in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
        for gene in definitions[panel_id]
    }
    expression = _apply_frozen_gene_aliases(expression)
    expression.index = expression.index.astype(str)
    expression.columns = expression.columns.astype(str)
    numeric = expression.apply(pd.to_numeric, errors="raise")
    records: list[dict] = []

    for (study, cancer, compartment), profiles in frame.groupby(
        ["cohort", "cancer", "compartment"], dropna=False, sort=True
    ):
        eligible = profiles[profiles["eligible"]].copy()
        if eligible["patient_id"].duplicated().any():
            raise ValueError("SC-1 summaries require one eligible profile per patient and compartment")
        profile_ids = eligible["profile_id"].astype(str).tolist()
        library_sizes = eligible["library_size"].to_numpy(dtype=float)
        donor_ids = eligible["patient_id"].astype(str).tolist()

        def append_record(
            *, unit_id: str, unit_type: str, gene_group: str, method_id: str,
            values: list[tuple[str, float, float]], n_members_total: int,
            member_support: list[int], n_members_available: int, reason: str = "",
        ) -> None:
            support = len(values)
            if not len(profiles):
                status, reason = "not_assessed", "no_source_profiles_for_compartment"
            elif eligible.empty:
                source_reasons = sorted({str(value) for value in profiles["reason"] if str(value)})
                status = "not_assessed"
                reason = ";".join(source_reasons) or "no_eligible_source_profiles"
            elif reason == "panel_member_availability_below_80_percent":
                status = "not_assessed"
            elif n_members_available == 0:
                status, reason = "not_assessed", reason or "all_members_missing_from_source_layer"
            elif support == 0:
                status, reason = "not_assessed", reason or "no_measured_donors_in_source_layer"
            elif support < 5:
                status, reason = "insufficient_donors", reason or "fewer_than_five_measured_donors"
            else:
                status, reason = "shown", ""
            log_values = [item[1] for item in values]
            cpm_values = [item[2] for item in values]
            records.append({
                "study": str(study),
                "cancer": str(cancer),
                "compartment": str(compartment),
                "unit_id": unit_id,
                "unit_type": unit_type,
                "gene_group": gene_group,
                "method_id": method_id,
                "n_profiles": int(len(profiles)),
                "n_eligible_donors": int(eligible["patient_id"].nunique()),
                "n_donors_support": int(support),
                "n_members_available_global": int(n_members_available),
                "n_members_total": int(n_members_total),
                "member_availability": f"{n_members_available}/{n_members_total}",
                "member_support_min": min(member_support) if member_support else np.nan,
                "member_support_max": max(member_support) if member_support else np.nan,
                "median_log2_cpm_plus1": float(np.median(log_values)) if log_values else np.nan,
                "q1_log2_cpm_plus1": float(np.quantile(log_values, 0.25)) if log_values else np.nan,
                "q3_log2_cpm_plus1": float(np.quantile(log_values, 0.75)) if log_values else np.nan,
                "median_cpm": float(np.median(cpm_values)) if cpm_values else np.nan,
                "median_percent_cells_detected": np.nan,
                "detection_limit_tag": "not_assessed",
                "status": status,
                "reason": reason,
            })

        for panel_id in SC1_PANEL_IDS:
            members = definitions[panel_id]
            available = [gene for gene in members if gene in numeric.index]
            required_members = math.ceil(0.8 * len(members))
            member_support: list[int] = []
            donor_values: list[tuple[str, float, float]] = []
            for donor, profile_id, library_size in zip(donor_ids, profile_ids, library_sizes, strict=True):
                values = []
                for gene in available:
                    count = numeric.at[gene, profile_id]
                    if pd.isna(count):
                        continue
                    if not np.isfinite(count) or count < 0 or count != math.floor(count):
                        raise ValueError("Eligible SC-1 profiles must contain non-negative integer UMI sums")
                    cpm = float(count) / library_size * 1_000_000.0
                    values.append(float(np.log2(cpm + 1.0)))
                member_support.append(len(values))
                if len(values) >= required_members:
                    donor_values.append((donor, float(np.mean(values)), float("nan")))
            global_reason = ""
            if len(available) < required_members:
                global_reason = "panel_member_availability_below_80_percent"
                donor_values = []
            append_record(
                unit_id=panel_id,
                unit_type="panel",
                gene_group="",
                method_id=f"CUSTOM_MEAN_{panel_id}",
                values=donor_values,
                n_members_total=len(members),
                member_support=member_support,
                n_members_available=len(available),
                reason=global_reason,
            )

        for gene, panel_id in focused.items():
            gene_values: list[tuple[str, float, float]] = []
            for donor, profile_id, library_size in zip(donor_ids, profile_ids, library_sizes, strict=True):
                if gene not in numeric.index:
                    continue
                count = numeric.at[gene, profile_id]
                if pd.isna(count):
                    continue
                if not np.isfinite(count) or count < 0 or count != math.floor(count):
                    raise ValueError("Eligible SC-1 profiles must contain non-negative integer UMI sums")
                cpm = float(count) / library_size * 1_000_000.0
                gene_values.append((donor, float(np.log2(cpm + 1.0)), cpm))
            append_record(
                unit_id=gene,
                unit_type="gene",
                gene_group="M5" if panel_id == "M5_CHECKPOINT_CANDIDATES" else "M6",
                method_id="GENE_STUDY_SCALE",
                values=gene_values,
                n_members_total=1,
                member_support=[int(gene in numeric.index and not pd.isna(numeric.at[gene, profile_id]))
                                for profile_id in profile_ids],
                n_members_available=int(gene in numeric.index),
                reason="gene_missing_from_source_layer" if gene not in numeric.index else "",
            )

    result = pd.DataFrame.from_records(records)
    if result.empty:
        return result
    for (_, gene), rows in result[result["unit_type"].eq("gene")].groupby(["study", "unit_id"]):
        assessed = rows[rows["status"].eq("shown")]
        if assessed.empty:
            tag = "not_assessed"
        elif (assessed["median_cpm"] < 50).all():
            tag = "below_scRNA_detection_limit"
        else:
            tag = "measured_at_or_above_detection_limit"
        result.loc[rows.index, "detection_limit_tag"] = tag
    return result


def _empty_summary_row(study: str, cancer: str, compartment: str, unit_id: str,
                       unit_type: str, gene_group: str, method_id: str) -> dict:
    return {
        "study": study, "cancer": cancer, "compartment": compartment, "unit_id": unit_id,
        "unit_type": unit_type, "gene_group": gene_group, "method_id": method_id,
        "n_profiles": 0, "n_eligible_donors": 0, "n_donors_support": 0,
        "n_members_available_global": np.nan,
        "n_members_total": len(panel_definitions_for_sc1()[unit_id]) if unit_type == "panel" else 1,
        "member_availability": "not_assessed", "member_support_min": np.nan,
        "member_support_max": np.nan, "median_log2_cpm_plus1": np.nan,
        "q1_log2_cpm_plus1": np.nan, "q3_log2_cpm_plus1": np.nan,
        "median_cpm": np.nan, "median_percent_cells_detected": np.nan,
        "detection_limit_tag": "not_assessed", "status": "not_assessed",
        "reason": "no_source_profiles_for_compartment",
    }


def _complete_summary_grid(summary: pd.DataFrame, products: LinProducts) -> pd.DataFrame:
    definitions = panel_definitions_for_sc1()
    rows = summary.to_dict(orient="records")
    existing = set(zip(summary.get("study", ()), summary.get("compartment", ())))
    for cohort in products.cohort_scope.itertuples(index=False):
        for compartment in LIN_COMPARTMENTS:
            if (cohort.cohort, compartment) in existing:
                continue
            for panel_id in SC1_PANEL_IDS:
                rows.append(_empty_summary_row(
                    cohort.cohort, cohort.cancer, compartment, panel_id,
                    "panel", "", f"CUSTOM_MEAN_{panel_id}",
                ))
            for panel_id in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS"):
                for gene in definitions[panel_id]:
                    rows.append(_empty_summary_row(
                        cohort.cohort, cohort.cancer, compartment, gene, "gene",
                        "M5" if panel_id == "M5_CHECKPOINT_CANDIDATES" else "M6",
                        "GENE_STUDY_SCALE",
                    ))
    result = pd.DataFrame.from_records(rows)
    expected_units = set(SC1_PANEL_IDS) | {
        gene for panel in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
        for gene in definitions[panel]
    }
    if set(result["unit_id"].astype(str)) != expected_units:
        raise ValueError("SC-1 presentation units differ from the signed panels and M5/M6 genes")
    if result.duplicated(["study", "compartment", "unit_id"]).any():
        raise ValueError("SC-1 presentation has duplicate study/compartment/unit rows")
    return result


def _verify_aggregate_gene_summaries(summary: pd.DataFrame, products: LinProducts) -> pd.DataFrame:
    genes = summary[summary["unit_type"].eq("gene")].copy()
    aggregates = products.aggregate_expression
    if aggregates.duplicated(["study", "compartment", "gene"]).any():
        raise ValueError("SC-1 aggregate gene table has duplicate study/compartment/gene rows")
    for index, row in genes.iterrows():
        if int(row["n_profiles"]) == 0:
            continue
        match = aggregates[
            aggregates["study"].astype(str).eq(str(row["study"]))
            & aggregates["compartment"].astype(str).eq(str(row["compartment"]))
            & aggregates["gene"].astype(str).eq(str(row["unit_id"]))
        ]
        if len(match) != 1:
            raise ValueError(f"Existing SC-1 aggregate is missing {row['study']}/{row['compartment']}/{row['unit_id']}")
        observed = match.iloc[0]
        if int(observed["n_gene_donors"]) != int(row["n_donors_support"]):
            raise ValueError("Existing SC-1 aggregate donor support differs from raw pseudobulk profiles")
        if int(observed["n_donors"]) != int(row["n_eligible_donors"]):
            raise ValueError("Existing SC-1 aggregate compartment donor support differs from pseudobulk profiles")
        if row["status"] == "shown":
            for column in ("median_log2_cpm_plus1", "q1_log2_cpm_plus1", "q3_log2_cpm_plus1", "median_cpm"):
                expected = float(row[column])
                actual = float(observed[column])
                if not np.isclose(expected, actual, rtol=1e-7, atol=1e-8):
                    raise ValueError(f"Existing SC-1 aggregate {column} differs for {row['unit_id']}")
        genes.loc[index, "median_percent_cells_detected"] = observed["median_percent_cells_detected"]
        genes.loc[index, "aggregate_gene_status"] = str(observed["status"])
    panel = summary[summary["unit_type"].eq("panel")].copy()
    return pd.concat([panel, genes], ignore_index=True, sort=False)


def _validate_compartment_qc(products: LinProducts) -> pd.DataFrame:
    clinical = products.clinical.copy()
    clinical["eligible"] = clinical["eligible"].map(_truthy)
    computed: dict[tuple[str, str], tuple[int, int]] = {}
    for key, frame in clinical.groupby(["cohort", "compartment"], dropna=False):
        computed[(str(key[0]), str(key[1]))] = (
            len(frame), int(frame.loc[frame["eligible"], "patient_id"].nunique())
        )
    qc = products.compartment_qc.copy()
    qc = qc[qc["cohort"].isin(set(products.cohort_scope["cohort"]))]
    if qc.duplicated(["cohort", "compartment"]).any():
        raise ValueError("SC-1 compartment QC contains duplicate study/compartment rows")
    missing = set((cohort, compartment) for cohort in products.cohort_scope["cohort"]
                  for compartment in LIN_COMPARTMENTS) - set(zip(qc["cohort"], qc["compartment"]))
    if missing:
        raise ValueError("SC-1 compartment QC is missing a signed cohort/compartment row")
    for row in qc.itertuples(index=False):
        expected_profiles, expected_donors = computed.get((str(row.cohort), str(row.compartment)), (0, 0))
        if int(row.profiles) != expected_profiles or int(row.eligible_donors) != expected_donors:
            raise ValueError(f"SC-1 compartment QC does not align for {row.cohort}/{row.compartment}")
    return qc


def _cell_support_table(products: LinProducts) -> pd.DataFrame:
    clinical = products.clinical.copy()
    clinical["eligible"] = clinical["eligible"].map(_truthy)
    clinical["n_cells"] = pd.to_numeric(clinical["n_cells"], errors="coerce")
    rows = []
    for (study, compartment), frame in clinical[clinical["eligible"]].groupby(
        ["cohort", "compartment"], sort=True
    ):
        values = frame["n_cells"].dropna().to_numpy(dtype=float)
        rows.append({
            "study": str(study), "compartment": str(compartment),
            "cells_per_donor_median": float(np.median(values)),
            "cells_per_donor_q1": float(np.quantile(values, 0.25)),
            "cells_per_donor_q3": float(np.quantile(values, 0.75)),
        })
    return pd.DataFrame(rows)


def _quality_by_cohort(products: LinProducts) -> dict[str, tuple[str, str]]:
    quality = products.data_quality.copy()
    selected = quality[quality["count_layer"].astype(str).eq("ALL")]
    if selected["cohort"].duplicated().any():
        raise ValueError("SC-1 source QC contains duplicate cohort summary rows")
    result: dict[str, tuple[str, str]] = {}
    for row in selected.itertuples(index=False):
        count = int(row.fractional_values)
        assessment = str(row.assessment)
        if count > 0:
            result[str(row.cohort)] = (assessment, "non_integer_or_invalid_raw_counts")
        else:
            result[str(row.cohort)] = ("no_fractional_stored_values_detected", "")
    return result


def _is_unverified_head_neck(value: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")
    return normalized == "head_and_neck"


def _block_unverified_head_neck_display(summary: pd.DataFrame) -> pd.DataFrame:
    result = summary.copy()
    unresolved = result["cancer"].map(_is_unverified_head_neck)
    result.loc[unresolved, "status"] = "not_assessed"
    result.loc[unresolved, "reason"] = "source_check_pending"
    for column in (
        "median_log2_cpm_plus1", "q1_log2_cpm_plus1", "q3_log2_cpm_plus1", "median_cpm",
        "median_percent_cells_detected",
    ):
        result.loc[unresolved, column] = np.nan
    result.loc[unresolved, "detection_limit_tag"] = "not_assessed"
    return result


def _add_provenance(summary: pd.DataFrame, products: LinProducts) -> pd.DataFrame:
    qc = _validate_compartment_qc(products)
    cell_support = _cell_support_table(products)
    quality = _quality_by_cohort(products)
    study_info = products.cohort_scope.rename(columns={"cohort": "study"})[["study", "cancer"]].copy()
    study_info["sorting"] = "not_assessed_from_safe_metadata"
    study_info["bulk_overlap_flag"] = "not_assessed"
    study_info["source_family"] = "not_assessed"
    study_info["source_mapping_status"] = "not_assessed"
    study_info["licence"] = "CC BY 4.0 atlas licence; study-level terms not separately assessed"
    study_info["processing"] = (
        "raw integer UMIs; donor pseudobulk per baseline ICI-only specimen and compartment; "
        "log2(CPM+1) uses the full-profile library denominator"
    )
    study_info["source"] = "Lin 2026 atlas; Zenodo 10.5281/zenodo.19586163"
    study_info["limitations"] = (
        "ambient RNA can blur detection; non-detection is not absence; no cross-study pooling or "
        "compartment z-score; no published weighted GEP claim; top outcome-selected genes deferred"
    )
    merged = summary.merge(study_info, on=["study", "cancer"], how="left", validate="many_to_one")
    merged["producer_revision"] = products.producer_revision or "current_working_tree"
    merged = merged.merge(cell_support, on=["study", "compartment"], how="left", validate="many_to_one")
    qc_rows = qc.rename(columns={"cohort": "study", "eligible_donors": "qc_eligible_donors"})[
        ["study", "compartment", "profiles", "qc_eligible_donors", "na_profiles"]
    ]
    merged = merged.merge(qc_rows, on=["study", "compartment"], how="left", validate="many_to_one")
    merged["source_quality_assessment"] = merged["study"].map(
        lambda study: quality.get(str(study), ("not_assessed", ""))[0]
    )
    source_reasons = merged["study"].map(lambda study: quality.get(str(study), ("", ""))[1])
    source_unsupported = merged["status"].eq("not_assessed") & merged["n_profiles"].eq(0) & source_reasons.ne("")
    merged.loc[source_unsupported, "reason"] = (
        merged.loc[source_unsupported, "reason"].astype(str)
        + ";" + source_reasons.loc[source_unsupported].astype(str)
    )
    unresolved = merged["cancer"].map(_is_unverified_head_neck)
    merged["bulk_overlap_note"] = "not assessed"
    merged.loc[unresolved, "bulk_overlap_note"] = "source_check_pending"
    merged.loc[unresolved, "source_mapping_status"] = "source_check_pending"
    return _block_unverified_head_neck_display(merged)


def _ordered_units(summary: pd.DataFrame) -> list[str]:
    definitions = panel_definitions_for_sc1()
    return [
        *SC1_PANEL_IDS,
        *definitions["M5_CHECKPOINT_CANDIDATES"],
        *definitions["M6_EPIGENETIC_REGULATORS"],
    ]


def _panel_membership_table() -> pd.DataFrame:
    definitions = panel_definitions_for_sc1()
    rows = []
    for panel_id in SC1_PANEL_IDS:
        source = (
            "Hallmark IFNG GMT with frozen RIGI-to-DDX58 alias"
            if panel_id == HALLMARK_IFNG
            else "signed Paper A custom panel with frozen alias resolution"
        )
        members = definitions[panel_id]
        for gene in members:
            rows.append({
                "unit_id": panel_id,
                "unit_type": "panel",
                "gene_group": "",
                "member_gene": gene,
                "method_id": f"CUSTOM_MEAN_{panel_id}",
                "n_members": len(members),
                "membership_source": source,
            })
    for panel_id, gene_group in (
        ("M5_CHECKPOINT_CANDIDATES", "M5"),
        ("M6_EPIGENETIC_REGULATORS", "M6"),
    ):
        for gene in definitions[panel_id]:
            rows.append({
                "unit_id": gene,
                "unit_type": "gene",
                "gene_group": gene_group,
                "member_gene": gene,
                "method_id": "GENE_STUDY_SCALE",
                "n_members": 1,
                "membership_source": f"individual gene from signed {gene_group} set",
            })
    return pd.DataFrame.from_records(rows)


def _coverage_audit_table(summary: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "study", "cancer", "compartment", "unit_id", "method_id",
        "n_members_available_global", "n_members_total", "member_availability",
        "n_eligible_donors", "n_donors_support", "member_support_min", "member_support_max",
        "status", "reason",
    ]
    audit = summary.loc[summary["unit_type"].eq("panel"), columns].copy()
    audit["n_members_required_80pct"] = audit["n_members_total"].map(
        lambda value: math.ceil(0.8 * value) if pd.notna(value) else np.nan
    )
    audit["donors_meeting_80pct"] = audit["n_donors_support"]
    audit["donors_below_80pct_or_missing"] = (
        audit["n_eligible_donors"] - audit["n_donors_support"]
    ).clip(lower=0)
    return audit


def _write_figure(summary: pd.DataFrame, output: Path) -> int:
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    definitions = panel_definitions_for_sc1()
    y_order = _ordered_units(summary)
    compartments = list(LIN_COMPARTMENTS)
    studies = summary[["study", "cancer"]].drop_duplicates().sort_values("study")
    output.parent.mkdir(parents=True, exist_ok=True)
    page_count = 0
    with PdfPages(output) as pdf:
        for study_row in studies.itertuples(index=False):
            current = summary[summary["study"].eq(study_row.study)]
            lookup = current.set_index(["unit_id", "compartment"])
            shown_values = current.loc[current["status"].eq("shown"), "median_log2_cpm_plus1"].dropna()
            if len(shown_values):
                vmin, vmax = float(shown_values.min()), float(shown_values.max())
                if vmin == vmax:
                    vmin, vmax = vmin - 0.5, vmax + 0.5
            else:
                vmin, vmax = 0.0, 1.0
            height = max(10.0, 0.32 * len(y_order) + 2.4)
            figure, axis = plt.subplots(figsize=(13.2, height))
            colour_map = plt.get_cmap("viridis")
            norm = plt.Normalize(vmin=vmin, vmax=vmax)
            for y_index, unit in enumerate(y_order):
                for x_index, compartment in enumerate(compartments):
                    key = (unit, compartment)
                    if key not in lookup.index:
                        status, reason = "not_assessed", "no_source_profiles_for_compartment"
                        record = None
                    else:
                        record = lookup.loc[key]
                        status, reason = str(record["status"]), str(record["reason"])
                    if status == "shown" and record is not None:
                        is_gene = str(record["unit_type"]) == "gene"
                        detection = record["median_percent_cells_detected"]
                        size = 22.0 if not is_gene or pd.isna(detection) else 18.0 + 0.45 * float(detection)
                        axis.scatter(
                            x_index, y_index, s=size,
                            c=[colour_map(norm(float(record["median_log2_cpm_plus1"])))],
                            edgecolors="black", linewidths=0.25, zorder=2,
                        )
                    else:
                        label = "n<5" if status == "insufficient_donors" else "NA"
                        axis.scatter(x_index, y_index, s=24, marker="s", color="#e5e7eb",
                                     edgecolors="#9ca3af", linewidths=0.3, zorder=1)
                        axis.text(x_index, y_index, label, ha="center", va="center",
                                  fontsize=5.7, color="#374151", zorder=3)
            if len(shown_values):
                colorbar = figure.colorbar(
                    plt.cm.ScalarMappable(norm=norm, cmap=colour_map), ax=axis, fraction=0.025, pad=0.02,
                )
                colorbar.set_label("Median log2(CPM + 1); this study's scale", fontsize=9)
            else:
                axis.set_title(
                    f"{study_row.study} · {study_row.cancer}\nNo assessed expression values; see coverage table",
                    loc="left", fontsize=12, pad=12,
                )
            axis.set_xticks(range(len(compartments)), compartments, rotation=30, ha="right", fontsize=8)
            axis.set_yticks(range(len(y_order)), y_order, fontsize=7)
            axis.invert_yaxis()
            axis.set_xlim(-0.5, len(compartments) - 0.5)
            axis.set_ylim(len(y_order) - 0.5, -0.5)
            axis.set_xlabel("Broad compartment", fontsize=9)
            if len(shown_values):
                axis.set_title(f"{study_row.study} · {study_row.cancer}", loc="left", fontsize=12, pad=10)
            axis.grid(which="major", color="#d1d5db", linewidth=0.35, alpha=0.8)
            axis.set_axisbelow(True)
            figure.text(
                0.08, 0.025,
                "Each page uses its own expression scale; studies are not pooled and compartments are not z-scored. "
                "Composite dots have fixed size. Gene dot size is median donor % cells with counts >0. "
                "NA means not assessed; n<5 means insufficient donor support. Ambient RNA may blur detection. "
                "No response-selected genes are shown; top A-META genes are deferred.",
                fontsize=7.2, wrap=True,
            )
            right_edge = 0.94 if len(shown_values) else 0.98
            figure.tight_layout(rect=(0.04, 0.06, right_edge, 0.97))
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)
            page_count += 1
    return page_count


def build_presentation(
    atlas_dir: Path | str,
    output_dir: Path | str | None = None,
    *,
    producer_revision: str | None = None,
) -> Path:
    """Build patient-free SC-1 tables and a study-scaled multipage PDF."""
    raw_atlas = _reject_symlink_components(Path(atlas_dir).expanduser())
    atlas_identity = raw_atlas.resolve(strict=False)
    raw_output = Path(output_dir).expanduser() if output_dir else atlas_identity / "presentation_w5"
    _reject_symlink_components(raw_output)
    output = raw_output.resolve(strict=False)
    input_roots = [atlas_identity / name for name in ("pseudobulk", "compartments", "qc", "labels")]
    if output.exists() or output == atlas_identity or any(
        output == source_root or source_root in output.parents or output in source_root.parents
        for source_root in input_roots
    ):
        raise ValueError("SC-1 presentation output must use a new directory")
    atlas_dir = raw_atlas.resolve(strict=True)
    products = read_lin_products(atlas_dir, producer_revision=producer_revision)
    summary = summarize_profiles(products.clinical, products.expression)
    summary = _complete_summary_grid(summary, products)
    summary = _verify_aggregate_gene_summaries(summary, products)
    summary = _block_unverified_head_neck_display(summary)
    provenance = _add_provenance(summary, products)
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "unit_summary.tsv"
    provenance_path = output / "provenance_coverage.tsv"
    source_path = output / "source_hashes.tsv"
    membership_path = output / "panel_membership.tsv"
    coverage_path = output / "coverage_audit.tsv"
    figure_path = output / "compartment_expression_panels.pdf"
    summary.to_csv(summary_path, sep="\t", index=False, na_rep="NA")
    provenance.to_csv(provenance_path, sep="\t", index=False, na_rep="NA")
    products.source_hashes.to_csv(source_path, sep="\t", index=False)
    membership = _panel_membership_table()
    membership.to_csv(membership_path, sep="\t", index=False)
    _coverage_audit_table(summary).to_csv(coverage_path, sep="\t", index=False, na_rep="NA")
    page_count = _write_figure(summary, figure_path)
    outputs = (summary_path, provenance_path, source_path, membership_path, coverage_path, figure_path)
    manifest = {
        "analysis": "Paper A SC-1 presentation",
        "data_classification": "existing measured-source pseudobulk and aggregate products",
        "status": "outcome_free_descriptive_presentation",
        "unit": "patient/donor",
        "atlas": "lin2026_atlas",
        "producer_revision": products.producer_revision or "current_working_tree",
        "producer_verification": (
            "immutable_git_commit" if products.producer_revision is not None else "current_working_tree"
        ),
        "source": "Lin 2026 atlas; Zenodo 10.5281/zenodo.19586163",
        "source_licence": "CC BY 4.0 atlas licence; source-study licence not separately assessed",
        "input_sha256": products.input_sha256,
        "verified_product_sha256": products.source_hashes.to_dict(orient="records"),
        "clinical_columns_read": list(SAFE_CLINICAL_COLUMNS),
        "clinical_outcome_columns_read": [],
        "restricted_output_not_opened": RESTRICTED_OUTPUT,
        "source_thresholds": {"minimum_cells": 15, "minimum_umis": 5000, "minimum_donors_to_show": 5},
        "panels": list(SC1_PANEL_IDS),
        "custom_method_ids": [f"CUSTOM_MEAN_{panel}" for panel in SC1_PANEL_IDS],
        "individual_gene_groups": {
            "M5": len(panel_definitions_for_sc1()["M5_CHECKPOINT_CANDIDATES"]),
            "M6": len(panel_definitions_for_sc1()["M6_EPIGENETIC_REGULATORS"]),
        },
        "scoring": "log2(CPM+1) from full profile library; per-donor unweighted member mean with at least 80% measured; equal-weight donor median",
        "missingness": "NA source-layer values remain missing; measured zero counts remain zero",
        "detection": "gene rows use donor-level median percent cells with counts >0; no composite detection percentage is defined",
        "figure_pages": page_count,
        "figure_scale": "independent per study page; no cross-study pooling or compartment z-score",
        "bulk_overlap": "not assessed; head-and-neck display is blocked with source_check_pending",
        "sorting": "not assessed from the selected safe metadata",
        "deferred_top_outcome_selected_genes": "deferred; no released A-META outcome results were used",
        "outputs": {path.name: _sha256(path) for path in outputs},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return output


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m tools.sc.presentation")
    parser.add_argument("--atlas-dir", required=True, help="Existing A/sc_lin2026 results directory")
    parser.add_argument("--output-dir", help="New presentation output directory; defaults to presentation_w5")
    parser.add_argument(
        "--producer-revision",
        help="Full immutable 40-character commit ID whose six allowlisted producer blobs match the saved manifests",
    )
    args = parser.parse_args(argv)
    try:
        output = build_presentation(
            args.atlas_dir,
            args.output_dir,
            producer_revision=args.producer_revision,
        )
    except (OSError, ValueError) as error:
        parser.exit(2, f"SC-1 presentation failed: {error}\n")
    print(f"SC-1 presentation written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
