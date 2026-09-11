"""Spec 009 / T005 — Stage 00 retrieval idempotency.

FR-004: a second invocation against already-populated downloads MUST make
zero HTTP calls. The existing `_download_url_if_missing` checks
`dest.exists() and dest.stat().st_size > 0` (cli.py L643). This test asserts
that the higher-level `retrieval_run` honors idempotency end-to-end.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest


STAGE_MODULE = "pipeline.modules.00_retrieval"


def _load_stage():
    return importlib.import_module(STAGE_MODULE)


def _write_discovery_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    from src.pipeline.common.io import write_tsv

    write_tsv(path, fieldnames=["cohort_id", "accession"], rows=rows)


def test_retrieval_run_is_idempotent_when_files_already_present(tmp_path: Path) -> None:
    stage = _load_stage()

    discovery_manifest = tmp_path / "discovery.tsv"
    out_dir = tmp_path / "out"
    _write_discovery_manifest(
        discovery_manifest,
        [{"cohort_id": "c1", "accession": "GSE100001"}],
    )

    # Seed the expected SOFT file so _download_url_if_missing short-circuits.
    cohort_dir = out_dir / "downloads" / "c1"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "GSE100001_family.soft.gz").write_bytes(b"already-here")

    with patch("urllib.request.urlopen") as mock_open:
        rc = stage.retrieval_run(
            discovery_manifest=discovery_manifest,
            out_dir=out_dir,
            no_download=False,
            dry_run=False,
            run_manifest=tmp_path / "logs/run_manifest.yaml",
        )

    assert rc == 0
    # FR-004 acceptance: urlopen must not be called.
    assert mock_open.call_count == 0, (
        f"retrieval_run made {mock_open.call_count} HTTP call(s); expected 0 "
        f"(file already present)."
    )
