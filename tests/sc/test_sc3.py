from __future__ import annotations

import math
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.cli import main
from tools.sc.core import panel_definitions
from tools.sc.sc3 import (
    _sc3_effects,
    authorize_sc3,
    guard_sc3,
    group_profiles,
    outcome_fields,
    metric_family,
    write_sc3_synthetic_manifest,
    write_sc3_r_synthetic_manifest,
)
from tools.sc.presentation import HALLMARK_IFNG, SC1_PANEL_IDS, panel_definitions_for_sc1


def _clinical(families=("RECIST",), arms=(3, 3), cohort="invented_study"):
    rows = []
    for metric in families:
        family = metric_family(metric)
        for arm, count in zip(("R", "NR"), arms, strict=True):
            for index in range(count):
                patient = f"synthetic_{metric}_{arm}_{index}"
                rows.append({
                    "cohort": cohort,
                    "source_family": f"{cohort}_source",
                    "profile_id": f"synthetic_profile_{metric}_{arm}_{index}",
                    "patient_id": patient,
                    "sample_id": f"synthetic_specimen_{metric}_{arm}_{index}",
                    "compartment": "T/NK",
                    "response_metric": metric,
                    "endpoint_family": family,
                    "outcome_label": arm,
                    "response": None if family == "expansion" else arm,
                    "eligible": True,
                    "baseline": True,
                    "n_cells": 20,
                    "total_umis": 10_000,
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
                "source_family": "invented_source",
                "response_metric": "RECIST",
                "endpoint_family": "RECIST",
                "outcome_label": arm,
                    "baseline": True,
                    "treatment": "aPD1",
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
        metadata_cols=("sample_id", "cohort", "response_metric", "endpoint_family", "outcome_label", "baseline", "treatment"),
        min_cells=15, min_umis=5_000,
    )
    profiles.clinical["source_family"] = "invented_source"
    profiles.clinical["n_cells"] = 20
    profiles.clinical["total_umis"] = 10_000
    profiles.clinical["library_size"] = 10_000
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
    assert metric_family("Pathology+RECIST") is None
    assert metric_family("T-cell expansion") == "expansion"

    mislabeled = clinical[clinical["endpoint_family"].eq("expansion")].copy()
    mislabeled["response"] = "R"
    bad_manifest = _manifest(mislabeled, tmp_path, "mislabeled_expansion.json")
    with pytest.raises(ValueError, match="cannot be stored as clinical response"):
        group_profiles(mislabeled, provenance_manifest=bad_manifest)


def test_sc3_reports_ambiguous_metric_compatibility_instead_of_using_declared_family(tmp_path):
    clinical = _clinical(("Pathology+RECIST",))
    clinical["endpoint_family"] = "pathology"
    manifest = _manifest(clinical, tmp_path, "ambiguous_metric_manifest.json")

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)

    assert not groups
    assert refusals[0]["reason"] == "metric_compatibility_requires_decision"


def test_sc3_refuses_a_cohort_with_fewer_than_three_distinct_patients_per_arm(tmp_path):
    clinical = _clinical(("RECIST",), arms=(2, 3), cohort="invented_small_study")
    manifest = _manifest(clinical, tmp_path)

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)

    assert not groups
    assert refusals[0]["reason"] == "fewer_than_three_patients_per_arm"
    assert refusals[0]["n_R"] == 2
    assert refusals[0]["n_NR"] == 3


def test_sc3_groups_only_baseline_ici_profiles(tmp_path):
    clinical = _clinical()
    clinical.loc[0, "baseline"] = False
    clinical.loc[3, "treatment"] = "chemotherapy"
    manifest = _manifest(clinical, tmp_path)

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)

    assert not groups
    assert refusals[0]["reason"] == "fewer_than_three_patients_per_arm"
    assert refusals[0]["n_R"] == 2
    assert refusals[0]["n_NR"] == 2


def test_sc3_excludes_non_ici_combinations_and_rechecks_profile_floors(tmp_path):
    clinical = _clinical()
    extra = clinical.iloc[[0, 3]].copy()
    extra["profile_id"] = extra["profile_id"].astype(str) + "_combo"
    extra["patient_id"] = extra["patient_id"].astype(str) + "_combo"
    extra["sample_id"] = extra["sample_id"].astype(str) + "_combo"
    extra["treatment"] = "aPD1+chemotherapy"
    clinical = pd.concat([clinical, extra], ignore_index=True)
    small = clinical[clinical["treatment"].eq("aPD1")].copy()
    small.loc[small["outcome_label"].eq("R").idxmax(), "n_cells"] = 14
    manifest = _manifest(clinical, tmp_path)

    groups, refusals = group_profiles(clinical, provenance_manifest=manifest)
    small_manifest = _manifest(small, tmp_path, "small_floor_manifest.json")
    small_groups, small_refusals = group_profiles(small, provenance_manifest=small_manifest)

    assert groups[("invented_study", "T/NK", "RECIST")].n_r == 3
    assert groups[("invented_study", "T/NK", "RECIST")].n_nr == 3
    assert not refusals
    assert not small_groups
    assert small_refusals[0]["n_R"] == 2
    assert small_refusals[0]["n_NR"] == 3


def test_sc3_rejects_reordered_duplicate_source_with_stable_identities(tmp_path):
    first = _clinical(cohort="invented_source_A")
    second = first.iloc[::-1].copy()
    second["cohort"] = "invented_source_B"
    second["source_family"] = "invented_source_B_family"
    duplicate = pd.concat([first, second], ignore_index=True)
    manifest = _manifest(duplicate, tmp_path, "duplicate_source_manifest.json")

    with pytest.raises(ValueError, match="stable patient/specimen identities"):
        group_profiles(duplicate, provenance_manifest=manifest)


def test_sc3_refuses_a_specimen_assigned_to_two_patient_profiles(tmp_path):
    clinical = _clinical()
    clinical.loc[1, "sample_id"] = clinical.loc[0, "sample_id"]
    manifest = _manifest(clinical, tmp_path)

    with pytest.raises(ValueError, match="cannot belong to more than one patient"):
        group_profiles(clinical, provenance_manifest=manifest)


def test_public_sc3_analysis_requires_real_authorization_or_synthetic_provenance():
    with pytest.raises(PermissionError, match="verified synthetic manifest"):
        group_profiles(_clinical())


def test_sc3_refuses_a_synthetic_manifest_for_a_real_atlas_cohort(tmp_path):
    clinical = _clinical(cohort="PCa_Hawley")
    manifest = _manifest(clinical, tmp_path)

    with pytest.raises(PermissionError, match="known real cohort"):
        group_profiles(clinical, provenance_manifest=manifest)


def test_sc3_provenance_writers_refuse_protected_destinations_before_io(tmp_path, monkeypatch):
    from tools.a_meta import provenance
    from tools.sc import sc3

    clinical = _clinical()
    clinical_path = tmp_path / "invented_clinical.tsv"
    counts_path = tmp_path / "invented_counts.tsv"
    clinical.to_csv(clinical_path, sep="\t", index=False)
    pd.DataFrame([[1] * len(clinical)], index=["GENE_A"], columns=clinical["profile_id"]).to_csv(
        counts_path, sep="\t", index_label="gene",
    )
    protected_parent = tmp_path / "invented" / "IMvigor_210"
    alias_parent = tmp_path / "invented" / "safe_alias"
    alias_parent.parent.mkdir()
    alias_parent.symlink_to(protected_parent, target_is_directory=True)

    def forbidden_access(*_args, **_kwargs):
        pytest.fail("SC-3 touched a protected provenance sentinel")

    monkeypatch.setattr(provenance, "write_synthetic_fixture_manifest", forbidden_access)
    monkeypatch.setattr(sc3, "_read_sc3_identity", forbidden_access)
    monkeypatch.setattr(sc3, "_input_sha256", forbidden_access)
    monkeypatch.setattr(Path, "open", forbidden_access)
    monkeypatch.setattr(Path, "write_text", forbidden_access)
    monkeypatch.setattr(Path, "mkdir", forbidden_access)

    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_synthetic_manifest(
            clinical,
            tmp_path / "invented" / "IMvigor_210" / "fixture_manifest.json",
        )
    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_r_synthetic_manifest(
            counts_path,
            clinical_path,
            tmp_path / "invented" / "ingestion_packet.json" / "fixture_manifest.json",
        )
    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_synthetic_manifest(
            clinical,
            alias_parent / "fixture_manifest.json",
        )
    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_r_synthetic_manifest(
            counts_path,
            clinical_path,
            alias_parent / "fixture_r_manifest.json",
        )
    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_synthetic_manifest(
            clinical,
            alias_parent / "fixture_manifest.json",
        )
    with pytest.raises(ValueError, match="forbidden protected paths"):
        write_sc3_r_synthetic_manifest(
            counts_path,
            clinical_path,
            alias_parent / "fixture_r_manifest.json",
        )
    assert not (tmp_path / "invented" / "IMvigor_210").exists()
    assert not (tmp_path / "invented" / "ingestion_packet.json").exists()


def test_sc3_real_outcome_route_stays_closed_even_for_known_cohorts():
    clinical = _clinical(cohort="PCa_Hawley")

    with pytest.raises(PermissionError, match="known real cohort"):
        authorize_sc3(clinical)

    with pytest.raises(PermissionError, match="not released"):
        guard_sc3(is_synthetic=False, allow_outcomes=False)


def test_sc3_cli_refuses_real_atlas_before_reading_data(tmp_path, capsys):
    result = main(["sc3", "--atlas", "lin2026", "--results", str(tmp_path)])

    assert result == 2
    assert "not released" in capsys.readouterr().err


def test_sc3_effects_reuse_a_meta_hedges_g_and_restrict_drug_strata(tmp_path):
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
    response = normalized[:3]
    nonresponse = normalized[3:]
    mean_response = sum(response) / len(response)
    mean_nonresponse = sum(nonresponse) / len(nonresponse)
    variance_response = sum((value - mean_response) ** 2 for value in response) / (len(response) - 1)
    variance_nonresponse = sum((value - mean_nonresponse) ** 2 for value in nonresponse) / (len(nonresponse) - 1)
    pooled_sd = math.sqrt(((len(response) - 1) * variance_response +
                           (len(nonresponse) - 1) * variance_nonresponse) /
                          (len(response) + len(nonresponse) - 2))
    degrees = len(response) + len(nonresponse) - 2
    correction = math.exp(
        math.lgamma(degrees / 2) - 0.5 * math.log(degrees / 2) - math.lgamma((degrees - 1) / 2)
    )
    expected_g = correction * (mean_response - mean_nonresponse) / pooled_sd
    expected_se = math.sqrt(
        (len(response) + len(nonresponse)) / (len(response) * len(nonresponse))
        + expected_g ** 2 / (2 * (len(response) + len(nonresponse)))
    )
    assert gene_rows.loc["ALL", "g"] == pytest.approx(expected_g)
    assert gene_rows.loc["ALL", "se"] == pytest.approx(expected_se)
    assert gene_rows.loc["ANTI_PD_L1_AXIS", "mean_R"] == pytest.approx(sum(normalized[:2]) / 2)
    assert gene_rows.loc["ANTI_PD_L1_AXIS", "status"] == "NA"
    assert pd.isna(gene_rows.loc["ANTI_PD_L1_AXIS", "g"])


def test_sc3_effects_use_the_signed_eleven_panels_and_keep_m5m6_gene_family(tmp_path):
    clinical = _clinical(("RECIST", "T-cell expansion"))
    myeloid = clinical.copy()
    myeloid["profile_id"] = myeloid["profile_id"].astype(str) + "_myeloid"
    myeloid["compartment"] = "myeloid"
    clinical = pd.concat([clinical, myeloid], ignore_index=True)
    clinical["library_size"] = 10_000
    manifest = _manifest(clinical, tmp_path)
    definitions = panel_definitions_for_sc1()
    genes = sorted({gene for members in definitions.values() for gene in members})
    profile_ids = clinical["profile_id"].astype(str).tolist()
    expression = pd.DataFrame(
        [[100, 200, 300, 20, 40, 60] * 4 for _ in genes],
        index=genes,
        columns=profile_ids,
    )

    effects = _sc3_effects(clinical, expression, provenance_manifest=manifest)
    panel_rows = effects[effects["unit_family"].eq("panel")]
    panel_ids = panel_rows["unit"].str.rsplit("::", n=1).str[-1]
    gene = definitions["M5_CHECKPOINT_CANDIDATES"][0]
    gene_row = effects[effects["unit"].eq(f"sc3::T/NK::RECIST::{gene}")].iloc[0]
    dimensions = set(effects["unit"].str.split("::").str[:3].map(tuple))

    assert set(panel_ids) == set(SC1_PANEL_IDS)
    assert set(panel_rows["method_id"]) == {f"CUSTOM_MEAN_{panel}" for panel in SC1_PANEL_IDS}
    assert gene_row["unit_family"] == "m5m6_gene"
    assert gene_row["method_id"] == "GENE_STUDY_SCALE"
    assert gene_row["m5m6_gene_flag"] == 1
    assert "CYT_FROZEN_UNOFFSET" not in set(panel_ids)
    assert "APM_WANG_18" not in set(panel_ids)
    assert dimensions == {
        ("sc3", "T/NK", "RECIST"),
        ("sc3", "T/NK", "expansion"),
        ("sc3", "myeloid", "RECIST"),
        ("sc3", "myeloid", "expansion"),
    }


def test_sc3_expression_alias_preserves_effect_support_and_rejects_collisions(tmp_path):
    clinical = _clinical()
    manifest = _manifest(clinical, tmp_path)
    genes = sorted({gene for members in panel_definitions_for_sc1().values() for gene in members})
    values = [100, 200, 300, 20, 40, 60]
    expression = pd.DataFrame([values for _ in genes], index=genes, columns=clinical["profile_id"].astype(str))
    canonical = _sc3_effects(clinical, expression, provenance_manifest=manifest)
    alias_expression = expression.drop(index="DDX58").rename(index={"RIGI": "DDX58"})
    if "RIGI" not in expression.index:
        alias_expression = expression.drop(index="DDX58").copy()
        alias_expression.loc["RIGI"] = values
    aliased = _sc3_effects(clinical, alias_expression, provenance_manifest=manifest)
    panel = f"sc3::T/NK::RECIST::{HALLMARK_IFNG}"
    canonical_row = canonical.loc[canonical["unit"].eq(panel) & canonical["drug_class_stratum"].eq("ALL")].iloc[0]
    alias_row = aliased.loc[aliased["unit"].eq(panel) & aliased["drug_class_stratum"].eq("ALL")].iloc[0]
    assert alias_row["g"] == pytest.approx(canonical_row["g"])
    assert alias_row["n_R"] == canonical_row["n_R"]
    assert alias_row["n_NR"] == canonical_row["n_NR"]

    collision = pd.concat([alias_expression, expression.loc[["DDX58"]]])
    with pytest.raises(ValueError, match="collide after frozen gene alias"):
        _sc3_effects(clinical, collision, provenance_manifest=manifest)


def test_a_meta_synthesis_accepts_synthetic_sc3_effect_contract(tmp_path):
    from tools.a_meta.provenance import write_synthetic_fixture_manifest
    from tools.a_meta.synthesis import _read_effects, synthesize
    from tools.a_meta.provenance import effect_rows_payload

    clinical = _clinical(("pathology",))
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
    assert {row["status"] for row in result.summaries} == {"per_study_only"}


def test_sc3_feature_missingness_rechecks_three_per_arm_floor(tmp_path):
    clinical = _clinical()
    gene = panel_definitions()["M5_CHECKPOINT_CANDIDATES"][0]
    profile_ids = clinical["profile_id"].astype(str).tolist()
    manifest = _manifest(clinical, tmp_path)
    expression = pd.DataFrame([[100, 200, None, 20, 40, 60]], index=[gene], columns=profile_ids)

    effects = _sc3_effects(clinical, expression, provenance_manifest=manifest)
    row = effects.loc[
        effects["unit"].eq(f"sc3::T/NK::RECIST::{gene}")
        & effects["drug_class_stratum"].eq("ALL")
    ].iloc[0]

    assert row["n_R"] == 2
    assert row["n_NR"] == 3
    assert row["status"] == "NA"
    assert pd.isna(row["g"])
    assert "n_R<3" in row["reason"]
