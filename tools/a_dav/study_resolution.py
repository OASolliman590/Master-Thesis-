"""DAV-T02 study and publication-family resolution (A-DAV-03).

Pure functions only. This module performs no file I/O, no network access and
reads no clock. Callers pass candidate packets, one explicit integrator decision
(or None), the validation query-ID set, and the frozen JSON schemas. Every output
is a PROPOSED record. Nothing here admits a source, and no record can carry
study_status RESOLVED.

Failure codes
- Scientific, frozen by the ticket and SOURCE_IDENTITY_AND_DEDUPLICATION.md:
  UNRESOLVED_ORIGINATING_STUDY, ACCESSION_ALIAS_CONFLICT, PUBLICATION_SUBSET_UNKNOWN.
- Structural, declared here and listed in the receipt: see STRUCTURAL_FAILURE_CODES.

Null tokens: NULL means not applicable or not recorded (JSON null in records).
UNKNOWN means it applies but is unresolved. An empty TSV cell is an error.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from tools.a_dav.search_log import (
    SearchLogError,
    _LEXICAL_ID,
    _scan_recursive,
    _scan_text,
    _utc,
    _validate_fact_locator,
    validate_candidate_packet,
)


DECISION_SCHEMA_VERSION = "1.0.0"
RECEIPT_SCHEMA = "A-DAV-03.study_resolution_receipt.1"
TICKET = "DAV-T02"
RECEIPT_STATUS = "PROPOSED_NOT_RESOLVED"
ADMITTED_COUNT = 0
ANALYSIS_READINESS = "NOT_ANALYSIS_READY"
NULL_TOKEN = "NULL"
UNKNOWN_TOKEN = "UNKNOWN"
NULL_TOKEN_MEANING = "not applicable or not recorded (JSON null in records)"
UNKNOWN_TOKEN_MEANING = "applies but is unresolved"

CERTAINTY_LEVELS = ("VERIFIED", "PROBABLE", "POSSIBLE", "UNRESOLVED", "DISPROVED")
ALIAS_TYPES = (
    "GEO_SERIES", "GEO_SUPERSERIES", "GEO_SUBSERIES", "SRA_STUDY", "BIOPROJECT", "ENA_STUDY",
    "DBGAP_STUDY", "EGA_STUDY", "CATALOGUE_LABEL", "TRIAL_ID", "PUBLICATION_DOI", "PUBLICATION_PMID",
    "AUTHOR_LABEL",
)
# GEO_SUPERSERIES and GEO_SUBSERIES are accepted only through the superseries block.
ALIAS_TYPES_SUPERSERIES_ONLY = ("GEO_SUPERSERIES", "GEO_SUBSERIES")
EVIDENCE_TYPES = (
    "REPOSITORY_LINK", "PUBLICATION_STATEMENT", "BIBLIOGRAPHIC_RECORD", "TRIAL_RECORD", "CATALOGUE_ASSERTION",
)
ALIAS_STATUSES = ("MERGED_VERIFIED", "FLAGGED_NOT_MERGED", "FLAGGED_UNRESOLVED", "DISTINCT_DISPROVED")
STUDY_CLASSES = (
    "CLINICAL_ICI", "NON_ICI_COMPARATOR", "VACCINE", "ADOPTIVE_CELL", "DENDRITIC_CELL",
    "MECHANISTIC_CELL_MODEL", "UNTREATED_MOLECULAR", "OTHER",
)
STUDY_STATUSES = ("CANDIDATE", "RESOLVING", "RESOLVED", "EXCLUDED", "SUPERSEDED")
STUDY_STATUSES_EMITTABLE = ("CANDIDATE", "RESOLVING")
STUDY_STATUSES_DECISION_ONLY = ("EXCLUDED", "SUPERSEDED")
PUBLICATION_ROLES = (
    "PRIMARY_CLINICAL", "MOLECULAR", "FOLLOWUP", "SURVIVAL", "CORRECTION", "REANALYSIS", "ATLAS_REUSE", "OTHER",
)
INDEPENDENCE_EMITTABLE = ("NOT_INDEPENDENT", "UNRESOLVED", "NOT_APPLICABLE")
INDEPENDENCE_REFUSED = ("INDEPENDENT_RECRUITMENT",)
FORCED_NOT_INDEPENDENT_ROLES = ("REANALYSIS", "ATLAS_REUSE")
MODALITIES = ("RNA", "DNA_METHYLATION", "OTHER", "UNKNOWN")
LOCATOR_KINDS = ("URL", "DOI", "PMID", "FILE")
OVERLAP_FLAG_KINDS = ("SUSPECTED_PATIENT_OVERLAP",)
SUBSET_FIELDS = ("patient_subset", "assay_subset", "treatment_subset", "outcome_subset")

SCIENTIFIC_FAILURE_CODES = ("UNRESOLVED_ORIGINATING_STUDY", "ACCESSION_ALIAS_CONFLICT", "PUBLICATION_SUBSET_UNKNOWN")
STRUCTURAL_FAILURE_CODES = (
    "CANDIDATE_PACKET_REJECTED", "DUPLICATE_PACKET_ID", "DECISION_PACKET_UNKNOWN", "MALFORMED_DECISION",
    "MISSING_REVIEWER", "INVALID_UTC_TIMESTAMP", "INVALID_ENUM", "STATUS_CEILING",
    "INDEPENDENCE_UPGRADE_NOT_PERMITTED", "DUPLICATE_STUDY_ID", "DUPLICATE_PUBLICATION_ID", "DUPLICATE_ALIAS",
    "FAMILY_MISMATCH", "MALFORMED_ALIAS", "MALFORMED_LOCATOR", "FACT_LOCATOR_REQUIRED", "SCHEMA_INVALID",
    "EMPTY_CELL", "MALFORMED_TSV", "SECRET_LOCATOR", "MALFORMED_PACKET",
    "REPOSITORY_NOT_VERIFIED", "UNKNOWN_REPOSITORY_PREFIX", "DUPLICATE_LOCATOR",
)
# H-1 / OSR-H01: each repository prefix may be backed only by these alias types, and only by a MERGED_VERIFIED row.
REPOSITORY_PREFIX_ALIAS_TYPES = {
    "GEO": ("GEO_SERIES", "GEO_SUPERSERIES", "GEO_SUBSERIES"),
    "SRA": ("SRA_STUDY",),
    "BIOPROJECT": ("BIOPROJECT",),
    "ENA": ("ENA_STUDY",),
    "DBGAP": ("DBGAP_STUDY",),
    "EGA": ("EGA_STUDY",),
}
# Identity-bearing alias types that claim ownership of their value (round 3, H-1).
IDENTITY_ALIAS_TYPES = (
    "GEO_SERIES", "GEO_SUPERSERIES", "GEO_SUBSERIES", "SRA_STUDY", "BIOPROJECT", "ENA_STUDY", "DBGAP_STUDY",
    "EGA_STUDY", "TRIAL_ID", "PUBLICATION_PMID", "PUBLICATION_DOI",
)
# M-2 (round 3): compared after casefolding and removing ALL non-alphanumeric characters.
PLACEHOLDER_REVIEWERS = (
    "", "pending", "tbd", "todo", "n/a", "na", "none", "null", "unknown", "provisional", "placeholder",
    "reviewer", "xxx",
)

STUDY_HEADER = (
    "study_id", "trial_id", "publication_family_id", "study_title", "study_class", "cancer_type",
    "cancer_subtype", "disease_state", "study_design", "country_centre", "treatment_regimen_id",
    "checkpoint_target", "drug", "drug_class", "monotherapy_or_combination", "treatment_sequence",
    "line_of_therapy", "prior_ici_policy", "biopsy_schedule", "response_assessment_system",
    "primary_publication", "secondary_publications", "source_repositories", "access_status",
    "candidate_paper_branches", "study_status", "source_locators", "notes",
)
PUBLICATION_HEADER = (
    "publication_family_id", "study_id", "publication_id", "doi", "pmid", "publication_role", "data_reused",
    "patient_subset", "assay_subset", "treatment_subset", "outcome_subset", "known_overlap",
    "source_object_ids", "independence_status", "source_locators", "notes",
)
ALIAS_HEADER = (
    "alias_id", "alias_type", "alias_value", "canonical_study_id", "source_locator", "evidence_type",
    "certainty", "reviewer", "review_date", "status", "notes",
)
STUDY_SORT_KEY = ("study_id",)
PUBLICATION_SORT_KEY = ("study_id", "publication_id")
ALIAS_SORT_KEY = ("canonical_study_id", "alias_type", "alias_value", "alias_id")

_NULLABLE_STUDY_TEXT = (
    "trial_id", "cancer_subtype", "disease_state", "country_centre", "treatment_regimen_id",
    "checkpoint_target", "drug", "drug_class", "monotherapy_or_combination", "treatment_sequence",
    "line_of_therapy", "prior_ici_policy", "biopsy_schedule", "response_assessment_system",
)
_TOP_REQUIRED = (
    "decision_id", "reviewer", "decided_utc", "provisional", "packet_ids",
    "studies", "aliases", "publications", "superseries", "overlap_flags",
)
_STUDY_REQUIRED = (
    "study_id", "publication_family_id", "study_title", "study_class", "cancer_type", "study_design",
    "candidate_paper_branches", "access_status", "source_repositories", "source_locators",
)
_STUDY_OPTIONAL = _NULLABLE_STUDY_TEXT + ("study_status", "status_reason", "notes")
_PUB_REQUIRED = ("publication_id", "study_id", "publication_family_id", "publication_role", "source_locators")
_PUB_OPTIONAL = (
    "doi", "pmid", "data_reused", "patient_subset", "assay_subset", "treatment_subset", "outcome_subset",
    "known_overlap", "source_object_ids", "independence_claim", "notes",
)
_ALIAS_REQUIRED = ("alias_type", "alias_value", "canonical_study_id", "source_locator", "evidence_type", "certainty")
_ALIAS_OPTIONAL = ("notes",)
_SUPER_REQUIRED = (
    "superseries_accession", "originating_study_id", "certainty", "evidence_type", "source_locator", "subseries",
)
_SUPER_OPTIONAL = ()
_SUB_REQUIRED = ("accession", "modality", "sra_study", "certainty", "evidence_type", "source_locator",
                 "modality_locator", "sra_locator")
_FLAG_REQUIRED = ("flag_id", "flag_kind", "study_ids", "certainty", "description", "source_locator")
_LOCATOR_REQUIRED = ("kind", "value")
_LOCATOR_OPTIONAL = ("page_or_section", "accessed_utc")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_RANK = {"UNRESOLVED": 1, "POSSIBLE": 2, "PROBABLE": 3, "VERIFIED": 4}


class ResolutionError(ValueError):
    """Fail-closed resolution error with a stable code and an optional cause code."""

    def __init__(self, code, message, cause_code=None):
        super().__init__(message)
        self.code = code
        self.cause_code = cause_code


def _fail(code, message):
    raise ResolutionError(code, message)


def _guard(function, *args):
    """Run an accepted A-DAV-02 helper and re-raise its failures under the same code."""
    try:
        return function(*args)
    except SearchLogError as error:
        raise ResolutionError(error.code, str(error)) from error


def _check_keys(obj, required, optional, where):
    if not isinstance(obj, dict):
        _fail("MALFORMED_DECISION", f"{where} must be an object")
    missing = [key for key in required if key not in obj]
    if missing:
        _fail("MALFORMED_DECISION", f"{where} is missing: {', '.join(missing)}")
    unknown = sorted(key for key in obj if key not in required and key not in optional)
    if unknown:
        _fail("MALFORMED_DECISION", f"{where} has unknown keys: {', '.join(unknown)}")


def _list(value, where):
    if not isinstance(value, list):
        _fail("MALFORMED_DECISION", f"{where} must be a list")
    return value


def _enum(value, allowed, where, code="INVALID_ENUM"):
    if not isinstance(value, str) or value not in allowed:
        _fail(code, f"{where} must be one of the declared closed values")
    return value


def _text(value, where, nullable=False, code="MALFORMED_DECISION"):
    if value is None:
        if nullable:
            return None
        _fail(code, f"{where} must not be null")
    if not isinstance(value, str):
        _fail(code, f"{where} must be text")
    if value == NULL_TOKEN:
        if nullable:
            return None
        _fail(code, f"{where} may not use the NULL token; use UNKNOWN for unresolved values")
    if value == UNKNOWN_TOKEN:
        return value
    if not value.strip():
        _fail(code, f"{where} must not be empty")
    if _CONTROL.search(value):
        _fail(code, f"{where} contains control characters")
    _guard(_scan_text, value)
    return value


def _lexical(value, where):
    if not isinstance(value, str) or not _LEXICAL_ID.fullmatch(value) or value in (NULL_TOKEN, UNKNOWN_TOKEN):
        _fail("MALFORMED_DECISION", f"{where} must be a lexical identifier and not a null token")
    return value


def _study_ref(value, where):
    if value == UNKNOWN_TOKEN:
        return UNKNOWN_TOKEN
    return _lexical(value, where)


def _text_list(values, where, lexical=False):
    values = _list(values, where)
    items = []
    for index, item in enumerate(values):
        if lexical:
            item = _lexical(item, f"{where}[{index}]")
        else:
            item = _text(item, f"{where}[{index}]")
            if ";" in item:
                _fail("MALFORMED_DECISION", f"{where}[{index}] may not contain the list separator ';'")
        items.append(item)
    if len(set(items)) != len(items):
        _fail("MALFORMED_DECISION", f"{where} contains duplicate items")
    return sorted(items)


def _locator(obj, where):
    _check_keys(obj, _LOCATOR_REQUIRED, _LOCATOR_OPTIONAL, where)
    kind = _enum(obj["kind"], LOCATOR_KINDS, f"{where}.kind", code="MALFORMED_LOCATOR")
    value = obj["value"]
    if not isinstance(value, str) or not value.strip():
        _fail("MALFORMED_LOCATOR", f"{where}.value must be non-empty text")
    _guard(_scan_text, value)
    _guard(_validate_fact_locator, kind, value)
    page = _text(obj.get("page_or_section"), f"{where}.page_or_section", nullable=True)
    accessed = obj.get("accessed_utc")
    if accessed is not None and not _utc(accessed):
        _fail("INVALID_UTC_TIMESTAMP", f"{where}.accessed_utc must be UTC ending in Z")
    return {"kind": kind, "value": value, "page_or_section": page, "accessed_utc": accessed}


def _locator_key(locator):
    page, accessed = locator["page_or_section"], locator["accessed_utc"]
    return (locator["kind"], locator["value"], (page is not None, page or ""), (accessed is not None, accessed or ""))


def _locators(values, where):
    values = _list(values, where)
    if not values:
        _fail("FACT_LOCATOR_REQUIRED", f"{where} requires at least one source locator")
    locators = [_locator(item, f"{where}[{index}]") for index, item in enumerate(values)]
    if len({_locator_key(item) for item in locators}) != len(locators):
        _fail("DUPLICATE_LOCATOR", f"{where} repeats an identical source locator")
    return sorted(locators, key=_locator_key)


def _repository_list(values, where):
    """source_repositories entries are PREFIX:IDENTIFIER with a closed prefix set (fail closed)."""
    items = _text_list(values, where)
    for item in items:
        prefix, separator, identifier = item.partition(":")
        if (not separator or prefix not in REPOSITORY_PREFIX_ALIAS_TYPES
                or not _LEXICAL_ID.fullmatch(identifier) or identifier in (NULL_TOKEN, UNKNOWN_TOKEN)):
            _fail("UNKNOWN_REPOSITORY_PREFIX", f"{where} entry {item!r} is not PREFIX:IDENTIFIER with a declared prefix")
    return items


def _fold(value):
    """Candidate-matching key only. The raw alias is kept byte-for-byte."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _weaker(first, second):
    if "DISPROVED" in (first, second):
        return "DISPROVED"
    return first if _RANK[first] <= _RANK[second] else second


def _validate_packets(packets, valid_query_ids):
    seen = set()
    for packet in packets:
        try:
            validate_candidate_packet(packet, valid_query_ids)
        except SearchLogError as error:
            raise ResolutionError("CANDIDATE_PACKET_REJECTED", f"candidate packet rejected: {error.code}",
                                  cause_code=error.code) from error
        if packet["packet_id"] in seen:
            _fail("DUPLICATE_PACKET_ID", "candidate packet IDs must be unique")
        seen.add(packet["packet_id"])
    return sorted(seen)


def _validator(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        _fail("SCHEMA_INVALID", f"frozen schema rejected: {error.message}")
    return Draft202012Validator(schema)


def _schema_default(schema):
    try:
        return schema["properties"]["schema_version"]["default"]
    except (KeyError, TypeError):
        _fail("SCHEMA_INVALID", "frozen schema declares no schema_version default")


def _validate_record(validator, record, where):
    errors = sorted(validator.iter_errors(record), key=lambda error: str(list(error.path)))
    if errors:
        _fail("SCHEMA_INVALID", f"{where} violates its frozen schema: {errors[0].message}")


def _reviewer_key(reviewer):
    """Placeholder-comparison key only (round 4).

    Casefold, then NFKD-decompose, then drop every combining mark (category M*), then keep only
    characters with str.isalnum(). Decomposing BEFORE dropping marks is required: NFKC would compose
    E plus a combining acute into a letter that survives the filter, so PEN+U+0301+DING would be accepted.
    Non-Latin letters are kept, so real names in any script are not placeholders. Punctuation,
    whitespace, invisible format characters and marks are removed, so they cannot hide a placeholder.
    """
    decomposed = unicodedata.normalize("NFKD", reviewer.casefold())
    base = "".join(ch for ch in decomposed if not unicodedata.category(ch).startswith("M"))
    return "".join(ch for ch in base if ch.isalnum())


def _validate_envelope(decision, packet_ids):
    _guard(_scan_recursive, decision)
    _check_keys(decision, _TOP_REQUIRED, (), "decision")
    reviewer = decision["reviewer"]
    if not isinstance(reviewer, str) or _reviewer_key(reviewer) in PLACEHOLDER_REVIEWERS or not _reviewer_key(reviewer):
        _fail("MISSING_REVIEWER", "decision requires a named, non-placeholder reviewer")
    reviewer = _text(reviewer, "reviewer")
    if not _utc(decision["decided_utc"]):
        _fail("INVALID_UTC_TIMESTAMP", "decided_utc must be ISO-8601 UTC ending in Z")
    if not isinstance(decision["provisional"], bool):
        _fail("MALFORMED_DECISION", "provisional must be a boolean")
    referenced = _text_list(decision["packet_ids"], "packet_ids")
    if not referenced:
        _fail("MALFORMED_DECISION", "decision must reference at least one validated packet")
    for packet_id in referenced:
        if packet_id not in packet_ids:
            _fail("DECISION_PACKET_UNKNOWN", "decision references a packet that was not validated")
    return {
        "decision_id": _lexical(decision["decision_id"], "decision_id"),
        "reviewer": reviewer,
        "decided_utc": decision["decided_utc"],
        "review_date": decision["decided_utc"][:10],
        "provisional": decision["provisional"],
        "packet_ids": referenced,
    }


def _normalize_study(entry, where):
    _check_keys(entry, _STUDY_REQUIRED, _STUDY_OPTIONAL, where)
    requested = entry.get("study_status")
    if requested is not None:
        _enum(requested, STUDY_STATUSES, f"{where}.study_status")
        if requested == "RESOLVED":
            _fail("STATUS_CEILING", "RESOLVED is never emitted by this packet")
    reason = _text(entry.get("status_reason"), f"{where}.status_reason", nullable=True)
    if reason is not None and requested not in STUDY_STATUSES_DECISION_ONLY:
        _fail("MALFORMED_DECISION", "status_reason is accepted only with EXCLUDED or SUPERSEDED")
    if requested in STUDY_STATUSES_DECISION_ONLY and reason is None:
        _fail("STATUS_CEILING", f"{requested} requires a status_reason and a reviewer")
    value = {
        "study_id": _lexical(entry["study_id"], f"{where}.study_id"),
        "publication_family_id": _lexical(entry["publication_family_id"], f"{where}.publication_family_id"),
        "study_title": _text(entry["study_title"], f"{where}.study_title"),
        "study_class": _enum(entry["study_class"], STUDY_CLASSES, f"{where}.study_class"),
        "cancer_type": _text(entry["cancer_type"], f"{where}.cancer_type"),
        "study_design": _text(entry["study_design"], f"{where}.study_design"),
        "candidate_paper_branches": _text_list(entry["candidate_paper_branches"], f"{where}.candidate_paper_branches"),
        "access_status": _text(entry["access_status"], f"{where}.access_status"),
        "source_repositories": _repository_list(entry["source_repositories"], f"{where}.source_repositories"),
        "source_locators": _locators(entry["source_locators"], f"{where}.source_locators"),
        "requested_status": requested,
        "status_reason": reason,
        "notes": _text(entry.get("notes"), f"{where}.notes", nullable=True),
    }
    for field in _NULLABLE_STUDY_TEXT:
        value[field] = _text(entry.get(field), f"{where}.{field}", nullable=True)
    return value


def _normalize_publication(entry, where):
    _check_keys(entry, _PUB_REQUIRED, _PUB_OPTIONAL, where)
    claim = entry.get("independence_claim", "UNRESOLVED")
    if claim in INDEPENDENCE_REFUSED:
        _fail("INDEPENDENCE_UPGRADE_NOT_PERMITTED", "INDEPENDENT_RECRUITMENT needs a frozen evidence rule not yet defined")
    _enum(claim, INDEPENDENCE_EMITTABLE, f"{where}.independence_claim")
    doi = _text(entry.get("doi"), f"{where}.doi", nullable=True)
    if doi is not None and doi != UNKNOWN_TOKEN:
        _guard(_validate_fact_locator, "DOI", doi)
    pmid = _text(entry.get("pmid"), f"{where}.pmid", nullable=True)
    if pmid is not None and pmid != UNKNOWN_TOKEN:
        _guard(_validate_fact_locator, "PMID", pmid)
    value = {
        "publication_id": _lexical(entry["publication_id"], f"{where}.publication_id"),
        "study_id": _lexical(entry["study_id"], f"{where}.study_id"),
        "publication_family_id": _lexical(entry["publication_family_id"], f"{where}.publication_family_id"),
        "publication_role": _enum(entry["publication_role"], PUBLICATION_ROLES, f"{where}.publication_role"),
        "doi": doi,
        "pmid": pmid,
        "independence_claim": claim,
        "source_object_ids": _text_list(entry.get("source_object_ids", []), f"{where}.source_object_ids", lexical=True),
        "source_locators": _locators(entry["source_locators"], f"{where}.source_locators"),
        "notes": _text(entry.get("notes"), f"{where}.notes", nullable=True),
    }
    for field in ("data_reused",) + SUBSET_FIELDS + ("known_overlap",):
        value[field] = _text(entry.get(field), f"{where}.{field}", nullable=True)
    return value


def _normalize_superseries(entry, where):
    _check_keys(entry, _SUPER_REQUIRED, _SUPER_OPTIONAL, where)
    subseries = []
    for index, sub in enumerate(_list(entry["subseries"], f"{where}.subseries")):
        sub_where = f"{where}.subseries[{index}]"
        _check_keys(sub, _SUB_REQUIRED, (), sub_where)
        sra, sra_locator = sub["sra_study"], sub["sra_locator"]
        if sra is None:
            if sra_locator is not None:
                _fail("MALFORMED_DECISION", f"{sub_where}.sra_locator must be null when sra_study is null")
            sra_value = None
        elif sra == UNKNOWN_TOKEN:
            if sra_locator is None:
                _fail("MALFORMED_DECISION", f"{sub_where}.sra_locator is required to record an unresolved SRA")
            sra_value = UNKNOWN_TOKEN
        else:
            if sra_locator is None:
                _fail("MALFORMED_DECISION", f"{sub_where}.sra_locator is required for a named SRA study")
            sra_value = _lexical(sra, f"{sub_where}.sra_study")
        subseries.append({
            "accession": _lexical(sub["accession"], f"{sub_where}.accession"),
            "modality": _enum(sub["modality"], MODALITIES, f"{sub_where}.modality"),
            "sra_study": sra_value,
            "sra_locator": None if sra_locator is None else _locator(sra_locator, f"{sub_where}.sra_locator"),
            "modality_locator": _locator(sub["modality_locator"], f"{sub_where}.modality_locator"),
            "certainty": _enum(sub["certainty"], CERTAINTY_LEVELS, f"{sub_where}.certainty"),
            "evidence_type": _enum(sub["evidence_type"], EVIDENCE_TYPES, f"{sub_where}.evidence_type"),
            "source_locator": _locator(sub["source_locator"], f"{sub_where}.source_locator"),
        })
    accessions = [sub["accession"] for sub in subseries]
    if len(set(accessions)) != len(accessions):
        _fail("MALFORMED_DECISION", f"{where}.subseries repeats an accession")
    return {
        "superseries_accession": _lexical(entry["superseries_accession"], f"{where}.superseries_accession"),
        "originating_study_id": _study_ref(entry["originating_study_id"], f"{where}.originating_study_id"),
        "certainty": _enum(entry["certainty"], CERTAINTY_LEVELS, f"{where}.certainty"),
        "evidence_type": _enum(entry["evidence_type"], EVIDENCE_TYPES, f"{where}.evidence_type"),
        "source_locator": _locator(entry["source_locator"], f"{where}.source_locator"),
        "subseries": sorted(subseries, key=lambda sub: sub["accession"]),
    }


def _normalize_alias(entry, where):
    _check_keys(entry, _ALIAS_REQUIRED, _ALIAS_OPTIONAL, where)
    if entry["alias_type"] in ALIAS_TYPES_SUPERSERIES_ONLY:
        _fail("MALFORMED_DECISION", f"{where}: {entry['alias_type']} is accepted only through the superseries block")
    alias_type = _enum(entry["alias_type"], ALIAS_TYPES, f"{where}.alias_type")
    alias_value = _text(entry["alias_value"], f"{where}.alias_value", code="MALFORMED_ALIAS")
    if alias_value == UNKNOWN_TOKEN or not _fold(alias_value):
        _fail("MALFORMED_ALIAS", f"{where}.alias_value must contain an identifying character")
    return {
        "alias_type": alias_type,
        "alias_value": alias_value,
        "canonical_study_id": _study_ref(entry["canonical_study_id"], f"{where}.canonical_study_id"),
        "source_locator": _locator(entry["source_locator"], f"{where}.source_locator"),
        "evidence_type": _enum(entry["evidence_type"], EVIDENCE_TYPES, f"{where}.evidence_type"),
        "certainty": _enum(entry["certainty"], CERTAINTY_LEVELS, f"{where}.certainty"),
        "notes": _text(entry.get("notes"), f"{where}.notes", nullable=True),
    }


def _candidate(alias_type, value, target, evidence_type, certainty, locator, notes):
    return {
        "alias_type": alias_type,
        "alias_value": value,
        "canonical_study_id": target,
        "evidence_type": evidence_type,
        "certainty": certainty,
        "source_locator": locator,
        "notes": notes,
    }


def _alias_candidates(aliases, superseries_blocks, study_ids):
    """Every alias-like row, from the alias list and from superseries blocks, before checks."""
    candidates = []
    for block in superseries_blocks:
        target = block["originating_study_id"]
        candidates.append(_candidate(
            "GEO_SUPERSERIES", block["superseries_accession"], target, block["evidence_type"],
            block["certainty"], block["source_locator"], "scope=SUPERSERIES_ALIAS_ONLY;not_a_matrix=TRUE"))
        for sub in block["subseries"]:
            # A SubSeries can be no more certain than the SuperSeries that names its origin.
            effective = _weaker(sub["certainty"], block["certainty"])
            notes = (f"series_modality={sub['modality']};modality_source={sub['modality_locator']['value']};"
                     "scope=SERIES_LEVEL_ONLY;patient_specimen_timepoint_intersection=NOT_CLAIMED")
            candidates.append(_candidate("GEO_SUBSERIES", sub["accession"], target, sub["evidence_type"],
                                         effective, sub["source_locator"], notes))
            # An unresolved SRA (UNKNOWN) emits no alias row; the receipt counts it instead.
            if sub["sra_study"] not in (None, UNKNOWN_TOKEN):
                candidates.append(_candidate("SRA_STUDY", sub["sra_study"], target, sub["evidence_type"],
                                             effective, sub["sra_locator"], notes))
    for alias_entry in aliases:
        candidates.append(_candidate(
            alias_entry["alias_type"], alias_entry["alias_value"], alias_entry["canonical_study_id"],
            alias_entry["evidence_type"], alias_entry["certainty"], alias_entry["source_locator"],
            alias_entry["notes"]))
    for candidate in candidates:
        target, certainty = candidate["canonical_study_id"], candidate["certainty"]
        if target != UNKNOWN_TOKEN and target not in study_ids:
            _fail("UNRESOLVED_ORIGINATING_STUDY", "alias names a study that is not in the decision")
        if certainty == "VERIFIED" and target == UNKNOWN_TOKEN:
            _fail("UNRESOLVED_ORIGINATING_STUDY", "a VERIFIED alias must name its originating study")
        if certainty == "UNRESOLVED" and target != UNKNOWN_TOKEN:
            _fail("UNRESOLVED_ORIGINATING_STUDY", "an UNRESOLVED alias cannot name a study; use UNKNOWN")
        if certainty == "DISPROVED" and target == UNKNOWN_TOKEN:
            _fail("MALFORMED_DECISION", "a DISPROVED alias must name the study it is distinct from")
    _check_conflicts(candidates)
    return candidates


def _check_conflicts(candidates):
    targets_by_key = {}
    disproved = []
    for candidate in candidates:
        key = _fold(candidate["alias_value"])
        if candidate["certainty"] == "DISPROVED":
            disproved.append((key, candidate["canonical_study_id"]))
            continue
        if candidate["canonical_study_id"] == UNKNOWN_TOKEN:
            continue
        targets_by_key.setdefault(key, set()).add(candidate["canonical_study_id"])
    for key, targets in targets_by_key.items():
        if len(targets) > 1:
            _fail("ACCESSION_ALIAS_CONFLICT", "one normalized alias maps to two studies")
    for key, target in disproved:
        if target in targets_by_key.get(key, set()):
            _fail("ACCESSION_ALIAS_CONFLICT",
                  "a DISPROVED alias row names a study that a non-DISPROVED row of the same normalized alias asserts")


def _alias_status(certainty, target):
    if certainty == "DISPROVED":
        return "DISTINCT_DISPROVED"
    if certainty == "VERIFIED":
        return "MERGED_VERIFIED"
    if certainty == "UNRESOLVED" or target == UNKNOWN_TOKEN:
        return "FLAGGED_UNRESOLVED"
    return "FLAGGED_NOT_MERGED"


def _alias_rows(candidates, envelope):
    rows = []
    for candidate in candidates:
        body = {
            "alias_type": candidate["alias_type"],
            "alias_value": candidate["alias_value"],
            "canonical_study_id": candidate["canonical_study_id"],
            "certainty": candidate["certainty"],
            "evidence_type": candidate["evidence_type"],
            "source_locator": candidate["source_locator"],
            "notes": candidate["notes"],
        }
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        row = {
            "alias_id": "ALIAS-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
            "alias_type": candidate["alias_type"],
            "alias_value": candidate["alias_value"],
            "canonical_study_id": candidate["canonical_study_id"],
            "source_locator": candidate["source_locator"],
            "evidence_type": candidate["evidence_type"],
            "certainty": candidate["certainty"],
            "reviewer": envelope["reviewer"],
            "review_date": envelope["review_date"],
            "status": _alias_status(candidate["certainty"], candidate["canonical_study_id"]),
            "notes": candidate["notes"],
        }
        rows.append(row)
    seen = set()
    for row in rows:
        if row["alias_id"] in seen:
            _fail("DUPLICATE_ALIAS", "identical alias rows are duplicates")
        seen.add(row["alias_id"])
    return rows


def _check_identity_ownership(studies, pub_records, alias_rows):
    """H-1 (round 3): ONE identity-ownership map for canonical fields and typed alias rows.

    Keys use the same fold as the alias conflict key. Claims come from: repository accessions (prefix
    stripped), trial_id, publication_family_id, publication PMID and DOI, and every non-DISPROVED alias
    row of an identity-bearing type whose target is a study (UNKNOWN claims nothing). A key owned by
    two different studies raises ACCESSION_ALIAS_CONFLICT. A DISPROVED alias row claims nothing, which
    is what DISPROVED means. UNKNOWN is never an identity.
    """
    owners = {}

    def claim(value, study_id, source):
        if value in (None, UNKNOWN_TOKEN):
            return
        owners.setdefault(_fold(value), {}).setdefault(study_id, set()).add(source)

    for study in studies:
        sid = study["study_id"]
        claim(study["publication_family_id"], sid, "publication_family_id")
        claim(study["trial_id"], sid, "trial_id")
        for repository in study["source_repositories"]:
            claim(repository.partition(":")[2], sid, "repository_accession")
    for pub in pub_records:
        claim(pub["pmid"], pub["study_id"], "publication_pmid")
        claim(pub["doi"], pub["study_id"], "publication_doi")
    for row in alias_rows:
        if (row["alias_type"] in IDENTITY_ALIAS_TYPES and row["status"] != "DISTINCT_DISPROVED"
                and row["canonical_study_id"] != UNKNOWN_TOKEN):
            claim(row["alias_value"], row["canonical_study_id"], "alias:" + row["alias_type"])
    for by_study in owners.values():
        if len(by_study) > 1:
            _fail("ACCESSION_ALIAS_CONFLICT", "an identity value is owned by two canonical studies")


def _check_repository_verification(studies, alias_rows):
    """H-1 / OSR-H01 (a): every source repository must be backed by a MERGED_VERIFIED alias of the same study."""
    for study in studies:
        for repository in study["source_repositories"]:
            prefix, _, identifier = repository.partition(":")
            backed = any(
                row["canonical_study_id"] == study["study_id"] and row["status"] == "MERGED_VERIFIED"
                and row["alias_type"] in REPOSITORY_PREFIX_ALIAS_TYPES[prefix] and _fold(row["alias_value"]) == _fold(identifier)
                for row in alias_rows)
            if not backed:
                _fail("REPOSITORY_NOT_VERIFIED", f"repository {repository} has no MERGED_VERIFIED alias of its study")


def _overlap_flags(entries, study_ids):
    flags = []
    seen = set()
    for index, entry in enumerate(entries):
        where = f"overlap_flags[{index}]"
        _check_keys(entry, _FLAG_REQUIRED, (), where)
        flag_id = _lexical(entry["flag_id"], f"{where}.flag_id")
        if flag_id in seen:
            _fail("MALFORMED_DECISION", "overlap flag IDs must be unique")
        seen.add(flag_id)
        studies = _text_list(entry["study_ids"], f"{where}.study_ids", lexical=True)
        if len(studies) < 2:
            _fail("MALFORMED_DECISION", "an overlap flag names at least two studies")
        for study_id in studies:
            if study_id not in study_ids:
                _fail("UNRESOLVED_ORIGINATING_STUDY", "overlap flag names a study that is not in the decision")
        flags.append({
            "flag_id": flag_id,
            "flag_kind": _enum(entry["flag_kind"], OVERLAP_FLAG_KINDS, f"{where}.flag_kind"),
            "study_ids": studies,
            "certainty": _enum(entry["certainty"], CERTAINTY_LEVELS, f"{where}.certainty"),
            "description": _text(entry["description"], f"{where}.description"),
            "source_locator": _locator(entry["source_locator"], f"{where}.source_locator"),
            "dav_t08_handoff": True,
            "merge_performed": False,
        })
    return sorted(flags, key=lambda flag: flag["flag_id"])


def _publication_records(entries, study_map, validator, version):
    records = []
    seen = set()
    for index, entry in enumerate(entries):
        pub = _normalize_publication(entry, f"publications[{index}]")
        if pub["publication_id"] in seen:
            _fail("DUPLICATE_PUBLICATION_ID", "publication IDs must be unique")
        seen.add(pub["publication_id"])
        study = study_map.get(pub["study_id"])
        if study is None:
            _fail("UNRESOLVED_ORIGINATING_STUDY", "publication names a study that is not in the decision")
        if pub["publication_family_id"] != study["publication_family_id"]:
            _fail("FAMILY_MISMATCH", "publication family differs from its study's family")
        reuse_claimed = pub["publication_role"] in FORCED_NOT_INDEPENDENT_ROLES or pub["data_reused"] is not None
        if reuse_claimed:
            for field in SUBSET_FIELDS:
                if pub[field] is None or pub[field] == UNKNOWN_TOKEN:
                    _fail("PUBLICATION_SUBSET_UNKNOWN", f"a reuse claim needs an explicit {field}")
        if reuse_claimed:
            independence = "NOT_INDEPENDENT"
        else:
            independence = pub["independence_claim"]
        record = {
            "schema_version": version,
            "publication_family_id": pub["publication_family_id"],
            "study_id": pub["study_id"],
            "publication_id": pub["publication_id"],
            "doi": pub["doi"],
            "pmid": pub["pmid"],
            "publication_role": pub["publication_role"],
            "data_reused": pub["data_reused"],
            "patient_subset": pub["patient_subset"],
            "assay_subset": pub["assay_subset"],
            "treatment_subset": pub["treatment_subset"],
            "outcome_subset": pub["outcome_subset"],
            "known_overlap": pub["known_overlap"],
            "source_object_ids": pub["source_object_ids"],
            "independence_status": independence,
            "source_locators": pub["source_locators"],
            "notes": pub["notes"],
        }
        _validate_record(validator, record, f"publication {record['publication_id']}")
        records.append(record)
    return records


def _study_status(study, alias_rows, flags):
    sid = study["study_id"]
    requested = study["requested_status"]
    touched = (any(row["canonical_study_id"] == sid and row["status"].startswith("FLAGGED") for row in alias_rows)
               or any(sid in flag["study_ids"] for flag in flags))
    if requested is None:
        return "RESOLVING" if touched else "CANDIDATE"
    return requested


def _study_records(studies, alias_rows, flags, pub_records, validator, version):
    records = []
    for study in studies:
        sid = study["study_id"]
        pubs = [pub for pub in pub_records if pub["study_id"] == sid]
        primaries = [pub for pub in pubs if pub["publication_role"] == "PRIMARY_CLINICAL"]
        if len(primaries) > 1:
            _fail("MALFORMED_DECISION", f"study {sid} names more than one PRIMARY_CLINICAL publication")
        primary = primaries[0]["publication_id"] if primaries else None
        secondary = sorted(pub["publication_id"] for pub in pubs if pub["publication_id"] != primary)
        status = _study_status(study, alias_rows, flags)
        parts = [part for part in (study["notes"],
                                   f"status_reason: {study['status_reason']}" if study["status_reason"] else None)
                 if part]
        record = {
            "schema_version": version,
            "study_id": sid,
            "trial_id": study["trial_id"],
            "publication_family_id": study["publication_family_id"],
            "study_title": study["study_title"],
            "study_class": study["study_class"],
            "cancer_type": study["cancer_type"],
            "cancer_subtype": study["cancer_subtype"],
            "disease_state": study["disease_state"],
            "study_design": study["study_design"],
            "country_centre": study["country_centre"],
            "treatment_regimen_id": study["treatment_regimen_id"],
            "checkpoint_target": study["checkpoint_target"],
            "drug": study["drug"],
            "drug_class": study["drug_class"],
            "monotherapy_or_combination": study["monotherapy_or_combination"],
            "treatment_sequence": study["treatment_sequence"],
            "line_of_therapy": study["line_of_therapy"],
            "prior_ici_policy": study["prior_ici_policy"],
            "biopsy_schedule": study["biopsy_schedule"],
            "response_assessment_system": study["response_assessment_system"],
            "primary_publication": primary,
            "secondary_publications": secondary,
            "source_repositories": study["source_repositories"],
            "access_status": study["access_status"],
            "candidate_paper_branches": study["candidate_paper_branches"],
            "study_status": status,
            "source_locators": study["source_locators"],
            "notes": " | ".join(parts) if parts else None,
        }
        _validate_record(validator, record, f"study {sid}")
        records.append(record)
    return records


def _cell(value):
    if value is None:
        return NULL_TOKEN
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    elif isinstance(value, list):
        if not value:
            return NULL_TOKEN
        if all(isinstance(item, dict) for item in value):
            text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        elif all(isinstance(item, str) for item in value):
            if any(item == "" for item in value):
                _fail("EMPTY_CELL", "an empty list item would render as an empty cell")
            if any(";" in item for item in value):
                _fail("MALFORMED_TSV", "a list item contains the list separator")
            text = ";".join(value)
        else:
            _fail("MALFORMED_TSV", "mixed list items cannot be rendered")
    else:
        _fail("MALFORMED_TSV", "unsupported value type for a table cell")
    if text == "":
        _fail("EMPTY_CELL", "an empty cell is invalid; use the NULL or UNKNOWN token")
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


def _render(header, sort_key, rows):
    ordered = sorted(
        rows,
        key=lambda row: (tuple("" if row.get(key) is None else str(row.get(key)) for key in sort_key),
                         json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)),
    )
    lines = ["\t".join(header)]
    for row in ordered:
        lines.append("\t".join(_cell(row.get(column)) for column in header))
    return "\n".join(lines) + "\n"


def render_study_tsv(records):
    """Study registry TSV with the frozen template header, sorted by study_id."""
    return _render(STUDY_HEADER, STUDY_SORT_KEY, records)


def render_publication_tsv(records):
    """Publication-family registry TSV, sorted by (study_id, publication_id)."""
    return _render(PUBLICATION_HEADER, PUBLICATION_SORT_KEY, records)


def render_alias_tsv(rows):
    """Alias crosswalk TSV, sorted by (canonical_study_id, alias_type, alias_value, alias_id)."""
    return _render(ALIAS_HEADER, ALIAS_SORT_KEY, rows)


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _enum_declaration():
    return {
        "alias_type": list(ALIAS_TYPES),
        "evidence_type": list(EVIDENCE_TYPES),
        "certainty": list(CERTAINTY_LEVELS),
        "alias_status": list(ALIAS_STATUSES),
        "study_class": list(STUDY_CLASSES),
        "study_status_emittable": list(STUDY_STATUSES_EMITTABLE),
        "study_status_decision_only": list(STUDY_STATUSES_DECISION_ONLY),
        "publication_role": list(PUBLICATION_ROLES),
        "independence_status_emittable": list(INDEPENDENCE_EMITTABLE),
        "independence_status_refused": list(INDEPENDENCE_REFUSED),
        "modality": list(MODALITIES),
        "locator_kind": list(LOCATOR_KINDS),
        "overlap_flag_kind": list(OVERLAP_FLAG_KINDS),
    }


def _assemble(packet_count, envelope, studies, pubs, aliases, flags, study_version, pub_version, extra=None):
    tables = {
        "study_registry.tsv": render_study_tsv(studies),
        "publication_family_registry.tsv": render_publication_tsv(pubs),
        "study_alias_crosswalk.tsv": render_alias_tsv(aliases),
    }
    alias_counts = {status: 0 for status in ALIAS_STATUSES}
    for row in aliases:
        alias_counts[row["status"]] += 1
    study_counts = {status: 0 for status in STUDY_STATUSES_EMITTABLE + STUDY_STATUSES_DECISION_ONLY}
    for record in studies:
        study_counts[record["study_status"]] += 1
    receipt = {
        "receipt_schema": RECEIPT_SCHEMA,
        "ticket": TICKET,
        "status": RECEIPT_STATUS,
        "admitted_count": ADMITTED_COUNT,
        "analysis_readiness": ANALYSIS_READINESS,
        "decision_present": envelope is not None,
        "decision_id": envelope["decision_id"] if envelope else None,
        "reviewer": envelope["reviewer"] if envelope else None,
        "decided_utc": envelope["decided_utc"] if envelope else None,
        "provisional": envelope["provisional"] if envelope else None,
        "decision_schema_version": DECISION_SCHEMA_VERSION,
        "packets_validated": packet_count,
        "study_count": len(studies),
        "publication_count": len(pubs),
        "alias_count": len(aliases),
        "alias_status_counts": alias_counts,
        "merged_alias_count": alias_counts["MERGED_VERIFIED"],
        "study_status_counts": study_counts,
        "overlap_flag_ids": [flag["flag_id"] for flag in flags],
        "overlap_edges_emitted": 0,
        "null_tokens": {NULL_TOKEN: NULL_TOKEN_MEANING, UNKNOWN_TOKEN: UNKNOWN_TOKEN_MEANING},
        "enums": _enum_declaration(),
        "status_ceiling": "CANDIDATE_OR_RESOLVING_ONLY_FROM_CODE",
        "schema_versions": {
            "study_registry": study_version,
            "publication_family": pub_version,
            "decision": DECISION_SCHEMA_VERSION,
        },
        "failure_codes": {
            "scientific": list(SCIENTIFIC_FAILURE_CODES),
            "structural": list(STRUCTURAL_FAILURE_CODES),
        },
        "tsv_row_counts": {
            "study_registry.tsv": len(studies),
            "publication_family_registry.tsv": len(pubs),
            "study_alias_crosswalk.tsv": len(aliases),
        },
        "tsv_sha256": {name: _digest(text) for name, text in tables.items()},
    }
    receipt.update(extra or {})
    receipt["repository_prefix_alias_types"] = {prefix: list(types) for prefix, types in REPOSITORY_PREFIX_ALIAS_TYPES.items()}
    receipt["placeholder_reviewers"] = list(PLACEHOLDER_REVIEWERS)
    receipt["identity_rules"] = {
        "repository_requires": "MERGED_VERIFIED alias of the same study and matching alias type",
        "identity_ownership_scope": ["repository_accession", "trial_id", "publication_family_id", "pmid", "doi",
                                     "alias rows of identity-bearing types (non-DISPROVED, target not UNKNOWN)"],
        "identity_ownership_fold": "same fold as the alias conflict key",
        "cross_study_pmid_or_doi": "refused (conservative; no amended rule permits sharing yet)",
    }
    receipt["reviewer_placeholder_rule"] = ("casefold, NFKD, drop combining marks, keep str.isalnum() characters "
                                            "(Unicode-aware); empty result refused")
    return {
        "receipt": receipt,
        "study_records": sorted(studies, key=lambda row: row["study_id"]),
        "publication_records": sorted(pubs, key=lambda row: (row["study_id"], row["publication_id"])),
        "alias_rows": sorted(aliases, key=lambda row: (row["canonical_study_id"], row["alias_type"],
                                                       row["alias_value"], row["alias_id"])),
        "overlap_flags": flags,
        "tables": tables,
    }


def resolve(packets, decision, valid_query_ids, study_schema, publication_schema):
    """Resolve validated candidate packets and one integrator decision into proposed records.

    packets: list of candidate packets (each validated by search_log).
    decision: an explicit integrator decision dict, or None. None creates nothing.
    valid_query_ids: the set of query IDs the packets may cite.
    study_schema, publication_schema: the frozen JSON schemas, passed in (no file I/O here).
    """
    if not isinstance(packets, list):
        _fail("MALFORMED_DECISION", "packets must be a list of candidate packets")
    packet_ids = _validate_packets(packets, valid_query_ids)
    study_validator = _validator(study_schema)
    publication_validator = _validator(publication_schema)
    study_version = _schema_default(study_schema)
    pub_version = _schema_default(publication_schema)
    if decision is None:
        return _assemble(len(packets), None, [], [], [], [], study_version, pub_version)

    envelope = _validate_envelope(decision, set(packet_ids))
    studies = [_normalize_study(entry, f"studies[{index}]")
               for index, entry in enumerate(_list(decision["studies"], "studies"))]
    if envelope["provisional"]:
        for study in studies:
            if study["requested_status"] in STUDY_STATUSES_DECISION_ONLY:
                _fail("STATUS_CEILING", "a provisional decision cannot emit EXCLUDED or SUPERSEDED")
    study_ids = [study["study_id"] for study in studies]
    if len(set(study_ids)) != len(study_ids):
        _fail("DUPLICATE_STUDY_ID", "study IDs must be unique")
    study_map = {study["study_id"]: study for study in studies}

    superseries_blocks = [_normalize_superseries(entry, f"superseries[{index}]")
                          for index, entry in enumerate(_list(decision["superseries"], "superseries"))]
    alias_entries = [_normalize_alias(entry, f"aliases[{index}]")
                     for index, entry in enumerate(_list(decision["aliases"], "aliases"))]
    candidates = _alias_candidates(alias_entries, superseries_blocks, set(study_ids))
    alias_rows = _alias_rows(candidates, envelope)
    flags = _overlap_flags(_list(decision["overlap_flags"], "overlap_flags"), set(study_ids))
    pub_records = _publication_records(_list(decision["publications"], "publications"), study_map,
                                       publication_validator, pub_version)
    _check_identity_ownership(studies, pub_records, alias_rows)
    _check_repository_verification(studies, alias_rows)
    study_records = _study_records(studies, alias_rows, flags, pub_records, study_validator, study_version)
    sra_unknown = sum(1 for block in superseries_blocks for sub in block["subseries"]
                      if sub["sra_study"] == UNKNOWN_TOKEN)
    return _assemble(len(packets), envelope, study_records, pub_records, alias_rows, flags,
                     study_version, pub_version, extra={"subseries_sra_unknown_count": sra_unknown})
