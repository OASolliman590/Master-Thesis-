#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) { val <- "" }
  arg_map[[key]] <- val
}

counts_path <- arg_map[["--counts"]]
meta_path <- arg_map[["--metadata"]]
group_col <- arg_map[["--group-col"]]
case_label <- arg_map[["--case"]]
control_label <- arg_map[["--control"]]
out_path <- arg_map[["--out"]]
paired_col <- arg_map[["--paired-col"]]

if (is.null(counts_path) || is.null(meta_path) || is.null(group_col) || is.null(case_label) || is.null(control_label) || is.null(out_path)) {
  stop("Missing required arguments: --counts --metadata --group-col --case --control --out")
}

suppressMessages(library(DESeq2))

counts <- read.table(counts_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)
meta <- read.table(meta_path, header = TRUE, sep = "\t", stringsAsFactors = FALSE)

if (!(group_col %in% colnames(meta))) {
  stop(paste("Missing group column in metadata:", group_col))
}

meta[[group_col]] <- factor(meta[[group_col]])
meta[[group_col]] <- relevel(meta[[group_col]], ref = control_label)

counts <- round(as.matrix(counts))

# Optional paired design for treatment-delta comparisons.
if (!is.null(paired_col) && paired_col != "") {
  if (!(paired_col %in% colnames(meta))) {
    stop(paste("Missing paired column in metadata:", paired_col))
  }
  meta[[paired_col]] <- factor(meta[[paired_col]])
  design_formula <- as.formula(paste("~", paired_col, "+", group_col))
} else {
  design_formula <- as.formula(paste("~", group_col))
}

dds <- DESeqDataSetFromMatrix(countData = counts, colData = meta, design = design_formula)
dds <- DESeq(dds)
res <- results(dds, contrast = c(group_col, case_label, control_label))
res <- as.data.frame(res)
res$gene_id <- rownames(res)

out <- res[, c("gene_id", "log2FoldChange", "lfcSE", "pvalue", "padj")]
colnames(out) <- c("gene_id", "log2fc", "se_or_stat", "p_value", "fdr")
write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
