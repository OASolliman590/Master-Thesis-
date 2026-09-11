#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
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


def most_common(values: list[str]) -> str:
    clean = [v.strip() for v in values if v and v.strip()]
    if not clean:
        return ""
    return Counter(clean).most_common(1)[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prefill study-level curation sheet from supplementary metadata.")
    parser.add_argument("--curation-sheet", required=True)
    parser.add_argument("--supplementary-merged", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    curation_rows = read_tsv(Path(args.curation_sheet))
    supplementary_rows = read_tsv(Path(args.supplementary_merged))

    by_cohort: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in supplementary_rows:
        cohort_id = row.get("cohort_id", "").strip()
        if cohort_id:
            by_cohort[cohort_id].append(row)

    for row in curation_rows:
        cohort_id = row.get("cohort_id", "").strip()
        sup_rows = by_cohort.get(cohort_id, [])
        if not sup_rows:
            continue

        response_values = [r.get("response_label_supplementary", "") for r in sup_rows]
        n_responder = sum(1 for v in response_values if v == "responder")
        n_nonresponder = sum(1 for v in response_values if v == "non_responder")
        timing_values = [r.get("timing_category_supplementary", "") for r in sup_rows]
        disease_values = [r.get("disease_supplementary", "") for r in sup_rows]

        if not row.get("confirmed_disease", "").strip():
            inferred_disease = most_common(disease_values)
            if inferred_disease:
                row["confirmed_disease"] = inferred_disease

        if not row.get("confirmed_timing_schema", "").strip():
            inferred_timing = most_common(timing_values)
            if inferred_timing:
                row["confirmed_timing_schema"] = inferred_timing

        if not row.get("confirmed_response_schema", "").strip() and (n_responder > 0 or n_nonresponder > 0):
            row["confirmed_response_schema"] = "supplementary_inferred_rnr"

        if not row.get("responder_count_confirmed", "").strip() and n_responder > 0:
            row["responder_count_confirmed"] = str(n_responder)

        if not row.get("nonresponder_count_confirmed", "").strip() and n_nonresponder > 0:
            row["nonresponder_count_confirmed"] = str(n_nonresponder)

        note = row.get("curation_notes", "").strip()
        prefill_note = "supplementary_prefill_applied"
        row["curation_notes"] = prefill_note if not note else f"{note}; {prefill_note}"

    fieldnames = list(curation_rows[0].keys()) if curation_rows else []
    write_tsv(Path(args.out), fieldnames, curation_rows)
    print(f"Wrote {args.out} ({len(curation_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
