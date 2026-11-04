from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
from scipy import sparse

from tools.sc.prostate import aggregate_profiles, _map_compartments


def _tiny_prostate_adata():
    rows = []
    for donor, sample_type, major, minor in (
        ("synthetic_epithelial", "cancer", "Epithelial", "Basal"),
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
        var=pd.DataFrame(index=["GENE_A", "GENE_B"]),
    )
    data.layers["counts"] = data.X.copy()
    return data


def test_prostate_mapping_splits_basal_from_luminal_epithelial_cells():
    adata = _tiny_prostate_adata()

    _map_compartments(adata)

    assert adata.obs["compartment"].iloc[0] == "basal epithelial"
    assert adata.obs["compartment"].iloc[30] == "luminal/malignant epithelial"


def test_prostate_pseudobulk_uses_cancer_tissue_and_patient_compartments():
    result = aggregate_profiles(_tiny_prostate_adata())

    assert set(result.clinical["patient_id"]) == {"synthetic_epithelial", "synthetic_immune"}
    assert set(result.clinical["compartment"]) == {"basal epithelial", "T/NK"}
    assert result.clinical["n_cells"].tolist() == [15, 15]
    assert (result.clinical["total_umis"] == 7_500).all()
