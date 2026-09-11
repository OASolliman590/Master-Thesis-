#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Write Spec-005 ingestion reconciliation report.")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--geo-summary", required=True)
    parser.add_argument("--sample-manifest", required=True)
    parser.add_argument("--inspection", required=False, default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    ledger_rows = read_tsv(Path(args.ledger))
    geo_rows = read_tsv(Path(args.geo_summary))
    manifest_rows = read_tsv(Path(args.sample_manifest))
    inspection_rows = read_tsv(Path(args.inspection)) if args.inspection and Path(args.inspection).exists() else []

    manifest_real = [r for r in manifest_rows if "_SYNC_STUB" not in (r.get("sample_id", ""))]
    pre_response_ready = sum(
        1
        for r in inspection_rows
        if (r.get("contrast", "").strip().upper() == "PRE_RESPONSE" and r.get("eligibility", "").strip().lower() == "eligible")
    )
    treatment_delta_ready = sum(
        1
        for r in inspection_rows
        if (r.get("contrast", "").strip().upper() == "TREATMENT_DELTA" and r.get("eligibility", "").strip().lower() == "eligible")
    )

    lines = [
        "# Spec-005 Ingestion Reconciliation Report",
        "",
        "## Cohort Inventory",
        "",
        f"- reconciled_cohorts: {len(ledger_rows)}",
        f"- geo_tables_rows: {len(geo_rows)}",
        "",
        "## Expression Resolution",
        "",
        f"- cohorts_with_primary_expression: {sum(1 for r in geo_rows if (r.get('primary_expression_file', '') or '').strip())}",
        f"- cohorts_with_downloads_folder: {sum(1 for r in geo_rows if (r.get('downloads_folder', '') or '').strip())}",
        "",
        "## Sample Coverage",
        "",
        f"- sample_manifest_rows_total: {len(manifest_rows)}",
        f"- sample_manifest_rows_real: {len(manifest_real)}",
        f"- sync_stub_rows_remaining: {sum(1 for r in manifest_rows if '_SYNC_STUB' in (r.get('sample_id', '')))}",
        "",
        "## Contrast Eligibility",
        "",
        f"- pre_response_eligible_rows: {pre_response_ready}",
        f"- treatment_delta_eligible_rows: {treatment_delta_ready}",
        "",
        "## Curation Tier Assignment",
        "",
        "- pending_manual_assignment: true",
        "",
        "## Evidence Run Summary",
        "",
        "- pending_evidence_execution: true",
        "",
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
