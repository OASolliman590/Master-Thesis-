source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "ggplot2", "matrixStats"))
bridge <- bridge_config()
cfg <- bridge$config
mode <- as.character(cfg$mode)
rep <- cfg$representation
if (mode %in% c("qc", "pca") && identical(rep$unit, "counts")) {
  bridge_require(c("DESeq2", "SummarizedExperiment"))
}
out_dir <- bridge$output_dir
`%||%` <- function(value, fallback) if (is.null(value)) fallback else value

read_expression <- function(path) {
  table <- read.delim(path, check.names = FALSE, stringsAsFactors = FALSE,
                      na.strings = c("", "NA"), quote = "\"", comment.char = "")
  if (ncol(table) < 4L) stop("Expression input needs one feature column and at least three samples")
  features <- as.character(table[[1L]])
  if (anyNA(features) || any(!nzchar(features)) || anyDuplicated(features)) {
    stop("Expression feature identifiers must be unique and non-empty")
  }
  matrix <- as.matrix(table[, -1L, drop = FALSE])
  suppressWarnings(storage.mode(matrix) <- "double")
  if (any(is.infinite(matrix), na.rm = TRUE)) stop("Expression values must be finite or missing")
  rownames(matrix) <- features
  matrix
}

read_metadata <- function(path, sample_ids) {
  metadata <- read.delim(path, check.names = FALSE, stringsAsFactors = FALSE,
                         na.strings = c("", "NA"), quote = "\"", comment.char = "")
  if (!"sample_id" %in% names(metadata) || anyDuplicated(metadata$sample_id)) {
    stop("Sample metadata needs unique sample_id values")
  }
  index <- match(sample_ids, metadata$sample_id)
  if (anyNA(index) || nrow(metadata) != length(sample_ids)) {
    stop("Expression columns and sample metadata do not align one-to-one")
  }
  metadata <- metadata[index, , drop = FALSE]
  rownames(metadata) <- sample_ids
  metadata
}

analysis_matrix <- function(raw, representation) {
  if (identical(representation$unit, "counts")) {
    if (anyNA(raw) || any(raw < 0) || any(raw != round(raw))) {
      stop("DESeq2 VST requires finite, non-negative integer counts")
    }
    counts <- round(raw)
    storage.mode(counts) <- "integer"
    keep <- rowSums(counts) > 0
    if (sum(keep) < 2L) stop("At least two non-zero count features are required")
    count_data <- counts[keep, , drop = FALSE]
    sample_data <- data.frame(intercept = factor(rep("all", ncol(count_data))),
                              row.names = colnames(count_data))
    dds <- DESeq2::DESeqDataSetFromMatrix(countData = count_data,
                                          colData = sample_data,
                                          design = ~ 1)
    transformed <- DESeq2::vst(dds, blind = TRUE,
                               nsub = min(1000L, nrow(count_data)))
    return(SummarizedExperiment::assay(transformed))
  }
  transform <- as.character(representation$transform)
  if (identical(transform, "linear")) {
    if (any(raw < 0, na.rm = TRUE)) stop("Linear expression values must be non-negative")
    raw <- log2(raw + 1)
  }
  raw
}

robust_outlier_flags <- function(values) {
  valid <- values[is.finite(values)]
  if (!length(valid)) stop("Robust outlier calculation needs finite values")
  center <- stats::median(valid)
  raw_mad <- stats::median(abs(valid - center))
  scaled_mad <- 1.4826 * raw_mad
  tolerance <- if (raw_mad <= sqrt(.Machine$double.eps) * max(1, abs(center))) {
    sqrt(.Machine$double.eps) * max(1, abs(center))
  } else {
    0
  }
  flags <- !is.finite(values) | abs(values - center) > 3 * scaled_mad + tolerance
  list(center = center, scaled_mad = scaled_mad, tolerance = tolerance, flags = flags)
}

prepare_pca <- function(raw, metadata, representation, top_n = 2000L) {
  transformed <- analysis_matrix(raw, representation)
  complete <- rowSums(!is.finite(transformed)) == 0L
  transformed <- transformed[complete, , drop = FALSE]
  if (nrow(transformed) < 2L || ncol(transformed) < 3L) {
    stop("PCA requires at least two complete features and three samples")
  }
  feature_variance <- matrixStats::rowVars(transformed)
  variable <- is.finite(feature_variance) & feature_variance > 0
  transformed <- transformed[variable, , drop = FALSE]
  feature_variance <- feature_variance[variable]
  if (nrow(transformed) < 2L) stop("PCA needs at least two non-constant complete features")
  ordering <- order(-feature_variance, rownames(transformed), method = "radix")
  top_n <- as.integer(top_n)
  selected <- ordering[seq_len(min(top_n, length(ordering)))]
  pca_matrix <- transformed[selected, , drop = FALSE]
  fit <- stats::prcomp(t(pca_matrix), center = TRUE, scale. = FALSE)
  if (ncol(fit$x) < 2L) stop("PCA did not produce two components")
  explained <- fit$sdev^2 / sum(fit$sdev^2)
  if (abs(sum(explained) - 1) < 1e-10) {
    explained[length(explained)] <- explained[length(explained)] + 1 - sum(explained)
  }
  if (sum(explained) > 1 + 1e-10) stop("PCA variance explained exceeds one")
  list(raw = raw, transformed = transformed, pca_matrix = pca_matrix,
       fit = fit, explained = explained, complete_feature_count = sum(complete),
       variable_feature_count = nrow(transformed), selected_feature_count = length(selected),
       metadata = metadata)
}

qc_outputs <- function(raw, prepared, metadata) {
  n_features <- nrow(raw)
  n_samples <- ncol(raw)
  counts <- identical(rep$unit, "counts")
  if (counts) {
    depth <- colSums(raw, na.rm = TRUE)
    column_total <- rep(NA_real_, n_samples)
    log_depth <- log2(depth)
    depth_name <- "log2_library_size"
    depth_outlier <- robust_outlier_flags(log_depth)$flags
  } else {
    depth <- rep(NA_real_, n_samples)
    column_total <- colSums(raw, na.rm = TRUE)
    log_depth <- rep(NA_real_, n_samples)
    depth_name <- "not_applicable"
    depth_outlier <- rep(NA, n_samples)
  }
  medians <- apply(raw, 2L, stats::median, na.rm = TRUE)
  detected <- colSums(!is.na(raw) & raw != 0)
  zeros <- colSums(!is.na(raw) & raw == 0)
  missing <- colSums(is.na(raw))
  pc <- prepared$fit$x[, 1:2, drop = FALSE]
  pc1_outlier <- robust_outlier_flags(pc[, 1L])$flags
  pc2_outlier <- robust_outlier_flags(pc[, 2L])$flags
  pc12_distance <- sqrt(rowSums(sweep(pc, 2L, apply(pc, 2L, stats::median), "-")^2))
  pc12_distance_outlier <- robust_outlier_flags(pc12_distance)$flags
  library_flag_for_union <- if (counts) depth_outlier else rep(FALSE, n_samples)
  any_outlier <- pc1_outlier | pc2_outlier | pc12_distance_outlier | library_flag_for_union
  qc <- data.frame(
    sample_id = colnames(raw),
    library_size = if (counts) unname(depth) else NA_real_,
    log_library_size = if (counts) unname(log_depth) else NA_real_,
    column_total = if (counts) NA_real_ else unname(column_total),
    column_median = unname(medians),
    detected_genes = unname(detected),
    fraction_zeros = unname(zeros / n_features),
    fraction_missing = unname(missing / n_features),
    pc1 = unname(pc[, 1L]),
    pc2 = unname(pc[, 2L]),
    pc12_distance = unname(pc12_distance),
    pc1_outlier = unname(pc1_outlier),
    pc2_outlier = unname(pc2_outlier),
    pc12_distance_outlier = unname(pc12_distance_outlier),
    library_size_outlier = unname(depth_outlier),
    outlier_flag = unname(any_outlier),
    check.names = FALSE
  )
  correlation <- stats::cor(prepared$transformed, method = "pearson",
                            use = "pairwise.complete.obs")
  correlations <- correlation[upper.tri(correlation)]
  correlations <- correlations[is.finite(correlations)]
  correlation_summary <- data.frame(
    pair_count = length(correlations),
    mean = if (length(correlations)) mean(correlations) else NA_real_,
    median = if (length(correlations)) stats::median(correlations) else NA_real_,
    minimum = if (length(correlations)) min(correlations) else NA_real_,
    maximum = if (length(correlations)) max(correlations) else NA_real_
  )
  list(qc = qc, correlation = correlation_summary,
       summary = list(
         sample_count = n_samples,
         feature_count = n_features,
         pca_feature_count = prepared$selected_feature_count,
         outlier_count = sum(qc$outlier_flag),
         pc1_outlier_count = sum(pc1_outlier),
         pc2_outlier_count = sum(pc2_outlier),
         pc_component_outlier_count = sum(pc1_outlier | pc2_outlier),
         pc12_distance_outlier_count = sum(pc12_distance_outlier),
         library_size_outlier_count = if (counts) sum(depth_outlier) else 0L,
         depth_metric = depth_name,
         sample_correlation = as.list(correlation_summary[1L, , drop = TRUE])
       ))
}

write_table <- function(table, filename) {
  utils::write.table(table, file = file.path(out_dir, filename), sep = "\t",
                     row.names = FALSE, quote = FALSE, na = "NA")
}

if (identical(mode, "panels")) {
  scores <- read.delim(bridge$inputs$scores, check.names = FALSE,
                       stringsAsFactors = FALSE, na.strings = c("", "NA"))
  if (!"sample_id" %in% names(scores)) stop("Panel score table needs a sample_id column")
  score_names <- unlist(cfg$score_names, use.names = FALSE)
  if (!all(score_names %in% names(scores))) stop("Panel score table is missing a requested score")
  numeric_scores <- as.data.frame(lapply(scores[score_names], as.numeric), check.names = FALSE)
  names(numeric_scores) <- score_names
  correlations <- if (nrow(numeric_scores) >= 2L) {
    stats::cor(numeric_scores, method = "spearman", use = "pairwise.complete.obs")
  } else {
    matrix(NA_real_, nrow = length(score_names), ncol = length(score_names),
           dimnames = list(score_names, score_names))
  }
  correlation_table <- data.frame(score = rownames(correlations), correlations,
                                   check.names = FALSE)
  write_table(correlation_table, "correlation.tsv")
  long <- expand.grid(score_x = score_names, score_y = score_names,
                      KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE)
  long$rho <- as.vector(correlations)
  long$score_x <- factor(long$score_x, levels = score_names)
  long$score_y <- factor(long$score_y, levels = rev(score_names))
  plot <- ggplot2::ggplot(long, ggplot2::aes(x = score_x, y = score_y, fill = rho)) +
    ggplot2::geom_tile(color = "white", linewidth = 0.15) +
    ggplot2::scale_fill_gradient2(limits = c(-1, 1), midpoint = 0,
                                  low = "#3B6FB6", mid = "white", high = "#B23A48",
                                  na.value = "grey90", name = "Spearman\nrho") +
    ggplot2::coord_fixed() +
    ggplot2::labs(x = NULL, y = NULL, title = "Within-dataset panel-score correlations") +
    ggplot2::theme_minimal(base_size = 9) +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
                   panel.grid = ggplot2::element_blank())
  ggplot2::ggsave(file.path(out_dir, "correlation_heatmap.png"), plot,
                  width = 9, height = 8, units = "in", dpi = 160, bg = "white")
  jsonlite::write_json(list(sample_count = nrow(scores), score_count = length(score_names)),
                       file.path(out_dir, "scores_summary.json"), auto_unbox = TRUE,
                       pretty = TRUE, na = "null")
} else {
  raw <- read_expression(bridge$inputs$expression)
  metadata <- read_metadata(bridge$inputs$sample_metadata, colnames(raw))
  prepared <- prepare_pca(raw, metadata, rep,
                          top_n = cfg$top_variance_genes %||% 2000L)
  if (identical(mode, "qc")) {
    qc <- qc_outputs(raw, prepared, metadata)
    write_table(qc$qc, "qc.tsv")
    write_table(qc$correlation, "correlation_summary.tsv")
    jsonlite::write_json(qc$summary, file.path(out_dir, "qc_summary.json"),
                         auto_unbox = TRUE, pretty = TRUE, na = "null")
  } else if (identical(mode, "pca")) {
    scores <- as.data.frame(prepared$fit$x, check.names = FALSE)
    scores$sample_id <- rownames(scores)
    scores <- scores[, c("sample_id", setdiff(names(scores), "sample_id")), drop = FALSE]
    write_table(scores, "pca.tsv")
    variance <- data.frame(component = paste0("PC", seq_along(prepared$explained)),
                           variance_explained = unname(prepared$explained))
    write_table(variance, "variance_explained.tsv")
    summary <- list(
      sample_count = ncol(raw),
      feature_count = nrow(raw),
      complete_feature_count = prepared$complete_feature_count,
      variable_feature_count = prepared$variable_feature_count,
      top_variance_gene_count = prepared$selected_feature_count,
      variance_explained_pc1 = unname(prepared$explained[[1L]]),
      variance_explained_pc2 = unname(prepared$explained[[2L]]),
      variance_explained_pc1_pc2 = sum(prepared$explained[1:2]),
      analysis_transform = if (identical(rep$unit, "counts")) "DESeq2_vst_blind" else rep$transform
    )
    jsonlite::write_json(summary, file.path(out_dir, "pca_summary.json"),
                         auto_unbox = TRUE, pretty = TRUE, na = "null")

    covariates <- unlist(cfg$plot_covariates, use.names = FALSE)
    if ("response" %in% covariates && !isTRUE(cfg$response_coloring_allowed)) {
      stop("Response-colored PCA requires allow_outcomes")
    }
    plot_data <- cbind(as.data.frame(prepared$fit$x[, 1:2, drop = FALSE]), metadata)
    for (covariate in covariates) {
      if (!covariate %in% names(plot_data)) next
      plot_data[[covariate]] <- factor(ifelse(is.na(plot_data[[covariate]]) |
                                                !nzchar(as.character(plot_data[[covariate]])),
                                              "Unknown", as.character(plot_data[[covariate]])))
      plot <- ggplot2::ggplot(plot_data,
                              ggplot2::aes(x = PC1, y = PC2, color = .data[[covariate]])) +
        ggplot2::geom_point(size = 2.4, alpha = 0.9) +
        ggplot2::labs(x = "PC1", y = "PC2", color = covariate,
                      title = paste("PCA colored by", covariate)) +
        ggplot2::theme_minimal(base_size = 11)
      ggplot2::ggsave(file.path(out_dir, paste0("pca_", covariate, ".png")), plot,
                      width = 7, height = 5, units = "in", dpi = 160, bg = "white")
    }
  } else {
    stop("Unsupported bulk_qc_pca mode")
  }
}

bridge_write_session(out_dir)
