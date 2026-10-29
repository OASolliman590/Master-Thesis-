"""Preparation entry point tests use invented packets and local temporary outputs only."""
from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import pytest

from tools.a_dav.core import DavError, ENTITY_TABLES, SchemaStore
from tools.a_dav.demo import synthetic_workflow_packet
from tools.a_dav.review_prepare import prepare_review
from tools.a_dav.worksheet import build_worksheet


def output_path() -> Path:
    from tools.a_dav.ingest import REPO_ROOT
    return REPO_ROOT / ".scratch" / "runtime" / ("test-review-prepare-" + uuid.uuid4().hex)


@pytest.fixture
def output_dir():
    path = output_path()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_rebuild_discards_old_receipts_and_derivations_and_refreshes_unsigned_context(output_dir: Path):
    packet = synthetic_workflow_packet()
    packet["dependencies"] = {"registries": {"receipt_id": "f" * 64, "status": "READY"}}
    packet["records"]["endpoint"] = [{"row_type": "ENDPOINT", "endpoint_id": "STALE"}]
    packet["config"].setdefault("admission", {})["reviewer_worksheet"] = {
        "signature": {"reviewer_name": "Old Reviewer", "review_date": "2026-01-01"}}
    packet["config"]["endpoints"] = {"version": "new-policy-v2", "classes": [], "category_map": {}}
    first = prepare_review(packet, output_dir)

    assert first["packet"]["dependencies"]["registries"]["receipt_id"] != "f" * 64
    assert "endpoint" not in first["packet"]["records"]
    assert set(first["packet"]["records"]) <= ENTITY_TABLES | {"coverage"}
    assert "signature" not in first["worksheet"]
    regenerated = build_worksheet(first["packet"])
    assert {k: v for k, v in first["worksheet"].items() if k != "created_utc"} == {
        k: v for k, v in regenerated.items() if k != "created_utc"}
    assert first["summary"]["source_admission"] is False
    assert first["summary"]["matrix_construction"] is False

    changed = copy.deepcopy(packet)
    changed["config"]["endpoints"]["version"] = "new-policy-v3"
    second = prepare_review(changed, output_dir)
    assert second["worksheet"]["context_hash"] != first["worksheet"]["context_hash"]
    assert second["worksheet"] == build_worksheet(second["packet"])
    saved = json.loads((output_dir / "reviewer_worksheet.json").read_text())
    assert saved == second["worksheet"]


def test_incomplete_metadata_evidence_stays_blocked_and_summary_has_no_patient_values(output_dir: Path):
    packet = synthetic_workflow_packet()
    packet["config"].pop("endpoints", None)
    packet["config"].pop("timing", None)
    result = prepare_review(packet, output_dir)
    stages = {row["stage"]: row for row in result["summary"]["stages"]}
    assert stages["registries"]["status"] == "READY"
    assert stages["endpoints"]["status"] == "BLOCKED_UNKNOWN"
    assert stages["timing"]["status"] == "BLOCKED_UNKNOWN"
    assert result["summary"]["source_admission"] is False
    summary_text = json.dumps(result["summary"])
    assert "p1" not in summary_text
    assert "sample-001" not in summary_text


def test_outputs_must_stay_under_private_runtime_boundary():
    packet = synthetic_workflow_packet()
    with pytest.raises(DavError, match="OUTPUT_PATH_NOT_ALLOWED"):
        prepare_review(packet, Path("/private/tmp/review-prepare-outside"), schemas=SchemaStore())


def test_missing_registry_evidence_stops_all_dependent_stages(output_dir: Path):
    packet: dict[str, Any] = synthetic_workflow_packet()
    packet["records"]["source_record"] = []
    result = prepare_review(packet, output_dir)
    assert [row["stage"] for row in result["summary"]["stages"]] == ["registries"]
    assert result["summary"]["stages"][0]["status"] == "BLOCKED_UNKNOWN"
    assert result["packet"]["dependencies"] == {}
