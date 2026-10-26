"""Single allowlisted source-object retrieval path for A-DAV."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, NoReturn
from urllib.parse import urlsplit


class RetrievalError(ValueError):
    """A fetch plan, HTTP response, or published object failed policy."""


def _fail(code: str, message: str) -> NoReturn:
    raise RetrievalError(f"{code}: {message}")


def build_locator(adapter: str, **values: str) -> str:
    """Build a locator for a pinned repository object without doing I/O."""
    if adapter == "geo":
        path = values.get("path", "")
        return "https://ftp.ncbi.nlm.nih.gov/geo/" + path.lstrip("/")
    if adapter == "ena_filereport":
        accession = values.get("accession", "")
        fields = values.get("fields", "")
        if not accession or not fields:
            _fail("LOCATOR_INVALID", "ENA requires accession and explicit fields")
        return ("https://www.ebi.ac.uk/ena/portal/api/filereport?accession="
                + accession + "&result=read_run&fields=" + fields + "&format=tsv")
    if adapter == "github_raw":
        repo, commit, path = (values.get(k, "") for k in ("repo", "commit", "path"))
        if not repo or re.fullmatch(r"[a-f0-9]{40}", commit) is None or not path:
            _fail("LOCATOR_INVALID", "GitHub raw locator requires repository, pinned commit, and path")
        return f"https://raw.githubusercontent.com/{repo}/{commit}/{path.lstrip('/')}"
    if adapter == "cbioportal_lfs":
        repo, commit, path = (values.get(k, "") for k in ("repo", "commit", "path"))
        if not repo or not commit or not path:
            _fail("LOCATOR_INVALID", "cBioPortal LFS locator requires repository, commit, and path")
        return f"https://media.githubusercontent.com/media/{repo}/{commit}/{path.lstrip('/')}"
    _fail("LOCATOR_INVALID", "unknown repository adapter")


def _validate_url(url: str, allowed_hosts: set[str] | list[str]) -> str:
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        _fail("URL_INVALID", "malformed URL")
    if parts.scheme != "https" or host not in allowed_hosts or parts.username or parts.password:
        _fail("HOST_OR_SCHEME_NOT_ALLOWED", "URL must use HTTPS and an allowlisted host")
    if parts.fragment:
        _fail("URL_INVALID", "URL fragments are forbidden")
    return host or ""


def load_plan(plan: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(plan, dict):
        value = plan
    else:
        try:
            value = json.loads(Path(plan).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            _fail("PLAN_INVALID", "could not read fetch plan")
    if not isinstance(value, dict):
        _fail("PLAN_INVALID", "fetch plan must be an object")
    hosts_value = value.get("allowed_hosts")
    objects_value = value.get("objects")
    cap = value.get("request_cap")
    max_object_bytes = value.get("max_object_bytes")
    if (not isinstance(hosts_value, list) or not hosts_value
            or any(not isinstance(host, str) for host in hosts_value)):
        _fail("PLAN_INVALID", "fetch plan host allowlist is invalid")
    if not isinstance(objects_value, list) or not objects_value:
        _fail("PLAN_INVALID", "fetch plan object list is invalid")
    if type(max_object_bytes) is not int or max_object_bytes <= 0:
        _fail("PLAN_INVALID", "fetch plan max_object_bytes must be a positive integer")
    if type(cap) is not int or cap < len(objects_value) or cap > 200:
        _fail("PLAN_INVALID", "fetch plan request cap is invalid")
    hosts: list[str] = hosts_value
    objects: list[dict[str, Any]] = objects_value
    seen: set[str] = set()
    for item in objects:
        if not isinstance(item, dict):
            _fail("PLAN_INVALID", "object entry must be an object")
        ident, url, version = item.get("id"), item.get("url"), item.get("version")
        if not isinstance(ident, str) or not ident or ident in seen:
            _fail("PLAN_INVALID", "object IDs must be nonempty and unique")
        seen.add(ident)
        if not isinstance(url, str) or not isinstance(version, str) or not version:
            _fail("PLAN_INVALID", "object URL and version are required")
        host = _validate_url(url, hosts)
        if item.get("host", host) != host:
            _fail("PLAN_INVALID", "declared object host does not match URL")
        for field in ("expected_size", "max_bytes"):
            if item.get(field) is not None and (type(item[field]) is not int or item[field] < 0):
                _fail("PLAN_INVALID", f"{field} must be a nonnegative integer or null")
        digest = item.get("expected_sha256")
        if digest is not None and (not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None):
            _fail("PLAN_INVALID", "expected_sha256 must be lowercase SHA-256 or null")
        if type(item.get("max_bytes")) is not int or item["max_bytes"] <= 0:
            _fail("PLAN_INVALID", "every object needs a positive max_bytes bound")
    if len(objects) * 3 > cap:
        _fail("REQUEST_CAP_EXCEEDED", "request cap must cover up to three attempts per object")
    return value


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        return None


def _urllib_transport(url: str, headers: dict[str, str], *, allowed_hosts: set[str] | list[str], max_bytes: int) -> dict[str, Any]:
    _validate_url(url, allowed_hosts)
    request = urllib.request.Request(url, headers=headers, method="GET")
    opener = urllib.request.build_opener(_NoRedirects())
    try:
        response = opener.open(request, timeout=60)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        status = int(response.status)
        response_headers = dict(response.headers.items())
        if 300 <= status < 400:
            return {"status": status, "headers": response_headers, "body": b"",
                    "final_url": url, "redirect_chain": [url]}
        chunks: list[bytes] = []
        byte_count = 0
        interrupted = False
        try:
            while chunk := response.read(min(64 * 1024, max_bytes + 1 - byte_count)):
                byte_count += len(chunk)
                if byte_count > max_bytes:
                    _fail("SIZE_OVERRUN", "response exceeded configured object limit")
                chunks.append(chunk)
        except http.client.IncompleteRead as exc:
            chunks.append(exc.partial)
            interrupted = True
        body = b"".join(chunks)
        return {"status": status, "headers": response_headers, "body": body,
                "final_url": url, "redirect_chain": [url], "interrupted": interrupted}

def _now(clock: Callable[[], Any]) -> tuple[float, str]:
    value = clock()
    if isinstance(value, (int, float)):
        return float(value), datetime.fromtimestamp(float(value), timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.timestamp(), parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def retrieve_plan(plan: str | Path | dict[str, Any], store: str | Path, *,
                  transport: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
                  clock: Callable[[], Any] = time.time, sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    config = load_plan(plan)
    allowed_hosts = config["allowed_hosts"]
    http = transport
    root = Path(store)
    objects_dir = root / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "MANIFEST.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _fail("STORE_MANIFEST_INVALID", "existing manifest is unreadable")
        if not isinstance(manifest, dict) or set(manifest) != {"objects"} or not isinstance(manifest["objects"], dict):
            _fail("STORE_MANIFEST_INVALID", "existing manifest has an unsupported shape")
    else:
        manifest = {"objects": {}}
    request_count = 0
    last_request_at: float | None = None
    retrieved = 0
    for item in config["objects"]:
        object_request_start = request_count
        url = item["url"]
        partial = root / ".partial" / f"{item['id']}.part"
        partial.parent.mkdir(parents=True, exist_ok=True)
        body = b""
        headers: dict[str, str] = {}
        prior_etag = None
        if partial.exists():
            body = partial.read_bytes()
            meta_path = partial.with_suffix(".json")
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                valid = (metadata.get("prefix_sha256") == hashlib.sha256(body).hexdigest()
                         and metadata.get("url") == url and isinstance(metadata.get("etag"), str)
                         and int(metadata.get("total_size", -1)) > len(body))
            except (OSError, ValueError, AttributeError, json.JSONDecodeError):
                valid = False
            if valid:
                prior_etag = metadata["etag"]
                headers = {"Range": f"bytes={len(body)}-", "If-Range": prior_etag}
            else:
                partial.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                body = b""
        attempt = 0
        response: dict[str, Any] | None = None
        redirect_chain = [url]
        while attempt < 3:
            current_url = redirect_chain[-1]
            redirect_count = 0
            while True:
                if request_count >= config["request_cap"]:
                    _fail("REQUEST_CAP_EXCEEDED", "plan exhausted its HTTP request cap")
                now, _ = _now(clock)
                if last_request_at is not None and now - last_request_at < 0.5:
                    delay = 0.5 - (now - last_request_at)
                    sleeper(delay)
                    now, _ = _now(clock)
                last_request_at = now
                request_count += 1
                try:
                    response = (_urllib_transport(current_url, headers, allowed_hosts=allowed_hosts,
                max_bytes=min(item["max_bytes"], config["max_object_bytes"]))
                                if http is None else http(current_url, headers))
                except urllib.error.URLError as exc:
                    if not isinstance(exc.reason, (TimeoutError, socket.timeout)):
                        _fail("HTTP_FAILURE", "request failed with a non-timeout transport error")
                    response = None
                    break
                except (TimeoutError, socket.timeout):
                    response = None
                    break
                status = int(response.get("status", 0))
                if 300 <= status < 400:
                    location = next((str(v) for k, v in response.get("headers", {}).items()
                                     if str(k).lower() == "location"), "")
                    if not location:
                        _fail("REDIRECT_INVALID", "redirect response has no Location")
                    from urllib.parse import urljoin
                    next_url = urljoin(current_url, location)
                    _validate_url(next_url, allowed_hosts)
                    redirect_count += 1
                    if redirect_count > 10:
                        _fail("REDIRECT_INVALID", "redirect limit exceeded")
                    redirect_chain.append(next_url)
                    current_url = next_url
                    continue
                break
            if response is None:
                if attempt == 2:
                    _fail("RETRY_EXHAUSTED", "request timed out after three attempts")
                attempt += 1
                sleeper(0.5 * (2 ** attempt))
                continue
            status = int(response.get("status", 0))
            if status == 429 or 500 <= status <= 599:
                if attempt == 2:
                    _fail("RETRY_EXHAUSTED", f"server returned retryable HTTP status {status}")
                attempt += 1
                sleeper(0.5 * (2 ** attempt))
                continue
            response_chain = response.get("redirect_chain", [current_url])
            if response_chain != [current_url]:
                _fail("REDIRECT_INVALID", "transport followed redirects outside the request budget")
            final_url = response.get("final_url", current_url)
            _validate_url(final_url, allowed_hosts)
            if final_url != current_url:
                _fail("REDIRECT_INVALID", "transport final URL differs from the requested hop")
            if status == 206:
                response_headers_lower = {str(k).lower(): str(v) for k, v in response.get("headers", {}).items()}
                content_range = response_headers_lower.get("content-range", "")
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
                chunk = response.get("body", b"")
                response_etag = response_headers_lower.get("etag")
                if match is None:
                    _fail("RANGE_INVALID", "resumed response did not include a valid byte range")
                if (not headers or int(match.group(1)) != len(body)
                        or int(match.group(2)) - int(match.group(1)) + 1 != len(chunk)
                        or int(match.group(3)) <= int(match.group(2))
                        or (prior_etag is not None and response_etag != prior_etag)):
                    headers = {}
                    body = b""
                    if attempt < 2:
                        attempt += 1
                        sleeper(0.5)
                        continue
                    _fail("RANGE_INVALID", "resumed response did not match requested byte range")
                body += chunk
                if response_headers_lower.get("content-length", "").isdigit() and int(response_headers_lower["content-length"]) != len(chunk):
                    _fail("CONTENT_LENGTH_MISMATCH", "resumed response length did not match Content-Length")
                total_size = int(match.group(3))
                if int(match.group(2)) + 1 < total_size:
                    if response_etag and attempt < 2:
                        partial.write_bytes(body)
                        partial.with_suffix(".json").write_text(json.dumps({"url": url, "etag": response_etag,
                            "total_size": total_size, "prefix_sha256": hashlib.sha256(body).hexdigest()}))
                        prior_etag = response_etag
                        headers = {"Range": f"bytes={len(body)}-", "If-Range": response_etag}
                        attempt += 1
                        sleeper(0.5)
                        continue
                    _fail("BODY_INCOMPLETE", "range response did not reach the declared object end")
            elif status == 200:
                body = response.get("body", b"")
                headers = {}
            else:
                _fail("HTTP_STATUS_INVALID", f"unexpected HTTP status {status}")
            if not isinstance(body, bytes):
                _fail("BODY_INVALID", "HTTP transport body must be bytes")
            if response.get("interrupted"):
                response_headers = {str(k).lower(): str(v) for k, v in response.get("headers", {}).items()}
                etag = response_headers.get("etag")
                total = response_headers.get("content-length")
                if etag and total and total.isdigit() and len(body) < int(total) and attempt < 2:
                    partial.write_bytes(body)
                    meta_path = partial.with_suffix(".json")
                    meta_path.write_text(json.dumps({"url": url, "etag": etag,
                        "total_size": int(total), "prefix_sha256": hashlib.sha256(body).hexdigest()}))
                    prior_etag = etag
                    headers = {"Range": f"bytes={len(body)}-", "If-Range": etag}
                    attempt += 1
                    sleeper(0.5)
                    continue
                _fail("BODY_INCOMPLETE", "response ended before the object was complete")
            break
        redirect_chain[-1] = current_url
        if response is None:
            _fail("HTTP_FAILURE", "request produced no response")
        completed_response: dict[str, Any] = response
        if len(body) > item["max_bytes"] or len(body) > config["max_object_bytes"]:
            _fail("SIZE_OVERRUN", "response exceeded configured object limit")
        response_headers = {str(k).lower(): str(v) for k, v in completed_response.get("headers", {}).items()}
        content_length = response_headers.get("content-length")
        if (int(completed_response.get("status", 0)) == 200 and content_length and content_length.isdigit()
                and len(body) != int(content_length)):
            _fail("CONTENT_LENGTH_MISMATCH", "complete response length did not match Content-Length")
        expected_size = item.get("expected_size")
        if expected_size is not None and len(body) != expected_size:
            _fail("SIZE_MISMATCH", "response length did not match the pinned size")
        digest = hashlib.sha256(body).hexdigest()
        if item.get("expected_sha256") and digest != item["expected_sha256"]:
            _fail("HASH_MISMATCH", "complete response did not match pinned SHA-256")
        content_type = response_headers.get("content-type", "").lower()
        if "text/html" in content_type or body.lstrip()[:20].lower().startswith((b"<!doctype html", b"<html")):
            _fail("HTML_RESPONSE", "repository returned an HTML page instead of the source object")
        if urlsplit(url).path.lower().endswith(".gz") and not body.startswith(b"\x1f\x8b"):
            _fail("CONTENT_SIGNATURE_INVALID", "gzip source object has no gzip signature")
        object_path = objects_dir / digest
        if object_path.exists() and object_path.read_bytes() != body:
            _fail("STORE_COLLISION", "content-addressed destination contains different bytes")
        if not object_path.exists():
            _atomic_write(object_path, body)
        timestamp = _now(clock)[1]
        entry = {"locator": url, "version": item["version"], "byte_size": len(body),
                 "retrieved_at": timestamp,
                 "receipt": {"http_status": int(completed_response.get("status", 0)),
                             "final_url": current_url,
                             "redirect_chain": redirect_chain,
                             "headers": response_headers, "complete_sha256": digest,
                             "attempts": request_count - object_request_start}}
        manifest["objects"][digest] = entry
        _atomic_write(manifest_path, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode())
        partial.unlink(missing_ok=True)
        partial.with_suffix(".json").unlink(missing_ok=True)
        retrieved += 1
    return {"retrieved": retrieved, "request_count": request_count,
            "objects": sorted(manifest["objects"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch allowlisted source objects into a content-addressed store")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--plan", required=True)
    fetch.add_argument("--store", required=True)
    args = parser.parse_args(argv)
    try:
        repository_root = Path(__file__).resolve().parents[2]
        requested_store = Path(args.store).resolve()
        allowed_store = (repository_root / ".scratch" / "runtime").resolve()
        if allowed_store not in requested_store.parents:
            _fail("STORE_PATH_FORBIDDEN", "CLI store must be inside .scratch/runtime")
        result = retrieve_plan(args.plan, requested_store)
    except RetrievalError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
