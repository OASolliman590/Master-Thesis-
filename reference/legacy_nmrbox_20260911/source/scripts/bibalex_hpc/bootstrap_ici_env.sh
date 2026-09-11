#!/usr/bin/env bash
set -euo pipefail

ROOT="${BIBALEX_REMOTE_ROOT:-/cluster/users/alex086u1/ici_thesis_pipeline_remote}"
CONDA_BIN="${BIBALEX_CONDA_BIN:-/cluster/eb/software/Anaconda3/2024.02-1/bin/conda}"
CONDA_ENV="${BIBALEX_CONDA_ENV:-ba-hpc}"
R_MODULE="${BIBALEX_R_MODULE:-R/4.4.1-gfbf-2023b}"
R_LIBS_USER="${BIBALEX_R_LIBS_USER:-${ROOT}/r_libs/R-4.4}"
LOG_DIR="${ROOT}/logs"

mkdir -p "${ROOT}" "${LOG_DIR}" "${R_LIBS_USER}"
chmod 700 "${ROOT}"

export PYTHONNOUSERSITE=1
export R_LIBS_USER
export MAKEFLAGS="${MAKEFLAGS:--j${SLURM_CPUS_PER_TASK:-2}}"

echo "== BibaLex ICI runtime bootstrap =="
date -u +"started_utc=%Y-%m-%dT%H:%M:%SZ"
echo "host=$(hostname)"
echo "root=${ROOT}"
echo "conda_env=${CONDA_ENV}"
echo "r_libs_user=${R_LIBS_USER}"

echo
echo "== Python smoke =="
"${CONDA_BIN}" run -n "${CONDA_ENV}" python -c 'import sys, numpy, pandas, scipy, statsmodels, matplotlib, yaml; print("python", sys.version.split()[0]); print("numpy", numpy.__version__); print("pandas", pandas.__version__); print("scipy", scipy.__version__); print("statsmodels", statsmodels.__version__); print("matplotlib", matplotlib.__version__); print("yaml", yaml.__version__)'

echo
echo "== R package bootstrap =="
source /etc/profile.d/modules.sh 2>/dev/null || true
module load "${R_MODULE}"
Rscript - <<'RS'
options(repos = c(CRAN = "https://cloud.r-project.org"))
lib <- Sys.getenv("R_LIBS_USER")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
cat("R.version\t", as.character(getRversion()), "\n", sep = "")
cat("R_LIBS_USER\t", lib, "\n", sep = "")

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", lib = lib)
}

bioc_pkgs <- c(
  "limma",
  "edgeR",
  "DESeq2",
  "GSVA",
  "GSEABase",
  "BiocParallel",
  "sva"
)
cran_pkgs <- c(
  "survival",
  "ggplot2",
  "msigdbr",
  "yaml"
)

missing_bioc <- bioc_pkgs[!vapply(bioc_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_bioc) > 0) {
  ncpus <- suppressWarnings(as.integer(Sys.getenv("SLURM_CPUS_PER_TASK", "2")))
  if (!is.finite(ncpus) || ncpus < 1L) {
    ncpus <- 2L
  }
  BiocManager::install(missing_bioc, lib = lib, ask = FALSE, update = FALSE, Ncpus = ncpus)
}

missing_cran <- cran_pkgs[!vapply(cran_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_cran) > 0) {
  install.packages(missing_cran, lib = lib)
}

all_pkgs <- c(bioc_pkgs, cran_pkgs)
for (pkg in all_pkgs) {
  status <- if (requireNamespace(pkg, quietly = TRUE)) as.character(packageVersion(pkg)) else "missing"
  cat(pkg, status, sep = "\t")
  cat("\n")
}
RS

echo
echo "== Final R smoke =="
Rscript - <<'RS'
lib <- Sys.getenv("R_LIBS_USER")
.libPaths(c(lib, .libPaths()))
pkgs <- c("limma", "DESeq2", "GSVA", "GSEABase", "BiocParallel", "survival", "ggplot2")
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  stop(paste("Missing required R packages:", paste(missing, collapse = ", ")))
}
cat("R required packages OK\n")
RS

date -u +"finished_utc=%Y-%m-%dT%H:%M:%SZ"
