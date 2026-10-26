import json
from collections import Counter
from pathlib import Path

import pytest

from tools.a_dav.metadata_queue import build_metadata_queue


ROOT = Path(__file__).resolve().parents[2]
CROSSWALK = ROOT / "docs/validation/A_DAV_06/LANE_CROSSWALK.json"
PINNED = {"ICB-BULK-003", "ICB-BULK-009", "S01"}


def load_crosswalk():
    return json.loads(CROSSWALK.read_text(encoding="utf-8"))


def synthetic_crosswalk(rows):
    return {"lanes": {"I": rows, "E": []}}


def test_real_crosswalk_emits_expected_offline_queue():
    result = build_metadata_queue(load_crosswalk())
    records = result["queue"]

    assert result["schema_version"] == 1
    assert result["admitted_count"] == 0
    assert result["analysis_ready"] is False
    assert result["decisions"] == []
    assert len(records) == 22
    assert {record["entry_id"] for record in records}.isdisjoint(PINNED)
    assert Counter(record["queue_class"] for record in records) == {
        "PUBLIC_GEO_FILELIST": 11,
        "CONTROLLED_LANDING_ONLY": 5,
        "NO_PUBLIC_ACCESSION": 3,
        "RAW_QUESTION": 2,
        "NON_GEO_PUBLIC": 1,
    }
    assert all(
        set(record) == {"entry_id", "lane", "queue_class", "public_series_accessions"}
        for record in records
    )


def test_rows_sharing_accessions_are_preserved_independently():
    records = build_metadata_queue(load_crosswalk())["queue"]
    by_id = {record["entry_id"]: record for record in records}

    assert by_id["ICB-BULK-004"]["public_series_accessions"] == ["GSE93157"]
    assert by_id["ICB-BULK-005"]["public_series_accessions"] == ["GSE93157"]
    assert by_id["ICB-BULK-006"]["public_series_accessions"] == ["GSE93157"]
    assert by_id["ICB-BULK-014"]["queue_class"] == "CONTROLLED_LANDING_ONLY"
    assert by_id["ICB-BULK-042"]["queue_class"] == "CONTROLLED_LANDING_ONLY"





