from __future__ import annotations

import datetime as dt
import json
import platform
import sys
from pathlib import Path
from typing import Any

from .io import ensure_parent


def append_run_manifest(
    manifest_path: Path,
    command: str,
    params: dict[str, Any],
    outputs: list[str] | None = None,
) -> None:
    ensure_parent(manifest_path)
    event = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": command,
        "params": params,
        "outputs": outputs or [],
        "software": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    # JSON Lines is valid YAML-compatible text and simple for append-only logs.
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True) + "\n")

