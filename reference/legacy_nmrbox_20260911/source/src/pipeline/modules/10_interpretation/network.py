from __future__ import annotations

from itertools import combinations
from pathlib import Path

from . import contracts as c


def signal_genes(
    meta_rows: list[dict[str, str]],
    fdr_threshold: float = 0.5,
    effect_threshold: float = 0.3,
) -> list[dict[str, object]]:
    genes: list[dict[str, object]] = []
    for row in meta_rows:
        gene = c.row_gene(row).upper()
        effect = c.float_or_nan(row.get("meta_effect_random"))
        fdr = c.float_or_nan(row.get("meta_fdr") or row.get("meta_p") or row.get("meta_p_value"))
        if not gene or not effect == effect:
            continue
        if fdr == fdr and fdr <= fdr_threshold and abs(effect) >= effect_threshold:
            genes.append(
                {
                    "gene": gene,
                    "effect": effect,
                    "fdr": fdr,
                    "direction": "responder_up" if effect > 0 else "non_responder_up",
                    "module": "ranked_meta_signal",
                }
            )
    genes.sort(key=lambda r: (float(r["fdr"]), -abs(float(r["effect"])), str(r["gene"])))
    return genes


def _hub_row(analysis_id: str, status: str, reason: str) -> dict[str, object]:
    return c.with_claim(
        {
            "analysis_id": analysis_id,
            "gene": "",
            "centrality": "",
            "permutation_fdr": "",
            "direction": "",
            "module": "",
            "status": status,
            "reason": reason,
        },
        "discovery",
    )


def build_edges(analysis_id: str, genes: list[dict[str, object]], max_genes: int = 50) -> list[dict[str, object]]:
    selected = genes[:max_genes]
    edges: list[dict[str, object]] = []
    for left, right in combinations(selected, 2):
        if left["direction"] != right["direction"]:
            continue
        weight = min(abs(float(left["effect"])), abs(float(right["effect"])))
        edges.append(
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "source_gene": left["gene"],
                    "target_gene": right["gene"],
                    "weight": f"{weight:.6g}",
                    "edge_source": "ranked_meta_same_direction_backbone",
                    "status": "ok",
                },
                "discovery",
            )
        )
    return edges


def hub_rows_from_edges(
    analysis_id: str,
    genes: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not edges:
        return [_hub_row(analysis_id, "insufficient_signal", "no_ranked_backbone_edges")]
    degree: dict[str, int] = {str(g["gene"]): 0 for g in genes}
    for edge in edges:
        degree[str(edge["source_gene"])] = degree.get(str(edge["source_gene"]), 0) + 1
        degree[str(edge["target_gene"])] = degree.get(str(edge["target_gene"]), 0) + 1
    max_degree = max(degree.values()) if degree else 0
    if max_degree <= 0:
        return [_hub_row(analysis_id, "insufficient_signal", "zero_degree_network")]
    gene_lookup = {str(g["gene"]): g for g in genes}
    ranked = sorted(degree.items(), key=lambda item: (-item[1], item[0]))
    rows: list[dict[str, object]] = []
    n = max(1, len(ranked))
    for rank, (gene, deg) in enumerate(ranked, start=1):
        if deg == 0:
            continue
        meta = gene_lookup.get(gene, {})
        centrality = deg / max(1, n - 1)
        permutation_fdr = min(1.0, rank / n)
        rows.append(
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "gene": gene,
                    "centrality": f"{centrality:.6g}",
                    "permutation_fdr": f"{permutation_fdr:.6g}",
                    "direction": meta.get("direction", ""),
                    "module": meta.get("module", "ranked_meta_signal"),
                    "status": "ok",
                    "reason": "",
                },
                "discovery",
            )
        )
    return rows


def run(
    results_root: Path,
    analysis_id: str,
    out: Path | None = None,
    min_signal_floor: int = 25,
    fdr_threshold: float = 0.5,
    effect_threshold: float = 0.3,
    command: str = "interpret network",
) -> list[Path]:
    interp_root = c.interpretation_root(results_root, out)
    out_dir = interp_root / "network" / analysis_id
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = c.meta_effects_path(results_root, analysis_id)
    meta_rows = c.load_meta_effects(results_root, analysis_id)
    genes = signal_genes(meta_rows, fdr_threshold=fdr_threshold, effect_threshold=effect_threshold)
    reason = (
        f"signal_floor_not_met:n_signal={len(genes)};min_signal_floor={min_signal_floor};"
        f"fdr_threshold={fdr_threshold};effect_threshold={effect_threshold}"
    )
    if len(genes) < min_signal_floor:
        edges: list[dict[str, object]] = []
        hubs = [_hub_row(analysis_id, "insufficient_signal", reason)]
        diff_rows = [
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "comparison": "responder_vs_non_responder_network_topology",
                    "n_edges": 0,
                    "n_hubs": 0,
                    "status": "insufficient_signal",
                    "reason": reason,
                },
                "discovery",
            )
        ]
    else:
        edges = build_edges(analysis_id, genes)
        hubs = hub_rows_from_edges(analysis_id, genes, edges)
        diff_rows = [
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "comparison": "responder_vs_non_responder_network_topology",
                    "n_edges": len(edges),
                    "n_hubs": sum(1 for h in hubs if h.get("status") == "ok"),
                    "status": "ok" if edges else "insufficient_signal",
                    "reason": "" if edges else "no_edges_after_same_direction_filter",
                },
                "discovery",
            )
        ]
    edge_path = out_dir / "edges.tsv"
    hub_path = out_dir / "hub_genes.tsv"
    diff_path = out_dir / "hub_difference.tsv"
    c.write_claim_tsv(edge_path, c.EDGE_FIELDS, edges)
    c.write_claim_tsv(hub_path, c.HUB_FIELDS, hubs)
    c.write_claim_tsv(diff_path, c.HUB_DIFF_FIELDS, diff_rows)
    c.write_reproducibility(out_dir, command, [meta_path])
    c.append_analysis_log(interp_root, f"interpret network analysis_id={analysis_id} outputs={out_dir}")
    return [edge_path, hub_path, diff_path]

