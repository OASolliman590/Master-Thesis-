"""CLI for the synthetic-first A-COMP workflow."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import ACompError, analyze_real_request, run_real_deconvolution, run_synthetic_demo


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.a_comp")
    commands = parser.add_subparsers(dest="command", required=True)

    synthetic = commands.add_parser("synthetic-demo", help="Run invented data through locked R and A-META")
    synthetic.add_argument("--out", type=Path, required=True)

    deconvolve = commands.add_parser("deconvolve", help="Run a gated, outcome-free cohort deconvolution")
    deconvolve.add_argument("--cohort", required=True)
    deconvolve.add_argument("--pin", type=Path, required=True)
    deconvolve.add_argument("--expression", type=Path, required=True)
    deconvolve.add_argument("--manifest", type=Path, required=True)
    deconvolve.add_argument("--out", type=Path, required=True)

    analyze = commands.add_parser("analyze", help="Run a gated response/composition analysis")
    analyze.add_argument("--cohort", required=True)
    analyze.add_argument("--pin", type=Path, required=True)
    analyze.add_argument("--expression", type=Path, required=True)
    analyze.add_argument("--clinical", type=Path, required=True)
    analyze.add_argument("--analysis-contract", type=Path)
    analyze.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "synthetic-demo":
            result = run_synthetic_demo(args.out)
        elif args.command == "deconvolve":
            result = run_real_deconvolution(
                cohort_id=args.cohort,
                pin_path=args.pin,
                expression_path=args.expression,
                manifest_path=args.manifest,
                output_dir=args.out,
            )
        else:
            result = analyze_real_request(
                cohort_id=args.cohort,
                pin_path=args.pin,
                expression_path=args.expression,
                clinical_path=args.clinical,
                analysis_contract_path=args.analysis_contract,
                output_dir=args.out,
            )
    except ACompError as error:
        print(f"A-COMP REFUSED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
