from __future__ import annotations

from pathlib import Path

from . import contracts as c
from ...common.io import read_tsv


def parse_gmt(path: Path) -> list[dict[str, object]]:
    gene_sets: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            name = parts[0].strip()
            genes = sorted({g.strip().upper() for g in parts[2:] if g.strip()})
            if name and genes:
                gene_sets.append({"pathway": name, "genes": genes})
    return gene_sets


def _resolve_path(raw: str, registry_path: Path) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    parent_candidate = registry_path.parent / p
    if parent_candidate.exists():
        return parent_candidate
    return Path.cwd() / p


def load_gene_sets(collection_paths: list[Path]) -> list[dict[str, object]]:
    loaded: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for collection in collection_paths:
        if collection.suffix.lower() == ".gmt":
            for gset in parse_gmt(collection):
                key = (collection.stem, str(gset["pathway"]))
                if key not in seen:
                    seen.add(key)
                    loaded.append(
                        {
                            "collection": collection.stem,
                            "pathway": gset["pathway"],
                            "genes": gset["genes"],
                            "source_path": str(collection),
                        }
                    )
            continue
        for row in read_tsv(collection):
            enabled = str(row.get("enabled", "true")).strip().lower()
            if enabled in {"false", "0", "no"}:
                continue
            gmt_raw = (row.get("gmt_path") or "").strip()
            if not gmt_raw:
                continue
            gmt_path = _resolve_path(gmt_raw, collection)
            if not gmt_path.exists():
                continue
            collection_name = row.get("gene_set_layer") or row.get("source") or collection.stem
            for gset in parse_gmt(gmt_path):
                pathway = str(gset["pathway"])
                key = (str(collection_name), pathway)
                if key in seen:
                    continue
                seen.add(key)
                loaded.append(
                    {
                        "collection": str(collection_name),
                        "pathway": pathway,
                        "genes": gset["genes"],
                        "source_path": str(gmt_path),
                    }
                )
    return loaded


def ranked_gene_values(meta_rows: list[dict[str, str]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in meta_rows:
        gene = c.row_gene(row).upper()
        value = c.float_or_nan(row.get("meta_effect_random"))
        if not gene or not value == value:
            continue
        if gene not in values or abs(value) > abs(values[gene]):
            values[gene] = value
    return values


def signature_genes(signature_rows: list[dict[str, str]]) -> set[str]:
    genes = set()
    for row in signature_rows:
        gene = c.row_gene(row).upper()
        if gene and str(row.get("blocked_flag", "")).strip().lower() not in {"true", "1", "yes"}:
            genes.add(gene)
    return genes


def compute_gsea_rows(
    analysis_id: str,
    ranked_values: dict[str, float],
    gene_sets: list[dict[str, object]],
    min_overlap: int = 2,
) -> list[dict[str, object]]:
    all_values = list(ranked_values.values())
    global_mean = c.mean(all_values)
    global_sd = c.stdev(all_values)
    rows: list[dict[str, object]] = []
    p_values: list[float] = []
    universe = set(ranked_values)
    for gset in gene_sets:
        genes = set(str(g).upper() for g in gset["genes"])  # type: ignore[index]
        overlap = sorted(genes & universe)
        if len(overlap) < min_overlap or not global_sd == global_sd or global_sd <= 0:
            nes = 0.0
            p_value = 1.0
            status = "insufficient_overlap"
            leading = ""
        else:
            vals = [ranked_values[g] for g in overlap]
            z = (c.mean(vals) - global_mean) / (global_sd / (len(vals) ** 0.5))
            nes = z
            p_value = c.normal_two_sided_p(z)
            status = "ok"
            leading_genes = sorted(overlap, key=lambda g: ranked_values[g], reverse=z >= 0)
            leading = ";".join(leading_genes[:25])
        p_values.append(p_value)
        rows.append(
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "collection": gset["collection"],
                    "pathway": gset["pathway"],
                    "n_genes": len(genes),
                    "n_overlap": len(overlap),
                    "statistic": "meta_effect_random",
                    "nes": f"{nes:.6g}",
                    "p_value": f"{p_value:.6g}",
                    "fdr": "",
                    "leading_edge_genes": leading,
                    "method": "ranked_meta_zscore_gsea_fallback",
                    "status": status,
                },
                "mechanism_hypothesis",
            )
        )
    for row, fdr in zip(rows, c.bh_fdr(p_values), strict=False):
        row["fdr"] = f"{fdr:.6g}"
    return sorted(rows, key=lambda r: (float(r["fdr"]), -abs(float(r["nes"])), str(r["pathway"])))


def compute_ora_rows(
    analysis_id: str,
    ranked_values: dict[str, float],
    sig_genes: set[str],
    gene_sets: list[dict[str, object]],
    min_overlap: int = 1,
) -> list[dict[str, object]]:
    universe = set(ranked_values)
    signature = sig_genes & universe
    rows: list[dict[str, object]] = []
    p_values: list[float] = []
    for gset in gene_sets:
        genes = set(str(g).upper() for g in gset["genes"]) & universe  # type: ignore[index]
        overlap = sorted(genes & signature)
        if len(overlap) < min_overlap or not signature:
            p_value = 1.0
            odds_proxy = 0.0
            status = "insufficient_signature_overlap"
        else:
            p_value = c.hypergeom_sf(len(overlap), len(universe), len(genes), len(signature))
            bg_rate = len(genes) / len(universe) if universe else 0.0
            sig_rate = len(overlap) / len(signature) if signature else 0.0
            odds_proxy = sig_rate / bg_rate if bg_rate > 0 else 0.0
            status = "ok"
        p_values.append(p_value)
        rows.append(
            c.with_claim(
                {
                    "analysis_id": analysis_id,
                    "collection": gset["collection"],
                    "pathway": gset["pathway"],
                    "n_genes": len(genes),
                    "n_overlap": len(overlap),
                    "signature_genes": len(signature),
                    "odds_proxy": f"{odds_proxy:.6g}",
                    "p_value": f"{p_value:.6g}",
                    "fdr": "",
                    "overlap_genes": ";".join(overlap[:50]),
                    "method": "signature_hypergeometric_ora",
                    "status": status,
                },
                "mechanism_hypothesis",
            )
        )
    for row, fdr in zip(rows, c.bh_fdr(p_values), strict=False):
        row["fdr"] = f"{fdr:.6g}"
    return sorted(rows, key=lambda r: (float(r["fdr"]), -float(r["n_overlap"]), str(r["pathway"])))


def _blocked_enrichment_rows(
    analysis_id: str,
    gene_sets: list[dict[str, object]],
    reason: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    n_gene_sets = len(gene_sets)
    gsea_rows = [
        c.with_claim(
            {
                "analysis_id": analysis_id,
                "collection": "",
                "pathway": "",
                "n_genes": 0,
                "n_overlap": 0,
                "statistic": "meta_effect_random",
                "nes": "0",
                "p_value": "1",
                "fdr": "1",
                "leading_edge_genes": "",
                "method": "ranked_meta_zscore_gsea_fallback",
                "status": f"blocked:{reason};n_gene_sets={n_gene_sets}",
            },
            "mechanism_hypothesis",
        )
    ]
    ora_rows = [
        c.with_claim(
            {
                "analysis_id": analysis_id,
                "collection": "",
                "pathway": "",
                "n_genes": 0,
                "n_overlap": 0,
                "signature_genes": 0,
                "odds_proxy": "0",
                "p_value": "1",
                "fdr": "1",
                "overlap_genes": "",
                "method": "signature_hypergeometric_ora",
                "status": f"blocked:{reason};n_gene_sets={n_gene_sets}",
            },
            "mechanism_hypothesis",
        )
    ]
    return gsea_rows, ora_rows, []


def run(
    results_root: Path,
    analysis_id: str,
    collections: list[Path],
    out: Path | None = None,
    min_overlap: int = 2,
    command: str = "interpret enrich",
) -> list[Path]:
    interp_root = c.interpretation_root(results_root, out)
    out_dir = interp_root / "enrichment" / analysis_id
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = c.meta_effects_path(results_root, analysis_id)
    sig_path = c.signature_path(results_root, analysis_id)
    meta_rows = c.load_meta_effects(results_root, analysis_id)
    ranked = ranked_gene_values(meta_rows)
    gene_sets = load_gene_sets(collections)
    if not ranked:
        gsea_rows, ora_rows, dotplot_rows = _blocked_enrichment_rows(
            analysis_id,
            gene_sets,
            "no_ranked_meta_effect_random",
        )
    else:
        gsea_rows = compute_gsea_rows(analysis_id, ranked, gene_sets, min_overlap=min_overlap)
        ora_rows = compute_ora_rows(
            analysis_id,
            ranked,
            signature_genes(c.load_signature(results_root, analysis_id)),
            gene_sets,
        )
        dotplot_rows = []
        for source, rows in [("gsea", gsea_rows[:30]), ("ora", ora_rows[:30])]:
            for row in rows:
                dotplot_rows.append(
                    c.with_claim(
                        {
                            "analysis_id": analysis_id,
                            "source": source,
                            "collection": row["collection"],
                            "pathway": row["pathway"],
                            "n_overlap": row["n_overlap"],
                            "score": row.get("nes") or row.get("odds_proxy") or "",
                            "fdr": row["fdr"],
                        },
                        "mechanism_hypothesis",
                    )
                )
    gsea_path = out_dir / "gsea.tsv"
    ora_path = out_dir / "ora.tsv"
    dotplot_path = out_dir / "dotplot_data.tsv"
    provenance_path = out_dir / "provenance.md"
    c.write_claim_tsv(gsea_path, c.GSEA_FIELDS, gsea_rows)
    c.write_claim_tsv(ora_path, c.ORA_FIELDS, ora_rows)
    c.write_claim_tsv(dotplot_path, c.DOTPLOT_FIELDS, dotplot_rows)
    sources = sorted({str(gs["source_path"]) for gs in gene_sets})
    provenance_path.write_text(
        "\n".join(
            [
                f"# Enrichment Provenance: {analysis_id}",
                "",
                f"- generated_utc: {c.timestamp()}",
                "- ranked_statistic: meta_effect_random",
                "- gsea_method: ranked_meta_zscore_gsea_fallback",
                "- ora_method: signature_hypergeometric_ora",
                f"- status: {'blocked_no_ranked_meta_effect_random' if not ranked else 'ok'}",
                f"- n_ranked_genes: {len(ranked)}",
                f"- n_gene_sets: {len(gene_sets)}",
                "- claim_class: mechanism_hypothesis",
                "- collections:",
                *[f"  - {src}" for src in sources],
                "",
            ]
        ),
        encoding="utf-8",
    )
    c.write_reproducibility(out_dir, command, [meta_path, sig_path, *collections])
    c.append_analysis_log(interp_root, f"interpret enrich analysis_id={analysis_id} outputs={out_dir}")
    return [gsea_path, ora_path, dotplot_path, provenance_path]
