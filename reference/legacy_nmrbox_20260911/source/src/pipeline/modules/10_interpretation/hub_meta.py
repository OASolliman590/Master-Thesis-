from __future__ import annotations

from pathlib import Path

from . import contracts as c
from ...common.io import read_tsv


def load_hubs(interpretation: Path) -> set[str]:
    genes: set[str] = set()
    network_root = interpretation / "network"
    if not network_root.exists():
        return genes
    for path in sorted(network_root.glob("*/hub_genes.tsv")):
        for row in read_tsv(path):
            if row.get("status") == "ok" and row.get("gene"):
                genes.add(str(row["gene"]).upper())
    return genes


def summarize_hub_effects(results_root: Path, genes: set[str]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    summary_rows: list[dict[str, object]] = []
    forest_rows: list[dict[str, object]] = []
    for gene in sorted(genes):
        effects: list[float] = []
        for analysis_id in c.active_analysis_ids(results_root):
            for row in c.load_meta_effects(results_root, analysis_id):
                if c.row_gene(row).upper() != gene:
                    continue
                effect = c.float_or_nan(row.get("meta_effect_random"))
                se = c.float_or_nan(row.get("meta_se_random") or row.get("meta_se_fixed"))
                if effect == effect:
                    effects.append(effect)
                    forest_rows.append(
                        c.with_claim(
                            {
                                "gene": gene,
                                "analysis_id": analysis_id,
                                "cancer_scope": "moderator_not_subgroup",
                                "effect": f"{effect:.6g}",
                                "standard_error": f"{se:.6g}" if se == se else "",
                            },
                            "discovery",
                        )
                    )
        if effects:
            effect_range = max(effects) - min(effects)
            pan_flag = "pan_cancer_candidate" if effect_range <= max(0.25, abs(c.mean(effects))) else "moderator_sensitive_candidate"
            status = "ok"
        else:
            effect_range = float("nan")
            pan_flag = "not_evaluable"
            status = "missing_meta_effect"
        summary_rows.append(
            c.with_claim(
                {
                    "gene": gene,
                    "n_analysis_ids": len(effects),
                    "pan_cancer_flag": pan_flag,
                    "moderator_status": "cancer_as_low_dimension_moderator_only",
                    "mean_effect": f"{c.mean(effects):.6g}" if effects else "",
                    "effect_range": f"{effect_range:.6g}" if effect_range == effect_range else "",
                    "status": status,
                },
                "discovery",
            )
        )
    return summary_rows, forest_rows


def run(
    results_root: Path,
    out: Path | None = None,
    command: str = "interpret hub-meta",
) -> list[Path]:
    interp_root = c.interpretation_root(results_root, out)
    out_dir = interp_root / "hub_meta"
    out_dir.mkdir(parents=True, exist_ok=True)
    hub_genes = load_hubs(interp_root)
    if not hub_genes:
        summary_rows = [
            c.with_claim(
                {
                    "gene": "",
                    "n_analysis_ids": 0,
                    "pan_cancer_flag": "not_evaluable",
                    "moderator_status": "cancer_as_low_dimension_moderator_only",
                    "mean_effect": "",
                    "effect_range": "",
                    "status": "insufficient_signal",
                },
                "discovery",
            )
        ]
        forest_rows: list[dict[str, object]] = []
    else:
        summary_rows, forest_rows = summarize_hub_effects(results_root, hub_genes)
    summary_path = out_dir / "cross_cancer_hub_meta.tsv"
    forest_path = out_dir / "forest_data.tsv"
    c.write_claim_tsv(summary_path, c.HUB_META_FIELDS, summary_rows)
    c.write_claim_tsv(forest_path, c.FOREST_FIELDS, forest_rows)
    input_paths = [Path(p) for p in sorted(str(p) for p in (interp_root / "network").glob("*/hub_genes.tsv"))]
    c.write_reproducibility(out_dir, command, input_paths)
    c.append_analysis_log(interp_root, f"interpret hub-meta outputs={out_dir}")
    return [summary_path, forest_path]

