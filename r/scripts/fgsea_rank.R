source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "fgsea"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir
ranking_id_type <- as.character(cfg$ranking_id_type)
gene_set_id_type <- as.character(cfg$gene_set_id_type)
if (length(ranking_id_type) != 1L || is.na(ranking_id_type) ||
    !nzchar(ranking_id_type) || length(gene_set_id_type) != 1L ||
    is.na(gene_set_id_type) || !nzchar(gene_set_id_type)) {
  stop("Ranking and GMT identifier types must be declared")
}
if (!identical(ranking_id_type, gene_set_id_type)) {
  stop("Ranking and GMT identifier types must match; no mapping is configured")
}
overlap_floor <- suppressWarnings(as.integer(cfg$min_gene_set_overlap))
if (length(overlap_floor) != 1L || is.na(overlap_floor) || overlap_floor < 1L) {
  stop("Minimum GMT/ranking membership overlap must be a positive integer")
}

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
gmt_members <- unique(unlist(pathways, use.names = FALSE))
ranking_members <- names(statistics)
overlap_members <- intersect(gmt_members, ranking_members)
overlap_count <- length(overlap_members)
if (overlap_count < overlap_floor) {
  stop(sprintf(
    "GMT/ranking membership overlap is below configured floor: %d < %d",
    overlap_count, overlap_floor
  ))
}
membership <- do.call(rbind, lapply(names(pathways), function(pathway) {
  members <- unique(pathways[[pathway]])
  overlap <- intersect(members, ranking_members)
  data.frame(
    pathway = pathway,
    gmt_gene_count = length(members),
    ranking_overlap_count = length(overlap),
    overlap_fraction = if (length(members)) length(overlap) / length(members) else 0,
    check.names = FALSE
  )
}))
utils::write.table(membership, file.path(out_dir, "membership_overlap.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")

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
  ranking_id_type = ranking_id_type,
  gene_set_id_type = gene_set_id_type,
  membership_overlap_count = overlap_count,
  membership_overlap_fraction = overlap_count / length(gmt_members),
  minimum_membership_overlap = overlap_floor,
  method = "fgseaMultilevel",
  endpoint = cfg$endpoint,
  gene_sets_input = "local_GMT"
)
jsonlite::write_json(summary, file.path(out_dir, "gsea_summary.json"),
                     auto_unbox = TRUE, pretty = TRUE, na = "null")
bridge_write_session(out_dir)
