"""A-DAV-04 queue reconciliation: DAV-T01 intake and DAV-T02 provisional decisions.

Pure functions only. This module performs no file I/O, no network access and reads no clock.
Callers pass parsed rows, file facts (path, sha256), a fixed pipeline timestamp and, for
Phase 2, the saved response bodies. Every output is a PROPOSED record or a candidate
packet. Nothing here admits a source, and no record can carry study_status RESOLVED.

Scope: the 117-row study-use registry (every row) and the 8 human-clinical rows of the
epigenetic-drug survey index. The 26 preclinical survey rows are out of scope, with reasons.

Identifier facts are only "queue row X lists identifier Y in field F". Registry dispositions,
titles, cancers and modalities are historical leads, labelled as notes and inferences, never
as verified facts.

Failure codes raised as QueueReconciliationError (stable, machine-readable):
- SECRET_LOCATOR, MALFORMED_ROW, DUPLICATE_ROW_ID, UNKNOWN_SOURCE, UNKNOWN_KIND,
  INVALID_UTC_TIMESTAMP, PHASE2_CAP_EXCEEDED.
Structural and scientific codes from study_resolution (STATUS_CEILING, ACCESSION_ALIAS_CONFLICT,
UNRESOLVED_ORIGINATING_STUDY, ...) propagate unchanged from resolve().
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from urllib.parse import quote, urlsplit

from tools.a_dav import search_log as sl
from tools.a_dav import study_resolution as sr


TICKET = "A-DAV-04"
RECEIPT_SCHEMA = "A-DAV-04.queue_reconciliation_receipt.1"
PROPOSED_STATUS = "PROPOSED_NOT_RESOLVED"
ADMITTED_COUNT = 0
ANALYSIS_READINESS = "NOT_ANALYSIS_READY"
PROVISIONAL_REVIEWER = "provisional-integrator-A-DAV-04-implementer"
PHASE1_DECISION_ID = "A-DAV-04-PHASE1-PROVISIONAL"
PHASE2_DECISION_ID = "A-DAV-04-PHASE2-PROVISIONAL"
AGENT_ID = "implementer-A-DAV-04 (Claude Haiku 5.5, effort high requested; runtime not attested)"
UNASSIGNED_REVIEWER = "unassigned-pending-independent-review"
LANE_CATALOGUE = "A-catalogue-resolution"
LANE_REPOSITORY = "C-repository-object-discovery"
LANE_PUBLICATION = "B-publication-metadata"
PHASE2_REQUEST_CAP = 150
PHASE2_MIN_SPACING_SECONDS = 0.4
PHASE2_TOOL = "a-dav-04-queue-reconciliation"
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HUMAN_CLINICAL_GROUP = "Human clinical"

SOURCE_SPECS = {
    "REG": {
        "path": "outputs/study-clearance-20261002/ALL_117_STUDY_USE_REGISTRY.csv",
        "sha256": "ae54d135cace7cd85ab4b96f1825474024fc841a56fcd25ffcbbc871196463da",
        "row_id": "catalogue_entry_id",
        "identifier_fields": ("source_family", "evidence_urls"),
        "family_field": "source_family",
    },
    "EPI": {
        "path": "reports/epigenetic_drug_study_index.csv",
        "sha256": "4634b52fed50fa8b057ebc0e89016071f3aa04571c448ef512fe1f59d597b2b1",
        "row_id": "study_id",
        "identifier_fields": ("accessions", "paper_url", "repository_urls", "raw_links", "processed_links",
                              "evidence_urls"),
        "family_field": None,
    },
}

# Frozen discovery vocabulary (SOURCE_DISCOVERY_STRATEGY.md, "Candidate exclusion at discovery").
DISCOVERY_LABELS = {
    "NON_ICI_TREATMENT": "non-ICI treatment",
    "VACCINE_OR_ADOPTIVE_CELL": "vaccine or adoptive-cell study",
    "MECHANISTIC_CELL_MODEL": "mechanistic cell model",
    "UNTREATED_MOLECULAR_COHORT": "untreated molecular cohort",
    "WRONG_ENDPOINT": "wrong endpoint",
    "NO_PATIENT_LEVEL_ROUTE": "no patient-level route",
    "NO_MOLECULAR_DATA": "no molecular data",
    "DUPLICATE_REANALYSIS": "duplicate/reanalysis",
    "INACCESSIBLE_OBJECT": "inaccessible or unavailable object",
    "WRONG_COMPARTMENT": "wrong biological compartment",
    "OUTSIDE_BRANCH_SCOPE": "outside branch scope",
}
FROZEN_DISCOVERY_CODES = tuple(DISCOVERY_LABELS)
LEAD_CODES = ("INCLUDED_AS_LEAD", "UNRESOLVED")
DISPOSITION_CODES = FROZEN_DISCOVERY_CODES + LEAD_CODES

REGISTRY_DISPOSITION_MAP = {
    "primary_candidate_pending_private": "INCLUDED_AS_LEAD",
    "blocked": "RULE_REFINED_DEFAULT_UNRESOLVED",
    "supporting_or_context": "RULE_REFINED_DEFAULT_INCLUDED_AS_LEAD",
}
ALIAS_TYPE_FOR_KIND = {
    "GSE": "GEO_SERIES", "SRP": "SRA_STUDY", "PRJNA": "BIOPROJECT", "PRJEB": "ENA_STUDY",
    "EGAS": "EGA_STUDY", "PHS": "DBGAP_STUDY", "NCT": "TRIAL_ID", "PMID": "PUBLICATION_PMID",
    "DOI": "PUBLICATION_DOI",
}
KIND_PRIORITY = ("GSE", "SRP", "SRR", "PRJNA", "PRJEB", "EGAS", "EGAD", "EGAC", "PHS", "EMTAB", "PXD", "NCT",
                 "PMID", "PMCID", "DOI")
CONTROLLED_KINDS = ("PHS", "EGAS", "EGAD", "EGAC")
_FOLD_PREFIX = {
    "GSE": "GSE", "SRP": "SRP", "SRR": "SRR", "PRJNA": "PRJNA", "PRJEB": "PRJEB", "EGAS": "EGAS",
    "EGAD": "EGAD", "EGAC": "EGAC", "PHS": "PHS", "EMTAB": "EMTAB", "NCT": "NCT", "PXD": "PXD",
    "PMID": "PMID", "PMCID": "PMC",
}
ALIAS_EVIDENCE_PROBABLE = "CATALOGUE_ASSERTION"

_LEFT = r"(?<![A-Za-z0-9])"
_RIGHT = r"(?![0-9A-Za-z])"
_PATH_END = r"(?=[/?#\s\"'<>)\]]|$)"
_ID_PATTERNS = (
    ("GSE", re.compile(_LEFT + r"GSE\d{3,}" + _RIGHT, re.I)),
    ("SRP", re.compile(_LEFT + r"SRP\d{4,}" + _RIGHT, re.I)),
    ("SRR", re.compile(_LEFT + r"SRR\d{4,}" + _RIGHT, re.I)),
    ("PRJNA", re.compile(_LEFT + r"PRJNA\d{3,}" + _RIGHT, re.I)),
    ("PRJEB", re.compile(_LEFT + r"PRJEB\d{3,}" + _RIGHT, re.I)),
    ("EGAS", re.compile(_LEFT + r"EGAS\d{6,}" + _RIGHT, re.I)),
    ("EGAD", re.compile(_LEFT + r"EGAD\d{6,}" + _RIGHT, re.I)),
    ("EGAC", re.compile(_LEFT + r"EGAC\d{6,}" + _RIGHT, re.I)),
    ("PHS", re.compile(_LEFT + r"phs\d{6}(?:\.v\d+(?:\.p\d+)?)?" + _RIGHT, re.I)),
    ("EMTAB", re.compile(_LEFT + r"E-MTAB-\d+" + _RIGHT, re.I)),
    ("NCT", re.compile(_LEFT + r"NCT\d{8}" + _RIGHT, re.I)),
    ("PXD", re.compile(_LEFT + r"PXD\d{6}" + _RIGHT, re.I)),
    ("PMID", re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{1,9})" + _PATH_END, re.I)),
    ("PMID", re.compile(r"pmc\.ncbi\.nlm\.nih\.gov/articles/pmid/(\d{1,9})" + _PATH_END, re.I)),
    ("PMID", re.compile(_LEFT + r"PMID[:\s]*(\d{1,9})" + _RIGHT, re.I)),
    ("PMCID", re.compile(r"pmc\.ncbi\.nlm\.nih\.gov/articles/(?:PMC)?(\d+)" + _PATH_END, re.I)),
    ("PMCID", re.compile(_LEFT + r"PMC(\d{5,})" + _RIGHT, re.I)),
)
_DOI_GENERIC = re.compile(r"(?<![A-Za-z0-9])(10\.\d{4,9}/[^\s\"'<>;,]+)")
_NATURE_ARTICLE = re.compile(r"nature\.com/articles/([A-Za-z0-9][A-Za-z0-9._-]*)")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_GSM = re.compile(r"\bGSM\d+\b")


class QueueReconciliationError(ValueError):
    """Fail-closed error with a stable code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise QueueReconciliationError(code, message)


# ---------------------------------------------------------------- identifiers


def fold_identifier(kind, raw):
    """Matching key for one identifier. Case, punctuation and version suffixes are folded.

    Leading zeros are preserved: the digit run is kept exactly, so EGAS00001004050 and
    EGAS1004050 stay distinct. The raw value is never changed by this function.
    """
    if kind == "DOI":
        value = raw.strip().lower()
        value = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", value)
        value = re.sub(r"^doi:\s*", "", value)
        return "DOI" + value
    if kind not in _FOLD_PREFIX:
        _fail("UNKNOWN_KIND", f"identifier kind {kind!r} is not declared")
    match = re.search(r"\d+", raw)
    if not match:
        _fail("MALFORMED_ROW", f"identifier {raw!r} has no digits")
    return _FOLD_PREFIX[kind] + match.group(0)


def _clean_doi(value):
    return value.rstrip(".,;)]")


def extract_identifiers(text, field):
    """Public identifiers listed in one text field. GSM sample accessions are never extracted.

    Every field is first passed through the imported A-DAV-02 scanner. A credential-bearing
    field fails closed with SECRET_LOCATOR.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        sl._scan_text(text)
    except sl.SearchLogError as error:
        raise QueueReconciliationError("SECRET_LOCATOR", f"field {field} rejected: {error.code}") from error
    found = []

    def add(kind, raw, derived=False):
        found.append({"kind": kind, "raw": raw, "fold": fold_identifier(kind, raw), "field": field,
                      "derived": derived})

    for kind, pattern in _ID_PATTERNS:
        for match in pattern.finditer(text):
            if kind in ("PMID", "PMCID") and pattern.groups == 1:
                digits = match.group(1)
                raw = digits if kind == "PMID" else "PMC" + digits
                add(kind, raw)
            else:
                add(kind, match.group(0))
    for match in _DOI_GENERIC.finditer(text):
        add("DOI", _clean_doi(match.group(1).split("?")[0].split("#")[0]))
    for match in _NATURE_ARTICLE.finditer(text):
        suffix = match.group(1).rstrip(".-")
        add("DOI", "10.1038/" + suffix, derived=True)
    unique = {}
    for item in found:
        unique[(item["kind"], item["raw"], item["field"], item["derived"])] = item
    return sorted(unique.values(), key=_identifier_sort_key)


def _identifier_sort_key(item):
    return (KIND_PRIORITY.index(item["kind"]), item["fold"], item["raw"], item["field"], item["derived"])


def intake_id(tag, row_id):
    """Manifest-scoped intake ID used as the candidate packet query ID (QUEUE-<file-tag>-<row-id>)."""
    if tag not in SOURCE_SPECS:
        _fail("UNKNOWN_SOURCE", f"source tag {tag!r} is not declared")
    value = "QUEUE-" + tag + "-" + row_id
    if not sl._LEXICAL_ID.fullmatch(value):
        _fail("MALFORMED_ROW", f"intake ID {value!r} is not lexical")
    return value


def scope_of(tag, row):
    """(in_scope, reason). Only the human-clinical epigenetic rows are in scope among EPI rows."""
    if tag == "EPI":
        group = row.get("model_group", "")
        if group != HUMAN_CLINICAL_GROUP:
            return False, f"outside human-clinical scope (model_group: {group})"
    return True, None


# ---------------------------------------------------------------- dispositions

_VACCINE_RE = re.compile(r"vaccin|prostvac|sipuleucel|adoptive|\bCAR[- ]?T\b|\bCART\b|dendritic|"
                         r"tumou?r-infiltrating|\bTCR-?T\b|cell therapy", re.I)
_MECH_RE = re.compile(r"cell[- ]line|organoid|murine|xenograft|in vitro|preclinical|mechanistic|"
                      r"\bCT26\b", re.I)
_PATIENT_RE = re.compile(r"patients?|trial|cohort|clinical", re.I)
_NONICI_RE = re.compile(r"azacitidine|decitabine|chemotherap|carboplatin|docetaxel|cabazitaxel|enzalutamide|"
                        r"abiraterone|radiother|olaparib|\bPARP\b|\bHDAC\b|\bDNMT\b", re.I)
_ICI_RE = re.compile(r"nivolumab|pembrolizumab|avelumab|atezolizumab|durvalumab|ipilimumab|cemiplimab|"
                     r"tremelimumab|camrelizumab|sintilimab|toripalimab|anti-?PD|PD-?L1|CTLA-?4|"
                     r"immunotherap|checkpoint|blockade", re.I)
_OVERLAP_RE = re.compile(r"overlap|duplicate|reanaly|re-analy", re.I)
_HISTO_RE = re.compile(r"histolog|histopath|\bWSI\b|H&E|\bIHC\b|imaging|TCIA|radiomic", re.I)
_MOLECULAR_RE = re.compile(r"RNA|DNA|sequenc|proteom|metabol|lipid|methylation|exome|cytof|microarray|"
                           r"nanostring|transcript|ATAC|spatial|TCR|BCR|serum|plasma|analyte|flow|cytometr", re.I)
_AMBIGUOUS_REGIMEN_RE = re.compile(r"later|protocol|mouse|experiment", re.I)
_NO_ICI_RE = re.compile(r"^\s*(none|no ici|not applicable|n/?a|-)?\s*$", re.I)


# ---------------------------------------------------------------- round 4: one shared clause-scoped matcher
# R3-QR-11/12/13 and OSR3-M01. Every excluding registry rule uses clause_signal(); no rule searches a bare regex.
# Clauses split on . ; , | and on " and " / " but ". A term is affirmative only if its clause does not negate it
# before the term (up to two words, e.g. "not", "no longer", "non-") or after the term (anywhere in the clause).
_NEG_WORD_RE = re.compile(r"\b(?:no|not|non|never|without|absent|none|neither|nor|cannot)\b", re.I)
_SCOPE_BREAK_RE = re.compile(r"\b(?:but|with|although|however|whereas|while|yet|except)\b", re.I)
_AFTER_NEG_WORDS = frozenset({"not", "never", "unavailable", "absent", "cannot"})


def clause_split(text):
    """Split on . ; , | outside quotes and brackets. Conjunctions do not split: scope is handled in _negated."""
    clauses, buf, depth, quoted = [], [], 0, False
    for ch in text or "":
        if ch == '"':
            quoted = not quoted
        elif not quoted and ch in "([":
            depth += 1
        elif not quoted and ch in ")]":
            depth = max(0, depth - 1)
        if not quoted and depth == 0 and ch in ".;,|":
            clauses.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    clauses.append("".join(buf))
    return [clause.strip() for clause in clauses if clause.strip()]


def _negated(clause, start, end):
    """Fail closed: a term is negated by any negation word earlier in its clause whose scope is not broken by a
    conjunction or contrast, or by a negation among the three words after the term."""
    seg = clause[:start]
    last = None
    for match in _NEG_WORD_RE.finditer(seg):
        last = match
    if last is not None and not _SCOPE_BREAK_RE.search(seg[last.end():]):
        return True
    after_words = re.findall(r"[A-Za-z]+", clause[end:])[:3]
    return any(word.lower() in _AFTER_NEG_WORDS for word in after_words)


def clause_signal(text, term_re, exclude_re=None):
    """First affirmative match of term_re: in a clause not matched by exclude_re and not negated around the term."""
    for clause in clause_split(text):
        if exclude_re is not None and exclude_re.search(clause):
            continue
        for match in term_re.finditer(clause):
            if not _negated(clause, match.start(), match.end()):
                return match.group(0)
    return None


# R2-QR-08 / R3-QR-13: explicit multi-study aggregation wording. Bare "integrated", "database", "resource",
# "curated", "portal" or "aggregated" never counts; an "integrat..." term needs a plural multi-source noun in its clause.
_AGGREGATION_RE = re.compile(
    r"meta-?analys[ie]s|meta-analytic|re-?analys[ei]s|"
    r"pooled (?:analys[ie]s|cohorts?|studies|trials|datasets)|"
    r"secondary (?:integrated )?(?:analysis|use|data|catalog|catalogue|database|resource)|"
    r"constituent (?:studies|cohorts|datasets)|aggregated (?:studies|cohorts|datasets)|"
    r"integrat(?:es|ed|ing|e)\b.{0,60}?\b(?:datasets|studies|cohorts|trials|sources|databases)\b|"
    r"(?:database|portal|compendium|catalog|catalogue) of [\w\s-]{0,40}?(?:studies|cohorts|datasets|trials)\b|"
    r"(?:covering|spanning|across|integrating|combining)\s+(?:\d+|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)\s+"
    r"(?:\w+\s+)?(?:cancers|cancer types|tumou?r types|cohorts|studies|datasets|trials|sources|institutions)\b|"
    r"source-specific (?:downloads|datasets|cohorts|studies|objects|sources)\b|"
    r"\b(?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)\s+cancers\b|"
    r"multi-?(?:cohort|study) (?:atlas|resource|dataset)", re.I)
# OSR4-M01 / R3-QR-13: one originating study is not aggregation, whatever else the clause says.
_SINGLE_STUDY_RE = re.compile(
    r"\b(?:single|one|sole|individual)[- ](?:study|trial|cohort|institution)\b|"
    r"\bone (?:primary |pembrolizumab |nivolumab |anti-PD-1 |anti-PD-L1 )?(?:study|trial|cohort|institution|patient)s?\b|"
    r"\bprimary (?:trial|cohort|study)\b", re.I)
_REGISTRY_AGGREGATION_FIELDS = ("original_title", "verified_title", "verified_modality", "intended_product",
                                  "usefulness")


def registry_aggregation_signal(row):
    """The matched explicit aggregation phrase in the registry row, or None. Used by REG-3B and by its tests."""
    return clause_signal(_registry_text(row, _REGISTRY_AGGREGATION_FIELDS), _AGGREGATION_RE)


def _registry_text(row, fields):
    return " | ".join(str(row.get(field) or "") for field in fields)


# R3-QR-11: affirmative untreated evidence only. "treatment-naive", "immunotherapy-naive", "baseline", "pre-treatment"
# and "before" describe sample timing or boilerplate and are never evidence; a negated "untreated" is not evidence.
_UNTREATED_TERM_RE = re.compile(
    r"\buntreated\b|\bno (?:prior )?(?:immunotherapy|ICI|checkpoint inhibitors?) (?:was |is )?"
    r"(?:administered|given|received)\b", re.I)
# OSR3-M01: "treatment-naive" describes sampling status; a baseline sample of a treated cohort can carry it.
_TREATMENT_NAIVE_RE = re.compile(r"\b(?:treatment|immunotherapy|therapy|ICI)[- ]naive\b", re.I)
_TIMING_CLAUSE_RE = re.compile(r"\b(?:before|prior to|pre-?treatment|pre-?therapy)\b", re.I)
# DA-M01 / R3-QR-12: explicitly non-molecular modality terms.
_NONMOLECULAR_MODALITY_RE = re.compile(
    r"radiolog|imaging|radiomic|histopatholog|histolog|\bH&E\b|\bWSI\b|whole[- ]slide|slides?\b", re.I)
# R2-QR-07: the regimen or response is documented as absent. This is missing evidence, so the row stays UNRESOLVED.
_REGIMEN_NOT_DOCUMENTED_RE = re.compile(
    r"(?:immunotherapy|ICI|checkpoint)\s+regimen[^|.;]{0,40}not documented|ORR[^|.;]{0,20}not documented", re.I)


def _row_has_named_molecular_assay(row):
    """True if a molecular assay is named affirmatively (not negated in its clause) in any registry field."""
    for field, value in row.items():
        if field == "evidence_urls" or not value:
            continue
        if clause_signal(str(value), _MOLECULAR_RE):
            return True
    return False


def _locator_hosts(row):
    hosts = []
    for url in re.split(r"\s*\|\s*|\s+", row.get("evidence_urls", "") or ""):
        if url.startswith("http"):
            host = urlsplit(url).netloc
            if host and host not in hosts:
                hosts.append(host)
    return hosts


def _disposition_for_registry(record):
    row, identifiers = record["row"], record["direct"]
    current = row.get("current_disposition", "")
    kinds = {item["kind"] for item in identifiers}
    title_text = _registry_text(row, ("verified_title", "source_family"))
    modality = row.get("verified_modality", "") or ""
    if current == "primary_candidate_pending_private":
        return "INCLUDED_AS_LEAD", "REG-1-PRIMARY", "registry primary candidate (historical lead); pending private object verification"
    # Controlled-access signals are conservative negatives: a family-label phs/EGA/EGAD identifier counts here
    # (never as a merge). Removing it would make the row look more accessible than the registry says.
    controlled_kinds = {item["kind"] for item in record["identifiers"]}
    if current == "blocked" and controlled_kinds & set(CONTROLLED_KINDS):
        return ("INACCESSIBLE_OBJECT", "REG-2-BLOCKED-CONTROLLED",
                "registry blocked; controlled-access repository identifier listed; no controlled content accessed")
    if current == "blocked" and clause_signal(row.get("next_action", "") or "", _OVERLAP_RE):
        return ("DUPLICATE_REANALYSIS", "REG-3-BLOCKED-OVERLAP",
                "registry blocked; next action names an overlap or reanalysis")
    if current == "supporting_or_context" and clause_signal(_registry_text(row, _REGISTRY_AGGREGATION_FIELDS),
                                                             _AGGREGATION_RE, _SINGLE_STUDY_RE):
        return ("DUPLICATE_REANALYSIS", "REG-3B-INTEGRATED-RESOURCE",
                "explicit integrated, portal, database, pooled, meta-analysis, re-analysis or constituent-study wording: "
                "a derived resource whose constituent studies need originating-study resolution before any lead is kept")
    if clause_signal(modality, _NONMOLECULAR_MODALITY_RE) and not _row_has_named_molecular_assay(row):
        hosts = _locator_hosts(row)
        reason = ("registry modality is explicitly non-molecular (radiology, imaging or histopathology) and no molecular "
                  "assay is named in the row")
        if hosts:
            reason += ("; note: a public locator on " + ", ".join(hosts) +
                       " is present but its identifier type is not extracted and still needs resolution")
        return ("NO_MOLECULAR_DATA", "REG-4-NONMOLECULAR-MODALITY", reason)
    if current == "supporting_or_context" and clause_signal(
            " | ".join([row.get("usefulness", "") or "", row.get("verified_title", "") or ""]),
            _UNTREATED_TERM_RE, _TIMING_CLAUSE_RE):
        return ("UNTREATED_MOLECULAR_COHORT", "REG-3C-AFFIRMATIVE-UNTREATED",
                "affirmative wording that the cohort was untreated in the input")
    ici_named = bool(_ICI_RE.search(title_text + " | " + modality))
    if current == "supporting_or_context" and not ici_named and clause_signal(title_text + " | " + modality, _VACCINE_RE):
        return ("VACCINE_OR_ADOPTIVE_CELL", "REG-5-VACCINE-OR-CELL-THERAPY",
                "title or modality names a vaccine or adoptive-cell study and no ICI")
    if (current == "supporting_or_context" and not ici_named and clause_signal(title_text + " | " + modality, _MECH_RE)
            and not _PATIENT_RE.search(title_text)):
        return ("MECHANISTIC_CELL_MODEL", "REG-6-MECHANISTIC-OR-PRECLINICAL",
                "title or modality names a cell line, organoid, xenograft or preclinical model and no patient cohort")
    if current == "supporting_or_context" and not ici_named and clause_signal(title_text, _NONICI_RE):
        return ("NON_ICI_TREATMENT", "REG-7-NON-ICI-TREATMENT",
                "title names a non-ICI treatment and no ICI")
    if current == "supporting_or_context" and _REGIMEN_NOT_DOCUMENTED_RE.search(row.get("usefulness", "") or ""):
        return ("UNRESOLVED", "REG-3D-REGIMEN-NOT-DOCUMENTED",
                "the ICI regimen and ORR are not documented in the input, so untreated status is not established; "
                "resolution: check the original publication for the treatment context")
    if current == "supporting_or_context" and clause_signal(
            " | ".join([row.get("usefulness", "") or "", row.get("verified_title", "") or ""]), _TREATMENT_NAIVE_RE):
        return ("UNRESOLVED", "REG-3E-TREATMENT-NAIVE-UNCONFIRMED",
                "treatment-naive wording describes sampling status and does not establish that no ICI was given; "
                "untreated status is not established; resolution: check the original publication for the treatment context")
    if not identifiers:
        hosts = _locator_hosts(row)
        if hosts:
            return ("UNRESOLVED", "REG-8-LOCATOR-TYPE-UNSUPPORTED",
                    "public locator present (" + ", ".join(hosts) + ") but its identifier type was not extracted "
                    "by the reconciler; resolution path required before the lead can be traced")
        return ("UNRESOLVED", "REG-8-NO-IDENTIFIER",
                "no public identifier or locator in the queue row; lead cannot be traced")
    if current == "blocked":
        return ("UNRESOLVED", "REG-9-BLOCKED-OTHER",
                "registry blocked; access, object or identity not verified")
    return ("INCLUDED_AS_LEAD", "REG-10-SUPPORTING-LEAD",
            "supporting or context row with an identifier; retained as a lead for DAV-T03 screening only")


def _disposition_for_epigenetic(record):
    row, identifiers = record["row"], record["identifiers"]
    immuno = row.get("immunotherapy", "") or ""
    if immuno.strip().lower() in ("", "none"):
        return ("NON_ICI_TREATMENT", "EPI-3-NO-ICI",
                "no ICI named in the survey index; supporting inventory only, not the Paper A clinical denominator")
    if _ICI_RE.search(immuno) and _AMBIGUOUS_REGIMEN_RE.search(immuno):
        return ("UNRESOLVED", "EPI-2-ICI-AMBIGUOUS-REGIMEN",
                "UNRESOLVED-regimen: ICI named but its place in the profiled regimen is ambiguous; regimen UNKNOWN pending DAV-T06")
    if _ICI_RE.search(immuno):
        return ("INCLUDED_AS_LEAD", "EPI-1-ICI-CLINICAL-LEAD",
                "candidate clinical-ICI lead (historical survey); regimen UNKNOWN pending DAV-T06")
    return ("UNRESOLVED", "EPI-4-UNCLASSIFIED-IMMUNOTHERAPY",
            "immunotherapy field not classifiable by the declared rules")


# Round 5 (user decision): free-text rules may only PROPOSE an excluding disposition. An exclusion takes effect only
# from a structured-field rule or from an explicit per-row reviewer confirmation (apply_confirmations).
STRUCTURAL_EXCLUSION_RULES = frozenset({
    "REG-2-BLOCKED-CONTROLLED",   # registry current_disposition == blocked AND a controlled-access identifier kind
    "EPI-3-NO-ICI",               # epigenetic immunotherapy field, normalised, exactly "" or "none"
})
PROPOSAL_EXCLUSION_RULES = frozenset({
    "REG-3-BLOCKED-OVERLAP", "REG-3B-INTEGRATED-RESOURCE", "REG-3C-AFFIRMATIVE-UNTREATED",
    "REG-4-NONMOLECULAR-MODALITY", "REG-5-VACCINE-OR-CELL-THERAPY", "REG-6-MECHANISTIC-OR-PRECLINICAL",
    "REG-7-NON-ICI-TREATMENT",
})
EXCLUDING_CODES = frozenset(DISPOSITION_CODES) - {"INCLUDED_AS_LEAD", "UNRESOLVED"}


def _disposition(record):
    """Returns (code, rule, reason, proposal). An excluding code from a free-text rule becomes a proposal."""
    if record["tag"] == "REG":
        code, rule, reason = _disposition_for_registry(record)
    else:
        code, rule, reason = _disposition_for_epigenetic(record)
    if code in EXCLUDING_CODES and rule not in STRUCTURAL_EXCLUSION_RULES:
        if rule not in PROPOSAL_EXCLUSION_RULES:
            _fail("UNCLASSIFIED_EXCLUSION", f"rule {rule} excludes but is in neither rule class")
        proposal = {"proposed_disposition": code, "proposed_rule_id": rule, "proposed_reason": reason}
        return ("UNRESOLVED", "PROPOSED:" + rule,
                f"proposed {code} by {rule}: {reason}; awaiting independent reviewer confirmation", proposal)
    return code, rule, reason, None


_RECEIPT_DIR = "docs/validation/A_DAV_04/"
AUTHORITY_SCHEMA = "A-DAV-04.confirmation_authorities.1"
_PLACEHOLDER_WORDS = frozenset({"", "tbd", "todo", "n/a", "na", "none", "unknown", "placeholder", "reviewer",
                                "reviewer name", "xxx", "x"})
_FORBIDDEN_ROLE_RE = re.compile(r"implement|coordinat", re.I)
# The receipt's decision words map explicitly onto the file's decision words.
_BLOCK_TO_FILE_DECISION = {"confirm": "confirmed", "reject": "rejected"}
_ENTRY_FIELDS = ("row_id", "decision", "confirmed_disposition", "proposed_rule_id", "reviewer", "reviewer_role",
                 "receipt_path", "receipt_sha256", "evidence_note")


def _is_placeholder(value):
    text = (value or "").strip()
    lowered = text.lower()
    return (lowered in _PLACEHOLDER_WORDS or "placeholder" in lowered or text.startswith(("<", "{"))
            or lowered.startswith("reviewer name"))


def _receipt_path_allowed(path):
    return (isinstance(path, str) and path.startswith(_RECEIPT_DIR) and "\\" not in path
            and ".." not in path.split("/") and not path.startswith("/"))


_BLOCK_BEGIN = "BEGIN_CONFIRMATIONS_JSON"
_BLOCK_END = "END_CONFIRMATIONS_JSON"
# Receipt-structure failures: each one makes the receipt's authority unusable (R7-AUTH-03).
RECEIPT_STRUCTURE_CODES = frozenset({"CONFIRMATION_RECEIPT_AMBIGUOUS", "CONFIRMATION_RECEIPT_MALFORMED",
                                     "CONFIRMATION_BLOCK_MISSING", "CONFIRMATION_BLOCK_INVALID"})


def _parse_confirmation_block(receipt_bytes):
    """The single BEGIN_CONFIRMATIONS_JSON ... END_CONFIRMATIONS_JSON block of a receipt, optionally fenced.

    A receipt must contain exactly one balanced block. Zero blocks fail as missing; unbalanced or reversed markers
    fail as malformed; more than one block (including nested markers) fails as ambiguous (R7-AUTH-03).
    """
    text = receipt_bytes.decode("utf-8", errors="strict")
    begins = [m.start() for m in re.finditer(re.escape(_BLOCK_BEGIN), text)]
    ends = [m.start() for m in re.finditer(re.escape(_BLOCK_END), text)]
    if not begins and not ends:
        _fail("CONFIRMATION_BLOCK_MISSING", "receipt has no BEGIN_CONFIRMATIONS_JSON block")
    if len(begins) != len(ends):
        _fail("CONFIRMATION_RECEIPT_MALFORMED", "receipt markers are unbalanced")
    if len(begins) > 1:
        _fail("CONFIRMATION_RECEIPT_AMBIGUOUS", f"receipt contains {len(begins)} confirmation blocks; exactly one is allowed")
    if ends[0] < begins[0]:
        _fail("CONFIRMATION_RECEIPT_MALFORMED", "receipt END marker precedes its BEGIN marker")
    inner_text = text[begins[0] + len(_BLOCK_BEGIN):ends[0]]
    inner = re.sub(r"^\s*```[A-Za-z]*\s*|\s*```\s*$", "", inner_text.strip()).strip()
    try:
        block = json.loads(inner)
    except ValueError:
        _fail("CONFIRMATION_BLOCK_INVALID", "confirmations block is not valid JSON")
    if not isinstance(block, list) or not all(isinstance(item, dict) for item in block):
        _fail("CONFIRMATION_BLOCK_INVALID", "confirmations block must be a JSON list of objects")
    row_counts = Counter(item.get("row_id") for item in block)
    repeated = sorted(str(row) for row, count in row_counts.items() if count > 1)
    if repeated:
        # R6-AUTH-02: any repeated row (identical, conflicting, or a different rule) makes the receipt ambiguous.
        _fail("CONFIRMATION_RECEIPT_AMBIGUOUS", f"receipt repeats row entries: {', '.join(repeated)}")
    return block


def _authority_for(authorities, path, sha):
    if not isinstance(authorities, dict) or authorities.get("schema") != AUTHORITY_SCHEMA:
        _fail("AUTHORITIES_INVALID", "authority document has the wrong schema")
    for authority in authorities.get("authorities", []):
        if authority.get("receipt_path") == path and authority.get("receipt_sha256") == sha:
            return authority
    _fail("CONFIRMATION_AUTHORITY_UNLISTED", f"{path} at {sha[:12]} is not a listed confirmation authority")


def _check_entry(entry, authorities, receipt_bytes):
    """Authority and content binding for one confirmation entry. Raises QueueReconciliationError (fail closed)."""
    row_id = entry["row_id"]
    if entry["decision"] not in ("confirmed", "rejected"):
        _fail("CONFIRMATION_DECISION_INVALID", f"{row_id}: decision must be confirmed or rejected")
    if _is_placeholder(entry["reviewer"]) or _is_placeholder(entry["reviewer_role"]):
        _fail("CONFIRMATION_PLACEHOLDER_REVIEWER", f"{row_id}: reviewer is a placeholder")
    if not _receipt_path_allowed(entry["receipt_path"]):
        _fail("CONFIRMATION_PATH_OUTSIDE_ALLOWED", f"{row_id}: receipt path not under {_RECEIPT_DIR}")
    digest = str(entry["receipt_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        _fail("CONFIRMATION_BAD_HASH_FORMAT", f"{row_id}: receipt_sha256 is not 64 lowercase hex")
    authority = _authority_for(authorities, entry["receipt_path"], digest)
    if _FORBIDDEN_ROLE_RE.search(entry["reviewer_role"]) or _FORBIDDEN_ROLE_RE.search(authority["reviewer_role"]):
        _fail("CONFIRMATION_ROLE_FORBIDDEN", f"{row_id}: an implementer or coordinator is not an independent authority")
    if entry["reviewer"] != authority["reviewer"] or entry["reviewer_role"] != authority["reviewer_role"]:
        _fail("CONFIRMATION_AUTHORITY_MISMATCH", f"{row_id}: reviewer does not equal the listed authority")
    if entry["receipt_path"] not in receipt_bytes:
        _fail("CONFIRMATION_RECEIPT_MISSING", f"{row_id}: caller did not supply {entry['receipt_path']}")
    if hashlib.sha256(receipt_bytes[entry["receipt_path"]]).hexdigest() != digest:
        _fail("CONFIRMATION_HASH_MISMATCH", f"{row_id}: receipt bytes do not hash to the authority sha256")
    block = _parse_confirmation_block(receipt_bytes[entry["receipt_path"]])
    wanted = "confirm" if entry["decision"] == "confirmed" else "reject"
    for item in block:
        if (item.get("row_id") == row_id and item.get("proposed_rule_id") == entry["proposed_rule_id"]
                and item.get("decision") == wanted
                and (entry["decision"] == "rejected" or item.get("confirmed_disposition") == entry["confirmed_disposition"])):
            return authority
    _fail("CONFIRMATION_NOT_IN_RECEIPT", f"{row_id}: no matching entry in the authority receipt's block")


def _structural_holds(rule, fields):
    """Re-evaluates a structural predicate on the fields of a row (R5-AUTH-01). Absence never satisfies a predicate
    (R7-STRUCT-01): every field must be present, and an EPI-3 value must be an explicit string."""
    if rule == "REG-2-BLOCKED-CONTROLLED":
        if "current_disposition" not in fields or "identifier_kinds" not in fields:
            return False
        return (fields["current_disposition"] == "blocked"
                and bool(set(fields["identifier_kinds"] or []) & set(CONTROLLED_KINDS)))
    if rule == "EPI-3-NO-ICI":
        value = fields.get("immunotherapy")
        if "immunotherapy" not in fields or not isinstance(value, str):
            return False
        return value.strip().lower() in ("", "none")
    return False


def structural_inputs_for(rows, epi_rows):
    """The fields the structural predicates read, keyed by row_id.

    Fail closed on ambiguity (R8-STRUCT-02): a row_id that occurs more than once among the rows (whatever the tag), or
    more than once among the epigenetic source rows, records NO fields, so its predicate fails and it is flagged.
    A field absent from its source is left out (R7-STRUCT-01). Nothing is resolved by last-row-wins.
    """
    row_counts = Counter(row["row_id"] for row in rows)
    epi_by_id = {}
    for source in epi_rows:
        epi_by_id.setdefault(source.get("study_id"), []).append(source)
    structural = {}
    for row in rows:
        row_id = row["row_id"]
        if row_counts[row_id] > 1:
            structural[row_id] = {}
            continue
        fields = {}
        if row["tag"] == "REG":
            if "current_disposition" in row:
                fields["current_disposition"] = row["current_disposition"]
            if isinstance(row.get("identifiers"), list):
                fields["identifier_kinds"] = [i["kind"] for i in row["identifiers"] if isinstance(i, dict) and "kind" in i]
        else:
            sources = epi_by_id.get(row_id, [])
            if len(sources) > 1:
                fields = {}
            elif len(sources) == 1 and sources[0].get("immunotherapy") is not None:
                fields["immunotherapy"] = sources[0]["immunotherapy"]
        structural[row_id] = fields
    return structural


def recount(counts, rows):
    """Recomputes every count that depends on the dispositions, from the applied rows (R6-STATE-02)."""
    tallies = Counter(row["disposition"] for row in rows)
    updated = dict(counts)
    updated["in_scope_total"] = len(rows)
    updated["dispositioned_total"] = sum(tallies.values())
    updated["unresolved_no_identifier_rows"] = sum(1 for row in rows if row["cluster_id"] is None)
    updated["disposition_tallies"] = {code: tallies.get(code, 0) for code in DISPOSITION_CODES}
    return updated


def finalize(result, confirmations, receipt_bytes, authorities, epi_rows):
    """reconcile -> apply_confirmations -> authority_violations (must be empty) -> recount. Pure; returns a new
    result. Every artifact must be generated from this result, so no stored count can predate the confirmations."""
    applied = apply_confirmations(result["dispositioned_rows"], confirmations, receipt_bytes, authorities)
    structural = structural_inputs_for(applied, epi_rows)
    unauthorised = authority_violations(applied, confirmations, receipt_bytes, authorities, structural)
    if unauthorised:
        _fail("AUTHORITY_VIOLATION", f"exclusions without authority: {unauthorised}")
    out = dict(result)
    out["dispositioned_rows"] = applied
    out["counts"] = recount(result["counts"], applied)
    return out


def apply_confirmations(dispositioned_rows, confirmations, receipt_bytes, authorities):
    """Pure. Applies explicit reviewer confirmations or rejections to proposed rows, failing closed.

    authorities is the parsed CONFIRMATION_AUTHORITIES.json; receipt_bytes maps receipt path to the bytes the caller
    read (the module performs no I/O). Returns a new list of rows. A rejected entry leaves the row UNRESOLVED.
    """
    rows = [dict(row) for row in dispositioned_rows]
    for row in rows:
        rule = str(row.get("rule_id", ""))
        if rule.startswith("PROPOSED:") and rule[len("PROPOSED:"):] not in PROPOSAL_EXCLUSION_RULES:
            _fail("CONFIRMATION_FORGED_PROPOSAL", f"{row['row_id']}: {rule} is not a proposal class")
    by_id = {}
    for row in rows:
        by_id.setdefault(row["row_id"], []).append(row)
    seen = set()
    for entry in confirmations:
        row_id = entry.get("row_id")
        if row_id in seen:
            _fail("CONFIRMATION_DUPLICATE_ROW", f"duplicate confirmation for row {row_id}")
        seen.add(row_id)
        if row_id not in by_id or len(by_id[row_id]) != 1:
            _fail("CONFIRMATION_ROW_UNKNOWN", f"no unique row {row_id}")
        row = by_id[row_id][0]
        if not str(row.get("rule_id", "")).startswith("PROPOSED:") or not row.get("proposed_disposition"):
            _fail("CONFIRMATION_ROW_NOT_PROPOSED", f"row {row_id} is not a proposal")
        if entry.get("proposed_rule_id") not in PROPOSAL_EXCLUSION_RULES:
            _fail("CONFIRMATION_RULE_NOT_IN_CLASS", f"{row_id}: {entry.get('proposed_rule_id')} is not a proposal class")
        for field in _ENTRY_FIELDS:
            if field != "reviewer" and not str(entry.get(field) or "").strip():
                _fail("CONFIRMATION_MISSING_FIELD", f"{row_id}: {field} is missing")
        if entry["proposed_rule_id"] != row["proposed_rule_id"]:
            _fail("CONFIRMATION_RULE_MISMATCH", f"{row_id}: proposal is {row['proposed_rule_id']}")
        if entry["decision"] == "confirmed":
            if entry["confirmed_disposition"] != row["proposed_disposition"]:
                _fail("CONFIRMATION_DISPOSITION_MISMATCH",
                      f"{row_id}: confirmed {entry['confirmed_disposition']} but proposal is {row['proposed_disposition']}")
        elif entry["decision"] == "rejected" and entry["confirmed_disposition"] != "UNRESOLVED":
            _fail("CONFIRMATION_DISPOSITION_MISMATCH", f"{row_id}: a rejection must keep UNRESOLVED")
        authority = _check_entry(entry, authorities, receipt_bytes)
        digest = entry["receipt_sha256"]
        citation = (f"{entry['reviewer']} ({entry['reviewer_role']}) in {entry['receipt_path']} "
                    f"(sha256 {digest[:12]}): {entry['evidence_note']}")
        if entry["decision"] == "confirmed":
            row["disposition"] = row["proposed_disposition"]
            row["rule_id"] = "CONFIRMED:" + row["proposed_rule_id"]
            row["reason"] = f"confirmed {row['proposed_disposition']} by {citation}"
        else:
            row["reason"] = (f"{row['reason']}; reviewer rejected proposed {row['proposed_disposition']} "
                             f"by {citation}")
    return rows


def _entry_authorises(entry, base_rule, disposition, authorities, receipt_bytes):
    if entry.get("proposed_rule_id") != base_rule or entry.get("decision") != "confirmed":
        return False
    if entry.get("confirmed_disposition") != disposition:
        return False
    try:
        _check_entry(entry, authorities, receipt_bytes)
    except QueueReconciliationError:
        return False
    return True


def authority_violations(rows, confirmations, receipt_bytes, authorities, structural_inputs):
    """Re-verifies every excluding row (and every proposal) from first principles; returns the offending row_ids.

    CONFIRMED:<rule> needs a confirmation that passes the full authority and binding checks and whose rule is a
    proposal class. A structural rule needs its predicate to hold on the row's own fields (structural_inputs, keyed
    by row_id; a missing entry is a violation). Any other excluding row, and any PROPOSED:<x> outside the classes, is
    a violation.
    """
    bad = []
    by_row = {}
    for entry in confirmations:
        by_row.setdefault(entry.get("row_id"), []).append(entry)
    for row in rows:
        rule = str(row.get("rule_id", ""))
        disposition = row.get("disposition")
        row_id = row.get("row_id")
        if rule.startswith("PROPOSED:"):
            if rule[len("PROPOSED:"):] not in PROPOSAL_EXCLUSION_RULES:
                bad.append(row_id)
            continue
        if disposition not in EXCLUDING_CODES:
            continue
        if rule in STRUCTURAL_EXCLUSION_RULES:
            fields = (structural_inputs or {}).get(row_id)
            if fields is None or not _structural_holds(rule, fields):
                bad.append(row_id)
            continue
        if rule.startswith("CONFIRMED:"):
            base = rule[len("CONFIRMED:"):]
            if base not in PROPOSAL_EXCLUSION_RULES:
                bad.append(row_id)
                continue
            # R8-STRUCT-02 / R6-AUTH-02: exactly one entry may speak for a row; a second, contrary entry is flagged
            # even if the first would authorise it.
            entries = by_row.get(row_id, [])
            if len(entries) != 1 or not _entry_authorises(entries[0], base, disposition, authorities, receipt_bytes):
                bad.append(row_id)
            continue
        bad.append(row_id)
    for entry in confirmations:
        try:
            _check_entry(entry, authorities, receipt_bytes)
        except QueueReconciliationError as error:
            if error.code in RECEIPT_STRUCTURE_CODES and entry.get("row_id") not in bad:
                bad.append(entry.get("row_id"))
    return bad


# ---------------------------------------------------------------- normalisation and clustering


def _record_from_row(tag, row):
    spec = SOURCE_SPECS[tag]
    row_id = row[spec["row_id"]]
    if not isinstance(row_id, str) or not row_id.strip():
        _fail("MALFORMED_ROW", f"{tag} row without an ID")
    if tag == "REG" and row.get("current_disposition") not in REGISTRY_DISPOSITION_MAP:
        _fail("UNKNOWN_INPUT_DISPOSITION",
              f"{row_id}: current_disposition {row.get('current_disposition')!r} is outside the closed registry vocabulary")
    if _CONTROL.search(" ".join(str(v) for v in row.values())):
        _fail("MALFORMED_ROW", f"{tag} {row_id} contains control characters")
    for value in row.values():
        if isinstance(value, str):
            try:
                sl._scan_text(value)
            except sl.SearchLogError as error:
                raise QueueReconciliationError("SECRET_LOCATOR", f"{tag} {row_id} rejected: {error.code}") from error
    identifiers = []
    for field in spec["identifier_fields"]:
        identifiers.extend(extract_identifiers(row.get(field, ""), field))
    family = row.get(spec["family_field"]) if spec["family_field"] else None
    # Direct identifiers are the row's own locators and listings. A family-label identifier is an
    # assertion only: it may suggest an association (POSSIBLE) but never merges rows or emits an alias.
    direct = [item for item in identifiers if item["field"] != spec["family_field"]]
    return {
        "tag": tag,
        "row_id": row_id,
        "intake_id": intake_id(tag, row_id),
        "row": row,
        "identifiers": identifiers,
        "direct": direct,
        "family": family,
    }


def _cluster(records):
    """Union-find over shared identifier keys. Returns {intake_id: root}."""
    parent = {}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for record in records:
        parent.setdefault(record["intake_id"], record["intake_id"])
        for item in record["direct"]:
            key = "KEY:" + item["fold"]
            parent.setdefault(key, key)
            union(record["intake_id"], key)
    return {record["intake_id"]: find(record["intake_id"]) if record["direct"] else None
            for record in records}


def _study_id_for(item):
    if item["kind"] == "DOI":
        return "QR-DOI-" + hashlib.sha256(item["fold"].encode("utf-8")).hexdigest()[:12]
    return "QR-" + re.sub(r"[^A-Za-z0-9]", "", item["fold"])


def _lead_label(cluster):
    return "CANDIDATE lead cluster; title not recorded here (see catalogue rows)"


def reconcile(sources, pipeline_utc=None):
    """Phase 1 reconciliation. sources: [{tag, path, sha256, rows}].

    Returns a dict with inputs, dispositioned_rows, out_of_scope_rows, clusters, conflicts and counts.
    Output is independent of the order of sources and rows.
    """
    if pipeline_utc is not None and not sl._utc(pipeline_utc):
        _fail("INVALID_UTC_TIMESTAMP", "pipeline_utc must be ISO-8601 UTC ending in Z")
    tags = [entry["tag"] for entry in sources]
    if len(set(tags)) != len(tags):
        _fail("DUPLICATE_ROW_ID", "each source tag may appear once")
    inputs, in_scope_records, out_of_scope = [], [], []
    for entry in sorted(sources, key=lambda item: item["tag"]):
        tag = entry["tag"]
        if tag not in SOURCE_SPECS:
            _fail("UNKNOWN_SOURCE", f"source tag {tag!r} is not declared")
        spec = SOURCE_SPECS[tag]
        if entry.get("path") != spec["path"] or entry.get("sha256") != spec["sha256"]:
            _fail("INPUT_IDENTITY_MISMATCH",
                  f"{tag} input identity does not match the frozen path and sha256 declared in SOURCE_SPECS")
        rows = sorted(entry["rows"], key=lambda row: str(row.get(spec["row_id"], "")))
        seen = set()
        scope_out = []
        scope_in_ids = []
        for row in rows:
            record = _record_from_row(tag, row)
            if record["row_id"] in seen:
                _fail("DUPLICATE_ROW_ID", f"{tag} row ID {record['row_id']} appears twice")
            seen.add(record["row_id"])
            ok, reason = scope_of(tag, row)
            if ok:
                in_scope_records.append(record)
                scope_in_ids.append(record["row_id"])
            else:
                scope_out.append({"tag": tag, "row_id": record["row_id"], "intake_id": record["intake_id"],
                                  "reason": reason})
                out_of_scope.append(scope_out[-1])
        inputs.append({
            "tag": tag,
            "path": entry["path"],
            "sha256": entry["sha256"],
            "row_count": len(rows),
            "in_scope_row_ids": scope_in_ids,
            "out_of_scope_rows": scope_out,
        })

    roots = _cluster(in_scope_records)
    members = {}
    for record in in_scope_records:
        if roots[record["intake_id"]] is not None:
            members.setdefault(roots[record["intake_id"]], []).append(record)

    cluster_for_root = {}
    for root, group in members.items():
        keyed = sorted({item["fold"]: item for record in group for item in record["direct"]}.values(),
                       key=_identifier_sort_key)
        primary = keyed[0]
        study_id = _study_id_for(primary)
        cluster_for_root[root] = study_id
    if len(set(cluster_for_root.values())) != len(cluster_for_root):
        _fail("DUPLICATE_ROW_ID", "two clusters derive the same study ID")

    dispositioned = []
    for record in in_scope_records:
        code, rule, reason, proposal = _disposition(record)
        if code not in DISPOSITION_CODES:
            _fail("MALFORMED_ROW", f"rule {rule} produced an undeclared code")
        root = roots[record["intake_id"]]
        dispositioned.append({
            "tag": record["tag"],
            "row_id": record["row_id"],
            "intake_id": record["intake_id"],
            "disposition": code,
            "rule_id": rule,
            "reason": reason,
            "cluster_id": cluster_for_root.get(root) if root is not None else None,
            "identifiers": [{"kind": item["kind"], "fold": item["fold"], "field": item["field"],
                             "derived": item["derived"]} for item in record["identifiers"]],
            "family": record["family"],
            "current_disposition": record["row"].get("current_disposition") if record["tag"] == "REG" else None,
            "current_primary_disposition": (record["row"].get("current_primary_disposition")
                                            if record["tag"] == "REG" else None),
            **(proposal or {}),
        })
    dispositioned.sort(key=lambda row: (row["tag"], row["row_id"]))

    clusters = []
    for root in sorted(members, key=lambda r: cluster_for_root[r]):
        group = sorted(members[root], key=lambda record: record["intake_id"])
        study_id = cluster_for_root[root]
        keyed = {}
        for record in group:
            for item in record["direct"]:
                entry = keyed.setdefault(item["fold"], {"kind": item["kind"], "fold": item["fold"], "raw": set(),
                                                        "fields": set(), "derived": True})
                entry["raw"].add(item["raw"])
                entry["fields"].add(item["field"])
                entry["derived"] = entry["derived"] and item["derived"]
        clusters.append({
            "study_id": study_id,
            "row_refs": sorted((record["tag"], record["row_id"]) for record in group),
            "row_ids": sorted(record["row_id"] for record in group),
            "tags": sorted({record["tag"] for record in group}),
            "intake_ids": [record["intake_id"] for record in group],
            "identifiers": [{"kind": v["kind"], "fold": v["fold"], "raw": sorted(v["raw"]),
                             "fields": sorted(v["fields"]), "derived_only": v["derived"]}
                            for _, v in sorted(keyed.items(), key=lambda kv: (
                                KIND_PRIORITY.index(kv[1]["kind"]), kv[0]))],
            "source_families": sorted({record["family"] for record in group if record["family"]}),
        })

    family_index = {}
    for record in in_scope_records:
        if record["tag"] != "REG":
            continue
        root = roots[record["intake_id"]]
        cluster = cluster_for_root.get(root) if root is not None else None
        for item in record["identifiers"]:
            if item["field"] == SOURCE_SPECS["REG"]["family_field"]:
                family_index.setdefault(item["fold"], []).append((cluster, record["row_id"]))
    family_associations = []
    for fold in sorted(family_index):
        entries_for_fold = family_index[fold]
        clusters_seen = sorted({c for c, _ in entries_for_fold if c is not None})
        if len(clusters_seen) >= 2:
            family_associations.append({
                "identifier": fold,
                "clusters": clusters_seen,
                "rows": sorted(r for _, r in entries_for_fold),
                "certainty": "POSSIBLE",
                "resolution": "NOT_MERGED",
                "evidence": "source_family label assertion",
                "note": "candidate association only; not a canonical merge and not an alias",
            })
    for cluster in clusters:
        cluster["family_assertion_ids"] = sorted({
            item["fold"] for record in members[next(r for r, c in cluster_for_root.items() if c == cluster["study_id"])]
            for item in record["identifiers"] if item["field"] == SOURCE_SPECS["REG"]["family_field"]})

    conflicts = _conflicts(in_scope_records, roots, cluster_for_root)
    tallies = Counter(row["disposition"] for row in dispositioned)
    counts = {
        "input_rows_total": sum(entry["row_count"] for entry in inputs),
        "in_scope_total": len(dispositioned),
        "out_of_scope_total": len(out_of_scope),
        "dispositioned_total": sum(tallies.values()),
        "candidate_study_count": len(clusters),
        "unresolved_no_identifier_rows": sum(1 for row in dispositioned if row["cluster_id"] is None),
        "disposition_tallies": {code: tallies.get(code, 0) for code in DISPOSITION_CODES},
        "conflict_counts": dict(sorted(Counter(c["code"] for c in conflicts).items())),
    }
    return {
        "receipt_schema": RECEIPT_SCHEMA,
        "ticket": TICKET,
        "pipeline_utc": pipeline_utc,
        "status": PROPOSED_STATUS,
        "admitted_count": ADMITTED_COUNT,
        "analysis_readiness": ANALYSIS_READINESS,
        "inputs": inputs,
        "dispositioned_rows": dispositioned,
        "out_of_scope_rows": sorted(out_of_scope, key=lambda row: (row["tag"], row["row_id"])),
        "clusters": clusters,
        "family_associations": family_associations,
        "conflicts": conflicts,
        "counts": counts,
        "_records": in_scope_records,
        "_roots": roots,
        "_cluster_for_root": cluster_for_root,
    }


def _conflicts(records, roots, cluster_for_root):
    conflicts = []
    by_key = {}
    for record in records:
        for item in record["identifiers"]:
            by_key.setdefault(item["fold"], []).append(record)
    for fold in sorted(by_key):
        group = by_key[fold]
        families = sorted({record["family"] for record in group if record["family"]})
        if len(families) > 1:
            conflicts.append({
                "code": "ACCESSION_ALIAS_CONFLICT",
                "identifiers": [fold],
                "families": families,
                "rows": sorted(record["row_id"] for record in group),
                "resolution": "UNRESOLVED_NOT_MAJORITY",
            })
    family_rows = {}
    for record in records:
        if record["tag"] == "REG" and record["family"]:
            family_rows.setdefault(record["family"], []).append(record)
    for family in sorted(family_rows):
        group = family_rows[family]
        studies = {cluster_for_root.get(roots[record["intake_id"]]) for record in group}
        studies.discard(None)
        if len(studies) > 1:
            conflicts.append({
                "code": "FAMILY_LABEL_SPLIT",
                "family": family,
                "rows": sorted(record["row_id"] for record in group),
                "candidate_study_count": len(studies),
                "resolution": "UNRESOLVED_NOT_MAJORITY",
            })
    for record in records:
        if record["tag"] != "REG" or not record["family"]:
            continue
        family_keys = {}
        url_keys = {}
        for item in record["identifiers"]:
            target = family_keys if item["field"] == "source_family" else url_keys
            target.setdefault(item["kind"], set()).add(item["fold"])
        for kind in sorted(set(family_keys) & set(url_keys)):
            if not family_keys[kind] & url_keys[kind]:
                conflicts.append({
                    "code": "FAMILY_IDENTIFIER_DISAGREEMENT",
                    "row": record["row_id"],
                    "kind": kind,
                    "identifiers": sorted(family_keys[kind] | url_keys[kind]),
                    "resolution": "UNRESOLVED_NOT_MAJORITY",
                })
    for record in records:
        if record["tag"] == "REG" and record["row"].get("current_disposition") != record["row"].get(
                "current_primary_disposition"):
            conflicts.append({
                "code": "DISPOSITION_FIELD_DISAGREEMENT",
                "row": record["row_id"],
                "current_disposition": record["row"].get("current_disposition"),
                "current_primary_disposition": record["row"].get("current_primary_disposition"),
                "resolution": "UNRESOLVED_NOT_MAJORITY",
            })
    return sorted(conflicts, key=lambda c: (c["code"], json.dumps(c, sort_keys=True)))


# ---------------------------------------------------------------- candidate packets


def _locator_file(tag, row_id, field=None):
    path = SOURCE_SPECS[tag]["path"]
    section = f"row {row_id}" + (f"; field {field}" if field else "")
    return {"kind": "FILE", "value": path, "page_or_section": section}


def _packet_for_record(record, disposition, cluster_study):
    facts = []
    for item in record["identifiers"]:
        facts.append({
            "claim": f"queue row {record['row_id']} lists {item['kind']} identifier {item['raw_value']} "
                     f"in field {item['field']}",
            "source_locator": _locator_file(record["tag"], record["row_id"], item["field"]),
        })
    if not facts:
        facts.append({
            "claim": f"queue row {record['row_id']} is present in the input file",
            "source_locator": _locator_file(record["tag"], record["row_id"]),
        })
    content = {
        "lane": LANE_CATALOGUE,
        "query_ids": [record["intake_id"]],
        "candidate_label": f"{record['tag']} {record['row_id']} queue lead",
        "verified_facts": facts,
        "inferences": [{
            "statement": f"historical lead disposition {disposition['disposition']} "
                         f"({disposition['rule_id']}); not a verified fact",
            "supporting_fact_indices": [0],
        }],
        "unknowns": [{
            "field": "clinical_fields_and_original_source",
            "resolution_path": "DAV-T03 object verification, then DAV-T05/T06 curation",
            "blocking_branches": ["paper_A_clinical_denominator"],
        }],
        "proposed_records": {"study_id": cluster_study, "disposition": disposition["disposition"]},
        "suspected_overlap": [],
        "recommended_next_action": "DAV-T02 provisional decision carried forward; DAV-T03 for included leads",
        "agent_id": AGENT_ID,
        "completed_utc": None,
    }
    return content


def build_packets(result, phase2=None):
    """One candidate packet per in-scope row (DAV-T01 contract). Phase 2 packets are appended."""
    pipeline = result["pipeline_utc"]
    if pipeline is None:
        _fail("INVALID_UTC_TIMESTAMP", "packets need a pipeline_utc")
    by_intake = {record["intake_id"]: record for record in result["_records"]}
    packets = []
    for row in result["dispositioned_rows"]:
        record = by_intake[row["intake_id"]]
        raw_record = {"tag": record["tag"], "row_id": record["row_id"], "intake_id": record["intake_id"],
                      "identifiers": [dict(item, raw_value=item["raw"]) for item in record["identifiers"]]}
        content = _packet_for_record(raw_record, row, row["cluster_id"])
        content["completed_utc"] = pipeline
        packets.append(_validated_packet(content, valid_query_ids(result, phase2)))
    if phase2 is not None:
        packets.extend(phase2["packets"])
    return packets


def _validated_packet(content, valid_ids):
    packet = {"packet_id": sl.candidate_packet_id(content), **content}
    sl.validate_candidate_packet(packet, set(valid_ids))
    return packet


def valid_query_ids(result, phase2=None):
    ids = {row["intake_id"] for row in result["dispositioned_rows"]}
    if phase2 is not None:
        ids |= {run["query_id"] for run in phase2["search_runs"]}
    return sorted(ids)


# ---------------------------------------------------------------- decision and proposed records


def _study_entry(cluster, notes_extra):
    tags = cluster["tags"]
    notes = ("historical lead cluster from " + ",".join(tags) + "; rows " + ",".join(cluster["row_ids"])
             + "; source families asserted by input (not reproduced by identifiers): "
             + (",".join(cluster["source_families"]) or "none") + "; " + notes_extra)
    return {
        "study_id": cluster["study_id"],
        "publication_family_id": "FAM-" + cluster["study_id"][3:],
        "study_title": _lead_label(cluster),
        "study_class": "OTHER",
        "cancer_type": "UNKNOWN",
        "study_design": "UNKNOWN",
        "candidate_paper_branches": ["UNKNOWN"],
        "access_status": "UNKNOWN",
        "source_repositories": [],
        "source_locators": [_locator_file(tag, row_id) for tag, row_id in _rows_for(cluster)],
        "treatment_regimen_id": "UNKNOWN" if "EPI" in cluster["tags"] else None,
        "notes": notes,
    }


def _rows_for(cluster):
    return [tuple(pair) for pair in cluster["row_refs"]]


def build_decision(result, phase2=None):
    """Provisional integrator decision for resolve(). Certainty is PROBABLE at most in Phase 1."""
    pipeline = result["pipeline_utc"]
    packets = build_packets(result, phase2=None)
    studies, aliases, publications = [], [], []
    alias_seen = set()
    pub_seen = set()
    record_by_row = {}
    for record in result["_records"]:
        record_by_row[(record["tag"], record["row_id"])] = record
    dispositions = {(row["tag"], row["row_id"]): row for row in result["dispositioned_rows"]}
    associations_by_cluster = {}
    for assoc in result.get("family_associations", []):
        for study_id in assoc["clusters"]:
            others = [c for c in assoc["clusters"] if c != study_id]
            associations_by_cluster.setdefault(study_id, []).append(
                f"POSSIBLE association via source_family accession {assoc['identifier']} with {', '.join(others)} "
                f"(not merged; not an alias)")
    for cluster in result["clusters"]:
        extra = "; ".join(
            f"{tag} {row_id}={dispositions[(tag, row_id)]['disposition']}" for tag, row_id in _rows_for(cluster))
        if associations_by_cluster.get(cluster["study_id"]):
            extra += "; " + "; ".join(associations_by_cluster[cluster["study_id"]])
        study = _study_entry(cluster, extra)
        studies.append(study)
        for tag, row_id in _rows_for(cluster):
            record = record_by_row[(tag, row_id)]
            for item in record["direct"]:
                alias_type = ALIAS_TYPE_FOR_KIND.get(item["kind"])
                if alias_type is None:
                    continue
                certainty = "POSSIBLE" if (item["derived"] or item["field"] == "source_family") else "PROBABLE"
                for raw in [item["raw"]]:
                    row_alias = {
                        "alias_type": alias_type,
                        "alias_value": raw,
                        "canonical_study_id": cluster["study_id"],
                        "source_locator": _locator_file(tag, row_id, item["field"]),
                        "evidence_type": ALIAS_EVIDENCE_PROBABLE,
                        "certainty": certainty,
                        "notes": "identifier folded " + item["fold"] + ("; derived from URL pattern" if item["derived"] else ""),
                    }
                    key = json.dumps(row_alias, sort_keys=True)
                    if key not in alias_seen:
                        alias_seen.add(key)
                        aliases.append(row_alias)
                if item["kind"] in ("PMID", "DOI"):
                    pub_key = (item["kind"], item["fold"])
                    if pub_key not in pub_seen and _publication_valid(item):
                        pub_seen.add(pub_key)
                        publications.append(_publication_entry(cluster, item, tag, row_id))
    for row in result["dispositioned_rows"]:
        if row["cluster_id"] is None:
            record = record_by_row[(row["tag"], row["row_id"])]
            label = record["family"] if record["family"] else row["row_id"]
            aliases.append({
                "alias_type": "CATALOGUE_LABEL",
                "alias_value": label,
                "canonical_study_id": "UNKNOWN",
                "source_locator": _locator_file(row["tag"], row["row_id"]),
                "evidence_type": ALIAS_EVIDENCE_PROBABLE,
                "certainty": "UNRESOLVED",
                "notes": "catalogue label of a row with no public identifier; unresolved",
            })
    aliases = _apply_phase2_aliases(aliases, phase2, studies)
    studies = _apply_phase2_repositories(studies, aliases)
    packet_ids = sorted({packet["packet_id"] for packet in packets})
    if phase2 is not None:
        packet_ids = sorted(set(packet_ids) | {packet["packet_id"] for packet in phase2["packets"]})
    return {
        "decision_id": PHASE2_DECISION_ID if phase2 is not None else PHASE1_DECISION_ID,
        "reviewer": PROVISIONAL_REVIEWER,
        "decided_utc": pipeline,
        "provisional": True,
        "packet_ids": packet_ids,
        "studies": studies,
        "aliases": aliases,
        "publications": publications,
        "superseries": [],
        "overlap_flags": [],
    }


def _publication_valid(item):
    if item["kind"] == "PMID":
        return re.fullmatch(r"[1-9]\d{0,8}", item["raw"]) is not None
    return re.fullmatch(r"10\.\d{4,9}/\S+", _clean_doi(item["raw"])) is not None


def _publication_entry(cluster, item, tag, row_id):
    pid = ("PUB-PMID" + item["fold"][4:]) if item["kind"] == "PMID" else \
        ("PUB-DOI-" + hashlib.sha256(item["fold"].encode("utf-8")).hexdigest()[:12])
    entry = {
        "publication_id": pid,
        "study_id": cluster["study_id"],
        "publication_family_id": "FAM-" + cluster["study_id"][3:],
        "publication_role": "OTHER",
        "doi": _clean_doi(item["raw"]) if item["kind"] == "DOI" else None,
        "pmid": item["raw"] if item["kind"] == "PMID" else None,
        "source_locators": [_locator_file(tag, row_id, item["field"])],
        "notes": "historical lead publication; role not established; independence unresolved",
        "independence_claim": "UNRESOLVED",
    }
    return entry


def _apply_phase2_aliases(aliases, phase2, studies):
    if phase2 is None:
        return aliases
    out = list(aliases)
    for upgrade in phase2["verified_aliases"]:
        out.append({
            "alias_type": upgrade["alias_type"],
            "alias_value": upgrade["alias_value"],
            "canonical_study_id": upgrade["study_id"],
            "source_locator": upgrade["locator"],
            "evidence_type": upgrade["evidence_type"],
            "certainty": "VERIFIED",
            "notes": "Phase 2 verified by " + upgrade["query_id"] + ": " + upgrade["claim"],
        })
    return sorted(out, key=lambda row: json.dumps(row, sort_keys=True))


def _apply_phase2_repositories(studies, aliases):
    verified_geo = {}
    for row in aliases:
        if row["certainty"] == "VERIFIED" and row["alias_type"] == "GEO_SERIES":
            verified_geo.setdefault(row["canonical_study_id"], set()).add(row["alias_value"])
    for study in studies:
        values = sorted(verified_geo.get(study["study_id"], set()))
        study["source_repositories"] = ["GEO:" + value.upper() for value in values]
    return studies


def proposed_records(result, study_schema, publication_schema, phase2=None):
    """Run resolve() over the packets and the provisional decision. Returns the resolve() output."""
    packets = build_packets(result, phase2=phase2)
    decision = build_decision(result, phase2=phase2)
    return sr.resolve(packets, decision, set(valid_query_ids(result, phase2)), study_schema, publication_schema)


# ---------------------------------------------------------------- Phase 2 (bounded public metadata)


def _url(endpoint, params):
    query = "&".join(f"{key}={quote(str(value), safe='')}" for key, value in params)
    return f"{EUTILS_BASE}{endpoint}.fcgi?{query}&tool={PHASE2_TOOL}"


def _esearch(db, term):
    return _url("esearch", [("db", db), ("term", term), ("retmode", "json"), ("retstart", 0), ("retmax", 20)])


def _esummary(db, ids):
    return _url("esummary", [("db", db), ("id", ",".join(ids)), ("retmode", "json")])


def _elink(dbfrom, db, ids):
    return _url("elink", [("dbfrom", dbfrom), ("db", db), ("id", ",".join(ids)), ("retmode", "json")])


def _priority_identifiers(result):
    """Priority subset: registry primary candidates and in-scope epigenetic ICI leads (see phase2_plan)."""
    rows = []
    for row in result["dispositioned_rows"]:
        if row["tag"] == "REG" and row["current_disposition"] == "primary_candidate_pending_private":
            rows.append(row)
        elif row["tag"] == "EPI" and row["rule_id"] in ("EPI-1-ICI-CLINICAL-LEAD", "EPI-2-ICI-AMBIGUOUS-REGIMEN"):
            rows.append(row)
    keys = {}
    for row in rows:
        for item in row["identifiers"]:
            entry = keys.setdefault((item["kind"], item["fold"]), {"kind": item["kind"], "fold": item["fold"],
                                                                 "rows": set(), "cluster": row["cluster_id"]})
            entry["rows"].add((row["tag"], row["row_id"]))
    return keys


def phase2_plan(result):
    """Static Phase 2 plan (before any response). Deterministic, in execution order."""
    keys = _priority_identifiers(result)
    requests = []

    def add(kind, lane, url, target, rows):
        requests.append({"kind": kind, "lane": lane, "url": url, "target": target,
                         "priority_rows": sorted(rows)})

    gse = sorted(fold for (k, fold) in keys if k == "GSE")
    for fold in gse:
        rows = [r for (tag, r) in keys[("GSE", fold)]["rows"]]
        add("esearch_gds_accn", LANE_REPOSITORY, _esearch("gds", f"{fold}[ACCN]"), {"gse": fold}, rows)
    pmids = sorted(fold[4:] for (k, fold) in keys if k == "PMID")
    if pmids:
        add("esummary_pubmed_batch", LANE_PUBLICATION, _esummary("pubmed", pmids), {"pmids": pmids},
            [r for (k, f), v in keys.items() if k == "PMID" for (tag, r) in v["rows"]])
    for (kind, fold), entry in sorted(keys.items()):
        if kind == "DOI":
            doi = fold[3:]
            add("esearch_pubmed_doi", LANE_PUBLICATION, _esearch("pubmed", f"{doi}[DOI]"), {"doi": doi},
                [r for (tag, r) in entry["rows"]])
    for (kind, fold), entry in sorted(keys.items()):
        if kind == "PMCID":
            pmc = fold[3:]
            add("elink_pmc_pubmed", LANE_PUBLICATION, _elink("pmc", "pubmed", [pmc]), {"pmc": pmc},
                [r for (tag, r) in entry["rows"]])
    numbered = []
    for index, request in enumerate(requests, start=1):
        numbered.append(dict(request, query_id=f"A-DAV-04-P2-Q{index:03d}"))
    if len(numbered) > PHASE2_REQUEST_CAP:
        _fail("PHASE2_CAP_EXCEEDED", "static plan exceeds the Phase 2 request cap")
    return numbered


def geo_series_uid(gse):
    """GEO DataSets UID of a series: 200000000 plus the accession number (as in A-DAV-03).

    This is a candidate only. It is used only when the accession search lists it, and it is
    accepted only when the sample-free esummary accession equals the target.
    """
    digits = re.search(r"\d+", gse).group(0)
    return str(200000000 + int(digits))


def phase2_followups(result, executed):
    """Requests that depend on earlier responses. IDs derive from the parent query (stable, order-free).

    A GEO accession search with a candidate DataSet UID yields "<parent>-F1" (sample-free esummary
    view) and "<parent>-F2" (elink to PubMed). A DOI search with exactly one PubMed hit yields
    "<parent>-F1" (PubMed esummary). Only successful responses contribute.
    """
    static = {request["query_id"]: request for request in phase2_plan(result)}
    out = []
    for response in executed:
        plan_entry = static.get(response.get("query_id"))
        if plan_entry is None or response.get("http_status") != 200:
            continue
        try:
            data = json.loads(response["body"])
        except (ValueError, TypeError):
            continue
        block = data.get("esearchresult", {}) if isinstance(data, dict) else {}
        ids = block.get("idlist", []) if isinstance(block, dict) else []
        parent = plan_entry["query_id"]
        if plan_entry["kind"] == "esearch_gds_accn":
            uid = geo_series_uid(plan_entry["target"]["gse"])
            if uid not in ids:
                continue
            target = {"gse": plan_entry["target"]["gse"], "uid": uid}
            out.append({"kind": "esummary_gds_uid", "lane": LANE_REPOSITORY, "url": _esummary("gds", [uid]),
                        "target": target, "priority_rows": plan_entry["priority_rows"],
                        "query_id": parent + "-F1", "parent_query_id": parent})
            out.append({"kind": "elink_gds_pubmed_uid", "lane": LANE_REPOSITORY,
                        "url": _elink("gds", "pubmed", [uid]), "target": target,
                        "priority_rows": plan_entry["priority_rows"],
                        "query_id": parent + "-F2", "parent_query_id": parent})
        if plan_entry["kind"] == "esearch_pubmed_doi":
            count = int(block.get("count", "0") or 0)
            if count == 1 and len(ids) == 1:
                out.append({"kind": "esummary_pubmed_uid", "lane": LANE_PUBLICATION,
                            "url": _esummary("pubmed", [ids[0]]),
                            "target": {"pmid": ids[0], "doi": plan_entry["target"]["doi"]},
                            "priority_rows": plan_entry["priority_rows"],
                            "query_id": parent + "-F1", "parent_query_id": parent})
    return out


def phase2_pending(result, executed, already_sent=0):
    """Pending requests in order, truncated so executed + already_sent + pending <= PHASE2_REQUEST_CAP.

    Static and follow-up requests share one budget. Requests beyond the cap are not planned.
    """
    static = phase2_plan(result)
    done = {response["query_id"] for response in executed}
    pending = [request for request in static if request["query_id"] not in done]
    pending.extend(request for request in phase2_followups(result, executed)
                   if request["query_id"] not in done)
    budget = PHASE2_REQUEST_CAP - len(executed) - already_sent
    return pending[:max(0, budget)]


def gds_sample_free_view(raw_text, uid):
    """Allow-listed, sample-free view of a GEO DataSets esummary (no GSM accessions, no sample titles).

    The raw esummary carries a sample listing and is held privately. This view keeps only series
    metadata, and the caller records the raw file's sha256 next to it.
    """
    data = json.loads(raw_text)
    record = data.get("result", {}).get(uid)
    if not isinstance(record, dict):
        _fail("MALFORMED_ROW", f"esummary has no record for UID {uid}")
    allowed = ("accession", "title", "gdstype", "n_samples", "pubmedids", "extrelations", "taxon", "gpl", "entrytype",
               "pdat", "summary")
    view = {"uid": uid, "view": "sample-free allow-listed GDS metadata; samples omitted"}
    for key in allowed:
        if key in record:
            view[key] = record[key]
    text = json.dumps(view, sort_keys=True, ensure_ascii=False)
    if _GSM.search(text):
        _fail("MALFORMED_ROW", "sample accession leaked into a sample-free view")
    return view


def phase2_evaluate(result, responses, pipeline_utc=None):
    """Evaluate saved Phase 2 responses against the Phase 1 reconciliation (two passes).

    Pass 1 collects claims from each response. A response is accepted only if its body contains the claimed
    identifier. Pass 2 attributes each claim to a cluster. A PubMed record attaches to the cluster that owns
    its PMID or DOI as a direct identifier. A GEO DataSet attaches to a cluster that lists its accession directly,
    or to the unique cluster whose verified PubMed identifiers the DataSet links to. A family-label accession never
    attaches by itself. Nothing is admitted here.
    """
    if len(responses) > PHASE2_REQUEST_CAP:
        _fail("PHASE2_CAP_EXCEEDED", f"{len(responses)} responses exceed the Phase 2 cap of {PHASE2_REQUEST_CAP}")
    pipeline = pipeline_utc or result["pipeline_utc"]
    static = {request["query_id"]: request for request in phase2_plan(result)}
    known = dict(static)
    search_runs, executed = [], []
    claims = {"geo": [], "gse_link": [], "pmid_record": [], "pmc_link": []}
    refusals = []
    for response in responses:
        plan_entry = known.get(response["query_id"])
        if plan_entry is None:
            _fail("PHASE2_CAP_EXCEEDED", f"response {response['query_id']} is not in the plan")
        if plan_entry["url"] != response["url"]:
            _fail("MALFORMED_ROW", f"URL for {response['query_id']} does not match the plan")
        executed.append(response)
        for followup in phase2_followups(result, executed):
            known.setdefault(followup["query_id"], followup)
        search_runs.append(_search_run(plan_entry, response))
        _collect(plan_entry, response, claims, refusals)
    validated_runs = sl.validate_search_log(search_runs)
    verified, unassigned = _attribute(result, claims, refusals)
    verified_aliases = _dedupe_verified(verified)
    packets = _phase2_packets(result, verified_aliases, pipeline)
    valid_ids = {run["query_id"] for run in validated_runs} | {row["intake_id"] for row in result["dispositioned_rows"]}
    for packet in packets:
        sl.validate_candidate_packet(packet, valid_ids)
    return {
        "pipeline_utc": pipeline,
        "requests_executed": len(responses),
        "request_cap": PHASE2_REQUEST_CAP,
        "search_runs": validated_runs,
        "verified_aliases": verified_aliases,
        "verified_alias_count": len(verified_aliases),
        "unassigned_geo_accessions": unassigned,
        "refusals": refusals,
        "unverified": _unverified_list(result, verified_aliases, refusals),
        "packets": packets,
    }


def _search_run(plan_entry, response):
    """One DAV-T01 search-log row per Phase 2 request. Pagination follows the accepted validator."""
    body = json.loads(response["body"]) if response.get("http_status") == 200 else {}
    ids, count = _ids_and_count(plan_entry["kind"], body)
    is_search = plan_entry["kind"].startswith("esearch")
    if is_search:
        retmax = 20
        result_ids = ids[:retmax]
        page_count = count
        exact = _unquote(plan_entry["url"], "term")
        db = "gds" if "db=gds" in plan_entry["url"] else "pubmed"
        covered = min(retmax, page_count)
        completion = "COMPLETE" if page_count <= retmax else "INCOMPLETE"
        end = covered
    else:
        result_ids = ids
        page_count = len(result_ids)
        retmax = max(1, len(result_ids))
        exact = plan_entry["kind"] + " " + plan_entry["url"].split("?", 1)[1].split("&tool=")[0]
        db = "gds" if ("db=gds" in plan_entry["url"] or "dbfrom=gds" in plan_entry["url"]) else "pubmed"
        completion = "COMPLETE"
        end = page_count
    page = {
        "query": exact,
        "url": plan_entry["url"],
        "count": page_count,
        "retstart": 0,
        "retmax": retmax,
        "result_ids": result_ids,
    }
    row = {
        "query_id": plan_entry["query_id"],
        "lane": plan_entry["lane"],
        "source": "NCBI E-utilities " + plan_entry["kind"] + " (" + db + ")",
        "exact_query": exact,
        "searched_utc": response["utc"],
        "filters": "no date or field filter beyond the query text; metadata only",
        "pagination_start": 0,
        "pagination_end": end,
        "result_ids": result_ids,
        "screened_count": len(result_ids),
        "included_count": 0,
        "excluded_count": 0,
        "disposition_summary": "metadata verification only; no candidate disposition in this row",
        "follow_up_action": "see PHASE2_EVALUATION.json for the verification outcome",
        "completion_status": completion,
        "agent_id": AGENT_ID,
        "reviewer": UNASSIGNED_REVIEWER,
        "supersedes_query_id": "",
        "pages": [page],
    }
    return row


def _unquote(url, name):
    from urllib.parse import unquote_plus
    for piece in url.split("?", 1)[1].split("&"):
        key, _, value = piece.partition("=")
        if key == name:
            return unquote_plus(value)
    _fail("MALFORMED_ROW", f"URL has no {name} parameter")


def _ids_and_count(kind, body):
    if kind.startswith("esearch"):
        block = body.get("esearchresult", {})
        return list(block.get("idlist", [])), int(block.get("count", "0") or 0)
    if kind in ("elink_pmc_pubmed", "elink_gds_pubmed_uid"):
        links = sorted(set(_links(body)), key=lambda x: (len(x), x))
        return links, len(links)
    if kind in ("esummary_pubmed_batch", "esummary_pubmed_uid"):
        uids = list(body.get("result", {}).get("uids", []))
        return uids, len(uids)
    if kind == "esummary_gds_uid":
        return ([body["uid"]], 1) if body.get("uid") else ([], 0)
    return [], 0


def _collect(plan_entry, response, claims, refusals):
    """Pass 1: turn one saved response into claims. Each claim keeps its locator and its body for containment."""
    kind = plan_entry["kind"]
    base = {"query_id": plan_entry["query_id"], "url": response["url"], "file": response.get("file"),
            "body": response["body"]}
    if response.get("http_status") != 200:
        refusals.append({"query_id": plan_entry["query_id"], "kind": kind,
                         "reason": f"HTTP {response.get('http_status')}"})
        return
    try:
        body = json.loads(response["body"])
    except ValueError:
        refusals.append({"query_id": plan_entry["query_id"], "kind": kind, "reason": "response is not JSON"})
        return
    if kind == "esummary_gds_uid":
        gse = plan_entry["target"]["gse"]
        if str(body.get("accession", "")).upper() != gse.upper():
            refusals.append({"query_id": plan_entry["query_id"], "kind": kind,
                             "reason": "sample-free view accession does not match the target"})
            return
        claims["geo"].append(dict(base, gse=gse, uid=plan_entry["target"]["uid"],
                                  pmids=[str(x) for x in body.get("pubmedids", []) or []]))
    elif kind == "elink_gds_pubmed_uid":
        claims["gse_link"].append(dict(base, gse=plan_entry["target"]["gse"], pmids=_links(body)))
    elif kind in ("esummary_pubmed_batch", "esummary_pubmed_uid"):
        records = body.get("result", {})
        for pmid in records.get("uids", []):
            record = records.get(pmid, {})
            dois = [item.get("value", "") for item in record.get("articleids", []) if item.get("idtype") == "doi"]
            claims["pmid_record"].append(dict(base, pmid=str(pmid), dois=dois))
    elif kind == "elink_pmc_pubmed":
        claims["pmc_link"].append(dict(base, pmc=plan_entry["target"]["pmc"], pmids=_links(body)))


def _attribute(result, claims, refusals):
    """Pass 2: attribute claims to clusters. Returns (verified alias rows, unassigned GEO accessions)."""
    index = {}
    for cluster in result["clusters"]:
        for ident in cluster["identifiers"]:
            index.setdefault((ident["kind"], ident["fold"]), set()).add(cluster["study_id"])
    cluster_pmids = {c["study_id"]: set() for c in result["clusters"]}
    for (kind, fold), owners in index.items():
        if kind == "PMID":
            for study in owners:
                cluster_pmids[study].add(fold[4:])
    verified = []

    def emit(study, alias_type, value, evidence, claim, claim_source, body_text, token):
        if token.upper() not in body_text.upper():
            refusals.append({"query_id": claim_source["query_id"], "kind": "containment",
                             "reason": f"response does not contain {token}"})
            return
        verified.append({
            "study_id": study, "alias_type": alias_type, "alias_value": value,
            "identifier": {"PUBLICATION_PMID": "PMID" + value, "PUBLICATION_DOI": "DOI" + value.lower(),
                           "GEO_SERIES": "GSE" + value[3:]}[alias_type],
            "evidence_type": evidence,
            "locator": {"kind": "URL", "value": claim_source["url"], "page_or_section": claim},
            "query_id": claim_source["query_id"], "locator_file": claim_source["file"], "claim": claim,
        })

    # PMC-to-PubMed links are not used here. Every saved elink_pmc_pubmed response lists 30 to 77 PubMed IDs,
    # so membership of one PMID does not identify the article. Publication identity rests on the PubMed record
    # evidence (esummary) and on DOI matches. The PMC responses stay in the search log.
    for claim in claims["pmid_record"]:
        pmid = claim["pmid"]
        owners_pmid = index.get(("PMID", "PMID" + pmid), set())
        dois = {"DOI" + d.lower() for d in claim["dois"]}
        owners_doi = set().union(*[index.get(("DOI", d), set()) for d in dois]) if dois else set()
        if owners_pmid and owners_doi and not (owners_pmid & owners_doi):
            refusals.append({"query_id": claim["query_id"], "kind": "pmid_record",
                             "reason": f"PubMed DOI for PMID {pmid} differs from the queue DOI"})
            continue
        owners = owners_pmid | owners_doi
        if len(owners) != 1:
            continue
        study = next(iter(owners))
        cluster_pmids[study].add(pmid)
        if owners_pmid == {study}:
            emit(study, "PUBLICATION_PMID", pmid, "BIBLIOGRAPHIC_RECORD",
                 "PubMed esummary record exists for this PMID", claim, claim["body"], pmid)
        for doi in claim["dois"]:
            if study in index.get(("DOI", "DOI" + doi.lower()), set()):
                emit(study, "PUBLICATION_DOI", doi, "BIBLIOGRAPHIC_RECORD",
                     "PubMed article IDs list the DOI", claim, claim["body"], doi)
    unassigned = []
    for claim in claims["geo"]:
        gse_fold = "GSE" + claim["gse"][3:]
        direct = index.get(("GSE", gse_fold), set())
        basis = "accession listed by the queue row"
        if len(direct) == 1:
            study = next(iter(direct))
        else:
            linked = set(claim["pmids"])
            for link in claims["gse_link"]:
                if link["gse"].upper() == claim["gse"].upper():
                    linked |= set(link["pmids"])
            candidates = sorted(s for s, pmids in cluster_pmids.items() if pmids & linked)
            if len(candidates) != 1:
                unassigned.append({"gse": claim["gse"], "uid": claim["uid"], "query_id": claim["query_id"],
                                   "reason": ("no cluster reached by a verified PubMed link" if not candidates
                                              else "linked PubMed records reach more than one cluster")})
                continue
            study = candidates[0]
            basis = "GEO DataSet links to a PubMed record of this cluster (verified link)"
        emit(study, "GEO_SERIES", claim["gse"].upper(), "REPOSITORY_LINK",
             f"GEO DataSet UID {claim['uid']} has accession {claim['gse'].upper()} (esummary, sample-free view); {basis}",
             claim, claim["body"], claim["gse"])
    return verified, unassigned


def _links(body):
    links = []
    for linkset in body.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            links.extend(str(x) for x in linksetdb.get("links", []))
    return links


def _cluster_for_fold(result, kind, fold):
    for cluster in result["clusters"]:
        for ident in cluster["identifiers"]:
            if ident["kind"] == kind and ident["fold"] == fold:
                return cluster
    return None


def _dedupe_verified(verified):
    seen, out = set(), []
    for item in sorted(verified, key=lambda x: (x["study_id"], x["alias_type"], x["identifier"], x["query_id"])):
        key = (item["study_id"], item["alias_type"], item["identifier"], item["locator"]["value"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _unverified_list(result, verified_aliases, refusals):
    verified_keys = {(item["study_id"], item["identifier"]) for item in verified_aliases}
    priority = set(_priority_identifiers(result))
    out = []
    for cluster in result["clusters"]:
        for ident in cluster["identifiers"]:
            if (cluster["study_id"], ident["fold"]) in verified_keys:
                continue
            if ident["kind"] in CONTROLLED_KINDS:
                reason = "controlled-access identifier: not queried (no controlled content accessed)"
            elif ident["kind"] in ("NCT", "EMTAB", "PXD", "SRP", "SRR", "PRJNA", "PRJEB"):
                reason = "no Phase 2 endpoint in scope for this kind (E-utilities metadata only for this packet)"
            elif (ident["kind"], ident["fold"]) not in priority:
                reason = "outside the Phase 2 priority subset; remains PROBABLE pending DAV-T03"
            else:
                reason = "queried; no saved response confirmed this identifier for this cluster"
            out.append({"study_id": cluster["study_id"], "identifier": ident["fold"], "kind": ident["kind"],
                        "reason": reason})
    return sorted(out, key=lambda x: (x["study_id"], x["identifier"]))


def _phase2_packets(result, verified, pipeline):
    by_study = {}
    for item in verified:
        by_study.setdefault(item["study_id"], []).append(item)
    packets = []
    for study_id in sorted(by_study):
        items = sorted(by_study[study_id], key=lambda x: (x["identifier"], x["query_id"], x["locator"]["value"]))
        facts_list = [{"claim": item["claim"] + " (" + item["identifier"] + ")", "source_locator": item["locator"]}
                      for item in items]
        queries = sorted({item["query_id"] for item in items})
        content = {
            "lane": LANE_REPOSITORY,
            "query_ids": queries,
            "candidate_label": f"Phase 2 metadata verification for {study_id}",
            "verified_facts": facts_list,
            "inferences": [],
            "unknowns": [{"field": "clinical_fields_and_regimen", "resolution_path": "DAV-T03 and DAV-T05/T06",
                          "blocking_branches": ["paper_A_clinical_denominator"]}],
            "proposed_records": {"study_id": study_id},
            "suspected_overlap": [],
            "recommended_next_action": "DAV-T03 object verification for this lead",
            "agent_id": AGENT_ID,
            "completed_utc": pipeline,
        }
        packet = {"packet_id": sl.candidate_packet_id(content), **content}
        packets.append(packet)
    return packets
