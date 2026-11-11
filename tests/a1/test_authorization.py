from __future__ import annotations

import hashlib
import json

import pytest

from tools.a1.authorization import (
    check_path_separation,
    guard_path,
    prepare_output_directory,
    read_released_inputs,
    validate_user_release,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _release_fixture(tmp_path, *, status="APPROVED"):
    root = tmp_path / "fake-root"
    decision_dir = root / "docs" / "decisions"
    decision_dir.mkdir(parents=True)
    decision = decision_dir / "FIXTURE_DECISION.md"
    decision.write_text("invented release-contract decision for tests\n", encoding="utf-8")
    record_path = tmp_path / "invented-release.json"
    source_path = tmp_path / "invented-expression.tsv"
    source_path.write_text("invented values only\n", encoding="utf-8")
    expected = {
        "release_scope": "N13_TWO_TIMEPOINT",
        "operation": "fit_two_timepoint",
        "policy_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "cohorts": ["invented-cohort"],
        "permitted_fields": ["on_value", "pre_value", "response"],
    }
    bindings = {
        "delta_method_id": "invented-delta-method",
        "ancova_method_id": "invented-ancova-method",
        "covariate_contract_sha256": "3" * 64,
    }
    record = {
        "record_type": "a_long_user_release_v1",
        "record_status": status,
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "source_sha256": {"paired_expression": _sha256(source_path)},
        **expected,
        **bindings,
        "decision": {
            "identity": decision.stem,
            "path": "docs/decisions/FIXTURE_DECISION.md",
            "sha256": _sha256(decision),
        },
    }
    record_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    return root, decision_dir, record_path, expected, bindings, {"paired_expression": source_path}


@pytest.mark.parametrize(
    "name",
    [
        "InGeStIoN_PaCkEt.JsOn",
        "copy-of-IMVIGOR210-payload.tsv",
    ],
)
def test_forbidden_path_names_are_rejected_without_opening_files(tmp_path, name):
    path = tmp_path / name
    with pytest.raises(PermissionError):
        guard_path(path, "fixture input")


def test_symlink_ancestry_and_input_output_alias_are_rejected(tmp_path):
    target = tmp_path / "invented-sentinel.tsv"
    target.write_text("invented fixture only", encoding="utf-8")
    alias = tmp_path / "benign-alias"
    alias.symlink_to(tmp_path, target_is_directory=True)

    with pytest.raises(PermissionError, match="symlink ancestry"):
        guard_path(alias / target.name, "fixture input")
    with pytest.raises(ValueError, match="overlap"):
        check_path_separation(
            inputs={"input": target}, outputs={"output": target}
        )
    assert target.read_text(encoding="utf-8") == "invented fixture only"


def test_existing_output_directory_must_be_empty(tmp_path):
    output = tmp_path / "results"
    output.mkdir()
    (output / "invented-sentinel.tsv").write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError, match="not empty"):
        prepare_output_directory(output)
    assert (output / "invented-sentinel.tsv").read_text(encoding="utf-8") == "preserve"


def test_user_release_requires_approved_exact_bindings_and_hashed_decision(tmp_path):
    root, decision_dir, release_path, expected, bindings, source_paths = _release_fixture(tmp_path)
    accepted = validate_user_release(
        release_path,
        **expected,
        extra_bindings=bindings,
        source_paths=source_paths,
        root=root,
        decisions_dir=decision_dir,
        allow_outcomes=True,
    )
    assert accepted.record["record_status"] == "APPROVED"
    assert accepted.source_sha256 == {"paired_expression": _sha256(source_paths["paired_expression"])}

    with pytest.raises(PermissionError, match="does not match"):
        validate_user_release(
            release_path,
            **{**expected, "policy_sha256": "f" * 64},
            extra_bindings=bindings,
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )


def test_arbitrary_reference_and_unapproved_status_do_not_authorize(tmp_path):
    root, decision_dir, release_path, expected, bindings, source_paths = _release_fixture(
        tmp_path, status="TEST_ONLY_NOT_APPROVED"
    )
    with pytest.raises(PermissionError, match="not approved"):
        validate_user_release(
            release_path,
            **expected,
            extra_bindings=bindings,
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )

    with pytest.raises(PermissionError, match="path"):
        validate_user_release(
            "arbitrary-nonempty-record-ref",
            **expected,
            extra_bindings=bindings,
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )


def test_release_header_is_checked_before_source_hash_and_hash_mismatch_fails(tmp_path):
    root, decision_dir, release_path, expected, bindings, source_paths = _release_fixture(tmp_path)
    source = source_paths["paired_expression"]
    source.write_text("changed invented data\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="source hash"):
        validate_user_release(
            release_path,
            **expected,
            extra_bindings=bindings,
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )


def test_each_release_scope_requires_its_own_exact_contract_bindings(tmp_path):
    root, decision_dir, release_path, expected, bindings, source_paths = _release_fixture(tmp_path)
    with pytest.raises(PermissionError, match="scope-specific"):
        validate_user_release(
            release_path,
            **expected,
            extra_bindings={},
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )


def _released_input_fixture(tmp_path):
    root = tmp_path / "release-root"
    decision_dir = root / "docs" / "decisions"
    decision_dir.mkdir(parents=True)
    decision = decision_dir / "INVENTED_RELEASE.md"
    decision.write_text("invented decision identity only\n", encoding="utf-8")
    source = tmp_path / "invented-design.tsv"
    source.write_text(
        "Study\tSubject\tTumor_Shrinkage\tscore\n"
        "invented-release-cohort\tpatient-01\tR\t2.5\n",
        encoding="utf-8",
    )
    bindings = {
        "delta_method_id": "invented-delta",
        "ancova_method_id": "invented-ancova",
        "covariate_contract_sha256": "4" * 64,
    }
    manifest = {
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": ["invented-release-cohort"],
        "source_files": {"design": source.name},
        "field_maps": {
            "design": {
                "study_id": "Study",
                "patient_id": "Subject",
                "response": "Tumor_Shrinkage",
                "score": "score",
            },
        },
        "identity_fields": {"design": ["Study", "Subject"]},
        "permitted_fields": [
            "design:Study", "design:Subject", "design:Tumor_Shrinkage", "design:score",
        ],
        "scope_bindings": bindings,
    }
    manifest_path = tmp_path / "invented-input-manifest.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_path.write_bytes(manifest_bytes)
    record = {
        "record_type": "a_long_user_release_v1",
        "record_status": "APPROVED",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "release_scope": "N13_TWO_TIMEPOINT",
        "operation": "fit_two_timepoint",
        "policy_sha256": "5" * 64,
        "input_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha256": {"design": _sha256(source)},
        "cohorts": ["invented-release-cohort"],
        "permitted_fields": manifest["permitted_fields"],
        **bindings,
        "decision": {
            "identity": decision.stem,
            "path": "docs/decisions/INVENTED_RELEASE.md",
            "sha256": _sha256(decision),
        },
    }
    record_path = tmp_path / "invented-user-release.json"
    record_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    return root, decision_dir, manifest_path, record_path, source


def test_released_table_reads_identity_then_only_exact_authorized_fields(tmp_path):
    root, decision_dir, manifest_path, record_path, source = _released_input_fixture(tmp_path)

    released = read_released_inputs(
        manifest_path,
        record_path,
        release_scope="N13_TWO_TIMEPOINT",
        operation="fit_two_timepoint",
        policy_sha256="5" * 64,
        root=root,
        decisions_dir=decision_dir,
        allow_outcomes=True,
    )

    assert released.tables["design"] == [{
        "study_id": "invented-release-cohort",
        "patient_id": "patient-01",
        "response": "R",
        "score": "2.5",
    }]
    assert released.authorization.record_sha256 == _sha256(record_path)
    assert source.read_text(encoding="utf-8").splitlines()[0].endswith("score")


def test_real_outcome_read_defaults_locked_before_source_hash_or_field_read(tmp_path, monkeypatch):
    root, decision_dir, manifest_path, record_path, source = _released_input_fixture(tmp_path)

    def forbidden_source_access(path, *args, **kwargs):
        if path == source or str(path) == str(source):
            pytest.fail("outcome source was accessed without explicit opt-in")
        raise AssertionError("no decision or release file should be opened before opt-in")

    monkeypatch.setattr("tools.a1.authorization.sha256_file", forbidden_source_access)
    monkeypatch.setattr("tools.a1.authorization._read_named_tsv", forbidden_source_access)
    with pytest.raises(PermissionError, match="allow_outcomes=True"):
        read_released_inputs(
            manifest_path,
            record_path,
            release_scope="N13_TWO_TIMEPOINT",
            operation="fit_two_timepoint",
            policy_sha256="5" * 64,
            root=root,
            decisions_dir=decision_dir,
        )


def test_validate_user_release_defaults_locked_before_source_hash(tmp_path, monkeypatch):
    root, decision_dir, release_path, expected, bindings, source_paths = _release_fixture(tmp_path)

    def forbid_outcome_hash(path, **kwargs):
        if path == source_paths["paired_expression"] or str(path) == str(source_paths["paired_expression"]):
            pytest.fail("outcome source was hashed without explicit opt-in")
        raise AssertionError("no source or decision hash should be computed before opt-in")

    monkeypatch.setattr("tools.a1.authorization.sha256_file", forbid_outcome_hash)
    with pytest.raises(PermissionError, match="allow_outcomes=True"):
        validate_user_release(
            release_path,
            **expected,
            extra_bindings=bindings,
            source_paths=source_paths,
            root=root,
            decisions_dir=decision_dir,
        )


def test_released_manifest_policy_mismatch_fails_before_source_hash_or_read(tmp_path, monkeypatch):
    root, decision_dir, manifest_path, record_path, source = _released_input_fixture(tmp_path)

    original_hash = __import__("tools.a1.authorization", fromlist=["sha256_file"]).sha256_file

    def must_not_hash(path, **kwargs):
        assert path != source
        return original_hash(path, **kwargs)

    monkeypatch.setattr("tools.a1.authorization.sha256_file", must_not_hash)
    with pytest.raises(PermissionError, match="does not match this operation"):
        read_released_inputs(
            manifest_path,
            record_path,
            release_scope="N13_TWO_TIMEPOINT",
            operation="fit_two_timepoint",
            policy_sha256="6" * 64,
            root=root,
            decisions_dir=decision_dir,
            allow_outcomes=True,
        )


def test_feature_join_requires_named_endpoint_identity_before_source_access(tmp_path):
    source_paths = {
        "pairs": tmp_path / "invented-pairs.tsv",
        "expression": tmp_path / "invented-expression.tsv",
        "endpoint": tmp_path / "invented-endpoint.tsv",
    }
    field_maps = {
        "pairs": {"study_id": "study_id", "patient_id": "patient_id"},
        "expression": {"study_id": "study_id", "sample_id": "sample_id"},
        "endpoint": {"study_id": "study_id", "patient_id": "patient_id", "response": "response"},
    }
    manifest = {
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": ["invented-feature-cohort"],
        "source_files": {name: str(path) for name, path in source_paths.items()},
        "field_maps": field_maps,
        "identity_fields": {
            "pairs": ["study_id", "patient_id"],
            "expression": ["study_id", "sample_id"],
            "endpoint": ["study_id", "patient_id"],
        },
        "permitted_fields": sorted(
            f"{name}:{column}"
            for name, mapping in field_maps.items()
            for column in mapping.values()
        ),
        "scope_bindings": {
            "feature_membership_sha256": "1" * 64,
            "pair_manifest_sha256": "2" * 64,
            "representation_sha256": "3" * 64,
        },
    }
    manifest_path = tmp_path / "invented-feature-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(PermissionError, match="endpoint ID and response"):
        read_released_inputs(
            manifest_path,
            tmp_path / "invented-user-record-not-read.json",
            release_scope="N13_FEATURE_JOIN",
            operation="pair_to_analysis",
            policy_sha256="4" * 64,
            expected_scope_bindings=manifest["scope_bindings"],
            allow_outcomes=True,
        )
    assert all(not path.exists() for path in source_paths.values())
