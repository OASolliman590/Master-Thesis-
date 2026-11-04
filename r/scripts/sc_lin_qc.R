source("R/bridge.R")
bridge_require(c(SeuratObject = "5.4.0"))
bridge_require(c("jsonlite", "BiocManager"))
config <- bridge_config()
metadata <- readRDS(config$inputs$metadata)

first_present <- function(candidates) {
  selected <- candidates[candidates %in% colnames(metadata)]
  if (length(selected)) selected[[1]] else NA_character_
}
umi_column <- first_present(c("nCount_RNA", "nCount_SCT", "nCount"))
gene_column <- first_present(c("nFeature_RNA", "nFeature_SCT", "nFeature"))
mito_column <- first_present(c("percent.mito", "percent.mt", "pct_counts_mt"))
required <- c("cohort", "patient", "sample")
if (length(setdiff(required, colnames(metadata)))) stop("QC metadata is missing cohort, patient, or sample fields")

summarize_metric <- function(values) {
  values <- suppressWarnings(as.numeric(values))
  values <- values[is.finite(values)]
  if (!length(values)) return(c(min = NA_real_, q1 = NA_real_, median = NA_real_, q3 = NA_real_, max = NA_real_))
  c(min = min(values), q1 = unname(quantile(values, .25)), median = median(values),
    q3 = unname(quantile(values, .75)), max = max(values))
}

qc_rows <- list()
for (entry in list(c("UMIs_per_cell", umi_column), c("genes_per_cell", gene_column), c("mitochondrial_percent", mito_column))) {
  metric <- entry[[1]]
  column <- entry[[2]]
  if (is.na(column)) next
  stats <- summarize_metric(metadata[[column]])
  qc_rows[[length(qc_rows) + 1L]] <- data.frame(
    metric = metric, source_column = column, n_cells = nrow(metadata),
    min = stats[["min"]], q1 = stats[["q1"]], median = stats[["median"]],
    q3 = stats[["q3"]], max = stats[["max"]], filtering_applied = FALSE,
    flag_value = NA_character_,
    stringsAsFactors = FALSE
  )
}
flag_columns <- grep("doublet|(^|_)qc($|_)|filter|singlet|outlier", colnames(metadata), ignore.case = TRUE, value = TRUE)
for (column in flag_columns) {
  frequencies <- as.data.frame(table(as.character(metadata[[column]]), useNA = "ifany"), stringsAsFactors = FALSE)
  colnames(frequencies) <- c("value", "cells")
  qc_rows[[length(qc_rows) + 1L]] <- data.frame(
    metric = paste0("author_flag:", column), source_column = column, n_cells = as.integer(frequencies$cells),
    min = NA_real_, q1 = NA_real_, median = NA_real_, q3 = NA_real_, max = NA_real_,
    filtering_applied = FALSE, flag_value = frequencies$value, stringsAsFactors = FALSE
  )
}
qc_summary <- if (length(qc_rows)) do.call(rbind, qc_rows) else data.frame()
qc_summary$n_patients <- length(unique(metadata$patient))
qc_summary$n_samples <- length(unique(metadata$sample))
qc_summary$n_cohorts <- length(unique(metadata$cohort))

sample_key <- interaction(metadata$cohort, metadata$sample, drop = TRUE, lex.order = TRUE)
sample_groups <- split(seq_len(nrow(metadata)), sample_key)
qc_by_sample <- do.call(rbind, lapply(sample_groups, function(index) {
  frame <- metadata[index, , drop = FALSE]
  umi <- if (!is.na(umi_column)) summarize_metric(frame[[umi_column]]) else rep(NA_real_, 5)
  genes <- if (!is.na(gene_column)) summarize_metric(frame[[gene_column]]) else rep(NA_real_, 5)
  data.frame(
    cohort = as.character(frame$cohort[[1]]), sample_id = as.character(frame$sample[[1]]),
    n_cells = nrow(frame), umi_median = umi[["median"]], umi_q1 = umi[["q1"]], umi_q3 = umi[["q3"]],
    genes_median = genes[["median"]], genes_q1 = genes[["q1"]], genes_q3 = genes[["q3"]],
    stringsAsFactors = FALSE
  )
}))
write.table(qc_summary, file.path(config$output_dir, "qc_summary.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
write.table(qc_by_sample, file.path(config$output_dir, "qc_by_cohort.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
bridge_write_session(config$output_dir)
