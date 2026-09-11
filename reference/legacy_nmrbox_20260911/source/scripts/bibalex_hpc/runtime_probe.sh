#!/usr/bin/env bash
set -euo pipefail

ROOT="${BIBALEX_REMOTE_ROOT:-/cluster/users/alex086u1/ici_thesis_pipeline_remote}"
CONDA_BIN="${BIBALEX_CONDA_BIN:-/cluster/eb/software/Anaconda3/2024.02-1/bin/conda}"
CONDA_ENV="${BIBALEX_CONDA_ENV:-ba-hpc}"
R_MODULE="${BIBALEX_R_MODULE:-R/4.4.1-gfbf-2023b}"
R_LIBS_USER="${BIBALEX_R_LIBS_USER:-${ROOT}/r_libs/R-4.4}"

export PYTHONNOUSERSITE=1
export R_LIBS_USER

echo "== Python =="
"${CONDA_BIN}" run -n "${CONDA_ENV}" python -c 'import sys, numpy, pandas, scipy, statsmodels, matplotlib, yaml; print("python", sys.version.split()[0]); print("numpy", numpy.__version__); print("pandas", pandas.__version__); print("scipy", scipy.__version__); print("statsmodels", statsmodels.__version__); print("matplotlib", matplotlib.__version__); print("yaml", yaml.__version__)'

echo "== R =="
source /etc/profile.d/modules.sh 2>/dev/null || true
module load "${R_MODULE}"
Rscript - <<'RS'
lib <- Sys.getenv("R_LIBS_USER")
.libPaths(c(lib, .libPaths()))
pkgs <- c("limma", "edgeR", "DESeq2", "GSVA", "GSEABase", "BiocParallel", "sva", "survival", "ggplot2", "msigdbr", "yaml")
for (pkg in pkgs) {
  status <- if (requireNamespace(pkg, quietly = TRUE)) as.character(packageVersion(pkg)) else "missing"
  cat(pkg, status, sep = "\t")
  cat("\n")
}
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  quit(status = 1)
}
RS
