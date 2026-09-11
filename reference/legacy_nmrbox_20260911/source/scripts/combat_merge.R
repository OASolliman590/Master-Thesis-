#!/usr/bin/env Rscript
# ComBat-Seq batch correction for multi-cohort RNA-seq mega-analysis
# Inputs:
#   --counts  : path to merged raw count matrix (genes × samples), TSV
#   --metadata: path to metadata TSV with columns: sample_id, cohort_id, response_label
#   --out     : path to write batch-corrected count matrix TSV

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) { val <- "" }
  arg_map[[key]] <- val
}

counts_path <- arg_map[["--counts"]]
meta_path   <- arg_map[["--metadata"]]
out_path    <- arg_map[["--out"]]

if (is.null(counts_path) || is.null(meta_path) || is.null(out_path)) {
  stop("Missing required arguments: --counts --metadata --out")
}

# Install sva if missing
if (!requireNamespace("sva", quietly = TRUE)) {
  if (!requireNamespace("BiocManager", quietly = TRUE)) {
    install.packages("BiocManager", repos = "http://cran.us.r-project.org")
  }
  BiocManager::install("sva")
}

suppressMessages(library(sva))

counts <- read.table(counts_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)
meta   <- read.table(meta_path, header = TRUE, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)

# Align samples
common <- intersect(colnames(counts), meta$sample_id)
if (length(common) < 4) {
  stop("Fewer than 4 samples in common between counts and metadata. Cannot run ComBat-Seq.")
}

counts <- counts[, common, drop = FALSE]
meta   <- meta[match(common, meta$sample_id), , drop = FALSE]

# Ensure integer counts
counts <- round(as.matrix(counts))

# Batch = cohort_id, biological condition = response_label
batch <- meta$cohort_id
group <- meta$response_label

# Verify we have >1 batch
if (length(unique(batch)) < 2) {
  message("Only one batch detected. Writing uncorrected counts.")
  write.table(
    data.frame(gene_id = rownames(counts), counts, check.names = FALSE),
    file = out_path, sep = "\t", row.names = FALSE, quote = FALSE
  )
  quit(save = "no", status = 0)
}

# ComBat-Seq preserves integer count distribution
adjusted <- ComBat_seq(
  counts  = counts,
  batch   = batch,
  group   = group
)

# Write output
out_df <- data.frame(gene_id = rownames(adjusted), adjusted, check.names = FALSE)
write.table(out_df, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
message(paste("ComBat-Seq complete. Wrote", out_path))
