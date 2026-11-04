from __future__ import annotations

import pytest

anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
import numpy as np
import pandas as pd
from scipy import sparse

from tools.sc.core import ProfileTable, panel_definitions
from tools.sc.prostate import aggregate_profiles, _map_compartments, compartment_table, qc_summary


def _tiny_prostate_adata():
    rows = []
    for donor, sample_type, major, minor in (
        ("synthetic_epithelial", "cancer", "Epithelial", "Basal"),
        ("synthetic_epithelial", "cancer", "Unassigned", "Unassigned"),
        ("synthetic_immune", "cancer", "T-cells", "CD8_T"),
        ("synthetic_benign", "adj_benign", "Epithelial", "Luminal"),
    ):
        rows.extend(
            {"donor_id": donor, "type": sample_type, "celltype_major_v2": major, "celltype_minor_v2": minor}
            for _ in range(15)
        )
    obs = pd.DataFrame(rows, index=[f"synthetic_cell_{i}" for i in range(len(rows))])
    matrix = np.tile([[250, 250]], (len(obs), 1))
    data = anndata.AnnData(
        X=sparse.csr_matrix(matrix),
        obs=obs,
        var=pd.DataFrame({"gene_name": ["GENE_A", "GENE_B"]}, index=["ENSG_SYNTH_A", "ENSG_SYNTH_B"]),
    )
    data.layers["counts"] = data.X.copy()
    data.X = data.X.astype(np.float32)
    data.X.data = np.log1p(data.X.data)
    return data


def test_prostate_mapping_splits_basal_from_luminal_epithelial_cells():
    adata = _tiny_prostate_adata()

    _map_compartments(adata)

    assert adata.obs["compartment"].iloc[0] == "basal epithelial"
    assert adata.obs["compartment"].iloc[45] == "luminal/malignant epithelial"


def test_prostate_qc_uses_raw_counts_layer_when_x_is_log_normalized():
    summary = qc_summary(_tiny_prostate_adata()).set_index("metric")

    assert summary.loc["umis_per_cell", "median"] == 500
    assert summary.loc["genes_per_cell", "median"] == 2


def test_prostate_pseudobulk_uses_cancer_tissue_and_patient_compartments():
    result = aggregate_profiles(_tiny_prostate_adata())

    assert set(result.clinical["patient_id"]) == {"synthetic_epithelial", "synthetic_immune"}
    assert set(result.clinical["compartment"]) == {"basal epithelial", "T/NK"}
    assert result.clinical["n_cells"].tolist() == [15, 15]
    assert (result.clinical["total_umis"] == 7_500).all()
    assert result.clinical.set_index("compartment").loc["basal epithelial", "fraction_cells_total"] == 0.5


def test_prostate_panel_summaries_map_symbols_to_stable_feature_ids():
    gene = panel_definitions()["P_ANTIGEN_PRESENTATION"][0]
    profile_ids = [f"synthetic_profile_{index}" for index in range(5)]
    clinical = pd.DataFrame({
        "profile_id": profile_ids,
        "patient_id": [f"synthetic_patient_{index}" for index in range(5)],
        "compartment": ["T/NK"] * 5,
        "study": ["invented_study"] * 5,
        "eligible": [True] * 5,
        "library_size": [1_000] * 5,
    })
    profiles = ProfileTable(
        expression=pd.DataFrame({profile_id: [10] for profile_id in profile_ids}, index=["ENSG_SYNTH"]),
        clinical=clinical,
        detection=pd.DataFrame({profile_id: [20.0] for profile_id in profile_ids}, index=["ENSG_SYNTH"]),
        gene_symbols=pd.Series([gene], index=["ENSG_SYNTH"]),
    )

    summary = compartment_table(profiles)
    row = summary.set_index("gene").loc[gene]

    assert row["status"] == "shown"
    assert row["n_donors"] == 5
    assert row["median_percent_cells_detected"] == 20.0
