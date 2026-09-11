"""CLI for the partial synthetic Paper B W7 report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.b_report.report import run_report
from tools.b_workflow.io import PipelineFailure, code_identity_sha256
from tools.b_workflow.stages import CODE_PATHS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the traceable Paper B W7 report.")
    parser.add_argument("--w3", required=True, type=Path)
    parser.add_argument("--w5", required=True, type=Path)
    parser.add_argument("--w6", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = (args.repo_root or Path.cwd()).resolve()
    try:
        run_report(
            w3_dir=args.w3.resolve(),
            w5_dir=args.w5.resolve(),
            w6_dir=args.w6.resolve(),
            stage_dir=args.output.resolve(),
            parent_hashes={},
            code_identity=code_identity_sha256(repo_root, CODE_PATHS),
            interpreter=sys.executable,
        )
        return 0
    except PipelineFailure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
