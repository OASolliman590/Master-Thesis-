"""Spec 009 / T007 — Stage 00 --dry-run.

FR-006: `--dry-run` MUST list every planned download in a `planned_downloads.tsv`
and MUST NOT call `urlopen`. Implemented in T029 (M4).
"""
from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch


STAGE_MODULE = "pipeline.modules.00_retrieval"


def _load_stage():
    return importlib.import_module(STAGE_MODULE)


def _write_discovery_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    from src.pipeline.common.io import write_tsv

    write_tsv(path, fieldnames=["cohort_id", "accession"], rows=rows)


def test_dry_run_emits_planned_downloads_and_makes_no_http_calls(tmp_path: Path) -> None:
    stage = _load_stage()

    discovery_manifest = tmp_path / "discovery.tsv"
    out_dir = tmp_path / "out"
    _write_discovery_manifest(
        discovery_manifest,
        [
            {"cohort_id": "c1", "accession": "GSE100001"},
            {"cohort_id": "c2", "accession": "GSE100002; SRP100002"},
        ],
    )

    with patch("urllib.request.urlopen") as mock_open:
        rc = stage.retrieval_run(
            discovery_manifest=discovery_manifest,
            out_dir=out_dir,
            no_download=False,
            dry_run=True,
            run_manifest=tmp_path / "logs/run_manifest.yaml",
        )

    assert rc == 0
    assert mock_open.call_count == 0, "dry-run must not call urlopen"

    planned = out_dir / "planned_downloads.tsv"
    assert planned.exists(), "dry-run must emit planned_downloads.tsv"

    from src.pipeline.common.io import read_tsv

    rows = read_tsv(planned)
    assert {"cohort_id", "accession", "file_kind", "url", "dest_path"} <= set(rows[0].keys())
    cohort_ids = {row["cohort_id"] for row in rows}
    assert cohort_ids == {"c1", "c2"}
    file_kinds = {row["file_kind"] for row in rows}
    assert "soft" in file_kinds
    assert "runinfo" in file_kinds
