"""Spec 009 / T010 — Stage 00 stale .part file cleanup.

FR-004 edge case 3: stale `.part` files left over from interrupted downloads
must be detected and cleaned (or resumed) at startup. The current
`_download_url` uses `.part` for atomic rename but does not clean stale
remnants. Implemented in T030 (M4).
"""
from __future__ import annotations

import importlib
import os
import time
from pathlib import Path


STAGE_MODULE = "pipeline.modules.00_retrieval.http"


def _load_http():
    return importlib.import_module(STAGE_MODULE)


def test_stale_part_files_are_cleaned_at_startup(tmp_path: Path) -> None:
    http = _load_http()

    cohort_dir = tmp_path / "downloads" / "c1"
    cohort_dir.mkdir(parents=True, exist_ok=True)

    stale = cohort_dir / "GSE100001_family.soft.gz.part"
    stale.write_bytes(b"interrupted download")
    # Mark mtime > 1 hour ago.
    old = time.time() - 3700
    os.utime(stale, (old, old))

    fresh = cohort_dir / "GSE100002_family.soft.gz.part"
    fresh.write_bytes(b"in-flight")
    # mtime = now (fresh; must not be cleaned)
    os.utime(fresh, None)

    cleaned = http.cleanup_stale_part_files(cohort_dir.parent, max_age_seconds=3600)

    assert stale in cleaned, "stale .part file (>1h old) must be cleaned"
    assert not stale.exists(), "stale .part file must be deleted"
    assert fresh.exists(), "fresh .part file must be preserved"
    assert fresh not in cleaned
