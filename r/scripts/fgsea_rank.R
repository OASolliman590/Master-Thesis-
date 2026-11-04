source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "fgsea"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir

ranking <- read.delim(bridge$inputs$ranking, check.names = FALSE,
                      stringsAsFactors = FALSE, na.strings = c("", "NA"),
                      quote = "\"", comment.char = "")
if (!all(c("gene", "statistic") %in% names(ranking))) {
  stop("DE ranking needs gene and statistic columns")
}
ranking$gene <- as.character(ranking$gene)
ranking$statistic <- suppressWarnings(as.numeric(ranking$statistic))
if (anyNA(ranking$gene) || any(!nzchar(ranking$gene)) || anyDuplicated(ranking$gene)) {
  stop("DE ranking gene identifiers must be unique and non-empty")
}
ranking <- ranking[is.finite(ranking$statistic), , drop = FALSE]
if (nrow(ranking) < 2L) stop("At least two finite ranked genes are required")
ordering <- order(-ranking$statistic, ranking$gene, method = "radix")
statistics <- ranking$statistic[ordering]
names(statistics) <- ranking$gene[ordering]
pathways <- fgsea::gmtPathways(bridge$inputs$gene_sets)
if (!length(pathways)) stop("The local GMT file contains no gene sets")

result <- fgsea::fgseaMultilevel(
  pathways = pathways,
  stats = statistics,
  minSize = as.integer(cfg$min_size),
  maxSize = as.integer(cfg$max_size),
  eps = 0
)
if (nrow(result)) {
  result <- as.data.frame(result, stringsAsFactors = FALSE)
  result$leadingEdge <- vapply(result$leadingEdge, paste, collapse = ";", FUN.VALUE = character(1))
  names(result)[names(result) == "pathway"] <- "pathway"
  names(result)[names(result) == "pval"] <- "p"
  names(result)[names(result) == "padj"] <- "q"
  names(result)[names(result) == "ES"] <- "ES"
  names(result)[names(result) == "NES"] <- "NES"
  names(result)[names(result) == "size"] <- "size"
  result <- result[, c("pathway", "p", "q", "ES", "NES", "size", "leadingEdge"), drop = FALSE]
} else {
  result <- data.frame(pathway = character(), p = numeric(), q = numeric(),
                       ES = numeric(), NES = numeric(), size = integer(),
                       leadingEdge = character())
}
utils::write.table(result, file.path(out_dir, "fgsea.tsv"), sep = "\t",
                    row.names = FALSE, quote = FALSE, na = "NA")
summary <- list(
  pathway_count = nrow(result),
  ranked_gene_count = length(statistics),
  gene_set_count = length(pathways),
  method = "fgseaMultilevel",
  endpoint = cfg$endpoint,
  gene_sets_input = "local_GMT"
)
jsonlite::write_json(summary, file.path(out_dir, "gsea_summary.json"),
                     auto_unbox = TRUE, pretty = TRUE, na = "null")
bridge_write_session(out_dir)
