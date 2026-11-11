"""Patient-free Paper A comparator readiness command."""
from __future__ import annotations

import argparse

from .readiness import method_status, method_statuses


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.a_comparators")
    commands = parser.add_subparsers(dest="command", required=True)
    readiness = commands.add_parser("readiness", help="List method readiness and blockers")
    readiness.add_argument("--method", help="Show one registered method")
    args = parser.parse_args(argv)

    try:
        rows = [method_status(args.method)] if args.method else method_statuses()
    except KeyError as error:
        raise SystemExit(str(error)) from None

    print("method_id\timplementation_state\tadmission_blocker")
    for row in rows:
        print(
            f"{row['method_id']}\t{row['implementation_state']}\t"
            f"{row['admission_blocker']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
