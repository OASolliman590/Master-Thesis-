"""Spec 009 / T004 — Stage 00 GEO accession parsing helpers.

FR-008 (edge case 2): exercises `_extract_geo_accession_from_cohort_id` and
`_geo_series_prefix`. Both functions exist today in `src/pipeline/cli.py` (L583,
L619) and are slated to move into `pipeline.modules.00_retrieval.geo` during
the M3 extraction. Tests target the future module via importlib so they:

- FAIL with ModuleNotFoundError before M3 (no module yet), and
- PASS after M3 once the helpers are re-exported from the stage module.

If the helpers' behavior regresses during extraction, these tests catch it.
"""
from __future__ import annotations

import importlib

import pytest

STAGE_MODULE = "pipeline.modules.00_retrieval.geo"


def _load_geo():
    return importlib.import_module(STAGE_MODULE)


def test_extract_geo_accession_from_cohort_id_canonical() -> None:
    geo = _load_geo()
    assert geo._extract_geo_accession_from_cohort_id("gse91061_melanoma_pd1") == "GSE91061"


def test_extract_geo_accession_from_cohort_id_handles_uppercase() -> None:
    geo = _load_geo()
    assert geo._extract_geo_accession_from_cohort_id("GSE91061_melanoma_pd1") == "GSE91061"


def test_extract_geo_accession_from_cohort_id_returns_empty_for_no_prefix() -> None:
    geo = _load_geo()
    assert geo._extract_geo_accession_from_cohort_id("erp105482_unified") == ""


@pytest.mark.parametrize(
    "gse_id, expected_prefix",
    [
        ("GSE91061", "GSE91nnn"),
        ("GSE100797", "GSE100nnn"),
        ("GSE305240", "GSE305nnn"),
        ("GSE12345", "GSE12nnn"),
    ],
)
def test_geo_series_prefix_canonical(gse_id: str, expected_prefix: str) -> None:
    geo = _load_geo()
    assert geo._geo_series_prefix(gse_id) == expected_prefix


def test_geo_series_prefix_short_gse_edge_case() -> None:
    """Edge case: GSE99 (2-digit) — current `_geo_series_prefix` truncates last
    3 chars, yielding "nnn" not "GSEnnn". The fix must either special-case
    short GSEs or return a value that round-trips to the real NCBI URL.
    """
    geo = _load_geo()
    result = geo._geo_series_prefix("GSE99")
    # Acceptance: the result must start with "GSE" (not be just "nnn").
    assert result.startswith("GSE"), (
        f"_geo_series_prefix('GSE99') returned '{result}'; should start with 'GSE'"
    )
