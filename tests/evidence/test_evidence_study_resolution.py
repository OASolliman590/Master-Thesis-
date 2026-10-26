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
FIXTURES = Path(__file__).resolve().parents[1] / "a_dav" / "fixtures" / "study_resolution"
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
















# -------------------------------------------- same study, GEO and SRA aliases




# ------------------------------------------------------- multiple publications










# ------------------------------------------------------ SuperSeries / SubSeries
















# ------------------------------------------------------- reanalysis and reuse


















# ------------------------------------------------ suspected overlap (DAV-T08)






# ---------------------------------------------- punctuation and case collisions












# ------------------------------------------------------------ frozen failure codes












# --------------------------------------------------------- certainty and merging










# ----------------------------------------------------------------- status ceiling










# ----------------------------------------------------------------- closed enums










# ------------------------------------------------------------ contract tests




















def test_module_has_no_file_network_or_subprocess_io():
    source = Path(sr.__file__).read_text(encoding="utf-8")
    for token in ("open(", "pathlib", "Path(", "socket", "urllib", "requests", "subprocess", "os.environ"):
        assert token not in source, token


def test_module_reuses_the_accepted_scanners_instead_of_reimplementing_them():
    source = Path(sr.__file__).read_text(encoding="utf-8")
    assert "from tools.a_dav.search_log import" in source
    for name in ("_scan_text", "_validate_fact_locator", "_scan_recursive", "SearchLogError"):
        assert name in source
    assert "def _scan_text" not in source
    assert "def _validate_fact_locator" not in source


# ---------------------------------------------------------- null tokens










# ------------------------------------------------------------ security
















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






# ------------------------------------------------------------- receipt










# ------------------------------------------------- golden synthetic crosswalk




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






















def test_proposed_tracer_records_are_labelled_validate_and_hold_no_alias_rows():
    document = json.loads(PROPOSED_DOC.read_text(encoding="utf-8"))
    assert document["status"] == "PROPOSED_NOT_RESOLVED"
    assert document["admitted_count"] == 0
    assert document["analysis_readiness"] == "NOT_ANALYSIS_READY"
    assert document["provisional_integrator"] is True
    study_validator = Draft202012Validator(STUDY_SCHEMA)
    pub_validator = Draft202012Validator(PUBLICATION_SCHEMA)
    for record in document["study_registry"]:
        assert list(study_validator.iter_errors(record)) == []
    for record in document["publication_family_registry"]:
        assert list(pub_validator.iter_errors(record)) == []
    assert "alias_value" not in json.dumps(document)
    crosswalk = document["private_alias_crosswalk"]
    assert crosswalk["row_count"] == 6
    assert len(crosswalk["sha256"]) == 64
    assert "GSM" not in PROPOSED_DOC.read_text(encoding="utf-8")


def test_proposed_tracer_study_identity_matches_the_saved_responses():
    document = json.loads(PROPOSED_DOC.read_text(encoding="utf-8"))
    studies = {record["study_id"]: record for record in document["study_registry"]}
    riaz = studies["STUDY-RIAZ-GSE91061"]
    cho = studies["STUDY-CHO-GSE126045"]
    assert "SRA:SRP094781" in riaz["source_repositories"]
    assert cho["source_repositories"] == ["GEO:GSE126045"]
    assert riaz["primary_publication"] is None and riaz["secondary_publications"] == ["PUB-PMID-29033130"]
    assert cho["secondary_publications"] == ["PUB-PMID-32879421"]
    assert cho["study_status"] == "RESOLVING"
    assert riaz["study_status"] == "CANDIDATE"
    publications = {record["publication_id"]: record for record in document["publication_family_registry"]}
    assert publications["PUB-PMID-29033130"]["doi"] == "10.1016/j.cell.2017.09.028"
    assert publications["PUB-PMID-32879421"]["doi"] == "10.1038/s12276-020-00493-8"
    assert {p["independence_status"] for p in publications.values()} == {"UNRESOLVED"}


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


def test_tracer_study_records_hold_no_clinical_or_treatment_values():
    # Tracer output is study-identity metadata only (PACKET section 8). Clinical and treatment
    # curation belongs to DAV-T05/T06, so these descriptive fields must not be filled from repository text.
    for record in _tracer_document()["study_registry"]:
        for field in CLINICAL_TREATMENT_FIELDS:
            assert record[field] in ("UNKNOWN", None), (record["study_id"], field, record[field])
        assert record["study_class"] == "OTHER", record["study_id"]


def test_every_tracer_record_locator_cites_a_response_containing_its_identifier():
    document = _tracer_document()
    for record in document["study_registry"]:
        ids = [repo.split(":", 1)[1] for repo in record["source_repositories"] if ":" in repo]
        ids += [pub["pmid"] for pub in document["publication_family_registry"] if pub["study_id"] == record["study_id"]]
        for locator in record["source_locators"]:
            _assert_locator_cites(locator["value"], ids, record["study_id"])
    for pub in document["publication_family_registry"]:
        for locator in pub["source_locators"]:
            _assert_locator_cites(locator["value"], [pub["pmid"]], pub["publication_id"])


MODALITY_TERMS = {"RNA": "high throughput sequencing", "DNA_METHYLATION": "Methylation profiling"}




# ------------------------------------ round 2 (H-1, M-1, M-2, L-1, OSR-M01/M02, OSR-L01)

ROUND2_LOCATOR_URL = "https://example.org/SYNTHETIC/record"


def _loc(accessed=None, page="synthetic section", value=ROUND2_LOCATOR_URL):
    return {"kind": "URL", "value": value, "page_or_section": page, "accessed_utc": accessed}


def repo_study(repos, study_id="SYN-STUDY-A", family="SYN-FAM-A", **overrides):
    return study(study_id, family, source_repositories=repos, **overrides)


# H-1 / OSR-H01: canonical identity invariant

























# M-1: total, deterministic locator order; exact duplicates refused





# M-2: placeholder reviewers and provisional decisions







# L-1: DISPROVED rule as implemented



# OSR-M01 / OSR-M02: per-field locators for SubSeries modality and SRA

def _sub_with(**overrides):
    value = {"accession": "GSE900044", "modality": "RNA", "sra_study": "SRP900044", "certainty": "VERIFIED",
             "evidence_type": "REPOSITORY_LINK", "source_locator": _loc(),
             "modality_locator": _loc(), "sra_locator": _loc()}
    value.update(overrides)
    return value










# Docs: the repository list of the proposed Cho record is only the VERIFIED-backed SuperSeries

def test_proposed_cho_repositories_list_only_the_verified_superseries_and_riaz_both_verified_links():
    document = _tracer_document()
    studies = {record["study_id"]: record for record in document["study_registry"]}
    assert studies["STUDY-CHO-GSE126045"]["source_repositories"] == ["GEO:GSE126045"]
    assert studies["STUDY-RIAZ-GSE91061"]["source_repositories"] == ["GEO:GSE91061", "SRA:SRP094781"]


def test_every_proposed_repository_is_backed_by_a_verified_row_in_the_private_crosswalk():
    crosswalk = SCRATCH_TRACER / "tracer_alias_crosswalk.tsv"
    if not crosswalk.exists():
        pytest.skip("private tracer crosswalk is not present in this checkout")
    lines = crosswalk.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    rows = [dict(zip(header, line.split("\t"))) for line in lines[1:]]
    prefix_types = {"GEO": {"GEO_SERIES", "GEO_SUPERSERIES", "GEO_SUBSERIES"}, "SRA": {"SRA_STUDY"}}
    for record in _tracer_document()["study_registry"]:
        for repository in record["source_repositories"]:
            prefix, identifier = repository.split(":", 1)
            assert any(row["canonical_study_id"] == record["study_id"] and row["status"] == "MERGED_VERIFIED"
                       and row["alias_type"] in prefix_types[prefix] and row["alias_value"] == identifier
                       for row in rows), repository



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






















# ------------- round 4 (M-3: Unicode-aware reviewer key; combining marks cannot bypass)







