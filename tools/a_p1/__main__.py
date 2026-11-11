"""Command-line interface for Paper A A-P1 endpoint sensitivity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .analysis import analyze_tsv
from .demo import run_demo
from .provenance import assert_allowed_input_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.a_p1")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="analyze a provenance-bound selected-field table")
    analyze.add_argument("--input", required=True, type=Path)
    analyze.add_argument("--provenance", required=True, type=Path)
    analyze.add_argument("--out", required=True, type=Path)
    analyze.add_argument("--synthesis-contract", type=Path)
    analyze.add_argument("--learned-input", type=Path)
    analyze.add_argument("--learned-provenance", type=Path)
    analyze.add_argument(
        "--allow-outcomes",
        action="store_true",
        help="allow a real outcome route only when its provenance records an explicit release ID",
    )
    demo = commands.add_parser("demo", help="run the clearly labelled invented-data demonstration")
    demo.add_argument("--out", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "demo":
        result = run_demo(args.out)
        print(json.dumps({
            "analysis_id": result["analysis_id"],
            "data_classification": result["data_classification"],
            "synthetic_scope": result["synthetic_scope"],
            "study_n": len(result["studies"]),
            "synthesis_status": result["synthesis"]["status"],
        }, sort_keys=True))
        return 0

    result = analyze_tsv(
        args.input,
        args.provenance,
        args.out,
        synthesis_contract_path=args.synthesis_contract,
        learned_input_path=args.learned_input,
        learned_provenance_path=args.learned_provenance,
        allow_outcomes=args.allow_outcomes,
    )
    print(json.dumps({
        "analysis_id": result["analysis_id"],
        "data_classification": result["data_classification"],
        "study_n": len(result["studies"]),
        "synthesis_status": result["synthesis"]["status"],
        "output": str(args.out),
    }, sort_keys=True))
    return 0


def _read_json_object(path: Path) -> dict:
    path = assert_allowed_input_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("A-P1 JSON contract must be an object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
