"""CLI for Paper B workflow plan, run and resume."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.b_workflow.io import PipelineFailure, canonical_json_bytes
from tools.b_workflow.plan import build_plan
from tools.b_workflow.run import run_workflow
from tools.b_workflow.stages import STAGE_ORDER


def _print_json(payload: dict) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paper B connected workflow (W1-W8).")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--config", required=True, type=Path)
    plan.add_argument("--output", type=Path, default=None)
    plan.add_argument("--repo-root", type=Path, default=None)

    run = sub.add_parser("run")
    run.add_argument("--mode", required=True, choices=["synthetic"])
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--through", choices=list(STAGE_ORDER), default="W8")
    run.add_argument("--repo-root", type=Path, default=None)

    resume = sub.add_parser("resume")
    resume.add_argument("--output", required=True, type=Path)
    resume.add_argument("--through", choices=list(STAGE_ORDER), default=None)
    resume.add_argument("--mode", choices=["synthetic"], default="synthetic")

    args = parser.parse_args(argv)
    repo_root = (getattr(args, "repo_root", None) or Path.cwd()).resolve()
    try:
        if args.command == "plan":
            payload = build_plan(args.config.resolve(), repo_root=repo_root, interpreter=sys.executable)
            _print_json(payload)
            if args.output is not None:
                from tools.b_workflow.io import atomic_write_json

                out = args.output.resolve()
                if out.suffix.lower() == ".json":
                    atomic_write_json(out, payload)
                else:
                    out.mkdir(parents=True, exist_ok=True)
                    atomic_write_json(out / "plan.json", payload)
            return 0
        if args.command == "run":
            status = run_workflow(
                config_path=args.config.resolve(),
                run_dir=args.output.resolve(),
                repo_root=repo_root,
                mode=args.mode,
                through=args.through,
                resume=False,
                interpreter=sys.executable,
            )
            _print_json(status)
            return 0
        if args.command == "resume":
            run_dir = args.output.resolve()
            through = args.through
            if through is None:
                status_path = run_dir / "run_status.json"
                if status_path.is_file():
                    previous = json.loads(status_path.read_text(encoding="utf-8"))
                    through = previous.get("through") or "W8"
                else:
                    through = "W8"
            status = run_workflow(
                config_path=Path("unused"),
                run_dir=run_dir,
                repo_root=repo_root,
                mode=args.mode,
                through=through,
                resume=True,
                interpreter=sys.executable,
            )
            _print_json(status)
            return 0
        raise PipelineFailure("unknown command", 2)
    except PipelineFailure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
