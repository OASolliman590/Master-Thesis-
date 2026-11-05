source("R/bridge.R")
bridge_require(c("jsonlite", "digest"))
bridge <- bridge_config()
out_dir <- bridge$output_dir
source("R/random_streams.R")

test_streams <- c("a_p2_splits", "fgsea", "sc_embedding", "second_check")
test_tasks <- c(
  "synthetic_study|rep01",
  "synthetic_dataset|orr|hallmark_2026.1.Hs",
  "synthetic_atlas",
  "fgsea"
)
task_seeds <- data.frame(
  stream = test_streams,
  task_id = test_tasks,
  seed = vapply(seq_along(test_streams), function(index) {
    random_task_seed(test_streams[[index]], test_tasks[[index]])
  }, integer(1)),
  stringsAsFactors = FALSE
)

strata <- c("NR", "R", "NR", "R", "R", "NR", "R", "R")
row_keys <- c("z", "e", "a", "c", "b", "x", "d", "f")
study <- rep("synthetic_study", length(strata))
bootstrap <- bootstrap_indices(strata, row_key = row_keys, study = study, repetitions = 8L)
bootstrap_repeat <- bootstrap_indices(strata, row_key = row_keys, study = study, repetitions = 8L)
bootstrap_other_seed <- bootstrap_indices(
  strata, row_key = row_keys, study = study,
  stream = "second_check", task_id = "a_p2_bootstrap", repetitions = 8L
)
reorder <- c(8L, 3L, 1L, 6L, 4L, 2L, 7L, 5L)
bootstrap_reordered <- bootstrap_indices(
  strata[reorder], row_key = row_keys[reorder], study = study[reorder], repetitions = 8L
)
bootstrap_keys <- data.frame(
  replicate = bootstrap$indices$replicate,
  stratum = bootstrap$indices$stratum,
  draw = bootstrap$indices$draw,
  row_key = row_keys[bootstrap$indices$row_index],
  stringsAsFactors = FALSE
)
bootstrap_reordered_keys <- data.frame(
  replicate = bootstrap_reordered$indices$replicate,
  stratum = bootstrap_reordered$indices$stratum,
  draw = bootstrap_reordered$indices$draw,
  row_key = row_keys[reorder][bootstrap_reordered$indices$row_index],
  stringsAsFactors = FALSE
)

tiny_study <- rep("synthetic_tiny", 5L)
tiny_keys <- c("key_z", "key_a", "key_m", "key_b", "key_y")
tiny_strata <- c("R", "R", "NR", "NR", "R")
tiny_bootstrap <- bootstrap_indices(
  tiny_strata, row_key = tiny_keys, study = tiny_study, repetitions = 4L
)
tiny_order <- order(enc2utf8(tiny_study), enc2utf8(tiny_keys), method = "radix")
set.seed(
  random_seed_for_task("a_p2_bootstrap"), kind = "Mersenne-Twister",
  normal.kind = "Inversion", sample.kind = "Rejection"
)
tiny_expected_rows <- list()
tiny_cursor <- 0L
for (replicate in seq_len(4L)) {
  for (level in c("R", "NR")) {
    rows <- tiny_order[tiny_strata[tiny_order] == level]
    sampled <- rows[sample.int(length(rows), length(rows), replace = TRUE)]
    tiny_cursor <- tiny_cursor + 1L
    tiny_expected_rows[[tiny_cursor]] <- data.frame(
      replicate = replicate,
      stratum = level,
      draw = seq_along(sampled),
      row_key = tiny_keys[sampled],
      stringsAsFactors = FALSE
    )
  }
}
tiny_expected <- do.call(rbind, tiny_expected_rows)
tiny_actual <- data.frame(
  replicate = tiny_bootstrap$indices$replicate,
  stratum = tiny_bootstrap$indices$stratum,
  draw = tiny_bootstrap$indices$draw,
  row_key = tiny_keys[tiny_bootstrap$indices$row_index],
  stringsAsFactors = FALSE
)

p1_strata <- c("PD", "O", "SD", "O", "PD", "SD", "O")
p1 <- bootstrap_indices(
  p1_strata, row_key = paste0("key", seq_along(p1_strata)),
  study = rep("synthetic_p1", length(p1_strata)),
  stream = "a_p1_bootstrap", repetitions = 5L
)

splits <- split_indices(study, row_keys, strata, repetitions = 20L)
splits_reordered <- split_indices(
  study[reorder], row_keys[reorder], strata[reorder], repetitions = 20L
)
split_keys <- data.frame(
  study = splits$indices$study,
  replicate = splits$indices$replicate,
  stratum = splits$indices$stratum,
  partition = splits$indices$partition,
  position = splits$indices$position,
  row_key = row_keys[splits$indices$row_index],
  stringsAsFactors = FALSE
)
split_reordered_keys <- data.frame(
  study = splits_reordered$indices$study,
  replicate = splits_reordered$indices$replicate,
  stratum = splits_reordered$indices$stratum,
  partition = splits_reordered$indices$partition,
  position = splits_reordered$indices$position,
  row_key = row_keys[reorder][splits_reordered$indices$row_index],
  stringsAsFactors = FALSE
)
odd_n <- splits$indices[
  splits$indices$replicate == 1L & splits$indices$stratum == "R", , drop = FALSE
]

receipt_root <- bridge$config$receipt_dir
if (length(receipt_root) != 1L || is.na(receipt_root) || !nzchar(receipt_root)) {
  stop("A synthetic receipt directory is required for this software check")
}
write_random_receipt(bootstrap, file.path(receipt_root, "bootstrap"), "a_p2_bootstrap", operation = "bootstrap")
write_random_receipt(p1, file.path(receipt_root, "bootstrap_p1"), "a_p1_bootstrap", operation = "bootstrap")
write_random_receipt(splits, file.path(receipt_root, "splits"), "a_p2_splits", operation = "split")

checks <- data.frame(
  check = c(
    "a_p2_repeat_identical", "a_p2_other_seed_differs", "a_p2_strata_order", "a_p1_strata_order",
    "split_r_train_odd_n", "split_nr_train_odd_n", "a_p2_receipt_present",
    "a_p2_receipt_matches_assignments", "split_receipt_present",
    "split_receipt_matches_assignments", "a_p2_reordered_input_equivalent",
    "split_reordered_input_equivalent", "a_p2_tiny_expected_assignment"
  ),
  value = c(
    identical(bootstrap$indices, bootstrap_repeat$indices),
    !identical(bootstrap$indices, bootstrap_other_seed$indices),
    paste(unique(bootstrap$indices$stratum), collapse = ","),
    paste(unique(p1$indices$stratum), collapse = ","),
    sum(odd_n$partition == "train"),
    sum(splits$indices$replicate == 1L & splits$indices$stratum == "NR" & splits$indices$partition == "train"),
    file.exists(file.path(receipt_root, "bootstrap", "receipt.json")),
    jsonlite::fromJSON(file.path(receipt_root, "bootstrap", "receipt.json"))$assignments_sha256 ==
      digest::digest(file = file.path(receipt_root, "bootstrap", "assignments.tsv"), algo = "sha256", serialize = FALSE),
    file.exists(file.path(receipt_root, "splits", "receipt.json")),
    jsonlite::fromJSON(file.path(receipt_root, "splits", "receipt.json"))$assignments_sha256 ==
      digest::digest(file = file.path(receipt_root, "splits", "assignments.tsv"), algo = "sha256", serialize = FALSE),
    identical(bootstrap_keys, bootstrap_reordered_keys),
    identical(split_keys, split_reordered_keys),
    identical(tiny_actual, tiny_expected)
  ),
  stringsAsFactors = FALSE
)

if (!as.logical(checks$value[[1L]]) || !as.logical(checks$value[[2L]]) || checks$value[[3L]] != "R,NR" ||
    checks$value[[4L]] != "O,SD,PD" || checks$value[[5L]] != 4L || checks$value[[6L]] != 2L ||
    !all(as.logical(checks$value[7:10])) || !all(as.logical(checks$value[11:13]))) {
  stop("Random-stream software checks failed")
}
if (!identical(random_seed_for_task("a_p2_bootstrap"), random_stream_seed("a_p2_bootstrap"))) {
  stop("One-task root seed contract failed")
}
utils::write.table(task_seeds, file.path(out_dir, "task_seeds.tsv"), sep = "\t",
                   row.names = FALSE, quote = FALSE)
utils::write.table(NUMERICAL_RANDOM_STREAMS, file.path(out_dir, "random_stream_table.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE)
utils::write.table(checks, file.path(out_dir, "checks.tsv"), sep = "\t",
                   row.names = FALSE, quote = FALSE)
bridge_write_session(out_dir)
