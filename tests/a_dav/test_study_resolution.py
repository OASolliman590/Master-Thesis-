"""Tests for DAV-T02 study and publication-family resolution (A-DAV-03).

All records here are SYNTHETIC: fictional identifiers and example.org locators.
The public NCBI tracer fixtures are checked in the final section, offline only.
"""

import copy
import hashlib
import json
import random
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.a_dav import study_resolution as sr
from tools.a_dav.search_log import candidate_packet_id
from tools.a_dav.study_resolution import (
    ResolutionError,
    render_alias_tsv,
    render_publication_tsv,
    render_study_tsv,
    resolve,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "A_DATA_ACQUISITION_VALIDATION"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "study_resolution"
VALID_QUERY_IDS = {"SYN-QUERY-0001"}
SYNTHETIC_LOCATOR = {"kind": "URL", "value": "https://example.org/SYNTHETIC/record", "page_or_section": "synthetic section"}


def _spec_json(relative):
    return json.loads((SPEC / relative).read_text(encoding="utf-8"))


def _template_header(name):
    return (SPEC / "templates" / name).read_text(encoding="utf-8").splitlines()[0].split("\t")


STUDY_SCHEMA = _spec_json("schemas/study_registry.schema.json")
PUBLICATION_SCHEMA = _spec_json("schemas/publication_family.schema.json")


# ---------------------------------------------------------------- fixtures


def make_packet(query_ids=("SYN-QUERY-0001",), label="synthetic catalogue packet", **overrides):
    content = {
        "lane": "catalogue_resolution",
        "query_ids": list(query_ids),
        "candidate_label": label,
        "verified_facts": [{
            "claim": "Synthetic catalogue identifier listed.",
            "source_locator": {"kind": "URL", "value": "https://example.org/SYNTHETIC/search", "page_or_section": "synthetic"},
        }],
        "inferences": [{"statement": "Synthetic inference.", "supporting_fact_indices": [0]}],
        "unknowns": [{"field": "publication_family", "resolution_path": "Review originals.", "blocking_branches": ["admission"]}],
        "proposed_records": {},
        "suspected_overlap": [],
        "recommended_next_action": "DAV-T02 integrator decision",
        "agent_id": "synthetic-agent",
        "completed_utc": "2026-10-17T09:00:00Z",
    }
    content.update(overrides)
    return {"packet_id": candidate_packet_id(content), **content}


def study(study_id="SYN-STUDY-A", family="SYN-FAM-A", **overrides):
    value = {
        "study_id": study_id,
        "publication_family_id": family,
        "study_title": "SYNTHETIC study " + study_id[-1],
        "study_class": "CLINICAL_ICI",
        "cancer_type": "SYNTHETIC_TUMOUR",
        "study_design": "SYNTHETIC design",
        "candidate_paper_branches": ["SYN_BRANCH_1"],
        "access_status": "SYNTHETIC_NOT_RETRIEVED",
        "source_repositories": [],
        "source_locators": [dict(SYNTHETIC_LOCATOR)],
    }
    value.update(overrides)
    return value


def alias(value, target, certainty="VERIFIED", alias_type="GEO_SERIES", evidence_type="REPOSITORY_LINK", **overrides):
    row = {
        "alias_type": alias_type,
        "alias_value": value,
        "canonical_study_id": target,
        "source_locator": dict(SYNTHETIC_LOCATOR),
        "evidence_type": evidence_type,
        "certainty": certainty,
        "notes": None,
    }
    row.update(overrides)
    return row


def publication(pub_id, study_id="SYN-STUDY-A", family="SYN-FAM-A", role="PRIMARY_CLINICAL", **overrides):
    row = {
        "publication_id": pub_id,
        "study_id": study_id,
        "publication_family_id": family,
        "publication_role": role,
        "doi": None,
        "pmid": None,
        "data_reused": None,
        "patient_subset": None,
        "assay_subset": None,
        "treatment_subset": None,
        "outcome_subset": None,
        "known_overlap": None,
        "source_object_ids": [],
        "independence_claim": "UNRESOLVED",
        "source_locators": [dict(SYNTHETIC_LOCATOR)],
        "notes": None,
    }
    row.update(overrides)
    return row


def reuse(**overrides):
    value = {
        "data_reused": "SYNTHETIC processed matrix",
        "patient_subset": "SYNTHETIC all eligible",
        "assay_subset": "SYNTHETIC RNA",
        "treatment_subset": "SYNTHETIC anti-PD-1",
        "outcome_subset": "SYNTHETIC response",
    }
    value.update(overrides)
    return value


def superseries(origin="SYN-STUDY-A", certainty="VERIFIED", subseries=None, accession="GSE900045"):
    if subseries is None:
        subseries = [
            {"accession": "GSE900044", "modality": "RNA", "sra_study": "SRP900044", "certainty": "VERIFIED",
             "evidence_type": "REPOSITORY_LINK", "source_locator": dict(SYNTHETIC_LOCATOR),
             "modality_locator": dict(SYNTHETIC_LOCATOR), "sra_locator": dict(SYNTHETIC_LOCATOR)},
            {"accession": "GSE900043", "modality": "DNA_METHYLATION", "sra_study": "UNKNOWN", "certainty": "VERIFIED",
             "evidence_type": "REPOSITORY_LINK", "source_locator": dict(SYNTHETIC_LOCATOR),
             "modality_locator": dict(SYNTHETIC_LOCATOR), "sra_locator": dict(SYNTHETIC_LOCATOR)},
        ]
    return {
        "superseries_accession": accession,
        "originating_study_id": origin,
        "certainty": certainty,
        "evidence_type": "REPOSITORY_LINK",
        "source_locator": dict(SYNTHETIC_LOCATOR),
        "subseries": subseries,
    }


def make_decision(packets=None, **overrides):
    packets = packets if packets is not None else [make_packet()]
    value = {
        "decision_id": "SYN-DEC-0001",
        "reviewer": "synthetic-integrator",
        "decided_utc": "2026-10-17T10:00:00Z",
        "provisional": False,
        "packet_ids": [packet["packet_id"] for packet in packets],
        "studies": [study()],
        "aliases": [],
        "publications": [],
        "superseries": [],
        "overlap_flags": [],
    }
    value.update(overrides)
    return value


def build(decision=None, packets=None, schemas=None, **overrides):
    packets = packets if packets is not None else [make_packet()]
    if decision is None:
        decision = make_decision(packets, **overrides)
    study_schema, publication_schema = schemas or (STUDY_SCHEMA, PUBLICATION_SCHEMA)
    return resolve(packets, decision, VALID_QUERY_IDS, study_schema, publication_schema)


def assert_code(code, fn):
    with pytest.raises(ResolutionError) as error:
        fn()
    assert error.value.code == code, error.value


def rich_decision(packets):
    return make_decision(
        packets,
        studies=[
            study("SYN-STUDY-A", "SYN-FAM-A"),
            study("SYN-STUDY-B", "SYN-FAM-B", study_title="SYNTHETIC study B", cancer_type="SYNTHETIC_TUMOUR_2"),
        ],
        aliases=[
            alias("GSE900001", "SYN-STUDY-A"),
            alias("SRP900001", "SYN-STUDY-A", alias_type="SRA_STUDY"),
            alias("gse-900001", "SYN-STUDY-A", alias_type="GEO_SERIES"),
            alias("GSE900077", "SYN-STUDY-B", certainty="PROBABLE"),
            alias("GSE900002", "SYN-STUDY-B", certainty="DISPROVED"),
        ],
        publications=[
            publication("SYN-PUB-001", "SYN-STUDY-A", "SYN-FAM-A", "PRIMARY_CLINICAL", pmid="900001"),
            publication("SYN-PUB-002", "SYN-STUDY-A", "SYN-FAM-A", "FOLLOWUP"),
            publication("SYN-PUB-003", "SYN-STUDY-B", "SYN-FAM-B", "REANALYSIS", independence_claim="UNRESOLVED", **reuse()),
        ],
        superseries=[superseries()],
        overlap_flags=[{
            "flag_id": "SYN-FLAG-0001",
            "flag_kind": "SUSPECTED_PATIENT_OVERLAP",
            "study_ids": ["SYN-STUDY-A", "SYN-STUDY-B"],
            "certainty": "POSSIBLE",
            "description": "SYNTHETIC suspected shared patients, flagged only.",
            "source_locator": dict(SYNTHETIC_LOCATOR),
        }],
    )


def rows_by_value(result):
    return {row["alias_value"]: row for row in result["alias_rows"]}


# ------------------------------------------------ input gate and no-decision


def test_invalid_candidate_packet_is_rejected_with_its_cause():
    packet = make_packet()
    packet["verified_facts"] = []
    packet["packet_id"] = candidate_packet_id({k: v for k, v in packet.items() if k != "packet_id"})
    with pytest.raises(ResolutionError) as error:
        build(packets=[packet], decision=make_decision([make_packet()]))
    assert error.value.code == "CANDIDATE_PACKET_REJECTED"
    assert error.value.cause_code == "FACT_LOCATOR_REQUIRED"


def test_packet_with_no_decision_creates_nothing():
    result = resolve([make_packet()], None, VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    assert result["study_records"] == []
    assert result["publication_records"] == []
    assert result["alias_rows"] == []
    assert result["overlap_flags"] == []
    assert result["receipt"]["decision_present"] is False
    assert result["receipt"]["admitted_count"] == 0


def test_decision_referencing_an_unvalidated_packet_is_rejected():
    decision = make_decision([make_packet()])
    decision["packet_ids"] = ["0" * 64]
    assert_code("DECISION_PACKET_UNKNOWN", lambda: resolve([make_packet()], decision, VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA))


@pytest.mark.parametrize("field,value,code", [
    ("reviewer", "", "MISSING_REVIEWER"),
    ("reviewer", "   ", "MISSING_REVIEWER"),
    ("decided_utc", "2026-10-17", "INVALID_UTC_TIMESTAMP"),
    ("decided_utc", "2026-10-17T10:00:00+01:00", "INVALID_UTC_TIMESTAMP"),
])
def test_decision_needs_reviewer_and_utc_timestamp(field, value, code):
    assert_code(code, lambda: build(**{field: value}))


def test_decision_with_unknown_top_level_key_is_malformed():
    assert_code("MALFORMED_DECISION", lambda: build(surprise_field="x"))


def test_decision_must_be_an_object_and_packets_a_list():
    assert_code("MALFORMED_DECISION", lambda: resolve([make_packet()], ["not", "object"], VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA))
    assert_code("MALFORMED_DECISION", lambda: resolve("packets", make_decision(), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA))


def test_duplicate_packet_ids_are_rejected():
    packet = make_packet()
    assert_code("DUPLICATE_PACKET_ID", lambda: build(packets=[packet, copy.deepcopy(packet)]))


# -------------------------------------------- same study, GEO and SRA aliases


def test_same_study_under_geo_and_sra_is_one_canonical_study():
    result = build(aliases=[
        alias("GSE900001", "SYN-STUDY-A"),
        alias("SRP900001", "SYN-STUDY-A", alias_type="SRA_STUDY"),
    ])
    assert [row["study_id"] for row in result["study_records"]] == ["SYN-STUDY-A"]
    statuses = {row["alias_value"]: row["status"] for row in result["alias_rows"]}
    assert statuses == {"GSE900001": "MERGED_VERIFIED", "SRP900001": "MERGED_VERIFIED"}
    assert result["receipt"]["merged_alias_count"] == 2


# ------------------------------------------------------- multiple publications


def test_multiple_publications_share_one_study_and_stay_independence_unresolved():
    result = build(
        studies=[study()],
        publications=[
            publication("SYN-PUB-001", role="PRIMARY_CLINICAL", pmid="900001"),
            publication("SYN-PUB-002", role="FOLLOWUP"),
        ],
    )
    assert len(result["study_records"]) == 1
    assert len(result["publication_records"]) == 2
    assert {row["independence_status"] for row in result["publication_records"]} == {"UNRESOLVED"}
    study_record = result["study_records"][0]
    assert study_record["primary_publication"] == "SYN-PUB-001"
    assert study_record["secondary_publications"] == ["SYN-PUB-002"]


def test_different_titles_never_imply_independence():
    # Publication records carry no title input at all; independence is never derived from text.
    result = build(publications=[
        publication("SYN-PUB-001", role="PRIMARY_CLINICAL", notes="SYNTHETIC title one"),
        publication("SYN-PUB-002", role="FOLLOWUP", notes="SYNTHETIC title two entirely different"),
    ])
    assert {row["independence_status"] for row in result["publication_records"]} == {"UNRESOLVED"}


def test_primary_publication_must_be_unique_per_study():
    assert_code("MALFORMED_DECISION", lambda: build(publications=[
        publication("SYN-PUB-001", role="PRIMARY_CLINICAL"),
        publication("SYN-PUB-002", role="PRIMARY_CLINICAL"),
    ]))


def test_publication_family_must_match_its_study():
    assert_code("FAMILY_MISMATCH", lambda: build(publications=[publication("SYN-PUB-001", family="SYN-FAM-OTHER")]))


# ------------------------------------------------------ SuperSeries / SubSeries


def test_verified_superseries_maps_subseries_to_one_study_at_series_level_only():
    result = build(superseries=[superseries()])
    rows = rows_by_value(result)
    assert rows["GSE900045"]["status"] == "MERGED_VERIFIED"
    assert rows["GSE900044"]["status"] == "MERGED_VERIFIED"
    assert rows["GSE900044"]["alias_type"] == "GEO_SUBSERIES"
    assert rows["SRP900044"]["alias_type"] == "SRA_STUDY"
    assert len(result["study_records"]) == 1
    for row in result["alias_rows"]:
        assert row["canonical_study_id"] == "SYN-STUDY-A"
    subseries_note = rows["GSE900044"]["notes"]
    assert "series_modality=RNA" in subseries_note
    assert "scope=SERIES_LEVEL_ONLY" in subseries_note
    assert "patient_specimen_timepoint_intersection=NOT_CLAIMED" in subseries_note


def test_unverified_superseries_stays_unresolved_and_never_merges():
    result = build(superseries=[superseries(certainty="PROBABLE", origin="SYN-STUDY-A")])
    rows = rows_by_value(result)
    assert rows["GSE900045"]["status"] == "FLAGGED_NOT_MERGED"
    assert result["receipt"]["merged_alias_count"] == 0
    unknown = build(superseries=[superseries(certainty="UNRESOLVED", origin="UNKNOWN")])
    assert rows_by_value(unknown)["GSE900045"]["status"] == "FLAGGED_UNRESOLVED"
    assert rows_by_value(unknown)["GSE900045"]["canonical_study_id"] == "UNKNOWN"


def test_superseries_subseries_alias_conflict_is_fail_closed():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("GSE900044", "SYN-STUDY-B")],
        superseries=[superseries()],
    ))


def test_verified_superseries_with_unknown_origin_is_unresolved_originating_study():
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(superseries=[superseries(origin="UNKNOWN", certainty="VERIFIED")]))


def test_subseries_cannot_be_more_certain_than_its_superseries():
    # Subseries rows are VERIFIED in their own records, but the parent SuperSeries is only PROBABLE.
    result = build(superseries=[superseries(origin="SYN-STUDY-A", certainty="PROBABLE")])
    rows = rows_by_value(result)
    assert rows["GSE900044"]["status"] == "FLAGGED_NOT_MERGED"
    assert rows["GSE900043"]["status"] == "FLAGGED_NOT_MERGED"
    assert result["receipt"]["merged_alias_count"] == 0


def test_superseries_alias_type_cannot_bypass_the_superseries_block():
    assert_code("MALFORMED_DECISION", lambda: build(aliases=[alias("GSE900045", "SYN-STUDY-A", alias_type="GEO_SUPERSERIES")]))


def test_subseries_with_unknown_modality_is_rejected():
    bad = superseries(subseries=[{"accession": "GSE900044", "modality": "PATIENT_LEVEL", "sra_study": None,
                                  "certainty": "VERIFIED", "evidence_type": "REPOSITORY_LINK",
                                  "source_locator": dict(SYNTHETIC_LOCATOR),
                                  "modality_locator": dict(SYNTHETIC_LOCATOR), "sra_locator": None}])
    assert_code("INVALID_ENUM", lambda: build(superseries=[bad]))


# ------------------------------------------------------- reanalysis and reuse


def test_reanalysis_mirror_is_not_independent_and_creates_no_study():
    result = build(
        studies=[study()],
        publications=[publication("SYN-PUB-R", role="REANALYSIS", **reuse())],
    )
    assert len(result["study_records"]) == 1
    assert result["publication_records"][0]["independence_status"] == "NOT_INDEPENDENT"


def test_atlas_reuse_is_forced_not_independent_even_when_decision_says_unresolved():
    result = build(publications=[publication("SYN-PUB-A", role="ATLAS_REUSE", independence_claim="UNRESOLVED", **reuse())])
    assert result["publication_records"][0]["independence_status"] == "NOT_INDEPENDENT"


def test_reuse_claim_with_unknown_subset_raises_publication_subset_unknown():
    assert_code("PUBLICATION_SUBSET_UNKNOWN", lambda: build(
        publications=[publication("SYN-PUB-R", role="REANALYSIS", **reuse(patient_subset="UNKNOWN"))]))


@pytest.mark.parametrize("field", ["patient_subset", "assay_subset", "treatment_subset", "outcome_subset"])
def test_reuse_claim_with_null_subset_is_also_unknown(field):
    assert_code("PUBLICATION_SUBSET_UNKNOWN", lambda: build(
        publications=[publication("SYN-PUB-R", role="REANALYSIS", **reuse(**{field: None}))]))


def test_data_reuse_declared_as_unknown_still_requires_known_subsets():
    assert_code("PUBLICATION_SUBSET_UNKNOWN", lambda: build(
        publications=[publication("SYN-PUB-R", role="OTHER", **reuse(data_reused="UNKNOWN", patient_subset="UNKNOWN"))]))


def test_independent_recruitment_upgrade_is_refused():
    assert_code("INDEPENDENCE_UPGRADE_NOT_PERMITTED", lambda: build(
        publications=[publication("SYN-PUB-I", role="PRIMARY_CLINICAL", independence_claim="INDEPENDENT_RECRUITMENT")]))


def test_unknown_independence_claim_is_an_invalid_enum():
    assert_code("INVALID_ENUM", lambda: build(publications=[publication("SYN-PUB-I", independence_claim="MAYBE")]))


def test_independence_defaults_to_unresolved_when_not_supplied():
    row = publication("SYN-PUB-D")
    del row["independence_claim"]
    result = build(publications=[row])
    assert result["publication_records"][0]["independence_status"] == "UNRESOLVED"


# ------------------------------------------------ suspected overlap (DAV-T08)


def test_suspected_patient_overlap_is_flagged_not_merged_and_emits_no_edges():
    flags = [{
        "flag_id": "SYN-FLAG-0001",
        "flag_kind": "SUSPECTED_PATIENT_OVERLAP",
        "study_ids": ["SYN-STUDY-A", "SYN-STUDY-B"],
        "certainty": "POSSIBLE",
        "description": "SYNTHETIC suspected shared patients, flagged only.",
        "source_locator": dict(SYNTHETIC_LOCATOR),
    }]
    result = build(studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")], overlap_flags=flags)
    assert [row["study_id"] for row in result["study_records"]] == ["SYN-STUDY-A", "SYN-STUDY-B"]
    assert result["alias_rows"] == []
    assert [flag["flag_id"] for flag in result["overlap_flags"]] == ["SYN-FLAG-0001"]
    assert all(flag["dav_t08_handoff"] is True for flag in result["overlap_flags"])
    assert result["receipt"]["overlap_edges_emitted"] == 0
    assert result["receipt"]["overlap_flag_ids"] == ["SYN-FLAG-0001"]


def test_overlap_flag_must_reference_known_studies():
    flags = [{"flag_id": "SYN-FLAG-0002", "flag_kind": "SUSPECTED_PATIENT_OVERLAP", "study_ids": ["SYN-STUDY-A", "SYN-MISSING"],
              "certainty": "POSSIBLE", "description": "SYNTHETIC.", "source_locator": dict(SYNTHETIC_LOCATOR)}]
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(overlap_flags=flags))


# ---------------------------------------------- punctuation and case collisions


def test_punctuation_and_case_variants_of_one_target_merge_and_keep_raw_bytes():
    result = build(aliases=[
        alias("GSE900001", "SYN-STUDY-A"),
        alias("gse-900001", "SYN-STUDY-A"),
        alias(" GSE900001.", "SYN-STUDY-A", evidence_type="PUBLICATION_STATEMENT"),
    ])
    raw = sorted(row["alias_value"] for row in result["alias_rows"])
    assert raw == sorted(["GSE900001", "gse-900001", " GSE900001."])
    assert len({row["alias_id"] for row in result["alias_rows"]}) == 3
    assert all(row["status"] == "MERGED_VERIFIED" for row in result["alias_rows"])


def test_punctuation_or_case_collision_with_different_targets_is_a_conflict():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("GSE900001", "SYN-STUDY-A"), alias("gse-900001", "SYN-STUDY-B", certainty="PROBABLE")],
    ))


def test_same_alias_under_two_alias_types_with_different_targets_is_a_conflict():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("900001", "SYN-STUDY-A", alias_type="TRIAL_ID"),
                 alias("900001", "SYN-STUDY-B", alias_type="CATALOGUE_LABEL")],
    ))


def test_disproved_alias_does_not_participate_in_conflict_detection():
    result = build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("GSE900001", "SYN-STUDY-B"), alias("GSE900001", "SYN-STUDY-A", certainty="DISPROVED")],
    )
    statuses = sorted(row["status"] for row in result["alias_rows"])
    assert statuses == ["DISTINCT_DISPROVED", "MERGED_VERIFIED"]


def test_identical_alias_rows_are_duplicates():
    assert_code("DUPLICATE_ALIAS", lambda: build(aliases=[alias("GSE900001", "SYN-STUDY-A"), alias("GSE900001", "SYN-STUDY-A")]))


# ------------------------------------------------------------ frozen failure codes


def test_publication_for_unknown_study_raises_unresolved_originating_study():
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(publications=[publication("SYN-PUB-X", study_id="SYN-MISSING")]))


def test_verified_alias_with_unknown_origin_raises_unresolved_originating_study():
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(aliases=[alias("GSE900001", "UNKNOWN")]))


def test_verified_alias_to_absent_study_raises_unresolved_originating_study():
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(aliases=[alias("GSE900001", "SYN-MISSING")]))


def test_unresolved_alias_claiming_a_study_raises_unresolved_originating_study():
    assert_code("UNRESOLVED_ORIGINATING_STUDY", lambda: build(aliases=[alias("GSE900001", "SYN-STUDY-A", certainty="UNRESOLVED")]))


def test_unresolved_alias_with_unknown_origin_is_flagged_and_unmerged():
    result = build(aliases=[alias("GSE900001", "UNKNOWN", certainty="UNRESOLVED")])
    row = result["alias_rows"][0]
    assert row["status"] == "FLAGGED_UNRESOLVED"
    assert row["canonical_study_id"] == "UNKNOWN"


# --------------------------------------------------------- certainty and merging


@pytest.mark.parametrize("certainty", ["PROBABLE", "POSSIBLE"])
def test_probable_and_possible_never_merge(certainty):
    result = build(aliases=[alias("GSE900001", "SYN-STUDY-A", certainty=certainty)])
    assert result["alias_rows"][0]["status"] == "FLAGGED_NOT_MERGED"
    assert result["receipt"]["merged_alias_count"] == 0
    assert len(result["study_records"]) == 1


def test_disproved_alias_keeps_entities_distinct():
    result = build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("SRP900002", "SYN-STUDY-B", alias_type="SRA_STUDY"),
                 alias("GSE900002", "SYN-STUDY-A", certainty="DISPROVED")],
    )
    rows = rows_by_value(result)
    assert rows["GSE900002"]["status"] == "DISTINCT_DISPROVED"
    assert rows["SRP900002"]["status"] == "MERGED_VERIFIED"
    assert [row["study_id"] for row in result["study_records"]] == ["SYN-STUDY-A", "SYN-STUDY-B"]


def test_only_verified_certainty_produces_a_merge():
    for certainty in sr.CERTAINTY_LEVELS:
        target = "UNKNOWN" if certainty == "UNRESOLVED" else "SYN-STUDY-A"
        result = build(aliases=[alias("GSE900001", target, certainty=certainty)])
        merged = result["receipt"]["merged_alias_count"]
        assert merged == (1 if certainty == "VERIFIED" else 0), certainty


def test_certainty_outside_the_frozen_scale_is_rejected():
    assert_code("INVALID_ENUM", lambda: build(aliases=[alias("GSE900001", "SYN-STUDY-A", certainty="LIKELY")]))


# ----------------------------------------------------------------- status ceiling


@pytest.mark.parametrize("status", ["RESOLVED", "ADMITTED", "READY"])
def test_code_never_emits_resolved_and_decision_cannot_set_it(status):
    assert_code("STATUS_CEILING" if status == "RESOLVED" else "INVALID_ENUM",
                lambda: build(studies=[study(study_status=status)]))


def test_excluded_or_superseded_without_reason_is_refused():
    for status in ("EXCLUDED", "SUPERSEDED"):
        assert_code("STATUS_CEILING", lambda: build(studies=[study(study_status=status)]))


def test_excluded_with_reason_and_reviewer_is_emitted_from_decision_only():
    result = build(studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC out of scope")])
    assert result["study_records"][0]["study_status"] == "EXCLUDED"
    assert "status_reason: SYNTHETIC out of scope" in result["study_records"][0]["notes"]


def test_default_status_is_candidate_or_resolving_never_resolved():
    rich = rich_decision([make_packet()])
    result = resolve([make_packet()], rich, VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    statuses = {row["study_status"] for row in result["study_records"]}
    assert statuses <= {"CANDIDATE", "RESOLVING"}
    assert "RESOLVED" not in statuses
    plain = build()
    assert plain["study_records"][0]["study_status"] in {"CANDIDATE", "RESOLVING"}


# ----------------------------------------------------------------- closed enums


@pytest.mark.parametrize("kwargs,code", [
    ({"alias_type": "GEO_FOO"}, "INVALID_ENUM"),
    ({"evidence_type": "GUESS"}, "INVALID_ENUM"),
    ({"certainty": "LIKELY"}, "INVALID_ENUM"),
])
def test_out_of_enum_alias_or_evidence_values_fail_closed(kwargs, code):
    assert_code(code, lambda: build(aliases=[alias("GSE900001", "SYN-STUDY-A", **kwargs)]))


def test_out_of_enum_study_class_and_publication_role_fail_closed():
    assert_code("INVALID_ENUM", lambda: build(studies=[study(study_class="ASSAY_ONLY")]))
    assert_code("INVALID_ENUM", lambda: build(publications=[publication("SYN-PUB-X", role="ABSTRACT")]))


def test_declared_enums_match_frozen_schema_enums():
    study_props = STUDY_SCHEMA["properties"]
    pub_props = PUBLICATION_SCHEMA["properties"]
    assert list(sr.STUDY_CLASSES) == study_props["study_class"]["enum"]
    assert list(sr.STUDY_STATUSES) == study_props["study_status"]["enum"]
    assert list(sr.PUBLICATION_ROLES) == pub_props["publication_role"]["enum"]
    assert set(sr.INDEPENDENCE_EMITTABLE) <= set(pub_props["independence_status"]["enum"])


def test_declared_enums_are_closed_and_documented_in_the_receipt():
    result = build()
    enums = result["receipt"]["enums"]
    assert enums["alias_type"] == list(sr.ALIAS_TYPES)
    assert enums["evidence_type"] == list(sr.EVIDENCE_TYPES)
    assert enums["certainty"] == list(sr.CERTAINTY_LEVELS)
    assert enums["alias_status"] == list(sr.ALIAS_STATUSES)
    assert "CANDIDATE" in enums["study_status_emittable"]
    assert "RESOLVED" not in enums["study_status_emittable"]


# ------------------------------------------------------------ contract tests


def test_every_emitted_record_validates_against_the_frozen_schemas():
    result = resolve([make_packet()], rich_decision([make_packet()]), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    study_validator = Draft202012Validator(STUDY_SCHEMA)
    publication_validator = Draft202012Validator(PUBLICATION_SCHEMA)
    assert result["study_records"] and result["publication_records"]
    for record in result["study_records"]:
        assert list(study_validator.iter_errors(record)) == []
    for record in result["publication_records"]:
        assert list(publication_validator.iter_errors(record)) == []


def test_schema_failure_is_reported_as_schema_invalid():
    stricter = copy.deepcopy(STUDY_SCHEMA)
    stricter["required"] = stricter["required"] + ["zzz_required_field"]
    assert_code("SCHEMA_INVALID", lambda: build(schemas=(stricter, PUBLICATION_SCHEMA)))


def test_schema_version_comes_from_the_frozen_schema_default():
    result = build()
    assert result["study_records"][0]["schema_version"] == STUDY_SCHEMA["properties"]["schema_version"]["default"]
    assert result["receipt"]["schema_versions"]["study_registry"] == "1.0.0"
    assert result["receipt"]["schema_versions"]["publication_family"] == "1.0.0"


def test_tsv_headers_are_exactly_the_frozen_template_headers():
    assert list(sr.STUDY_HEADER) == _template_header("study_registry.tsv")
    assert list(sr.PUBLICATION_HEADER) == _template_header("publication_family_registry.tsv")
    assert list(sr.ALIAS_HEADER) == _template_header("study_alias_crosswalk.tsv")
    result = resolve([make_packet()], rich_decision([make_packet()]), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    assert render_study_tsv(result["study_records"]).splitlines()[0].split("\t") == _template_header("study_registry.tsv")
    assert render_publication_tsv(result["publication_records"]).splitlines()[0].split("\t") == _template_header("publication_family_registry.tsv")
    assert render_alias_tsv(result["alias_rows"]).splitlines()[0].split("\t") == _template_header("study_alias_crosswalk.tsv")


def test_no_duplicate_canonical_study_ids():
    assert_code("DUPLICATE_STUDY_ID", lambda: build(studies=[study("SYN-STUDY-A"), study("SYN-STUDY-A")]))
    result = resolve([make_packet()], rich_decision([make_packet()]), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    ids = [row["study_id"] for row in result["study_records"]]
    assert len(ids) == len(set(ids))


def test_duplicate_publication_ids_are_rejected():
    assert_code("DUPLICATE_PUBLICATION_ID", lambda: build(publications=[publication("SYN-PUB-1"), publication("SYN-PUB-1")]))


def test_no_empty_cells_in_any_rendered_table():
    result = resolve([make_packet()], rich_decision([make_packet()]), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    tables = {
        "study": (render_study_tsv(result["study_records"]), sr.STUDY_HEADER),
        "publication": (render_publication_tsv(result["publication_records"]), sr.PUBLICATION_HEADER),
        "alias": (render_alias_tsv(result["alias_rows"]), sr.ALIAS_HEADER),
    }
    for name, (text, header) in tables.items():
        lines = text.split("\n")
        assert lines[-1] == "", name
        for line in lines[:-1]:
            cells = line.split("\t")
            assert len(cells) == len(header), name
            assert all(cell != "" for cell in cells), name


def test_renderer_rejects_an_empty_text_cell_directly():
    record = copy.deepcopy(build()["study_records"][0])
    record["study_title"] = ""
    assert_code("EMPTY_CELL", lambda: render_study_tsv([record]))


def test_empty_text_field_in_decision_is_malformed_not_silently_rendered():
    assert_code("MALFORMED_DECISION", lambda: build(studies=[study(study_title="")]))






# ---------------------------------------------------------- null tokens


def test_null_and_unknown_tokens_render_as_declared():
    result = build(studies=[study(cancer_subtype=None, disease_state="UNKNOWN", country_centre="NULL")])
    text = render_study_tsv(result["study_records"])
    header = text.splitlines()[0].split("\t")
    cells = dict(zip(header, text.splitlines()[1].split("\t")))
    assert cells["cancer_subtype"] == "NULL"
    assert cells["disease_state"] == "UNKNOWN"
    assert cells["country_centre"] == "NULL"


def test_null_token_is_refused_in_a_non_nullable_text_field():
    assert_code("MALFORMED_DECISION", lambda: build(studies=[study(study_title="NULL")]))


def test_empty_list_renders_as_null_token():
    result = build(studies=[study(source_repositories=[])])
    text = render_study_tsv(result["study_records"])
    header = text.splitlines()[0].split("\t")
    cells = dict(zip(header, text.splitlines()[1].split("\t")))
    assert cells["source_repositories"] == "NULL"


def test_receipt_declares_both_null_tokens():
    receipt = build()["receipt"]
    assert receipt["null_tokens"]["NULL"]
    assert receipt["null_tokens"]["UNKNOWN"]
    assert sr.NULL_TOKEN == "NULL" and sr.UNKNOWN_TOKEN == "UNKNOWN"


# ------------------------------------------------------------ security


@pytest.mark.parametrize("url", [
    "https://example.org/SYNTHETIC/record?api_key=SYNTHETIC123",
    "https://user:pass@example.org/SYNTHETIC/record",
])
def test_secret_bearing_locator_is_rejected_through_imported_scanners(url):
    # The accepted text scanners run over the whole decision before locator format checks.
    locator = dict(SYNTHETIC_LOCATOR, value=url)
    assert_code("SECRET_LOCATOR", lambda: build(studies=[study(source_locators=[locator])]))


def test_secret_bearing_text_is_rejected_through_imported_scanners():
    assert_code("SECRET_LOCATOR", lambda: build(studies=[study(notes="Bearer abcdefghijklmnopqrstuvwx")]))


def test_secret_bearing_key_is_rejected_through_imported_scanners():
    assert_code("SECRET_LOCATOR", lambda: build(studies=[study(api_key="SYNTHETIC")]))


def test_secret_text_in_alias_value_is_rejected():
    assert_code("SECRET_LOCATOR", lambda: build(aliases=[alias("token=SYNTHETICSECRET123456", "SYN-STUDY-A")]))


def test_secret_text_in_a_candidate_packet_rejects_the_packet():
    packet = make_packet(label="api_key=SYNTHETIC123456789")
    with pytest.raises(ResolutionError) as error:
        build(packets=[packet], decision=make_decision([make_packet()]))
    assert error.value.code == "CANDIDATE_PACKET_REJECTED"
    assert error.value.cause_code == "SECRET_LOCATOR"


def test_control_characters_in_alias_values_are_malformed():
    assert_code("MALFORMED_ALIAS", lambda: build(aliases=[alias("GSE\t900001", "SYN-STUDY-A")]))


def test_list_items_containing_the_separator_are_malformed():
    assert_code("MALFORMED_DECISION", lambda: build(studies=[study(source_repositories=["A;B"])]))


# ------------------------------------------------------ determinism


def _reverse_keys(value):
    if isinstance(value, dict):
        return {k: _reverse_keys(value[k]) for k in reversed(list(value))}
    if isinstance(value, list):
        return [_reverse_keys(item) for item in value]
    return value


def _digest(result):
    payload = json.dumps({
        "study": render_study_tsv(result["study_records"]),
        "publication": render_publication_tsv(result["publication_records"]),
        "alias": render_alias_tsv(result["alias_rows"]),
        "receipt": result["receipt"],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_row_and_key_permutations_give_byte_identical_tables_and_ids():
    packets = [make_packet(), make_packet(query_ids=("SYN-QUERY-0001",), label="second synthetic packet")]
    decision = rich_decision(packets)
    base = resolve(packets, decision, VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    rng = random.Random(20261017)
    for _ in range(5):
        shuffled_packets = list(packets)
        rng.shuffle(shuffled_packets)
        shuffled = copy.deepcopy(decision)
        for key in ("studies", "aliases", "publications", "superseries", "overlap_flags", "packet_ids"):
            rng.shuffle(shuffled[key])
        shuffled["aliases"] = list(reversed(shuffled["aliases"]))
        permuted = resolve(shuffled_packets, _reverse_keys(shuffled), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
        assert render_study_tsv(permuted["study_records"]) == render_study_tsv(base["study_records"])
        assert render_publication_tsv(permuted["publication_records"]) == render_publication_tsv(base["publication_records"])
        assert render_alias_tsv(permuted["alias_rows"]) == render_alias_tsv(base["alias_rows"])
        assert [r["alias_id"] for r in permuted["alias_rows"]] == [r["alias_id"] for r in base["alias_rows"]]
        assert _digest(permuted) == _digest(base)


def test_alias_ids_are_content_derived_and_stable():
    first = build(aliases=[alias("GSE900001", "SYN-STUDY-A")])["alias_rows"][0]["alias_id"]
    second = build(aliases=[alias("GSE900001", "SYN-STUDY-A")])["alias_rows"][0]["alias_id"]
    third = build(aliases=[alias("GSE900001", "SYN-STUDY-A", notes="changed")])["alias_rows"][0]["alias_id"]
    assert first == second
    assert first != third
    assert re.fullmatch(r"ALIAS-[0-9a-f]{16}", first)


# ------------------------------------------------------------- receipt


def test_receipt_status_counts_and_hashes_match_rendered_tables():
    packets = [make_packet()]
    result = resolve(packets, rich_decision(packets), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    receipt = result["receipt"]
    assert receipt["status"] == "PROPOSED_NOT_RESOLVED"
    assert receipt["admitted_count"] == 0
    assert receipt["analysis_readiness"] == "NOT_ANALYSIS_READY"
    assert receipt["decision_present"] is True
    assert receipt["overlap_edges_emitted"] == 0
    assert receipt["tsv_sha256"]["study_registry.tsv"] == hashlib.sha256(render_study_tsv(result["study_records"]).encode("utf-8")).hexdigest()
    assert receipt["tsv_sha256"]["study_alias_crosswalk.tsv"] == hashlib.sha256(render_alias_tsv(result["alias_rows"]).encode("utf-8")).hexdigest()
    assert receipt["study_count"] == len(result["study_records"])
    assert receipt["alias_count"] == len(result["alias_rows"])


def test_receipt_contains_no_raw_alias_values():
    result = build(aliases=[alias("GSE900001", "SYN-STUDY-A")])
    assert "GSE900001" not in json.dumps(result["receipt"])


def test_receipt_declares_the_decision_shape_version_and_provisional_flag():
    receipt = build(provisional=True)["receipt"]
    assert receipt["decision_schema_version"] == sr.DECISION_SCHEMA_VERSION
    assert receipt["provisional"] is True


def test_outputs_are_sorted_by_declared_stable_keys():
    result = resolve([make_packet()], rich_decision([make_packet()]), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    assert [r["study_id"] for r in result["study_records"]] == sorted(r["study_id"] for r in result["study_records"])
    pub_keys = [(r["study_id"], r["publication_id"]) for r in result["publication_records"]]
    assert pub_keys == sorted(pub_keys)
    alias_keys = [(r["canonical_study_id"], r["alias_type"], r["alias_value"], r["alias_id"]) for r in result["alias_rows"]]
    assert alias_keys == sorted(alias_keys)


# ------------------------------------------------- golden synthetic crosswalk


def test_synthetic_golden_crosswalk_matches_the_committed_fixture():
    packets = [make_packet()]
    result = resolve(packets, rich_decision(packets), VALID_QUERY_IDS, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    golden = (FIXTURES / "synthetic_alias_crosswalk.tsv").read_text(encoding="utf-8")
    assert render_alias_tsv(result["alias_rows"]) == golden


# ------------------------------------------------ public tracer (offline checks)

TRACER = FIXTURES / "tracer"
PRIVATE_TRACER = ROOT / ".scratch" / "runtime" / "A_DAV_03" / "tracer_private"
PROPOSED_DOC = ROOT / "docs" / "validation" / "A_DAV_03" / "TRACER_PROPOSED_RECORDS.json"
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _manifest():
    return json.loads((TRACER / "MANIFEST.json").read_text(encoding="utf-8"))


def _committed_json(name):
    return json.loads((TRACER / name).read_text(encoding="utf-8"))


def _entry(index):
    return next(entry for entry in _manifest()["requests"] if entry["request_index"] == index)


def _utc(value):
    from datetime import datetime
    return datetime.fromisoformat(value[:-1] + "+00:00")


def test_tracer_manifest_is_bounded_and_carries_no_credentials():
    manifest = _manifest()
    requests = manifest["requests"]
    assert manifest["request_count"] == len(requests) <= 25
    assert manifest["api_key"] == "not used"
    for entry in requests:
        assert entry["url"].startswith(NCBI_BASE)
        assert "api_key" not in entry["url"].lower()
        assert "email=" not in entry["url"].lower()
        assert "tool=a-dav-03-dav-t02-tracer" in entry["url"]
        assert entry["http_status"] == 200
        assert entry["curl_returncode"] == 0
        assert entry["url"].count("term=") <= 1


def test_tracer_requests_are_at_least_point_four_seconds_apart_and_utc_stamped():
    requests = _manifest()["requests"]
    stamps = [_utc(entry["utc"]) for entry in requests]
    assert stamps == sorted(stamps)
    for before, after in zip(stamps, stamps[1:]):
        assert (after - before).total_seconds() >= 0.4


def test_tracer_storage_is_declared_for_every_request_and_sample_bearing_files_are_private():
    requests = _manifest()["requests"]
    for entry in requests:
        assert entry["storage"] in {"COMMITTED", "PRIVATE_SCRATCH_NOT_COMMITTED"}
    private = {entry["file"] for entry in requests if entry["storage"] == "PRIVATE_SCRATCH_NOT_COMMITTED"}
    assert private == {"07_esummary_gds_GSE91061.json", "10_esummary_gds_GSE126045.json",
                       "13_esummary_gds_GSE126044.json", "16_esummary_gds_GSE126043.json"}


def test_committed_tracer_raw_bytes_match_recorded_size_and_sha256():
    for entry in _manifest()["requests"]:
        if entry["storage"] != "COMMITTED":
            continue
        raw = (TRACER / entry["file"]).read_bytes()
        assert len(raw) == entry["bytes"], entry["file"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["file"]


def test_private_tracer_raw_bytes_match_recorded_sha256_when_present_locally():
    checked = 0
    for entry in _manifest()["requests"]:
        if entry["storage"] != "PRIVATE_SCRATCH_NOT_COMMITTED":
            continue
        assert len(entry["sha256"]) == 64 and entry["bytes"] > 0
        path = PRIVATE_TRACER / entry["file"]
        if not path.exists():
            continue
        raw = path.read_bytes()
        assert len(raw) == entry["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        checked += 1
    if checked == 0:
        pytest.skip("private sample-bearing raw responses are not present in this checkout")


def test_committed_tracer_responses_have_the_expected_ncbi_structure():
    esearch = _committed_json("01_esearch_gds_GSE91061.json")["esearchresult"]
    assert esearch["idlist"][0] == "200091061"
    assert int(esearch["count"]) >= 1
    sra = _committed_json("05_esearch_sra_SRP094781.json")["esearchresult"]
    assert int(sra["count"]) == 109
    link = _committed_json("08_elink_gds_pubmed_GSE91061.json")["linksets"][0]
    assert link["ids"] == ["200091061"]
    assert link["linksetdbs"][0]["links"] == ["29033130"]
    pubs = _committed_json("19_esummary_pubmed_linked.json")["result"]
    assert sorted(pubs["uids"]) == ["29033130", "32879421"]
    assert pubs["29033130"]["source"] == "Cell"
    assert pubs["32879421"]["source"] == "Exp Mol Med"


def test_confirmed_tracer_relationships_are_read_from_the_saved_responses():
    cho_linked = _committed_json("11_elink_gds_pubmed_GSE126045.json")["linksets"][0]["linksetdbs"][0]["links"]
    assert cho_linked == ["32879421"]
    assert _committed_json("14_elink_gds_pubmed_GSE126044.json")["linksets"][0]["linksetdbs"][0]["links"] == ["32879421"]
    assert _committed_json("17_elink_gds_pubmed_GSE126043.json")["linksets"][0]["linksetdbs"][0]["links"] == ["32879421"]
    assert _committed_json("06_esearch_sra_SRP183455.json")["esearchresult"]["count"] == "16"
    extract = {record["accession"]: record for record in _committed_json("GDS_SERIES_METADATA_EXTRACT.json")["records"]}
    assert extract["GSE91061"]["extrelations"][0]["targetobject"] == "SRP094781"
    assert extract["GSE126044"]["extrelations"][0]["targetobject"] == "SRP183455"
    assert extract["GSE126043"]["extrelations"] == []
    assert extract["GSE126045"]["summary"] == "This SuperSeries is composed of the SubSeries listed below."
    assert extract["GSE126044"]["gdstype"] == "Expression profiling by high throughput sequencing"
    assert extract["GSE126043"]["gdstype"] == "Methylation profiling by array"


def test_superseries_membership_is_not_confirmed_by_a_direct_link():
    # The 'gds_gds' link returns only the record itself; the 'gds_gds_similar' link is a similarity
    # relation. Neither is a membership listing, so membership stays PROBABLE, not VERIFIED.
    linksets = _committed_json("20_elink_gds_gds_superseries_200126045.json")["linksets"][0]["linksetdbs"]
    by_name = {db["linkname"]: db["links"] for db in linksets}
    assert by_name["gds_gds"] == ["200126045"]
    assert "200126044" in by_name["gds_gds_similar"] and "200126043" in by_name["gds_gds_similar"]


def test_sample_level_listings_are_absent_from_committed_tracer_files_and_extract():
    for path in TRACER.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "GSM" not in text, path.name
        assert '"samples": [' not in text, path.name
    extract = _committed_json("GDS_SERIES_METADATA_EXTRACT.json")
    assert "samples" in extract["fields_excluded"]
    for record in extract["records"]:
        assert set(record) <= {"source_request_index", "source_file", "source_bytes", "source_sha256", "source_url",
                               "uid", "accession", "title", "entrytype", "gdstype", "taxon", "gpl", "n_samples",
                               "pdat", "bioproject", "pubmedids", "extrelations", "summary"}


def test_extract_source_hashes_point_at_the_manifest_entries():
    by_file = {entry["file"]: entry for entry in _manifest()["requests"]}
    for record in _committed_json("GDS_SERIES_METADATA_EXTRACT.json")["records"]:
        entry = by_file[record["source_file"]]
        assert record["source_sha256"] == entry["sha256"]
        assert record["source_bytes"] == entry["bytes"]
        assert record["source_url"] == entry["url"]
        assert entry["storage"] == "PRIVATE_SCRATCH_NOT_COMMITTED"






# -------------------------- coordinator findings round 1 (C-1 locators, C-2 clinical, C-3 guards)

CLINICAL_TREATMENT_FIELDS = (
    "trial_id", "country_centre", "cancer_type", "cancer_subtype", "disease_state", "study_design", "checkpoint_target", "drug",
    "drug_class", "monotherapy_or_combination", "treatment_sequence", "line_of_therapy",
    "prior_ici_policy", "biopsy_schedule", "response_assessment_system", "treatment_regimen_id",
)
SCRATCH_TRACER = ROOT / ".scratch" / "runtime" / "A_DAV_03"


def _tracer_document():
    return json.loads(PROPOSED_DOC.read_text(encoding="utf-8"))


def _manifest_entry_for_url(url):
    matches = [entry for entry in _manifest()["requests"] if entry["url"] == url]
    assert len(matches) == 1, url
    return matches[0]


def _tracer_text(entry):
    """Text of the cited response: the committed raw bytes, the private raw bytes if present locally,
    or otherwise the committed sample-free extract for that same request (hash-linked in the extract)."""
    if entry["storage"] == "COMMITTED":
        return (TRACER / entry["file"]).read_text(encoding="utf-8")
    private = PRIVATE_TRACER / entry["file"]
    if private.exists():
        return private.read_text(encoding="utf-8")
    matches = [record for record in _committed_json("GDS_SERIES_METADATA_EXTRACT.json")["records"]
               if record["source_file"] == entry["file"]]
    assert matches, entry["file"]
    return json.dumps(matches[0], sort_keys=True)


def _gds_uid(accession):
    return str(200000000 + int(accession[3:]))


def _id_present(token, text):
    if re.fullmatch(r"GSE\d+", token):
        return token in text or _gds_uid(token) in text
    return token in text


def _claim_ids(claim):
    found = set(re.findall(r"\bGSE\d+\b|\bSRP\d+\b", claim))
    found |= set(re.findall(r"(?<![\d.])\d{8}(?![\d])", claim))
    found |= set(re.findall(r"10\.\d{4,9}/\S+", claim))
    return found


def _assert_locator_cites(url, ids, label):
    entry = _manifest_entry_for_url(url)
    text = _tracer_text(entry)
    assert any(_id_present(token, text) for token in ids), (label, entry["file"], sorted(ids))






MODALITY_TERMS = {"RNA": "high throughput sequencing", "DNA_METHYLATION": "Methylation profiling"}


def test_every_tracer_decision_and_packet_locator_cites_a_response_containing_its_identifier():
    decision_path = SCRATCH_TRACER / "tracer_decision.json"
    packets_path = SCRATCH_TRACER / "tracer_packets.json"
    if not (decision_path.exists() and packets_path.exists()):
        pytest.skip("scratch tracer decision and packets are not present in this checkout")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    for row in decision["aliases"]:
        _assert_locator_cites(row["source_locator"]["value"], [row["alias_value"]]
                              + ([_gds_uid(row["alias_value"])] if row["alias_value"].startswith("GSE") else []),
                              row["alias_value"])
    for block in decision["superseries"]:
        _assert_locator_cites(block["source_locator"]["value"], [block["superseries_accession"]],
                              block["superseries_accession"])
        for sub in block["subseries"]:
            _assert_locator_cites(sub["source_locator"]["value"], [sub["accession"]], sub["accession"])
            # OSR-M01: the membership locator must not claim a PMID it does not contain.
            assert "PMID" not in (sub["source_locator"]["page_or_section"] or ""), sub["accession"]
            modality_text = _tracer_text(_manifest_entry_for_url(sub["modality_locator"]["value"]))
            assert _id_present(sub["accession"], modality_text), sub["accession"]
            assert MODALITY_TERMS[sub["modality"]] in modality_text, (sub["accession"], sub["modality"])
            if sub["sra_study"] in (None, "UNKNOWN"):
                assert sub["sra_locator"] is None or sub["sra_study"] == "UNKNOWN"
            if sub["sra_study"] not in (None, "UNKNOWN"):
                _assert_locator_cites(sub["sra_locator"]["value"], [sub["sra_study"]], sub["sra_study"])
            if sub["sra_study"] == "UNKNOWN":
                # OSR-M02: the claim is limited to "no SRA link observed in the inspected responses".
                linked_dbs = [db["dbto"] for linkset in json.loads(
                    (TRACER / _manifest_entry_for_url(sub["sra_locator"]["value"])["file"]).read_text(encoding="utf-8"))["linksets"]
                    for db in linkset.get("linksetdbs", [])]
                assert "sra" not in linked_dbs, sub["accession"]
    for packet in json.loads(packets_path.read_text(encoding="utf-8")):
        for fact in packet["verified_facts"]:
            entry = _manifest_entry_for_url(fact["source_locator"]["value"])
            text = _tracer_text(entry)
            for token in _claim_ids(fact["claim"]):
                assert _id_present(token, text), (fact["claim"], entry["file"], token)


# ------------------------------------ round 2 (H-1, M-1, M-2, L-1, OSR-M01/M02, OSR-L01)

ROUND2_LOCATOR_URL = "https://example.org/SYNTHETIC/record"


def _loc(accessed=None, page="synthetic section", value=ROUND2_LOCATOR_URL):
    return {"kind": "URL", "value": value, "page_or_section": page, "accessed_utc": accessed}


def repo_study(repos, study_id="SYN-STUDY-A", family="SYN-FAM-A", **overrides):
    return study(study_id, family, source_repositories=repos, **overrides)


# H-1 / OSR-H01: canonical identity invariant

def test_repository_backed_by_verified_aliases_of_the_matching_types_is_accepted():
    result = build(
        studies=[repo_study(["GEO:GSE900001", "SRA:SRP900001"])],
        aliases=[alias("GSE900001", "SYN-STUDY-A"), alias("SRP900001", "SYN-STUDY-A", alias_type="SRA_STUDY")],
    )
    assert result["study_records"][0]["source_repositories"] == ["GEO:GSE900001", "SRA:SRP900001"]


def test_repository_without_any_alias_row_is_rejected():
    assert_code("REPOSITORY_NOT_VERIFIED", lambda: build(studies=[repo_study(["GEO:GSE900001"])]))


@pytest.mark.parametrize("certainty", ["PROBABLE", "POSSIBLE", "UNRESOLVED"])
def test_repository_backed_only_by_a_non_verified_alias_is_rejected(certainty):
    target = "UNKNOWN" if certainty == "UNRESOLVED" else "SYN-STUDY-A"
    assert_code("REPOSITORY_NOT_VERIFIED", lambda: build(
        studies=[repo_study(["GEO:GSE900001"])], aliases=[alias("GSE900001", target, certainty=certainty)]))


def test_repository_prefix_must_match_the_alias_type():
    assert_code("REPOSITORY_NOT_VERIFIED", lambda: build(
        studies=[repo_study(["SRA:GSE900001"])], aliases=[alias("GSE900001", "SYN-STUDY-A")]))


@pytest.mark.parametrize("entry", ["XYZ:GSE900001", "GSE900001", "GEO:"])
def test_unknown_or_malformed_repository_prefix_fails_closed(entry):
    assert_code("UNKNOWN_REPOSITORY_PREFIX", lambda: build(
        studies=[repo_study([entry])], aliases=[alias("GSE900001", "SYN-STUDY-A")]))


def test_same_repository_accession_on_two_studies_is_refused_even_without_alias_rows():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=[
        repo_study(["GEO:GSE900001"]),
        repo_study(["GEO:GSE900001"], "SYN-STUDY-B", "SYN-FAM-B"),
    ]))


def test_same_trial_id_on_two_studies_is_refused_under_case_and_punctuation_variants():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=[
        study("SYN-STUDY-A", trial_id="NCT900001"),
        study("SYN-STUDY-B", "SYN-FAM-B", trial_id="nct-900001"),
    ]))


def test_unknown_trial_id_is_not_an_identity_and_does_not_collide():
    result = build(studies=[study("SYN-STUDY-A", trial_id="UNKNOWN"),
                            study("SYN-STUDY-B", "SYN-FAM-B", trial_id="UNKNOWN")])
    assert len(result["study_records"]) == 2


def test_same_publication_family_on_two_studies_is_refused_under_case_variants():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=[
        study("SYN-STUDY-A", "SYN-FAM-X"),
        study("SYN-STUDY-B", "syn-fam-x"),
    ]))


def test_same_pmid_on_two_studies_is_refused_even_under_different_publication_ids():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        publications=[publication("SYN-PUB-1", "SYN-STUDY-A", "SYN-FAM-A", pmid="900001"),
                      publication("SYN-PUB-2", "SYN-STUDY-B", "SYN-FAM-B", pmid="900001")],
    ))


def test_same_doi_on_two_studies_is_refused_under_case_variants():
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        publications=[publication("SYN-PUB-1", "SYN-STUDY-A", "SYN-FAM-A", doi="10.1000/syn.900001"),
                      publication("SYN-PUB-2", "SYN-STUDY-B", "SYN-FAM-B", doi="10.1000/SYN.900001")],
    ))


def test_same_pmid_on_two_publications_of_one_study_is_allowed():
    result = build(publications=[publication("SYN-PUB-1", pmid="900001"),
                                 publication("SYN-PUB-2", role="FOLLOWUP", pmid="900001")])
    assert len(result["publication_records"]) == 2


# M-1: total, deterministic locator order; exact duplicates refused

@pytest.mark.parametrize("first,second", [
    (_loc("2026-10-17T01:00:00Z"), _loc("2026-10-17T02:00:00Z")),
    (_loc(None), _loc("2026-10-17T02:00:00Z")),
])
def test_tied_locators_differing_only_in_accessed_utc_give_byte_identical_output_in_both_orders(first, second):
    forward = build(studies=[study(source_locators=[first, second])])
    reverse = build(studies=[study(source_locators=[second, first])])
    assert forward["study_records"] == reverse["study_records"]
    assert render_study_tsv(forward["study_records"]) == render_study_tsv(reverse["study_records"])
    assert forward["receipt"]["tsv_sha256"] == reverse["receipt"]["tsv_sha256"]


def test_exact_duplicate_locators_are_rejected():
    assert_code("DUPLICATE_LOCATOR", lambda: build(studies=[study(source_locators=[_loc(), _loc()])]))


# M-2: placeholder reviewers and provisional decisions

@pytest.mark.parametrize("reviewer", [
    "PENDING", " tbd ", "Todo", "N/A", "n / a", "NA", "None", "NULL", "Unknown", "PROVISIONAL",
    "Placeholder", "Reviewer", "XXX", "", "   ",
])
def test_placeholder_reviewers_are_rejected_whatever_the_case_or_spacing(reviewer):
    assert_code("MISSING_REVIEWER", lambda: build(reviewer=reviewer))


@pytest.mark.parametrize("status", ["EXCLUDED", "SUPERSEDED"])
def test_provisional_decision_cannot_emit_excluded_or_superseded(status):
    assert_code("STATUS_CEILING", lambda: build(provisional=True,
                                                studies=[study(study_status=status, status_reason="SYNTHETIC reason")]))


def test_provisional_decision_may_still_emit_candidate_or_resolving():
    result = build(provisional=True)
    assert result["study_records"][0]["study_status"] in {"CANDIDATE", "RESOLVING"}


# L-1: DISPROVED rule as implemented

@pytest.mark.parametrize("certainty", ["PROBABLE", "POSSIBLE"])
def test_non_disproved_target_on_the_same_key_and_study_conflicts_with_disproved(certainty):
    with pytest.raises(ResolutionError) as error:
        build(aliases=[alias("GSE900002", "SYN-STUDY-A", certainty=certainty),
                       alias("GSE900002", "SYN-STUDY-A", certainty="DISPROVED")])
    assert error.value.code == "ACCESSION_ALIAS_CONFLICT"
    assert "non-DISPROVED" in str(error.value)


# OSR-M01 / OSR-M02: per-field locators for SubSeries modality and SRA

def _sub_with(**overrides):
    value = {"accession": "GSE900044", "modality": "RNA", "sra_study": "SRP900044", "certainty": "VERIFIED",
             "evidence_type": "REPOSITORY_LINK", "source_locator": _loc(),
             "modality_locator": _loc(), "sra_locator": _loc()}
    value.update(overrides)
    return value


def test_each_subseries_must_carry_its_own_modality_locator():
    sub = _sub_with()
    del sub["modality_locator"]
    assert_code("MALFORMED_DECISION", lambda: build(superseries=[superseries(subseries=[sub])]))


def test_sra_locator_is_forbidden_for_null_and_required_for_a_named_or_unknown_sra():
    assert_code("MALFORMED_DECISION", lambda: build(superseries=[superseries(subseries=[_sub_with(sra_study=None)])]))
    assert_code("MALFORMED_DECISION", lambda: build(superseries=[superseries(subseries=[_sub_with(sra_study="UNKNOWN", sra_locator=None)])]))


def test_modality_source_is_carried_into_the_alias_row_notes():
    modality = _loc(value="https://example.org/SYNTHETIC/modality-record")
    result = build(superseries=[superseries(subseries=[_sub_with(modality_locator=modality)])])
    rows = rows_by_value(result)
    marker = "modality_source=https://example.org/SYNTHETIC/modality-record"
    assert marker in rows["GSE900044"]["notes"]
    assert marker in rows["SRP900044"]["notes"]


def test_unknown_sra_emits_no_alias_row_and_is_counted_in_the_receipt():
    result = build(superseries=[superseries(subseries=[_sub_with(sra_study="UNKNOWN")])])
    assert "SRP900044" not in {row["alias_value"] for row in result["alias_rows"]}
    assert result["receipt"]["subseries_sra_unknown_count"] == 1


# Docs: the repository list of the proposed Cho record is only the VERIFIED-backed SuperSeries






# ------------------- round 3 (H-1: one identity-ownership map; M-2: punctuated placeholders)

def _trial_field_forward():
    return ([study("SYN-STUDY-A", trial_id="NCT900001"), study("SYN-STUDY-B", "SYN-FAM-B")],
            [alias("nct-900001", "SYN-STUDY-B", alias_type="TRIAL_ID")])


def _trial_field_reverse():
    return ([study("SYN-STUDY-A", "SYN-FAM-A"), study("SYN-STUDY-B", "SYN-FAM-B", trial_id="NCT900001")],
            [alias("nct-900001", "SYN-STUDY-A", alias_type="TRIAL_ID")])


def _pmid_forward():
    return ([study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
            [publication("SYN-PUB-1", "SYN-STUDY-A", "SYN-FAM-A", pmid="900001")],
            [alias("900001", "SYN-STUDY-B", alias_type="PUBLICATION_PMID")])


def _pmid_reverse():
    return ([study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
            [publication("SYN-PUB-2", "SYN-STUDY-B", "SYN-FAM-B", pmid="900001")],
            [alias("900001", "SYN-STUDY-A", alias_type="PUBLICATION_PMID")])


def _doi_forward():
    return ([study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
            [publication("SYN-PUB-1", "SYN-STUDY-A", "SYN-FAM-A", doi="10.1000/synthetic")],
            [alias("10.1000/SYNTHETIC", "SYN-STUDY-B", alias_type="PUBLICATION_DOI")])


def _doi_reverse():
    return ([study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
            [publication("SYN-PUB-2", "SYN-STUDY-B", "SYN-FAM-B", doi="10.1000/synthetic")],
            [alias("10.1000/SYNTHETIC", "SYN-STUDY-A", alias_type="PUBLICATION_DOI")])


@pytest.mark.parametrize("case", [_trial_field_forward, _trial_field_reverse])
def test_trial_field_and_verified_trial_alias_on_different_studies_conflict_in_both_orders(case):
    studies, aliases = case()
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=studies, aliases=aliases))


@pytest.mark.parametrize("case", [_pmid_forward, _pmid_reverse])
def test_pmid_field_and_verified_pmid_alias_on_different_studies_conflict_in_both_orders(case):
    studies, publications_, aliases = case()
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=studies, publications=publications_, aliases=aliases))


@pytest.mark.parametrize("case", [_doi_forward, _doi_reverse])
def test_doi_field_and_verified_doi_alias_on_different_studies_conflict_in_both_orders(case):
    studies, publications_, aliases = case()
    assert_code("ACCESSION_ALIAS_CONFLICT", lambda: build(studies=studies, publications=publications_, aliases=aliases))


def test_disproved_trial_alias_for_study_b_is_not_a_conflict_with_study_a_field():
    result = build(
        studies=[study("SYN-STUDY-A", trial_id="NCT900001"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("nct-900001", "SYN-STUDY-B", certainty="DISPROVED", alias_type="TRIAL_ID")],
    )
    assert len(result["study_records"]) == 2
    assert rows_by_value(result)["nct-900001"]["status"] == "DISTINCT_DISPROVED"


def test_disproved_pmid_and_doi_aliases_for_study_b_are_not_conflicts_with_study_a_fields():
    result = build(
        studies=[study("SYN-STUDY-A"), study("SYN-STUDY-B", "SYN-FAM-B")],
        publications=[publication("SYN-PUB-1", "SYN-STUDY-A", "SYN-FAM-A", pmid="900001", doi="10.1000/synthetic")],
        aliases=[alias("900001", "SYN-STUDY-B", certainty="DISPROVED", alias_type="PUBLICATION_PMID"),
                 alias("10.1000/SYNTHETIC", "SYN-STUDY-B", certainty="DISPROVED", alias_type="PUBLICATION_DOI")],
    )
    assert len(result["study_records"]) == 2
    assert {row["status"] for row in result["alias_rows"]} == {"DISTINCT_DISPROVED"}


def test_unknown_target_alias_claims_no_ownership_and_does_not_conflict():
    result = build(
        studies=[study("SYN-STUDY-A", trial_id="NCT900001")],
        aliases=[alias("nct-900001", "UNKNOWN", certainty="UNRESOLVED", alias_type="TRIAL_ID")],
    )
    assert rows_by_value(result)["nct-900001"]["status"] == "FLAGGED_UNRESOLVED"


def test_non_identity_alias_type_claims_no_ownership_in_the_identity_map():
    result = build(
        studies=[study("SYN-STUDY-A", trial_id="NCT900001"), study("SYN-STUDY-B", "SYN-FAM-B")],
        aliases=[alias("nct-900001", "SYN-STUDY-B", alias_type="CATALOGUE_LABEL")],
    )
    assert len(result["study_records"]) == 2


@pytest.mark.parametrize("reviewer", ["T.B.D.", "PEN-DING", "N.A.", "N/A", "  t b d ", "Pending!", "-"])
def test_punctuated_placeholder_reviewers_cannot_authorize_decision_only_statuses(reviewer):
    assert_code("MISSING_REVIEWER", lambda: build(
        reviewer=reviewer, studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC reason")]))


@pytest.mark.parametrize("reviewer", ["T.B.D.", "PEN-DING", "...", "!!!", "-"])
def test_punctuated_placeholder_reviewers_are_refused_for_every_decision(reviewer):
    assert_code("MISSING_REVIEWER", lambda: build(reviewer=reviewer))


@pytest.mark.parametrize("reviewer", ["integrator-A.Smith", "A.Smith", "synthetic-integrator"])
def test_real_reviewer_strings_with_punctuation_still_authorize_decision_only_statuses(reviewer):
    result = build(reviewer=reviewer, studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC reason")])
    assert result["study_records"][0]["study_status"] == "EXCLUDED"
    assert result["receipt"]["reviewer"] == reviewer


# ------------- round 4 (M-3: Unicode-aware reviewer key; combining marks cannot bypass)

@pytest.mark.parametrize("reviewer", ["محمد", "张伟", "Αλέξανδρος"])
def test_non_latin_reviewer_names_authorize_decision_only_statuses(reviewer):
    result = build(reviewer=reviewer, studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC reason")])
    assert result["study_records"][0]["study_status"] == "EXCLUDED"
    assert result["receipt"]["reviewer"] == reviewer


@pytest.mark.parametrize("reviewer", [
    "ＴＢＤ", "ＰＥＮＤＩＮＧ",                   # fullwidth forms: NFKD folds them to ASCII
    "T́BD", "PEŃDING", "PÉNDING",  # combining marks, precomposed accents
    "Ñ.A.", "PEN​DING", "PEN­DING",  # combining tilde on a placeholder, zero-width, soft hyphen
])
def test_fullwidth_combining_and_invisible_variants_of_placeholders_are_rejected(reviewer):
    assert_code("MISSING_REVIEWER", lambda: build(
        reviewer=reviewer, studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC reason")]))
    assert_code("MISSING_REVIEWER", lambda: build(reviewer=reviewer))


@pytest.mark.parametrize("reviewer", [
    "—", "。", "؟", "،", "・・・", "́", "​", "  ", "-", "...", "!!!",
])
def test_punctuation_or_whitespace_only_reviewers_are_refused_in_any_script(reviewer):
    assert_code("MISSING_REVIEWER", lambda: build(reviewer=reviewer))


def test_all_existing_placeholder_rejections_still_hold_with_authorization_attempted():
    for reviewer in ["T.B.D.", "PEN-DING", "N.A.", "N/A", "  t b d ", "Pending!", "-",
                     "PENDING", "tbd", "todo", "NA", "None", "NULL", "Unknown", "PROVISIONAL",
                     "Placeholder", "Reviewer", "XXX", "", "   "]:
        assert_code("MISSING_REVIEWER", lambda: build(
            reviewer=reviewer, studies=[study(study_status="EXCLUDED", status_reason="SYNTHETIC reason")]))
