from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.cli import main
from tools.sc.sc3 import (
    guard_sc3,
    hedges_g,
    metric_family,
    outcome_fields,
    group_profiles,
)


def test_sc3_sample_size_is_the_number_of_pseudobulk_patients():
    anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
    from scipy import sparse
    from tools.sc.core import aggregate_anndata

    patients = [(arm, f"synthetic_{arm}_{index}") for arm in ("R", "NR") for index in range(3)]
    obs_rows = []
    count_rows = []
    for arm, patient in patients:
        for cell_index in range(20):
            obs_rows.append({
                "patient_id": patient,
                "compartment": "T/NK",
                "cohort": "invented_study",
                "endpoint_family": "RECIST",
                "outcome_label": arm,
            })
            count_rows.append([250, 250])
    adata = anndata.AnnData(
        X=sparse.csr_matrix(count_rows),
        obs=pd.DataFrame(obs_rows, index=[f"synthetic_cell_{i}" for i in range(len(obs_rows))]),
        var=pd.DataFrame(index=["GENE_A", "GENE_B"]),
    )
    adata.layers["counts"] = adata.X.copy()
    profiles = aggregate_anndata(
        adata, donor_col="patient_id", compartment_col="compartment",
        metadata_cols=("cohort", "endpoint_family", "outcome_label"), min_cells=15, min_umis=5_000,
    )

    groups, refusals = group_profiles(profiles.clinical)

    assert not refusals
    group = groups[("invented_study", "T/NK", "RECIST")]
    assert group.n_r == 3
    assert group.n_nr == 3
    assert len(group.profile_ids) == 6
    assert adata.n_obs == 120


def test_response_metric_families_stay_separate_and_expansion_is_not_response():
    clinical = pd.DataFrame(
        [
            {
                "cohort": "invented_study",
                "profile_id": f"synthetic_profile_{family}_{arm}_{index}",
                "patient_id": f"synthetic_{family}_{arm}_{index}",
                "compartment": "T/NK",
                "endpoint_family": family,
                "outcome_label": arm,
                "eligible": True,
            }
            for family in ("RECIST", "expansion")
            for arm in ("R", "NR")
            for index in range(3)
        ]
    )

    groups, refusals = group_profiles(clinical)
    expansion = outcome_fields("T-cell expansion", "R")

    assert set(groups) == {
        ("invented_study", "T/NK", "RECIST"),
        ("invented_study", "T/NK", "expansion"),
    }
    assert not refusals
    assert expansion["endpoint_family"] == "expansion"
    assert expansion["response"] is None
    assert expansion["outcome_label"] == "R"
    assert metric_family("Pathology+RECIST") == "pathology"
    assert metric_family("T-cell expansion") == "expansion"


def test_sc3_refuses_a_cohort_with_fewer_than_three_patients_in_an_arm():
    clinical = pd.DataFrame(
        [
            {
                "cohort": "invented_small_study",
                "profile_id": f"synthetic_profile_{arm}_{index}",
                "patient_id": f"synthetic_{arm}_{index}",
                "compartment": "Myeloid",
                "endpoint_family": "pathology",
                "outcome_label": arm,
                "eligible": True,
            }
            for arm, count in (("R", 2), ("NR", 3))
            for index in range(count)
        ]
    )

    groups, refusals = group_profiles(clinical)

    assert not groups
    assert refusals[0]["reason"] == "fewer_than_three_patients_per_arm"
    assert refusals[0]["n_R"] == 2
    assert refusals[0]["n_NR"] == 3


def test_sc3_requires_explicit_permission_for_real_atlas_outcomes():
    try:
        guard_sc3(is_synthetic=False, allow_outcomes=False)
    except PermissionError as error:
        assert "--allow-outcomes" in str(error)
    else:
        raise AssertionError("real-atlas SC-3 ran without --allow-outcomes")


def test_sc3_cli_refuses_real_atlas_before_reading_data(tmp_path, capsys):
    result = main(["sc3", "--atlas", "lin2026", "--results", str(tmp_path)])

    assert result == 2
    assert "requires --allow-outcomes" in capsys.readouterr().err


def test_hedges_g_matches_a_hand_calculated_two_group_example():
    result = hedges_g([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])

    assert result["n_R"] == 3
    assert result["n_NR"] == 3
    assert result["mean_R"] == 2.0
    assert result["mean_NR"] == 3.0
    assert result["g"] == -0.8
