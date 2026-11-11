"""Run Paper A outcome-free or outcome-dependent biology workflows."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from tools.a_bio.fixtures import write_fixture
from tools.a_bio.runner import MetaRankingContract, run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.a_bio")
    commands = parser.add_subparsers(dest="command", required=True)

    fixture = commands.add_parser("fixture", help="write a fully invented, hash-matched cohort")
    fixture.add_argument("--runtime", type=Path, default=Path(".scratch/a_bio_fixture/runtime"))
    fixture.add_argument("--cohort", default="invented_a_bio_demo")
    fixture.add_argument(
        "--endpoint-family",
        choices=("orr", "clinical_benefit", "source_label"),
        default="orr",
    )
    fixture.add_argument("--sample-count", type=int, default=8)
    fixture.add_argument("--cancer", choices=(
        "melanoma", "lung", "kidney", "bladder", "gastric", "liver", "head_and_neck",
    ), default="melanoma")

    action = commands.add_parser("run", help="run an A-BIO route over signed or invented cohorts")
    action.add_argument("--route", required=True, choices=("outcome-free", "outcomes"))
    action.add_argument("--cohort", action="append", required=True, help="cohort identifier; repeat for multiple cohorts")
    action.add_argument("--runtime", type=Path, help="cohort runtime; THESIS_RUNTIME is used when omitted")
    action.add_argument("--results", type=Path, help="results root; THESIS_RESULTS is used when omitted")
    action.add_argument(
        "--retention-dir",
        type=Path,
        help="private R-stage retention root; defaults to a hidden sibling work directory",
    )
    action.add_argument(
        "--synthetic-manifest",
        action="append",
        type=Path,
        default=[],
        help="explicit invented provenance for a synthetic cohort; repeat per synthetic cohort",
    )
    action.add_argument(
        "--allow-outcomes",
        action="store_true",
        help="future release gate for response-associated analysis on signed real cohorts",
    )
    action.add_argument("--adjusted", action="store_true", help="request adjusted models")
    action.add_argument(
        "--meta-ranking-contract-id",
        help="explicit contract ID for invented-only post-meta enrichment checks",
    )
    action.add_argument(
        "--meta-ranking-statistic",
        choices=("estimate", "estimate_over_se"),
        help="explicit pooled ranking statistic; no real-data default is signed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fixture":
            manifest = write_fixture(
                args.runtime,
                cohort_id=args.cohort,
                endpoint_family=args.endpoint_family,
                sample_count=args.sample_count,
                cancer=args.cancer,
            )
            sys.stdout.write(json.dumps({
                "cohort_id": args.cohort,
                "data_classification": "synthetic",
                "manifest": str(manifest),
            }, sort_keys=True) + "\n")
            return 0

        if bool(args.meta_ranking_contract_id) != bool(args.meta_ranking_statistic):
            raise ValueError("Meta-ranking contract ID and statistic must be supplied together")
        meta_ranking_contract = (
            MetaRankingContract(
                contract_id=args.meta_ranking_contract_id,
                statistic=args.meta_ranking_statistic,
            )
            if args.meta_ranking_contract_id else None
        )
        summary = run(
            args.route,
            cohorts=tuple(args.cohort),
            runtime=args.runtime,
            results=args.results,
            synthetic_manifests=tuple(args.synthetic_manifest),
            retention_dir=args.retention_dir,
            allow_outcomes=args.allow_outcomes,
            adjusted=args.adjusted,
            meta_ranking_contract=meta_ranking_contract,
        )
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    sys.stdout.write(json.dumps(summary, sort_keys=True, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
