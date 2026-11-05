"""Command line interface for the Paper A A-META modules."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Mapping

from tools.a_cohorts.view import REPRESENTATION_FILE, cohort_view
from tools.a_meta.effects import EFFECT_COLUMNS, study_effects
from tools.a_meta.features import (
    AVAILABLE_PANEL_IDS,
    FeatureTable,
    GENE_ALIAS_ADDENDUM_PATH,
    TARGETED_SUBSET_STUDIES,
    _panel_definitions,
    _gene_table,
    build_feature_table,
    read_external_feature_table,
    read_feature_table,
    write_feature_table,
    _resolution_targets,
    _panel_coverage90_table,
    _panel_member_coverage,
    _panel_table,
    _gse176307_source_hashes,
)
from tools.a_meta.provenance import (
    SYNTHETIC_FIXTURE_PRODUCER,
    canonical_sha256,
    is_locked_study,
    known_cohort_ids,
    effect_input_payload,
    validate_effect_file_manifest,
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
    "tools/a_meta/endpoint_definitions.py",
    "tools/a_meta/features.py",
    "tools/a_meta/provenance.py",
    "tools/a_meta/r_manifest.py",
    "tools/a_meta/synthesis.py",
    "tools/a_meta/frozen.py",
    "tools/a_meta/random_streams.py",
    "tools/a_cohorts/view.py",
    "tools/a_cohorts/core.py",
    "tools/a_scoring/__init__.py",
    "tools/a_scoring/core.py",
    "tools/a_p2/build.py",
    "tools/r_bridge/__init__.py",
    "r/R/bridge.R",
    "r/scripts/singscore.R",
    "r/R/random_streams.R",
    "tools/a_bulk/core.py",
    "r/scripts/fgsea_rank.R",
    "tools/sc/prostate.py",
    "tools/sc/cli.py",
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

    coverage_parser = commands.add_parser(
        "coverage", help="Write outcome-blind panel, 90% sensitivity, and CYT availability for signed cohorts"
    )
    coverage_parser.add_argument("--runtime", type=Path)
    coverage_parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/cohorts/PANEL_COVERAGE.tsv"
    )

    effects_parser = commands.add_parser("effects", help="Estimate within-study Hedges-g effects")
    effects_parser.add_argument("--cohort", required=True)
    effects_parser.add_argument("--runtime", type=Path)
    effects_parser.add_argument("--results", type=Path)
    effects_parser.add_argument("--endpoint-family", choices=("all", "orr", "clinical_benefit", "source_label"), default="all")
    effects_parser.add_argument(
        "--unit-family",
        choices=(
            "all", "gene", "m5m6_gene", "panel", "panel_coverage90", "pathway",
            "pathway_coverage90", "pathway_common", "targeted_subset", "fraction",
        ),
        default="all",
    )
    effects_parser.add_argument("--adjusted", action="store_true")
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
    results_root = _results_root(getattr(args, "results", None))
    if args.command == "features":
        _features(args, results_root)
    elif args.command == "effects":
        _effects(args, results_root)
    elif args.command == "synthesize":
        _synthesize(args, results_root)
    else:
        _coverage(args)
    return 0


def _features(args, results_root: Path) -> None:
    view = cohort_view(args.cohort, args.runtime)
    dataset_dir = results_root / args.cohort
    output_dir = dataset_dir / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    platform = str(view.metadata.representation.platform).casefold()
    targeted = platform in {"targeted_rna", "nanostring"}
    common = {
        "runtime": args.runtime,
        "gene_map": args.gene_map,
        "gtf_path": args.gtf,
    }
    tables: dict[str, FeatureTable] = {}
    if not targeted:
        tables["gene"] = build_feature_table(view, "gene", **common)
    tables["m5m6_gene"] = build_feature_table(view, "m5m6_gene", **common)
    tables["panel"] = build_feature_table(view, "panel", **common)
    tables["panel_coverage90"] = build_feature_table(view, "panel_coverage90", **common)
    if not targeted:
        for family in ("pathway", "pathway_coverage90", "pathway_common"):
            tables[family] = build_feature_table(
                view,
                family,
                gene_sets=args.gene_sets,
                r_out_dir=output_dir / f"R-singscore-{family}",
                **common,
            )
    else:
        if args.cohort in TARGETED_SUBSET_STUDIES:
            tables["targeted_subset"] = build_feature_table(view, "targeted_subset", **common)
    if args.external_table is not None:
        tables["fraction"] = read_external_feature_table(
            args.external_table,
            cohort_id=args.cohort,
            expected_patients=len(view.clinical_rows),
        )

    output_hashes = {}
    table_stats = {}
    feature_filenames = {
        "gene": "genes.tsv",
        "m5m6_gene": "m5m6_genes.tsv",
        "panel": "panels.tsv",
        "panel_coverage90": "panel_coverage90.tsv",
        "pathway": "pathways.tsv",
        "pathway_coverage90": "pathways_coverage90.tsv",
        "pathway_common": "pathways_common.tsv",
        "targeted_subset": "targeted_subset.tsv",
        "fraction": "fractions.tsv",
    }
    for family, table in tables.items():
        table_path = output_dir / feature_filenames[family]
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
            "complete": str(_coverage_complete(details.get("complete", False))).lower(),
            "missing": ",".join(details.get("missing", ())),
            "scorable": str(_coverage_complete(details.get("scorable", details.get("complete", False)))).lower(),
            "fixed_subset": ";".join(details.get("fixed_subset", ())),
            "reason": details.get("reason", ""),
            "sensitivity_label": table.metadata.get("sensitivity_label", ""),
        }
        for family, table in tables.items()
        for unit, details in table.coverage.items()
    ]
    coverage_path = output_dir / "coverage.tsv"
    _write_tsv(
        coverage_path,
        coverage_rows,
        ("unit_family", "unit", "n_found", "n_total", "complete", "missing", "scorable", "fixed_subset", "reason", "sensitivity_label"),
    )
    output_hashes[coverage_path.name] = _sha256(coverage_path)
    for family, table in tables.items():
        if "r_manifest" not in table.metadata:
            continue
        r_dir = output_dir / f"R-singscore-{family}"
        for name in ("scores.tsv", "coverage.tsv", "sessionInfo.txt", "manifest.json"):
            path = r_dir / name
            if path.is_file():
                output_hashes[path.relative_to(output_dir).as_posix()] = _sha256(path)

    input_hashes = {
        "cohort_expression": _sha256(view.expression_path),
        "cohort_clinical": _sha256(view.expression_path.parent / "clinical.tsv"),
        "representation_registry": _sha256(REPRESENTATION_FILE),
        "cohort_registry": _sha256(REGISTRY),
        "panel_registry": _sha256(PANEL_REGISTRY_PATH),
        "gene_aliases": _sha256(ALIAS_TABLE_PATH),
        "gene_alias_addendum": _sha256(GENE_ALIAS_ADDENDUM_PATH),
        "hallmark_identifier_proposals": _sha256(ROOT / "docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv"),
    }
    if "gene" in tables:
        input_hashes.update(tables["gene"].metadata.get("source_inputs_sha256", {}))
    elif "m5m6_gene" in tables:
        input_hashes.update(tables["m5m6_gene"].metadata.get("source_inputs_sha256", {}))
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
    if any(family in tables for family in ("pathway", "pathway_coverage90", "pathway_common", "targeted_subset")):
        input_hashes["hallmark_gene_sets"] = _sha256(
            args.gene_sets or (ROOT / "specs/amendments/2026-11-04-numerical-freeze/hallmark_2026.1.Hs.gmt")
        )
    if "pathway_common" in tables:
        input_hashes["common_gene_table"] = _sha256(ROOT / "docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv")
    if args.external_table is not None:
        input_hashes["external_patient_table"] = _sha256(args.external_table)

    r_manifests = {
        family: table.metadata["r_manifest"]
        for family, table in tables.items()
        if "r_manifest" in table.metadata
    }
    panel_coverage = _panel_coverage_counts(coverage_rows)
    panel_coverage90 = _panel_coverage90_counts(coverage_rows)
    manifest = {
        "data_classification": "real",
        "cohort": args.cohort,
        "inputs_sha256": input_hashes,
        "code_sha256": _code_hashes(),
        "outputs_sha256": output_hashes,
        "feature_tables": table_stats,
        "row_identity_sha256": _cohort_row_identity_sha256(view),
        "effect_input_sha256": {
            family: canonical_sha256(effect_input_payload(view, table))
            for family, table in tables.items()
        },
        "feature_metadata": {
            family: _safe_feature_metadata(table.metadata)
            for family, table in tables.items()
        },
        "panel_coverage": {
            "complete": panel_coverage[0],
            "incomplete": panel_coverage[1],
        },
        "panel_coverage90": {
            "met": panel_coverage90[0],
            "not_met": panel_coverage90[1],
            "sensitivity_label": "sensitivity only; does not support claims alone",
            "rule": "one fixed study subset of at least 90%; any patient missing a subset member gets NA",
        },
        "custom_method_ids": {
            family: table.metadata.get("custom_method_ids", {})
            for family, table in tables.items()
            if table.metadata.get("custom_method_ids")
        },
        "sensitivity_families": sorted(family for family in tables if family in {
            "panel_coverage90", "pathway_coverage90", "pathway_common", "targeted_subset"
        }),
        "panel_registry_note": "Eleven frozen custom expression features, including Hallmark IFN-gamma.",
        "R_manifests": r_manifests,
        "patient_identifier_policy": "zero-based row index only; source identifiers are not exported",
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    for family, stats in table_stats.items():
        print(f"cohort={args.cohort} family={family} rows={stats['rows']} columns={stats['columns']} units={stats['units']}")
    print(f"cohort={args.cohort} panel_coverage_complete={manifest['panel_coverage']['complete']} panel_coverage_incomplete={manifest['panel_coverage']['incomplete']}")


def _effects(args, results_root: Path) -> None:
    if getattr(args, "adjusted", False):
        raise SystemExit(
            "Adjusted models are unavailable: clinical covariate sets and missingness rules are not frozen"
        )
    if is_locked_study(args.cohort):
        raise SystemExit("IMvigor210 is a locked final test and is refused by A-META")
    is_real = _is_real_cohort(args.cohort)
    if is_real and not args.allow_outcomes:
        raise SystemExit("Real-cohort effects require the explicit --allow-outcomes flag")

    view = cohort_view(args.cohort, args.runtime)
    feature_dir = results_root / args.cohort / "features"
    feature_manifest_path = feature_dir / "manifest.json"
    feature_manifest = _validate_feature_manifest(view, feature_dir, args.cohort, args.runtime)
    if not is_real:
        if feature_manifest.get("data_classification") != "synthetic":
            raise SystemExit("Unknown-cohort effects require a hash-matched synthetic feature fixture")
        if feature_manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER:
            raise SystemExit("Synthetic feature classification was not written by the fixture path")
    families = (
        (
            "gene", "m5m6_gene", "panel", "panel_coverage90", "pathway",
            "pathway_coverage90", "pathway_common", "targeted_subset", "fraction",
        )
        if args.unit_family == "all"
        else (args.unit_family,)
    )
    feature_paths = _manifested_feature_files(feature_dir, feature_manifest, families)
    if "panel_coverage90" in families and "panel_coverage90" not in feature_paths:
        raise SystemExit(
            "Feature bundle is missing required panel_coverage90.tsv; rebuild features first"
        )
    endpoints = view.metadata.endpoint_families if args.endpoint_family == "all" else (args.endpoint_family,)
    results = []
    input_hashes = {
        "cohort_expression": _sha256(view.expression_path),
        "cohort_clinical": _sha256(view.expression_path.parent / "clinical.tsv"),
    }
    for unit_family in families:
        feature_path = feature_paths.get(unit_family)
        if feature_path is None:
            continue
        coverage_path = feature_dir / "coverage.tsv"
        table = read_feature_table(
            feature_path,
            cohort_id=args.cohort,
            unit_family=unit_family,
            n_patients=len(view.clinical_rows),
            coverage_path=coverage_path,
            metadata=feature_manifest.get("feature_metadata", {}).get(unit_family, {}),
        )
        input_hashes[f"{unit_family}_features"] = _sha256(feature_path)
        input_hashes["feature_coverage"] = _sha256(coverage_path)
        for endpoint in endpoints:
            results.extend(study_effects(
                view,
                table,
                endpoint,
                by_drug_class=not args.no_drug_class,
                allow_outcomes=args.allow_outcomes,
                provenance_manifest=feature_manifest_path,
            ))
    output_dir = results_root / args.cohort / "effects"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "effects.tsv"
    _write_tsv(output_path, results, EFFECT_COLUMNS)
    manifest = {
        "data_classification": "real" if is_real else "synthetic",
        "cohort": args.cohort,
        "inputs_sha256": input_hashes,
        "code_sha256": _code_hashes(),
        "outputs_sha256": {output_path.name: _sha256(output_path)},
        "effect_variance": "metafor escalc(measure='SMD', vtype='LS'): N/(n_R*n_NR) + g^2/(2N), with exact gamma Hedges correction",
        "adjustment": "unadjusted only",
        "method_ids": sorted({str(row.get("method_id", "")) for row in results if row.get("method_id")}),
    }
    if not is_real:
        manifest.update({
            "producer": SYNTHETIC_FIXTURE_PRODUCER,
            "manifest_version": 1,
            "kind": "effect_table",
            "cohort_ids": [args.cohort],
        })
    manifest["outputs_sha256"] = {output_path.name: _sha256(output_path)}
    _write_json(output_dir / "manifest.json", manifest)
    print(f"cohort={args.cohort} effect_rows={len(results)} columns={len(EFFECT_COLUMNS)}")


def _synthesize(args, results_root: Path) -> None:
    try:
        _, real_input = validate_effect_file_manifest(args.effects, allow_outcomes=args.allow_outcomes)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    run_hash = _sha256(args.effects)[:10]
    run_name = args.run or f"{args.stratum}-{run_hash}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_name):
        raise SystemExit("Run name may contain only letters, numbers, dots, underscores, and hyphens")
    output_dir = results_root / "meta" / run_name
    result = synthesize(
        args.effects,
        args.stratum,
        output_dir=output_dir,
        allow_outcomes=args.allow_outcomes,
        provenance_manifest=args.effects.parent / "manifest.json",
    )
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


def _coverage(args) -> None:
    """Write patient-free coverage counts for all signed development cohorts."""
    panel_definitions = _panel_definitions(AVAILABLE_PANEL_IDS)
    rows = []
    cohort_ids = _signed_development_cohorts()
    for cohort_id in cohort_ids:
        view = cohort_view(cohort_id, args.runtime)
        genes = _gene_table(
            view,
            runtime=args.runtime,
            gene_map=None,
            gtf_path=None,
            probe_map=None,
            target_symbols=_resolution_targets(panel_definitions),
        )
        available = set(genes.values_by_unit)
        complete_panels = _panel_table(view, genes, panel_definitions)
        coverage90_panels = _panel_coverage90_table(view, genes, panel_definitions)
        gzma_present = "GZMA" in available
        prf1_present = "PRF1" in available
        representation = view.metadata.representation
        unit = str(representation.unit).casefold()
        platform = str(representation.platform).casefold()
        transform = str(representation.transform).casefold()
        linear_tpm_available = (
            cohort_id == "gse176307"
            or (
                transform == "linear"
                and (
                    unit == "tpm"
                    or (platform == "rnaseq" and unit in {"fpkm", "rpkm"})
                )
            )
        )
        for panel_id, members in panel_definitions.items():
            main_details = _panel_member_coverage(genes.values_by_unit, members)
            sensitivity_details = coverage90_panels.coverage[panel_id]
            main_complete = main_details["n_found"] == len(members)
            rows.append({
                "cohort": cohort_id,
                "panel": panel_id,
                "n_found": main_details["n_found"],
                "n_total": len(members),
                "complete": str(main_complete).lower(),
                "coverage90": str(sensitivity_details["complete"]).lower(),
                "missing": ",".join(main_details["missing"]),
                "n_patients": genes.n_patients,
                "patients_complete": sum(value is not None for value in complete_panels.values_by_unit[panel_id]),
                "patients_coverage90": sum(value is not None for value in coverage90_panels.values_by_unit[panel_id]),
                "cyt_gzma_present": str(gzma_present).lower(),
                "cyt_prf1_present": str(prf1_present).lower(),
                "cyt_complete": str(gzma_present and prf1_present).lower(),
                "linear_tpm_available": str(linear_tpm_available).lower(),
            })
    columns = (
        "cohort", "panel", "n_found", "n_total", "complete", "coverage90", "missing",
        "n_patients", "patients_complete", "patients_coverage90",
        "cyt_gzma_present", "cyt_prf1_present", "cyt_complete", "linear_tpm_available",
    )
    _write_tsv(args.output, rows, columns)
    output_path = Path(args.output).expanduser().resolve()
    output_label = output_path.relative_to(ROOT).as_posix() if output_path.is_relative_to(ROOT) else output_path.name
    print(f"coverage_cohorts={len(cohort_ids)} panels={len(panel_definitions)} rows={len(rows)} output={output_label}")


def _signed_development_cohorts() -> tuple[str, ...]:
    with REGISTRY.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    return tuple(
        row["cohort_id"]
        for row in rows
        if row["role"].casefold() == "development" and row["status"].startswith("SIGNED")
    )


def _results_root(argument: Path | None) -> Path:
    if argument is not None:
        return argument.expanduser()
    configured = os.environ.get("THESIS_RESULTS")
    if configured:
        return Path(configured).expanduser()
    thesis_root = ROOT.parent.parent if ROOT.parent.name == "worktrees" else ROOT.parent
    return thesis_root / "results" / "A"


def _registry_ids() -> set[str]:
    return known_cohort_ids()


def _is_real_cohort(value: str) -> bool:
    return value in _registry_ids()


def _validate_feature_manifest(view, feature_dir: Path, cohort_id: str, runtime=None) -> dict:
    manifest_path = feature_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit("Feature manifest is missing or malformed") from error
    if not isinstance(manifest, dict) or manifest.get("cohort") != cohort_id:
        raise SystemExit("Feature manifest cohort does not match the loaded cohort")
    if cohort_id in _registry_ids() and manifest.get("data_classification") != "real":
        raise SystemExit("A known signed cohort cannot be classified as synthetic")
    expected_inputs = {
        "cohort_expression": _sha256(view.expression_path),
        "cohort_clinical": _sha256(view.expression_path.parent / "clinical.tsv"),
    }
    stored_inputs = manifest.get("inputs_sha256", {})
    if not isinstance(stored_inputs, Mapping):
        raise SystemExit("Feature manifest has invalid input identities")
    if any(stored_inputs.get(name) != expected for name, expected in expected_inputs.items()):
        raise SystemExit("Feature inputs are stale relative to the current cohort view")
    expected_analysis_inputs = {
        "representation_registry": _sha256(REPRESENTATION_FILE),
        "cohort_registry": _sha256(REGISTRY),
        "panel_registry": _sha256(PANEL_REGISTRY_PATH),
        "gene_aliases": _sha256(ALIAS_TABLE_PATH),
        "gene_alias_addendum": _sha256(GENE_ALIAS_ADDENDUM_PATH),
        "hallmark_identifier_proposals": _sha256(ROOT / "docs/cohorts/HALLMARK_IDENTIFIER_PROPOSALS.tsv"),
    }
    declared_feature_tables = manifest.get("feature_tables", {})
    if any(family in declared_feature_tables for family in (
        "pathway", "pathway_coverage90", "pathway_common", "targeted_subset"
    )):
        expected_analysis_inputs["hallmark_gene_sets"] = _sha256(
            ROOT / "specs/amendments/2026-11-04-numerical-freeze/hallmark_2026.1.Hs.gmt"
        )
    if "pathway_common" in declared_feature_tables:
        expected_analysis_inputs["common_gene_table"] = _sha256(
            ROOT / "docs/cohorts/HALLMARK_BRIDGING_COMMON_GENES.tsv"
        )
    if any(
        stored_inputs.get(name) != expected
        for name, expected in expected_analysis_inputs.items()
    ):
        raise SystemExit("Feature bundle analysis input identities do not match current files")
    if manifest.get("code_sha256") != _code_hashes():
        raise SystemExit("Feature bundle code identity does not match current A-META code")
    if manifest.get("row_identity_sha256") != _cohort_row_identity_sha256(view):
        raise SystemExit("Feature rows do not match the current cohort-view row identities")
    if cohort_id == "gse176307":
        feature_metadata = manifest.get("feature_metadata", {})
        gene_metadata = feature_metadata.get("gene", {}) if isinstance(feature_metadata, Mapping) else {}
        if not isinstance(gene_metadata, Mapping):
            raise SystemExit("GSE176307 feature bundle has no Salmon TPM source metadata")
        if (
            gene_metadata.get("source_route")
            != "official Salmon TPM via the A-P2 GSE176307 assay mapping"
            or gene_metadata.get("scale_rule")
            != "log2(TPM+1); official GSE176307 Salmon TPM"
        ):
            raise SystemExit("GSE176307 feature bundle does not use the current Salmon TPM route")
        expected_source_hashes = _gse176307_source_hashes(view, runtime)
        stored_source_hashes = gene_metadata.get("source_inputs_sha256")
        if stored_source_hashes != expected_source_hashes or any(
            stored_inputs.get(name) != digest
            for name, digest in expected_source_hashes.items()
        ):
            raise SystemExit("GSE176307 feature source identities do not match current Salmon TPM inputs")
    outputs = manifest.get("outputs_sha256", {})
    if not outputs:
        raise SystemExit("Feature manifest has no output hashes")
    for name, expected_hash in outputs.items():
        output_path = (feature_dir / name).resolve()
        if not output_path.is_relative_to(feature_dir.resolve()):
            raise SystemExit("Feature manifest contains an output path outside its feature directory")
        if not output_path.is_file() or _sha256(output_path) != expected_hash:
            raise SystemExit(f"Feature output hash mismatch: {name}")
    return manifest


def _manifested_feature_files(feature_dir: Path, manifest: Mapping, families) -> dict[str, Path]:
    """Return only feature tables named in the current manifest and hash list."""
    feature_tables = manifest.get("feature_tables", {})
    outputs = manifest.get("outputs_sha256", {})
    if not isinstance(feature_tables, Mapping) or not isinstance(outputs, Mapping):
        raise SystemExit("Feature manifest has invalid feature-table or output declarations")
    filenames = {
        "gene": "genes.tsv",
        "m5m6_gene": "m5m6_genes.tsv",
        "panel": "panels.tsv",
        "panel_coverage90": "panel_coverage90.tsv",
        "pathway": "pathways.tsv",
        "pathway_coverage90": "pathways_coverage90.tsv",
        "pathway_common": "pathways_common.tsv",
        "targeted_subset": "targeted_subset.tsv",
        "fraction": "fractions.tsv",
    }
    requested = set(families)
    result = {}
    for family, filename in filenames.items():
        path = feature_dir / filename
        declared = family in feature_tables and filename in outputs
        if path.is_file() and not declared:
            warnings.warn(
                f"Ignoring unlisted feature file {filename}",
                RuntimeWarning,
                stacklevel=2,
            )
        if family in requested and declared:
            result[family] = path
    return result


def _cohort_row_identity_sha256(view) -> str:
    identities = [
        {
            "patient": str(row.get("patient_id", "")),
            "sample": str(row.get("sample_id", "")),
            "timepoint": str(row.get("timepoint", "")),
        }
        for row in view.clinical_rows
    ]
    return canonical_sha256(identities)


def _coverage_complete(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().casefold()
        if normalised in {"true", "1"}:
            return True
        if normalised in {"false", "0"}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ValueError(f"Invalid coverage boolean: {value!r}")


def _panel_coverage_counts(rows) -> tuple[int, int]:
    panel_rows = [row for row in rows if row["unit_family"] == "panel"]
    complete = sum(_coverage_complete(row["complete"]) for row in panel_rows)
    return complete, len(panel_rows) - complete


def _panel_coverage90_counts(rows) -> tuple[int, int]:
    panel_rows = [row for row in rows if row["unit_family"] == "panel_coverage90"]
    met = sum(_coverage_complete(row["complete"]) for row in panel_rows)
    return met, len(panel_rows) - met


def _code_hashes() -> dict[str, str]:
    return {relative: _sha256(ROOT / relative) for relative in _CODE_FILES if (ROOT / relative).is_file()}


def _safe_feature_metadata(metadata: Mapping) -> dict:
    allowed = {
        "scale_rule", "representation", "probe_rule", "probe_counts",
        "unmapped_probes", "gene_map_rows", "score_rule",
        "source_scale_rule", "coverage_policy", "input_kind",
        "recount3_non_primary_dropped", "duplicate_gene_rule", "duplicate_gene_counts",
        "duplicate_gene_symbols", "source_route", "source_inputs_sha256", "sensitivity_label",
        "patients_with_tpm_assay", "patients_without_tpm_assay",
        "method_id_by_unit", "custom_method_ids", "m5m6_gene_units", "claim_scope",
        "source_gene_sets_sha256", "source_gene_sets_collection", "common_gene_table_sha256",
        "membership_sha256", "test_only_gene_sets",
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
