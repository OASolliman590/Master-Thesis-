from __future__ import annotations

from pathlib import Path


def write_meta_forest_plots(
    *,
    out_rows: list[dict[str, str]],
    out_dir: Path,
    max_genes: int = 50,
    fdr_threshold: float = 0.05,
) -> int:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return 0

    forest_dir = Path(out_dir)
    forest_dir.mkdir(parents=True, exist_ok=True)
    written = 0

    sorted_by_fdr = sorted(out_rows, key=lambda r: float(r.get("meta_fdr", "1.0") or 1.0))
    for row in sorted_by_fdr[:max_genes]:
        if float(row.get("meta_fdr", "1.0") or 1.0) > fdr_threshold:
            break
        entries = row.get("_entries", [])
        if not entries:
            continue
        gene = row.get("gene_id", "")
        if not gene:
            continue
        n = len(entries)

        fig, ax = plt.subplots(figsize=(7, max(2, 0.5 * n + 1.5)))
        for j, (eff, se, _pv, cohort) in enumerate(entries):
            ci_lo = eff - 1.96 * se
            ci_hi = eff + 1.96 * se
            ax.plot([ci_lo, ci_hi], [j, j], color="#4C78A8", linewidth=1.5)
            ax.plot(eff, j, "o", color="#4C78A8", markersize=6)
            ax.text(ci_hi + 0.05, j, cohort, va="center", fontsize=8)

        pooled = float(row.get("meta_effect_random", "0.0") or 0.0)
        pooled_se = float(row.get("meta_se_random", "0.0") or 0.0)
        diamond_y = -1
        ax.fill(
            [pooled - 1.96 * pooled_se, pooled, pooled + 1.96 * pooled_se, pooled],
            [diamond_y, diamond_y - 0.3, diamond_y, diamond_y + 0.3],
            color="#E45756",
            alpha=0.8,
        )
        ax.axvline(0, color="grey", linestyle="--", linewidth=0.7)
        ax.set_yticks(list(range(n)) + [diamond_y])
        ax.set_yticklabels([e[3] for e in entries] + ["Pooled"], fontsize=8)
        ax.set_xlabel("log2 Fold Change")
        ax.set_title(f"{gene} (FDR={row.get('meta_fdr', '')})")
        ax.invert_yaxis()
        fig.tight_layout()
        fig.savefig(forest_dir / f"{gene}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        written += 1

    return written
