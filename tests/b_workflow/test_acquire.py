"""W2 acquisition tests: local files and loopback HTTP. No live network."""

from __future__ import annotations

import gzip
import hashlib
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.b_acquire.acquire import acquire_source
from tools.b_workflow.io import PipelineFailure

REPO = Path(__file__).resolve().parents[2]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tmp() -> Path:
    explicit = os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    return Path(explicit) if explicit else Path(tempfile.gettempdir())


class _Server:
    def __init__(self, routes: dict[str, tuple[int, dict[str, str], bytes, bool]]):
        self.routes = routes
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A003
                return

            def do_GET(self):  # noqa: N802
                spec = parent.routes.get(self.path)
                if spec is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                status, headers, body, interrupt = spec
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                if "Content-Length" not in headers:
                    self.send_header("Content-Length", str(len(body) if not interrupt else 1000))
                self.end_headers()
                if interrupt:
                    self.wfile.write(body[: max(1, len(body) // 4)])
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def origin(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


class TestAcquire(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="b_w2_", dir=_tmp()))
        self.cache = self.tmp / "cache"
        self.work = self.tmp / "work"
        self.cache.mkdir()
        self.work.mkdir()

    def _source(self, **kwargs):
        base = {
            "source_id": "syn.http.test",
            "accession": "SYNTHETIC-HTTP",
            "exact_url": "http://127.0.0.1/unused",
            "access_tier": "synthetic-fixture",
            "expected_sha256": "0" * 64,
            "expected_size": 1,
            "compression": "none",
            "role": "fixture",
            "format": "tcga-methylation-beta",
            "completeness": "full",
            "object_name": "payload.bin",
        }
        base.update(kwargs)
        return base

    def test_file_success(self) -> None:
        src = REPO / "specs" / "B" / "synthetic" / "raw" / "tcga_meth_TCGA-0001.tsv"
        data = src.read_bytes()
        receipt = acquire_source(
            self._source(
                source_id="syn.file.ok",
                exact_url="file:specs/B/synthetic/raw/tcga_meth_TCGA-0001.tsv",
                expected_sha256=_sha(data),
                expected_size=len(data),
                object_name=src.name,
            ),
            repo_root=REPO,
            cache_dir=self.cache,
            work_dir=self.work,
        )
        self.assertTrue(receipt["synthetic"])
        self.assertEqual(receipt["checksum_value"], _sha(data))
        self.assertEqual((self.cache / "syn.file.ok" / "payload").read_bytes(), data)

    def test_http_success_html_interrupt_checksum(self) -> None:
        ok = b"synthetic-ok-bytes\n"
        html = b"<!DOCTYPE html><html><body>not data</body></html>"
        other = b"wrong-checksum-bytes\n"
        server = _Server(
            {
                "/ok": (200, {"Content-Type": "application/octet-stream"}, ok, False),
                "/html": (200, {"Content-Type": "text/html"}, html, False),
                "/partial": (200, {"Content-Type": "application/octet-stream"}, ok, True),
                "/mismatch": (200, {"Content-Type": "application/octet-stream"}, other, False),
            }
        )
        self.addCleanup(server.close)
        receipt = acquire_source(
            self._source(
                source_id="syn.http.ok",
                exact_url=f"{server.origin}/ok",
                expected_sha256=_sha(ok),
                expected_size=len(ok),
            ),
            repo_root=REPO,
            cache_dir=self.cache,
            work_dir=self.work,
        )
        self.assertEqual(receipt["checksum_value"], _sha(ok))
        with self.assertRaises(PipelineFailure) as html_exc:
            acquire_source(
                self._source(
                    source_id="syn.http.html",
                    exact_url=f"{server.origin}/html",
                    expected_sha256=_sha(html),
                    expected_size=len(html),
                ),
                repo_root=REPO,
                cache_dir=self.cache,
                work_dir=self.work,
            )
        self.assertIn("html-or-error-body-rejected", str(html_exc.exception))
        self.assertFalse((self.cache / "syn.http.html" / "payload").exists())
        with self.assertRaises(PipelineFailure) as part_exc:
            acquire_source(
                self._source(
                    source_id="syn.http.partial",
                    exact_url=f"{server.origin}/partial",
                    expected_sha256=_sha(ok),
                    expected_size=len(ok),
                ),
                repo_root=REPO,
                cache_dir=self.cache,
                work_dir=self.work,
            )
        self.assertTrue(
            "interrupted" in str(part_exc.exception) or "size-mismatch" in str(part_exc.exception)
        )
        self.assertFalse((self.cache / "syn.http.partial" / "payload").exists())
        with self.assertRaises(PipelineFailure) as sum_exc:
            acquire_source(
                self._source(
                    source_id="syn.http.mismatch",
                    exact_url=f"{server.origin}/mismatch",
                    expected_sha256=_sha(ok),
                    expected_size=len(other),
                ),
                repo_root=REPO,
                cache_dir=self.cache,
                work_dir=self.work,
            )
        self.assertIn("checksum-mismatch", str(sum_exc.exception))
        self.assertFalse((self.cache / "syn.http.mismatch" / "payload").exists())

    def test_non_loopback_http_forbidden(self) -> None:
        with self.assertRaises(PipelineFailure) as ctx:
            acquire_source(
                self._source(exact_url="https://ftp.ncbi.nlm.nih.gov/geo/nothing"),
                repo_root=REPO,
                cache_dir=self.cache,
                work_dir=self.work,
            )
        self.assertIn("non-loopback-http-forbidden", str(ctx.exception))

    def test_object_name_substitution_rejected(self) -> None:
        src = REPO / "specs" / "B" / "synthetic" / "raw" / "tcga_meth_TCGA-0001.tsv"
        data = src.read_bytes()
        with self.assertRaises(PipelineFailure) as ctx:
            acquire_source(
                self._source(
                    source_id="syn.file.sub",
                    exact_url="file:specs/B/synthetic/raw/tcga_meth_TCGA-0001.tsv",
                    expected_sha256=_sha(data),
                    expected_size=len(data),
                    object_name="GSE999999_other.tsv",
                    accession="GSE107299",
                ),
                repo_root=REPO,
                cache_dir=self.cache,
                work_dir=self.work,
            )
        self.assertIn("silent-accession-substitution", str(ctx.exception))

    def test_gzip_compressed_and_decompressed_hashes(self) -> None:
        inner = b"cgA1\t0.2\ncgA2\tNA\n"
        gz_path = self.tmp / "tiny.tsv.gz"
        with gzip.open(gz_path, "wb") as handle:
            handle.write(inner)
        compressed = gz_path.read_bytes()
        receipt = acquire_source(
            self._source(
                source_id="syn.gz",
                exact_url=f"file:{gz_path.as_posix()}",
                expected_sha256=_sha(compressed),
                expected_size=len(compressed),
                compression="gzip",
                expected_decompressed_sha256=_sha(inner),
                object_name="tiny.tsv.gz",
            ),
            repo_root=REPO,
            cache_dir=self.cache,
            work_dir=self.work,
        )
        self.assertEqual(receipt["compressed_sha256"], _sha(compressed))
        self.assertEqual(receipt["decompressed_sha256"], _sha(inner))
        self.assertEqual((self.cache / "syn.gz" / "payload").read_bytes(), inner)


if __name__ == "__main__":
    unittest.main()
