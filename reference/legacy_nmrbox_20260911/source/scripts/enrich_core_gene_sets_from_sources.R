#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) {
    val <- ""
  }
  arg_map[[key]] <- val
}

get_arg <- function(name, default = "") {
  val <- arg_map[[name]]
  if (is.null(val) || val == "") {
    return(default)
  }
  val
}

base_registry <- get_arg("--base-registry", "configs/immune_gene_sets_registry.tsv")
out_dir <- get_arg("--out-dir")
registry_out <- get_arg("--registry-out", "configs/immune_gene_sets_registry_core_enriched.tsv")
species <- get_arg("--species", "Homo sapiens")
source_keys_raw <- get_arg("--source-keys", "H|C2:CP:REACTOME|C5:GO:BP|C7")
min_size <- as.integer(get_arg("--min-size", "5"))
max_size <- as.integer(get_arg("--max-size", "300"))
min_overlap <- as.integer(get_arg("--min-overlap", "3"))
max_q <- as.numeric(get_arg("--max-q", "0.10"))
max_sets_per_seed <- as.integer(get_arg("--max-sets-per-seed", "40"))

if (out_dir == "") {
  stop("Missing required argument: --out-dir")
}
if (!requireNamespace("msigdbr", quietly = TRUE)) {
  stop("Required R package missing: msigdbr")
}
if (!file.exists(base_registry)) {
  stop(sprintf("Base registry not found: %s", base_registry))
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_tsv <- function(path) {
  read.delim(path, sep = "\t", header = TRUE, stringsAsFactors = FALSE, check.names = FALSE, quote = "")
}

write_tsv <- function(df, path) {
  write.table(df, file = path, sep = "\t", row.names = FALSE, quote = FALSE, na = "")
}

sanitize <- function(x) {
  x <- as.character(x)
  x <- gsub("[\t\r\n]+", " ", x)
  x <- gsub(" +", " ", x)
  trimws(x)
}

slug <- function(x) {
  x <- toupper(gsub("[^A-Za-z0-9]+", "_", x))
  x <- gsub("^_+|_+$", "", x)
  x
}

read_gmt <- function(path) {
  rows <- list()
  lines <- readLines(path, warn = FALSE)
  for (ln in lines) {
    parts <- strsplit(ln, "\t", fixed = TRUE)[[1]]
    if (length(parts) < 3) {
      next
    }
    rows[[length(rows) + 1]] <- list(
      term = parts[[1]],
      description = parts[[2]],
      genes = sort(unique(toupper(parts[3:length(parts)])))
    )
  }
  rows
}

split_source_key <- function(source_key) {
  parts <- strsplit(source_key, ":", fixed = TRUE)[[1]]
  if (length(parts) == 1) {
    return(list(collection = parts[[1]], subcollection = ""))
  }
  list(collection = parts[[1]], subcollection = paste(parts[-1], collapse = ":"))
}

pull_source <- function(source_key) {
  spec <- split_source_key(source_key)
  if (spec$subcollection == "") {
    df <- msigdbr::msigdbr(species = species, collection = spec$collection)
  } else {
    df <- msigdbr::msigdbr(
      species = species,
      collection = spec$collection,
      subcollection = spec$subcollection
    )
  }
  if (nrow(df) == 0) {
    warning(sprintf("No rows pulled for source key: %s", source_key))
    return(df)
  }
  df$source_key <- source_key
  df$gene_symbol <- toupper(df$gene_symbol)
  df
}

write_gmt <- function(df, path) {
  con <- file(path, open = "wt", encoding = "UTF-8")
  on.exit(close(con), add = TRUE)
  if (nrow(df) == 0) {
    return(invisible(NULL))
  }
  name_col <- if ("output_gene_set_id" %in% colnames(df)) "output_gene_set_id" else "gs_name"
  set_names <- sort(unique(df[[name_col]]))
  for (nm in set_names) {
    rows <- df[df[[name_col]] == nm, , drop = FALSE]
    genes <- sort(unique(sanitize(rows$gene_symbol)))
    genes <- genes[genes != ""]
    meta <- rows[1, , drop = FALSE]
    desc <- paste(
      "core_seed=", sanitize(meta$core_seed_id),
      "; source_key=", sanitize(meta$source_key),
      "; collection=", sanitize(meta$gs_collection),
      "; subcollection=", sanitize(meta$gs_subcollection),
      "; overlap=", sanitize(meta$n_overlap),
      "; q_value=", sanitize(signif(meta$q_value, 4)),
      "; description=", sanitize(meta$gs_description),
      "; pmid=", sanitize(meta$gs_pmid),
      "; url=", sanitize(meta$gs_url),
      sep = ""
    )
    writeLines(paste(c(nm, desc, genes), collapse = "\t"), con = con)
  }
}

registry <- read_tsv(base_registry)
required <- c("gene_set_id", "gene_set_layer", "gmt_path", "enabled")
missing <- setdiff(required, colnames(registry))
if (length(missing) > 0) {
  stop(sprintf("Registry missing required columns: %s", paste(missing, collapse = ", ")))
}
registry <- registry[tolower(registry$enabled) %in% c("true", "1", "yes"), , drop = FALSE]

seed_rows <- list()
for (i in seq_len(nrow(registry))) {
  gmt_path <- registry$gmt_path[[i]]
  if (!file.exists(gmt_path)) {
    stop(sprintf("GMT path from registry does not exist: %s", gmt_path))
  }
  for (gmt in read_gmt(gmt_path)) {
    seed_rows[[length(seed_rows) + 1]] <- data.frame(
      core_registry_id = registry$gene_set_id[[i]],
      core_layer = registry$gene_set_layer[[i]],
      core_seed_id = gmt$term,
      core_seed_description = gmt$description,
      core_seed_size = length(gmt$genes),
      seed_genes = paste(gmt$genes, collapse = "|"),
      stringsAsFactors = FALSE
    )
  }
}
seeds <- do.call(rbind, seed_rows)

source_keys <- strsplit(source_keys_raw, "\\|")[[1]]
source_keys <- source_keys[source_keys != ""]
source_tables <- lapply(source_keys, pull_source)
all_sources <- do.call(rbind, source_tables)
if (is.null(all_sources) || nrow(all_sources) == 0) {
  stop("No source rows available.")
}

set_sizes <- aggregate(gene_symbol ~ source_key + gs_name, data = all_sources, FUN = function(x) length(unique(x)))
colnames(set_sizes)[colnames(set_sizes) == "gene_symbol"] <- "source_set_size"
all_sources <- merge(all_sources, set_sizes, by = c("source_key", "gs_name"), all.x = TRUE)
all_sources <- all_sources[all_sources$source_set_size >= min_size & all_sources$source_set_size <= max_size, , drop = FALSE]

source_keys_by_set <- unique(all_sources[, c(
  "source_key",
  "gs_name",
  "gs_collection",
  "gs_subcollection",
  "gs_description",
  "gs_pmid",
  "gs_url",
  "gs_exact_source",
  "db_version",
  "source_set_size"
), drop = FALSE])

source_genes <- split(all_sources$gene_symbol, paste(all_sources$source_key, all_sources$gs_name, sep = "\t"))
source_genes <- lapply(source_genes, function(x) sort(unique(x)))
universe <- sort(unique(all_sources$gene_symbol))
universe_n <- length(universe)

selection_rows <- list()
selected_source_keys <- list()

for (seed_idx in seq_len(nrow(seeds))) {
  seed <- seeds[seed_idx, , drop = FALSE]
  seed_genes <- strsplit(seed$seed_genes[[1]], "\\|")[[1]]
  seed_genes <- unique(seed_genes[seed_genes %in% universe])
  if (length(seed_genes) == 0) {
    next
  }

  candidate_rows <- list()
  for (key in names(source_genes)) {
    genes <- source_genes[[key]]
    n_overlap <- length(intersect(seed_genes, genes))
    if (n_overlap < min_overlap) {
      next
    }
    source_size <- length(genes)
    p_value <- phyper(
      q = n_overlap - 1,
      m = source_size,
      n = universe_n - source_size,
      k = length(seed_genes),
      lower.tail = FALSE
    )
    parts <- strsplit(key, "\t", fixed = TRUE)[[1]]
    candidate_rows[[length(candidate_rows) + 1]] <- data.frame(
      source_key = parts[[1]],
      gs_name = parts[[2]],
      n_overlap = n_overlap,
      seed_size_in_universe = length(seed_genes),
      source_set_size = source_size,
      overlap_fraction_seed = n_overlap / length(seed_genes),
      overlap_fraction_source = n_overlap / source_size,
      p_value = p_value,
      stringsAsFactors = FALSE
    )
  }
  if (length(candidate_rows) == 0) {
    next
  }
  candidates <- do.call(rbind, candidate_rows)
  candidates$q_value <- p.adjust(candidates$p_value, method = "BH")
  candidates <- candidates[candidates$q_value <= max_q, , drop = FALSE]
  if (nrow(candidates) == 0) {
    next
  }
  candidates <- candidates[order(
    candidates$q_value,
    -candidates$n_overlap,
    -candidates$overlap_fraction_seed,
    candidates$source_set_size
  ), , drop = FALSE]
  if (nrow(candidates) > max_sets_per_seed) {
    candidates <- candidates[seq_len(max_sets_per_seed), , drop = FALSE]
  }
  candidates$core_registry_id <- seed$core_registry_id[[1]]
  candidates$core_layer <- seed$core_layer[[1]]
  candidates$core_seed_id <- seed$core_seed_id[[1]]
  candidates$core_seed_description <- seed$core_seed_description[[1]]
  candidates$core_seed_size <- seed$core_seed_size[[1]]
  candidates$selection_method <- "hypergeometric_seed_overlap"
  selection_rows[[length(selection_rows) + 1]] <- candidates
}

selection <- if (length(selection_rows) > 0) do.call(rbind, selection_rows) else data.frame()
if (nrow(selection) == 0) {
  stop("No enriched source gene sets selected. Relax thresholds or inspect seed overlap.")
}

selection <- merge(selection, source_keys_by_set, by = c("source_key", "gs_name", "source_set_size"), all.x = TRUE)
selection$enriched_layer <- paste0(selection$core_layer, "_SOURCE_ENRICHED")

registry_rows <- list()
summary_rows <- list()
combined_selected <- list()

for (seed_id in sort(unique(selection$core_seed_id))) {
  seed_sel <- selection[selection$core_seed_id == seed_id, , drop = FALSE]
  keys <- paste(seed_sel$source_key, seed_sel$gs_name, sep = "\t")
  source_subset <- all_sources[paste(all_sources$source_key, all_sources$gs_name, sep = "\t") %in% keys, , drop = FALSE]
  source_subset <- merge(
    source_subset,
    seed_sel[, c("source_key", "gs_name", "core_seed_id", "n_overlap", "q_value"), drop = FALSE],
    by = c("source_key", "gs_name"),
    all.x = TRUE
  )
  seed_layer <- seed_sel$enriched_layer[[1]]
  seed_slug <- slug(seed_id)
  source_subset$output_gene_set_id <- paste0("CORE_ENRICHED_", seed_slug, "__", slug(source_subset$gs_name))
  combined_selected[[length(combined_selected) + 1]] <- source_subset

  out_file <- file.path(out_dir, paste0("CORE_ENRICHED_", seed_slug, ".gmt"))
  write_gmt(source_subset, out_file)

  registry_rows[[length(registry_rows) + 1]] <- data.frame(
    gene_set_id = paste0("CORE_ENRICHED_", seed_slug),
    gene_set_layer = seed_layer,
    gene_set_name = paste0("Source-enriched ", seed_id),
    gmt_path = out_file,
    source = "MSigDB/msigdbr hypergeometric overlap to original core seed",
    enabled = "true",
    notes = paste0(
      "Seed=", seed_id,
      "; selected_sets=", length(unique(source_subset$gs_name)),
      "; min_overlap=", min_overlap,
      "; max_q=", max_q,
      "; no manual source genes."
    ),
    stringsAsFactors = FALSE
  )

  summary_rows[[length(summary_rows) + 1]] <- data.frame(
    core_seed_id = seed_id,
    core_layer = seed_sel$core_layer[[1]],
    enriched_layer = seed_layer,
    core_seed_size = seed_sel$core_seed_size[[1]],
    n_selected_source_sets = length(unique(seed_sel$gs_name)),
    min_overlap = min(seed_sel$n_overlap),
    max_overlap = max(seed_sel$n_overlap),
    min_q_value = min(seed_sel$q_value),
    max_q_value = max(seed_sel$q_value),
    gmt_path = out_file,
    stringsAsFactors = FALSE
  )
}

combined_source <- do.call(rbind, combined_selected)
combined_file <- file.path(out_dir, "CORE_SOURCE_ENRICHED_ATLAS.gmt")
write_gmt(combined_source, combined_file)

summary_df <- do.call(rbind, summary_rows)
registry_df <- do.call(rbind, registry_rows)

write_tsv(seeds, file.path(out_dir, "core_seed_sets.tsv"))
write_tsv(selection[order(selection$core_seed_id, selection$q_value), ], file.path(out_dir, "core_enrichment_provenance.tsv"))
write_tsv(summary_df, file.path(out_dir, "core_enrichment_summary.tsv"))
write_tsv(registry_df, file.path(out_dir, "core_enriched_registry_rows.tsv"))

if (registry_out != "") {
  base_df <- read_tsv(base_registry)
  missing_cols <- setdiff(colnames(base_df), colnames(registry_df))
  for (col in missing_cols) {
    registry_df[[col]] <- ""
  }
  missing_cols2 <- setdiff(colnames(registry_df), colnames(base_df))
  for (col in missing_cols2) {
    base_df[[col]] <- ""
  }
  combined_registry <- rbind(base_df[, colnames(registry_df), drop = FALSE], registry_df)
  write_tsv(combined_registry, registry_out)
}

cat("Wrote core source-enriched atlas to:", out_dir, "\n")
cat("Wrote combined GMT:", combined_file, "\n")
cat("Wrote provenance:", file.path(out_dir, "core_enrichment_provenance.tsv"), "\n")
cat("Wrote registry:", registry_out, "\n")
