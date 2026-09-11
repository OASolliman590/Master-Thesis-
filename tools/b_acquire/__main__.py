"""CLI for W2 immutable acquisition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.b_acquire.acquire import run_acquire
from tools.b_workflow.config import load_config
from tools.b_workflow.io import PipelineFailure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire configured Paper B sources.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = (args.repo_root or Path.cwd()).resolve()
    try:
        config = load_config(args.config, repo_root=repo_root)
        run_acquire(
            config["sources"],
            repo_root=repo_root,
            stage_dir=args.output.resolve(),
            parent_hashes={"config": config["_config_sha256"]},
            code_identity_sha256="cli-direct",
            interpreter=sys.executable,
        )
        return 0
    except PipelineFailure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
