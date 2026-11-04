source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "singscore"))
config <- bridge_config()

expression_table <- read.delim(
  config$inputs$expression,
  check.names = FALSE,
  stringsAsFactors = FALSE,
  quote = ""
)
if (ncol(expression_table) < 2L || anyDuplicated(expression_table[[1L]])) {
  stop("Expression input must have unique genes and at least one patient row")
}
genes <- as.character(expression_table[[1L]])
expression <- as.matrix(expression_table[-1L])
rownames(expression) <- genes
storage.mode(expression) <- "double"
if (any(!is.finite(expression))) {
  stop("Expression input contains non-finite values")
}

gene_set_lines <- readLines(config$inputs$gene_sets, warn = FALSE)
if (!length(gene_set_lines)) {
  stop("Gene-set input is empty")
}
gene_sets <- lapply(gene_set_lines, function(line) {
  fields <- strsplit(line, "\t", fixed = TRUE)[[1L]]
  if (length(fields) < 3L || !nzchar(fields[[1L]])) {
    stop("Gene-set input must use GMT rows: name, description, genes")
  }
  unique(fields[-c(1L, 2L)])
})
names(gene_sets) <- vapply(gene_set_lines, function(line) {
  strsplit(line, "\t", fixed = TRUE)[[1L]][[1L]]
}, character(1L))
if (anyDuplicated(names(gene_sets))) {
  stop("Gene-set names must be unique")
}

sample_rows <- colnames(expression)
ranked <- singscore::rankGenes(expression, tiesMethod = "min")
score_rows <- list()
coverage_rows <- list()
for (unit in names(gene_sets)) {
  members <- gene_sets[[unit]]
  found <- intersect(members, rownames(expression))
  missing <- setdiff(members, rownames(expression))
  complete <- length(missing) == 0L
  coverage_rows[[length(coverage_rows) + 1L]] <- data.frame(
    unit = unit,
    n_found = length(found),
    n_total = length(members),
    complete = complete,
    missing_genes = paste(missing, collapse = ","),
    stringsAsFactors = FALSE
  )
  if (complete && length(found) > 0L) {
    scores <- singscore::simpleScore(ranked, upSet = members, knownDirection = TRUE)
    if (!"TotalScore" %in% names(scores) || nrow(scores) != length(sample_rows)) {
      stop("singscore returned an unexpected score table")
    }
    score_values <- as.numeric(scores$TotalScore)
  } else {
    score_values <- rep(NA_real_, length(sample_rows))
  }
  score_rows[[length(score_rows) + 1L]] <- data.frame(
    patient_row = sample_rows,
    unit = unit,
    value = score_values,
    stringsAsFactors = FALSE
  )
}

scores <- do.call(rbind, score_rows)
coverage <- do.call(rbind, coverage_rows)
write.table(
  scores,
  file = file.path(config$output_dir, "scores.tsv"),
  sep = "\t",
  row.names = FALSE,
  col.names = TRUE,
  quote = FALSE,
  na = "NA"
)
write.table(
  coverage,
  file = file.path(config$output_dir, "coverage.tsv"),
  sep = "\t",
  row.names = FALSE,
  col.names = TRUE,
  quote = FALSE,
  na = "NA"
)
bridge_write_session(config$output_dir)
