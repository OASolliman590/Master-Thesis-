from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_report_build, cmd_tcga_naive_manifest, cmd_tcga_naive_map, cmd_tcga_project
from src.pipeline.common.io import read_tsv, write_tsv


def test_tcga_two_project_smoke_run(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    run_root = tmp_path / "tcga_naive_projection"
    mapping_dir = run_root / "mapping"
    manifests_dir = run_root / "manifests"
    projection_dir = run_root / "projection"
    report_dir = run_root / "reports"
    signature_file = run_root / "signature" / "pre_response_signature_v1.tsv"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    sample_manifest = tmp_path / "sample_manifest.tsv"
    project_registry = tmp_path / "project_registry.tsv"
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "cancer_type"],
        rows=[
            {"cohort_id": "c_mel", "cancer_type": "Melanoma"},
            {"cohort_id": "c_nsclc", "cancer_type": "Non small-cell lung cancer"},
        ],
    )
    write_tsv(
        project_registry,
        fieldnames=[
            "tcga_project",
            "tcga_cancer_type",
            "matched_geo_group",
            "priority",
            "analysis_include_flag",
            "required_outcomes",
            "notes",
        ],
        rows=[
            {
                "tcga_project": "TCGA-SKCM",
                "tcga_cancer_type": "Skin Cutaneous Melanoma",
                "matched_geo_group": "Melanoma",
                "priority": "1",
                "analysis_include_flag": "1",
                "required_outcomes": "OS",
                "notes": "",
            },
            {
                "tcga_project": "TCGA-LUAD",
                "tcga_cancer_type": "Lung adenocarcinoma",
                "matched_geo_group": "NSCLC",
                "priority": "1",
                "analysis_include_flag": "1",
                "required_outcomes": "OS",
                "notes": "",
            },
        ],
    )

    args_map = Namespace(
        sample_manifest=str(sample_manifest),
        project_registry=str(project_registry),
        out=str(mapping_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_tcga_naive_map(args_map) == 0

    expr_skcm = tmp_path / "TCGA-SKCM.htseq_counts.tsv"
    expr_luad = tmp_path / "TCGA-LUAD.htseq_counts.tsv"
    surv_skcm = tmp_path / "TCGA-SKCM.survival.tsv"
    surv_luad = tmp_path / "TCGA-LUAD.survival.tsv"
    gene_map = tmp_path / "gene_id_mapping.tsv"
    expr_skcm.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-SKCM-0001-01A\tTCGA-SKCM-0002-01A",
                "ENSG000001\t11\t7",
                "ENSG000002\t2\t6",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_tsv(
        gene_map,
        fieldnames=["ensembl_gene_id", "hgnc_symbol", "alias_symbols"],
        rows=[
            {"ensembl_gene_id": "ENSG000001", "hgnc_symbol": "GENE_UP", "alias_symbols": ""},
            {"ensembl_gene_id": "ENSG000002", "hgnc_symbol": "GENE_DOWN", "alias_symbols": ""},
        ],
    )
    expr_luad.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-LUAD-0001-01A\tTCGA-LUAD-0002-01A",
                "ENSG000001\t8\t9",
                "ENSG000002\t4\t3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surv_skcm.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS\ttreatment_status",
                "TCGA-SKCM-0001-01A\t100\t1\tno prior treatment",
                "TCGA-SKCM-0002-01A\t150\t0\tno prior treatment",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surv_luad.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS\ttreatment_status",
                "TCGA-LUAD-0001-01A\t130\t1\tno prior treatment",
                "TCGA-LUAD-0002-01A\t170\t0\tno prior treatment",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tcga_map = mapping_dir / "tcga_sample_map.tsv"
    write_tsv(
        tcga_map,
        fieldnames=[
            "project",
            "expression_url",
            "survival_url",
            "local_expression_path",
            "local_survival_path",
            "status",
        ],
        rows=[
            {
                "project": "TCGA-SKCM",
                "expression_url": "",
                "survival_url": "",
                "local_expression_path": str(expr_skcm),
                "local_survival_path": str(surv_skcm),
                "status": "ready",
            },
            {
                "project": "TCGA-LUAD",
                "expression_url": "",
                "survival_url": "",
                "local_expression_path": str(expr_luad),
                "local_survival_path": str(surv_luad),
                "status": "ready",
            },
        ],
    )

    args_manifest = Namespace(tcga_map=str(tcga_map), out=str(manifests_dir), run_manifest=str(run_manifest))
    assert cmd_tcga_naive_manifest(args_manifest) == 0

    write_tsv(
        signature_file,
        fieldnames=["gene_id", "signature_direction"],
        rows=[
            {"gene_id": "GENE_UP", "signature_direction": "up"},
            {"gene_id": "GENE_DOWN", "signature_direction": "down"},
        ],
    )

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/Rscript")

    def _fake_subprocess_run(cmd: list[str], check: bool = True):  # noqa: ANN001
        del check
        stats_path = Path(cmd[cmd.index("--out-stats") + 1])
        plot_path = Path(cmd[cmd.index("--out-plot") + 1])
        write_tsv(
            stats_path,
            fieldnames=["project", "n_samples", "hazard_ratio", "lower_95_ci", "upper_95_ci", "p_value"],
            rows=[{"project": "stub", "n_samples": "2", "hazard_ratio": "0.95", "lower_95_ci": "0.7", "upper_95_ci": "1.2", "p_value": "0.4"}],
        )
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plot_path.write_text("stub", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("subprocess.run", _fake_subprocess_run)

    args_project = Namespace(
        signature=str(signature_file),
        tcga_map=str(tcga_map),
        naive_manifest=str(manifests_dir / "tcga_naive_patient_manifest.tsv"),
        tier_signatures_dir="",
        gene_id_mapping=str(gene_map),
        out=str(projection_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_tcga_project(args_project) == 0

    status_rows = read_tsv(projection_dir / "tcga_projection_status.tsv")
    completed_projects = {r["project"] for r in status_rows if r["status"] == "completed"}
    assert completed_projects == {"TCGA-SKCM", "TCGA-LUAD"}

    args_report = Namespace(results_root=str(run_root), out=str(report_dir), run_manifest=str(run_manifest))
    assert cmd_report_build(args_report) == 0
    assert (report_dir / "pipeline_summary.md").exists()
