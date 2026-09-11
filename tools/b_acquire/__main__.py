"""CLI for W2 immutable acquisition and real-source audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.b_acquire.acquire import run_acquire
from tools.b_acquire.audit import audit_sources
from tools.b_workflow.config import load_config
from tools.b_workflow.io import PipelineFailure, canonical_json_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire or audit Paper B sources.")
    sub = parser.add_subparsers(dest="command", required=True)
    acquire = sub.add_parser("run", help="Acquire configured synthetic/file sources.")
    acquire.add_argument("--config", required=True, type=Path)
    acquire.add_argument("--output", required=True, type=Path)
    acquire.add_argument("--repo-root", type=Path, default=None)

    audit = sub.add_parser("audit", help="Audit real sources without scoring or fitting.")
    audit.add_argument("--manifest", required=True, type=Path)
    audit.add_argument("--output", required=True, type=Path)
    audit.add_argument("--repo-root", type=Path, default=None)
    audit.add_argument("--network", choices=["none"], default="none")
    args = parser.parse_args(argv)
    repo_root = (getattr(args, "repo_root", None) or Path.cwd()).resolve()
    try:
        if args.command == "audit":
            payload = audit_sources(
                repo_root=repo_root,
                manifest_path=args.manifest.resolve(),
                output_path=args.output.resolve(),
                network=args.network,
            )
            sys.stdout.buffer.write(canonical_json_bytes({"status": "complete", "counts": payload["counts"]}))
            return 0
        if args.command == "run":
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
        parser.error("specify audit or run")
    except PipelineFailure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
