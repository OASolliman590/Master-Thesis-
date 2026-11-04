from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from tools.a_meta.effects import study_effects
from tools.a_meta.features import FeatureTable
from tests.a_meta.helpers import synthetic_effect_input_manifest


def _view(rows, *, cancer="melanoma", study="synthetic"):
    return SimpleNamespace(
        metadata=SimpleNamespace(
            cohort_id=study,
            cancer=cancer,
            endpoint_families=("orr",),
            uniform_drug_class=None,
        ),
        clinical_rows=rows,
    )


def _features(values):
    return [
        {"patient_row": row_index, "unit": "GENE_X", "value": value}
        for row_index, value in enumerate(values)
    ]


def _row(label, drug="ANTI_PD_L1_AXIS", *, definition="ORR RECIST CR PR SD PD"):
    return {
        "raw_orr": label,
        "endpoint_definition": definition,
        "drug_class_normalised": drug,
    }


def test_study_effect_is_hand_computed_hedges_g_and_standard_error(tmp_path):
    view = _view([_row("CR"), _row("PR"), _row("SD"), _row("PD")])
    features = _features([2.0, 4.0, 0.0, 2.0])
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "synthetic-manifest.json")

    rows = study_effects(view, features, "orr", provenance_manifest=manifest)
    overall = next(row for row in rows if row["drug_class_stratum"] == "ALL")

    correction = 1.0 / math.sqrt(math.pi)
    expected_g = correction * math.sqrt(2.0)
    expected_variance = 1.0 + expected_g**2 / 8.0
    assert overall["unit_family"] == "gene"
    assert overall["n_R"] == 2
    assert overall["n_NR"] == 2
    assert overall["mean_R"] == 3.0
    assert overall["mean_NR"] == 1.0
    assert overall["sd_R"] == pytest.approx(math.sqrt(2.0))
    assert overall["sd_NR"] == pytest.approx(math.sqrt(2.0))
    assert overall["g"] == pytest.approx(expected_g)
    assert overall["se"] == pytest.approx(math.sqrt(expected_variance))
    assert overall["status"] == "ok"
    assert overall["endpoint_definition_id"] == "ORR"
    assert len(overall["patient_set_id"]) == 64


@pytest.mark.parametrize(
    ("labels", "values", "reason"),
    [
        (["CR", "SD", "NE"], [1.0, 2.0, 3.0], "n_R<2"),
        (["CR", "PR", "SD", "PD"], [1.0, 1.0, 1.0, 1.0], "pooled_sd_zero"),
    ],
)
def test_not_estimable_effects_have_na_status_and_reason(tmp_path, labels, values, reason):
    view = _view([_row(label) for label in labels])
    features = _features(values)
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "synthetic-manifest.json")

    overall = next(
        row for row in study_effects(view, features, "orr", provenance_manifest=manifest)
        if row["drug_class_stratum"] == "ALL"
    )

    assert overall["status"] == "NA"
    assert overall["g"] is None
    assert overall["se"] is None
    assert reason in overall["reason"]


def test_incomplete_panel_coverage_produces_na_effect(tmp_path):
    view = _view([_row("CR"), _row("PR"), _row("SD"), _row("PD")])
    features = FeatureTable(
        cohort_id="synthetic",
        unit_family="panel",
        values_by_unit={"INCOMPLETE_PANEL": [1.0, 2.0, 3.0, 4.0]},
        n_patients=4,
        coverage={"INCOMPLETE_PANEL": {
            "n_found": 2, "n_total": 3, "missing": ["GENE_Z"], "complete": False,
        }},
    )
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "incomplete-panel.json")

    effect = study_effects(
        view,
        features,
        "orr",
        by_drug_class=False,
        provenance_manifest=manifest,
    )[0]

    assert effect["unit_family"] == "panel"
    assert effect["status"] == "NA"
    assert effect["g"] is None
    assert "incomplete_feature_coverage" in effect["reason"]


def test_or_ne_and_unknown_are_excluded_and_mixed_drug_classes_are_separate(tmp_path):
    rows = [
        _row("CR", "ANTI_PD_L1_AXIS"),
        _row("PR", "ANTI_PD_L1_AXIS"),
        _row("SD", "ANTI_PD_L1_AXIS"),
        _row("PD", "ANTI_PD_L1_AXIS"),
        _row("NE", "ANTI_PD_L1_AXIS"),
        _row("UNKNOWN", "ANTI_PD_L1_AXIS"),
        _row("CR", "ANTI_CTLA4"),
        _row("PR", "ANTI_CTLA4"),
        _row("SD", "ANTI_CTLA4"),
        _row("PD", "ANTI_CTLA4"),
        _row("CR", "OTHER_EXCLUDED"),
        _row("PD", "OTHER_EXCLUDED"),
    ]
    features = _features([float(index) for index in range(len(rows))])

    view = _view(rows)
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "synthetic-manifest.json")
    effects = study_effects(view, features, "orr", provenance_manifest=manifest)
    strata = {row["drug_class_stratum"] for row in effects}
    overall = next(row for row in effects if row["drug_class_stratum"] == "ALL")
    pd1 = next(row for row in effects if row["drug_class_stratum"] == "ANTI_PD_L1_AXIS")
    ctla4 = next(row for row in effects if row["drug_class_stratum"] == "ANTI_CTLA4")

    assert strata == {"ALL", "ANTI_PD_L1_AXIS", "ANTI_CTLA4"}
    assert (overall["n_R"], overall["n_NR"]) == (4, 4)
    assert (pd1["n_R"], pd1["n_NR"]) == (2, 2)
    assert (ctla4["n_R"], ctla4["n_NR"]) == (2, 2)
    assert "not_evaluable=1" in overall["reason"]
    assert "unknown=1" in overall["reason"]


def test_multi_cancer_study_emits_cancer_effects_and_one_aggregate_effect(tmp_path):
    rows = [
        {**_row("CR"), "cancer_normalised": "melanoma"},
        {**_row("PR"), "cancer_normalised": "melanoma"},
        {**_row("SD"), "cancer_normalised": "melanoma"},
        {**_row("PD"), "cancer_normalised": "melanoma"},
        {**_row("CR"), "cancer_normalised": "lung"},
        {**_row("PR"), "cancer_normalised": "lung"},
        {**_row("SD"), "cancer_normalised": "lung"},
        {**_row("PD"), "cancer_normalised": "lung"},
    ]
    view = _view(rows, cancer="multi", study="multi_synthetic")
    features = _features([0, 2, 1, 3, 0, 2, 1, 3])
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "synthetic-manifest.json")
    effects = study_effects(view, features, "orr", provenance_manifest=manifest)

    cancer_effects = [row for row in effects if row["drug_class_stratum"] == "ALL"]
    assert {row["cancer"] for row in cancer_effects} == {"melanoma", "lung", "multi"}
    assert len(cancer_effects) == 3
    per_cancer = [row for row in cancer_effects if row["cancer"] != "multi"]
    aggregate = next(row for row in cancer_effects if row["cancer"] == "multi")
    assert all(row["n_R"] == row["n_NR"] == 2 for row in per_cancer)
    assert aggregate["n_R"] == aggregate["n_NR"] == 4
    assert len({row["study"] for row in cancer_effects}) == 1


def test_clinical_benefit_definitions_receive_separate_effect_ids(tmp_path):
    rows = [
        {**_row(label), "raw_clinical_benefit": label, "endpoint_definition": definition}
        for definition, labels in (
            ("DCB/NDB", ("DCB", "DCB", "NDB", "NDB")),
            ("Clinical benefit: PFS > 6 months.", ("R", "R", "NR", "NR")),
        )
        for label in labels
    ]
    view = _view(rows)
    view.metadata.endpoint_families = ("clinical_benefit",)
    features = _features([0, 2, 1, 3, 5, 7, 4, 6])
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "definitions.json")

    effects = study_effects(
        view,
        features,
        "clinical_benefit",
        by_drug_class=False,
        provenance_manifest=manifest,
    )

    assert {row["endpoint_definition_id"] for row in effects} == {"CB_DCB_NDB", "CB_PFS_GT6M"}
    assert len(effects) == 2


def test_unmapped_endpoint_definition_fails_closed(tmp_path):
    view = _view([_row("CR", definition="mystery endpoint"), _row("PR"), _row("SD"), _row("PD")])
    features = _features([1.0, 2.0, 3.0, 4.0])
    manifest = synthetic_effect_input_manifest(view, features, tmp_path / "unknown-definition.json")

    with pytest.raises(ValueError, match="Unmapped or ambiguous endpoint definition"):
        study_effects(view, features, "orr", provenance_manifest=manifest)


def test_study_effects_fails_closed_for_signed_ids_and_locked_test(tmp_path):
    features = _features([1.0, 2.0, 3.0, 4.0])
    for cohort_id in ("liu2019", "IMvigor210"):
        view = _view([_row("CR"), _row("PR"), _row("SD"), _row("PD")], study=cohort_id)
        if cohort_id == "liu2019":
            with pytest.raises(ValueError, match="Real-cohort outcomes are restricted"):
                study_effects(view, features, "orr")
            manifest = synthetic_effect_input_manifest(view, features, tmp_path / "contradictory.json")
            with pytest.raises(ValueError, match="Synthetic provenance contradicts"):
                study_effects(view, features, "orr", allow_outcomes=True, provenance_manifest=manifest)
        else:
            with pytest.raises(ValueError, match="IMvigor210"):
                study_effects(view, features, "orr", allow_outcomes=True)

