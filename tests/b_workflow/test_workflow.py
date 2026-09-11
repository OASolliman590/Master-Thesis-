"""Connected W1-W4 workflow: plan, run, resume, tamper, unimplemented W5."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.b_workflow.io import read_tsv, sha256_file
from tools.b_workflow.run import run_workflow, verify_complete_stage

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs" / "B" / "workflow.synthetic.json"
PYTHON = sys.executable


def _tmp() -> Path:
    explicit = os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else REPO / "tmp" / "paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_w1_", dir=root))


def _cli(args: list[str], cwd: Path = REPO) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, "-m", "tools.b_workflow", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
        shell=False,
    )


class TestWorkflow(unittest.TestCase):
    def test_plan_lists_w1_w8_and_unimplemented_gates(self) -> None:
        proc = _cli(["plan", "--config", str(CONFIG)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        plan = json.loads(proc.stdout)
        ids = [stage["id"] for stage in plan["stages"]]
        self.assertEqual(ids, ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"])
        by_id = {stage["id"]: stage for stage in plan["stages"]}
        self.assertTrue(by_id["W4"]["implemented"])
        self.assertFalse(by_id["W5"]["implemented"])
        self.assertEqual(by_id["W5"]["blocked_reason"], "stage-not-implemented:w5")
        self.assertFalse(plan["pipeline_complete"])
        self.assertTrue(plan["synthetic"])
        for stage in plan["stages"]:
            for command in stage["commands"]:
                self.assertIsInstance(command, list)
                self.assertNotIn("shell", command)

    def test_config_rejects_shell_commands(self) -> None:
        tmp = _tmp()
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["shell"] = "rm -rf /"
        bad = tmp / "bad.json"
        bad.write_text(json.dumps(payload), encoding="utf-8")
        proc = _cli(["plan", "--config", str(bad)])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("forbidden-key", proc.stderr)

    def test_run_through_w4_is_connected_and_not_complete_pipeline(self) -> None:
        run_dir = _tmp() / "run"
        proc = _cli(
            [
                "run",
                "--mode",
                "synthetic",
                "--config",
                str(CONFIG),
                "--output",
                str(run_dir),
                "--through",
                "W4",
            ]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        status = json.loads(proc.stdout)
        self.assertEqual(status["status"], "complete-through")
        self.assertFalse(status["pipeline_complete"])
        self.assertTrue(status["synthetic"])
        for stage in ("W1", "W2", "W3", "W4"):
            self.assertTrue((run_dir / stage / "COMPLETE.json").is_file(), stage)
            complete = json.loads((run_dir / stage / "COMPLETE.json").read_text(encoding="utf-8"))
            self.assertEqual(complete["status"], "complete")
            self.assertTrue(complete["synthetic"])
        self.assertFalse((run_dir / "W5" / "COMPLETE.json").exists())
        w2_manifest = json.loads((run_dir / "W2" / "checksums.json").read_text(encoding="utf-8"))
        w3_manifest = json.loads((run_dir / "W3" / "checksums.json").read_text(encoding="utf-8"))
        self.assertEqual(w3_manifest["parent_hashes"]["parent:W2"], sha256_file(run_dir / "W2" / "checksums.json"))
        scores_h, scores = read_tsv(run_dir / "W4" / "score_features.tsv")
        y_idx = scores_h.index("Y")
        pid_idx = scores_h.index("patient_id")
        by_pid = {row[pid_idx]: row for row in scores}
        self.assertAlmostEqual(float(by_pid["TCGA-0001"][y_idx]), 0.375)
        self.assertAlmostEqual(float(by_pid["TCGA-0002"][y_idx]), 0.125)
        self.assertAlmostEqual(float(by_pid["TCGA-0003"][y_idx]), 0.5)
        self.assertEqual(by_pid["TCGA-0004"][scores_h.index("eligible")], "false")
        state = json.loads((run_dir / "W4" / "full_training_feature_state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["synthetic"])
        self.assertEqual(state["eligible_probes_by_gene"]["SYN:GENE_A"], ["cgA1"])
        self.assertIn("state_sha256", state)
        self.test_run_dir = run_dir

    def test_default_run_fails_honestly_at_w5(self) -> None:
        run_dir = _tmp() / "full"
        proc = _cli(
            [
                "run",
                "--mode",
                "synthetic",
                "--config",
                str(CONFIG),
                "--output",
                str(run_dir),
            ]
        )
        self.assertEqual(proc.returncode, 5, proc.stderr + proc.stdout)
        self.assertIn("stage-not-implemented:w5", proc.stderr)
        self.assertTrue((run_dir / "W4" / "COMPLETE.json").is_file())
        self.assertFalse((run_dir / "W5" / "COMPLETE.json").exists())
        status = json.loads((run_dir / "run_status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["pipeline_complete"])
        self.assertEqual(status["failed_stage"], "W5")

    def test_resume_skips_completed_work(self) -> None:
        run_dir = _tmp() / "resume"
        first = _cli(
            [
                "run",
                "--mode",
                "synthetic",
                "--config",
                str(CONFIG),
                "--output",
                str(run_dir),
                "--through",
                "W4",
            ]
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        w4_hash = sha256_file(run_dir / "W4" / "checksums.json")
        w3_hash = sha256_file(run_dir / "W3" / "checksums.json")
        second = _cli(["resume", "--output", str(run_dir), "--through", "W4"])
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        status = json.loads(second.stdout)
        self.assertEqual(status["executed"], [])
        self.assertEqual(status["skipped"], ["W1", "W2", "W3", "W4"])
        self.assertEqual(sha256_file(run_dir / "W4" / "checksums.json"), w4_hash)
        self.assertEqual(sha256_file(run_dir / "W3" / "checksums.json"), w3_hash)

    def test_tamper_invalidates_descendants(self) -> None:
        run_dir = _tmp() / "tamper"
        first = _cli(
            [
                "run",
                "--mode",
                "synthetic",
                "--config",
                str(CONFIG),
                "--output",
                str(run_dir),
                "--through",
                "W4",
            ]
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        w3_before = sha256_file(run_dir / "W3" / "checksums.json")
        payload = run_dir / "W2" / "cache" / "syn.tcga.star.0001" / "payload"
        original = payload.read_bytes()
        payload.write_bytes(original + b"\n#tampered\n")
        ok, reason = verify_complete_stage(run_dir, "W2")
        self.assertFalse(ok)
        self.assertIn("artifact-hash-mismatch", reason)
        second = _cli(["resume", "--output", str(run_dir), "--through", "W4"])
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        status = json.loads(second.stdout)
        actions = [(item["action"], item.get("stage")) for item in status["log"]]
        self.assertIn(("invalidate", "W2"), actions)
        self.assertIn(("invalidate", "W3"), actions)
        self.assertIn(("invalidate", "W4"), actions)
        self.assertNotIn(("skip-complete", "W3"), actions)
        self.assertIn("W3", status["executed"])
        self.assertTrue((run_dir / "W3" / "COMPLETE.json").is_file())
        self.assertEqual(payload.read_bytes(), original)

    def test_complete_record_pins_checksums_and_manifest(self) -> None:
        run_dir = _tmp() / "pinned-completion"
        first = _cli(
            [
                "run",
                "--mode",
                "synthetic",
                "--config",
                str(CONFIG),
                "--output",
                str(run_dir),
                "--through",
                "W2",
            ]
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        stage_dir = run_dir / "W2"
        payload_path = stage_dir / "cache" / "syn.tcga.star.0001" / "payload"
        checksums_path = stage_dir / "checksums.json"
        manifest_path = stage_dir / "manifest.json"
        original_payload = payload_path.read_bytes()

        # Updating an artifact and its mutable checksum index must not bypass the
        # immutable hash recorded in COMPLETE.json.
        payload_path.write_bytes(original_payload + b"\n#tampered\n")
        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        checksums["artifact_hashes"]["cache/syn.tcga.star.0001/payload"] = sha256_file(payload_path)
        checksums_path.write_text(json.dumps(checksums), encoding="utf-8")
        ok, reason = verify_complete_stage(run_dir, "W2")
        self.assertFalse(ok)
        self.assertEqual(reason, "checksums-hash-mismatch")
        repaired = _cli(["resume", "--output", str(run_dir), "--through", "W2"])
        self.assertEqual(repaired.returncode, 0, repaired.stderr + repaired.stdout)
        self.assertEqual(payload_path.read_bytes(), original_payload)

        # The human-readable manifest is independently pinned as well.
        manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
        ok, reason = verify_complete_stage(run_dir, "W2")
        self.assertFalse(ok)
        self.assertEqual(reason, "manifest-hash-mismatch")
        repaired = _cli(["resume", "--output", str(run_dir), "--through", "W2"])
        self.assertEqual(repaired.returncode, 0, repaired.stderr + repaired.stdout)
        ok, reason = verify_complete_stage(run_dir, "W2")
        self.assertTrue(ok, reason)

    def test_interrupted_stage_is_not_complete(self) -> None:
        run_dir = _tmp() / "interrupt"
        run_workflow(
            config_path=CONFIG,
            run_dir=run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W2",
            resume=False,
        )
        work = run_dir / "W3.work"
        work.mkdir()
        (work / "partial.tsv").write_text("not-complete\n", encoding="utf-8")
        self.assertFalse((run_dir / "W3" / "COMPLETE.json").exists())
        status = run_workflow(
            config_path=CONFIG,
            run_dir=run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W3",
            resume=True,
        )
        self.assertIn("W3", status["executed"])
        self.assertTrue((run_dir / "W3" / "COMPLETE.json").is_file())
        self.assertFalse(work.exists())

    def test_cli_help(self) -> None:
        proc = _cli(["--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("plan", proc.stdout)
        self.assertIn("run", proc.stdout)
        self.assertIn("resume", proc.stdout)


if __name__ == "__main__":
    unittest.main()
