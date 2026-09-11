"""W7 traceability, scope labels, determinism and tamper tests."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tools.b_report.report import FIGURE_FILES, SYNTHETIC_LABEL, _build_flow_rows, run_report
from tools.b_workflow.io import PipelineFailure, code_identity_sha256, sha256_file
from tools.b_workflow.run import run_workflow, verify_complete_stage
from tools.b_workflow.stages import CODE_PATHS

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs" / "B" / "workflow.synthetic.json"
IDENTITY = code_identity_sha256(REPO, CODE_PATHS)


def _tmp() -> Path:
    explicit = os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else REPO / "tmp" / "paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_w7_", dir=root))


class TestReportW7(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = _tmp() / "connected"
        run_workflow(
            config_path=CONFIG,
            run_dir=cls.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W7",
            resume=False,
        )

    def test_four_figures_are_real_traceable_synthetic_artifacts(self) -> None:
        w7 = self.run_dir / "W7"
        ok, reason = verify_complete_stage(self.run_dir, "W7")
        self.assertTrue(ok, reason)
        trace = json.loads((w7 / "traceability.json").read_text(encoding="utf-8"))
        self.assertEqual(set(trace["figure_sources"]), set(FIGURE_FILES))
        for figure, tables in trace["figure_sources"].items():
            svg = (w7 / figure).read_text(encoding="utf-8")
            self.assertIn("<svg", svg)
            self.assertIn("SYNTHETIC FIXTURE ONLY", svg)
            self.assertGreater(len(svg), 500)
            for table in tables:
                self.assertTrue((w7 / table).is_file())
                self.assertEqual(sha256_file(w7 / table), trace["source_table_hashes"][table])

    def test_w3_exclusions_are_retained_with_patient_and_specimen_units(self) -> None:
        coverage = [{
            "patient_id": "P1",
            "cohort": "DEV-SYN",
            "expression_gene_count": "5",
            "methylation_probe_count": "7",
        }]
        w3_exclusions = [{
            "patient_id": "P2",
            "specimen_id": "S2",
            "assay_id": "A2",
            "cohort": "EXT-SYN",
            "modality": "methylation",
            "exclusion_reason": "ambiguous-focus",
        }]
        rows, bars = _build_flow_rows(
            coverage,
            [{"patient_id": "P1"}],
            [],
            [],
            w3_exclusions,
        )
        self.assertEqual(rows[1][0:4], ["excluded-specimen", "P2", "S2", "A2"])
        counts = {label: value for label, value, _ in bars}
        self.assertEqual(counts["W3-excluded patients (unique)"], 1)
        self.assertEqual(counts["W3-excluded specimen/assay rows"], 1)

    def test_report_is_explicitly_partial_and_preserves_metrics(self) -> None:
        w7 = self.run_dir / "W7"
        report = json.loads((w7 / "report.json").read_text(encoding="utf-8"))
        w6 = json.loads((self.run_dir / "W6" / "evaluation.json").read_text(encoding="utf-8"))
        self.assertEqual(report["scope_status"], "partial-apm-component")
        self.assertFalse(report["broader_immune_barrier_framework_complete"])
        self.assertIn("pending", report["methylcibersort_status"])
        self.assertEqual(report["metrics"]["external_delta_r2"], w6["metrics"]["delta_r2"])
        metrics_row = (w7 / "tables" / "figure_4_external_metrics.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")
        self.assertEqual(float(metrics_row[4]), w6["metrics"]["r2_baseline"])
        self.assertLess(float(metrics_row[4]), 0.0)
        markdown = (w7 / "report.md").read_text(encoding="utf-8")
        self.assertIn(SYNTHETIC_LABEL, markdown)
        self.assertIn("not implemented", markdown.lower())
        self.assertIn("does not validate CPC-GENE biology", markdown)
        self.assertIn("[Open SVG](figures/figure_4_external_validation.svg)", markdown)
        self.assertIn("paired-patient bootstrap", markdown)

    def test_report_payloads_are_deterministic(self) -> None:
        destinations = [_tmp() / "report-a", _tmp() / "report-b"]
        for destination in destinations:
            run_report(
                w3_dir=self.run_dir / "W3",
                w5_dir=self.run_dir / "W5",
                w6_dir=self.run_dir / "W6",
                stage_dir=destination,
                parent_hashes={"fixture": "same"},
                code_identity=IDENTITY,
                interpreter=sys.executable,
            )
        comparable = [*FIGURE_FILES, "report.json", "report.md", "traceability.json"]
        comparable.extend(sorted(path.relative_to(destinations[0]).as_posix() for path in (destinations[0] / "tables").glob("*.tsv")))
        for rel in comparable:
            self.assertEqual((destinations[0] / rel).read_bytes(), (destinations[1] / rel).read_bytes(), rel)

    def test_parent_tamper_blocks_report(self) -> None:
        w6_copy = _tmp() / "W6"
        shutil.copytree(self.run_dir / "W6", w6_copy)
        predictions = w6_copy / "predictions.tsv"
        predictions.write_bytes(predictions.read_bytes() + b"\n")
        with self.assertRaises(PipelineFailure) as ctx:
            run_report(
                w3_dir=self.run_dir / "W3",
                w5_dir=self.run_dir / "W5",
                w6_dir=w6_copy,
                stage_dir=_tmp() / "blocked",
                parent_hashes={},
                code_identity=IDENTITY,
                interpreter=sys.executable,
            )
        self.assertIn("parent-publication-invalid", str(ctx.exception))
        self.assertIn("artifact-hash-mismatch:predictions.tsv", str(ctx.exception))

    def test_resume_skips_w7(self) -> None:
        status = run_workflow(
            config_path=CONFIG,
            run_dir=self.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W7",
            resume=True,
        )
        self.assertEqual(status["executed"], [])
        self.assertEqual(status["skipped"], ["W1", "W2", "W3", "W4", "W5", "W6", "W7"])


if __name__ == "__main__":
    unittest.main()
