from __future__ import annotations

import math

import pytest

from tools.a_meta.synthesis import synthesize


@pytest.mark.requires_r
def test_meta_rma_matches_metafor_normand1999_and_two_stage_toy(tmp_path):
    # escalc(measure="SMD") values from metadat::dat.normand1999, verified
    # against metafor::rma(method="REML", test="adhoc") in the pinned R library.
    yi_vi = [
        (-0.355169640940, 0.013064675542),
        (-0.347940022739, 0.064468876099),
        (-2.317569160164, 0.045812110280),
        (-1.887982252937, 0.160617735936),
        (-0.383964141170, 0.205433278392),
        (0.172148669070, 0.036910570000),
        (0.272052073853, 0.060267125836),
        (-0.424596271894, 0.014863038419),
        (0.289556230081, 0.036271734158),
    ]
    normand = [
        {
            "unit_family": "panel",
            "unit": "EXAMPLE_SMD",
            "study": f"example_{index + 1}",
            "cancer": "melanoma",
            "drug_class_stratum": "ALL",
            "endpoint_family": "orr",
            "g": yi,
            "se": math.sqrt(vi),
            "status": "ok",
        }
        for index, (yi, vi) in enumerate(yi_vi)
    ]
    example = synthesize(
        normand,
        "per_cancer",
        output_dir=tmp_path / "normand1999",
    )
    pooled = example.summaries[0]

    assert pooled["k"] == 9
    assert pooled["estimate"] == pytest.approx(-0.537108258567, abs=1e-6)
    assert pooled["ci_lb"] == pytest.approx(-1.250322209227, abs=1e-6)
    assert pooled["ci_ub"] == pytest.approx(0.176105692093, abs=1e-6)
    assert pooled["tau2"] == pytest.approx(0.790842921048, abs=1e-6)
    assert pooled["label"] == "standard"

    # Compare the signed formula with the first row of metafor's SMD example.
    # metafor's default uses its exact gamma correction and a different
    # large-sample variance; the implementation follows the signed formula.
    n_r, n_nr = 155, 156
    mean_r, mean_nr, sd_r, sd_nr = 55.0, 75.0, 47.0, 64.0
    pooled_sd = math.sqrt(((n_r - 1) * sd_r**2 + (n_nr - 1) * sd_nr**2) / (n_r + n_nr - 2))
    d = (mean_r - mean_nr) / pooled_sd
    correction = 1 - 3 / (4 * (n_r + n_nr) - 9)
    formula_g = correction * d
    formula_variance = correction**2 * (
        (n_r + n_nr) / (n_r * n_nr) + d**2 / (2 * (n_r + n_nr))
    )
    assert formula_g == pytest.approx(-0.355169757748, abs=1e-10)
    assert formula_variance == pytest.approx(0.013002264755, abs=1e-10)
    assert abs(formula_g - yi_vi[0][0]) > 1e-8
    assert abs(formula_variance - yi_vi[0][1]) > 1e-6

    toy = []
    for cancer, value in (("melanoma", 0.2), ("lung", 0.6), ("kidney", 1.0)):
        toy.append({
            "unit_family": "panel",
            "unit": "TOY_PANEL",
            "study": f"toy_{cancer}",
            "cancer": cancer,
            "drug_class_stratum": "ALL",
            "endpoint_family": "orr",
            "g": value,
            "se": 0.1,
            "status": "ok",
        })
    across = synthesize(
        toy,
        "across_cancers",
        output_dir=tmp_path / "across-cancers",
    )
    overall = next(
        row for row in across.summaries
        if row["stratum_type"] == "across_cancers" and row["drug_class_stratum"] == "ALL"
    )

    assert overall["k"] == 3
    assert overall["estimate"] == pytest.approx(0.6, abs=1e-10)
    assert overall["label"] == "standard"
    assert "vi=1 per cancer" in overall["weighting"]
    assert "equal weight per cancer" in across.metadata["cross_cancer_weighting"]

