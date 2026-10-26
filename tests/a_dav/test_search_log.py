import copy
import json
from pathlib import Path

import pytest

from tools.a_dav.search_log import (
    SEARCH_LOG_HEADER,
    SearchLogError,
    candidate_packet_id,
    render_search_log_tsv,
    validate_candidate_packet,
    validate_search_log,
    validate_search_run,
)


FIXTURES = Path(__file__).parent / "fixtures"
POSITIVE_QUERY = "(GSE91061[ACCN] OR GSE78220[ACCN]) AND gse[ETYP]"
NO_RESULT_QUERY = "A_DAV_02_INTENTIONAL_NO_RESULT_20261016[ACCN]"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def page(query, retstart, ids, count=2, url=None):
    return {
        "query": query,
        "count": count,
        "retstart": retstart,
        "retmax": 1,
        "result_ids": ids,
        "url": url or "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json",
    }


def run(query_id="GSE-PUBLIC-20261016", query=POSITIVE_QUERY, pages=None, **overrides):
    value = {
        "query_id": query_id,
        "lane": "catalogue_resolution",
        "source": "NCBI GEO DataSets",
        "exact_query": query,
        "searched_utc": "2026-10-16T13:56:57Z",
        "filters": "db=gds;retmode=json;retmax=1",
        "pagination_start": 0,
        "pagination_end": 2,
        "result_ids": ["200091061", "200078220"],
        "screened_count": 2,
        "included_count": 0,
        "excluded_count": 0,
        "disposition_summary": "Metadata candidates only; no records admitted.",
        "follow_up_action": "Resolve publication families under DAV-T02.",
        "completion_status": "COMPLETE",
        "agent_id": "A-DAV-02-public-tracer",
        "reviewer": "pending",
        "supersedes_query_id": "",
        "pages": pages or [
            page(POSITIVE_QUERY, 0, ["200091061"]),
            page(POSITIVE_QUERY, 1, ["200078220"]),
        ],
    }
    value.update(overrides)
    return value


def candidate(query_ids=None):
    return {
        "packet_id": "pending",
        "lane": "catalogue_resolution",
        "query_ids": query_ids or ["GSE-PUBLIC-20261016"],
        "candidate_label": "NCBI GDS public metadata tracer",
        "verified_facts": [
            {
                "claim": "ESearch returned a public catalogue identifier.",
                "source_locator": {
                    "kind": "URL",
                    "value": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds",
                    "page_or_section": "retstart=0",
                },
            }
        ],
        "inferences": [{"statement": "These identifiers require source review.", "supporting_fact_indices": [0]}],
        "unknowns": [{"field": "publication_family", "resolution_path": "Review original publications.", "blocking_branches": ["admission"]}],
        "proposed_records": {},
        "suspected_overlap": [],
        "recommended_next_action": "DAV-T02 review",
        "agent_id": "catalogue-tracer",
        "completed_utc": "2026-10-16T13:56:57Z",
    }


def test_official_two_page_observation_validates_and_uses_frozen_header():
    p0, p1 = fixture("ncbi_esearch_gse_page_0.json"), fixture("ncbi_esearch_gse_page_1.json")
    assert p0["esearchresult"]["count"] == p1["esearchresult"]["count"] == "2"
    assert p0["esearchresult"]["idlist"] == ["200091061"]
    assert p1["esearchresult"]["idlist"] == ["200078220"]
    checked = validate_search_run(run())
    assert checked["completion_status"] == "COMPLETE"
    assert checked["result_ids"] == ["200078220", "200091061"]
    frozen_header = (Path(__file__).parents[2] / "specs/A_DATA_ACQUISITION_VALIDATION/templates/search_log.tsv").read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert list(SEARCH_LOG_HEADER) == frozen_header
    assert render_search_log_tsv([checked]).splitlines()[0] == "\t".join(frozen_header)


def test_official_zero_result_is_complete_with_zero_counts():
    observed = fixture("ncbi_esearch_no_result.json")["esearchresult"]
    assert observed["count"] == "0" and observed["idlist"] == []
    value = run("NO-RESULT-20261016", NO_RESULT_QUERY, [page(NO_RESULT_QUERY, 0, [], count=0)],
                pagination_end=0, result_ids=[], screened_count=0, included_count=0,
                excluded_count=0)
    assert validate_search_run(value)["completion_status"] == "COMPLETE"


def test_incomplete_missing_page_must_be_explicit_and_cannot_claim_complete():
    value = run(pages=[page(POSITIVE_QUERY, 0, ["200091061"])], pagination_end=1,
                result_ids=["200091061"], screened_count=1)
    with pytest.raises(SearchLogError) as error:
        validate_search_run(value)
    assert error.value.code == "PAGINATION_INCOMPLETE"
    value["completion_status"] = "INCOMPLETE"
    assert validate_search_run(value)["completion_status"] == "INCOMPLETE"


@pytest.mark.parametrize("pages,code", [
    ([page(POSITIVE_QUERY, 0, ["200091061"]), page(POSITIVE_QUERY, 0, ["200078220"])], "PAGE_OVERLAP"),
    ([page(POSITIVE_QUERY, 0, ["200091061"]), page(POSITIVE_QUERY, 1, ["200091061"])], "DUPLICATE_RESULT_ID"),
    ([page(POSITIVE_QUERY, 0, ["200091061"], count=3), page(POSITIVE_QUERY, 1, ["200078220"])], "PAGE_COUNT_MISMATCH"),
    ([page(POSITIVE_QUERY, 0, ["200091061"]), page("other query", 1, ["200078220"])], "PAGE_QUERY_MISMATCH"),
    ([page(POSITIVE_QUERY, 0, ["200091061"], count=20001) | {"retmax": 20001}], "INVALID_PAGE_RANGE"),
    ([page(POSITIVE_QUERY, 0, [], count=2), page(POSITIVE_QUERY, 1, ["200078220"])], "PAGE_RESULT_COUNT_MISMATCH"),
])
def test_invalid_page_receipts_fail_closed(pages, code):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(pages=pages))
    assert error.value.code == code


@pytest.mark.parametrize("field,value", [
    ("exact_query", "GSE91061[ACCN]&api_key=abc123"),
    ("filters", "db=gds&token=abc123"),
])
def test_secret_bearing_query_and_filter_are_rejected(field, value):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(**{field: value}))
    assert error.value.code == "SECRET_LOCATOR"


@pytest.mark.parametrize("url,code", [
    ("https://eutils.ncbi.nlm.nih.gov/x?api_key=secret", "SECRET_LOCATOR"),
    ("javascript:alert(1)", "MALFORMED_LOCATOR"),
    ("https://user:pass@example.org/x", "MALFORMED_LOCATOR"),
])
def test_page_url_must_be_safe_http_locator(url, code):
    value = run(pages=[page(POSITIVE_QUERY, 0, ["200091061"], url=url), page(POSITIVE_QUERY, 1, ["200078220"])])
    with pytest.raises(SearchLogError) as error:
        validate_search_run(value)
    assert error.value.code == code


@pytest.mark.parametrize("changes,code", [
    ({"searched_utc": "16-10-2026"}, "INVALID_UTC_TIMESTAMP"),
    ({"screened_count": -1}, "INVALID_COUNT"),
    ({"included_count": 3}, "COUNT_ACCOUNTING"),
    ({"query_id": "not lexical"}, "INVALID_IDENTIFIER"),
])
def test_search_log_field_constraints(changes, code):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(**changes))
    assert error.value.code == code


def test_duplicate_query_id_rejected_across_log():
    with pytest.raises(SearchLogError) as error:
        validate_search_log([run(), run()])
    assert error.value.code == "DUPLICATE_QUERY_ID"


def test_idempotent_packet_revalidation_and_valid_supersession_are_distinguished():
    original = run()
    corrected = run("GSE-PUBLIC-20261017", supersedes_query_id=original["query_id"])
    assert len(validate_search_log([original, corrected])) == 2
    with pytest.raises(SearchLogError) as error:
        validate_search_log([original, run("GSE-PUBLIC-20261017", supersedes_query_id="missing")])
    assert error.value.code == "INVALID_SUPERSESSION"


def test_candidate_packet_requires_validated_facts_inferences_and_unknowns():
    p = candidate()
    p["packet_id"] = candidate_packet_id({k: v for k, v in p.items() if k != "packet_id"})
    receipt = validate_candidate_packet(p, {"GSE-PUBLIC-20261016"})
    assert receipt["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"
    assert receipt["admitted_count"] == 0
    assert receipt["analysis_readiness"] == "NOT_ANALYSIS_READY"


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p["verified_facts"][0].pop("source_locator"), "FACT_LOCATOR_REQUIRED"),
    (lambda p: p["inferences"][0].update(supporting_fact_indices=[4]), "INVALID_INFERENCE_INDEX"),
    (lambda p: p["unknowns"][0].pop("resolution_path"), "UNKNOWN_RESOLUTION_REQUIRED"),
    (lambda p: p["verified_facts"][0]["source_locator"].update(value="https://x.test/?sig=secret"), "SECRET_LOCATOR"),
    (lambda p: p["verified_facts"][0].update(claim="Found https://x.test/?Signature=private&Expires=1&Key-Pair-Id=K"), "SECRET_LOCATOR"),
    (lambda p: p["verified_facts"][0]["claim"].__class__, None),
])
def test_malformed_candidate_facts_and_references_fail(mutate, code):
    p = candidate()
    mutate(p)
    if code is None:
        p["verified_facts"][0]["claim"] = ""
        code = "MALFORMED_FACT"
    with pytest.raises(SearchLogError) as error:
        validate_candidate_packet(p, {"GSE-PUBLIC-20261016"})
    assert error.value.code == code


def test_candidate_packet_id_and_normalization_ignore_key_row_and_page_order():
    first = run()
    second = copy.deepcopy(first)
    second["pages"] = list(reversed(second["pages"]))
    second["result_ids"] = list(reversed(second["result_ids"]))
    assert validate_search_run(first) == validate_search_run(second)
    base = candidate()
    base.pop("packet_id")
    base["pages"] = [page(POSITIVE_QUERY, 0, ["200091061"]), page(POSITIVE_QUERY, 1, ["200078220"])]
    reordered = dict(reversed(list(base.items())))
    reordered["pages"] = list(reversed(reordered["pages"]))
    assert candidate_packet_id(base) == candidate_packet_id(reordered)


def test_duplicate_query_id_allowed_only_for_exact_packet_revalidation():
    p = candidate()
    p["packet_id"] = candidate_packet_id({k: v for k, v in p.items() if k != "packet_id"})
    first, second = run(candidate_packet=p), run(candidate_packet=copy.deepcopy(p))
    allowed = validate_search_log([first, second])
    assert len(allowed) == 2
    changed = copy.deepcopy(p)
    changed["candidate_label"] = "changed"
    first, second = run(candidate_packet=p), run(candidate_packet=changed)
    with pytest.raises(SearchLogError) as error:
        validate_search_log([first, second])
    assert error.value.code == "DUPLICATE_QUERY_ID"


# Revision 1 (coordinator review findings R1-F1..F12). Each test pins a defect
# found by adversarial probing of the original implementation.

QIDS = {"GSE-PUBLIC-20261016"}


def packet(mutate=None, query_ids=None):
    p = candidate(query_ids)
    if mutate:
        mutate(p)
    p["packet_id"] = candidate_packet_id({k: v for k, v in p.items() if k != "packet_id"})
    return p


def test_final_partial_page_is_valid_pagination():
    pages = [page(POSITIVE_QUERY, 0, ["1", "2"], count=3) | {"retmax": 2},
             page(POSITIVE_QUERY, 2, ["3"], count=3) | {"retmax": 2}]
    checked = validate_search_run(run(pages=pages, result_ids=["1", "2", "3"], pagination_end=3, screened_count=3))
    assert checked["completion_status"] == "COMPLETE"
    assert checked["pagination_end"] == 3


@pytest.mark.parametrize("pages,code", [
    ([page(POSITIVE_QUERY, 2, [], count=2)], "INVALID_PAGE_RANGE"),
    ([page(POSITIVE_QUERY, 1, [], count=0)], "INVALID_PAGE_RANGE"),
])
def test_page_outside_result_range_fails_closed(pages, code):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(pages=pages))
    assert error.value.code == code


@pytest.mark.parametrize("mutate", [
    lambda p: p["proposed_records"].update(authors=["Riaz N"], design="phase II"),
    lambda p: p.update(design_implications=["Pairing requires DAV-T06 timing review."]),
    lambda p: p["verified_facts"][0]["source_locator"].update(value="https://pubmed.ncbi.nlm.nih.gov/?term=x&author=Riaz"),
    lambda p: p["proposed_records"].update(signal_type="RNA", tokenizer_note="none"),
])
def test_legitimate_scientific_keys_are_not_secret_false_positives(mutate):
    assert validate_candidate_packet(packet(mutate), QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("mutate", [
    lambda p: p["proposed_records"].update(client_secret="x"),
    lambda p: p["proposed_records"].update(sessionToken="x"),
    lambda p: p["verified_facts"][0]["source_locator"].update(value="https://x.test/o?X-Amz-Credential=a&X-Amz-Signature=b"),
    lambda p: p["verified_facts"][0].update(claim="Header was Authorization: Bearer abcdef0123456789xyz"),
    lambda p: p["verified_facts"][0].update(claim="key ghp_abcdefghijklmnopqrstuvwxyz0123"),
    lambda p: p["unknowns"][0].update(resolution_path="-----BEGIN OPENSSH PRIVATE KEY----- x"),
])
def test_secret_material_in_packet_is_rejected(mutate):
    with pytest.raises(SearchLogError) as error:
        validate_candidate_packet(packet(mutate), QIDS)
    assert error.value.code == "SECRET_LOCATOR"


def test_attached_candidate_packet_is_validated_for_every_row():
    bad = candidate()
    bad["packet_id"] = "not-the-canonical-id"
    with pytest.raises(SearchLogError) as error:
        validate_search_log([run(candidate_packet=bad)])
    assert error.value.code == "PACKET_ID_MISMATCH"


def test_attached_packet_must_reference_its_host_query():
    other = packet()
    with pytest.raises(SearchLogError) as error:
        validate_search_log([run(), run("GSE-PUBLIC-20261018", candidate_packet=other)])
    assert error.value.code == "INVALID_PACKET_QUERY"


def test_duplicate_query_id_with_same_packet_but_different_row_is_rejected():
    p = packet()
    altered = run(candidate_packet=copy.deepcopy(p), disposition_summary="Different disposition.")
    with pytest.raises(SearchLogError) as error:
        validate_search_log([run(candidate_packet=p), altered])
    assert error.value.code == "DUPLICATE_QUERY_ID"


def test_render_applies_log_level_checks_and_emits_idempotent_row_once():
    with pytest.raises(SearchLogError) as error:
        render_search_log_tsv([run(), run()])
    assert error.value.code == "DUPLICATE_QUERY_ID"
    p = packet()
    tsv = render_search_log_tsv([run(candidate_packet=p), run(candidate_packet=copy.deepcopy(p))])
    assert len(tsv.splitlines()) == 2


@pytest.mark.parametrize("value", ["2026-10-16T13Z", "2026-10-16T13:56Z", "2026-10-16 13:56:57Z",
                                   "2026-10-16T13:56:57.123456789Z", "2026-10-16T13:56:57+00:00"])
def test_utc_timestamp_must_be_full_second_precision_z(value):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(searched_utc=value))
    assert error.value.code == "INVALID_UTC_TIMESTAMP"


def test_utc_timestamp_accepts_fractional_seconds():
    assert validate_search_run(run(searched_utc="2026-10-16T13:56:57.250Z"))["searched_utc"].endswith("Z")


@pytest.mark.parametrize("kind,value", [
    ("PMID", "not-a-pmid"), ("PMID", "0123"), ("DOI", "nonsense"),
    ("FILE", "/home/omics/projects/private.tsv"), ("FILE", "../../outside"), ("FILE", "~/x"),
    ("FILE", "C:\\data\\x.tsv"),
])
def test_non_url_fact_locators_are_format_checked(kind, value):
    with pytest.raises(SearchLogError) as error:
        validate_candidate_packet(packet(lambda p: p["verified_facts"][0]["source_locator"].update(kind=kind, value=value)), QIDS)
    assert error.value.code == "MALFORMED_LOCATOR"


@pytest.mark.parametrize("kind,value", [
    ("PMID", "28038787"), ("DOI", "10.1016/j.cell.2017.09.028"),
    ("FILE", "specs/A_DATA_ACQUISITION_VALIDATION/templates/search_log.tsv"),
])
def test_well_formed_non_url_fact_locators_pass(kind, value):
    p = packet(lambda p: p["verified_facts"][0]["source_locator"].update(kind=kind, value=value))
    assert validate_candidate_packet(p, QIDS)["admitted_count"] == 0


def test_screened_count_cannot_exceed_retrieved_result_ids():
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(screened_count=3))
    assert error.value.code == "COUNT_ACCOUNTING"


def test_page_url_term_must_match_page_query():
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term=OTHER%5BACCN%5D"
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(pages=[page(POSITIVE_QUERY, 0, ["200091061"], url=url), page(POSITIVE_QUERY, 1, ["200078220"])]))
    assert error.value.code == "PAGE_QUERY_MISMATCH"




@pytest.mark.parametrize("content", [{"x": {1, 2}}, {"x": float("nan")}])
def test_non_canonical_json_packet_content_fails_with_reason_code(content):
    with pytest.raises(SearchLogError) as error:
        candidate_packet_id(content)
    assert error.value.code == "MALFORMED_PACKET"


def test_duplicate_query_id_with_different_valid_packet_is_rejected():
    first = packet()
    second = packet(lambda p: p.update(candidate_label="different but validly hashed"))
    with pytest.raises(SearchLogError) as error:
        validate_search_log([run(candidate_packet=first), run(candidate_packet=second)])
    assert error.value.code == "DUPLICATE_QUERY_ID"


def test_pagination_cursor_keys_are_not_treated_as_credentials():
    url = "https://catalogue.example.org/api/search?q=x&pageToken=abc&nextPageToken=def"
    value = run(pages=[page(POSITIVE_QUERY, 0, ["200091061"], url=url), page(POSITIVE_QUERY, 1, ["200078220"])])
    assert validate_search_run(value)["completion_status"] == "COMPLETE"


# Revision 2 (Claude pre-review findings M1-M3, L1, L2, L6; trivial L4, L7).

NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds"


def two_pages(url0):
    return [page(POSITIVE_QUERY, 0, ["200091061"], url=url0), page(POSITIVE_QUERY, 1, ["200078220"])]


def rejected(fn, code="SECRET_LOCATOR"):
    with pytest.raises(SearchLogError) as error:
        fn()
    assert error.value.code == code


@pytest.mark.parametrize("text", [
    "db=gds;secret_key=abc", "aws_secret_access_key=wJalrXUtnFEMI", "access_key=abc", "pwd=hunter2",
    "api_key: abc123def456", '{"api_key":"abc123def456"}', "api%5Fkey=abc123", "api%255Fkey=abc123",
    "key sk-proj-abcdefghijklmnopqrstuvwx", "AIzaSyA1234567890abcdefghijklmnopqrstu",
])
def test_m1_credential_names_and_formats_in_text_are_rejected(text):
    rejected(lambda: validate_search_run(run(filters=text)))


@pytest.mark.parametrize("url", [
    NCBI + "&key=AIzaSyA1234567890abcdefghijklmnopqrstu",
    NCBI + "#access_token=abc123",
    NCBI + ";api_key=SECRET",
    NCBI + "&api%255Fkey=SECRET",
])
def test_m1_m2_page_url_secret_variants_are_rejected(url):
    rejected(lambda: validate_search_run(run(pages=two_pages(url))))


def test_m1_credential_dict_key_is_rejected():
    rejected(lambda: validate_candidate_packet(packet(lambda p: p["proposed_records"].update(access_key="x")), QIDS))


@pytest.mark.parametrize("url", ["https://exa mple.org/x", "https://x.org:abc/", "https:///nohost"])
def test_m2_malformed_page_url_host_or_port_is_rejected(url):
    rejected(lambda: validate_search_run(run(pages=two_pages(url))), "MALFORMED_LOCATOR")


def test_m2_userinfo_url_in_run_query_text_is_rejected():
    q = "see https://user:pw@x.org/q"
    pages = [page(q, 0, ["200091061"]), page(q, 1, ["200078220"])]
    rejected(lambda: validate_search_run(run(query=q, exact_query=q, pages=pages)))


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(suspected_overlap=["https://user:pw@x.org/a"]),
    lambda p: p["verified_facts"][0].update(claim="mirror at HTTPS://user:pw@x.org/a"),
    lambda p: p["verified_facts"][0].update(claim="mirror at ftp://anon:secret@ftp.x.org/a"),
    lambda p: p["unknowns"][0].update(resolution_path="https://x.org/a#token=abc123"),
])
def test_m2_embedded_urls_anywhere_in_packet_are_checked(mutate):
    rejected(lambda: validate_candidate_packet(packet(mutate), QIDS))


@pytest.mark.parametrize("mutate", [
    lambda p: p["proposed_records"].update(gene_signature="HOPE18", mutational_signature="SBS4", signature="CYT"),
    lambda p: p["proposed_records"].update(sig="p<0.05", auth="Riaz N et al."),
    lambda p: p["verified_facts"][0].update(claim="HLA-B44 bearer subgroups had longer OS"),
    lambda p: p["verified_facts"][0].update(claim="dbGaP authorization: required before access"),
    lambda p: p["verified_facts"][0].update(claim="Programme signature=IFNG-6"),
    lambda p: p["verified_facts"][0].update(claim="Signature: HOPE18"),
    lambda p: p["verified_facts"][0].update(claim="Bearer subgroups were defined by HLA typing"),
])
def test_m3_scientific_text_is_not_a_secret_false_positive(mutate):
    assert validate_candidate_packet(packet(mutate), QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("field,value", [
    ("disposition_summary", "api_key=abc123secret"), ("follow_up_action", "retry with token=abc"),
    ("agent_id", "token=abc"), ("reviewer", "password=x"), ("lane", "lane https://u:p@x.org"),
    ("source", "NCBI ?api_key=abc"),
])
def test_l1_all_rendered_row_text_is_secret_scanned(field, value):
    rejected(lambda: validate_search_run(run(**{field: value})))


def test_l2_duplicate_zero_result_pages_overlap():
    pages = [page(NO_RESULT_QUERY, 0, [], count=0), page(NO_RESULT_QUERY, 0, [], count=0)]
    value = run("NO-RESULT-20261016", NO_RESULT_QUERY, pages, pagination_end=0, result_ids=[], screened_count=0)
    rejected(lambda: validate_search_run(value), "PAGE_OVERLAP")


@pytest.mark.parametrize("value", ["file:///etc/passwd", "%2e%2e/%2e%2e/etc/passwd", "%2Fetc%2Fpasswd",
                                   "s3://bucket/private.tsv", "%7E/x"])
def test_l6_file_locator_uri_and_encoded_traversal_rejected(value):
    rejected(lambda: validate_candidate_packet(
        packet(lambda p: p["verified_facts"][0]["source_locator"].update(kind="FILE", value=value)), QIDS),
        "MALFORMED_LOCATOR")


def test_l4_idempotent_revalidation_uses_canonical_packet_identity():
    p = packet(lambda p: p.update(pages=[page(POSITIVE_QUERY, 0, ["200091061"]), page(POSITIVE_QUERY, 1, ["200078220"])]))
    reordered = copy.deepcopy(p)
    reordered["pages"] = list(reversed(reordered["pages"]))
    assert reordered["packet_id"] == candidate_packet_id({k: v for k, v in reordered.items() if k != "packet_id"})
    assert len(validate_search_log([run(candidate_packet=p), run(candidate_packet=reordered)])) == 2


def test_l7_blocking_branches_must_be_text():
    rejected(lambda: validate_candidate_packet(packet(lambda p: p["unknowns"][0].update(blocking_branches=[1, None])), QIDS),
             "MALFORMED_UNKNOWN")


def test_l7_frozenset_query_ids_are_accepted():
    assert validate_candidate_packet(packet(), frozenset(QIDS))["admitted_count"] == 0


# Revision 3 (Sol 5.6 MEDIUM review findings M-01..M-04).


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(verified_facts=[], inferences=[], unknowns=[]),
    lambda p: p.update(verified_facts=[], inferences=[]),
])
def test_m01_packet_without_any_source_located_fact_is_rejected(mutate):
    rejected(lambda: validate_candidate_packet(packet(mutate), QIDS), "FACT_LOCATOR_REQUIRED")


@pytest.mark.parametrize("params", ["&retstart=999&retmax=999", "&retstart=0&retmax=5", "&retstart=1&retmax=1"])
def test_m02_page_url_pagination_must_match_page_receipt(params):
    rejected(lambda: validate_search_run(run(pages=two_pages(NCBI + params))), "PAGE_URL_MISMATCH")


def test_m02_page_url_with_matching_pagination_is_accepted():
    pages = [page(POSITIVE_QUERY, 0, ["200091061"], url=NCBI + "&retstart=0&retmax=1"),
             page(POSITIVE_QUERY, 1, ["200078220"], url=NCBI + "&retstart=1&retmax=1")]
    assert validate_search_run(run(pages=pages))["completion_status"] == "COMPLETE"


@pytest.mark.parametrize("params", ["&retstart=abc", "&retstart=0&retstart=0", "&term=x&term=x"])
def test_m02_ambiguous_or_non_integer_url_pagination_is_rejected(params):
    with pytest.raises(SearchLogError) as error:
        validate_search_run(run(pages=two_pages(NCBI + params)))
    assert error.value.code in {"PAGE_URL_MISMATCH", "PAGE_QUERY_MISMATCH"}


@pytest.mark.parametrize("text", ["Bearer abcdefghijklmnop", "use Bearer abcdefghijklmnopqrstuv"])
def test_m03_letters_only_bearer_token_is_rejected(text):
    rejected(lambda: validate_search_run(run(filters=text)))


@pytest.mark.parametrize("where", ["locator", "page", "claim"])
def test_m04_scientific_signature_url_parameter_is_accepted(where):
    url = "https://catalogue.example.org/search?signature=HOPE18"
    if where == "page":
        assert validate_search_run(run(pages=two_pages(url)))["completion_status"] == "COMPLETE"
        return
    if where == "locator":
        p = packet(lambda p: p["verified_facts"][0]["source_locator"].update(value=url))
    else:
        p = packet(lambda p: p["verified_facts"][0].update(claim=f"Signature search at {url}"))
    assert validate_candidate_packet(p, QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("url", [
    "https://d1.cloudfront.net/o?Signature=abc&Expires=1&Key-Pair-Id=K",
    "https://storage.googleapis.com/b/o?X-Goog-Signature=abc",
    "https://bucket.s3.amazonaws.com/o?X-Amz-Signature=abc",
    "https://x.blob.core.windows.net/c/o?sv=2020&sig=abc",
    "https://api.example.org/x?oauth_signature=abc",
])
def test_m04_signed_url_signatures_remain_secret(url):
    rejected(lambda: validate_candidate_packet(packet(lambda p: p["verified_facts"][0]["source_locator"].update(value=url)), QIDS))


# Revision 4 (Sol re-review findings M-02 and M-04 still open, plus new N-01).


@pytest.mark.parametrize("params,code", [
    (";retstart=999;retmax=999", "PAGE_URL_MISMATCH"),
    (";retstart=0;retmax=5", "PAGE_URL_MISMATCH"),
    ("&retstart=0;retstart=0", "PAGE_URL_MISMATCH"),
    (";term=OTHER%5BACCN%5D", "PAGE_QUERY_MISMATCH"),
])
def test_r4_semicolon_separated_url_parameters_are_cross_checked(params, code):
    rejected(lambda: validate_search_run(run(pages=two_pages(NCBI + params))), code)


def test_r4_semicolon_separated_matching_pagination_is_accepted():
    pages = [page(POSITIVE_QUERY, 0, ["200091061"], url=NCBI + ";retstart=0;retmax=1"),
             page(POSITIVE_QUERY, 1, ["200078220"], url=NCBI + ";retstart=1;retmax=1")]
    assert validate_search_run(run(pages=pages))["completion_status"] == "COMPLETE"


@pytest.mark.parametrize("url", [
    "https://catalogue.example.org/search?signature=HOPE18&policy=inclusion",
    "https://catalogue.example.org/search?signature=HOPE18&expires=2027",
    "https://catalogue.example.org/search?signature=HOPE18&key-pair-id=K",
])
def test_r4_signature_with_partial_generic_context_is_scientific(url):
    p = packet(lambda p: p["verified_facts"][0]["source_locator"].update(value=url))
    assert validate_candidate_packet(p, QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("url", [
    "https://d1.cloudfront.net/o?Signature=abc&Policy=p&Key-Pair-Id=K",
    "https://d1.cloudfront.net/o?Expires=1&Signature=abc&Key-Pair-Id=K",
])
def test_r4_full_cloudfront_signed_set_is_secret(url):
    rejected(lambda: validate_candidate_packet(packet(lambda p: p["verified_facts"][0]["source_locator"].update(value=url)), QIDS))


@pytest.mark.parametrize("claim", [
    "HLA-B44 bearer subgroups had longer OS",
])
def test_r4_bearer_followed_by_scientific_prose_is_accepted(claim):
    p = packet(lambda p: p["verified_facts"][0].update(claim=claim))
    assert validate_candidate_packet(p, QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("text", [
    "Bearer abcdefghijklmnop",
    "header Bearer abcdefghijklmnopqr,",
    '{"h": "Bearer abcdefghijklmnopqr"}',
    "Bearer abcDefghijklmnopq then more words",
    "Bearer abcdefghijklmnop1 then more words",
    "Bearer abc.defghijklmnopq then more words",
    "Bearer abc_defghijklmnopq then more words",
])
def test_r4_bearer_token_by_character_class_or_standing_alone_is_rejected(text):
    rejected(lambda: validate_search_run(run(filters=text)))


# Revision 5 (Sol FAIL-CLOSED policy ruling, SOL_POLICY_RULING_BEARER.md): every
# case-sensitive "Bearer" followed by 16+ token characters is a secret, whatever follows.
# N-01 and N-03 inputs are Low, accepted false positives under that ruling.


@pytest.mark.parametrize("text", [
    "Bearer clinicopathological features were compared",                          # N-01
    "Bearer abcdefghijklmnop then more words",                                    # N-02
    "Bearer clinicopathological, molecular and immune features were compared",    # N-03
    "Bearer immunophenotypically distinct subsets responded",
    "Bearer Immunophenotypically distinct subsets responded",
    "use Bearer abcdefghijklmnopqrstuv now",
])
def test_r5_bearer_with_16_plus_token_characters_fails_closed(text):
    rejected(lambda: validate_search_run(run(filters=text)))
    rejected(lambda: validate_candidate_packet(packet(lambda p: p["verified_facts"][0].update(claim=text)), QIDS))
    rejected(lambda: validate_search_run(run(disposition_summary=text)))


@pytest.mark.parametrize("claim", [
    "bearer clinicopathological features were compared",
    "HLA-B44 bearer subgroups had longer OS",
    "Bearer subgroups were defined by HLA typing",
])
def test_r5_lowercase_or_short_bearer_prose_stays_accepted(claim):
    p = packet(lambda p: p["verified_facts"][0].update(claim=claim))
    assert validate_candidate_packet(p, QIDS)["status"] == "CANDIDATE_PACKET_VALID_NOT_ADMITTED"


@pytest.mark.parametrize("text", ["Authorization: Bearer abcdef0123456789xyz", "proxy-authorization: basic dXNlcjpwYXNzd29yZA=="])
def test_r5_authorization_header_detection_unchanged(text):
    rejected(lambda: validate_search_run(run(filters=text)))
