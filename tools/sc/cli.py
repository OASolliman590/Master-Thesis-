"""Command-line interface for outcome-free atlas work and guarded SC-3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

from .core import MIN_CELLS, MIN_DONORS_TO_SHOW, MIN_UMIS, gene_set_table, panel_definitions
from .runtime import configure_runtime
from .sc3 import (
    guard_sc3,
    group_profiles,
    validated_group_manifest,
    _sc3_effects,
)


ROOT = Path(__file__).resolve().parents[2]
COMPARTMENTS = (
    "T/NK",
    "B/plasma",
    "myeloid",
    "fibroblast/stromal",
    "endothelial",
    "malignant/epithelial",
    "luminal/malignant epithelial",
    "basal epithelial",
)
LIN_COMPARTMENTS = COMPARTMENTS[:6]
PROSTATE_COMPARTMENTS = (
    "T/NK",
    "B/plasma",
    "myeloid",
    "fibroblast/stromal",
    "endothelial",
    "luminal/malignant epithelial",
    "basal epithelial",
)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_root() -> Path:
    return Path(os.environ.get("THESIS_RUNTIME", ROOT / ".scratch/runtime")).expanduser()


def _results_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().absolute()
    if os.environ.get("THESIS_RESULTS"):
        return Path(os.environ["THESIS_RESULTS"]).expanduser().absolute()
    master_root = ROOT.parent.parent if ROOT.parent.name == "worktrees" else ROOT
    return master_root / "results"


def _atlas_output(results: Path, atlas: str) -> tuple[str, Path]:
    paper = "A" if atlas == "lin2026" else "B"
    directory = results / paper / f"sc_{atlas}"
    directory.mkdir(parents=True, exist_ok=True)
    return paper, directory


def _write_manifest(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _code_ref(relative_path: str) -> dict[str, str]:
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Published code reference is missing: {relative_path}")
    return {"path": relative_path, "sha256": _digest(path)}


def _public_bridge_summary(result, script: Path) -> dict:
    raw = result.manifest
    return {
        "script": _code_ref(script.relative_to(ROOT).as_posix()),
        "input_sha256": dict(raw.get("input_sha256", {})),
        "output_sha256": dict(raw.get("output_sha256", {})),
        "r_version": raw.get("r_version", "unknown"),
        "bioconductor_version": raw.get("bioconductor_version", "unknown"),
        "package_versions": dict(raw.get("package_versions", {})),
        "session_info_sha256": hashlib.sha256(str(raw.get("session_info", "")).encode("utf-8")).hexdigest(),
    }


def _validate_public_manifest(manifest: dict, compartment_dir: Path, atlas: str, compartment: str) -> dict:
    expected_atlas = "lin2026_atlas" if atlas == "lin2026" else "prostate_hormone_naive_atlas"
    expected_paper = "A" if atlas == "lin2026" else "B"
    if manifest.get("atlas") != expected_atlas or manifest.get("paper") != expected_paper:
        raise ValueError(f"Pseudobulk manifest atlas/paper mismatch in {compartment_dir.name}")
    if manifest.get("unit") != "patient" or manifest.get("compartment") != compartment:
        raise ValueError(f"Pseudobulk manifest patient/compartment identity mismatch in {compartment_dir.name}")
    if manifest.get("minimum_cells") != MIN_CELLS or manifest.get("minimum_umis") != MIN_UMIS:
        raise ValueError(f"Pseudobulk manifest threshold mismatch in {compartment_dir.name}")
    inputs = manifest.get("input_sha256")
    if not isinstance(inputs, dict) or not inputs or any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in inputs.values()
    ):
        raise ValueError(f"Pseudobulk manifest has invalid input identity in {compartment_dir.name}")
    code = manifest.get("code")
    if not isinstance(code, list) or not code:
        raise ValueError(f"Pseudobulk manifest lacks relative code references in {compartment_dir.name}")
    for reference in code:
        relative = Path(str(reference.get("path", "")))
        expected_hash = str(reference.get("sha256", ""))
        if relative.is_absolute() or ".." in relative.parts or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Pseudobulk code references must use relative paths and SHA256 hashes")
        source = ROOT / relative
        if not source.is_file() or _digest(source) != expected_hash:
            raise ValueError(f"Pseudobulk code hash is stale or unverifiable: {relative.as_posix()}")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or not {"expression.tsv", "clinical.tsv"}.issubset(outputs):
        raise ValueError(f"Pseudobulk manifest lacks expression/clinical hashes in {compartment_dir.name}")
    for name, expected_hash in outputs.items():
        relative = Path(str(name))
        if relative.is_absolute() or ".." in relative.parts or not re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)):
            raise ValueError("Pseudobulk output hashes must use relative filenames and SHA256 hashes")
        output = compartment_dir / relative
        if not output.is_file() or _digest(output) != expected_hash:
            raise ValueError(f"Pseudobulk output hash mismatch: {compartment_dir.name}/{name}")

    def check_relative_only(value, key=""):
        if key in {"script_path", "r_library", "config", "session_info"}:
            raise ValueError("Published pseudobulk manifests cannot contain absolute script, library, or config details")
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                check_relative_only(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                check_relative_only(child, key)
        elif isinstance(value, str) and value.startswith("/"):
            raise ValueError("Published pseudobulk manifests cannot contain absolute paths")

    check_relative_only(manifest)
    return inputs


def _read_profiles(atlas_dir: Path, atlas: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    clinical_parts = []
    expression_parts = []
    root = atlas_dir / "pseudobulk"
    if not root.is_dir():
        raise FileNotFoundError("Run pseudobulk first; no patient-level profiles were found")
    allowed = LIN_COMPARTMENTS if atlas == "lin2026" else PROSTATE_COMPARTMENTS
    compartment_by_slug = {_slug(value): value for value in allowed}
    directories = sorted(path for path in root.iterdir() if path.is_dir())
    if not directories:
        raise FileNotFoundError("No compartment pseudobulk directories were found")
    shared_inputs = None
    seen_profiles: set[str] = set()
    for compartment_dir in directories:
        compartment = compartment_by_slug.get(compartment_dir.name)
        if compartment is None:
            raise ValueError(f"Unrecognized pseudobulk compartment directory: {compartment_dir.name}")
        clinical_path = compartment_dir / "clinical.tsv"
        expression_path = compartment_dir / "expression.tsv"
        manifest_path = compartment_dir / "manifest.json"
        if not (clinical_path.is_file() and expression_path.is_file() and manifest_path.is_file()):
            raise FileNotFoundError(f"Pseudobulk output is incomplete for compartment {compartment}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Pseudobulk manifest is invalid for compartment {compartment}") from error
        inputs = _validate_public_manifest(manifest, compartment_dir, atlas, compartment)
        if shared_inputs is None:
            shared_inputs = inputs
        elif inputs != shared_inputs:
            raise ValueError("Compartment pseudobulk manifests do not share one input identity")
        clinical = pd.read_csv(clinical_path, sep="\t", dtype=str, keep_default_na=False)
        expression = pd.read_csv(expression_path, sep="\t", index_col=0, na_values=["NA"])
        if "profile_id" not in clinical or clinical["profile_id"].astype(str).duplicated().any():
            raise ValueError(f"Clinical profile IDs are missing or duplicated for {compartment}")
        if not {"patient_id", "sample_id", "compartment", "cohort", "eligible"}.issubset(clinical.columns):
            raise ValueError(f"Clinical patient/specimen fields are missing for {compartment}")
        if not clinical["compartment"].astype(str).eq(compartment).all():
            raise ValueError(f"Clinical compartment membership differs from manifest for {compartment}")
        profile_ids = clinical["profile_id"].astype(str).tolist()
        if set(map(str, expression.columns)) != set(profile_ids) or list(map(str, expression.columns)) != profile_ids:
            raise ValueError(f"Expression columns do not align with clinical profiles for {compartment}")
        if expression.index.astype(str).duplicated().any() or expression.columns.astype(str).duplicated().any():
            raise ValueError(f"Expression gene/profile identities are duplicated for {compartment}")
        duplicate_profiles = seen_profiles.intersection(profile_ids)
        if duplicate_profiles:
            raise ValueError("A pseudobulk profile occurs in more than one compartment")
        seen_profiles.update(profile_ids)
        clinical_parts.append(clinical)
        expression_parts.append(expression)
    clinical = pd.concat(clinical_parts, ignore_index=True, sort=False)
    if clinical[["cohort", "patient_id", "sample_id"]].astype(str).eq("").any().any():
        raise ValueError("Clinical profiles contain an empty cohort, patient, or specimen identity")
    patient_sample_counts = clinical.groupby(["cohort", "patient_id"], dropna=False)["sample_id"].nunique()
    if (patient_sample_counts > 1).any():
        raise ValueError("A patient has multiple pseudobulk specimens in one cohort")
    clinical["eligible"] = clinical["eligible"].astype(str).str.casefold().eq("true")
    for column in ("n_cells", "total_umis", "library_size", "fraction_cells_total"):
        if column in clinical:
            clinical[column] = pd.to_numeric(clinical[column], errors="coerce")
    expression = pd.concat(expression_parts, axis=1, sort=False)
    return clinical, expression


def _new_workdir(atlas_dir: Path, label: str) -> Path:
    root = atlas_dir.parents[1] / "tmp" / "sc-working"
    root.mkdir(parents=True, exist_ok=True)
    run = 1
    while (root / f"{label}-{run:03d}").exists():
        run += 1
    work = root / f"{label}-{run:03d}"
    work.mkdir()
    return work


def _run_sc3(args, atlas_dir: Path, atlas: str) -> None:
    guard_sc3(is_synthetic=False, allow_outcomes=args.allow_outcomes)
    clinical, expression = _read_profiles(atlas_dir, atlas)
    groups, refusals = group_profiles(clinical, allow_outcomes=args.allow_outcomes)
    group_contract = validated_group_manifest(clinical, groups, allow_outcomes=args.allow_outcomes)
    group_ids = {
        key: contract["group_id"]
        for key, contract in zip(groups, group_contract, strict=True)
    }
    group_by_profile = {
        profile_id: group_ids[(cohort, compartment, family)]
        for (cohort, compartment, family), group in groups.items()
        for profile_id in group.profile_ids
    }
    analysis_clinical = clinical[clinical["profile_id"].astype(str).isin(group_by_profile)].copy()
    analysis_clinical["sc3_group_id"] = analysis_clinical["profile_id"].astype(str).map(group_by_profile)
    work = _new_workdir(atlas_dir, f"{atlas}-sc3")
    counts_path = work / "pseudobulk_counts.tsv"
    clinical_path = work / "pseudobulk_clinical.tsv"
    expression.loc[:, analysis_clinical["profile_id"].astype(str)].to_csv(
        counts_path, sep="\t", index_label="gene", na_rep="NA"
    )
    analysis_clinical.to_csv(clinical_path, sep="\t", index=False, na_rep="NA")
    from tools.r_bridge import run_r

    script = ROOT / "r/scripts/sc3_deseq2.R"
    expected = ["de_results.tsv", "de_refusals.tsv"]
    authorization = {"data_classification": "real", "allow_outcomes": bool(args.allow_outcomes)}
    result = run_r(
        script,
        {"counts": counts_path, "clinical": clinical_path},
        {"expected_outputs": expected, "atlas": atlas, "design": "~ response", "fdr": 0.10,
         "authorization": authorization, "validated_groups": group_contract},
        work / "r-output",
    )
    bridge_summary = _public_bridge_summary(result, script)
    _write_manifest(work / "r-output" / "manifest.json", bridge_summary)
    output = atlas_dir / "sc3"
    output.mkdir(parents=True, exist_ok=True)
    effects = _sc3_effects(clinical, expression, allow_outcomes=args.allow_outcomes)
    effects.to_csv(output / "effects.tsv", sep="\t", index=False, na_rep="NA")
    pd.DataFrame.from_records(refusals, columns=["cohort", "compartment", "endpoint_family", "n_R", "n_NR", "reason"]).to_csv(
        output / "refusals.tsv", sep="\t", index=False
    )
    for name, source in result.outputs.items():
        shutil.copy2(source, output / name)
    _write_manifest(
        output / "manifest.json",
        {
            "analysis": "SC-3",
            "status": "exploratory_outcome_analysis",
            "unit": "patient",
            "atlas": atlas,
            "eligible_groups": len(groups),
            "design": "~ response within cohort x compartment x endpoint family",
            "endpoint_mappings": {
                "RECIST": {"endpoint_family": "orr", "endpoint_definition_id": "ORR"},
                "pathology": {"endpoint_family": "source_label", "endpoint_definition_id": "SOURCE_LABEL_UNSPECIFIED"},
                "expansion": {"endpoint_family": "source_label", "endpoint_definition_id": "SOURCE_LABEL_UNSPECIFIED",
                              "clinical_response": "not_applicable"},
            },
            "fdr_method": "BH",
            "fdr_threshold": 0.10,
            "code": [_code_ref("tools/sc/sc3.py"), _code_ref("tools/sc/cli.py"),
                     _code_ref("r/scripts/sc3_deseq2.R")],
            "outputs": {name: _digest(output / name) for name in
                        ("effects.tsv", "refusals.tsv", "de_results.tsv", "de_refusals.tsv")},
            "de_run": bridge_summary,
        },
    )


def _prostate_command(command: str, atlas_dir: Path, runtime: Path) -> None:
    from . import prostate

    if command == "qc":
        adata, source = prostate.load_h5ad(runtime)
        summary = prostate.qc_summary(adata)
        output = atlas_dir / "qc"
        output.mkdir(parents=True, exist_ok=True)
        summary.to_csv(output / "qc_summary.tsv", sep="\t", index=False, na_rep="NA")
        _write_manifest(
            output / "manifest.json",
            {"atlas": "prostate_hormone_naive_atlas", "scope": "all_cells", "filtering_applied": False,
             "paper": "B", "input_sha256": {"h5ad": _digest(source)},
             "code": [_code_ref("tools/sc/prostate.py"), _code_ref("tools/sc/cli.py")],
             "outputs": {"qc_summary.tsv": _digest(output / "qc_summary.tsv")}},
        )
    elif command == "embed":
        adata, source = prostate.load_h5ad(runtime)
        output = atlas_dir / "embedding"
        prostate.run_embedding(adata, output)
        _write_manifest(output / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "paper": "B",
            "input_sha256": {"h5ad": _digest(source)}, "code": [_code_ref("tools/sc/prostate.py"), _code_ref("tools/sc/cli.py")],
            "normalisation": "library size 10,000 then log1p", "hvg": "Seurat flavor, 2,000 genes", "leiden_resolution": 0.8,
            "status": "descriptive_embedding",
            "outputs": {name: _digest(output / name) for name in ("umap.png", "prostate_embedding.h5ad")}})
    elif command == "labels":
        adata, source = prostate.load_h5ad(runtime)
        output = atlas_dir / "labels" / "author_marker_dotplot.png"
        prostate.marker_plot(adata, output)
        _write_manifest(output.parent / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "paper": "B",
            "input_sha256": {"h5ad": _digest(source)}, "code": [_code_ref("tools/sc/prostate.py"), _code_ref("tools/sc/cli.py")],
            "author_label": "celltype_major_v2", "markers": prostate.MARKERS,
            "outputs": {"author_marker_dotplot.png": _digest(output)}})
    elif command in {"compartments", "pseudobulk"}:
        adata, source = prostate.load_h5ad(runtime)
        profiles = prostate.aggregate_profiles(adata)
        if command == "pseudobulk":
            prostate.write_layout(profiles, atlas_dir, _digest(source))
        summary = prostate.compartment_table(profiles)
        output = atlas_dir / "compartments"
        output.mkdir(parents=True, exist_ok=True)
        summary.to_csv(output / "compartment_expression.tsv", sep="\t", index=False, na_rep="NA")
        prostate.compartment_dotplot(summary, output / "compartment_expression_dotplot.png")
        _write_manifest(output / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "paper": "B",
            "input_sha256": {"h5ad": _digest(source)}, "code": [_code_ref("tools/sc/prostate.py"), _code_ref("tools/sc/core.py"),
                _code_ref("tools/sc/prostate_compartment_map.tsv"), _code_ref("tools/sc/cli.py")],
            "unit": "patient", "expression": "patient median log2(CPM+1)", "detection": "median patient percent cells > 0",
            "minimum_cells": MIN_CELLS, "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "outputs": {"compartment_expression.tsv": _digest(output / "compartment_expression.tsv"),
                        "compartment_expression_dotplot.png": _digest(output / "compartment_expression_dotplot.png")}})
        if command == "pseudobulk":
            labels_output = atlas_dir / "labels"
            labels_output.mkdir(parents=True, exist_ok=True)
            marker_output = labels_output / "author_marker_dotplot.png"
            prostate.marker_plot(adata, marker_output)
            _write_manifest(labels_output / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "paper": "B",
                "input_sha256": {"h5ad": _digest(source)}, "code": [_code_ref("tools/sc/prostate.py"), _code_ref("tools/sc/cli.py")],
                "author_label": "celltype_major_v2", "markers": prostate.MARKERS,
                "outputs": {marker_output.name: _digest(marker_output)}})


def _lin_command(command: str, atlas_dir: Path, runtime: Path) -> None:
    from . import prostate
    from tools.r_bridge import run_r

    lin_root = runtime / "lin2026_atlas"
    work = _new_workdir(atlas_dir, f"lin2026-{command}")
    output_root = work / "r-output"
    script = ROOT / "r/scripts/sc_lin_pseudobulk.R"
    if command == "qc":
        metadata = lin_root / "gate0/metadata.rds"
        script = ROOT / "r/scripts/sc_lin_qc.R"
        expected = ["qc_summary.tsv", "qc_by_cohort.tsv"]
        inputs = {"metadata": metadata}
        config = {"expected_outputs": expected}
        result = run_r(script, inputs, config, output_root)
        bridge_summary = _public_bridge_summary(result, script)
        _write_manifest(output_root / "manifest.json", bridge_summary)
        output = atlas_dir / "qc"
        output.mkdir(parents=True, exist_ok=True)
        for name, source in result.outputs.items():
            shutil.copy2(source, output / name)
        _write_manifest(output / "manifest.json", {
            "atlas": "lin2026_atlas", "paper": "A", "unit": "cell-level QC audit",
            "source": "Gate 0 metadata", "input_sha256": dict(result.manifest["input_sha256"]),
            "code": [_code_ref("r/scripts/sc_lin_qc.R"), _code_ref("tools/sc/cli.py")],
            "outputs": {name: _digest(output / name) for name in expected},
            "r_run": bridge_summary,
        })
        return

    object_path = prostate._source_by_suffix(runtime, "lin2026_atlas", ".qs2")
    metadata_path = lin_root / "gate0/metadata.rds"
    if object_path.name != _digest(object_path):
        raise ValueError("Lin qs2 object filename does not match its source SHA256")
    panel_path = work / "panel_membership.tsv"
    gene_set_table(panel_definitions()).to_csv(panel_path, sep="\t", index=False)
    cohort_map = ROOT / "tools/sc/lin_cohort_map.tsv"
    compartment_map = ROOT / "tools/sc/lin_compartment_map.tsv"
    all_outputs = {
        "pseudobulk": [
            *[f"expression__{slug}.tsv" for slug in _lin_slugs()],
            *[f"clinical__{slug}.tsv" for slug in _lin_slugs()],
            "compartment_qc.tsv", "gene_coverage.tsv", "data_quality.tsv", "compartment_expression.tsv",
            "pcahawley_per_patient_expression.tsv", "labels_markers.tsv", "stage.log",
            "labels_dotplot.png", "compartment_dotplot.png",
        ],
        "labels": ["labels_markers.tsv", "labels_dotplot.png"],
        "compartments": ["compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "compartment_dotplot.png"],
    }
    expected = all_outputs[command]
    inputs = {"seurat": object_path, "metadata": metadata_path,
        "cohort_map": cohort_map, "compartment_map": compartment_map, "panels": panel_path}
    config = {"expected_outputs": expected, "mode": command, "minimum_cells": MIN_CELLS,
        "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
        "cohort_map": str(cohort_map), "compartment_map": str(compartment_map), "panel_membership": str(panel_path),
        "source_sha256": _digest(object_path), "metadata_sha256": _digest(metadata_path)}
    result = run_r(script, inputs, config, output_root)
    bridge_summary = _public_bridge_summary(result, script)
    _write_manifest(output_root / "manifest.json", bridge_summary)
    input_hashes = dict(result.manifest["input_sha256"])
    code_refs = [
        _code_ref("r/scripts/sc_lin_pseudobulk.R"), _code_ref("r/R/sc_lin.R"),
        _code_ref("tools/sc/cli.py"), _code_ref("tools/sc/lin_cohort_map.tsv"),
        _code_ref("tools/sc/lin_compartment_map.tsv"), _code_ref("tools/a_scoring/core.py"),
    ]
    if command == "labels":
        output = atlas_dir / "labels"
        output.mkdir(parents=True, exist_ok=True)
        for name in expected:
            shutil.copy2(result.outputs[name], output / name)
        _write_manifest(output / "manifest.json", {
            "atlas": "lin2026_atlas", "paper": "A", "author_label": "celltype_main",
            "markers": "canonical marker dot plot", "input_sha256": input_hashes,
            "code": code_refs, "outputs": {name: _digest(output / name) for name in expected},
            "r_run": bridge_summary,
        })
    elif command == "compartments":
        output = atlas_dir / "compartments"
        output.mkdir(parents=True, exist_ok=True)
        for name in expected:
            shutil.copy2(result.outputs[name], output / name)
        _write_manifest(output / "manifest.json", {"atlas": "lin2026_atlas", "paper": "A", "unit": "patient",
            "expression": "donor median log2(CPM+1)", "minimum_cells": MIN_CELLS,
            "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "input_sha256": input_hashes, "code": code_refs,
            "outputs": {name: _digest(output / name) for name in expected},
            "r_run": bridge_summary})
    else:
        pseudobulk_root = atlas_dir / "pseudobulk"
        pseudobulk_root.mkdir(parents=True, exist_ok=True)
        stage_log_path = pseudobulk_root / "sc_lin_stage.log"
        shutil.copy2(result.outputs["stage.log"], stage_log_path)
        stage_log_sha256 = _digest(stage_log_path)
        for compartment, slug in zip(LIN_COMPARTMENTS, _lin_slugs(), strict=True):
            destination = atlas_dir / "pseudobulk" / slug
            destination.mkdir(parents=True, exist_ok=True)
            expr_name, clin_name = f"expression__{slug}.tsv", f"clinical__{slug}.tsv"
            shutil.copy2(result.outputs[expr_name], destination / "expression.tsv")
            shutil.copy2(result.outputs[clin_name], destination / "clinical.tsv")
            _write_manifest(destination / "manifest.json", {"atlas": "lin2026_atlas", "paper": "A",
                "unit": "patient", "compartment": compartment, "count_source": "raw UMI counts",
                "minimum_cells": MIN_CELLS, "minimum_umis": MIN_UMIS,
                "input_sha256": input_hashes, "code": code_refs,
                "stage_log_sha256": stage_log_sha256,
                "r_package_versions": result.manifest["package_versions"],
                "outputs": {"expression.tsv": _digest(destination / "expression.tsv"),
                    "clinical.tsv": _digest(destination / "clinical.tsv")}})
        shutil.copy2(result.outputs["gene_coverage.tsv"], pseudobulk_root / "gene_coverage.tsv")
        qc_root = atlas_dir / "qc"
        qc_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(result.outputs["data_quality.tsv"], qc_root / "data_quality.tsv")
        qc_manifest_path = qc_root / "manifest.json"
        qc_manifest = json.loads(qc_manifest_path.read_text(encoding="utf-8")) if qc_manifest_path.exists() else {
            "atlas": "lin2026_atlas", "paper": "A", "unit": "patient-level raw-count audit"
        }
        qc_manifest.update({
            "input_sha256": input_hashes,
            "code": code_refs,
            "outputs": {**qc_manifest.get("outputs", {}), "data_quality.tsv": _digest(qc_root / "data_quality.tsv")},
        })
        _write_manifest(qc_manifest_path, qc_manifest)
        expression_root = atlas_dir / "compartments"
        expression_root.mkdir(parents=True, exist_ok=True)
        for name in ("compartment_qc.tsv", "compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "compartment_dotplot.png"):
            shutil.copy2(result.outputs[name], expression_root / name)
        _write_manifest(expression_root / "manifest.json", {"atlas": "lin2026_atlas", "paper": "A", "unit": "patient",
            "expression": "donor median log2(CPM+1)", "minimum_cells": MIN_CELLS,
            "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "pcahawley_exception": "per-patient log2(CPM+1); no group medians, intervals, or response contrast",
            "interpretation_note": "Ambient RNA may blur detection; non-detection is not evidence of absence.",
            "input_sha256": input_hashes, "code": code_refs,
            "outputs": {name: _digest(expression_root / name) for name in
                ("compartment_qc.tsv", "compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "compartment_dotplot.png")},
            "r_run": bridge_summary})
        marker_root = atlas_dir / "labels"
        marker_root.mkdir(parents=True, exist_ok=True)
        for name in ("labels_markers.tsv", "labels_dotplot.png"):
            shutil.copy2(result.outputs[name], marker_root / name)
        _write_manifest(marker_root / "manifest.json", {"atlas": "lin2026_atlas", "paper": "A",
            "author_label": "celltype_main", "input_sha256": input_hashes, "code": code_refs,
            "outputs": {name: _digest(marker_root / name) for name in ("labels_markers.tsv", "labels_dotplot.png")}})


def _lin_slugs() -> tuple[str, ...]:
    return tuple(re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_") for name in LIN_COMPARTMENTS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.sc")
    parser.add_argument("command", choices=("qc", "embed", "labels", "compartments", "pseudobulk", "sc3"))
    parser.add_argument("--atlas", required=True, choices=("lin2026", "prostate"))
    parser.add_argument("--results", help="Results root (overrides THESIS_RESULTS)")
    parser.add_argument("--allow-outcomes", action="store_true", help="Permit SC-3 on real outcome labels")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sc3":
        try:
            guard_sc3(is_synthetic=False, allow_outcomes=args.allow_outcomes)
        except PermissionError as error:
            print(str(error), file=sys.stderr)
            return 2
    if args.atlas == "lin2026" and args.command == "embed":
        print("The signed Lin workflow does not compute embeddings; use the R QC/label/pseudobulk commands.", file=sys.stderr)
        return 2
    configure_runtime()
    results = _results_root(args.results)
    _, atlas_dir = _atlas_output(results, args.atlas)
    runtime = _runtime_root()
    try:
        if args.atlas == "prostate":
            if args.command == "sc3":
                _run_sc3(args, atlas_dir, args.atlas)
            else:
                _prostate_command(args.command, atlas_dir, runtime)
        elif args.command == "sc3":
            _run_sc3(args, atlas_dir, args.atlas)
        else:
            _lin_command(args.command, atlas_dir, runtime)
    except (OSError, ValueError, RuntimeError, PermissionError) as error:
        print(f"single-cell {args.command} failed: {error}", file=sys.stderr)
        return 1
    print(f"single-cell {args.command} completed for atlas {args.atlas}")
    return 0
