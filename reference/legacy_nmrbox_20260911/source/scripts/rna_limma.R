#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
if (length(args) > 0) {
  for (i in seq(1, length(args), by = 2)) {
    key <- args[[i]]
    val <- args[[i + 1]]
    if (is.null(val)) { val <- "" }
    arg_map[[key]] <- val
  }
}

expr_path <- arg_map[["--expr"]]
meta_path <- arg_map[["--metadata"]]
group_col <- arg_map[["--group-col"]]
case_label <- arg_map[["--case"]]
control_label <- arg_map[["--control"]]
out_path <- arg_map[["--out"]]

if (is.null(expr_path) || is.null(meta_path) || is.null(group_col) || is.null(case_label) || is.null(control_label) || is.null(out_path)) {
  stop("Missing required arguments: --expr --metadata --group-col --case --control --out")
}

suppressMessages(library(limma))

expr_df <- read.table(expr_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)
meta_df <- read.table(meta_path, header = TRUE, sep = "\t", check.names = FALSE, stringsAsFactors = FALSE)

if (!("sample_id" %in% colnames(meta_df))) {
  stop("Metadata file must include sample_id column.")
}
if (!(group_col %in% colnames(meta_df))) {
  stop(sprintf("Metadata missing group column: %s", group_col))
}

meta_df <- meta_df[meta_df$sample_id %in% colnames(expr_df), , drop = FALSE]
if (nrow(meta_df) < 4) {
  stop("Need at least four samples for limma model.")
}
meta_df <- meta_df[match(colnames(expr_df), meta_df$sample_id), , drop = FALSE]

groups <- as.character(meta_df[[group_col]])
keep <- groups %in% c(case_label, control_label)
meta_df <- meta_df[keep, , drop = FALSE]
expr_df <- expr_df[, meta_df$sample_id, drop = FALSE]
groups <- as.character(meta_df[[group_col]])

if (sum(groups == case_label) < 2 || sum(groups == control_label) < 2) {
  stop("Need >=2 samples in each group for limma model.")
}

expr_mat <- as.matrix(expr_df)
suppressWarnings(storage.mode(expr_mat) <- "numeric")
finite_rows <- rowSums(is.finite(expr_mat)) == ncol(expr_mat)
row_variance <- apply(expr_mat, 1, var)
testable_rows <- finite_rows & is.finite(row_variance) & row_variance > 0
expr_mat <- expr_mat[testable_rows, , drop = FALSE]

if (nrow(expr_mat) == 0) {
  out <- data.frame(
    gene_id = character(0),
    log2fc = numeric(0),
    se_or_stat = numeric(0),
    p_value = numeric(0),
    fdr = numeric(0)
  )
  write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
  quit(status = 0)
}

group_factor <- factor(groups, levels = c(control_label, case_label))
design <- model.matrix(~ group_factor)
fit <- lmFit(expr_mat, design)
fit <- eBayes(fit, trend = TRUE)

coef_name <- colnames(design)[2]
tt <- topTable(
  fit,
  coef = coef_name,
  number = Inf,
  sort.by = "none",
  adjust.method = "BH"
)

if (nrow(tt) == 0) {
  out <- data.frame(
    gene_id = character(0),
    log2fc = numeric(0),
    se_or_stat = numeric(0),
    p_value = numeric(0),
    fdr = numeric(0)
  )
  write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
  quit(status = 0)
}

out <- data.frame(
  gene_id = rownames(tt),
  log2fc = tt$logFC,
  se_or_stat = abs(tt$logFC / tt$t),
  p_value = tt$P.Value,
  fdr = tt$adj.P.Val
)
out$se_or_stat[!is.finite(out$se_or_stat)] <- NA_real_
write.table(out, file = out_path, sep = "\t", row.names = FALSE, quote = FALSE)
