"""Fold-local feature provider leakage and promoter fixtures."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.b_features.provider import FeatureState, FoldFeatureProvider
from tools.b_features.scores import program_score


REPO_ROOT = Path(__file__).resolve().parents[2]


POLICY = {
    "policy_label": "synthetic-fixture-only",
    "program_p": ["SYN:GENE_A", "SYN:GENE_B"],
    "universe_u": ["SYN:GENE_A", "SYN:GENE_B", "SYN:GENE_C", "SYN:GENE_D", "SYN:GENE_E"],
    "detection_p": {
        "apply_when_present": True,
        "max_detection_p": 0.01,
        "missing_detection_p": "treat-as-missing-beta",
    },
    "probe_training_coverage": 0.95,
    "aggregate_min_coverage": 0.80,
    "aggregate_min_probes": 1,
    "missingness": {
        "na_token": "NA",
        "na_is_not_zero": True,
        "required_u_finite": True,
        "required_p_finite": True,
        "incomplete_score": "exclude",
    },
    "eligibility": {
        "require_age": True,
        "require_gleason": True,
        "require_purity": True,
        "require_score": True,
        "require_all_promoter_aggregates": True,
    },
    "covariate_policy": {
        "quarantine_fields": ["WGS_BASED_PURITY_ESTIMATION"],
        "purity_source_field": "qpure_cellularity",
        "purity_method": "synthetic-qpure-fixture",
        "purity_scale": "fraction-0-1",
    },
}

PROBES = [
    {"probe_id": "cgA1", "target_gene_id": "SYN:GENE_A", "promoter_category": "promoter", "mask_status": "pass", "mask_reason": "none"},
    {"probe_id": "cgA2", "target_gene_id": "SYN:GENE_A", "promoter_category": "promoter", "mask_status": "pass", "mask_reason": "none"},
    {"probe_id": "cgA3", "target_gene_id": "SYN:GENE_A", "promoter_category": "body", "mask_status": "pass", "mask_reason": "none"},
    {"probe_id": "cgB1", "target_gene_id": "SYN:GENE_B", "promoter_category": "promoter", "mask_status": "pass", "mask_reason": "none"},
    {"probe_id": "cgB2", "target_gene_id": "SYN:GENE_B", "promoter_category": "promoter", "mask_status": "pass", "mask_reason": "none"},
    {"probe_id": "cgX1", "target_gene_id": "SYN:GENE_C", "promoter_category": "promoter", "mask_status": "masked", "mask_reason": "cross-reactive-synthetic-fixture"},
]


def _cov(pid: str) -> dict[str, str]:
    return {
        "patient_id": pid,
        "specimen_id": f"{pid}-01A",
        "cohort": "TCGA-SYN",
        "age_years": "60",
        "gleason_sum": "7",
        "purity_value": "0.7",
    }


def _expr(a, b, c, d, e):
    return {
        "SYN:GENE_A": a,
        "SYN:GENE_B": b,
        "SYN:GENE_C": c,
        "SYN:GENE_D": d,
        "SYN:GENE_E": e,
    }


def _probe_pack(beta_by_probe: dict[str, float | None]) -> dict[str, dict[str, float | None]]:
    out = {}
    for probe, beta in beta_by_probe.items():
        out[probe] = {"beta": beta, "detection_p": None}
    return out


def _write_tsv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    lines = ["\t".join(header), *("\t".join(str(value) for value in row) for row in rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestFoldFeatureProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.expression = {
            "T1": _expr(10.0, 10.0, 30.0, 5.0, 20.0),
            "T2": _expr(1.0, 2.0, 3.0, 4.0, 5.0),
            "T3": _expr(7.0, 7.0, 7.0, 7.0, 7.0),
        }
        self.methylation = {
            "T1": _probe_pack({"cgA1": 0.2, "cgA2": 0.3, "cgA3": 0.9, "cgB1": 0.1, "cgB2": 0.8, "cgX1": 0.5}),
            "T2": _probe_pack({"cgA1": 0.4, "cgA2": None, "cgA3": 0.9, "cgB1": 0.1, "cgB2": 0.8, "cgX1": 0.5}),
            "T3": _probe_pack({"cgA1": 0.6, "cgA2": 0.5, "cgA3": 0.9, "cgB1": 0.1, "cgB2": 0.8, "cgX1": 0.5}),
        }
        self.provider = FoldFeatureProvider(
            expression=self.expression,
            methylation=self.methylation,
            covariates={pid: _cov(pid) for pid in ("T1", "T2", "T3")},
            probes=PROBES,
            policy=POLICY,
            parent_hashes={"config": "abc"},
            code_identity_sha256="def",
            detection_p_present_by_patient={"T1": False, "T2": False, "T3": False},
        )

    def test_full_training_excludes_low_coverage_and_body_and_mask(self) -> None:
        state = self.provider.fit(["T1", "T2", "T3"])
        probes = state.payload["eligible_probes_by_gene"]
        self.assertEqual(probes["SYN:GENE_A"], ["cgA1"])
        self.assertEqual(probes["SYN:GENE_B"], ["cgB1", "cgB2"])
        excluded = {row["probe_id"]: row["reason"] for row in state.payload["probe_exclusions"]}
        self.assertEqual(excluded["cgA2"], "training-coverage-below-threshold")
        ann = {row["probe_id"]: row["reason"] for row in state.payload["annotation_exclusions"]}
        self.assertEqual(ann["cgA3"], "not-promoter")
        self.assertEqual(ann["cgX1"], "masked")

    def test_promoter_mean_uses_training_selected_probes(self) -> None:
        state = self.provider.fit(["T1", "T2", "T3"])
        rows = {row["patient_id"]: row for row in self.provider.transform(["T1"], state)}
        self.assertEqual(rows["T1"]["promoter"]["SYN:GENE_A"], 0.2)
        self.assertEqual(rows["T1"]["promoter"]["SYN:GENE_B"], 0.45)
        self.assertEqual(rows["T1"]["Y"], 0.375)

    def test_heldout_beta_change_does_not_change_training_state(self) -> None:
        train = ["T1", "T3"]
        before = self.provider.fit(train)
        mutated = copy.deepcopy(self.methylation)
        mutated["T2"]["cgA2"]["beta"] = 0.0
        mutated["T2"]["cgA1"]["beta"] = 0.0
        other = FoldFeatureProvider(
            expression=self.expression,
            methylation=mutated,
            covariates={pid: _cov(pid) for pid in ("T1", "T2", "T3")},
            probes=PROBES,
            policy=POLICY,
            parent_hashes={"config": "abc"},
            code_identity_sha256="def",
            detection_p_present_by_patient={"T1": False, "T2": False, "T3": False},
        )
        after = other.fit(train)
        self.assertEqual(before.sha256, after.sha256)
        self.assertEqual(
            before.payload["eligible_probes_by_gene"],
            after.payload["eligible_probes_by_gene"],
        )
        self.assertIn("cgA2", before.payload["eligible_probes_by_gene"]["SYN:GENE_A"])

    def test_fold_with_missing_training_probe_excludes_it(self) -> None:
        state = self.provider.fit(["T1", "T2"])
        self.assertNotIn("cgA2", state.payload["eligible_probes_by_gene"].get("SYN:GENE_A", []))

    def test_transform_does_not_refit_or_use_outcomes(self) -> None:
        state = self.provider.fit(["T1", "T2"])
        with self.assertRaises(Exception):
            self.provider.transform(["T3"], state, refit=True)
        rows = self.provider.transform(["T3"], state)
        self.assertEqual(rows[0]["feature_state_sha256"], state.sha256)
        self.assertEqual(
            rows[0]["Y"],
            program_score(self.expression["T3"], POLICY["universe_u"], POLICY["program_p"]),
        )

    def test_na_is_not_zero(self) -> None:
        state = self.provider.fit(["T1", "T2", "T3"])
        rows = {row["patient_id"]: row for row in self.provider.transform(["T2"], state)}
        self.assertEqual(rows["T2"]["promoter"]["SYN:GENE_A"], 0.4)

    def test_all_na_detection_p_still_marks_paired_assay_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="b_w4_detection_", dir=REPO_ROOT / "tmp") as temp:
            cohort = Path(temp)
            _write_tsv(
                cohort / "expression.tsv",
                ["patient_id", "stable_gene_id", "value"],
                [["T1", gene, index + 1] for index, gene in enumerate(POLICY["universe_u"])],
            )
            _write_tsv(
                cohort / "methylation.tsv",
                ["patient_id", "assay_id", "probe_id", "beta", "detection_p"],
                [["T1", "T1-METH", "cgA1", "0.2", "NA"]],
            )
            _write_tsv(
                cohort / "covariates.tsv",
                ["patient_id", "specimen_id", "cohort", "age_years", "gleason_sum", "purity_value"],
                [["T1", "T1-01A", "CPC-SYN", "60", "7", "0.7"]],
            )
            _write_tsv(
                cohort / "specimens.tsv",
                ["assay_id", "source_id", "modality", "inclusion"],
                [["T1-METH", "syn.cpc.methylation", "methylation", "include"]],
            )
            # Match the exact lowercase W3 filename so Linux/POSIX portability
            # is exercised even when the local filesystem is case-insensitive.
            (cohort / "manifest.json").write_text(
                json.dumps(
                    {
                        "parse_meta": [
                            {
                                "source_id": "syn.cpc.methylation",
                                "format": "cpc-methylation",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            probe_map = cohort / "probe_map.tsv"
            _write_tsv(
                probe_map,
                ["probe_id", "target_gene_id", "promoter_category", "mask_status", "mask_reason"],
                [["cgA1", "SYN:GENE_A", "promoter", "pass", "none"]],
            )
            provider = FoldFeatureProvider.from_cohort(
                cohort,
                copy.deepcopy(POLICY),
                probe_map_path=probe_map,
                parent_hashes={"config": "abc"},
                code_identity_sha256="def",
            )
            self.assertTrue(provider.detection_p_present_by_patient["T1"])
            state = provider.fit(["T1"])
            self.assertEqual(state.payload["eligible_probes_by_gene"], {})

    def test_transform_uses_frozen_detection_p_policy(self) -> None:
        methylation = copy.deepcopy(self.methylation)
        for patient in methylation.values():
            for record in patient.values():
                record["detection_p"] = 0.001
        methylation["T3"]["cgB2"]["detection_p"] = 0.5
        policy = copy.deepcopy(POLICY)
        provider = FoldFeatureProvider(
            expression=self.expression,
            methylation=methylation,
            covariates={pid: _cov(pid) for pid in ("T1", "T2", "T3")},
            probes=PROBES,
            policy=policy,
            parent_hashes={"config": "abc"},
            code_identity_sha256="def",
            detection_p_present_by_patient={"T1": True, "T2": True, "T3": True},
        )
        state = provider.fit(["T1", "T2"])
        provider.policy["detection_p"]["max_detection_p"] = 1.0
        row = provider.transform(["T3"], state)[0]
        self.assertEqual(state.sha256, state.payload["state_sha256"])
        self.assertIsNone(row["promoter"]["SYN:GENE_B"])
        self.assertEqual(row["exclusion_reason"], "promoter-aggregate-ineligible:SYN:GENE_B")

    def test_transform_rejects_tampered_feature_state(self) -> None:
        state = self.provider.fit(["T1", "T2"])
        payload = copy.deepcopy(state.payload)
        payload["aggregate_min_coverage"] = 0.0
        with self.assertRaisesRegex(Exception, "feature-state-hash-mismatch"):
            self.provider.transform(["T3"], FeatureState(payload))


if __name__ == "__main__":
    unittest.main()
