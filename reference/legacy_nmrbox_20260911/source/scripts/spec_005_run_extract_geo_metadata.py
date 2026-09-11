#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run extract-geo-metadata across Spec-005 GEO accessions.")
    parser.add_argument("--reconciled-tsv", required=True)
    parser.add_argument("--tool-python", required=True)
    parser.add_argument("--tool-script", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--status-out", required=True)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    reconciled_rows = read_tsv(Path(args.reconciled_tsv))
    accessions = sorted({r.get("accession", "").strip().upper() for r in reconciled_rows if r.get("accession", "").strip().upper().startswith("GSE")})
    if args.limit and args.limit > 0:
        accessions = accessions[: args.limit]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status_rows: list[dict[str, str]] = []

    for acc in accessions:
        out_tsv = out_dir / f"{acc}.tsv"
        if args.skip_existing and out_tsv.exists():
            status_rows.append(
                {
                    "accession": acc,
                    "status": "skipped_existing",
                    "output_tsv": str(out_tsv),
                    "error": "",
                }
            )
            continue

        cmd = [args.tool_python, args.tool_script, acc]
        run = subprocess.run(
            cmd,
            cwd=str(out_dir),
            capture_output=True,
            text=True,
        )
        status_rows.append(
            {
                "accession": acc,
                "status": "ok" if run.returncode == 0 else "failed",
                "output_tsv": str(out_tsv if out_tsv.exists() else ""),
                "error": (run.stderr or run.stdout).strip()[:2000] if run.returncode != 0 else "",
            }
        )

    write_tsv(
        Path(args.status_out),
        ["accession", "status", "output_tsv", "error"],
        status_rows,
    )
    n_ok = sum(1 for r in status_rows if r["status"] == "ok")
    n_fail = sum(1 for r in status_rows if r["status"] == "failed")
    n_skip = sum(1 for r in status_rows if r["status"] == "skipped_existing")
    print(f"Wrote {args.status_out}; ok={n_ok}; failed={n_fail}; skipped_existing={n_skip}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
