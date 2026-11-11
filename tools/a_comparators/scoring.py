"""Narrow scoring adapters for the Paper A comparator contract."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from tools import a_scoring


_CYT_GENES = ("GZMA", "PRF1")


def cyt_scores_from_tpm(
    feature_symbols: Sequence[str],
    expression_by_feature: Sequence[Sequence[float | None]],
    representation,
    *,
    runtime=None,
    aliases: Mapping[str, str] | None = None,
    synonyms: Mapping[str, set[str] | frozenset[str]] | None = None,
    gene_symbols: Mapping[str, str] | None = None,
) -> list[float | None]:
    """Score already-qualified full-source linear RNA-seq TPM in sample order.

    This function does not normalize, impute, or infer source completeness.
    Source qualification and full-universe TPM preparation remain with the
    accepted A-P2 input route; this adapter accepts only its TPM representation.
    """
    _require_linear_rnaseq_tpm(representation)
    rows = _numeric_matrix(expression_by_feature)
    if len(feature_symbols) != len(rows):
        raise ValueError("CYT feature symbols and expression rows do not align")
    if not rows:
        raise ValueError("CYT expression matrix is empty")

    indices, coverage = a_scoring.resolve(
        feature_symbols,
        _CYT_GENES,
        runtime=runtime,
        aliases=aliases,
        synonyms=synonyms,
        gene_symbols=gene_symbols,
    )
    unresolved = [
        f"{gene} ({coverage[gene]['resolution']})"
        for gene in _CYT_GENES
        if not coverage[gene]["present"]
    ]
    if unresolved:
        raise ValueError("CYT requires unique GZMA and PRF1 rows; unresolved: " + ", ".join(unresolved))

    gzma = rows[indices["GZMA"]]
    prf1 = rows[indices["PRF1"]]
    return [
        None if gzma_value is None or prf1_value is None
        else a_scoring.cyt(gzma_value, prf1_value)
        for gzma_value, prf1_value in zip(gzma, prf1)
    ]


def _require_linear_rnaseq_tpm(representation) -> None:
    if hasattr(representation, "representation"):
        representation = representation.representation
    if isinstance(representation, Mapping):
        platform = representation.get("platform", "")
        unit = representation.get("unit", "")
        transform = representation.get("transform", "")
    else:
        platform = getattr(representation, "platform", "")
        unit = getattr(representation, "unit", "")
        transform = getattr(representation, "transform", "")
    if (str(platform).casefold(), str(unit).casefold(), str(transform).casefold()) != (
        "rnaseq", "tpm", "linear"
    ):
        raise ValueError("CYT requires qualified linear RNA-seq TPM; no conversion is performed")


def _numeric_matrix(matrix: Sequence[Sequence[float | None]]) -> list[list[float | None]]:
    try:
        rows = [
            [None if value is None else float(value) for value in row]
            for row in matrix
        ]
    except (TypeError, ValueError):
        raise ValueError("expression matrix must be a rectangular numeric matrix") from None
    if not rows:
        return rows
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("expression matrix must be rectangular")
    if any(
        value is not None and (not math.isfinite(value) or value < 0)
        for row in rows
        for value in row
    ):
        raise ValueError("invalid TPM abundance: values must be finite and non-negative")
    return rows
