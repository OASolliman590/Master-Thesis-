"""Outcome-free aggregation and expression summaries for cell-count data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .runtime import configure_runtime


MIN_CELLS = 15
MIN_UMIS = 5_000
MIN_DONORS_TO_SHOW = 5
DETECTION_LIMIT_CPM = 50.0

SINGLE_CELL_PANEL_IDS = (
    "P_ANTIGEN_PRESENTATION",
    "AYERS_GEP_18",
    "HOPE_18",
    "M0_EXTRA_ANTIGEN_PRESENTATION",
    "M1_MOBILITY",
    "M2_CYTOTOXICITY",
    "M3_VIRAL_MIMICRY",
    "M4_EXCLUSION",
    "CYT_FROZEN_UNOFFSET",
    "CYT_ROONEY_OFFSET_REFERENCE",
    "APM_WANG_18",
)


@dataclass
class ProfileTable:
    """Patient-level count profiles, metadata, and cell-detection proportions."""

    expression: pd.DataFrame
    clinical: pd.DataFrame
    detection: pd.DataFrame | None = None
    gene_symbols: pd.Series | None = None


def _matrix_frame(matrix, genes: Sequence[str], profile_ids: Sequence[str]) -> pd.DataFrame:
    if hasattr(matrix, "toarray"):
        matrix = matrix.toarray()
    return pd.DataFrame(np.asarray(matrix).T, index=list(genes), columns=list(profile_ids))


def aggregate_anndata(
    adata,
    *,
    donor_col: str,
    compartment_col: str,
    metadata_cols: Iterable[str] = (),
    count_layer: str = "counts",
    min_cells: int = MIN_CELLS,
    min_umis: int = MIN_UMIS,
) -> ProfileTable:
    """Sum raw UMIs per donor and compartment with decoupler's pseudobulk API.

    Ineligible profiles stay in the clinical table with a reason and have NA in
    every expression row. Gene absence must be expressed by a different layer
    table and combined with :func:`merge_layer_profiles`.
    """
    configure_runtime()
    import decoupler as dc

    if count_layer not in adata.layers:
        raise ValueError(f"AnnData is missing its raw count layer {count_layer!r}")
    required = {donor_col, compartment_col, *metadata_cols}
    missing = required - set(adata.obs.columns)
    if missing:
        raise ValueError(f"AnnData metadata is missing columns: {sorted(missing)}")
    selected = adata.obs[compartment_col].notna().to_numpy(copy=True)
    selected &= adata.obs[donor_col].notna().to_numpy(copy=True)
    working = adata[selected].copy()
    if not working.n_obs:
        return ProfileTable(pd.DataFrame(index=adata.var_names), pd.DataFrame())

    pseudobulk = dc.pp.pseudobulk(
        working,
        sample_col=donor_col,
        groups_col=compartment_col,
        layer=count_layer,
        mode="sum",
        skip_checks=False,
        bsize=250_000,
        verbose=False,
    )
    pseudobulk = pseudobulk[pseudobulk.obs["psbulk_cells"].astype(int) > 0].copy()
    sample_metadata = pseudobulk.obs
    donor_values = sample_metadata[donor_col].astype(str).to_numpy()
    compartment_values = sample_metadata[compartment_col].astype(str).to_numpy()
    profile_ids = [
        f"{donor}__{compartment}"
        for donor, compartment in zip(donor_values, compartment_values, strict=True)
    ]
    if len(set(profile_ids)) != len(profile_ids):
        raise ValueError("Pseudobulk profile IDs are not unique")

    n_cells = sample_metadata["psbulk_cells"].astype(int).to_numpy()
    total_umis = sample_metadata["psbulk_counts"].astype(float).to_numpy()
    status = np.where(
        n_cells < min_cells,
        "below_cell_threshold",
        np.where(total_umis < min_umis, "below_umi_threshold", "eligible"),
    )
    eligible = status == "eligible"
    matrix = _matrix_frame(pseudobulk.X, pseudobulk.var_names, profile_ids)
    matrix.loc[:, ~eligible] = np.nan

    clinical = pd.DataFrame(
        {
            "profile_id": profile_ids,
            "patient_id": donor_values,
            "donor_id": donor_values,
            "compartment": compartment_values,
            "n_cells": n_cells,
            "total_umis": total_umis.astype(np.int64),
            "eligible": eligible,
            "status": status,
        }
    )
    for column in metadata_cols:
        if column not in {donor_col, compartment_col}:
            clinical[column] = sample_metadata[column].astype("string").fillna("").to_numpy()
    clinical["library_size"] = total_umis.astype(np.int64)

    detection_matrix = pseudobulk.layers.get("psbulk_props")
    detection = None
    if detection_matrix is not None:
        detection = _matrix_frame(detection_matrix, pseudobulk.var_names, profile_ids) * 100.0
        detection.loc[:, ~eligible] = np.nan
    return ProfileTable(matrix, clinical, detection)


def merge_layer_profiles(profiles: Sequence[ProfileTable]) -> ProfileTable:
    """Join layer-specific profile tables while keeping absent genes NA."""
    if not profiles:
        raise ValueError("At least one layer profile table is required")
    all_ids = [str(pid) for part in profiles for pid in part.expression.columns]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("A patient-compartment profile occurs in more than one count layer")
    expression = pd.concat([part.expression for part in profiles], axis=1, sort=False)
    clinical = pd.concat([part.clinical for part in profiles], ignore_index=True, sort=False)
    available_detection = [part.detection for part in profiles if part.detection is not None]
    detection = (
        pd.concat(available_detection, axis=1, sort=False)
        if available_detection
        else None
    )
    if detection is not None:
        detection = detection.reindex(index=expression.index, columns=expression.columns)
    return ProfileTable(expression, clinical, detection)


def panel_definitions() -> dict[str, tuple[str, ...]]:
    """Load the eleven locked single-cell panels and the separate M5/M6 genes."""
    from tools.a_scoring.core import panel_definitions as load_panels

    ids = (*SINGLE_CELL_PANEL_IDS, "M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
    return load_panels(ids)


def expression_summary(
    profiles: ProfileTable,
    *,
    study_col: str,
    genes: Iterable[str],
    min_donors: int = MIN_DONORS_TO_SHOW,
    detection_limit_cpm: float = DETECTION_LIMIT_CPM,
) -> pd.DataFrame:
    """Compute donor-median log2(CPM+1) and percent detected per study/compartment."""
    if profiles.clinical.empty:
        return pd.DataFrame()
    clinical = profiles.clinical.copy()
    if study_col not in clinical:
        clinical[study_col] = "study"
    if "library_size" not in clinical:
        clinical["library_size"] = clinical["total_umis"]
    if "eligible" not in clinical:
        clinical["eligible"] = True
    detection = profiles.detection
    gene_order = tuple(dict.fromkeys(map(str, genes)))
    records: list[dict] = []

    for (study, compartment), frame in clinical.groupby([study_col, "compartment"], dropna=False):
        valid = frame[frame["eligible"].astype(bool) & (frame["library_size"] > 0)]
        donor_count = valid["patient_id"].nunique()
        for gene in gene_order:
            record = {
                "gene": gene,
                "compartment": compartment,
                "study": study,
                "n_donors": int(donor_count),
                "median_log2_cpm_plus1": np.nan,
                "q1_log2_cpm_plus1": np.nan,
                "q3_log2_cpm_plus1": np.nan,
                "median_cpm": np.nan,
                "median_percent_cells_detected": np.nan,
                "status": "shown",
            }
            if gene not in profiles.expression.index:
                record["status"] = "missing_from_layer"
            elif donor_count < min_donors:
                record["status"] = "insufficient_donors"
            else:
                values = []
                percentages = []
                for row in valid.itertuples(index=False):
                    profile_id = getattr(row, "profile_id")
                    count = profiles.expression.at[gene, profile_id]
                    if pd.isna(count):
                        continue
                    cpm = float(count) / float(getattr(row, "library_size")) * 1_000_000.0
                    values.append((cpm, np.log2(cpm + 1.0)))
                    if detection is not None and gene in detection.index and profile_id in detection:
                        cell_pct = detection.at[gene, profile_id]
                        if not pd.isna(cell_pct):
                            percentages.append(float(cell_pct))
                if values:
                    cpms = np.asarray([item[0] for item in values], dtype=float)
                    log_values = np.asarray([item[1] for item in values], dtype=float)
                    record["median_cpm"] = float(np.median(cpms))
                    record["median_log2_cpm_plus1"] = float(np.median(log_values))
                    record["q1_log2_cpm_plus1"] = float(np.quantile(log_values, 0.25))
                    record["q3_log2_cpm_plus1"] = float(np.quantile(log_values, 0.75))
                    record["median_percent_cells_detected"] = (
                        float(np.median(percentages)) if percentages else np.nan
                    )
                else:
                    record["status"] = "no_eligible_measurements"
            records.append(record)

    result = pd.DataFrame.from_records(records)
    if result.empty:
        return result
    for _, index in result.groupby(["study", "gene"], dropna=False).groups.items():
        subset = result.loc[index]
        if subset["status"].eq("missing_from_layer").any():
            tag = "not_assessed"
        elif subset["status"].eq("insufficient_donors").any() or subset["median_cpm"].isna().any():
            tag = "not_assessed"
        elif (subset["median_cpm"] < detection_limit_cpm).all():
            tag = "below_scRNA_detection_limit"
        else:
            tag = "measured_at_or_above_detection_limit"
        result.loc[index, "detection_limit_tag"] = tag
    return result


def gene_set_table(definitions: dict[str, Sequence[str]]) -> pd.DataFrame:
    """Flatten locked memberships for source adapters and manifests."""
    return pd.DataFrame(
        [(panel, gene) for panel, members in definitions.items() for gene in members],
        columns=["panel_id", "gene"],
    )


def as_output_matrix(path: Path, expression: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    expression.to_csv(path, sep="\t", index_label="gene", na_rep="NA")
