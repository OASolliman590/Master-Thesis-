from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


PACKET = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("target_runner", PACKET / "runner.py")
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def payload(tmp_path: Path) -> Path:
    root = tmp_path / "payload"
    root.mkdir()
    entries: list[dict[str, Any]] = []
    for rel in sorted(runner.EXPECTED_FILES):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ("synthetic fixture: " + rel + "\n").encode()
        path.write_bytes(body)
        if rel == "runner.py":
            shutil.copyfile(PACKET / "runner.py", path)
            body = path.read_bytes()
        elif rel == "tools/a_dav/requirements-synthetic.txt":
            shutil.copyfile(PACKET.parents[2] / "tools/a_dav/requirements-synthetic.txt", path)
            body = path.read_bytes()
        entries.append({"path": rel, "size": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    (root / "ALLOWLIST_MANIFEST.json").write_text(
        json.dumps({
            "classification": "SYNTHETIC_ONLY",
            "base_commit": runner.BASE_COMMIT,
            "files": entries,
        }),
        encoding="utf-8",
    )
    return root


def write_bundle(destination: Path, *, true_flag: str | None = None) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in runner.BUNDLE_FILES - {"manifest.json"}:
        (destination / name).write_text("{}", encoding="utf-8")
    (destination / "manifest.json").write_text(json.dumps({
        "classification": "SYNTHETIC_ONLY",
        "files": {name: hashlib.sha256(b"{}").hexdigest() for name in runner.BUNDLE_FILES if name != "manifest.json"},
        **{flag: flag == true_flag for flag in runner.ACTUAL_FLAGS},
    }), encoding="utf-8")


def public_summary(binding: str = "a" * 64) -> str:
    return json.dumps({
        "classification": "SYNTHETIC_ONLY", "stage": "workflow", "status": "SYNTHETIC_READY",
        "reasons": [], "bindings": {"code_sha256": binding},
        **{flag: False for flag in runner.ACTUAL_FLAGS},
    }) + "\n"


def test_rejects_unsafe_manifest_members_before_child_process(tmp_path: Path) -> None:
    root = payload(tmp_path)
    manifest_path = root / "ALLOWLIST_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "out"
    result = runner.execute(root, output, python="/synthetic/python", process=lambda *a, **k: pytest.fail("child must not run"))
    assert result["status"] == "FAILED"
    assert result["failed_stage"] == "payload_validation"
    assert not any(output.glob("process-*.log"))


def test_rejects_symlink_payload_member(tmp_path: Path) -> None:
    root = payload(tmp_path)
    member = root / sorted(runner.EXPECTED_FILES)[0]
    content = member.read_bytes()
    external = tmp_path / "synthetic-external.txt"
    external.write_bytes(content)
    member.unlink()
    member.symlink_to(external)
    with pytest.raises(runner.ValidationError, match="symlink"):
        runner.verify_payload(root)


@pytest.mark.parametrize("mutation", ["missing", "changed", "extra"])
def test_rejects_incomplete_changed_or_extra_payload(tmp_path: Path, mutation: str) -> None:
    root = payload(tmp_path)
    if mutation == "missing":
        (root / sorted(runner.EXPECTED_FILES)[0]).unlink()
    elif mutation == "changed":
        (root / sorted(runner.EXPECTED_FILES)[0]).write_text("changed", encoding="utf-8")
    else:
        (root / "unexpected.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(runner.ValidationError):
        runner.verify_payload(root)


def test_failed_test_stage_never_accepts_and_flags_stay_false(tmp_path: Path) -> None:
    root = payload(tmp_path)
    calls: list[list[str]] = []

    def failed(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(args[0]))
        return subprocess.CompletedProcess(args[0], 4, "synthetic failure\n", "")

    receipt = runner.execute(root, tmp_path / "out", python="/synthetic/python", process=failed)
    assert calls
    assert receipt["status"] == "FAILED"
    assert receipt["failed_stage"] == "full_synthetic_tests"
    assert receipt["target_environment_software_acceptance"] is False
    assert receipt["analysis_ready"] is False
    assert receipt["source_admission"] is False
    assert receipt["statistical_release"] is False
    assert receipt["biological_analysis_executed"] is False


def test_fresh_resume_summary_mismatch_fails_and_no_acceptance(tmp_path: Path) -> None:
    root = payload(tmp_path)
    calls: list[list[str]] = []

    def mismatch(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if "--freeze" in args:
            write_bundle(Path(args[args.index("--freeze") + 1]))
        stdout = public_summary("a" * 64 if len(calls) == 2 else "b" * 64)
        return subprocess.CompletedProcess(args, 0, stdout, "")

    receipt = runner.execute(root, tmp_path / "out", python="/synthetic/python", process=mismatch)
    assert [c[3] for c in calls] == ["pytest", "tools.a_dav.demo", "tools.a_dav.demo"]
    assert receipt["status"] == "FAILED"
    assert receipt["failed_stage"] == "fresh_resume_comparison"
    assert receipt["target_environment_software_acceptance"] is False


def test_success_requires_every_child_and_four_file_bundle(tmp_path: Path) -> None:
    root = payload(tmp_path)
    calls: list[list[str]] = []

    def success(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert all(kwargs["env"][name] == "1" for name in (
            "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
        ))
        if "--freeze" in args:
            destination = Path(args[args.index("--freeze") + 1])
            write_bundle(destination)
        return subprocess.CompletedProcess(args, 0, public_summary(), "")

    receipt = runner.execute(root, tmp_path / "out", python="/synthetic/python", process=success)
    assert receipt["status"] == "PASSED"
    assert receipt["target_environment_software_acceptance"] is True


def test_bundle_with_true_actual_flag_fails_closed(tmp_path: Path) -> None:
    root = payload(tmp_path)

    def unsafe(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "--freeze" in args:
            write_bundle(Path(args[args.index("--freeze") + 1]), true_flag="analysis_ready")
        return subprocess.CompletedProcess(args, 0, public_summary(), "")

    receipt = runner.execute(root, tmp_path / "out", python="/synthetic/python", process=unsafe)
    assert receipt["status"] == "FAILED"
    assert receipt["failed_stage"] == "fresh_resume"
    assert receipt["target_environment_software_acceptance"] is False


@pytest.mark.parametrize("problem", ["missing", "mismatch"])
def test_dependency_preflight_blocks_without_running_children(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str) -> None:
    root = payload(tmp_path)
    environment = runner.environment_record(root)
    environment["installed_distributions"]["pytest"] = None if problem == "missing" else "0.0"
    monkeypatch.setattr(runner, "environment_record", lambda _: environment)

    def forbidden(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        pytest.fail("child process must not run")

    receipt = runner.execute(root, tmp_path / "out", process=forbidden)
    assert receipt["status"] == "BLOCKED"
    assert receipt["failed_stage"] == "environment_preflight"
    assert receipt["failure_category"] == (
        "REQUIRED_DEPENDENCY_UNAVAILABLE" if problem == "missing" else "DEPENDENCY_VERSION_MISMATCH"
    )
    assert receipt["target_environment_software_acceptance"] is False


@pytest.mark.parametrize("unsafe", [
    {"record_count": 1}, {"patient_id": "synthetic-id"},
])
def test_summary_rejects_counts_and_identifiers(unsafe: dict[str, Any]) -> None:
    summary = json.loads(public_summary())
    summary.update(unsafe)
    with pytest.raises(runner.ValidationError):
        runner._check_safe_summary(json.dumps(summary))


def test_bundle_rejects_symlink_root_and_member(tmp_path: Path) -> None:
    real = tmp_path / "real-bundle"
    write_bundle(real)
    linked = tmp_path / "linked-bundle"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(runner.ValidationError, match="symlinked"):
        runner._check_bundle(linked)
    member = real / "packet.json"
    external = tmp_path / "outside-packet.json"
    external.write_text("{}", encoding="utf-8")
    member.unlink()
    member.symlink_to(external)
    with pytest.raises(runner.ValidationError):
        runner._check_bundle(real)
