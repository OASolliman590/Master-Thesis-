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

if (is.null(counts_path) || is.null(meta_path) || is.null(group_col) || is.null(case_label) || is.null(control_label) || is.null(out_path)) {
  stop("Missing required arguments: --counts --metadata --group-col --case --control --out")
}

suppressMessages(library(edgeR))

counts <- read.table(counts_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)
meta <- read.table(meta_path, header = TRUE, sep = "\t", stringsAsFactors = FALSE)

if (!(group_col %in% colnames(meta))) {
  stop(paste("Missing group column in metadata:", group_col))
}

group <- factor(meta[[group_col]])
counts <- round(as.matrix(counts))

y <- DGEList(counts = counts, group = group)
y <- calcNormFactors(y)

paired_col <- arg_map[["--paired-col"]]

if (!is.null(paired_col) && paired_col != "") {
  patient <- factor(meta[[paired_col]])
  design <- model.matrix(~ patient + group)
  coef <- ncol(design)
} else {
  design <- model.matrix(~ group)
  coef <- 2
}

y <- estimateDisp(y, design)
fit <- glmQLFit(y, design)
qlf <- glmQLFTest(fit, coef = coef)
res <- topTags(qlf, n = nrow(counts), sort.by = "none")$table
res$gene_id <- rownames(res)

# Robust SE derivation with fallback
# Primary: F-statistic based (exact when available)
# Fallback: dispersion-based approximation using tagwise dispersion
res$se <- ifelse(
  !is.na(res$F) & res$F > 0,
  abs(res$logFC) / sqrt(res$F),
  {
    # Fallback: sqrt(tagwise dispersion / mean library size)
    disp <- y$tagwise.dispersion
    if (is.null(disp)) disp <- rep(y$common.dispersion, nrow(res))
    mean_lib <- mean(y$samples$lib.size * y$samples$norm.factors)
    sqrt(disp / max(mean_lib, 1))
  }
)
out <- res[, c("gene_id", "logFC", "se", "PValue", "FDR")]
colnames(out) <- c("gene_id", "log2fc", "se_or_stat", "p_value", "fdr")
write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
