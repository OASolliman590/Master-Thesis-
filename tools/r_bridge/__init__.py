"""Run project-pinned R scripts as subprocesses with file provenance."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


_ROOT = Path(__file__).resolve().parents[2]
_R_PROJECT = _ROOT / "r"
_SESSION_INFO = "sessionInfo.txt"
_RUNTIME_INFO = "bridge-runtime.json"
_MANIFEST = "manifest.json"
_CONFIG = "config.json"
_RESERVED_OUTPUTS = {_SESSION_INFO, _RUNTIME_INFO, _MANIFEST, _CONFIG}


@dataclass(frozen=True)
class RResult:
    outputs: dict[str, Path]
    manifest: dict[str, Any]
    stdout: str = ""
    stderr: str = ""


class RScriptError(RuntimeError):
    """An R script failed or its staged outputs did not meet the contract."""

    def __init__(
        self,
        script: str | Path,
        stderr: str,
        returncode: int | None = None,
        stdout: str = "",
    ):
        self.script_name = Path(script).name
        self.stderr_tail = "\n".join(stderr.splitlines()[-50:])
        self.returncode = returncode
        self.stdout = stdout
        if returncode == 0:
            detail = " (post-execution validation)"
        elif returncode is None:
            detail = ""
        else:
            detail = f" (exit {returncode})"
        tail = f"\n{self.stderr_tail}" if self.stderr_tail else ""
        super().__init__(f"R script {self.script_name!r} failed{detail}{tail}")


class FakeR:
    """A subprocess-compatible fake that writes canned files by script name."""

    def __init__(self, canned: dict[str, dict[str, str]]):
        self.canned = canned

    def __call__(self, command, *, cwd, env, capture_output, text, check=False):
        script = Path(command[-2])
        config_path = Path(command[-1])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        canned = self.canned.get(script.name)
        if canned is None:
            return subprocess.CompletedProcess(
                command, 1, "", f"No canned output for {script.name}\n"
            )

        output_dir = Path(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, contents in canned.items():
            if Path(name).name != name or name in {"", ".", ".."}:
                return subprocess.CompletedProcess(
                    command, 1, "", f"Invalid canned output name: {name}\n"
                )
            (output_dir / name).write_text(contents, encoding="utf-8")

        (output_dir / _SESSION_INFO).write_text(
            "FakeR sessionInfo()\n", encoding="utf-8"
        )
        (output_dir / _RUNTIME_INFO).write_text(
            json.dumps(
                {
                    "r_version": "FakeR",
                    "bioconductor_version": "FakeBioconductor",
                    "r_library": "~/.fake/renv/library",
                    "package_versions": {"jsonlite": "2.0.0"},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")


def run_r(
    script: str | Path,
    inputs: dict[str, Path],
    config: dict,
    out_dir: Path,
    *,
    runner=None,
) -> RResult:
    """Run one script, validate its staged files, then publish the result."""
    script_path = Path(script).expanduser().resolve(strict=True)
    if not script_path.is_file():
        raise ValueError(f"R script is not a file: {script_path}")
    if not _R_PROJECT.is_dir():
        raise FileNotFoundError(f"R project not found: {_R_PROJECT}")

    expected_outputs = _expected_outputs(config)
    serialized_config = json.loads(json.dumps(config, default=str))
    serialized_config["expected_outputs"] = expected_outputs
    input_paths = {}
    input_hashes = {}
    for name, path in inputs.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Input names must be non-empty strings")
        input_path = Path(path).expanduser().resolve(strict=True)
        if not input_path.is_file():
            raise ValueError(f"Input is not a file: {input_path}")
        input_paths[name] = str(input_path)
        input_hashes[name] = _sha256(input_path)

    destination = Path(out_dir).expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent)
    )
    try:
        staged_outputs = stage / "outputs"
        staged_outputs.mkdir()
        config_path = stage / _CONFIG
        bridge_config = {
            "config": serialized_config,
            "inputs": input_paths,
            "expected_outputs": expected_outputs,
            "output_dir": str(staged_outputs),
        }
        config_path.write_text(
            json.dumps(bridge_config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        env = _r_environment()
        command = [
            shutil.which("Rscript") or "Rscript",
            "--no-save",
            "--no-restore",
            "--no-site-file",
            str(script_path),
            str(config_path),
        ]
        execute = runner or subprocess.run
        try:
            completed = execute(
                command,
                cwd=str(_R_PROJECT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            raise RScriptError(script_path, str(error)) from error

        stdout = _as_text(completed.stdout)
        stderr = _as_text(completed.stderr)
        if completed.returncode != 0:
            raise RScriptError(script_path, stderr, completed.returncode, stdout)

        _validate_staged_outputs(script_path, staged_outputs, expected_outputs, stdout)
        session_path = staged_outputs / _SESSION_INFO
        runtime_path = staged_outputs / _RUNTIME_INFO
        session_info = session_path.read_text(encoding="utf-8")
        try:
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RScriptError(
                script_path,
                f"invalid bridge runtime metadata: {error}",
                completed.returncode,
                stdout,
            ) from error

        output_hashes = {
            name: _sha256(staged_outputs / name) for name in expected_outputs
        }
        output_hashes[_SESSION_INFO] = _sha256(session_path)
        manifest = {
            "script_path": str(script_path),
            "script_sha256": _sha256(script_path),
            "input_sha256": input_hashes,
            "config": serialized_config,
            "output_sha256": output_hashes,
            "r_version": runtime["r_version"],
            "bioconductor_version": runtime["bioconductor_version"],
            "r_library": runtime["r_library"],
            "package_versions": runtime["package_versions"],
            "session_info": session_info,
        }
        runtime_path.unlink()
        manifest_path = staged_outputs / _MANIFEST
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        if destination.exists() or destination.is_symlink():
            if destination.is_symlink():
                raise FileExistsError(f"Output directory is a symlink: {destination}")
            existing_manifest = destination / _MANIFEST
            if existing_manifest.is_file():
                try:
                    same_result = json.loads(existing_manifest.read_text()) == manifest
                except (OSError, json.JSONDecodeError):
                    same_result = False
                if same_result:
                    _verify_published_outputs(destination, manifest)
                    return RResult(
                        {name: destination / name for name in expected_outputs},
                        manifest,
                        stdout,
                        stderr,
                    )
            raise FileExistsError(f"Output directory already exists: {destination}")

        os.rename(staged_outputs, destination)
        return RResult(
            {name: destination / name for name in expected_outputs},
            manifest,
            stdout,
            stderr,
        )
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _expected_outputs(config: dict) -> list[str]:
    names = config.get("expected_outputs")
    if not isinstance(names, (list, tuple)) or not names:
        raise ValueError("config must include a non-empty expected_outputs list")
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("Expected output names must be non-empty strings")

    normalized = [posixpath.normpath(name.replace("\\", "/")) for name in names]
    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate expected output names after normalization")

    for original, name in zip(names, normalized):
        windows_path = PureWindowsPath(original)
        if name in _RESERVED_OUTPUTS:
            raise ValueError(f"Reserved output name: {name}")
        if name in {".", ".."} or name.startswith("../") or name.startswith("/"):
            raise ValueError(f"Invalid expected output name: {original}")
        if windows_path.is_absolute() or windows_path.drive:
            raise ValueError(f"Absolute expected output name: {original}")
        if original != name or "/" in original or "\\" in original:
            raise ValueError(f"Expected output names cannot contain path syntax: {original}")
    return normalized


def _r_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in ("R_LIBS", "R_LIBS_USER", "R_LIBS_SITE"):
        env.pop(name, None)
    env["RENV_PROJECT"] = str(_R_PROJECT.resolve())
    env["R_ENVIRON_USER"] = str((_R_PROJECT / ".Renviron").resolve())
    env["R_PROFILE_USER"] = str((_R_PROJECT / ".Rprofile").resolve())
    # The system renv sandbox lives outside this worktree's writable roots.
    env["RENV_CONFIG_SANDBOX_ENABLED"] = "FALSE"
    return env


def _validate_staged_outputs(
    script: Path,
    output_dir: Path,
    expected_outputs: list[str],
    stdout: str,
) -> None:
    missing = [
        name
        for name in expected_outputs
        if not (output_dir / name).is_file() or (output_dir / name).is_symlink()
    ]
    if not (output_dir / _SESSION_INFO).is_file():
        missing.append(_SESSION_INFO)
    if not (output_dir / _RUNTIME_INFO).is_file():
        missing.append(_RUNTIME_INFO)

    allowed = set(expected_outputs) | {_SESSION_INFO, _RUNTIME_INFO}
    unexpected = []
    for path in output_dir.rglob("*"):
        relative = path.relative_to(output_dir).as_posix()
        if path.is_symlink() or path.is_dir() or relative not in allowed:
            unexpected.append(relative)

    failures = []
    if missing:
        label = "output" if len(missing) == 1 else "outputs"
        failures.append(f"missing expected {label}: {', '.join(missing)}")
    if unexpected:
        failures.append(f"unexpected staged files: {', '.join(sorted(unexpected))}")
    if failures:
        raise RScriptError(script, "\n".join(failures), 0, stdout)


def _verify_published_outputs(destination: Path, manifest: dict[str, Any]) -> None:
    hashes = manifest["output_sha256"]
    missing = []
    mismatched = []
    for name, expected_hash in hashes.items():
        path = destination / name
        if not path.is_file() or path.is_symlink():
            missing.append(name)
        elif _sha256(path) != expected_hash:
            mismatched.append(name)

    allowed = set(hashes) | {_MANIFEST}
    unexpected = []
    for path in destination.rglob("*"):
        relative = path.relative_to(destination).as_posix()
        if path.is_symlink() or path.is_dir() or relative not in allowed:
            unexpected.append(relative)

    if missing or mismatched or unexpected:
        details = []
        if missing:
            details.append(f"missing outputs: {', '.join(missing)}")
        if mismatched:
            details.append(f"hash mismatches: {', '.join(mismatched)}")
        if unexpected:
            details.append(f"unexpected published files: {', '.join(sorted(unexpected))}")
        raise ValueError(f"Existing output failed integrity validation: {'; '.join(details)}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_text(value) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)
