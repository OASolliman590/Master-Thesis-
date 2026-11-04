"""Command-line entry point for per-dataset bulk expression analyses."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.a_bulk.core import OutcomeGuardError, analyse, validate_dataset_identifiers
from tools.a_cohorts.view import cohort_metadata, cohort_view


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.a_bulk")
    parser.add_argument("stage", choices=("qc", "pca", "de", "gsea", "panels", "all"))
    parser.add_argument("--cohort", required=True, help="signed dataset identifier")
    parser.add_argument("--paper", required=True, choices=("A", "B"))
    parser.add_argument("--endpoint", default="orr", choices=("orr", "clinical_benefit", "source_label"))
    parser.add_argument("--results", type=Path, help="results root; THESIS_RESULTS is used when omitted")
    parser.add_argument("--gene-sets", type=Path, help="local GMT file for fgsea")
    parser.add_argument(
        "--gene-set-id-type", choices=("symbol", "entrez"),
        help="identifier namespace declared by the local GMT file",
    )
    parser.add_argument(
        "--min-gene-set-overlap", type=int, default=10,
        help="minimum unique GMT/ranking membership overlap for fgsea",
    )
    parser.add_argument("--runtime", type=Path, help="cohort-view runtime, or THESIS_RUNTIME when omitted")
    parser.add_argument(
        "--allow-outcomes", action="store_true",
        help="explicitly permit response-associated analysis on a real cohort",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        validate_dataset_identifiers(args.cohort)
    except ValueError as error:
        parser.error(str(error))
    if args.paper == "B":
        parser.error(
            "Paper B data are not loaded yet; pass a cohort-view-like object to the Python API"
        )

    try:
        # Metadata lookup rejects locked cohorts before the loader can inspect their files.
        cohort_metadata(args.cohort)
        outcome_stage = args.stage in {"de", "gsea", "all"}
        response_pca = args.stage == "pca" and args.allow_outcomes
        if (outcome_stage or response_pca) and not args.allow_outcomes:
            raise OutcomeGuardError(
                "Outcome analysis on a real cohort requires --allow-outcomes; no outcome labels were read"
            )
        view = cohort_view(args.cohort, runtime=args.runtime)
        summary = analyse(
            view,
            args.stage,
            paper="A",
            endpoint=args.endpoint,
            results=args.results,
            gene_sets=args.gene_sets,
            gene_set_id_type=args.gene_set_id_type,
            min_gene_set_overlap=args.min_gene_set_overlap,
            allow_outcomes=args.allow_outcomes,
        )
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        parser.error(str(error))
    sys.stdout.write(json.dumps(summary, sort_keys=True, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
