#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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
    parser = argparse.ArgumentParser(description="Attach downloads_folder column to geo_tables_summary.tsv")
    parser.add_argument("--geo-summary", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    summary_rows = read_tsv(Path(args.geo_summary))
    ledger_rows = read_tsv(Path(args.ledger))

    folder_by_cohort = {
        row.get("canonical_cohort_id", "").strip(): row.get("t7_folder_name", "").strip()
        for row in ledger_rows
        if row.get("canonical_cohort_id", "").strip()
    }

    for row in summary_rows:
        cohort_id = row.get("cohort_id", "").strip()
        row["downloads_folder"] = folder_by_cohort.get(cohort_id, "")

    fieldnames = list(summary_rows[0].keys()) if summary_rows else []
    if "downloads_folder" not in fieldnames:
        fieldnames.append("downloads_folder")
    else:
        fieldnames = [f for f in fieldnames if f != "downloads_folder"] + ["downloads_folder"]

    write_tsv(Path(args.out), fieldnames, summary_rows)
    print(f"Wrote {args.out} ({len(summary_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
