"""W6 frozen external evaluation: no refit, lock, overlap, metric oracles."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tools.b_features.provider import FoldFeatureProvider
from tools.b_prediction.__main__ import _bootstrap_delta
from tools.b_prediction.fold_evaluate import run_fold_evaluate
from tools.b_prediction.w5_bundle import load_w5_bundle
from tools.b_workflow.config import load_config
from tools.b_workflow.io import PipelineFailure, code_identity_sha256, sha256_file
from tools.b_workflow.run import run_workflow, verify_complete_stage
from tools.b_workflow.stages import CODE_PATHS


REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs" / "B" / "workflow.synthetic.json"
PYTHON = sys.executable
IDENTITY = code_identity_sha256(REPO, CODE_PATHS)


def _tmp() -> Path:
    explicit = os.environ.get("BP1_TEST_TMP_ROOT") or os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else REPO / "tmp" / "paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_w6_", dir=root))


class TestFoldEvaluateW6(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = _tmp() / "connected"
        run_workflow(
            config_path=CONFIG,
            run_dir=cls.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W6",
            resume=False,
        )
        cls.config = load_config(CONFIG, repo_root=REPO)
        cls.w5_hashes = {
            rel: sha256_file(cls.run_dir / "W5" / rel)
            for rel in (
                "bundle/checksums.json",
                "bundle/COMPLETE.json",
                "bundle/baseline_model.json",
                "bundle/extended_model.json",
                "bundle/final_feature_state.json",
            )
        }

    def test_original_evaluate_help_unchanged(self) -> None:
        proc = subprocess.run(
            [PYTHON, "-m", "tools.b_prediction", "evaluate", "--help"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--bundle", proc.stdout)
        self.assertIn("--external", proc.stdout)
        self.assertNotIn("--cohort", proc.stdout)

    def test_w6_emits_paired_metrics_and_exclusions(self) -> None:
        w6 = self.run_dir / "W6"
        self.assertTrue((w6 / "COMPLETE.json").is_file())
        evaluation = json.loads((w6 / "evaluation.json").read_text(encoding="utf-8"))
        self.assertTrue(evaluation["synthetic"])
        self.assertFalse(evaluation["used_external_fit"])
        self.assertTrue(evaluation["paired_identical_patient_set"])
        self.assertGreaterEqual(evaluation["n"], 2)
        metrics = evaluation["metrics"]
        self.assertEqual(metrics["status"], "defined")
        sse0, sse1, sst = metrics["sse_baseline"], metrics["sse_extended"], metrics["sst"]
        self.assertAlmostEqual(metrics["delta_r2"], (sse0 - sse1) / sst)
        lock = json.loads((w6 / "evaluation_lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["status"], "synthetic-only")
        self.assertIn("SYNTHETIC", lock["synthetic_label"].upper())
        self.assertEqual(lock["bundle_sha256"], sha256_file(self.run_dir / "W5" / "bundle" / "checksums.json"))
        exclusions = (w6 / "exclusions.tsv").read_text(encoding="utf-8")
        self.assertIn("CPCG0002", exclusions)

    def test_w6_does_not_call_fit(self) -> None:
        def boom(*args, **kwargs):
            raise AssertionError("fit must not run during W6")

        dest = _tmp() / "nofit"
        with patch("sklearn.linear_model.Ridge.fit", boom), patch(
            "sklearn.pipeline.Pipeline.fit", boom
        ), patch("sklearn.model_selection.GridSearchCV.fit", boom), patch(
            "tools.b_features.provider.FoldFeatureProvider.fit", boom
        ):
            run_fold_evaluate(
                self.config,
                repo_root=REPO,
                w3_dir=self.run_dir / "W3",
                w5_dir=self.run_dir / "W5",
                stage_dir=dest,
                parent_hashes={"config": self.config["_config_sha256"]},
                code_identity=IDENTITY,
                interpreter=sys.executable,
            )
        self.assertTrue((dest / "COMPLETE.json").is_file())

    def test_evaluation_lock_is_written_before_external_transform(self) -> None:
        dest = _tmp() / "lock-first"
        with patch.object(FoldFeatureProvider, "transform", side_effect=RuntimeError("stop-before-transform")):
            with self.assertRaisesRegex(RuntimeError, "stop-before-transform"):
                run_fold_evaluate(
                    self.config,
                    repo_root=REPO,
                    w3_dir=self.run_dir / "W3",
                    w5_dir=self.run_dir / "W5",
                    stage_dir=dest,
                    parent_hashes={"config": self.config["_config_sha256"]},
                    code_identity=IDENTITY,
                    interpreter=sys.executable,
                )
        work = dest.parent / f"{dest.name}.work"
        self.assertTrue((work / "evaluation_lock.json").is_file())
        self.assertFalse((work / "evaluation.json").exists())
        self.assertFalse((dest / "COMPLETE.json").exists())

    def test_external_y_change_does_not_change_predictions_or_w5_bytes(self) -> None:
        w3_copy = _tmp() / "w3-y-change"
        shutil.copytree(self.run_dir / "W3", w3_copy)
        expression = w3_copy / "expression.tsv"
        lines = expression.read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")
        idx = {name: i for i, name in enumerate(header)}
        for line_no in range(1, len(lines)):
            row = lines[line_no].split("\t")
            if row[idx["patient_id"]] == "CPCG0001" and row[idx["stable_gene_id"]] == "SYN:GENE_A":
                row[idx["value"]] = "100"
                lines[line_no] = "\t".join(row)
        expression.write_text("\n".join(lines) + "\n", encoding="utf-8")
        dest = _tmp() / "y-change"
        run_fold_evaluate(
            self.config,
            repo_root=REPO,
            w3_dir=w3_copy,
            w5_dir=self.run_dir / "W5",
            stage_dir=dest,
            parent_hashes={"config": self.config["_config_sha256"]},
            code_identity=IDENTITY,
            interpreter=sys.executable,
        )
        original_predictions = (self.run_dir / "W6" / "predictions.tsv").read_text(encoding="utf-8")
        changed_predictions = (dest / "predictions.tsv").read_text(encoding="utf-8")
        original_rows = [line.split("\t") for line in original_predictions.splitlines()]
        changed_rows = [line.split("\t") for line in changed_predictions.splitlines()]
        self.assertNotEqual(original_rows[1][1], changed_rows[1][1])
        for old, new in zip(original_rows[1:], changed_rows[1:]):
            self.assertEqual(old[0], new[0])
            self.assertEqual(old[2:4], new[2:4])
        original_metrics = json.loads((self.run_dir / "W6" / "evaluation.json").read_text(encoding="utf-8"))["metrics"]
        changed_metrics = json.loads((dest / "evaluation.json").read_text(encoding="utf-8"))["metrics"]
        self.assertNotEqual(original_metrics, changed_metrics)
        for rel, digest in self.w5_hashes.items():
            self.assertEqual(sha256_file(self.run_dir / "W5" / rel), digest)

    def test_predictor_change_can_change_extended_prediction(self) -> None:
        w3_copy = _tmp() / "w3-predictor-change"
        shutil.copytree(self.run_dir / "W3", w3_copy)
        methylation = w3_copy / "methylation.tsv"
        lines = methylation.read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")
        idx = {name: i for i, name in enumerate(header)}
        for line_no in range(1, len(lines)):
            row = lines[line_no].split("\t")
            if row[idx["patient_id"]] == "CPCG0001" and row[idx["probe_id"]] == "cgA1":
                row[idx["beta"]] = "0.99"
                lines[line_no] = "\t".join(row)
        methylation.write_text("\n".join(lines) + "\n", encoding="utf-8")
        dest = _tmp() / "predictor-change"
        run_fold_evaluate(
            self.config,
            repo_root=REPO,
            w3_dir=w3_copy,
            w5_dir=self.run_dir / "W5",
            stage_dir=dest,
            parent_hashes={"config": self.config["_config_sha256"]},
            code_identity=IDENTITY,
            interpreter=sys.executable,
        )
        original = (self.run_dir / "W6" / "predictions.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")
        changed = (dest / "predictions.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")
        self.assertEqual(original[2], changed[2])
        self.assertNotEqual(original[3], changed[3])
        for rel, digest in self.w5_hashes.items():
            self.assertEqual(sha256_file(self.run_dir / "W5" / rel), digest)

    def test_bundle_and_state_tamper_fail(self) -> None:
        model = self.run_dir / "W5" / "bundle" / "baseline_model.json"
        original = model.read_bytes()
        model.write_bytes(original + b"\n")
        with self.assertRaises(PipelineFailure) as ctx:
            load_w5_bundle(self.run_dir / "W5" / "bundle")
        self.assertIn("bundle-payload-hash-mismatch", str(ctx.exception))
        model.write_bytes(original)
        load_w5_bundle(self.run_dir / "W5" / "bundle")
        state = self.run_dir / "W5" / "bundle" / "final_feature_state.json"
        raw = json.loads(state.read_text(encoding="utf-8"))
        raw["state_sha256"] = "0" * 64
        tampered = _tmp() / "tamper-state"
        tampered.mkdir()
        for path in (self.run_dir / "W5" / "bundle").iterdir():
            (tampered / path.name).write_bytes(path.read_bytes())
        (tampered / "final_feature_state.json").write_text(json.dumps(raw), encoding="utf-8")
        checksums = json.loads((tampered / "checksums.json").read_text(encoding="utf-8"))
        checksums["files"]["final_feature_state.json"] = sha256_file(tampered / "final_feature_state.json")
        (tampered / "checksums.json").write_text(json.dumps(checksums, sort_keys=True), encoding="utf-8")
        complete = json.loads((tampered / "COMPLETE.json").read_text(encoding="utf-8"))
        complete["bundle_hash"] = sha256_file(tampered / "checksums.json")
        (tampered / "COMPLETE.json").write_text(json.dumps(complete, sort_keys=True), encoding="utf-8")
        with self.assertRaises(PipelineFailure) as state_exc:
            load_w5_bundle(tampered)
        self.assertIn("feature-state-hash-mismatch", str(state_exc.exception))

        contract_tampered = _tmp() / "tamper-contract"
        shutil.copytree(self.run_dir / "W5" / "bundle", contract_tampered)
        contract_path = contract_tampered / "contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["external_cohort"] = "OTHER-SYN"
        contract_path.write_text(json.dumps(contract, sort_keys=True) + "\n", encoding="utf-8")
        checksums_path = contract_tampered / "checksums.json"
        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        checksums["files"]["contract.json"] = sha256_file(contract_path)
        checksums_path.write_text(json.dumps(checksums, sort_keys=True) + "\n", encoding="utf-8")
        complete_path = contract_tampered / "COMPLETE.json"
        complete = json.loads(complete_path.read_text(encoding="utf-8"))
        complete["bundle_hash"] = sha256_file(checksums_path)
        complete_path.write_text(json.dumps(complete, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(PipelineFailure) as contract_exc:
            load_w5_bundle(contract_tampered)
        self.assertIn("bundle-contract-link-mismatch", str(contract_exc.exception))

    def test_overlap_fails(self) -> None:
        bundle = load_w5_bundle(self.run_dir / "W5" / "bundle")
        fake = bundle["development_patient_id_hashes"][0]
        from tools.b_prediction.__main__ import _sha256

        overlap_id = "TCGA-0001"
        self.assertEqual(_sha256(overlap_id.encode("utf-8")), fake)
        dest = _tmp() / "overlap"
        w3_copy = _tmp() / "w3overlap"
        shutil.copytree(self.run_dir / "W3", w3_copy)
        cov_path = w3_copy / "covariates.tsv"
        cov_path.write_text(
            cov_path.read_text(encoding="utf-8").replace("\tCPCG0001\t", "\tTCGA-0001\t", 1),
            encoding="utf-8",
        )
        with self.assertRaises(PipelineFailure) as ctx:
            run_fold_evaluate(
                self.config,
                repo_root=REPO,
                w3_dir=w3_copy,
                w5_dir=self.run_dir / "W5",
                stage_dir=dest,
                parent_hashes={"config": self.config["_config_sha256"]},
                code_identity=IDENTITY,
                interpreter=sys.executable,
            )
        self.assertIn("tcga-external-patient-overlap", str(ctx.exception))

    def test_metric_and_undefined_oracles(self) -> None:
        y = np.array([1.0, 3.0, 5.0], dtype=np.float64)
        f0 = np.array([1.0, 3.0, 5.0], dtype=np.float64)
        f1 = np.array([2.0, 2.0, 4.0], dtype=np.float64)
        sst = float(np.sum((y - y.mean()) ** 2))
        sse0 = float(np.sum((y - f0) ** 2))
        sse1 = float(np.sum((y - f1) ** 2))
        payload = _bootstrap_delta(
            y,
            f0,
            f1,
            {
                "resamples": 2000,
                "random_state": 42,
                "bit_generator": "PCG64",
                "quantiles": [0.025, 0.975],
                "quantile_method": "linear",
            },
        )
        self.assertEqual(payload["status"], "defined")
        self.assertAlmostEqual(payload["delta_r2"], (sse0 - sse1) / sst)
        constant = _bootstrap_delta(np.array([2.0, 2.0]), np.array([1.0, 1.0]), np.array([1.0, 1.0]), payload and {
            "resamples": 2000,
            "random_state": 42,
            "bit_generator": "PCG64",
            "quantiles": [0.025, 0.975],
            "quantile_method": "linear",
        })
        self.assertEqual(constant["status"], "undefined")
        self.assertIsNone(constant["delta_r2"])
        one = _bootstrap_delta(np.array([1.0]), np.array([0.0]), np.array([0.5]), {
            "resamples": 2000,
            "random_state": 42,
            "bit_generator": "PCG64",
            "quantiles": [0.025, 0.975],
            "quantile_method": "linear",
        })
        self.assertEqual(one["status"], "undefined")
        self.assertEqual(one["bootstrap"]["undefined_count"], 2000)
        worse = _bootstrap_delta(y, y, y + 10.0, {
            "resamples": 2000,
            "random_state": 42,
            "bit_generator": "PCG64",
            "quantiles": [0.025, 0.975],
            "quantile_method": "linear",
        })
        self.assertLess(worse["delta_r2"], 0.0)

    def test_resume_skips_w6(self) -> None:
        ok, reason = verify_complete_stage(self.run_dir, "W6")
        self.assertTrue(ok, reason)
        status = run_workflow(
            config_path=CONFIG,
            run_dir=self.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W6",
            resume=True,
        )
        self.assertEqual(status["executed"], [])
        self.assertIn("W6", status["skipped"])


if __name__ == "__main__":
    unittest.main()
