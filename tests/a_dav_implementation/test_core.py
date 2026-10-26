"""Public synthetic DAV packet and receipt contracts."""
import importlib

import pytest

from tools.a_dav.core import SchemaStore, check_packet, finish, verify_result


def test_synthetic_result_is_sealed_without_admission():
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    check_packet(packet, schemas)
    result = finish("core", packet, schemas=schemas)
    assert result["status"] == "READY"
    assert result["source_admission"] is False
    assert result["analysis_ready"] is False
    assert result["statistical_release"] is False
    assert result["biological_analysis_executed"] is False
    verify_result(result, stage="core", branch_id="A_BASELINE_BIO", schemas=schemas)


def test_worksheet_code_change_invalidates_admission_runtime_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path
    from tools.a_dav.core import DavError, runtime_hashes

    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    result = finish("admission", packet, schemas=schemas)
    assert "worksheet.py" in result["bindings"]["runtime_sha256"]
    assert "worksheet.py" in runtime_hashes("workflow")
    assert "worksheet.py" in runtime_hashes("freeze")

    original = Path.read_bytes

    def changed_worksheet(path: Path) -> bytes:
        raw = original(path)
        return raw + b"\n# changed" if path.name == "worksheet.py" else raw

    monkeypatch.setattr(Path, "read_bytes", changed_worksheet)
    with pytest.raises(DavError, match="CODE_BINDING_MISMATCH"):
        verify_result(result, schemas=schemas)


def test_tampering_stale_schemas_and_wrong_branch_are_rejected():
    import copy
    import pytest
    from tools.a_dav.core import DavError
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    result = finish("core", packet, schemas=schemas)
    changed = copy.deepcopy(result)
    changed["records"]["patient_registry"] = [{"patient_uid": "invented-tamper"}]
    with pytest.raises(DavError, match="RECEIPT_TAMPERED"):
        verify_result(changed)
    with pytest.raises(DavError, match="DEPENDENCY_INVALID"):
        verify_result(result, branch_id="A_P2_FINAL_TEST")
    packet["schema_hashes"]["patient_registry"] = "0" * 64
    with pytest.raises(DavError, match="SCHEMA_BINDING_MISMATCH"):
        check_packet(packet, schemas)


def test_public_summary_redacts_rows_unknown_codes_and_locators():
    import json
    from tools.a_dav.core import public_summary
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    result = finish("core", packet, {"patient_registry": [{"source_patient_id": "private-sentinel"}]},
                    reasons=["RAW_IDENTIFIER_SENTINEL"], audit=[{"locator": "/private/sentinel"}], schemas=schemas)
    summary = public_summary(result, include_counts=False)
    assert summary["reasons"] == ["UNCLASSIFIED_REASON"]
    assert "record_count" not in summary
    assert "sentinel" not in json.dumps(summary).lower()


def test_record_permutation_preserves_receipt_but_configuration_order_does_not():
    import copy
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {"study_registry": [{"study_id": "b"}, {"study_id": "a"}]},
              "config": {"rank": ["b", "a"]}, "schema_hashes": schemas.hashes}
    first = finish("core", packet, packet["records"], schemas=schemas)
    second_packet = copy.deepcopy(packet)
    second_packet["records"]["study_registry"].reverse()
    assert first == finish("core", second_packet, second_packet["records"], schemas=schemas)
    second_packet["config"]["rank"].reverse()
    assert first["receipt_id"] != finish("core", second_packet, second_packet["records"], schemas=schemas)["receipt_id"]


def test_private_classification_and_nonfinite_values_are_checked_separately():
    import pytest
    from tools.a_dav.core import DavError
    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    check_packet(packet, schemas)
    packet["config"]["value"] = float("nan")
    with pytest.raises(DavError, match="MALFORMED_INPUT"):
        check_packet(packet, schemas)


def test_private_patient_level_is_an_origin_and_ready_is_neutral():
    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    check_packet(packet, schemas)
    result = finish("core", packet, schemas=schemas)
    assert result["classification"] == "PRIVATE_PATIENT_LEVEL"
    assert result["status"] == "READY"
    verify_result(result, stage="core", branch_id="A_BASELINE_BIO", schemas=schemas)


@pytest.mark.parametrize("module_name,function_name", [
    ("workflow", "run_existing_seams"),
    ("workflow", "run_workflow"),
    ("registries", "build_registries"),
    ("endpoints", "map_endpoints"),
    ("timing", "validate_timing"),
    ("assays", "validate_assays"),
    ("overlap", "validate_overlap"),
    ("exposure", "validate_exposure"),
    ("matrices", "build_baseline"),
    ("matrices", "build_longitudinal"),
    ("admission", "evaluate_admission"),
    ("release", "validate_split"),
    ("reporting", "build_public_report"),
    ("prat_review", "review_prat_packet"),
])
def test_each_stage_copies_private_classification_on_blocked_packets(module_name, function_name):
    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes, "dependencies": {}}
    stage = getattr(importlib.import_module("tools.a_dav." + module_name), function_name)
    result = stage(packet, schemas=schemas)
    assert result["classification"] == "PRIVATE_PATIENT_LEVEL", function_name
    assert result["status"] in {"BLOCKED_UNKNOWN", "FAIL"}, function_name


def test_freeze_never_writes_private_packet(tmp_path):
    from tools.a_dav.release import freeze_bundle
    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes, "dependencies": {}}
    frozen = freeze_bundle(packet, tmp_path / "private-bundle", schemas=schemas)
    assert frozen["classification"] == "PRIVATE_PATIENT_LEVEL"
    assert not (tmp_path / "private-bundle").exists()


def test_dependency_binds_added_canonical_entities_and_derived_views():
    import copy
    import pytest
    from tools.a_dav.core import DavError, dependency
    schemas = SchemaStore()
    base = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
            "records": {"endpoint": [{"binary_value": 1}]}, "config": {},
            "schema_hashes": schemas.hashes, "dependencies": {}}
    upstream = finish("endpoints", base, base["records"], schemas=schemas)
    for table, rows in [("patient_registry", [{"patient_uid": "added"}]),
                        ("endpoint", [{"binary_value": 0}])]:
        changed = copy.deepcopy(base)
        changed["dependencies"]["endpoints"] = upstream
        changed["records"][table] = rows
        with pytest.raises(DavError, match="DEPENDENCY_INVALID"):
            dependency(changed, "endpoints", schemas)


def test_public_stage_seals_malformed_configs_without_echoing_them():
    from tools.a_dav.workflow import run_existing_seams
    schemas = SchemaStore()
    for value in (float("nan"), {"not-json"}, b"not-json"):
        packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
                  "records": {"study_registry": [{"study_id": "safe"}]},
                  "config": {"existing_seams": value}, "schema_hashes": schemas.hashes}
        result = run_existing_seams(packet, schemas=schemas)
        assert result["status"] == "FAIL"
        assert result["reasons"] == ["MALFORMED_INPUT"]
        assert result["records"] == {}
        assert all(result[key] is False for key in (
            "analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed"))
        verify_result(result, stage="existing_seams", branch_id="A_BASELINE_BIO", schemas=schemas)


def test_public_stage_seals_cyclic_config_with_safe_digest_fallback():
    import hashlib
    from tools.a_dav.workflow import run_existing_seams
    schemas = SchemaStore()
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {"existing_seams": cyclic}, "schema_hashes": schemas.hashes}
    result = run_existing_seams(packet, schemas=schemas)
    safe_digest = hashlib.sha256(b"null").hexdigest()
    assert result["status"] == "FAIL"
    assert result["reasons"] == ["MALFORMED_INPUT"]
    assert result["records"] == {}
    assert result["bindings"]["config_sha256"] == safe_digest
    assert result["bindings"]["input_sha256"] == safe_digest
    verify_result(result, stage="existing_seams", branch_id="A_BASELINE_BIO", schemas=schemas)


def test_invalid_branch_is_normalized_to_none_in_sealed_failure():
    from tools.a_dav.workflow import run_existing_seams
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": ["untrusted"],
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    result = run_existing_seams(packet, schemas=schemas)
    assert result["status"] == "FAIL"
    assert result["reasons"] == ["UNSUPPORTED_BRANCH"]
    assert result["branch_id"] is None
    verify_result(result, stage="existing_seams", schemas=schemas)


def test_direct_finish_uses_safe_digest_for_malformed_config():
    import hashlib
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {"bad": {1, 2}}, "schema_hashes": schemas.hashes}
    result = finish("core", packet, status="FAIL", reasons=["MALFORMED_INPUT"], schemas=schemas)
    assert result["bindings"]["config_sha256"] == hashlib.sha256(b"null").hexdigest()
    verify_result(result, stage="core", branch_id="A_BASELINE_BIO", schemas=schemas)


def test_malformed_dependency_lineage_still_has_verifiable_safe_failure():
    from tools.a_dav.workflow import run_existing_seams
    schemas = SchemaStore()
    for dependencies in ([], {'registries': {'receipt_id': b'not-json'}},
                         {'registries': {'receipt_id': {'untrusted'}}}):
        packet = {'classification': 'SYNTHETIC_ONLY', 'branch_id': 'A_BASELINE_BIO',
                  'records': {}, 'config': {}, 'schema_hashes': schemas.hashes,
                  'dependencies': dependencies}
        result = run_existing_seams(packet, schemas=schemas)
        assert result['status'] == 'FAIL'
        assert result['records'] == {}
        verify_result(result, stage='existing_seams', schemas=schemas)
        assert result['bindings']['upstream_receipt_ids'] == {}
