from __future__ import annotations

from typing import Callable


def harmonize_expression_for_assay(
    expr,
    assay_type: str,
    *,
    canonicalize_assay_type: Callable[[str], str] | None = None,
):
    import numpy as np

    canonical = (
        canonicalize_assay_type(assay_type) if canonicalize_assay_type is not None else (assay_type or "")
    )
    assay = canonical or (assay_type or "")
    expr = expr.fillna(0.0)

    if assay in {"log_normalized", "rlog_vst", "microarray_intensity"}:
        return expr, "as_is_log_scale"
    if assay in {"tpm", "fpkm", "normalized_other", "raw_counts_suspect", "raw_counts"}:
        return np.log2(expr + 1.0), "log2(x+1)"
    return expr, "unknown"
