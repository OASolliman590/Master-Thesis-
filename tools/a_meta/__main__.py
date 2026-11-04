"""Command line interface for the Paper A A-META modules."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping

from tools.a_cohorts.view import REPRESENTATION_FILE, cohort_view
from tools.a_meta.effects import EFFECT_COLUMNS, study_effects
from tools.a_meta.features import (
    FeatureTable,
    build_feature_table,
    read_external_feature_table,
    read_feature_table,
    write_feature_table,
)
from tools.a_meta.synthesis import (
    SUBGROUP_COLUMNS,
    SYNTHESIS_COLUMNS,
    synthesize,
)
from tools import a_scoring
from tools.a_scoring import ALIAS_TABLE_PATH, PANEL_REGISTRY_PATH
from tools.r_bridge import _sha256


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/cohorts/REGISTRY.tsv"
_CODE_FILES = (
    "tools/a_meta/__init__.py",
    "tools/a_meta/__main__.py",
    "tools/a_meta/effects.py",
    "tools/a_meta/features.py",
    "tools/a_meta/synthesis.py",
    "tools/a_cohorts/view.py",
    "tools/a_cohorts/core.py",
    "tools/a_scoring/__init__.py",
    "tools/a_scoring/core.py",
    "tools/r_bridge/__init__.py",
    "r/R/bridge.R",
    "r/scripts/singscore.R",
    "r/scripts/meta_rma.R",
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.a_meta")
    commands = parser.add_subparsers(dest="command", required=True)

    features_parser = commands.add_parser("features", help="Build outcome-blind per-cohort features")
    features_parser.add_argument("--cohort", required=True)
    features_parser.add_argument("--runtime", type=Path)
    features_parser.add_argument("--results", type=Path)
    features_parser.add_argument("--gene-sets", type=Path)
    features_parser.add_argument("--gene-map", type=Path)
    features_parser.add_argument("--gtf", type=Path)
    features_parser.add_argument("--external-table", type=Path)

    effects_parser = commands.add_parser("effects", help="Estimate within-study Hedges-g effects")
    effects_parser.add_argument("--cohort", required=True)
    effects_parser.add_argument("--runtime", type=Path)
    effects_parser.add_argument("--results", type=Path)
    effects_parser.add_argument("--endpoint-family", choices=("all", "orr", "clinical_benefit", "source_label"), default="all")
    effects_parser.add_argument("--unit-family", choices=("all", "gene", "panel", "pathway", "fraction"), default="all")
    effects_parser.add_argument("--no-drug-class", action="store_true")
    effects_parser.add_argument("--allow-outcomes", action="store_true")

    synthesis_parser = commands.add_parser("synthesize", help="Pool effects with metafor")
    synthesis_parser.add_argument("--effects", type=Path, required=True)
    synthesis_parser.add_argument("--stratum", choices=(
        "per_cancer", "per_drug_class", "across_cancers", "melanoma_cancer_drug"
    ), required=True)
    synthesis_parser.add_argument("--results", type=Path)
    synthesis_parser.add_argument("--run")
    synthesis_parser.add_argument("--allow-outcomes", action="store_true")

    args = parser.parse_args(argv)
    results_root = _results_root(args.results)
    if args.command == "features":
        _features(args, results_root)
    elif args.command == "effects":
        _effects(args, results_root)
    else:
        _synthesize(args, results_root)
    return 0


def _features(args, results_root: Path) -> None:
    view = cohort_view(args.cohort, args.runtime)
    dataset_dir = results_root / args.cohort
    output_dir = dataset_dir / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    tables: dict[str, FeatureTable] = {
        "gene": build_feature_table(
            view, "gene", runtime=args.runtime, gene_map=args.gene_map, gtf_path=args.gtf
        ),
        "panel": build_feature_table(
            view, "panel", runtime=args.runtime, gene_map=args.gene_map, gtf_path=args.gtf
        ),
    }
    if args.gene_sets is not None:
        tables["pathway"] = build_feature_table(
            view,
            "pathway",
            runtime=args.runtime,
            gene_sets=args.gene_sets,
            gene_map=args.gene_map,
            gtf_path=args.gtf,
            r_out_dir=output_dir / "R-singscore",
        )
    if args.external_table is not None:
        tables["fraction"] = read_external_feature_table(
            args.external_table,
            cohort_id=args.cohort,
            expected_patients=len(view.clinical_rows),
        )

    output_hashes = {}
    table_stats = {}
    for family, table in tables.items():
        table_path = output_dir / f"{family}s.tsv"
        write_feature_table(table, table_path)
        output_hashes[table_path.name] = _sha256(table_path)
        table_stats[family] = {
            "rows": table.n_patients,
            "columns": len(table.values_by_unit) + 1,
            "units": len(table.values_by_unit),
        }

    coverage_rows = [
        {
            "unit_family": family,
            "unit": unit,
            "n_found": details.get("n_found", ""),
            "n_total": details.get("n_total", ""),
            "complete": str(bool(details.get("complete", False))).lower(),
            "missing": ",".join(details.get("missing", ())),
        }
        for family, table in tables.items()
        for unit, details in table.coverage.items()
    ]
    coverage_path = output_dir / "coverage.tsv"
    _write_tsv(coverage_path, coverage_rows, ("unit_family", "unit", "n_found", "n_total", "complete", "missing"))
    output_hashes[coverage_path.name] = _sha256(coverage_path)

    input_hashes = {
        "cohort_expression": _sha256(view.expression_path),
        "cohort_clinical": _sha256(view.expression_path.parent / "clinical.tsv"),
        "representation_registry": _sha256(REPRESENTATION_FILE),
        "cohort_registry": _sha256(REGISTRY),
        "panel_registry": _sha256(PANEL_REGISTRY_PATH),
        "gene_aliases": _sha256(ALIAS_TABLE_PATH),
    }
    probe_map = view.expression_path.parent / "probe_to_gene.tsv"
    if probe_map.is_file():
        input_hashes["probe_to_gene_map"] = _sha256(probe_map)
    if args.gene_map is not None:
        input_hashes["gene_map"] = _sha256(args.gene_map)
    if args.gtf is not None:
        input_hashes["gene_annotation_gtf"] = _sha256(args.gtf)
    gene_info = a_scoring.core.gene_info_path(args.runtime)
    if gene_info.is_file():
        input_hashes["pinned_gene_info"] = _sha256(gene_info)
    if args.gene_sets is not None:
        input_hashes["gene_sets"] = _sha256(args.gene_sets)
    if args.external_table is not None:
        input_hashes["external_patient_table"] = _sha256(args.external_table)

    r_manifests = {
        family: table.metadata["r_manifest"]
        for family, table in tables.items()
        if "r_manifest" in table.metadata
    }
    manifest = {
        "data_classification": "real",
        "cohort": args.cohort,
        "inputs_sha256": input_hashes,
        "code_sha256": _code_hashes(),
        "outputs_sha256": output_hashes,
        "feature_tables": table_stats,
        "feature_metadata": {
            family: _safe_feature_metadata(table.metadata)
            for family, table in tables.items()
        },
        "panel_coverage": {
            "complete": sum(bool(item["complete"]) for item in coverage_rows if item["unit_family"] == "panel"),
            "incomplete": sum(not bool(item["complete"]) for item in coverage_rows if item["unit_family"] == "panel"),
        },
        "panel_registry_note": (
            "Ten materialized memberships are currently available. Hallmark IFN-gamma "
            "membership remains pending its signed pre-outcome freeze."
        ),
        "R_manifests": r_manifests,
        "patient_identifier_policy": "zero-based row index only; source identifiers are not exported",
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    for family, stats in table_stats.items():
        print(f"cohort={args.cohort} family={family} rows={stats['rows']} columns={stats['columns']} units={stats['units']}")
    print(f"cohort={args.cohort} panel_coverage_complete={manifest['panel_coverage']['complete']} panel_coverage_incomplete={manifest['panel_coverage']['incomplete']}")


def _effects(args, results_root: Path) -> None:
    if _is_locked_study(args.cohort):
        raise SystemExit("IMvigor210 is a locked final test and is refused by A-META")
    if _is_real_cohort(args.cohort) and not args.allow_outcomes:
        raise SystemExit("Real-cohort effects require the explicit --allow-outcomes flag")

    view = cohort_view(args.cohort, args.runtime)
    feature_dir = results_root / args.cohort / "features"
    families = (
        ("gene", "panel", "pathway", "fraction")
        if args.unit_family == "all"
        else (args.unit_family,)
    )
    endpoints = view.metadata.endpoint_families if args.endpoint_family == "all" else (args.endpoint_family,)
    results = []
    input_hashes = {
        "cohort_expression": _sha256(view.expression_path),
        "cohort_clinical": _sha256(view.expression_path.parent / "clinical.tsv"),
    }
    for unit_family in families:
        feature_path = feature_dir / f"{unit_family}s.tsv"
        if not feature_path.is_file():
            continue
        coverage_path = feature_dir / "coverage.tsv"
        table = read_feature_table(
            feature_path,
            cohort_id=args.cohort,
            unit_family=unit_family,
            n_patients=len(view.clinical_rows),
            coverage_path=coverage_path,
        )
        input_hashes[f"{unit_family}_features"] = _sha256(feature_path)
        for endpoint in endpoints:
            results.extend(study_effects(
                view,
                table,
                endpoint,
                by_drug_class=not args.no_drug_class,
            ))
    output_dir = results_root / args.cohort / "effects"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "effects.tsv"
    _write_tsv(output_path, results, EFFECT_COLUMNS)
    manifest = {
        "data_classification": "real" if _is_real_cohort(args.cohort) else "synthetic",
        "cohort": args.cohort,
        "inputs_sha256": input_hashes,
        "code_sha256": _code_hashes(),
        "outputs_sha256": {output_path.name: _sha256(output_path)},
        "effect_variance": "Hedges-g variance from SPEC_v2: J^2 * [N/(n_R*n_NR) + d^2/(2N)]",
    }
    _write_json(output_dir / "manifest.json", manifest)
    print(f"cohort={args.cohort} effect_rows={len(results)} columns={len(EFFECT_COLUMNS)}")


def _synthesize(args, results_root: Path) -> None:
    if _is_locked_effect_file(args.effects):
        raise SystemExit("IMvigor210 is a locked final test and is refused by A-META")
    real_input = _effect_input_is_real(args.effects)
    if real_input and not args.allow_outcomes:
        raise SystemExit("Real-cohort synthesis requires the explicit --allow-outcomes flag")

    run_hash = _sha256(args.effects)[:10]
    run_name = args.run or f"{args.stratum}-{run_hash}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_name):
        raise SystemExit("Run name may contain only letters, numbers, dots, underscores, and hyphens")
    output_dir = results_root / "meta" / run_name
    result = synthesize(args.effects, args.stratum, output_dir=output_dir)
    summary_path = output_dir / "synthesis.tsv"
    subgroup_path = output_dir / "subgroups.tsv"
    _write_tsv(summary_path, result.summaries, SYNTHESIS_COLUMNS)
    _write_tsv(subgroup_path, result.subgroup_tests, SUBGROUP_COLUMNS)
    manifest = {
        "data_classification": "real" if real_input else "synthetic",
        "stratum": args.stratum,
        "effect_input_sha256": _sha256(args.effects),
        "code_sha256": _code_hashes(),
        "outputs_sha256": {
            summary_path.name: _sha256(summary_path),
            subgroup_path.name: _sha256(subgroup_path),
        },
        "analysis_metadata": result.metadata,
        "R_manifest": result.r_manifest,
    }
    _write_json(output_dir / "manifest.json", manifest)
    print(f"run={run_name} synthesis_rows={len(result.summaries)} subgroup_rows={len(result.subgroup_tests)}")


def _results_root(argument: Path | None) -> Path:
    if argument is not None:
        return argument.expanduser()
    configured = os.environ.get("THESIS_RESULTS")
    if configured:
        return Path(configured).expanduser()
    thesis_root = ROOT.parent.parent if ROOT.parent.name == "worktrees" else ROOT.parent
    return thesis_root / "results" / "A"


def _registry_ids() -> set[str]:
    with REGISTRY.open(newline="", encoding="utf-8") as stream:
        return {row["cohort_id"] for row in csv.DictReader(stream, delimiter="\t")}


def _is_real_cohort(value: str) -> bool:
    return value in _registry_ids()


def _is_locked_study(value: str) -> bool:
    return re.sub(r"[^a-z0-9]", "", value.casefold()).find("imvigor210") >= 0


def _is_locked_effect_file(path: Path) -> bool:
    manifest_path = path.parent / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cohort = str(manifest.get("cohort", ""))
        if _is_locked_study(cohort):
            return True
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if "study" not in (reader.fieldnames or []):
            raise SystemExit("Effect table requires a study column")
        return any(_is_locked_study(str(row.get("study", ""))) for row in reader)


def _effect_input_is_real(path: Path) -> bool:
    manifest_path = path.parent / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("data_classification") == "real":
            return True
        if manifest.get("data_classification") == "synthetic":
            return False
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if "study" not in (reader.fieldnames or []):
            raise SystemExit("Effect table requires a study column")
        return any(str(row.get("study", "")) in _registry_ids() for row in reader)


def _code_hashes() -> dict[str, str]:
    return {relative: _sha256(ROOT / relative) for relative in _CODE_FILES if (ROOT / relative).is_file()}


def _safe_feature_metadata(metadata: Mapping) -> dict:
    allowed = {
        "scale_rule", "representation", "probe_rule", "probe_counts",
        "unmapped_probes", "gene_map_rows", "score_rule",
        "source_scale_rule", "coverage_policy", "input_kind",
        "recount3_non_primary_dropped",
    }
    return {key: value for key, value in metadata.items() if key in allowed}


def _write_tsv(path: Path, rows, columns) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
