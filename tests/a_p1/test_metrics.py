from __future__ import annotations

import pytest

from tools.a_p1 import category_metrics, cyt_score, source_category


@pytest.mark.parametrize(
    ("scores", "categories", "expected_or_auc", "expected_dc_auc", "expected_delta"),
    [
        ([1.0, 2.0, 1.0], ["O", "SD", "PD"], 0.25, 0.75, 0.5),
        ([1.0, 1.0, 1.0], ["O", "SD", "PD"], 0.5, 0.5, 0.0),
        ([2.0, 1.0, 2.0], ["O", "SD", "PD"], 0.75, 0.25, -0.5),
    ],
)
def test_endpoint_delta_uses_fixed_score_and_half_credit_for_ties(
    scores, categories, expected_or_auc, expected_dc_auc, expected_delta
):
    result = category_metrics(scores, categories)

    assert result["auc_orr"] == expected_or_auc
    assert result["auc_dcr"] == expected_dc_auc
    assert result["delta"] == expected_delta
    assert result["pairwise_auc"] == {
        "O_SD": 0.0 if scores[0] < scores[1] else 1.0 if scores[0] > scores[1] else 0.5,
        "O_PD": 0.5,
        "SD_PD": 1.0 if scores[1] > scores[2] else 0.0 if scores[1] < scores[2] else 0.5,
    }


def test_category_composition_identities_are_reported_and_verified():
    result = category_metrics(
        [0.1, 0.7, 0.4, 0.8, 0.2, 0.9],
        ["O", "O", "SD", "SD", "PD", "PD"],
    )

    assert result["decomposition_verified"] is True
    assert result["auc_orr_decomposed"] == pytest.approx(result["auc_orr"], abs=1e-15)
    assert result["auc_dcr_decomposed"] == pytest.approx(result["auc_dcr"], abs=1e-15)


def test_no_sd_is_a_structural_zero_outside_the_informative_set():
    result = category_metrics([0.2, 0.8, 0.5, 0.9], ["O", "O", "PD", "PD"])

    assert result["status"] == "structurally_zero_no_sd"
    assert result["informative"] is False
    assert result["auc_orr"] == result["auc_dcr"] == 0.25
    assert result["delta"] == 0.0
    assert result["pairwise_auc"]["O_SD"] is None
    assert result["pairwise_auc"]["SD_PD"] is None


@pytest.mark.parametrize(
    ("categories", "missing"),
    [(["SD", "PD"], "O"), (["O", "SD"], "PD")],
)
def test_absent_o_or_pd_makes_endpoint_contrast_nonestimable(categories, missing):
    result = category_metrics([0.1, 0.8], categories)

    assert result["status"] == "nonestimable_missing_o_or_pd"
    assert result["informative"] is False
    assert result["category_counts"][missing] == 0
    assert result["delta"] is None
    assert result["nonestimability_reason"] == "missing_" + missing.lower()


@pytest.mark.parametrize("response", ["NE", "", "UNKNOWN", "R", "NR", "other"])
def test_unknown_ne_and_binary_source_labels_are_not_mapped_to_categories(response):
    assert source_category(response) is None


def test_fixed_cyt_uses_exact_unlogged_tpm_scale_and_missing_is_not_zero():
    assert cyt_score(4.0, 9.0) == 6.0
    assert cyt_score(0.0, 9.0) == 0.0
    assert cyt_score(None, 9.0) is None
    assert cyt_score(4.0, "NA") is None
    with pytest.raises(ValueError, match="nonnegative"):
        cyt_score(-1.0, 4.0)
