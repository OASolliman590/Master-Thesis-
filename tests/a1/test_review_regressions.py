from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict, fields, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_meta.provenance import canonical_sha256
from tools.a1 import features
from tools.a1.authorization import validate_user_release
from tools.a1.features import LongFeatureMemberships, build_pair_analysis_rows
from tools.a1.pairing import (
    CANONICAL_COLUMNS,
    PairingPolicy,
    PolicyAcceptance,
    SourceColumns,
    WindowRule,
    build_pairs,
    read_specimens,
    validate_real_source_columns,
    write_pair_products,
)
from tools.a1.__main__ import _read_user_crosswalk
import tools.a1.__main__ as a1_cli


FIXTURE = Path(__file__).parent / "fixtures" / "a_long_fixed_memberships.json"


def _fixed_memberships():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload = {key: raw[key] for key in ("ap2_panels", "custom_panels", "m5m6_genes", "aliases")}
    return LongFeatureMemberships(
        ap2_panels={name: tuple(values) for name, values in raw["ap2_panels"].items()},
        custom_panels={name: tuple(values) for name, values in raw["custom_panels"].items()},
        m5m6_genes=tuple(raw["m5m6_genes"]),
        aliases=dict(raw["aliases"]),
        membership_sha256=canonical_sha256(payload),
    )


def _feature_policy(fixed):
    representation = {"platform": "rnaseq", "unit": "tpm", "transform": "linear"}
    identities = {}
    for unit in (
        *(f"AP2:{name}" for name in fixed.ap2_panels), "CYT",
        *(f"CUSTOM:{name}" for name in fixed.custom_panels),
        *(f"M5M6:{name}" for name in fixed.m5m6_genes),
    ):
        if unit.startswith("AP2:"):
            identity = ("panel", "A_P2", "A_P2_PANELS")
        elif unit == "CYT":
            identity = ("comparator", "CYT", "CYT_SINGLETON")
        elif unit.startswith("CUSTOM:"):
            identity = ("custom_panel", "A_LONG_CUSTOM", "A_LONG_CUSTOM_PANELS")
        else:
            identity = ("m5m6_gene", "M5M6", "M5M6_GENES")
        identities[unit] = dict(zip(("unit_family", "panel_family", "multiplicity_family_id"), identity))
    return {
        "analysis_method_id": "lm_change_response_covariates_v1",
        "assay_id": "invented-qualified-bulk-rnaseq",
        "covariates": [],
        "endpoint_id": "invented-response",
        "regimen_id": "invented-ici-only",
        "representation": representation,
        "source_scale": "rnaseq:tpm:linear",
        "tpm_qualified": True,
        "tpm_route": "invented-linear-tpm-contract",
        "window_id": "invented-on-window",
        "unit_identities": identities,
    }


def _pair(study, patient, pre_assay, on_assay, *, regimen="invented-ici-only"):
    return {
        "study_id": study,
        "patient_id": patient,
        "pair_id": f"pair-{study}-{patient}",
        "selected": "true",
        "pre_specimen_id": "reused-specimen-pre",
        "on_specimen_id": "reused-specimen-on",
        "pre_assay_id": pre_assay,
        "on_assay_id": on_assay,
        "endpoint_id": "invented-response",
        "regimen_id": regimen,
        "window_id": "invented-on-window",
        "same_lesion": "true",
        "pre_day_precision": "exact",
        "on_day_precision": "exact",
        "pre_day_numeric": "-2",
        "on_day_numeric": "8",
        "day_distance_to_target": "2",
        "pair_day_distance": "10",
        "timing_ambiguity": "none",
        "source_family_id": f"source-{study}",
        "overlap_receipt_id": hashlib.sha256(study.encode()).hexdigest(),
        "overlap_status": "UNRESOLVED",
        "admission_receipt": f"invented-admission-{study}",
        "pre_source_locator": f"invented://{study}/pre",
        "on_source_locator": f"invented://{study}/on",
        "pre_source_confidence": "invented-high",
        "on_source_confidence": "invented-high",
        "pre_annotation_id": "invented-annotation",
        "on_annotation_id": "invented-annotation",
        "pre_measurement_comparability_id": "invented-tpm",
        "on_measurement_comparability_id": "invented-tpm",
        "pre_day_origin": "invented-first-dose",
        "on_day_origin": "invented-first-dose",
    }


def _fake_released(monkeypatch, policy, pairs, expression, endpoints, studies):
    fixed = _fixed_memberships()
    monkeypatch.setattr(features, "fixed_long_feature_memberships", lambda: fixed)
    policy_sha = canonical_sha256(policy)
    pair_sha = "pair-source-hash"
    manifest = {
        "cohort_ids": list(studies),
        "scope_bindings": {
            "feature_membership_sha256": fixed.membership_sha256,
            "pair_manifest_sha256": pair_sha,
            "representation_sha256": canonical_sha256(policy["representation"]),
        },
    }
    released = SimpleNamespace(
        authorization=SimpleNamespace(
            record={"policy_sha256": policy_sha}, source_sha256={"pairs": pair_sha}
        ),
        manifest=manifest,
        tables={"pairs": pairs, "expression": expression, "endpoint": endpoints},
    )
    monkeypatch.setattr(features, "is_released_inputs", lambda *_args, **_kwargs: True)
    return fixed, released


def _expression_rows(fixed, measurements):
    genes = sorted(
        {gene for panel in (*fixed.ap2_panels.values(), *fixed.custom_panels.values()) for gene in panel}
        | set(fixed.m5m6_genes) | {"GZMA", "PRF1"}
    )
    return [
        {"study_id": study, "sample_id": sample, "assay_id": assay, "gene_id": gene, "value": value}
        for (study, sample, assay), value in measurements.items()
        for gene in genes
    ]


def test_feature_join_uses_study_and_selected_assay_identity(monkeypatch):
    fixed = _fixed_memberships()
    policy = _feature_policy(fixed)
    pairs = [
        _pair("invented-study-a", "person-a", "a-pre", "a-on"),
        _pair("invented-study-b", "person-b", "b-pre", "b-on"),
    ]
    measurements = {
        ("invented-study-a", "reused-specimen-pre", "a-pre"): "3",
        ("invented-study-a", "reused-specimen-pre", "a-other-assay"): "99",
        ("invented-study-a", "reused-specimen-on", "a-on"): "7",
        ("invented-study-b", "reused-specimen-pre", "b-pre"): "5",
        ("invented-study-b", "reused-specimen-on", "b-on"): "11",
    }
    endpoints = [
        {"study_id": "invented-study-a", "patient_id": "person-a", "endpoint_id": "invented-response", "response": "R"},
        {"study_id": "invented-study-b", "patient_id": "person-b", "endpoint_id": "invented-response", "response": "NR"},
    ]
    _, released = _fake_released(monkeypatch, policy, pairs, _expression_rows(fixed, measurements), endpoints,
                                 ("invented-study-a", "invented-study-b"))

    rows, _ = build_pair_analysis_rows(released, policy=policy, allow_outcomes=True)

    by_study = {row["study_id"]: row for row in rows if row["unit"].startswith("AP2:")}
    assert by_study["invented-study-a"]["pre_value"] == pytest.approx(2.0)
    assert by_study["invented-study-a"]["on_value"] == pytest.approx(3.0)
    assert by_study["invented-study-b"]["pre_value"] == pytest.approx(math.log2(6))


def test_feature_join_does_not_borrow_same_specimen_from_another_study(monkeypatch):
    fixed = _fixed_memberships()
    policy = _feature_policy(fixed)
    pairs = [_pair("invented-study-a", "person-a", "a-pre", "a-on")]
    measurements = {
        ("invented-study-b", "reused-specimen-pre", "a-pre"): "3",
        ("invented-study-b", "reused-specimen-on", "a-on"): "7",
    }
    endpoints = [{"study_id": "invented-study-a", "patient_id": "person-a", "endpoint_id": "invented-response", "response": "R"}]
    _, released = _fake_released(monkeypatch, policy, pairs, _expression_rows(fixed, measurements), endpoints,
                                 ("invented-study-a", "invented-study-b"))

    rows, coverage = build_pair_analysis_rows(released, policy=policy, allow_outcomes=True)

    assert all(row["pre_value"] is None and row["on_value"] is None for row in rows if row["unit"].startswith("AP2:"))
    assert not next(row for row in coverage if row["unit"].startswith("AP2:"))["complete"]


def test_feature_join_rejects_policy_mutation_and_regimen_mismatch_before_use(monkeypatch):
    fixed = _fixed_memberships()
    policy = _feature_policy(fixed)
    pair = _pair("invented-study-a", "person-a", "a-pre", "a-on", regimen="invented-combination")
    _, released = _fake_released(
        monkeypatch, policy, [pair], _expression_rows(
            fixed, {
                ("invented-study-a", "reused-specimen-pre", "a-pre"): "3",
                ("invented-study-a", "reused-specimen-on", "a-on"): "7",
            }
        ),
        [{"study_id": "invented-study-a", "patient_id": "person-a", "endpoint_id": "invented-response", "response": "R"}],
        ("invented-study-a",),
    )
    with pytest.raises(ValueError, match="regimen"):
        build_pair_analysis_rows(released, policy=policy, allow_outcomes=True)

    class UnreadableInputs:
        authorization = released.authorization

        @property
        def tables(self):
            raise AssertionError("policy must be compared before table access")

    changed = {**policy, "covariates": ["invented_covariate"]}
    with pytest.raises(PermissionError, match="policy differs"):
        build_pair_analysis_rows(UnreadableInputs(), policy=changed, allow_outcomes=True)


def _real_pairing_acceptance(tmp_path, policy):
    root = tmp_path / "decision-root"
    decisions = root / "docs" / "decisions"
    decisions.mkdir(parents=True)
    decision = decisions / "TEST_ONLY_N12.md"
    decision.write_text("TEST ONLY invented N12 record fixture\n", encoding="utf-8")
    source = tmp_path / "TEST_ONLY_specimens.tsv"
    source.write_text("study_id\tpatient_id\n", encoding="utf-8")
    bindings = {"source_column_map_sha256": "a" * 64, "window_policy_sha256": "b" * 64}
    record = {
        "record_type": "a_long_user_release_v1", "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL", "release_scope": "N12_PAIRING",
        "operation": "pair", "policy_sha256": canonical_sha256(asdict(policy)),
        "input_manifest_sha256": "c" * 64,
        "source_sha256": {"specimens": hashlib.sha256(source.read_bytes()).hexdigest()},
        "cohorts": [policy.study_id], "permitted_fields": ["patient_id", "study_id"],
        **bindings,
        "decision": {"identity": decision.stem, "path": "docs/decisions/TEST_ONLY_N12.md",
                     "sha256": hashlib.sha256(decision.read_bytes()).hexdigest()},
    }
    record_path = tmp_path / "TEST_ONLY_n12_release.json"
    record_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    authorized = validate_user_release(
        record_path, release_scope="N12_PAIRING", operation="pair",
        policy_sha256=record["policy_sha256"], input_manifest_sha256=record["input_manifest_sha256"],
        source_paths={"specimens": source}, cohorts=[policy.study_id],
        permitted_fields=record["permitted_fields"], root=root, decisions_dir=decisions,
        extra_bindings=bindings,
    )
    return PolicyAcceptance(decision.stem, authorized.record_sha256, authorization=authorized)


def test_real_pairing_api_refuses_missing_named_admission_provenance(tmp_path):
    policy = PairingPolicy(
        study_id="invented-real-classified-study", status="ACCEPTED", decision_ref="TEST_ONLY_N12",
        baseline_window="baseline",
        windows=(WindowRule("baseline", "baseline", ("PRE",)), WindowRule("on", "followup", ("ON",))),
        baseline_hierarchy=("research",), allowed_prior_treatment=("none",),
        allowed_disease_states=("stable",), allowed_regimen_states=("stable",),
        prefer_same_lesion=True, endpoint_id="invented-endpoint", admission_receipt="invented-admission",
        source_family_id="invented-family", overlap_receipt_id="d" * 64,
        overlap_status="DISJOINT_VERIFIED",
    )
    acceptance = _real_pairing_acceptance(tmp_path, policy)
    base = {
        "study_id": policy.study_id, "patient_id": "invented-person", "index_episode": "invented-episode",
        "exposure": "ici-only", "baseline_source": "research", "prior_treatment": "none",
        "disease_state": "stable", "regimen_state": "stable", "compartment": "tumour",
        "platform": "rnaseq", "unit": "tpm", "assay_method": "bulk", "assay_qualified": "yes",
        "source_locator": "invented://source", "source_confidence": "invented-high", "day_origin": "invented-origin",
        "annotation_id": "", "measurement_comparability_id": "", "endpoint_id": "invented-endpoint",
        "admission_receipt": "invented-admission",
        "collection_day": "", "day_precision": "unknown", "lesion_id": "invented-lesion",
    }
    rows = [
        {**base, "specimen_id": "invented-pre", "assay_id": "pre-assay", "timepoint_category": "PRE"},
        {**base, "specimen_id": "invented-on", "assay_id": "on-assay", "timepoint_category": "ON"},
    ]

    with pytest.raises(PermissionError, match="provenance/admission field"):
        build_pairs(rows, policy, classification="real", acceptance=acceptance)


@pytest.mark.parametrize(
    "field",
    ["source_locator", "source_confidence", "day_origin", "annotation_id",
     "measurement_comparability_id", "endpoint_id", "admission_receipt"],
)
def test_real_pairing_rejects_each_empty_source_admission_field(tmp_path, field):
    policy = PairingPolicy(
        study_id="invented-real-classified-study", status="ACCEPTED", decision_ref="TEST_ONLY_N12",
        baseline_window="baseline",
        windows=(WindowRule("baseline", "baseline", ("PRE",)), WindowRule("on", "followup", ("ON",))),
        baseline_hierarchy=("research",), allowed_prior_treatment=("none",),
        allowed_disease_states=("stable",), allowed_regimen_states=("stable",),
        prefer_same_lesion=True, endpoint_id="invented-endpoint", admission_receipt="invented-admission",
        source_family_id="invented-family", overlap_receipt_id="d" * 64,
        overlap_status="DISJOINT_VERIFIED",
    )
    acceptance = _real_pairing_acceptance(tmp_path, policy)
    base = {
        "study_id": policy.study_id, "patient_id": "invented-person", "index_episode": "invented-episode",
        "exposure": "ici-only", "baseline_source": "research", "prior_treatment": "none",
        "disease_state": "stable", "regimen_state": "stable", "compartment": "tumour",
        "platform": "rnaseq", "unit": "tpm", "assay_method": "bulk", "assay_qualified": "yes",
        "source_locator": "invented://source", "source_confidence": "invented-high", "day_origin": "invented-origin",
        "annotation_id": "invented-annotation", "measurement_comparability_id": "invented-tpm",
        "endpoint_id": "invented-endpoint", "admission_receipt": "invented-admission",
        "collection_day": "", "day_precision": "unknown", "lesion_id": "invented-lesion",
    }
    rows = [
        {**base, "specimen_id": "invented-pre", "assay_id": "pre-assay", "timepoint_category": "PRE"},
        {**base, "specimen_id": "invented-on", "assay_id": "on-assay", "timepoint_category": "ON"},
    ]
    rows[0][field] = ""

    with pytest.raises(PermissionError, match="provenance/admission field"):
        build_pairs(rows, policy, classification="real", acceptance=acceptance)


def test_real_source_mapping_requires_all_admission_columns_before_read(tmp_path):
    columns = SourceColumns(
        study_id="study", patient_id="patient", specimen_id="specimen", assay_id="assay",
        timepoint_category="timepoint", index_episode="episode", exposure="exposure",
        baseline_source="baseline", prior_treatment="prior", disease_state="disease",
        regimen_state="regimen", compartment="compartment", platform="platform", unit="unit",
        assay_method="method", assay_qualified="qualified",
    )
    with pytest.raises(ValueError, match="explicitly named source"):
        read_specimens(
            tmp_path / "unopened-invented-source.tsv", columns=columns,
            study_id="invented-real-classified-study", classification="real",
        )
    with pytest.raises(ValueError, match="explicitly named source"):
        validate_real_source_columns(columns.mapping())


def test_real_pair_cli_canonical_rows_reject_missing_admission_provenance(tmp_path, monkeypatch):
    study = "invented-real-cli-study"
    source_path = tmp_path / "TEST_ONLY_source.tsv"
    source_path.write_text("invented source placeholder\n", encoding="utf-8")
    columns = SourceColumns(**{field.name: field.name for field in fields(SourceColumns)})
    policy = PairingPolicy(
        study_id=study, status="ACCEPTED", decision_ref="TEST_ONLY_N12",
        baseline_window="baseline",
        windows=(WindowRule("baseline", "baseline", ("PRE",)), WindowRule("on", "followup", ("ON",))),
        baseline_hierarchy=("research",), allowed_prior_treatment=("none",),
        allowed_disease_states=("stable",), allowed_regimen_states=("stable",),
        prefer_same_lesion=True, endpoint_id="invented-endpoint", admission_receipt="invented-admission",
        source_family_id="invented-family", overlap_receipt_id="d" * 64,
        overlap_status="DISJOINT_VERIFIED",
    )
    columns_path = tmp_path / "TEST_ONLY_columns.json"
    columns_path.write_text(json.dumps(asdict(columns)), encoding="utf-8")
    policy_path = tmp_path / "TEST_ONLY_policy.json"
    policy_path.write_text(json.dumps(asdict(policy)), encoding="utf-8")
    mapping = columns.mapping()
    record = {
        "policy_sha256": canonical_sha256(asdict(policy)),
        "cohorts": [study],
        "decision": {"identity": "TEST_ONLY_N12"},
        "release_scope": "N12_PAIRING",
        "operation": "pair",
    }
    authorization = SimpleNamespace(record=record, record_sha256="e" * 64)
    row = {name: "invented-value" for name in CANONICAL_COLUMNS}
    row.update({
        "study_id": study, "patient_id": "invented-person", "specimen_id": "invented-specimen",
        "assay_id": "invented-assay", "timepoint_category": "PRE", "index_episode": "invented-episode",
        "exposure": "ici-only", "baseline_source": "research", "prior_treatment": "none",
        "disease_state": "stable", "regimen_state": "stable", "compartment": "tumour",
        "platform": "rnaseq", "unit": "tpm", "assay_method": "bulk", "assay_qualified": "yes",
        "source_locator": "", "source_confidence": "invented-high", "day_origin": "invented-origin",
        "annotation_id": "invented-annotation", "measurement_comparability_id": "invented-tpm",
        "endpoint_id": "invented-endpoint", "admission_receipt": "invented-admission",
    })
    released = SimpleNamespace(
        authorization=authorization,
        manifest={"field_maps": {"specimens": mapping}},
        source_paths={"specimens": source_path.resolve()},
        tables={"specimens": [row]},
        manifest_sha256="f" * 64,
    )
    monkeypatch.setattr(a1_cli, "read_released_inputs", lambda *_args, **_kwargs: released)
    monkeypatch.setattr(a1_cli, "_private_output_root", lambda *_args, **_kwargs: tmp_path)
    monkeypatch.setattr("tools.a1.pairing.is_authorized_release", lambda *_args, **_kwargs: True)

    with pytest.raises(PermissionError, match="provenance/admission field"):
        a1_cli.main([
            "pair", "--study-id", study, "--classification", "real",
            "--input", str(source_path), "--columns-json", str(columns_path),
            "--policy-json", str(policy_path), "--input-manifest", str(tmp_path / "TEST_ONLY_manifest.json"),
            "--release-record", str(tmp_path / "TEST_ONLY_release.json"),
            "--out", str(tmp_path / "private-output"),
        ])


def test_accepted_gide_crosswalk_file_route_uses_external_manifest_hash(tmp_path):
    study = "gide-invented-file-route"
    root = tmp_path / "TEST_ONLY_decision_root"
    decisions = root / "docs" / "decisions"
    decisions.mkdir(parents=True)
    decision = decisions / "TEST_ONLY_GIDE_CROSSWALK.md"
    decision.write_text("TEST ONLY invented crosswalk decision fixture\n", encoding="utf-8")
    mapping = {"invented-run-a": "invented-patient-a", "invented-run-b": "invented-patient-b"}
    crosswalk_path = tmp_path / "TEST_ONLY_crosswalk.json"
    crosswalk_path.write_text(json.dumps(mapping, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    manifest = {
        "schema": "a_long_gide_crosswalk_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": [study],
        "permitted_fields": ["crosswalk:patient_id", "crosswalk:source_run"],
        "scope_bindings": {"crosswalk_sha256": canonical_sha256(mapping)},
    }
    manifest_path = tmp_path / "TEST_ONLY_crosswalk_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    release_bindings = {
        "crosswalk_sha256": manifest["scope_bindings"]["crosswalk_sha256"],
        "crosswalk_source_manifest_sha256": manifest_hash,
    }
    record = {
        "record_type": "a_long_user_release_v1", "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL", "release_scope": "N12_GIDE_CROSSWALK",
        "operation": "accept_gide_crosswalk",
        "policy_sha256": canonical_sha256({"study_id": study, **release_bindings}),
        "input_manifest_sha256": manifest_hash,
        "source_sha256": {"crosswalk": hashlib.sha256(crosswalk_path.read_bytes()).hexdigest()},
        "cohorts": [study], "permitted_fields": manifest["permitted_fields"],
        **release_bindings,
        "decision": {"identity": decision.stem, "path": "docs/decisions/TEST_ONLY_GIDE_CROSSWALK.md",
                     "sha256": hashlib.sha256(decision.read_bytes()).hexdigest()},
    }
    record_path = tmp_path / "TEST_ONLY_crosswalk_release.json"
    record_path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    accepted = _read_user_crosswalk(
        crosswalk_path, manifest_path, record_path, study_id=study, root=root, decisions_dir=decisions
    )
    assert dict(accepted.mapping) == mapping
    assert accepted.record_ref == hashlib.sha256(record_path.read_bytes()).hexdigest()

    altered_manifest = {**manifest, "permitted_fields": ["crosswalk:changed"]}
    altered_manifest_path = tmp_path / "TEST_ONLY_altered_crosswalk_manifest.json"
    altered_manifest_path.write_text(json.dumps(altered_manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        _read_user_crosswalk(
            crosswalk_path, altered_manifest_path, record_path, study_id=study, root=root, decisions_dir=decisions
        )

    altered_mapping_path = tmp_path / "TEST_ONLY_altered_crosswalk.json"
    altered_mapping_path.write_text(json.dumps({**mapping, "invented-run-c": "invented-patient-c"}, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        _read_user_crosswalk(
            altered_mapping_path, manifest_path, record_path, study_id=study, root=root, decisions_dir=decisions
        )


def test_missing_followup_receipts_are_emitted_per_approved_window():
    policy = PairingPolicy(
        study_id="fixture-study", status="PROPOSED", decision_ref=None, baseline_window="baseline",
        windows=(
            WindowRule("baseline", "baseline", ("PRE",)),
            WindowRule("early", "followup", ("EARLY",), (1, 10), "first-dose", 5),
            WindowRule("late", "followup", ("LATE",), (11, 30), "first-dose", 20),
        ),
        baseline_hierarchy=("research",), allowed_prior_treatment=("none",),
        allowed_disease_states=("stable",), allowed_regimen_states=("stable",),
        prefer_same_lesion=True,
    )
    def row(specimen, category, day=""):
        return {
            "study_id": "fixture-study", "patient_id": "invented-person", "specimen_id": specimen,
            "assay_id": specimen + "-assay", "timepoint_category": category, "collection_day": day,
            "day_precision": "exact" if day else "unknown", "index_episode": "episode-a", "exposure": "ici-only",
            "baseline_source": "research", "prior_treatment": "none", "disease_state": "stable",
            "regimen_state": "stable", "compartment": "tumour", "platform": "rnaseq", "unit": "tpm",
            "assay_method": "bulk", "assay_qualified": "yes", "lesion_id": "lesion-a",
            "source_locator": "invented://" + specimen, "source_confidence": "invented-high",
            "day_origin": "first-dose" if day else "unknown", "annotation_id": "invented-ann",
            "measurement_comparability_id": "invented-scale", "endpoint_id": "", "admission_receipt": "",
        }
    rows = [row("pre", "PRE"), row("early-on", "EARLY", "5")]
    result = build_pairs(rows, policy, classification="synthetic",
                         acceptance=SimpleNamespace(decision_id="TEST_ONLY", record_ref="TEST_ONLY", fixture_only=True))

    assert [(row["window_id"], row["reason"]) for row in result.missing_followups] == [("late", "no_followup_specimen")]


def test_rejected_pair_receipts_keep_assay_timing_and_source_provenance(tmp_path):
    from tests.a1.test_pairing import _acceptance as fixture_acceptance
    from tests.a1.test_pairing import _policy as fixture_policy
    from tests.a1.test_pairing import _row

    rows = [
        _row(patient="invented-person", specimen="pre", category="PRE"),
        _row(patient="invented-person", specimen="bad-on", category="ON", day="3", assay="technical-a"),
        _row(patient="invented-person", specimen="bad-on", category="ON", day="3", assay="technical-b"),
    ]
    result = build_pairs(rows, fixture_policy(), classification="synthetic", acceptance=fixture_acceptance())
    rejected = [row for row in result.exclusions if row["reason"] == "timing_contradiction"]
    assert {row["assay_id"] for row in rejected} == {"technical-a", "technical-b"}
    assert all(row["timepoint_category"] == "ON" and row["collection_day"] == "3" for row in rejected)
    assert all(row["source_locator"] and row["index_episode"] and row["exposure"] for row in rejected)

    paths = write_pair_products(result, tmp_path / "private-receipts")
    with paths["pairing_exclusions"].open(newline="", encoding="utf-8") as stream:
        serialized = list(csv.DictReader(stream, delimiter="\t"))
    serialized_rejected = [row for row in serialized if row["reason"] == "timing_contradiction"]
    assert {row["assay_id"] for row in serialized_rejected} == {"technical-a", "technical-b"}
    assert all(row["collection_day"] == "3" and row["day_precision"] == "exact" for row in serialized_rejected)
