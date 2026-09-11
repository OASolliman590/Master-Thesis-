"""Immutable source acquisition with validation before publication."""

from __future__ import annotations

import gzip
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse

from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_bytes,
    atomic_write_json,
    canonical_json_bytes,
    looks_like_html,
    sha256_bytes,
    sha256_file,
    utc_stamp,
)

SCHEMA_VERSION = "B-W2-receipt-v1"
MANIFEST_VERSION = "B-W2-manifest-v1"
CHUNK = 1 << 16
GZIP_MAGIC = b"\x1f\x8b"
FORBIDDEN_HOST_SUFFIXES = (".ncbi.nlm.nih.gov", ".cancer.gov", "github.com", "googleapis.com")
CREDENTIAL_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "awsaccesskeyid",
    "credential",
    "credentials",
    "id_token",
    "key",
    "password",
    "passwd",
    "private_key",
    "sas",
    "secret",
    "sig",
    "signature",
    "token",
    "x-amz-security-token",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise PipelineFailure(
            f"stage=W2 reason=redirect-refused from={req.full_url} to={newurl}",
            3,
            "W2",
        )


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(message if message.startswith("stage=") else f"stage=W2 {message}", code, "W2")


def resolve_file_url(url: str, repo_root: Path) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        _fail(f"reason=not-a-file-url url={url}")
    raw_path = unquote(parsed.path or "")
    if parsed.netloc and parsed.netloc not in {"localhost", "127.0.0.1"}:
        raw_path = f"//{parsed.netloc}{raw_path}"
    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    if url.startswith("file:") and not url.startswith("file://"):
        raw_path = url[len("file:") :]
    path = Path(raw_path)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return path


def _reject_credential_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        _fail("reason=credential-bearing-url-rejected")
    for raw_key, _value in parse_qsl(parsed.query, keep_blank_values=True):
        key = raw_key.lower()
        if key in CREDENTIAL_QUERY_KEYS or "token" in key or "secret" in key or "password" in key:
            _fail("reason=credential-bearing-url-rejected")


def _assert_loopback_http(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        _fail(f"reason=non-loopback-http-forbidden host={host}")
    if any(host.endswith(suffix) for suffix in FORBIDDEN_HOST_SUFFIXES):
        _fail(f"reason=live-network-forbidden host={host}")


def _reject_html_or_error(data: bytes, content_type: str | None, status: int | None) -> None:
    if status is not None and status >= 400:
        _fail(f"reason=http-error-body status={status}")
    if looks_like_html(data, content_type):
        _fail("reason=html-or-error-body-rejected")


def _stream_copy(src, dest: Path, expected_size: int | None) -> int:
    written = 0
    with dest.open("wb") as handle:
        while True:
            chunk = src.read(CHUNK)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
            if expected_size is not None and written > expected_size:
                _fail(
                    f"reason=size-exceeds-expected written={written} expected={expected_size}"
                )
        handle.flush()
        os.fsync(handle.fileno())
    return written


def _open_http(url: str, timeout: float):
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, method="GET")
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read(256)
        _reject_html_or_error(body, exc.headers.get("Content-Type") if exc.headers else None, exc.code)
        _fail(f"reason=http-error status={exc.code}")
    except urllib.error.URLError as exc:
        _fail(f"reason=http-interrupted {exc}")


def _acquire_bytes(
    source: dict[str, Any],
    repo_root: Path,
    work_dir: Path,
    timeout: float,
) -> tuple[Path, int, str | None, int | None]:
    url = source["exact_url"]
    _reject_credential_url(url)
    source_id = source["source_id"]
    expected_size = source.get("expected_size")
    part = work_dir / f"{source_id}.part"
    if part.exists():
        part.unlink()
    content_type = None
    status = None
    if url.startswith("file:"):
        path = resolve_file_url(url, repo_root)
        if not path.is_file():
            _fail(f"reason=missing-file path={path}")
        configured_name = source.get("object_name")
        if configured_name and path.name != configured_name:
            _fail(
                f"reason=silent-accession-substitution configured={configured_name} actual={path.name}"
            )
        with path.open("rb") as handle:
            written = _stream_copy(handle, part, expected_size)
        return part, written, content_type, status
    if url.startswith("http://") or url.startswith("https://"):
        _assert_loopback_http(url)
        try:
            with _open_http(url, timeout) as response:
                status = getattr(response, "status", None) or response.getcode()
                content_type = response.headers.get("Content-Type")
                if status != 200:
                    preview = response.read(256)
                    _reject_html_or_error(preview, content_type, status)
                    _fail(f"reason=http-error-body status={status}")
                final_url = response.geturl()
                if final_url != url:
                    _fail(
                        f"reason=silent-accession-substitution configured={url} actual={final_url}"
                    )
                written = _stream_copy(response, part, expected_size)
        except PipelineFailure:
            if part.exists():
                part.unlink()
            raise
        except Exception as exc:
            if part.exists():
                part.unlink()
            _fail(f"reason=http-interrupted {exc}")
        return part, written, content_type, status
    _fail(f"reason=unsupported-url-scheme url={url}")
    raise AssertionError("unreachable")


def _decompress_gzip(compressed_path: Path, dest: Path) -> None:
    try:
        with gzip.open(compressed_path, "rb") as src, dest.open("wb") as handle:
            while True:
                chunk = src.read(CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        _fail(f"reason=gzip-decompress-failed {exc}")


def acquire_source(
    source: dict[str, Any],
    *,
    repo_root: Path,
    cache_dir: Path,
    work_dir: Path,
    timeout: float = 30.0,
) -> dict[str, Any]:
    source_id = source["source_id"]
    expected_sha = str(source["expected_sha256"]).lower()
    expected_size = source["expected_size"]
    if not isinstance(expected_size, int) or expected_size < 0:
        _fail("reason=expected-size-missing")
    compression = source.get("compression", "none")
    part, written, content_type, status = _acquire_bytes(source, repo_root, work_dir, timeout)
    preview = part.read_bytes()[:512]
    _reject_html_or_error(preview, content_type, status)
    if written != expected_size:
        part.unlink(missing_ok=True)
        _fail(f"reason=size-mismatch actual={written} expected={expected_size}")
    compressed_sha = sha256_file(part)
    decompressed_sha = None
    decompressed_size = None
    published_path = cache_dir / source_id / "payload"
    published_path.parent.mkdir(parents=True, exist_ok=True)
    payload_source = part
    if compression == "gzip":
        with part.open("rb") as handle:
            if handle.read(2) != GZIP_MAGIC:
                _fail("reason=gzip-magic-missing")
        if compressed_sha != expected_sha:
            _fail(
                f"reason=checksum-mismatch kind=compressed supplied={expected_sha} actual={compressed_sha}"
            )
        expected_decompressed = source.get("expected_decompressed_sha256")
        if not expected_decompressed:
            _fail("reason=expected-decompressed-sha256-missing")
        expected_decompressed_size = source.get("expected_decompressed_size")
        if not isinstance(expected_decompressed_size, int) or expected_decompressed_size < 1:
            _fail("reason=expected-decompressed-size-missing")
        unzipped = work_dir / f"{source_id}.decompressed"
        _decompress_gzip(part, unzipped)
        decompressed_sha = sha256_file(unzipped)
        decompressed_size = unzipped.stat().st_size
        if decompressed_size != expected_decompressed_size:
            _fail(
                f"reason=decompressed-size-mismatch actual={decompressed_size} expected={expected_decompressed_size}"
            )
        if decompressed_sha.lower() != str(expected_decompressed).lower():
            _fail(
                f"reason=checksum-mismatch kind=decompressed supplied={expected_decompressed} actual={decompressed_sha}"
            )
        payload_source = unzipped
        published_compressed = cache_dir / source_id / "payload.gz"
        os.replace(part, published_compressed)
        part = published_compressed
    elif compression != "none":
        _fail(f"reason=unsupported-compression {compression}")
    actual_sha = sha256_file(payload_source)
    if compression == "none" and actual_sha != expected_sha:
        payload_source.unlink(missing_ok=True)
        _fail(
            f"reason=checksum-mismatch supplied={expected_sha} actual={actual_sha}"
        )
    full_preview = payload_source.read_bytes()[:512]
    _reject_html_or_error(full_preview, content_type, status)
    if published_path.exists():
        _fail(f"reason=cache-path-exists {published_path}")
    os.replace(payload_source, published_path)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a real cohort object.",
        "source_id": source_id,
        "accession": source["accession"],
        "exact_url": source["exact_url"],
        "access_tier": source["access_tier"],
        "role": source["role"],
        "format": source["format"],
        "completeness": source["completeness"],
        "retrieved_utc": utc_stamp(),
        "local_path": str(published_path.as_posix()),
        "byte_count": published_path.stat().st_size,
        "checksum_algorithm": "sha256",
        "checksum_value": sha256_file(published_path),
        "compressed_sha256": compressed_sha if compression == "gzip" else None,
        "decompressed_sha256": decompressed_sha,
        "decompressed_byte_count": decompressed_size,
        "compression": compression,
        "status": "complete",
        "object_name": source.get("object_name"),
    }
    receipt_path = cache_dir / source_id / "receipt.json"
    atomic_write_json(receipt_path, receipt)
    return receipt


def run_acquire(
    sources: list[dict[str, Any]],
    *,
    repo_root: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity_sha256: str,
    interpreter: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        from tools.b_workflow.io import remove_tree

        remove_tree(work)
    cache_dir = work / "cache"
    receipts_dir = work / "receipts"
    cache_dir.mkdir(parents=True)
    receipts_dir.mkdir(parents=True)
    receipts: list[dict[str, Any]] = []
    try:
        for source in sources:
            receipt = acquire_source(
                source,
                repo_root=repo_root,
                cache_dir=cache_dir,
                work_dir=work,
                timeout=timeout,
            )
            receipts.append(receipt)
            atomic_write_json(receipts_dir / f"{source['source_id']}.json", receipt)
        sources_jsonl = "".join(
            canonical_json_bytes(
                {
                    "source_id": r["source_id"],
                    "accession": r["accession"],
                    "exact_url": r["exact_url"],
                    "access_tier": r["access_tier"],
                    "licence_or_terms_url": "synthetic-fixture-only",
                    "cache_relpath": f"cache/{r['source_id']}/payload",
                    "byte_count": r["byte_count"],
                    "checksum_algorithm": "sha256",
                    "checksum_value": r["checksum_value"],
                    "completeness": "full",
                    "role": r["role"],
                    "synthetic": True,
                }
            ).decode("utf-8")
            for r in receipts
        ).encode("utf-8")
        atomic_write_bytes(work / "sources.jsonl", sources_jsonl)
        artifact_hashes = {
            "sources.jsonl": sha256_bytes(sources_jsonl),
            **{f"cache/{r['source_id']}/payload": r["checksum_value"] for r in receipts},
        }
        scientific = {
            "schema_version": MANIFEST_VERSION,
            "stage": "W2",
            "synthetic": True,
            "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a real acquisition.",
            "parent_hashes": parent_hashes,
            "code_identity_sha256": code_identity_sha256,
            "interpreter": interpreter,
            "source_ids": [r["source_id"] for r in receipts],
            "artifact_hashes": artifact_hashes,
        }
        atomic_write_json(work / "checksums.json", scientific)
        manifest = dict(scientific)
        manifest["created_utc"] = utc_stamp()
        manifest["receipts"] = receipts
        atomic_write_json(work / "manifest.json", manifest)
        complete = {
            "stage": "W2",
            "status": "complete",
            "synthetic": True,
            "checksums_sha256": sha256_file(work / "checksums.json"),
            "manifest_sha256": sha256_file(work / "manifest.json"),
            "parent_hashes": parent_hashes,
            "code_identity_sha256": code_identity_sha256,
        }
        atomic_write_json(work / "COMPLETE.json", complete)
    except Exception:
        raise
    from tools.b_workflow.io import publish_directory

    publish_directory(work, stage_dir)
    return json_load(stage_dir / "manifest.json")


def json_load(path: Path) -> dict[str, Any]:
    from tools.b_workflow.io import json_no_dups

    return json_no_dups(path.read_bytes())
