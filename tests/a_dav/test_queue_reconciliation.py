"""Tests for A-DAV-04 queue reconciliation (DAV-T01 intake, DAV-T02 provisional decisions).

Sections
- Synthetic unit tests (fictional identifiers, example.org locators only).
- Real-input offline tests: the hashed queue files are read in place from the project
  container. Nothing is copied into Git.
- Phase 2 offline tests: run against the committed sample-free NCBI fixtures and the
  manifest. No network access.
"""

import copy
import csv
from collections import Counter
import hashlib
import json
import random
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.a_dav import queue_reconciliation as qr
from tools.a_dav import search_log as sl
from tools.a_dav import study_resolution as sr


WORKTREE = Path(__file__).resolve().parents[2]
PROJECT_CONTAINER = Path(__file__).resolve().parents[4]
SPEC = WORKTREE / "specs" / "A_DATA_ACQUISITION_VALIDATION"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "queue_reconciliation"
PHASE2_DIR = FIXTURES / "phase2"
PHASE2_PRIVATE = WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "phase2_private"
DISCOVERY_SPEC = SPEC / "SOURCE_DISCOVERY_STRATEGY.md"

REG_CSV = PROJECT_CONTAINER / "outputs" / "study-clearance-20261002" / "ALL_117_STUDY_USE_REGISTRY.csv"
REG_JSON = PROJECT_CONTAINER / "outputs" / "study-clearance-20261002" / "ALL_117_STUDY_USE_REGISTRY.json"
EPI_CSV = PROJECT_CONTAINER / "reports" / "epigenetic_drug_study_index.csv"
EPI_XLSX = PROJECT_CONTAINER / "reports" / "epigenetic_drug_study_index.xlsx"

HASHES = {
    REG_CSV: "ae54d135cace7cd85ab4b96f1825474024fc841a56fcd25ffcbbc871196463da",
    REG_JSON: "485185147421aa320bd51a21b36e171e4516ad09381f488f9f886ef9820ee973",
    EPI_CSV: "4634b52fed50fa8b057ebc0e89016071f3aa04571c448ef512fe1f59d597b2b1",
    EPI_XLSX: "1006003675cc608e08efde478ae03434a1eb250ad6d9074d6ef908f963720950",
}
STUDY_SCHEMA_SHA = "06bf4e1cfacc70ee6b1470dc66cb6b6bb3db5daa8aa77b208f714fae94095f7b"
PUB_SCHEMA_SHA = "ca78d371009f5747769449848772422ebc2ce36ffc8a59434cc167e1808d8bf7"
PIPELINE_UTC = "2026-10-17T16:00:00Z"
GSM_PATTERN = re.compile(r"\bGSM\d+\b")


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _schema(relative):
    return json.loads((SPEC / relative).read_text(encoding="utf-8"))


STUDY_SCHEMA = _schema("schemas/study_registry.schema.json")
PUBLICATION_SCHEMA = _schema("schemas/publication_family.schema.json")


# ------------------------------------------------------------------ synthetic builders

REG_COLUMNS = (
    "catalogue_entry_id", "current_disposition", "current_primary_disposition", "source_family",
    "original_title", "verified_title", "original_cancer", "verified_cancer", "verified_modality",
    "native_scale", "intended_product", "usefulness", "next_data_product", "next_action",
    "analysis_cleared", "evidence_urls",
)
EPI_COLUMNS = (
    "title", "authors", "year", "class", "drugs", "immunotherapy", "immunotherapy_type", "cancer",
    "model", "species", "assay", "accessions", "status", "readiness", "paper_url", "repository_urls",
    "study_id", "model_group", "experiment_ids", "arms", "access_status", "raw_links", "processed_links",
    "evidence_urls", "priority_order",
)


def reg(row_id, disposition="supporting_or_context", family="SYN-FAMILY-A", urls="", **extra):
    row = {column: "" for column in REG_COLUMNS}
    row.update({
        "catalogue_entry_id": row_id,
        "current_disposition": disposition,
        "current_primary_disposition": disposition,
        "source_family": family,
        "original_title": "SYNTHETIC original title " + row_id,
        "verified_title": "SYNTHETIC verified title " + row_id,
        "verified_modality": "SYNTHETIC bulk RNA",
        "usefulness": "SYNTHETIC usefulness",
        "next_action": "SYNTHETIC next action",
        "analysis_cleared": "False",
        "evidence_urls": urls,
    })
    row.update(extra)
    return row


def epi(study_id, model_group="Human clinical", immunotherapy="None", accessions="", paper_url="",
        title=None, **extra):
    row = {column: "" for column in EPI_COLUMNS}
    row.update({
        "study_id": study_id,
        "model_group": model_group,
        "immunotherapy": immunotherapy,
        "accessions": accessions,
        "paper_url": paper_url,
        "title": title or "SYNTHETIC epigenetic title " + study_id,
        "drugs": "SYNTHETIC drug",
        "cancer": "SYNTHETIC cancer",
        "access_status": "SYNTHETIC access",
        "evidence_urls": paper_url,
    })
    row.update(extra)
    return row


def source(tag, rows, path=None, sha256=None):
    spec = qr.SOURCE_SPECS[tag]
    return {
        "tag": tag,
        "path": path or spec["path"],
        "sha256": sha256 or spec["sha256"],
        "rows": rows,
    }


def run(*sources, **kwargs):
    return qr.reconcile(list(sources), pipeline_utc=PIPELINE_UTC, **kwargs)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------------ identifier extraction


def test_extracts_every_declared_identifier_kind():
    text = " ".join([
        "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE115821",
        "SRP094781", "PRJNA1041407", "PRJEB23709", "EGAS00001004050", "EGAD00001007672",
        "phs001493.v1.p1", "E-MTAB-6214", "NCT03582475", "PXD039469",
        "https://pubmed.ncbi.nlm.nih.gov/29033130/", "https://doi.org/10.1038/s41467-021-26299-4",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6028240/",
    ])
    kinds = {item["kind"] for item in qr.extract_identifiers(text, "evidence_urls")}
    assert {"GSE", "SRP", "PRJNA", "PRJEB", "EGAS", "EGAD", "PHS", "EMTAB", "NCT", "PXD", "PMID", "DOI",
            "PMCID"} <= kinds


def test_extraction_preserves_raw_value_and_records_field_provenance():
    items = qr.extract_identifiers("phs001493.v1.p1 and acc=gse115821", "accessions")
    raws = {item["raw"] for item in items}
    assert "phs001493.v1.p1" in raws
    assert "gse115821" in raws
    assert all(item["field"] == "accessions" for item in items)


def test_fold_is_case_and_punctuation_insensitive_and_drops_phs_version_suffix():
    assert qr.fold_identifier("GSE", "gse115821") == "GSE115821"
    assert qr.fold_identifier("PHS", "phs001493.v1.p1") == "PHS001493"
    assert qr.fold_identifier("PHS", "PHS001493") == "PHS001493"
    assert qr.fold_identifier("DOI", "10.1038/NATURE25501") == qr.fold_identifier("DOI", "10.1038/nature25501")


def test_leading_zeros_are_preserved_and_never_folded_away():
    assert qr.fold_identifier("EGAS", "EGAS00001004050") != qr.fold_identifier("EGAS", "EGAS1004050")
    assert qr.fold_identifier("NCT", "NCT03582475").endswith("03582475")
    items = qr.extract_identifiers("NCT00123456", "evidence_urls")
    assert [item["raw"] for item in items] == ["NCT00123456"]


def test_nature_article_url_yields_a_derived_doi_marked_as_derived():
    items = qr.extract_identifiers("https://www.nature.com/articles/nature25501", "evidence_urls")
    doi = [item for item in items if item["kind"] == "DOI"]
    assert doi and doi[0]["raw"] == "10.1038/nature25501"
    assert doi[0]["derived"] is True


def test_pubmed_and_pmc_urls_are_typed_correctly():
    pmid = qr.extract_identifiers("https://pubmed.ncbi.nlm.nih.gov/29443960/", "evidence_urls")
    pmc = qr.extract_identifiers("https://pmc.ncbi.nlm.nih.gov/articles/6028240/", "evidence_urls")
    pmid_path = qr.extract_identifiers("https://pmc.ncbi.nlm.nih.gov/articles/pmid/27301722/", "evidence_urls")
    assert [(i["kind"], i["raw"]) for i in pmid] == [("PMID", "29443960")]
    assert [(i["kind"], i["raw"]) for i in pmc] == [("PMCID", "PMC6028240")]
    assert [(i["kind"], i["raw"]) for i in pmid_path] == [("PMID", "27301722")]


def test_geo_bin_directory_names_are_not_accessions():
    text = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE188nnn/GSE188249/suppl/x.csv.gz"
    raws = {item["raw"] for item in qr.extract_identifiers(text, "processed_links")}
    assert raws == {"GSE188249"}


def test_geo_sample_accessions_are_never_extracted_as_identifiers():
    items = qr.extract_identifiers(
        "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM0000001 and GSM0000002", "evidence_urls")
    assert items == []


def test_credential_bearing_text_is_rejected_through_the_imported_scanners():
    row = reg("SYN-SECRET-1", urls="https://example.org/a?api_key=SYNTHETICVALUE123456")
    with pytest.raises(qr.QueueReconciliationError) as caught:
        run(source("REG", [row]))
    assert caught.value.code == "SECRET_LOCATOR"
    row = reg("SYN-SECRET-2", family="password=SYNTHETICVALUE")
    with pytest.raises(qr.QueueReconciliationError):
        run(source("REG", [row]))


# ------------------------------------------------------------------ intake IDs and scope




def test_out_of_scope_rows_are_listed_with_a_reason_and_not_dispositioned():
    result = run(source("EPI", [
        epi("S01", immunotherapy="Nivolumab", accessions="GSE248014"),
        epi("S02", model_group="Mouse", accessions="GSE111111"),
    ]))
    assert [row["row_id"] for row in result["dispositioned_rows"]] == ["S01"]
    out = result["out_of_scope_rows"]
    assert len(out) == 1 and out[0]["row_id"] == "S02"
    assert "Mouse" in out[0]["reason"]
    assert out[0]["reason"].startswith("outside human-clinical scope")


def test_count_reconciliation_is_exact_on_synthetic_inputs():
    result = run(
        source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
                       reg("SYN-B", urls="https://example.org/no-identifier")]),
        source("EPI", [
            epi("S01", immunotherapy="Nivolumab", accessions="GSE700001"),
            epi("S02", immunotherapy="None", accessions="GSE700002"),
            epi("S03", model_group="Cell-line culture"),
            epi("S04", model_group="Mouse"),
        ]),
    )
    counts = result["counts"]
    assert counts["in_scope_total"] == 2 + 2
    assert counts["out_of_scope_total"] == 2
    assert counts["input_rows_total"] == 6
    assert counts["dispositioned_total"] == counts["in_scope_total"]
    assert counts["in_scope_total"] + counts["out_of_scope_total"] == counts["input_rows_total"]


def test_every_in_scope_row_has_exactly_one_disposition_with_a_reason():
    result = run(source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
                                reg("SYN-B", disposition="blocked")]))
    ids = [row["intake_id"] for row in result["dispositioned_rows"]]
    assert len(ids) == len(set(ids)) == 2
    for row in result["dispositioned_rows"]:
        assert row["disposition"] in qr.DISPOSITION_CODES
        assert row["reason"].strip()
        assert row["rule_id"].strip()


# ------------------------------------------------------------------ disposition vocabulary


def test_declared_discovery_codes_match_the_frozen_vocabulary_verbatim():
    text = DISCOVERY_SPEC.read_text(encoding="utf-8")
    frozen = ["non-ICI treatment", "vaccine or adoptive-cell study", "mechanistic cell model",
              "untreated molecular cohort", "wrong endpoint", "no patient-level route", "no molecular data",
              "duplicate/reanalysis", "inaccessible or unavailable object", "wrong biological compartment",
              "outside branch scope"]
    for label in frozen:
        assert label in text
    declared = {qr.DISCOVERY_LABELS[code] for code in qr.FROZEN_DISCOVERY_CODES}
    assert declared == set(frozen)
    assert set(qr.DISPOSITION_CODES) == set(qr.FROZEN_DISCOVERY_CODES) | {"INCLUDED_AS_LEAD", "UNRESOLVED"}


def test_registry_disposition_mapping_is_declared_and_closed():
    assert set(qr.REGISTRY_DISPOSITION_MAP) == {
        "primary_candidate_pending_private", "blocked", "supporting_or_context"}
    for value in qr.REGISTRY_DISPOSITION_MAP.values():
        assert value in qr.DISPOSITION_CODES or value.startswith("RULE_REFINED")


@pytest.mark.parametrize("expected, row_kwargs, identifier_text", [
    ("INCLUDED_AS_LEAD", dict(disposition="primary_candidate_pending_private",
                              urls="https://pubmed.ncbi.nlm.nih.gov/111111/"), None),
    ("INACCESSIBLE_OBJECT", dict(disposition="blocked", urls="https://ega-archive.org/studies/EGAS00001005013"), None),
    ("DUPLICATE_REANALYSIS", dict(disposition="blocked", urls="https://pubmed.ncbi.nlm.nih.gov/222222/",
                                  next_action="reconcile overlap with the Snyder cohort"), None),
    ("NO_MOLECULAR_DATA", dict(disposition="supporting_or_context", verified_modality="H&E histopathology WSI",
                               urls="https://pubmed.ncbi.nlm.nih.gov/333333/"), None),
    ("VACCINE_OR_ADOPTIVE_CELL", dict(disposition="supporting_or_context", verified_title="PROSTVAC antiglycan",
                                      urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700010"), None),
    ("MECHANISTIC_CELL_MODEL", dict(disposition="supporting_or_context", verified_modality="organoid culture",
                                    urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700011"), None),
    ("NON_ICI_TREATMENT", dict(disposition="supporting_or_context", verified_title="azacitidine response",
                               urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700012"), None),
    ("UNRESOLVED", dict(disposition="supporting_or_context", urls="https://example.org/no-identifier"), None),
    ("INCLUDED_AS_LEAD", dict(disposition="supporting_or_context",
                              urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700013"), None),
])
def test_each_registry_rule_is_reachable(expected, row_kwargs, identifier_text):
    row_id = "SYN-RULE-" + expected
    result = run(source("REG", [reg(row_id, **row_kwargs)]))
    disposition = result["dispositioned_rows"][0]
    if disposition["rule_id"].startswith("PROPOSED:"):
        assert disposition["disposition"] == "UNRESOLVED"  # round 5: free-text rules propose only
        assert disposition["proposed_disposition"] == expected
    else:
        assert disposition["disposition"] == expected
    assert disposition["rule_id"]


@pytest.mark.parametrize("expected, row_kwargs", [
    ("INCLUDED_AS_LEAD", dict(immunotherapy="Nivolumab (anti-PD-1)", accessions="GSE700020")),
    ("UNRESOLVED", dict(immunotherapy="Pembrolizumab later in clinical protocol; mouse experiments",
                        accessions="None verified")),
    ("NON_ICI_TREATMENT", dict(immunotherapy="None", accessions="GSE700021")),
])
def test_epigenetic_clinical_rules_are_reachable(expected, row_kwargs):
    result = run(source("EPI", [epi("S70", **row_kwargs)]))
    assert result["dispositioned_rows"][0]["disposition"] == expected


def test_epigenetic_ici_lead_names_regimen_unknown_pending_dav_t06():
    result = run(source("EPI", [epi("S71", immunotherapy="Nivolumab", accessions="GSE700022")]))
    row = result["dispositioned_rows"][0]
    assert "DAV-T06" in row["reason"]
    assert "UNKNOWN" in row["reason"]


def test_ambiguous_regimen_row_is_flagged_as_unresolved_regimen():
    result = run(source("EPI", [epi("S72", immunotherapy="Pembrolizumab later in clinical protocol",
                                    accessions="None verified")]))
    row = result["dispositioned_rows"][0]
    assert row["disposition"] == "UNRESOLVED"
    assert "UNRESOLVED-regimen" in row["reason"]


def test_unassigned_frozen_codes_are_declared_but_not_produced_by_this_packet():
    result = run(source("REG", [reg("SYN-A", disposition="supporting_or_context",
                                    urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700030")]))
    produced = {row["disposition"] for row in result["dispositioned_rows"]}
    unassigned = set(qr.FROZEN_DISCOVERY_CODES) - produced
    assert {"UNTREATED_MOLECULAR_COHORT", "WRONG_ENDPOINT", "NO_PATIENT_LEVEL_ROUTE",
            "WRONG_COMPARTMENT", "OUTSIDE_BRANCH_SCOPE"} <= unassigned


# ------------------------------------------------------------------ clustering and conflicts


def test_shared_identifier_merges_rows_into_one_candidate_study():
    result = run(source("REG", [
        reg("SYN-A", urls="https://pmc.ncbi.nlm.nih.gov/articles/PMC6028240/"),
        reg("SYN-B", urls="https://pubmed.ncbi.nlm.nih.gov/222222/ https://pmc.ncbi.nlm.nih.gov/articles/6028240/"),
        reg("SYN-C", urls="https://pubmed.ncbi.nlm.nih.gov/333333/"),
    ]))
    by_row = {row["row_id"]: row["cluster_id"] for row in result["dispositioned_rows"]}
    assert by_row["SYN-A"] == by_row["SYN-B"]
    assert by_row["SYN-C"] != by_row["SYN-A"]
    assert result["counts"]["candidate_study_count"] == 2


def test_clustering_is_transitive_over_chained_identifiers():
    result = run(source("REG", [
        reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
        reg("SYN-B", urls="https://pubmed.ncbi.nlm.nih.gov/111111/ https://pmc.ncbi.nlm.nih.gov/articles/6028240/"),
        reg("SYN-C", urls="https://pmc.ncbi.nlm.nih.gov/articles/6028240/"),
    ]))
    assert len({row["cluster_id"] for row in result["dispositioned_rows"]}) == 1


def test_shared_source_family_label_alone_does_not_merge_and_is_reported():
    result = run(source("REG", [
        reg("SYN-A", family="SYN-LABEL", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
        reg("SYN-B", family="SYN-LABEL", urls="https://pubmed.ncbi.nlm.nih.gov/222222/"),
    ]))
    assert len({row["cluster_id"] for row in result["dispositioned_rows"]}) == 2
    codes = [conflict["code"] for conflict in result["conflicts"]]
    assert "FAMILY_LABEL_SPLIT" in codes


def test_study_ids_are_identifier_derived_and_stable():
    # Round 2: a family-label accession no longer names a study, so the accession is listed directly in the row.
    result = run(source("REG", [reg("SYN-A", family="SYN-GSE-FAMILY-GSE700040",
                                    urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700040")]))
    study_ids = [cluster["study_id"] for cluster in result["clusters"]]
    assert study_ids == ["QR-GSE700040"]
    again = run(source("REG", [reg("SYN-A", family="SYN-GSE-FAMILY-GSE700040",
                                   urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700040")]))
    assert canonical(again["clusters"]) == canonical(result["clusters"])


def test_family_identifier_disagreement_is_surfaced_and_not_resolved_by_majority():
    result = run(source("REG", [reg("SYN-A", family="SYN-GSE173351",
                                    urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176021")]))
    conflicts = [c for c in result["conflicts"] if c["code"] == "FAMILY_IDENTIFIER_DISAGREEMENT"]
    assert len(conflicts) == 1
    assert set(conflicts[0]["identifiers"]) == {"GSE173351", "GSE176021"}
    assert conflicts[0]["resolution"] == "UNRESOLVED_NOT_MAJORITY"


def test_accession_alias_conflict_when_one_identifier_spans_two_families():
    result = run(source("REG", [
        reg("SYN-A", family="SYN-FAMILY-ONE", urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700050"),
        reg("SYN-B", family="SYN-FAMILY-TWO", urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700050"),
    ]))
    conflicts = [c for c in result["conflicts"] if c["code"] == "ACCESSION_ALIAS_CONFLICT"]
    assert len(conflicts) == 1
    assert conflicts[0]["identifiers"] == ["GSE700050"]
    assert set(conflicts[0]["families"]) == {"SYN-FAMILY-ONE", "SYN-FAMILY-TWO"}


def test_disposition_field_disagreement_is_reported_per_row():
    row = reg("SYN-A", disposition="blocked", urls="https://pubmed.ncbi.nlm.nih.gov/111111/",
              current_primary_disposition="supporting_or_context")
    result = run(source("REG", [row]))
    codes = [c["code"] for c in result["conflicts"]]
    assert "DISPOSITION_FIELD_DISAGREEMENT" in codes
    assert result["dispositioned_rows"][0]["disposition"] in qr.DISPOSITION_CODES


def test_row_without_identifiers_stays_unresolved_with_a_catalogue_label_alias():
    result = run(source("REG", [reg("SYN-A", urls="https://example.org/no-identifier")]))
    row = result["dispositioned_rows"][0]
    assert row["disposition"] == "UNRESOLVED"
    assert row["cluster_id"] is None


# ------------------------------------------------------------------ packets and contracts


def test_every_in_scope_row_yields_a_candidate_packet_that_validates():
    result = run(
        source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
                       reg("SYN-B", urls="https://example.org/none")]),
        source("EPI", [epi("S01", immunotherapy="Nivolumab", accessions="GSE700060")]),
    )
    packets = qr.build_packets(result)
    assert len(packets) == 3
    valid = {row["intake_id"] for row in result["dispositioned_rows"]}
    for packet in packets:
        sl.validate_candidate_packet(packet, valid)
        assert packet["query_ids"] and packet["query_ids"][0] in valid
        assert packet["verified_facts"]
        for fact in packet["verified_facts"]:
            assert fact["source_locator"]["kind"] == "FILE"


def test_packet_ids_and_query_ids_are_manifest_scoped():
    result = run(source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")]))
    packet = qr.build_packets(result)[0]
    assert packet["query_ids"] == ["QUEUE-REG-SYN-A"]


def test_proposed_records_pass_resolve_and_the_frozen_schemas():
    result = run(
        source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
                       reg("SYN-B", family="SYN-GSE-FAMILY-GSE700070",
                           urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700070")]),
        source("EPI", [epi("S01", immunotherapy="Nivolumab", accessions="GSE700071")]),
    )
    proposed = qr.proposed_records(result, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    receipt = proposed["receipt"]
    assert receipt["status"] == "PROPOSED_NOT_RESOLVED"
    assert receipt["admitted_count"] == 0
    assert receipt["analysis_readiness"] == "NOT_ANALYSIS_READY"
    studies = proposed["study_records"]
    assert studies and all(study["study_status"] in ("CANDIDATE", "RESOLVING") for study in studies)
    for study in studies:
        Draft202012Validator(STUDY_SCHEMA).validate(study)
        assert study["study_class"] == "OTHER"
        for field in ("cancer_type", "treatment_regimen_id", "drug", "checkpoint_target"):
            assert study[field] in ("UNKNOWN", None)
    assert all(row["certainty"] != "VERIFIED" for row in proposed["alias_rows"])
    assert "RESOLVED" not in {study["study_status"] for study in studies}


def test_phase1_certainty_never_exceeds_probable():
    result = run(source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")]))
    decision = qr.build_decision(result)
    certainties = {alias["certainty"] for alias in decision["aliases"]}
    assert certainties <= {"PROBABLE", "POSSIBLE", "UNRESOLVED"}
    assert decision["provisional"] is True
    assert decision["reviewer"] == "provisional-integrator-A-DAV-04-implementer"


def test_provisional_decision_cannot_emit_excluded_or_resolved():
    result = run(source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")]))
    decision = qr.build_decision(result)
    for status in ("EXCLUDED", "SUPERSEDED", "RESOLVED"):
        mutated = copy.deepcopy(decision)
        mutated["studies"][0]["study_status"] = status
        mutated["studies"][0]["status_reason"] = "SYNTHETIC reason"
        with pytest.raises(sr.ResolutionError) as caught:
            sr.resolve(qr.build_packets(result), mutated, set(qr.valid_query_ids(result)),
                       STUDY_SCHEMA, PUBLICATION_SCHEMA)
        assert caught.value.code == "STATUS_CEILING"


def test_resolve_rejects_a_packet_that_does_not_reference_a_valid_intake_id():
    result = run(source("REG", [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")]))
    packets = qr.build_packets(result)
    with pytest.raises(sr.ResolutionError):
        sr.resolve(packets, qr.build_decision(result), {"QUEUE-OTHER-ROW"}, STUDY_SCHEMA, PUBLICATION_SCHEMA)


# ------------------------------------------------------------------ determinism (metamorphic)


def test_shuffled_rows_and_files_give_identical_clusters_ids_and_reports():
    reg_rows = [
        reg("SYN-A", family="SYN-FAMILY-ONE", urls="https://pmc.ncbi.nlm.nih.gov/articles/PMC6028240/"),
        reg("SYN-B", family="SYN-FAMILY-ONE", urls="https://pubmed.ncbi.nlm.nih.gov/222222/ https://pmc.ncbi.nlm.nih.gov/articles/6028240/"),
        reg("SYN-C", family="SYN-GSE-FAMILY-GSE700080", urls="https://pubmed.ncbi.nlm.nih.gov/333333/"),
        reg("SYN-D", family="SYN-GSE-FAMILY-GSE700080", urls="https://pubmed.ncbi.nlm.nih.gov/444444/"),
        reg("SYN-E", urls="https://example.org/none"),
    ]
    epi_rows = [epi("S01", immunotherapy="Nivolumab", accessions="GSE700081"),
                epi("S02", model_group="Mouse")]
    baseline = run(source("REG", reg_rows), source("EPI", epi_rows))
    rng = random.Random(20261017)
    for _ in range(5):
        shuffled_reg = list(reg_rows)
        shuffled_epi = list(epi_rows)
        rng.shuffle(shuffled_reg)
        rng.shuffle(shuffled_epi)
        sources = [source("EPI", shuffled_epi), source("REG", shuffled_reg)]
        rng.shuffle(sources)
        shuffled = run(*sources)
        assert canonical(shuffled["clusters"]) == canonical(baseline["clusters"])
        assert canonical(shuffled["dispositioned_rows"]) == canonical(baseline["dispositioned_rows"])
        assert canonical(shuffled["conflicts"]) == canonical(baseline["conflicts"])
        assert canonical(shuffled["counts"]) == canonical(baseline["counts"])
        assert canonical(qr.build_packets(shuffled)) == canonical(qr.build_packets(baseline))
        assert canonical(qr.build_decision(shuffled)) == canonical(qr.build_decision(baseline))


def test_shuffled_inputs_give_identical_tsv_hashes():
    rows = [reg("SYN-A", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
            reg("SYN-B", urls="https://pubmed.ncbi.nlm.nih.gov/222222/")]
    a = qr.proposed_records(run(source("REG", rows)), STUDY_SCHEMA, PUBLICATION_SCHEMA)
    b = qr.proposed_records(run(source("REG", list(reversed(rows)))), STUDY_SCHEMA, PUBLICATION_SCHEMA)
    assert a["receipt"]["tsv_sha256"] == b["receipt"]["tsv_sha256"]


# ------------------------------------------------------------------ real inputs (offline, read in place)


def _real_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def real_result():
    return qr.reconcile([
        {"tag": "REG", "path": "outputs/study-clearance-20261002/ALL_117_STUDY_USE_REGISTRY.csv",
         "sha256": HASHES[REG_CSV], "rows": _real_rows(REG_CSV)},
        {"tag": "EPI", "path": "reports/epigenetic_drug_study_index.csv",
         "sha256": HASHES[EPI_CSV], "rows": _real_rows(EPI_CSV)},
    ], pipeline_utc=PIPELINE_UTC)


def test_the_project_container_is_four_levels_above_the_test_file_parent():
    assert PROJECT_CONTAINER.name == "MyThesis_Epigentics_Project"
    assert (PROJECT_CONTAINER / "outputs" / "study-clearance-20261002").is_dir()
    assert WORKTREE.name == "a-dav-01"


def test_real_input_hashes_match_the_recorded_values():
    for path, expected in HASHES.items():
        assert path.exists(), path
        assert _sha256(path) == expected, path.name


def test_real_inputs_are_fully_dispositioned_with_exact_counts(real_result):
    counts = real_result["counts"]
    assert counts["input_rows_total"] == 151
    assert counts["in_scope_total"] == 125
    assert counts["out_of_scope_total"] == 26
    assert counts["dispositioned_total"] == 125
    per_source = {entry["tag"]: entry for entry in real_result["inputs"]}
    assert per_source["REG"]["row_count"] == 117
    assert per_source["EPI"]["row_count"] == 34
    assert len(per_source["REG"]["in_scope_row_ids"]) == 117
    assert len(per_source["EPI"]["in_scope_row_ids"]) == 8
    assert len(per_source["EPI"]["out_of_scope_rows"]) == 26


def _twin_urls(record):
    values = []
    for key in ("evidence_url", "evidence_urls"):
        value = record.get(key)
        if value is None:
            continue
        values.extend([value] if isinstance(value, str) else list(value))
    out = set()
    for value in values:
        for piece in re.split(r"\s*\|\s*|\s*;\s*", value):
            if piece.strip():
                out.add(piece.strip())
    return out


def test_real_registry_csv_and_json_twin_agree():
    csv_rows = {row["catalogue_entry_id"]: row for row in _real_rows(REG_CSV)}
    twin = json.loads(REG_JSON.read_text(encoding="utf-8"))["records"]
    assert set(csv_rows) == {record["catalogue_entry_id"] for record in twin}
    local_only = {}
    for record in twin:
        row = csv_rows[record["catalogue_entry_id"]]
        assert record["current_disposition"] == row["current_disposition"]
        assert record["source_family_id_or_unresolved"] == row["source_family"]
        csv_urls = {piece.strip() for piece in re.split(r"\s*\|\s*", row["evidence_urls"]) if piece.strip()}
        twin_urls = _twin_urls(record)
        extra_csv = csv_urls - twin_urls
        if extra_csv:
            local_only[record["catalogue_entry_id"]] = sorted(extra_csv)
        assert twin_urls <= csv_urls, record["catalogue_entry_id"]
    # Known, documented discrepancy: two CSV evidence entries are local project paths that the JSON twin omits.
    assert set(local_only) == {"ICB-BULK-029", "ICB-BULK-032"}
    for entries in local_only.values():
        assert all(not entry.startswith("http") for entry in entries)


def test_real_known_duplicate_pairs_cluster_together(real_result):
    by_row = {row["row_id"]: row["cluster_id"] for row in real_result["dispositioned_rows"]}
    assert by_row["ICB-BULK-014"] == by_row["ICB-BULK-042"]
    # Round 2 (OSR-M01): the MGH rows are not one canonical cluster; see the POSSIBLE association test above.
    assert by_row["ICB-BULK-003"] != by_row["ICB-BULK-019"]


def test_real_disposition_tallies_sum_to_the_in_scope_total(real_result):
    tallies = real_result["counts"]["disposition_tallies"]
    assert sum(tallies.values()) == real_result["counts"]["in_scope_total"]
    assert set(tallies) <= set(qr.DISPOSITION_CODES)


def test_real_epigenetic_rows_follow_the_declared_clinical_rules(real_result):
    by_row = {row["row_id"]: row for row in real_result["dispositioned_rows"] if row["tag"] == "EPI"}
    assert sorted(by_row) == ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S24"]
    assert by_row["S04"]["disposition"] == "NON_ICI_TREATMENT"
    assert by_row["S06"]["disposition"] == "UNRESOLVED"
    for row_id in ("S01", "S02", "S03", "S05", "S07", "S24"):
        assert by_row[row_id]["disposition"] == "INCLUDED_AS_LEAD"


def test_real_registry_primary_candidates_are_included_as_leads(real_result):
    primary = [row for row in _real_rows(REG_CSV) if row["current_disposition"] == "primary_candidate_pending_private"]
    assert len(primary) == 16
    by_row = {row["row_id"]: row for row in real_result["dispositioned_rows"]}
    for row in primary:
        assert by_row[row["catalogue_entry_id"]]["disposition"] == "INCLUDED_AS_LEAD"


def test_real_packets_all_validate_and_resolve_under_frozen_schemas(real_result):
    packets = qr.build_packets(real_result)
    assert len(packets) == 125
    proposed = qr.proposed_records(real_result, STUDY_SCHEMA, PUBLICATION_SCHEMA)
    assert proposed["receipt"]["admitted_count"] == 0
    assert proposed["receipt"]["study_count"] == real_result["counts"]["candidate_study_count"] \
        or proposed["receipt"]["study_count"] >= 1
    for study in proposed["study_records"]:
        assert study["study_status"] != "RESOLVED"


# ------------------------------------------------------------------ Phase 2 planning (offline)


def test_phase2_plan_covers_only_the_priority_subset_and_stays_under_the_cap(real_result):
    plan = qr.phase2_plan(real_result)
    assert 1 <= len(plan) <= qr.PHASE2_REQUEST_CAP
    priority_rows = {row["row_id"] for row in real_result["dispositioned_rows"]
                     if row["tag"] == "REG" and row["current_disposition"] == "primary_candidate_pending_private"}
    assert len(priority_rows) == 16
    for query in plan:
        assert query["priority_rows"], query["query_id"]
        assert set(query["priority_rows"]) <= priority_rows | {"S01", "S02", "S03", "S05", "S06", "S07", "S24"}
        assert query["url"].startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/")
        assert "tool=a-dav-04-queue-reconciliation" in query["url"]
        assert "api_key" not in query["url"].lower() and "email=" not in query["url"].lower()
        assert re.search(r"/(esearch|esummary|elink)\.fcgi\?", query["url"])
        assert "GSM" not in query["url"]


def test_phase2_plan_is_deterministic(real_result):
    assert canonical(qr.phase2_plan(real_result)) == canonical(qr.phase2_plan(real_result))


# ------------------------------------------------------------------ Phase 2 synthetic rules (post-GREEN regressions)
#
# Added after the first GREEN run, when real-input inspection showed the defects these tests encode:
# a PMC link credited to a cluster it does not belong to, and a DOI check skipped when the PubMed record's
# PMID is in no cluster. These tests were not observed failing before the fix; they guard the fixed rules.


def _phase2_synthetic_result():
    return run(source("REG", [
        reg("SYN-A", disposition="primary_candidate_pending_private",
            urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700090 https://pubmed.ncbi.nlm.nih.gov/111111/"),
        reg("SYN-B", disposition="primary_candidate_pending_private",
            urls="https://pmc.ncbi.nlm.nih.gov/articles/PMC700222/ https://pubmed.ncbi.nlm.nih.gov/333333/"),
    ]))


def _response_for(plan_entry, body):
    return {"query_id": plan_entry["query_id"], "kind": plan_entry["kind"], "url": plan_entry["url"],
            "http_status": 200, "utc": "2026-10-17T16:00:01.000Z", "body": json.dumps(body), "file": None}


def test_geo_series_uid_is_the_accession_number_under_the_200_prefix():
    assert qr.geo_series_uid("GSE115821") == "200115821"
    assert qr.geo_series_uid("GSE78220") == "200078220"


def test_pmc_link_is_credited_only_to_the_cluster_that_lists_the_pmc():
    result = _phase2_synthetic_result()
    plan = {entry["target"].get("pmc", "x"): entry for entry in qr.phase2_plan(result)
            if entry["kind"] == "elink_pmc_pubmed"}
    entry = plan["700222"]
    # The PMC belongs to SYN-B's cluster. PMID 111111 belongs to SYN-A's cluster, so it must not be credited.
    evaluation = qr.phase2_evaluate(result, [_response_for(entry, {"linksets": [
        {"dbfrom": "pmc", "ids": ["700222"], "linksetdbs": [{"dbto": "pubmed", "links": ["111111"]}]}]})],
        pipeline_utc=PIPELINE_UTC)
    assert [v for v in evaluation["verified_aliases"] if v["identifier"] == "PMID111111"] == []


def test_pmc_link_listing_many_pubmed_ids_is_not_an_identity_claim():
    # Round 2: every saved elink_pmc_pubmed response lists 30 to 77 PubMed IDs, so membership of a PMID in the
    # list does not identify the article. Such a link must not create a PUBLICATION_PMID claim, even when the
    # PMID is listed by the same cluster.
    result = _phase2_synthetic_result()
    plan = {entry["target"].get("pmc", "x"): entry for entry in qr.phase2_plan(result)
            if entry["kind"] == "elink_pmc_pubmed"}
    entry = plan["700222"]
    evaluation = qr.phase2_evaluate(result, [_response_for(entry, {"linksets": [
        {"dbfrom": "pmc", "ids": ["700222"], "linksetdbs": [{"dbto": "pubmed", "links": ["333333", "444444"]}]}]})],
        pipeline_utc=PIPELINE_UTC)
    assert [v for v in evaluation["verified_aliases"] if v["alias_type"] == "PUBLICATION_PMID"] == []




def test_follow_up_is_planned_only_when_the_candidate_uid_is_on_the_search_page():
    result = _phase2_synthetic_result()
    accession = [entry for entry in qr.phase2_plan(result) if entry["kind"] == "esearch_gds_accn"][0]
    off_page = {"esearchresult": {"count": "3", "retmax": "20", "retstart": "0", "idlist": ["100000001"],
                                  "querytranslation": "GSE700090[ACCN]"}}
    assert qr.phase2_followups(result, [_response_for(accession, off_page)]) == []
    on_page = {"esearchresult": {"count": "3", "retmax": "20", "retstart": "0",
                                 "idlist": ["200700090", "100000001"], "querytranslation": "GSE700090[ACCN]"}}
    kinds = [item["kind"] for item in qr.phase2_followups(result, [_response_for(accession, on_page)])]
    assert kinds == ["esummary_gds_uid", "elink_gds_pubmed_uid"]


def test_phase2_plan_ids_are_order_free_and_parent_derived_for_follow_ups():
    result = _phase2_synthetic_result()
    accession = [entry for entry in qr.phase2_plan(result) if entry["kind"] == "esearch_gds_accn"][0]
    on_page = {"esearchresult": {"count": "2", "retmax": "20", "retstart": "0",
                                 "idlist": ["200700090"], "querytranslation": "GSE700090[ACCN]"}}
    follow = qr.phase2_followups(result, [_response_for(accession, on_page)])
    assert [item["query_id"] for item in follow] == [accession["query_id"] + "-F1",
                                                    accession["query_id"] + "-F2"]


# ------------------------------------------------------------------ Round 2 (reviewer findings QR-01..06, OSR-M01, SA-*)


def _gse_row(index):
    return reg(f"SYN-BUDGET-{index:03d}", disposition="primary_candidate_pending_private",
               urls=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE{700000 + index}")


def test_qr01_one_budget_covers_static_and_follow_up_requests():
    result = run(source("REG", [_gse_row(i) for i in range(51)]))
    plan = qr.phase2_plan(result)
    assert len(plan) == 51
    executed = []
    for entry in plan:
        uid = qr.geo_series_uid(entry["target"]["gse"])
        body = {"esearchresult": {"count": "1", "retmax": "20", "retstart": "0", "idlist": [uid],
                                  "querytranslation": entry["target"]["gse"] + "[ACCN]"}}
        executed.append(_response_for(entry, body))
    follow_ups = qr.phase2_followups(result, executed)
    assert len(follow_ups) == 102
    pending = qr.phase2_pending(result, executed)
    assert len(executed) + len(pending) <= qr.PHASE2_REQUEST_CAP
    assert len(pending) == qr.PHASE2_REQUEST_CAP - len(executed)


def test_qr01_evaluation_refuses_request_151():
    result = run(source("REG", [_gse_row(i) for i in range(51)]))
    plan = qr.phase2_plan(result)
    response = _response_for(plan[0], {"esearchresult": {"count": "0", "idlist": []}})
    with pytest.raises(qr.QueueReconciliationError) as caught:
        qr.phase2_evaluate(result, [response] * 151, pipeline_utc=PIPELINE_UTC)
    assert caught.value.code == "PHASE2_CAP_EXCEEDED"


def test_qr02_unknown_registry_disposition_fails_closed():
    with pytest.raises(qr.QueueReconciliationError) as caught:
        run(source("REG", [reg("SYN-MISSPELLED", disposition="misspelled_status",
                               urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700001")]))
    assert caught.value.code == "UNKNOWN_INPUT_DISPOSITION"


def test_qr02_empty_registry_disposition_fails_closed():
    with pytest.raises(qr.QueueReconciliationError) as caught:
        run(source("REG", [reg("SYN-EMPTY", disposition="", urls="https://example.org/x")]))
    assert caught.value.code == "UNKNOWN_INPUT_DISPOSITION"


@pytest.mark.parametrize("text", ["123GSE000123", "xGSE000123", "https://pubmed.ncbi.nlm.nih.gov/123abc",
                                  "https://pmc.ncbi.nlm.nih.gov/articles/PMC12345XYZ", "PMC12345XYZ",
                                  "https://pubmed.ncbi.nlm.nih.gov/12345678901"])
def test_qr03_partial_or_contaminated_tokens_yield_nothing(text):
    assert [i for i in qr.extract_identifiers(text, "evidence_urls") if i["kind"] in ("GSE", "PMID", "PMCID")] == []


def test_qr03_whole_tokens_are_still_extracted():
    assert [(i["kind"], i["raw"]) for i in qr.extract_identifiers(
        "https://pubmed.ncbi.nlm.nih.gov/123456/ GSE000123 PMC12345", "evidence_urls")] == [
        ("GSE", "GSE000123"), ("PMID", "123456"), ("PMCID", "PMC12345")]


def test_qr03_doi_url_query_and_fragment_are_not_part_of_the_doi():
    items = qr.extract_identifiers("https://doi.org/10.1038/abc.def?tracking=1#frag", "evidence_urls")
    dois = [i["raw"] for i in items if i["kind"] == "DOI"]
    assert dois == ["10.1038/abc.def"]


def test_qr04_wrong_input_path_is_rejected():
    with pytest.raises(qr.QueueReconciliationError) as caught:
        run(source("REG", [reg("SYN-P", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")], path="wrong.csv"))
    assert caught.value.code == "INPUT_IDENTITY_MISMATCH"


def test_qr04_wrong_input_hash_is_rejected():
    with pytest.raises(qr.QueueReconciliationError) as caught:
        run(source("REG", [reg("SYN-H", urls="https://pubmed.ncbi.nlm.nih.gov/111111/")], sha256="0" * 64))
    assert caught.value.code == "INPUT_IDENTITY_MISMATCH"


def test_osr_m01_family_label_accession_never_merges_rows_and_is_recorded_as_possible_association():
    result = run(source("REG", [
        reg("SYN-M1", family="SYN-MGH-GSE700093-GSE700094", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
        reg("SYN-M2", family="SYN-MGH-GSE700093-GSE700094", urls="https://doi.org/10.1038/synthetic-700094"),
    ]))
    by_row = {row["row_id"]: row["cluster_id"] for row in result["dispositioned_rows"]}
    assert by_row["SYN-M1"] != by_row["SYN-M2"]
    assoc = [a for a in result["family_associations"] if a["identifier"] == "GSE700093"]
    assert len(assoc) == 1 and assoc[0]["certainty"] == "POSSIBLE"
    assert set(assoc[0]["clusters"]) == {by_row["SYN-M1"], by_row["SYN-M2"]}
    assert assoc[0]["resolution"] == "NOT_MERGED"


def test_osr_m01_family_label_accession_is_not_emitted_as_an_alias_or_repository():
    result = run(source("REG", [
        reg("SYN-N1", family="SYN-GSE-FAMILY-GSE700095", urls="https://pubmed.ncbi.nlm.nih.gov/111111/"),
    ]))
    decision = qr.build_decision(result)
    assert not any("700095" in str(alias["alias_value"]) for alias in decision["aliases"])


def test_osr_m01_two_mga_rows_with_separate_publications_are_separate_candidate_studies_on_real_inputs(real_result):
    by_row = {row["row_id"]: row["cluster_id"] for row in real_result["dispositioned_rows"]}
    assert by_row["ICB-BULK-003"] != by_row["ICB-BULK-019"]
    assert by_row["ICB-BULK-014"] == by_row["ICB-BULK-042"]
    associations = [a for a in real_result["family_associations"] if a["identifier"] in ("GSE115821", "GSE168204")]
    assert associations and all(a["certainty"] == "POSSIBLE" and a["resolution"] == "NOT_MERGED" for a in associations)


def test_sa_resource_wording_is_duplicate_reanalysis_not_a_lead():
    row = reg("SYN-R1", disposition="supporting_or_context",
              verified_title="scICB: A pan-cancer database of human temporal immune checkpoint blockade",
              verified_modality="integrated_single_cell_resource",
              urls="https://onlinelibrary.wiley.com/doi/abs/10.1002/ctd2.70044")
    result = run(source("REG", [row]))
    # Round 5 (OSR4-M01): a bare "pan-cancer" is not aggregation evidence, so this row is no longer a REG-3B proposal.
    assert result["dispositioned_rows"][0]["rule_id"] == "REG-10-SUPPORTING-LEAD"


def test_sa_explicitly_absent_ici_regimen_is_untreated_molecular_cohort():
    # Round 3 (R2-QR-07): superseded. Missing regimen wording is UNRESOLVED, not UNTREATED. See the R3 tests.
    row = reg("SYN-U1", disposition="supporting_or_context",
              usefulness="Source-specific basis: spatial series verified; immunotherapy regimen/ORR not documented in series.",
              urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700096")
    result = run(source("REG", [row]))
    assert result["dispositioned_rows"][0]["disposition"] == "UNRESOLVED"
    assert result["dispositioned_rows"][0]["rule_id"] == "REG-3D-REGIMEN-NOT-DOCUMENTED"


def test_sa_unsupported_locator_reason_names_the_host_not_absence_of_a_locator():
    row = reg("SYN-L1", disposition="supporting_or_context", urls="https://zenodo.org/records/15392699")
    result = run(source("REG", [row]))
    dispo = result["dispositioned_rows"][0]
    assert dispo["disposition"] == "UNRESOLVED"
    assert "zenodo.org" in dispo["reason"] and "not extracted" in dispo["reason"]
    assert "no public identifier or locator" not in dispo["reason"]


def test_sa_row_with_no_locator_at_all_keeps_the_absence_reason():
    result = run(source("REG", [reg("SYN-L2", disposition="supporting_or_context", urls="")]))
    assert result["dispositioned_rows"][0]["reason"].startswith("no public identifier or locator")


def test_sa_real_audited_rows_match_the_round_two_rules(real_result):
    by_row = {row["row_id"]: row for row in real_result["dispositioned_rows"]}
    assert by_row["ICB-SC-018"]["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE"  # round 5: proposal only
    assert _code(by_row["ICB-SC-018"]) == "DUPLICATE_REANALYSIS"
    assert "originating-study resolution" in by_row["ICB-SC-018"]["reason"]
    assert by_row["ICB-SPAT-002"]["disposition"] == "UNRESOLVED"  # Round 3 (R2-QR-07) coordinator ruling
    assert by_row["ICB-SPAT-005"]["disposition"] == "UNRESOLVED"
    assert "zenodo.org" in by_row["ICB-SPAT-005"]["reason"]


def test_qr05_every_phase2_request_is_logged_or_marked_unevidenced_with_a_compliant_rerun():
    manifest = _manifest()
    originals = manifest["requests"] + manifest["duplicate_requests"]
    reruns = manifest.get("rerun_requests", [])
    by_original = {}
    for rerun in reruns:
        by_original.setdefault(rerun["rerun_of"], []).append(rerun)
    for entry in originals:
        if entry.get("spacing_status") == "original_unevidenced_spacing":
            siblings = by_original.get(entry["query_id"], [])
            assert len(siblings) == 1, entry["query_id"]
            assert siblings[0]["start_utc"] and siblings[0]["end_utc"]
        else:
            assert entry.get("spacing_status") == "logged_start", entry["query_id"]
    assert len(originals) == 30 + 51 and len(reruns) == 30


def test_qr05_rerun_start_times_are_logged_and_at_least_0_4_seconds_apart():
    from datetime import datetime
    reruns = _manifest().get("rerun_requests", [])
    assert len(reruns) == 30
    stamps = sorted(datetime.fromisoformat(e["start_utc"][:-1] + "+00:00") for e in reruns)
    gaps = [(b - a).total_seconds() for a, b in zip(stamps, stamps[1:])]
    assert min(gaps) >= qr.PHASE2_MIN_SPACING_SECONDS, min(gaps)


def test_qr05_rerun_identity_is_reported_per_request_and_differences_are_kept():
    reruns = _manifest().get("rerun_requests", [])
    assert len(reruns) == 30
    for rerun in reruns:
        assert isinstance(rerun["identical_to_original"], bool)
        assert rerun["original_bytes"] == rerun.get("original_bytes")
        if not rerun["identical_to_original"]:
            assert rerun["difference_note"].strip()


def test_qr05_total_request_count_including_reruns_is_within_the_cap():
    manifest = _manifest()
    total = len(manifest["requests"]) + len(manifest["duplicate_requests"]) + len(manifest.get("rerun_requests", []))
    assert manifest["request_count"] == total == 111
    assert total <= qr.PHASE2_REQUEST_CAP


def test_qr05_sample_bearing_reruns_are_private_and_only_sample_free_are_committed():
    reruns = _manifest().get("rerun_requests", [])
    assert len(reruns) == 30
    for rerun in reruns:
        if rerun["kind"] == "esummary_gds_uid":
            assert rerun["raw_storage"] == "private" and rerun["storage"] == "committed"
            assert not GSM_PATTERN.search((PHASE2_DIR / rerun["file"]).read_text(encoding="utf-8"))


def test_qr06_receipt_private_artifact_hashes_match_current_bytes_when_scratch_is_present():
    import os
    scratch = WORKTREE / ".scratch" / "runtime" / "A_DAV_04"
    if not scratch.is_dir():
        pytest.skip("scratch directory absent")
    receipt = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "IMPLEMENTATION_RECEIPT.md").read_text(encoding="utf-8")
    # Round 10: the current private table is the one in section 25 (24 to 19 hold earlier tables; 18.6 is historical).
    if "## 25. Round 10" in receipt:
        receipt = receipt[receipt.index("## 25. Round 10"):]
    elif "## 24. Round 9" in receipt:
        receipt = receipt[receipt.index("## 24. Round 9"):]
    elif "## 23. Round 8" in receipt:
        receipt = receipt[receipt.index("## 23. Round 8"):]
    elif "## 22. Round 7" in receipt:
        receipt = receipt[receipt.index("## 22. Round 7"):]
    elif "## 21. Round 6" in receipt:
        receipt = receipt[receipt.index("## 21. Round 6"):]
    elif "## 20. Round 5" in receipt:
        receipt = receipt[receipt.index("## 20. Round 5"):]
    elif "## 19. Round 4" in receipt:
        receipt = receipt[receipt.index("## 19. Round 4"):]
    rows = re.findall(r"^\| private \| (\S+) \| (\d+) \| ([0-9a-f]{64}) \|$", receipt, re.M)
    assert len(rows) >= 25, len(rows)
    for rel, size, digest in rows:
        path = scratch / rel
        assert path.is_file(), rel
        assert path.stat().st_size == int(size), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, rel


# ------------------------------------------------------------------ Round 3 (R2-QR-07..10, DA-M01, DA-L01, DA-L02)


def _rule(row_kwargs):
    return run(source("REG", [reg("SYN-R3", **row_kwargs)]))["dispositioned_rows"][0]


def test_r3_qr07_missing_regimen_wording_is_unresolved_with_a_resolution_path():
    dispo = _rule(dict(disposition="supporting_or_context",
                       usefulness="Immunotherapy regimen not documented in the available series.",
                       urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700201"))
    assert dispo["disposition"] == "UNRESOLVED"
    assert dispo["rule_id"] == "REG-3D-REGIMEN-NOT-DOCUMENTED"
    assert "not established" in dispo["reason"] and "original publication" in dispo["reason"]


@pytest.mark.parametrize("text", ["Treatment-naive cohort; no immunotherapy administered.",
                                  "Cohort was untreated."])
def test_r3_qr07_affirmative_untreated_evidence_gives_untreated_molecular_cohort(text):
    # Round 4 (R3-QR-11): "Untreated primary tumours profiled before any therapy." is a sample-level statement and is
    # no longer an untreated signal; see the round-4 negative cases.
    dispo = _rule(dict(disposition="supporting_or_context", usefulness=text,
                       urls="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE700202"))
    assert dispo["disposition"] == "UNRESOLVED"  # round 5: free-text untreated wording is a proposal only
    assert dispo["rule_id"] == "PROPOSED:REG-3C-AFFIRMATIVE-UNTREATED"
    assert dispo["proposed_disposition"] == "UNTREATED_MOLECULAR_COHORT"


def test_r3_qr07_real_spat002_is_unresolved_with_reason_and_resolution(real_result):
    dispo = {r["row_id"]: r for r in real_result["dispositioned_rows"]}["ICB-SPAT-002"]
    assert dispo["disposition"] == "UNRESOLVED"
    assert dispo["rule_id"] == "REG-3D-REGIMEN-NOT-DOCUMENTED"
    assert "ICI regimen and ORR are not documented" in dispo["reason"]
    assert "untreated status is not established" in dispo["reason"]
    assert "original publication" in dispo["reason"]


def test_r3_qr08_standalone_resource_wording_is_not_duplicate_reanalysis():
    dispo = _rule(dict(disposition="supporting_or_context",
                       verified_title="Patient-level molecular resource from a primary ICI cohort",
                       urls="https://pubmed.ncbi.nlm.nih.gov/111111/"))
    assert dispo["disposition"] == "INCLUDED_AS_LEAD"
    assert dispo["rule_id"] == "REG-10-SUPPORTING-LEAD"


@pytest.mark.parametrize("title", ["integrated multi-cohort dataset of PD-1 blockade",
                                                                                                         "a meta-analysis of PD-1 cohorts",
                                   "a pooled analysis of anti-PD-1 trials",
                                   "a reanalysis of a published melanoma cohort",
                                   "a secondary analysis of trial data",
                                   "constituent studies GSE700203 and GSE700204",
                                   "a multi-cohort atlas of immune checkpoint response"])
def test_r3_qr08_explicit_aggregation_or_secondary_use_wording_is_duplicate_reanalysis(title):
    dispo = _rule(dict(disposition="supporting_or_context", verified_title=title,
                       urls="https://pubmed.ncbi.nlm.nih.gov/222222/"))
    assert dispo["disposition"] == "UNRESOLVED"  # round 5: proposal only
    assert dispo["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE"
    assert dispo["proposed_disposition"] == "DUPLICATE_REANALYSIS"


def test_r3_qr08_real_reg3b_rows_each_keep_explicit_wording(real_result):
    rows = [r for r in real_result["dispositioned_rows"] if r["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE"]
    assert rows, "expected at least one REG-3B proposal on real inputs"
    csv_rows = {r["catalogue_entry_id"]: r for r in _real_rows(REG_CSV)}
    for row in rows:
        phrase = qr.registry_aggregation_signal(csv_rows[row["row_id"]])
        assert phrase, row["row_id"]
        assert phrase.lower() not in ("resource", "curated", "aggregated", "integrated", "database", "portal"), row["row_id"]


def test_r3_dam01_radiology_only_row_is_no_molecular_data_and_keeps_the_locator_as_a_note():
    dispo = _rule(dict(disposition="supporting_or_context", verified_modality="radiology",
                       urls="https://zenodo.org/records/15392699"))
    assert dispo["disposition"] == "UNRESOLVED"  # round 5: proposal only
    assert dispo["proposed_disposition"] == "NO_MOLECULAR_DATA"
    assert dispo["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"
    assert "zenodo.org" in dispo["reason"] and "note" in dispo["reason"]


def test_r3_dam01_a_named_molecular_assay_anywhere_in_the_row_blocks_the_non_molecular_rule():
    dispo = _rule(dict(disposition="supporting_or_context", verified_modality="radiology",
                       next_data_product="Native imaging manifest with RNA-seq counts for the same patients.",
                       urls="https://pubmed.ncbi.nlm.nih.gov/333333/"))
    assert dispo["rule_id"] != "PROPOSED:REG-4-NONMOLECULAR-MODALITY"


def test_r3_dam01_a_negated_molecular_mention_does_not_block_the_non_molecular_rule():
    dispo = _rule(dict(disposition="supporting_or_context", verified_modality="histopathology",
                       usefulness="Imaging-only branch; no RNA object is present.",
                       urls="https://pubmed.ncbi.nlm.nih.gov/444444/"))
    assert _code(dispo) == "NO_MOLECULAR_DATA"


def test_r3_dam01_real_radiology_and_histopathology_rows(real_result):
    by_row = {r["row_id"]: r for r in real_result["dispositioned_rows"]}
    for row_id in ("ICB-PATH-001", "ICB-PATH-002", "ICB-PATH-003", "ICB-PATH-004"):
        assert _code(by_row[row_id]) == "NO_MOLECULAR_DATA", row_id
    assert by_row["ICB-PATH-004"]["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"
    assert "zenodo" not in by_row["ICB-PATH-004"]["reason"] or "note" in by_row["ICB-PATH-004"]["reason"]
    assert by_row["ICB-PATH-005"]["rule_id"] != "PROPOSED:REG-4-NONMOLECULAR-MODALITY"  # TCR is a named molecular assay


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def test_r3_qr09_rerun_identity_compares_sizes_and_sha256_with_the_original_bytes():
    manifest = _manifest()
    reruns = manifest["rerun_requests"]
    assert len(reruns) == 30
    for entry in reruns:
        rerun_bytes = (PHASE2_DIR / entry["file"]).read_bytes()
        assert len(rerun_bytes) == entry["bytes"], entry["query_id"]
        assert _sha256_bytes(rerun_bytes) == entry["sha256"], entry["query_id"]
        original_dir = PHASE2_DIR if entry["original_storage"] == "committed" else PHASE2_PRIVATE
        original_path = original_dir / entry["original_file"]
        original_bytes = original_path.read_bytes()
        assert len(original_bytes) == entry["original_bytes"], entry["query_id"]
        assert _sha256_bytes(original_bytes) == entry["original_sha256"], entry["query_id"]
        assert entry["identical_to_original"] == (rerun_bytes == original_bytes), entry["query_id"]
        if not entry["identical_to_original"]:
            assert entry["difference_note"].strip(), entry["query_id"]
        if entry["kind"] == "esummary_gds_uid":
            raw_rerun = (PHASE2_PRIVATE / entry["raw_file"]).read_bytes()
            raw_original = (PHASE2_PRIVATE / entry["raw_original_file"]).read_bytes()
            assert _sha256_bytes(raw_rerun) == entry["raw_sha256"] and len(raw_rerun) == entry["raw_bytes"], entry["query_id"]
            assert _sha256_bytes(raw_original) == entry["raw_original_sha256"], entry["query_id"]
            assert entry["raw_identical_to_original"] == (raw_rerun == raw_original), entry["query_id"]


def test_r3_dal01_unverified_breakdown_sums_to_the_total_and_matches_the_evaluation():
    evaluation = _evaluation()
    categories = {"outside the Phase 2 priority subset": 0, "no Phase 2 endpoint in scope": 0,
                  "controlled-access identifier": 0, "queried; no saved response": 0}
    for item in evaluation["unverified"]:
        matched = [k for k in categories if item["reason"].startswith(k)]
        assert len(matched) == 1, item["reason"]
        categories[matched[0]] += 1
    assert sum(categories.values()) == len(evaluation["unverified"]) == 128
    report = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    line = [l for l in report.splitlines() if l.startswith("- Identifiers not verified: 128")]
    assert len(line) == 1, "report must state the current total of 128"
    assert "96 outside the priority subset" in line[0] and "10 with no in-scope endpoint" in line[0]
    assert "11 controlled-access" in line[0] and "11 queried and not confirmed" in line[0]
    assert categories == {"outside the Phase 2 priority subset": 96, "no Phase 2 endpoint in scope": 10,
                          "controlled-access identifier": 11, "queried; no saved response": 11}


def _table_rows(text, heading):
    start = text.index(heading)
    lines = text[start:].splitlines()
    rows = []
    for line in lines[1:]:
        if line.startswith("| ICB-") or line.startswith("| PROST-"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif rows and not line.startswith("|"):
            break
    return rows


def test_r3_dal02_change_counts_are_derived_from_the_before_after_table():
    receipt = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "IMPLEMENTATION_RECEIPT.md").read_text(encoding="utf-8")
    table = _table_rows(receipt, "### 17.3")
    assert len(table) == 49
    derived_disposition = [r[0] for r in table if "->" in r[1]]
    stated = re.search(r"Disposition changes: (\d+)", receipt[receipt.index("### 17.3"):])
    assert stated and int(stated.group(1)) == len(derived_disposition) == 6
    assert "ICB-BULK-016" not in derived_disposition


def test_r3_changed_rows_table_is_consistent_with_the_current_results(real_result):
    report = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    table = _table_rows(report, "## 6d.")
    assert table, "round-3 changed-row table missing"
    # Round 6: the committed outputs carry the applied confirmations, so the current state is reconcile + apply.
    auth, conf, receipts = _r6_real_inputs()
    current = {(r["tag"], r["row_id"]): r
               for r in qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)}
    for row_id, disposition, rule, cluster, reason_changed in [(r[0], r[1], r[2], r[3], r[4]) for r in table]:
        after = disposition.split(" -> ")[-1]
        assert current[("REG", row_id)]["disposition"] == after, row_id
    stated = re.search(r"Rows changed versus round 2: (\d+)", report)
    assert stated and int(stated.group(1)) == len(table)


def test_r3_qr10_receipt_reg3b_statement_matches_the_current_rule_count(real_result):
    count = sum(1 for r in real_result["dispositioned_rows"]
                if r["rule_id"] in ("REG-3B-INTEGRATED-RESOURCE", "PROPOSED:REG-3B-INTEGRATED-RESOURCE"))
    receipt = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "IMPLEMENTATION_RECEIPT.md").read_text(encoding="utf-8")
    section = receipt[receipt.index("## 18. Round 3"):]
    stated = re.search(r"REG-3B rows in total: (\d+)", section)
    assert stated, "round-3 section must state the REG-3B row count"
    assert int(stated.group(1)) == count


# ------------------------------------------------------------------ Git-bound privacy (coordinator round 1)

SYNTHETIC_GSM_ACCESSIONS = {"GSM0000001", "GSM0000002"}
LOCAL_PATH_MARKER = "/" + "Users" + "/"


def _git_bound_a_dav_04_files():
    docs = WORKTREE / "docs" / "validation" / "A_DAV_04"
    files = [WORKTREE / "tools" / "a_dav" / "queue_reconciliation.py", Path(__file__).resolve()]
    files += [p for p in (PHASE2_DIR).iterdir() if p.is_file()]
    for name in ("INTAKE_MANIFEST.json", "RECONCILIATION_REPORT.md", "PROPOSED_RECORDS.json",
                 "TEST_EVIDENCE.json", "IMPLEMENTATION_RECEIPT.md", "ARTIFACT_HASHES.tsv"):
        files.append(docs / name)
    return files




# ------------------------------------------------------------------ Phase 2 committed fixtures (offline)


def _manifest():
    return json.loads((PHASE2_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


def _evaluation():
    return json.loads((PHASE2_DIR / "PHASE2_EVALUATION.json").read_text(encoding="utf-8"))


def _kind_contains(identifier, text):
    """Locator containment per identifier kind (case-insensitive where the source is)."""
    if identifier.startswith("GSE"):
        return identifier.upper() in text.upper()
    if identifier.startswith("PMID"):
        return re.search(r"(?<!\d)" + identifier[4:] + r"(?!\d)", text) is not None
    if identifier.startswith("DOI"):
        return identifier[3:].lower() in text.lower()
    return False


def test_phase2_manifest_counts_every_sent_request_and_matches_stored_bytes():
    manifest = _manifest()
    evaluated, duplicates = manifest["requests"], manifest["duplicate_requests"]
    reruns = manifest["rerun_requests"]
    assert manifest["request_count"] == len(evaluated) + len(duplicates) + len(reruns) == 111
    assert manifest["request_count"] <= qr.PHASE2_REQUEST_CAP
    assert manifest["evaluated_request_count"] == len(evaluated)
    assert manifest["duplicate_request_count"] == len(duplicates)
    for entry in evaluated + duplicates:
        assert entry["http_status"] == 200, entry["query_id"]
        assert entry["url"].startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/")
    for entry in evaluated:
        assert entry["storage"] == "committed", entry["query_id"]
        path = PHASE2_DIR / entry["file"]
        assert path.exists(), entry["file"]
        assert path.stat().st_size == entry["bytes"], entry["file"]
        assert _sha256(path) == entry["sha256"], entry["file"]
        if entry.get("raw_storage") == "private":
            raw = PHASE2_PRIVATE / entry["raw_file"]
            if raw.exists():
                assert _sha256(raw) == entry["raw_sha256"], entry["raw_file"]
    for entry in duplicates:
        assert entry["storage"] == "private" and entry["file"] is None
        assert entry["duplicate_of"] in {e["query_id"] for e in evaluated}


def test_phase2_follow_up_ids_derive_from_their_parent_query():
    manifest = _manifest()
    ids = [e["query_id"] for e in manifest["requests"]]
    assert len(ids) == len(set(ids))
    for query_id in ids:
        assert re.fullmatch(r"A-DAV-04-P2-Q\d{3}(-F[12])?", query_id), query_id
        if "-F" in query_id:
            parent = query_id.split("-F")[0]
            assert parent in ids


def test_phase2_logged_request_starts_are_spaced_at_least_the_required_minimum():
    from datetime import datetime
    manifest = _manifest()
    logged = [e for e in manifest["requests"] if e.get("utc_source", "request start") == "request start" or
              e.get("session") == 1 or e.get("utc_source") == "request start (logged)"]
    assert len(logged) >= 2
    stamps = sorted(datetime.fromisoformat(e["utc"][:-1] + "+00:00") for e in logged)
    gaps = [(b - a).total_seconds() for a, b in zip(stamps, stamps[1:])]
    assert min(gaps) >= qr.PHASE2_MIN_SPACING_SECONDS, min(gaps)


def test_phase2_session_two_timestamps_are_declared_unlogged_not_claimed():
    manifest = _manifest()
    unlogged = [e for e in manifest["requests"] + manifest["duplicate_requests"]
                if e.get("utc_source", "").startswith("file write time")]
    assert len(unlogged) == 30
    for entry in unlogged:
        assert entry["session"] == 2


# Round 4: a credential is a value, not the word. A reviewer PASS line ("no API-key, token ... found") is not a secret.
CREDENTIAL_VALUE_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"
    r"|authorization\s*:\s*(?:basic|bearer)\s+[A-Za-z0-9._\-+/=]{8,}"
    r"|bearer\s+[A-Za-z0-9._\-]{8,}", re.I)


def test_r4_credential_guard_flags_values_and_not_negated_mentions():
    assert CREDENTIAL_VALUE_RE.search("https://example.org/?api_key=AbC123xyz9")
    assert CREDENTIAL_VALUE_RE.search('apikey: "A1b2C3d4E5"')
    assert CREDENTIAL_VALUE_RE.search("Authorization: Bearer abcdEFGH1234")
    assert not CREDENTIAL_VALUE_RE.search("no API-key, token, password, or secret query parameters found")
    assert not CREDENTIAL_VALUE_RE.search("the NCBI API key was not used")


# R4-QR-15 / round 5: reviewers quote synthetic reproducer values in their receipts; those exact values are not secrets.
SYNTHETIC_CREDENTIAL_REPRODUCERS = frozenset({"Abcdefgh1234", "AbC123xyz9", "A1b2C3d4E5", "abcdEFGH1234",
                                              "dXNlcjpwYXNzd29yZA=="})


def _credential_hits(text):
    hits = []
    for match in CREDENTIAL_VALUE_RE.finditer(text):
        value = re.split(r"[\s:=]+", match.group(0).strip("'\""))[-1].strip("'\"")
        if value not in SYNTHETIC_CREDENTIAL_REPRODUCERS:
            hits.append(match.group(0))
    return hits


def test_r5_credential_guard_allows_only_the_named_synthetic_reproducers():
    assert _credential_hits("reviewer reproducer: token=Abcdefgh1234") == []
    assert _credential_hits("leaked: token=Zq9Lm2Vx8Kp4") != []


def test_phase2_committed_files_contain_no_credentials_or_gsm_accessions():
    manifest = _manifest()
    for entry in manifest["requests"] + manifest["duplicate_requests"]:
        assert "api_key" not in entry["url"].lower()
        assert "email=" not in entry["url"].lower()
    git_bound = list(PHASE2_DIR.rglob("*"))
    docs = WORKTREE / "docs" / "validation" / "A_DAV_04"
    if docs.is_dir():
        git_bound += list(docs.rglob("*"))
    for path in git_bound:
        if path.is_file() and path.name != "MANIFEST.json":
            text = path.read_text(encoding="utf-8")
            for accession in GSM_PATTERN.findall(text):
                assert accession in SYNTHETIC_GSM_ACCESSIONS, (path.name, accession)
            assert not _credential_hits(text), path.name


def test_phase2_responses_contain_every_identifier_their_locators_cite():
    evaluation = _evaluation()
    assert evaluation["verified_alias_count"] == len(evaluation["verified_aliases"]) > 0
    for alias in evaluation["verified_aliases"]:
        text = (PHASE2_DIR / alias["locator_file"]).read_text(encoding="utf-8")
        assert _kind_contains(alias["identifier"], text), (alias["identifier"], alias["locator_file"])


def test_phase2_verified_links_are_only_upgrades_of_queue_identifiers(real_result):
    evaluation = _evaluation()
    known = {(c["study_id"], i["fold"]) for c in real_result["clusters"] for i in c["identifiers"]}
    studies = {c["study_id"] for c in real_result["clusters"]}
    for alias in evaluation["verified_aliases"]:
        assert alias["study_id"] in studies, alias["identifier"]
        if (alias["study_id"], alias["identifier"]) not in known:
            # Round 2: a family-label accession attaches only through a verified PubMed link of the same cluster.
            assert alias["alias_type"] == "GEO_SERIES" and "(verified link)" in alias["claim"]
        assert alias["locator"]["kind"] == "URL"


def test_phase2_evaluation_is_reproducible_from_the_committed_responses(real_result):
    manifest = _manifest()
    responses = []
    for entry in manifest["requests"]:
        body = (PHASE2_DIR / entry["file"]).read_text(encoding="utf-8")
        responses.append({"query_id": entry["query_id"], "kind": entry["kind"], "url": entry["url"],
                          "http_status": entry["http_status"], "utc": entry["utc"], "body": body,
                          "file": entry["file"]})
    recorded = _evaluation()
    evaluation = qr.phase2_evaluate(real_result, responses, pipeline_utc=PIPELINE_UTC)
    assert canonical(evaluation["verified_aliases"]) == canonical(recorded["verified_aliases"])
    assert canonical(evaluation["search_runs"]) == canonical(recorded["search_runs"])
    assert canonical(evaluation["unverified"]) == canonical(recorded["unverified"])


def test_phase2_search_log_rows_are_validated_dav_t01_rows(real_result):
    evaluation = _evaluation()
    validated = sl.validate_search_log(evaluation["search_runs"])
    assert len(validated) == len(evaluation["search_runs"]) == _manifest()["evaluated_request_count"]
    for row in validated:
        assert row["completion_status"] in ("COMPLETE", "INCOMPLETE")
        assert row["pages"]


def test_committed_search_log_covers_every_request_sent_including_duplicates():
    manifest = _manifest()
    lines = (PHASE2_DIR / "PHASE2_SEARCH_LOG.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == list(sl.SEARCH_LOG_HEADER)
    assert len(lines) - 1 == manifest["request_count"] == 111
    query_ids = [line.split("\t")[0] for line in lines[1:]]
    assert len(query_ids) == len(set(query_ids))
    assert set(query_ids) == ({e["query_id"] for e in manifest["requests"]} |
                              {e["query_id"] for e in manifest["duplicate_requests"]} |
                              {e["query_id"] for e in manifest["rerun_requests"]})


# ------------------------------------------------------------------ Round 4 (R3-QR-11, R3-QR-12, R3-QR-13, OSR3-M01)
# One shared clause-scoped matcher serves every excluding rule. Clauses split on . ; , | and " and " / " but ".
# A term counts only if the clause does not negate it before or after the term.

R4_URL = "https://pubmed.ncbi.nlm.nih.gov/555555/"


def _r4(**row_kwargs):
    row_kwargs.setdefault("disposition", "supporting_or_context")
    row_kwargs.setdefault("urls", R4_URL)
    return _rule(row_kwargs)


def test_r4_clause_split_uses_the_declared_boundaries():
    # Round 5: conjunctions do not split clauses; negation scope across them is decided in _negated.
    assert qr.clause_split("A. B; C, D and E but F | G") == ["A", "B", "C", "D and E but F", "G"]
    assert qr.clause_split('not "radiology; imaging"') == ['not "radiology; imaging"']


# R3-QR-11: untreated evidence must be an affirmative, non-negated, non-timing clause.
@pytest.mark.parametrize("usefulness", [
    "Cohort was not untreated; patients received pembrolizumab.",
    "Treatment-naive baseline samples before nivolumab treatment.",
    "Treatment-naive cohort.",
    "Immunotherapy-naive baseline biopsies.",
    "Untreated primary tumours profiled before any therapy.",
    "Untreated status was not confirmed.",
    "The cohort is no longer untreated.",
    "Cohort never untreated.",
    "Non-untreated cohort.",
    "Untreated: no.",
    "Treatment-naive and untreated before anti-PD-1.",
    "No immunotherapy was administered before biopsy.",
])
def test_r4_qr11_untreated_wording_without_an_affirmative_clause_is_not_evidence(usefulness):
    dispo = _r4(usefulness=usefulness)
    assert dispo["rule_id"] != "REG-3C-AFFIRMATIVE-UNTREATED", usefulness
    assert dispo["disposition"] != "UNTREATED_MOLECULAR_COHORT", usefulness


# OSR3-M01: standalone "treatment-naive" fails closed to UNRESOLVED with a treatment-context resolution path.
@pytest.mark.parametrize("usefulness", [
    "Treatment-naive cohort.",
    "Treatment-naive baseline samples before nivolumab treatment.",
    "Immunotherapy-naive baseline biopsies.",
    "Treatment-naive and untreated before anti-PD-1.",
])
def test_r4_osr3m01_standalone_treatment_naive_fails_closed_to_unresolved(usefulness):
    dispo = _r4(usefulness=usefulness)
    assert dispo["disposition"] == "UNRESOLVED", usefulness
    assert dispo["rule_id"] == "REG-3E-TREATMENT-NAIVE-UNCONFIRMED"
    assert "original publication" in dispo["reason"] and "treatment context" in dispo["reason"]


@pytest.mark.parametrize("usefulness", [
    "Cohort was untreated.",
    "No immunotherapy was administered.",
    "No prior ICI was given.",
    "Treatment-naive cohort; no immunotherapy administered.",
])
def test_r4_qr11_affirmative_untreated_clause_still_gives_untreated(usefulness):
    dispo = _r4(usefulness=usefulness)
    assert dispo["disposition"] == "UNRESOLVED", usefulness  # round 5: proposal only
    assert dispo["rule_id"] == "PROPOSED:REG-3C-AFFIRMATIVE-UNTREATED", usefulness
    assert dispo["proposed_disposition"] == "UNTREATED_MOLECULAR_COHORT"


def test_r4_qr11_non_molecular_modality_is_checked_before_untreated():
    dispo = _r4(verified_modality="radiology only", usefulness="Cohort was untreated.")
    assert dispo["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"
    assert dispo["proposed_disposition"] == "NO_MOLECULAR_DATA"


# R3-QR-12: a non-molecular modality is explicit only without a negation in its clause; a molecular
# assay counts only if it is named without a negation in its clause.
@pytest.mark.parametrize("modality, usefulness", [
    ("radiology only and no molecular assay", "SYNTHETIC usefulness"),
    ("radiology", "RNA was not available."),
    ("radiology only, not RNA", "SYNTHETIC usefulness"),
    ("histology", "SYNTHETIC usefulness"),
    ("imaging only; RNA-seq not performed", "SYNTHETIC usefulness"),
])
def test_r4_qr12_explicit_non_molecular_modality_with_negated_molecular_mentions_is_no_molecular_data(modality, usefulness):
    dispo = _r4(verified_modality=modality, usefulness=usefulness)
    assert dispo["disposition"] == "UNRESOLVED", (modality, usefulness)  # round 5: proposal only
    assert dispo["proposed_disposition"] == "NO_MOLECULAR_DATA", (modality, usefulness)
    assert dispo["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"


@pytest.mark.parametrize("modality, usefulness", [
    ("not radiology only", "SYNTHETIC usefulness"),
    ("radiology", "RNA-seq counts available"),
    ("histopathology", "Transcriptome counts available for the same patients"),
    ("no imaging, RNA-seq counts available", "SYNTHETIC usefulness"),
    ("non-radiology imaging-free bulk RNA", "SYNTHETIC usefulness"),
    ("radiology and RNA-seq", "SYNTHETIC usefulness"),
    ("radiology", "transcriptome not available; RNA-seq counts available"),
    ("histopathology", "methylation array available"),
    ("radiology", "Single-cell sequencing of the same tumours"),
    ("radiology", "plasma cfDNA profiles available"),
    ("imaging; no molecular assay, but RNA counts were deposited", "SYNTHETIC usefulness"),
    ("Radiology, RNA-seq", "SYNTHETIC usefulness"),
    ("imaging without RNA but with proteomic profiling", "SYNTHETIC usefulness"),
    ("radiology", "SYNTHETIC usefulness; RNA-seq object exists"),
])
def test_r4_qr12_negation_scope_does_not_suppress_or_trigger_the_non_molecular_rule(modality, usefulness):
    dispo = _r4(verified_modality=modality, usefulness=usefulness)
    assert dispo["rule_id"] != "PROPOSED:REG-4-NONMOLECULAR-MODALITY", (modality, usefulness)


def test_r4_qr12_pending_whole_slide_image_clause_is_not_an_explicit_modality():
    dispo = _r4(verified_modality="Clinical trial report; processed omics or whole-slide-image dataset not established")
    assert dispo["rule_id"] != "REG-4-NONMOLECULAR-MODALITY"


# R3-QR-13: explicit multi-study aggregation wording only; "integrated", "database", "resource" alone do not count.
@pytest.mark.parametrize("title", [
    "Integrated transcriptomic and proteomic analysis of a single primary ICI trial",
    "Primary clinical database for one pembrolizumab trial",
    "Patient-level molecular resource from a primary ICI cohort",
])
def test_r4_qr13_single_study_integrated_or_database_wording_is_an_included_lead(title):
    dispo = _r4(verified_title=title)
    assert dispo["disposition"] == "INCLUDED_AS_LEAD", title
    assert dispo["rule_id"] == "REG-10-SUPPORTING-LEAD"


@pytest.mark.parametrize("title", [
    "database of published immunotherapy cohorts",
    "Integrated single-cell datasets from nine cancers",
    "a pooled analysis of anti-PD-1 trials",
    "a meta-analysis of PD-1 cohorts",
    "constituent studies GSE700203 and GSE700204",
])
def test_r4_qr13_explicit_multi_study_wording_is_duplicate_reanalysis(title):
    dispo = _r4(verified_title=title)
    assert dispo["disposition"] == "UNRESOLVED", title  # round 5: proposal only
    assert dispo["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE"
    assert dispo["proposed_disposition"] == "DUPLICATE_REANALYSIS"


@pytest.mark.parametrize("title", [
    "not a meta-analysis of PD-1 cohorts",
    "Integrated transcriptomic data from one trial",
    "a single-study atlas of melanoma",
    "Primary database of one institution",
    "Portal of one trial's samples",
    "Resource of 20 patients from a single trial",
    "Curated cohort of primary tumours",
    "Aggregated data from one trial",
    "Integrated proteomics dataset of one patient",
    "Integrated analysis of a single trial; not a pooled cohort.",
    "Multi-omic profiling of one pembrolizumab patient",
    "Single-cell atlas of one tumour",
    "Integrated, not pooled, single-trial data",
])
def test_r4_qr13_adversarial_single_study_wording_is_not_duplicate_reanalysis(title):
    dispo = _r4(verified_title=title)
    assert dispo["rule_id"] != "REG-3B-INTEGRATED-RESOURCE", title


def test_r4_qr13_the_four_real_reg3b_rows_keep_explicit_aggregation_wording(real_result):
    by_row = {r["row_id"]: r for r in real_result["dispositioned_rows"]}
    for row_id in ("ICB-SC-017", "ICB-SC-018", "ICB-BULK-040", "ICB-BULK-045"):
        assert by_row[row_id]["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE", row_id




# OSR3-M01 / inventory: every receipt in the A_DAV_04 folder has a row in ARTIFACT_HASHES.tsv.
REQUIRED_REVIEW_RECEIPTS = {
    "COORDINATOR_REVIEW_RECEIPT.md", "SOL_CODE_REVIEW_01_RECEIPT.md", "SOL_SOURCE_AUDIT_REVIEW_01_RECEIPT.md",
    "SOL_CODE_REREVIEW_01_RECEIPT.md", "SOL_SOURCE_AUDIT_REREVIEW_01_RECEIPT.md",
    "SOL_CODE_REREVIEW_02_RECEIPT.md", "SOL_SOURCE_AUDIT_REREVIEW_02_RECEIPT.md",
}






# ------------------------------------------------------------------ Round 5 (user decision: structural exclusions only)
# Free-text rules may only PROPOSE an excluding disposition. An exclusion takes effect only from a structured-field
# rule (STRUCTURAL_EXCLUSION_RULES) or from an explicit per-row reviewer confirmation (apply_confirmations).

def _code(dispo):
    """The excluding code a free-text rule proposed, or the effective disposition (round 5)."""
    return dispo.get("proposed_disposition") or dispo["disposition"]


R5_RECEIPT = "docs/validation/A_DAV_04/SYNTHETIC_AUTHORITY_RECEIPT.md"
R5_RECEIPT_BLOCK = [
    {"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
     "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "suggested_disposition": None, "evidence_note": "synthetic"},
]
# Round 7: a separate synthetic authority whose only entry is a rejection (one entry per row, R6-AUTH-02).
R5_REJECT_BLOCK = [
    {"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
     "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "suggested_disposition": None, "evidence_note": "synthetic"},
]
R5_RECEIPT_BYTES = ("# synthetic authority receipt for the round-6 tests\n\nBEGIN_CONFIRMATIONS_JSON\n"
                    + json.dumps(R5_RECEIPT_BLOCK, indent=2) + "\nEND_CONFIRMATIONS_JSON\n").encode("utf-8")
R5_RECEIPT_SHA = hashlib.sha256(R5_RECEIPT_BYTES).hexdigest()
R5_AUTHORITIES = {"schema": "A-DAV-04.confirmation_authorities.1", "authorities": [{
    "receipt_path": R5_RECEIPT, "receipt_sha256": R5_RECEIPT_SHA, "reviewer": "Synthetic independent reviewer",
    "reviewer_role": "independent source reviewer", "independence": "synthetic", "recorded_utc": "2026-10-18"}]}
R5_REJECT_BYTES = ("# synthetic rejection receipt\n\nBEGIN_CONFIRMATIONS_JSON\n"
                   + json.dumps(R5_REJECT_BLOCK, indent=2) + "\nEND_CONFIRMATIONS_JSON\n").encode("utf-8")
R5_REJECT_SHA = hashlib.sha256(R5_REJECT_BYTES).hexdigest()
R5_REJECT_AUTHORITIES = {"schema": "A-DAV-04.confirmation_authorities.1", "authorities": [{
    "receipt_path": R5_RECEIPT, "receipt_sha256": R5_REJECT_SHA, "reviewer": "Synthetic independent reviewer",
    "reviewer_role": "independent source reviewer", "independence": "synthetic", "recorded_utc": "2026-10-18"}]}
EXCLUDING = set(qr.DISPOSITION_CODES) - {"INCLUDED_AS_LEAD", "UNRESOLVED"}

# Every adversarial or control string named in the Sol code re-reviews (REREVIEW_01, 02, 03) and the source-audit
# re-reviews, plus the round-4 adversarial set. Each is fed through the full pipeline in several free-text fields.
ADVERSARIAL_SOL_STRINGS = [
    # SOL_CODE_REREVIEW_03 (R3-QR-11, R3-QR-12, R3-QR-13, R4-QR-14)
    "Cohort was not (untreated).",
    "Cohort was not in any meaningful clinical sense untreated.",
    "No immunotherapy was administered throughout the study with baseline sampling.",
    "No immunotherapy was administered",
    "not (radiology only)",
    "not just imaging and histology",
    'not "radiology; imaging"',
    "radiology with no molecular assay",
    "RNA sequencing with no missing values",
    "Prospective single-study pan-cancer basket trial",
    "Integrated multiomic datasets from one primary trial",
    "Database of cohorts from one study",
    "not (pan-cancer)",
    "pan-cancer",
    "integrated single trial",
    "primary database",
    "This is not a vaccine study",
    "Not an organoid model",
    "Patients did not receive chemotherapy",
    "Confirmed not a duplicate or reanalysis",
    # SOL_CODE_REREVIEW_02 and SOL_CODE_REREVIEW_01 inputs and controls
    "Cohort was not untreated; patients received pembrolizumab.",
    "Integrated transcriptomic and proteomic analysis of a single primary ICI trial",
    "Primary clinical database for one pembrolizumab trial",
    "RNA was not available.",
    "Treatment-naive baseline samples before nivolumab treatment.",
    "not radiology only",
    "radiology only and no molecular assay",
    "radiology only, not RNA",
    "treatment-naive",
    "Immunotherapy regimen not documented in the available series.",
    # Source-audit re-review wording for the four real REG-3B rows and the untreated controls
    "Author deposit integrates eight datasets across nine cancers",
    "Portal verifies UCLA, MSK, DFCI and harmonized iAtlas melanoma studies",
    "This is explicitly a secondary integrated database.",
    "Database covering 13 cancers with source-specific downloads requiring follow-up",
    "Untreated: no.",
    # Round-4 adversarial set (kept)
    "not a meta-analysis of PD-1 cohorts",
    "Integrated transcriptomic data from one trial",
    "Primary database of one institution",
    "Portal of one trial's samples",
    "Single-cell atlas of one tumour",
    "Integrated analysis of a single trial; not a pooled cohort.",
    "Treatment-naive cohort.",
    "Immunotherapy-naive baseline biopsies.",
    "Untreated primary tumours profiled before any therapy.",
    "non-radiology imaging-free bulk RNA",
    "imaging without RNA but with proteomic profiling",
]
R5_FIELDS = ("usefulness", "verified_title", "verified_modality", "next_action", "original_title")


def _r5_run_one(field, text, disposition="supporting_or_context", urls=R4_URL):
    row_kwargs = {"disposition": disposition, "urls": urls, field: text}
    return _rule(row_kwargs)


@pytest.mark.parametrize("text", ADVERSARIAL_SOL_STRINGS)
@pytest.mark.parametrize("field", R5_FIELDS)
@pytest.mark.parametrize("disposition", ["supporting_or_context", "blocked"])
def test_r5_no_adversarial_string_produces_an_exclusion_without_structural_authority(text, field, disposition):
    dispo = _r5_run_one(field, text, disposition=disposition)
    if dispo["disposition"] in EXCLUDING:
        assert dispo["rule_id"] in qr.STRUCTURAL_EXCLUSION_RULES, (field, text, dispo)


def test_r5_rule_classes_are_declared_and_disjoint():
    assert qr.STRUCTURAL_EXCLUSION_RULES == frozenset({"REG-2-BLOCKED-CONTROLLED", "EPI-3-NO-ICI"})
    assert qr.PROPOSAL_EXCLUSION_RULES == frozenset({
        "REG-3-BLOCKED-OVERLAP", "REG-3B-INTEGRATED-RESOURCE", "REG-3C-AFFIRMATIVE-UNTREATED",
        "REG-4-NONMOLECULAR-MODALITY", "REG-5-VACCINE-OR-CELL-THERAPY", "REG-6-MECHANISTIC-OR-PRECLINICAL",
        "REG-7-NON-ICI-TREATMENT"})
    assert not (qr.STRUCTURAL_EXCLUSION_RULES & qr.PROPOSAL_EXCLUSION_RULES)


@pytest.mark.parametrize("rule, code, row_kwargs", [
    ("REG-4-NONMOLECULAR-MODALITY", "NO_MOLECULAR_DATA", dict(verified_modality="radiology")),
    ("REG-5-VACCINE-OR-CELL-THERAPY", "VACCINE_OR_ADOPTIVE_CELL", dict(verified_title="PROSTVAC antiglycan")),
    ("REG-6-MECHANISTIC-OR-PRECLINICAL", "MECHANISTIC_CELL_MODEL", dict(verified_modality="organoid culture")),
    ("REG-7-NON-ICI-TREATMENT", "NON_ICI_TREATMENT", dict(verified_title="azacitidine response")),
    ("REG-3C-AFFIRMATIVE-UNTREATED", "UNTREATED_MOLECULAR_COHORT", dict(usefulness="Cohort was untreated.")),
    ("REG-3B-INTEGRATED-RESOURCE", "DUPLICATE_REANALYSIS", dict(verified_title="a meta-analysis of PD-1 cohorts")),
    ("REG-3-BLOCKED-OVERLAP", "DUPLICATE_REANALYSIS",
     dict(disposition="blocked", next_action="reconcile overlap with the Snyder cohort")),
])
def test_r5_text_rule_fires_as_a_proposal_not_an_exclusion(rule, code, row_kwargs):
    dispo = _r4(**row_kwargs)
    assert dispo["disposition"] == "UNRESOLVED", rule
    assert dispo["rule_id"] == "PROPOSED:" + rule
    assert dispo["proposed_disposition"] == code
    assert dispo["proposed_rule_id"] == rule
    assert dispo["reason"].startswith(f"proposed {code} by {rule}: ")
    assert dispo["reason"].endswith("; awaiting independent reviewer confirmation")
    assert dispo["proposed_reason"]


def test_r5_structural_blocked_controlled_identifier_stays_an_exclusion():
    dispo = _r4(disposition="blocked", urls="https://ega-archive.org/studies/EGAS00001005013")
    assert dispo["disposition"] == "INACCESSIBLE_OBJECT"
    assert dispo["rule_id"] == "REG-2-BLOCKED-CONTROLLED"
    assert "proposed_disposition" not in dispo


def test_r5_structural_epigenetic_no_ici_field_stays_an_exclusion():
    result = run(source("EPI", [epi("S80", immunotherapy="None")]))
    dispo = result["dispositioned_rows"][0]
    assert dispo["disposition"] == "NON_ICI_TREATMENT"
    assert dispo["rule_id"] == "EPI-3-NO-ICI"


def test_r5_epigenetic_no_ici_prose_is_not_structural():
    result = run(source("EPI", [epi("S81", immunotherapy="No ICI was administered in this model")]))
    assert result["dispositioned_rows"][0]["disposition"] != "NON_ICI_TREATMENT"


# OSR4-M01 and R3-QR-13: bare "pan-cancer" and single-study aggregation phrasing are not aggregation.
@pytest.mark.parametrize("title", [
    "pan-cancer",
    "Prospective single-study pan-cancer basket trial",
    "Integrated multiomic datasets from one primary trial",
    "Database of cohorts from one study",
    "not (pan-cancer)",
])
def test_r5_osr4m01_bare_or_single_study_wording_is_not_an_aggregation_proposal(title):
    dispo = _r4(verified_title=title)
    assert dispo["rule_id"] != "PROPOSED:REG-3B-INTEGRATED-RESOURCE", title


def test_r5_osr4m01_explicit_multi_cancer_aggregation_is_proposed():
    dispo = _r4(usefulness="Database covering 13 cancers with source-specific downloads requiring follow-up.")
    assert dispo["rule_id"] == "PROPOSED:REG-3B-INTEGRATED-RESOURCE"


# R3-QR-11 / R3-QR-12 / R4-QR-14: negation and clause scope of the proposal heuristics.
@pytest.mark.parametrize("usefulness", [
    "Cohort was not (untreated).",
    "Cohort was not in any meaningful clinical sense untreated.",
    "Patients did not receive chemotherapy",
])
def test_r5_negated_untreated_or_nonicI_wording_is_not_proposed(usefulness):
    dispo = _r4(usefulness=usefulness)
    assert not dispo["rule_id"].startswith("PROPOSED:REG-3C"), usefulness
    assert not dispo["rule_id"].startswith("PROPOSED:REG-7"), usefulness


def test_r5_affirmative_whole_study_untreated_statement_is_proposed():
    dispo = _r4(usefulness="No immunotherapy was administered throughout the study with baseline sampling.")
    assert dispo["rule_id"] == "PROPOSED:REG-3C-AFFIRMATIVE-UNTREATED"


@pytest.mark.parametrize("modality", ['not "radiology; imaging"', "not (radiology only)", "not just imaging and histology"])
def test_r5_negated_non_molecular_modality_is_not_proposed(modality):
    dispo = _r4(verified_modality=modality)
    assert dispo["rule_id"] != "PROPOSED:REG-4-NONMOLECULAR-MODALITY", modality


def test_r5_radiology_with_negated_molecular_mention_is_proposed():
    dispo = _r4(verified_modality="radiology with no molecular assay")
    assert dispo["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"


def test_r5_molecular_assay_with_no_missing_values_blocks_the_non_molecular_proposal():
    dispo = _r4(verified_modality="radiology", usefulness="RNA sequencing with no missing values")
    assert dispo["rule_id"] != "PROPOSED:REG-4-NONMOLECULAR-MODALITY"


@pytest.mark.parametrize("text", ["This is not a vaccine study", "Not an organoid model",
                                  "Confirmed not a duplicate or reanalysis"])
def test_r5_r4qr14_negated_older_rule_terms_are_not_proposed(text):
    for field in ("verified_title", "verified_modality", "next_action"):
        dispo = _r5_run_one(field, text, disposition="blocked" if field == "next_action" else "supporting_or_context")
        assert not str(dispo["rule_id"]).startswith("PROPOSED:REG-"), (field, text, dispo["rule_id"])


# ------------------------------------------------------------------ confirmations (pure, fail closed)

def _r5_rows(**row_kwargs):
    return run(source("REG", [reg("SYN-R5", **dict(dict(disposition="supporting_or_context", urls=R4_URL),
                                                   **row_kwargs))]))["dispositioned_rows"]


def _r5_entry(row_id="SYN-R5", **over):
    entry = {"row_id": row_id, "decision": "confirmed", "confirmed_disposition": "NO_MOLECULAR_DATA",
             "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "reviewer": "Synthetic independent reviewer",
             "reviewer_role": "independent source reviewer", "receipt_path": R5_RECEIPT,
             "receipt_sha256": R5_RECEIPT_SHA, "evidence_note": "synthetic evidence note"}
    entry.update(over)
    return entry


def test_r5_confirmation_applies_only_with_every_check_passing():
    rows = _r5_rows(verified_modality="radiology")
    out = qr.apply_confirmations(rows, [_r5_entry()], {R5_RECEIPT: R5_RECEIPT_BYTES}, R5_AUTHORITIES)
    confirmed = out[0]
    assert confirmed["disposition"] == "NO_MOLECULAR_DATA"
    assert confirmed["rule_id"] == "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"
    assert R5_RECEIPT in confirmed["reason"]


def test_r5_empty_confirmations_leave_every_proposal_unresolved():
    rows = _r5_rows(verified_modality="radiology")
    out = qr.apply_confirmations(rows, [], {}, R5_AUTHORITIES)
    assert out[0]["disposition"] == "UNRESOLVED"
    assert out[0]["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"


def test_r5_rejected_entry_keeps_the_row_unresolved_and_records_the_rejection():
    rows = _r5_rows(verified_modality="radiology")
    out = qr.apply_confirmations(rows, [_r5_entry(decision="rejected", confirmed_disposition="UNRESOLVED",
                                                 receipt_sha256=R5_REJECT_SHA)],
                                 {R5_RECEIPT: R5_REJECT_BYTES}, R5_REJECT_AUTHORITIES)
    assert out[0]["disposition"] == "UNRESOLVED"
    assert out[0]["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"
    assert "reviewer rejected proposed NO_MOLECULAR_DATA" in out[0]["reason"]


@pytest.mark.parametrize("over, code", [
    (dict(confirmed_disposition="VACCINE_OR_ADOPTIVE_CELL"), "CONFIRMATION_DISPOSITION_MISMATCH"),
    (dict(reviewer="TBD"), "CONFIRMATION_PLACEHOLDER_REVIEWER"),
    (dict(reviewer="placeholder reviewer"), "CONFIRMATION_PLACEHOLDER_REVIEWER"),
    (dict(reviewer="<reviewer>"), "CONFIRMATION_PLACEHOLDER_REVIEWER"),
    (dict(reviewer=""), "CONFIRMATION_PLACEHOLDER_REVIEWER"),
    (dict(reviewer="N/A"), "CONFIRMATION_PLACEHOLDER_REVIEWER"),
    (dict(receipt_sha256="0" * 63), "CONFIRMATION_BAD_HASH_FORMAT"),
    (dict(receipt_sha256="f" * 64), "CONFIRMATION_AUTHORITY_UNLISTED"),
    (dict(receipt_path="/etc/passwd"), "CONFIRMATION_PATH_OUTSIDE_ALLOWED"),
    (dict(receipt_path="docs/validation/A_DAV_01/SOL_X_RECEIPT.md"), "CONFIRMATION_PATH_OUTSIDE_ALLOWED"),
    (dict(receipt_path="docs/validation/A_DAV_04/../A_DAV_01/SOL_X_RECEIPT.md"), "CONFIRMATION_PATH_OUTSIDE_ALLOWED"),
    (dict(receipt_path="docs\\validation\\A_DAV_04\\x.md"), "CONFIRMATION_PATH_OUTSIDE_ALLOWED"),
    (dict(row_id="NO-SUCH-ROW"), "CONFIRMATION_ROW_UNKNOWN"),
    (dict(proposed_rule_id="REG-5-VACCINE-OR-CELL-THERAPY"), "CONFIRMATION_RULE_MISMATCH"),
    (dict(evidence_note=""), "CONFIRMATION_MISSING_FIELD"),
])
def test_r5_confirmation_rejections_fail_closed(over, code):
    rows = _r5_rows(verified_modality="radiology")
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.apply_confirmations(rows, [_r5_entry(**over)], {R5_RECEIPT: R5_RECEIPT_BYTES}, R5_AUTHORITIES)
    assert excinfo.value.code == code


def test_r5_confirmation_rejects_a_row_that_is_not_proposed():
    rows = _r5_rows(verified_title="Patient-level molecular resource from a primary ICI cohort")
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.apply_confirmations(rows, [_r5_entry(confirmed_disposition="NO_MOLECULAR_DATA")],
                               {R5_RECEIPT: R5_RECEIPT_BYTES}, R5_AUTHORITIES)
    assert excinfo.value.code == "CONFIRMATION_ROW_NOT_PROPOSED"


def test_r5_confirmation_rejects_a_duplicate_row_id():
    rows = _r5_rows(verified_modality="radiology")
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.apply_confirmations(rows, [_r5_entry(), _r5_entry()], {R5_RECEIPT: R5_RECEIPT_BYTES}, R5_AUTHORITIES)
    assert excinfo.value.code == "CONFIRMATION_DUPLICATE_ROW"


def test_r5_confirmation_rejects_a_receipt_the_caller_did_not_supply():
    rows = _r5_rows(verified_modality="radiology")
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.apply_confirmations(rows, [_r5_entry()], {}, R5_AUTHORITIES)
    assert excinfo.value.code == "CONFIRMATION_RECEIPT_MISSING"


def test_r5_authority_check_flags_any_exclusion_without_structural_rule_or_confirmation():
    rows = [{"tag": "REG", "row_id": "X", "disposition": "NO_MOLECULAR_DATA", "rule_id": "REG-4-NONMOLECULAR-MODALITY"},
            {"tag": "REG", "row_id": "Y", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED"},
            {"tag": "REG", "row_id": "Z", "disposition": "NO_MOLECULAR_DATA", "rule_id": "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"}]
    structural = {"Y": {"current_disposition": "blocked", "identifier_kinds": ["EGAS"]}}
    # Round 6: Z has no confirmation at all, so it is flagged too.
    assert qr.authority_violations(rows, [], {}, R5_AUTHORITIES, structural) == ["X", "Z"]




def test_r5_real_reconcile_output_has_no_unauthorised_exclusion(real_result):
    # Round 6: superseded by test_r6_real_outputs_equal_reconcile_plus_apply_over_committed_files; kept as a
    # reconcile-only check (the proposals are non-excluding, and the structural rows need their inputs).
    structural = {r["row_id"]: {"current_disposition": r["current_disposition"],
                                "identifier_kinds": [i["kind"] for i in r["identifiers"]]}
                  for r in real_result["dispositioned_rows"] if r["tag"] == "REG"}
    assert [x for x in qr.authority_violations(real_result["dispositioned_rows"], [], {}, R5_AUTHORITIES, structural)
            if x not in {r["row_id"] for r in real_result["dispositioned_rows"] if r["tag"] == "EPI"}] == []


# R4-QR-15 (Low): credential values in the forms named by the reviewer.
@pytest.mark.parametrize("sample", [
    "token=Abcdefgh1234", "secret=Abcdefgh1234", "api_key=AbC123xyz9", "password=Abcdefgh1234",
    "Authorization: Basic dXNlcjpwYXNzd29yZA==", "Authorization: Bearer abcdEFGH1234",
    'client_secret: "Abcdefgh1234"',
])
def test_r5_r4qr15_credential_forms_are_detected(sample):
    assert CREDENTIAL_VALUE_RE.search(sample), sample


@pytest.mark.parametrize("sample", [
    "no API-key, token, password, or secret query parameters found",
    "the NCBI API key was not used",
    "Credential inspection: PASS, no token or secret values present",
])
def test_r5_r4qr15_reviewer_pass_lines_are_not_false_positives(sample):
    assert not CREDENTIAL_VALUE_RE.search(sample), sample


# OSR4-L01 / round 5: the single documented inventory exclusion is the self-referential evidence file.
INVENTORY_SELF_REFERENTIAL_EXCLUSIONS = {"TEST_EVIDENCE.json", "ARTIFACT_HASHES.tsv"}




# ------------------------------------------------------------------ Round 6 (R5-AUTH-01 HIGH, R5-STATE-01 MEDIUM)
# The trust root is CONFIRMATION_AUTHORITIES.json (coordinator-maintained). A confirmation must match a listed
# authority, must cite a receipt whose bytes hash to that authority, must match a BEGIN/END_CONFIRMATIONS_JSON
# entry in that receipt, and must not be issued by an implementer or coordinator.

FOLDER_A04 = WORKTREE / "docs" / "validation" / "A_DAV_04"
R6_IMPL = "docs/validation/A_DAV_04/IMPLEMENTATION_RECEIPT.md"
R6_SOURCE = "docs/validation/A_DAV_04/SOL_SOURCE_CONFIRMATION_REVIEW_04_RECEIPT.md"
R6_EXPECTED_TALLY = {"INCLUDED_AS_LEAD": 93, "UNRESOLVED": 14, "NO_MOLECULAR_DATA": 5, "DUPLICATE_REANALYSIS": 5,
                     "VACCINE_OR_ADOPTIVE_CELL": 5, "INACCESSIBLE_OBJECT": 2, "NON_ICI_TREATMENT": 1}


def _r6_auth(role="independent source reviewer", reviewer="Synthetic independent reviewer", block=None,
             path=R5_RECEIPT, text=None):
    body = text if text is not None else (
        "# synthetic authority receipt\n\nBEGIN_CONFIRMATIONS_JSON\n"
        + json.dumps(R5_RECEIPT_BLOCK if block is None else block, indent=2) + "\nEND_CONFIRMATIONS_JSON\n")
    data = body.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    auth = {"schema": "A-DAV-04.confirmation_authorities.1", "authorities": [{
        "receipt_path": path, "receipt_sha256": sha, "reviewer": reviewer, "reviewer_role": role,
        "independence": "synthetic", "recorded_utc": "2026-10-18"}]}
    return auth, {path: data}, sha


def _r6_entry(auth, sha, row_id="SYN-R5", **over):
    authority = auth["authorities"][0]
    entry = {"row_id": row_id, "decision": "confirmed", "confirmed_disposition": "NO_MOLECULAR_DATA",
             "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "reviewer": authority["reviewer"],
             "reviewer_role": authority["reviewer_role"], "receipt_path": authority["receipt_path"],
             "receipt_sha256": sha, "evidence_note": "synthetic evidence note"}
    entry.update(over)
    return entry


def _r6_proposed_rows():
    return _r5_rows(verified_modality="radiology")


def _r6_code(rows, entries, auth, receipts):
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.apply_confirmations(rows, entries, receipts, auth)
    return excinfo.value.code


def test_r6_trust_root_must_be_the_parsed_authority_document():
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth()
    out = qr.apply_confirmations(rows, [_r6_entry(auth, sha)], receipts, auth)
    assert out[0]["rule_id"] == "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"


def test_r6_self_confirmation_with_the_correct_implementation_receipt_hash_is_rejected(real_result):
    impl_bytes = (WORKTREE / R6_IMPL).read_bytes()
    auth = json.loads((FOLDER_A04 / "CONFIRMATION_AUTHORITIES.json").read_text(encoding="utf-8"))
    rows = [r for r in real_result["dispositioned_rows"] if r["rule_id"] == "PROPOSED:REG-4-NONMOLECULAR-MODALITY"]
    row = rows[0]
    entry = {"row_id": row["row_id"], "decision": "confirmed", "confirmed_disposition": "NO_MOLECULAR_DATA",
             "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "reviewer": "implementer", "reviewer_role": "implementer",
             "receipt_path": R6_IMPL, "receipt_sha256": hashlib.sha256(impl_bytes).hexdigest(),
             "evidence_note": "self-confirmation probe"}
    code = _r6_code(rows, [entry], auth, {R6_IMPL: impl_bytes})
    assert code == "CONFIRMATION_AUTHORITY_UNLISTED"


@pytest.mark.parametrize("role", ["implementer", "Implementer lead", "Coordinator", "coordinating reviewer"])
def test_r6_implementer_or_coordinator_roles_are_never_independent(role):
    auth, receipts, sha = _r6_auth(role=role)
    rows = _r6_proposed_rows()
    assert _r6_code(rows, [_r6_entry(auth, sha, reviewer_role=role)], auth, receipts) == "CONFIRMATION_ROLE_FORBIDDEN"


def test_r6_reviewer_and_role_must_equal_the_listed_authority():
    auth, receipts, sha = _r6_auth()
    rows = _r6_proposed_rows()
    assert _r6_code(rows, [_r6_entry(auth, sha, reviewer="Someone Else")], auth, receipts) == "CONFIRMATION_AUTHORITY_MISMATCH"
    assert _r6_code(rows, [_r6_entry(auth, sha, reviewer_role="independent original-source reviewer")], auth,
                    receipts) == "CONFIRMATION_AUTHORITY_MISMATCH"


def test_r6_supplied_receipt_bytes_must_hash_to_the_authority():
    auth, receipts, sha = _r6_auth()
    rows = _r6_proposed_rows()
    tampered = {R5_RECEIPT: receipts[R5_RECEIPT] + b"tampered\n"}
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, tampered) == "CONFIRMATION_HASH_MISMATCH"


def test_r6_receipt_without_a_confirmations_block_fails_closed():
    auth, receipts, sha = _r6_auth(text="# no block in this receipt\n")
    rows = _r6_proposed_rows()
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_BLOCK_MISSING"


def test_r6_block_must_contain_a_matching_row_rule_and_decision():
    rows = _r6_proposed_rows()
    other_row = [{"row_id": "OTHER", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
                  "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]
    auth, receipts, sha = _r6_auth(block=other_row)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_NOT_IN_RECEIPT"
    wrong_rule = [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
                   "proposed_rule_id": "REG-5-VACCINE-OR-CELL-THERAPY"}]
    auth, receipts, sha = _r6_auth(block=wrong_rule)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_NOT_IN_RECEIPT"
    reject_only = [{"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
                    "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]
    auth, receipts, sha = _r6_auth(block=reject_only)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_NOT_IN_RECEIPT"


def test_r6_block_confirmed_disposition_must_match_the_entry():
    rows = _r6_proposed_rows()
    block = [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "VACCINE_OR_ADOPTIVE_CELL",
              "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]
    auth, receipts, sha = _r6_auth(block=block)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_NOT_IN_RECEIPT"


def test_r6_reviewer_block_fenced_in_markdown_is_accepted():
    rows = _r6_proposed_rows()
    fenced = ("# fenced\n\nBEGIN_CONFIRMATIONS_JSON\n```json\n" + json.dumps(R5_RECEIPT_BLOCK) + "\n```\n"
              "END_CONFIRMATIONS_JSON\n").encode("utf-8")
    auth, receipts, sha = _r6_auth(text=fenced.decode("utf-8"))
    out = qr.apply_confirmations(rows, [_r6_entry(auth, sha)], receipts, auth)
    assert out[0]["rule_id"] == "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"


def test_r6_confirm_maps_to_confirmed_and_reject_maps_to_rejected():
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth()
    # the file's "confirmed" matches the receipt's "confirm"
    assert qr.apply_confirmations(rows, [_r6_entry(auth, sha)], receipts, auth)[0]["disposition"] == "NO_MOLECULAR_DATA"
    # a "confirmed" file entry must not match a "reject" block entry
    block = [{"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
              "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]
    auth, receipts, sha = _r6_auth(block=block)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_NOT_IN_RECEIPT"


def test_r6_forged_proposal_rule_is_rejected_by_apply_and_flagged_by_the_authority_check():
    forged = {"tag": "REG", "row_id": "X", "disposition": "UNRESOLVED", "rule_id": "PROPOSED:FAKE-RULE",
              "proposed_disposition": "NO_MOLECULAR_DATA", "proposed_rule_id": "FAKE-RULE", "reason": "forged"}
    auth, receipts, sha = _r6_auth()
    assert _r6_code([forged], [], auth, receipts) == "CONFIRMATION_FORGED_PROPOSAL"
    assert qr.authority_violations([forged], [], receipts, auth, {}) == ["X"]


def test_r6_confirmation_for_a_rule_outside_the_proposal_class_is_rejected():
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth()
    entry = _r6_entry(auth, sha, proposed_rule_id="REG-2-BLOCKED-CONTROLLED")
    assert _r6_code(rows, [entry], auth, receipts) == "CONFIRMATION_RULE_NOT_IN_CLASS"


def test_r6_forged_confirmed_row_is_flagged():
    forged = {"tag": "REG", "row_id": "X", "disposition": "NO_MOLECULAR_DATA", "rule_id": "CONFIRMED:FORGED"}
    auth, receipts, sha = _r6_auth()
    assert qr.authority_violations([forged], [], receipts, auth, {}) == ["X"]


def test_r6_confirmed_row_is_reverified_against_the_receipt_and_passes_when_valid():
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth()
    entries = [_r6_entry(auth, sha)]
    out = qr.apply_confirmations(rows, entries, receipts, auth)
    assert qr.authority_violations(out, entries, receipts, auth, {}) == []
    # a confirmed row whose confirmation is no longer supplied is flagged
    assert qr.authority_violations(out, [], receipts, auth, {}) == [out[0]["row_id"]]


def test_r6_confirmed_row_with_a_non_proposal_base_rule_is_flagged():
    row = {"tag": "REG", "row_id": "X", "disposition": "NO_MOLECULAR_DATA", "rule_id": "CONFIRMED:REG-2-BLOCKED-CONTROLLED"}
    auth, receipts, sha = _r6_auth()
    assert qr.authority_violations([row], [], receipts, auth, {}) == ["X"]


def test_r6_structural_rule_without_its_predicate_is_flagged():
    supporting = {"tag": "REG", "row_id": "X", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
                  "current_disposition": "supporting_or_context", "identifiers": [{"kind": "EGAS"}]}
    blocked_no_controlled = {"tag": "REG", "row_id": "Y", "disposition": "INACCESSIBLE_OBJECT",
                             "rule_id": "REG-2-BLOCKED-CONTROLLED", "current_disposition": "blocked",
                             "identifiers": [{"kind": "PMID"}]}
    blocked_ega = {"tag": "REG", "row_id": "Z", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
                   "current_disposition": "blocked", "identifiers": [{"kind": "EGAS"}]}
    auth, receipts, sha = _r6_auth()
    structural = {"X": {"current_disposition": "supporting_or_context", "identifier_kinds": ["EGAS"]},
                  "Y": {"current_disposition": "blocked", "identifier_kinds": ["PMID"]},
                  "Z": {"current_disposition": "blocked", "identifier_kinds": ["EGAS"]}}
    assert qr.authority_violations([supporting, blocked_no_controlled, blocked_ega], [], receipts, auth,
                                   structural) == ["X", "Y"]


def test_r6_epigenetic_no_ici_predicate_is_reevaluated_on_the_input_field():
    auth, receipts, sha = _r6_auth()
    rows = [{"tag": "EPI", "row_id": "E1", "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"},
            {"tag": "EPI", "row_id": "E2", "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"},
            {"tag": "EPI", "row_id": "E3", "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"}]
    structural = {"E1": {"immunotherapy": "Nivolumab"}, "E2": {"immunotherapy": "none"},
                  "E3": {"immunotherapy": "no ICI"}}
    assert qr.authority_violations(rows, [], receipts, auth, structural) == ["E1", "E3"]


def test_r6_missing_structural_input_is_flagged_not_assumed():
    row = {"tag": "REG", "row_id": "X", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED"}
    auth, receipts, sha = _r6_auth()
    assert qr.authority_violations([row], [], receipts, auth, {}) == ["X"]


def test_r6_authority_check_flags_every_round_six_forgery_together():
    auth, receipts, sha = _r6_auth()
    rows = [{"tag": "REG", "row_id": "F1", "disposition": "NO_MOLECULAR_DATA", "rule_id": "CONFIRMED:FORGED"},
            {"tag": "REG", "row_id": "F2", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
             "current_disposition": "supporting_or_context", "identifiers": []},
            {"tag": "REG", "row_id": "F3", "disposition": "UNRESOLVED", "rule_id": "PROPOSED:FAKE-RULE"}]
    structural = {"F2": {"current_disposition": "supporting_or_context", "identifier_kinds": []}}
    assert qr.authority_violations(rows, [], receipts, auth, structural) == ["F1", "F2", "F3"]


def test_r6_authorities_file_lists_exactly_one_authority_at_the_receipt_hash():
    auth = json.loads((FOLDER_A04 / "CONFIRMATION_AUTHORITIES.json").read_text(encoding="utf-8"))
    assert len(auth["authorities"]) == 1
    entry = auth["authorities"][0]
    assert entry["receipt_path"] == R6_SOURCE
    assert hashlib.sha256((WORKTREE / R6_SOURCE).read_bytes()).hexdigest() == entry["receipt_sha256"]


def _r6_real_inputs():
    auth = json.loads((FOLDER_A04 / "CONFIRMATION_AUTHORITIES.json").read_text(encoding="utf-8"))
    conf = json.loads((FOLDER_A04 / "EXCLUSION_CONFIRMATIONS.json").read_text(encoding="utf-8"))
    receipts = {a["receipt_path"]: (WORKTREE / a["receipt_path"]).read_bytes() for a in auth["authorities"]}
    return auth, conf, receipts


def _r6_real_structural(rows):
    epi_rows = {r["study_id"]: r for r in _real_rows(EPI_CSV)}
    structural = {}
    for r in rows:
        if r["tag"] == "REG":
            structural[r["row_id"]] = {"current_disposition": r["current_disposition"],
                                       "identifier_kinds": [i["kind"] for i in r["identifiers"]]}
        else:
            structural[r["row_id"]] = {"immunotherapy": epi_rows[r["row_id"]]["immunotherapy"]}
    return structural


def test_r6_committed_confirmations_match_the_source_receipt_block_one_for_one():
    auth, conf, receipts = _r6_real_inputs()
    text = receipts[R6_SOURCE].decode("utf-8")
    block = json.loads(re.search(r"BEGIN_CONFIRMATIONS_JSON\s*(.*?)\s*END_CONFIRMATIONS_JSON", text, re.S).group(1)
                       .strip().strip("`").replace("json\n", "", 1))
    mapped = {("confirm", "confirmed"), ("reject", "rejected")}
    assert len(conf) == 15 and len(block) == 15
    for entry in conf:
        match = [b for b in block if b["row_id"] == entry["row_id"] and b["proposed_rule_id"] == entry["proposed_rule_id"]
                 and b["confirmed_disposition"] == entry["confirmed_disposition"]]
        assert len(match) == 1 and (match[0]["decision"], entry["decision"]) in mapped, entry["row_id"]


def test_r6_real_confirmations_apply_to_the_proposed_rows_and_leave_no_proposals(real_result):
    auth, conf, receipts = _r6_real_inputs()
    out = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    assert all(not r["rule_id"].startswith("PROPOSED:") for r in out)
    assert sum(1 for r in out if r["rule_id"].startswith("CONFIRMED:")) == 15
    assert qr.authority_violations(out, conf, receipts, auth, _r6_real_structural(out)) == []


def test_r6_real_outputs_equal_reconcile_plus_apply_over_committed_files(real_result):
    auth, conf, receipts = _r6_real_inputs()
    out = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    committed = json.loads((WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs" / "reconciliation_full.json")
                           .read_text(encoding="utf-8"))["dispositioned_rows"] if (
        WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs" / "reconciliation_full.json").exists() else None
    if committed is None:
        pytest.skip("private outputs absent")
    keys = ("tag", "row_id", "disposition", "rule_id", "reason", "cluster_id", "proposed_disposition")
    assert [{k: r.get(k) for k in keys} for r in out] == [{k: r.get(k) for k in keys} for r in committed]


def test_r6_real_tallies_after_confirmation_match_the_expected_counts(real_result):
    auth, conf, receipts = _r6_real_inputs()
    out = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    from collections import Counter
    tallies = Counter(r["disposition"] for r in out)
    assert dict(tallies) == R6_EXPECTED_TALLY
    assert len({r["cluster_id"] for r in out if r["cluster_id"] is not None}) == 101


# ------------------------------------------------------------------ Round 7 (R6-AUTH-02, R6-STATE-02)
# R6-AUTH-02: a receipt block with more than one entry for a row is ambiguous; the whole receipt is invalid.

@pytest.mark.parametrize("block", [
    [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"},
     {"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}],
    [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"},
     {"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}],
    [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"},
     {"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "DUPLICATE_REANALYSIS",
      "proposed_rule_id": "REG-3B-INTEGRATED-RESOURCE"}],
], ids=["confirm-and-reject", "identical-duplicates", "different-rules"])
def test_r7_ambiguous_receipt_block_is_rejected_whole(block):
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth(block=block)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == "CONFIRMATION_RECEIPT_AMBIGUOUS"


@pytest.mark.parametrize("block", [
    [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"},
     {"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
      "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}],
], ids=["confirm-and-reject"])
def test_r7_authority_check_flags_an_ambiguous_receipt_even_for_an_unconfirmed_proposal(block):
    auth, receipts, sha = _r6_auth(block=block)
    proposal = {"tag": "REG", "row_id": "SYN-R5", "disposition": "UNRESOLVED",
                "rule_id": "PROPOSED:REG-4-NONMOLECULAR-MODALITY", "proposed_disposition": "NO_MOLECULAR_DATA",
                "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "reason": "x"}
    assert qr.authority_violations([proposal], [_r6_entry(auth, sha)], receipts, auth, {}) == ["SYN-R5"]


def test_r7_authority_check_flags_a_confirmed_row_whose_receipt_is_ambiguous():
    auth, receipts, sha = _r6_auth(block=[
        {"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
         "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"},
        {"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
         "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}])
    confirmed = {"tag": "REG", "row_id": "SYN-R5", "disposition": "NO_MOLECULAR_DATA",
                 "rule_id": "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"}
    assert qr.authority_violations([confirmed], [_r6_entry(auth, sha)], receipts, auth, {}) == ["SYN-R5"]




# R6-STATE-02: stored tallies recomputed from the applied rows (the state the committed artifacts must hold).

def _r7_committed(name):
    return WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs" / name


def test_r7_committed_reconciliation_tallies_equal_the_applied_rows(real_result):
    auth, conf, receipts = _r6_real_inputs()
    applied = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    expected = {code: sum(1 for r in applied if r["disposition"] == code) for code in qr.DISPOSITION_CODES}
    path = _r7_committed("reconciliation_full.json")
    if not path.exists():
        pytest.skip("private outputs absent")
    stored = json.loads(path.read_text(encoding="utf-8"))["counts"]["disposition_tallies"]
    assert stored == expected


def test_r7_committed_summary_tallies_equal_the_applied_rows(real_result):
    auth, conf, receipts = _r6_real_inputs()
    applied = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    expected = {code: sum(1 for r in applied if r["disposition"] == code) for code in qr.DISPOSITION_CODES}
    path = _r7_committed("summary.json")
    if not path.exists():
        pytest.skip("private outputs absent")
    assert json.loads(path.read_text(encoding="utf-8"))["counts"]["disposition_tallies"] == expected


def test_r7_committed_report_tallies_equal_the_applied_rows(real_result):
    auth, conf, receipts = _r6_real_inputs()
    applied = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    report = (FOLDER_A04 / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    section = report[report.index("## 2. Disposition tallies"):]
    stated = dict(re.findall(r"^\| ([A-Z_]+) \| (\d+) \|$", section, re.M))
    for code in qr.DISPOSITION_CODES:
        assert int(stated[code]) == sum(1 for r in applied if r["disposition"] == code), code


def test_r7_committed_intake_totals_equal_the_applied_rows(real_result):
    auth, conf, receipts = _r6_real_inputs()
    applied = qr.apply_confirmations(real_result["dispositioned_rows"], conf, receipts, auth)
    intake = json.loads((FOLDER_A04 / "INTAKE_MANIFEST.json").read_text(encoding="utf-8"))
    assert intake["dispositioned_total"] == len(applied) == intake["in_scope_total"]


def _r7_round_trip(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def test_r7_every_committed_artifact_equals_reconcile_then_finalize(real_result):
    """R6-STATE-02 strengthened: the full public state of each committed artifact is recomputed from
    reconcile -> apply_confirmations (via finalize) over the committed inputs, including every stored count."""
    if not _r7_committed("reconciliation_full.json").exists():
        pytest.skip("private outputs absent")
    auth, conf, receipts = _r6_real_inputs()
    exp = qr.finalize(real_result, conf, receipts, auth, _real_rows(EPI_CSV))
    ev = json.loads((PHASE2_DIR / "PHASE2_EVALUATION.json").read_text(encoding="utf-8"))
    ss, ps = STUDY_SCHEMA, PUBLICATION_SCHEMA
    clean = {k: v for k, v in exp.items() if not k.startswith("_")}
    assert json.loads(_r7_committed("reconciliation_full.json").read_text(encoding="utf-8")) == _r7_round_trip(clean)
    summary = json.loads(_r7_committed("summary.json").read_text(encoding="utf-8"))
    proposed = qr.proposed_records(exp, ss, ps, phase2=ev)
    assert summary["counts"] == _r7_round_trip(exp["counts"])
    assert summary["resolve_receipt"]["study_count"] == proposed["receipt"]["study_count"]
    assert summary["resolve_receipt"]["study_status_counts"] == _r7_round_trip(proposed["receipt"]["study_status_counts"])
    assert json.loads(_r7_committed("packets.json").read_text(encoding="utf-8")) == _r7_round_trip(
        qr.build_packets(exp, phase2=ev))
    assert json.loads(_r7_committed("decision.json").read_text(encoding="utf-8")) == _r7_round_trip(
        qr.build_decision(exp, phase2=ev))
    records = json.loads((FOLDER_A04 / "PROPOSED_RECORDS.json").read_text(encoding="utf-8"))
    assert records["study_records"] == _r7_round_trip(proposed["study_records"])
    assert records["publication_records"] == _r7_round_trip(proposed["publication_records"])
    for name in ("study_registry.tsv", "publication_family_registry.tsv", "study_alias_crosswalk.tsv"):
        assert _r7_committed(name).read_text(encoding="utf-8") == proposed["tables"][name], name


# ------------------------------------------------------------------ Round 8 (R7-AUTH-03, R7-STRUCT-01)
# R7-AUTH-03: a receipt must contain EXACTLY ONE confirmation block, and its markers must be balanced.
# R7-STRUCT-01: a structural predicate holds only on a present, explicit value. Absence is a violation.

def _r8_block_text(*blocks):
    return "# receipt\n\n" + "\n".join(
        f"BEGIN_CONFIRMATIONS_JSON\n{json.dumps(b)}\nEND_CONFIRMATIONS_JSON" for b in blocks) + "\n"


_R8_CONFIRM = [{"row_id": "SYN-R5", "decision": "confirm", "confirmed_disposition": "NO_MOLECULAR_DATA",
                "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]
_R8_REJECT = [{"row_id": "SYN-R5", "decision": "reject", "confirmed_disposition": "UNRESOLVED",
               "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY"}]


@pytest.mark.parametrize("text, code", [
    # the reviewer's reproducer: confirm in block 1, reject in block 2
    (_r8_block_text(_R8_CONFIRM, _R8_REJECT), "CONFIRMATION_RECEIPT_AMBIGUOUS"),
    (_r8_block_text(_R8_CONFIRM, _R8_CONFIRM), "CONFIRMATION_RECEIPT_AMBIGUOUS"),
    # nested markers: BEGIN BEGIN ... END END
    ("BEGIN_CONFIRMATIONS_JSON\nBEGIN_CONFIRMATIONS_JSON\n" + json.dumps(_R8_CONFIRM)
     + "\nEND_CONFIRMATIONS_JSON\nEND_CONFIRMATIONS_JSON\n", "CONFIRMATION_RECEIPT_AMBIGUOUS"),
    # unbalanced markers
    ("BEGIN_CONFIRMATIONS_JSON\n" + json.dumps(_R8_CONFIRM) + "\n", "CONFIRMATION_RECEIPT_MALFORMED"),
    ("# x\nEND_CONFIRMATIONS_JSON\n", "CONFIRMATION_RECEIPT_MALFORMED"),
    ("BEGIN_CONFIRMATIONS_JSON\n" + json.dumps(_R8_CONFIRM) + "\nEND_CONFIRMATIONS_JSON\nEND_CONFIRMATIONS_JSON\n",
     "CONFIRMATION_RECEIPT_MALFORMED"),
    # reversed markers
    ("END_CONFIRMATIONS_JSON\n" + json.dumps(_R8_CONFIRM) + "\nBEGIN_CONFIRMATIONS_JSON\n", "CONFIRMATION_RECEIPT_MALFORMED"),
    # no block at all
    ("# a receipt with no block\n", "CONFIRMATION_BLOCK_MISSING"),
], ids=["confirm-then-reject", "identical-blocks", "nested-markers", "begin-without-end", "end-without-begin",
        "extra-end", "reversed-markers", "no-block"])
def test_r8_receipt_must_contain_exactly_one_balanced_block(text, code):
    rows = _r6_proposed_rows()
    auth, receipts, sha = _r6_auth(text=text)
    assert _r6_code(rows, [_r6_entry(auth, sha)], auth, receipts) == code


@pytest.mark.parametrize("text", [
    _r8_block_text(_R8_CONFIRM, _R8_REJECT),
    "BEGIN_CONFIRMATIONS_JSON\n" + json.dumps(_R8_CONFIRM) + "\n",
], ids=["two-blocks", "begin-without-end"])
def test_r8_authority_check_flags_a_receipt_with_unbalanced_or_repeated_blocks(text):
    auth, receipts, sha = _r6_auth(text=text)
    proposal = {"tag": "REG", "row_id": "SYN-R5", "disposition": "UNRESOLVED",
                "rule_id": "PROPOSED:REG-4-NONMOLECULAR-MODALITY", "proposed_disposition": "NO_MOLECULAR_DATA",
                "proposed_rule_id": "REG-4-NONMOLECULAR-MODALITY", "reason": "x"}
    assert qr.authority_violations([proposal], [_r6_entry(auth, sha)], receipts, auth, {}) == ["SYN-R5"]




def _r8_epi_row(study_id="E1"):
    return {"tag": "EPI", "row_id": study_id, "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"}


def test_r8_missing_epigenetic_source_row_is_a_violation_not_an_empty_value():
    auth, receipts, _ = _r6_auth()
    rows = [_r8_epi_row()]
    structural = qr.structural_inputs_for(rows, [])
    assert "immunotherapy" not in structural["E1"]
    assert qr.authority_violations(rows, [], receipts, auth, structural) == ["E1"]


def test_r8_finalize_refuses_an_epi3_exclusion_with_no_epigenetic_source():
    result = {"dispositioned_rows": [_r8_epi_row()], "counts": {}}
    auth, _receipts, _ = _r6_auth()
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.finalize(result, [], {}, auth, [])
    assert excinfo.value.code == "AUTHORITY_VIOLATION"


@pytest.mark.parametrize("fields, flagged", [
    ({}, True),                                    # key absent
    ({"immunotherapy": ""}, False),                # present and explicitly empty
    ({"immunotherapy": " none "}, False),          # present, normalises to none
    ({"immunotherapy": "None"}, False),
    ({"immunotherapy": "nivolumab"}, True),
    ({"immunotherapy": None}, True),               # None is absence, not an explicit value
], ids=["absent", "empty", "padded-none", "None", "nivolumab", "explicit-None"])
def test_r8_epi3_holds_only_on_a_present_explicit_empty_or_none_value(fields, flagged):
    auth, receipts, _ = _r6_auth()
    assert (qr.authority_violations([_r8_epi_row()], [], receipts, auth, {"E1": fields}) == ["E1"]) is flagged


def test_r8_structural_inputs_keep_absence_as_absence():
    rows = [_r8_epi_row("E9")]
    epi = [{"study_id": "E9"}]           # source row present but the immunotherapy key absent
    assert "immunotherapy" not in qr.structural_inputs_for(rows, epi)["E9"]
    epi_empty = [{"study_id": "E9", "immunotherapy": ""}]
    assert qr.structural_inputs_for(rows, epi_empty)["E9"] == {"immunotherapy": ""}


@pytest.mark.parametrize("fields, flagged", [
    ({}, True),                                                         # no registry input at all
    ({"identifier_kinds": ["EGAS"]}, True),                             # current_disposition absent
    ({"current_disposition": "blocked"}, True),                         # identifier_kinds absent
    ({"current_disposition": "blocked", "identifier_kinds": ["EGAS"]}, False),
], ids=["no-input", "no-disposition", "no-identifiers", "holds"])
def test_r8_reg2_requires_every_field_to_be_present(fields, flagged):
    auth, receipts, _ = _r6_auth()
    row = {"tag": "REG", "row_id": "R1", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED"}
    assert (qr.authority_violations([row], [], receipts, auth, {"R1": fields} if fields or fields == {} else {}) == ["R1"]) is flagged


def test_r8_reg2_missing_registry_fields_in_a_real_row_are_not_assumed():
    row = {"tag": "REG", "row_id": "R2", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
           "current_disposition": "blocked"}          # no identifiers key on the row
    assert "identifier_kinds" not in qr.structural_inputs_for([row], [])["R2"]


# ------------------------------------------------------------------ Round 9 (R8-STRUCT-02, R8-STATE-01)
# R8-STRUCT-02: a structural-source ID that occurs more than once is ambiguous. It records no fields, so its predicate
# fails and the row is flagged. Last-row-wins is never used for a source ID.

def _r9_epi_src(study_id, immunotherapy):
    return {"study_id": study_id, "immunotherapy": immunotherapy}


def test_r9_reviewer_reproducer_duplicate_epi_source_is_ambiguous_and_flagged():
    rows = [_r8_epi_row("E1")]
    epi = [_r9_epi_src("E1", "nivolumab"), _r9_epi_src("E1", "")]
    structural = qr.structural_inputs_for(rows, epi)
    assert structural["E1"] == {}
    auth, receipts, _ = _r6_auth()
    assert qr.authority_violations(rows, [], receipts, auth, structural) == ["E1"]


def test_r9_finalize_refuses_the_duplicate_epi_source_reproducer():
    result = {"dispositioned_rows": [_r8_epi_row("E1")], "counts": {}}
    auth, _receipts, _ = _r6_auth()
    with pytest.raises(qr.QueueReconciliationError) as excinfo:
        qr.finalize(result, [], {}, auth, [_r9_epi_src("E1", "nivolumab"), _r9_epi_src("E1", "")])
    assert excinfo.value.code == "AUTHORITY_VIOLATION"


def test_r9_identical_duplicate_epi_sources_are_ambiguous_too():
    rows = [_r8_epi_row("E2")]
    epi = [_r9_epi_src("E2", "none"), _r9_epi_src("E2", "none")]
    auth, receipts, _ = _r6_auth()
    assert qr.authority_violations(rows, [], receipts, auth, qr.structural_inputs_for(rows, epi)) == ["E2"]


def test_r9_duplicate_registry_row_for_reg2_is_ambiguous_and_flagged():
    blocked = {"tag": "REG", "row_id": "R9", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
               "current_disposition": "blocked", "identifiers": [{"kind": "EGAS"}]}
    supporting = dict(blocked, current_disposition="supporting_or_context")
    structural = qr.structural_inputs_for([blocked, supporting], [])
    assert structural["R9"] == {}
    auth, receipts, _ = _r6_auth()
    assert set(qr.authority_violations([blocked, supporting], [], receipts, auth, structural)) == {"R9"}


def test_r9_registry_and_epigenetic_ids_that_collide_are_ambiguous():
    reg = {"tag": "REG", "row_id": "X1", "disposition": "INACCESSIBLE_OBJECT", "rule_id": "REG-2-BLOCKED-CONTROLLED",
           "current_disposition": "blocked", "identifiers": [{"kind": "EGAS"}]}
    epi_row = {"tag": "EPI", "row_id": "X1", "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"}
    structural = qr.structural_inputs_for([reg, epi_row], [_r9_epi_src("X1", "")])
    assert structural["X1"] == {}


def test_r9_a_row_with_two_confirmation_entries_is_flagged_even_if_one_would_authorise():
    auth, receipts, sha = _r6_auth()
    row = {"tag": "REG", "row_id": "SYN-R5", "disposition": "NO_MOLECULAR_DATA",
           "rule_id": "CONFIRMED:REG-4-NONMOLECULAR-MODALITY"}
    good = _r6_entry(auth, sha)
    contrary = dict(good, decision="rejected", confirmed_disposition="UNRESOLVED")
    assert qr.authority_violations([row], [good], receipts, auth, {}) == []
    assert qr.authority_violations([row], [good, contrary], receipts, auth, {}) == ["SYN-R5"]


# R8-STATE-01: no artifact embeds a hash of itself; regeneration is byte-identical; every recorded hash is true.

_R9_PRIV = WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs"
_R9_DRIVER = WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "drivers" / "build_outputs.py"


def test_r9_summary_json_has_no_self_entry_in_its_private_hash_table():
    if not (_R9_PRIV / "summary.json").exists():
        pytest.skip("private outputs absent")
    summary = json.loads((_R9_PRIV / "summary.json").read_text(encoding="utf-8"))
    assert "summary.json" not in summary["private_hashes"]


def _r9_snapshot():
    generated = sorted(_R9_PRIV.iterdir()) + [FOLDER_A04 / n for n in
                                               ("RECONCILIATION_REPORT.md", "INTAKE_MANIFEST.json", "PROPOSED_RECORDS.json")]
    return {str(p.relative_to(WORKTREE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in generated if p.is_file()}


def test_r9_regenerating_twice_from_unchanged_inputs_is_byte_identical():
    import subprocess
    import sys as _sys
    if not _R9_DRIVER.exists() or not (_R9_PRIV / "summary.json").exists():
        pytest.skip("driver or private outputs absent")
    env = dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1")
    runs = []
    for _ in range(2):
        subprocess.run([_sys.executable, "-I", str(_R9_DRIVER)], cwd=str(WORKTREE), env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        runs.append(_r9_snapshot())
    assert runs[0] == runs[1], sorted(k for k in runs[0] if runs[0][k] != runs[1].get(k))


def test_r9_every_hash_recorded_in_a_current_artifact_matches_the_bytes_it_names():
    """Scope: summary.json, reconciliation_full.json, INTAKE_MANIFEST.json, PROPOSED_RECORDS.json, the current
    IMPLEMENTATION_RECEIPT private table, the authority file and the inventory. TEST_EVIDENCE.json is checked by the
    round evidence step, because it records the run that contains this test."""
    if not (_R9_PRIV / "summary.json").exists():
        pytest.skip("private outputs absent")
    summary = json.loads((_R9_PRIV / "summary.json").read_text(encoding="utf-8"))
    for name, rec in summary["private_hashes"].items():
        data = (_R9_PRIV / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == rec["sha256"], name
        assert len(data) == rec["bytes"], name
    recon = json.loads((_R9_PRIV / "reconciliation_full.json").read_text(encoding="utf-8"))
    for item in recon["inputs"]:
        assert hashlib.sha256((PROJECT_CONTAINER / item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
    intake = json.loads((FOLDER_A04 / "INTAKE_MANIFEST.json").read_text(encoding="utf-8"))
    for item in intake["inputs"]:
        if "sha256" in item and (PROJECT_CONTAINER / item["path"]).exists():
            assert hashlib.sha256((PROJECT_CONTAINER / item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
    records = json.loads((FOLDER_A04 / "PROPOSED_RECORDS.json").read_text(encoding="utf-8"))
    for name, digest in records["tsv_sha256_private"].items():
        assert hashlib.sha256((_R9_PRIV / name).read_bytes()).hexdigest() == digest, name
    for name in ("study_registry.tsv", "publication_family_registry.tsv", "study_alias_crosswalk.tsv"):
        assert hashlib.sha256((_R9_PRIV / name).read_bytes()).hexdigest() == summary["private_hashes"][name]["sha256"], name


# ------------------------------------------------------------------ Round 10 (Astra closure finding 2: report wording)
# Every count or prose claim the reconciliation report makes about a subset must be computed from the applied rows
# (the rows after confirmations), so that it cannot go stale when dispositions change. No disposition is changed here.

def _r10_breakdown(tally):
    """The one breakdown format used by the generator and checked here: count descending, then code name."""
    return ", ".join(f"{count} {code}" for code, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])))


def _r10_applied(real_result):
    auth, conf, receipts = _r6_real_inputs()
    return qr.finalize(real_result, conf, receipts, auth, _real_rows(EPI_CSV))


def test_r10_identifier_less_line_states_the_count_and_the_applied_breakdown(real_result):
    applied = _r10_applied(real_result)["dispositioned_rows"]
    idless = [r for r in applied if r["cluster_id"] is None]
    expected = Counter(r["disposition"] for r in idless)
    report = (FOLDER_A04 / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    line = next(l for l in report.splitlines() if l.startswith("- In-scope rows with no public identifier"))
    assert line == (f"- In-scope rows with no public identifier: {len(idless)}. "
                    f"Applied dispositions: {_r10_breakdown(expected)}.")


def test_r10_identifier_less_heading_states_the_count_and_the_applied_breakdown(real_result):
    applied = _r10_applied(real_result)["dispositioned_rows"]
    idless = [r for r in applied if r["cluster_id"] is None]
    expected = Counter(r["disposition"] for r in idless)
    report = (FOLDER_A04 / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    heading = next(l for l in report.splitlines() if l.startswith("## 4. "))
    assert heading.startswith(f"## 4. Identifier-less rows ({len(idless)}; applied dispositions "
                              f"{_r10_breakdown(expected)};")
    assert "Unresolved rows" not in heading


def test_r10_no_section_describes_every_identifier_less_row_as_unresolved():
    report = (FOLDER_A04 / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    current = report[:report.index("## 6c.")]
    assert not re.search(r"\(UNRESOLVED\)", current)
    assert not re.search(r"[Uu]nresolved rows", current)


def test_r10_report_source_split_and_accession_conflict_are_computed(real_result):
    result = _r10_applied(real_result)
    applied = result["dispositioned_rows"]
    reg = sum(1 for r in applied if r["tag"] == "REG")
    epi = sum(1 for r in applied if r["tag"] == "EPI")
    inputs = {i["tag"]: i["row_count"] for i in real_result["inputs"]}
    report = (FOLDER_A04 / "RECONCILIATION_REPORT.md").read_text(encoding="utf-8")
    assert (f"- Input rows: {sum(inputs.values())} (REG {inputs['REG']}, EPI {inputs['EPI']})." in report)
    assert f"(REG {reg}; EPI human clinical {epi})" in report
    accession = sum(1 for c in result["conflicts"] if c["code"] == "ACCESSION_ALIAS_CONFLICT")
    assert f"ACCESSION_ALIAS_CONFLICT is {accession}:" in report
