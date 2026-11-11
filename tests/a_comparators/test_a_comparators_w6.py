import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from tools.a_comparators import cyt_scores_from_tpm
from tools.a_comparators.__main__ import main as comparators_main
from tools.a_comparators.readiness import (
    ComparatorNotReady,
    method_status,
    method_statuses,
    require_method_ready,
)
from tools.a_meta import provenance as a_meta_provenance
from tools.a_meta.effects import study_effects
from tools.a_meta.provenance import (
    SYNTHETIC_FIXTURE_PRODUCER,
    canonical_sha256,
    effect_input_payload,
    write_synthetic_fixture_manifest,
)
from tools.a_meta import __main__ as a_meta_cli


class _ClinicalReadSentinel(SimpleNamespace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clinical_reads = 0

    @property
    def clinical_rows(self):
        self.clinical_reads += 1
        raise AssertionError("clinical payload was accessed before real-classification refusal")


class CytScoringTests(unittest.TestCase):
    def test_cyt_uses_no_offset_geometric_mean_and_preserves_patient_row_order(self):
        scores = cyt_scores_from_tpm(
            feature_symbols=("GZMA", "PRF1"),
            expression_by_feature=((4, 16, 25, 0), (9, 4, 1, 100)),
            representation={
                "platform": "rnaseq",
                "unit": "tpm",
                "transform": "linear",
                "feature_id": "symbol",
            },
            aliases={},
            synonyms={},
            gene_symbols={},
        )

        # Hand-derived from sqrt(4*9), sqrt(16*4), sqrt(25*1), sqrt(0*100).
        self.assertEqual(scores, [6.0, 8.0, 5.0, 0.0])

    def test_missing_required_gene_value_stays_unscorable(self):
        scores = cyt_scores_from_tpm(
            feature_symbols=("GZMA", "PRF1"),
            expression_by_feature=((4, None), (9, 16)),
            representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
            aliases={},
            synonyms={},
            gene_symbols={},
        )

        self.assertEqual(scores, [6.0, None])

    def test_non_tpm_units_are_refused_without_conversion(self):
        for unit in ("fpkm", "counts", "normalized_counts"):
            with self.subTest(unit=unit):
                with self.assertRaisesRegex(ValueError, "qualified linear RNA-seq TPM"):
                    cyt_scores_from_tpm(
                        feature_symbols=("GZMA", "PRF1"),
                        expression_by_feature=((4,), (9,)),
                        representation={"platform": "rnaseq", "unit": unit, "transform": "linear"},
                        aliases={},
                        synonyms={},
                        gene_symbols={},
                    )

    def test_duplicate_or_ambiguous_required_symbols_are_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate rows for required gene GZMA"):
            cyt_scores_from_tpm(
                feature_symbols=("GZMA", "GZMA", "PRF1"),
                expression_by_feature=((1,), (2,), (3,)),
                representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
                aliases={},
                synonyms={},
                gene_symbols={},
            )

        with self.assertRaisesRegex(ValueError, r"unresolved: GZMA \(ambiguous\), PRF1 \(ambiguous\)"):
            cyt_scores_from_tpm(
                feature_symbols=("SHARED",),
                expression_by_feature=((1,),),
                representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
                aliases={},
                synonyms={"GZMA": {"SHARED"}, "PRF1": {"SHARED"}},
                gene_symbols={},
            )

    def test_invalid_abundance_fails_without_reclassification(self):
        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            cyt_scores_from_tpm(
                feature_symbols=("GZMA", "PRF1"),
                expression_by_feature=((4,), (-1,)),
                representation={"platform": "rnaseq", "unit": "tpm", "transform": "linear"},
                aliases={},
                synonyms={},
                gene_symbols={},
            )


class ComparatorReadinessTests(unittest.TestCase):
    def test_conditional_comparator_refuses_with_its_specific_blocker(self):
        with self.assertRaisesRegex(ComparatorNotReady, "Final 59-gene membership/rule and 19-cohort roster"):
            require_method_ready("LIN_2026_59G")

    def test_readiness_command_exposes_each_method_once(self):
        output = StringIO()
        with redirect_stdout(output):
            result = comparators_main(["readiness"])

        rows = output.getvalue().splitlines()
        method_ids = [row["method_id"] for row in method_statuses()]
        self.assertEqual(result, 0)
        self.assertEqual(len(method_ids), len(set(method_ids)))
        self.assertEqual(len(rows), len(method_ids) + 1)
        self.assertIn("BLOCKED", output.getvalue())

    def test_constant_is_only_a_sanity_baseline_and_never_promises_auc(self):
        constant = method_status("CONSTANT_SANITY_v1")

        self.assertEqual(constant["implementation_state"], "SANITY_BASELINE_ONLY")
        self.assertIn("sanity baseline", constant["measurement_coverage_missing_policy"])
        self.assertIn("no AUC if either outcome class is absent", constant["measurement_coverage_missing_policy"])


class OutcomeLockTests(unittest.TestCase):
    def test_a_meta_compares_methods_on_same_invented_rows_despite_record_order(self):
        view = SimpleNamespace(
            metadata=SimpleNamespace(
                cohort_id="invented_comparator_alignment",
                cancer="melanoma",
                endpoint_families=("orr",),
                uniform_drug_class=None,
            ),
            clinical_rows=[
                {"raw_orr": label, "endpoint_definition": "ORR RECIST CR PR SD PD",
                 "drug_class_normalised": "ANTI_PD_L1_AXIS"}
                for label in ("CR", "PR", "SD", "PD")
            ],
        )
        features = {
            "cohort_id": "invented_comparator_alignment",
            "unit_family": "gene",
            "records": [
                {"patient_row": 3, "unit": "CYT", "value": 4.0},
                {"patient_row": 1, "unit": "CYT", "value": 8.0},
                {"patient_row": 0, "unit": "CYT", "value": 6.0},
                {"patient_row": 2, "unit": "CYT", "value": 2.0},
                {"patient_row": 3, "unit": "VARYING", "value": 7.0},
                {"patient_row": 1, "unit": "VARYING", "value": 3.0},
                {"patient_row": 0, "unit": "VARYING", "value": 1.0},
                {"patient_row": 2, "unit": "VARYING", "value": 5.0},
            ],
            "metadata": {
                "method_id_by_unit": {
                    "CYT": "CYT_Rooney_TPM_v1",
                    "VARYING": "INVENTED_VARYING_COMPARATOR",
                }
            },
        }

        with TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "synthetic-manifest.json"
            write_synthetic_fixture_manifest(
                manifest,
                kind="study_effects_input",
                payload=effect_input_payload(view, features),
                cohort_ids=(view.metadata.cohort_id,),
            )
            effects = study_effects(
                view,
                features,
                "orr",
                by_drug_class=False,
                provenance_manifest=manifest,
            )

        by_unit = {row["unit"]: row for row in effects}
        self.assertEqual(by_unit["CYT"]["patient_set_id"], by_unit["VARYING"]["patient_set_id"])
        self.assertEqual((by_unit["CYT"]["mean_R"], by_unit["CYT"]["mean_NR"]), (7.0, 3.0))
        self.assertEqual((by_unit["VARYING"]["mean_R"], by_unit["VARYING"]["mean_NR"]), (2.0, 6.0))

    def test_constant_sanity_baseline_uses_equal_scores_and_is_not_estimable(self):
        view = SimpleNamespace(
            metadata=SimpleNamespace(
                cohort_id="invented_constant_sanity",
                cancer="melanoma",
                endpoint_families=("orr",),
                uniform_drug_class=None,
            ),
            clinical_rows=[
                {"raw_orr": label, "endpoint_definition": "ORR RECIST CR PR SD PD",
                 "drug_class_normalised": "ANTI_PD_L1_AXIS"}
                for label in ("CR", "PR", "SD", "PD")
            ],
        )
        features = {
            "cohort_id": view.metadata.cohort_id,
            "unit_family": "gene",
            "records": [
                {"patient_row": index, "unit": "CONSTANT", "value": 1.0}
                for index in range(4)
            ],
            "metadata": {"method_id_by_unit": {"CONSTANT": "CONSTANT_SANITY_v1"}},
        }

        with TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "synthetic-manifest.json"
            write_synthetic_fixture_manifest(
                manifest,
                kind="study_effects_input",
                payload=effect_input_payload(view, features),
                cohort_ids=(view.metadata.cohort_id,),
            )
            effect = next(
                row for row in study_effects(
                    view, features, "orr", by_drug_class=False, provenance_manifest=manifest
                ) if row["drug_class_stratum"] == "ALL"
            )

        self.assertEqual((effect["mean_R"], effect["mean_NR"]), (1.0, 1.0))
        self.assertEqual(effect["method_id"], "CONSTANT_SANITY_v1")
        self.assertEqual(effect["status"], "NA")
        self.assertIn("pooled_sd_zero", effect["reason"])

    def test_explicit_real_view_rejects_synthetic_manifests_before_payload_or_hash(self):
        cohort_id = "invented_explicit_real_classification"
        normal_view = SimpleNamespace(
            metadata=SimpleNamespace(
                cohort_id=cohort_id,
                cancer="melanoma",
                endpoint_families=("orr",),
                uniform_drug_class=None,
            ),
            clinical_rows=[
                {"raw_orr": "CR", "endpoint_definition": "ORR RECIST CR PR SD PD",
                 "drug_class_normalised": "ANTI_PD_L1_AXIS"}
            ],
        )
        cases = (
            ("study_effects_input", [
                {"patient_row": 0, "unit": "GENE_X", "value": 1.0},
            ]),
            ("feature_bundle", SimpleNamespace(
                cohort_id=cohort_id,
                unit_family="gene",
                values_by_unit={"GENE_X": [1.0]},
                coverage={},
                metadata={},
            )),
        )

        with TemporaryDirectory() as temporary:
            for index, (manifest_kind, features) in enumerate(cases):
                with self.subTest(manifest_kind=manifest_kind):
                    manifest = Path(temporary) / f"synthetic-{index}.json"
                    if manifest_kind == "study_effects_input":
                        write_synthetic_fixture_manifest(
                            manifest,
                            kind=manifest_kind,
                            payload=effect_input_payload(normal_view, features),
                            cohort_ids=(cohort_id,),
                        )
                    else:
                        expected_hash = canonical_sha256(effect_input_payload(normal_view, features))
                        manifest.write_text(json.dumps({
                            "manifest_version": 1,
                            "producer": SYNTHETIC_FIXTURE_PRODUCER,
                            "data_classification": "synthetic",
                            "kind": manifest_kind,
                            "cohort_ids": [cohort_id],
                            "effect_input_sha256": {"gene": expected_hash},
                        }))

                    view = _ClinicalReadSentinel(
                        metadata=normal_view.metadata,
                        data_classification="real",
                    )
                    with patch.object(a_meta_provenance, "canonical_sha256", wraps=canonical_sha256) as hasher:
                        with self.assertRaisesRegex(ValueError, "Real-cohort effects are restricted"):
                            study_effects(
                                view,
                                features,
                                "orr",
                                by_drug_class=False,
                                provenance_manifest=manifest,
                            )
                        self.assertEqual(view.clinical_reads, 0)
                        hasher.assert_not_called()

    def _synthetic_manifest(self, root: Path, cohort_id: str) -> Path:
        manifest_path = root / cohort_id / "features" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps({
            "data_classification": "synthetic",
            "cohort_ids": [cohort_id],
            "kind": "feature_bundle",
            "producer": "invented-test-only",
        }))
        return manifest_path

    def test_known_real_cohort_cannot_bypass_outcome_lock_with_synthetic_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._synthetic_manifest(root, "liu2019")
            with patch.object(a_meta_cli, "cohort_view") as source_loader:
                with self.assertRaisesRegex(SystemExit, "Real-cohort effects require"):
                    a_meta_cli.main(["effects", "--cohort", "liu2019", "--results", str(root)])
            source_loader.assert_not_called()

    def test_final_test_lock_precedes_source_access_even_with_synthetic_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._synthetic_manifest(root, "imvigor210")
            with patch.object(a_meta_cli, "cohort_view") as source_loader:
                with self.assertRaisesRegex(SystemExit, "locked final test"):
                    a_meta_cli.main(["effects", "--cohort", "imvigor210", "--results", str(root)])
            source_loader.assert_not_called()
