"""Paper A pre-merge gate.

    python -m tools.gate privacy [--staged | PATH ...]
    python -m tools.gate tests [--receipt FILE] [--quick]

`tests` runs the Paper A suite once, with THESIS_RUNTIME pointed at a fresh empty
directory, so a test that silently needs real cohort data fails instead of reading it.
Every test sets or clears THESIS_RUNTIME itself where it matters, so a second
"unset" run adds nothing. No test is deselected. It then runs the single-cell suite
in its own environment. With --receipt it writes one JSON receipt for the merge
(commit, commands, summaries, failures, exit codes, privacy result) and the full
pytest logs next to it; keep both outside Git.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.gate.privacy import scan_paths, staged_paths

ROOT = Path(__file__).resolve().parents[2]

PAPER_A_TESTS = [
    "tests/a_cohorts", "tests/r_bridge", "tests/a_scoring", "tests/a_meta", "tests/a_bulk",
    "tests/sc", "tests/freeze_audit", "tests/a_bio", "tests/a_comp", "tests/a_comparators",
    "tests/a_p1", "tests/a_p2", "tests/a1", "tests/a_report",
]
SC_TESTS = ["tests/sc", "tests/a_report"]


def _find_env(name: str) -> Path | None:
    for parent in [ROOT, *ROOT.parents]:
        candidate = parent / "envs" / name / "bin" / "python"
        if candidate.exists():
            return candidate
    return None


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _pytest(python: Path, targets: list[str], scratch: Path, label: str, log_dir: Path | None) -> dict:
    runtime = scratch / "empty_runtime"
    runtime.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "THESIS_RUNTIME": str(runtime),
        "PYTHONHASHSEED": "48",
        "PYTHONDONTWRITEBYTECODE": "1",
        "MPLCONFIGDIR": str(scratch / f"mpl_{label}"),
    }
    command = [str(python), "-m", "pytest", "-p", "no:cacheprovider", f"--basetemp={scratch / label}", "-q", "-rs", *targets]
    started = time.monotonic()
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    failures = [l.split(" - ")[0] for l in lines if l.startswith(("FAILED ", "ERROR "))]
    sys.stdout.write("\n".join(failures + lines[-5:]) + "\n")
    sys.stderr.write(proc.stderr[-2000:])
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"gate_{label}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    summary = next((l for l in reversed(lines) if l.strip()), "")
    shown = ["python", *command[1:5], "--basetemp=<tmp>", *command[6:]]
    return {
        "label": label,
        "command": "THESIS_RUNTIME=<empty tmp> " + " ".join(shown),
        "exit_code": proc.returncode,
        "summary": summary.strip("= "),
        "failures": failures,
        "seconds": round(time.monotonic() - started),
    }


def _privacy(paths: list[str]) -> dict:
    hits = scan_paths(ROOT, paths)
    for hit in hits:
        print(f"privacy: {hit.path}:{hit.line}: {hit.kind}", file=sys.stderr)
    return {"files": len(paths), "hits": len(hits), "passed": not hits}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.gate")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("privacy", help="scan staged files (default) or given paths")
    p.add_argument("paths", nargs="*")
    t = sub.add_parser("tests", help="run the Paper A suite once and the single-cell suite")
    t.add_argument("--receipt", type=Path, help="write the merge receipt here (outside Git)")
    t.add_argument("--targets", nargs="+", help="override the test directories (for module work)")
    t.add_argument("--no-sc", action="store_true", help="skip the single-cell environment run")
    args = parser.parse_args(argv)

    if args.action == "privacy":
        result = _privacy(args.paths or staged_paths(ROOT))
        print(json.dumps(result))
        return 0 if result["passed"] else 1

    if not _git("rev-parse", "--git-dir"):
        print("run the gate inside a Git checkout; several tests need Git", file=sys.stderr)
        return 2
    python = _find_env("dav-pipeline")
    if python is None:
        print("envs/dav-pipeline not found above the repository", file=sys.stderr)
        return 2
    runs = []
    with tempfile.TemporaryDirectory(prefix="paper_a_gate_") as tmp:
        scratch = Path(tmp)
        log_dir = args.receipt.parent if args.receipt else None
        runs.append(_pytest(python, args.targets or PAPER_A_TESTS, scratch, "paper_a", log_dir))
        sc_python = _find_env("sc-analysis")
        if not args.no_sc and not args.targets and sc_python is not None:
            runs.append(_pytest(sc_python, SC_TESTS, scratch, "single_cell", log_dir))
    receipt = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "uncommitted_tracked_changes": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "runs": runs,
        "privacy_staged": _privacy(staged_paths(ROOT)) if _git("rev-parse", "--git-dir") else None,
        "passed": all(r["exit_code"] == 0 for r in runs),
    }
    text = json.dumps(receipt, indent=1)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
