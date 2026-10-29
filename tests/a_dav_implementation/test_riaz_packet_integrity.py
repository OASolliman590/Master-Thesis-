"""Invented-data regression tests for field-map integrity and source certification."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.a_dav.admit import run_signed_admission
from tools.a_dav.ingest import build_canonical_records
from tools.a_dav.delimited import read_delimited_table


def test_admit_rejects_packet_study_class_that_disagrees_with_field_map() -> None:
    packet = {"records": {"study_registry": [{"study_id": "invented-study",
                                               "study_class": "OTHER"}]}}
    with pytest.raises(ValueError, match="FIELD_MAP_STUDY_CLASS_MISMATCH"):
        run_signed_admission(packet, {"study_class": "CLINICAL_ICI"}, {},
                             Path(".scratch/runtime/invented/unused"))


def test_geo_source_name_maps_to_compartment_and_unmatched_values_stay_unknown() -> None:
    field_map: dict[str, Any] = {
        "cohort": "invented_cohort", "branch_id": "A_BASELINE_BIO",
        "study_class": "CLINICAL_ICI",
        "source_objects": {"geo_family_soft": {"sha256": "a" * 64,
            "locator": "https://example.invalid/soft", "version": "v1", "format": "GEO_FAMILY_SOFT"},
            "author_sample_table": {"sha256": "b" * 64, "locator": "https://example.invalid/sample",
                                     "version": "v1", "format": "DELIMITED_CSV"},
            "author_clinical_table": {"sha256": "c" * 64, "locator": "https://example.invalid/clinical",
                                       "version": "v1", "format": "DELIMITED_CSV"}},
        "sample_identity": {"title_regex": r"^(Pt\d+)_(Pre|On)", "patient_group": 1, "visit_group": 2},
        "geo": {"characteristics": {"visit": "visit (pre or on treatment)", "response": "response"},
                "relation_kinds": []},
        "biological_compartment": {"source_name_field": "source_name_ch1",
                                    "source_name_map": {"tumor": "TUMOUR"}},
        "author_sample_table": {"sample_name_column": 0, "patient_column": 1, "bam_suffix": ".bam",
            "response_positions": {"bor": 2, "response_primary": 3, "response_alternative": 4},
            "sample_name_rule": {"regex": r"\.(\d+)$", "replacement": r"-\1"}},
        "author_clinical_table": {"patient_column": 0, "bor_column": "BOR", "cohort_column": "Cohort"},
        "treatment": {"prior_ipilimumab_by_cohort": {}}, "labels": {},
        "measurement_representations": {},
    }
    parsed = {"geo_family_soft": [
        {"accession": "invented-sample-1", "title": "Pt999_Pre_x", "source_name_ch1": "tumor",
         "characteristics": [{"key": "visit (pre or on treatment)", "value": "Pre"}],
         "relations": []},
        {"accession": "invented-sample-2", "title": "Pt998_Pre_x", "source_name_ch1": "mystery",
         "characteristics": [{"key": "visit (pre or on treatment)", "value": "Pre"}],
         "relations": []}],
        "author_sample_table": read_delimited_table(
            b"Sample,PatientID,BOR,Response,Response\nPt999_Pre_x,Pt999,PR,PRCR,LB\nPt998_Pre_x,Pt998,SD,SD,SD\n",
            delimiter=","),
        "author_clinical_table": read_delimited_table(
            b"PatientID,BOR,Cohort\nPt999,PR,NIV3-NAIVE\nPt998,SD,NIV3-NAIVE\n", delimiter=",")}
    rows = build_canonical_records(parsed, {}, field_map, [])
    assert rows["study_registry"][0]["study_class"] == "CLINICAL_ICI"
    assert [row["biological_compartment"] for row in rows["specimen_registry"]] == ["TUMOUR", "UNKNOWN"]


def test_required_source_roles_are_materialized_from_field_map_declaration() -> None:
    # The field-map role declaration is the policy source; optional objects remain optional.
    from pathlib import Path
    from tools.a_dav.field_maps import load_field_map

    field_map = load_field_map(Path("tools/a_dav/field_maps/riaz_gse91061.json"))
    assert field_map["proposal_generation"]["stage_config"]["admission"]["required_source_roles"] == [
        "geo_family_soft", "author_sample_table", "author_clinical_table", "author_fpkm_hg19"]


def test_source_pass_requires_hash_parse_and_signed_join_decisions() -> None:
    from tools.a_dav.admit import certify_required_source_validation

    source_roles = ("geo_family_soft", "author_sample_table", "author_clinical_table")
    packet = {"records": {"source_record": [
                {"source_object_id": f"invented:{role}", "sha256": chr(97 + index) * 64,
                 "hash_scope": "FULL_OBJECT", "retrieval_status": "RETRIEVED",
                 "validation_status": "STRUCTURAL_ONLY", "notes": None}
                for index, role in enumerate(source_roles)],
              "patient_registry": [{"patient_uid": "invented:p1", "patient_identity_confidence": "VERIFIED"},
                                  {"patient_uid": "invented:p2", "patient_identity_confidence": "VERIFIED"}],
              "specimen_registry": [{"specimen_uid": "invented:s1", "patient_uid": "invented:p1",
                                     "timing_raw_text": "Pre"},
                                    {"specimen_uid": "invented:s2", "patient_uid": "invented:p2",
                                     "timing_raw_text": "Pre"}],
              "clinical_outcome": [{"outcome_id": "invented:o1", "patient_uid": "invented:p1",
                                    "raw_endpoint_label": "PR"},
                                   {"outcome_id": "invented:o2", "patient_uid": "invented:p2",
                                    "raw_endpoint_label": "SD"}]},
              "config": {"ingestion_validation": {"sha256_verified_roles": list(source_roles),
                                                   "parsed_source_roles": list(source_roles),
                                                   "adapter_by_role": {role: "INVENTED_ADAPTER"
                                                                       for role in source_roles}}}}
    field_map = {"source_objects": {role: {"sha256": chr(97 + index) * 64,
                                           "format": "INVENTED_ADAPTER"}
                                    for index, role in enumerate(source_roles)},
                 "source_validation": {"roles": list(source_roles), "baseline_specimen_patient_links": 2,
                                       "baseline_bor_patients": 2}}
    ingestion_validation = packet["config"]["ingestion_validation"]
    certified = certify_required_source_validation(packet, field_map, {"V4": "PASS", "V5": "PASS"},
                                                   ingestion_validation)
    assert {row["validation_status"] for row in certified["records"]["source_record"]} == {"PASS"}
    assert all("FULL_OBJECT_SHA256_VERIFIED" in row["notes"] and
               "DECLARED_ADAPTER_PARSE_PASS" in row["notes"] and
               "SIGNED_V4_AND_V5_PASS" in row["notes"]
               for row in certified["records"]["source_record"])

    unsigned_decisions = certify_required_source_validation(
        packet, field_map, {"V4": "PASS", "V5": "BLOCKED_UNKNOWN"}, ingestion_validation)
    assert {row["validation_status"] for row in unsigned_decisions["records"]["source_record"]} == {
        "STRUCTURAL_ONLY"}

    missing_hash = dict(ingestion_validation)
    missing_hash["sha256_verified_roles"] = source_roles[:-1]
    hash_not_verified = certify_required_source_validation(
        packet, field_map, {"V4": "PASS", "V5": "PASS"}, missing_hash)
    assert [row["validation_status"] for row in hash_not_verified["records"]["source_record"]] == [
        "PASS", "PASS", "STRUCTURAL_ONLY"]

    missing_parse = dict(ingestion_validation)
    missing_parse["parsed_source_roles"] = source_roles[:-1]
    parse_not_verified = certify_required_source_validation(
        packet, field_map, {"V4": "PASS", "V5": "PASS"}, missing_parse)
    assert [row["validation_status"] for row in parse_not_verified["records"]["source_record"]] == [
        "PASS", "PASS", "STRUCTURAL_ONLY"]


def test_selected_matrix_source_requires_signed_v3_to_upgrade() -> None:
    from tools.a_dav.admit import certify_required_source_validation
    sha = 'e' * 64
    packet = {'records':{'source_record':[{'source_object_id':'invented-matrix','sha256':sha,
        'hash_scope':'FULL_OBJECT','retrieval_status':'RETRIEVED','validation_status':'STRUCTURAL_ONLY'}],
        'patient_registry':[{'patient_uid':'invented-p','patient_identity_confidence':'VERIFIED'}],
        'specimen_registry':[{'specimen_uid':'invented-s','patient_uid':'invented-p','timing_raw_text':'Pre'}],
        'clinical_outcome':[{'patient_uid':'invented-p','raw_endpoint_label':'invented'}]},
        'config':{'assays':{'matrices':[{'source_sha256':sha}]}}}
    fmap = {'source_objects':{'invented_matrix':{'sha256':sha,'format':'MATRIX_HEADER_CSV'}},
            'source_validation':{'roles':['invented_matrix'],'baseline_specimen_patient_links':1,'baseline_bor_patients':1}}
    evidence = {'sha256_verified_roles':['invented_matrix'],'parsed_source_roles':['invented_matrix'],
                'adapter_by_role':{'invented_matrix':'MATRIX_HEADER_CSV'}}
    no_v3 = certify_required_source_validation(packet, fmap, {'V4':'PASS','V5':'PASS'}, evidence)
    assert no_v3['records']['source_record'][0]['validation_status'] == 'STRUCTURAL_ONLY'
    with_v3 = certify_required_source_validation(packet, fmap, {'V3':'PASS','V4':'PASS','V5':'PASS'}, evidence)
    assert with_v3['records']['source_record'][0]['validation_status'] == 'PASS'
