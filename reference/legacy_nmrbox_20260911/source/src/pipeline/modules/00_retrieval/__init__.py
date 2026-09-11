"""Stage 00: retrieval."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

from src.pipeline.common.io import (
    build_source_uri,
    infer_source_db,
    read_tsv,
    split_accessions,
    write_tsv,
)

from .errors import ErrorClass
from .geo import _geo_series_prefix
from .http import _download_url_if_missing, build_planned_downloads, cleanup_stale_part_files

LEDGER_COLUMNS = [
    "cohort_id",
    "input_accession",
    "gse_id",
    "srp_id",
    "srx_id",
    "srr_id",
    "bioproject_id",
    "source_db",
    "source_uri",
    "retrieval_status",
    "retrieval_timestamp",
    "retrieval_note",
]


def _timestamp_utc() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat()


def _join_tokens(tokens: Iterable[str], prefixes: tuple[str, ...]) -> str:
    matched = [token for token in tokens if token.startswith(prefixes)]
    return ";".join(matched)


def format_retrieval_note(entries: list[tuple[str, str, str, str]]) -> str:
    chunks: list[str] = []
    for accession, file_kind, error_class, detail in entries:
        prefix = f"{accession}:{file_kind}:{error_class}"
        if detail:
            chunks.append(f"{prefix}:{detail}")
        else:
            chunks.append(prefix)
    return "; ".join(chunks)


def _download_geo_family_soft(gse_id: str, cohort_dir: Path) -> tuple[int, int, list[tuple[str, str, str, str]]]:
    url = (
        f"https://ftp.ncbi.nlm.nih.gov/geo/series/{_geo_series_prefix(gse_id)}/"
        f"{gse_id}/soft/{gse_id}_family.soft.gz"
    )
    dest = cohort_dir / f"{gse_id}_family.soft.gz"
    ok, err = _download_url_if_missing(url, dest)
    if ok:
        return 1, 1, []
    return 1, 0, [(gse_id, "soft", err, "")]


def _download_runinfo(
    accession: str,
    cohort_dir: Path,
) -> tuple[int, int, list[tuple[str, str, str, str]]]:
    url = f"https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc={quote_plus(accession)}"
    dest = cohort_dir / f"{accession}_runinfo.csv"
    ok, err = _download_url_if_missing(url, dest)
    if ok:
        text = dest.read_text(encoding="utf-8", errors="ignore").strip()
        if not text or "Run," not in text:
            dest.unlink(missing_ok=True)
            return 1, 0, [(accession, "runinfo", ErrorClass.EMPTY_RESPONSE.value, "missing Run,")]
        return 1, 1, []
    return 1, 0, [(accession, "runinfo", err, "")]


def retrieval_run(
    discovery_manifest: Path,
    out_dir: Path,
    no_download: bool = False,
    dry_run: bool = False,
    run_manifest: Path | None = None,
) -> int:
    records = read_tsv(Path(discovery_manifest))
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    ledger_file = out_root / "retrieval_ledger.tsv"
    planned_file = out_root / "planned_downloads.tsv"

    cleanup_stale_part_files(out_root / "downloads", max_age_seconds=3600)

    cohort_counts = Counter((row.get("cohort_id", "") or "").strip() for row in records)
    ledger_rows: list[dict[str, str]] = []
    planned_rows: list[dict[str, str]] = []

    for rec in records:
        cohort_id = (rec.get("cohort_id", "") or "").strip()
        raw_accession = (rec.get("accession", "") or "").strip()
        tokens = split_accessions(raw_accession)
        cohort_dir = out_root / "downloads" / cohort_id
        attempts = 0
        successes = 0
        errors: list[tuple[str, str, str, str]] = []

        if cohort_counts.get(cohort_id, 0) > 1:
            errors.append((raw_accession or "unknown", "manifest", ErrorClass.MANIFEST_ERROR.value, "duplicate_cohort_id"))
            retrieval_status = "failed"
            retrieval_note = format_retrieval_note(errors)
        elif dry_run:
            planned_rows.extend(build_planned_downloads(cohort_id, raw_accession, tokens, cohort_dir))
            retrieval_status = "not_started"
            retrieval_note = "download_planned_dry_run"
        elif no_download:
            retrieval_status = "not_started"
            retrieval_note = "download_skipped_by_flag"
        else:
            for token in tokens:
                if token.startswith("GSE"):
                    a, s, e = _download_geo_family_soft(token, cohort_dir)
                elif token.startswith(("SRP", "SRX", "SRR", "PRJ")):
                    a, s, e = _download_runinfo(token, cohort_dir)
                else:
                    continue
                attempts += a
                successes += s
                errors.extend(e)

            if attempts == 0:
                retrieval_status = "not_started"
                retrieval_note = "no_supported_accessions_for_download"
            elif successes == attempts:
                retrieval_status = "downloaded"
                retrieval_note = f"downloaded {successes}/{attempts}"
            elif successes == 0:
                retrieval_status = "failed"
                retrieval_note = format_retrieval_note(errors) or f"downloaded 0/{attempts}"
            else:
                retrieval_status = "partial"
                if errors:
                    retrieval_note = (
                        f"downloaded {successes}/{attempts}; {format_retrieval_note(errors)}"
                    )
                else:
                    retrieval_note = f"downloaded {successes}/{attempts}"

        ledger_rows.append(
            {
                "cohort_id": cohort_id,
                "input_accession": raw_accession,
                "gse_id": _join_tokens(tokens, ("GSE", "GSM", "GPL")),
                "srp_id": _join_tokens(tokens, ("SRP",)),
                "srx_id": _join_tokens(tokens, ("SRX",)),
                "srr_id": _join_tokens(tokens, ("SRR",)),
                "bioproject_id": _join_tokens(tokens, ("PRJ", "BIOPROJECT")),
                "source_db": infer_source_db(tokens),
                "source_uri": build_source_uri(tokens),
                "retrieval_status": retrieval_status,
                "retrieval_timestamp": _timestamp_utc(),
                "retrieval_note": retrieval_note,
            }
        )

    write_tsv(ledger_file, fieldnames=LEDGER_COLUMNS, rows=ledger_rows)
    if dry_run:
        write_tsv(
            planned_file,
            fieldnames=["cohort_id", "accession", "file_kind", "url", "dest_path"],
            rows=planned_rows,
        )
    if run_manifest:
        run_manifest = Path(run_manifest)
        run_manifest.parent.mkdir(parents=True, exist_ok=True)
        run_manifest.write_text(
            "stage: retrieval\nstatus: complete\n",
            encoding="utf-8",
        )
    return 0
