"""W5 fold-local development: leakage, frozen-state tamper, original interface."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.b_features.provider import FoldFeatureProvider
from tools.b_prediction.fold_develop import _candidate_ids
from tools.b_workflow.config import load_config
from tools.b_workflow.io import json_no_dups, read_tsv, sha256_file
from tools.b_workflow.run import run_workflow, verify_complete_stage


REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs" / "B" / "workflow.synthetic.json"
PYTHON = sys.executable


def _tmp() -> Path:
    explicit = os.environ.get("BP1_TEST_TMP_ROOT") or os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else REPO / "tmp" / "paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_w5_", dir=root))


class TestFoldLocalW5(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = _tmp() / "connected"
        run_workflow(
            config_path=CONFIG,
            run_dir=cls.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W5",
            resume=False,
        )
        cls.config = load_config(CONFIG, repo_root=REPO)

    def test_original_develop_cli_has_no_cohort_or_external(self) -> None:
        proc = subprocess.run(
            [PYTHON, "-m", "tools.b_prediction", "develop", "--help"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--development", proc.stdout)
        self.assertNotIn("--external", proc.stdout)
        self.assertNotIn("--cohort", proc.stdout)

    def test_connected_w5_wrote_models_and_feature_state(self) -> None:
        w5 = self.run_dir / "W5"
        self.assertTrue((w5 / "COMPLETE.json").is_file())
        self.assertTrue((w5 / "final_feature_state.json").is_file())
        self.assertTrue((w5 / "bundle" / "baseline_model.json").is_file())
        self.assertTrue((w5 / "bundle" / "extended_model.json").is_file())
        self.assertTrue((w5 / "bundle" / "oof_predictions.tsv").is_file())
        metrics = json.loads((w5 / "bundle" / "development_metrics.json").read_text(encoding="utf-8"))
        self.assertFalse(metrics["used_w4_full_state_for_nested_cv"])
        self.assertGreaterEqual(metrics["n_candidates"], 10)
        self.assertEqual(len(metrics["outer_folds"]), 5)
        state = json.loads((w5 / "final_feature_state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["synthetic"])
        self.assertEqual(state["state_sha256"], json.loads((w5 / "COMPLETE.json").read_text(encoding="utf-8"))["final_feature_state_sha256"])
        inner = json.loads((w5 / "inner_feature_states.json").read_text(encoding="utf-8"))
        self.assertTrue(inner)
        for row in inner:
            self.assertNotEqual(set(row["training_patient_ids"]), set(state["training_patient_ids"]))
        bundle_complete = json.loads((w5 / "bundle" / "COMPLETE.json").read_text(encoding="utf-8"))
        self.assertEqual(bundle_complete["bundle_hash"], sha256_file(w5 / "bundle" / "checksums.json"))
        manifest = json.loads((w5 / "bundle" / "bundle_manifest.json").read_text(encoding="utf-8"))
        for model_name in ("baseline_model.json", "extended_model.json"):
            model = json.loads((w5 / "bundle" / model_name).read_text(encoding="utf-8"))
            self.assertEqual(model["feature_state_sha256"], state["state_sha256"])
        self.assertEqual(manifest["final_feature_state_sha256"], state["state_sha256"])
        oof_header, oof_rows = read_tsv(w5 / "bundle" / "oof_predictions.tsv")
        oof_idx = {name: i for i, name in enumerate(oof_header)}
        oof_ids = [row[oof_idx["patient_id"]] for row in oof_rows]
        self.assertEqual(len(oof_ids), len(set(oof_ids)))
        self.assertEqual(len(oof_ids), metrics["n_oof"])
        for row in oof_rows:
            self.assertTrue(row[oof_idx["f0"]])
            self.assertTrue(row[oof_idx["f1"]])

    def test_candidate_population_does_not_prefilter_fold_dependent_promoter_missingness(self) -> None:
        provider = FoldFeatureProvider.from_cohort(
            self.run_dir / "W3",
            self.config["w4"],
            probe_map_path=REPO / self.config["w3"]["annotation"]["probe_map_path"],
            parent_hashes={"config": self.config["_config_sha256"]},
            code_identity_sha256="test",
        )
        candidates = _candidate_ids(provider, "TCGA-SYN")
        self.assertIn("TCGA-0002", candidates)
        self.assertIn("TCGA-0008", candidates)
        self.assertNotIn("TCGA-0004", candidates)  # fixed endpoint/universe failure

    def test_identical_fresh_runs_freeze_identical_bundle_bytes(self) -> None:
        repeat = _tmp() / "repeat"
        run_workflow(
            config_path=CONFIG,
            run_dir=repeat,
            repo_root=REPO,
            mode="synthetic",
            through="W5",
            resume=False,
        )
        first_bundle = self.run_dir / "W5" / "bundle"
        second_bundle = repeat / "W5" / "bundle"
        first = json.loads((first_bundle / "checksums.json").read_text(encoding="utf-8"))["files"]
        second = json.loads((second_bundle / "checksums.json").read_text(encoding="utf-8"))["files"]
        self.assertEqual(first, second)
        for name in first:
            self.assertEqual((first_bundle / name).read_bytes(), (second_bundle / name).read_bytes(), name)

    def test_heldout_beta_does_not_change_inner_training_state(self) -> None:
        provider = FoldFeatureProvider.from_cohort(
            self.run_dir / "W3",
            self.config["w4"],
            probe_map_path=REPO / self.config["w3"]["annotation"]["probe_map_path"],
            parent_hashes={"config": self.config["_config_sha256"]},
            code_identity_sha256="test",
        )
        candidates = _candidate_ids(provider, "TCGA-SYN")
        train = candidates[:8]
        heldout = candidates[8]
        before = provider.fit(train)
        mutated = copy.deepcopy(provider.methylation)
        for probe in mutated[heldout]:
            if mutated[heldout][probe]["beta"] is not None:
                mutated[heldout][probe]["beta"] = 0.0
        other = FoldFeatureProvider(
            expression=provider.expression,
            methylation=mutated,
            covariates=provider.covariates,
            probes=provider.probes,
            policy=provider.policy,
            parent_hashes=provider.parent_hashes,
            code_identity_sha256=provider.code_identity_sha256,
            detection_p_present_by_patient=provider.detection_p_present_by_patient,
        )
        after = other.fit(train)
        self.assertEqual(before.sha256, after.sha256)
        self.assertEqual(
            before.payload["eligible_probes_by_gene"],
            after.payload["eligible_probes_by_gene"],
        )

    def test_frozen_feature_state_tamper_is_rejected(self) -> None:
        w5 = self.run_dir / "W5"
        path = w5 / "final_feature_state.json"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        ok, reason = verify_complete_stage(self.run_dir, "W5")
        self.assertFalse(ok)
        self.assertIn("artifact-hash-mismatch", reason)
        path.write_bytes(original)
        ok, reason = verify_complete_stage(self.run_dir, "W5")
        self.assertTrue(ok, reason)
        payload = json_no_dups(original)
        payload["state_sha256"] = "0" * 64
        from tools.b_features.provider import FeatureState

        with self.assertRaises(Exception):
            FoldFeatureProvider.from_cohort(
                self.run_dir / "W3",
                self.config["w4"],
                probe_map_path=REPO / self.config["w3"]["annotation"]["probe_map_path"],
                parent_hashes={"config": self.config["_config_sha256"]},
                code_identity_sha256="test",
            ).transform(payload["training_patient_ids"], FeatureState(payload))


if __name__ == "__main__":
    unittest.main()
