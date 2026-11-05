source("R/bridge.R")
bridge_require(c("jsonlite", "digest", "BiocManager", "fgsea"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir
source("R/random_streams.R")
ranking_id_type <- as.character(cfg$ranking_id_type)
gene_set_id_type <- as.character(cfg$gene_set_id_type)
if (length(ranking_id_type) != 1L || is.na(ranking_id_type) ||
    !nzchar(ranking_id_type) || length(gene_set_id_type) != 1L ||
    is.na(gene_set_id_type) || !nzchar(gene_set_id_type)) {
  stop("Ranking and GMT identifier types must be declared")
}
if (!identical(ranking_id_type, gene_set_id_type)) {
  stop("Ranking and GMT identifier types must match; no mapping is configured")
}
gene_set_sha256 <- digest::digest(file = bridge$inputs$gene_sets, algo = "sha256", serialize = FALSE)
if (!identical(gene_set_sha256, as.character(cfg$gene_set_sha256))) {
  stop("Gene-set input hash differs from the GSEA contract")
}
test_only_gene_sets <- isTRUE(cfg$test_only_gene_sets)
gene_set_collection <- as.character(cfg$gene_set_collection)
if (!test_only_gene_sets) {
  frozen_hash <- switch(
    gene_set_collection,
    hallmark = "01f390fb123ac08c75874030233a4252122c9d7f97c1e173366b587438f57ad5",
    reactome = "4e1b4a6231ccb812985bffef6b9991bc54745c1b72bbcbcd2d132d5188b006bb",
    stop("Gene-set collection is not in the signed numerical freeze")
  )
  if (!identical(gene_set_sha256, frozen_hash)) stop("Gene-set input does not match its frozen hash")
  if (!identical(as.integer(cfg$min_size), 15L) || !identical(as.integer(cfg$max_size), 500L)) {
    stop("Frozen fgsea requires minSize 15 and maxSize 500")
  }
} else if (as.integer(cfg$min_size) < 1L || as.integer(cfg$max_size) > 500L) {
  stop("Test-only fgsea settings are outside the allowed bounds")
}
overlap_floor <- suppressWarnings(as.integer(cfg$min_gene_set_overlap))
if (length(overlap_floor) != 1L || is.na(overlap_floor) || overlap_floor < 1L) {
  stop("Minimum GMT/ranking membership overlap must be a positive integer")
}

ranking <- read.delim(bridge$inputs$ranking, check.names = FALSE,
                      stringsAsFactors = FALSE, na.strings = c("", "NA"),
                      quote = "\"", comment.char = "")
if (!all(c("gene", "statistic") %in% names(ranking))) {
  stop("DE ranking needs gene and statistic columns")
}
ranking$gene <- as.character(ranking$gene)
ranking$statistic <- suppressWarnings(as.numeric(ranking$statistic))
if (anyNA(ranking$gene) || any(!nzchar(ranking$gene)) || anyDuplicated(ranking$gene)) {
  stop("DE ranking gene identifiers must be unique and non-empty")
}
ranking <- ranking[is.finite(ranking$statistic), , drop = FALSE]
if (nrow(ranking) < 2L) stop("At least two finite ranked genes are required")
ordering <- order(-ranking$statistic, ranking$gene, method = "radix")
statistics <- ranking$statistic[ordering]
names(statistics) <- ranking$gene[ordering]
pathways <- fgsea::gmtPathways(bridge$inputs$gene_sets)
if (!length(pathways)) stop("The local GMT file contains no gene sets")
if (identical(ranking_id_type, "symbol")) {
  if (is.null(bridge$inputs$gene_aliases) || is.null(cfg$gene_set_aliases) ||
      is.null(cfg$gene_alias_table_sha256)) {
    stop("Symbol rankings require the frozen gene-alias table and mapping")
  }
  alias_sha256 <- digest::digest(file = bridge$inputs$gene_aliases, algo = "sha256", serialize = FALSE)
  if (!identical(alias_sha256, as.character(cfg$gene_alias_table_sha256))) {
    stop("Frozen gene-alias table hash mismatch")
  }
  alias_table <- read.delim(
    bridge$inputs$gene_aliases,
    check.names = FALSE,
    stringsAsFactors = FALSE,
    quote = ""
  )
  if (!all(c("source_symbol", "registry_symbol") %in% names(alias_table)) ||
      anyDuplicated(alias_table$source_symbol)) {
    stop("Frozen gene-alias table has an unexpected schema")
  }
  frozen_aliases <- stats::setNames(
    as.character(alias_table$registry_symbol), as.character(alias_table$source_symbol)
  )
  configured_aliases <- unlist(cfg$gene_set_aliases, use.names = TRUE)
  if (is.null(names(configured_aliases)) ||
      !setequal(names(configured_aliases), names(frozen_aliases)) ||
      any(configured_aliases[names(frozen_aliases)] != frozen_aliases)) {
    stop("Configured gene-set aliases differ from the frozen alias table")
  }
  pathway_names <- names(pathways)
  pathways <- lapply(pathway_names, function(pathway_name) {
    members <- as.character(pathways[[pathway_name]])
    mapped <- unname(configured_aliases[members])
    missing <- is.na(mapped)
    mapped[missing] <- members[missing]
    if (anyDuplicated(mapped)) {
      stop(sprintf("Frozen aliases collapse duplicate members in gene set '%s'", pathway_name))
    }
    mapped
  })
  names(pathways) <- pathway_names
}
gmt_members <- unique(unlist(pathways, use.names = FALSE))
ranking_members <- names(statistics)
overlap_members <- intersect(gmt_members, ranking_members)
overlap_count <- length(overlap_members)
if (overlap_count < overlap_floor) {
  stop(sprintf(
    "GMT/ranking membership overlap is below configured floor: %d < %d",
    overlap_count, overlap_floor
  ))
}
membership <- do.call(rbind, lapply(names(pathways), function(pathway) {
  members <- unique(pathways[[pathway]])
  overlap <- intersect(members, ranking_members)
  data.frame(
    pathway = pathway,
    gmt_gene_count = length(members),
    ranking_overlap_count = length(overlap),
    overlap_fraction = if (length(members)) length(overlap) / length(members) else 0,
    check.names = FALSE
  )
}))
utils::write.table(membership, file.path(out_dir, "membership_overlap.tsv"),
                   sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")

seed <- suppressWarnings(as.integer(cfg$seed))
task_id <- as.character(cfg$random_task_id)
if (length(seed) != 1L || is.na(seed) || !identical(as.character(cfg$random_stream), "fgsea") ||
    length(task_id) != 1L || is.na(task_id) || !nzchar(task_id) ||
    seed != random_task_seed("fgsea", task_id)) {
  stop("A task seed from the signed fgsea stream is required")
}
second_check_seed <- suppressWarnings(as.integer(cfg$second_check_seed))
if (length(second_check_seed) != 1L || is.na(second_check_seed) ||
    !identical(as.character(cfg$second_check_random_stream), "second_check") ||
    !identical(as.character(cfg$second_check_random_task_id), "fgsea") ||
    second_check_seed != random_task_seed("second_check", "fgsea")) {
  stop("A reported-only second_check task seed for fgsea is required")
}
run_second_check <- if (is.null(cfg$run_second_check)) TRUE else isTRUE(cfg$run_second_check)
if (!run_second_check && !test_only_gene_sets) {
  stop("The signed real-data fgsea second check cannot be skipped")
}
options(ports = 32567L)
run_fgsea <- function(call_seed) {
  set.seed(
    call_seed, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection"
  )
  fgsea::fgseaMultilevel(
    pathways = pathways,
    stats = statistics,
    minSize = as.integer(cfg$min_size),
    maxSize = as.integer(cfg$max_size),
    eps = 0,
    nproc = 1L
  )
}
result <- run_fgsea(seed)
if (nrow(result)) {
  result <- as.data.frame(result, stringsAsFactors = FALSE)
  result$leadingEdge <- vapply(result$leadingEdge, paste, collapse = ";", FUN.VALUE = character(1))
  names(result)[names(result) == "pathway"] <- "pathway"
  names(result)[names(result) == "pval"] <- "p"
  names(result)[names(result) == "padj"] <- "q"
  names(result)[names(result) == "ES"] <- "ES"
  names(result)[names(result) == "NES"] <- "NES"
  names(result)[names(result) == "size"] <- "size"
  if (!"log2err" %in% names(result)) stop("fgsea did not return the frozen log2err diagnostic")
  result <- result[, c("pathway", "p", "q", "ES", "NES", "size", "log2err", "leadingEdge"), drop = FALSE]
} else {
  result <- data.frame(pathway = character(), p = numeric(), q = numeric(),
                       ES = numeric(), NES = numeric(), size = integer(), log2err = numeric(),
                       leadingEdge = character())
}
utils::write.table(result, file.path(out_dir, "fgsea.tsv"), sep = "\t",
                    row.names = FALSE, quote = FALSE, na = "NA")
if (run_second_check) {
  second_result <- as.data.frame(run_fgsea(second_check_seed), stringsAsFactors = FALSE)
  if (!setequal(as.character(result$pathway), as.character(second_result$pathway))) {
    stop("Main and second-check fgsea pathway rows do not match")
  }
  second_q <- second_result$padj[match(result$pathway, second_result$pathway)]
  main_decision <- !is.na(result$q) & result$q <= 0.10
  second_decision <- !is.na(second_q) & second_q <= 0.10
  flipped <- main_decision != second_decision
  second_check <- data.frame(
    pathway = result$pathway,
    main_q = result$q,
    second_q = second_q,
    bh_decision_flip_10pct = flipped,
    stringsAsFactors = FALSE
  )
  second_check_flip_count <- sum(flipped)
  second_check_status <- "reported_only"
} else {
  second_check <- data.frame(
    pathway = character(), main_q = numeric(), second_q = numeric(),
    bh_decision_flip_10pct = logical(), stringsAsFactors = FALSE
  )
  second_check_flip_count <- NA_integer_
  second_check_status <- "skipped_test_only"
}
utils::write.table(second_check, file.path(out_dir, "fgsea_second_check.tsv"), sep = "\t",
                    row.names = FALSE, quote = FALSE, na = "NA")
summary <- list(
  pathway_count = nrow(result),
  ranked_gene_count = length(statistics),
  gene_set_count = length(pathways),
  ranking_id_type = ranking_id_type,
  gene_set_id_type = gene_set_id_type,
  membership_overlap_count = overlap_count,
  membership_overlap_fraction = overlap_count / length(gmt_members),
  minimum_membership_overlap = overlap_floor,
  method = "fgseaMultilevel",
  endpoint = cfg$endpoint,
  gene_sets_input = "local_GMT",
  gene_set_collection = gene_set_collection,
  gene_set_sha256 = gene_set_sha256,
  min_size = as.integer(cfg$min_size),
  max_size = as.integer(cfg$max_size),
  random_stream = cfg$random_stream,
  random_task_id = cfg$random_task_id,
  seed = seed,
  nproc = 1L,
  second_check_random_stream = cfg$second_check_random_stream,
  second_check_random_task_id = cfg$second_check_random_task_id,
  second_check_seed = second_check_seed,
  second_check_status = second_check_status,
  second_check_reported_only = TRUE,
  second_check_flip_count = second_check_flip_count
)
jsonlite::write_json(summary, file.path(out_dir, "gsea_summary.json"),
                     auto_unbox = TRUE, pretty = TRUE, na = "null")
bridge_write_session(out_dir)
