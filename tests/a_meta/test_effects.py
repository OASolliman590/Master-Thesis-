from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from tools.a_meta.effects import study_effects


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


def test_study_effect_is_hand_computed_hedges_g_and_standard_error():
    view = _view([_row("CR"), _row("PR"), _row("SD"), _row("PD")])

    rows = study_effects(view, _features([2.0, 4.0, 0.0, 2.0]), "orr")
    overall = next(row for row in rows if row["drug_class_stratum"] == "ALL")

    expected_g = (1.0 - 3.0 / 7.0) * math.sqrt(2.0)
    expected_variance = (1.0 - 3.0 / 7.0) ** 2 * (1.0 + 2.0 / 8.0)
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


@pytest.mark.parametrize(
    ("labels", "values", "reason"),
    [
        (["CR", "SD", "NE"], [1.0, 2.0, 3.0], "n_R<2"),
        (["CR", "PR", "SD", "PD"], [1.0, 1.0, 1.0, 1.0], "pooled_sd_zero"),
    ],
)
def test_not_estimable_effects_have_na_status_and_reason(labels, values, reason):
    view = _view([_row(label) for label in labels])

    overall = next(
        row for row in study_effects(view, _features(values), "orr")
        if row["drug_class_stratum"] == "ALL"
    )

    assert overall["status"] == "NA"
    assert overall["g"] is None
    assert overall["se"] is None
    assert reason in overall["reason"]


def test_or_ne_and_unknown_are_excluded_and_mixed_drug_classes_are_separate():
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

    effects = study_effects(_view(rows), features, "orr")
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


def test_multi_cancer_study_emits_cancer_effects_and_one_aggregate_effect():
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
    effects = study_effects(view, _features([0, 2, 1, 3, 0, 2, 1, 3]), "orr")

    cancer_effects = [row for row in effects if row["drug_class_stratum"] == "ALL"]
    assert {row["cancer"] for row in cancer_effects} == {"melanoma", "lung", "multi"}
    assert len(cancer_effects) == 3
    per_cancer = [row for row in cancer_effects if row["cancer"] != "multi"]
    aggregate = next(row for row in cancer_effects if row["cancer"] == "multi")
    assert all(row["n_R"] == row["n_NR"] == 2 for row in per_cancer)
    assert aggregate["n_R"] == aggregate["n_NR"] == 4
    assert len({row["study"] for row in cancer_effects}) == 1

