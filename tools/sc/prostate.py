"""Python adapter for the hormone-naive prostate single-cell atlas."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from .core import (
    MIN_CELLS,
    MIN_DONORS_TO_SHOW,
    MIN_UMIS,
    ProfileTable,
    aggregate_anndata,
    expression_summary,
    gene_set_table,
    panel_definitions,
)
from .runtime import configure_runtime


ROOT = Path(__file__).resolve().parents[2]
MARKERS = {
    "Epithelial": ("EPCAM", "KRT8", "KRT18", "KLK3"),
    "Basal": ("KRT5", "KRT14", "KRT15", "TP63"),
    "T/NK": ("CD3D", "CD3E", "TRAC", "NKG7"),
    "B/plasma": ("MS4A1", "CD79A", "MZB1", "JCHAIN"),
    "Myeloid": ("LST1", "TYROBP", "FCER1G", "S100A9"),
    "Fibroblast/stromal": ("COL1A1", "DCN", "ACTA2", "RGS5"),
    "Endothelial": ("PECAM1", "VWF", "KDR", "EMCN"),
}


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_candidates(runtime: Path, atlas: str, suffix: str) -> list[Path]:
    root = runtime / atlas
    manifest = json.loads((root / "store/MANIFEST.json").read_text(encoding="utf-8"))
    candidates = []
    for key, record in manifest.get("objects", {}).items():
        locator = str(record.get("locator", ""))
        receipt_url = str(record.get("receipt", {}).get("final_url", ""))
        receipt_path = urlparse(receipt_url).path
        if suffix.casefold() in locator.casefold() or suffix.casefold() in receipt_path.casefold():
            candidate = root / "store/objects" / key
            if candidate.is_file():
                candidates.append(candidate)
    return candidates


def _source_by_suffix(runtime: Path, atlas: str, suffix: str) -> Path:
    candidates = _source_candidates(runtime, atlas, suffix)
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one {suffix} source for {atlas}; found {len(candidates)}")
    return candidates[0]


def _prostate_source(runtime: Path) -> Path:
    candidates = _source_candidates(runtime, "prostate_hormone_naive_atlas", ".h5ad")
    if not candidates:
        raise FileNotFoundError("No h5ad objects were recorded for the prostate atlas")
    import anndata

    matches = []
    for candidate in candidates:
        adata = anndata.read_h5ad(candidate, backed="r")
        try:
            if adata.shape == (68_322, 32_397) and "donor_id" in adata.obs:
                if adata.obs["donor_id"].nunique(dropna=True) == 24:
                    matches.append(candidate)
        finally:
            adata.file.close()
    if len(matches) != 1:
        raise FileNotFoundError(
            "Expected one full prostate atlas matching the signed 68,322-cell, 24-donor record; "
            f"found {len(matches)}"
        )
    return matches[0]


def load_h5ad(runtime: Path):
    configure_runtime()
    import anndata

    source = _prostate_source(runtime)
    adata = anndata.read_h5ad(source)
    if adata.raw is not None:
        if not adata.raw.var_names.equals(adata.var_names):
            raise ValueError("AnnData.raw.X and X use different gene orders")
        matrix = adata.raw.X
        raw_source = "AnnData.raw.X"
    else:
        matrix = adata.X
        raw_source = "AnnData.X"
    values = matrix.data if hasattr(matrix, "data") and hasattr(matrix, "indptr") else np.asarray(matrix).ravel()
    if np.any(values < 0) or not np.allclose(values, np.round(values)):
        raise ValueError(f"{raw_source} is not a non-negative integer count matrix")
    adata.layers["counts"] = matrix.copy()
    return adata, source


def _summaries(series: pd.Series) -> dict[str, float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {key: np.nan for key in ("min", "q1", "median", "q3", "max")}
    return {
        "min": float(values.min()),
        "q1": float(values.quantile(0.25)),
        "median": float(values.median()),
        "q3": float(values.quantile(0.75)),
        "max": float(values.max()),
    }


def qc_summary(adata) -> pd.DataFrame:
    """Summarize per-cell QC distributions without applying a filter."""
    configure_runtime()
    import scanpy as sc

    adata.var["mt"] = adata.var_names.astype(str).str.upper().str.startswith("MT-")
    sc.pp.calculate_qc_metrics(
        adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True, layer="counts"
    )
    fields = {
        "genes_per_cell": "n_genes_by_counts",
        "umis_per_cell": "total_counts",
        "mitochondrial_percent": "pct_counts_mt",
    }
    records = []
    for metric, column in fields.items():
        record = {"metric": metric, "scope": "all cells", "cells": int(adata.n_obs)}
        record.update(_summaries(adata.obs[column]))
        records.append(record)
    flag_columns = [
        column for column in adata.obs.columns
        if re.search(r"doublet|(^|_)qc($|_)|filter|singlet|outlier", str(column), re.I)
    ]
    for column in flag_columns:
        counts = adata.obs[column].astype("string").fillna("NA").value_counts(dropna=False)
        for label, count in counts.items():
            records.append(
                {"metric": f"author_flag:{column}", "scope": str(label), "cells": int(count)}
            )
    result = pd.DataFrame.from_records(records)
    result["filtering_applied"] = False
    result["count_layer"] = "AnnData.raw.X"
    return result


def _map_compartments(adata) -> None:
    mapping_path = Path(__file__).with_name("prostate_compartment_map.tsv")
    mapping = pd.read_csv(mapping_path, sep="\t", dtype=str).fillna("")
    index = {(row.source_major, row.source_minor): row.compartment for row in mapping.itertuples()}
    major = adata.obs["celltype_major_v2"].astype("string").fillna("").astype(str)
    minor = adata.obs["celltype_minor_v2"].astype("string").fillna("").astype(str)
    values = [index.get((m, n), index.get((m, "*"), index.get((m, "")))) for m, n in zip(major, minor, strict=True)]
    adata.obs["compartment"] = pd.Categorical(
        [value if value and value != "unmapped" else None for value in values]
    )


def aggregate_profiles(adata) -> ProfileTable:
    """Create donor-by-compartment count profiles for cancer tissue only."""
    _map_compartments(adata)
    tissue = adata.obs["type"].astype("string").fillna("").str.casefold()
    all_cancer = adata[tissue.eq("cancer").to_numpy()].copy()
    cancer = all_cancer[all_cancer.obs["compartment"].notna().to_numpy()].copy()
    if "donor_id" not in cancer.obs:
        raise ValueError("The prostate atlas is missing donor_id")
    cancer.obs["cohort"] = "prostate_hormone_naive_atlas"
    cancer.obs["study"] = "prostate_hormone_naive_atlas"
    cancer.obs["cancer"] = "prostate"
    cancer.obs["treatment"] = "untreated_hormone_naive"
    cancer.obs["response_metric"] = ""
    cancer.obs["response"] = ""
    profiles = aggregate_anndata(
        cancer,
        donor_col="donor_id",
        compartment_col="compartment",
        metadata_cols=("cohort", "study", "cancer", "treatment", "response_metric", "response"),
        min_cells=MIN_CELLS,
        min_umis=MIN_UMIS,
    )
    symbol_column = "gene_name" if "gene_name" in cancer.var else "feature_name"
    if symbol_column not in cancer.var:
        raise ValueError("The prostate atlas has no gene-symbol annotation for panel extraction")
    profiles.gene_symbols = pd.Series(
        cancer.var[symbol_column].astype("string").fillna("").astype(str).to_numpy(),
        index=cancer.var_names.astype(str),
        name=symbol_column,
    )
    denominator = all_cancer.obs.groupby("donor_id", observed=True).size()
    profiles.clinical["fraction_cells_total"] = [
        float(row.n_cells) / float(denominator.loc[row.donor_id])
        for row in profiles.clinical.itertuples()
    ]
    profiles.clinical["endpoint_family"] = ""
    profiles.clinical["outcome_label"] = ""
    profiles.clinical["baseline"] = True
    return profiles


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not_installed"


def write_layout(profiles: ProfileTable, atlas_dir: Path, input_sha256: str) -> None:
    base = atlas_dir / "pseudobulk"
    base.mkdir(parents=True, exist_ok=True)
    for compartment, clinical in profiles.clinical.groupby("compartment", sort=True, dropna=False):
        name = str(compartment)
        slug = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
        output = base / slug
        output.mkdir(parents=True, exist_ok=True)
        profile_ids = clinical["profile_id"].astype(str).tolist()
        profiles.expression.loc[:, profile_ids].to_csv(
            output / "expression.tsv", sep="\t", index_label="gene", na_rep="NA"
        )
        clinical.to_csv(output / "clinical.tsv", sep="\t", index=False, na_rep="NA")
        manifest = {
            "atlas": "prostate_hormone_naive_atlas",
            "paper": "B",
            "unit": "patient",
            "compartment": name,
            "count_source": "raw UMI counts from AnnData.raw.X",
            "count_layer": "counts",
            "minimum_cells": MIN_CELLS,
            "minimum_umis": MIN_UMIS,
            "minimum_donors_for_summary": MIN_DONORS_TO_SHOW,
            "interpretation_note": "Ambient RNA may blur detection; non-detection is not evidence of absence.",
            "input_sha256": input_sha256,
            "packages": {name: _version(name) for name in ("scanpy", "anndata", "decoupler", "matplotlib")},
            "outputs": {"expression.tsv": _digest(output / "expression.tsv"), "clinical.tsv": _digest(output / "clinical.tsv")},
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def marker_plot(adata, output: Path) -> None:
    configure_runtime()
    import scanpy as sc

    symbol_column = "gene_name" if "gene_name" in adata.var else "feature_name"
    if symbol_column not in adata.var:
        raise ValueError("The prostate atlas has no gene-symbol annotation for marker checks")
    symbols = adata.var[symbol_column].astype("string").fillna("").astype(str)
    symbol_counts = symbols.value_counts()
    marker_map = {
        label: [gene for gene in genes if symbol_counts.get(gene, 0) == 1]
        for label, genes in MARKERS.items()
    }
    marker_map = {label: genes for label, genes in marker_map.items() if genes}
    if not marker_map:
        raise ValueError("None of the canonical marker genes are present in the prostate atlas")
    display = adata.copy()
    display.X = display.layers["counts"].copy()
    sc.pp.normalize_total(display, target_sum=1_000_000)
    sc.pp.log1p(display)
    output.parent.mkdir(parents=True, exist_ok=True)
    dot = sc.pl.dotplot(
        display,
        marker_map,
        groupby="celltype_minor_v2",
        gene_symbols=symbol_column,
        use_raw=False,
        standard_scale=None,
        dendrogram=False,
        show=False,
        return_fig=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    dot.savefig(output, dpi=160, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close("all")
    del display


def compartment_table(profiles: ProfileTable) -> pd.DataFrame:
    definitions = panel_definitions()
    genes = tuple(dict.fromkeys(gene for members in definitions.values() for gene in members))
    summary_profiles = profiles
    if profiles.gene_symbols is not None:
        symbols = profiles.gene_symbols.astype(str)
        counts = symbols[symbols.ne("")].value_counts()
        id_to_symbol = {
            feature_id: symbol
            for feature_id, symbol in symbols.items()
            if symbol and counts.get(symbol, 0) == 1
        }
        summary_expression = profiles.expression.rename(index=id_to_symbol)
        summary_detection = (
            profiles.detection.rename(index=id_to_symbol)
            if profiles.detection is not None
            else None
        )
        summary_profiles = ProfileTable(summary_expression, profiles.clinical, summary_detection)
    result = expression_summary(summary_profiles, study_col="study", genes=genes)
    if not result.empty:
        result["panel_ids"] = result["gene"].map(
            lambda gene: ",".join(panel for panel, members in definitions.items() if gene in members)
        )
    return result


def compartment_dotplot(summary: pd.DataFrame, output: Path) -> None:
    configure_runtime()
    import matplotlib.pyplot as plt

    shown = summary.loc[summary["status"].eq("shown")].copy()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(max(12, len(shown["gene"].unique()) * 0.18), 6))
    if not shown.empty:
        x_order = list(dict.fromkeys(shown["gene"]))
        y_order = list(dict.fromkeys(shown["compartment"]))
        x = pd.Categorical(shown["gene"], categories=x_order).codes
        y = pd.Categorical(shown["compartment"], categories=y_order).codes
        sizes = shown["median_percent_cells_detected"].fillna(0).clip(0, 100) * 2.0 + 3.0
        points = ax.scatter(x, y, s=sizes, c=shown["median_log2_cpm_plus1"], cmap="viridis", linewidths=0)
        ax.set_xticks(range(len(x_order)), x_order, rotation=90, fontsize=6)
        ax.set_yticks(range(len(y_order)), y_order)
        fig.colorbar(points, ax=ax, label="Median donor log2(CPM + 1)")
    ax.set_title("Prostate compartment expression; dot size = median cell detection")
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def run_embedding(adata, output_dir: Path) -> None:
    configure_runtime()
    import scanpy as sc

    output_dir.mkdir(parents=True, exist_ok=True)
    adata.X = adata.layers["counts"].copy()
    sc.pp.normalize_total(adata, target_sum=10_000)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, flavor="seurat", n_top_genes=2_000)
    sc.tl.pca(adata, n_comps=50, mask_var="highly_variable", svd_solver="arpack")
    sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)
    sc.tl.umap(adata)
    sc.tl.leiden(adata, resolution=0.8, key_added="leiden", flavor="igraph", directed=False)
    sc.pl.umap(adata, color=["celltype_major_v2", "leiden"], show=False)
    import matplotlib.pyplot as plt

    plt.savefig(output_dir / "umap.png", dpi=180, bbox_inches="tight")
    plt.close("all")
    adata.write_h5ad(output_dir / "prostate_embedding.h5ad")
