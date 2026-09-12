"""W8 contract oracles, provenance boundaries and connected publication tests."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from tools.b_secondary.secondary import (
    handoff_rows, run_secondary, score_contract, validate_contract,
    validate_handoff, verify_publication,
)
from tools.b_workflow.config import load_config
from tools.b_workflow.io import PipelineFailure, atomic_write_json, sha256_file, read_tsv
from tools.b_workflow.run import run_workflow, verify_complete_stage

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs/B/workflow.synthetic.json"


def scratch():
    root = REPO / "tmp/paper_b_checks"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="w8_tests_", dir=root))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(CONFIG.read_text())["w8"]
        self.score = self.policy["contracts"][0]
        self.handoff = self.policy["c_handoff"]

    def test_signed_weight_oracle_negative_zero_and_undefined(self):
        rows = score_contract(self.score, {
            "TCGA-1": {"SYN:GENE_A": 3, "SYN:GENE_B": 8},
            "TCGA-2": {"SYN:GENE_A": 4, "SYN:GENE_B": 4},
            "TCGA-3": {"SYN:GENE_A": 9},
        })
        self.assertEqual([r[3] for r in rows], [-5, 0, None])
        self.assertEqual(rows[2][4:6], ["undefined", "missing-member"])
        weighted = deepcopy(self.score)
        weighted["members"][0]["weight"] = 2
        self.assertEqual(score_contract(weighted, {"TCGA-1": {"SYN:GENE_A": 3, "SYN:GENE_B": 8}})[0][3], -2)

    def test_blocked_has_no_score(self):
        for contract in self.policy["contracts"][1:]:
            self.assertEqual(score_contract(contract, {"TCGA-1": {"SYN:GENE_A": 99}}), [])

    def test_unknown_missing_contract_fields_and_unresolved_names_fail(self):
        for key in self.score:
            changed = deepcopy(self.score)
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(PipelineFailure):
                validate_contract(changed)
        changed = deepcopy(self.score)
        changed["unfrozen_default"] = True
        with self.assertRaises(PipelineFailure):
            validate_contract(changed)
        for name in ["AYERS_GEP_18", "HALLMARK_INTERFERON_GAMMA_RESPONSE", "HOPE_18", "M0_EXTRA_ANTIGEN_PRESENTATION"]:
            changed = deepcopy(self.score)
            changed["id"] = name
            with self.subTest(name=name), self.assertRaises(PipelineFailure):
                validate_contract(changed)

    def test_handoff_rejects_external_and_outcome_derived_contract(self):
        for key, value in [("source_cohort", "CPC-SYN"), ("source_stage", "W6"),
                           ("uses_external_outcomes", True), ("uses_external_outcomes", 0),
                           ("membership_source", "CPC-selected"), ("selection", "best-external-effect"),
                           ("scale", "unspecified")]:
            changed = deepcopy(self.handoff)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(PipelineFailure):
                validate_handoff(changed)
        changed = deepcopy(self.handoff)
        del changed["missingness"]
        with self.assertRaises(PipelineFailure):
            validate_handoff(changed)

    def test_handoff_retains_negative_zero_undefined_and_missing_counts(self):
        rows = handoff_rows(self.handoff, {"TCGA-1": {"SYN:GENE_A": 10, "SYN:GENE_B": 20},
                                         "TCGA-2": {"SYN:GENE_A": None, "SYN:GENE_B": 20}})
        self.assertEqual([r[4] for r in rows], [-10, 0, None])
        self.assertEqual([r[5] for r in rows], ["negative", "zero", "undefined"])
        self.assertEqual(rows[0][2:4], [1, 1])
        self.assertTrue(all(r[6:8] == [None, None] for r in rows))

    def test_score_overflow_fails_closed(self):
        with self.assertRaises(PipelineFailure):
            score_contract(self.score, {"TCGA-1": {"SYN:GENE_A": 1.7e308, "SYN:GENE_B": -1.7e308}})


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = scratch()
        cls.run_dir = cls.root / "fresh"
        cls.status = run_workflow(config_path=CONFIG, run_dir=cls.run_dir, repo_root=REPO,
                                  mode="synthetic", through="W8", resume=False, interpreter=sys.executable)
        cls.config = load_config(CONFIG, repo_root=REPO)
        cls.identity = cls.status["code_identity_sha256"]

    def copy(self):
        dest = scratch() / "copy"
        shutil.copytree(self.run_dir, dest)
        return dest

    def invoke(self, run):
        complete = json.loads((run / "W8/COMPLETE.json").read_text())
        return run_secondary(self.config, repo_root=REPO, run_dir=run, stage_dir=run / "W8-new",
                             parent_hashes=complete["parent_hashes"], code_identity=self.identity, interpreter=sys.executable)

    def test_full_completion_is_software_only_and_resume_skips_all(self):
        self.assertTrue(self.status["pipeline_complete"])
        self.assertEqual(self.status["completion_scope"], "synthetic-software-w1-w8")
        self.assertFalse(self.status["biological_validation"])
        status = run_workflow(config_path=CONFIG, run_dir=self.run_dir, repo_root=REPO,
                              mode="synthetic", through="W8", resume=True)
        self.assertEqual(status["executed"], [])
        self.assertEqual(status["skipped"], [f"W{i}" for i in range(1, 9)])

    def test_computed_rows_trace_to_w3_and_named_modules_blocked(self):
        header, rows = read_tsv(self.run_dir / "W8/module_results.tsv")
        indexed = {r[1]: dict(zip(header, r)) for r in rows}
        self.assertEqual(float(indexed["TCGA-0001"]["value"]), 0)
        # Missing unrelated GENE_E blocks the primary rank score, not this A-B fixture.
        self.assertEqual(float(indexed["TCGA-0004"]["value"]), 0)
        self.assertTrue(all(r[0] == "FICTIONAL_SIGNED_TPM_DIFFERENCE_V1" for r in rows))
        _, blocked = read_tsv(self.run_dir / "W8/blocked_reasons.tsv")
        self.assertTrue({"AYERS_GEP_18", "HOPE_18", "HALLMARK_INTERFERON_GAMMA_RESPONSE", "MethylCIBERSORT", "LUAD"}.issubset({r[0] for r in blocked}))
        self.assertTrue(all(r[1] for r in blocked))

    def test_context_is_not_scored_and_approval_evidence_is_not_invented(self):
        _, rows = read_tsv(self.run_dir / "W8/registry_context.tsv")
        self.assertEqual(len({r[0] for r in rows}), 7)
        self.assertTrue(all(r[4] == "not-scored" for r in rows))
        _, targets = read_tsv(self.run_dir / "W8/approval_evidence_targets.tsv")
        self.assertEqual(targets, [])

    def test_payload_tamper_each_upstream_and_w8_is_detected(self):
        for stage, file in [("W3", "expression.tsv"), ("W5", "bundle/baseline_model.json"),
                            ("W6", "predictions.tsv"), ("W7", "report.json"), ("W8", "paper_c_handoff.tsv")]:
            run = self.copy()
            path = run / stage / file
            path.write_bytes(path.read_bytes() + b"tamper")
            with self.subTest(stage=stage):
                if stage == "W8":
                    self.assertFalse(verify_complete_stage(run, stage)[0])
                else:
                    with self.assertRaises(PipelineFailure):
                        self.invoke(run)
                    self.assertFalse((run / "W8-new/COMPLETE.json").exists())

    def test_exact_payload_and_rehashed_manifest_disagreement_rejected(self):
        run = self.copy()
        (run / "W7/undeclared.tsv").write_text("extra")
        with self.assertRaisesRegex(PipelineFailure, "undeclared"):
            self.invoke(run)

        run = self.copy()
        path = run / "W7/manifest.json"
        payload = json.loads(path.read_text())
        payload["code_identity_sha256"] = "wrong"
        atomic_write_json(path, payload)
        complete = json.loads((run / "W7/COMPLETE.json").read_text())
        complete["manifest_sha256"] = sha256_file(path)
        atomic_write_json(run / "W7/COMPLETE.json", complete)
        with self.assertRaisesRegex(PipelineFailure, "manifest-disagreement"):
            self.invoke(run)

    def test_missing_complete_has_clean_failure(self):
        empty = scratch()
        self.assertEqual(verify_complete_stage(empty, "W8"), (False, "missing-COMPLETE"))

    def test_w8_completion_cannot_claim_biological_scope(self):
        run = self.copy()
        path = run / "W8/COMPLETE.json"
        complete = json.loads(path.read_text())
        complete["completion_scope"] = "biological-validation"
        atomic_write_json(path, complete)
        ok, reason = verify_complete_stage(run, "W8")
        self.assertFalse(ok)
        self.assertIn("invalid-software-completion-scope", reason)

    def test_c_handoff_ignores_external_expression_values(self):
        # Exercise the input-reading boundary directly without forging publications.
        from tools.b_secondary.secondary import expression_rows, tcga_values
        rows = expression_rows(self.run_dir / "W3/expression.tsv")
        before = handoff_rows(self.config["w8"]["c_handoff"], tcga_values(rows))
        for row in rows:
            if row["cohort"] == "CPC-SYN":
                row["value"] = "99999999"
        after = handoff_rows(self.config["w8"]["c_handoff"], tcga_values(rows))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
