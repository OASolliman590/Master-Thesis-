"""Real-source audit: local evidence only, no scores or synthetic substitution."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from tools.b_acquire.audit import audit_sources


def _tmp() -> Path:
    explicit = os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else REPO / "tmp" / "paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_audit_", dir=root))


class TestSourceAudit(unittest.TestCase):
    def test_audit_reports_confirmed_and_missing_without_scoring(self) -> None:
        root = _tmp()
        evidence = root / "evidence.txt"
        evidence.write_bytes(b"patient-free synthetic source evidence\n")
        stale = root / "stale.md"
        stale.write_bytes(b"changed\n")
        manifest = {
            "retrieved_objects": [
                {
                    "source_file": "evidence.txt",
                    "exact_url": "https://example.invalid/public-metadata",
                    "access": "public",
                    "completeness": "synthetic-test-evidence",
                    "byte_count": evidence.stat().st_size,
                    "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                }
            ],
            "coverage": {
                "full_external_expression_audit": {
                    "matrix_retained": False,
                    "complete_object_sha256": "0" * 64,
                    "complete_object_bytes": 123,
                }
            },
            "local_evidence_snapshots": [
                {"path": "stale.md", "role": "synthetic stale snapshot", "bytes": 999, "sha256": "1" * 64}
            ],
        }
        manifest_path = root / "source_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        output = root / "audit.json"
        payload = audit_sources(
            repo_root=root,
            manifest_path=manifest_path,
            output_path=output,
            network="none",
        )
        self.assertTrue(output.is_file())
        self.assertFalse(payload["computes_scores"])
        self.assertFalse(payload["fits_models"])
        self.assertGreater(payload["counts"]["confirmed"], 0)
        self.assertGreaterEqual(payload["counts"]["missing"], 1)
        self.assertEqual(payload["counts"]["mismatch"], 1)
        notes = " ".join(str(item.get("note") or "") for item in payload["missing_files"])
        self.assertIn("not retained", notes.lower())
        self.assertTrue(payload["unresolved_specimen_annotation_purity_policies"])
        for item in payload["confirmed_source_evidence"] + payload["missing_files"]:
            self.assertFalse(item.get("synthetic_substitute"))
        dumped = json.dumps(payload)
        self.assertNotIn("delta_r2", dumped.lower())
        self.assertNotIn("\"Y\":", dumped)


if __name__ == "__main__":
    unittest.main()
