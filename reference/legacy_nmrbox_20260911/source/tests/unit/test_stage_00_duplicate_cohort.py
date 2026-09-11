"""Spec 009 / T009 — Stage 00 duplicate cohort handling.

FR-008 edge case 6: a cohort_id listed twice must be rejected with
ErrorClass.manifest_error, not silently re-downloaded. The current
cli.py implementation iterates the manifest naively and re-downloads.
"""
from __future__ import annotations

import importlib
from pathlib import Path


STAGE_MODULE = "pipeline.modules.00_retrieval"


def _load_stage():
    return importlib.import_module(STAGE_MODULE)


def test_duplicate_cohort_id_is_rejected_as_manifest_error(tmp_path: Path) -> None:
    from src.pipeline.common.io import write_tsv, read_tsv

    stage = _load_stage()

    discovery_manifest = tmp_path / "discovery.tsv"
    write_tsv(
        discovery_manifest,
        fieldnames=["cohort_id", "accession"],
        rows=[
            {"cohort_id": "c1", "accession": "GSE100001"},
            {"cohort_id": "c1", "accession": "GSE100002"},  # duplicate cohort_id
        ],
    )
    out_dir = tmp_path / "out"

    rc = stage.retrieval_run(
        discovery_manifest=discovery_manifest,
        out_dir=out_dir,
        no_download=True,
        dry_run=False,
        run_manifest=tmp_path / "logs/run_manifest.yaml",
    )
    # rc may be 0 (best-effort) or non-zero (hard fail) — both acceptable.
    # The key invariant: the ledger row records the manifest_error.
    rows = read_tsv(out_dir / "retrieval_ledger.tsv")
    c1_rows = [r for r in rows if r["cohort_id"] == "c1"]
    assert c1_rows, "duplicate cohort must still produce a ledger row"
    # The first occurrence (or a merged row) carries manifest_error.
    note_values = " ".join(r.get("retrieval_note", "") for r in c1_rows)
    assert "manifest_error" in note_values, (
        f"expected manifest_error in retrieval_note for duplicate cohort_id; "
        f"got: {note_values!r}"
    )
