from __future__ import annotations

import pytest

anndata = pytest.importorskip("anndata", reason="run with envs/sc-analysis Python")
import numpy as np
import pandas as pd
from scipy import sparse

from tools.sc.core import ProfileTable, aggregate_anndata, expression_summary, merge_layer_profiles


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
        clinical=pd.DataFrame({"profile_id": ["profile_left"], "patient_id": ["synthetic_left"],
            "sample_id": ["sample_left"], "compartment": ["T/NK"], "n_cells": [15],
            "total_umis": [14], "library_size": [14], "eligible": [True],
            "status": ["eligible"], "count_layer": ["layer_left"]}),
        raw_expression=pd.DataFrame({"profile_left": [11, 3]}, index=["GENE_A", "GENE_B"]),
        cell_ids_by_profile={"profile_left": tuple(f"synthetic_cell_left_{i}" for i in range(15))},
        layer_gene_coverage={"layer_left": ("GENE_A", "GENE_B")},
    )
    right = ProfileTable(
        expression=pd.DataFrame({"profile_right": [5, 7]}, index=["GENE_B", "GENE_C"]),
        clinical=pd.DataFrame({"profile_id": ["profile_right"], "patient_id": ["synthetic_right"],
            "sample_id": ["sample_right"], "compartment": ["T/NK"], "n_cells": [15],
            "total_umis": [12], "library_size": [12], "eligible": [True],
            "status": ["eligible"], "count_layer": ["layer_right"]}),
        raw_expression=pd.DataFrame({"profile_right": [5, 7]}, index=["GENE_B", "GENE_C"]),
        cell_ids_by_profile={"profile_right": tuple(f"synthetic_cell_right_{i}" for i in range(15))},
        layer_gene_coverage={"layer_right": ("GENE_B", "GENE_C")},
    )

    merged = merge_layer_profiles((left, right), min_cells=0, min_umis=0)

    assert merged.expression.loc["GENE_A", "profile_left"] == 11
    assert pd.isna(merged.expression.loc["GENE_C", "profile_left"])
    assert pd.isna(merged.expression.loc["GENE_A", "profile_right"])
    assert merged.expression.loc["GENE_C", "profile_right"] == 7
    assert merged.layer_gene_coverage == {
        "layer_left": ("GENE_A", "GENE_B"), "layer_right": ("GENE_B", "GENE_C")
    }


def test_layer_merge_combines_disjoint_patient_specimen_cells_before_thresholds():
    def layer(layer_id, genes, cell_prefix):
        values = np.full((8, len(genes)), 350, dtype=np.int32)
        obs = pd.DataFrame(
            {"donor": ["synthetic_patient"] * 8, "compartment": ["T/NK"] * 8,
             "cohort": ["invented_study"] * 8, "sample_id": ["synthetic_specimen"] * 8},
            index=[f"{cell_prefix}_{index}" for index in range(8)],
        )
        adata = anndata.AnnData(X=sparse.csr_matrix(values), obs=obs, var=pd.DataFrame(index=genes))
        adata.layers["counts"] = adata.X.copy()
        return aggregate_anndata(
            adata, donor_col="donor", compartment_col="compartment", metadata_cols=("cohort", "sample_id"),
            min_cells=15, min_umis=5_000, layer_id=layer_id,
        )

    merged = merge_layer_profiles((
        layer("layer_left", ["GENE_A", "GENE_B"], "synthetic_cells_left"),
        layer("layer_right", ["GENE_B", "GENE_C"], "synthetic_cells_right"),
    ))

    profile_id = "synthetic_patient__T/NK"
    clinical = merged.clinical.set_index("profile_id").loc[profile_id]
    assert clinical["n_cells"] == 16
    assert clinical["total_umis"] == 11_200
    assert clinical["eligible"]
    assert merged.expression.at["GENE_B", profile_id] == 5_600
    assert pd.isna(merged.expression.at["GENE_A", profile_id])
    assert pd.isna(merged.expression.at["GENE_C", profile_id])
    assert len(merged.cell_ids_by_profile[profile_id]) == 16


def test_layer_merge_rejects_reused_cell_identity():
    common = {"profile_id": ["synthetic_patient__T/NK"], "patient_id": ["synthetic_patient"],
        "sample_id": ["synthetic_specimen"], "compartment": ["T/NK"], "n_cells": [15],
        "total_umis": [5_100], "library_size": [5_100], "eligible": [True],
        "status": ["eligible"], "count_layer": ["layer"]}
    first = ProfileTable(
        pd.DataFrame({"synthetic_patient__T/NK": [5_100]}, index=["GENE_A"]),
        pd.DataFrame(common),
        raw_expression=pd.DataFrame({"synthetic_patient__T/NK": [5_100]}, index=["GENE_A"]),
        cell_ids_by_profile={"synthetic_patient__T/NK": tuple(f"synthetic_cell_shared_{i}" for i in range(15))},
        layer_gene_coverage={"layer_a": ("GENE_A",)},
    )
    second = ProfileTable(
        pd.DataFrame({"synthetic_patient__T/NK": [5_100]}, index=["GENE_A"]),
        pd.DataFrame({**common, "count_layer": ["layer"]}),
        raw_expression=pd.DataFrame({"synthetic_patient__T/NK": [5_100]}, index=["GENE_A"]),
        cell_ids_by_profile={"synthetic_patient__T/NK": tuple(f"synthetic_cell_shared_{i}" for i in range(15))},
        layer_gene_coverage={"layer_b": ("GENE_A",)},
    )

    with pytest.raises(ValueError, match="duplicate cell identities"):
        merge_layer_profiles((first, second))


def test_expression_summary_applies_donor_floor_per_gene_and_reports_support():
    profiles = ProfileTable(
        expression=pd.DataFrame(
            {f"profile_{index}": [float(index), float(index * 2)] for index in range(5)},
            index=["GENE_MEASURED", "GENE_SPARSE"],
        ),
        clinical=pd.DataFrame({
            "profile_id": [f"profile_{index}" for index in range(5)],
            "patient_id": [f"synthetic_patient_{index}" for index in range(5)],
            "compartment": ["T/NK"] * 5, "study": ["invented_study"] * 5,
            "eligible": [True] * 5, "library_size": [10_000] * 5,
        }),
    )
    profiles.expression.loc["GENE_SPARSE", "profile_4"] = np.nan

    summary = expression_summary(profiles, study_col="study", genes=("GENE_MEASURED", "GENE_SPARSE"))
    measured = summary.set_index("gene").loc["GENE_MEASURED"]
    sparse = summary.set_index("gene").loc["GENE_SPARSE"]

    assert measured["n_gene_donors"] == 5
    assert measured["status"] == "shown"
    assert sparse["n_donors"] == 5
    assert sparse["n_gene_donors"] == 4
    assert sparse["status"] == "insufficient_gene_donors"
    assert pd.isna(sparse["median_log2_cpm_plus1"])
