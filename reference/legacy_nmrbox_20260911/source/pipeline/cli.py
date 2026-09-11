"""Thin wrapper for `python -m pipeline.cli` in source-layout mode."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


_bootstrap_src_path()

from src.pipeline.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

