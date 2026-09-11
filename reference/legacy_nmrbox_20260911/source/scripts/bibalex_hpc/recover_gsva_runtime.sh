#!/usr/bin/env bash
set -euo pipefail

ROOT="${BIBALEX_REMOTE_ROOT:-/cluster/users/alex086u1/ici_thesis_pipeline_remote}"
R_MODULE="${BIBALEX_R_MODULE:-R/4.4.1-gfbf-2023b}"
R_LIBS_USER="${BIBALEX_R_LIBS_USER:-${ROOT}/r_libs/R-4.4}"

export R_LIBS_USER
export MAKEFLAGS="${MAKEFLAGS:--j${SLURM_CPUS_PER_TASK:-2}}"

echo "== BibaLex GSVA runtime recovery =="
date -u +"started_utc=%Y-%m-%dT%H:%M:%SZ"
echo "host=$(hostname)"
echo "root=${ROOT}"
echo "r_libs_user=${R_LIBS_USER}"

source /etc/profile.d/modules.sh 2>/dev/null || true
module load "${R_MODULE}"

# R magick needs ImageMagick's Magick++ development files. BibaLex exposes a
# GraphicsMagick module, which may or may not satisfy the CRAN package.
module load GraphicsMagick/1.3.36-GCCcore-11.2.0 2>/dev/null || true

echo
echo "== System probes =="
command -v Rscript
Rscript --version
command -v pkg-config || true
pkg-config --modversion Magick++ 2>/dev/null || true
pkg-config --modversion ImageMagick++ 2>/dev/null || true
pkg-config --modversion GraphicsMagick++ 2>/dev/null || true
command -v Magick++-config || true
command -v GraphicsMagick++-config || true
command -v convert || true
command -v gm || true

echo
echo "== Remove stale R package locks =="
find "${R_LIBS_USER}" -maxdepth 1 -type d -name '00LOCK*' -print -exec rm -rf {} +

echo
echo "== Targeted R install/probe =="
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

cran_first <- c("magick")
missing_cran <- cran_first[!vapply(cran_first, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_cran) > 0) {
  install.packages(missing_cran, lib = lib)
}

bioc_pkgs <- c("SpatialExperiment", "GSVA")
missing_bioc <- bioc_pkgs[!vapply(bioc_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_bioc) > 0) {
  ncpus <- suppressWarnings(as.integer(Sys.getenv("SLURM_CPUS_PER_TASK", "2")))
  if (!is.finite(ncpus) || ncpus < 1L) {
    ncpus <- 2L
  }
  BiocManager::install(
    missing_bioc,
    lib = lib,
    ask = FALSE,
    update = FALSE,
    Ncpus = ncpus,
    dependencies = c("Depends", "Imports", "LinkingTo")
  )
}

required <- c(
  "limma",
  "edgeR",
  "DESeq2",
  "GSVA",
  "GSEABase",
  "BiocParallel",
  "sva",
  "survival",
  "ggplot2",
  "msigdbr",
  "yaml"
)
for (pkg in required) {
  status <- if (requireNamespace(pkg, quietly = TRUE)) as.character(packageVersion(pkg)) else "missing"
  cat(pkg, status, sep = "\t")
  cat("\n")
}
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  stop(paste("Missing required R packages:", paste(missing, collapse = ", ")))
}
cat("BibaLex required R runtime OK\n")
RS

date -u +"finished_utc=%Y-%m-%dT%H:%M:%SZ"
