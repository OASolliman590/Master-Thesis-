from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_tcga_epigenetic_layer
from src.pipeline.common.io import read_tsv, write_tsv


def test_tcga_epigenetic_layer_scores_and_kruskal_validation(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    expr = tmp_path / "TCGA-SKCM.expression.tsv"
    expr.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-SKCM-0001-01A\tTCGA-SKCM-0002-01A\tTCGA-SKCM-0003-01A\tTCGA-SKCM-0004-01A",
                "BRD4\t10\t9\t2\t1",
                "EZH2\t9\t8\t2\t1",
                "ARID1A\t8\t8\t3\t2",
                "CD274\t2\t2\t8\t9",
                "PDCD1LG2\t1\t2\t7\t8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    expression_manifest = tmp_path / "tcga_expression_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["tcga_project", "expression_path"],
        rows=[{"tcga_project": "TCGA-SKCM", "expression_path": str(expr)}],
    )
    subtype_manifest = tmp_path / "thorsson_subtypes.tsv"
    write_tsv(
        subtype_manifest,
        fieldnames=["tcga_project", "sample_id", "immune_subtype"],
        rows=[
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-SKCM-0001", "immune_subtype": "C1"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-SKCM-0002", "immune_subtype": "C1"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-SKCM-0003", "immune_subtype": "C2"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-SKCM-0004", "immune_subtype": "C2"},
        ],
    )
    gmt = tmp_path / "layer4.gmt"
    gmt.write_text(
        "\n".join(
            [
                "EPIGENETIC_HIGH\tfixture\tBRD4\tEZH2\tARID1A",
                "CHECKPOINT_HIGH\tfixture\tCD274\tPDCD1LG2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    registry = tmp_path / "immune_gene_sets_registry.tsv"
    write_tsv(
        registry,
        fieldnames=[
            "gene_set_id",
            "gene_set_layer",
            "gene_set_name",
            "gmt_path",
            "source",
            "enabled",
            "notes",
        ],
        rows=[
            {
                "gene_set_id": "EPIGENETIC_HIGH",
                "gene_set_layer": "L4_EPIGENETIC",
                "gene_set_name": "Epigenetic high",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            }
        ],
    )

    out_dir = tmp_path / "tcga_projection"
    args = Namespace(
        expression_manifest=str(expression_manifest),
        subtype_manifest=str(subtype_manifest),
        gene_set_registry=str(registry),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_samples=4,
        min_subtype_samples=2,
        allow_weak_gene_mapping=True,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_tcga_epigenetic_layer(args) == 0

    validation = read_tsv(out_dir / "epigenetic_layer_tcga_validation.tsv")
    assert {row["gene_set"] for row in validation} == {"EPIGENETIC_HIGH", "CHECKPOINT_HIGH"}
    assert all(row["tcga_project"] == "TCGA-SKCM" for row in validation)
    assert all(row["status"] == "ok" for row in validation)
    assert all(row["n_patients"] == "4" for row in validation)
    assert all(row["n_subtypes"] == "2" for row in validation)
    assert all(row["kw_statistic"] for row in validation)
    assert all(row["fdr"] for row in validation)

    scores = read_tsv(out_dir / "epigenetic_layer_tcga_scores.tsv")
    assert len(scores) == 8
    assert {"tcga_project", "sample_id", "patient_id", "immune_subtype", "gene_set", "score"}.issubset(
        scores[0]
    )
    assert (out_dir / "tcga_epigenetic_layer_input_contracts.md").exists()
