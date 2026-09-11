from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AssayDetection:
    assay_type: str
    confidence: float
    evidence: str
    n_genes: int
    n_samples: int


def _evidence_from_matrix(df: pd.DataFrame) -> dict[str, float | bool]:
    values = df.to_numpy(dtype=float, copy=False)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "has_negative": False,
            "min": np.nan,
            "max": np.nan,
            "median": np.nan,
            "integer_frac": 0.0,
            "colsum_median": np.nan,
            "colsum_cv": np.nan,
        }

    sample = finite if finite.size <= 200000 else np.random.choice(finite, 200000, replace=False)
    int_frac = float(np.mean(np.isclose(sample, np.round(sample), atol=1e-6)))
    has_negative = bool((finite < 0).any())
    col_sums = np.nansum(np.where(np.isfinite(values), values, np.nan), axis=0)
    col_sums = col_sums[np.isfinite(col_sums)]
    colsum_median = float(np.median(col_sums)) if col_sums.size else np.nan
    colsum_cv = (
        float(np.std(col_sums) / np.mean(col_sums))
        if col_sums.size and not np.isclose(np.mean(col_sums), 0.0)
        else np.nan
    )
    return {
        "has_negative": has_negative,
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "median": float(np.median(finite)),
        "integer_frac": int_frac,
        "colsum_median": colsum_median,
        "colsum_cv": colsum_cv,
    }


def _format_evidence(evidence: dict[str, float | bool]) -> str:
    return (
        f"integer_frac={evidence['integer_frac']:.3f};"
        f"has_negative={str(bool(evidence['has_negative'])).lower()};"
        f"min={evidence['min']:.3g};max={evidence['max']:.3g};"
        f"median={evidence['median']:.3g};"
        f"colsum_median={evidence['colsum_median']:.4g};"
        f"colsum_cv={evidence['colsum_cv']:.3f}"
    )


def _probe_matrix_evidence(df: pd.DataFrame) -> tuple[bool, str]:
    index_sample = [str(value).upper() for value in list(df.index[: min(len(df.index), 1000)])]
    illumina_frac = (
        float(np.mean([value.startswith("ILMN_") for value in index_sample]))
        if index_sample
        else 0.0
    )
    detection_pvalue_cols = sum(1 for col in df.columns if "detection p" in str(col).lower())
    probe_matrix = (illumina_frac >= 0.25 and detection_pvalue_cols > 0) or illumina_frac >= 0.75
    evidence = (
        f"illumina_probe_id_fraction={illumina_frac:.3f};"
        f"detection_pvalue_columns={detection_pvalue_cols}"
    )
    return probe_matrix, evidence


def classify_expression_matrix(
    df: pd.DataFrame | None,
    *,
    data_processing_text: str = "",
) -> AssayDetection:
    if df is None or df.empty:
        return AssayDetection(
            assay_type="unreadable",
            confidence=0.0,
            evidence="unreadable_or_empty_matrix",
            n_genes=0,
            n_samples=0,
        )

    n_genes, n_samples = int(df.shape[0]), int(df.shape[1])
    ev = _evidence_from_matrix(df)
    has_negative = bool(ev["has_negative"])
    vmin = float(ev["min"])
    vmax = float(ev["max"])
    vmed = float(ev["median"])
    int_frac = float(ev["integer_frac"])
    colsum_median = float(ev["colsum_median"])
    colsum_cv = float(ev["colsum_cv"])
    evidence = _format_evidence(ev)
    dp = (data_processing_text or "").lower()
    is_probe_matrix, probe_evidence = _probe_matrix_evidence(df)

    if is_probe_matrix:
        return AssayDetection(
            "microarray_probe_matrix",
            0.98,
            f"{probe_evidence};{evidence}",
            n_genes,
            n_samples,
        )

    if np.isfinite(vmin) and np.isfinite(vmax) and vmin >= 0.0 and vmax <= 1.0 and n_genes >= 100000:
        return AssayDetection("methylation_beta", 0.99, evidence, n_genes, n_samples)

    if has_negative:
        if vmin >= -30.0 and vmax <= 30.0:
            return AssayDetection("rlog_vst", 0.90, evidence, n_genes, n_samples)
        return AssayDetection("microarray_intensity", 0.85, evidence, n_genes, n_samples)

    if np.isfinite(colsum_median) and 0.9e6 <= colsum_median <= 1.1e6 and vmin >= 0.0:
        return AssayDetection("tpm", 0.88, evidence, n_genes, n_samples)

    if int_frac >= 0.98 and vmin >= 0.0:
        if np.isfinite(colsum_cv) and colsum_cv <= 0.01:
            return AssayDetection("normalized_other", 0.80, evidence, n_genes, n_samples)
        return AssayDetection("raw_counts", min(0.98, 0.65 + (int_frac * 0.33)), evidence, n_genes, n_samples)

    if 0.50 <= int_frac < 0.98 and vmin >= 0.0:
        if np.isfinite(colsum_cv) and colsum_cv <= 0.01:
            return AssayDetection("normalized_other", 0.72, evidence, n_genes, n_samples)
        return AssayDetection("raw_counts_suspect", 0.60, evidence, n_genes, n_samples)

    if np.isfinite(colsum_cv) and colsum_cv <= 0.01:
        return AssayDetection("normalized_other", 0.78, evidence, n_genes, n_samples)

    if vmax < 25.0 and vmed < 20.0:
        return AssayDetection("log_normalized", 0.82, evidence, n_genes, n_samples)

    if "fpkm" in dp or "rpkm" in dp:
        return AssayDetection("fpkm", 0.75, evidence, n_genes, n_samples)
    if "tpm" in dp:
        return AssayDetection("tpm", 0.75, evidence, n_genes, n_samples)

    return AssayDetection("normalized_other", 0.65, evidence, n_genes, n_samples)
