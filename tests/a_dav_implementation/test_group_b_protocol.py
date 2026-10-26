"""Invented protocol packets; no source access or authenticated reader claims."""
from __future__ import annotations
import copy
import hashlib
import importlib
from typing import Any
import pytest
from tools.a_dav.core import SchemaStore, digest, finish

STORE = SchemaStore()


def packet() -> dict[str, Any]:
    return {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO", "records": {},
            "config": {}, "schema_hashes": STORE.hashes, "dependencies": {}}


def invoke(module: str, function: str, value: dict[str, Any]) -> dict[str, Any]:
    return getattr(importlib.import_module("tools.a_dav." + module), function)(value, schemas=STORE)


QUESTIONS = ["identity", "patient_specimen_assay", "episode_bindings", "baseline_repeat_policy", "endpoint", "assay", "overlap_exposure"]


def prat() -> dict[str, Any]:
    p = packet()
    obj = {"object_id": "invented-object", "required": True, "state": "AVAILABLE", "content_hex": "616263",
           "sha256": hashlib.sha256(b"abc").hexdigest(), "byte_size": 3, "hash_scope": "FULL_OBJECT",
           "authored_version": None, "immutable_capture_id": "invented-capture", "origin": "invented-origin",
           "retrieval_utc": "invented-date", "terms": "invented-terms", "custody_reference": "invented-custody"}
    basis = {"manifest_sha256": digest([obj]), "manifest_version": "invented-v1", "inventory_scope_sha256": digest("invented-bounded-universe"), "required_object_ids_sha256": digest(["invented-object"]), "branch_id": "A_BASELINE_BIO",
             "schema_sha256": digest(p["schema_hashes"]), "executor_sha256": "1" * 64,
             "auditor_sha256": "2" * 64, "rule_language_version": "invented-rules-v1",
             "questions_sha256": digest(QUESTIONS), "repeat_policy_sha256": digest({"version": "invented-policy"})}
    def reader(name: str, order: int) -> dict[str, Any]:
        value = {"reader_id": name, "basis": copy.deepcopy(basis), "authored_contract_version": "v1",
                 "authored_contract_sha256": digest(name), "sealed_order": order, "read_started_order": 2,
                 "peer_access_before_seal": False, "independence_attested": True,
                 "authentication_reference": "invented-auth-" + name, "outcome_exposure": "NONE_DECLARED",
                 "assertions": [{"question_id": q, "value": "invented", "authority_object_id": "invented-object",
                                 "source_locator": "invented-section", "rule_locator": "invented-rule"}
                                for q in QUESTIONS], "legacy_table_hashes": {"table": "3" * 64}}
        value["seal_sha256"] = digest(value)
        return value
    p["config"]["prat_review"] = {"manifest": [obj], "required_object_ids": ["invented-object"], "inventory_scope": "invented-bounded-universe", "basis": basis, "questions": QUESTIONS,
         "repeat_policy": {"version": "invented-policy"}, "policy_locked_order": 1,
         "selection_inputs": ["timing", "qc"], "comparison_order": 5, "readers": [reader("invented-a", 3), reader("invented-b", 4)],
         "adjudications": [], "current_contract_sha256": "4" * 64, "export_schema_version": "prat-narrow-v1",
         "extra_artifacts": []}
    return p


def test_all_three_dependency_stages_block_without_upstream() -> None:
    for module, function in [("overlap", "validate_overlap"), ("exposure", "validate_exposure"), ("admission", "evaluate_admission")]:
        result = invoke(module, function, packet())
        assert result["status"] == "BLOCKED_UNKNOWN"
        assert result["reasons"] == ["DEPENDENCY_MISSING"]


def test_complete_invented_prat_protocol_never_authenticates_actual_evidence() -> None:
    p = prat()
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "READY"
    assert result["source_admission"] is False
    audit = next(row for row in result["audit"] if row["kind"] == "prat_protocol")
    assert audit["actual_source_evidence"] == "NOT_RUN"
    assert audit["actual_reader_authentication"] == "NOT_RUN"
    assert audit["canonical_admission"] == "BLOCKED_UNKNOWN"
    assert result["records"] == p["records"]


@pytest.mark.parametrize("change,reason", [
    ("prefix", "OBJECT_BYTES_MISMATCH"), ("size", "OBJECT_BYTES_MISMATCH"),
    ("stale_basis", "REVIEW_BASIS_MISMATCH"), ("seal", "FIRST_PASS_TAMPERED"),
    ("single_reader", "TWO_READERS_REQUIRED"), ("copy_reader", "READER_INDEPENDENCE_REQUIRED"),
    ("early_compare", "FIRST_PASS_ORDER_INVALID"), ("outcome_selection", "OUTCOME_SELECTION_PROHIBITED"),
    ("late_policy", "POLICY_LOCK_ORDER_INVALID"), ("export_sidecar", "PRAT_EXPORT_PROHIBITED"),
])
def test_prat_adversaries(change: str, reason: str) -> None:
    p = prat(); c = p["config"]["prat_review"]
    if change == "prefix": c["manifest"][0]["hash_scope"] = "HEADER_ONLY"
    if change == "size": c["manifest"][0]["byte_size"] = 4
    if change == "stale_basis": c["basis"]["manifest_version"] = "v2"
    if change == "seal": c["readers"][0]["assertions"][0]["value"] = "tampered"
    if change == "single_reader": c["readers"].pop()
    if change == "copy_reader": c["readers"][1] = copy.deepcopy(c["readers"][0])
    if change == "early_compare": c["comparison_order"] = 3
    if change == "outcome_selection": c["selection_inputs"].append("orr")
    if change == "late_policy": c["policy_locked_order"] = 3
    if change == "export_sidecar": c["extra_artifacts"] = [{"patient_id": "private"}]
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == ("BLOCKED_UNKNOWN" if change == "single_reader" else "FAIL")
    assert result["reasons"] == [reason]


def test_equal_legacy_hashes_cannot_hide_assertion_disagreement() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["readers"][1]["assertions"][0]["value"] = "conflicting"
    r = c["readers"][1]; r["seal_sha256"] = digest({k: v for k, v in r.items() if k != "seal_sha256"})
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["reasons"] == ["ASSERTION_DISAGREEMENT_UNRESOLVED"]
    conflicts = [a for a in result["audit"] if a["kind"] == "assertion_disagreement"]
    assert len(conflicts) == 1
    assert conflicts[0]["question_id"] == "identity"
    assert conflicts[0]["first_assertion"]["value"] == "invented"
    assert conflicts[0]["second_assertion"]["value"] == "conflicting"


def test_missing_locator_blocks_even_when_legacy_tables_equal() -> None:
    p = prat(); r = p["config"]["prat_review"]["readers"][1]
    r["assertions"][0]["source_locator"] = ""
    r["seal_sha256"] = digest({k: v for k, v in r.items() if k != "seal_sha256"})
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["reasons"] == ["ASSERTION_DISAGREEMENT_UNRESOLVED", "ASSERTION_EVIDENCE_MISSING"]


def test_prat_public_summary_has_no_private_channels_or_counts() -> None:
    result = invoke("prat_review", "review_prat_packet", prat())
    module = importlib.import_module("tools.a_dav.prat_review")
    summary = module.public_prat_summary(result)
    assert set(summary) == {"classification", "stage", "status", "reasons", "bindings", "analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed"}
    assert "invented" not in str(summary)
    assert "count" not in str(summary)


def test_prat_legacy_questions_cannot_omit_current_canonical_grains() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["questions"] = ["identity", "endpoint"]
    c["basis"]["questions_sha256"] = digest(c["questions"])
    for r in c["readers"]:
        r["basis"] = copy.deepcopy(c["basis"])
        r["assertions"] = [a for a in r["assertions"] if a["question_id"] in c["questions"]]
        r["seal_sha256"] = digest({k: v for k, v in r.items() if k != "seal_sha256"})
    r = invoke("prat_review", "review_prat_packet", p)
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert r["reasons"] == ["CURRENT_BRANCH_CHECKLIST_MISSING"]


def test_prat_scoped_object_inventory_must_include_required_object() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["required_object_ids"] = ["invented-object", "missing-object"]
    c["basis"]["required_object_ids_sha256"] = digest(c["required_object_ids"])
    for reader in c["readers"]:
        reader["basis"] = copy.deepcopy(c["basis"])
        reader["seal_sha256"] = digest({k: v for k, v in reader.items() if k != "seal_sha256"})
    r = invoke("prat_review", "review_prat_packet", p)
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert "OBJECT_MANIFEST_INCOMPLETE" in r["reasons"]


def test_prat_retains_resolved_disagreement_and_current_adjudication() -> None:
    p = prat(); c = p["config"]["prat_review"]; r = c["readers"][1]
    r["assertions"][0]["value"] = "different-invented-value"
    r["seal_sha256"] = digest({k: v for k, v in r.items() if k != "seal_sha256"})
    adj = {"question_id": "identity", "basis_sha256": digest(c["basis"]), "first_pass_sha256": sorted(x["seal_sha256"] for x in c["readers"]), "final_contract_sha256": c["current_contract_sha256"], "rationale": "invented", "adjudicator_id": "invented", "adjudication_date": "invented", "authentication_reference": "invented", "source_locator": "invented", "disposition": "RESOLVED_FIRST"}
    c["adjudications"] = [adj]
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "READY"
    conflict = next(a for a in result["audit"] if a["kind"] == "assertion_disagreement")
    assert conflict["first_assertion"]["value"] == "invented"
    assert conflict["second_assertion"]["value"] == "different-invented-value"
    assert conflict["adjudication"] == adj
    c["current_contract_sha256"] = "5" * 64
    assert invoke("prat_review", "review_prat_packet", p)["reasons"] == ["ADJUDICATION_INVALID"]


def test_prat_inventory_scope_change_invalidates_reader_basis() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["inventory_scope"] = "another-invented-bounded-universe"
    assert invoke("prat_review", "review_prat_packet", p)["reasons"] == ["REVIEW_BASIS_MISMATCH"]


def test_prat_missing_reader_auth_reference_has_distinct_block() -> None:
    p = prat(); r = p["config"]["prat_review"]["readers"][0]
    r.pop("authentication_reference")
    r["seal_sha256"] = digest({k: v for k, v in r.items() if k != "seal_sha256"})
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["reasons"] == ["READER_AUTHENTICATION_REFERENCE_MISSING"]


def test_prat_canonical_episode_binding_cannot_transfer_between_people() -> None:
    from test_group_a import packet as registry_packet
    p = prat(); p["records"] = registry_packet()["records"]
    p["records"]["episode_binding"][0]["patient_uid"] = "invented-wrong-person"
    r = invoke("prat_review", "review_prat_packet", p)
    assert r["status"] == "FAIL"
    assert r["reasons"] == ["FOREIGN_KEY_UNRESOLVED"]


def test_prat_changed_required_inventory_invalidates_first_pass_basis() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["required_object_ids"] = []
    assert invoke("prat_review", "review_prat_packet", p)["reasons"] == ["REVIEW_BASIS_MISMATCH"]


def test_prat_missing_second_first_pass_is_unknown_evidence() -> None:
    p = prat(); p["config"]["prat_review"]["readers"].pop()
    r = invoke("prat_review", "review_prat_packet", p)
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert r["reasons"] == ["TWO_READERS_REQUIRED"]


def test_prat_missing_seal_is_unknown_and_present_tampering_fails() -> None:
    p = prat(); p["config"]["prat_review"]["readers"][1].pop("seal_sha256")
    r = invoke("prat_review", "review_prat_packet", p)
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert r["reasons"] == ["FIRST_PASS_MISSING"]


def reseal_review_inventory(c: dict[str, Any]) -> None:
    c["basis"]["manifest_sha256"] = digest(c["manifest"])
    for reader in c["readers"]:
        reader["basis"] = copy.deepcopy(c["basis"])
        reader["seal_sha256"] = digest({k: v for k, v in reader.items() if k != "seal_sha256"})


@pytest.mark.parametrize("state", ["MISSING", "UNAVAILABLE", "UNINSPECTED", "SUPERSEDED"])
def test_review_required_inventory_overrides_optional_flag_after_fresh_seals(state: str) -> None:
    p = prat(); c = p["config"]["prat_review"]
    obj = c["manifest"][0]
    obj.update(state=state, required=False)
    obj.pop("content_hex")
    reseal_review_inventory(c)
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert "OBJECT_MANIFEST_INCOMPLETE" in result["reasons"]
    assert "ASSERTION_EVIDENCE_MISSING" in result["reasons"]
    assert result["source_admission"] is False


@pytest.mark.parametrize("state", ["MISSING", "UNAVAILABLE", "UNINSPECTED", "SUPERSEDED"])
def test_review_assertions_cannot_use_unavailable_optional_authority(state: str) -> None:
    p = prat(); c = p["config"]["prat_review"]
    optional = {"object_id": "invented-optional", "state": state, "required": False}
    c["manifest"].append(optional)
    for reader in c["readers"]:
        reader["assertions"][0]["authority_object_id"] = "invented-optional"
    reseal_review_inventory(c)
    result = invoke("prat_review", "review_prat_packet", p)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["reasons"] == ["ASSERTION_EVIDENCE_MISSING"]


def test_review_unreferenced_optional_missing_object_does_not_block() -> None:
    p = prat(); c = p["config"]["prat_review"]
    c["manifest"].append({"object_id": "invented-optional", "state": "MISSING", "required": False})
    reseal_review_inventory(c)
    assert invoke("prat_review", "review_prat_packet", p)["status"] == "READY"
