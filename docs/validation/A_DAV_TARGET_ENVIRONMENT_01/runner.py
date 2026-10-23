#!/usr/bin/env python3
"""Run the bounded synthetic DAV software check on an isolated payload."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import locale
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

BASE_COMMIT = "f53d2222d7d82e6dfdf4af381d71946cd247a89d"
RUNTIME = {
    "tools/a_dav/__init__.py", "tools/a_dav/search_log.py", "tools/a_dav/study_resolution.py",
    "tools/a_dav/object_verification.py", "tools/a_dav/admission.py", "tools/a_dav/assays.py",
    "tools/a_dav/core.py", "tools/a_dav/endpoints.py", "tools/a_dav/exposure.py",
    "tools/a_dav/matrices.py", "tools/a_dav/overlap.py", "tools/a_dav/prat_review.py",
    "tools/a_dav/registries.py", "tools/a_dav/release.py", "tools/a_dav/reporting.py",
    "tools/a_dav/timing.py", "tools/a_dav/workflow.py", "tools/a_dav/demo.py",
}
TESTS = {
    "tests/a_dav_implementation/test_core.py", "tests/a_dav_implementation/test_existing_seams.py",
    "tests/a_dav_implementation/test_group_a.py", "tests/a_dav_implementation/test_group_b_graph_admission.py",
    "tests/a_dav_implementation/test_group_b_protocol.py", "tests/a_dav_implementation/test_group_c.py",
    "tests/a_dav_implementation/test_workflow.py",
}
SCHEMAS = {f"specs/A_DATA_ACQUISITION_VALIDATION/schemas/{name}.schema.json" for name in (
    "assay_registry", "clinical_outcome", "cohort_admission_receipt", "episode_binding",
    "materialized_matrix", "matrix_build_receipt", "overlap_edge", "patient_registry",
    "prior_exposure_record", "publication_family", "release_contract", "source_record",
    "specimen_registry", "study_registry", "treatment_episode", "treatment_exposure",
    "validation_receipt",
)}
REQUIREMENTS = {"tools/a_dav/requirements-synthetic.txt"}
EXPECTED_FILES = RUNTIME | TESTS | SCHEMAS | REQUIREMENTS | {"runner.py"}
BUNDLE_FILES = {"manifest.json", "packet.json", "release_draft.json", "result.json"}
ACTUAL_FLAGS = {"analysis_ready", "source_admission", "statistical_release", "biological_analysis_executed"}
SUMMARY_KEYS = {"classification", "stage", "status", "reasons", "bindings", *ACTUAL_FLAGS}
SUMMARY_BINDINGS = {"input_sha256", "config_sha256", "schemas_sha256", "code_sha256", "core_sha256", "output_sha256"}
MANIFEST_NAME = "ALLOWLIST_MANIFEST.json"
MAX_CHILD_SECONDS = 900


class ValidationError(Exception):
    """The payload or an executed acceptance condition is invalid."""


class BlockedError(Exception):
    """The environment cannot run the required check as pinned."""

    def __init__(self, category: str) -> None:
        self.category = category


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member(name: Any) -> str:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValidationError("unsafe manifest path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValidationError("unsafe manifest path")
    if path.as_posix() != name:
        raise ValidationError("noncanonical manifest path")
    return name


def verify_payload(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValidationError("payload root is not a directory")
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValidationError("manifest missing or unsafe")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError):
        raise ValidationError("manifest unreadable") from None
    if (not isinstance(manifest, dict) or manifest.get("classification") != "SYNTHETIC_ONLY"
            or manifest.get("base_commit") != BASE_COMMIT or not isinstance(manifest.get("files"), list)):
        raise ValidationError("manifest header invalid")
    entries: dict[str, tuple[int, str]] = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise ValidationError("manifest entry invalid")
        name = _safe_member(entry["path"])
        if name in entries or type(entry["size"]) is not int or entry["size"] < 0:
            raise ValidationError("duplicate or invalid manifest entry")
        if not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64:
            raise ValidationError("invalid manifest digest")
        entries[name] = (entry["size"], entry["sha256"])
    if set(entries) != EXPECTED_FILES:
        raise ValidationError("manifest file set differs from fixed allowlist")
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValidationError("symlink in payload")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != EXPECTED_FILES | {MANIFEST_NAME}:
        raise ValidationError("payload contains missing or extra files")
    hashes: dict[str, str] = {}
    for name, (size, expected_hash) in entries.items():
        path = root.joinpath(*PurePosixPath(name).parts)
        if not path.is_file():
            raise ValidationError("allowlisted member missing")
        raw = path.read_bytes()
        if len(raw) != size or digest(raw) != expected_hash:
            raise ValidationError("allowlisted member changed")
        hashes[name] = expected_hash
    if (root / "runner.py").read_bytes() != Path(__file__).resolve().read_bytes():
        raise ValidationError("executed runner differs from payload runner")
    return {"manifest_sha256": digest(manifest_bytes), "files": hashes}


def _requirements(root: Path) -> dict[str, str]:
    requested: dict[str, str] = {}
    for line in (root / next(iter(REQUIREMENTS))).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            package, sep, version = line.partition("==")
            if not sep or not package or not version or package.lower() not in {"pytest", "jsonschema", "mypy"}:
                raise ValidationError("synthetic requirements file invalid")
            requested[package.lower()] = version
    if set(requested) != {"pytest", "jsonschema", "mypy"}:
        raise ValidationError("synthetic requirements incomplete")
    return requested


def environment_record(root: Path) -> dict[str, Any]:
    requirements = _requirements(root)
    installed: dict[str, str | None] = {}
    for package in ("pytest", "jsonschema", "mypy"):
        try:
            installed[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed[package] = None
    return {
        "os": platform.system(), "platform": platform.platform(), "machine": platform.machine(),
        "python_executable": sys.executable, "python_version": platform.python_version(),
        "locale": locale.setlocale(locale.LC_CTYPE, None), "timezone": time.tzname,
        "installed_distributions": installed, "public_requirements": requirements,
    }


def _check_dependencies(environment: Mapping[str, Any]) -> None:
    installed = environment["installed_distributions"]
    required = environment["public_requirements"]
    if any(installed.get(name) is None for name in ("pytest", "jsonschema")):
        raise BlockedError("REQUIRED_DEPENDENCY_UNAVAILABLE")
    if any(installed[name] != required[name] for name in ("pytest", "jsonschema")):
        raise BlockedError("DEPENDENCY_VERSION_MISMATCH")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _child_env() -> dict[str, str]:
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "TZ": "UTC",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "BLIS_NUM_THREADS": "1"}
    if os.name == "nt":
        for name in ("SYSTEMROOT", "WINDIR", "PATH"):
            if name in os.environ:
                env[name] = os.environ[name]
    return env


def _process_record(
    argv: Sequence[str], cwd: Path, output: Path, label: str,
    process: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    try:
        result = process(list(argv), cwd=str(cwd), env=_child_env(), text=True,
                         capture_output=True, timeout=MAX_CHILD_SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        code = 124
    except OSError:
        stdout, stderr, code = "", "child process could not start", 127
    else:
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    (output / f"process-{label}.stdout.log").write_text(stdout, encoding="utf-8")
    (output / f"process-{label}.stderr.log").write_text(stderr, encoding="utf-8")
    return {"command": list(argv), "exit_code": code,
            "stdout_log": f"process-{label}.stdout.log", "stderr_log": f"process-{label}.stderr.log"}


def _check_bundle(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_dir():
        raise ValidationError("freeze bundle root is missing or symlinked")
    items = list(path.iterdir())
    if any(item.is_symlink() or not item.is_file() for item in items) or {item.name for item in items} != BUNDLE_FILES:
        raise ValidationError("fresh output bundle must contain exactly four files")
    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValidationError("bundle manifest unreadable") from None
    if (not isinstance(manifest, dict) or manifest.get("classification") != "SYNTHETIC_ONLY"
            or not ACTUAL_FLAGS.issubset(manifest) or any(manifest.get(flag) is not False for flag in ACTUAL_FLAGS)
            or set(manifest.get("files", {})) != BUNDLE_FILES - {"manifest.json"}):
        raise ValidationError("bundle manifest or frozen flags invalid")
    hashes: dict[str, str] = {}
    for name in BUNDLE_FILES:
        raw = (path / name).read_bytes()
        hashes[name] = digest(raw)
        if name != "manifest.json" and manifest["files"][name] != hashes[name]:
            raise ValidationError("bundle member hash mismatch")
    return hashes


def _check_safe_summary(text: str) -> None:
    try:
        summary = json.loads(text)
    except json.JSONDecodeError:
        raise ValidationError("public summary is not JSON") from None
    if (not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS
            or summary.get("classification") != "SYNTHETIC_ONLY" or summary.get("stage") != "workflow"
            or summary.get("status") != "SYNTHETIC_READY"
            or any(summary.get(flag) is not False for flag in ACTUAL_FLAGS)):
        raise ValidationError("public summary shape or flags invalid")
    reasons = summary.get("reasons")
    bindings = summary.get("bindings")
    if (not isinstance(reasons, list) or any(not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code) for code in reasons)
            or not isinstance(bindings, dict) or not bindings or not set(bindings).issubset(SUMMARY_BINDINGS)
            or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in bindings.values())):
        raise ValidationError("public summary contains unsafe or malformed fields")


def execute(
    root: Path, output: Path, *, python: str | None = None,
    process: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    if output == root or root in output.parents or output in root.parents:
        raise ValidationError("output must be separate from payload")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValidationError("output directory must be fresh and empty")
    output.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    receipt: dict[str, Any] = {
        "classification": "SYNTHETIC_ONLY", "status": "STARTED", "pid": os.getpid(),
        "started_utc": started, "finished_utc": None, "failed_stage": None,
        "target_environment_software_acceptance": False, "real_source_data_used": False,
        "frozen_specs_changed": False, "analysis_ready": False, "source_admission": False,
        "statistical_release": False, "biological_analysis_executed": False, "stages": {},
    }
    status_path = output / "status.json"
    _atomic_json(status_path, receipt)
    stage = "payload_validation"
    try:
        verified = verify_payload(root)
        receipt["payload"] = verified
        receipt["environment"] = environment_record(root)
        receipt["frozen_spec_sha256"] = {name: verified["files"][name] for name in sorted(SCHEMAS)}
        _check_dependencies(receipt["environment"])
        python = python or sys.executable
        command_prefix = [python, "-B", "-m"]
        stage = "full_synthetic_tests"
        test = _process_record(command_prefix + ["pytest", "-q", "-p", "no:cacheprovider", "tests/a_dav_implementation"],
                               root, output, "tests", process)
        receipt["stages"][stage] = test
        _atomic_json(status_path, receipt)
        if test["exit_code"] != 0:
            raise ValidationError("full synthetic tests failed")
        stage = "fresh_resume"
        bundle = output / "synthetic-bundle"
        demo_args = command_prefix + ["tools.a_dav.demo", "--freeze", str(bundle)]
        fresh = _process_record(demo_args, root, output, "fresh", process)
        receipt["stages"]["fresh_demo"] = fresh
        _atomic_json(status_path, receipt)
        if fresh["exit_code"] != 0:
            raise ValidationError("fresh demo failed")
        fresh_bundle_hashes = _check_bundle(bundle)
        receipt["fresh_bundle_sha256"] = fresh_bundle_hashes
        resume = _process_record(demo_args, root, output, "resume", process)
        receipt["stages"]["resume_demo"] = resume
        _atomic_json(status_path, receipt)
        if resume["exit_code"] != 0:
            raise ValidationError("resume demo failed")
        fresh_summary = (output / "process-fresh.stdout.log").read_text(encoding="utf-8").strip()
        resume_summary = (output / "process-resume.stdout.log").read_text(encoding="utf-8").strip()
        _check_safe_summary(fresh_summary)
        _check_safe_summary(resume_summary)
        if fresh_summary != resume_summary:
            stage = "fresh_resume_comparison"
            raise ValidationError("fresh and resume summaries differ")
        receipt["safe_summary_sha256"] = digest(fresh_summary.encode())
        if _check_bundle(bundle) != fresh_bundle_hashes:
            stage = "fresh_resume_comparison"
            raise ValidationError("resume changed the frozen bundle")
        stage = "payload_postcheck"
        if verify_payload(root) != verified:
            raise ValidationError("payload changed during validation")
        receipt["target_environment_software_acceptance"] = True
        receipt["status"] = "PASSED"
    except BlockedError as exc:
        receipt["status"] = "BLOCKED"
        receipt["failed_stage"] = "environment_preflight"
        receipt["failure_category"] = exc.category
    except (ValidationError, OSError, ValueError, TypeError):
        receipt["status"] = "FAILED"
        receipt["failed_stage"] = stage
        receipt["failure_category"] = "VALIDATION_FAILED"
    finally:
        receipt["finished_utc"] = utc_now()
        _atomic_json(status_path, receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Exact isolated transferred payload root")
    parser.add_argument("--output", type=Path, required=True, help="Fresh dedicated synthetic output directory")
    args = parser.parse_args(argv)
    try:
        receipt = execute(args.root, args.output)
    except (OSError, ValidationError) as exc:
        print(json.dumps({"classification": "SYNTHETIC_ONLY", "status": "FAILED",
                          "failure_category": "VALIDATION_FAILED", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
