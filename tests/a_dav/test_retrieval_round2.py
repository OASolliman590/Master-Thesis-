from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.a_dav.retrieval import (
    RetrievalError,
    build_locator,
    load_plan,
    retrieve_plan,
)


def test_riaz_plan_has_nine_allowlisted_source_objects():
    plan_path = Path("tools/a_dav/fetch_plans/riaz_gse91061.json")
    plan = load_plan(plan_path)
    assert len(plan["objects"]) == 9
    assert {item["id"] for item in plan["objects"]} == {
        "geo_family_soft", "author_fpkm_hg19", "ncbi_tpm_grch38",
        "ncbi_annotation_grch38", "author_sample_table", "author_clinical_table",
        "author_analysis_code", "cbioportal_sample", "cbioportal_patient",
    }
    assert all(item["url"].startswith("https://") for item in plan["objects"])
    assert all(item["host"] in plan["allowed_hosts"] for item in plan["objects"])


@pytest.mark.parametrize("bad_cap", [None, 0, -1, True, "100"])
def test_plan_requires_positive_integer_max_object_bytes(bad_cap):
    plan = {
        "allowed_hosts": ["data.example.org"], "request_cap": 3,
        "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                     "expected_size": None, "expected_sha256": None, "max_bytes": 100}],
    }
    if bad_cap is not None:
        plan["max_object_bytes"] = bad_cap

    with pytest.raises(RetrievalError, match="PLAN_INVALID"):
        load_plan(plan)


def test_thin_url_adapters_pin_github_and_resolve_lfs_media():
    assert build_locator("github_raw", repo="riazn/bms038_analysis", commit="a" * 40,
                         path="data/example.csv") == (
        "https://raw.githubusercontent.com/riazn/bms038_analysis/" + "a" * 40 + "/data/example.csv"
    )
    url = build_locator("cbioportal_lfs", repo="cBioPortal/datahub", commit="b" * 40,
                        path="public/study/file.txt")
    assert url == "https://media.githubusercontent.com/media/cBioPortal/datahub/" + "b" * 40 + "/public/study/file.txt"


def test_retrieval_spaces_every_attempt_and_publishes_content_addressed_object(tmp_path):
    body = b"source bytes"
    digest = hashlib.sha256(body).hexdigest()
    plan = {
        "allowed_hosts": ["data.example.org"], "request_cap": 3, "max_object_bytes": len(body),
        "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                     "expected_size": len(body), "expected_sha256": digest, "max_bytes": len(body)}],
    }
    times: list[float] = []
    now = [0.0]
    attempts = [0]

    def clock():
        return now[0]

    def sleep(seconds):
        times.append(seconds)
        now[0] += seconds

    def transport(url, headers):
        attempts[0] += 1
        if attempts[0] == 1:
            return {"status": 503, "headers": {}, "body": b"", "final_url": url, "redirect_chain": [url]}
        return {"status": 200, "headers": {"Content-Length": str(len(body))}, "body": body,
                "final_url": url, "redirect_chain": [url]}

    result = retrieve_plan(plan, tmp_path, transport=transport, clock=clock, sleeper=sleep)
    assert attempts[0] == 2
    assert times and all(delay >= 0.5 for delay in times)
    assert (tmp_path / "objects" / digest).read_bytes() == body
    manifest = json.loads((tmp_path / "MANIFEST.json").read_text())
    entry = manifest["objects"][digest]
    assert entry["byte_size"] == len(body)
    assert entry["version"] == "v1"
    assert result["retrieved"] == 1


def test_nonallowlisted_redirect_is_rejected_before_body_is_accepted(tmp_path):
    plan = {"allowed_hosts": ["data.example.org"], "request_cap": 3, "max_object_bytes": 100,
            "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                         "expected_size": None, "expected_sha256": None, "max_bytes": 100}]}
    def transport(url, headers):
        return {"status": 302, "headers": {"Location": "https://evil.example/file"},
                "body": b"", "final_url": url, "redirect_chain": [url]}
    with pytest.raises(RetrievalError, match="HOST_OR_SCHEME_NOT_ALLOWED"):
        retrieve_plan(plan, tmp_path, transport=transport, sleeper=lambda _: None)


def test_expected_hash_mismatch_does_not_publish(tmp_path):
    plan = {"allowed_hosts": ["data.example.org"], "request_cap": 3, "max_object_bytes": 100,
            "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                         "expected_size": None, "expected_sha256": "0" * 64, "max_bytes": 100}]}
    def transport(url, headers):
        return {"status": 200, "headers": {}, "body": b"x", "final_url": url, "redirect_chain": [url]}
    with pytest.raises(RetrievalError, match="HASH_MISMATCH"):
        retrieve_plan(plan, tmp_path, transport=transport, sleeper=lambda _: None)
    assert not (tmp_path / "MANIFEST.json").exists()
    assert not list((tmp_path / "objects").glob("*")) if (tmp_path / "objects").exists() else True


def test_redirect_hops_are_counted_and_spaced_as_individual_requests(tmp_path):
    body = b"ok"
    plan = {"allowed_hosts": ["data.example.org", "mirror.example.org"], "request_cap": 3, "max_object_bytes": 20,
            "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                         "expected_size": 2, "expected_sha256": hashlib.sha256(body).hexdigest(),
                         "max_bytes": 20}]}
    now = [0.0]
    gaps = []
    calls = []
    def clock():
        return now[0]
    def sleep(delay):
        gaps.append(delay)
        now[0] += delay
    def transport(url, headers):
        calls.append(url)
        if url == "https://data.example.org/file":
            return {"status": 302, "headers": {"Location": "https://mirror.example.org/file"},
                    "body": b"", "final_url": url, "redirect_chain": [url]}
        return {"status": 200, "headers": {"Content-Length": "2"}, "body": body,
                "final_url": url, "redirect_chain": [url]}
    result = retrieve_plan(plan, tmp_path, transport=transport, clock=clock, sleeper=sleep)
    assert calls == ["https://data.example.org/file", "https://mirror.example.org/file"]
    assert result["request_count"] == 2
    assert gaps == [0.5]


def test_interrupted_download_resumes_only_at_validated_range(tmp_path):
    body = b"source bytes"
    digest = hashlib.sha256(body).hexdigest()
    plan = {"allowed_hosts": ["data.example.org"], "request_cap": 3, "max_object_bytes": 100,
            "objects": [{"id": "sample", "url": "https://data.example.org/file", "version": "v1",
                         "expected_size": len(body), "expected_sha256": digest, "max_bytes": 100}]}
    calls = []
    def transport(url, headers):
        calls.append(dict(headers))
        if len(calls) == 1:
            return {"status": 200, "headers": {"Content-Length": str(len(body)), "ETag": "v1"},
                    "body": body[:8], "interrupted": True, "final_url": url, "redirect_chain": [url]}
        return {"status": 206, "headers": {"Content-Length": str(len(body) - 8), "ETag": "v1",
                "Content-Range": f"bytes 8-{len(body)-1}/{len(body)}"}, "body": body[8:],
                "final_url": url, "redirect_chain": [url]}
    result = retrieve_plan(plan, tmp_path, transport=transport, sleeper=lambda delay: None)
    assert calls[1] == {"Range": "bytes=8-", "If-Range": "v1"}
    assert result["request_count"] == 2
    assert (tmp_path / "objects" / digest).read_bytes() == body
