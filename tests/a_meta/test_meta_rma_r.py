from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from tools.a_meta.effects import study_effects
from tools.a_meta.r_manifest import run_r_sanitised
from tools.a_meta.synthesis import synthesize
from tests.a_meta.helpers import (
    synthetic_effect_input_manifest,
    synthetic_effect_rows_manifest,
)


def _effect(unit_family, unit, study, *, cancer="melanoma", g=0.2, se=0.1, patient_set_id=None):
    return {
        "unit_family": unit_family,
        "unit": unit,
        "study": study,
        "cancer": cancer,
        "cancer_components": cancer,
        "drug_class_stratum": "ALL",
        "endpoint_family": "orr",
        "endpoint_definition_id": "ORR",
        "patient_set_id": patient_set_id or f"set-{study}-{cancer}",
        "n_R": 4,
        "n_NR": 4,
        "g": g,
        "se": se,
        "status": "ok",
    }


def _read_tsv(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _metafor_reference(tmp_path, *, groups=(), cross=(), equal_weights=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    reference_script = tmp_path / "metafor_reference.R"
    cross_weights = ", weights = rep(1, nrow(cross))" if equal_weights else ""
    script = '''source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "metafor"))
config <- bridge_config()
groups <- read.delim(config$inputs$groups, check.names = FALSE)
cross <- read.delim(config$inputs$cross, check.names = FALSE)
if (nrow(groups)) {
  effect <- metafor::escalc(
    measure = "SMD", m1i = groups$mean_R, sd1i = groups$sd_R, n1i = groups$n_R,
    m2i = groups$mean_NR, sd2i = groups$sd_NR, n2i = groups$n_NR
  )
  write.table(data.frame(id = groups$id, yi = effect$yi, vi = effect$vi),
              file.path(config$output_dir, "hedges.tsv"), sep = "\\t", row.names = FALSE,
              col.names = TRUE, quote = FALSE, na = "NA")
} else {
  writeLines("id\\tyi\\tvi", file.path(config$output_dir, "hedges.tsv"))
}
if (nrow(cross)) {
  fit <- metafor::rma.uni(
    yi = cross$yi, vi = cross$vi__CROSS_WEIGHTS__,
    method = "REML", test = "adhoc"
  )
  write.table(data.frame(estimate = as.numeric(fit$b[1L, 1L]), se = as.numeric(fit$se[1L]),
                         ci_lb = as.numeric(fit$ci.lb[1L]), ci_ub = as.numeric(fit$ci.ub[1L]),
                         tau2 = as.numeric(fit$tau2[1L])),
              file.path(config$output_dir, "cross.tsv"), sep = "\\t", row.names = FALSE,
              col.names = TRUE, quote = FALSE, na = "NA")
} else {
  writeLines("estimate\\tse\\tci_lb\\tci_ub\\ttau2", file.path(config$output_dir, "cross.tsv"))
}
bridge_write_session(config$output_dir)
'''
    reference_script.write_text(
        script.replace("__CROSS_WEIGHTS__", cross_weights),
        encoding="utf-8",
    )
    input_dir = tmp_path / "reference-input"
    input_dir.mkdir(exist_ok=True)
    groups_path = input_dir / "groups.tsv"
    cross_path = input_dir / "cross.tsv"
    for path, rows, columns in (
        (groups_path, groups, ("id", "mean_R", "sd_R", "n_R", "mean_NR", "sd_NR", "n_NR")),
        (cross_path, cross, ("yi", "vi")),
    ):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    result = run_r_sanitised(
        reference_script,
        {"groups": groups_path, "cross": cross_path},
        {"expected_outputs": ["hedges.tsv", "cross.tsv"]},
        tmp_path / "reference-output",
        script_id="tests/a_meta/metafor_reference.R",
    )
    return result


@pytest.mark.requires_r
def test_effect_g_and_ls_variance_match_escalc_default_for_several_group_sizes(tmp_path):
    sizes = ((2, 2), (5, 5), (7, 11), (10, 2))
    reference_rows = []
    effects = []
    for index, (n_r, n_nr) in enumerate(sizes):
        r_values = [float(value * 2 + index) for value in range(n_r)]
        nr_values = [float(value * 2 + 4 + index) for value in range(n_nr)]
        reference_rows.append({
            "id": f"size_{n_r}_{n_nr}",
            "mean_R": sum(r_values) / n_r,
            "sd_R": math.sqrt(sum((value - sum(r_values) / n_r) ** 2 for value in r_values) / (n_r - 1)),
            "n_R": n_r,
            "mean_NR": sum(nr_values) / n_nr,
            "sd_NR": math.sqrt(sum((value - sum(nr_values) / n_nr) ** 2 for value in nr_values) / (n_nr - 1)),
            "n_NR": n_nr,
        })
        rows = [
            {"raw_orr": "CR", "endpoint_definition": "ORR: CR/PR versus SD/PD; original category retained.",
             "drug_class_normalised": "ANTI_PD_L1_AXIS"}
            for _ in r_values
        ] + [
            {"raw_orr": "SD", "endpoint_definition": "ORR: CR/PR versus SD/PD; original category retained.",
             "drug_class_normalised": "ANTI_PD_L1_AXIS"}
            for _ in nr_values
        ]
        view = type("View", (), {
            "metadata": type("Metadata", (), {
                "cohort_id": f"synthetic_{index}",
                "cancer": "melanoma",
                "endpoint_families": ("orr",),
                "uniform_drug_class": None,
            })(),
            "clinical_rows": rows,
        })()
        features = [
            {"patient_row": row, "unit": "GENE_X", "value": value, "unit_family": "gene"}
            for row, value in enumerate(r_values + nr_values)
        ]
        manifest = synthetic_effect_input_manifest(view, features, tmp_path / f"effect-{index}.json")
        effects.extend(study_effects(view, features, "orr", by_drug_class=False, provenance_manifest=manifest))

    reference = _metafor_reference(tmp_path / "escalc", groups=reference_rows)
    expected = {row["id"]: row for row in _read_tsv(reference.outputs["hedges.tsv"])}
    for index, (n_r, n_nr) in enumerate(sizes):
        row = next(item for item in effects if item["study"] == f"synthetic_{index}")
        result = expected[f"size_{n_r}_{n_nr}"]
        assert row["g"] == pytest.approx(float(result["yi"]), abs=1e-10)
        assert row["se"] ** 2 == pytest.approx(float(result["vi"]), abs=1e-10)
    assert sizes[0] == (2, 2)
    assert sum(sizes[1]) == 10


@pytest.mark.requires_r
def test_meta_rma_normand1999_and_two_stage_equal_weight_real_variance(tmp_path):
    # escalc(measure="SMD") values from metafor::dat.normand1999.
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
        _effect("panel", "EXAMPLE_SMD", f"example_{index + 1}", g=yi, se=math.sqrt(vi))
        for index, (yi, vi) in enumerate(yi_vi)
    ]
    normand_manifest = synthetic_effect_rows_manifest(normand, tmp_path / "normand-manifest.json")
    example = synthesize(
        normand,
        "per_cancer",
        output_dir=tmp_path / "normand1999",
        provenance_manifest=normand_manifest,
    )
    pooled = example.summaries[0]
    normand_reference = _metafor_reference(
        tmp_path / "normand-reference",
        cross=({"yi": yi, "vi": vi} for yi, vi in yi_vi),
    )
    normand_expected = _read_tsv(normand_reference.outputs["cross.tsv"])[0]

    assert pooled["k"] == 9
    assert pooled["estimate"] == pytest.approx(float(normand_expected["estimate"]), abs=1e-10)
    assert pooled["ci_lb"] == pytest.approx(float(normand_expected["ci_lb"]), abs=1e-10)
    assert pooled["ci_ub"] == pytest.approx(float(normand_expected["ci_ub"]), abs=1e-10)
    assert pooled["tau2"] == pytest.approx(float(normand_expected["tau2"]), abs=1e-10)
    assert pooled["estimate"] == pytest.approx(-0.537108258567, abs=1e-6)
    assert pooled["ci_lb"] == pytest.approx(-1.250322209227, abs=1e-6)
    assert pooled["ci_ub"] == pytest.approx(0.176105692093, abs=1e-6)
    assert pooled["tau2"] == pytest.approx(0.790842921048, abs=1e-6)
    assert pooled["label"] == "standard"
    assert pooled["n_cancers"] == 1
    assert pooled["n_studies"] == 9

    toy = [
        _effect("panel", "TOY_PANEL", f"toy_{cancer}", cancer=cancer, g=value, se=0.1)
        for cancer, value in (("melanoma", 0.2), ("lung", 0.6), ("kidney", 1.0))
    ]
    toy_manifest = synthetic_effect_rows_manifest(toy, tmp_path / "toy-manifest.json")
    across = synthesize(
        toy,
        "across_cancers",
        output_dir=tmp_path / "across-cancers",
        provenance_manifest=toy_manifest,
    )
    overall = next(row for row in across.summaries if row["stage"] == "stage2_across_cancers")
    reference = _metafor_reference(
        tmp_path / "cross-reference",
        cross=({"yi": value, "vi": 0.01} for value in (0.2, 0.6, 1.0)),
        equal_weights=True,
    )
    expected = _read_tsv(reference.outputs["cross.tsv"])[0]
    assert overall["k"] == 3
    assert overall["n_cancers"] == 3
    assert overall["n_studies"] == 3
    assert overall["estimate"] == pytest.approx(0.6, abs=1e-10)
    assert overall["estimate"] == pytest.approx(float(expected["estimate"]), abs=1e-10)
    assert overall["se"] == pytest.approx(float(expected["se"]), abs=1e-10)
    assert overall["ci_lb"] == pytest.approx(float(expected["ci_lb"]), abs=1e-10)
    assert overall["ci_ub"] == pytest.approx(float(expected["ci_ub"]), abs=1e-10)
    assert overall["ci_lb"] == pytest.approx(-0.394, abs=0.02)
    assert overall["ci_ub"] == pytest.approx(1.594, abs=0.02)
    assert overall["tau2"] == pytest.approx(float(expected["tau2"]), abs=1e-10)
    assert overall["se"] ** 2 == pytest.approx(
        sum(0.01 + overall["tau2"] for _ in range(3)) / 3**2,
        abs=1e-10,
    )
    assert overall["label"] == "standard"
    assert "equal metafor weights" in overall["weighting"]
    assert "vi=1 per cancer" not in overall["weighting"]

    unequal_variance = [
        _effect("panel", "UNEQUAL_PANEL", "shared_study", cancer="melanoma", g=0.2, se=0.1),
        _effect("panel", "UNEQUAL_PANEL", "study_b", cancer="lung", g=0.6, se=0.2),
        _effect("panel", "UNEQUAL_PANEL", "shared_study", cancer="kidney", g=1.0, se=0.3),
    ]
    unequal_manifest = synthetic_effect_rows_manifest(
        unequal_variance, tmp_path / "unequal-variance-manifest.json"
    )
    unequal = synthesize(
        unequal_variance,
        "across_cancers",
        output_dir=tmp_path / "unequal-across-cancers",
        provenance_manifest=unequal_manifest,
    )
    unequal_overall = next(
        row for row in unequal.summaries if row["stage"] == "stage2_across_cancers"
    )
    unequal_reference = _metafor_reference(
        tmp_path / "unequal-cross-reference",
        cross=({"yi": value, "vi": variance} for value, variance in (
            (0.2, 0.01), (0.6, 0.04), (1.0, 0.09),
        )),
        equal_weights=True,
    )
    unequal_expected = _read_tsv(unequal_reference.outputs["cross.tsv"])[0]
    assert unequal_overall["estimate"] == pytest.approx(0.6, abs=1e-10)
    assert unequal_overall["estimate"] == pytest.approx(float(unequal_expected["estimate"]), abs=1e-10)
    assert unequal_overall["se"] == pytest.approx(float(unequal_expected["se"]), abs=1e-10)
    assert unequal_overall["tau2"] == pytest.approx(float(unequal_expected["tau2"]), abs=1e-10)
    assert unequal_overall["n_cancers"] == 3
    assert unequal_overall["n_studies"] == 2


@pytest.mark.requires_r
def test_meta_regression_uses_ten_independent_studies(tmp_path):
    effects = [
        _effect(
            "panel",
            "SUBGROUP_PANEL",
            f"subgroup_study_{index}",
            cancer="melanoma" if index < 5 else "lung",
            g=0.1 + index * 0.02,
            patient_set_id=f"subgroup-set-{index}",
        )
        for index in range(10)
    ]
    manifest = synthetic_effect_rows_manifest(effects, tmp_path / "subgroup-manifest.json")
    result = synthesize(
        effects,
        "per_cancer",
        output_dir=tmp_path / "subgroup-real-r",
        provenance_manifest=manifest,
    )

    assert result.subgroup_tests[0]["total_k"] == 10
    assert result.subgroup_tests[0]["status"] == "tested"
    assert math.isfinite(result.subgroup_tests[0]["F"])
    assert math.isfinite(result.subgroup_tests[0]["p"])
    assert result.r_manifest["script"] == "r/scripts/meta_rma.R"
    assert "script_path" not in result.r_manifest
    r_manifest_text = (tmp_path / "subgroup-real-r/R/manifest.json").read_text(encoding="utf-8")
    assert "/Volumes/" not in r_manifest_text
    assert "/Users/" not in r_manifest_text
