source("R/bridge.R")
bridge_require(c("jsonlite", "digest", "glmnet"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir
source("R/random_streams.R")

feature_names <- unlist(cfg$feature_names, use.names = FALSE)
response_name <- cfg$response_column
if (!identical(feature_names, c(
  "P_ANTIGEN_PRESENTATION", "M2_CYTOTOXICITY", "M3_VIRAL_MIMICRY", "M4_EXCLUSION"
)) || !identical(response_name, "orr_class")) {
  stop("A-P2 feature and response columns must match the signed contract")
}

safe_number <- function(value) {
  if (length(value) == 0L || !is.finite(value)) NA_real_ else as.numeric(value)
}

.a_p2_solver_attempts <- 0L

record_solver_failure <- function(reason, warnings = character(), jerr = NA_integer_) {
  work_dir <- cfg$work_dir
  if (is.null(work_dir) || !nzchar(work_dir)) stop("A-P2 needs private work storage for solver diagnostics")
  dir.create(work_dir, recursive = TRUE, showWarnings = FALSE)
  jsonlite::write_json(list(
    status = "FIT_ABORTED",
    reason = reason,
    warnings = as.list(warnings),
    jerr = as.integer(jerr),
    fit_attempts = as.integer(.a_p2_solver_attempts),
    result_published = FALSE
  ), file.path(work_dir, "solver_failure.json"), auto_unbox = TRUE, pretty = TRUE)
}

read_features <- function(input_bytes) {
  input_text <- rawToChar(input_bytes)
  header <- names(utils::read.delim(
    text = input_text, sep = "\t", nrows = 0L, check.names = FALSE,
    quote = "", comment.char = "", stringsAsFactors = FALSE
  ))
  if (anyDuplicated(header)) stop("A-P2 input has duplicate column names")
  required <- c("cohort", "patient_id", response_name, feature_names, "CYT")
  missing <- setdiff(required, header)
  if (length(missing)) stop(paste("A-P2 input is missing required named columns:", paste(missing, collapse = ", ")))
  col_classes <- rep("NULL", length(header))
  col_classes[match(required, header)] <- "character"
  data <- utils::read.delim(
    text = input_text, sep = "\t", colClasses = col_classes, check.names = FALSE,
    quote = "", comment.char = "", stringsAsFactors = FALSE,
    na.strings = character(), fill = FALSE
  )
  if (!nrow(data)) stop("A-P2 input contains no patient rows")
  if (anyNA(data$cohort) || any(!nzchar(data$cohort)) ||
      anyNA(data$patient_id) || any(!nzchar(data$patient_id))) {
    stop("A-P2 rows require non-empty cohort and patient identifiers")
  }
  if (anyNA(data[[response_name]]) || !all(data[[response_name]] %in% c("R", "NR"))) {
    stop("A-P2 response field must contain only the explicit R and NR classes")
  }
  if (anyDuplicated(paste(data$cohort, data$patient_id, sep = "\r"))) {
    stop("A-P2 input repeats a patient within an originating study")
  }
  for (feature in feature_names) {
    original <- data[[feature]]
    converted <- suppressWarnings(as.numeric(original))
    if (any(!is.na(original) & nzchar(original) & is.na(converted))) {
      stop(paste("A-P2 feature contains a non-numeric value:", feature))
    }
    data[[feature]] <- converted
  }
  cyt_original <- data$CYT
  data$CYT <- suppressWarnings(as.numeric(cyt_original))
  if (any(!is.na(cyt_original) & nzchar(cyt_original) & is.na(data$CYT))) {
    stop("A-P2 CYT contains a non-numeric value")
  }
  data$orr_class <- data[[response_name]]
  data$row_index <- seq_len(nrow(data))
  cohorts <- cfg$cohorts
  unknown <- setdiff(unique(data$cohort), names(cohorts))
  if (length(unknown)) stop(paste("A-P2 rows have undeclared cohorts:", paste(unknown, collapse = ", ")))
  declared <- names(cohorts)
  absent <- setdiff(declared, unique(data$cohort))
  if (length(absent)) stop(paste("A-P2 manifest cohorts have no input rows:", paste(absent, collapse = ", ")))
  metadata <- lapply(declared, function(cohort) {
    item <- cohorts[[cohort]]
    data.frame(
      cohort = cohort,
      study_family = item$study_family,
      cancer = item$cancer,
      representation = item$representation,
      primary_eligible = isTRUE(item$primary_eligible),
      adaptive_eligible = isTRUE(item$adaptive_eligible),
      cyt_available = isTRUE(item$cyt_available),
      stringsAsFactors = FALSE
    )
  })
  metadata <- do.call(rbind, metadata)
  data <- merge(data, metadata, by = "cohort", all.x = TRUE, sort = FALSE)
  data <- data[order(enc2utf8(data$cohort), enc2utf8(data$patient_id), method = "radix"), , drop = FALSE]
  rownames(data) <- NULL
  data$row_index <- seq_len(nrow(data))
  data
}

count_classes <- function(rows) {
  c(R = sum(rows$orr_class == "R"), NR = sum(rows$orr_class == "NR"))
}

training_floor_reason <- function(rows, min_class = 20L, min_families = 2L) {
  if (!nrow(rows)) return("UNAVAILABLE_NO_TRAINING_ROWS")
  counts <- count_classes(rows)
  if (any(counts < min_class)) return("UNAVAILABLE_TRAINING_CLASS_FLOOR")
  if (length(unique(rows$study_family)) < min_families) return("UNAVAILABLE_TRAINING_FAMILY_FLOOR")
  if (any(!is.finite(as.matrix(rows[, feature_names, drop = FALSE])))) {
    return("UNAVAILABLE_MISSING_OR_NONFINITE_FEATURE")
  }
  "AVAILABLE"
}

fit_glmnet <- function(x, rows, scaling = NULL, adaptive_scaling = NULL) {
  y <- as.integer(rows$orr_class == "R")
  warnings <- character()
  .a_p2_solver_attempts <<- .a_p2_solver_attempts + 1L
  solver <- getOption("a_p2.glmnet_solver", glmnet::glmnet)
  fit <- tryCatch(withCallingHandlers(
    solver(
      x, y, family = "binomial", alpha = 0, lambda = 0.1,
      standardize = FALSE, intercept = TRUE,
      control = list(thresh = 1e-10, maxit = 1e6)
    ),
    warning = function(condition) {
      warnings <<- c(warnings, conditionMessage(condition))
      invokeRestart("muffleWarning")
    }
  ), error = function(error) error)
  if (inherits(fit, "error")) {
    message <- conditionMessage(fit)
    record_solver_failure("glmnet_error", warnings)
    stop(paste("A-P2 glmnet solver failed; operation aborted:", message), call. = FALSE)
  }
  jerr <- as.integer(fit$jerr)
  if (length(jerr) != 1L || is.na(jerr) || jerr != 0L) {
    record_solver_failure("nonzero_or_missing_jerr", warnings, jerr)
    stop(paste("A-P2 glmnet returned nonzero or missing jerr; operation aborted:",
      if (length(jerr) == 1L && !is.na(jerr)) jerr else "NA"), call. = FALSE)
  }
  if (length(warnings)) {
    record_solver_failure("glmnet_warning", warnings, jerr)
    stop(paste("A-P2 glmnet emitted a warning; operation aborted:", paste(warnings, collapse = "; ")), call. = FALSE)
  }
  coefficient_matrix <- as.matrix(stats::coef(fit, s = 0.1))
  coefficients <- as.numeric(coefficient_matrix[-1L, 1L])
  names(coefficients) <- feature_names
  intercept <- as.numeric(coefficient_matrix[1L, 1L])
  eta <- as.numeric(intercept + x %*% coefficients)
  probability <- stats::plogis(eta)
  residual <- probability - y
  kkt <- max(abs(c(
    mean(residual),
    drop(crossprod(x, residual)) / nrow(x) + 0.1 * coefficients
  )))
  direct <- as.numeric(stats::predict(fit, newx = x, s = 0.1, type = "response"))
  direct_difference <- max(abs(direct - probability))
  if (!is.finite(kkt) || kkt > 1e-6) {
    record_solver_failure("kkt_tolerance_failure", warnings, jerr)
    stop(paste0("A-P2 glmnet KKT residual exceeds the frozen tolerance: ", format(kkt, digits = 16)), call. = FALSE)
  }
  if (!is.finite(direct_difference) || direct_difference > 1e-6) {
    record_solver_failure("direct_score_tolerance_failure", warnings, jerr)
    stop(paste0("A-P2 direct prediction check exceeds the frozen tolerance: ", format(direct_difference, digits = 16)), call. = FALSE)
  }
  list(
    available = TRUE,
    reason = "AVAILABLE",
    coefficients = coefficients,
    intercept = intercept,
    scaling = scaling,
    scaling_by_study = adaptive_scaling,
    jerr = jerr,
    npasses = as.integer(fit$npasses),
    kkt_max_residual = kkt,
    direct_prediction_max_difference = direct_difference,
    fit = fit
  )
}

fit_primary <- function(rows, min_class = 20L, min_families = 2L) {
  reason <- training_floor_reason(rows, min_class, min_families)
  if (!identical(reason, "AVAILABLE")) return(list(available = FALSE, reason = reason))
  x <- as.matrix(rows[, feature_names, drop = FALSE])
  means <- colMeans(x)
  sds <- apply(x, 2L, stats::sd)
  if (any(!is.finite(sds) | sds <= 0)) {
    return(list(available = FALSE, reason = "UNAVAILABLE_ZERO_OR_NONFINITE_TRAINING_SD"))
  }
  standardized <- sweep(sweep(x, 2L, means, "-"), 2L, sds, "/")
  scaling <- lapply(feature_names, function(feature) {
    list(mean = unname(means[[feature]]), sd = unname(sds[[feature]]))
  })
  names(scaling) <- feature_names
  result <- fit_glmnet(standardized, rows, scaling = scaling)
  result$training_counts <- as.list(count_classes(rows))
  result$training_n <- nrow(rows)
  result$training_family_count <- length(unique(rows$study_family))
  result$training_study_count <- length(unique(rows$cohort))
  result
}

study_statistics <- function(rows) {
  x <- as.matrix(rows[, feature_names, drop = FALSE])
  means <- colMeans(x)
  sds <- apply(x, 2L, stats::sd)
  if (any(!is.finite(x)) || any(!is.finite(means)) || any(!is.finite(sds) | sds <= 0)) {
    return(list(available = FALSE, reason = "UNAVAILABLE_ZERO_NONFINITE_SD_OR_MISSING_FEATURE"))
  }
  scaling <- lapply(feature_names, function(feature) {
      list(mean = unname(means[[feature]]), sd = unname(sds[[feature]]))
  })
  names(scaling) <- feature_names
  list(available = TRUE, scaling = scaling)
}

adaptive_matrix <- function(rows, scaling_by_study) {
  x <- as.matrix(rows[, feature_names, drop = FALSE])
  if (any(!is.finite(x))) return(list(available = FALSE, reason = "UNAVAILABLE_MISSING_OR_NONFINITE_FEATURE"))
  result <- matrix(NA_real_, nrow = nrow(x), ncol = length(feature_names), dimnames = list(NULL, feature_names))
  for (study in unique(rows$cohort)) {
    statistics <- scaling_by_study[[study]]
    if (is.null(statistics)) return(list(available = FALSE, reason = paste("UNAVAILABLE_NO_COHORT_ADAPTATION", study)))
    center <- vapply(feature_names, function(feature) statistics[[feature]]$mean, numeric(1))
    scale <- vapply(feature_names, function(feature) statistics[[feature]]$sd, numeric(1))
    if (any(!is.finite(scale) | scale <= 0)) return(list(available = FALSE, reason = "UNAVAILABLE_ZERO_OR_NONFINITE_COHORT_SD"))
    selected <- rows$cohort == study
    result[selected, ] <- sweep(sweep(x[selected, , drop = FALSE], 2L, center, "-"), 2L, scale, "/")
  }
  list(available = TRUE, matrix = result)
}

fit_adaptive <- function(rows, min_class = 20L, min_families = 2L) {
  reason <- training_floor_reason(rows, min_class, min_families)
  if (!identical(reason, "AVAILABLE")) return(list(available = FALSE, reason = reason))
  scaling_by_study <- list()
  for (study in sort(unique(rows$cohort), method = "radix")) {
    part <- rows[rows$cohort == study, , drop = FALSE]
    statistics <- study_statistics(part)
    if (!isTRUE(statistics$available)) {
      return(list(available = FALSE, reason = paste(statistics$reason, study, sep = ":")))
    }
    scaling_by_study[[study]] <- statistics$scaling
  }
  transformed <- adaptive_matrix(rows, scaling_by_study)
  if (!isTRUE(transformed$available)) return(transformed)
  result <- fit_glmnet(transformed$matrix, rows, adaptive_scaling = scaling_by_study)
  result$training_counts <- as.list(count_classes(rows))
  result$training_n <- nrow(rows)
  result$training_family_count <- length(unique(rows$study_family))
  result$training_study_count <- length(unique(rows$cohort))
  result
}

model_scores <- function(model, rows, adaptive = FALSE, extra_scaling = NULL) {
  if (!isTRUE(model$available)) return(rep(NA_real_, nrow(rows)))
  x <- as.matrix(rows[, feature_names, drop = FALSE])
  if (any(!is.finite(x))) return(rep(NA_real_, nrow(rows)))
  if (adaptive) {
    scaling <- model$scaling_by_study
    if (!is.null(extra_scaling)) scaling <- c(scaling, extra_scaling)
    transformed <- adaptive_matrix(rows, scaling)
    if (!isTRUE(transformed$available)) return(rep(NA_real_, nrow(rows)))
    x <- transformed$matrix
  } else {
    means <- vapply(feature_names, function(feature) model$scaling[[feature]]$mean, numeric(1))
    sds <- vapply(feature_names, function(feature) model$scaling[[feature]]$sd, numeric(1))
    x <- sweep(sweep(x, 2L, means, "-"), 2L, sds, "/")
  }
  as.numeric(stats::plogis(model$intercept + x %*% model$coefficients))
}

auc_value <- function(labels, scores) {
  if (length(labels) != length(scores) || any(!is.finite(scores))) return(NA_real_)
  positive <- labels == "R"
  n_positive <- sum(positive)
  n_negative <- sum(!positive)
  if (!n_positive || !n_negative) return(NA_real_)
  ranks <- rank(scores, ties.method = "average")
  (sum(ranks[positive]) - n_positive * (n_positive + 1) / 2) / (n_positive * n_negative)
}

auc_reason <- function(rows, scores) {
  if (!nrow(rows) || any(!is.finite(scores))) return("UNAVAILABLE_SCORE")
  counts <- count_classes(rows)
  if (any(counts == 0L)) return("UNAVAILABLE_AUC_CLASS")
  "AVAILABLE"
}

cohort_summary <- function(rows, study, score, model_status, adaptive = FALSE,
                           extra_scaling = NULL, roster_cohorts = names(cfg$cohorts),
                           validation_label = "INTERNAL_EXTERNAL") {
  selected <- rows$cohort == study
  part <- rows[selected, , drop = FALSE]
  score_selected <- score[selected]
  learner_status <- auc_reason(part, score_selected)
  learner_auc <- if (learner_status == "AVAILABLE") auc_value(part$orr_class, score_selected) else NA_real_
  meta <- cfg$cohorts[[study]]
  cyt_complete <- isTRUE(meta$cyt_available) && all(is.finite(part$CYT))
  cyt_auc <- if (cyt_complete) auc_value(part$orr_class, part$CYT) else NA_real_
  cyt_status <- if (!isTRUE(meta$cyt_available)) "CYT_UNAVAILABLE_BY_MEASUREMENT_CONTRACT" else if (!all(is.finite(part$CYT))) "CYT_UNAVAILABLE_INCOMPLETE_SCORE" else if (!is.finite(cyt_auc)) "UNAVAILABLE_AUC_CLASS" else "AVAILABLE"
  delta <- if (learner_status == "AVAILABLE" && cyt_status == "AVAILABLE") learner_auc - cyt_auc else NA_real_
  comparison_status <- if (is.finite(delta)) "AVAILABLE_PAIRED" else if (learner_status == "AVAILABLE" && cyt_status != "AVAILABLE") "LEARNER_ONLY_CYT_UNAVAILABLE" else learner_status
  cancer <- meta$cancer
  family <- meta$study_family
  transfer <- if (sum(vapply(roster_cohorts, function(value) identical(cfg$cohorts[[value]]$cancer, cancer), logical(1))) == 1L) {
    "JOINT_STUDY_AND_CANCER_TRANSFER"
  } else {
    "STUDY_FAMILY_TRANSFER"
  }
  list(
    analysis = if (adaptive) "COHORT_ADAPTIVE_SENSITIVITY" else "PRIMARY_TPM",
    validation_label = validation_label,
    study_family = family, study = study, cancer = cancer,
    transfer_label = transfer,
    n = nrow(part), responders = sum(part$orr_class == "R"), nonresponders = sum(part$orr_class == "NR"),
    learner_auc = learner_auc, learner_status = learner_status,
    cyt_auc = cyt_auc, cyt_status = cyt_status, delta_auc = delta,
    comparison_status = comparison_status,
    model_status = model_status,
    scaling_scope = if (adaptive) "WITHIN_STUDY_OUTCOME_BLINDED" else "DEVELOPMENT_TRAINING_ONLY"
  )
}

records_frame <- function(records) {
  columns <- c(
    "analysis", "validation_label", "study_family", "study", "cancer", "transfer_label", "n",
    "responders", "nonresponders", "learner_auc", "learner_status", "cyt_auc",
    "cyt_status", "delta_auc", "comparison_status", "model_status", "scaling_scope"
  )
  if (!length(records)) return(as.data.frame(setNames(replicate(length(columns), character(), simplify = FALSE), columns)))
  result <- lapply(records, function(record) as.data.frame(record, stringsAsFactors = FALSE, check.names = FALSE))
  do.call(rbind, result)[, columns, drop = FALSE]
}

primary_roster <- function(data) {
  data[data$primary_eligible, , drop = FALSE]
}

adaptive_roster <- function(data) {
  data[data$adaptive_eligible, , drop = FALSE]
}

aggregate_leave_out <- function(records, roster, analysis) {
  frame <- records_frame(records)
  studies <- sort(unique(roster$cohort), method = "radix")
  cancers <- vapply(studies, function(study) cfg$cohorts[[study]]$cancer, character(1))
  study_count_by_cancer <- table(cancers)
  frame$equal_study_weight <- if (nrow(frame)) 1 / length(studies) else numeric()
  frame$equal_cancer_weight <- if (nrow(frame)) {
    vapply(frame$cancer, function(cancer) 1 / length(unique(cancers)) / as.numeric(study_count_by_cancer[[cancer]]), numeric(1))
  } else numeric()
  records_frame_out <- frame
  aggregate_rows <- list()
  for (weighting in c("equal_study", "equal_cancer")) {
    for (metric in c("learner_auc", "cyt_auc", "delta_auc")) {
      status_column <- switch(
        metric, learner_auc = "learner_status", cyt_auc = "cyt_status",
        delta_auc = "comparison_status"
      )
      required_status <- if (metric == "delta_auc") "AVAILABLE_PAIRED" else "AVAILABLE"
      complete_roster <- nrow(frame) == length(studies) &&
        setequal(frame$study, studies) && !anyDuplicated(frame$study)
      complete_metric <- complete_roster && all(frame[[status_column]] == required_status) &&
        all(is.finite(frame[[metric]]))
      if (!complete_metric) {
        value <- NA_real_
        status <- if (!complete_roster) {
          "UNAVAILABLE_INCOMPLETE_REQUIRED_STUDY"
        } else if (metric == "learner_auc") {
          "UNAVAILABLE_REQUIRED_STUDY_LEARNER"
        } else if (metric == "cyt_auc") {
          "UNAVAILABLE_REQUIRED_STUDY_CYT"
        } else {
          "UNAVAILABLE_REQUIRED_STUDY_PAIRED_COMPARISON"
        }
      } else if (weighting == "equal_study") {
        value <- mean(frame[[metric]])
        status <- "AVAILABLE"
      } else {
        by_cancer <- vapply(sort(unique(frame$cancer), method = "radix"), function(cancer) {
          mean(frame[[metric]][frame$cancer == cancer])
        }, numeric(1))
        value <- mean(by_cancer)
        status <- "AVAILABLE"
    }
    aggregate_rows[[length(aggregate_rows) + 1L]] <- data.frame(
        analysis = analysis, metric = metric, weighting = weighting,
        study_count = length(studies), cancer_count = length(unique(cancers)),
        value = value, status = status, stringsAsFactors = FALSE
      )
    }
  }
  list(studies = records_frame_out, aggregates = do.call(rbind, aggregate_rows))
}

leave_family_out <- function(roster, adaptive = FALSE) {
  analysis <- if (adaptive) "COHORT_ADAPTIVE_SENSITIVITY" else "PRIMARY_TPM"
  families <- sort(unique(roster$study_family), method = "radix")
  family_records <- list()
  model_records <- list()
  records <- list()
  for (family in families) {
    held <- roster[roster$study_family == family, , drop = FALSE]
    train <- roster[roster$study_family != family, , drop = FALSE]
    fit <- if (adaptive) fit_adaptive(train, 20L, 2L) else fit_primary(train, 20L, 2L)
    fold_model_records <- family_model_rows(analysis, family, fit, adaptive)
    family_records[[length(family_records) + 1L]] <- data.frame(
      analysis = analysis, held_out_family = family,
      held_out_studies = paste(sort(unique(held$cohort), method = "radix"), collapse = ","),
      training_study_count = length(unique(train$cohort)),
      training_family_count = length(unique(train$study_family)),
      training_n = nrow(train), responders = sum(train$orr_class == "R"),
      nonresponders = sum(train$orr_class == "NR"),
      status = if (isTRUE(fit$available)) "AVAILABLE" else fit$reason,
      stringsAsFactors = FALSE
    )
    score <- rep(NA_real_, nrow(held))
    extra <- NULL
    if (isTRUE(fit$available) && adaptive) {
      for (study in sort(unique(held$cohort), method = "radix")) {
        part <- held[held$cohort == study, , drop = FALSE]
        statistics <- study_statistics(part)
        if (!isTRUE(statistics$available)) {
          fit$available <- FALSE
          fit$reason <- paste(statistics$reason, study, sep = ":")
          break
        }
        extra[[study]] <- statistics$scaling
        for (feature in feature_names) {
          value <- statistics$scaling[[feature]]
          fold_model_records <- rbind(fold_model_records, data.frame(
            analysis = analysis, held_out_family = family,
            study_scope = paste0("HELD_OUT_OUTCOME_BLINDED:", study),
            feature = feature, mean = value$mean, sd = value$sd,
            coefficient = NA_real_, intercept = NA_real_,
            status = "AVAILABLE_OUTCOME_BLINDED", stringsAsFactors = FALSE
          ))
        }
      }
    }
    model_records[[length(model_records) + 1L]] <- fold_model_records
    if (isTRUE(fit$available)) {
      score <- model_scores(fit, held, adaptive, extra)
    }
    for (study in sort(unique(held$cohort), method = "radix")) {
      record <- cohort_summary(
        held, study, score, if (isTRUE(fit$available)) "AVAILABLE" else fit$reason,
        adaptive, extra, sort(unique(roster$cohort), method = "radix")
      )
      if (!isTRUE(fit$available)) {
        record$learner_status <- fit$reason
        record$comparison_status <- fit$reason
      }
      records[[length(records) + 1L]] <- record
    }
  }
  assembled <- aggregate_leave_out(records, roster, analysis)
  list(
    family_folds = if (length(family_records)) do.call(rbind, family_records) else data.frame(),
    models = if (length(model_records)) do.call(rbind, model_records) else data.frame(
      analysis = character(), held_out_family = character(), study_scope = character(),
      feature = character(), mean = numeric(), sd = numeric(), coefficient = numeric(),
      intercept = numeric(), status = character(), stringsAsFactors = FALSE
    ),
    studies = assembled$studies,
    aggregates = assembled$aggregates
  )
}

append_small_training_rows <- function(split_result, split_roster, full_roster, eligible_studies) {
  indices <- split_result$indices
  small <- full_roster[!full_roster$cohort %in% eligible_studies, , drop = FALSE]
  additions <- list()
  if (nrow(small)) {
    for (repeat_id in seq_len(20L)) {
      for (study in sort(unique(small$cohort), method = "radix")) {
        part <- small[small$cohort == study, , drop = FALSE]
        for (stratum in c("R", "NR")) {
          selected <- part[part$orr_class == stratum, , drop = FALSE]
          if (!nrow(selected)) next
          additions[[length(additions) + 1L]] <- data.frame(
            study = study, replicate = repeat_id, stratum = stratum,
            partition = "train", position = seq_len(nrow(selected)),
            row_index = selected$row_index, stringsAsFactors = FALSE
          )
        }
      }
    }
  }
  if (length(additions)) indices <- rbind(indices, do.call(rbind, additions))
  indices <- indices[order(
    enc2utf8(indices$study), indices$replicate,
    match(indices$stratum, c("R", "NR")), indices$position, method = "radix"
  ), , drop = FALSE]
  split_result$indices <- indices
  split_result$receipt_sha256 <- .random_receipt_hash(indices)
  split_result
}

split_output_row <- function(analysis, result_type, status, replicate = NA_integer_,
                             weighting = "", study_family = "", study = "",
                             cancer = "", n = NA_integer_, responders = NA_integer_,
                             nonresponders = NA_integer_, learner_auc = NA_real_,
                             learner_status = "", cyt_auc = NA_real_, cyt_status = "",
                             delta_auc = NA_real_, comparison_status = "",
                             equal_study_weight = NA_real_, equal_cancer_weight = NA_real_,
                             repeat_mean = NA_real_, repeat_sd = NA_real_,
                             validation_label = "VALIDATION_SETTING_CONTRAST_NOT_OPTIMISM",
                             metric = "") {
  data.frame(
    analysis = analysis, validation_label = validation_label,
    result_type = result_type, metric = metric, replicate = replicate,
    weighting = weighting, study_family = study_family, study = study,
    cancer = cancer, n = n, responders = responders, nonresponders = nonresponders,
    learner_auc = learner_auc, learner_status = learner_status,
    cyt_auc = cyt_auc, cyt_status = cyt_status, delta_auc = delta_auc,
    comparison_status = comparison_status,
    equal_study_weight = equal_study_weight, equal_cancer_weight = equal_cancer_weight,
    repeat_mean = repeat_mean, repeat_sd = repeat_sd, status = status,
    stringsAsFactors = FALSE
  )
}

publish_random_receipt <- function(result, work_name, assignments_name, receipt_name,
                                   stream, task_id = NULL, operation) {
  work_dir <- file.path(cfg$work_dir, "random_receipts", work_name)
  dir.create(work_dir, recursive = TRUE, showWarnings = FALSE)
  write_random_receipt(result, work_dir, stream, task_id = task_id, operation = operation)
  assignments_path <- file.path(out_dir, assignments_name)
  if (!file.copy(file.path(work_dir, "assignments.tsv"), assignments_path, overwrite = TRUE)) {
    stop("A-P2 could not publish its assignment table")
  }
  receipt <- jsonlite::fromJSON(file.path(work_dir, "receipt.json"), simplifyVector = FALSE)
  receipt$assignments_file <- assignments_name
  receipt$assignments_sha256 <- digest::digest(file = assignments_path, algo = "sha256", serialize = FALSE)
  receipt_path <- file.path(out_dir, receipt_name)
  jsonlite::write_json(receipt, receipt_path, auto_unbox = TRUE, pretty = TRUE)
  file.copy(assignments_path, file.path(cfg$work_dir, assignments_name), overwrite = TRUE)
  file.copy(receipt_path, file.path(cfg$work_dir, receipt_name), overwrite = TRUE)
}

write_unavailable_split_receipt <- function(analysis, adaptive, reason) {
  prefix <- if (adaptive) "cohort_adaptive" else "primary"
  assignments_path <- file.path(out_dir, paste0(prefix, "_split_assignments.tsv"))
  receipt_path <- file.path(out_dir, paste0(prefix, "_split_receipt.json"))
  utils::write.table(
    data.frame(study = character(), replicate = integer(), stratum = character(),
      partition = character(), position = integer(), row_index = integer()),
    assignments_path, sep = "\t", row.names = FALSE, col.names = TRUE, quote = FALSE,
    na = "NA"
  )
  assignments_sha256 <- digest::digest(file = assignments_path, algo = "sha256", serialize = FALSE)
  jsonlite::write_json(list(
    operation = paste0(analysis, "_20x70_30"),
    stream = "a_p2_splits", status = reason, assignments_file = basename(assignments_path),
    assignments_sha256 = assignments_sha256, random_draws = FALSE
  ), receipt_path, auto_unbox = TRUE, pretty = TRUE)
  file.copy(assignments_path, file.path(cfg$work_dir, basename(assignments_path)), overwrite = TRUE)
  file.copy(receipt_path, file.path(cfg$work_dir, basename(receipt_path)), overwrite = TRUE)
}

run_splits <- function(roster, adaptive = FALSE) {
  analysis <- if (adaptive) "COHORT_ADAPTIVE_SENSITIVITY" else "PRIMARY_TPM"
  prefix <- if (adaptive) "cohort_adaptive" else "primary"
  if (!nrow(roster)) {
    reason <- "UNAVAILABLE_NO_ELIGIBLE_STUDIES"
    write_unavailable_split_receipt(analysis, adaptive, reason)
    return(list(records = split_output_row(analysis, "unavailable", reason), receipt = NULL, status = reason))
  }
  if (length(unique(roster$study_family)) < 3L) {
    reason <- "UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"
    write_unavailable_split_receipt(analysis, adaptive, reason)
    return(list(records = split_output_row(analysis, "unavailable", reason), receipt = NULL, status = reason))
  }
  class_table <- table(roster$cohort, roster$orr_class)
  studies <- sort(unique(roster$cohort), method = "radix")
  eligible <- studies[vapply(studies, function(study) {
    values <- class_table[study, , drop = TRUE]
    length(values) == 2L && all(values[c("R", "NR")] >= 10L)
  }, logical(1))]
  split_rows <- roster[roster$cohort %in% eligible, , drop = FALSE]
  if (!length(eligible)) {
    reason <- "UNAVAILABLE_NO_STUDY_MEETS_10_PER_CLASS"
    write_unavailable_split_receipt(analysis, adaptive, reason)
    return(list(records = split_output_row(analysis, "unavailable", reason), receipt = NULL, status = reason))
  }
  split_result <- split_indices(
    study = split_rows$cohort, row_key = split_rows$patient_id,
    strata = split_rows$orr_class, repetitions = 20L
  )
  split_result$indices$row_index <- split_rows$row_index[split_result$indices$row_index]
  split_result <- append_small_training_rows(split_result, split_rows, roster, eligible)
  records <- list()
  for (repeat_id in seq_len(20L)) {
    assignment <- split_result$indices[split_result$indices$replicate == repeat_id, , drop = FALSE]
    training_indices <- assignment$row_index[assignment$partition == "train"]
    test_indices <- assignment$row_index[assignment$partition == "test"]
    train <- roster[match(training_indices, roster$row_index), , drop = FALSE]
    tests <- roster[match(test_indices, roster$row_index), , drop = FALSE]
    fit <- if (adaptive) fit_adaptive(train, 1L, 1L) else fit_primary(train, 1L, 1L)
    extra <- NULL
    if (isTRUE(fit$available) && adaptive) {
      extra <- fit$scaling_by_study
    }
    score <- if (isTRUE(fit$available)) model_scores(fit, tests, adaptive, extra) else rep(NA_real_, nrow(tests))
    for (study in eligible) {
      record <- cohort_summary(
        tests, study, score, if (isTRUE(fit$available)) "AVAILABLE" else fit$reason,
        adaptive, extra, sort(unique(roster$cohort), method = "radix"),
        "VALIDATION_SETTING_CONTRAST_NOT_OPTIMISM"
      )
      record$replicate <- repeat_id
      if (!isTRUE(fit$available)) {
        record$learner_status <- fit$reason
        record$comparison_status <- fit$reason
      }
      records[[length(records) + 1L]] <- record
    }
  }
  frame <- records_frame(records)
  frame$replicate <- rep(seq_len(20L), each = length(eligible))
  frame$equal_study_weight <- 1 / length(eligible)
  eligible_cancers <- vapply(eligible, function(study) cfg$cohorts[[study]]$cancer, character(1))
  n_cancers <- length(unique(eligible_cancers))
  frame$equal_cancer_weight <- vapply(frame$cancer, function(cancer) {
    1 / n_cancers / sum(eligible_cancers == cancer)
  }, numeric(1))
  split_summary <- list()
  for (repeat_id in seq_len(20L)) {
    part <- frame[frame$replicate == repeat_id, , drop = FALSE]
    complete <- nrow(part) == length(eligible) && all(part$learner_status == "AVAILABLE")
    learner_study <- if (complete) mean(part$learner_auc) else NA_real_
    learner_cancer <- if (complete) mean(vapply(sort(unique(part$cancer), method = "radix"), function(cancer) mean(part$learner_auc[part$cancer == cancer]), numeric(1))) else NA_real_
    cyt_complete <- nrow(part) == length(eligible) && all(part$cyt_status == "AVAILABLE")
    cyt_study <- if (cyt_complete) mean(part$cyt_auc) else NA_real_
    cyt_cancer <- if (cyt_complete) mean(vapply(sort(unique(part$cancer), method = "radix"), function(cancer) mean(part$cyt_auc[part$cancer == cancer]), numeric(1))) else NA_real_
    paired <- nrow(part) == length(eligible) && all(part$comparison_status == "AVAILABLE_PAIRED")
    delta_study <- if (paired) mean(part$delta_auc) else NA_real_
    delta_cancer <- if (paired) mean(vapply(sort(unique(part$cancer), method = "radix"), function(cancer) mean(part$delta_auc[part$cancer == cancer]), numeric(1))) else NA_real_
    split_summary[[length(split_summary) + 1L]] <- data.frame(
      analysis = analysis, replicate = repeat_id, evaluated_studies = length(eligible),
      learner_equal_study = learner_study, learner_equal_cancer = learner_cancer,
      cyt_equal_study = cyt_study, cyt_equal_cancer = cyt_cancer,
      paired_delta_equal_study = delta_study, paired_delta_equal_cancer = delta_cancer,
      status = if (complete) if (paired) "AVAILABLE" else "LEARNER_ONLY_OR_CYT_UNAVAILABLE" else "UNAVAILABLE_REQUIRED_STUDY",
      stringsAsFactors = FALSE
    )
  }
  summary_frame <- do.call(rbind, split_summary)
  split_rows_out <- list()
  for (repeat_id in seq_len(20L)) {
    study_part <- frame[frame$replicate == repeat_id, , drop = FALSE]
    for (index in seq_len(nrow(study_part))) {
      item <- study_part[index, , drop = FALSE]
      split_rows_out[[length(split_rows_out) + 1L]] <- split_output_row(
        analysis, "study_repeat", if (item$comparison_status == "AVAILABLE_PAIRED") "AVAILABLE" else item$comparison_status,
        repeat_id, "", item$study_family, item$study, item$cancer, item$n,
        item$responders, item$nonresponders, item$learner_auc, item$learner_status,
        item$cyt_auc, item$cyt_status, item$delta_auc, item$comparison_status,
        item$equal_study_weight, item$equal_cancer_weight
      )
    }
    for (weighting in c("equal_study", "equal_cancer")) {
      learner_value <- if (weighting == "equal_study") summary_frame$learner_equal_study[[repeat_id]] else summary_frame$learner_equal_cancer[[repeat_id]]
      cyt_value <- if (weighting == "equal_study") summary_frame$cyt_equal_study[[repeat_id]] else summary_frame$cyt_equal_cancer[[repeat_id]]
      delta_value <- if (weighting == "equal_study") summary_frame$paired_delta_equal_study[[repeat_id]] else summary_frame$paired_delta_equal_cancer[[repeat_id]]
      learner_status <- if (is.finite(learner_value)) "AVAILABLE" else "UNAVAILABLE_REQUIRED_STUDY_LEARNER"
      cyt_status <- if (is.finite(cyt_value)) "AVAILABLE" else "UNAVAILABLE_REQUIRED_STUDY_CYT"
      comparison_status <- if (is.finite(delta_value)) "AVAILABLE_PAIRED" else if (is.finite(learner_value)) "LEARNER_ONLY_OR_CYT_UNAVAILABLE" else "UNAVAILABLE_REQUIRED_STUDY_PAIRED_COMPARISON"
      split_rows_out[[length(split_rows_out) + 1L]] <- split_output_row(
        analysis, "repeat_aggregate", summary_frame$status[[repeat_id]], repeat_id,
        weighting, study = "ALL_ELIGIBLE_STUDIES", learner_auc = learner_value,
        learner_status = learner_status, cyt_auc = cyt_value, cyt_status = cyt_status,
        delta_auc = delta_value, comparison_status = comparison_status
      )
    }
  }
  for (weighting in c("equal_study", "equal_cancer")) {
    for (metric in c("learner_auc", "cyt_auc", "delta_auc")) {
      column <- switch(
        metric,
        learner_auc = if (weighting == "equal_study") "learner_equal_study" else "learner_equal_cancer",
        cyt_auc = if (weighting == "equal_study") "cyt_equal_study" else "cyt_equal_cancer",
        delta_auc = if (weighting == "equal_study") "paired_delta_equal_study" else "paired_delta_equal_cancer"
      )
      values <- summary_frame[[column]]
      finite <- values[is.finite(values)]
      summary_status <- if (length(finite) == 20L) {
        "AVAILABLE"
      } else if (metric != "learner_auc" && all(is.finite(summary_frame[[if (weighting == "equal_study") "learner_equal_study" else "learner_equal_cancer"]]))) {
        "LEARNER_ONLY_OR_CYT_UNAVAILABLE"
      } else {
        "UNAVAILABLE_REQUIRED_STUDY"
      }
      split_rows_out[[length(split_rows_out) + 1L]] <- split_output_row(
        analysis, "repeat_summary", summary_status,
        weighting = weighting, study = "20_REPEAT_SPLIT_VARIABILITY",
        repeat_mean = if (length(finite)) mean(finite) else NA_real_,
        repeat_sd = if (length(finite) > 1L) stats::sd(finite) else NA_real_,
        metric = metric
      )
    }
  }
  publish_random_receipt(
    split_result, paste0(prefix, "_split"),
    paste0(prefix, "_split_assignments.tsv"), paste0(prefix, "_split_receipt.json"),
    "a_p2_splits", operation = paste0(analysis, "_20x70_30")
  )
  list(records = do.call(rbind, split_rows_out), receipt = split_result, status = "AVAILABLE")
}

write_tsv <- function(value, filename) {
  comparison_outputs <- c(
    "primary_leave_family_out.tsv", "primary_aggregates.tsv",
    "cohort_adaptive_aggregates.tsv", "primary_split_sensitivity.tsv",
    "cohort_adaptive_leave_family_out.tsv", "cohort_adaptive_split_sensitivity.tsv",
    "final_metrics.tsv", "predictions.tsv", "bootstrap.tsv",
    "bootstrap_summary.tsv", "second_check.tsv"
  )
  if (filename %in% comparison_outputs) {
    value$comparator_membership_caveat <- rep(
      "M2 includes GZMA and PRF1 and therefore partly overlaps the CYT comparator.",
      nrow(value)
    )
  }
  utils::write.table(
    value, file.path(out_dir, filename), sep = "\t", row.names = FALSE,
    col.names = TRUE, quote = FALSE, na = "NA"
  )
}

diagnostic_row <- function(analysis, fit) {
  counts <- fit$training_counts
  data.frame(
    analysis = analysis,
    status = if (isTRUE(fit$available)) "AVAILABLE" else fit$reason,
    training_n = if (isTRUE(fit$available)) fit$training_n else NA_integer_,
    responders = if (isTRUE(fit$available)) counts$R else NA_integer_,
    nonresponders = if (isTRUE(fit$available)) counts$NR else NA_integer_,
    family_count = if (isTRUE(fit$available)) fit$training_family_count else NA_integer_,
    study_count = if (isTRUE(fit$available)) fit$training_study_count else NA_integer_,
    jerr = if (isTRUE(fit$available)) fit$jerr else NA_integer_,
    kkt_max_residual = if (isTRUE(fit$available)) fit$kkt_max_residual else NA_real_,
    direct_prediction_max_difference = if (isTRUE(fit$available)) fit$direct_prediction_max_difference else NA_real_,
    stringsAsFactors = FALSE
  )
}

equation_model <- function(fit, adaptive = FALSE) {
  if (!isTRUE(fit$available)) return(list(status = fit$reason, available = FALSE))
  base <- list(
    available = TRUE,
    features = as.list(feature_names),
    coefficients = as.list(fit$coefficients),
    intercept = fit$intercept,
    training_counts = fit$training_counts,
    training_n = fit$training_n,
    training_family_count = fit$training_family_count,
    training_study_count = fit$training_study_count,
    jerr = fit$jerr,
    npasses = fit$npasses,
    kkt_max_residual = fit$kkt_max_residual,
    direct_prediction_max_difference = fit$direct_prediction_max_difference
  )
  if (adaptive) {
    base$scaling_by_study <- fit$scaling_by_study
    base$scaling_rule <- "within-study mean and sample SD (n-1); glmnet standardize=FALSE"
  } else {
    base$scaling <- fit$scaling
    base$scaling_rule <- "pooled training-only mean and sample SD (n-1); glmnet standardize=FALSE"
  }
  base
}

family_model_rows <- function(analysis, family, fit, adaptive = FALSE) {
  if (!isTRUE(fit$available)) {
    return(data.frame(
      analysis = analysis, held_out_family = family, study_scope = "",
      feature = "", mean = NA_real_, sd = NA_real_, coefficient = NA_real_,
      intercept = NA_real_, status = fit$reason, stringsAsFactors = FALSE
    ))
  }
  result <- list()
  studies <- if (adaptive) names(fit$scaling_by_study) else "POOLED_TRAINING_ONLY"
  for (study in studies) {
    for (feature in feature_names) {
      scaling <- if (adaptive) fit$scaling_by_study[[study]][[feature]] else fit$scaling[[feature]]
      result[[length(result) + 1L]] <- data.frame(
        analysis = analysis, held_out_family = family, study_scope = study,
        feature = feature, mean = scaling$mean, sd = scaling$sd,
        coefficient = fit$coefficients[[feature]], intercept = fit$intercept,
        status = "AVAILABLE", stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, result)
}

unavailable_aggregates <- function(analysis, roster, reason) {
  result <- expand.grid(
    metric = c("learner_auc", "cyt_auc", "delta_auc"),
    weighting = c("equal_study", "equal_cancer"),
    stringsAsFactors = FALSE
  )
  result$analysis <- analysis
  result$study_count <- length(unique(roster$cohort))
  result$cancer_count <- length(unique(roster$cancer))
  result$value <- NA_real_
  result$status <- reason
  result[, c("analysis", "metric", "weighting", "study_count", "cancer_count", "value", "status")]
}

run_development <- function(data) {
  primary <- primary_roster(data)
  adaptive <- adaptive_roster(data)
  primary_families <- length(unique(primary$study_family))
  adaptive_families <- length(unique(adaptive$study_family))
  primary_result <- if (primary_families < 3L) {
    list(family_folds = data.frame(), studies = data.frame(),
      aggregates = unavailable_aggregates("PRIMARY_TPM", primary, "UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"),
      models = data.frame(
      analysis = character(), held_out_family = character(), study_scope = character(),
      feature = character(), mean = numeric(), sd = numeric(), coefficient = numeric(),
      intercept = numeric(), status = character(), stringsAsFactors = FALSE
    ))
  } else leave_family_out(primary, FALSE)
  adaptive_result <- if (adaptive_families < 3L) {
    list(family_folds = data.frame(), studies = data.frame(),
      aggregates = unavailable_aggregates("COHORT_ADAPTIVE_SENSITIVITY", adaptive, "UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES"),
      models = data.frame(
      analysis = character(), held_out_family = character(), study_scope = character(),
      feature = character(), mean = numeric(), sd = numeric(), coefficient = numeric(),
      intercept = numeric(), status = character(), stringsAsFactors = FALSE
    ))
  } else leave_family_out(adaptive, TRUE)
  primary_splits <- run_splits(primary, FALSE)
  adaptive_splits <- run_splits(adaptive, TRUE)
  family_folds <- rbind(primary_result$family_folds, adaptive_result$family_folds)
  family_models <- rbind(primary_result$models, adaptive_result$models)
  write_tsv(primary_result$studies, "primary_leave_family_out.tsv")
  write_tsv(primary_result$aggregates, "primary_aggregates.tsv")
  write_tsv(adaptive_result$aggregates, "cohort_adaptive_aggregates.tsv")
  write_tsv(primary_splits$records, "primary_split_sensitivity.tsv")
  write_tsv(adaptive_result$studies, "cohort_adaptive_leave_family_out.tsv")
  write_tsv(adaptive_splits$records, "cohort_adaptive_split_sensitivity.tsv")
  write_tsv(family_folds, "family_folds.tsv")
  write_tsv(family_models, "family_models.tsv")
}

leave_family_training_floor_reason <- function(rows) {
  families <- unique(rows$study_family)
  if (length(families) < 3L) return("UNAVAILABLE_LT_3_DEVELOPMENT_FAMILIES")
  for (family in families) {
    training <- rows[rows$study_family != family, , drop = FALSE]
    counts <- count_classes(training)
    if (any(counts < 20L)) return("UNAVAILABLE_LEAVE_FAMILY_OUT_TRAINING_CLASS_FLOOR")
    if (length(unique(training$study_family)) < 2L) return("UNAVAILABLE_LEAVE_FAMILY_OUT_TRAINING_FAMILY_FLOOR")
  }
  "AVAILABLE"
}

run_freeze <- function(data) {
  primary <- primary_roster(data)
  adaptive <- adaptive_roster(data)
  primary_floor <- leave_family_training_floor_reason(primary)
  adaptive_floor <- leave_family_training_floor_reason(adaptive)
  if (!identical(primary_floor, "AVAILABLE")) {
    primary_fit <- list(available = FALSE, reason = primary_floor)
  } else {
    primary_fit <- fit_primary(primary, 20L, 3L)
  }
  if (!identical(adaptive_floor, "AVAILABLE")) {
    adaptive_fit <- list(available = FALSE, reason = adaptive_floor)
  } else {
    adaptive_fit <- fit_adaptive(adaptive, 20L, 3L)
  }
  status <- if (isTRUE(primary_fit$available)) {
    if (identical(cfg$data_classification, "SYNTHETIC_ONLY")) "AVAILABLE_SYNTHETIC_SOFTWARE_ONLY" else "AVAILABLE_REAL_RELEASED_FIT"
  } else primary_fit$reason
  equation <- list(
    schema = "a_p2_equation_v1",
    status = status,
    model = list(
      family = "binomial", alpha = 0, lambda = 0.1,
      standardize = FALSE, intercept = TRUE,
      solver = "glmnet 5.2", thresh = 1e-10, maxit = 1e6,
      objective = "mean logistic loss + (0.1/2) * sum(beta^2); unpenalized intercept",
      responder_label = "R", nonresponder_label = "NR"
    ),
    primary = equation_model(primary_fit, FALSE),
    cohort_adaptive = equation_model(adaptive_fit, TRUE),
    comparator = list(
      name = "CYT", definition = "sqrt(TPM_GZMA * TPM_PRF1)",
      offset = 0, gene_wise_standardization = FALSE
    ),
    primary_training_cohort_families = as.list(sort(unique(primary$study_family), method = "radix")),
    adaptive_training_cohort_families = as.list(sort(unique(adaptive$study_family), method = "radix")),
    transforms = list(
      panel_feature = "arithmetic mean over every member after the cohort-declared source transform",
      primary = "training-only pooled mean and sample SD (n-1)",
      cohort_adaptive = "within-study mean and sample SD (n-1); validation cohort moments are outcome-blinded"
    )
  )
  jsonlite::write_json(
    equation, file.path(out_dir, "equation.json"), auto_unbox = TRUE,
    pretty = TRUE, digits = NA, na = "null", null = "null"
  )
  write_tsv(rbind(diagnostic_row("PRIMARY_TPM", primary_fit), diagnostic_row("COHORT_ADAPTIVE_SENSITIVITY", adaptive_fit)), "fit_diagnostics.tsv")
}

adaptation_for_final <- function(rows) {
  result <- list()
  for (study in unique(rows$cohort)) {
    part <- rows[rows$cohort == study, , drop = FALSE]
    statistics <- study_statistics(part)
    if (!isTRUE(statistics$available)) return(list(available = FALSE, reason = paste(statistics$reason, study, sep = ":")))
    result[[study]] <- statistics$scaling
  }
  list(available = TRUE, scaling = result)
}

bootstrap_delta <- function(rows, learner, cyt, stream, task_id = NULL) {
  sampled <- bootstrap_indices(
    strata = rows$orr_class,
    row_key = rows$patient_id,
    study = rows$cohort,
    stream = stream,
    task_id = task_id,
    repetitions = 2000L
  )
  indices <- sampled$indices
  draws_by_replicate <- split(indices$row_index, indices$replicate)
  learner_values <- vapply(seq_len(2000L), function(replicate) {
    row_index <- draws_by_replicate[[as.character(replicate)]]
    auc_value(rows$orr_class[row_index], learner[row_index])
  }, numeric(1))
  cyt_values <- vapply(seq_len(2000L), function(replicate) {
    row_index <- draws_by_replicate[[as.character(replicate)]]
    auc_value(rows$orr_class[row_index], cyt[row_index])
  }, numeric(1))
  values <- learner_values - cyt_values
  if (length(values) != 2000L || any(!is.finite(values))) stop("A-P2 bootstrap produced an undefined paired AUROC draw")
  interval <- stats::quantile(values, probs = c(0.025, 0.975), names = FALSE, type = 7)
  list(indices = sampled, learner_values = learner_values, cyt_values = cyt_values,
    values = values, interval = interval)
}

run_final <- function(data, equation) {
  primary_rows <- primary_roster(data)
  adaptive_rows <- adaptive_roster(data)
  primary_model <- equation$primary
  adaptive_model <- equation$cohort_adaptive
  metrics <- list()
  predictions <- data.frame(
    analysis = character(), row_index = integer(), study = character(), cancer = character(),
    orr_class = character(), learner_score = numeric(), cyt_score = numeric(),
    stringsAsFactors = FALSE
  )
  bootstrap_table <- data.frame(
    replicate = integer(), learner_auc = numeric(), cyt_auc = numeric(), delta_auc = numeric()
  )
  bootstrap_summary <- data.frame(
    stream = character(), repetitions = integer(), confidence_level = numeric(),
    lower_95 = numeric(), upper_95 = numeric(), conditional_on = character(),
    stringsAsFactors = FALSE
  )
  second_check <- data.frame(
    stream = character(), repetitions = integer(), lower_95 = numeric(),
    upper_95 = numeric(), lower_endpoint_difference = numeric(),
    upper_endpoint_difference = numeric(), discrepancy_threshold = numeric(),
    discrepancy_flag = logical(), replaces_main_result = logical(),
    stringsAsFactors = FALSE
  )
  adaptive_external_scaling <- data.frame(
    study = character(), feature = character(), mean = numeric(), sd = numeric(),
    scope = character(), status = character(), stringsAsFactors = FALSE
  )
  if (!isTRUE(primary_model$available) || !nrow(primary_rows)) {
    metrics[[length(metrics) + 1L]] <- data.frame(
      analysis = "PRIMARY_TPM", evaluation_label = cfg$final_test_label,
      inference_status = "NOT_ESTIMABLE",
      status = "UNAVAILABLE_FINAL_MEASUREMENT_OR_EQUATION",
      n = nrow(primary_rows), responders = sum(primary_rows$orr_class == "R"),
      nonresponders = sum(primary_rows$orr_class == "NR"), learner_auc = NA_real_,
      cyt_auc = NA_real_, delta_auc = NA_real_, lower_95 = NA_real_, upper_95 = NA_real_,
      second_check_flag = NA, reason = "final input is not primary-eligible or frozen primary equation is unavailable",
      stringsAsFactors = FALSE
    )
  } else {
    score <- as.numeric(stats::plogis(primary_model$intercept +
      sweep(sweep(as.matrix(primary_rows[, feature_names, drop = FALSE]), 2L,
        vapply(feature_names, function(feature) primary_model$scaling[[feature]]$mean, numeric(1)), "-"),
        2L, vapply(feature_names, function(feature) primary_model$scaling[[feature]]$sd, numeric(1)), "/") %*%
      vapply(feature_names, function(feature) as.numeric(primary_model$coefficients[[feature]]), numeric(1))))
    primary_counts <- count_classes(primary_rows)
    learner_auc <- auc_value(primary_rows$orr_class, score)
    cyt_complete <- all(is.finite(primary_rows$CYT)) && all(vapply(unique(primary_rows$cohort), function(study) isTRUE(cfg$cohorts[[study]]$cyt_available), logical(1)))
    cyt_auc <- if (cyt_complete) auc_value(primary_rows$orr_class, primary_rows$CYT) else NA_real_
    class_floor <- all(primary_counts >= 10L)
    family_floor <- length(unique(primary_rows$study_family)) == 1L
    paired_available <- class_floor && family_floor && is.finite(learner_auc) && is.finite(cyt_auc)
    status <- if (!family_floor) "UNAVAILABLE_FINAL_FAMILY_FLOOR" else if (!class_floor) "UNAVAILABLE_FINAL_CLASS_FLOOR_DESCRIPTIVE_ONLY" else if (!is.finite(learner_auc)) "UNAVAILABLE_FINAL_AUC" else if (!cyt_complete || !is.finite(cyt_auc)) "UNAVAILABLE_PAIRED_CYT" else "AVAILABLE"
    lower <- upper <- NA_real_
    flag <- NA
    if (paired_available) {
      main <- bootstrap_delta(primary_rows, score, primary_rows$CYT, "a_p2_bootstrap")
      check <- bootstrap_delta(primary_rows, score, primary_rows$CYT, "second_check", "a_p2_bootstrap")
      lower <- main$interval[[1L]]
      upper <- main$interval[[2L]]
      flag <- abs(main$interval[[1L]] - check$interval[[1L]]) > 0.01 ||
        abs(main$interval[[2L]] - check$interval[[2L]]) > 0.01
      bootstrap_table <- data.frame(
        replicate = seq_len(2000L), learner_auc = main$learner_values,
        cyt_auc = main$cyt_values, delta_auc = main$values, stringsAsFactors = FALSE
      )
      bootstrap_summary <- data.frame(
        stream = "a_p2_bootstrap", repetitions = 2000L,
        confidence_level = 0.95, lower_95 = lower, upper_95 = upper,
        conditional_on = "fitted equation and observed final-test cohort",
        stringsAsFactors = FALSE
      )
      second_check <- data.frame(
        stream = "second_check", repetitions = 2000L,
        lower_95 = check$interval[[1L]], upper_95 = check$interval[[2L]],
        lower_endpoint_difference = abs(main$interval[[1L]] - check$interval[[1L]]),
        upper_endpoint_difference = abs(main$interval[[2L]] - check$interval[[2L]]),
        discrepancy_threshold = 0.01, discrepancy_flag = flag,
        replaces_main_result = FALSE, stringsAsFactors = FALSE
      )
      publish_random_receipt(
        main$indices, "main_bootstrap", "bootstrap_assignments.tsv",
        "bootstrap_receipt.json", "a_p2_bootstrap",
        operation = "A-P2 paired ORR bootstrap"
      )
      publish_random_receipt(
        check$indices, "second_check_bootstrap", "second_check_assignments.tsv",
        "second_check_receipt.json", "second_check", task_id = "a_p2_bootstrap",
        operation = "reported-only A-P2 second-check bootstrap"
      )
    } else {
      bootstrap_summary <- data.frame(
        stream = "a_p2_bootstrap", repetitions = 0L,
        confidence_level = 0.95, lower_95 = NA_real_, upper_95 = NA_real_,
        conditional_on = "not_run_below final class/family or paired-score floor",
        stringsAsFactors = FALSE
      )
      second_check <- data.frame(
        stream = "second_check", repetitions = 0L, lower_95 = NA_real_, upper_95 = NA_real_,
        lower_endpoint_difference = NA_real_, upper_endpoint_difference = NA_real_,
        discrepancy_threshold = 0.01, discrepancy_flag = NA, replaces_main_result = FALSE,
        stringsAsFactors = FALSE
      )
    }
    inference_status <- if (!class_floor) {
      "DESCRIPTIVE_ONLY_BELOW_10_PER_CLASS"
    } else if (!family_floor || !is.finite(learner_auc) || !is.finite(cyt_auc)) {
      "NOT_ESTIMABLE_PAIRED_COMPARISON"
    } else if (lower <= 0 && upper >= 0) {
      "INCONCLUSIVE_INTERVAL_SPANS_ZERO"
    } else {
      "INTERVAL_DOES_NOT_SPAN_ZERO"
    }
    metrics[[length(metrics) + 1L]] <- data.frame(
      analysis = "PRIMARY_TPM", evaluation_label = cfg$final_test_label,
      inference_status = inference_status, status = status, n = nrow(primary_rows),
      responders = primary_counts[["R"]], nonresponders = primary_counts[["NR"]],
      learner_auc = learner_auc, cyt_auc = cyt_auc,
      delta_auc = if (is.finite(learner_auc) && is.finite(cyt_auc)) learner_auc - cyt_auc else NA_real_,
      lower_95 = lower, upper_95 = upper, second_check_flag = flag,
      reason = if (status == "AVAILABLE") "" else status,
      stringsAsFactors = FALSE
    )
    predictions <- data.frame(
      analysis = "PRIMARY_TPM", row_index = primary_rows$row_index, study = primary_rows$cohort,
      cancer = primary_rows$cancer, orr_class = primary_rows$orr_class,
      learner_score = score, cyt_score = primary_rows$CYT,
      stringsAsFactors = FALSE
    )
  }
  if (isTRUE(adaptive_model$available) && nrow(adaptive_rows)) {
    adaptive_fit <- list(
      available = TRUE,
      coefficients = vapply(feature_names, function(feature) as.numeric(adaptive_model$coefficients[[feature]]), numeric(1)),
      intercept = as.numeric(adaptive_model$intercept),
      scaling_by_study = adaptive_model$scaling_by_study
    )
    adapted <- adaptation_for_final(adaptive_rows)
    if (isTRUE(adapted$available)) {
      adaptive_external_scaling <- do.call(rbind, lapply(names(adapted$scaling), function(study) {
        do.call(rbind, lapply(feature_names, function(feature) {
          value <- adapted$scaling[[study]][[feature]]
          data.frame(
            study = study, feature = feature, mean = value$mean, sd = value$sd,
            scope = "EXTERNAL_COHORT_OUTCOME_BLINDED", status = "AVAILABLE",
            stringsAsFactors = FALSE
          )
        }))
      }))
      score <- model_scores(adaptive_fit, adaptive_rows, TRUE, adapted$scaling)
      summary <- cohort_summary(adaptive_rows, unique(adaptive_rows$cohort)[[1L]], score,
        "AVAILABLE", TRUE, adapted$scaling)
      metrics[[length(metrics) + 1L]] <- data.frame(
        analysis = "COHORT_ADAPTIVE_SENSITIVITY_DESCRIPTIVE",
        evaluation_label = cfg$adaptive_final_label,
        inference_status = "DESCRIPTIVE_SENSITIVITY_NO_INFERENCE",
        status = summary$comparison_status, n = summary$n,
        responders = summary$responders, nonresponders = summary$nonresponders,
        learner_auc = summary$learner_auc, cyt_auc = summary$cyt_auc,
        delta_auc = summary$delta_auc, lower_95 = NA_real_, upper_95 = NA_real_,
        second_check_flag = NA,
        reason = if (summary$cyt_status == "AVAILABLE") "descriptive sensitivity; learner and CYT use same patients" else summary$cyt_status,
        stringsAsFactors = FALSE
      )
      predictions <- rbind(predictions, data.frame(
        analysis = "COHORT_ADAPTIVE_SENSITIVITY", row_index = adaptive_rows$row_index, study = adaptive_rows$cohort,
        cancer = adaptive_rows$cancer, orr_class = adaptive_rows$orr_class,
        learner_score = score,
        cyt_score = ifelse(is.finite(adaptive_rows$CYT), adaptive_rows$CYT, NA_real_),
        stringsAsFactors = FALSE
      ))
    } else {
      adaptive_external_scaling <- do.call(rbind, lapply(unique(adaptive_rows$cohort), function(study) {
        data.frame(
          study = study, feature = feature_names, mean = NA_real_, sd = NA_real_,
          scope = "EXTERNAL_COHORT_OUTCOME_BLINDED", status = adapted$reason,
          stringsAsFactors = FALSE
        )
      }))
      metrics[[length(metrics) + 1L]] <- data.frame(
        analysis = "COHORT_ADAPTIVE_SENSITIVITY_DESCRIPTIVE",
        evaluation_label = cfg$adaptive_final_label,
        inference_status = "NOT_ESTIMABLE",
        status = adapted$reason, n = nrow(adaptive_rows),
        responders = sum(adaptive_rows$orr_class == "R"), nonresponders = sum(adaptive_rows$orr_class == "NR"),
        learner_auc = NA_real_, cyt_auc = NA_real_, delta_auc = NA_real_,
        lower_95 = NA_real_, upper_95 = NA_real_, second_check_flag = NA,
        reason = adapted$reason, stringsAsFactors = FALSE
      )
    }
  } else {
    if (nrow(adaptive_rows)) {
      adaptive_external_scaling <- do.call(rbind, lapply(unique(adaptive_rows$cohort), function(study) {
        data.frame(
          study = study, feature = feature_names, mean = NA_real_, sd = NA_real_,
          scope = "EXTERNAL_COHORT_OUTCOME_BLINDED", status = adaptive_model$status,
          stringsAsFactors = FALSE
        )
      }))
    }
    metrics[[length(metrics) + 1L]] <- data.frame(
      analysis = "COHORT_ADAPTIVE_SENSITIVITY_DESCRIPTIVE",
      evaluation_label = cfg$adaptive_final_label,
      inference_status = "NOT_ESTIMABLE",
      status = if (nrow(adaptive_rows)) adaptive_model$status else "UNAVAILABLE_NO_ADAPTIVE_ELIGIBLE_ROWS",
      n = nrow(adaptive_rows), responders = sum(adaptive_rows$orr_class == "R"),
      nonresponders = sum(adaptive_rows$orr_class == "NR"), learner_auc = NA_real_,
      cyt_auc = NA_real_, delta_auc = NA_real_, lower_95 = NA_real_, upper_95 = NA_real_,
      second_check_flag = NA, reason = adaptive_model$status,
      stringsAsFactors = FALSE
    )
  }
  write_tsv(do.call(rbind, metrics), "final_metrics.tsv")
  write_tsv(predictions, "predictions.tsv")
  write_tsv(bootstrap_table, "bootstrap.tsv")
  write_tsv(adaptive_external_scaling, "adaptive_external_scaling.tsv")
  write_tsv(bootstrap_summary, "bootstrap_summary.tsv")
  write_tsv(second_check, "second_check.tsv")
  if (!file.exists(file.path(out_dir, "bootstrap_assignments.tsv"))) {
    empty_assignments <- data.frame(
      replicate = integer(), stratum = character(), draw = integer(), row_index = integer()
    )
    write_tsv(empty_assignments, "bootstrap_assignments.tsv")
    write_tsv(empty_assignments, "second_check_assignments.tsv")
    bootstrap_assignments_hash <- digest::digest(
      file = file.path(out_dir, "bootstrap_assignments.tsv"), algo = "sha256", serialize = FALSE
    )
    second_assignments_hash <- digest::digest(
      file = file.path(out_dir, "second_check_assignments.tsv"), algo = "sha256", serialize = FALSE
    )
    jsonlite::write_json(list(
      stream = "a_p2_bootstrap", status = "UNAVAILABLE_FINAL_CLASS_FAMILY_OR_PAIRED_SCORE_FLOOR",
      random_draws = FALSE, assignments_file = "bootstrap_assignments.tsv",
      assignments_sha256 = bootstrap_assignments_hash
    ), file.path(out_dir, "bootstrap_receipt.json"), auto_unbox = TRUE, pretty = TRUE)
    jsonlite::write_json(list(
      stream = "second_check", status = "NOT_RUN_WITHOUT_MAIN_BOOTSTRAP",
      reported_only = TRUE, random_draws = FALSE,
      assignments_file = "second_check_assignments.tsv",
      assignments_sha256 = second_assignments_hash
    ), file.path(out_dir, "second_check_receipt.json"), auto_unbox = TRUE, pretty = TRUE)
    file.copy(file.path(out_dir, "bootstrap_assignments.tsv"), file.path(cfg$work_dir, "bootstrap_assignments.tsv"), overwrite = TRUE)
    file.copy(file.path(out_dir, "bootstrap_receipt.json"), file.path(cfg$work_dir, "bootstrap_receipt.json"), overwrite = TRUE)
    file.copy(file.path(out_dir, "second_check_assignments.tsv"), file.path(cfg$work_dir, "second_check_assignments.tsv"), overwrite = TRUE)
    file.copy(file.path(out_dir, "second_check_receipt.json"), file.path(cfg$work_dir, "second_check_receipt.json"), overwrite = TRUE)
  }
}

.read_exact_file_bytes <- function(path) {
  info <- file.info(path)
  if (is.na(info$size) || info$isdir) stop("A-P2 verified input snapshot is unavailable")
  readBin(path, what = "raw", n = info$size)
}

input_bytes <- .read_exact_file_bytes(bridge$inputs$features)
staged_input_sha256 <- digest::digest(input_bytes, algo = "sha256", serialize = FALSE)
if (!identical(staged_input_sha256, cfg$input_sha256)) {
  stop("A-P2 staged input hash does not match the authorized input manifest")
}
data <- read_features(input_bytes)
if (identical(cfg$operation, "test-solver-failure-contract")) {
  if (!identical(cfg$data_classification, "SYNTHETIC_ONLY")) stop("Fault injection is restricted to invented data")
  solver_calls <- 0L
  previous_options <- options(a_p2.glmnet_solver = function(...) {
    solver_calls <<- solver_calls + 1L
    warning("invented solver warning paired with nonzero jerr", call. = FALSE)
    list(jerr = 17L)
  })
  failure <- tryCatch({
    leave_family_out(primary_roster(data), FALSE)
    "NO_FAILURE"
  }, error = function(error) conditionMessage(error))
  options(previous_options)
  write_tsv(data.frame(
    status = if (solver_calls == 1L && grepl("jerr", failure, ignore.case = TRUE)) "EXPECTED_STOP" else "FAILED_TO_STOP",
    jerr = 17L, fit_attempts = solver_calls,
    later_fit_executed = solver_calls > 1L,
    stringsAsFactors = FALSE
  ), "solver_fault_injection.tsv")
} else if (identical(cfg$operation, "test-leakage-family-contract")) {
  if (!identical(cfg$data_classification, "SYNTHETIC_ONLY")) stop("Leakage contract test is restricted to invented data")
  held_family <- cfg$test_only_family
  if (!is.character(held_family) || length(held_family) != 1L || !nzchar(held_family)) {
    stop("Leakage contract test needs one named invented family")
  }
  primary <- primary_roster(data)
  adaptive <- adaptive_roster(data)
  if (!held_family %in% unique(primary$study_family)) stop("Invented held-out family is not in the test roster")
  primary_train <- primary[primary$study_family != held_family, , drop = FALSE]
  adaptive_train <- adaptive[adaptive$study_family != held_family, , drop = FALSE]
  primary_fit <- fit_primary(primary_train, 20L, 2L)
  adaptive_fit <- fit_adaptive(adaptive_train, 20L, 2L)
  records <- list(
    family_model_rows("PRIMARY_TPM", held_family, primary_fit, FALSE),
    family_model_rows("COHORT_ADAPTIVE_SENSITIVITY", held_family, adaptive_fit, TRUE)
  )
  if (isTRUE(adaptive_fit$available)) {
    for (study in sort(unique(adaptive$cohort[adaptive$study_family == held_family]), method = "radix")) {
      statistics <- study_statistics(adaptive[adaptive$cohort == study & adaptive$study_family == held_family, , drop = FALSE])
      if (!isTRUE(statistics$available)) stop("Invented held-out adaptive scaling is unavailable")
      for (feature in feature_names) {
        value <- statistics$scaling[[feature]]
        records[[length(records) + 1L]] <- data.frame(
          analysis = "COHORT_ADAPTIVE_SENSITIVITY", held_out_family = held_family,
          study_scope = paste0("HELD_OUT_OUTCOME_BLINDED:", study),
          feature = feature, mean = value$mean, sd = value$sd,
          coefficient = NA_real_, intercept = NA_real_,
          status = "AVAILABLE_OUTCOME_BLINDED", stringsAsFactors = FALSE
        )
      }
    }
  }
  write_tsv(do.call(rbind, records), "leakage_model.tsv")
} else if (identical(cfg$operation, "development")) {
  run_development(data)
} else if (identical(cfg$operation, "freeze")) {
  run_freeze(data)
} else if (identical(cfg$operation, "final-evaluate")) {
  if (is.null(bridge$inputs$equation)) stop("Final evaluation needs the frozen equation input")
  equation_bytes <- .read_exact_file_bytes(bridge$inputs$equation)
  equation_file_sha256 <- digest::digest(equation_bytes, algo = "sha256", serialize = FALSE)
  if (!identical(equation_file_sha256, cfg$equation_file_sha256)) {
    stop("A-P2 frozen equation snapshot changed before scoring")
  }
  equation <- jsonlite::fromJSON(rawToChar(equation_bytes), simplifyVector = FALSE)
  run_final(data, equation)
} else {
  stop("Unknown A-P2 operation")
}
bridge_write_session(out_dir)
