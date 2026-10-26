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
FIXTURES = Path(__file__).resolve().parents[1] / "a_dav" / "fixtures" / "queue_reconciliation"
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




















# ------------------------------------------------------------------ intake IDs and scope


def test_intake_id_format_is_manifest_scoped():
    assert qr.intake_id("REG", "ICB-BULK-001") == "QUEUE-REG-ICB-BULK-001"
    assert qr.intake_id("EPI", "S01") == "QUEUE-EPI-S01"
    assert sl._LEXICAL_ID.fullmatch(qr.intake_id("REG", "ICB-PROST-XYZ"))








# ------------------------------------------------------------------ disposition vocabulary
















# ------------------------------------------------------------------ clustering and conflicts


















# ------------------------------------------------------------------ packets and contracts














# ------------------------------------------------------------------ determinism (metamorphic)






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














# ------------------------------------------------------------------ Phase 2 planning (offline)






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








def test_doi_is_verified_through_a_pubmed_record_whose_pmid_is_in_no_cluster():
    result = run(source("REG", [
        reg("SYN-D", disposition="primary_candidate_pending_private",
            urls="https://doi.org/10.1038/synthetic-doi-700333"),
    ]))
    plan = qr.phase2_plan(result)
    doi_search = [entry for entry in plan if entry["kind"] == "esearch_pubmed_doi"][0]
    search_body = {"esearchresult": {"count": "1", "retmax": "20", "retstart": "0", "idlist": ["999111"],
                                     "querytranslation": "10.1038/synthetic-doi-700333[DOI]"}}
    summary_url = qr._esummary("pubmed", ["999111"])
    summary_body = {"result": {"uids": ["999111"], "999111": {
        "uid": "999111", "articleids": [{"idtype": "doi", "value": "10.1038/synthetic-doi-700333"}]}}}
    responses = [
        _response_for(doi_search, search_body),
        {"query_id": doi_search["query_id"] + "-F1", "kind": "esummary_pubmed_uid", "url": summary_url,
         "http_status": 200, "utc": "2026-10-17T16:00:02.000Z", "body": json.dumps(summary_body), "file": None},
    ]
    evaluation = qr.phase2_evaluate(result, responses, pipeline_utc=PIPELINE_UTC)
    dois = [v for v in evaluation["verified_aliases"] if v["alias_type"] == "PUBLICATION_DOI"]
    assert len(dois) == 1 and dois[0]["identifier"] == "DOI10.1038/synthetic-doi-700333"
    assert [v for v in evaluation["verified_aliases"] if v["alias_type"] == "PUBLICATION_PMID"] == []






# ------------------------------------------------------------------ Round 2 (reviewer findings QR-01..06, OSR-M01, SA-*)


def _gse_row(index):
    return reg(f"SYN-BUDGET-{index:03d}", disposition="primary_candidate_pending_private",
               urls=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE{700000 + index}")
















































# ------------------------------------------------------------------ Round 3 (R2-QR-07..10, DA-M01, DA-L01, DA-L02)


def _rule(row_kwargs):
    return run(source("REG", [reg("SYN-R3", **row_kwargs)]))["dispositioned_rows"][0]






















def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()






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


def test_git_bound_a_dav_04_files_hold_only_synthetic_gsm_accessions_and_no_local_absolute_paths():
    files = _git_bound_a_dav_04_files()
    assert len(files) > 80
    for path in files:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert LOCAL_PATH_MARKER not in text, path.name
        for accession in re.findall(r"\bGSM\d+\b", text):
            assert accession in SYNTHETIC_GSM_ACCESSIONS, (path.name, accession)


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










# Round 4: a credential is a value, not the word. A reviewer PASS line ("no API-key, token ... found") is not a secret.
CREDENTIAL_VALUE_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"
    r"|authorization\s*:\s*(?:basic|bearer)\s+[A-Za-z0-9._\-+/=]{8,}"
    r"|bearer\s+[A-Za-z0-9._\-]{8,}", re.I)




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
















# ------------------------------------------------------------------ Round 4 (R3-QR-11, R3-QR-12, R3-QR-13, OSR3-M01)
# One shared clause-scoped matcher serves every excluding rule. Clauses split on . ; , | and " and " / " but ".
# A term counts only if the clause does not negate it before or after the term.

R4_URL = "https://pubmed.ncbi.nlm.nih.gov/555555/"


def _r4(**row_kwargs):
    row_kwargs.setdefault("disposition", "supporting_or_context")
    row_kwargs.setdefault("urls", R4_URL)
    return _rule(row_kwargs)




# R3-QR-11: untreated evidence must be an affirmative, non-negated, non-timing clause.


# OSR3-M01: standalone "treatment-naive" fails closed to UNRESOLVED with a treatment-context resolution path.






# R3-QR-12: a non-molecular modality is explicit only without a negation in its clause; a molecular
# assay counts only if it is named without a negation in its clause.






# R3-QR-13: explicit multi-study aggregation wording only; "integrated", "database", "resource" alone do not count.








def test_r4_one_shared_clause_matcher_serves_every_excluding_rule():
    import inspect
    source = inspect.getsource(qr._disposition_for_registry)
    assert source.count("clause_signal(") >= 3
    for legacy in ("_RESOURCE_RE.search", "_AFFIRM_UNTREATED_RE.search", "_explicit_nonmolecular_modality("):
        assert legacy not in source, legacy


# OSR3-M01 / inventory: every receipt in the A_DAV_04 folder has a row in ARTIFACT_HASHES.tsv.
REQUIRED_REVIEW_RECEIPTS = {
    "COORDINATOR_REVIEW_RECEIPT.md", "SOL_CODE_REVIEW_01_RECEIPT.md", "SOL_SOURCE_AUDIT_REVIEW_01_RECEIPT.md",
    "SOL_CODE_REREVIEW_01_RECEIPT.md", "SOL_SOURCE_AUDIT_REREVIEW_01_RECEIPT.md",
    "SOL_CODE_REREVIEW_02_RECEIPT.md", "SOL_SOURCE_AUDIT_REREVIEW_02_RECEIPT.md",
}


def test_r4_every_receipt_in_the_folder_has_an_inventory_row():
    folder = WORKTREE / "docs" / "validation" / "A_DAV_04"
    receipts = {p.name for p in folder.glob("*_RECEIPT.md")}
    rows = [line.split("\t") for line in (folder / "ARTIFACT_HASHES.tsv").read_text(encoding="utf-8").splitlines()[1:]]
    inventoried = {Path(r[1]).name for r in rows if len(r) == 4}
    assert REQUIRED_REVIEW_RECEIPTS <= receipts
    assert receipts - inventoried == set(), sorted(receipts - inventoried)
    assert REQUIRED_REVIEW_RECEIPTS <= inventoried


def test_r4_inventory_rows_match_the_current_bytes_and_hashes():
    folder_root = WORKTREE
    lines = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "ARTIFACT_HASHES.tsv").read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        classification, relpath, size, digest = line.split("\t")
        target = folder_root / relpath
        assert target.exists(), relpath
        assert target.stat().st_size == int(size), relpath
        assert _sha256(target) == digest, relpath


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














# OSR4-M01 and R3-QR-13: bare "pan-cancer" and single-study aggregation phrasing are not aggregation.




# R3-QR-11 / R3-QR-12 / R4-QR-14: negation and clause scope of the proposal heuristics.












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


















def test_r5_confirmations_file_is_inventoried():
    # Round 6: the file now carries the coordinator's 15 transcribed confirmations (see the round-6 tests).
    inventoried = (WORKTREE / "docs" / "validation" / "A_DAV_04" / "ARTIFACT_HASHES.tsv").read_text(encoding="utf-8")
    assert "docs/validation/A_DAV_04/EXCLUSION_CONFIRMATIONS.json" in inventoried




# R4-QR-15 (Low): credential values in the forms named by the reviewer.




# OSR4-L01 / round 5: the single documented inventory exclusion is the self-referential evidence file.
INVENTORY_SELF_REFERENTIAL_EXCLUSIONS = {"TEST_EVIDENCE.json", "ARTIFACT_HASHES.tsv"}


def test_r5_inventory_covers_every_a_dav_04_artifact_except_the_documented_self_referential_files():
    folder = WORKTREE / "docs" / "validation" / "A_DAV_04"
    rows = [line.split("\t") for line in (folder / "ARTIFACT_HASHES.tsv").read_text(encoding="utf-8").splitlines()[1:]]
    inventoried = {Path(r[1]).name for r in rows}
    expected = {p.name for p in folder.iterdir() if p.is_file()} - INVENTORY_SELF_REFERENTIAL_EXCLUSIONS
    assert expected <= inventoried, sorted(expected - inventoried)
    assert "TEST_EVIDENCE.json" not in inventoried


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










# ------------------------------------------------------------------ Round 7 (R6-AUTH-02, R6-STATE-02)
# R6-AUTH-02: a receipt block with more than one entry for a row is ambiguous; the whole receipt is invalid.







def test_r7_real_receipt_block_has_fifteen_unique_keys_and_stays_valid():
    _auth, conf, receipts = _r6_real_inputs()
    block = qr._parse_confirmation_block(receipts[R6_SOURCE])
    keys = {(b["row_id"], b["proposed_rule_id"]) for b in block}
    assert len(block) == 15 and len(keys) == 15 and len({b["row_id"] for b in block}) == 15


# R6-STATE-02: stored tallies recomputed from the applied rows (the state the committed artifacts must hold).

def _r7_committed(name):
    return WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs" / name










def _r7_round_trip(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))




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






def test_r8_real_receipt_has_exactly_one_block_and_stays_valid():
    _auth, conf, receipts = _r6_real_inputs()
    text = receipts[R6_SOURCE].decode("utf-8")
    assert text.count("BEGIN_CONFIRMATIONS_JSON") == 1 and text.count("END_CONFIRMATIONS_JSON") == 1
    assert len(qr._parse_confirmation_block(receipts[R6_SOURCE])) == 15


def _r8_epi_row(study_id="E1"):
    return {"tag": "EPI", "row_id": study_id, "disposition": "NON_ICI_TREATMENT", "rule_id": "EPI-3-NO-ICI"}














# ------------------------------------------------------------------ Round 9 (R8-STRUCT-02, R8-STATE-01)
# R8-STRUCT-02: a structural-source ID that occurs more than once is ambiguous. It records no fields, so its predicate
# fails and the row is flagged. Last-row-wins is never used for a source ID.

def _r9_epi_src(study_id, immunotherapy):
    return {"study_id": study_id, "immunotherapy": immunotherapy}














# R8-STATE-01: no artifact embeds a hash of itself; regeneration is byte-identical; every recorded hash is true.

_R9_PRIV = WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "outputs"
_R9_DRIVER = WORKTREE / ".scratch" / "runtime" / "A_DAV_04" / "drivers" / "build_outputs.py"




def _r9_snapshot():
    generated = sorted(_R9_PRIV.iterdir()) + [FOLDER_A04 / n for n in
                                               ("RECONCILIATION_REPORT.md", "INTAKE_MANIFEST.json", "PROPOSED_RECORDS.json")]
    return {str(p.relative_to(WORKTREE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in generated if p.is_file()}






# ------------------------------------------------------------------ Round 10 (Astra closure finding 2: report wording)
# Every count or prose claim the reconciliation report makes about a subset must be computed from the applied rows
# (the rows after confirmations), so that it cannot go stale when dispositions change. No disposition is changed here.

def _r10_breakdown(tally):
    """The one breakdown format used by the generator and checked here: count descending, then code name."""
    return ", ".join(f"{count} {code}" for code, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])))


def _r10_applied(real_result):
    auth, conf, receipts = _r6_real_inputs()
    return qr.finalize(real_result, conf, receipts, auth, _real_rows(EPI_CSV))








