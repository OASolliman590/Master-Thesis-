"""Public synthetic DAV packet and receipt contracts."""
from tools.a_dav.core import SchemaStore, check_packet, finish, verify_result


def test_synthetic_result_is_sealed_without_admission():
    schemas = SchemaStore()
    packet = {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    check_packet(packet, schemas)
    result = finish("core", packet, schemas=schemas)
    assert result["status"] == "SYNTHETIC_READY"
    assert result["source_admission"] is False
    assert result["analysis_ready"] is False
    assert result["statistical_release"] is False
    assert result["biological_analysis_executed"] is False
    verify_result(result, stage="core", branch_id="A_BASELINE_BIO", schemas=schemas)


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


def test_real_data_classification_and_nonfinite_values_are_rejected():
    import pytest
    from tools.a_dav.core import DavError
    schemas = SchemaStore()
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {}, "config": {}, "schema_hashes": schemas.hashes}
    with pytest.raises(DavError, match="SYNTHETIC_ONLY_REQUIRED"):
        check_packet(packet, schemas)
    packet["classification"] = "SYNTHETIC_ONLY"
    packet["config"]["value"] = float("nan")
    with pytest.raises(DavError, match="MALFORMED_INPUT"):
        check_packet(packet, schemas)


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
