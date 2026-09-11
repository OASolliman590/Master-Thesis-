"""Spec 009 / T006 — Stage 00 failure taxonomy.

FR-005: failures must be classified into a fixed `ErrorClass` vocabulary and
`retrieval_note` must format as `<accession>:<file_kind>:<error_class>[:<detail>]`.

This test currently FAILS because:
1. `ErrorClass` enum does not exist (planned in M4 / T023).
2. `_download_url` returns string `err` like `"http_404"`, not an `ErrorClass`.
3. `retrieval_note` is currently free-text from cli.py L1346-L1349.
"""
from __future__ import annotations

import importlib
from urllib.error import HTTPError

import pytest


STAGE_ERRORS_MODULE = "pipeline.modules.00_retrieval.errors"
STAGE_HTTP_MODULE = "pipeline.modules.00_retrieval.http"


def _load_errors():
    return importlib.import_module(STAGE_ERRORS_MODULE)


def _load_http():
    return importlib.import_module(STAGE_HTTP_MODULE)


def test_error_class_enum_has_required_vocabulary() -> None:
    errors = _load_errors()
    required = {
        "http_404",
        "http_5xx",
        "http_other",
        "network_timeout",
        "empty_response",
        "parse_error",
        "manifest_error",
    }
    enum_values = {member.value for member in errors.ErrorClass}
    missing = required - enum_values
    assert not missing, f"ErrorClass missing required members: {missing}"


@pytest.mark.parametrize(
    "http_code, expected_class",
    [
        (404, "http_404"),
        (500, "http_5xx"),
        (502, "http_5xx"),
        (503, "http_5xx"),
        (429, "http_5xx"),  # NCBI rate-limit response
        (400, "http_other"),
        (418, "http_other"),
    ],
)
def test_classify_http_exception_maps_codes(http_code: int, expected_class: str) -> None:
    errors = _load_errors()
    exc = HTTPError(
        url="https://example.test/x",
        code=http_code,
        msg="test",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    result = errors.classify_http_exception(exc)
    assert result.value == expected_class


def test_retrieval_note_format_is_structured() -> None:
    """Format: '<accession>:<file_kind>:<error_class>[:<detail>]; ...'

    After M4 the note must parse deterministically; before M4 it's free-text.
    """
    stage = importlib.import_module("pipeline.modules.00_retrieval")
    note = stage.format_retrieval_note(
        [
            ("GSE123456", "suppl", "http_404", ""),
            ("SRP100001", "runinfo", "empty_response", "missing Run,"),
        ]
    )
    assert note == (
        "GSE123456:suppl:http_404; SRP100001:runinfo:empty_response:missing Run,"
    )
