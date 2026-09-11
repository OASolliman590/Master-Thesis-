from __future__ import annotations

from src.pipeline.common.io import split_accessions


def test_split_accessions_deduplicates_and_uppercases() -> None:
    raw = "gse12345; srp111111, gse12345  srx1"
    tokens = split_accessions(raw)
    assert tokens == ["GSE12345", "SRP111111", "SRX1"]

