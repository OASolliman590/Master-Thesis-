source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "limma", "ggplot2"))
bridge <- bridge_config()
cfg <- bridge$config
rep <- cfg$representation
if (!identical(cfg$engine, "limma")) stop("limma-trend requires a non-count representation")
out_dir <- bridge$output_dir

table <- read.delim(bridge$inputs$expression, check.names = FALSE,
                    stringsAsFactors = FALSE, na.strings = c("", "NA"),
                    quote = "\"", comment.char = "")
if (ncol(table) < 4L) stop("Expression input needs one feature column and at least three samples")
features <- as.character(table[[1L]])
if (anyNA(features) || any(!nzchar(features)) || anyDuplicated(features)) {
  stop("Expression feature identifiers must be unique and non-empty")
}
expression <- as.matrix(table[, -1L, drop = FALSE])
suppressWarnings(storage.mode(expression) <- "double")
if (any(is.infinite(expression), na.rm = TRUE)) stop("Expression values must be finite or missing")
rownames(expression) <- features

transform <- as.character(rep$transform)
if (identical(transform, "linear")) {
  if (any(expression < 0, na.rm = TRUE)) stop("Linear expression values must be non-negative")
  expression <- log2(expression + 1)
} else if (!transform %in% c("log2", "log2p1")) {
  stop("limma-trend needs a declared linear, log2, or log2p1 representation")
}

metadata <- read.delim(bridge$inputs$sample_metadata, check.names = FALSE,
                       stringsAsFactors = FALSE, na.strings = c("", "NA"),
                       quote = "\"", comment.char = "")
if (!all(c("sample_id", "response") %in% names(metadata)) || anyDuplicated(metadata$sample_id)) {
  stop("DE metadata needs unique sample_id and response columns")
}
columns <- match(metadata$sample_id, colnames(expression))
if (anyNA(columns) || nrow(metadata) > ncol(expression)) stop("DE metadata do not match expression columns")
expression <- expression[, columns, drop = FALSE]
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
  design <- stats::model.matrix(~ batch + response, data = metadata)
} else {
  design <- stats::model.matrix(~ response, data = metadata)
}
if (qr(design)$rank < ncol(design)) {
  stop("DE design is not full rank; response is confounded with the recorded batch")
}
response_coefficient <- which(colnames(design) == "responseR")
if (length(response_coefficient) != 1L) stop("Could not identify the R versus NR coefficient")

fit <- limma::lmFit(expression, design)
fit <- limma::eBayes(fit, trend = TRUE)
coefficient <- response_coefficient[[1L]]
standard_error <- fit$stdev.unscaled[, coefficient] * sqrt(fit$s2.post)
p <- fit$p.value[, coefficient]
de <- data.frame(
  gene = rownames(expression),
  log2FC = fit$coefficients[, coefficient],
  SE = standard_error,
  statistic = fit$t[, coefficient],
  p = p,
  q = stats::p.adjust(p, method = "BH"),
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
  engine = "limma-trend",
  effect = "unshrunk_log2_scale_coefficient_R_minus_NR",
  endpoint = cfg$endpoint,
  sample_count = nrow(metadata),
  responder_count = sum(metadata$response == "R"),
  non_responder_count = sum(metadata$response == "NR"),
  excluded_count = as.integer(cfg$input_sample_count - nrow(metadata)),
  excluded_reason_counts = cfg$excluded_reason_counts,
  batch_adjusted = include_batch,
  expression_transform = if (identical(transform, "linear")) "log2(x+1)" else transform,
  gene_count = nrow(de)
)
jsonlite::write_json(summary, file.path(out_dir, "de_summary.json"),
                     auto_unbox = TRUE, pretty = TRUE, na = "null")
bridge_write_session(out_dir)
