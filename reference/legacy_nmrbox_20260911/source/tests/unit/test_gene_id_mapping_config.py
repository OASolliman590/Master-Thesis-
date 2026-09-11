from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_human_gene_id_mapping_config_is_populated() -> None:
    mapping_path = Path("configs/gene_id_mapping_human.tsv")
    mapping = pd.read_csv(mapping_path, sep="\t", dtype=str).fillna("")

    assert {"ensembl_gene_id", "hgnc_symbol", "alias_symbols"}.issubset(mapping.columns)
    assert len(mapping) > 50_000
    assert mapping["ensembl_gene_id"].str.match(r"^ENSG\d+$").mean() > 0.95
    assert mapping["hgnc_symbol"].str.len().gt(0).mean() > 0.95
