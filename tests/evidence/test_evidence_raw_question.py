import json
from pathlib import Path

import pytest

from tools.a_dav.raw_question import build_raw_question


ROOT = Path(__file__).resolve().parents[2]
SOURCE_OBJECT_RECORDS = (
    ROOT / "docs/validation/A_DAV_05/SOURCE_OBJECT_RECORDS.json"
)


def load_source_object_records():
    return json.loads(SOURCE_OBJECT_RECORDS.read_text(encoding="utf-8"))


def s02_filelist_record():
    return {
        "study_id": "QR-GSE188249",
        "access_route": "PUBLIC_DIRECT",
        "exact_file_name": "filelist.txt",
    }


def test_real_records_classify_s02_and_s03_without_resolving_matrix_question():
    result = build_raw_question(load_source_object_records())

    assert result["schema_version"] == 1
    assert result["admitted_count"] == 0
    assert result["analysis_ready"] is False
    assert result["decisions"] == []
    questions = {record["entry_id"]: record for record in result["questions"]}
    assert set(questions) == {"S02", "S03"}
    assert questions["S02"]["series_accessions"] == ["GSE188249", "GSE188250"]
    assert questions["S03"]["series_accessions"] == ["GSE198052"]
    assert questions["S02"]["file_name_class_counts"] == {
        "RAW_ARCHIVE": 2,
        "FILELIST": 2,
        "MATRIX_NAME": 0,
    }
    assert questions["S03"]["file_name_class_counts"] == {
        "RAW_ARCHIVE": 1,
        "FILELIST": 1,
        "MATRIX_NAME": 0,
    }
    assert questions["S02"]["matrix_name_present"] is False
    assert questions["S03"]["matrix_name_present"] is False






