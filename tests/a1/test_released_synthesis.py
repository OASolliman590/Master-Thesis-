from __future__ import annotations

import hashlib
import json
from dataclasses import fields

from tools.a_meta.provenance import canonical_sha256
from tools.a1.analysis import N13Policy, run_released_synthesis
from tools.a1.authorization import read_released_inputs
from tools.r_bridge import FakeR


def _write_tsv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write("\t".join(columns) + "\n")
        for row in rows:
            stream.write("\t".join(str(row.get(column, "")) for column in columns) + "\n")


def test_released_synthesis_accepts_only_hash_bound_invented_effect_and_overlap_inputs(tmp_path, monkeypatch):
    root = tmp_path / "invented-release-root"
    decisions = root / "docs" / "decisions"
    decisions.mkdir(parents=True)
    decision = decisions / "FAKE_N13_SYNTHESIS.md"
    decision.write_text("invented test decision; not a user signature\n", encoding="utf-8")
    study = "invented-release-study"
    source_family = "invented-source-family"
    effect_columns = (
        "study", "patient_set_id", "source_family_id", "overlap_receipt_id", "overlap_status",
        "unit_family", "unit", "panel_family", "multiplicity_family_id", "feature_method_id",
        "analysis_method_id", "endpoint_id", "regimen_id", "window_id", "assay_id",
        "effect_scale_id", "estimate", "se", "ci_lb", "ci_ub", "p_value", "status", "reason",
    )
    effect = {
        "study": study,
        "patient_set_id": hashlib.sha256(b"invented patient set").hexdigest(),
        "source_family_id": source_family,
        "overlap_receipt_id": hashlib.sha256(b"invented source receipt").hexdigest(),
        "overlap_status": "DISJOINT_VERIFIED",
        "unit_family": "panel",
        "unit": "fixture-panel",
        "panel_family": "A_LONG_CUSTOM",
        "multiplicity_family_id": "FIXTURE_PANELS",
        "feature_method_id": "A_LONG_STRICT_CUSTOM_PANEL_MEAN_SOURCE_SCALE",
        "analysis_method_id": "lm_change_response_covariates_v1",
        "endpoint_id": "invented-endpoint",
        "regimen_id": "invented-regimen",
        "window_id": "invented-window",
        "assay_id": "invented-assay",
        "effect_scale_id": "invented-log2-change",
        "estimate": "0.4",
        "se": "0.2",
        "ci_lb": "0.0",
        "ci_ub": "0.8",
        "p_value": "0.04",
        "status": "ESTIMABLE",
        "reason": "",
    }
    effects_path = tmp_path / "invented-effects.tsv"
    _write_tsv(effects_path, [effect], effect_columns)
    overlap_columns = (
        "study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256",
    )
    overlap_path = tmp_path / "invented-overlap-receipts.tsv"
    _write_tsv(overlap_path, [], overlap_columns)

    source_overlap_hash = hashlib.sha256(b"invented overlap contract").hexdigest()
    policy = {
        "status": "ACCEPTED",
        "decision_ref": decision.stem,
        "delta_method_id": "lm_change_response_covariates_v1",
        "ancova_method_id": "lm_on_response_baseline_covariates_sensitivity_v1",
        "repeated_method_id": "lmerTest_lme4_response_window_random_intercept_v1",
        "randomized_arm_method_id": "lm_randomized_arm_change_contrast_v1",
        "meta_method_id": "metafor_REML_modified_KH_v1",
        "df_method_id": "residual_t_and_Satterthwaite_v1",
        "covariates": [],
        "repeated_windows": ["baseline", "on"],
        "min_repeated_patients": 4,
        "min_per_response_group": 2,
        "min_meta_k_pool": 4,
        "confidence_level": 0.95,
        "fdr_scope_id": "predeclared_panel_families_v1",
        "repeated_selection_mode": "complete_declared_windows",
        "min_per_randomized_arm": 2,
        "panel_family_members": {"FIXTURE_PANELS": ["fixture-panel"]},
        "m5m6_family_members": ["fixture-gene"],
        "fdr_denominator_policy": "all_predeclared_members_missing_as_p1_v1",
        "source_overlap_contract_sha256": source_overlap_hash,
        "same_lesion_sensitivity_method_id": "lm_change_response_covariates_same_lesion_sensitivity_v1",
        "exact_day_sensitivity_method_id": "lm_change_response_covariates_exact_day_sensitivity_v1",
        "tighter_timing_sensitivity_method_id": "lm_change_response_covariates_tighter_timing_sensitivity_v1",
        "sensitivity_modes": [],
        "tighter_timing_max_deviation_days": None,
    }
    assert set(policy) == {field.name for field in fields(N13Policy)}
    multiplicity_hash = canonical_sha256({
        "panel_family_members": policy["panel_family_members"],
        "m5m6_family_members": policy["m5m6_family_members"],
        "fdr_denominator_policy": policy["fdr_denominator_policy"],
    })
    bindings = {
        "meta_method_id": policy["meta_method_id"],
        "multiplicity_contract_sha256": multiplicity_hash,
        "source_overlap_contract_sha256": source_overlap_hash,
    }
    source_tables = {"effects": (effects_path, effect_columns), "overlap_receipts": (overlap_path, overlap_columns)}
    field_maps = {name: {column: column for column in columns} for name, (_, columns) in source_tables.items()}
    identity_fields = {
        "effects": ["study", "source_family_id"],
        "overlap_receipts": ["study_a", "study_b", "source_family_a", "source_family_b"],
    }
    permitted_fields = sorted(f"{name}:{column}" for name, (_, columns) in source_tables.items() for column in columns)
    manifest = {
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": [study],
        "source_files": {name: str(path) for name, (path, _) in source_tables.items()},
        "field_maps": field_maps,
        "identity_fields": identity_fields,
        "permitted_fields": permitted_fields,
        "scope_bindings": bindings,
    }
    manifest_path = tmp_path / "invented-release-manifest.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_path.write_bytes(manifest_bytes)
    record = {
        "record_type": "a_long_user_release_v1",
        "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "release_scope": "N13_SYNTHESIS",
        "operation": "synthesize_effects",
        "decision": {
            "identity": decision.stem,
            "path": "docs/decisions/FAKE_N13_SYNTHESIS.md",
            "sha256": hashlib.sha256(decision.read_bytes()).hexdigest(),
        },
        "policy_sha256": canonical_sha256(policy),
        "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, (path, _) in source_tables.items()
        },
        "cohorts": [study],
        "permitted_fields": permitted_fields,
        **bindings,
    }
    record_path = tmp_path / "invented-user-release.json"
    record_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    released = read_released_inputs(
        manifest_path,
        record_path,
        release_scope="N13_SYNTHESIS",
        operation="synthesize_effects",
        policy_sha256=canonical_sha256(policy),
        expected_scope_bindings=bindings,
        root=root,
        decisions_dir=decisions,
        allow_outcomes=True,
    )

    # Exercise the public released route with an invented runner; production path guards
    # are covered separately and are left active outside this test's temporary root.
    monkeypatch.setattr("tools.a1.analysis._safe_real_output_dir", lambda path: path)
    output = """unit_family\tunit\tpanel_family\tmultiplicity_family_id\tfeature_method_id\tanalysis_method_id\tendpoint_id\tregimen_id\twindow_id\tassay_id\teffect_scale_id\tk\tstatus\treason\testimate\tse\tci_lb\tci_ub\tp_value\n""" \
        "panel\tfixture-panel\tA_LONG_CUSTOM\tFIXTURE_PANELS\tA_LONG_STRICT_CUSTOM_PANEL_MEAN_SOURCE_SCALE\tlm_change_response_covariates_v1\tinvented-endpoint\tinvented-regimen\tinvented-window\tinvented-assay\tinvented-log2-change\t1\tsingle_study\tone_study_effect_retained_without_pooling\t0.4\t0.2\t0.0\t0.8\t0.04\n"
    class InspectingFakeR(FakeR):
        def __call__(self, command, **kwargs):
            self.config = json.loads(__import__("pathlib").Path(command[-1]).read_text(encoding="utf-8"))
            return super().__call__(command, **kwargs)

    runner = InspectingFakeR({"a_long.R": {"synthesis.tsv": output}})
    result = run_released_synthesis(
        released_inputs=released,
        policy_payload=policy,
        output_dir=tmp_path / "invented-private-output",
        retention_dir=tmp_path / "invented-private-retention",
        runner=runner,
        allow_outcomes=True,
    )

    assert result.policy_status == "USER_RECORD_BOUND"
    assert result.effects[0]["adjustment_method"] == "holm"
    assert runner.config["config"]["boundary"]["release_record_sha256"] == hashlib.sha256(record_path.read_bytes()).hexdigest()
    assert runner.config["config"]["boundary"]["input_sha256"].keys() == {"effects", "overlap_receipts", "groups"}
