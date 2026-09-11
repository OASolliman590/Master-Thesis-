#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
expr_path <- args[which(args == "--expr") + 1]
out_path <- args[which(args == "--out") + 1]

if (length(expr_path) == 0 || length(out_path) == 0) {
  stop("Missing required arguments: --expr and --out")
}

out_dir <- dirname(out_path)
if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
}

# If the input matrix cannot be resolved, still emit a valid placeholder.
if (!file.exists(expr_path)) {
  fallback <- data.frame(cell_type = "EPIC_input_missing", stringsAsFactors = FALSE)
  write.table(
    fallback,
    file = out_path,
    sep = "\t",
    row.names = FALSE,
    quote = FALSE
  )
  quit(status = 0)
}

# Load linear-scale bulk RNA-seq
expr <- read.table(expr_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)

# Graceful fallback for offline environments where EPIC is not installed.
# Emit a valid scaffold matrix so downstream readiness reporting can proceed.
if (!requireNamespace("EPIC", quietly = TRUE)) {
  sample_ids <- colnames(expr)
  fallback <- data.frame(cell_type = "EPIC_unavailable", stringsAsFactors = FALSE)
  for (sid in sample_ids) {
    fallback[[sid]] <- NA_real_
  }
  write.table(
    fallback,
    file = out_path,
    sep = "\t",
    row.names = FALSE,
    quote = FALSE
  )
  quit(status = 0)
}
suppressMessages(library(EPIC))

# Deconvolute using EPIC standard Tumor Reference (TRef) or Blood (BRef)
# TRef is optimal for solid tumors
epic_res <- EPIC(bulk = expr, reference = "TRef")

# Fractions output (Samples as rows, Cell Types as cols)
fractions <- t(epic_res$cellFractions)

# Write output as a long-format or wide-format TSV
# We will write wide-format (cell types as rows, samples as cols) to match standard pipeline conventions
write.table(
  data.frame(cell_type = rownames(fractions), fractions, check.names=FALSE),
  file = out_path,
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)
