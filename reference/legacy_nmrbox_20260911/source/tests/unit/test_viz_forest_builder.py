from __future__ import annotations

from pathlib import Path

from src.pipeline.modules._viz.forest import write_meta_forest_plots


def test_write_meta_forest_plots_writes_png_for_significant_gene(tmp_path: Path) -> None:
    out_rows = [
        {
            "gene_id": "GENE_A",
            "meta_fdr": "0.01",
            "meta_effect_random": "1.2",
            "meta_se_random": "0.3",
            "_entries": [
                (1.0, 0.2, 0.01, "cohort_1"),
                (1.4, 0.3, 0.02, "cohort_2"),
            ],
        },
        {
            "gene_id": "GENE_B",
            "meta_fdr": "0.20",
            "meta_effect_random": "0.1",
            "meta_se_random": "0.2",
            "_entries": [(0.1, 0.2, 0.5, "cohort_3")],
        },
    ]

    forest_dir = tmp_path / "forest_plots"
    n_written = write_meta_forest_plots(out_rows=out_rows, out_dir=forest_dir)

    assert n_written == 1
    assert (forest_dir / "GENE_A.png").exists()
    assert not (forest_dir / "GENE_B.png").exists()
