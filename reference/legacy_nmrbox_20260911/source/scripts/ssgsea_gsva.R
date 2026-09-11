#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) { val <- "" }
  arg_map[[key]] <- val
}

expr_path <- arg_map[["--expr"]]
gmt_path <- arg_map[["--gmt"]]
out_path <- arg_map[["--out"]]

if (is.null(expr_path) || is.null(gmt_path) || is.null(out_path)) {
  stop("Missing required arguments: --expr --gmt --out")
}

suppressMessages(library(GSVA))

read_gmt <- function(path) {
  lines <- readLines(path, warn = FALSE)
  sets <- list()
  for (ln in lines) {
    parts <- strsplit(ln, "\t", fixed = TRUE)[[1]]
    if (length(parts) < 3) next
    set_name <- parts[[1]]
    genes <- unique(parts[3:length(parts)])
    genes <- genes[genes != ""]
    if (length(genes) == 0) next
    sets[[set_name]] <- genes
  }
  sets
}

expr_df <- read.table(expr_path, header = TRUE, sep = "\t", check.names = FALSE, stringsAsFactors = FALSE)
if (ncol(expr_df) < 2) {
  stop("Expression matrix must have >=2 columns (gene_id + at least one sample).")
}

gene_col <- colnames(expr_df)[1]
expr_df[[gene_col]] <- as.character(expr_df[[gene_col]])
expr_df <- expr_df[!is.na(expr_df[[gene_col]]) & expr_df[[gene_col]] != "", , drop = FALSE]

# Collapse duplicate gene IDs by mean to ensure a unique row index for GSVA.
dup_mask <- duplicated(expr_df[[gene_col]])
if (any(dup_mask)) {
  numeric_cols <- setdiff(colnames(expr_df), gene_col)
  expr_df[numeric_cols] <- lapply(expr_df[numeric_cols], as.numeric)
  expr_df <- aggregate(expr_df[numeric_cols], by = list(gene_id = expr_df[[gene_col]]), FUN = mean, na.rm = TRUE)
  gene_col <- "gene_id"
}

rownames(expr_df) <- expr_df[[gene_col]]
expr_df <- expr_df[, setdiff(colnames(expr_df), gene_col), drop = FALSE]
expr <- as.matrix(expr_df)
mode(expr) <- "numeric"

gene_sets <- read_gmt(gmt_path)
if (length(gene_sets) == 0) {
  stop(sprintf("No gene sets parsed from GMT: %s", gmt_path))
}

# Keep only sets with at least one overlapping feature to avoid hard GSVA failures.
expr_features <- rownames(expr)
gene_sets <- lapply(gene_sets, function(gs) intersect(gs, expr_features))
gene_sets <- gene_sets[vapply(gene_sets, length, integer(1)) > 0]
if (length(gene_sets) == 0) {
  empty_scores <- matrix(
    numeric(0),
    nrow = 0,
    ncol = ncol(expr),
    dimnames = list(character(0), colnames(expr))
  )
  write.table(empty_scores, file = out_path, sep = "\t", row.names = TRUE, quote = FALSE)
  quit(status = 0)
}

# GSVA >= 2.0 uses method-specific parameter objects (e.g. ssgseaParam).
# Keep compatibility with older GSVA APIs to avoid runtime breakage across environments.
gsva_formals <- names(formals(GSVA::gsva))
if (!is.null(gsva_formals) && "param" %in% gsva_formals) {
  ssgsea_param <- GSVA::ssgseaParam(
    exprData = expr,
    geneSets = gene_sets,
    normalize = TRUE
  )
  ssgsea_scores <- GSVA::gsva(ssgsea_param, verbose = FALSE)
} else {
  ssgsea_scores <- GSVA::gsva(
    expr,
    gene_sets,
    method = "ssgsea",
    kcdf = "Gaussian",
    abs.ranking = FALSE
  )
}

write.table(ssgsea_scores, file = out_path, sep = "\t", row.names = TRUE, quote = FALSE)
