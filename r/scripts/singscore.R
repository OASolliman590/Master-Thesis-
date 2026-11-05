source("R/bridge.R")
bridge_require(c("jsonlite", "digest", "BiocManager", "singscore"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir

family <- as.character(cfg$family)
if (!family %in% c("pathway", "pathway_coverage90", "pathway_common")) {
  stop("Unknown frozen pathway family")
}

gene_set_sha256 <- digest::digest(file = bridge$inputs$gene_sets, algo = "sha256", serialize = FALSE)
if (!identical(gene_set_sha256, as.character(cfg$gene_set_sha256))) {
  stop("Gene-set input hash differs from the feature contract")
}
test_only <- isTRUE(cfg$test_only_gene_sets)
if (!test_only && !identical(gene_set_sha256,
    "01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5")) {
  stop("Hallmark GMT does not match the signed numerical-freeze hash")
}

expression_table <- read.delim(
  bridge$inputs$expression,
  check.names = FALSE,
  stringsAsFactors = FALSE,
  na.strings = c("", "NA"),
  quote = ""
)
if (ncol(expression_table) < 2L || anyDuplicated(expression_table[[1L]])) {
  stop("Expression input must have unique genes and at least one patient row")
}
genes <- as.character(expression_table[[1L]])
expression <- as.matrix(expression_table[-1L])
rownames(expression) <- genes
storage.mode(expression) <- "double"
if (any(is.infinite(expression), na.rm = TRUE)) {
  stop("Expression input contains infinite values")
}

alias_table <- read.delim(
  bridge$inputs$aliases,
  check.names = FALSE,
  stringsAsFactors = FALSE,
  quote = ""
)
if (!all(c("source_symbol", "registry_symbol") %in% names(alias_table))) {
  stop("Frozen alias table has an unexpected schema")
}
aliases <- stats::setNames(as.character(alias_table$registry_symbol), as.character(alias_table$source_symbol))

gene_set_lines <- readLines(bridge$inputs$gene_sets, warn = FALSE, encoding = "UTF-8")
if (!length(gene_set_lines)) stop("Gene-set input is empty")
gene_sets <- lapply(gene_set_lines, function(line) {
  fields <- strsplit(line, "\t", fixed = TRUE)[[1L]]
  if (length(fields) < 3L || !nzchar(fields[[1L]])) {
    stop("Gene-set input must use GMT rows: name, description, genes")
  }
  members <- as.character(fields[-c(1L, 2L)])
  mapped <- unname(aliases[members])
  mapped[is.na(mapped)] <- members[is.na(mapped)]
  if (anyDuplicated(mapped)) stop("Frozen aliases collapse duplicate genes within a set")
  mapped
})
names(gene_sets) <- vapply(gene_set_lines, function(line) {
  strsplit(line, "\t", fixed = TRUE)[[1L]][[1L]]
}, character(1L))
if (anyDuplicated(names(gene_sets))) stop("Gene-set names must be unique")

common_sets <- NULL
if (family == "pathway_common") {
  if (!identical(as.integer(cfg$minimum_common_membership), 10L)) {
    stop("Frozen common-gene scoring requires a minimum membership of 10")
  }
  if (is.null(bridge$inputs$common_gene_table)) stop("pathway_common requires the frozen common-gene table")
  common_sha256 <- digest::digest(file = bridge$inputs$common_gene_table, algo = "sha256", serialize = FALSE)
  if (!identical(common_sha256, as.character(cfg$common_gene_table_sha256)) ||
      !identical(common_sha256, "1ce5611a406b98d96016eed697ccaf2642df847ca0907fc7f877da65b9d53e51")) {
    stop("Common-gene table hash mismatch")
  }
  common_table <- read.delim(
    bridge$inputs$common_gene_table,
    check.names = FALSE,
    stringsAsFactors = FALSE,
    quote = ""
  )
  if (!all(c("hallmark_set", "n_common", "common_genes", "membership_sha256") %in% names(common_table)) ||
      anyDuplicated(common_table$hallmark_set) || nrow(common_table) != 50L) {
    stop("Frozen common-gene table has an unexpected schema")
  }
  common_sets <- stats::setNames(vector("list", nrow(common_table)), common_table$hallmark_set)
  for (index in seq_len(nrow(common_table))) {
    row <- common_table[index, , drop = FALSE]
    members <- strsplit(as.character(row$common_genes), ";", fixed = TRUE)[[1L]]
    if (length(members) != as.integer(row$n_common) || any(!nzchar(members)) ||
        !identical(members, sort(unique(members)))) {
      stop("Malformed common-gene membership")
    }
    payload <- paste0(paste(members, collapse = "\n"), "\n")
    membership_hash <- digest::digest(payload, algo = "sha256", serialize = FALSE)
    if (!identical(membership_hash, as.character(row$membership_sha256))) {
      stop("Common-gene membership hash mismatch")
    }
    mapped <- unname(aliases[members])
    mapped[is.na(mapped)] <- members[is.na(mapped)]
    if (anyDuplicated(mapped)) stop("Frozen aliases collapse duplicate common genes")
    common_sets[[as.character(row$hallmark_set)]] <- mapped
  }
}

if (family != "pathway_common" && length(gene_sets) != 50L && !test_only) {
  stop("The signed Hallmark GMT must contain exactly 50 sets")
}
if (family == "pathway_common" && !setequal(names(gene_sets), names(common_sets))) {
  stop("Common-gene memberships do not match the frozen Hallmark set names")
}

available <- rownames(expression)[vapply(seq_len(nrow(expression)), function(index) {
  any(is.finite(expression[index, ]))
}, logical(1L))]
score_rows <- list()
coverage_rows <- list()
for (unit in names(gene_sets)) {
  full_members <- gene_sets[[unit]]
  if (family == "pathway_common") {
    members <- common_sets[[unit]]
    n_total <- length(members)
    found <- intersect(members, available)
    missing <- setdiff(members, found)
    complete <- length(found) == n_total
    fixed_subset <- members
    minimum_met <- n_total >= as.integer(cfg$minimum_common_membership)
    scorable <- complete && minimum_met
    reason <- if (!minimum_met) "common_membership_below_10" else if (!complete) "common_gene_missing" else ""
  } else {
    members <- full_members
    n_total <- length(members)
    found <- intersect(members, available)
    missing <- setdiff(members, found)
    if (family == "pathway_coverage90") {
      fixed_subset <- found
      complete <- length(found) * 10L >= n_total * 9L
      scorable <- complete && length(fixed_subset) > 0L
      reason <- if (!complete) "study_coverage_below_90_percent" else ""
    } else {
      fixed_subset <- members
      complete <- length(found) == n_total
      scorable <- complete
      reason <- if (!complete) "incomplete_study_coverage" else ""
    }
  }
  selected <- if (scorable) fixed_subset else character()
  selected_indexes <- match(selected, rownames(expression))
  if (anyNA(selected_indexes)) stop("Scorable singscore membership is absent from the study matrix")
  non_member_indexes <- setdiff(seq_len(nrow(expression)), selected_indexes)
  sample_scores <- rep(NA_real_, ncol(expression))
  if (length(selected_indexes)) {
    for (sample_index in seq_len(ncol(expression))) {
      sample_values <- expression[, sample_index]
      if (any(!is.finite(sample_values[non_member_indexes]))) {
        stop("Singscore fixed background requires every non-member gene to be finite for every scored patient")
      }
      if (!all(is.finite(sample_values[selected_indexes]))) next
      sample_matrix <- matrix(
        sample_values, ncol = 1L,
        dimnames = list(rownames(expression), colnames(expression)[sample_index])
      )
      ranked <- singscore::rankGenes(sample_matrix, tiesMethod = "min")
      score <- singscore::simpleScore(
        ranked, upSet = selected, knownDirection = TRUE
      )
      if (!"TotalScore" %in% names(score) || nrow(score) != 1L) {
        stop("singscore returned an unexpected score table")
      }
      sample_scores[[sample_index]] <- as.numeric(score$TotalScore[[1L]])
    }
  }
  score_rows[[length(score_rows) + 1L]] <- data.frame(
    patient_row = colnames(expression), unit = unit, value = sample_scores,
    stringsAsFactors = FALSE
  )
  coverage_rows[[length(coverage_rows) + 1L]] <- data.frame(
    unit = unit,
    n_found = length(found),
    n_total = n_total,
    complete = complete,
    missing_genes = paste(missing, collapse = ";"),
    fixed_subset = paste(fixed_subset, collapse = ";"),
    scorable = scorable,
    reason = reason,
    stringsAsFactors = FALSE
  )
}

scores <- do.call(rbind, score_rows)
coverage <- do.call(rbind, coverage_rows)
utils::write.table(
  scores, file = file.path(out_dir, "scores.tsv"), sep = "\t", row.names = FALSE,
  col.names = TRUE, quote = FALSE, na = "NA"
)
utils::write.table(
  coverage, file = file.path(out_dir, "coverage.tsv"), sep = "\t", row.names = FALSE,
  col.names = TRUE, quote = FALSE, na = "NA"
)
bridge_write_session(out_dir)
