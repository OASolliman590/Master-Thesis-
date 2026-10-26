from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.a_identity_adapter.core import AdapterError, build_packet, canonical_bytes


def bundle() -> dict:
    source = {"source_id": "SRC:0007", "sha256": "a" * 64, "classification": "SYNTHETIC_ONLY"}
    return {
        "schema_version": "a_identity_adapter.v1",
        "data_classification": "SYNTHETIC_ONLY",
        "run_id": "run:001",
        "selection_policy_id": "SYNTHETIC-FOLLOWUP-v1",
        "assay_routes": {"rna_bulk": {"modality": "RNA", "known": True}},
        "followup_windows": [{"window_id": "win:early", "min_day": 1, "max_day": 30}],
        "sources": [source],
        "studies": [
            {"study_id": "STUDY:001", "source_id": source["source_id"], "raw_study_id": "GSE0007", "family_id": "FAM:DEV"},
            {"study_id": "STUDY:002", "source_id": source["source_id"], "raw_study_id": "GSE0008", "family_id": "FAM:TEST"},
        ],
        "families": [
            {"family_id": "FAM:DEV", "role": "DEVELOPMENT", "source_id": source["source_id"]},
            {"family_id": "FAM:TEST", "role": "FINAL_TEST", "source_id": source["source_id"]},
        ],
        "patients": [
            {"patient_id": "PAT:001", "study_id": "STUDY:001", "raw_patient_id": "0007", "family_id": "FAM:DEV"},
            {"patient_id": "PAT:002", "study_id": "STUDY:002", "raw_patient_id": "0008", "family_id": "FAM:TEST"},
        ],
        "episodes": [
            {"episode_id": "EP:001", "patient_id": "PAT:001", "sequence": 1, "regimen_id": "REG:A", "raw_regimen_label": "Therapy A", "start_day": 0, "end_day": 45, "source_id": source["source_id"]},
            {"episode_id": "EP:002", "patient_id": "PAT:001", "sequence": 2, "regimen_id": "REG:B", "raw_regimen_label": "Therapy B", "start_day": 46, "end_day": 100, "source_id": source["source_id"]},
            {"episode_id": "EP:003", "patient_id": "PAT:002", "sequence": 1, "regimen_id": "REG:C", "raw_regimen_label": "Therapy C", "start_day": 0, "end_day": 50, "source_id": source["source_id"]},
        ],
        "specimens": [
            {"specimen_id": "SP:BASE", "raw_specimen_id": "000100", "patient_id": "PAT:001", "episode_id": "EP:001", "timing": "PRE_INDEX_BASELINE", "relative_day": -7, "timing_precision": "EXACT", "source_id": source["source_id"], "family_id": "FAM:DEV", "protected": False},
            {"specimen_id": "SP:FU2", "raw_specimen_id": "000102", "patient_id": "PAT:001", "episode_id": "EP:001", "timing": "EARLY_ON_TREATMENT", "relative_day": 21, "timing_precision": "EXACT", "source_id": source["source_id"], "family_id": "FAM:DEV", "protected": False, "window_id": "win:early", "selection_priority": 2},
            {"specimen_id": "SP:FU1", "raw_specimen_id": "000101", "patient_id": "PAT:001", "episode_id": "EP:001", "timing": "EARLY_ON_TREATMENT", "relative_day": 14, "timing_precision": "EXACT", "source_id": source["source_id"], "family_id": "FAM:DEV", "protected": False, "window_id": "win:early", "selection_priority": 1},
            {"specimen_id": "SP:TEST", "raw_specimen_id": "000200", "patient_id": "PAT:002", "episode_id": "EP:003", "timing": "PRE_INDEX_BASELINE", "relative_day": -5, "timing_precision": "EXACT", "source_id": source["source_id"], "family_id": "FAM:TEST", "protected": True},
        ],
        "assays": [
            {"assay_id": "AS:BASE", "raw_assay_id": "000300", "specimen_id": "SP:BASE", "route": "rna_bulk", "source_id": source["source_id"]},
            {"assay_id": "AS:FU2", "raw_assay_id": "000302", "specimen_id": "SP:FU2", "route": "rna_bulk", "source_id": source["source_id"]},
            {"assay_id": "AS:FU1", "raw_assay_id": "000301", "specimen_id": "SP:FU1", "route": "rna_bulk", "source_id": source["source_id"]},
            {"assay_id": "AS:TEST", "raw_assay_id": "000400", "specimen_id": "SP:TEST", "route": "rna_bulk", "source_id": source["source_id"]},
        ],
        "outcomes": [
            {"outcome_id": "OUT:001", "patient_id": "PAT:001", "episode_id": "EP:001", "raw_response": None, "canonical_response": "UNKNOWN", "orr": None, "source_id": source["source_id"]},
            {"outcome_id": "OUT:002", "patient_id": "PAT:001", "episode_id": "EP:002", "raw_response": "PR", "canonical_response": "PR", "orr": 1, "source_id": source["source_id"]},
        ],
        "episode_bindings": [
            {"binding_id": "BIND:SP:BASE", "patient_id": "PAT:001", "episode_id": "EP:001", "subject_type": "SPECIMEN", "subject_id": "SP:BASE", "role": "PRE_INDEX_BASELINE", "binding_status": "VERIFIED", "source_locators": ["fixture://SP:BASE"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
            {"binding_id": "BIND:SP:FU2", "patient_id": "PAT:001", "episode_id": "EP:001", "subject_type": "SPECIMEN", "subject_id": "SP:FU2", "role": "ON_TREATMENT", "binding_status": "VERIFIED", "source_locators": ["fixture://SP:FU2"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
            {"binding_id": "BIND:SP:FU1", "patient_id": "PAT:001", "episode_id": "EP:001", "subject_type": "SPECIMEN", "subject_id": "SP:FU1", "role": "ON_TREATMENT", "binding_status": "VERIFIED", "source_locators": ["fixture://SP:FU1"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
            {"binding_id": "BIND:SP:TEST", "patient_id": "PAT:002", "episode_id": "EP:003", "subject_type": "SPECIMEN", "subject_id": "SP:TEST", "role": "PRE_INDEX_BASELINE", "binding_status": "VERIFIED", "source_locators": ["fixture://SP:TEST"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
            {"binding_id": "BIND:OUT:001", "patient_id": "PAT:001", "episode_id": "EP:001", "subject_type": "CLINICAL_OUTCOME", "subject_id": "OUT:001", "role": "OUTCOME_ASSESSMENT", "binding_status": "VERIFIED", "source_locators": ["fixture://OUT:001"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
            {"binding_id": "BIND:OUT:002", "patient_id": "PAT:001", "episode_id": "EP:002", "subject_type": "CLINICAL_OUTCOME", "subject_id": "OUT:002", "role": "OUTCOME_ASSESSMENT", "binding_status": "VERIFIED", "source_locators": ["fixture://OUT:002"], "reviewer": "synthetic_fixture", "reviewed_utc": "2026-10-16T00:00:00Z"},
        ],
        "exclusions": [],
    }














































def test_saved_synthetic_fixture_reproduces_saved_output_hashes() -> None:
    fixture_path = ROOT / "tests/a_identity_adapter/fixtures/a_dav_01_synthetic_input.json"
    saved = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = build_packet(saved)
    output_path = ROOT / "docs/validation/A_DAV_01/synthetic_outputs.json"
    saved_outputs = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["outputs"] == saved_outputs
    assert hashlib.sha256(canonical_bytes(saved_outputs)).hexdigest() == result["receipt"]["output_sha256"]

