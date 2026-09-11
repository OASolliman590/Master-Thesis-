"""W3 identity, NA preservation and WGS-purity quarantine tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.b_cohort.build import run_cohort
from tools.b_workflow.config import load_config
from tools.b_workflow.io import PipelineFailure, read_tsv
from tools.b_workflow.run import run_workflow

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "specs" / "B" / "workflow.synthetic.json"
PYTHON = os.environ.get("B_WORKFLOW_PYTHON")


def _tmp() -> Path:
    explicit = os.environ.get("B_WORKFLOW_TEST_TMP_ROOT")
    root = Path(explicit) if explicit else Path(tempfile.gettempdir())
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="b_w3_", dir=root))


class TestCohort(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = _tmp() / "run"
        run_workflow(
            config_path=CONFIG,
            run_dir=cls.run_dir,
            repo_root=REPO,
            mode="synthetic",
            through="W4",
            resume=False,
        )
        cls.w3 = cls.run_dir / "W3"

    def test_canonical_tables_exist_and_are_synthetic(self) -> None:
        for name in (
            "specimens.tsv",
            "expression.tsv",
            "methylation.tsv",
            "covariates.tsv",
            "exclusions.tsv",
            "coverage.tsv",
            "COMPLETE.json",
        ):
            self.assertTrue((self.w3 / name).is_file(), name)
        header, rows = read_tsv(self.w3 / "expression.tsv")
        self.assertIn("synthetic", header)
        self.assertTrue(all(row[header.index("synthetic")] == "true" for row in rows))
        summaries = [row for row in rows if row[header.index("raw_gene_id")].startswith("N_")]
        self.assertEqual(summaries, [])
        genes_f = [row for row in rows if row[header.index("symbol")] == "GENE_F"]
        self.assertTrue(genes_f)

    def test_na_preserved_not_zero(self) -> None:
        header, rows = read_tsv(self.w3 / "methylation.tsv")
        idx = {name: i for i, name in enumerate(header)}
        t2 = [
            row
            for row in rows
            if row[idx["patient_id"]] == "TCGA-0002" and row[idx["probe_id"]] == "cgA2"
        ]
        self.assertEqual(len(t2), 1)
        self.assertEqual(t2[0][idx["beta"]], "NA")
        self.assertNotEqual(t2[0][idx["beta"]], "0")

    def test_detection_p_preserved(self) -> None:
        header, rows = read_tsv(self.w3 / "methylation.tsv")
        idx = {name: i for i, name in enumerate(header)}
        cpc = [
            row
            for row in rows
            if row[idx["patient_id"]].startswith("CPCG") and row[idx["detection_p"]] != "NA"
        ]
        self.assertTrue(cpc)
        self.assertIn("detection_p", header)

    def test_wgs_agreement_is_not_purity(self) -> None:
        header, rows = read_tsv(self.w3 / "covariates.tsv")
        idx = {name: i for i, name in enumerate(header)}
        row = next(r for r in rows if r[idx["patient_id"]] == "TCGA-0001")
        self.assertEqual(row[idx["purity_source_field"]], "qpure_cellularity")
        self.assertNotEqual(row[idx["purity_value"]], row[idx["wgs_agreement_quarantined"]])
        self.assertAlmostEqual(float(row[idx["purity_value"]]), 0.7)
        self.assertAlmostEqual(float(row[idx["wgs_agreement_quarantined"]]), 0.99)

    def test_one_evaluation_row_per_patient(self) -> None:
        header, rows = read_tsv(self.w3 / "covariates.tsv")
        idx = {name: i for i, name in enumerate(header)}
        patients = [row[idx["patient_id"]] for row in rows]
        self.assertEqual(len(patients), len(set(patients)))

    def test_cpc_replicate_median(self) -> None:
        header, rows = read_tsv(self.w3 / "methylation.tsv")
        idx = {name: i for i, name in enumerate(header)}
        row = next(
            r
            for r in rows
            if r[idx["patient_id"]] == "CPCG0001" and r[idx["probe_id"]] == "cgA1"
        )
        self.assertAlmostEqual(float(row[idx["beta"]]), 0.3)

    def _mutated_spec_config(self, name: str, mutate) -> Path:
        spec_src = REPO / "specs" / "B" / "synthetic" / "identity" / "specimens.tsv"
        lines = spec_src.read_text(encoding="utf-8").splitlines()
        dest_dir = REPO / "tmp" / "paper_b_checks" / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "specimens.tsv").write_text("\n".join(mutate(lines)) + "\n", encoding="utf-8")
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["w3"]["identity"]["specimen_map_path"] = f"tmp/paper_b_checks/{name}/specimens.tsv"
        dest_cfg = dest_dir / "config.json"
        dest_cfg.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return dest_cfg

    def test_ambiguous_focus_fails(self) -> None:
        def mutate(lines: list[str]) -> list[str]:
            out = []
            for line in lines:
                fields = line.split("\t")
                if len(fields) > 9 and fields[1] == "TCGA-0002" and fields[9] == "expression":
                    fields[1] = "TCGA-0001"
                    fields[3] = "F2"
                    line = "\t".join(fields)
                out.append(line)
            return out

        dest_cfg = self._mutated_spec_config("bad_identity", mutate)
        loaded = load_config(dest_cfg, repo_root=REPO)
        with self.assertRaises(PipelineFailure) as ctx:
            run_cohort(
                loaded,
                repo_root=REPO,
                w2_dir=self.run_dir / "W2",
                stage_dir=_tmp() / "W3bad",
                parent_hashes={"config": loaded["_config_sha256"]},
                code_identity="test",
                interpreter="test",
            )
        self.assertIn("ambiguous-focus-join", str(ctx.exception))

    def test_overlap_fails(self) -> None:
        def mutate(lines: list[str]) -> list[str]:
            out = []
            for line in lines:
                fields = line.split("\t")
                if len(fields) > 1 and fields[0] == "CPC-SYN" and fields[1] == "CPCG0003":
                    fields[1] = "TCGA-0001"
                    line = "\t".join(fields)
                out.append(line)
            return out

        dest_cfg = self._mutated_spec_config("overlap_identity", mutate)
        loaded = load_config(dest_cfg, repo_root=REPO)
        with self.assertRaises(PipelineFailure) as ctx:
            run_cohort(
                loaded,
                repo_root=REPO,
                w2_dir=self.run_dir / "W2",
                stage_dir=_tmp() / "W3overlap",
                parent_hashes={"config": loaded["_config_sha256"]},
                code_identity="test",
                interpreter="test",
            )
        self.assertIn("tcga-external-patient-overlap", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
