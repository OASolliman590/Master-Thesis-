"""Invented-data boundary tests for the Riaz baseline policy API and CLI."""
from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools.a_dav.core import DavError
from tools.a_dav.demo import synthetic_workflow_packet
from tools.a_dav.baseline_policy import POLICY_VERSION, build_baseline_packet, main, prepare_baseline
from tools.a_dav.baseline_policy import _RIAZ_SOURCE_HASHES


def _packet():
    packet = synthetic_workflow_packet()
    rows = packet["records"]
    rows["prior_exposure_record"] = []
    source = copy.deepcopy(rows["source_record"][0])
    for number, source_hash in enumerate(sorted(_RIAZ_SOURCE_HASHES), start=1):
        source_copy = copy.deepcopy(source)
        source_copy.update(source_object_id=f"synthetic-riaz-source-{number}", sha256=source_hash)
        rows["source_record"].append(source_copy)
    rows["clinical_outcome"][0]["raw_endpoint_label"] = "PR"
    rows["patient_registry"].append({**copy.deepcopy(rows["patient_registry"][0]),
                                      "patient_uid": "p2", "source_patient_id": "002",
                                      "source_aliases": []})
    pre = copy.deepcopy(rows["specimen_registry"][0])
    pre.update(specimen_uid="sp3", patient_uid="p2", raw_sample_aliases=["sample-003"],
               canonical_timing_category="PRE_INDEX_BASELINE")
    on = copy.deepcopy(pre)
    on.update(specimen_uid="sp4", raw_sample_aliases=["sample-004"],
              canonical_timing_category="UNKNOWN", baseline_candidate_status="NO", timing_raw_text="On")
    rows["specimen_registry"].extend([pre, on])
    for number, specimen in enumerate((pre, on), start=3):
        assay = copy.deepcopy(rows["assay_registry"][0])
        assay.update(assay_uid=f"a{number}", specimen_uid=specimen["specimen_uid"],
                    source_sample_id=specimen["raw_sample_aliases"][0],
                    matrix_header=specimen["raw_sample_aliases"][0])
        rows["assay_registry"].append(assay)
    outcome = copy.deepcopy(rows["clinical_outcome"][0])
    outcome.update(outcome_id="o2", patient_uid="p2", raw_endpoint_label="NE",
                   canonical_category="NE", orr_mapping=None, dcr_mapping=None,
                   evaluability="NOT_EVALUABLE", discrepancy_status="UNRESOLVED")
    rows["clinical_outcome"].append(outcome)
    packet["config"]["admission"]["ingestion_worksheet"] = []
    rows["episode_binding"] = [b for b in rows["episode_binding"] if b["subject_id"] != "sp2"]
    outcome_binding = next(row for row in rows["episode_binding"]
                           if row["subject_type"] == "CLINICAL_OUTCOME")
    rows["episode_binding"].append({**copy.deepcopy(outcome_binding),
        "binding_id": "bo2", "patient_uid": "p2", "subject_id": "o2"})
    rows["episode_binding"].append({**copy.deepcopy(rows["episode_binding"][0]),
        "binding_id": "bs3", "patient_uid": "p2", "subject_id": "sp3"})
    rows["treatment_episode"].append({**copy.deepcopy(rows["treatment_episode"][0]),
        "treatment_episode_id": "e2", "patient_uid": "p2"})
    for binding in rows["episode_binding"]:
        if binding.get("patient_uid") == "p2":
            binding["treatment_episode_id"] = "e2"
    categories = ["AUTHOR_SAMPLE_CODE_IDENTITY_CONFLICT", "AUTHOR_SAMPLE_ROW_MISSING",
                  "DUPLICATE_GEO_PATIENT_VISIT", "ON_TREATMENT_WINDOW_UNRESOLVED",
                  "OUTCOME_LABEL_DISAGREEMENT", "OUTCOME_LABEL_DISAGREEMENT",
                  "OUTCOME_LABEL_DISAGREEMENT", "AUTHOR_EXCLUSION_POLICY_UNRESOLVED",
                  "HARMONIZED_SAMPLE_COUNT_CROSSCHECK"]
    rows["_questions"] = [{"category": category, "status": "BLOCKED_UNKNOWN",
                           "evidence_pointers": []} for category in categories]
    # Only the exact, source-backed NE/UNK pair may close this raw vocabulary issue.
    rows["_questions"][5] = {"category": "OUTCOME_LABEL_DISAGREEMENT", "status": "BLOCKED_UNKNOWN",
        "evidence_pointers": [{"role": "author_clinical_table", "record": "002", "field": "BOR"}],
        "context": {"source_of_record_bor": "NE", "corroborating_label": "UNK"}}
    packet["config"]["admission"]["ingestion_worksheet"] = rows.pop("_questions")
    return packet


def test_baseline_packet_closes_pre_membership_without_mutating_source_packet():
    packet = _packet()
    before = copy.deepcopy(packet)
    scoped = build_baseline_packet(packet)
    assert packet == before
    assert {row["specimen_uid"] for row in scoped["records"]["specimen_registry"]} == {"sp1", "sp3"}
    assert {row["assay_uid"] for row in scoped["records"]["assay_registry"]} == {"a1", "a3"}
    assert {row["patient_uid"] for row in scoped["records"]["patient_registry"]} == {"p1", "p2"}
    assert {row["outcome_id"] for row in scoped["records"]["clinical_outcome"]} == {"o1", "o2"}
    assert len(scoped["records"]["source_record"]) == len(packet["records"]["source_record"])
    assert scoped["records"]["clinical_outcome"][1]["raw_endpoint_label"] == "NE"
    assert scoped["records"]["clinical_outcome"][1]["orr_mapping"] is None
    assert scoped["records"]["clinical_outcome"][1]["discrepancy_status"] == "RESOLVED"
    assert scoped["config"]["endpoints"]["version"] == POLICY_VERSION
    assert {row["mapping_rule_version"] for row in scoped["records"]["clinical_outcome"]} == {POLICY_VERSION}


def test_unknown_or_substantive_conflict_is_not_resolved():
    packet = _packet()
    packet["records"]["clinical_outcome"][1]["raw_endpoint_label"] = "PD"
    packet["records"]["clinical_outcome"][1]["canonical_category"] = "PD"
    scoped = build_baseline_packet(packet)
    assert scoped["records"]["clinical_outcome"][1]["discrepancy_status"] == "UNRESOLVED"
    packet["records"]["clinical_outcome"][1]["raw_endpoint_label"] = "NE"
    packet["records"]["clinical_outcome"][1]["discrepancy_status"] = "CONFLICT"
    scoped = build_baseline_packet(packet)
    assert scoped["records"]["clinical_outcome"][1]["discrepancy_status"] == "CONFLICT"
    packet["records"]["clinical_outcome"][1]["raw_endpoint_label"] = "NOT_A_KNOWN_LABEL"
    with pytest.raises(DavError, match="BASELINE_OUTCOME_CONFLICT"):
        build_baseline_packet(packet)


def test_additional_ne_pd_corroboration_keeps_patient_discrepancy_unresolved():
    packet = _packet()
    packet["config"]["admission"]["ingestion_worksheet"].append({
        "category": "OUTCOME_LABEL_DISAGREEMENT", "status": "BLOCKED_UNKNOWN",
        "evidence_pointers": [{"role": "author_clinical_table", "record": "002", "field": "BOR"}],
        "context": {"source_of_record_bor": "NE", "corroborating_label": "PD"}})
    scoped = build_baseline_packet(packet)
    assert scoped["records"]["clinical_outcome"][1]["discrepancy_status"] == "UNRESOLVED"


def test_wrong_source_objects_are_rejected_before_riaz_rules_apply():
    packet = _packet()
    packet["records"]["source_record"] = packet["records"]["source_record"][:1]
    with pytest.raises(DavError, match="BASELINE_SOURCE_MISMATCH"):
        build_baseline_packet(packet)


def test_source_priority_conflict_stays_blocked_in_rebuilt_endpoint_stage():
    from tools.a_dav.ingest import REPO_ROOT
    packet = _packet()
    conflict = copy.deepcopy(packet["records"]["clinical_outcome"][0])
    conflict.update(outcome_id="o3", raw_endpoint_label="PD", canonical_category="PD",
                    discrepancy_status="CONFLICT")
    packet["records"]["clinical_outcome"].append(conflict)
    binding = copy.deepcopy(next(row for row in packet["records"]["episode_binding"]
                                if row["subject_type"] == "CLINICAL_OUTCOME"))
    binding.update(binding_id="bo3", subject_id="o3")
    packet["records"]["episode_binding"].append(binding)
    output = REPO_ROOT / ".scratch" / "runtime" / ("baseline-conflict-out-" + uuid.uuid4().hex)
    try:
        result = prepare_baseline(packet, output)
        endpoints = next(row for row in result["summary"]["stages"] if row["stage"] == "endpoints")
        assert endpoints["status"] == "BLOCKED_UNKNOWN"
        assert "ENDPOINT_SOURCE_CONFLICT" in endpoints["reasons"]
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_missing_binding_keeps_endpoint_blocked_without_fabricated_reviewer(tmp_path: Path):
    from tools.a_dav.ingest import REPO_ROOT
    packet = _packet()
    packet["records"]["episode_binding"] = []
    output = REPO_ROOT / ".scratch" / "runtime" / ("baseline-unbound-out-" + uuid.uuid4().hex)
    try:
        result = prepare_baseline(packet, output)
        endpoints = next(row for row in result["summary"]["stages"] if row["stage"] == "endpoints")
        assert endpoints["status"] == "BLOCKED_UNKNOWN"
        assert "ENDPOINT_EPISODE_UNKNOWN" in endpoints["reasons"]
        assert result["packet"]["records"]["episode_binding"] == []
        assert all(not row.get("reviewer") and not row.get("reviewed_utc")
                   for row in result["packet"]["records"]["episode_binding"])
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_cli_writes_fresh_unsigned_packet_and_keeps_qc_pending(tmp_path: Path):
    from tools.a_dav.ingest import REPO_ROOT
    packet_path = REPO_ROOT / ".scratch" / "runtime" / ("baseline-policy-input-" + uuid.uuid4().hex + ".json")
    output = REPO_ROOT / ".scratch" / "runtime" / ("baseline-policy-out-" + uuid.uuid4().hex)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet = _packet()
    packet["config"]["admission"]["reviewer_worksheet"] = {"signature": {"reviewer_name": "stale"}}
    # The packet input contains only invented aliases and invented records.
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    try:
        assert main(["--packet", str(packet_path), "--out", str(output)]) == 0
        review_packet = json.loads((output / "review_packet.json").read_text(encoding="utf-8"))
        worksheet = json.loads((output / "reviewer_worksheet.json").read_text(encoding="utf-8"))
        assert "signature" not in worksheet
        questions = review_packet["config"]["admission"]["ingestion_worksheet"]
        assert len(questions) == 9
        assert sum(item["category"] == "OUTCOME_LABEL_DISAGREEMENT" for item in questions) == 3
        qc = [item for item in review_packet["config"]["admission"]["ingestion_worksheet"]
              if item["branch_disposition"] == "PENDING_OUTCOME_INDEPENDENT_QC_POLICY"]
        assert len(qc) == 1 and qc[0]["status"] == "BLOCKED_UNKNOWN"
        assert "reviewer_worksheet" not in review_packet["config"]["admission"]
        assert worksheet["context"]["branch_id"] == "A_BASELINE_BIO"
    finally:
        packet_path.unlink(missing_ok=True)
        shutil.rmtree(output, ignore_errors=True)


def test_output_keeps_private_runtime_boundary():
    with pytest.raises(DavError, match="OUTPUT_PATH_NOT_ALLOWED"):
        prepare_baseline(_packet(), Path("/private/tmp/riaz-baseline-outside"))


def test_generic_baseline_uses_declared_source_roles_and_retains_extra_specimen():
    packet = {'classification': 'PRIVATE_PATIENT_LEVEL', 'branch_id': 'A_BASELINE_BIO',
        'records': {'study_registry': [{'study_id': 'invented-study'}],
            'source_record': [{'source_object_id': 'SOURCE:invented:geo', 'sha256': 'a' * 64, 'retrieval_status': 'RETRIEVED', 'hash_scope': 'FULL_OBJECT'}, {'source_object_id': 'SOURCE:invented:matrix', 'sha256': 'b' * 64, 'retrieval_status': 'RETRIEVED', 'hash_scope': 'FULL_OBJECT'}],
            'patient_registry': [{'patient_uid': 'p1', 'source_patient_id': 'p1', 'patient_identity_confidence': 'UNRESOLVED'}, {'patient_uid': 'p2', 'source_patient_id': 'p2', 'patient_identity_confidence': 'UNRESOLVED'}],
            'specimen_registry': [{'specimen_uid': 's1', 'patient_uid': 'p1', 'canonical_timing_category': 'PRE_INDEX_BASELINE', 'baseline_candidate_status': 'YES'}, {'specimen_uid': 's2', 'patient_uid': 'p1', 'canonical_timing_category': 'PRE_INDEX_BASELINE', 'baseline_candidate_status': 'NO'}, {'specimen_uid': 's3', 'patient_uid': 'p2', 'canonical_timing_category': 'UNKNOWN', 'baseline_candidate_status': 'NO'}],
            'assay_registry': [{'assay_uid': 'a1', 'specimen_uid': 's1'}, {'assay_uid': 'a2', 'specimen_uid': 's2'}],
            'clinical_outcome': [{'outcome_id': 'o1', 'patient_uid': 'p1', 'raw_endpoint_label': 'R', 'canonical_category': 'SOURCE_POSITIVE', 'endpoint_class': 'SOURCE_BINARY'}]},
        'config': {'admission': {'ingestion_worksheet': {'items': []}}, 'registries': {}}, 'dependencies': {}}
    mapping = {'cohort': 'invented', 'geo_ingest': {'response_map': {'R': 'SOURCE_POSITIVE'}, 'endpoint_class': 'SOURCE_BINARY'},
        'decision_config': {'preview': {'required_roles': ['geo', 'matrix']}},
        'source_objects': {'geo': {'sha256': 'a' * 64}, 'matrix': {'sha256': 'b' * 64}}}
    result = build_baseline_packet(packet, field_map=mapping)
    assert [p['patient_uid'] for p in result['records']['patient_registry']] == ['p1']
    assert {s['specimen_uid'] for s in result['records']['specimen_registry']} == {'s1', 's2'}
    assert result['records']['clinical_outcome'][0]['endpoint_class'] == 'SOURCE_BINARY'
    assert result['records']['patient_registry'][0]['patient_identity_confidence'] == 'UNRESOLVED'


def test_generic_baseline_refuses_unretrieved_declared_source():
    packet = {'branch_id': 'A_BASELINE_BIO', 'records': {'source_record': [{'source_object_id': 'SOURCE:invented:geo', 'sha256': 'a' * 64, 'retrieval_status': 'NOT_ATTEMPTED', 'hash_scope': 'NOT_RETRIEVED'}], 'specimen_registry': [{'patient_uid': 'p1', 'specimen_uid': 's1', 'canonical_timing_category': 'PRE_INDEX_BASELINE', 'baseline_candidate_status': 'YES'}]}, 'config': {}}
    mapping = {'cohort': 'invented', 'geo_ingest': {'response_map': {}, 'endpoint_class': 'SOURCE_BINARY'}, 'decision_config': {'preview': {'required_roles': ['geo']}}, 'source_objects': {'geo': {'sha256': 'a' * 64}}}
    with pytest.raises(DavError, match='BASELINE_SOURCE_MISMATCH'):
        build_baseline_packet(packet, field_map=mapping)
