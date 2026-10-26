"""Public overlap/exposure/admission adversaries using invented normalized rows."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
import pytest
from tools.a_dav.core import BRANCHES, SchemaStore, finish
from functools import partial
from tools.a_dav.overlap import validate_overlap
from tools.a_dav.exposure import validate_exposure
from tools.a_dav.admission import evaluate_admission
from tools.a_dav.worksheet import build_worksheet
from test_group_a import packet as registry_packet

STORE = SchemaStore()
validate_overlap = partial(validate_overlap, schemas=STORE)
validate_exposure = partial(validate_exposure, schemas=STORE)
evaluate_admission = partial(evaluate_admission, schemas=STORE)


def packet() -> dict[str, Any]:
    p = registry_packet()
    p["config"].update({"overlap": {"review_complete": True}, "exposure": {"analysis_lineage_id": "invented-lineage", "review_complete": True, "covered_subjects": [{"subject_type": "STUDY_FAMILY", "subject_id": "f1"}]},
      "admission": {"required_source_object_ids": ["obj1"], "branch_policies": {"A_BASELINE_BIO": {"baseline": {"policy_version": "invented-v1", "source_locators": ["invented"]}, "endpoint": {"policy_version": "invented-v1", "source_locators": ["invented"], "endpoint_class": "ORR"}}}}})
    p["records"]["prior_exposure_record"] = [{"schema_version": "1.1.0", "exposure_id": "invented-use", "subject_type": "STUDY_FAMILY", "subject_id": "f1", "analysis_lineage_id": "invented-lineage", "fields_accessed": ["title"], "use": "METADATA_INSPECTION", "occurred_utc": None, "date_precision": "UNKNOWN", "actor_role": "invented", "independence_implication": "METADATA_ONLY_REVIEWED", "source_locators": ["invented"]}]
    p["records"]["clinical_outcome"][0]["endpoint_class"] = "ORR"
    return p


def seal(p: dict[str, Any], stages: tuple[str, ...] = ("registries",)) -> dict[str, Any]:
    p["dependencies"] = {}
    for stage in stages:
        p["dependencies"][stage] = finish(stage, p, p["records"], schemas=STORE)
    return p


def edge(id: str, a: str, b: str, certainty: str = "POSSIBLE") -> dict[str, Any]:
    return {"overlap_edge_id": id, "source_node_type": "STUDY", "source_node_id": a, "target_node_type": "STUDY", "target_node_id": b, "edge_type": "SAME_TRIAL", "evidence": "invented", "certainty": certainty, "implication_for_independence": "INDEPENDENCE_BLOCKED", "reviewer": "invented", "review_date": "invented", "source_locators": [{"kind": "INVENTED", "value": "invented"}]}


def test_potential_overlap_transitive_and_permutation_invariant() -> None:
    p = packet()
    for number in [2, 3]:
        s = deepcopy(p["records"]["study_registry"][0]); s.update(study_id=f"s{number}", publication_family_id=f"f{number}")
        f = deepcopy(p["records"]["publication_family"][0]); f.update(study_id=f"s{number}", publication_family_id=f"f{number}", publication_id=f"pub{number}")
        p["records"]["study_registry"].append(s); p["records"]["publication_family"].append(f)
    p["records"]["overlap_edge"] = [edge("edge1", "s1", "s2"), edge("edge2", "s2", "s3")]
    r = validate_overlap(seal(p))
    assert r["status"] == "READY"
    component = r["audit"][0]
    assert component["protection"] == "POTENTIAL_OR_UNKNOWN"
    assert {x["node_id"] for x in component["nodes"] if x["node_type"] == "STUDY"} == {"s1", "s2", "s3"}
    before = deepcopy(r)
    for rows in p["records"].values(): rows.reverse()
    assert validate_overlap(seal(p)) == before


def test_cross_namespace_alias_does_not_join_missing_patient() -> None:
    p = packet(); e = edge("edge", "s1", "s1"); e["target_node_type"] = "PATIENT"
    p["records"]["overlap_edge"] = [e]
    assert validate_overlap(seal(p))["reasons"] == ["OVERLAP_NODE_UNKNOWN"]


def test_same_trial_different_labels_protects_without_explicit_edges() -> None:
    p = packet(); p["records"]["study_registry"][0]["trial_id"] = "invented-trial"
    s = deepcopy(p["records"]["study_registry"][0]); s.update(study_id="s2", publication_family_id="f2")
    f = deepcopy(p["records"]["publication_family"][0]); f.update(study_id="s2", publication_family_id="f2", publication_id="pub2")
    p["records"]["study_registry"].append(s); p["records"]["publication_family"].append(f)
    result = validate_overlap(seal(p))
    assert len(result["audit"]) == 1
    assert result["audit"][0]["independence_certified"] is False


def test_false_independent_alias_is_contradiction() -> None:
    p = packet(); e = edge("edge", "s1", "s1", "VERIFIED"); e["implication_for_independence"] = "INDEPENDENT_FOR_DECLARED_UNIT"
    p["records"]["overlap_edge"] = [e]
    assert validate_overlap(seal(p))["status"] == "FAIL"


@pytest.mark.parametrize("use,implication,state,status", [
 ("METADATA_INSPECTION", "METADATA_ONLY_REVIEWED", "METADATA_ONLY", "READY"),
 ("MOLECULAR_RESPONSE_INSPECTION", "BLOCKS_UNTOUCHED_FOR_LINEAGE", "RESPONSE_ASSOCIATED", "READY"),
 ("UNKNOWN", "REVIEW_REQUIRED", "UNKNOWN", "BLOCKED_UNKNOWN"),
 ("CLINICAL_ENDPOINT_CURATION", "REVIEW_REQUIRED", "CLINICAL_ONLY", "READY")])
def test_prior_use_is_distinguished(use: str, implication: str, state: str, status: str) -> None:
    p = packet(); p["records"]["prior_exposure_record"][0].update(use=use, independence_implication=implication)
    result = validate_exposure(seal(p))
    assert result["status"] == status
    assert result["audit"][0]["state"] == state
    assert result["audit"][0]["untouched_certified"] is False


def test_missing_lineage_never_means_untouched() -> None:
    p = packet(); p["records"]["prior_exposure_record"][0]["analysis_lineage_id"] = "another-lineage"
    assert validate_exposure(seal(p))["status"] == "BLOCKED_UNKNOWN"


def test_metadata_label_cannot_hide_response_field() -> None:
    p = packet(); p["records"]["prior_exposure_record"][0]["fields_accessed"] = ["response"]
    assert validate_exposure(seal(p))["reasons"] == ["EXPOSURE_CONTRADICTION"]


def admission_packet() -> dict[str, Any]:
    return seal(packet(), ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))


def test_synthetic_eligibility_never_admits_and_preserves_all_rows() -> None:
    p = admission_packet(); before = deepcopy(p)
    r = evaluate_admission(p)
    assert r["status"] == "READY"
    assert r["audit"][0]["eligibility"] == "READY"
    assert r["source_admission"] is False
    draft = r["records"]["cohort_admission_receipt"][0]
    assert draft["admission_status"] == "BLOCKED_UNKNOWN"
    assert draft["approved_branches"] == []
    assert {x["status"] for x in draft["gate_results"]} == {"BLOCKED_UNKNOWN"}
    for table, rows in before["records"].items(): assert sorted(r["records"][table], key=str) == sorted(rows, key=str)
    assert p == before


def test_signed_public_worksheet_admits_only_when_upstream_evidence_is_ready() -> None:
    p = admission_packet()
    p["classification"] = "PRIVATE_PATIENT_LEVEL"
    p["records"]["source_record"][0]["access_route"] = "PUBLIC_DIRECT"
    worksheet = build_worksheet(p)
    worksheet["signature"] = {"reviewer_name": "Thesis Author", "review_date": "2026-10-25"}
    worksheet["decisions"] = [
        {"item_id": item["item_id"],
         "status": "BLOCKED_UNKNOWN" if item.get("gate") == "V8" else "PASS",
         "rationale": "Reviewed against the cited source."}
        for item in worksheet["items"]
    ]
    p = seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))
    result = evaluate_admission(p, reviewer_worksheet=worksheet)
    assert result["status"] == "READY"
    receipt = result["records"]["cohort_admission_receipt"][0]
    assert receipt["admission_status"] == "ADMITTED"
    assert receipt["approved_branches"] == ["A_BASELINE_BIO"]
    assert receipt["reviewer"] == "Thesis Author"
    assert next(gate for gate in receipt["gate_results"] if gate["gate"] == "V8") == {
        "gate": "V8", "status": "BLOCKED_UNKNOWN", "reason": "MATRIX_BUILD_PENDING"}

    invalid_v8 = deepcopy(worksheet)
    next(decision for decision in invalid_v8["decisions"] if decision["item_id"] == "V8")["status"] = "PASS"
    rejected = evaluate_admission(p, reviewer_worksheet=invalid_v8)
    assert rejected["status"] == "FAIL"

    p["records"]["source_record"][0]["validation_status"] = "FAIL"
    failed_worksheet = build_worksheet(p)
    failed_worksheet["signature"] = worksheet["signature"]
    failed_worksheet["decisions"] = worksheet["decisions"]
    p = seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))
    failed = evaluate_admission(p, reviewer_worksheet=failed_worksheet)
    assert failed["status"] == "FAIL"
    assert failed["records"]["cohort_admission_receipt"][0]["admission_status"] == "EXCLUDED"


def test_signed_worksheet_does_not_contradict_declared_clinical_ici() -> None:
    p = admission_packet()
    p["classification"] = "PRIVATE_PATIENT_LEVEL"
    p["records"]["study_registry"][0]["study_class"] = "CLINICAL_ICI"
    p["records"]["source_record"][0]["access_route"] = "PUBLIC_DIRECT"
    worksheet = build_worksheet(p)
    worksheet["signature"] = {"reviewer_name": "Thesis Author", "review_date": "2026-10-25"}
    worksheet["decisions"] = [
        {"item_id": item["item_id"], "status": "BLOCKED_UNKNOWN" if item.get("gate") == "V8" else "PASS",
         "rationale": "Reviewed against the cited source."}
        for item in worksheet["items"]
    ]
    p = seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))

    result = evaluate_admission(p, reviewer_worksheet=worksheet)

    audit = next(row for row in result["audit"] if row.get("kind") == "admission_eligibility")
    assert audit["criteria"]["clinical_ici"] == "SUPPORTED"
    assert result["records"]["cohort_admission_receipt"][0]["admission_status"] != "EXCLUDED"


def test_undeclared_study_class_blocks_as_unknown_without_exclusion() -> None:
    p = admission_packet()
    p["classification"] = "PRIVATE_PATIENT_LEVEL"
    p["records"]["study_registry"][0].pop("study_class")
    p["records"]["source_record"][0]["access_route"] = "PUBLIC_DIRECT"
    worksheet = build_worksheet(p)
    worksheet["signature"] = {"reviewer_name": "Thesis Author", "review_date": "2026-10-25"}
    worksheet["decisions"] = [
        {"item_id": item["item_id"], "status": "BLOCKED_UNKNOWN" if item.get("gate") == "V8" else "PASS",
         "rationale": "Reviewed against the cited source."}
        for item in worksheet["items"]
    ]
    p = seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))

    result = evaluate_admission(p, reviewer_worksheet=worksheet)

    audit = next(row for row in result["audit"] if row.get("kind") == "admission_eligibility")
    receipt = result["records"]["cohort_admission_receipt"][0]
    assert audit["criteria"]["clinical_ici"] == "UNKNOWN"
    assert receipt["admission_status"] == "BLOCKED_UNKNOWN"


def test_superseded_v7_does_not_admit_real_cohort() -> None:
    p = admission_packet()
    p["classification"] = "PRIVATE_PATIENT_LEVEL"
    p["records"]["source_record"][0]["access_route"] = "PUBLIC_DIRECT"
    worksheet = build_worksheet(p)
    worksheet["signature"] = {"reviewer_name": "Thesis Author", "review_date": "2026-10-25"}
    worksheet["decisions"] = [
        {"item_id": item["item_id"],
         "status": "BLOCKED_UNKNOWN" if item.get("gate") == "V8" else
                   "SUPERSEDED" if item.get("gate") == "V7" else "PASS",
         "rationale": "Reviewed with the available source context."}
        for item in worksheet["items"]
    ]
    p = seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))
    result = evaluate_admission(p, reviewer_worksheet=worksheet)
    receipt = result["records"]["cohort_admission_receipt"][0]
    assert receipt["admission_status"] == "BLOCKED_UNKNOWN"
    assert receipt["approved_branches"] == []
    assert next(gate for gate in receipt["gate_results"] if gate["gate"] == "V7")["status"] == "SUPERSEDED"


def test_required_source_cannot_disappear() -> None:
    p = packet(); p["config"]["admission"]["required_source_object_ids"].append("missing")
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert "REQUIRED_SOURCE_MISSING" in r["reasons"]


@pytest.mark.parametrize("branch", sorted(BRANCHES))
def test_every_branch_requires_current_structured_evidence(branch: str) -> None:
    p = packet(); p["branch_id"] = branch
    p["config"]["admission"]["branch_policies"] = {branch: {"status": "PASS", "reviewer": "invented", "V1": "PASS", "V6": "PASS"}}
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert "BRANCH_EVIDENCE_UNKNOWN" in r["reasons"]


def test_stale_upstream_and_non_ici_known_contradiction_fail() -> None:
    p = admission_packet(); p["dependencies"]["timing"]["status"] = "READY"; p["dependencies"]["timing"]["audit"] = [{"tampered": True}]
    assert evaluate_admission(p)["reasons"] == ["RECEIPT_TAMPERED"]
    p = packet(); p["records"]["study_registry"][0]["study_class"] = "UNTREATED_MOLECULAR"
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "FAIL"
    assert "BRANCH_CRITERION_FAILED" in r["reasons"]
    audit = next(row for row in r["audit"] if row.get("kind") == "admission_eligibility")
    assert audit["criteria"]["clinical_ici"] == "CONTRADICTED"
    assert r["records"]["cohort_admission_receipt"][0]["admission_status"] == "EXCLUDED"


def test_all_families_must_have_explicit_exposure_coverage() -> None:
    p = packet(); f = deepcopy(p["records"]["publication_family"][0]); f["publication_family_id"] = "uncovered-family"
    p["records"]["publication_family"].append(f)
    r = validate_exposure(seal(p))
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert "EXPOSURE_REVIEW_REQUIRED" in r["reasons"]


def test_required_source_unknown_policy_does_not_mask_present_failure() -> None:
    p = packet(); p["records"]["source_record"][0]["validation_status"] = "FAIL"
    p["config"]["admission"]["branch_policies"] = {}
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "FAIL"
    assert "BRANCH_CRITERION_FAILED" in r["reasons"]


def test_wrong_study_policy_record_reference_is_contradiction() -> None:
    p = packet(); p["branch_id"] = "PROSTATE_TRANSPORT"; p["records"]["study_registry"][0]["cancer_type"] = "prostate"
    ev = {"policy_version": "invented", "source_locators": ["invented"], "rule": "invented", "record_refs": [{"table": "patient_registry", "key": "patient_uid", "value": "other-study-patient"}]}
    other = deepcopy(p["records"]["patient_registry"][0]); other.update(patient_uid="other-study-patient", study_id="other-study")
    p["records"]["patient_registry"].append(other)
    p["config"]["admission"]["branch_policies"] = {"PROSTATE_TRANSPORT": {name: deepcopy(ev) for name in ["prostate_eligibility", "transport_assay", "transport_specimen", "claim_ceiling"]}}
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "FAIL"


def test_structural_source_can_simulate_only_after_actual_assay_api_verifies_it() -> None:
    from tools.a_dav.registries import build_registries
    from tools.a_dav.endpoints import map_endpoints
    from tools.a_dav.timing import validate_timing
    from tools.a_dav.assays import validate_assays
    from test_group_a import endpoint_config, timing_config, assay_config
    p = assay_config(timing_config(endpoint_config(packet())))
    p["records"]["source_record"][0]["validation_status"] = "STRUCTURAL_ONLY"
    p["dependencies"] = {}
    for stage, function in [("registries", build_registries), ("endpoints", map_endpoints), ("timing", validate_timing), ("assays", validate_assays), ("overlap", validate_overlap), ("exposure", validate_exposure)]:
        r = function(p, schemas=STORE)
        assert r["status"] == "READY", (stage, r["reasons"])
        p["dependencies"][stage] = r
        p["records"] = r["records"]
    result = evaluate_admission(p)
    assert result["status"] == "READY"
    assert result["records"]["source_record"][0]["validation_status"] == "STRUCTURAL_ONLY"
    assert result["records"]["cohort_admission_receipt"][0]["admission_status"] == "BLOCKED_UNKNOWN"
    assert result["source_admission"] is False


def test_arbitrary_existing_record_and_rule_cannot_replace_branch_specific_policy() -> None:
    p = packet(); p["branch_id"] = "A_P2_DEVELOPMENT"
    p["config"]["admission"]["branch_policies"]["A_P2_DEVELOPMENT"] = deepcopy(p["config"]["admission"]["branch_policies"]["A_BASELINE_BIO"])
    policy = p["config"]["admission"]["branch_policies"]["A_P2_DEVELOPMENT"]
    for name in ["assay_compatibility", "class_representation", "development_freeze"]:
        policy[name] = {"policy_version": "invented", "source_locators": ["invented"], "rule": "PASS", "record_refs": [{"table": "patient_registry", "key": "patient_uid", "value": "p1"}]}
    r = evaluate_admission(seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure")))
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert r["audit"][0]["criteria"]["class_representation"] == "UNKNOWN"


def two_studies(p: dict[str, Any]) -> None:
    s = deepcopy(p["records"]["study_registry"][0]); s.update(study_id="s2", publication_family_id="f2")
    f = deepcopy(p["records"]["publication_family"][0]); f.update(study_id="s2", publication_family_id="f2")
    p["records"]["study_registry"].append(s); p["records"]["publication_family"].append(f)


def test_shared_publication_under_different_studies_is_protected() -> None:
    p = packet(); two_studies(p)
    r = validate_overlap(seal(p))
    assert r["status"] == "READY"
    assert len(r["audit"]) == 1


def test_same_repository_accession_is_alias_but_cross_namespace_is_not() -> None:
    p = packet(); two_studies(p)
    p["records"]["publication_family"][1]["publication_id"] = "other-publication"
    p["records"]["source_record"][0]["accession"] = "invented-accession"
    other = deepcopy(p["records"]["source_record"][0]); other.update(source_object_id="obj2", study_id="s2", publication_family_id="f2", sha256="b" * 64)
    p["records"]["source_record"].append(other)
    assert len(validate_overlap(seal(p))["audit"]) == 1
    other["repository"] = "OTHER_INVENTED_NAMESPACE"
    assert len(validate_overlap(seal(p))["audit"]) == 2


def test_known_clinical_curation_is_retained_without_untouched_claim() -> None:
    p = packet(); p["records"]["prior_exposure_record"][0].update(use="CLINICAL_ENDPOINT_CURATION", independence_implication="REVIEW_REQUIRED")
    r = validate_exposure(seal(p))
    assert r["status"] == "READY"
    assert r["audit"][0]["state"] == "CLINICAL_ONLY"
    assert r["audit"][0]["untouched_certified"] is False


def test_admission_same_draft_is_not_duplicated_on_repeat() -> None:
    p = admission_packet(); r = evaluate_admission(p)
    p["records"] = r["records"]
    seal(p, ("registries", "endpoints", "timing", "assays", "overlap", "exposure"))
    repeated = evaluate_admission(p)
    assert repeated["status"] == "READY"
    assert len(repeated["records"]["cohort_admission_receipt"]) == 1


@pytest.mark.parametrize("unsupported,aggregate_status,second_status", [
    ("missing_evidence", "BLOCKED_UNKNOWN", "BLOCKED_UNKNOWN"),
    ("non_ici", "FAIL", "FAIL"),
    ("source_failure", "FAIL", "FAIL"),
])
def test_review_study_eligibility_is_scoped_and_invariant_under_reversal(
    unsupported: str, aggregate_status: str, second_status: str,
) -> None:
    p = packet(); two_studies(p)
    other = deepcopy(p["records"]["source_record"][0])
    other.update(source_object_id="obj2", study_id="s2", publication_family_id="f2")
    p["records"]["source_record"].append(other)
    p["config"]["admission"]["required_source_object_ids"].append("obj2")
    if unsupported == "non_ici":
        p["records"]["study_registry"][1]["study_class"] = "UNTREATED_MOLECULAR"
    if unsupported == "source_failure":
        other["validation_status"] = "FAIL"
    stages = ("registries", "endpoints", "timing", "assays", "overlap", "exposure")
    forward = evaluate_admission(seal(p, stages))
    reversed_packet = deepcopy(p)
    for rows in reversed_packet["records"].values():
        rows.reverse()
    reversed_result = evaluate_admission(seal(reversed_packet, stages))
    assert forward["status"] == aggregate_status
    expected = {"s1": "READY", "s2": second_status}
    assert {a["study_id"]: a["eligibility"] for a in forward["audit"] if a["kind"] == "admission_eligibility"} == expected
    assert {a["study_id"]: a["eligibility"] for a in reversed_result["audit"] if a["kind"] == "admission_eligibility"} == expected
    assert reversed_result == forward
