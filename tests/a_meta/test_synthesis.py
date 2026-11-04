from __future__ import annotations

import pytest

from tools.a_meta.synthesis import synthesize
from tools.r_bridge import FakeR


def _effect(unit_family, unit, study, *, cancer="melanoma", drug="ALL", endpoint="orr", g=0.2, se=0.1):
    return {
        "unit_family": unit_family,
        "unit": unit,
        "study": study,
        "cancer": cancer,
        "drug_class_stratum": drug,
        "endpoint_family": endpoint,
        "n_R": 4,
        "n_NR": 4,
        "g": g,
        "se": se,
        "status": "ok",
        "reason": "",
    }


def _canned_meta(rows):
    columns = (
        "analysis_id", "k", "estimate", "se", "ci_lb", "ci_ub", "tau2", "I2",
        "Q", "p", "fixed_estimate", "fixed_ci_lb", "fixed_ci_ub", "status", "reason",
    )
    return "\t".join(columns) + "\n" + "".join(
        "\t".join(str(row.get(column, "NA")) for column in columns) + "\n"
        for row in rows
    )


def _pooled(analysis_id, k, estimate, p):
    return {
        "analysis_id": analysis_id,
        "k": k,
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

    result = synthesize(effects, "per_cancer", output_dir=tmp_path / "synthesis", runner=fake)

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
    assert gene_b["estimate"] is None
    assert panel_a_orr["q"] == pytest.approx(0.08)
    assert panel_b["q"] == pytest.approx(0.20)
    assert panel_a_benefit["q"] == pytest.approx(0.03)
    assert panel_c["label"] == "single_study"
    assert panel_c["estimate"] == pytest.approx(0.25)
    assert panel_c["q"] is None


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

    result = synthesize(effects, "per_drug_class", output_dir=tmp_path / "classes", runner=fake)

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

    result = synthesize(effects, "per_cancer", output_dir=tmp_path / "subgroup", runner=fake)

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

    result = synthesize(effects, "per_cancer", output_dir=tmp_path / "subgroup-ten", runner=fake)

    assert result.subgroup_tests[0]["total_k"] == 10
    assert result.subgroup_tests[0]["status"] == "tested"
    assert result.subgroup_tests[0]["F"] == pytest.approx(4.0)
    assert result.subgroup_tests[0]["p"] == pytest.approx(0.05)


def test_locked_final_test_is_refused_before_synthesis():
    with pytest.raises(ValueError, match="locked"):
        synthesize([_effect("gene", "GENE_A", "IMvigor210")], "per_cancer")

