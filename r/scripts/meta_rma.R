source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "metafor"))
config <- bridge_config()

groups <- read.delim(config$inputs$groups, check.names = FALSE, stringsAsFactors = FALSE)
effects <- read.delim(config$inputs$effects, check.names = FALSE, stringsAsFactors = FALSE)
subgroups <- read.delim(config$inputs$subgroups, check.names = FALSE, stringsAsFactors = FALSE)

meta_columns <- c(
  "analysis_id", "k", "n_cancers", "n_studies", "estimate", "se", "ci_lb", "ci_ub", "tau2", "I2",
  "Q", "p", "fixed_estimate", "fixed_ci_lb", "fixed_ci_ub", "status", "reason"
)
meta_results <- list()

empty_result <- function(analysis_id, k, status, reason, n_cancers = 0L, n_studies = 0L) {
  data.frame(
    analysis_id = analysis_id,
    k = as.integer(k),
    n_cancers = as.integer(n_cancers),
    n_studies = as.integer(n_studies),
    estimate = NA_real_,
    se = NA_real_,
    ci_lb = NA_real_,
    ci_ub = NA_real_,
    tau2 = NA_real_,
    I2 = NA_real_,
    Q = NA_real_,
    p = NA_real_,
    fixed_estimate = NA_real_,
    fixed_ci_lb = NA_real_,
    fixed_ci_ub = NA_real_,
    status = status,
    reason = reason,
    stringsAsFactors = FALSE
  )
}

single_result <- function(analysis_id, yi, vi, n_cancers, n_studies) {
  standard_error <- sqrt(vi)
  result <- empty_result(
    analysis_id, 1L, "single_study", "one independent unit; no pooling",
    n_cancers = n_cancers, n_studies = n_studies
  )
  result$estimate <- yi
  result$se <- standard_error
  result$ci_lb <- yi - 1.96 * standard_error
  result$ci_ub <- yi + 1.96 * standard_error
  result
}

pooled_result <- function(analysis_id, yi, vi, n_cancers, n_studies, weights = NULL) {
  arguments <- list(yi = yi, vi = vi, method = "REML", test = "adhoc")
  if (!is.null(weights)) {
    arguments$weights <- weights
  }
  fit <- do.call(metafor::rma.uni, arguments)
  fixed <- metafor::rma.uni(yi = yi, vi = vi, method = "FE", test = "z")
  result <- empty_result(
    analysis_id, length(yi), "pooled", "",
    n_cancers = n_cancers, n_studies = n_studies
  )
  result$estimate <- as.numeric(fit$b[1L, 1L])
  result$se <- as.numeric(fit$se[1L])
  result$ci_lb <- as.numeric(fit$ci.lb[1L])
  result$ci_ub <- as.numeric(fit$ci.ub[1L])
  result$tau2 <- as.numeric(fit$tau2[1L])
  result$I2 <- as.numeric(fit$I2[1L])
  result$Q <- as.numeric(fit$QE[1L])
  result$p <- as.numeric(fit$pval[1L])
  result$fixed_estimate <- as.numeric(fixed$b[1L, 1L])
  result$fixed_ci_lb <- as.numeric(fixed$ci.lb[1L])
  result$fixed_ci_ub <- as.numeric(fixed$ci.ub[1L])
  result
}

for (index in seq_len(nrow(groups))) {
  group <- groups[index, , drop = FALSE]
  if (group$analysis_type[[1L]] == "across_cancers") {
    next
  }
  group_id <- as.character(group$analysis_id[[1L]])
  group_effects <- effects[effects$analysis_id == group_id, , drop = FALSE]
  k <- nrow(group_effects)
  cancer_values <- unique(unlist(strsplit(as.character(group_effects$cancer_components), ",", fixed = TRUE)))
  cancer_values <- cancer_values[nzchar(cancer_values) & cancer_values != "multi"]
  n_cancers <- if (length(cancer_values)) length(cancer_values) else 0L
  n_studies <- length(unique(group_effects$study))
  if (k == 0L) {
    result <- empty_result(group_id, 0L, "not_estimable", "no_estimable_studies")
  } else if (k == 1L) {
    result <- single_result(group_id, group_effects$yi[[1L]], group_effects$vi[[1L]], n_cancers, n_studies)
  } else if (group$unit_family[[1L]] == "gene" && k < 3L) {
    result <- empty_result(group_id, k, "not_pooled", "gene_pooling_requires_k>=3", n_cancers, n_studies)
  } else {
    result <- pooled_result(group_id, group_effects$yi, group_effects$vi, n_cancers, n_studies)
  }
  meta_results[[group_id]] <- result
}

for (index in seq_len(nrow(groups))) {
  group <- groups[index, , drop = FALSE]
  if (group$analysis_type[[1L]] != "across_cancers") {
    next
  }
  group_id <- as.character(group$analysis_id[[1L]])
  child_groups <- groups[groups$parent_id == group_id & groups$analysis_type == "across_within", , drop = FALSE]
  child_results <- lapply(as.character(child_groups$analysis_id), function(child_id) meta_results[[child_id]])
  available_indices <- which(vapply(child_results, function(result) {
    !is.null(result) && is.finite(result$estimate[[1L]])
  }, logical(1L)))
  available <- child_results[available_indices]
  available_child_ids <- as.character(child_groups$analysis_id[available_indices])
  contributing_effects <- effects[effects$analysis_id %in% available_child_ids, , drop = FALSE]
  n_studies <- length(unique(contributing_effects$study))
  k <- length(available)
  if (k == 0L) {
    result <- empty_result(group_id, 0L, "not_estimable", "no_estimable_cancers")
  } else if (k == 1L) {
    child <- available[[1L]]
    result <- empty_result(
      group_id, 1L, "single_study", "one cancer contributes; no pooling",
      n_cancers = 1L, n_studies = n_studies
    )
    result$estimate <- child$estimate[[1L]]
    result$se <- child$se[[1L]]
    result$ci_lb <- child$ci_lb[[1L]]
    result$ci_ub <- child$ci_ub[[1L]]
  } else if (group$unit_family[[1L]] == "gene" && k < 3L) {
    result <- empty_result(
      group_id, k, "not_pooled", "gene_pooling_requires_k>=3",
      n_cancers = k, n_studies = n_studies
    )
  } else {
    cancer_estimates <- vapply(available, function(item) item$estimate[[1L]], numeric(1L))
    cancer_variances <- vapply(available, function(item) item$se[[1L]]^2, numeric(1L))
    # vi retains each stage-one sampling variance; weights make the stage-two mean equal by cancer.
    result <- pooled_result(
      group_id, cancer_estimates, cancer_variances,
      n_cancers = k,
      n_studies = n_studies,
      weights = rep(1, k)
    )
  }
  meta_results[[group_id]] <- result
}

meta_table <- if (length(meta_results)) do.call(rbind, meta_results) else as.data.frame(setNames(replicate(length(meta_columns), logical(0), simplify = FALSE), meta_columns))
meta_table <- meta_table[, meta_columns, drop = FALSE]
write.table(
  meta_table,
  file = file.path(config$output_dir, "meta.tsv"),
  sep = "\t",
  row.names = FALSE,
  col.names = TRUE,
  quote = FALSE,
  na = "NA"
)

subgroup_columns <- c("test_id", "F", "p", "status", "reason")
subgroup_results <- list()
for (test_id in unique(as.character(subgroups$test_id))) {
  test_rows <- subgroups[subgroups$test_id == test_id, , drop = FALSE]
  if (!nrow(test_rows) || test_rows$n_studies[[1L]] < 10L) {
    result <- data.frame(test_id = test_id, F = NA_real_, p = NA_real_, status = "not_tested", reason = "total_k<10")
  } else if (length(unique(test_rows$stratum)) < 2L) {
    result <- data.frame(test_id = test_id, F = NA_real_, p = NA_real_, status = "not_tested", reason = "fewer_than_two_strata")
  } else {
    fit <- metafor::rma.uni(
      yi = test_rows$yi,
      vi = test_rows$vi,
      mods = ~ factor(stratum),
      data = test_rows,
      method = "REML",
      test = "adhoc"
    )
    result <- data.frame(
      test_id = test_id,
      F = as.numeric(fit$QM[1L]),
      p = as.numeric(fit$QMp[1L]),
      status = "tested",
      reason = "",
      stringsAsFactors = FALSE
    )
  }
  subgroup_results[[test_id]] <- result
}
subgroup_table <- if (length(subgroup_results)) do.call(rbind, subgroup_results) else data.frame(
  test_id = character(), F = numeric(), p = numeric(), status = character(), reason = character()
)
subgroup_table <- subgroup_table[, subgroup_columns, drop = FALSE]
write.table(
  subgroup_table,
  file = file.path(config$output_dir, "subgroups.tsv"),
  sep = "\t",
  row.names = FALSE,
  col.names = TRUE,
  quote = FALSE,
  na = "NA"
)
bridge_write_session(config$output_dir)
