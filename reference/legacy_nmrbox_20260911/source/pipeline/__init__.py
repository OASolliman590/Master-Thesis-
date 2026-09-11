"""Runtime wrapper package for source-layout execution.

This allows running `python -m pipeline.cli` from repository root
without requiring an editable installation first.
"""

from __future__ import annotations

from pathlib import Path


# Expose src/pipeline subpackages (e.g. pipeline.modules.*) through this
# lightweight runtime wrapper package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_PIPELINE = _REPO_ROOT / "src" / "pipeline"
if _SRC_PIPELINE.exists():
    __path__.append(str(_SRC_PIPELINE))
