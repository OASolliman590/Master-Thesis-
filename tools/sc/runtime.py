"""Runtime cache setup for the separately pinned single-cell environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def configure_runtime() -> None:
    """Keep matplotlib and Numba caches in the ignored worktree results tree."""
    cache_root = ROOT / "results" / ".sc-cache"
    for variable, name in (
        ("MPLCONFIGDIR", "matplotlib"),
        ("NUMBA_CACHE_DIR", "numba"),
    ):
        destination = Path(os.environ.get(variable, cache_root / name))
        destination.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(destination)
    if "numba" in sys.modules:
        from numba.core import config

        config.reload_config()
