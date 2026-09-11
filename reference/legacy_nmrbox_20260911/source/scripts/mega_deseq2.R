#!/usr/bin/env Rscript
# Mega-Analysis DESeq2: unified model across all cohorts
# Design: ~ cohort_id + response_label
# The cohort_id covariate absorbs residual batch effects post-ComBat-Seq
# Inputs:
#   --counts  : batch-corrected count matrix (from combat_merge.R)
#   --metadata: metadata TSV with: sample_id, cohort_id, response_label
#   --case    : case level for response_label (e.g. "responder")
#   --control : control level for response_label (e.g. "non_responder")
#   --out     : output DE results TSV

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) { val <- "" }
  arg_map[[key]] <- val
}

counts_path   <- arg_map[["--counts"]]
meta_path     <- arg_map[["--metadata"]]
case_label    <- arg_map[["--case"]]
control_label <- arg_map[["--control"]]
out_path      <- arg_map[["--out"]]

if (is.null(counts_path) || is.null(meta_path) || is.null(case_label) || is.null(control_label) || is.null(out_path)) {
  stop("Missing required arguments: --counts --metadata --case --control --out")
}

suppressMessages(library(DESeq2))

counts <- read.table(counts_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)
meta   <- read.table(meta_path, header = TRUE, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)

# Align
common <- intersect(colnames(counts), meta$sample_id)
counts <- counts[, common, drop = FALSE]
meta   <- meta[match(common, meta$sample_id), , drop = FALSE]
rownames(meta) <- meta$sample_id

# Ensure integer counts
counts <- round(as.matrix(counts))

# Factor setup
meta$response_label <- factor(meta$response_label)
meta$response_label <- relevel(meta$response_label, ref = control_label)
meta$cohort_id      <- factor(meta$cohort_id)

# Determine design: include cohort_id only if >1 cohort
if (length(unique(meta$cohort_id)) > 1) {
  design_formula <- ~ cohort_id + response_label
} else {
  design_formula <- ~ response_label
}

dds <- DESeqDataSetFromMatrix(countData = counts, colData = meta, design = design_formula)
dds <- DESeq(dds)

res <- results(dds, contrast = c("response_label", case_label, control_label))
res <- as.data.frame(res)
res$gene_id <- rownames(res)

out <- res[, c("gene_id", "log2FoldChange", "lfcSE", "pvalue", "padj")]
colnames(out) <- c("gene_id", "log2fc", "se_or_stat", "p_value", "fdr")
write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
message(paste("Mega-analysis DESeq2 complete. Wrote", out_path))
