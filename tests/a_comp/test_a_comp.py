from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import stdev

import pytest

import tools.a_comp.core as a_comp_core
from tools.a_comp.core import (
    ALLOWED_COHORTS,
    EXPECTED_PACKAGE_VERSIONS,
    EXPECTED_REFERENCE_SHA256,
    N15PinError,
    ACompError,
    AVAILABLE_PANEL_IDS,
    CLINICAL_INPUT_COLUMNS,
    classify_input,
    analyze_synthetic_inputs,
    run_real_deconvolution,
    run_synthetic_demo,
    require_analysis_contract,
    _spearman,
    validate_fraction_rows,
    _validate_input_manifest,
    validate_tpm_matrix,
    verify_reference_report,
    validate_sample_alignment,
    _validate_synthetic_endpoint_inputs,
    R_SCRIPT,
    FRACTION_CELL_TYPES,
    FRACTION_INPUT_COLUMNS,
    _write_analysis_input_manifest,
)
from tools.r_bridge import RScriptError, run_r


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _safe_r_retention(test_name, tmp_path):
    return PROJECT_ROOT / ".scratch" / "a_comp" / "test_retention" / f"{test_name}_{tmp_path.parent.name}_{tmp_path.name}"


def _valid_representation():
    return {
        "data_classification": "synthetic",
        "cohort_id": "invented_cohort_alpha",
        "platform": "rnaseq",
        "unit": "TPM",
        "transform": "unlogged",
        "feature_id": "gene_symbol",
        "full_source": True,
        "route_id": "INVENTED_FULL_SOURCE_TPM_V1",
        "n_features": 2,
        "n_samples": 2,
    }


def _read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _write_fixture_tsv(path, columns, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_endpoint_validation_fixture(tmp_path, clinical_rows):
    sample_ids = [row["sample_id"] for row in clinical_rows]
    expression = tmp_path / "invented_tpm.tsv"
    clinical = tmp_path / "invented_clinical.tsv"
    fractions = tmp_path / "invented_fractions.tsv"
    manifest = tmp_path / "invented_manifest.json"
    _write_fixture_tsv(
        expression,
        ("gene_symbol", *sample_ids),
        [
            {"gene_symbol": "GZMA", **dict(zip(sample_ids, ("1", "2", "3", "4")))},
            {"gene_symbol": "PRF1", **dict(zip(sample_ids, ("4", "3", "2", "1")))},
        ],
    )
    _write_fixture_tsv(clinical, CLINICAL_INPUT_COLUMNS, clinical_rows)
    _write_fixture_tsv(
        fractions,
        FRACTION_INPUT_COLUMNS,
        [
            {
                "study_id": "invented_fixture_cohort", "sample_id": sample,
                "cell_type": cell, "fraction": 1 / len(FRACTION_CELL_TYPES),
            }
            for sample in sample_ids
            for cell in FRACTION_CELL_TYPES
        ],
    )
    _write_analysis_input_manifest(
        manifest,
        inputs={"expression": expression, "clinical": clinical, "fractions": fractions},
        cohorts=[{
            "study_id": "invented_fixture_cohort", "cancer": "melanoma",
            "drug_class": "ANTI_PD_L1_AXIS",
        }],
    )
    return expression, clinical, fractions, manifest


def _valid_endpoint_rows():
    categories = (
        ("CR", "DCB", "Responder"),
        ("PR", "NDB", "Progressor"),
        ("SD", "DCB", "Progressor"),
        ("PD", "NDB", "Responder"),
    )
    return [
        {
            "study_id": "invented_fixture_cohort", "sample_id": f"invented_fixture_{index:03d}",
            "cancer": "melanoma", "drug_class": "ANTI_PD_L1_AXIS",
            "orr_label": orr, "clinical_benefit_label": benefit, "source_label": source,
            "orr_definition": "ORR: CR/PR versus SD/PD; original best.resp category retained.",
            "clinical_benefit_definition": "DCB/NDB",
            "source_label_definition": (
                "SOURCE_BINARY; responder/progressor source labels retained; "
                "SOFT does not define this as RECIST."
            ),
        }
        for index, (orr, benefit, source) in enumerate(categories, 1)
    ]


def _pairwise_auc(outcomes, scores):
    positive = [score for outcome, score in zip(outcomes, scores) if outcome == 1]
    negative = [score for outcome, score in zip(outcomes, scores) if outcome == 0]
    assert positive and negative
    wins = sum(p > n for p in positive for n in negative)
    ties = sum(p == n for p in positive for n in negative)
    return (wins + 0.5 * ties) / (len(positive) * len(negative))


def _type7_quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def _bh(values):
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    adjusted = [0.0] * len(values)
    running = 1.0
    for reverse_rank in range(len(order) - 1, -1, -1):
        index = order[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, values[index] * len(values) / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def test_reusable_analyzer_accepts_external_hash_bound_fixture_and_checks_alignment(tmp_path):
    expression = tmp_path / "fixture_tpm.tsv"
    clinical = tmp_path / "fixture_clinical.tsv"
    fractions = tmp_path / "fixture_fractions.tsv"
    manifest = tmp_path / "fixture_manifest.json"
    sample_ids = ["invented_fixture_001", "invented_fixture_002"]
    _write_fixture_tsv(
        expression,
        ("gene_symbol", *sample_ids),
        [
            {"gene_symbol": "GZMA", sample_ids[0]: "1", sample_ids[1]: "4"},
            {"gene_symbol": "PRF1", sample_ids[0]: "2", sample_ids[1]: "3"},
        ],
    )
    clinical_rows = [
        {
            "study_id": "invented_fixture_cohort", "sample_id": sample,
            "cancer": "melanoma", "drug_class": "ANTI_PD_L1_AXIS",
            "orr_label": label, "clinical_benefit_label": benefit,
            "source_label": source, "orr_definition": "ORR: CR/PR versus SD/PD; original best.resp category retained.",
            "clinical_benefit_definition": "DCB/NDB",
            "source_label_definition": "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST.",
        }
        for sample, label, benefit, source in zip(
            sample_ids, ("CR", "PD"), ("DCB", "NDB"), ("Responder", "Progressor")
        )
    ]
    _write_fixture_tsv(clinical, CLINICAL_INPUT_COLUMNS, clinical_rows)
    fraction_rows = [
        {
            "study_id": "invented_fixture_cohort", "sample_id": sample,
            "cell_type": cell, "fraction": 1 / len(FRACTION_CELL_TYPES),
        }
        for sample in reversed(sample_ids)
        for cell in FRACTION_CELL_TYPES
    ]
    _write_fixture_tsv(fractions, FRACTION_INPUT_COLUMNS, fraction_rows)
    _write_analysis_input_manifest(
        manifest,
        inputs={"expression": expression, "clinical": clinical, "fractions": fractions},
        cohorts=[{
            "study_id": "invented_fixture_cohort", "cancer": "melanoma",
            "drug_class": "ANTI_PD_L1_AXIS",
        }],
    )

    with pytest.raises(ACompError, match="Fraction sample coverage/order"):
        analyze_synthetic_inputs(
            expression_path=expression,
            clinical_path=clinical,
            fractions_path=fractions,
            manifest_path=manifest,
            output_dir=tmp_path / "analysis-output",
        )
    assert not (tmp_path / "analysis-output" / "fraction_effects.tsv").exists()


def test_invented_endpoint_encoding_keeps_supported_categories_and_source_definition():
    rows = _valid_endpoint_rows()
    validated = _validate_synthetic_endpoint_inputs(rows)

    assert validated["definitions"] == {
        "orr": "ORR: CR/PR versus SD/PD; original best.resp category retained.",
        "clinical_benefit": "DCB/NDB",
        "source_label": (
            "SOURCE_BINARY; responder/progressor source labels retained; "
            "SOFT does not define this as RECIST."
        ),
    }
    assert validated["outcomes_by_sample"] == {
        "invented_fixture_001": {"orr": 1, "clinical_benefit": 1, "source_label": 1},
        "invented_fixture_002": {"orr": 1, "clinical_benefit": 0, "source_label": 0},
        "invented_fixture_003": {"orr": 0, "clinical_benefit": 1, "source_label": 0},
        "invented_fixture_004": {"orr": 0, "clinical_benefit": 0, "source_label": 1},
    }


@pytest.mark.parametrize(
    ("column", "value", "reason"),
    [
        ("orr_definition", "CR/PR only", "orr_definition"),
        ("clinical_benefit_definition", "CB unknown", "clinical_benefit_definition"),
        ("source_label_definition", "responder means RECIST", "source_label_definition"),
        ("source_label_definition", "", "source_label_definition"),
        ("orr_label", "NE", "orr_label"),
        ("orr_label", "", "orr_label"),
        ("clinical_benefit_label", "unknown", "clinical_benefit_label"),
        ("clinical_benefit_label", "", "clinical_benefit_label"),
        ("source_label", "Unknown", "source_label"),
        ("source_label", "", "source_label"),
    ],
)
def test_analyzer_refuses_unsupported_endpoint_definitions_or_labels_before_r(
    column, value, reason, tmp_path, monkeypatch
):
    rows = _valid_endpoint_rows()
    rows[0][column] = value
    expression, clinical, fractions, manifest = _write_endpoint_validation_fixture(tmp_path, rows)

    def unexpected_r_call(*_args, **_kwargs):
        pytest.fail("invalid invented endpoint input reached an R operation")

    monkeypatch.setattr(a_comp_core, "run_r", unexpected_r_call)
    preflight = {
        "r_version": "4.6.1",
        "bioconductor_version": "3.23",
        "package_versions": dict(EXPECTED_PACKAGE_VERSIONS),
        "reference_files": dict(EXPECTED_REFERENCE_SHA256),
    }
    with pytest.raises(ACompError, match=reason):
        analyze_synthetic_inputs(
            expression_path=expression,
            clinical_path=clinical,
            fractions_path=fractions,
            manifest_path=manifest,
            output_dir=tmp_path / "analysis-output",
            preflight_report=preflight,
        )


def test_proposed_and_missing_n15_pins_refuse_before_any_input_access(tmp_path):
    expression = tmp_path / "must-not-open-expression.tsv"
    manifest = tmp_path / "must-not-open-manifest.json"

    with pytest.raises(N15PinError, match="PROPOSED"):
        run_real_deconvolution(
            cohort_id="riaz_gse91061",
            pin_path=Path("docs/decisions/A_COMP_N15_PROPOSED_20261106.md"),
            expression_path=expression,
            manifest_path=manifest,
            output_dir=tmp_path / "real-output",
        )
    assert not expression.exists()
    assert not manifest.exists()

    with pytest.raises(N15PinError, match="pin document is missing"):
        run_real_deconvolution(
            cohort_id="riaz_gse91061",
            pin_path=tmp_path / "missing-pin.md",
            expression_path=expression,
            manifest_path=manifest,
            output_dir=tmp_path / "real-output-missing-pin",
        )
    assert not expression.exists()
    assert not manifest.exists()


def test_real_cohort_allow_list_and_synthetic_bypass_are_closed():
    assert len(ALLOWED_COHORTS) == 12
    assert classify_input(
        cohort_id="riaz_gse91061",
        data_classification="real",
        representation={
            "platform": "rnaseq",
            "unit": "TPM",
            "transform": "unlogged",
            "feature_id": "gene_symbol",
            "full_source": True,
            "route_id": "accepted A-P2 source TPM route",
        },
    ) == "real"

    invalid = [
        ("gse67501", {"platform": "microarray", "unit": "TPM", "transform": "unlogged", "feature_id": "gene_symbol", "full_source": True}),
        ("gse136961", {"platform": "targeted_rna", "unit": "TPM", "transform": "unlogged", "feature_id": "gene_symbol", "full_source": True}),
        ("braun2020", {"platform": "rnaseq", "unit": "TPM", "transform": "log2", "feature_id": "gene_symbol", "full_source": True}),
        ("imvigor210", {"platform": "rnaseq", "unit": "TPM", "transform": "unlogged", "feature_id": "gene_symbol", "full_source": True}),
        ("riaz_gse91061", {"platform": "rnaseq", "unit": "FPKM", "transform": "unlogged", "feature_id": "gene_symbol", "full_source": True}),
    ]
    for cohort_id, representation in invalid:
        with pytest.raises(ACompError):
            classify_input(
                cohort_id=cohort_id,
                data_classification="real",
                representation=representation,
            )

    for real_id in (*ALLOWED_COHORTS, "imvigor210", "braun2020", "gse67501"):
        with pytest.raises(ACompError, match="synthetic bypass"):
            classify_input(
                cohort_id=real_id,
                data_classification="synthetic",
                representation=_valid_representation(),
            )

    with pytest.raises(ACompError, match="data classification"):
        classify_input(
            cohort_id="invented_cohort_alpha",
            data_classification="invented-but-not-declared",
            representation=_valid_representation(),
        )


def test_tpm_contract_refuses_duplicate_keys_negative_and_nonfinite_values():
    representation = _valid_representation()
    validate_tpm_matrix(
        genes=["TP53", "GZMA"],
        sample_ids=["invented_001", "invented_002"],
        values=[[0.0, 2.5], [1.0, 8.0]],
        representation=representation,
    )

    cases = [
        (["TP53", "TP53"], ["invented_001", "invented_002"], [[1.0, 2.0], [3.0, 4.0]], "duplicate gene"),
        (["TP53", "GZMA"], ["invented_001", "invented_001"], [[1.0, 2.0], [3.0, 4.0]], "duplicate sample"),
        (["TP53", "GZMA"], ["invented_001", "invented_002"], [[1.0, -0.1], [3.0, 4.0]], "non-negative"),
        (["TP53", "GZMA"], ["invented_001", "invented_002"], [[1.0, math.nan], [3.0, 4.0]], "finite"),
        (["TP53", "GZMA"], ["invented_001", "invented_002"], [[1.0], [3.0, 4.0]], "dimensions"),
    ]
    for genes, samples, values, message in cases:
        with pytest.raises(ACompError, match=message):
            validate_tpm_matrix(
                genes=genes,
                sample_ids=samples,
                values=values,
                representation=representation,
            )


def test_reference_version_and_hash_mismatch_refuse():
    report = {
        "r_version": "4.6.1",
        "bioconductor_version": "3.23",
        "package_versions": dict(EXPECTED_PACKAGE_VERSIONS),
        "reference_files": dict(EXPECTED_REFERENCE_SHA256),
    }
    verify_reference_report(report)

    mismatched = {**report, "reference_files": {**report["reference_files"], "TIL10_signature.txt": "0" * 64}}
    with pytest.raises(ACompError, match="reference hash mismatch"):
        verify_reference_report(mismatched)

    mismatched_runtime = {**report, "package_versions": {**report["package_versions"], "quantiseqr": "1.19.0"}}
    with pytest.raises(ACompError, match="package version mismatch"):
        verify_reference_report(mismatched_runtime)


def test_input_manifest_rejects_expression_hash_mismatch(tmp_path):
    expression = tmp_path / "invented_tpm.tsv"
    expression.write_text("gene_symbol\tinvented_001\nTP53\t1\n", encoding="utf-8")
    with pytest.raises(ACompError, match="TPM expression hash mismatch"):
        _validate_input_manifest(
            {"cohort_id": "invented_cohort_alpha", "expression_sha256": "0" * 64},
            expression,
            "invented_cohort_alpha",
        )


def test_python_external_paths_reject_symlink_ancestry_before_pin_access(tmp_path):
    target = tmp_path / "safe"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(ACompError, match="symlink ancestry"):
        run_real_deconvolution(
            cohort_id="riaz_gse91061",
            pin_path=Path("docs/decisions/A_COMP_N15_PROPOSED_20261106.md"),
            expression_path=linked / "invented.tsv",
            manifest_path=tmp_path / "missing.json",
            output_dir=tmp_path / "real-output",
        )


@pytest.mark.requires_r
def test_direct_r_auc_rejects_protected_identity_before_input_columns(tmp_path):
    auc_input = tmp_path / "invented_auc.tsv"
    auc_input.write_text("study_id\tTumor_Shrinkage\n", encoding="utf-8")
    auc_manifest = tmp_path / "auc_manifest.json"
    auc_manifest.write_text(
        '{"manifest_version":1,"producer":"tools.a_meta.synthetic_fixture",'
        '"data_classification":"synthetic","kind":"a_comp_incremental_auc_input",'
        '"payload_sha256":"' + "0" * 64 + '","cohort_ids":["IMvigor-210"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(RScriptError, match="known real or protected"):
        run_r(
            R_SCRIPT,
            {"auc_input": auc_input, "auc_manifest": auc_manifest},
            {
                "project_root": str(PROJECT_ROOT),
                "operation": "synthetic_incremental_auc",
                "expected_outputs": ["incremental_auc.tsv", "bootstrap_assignments.tsv", "bootstrap_receipt.json", "auc_predictions.tsv"],
            },
            tmp_path / "r-auction",
            retention_dir=_safe_r_retention("direct_auc", tmp_path),
        )


@pytest.mark.requires_r
def test_direct_r_deconvolution_requires_signed_n15_before_expression_read(tmp_path):
    expression = tmp_path / "expression.tsv"
    expression.write_text("not a TPM payload\n", encoding="utf-8")
    manifest = tmp_path / "input_manifest.json"
    manifest.write_text('{"data_classification":"real","cohort_id":"riaz_gse91061"}\n', encoding="utf-8")
    with pytest.raises(RScriptError, match="N15 pin status is PROPOSED"):
        run_r(
            R_SCRIPT,
            {
                "expression": expression,
                "input_manifest": manifest,
                "n15_pin": Path("docs/decisions/A_COMP_N15_PROPOSED_20261106.md"),
            },
            {
                "project_root": str(PROJECT_ROOT),
                "operation": "deconvolve",
                "cohort_id": "riaz_gse91061",
                "expected_outputs": ["fractions.tsv", "coverage.tsv", "deconvolution_status.json"],
            },
            tmp_path / "r-deconvolution",
            retention_dir=_safe_r_retention("direct_deconvolution", tmp_path),
        )


def test_fraction_validation_checks_all_types_range_and_sum_without_renormalizing():
    cells = [
        "B cell", "Macrophage M1", "Macrophage M2", "Monocyte", "Neutrophil",
        "NK cell", "T cell CD4+ (non-regulatory)", "T cell CD8+",
        "T cell regulatory (Tregs)", "Myeloid dendritic cell", "Other",
    ]
    rows = [
        {"sample_id": "invented_001", "cell_type": cell, "fraction": 1.0 / 11}
        for cell in cells
    ]
    original = [row["fraction"] for row in rows]
    validate_fraction_rows(rows, expected_sample_ids=["invented_001"], tolerance=1e-6)
    assert [row["fraction"] for row in rows] == original

    for invalid_rows, message in [
        (rows[:-1], "required cell types"),
        ([*rows[:-1], {**rows[-1], "fraction": -0.01}], "range"),
        ([*rows[:-1], {**rows[-1], "fraction": math.inf}], "finite"),
        ([*rows[:-1], {**rows[-1], "fraction": 0.5}], "sum"),
    ]:
        with pytest.raises(ACompError, match=message):
            validate_fraction_rows(
                invalid_rows,
                expected_sample_ids=["invented_001"],
                tolerance=1e-6,
            )


def test_analysis_alignment_requires_identical_order_and_coverage():
    expected = ["invented_001", "invented_002", "invented_003"]
    validate_sample_alignment(
        expected,
        clinical_sample_ids=expected,
        fraction_sample_ids=expected,
        score_sample_ids=expected,
    )
    with pytest.raises(ACompError, match="identical sample order"):
        validate_sample_alignment(
            expected,
            clinical_sample_ids=expected,
            fraction_sample_ids=list(reversed(expected)),
            score_sample_ids=expected,
        )
    with pytest.raises(ACompError, match="coverage"):
        validate_sample_alignment(
            expected,
            clinical_sample_ids=expected[:-1],
            fraction_sample_ids=expected,
            score_sample_ids=expected,
        )


def test_spearman_uses_average_ranks_for_ties_and_returns_known_values():
    assert _spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert _spearman([1, 2, 2, 4], [10, 20, 20, 40]) == pytest.approx(1.0)


def test_real_analysis_refuses_unresolved_bootstrap_and_published_gep_contracts():
    with pytest.raises(ACompError, match="A-COMP bootstrap stream/refit/evaluation"):
        require_analysis_contract(None, data_classification="real")


@pytest.mark.requires_r
def test_real_r_synthetic_quantiseq_and_analysis_integration(tmp_path):
    output = PROJECT_ROOT / ".scratch" / "a_comp" / f"test_demo_{tmp_path.parent.name}_{tmp_path.name}"
    result = run_synthetic_demo(output)

    assert result["data_classification"] == "synthetic"
    assert result["biological_validation"] is False
    assert result["cibersortx"] == "not run"
    assert result["quantiseq"]["method"] == "lsei"
    assert result["quantiseq"]["signature"] == "TIL10"
    assert result["quantiseq"]["tumor"] is True
    assert result["quantiseq"]["arrays"] is False
    assert result["quantiseq"]["scale_mrna"] is True
    assert result["r_version"] == "4.6.1"
    assert result["bioconductor_version"] == "3.23"
    assert result["package_versions"] == EXPECTED_PACKAGE_VERSIONS
    assert result["reference_files"] == EXPECTED_REFERENCE_SHA256
    assert result["fraction_rows"] > 0
    assert result["correlation_rows"] > 0
    assert result["effect_rows"] > 0
    assert result["synthesis_rows"] > 0
    assert result["incremental_auc_rows"] > 0
    assert result["incremental_auc_method"] == "SYNTHETIC_WEIGHTED_GEP18_DEMO"
    assert result["incremental_auc_is_published_gep"] is False
    assert "a_comp_synthetic_demo" in result["bootstrap"]["contract_id"]
    assert result["bootstrap"]["draws_in"] == "R"
    assert result["second_check"]["reported_only"] is True
    assert result["second_check"]["replaced_main_result"] is False
    assert result["second_check"]["outcome_based_rerun"] is False
    assert all((output / name).is_file() for name in (
        "synthetic_summary.json", "fractions.tsv", "coverage.tsv",
        "fraction_effects.tsv", "fraction_synthesis.tsv", "panel_correlations.tsv",
        "incremental_auc.tsv", "auc_predictions.tsv", "bootstrap_assignments.tsv",
        "bootstrap_receipt.json", "analysis_input_manifest.json", "artifact_manifest.json",
    ))
    synthesis_retention = output / ".private" / "bridge_retention" / "synthesis"
    assert synthesis_retention.is_dir()
    assert any(path.is_file() for path in synthesis_retention.rglob("*"))
    fraction_rows = _read_tsv(output / "fractions.tsv")
    by_sample = {}
    for row in fraction_rows:
        by_sample.setdefault(row["sample_id"], []).append(float(row["fraction"]))
    assert len(by_sample) == 48
    assert all(len(values) == 11 for values in by_sample.values())
    assert all(abs(math.fsum(values) - 1.0) <= 1e-6 for values in by_sample.values())
    coverage_rows = _read_tsv(output / "coverage.tsv")
    assert len(coverage_rows) == 40
    assert all(row["status"] == "available" for row in coverage_rows)
    assert all(float(row["coverage_before"]) >= 0.0 for row in coverage_rows)
    assert all(float(row["coverage_after_effective_exclusions"]) >= 0.90 for row in coverage_rows)
    assert sum(row["weak_type_flag"].casefold() == "true" for row in coverage_rows) == 12

    clinical_rows = _read_tsv(output / "clinical.tsv")
    assert {row["cancer"] for row in clinical_rows} == {"melanoma", "bladder"}
    assert {row["drug_class"] for row in clinical_rows} == {"ANTI_PD_L1_AXIS", "ANTI_CTLA4"}
    endpoint_positive_sets = {}
    for study in sorted({row["study_id"] for row in clinical_rows}):
        study_rows = [row for row in clinical_rows if row["study_id"] == study]
        endpoint_positive_sets[study] = {
            "orr": frozenset(row["sample_id"] for row in study_rows if row["orr_label"] in {"CR", "PR"}),
            "clinical_benefit": frozenset(row["sample_id"] for row in study_rows if row["clinical_benefit_label"] == "DCB"),
            "source_label": frozenset(row["sample_id"] for row in study_rows if row["source_label"].casefold() == "responder"),
        }
        assert len(set(endpoint_positive_sets[study].values())) == 3

    effect_rows = _read_tsv(output / "fraction_effects.tsv")
    partitions = {
        (row["unit_family"], row["endpoint_family"], row["endpoint_definition_id"])
        for row in effect_rows
    }
    assert partitions == {
        ("fraction", "orr", "ORR"),
        ("fraction", "clinical_benefit", "CB_DCB_NDB"),
        ("fraction", "source_label", "SOURCE_LABEL_UNSPECIFIED"),
    }
    selected = next(
        row for row in effect_rows
        if row["study"] == "invented_cohort_01" and row["unit"] == "B cell"
        and row["endpoint_family"] == "orr" and row["drug_class_stratum"] == "ALL"
        and row["status"] == "ok"
    )
    values_by_sample = {
        row["sample_id"]: float(row["fraction"])
        for row in fraction_rows
        if row["study_id"] == "invented_cohort_01" and row["cell_type"] == "B cell"
    }
    study_clinical = [row for row in clinical_rows if row["study_id"] == "invented_cohort_01"]
    responders = [values_by_sample[row["sample_id"]] for row in study_clinical if row["orr_label"] in {"CR", "PR"}]
    nonresponders = [values_by_sample[row["sample_id"]] for row in study_clinical if row["orr_label"] not in {"CR", "PR"}]
    pooled_sd = math.sqrt(
        ((len(responders) - 1) * stdev(responders) ** 2
         + (len(nonresponders) - 1) * stdev(nonresponders) ** 2)
        / (len(responders) + len(nonresponders) - 2)
    )
    df = len(responders) + len(nonresponders) - 2
    j_correction = math.exp(
        math.lgamma(df / 2) - 0.5 * math.log(df / 2) - math.lgamma((df - 1) / 2)
    )
    independent_g = j_correction * (
        (math.fsum(responders) / len(responders) - math.fsum(nonresponders) / len(nonresponders))
        / pooled_sd
    )
    assert float(selected["g"]) == pytest.approx(independent_g, abs=1e-12)
    assert independent_g > 0
    assert (float(selected["g"]) > 0) == (
        math.fsum(responders) / len(responders) > math.fsum(nonresponders) / len(nonresponders)
    )

    synthesis_rows = _read_tsv(output / "fraction_synthesis.tsv")
    assert {row["requested_stratum"] for row in synthesis_rows} == {
        "per_cancer", "per_drug_class", "melanoma_cancer_drug", "across_cancers",
    }
    assert {row["requested_endpoint_family"] for row in synthesis_rows} == {
        "orr", "clinical_benefit", "source_label",
    }
    assert any(row["stratum"] == "bladder" for row in synthesis_rows if row["requested_stratum"] == "per_cancer")
    assert any(row["stratum"] == "ANTI_PD_L1_AXIS" for row in synthesis_rows if row["requested_stratum"] == "per_drug_class")
    assert any(row["stratum"] == "melanoma|ANTI_CTLA4" for row in synthesis_rows if row["requested_stratum"] == "melanoma_cancer_drug")
    assert any(row["stage"] == "stage2_across_cancers" for row in synthesis_rows if row["requested_stratum"] == "across_cancers")
    pooled_rows = [row for row in synthesis_rows if row["status"] == "pooled" and row.get("p") and row.get("q")]
    assert pooled_rows, "invented fixture must exercise the fraction-family BH adjustment"
    bh_groups = {}
    for row in pooled_rows:
        key = (
            row["requested_stratum"], row["requested_unit_family"], row["stratum_type"],
            row["stratum"], row["drug_class_stratum"], row["requested_endpoint_family"],
            row["requested_endpoint_definition_id"],
        )
        bh_groups.setdefault(key, []).append(row)
    for family_rows in bh_groups.values():
        adjusted = _bh([float(row["p"]) for row in family_rows])
        for row, expected_q in zip(family_rows, adjusted):
            assert float(row["q"]) == pytest.approx(expected_q, abs=1e-12)

    correlation_rows = _read_tsv(output / "panel_correlations.tsv")
    assert len(correlation_rows) == 4 * len(FRACTION_CELL_TYPES) * 12
    assert {row["score_id"] for row in correlation_rows} == set(AVAILABLE_PANEL_IDS) | {"CYT"}
    assert all("no raw pooling" in row["summary_type"] for row in _read_tsv(output / "panel_correlation_summary.tsv"))

    auc_rows = _read_tsv(output / "incremental_auc.tsv")
    prediction_rows = _read_tsv(output / "auc_predictions.tsv")
    assignments = _read_tsv(output / "bootstrap_assignments.tsv")
    receipt = json.loads((output / "bootstrap_receipt.json").read_text(encoding="utf-8"))
    assert receipt["published_gep_used"] is False
    assert receipt["paired_evaluation"] == "baseline and augmented AUROC use identical row_index assignments"
    assert receipt["assignment_sha256"] == hashlib.sha256(
        (output / "bootstrap_assignments.tsv").read_bytes()
    ).hexdigest()
    predictions_by_task = {}
    for row in prediction_rows:
        task = row["task_id"]
        row_index = int(row["row_index"])
        assert row_index not in predictions_by_task.setdefault(task, {})
        predictions_by_task[task][row_index] = {
            "outcome": int(row["outcome"]),
            "baseline": float(row["baseline_prediction"]),
            "augmented": float(row["augmented_prediction"]),
        }
    assignments_by_task_check = {}
    for row in assignments:
        assignments_by_task_check.setdefault((row["task_id"], row["check"]), {}).setdefault(
            int(row["replicate"]), []
        ).append(row)
    estimable = [row for row in auc_rows if row["status"] == "ok"]
    unavailable = [row for row in auc_rows if row["status"] != "ok"]
    assert estimable and unavailable
    assert all(row["reason"] for row in unavailable)
    observed_second_check_flags = []
    for row in estimable:
        task_id = "|".join((
            "a_comp_synthetic_demo_v2", row["study"], row["endpoint_family"],
            row["baseline_model"], f"fraction__{row['fraction']}",
        ))
        task_predictions = predictions_by_task[task_id]
        row_indices = sorted(task_predictions)
        assert row_indices == list(range(1, len(row_indices) + 1))
        outcomes = [task_predictions[index]["outcome"] for index in row_indices]
        base_scores = [task_predictions[index]["baseline"] for index in row_indices]
        augmented_scores = [task_predictions[index]["augmented"] for index in row_indices]
        base_auc = _pairwise_auc(outcomes, base_scores)
        augmented_auc = _pairwise_auc(outcomes, augmented_scores)
        assert float(row["auc_baseline"]) == pytest.approx(base_auc, abs=1e-12)
        assert float(row["auc_augmented"]) == pytest.approx(augmented_auc, abs=1e-12)
        assert float(row["delta_auc"]) == pytest.approx(augmented_auc - base_auc, abs=1e-12)

        intervals = {}
        for check_name, output_prefix in (
            ("primary_synthetic_only", ""),
            ("second_check_report_only", "second_check_"),
        ):
            replicate_groups = assignments_by_task_check[(task_id, check_name)]
            deltas = []
            for replicate_rows in replicate_groups.values():
                replicate_rows.sort(key=lambda item: int(item["draw"]))
                sample_indices = [int(item["row_index"]) for item in replicate_rows]
                sampled_y = [task_predictions[index]["outcome"] for index in sample_indices]
                sampled_base = [task_predictions[index]["baseline"] for index in sample_indices]
                sampled_augmented = [task_predictions[index]["augmented"] for index in sample_indices]
                deltas.append(
                    _pairwise_auc(sampled_y, sampled_augmented)
                    - _pairwise_auc(sampled_y, sampled_base)
                )
            intervals[check_name] = (_type7_quantile(deltas, 0.025), _type7_quantile(deltas, 0.975))
            assert float(row[f"{output_prefix}ci_lb"]) == pytest.approx(intervals[check_name][0], abs=1e-12)
            assert float(row[f"{output_prefix}ci_ub"]) == pytest.approx(intervals[check_name][1], abs=1e-12)
        shift = max(abs(main - second) for main, second in zip(
            intervals["primary_synthetic_only"], intervals["second_check_report_only"]
        ))
        assert float(row["second_check_endpoint_shift"]) == pytest.approx(shift, abs=1e-12)
        flag = row["second_check_flag_gt_0_01"].casefold() == "true"
        assert flag is (shift > 0.01)
        assert row["second_check_reported_only"].casefold() == "true"
        assert row["second_check_replaced_main"].casefold() == "false"
        assert row["outcome_based_rerun"].casefold() == "false"
        observed_second_check_flags.append(flag)
    assert any(observed_second_check_flags), "second_check must show a nontrivial report-only flag"

    artifact_manifest = json.loads((output / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert artifact_manifest["manifest_schema"] == "A_COMP_ARTIFACT_MANIFEST_V1"
    assert artifact_manifest["n15"]["accepted_pin_sha256"] is None
    assert artifact_manifest["n15"]["proposal_status"] == "PROPOSED_UNSIGNED"
    assert {row["operation"] for row in artifact_manifest["r"]["runs"]} == {
        "preflight", "synthetic_demo", "synthetic_incremental_auc",
    }
    assert set(artifact_manifest["r"]["reference_files"]) == set(EXPECTED_REFERENCE_SHA256)
    assert "tools/a_comp/core.py" in artifact_manifest["python"]["code_sha256"]
    assert len(artifact_manifest["scoring"]["scoring_source_sha256"]) == 64
    assert set(artifact_manifest["python"]["lock_sha256"]) == {
        "r/renv.lock", "tools/a_dav/requirements-synthetic.txt",
    }
    product_paths = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(output).parts)
        and path.name != "artifact_manifest.json"
    }
    assert set(artifact_manifest["public_products"]) == product_paths
    for relative, expected_hash in artifact_manifest["public_products"].items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == expected_hash
    assert all(".private" not in name and "bridge" not in name for name in artifact_manifest["public_products"])
