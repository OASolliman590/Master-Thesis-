"""Spec 009 / T011 — Stage 00 golden ledger integration test.

FR-001, FR-003: re-running `retrieval_run` against a fixed discovery manifest
and a populated downloads tree must produce a ledger identical to the
committed golden file (modulo `retrieval_timestamp`).

The fixture and golden file are added in T011; this test fails until then.
"""
from __future__ import annotations

import importlib
from pathlib import Path


STAGE_MODULE = "pipeline.modules.00_retrieval"

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stage_00_golden"


def _load_stage():
    return importlib.import_module(STAGE_MODULE)


def test_retrieval_run_matches_golden_ledger(tmp_path: Path) -> None:
    from src.pipeline.common.io import read_tsv

    stage = _load_stage()

    discovery_manifest = FIXTURE_DIR / "discovery_manifest.tsv"
    downloads_seed = FIXTURE_DIR / "downloads"
    golden_ledger = FIXTURE_DIR / "golden_retrieval_ledger.tsv"

    assert discovery_manifest.exists(), (
        f"missing fixture {discovery_manifest} — create it in T011"
    )
    assert downloads_seed.exists(), (
        f"missing fixture {downloads_seed} — create it in T011"
    )
    assert golden_ledger.exists(), (
        f"missing golden ledger {golden_ledger} — create it in T011"
    )

    # Stage the fixture into tmp so the test does not mutate the fixture tree.
    import shutil

    out_dir = tmp_path / "out"
    shutil.copytree(downloads_seed, out_dir / "downloads")

    rc = stage.retrieval_run(
        discovery_manifest=discovery_manifest,
        out_dir=out_dir,
        no_download=True,
        dry_run=False,
        run_manifest=tmp_path / "logs/run_manifest.yaml",
    )
    assert rc == 0

    actual_rows = read_tsv(out_dir / "retrieval_ledger.tsv")
    golden_rows = read_tsv(golden_ledger)

    assert len(actual_rows) == len(golden_rows)

    ignore_cols = {"retrieval_timestamp"}
    for actual, golden in zip(actual_rows, golden_rows):
        for col in golden:
            if col in ignore_cols:
                continue
            assert actual.get(col, "") == golden.get(col, ""), (
                f"column {col!r} diverges from golden: "
                f"got {actual.get(col)!r}, expected {golden.get(col)!r}"
            )
