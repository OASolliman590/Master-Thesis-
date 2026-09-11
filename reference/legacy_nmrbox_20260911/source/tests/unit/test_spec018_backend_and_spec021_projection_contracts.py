from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

from src.pipeline.cli import _read_layer4_gene_sets_from_registry, cmd_immune_score, cmd_tcga_project
from src.pipeline.common.io import read_tsv, write_tsv


def _write_symbol_gene_map(path: Path, symbols: list[str]) -> None:
    write_tsv(
        path,
        fieldnames=["ensembl_gene_id", "hgnc_symbol", "alias_symbols"],
        rows=[
            {"ensembl_gene_id": "", "hgnc_symbol": symbol, "alias_symbols": ""}
            for symbol in symbols
        ],
    )


def test_layer4_registry_includes_required_epigenetic_gene_sets() -> None:
    registry = Path("configs/immune_gene_sets_registry.tsv")
    sets = {
        row.get("gene_set", "")
        for row in _read_layer4_gene_sets_from_registry(registry)
        if row.get("gene_set", "")
    }
    required = {
        "EPIGENETIC_IMMUNE_PRIMING",
        "PRC2_IMMUNE_TARGETS",
        "SWI_SNF_ICB",
        "DNMT_IMMUNE_LOCI",
        "HISTONE_WRITERS_ICB",
        "RETROELEMENT_SENSING",
        "T_CELL_EXHAUSTION_EPIGENETIC",
        "T_CELL_MEMORY_EPIGENETIC",
    }
    assert required.issubset(sets)


def test_ssgsea_legacy_branch_uses_directional_ranking_not_abs_ranking() -> None:
    script = Path("scripts/ssgsea_gsva.R").read_text(encoding="utf-8")
    assert "abs.ranking = FALSE" in script


def test_immune_score_requires_real_backend_unless_legacy_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "include_flag", "input_class", "timing_category", "response_label"],
        rows=[],
    )
    registry = tmp_path / "registry.tsv"
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("SET_A\tset A\tCD274\n", encoding="utf-8")
    write_tsv(
        registry,
        fieldnames=["gene_set_id", "gene_set_layer", "gene_set_name", "gmt_path", "source", "enabled", "notes"],
        rows=[
            {
                "gene_set_id": "SET_A",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "gene_set_name": "Set A",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda _: None)
    args = Namespace(
        sample_manifest=str(sample_manifest),
        ingest_dir="",
        expression_manifest=str(tmp_path / "expr_manifest.tsv"),
        downloads_root=str(tmp_path / "downloads"),
        gene_set_registry=str(registry),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.0,
        max_unmapped_ensembl_fraction=1.0,
        max_duplicate_collapse_fraction=1.0,
        allow_weak_gene_mapping=True,
        skip_backend_check=True,  # must NOT bypass real-backend requirement
        legacy_rank_mean=False,
        out=str(tmp_path / "immune_out"),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )

    with pytest.raises(RuntimeError, match="Rscript not found"):
        cmd_immune_score(args)


def test_immune_score_emits_mediator_and_reproducibility_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_a"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tR1\tN1",
                "CD274\t10\t3",
                "GENE_X\t8\t2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "include_flag",
            "input_class",
            "timing_category",
            "response_label",
            "assay_type",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "R1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "assay_type": "log_normalized",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "N1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "assay_type": "log_normalized",
            },
        ],
    )
    expression_manifest = tmp_path / "expr_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv", "downloads_folder": "cohort_a"}],
    )
    registry = tmp_path / "registry.tsv"
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("SET_A\tset A\tCD274\n", encoding="utf-8")
    write_tsv(
        registry,
        fieldnames=["gene_set_id", "gene_set_layer", "gene_set_name", "gmt_path", "source", "enabled", "notes"],
        rows=[
            {
                "gene_set_id": "SET_A",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "gene_set_name": "Set A",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        cmd_s = " ".join(cmd)
        if "ssgsea_gsva.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text("gene_set\tR1\tN1\nSET_A\t0.8\t0.2\n", encoding="utf-8")
        elif "estimate_scores.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text(
                "\n".join(
                    [
                        "NAME\tDescription\tR1\tN1",
                        "ImmuneScore\tscore\t1200\t200",
                        "StromalScore\tscore\t800\t100",
                        "ESTIMATEScore\tscore\t2000\t300",
                        "TumorPurity\tscore\t0.35\t0.75",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        elif "epic_scores.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text(
                "\n".join(
                    [
                        "cell_type\tR1\tN1",
                        "CD8_T\t0.2\t0.05",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("subprocess.run", _fake_run)
    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)

    out_dir = tmp_path / "immune_out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        ingest_dir="",
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        gene_set_registry=str(registry),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.0,
        max_unmapped_ensembl_fraction=1.0,
        max_duplicate_collapse_fraction=1.0,
        allow_weak_gene_mapping=True,
        legacy_rank_mean=False,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_immune_score(args) == 0

    mediator_rows = read_tsv(out_dir / "composition_mediator_inputs.tsv")
    assert mediator_rows
    assert mediator_rows[0]["mediator_role"] == "composition_mediator_candidate"
    assert mediator_rows[0]["intended_use"] == "spec015_d5_secondary_mediation"

    long_rows = read_tsv(out_dir / "ssgsea_scores_long.tsv")
    assert long_rows
    assert {r["method"] for r in long_rows} == {"gsva_ssgsea_r"}

    repro_dir = out_dir / "reproducibility"
    assert (repro_dir / "commands.sh").exists()
    assert (repro_dir / "environment.yml").exists()
    assert (repro_dir / "checksums.sha256").exists()


def test_immune_score_matches_reference_gsva_output_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / "cohort_a"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2",
                "CD274\t5\t1",
                "GENE_Y\t2\t3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id", "include_flag", "input_class", "timing_category", "response_label", "assay_type"],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "S1",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "assay_type": "log_normalized",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "S2",
                "include_flag": "true",
                "input_class": "processed_matrix",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "assay_type": "log_normalized",
            },
        ],
    )
    expression_manifest = tmp_path / "expr_manifest.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv", "downloads_folder": "cohort_a"}],
    )
    registry = tmp_path / "registry.tsv"
    gmt = tmp_path / "sets.gmt"
    gmt.write_text("SET_A\tset A\tCD274\n", encoding="utf-8")
    write_tsv(
        registry,
        fieldnames=["gene_set_id", "gene_set_layer", "gene_set_name", "gmt_path", "source", "enabled", "notes"],
        rows=[
            {
                "gene_set_id": "SET_A",
                "gene_set_layer": "L1_ICB_PREDICTOR",
                "gene_set_name": "Set A",
                "gmt_path": str(gmt),
                "source": "fixture",
                "enabled": "true",
                "notes": "",
            }
        ],
    )
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    reference_scores = {"SET_A": {"S1": 0.75, "S2": 0.25}}

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        cmd_s = " ".join(cmd)
        if "ssgsea_gsva.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text(
                "\n".join(
                    [
                        "gene_set\tS1\tS2",
                        f"SET_A\t{reference_scores['SET_A']['S1']}\t{reference_scores['SET_A']['S2']}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        elif "estimate_scores.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text(
                "\n".join(
                    [
                        "NAME\tDescription\tS1\tS2",
                        "ImmuneScore\tscore\t100\t50",
                        "StromalScore\tscore\t80\t40",
                        "ESTIMATEScore\tscore\t180\t90",
                        "TumorPurity\tscore\t0.4\t0.6",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        elif "epic_scores.R" in cmd_s:
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text("cell_type\tS1\tS2\nCD8_T\t0.1\t0.05\n", encoding="utf-8")

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("subprocess.run", _fake_run)
    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)

    out_dir = tmp_path / "immune_out"
    args = Namespace(
        sample_manifest=str(sample_manifest),
        ingest_dir="",
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        gene_set_registry=str(registry),
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.0,
        max_unmapped_ensembl_fraction=1.0,
        max_duplicate_collapse_fraction=1.0,
        allow_weak_gene_mapping=True,
        legacy_rank_mean=False,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_immune_score(args) == 0

    wide_rows = read_tsv(out_dir / "ssgsea_scores.tsv")
    assert wide_rows and len(wide_rows) == 2
    by_sample = {r["sample_id"]: r for r in wide_rows}
    assert float(by_sample["S1"]["SET_A"]) == pytest.approx(reference_scores["SET_A"]["S1"], abs=1e-9)
    assert float(by_sample["S2"]["SET_A"]) == pytest.approx(reference_scores["SET_A"]["S2"], abs=1e-9)

    long_rows = read_tsv(out_dir / "ssgsea_scores_long.tsv")
    assert {row["method"] for row in long_rows} == {"gsva_ssgsea_r"}


def test_tcga_project_outputs_zscore_and_continuous_cox_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = tmp_path / "signature.tsv"
    write_tsv(
        signature,
        fieldnames=["gene_id", "signature_direction"],
        rows=[
            {"gene_id": "GENE_UP", "signature_direction": "up"},
            {"gene_id": "GENE_DOWN", "signature_direction": "down"},
        ],
    )

    expr = tmp_path / "tcga_expr.tsv"
    expr.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-A\tTCGA-B\tTCGA-C\tTCGA-D",
                "GENE_UP\t8\t7\t2\t1",
                "GENE_DOWN\t1\t2\t7\t8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surv = tmp_path / "tcga_surv.tsv"
    surv.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS",
                "TCGA-A\t100\t1",
                "TCGA-B\t200\t1",
                "TCGA-C\t300\t0",
                "TCGA-D\t400\t0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tcga_map = tmp_path / "tcga_map.tsv"
    write_tsv(
        tcga_map,
        fieldnames=["project", "local_expression_path", "local_survival_path"],
        rows=[
            {
                "project": "TCGA-SKCM",
                "local_expression_path": str(expr),
                "local_survival_path": str(surv),
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        out_stats = Path(cmd[cmd.index("--out-stats") + 1])
        out_plot = Path(cmd[cmd.index("--out-plot") + 1])
        write_tsv(
            out_stats,
            fieldnames=["project", "n_samples", "hazard_ratio", "lower_95_ci", "upper_95_ci", "p_value"],
            rows=[
                {
                    "project": "TCGA-SKCM",
                    "n_samples": "4",
                    "hazard_ratio": "1.2",
                    "lower_95_ci": "0.8",
                    "upper_95_ci": "1.9",
                    "p_value": "0.2",
                }
            ],
        )
        out_plot.write_bytes(b"png")

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)
    monkeypatch.setattr("subprocess.run", _fake_run)

    out_dir = tmp_path / "tcga_out"
    args = Namespace(
        signature=str(signature),
        tcga_map=str(tcga_map),
        naive_manifest="",
        tier_signatures_dir="",
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_tcga_project(args) == 0

    score_rows = read_tsv(out_dir / "TCGA-SKCM_score_input.tsv")
    assert score_rows
    assert "signature_score_z" in score_rows[0]
    z_vals = np.array([float(r["signature_score_z"]) for r in score_rows], dtype=float)
    assert abs(float(z_vals.mean())) < 1e-8
    assert float(z_vals.std(ddof=0)) > 0.0

    stats_rows = read_tsv(out_dir / "TCGA-SKCM_survival_stats.tsv")
    assert stats_rows[0]["model_covariates"] == "signature_score_z_continuous"
    assert stats_rows[0]["status"] == "ok"


def test_tcga_project_preserves_covariate_aware_model_contract_from_r_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = tmp_path / "signature.tsv"
    write_tsv(
        signature,
        fieldnames=["gene_id", "signature_direction"],
        rows=[{"gene_id": "GENE_UP", "signature_direction": "up"}],
    )
    expr = tmp_path / "tcga_expr.tsv"
    expr.write_text("gene_id\tTCGA-A\tTCGA-B\tTCGA-C\tTCGA-D\nGENE_UP\t8\t7\t2\t1\n", encoding="utf-8")
    surv = tmp_path / "tcga_surv.tsv"
    surv.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS\tage_at_diagnosis\tajcc_pathologic_stage",
                "TCGA-A\t100\t1\t65\tStage II",
                "TCGA-B\t200\t1\t61\tStage III",
                "TCGA-C\t300\t0\t58\tStage I",
                "TCGA-D\t400\t0\t67\tStage II",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tcga_map = tmp_path / "tcga_map.tsv"
    write_tsv(
        tcga_map,
        fieldnames=["project", "local_expression_path", "local_survival_path"],
        rows=[
            {
                "project": "TCGA-SKCM",
                "local_expression_path": str(expr),
                "local_survival_path": str(surv),
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        out_stats = Path(cmd[cmd.index("--out-stats") + 1])
        out_plot = Path(cmd[cmd.index("--out-plot") + 1])
        write_tsv(
            out_stats,
            fieldnames=[
                "project",
                "n_samples",
                "hazard_ratio",
                "lower_95_ci",
                "upper_95_ci",
                "p_value",
                "model_covariates",
            ],
            rows=[
                {
                    "project": "TCGA-SKCM",
                    "n_samples": "4",
                    "hazard_ratio": "1.2",
                    "lower_95_ci": "0.8",
                    "upper_95_ci": "1.9",
                    "p_value": "0.2",
                    "model_covariates": "signature_score_z_continuous+age+stage",
                }
            ],
        )
        out_plot.write_bytes(b"png")

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)
    monkeypatch.setattr("subprocess.run", _fake_run)

    out_dir = tmp_path / "tcga_out"
    args = Namespace(
        signature=str(signature),
        tcga_map=str(tcga_map),
        naive_manifest="",
        tier_signatures_dir="",
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_tcga_project(args) == 0

    stats_rows = read_tsv(out_dir / "TCGA-SKCM_survival_stats.tsv")
    assert stats_rows[0]["model_covariates"] == "signature_score_z_continuous+age+stage"
    assert stats_rows[0]["status"] == "ok"


def test_tcga_project_optionally_emits_layer4_vs_thorsson_association(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = tmp_path / "signature.tsv"
    write_tsv(
        signature,
        fieldnames=["gene_id", "signature_direction"],
        rows=[
            {"gene_id": "GENE_UP", "signature_direction": "up"},
            {"gene_id": "GENE_DOWN", "signature_direction": "down"},
        ],
    )
    expr = tmp_path / "tcga_expr.tsv"
    expr.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-A\tTCGA-B\tTCGA-C\tTCGA-D",
                "GENE_UP\t8\t7\t2\t1",
                "GENE_DOWN\t1\t2\t7\t8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surv = tmp_path / "tcga_surv.tsv"
    surv.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS",
                "TCGA-A\t100\t1",
                "TCGA-B\t200\t1",
                "TCGA-C\t300\t0",
                "TCGA-D\t400\t0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tcga_map = tmp_path / "tcga_map.tsv"
    write_tsv(
        tcga_map,
        fieldnames=["project", "local_expression_path", "local_survival_path"],
        rows=[
            {
                "project": "TCGA-SKCM",
                "local_expression_path": str(expr),
                "local_survival_path": str(surv),
            }
        ],
    )
    subtype_manifest = tmp_path / "thorsson_subtypes.tsv"
    write_tsv(
        subtype_manifest,
        fieldnames=["tcga_project", "sample_id", "immune_subtype"],
        rows=[
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-A", "immune_subtype": "C1"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-B", "immune_subtype": "C1"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-C", "immune_subtype": "C2"},
            {"tcga_project": "TCGA-SKCM", "sample_id": "TCGA-D", "immune_subtype": "C2"},
        ],
    )
    gmt = tmp_path / "layer4.gmt"
    gmt.write_text(
        "\n".join(
            [
                "EPIGENETIC_HIGH\tfixture\tGENE_UP",
                "EPIGENETIC_LOW\tfixture\tGENE_DOWN",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.tsv"
    gene_map = tmp_path / "gene_map.tsv"
    _write_symbol_gene_map(gene_map, ["GENE_UP", "GENE_DOWN"])
    write_tsv(
        registry,
        fieldnames=["gene_set_id", "gene_set_layer", "gene_set_name", "gmt_path", "source", "enabled", "notes"],
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

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        out_stats = Path(cmd[cmd.index("--out-stats") + 1])
        out_plot = Path(cmd[cmd.index("--out-plot") + 1])
        write_tsv(
            out_stats,
            fieldnames=["project", "n_samples", "hazard_ratio", "lower_95_ci", "upper_95_ci", "p_value"],
            rows=[
                {
                    "project": "TCGA-SKCM",
                    "n_samples": "4",
                    "hazard_ratio": "1.2",
                    "lower_95_ci": "0.8",
                    "upper_95_ci": "1.9",
                    "p_value": "0.2",
                }
            ],
        )
        out_plot.write_bytes(b"png")

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)
    monkeypatch.setattr("subprocess.run", _fake_run)

    out_dir = tmp_path / "tcga_out"
    args = Namespace(
        signature=str(signature),
        tcga_map=str(tcga_map),
        naive_manifest="",
        tier_signatures_dir="",
        thorsson_subtypes=str(subtype_manifest),
        gene_set_registry=str(registry),
        gene_id_mapping=str(gene_map),
        min_layer4_samples=4,
        min_layer4_subtype_samples=2,
        allow_weak_gene_mapping=True,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_tcga_project(args) == 0

    layer4_out = out_dir / "thorsson_layer4"
    validation_rows = read_tsv(layer4_out / "epigenetic_layer_tcga_validation.tsv")
    assert validation_rows
    assert all(row["tcga_project"] == "TCGA-SKCM" for row in validation_rows)
    assert {row["status"] for row in validation_rows} == {"ok"}
    assert (out_dir / "reproducibility" / "commands.sh").exists()
    assert (out_dir / "reproducibility" / "environment.yml").exists()
    assert (out_dir / "reproducibility" / "checksums.sha256").exists()


def test_tcga_project_marks_layer4_status_blocked_when_subtype_manifest_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = tmp_path / "signature.tsv"
    write_tsv(
        signature,
        fieldnames=["gene_id", "signature_direction"],
        rows=[{"gene_id": "GENE_UP", "signature_direction": "up"}],
    )
    expr = tmp_path / "tcga_expr.tsv"
    expr.write_text("gene_id\tTCGA-A\tTCGA-B\nGENE_UP\t8\t7\n", encoding="utf-8")
    surv = tmp_path / "tcga_surv.tsv"
    surv.write_text("sample\tOS.time\tOS\nTCGA-A\t100\t1\nTCGA-B\t200\t0\n", encoding="utf-8")
    tcga_map = tmp_path / "tcga_map.tsv"
    write_tsv(
        tcga_map,
        fieldnames=["project", "local_expression_path", "local_survival_path"],
        rows=[
            {
                "project": "TCGA-SKCM",
                "local_expression_path": str(expr),
                "local_survival_path": str(surv),
            }
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript" if name == "Rscript" else None)

    def _fake_run(cmd: list[str], *args, **kwargs):  # noqa: ARG001
        out_stats = Path(cmd[cmd.index("--out-stats") + 1])
        out_plot = Path(cmd[cmd.index("--out-plot") + 1])
        write_tsv(
            out_stats,
            fieldnames=["project", "n_samples", "hazard_ratio", "lower_95_ci", "upper_95_ci", "p_value"],
            rows=[
                {
                    "project": "TCGA-SKCM",
                    "n_samples": "2",
                    "hazard_ratio": "1.1",
                    "lower_95_ci": "0.6",
                    "upper_95_ci": "2.1",
                    "p_value": "0.5",
                }
            ],
        )
        out_plot.write_bytes(b"png")

        class _Done:
            returncode = 0

        return _Done()

    monkeypatch.setattr("src.pipeline.cli.append_run_manifest", lambda **_: None)
    monkeypatch.setattr("subprocess.run", _fake_run)

    missing_subtypes = tmp_path / "missing_subtypes.tsv"
    gene_map = tmp_path / "gene_map.tsv"
    _write_symbol_gene_map(gene_map, ["GENE_UP"])
    out_dir = tmp_path / "tcga_out"
    args = Namespace(
        signature=str(signature),
        tcga_map=str(tcga_map),
        naive_manifest="",
        tier_signatures_dir="",
        thorsson_subtypes=str(missing_subtypes),
        gene_set_registry=str(tmp_path / "missing_registry.tsv"),
        gene_id_mapping=str(gene_map),
        min_layer4_samples=3,
        min_layer4_subtype_samples=1,
        allow_weak_gene_mapping=True,
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_tcga_project(args) == 0

    status_rows = read_tsv(out_dir / "tcga_projection_status.tsv")
    layer4_rows = [r for r in status_rows if r["stage"] == "tcga_layer4_vs_thorsson"]
    assert layer4_rows
    assert layer4_rows[0]["status"] == "blocked"
    assert layer4_rows[0]["reason"] == "missing_thorsson_subtypes"
