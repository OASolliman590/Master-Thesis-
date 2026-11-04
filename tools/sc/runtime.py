"""Runtime cache setup for the separately pinned single-cell environment."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def configure_runtime() -> None:
    """Give matplotlib and Numba writable caches without changing the source env."""
    temporary_root = Path(tempfile.gettempdir())
    for variable, name in (
        ("MPLCONFIGDIR", "thesis-sc-matplotlib"),
        ("NUMBA_CACHE_DIR", "thesis-sc-numba"),
    ):
        destination = Path(os.environ.get(variable, temporary_root / name))
        destination.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(destination)
