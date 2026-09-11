from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_report_build, cmd_tcga_naive_manifest, cmd_tcga_naive_map
from src.pipeline.common.io import read_tsv, write_tsv


def test_tcga_naive_map_contract_columns_and_vocab(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    project_registry = tmp_path / "project_registry.tsv"
    out_dir = tmp_path / "out_map"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "cancer_type"],
        rows=[
            {"cohort_id": "c_mel", "cancer_type": "Melanoma"},
            {"cohort_id": "c_nsclc", "cancer_type": "Non small-cell lung cancer"},
            {"cohort_id": "c_unmapped", "cancer_type": "Brain lower grade glioma"},
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
                "priority": "2",
                "analysis_include_flag": "1",
                "required_outcomes": "OS",
                "notes": "",
            },
        ],
    )

    args = Namespace(
        sample_manifest=str(sample_manifest),
        project_registry=str(project_registry),
        out=str(out_dir),
        run_manifest=str(run_manifest),
    )
    assert cmd_tcga_naive_map(args) == 0

    rows = read_tsv(out_dir / "geo_tcga_cancer_mapping.tsv")
    assert rows
    required_cols = {
        "cohort_id",
        "geo_cancer_type",
        "tcga_project",
        "tcga_cancer_type",
        "mapping_basis",
        "mapping_confidence",
        "include_flag",
        "notes",
    }
    assert required_cols.issubset(rows[0].keys())
    assert {r["mapping_confidence"] for r in rows}.issubset({"high", "moderate", "low"})
    assert {r["include_flag"] for r in rows}.issubset({"0", "1"})
    assert any(r["mapping_basis"] == "unmapped" and r["mapping_confidence"] == "low" for r in rows)


def test_tcga_naive_manifest_contract_columns_and_vocab(tmp_path: Path) -> None:
    tcga_map = tmp_path / "tcga_sample_map.tsv"
    expr_path = tmp_path / "TCGA-SKCM.htseq_counts.tsv"
    surv_path = tmp_path / "TCGA-SKCM.survival.tsv"
    out_dir = tmp_path / "out_manifest"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    expr_path.write_text(
        "\n".join(
            [
                "gene_id\tTCGA-SKCM-0001-01A\tTCGA-SKCM-0002-01A",
                "ENSG000001\t10\t5",
                "ENSG000002\t3\t8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surv_path.write_text(
        "\n".join(
            [
                "sample\tOS.time\tOS\ttreatment_status\tage\tgender\trace",
                "TCGA-SKCM-0001-01A\t100\t1\tno prior treatment\t61\tmale\twhite",
                "TCGA-SKCM-0002-01A\t150\t0\ttreated with chemotherapy\t57\tfemale\tasian",
                "TCGA-SKCM-0003-01A\t180\t0\t\t49\tfemale\tblack",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
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
                "local_expression_path": str(expr_path),
                "local_survival_path": str(surv_path),
                "status": "ready",
            }
        ],
    )

    args = Namespace(tcga_map=str(tcga_map), out=str(out_dir), run_manifest=str(run_manifest))
    assert cmd_tcga_naive_manifest(args) == 0

    manifest_rows = read_tsv(out_dir / "tcga_naive_patient_manifest.tsv")
    clinical_rows = read_tsv(out_dir / "tcga_clinical_flat.tsv")
    assert manifest_rows
    assert clinical_rows

    manifest_required = {
        "project",
        "case_id",
        "sample_id",
        "naive_flag",
        "naive_rule_version",
        "treatment_any_flag",
        "treatment_evidence",
        "rna_available_flag",
        "survival_available_flag",
        "include_primary_projection",
        "exclude_reason",
    }
    clinical_required = {
        "project",
        "case_id",
        "sample_id",
        "age_at_index",
        "sex",
        "race",
        "ethnicity",
        "vital_status",
        "days_to_death",
        "days_to_last_follow_up",
        "ajcc_pathologic_stage",
        "tumor_grade",
        "smoking_status",
        "pack_years_smoked",
        "alcohol_history",
        "molecular_subtype",
    }
    assert manifest_required.issubset(manifest_rows[0].keys())
    assert clinical_required.issubset(clinical_rows[0].keys())
    assert {r["naive_flag"] for r in manifest_rows}.issubset({"1", "0", "NA"})
    assert {r["include_primary_projection"] for r in manifest_rows}.issubset({"0", "1"})
    assert any(r["include_primary_projection"] == "1" for r in manifest_rows)


def test_report_build_includes_tcga_naive_projection_section(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    out_dir = tmp_path / "report"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    (results_root / "tcga_naive_projection" / "manifests").mkdir(parents=True, exist_ok=True)
    (results_root / "tcga_naive_projection" / "projection").mkdir(parents=True, exist_ok=True)
    (results_root / "tcga_naive_projection" / "epidemiology").mkdir(parents=True, exist_ok=True)
    (results_root / "tcga_naive_projection" / "reports").mkdir(parents=True, exist_ok=True)
    (results_root / "tcga_naive_projection" / "concordance_tiers").mkdir(parents=True, exist_ok=True)

    write_tsv(
        results_root / "tcga_naive_projection" / "manifests" / "tcga_naive_manifest_status.tsv",
        fieldnames=["stage", "project", "status", "reason", "detail"],
        rows=[{"stage": "tcga_naive_manifest", "project": "TCGA-SKCM", "status": "completed", "reason": "", "detail": ""}],
    )
    write_tsv(
        results_root / "tcga_naive_projection" / "projection" / "tcga_projection_status.tsv",
        fieldnames=["stage", "project", "signature_tier", "status", "reason", "detail"],
        rows=[{"stage": "tcga_project", "project": "TCGA-SKCM", "signature_tier": "ALL", "status": "completed", "reason": "ok", "detail": ""}],
    )
    write_tsv(
        results_root / "tcga_naive_projection" / "reports" / "tcga_pan_cancer_survival_summary.tsv",
        fieldnames=[
            "project",
            "tcga_cancer_type",
            "endpoint",
            "signature_tier",
            "hazard_ratio",
            "lower_95_ci",
            "upper_95_ci",
            "p_value",
            "n_samples",
            "n_events",
            "status",
        ],
        rows=[
            {
                "project": "TCGA-SKCM",
                "tcga_cancer_type": "Skin Cutaneous Melanoma",
                "endpoint": "OS",
                "signature_tier": "ALL",
                "hazard_ratio": "0.80",
                "lower_95_ci": "0.60",
                "upper_95_ci": "0.99",
                "p_value": "0.04",
                "n_samples": "100",
                "n_events": "50",
                "status": "ok",
            }
        ],
    )

    args = Namespace(results_root=str(results_root), out=str(out_dir), run_manifest=str(run_manifest))
    assert cmd_report_build(args) == 0

    summary_text = (out_dir / "pipeline_summary.md").read_text(encoding="utf-8")
    assert "## TCGA Naive Projection" in summary_text
    assert "## Execution Readiness" in summary_text
    assert "naive_manifest_status:" in summary_text
    assert "projection_status:" in summary_text
    assert "pan_cancer_survival_rows:" in summary_text
    assert (out_dir / "run_readiness_summary.tsv").exists()
    assert (out_dir / "evidence_readiness_status.tsv").exists()


def test_report_build_consumes_robustness_summary_when_validation_summary_absent(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    out_dir = tmp_path / "report"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    robust_dir = results_root / "validate"
    robust_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(
        robust_dir / "robustness_concordance_summary.tsv",
        fieldnames=[
            "contrast",
            "status",
            "signature_readiness_status",
            "upstream_meta_status",
            "external_validation_status",
            "readiness_status",
        ],
        rows=[
            {
                "contrast": "PRE_RESPONSE",
                "status": "ok",
                "signature_readiness_status": "completed",
                "upstream_meta_status": "completed",
                "external_validation_status": "completed",
                "readiness_status": "completed",
            }
        ],
    )

    args = Namespace(results_root=str(results_root), out=str(out_dir), run_manifest=str(run_manifest))
    assert cmd_report_build(args) == 0

    summary_text = (out_dir / "pipeline_summary.md").read_text(encoding="utf-8")
    assert "validation_status: completed" in summary_text
    evidence_rows = read_tsv(out_dir / "evidence_readiness_status.tsv")
    validation_rows = [row for row in evidence_rows if row.get("stage") == "validation"]
    assert validation_rows
    assert validation_rows[0]["status"] == "completed"


def test_report_build_summarizes_claim_boundaries_and_figure_manifests(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    out_dir = tmp_path / "report"
    figure_root = tmp_path / "figures"
    run_manifest = tmp_path / "logs/run_manifest.yaml"
    figure_dir = figure_root / "PRE_RESPONSE"
    figure_dir.mkdir(parents=True, exist_ok=True)
    results_root.mkdir(parents=True, exist_ok=True)

    write_tsv(
        figure_dir / "figure_manifest.tsv",
        fieldnames=[
            "figure_id",
            "plot_path",
            "relative_path",
            "framing",
            "scientific_note",
            "caption_sidecar",
        ],
        rows=[
            {
                "figure_id": "tcga1",
                "plot_path": str(figure_dir / "tcga/continuous_cox_hazard_ratios.png"),
                "relative_path": "tcga/continuous_cox_hazard_ratios.png",
                "framing": "prognostic_only",
                "scientific_note": "Prognostic context only (TCGA is non-ICB and not ICB-predictive).",
                "caption_sidecar": str(figure_dir / "tcga1.caption.txt"),
            },
            {
                "figure_id": "immune1",
                "plot_path": str(figure_dir / "immune/l1_box.png"),
                "relative_path": "immune/l1_box.png",
                "framing": "descriptive",
                "scientific_note": "Descriptive immune-state figure.",
                "caption_sidecar": str(figure_dir / "immune1.caption.txt"),
            },
        ],
    )

    args = Namespace(
        results_root=str(results_root),
        out=str(out_dir),
        figure_root=str(figure_root),
        run_manifest=str(run_manifest),
    )
    assert cmd_report_build(args) == 0

    summary_text = (out_dir / "pipeline_summary.md").read_text(encoding="utf-8")
    assert "## Scientific Claim Boundaries" in summary_text
    assert "tcga_projection: required label `prognostic_projection`" in summary_text
    assert "## Visualization Artifacts" in summary_text

    figure_rows = read_tsv(out_dir / "figure_manifest_summary.tsv")
    assert figure_rows[0]["n_figures"] == "2"
    assert figure_rows[0]["n_tcga_figures"] == "1"
    assert figure_rows[0]["caption_lint_failures"] == "0"

    evidence_rows = read_tsv(out_dir / "evidence_readiness_status.tsv")
    visualization_rows = [row for row in evidence_rows if row.get("stage") == "visualization"]
    assert visualization_rows
    assert visualization_rows[0]["status"] == "completed"
