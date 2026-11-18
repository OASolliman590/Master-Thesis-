"""Scan files bound for the public repository for private paths, sample/run IDs and credentials.

Study accessions (GSE, PRJNA, EGAS) are public and allowed. Per-sample and per-run
accessions (GSM, SRR/ERR/DRR, SRX/ERX, SAMN/SAMEA) identify specimens and are refused.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "private path": re.compile(r"/(?:Volumes|Users|home|private/tmp|private/var)/[A-Za-z0-9._-]+"),
    "sample or run accession": re.compile(r"\b(?:GSM\d{4,}|[SED]RR\d{5,}|[SED]RX\d{5,}|SAM[NE][A-Z]?\d{5,})\b"),
    "credential": re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bsk-[A-Za-z0-9_-]{20,}\b"
    ),
}

# Files that must never be committed, whatever their content.
FORBIDDEN_NAMES = ("ingestion_packet.json",)


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    kind: str


def scan_text(path: str, text: str) -> list[Hit]:
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                hits.append(Hit(path, number, kind))
    return hits


def scan_paths(root: Path, relative_paths: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for relative in relative_paths:
        if Path(relative).name in FORBIDDEN_NAMES:
            hits.append(Hit(relative, 0, "forbidden file"))
            continue
        path = root / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue  # binary; reviewed by name only
        hits.extend(scan_text(relative, data.decode("utf-8", errors="replace")))
    return hits


def staged_paths(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=root, check=True, capture_output=True,
    ).stdout.decode()
    return [p for p in out.split("\0") if p]
