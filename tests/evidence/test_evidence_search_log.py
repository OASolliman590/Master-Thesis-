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




























# Revision 1 (coordinator review findings R1-F1..F12). Each test pins a defect
# found by adversarial probing of the original implementation.

QIDS = {"GSE-PUBLIC-20261016"}


def packet(mutate=None, query_ids=None):
    p = candidate(query_ids)
    if mutate:
        mutate(p)
    p["packet_id"] = candidate_packet_id({k: v for k, v in p.items() if k != "packet_id"})
    return p






























def test_recorded_canonical_tracer_urls_validate_against_their_queries():
    receipt = json.loads((Path(__file__).parents[2] / "docs/validation/A_DAV_02/PUBLIC_TRACER_RECEIPT.json").read_text(encoding="utf-8"))
    urls = [entry["url"] for entry in receipt["canonical_request_urls"]]
    pages = [page(POSITIVE_QUERY, 0, ["200091061"], url=urls[0]), page(POSITIVE_QUERY, 1, ["200078220"], url=urls[1])]
    assert validate_search_run(run(pages=pages))["completion_status"] == "COMPLETE"
    zero = run("NO-RESULT-20261016", NO_RESULT_QUERY, [page(NO_RESULT_QUERY, 0, [], count=0, url=urls[2])],
               pagination_end=0, result_ids=[], screened_count=0)
    assert validate_search_run(zero)["completion_status"] == "COMPLETE"








# Revision 2 (Claude pre-review findings M1-M3, L1, L2, L6; trivial L4, L7).

NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds"


def two_pages(url0):
    return [page(POSITIVE_QUERY, 0, ["200091061"], url=url0), page(POSITIVE_QUERY, 1, ["200078220"])]


def rejected(fn, code="SECRET_LOCATOR"):
    with pytest.raises(SearchLogError) as error:
        fn()
    assert error.value.code == code




























# Revision 3 (Sol 5.6 MEDIUM review findings M-01..M-04).
















# Revision 4 (Sol re-review findings M-02 and M-04 still open, plus new N-01).














# Revision 5 (Sol FAIL-CLOSED policy ruling, SOL_POLICY_RULING_BEARER.md): every
# case-sensitive "Bearer" followed by 16+ token characters is a secret, whatever follows.
# N-01 and N-03 inputs are Low, accepted false positives under that ruling.






