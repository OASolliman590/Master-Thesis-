from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_help_runs() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "pipeline.cli", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "ICI thesis pipeline scaffold CLI" in proc.stdout

