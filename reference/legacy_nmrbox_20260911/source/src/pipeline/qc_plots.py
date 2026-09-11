import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    import pandas as pd
    import matplotlib
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.decomposition import PCA
    from scipy.stats import spearmanr
    from scipy.spatial.distance import pdist, squareform

    matplotlib.use("Agg")  # Headless backend
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


def _get_top_variable_genes(expr: "pd.DataFrame", n: int = 1000) -> "pd.DataFrame":
    """Extract top N most variable genes by MAD."""
    mad = np.abs(expr.sub(expr.median(axis=1), axis=0)).median(axis=1)
    top_genes = mad.nlargest(n).index
    return expr.loc[top_genes]


def _stringify_matrix_labels(expr: "pd.DataFrame") -> "pd.DataFrame":
    """Normalize axis labels for sklearn/seaborn plotting APIs."""
    out = expr.copy()
    out.index = out.index.map(str)
    out.columns = out.columns.map(str)
    return out


def plot_library_size_boxplot(lib_sizes: "pd.Series", out_path: Path) -> None:
    if not PLOTTING_AVAILABLE:
        return
    plt.figure(figsize=(6, 4))
    sns.boxplot(y=lib_sizes)
    sns.swarmplot(y=lib_sizes, color=".25")
    plt.title("Library Size Distribution")
    plt.ylabel("Total Counts per Sample")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_gene_detection_barplot(zeros_frac: "pd.Series", out_path: Path) -> None:
    if not PLOTTING_AVAILABLE:
        return
    plt.figure(figsize=(10, 4))
    zeros_frac = zeros_frac.sort_values(ascending=False)
    ax = sns.barplot(x=zeros_frac.index, y=zeros_frac.values, color="steelblue")
    plt.title("Fraction of Undetected Genes per Sample")
    plt.ylabel("Fraction Zeros")
    plt.xticks(rotation=90)
    if len(zeros_frac) > 50:
        ax.set_xticks([])  # Hide x-labels if too many samples
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def calculate_housekeeping_stability(expr: "pd.DataFrame") -> List[Dict[str, Any]]:
    if not PLOTTING_AVAILABLE:
        return []
    hk_genes = ["ACTB", "GAPDH", "B2M", "RPL13A", "RPLP0", "HPRT1"]
    found = [g for g in hk_genes if g in expr.index]
    if not found:
        return []
    
    results = []
    for g in found:
        vals = expr.loc[g]
        mean_val = vals.mean()
        std_val = vals.std(ddof=1)
        cv = std_val / mean_val if mean_val > 0 else np.nan
        results.append({
            "gene": g,
            "mean_log2": f"{mean_val:.4f}",
            "std_log2": f"{std_val:.4f}",
            "cv": f"{cv:.4f}"
        })
    return results


def calculate_cooks_distance(expr: "pd.DataFrame") -> "pd.Series":
    """
    Approximation of Cook's distance leverage for samples across top genes.
    A high value indicates the sample strongly pulls the global mean.
    """
    if not PLOTTING_AVAILABLE or expr.empty:
        return None
    
    expr_top = _get_top_variable_genes(expr, 1000)
    if expr_top.empty:
        return None

    expr_top = expr_top.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    if expr_top.empty:
        return None
    expr_top = _stringify_matrix_labels(expr_top)

    global_mean = expr_top.mean(axis=1)
    
    distances = {}
    n_samples = expr_top.shape[1]
    
    for col in expr_top.columns:
        # Mean without this sample
        mean_without = (expr_top.sum(axis=1) - expr_top[col]) / (n_samples - 1)
        # MSE
        mse = ((global_mean - mean_without) ** 2).mean()
        distances[col] = mse
        
    dist_series = pd.Series(distances)
    # Normalize to z-scores roughly
    if dist_series.std() > 0:
        dist_z = (dist_series - dist_series.mean()) / dist_series.std()
    else:
        dist_z = pd.Series(0.0, index=dist_series.index)
    return dist_z


def plot_pca(
    expr: "pd.DataFrame", 
    metadata: "pd.DataFrame", 
    color_by: str, 
    shape_by: Optional[str], 
    out_path: Path,
    title: str = "PCA"
) -> Dict[str, float]:
    if not PLOTTING_AVAILABLE:
        return {}
        
    expr_top = _get_top_variable_genes(expr, 1000)
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return {}

    # Drop genes/samples with NaN/Inf values that break PCA
    expr_top = expr_top.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return {}
    expr_top = _stringify_matrix_labels(expr_top)

    pca = PCA(n_components=2)
    pcs = pca.fit_transform(expr_top.T)
    
    df_pca = pd.DataFrame({
        "PC1": pcs[:, 0],
        "PC2": pcs[:, 1],
        "sample_id": expr_top.columns
    })
    
    # Merge metadata safely
    metadata = metadata.copy()
    if "sample_id" in metadata.columns:
        metadata["sample_id"] = metadata["sample_id"].astype(str)
    df_pca = df_pca.merge(metadata, on="sample_id", how="left")
    
    # Fill NAs in coloring columns
    if color_by in df_pca.columns:
        df_pca[color_by] = df_pca[color_by].fillna("unknown").astype(str)
    else:
        df_pca[color_by] = "unknown"
        
    if shape_by and shape_by in df_pca.columns:
        df_pca[shape_by] = df_pca[shape_by].fillna("unknown").astype(str)
    else:
        shape_by = None

    plt.figure(figsize=(8, 6))
    
    sns.scatterplot(
        data=df_pca, 
        x="PC1", 
        y="PC2", 
        hue=color_by, 
        style=shape_by, 
        s=100, 
        alpha=0.8,
        palette="Set2" if df_pca[color_by].nunique() <= 8 else "husl"
    )
    
    plt.title(title)
    plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    
    return {
        "pc1_var_explained": pca.explained_variance_ratio_[0],
        "pc2_var_explained": pca.explained_variance_ratio_[1]
    }


def plot_sample_distance_heatmap(expr: "pd.DataFrame", out_path: Path) -> None:
    if not PLOTTING_AVAILABLE:
        return
        
    expr_top = _get_top_variable_genes(expr, 1000)
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return

    expr_top = expr_top.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return
    expr_top = _stringify_matrix_labels(expr_top)

    # Spearman correlation distance
    corr_matrix = expr_top.corr(method="spearman")
    
    # Use seaborn clustermap
    plt.figure(figsize=(10, 10))
    g = sns.clustermap(
        corr_matrix, 
        cmap="vlag", 
        vmin=corr_matrix.values.min(), 
        vmax=1.0,
        xticklabels=True if corr_matrix.shape[0] < 30 else False,
        yticklabels=True if corr_matrix.shape[0] < 30 else False,
        figsize=(8, 8)
    )
    g.fig.suptitle("Sample Spearman Correlation Heatmap", y=1.05)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close('all')


def calculate_variance_partition(expr: "pd.DataFrame", metadata: "pd.DataFrame", factors: List[str]) -> Dict[str, float]:
    """
    Very crude fast approximation of variance explained by discrete categorical factors using PC1 & PC2 sums of squares.
    Returns % variance explained by each factor.
    """
    if not PLOTTING_AVAILABLE or expr.empty:
        return {}
        
    expr_top = _get_top_variable_genes(expr, 1000)
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return {}

    # Drop genes/samples with NaN/Inf values that break PCA
    expr_top = expr_top.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    if expr_top.shape[0] < 3 or expr_top.shape[1] < 3:
        return {}
    expr_top = _stringify_matrix_labels(expr_top)

    # We will compute the sum of squares for the first 5 PCs to approximate total dataset variance.
    pca = PCA(n_components=min(5, expr_top.shape[1]-1))
    pcs = pca.fit_transform(expr_top.T)
    weights = pca.explained_variance_ratio_
    
    df_pca = pd.DataFrame(pcs, columns=[f"PC{i+1}" for i in range(pcs.shape[1])])
    df_pca["sample_id"] = expr_top.columns
    df_pca = df_pca.merge(metadata, on="sample_id", how="left")
    
    results = {}
    for factor in factors:
        if factor not in df_pca.columns:
            results[factor] = 0.0
            continue
            
        # Drop NAs for this factor
        valid = df_pca.dropna(subset=[factor])
        if valid[factor].nunique() < 2:
            results[factor] = 0.0
            continue
            
        explained_var = 0.0
        for i in range(pcs.shape[1]):
            pc_col = f"PC{i+1}"
            global_mean = valid[pc_col].mean()
            tss = ((valid[pc_col] - global_mean)**2).sum()
            
            # Group sum of squares
            bg_ss = 0.0
            for name, group in valid.groupby(factor):
                bg_ss += len(group) * ((group[pc_col].mean() - global_mean)**2)
                
            if tss > 0:
                r2 = bg_ss / tss
                explained_var += r2 * weights[i]
                
        # Normalize by the variance we captured in the top 5 PCs
        results[factor] = explained_var / weights.sum()
        
    return results
