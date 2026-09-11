"""Execute and resume connected Paper B stages with atomic completion records."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tools.b_acquire.acquire import run_acquire
from tools.b_cohort.build import run_cohort
from tools.b_features.provider import run_features
from tools.b_prediction.fold_develop import run_fold_develop
from tools.b_workflow.config import load_config
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    code_identity_sha256,
    json_no_dups,
    remove_tree,
    sha256_file,
    utc_stamp,
)
from tools.b_workflow.plan import build_plan
from tools.b_workflow.stages import CODE_PATHS, IMPLEMENTED, STAGE_DEPS, STAGE_ORDER, descendants


def _fail(message: str, code: int = 3, stage: str | None = None) -> None:
    raise PipelineFailure(message, code, stage)


def _stage_path(run_dir: Path, stage_id: str) -> Path:
    return run_dir / stage_id


def _work_path(run_dir: Path, stage_id: str) -> Path:
    return run_dir / f"{stage_id}.work"


def is_complete(run_dir: Path, stage_id: str) -> bool:
    complete = _stage_path(run_dir, stage_id) / "COMPLETE.json"
    return complete.is_file()


def load_complete(run_dir: Path, stage_id: str) -> dict[str, Any] | None:
    path = _stage_path(run_dir, stage_id) / "COMPLETE.json"
    if not path.is_file():
        return None
    return json_no_dups(path.read_bytes())


def verify_complete_stage(run_dir: Path, stage_id: str) -> tuple[bool, str]:
    stage_dir = _stage_path(run_dir, stage_id)
    complete_path = stage_dir / "COMPLETE.json"
    if not complete_path.is_file():
        return False, "missing-COMPLETE"
    if _work_path(run_dir, stage_id).exists():
        return False, "work-dir-present"
    complete = json_no_dups(complete_path.read_bytes())
    if complete.get("status") != "complete":
        return False, "status-not-complete"
    if complete.get("stage") != stage_id:
        return False, "stage-mismatch"
    checksums = stage_dir / "checksums.json"
    if not checksums.is_file():
        return False, "missing-checksums"
    if complete.get("checksums_sha256") != sha256_file(checksums):
        return False, "checksums-hash-mismatch"
    manifest = stage_dir / "manifest.json"
    if not manifest.is_file():
        return False, "missing-manifest"
    if complete.get("manifest_sha256") != sha256_file(manifest):
        return False, "manifest-hash-mismatch"
    payload = json_no_dups(checksums.read_bytes())
    artifacts = payload.get("artifact_hashes") or {}
    for rel, expected in artifacts.items():
        if rel == "checksums.json" or expected is None:
            continue
        path = stage_dir / rel
        if not path.is_file():
            return False, f"missing-artifact:{rel}"
        actual = sha256_file(path)
        if actual != expected:
            return False, f"artifact-hash-mismatch:{rel}"
    return True, "ok"


def invalidate(run_dir: Path, stage_id: str, log: list[dict[str, Any]]) -> None:
    targets = [stage_id, *descendants(stage_id)]
    for sid in targets:
        path = _stage_path(run_dir, sid)
        work = _work_path(run_dir, sid)
        if path.exists() or work.exists():
            log.append({"action": "invalidate", "stage": sid, "synthetic": True})
        if path.exists():
            remove_tree(path)
        if work.exists():
            remove_tree(work)


def _write_plan(run_dir: Path, plan: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(run_dir / "plan.json", plan)


def _mark_w1(run_dir: Path, plan: dict[str, Any]) -> None:
    stage_dir = _stage_path(run_dir, "W1")
    if is_complete(run_dir, "W1"):
        return
    work = _work_path(run_dir, "W1")
    if work.exists():
        remove_tree(work)
    work.mkdir(parents=True)
    atomic_write_json(work / "plan.json", plan)
    checksums = {
        "schema_version": "B-W1-manifest-v1",
        "stage": "W1",
        "synthetic": True,
        "plan_sha256": plan["plan_sha256"],
        "config_sha256": plan["config_sha256"],
        "code_identity_sha256": plan["code_identity_sha256"],
        "artifact_hashes": {"plan.json": sha256_file(work / "plan.json")},
        "pipeline_complete": False,
    }
    atomic_write_json(work / "checksums.json", checksums)
    manifest = dict(checksums)
    manifest["created_utc"] = utc_stamp()
    atomic_write_json(work / "manifest.json", manifest)
    complete = {
        "stage": "W1",
        "status": "complete",
        "synthetic": True,
        "checksums_sha256": sha256_file(work / "checksums.json"),
        "manifest_sha256": sha256_file(work / "manifest.json"),
        "parent_hashes": {"config": plan["config_sha256"]},
        "code_identity_sha256": plan["code_identity_sha256"],
        "pipeline_complete": False,
    }
    atomic_write_json(work / "COMPLETE.json", complete)
    from tools.b_workflow.io import publish_directory

    publish_directory(work, stage_dir)


def _parent_hashes(run_dir: Path, stage_id: str, plan: dict[str, Any]) -> dict[str, str]:
    hashes = {
        "config": plan["config_sha256"],
        "plan": plan["plan_sha256"],
        "code_identity": plan["code_identity_sha256"],
    }
    for dep in STAGE_DEPS[stage_id]:
        complete = load_complete(run_dir, dep)
        if complete is None:
            _fail(f"stage={stage_id} reason=missing-parent {dep}", 3, stage_id)
        checksums = _stage_path(run_dir, dep) / "checksums.json"
        hashes[f"parent:{dep}"] = sha256_file(checksums)
    return hashes


def _parents_match(run_dir: Path, stage_id: str, plan: dict[str, Any]) -> bool:
    complete = load_complete(run_dir, stage_id)
    if complete is None:
        return False
    expected = _parent_hashes(run_dir, stage_id, plan)
    stored = complete.get("parent_hashes") or {}
    for key, value in expected.items():
        if stored.get(key) != value:
            return False
    if complete.get("code_identity_sha256") != plan["code_identity_sha256"]:
        return False
    return True


def _execute_stage(
    stage_id: str,
    *,
    config: dict[str, Any],
    plan: dict[str, Any],
    repo_root: Path,
    run_dir: Path,
    interpreter: str,
) -> None:
    parent = _parent_hashes(run_dir, stage_id, plan)
    identity = plan["code_identity_sha256"]
    if stage_id == "W2":
        run_acquire(
            config["sources"],
            repo_root=repo_root,
            stage_dir=_stage_path(run_dir, "W2"),
            parent_hashes=parent,
            code_identity_sha256=identity,
            interpreter=interpreter,
        )
        return
    if stage_id == "W3":
        run_cohort(
            config,
            repo_root=repo_root,
            w2_dir=_stage_path(run_dir, "W2"),
            stage_dir=_stage_path(run_dir, "W3"),
            parent_hashes=parent,
            code_identity=identity,
            interpreter=interpreter,
        )
        return
    if stage_id == "W4":
        run_features(
            config,
            repo_root=repo_root,
            w3_dir=_stage_path(run_dir, "W3"),
            stage_dir=_stage_path(run_dir, "W4"),
            parent_hashes=parent,
            code_identity=identity,
            interpreter=interpreter,
        )
        return
    if stage_id == "W5":
        run_fold_develop(
            config,
            repo_root=repo_root,
            w3_dir=_stage_path(run_dir, "W3"),
            w4_dir=_stage_path(run_dir, "W4"),
            stage_dir=_stage_path(run_dir, "W5"),
            parent_hashes=parent,
            code_identity=identity,
            interpreter=interpreter,
        )
        return
    _fail(f"stage-not-implemented:{stage_id.lower()}", 5, stage_id)


def run_workflow(
    *,
    config_path: Path,
    run_dir: Path,
    repo_root: Path,
    mode: str,
    through: str,
    resume: bool,
    interpreter: str | None = None,
) -> dict[str, Any]:
    if mode != "synthetic":
        _fail("reason=mode-must-be-synthetic", 2)
    interp = interpreter or sys.executable
    log: list[dict[str, Any]] = []
    if through not in STAGE_ORDER:
        _fail(f"reason=unknown-through {through}", 2)

    if resume:
        if not (run_dir / "plan.json").is_file():
            _fail("reason=resume-missing-plan", 2)
        plan = json_no_dups((run_dir / "plan.json").read_bytes())
        config_path = Path(plan["config_path"])
        repo_root = Path(plan["repo_root"])
        config = load_config(config_path, repo_root=repo_root)
        current = build_plan(config_path, repo_root=repo_root, interpreter=plan["interpreter"])
        if current["config_sha256"] != plan["config_sha256"] or current["code_identity_sha256"] != plan["code_identity_sha256"]:
            log.append({"action": "plan-identity-changed", "synthetic": True})
            invalidate(run_dir, "W1", log)
            plan = current
            _write_plan(run_dir, plan)
        interp = plan["interpreter"]
    else:
        if run_dir.exists() and any(run_dir.iterdir()):
            _fail(f"reason=output-must-be-empty path={run_dir}", 4)
        run_dir.mkdir(parents=True, exist_ok=True)
        config = load_config(config_path, repo_root=repo_root)
        plan = build_plan(config_path, repo_root=repo_root, interpreter=interp)
        _write_plan(run_dir, plan)

    if config["purpose"] == "synthetic-test" and mode != "synthetic":
        _fail("reason=synthetic-config-requires-synthetic-mode", 2)

    executed: list[str] = []
    skipped: list[str] = []
    stop_reason = None
    failed_stage = None
    try:
        for stage_id in STAGE_ORDER:
            if STAGE_ORDER.index(stage_id) > STAGE_ORDER.index(through):
                break
            work = _work_path(run_dir, stage_id)
            if work.exists() and not is_complete(run_dir, stage_id):
                log.append({"action": "discard-incomplete", "stage": stage_id, "synthetic": True})
                remove_tree(work)
            if is_complete(run_dir, stage_id):
                ok, reason = verify_complete_stage(run_dir, stage_id)
                parents_ok = True
                if stage_id != "W1":
                    try:
                        parents_ok = _parents_match(run_dir, stage_id, plan)
                    except PipelineFailure:
                        parents_ok = False
                if ok and parents_ok:
                    skipped.append(stage_id)
                    log.append({"action": "skip-complete", "stage": stage_id, "synthetic": True})
                    continue
                log.append(
                    {
                        "action": "stale-or-corrupt",
                        "stage": stage_id,
                        "reason": reason if not ok else "parent-hash-mismatch",
                        "synthetic": True,
                    }
                )
                invalidate(run_dir, stage_id, log)
            if stage_id not in IMPLEMENTED:
                stop_reason = f"stage-not-implemented:{stage_id.lower()}"
                failed_stage = stage_id
                _fail(stop_reason, 5, stage_id)
            if stage_id == "W1":
                _mark_w1(run_dir, plan)
                executed.append("W1")
                log.append({"action": "execute", "stage": "W1", "synthetic": True})
                continue
            _execute_stage(
                stage_id,
                config=config,
                plan=plan,
                repo_root=repo_root,
                run_dir=run_dir,
                interpreter=interp,
            )
            executed.append(stage_id)
            log.append({"action": "execute", "stage": stage_id, "synthetic": True})
    except PipelineFailure as exc:
        failed_stage = exc.stage or failed_stage
        stop_reason = str(exc)
        receipt = {
            "status": "failed",
            "synthetic": True,
            "pipeline_complete": False,
            "failed_stage": failed_stage,
            "reason": stop_reason,
            "executed": executed,
            "skipped": skipped,
            "through": through,
            "log": log,
            "created_utc": utc_stamp(),
        }
        atomic_write_json(run_dir / "run_status.json", receipt)
        raise

    pipeline_complete = through == "W8" and failed_stage is None and "W8" in IMPLEMENTED
    status = {
        "status": "complete-through" if failed_stage is None else "failed",
        "synthetic": True,
        "synthetic_label": plan["synthetic_label"],
        "pipeline_complete": False,
        "through": through,
        "executed": executed,
        "skipped": skipped,
        "failed_stage": failed_stage,
        "reason": stop_reason,
        "plan_sha256": plan["plan_sha256"],
        "config_sha256": plan["config_sha256"],
        "code_identity_sha256": plan["code_identity_sha256"],
        "log": log,
        "created_utc": utc_stamp(),
        "note": "W1-W5 synthetic execution is not a completed Paper B pipeline.",
    }
    if pipeline_complete:
        status["pipeline_complete"] = True
    atomic_write_json(run_dir / "run_status.json", status)
    return status
