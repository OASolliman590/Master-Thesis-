"""Run an A-META R script and publish path-sanitised bridge provenance."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

from tools.r_bridge import run_r


_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9._~-])/(?:Volumes|Users|private|tmp|home|opt|Library|System|usr|var)/[^\s,;\"')]+"
)


def sanitise_r_manifest(manifest: Mapping, *, script_id: str) -> dict:
    """Replace machine-specific locations with relative identifiers or hashes."""
    result = _sanitize_value(dict(manifest))
    result.pop("script_path", None)
    result["script"] = script_id
    return result


def run_r_sanitised(
    script: Path | str,
    inputs: dict[str, Path],
    config: dict,
    output_dir: Path | str,
    *,
    script_id: str,
    runner=None,
):
    """Run through r_bridge, then publish sanitized outputs and manifest."""
    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage_parent = Path(tempfile.mkdtemp(prefix="a-meta-r-stage-", dir=destination.parent))
    try:
        staged = run_r(
            script,
            inputs,
            config,
            stage_parent / "R",
            runner=runner,
        )
        safe_manifest = sanitise_r_manifest(staged.manifest, script_id=script_id)
        expected_names = list(staged.outputs)
        session_info = str(safe_manifest.get("session_info", ""))
        safe_manifest.setdefault("output_sha256", {})["sessionInfo.txt"] = _sha256_bytes(
            session_info.encode("utf-8")
        )
        if destination.exists():
            manifest_path = destination / "manifest.json"
            try:
                current = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raise FileExistsError(f"A-META R output already exists: {destination}") from None
            if current != safe_manifest or any(
                not (destination / name).is_file()
                or _sha256_file(destination / name) != staged.manifest["output_sha256"][name]
                for name in expected_names
            ):
                raise FileExistsError(f"A-META R output differs from the requested run: {destination}")
            return SimpleNamespace(
                outputs={name: destination / name for name in expected_names},
                manifest=safe_manifest,
                stdout=staged.stdout,
                stderr=staged.stderr,
            )

        destination.mkdir(parents=True)
        for name, path in staged.outputs.items():
            shutil.copyfile(path, destination / name)
        (destination / "sessionInfo.txt").write_text(session_info, encoding="utf-8")
        (destination / "manifest.json").write_text(
            json.dumps(safe_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            outputs={name: destination / name for name in expected_names},
            manifest=safe_manifest,
            stdout=staged.stdout,
            stderr=staged.stderr,
        )
    finally:
        shutil.rmtree(stage_parent, ignore_errors=True)


def _sanitize_value(value):
    if isinstance(value, Mapping):
        return {str(key): _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        if Path(value).is_absolute():
            return "<absolute-path>"
        return _ABSOLUTE_PATH.sub("<absolute-path>", value)
    return value


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
