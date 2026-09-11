#!/usr/bin/env bash
set -euo pipefail

R_LIBS_USER="${R_LIBS_USER:-/home/nmrbox/0000/osoliman/ici_thesis_pipeline_remote/R_libs/4.1}"
NCPUS="${NCPUS:-2}"

mkdir -p "${R_LIBS_USER}"
export R_LIBS_USER
export MAKEFLAGS="-j${NCPUS}"

Rscript - <<'RS'
user_lib <- Sys.getenv("R_LIBS_USER")
.libPaths(c(user_lib, .libPaths()))
options(repos = c(CRAN = "https://cloud.r-project.org"))

cat("R_VERSION", as.character(getRversion()), "\n")
cat("R_LIBS_USER", user_lib, "\n")
cat("LIBPATHS", paste(.libPaths(), collapse = "|"), "\n")

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", lib = user_lib)
}

required <- c("GSVA", "DESeq2", "limma")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  cat("INSTALLING", paste(missing, collapse = ","), "\n")
  BiocManager::install(
    missing,
    lib = user_lib,
    ask = FALSE,
    update = FALSE,
    Ncpus = as.integer(Sys.getenv("NCPUS", "2"))
  )
}

all_required <- c("GSVA", "GSEABase", "limma", "DESeq2", "BiocManager")
status <- vapply(all_required, requireNamespace, logical(1), quietly = TRUE)
for (pkg in names(status)) {
  cat("PACKAGE", pkg, status[[pkg]], "\n")
}

if (!all(status)) {
  quit(status = 1)
}
RS
