"""Spec 009 / T008 — Stage 00 empty discovery manifest.

FR-008 edge case 4: empty manifest must produce an empty ledger with the
correct schema, not crash.
"""
from __future__ import annotations

import importlib
from pathlib import Path


STAGE_MODULE = "pipeline.modules.00_retrieval"


def _load_stage():
    return importlib.import_module(STAGE_MODULE)


# The retrieval_ledger.tsv schema is FROZEN in research.md § 2.2.
EXPECTED_LEDGER_COLUMNS = [
    "cohort_id",
    "input_accession",
    "gse_id",
    "srp_id",
    "srx_id",
    "srr_id",
    "bioproject_id",
    "source_db",
    "source_uri",
    "retrieval_status",
    "retrieval_timestamp",
    "retrieval_note",
]


def test_empty_manifest_produces_empty_ledger_with_correct_schema(tmp_path: Path) -> None:
    from src.pipeline.common.io import write_tsv

    stage = _load_stage()

    discovery_manifest = tmp_path / "discovery.tsv"
    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession"],
        rows=[],
    )
    out_dir = tmp_path / "out"

    rc = stage.retrieval_run(
        discovery_manifest=discovery_manifest,
        out_dir=out_dir,
        no_download=True,
        dry_run=False,
        run_manifest=tmp_path / "logs/run_manifest.yaml",
    )
    assert rc == 0

    ledger = out_dir / "retrieval_ledger.tsv"
    assert ledger.exists(), "empty input must still produce a ledger file"

    header = ledger.read_text(encoding="utf-8").splitlines()
    assert len(header) >= 1, "ledger must at least carry the header row"
    cols = header[0].split("\t")
    assert cols == EXPECTED_LEDGER_COLUMNS, (
        f"ledger schema drift: got {cols}, expected {EXPECTED_LEDGER_COLUMNS}"
    )
    # Empty input → exactly one header line, no data rows.
    assert len(header) == 1
