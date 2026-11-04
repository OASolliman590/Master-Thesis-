from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
from scipy import sparse

from tools.sc.core import ProfileTable, aggregate_anndata, merge_layer_profiles


def _tiny_adata():
    # Three invented donors: one eligible profile, one below the UMI floor,
    # and one below the cell floor.
    matrix = np.vstack(
        [
            np.tile([[250, 250]], (15, 1)),
            np.tile([[20, 40]], (15, 1)),
            np.tile([[400, 100]], (14, 1)),
        ]
    )
    obs = pd.DataFrame(
        {
            "donor_id": ["synthetic_a"] * 15 + ["synthetic_b"] * 15 + ["synthetic_c"] * 14,
            "compartment": ["T/NK"] * 44,
            "cohort": ["invented_study"] * 44,
        },
        index=[f"synthetic_cell_{i}" for i in range(44)],
    )
    adata = anndata.AnnData(
        X=sparse.csr_matrix(matrix),
        obs=obs,
        var=pd.DataFrame(index=["GENE_A", "GENE_B"]),
    )
    adata.layers["counts"] = adata.X.copy()
    return adata


def test_pseudobulk_sums_raw_counts_and_marks_ineligible_profiles_missing():
    result = aggregate_anndata(
        _tiny_adata(),
        donor_col="donor_id",
        compartment_col="compartment",
        metadata_cols=("cohort",),
        min_cells=15,
        min_umis=5_000,
    )

    eligible = result.clinical.set_index("donor_id").loc["synthetic_a", "profile_id"]
    low_umis = result.clinical.set_index("donor_id").loc["synthetic_b", "profile_id"]
    low_cells = result.clinical.set_index("donor_id").loc["synthetic_c", "profile_id"]
    assert result.expression.loc["GENE_A", eligible] == 3_750
    assert result.expression.loc["GENE_B", eligible] == 3_750
    assert result.clinical.set_index("profile_id").loc[eligible, "n_cells"] == 15
    assert result.clinical.set_index("profile_id").loc[eligible, "total_umis"] == 7_500
    assert result.clinical.set_index("profile_id").loc[eligible, "eligible"]
    assert result.expression[low_umis].isna().all()
    assert result.expression[low_cells].isna().all()
    assert result.clinical.set_index("profile_id").loc[low_umis, "status"] == "below_umi_threshold"
    assert result.clinical.set_index("profile_id").loc[low_cells, "status"] == "below_cell_threshold"


def test_layer_merge_preserves_unmeasured_genes_as_missing():
    left = ProfileTable(
        expression=pd.DataFrame({"profile_left": [11, 3]}, index=["GENE_A", "GENE_B"]),
        clinical=pd.DataFrame({"profile_id": ["profile_left"], "layer": ["layer_left"]}),
    )
    right = ProfileTable(
        expression=pd.DataFrame({"profile_right": [5, 7]}, index=["GENE_B", "GENE_C"]),
        clinical=pd.DataFrame({"profile_id": ["profile_right"], "layer": ["layer_right"]}),
    )

    merged = merge_layer_profiles((left, right))

    assert merged.expression.loc["GENE_A", "profile_left"] == 11
    assert pd.isna(merged.expression.loc["GENE_C", "profile_left"])
    assert pd.isna(merged.expression.loc["GENE_A", "profile_right"])
    assert merged.expression.loc["GENE_C", "profile_right"] == 7
