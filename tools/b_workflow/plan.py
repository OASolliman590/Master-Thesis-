"""Build the W1 plan artifact."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tools.b_workflow.config import load_config
from tools.b_workflow.io import canonical_json_bytes, code_identity_sha256, sha256_bytes
from tools.b_workflow.stages import CODE_PATHS, IMPLEMENTED, STAGE_DEPS, STAGE_GATES, STAGE_ORDER


PLAN_SCHEMA = "B-workflow-plan-v1"


def build_plan(
    config_path: Path,
    *,
    repo_root: Path,
    interpreter: str | None = None,
) -> dict[str, Any]:
    config = load_config(config_path, repo_root=repo_root)
    interp = interpreter or sys.executable
    identity = code_identity_sha256(repo_root, CODE_PATHS)
    input_hashes = {"config": config["_config_sha256"]}
    for source in config["sources"]:
        input_hashes[f"source:{source['source_id']}:expected"] = source["expected_sha256"]
    from tools.b_workflow.io import sha256_file

    for rel in (
        config["w3"]["annotation"]["gene_universe_path"],
        config["w3"]["annotation"]["probe_map_path"],
        config["w3"]["annotation"]["gene_map_path"],
        config["w3"]["identity"]["specimen_map_path"],
        config["w3"]["identity"]["covariate_path"],
    ):
        path = repo_root / rel
        if not path.is_file():
            from tools.b_workflow.io import PipelineFailure

            raise PipelineFailure(f"config reason=missing-input {rel}", 3)
        input_hashes[f"file:{rel}"] = sha256_file(path)
    stages = []
    for stage_id in STAGE_ORDER:
        implemented = stage_id in IMPLEMENTED
        commands: list[list[str]]
        if stage_id == "W1":
            commands = [[interp, "-m", "tools.b_workflow", "plan", "--config", str(config_path)]]
        elif stage_id == "W2":
            commands = [[interp, "-m", "tools.b_workflow", "run", "--mode", "synthetic", "--config", str(config_path), "--through", "W2"]]
        elif stage_id == "W3":
            commands = [[interp, "-m", "tools.b_workflow", "run", "--mode", "synthetic", "--config", str(config_path), "--through", "W3"]]
        elif stage_id == "W4":
            commands = [[interp, "-m", "tools.b_workflow", "run", "--mode", "synthetic", "--config", str(config_path), "--through", "W4"]]
        else:
            commands = [[interp, "-m", "tools.b_workflow", "run", "--mode", "synthetic", "--config", str(config_path), "--through", stage_id]]
        stages.append(
            {
                "id": stage_id,
                "depends_on": list(STAGE_DEPS[stage_id]),
                "implemented": implemented,
                "blocked_reason": None if implemented else f"stage-not-implemented:{stage_id.lower()}",
                "scientific_gates": list(STAGE_GATES[stage_id]),
                "commands": commands,
                "synthetic": True,
            }
        )
    outstanding = []
    for stage in stages:
        if not stage["implemented"]:
            outstanding.append(stage["blocked_reason"])
        outstanding.extend(
            gate
            for gate in stage["scientific_gates"]
            if gate.startswith("E") or gate.startswith("stage-not-implemented") or "not-inferred" in gate
        )
    plan = {
        "schema_version": PLAN_SCHEMA,
        "synthetic": True,
        "synthetic_label": config["synthetic_label"],
        "purpose": config["purpose"],
        "pipeline_complete": False,
        "config_path": str(Path(config["_config_path"])),
        "config_sha256": config["_config_sha256"],
        "code_identity_sha256": identity,
        "interpreter": interp,
        "repo_root": str(repo_root),
        "input_hashes": input_hashes,
        "stages": stages,
        "outstanding_scientific_gates": sorted(set(outstanding)),
        "note": (
            "W1-W4 may execute in synthetic mode. A W1-W4 run is not a completed Paper B pipeline. "
            "Default continuation past W4 fails with stage-not-implemented:w5."
        ),
    }
    plan["plan_sha256"] = sha256_bytes(
        canonical_json_bytes({k: v for k, v in plan.items() if k != "plan_sha256"})
    )
    return plan
