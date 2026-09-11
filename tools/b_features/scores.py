"""Exact sample-wise midrank score and promoter aggregates. Fixture policies only."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence


def midranks(values: Sequence[float]) -> list[float]:
    """Ascending 1-based midranks. Tied values share the mean of occupied ranks."""
    n = len(values)
    order = sorted(range(n), key=lambda i: (values[i], i))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        mid = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = mid
        i = j + 1
    return ranks


def percentile_from_rank(rank: float, universe_size: int) -> float:
    if universe_size <= 1:
        raise ValueError("universe size must be > 1")
    return (rank - 1.0) / (universe_size - 1.0)


def program_score(
    gene_values: dict[str, float],
    universe: Sequence[str],
    program: Sequence[str],
) -> float:
    missing_u = [gene for gene in universe if gene not in gene_values]
    if missing_u:
        raise ValueError(f"incomplete-universe {missing_u[0]}")
    missing_p = [gene for gene in program if gene not in universe]
    if missing_p:
        raise ValueError(f"program-gene-not-in-universe {missing_p[0]}")
    ordered = list(universe)
    values = [gene_values[gene] for gene in ordered]
    ranks = midranks(values)
    q = {
        gene: percentile_from_rank(rank, len(ordered))
        for gene, rank in zip(ordered, ranks)
    }
    return sum(q[gene] for gene in program) / float(len(program))


def mean_or_none(values: Iterable[float]) -> float | None:
    collected = list(values)
    if not collected:
        return None
    return sum(collected) / float(len(collected))
