from __future__ import annotations

from pathlib import Path


def test_contract_document_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = root / "specs/002-ici-discovery-meta-pipeline/contracts/io-contracts.md"
    assert contract.exists()

