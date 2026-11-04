source("R/bridge.R")
bridge_require(c(DESeq2 = "1.52.0", digest = "0.6.39"))
bridge_require(c("jsonlite", "BiocManager"))
config <- bridge_config()

authorization <- config$config$authorization
if (is.null(authorization) || is.null(authorization$data_classification)) {
  stop("SC-3 requires explicit outcome authorization or verified synthetic provenance")
}
classification <- as.character(authorization$data_classification)
if (identical(classification, "real")) {
  if (!isTRUE(authorization$allow_outcomes)) {
    stop("SC-3 real outcomes require explicit allow_outcomes=TRUE")
  }
} else if (!identical(classification, "synthetic")) {
  stop("SC-3 authorization has an unsupported data classification")
}

clinical <- read.delim(config$inputs$clinical, check.names = FALSE, stringsAsFactors = FALSE,
  na.strings = c("NA", ""))
if (!"cohort" %in% colnames(clinical)) stop("SC-3 clinical input requires a cohort field")

if (identical(classification, "synthetic")) {
  manifest_path <- as.character(authorization$provenance_manifest %||% "")
  if (!nzchar(manifest_path) || !file.exists(manifest_path)) {
    stop("SC-3 synthetic provenance manifest is missing")
  }
  manifest <- jsonlite::fromJSON(manifest_path, simplifyVector = FALSE)
  if (!identical(as.integer(manifest$manifest_version), 1L) ||
      !identical(manifest$producer, "tools.a_meta.synthetic_fixture") ||
      !identical(manifest$data_classification, "synthetic") ||
      !identical(manifest$kind, "sc3_r_input")) {
    stop("SC-3 synthetic provenance header is invalid")
  }
  script_argument <- grep("^--file=", commandArgs(FALSE), value = TRUE)
  if (length(script_argument) != 1L) stop("Cannot locate the SC-3 repository root for provenance checks")
  script_path <- normalizePath(sub("^--file=", "", script_argument[[1]]), mustWork = TRUE)
  repo_root <- normalizePath(file.path(dirname(script_path), "../.."), mustWork = TRUE)
  registry <- read.delim(file.path(repo_root, "docs/cohorts/REGISTRY.tsv"), stringsAsFactors = FALSE)
  lin_cohorts <- read.delim(file.path(repo_root, "tools/sc/lin_cohort_map.tsv"), stringsAsFactors = FALSE)$cohort
  real_cohorts <- unique(c(registry$cohort_id, lin_cohorts, "prostate_hormone_naive_atlas"))
  cohort_ids <- sort(unique(as.character(clinical$cohort)))
  if (length(intersect(cohort_ids, real_cohorts))) stop("Synthetic provenance contradicts a real cohort")
  declared_cohorts <- sort(unlist(manifest$cohort_ids, use.names = FALSE))
  if (!identical(cohort_ids, declared_cohorts)) stop("Synthetic manifest cohort IDs do not match clinical profiles")
  counts_hash <- digest::digest(config$inputs$counts, algo = "sha256", file = TRUE)
  clinical_hash <- digest::digest(config$inputs$clinical, algo = "sha256", file = TRUE)
  payload <- paste0("counts:", counts_hash, "\nclinical:", clinical_hash,
    "\ncohorts:", paste(cohort_ids, collapse = ","), "\n")
  payload_hash <- digest::digest(payload, algo = "sha256", serialize = FALSE)
  if (!identical(manifest$payload_sha256, payload_hash)) stop("SC-3 synthetic provenance does not match input hashes")
}

counts_frame <- read.delim(config$inputs$counts, check.names = FALSE, row.names = 1,
  na.strings = c("NA", ""), stringsAsFactors = FALSE)
if (anyDuplicated(rownames(counts_frame)) || anyDuplicated(colnames(counts_frame))) {
  stop("SC-3 count gene and profile identities must be unique")
}
required <- c("profile_id", "patient_id", "sample_id", "cohort", "compartment", "endpoint_family",
  "outcome_label", "eligible", "sc3_group_id")
if (length(setdiff(required, colnames(clinical)))) stop("SC-3 clinical profiles are missing required grouping fields")
if (anyDuplicated(clinical$profile_id)) stop("SC-3 profile IDs must be unique")
if (!all(clinical$profile_id %in% colnames(counts_frame))) stop("Expression columns do not align to clinical profiles")
if (anyNA(clinical$patient_id) || anyNA(clinical$sample_id) || any(!nzchar(clinical$patient_id)) ||
    any(!nzchar(clinical$sample_id))) stop("SC-3 patient and specimen IDs must be non-empty")
if ("response" %in% colnames(clinical)) {
  expansion <- clinical$endpoint_family == "expansion"
  response_values <- toupper(trimws(as.character(clinical$response)))
  response_values[is.na(response_values)] <- ""
  if (any(expansion & response_values %in% c("R", "NR"))) {
    stop("T-cell expansion labels cannot be stored as clinical response")
  }
}

validated_groups <- config$config$validated_groups
if (is.null(validated_groups) || !length(validated_groups)) stop("SC-3 requires validated groups from Python")
expected_ids <- vapply(validated_groups, function(row) as.character(row$group_id), character(1))
if (anyDuplicated(expected_ids) || !setequal(unique(clinical$sc3_group_id), expected_ids)) {
  stop("SC-3 group IDs do not match the validated Python group contract")
}
groups <- split(seq_len(nrow(clinical)), clinical$sc3_group_id)
de_rows <- list()
for (expected in validated_groups) {
  group_id <- as.character(expected$group_id)
  selected <- groups[[group_id]]
  if (is.null(selected)) stop("A validated SC-3 group is absent from clinical profiles")
  frame <- clinical[selected, , drop = FALSE]
  if (length(unique(frame$cohort)) != 1L || length(unique(frame$compartment)) != 1L ||
      length(unique(frame$endpoint_family)) != 1L ||
      !identical(as.character(frame$cohort[[1]]), as.character(expected$cohort)) ||
      !identical(as.character(frame$compartment[[1]]), as.character(expected$compartment)) ||
      !identical(as.character(frame$endpoint_family[[1]]), as.character(expected$endpoint_family))) {
    stop("SC-3 group identity differs from the validated Python contract")
  }
  if (anyDuplicated(frame$patient_id)) stop("SC-3 requires one profile per patient in every analysis group")
  if (anyDuplicated(frame$sample_id)) stop("SC-3 requires unique specimens in every analysis group")
  if (any(!tolower(as.character(frame$eligible)) %in% c("true", "1", "yes")) ||
      any(!frame$outcome_label %in% c("R", "NR"))) {
    stop("SC-3 validated groups may contain only eligible R/NR profiles")
  }
  n_r <- length(unique(frame$patient_id[frame$outcome_label == "R"]))
  n_nr <- length(unique(frame$patient_id[frame$outcome_label == "NR"]))
  profile_hash <- digest::digest(paste(sort(as.character(frame$profile_id)), collapse = "\n"),
    algo = "sha256", serialize = FALSE)
  if (n_r != as.integer(expected$n_R) || n_nr != as.integer(expected$n_NR) ||
      nrow(frame) != as.integer(expected$profile_count) ||
      !identical(profile_hash, as.character(expected$profile_ids_sha256))) {
    stop("SC-3 arm counts or profile membership differ from the validated Python contract")
  }
  if (n_r < 3L || n_nr < 3L) stop("SC-3 requires at least three distinct patients per arm")

  profile_ids <- as.character(frame$profile_id)
  current <- as.matrix(counts_frame[, profile_ids, drop = FALSE])
  complete <- rowSums(is.na(current)) == 0L
  current <- current[complete, , drop = FALSE]
  nonzero <- rowSums(current) > 0
  current <- current[nonzero, , drop = FALSE]
  if (nrow(current) < 2L) next
  if (any(!is.finite(current)) || any(current < 0) || any(current != trunc(current))) {
    stop("DESeq2 input must contain non-negative integer UMIs")
  }
  storage.mode(current) <- "integer"
  col_data <- data.frame(response = factor(frame$outcome_label, levels = c("NR", "R")), row.names = profile_ids)
  if (anyNA(col_data$response)) stop("Response levels are not exactly R and NR")
  attempt <- tryCatch({
    dds <- DESeq2::DESeqDataSetFromMatrix(current, colData = col_data, design = ~ response)
    dds <- DESeq2::DESeq(dds, quiet = TRUE)
    result <- as.data.frame(DESeq2::results(dds, contrast = c("response", "R", "NR"), pAdjustMethod = "BH"))
    result$gene <- rownames(result)
    result$comparison_id <- group_id
    result$cohort <- as.character(frame$cohort[[1]])
    result$compartment <- as.character(frame$compartment[[1]])
    result$endpoint_family <- as.character(frame$endpoint_family[[1]])
    result$status <- "ok"
    result$reason <- ""
    result[, c("comparison_id", "cohort", "compartment", "endpoint_family", "gene", "baseMean",
      "log2FoldChange", "lfcSE", "stat", "pvalue", "padj", "status", "reason")]
  }, error = function(error) error)
  if (inherits(attempt, "error")) {
    stop("DESeq2 failed for validated SC-3 group ", group_id, ": ", conditionMessage(attempt))
  }
  de_rows[[length(de_rows) + 1L]] <- attempt
}
de_results <- if (length(de_rows)) do.call(rbind, de_rows) else data.frame(
  comparison_id = character(), cohort = character(), compartment = character(), endpoint_family = character(), gene = character(),
  baseMean = numeric(), log2FoldChange = numeric(), lfcSE = numeric(), stat = numeric(), pvalue = numeric(), padj = numeric(),
  status = character(), reason = character(), stringsAsFactors = FALSE
)
de_refusals <- data.frame(cohort = character(), compartment = character(), endpoint_family = character(), n_R = integer(),
  n_NR = integer(), reason = character(), detail = character(), stringsAsFactors = FALSE)
write.table(de_results, file.path(config$output_dir, "de_results.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
write.table(de_refusals, file.path(config$output_dir, "de_refusals.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
bridge_write_session(config$output_dir)
