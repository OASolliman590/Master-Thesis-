from __future__ import annotations

import csv
import json

import pytest

from tools.a_meta.synthesis import synthesize
from tools.a_meta import synthesis as synthesis_module
from tools.r_bridge import FakeR
from tests.a_meta.helpers import synthetic_effect_rows_manifest


def _effect(
    unit_family,
    unit,
    study,
    *,
    cancer="melanoma",
    drug="ALL",
    endpoint="orr",
    definition_id=None,
    patient_set_id=None,
    cancer_components=None,
    g=0.2,
    se=0.1,
):
    definition_id = definition_id or ("CB_DCB_NDB" if endpoint == "clinical_benefit" else "ORR")
    return {
        "unit_family": unit_family,
        "unit": unit,
        "study": study,
        "cancer": cancer,
        "cancer_components": cancer_components or ("melanoma,lung" if cancer == "multi" else cancer),
        "drug_class_stratum": drug,
        "endpoint_family": endpoint,
        "endpoint_definition_id": definition_id,
        "patient_set_id": patient_set_id or f"set-{study}-{cancer}-{drug}-{endpoint}-{definition_id}",
        "n_R": 4,
        "n_NR": 4,
        "g": g,
        "se": se,
        "status": "ok",
        "reason": "",
    }


def _canned_meta(rows):
    columns = (
        "analysis_id", "k", "n_cancers", "n_studies", "estimate", "se", "ci_lb", "ci_ub", "tau2", "I2",
        "Q", "p", "fixed_estimate", "fixed_ci_lb", "fixed_ci_ub", "status", "reason",
    )
    return "\t".join(columns) + "\n" + "".join(
        "\t".join(str(row.get(column, "NA")) for column in columns) + "\n"
        for row in rows
    )


def test_bh_families_keep_drug_strata_separate_within_one_cancer():
    rows = [
        {
            "unit_family": "panel",
            "unit": "PANEL_A",
            "status": "pooled",
            "p": 0.01,
            "q": None,
            "k": 3,
            "stratum_type": "cancer",
            "stratum": "melanoma",
            "drug_class_stratum": "ALL",
            "endpoint_family": "orr",
        },
        {
            "unit_family": "panel",
            "unit": "PANEL_A",
            "status": "pooled",
            "p": 0.03,
            "q": None,
            "k": 3,
            "stratum_type": "cancer",
            "stratum": "melanoma",
            "drug_class_stratum": "ANTI_PD_L1_AXIS",
            "endpoint_family": "orr",
        },
    ]

    synthesis_module._apply_fdr(rows)

    assert [row["q"] for row in rows] == [0.01, 0.03]


def _pooled(analysis_id, k, estimate, p):
    return {
        "analysis_id": analysis_id,
        "k": k,
        "n_cancers": 1,
        "n_studies": k,
        "estimate": estimate,
        "se": 0.2,
        "ci_lb": estimate - 0.4,
        "ci_ub": estimate + 0.4,
        "tau2": 0.03,
        "I2": 20,
        "Q": 4.0,
        "p": p,
        "fixed_estimate": estimate,
        "fixed_ci_lb": estimate - 0.3,
        "fixed_ci_ub": estimate + 0.3,
        "status": "pooled",
        "reason": "",
    }


def _synthesize_synthetic(effects, stratum, *, output_dir, runner=None, manifest_dir=None):
    if manifest_dir is None:
        manifest_dir = output_dir
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = synthetic_effect_rows_manifest(effects, manifest_dir / "synthetic-fixture-manifest.json")
    return synthesize(
        effects,
        stratum,
        output_dir=output_dir,
        runner=runner,
        provenance_manifest=manifest,
    )


def test_fake_r_synthesis_obeys_k_rules_fdr_families_and_endpoint_boundaries(tmp_path):
    effects = []
    effects += [_effect("gene", "GENE_A", f"study_{index}", g=0.1 * index) for index in range(3)]
    effects += [_effect("gene", "GENE_B", f"study_{index}") for index in range(2)]
    effects += [_effect("panel", "PANEL_A", f"benefit_{index}", endpoint="clinical_benefit") for index in range(3)]
    effects += [_effect("panel", "PANEL_A", f"orr_a_{index}", g=0.2 * index) for index in range(3)]
    effects += [_effect("panel", "PANEL_B", f"orr_b_{index}", g=0.3 * index) for index in range(3)]
    effects += [_effect("panel", "PANEL_C", "single_study", g=0.25, se=0.1)]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 3, 0.2, 0.01),
                {"analysis_id": "A00002", "k": 2, "status": "not_pooled", "reason": "gene_pooling_requires_k>=3"},
                _pooled("A00003", 3, 0.3, 0.03),
                _pooled("A00004", 3, 0.4, 0.04),
                _pooled("A00005", 3, 0.5, 0.20),
                {"analysis_id": "A00006", "k": 1, "estimate": 0.25, "se": 0.1,
                 "ci_lb": 0.054, "ci_ub": 0.446, "status": "single_study", "reason": "no pooling"},
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(effects, "per_cancer", output_dir=tmp_path / "synthesis", runner=fake)

    gene_a = next(row for row in result.summaries if row["unit"] == "GENE_A")
    gene_b = next(row for row in result.summaries if row["unit"] == "GENE_B")
    panel_a_orr = next(row for row in result.summaries if row["unit"] == "PANEL_A" and row["endpoint_family"] == "orr")
    panel_a_benefit = next(row for row in result.summaries if row["unit"] == "PANEL_A" and row["endpoint_family"] == "clinical_benefit")
    panel_b = next(row for row in result.summaries if row["unit"] == "PANEL_B")
    panel_c = next(row for row in result.summaries if row["unit"] == "PANEL_C")

    assert gene_a["label"] == "standard"
    assert gene_a["q"] == pytest.approx(0.01)
    assert gene_b["k"] == 2
    assert gene_b["label"] == "tentative_k2"
    assert gene_b["status"] == "not_pooled"
    gene_b_rows = [row for row in result.summaries if row["unit"] == "GENE_B"]
    assert len(gene_b_rows) == 2
    assert [row["estimate"] for row in gene_b_rows] == pytest.approx([0.2, 0.2])
    assert [row["se"] for row in gene_b_rows] == pytest.approx([0.1, 0.1])
    assert all(row["ci_lb"] is not None and row["ci_ub"] is not None for row in gene_b_rows)
    assert all(row["status"] == "not_pooled" and row["q"] is None for row in gene_b_rows)
    assert {row["stage"] for row in gene_b_rows} == {"per_study"}
    assert panel_a_orr["q"] == pytest.approx(0.08)
    assert panel_b["q"] == pytest.approx(0.20)
    assert panel_a_benefit["q"] == pytest.approx(0.03)
    assert panel_c["label"] == "single_study"
    assert panel_c["estimate"] == pytest.approx(0.25)
    assert panel_c["q"] is None


def test_panel_coverage90_stays_in_its_own_stratum_fdr_and_label(tmp_path):
    effects = []
    for family in ("panel", "panel_coverage90"):
        for index in range(3):
            effect = _effect(family, "PANEL_A", f"{family}_{index}")
            if family == "panel_coverage90":
                effect.update({
                    "n_found": 17,
                    "n_total": 18,
                    "sensitivity_label": "sensitivity only; does not support claims alone",
                })
            effects.append(effect)
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 3, 0.2, 0.01),
                _pooled("A00002", 3, 0.3, 0.20),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(
        effects,
        "per_cancer",
        output_dir=tmp_path / "separate-coverage90",
        runner=fake,
    )
    main = next(row for row in result.summaries if row["unit_family"] == "panel")
    sensitivity = next(row for row in result.summaries if row["unit_family"] == "panel_coverage90")
    with (tmp_path / "separate-coverage90/groups.tsv").open(newline="", encoding="utf-8") as stream:
        groups = list(csv.DictReader(stream, delimiter="\t"))
    with (tmp_path / "separate-coverage90/meta_input.tsv").open(newline="", encoding="utf-8") as stream:
        meta_input = list(csv.DictReader(stream, delimiter="\t"))
    family_by_analysis = {row["analysis_id"]: row["unit_family"] for row in groups}

    assert {row["unit_family"] for row in groups} == {"panel", "panel_coverage90"}
    assert {family_by_analysis[row["analysis_id"]] for row in meta_input} == {
        "panel", "panel_coverage90"
    }
    assert main["q"] == pytest.approx(0.01)
    assert main["label"] == "standard"
    assert sensitivity["q"] == pytest.approx(0.20)
    assert sensitivity["label"] == "panel_coverage90_standard"
    assert sensitivity["sensitivity_label"] == "sensitivity only; does not support claims alone"


def test_targeted_subset_is_reported_per_study_without_pooling_or_fdr(tmp_path):
    effects = [
        {**_effect("targeted_subset", "HALLMARK_SYNTHETIC_SET", f"study_{index}"),
         "method_id": "CUSTOM_MEAN_TARGETED_SUBSET"}
        for index in range(3)
    ]

    result = _synthesize_synthetic(effects, "per_cancer", output_dir=tmp_path / "targeted-subset")

    assert len(result.summaries) == 3
    assert {row["status"] for row in result.summaries} == {"per_study_only"}
    assert {row["method_id"] for row in result.summaries} == {"CUSTOM_MEAN_TARGETED_SUBSET"}
    assert all(row["q"] is None for row in result.summaries)
    assert result.metadata["non_pooled_families"]["targeted_subset"] == "per-study only; no pooling or FDR"


def test_m5m6_gene_family_requires_k_of_three_for_pooling():
    effects = [_effect("m5m6_gene", "GENE_SYNTH_M5", f"study_{index}") for index in range(2)]
    groups, _ = synthesis_module._plan_groups(effects, "per_cancer")

    summary = synthesis_module._summary(
        groups[0], {"k": 2, "status": "not_pooled", "reason": "gene_pooling_requires_k>=3"}
    )

    assert groups[0]["min_k"] == 3
    assert summary["status"] == "not_pooled"
    assert summary["reason"] == "gene_pooling_requires_k>=3"


def test_fdr_scope_is_family_stratum_and_endpoint_family():
    from tools.a_meta.synthesis import _apply_fdr

    rows = [
        {"unit_family": "panel", "unit": "P1", "stratum_type": "cancer", "stratum": "melanoma",
         "drug_class_stratum": "ALL", "endpoint_family": "orr", "endpoint_definition_id": "ORR_A", "status": "pooled", "p": 0.01, "k": 3},
        {"unit_family": "panel", "unit": "P2", "stratum_type": "cancer", "stratum": "melanoma",
         "drug_class_stratum": "ALL", "endpoint_family": "orr", "endpoint_definition_id": "ORR_B", "status": "pooled", "p": 0.03, "k": 3},
        {"unit_family": "panel_coverage90", "unit": "P1", "stratum_type": "cancer", "stratum": "melanoma",
         "drug_class_stratum": "ALL", "endpoint_family": "orr", "endpoint_definition_id": "ORR_A", "status": "pooled", "p": 0.02, "k": 3},
        {"unit_family": "panel", "unit": "P1", "stratum_type": "drug_class", "stratum": "ANTI_PD_L1_AXIS",
         "drug_class_stratum": "ANTI_PD_L1_AXIS", "endpoint_family": "orr", "endpoint_definition_id": "ORR_A", "status": "pooled", "p": 0.001, "k": 3},
        {"unit_family": "panel", "unit": "P1", "stratum_type": "cancer", "stratum": "melanoma",
         "drug_class_stratum": "ALL", "endpoint_family": "clinical_benefit", "endpoint_definition_id": "CB_A", "status": "pooled", "p": 0.001, "k": 3},
        {"unit_family": "targeted_subset", "unit": "HALLMARK_SYNTHETIC_SET", "stratum_type": "cancer", "stratum": "melanoma",
         "drug_class_stratum": "ALL", "endpoint_family": "orr", "endpoint_definition_id": "ORR_A", "status": "pooled", "p": 0.0001, "k": 3},
    ]

    _apply_fdr(rows)

    assert rows[0]["q"] == pytest.approx(0.02)
    assert rows[1]["q"] == pytest.approx(0.03)
    assert rows[2]["q"] == pytest.approx(0.02)
    assert rows[3]["q"] == pytest.approx(0.001)
    assert rows[4]["q"] == pytest.approx(0.001)
    assert rows[5].get("q") is None


def test_low_k_flag_is_set_for_anti_ctla4_and_dual_class_strata(tmp_path):
    effects = [
        *[_effect("panel", "PANEL", f"ctla_{index}", drug="ANTI_CTLA4") for index in range(2)],
        *[_effect("panel", "PANEL", f"pd1_{index}", drug="ANTI_PD_L1_AXIS") for index in range(3)],
        *[_effect("panel", "PANEL", f"dual_{index}", drug="DUAL_PD1_CTLA4") for index in range(2)],
    ]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 2, 0.1, 0.04),
                _pooled("A00002", 3, 0.2, 0.01),
                _pooled("A00003", 2, 0.15, 0.03),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(effects, "per_drug_class", output_dir=tmp_path / "classes", runner=fake)

    ctla4 = next(row for row in result.summaries if row["drug_class_stratum"] == "ANTI_CTLA4")
    pd1 = next(row for row in result.summaries if row["drug_class_stratum"] == "ANTI_PD_L1_AXIS")
    dual = next(row for row in result.summaries if row["drug_class_stratum"] == "DUAL_PD1_CTLA4")
    assert ctla4["k"] == 2 and ctla4["label"] == "tentative_k2" and ctla4["low_k"] is True
    assert pd1["k"] == 3 and pd1["label"] == "standard" and pd1["low_k"] is False
    assert dual["k"] == 2 and dual["label"] == "tentative_k2" and dual["low_k"] is True


def test_subgroup_difference_is_not_tested_below_ten_studies(tmp_path):
    effects = [_effect("panel", "PANEL", f"study_{index}") for index in range(9)]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([_pooled("A00001", 9, 0.2, 0.1)]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(effects, "per_cancer", output_dir=tmp_path / "subgroup", runner=fake)

    assert result.subgroup_tests[0]["total_k"] == 9
    assert result.subgroup_tests[0]["status"] == "not_tested"
    assert result.subgroup_tests[0]["reason"] == "total_k<10"


def test_subgroup_difference_is_run_at_ten_studies(tmp_path):
    effects = [
        _effect("panel", "PANEL", f"study_{index}", cancer="melanoma" if index < 5 else "lung")
        for index in range(10)
    ]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 5, 0.2, 0.1),
                _pooled("A00002", 5, 0.3, 0.1),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\nT00001\t4\t0.05\ttested\t\n",
        }
    })

    result = _synthesize_synthetic(effects, "per_cancer", output_dir=tmp_path / "subgroup-ten", runner=fake)

    assert result.subgroup_tests[0]["total_k"] == 10
    assert result.subgroup_tests[0]["status"] == "tested"
    assert result.subgroup_tests[0]["F"] == pytest.approx(4.0)
    assert result.subgroup_tests[0]["p"] == pytest.approx(0.05)


def test_cancer_subgroup_uses_one_selected_patient_set_per_study(tmp_path):
    effects = [_effect("panel", "PANEL", f"single_{index}", cancer="melanoma") for index in range(7)]
    for index in range(3):
        study = f"multi_{index}"
        effects.extend([
            _effect("panel", "PANEL", study, cancer="melanoma", patient_set_id=f"{study}-melanoma"),
            _effect("panel", "PANEL", study, cancer="lung", patient_set_id=f"{study}-lung"),
            _effect(
                "panel", "PANEL", study, cancer="multi", patient_set_id=f"{study}-aggregate",
                cancer_components="melanoma,lung",
            ),
        ])
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 5, 0.2, 0.1),
                _pooled("A00002", 5, 0.3, 0.1),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\nT00001\t2\t0.15\ttested\t\n",
        }
    })

    result = _synthesize_synthetic(
        effects,
        "per_cancer",
        output_dir=tmp_path / "deduplicated",
        runner=fake,
    )
    subgroup_input = list(csv.DictReader(
        (tmp_path / "deduplicated/subgroup_input.tsv").open(newline="", encoding="utf-8"),
        delimiter="\t",
    ))

    assert len(subgroup_input) == 10
    assert len({row["study"] for row in subgroup_input}) == 10
    assert len({(row["study"], row["patient_set_id"]) for row in subgroup_input}) == 10
    assert len({row["patient_set_id"] for row in subgroup_input}) == 10
    assert result.subgroup_tests[0]["total_k"] == 10


def test_drug_class_and_subgroup_inputs_select_one_aggregate_or_component_per_study(tmp_path):
    effects = []
    for index in range(10):
        study = f"study_{index}"
        drug = "ANTI_PD_L1_AXIS" if index < 5 else "DUAL_PD1_CTLA4"
        if index == 0:
            effects.extend([
                _effect(
                    "panel", "PANEL", study, cancer="multi", drug=drug,
                    patient_set_id="aggregate-set", cancer_components="melanoma,lung",
                ),
                _effect(
                    "panel", "PANEL", study, cancer="melanoma", drug=drug,
                    patient_set_id="melanoma-component-set",
                ),
                _effect(
                    "panel", "PANEL", study, cancer="lung", drug=drug,
                    patient_set_id="lung-component-set",
                ),
            ])
        else:
            effects.append(_effect(
                "panel", "PANEL", study, cancer="melanoma" if index % 2 else "lung",
                drug=drug,
            ))
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 5, 0.2, 0.04),
                _pooled("A00002", 5, 0.3, 0.05),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\nT00001\t2\t0.15\ttested\t\n",
        }
    })

    _synthesize_synthetic(
        effects,
        "per_drug_class",
        output_dir=tmp_path / "overlap-selection",
        runner=fake,
    )

    meta_inputs = list(csv.DictReader(
        (tmp_path / "overlap-selection/meta_input.tsv").open(newline="", encoding="utf-8"),
        delimiter="\t",
    ))
    subgroup_inputs = list(csv.DictReader(
        (tmp_path / "overlap-selection/subgroup_input.tsv").open(newline="", encoding="utf-8"),
        delimiter="\t",
    ))
    assert len(meta_inputs) == 10
    assert len({row["study"] for row in meta_inputs}) == 10
    assert len(subgroup_inputs) == 10
    assert len({row["study"] for row in subgroup_inputs}) == 10
    assert next(row for row in meta_inputs if row["study"] == "study_0")["cancer"] == "multi"
    assert next(row for row in subgroup_inputs if row["study"] == "study_0")["patient_set_id"] == "aggregate-set"

    aggregate = effects[0]
    component = effects[1]
    assert aggregate["patient_set_id"] != component["patient_set_id"]
    with pytest.raises(ValueError, match="aggregate and overlapping cancer-component"):
        synthesis_module._assert_unique_patient_sets(
            [aggregate, component], "synthetic subgroup"
        )


def test_source_label_family_is_reported_per_study_and_never_pooled(tmp_path):
    effects = [
        _effect(
            "panel", "PANEL", f"source_{index}", endpoint="source_label",
            definition_id="SOURCE_LABEL_UNSPECIFIED",
            g=0.1 * (index + 1),
        )
        for index in range(3)
    ]
    non_estimable = _effect(
        "panel", "PANEL", "source_unknown", endpoint="source_label",
        definition_id="SOURCE_LABEL_UNSPECIFIED", g=None, se=None,
    )
    non_estimable.update(status="NA", reason="unknown=4", patient_set_id="empty-set")
    effects.append(non_estimable)

    result = _synthesize_synthetic(
        effects,
        "per_cancer",
        output_dir=tmp_path / "source-only",
    )

    assert len(result.summaries) == 4
    assert {row["label"] for row in result.summaries} == {"per_study_only"}
    assert {row["status"] for row in result.summaries} == {"per_study_only"}
    estimates = sorted((row["estimate"] for row in result.summaries if row["estimate"] is not None))
    assert estimates == pytest.approx([0.1, 0.2, 0.3])
    assert sum(row["estimate"] is None for row in result.summaries) == 1
    assert all(
        row["ci_lb"] is not None and row["ci_ub"] is not None
        for row in result.summaries if row["estimate"] is not None
    )
    assert all(row["q"] is None for row in result.summaries)
    assert result.subgroup_tests == []
    assert result.r_manifest is None


def test_endpoint_definition_ids_split_pools_and_bh_families(tmp_path):
    effects = [
        _effect(
            "panel", "PANEL", f"dcb_{index}", endpoint="clinical_benefit",
            definition_id="CB_DCB_NDB",
        )
        for index in range(3)
    ] + [
        _effect(
            "panel", "PANEL", f"pfs_{index}", endpoint="clinical_benefit",
            definition_id="CB_PFS_GT6M",
        )
        for index in range(3)
    ]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([
                _pooled("A00001", 3, 0.1, 0.01),
                _pooled("A00002", 3, 0.2, 0.20),
            ]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(
        effects,
        "per_cancer",
        output_dir=tmp_path / "definitions",
        runner=fake,
    )

    assert {row["endpoint_definition_id"] for row in result.summaries} == {
        "CB_DCB_NDB", "CB_PFS_GT6M",
    }
    assert {row["k"] for row in result.summaries} == {3}
    assert {row["q"] for row in result.summaries} == {0.02, 0.20}


def test_single_gene_effect_keeps_its_effect_and_interval(tmp_path):
    effects = [_effect("gene", "GENE_A", "one_gene_study", g=0.33, se=0.12)]
    fake = FakeR({
        "meta_rma.R": {
            "meta.tsv": _canned_meta([{
                "analysis_id": "A00001", "k": 1, "n_cancers": 1, "n_studies": 1,
                "estimate": 0.33, "se": 0.12, "ci_lb": 0.0948, "ci_ub": 0.5652,
                "status": "single_study", "reason": "one independent unit; no pooling",
            }]),
            "subgroups.tsv": "test_id\tF\tp\tstatus\treason\n",
        }
    })

    result = _synthesize_synthetic(
        effects,
        "per_cancer",
        output_dir=tmp_path / "single-gene",
        runner=fake,
    )
    gene = result.summaries[0]

    assert gene["label"] == "single_study"
    assert gene["estimate"] == pytest.approx(0.33)
    assert gene["se"] == pytest.approx(0.12)
    assert gene["ci_lb"] == pytest.approx(0.0948)
    assert gene["ci_ub"] == pytest.approx(0.5652)
    assert gene["q"] is None


def test_locked_final_test_is_refused_before_synthesis(tmp_path):
    with pytest.raises(ValueError, match="IMvigor210"):
        _synthesize_synthetic(
            [_effect("gene", "GENE_A", "IMvigor210")],
            "per_cancer",
            output_dir=tmp_path / "locked",
        )


def test_synthesis_requires_hash_matched_fixture_provenance_and_refuses_contradictions(tmp_path):
    rows = [_effect("panel", "PANEL", "synthetic_study")]
    with pytest.raises(ValueError, match="synthetic-fixture manifest"):
        synthesize(rows, "per_cancer")

    manifest = synthetic_effect_rows_manifest(rows, tmp_path / "fixture.json")
    rows[0]["g"] = 0.9
    with pytest.raises(ValueError, match="does not match the input hash"):
        synthesize(rows, "per_cancer", provenance_manifest=manifest)

    real_id_rows = [_effect("panel", "PANEL", "liu2019")]
    contradictory = synthetic_effect_rows_manifest(real_id_rows, tmp_path / "contradictory.json")
    with pytest.raises(ValueError, match="Synthetic provenance contradicts"):
        synthesize(
            real_id_rows,
            "per_cancer",
            allow_outcomes=True,
            provenance_manifest=contradictory,
        )


def test_synthesis_path_preflights_real_and_locked_manifests_before_reading_effects(tmp_path):
    effect_path = tmp_path / "effects.tsv"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "data_classification": "real",
        "cohort": "liu2019",
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Real-cohort synthesis is restricted"):
        synthesize(effect_path, "per_cancer")

    manifest_path.write_text(json.dumps({
        "data_classification": "real",
        "cohort": "IMvigor210",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="IMvigor210"):
        synthesize(effect_path, "per_cancer", allow_outcomes=True)

