#!/usr/bin/env python3
"""Confirm sample-level response/timing metadata for candidate GEO ICI cohorts.

This is a metadata-only curation probe for spec 080 external validation. It
downloads GEO series-matrix files, extracts sample characteristics, and reports
whether a per-sample responder/non-responder-like field is visible. It does not
download expression matrices and does not run the analysis pipeline.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import io
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

csv.field_size_limit(sys.maxsize)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    REPO_ROOT.parent
    / "specs/080-external-ici-treated-validation/discovery/geo_rnr_confirmation_20260703"
)

DEFAULT_ACCESSIONS = ["GSE289743", "GSE284400", "GSE160638"]

RESPONSE_FIELD_RE = re.compile(
    r"(response|responder|non[-_\s]?responder|recist|benefit|progress|"
    r"resistan|refractory|sensitive|outcome|bor|best.*response|clinical.*benefit|"
    r"pathologic|pcr|dcbr|irrecist)",
    re.I,
)
RESPONSE_VALUE_RE = re.compile(
    r"((?<![-A-Za-z0-9])CR(?![-A-Za-z0-9])|"
    r"(?<![-A-Za-z0-9])PR(?![-A-Za-z0-9])|"
    r"(?<![-A-Za-z0-9])SD(?![-A-Za-z0-9])|"
    r"(?<![-A-Za-z0-9])PD(?![-A-Za-z0-9])|"
    r"complete response|partial response|stable disease|progressive disease|"
    r"responders?|non[-_\s]?responders?|clinical benefit|no clinical benefit|"
    r"durable clinical benefit|non[-_\s]?benefit|refractory)",
    re.I,
)
TIMING_FIELD_RE = re.compile(
    r"(^|_)(time|timing|visit|baseline|sample_collection_time|treatment_time)($|_)|"
    r"(^|_)(pre|post|on_treatment|pre_treatment|post_treatment)($|_)",
    re.I,
)
TIMING_VALUE_RE = re.compile(
    r"(baseline|pre[-_\s]?(treatment|therapy|immunotherapy)|before|"
    r"on[-_\s]?(treatment|therapy|immunotherapy)|"
    r"post[-_\s]?(treatment|therapy|immunotherapy)|after)",
    re.I,
)
DRUG_RE = re.compile(
    r"(anti[-_\s]?pd[-_\s]?1|anti[-_\s]?pdl1|pd[-_\s]?1|pd[-_\s]?l1|"
    r"anti[-_\s]?ctla[-_\s]?4|ctla[-_\s]?4|nivolumab|pembrolizumab|"
    r"atezolizumab|durvalumab|avelumab|ipilimumab|cemiplimab|tremelimumab|"
    r"checkpoint|immunotherapy|ici|icb)",
    re.I,
)
NON_CLINICAL_RESPONSE_FIELD_RE = re.compile(
    r"^(channel_count|contact_.*|data_processing|data_row_count|description|"
    r"extract_protocol.*|growth_protocol.*|instrument_model|last_update_date|"
    r"library_.*|molecule.*|organism.*|platform_id|relation|source_name.*|"
    r"status|submission_date|supplementary_file.*|taxid.*|title|tissue|"
    r"treatment|type)$",
    re.I,
)


def geo_prefix(gse: str) -> str:
    gse = gse.upper()
    return f"{gse[:-3]}nnn"


def matrix_url(gse: str) -> str:
    gse = gse.upper()
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_prefix(gse)}/{gse}/matrix/{gse}_series_matrix.txt.gz"


def soft_url(gse: str) -> str:
    gse = gse.upper()
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_prefix(gse)}/{gse}/soft/{gse}_family.soft.gz"


def fetch_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=180) as response:
        return response.read()


def iter_gzip_lines(payload: bytes) -> Iterable[str]:
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as gz:
        text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
        for line in text:
            yield line.rstrip("\n")


def parse_geo_matrix(payload: bytes) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    series_fields: dict[str, list[str]] = defaultdict(list)
    sample_fields: dict[str, list[list[str]]] = defaultdict(list)

    for line in iter_gzip_lines(payload):
        if line.startswith("!series_matrix_table_begin"):
            break
        if not line.startswith("!"):
            continue
        cells = next(csv.reader([line], delimiter="\t"))
        if not cells:
            continue
        key = cells[0].strip()
        values = [cell.strip().strip('"') for cell in cells[1:]]
        if key.startswith("!Series_"):
            series_fields[key.removeprefix("!Series_")].append(" ".join(v for v in values if v))
        elif key.startswith("!Sample_"):
            sample_fields[key.removeprefix("!Sample_")].append(values)

    accessions = []
    for values in sample_fields.get("geo_accession", []):
        accessions.extend(values)
    n = len(accessions)

    samples: list[dict[str, str]] = []
    for idx, sample_id in enumerate(accessions):
        rec: dict[str, str] = {"sample_id": sample_id}
        for key, rows in sample_fields.items():
            if key == "geo_accession":
                continue
            vals = []
            for row in rows:
                if idx < len(row) and row[idx]:
                    vals.append(row[idx])
            if key == "characteristics_ch1":
                for char_idx, val in enumerate(vals, start=1):
                    char_key, char_value = split_characteristic(val, char_idx)
                    rec[dedupe_key(rec, normalize_key(char_key))] = char_value
            elif vals:
                rec[dedupe_key(rec, normalize_key(key))] = " | ".join(vals)
        samples.append(rec)

    # Defensive fallback: a matrix without Sample_geo_accession is not useful for
    # this curation task, but return any parsed fields for easier debugging.
    if not samples and n == 0:
        return dict(series_fields), []
    return dict(series_fields), samples


def split_characteristic(value: str, char_idx: int) -> tuple[str, str]:
    raw = (value or "").strip()
    if ":" in raw:
        key, val = raw.split(":", 1)
        key = key.strip() or f"characteristic_{char_idx}"
        val = val.strip()
        return key, val
    return f"characteristic_{char_idx}", raw


def normalize_key(key: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", (key or "").strip().lower())
    key = re.sub(r"_+", "_", key).strip("_")
    return key or "field"


def dedupe_key(rec: dict[str, str], key: str) -> str:
    if key not in rec:
        return key
    i = 2
    while f"{key}_{i}" in rec:
        i += 1
    return f"{key}_{i}"


def field_counts(samples: list[dict[str, str]]) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in samples:
        for key, value in row.items():
            if key == "sample_id":
                continue
            val = (value or "").strip()
            if val:
                counts[key][val] += 1
    return counts


def score_field(key: str, counts: Counter[str]) -> tuple[int, str]:
    if NON_CLINICAL_RESPONSE_FIELD_RE.match(key):
        return 0, ""
    key_hit = bool(RESPONSE_FIELD_RE.search(key))
    value_hits = sum(n for val, n in counts.items() if RESPONSE_VALUE_RE.search(val))
    if not key_hit and not value_hits:
        return 0, ""
    distinct = len(counts)
    score = 0
    reasons = []
    if key_hit:
        score += 5
        reasons.append("response_key")
    if value_hits:
        score += min(5, value_hits)
        reasons.append(f"response_values={value_hits}")
    if 2 <= distinct <= 12:
        score += 2
        reasons.append(f"distinct={distinct}")
    elif distinct > 20:
        score -= 2
        reasons.append(f"high_cardinality={distinct}")
    return score, ";".join(reasons)


def classify_study(series: dict[str, list[str]], samples: list[dict[str, str]]) -> dict[str, str]:
    counts = field_counts(samples)
    response_candidates = []
    timing_candidates = []
    drug_hits = []
    for key, counter in counts.items():
        score, reasons = score_field(key, counter)
        if score > 0:
            response_candidates.append((score, key, reasons, counter))
        if TIMING_FIELD_RE.search(key) or any(TIMING_VALUE_RE.search(v) for v in counter):
            timing_candidates.append(key)
        if DRUG_RE.search(key) or any(DRUG_RE.search(v) for v in counter):
            drug_hits.append(key)

    response_candidates.sort(key=lambda x: (-x[0], x[1]))
    title = " ".join(series.get("title", [])).strip()
    summary = " ".join(series.get("summary", [])).strip()
    series_blob = f"{title} {summary}"
    drug_series = bool(DRUG_RE.search(series_blob))

    top_field = response_candidates[0][1] if response_candidates else ""
    top_values = ""
    top_score = ""
    top_reasons = ""
    if response_candidates:
        score, _key, reasons, counter = response_candidates[0]
        top_score = str(score)
        top_reasons = reasons
        top_values = "; ".join(f"{value}={n}" for value, n in counter.most_common(20))

    status = "no_visible_rnr_field"
    if response_candidates and (drug_hits or drug_series):
        status = "candidate_rnr_field_present"
    elif response_candidates:
        status = "candidate_response_field_but_drug_unclear"
    elif drug_hits or drug_series:
        status = "drug_visible_but_no_rnr_field"

    curation_decision, next_action, claim_boundary = interpret_status(status)
    return {
        "n_samples": str(len(samples)),
        "series_title": title,
        "status": status,
        "curation_decision": curation_decision,
        "next_action": next_action,
        "claim_boundary": claim_boundary,
        "top_response_field": top_field,
        "top_response_field_score": top_score,
        "top_response_field_reasons": top_reasons,
        "top_response_field_values": top_values,
        "n_response_candidate_fields": str(len(response_candidates)),
        "timing_candidate_fields": ";".join(sorted(set(timing_candidates))),
        "drug_candidate_fields": ";".join(sorted(set(drug_hits))),
        "drug_hint_in_series": "true" if drug_series else "false",
    }


def interpret_status(status: str) -> tuple[str, str, str]:
    if status == "candidate_rnr_field_present":
        return (
            "metadata_pass",
            "Check expression matrix, sample timing compatibility, and derivation-cohort independence before frozen-signature scoring.",
            "Candidate only until frozen signature is scored; not validation evidence yet.",
        )
    if status == "candidate_response_field_but_drug_unclear":
        return (
            "paper_curation_required",
            "Confirm ICI treatment at paper or supplement level before considering validation.",
            "Do not call this an ICI validation cohort yet.",
        )
    if status == "drug_visible_but_no_rnr_field":
        return (
            "paper_curation_required",
            "Find paper/supplement sample-to-response mapping or exclude from response-labelled external validation.",
            "ICI context visible, but no per-sample R/NR label was visible in GEO metadata.",
        )
    return (
        "not_ready",
        "Exclude from external validation unless independent response and treatment labels are curated elsewhere.",
        "No visible per-sample response evidence in GEO metadata.",
    )


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        ordered = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    ordered.append(key)
                    seen.add(key)
        fieldnames = ordered
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(accessions: list[str], out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, str]] = []
    field_rows: list[dict[str, str]] = []
    all_sample_rows: list[dict[str, str]] = []

    for accession in accessions:
        gse = accession.upper()
        url = matrix_url(gse)
        payload = fetch_url(url)
        raw_path = out_dir / "raw" / f"{gse}_series_matrix.txt.gz"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)

        series, samples = parse_geo_matrix(payload)
        result = classify_study(series, samples)
        result.update(
            {
                "accession": gse,
                "geo_matrix_url": url,
                "raw_matrix_file": str(raw_path),
                "pulled_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            }
        )
        summary_rows.append(result)

        counts = field_counts(samples)
        for key, counter in sorted(counts.items()):
            score, reasons = score_field(key, counter)
            response_like = "true" if score > 0 else "false"
            timing_like = "true" if TIMING_FIELD_RE.search(key) or any(TIMING_VALUE_RE.search(v) for v in counter) else "false"
            drug_like = "true" if DRUG_RE.search(key) or any(DRUG_RE.search(v) for v in counter) else "false"
            field_rows.append(
                {
                    "accession": gse,
                    "field": key,
                    "n_nonempty": str(sum(counter.values())),
                    "n_unique": str(len(counter)),
                    "response_like": response_like,
                    "timing_like": timing_like,
                    "drug_like": drug_like,
                    "response_score": str(score),
                    "response_reasons": reasons,
                    "values": "; ".join(f"{value}={n}" for value, n in counter.most_common(40)),
                }
            )

        for sample in samples:
            row = {"accession": gse, **sample}
            all_sample_rows.append(row)
        write_tsv(out_dir / f"{gse}_sample_metadata.tsv", [{"accession": gse, **s} for s in samples])

    write_tsv(
        out_dir / "geo_rnr_confirmation_summary.tsv",
        summary_rows,
        fieldnames=[
            "accession",
            "n_samples",
            "status",
            "curation_decision",
            "next_action",
            "claim_boundary",
            "top_response_field",
            "top_response_field_score",
            "top_response_field_reasons",
            "top_response_field_values",
            "n_response_candidate_fields",
            "timing_candidate_fields",
            "drug_candidate_fields",
            "drug_hint_in_series",
            "series_title",
            "geo_matrix_url",
            "raw_matrix_file",
            "pulled_at_utc",
        ],
    )
    write_tsv(out_dir / "geo_rnr_candidate_fields.tsv", field_rows)
    write_tsv(out_dir / "geo_sample_metadata_wide.tsv", all_sample_rows)
    write_report(out_dir, summary_rows)
    return 0


def write_report(out_dir: Path, summary_rows: list[dict[str, str]]) -> None:
    lines = [
        "# GEO R/NR Metadata Confirmation",
        "",
        f"Date: {dt.date.today().isoformat()}",
        "",
        "Metadata-only probe of candidate Track B external-validation cohorts. This confirms visible sample-level fields only; it does not score signatures and does not make validation claims.",
        "",
        "## Verdict",
        "",
        "| accession | n | decision | status | top response-like field | values | next action |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            "| {accession} | {n_samples} | {curation_decision} | {status} | {top_response_field} | {top_response_field_values} | {next_action} |".format(
                **{k: (v or "").replace("|", "/") for k, v in row.items()}
            )
        )
    lines.extend(["", "## Interpretation", ""])
    for row in summary_rows:
        lines.append(f"- `{row['accession']}`: {row['claim_boundary']}")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `geo_rnr_confirmation_summary.tsv`",
            "- `geo_rnr_candidate_fields.tsv`",
            "- `geo_sample_metadata_wide.tsv`",
            "- `GSE*_sample_metadata.tsv`",
            "- `raw/GSE*_series_matrix.txt.gz`",
            "",
            "## Reproducibility",
            "",
            "```bash",
            "python3.13 scripts/confirm_external_ici_geo_metadata.py --out-dir ../specs/080-external-ici-treated-validation/discovery/geo_rnr_confirmation_20260703",
            "```",
        ]
    )
    (out_dir / "geo_rnr_confirmation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accession", action="append", default=[], help="GSE accession; may be repeated.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    accessions = args.accession or DEFAULT_ACCESSIONS
    return run(accessions, args.out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
