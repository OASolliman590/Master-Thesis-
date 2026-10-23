"""Pure validation for append-only discovery logs and proposed packets.

This module consumes only caller-provided dictionaries. It performs no I/O,
network access, source resolution, registry mutation, or admission decision.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import unquote, unquote_plus, urlsplit


SEARCH_LOG_HEADER = (
    "query_id", "lane", "source", "exact_query", "searched_utc", "filters",
    "pagination_start", "pagination_end", "result_ids", "screened_count",
    "included_count", "excluded_count", "disposition_summary", "follow_up_action",
    "completion_status", "agent_id", "reviewer", "supersedes_query_id",
)

_LEXICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MAX_RETPAGE = 10000
# Credential detection uses two vocabularies, compared after percent-decoding
# and removing case and separators. Credential names match in every context:
# record keys, "key=value" / "key: value" text and URL parameters.
_CREDENTIAL_EXACT = {"pwd", "passwd", "password", "passphrase", "secret", "token", "apikey",
                     "bearer", "cookie"}
_CREDENTIAL_SUFFIX = ("apikey", "secretkey", "accesskey", "accesskeyid", "privatekey", "sessionkey",
                      "signingkey", "token", "secret", "password", "passwd", "passphrase",
                      "credential", "credentials")
# These names are credentials only as URL parameters (?key=, ?sig=). In prose and
# record keys they are scientific words: gene signature, significance, author.
_URL_ONLY_EXACT = {"key", "sig", "auth", "authorization"}
# A URL "signature" parameter is a secret only in a signing scheme: a vendor-prefixed
# name (X-Amz-Signature, X-Goog-Signature, oauth_signature), or a plain "Signature"
# with the full CloudFront signed set (Key-Pair-Id plus Expires or Policy). A plain
# ?signature=HOPE18, even beside a generic policy= or expires=, is scientific.
_SIGNING_PREFIXES = ("xamz", "xgoog", "xms", "oauth", "aws")
_SIGNED_URL_REQUIRED = "keypairid"
_SIGNED_URL_ONE_OF = {"expires", "policy"}
# Pagination cursors are provenance, not credentials.
_NON_SECRET_KEYS = {"pagetoken", "nextpagetoken", "continuationtoken", "cursortoken"}
# Token formats are matched case-sensitively. Per the reviewer's FAIL-CLOSED ruling
# (SOL_POLICY_RULING_BEARER.md), "Bearer" followed by 16+ token characters is always a
# secret, whatever follows; a sentence-initial "Bearer <long word>" is an accepted false
# positive, while lowercase "bearer" prose is unaffected.
_SECRET_TOKEN = re.compile(
    r"\bBearer\s+[\w.~+/=-]{16,}"
    r"|\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bAIza[0-9A-Za-z_-]{30,}"
    r"|\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----")
_AUTH_HEADER = re.compile(r"\b(?:Proxy-)?Authorization\s*:\s*(?:Bearer|Basic|Token|Digest|Negotiate)\s+\S{8,}", re.I)
_TEXT_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_.%-]*)[\"']?\s*[=:]")
_EMBEDDED_URL = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'<>]+")
_HOSTNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_PMID = re.compile(r"^[1-9]\d{0,8}$")
_ID_FIELDS = ("query_id", "supersedes_query_id")


class SearchLogError(ValueError):
    """Validation failure carrying a stable machine-readable reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise SearchLogError(code, message)


def _fold_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unquote(unquote(key)).lower())


def _secret_key(key: str, url_parameter: bool = False, signed_url: bool = False) -> bool:
    folded = _fold_key(key)
    if folded in _NON_SECRET_KEYS:
        return False
    if folded in _CREDENTIAL_EXACT or folded.endswith(_CREDENTIAL_SUFFIX):
        return True
    if not url_parameter:
        return False
    if folded in _URL_ONLY_EXACT:
        return True
    return folded.endswith("signature") and (signed_url or folded.startswith(_SIGNING_PREFIXES))


def _query_parameters(url: str) -> list[tuple[str, str]]:
    """Query parameters split on both '&' and ';', as the secret scan does."""
    pairs = []
    for piece in re.split(r"[&;]", urlsplit(url).query):
        if piece:
            key, _, value = piece.partition("=")
            pairs.append((unquote_plus(key), unquote_plus(value)))
    return pairs


def _url_parameter_keys(parts) -> list[str]:
    """Keys from the query and fragment, split on both '&' and ';'."""
    return [piece.split("=", 1)[0] for chunk in (parts.query, parts.fragment)
            for piece in re.split(r"[&;]", chunk) if piece]


def _url_has_secret(parts) -> bool:
    keys = _url_parameter_keys(parts)
    folded = {_fold_key(key) for key in keys}
    signed = _SIGNED_URL_REQUIRED in folded and bool(folded & _SIGNED_URL_ONE_OF)
    return any(_secret_key(key, url_parameter=True, signed_url=signed) for key in keys)


def _validate_locator(value: str) -> None:
    if not isinstance(value, str) or not value or re.search(r"\s", value):
        _fail("MALFORMED_LOCATOR", "locator must be a non-empty string without whitespace")
    try:
        parts = urlsplit(value)
        parts.port
    except ValueError:
        _fail("MALFORMED_LOCATOR", "locator has an invalid host or port")
    if (parts.scheme not in {"http", "https"} or "@" in parts.netloc
            or not parts.hostname or not _HOSTNAME.fullmatch(parts.hostname)):
        _fail("MALFORMED_LOCATOR", "locator must be an absolute HTTP(S) URL with a valid host and no user information")
    if _url_has_secret(parts):
        _fail("SECRET_LOCATOR", "locator contains a credential-like query or fragment parameter")


def _check_embedded_url(value: str) -> None:
    """Any-scheme URL found inside text: reject user information and secret parameters."""
    value = value.rstrip(",.;)")
    try:
        parts = urlsplit(value)
    except ValueError:
        return
    if "@" in parts.netloc or _url_has_secret(parts):
        _fail("SECRET_LOCATOR", "text contains a URL with user information or a credential-like parameter")


def _scan_text(text: str) -> None:
    if not isinstance(text, str):
        _fail("MALFORMED_QUERY", "text fields must be strings")
    for variant in {text, unquote(text), unquote(unquote(text))}:
        if (_SECRET_TOKEN.search(variant) or _AUTH_HEADER.search(variant)
                or any(_secret_key(key) for key in _TEXT_ASSIGNMENT.findall(variant))):
            _fail("SECRET_LOCATOR", "text contains a credential-like key or token")
        for url in _EMBEDDED_URL.findall(variant):
            _check_embedded_url(url)


def _validate_fact_locator(kind: str, value: str) -> None:
    if kind == "URL":
        _validate_locator(value)
        return
    if not isinstance(value, str) or not value.strip():
        _fail("MALFORMED_LOCATOR", "fact locator value must be non-empty text")
    if kind == "DOI" and not _DOI.fullmatch(value):
        _fail("MALFORMED_LOCATOR", "DOI locator must have the form 10.<registrant>/<suffix>")
    if kind == "PMID" and not _PMID.fullmatch(value):
        _fail("MALFORMED_LOCATOR", "PMID locator must be a positive integer without leading zeros")
    if kind == "FILE":
        decoded = unquote(unquote(value)).replace("\\", "/")
        if (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", decoded) or decoded.startswith(("/", "~"))
                or ".." in decoded.split("/")):
            _fail("MALFORMED_LOCATOR", "FILE locator must be a relative path inside the project, not a URI")


def _utc(value: object) -> bool:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _normalize_page(page: dict) -> dict:
    if not isinstance(page, dict):
        _fail("MALFORMED_PAGE", "page receipt must be an object")
    query = page.get("query")
    if not isinstance(query, str) or not query:
        _fail("MALFORMED_PAGE", "page query must be non-empty")
    _scan_text(query)
    url = page.get("url")
    _validate_locator(url)
    params = _query_parameters(url)
    terms = [v for k, v in params if k == "term"]
    if any(term != query for term in terms):
        _fail("PAGE_QUERY_MISMATCH", "page URL term differs from the page query")
    for name in ("count", "retstart", "retmax"):
        value = page.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail("INVALID_PAGE_RANGE", f"page {name} must be a nonnegative integer")
    if page["retmax"] < 1 or page["retmax"] > _MAX_RETPAGE:
        _fail("INVALID_PAGE_RANGE", f"page retmax must be between 1 and {_MAX_RETPAGE}")
    # retmax is the requested page size; only the final page may be short.
    if page["count"] == 0 and page["retstart"] != 0:
        _fail("INVALID_PAGE_RANGE", "a zero-result page must start at retstart 0")
    if page["count"] > 0 and page["retstart"] >= page["count"]:
        _fail("INVALID_PAGE_RANGE", "page starts outside the reported result count")
    # A cited request URL must not contradict the receipt it documents.
    for name in ("retstart", "retmax"):
        values = [v for k, v in params if k == name]
        if len(values) > 1 or (values and (not values[0].isdigit() or int(values[0]) != page[name])):
            _fail("PAGE_URL_MISMATCH", f"page URL {name} contradicts the page receipt")
    ids = page.get("result_ids")
    if not isinstance(ids, list) or any(not isinstance(x, str) or not _LEXICAL_ID.fullmatch(x) for x in ids):
        _fail("INVALID_IDENTIFIER", "page result IDs must be lexical strings")
    if len(ids) > page["retmax"]:
        _fail("INVALID_PAGE_RANGE", "page returned more IDs than retmax")
    expected_ids = min(page["retmax"], max(0, page["count"] - page["retstart"]))
    if len(ids) != expected_ids:
        _fail("PAGE_RESULT_COUNT_MISMATCH", "page ID count does not match its covered result range")
    return {"query": query, "count": page["count"], "retstart": page["retstart"],
            "retmax": page["retmax"], "result_ids": list(ids), "url": url}


def validate_search_run(run: dict) -> dict:
    """Validate and normalize one search row and its in-memory page receipts."""
    if not isinstance(run, dict):
        _fail("MALFORMED_RUN", "search run must be an object")
    missing = [key for key in SEARCH_LOG_HEADER if key not in run]
    if missing:
        _fail("MISSING_FIELD", f"missing search-log fields: {', '.join(missing)}")
    for key in _ID_FIELDS:
        value = run[key]
        if key == "supersedes_query_id" and value == "":
            continue
        if not isinstance(value, str) or not _LEXICAL_ID.fullmatch(value):
            _fail("INVALID_IDENTIFIER", f"{key} must be a lexical identifier")
    for key in ("lane", "source", "agent_id", "reviewer"):
        if not isinstance(run[key], str) or not run[key].strip():
            _fail("MALFORMED_RUN", f"{key} must be non-empty text")
    _scan_text(run["exact_query"])
    _scan_text(run["filters"])
    if not run["exact_query"]:
        _fail("MALFORMED_QUERY", "exact_query must be non-empty")
    if not _utc(run["searched_utc"]):
        _fail("INVALID_UTC_TIMESTAMP", "searched_utc must be an ISO-8601 UTC timestamp ending in Z")
    for key in ("pagination_start", "pagination_end", "screened_count", "included_count", "excluded_count"):
        value = run[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail("INVALID_COUNT", f"{key} must be a nonnegative integer")
    if run["pagination_end"] < run["pagination_start"]:
        _fail("INVALID_COUNT", "pagination_end must not precede pagination_start")
    if run["included_count"] + run["excluded_count"] > run["screened_count"]:
        _fail("COUNT_ACCOUNTING", "included plus excluded cannot exceed screened count")
    for key in ("disposition_summary", "follow_up_action"):
        if not isinstance(run[key], str) or not run[key].strip():
            _fail("MALFORMED_RUN", f"{key} must be non-empty text")
    # Every free-text field is rendered into the canonical TSV, so all are secret-scanned.
    for key in ("lane", "source", "agent_id", "reviewer", "disposition_summary", "follow_up_action"):
        _scan_text(run[key])
    if run["completion_status"] not in {"COMPLETE", "INCOMPLETE"}:
        _fail("INVALID_COMPLETION_STATUS", "completion_status must be COMPLETE or INCOMPLETE")

    pages = run.get("pages")
    if not isinstance(pages, list) or not pages:
        _fail("MALFORMED_PAGE", "at least one page receipt is required")
    normalized = sorted((_normalize_page(p) for p in pages), key=lambda p: p["retstart"])
    if any(p["query"] != run["exact_query"] for p in normalized):
        _fail("PAGE_QUERY_MISMATCH", "page query differs from exact_query")
    counts = {p["count"] for p in normalized}
    if len(counts) != 1:
        _fail("PAGE_COUNT_MISMATCH", "pages report inconsistent total counts")
    total = next(iter(counts))
    if total == 0 and len(normalized) > 1:
        _fail("PAGE_OVERLAP", "a zero-result search has exactly one page receipt")
    cursor = 0
    all_ids = []
    covered = True
    for p in normalized:
        if p["retstart"] < cursor:
            _fail("PAGE_OVERLAP", "page ranges overlap")
        if p["retstart"] != cursor:
            covered = False
        cursor = min(p["retstart"] + p["retmax"], total)
        all_ids.extend(p["result_ids"])
    if len(set(all_ids)) != len(all_ids):
        _fail("DUPLICATE_RESULT_ID", "result IDs must be unique across pages")
    complete_coverage = total == 0 or (covered and cursor >= total)
    if total == 0:
        cursor = 0
    if run["completion_status"] == "COMPLETE" and not complete_coverage:
        _fail("PAGINATION_INCOMPLETE", "COMPLETE run does not cover every result position")
    if run["completion_status"] == "INCOMPLETE" and complete_coverage:
        _fail("INCOMPLETE_MISMATCH", "complete page coverage must be labeled COMPLETE")
    if run["pagination_start"] != normalized[0]["retstart"] or run["pagination_end"] != cursor:
        _fail("PAGINATION_SUMMARY_MISMATCH", "pagination summary does not match normalized page ranges")
    supplied_ids = run.get("result_ids")
    if not isinstance(supplied_ids, list) or any(not isinstance(x, str) for x in supplied_ids):
        _fail("INVALID_IDENTIFIER", "result_ids must be a list of lexical strings")
    if sorted(supplied_ids) != sorted(all_ids):
        _fail("RESULT_ID_MISMATCH", "result_ids do not match page receipts")
    if run["screened_count"] > len(all_ids):
        _fail("COUNT_ACCOUNTING", "screened count cannot exceed retrieved result IDs")
    result = {key: run[key] for key in SEARCH_LOG_HEADER}
    result["result_ids"] = sorted(all_ids)
    result["pages"] = normalized
    if "candidate_packet" in run:
        if not isinstance(run["candidate_packet"], dict):
            _fail("MALFORMED_PACKET", "candidate_packet must be an object")
        result["candidate_packet"] = run["candidate_packet"]
    return result


def validate_search_log(runs: list[dict]) -> list[dict]:
    """Validate log rows, duplicate IDs, and append-only supersession links."""
    if not isinstance(runs, list):
        _fail("MALFORMED_RUN", "runs must be a list")
    validated = [validate_search_run(run) for run in runs]
    valid_query_ids = {row["query_id"] for row in validated}
    by_id = {}
    first_index = {}
    for index, row in enumerate(validated):
        qid = row["query_id"]
        packet = row.get("candidate_packet")
        if qid in by_id:
            # Only an exact repeat of a packet-bearing row is an idempotent revalidation.
            # Packets compare by the hash of their canonical content, so page-order
            # differences inside a packet are not changes.
            if packet is None or _row_without_packet(by_id[qid]) != _row_without_packet(row) \
                    or _content_id(by_id[qid].get("candidate_packet")) != _content_id(packet):
                _fail("DUPLICATE_QUERY_ID", f"duplicate query_id: {qid}")
        else:
            by_id[qid] = row
            first_index[qid] = index
        if packet is not None:
            validate_candidate_packet(packet, valid_query_ids)
            if qid not in packet["query_ids"]:
                _fail("INVALID_PACKET_QUERY", f"attached candidate packet does not reference its row query_id: {qid}")
    for index, row in enumerate(validated):
        supersedes = row["supersedes_query_id"]
        if supersedes and (supersedes not in by_id or supersedes == row["query_id"] or first_index[supersedes] >= index):
            _fail("INVALID_SUPERSESSION", f"supersedes_query_id does not identify an earlier query: {supersedes}")
    return validated


def _content_id(packet: dict | None) -> str | None:
    if packet is None:
        return None
    return candidate_packet_id({key: value for key, value in packet.items() if key != "packet_id"})


def _row_without_packet(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "candidate_packet"}


def render_search_log_tsv(runs: list[dict]) -> str:
    """Render a validated log with the frozen header and escaped tabs/newlines.

    Exact idempotent revalidations are emitted once, so each query_id appears
    in at most one TSV row.
    """
    validated = validate_search_log(runs)
    lines = ["\t".join(SEARCH_LOG_HEADER)]
    emitted = set()
    for run in validated:
        if run["query_id"] in emitted:
            continue
        emitted.add(run["query_id"])
        values = []
        for key in SEARCH_LOG_HEADER:
            value = run[key]
            if key == "result_ids":
                value = ",".join(value)
            elif isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            text = str(value).replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
            values.append(text)
        lines.append("\t".join(values))
    return "\n".join(lines) + "\n"


def candidate_packet_id(packet_without_id: dict) -> str:
    """Return SHA-256 of compact sorted-key UTF-8 JSON packet content."""
    if not isinstance(packet_without_id, dict):
        _fail("MALFORMED_PACKET", "packet content must be an object")
    try:
        canonical = json.dumps(_canonical_packet_content(packet_without_id), ensure_ascii=False,
                               sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        _fail("MALFORMED_PACKET", f"packet content is not canonical JSON: {error}")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_packet_content(value):
    if isinstance(value, dict):
        normalized = {key: _canonical_packet_content(item) for key, item in value.items()}
        if isinstance(normalized.get("pages"), list) and all(isinstance(p, dict) and isinstance(p.get("retstart"), int) for p in normalized["pages"]):
            normalized["pages"] = sorted(normalized["pages"], key=lambda p: p["retstart"])
        return normalized
    if isinstance(value, list):
        return [_canonical_packet_content(item) for item in value]
    return value


def validate_candidate_packet(packet: dict, valid_query_ids: set[str]) -> dict:
    """Validate a catalogue-agent proposal without admitting any source."""
    if not isinstance(packet, dict) or not isinstance(valid_query_ids, (set, frozenset)):
        _fail("MALFORMED_PACKET", "packet and valid_query_ids have invalid types")
    required = {"packet_id", "lane", "query_ids", "candidate_label", "verified_facts", "inferences", "unknowns",
                "proposed_records", "suspected_overlap", "recommended_next_action", "agent_id", "completed_utc"}
    if required - packet.keys():
        _fail("MALFORMED_PACKET", "candidate packet is missing required envelope fields")
    for field in ("lane", "candidate_label", "recommended_next_action", "agent_id"):
        if not isinstance(packet[field], str) or not packet[field].strip():
            _fail("MALFORMED_PACKET", f"{field} must be non-empty text")
    content = {k: v for k, v in packet.items() if k != "packet_id"}
    if not isinstance(packet["packet_id"], str):
        _fail("PACKET_ID_MISMATCH", "packet_id must be a string")
    if not isinstance(packet["query_ids"], list) or not packet["query_ids"]:
        _fail("INVALID_PACKET_QUERY", "query_ids must be a non-empty list")
    if any(not isinstance(query_id, str) or not _LEXICAL_ID.fullmatch(query_id) for query_id in packet["query_ids"]):
        _fail("INVALID_PACKET_QUERY", "query_ids must be lexical identifiers")
    if len(set(packet["query_ids"])) != len(packet["query_ids"]):
        _fail("INVALID_PACKET_QUERY", "query_ids must not contain duplicates")
    for query_id in packet["query_ids"]:
        if not isinstance(query_id, str) or query_id not in valid_query_ids:
            _fail("INVALID_PACKET_QUERY", "candidate packet references an unknown query ID")
    if not _utc(packet["completed_utc"]):
        _fail("INVALID_UTC_TIMESTAMP", "completed_utc must be ISO-8601 UTC ending in Z")
    facts, inferences, unknowns = packet["verified_facts"], packet["inferences"], packet["unknowns"]
    if not all(isinstance(x, list) for x in (facts, inferences, unknowns)):
        _fail("MALFORMED_PACKET", "facts, inferences, and unknowns must be lists")
    if not facts:
        # "No packet is accepted without a source locator" (AGENTIC_SEARCH_ARCHITECTURE).
        _fail("FACT_LOCATOR_REQUIRED", "a candidate packet needs at least one source-located verified fact")
    if not isinstance(packet["proposed_records"], dict) or not isinstance(packet["suspected_overlap"], list):
        _fail("MALFORMED_PACKET", "proposed_records must be an object and suspected_overlap a list")
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("claim"), str) or not fact["claim"].strip():
            _fail("MALFORMED_FACT", "each verified fact needs a non-empty claim")
        locator = fact.get("source_locator")
        if not isinstance(locator, dict) or not locator.get("value"):
            _fail("FACT_LOCATOR_REQUIRED", "each verified fact requires a source locator")
        kind = locator.get("kind")
        if kind not in {"URL", "DOI", "PMID", "FILE"}:
            _fail("MALFORMED_LOCATOR", "fact locator kind must be URL, DOI, PMID, or FILE")
        _validate_fact_locator(kind, locator["value"])
    for inference in inferences:
        if not isinstance(inference, dict) or not isinstance(inference.get("statement"), str) or not inference["statement"].strip():
            _fail("MALFORMED_INFERENCE", "each inference needs a non-empty statement")
        indices = inference.get("supporting_fact_indices")
        if not isinstance(indices, list) or not indices or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(facts) for i in indices):
            _fail("INVALID_INFERENCE_INDEX", "inference indices must refer to verified facts")
    for unknown in unknowns:
        if not isinstance(unknown, dict) or not all(isinstance(unknown.get(k), str) and unknown[k].strip() for k in ("field", "resolution_path")):
            _fail("UNKNOWN_RESOLUTION_REQUIRED", "unknowns require field and resolution_path")
        branches = unknown.get("blocking_branches")
        if not isinstance(branches, list) or any(not isinstance(b, str) or not b.strip() for b in branches):
            _fail("MALFORMED_UNKNOWN", "unknown blocking_branches must be a list of non-empty text")
    _scan_recursive(packet)
    if packet["packet_id"] != candidate_packet_id(content):
        _fail("PACKET_ID_MISMATCH", "packet_id does not match canonical packet content")
    return {"packet_id": packet["packet_id"], "status": "CANDIDATE_PACKET_VALID_NOT_ADMITTED",
            "admitted_count": 0, "analysis_readiness": "NOT_ANALYSIS_READY"}


def _scan_recursive(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if _secret_key(str(key)):
                _fail("SECRET_LOCATOR", "candidate packet contains a credential-like key")
            _scan_recursive(item)
    elif isinstance(value, list):
        for item in value:
            _scan_recursive(item)
    elif isinstance(value, str):
        _scan_text(value)
