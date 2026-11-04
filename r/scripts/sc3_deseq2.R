source("R/bridge.R")
bridge_require(c("DESeq2", "jsonlite", "BiocManager"))
config <- bridge_config()
counts_frame <- read.delim(config$inputs$counts, check.names = FALSE, row.names = 1,
  na.strings = c("NA", ""), stringsAsFactors = FALSE)
clinical <- read.delim(config$inputs$clinical, check.names = FALSE, stringsAsFactors = FALSE,
  na.strings = c("NA", ""))
if (!"profile_id" %in% colnames(clinical) || anyDuplicated(clinical$profile_id)) stop("Clinical profile IDs must be unique")
if (!all(clinical$profile_id %in% colnames(counts_frame))) stop("Expression columns do not align to clinical profiles")
if (!all(c("cohort", "compartment", "endpoint_family", "outcome_label", "eligible") %in% colnames(clinical))) {
  stop("Clinical profiles are missing SC-3 grouping fields")
}
eligible_text <- tolower(as.character(clinical$eligible))
eligible <- eligible_text %in% c("true", "1") & clinical$outcome_label %in% c("R", "NR") & !is.na(clinical$endpoint_family)
dimensions <- interaction(clinical$cohort, clinical$compartment, clinical$endpoint_family, drop = TRUE, lex.order = TRUE)
groups <- split(which(eligible), dimensions[eligible])
de_rows <- list()
refusal_rows <- list()
for (index in seq_along(groups)) {
  selected <- groups[[index]]
  frame <- clinical[selected, , drop = FALSE]
  cohort <- as.character(frame$cohort[[1]])
  compartment <- as.character(frame$compartment[[1]])
  endpoint_family <- as.character(frame$endpoint_family[[1]])
  n_r <- sum(frame$outcome_label == "R")
  n_nr <- sum(frame$outcome_label == "NR")
  if (n_r < 3L || n_nr < 3L) {
    refusal_rows[[length(refusal_rows) + 1L]] <- data.frame(
      cohort = cohort, compartment = compartment, endpoint_family = endpoint_family,
      n_R = n_r, n_NR = n_nr, reason = "fewer_than_three_patients_per_arm", detail = "", stringsAsFactors = FALSE
    )
    next
  }
  profile_ids <- as.character(frame$profile_id)
  current <- as.matrix(counts_frame[, profile_ids, drop = FALSE])
  complete <- rowSums(is.na(current)) == 0L
  current <- current[complete, , drop = FALSE]
  nonzero <- rowSums(current) > 0
  current <- current[nonzero, , drop = FALSE]
  if (nrow(current) < 2L) {
    refusal_rows[[length(refusal_rows) + 1L]] <- data.frame(
      cohort = cohort, compartment = compartment, endpoint_family = endpoint_family,
      n_R = n_r, n_NR = n_nr, reason = "fewer_than_two_complete_nonzero_genes", detail = "", stringsAsFactors = FALSE
    )
    next
  }
  if (any(current < 0) || any(abs(current - round(current)) > 1e-8)) stop("DESeq2 input must contain non-negative integer UMIs")
  col_data <- data.frame(response = factor(frame$outcome_label, levels = c("NR", "R")), row.names = profile_ids)
  if (anyNA(col_data$response)) stop("Response levels are not exactly R and NR")
  comparison_id <- paste(cohort, compartment, endpoint_family, sep = "__")
  attempt <- tryCatch({
    dds <- DESeq2::DESeqDataSetFromMatrix(round(current), colData = col_data, design = ~ response)
    dds <- DESeq2::DESeq(dds, quiet = TRUE)
    result <- as.data.frame(DESeq2::results(dds, contrast = c("response", "R", "NR"), pAdjustMethod = "BH"))
    result$gene <- rownames(result)
    result$comparison_id <- comparison_id
    result$cohort <- cohort
    result$compartment <- compartment
    result$endpoint_family <- endpoint_family
    result$status <- "ok"
    result$reason <- ""
    result[, c("comparison_id", "cohort", "compartment", "endpoint_family", "gene", "baseMean",
      "log2FoldChange", "lfcSE", "stat", "pvalue", "padj", "status", "reason")]
  }, error = function(error) error)
  if (inherits(attempt, "error")) {
    refusal_rows[[length(refusal_rows) + 1L]] <- data.frame(
      cohort = cohort, compartment = compartment, endpoint_family = endpoint_family,
      n_R = n_r, n_NR = n_nr, reason = "deseq2_failed", detail = conditionMessage(attempt), stringsAsFactors = FALSE
    )
  } else {
    de_rows[[length(de_rows) + 1L]] <- attempt
  }
}
de_results <- if (length(de_rows)) do.call(rbind, de_rows) else data.frame(
  comparison_id = character(), cohort = character(), compartment = character(), endpoint_family = character(), gene = character(),
  baseMean = numeric(), log2FoldChange = numeric(), lfcSE = numeric(), stat = numeric(), pvalue = numeric(), padj = numeric(),
  status = character(), reason = character(), stringsAsFactors = FALSE
)
de_refusals <- if (length(refusal_rows)) do.call(rbind, refusal_rows) else data.frame(
  cohort = character(), compartment = character(), endpoint_family = character(), n_R = integer(), n_NR = integer(),
  reason = character(), detail = character()
)
write.table(de_results, file.path(config$output_dir, "de_results.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
write.table(de_refusals, file.path(config$output_dir, "de_refusals.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
bridge_write_session(config$output_dir)
