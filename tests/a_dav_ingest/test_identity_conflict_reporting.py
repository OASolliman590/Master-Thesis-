from __future__ import annotations

from typing import Any

from tools.a_dav.delimited import read_delimited_table
from tools.a_dav.ingest import build_canonical_records
from tools.a_dav.source_objects import SourceObject


def _source(role: str) -> SourceObject:
    raw = role.encode()
    import hashlib

    return SourceObject(hashlib.sha256(raw).hexdigest(), f"https://example.invalid/{role}",
                        "synthetic-v1", len(raw), "2026-10-26T00:00:00Z", raw)


def _field_map() -> dict[str, Any]:
    return {
        "cohort": "synthetic_identity_case",
        "branch_id": "A_BASELINE_BIO",
        "source_objects": {
            role: {"locator": f"https://example.invalid/{role}", "format": "DELIMITED_CSV",
                   "version": "synthetic-v1", "sha256": None}
            for role in ("geo_family_soft", "author_sample_table", "author_clinical_table")
        },
        "sample_identity": {"title_regex": r"^(Pt\d+)_(Pre|On)",
                            "patient_group": 1, "visit_group": 2},
        "geo": {"characteristics": {"visit": "visit (pre or on treatment)",
                                      "response": "response"}},
        "author_sample_table": {
            "sample_name_column": 3,
            "patient_column": 4,
            "bam_suffix": ".bam",
            "sample_name_rule": {"regex": r"\.(\d+)$", "replacement": r"-\1"},
            "sample_code_group": {"regex": r"^[^_]+_[^_]+_(.+)$", "capture_group": 1},
            "response_positions": {"bor": 9},
        },
        "author_clinical_table": {"patient_column": 0, "bor_column": "BOR",
                                  "cohort_column": "Cohort"},
        "treatment": {"prior_ipilimumab_by_cohort": {}},
        "labels": {"source_of_record_bor": {}, "geo_response": {}},
        "measurement_representations": {},
    }


def _sample(accession: str, title: str, visit: str) -> dict[str, Any]:
    return {"accession": accession, "geo_accession": accession, "title": title,
            "characteristics": [{"key": "visit (pre or on treatment)", "value": visit}],
            "relations": []}


def _sample_table(*rows: str) -> bytes:
    header = ",Sample,IDX,BamName,PatientID,PatientID.replicate,PreOn,PatientIDrep,PopCateg,BOR,Response,Response,USUBJID,Cohort\n"
    return (header + "".join(row + "\n" for row in rows)).encode()


def _records(soft: list[dict[str, Any]], sample_bytes: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    clinical_bytes = b"PatientID,BOR,Cohort\nPt100,PR,NIV3-NAIVE\n"
    parsed = {
        "geo_family_soft": soft,
        "author_sample_table": read_delimited_table(sample_bytes, delimiter=","),
        "author_clinical_table": read_delimited_table(clinical_bytes, delimiter=","),
    }
    sources = {role: _source(role) for role in parsed}
    items: list[dict[str, Any]] = []
    records = build_canonical_records(parsed, sources, _field_map(), items)
    return records, items


def test_conflicting_sample_code_candidate_is_reported_without_linking_or_losing_baseline() -> None:
    soft = [
        _sample("GSM0000001", "Pt100_Pre_BASE-1", "Pre"),
        _sample("GSM0000002", "Pt200_On_CODE-2", "On"),
    ]
    sample_bytes = _sample_table(
        ",BASE,1,Pt100_Pre_BASE-1.bam,Pt100,,,,,PR,PRCR,LB,SUB1,NIV3-NAIVE",
        ",CANDIDATE,2,Pt7_Pre_CODE.2.bam,Pt300,,,,,PD,PD,LB,SUB2,NIV3-NAIVE",
    )

    records, items = _records(soft, sample_bytes)

    conflicts = [item for item in items if item["category"] == "AUTHOR_SAMPLE_CODE_IDENTITY_CONFLICT"]
    assert len(conflicts) == 1
    assert conflicts[0]["status"] == "BLOCKED_UNKNOWN"
    assert conflicts[0]["context"] == {"candidate_count": 1, "conflicting_candidate_count": 1}
    assert {pointer["role"] for pointer in conflicts[0]["evidence_pointers"]} == {
        "geo_family_soft", "author_sample_table"}
    assert len(records["specimen_registry"]) == 1
    assert records["specimen_registry"][0]["timing_raw_text"] == "Pre"
    assert [patient["source_patient_id"] for patient in records["patient_registry"]] == ["Pt100"]


def test_unmatched_sample_without_code_candidate_stays_missing() -> None:
    records, items = _records([_sample("GSM0000003", "Pt200_On_NOMATCH-3", "On")],
                              _sample_table(",OTHER,1,Pt999_On_OTHER-1.bam,Pt999,,,,,PD,PD,LB,SUB9,NIV3-NAIVE"))

    assert [item["category"] for item in items] == ["AUTHOR_SAMPLE_ROW_MISSING", "ON_TREATMENT_WINDOW_UNRESOLVED"]
    assert records["specimen_registry"] == []
    assert records["patient_registry"] == []


def test_multiple_conflicting_candidates_remain_unresolved() -> None:
    soft = [_sample("GSM0000004", "Pt200_On_CODE-4", "On")]
    sample_bytes = _sample_table(
        ",CANDIDATE1,1,Pt7_Pre_CODE.4.bam,Pt300,,,,,PD,PD,LB,SUB2,NIV3-NAIVE",
        ",CANDIDATE2,2,Pt8_Pre_CODE.4.bam,Pt400,,,,,PD,PD,LB,SUB3,NIV3-NAIVE",
    )

    records, items = _records(soft, sample_bytes)

    conflict = next(item for item in items if item["category"] == "AUTHOR_SAMPLE_CODE_IDENTITY_CONFLICT")
    assert conflict["context"] == {"candidate_count": 2, "conflicting_candidate_count": 2}
    assert records["specimen_registry"] == []
    assert records["patient_registry"] == []
