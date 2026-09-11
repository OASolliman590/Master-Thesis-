from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable


ACCESSION_SPLIT_RE = re.compile(r"[;,|\s]+")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return [dict(row) for row in reader]


def write_tsv(
    path: Path,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, object]],
) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=list(fieldnames),
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _to_cell(v) for k, v in row.items()})


def _to_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def split_accessions(raw: str) -> list[str]:
    if not raw:
        return []
    tokens = [tok.strip() for tok in ACCESSION_SPLIT_RE.split(raw) if tok.strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        upper = token.upper()
        if upper not in seen:
            seen.add(upper)
            ordered.append(upper)
    return ordered


def infer_source_db(tokens: list[str]) -> str:
    has_geo = any(tok.startswith(("GSE", "GSM", "GPL")) for tok in tokens)
    has_sra = any(tok.startswith(("SRP", "SRX", "SRR", "PRJ")) for tok in tokens)
    if has_geo and has_sra:
        return "GEO/SRA"
    if has_geo:
        return "GEO"
    if has_sra:
        return "SRA"
    return "unknown"


def build_source_uri(tokens: list[str]) -> str:
    if not tokens:
        return ""
    first = tokens[0]
    if first.startswith(("GSE", "GSM", "GPL")):
        return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={first}"
    if first.startswith("PRJ"):
        return f"https://www.ncbi.nlm.nih.gov/bioproject/{first}"
    if first.startswith(("SRP", "SRX", "SRR")):
        return f"https://www.ncbi.nlm.nih.gov/sra/?term={first}"
    return ""


def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    norm = str(value).strip().lower()
    if norm in {"1", "true", "yes", "y"}:
        return True
    if norm in {"0", "false", "no", "n"}:
        return False
    return default

