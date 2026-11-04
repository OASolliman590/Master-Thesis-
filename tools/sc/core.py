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
    raw_expression: pd.DataFrame | None = None
    cell_ids_by_profile: dict[str, tuple[str, ...]] | None = None
    layer_gene_coverage: dict[str, tuple[str, ...]] | None = None
    raw_detection: pd.DataFrame | None = None


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
    layer_id: str | None = None,
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
    reason = np.where(
        n_cells < min_cells,
        "below_minimum_cells",
        np.where(total_umis < min_umis, "below_minimum_umis", ""),
    )
    matrix = _matrix_frame(pseudobulk.X, pseudobulk.var_names, profile_ids)
    raw_matrix = matrix.copy()
    matrix.loc[:, ~eligible] = np.nan

    clinical = pd.DataFrame(
        {
            "profile_id": profile_ids,
            "patient_id": donor_values,
            "donor_id": donor_values,
            "sample_id": (
                sample_metadata["sample_id"].astype("string").fillna("").to_numpy()
                if "sample_id" in sample_metadata
                else sample_metadata["sample"].astype("string").fillna("").to_numpy()
                if "sample" in sample_metadata
                else donor_values
            ),
            "compartment": compartment_values,
            "n_cells": n_cells,
            "total_umis": total_umis.astype(np.int64),
            "eligible": eligible,
            "status": status,
            "reason": reason,
        }
    )
    for column in metadata_cols:
        if column not in {donor_col, compartment_col}:
            clinical[column] = sample_metadata[column].astype("string").fillna("").to_numpy()
    clinical["library_size"] = total_umis.astype(np.int64)

    detection_matrix = pseudobulk.layers.get("psbulk_props")
    detection = None
    raw_detection = None
    if detection_matrix is not None:
        detection = _matrix_frame(detection_matrix, pseudobulk.var_names, profile_ids) * 100.0
        raw_detection = detection.copy()
        detection.loc[:, ~eligible] = np.nan
    cell_frame = pd.DataFrame(
        {
            "patient": working.obs[donor_col].astype(str).to_numpy(),
            "compartment": working.obs[compartment_col].astype(str).to_numpy(),
            "cell_id": working.obs_names.astype(str),
        }
    )
    cell_ids = {
        f"{patient}__{compartment}": tuple(frame["cell_id"].astype(str))
        for (patient, compartment), frame in cell_frame.groupby(
            ["patient", "compartment"], sort=False, observed=True
        )
    }
    layer_name = layer_id or count_layer
    return ProfileTable(
        matrix,
        clinical,
        detection,
        raw_expression=raw_matrix,
        cell_ids_by_profile=cell_ids,
        layer_gene_coverage={layer_name: tuple(map(str, raw_matrix.index))},
        raw_detection=raw_detection,
    )


def merge_layer_profiles(
    profiles: Sequence[ProfileTable],
    *,
    min_cells: int = MIN_CELLS,
    min_umis: int = MIN_UMIS,
) -> ProfileTable:
    """Sum disjoint layer cells per patient/specimen/compartment before thresholds."""
    if not profiles:
        raise ValueError("At least one layer profile table is required")
    if any(part.cell_ids_by_profile is None for part in profiles):
        raise ValueError("Layer merges require cell identities to verify disjoint inputs")
    layer_coverage: dict[str, tuple[str, ...]] = {}
    for part in profiles:
        for layer, genes in (part.layer_gene_coverage or {}).items():
            if layer in layer_coverage:
                raise ValueError("Layer identifiers must be unique during a profile merge")
            layer_coverage[layer] = tuple(map(str, genes))

    seen_cells: set[str] = set()
    profile_parts: dict[str, list[tuple[int, int]]] = {}
    raw_parts: list[pd.DataFrame] = []
    for part_index, part in enumerate(profiles):
        raw = part.raw_expression if part.raw_expression is not None else part.expression
        if raw.index.has_duplicates or raw.columns.has_duplicates:
            raise ValueError("Layer profile matrices must have unique genes and profile IDs")
        if "profile_id" not in part.clinical or part.clinical["profile_id"].astype(str).duplicated().any():
            raise ValueError("Layer clinical tables require unique profile IDs")
        raw_parts.append(raw)
        cell_map = part.cell_ids_by_profile or {}
        if set(map(str, part.expression.columns)) != set(map(str, cell_map)):
            raise ValueError("Cell identity coverage does not match layer profile columns")
        cell_counts = part.clinical.set_index(part.clinical["profile_id"].astype(str))["n_cells"].to_dict() \
            if "n_cells" in part.clinical else {}
        for profile_index, profile_id in enumerate(map(str, raw.columns)):
            cell_ids = tuple(map(str, cell_map[profile_id]))
            if len(cell_ids) != len(set(cell_ids)):
                raise ValueError("A layer contains duplicate cell identities")
            if cell_counts and len(cell_ids) != int(cell_counts[profile_id]):
                raise ValueError("Cell identity counts do not match layer pseudobulk counts")
            overlap = seen_cells.intersection(cell_ids)
            if overlap:
                raise ValueError("Layer inputs contain duplicate cell identities")
            seen_cells.update(cell_ids)
            profile_parts.setdefault(profile_id, []).append((part_index, profile_index))

    clinical_by_profile: dict[str, list[pd.Series]] = {}
    for part_index, part in enumerate(profiles):
        for _, row in part.clinical.iterrows():
            clinical_by_profile.setdefault(str(row["profile_id"]), []).append((part_index, row))
    if set(clinical_by_profile) != set(profile_parts):
        raise ValueError("Layer clinical profiles do not align with expression profiles")

    genes = list(dict.fromkeys(str(gene) for raw in raw_parts for gene in raw.index))
    profile_ids = list(profile_parts)
    raw_expression = pd.DataFrame(np.nan, index=genes, columns=profile_ids, dtype=float)
    detection = pd.DataFrame(np.nan, index=genes, columns=profile_ids, dtype=float)
    merged_clinical: list[dict] = []
    identity_columns = (
        "patient_id", "donor_id", "sample_id", "sample", "compartment", "cohort", "study",
        "cancer", "treatment", "response_metric", "response", "outcome_label", "endpoint_family",
    )

    for profile_id in profile_ids:
        sources = profile_parts[profile_id]
        rows = clinical_by_profile[profile_id]
        base = rows[0][1].to_dict()
        for column in identity_columns:
            values = {str(row.get(column, "")) for _, row in rows if column in row.index}
            if len(values) > 1:
                raise ValueError(f"Layer metadata disagree for patient profile field {column}")
        n_cells = sum(int(row.get("n_cells", 0)) for _, row in rows)
        total_umis = sum(float(row.get("total_umis", 0)) for _, row in rows)
        invalid = any(str(row.get("status", "")) == "invalid_raw_counts" for _, row in rows)
        status = (
            "below_cell_threshold" if n_cells < min_cells
            else "invalid_raw_counts" if invalid
            else "below_umi_threshold" if total_umis < min_umis
            else "eligible"
        )
        base.update(
            n_cells=n_cells,
            total_umis=total_umis,
            library_size=total_umis,
            eligible=status == "eligible",
            status=status,
            reason={
                "below_cell_threshold": "below_minimum_cells",
                "below_umi_threshold": "below_minimum_umis",
                "invalid_raw_counts": "non_integer_or_invalid_raw_counts",
                "eligible": "",
            }[status],
            count_layer=";".join(dict.fromkeys(str(row.get("count_layer", "")) for _, row in rows)),
        )
        for gene in genes:
            values = []
            detected_counts = []
            measured = True
            for part_index, profile_index in sources:
                raw = raw_parts[part_index]
                if gene not in raw.index:
                    measured = False
                    break
                value = raw.iloc[raw.index.get_loc(gene), profile_index]
                if pd.isna(value):
                    measured = False
                    break
                values.append(float(value))
                part = profiles[part_index]
                source_detection = part.raw_detection if part.raw_detection is not None else part.detection
                if source_detection is not None and gene in source_detection.index:
                    detected_pct = source_detection.iloc[source_detection.index.get_loc(gene), profile_index]
                    if pd.isna(detected_pct):
                        measured = False
                        break
                    source_n = int(next(row for index, row in rows if index == part_index).get("n_cells", 0))
                    detected_counts.append(float(detected_pct) * source_n / 100.0)
                else:
                    detected_counts = []
            if measured:
                raw_expression.at[gene, profile_id] = sum(values)
                if detected_counts and len(detected_counts) == len(sources) and n_cells:
                    detection.at[gene, profile_id] = sum(detected_counts) * 100.0 / n_cells
        merged_clinical.append(base)

    clinical = pd.DataFrame.from_records(merged_clinical)
    expression = raw_expression.copy()
    ineligible = ~clinical.set_index("profile_id").loc[profile_ids, "eligible"].astype(bool)
    expression.loc[:, ineligible.to_numpy()] = np.nan
    return ProfileTable(
        expression=expression,
        clinical=clinical,
        detection=detection,
        raw_expression=raw_expression,
        cell_ids_by_profile={
            profile_id: tuple(
                cell_id
                for part_index, profile_index in sources
                for cell_id in profiles[part_index].cell_ids_by_profile[profile_id]
            )
            for profile_id, sources in profile_parts.items()
        },
        layer_gene_coverage=layer_coverage,
    )


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
        if valid["patient_id"].astype(str).duplicated().any():
            raise ValueError("Expression summaries require one profile per patient and compartment")
        donor_count = valid["patient_id"].nunique()
        for gene in gene_order:
            record = {
                "gene": gene,
                "compartment": compartment,
                "study": study,
                "n_donors": int(donor_count),
                "n_gene_donors": 0,
                "median_log2_cpm_plus1": np.nan,
                "q1_log2_cpm_plus1": np.nan,
                "q3_log2_cpm_plus1": np.nan,
                "median_cpm": np.nan,
                "median_percent_cells_detected": np.nan,
                "status": "shown",
            }
            if gene not in profiles.expression.index:
                record["status"] = "missing_from_layer"
            else:
                values = []
                percentages = []
                measured_donors = set()
                for row in valid.itertuples(index=False):
                    profile_id = getattr(row, "profile_id")
                    count = profiles.expression.at[gene, profile_id]
                    if pd.isna(count):
                        continue
                    measured_donors.add(str(getattr(row, "patient_id")))
                    cpm = float(count) / float(getattr(row, "library_size")) * 1_000_000.0
                    values.append((cpm, np.log2(cpm + 1.0)))
                    if detection is not None and gene in detection.index and profile_id in detection:
                        cell_pct = detection.at[gene, profile_id]
                        if not pd.isna(cell_pct):
                            percentages.append(float(cell_pct))
                record["n_gene_donors"] = len(measured_donors)
                if len(measured_donors) < min_donors:
                    record["status"] = "insufficient_gene_donors"
                elif values:
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
        elif subset["status"].ne("shown").any() or subset["median_cpm"].isna().any():
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
