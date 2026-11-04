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

import numpy as np
import pandas as pd

from .core import MIN_CELLS, MIN_DONORS_TO_SHOW, MIN_UMIS, gene_set_table, panel_definitions
from .runtime import configure_runtime
from .sc3 import guard_sc3, group_profiles, hedges_g


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


def _read_profiles(atlas_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    clinical_parts = []
    expression_parts = []
    root = atlas_dir / "pseudobulk"
    if not root.is_dir():
        raise FileNotFoundError("Run pseudobulk first; no patient-level profiles were found")
    for compartment_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        clinical_path = compartment_dir / "clinical.tsv"
        expression_path = compartment_dir / "expression.tsv"
        if clinical_path.is_file() and expression_path.is_file():
            clinical_parts.append(pd.read_csv(clinical_path, sep="\t", dtype=str, keep_default_na=False))
            matrix = pd.read_csv(expression_path, sep="\t", index_col=0, na_values=["NA"])
            expression_parts.append(matrix)
    if not clinical_parts:
        raise FileNotFoundError("No pseudobulk expression/clinical pairs were found")
    clinical = pd.concat(clinical_parts, ignore_index=True, sort=False)
    clinical["eligible"] = clinical["eligible"].astype(str).str.casefold().eq("true")
    for column in ("n_cells", "total_umis", "library_size", "fraction_cells_total"):
        if column in clinical:
            clinical[column] = pd.to_numeric(clinical[column], errors="coerce")
    expression = pd.concat(expression_parts, axis=1, sort=False)
    return clinical, expression


def _drug_class(treatment: str) -> str:
    value = (treatment or "").casefold().replace(" ", "")
    if "chemo" in value or "tim3" in value:
        return "OTHER_EXCLUDED"
    if value in {"apd1+ctla4", "apdl1+ctla4", "apd1+ipilimumab"}:
        return "DUAL_PD1_CTLA4"
    if value in {"actla4", "ipilimumab", "aCTLA4".casefold()}:
        return "ANTI_CTLA4"
    if value in {"apd1", "apdl1"}:
        return "ANTI_PD_L1_AXIS"
    if value in {"untreated_hormone_naive", "untreated", "noici"}:
        return "NOT_APPLICABLE"
    return "UNMAPPED"


def _sc3_effects(clinical: pd.DataFrame, expression: pd.DataFrame) -> pd.DataFrame:
    definitions = panel_definitions()
    groups, _ = group_profiles(clinical)
    records: list[dict] = []
    by_profile = clinical.set_index("profile_id", drop=False)

    def append_effect(group, ids, values_by_id, unit_family, unit):
        frame = clinical.loc[clinical["profile_id"].astype(str).isin(ids)].copy()
        r_ids = frame.loc[frame["outcome_label"].eq("R"), "profile_id"].astype(str).tolist()
        nr_ids = frame.loc[frame["outcome_label"].eq("NR"), "profile_id"].astype(str).tolist()
        usable_r = [values_by_id[pid] for pid in r_ids if pid in values_by_id and pd.notna(values_by_id[pid])]
        usable_nr = [values_by_id[pid] for pid in nr_ids if pid in values_by_id and pd.notna(values_by_id[pid])]
        base = {
            "unit_family": unit_family,
            "unit": unit,
            "study": group.cohort,
            "cancer": str(by_profile.loc[ids[0]].get("cancer", "")) if ids else "",
            "drug_class_stratum": _drug_class(str(by_profile.loc[ids[0]].get("treatment", ""))) if ids else "UNMAPPED",
            "endpoint_family": group.endpoint_family,
            "n_R": len(usable_r),
            "n_NR": len(usable_nr),
            "mean_R": float(pd.Series(usable_r).mean()) if usable_r else float("nan"),
            "mean_NR": float(pd.Series(usable_nr).mean()) if usable_nr else float("nan"),
            "sd_R": float(pd.Series(usable_r).std(ddof=1)) if len(usable_r) > 1 else float("nan"),
            "sd_NR": float(pd.Series(usable_nr).std(ddof=1)) if len(usable_nr) > 1 else float("nan"),
            "status": "ok",
            "reason": "",
        }
        if len(usable_r) < 3 or len(usable_nr) < 3:
            base.update(status="insufficient_profiles", reason="fewer_than_three_eligible_profiles_per_arm")
            base.update(g=float("nan"), se=float("nan"))
        else:
            base.update(hedges_g(usable_r, usable_nr))
        records.append(base)

    for group in groups.values():
        ids = list(group.profile_ids)
        subset = expression.loc[:, ids]
        total = pd.to_numeric(by_profile.loc[ids, "library_size"], errors="coerce")
        normalized = subset.divide(total.to_numpy(), axis=1) * 1_000_000.0
        normalized = np_log2_plus1(normalized)
        for panel_id in (pid for pid in definitions if pid in {
            "P_ANTIGEN_PRESENTATION", "AYERS_GEP_18", "HOPE_18", "M0_EXTRA_ANTIGEN_PRESENTATION",
            "M1_MOBILITY", "M2_CYTOTOXICITY", "M3_VIRAL_MIMICRY", "M4_EXCLUSION",
            "CYT_FROZEN_UNOFFSET", "CYT_ROONEY_OFFSET_REFERENCE", "APM_WANG_18",
        }):
            members = definitions[panel_id]
            present = [gene for gene in members if gene in normalized.index]
            coverage = len(present) / len(members) if members else 0.0
            values = {}
            if coverage >= 0.8 and present:
                for profile_id in ids:
                    profile_values = normalized.loc[present, profile_id].dropna()
                    values[profile_id] = float(profile_values.mean()) if len(profile_values) >= 0.8 * len(members) else np.nan
            append_effect(group, ids, values, "panel", panel_id)
        for panel_id in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS"):
            for gene in definitions[panel_id]:
                values = {
                    profile_id: normalized.at[gene, profile_id]
                    for profile_id in ids
                    if gene in normalized.index and pd.notna(normalized.at[gene, profile_id])
                }
                append_effect(group, ids, values, "gene", gene)
        fractions = {
            row.profile_id: row.fraction_cells_total
            for row in clinical.loc[clinical["profile_id"].astype(str).isin(ids)].itertuples()
            if hasattr(row, "fraction_cells_total")
        }
        if fractions:
            append_effect(group, ids, fractions, "fraction", "compartment_fraction")
    return pd.DataFrame.from_records(records)


def np_log2_plus1(frame: pd.DataFrame) -> pd.DataFrame:
    import numpy as np

    return np.log2(frame + 1.0)


def _run_sc3(args, atlas_dir: Path, atlas: str) -> None:
    guard_sc3(is_synthetic=False, allow_outcomes=args.allow_outcomes)
    clinical, expression = _read_profiles(atlas_dir)
    groups, refusals = group_profiles(clinical)
    output = atlas_dir / "sc3"
    output.mkdir(parents=True, exist_ok=True)
    effects = _sc3_effects(clinical, expression)
    effects.to_csv(output / "effects.tsv", sep="\t", index=False, na_rep="NA")
    pd.DataFrame.from_records(refusals, columns=["cohort", "compartment", "endpoint_family", "n_R", "n_NR", "reason"]).to_csv(
        output / "refusals.tsv", sep="\t", index=False
    )
    counts_path = output / "pseudobulk_counts.tsv"
    clinical_path = output / "pseudobulk_clinical.tsv"
    expression.to_csv(counts_path, sep="\t", index_label="gene", na_rep="NA")
    clinical.to_csv(clinical_path, sep="\t", index=False, na_rep="NA")
    from tools.r_bridge import run_r

    expected = ["de_results.tsv", "de_refusals.tsv"]
    result = run_r(
        ROOT / "r/scripts/sc3_deseq2.R",
        {"counts": counts_path, "clinical": clinical_path},
        {"expected_outputs": expected, "atlas": atlas, "design": "~ response", "fdr": 0.10},
        output / "deseq2_run",
    )
    for name, path in result.outputs.items():
        shutil.copy2(path, output / name)
    _write_manifest(
        output / "manifest.json",
        {
            "analysis": "SC-3",
            "status": "exploratory_outcome_analysis",
            "unit": "patient",
            "atlas": atlas,
            "eligible_groups": len(groups),
            "design": "~ response within cohort x compartment x endpoint family",
            "fdr_method": "BH",
            "fdr_threshold": 0.10,
            "de_manifest": result.manifest,
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
             "input_sha256": _digest(source), "outputs": {"qc_summary.tsv": _digest(output / "qc_summary.tsv")}},
        )
    elif command == "embed":
        adata, source = prostate.load_h5ad(runtime)
        output = atlas_dir / "embedding"
        prostate.run_embedding(adata, output)
        _write_manifest(output / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "input_sha256": _digest(source),
            "normalisation": "library size 10,000 then log1p", "hvg": "Seurat flavor, 2,000 genes", "leiden_resolution": 0.8,
            "status": "descriptive_embedding"})
    elif command == "labels":
        adata, source = prostate.load_h5ad(runtime)
        output = atlas_dir / "labels" / "author_marker_dotplot.png"
        prostate.marker_plot(adata, output)
        _write_manifest(output.parent / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "input_sha256": _digest(source),
            "author_label": "celltype_major_v2", "markers": prostate.MARKERS})
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
        _write_manifest(output / "manifest.json", {"atlas": "prostate_hormone_naive_atlas", "input_sha256": _digest(source),
            "unit": "donor", "expression": "donor median log2(CPM+1)", "detection": "median donor percent cells > 0",
            "minimum_cells": MIN_CELLS, "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "outputs": {"compartment_expression.tsv": _digest(output / "compartment_expression.tsv"),
                        "compartment_expression_dotplot.png": _digest(output / "compartment_expression_dotplot.png")}})
        if command == "pseudobulk":
            prostate.marker_plot(adata, atlas_dir / "labels" / "author_marker_dotplot.png")


def _lin_command(command: str, atlas_dir: Path, runtime: Path) -> None:
    from tools.r_bridge import run_r

    lin_root = runtime / "lin2026_atlas"
    output_root = atlas_dir / "_bridge_runs"
    if command == "qc":
        metadata = lin_root / "gate0/metadata.rds"
        script = ROOT / "r/scripts/sc_lin_qc.R"
        expected = ["qc_summary.tsv", "qc_by_cohort.tsv"]
        inputs = {"metadata": metadata}
        config = {"expected_outputs": expected}
        bridge_output = output_root / "qc"
        result = run_r(script, inputs, config, bridge_output)
        output = atlas_dir / "qc"
        output.mkdir(parents=True, exist_ok=True)
        for name, source in result.outputs.items():
            shutil.copy2(source, output / name)
        _write_manifest(output / "manifest.json", {"atlas": "lin2026_atlas", "unit": "cell-level QC audit",
            "source": "Gate 0 metadata", "bridge_manifest": result.manifest})
        return

    object_path = prostate._source_by_suffix(runtime, "lin2026_atlas", ".qs2")
    panel_path = atlas_dir / "_bridge_runs" / "panel_membership.tsv"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    gene_set_table(panel_definitions()).to_csv(panel_path, sep="\t", index=False)
    cohort_map = ROOT / "tools/sc/lin_cohort_map.tsv"
    compartment_map = ROOT / "tools/sc/lin_compartment_map.tsv"
    all_outputs = {
        "pseudobulk": [
            *[f"expression__{slug}.tsv" for slug in _lin_slugs()],
            *[f"clinical__{slug}.tsv" for slug in _lin_slugs()],
            "compartment_qc.tsv", "compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "labels_markers.tsv",
            "labels_dotplot.png", "compartment_dotplot.png",
        ],
        "labels": ["labels_markers.tsv", "labels_dotplot.png"],
        "compartments": ["compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "compartment_dotplot.png"],
    }
    expected = all_outputs[command]
    inputs = {"seurat": object_path, "cohort_map": cohort_map, "compartment_map": compartment_map, "panels": panel_path}
    config = {"expected_outputs": expected, "mode": command, "minimum_cells": MIN_CELLS,
        "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
        "cohort_map": str(cohort_map), "compartment_map": str(compartment_map), "panel_membership": str(panel_path)}
    bridge_output = output_root / command
    result = run_r(ROOT / "r/scripts/sc_lin_pseudobulk.R", inputs, config, bridge_output)
    if command == "labels":
        output = atlas_dir / "labels"
        output.mkdir(parents=True, exist_ok=True)
        for name in expected:
            shutil.copy2(result.outputs[name], output / name)
        _write_manifest(output / "manifest.json", {"atlas": "lin2026_atlas", "author_label": "celltype_main",
            "markers": "canonical marker dot plot", "bridge_manifest": result.manifest})
    elif command == "compartments":
        output = atlas_dir / "compartments"
        output.mkdir(parents=True, exist_ok=True)
        for name in expected:
            shutil.copy2(result.outputs[name], output / name)
        _write_manifest(output / "manifest.json", {"atlas": "lin2026_atlas", "unit": "patient",
            "expression": "donor median log2(CPM+1)", "minimum_cells": MIN_CELLS,
            "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "bridge_manifest": result.manifest})
    else:
        for compartment, slug in zip(LIN_COMPARTMENTS, _lin_slugs(), strict=True):
            destination = atlas_dir / "pseudobulk" / slug
            destination.mkdir(parents=True, exist_ok=True)
            expr_name, clin_name = f"expression__{slug}.tsv", f"clinical__{slug}.tsv"
            shutil.copy2(result.outputs[expr_name], destination / "expression.tsv")
            shutil.copy2(result.outputs[clin_name], destination / "clinical.tsv")
            _write_manifest(destination / "manifest.json", {"atlas": "lin2026_atlas", "paper": "A",
                "unit": "patient", "compartment": compartment, "count_source": "raw UMI counts",
                "minimum_cells": MIN_CELLS, "minimum_umis": MIN_UMIS,
                "input_sha256": result.manifest["input_sha256"]["seurat"],
                "r_package_versions": result.manifest["package_versions"],
                "outputs": {"expression.tsv": _digest(destination / "expression.tsv"), "clinical.tsv": _digest(destination / "clinical.tsv")}})
        expression_root = atlas_dir / "compartments"
        expression_root.mkdir(parents=True, exist_ok=True)
        for name in ("compartment_qc.tsv", "compartment_expression.tsv", "pcahawley_per_patient_expression.tsv", "compartment_dotplot.png"):
            shutil.copy2(result.outputs[name], expression_root / name)
        _write_manifest(expression_root / "manifest.json", {"atlas": "lin2026_atlas", "unit": "patient",
            "expression": "donor median log2(CPM+1)", "minimum_cells": MIN_CELLS,
            "minimum_umis": MIN_UMIS, "minimum_donors_to_show": MIN_DONORS_TO_SHOW,
            "pcahawley_exception": "per-patient log2(CPM+1); no group medians, intervals, or response contrast",
            "bridge_manifest": result.manifest})
        marker_root = atlas_dir / "labels"
        marker_root.mkdir(parents=True, exist_ok=True)
        for name in ("labels_markers.tsv", "labels_dotplot.png"):
            shutil.copy2(result.outputs[name], marker_root / name)
        _write_manifest(marker_root / "manifest.json", {"atlas": "lin2026_atlas", "author_label": "celltype_main",
            "bridge_manifest": result.manifest})


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
