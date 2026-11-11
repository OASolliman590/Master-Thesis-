"""Outcome-free pairing CLI and invented-data demonstration."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict, fields
from pathlib import Path

from tools.a_meta.provenance import canonical_sha256
from tools.a1.authorization import (
    check_path_separation,
    guard_path,
    prepare_output_directory,
    read_released_inputs,
    sha256_file,
    validate_user_release,
    validate_output_directory,
)
from tools.a1.analysis import (
    N13Acceptance,
    N13Policy,
    fit_two_timepoint,
    run_released_synthesis,
    validate_n13_policy_payload,
    write_synthetic_analysis_manifest,
)
from tools.a1.pairing import (
    CANONICAL_COLUMNS,
    CrosswalkAcceptance,
    PairingPolicy,
    PolicyAcceptance,
    SourceColumns,
    WindowRule,
    _guard_study_id,
    build_pairs,
    read_specimens,
    validate_pairing_policy_contract,
    validate_pairing_policy,
    validate_real_source_columns,
    write_pair_products,
    write_synthetic_pair_manifest,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.a1")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="run the invented outcome-free pairing demonstration")
    demo.add_argument("--out", required=True, type=Path)

    analysis_demo = commands.add_parser(
        "demo-analysis", help="run the invented two-timepoint analysis demonstration"
    )
    analysis_demo.add_argument("--out", required=True, type=Path)

    pair = commands.add_parser("pair", help="build source-specific outcome-free longitudinal pairs")
    pair.add_argument("--study-id", required=True)
    pair.add_argument("--classification", required=True, choices=("real", "synthetic"))
    pair.add_argument("--input", required=True, type=Path)
    pair.add_argument("--columns-json", required=True, type=Path)
    pair.add_argument("--policy-json", required=True, type=Path)
    pair.add_argument("--acceptance-record-ref")
    pair.add_argument("--acceptance-decision-id")
    pair.add_argument("--fixture-only-policy", action="store_true")
    pair.add_argument("--provenance-manifest", type=Path)
    pair.add_argument("--input-manifest", type=Path)
    pair.add_argument("--release-record", type=Path)
    pair.add_argument("--use-gide-crosswalk", action="store_true")
    pair.add_argument("--gide-crosswalk-json", type=Path)
    pair.add_argument("--crosswalk-input-manifest", type=Path)
    pair.add_argument("--crosswalk-release-record", type=Path)
    pair.add_argument("--crosswalk-acceptance-ref")
    pair.add_argument("--out", required=True, type=Path)

    released_commands = (
        "pair-to-analysis", "two-timepoint", "ancova", "repeated",
        "randomized-arm", "synthesize",
    )
    for name in released_commands:
        route = commands.add_parser(
            name,
            help="run one user-record-scoped A-LONG product from named released inputs",
        )
        route.add_argument("--input-manifest", required=True, type=Path)
        route.add_argument("--release-record", required=True, type=Path)
        route.add_argument("--policy-json", required=True, type=Path)
        route.add_argument("--out", required=True, type=Path)
        route.add_argument("--retention-dir", required=True, type=Path)
        route.add_argument(
            "--allow-outcomes",
            action="store_true",
            default=False,
            help="explicitly opt in to the exact user-record-scoped outcome fields for this future route",
        )

    args = parser.parse_args(argv)
    if args.command == "demo":
        return _demo(args.out)
    if args.command == "demo-analysis":
        return _demo_analysis(args.out)
    if args.command == "pair":
        return _pair(args)
    if args.command in released_commands:
        return _released_route(args)
    parser.error("unsupported command")
    return 2


def _pair(args) -> int:
    _guard_study_id(args.study_id, args.classification)
    if args.fixture_only_policy and args.classification != "synthetic":
        raise ValueError("--fixture-only-policy is restricted to invented data")
    if args.classification == "synthetic" and args.provenance_manifest is None:
        raise ValueError("Synthetic pair input requires --provenance-manifest")
    if args.classification == "real" and (args.input_manifest is None or args.release_record is None):
        raise PermissionError("Real pairing requires the named input manifest and approved N12 record")
    if args.gide_crosswalk_json is not None and not args.use_gide_crosswalk:
        raise ValueError("Gide crosswalk file is ignored unless --use-gide-crosswalk is explicit")
    if args.use_gide_crosswalk and args.gide_crosswalk_json is None:
        raise ValueError("Gide crosswalk activation requires a file and explicit acceptance record")
    if args.use_gide_crosswalk and args.classification == "synthetic" and not args.crosswalk_acceptance_ref:
        raise ValueError("Fixture Gide crosswalk activation requires its explicit fixture record label")
    if args.use_gide_crosswalk and args.classification == "real" and (
        args.crosswalk_input_manifest is None or args.crosswalk_release_record is None
    ):
        raise PermissionError("Real Gide crosswalk activation requires its own scoped user-release record")

    input_paths = {
        "source table": args.input,
        "column map": args.columns_json,
        "pairing policy": args.policy_json,
    }
    if args.provenance_manifest is not None:
        input_paths["provenance manifest"] = args.provenance_manifest
    if args.input_manifest is not None:
        input_paths["released input manifest"] = args.input_manifest
    if args.release_record is not None:
        input_paths["pairing user-release record"] = args.release_record
    if args.gide_crosswalk_json is not None:
        input_paths["Gide crosswalk"] = args.gide_crosswalk_json
    if args.crosswalk_input_manifest is not None:
        input_paths["Gide crosswalk manifest"] = args.crosswalk_input_manifest
    if args.crosswalk_release_record is not None:
        input_paths["Gide crosswalk user-release record"] = args.crosswalk_release_record
    guarded_inputs, guarded_outputs = check_path_separation(
        inputs=input_paths,
        outputs={"pairing product": args.out},
    )
    args.input = guarded_inputs["source table"]
    args.columns_json = guarded_inputs["column map"]
    args.policy_json = guarded_inputs["pairing policy"]
    if args.provenance_manifest is not None:
        args.provenance_manifest = guarded_inputs["provenance manifest"]
    if args.input_manifest is not None:
        args.input_manifest = guarded_inputs["released input manifest"]
    if args.release_record is not None:
        args.release_record = guarded_inputs["pairing user-release record"]
    if args.gide_crosswalk_json is not None:
        args.gide_crosswalk_json = guarded_inputs["Gide crosswalk"]
    if args.crosswalk_input_manifest is not None:
        args.crosswalk_input_manifest = guarded_inputs["Gide crosswalk manifest"]
    if args.crosswalk_release_record is not None:
        args.crosswalk_release_record = guarded_inputs["Gide crosswalk user-release record"]
    private_root = _private_output_root(
        guarded_outputs["pairing product"], classification=args.classification
    )
    args.out = validate_output_directory(
        guarded_outputs["pairing product"], private_root=private_root
    )

    columns_payload = _read_json_object(args.columns_json)
    policy_payload = _read_json_object(args.policy_json)
    columns = SourceColumns(**columns_payload)
    policy = _policy_from_json(policy_payload)
    column_map = columns.mapping()
    if args.classification == "real":
        validate_real_source_columns(column_map)
    if policy.study_id != args.study_id:
        raise ValueError("Pairing policy study ID does not match --study-id")
    validate_pairing_policy_contract(policy, args.classification)
    crosswalk = None
    released_pair_input = None
    if args.classification == "synthetic":
        if not args.acceptance_record_ref or not args.acceptance_decision_id:
            raise ValueError("Invented pairing requires an explicit fixture policy label")
        acceptance = PolicyAcceptance(
            decision_id=args.acceptance_decision_id,
            record_ref=args.acceptance_record_ref,
            fixture_only=args.fixture_only_policy,
        )
        if args.use_gide_crosswalk:
            mapping = _read_json_object(args.gide_crosswalk_json)
            crosswalk = CrosswalkAcceptance(
                mapping=mapping,
                record_ref=args.crosswalk_acceptance_ref,
                fixture_only=args.fixture_only_policy,
            )
    else:
        if args.use_gide_crosswalk:
            crosswalk = _read_user_crosswalk(
                args.gide_crosswalk_json,
                args.crosswalk_input_manifest,
                args.crosswalk_release_record,
                study_id=args.study_id,
            )
        released_pair_input = read_released_inputs(
            args.input_manifest,
            args.release_record,
            release_scope="N12_PAIRING",
            operation="pair",
            policy_sha256=canonical_sha256(asdict(policy)),
            expected_scope_bindings={
                "source_column_map_sha256": canonical_sha256(columns.mapping()),
                "window_policy_sha256": canonical_sha256({
                    "baseline_window": policy.baseline_window,
                    "baseline_hierarchy": policy.baseline_hierarchy,
                    "windows": [asdict(rule) for rule in policy.windows],
                }),
            },
            output_paths={"pairing product": args.out},
        )
        if set(released_pair_input.tables) != {"specimens"}:
            raise ValueError("N12 pairing input manifest must name exactly one specimens source")
        if released_pair_input.manifest["field_maps"]["specimens"] != columns.mapping():
            raise PermissionError("N12 named source columns do not match the explicit pairing column map")
        if released_pair_input.source_paths["specimens"] != args.input.resolve():
            raise PermissionError("N12 pairing source path differs from the declared --input path")
        decision = released_pair_input.authorization.record["decision"]["identity"]
        acceptance = PolicyAcceptance(
            decision_id=decision,
            record_ref=released_pair_input.authorization.record_sha256,
            authorization=released_pair_input.authorization,
        )

    validate_pairing_policy(
        policy,
        classification=args.classification,
        acceptance=acceptance,
        crosswalk=crosswalk,
        use_gide_crosswalk=args.use_gide_crosswalk,
    )

    prepare_output_directory(
        args.out,
        private_root=private_root,
    )

    if released_pair_input is None:
        rows = read_specimens(
            args.input,
            columns=columns,
            study_id=args.study_id,
            classification=args.classification,
            provenance_manifest=args.provenance_manifest,
        )
    else:
        rows = []
        for source_row in released_pair_input.tables["specimens"]:
            row = {name: str(source_row.get(name, "")) for name in CANONICAL_COLUMNS}
            if row["study_id"] != args.study_id:
                raise PermissionError("N12 pairing source rows do not match the released study identity")
            rows.append(row)
    result = build_pairs(
        rows,
        policy,
        classification=args.classification,
        acceptance=acceptance,
        crosswalk=crosswalk,
        use_gide_crosswalk=args.use_gide_crosswalk,
    )
    paths = write_pair_products(result, args.out)
    manifest = _write_pair_manifest(
        args.out,
        result,
        rows,
        args.classification,
        policy,
        columns.mapping(),
        acceptance,
        crosswalk,
        paths,
        input_manifest=args.input_manifest or args.provenance_manifest,
    )
    print(json.dumps({
        "pair_manifest": manifest.name,
        "patients_in": result.summary["patients_in"],
        "selected_pairs": result.summary["selected_pairs"],
        "missing_followups": len(result.missing_followups),
        "endpoint_evaluable_counts": None,
    }, sort_keys=True))
    return 0


def _released_route(args) -> int:
    """Run one real-input route only after its exact user-release record passes."""
    route_contracts = {
        "pair-to-analysis": ("N13_FEATURE_JOIN", "pair_to_analysis"),
        "two-timepoint": ("N13_TWO_TIMEPOINT", "fit_two_timepoint"),
        "ancova": ("N13_TWO_TIMEPOINT", "fit_two_timepoint"),
        "repeated": ("N13_REPEATED", "fit_repeated_windows"),
        "randomized-arm": ("N13_RANDOMIZED_ARM", "fit_randomized_arm"),
        "synthesize": ("N13_SYNTHESIS", "synthesize_effects"),
    }
    release_scope, operation = route_contracts[args.command]
    if args.allow_outcomes is not True:
        raise PermissionError("N13 outcome routes require the explicit --allow-outcomes option")
    guarded_inputs, guarded_outputs = check_path_separation(
        inputs={
            "released input manifest": args.input_manifest,
            "user-release record": args.release_record,
            "route policy": args.policy_json,
        },
        outputs={"product": args.out, "retention": args.retention_dir},
    )
    args.input_manifest = guarded_inputs["released input manifest"]
    args.release_record = guarded_inputs["user-release record"]
    args.policy_json = guarded_inputs["route policy"]
    private_root = _private_output_root(guarded_outputs["product"], classification="real")
    retention_root = _private_output_root(guarded_outputs["retention"], classification="real")
    args.out = validate_output_directory(guarded_outputs["product"], private_root=private_root)
    args.retention_dir = validate_output_directory(
        guarded_outputs["retention"], private_root=retention_root
    )
    policy_payload = _read_json_object(args.policy_json)
    if args.command == "pair-to-analysis":
        from tools.a1.features import fixed_long_feature_memberships, validate_feature_join_policy

        validate_feature_join_policy(policy_payload)
        expected_bindings = {
            "feature_membership_sha256": fixed_long_feature_memberships().membership_sha256,
            "representation_sha256": canonical_sha256(policy_payload.get("representation")),
        }
    elif args.command in {"two-timepoint", "ancova"}:
        expected_bindings = {
            "delta_method_id": policy_payload.get("delta_method_id"),
            "ancova_method_id": policy_payload.get("ancova_method_id"),
            "covariate_contract_sha256": canonical_sha256(policy_payload.get("covariates")),
        }
    elif args.command == "repeated":
        expected_bindings = {
            "repeated_method_id": policy_payload.get("repeated_method_id"),
            "selection_mode": policy_payload.get("repeated_selection_mode"),
            "window_set_sha256": canonical_sha256(policy_payload.get("repeated_windows")),
        }
    elif args.command == "randomized-arm":
        admission = policy_payload.get("randomization_admission")
        expected_bindings = {
            "randomized_method_id": policy_payload.get("randomized_arm_method_id"),
            "comparative_estimand_id": admission.get("comparative_estimand_id") if isinstance(admission, dict) else None,
            "randomization_receipt_sha256": admission.get("receipt_sha256") if isinstance(admission, dict) else None,
        }
    else:
        expected_bindings = {
            "meta_method_id": policy_payload.get("meta_method_id"),
            "multiplicity_contract_sha256": canonical_sha256({
                "panel_family_members": policy_payload.get("panel_family_members"),
                "m5m6_family_members": policy_payload.get("m5m6_family_members"),
                "fdr_denominator_policy": policy_payload.get("fdr_denominator_policy"),
            }),
            "source_overlap_contract_sha256": policy_payload.get("source_overlap_contract_sha256"),
        }
    if args.command != "pair-to-analysis":
        analysis_route = {
            "two-timepoint": "two_timepoint",
            "ancova": "two_timepoint",
            "repeated": "repeated",
            "randomized-arm": "randomized_arm",
            "synthesize": "synthesis",
        }[args.command]
        validate_n13_policy_payload(policy_payload, route=analysis_route)
    released = read_released_inputs(
        args.input_manifest,
        args.release_record,
        release_scope=release_scope,
        operation=operation,
        policy_sha256=canonical_sha256(policy_payload),
        expected_scope_bindings=expected_bindings,
        output_paths={"product": args.out, "retention": args.retention_dir},
        allow_outcomes=args.allow_outcomes,
    )
    if args.command == "pair-to-analysis":
        from tools.a1.features import build_pair_analysis_rows

        rows, coverage = build_pair_analysis_rows(
            released, policy=policy_payload, allow_outcomes=args.allow_outcomes
        )
        out_dir = prepare_output_directory(args.out, private_root=private_root)
        retention_dir = prepare_output_directory(args.retention_dir, private_root=retention_root)
        _write_rows_tsv(out_dir / "analysis_rows.tsv", rows)
        _write_rows_tsv(out_dir / "feature_coverage.tsv", coverage)
        support = []
        for study in sorted({row["study_id"] for row in rows}):
            for window in sorted({row["window_id"] for row in rows if row["study_id"] == study}):
                subset = [row for row in rows if row["study_id"] == study and row["window_id"] == window]
                support.append({
                    "study_id": study,
                    "window_id": window,
                    "record_type": "pairing_model_input",
                    "model": "",
                    "effect_role": "",
                    "n_pairs": len({row["pair_id"] for row in subset}),
                    "n_patients_input": len({row["patient_key"] for row in subset}),
                    "n_patients_used": "NA",
                    "n_observations_used": len(subset),
                    "n_R": "NA",
                    "n_NR": "NA",
                    "n_arm_ici": "NA",
                    "n_arm_combination": "NA",
                    "status": "FEATURE_JOIN_COMPLETE",
                    "reason": "endpoint_class_counts_unavailable",
                    "support_role": "feature_join_input_support",
                })
        _write_rows_tsv(
            out_dir / "longitudinal_support.tsv",
            support,
            columns=(
                "study_id", "window_id", "record_type", "model", "effect_role", "n_pairs",
                "n_patients_input", "n_patients_used", "n_observations_used", "n_R", "n_NR",
                "n_arm_ici", "n_arm_combination", "status", "reason", "support_role",
            ),
        )
        _write_rows_tsv(
            retention_dir / "released_input_receipt.tsv",
            [{
                "input_manifest_sha256": released.manifest_sha256,
                "user_release_record_sha256": released.authorization.record_sha256,
                "source_count": len(released.source_paths),
                "released_field_count": len(released.authorization.record["permitted_fields"]),
            }],
        )
        output_hashes = {
            path.name: sha256_file(path, label="A-LONG private feature output")
            for path in sorted(out_dir.iterdir())
        }
        manifest_path = out_dir / "feature_join_manifest.json"
        with manifest_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "schema": "a_long_feature_join_manifest_v1",
                "data_classification": "PRIVATE_PATIENT_LEVEL",
                "release_scope": release_scope,
                "policy_sha256": released.authorization.record["policy_sha256"],
                "input_manifest_sha256": released.manifest_sha256,
                "user_release_record_sha256": released.authorization.record_sha256,
                "output_sha256": output_hashes,
                "endpoint_evaluable_counts": None,
                "endpoint_status": "CLASS_COUNTS_NOT_REQUESTED",
            }, indent=2, sort_keys=True) + "\n")
        print(json.dumps({
            "data_classification": "PRIVATE_PATIENT_LEVEL",
            "product_manifest": manifest_path.name,
            "feature_units": len(coverage),
            "endpoint_evaluable_counts": None,
        }, sort_keys=True))
        return 0

    if args.command == "synthesize":
        result = run_released_synthesis(
            released_inputs=released,
            policy_payload=policy_payload,
            output_dir=args.out,
            retention_dir=args.retention_dir,
            allow_outcomes=args.allow_outcomes,
        )
    else:
        from tools.a1.analysis import run_released_analysis

        result = run_released_analysis(
            args.command,
            released_inputs=released,
            policy_payload=policy_payload,
            output_dir=args.out,
            retention_dir=args.retention_dir,
            allow_outcomes=args.allow_outcomes,
        )
    print(json.dumps({
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "product": args.command,
        "effects": len(result.effects),
        "policy_status": result.policy_status,
        "endpoint_class_counts": None,
    }, sort_keys=True))
    return 0


def _write_rows_tsv(path, rows, columns=None):
    path = guard_path(path, "private A-LONG TSV output")
    if path.exists():
        raise FileExistsError("A-LONG private output already exists")
    columns = tuple(columns or (tuple(rows[0]) if rows else ()))
    if not columns:
        raise ValueError("A-LONG private TSV output needs a declared schema")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(columns), delimiter="\t", lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})


def _demo(output_dir: Path) -> int:
    output_dir = prepare_output_directory(
        output_dir, private_root=_private_output_root(output_dir, classification="synthetic")
    )
    study_id = "a-long-synthetic-demo"
    rows = _demo_rows(study_id)
    input_dir = output_dir / "input"
    input_dir = prepare_output_directory(input_dir)
    input_path = input_dir / "invented_specimens.tsv"
    with input_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(CANONICAL_COLUMNS), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    provenance_path = input_dir / "input_provenance.json"
    write_synthetic_pair_manifest(input_path, provenance_path, study_id=study_id)
    columns = SourceColumns(**{name: name for name in CANONICAL_COLUMNS})
    policy = PairingPolicy(
        study_id=study_id,
        status="PROPOSED",
        decision_ref=None,
        baseline_window="fixture_baseline",
        windows=(
            WindowRule("fixture_baseline", "baseline", ("PRE_FIXTURE",)),
            WindowRule(
                "fixture_on_window",
                "followup",
                ("ON_FIXTURE",),
                day_interval=(8, 12),
                day_origin="invented-dose-origin",
                target_day=10,
            ),
        ),
        baseline_hierarchy=("source_primary", "source_secondary"),
        allowed_prior_treatment=("none",),
        allowed_disease_states=("no_progression",),
        allowed_regimen_states=("stable",),
        prefer_same_lesion=True,
        allow_different_lesion=False,
        endpoint_id="fixture-endpoint",
        admission_receipt="invented-N12-receipt",
    )
    selected_rows = read_specimens(
        input_path,
        columns=columns,
        study_id=study_id,
        classification="synthetic",
        provenance_manifest=provenance_path,
    )
    result = build_pairs(
        selected_rows,
        policy,
        classification="synthetic",
        acceptance=PolicyAcceptance("N12-fixture", "invented-demo-policy", fixture_only=True),
    )
    pair_output = output_dir / "pairing"
    prepare_output_directory(pair_output)
    paths = write_pair_products(result, pair_output)
    _write_pair_manifest(
        pair_output,
        result,
        selected_rows,
        "synthetic",
        policy,
        columns.mapping(),
        PolicyAcceptance("N12-fixture", "invented-demo-policy", fixture_only=True),
        None,
        paths,
        input_manifest=provenance_path,
    )
    print(json.dumps({
        "data_classification": "synthetic",
        "selected_pairs": result.summary["selected_pairs"],
        "patients_in": result.summary["patients_in"],
        "missing_followups": len(result.missing_followups),
        "policy_status": result.policy_status,
        "endpoint_evaluable_counts": None,
    }, sort_keys=True))
    return 0


def _demo_analysis(output_dir: Path) -> int:
    output_dir = prepare_output_directory(
        output_dir, private_root=_private_output_root(output_dir, classification="synthetic")
    )
    study_id = "a-long-synthetic-analysis-demo"
    rows = []
    groups = (
        ("R", (10.0, 12.0, 14.0, 16.0), 3.0, 0),
        ("NR", (0.0, 2.0, 4.0, 6.0), 0.0, 4),
    )
    for response, baselines, intercept, start in groups:
        for index, baseline in enumerate(baselines, start=start):
            rows.append({
                "study_id": study_id,
                "patient_key": f"invented-patient-{index:02d}",
                "pair_id": f"invented-pair-{index:02d}",
                "unit": "fixture-panel",
                "pre_value": baseline,
                "on_value": 0.5 * baseline + intercept,
                "response": response,
                "unit_family": "panel",
                "feature_method_id": "fixture_panel_score_v1",
                "analysis_method_id": "lm_change_response_covariates_v1",
                "endpoint_id": "FIXTURE_RESPONSE",
                "regimen_id": "FIXTURE_ICI_MONO",
                "window_id": "fixture_baseline_to_on",
                "assay_id": "fixture_tpm",
                "effect_scale_id": "FIXTURE_LOG2_TPMPLUS1_PANEL_MEAN",
                "panel_family": "FIXTURE_PANEL_FAMILY",
                "multiplicity_family_id": "FIXTURE_PANEL_MULTIPLICITY",
                "source_family_id": f"fixture-source-family-{study_id}",
                "overlap_receipt_id": hashlib.sha256(study_id.encode()).hexdigest(),
                "overlap_status": "DISJOINT_VERIFIED",
            })
    provenance_path = output_dir / "analysis_input_provenance.json"
    write_synthetic_analysis_manifest(
        provenance_path, rows, study_ids=(study_id,)
    )
    policy = N13Policy(
        status="PROPOSED",
        decision_ref=None,
        delta_method_id="lm_change_response_covariates_v1",
        ancova_method_id="lm_on_response_baseline_covariates_sensitivity_v1",
        repeated_method_id="lmerTest_lme4_response_window_random_intercept_v1",
        randomized_arm_method_id="lm_randomized_arm_change_contrast_v1",
        meta_method_id="metafor_REML_modified_KH_v1",
        df_method_id="residual_t_and_Satterthwaite_v1",
        covariates=(),
        repeated_windows=("baseline", "fixture_on"),
        min_repeated_patients=4,
        min_per_response_group=2,
        min_meta_k_pool=4,
        confidence_level=0.95,
        fdr_scope_id="predeclared_panel_families_v1",
    )
    result = fit_two_timepoint(
        rows,
        study_id=study_id,
        provenance_manifest=provenance_path,
        policy=policy,
        acceptance=N13Acceptance(
            decision_id="N13-fixture",
            record_ref="invented-analysis-demo",
            fixture_only=True,
        ),
        output_dir=output_dir / "analysis",
        retention_dir=output_dir / "retention",
    )
    print(json.dumps({
        "data_classification": "synthetic",
        "study_id": study_id,
        "policy_status": result.policy_status,
        "input_rows": len(rows),
        "effects": [
            {
                "model": row["model"],
                "estimate": row["estimate"],
                "status": row["status"],
                "effect_role": row["effect_role"],
            }
            for row in result.effects
        ],
        "provenance_manifest": provenance_path.name,
    }, sort_keys=True))
    return 0


def _demo_rows(study_id):
    def opaque(kind, index):
        token = hashlib.sha256(f"a-long-demo:{kind}:{index}".encode()).hexdigest()[:12]
        return f"synthetic-{token}"

    def specimen(patient_index, sample_role, category, day=""):
        return {
            "study_id": study_id,
            "patient_id": opaque("patient", patient_index),
            "specimen_id": opaque("specimen", f"{patient_index}:{sample_role}"),
            "assay_id": opaque("assay", f"{patient_index}:{sample_role}"),
            "timepoint_category": category,
            "collection_day": day,
            "day_precision": "exact" if day else "unknown",
            "index_episode": opaque("episode", patient_index),
            "exposure": "fixture_ici_only",
            "baseline_source": "source_primary",
            "prior_treatment": "none",
            "disease_state": "no_progression",
            "regimen_state": "stable",
            "compartment": "fixture_tumour",
            "platform": "rnaseq",
            "unit": "tpm",
            "assay_method": "fixture_whole_transcriptome",
            "assay_qualified": "yes",
            "lesion_id": opaque("lesion", patient_index),
            "source_locator": f"fixture://{sample_role}/{patient_index}",
            "source_confidence": "invented_high",
            "day_origin": "invented-dose-origin" if day else "unknown",
            "annotation_id": "fixture-annotation-v1",
            "measurement_comparability_id": "fixture-tpm-v1",
            "endpoint_id": "fixture-endpoint",
            "admission_receipt": "invented-N12-receipt",
        }

    return [
        specimen(0, "pre", "PRE_FIXTURE"),
        specimen(0, "on", "ON_FIXTURE", "9"),
        specimen(1, "pre", "PRE_FIXTURE"),
        specimen(1, "on", "ON_FIXTURE", "11"),
        specimen(2, "pre", "PRE_FIXTURE"),
    ]


def _policy_from_json(value):
    allowed = {field.name for field in fields(PairingPolicy)}
    if set(value) != allowed:
        raise ValueError("Pairing policy JSON must supply every declared source policy field exactly")
    windows = []
    for row in value["windows"]:
        payload = dict(row)
        payload["categories"] = tuple(payload["categories"])
        for name in ("allowed_window_disease_states", "allowed_window_regimen_states"):
            if name in payload:
                payload[name] = tuple(payload[name])
        if payload.get("day_interval") is not None:
            payload["day_interval"] = tuple(float(value) for value in payload["day_interval"])
        windows.append(WindowRule(**payload))
    value = dict(value)
    value["windows"] = tuple(windows)
    for name in ("baseline_hierarchy", "allowed_prior_treatment", "allowed_disease_states", "allowed_regimen_states"):
        value[name] = tuple(value[name])
    return PairingPolicy(**value)


def _read_json_object(path):
    try:
        guarded = guard_path(path, "JSON configuration")
        value = json.loads(guarded.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read JSON object: {Path(path).name}") from error
    if not isinstance(value, dict):
        raise ValueError("JSON configuration must be an object")
    return value


def _read_user_crosswalk(
    crosswalk_path, manifest_path, record_path, *, study_id, root=None, decisions_dir=None
):
    crosswalk_path = guard_path(crosswalk_path, "Gide crosswalk input")
    manifest_path = guard_path(manifest_path, "Gide crosswalk input manifest")
    record_path = guard_path(record_path, "Gide crosswalk user-release record")
    if len({crosswalk_path, manifest_path, record_path}) != 3:
        raise ValueError("Gide crosswalk inputs, manifest, and release record must be distinct")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermissionError("Gide crosswalk manifest is unavailable or malformed") from error
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema", "data_classification", "cohort_ids", "permitted_fields", "scope_bindings",
    }:
        raise PermissionError("Gide crosswalk manifest has missing or contradictory fields")
    bindings = manifest["scope_bindings"]
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        manifest["schema"] != "a_long_gide_crosswalk_manifest_v1"
        or manifest["data_classification"] != "PRIVATE_PATIENT_LEVEL"
        or manifest["cohort_ids"] != [study_id]
        or not isinstance(bindings, dict)
        or set(bindings) != {"crosswalk_sha256"}
        or not isinstance(bindings.get("crosswalk_sha256"), str)
        or len(bindings["crosswalk_sha256"]) != 64
    ):
        raise PermissionError("Gide crosswalk manifest does not bind one exact study and mapping")
    release_bindings = {
        "crosswalk_sha256": bindings["crosswalk_sha256"],
        "crosswalk_source_manifest_sha256": manifest_sha256,
    }
    permitted_fields = manifest["permitted_fields"]
    expected_policy_hash = canonical_sha256({
        "study_id": study_id,
        **release_bindings,
    })
    authorization = validate_user_release(
        record_path,
        release_scope="N12_GIDE_CROSSWALK",
        operation="accept_gide_crosswalk",
        policy_sha256=expected_policy_hash,
        input_manifest_sha256=manifest_sha256,
        source_paths={"crosswalk": crosswalk_path},
        cohorts=(study_id,),
        permitted_fields=permitted_fields,
        root=root,
        decisions_dir=decisions_dir,
        extra_bindings=release_bindings,
    )
    mapping = _read_json_object(crosswalk_path)
    if not mapping or canonical_sha256(mapping) != bindings["crosswalk_sha256"]:
        raise PermissionError("Gide crosswalk bytes do not match the approved mapping hash")
    return CrosswalkAcceptance(
        mapping=mapping,
        record_ref=authorization.record_sha256,
        authorization=authorization,
    )


def _private_output_root(path, *, classification):
    root = Path(__file__).resolve().parents[2]
    try:
        relative = Path(path).relative_to(root)
    except ValueError:
        if classification == "real":
            raise PermissionError("Real patient-level outputs must stay under results/ or .scratch/")
        return None
    if not relative.parts or relative.parts[0] not in {"results", ".scratch"}:
        raise PermissionError("Patient-level outputs inside the worktree must stay under results/ or .scratch/")
    return root / relative.parts[0]


def _write_pair_manifest(
    output_dir,
    result,
    rows,
    classification,
    policy,
    column_map,
    acceptance,
    crosswalk,
    paths,
    *,
    input_manifest=None,
):
    output_dir = Path(output_dir)
    output_dir = guard_path(output_dir, "pair manifest output directory")
    manifest_path = guard_path(output_dir / "pair_manifest.json", "pair manifest output")
    if manifest_path.exists():
        raise FileExistsError("A-LONG pair manifest output already exists")
    input_manifest_sha256 = (
        sha256_file(input_manifest, label="input provenance manifest")
        if input_manifest else None
    )
    output_hashes = {
        path.name: sha256_file(path, label="pair product") for path in paths.values()
    }
    manifest = {
        "manifest_version": 1,
        "data_classification": classification,
        "study_id": policy.study_id,
        "product": "outcome_free_pairing",
        "policy_status": result.policy_status,
        "policy_decision_ref": policy.decision_ref,
        "policy_sha256": canonical_sha256(asdict(policy)),
        "source_family_id": policy.source_family_id,
        "overlap_receipt_id": policy.overlap_receipt_id,
        "overlap_status": policy.overlap_status or "UNRESOLVED",
        "acceptance_decision_id": acceptance.decision_id,
        "acceptance_record_ref": acceptance.record_ref,
        "user_release_record_sha256": (
            acceptance.authorization.record_sha256 if acceptance.authorization is not None else None
        ),
        "selected_source_column_map": column_map,
        "selected_columns_sha256": canonical_sha256(rows),
        "input_provenance_manifest_sha256": input_manifest_sha256,
        "crosswalk_record_ref": crosswalk.record_ref if isinstance(crosswalk, CrosswalkAcceptance) else None,
        "crosswalk_release_record_sha256": (
            crosswalk.authorization.record_sha256
            if isinstance(crosswalk, CrosswalkAcceptance) and crosswalk.authorization is not None
            else None
        ),
        "output_sha256": output_hashes,
        "endpoint_evaluable_counts": None,
        "endpoint_status": "UNAVAILABLE_OUTCOME_LOCKED",
    }
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest_path


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
