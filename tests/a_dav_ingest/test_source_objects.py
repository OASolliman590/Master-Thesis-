import gzip
import hashlib
import json
from pathlib import Path

import pytest

from tools.a_dav.geo_soft import parse_geo_family_soft
from tools.a_dav.source_objects import ContentAddressedStore, SourceObjectError

FIXTURES = Path(__file__).parent / "fixtures"


def test_geo_family_soft_parses_gzipped_sample_blocks_and_repeated_attributes():
    compressed = gzip.compress((FIXTURES / "geo_family_excerpt.soft").read_bytes(), mtime=0)
    samples = parse_geo_family_soft(compressed)
    assert [sample["accession"] for sample in samples] == [
        "GSMTEST001", "GSMTEST002", "GSMTEST003"]
    assert samples[0]["title"] == "Subject01_Pre_A001-1"
    assert samples[0]["characteristics"] == [
        {"key": "visit (pre or on treatment)", "value": "Pre"},
        {"key": "response", "value": "PD"},
    ]
    assert [relation["kind"] for relation in samples[0]["relations"]] == ["BioSample", "SRA"]
    assert samples[0]["geo_accession"] == "GSMTEST001"


def test_content_addressed_store_reads_by_sha_and_returns_manifest_provenance(tmp_path):
    raw = b"private source object bytes"
    sha = hashlib.sha256(raw).hexdigest()
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / sha).write_bytes(raw)
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"objects": {
        sha: {"locator": "https://example.invalid/object", "version": "v1",
             "byte_size": len(raw), "retrieved_at": "2026-10-25T00:00:00Z"}}}))

    source = ContentAddressedStore(tmp_path).read(sha)
    assert source.bytes == raw
    assert source.sha256 == sha
    assert source.locator == "https://example.invalid/object"
    assert source.version == "v1"
    assert source.byte_size == len(raw)
    assert source.retrieved_at == "2026-10-25T00:00:00Z"


def test_content_addressed_store_verifies_full_hash_before_returning_bytes(tmp_path):
    expected = hashlib.sha256(b"expected").hexdigest()
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / expected).write_bytes(b"changed")
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"objects": {
        expected: {"locator": "local-only", "version": "v1", "byte_size": 7,
                   "retrieved_at": "2026-10-25T00:00:00Z"}}}))
    with pytest.raises(SourceObjectError, match="SOURCE_HASH_MISMATCH"):
        ContentAddressedStore(tmp_path).read(expected)


def test_content_addressed_store_accepts_retrieval_receipt_metadata(tmp_path):
    raw = b"receipt compatible bytes"
    sha = hashlib.sha256(raw).hexdigest()
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / sha).write_bytes(raw)
    receipt = {"http_status": 200, "final_url": "https://example.invalid/object",
               "redirect_chain": ["https://example.invalid/object"],
               "headers": {"content-length": str(len(raw))}, "complete_sha256": sha,
               "attempts": 1}
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"objects": {
        sha: {"locator": "https://example.invalid/object", "version": "v1",
             "byte_size": len(raw), "retrieved_at": "2026-10-25T00:00:00Z",
             "receipt": receipt}}}))
    source = ContentAddressedStore(tmp_path).read(sha)
    assert source.sha256 == sha
    assert source.byte_size == len(raw)
    assert source.receipt == receipt
