from __future__ import annotations

from types import SimpleNamespace
import math

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.cli import main
from tools.sc.core import panel_definitions
from tools.sc.sc3 import (
    _sc3_effects,
    group_profiles,
    outcome_fields,
    metric_family,
    write_sc3_synthetic_manifest,
)


def _clinical(families=("RECIST",), arms=(3, 3), cohort="invented_study"):
    rows = []
    for metric in families:
        family = metric_family(metric)
        for arm, count in zip(("R", "NR"), arms, strict=True):
            for index in range(count):
                patient = f"synthetic_{metric}_{arm}_{index}"
                rows.append({
                    "cohort": cohort,
                    "profile_id": f"synthetic_profile_{metric}_{arm}_{index}",
                    "patient_id": patient,
                    "sample_id": f"synthetic_specimen_{metric}_{arm}_{index}",
                    "compartment": "T/NK",
                    "response_metric": metric,
                    "endpoint_family": family,
                    "outcome_label": arm,
                    "response": None if family == "expansion" else arm,
                    "eligible": True,
                    "library_size": 10_000,
                    "cancer": "lung",
                    "treatment": "aPD1",
                    "fraction_cells_total": 0.1,
                })
    return pd.DataFrame(rows)


def _manifest(clinical, tmp_path, name="synthetic_sc3_manifest.json"):
    path = tmp_path / name
    write_sc3_synthetic_manifest(clinical, path)
    return path


def test_sc3_sample_size_is_the_number_of_pseudobulk_patients(tmp_path):
    anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
    from scipy import sparse
    from tools.sc.core import aggregate_anndata

    patients = [(arm, f"synthetic_{arm}_{index}") for arm in ("R", "NR") for index in range(3)]
    obs_rows = []
    count_rows = []
    for arm, patient in patients:
        for _ in range(20):
            obs_rows.append({
                "patient_id": patient,
                "sample_id": f"synthetic_specimen_{patient}",
                "compartment": "T/NK",
                "cohort": "invented_study",
                "response_metric": "RECIST",
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
        metadata_cols=("sample_id", "cohort", "response_metric", "endpoint_family", "outcome_label"),
        min_cells=15, min_umis=5_000,
    )
    manifest = _manifest(profiles.clinical, tmp_path)

    groups, refusals = group_profiles(profiles.clinical, provenance_manifest=manifest)

    assert not refusals
    group = groups[("invented_study", "T/NK", "RECIST")]
    assert group.n_r == 3
    assert group.n_nr == 3
    assert len(group.profile_ids) == 6
    assert adata.n_obs == 120


def test_response_metric_families_stay_separate_and_expansion_is_not_response(tmp_path):
    clinical = _clinical(("RECIST", "T-cell expansion"))
    manifest = _manifest(clinical, tmp_path)

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)
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

    mislabeled = clinical[clinical["endpoint_family"].eq("expansion")].copy()
    mislabeled["response"] = "R"
    bad_manifest = _manifest(mislabeled, tmp_path, "mislabeled_expansion.json")
    with pytest.raises(ValueError, match="cannot be stored as clinical response"):
        group_profiles(mislabeled, provenance_manifest=bad_manifest)


def test_sc3_refuses_a_cohort_with_fewer_than_three_distinct_patients_per_arm(tmp_path):
    clinical = _clinical(("pathology±RECIST",), arms=(2, 3), cohort="invented_small_study")
    manifest = _manifest(clinical, tmp_path)

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)

    assert not groups
    assert refusals[0]["reason"] == "fewer_than_three_patients_per_arm"
    assert refusals[0]["n_R"] == 2
    assert refusals[0]["n_NR"] == 3


def test_public_sc3_analysis_requires_real_authorization_or_synthetic_provenance():
    with pytest.raises(PermissionError, match="verified synthetic manifest"):
        group_profiles(_clinical())


def test_sc3_refuses_a_synthetic_manifest_for_a_real_atlas_cohort(tmp_path):
    clinical = _clinical(cohort="PCa_Hawley")
    manifest = _manifest(clinical, tmp_path)

    with pytest.raises(PermissionError, match="explicit allow_outcomes"):
        group_profiles(clinical, provenance_manifest=manifest)


def test_sc3_cli_refuses_real_atlas_before_reading_data(tmp_path, capsys):
    result = main(["sc3", "--atlas", "lin2026", "--results", str(tmp_path)])

    assert result == 2
    assert "requires --allow-outcomes" in capsys.readouterr().err


def test_sc3_effects_reuse_a_meta_hedges_g_and_restrict_drug_strata(tmp_path):
    from tools.a_meta.effects import _effect_row

    clinical = _clinical()
    clinical["treatment"] = ["aPD1", "aPD1", "aPD1+aCTLA4", "aPD1", "aPD1", "aPD1+aCTLA4"]
    gene = panel_definitions()["M5_CHECKPOINT_CANDIDATES"][0]
    values = [100, 200, 300, 20, 40, 60]
    profile_ids = clinical["profile_id"].astype(str).tolist()
    clinical["profile_id"] = profile_ids
    clinical["library_size"] = 10_000
    manifest = _manifest(clinical, tmp_path)
    expression = pd.DataFrame([values], index=[gene], columns=profile_ids)

    effects = _sc3_effects(clinical, expression, provenance_manifest=manifest)
    target = effects.loc[effects["unit"].eq(f"sc3::T/NK::RECIST::{gene}")]
    gene_rows = target.set_index("drug_class_stratum")

    assert set(gene_rows.index) == {"ALL", "ANTI_PD_L1_AXIS", "DUAL_PD1_CTLA4"}
    assert gene_rows.loc["ALL", "n_R"] == 3
    assert gene_rows.loc["ALL", "n_NR"] == 3
    assert gene_rows.loc["ANTI_PD_L1_AXIS", "n_R"] == 2
    assert gene_rows.loc["ANTI_PD_L1_AXIS", "n_NR"] == 2
    assert gene_rows.loc["DUAL_PD1_CTLA4", "n_R"] == 1
    assert gene_rows.loc["DUAL_PD1_CTLA4", "n_NR"] == 1
    assert gene_rows.loc["ALL", "endpoint_family"] == "orr"
    assert gene_rows.loc["ALL", "endpoint_definition_id"] == "ORR"
    assert gene_rows.loc["ALL", "compartment"] == "T/NK"

    normalized = [math.log2(value / 10_000 * 1_000_000 + 1) for value in values]
    labels = [1, 1, 1, 0, 0, 0]
    view = SimpleNamespace(metadata=SimpleNamespace(cohort_id="invented_study"))
    clinical_rows = [
        {"patient_id": row.patient_id, "sample_id": row.sample_id}
        for row in clinical.itertuples(index=False)
    ]
    expected = _effect_row(
        view=view, unit_family="gene", unit=f"sc3::T/NK::RECIST::{gene}", cancer="lung", stratum="ALL",
        endpoint_family="orr", endpoint_definition_id="ORR", labels=labels, values=normalized,
        patient_indices=list(range(6)), excluded={}, coverage=None, clinical_rows=clinical_rows,
        cancer_components=["lung"],
    )
    assert gene_rows.loc["ALL", "g"] == pytest.approx(expected["g"])
    assert gene_rows.loc["ALL", "se"] == pytest.approx(expected["se"])
    assert gene_rows.loc["ANTI_PD_L1_AXIS", "mean_R"] == pytest.approx(sum(normalized[:2]) / 2)


def test_a_meta_synthesis_accepts_synthetic_sc3_effect_contract(tmp_path):
    from tools.a_meta.provenance import write_synthetic_fixture_manifest
    from tools.a_meta.synthesis import _read_effects, synthesize
    from tools.a_meta.provenance import effect_rows_payload

    clinical = _clinical(("pathology±RECIST",))
    gene = panel_definitions()["M5_CHECKPOINT_CANDIDATES"][0]
    expression = pd.DataFrame(
        [[100, 120, 140, 20, 40, 60]],
        index=[gene],
        columns=clinical["profile_id"].astype(str),
    )
    clinical["library_size"] = 10_000
    profile_manifest = _manifest(clinical, tmp_path)
    effects = _sc3_effects(clinical, expression, provenance_manifest=profile_manifest)
    rows = effects.to_dict(orient="records")
    normalized_rows = _read_effects(rows)
    manifest = tmp_path / "effect_rows_manifest.json"
    write_synthetic_fixture_manifest(
        manifest, kind="effect_rows", payload=effect_rows_payload(normalized_rows), cohort_ids=["invented_study"]
    )

    result = synthesize(rows, "per_cancer", provenance_manifest=manifest)

    assert result.summaries
    assert {row["endpoint_family"] for row in result.summaries} == {"source_label"}
    assert {row["endpoint_definition_id"] for row in result.summaries} == {"SOURCE_LABEL_UNSPECIFIED"}
