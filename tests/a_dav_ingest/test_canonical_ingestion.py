from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path
from typing import Any

from tools.a_dav.core import ENTITY_TABLES, SchemaStore
from tools.a_dav.delimited import read_delimited_table
from tools.a_dav.ingest import build_canonical_records
import tools.a_dav.ingest as ingest_module
from tools.a_dav.ingest import run_ingest
from tools.a_dav.registries import build_registries
from tools.a_dav.source_objects import SourceObject


def _source(role: str, raw: bytes) -> SourceObject:
    return SourceObject(hashlib.sha256(raw).hexdigest(), f"https://example.invalid/{role}",
                        "invented-v1", len(raw), "2026-01-01T00:00:00Z", raw)


def test_clean_metadata_maps_to_schema_valid_canonical_entity_tables() -> None:
    soft = [{"accession": "GSM0000001", "geo_accession": "GSM0000001",
             "title": "Pt999_Pre_AA1-1", "characteristics": [
                 {"key": "visit (pre or on treatment)", "value": "Pre"},
                 {"key": "response", "value": "PRCR"},
                 {"key": "tissue", "value": "melanoma"}],
             "relations": [{"kind": "BioSample", "locator": "https://example.invalid/SAMN1"},
                           {"kind": "SRA", "locator": "https://example.invalid/SRX1"}]}]
    sample_csv = (",Sample,IDX,BamName,PatientID,PatientID.replicate,PreOn,PatientIDrep,PopCateg,BOR,Response,Response,USUBJID,Cohort\n"
                  ",S1,1,Pt999_Pre_AA1-1.bam,Pt999,,,,,PR,PRCR,LB,SUBJ1,NIV3-NAIVE\n").encode()
    clinical_csv = b"PatientID,BOR,Cohort\nPt999,PR,NIV3-NAIVE\n"
    matrix = ("GeneID,GSM0000001\n").encode()
    source_bytes = {"geo_family_soft": b"geo", "author_sample_table": sample_csv,
                    "author_clinical_table": clinical_csv, "author_fpkm_hg19": matrix}
    sources = {role: _source(role, raw) for role, raw in source_bytes.items()}
    parsed: dict[str, Any] = {
        "geo_family_soft": soft,
        "author_sample_table": read_delimited_table(sample_csv, delimiter=","),
        "author_clinical_table": read_delimited_table(clinical_csv, delimiter=","),
        "author_fpkm_hg19": ("GeneID", "GSM0000001"),
    }
    field_map = {
        "cohort": "riaz_gse91061", "branch_id": "A_BASELINE_BIO",
        "study_class": "CLINICAL_ICI",
        "source_objects": {role: {"sha256": source.sha256, "locator": source.locator,
                                   "version": source.version, "format": "MATRIX_HEADER_CSV"}
                           for role, source in sources.items()},
        "sample_identity": {"title_regex": r"^(Pt\d+)_(Pre|On)",
                            "patient_group": 1, "visit_group": 2},
        "geo": {"characteristics": {"visit": "visit (pre or on treatment)",
                                      "response": "response"}, "relation_kinds": ["BioSample", "SRA"]},
        "author_sample_table": {"sample_name_column": 3, "patient_column": 4, "bam_suffix": ".bam",
                                "response_positions": {"bor": 9, "response_primary": 10,
                                                       "response_alternative": 11},
                                "sample_name_rule": {"regex": r"\.(\d+)$", "replacement": r"-\1"}},
        "author_clinical_table": {"patient_column": 0, "bor_column": "BOR", "cohort_column": "Cohort"},
        "treatment": {"agent": "nivolumab", "prior_ipilimumab_by_cohort":
                      {"NIV3-NAIVE": False, "NIV3-PROG": True}},
        "labels": {"source_of_record_bor": {"CR": "CR", "PR": "PR", "SD": "SD", "PD": "PD", "NE": "NE"},
                   "geo_response": {"PRCR": "RESPONDER", "SD": "SD", "PD": "PD", "UNK": "UNK"}},
        "measurement_representations": {"author_fpkm_hg19": {"unit": "FPKM",
                "transform": "AUTHOR_REPORTED", "genome_build": "hg19", "annotation": "KnownGene"}},
    }
    items: list[dict[str, Any]] = []

    records = build_canonical_records(parsed, sources, field_map, items)

    assert ENTITY_TABLES <= records.keys()
    assert not any(key.endswith("_proposals") for key in records)
    assert len(records["patient_registry"]) == 1
    patient = records["patient_registry"][0]
    assert patient["source_patient_id"] == "Pt999"
    assert patient["patient_identity_confidence"] == "VERIFIED"
    assert patient["prior_ici"] == "NO"
    assert patient["treatment_naive_status"] == "UNKNOWN"
    assert len(records["specimen_registry"]) == 1
    specimen = records["specimen_registry"][0]
    assert specimen["canonical_timing_category"] == "PRE_INDEX_BASELINE"
    assert specimen["baseline_candidate_status"] == "YES"
    assert specimen["timing_raw_text"] == "Pre"
    assert len(records["clinical_outcome"]) == 1
    outcome = records["clinical_outcome"][0]
    assert outcome["best_overall_response"] == "PR"
    assert outcome["canonical_category"] == "PR"
    assert outcome["assessment_criteria"] == ""
    assert len(records["assay_registry"]) == 1
    assert records["assay_registry"][0]["measurement_unit"] == "FPKM"
    assert records["assay_registry"][0]["transform"] == "AUTHOR_REPORTED"
    assert records["study_registry"][0]["study_class"] == "CLINICAL_ICI"
    assert patient["data_classification"] == "PRIVATE_PATIENT_LEVEL"

    schemas = SchemaStore()
    for table in ENTITY_TABLES:
        for row in records[table]:
            schemas.validate(table, row)

    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": records, "config": {"registries": {
                  "study_ids": [records["study_registry"][0]["study_id"]],
                  "source_hashes": {row["source_object_id"]: row["sha256"]
                                    for row in records["source_record"]}}},
              "schema_hashes": schemas.hashes, "dependencies": {}}
    registry_result = build_registries(packet, schemas=schemas)
    assert registry_result["status"] == "READY"


def test_undeclared_study_class_is_not_filled_with_a_guessed_class() -> None:
    field_map = {
        "cohort": "invented_cohort", "branch_id": "A_BASELINE_BIO",
        "source_objects": {"source": {"locator": "https://example.invalid/source", "version": "v1",
                                         "format": "TEXT_UTF8", "sha256": None}},
    }
    records = build_canonical_records({}, {}, field_map, [])
    assert "study_class" not in records["study_registry"][0]


def test_run_ingest_chains_canonical_registry_stage_for_a_clean_source_join(tmp_path: Path,
                                                                            monkeypatch: Any) -> None:
    field_map = json.loads(Path("tools/a_dav/field_maps/riaz_gse91061.json").read_text())
    title = "Pt999_Pre_AA1-1"
    soft = ("^SAMPLE = GSM0000001\n!Sample_geo_accession = GSM0000001\n"
            f"!Sample_title = {title}\n"
            "!Sample_characteristics_ch1 = visit (pre or on treatment): Pre\n"
            "!Sample_characteristics_ch1 = response: PRCR\n"
            "!Sample_characteristics_ch1 = tissue: melanoma\n")
    sample_table = (",Sample,IDX,BamName,PatientID,PatientID.replicate,PreOn,PatientIDrep,PopCateg,BOR,Response,Response,USUBJID,Cohort\n"
                    f",S1,1,{title}.bam,Pt999,,,,,PR,PRCR,LB,SUBJ1,NIV3-NAIVE\n")
    clinical = "PatientID,BOR,Cohort\nPt999,PR,NIV3-NAIVE\n"
    contents: dict[str, bytes] = {}
    for role, metadata in field_map["source_objects"].items():
        if role == "geo_family_soft":
            raw = gzip.compress(soft.encode())
        elif role == "author_sample_table":
            raw = sample_table.encode()
        elif role == "author_clinical_table":
            raw = clinical.encode()
        elif role == "author_analysis_code":
            raw = b"# Invented fixture. No exclusion rules.\n"
        elif role == "author_fpkm_hg19":
            raw = f",{title}\n".encode()
        elif role == "ncbi_tpm_grch38":
            raw = b"GeneID\tGSM0000001\n"
        elif role == "ncbi_annotation_grch38":
            raw = b"GeneID\tSymbol\n"
        elif role == "cbioportal_sample":
            raw = b"# metadata\nSAMPLE_ID\tRESPONSE\nS1\tPR\n"
        elif role == "cbioportal_patient":
            raw = b"# metadata\nPATIENT_ID\tAGE\nP1\t60\n"
        else:
            raise AssertionError(f"Unexpected field-map role: {role}")
        sha = hashlib.sha256(raw).hexdigest()
        metadata["sha256"] = sha
        contents[sha] = raw

    map_root = tmp_path / "maps"
    map_root.mkdir()
    (map_root / "riaz_gse91061.json").write_text(json.dumps(field_map))
    monkeypatch.setattr(ingest_module, "FIELD_MAP_ROOT", map_root)
    store = tmp_path / "store"
    (store / "objects").mkdir(parents=True)
    manifest_objects = {}
    for role, metadata in field_map["source_objects"].items():
        sha = metadata["sha256"]
        raw = contents[sha]
        (store / "objects" / sha).write_bytes(raw)
        manifest_objects[sha] = {"locator": metadata["locator"], "version": metadata["version"],
                                 "byte_size": len(raw), "retrieved_at": "2026-10-25T00:00:00Z"}
    (store / "MANIFEST.json").write_text(json.dumps({"objects": manifest_objects}))

    result = run_ingest("riaz_gse91061", "A_BASELINE_BIO", store, tmp_path / "out",
                        allow_external_out=True)

    assert result["summary"]["counts"]["geo_samples"] == 1
    assert result["summary"]["counts"]["baseline_samples_linked_to_patient"] == 1
    assert result["summary"]["stage_statuses"]["registries"] == "READY"
    assert result["summary"]["stage_statuses"]["endpoints"] == "BLOCKED_UNKNOWN"
    assert {row["measurement_unit"] for row in result["packet"]["records"]["assay_registry"]} == {"FPKM", "TPM"}
    assert {row["genome_build"] for row in result["packet"]["records"]["assay_registry"]} == {"hg19", "GRCh38.p13"}
    assert set(result["packet"]["dependencies"]) == {"registries"}
    ingestion_items = [item for item in result["worksheet"]["items"] if item["kind"] == "ingestion"]
    assert ingestion_items == []
    assert not any(item.get("reason_codes") == "MISSING_ASSERTION"
                   for item in result["worksheet"]["items"])


def test_generic_on_treatment_label_stays_unknown_in_canonical_window() -> None:
    soft = [{"accession": "GSM0000002", "geo_accession": "GSM0000002",
             "title": "Pt888_On_AA1-1", "characteristics": [
                 {"key": "visit (pre or on treatment)", "value": "On"}], "relations": []}]
    sample_csv = (",Sample,IDX,BamName,PatientID,PatientID.replicate,PreOn,PatientIDrep,PopCateg,BOR,Response,Response,USUBJID,Cohort\n"
                  ",S2,2,Pt888_On_AA1-1.bam,Pt888,,,,,PD,PD,LB,SUBJ2,NIV3-NAIVE\n").encode()
    clinical_csv = b"PatientID,BOR,Cohort\nPt888,PD,NIV3-NAIVE\n"
    sample_table = read_delimited_table(sample_csv, delimiter=",")
    clinical_table = read_delimited_table(clinical_csv, delimiter=",")
    parsed = {"geo_family_soft": soft, "author_sample_table": sample_table,
              "author_clinical_table": clinical_table}
    sources = {"geo_family_soft": _source("geo_family_soft", b"geo"),
               "author_sample_table": _source("author_sample_table", sample_csv),
               "author_clinical_table": _source("author_clinical_table", clinical_csv)}
    field_map = {"cohort": "riaz_gse91061", "branch_id": "A_BASELINE_BIO",
        "source_objects": {role: {"locator": f"https://example.invalid/{role}", "version": "v1",
                                   "format": "DELIMITED_CSV", "sha256": None}
                           for role in sources},
        "sample_identity": {"title_regex": r"^(Pt\d+)_(Pre|On)", "patient_group": 1, "visit_group": 2},
        "geo": {"characteristics": {"visit": "visit (pre or on treatment)", "response": "response"}},
        "author_sample_table": {"sample_name_column": 3, "patient_column": 4, "bam_suffix": ".bam",
            "sample_name_rule": {"regex": r"\.(\d+)$", "replacement": r"-\1"},
            "response_positions": {"bor": 9}},
        "author_clinical_table": {"patient_column": 0, "bor_column": "BOR", "cohort_column": "Cohort"},
        "labels": {"source_of_record_bor": {"PD": "PD"}, "geo_response": {}},
        "measurement_representations": {}}
    items: list[dict[str, Any]] = []

    records = build_canonical_records(parsed, sources, field_map, items)

    assert records["specimen_registry"][0]["canonical_timing_category"] == "UNKNOWN"
    assert records["specimen_registry"][0]["baseline_candidate_status"] == "NO"
    assert [item["category"] for item in items] == ["ON_TREATMENT_WINDOW_UNRESOLVED"]
    assert items[0]["status"] == "BLOCKED_UNKNOWN"
    assert items[0]["context"] == {"source_label": "On", "specimen_count": 1}
    from tools.a_dav.worksheet import build_worksheet
    packet = {"branch_id": "A_BASELINE_BIO", "records": records,
              "config": {"admission": {"ingestion_worksheet": {
                  "classification": "PRIVATE_PATIENT_LEVEL", "status": "BLOCKED_UNKNOWN", "items": items}}}}
    consolidated = build_worksheet(packet)
    assert consolidated["items"][0]["status"] == "BLOCKED_UNKNOWN"


def test_harmonized_count_discrepancy_requires_actual_source_count_difference() -> None:
    from tools.a_dav.ingest import _known_items

    table = read_delimited_table(b"SAMPLE_ID\tRESPONSE\nS1\tPR\n", delimiter="\t")
    items: list[dict[str, Any]] = []
    _known_items({"harmonized_cross_checks": [{"resource": "invented", "expected_sample_count": 107}]},
                 items, {"geo_samples": 1}, {"cbioportal_sample": table})

    assert items == []
    _known_items({"harmonized_cross_checks": [{"resource": "invented", "expected_sample_count": 1}]},
                 items, {"geo_samples": 2}, {"cbioportal_sample": table})
    assert [item["category"] for item in items] == ["HARMONIZED_SAMPLE_COUNT_CROSSCHECK"]
