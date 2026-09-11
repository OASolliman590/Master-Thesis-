#!/usr/bin/env python3
"""Map short NMRbox retrieval cohort IDs to curated sample-manifest cohort IDs."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


FIELDS = [
    "cohort_id",
    "n_samples",
    "n_expression_candidates",
    "source_type_selected",
    "primary_expression_file",
    "downloads_folder",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geo-summary", required=True, type=Path)
    parser.add_argument("--sample-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    short_rows = read_tsv(args.geo_summary)
    short_by_id = {row.get("cohort_id", "").strip().lower(): row for row in short_rows}
    sample_rows = read_tsv(args.sample_manifest)
    curated_ids = sorted({row.get("cohort_id", "").strip() for row in sample_rows if row.get("cohort_id", "").strip()})

    out_rows: list[dict[str, str]] = []
    for cohort_id in curated_ids:
        match = re.match(r"^(gse\d+)", cohort_id, re.IGNORECASE)
        if not match:
            continue
        short_id = match.group(1).lower()
        source = short_by_id.get(short_id)
        if not source:
            continue
        out_rows.append(
            {
                "cohort_id": cohort_id,
                "n_samples": source.get("n_samples", ""),
                "n_expression_candidates": source.get("n_expression_candidates", ""),
                "source_type_selected": source.get("source_type_selected", ""),
                "primary_expression_file": source.get("primary_expression_file", ""),
                "downloads_folder": short_id,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"short_rows\t{len(short_rows)}")
    print(f"curated_rows\t{len(out_rows)}")
    print(f"out\t{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
