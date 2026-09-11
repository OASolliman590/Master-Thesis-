from __future__ import annotations


def resolve_de_backend(
    *,
    assay_type: str,
    count_like_matrix: bool,
    hard_exclude_assays: set[str],
) -> str:
    if assay_type in hard_exclude_assays:
        return "excluded"
    if assay_type == "raw_counts" and count_like_matrix:
        return "count_model"
    return "limma_trend"
