from __future__ import annotations

import csv
import hashlib
import json
import re
import unittest
from pathlib import Path

try:
    from jsonschema.validators import validator_for
except Exception:  # pragma: no cover
    validator_for = None

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "specs" / "A_DATA_ACQUISITION_VALIDATION"

CORE_DOCS = [
    "README.md",
    "A_DATA_ACQUISITION_VALIDATION_APPRAISAL.md",
    "SCOPE_AND_INTERFACES.md",
    "PROTOCOL_CROSSWALK.md",
    "SOURCE_DISCOVERY_STRATEGY.md",
    "AGENTIC_SEARCH_ARCHITECTURE.md",
    "PROCESSED_DATA_POLICY.md",
    "SOURCE_IDENTITY_AND_DEDUPLICATION.md",
    "PATIENT_DATA_MODEL.md",
    "ENDPOINT_ONTOLOGY.md",
    "TREATMENT_AND_TIMEPOINT_ONTOLOGY.md",
    "ASSAY_AND_MEASUREMENT_CONTRACT.md",
    "MULTIOMICS_PAIRING_CONTRACT.md",
    "PATIENT_MATRIX_CONTRACT.md",
    "LONGITUDINAL_PAIRING_CONTRACT.md",
    "COHORT_ADMISSION_AND_RELEASE.md",
    "VALIDATION_FRAMEWORK.md",
    "SPLIT_AND_PRIOR_EXPOSURE_VALIDATION.md",
    "ACCESS_PRIVACY_AND_REDISTRIBUTION.md",
    "IMPLEMENTATION_RECONCILIATION.md",
    "SOFTWARE_ARCHITECTURE.md",
    "TICKETS_AND_TESTS.md",
    "REPRODUCE_AND_READINESS.md",
    "DECISION_LOG.md",
    "UNRESOLVED_QUESTIONS.md",
]
SCHEMAS = [
    "source_record.schema.json",
    "study_registry.schema.json",
    "publication_family.schema.json",
    "patient_registry.schema.json",
    "treatment_exposure.schema.json",
    "specimen_registry.schema.json",
    "assay_registry.schema.json",
    "clinical_outcome.schema.json",
    "overlap_edge.schema.json",
    "cohort_admission_receipt.schema.json",
    "matrix_build_receipt.schema.json",
    "validation_receipt.schema.json",
]
TEMPLATES = [
    "search_log.tsv",
    "study_registry.tsv",
    "publication_family_registry.tsv",
    "source_object_registry.tsv",
    "study_alias_crosswalk.tsv",
    "overlap_edges.tsv",
    "prior_exposure_ledger.tsv",
    "branch_admission_registry.tsv",
    "source_gap_register.tsv",
    "feature_coverage.tsv",
    "split_registry.tsv",
    "analysis_membership.tsv",
]
MATRICES = [
    "BASELINE_PATIENT_MATRIX.md",
    "PATIENT_TIMEPOINT_LONG.md",
    "LONGITUDINAL_PAIR_MATRIX.md",
    "ENDPOINT_MATRIX.md",
    "ASSAY_FEATURE_COVERAGE.md",
    "SPLIT_REGISTRY.md",
    "ANALYSIS_MEMBERSHIP.md",
]
PROMPTS = [
    "catalogue_resolution.md",
    "publication_and_supplement_search.md",
    "repository_object_discovery.md",
    "longitudinal_study_search.md",
    "multiomics_source_search.md",
    "overlap_and_alias_audit.md",
    "controlled_access_search.md",
    "novelty_and_method_overlap.md",
]


class SpecKitTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for name in CORE_DOCS:
            self.assertTrue((PKG / name).is_file(), name)
        for name in SCHEMAS:
            self.assertTrue((PKG / "schemas" / name).is_file(), name)
        for name in TEMPLATES:
            self.assertTrue((PKG / "templates" / name).is_file(), name)
        for name in MATRICES:
            self.assertTrue((PKG / "matrices" / name).is_file(), name)
        for name in PROMPTS:
            self.assertTrue((PKG / "agent_prompts" / name).is_file(), name)

    def test_json_schemas_are_draft_2020_12_and_self_validating(self) -> None:
        for name in SCHEMAS:
            path = PKG / "schemas" / name
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(data.get("type"), "object")
            self.assertIsInstance(data.get("required"), list)
            self.assertGreater(len(data["required"]), 0)
            self.assertIn("additionalProperties", data)
            if validator_for is not None:
                validator_for(data).check_schema(data)

    def test_tsv_templates_have_unique_nonempty_headers_and_no_records(self) -> None:
        for name in TEMPLATES:
            path = PKG / "templates" / name
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))
            self.assertEqual(len(rows), 1, f"{name} must be header-only")
            header = rows[0]
            self.assertTrue(all(header), name)
            self.assertEqual(len(header), len(set(header)), name)

    def test_matrix_contracts_define_grain_invariants_and_receipt(self) -> None:
        for name in MATRICES:
            text = (PKG / "matrices" / name).read_text(encoding="utf-8")
            self.assertRegex(text, r"(?i)row grain")
            self.assertRegex(text, r"(?i)invariant")
            self.assertRegex(text, r"(?i)receipt")
            self.assertRegex(text, r"(?i)fail")

    def test_agent_prompts_are_read_only_and_structured(self) -> None:
        for name in PROMPTS:
            text = (PKG / "agent_prompts" / name).read_text(encoding="utf-8")
            self.assertRegex(text, r"(?i)read-only")
            self.assertRegex(text, r"(?i)source locator")
            self.assertRegex(text, r"(?i)structured output")
            self.assertRegex(text, r"(?i)canonical registr")
            self.assertRegex(text, r"(?i)unknown")

    def test_readme_and_decisions_keep_analysis_blocked(self) -> None:
        readme = (PKG / "README.md").read_text(encoding="utf-8")
        self.assertIn("No cohort is admitted", readme)
        self.assertIn("Implementation completion is separate", readme)
        decisions = (PKG / "DECISION_LOG.md").read_text(encoding="utf-8")
        for decision_id in [f"D{i:02d}" for i in range(1, 11)]:
            self.assertIn(decision_id, decisions)
            self.assertRegex(decisions, rf"(?s){decision_id}.*?APPROVED")

    def test_required_mermaid_diagrams_exist(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in PKG.glob("*.md"))
        self.assertGreaterEqual(text.count("```mermaid"), 5)
        for phrase in [
            "Source discovery and admission",
            "Normalized data model",
            "Baseline matrix flow",
            "Longitudinal matrix flow",
            "Validation gates",
        ]:
            self.assertIn(phrase, text)

    def test_protocol_and_reconciliation_tables_are_substantive(self) -> None:
        with (PKG / "protocol_crosswalk.tsv").open(encoding="utf-8") as handle:
            protocol = list(csv.DictReader(handle, delimiter="\t"))
        with (PKG / "implementation_reconciliation.tsv").open(encoding="utf-8") as handle:
            reconciliation = list(csv.DictReader(handle, delimiter="\t"))
        self.assertGreaterEqual(len(protocol), 15)
        self.assertGreaterEqual(len(reconciliation), 20)
        self.assertIn("status", protocol[0])
        self.assertIn("disposition", reconciliation[0])

    def test_manifest_hashes_match(self) -> None:
        manifest_path = PKG / "SPEC_KIT_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["files"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, item["sha256"], item["path"])

    def test_no_obvious_secrets_or_patient_records_in_public_package(self) -> None:
        forbidden = re.compile(r"(?i)(api[_-]?key\s*=|bearer\s+[A-Za-z0-9._-]{20,}|signed_url=|password\s*=)")
        for path in PKG.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".tsv"}:
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(forbidden.search(text), str(path))
        patient_template = PKG / "schemas" / "patient_registry.schema.json"
        self.assertIn("private", patient_template.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
