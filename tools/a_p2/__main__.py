import argparse
import sys
from pathlib import Path

from .build import build
from .product import ProductError, run_development, run_final_evaluation, run_freeze
from tools.r_bridge import RScriptError


def _parser():
    parser = argparse.ArgumentParser(prog="python -m tools.a_p2")
    commands = parser.add_subparsers(dest="command", required=True)

    build_parser = commands.add_parser("build", help="build the frozen A-P2 feature inputs")
    build_parser.add_argument(
        "--runtime",
        help="validated cohort runtime (defaults to THESIS_RUNTIME or the worktree runtime)",
    )
    build_parser.add_argument("--out", help="output directory (defaults to the worktree runtime a_p2/inputs)")

    for name, help_text in (
        ("development", "run synthetic or explicitly released development evaluations"),
        ("freeze", "fit and publish the development equation"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--manifest", required=True, type=Path)
        command.add_argument("--release-record", type=Path, help="approved scoped decision record for a future real run")
        command.add_argument("--allow-outcomes", action="store_true", default=False, help="explicitly enable outcome access when a matching approved user-release record exists")
        command.add_argument("--out", required=True, type=Path)

    final_parser = commands.add_parser("final-evaluate", help="evaluate a frozen equation on one final study")
    final_parser.add_argument("--manifest", required=True, type=Path)
    final_parser.add_argument("--equation", required=True, type=Path)
    final_parser.add_argument("--release-record", type=Path, help="approved scoped decision record bound to this equation and final input")
    final_parser.add_argument("--allow-outcomes", action="store_true", default=False, help="explicitly enable outcome access when a matching approved user-release record exists")
    final_parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            build(runtime=args.runtime, out=args.out)
        elif args.command == "development":
            run_development(args.manifest, args.out, args.release_record, args.allow_outcomes)
        elif args.command == "freeze":
            run_freeze(args.manifest, args.out, args.release_record, args.allow_outcomes)
        elif args.command == "final-evaluate":
            run_final_evaluation(args.manifest, args.equation, args.out, args.release_record, args.allow_outcomes)
    except (ProductError, PermissionError, FileExistsError, OSError, RScriptError) as error:
        print(f"A-P2 {args.command} refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
