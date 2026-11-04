source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "DESeq2", "SummarizedExperiment", "ggplot2"))
bridge <- bridge_config()
cfg <- bridge$config
rep <- cfg$representation
if (!identical(cfg$engine, "deseq2") || !identical(rep$unit, "counts") ||
    !identical(rep$transform, "linear")) {
  stop("DESeq2 accepts only the declared linear integer-count representation")
}
out_dir <- bridge$output_dir

table <- read.delim(bridge$inputs$expression, check.names = FALSE,
                    stringsAsFactors = FALSE, na.strings = c("", "NA"),
                    quote = "\"", comment.char = "")
if (ncol(table) < 4L) stop("Expression input needs one feature column and at least three samples")
features <- as.character(table[[1L]])
if (anyNA(features) || any(!nzchar(features)) || anyDuplicated(features)) {
  stop("Expression feature identifiers must be unique and non-empty")
}
counts <- as.matrix(table[, -1L, drop = FALSE])
suppressWarnings(storage.mode(counts) <- "double")
if (anyNA(counts) || any(!is.finite(counts)) || any(counts < 0) || any(counts != round(counts))) {
  stop("DESeq2 input must contain finite, non-negative integer counts")
}
rownames(counts) <- features
storage.mode(counts) <- "integer"

metadata <- read.delim(bridge$inputs$sample_metadata, check.names = FALSE,
                       stringsAsFactors = FALSE, na.strings = c("", "NA"),
                       quote = "\"", comment.char = "")
if (!all(c("sample_id", "response") %in% names(metadata)) || anyDuplicated(metadata$sample_id)) {
  stop("DE metadata needs unique sample_id and response columns")
}
columns <- match(metadata$sample_id, colnames(counts))
if (anyNA(columns) || nrow(metadata) > ncol(counts)) stop("DE metadata do not match expression columns")
counts <- counts[, columns, drop = FALSE]
rownames(metadata) <- metadata$sample_id
metadata$response <- factor(metadata$response, levels = c("NR", "R"))
if (anyNA(metadata$response) || length(unique(metadata$response)) != 2L) {
  stop("DE requires eligible R and NR samples")
}
include_batch <- isTRUE(cfg$include_batch)
if (include_batch) {
  if (!"batch" %in% names(metadata)) stop("Batch adjustment was requested without a batch field")
  metadata$batch[is.na(metadata$batch) | !nzchar(metadata$batch)] <- "UNKNOWN"
  metadata$batch <- factor(metadata$batch)
  if (nlevels(metadata$batch) < 2L) stop("Batch covariate has fewer than two levels")
  design_formula <- ~ batch + response
} else {
  design_formula <- ~ response
}
design_matrix <- stats::model.matrix(design_formula, data = metadata)
if (qr(design_matrix)$rank < ncol(design_matrix)) {
  stop("DE design is not full rank; response is confounded with the recorded batch")
}

keep <- rowSums(counts) > 0
if (sum(keep) < 2L) stop("At least two non-zero genes are required for DE")
counts <- counts[keep, , drop = FALSE]
dds <- DESeq2::DESeqDataSetFromMatrix(countData = counts,
                                      colData = metadata,
                                      design = design_formula)
dds <- DESeq2::DESeq(dds, quiet = TRUE)
result <- DESeq2::results(dds, contrast = c("response", "R", "NR"),
                          independentFiltering = FALSE,
                          pAdjustMethod = "BH")
de <- data.frame(
  gene = rownames(result),
  log2FC = result$log2FoldChange,
  SE = result$lfcSE,
  statistic = result$stat,
  p = result$pvalue,
  q = result$padj,
  check.names = FALSE
)
utils::write.table(de, file.path(out_dir, "de.tsv"), sep = "\t",
                    row.names = FALSE, quote = FALSE, na = "NA")

plot_data <- de[is.finite(de$log2FC) & is.finite(de$p) & is.finite(de$q), , drop = FALSE]
plot_data$minus_log10_p <- -log10(pmax(plot_data$p, .Machine$double.xmin))
plot_data$minus_log10_q <- -log10(pmax(plot_data$q, .Machine$double.xmin))
volcano <- ggplot2::ggplot(plot_data,
                           ggplot2::aes(x = log2FC, y = minus_log10_p,
                                        color = minus_log10_q)) +
  ggplot2::geom_point(size = 1.4, alpha = 0.75) +
  ggplot2::scale_color_gradient(low = "grey75", high = "firebrick",
                                name = "-log10(BH q)") +
  ggplot2::labs(x = "Unshrunk log2 fold change (R - NR)", y = "-log10(p)",
                title = paste("Differential expression:", cfg$endpoint)) +
  ggplot2::theme_minimal(base_size = 11)
ggplot2::ggsave(file.path(out_dir, "volcano.png"), volcano,
                width = 7, height = 5, units = "in", dpi = 160, bg = "white")

summary <- list(
  engine = "DESeq2",
  effect = "unshrunk_log2_fold_change_R_minus_NR",
  endpoint = cfg$endpoint,
  sample_count = nrow(metadata),
  responder_count = sum(metadata$response == "R"),
  non_responder_count = sum(metadata$response == "NR"),
  excluded_count = as.integer(cfg$input_sample_count - nrow(metadata)),
  excluded_reason_counts = cfg$excluded_reason_counts,
  batch_adjusted = include_batch,
  gene_count = nrow(de)
)
jsonlite::write_json(summary, file.path(out_dir, "de_summary.json"),
                     auto_unbox = TRUE, pretty = TRUE, na = "null")
bridge_write_session(out_dir)
