from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
REV = ROOT / "specs" / "C" / "revision_20261015"

REQUIRED_FILES = [
    ROOT / "docs/decisions/C_FRAMEWORK_20261015.md",
    ROOT / "docs/research/C_SCIENTIFIC_REVISION_20261015.md",
    ROOT / "docs/plans/2026-10-15-paper-c-scientific-revision.md",
    ROOT / "CONTEXT.md",
    ROOT / "specs/C/README.md",
    REV / "README.md",
    REV / "SCIENTIFIC_SCOPE.md",
    REV / "PROTOCOL_CROSSWALK.md",
    REV / "NOVELTY.md",
    REV / "DATA_SOURCE_CONTRACT.md",
    REV / "QUERY_HANDOFF.md",
    REV / "DRUG_UNIVERSE.md",
    REV / "ANALYSIS_CONTRACT.md",
    REV / "SCORER_CONTRACT.md",
    REV / "EXPOSURE_CONTEXT.md",
    REV / "VALIDATION_ARCHITECTURE.md",
    REV / "PHARMACOLOGY.md",
    REV / "EVIDENCE_INTEGRATION.md",
    REV / "WETLAB_HANDOFF.md",
    REV / "FIGURES.md",
    REV / "SOFTWARE_ARCHITECTURE.md",
    REV / "IMPLEMENTATION_READINESS.md",
    REV / "UNRESOLVED_QUESTIONS.md",
    REV / "PREREGISTRATION_DECISIONS.md",
    REV / "REFERENCES.md",
    REV / "manifests/decision_register.tsv",
    REV / "manifests/source_roles.tsv",
    REV / "tickets/IMPLEMENTATION_TICKETS.md",
]

SCHEMA_FIXTURE_PAIRS = [
    (REV / "schemas/query_handoff.schema.json", REV / "fixtures/query_handoff.example.json"),
    (REV / "schemas/source_record.schema.json", REV / "fixtures/source_record.example.json"),
    (REV / "schemas/candidate_evidence.schema.json", REV / "fixtures/candidate_evidence.example.json"),
]

EXISTING_REPO_PATHS = {
    "docs/decisions/AB_IMMUNE_BARRIERS_20260911.md",
    "docs/research/C_novelty_comparison.md",
    "docs/research/C_lincs2020_readiness.md",
    "docs/research/C_GSE199800_IDENTITY.md",
    "docs/research/C_pharmacology_contracts.md",
    "specs/B/revision_20260928",
    "specs/C/DATA.md",
    "specs/C/ANALYSIS.md",
    "specs/C/VALIDATION_AND_FIGURES.md",
    "specs/C/ENGINEERING.md",
    "specs/C/PREREGISTRATION.md",
    "specs/C/references.bib",
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class PaperCRevisionContractTests(unittest.TestCase):
    def test_required_package_files_exist_and_are_nonempty(self) -> None:
        missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.is_file()]
        self.assertEqual(missing, [])
        empty = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if path.stat().st_size == 0]
        self.assertEqual(empty, [])

    def test_json_schemas_are_valid_and_examples_conform(self) -> None:
        for schema_path, fixture_path in SCHEMA_FIXTURE_PAIRS:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            errors = sorted(Draft202012Validator(schema).iter_errors(fixture), key=lambda err: list(err.path))
            self.assertEqual([error.message for error in errors], [], schema_path.name)
            self.assertFalse(schema.get("additionalProperties", True), schema_path.name)

    def test_decision_register_records_approved_framework_and_unfrozen_primary(self) -> None:
        rows = read_tsv(REV / "manifests/decision_register.tsv")
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        status = {row["decision_id"]: row["status"] for row in rows}
        self.assertEqual(status["C-D001"], "approved_framework")
        self.assertEqual(status["C-D002"], "proposed_not_frozen")
        self.assertEqual(status["C-D003"], "secondary_calibration")
        self.assertEqual(status["C-D007"], "no_run_authorization")

    def test_source_manifest_keeps_roles_and_unknown_counts_explicit(self) -> None:
        rows = read_tsv(REV / "manifests/source_roles.tsv")
        ids = [row["source_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(rows), 15)
        allowed_statuses = {
            "blocked_pending_A_release", "blocked_pending_B_release", "metadata_ready_matrix_blocked",
            "blocked_control_join", "candidate_admission", "metadata_unresolved", "conditional_release",
            "optional", "secondary_only", "restricted_role", "access_conditional", "shortlist_only",
            "planned_not_executed", "future_separate",
        }
        self.assertTrue(all(row["status"] in allowed_statuses for row in rows))
        self.assertTrue(all(row["verified_n"] in {"UNKNOWN", "metadata_audited", "0"} for row in rows))
        paper_d = next(row for row in rows if row["source_id"] == "C-S019")
        self.assertEqual(paper_d["role"], "separate_prediction")
        self.assertIn("cannot count", paper_d["blocker_or_limit"])

    def test_primary_contract_is_paired_and_uses_biological_units(self) -> None:
        text = (REV / "ANALYSIS_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("D_i = S_i(Q_M) - S_i(Q_E)", text)
        self.assertIn("Delta_Q = mean_s(delta_s)", text)
        self.assertIn("independent biological replicate", text)
        self.assertIn("Genes, cells, wells, technical replicates and collapsed signatures are not independent units", text)
        self.assertIn("fewer than three independent originating studies", text)
        self.assertIn("It cannot establish comparative drug efficacy", text)

    def test_query_contract_requires_equal_budgets_and_no_padding(self) -> None:
        text = (REV / "QUERY_HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("same quota `k[p,d]`", text)
        self.assertIn("It is not padded with unsupported genes", text)
        self.assertIn("C perturbation effects may not alter B query membership", text)
        self.assertIn("must not be manufactured", text)

    def test_c1_is_secondary_and_not_comparative_efficacy(self) -> None:
        decision = (ROOT / "docs/decisions/C_FRAMEWORK_20261015.md").read_text(encoding="utf-8")
        scorer = (REV / "SCORER_CONTRACT.md").read_text(encoding="utf-8")
        pointer = (ROOT / "specs/C/README.md").read_text(encoding="utf-8")
        self.assertIn("C1 is demoted to secondary calibration", decision)
        self.assertIn("No treatment-superiority p-value", scorer)
        self.assertIn("C1 secondary calibration", pointer)

    def test_package_contains_no_biological_completion_claim(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED_FILES if path.suffix == ".md")
        forbidden = [
            "biological_validation=true",
            "primary_frozen=true",
            "production_ready=true",
            "ICI sensitisation is demonstrated",
            "winning drug is",
        ]
        for token in forbidden:
            self.assertNotIn(token, combined)
        readme = (REV / "README.md").read_text(encoding="utf-8")
        self.assertIn("NO BIOLOGICAL RUN AUTHORIZATION", readme)

    def test_relative_markdown_links_resolve_or_are_known_existing_paths(self) -> None:
        scan_paths = [path for path in REQUIRED_FILES if path.suffix == ".md"]
        unresolved: list[str] = []
        for path in scan_paths:
            text = path.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                target = raw_target.split("#", 1)[0].strip()
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (path.parent / target).resolve()
                if resolved.exists():
                    continue
                try:
                    repo_relative = resolved.relative_to(ROOT).as_posix()
                except ValueError:
                    unresolved.append(f"{path.relative_to(ROOT)} -> {raw_target}")
                    continue
                if repo_relative not in EXISTING_REPO_PATHS:
                    unresolved.append(f"{path.relative_to(ROOT)} -> {raw_target}")
        self.assertEqual(unresolved, [])

    def test_unresolved_register_has_no_closed_scientific_unknowns(self) -> None:
        rows = read_tsv(REV / "manifests/decision_register.tsv")
        self.assertFalse(any(row["decision_id"].startswith("C-U") for row in rows))
        unresolved = (REV / "UNRESOLVED_QUESTIONS.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(unresolved.count("| C-U"), 16)
        self.assertNotIn("| CLOSED |", unresolved)


if __name__ == "__main__":
    unittest.main()
