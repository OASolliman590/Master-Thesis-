"""Reviewer worksheet behavior through the public worksheet and admission interfaces."""
from __future__ import annotations

from copy import deepcopy

import pytest

from tools.a_dav.core import BRANCHES
from tools.a_dav.worksheet import (build_worksheet, read_worksheet, validate_signed_worksheet,
                                   worksheet_status, write_worksheet)


def packet() -> dict:
    return {
        "classification": "PRIVATE_PATIENT_LEVEL",
        "branch_id": "A_BASELINE_BIO",
        "records": {
            "study_registry": [{"study_id": "study-demo", "publication_family_id": "family-demo"}],
            "source_record": [{"study_id": "study-demo", "source_object_id": "source-demo",
                               "sha256": "a" * 64, "access_route": "PUBLIC_DIRECT"}],
        },
        "config": {"admission": {"branch_policies": {}}},
        "dependencies": {},
    }


def signed(worksheet: dict) -> dict:
    result = deepcopy(worksheet)
    result["signature"] = {"reviewer_name": "Thesis Author", "review_date": "2026-10-25"}
    result["decisions"] = [
        {"item_id": item["item_id"], "status": "NOT_APPLICABLE" if item.get("gate") == "V8" else "PASS",
         "rationale": "Reviewed against the cited source."}
        for item in worksheet["items"]
    ]
    return result


def test_worksheet_merges_ingestion_items_and_all_nine_gates() -> None:
    p = packet()
    p["config"]["admission"]["ingestion_worksheet"] = {
        "classification": "PRIVATE_PATIENT_LEVEL", "status": "BLOCKED_UNKNOWN",
        "items": [{"category": "LABEL_AMBIGUITY", "status": "BLOCKED_UNKNOWN",
                   "evidence_pointers": [{"role": "clinical", "row": "invented-row-1"}],
                   "context": {"raw": "demo-label"}}],
    }
    worksheet = build_worksheet(p)
    assert worksheet["context"]["study_id"] == "study-demo"
    assert worksheet["context"]["branch_id"] == "A_BASELINE_BIO"
    assert {item["gate"] for item in worksheet["items"] if item.get("kind") == "gate"} == {
        f"V{i}" for i in range(9)
    }
    ingestion = next(item for item in worksheet["items"] if item.get("category") == "LABEL_AMBIGUITY")
    assert ingestion["evidence_pointers"] == [{"role": "clinical", "row": "invented-row-1"}]
    assert "source-demo" in str(worksheet["context"])


def test_signature_is_bound_to_exact_sources_branch_and_item_set() -> None:
    p = packet()
    worksheet = build_worksheet(p)
    assert validate_signed_worksheet(p, signed(worksheet))["reviewer_name"] == "Thesis Author"

    for mutate in (
        lambda value: value["records"]["source_record"][0].update(sha256="b" * 64),
        lambda value: value["records"].setdefault("patient_registry", []).append({"patient_uid": "invented-p2"}),
        lambda value: value.update(branch_id="A_P2_FINAL_TEST"),
        lambda value: value["config"]["admission"].update(branch_policies={"new": "context"}),
    ):
        changed = deepcopy(p)
        mutate(changed)
        with pytest.raises(ValueError, match="WORKSHEET_CONTEXT_MISMATCH"):
            validate_signed_worksheet(changed, signed(worksheet))


def test_unsigned_partial_and_contradictory_decisions_are_not_accepted() -> None:
    p = packet()
    worksheet = build_worksheet(p)
    unsigned = deepcopy(worksheet)
    with pytest.raises(ValueError, match="WORKSHEET_UNSIGNED"):
        validate_signed_worksheet(p, unsigned)

    partial = signed(worksheet)
    partial["decisions"].pop()
    with pytest.raises(ValueError, match="WORKSHEET_PARTIAL"):
        validate_signed_worksheet(p, partial)

    duplicate = signed(worksheet)
    duplicate["decisions"].append(deepcopy(duplicate["decisions"][0]))
    with pytest.raises(ValueError, match="WORKSHEET_CONTRADICTION"):
        validate_signed_worksheet(p, duplicate)


def test_controlled_source_requires_separate_source_reviewer_and_integrator() -> None:
    p = packet()
    p["records"]["source_record"][0]["access_route"] = "CONTROLLED"
    worksheet = build_worksheet(p)
    with pytest.raises(ValueError, match="CONTROLLED_REVIEWERS_REQUIRED"):
        validate_signed_worksheet(p, signed(worksheet))

    reviewed = signed(worksheet)
    reviewed["signature"].update(source_reviewer_name="Source Reviewer", source_review_date="2026-10-25",
                                  integrator_name="Integrator", integration_date="2026-10-25")
    assert validate_signed_worksheet(p, reviewed)["integrator_name"] == "Integrator"

    p["records"]["source_record"][0]["access_route"] = "UNKNOWN"
    with pytest.raises(ValueError, match="CONTROLLED_REVIEWERS_REQUIRED"):
        validate_signed_worksheet(p, signed(build_worksheet(p)))


def test_public_read_write_and_status_interfaces(tmp_path) -> None:
    p = packet()
    path = tmp_path / "worksheet.json"
    with pytest.raises(ValueError, match="OUTPUT_PATH_NOT_ALLOWED"):
        write_worksheet(p, path)
    written = write_worksheet(p, path, allow_external_out=True)
    loaded = read_worksheet(path)
    assert loaded == written
    assert worksheet_status(p, loaded) == "UNSIGNED"
    assert worksheet_status(p, signed(loaded)) == "SIGNED"
    assert validate_signed_worksheet(p, signed(loaded))["signer_identity_status"] == "SELF_REPORTED"
