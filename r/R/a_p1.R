source("R/bridge.R")
bridge <- bridge_config()
bridge_require(c("digest", "jsonlite", "BiocManager"))
source("R/random_streams.R")

if (!identical(as.character(getRversion()), "4.6.1")) {
  stop("A-P1 requires the pinned R 4.6.1 runtime")
}
bioc_version <- as.character(BiocManager::version())
if (!identical(bioc_version, "3.23")) {
  stop("A-P1 requires the pinned Bioconductor 3.23 runtime")
}

input_path <- bridge$inputs$analysis_input
if (is.null(input_path) || length(input_path) != 1L || !file.exists(input_path)) {
  stop("A-P1 R input is missing")
}
input <- utils::read.delim(
  input_path,
  sep = "\t",
  quote = "",
  check.names = FALSE,
  stringsAsFactors = FALSE,
  colClasses = c("character", "character", "character", "numeric", "character")
)
expected_fields <- c("study_id", "patient_key", "category", "score", "score_method")
if (!identical(names(input), expected_fields) || !nrow(input)) {
  stop("A-P1 R input has the wrong exact schema or no rows")
}
if (anyNA(input) || any(!is.finite(input$score)) ||
    any(!input$category %in% c("O", "SD", "PD")) ||
    any(!input$score_method %in% c("CYT", "LEARNED"))) {
  stop("A-P1 R input contains an invalid score, method or category")
}
if (anyDuplicated(input[c("study_id", "patient_key", "score_method")])) {
  stop("A-P1 R input has duplicate method/study/patient keys")
}
patient_categories <- unique(input[c("study_id", "patient_key", "category")])
if (anyDuplicated(patient_categories[c("study_id", "patient_key")])) {
  stop("A-P1 score series disagree on the source category for one study/patient")
}

utf8_order <- function(values) order(enc2utf8(values), method = "radix")
input <- input[order(
  enc2utf8(input$study_id), enc2utf8(input$patient_key), enc2utf8(input$score_method),
  method = "radix"
), , drop = FALSE]

pair_auc <- function(positive, negative) {
  if (!length(positive) || !length(negative)) return(NA_real_)
  comparisons <- outer(positive, negative, function(case, control) {
    ifelse(case > control, 1, ifelse(case == control, 0.5, 0))
  })
  mean(comparisons)
}

endpoint_auc <- function(scores, categories) {
  auc_orr <- pair_auc(scores[categories == "O"], scores[categories %in% c("SD", "PD")])
  auc_dcr <- pair_auc(scores[categories %in% c("O", "SD")], scores[categories == "PD"])
  c(auc_orr = auc_orr, auc_dcr = auc_dcr, delta = auc_dcr - auc_orr)
}

quantile_ends <- function(values) {
  as.numeric(stats::quantile(values, probs = c(0.025, 0.975), names = FALSE, type = 7))
}

assignment_serialization_sha256 <- function(indices) {
  lines <- capture.output(utils::write.table(
    indices, sep = "\t", row.names = FALSE,
    col.names = TRUE, quote = FALSE, na = "NA"
  ))
  payload <- paste0(paste(lines, collapse = "\n"), "\n")
  digest::digest(payload, algo = "sha256", serialize = FALSE)
}

run_stream <- function(stream, role, task_id = NULL) {
  result <- bootstrap_indices_within_study(
    strata = input$category,
    row_key = input$patient_key,
    study = input$study_id,
    series = input$score_method,
    stream = stream,
    task_id = task_id,
    repetitions = 2000L
  )
  assignment <- result$indices
  receipt_assignments <- assignment
  receipt_assignments$stream <- stream
  studies <- unique(input$study_id[utf8_order(input$study_id)])
  methods <- unique(input$score_method[utf8_order(input$score_method)])
  replicate_rows <- list()
  cursor <- 0L

  for (study_id in studies) {
    for (method in methods) {
      data <- input[input$study_id == study_id & input$score_method == method, , drop = FALSE]
      if (!nrow(data)) next
      for (replicate in seq_len(2000L)) {
        selected <- assignment[
          assignment$study == study_id & assignment$series == method &
            assignment$replicate == replicate, , drop = FALSE
        ]
        sampled <- selected$row_index
        metrics <- endpoint_auc(input$score[sampled], input$category[sampled])
        cursor <- cursor + 1L
        replicate_rows[[cursor]] <- data.frame(
          scope = "study",
          score_method = method,
          study_id = study_id,
          stream = stream,
          replicate = replicate,
          auc_orr = metrics[["auc_orr"]],
          auc_dcr = metrics[["auc_dcr"]],
          delta = metrics[["delta"]],
          stringsAsFactors = FALSE
        )
      }
    }
  }
  replicates <- do.call(rbind, replicate_rows)
  synthesis_weights <- bridge$config$synthesis_weights
  collection_ids <- bridge$config$synthesis_collection_ids
  collection_rows <- list()
  collection_cursor <- 0L
  if (length(synthesis_weights)) {
    for (method in methods) {
      raw_weights <- synthesis_weights[[method]]
      if (is.null(raw_weights) || !length(raw_weights)) next
      weights <- unlist(raw_weights, use.names = TRUE)
      if (is.null(names(weights)) || !length(weights)) {
        stop("A-P1 synthesis weights must retain their declared study names")
      }
      positive_studies <- names(weights)[as.numeric(weights) > 0]
      collection_id <- collection_ids[[method]]
      if (is.null(collection_id) || !length(positive_studies)) next
      study_replicates <- replicates[
        replicates$stream == stream & replicates$score_method == method &
          replicates$scope == "study", , drop = FALSE
      ]
      for (replicate in seq_len(2000L)) {
        values <- study_replicates[study_replicates$replicate == replicate, , drop = FALSE]
        positions <- match(positive_studies, values$study_id)
        if (anyNA(positions)) next
        values <- values[positions, , drop = FALSE]
        if (any(!is.finite(values$auc_orr)) || any(!is.finite(values$auc_dcr)) ||
            any(!is.finite(values$delta))) next
        selected_weights <- as.numeric(weights[positive_studies])
        collection_cursor <- collection_cursor + 1L
        collection_rows[[collection_cursor]] <- data.frame(
          scope = "collection",
          score_method = method,
          study_id = as.character(collection_id),
          stream = stream,
          replicate = replicate,
          auc_orr = sum(selected_weights * values$auc_orr),
          auc_dcr = sum(selected_weights * values$auc_dcr),
          delta = sum(selected_weights * values$delta),
          stringsAsFactors = FALSE
        )
      }
    }
  }
  if (length(collection_rows)) {
    replicates <- rbind(replicates, do.call(rbind, collection_rows))
  }
  list(
    assignments = receipt_assignments,
    replicates = replicates,
    seed = result$seed,
    receipt_sha256 = result$receipt_sha256,
    assignment_file_sha256 = assignment_serialization_sha256(receipt_assignments),
    task_id = if (is.null(task_id)) "" else task_id,
    role = role,
    stream = stream
  )
}

intervals_for <- function(replicates, role) {
  rows <- list()
  cursor <- 0L
  keys <- unique(replicates[c("scope", "score_method", "study_id", "stream")])
  for (index in seq_len(nrow(keys))) {
    key <- keys[index, , drop = FALSE]
    group <- replicates[
      replicates$scope == key$scope & replicates$score_method == key$score_method &
        replicates$study_id == key$study_id & replicates$stream == key$stream,
      , drop = FALSE
    ]
    for (metric in c("auc_orr", "auc_dcr", "delta")) {
      values <- group[[metric]]
      if (length(values) != 2000L || any(!is.finite(values))) next
      ends <- quantile_ends(values)
      cursor <- cursor + 1L
      rows[[cursor]] <- data.frame(
        scope = key$scope,
        score_method = key$score_method,
        study_id = key$study_id,
        stream = key$stream,
        role = role,
        metric = metric,
        lower = ends[[1L]],
        upper = ends[[2L]],
        conditioning = "conditional_on_original_study_category_counts_O_SD_PD",
        stringsAsFactors = FALSE
      )
    }
  }
  if (length(rows)) do.call(rbind, rows) else data.frame(
    scope = character(), score_method = character(), study_id = character(),
    stream = character(), role = character(), metric = character(),
    lower = numeric(), upper = numeric(), conditioning = character()
  )
}

main <- run_stream("a_p1_bootstrap", "primary")
check <- run_stream("second_check", "reported_only", "a_p1_bootstrap")
all_replicates <- rbind(main$replicates, check$replicates)
all_assignments <- rbind(main$assignments, check$assignments)
all_assignments$stream <- c(
  rep("a_p1_bootstrap", nrow(main$assignments)),
  rep("second_check", nrow(check$assignments))
)
all_intervals <- rbind(
  intervals_for(main$replicates, "primary"),
  intervals_for(check$replicates, "reported_only")
)
all_receipts <- do.call(rbind, lapply(list(main, check), function(result) {
  data.frame(
    stream = result$stream,
    role = result$role,
    task_id = result$task_id,
    seed = result$seed,
    repetitions = 2000L,
    reported_only = if (result$role == "reported_only") "TRUE" else "FALSE",
    receipt_sha256 = result$receipt_sha256,
    assignment_file_sha256 = result$assignment_file_sha256,
    conditioning = "conditional_on_original_study_category_counts_O_SD_PD",
    stringsAsFactors = FALSE
  )
}))

comparison_rows <- list()
comparison_cursor <- 0L
delta_intervals <- all_intervals[all_intervals$metric == "delta", , drop = FALSE]
for (index in seq_len(nrow(delta_intervals))) {
  main_row <- delta_intervals[index, , drop = FALSE]
  if (main_row$stream != "a_p1_bootstrap") next
  check_row <- delta_intervals[
    delta_intervals$scope == main_row$scope &
      delta_intervals$score_method == main_row$score_method &
      delta_intervals$study_id == main_row$study_id &
      delta_intervals$stream == "second_check", , drop = FALSE
  ]
  if (nrow(check_row) != 1L) next
  lower_difference <- abs(main_row$lower[[1L]] - check_row$lower[[1L]])
  upper_difference <- abs(main_row$upper[[1L]] - check_row$upper[[1L]])
  comparison_cursor <- comparison_cursor + 1L
  comparison_rows[[comparison_cursor]] <- data.frame(
    scope = main_row$scope,
    score_method = main_row$score_method,
    study_id = main_row$study_id,
    main_delta_lower = main_row$lower[[1L]],
    second_check_delta_lower = check_row$lower[[1L]],
    delta_lower_difference = lower_difference,
    main_delta_upper = main_row$upper[[1L]],
    second_check_delta_upper = check_row$upper[[1L]],
    delta_upper_difference = upper_difference,
    flag_over_0_01 = lower_difference > 0.01 || upper_difference > 0.01,
    second_check_replaces_main = FALSE,
    stringsAsFactors = FALSE
  )
}
all_comparisons <- if (length(comparison_rows)) do.call(rbind, comparison_rows) else data.frame(
  scope = character(), score_method = character(), study_id = character(),
  main_delta_lower = numeric(), second_check_delta_lower = numeric(),
  delta_lower_difference = numeric(), main_delta_upper = numeric(),
  second_check_delta_upper = numeric(), delta_upper_difference = numeric(),
  flag_over_0_01 = logical(), second_check_replaces_main = logical()
)

out_dir <- bridge$output_dir
utils::write.table(all_assignments, file.path(out_dir, "bootstrap_assignments.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
utils::write.table(all_replicates, file.path(out_dir, "bootstrap_replicates.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
utils::write.table(all_intervals, file.path(out_dir, "intervals.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
utils::write.table(all_receipts, file.path(out_dir, "random_receipts.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
utils::write.table(all_comparisons, file.path(out_dir, "second_check_comparison.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
bridge_write_session(out_dir)
