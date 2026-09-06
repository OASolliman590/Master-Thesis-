"""Offline regression checks for cached retrieval provenance.

The historical helper is exercised through a temporary path substitution so the
pre-fix failure is reproducible without touching the original cache. The fixed
helper is exercised through its public CLI. No test permits a network request.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).with_name("retrieve.py")
TEMP_PARENT = Path(__file__).parent
BODY_NAME = "TCGA_mastercalls.abs_tables_JSedit.fixed.txt"
OLD_TIMESTAMP = "2026-09-05T23:31:00+00:00"
URL = "https://invalid.example.test/no-network"


def make_cache(root: Path) -> tuple[Path, str]:
    body = b"synthetic cached source body\n"
    digest = hashlib.sha256(body).hexdigest()
    (root / BODY_NAME).write_bytes(body)
    receipt_path = root / "retrieval.json"
    receipt_path.write_text(
        json.dumps(
            {
                "url": URL,
                "source_page": "https://invalid.example.test/source",
                "bytes": len(body),
                "sha256": digest,
                "retrieved_utc": OLD_TIMESTAMP,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt_path, digest


class CachedRetrievalProvenanceTest(unittest.TestCase):
    def run_fixed_helper(self, root: Path, expected_sha256: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "--output-dir",
                str(root),
                "--url",
                URL,
                "--expected-sha256",
                expected_sha256,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_cache_reuse_preserves_retrieval_time(self) -> None:
        with tempfile.TemporaryDirectory(prefix="b-tcga-cache-", dir=TEMP_PARENT) as tmp:
            root = Path(tmp)
            receipt_path, digest = make_cache(root)
            source = HELPER.read_text(encoding="utf-8")
            if "--output-dir" in source:
                run = self.run_fixed_helper(root, digest)
                self.assertEqual(run.returncode, 0, run.stderr)
            else:
                old_root = (
                    "out=Path(r'E:\\Master_Thesis\\planning\\next_evidence"
                    "\\B_TCGA_cellularity')"
                )
                replacement = f"out=Path({str(root)!r})"
                self.assertIn(old_root, source)
                isolated_source = source.replace(old_root, replacement, 1)
                exec(compile(isolated_source, str(HELPER), "exec"), {"__name__": "__main__"})

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["retrieved_utc"], OLD_TIMESTAMP)
            self.assertIn("verified_utc", receipt)

    def test_expected_digest_mismatch_fails_without_rewriting_receipt(self) -> None:
        source = HELPER.read_text(encoding="utf-8")
        if "--output-dir" not in source:
            self.skipTest("fixed isolated-cache CLI not implemented yet")
        with tempfile.TemporaryDirectory(prefix="b-tcga-cache-", dir=TEMP_PARENT) as tmp:
            root = Path(tmp)
            receipt_path, _ = make_cache(root)
            before = receipt_path.read_bytes()
            run = self.run_fixed_helper(root, "0" * 64)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(receipt_path.read_bytes(), before)

    def test_receipt_digest_mismatch_fails_without_rewriting_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="b-tcga-cache-", dir=TEMP_PARENT) as tmp:
            root = Path(tmp)
            receipt_path, digest = make_cache(root)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["sha256"] = "f" * 64
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            before = receipt_path.read_bytes()
            run = self.run_fixed_helper(root, digest)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(receipt_path.read_bytes(), before)

    def test_cached_body_without_receipt_fails_without_network(self) -> None:
        with tempfile.TemporaryDirectory(prefix="b-tcga-cache-", dir=TEMP_PARENT) as tmp:
            root = Path(tmp)
            receipt_path, digest = make_cache(root)
            receipt_path.unlink()
            body_before = (root / BODY_NAME).read_bytes()
            run = self.run_fixed_helper(root, digest)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(receipt_path.exists())
            self.assertEqual((root / BODY_NAME).read_bytes(), body_before)


if __name__ == "__main__":
    unittest.main()
