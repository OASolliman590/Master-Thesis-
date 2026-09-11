#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: fgsea_enrich.R <ranked_tsv> <gmt_file> <out_tsv>", call. = FALSE)
}

if (!requireNamespace("fgsea", quietly = TRUE)) {
  stop("Bioconductor package 'fgsea' is not installed. Use the spec 094 portable R runtime or the Python fallback.", call. = FALSE)
}

ranked_tsv <- args[[1]]
gmt_file <- args[[2]]
out_tsv <- args[[3]]

ranked <- read.delim(ranked_tsv, stringsAsFactors = FALSE, check.names = FALSE)
required <- c("gene_symbol", "meta_effect_random")
missing <- setdiff(required, colnames(ranked))
if (length(missing) > 0) {
  stop(paste("ranked_tsv missing columns:", paste(missing, collapse = ",")), call. = FALSE)
}

ranked <- ranked[!is.na(ranked$gene_symbol) & ranked$gene_symbol != "" & !is.na(ranked$meta_effect_random), ]
ranks <- ranked$meta_effect_random
names(ranks) <- toupper(ranked$gene_symbol)
ranks <- sort(ranks, decreasing = TRUE)

pathways <- fgsea::gmtPathways(gmt_file)
fg <- fgsea::fgsea(pathways = pathways, stats = ranks)
fg$leadingEdge <- vapply(fg$leadingEdge, paste, collapse = ";", FUN.VALUE = character(1))
dir.create(dirname(out_tsv), recursive = TRUE, showWarnings = FALSE)
write.table(fg, out_tsv, sep = "\t", quote = FALSE, row.names = FALSE)
