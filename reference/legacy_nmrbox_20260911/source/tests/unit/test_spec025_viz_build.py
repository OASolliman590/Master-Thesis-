from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_viz_build
from src.pipeline.common.io import read_tsv, write_tsv


def _write_registry(path: Path) -> None:
    write_tsv(
        path,
        fieldnames=["path_pattern", "framing", "scientific_note"],
        rows=[
            {
                "path_pattern": "*tcga*",
                "framing": "prognostic_only",
                "scientific_note": "Prognostic context only (TCGA is non-ICB and not ICB-predictive).",
            },
            {
                "path_pattern": "*concordance*",
                "framing": "internal_robustness",
                "scientific_note": "Internal same-sample cross-method robustness (not external predictive evidence).",
            },
            {
                "path_pattern": "*",
                "framing": "descriptive",
                "scientific_note": "Descriptive analysis figure for cohort-level or pooled-effect interpretation.",
            },
        ],
    )


def test_viz_build_emits_manifest_and_caption_sidecars(tmp_path: Path, monkeypatch) -> None:
    def _fake_visualize_run(args: Namespace) -> int:
        out = Path(args.out)
        (out / "tcga").mkdir(parents=True, exist_ok=True)
        (out / "meta").mkdir(parents=True, exist_ok=True)
        (out / "qc").mkdir(parents=True, exist_ok=True)
        (out / "tcga" / "luad_survival_curve.png").write_bytes(b"png")
        (out / "meta" / "concordance_gold_bar.png").write_bytes(b"png")
        (out / "qc" / "cohort_pca.png").write_bytes(b"png")
        return 0

    monkeypatch.setattr("src.pipeline.cli.cmd_visualize_run", _fake_visualize_run)

    registry = tmp_path / "figure_registry.tsv"
    _write_registry(registry)
    run_manifest = tmp_path / "logs" / "run_manifest.yaml"

    args = Namespace(
        sample_manifest=str(tmp_path / "sample.tsv"),
        expression_manifest=str(tmp_path / "expression.tsv"),
        downloads_root=str(tmp_path / "downloads"),
        de_dir="",
        meta_dir="",
        immune_dir="",
        ssgsea_heatmap_top_sets=25,
        figure_registry=str(registry),
        out=str(tmp_path / "figures"),
        run_manifest=str(run_manifest),
    )
    assert cmd_viz_build(args) == 0

    rows = read_tsv(tmp_path / "figures" / "figure_manifest.tsv")
    assert len(rows) == 3
    assert all((row.get("scientific_note", "") or "").strip() for row in rows)
    assert all((row.get("caption_sidecar", "") or "").strip() for row in rows)

    tcga_row = next(row for row in rows if "tcga" in row["relative_path"])
    assert tcga_row["framing"] == "prognostic_only"
    assert "prognostic" in tcga_row["scientific_note"].lower()
    assert "validation" not in tcga_row["scientific_note"].lower()

    for row in rows:
        sidecar = Path(row["caption_sidecar"])
        assert sidecar.exists()
        assert row["scientific_note"] in sidecar.read_text(encoding="utf-8")
    assert (tmp_path / "figures" / "reproducibility" / "commands.sh").exists()
    assert (tmp_path / "figures" / "reproducibility" / "environment.yml").exists()
    assert (tmp_path / "figures" / "reproducibility" / "checksums.sha256").exists()


def test_viz_build_lints_tcga_and_concordance_validation_wording(tmp_path: Path, monkeypatch) -> None:
    def _fake_visualize_run(args: Namespace) -> int:
        out = Path(args.out)
        (out / "tcga").mkdir(parents=True, exist_ok=True)
        (out / "meta").mkdir(parents=True, exist_ok=True)
        (out / "tcga" / "skcm_survival_curve.png").write_bytes(b"png")
        (out / "meta" / "concordance_gold_bar.png").write_bytes(b"png")
        return 0

    monkeypatch.setattr("src.pipeline.cli.cmd_visualize_run", _fake_visualize_run)

    bad_registry = tmp_path / "bad_registry.tsv"
    write_tsv(
        bad_registry,
        fieldnames=["path_pattern", "framing", "scientific_note"],
        rows=[
            {
                "path_pattern": "*tcga*",
                "framing": "prognostic_only",
                "scientific_note": "TCGA external validation panel.",
            },
            {
                "path_pattern": "*concordance*",
                "framing": "internal_robustness",
                "scientific_note": "Concordance validation summary.",
            },
            {
                "path_pattern": "*",
                "framing": "descriptive",
                "scientific_note": "Descriptive figure.",
            },
        ],
    )

    args = Namespace(
        sample_manifest=str(tmp_path / "sample.tsv"),
        expression_manifest=str(tmp_path / "expression.tsv"),
        downloads_root=str(tmp_path / "downloads"),
        de_dir="",
        meta_dir="",
        immune_dir="",
        ssgsea_heatmap_top_sets=25,
        figure_registry=str(bad_registry),
        out=str(tmp_path / "figures"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    import pytest

    with pytest.raises(RuntimeError, match="scientific-note lint failed"):
        cmd_viz_build(args)
