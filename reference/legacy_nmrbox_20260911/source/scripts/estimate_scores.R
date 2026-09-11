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
out_path <- arg_map[["--out"]]

if (is.null(expr_path) || is.null(out_path)) {
  stop("Missing required arguments: --expr --out")
}

expr <- read.table(expr_path, header = TRUE, row.names = 1, sep = "\t", check.names = FALSE)

# Graceful fallback when the optional estimate package is unavailable.
# Emit a valid GCT scaffold with NA scores so downstream readiness reporting can continue.
if (!requireNamespace("estimate", quietly = TRUE)) {
  sample_ids <- colnames(expr)
  score_names <- c("StromalScore", "ImmuneScore", "ESTIMATEScore", "TumorPurity")
  score_tbl <- data.frame(
    NAME = score_names,
    Description = score_names,
    stringsAsFactors = FALSE
  )
  for (sid in sample_ids) {
    score_tbl[[sid]] <- NA_real_
  }

  gct_path <- paste0(out_path, ".gct")
  con <- file(gct_path, "w")
  writeLines("#1.2", con)
  writeLines(paste(nrow(score_tbl), length(sample_ids), sep = "\t"), con)
  write.table(score_tbl, con, sep = "\t", row.names = FALSE, quote = FALSE)
  close(con)
  quit(status = 0)
}

suppressMessages(library(estimate))

# Write GCT format for ESTIMATE
n_genes <- nrow(expr)
n_samples <- ncol(expr)

gct_path <- paste0(out_path, ".gct")
con <- file(gct_path, "w")
writeLines("#1.2", con)
writeLines(paste(n_genes, n_samples, sep = "\t"), con)
write.table(
  data.frame(Name = rownames(expr), Description = rownames(expr), expr),
  con,
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)
close(con)

filtered_path <- paste0(out_path, ".filtered.gct")
filterCommonGenes(input.f = gct_path, output.f = filtered_path, id = "GeneSymbol")

estimateScore(filtered_path, out_path, platform = "illumina")
