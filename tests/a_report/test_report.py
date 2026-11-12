from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.a_report.__main__ import CODE_VERSION, FIXTURE_ID, LABEL, ROOT


HAS_RENDERING_DEPS = all(
    importlib.util.find_spec(name) is not None for name in ("matplotlib", "numpy")
)


def _persistent_private_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="a-report-w10-test-")).resolve()


def _test_env(mpl_config_dir: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if mpl_config_dir is not None:
        mpl_config_dir.mkdir(parents=True, exist_ok=True)
        env["MPLCONFIGDIR"] = str(mpl_config_dir)
    return env


def _visible_svg_text(path: Path) -> str:
    svg_ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(path).getroot()
    return " ".join(node.text or "" for node in root.iter(svg_ns + "text"))


@pytest.mark.skipif(
    not HAS_RENDERING_DEPS,
    reason="figure rendering requires Matplotlib and NumPy; use sc-analysis Python",
)
def test_cli_builds_invented_shells_with_visible_labels() -> None:
    test_dir = _persistent_private_dir()
    output = test_dir / "paper-a-shell"
    env = _test_env(test_dir / "mplconfig")
    result = subprocess.run(
        [sys.executable, "-m", "tools.a_report", "--output-dir", str(output)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["classification"] == LABEL
    assert manifest["data_classification"] == "invented"
    assert manifest["biological_validation"] is False
    assert manifest["external_inputs_opened"] is False
    assert manifest["figure_count"] == 18
    assert manifest["table_count"] == 7
    assert len(list((output / "figures").glob("*.svg"))) == 18
    assert len(list((output / "figures").glob("*.pdf"))) == 18

    for path in sorted((output / "figures").glob("*.svg")):
        assert LABEL in _visible_svg_text(path), path.name
        source = path.read_text(encoding="utf-8")
        assert CODE_VERSION in source, path.name
        assert FIXTURE_ID in source, path.name
        assert manifest["input_provenance"]["fixture_sha256"] in source, path.name

    sc1_text = _visible_svg_text(output / "figures" / "Figure_06_sc1_compartment_dotplot.svg").casefold()
    for phrase in (
        "per-study donor medians", "custom panels only", "median donor log2(cpm+1)",
        "custom panel a", "custom panel b", "fixed-size composite dots", "0.00",
        "not assessed", "insufficient donors", "m5/m6 genes are not plotted",
        "study-specific scale", "0–1.00", "all zero/unavailable fallback",
        "0–1.20", "0–2.40", "no cross-study pooling or z-scoring",
    ):
        assert phrase in sc1_text, phrase
    assert "m5/m6 composite" not in sc1_text
    assert "coverage" not in sc1_text

    sc3_text = _visible_svg_text(output / "figures" / "Figure_07_sc3_exploratory_effects.svg").casefold()
    for phrase in (
        "sc-3 exploratory heatmaps", "panel hedges g", "cohort", "compartment",
        "recist", "pathology", "t-cell expansion", "distinct nonclinical metric family",
        "nonclinical metric", "not clinical response", "fixed symmetric scale", "0.00", "na",
    ):
        assert phrase in sc3_text, phrase
    assert "exploratory size change" not in sc3_text
    assert "score difference" not in sc3_text

    along_text = _visible_svg_text(output / "figures" / "Figure_08_along_pairing_time_effects.svg").casefold()
    for phrase in (
        "panel 1b", "pairing_summary.tsv", "specimens", "assays", "patients_in",
        "baseline/follow-up/paired", "candidate→selected", "same-lesion",
        "pre · day 0", "on · exact day +28", "on · interval +21 to +42",
        "panel 2b", "r_minus_nr_change", "r minus nr in (on−pre)",
        "ancova sensitivity", "r_minus_nr_on_value_conditional_on_pre",
        "not central delta", "not_estimable", "real source/release: not admitted",
        "invented too-few-pairs layout",
        "real unique-patient n: unknown", "real specimen/assay n: unknown separately",
        "experimental unit: patient", "delta_primary", "no patient rows",
        "claim limit: invented layout only, no findings",
    ):
        assert phrase in along_text, phrase

    along_supplements = {
        "Supplement_S3_a_long_1a.svg": (
            "a-long1a", "which longitudinal source families and time windows are represented?",
            "source flow into family and regimen/window coverage", "invented family a",
            "source-flow unit: independent study family",
            "selected_pairs", "real patient n", "unknown", "specimen / assay n",
            "catalogue entries are not independent cohort counts", "no estimate or interval",
        ),
        "Supplement_S4_a_long_2a.svg": (
            "a-long2a", "what changes within each response group?", "within_group_deltas.tsv",
            "window=baseline_to_on",
            "delta_r", "delta_nr", "response=r", "response=nr", "not_estimable",
            "real unique-patient n: unknown", "real specimen/assay n: unknown separately",
            "not evidence of a response-by-time interaction",
        ),
        "Supplement_S5_a_long_2c.svg": (
            "a-long2c", "which programme directions replicate?", "invented programme a",
            "invented family a", "invented cancer",
            "comparison unit: independent study family across cancers",
            "within-study effects use patient units",
            "invented interval", "real independent-family count: unknown",
            "influence availability: unavailable", "do not establish replication",
            "shared baselines are not counted as independent evidence",
        ),
        "Supplement_S6_a_long_3c.svg": (
            "a-long3c", "lesion, timing, and selection sensitivity", "delta_primary",
            "same-lesion sensitivity", "exact-day sensitivity",
            "tighter-timing sensitivity", "n_patients_used", "missing-biopsy",
            "not assumed random", "unavailable",
        ),
    }
    for filename, phrases in along_supplements.items():
        supplement_text = _visible_svg_text(output / "figures" / filename).casefold()
        for phrase in phrases:
            assert phrase in supplement_text, (filename, phrase)

    gated_expectations = {
        "Supplement_S7_a_long_3a_gated.svg": (
            "moderator-design identifiability", "cancer / regimen / class / window",
            "rank and confounding", "independent studies", "paired-patient support",
            "study n unknown", "paired-patient n unknown", "no estimates shown",
        ),
        "Supplement_S8_a_long_3b_gated.svg": (
            "released moderator-effect heterogeneity", "not an efficacy ranking",
            "independent study families", "family n unknown",
        ),
        "Supplement_S9_a_long_4a_gated.svg": (
            "orthogonal cellular/modality context", "no causal proof", "patient units",
            "cells/spots are nested", "nested cell/spot n unknown",
        ),
        "Supplement_S10_a_long_4b_gated.svg": (
            "nma feasibility", "qualified temporal handoff", "unsupported arrows are absent",
            "studies/programmes", "study/programme n unknown",
        ),
    }
    for filename, phrases in gated_expectations.items():
        gated_text = _visible_svg_text(output / "figures" / filename).casefold()
        for phrase in phrases:
            assert phrase in gated_text, (filename, phrase)
        assert "no estimate or interval" in gated_text

    for path in sorted((output / "figures").glob("*.pdf")):
        assert path.read_bytes().startswith(b"%PDF-"), path.name
        assert path.stat().st_size > 1000, path.name

    tables = sorted((output / "tables").glob("*.tsv"))
    assert len(tables) == 7
    for path in tables:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            rows = list(reader)
        assert rows, path.name
        assert "classification" in (reader.fieldnames or ())
        assert all(row["classification"] == LABEL for row in rows), path.name
        assert all(row["data_classification"] == "invented" for row in rows), path.name
        assert all(row["input_fixture_sha256"] == manifest["input_provenance"]["fixture_sha256"]
                   for row in rows), path.name

    validation_path = output / "tables" / "Table_04_a_p2_validation.tsv"
    with validation_path.open(newline="", encoding="utf-8") as stream:
        validation_rows = list(csv.DictReader(stream, delimiter="\t"))
    development_rows = [
        row for row in validation_rows
        if row["validation_stage"] == "development leave-family-out example"
    ]
    final_row = next(row for row in validation_rows if row["validation_stage"] == "final-test example")
    assert {row["metric"] for row in development_rows} == {"learner_auc", "cyt_auc", "delta_auc"}
    assert all(row["output_file"] == "primary_aggregates.tsv" for row in development_rows)
    assert all("metric,weighting,study_count,cancer_count,value" in row["source_metric_columns"]
               for row in development_rows)
    assert final_row["output_file"] == "final_metrics.tsv"
    assert "learner_auc,cyt_auc,delta_auc,lower_95,upper_95" in final_row["source_metric_columns"]
    assert "pending" not in final_row["schema_mapping_status"].casefold()

    effects_path = output / "tables" / "Table_03_full_effects_multiplicity.tsv"
    with effects_path.open(newline="", encoding="utf-8") as stream:
        effect_rows = list(csv.DictReader(stream, delimiter="\t"))
    panel_effect_rows = [row for row in effect_rows if row["record_type"] == "study_effect"
                         and row["unit_family"] == "panel"]
    actual_panel_effects = {
        (row["cancer"], row["drug_class_stratum"]): (
            row["unit"], row["study"], float(row["g"]),
            float(row["ci_lb"]), float(row["ci_ub"]),
        )
        for row in panel_effect_rows
    }
    assert actual_panel_effects == {
        ("Cancer A", "Drug A"): (
            "Panel A", "Invented study A", 0.48, 0.09, 0.87,
        ),
        ("Cancer A", "Drug B"): (
            "Panel A", "Invented study B", 0.18, -0.21, 0.57,
        ),
        ("Cancer B", "Drug A"): (
            "Panel B", "Invented study C", -0.31, -0.72, 0.10,
        ),
    }

    pair_path = output / "tables" / "Table_05_a_long_pairing_attrition.tsv"
    with pair_path.open(newline="", encoding="utf-8") as stream:
        pair_rows = list(csv.DictReader(stream, delimiter="\t"))
    for row in pair_rows:
        specimens = int(row["specimens_in"])
        assays = int(row["assays_in"])
        baseline = int(row["patients_with_baseline"])
        followup = int(row["patients_with_followup"])
        paired = int(row["patients_paired"])
        selected = int(row["selected_pairs"])
        assert baseline + followup <= specimens
        assert assays >= specimens
        assert paired <= baseline and paired <= followup
        assert selected == paired
        assert row["platform_counts"].endswith(f"{assays} assays")
        assert int(row["derived_unpaired_baseline_patients"]) == (
            int(row["patients_with_baseline"]) - int(row["patients_paired"])
        )
        assert row["derived_field_definition"] == (
            "patients_with_baseline - patients_paired; single-window invented example"
        )
        assert row["selected_by_window"].startswith("Invented single window:")
        assert row["endpoint_evaluable_counts"] == "unavailable before release"
        assert row["endpoint_status"] == "unavailable before release"
    assert set(pair_rows[0]) >= {
        "study_id", "specimens_in", "assays_in", "patients_in", "patients_with_baseline",
        "patients_with_followup", "patients_paired", "candidate_pairs", "selected_pairs",
        "technical_replicate_specimens", "same_lesion_pairs", "platform_counts",
        "selected_by_window", "endpoint_evaluable_counts", "endpoint_status",
    }

    schema_path = output / "tables" / "Table_00_product_schema_map.tsv"
    with schema_path.open(newline="", encoding="utf-8") as stream:
        schema_rows = list(csv.DictReader(stream, delimiter="\t"))
    sc1_schema = next(row for row in schema_rows if row["shell_table"] == "Figure_06_sc1_compartment_dotplot")
    sc3_schema = next(row for row in schema_rows if row["shell_table"] == "Figure_07_sc3_exploratory_effects")
    assert "unit_summary.tsv" in sc1_schema["source_schema"]
    assert "median_log2_cpm_plus1" in sc1_schema["mapped_fields"]
    assert "median_percent_cells_detected" in sc1_schema["mapped_fields"]
    assert "not M5/M6 genes" in sc1_schema["mapping_status"]
    assert "panel Hedges g by cohort and compartment" in sc3_schema["mapped_fields"]
    assert "response_metric" in sc3_schema["mapped_fields"]
    assert "log2FoldChange" in sc3_schema["mapped_fields"]
    assert "T-cell expansion remain separate" in sc3_schema["mapping_status"]
    assert "not clinical response" in sc3_schema["mapping_status"]

    along_schema = next(row for row in schema_rows if row["shell_table"] == "Table_05_a_long_pairing_attrition.tsv")
    for field in (
        "patients_with_baseline", "patients_with_followup", "patients_paired",
        "candidate_pairs", "selected_pairs", "effect_scale_id", "contrast",
        "effect_role", "source_family_id", "adjusted_p", "within_group_deltas.tsv",
        "model_support.tsv R columns:unit,n_input,n_complete,n_patients_input",
        "synthesis_support.tsv:analysis_group_id,preflight_reason,k,n_input,n_excluded,independence_status",
    ):
        assert field in along_schema["mapped_fields"], field
    all_along_schema = next(row for row in schema_rows if row["shell_table"] == "W8_A_LONG_all_products")
    assert "pairing_summary.tsv" in along_schema["source_schema"]
    assert "a_long_effects.tsv" in along_schema["source_schema"]
    assert "a_long_synthesis.tsv" in along_schema["source_schema"]
    assert "within_group_deltas.tsv" in all_along_schema["source_schema"]
    assert "stay private" in all_along_schema["mapped_fields"]
    assert "no pair or patient rows" in all_along_schema["mapped_fields"]

    schema_by_component = {row["shell_table"]: row for row in schema_rows}
    figure8_schema = schema_by_component["Figure_08_along_pair_structure_and_direct_effect"]
    assert "A-LONG1B + A-LONG2B" == figure8_schema["product"]
    for field in (
        "specimens_in", "assays_in", "patients_paired", "candidate_pairs",
        "selected_pairs", "same_lesion_pairs", "R_minus_NR_change",
        "central_change_contrast", "R_minus_NR_on_value_conditional_on_pre",
    ):
        assert field in figure8_schema["mapped_fields"], field

    source_schema = schema_by_component["Supplement_S3_a_long_1a_source_coverage"]
    for field in (
        "source_family_id", "overlap_receipt_id", "overlap_status", "regimen_id",
        "window_id", "selected_pairs",
    ):
        assert field in source_schema["mapped_fields"], field
    assert "comparison unit is independent study family" in source_schema["mapping_status"]
    assert "not independent cohort counts" in source_schema["mapping_status"]

    within_schema = schema_by_component["Supplement_S4_a_long_2a_within_group_delta"]
    for field in (
        "within_group_deltas.tsv:unit,window,response,arm,n,estimate,se,ci_lb,ci_ub,df,effect_role,status,reason,policy_status",
        "baseline_to_on", "not an interaction",
    ):
        assert field in within_schema["mapped_fields"] + within_schema["mapping_status"]

    programme_schema = schema_by_component["Supplement_S5_a_long_2c_programme_directions"]
    for field in (
        "source_family_id", "cancer", "analysis_method_id", "effect_scale_id",
        "independence_status", "prediction_interval_lb", "adjusted_p",
    ):
        assert field in programme_schema["mapped_fields"], field
    assert "within-study effects use patient units" in programme_schema["mapping_status"]
    assert "influence availability UNAVAILABLE" in programme_schema["mapping_status"]

    sensitivity_schema = schema_by_component["Supplement_S6_a_long_3c_sensitivity"]
    for field in ("same-lesion", "exact-day", "tighter-timing", "n_patients_used"):
        assert field in sensitivity_schema["mapped_fields"], field
    assert "missing biopsies are not assumed random" in sensitivity_schema["mapping_status"]

    gated_schema = schema_by_component["Supplements_S7-S10_a_long_gated_questions"]
    for phrase in (
        "3A moderator-design identifiability", "3B released moderator-effect heterogeneity",
        "4A orthogonal cellular/modality context", "4B NMA feasibility/qualified temporal handoff",
        "3A independent studies plus paired-patient support, 3B independent families, 4A patients with nested cells/spots, 4B studies/programmes",
    ):
        assert phrase in gated_schema["mapped_fields"], phrase
    assert "unsupported network arrows" in gated_schema["mapping_status"]


def test_cli_help_works_without_optional_plotting_dependencies() -> None:
    result = subprocess.run(
        [sys.executable, "-S", "-m", "tools.a_report", "--help"],
        cwd=ROOT,
        env=_test_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--output-dir" in result.stdout


def test_missing_plotting_dependency_is_reported_without_artifact_writes() -> None:
    test_dir = _persistent_private_dir()
    output = test_dir / "missing-plotting-dependency"
    result = subprocess.run(
        [sys.executable, "-S", "-m", "tools.a_report", "--output-dir", str(output)],
        cwd=ROOT,
        env=_test_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "figure rendering requires Matplotlib and NumPy" in result.stderr
    assert output.is_dir()
    assert list(output.iterdir()) == []


def test_cli_refuses_repository_output_path() -> None:
    candidate = ROOT / "tools" / "a_report" / "must_not_be_created"
    result = subprocess.run(
        [sys.executable, "-S", "-m", "tools.a_report", "--output-dir", str(candidate)],
        cwd=ROOT,
        env=_test_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "outside the repository" in result.stderr
    assert not candidate.exists()


def test_cli_refuses_nonempty_directory_without_changing_existing_bytes() -> None:
    test_dir = _persistent_private_dir()
    output = test_dir / "existing-output"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    report = output / "manifest.json"
    sentinel_bytes = b"preserve this invented sentinel\n"
    report_bytes = b"preserve these existing report bytes\n"
    sentinel.write_bytes(sentinel_bytes)
    report.write_bytes(report_bytes)
    original_names = {path.name for path in output.iterdir()}
    result = subprocess.run(
        [sys.executable, "-S", "-m", "tools.a_report", "--output-dir", str(output)],
        cwd=ROOT,
        env=_test_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "nonempty output directory" in result.stderr
    assert {path.name for path in output.iterdir()} == original_names
    assert sentinel.read_bytes() == sentinel_bytes
    assert report.read_bytes() == report_bytes
