#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import shutil
import sys
import time
import urllib.request
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh, delimiter="\t")]


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if value is None else str(value) for key, value in row.items()})


def download(url: str, dest: Path, *, timeout: int = 120, retries: int = 3) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest.stat().st_size

    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp, tmp.open("wb") as fh:
                shutil.copyfileobj(resp, fh, length=1024 * 1024)
            if tmp.stat().st_size <= 0:
                raise RuntimeError("downloaded file is empty")
            tmp.replace(dest)
            return dest.stat().st_size
        except Exception:
            if tmp.exists():
                tmp.unlink()
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return 0


def download_first_available(
    urls: list[str],
    dest: Path,
    *,
    timeout: int = 120,
    retries: int = 3,
) -> tuple[str, int]:
    errors: list[str] = []
    for url in urls:
        try:
            size = download(url, dest, timeout=timeout, retries=retries)
            return url, size
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url} -> {exc}")
    raise RuntimeError("; ".join(errors))


def first_line(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.readline().rstrip("\n")
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        return fh.readline().rstrip("\n")


def validate_expression(path: Path) -> tuple[str, str]:
    try:
        header = first_line(path).split("\t")
    except Exception as exc:
        return "fail", f"expression_header_unreadable:{exc}"
    if len(header) < 2:
        return "fail", "expression_header_has_lt2_columns"
    first = header[0].strip().lower()
    if first not in {"gene_id", "ensgene", "gene"} and not first:
        return "warn", f"unexpected_expression_first_column:{header[0]}"
    return "pass", f"expression_columns={len(header)}"


def validate_survival(path: Path) -> tuple[str, str]:
    try:
        header = first_line(path).split("\t")
    except Exception as exc:
        return "fail", f"survival_header_unreadable:{exc}"
    header_set = set(header)
    required = {"OS.time", "OS"}
    missing = sorted(required - header_set)
    if missing:
        return "fail", "survival_missing_columns:" + ",".join(missing)
    return "pass", f"survival_columns={len(header)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download GDC Hub TCGA expression/survival files to T7.")
    parser.add_argument("--input-map", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-map", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    input_map = Path(args.input_map)
    out_dir = Path(args.out_dir)
    out_map = Path(args.out_map)
    audit_path = Path(args.audit)

    rows = read_tsv(input_map)
    map_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []

    for row in rows:
        project = row.get("project", "").strip()
        expr_url = row.get("expression_url", "").strip()
        surv_url = row.get("survival_url", "").strip()
        expr_urls = [
            expr_url,
            f"https://gdc.xenahubs.net/download/{project}.star_counts.tsv.gz",
            f"https://gdc.xenahubs.net/download/{project}.htseq_counts.tsv.gz",
        ]
        surv_urls = [
            surv_url,
            f"https://gdc.xenahubs.net/download/{project}.survival.tsv.gz",
            f"https://gdc.xenahubs.net/download/{project}.survival.tsv",
        ]
        expr_dest = out_dir / f"{project}.star_counts.tsv.gz"
        surv_dest = out_dir / f"{project}.survival.tsv.gz"

        expr_status = "not_started"
        surv_status = "not_started"
        expr_reason = ""
        surv_reason = ""
        expr_size = 0
        surv_size = 0

        try:
            print(f"[{project}] expression -> {expr_dest}", flush=True)
            expr_url, expr_size = download_first_available(expr_urls, expr_dest)
            expr_status, expr_reason = validate_expression(expr_dest)
        except Exception as exc:  # noqa: BLE001
            expr_status = "fail"
            expr_reason = str(exc)

        try:
            print(f"[{project}] survival -> {surv_dest}", flush=True)
            surv_url, surv_size = download_first_available(surv_urls, surv_dest)
            surv_status, surv_reason = validate_survival(surv_dest)
        except Exception as exc:  # noqa: BLE001
            surv_status = "fail"
            surv_reason = str(exc)

        ready = expr_status in {"pass", "warn"} and surv_status == "pass"
        status = "ready" if ready else "failed"
        map_rows.append(
            {
                "project": project,
                "expression_url": expr_url,
                "survival_url": surv_url,
                "local_expression_path": str(expr_dest),
                "local_survival_path": str(surv_dest),
                "status": status,
            }
        )
        audit_rows.append(
            {
                "project": project,
                "expression_status": expr_status,
                "expression_reason": expr_reason,
                "expression_bytes": expr_size,
                "expression_path": str(expr_dest),
                "survival_status": surv_status,
                "survival_reason": surv_reason,
                "survival_bytes": surv_size,
                "survival_path": str(surv_dest),
                "overall_status": status,
            }
        )

    write_tsv(
        out_map,
        [
            "project",
            "expression_url",
            "survival_url",
            "local_expression_path",
            "local_survival_path",
            "status",
        ],
        map_rows,
    )
    write_tsv(
        audit_path,
        [
            "project",
            "expression_status",
            "expression_reason",
            "expression_bytes",
            "expression_path",
            "survival_status",
            "survival_reason",
            "survival_bytes",
            "survival_path",
            "overall_status",
        ],
        audit_rows,
    )

    failed = [row for row in audit_rows if row["overall_status"] != "ready"]
    print(f"Wrote {out_map}")
    print(f"Wrote {audit_path}")
    if failed:
        print(f"{len(failed)} project(s) failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
