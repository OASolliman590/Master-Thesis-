from __future__ import annotations

from pathlib import Path

from src.pipeline.cli import main
from src.pipeline.common.io import read_tsv, write_tsv
from src.pipeline.modules._analysis_design.registry import build_analysis_design


def _fixture_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(
        cohort: str,
        sample: str,
        patient: str,
        timing: str,
        response: str,
        therapy_class: str = "PD-1",
        therapy_agent: str = "nivolumab",
        cancer: str = "Melanoma",
        assay_type: str = "already_log",
        input_class: str = "processed_matrix",
        include_flag: str = "true",
        exclude_reason: str = "",
    ) -> None:
        rows.append(
            {
                "cohort_id": cohort,
                "sample_id": sample,
                "patient_id": patient,
                "pair_id": patient,
                "timing_category": timing,
                "response_label": response,
                "include_flag": include_flag,
                "exclude_reason": exclude_reason,
                "assay_type": assay_type,
                "input_class": input_class,
                "therapy_class": therapy_class,
                "therapy_agent": therapy_agent,
                "cancer_type": cancer,
                "analysis_role": "analysis",
            }
        )

    for idx, response in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        add("cohort_a", f"A{idx}_PRE", f"PA{idx}", "pre-treatment", response)
        add("cohort_a", f"A{idx}_ON", f"PA{idx}", "on-treatment", response)
        add("cohort_a", f"A{idx}_POST", f"PA{idx}", "post-treatment", response)

    for idx, response in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        add(
            "cohort_b",
            f"B{idx}_PRE",
            f"PB{idx}",
            "pre-treatment",
            response,
            therapy_class="PD-L1",
            therapy_agent="atezolizumab",
            cancer="Non-small cell lung cancer",
        )

    add("cohort_a", "A_UNKNOWN", "PA9", "pre-treatment", "unknown")
    add("cohort_a", "A_METH", "PA10", "pre-treatment", "responder", assay_type="methylation_beta")
    add("cohort_a", "A_UNPAIRED_POST", "PA11", "post-treatment", "responder")
    return rows


def test_analysis_design_normalizes_samples_and_preserves_raw_labels() -> None:
    samples, registry, membership, _ = build_analysis_design(_fixture_rows())

    sample = next(row for row in samples if row["sample_id"] == "B1_PRE")
    assert sample["timing_category"] == "pre-treatment"
    assert sample["response_label"] == "responder"
    assert sample["drug_group"] == "PD_L1"
    assert sample["therapy_agent_raw"] == "atezolizumab"
    assert sample["cancer_group"] == "NSCLC_LUNG"
    assert sample["cancer_type_raw"] == "Non-small cell lung cancer"

    excluded = next(row for row in samples if row["sample_id"] == "A_METH")
    assert excluded["analysis_eligible"] == "false"
    assert excluded["analysis_exclusion_reason"] == "excluded_assay_type:methylation_beta"

    feasible_ids = {row["analysis_id"] for row in registry if row["feasibility_status"] == "feasible"}
    assert {"PRE_RESPONSE", "ON_RESPONSE", "POST_RESPONSE"}.issubset(feasible_ids)
    assert "DELTA_RESPONSE__PRE_TO_ON_TREATMENT" in feasible_ids
    assert "DELTA_RESPONSE__PRE_TO_POST_TREATMENT" in feasible_ids

    member_ids = {row["sample_id"] for row in membership}
    assert "A_METH" not in member_ids
    assert "A_UNPAIRED_POST" in member_ids


def test_delta_membership_is_paired_only() -> None:
    _, _, membership, _ = build_analysis_design(_fixture_rows())

    delta_rows = [
        row
        for row in membership
        if row["analysis_id"] == "DELTA_RESPONSE__PRE_TO_POST_TREATMENT"
    ]
    assert delta_rows
    assert {row["membership_role"] for row in delta_rows} == {
        "case_pre",
        "case_after",
        "control_pre",
        "control_after",
    }
    assert "A_UNPAIRED_POST" not in {row["sample_id"] for row in delta_rows}
    assert {row["pair_id"] for row in delta_rows} == {"PA1", "PA2", "PA3", "PA4"}


def test_manifest_include_false_excludes_design_membership() -> None:
    rows = _fixture_rows()
    for idx, response in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        rows.append(
            {
                "cohort_id": "cohort_manifest_excluded",
                "sample_id": f"X{idx}_PRE",
                "patient_id": f"PX{idx}",
                "pair_id": f"PX{idx}",
                "timing_category": "pre-treatment",
                "response_label": response,
                "include_flag": "false",
                "exclude_reason": "excluded_assay_type_microarray_probe_matrix",
                "assay_type": "already_log",
                "input_class": "processed_matrix",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
                "cancer_type": "Melanoma",
                "analysis_role": "analysis",
            }
        )

    samples, _, membership, _ = build_analysis_design(rows)

    excluded_samples = [row for row in samples if row["cohort_id"] == "cohort_manifest_excluded"]
    assert excluded_samples
    assert {row["analysis_eligible"] for row in excluded_samples} == {"false"}
    assert {row["analysis_exclusion_reason"] for row in excluded_samples} == {
        "excluded_assay_type_microarray_probe_matrix"
    }
    assert "cohort_manifest_excluded" not in {row["cohort_id"] for row in membership}


def test_legacy_pre_only_timing_exclusion_does_not_block_post_axis() -> None:
    rows = _fixture_rows()
    for idx, response in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        rows.append(
            {
                "cohort_id": "cohort_legacy_post",
                "sample_id": f"LP{idx}_POST",
                "patient_id": f"LP{idx}",
                "pair_id": f"LP{idx}",
                "timing_category": "post-treatment",
                "response_label": response,
                "include_flag": "false",
                "exclude_reason": "post_treatment_excluded_from_pre_response",
                "assay_type": "already_log",
                "input_class": "processed_matrix",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
                "cancer_type": "Melanoma",
                "analysis_role": "analysis",
            }
        )

    samples, registry, membership, _ = build_analysis_design(rows)

    post_samples = [row for row in samples if row["cohort_id"] == "cohort_legacy_post"]
    assert post_samples
    assert {row["include_flag"] for row in post_samples} == {"false"}
    assert {row["analysis_eligible"] for row in post_samples} == {"true"}
    post = next(row for row in registry if row["analysis_id"] == "POST_RESPONSE")
    assert post["feasibility_status"] == "feasible"
    assert "cohort_legacy_post" in {
        row["cohort_id"]
        for row in membership
        if row["analysis_id"] == "POST_RESPONSE"
    }


def test_blocked_registry_rows_are_explicit() -> None:
    _, registry, _, _ = build_analysis_design(_fixture_rows())

    blocked = {
        row["analysis_id"]: row
        for row in registry
        if row["feasibility_status"] == "blocked"
    }
    assert "DRUG_STRATIFIED_RESPONSE__ON_TREATMENT__PD_L1" in blocked
    assert blocked["DRUG_STRATIFIED_RESPONSE__ON_TREATMENT__PD_L1"]["blocker_reason"]


def test_ici_combination_family_uses_any_ici_combination_marker() -> None:
    rows = _fixture_rows()
    for idx, response in enumerate(["responder", "responder", "non_responder", "non_responder"], start=1):
        rows.append(
            {
                "cohort_id": "cohort_combo",
                "sample_id": f"C{idx}_PRE",
                "patient_id": f"PC{idx}",
                "pair_id": f"PC{idx}",
                "timing_category": "pre-treatment",
                "response_label": response,
                "include_flag": "true",
                "assay_type": "already_log",
                "input_class": "bulk_rna_seq",
                "therapy_class": "ICI combination",
                "therapy_agent": "durvalumab + metformin",
                "therapy_combination_final": "durvalumab+metformin",
                "cancer_type": "Head and neck squamous cell carcinoma",
                "analysis_role": "analysis",
            }
        )

    samples, registry, membership, _ = build_analysis_design(rows)

    combo_samples = [row for row in samples if row["cohort_id"] == "cohort_combo"]
    assert {row["drug_group"] for row in combo_samples} == {"ICI_COMBINATION"}

    combo_registry = {
        row["analysis_id"]: row
        for row in registry
        if row["analysis_family"] == "ICI_COMBINATION_RESPONSE"
    }
    assert combo_registry["ICI_COMBINATION_RESPONSE__PRE_TREATMENT"]["feasibility_status"] == "feasible"
    combo_members = [
        row
        for row in membership
        if row["analysis_id"] == "ICI_COMBINATION_RESPONSE__PRE_TREATMENT"
    ]
    assert "cohort_combo" in {row["cohort_id"] for row in combo_members}


def test_design_readiness_detects_readable_bulk_rnaseq_assay(tmp_path: Path) -> None:
    cohort_id = "cohort_bulk"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True)
    (cohort_dir / "counts.tsv").write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2\tS3\tS4",
                "GENE1\t10\t11\t3\t4",
                "GENE2\t8\t9\t2\t3",
                "GENE3\t7\t8\t1\t2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[
            {
                "cohort_id": cohort_id,
                "primary_expression_file": "counts.tsv",
                "downloads_folder": cohort_id,
            }
        ],
    )
    rows = [
        {
            "cohort_id": cohort_id,
            "sample_id": sample_id,
            "patient_id": sample_id,
            "pair_id": sample_id,
            "include_flag": "true",
            "input_class": "bulk_rna_seq",
            "timing_category": "pre-treatment",
            "response_label": response,
            "therapy_class": "PD-1",
            "therapy_agent": "nivolumab",
            "cancer_type": "Melanoma",
        }
        for sample_id, response in [
            ("S1", "responder"),
            ("S2", "responder"),
            ("S3", "non_responder"),
            ("S4", "non_responder"),
        ]
    ]

    samples, registry, _, _ = build_analysis_design(
        rows,
        expression_manifest=expression_manifest,
        downloads_root=downloads_root,
        check_expression_readiness=True,
    )

    assert {row["assay_type"] for row in samples} == {"raw_counts"}
    assert {row["analysis_eligible"] for row in samples} == {"true"}
    pre = next(row for row in registry if row["analysis_id"] == "PRE_RESPONSE")
    assert pre["feasibility_status"] == "feasible"


def test_design_readiness_excludes_illumina_probe_matrix(tmp_path: Path) -> None:
    cohort_id = "gse67501_rcc_pd1"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True)
    (cohort_dir / "probe_matrix.tsv").write_text(
        "\n".join(
            [
                "ID_REF\tS1\tDetection Pval\tS2\tDetection Pval\tS3\tDetection Pval\tS4\tDetection Pval",
                "ILMN_3166687\t185.7\t0.17\t141.3\t0.75\t155.7\t0.73\t139.6\t0.97",
                "ILMN_3165566\t168.4\t0.64\t164.6\t0.16\t155.8\t0.73\t162.7\t0.41",
                "ILMN_3164811\t166.2\t0.70\t150.1\t0.50\t129.7\t1.00\t158.4\t0.54",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[
            {
                "cohort_id": cohort_id,
                "primary_expression_file": "probe_matrix.tsv",
                "downloads_folder": cohort_id,
            }
        ],
    )
    rows = [
        {
            "cohort_id": cohort_id,
            "sample_id": sample_id,
            "patient_id": sample_id,
            "pair_id": sample_id,
            "include_flag": "true",
            "input_class": "processed_matrix",
            "timing_category": "pre-treatment",
            "response_label": response,
            "therapy_class": "PD-1",
            "therapy_agent": "nivolumab",
            "cancer_type": "Renal cell carcinoma",
        }
        for sample_id, response in [
            ("S1", "responder"),
            ("S2", "responder"),
            ("S3", "non_responder"),
            ("S4", "non_responder"),
        ]
    ]

    samples, registry, membership, _ = build_analysis_design(
        rows,
        expression_manifest=expression_manifest,
        downloads_root=downloads_root,
        check_expression_readiness=True,
    )

    assert {row["assay_type"] for row in samples} == {"microarray_probe_matrix"}
    assert {row["analysis_eligible"] for row in samples} == {"false"}
    assert not membership
    pre = next(row for row in registry if row["analysis_id"] == "PRE_RESPONSE")
    assert pre["feasibility_status"] == "blocked"


def test_design_build_cli_and_router_dry_run(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    out_dir = tmp_path / "design"
    router_out = tmp_path / "router"
    fieldnames = list(_fixture_rows()[0].keys())
    write_tsv(sample_manifest, fieldnames=fieldnames, rows=_fixture_rows())

    assert (
        main(
            [
                "design",
                "build",
                "--sample-manifest",
                str(sample_manifest),
                "--out",
                str(out_dir),
                "--run-manifest",
                str(tmp_path / "logs" / "run_manifest.yaml"),
            ]
        )
        == 0
    )
    for name in [
        "analysis_sample_manifest.tsv",
        "analysis_contrast_registry.tsv",
        "analysis_contrast_membership.tsv",
        "analysis_design_audit.md",
    ]:
        assert (out_dir / name).exists()

    assert (
        main(
            [
                "router",
                "run",
                "--sample-manifest",
                str(sample_manifest),
                "--analysis-registry",
                str(out_dir / "analysis_contrast_registry.tsv"),
                "--analysis-membership",
                str(out_dir / "analysis_contrast_membership.tsv"),
                "--dry-run",
                "--out",
                str(router_out),
                "--run-manifest",
                str(tmp_path / "logs" / "router_manifest.yaml"),
            ]
        )
        == 0
    )
    summary = read_tsv(router_out / "route_execution_summary.tsv")
    assert summary[0]["track"] == "DESIGN"
    assert summary[0]["track_name"] == "analysis_design"
    assert "PRE_RESPONSE" in summary[0]["analysis_ids"]
    assert "DELTA_RESPONSE__PRE_TO_POST_TREATMENT" in summary[0]["analysis_ids"]
    assert summary[0]["executed"] == "false"


def test_de_and_meta_outputs_carry_analysis_id(tmp_path: Path) -> None:
    analysis_id = "PAN_ICB_RESPONSE__PRE_TREATMENT"
    cohort_id = "cohort_trace"
    downloads_root = tmp_path / "downloads"
    cohort_dir = downloads_root / cohort_id
    cohort_dir.mkdir(parents=True)
    (cohort_dir / "expr.tsv").write_text(
        "\n".join(
            [
                "gene_id\tS1\tS2\tS3\tS4",
                "CD274\t10\t11\t3\t4",
                "IFNG\t8\t9\t2\t3",
                "CXCL9\t7\t8\t1\t2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sample_manifest = tmp_path / "sample_manifest.tsv"
    rows = [
        {
            "cohort_id": cohort_id,
            "sample_id": sample_id,
            "patient_id": sample_id,
            "pair_id": sample_id,
            "include_flag": "true",
                "input_class": "processed_matrix",
            "timing_category": "pre-treatment",
            "response_label": response,
            "cancer_type": "Melanoma",
            "therapy_class": "PD-1",
            "therapy_agent": "nivolumab",
        }
        for sample_id, response in [
            ("S1", "responder"),
            ("S2", "responder"),
            ("S3", "non_responder"),
            ("S4", "non_responder"),
        ]
    ]
    write_tsv(sample_manifest, fieldnames=list(rows[0].keys()), rows=rows)
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file"],
        rows=[{"cohort_id": cohort_id, "primary_expression_file": "expr.tsv"}],
    )
    registry = tmp_path / "analysis_contrast_registry.tsv"
    write_tsv(
        registry,
        fieldnames=["analysis_id", "legacy_contrast_alias", "feasibility_status"],
        rows=[
            {
                "analysis_id": analysis_id,
                "legacy_contrast_alias": "PRE_RESPONSE",
                "feasibility_status": "feasible",
            }
        ],
    )
    membership = tmp_path / "analysis_contrast_membership.tsv"
    write_tsv(
        membership,
        fieldnames=["analysis_id", "cohort_id", "sample_id"],
        rows=[
            {"analysis_id": analysis_id, "cohort_id": cohort_id, "sample_id": row["sample_id"]}
            for row in rows
        ],
    )
    de_out = tmp_path / "de"
    meta_out = tmp_path / "meta"

    assert (
        main(
            [
                "de",
                "run",
                "--contrast",
                "PRE_RESPONSE",
                "--analysis-id",
                analysis_id,
                "--analysis-registry",
                str(registry),
                "--analysis-membership",
                str(membership),
                "--sample-manifest",
                str(sample_manifest),
                "--expression-manifest",
                str(expression_manifest),
                "--downloads-root",
                str(downloads_root),
                "--gene-id-mapping",
                str(tmp_path / "gene_map.tsv"),
                "--allow-weak-gene-mapping",
                "--allow-welch-fallback",
                "--out",
                str(de_out),
                "--run-manifest",
                str(tmp_path / "logs" / "de_manifest.yaml"),
            ]
        )
        == 0
    )
    de_rows = read_tsv(de_out / analysis_id / f"{cohort_id}.tsv")
    assert de_rows
    assert {row["analysis_id"] for row in de_rows} == {analysis_id}

    assert (
        main(
            [
                "meta",
                "run",
                "--contrast",
                "PRE_RESPONSE",
                "--analysis-id",
                analysis_id,
                "--de-dir",
                str(de_out),
                "--include-k1-genes",
                "--skip-forest-plots",
                "--out",
                str(meta_out),
                "--run-manifest",
                str(tmp_path / "logs" / "meta_manifest.yaml"),
            ]
        )
        == 0
    )
    meta_rows = read_tsv(meta_out / analysis_id / "meta_effects.tsv")
    assert meta_rows
    assert {row["analysis_id"] for row in meta_rows} == {analysis_id}


def test_design_plan_runs_writes_dry_run_commands_for_pilot_only(tmp_path: Path) -> None:
    registry = tmp_path / "analysis_contrast_registry.tsv"
    membership = tmp_path / "analysis_contrast_membership.tsv"
    out_dir = tmp_path / "plan"
    execution_root = tmp_path / "analysis_runs"
    write_tsv(
        registry,
        fieldnames=[
            "analysis_id",
            "analysis_family",
            "legacy_contrast_alias",
            "timing_scope",
            "n_cohorts_eligible",
            "n_case_samples",
            "n_control_samples",
            "feasibility_status",
            "blocker_reason",
        ],
        rows=[
            {
                "analysis_id": "PRE_RESPONSE",
                "analysis_family": "PRE_RESPONSE",
                "legacy_contrast_alias": "PRE_RESPONSE",
                "timing_scope": "pre-treatment",
                "n_cohorts_eligible": "2",
                "n_case_samples": "4",
                "n_control_samples": "4",
                "feasibility_status": "feasible",
                "blocker_reason": "",
            },
            {
                "analysis_id": "PAN_ICB_RESPONSE__PRE_TREATMENT",
                "analysis_family": "PAN_ICB_RESPONSE",
                "legacy_contrast_alias": "PRE_RESPONSE",
                "timing_scope": "pre-treatment",
                "n_cohorts_eligible": "2",
                "n_case_samples": "4",
                "n_control_samples": "4",
                "feasibility_status": "feasible",
                "blocker_reason": "",
            },
            {
                "analysis_id": "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
                "analysis_family": "ICI_COMBINATION_RESPONSE",
                "legacy_contrast_alias": "PRE_RESPONSE",
                "timing_scope": "pre-treatment",
                "n_cohorts_eligible": "1",
                "n_case_samples": "2",
                "n_control_samples": "2",
                "feasibility_status": "feasible",
                "blocker_reason": "",
            },
            {
                "analysis_id": "DRUG_STRATIFIED_RESPONSE__PRE_TREATMENT__PD_1",
                "analysis_family": "DRUG_STRATIFIED_RESPONSE",
                "legacy_contrast_alias": "PRE_RESPONSE",
                "timing_scope": "pre-treatment",
                "n_cohorts_eligible": "1",
                "n_case_samples": "2",
                "n_control_samples": "2",
                "feasibility_status": "feasible",
                "blocker_reason": "",
            },
            {
                "analysis_id": "DRUG_STRATIFIED_RESPONSE__PRE_TREATMENT__CTLA_4",
                "analysis_family": "DRUG_STRATIFIED_RESPONSE",
                "legacy_contrast_alias": "PRE_RESPONSE",
                "timing_scope": "pre-treatment",
                "n_cohorts_eligible": "0",
                "n_case_samples": "0",
                "n_control_samples": "0",
                "feasibility_status": "blocked",
                "blocker_reason": "no_cohort_passes_arm_gates",
            },
        ],
    )
    write_tsv(
        membership,
        fieldnames=["analysis_id", "cohort_id", "sample_id"],
        rows=[{"analysis_id": "PRE_RESPONSE", "cohort_id": "cohort_a", "sample_id": "S1"}],
    )

    assert (
        main(
            [
                "design",
                "plan-runs",
                "--analysis-registry",
                str(registry),
                "--analysis-membership",
                str(membership),
                "--pilot",
                "--execution-root",
                str(execution_root),
                "--allow-weak-gene-mapping",
                "--allow-welch-fallback",
                "--out",
                str(out_dir),
                "--run-manifest",
                str(tmp_path / "logs" / "plan_manifest.yaml"),
            ]
        )
        == 0
    )

    plan_rows = read_tsv(out_dir / "analysis_execution_plan.tsv")
    assert len(plan_rows) == 6
    assert {row["analysis_id"] for row in plan_rows} == {
        "PRE_RESPONSE",
        "PAN_ICB_RESPONSE__PRE_TREATMENT",
        "ICI_COMBINATION_RESPONSE__PRE_TREATMENT",
    }
    assert {row["stage"] for row in plan_rows} == {"stage06_de", "stage07_meta"}
    assert all(row["plan_status"] == "planned_dry_run" for row in plan_rows)
    assert all("python3.13 -m src.pipeline.cli" in row["command"] for row in plan_rows)
    assert all(f"{execution_root}/logs/run_manifest.yaml" in row["command"] for row in plan_rows)
    assert any("--allow-welch-fallback" in row["command"] for row in plan_rows)
    assert all("DRUG_STRATIFIED_RESPONSE__PRE_TREATMENT__CTLA_4" not in row["command"] for row in plan_rows)
