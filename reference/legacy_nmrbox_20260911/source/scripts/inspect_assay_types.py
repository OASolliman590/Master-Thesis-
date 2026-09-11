#!/usr/bin/env python3
"""Round-2 Step-1 empirical assay inspector.

Opens each cohort's primary expression matrix (via the pipeline's own resolver)
and computes file-derived evidence to verify the source_type_selected label.
Prototype of the spec-010 assay-type detector — its agreement/disagreement with
the manifest is the X1 evidence.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from pipeline.common.expression import (  # noqa: E402
    resolve_primary_expression_path,
    load_expression_matrix,
)

DOWNLOADS_ROOT = Path(
    "/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_geo_merged30"
)
EXPR_MANIFEST = REPO / "results/geo_tables/geo_tables_summary.tsv"


def classify(df: pd.DataFrame) -> tuple[str, float, str]:
    """Prototype detector. Returns (assay_type, confidence, evidence)."""
    vals = df.to_numpy(dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return "empty", 0.0, "no_finite_values"
    has_neg = bool((finite < 0).any())
    vmin, vmax, vmed = float(finite.min()), float(finite.max()), float(np.median(finite))
    # integer fraction on a sample
    samp = finite if finite.size <= 200000 else np.random.choice(finite, 200000, replace=False)
    int_frac = float(np.mean(np.isclose(samp, np.round(samp))))
    colsums = np.nansum(np.where(np.isfinite(vals), vals, np.nan), axis=0)
    colsums = colsums[np.isfinite(colsums)]
    colsum_med = float(np.median(colsums)) if colsums.size else float("nan")
    colsum_cv = float(np.std(colsums) / np.mean(colsums)) if colsums.size and np.mean(colsums) else float("nan")
    ev = (
        f"int_frac={int_frac:.3f};has_neg={has_neg};min={vmin:.3g};max={vmax:.3g};"
        f"median={vmed:.3g};colsum_med={colsum_med:.4g};colsum_cv={colsum_cv:.3f}"
    )
    # rules (research.md spec 010 §2)
    if has_neg:
        if vmax < 30 and vmin > -30:
            return "rlog_vst_or_log", 0.8, ev
        return "microarray_intensity_or_log", 0.7, ev
    if int_frac >= 0.98 and vmin >= 0:
        return "raw_counts", min(0.95, 0.6 + int_frac * 0.35), ev
    if 0.5 <= int_frac < 0.98:
        return "raw_counts_suspect", 0.5, ev
    # non-integer, non-negative
    if 0.9e6 <= colsum_med <= 1.1e6:
        return "tpm", 0.85, ev
    if vmax < 30 and vmed < 20:
        return "log_normalized", 0.75, ev  # log2(TPM/CPM) etc
    return "fpkm_or_normalized_other", 0.6, ev


def main() -> int:
    rows = []
    man = pd.read_csv(EXPR_MANIFEST, sep="\t", dtype=str).fillna("")
    for _, r in man.iterrows():
        cid = r["cohort_id"]
        claimed = r["source_type_selected"]
        path = resolve_primary_expression_path(cid, EXPR_MANIFEST, DOWNLOADS_ROOT)
        if path is None or not path.exists():
            rows.append({"cohort_id": cid, "claimed": claimed, "detected": "FILE_NOT_FOUND",
                         "confidence": "", "agree": "", "evidence": str(path or "")})
            continue
        try:
            df = load_expression_matrix(path)
        except Exception as exc:  # noqa: BLE001
            rows.append({"cohort_id": cid, "claimed": claimed, "detected": f"LOAD_ERR:{exc}",
                         "confidence": "", "agree": "", "evidence": ""})
            continue
        if df is None or df.empty:
            rows.append({"cohort_id": cid, "claimed": claimed, "detected": "UNREADABLE",
                         "confidence": "", "agree": "", "evidence": str(path)})
            continue
        detected, conf, ev = classify(df)
        claimed_norm = claimed.replace("processed_", "").replace("_suppl", "")
        agree = "Y" if (
            (claimed_norm.startswith("raw_count") and detected.startswith("raw_counts"))
            or (claimed_norm == "tpm" and detected == "tpm")
            or (claimed_norm == "fpkm" and detected.startswith("fpkm"))
        ) else ("?" if claimed_norm in ("matrix",) else "N")
        rows.append({"cohort_id": cid, "claimed": claimed, "detected": detected,
                     "confidence": f"{conf:.2f}", "agree": agree,
                     "shape": f"{df.shape[0]}x{df.shape[1]}", "evidence": ev})
    out = pd.DataFrame(rows)
    pd.set_option("display.max_colwidth", 200)
    pd.set_option("display.width", 240)
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
