NUMERICAL_RANDOM_STREAMS <- data.frame(
  stream = c(
    "a_p2_bootstrap", "a_p2_splits", "fgsea", "sc_embedding",
    "b_bootstrap", "second_check", "a_p1_bootstrap"
  ),
  seed = c(20261102L, 20261103L, 20261104L, 20261105L, 20261106L, 20261107L, 20261108L),
  task_id = c(
    "one task", "<study>|rep<01-20>", "<dataset>|<endpoint>|<collection>",
    "<atlas>", "set by Paper B contract", "<stream>", "one task"
  ),
  role = c(
    "signed A-P2 bootstrap", "A-P2 split sensitivity", "fgsea", "single-cell embedding",
    "Paper B bootstrap", "reported-only Monte Carlo check", "A-P1 bootstrap"
  ),
  reported_only = c(FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE),
  stringsAsFactors = FALSE
)

random_stream_seed <- function(stream) {
  row <- NUMERICAL_RANDOM_STREAMS[NUMERICAL_RANDOM_STREAMS$stream == stream, , drop = FALSE]
  if (nrow(row) != 1L) stop("Unknown random stream")
  as.integer(row$seed[[1L]])
}

random_task_seed <- function(stream, task_id) {
  if (length(task_id) != 1L || is.na(task_id) || !nzchar(task_id)) {
    stop("Task ID must be one non-empty string")
  }
  payload <- paste0(random_stream_seed(stream), "|", enc2utf8(task_id))
  hash <- digest::digest(payload, algo = "sha256", serialize = FALSE)
  strtoi(substr(hash, 1L, 7L), base = 16L)
}

random_seed_for_task <- function(stream, task_id = NULL) {
  row <- NUMERICAL_RANDOM_STREAMS[NUMERICAL_RANDOM_STREAMS$stream == stream, , drop = FALSE]
  if (nrow(row) != 1L) stop("Unknown random stream")
  if (identical(row$task_id[[1L]], "one task")) {
    if (!is.null(task_id)) stop("This stream has one task and uses its root seed directly")
    return(as.integer(row$seed[[1L]]))
  }
  if (is.null(task_id)) stop("This stream requires a task ID")
  random_task_seed(stream, task_id)
}

bootstrap_indices <- function(
  strata,
  row_key = as.character(seq_along(strata)),
  study,
  stream = "a_p2_bootstrap",
  task_id = NULL,
  repetitions = 2000L
) {
  strata <- as.character(strata)
  order_levels <- .bootstrap_strata(stream, strata)
  if (length(row_key) != length(strata) || length(study) != length(strata) ||
      anyNA(row_key) || anyNA(study) || anyNA(strata) || any(!nzchar(row_key)) ||
      any(!nzchar(study)) || !length(strata)) {
    stop("Bootstrap rows require non-empty study, row key and stratum values")
  }
  repetitions <- as.integer(repetitions)
  if (length(repetitions) != 1L || is.na(repetitions) || repetitions < 1L) {
    stop("Bootstrap repetitions must be positive")
  }
  stream_row <- NUMERICAL_RANDOM_STREAMS[
    NUMERICAL_RANDOM_STREAMS$stream == stream, , drop = FALSE
  ]
  if (nrow(stream_row) != 1L) stop("Unknown random stream")
  seed <- random_seed_for_task(stream, task_id)

  row_order <- order(enc2utf8(study), enc2utf8(row_key), method = "radix")
  ordered_strata <- strata[row_order]
  set.seed(seed, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
  assignments <- vector("list", repetitions * length(order_levels))
  cursor <- 0L
  for (replicate in seq_len(repetitions)) {
    for (level in order_levels) {
      rows <- row_order[ordered_strata == level]
      if (!length(rows)) next
      sampled <- rows[sample.int(length(rows), length(rows), replace = TRUE)]
      cursor <- cursor + 1L
      assignments[[cursor]] <- data.frame(
        replicate = replicate,
        stratum = level,
        draw = seq_along(sampled),
        row_index = sampled,
        stringsAsFactors = FALSE
      )
    }
  }
  result <- do.call(rbind, assignments[seq_len(cursor)])
  list(indices = result, seed = seed, receipt_sha256 = .random_receipt_hash(result))
}

split_indices <- function(
  study,
  row_key,
  strata,
  repetitions = 20L,
  stream = "a_p2_splits"
) {
  study <- as.character(study)
  row_key <- as.character(row_key)
  strata <- as.character(strata)
  if (!length(study) || length(study) != length(row_key) || length(study) != length(strata) ||
      anyNA(study) || anyNA(row_key) || anyNA(strata) || any(!nzchar(study)) ||
      any(!nzchar(row_key)) || any(!nzchar(strata))) {
    stop("Split rows require non-empty study, row key and stratum values")
  }
  if (stream != "a_p2_splits") stop("The signed split stream is a_p2_splits")
  if (!all(strata %in% c("R", "NR"))) stop("A-P2 split strata must be R then NR")
  repetitions <- as.integer(repetitions)
  if (length(repetitions) != 1L || is.na(repetitions) || repetitions < 1L || repetitions > 20L) {
    stop("The signed split contract allows 1 to 20 of its 20 repeats")
  }
  row_order <- order(enc2utf8(study), enc2utf8(row_key), method = "radix")
  studies <- unique(study[row_order])
  assignments <- list()
  task_seeds <- list()
  cursor <- 0L
  for (study_id in studies) {
    for (replicate in seq_len(repetitions)) {
      task_id <- paste0(study_id, "|rep", sprintf("%02d", replicate))
      seed <- random_seed_for_task(stream, task_id)
      task_seeds[[length(task_seeds) + 1L]] <- data.frame(
        study = study_id, replicate = replicate, task_id = task_id, seed = seed,
        stringsAsFactors = FALSE
      )
      set.seed(seed, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
      for (level in c("R", "NR")) {
        rows <- row_order[study[row_order] == study_id & strata[row_order] == level]
        if (!length(rows)) next
        permutation <- rows[sample.int(length(rows))]
        n_train <- floor(0.7 * length(rows) + 0.5)
        partition <- c(rep("train", n_train), rep("test", length(rows) - n_train))
        cursor <- cursor + 1L
        assignments[[cursor]] <- data.frame(
          study = study_id,
          replicate = replicate,
          stratum = level,
          partition = partition,
          position = seq_along(permutation),
          row_index = permutation,
          stringsAsFactors = FALSE
        )
      }
    }
  }
  result <- do.call(rbind, assignments[seq_len(cursor)])
  list(
    indices = result,
    task_seeds = do.call(rbind, task_seeds),
    receipt_sha256 = .random_receipt_hash(result)
  )
}

write_random_receipt <- function(result, output_dir, stream, task_id = "", operation) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  assignments_path <- file.path(output_dir, "assignments.tsv")
  utils::write.table(
    result$indices, assignments_path, sep = "\t", row.names = FALSE,
    col.names = TRUE, quote = FALSE, na = "NA"
  )
  stream_row <- NUMERICAL_RANDOM_STREAMS[
    NUMERICAL_RANDOM_STREAMS$stream == stream, , drop = FALSE
  ]
  if (nrow(stream_row) != 1L) stop("Unknown random stream")
  manifest <- list(
    operation = operation,
    stream = stream,
    role = stream_row$role[[1L]],
    reported_only = stream_row$reported_only[[1L]],
    task_id = task_id,
    seed = result$seed %||% NA_integer_,
    rng = list(kind = "Mersenne-Twister", normal_kind = "Inversion", sample_kind = "Rejection"),
    receipt_sha256 = result$receipt_sha256,
    assignments_sha256 = digest::digest(file = assignments_path, algo = "sha256", serialize = FALSE),
    assignments_file = "assignments.tsv",
    task_seeds = result$task_seeds
  )
  jsonlite::write_json(manifest, file.path(output_dir, "receipt.json"), auto_unbox = TRUE, pretty = TRUE)
  invisible(manifest)
}

`%||%` <- function(left, right) if (is.null(left)) right else left

.bootstrap_strata <- function(stream, strata) {
  expected <- switch(
    stream,
    a_p2_bootstrap = c("R", "NR"),
    a_p1_bootstrap = c("O", "SD", "PD"),
    second_check = if (all(strata %in% c("R", "NR"))) c("R", "NR") else c("O", "SD", "PD"),
    stop("Unsupported bootstrap stream")
  )
  if (!all(strata %in% expected)) stop("Bootstrap strata do not match the signed stream contract")
  expected
}

.random_receipt_hash <- function(assignments) {
  lines <- capture.output(utils::write.table(
    assignments, sep = "\t", row.names = FALSE,
    col.names = TRUE, quote = FALSE, na = "NA"
  ))
  payload <- paste0(paste(lines, collapse = "\n"), "\n")
  digest::digest(payload, algo = "sha256", serialize = FALSE)
}
