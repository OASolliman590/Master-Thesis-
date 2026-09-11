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

out_dir <- get_arg("--out-dir")
if (out_dir == "") {
  stop("Missing required argument: --out-dir")
}

rules_path <- get_arg("--rules", "configs/expanded_gene_set_atlas_rules.tsv")
base_registry <- get_arg("--base-registry", "configs/immune_gene_sets_registry.tsv")
registry_out <- get_arg("--registry-out", "configs/immune_gene_sets_registry_expanded.tsv")
species <- get_arg("--species", "Homo sapiens")
min_size <- as.integer(get_arg("--min-size", "5"))
max_size <- as.integer(get_arg("--max-size", "300"))

if (!requireNamespace("msigdbr", quietly = TRUE)) {
  stop("Required R package missing: msigdbr")
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_tsv <- function(path) {
  read.delim(path, sep = "\t", header = TRUE, stringsAsFactors = FALSE, check.names = FALSE, quote = "")
}

sanitize <- function(x) {
  x <- as.character(x)
  x <- gsub("[\t\r\n]+", " ", x)
  x <- gsub(" +", " ", x)
  trimws(x)
}

write_tsv <- function(df, path) {
  write.table(df, file = path, sep = "\t", row.names = FALSE, quote = FALSE, na = "")
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
  df
}

write_gmt <- function(df, path) {
  con <- file(path, open = "wt", encoding = "UTF-8")
  on.exit(close(con), add = TRUE)
  if (nrow(df) == 0) {
    return(invisible(NULL))
  }
  set_names <- sort(unique(df$gs_name))
  for (nm in set_names) {
    rows <- df[df$gs_name == nm, , drop = FALSE]
    genes <- sort(unique(sanitize(rows$gene_symbol)))
    genes <- genes[genes != ""]
    desc <- paste(
      "source_key=", sanitize(rows$source_key[[1]]),
      "; collection=", sanitize(rows$gs_collection[[1]]),
      "; subcollection=", sanitize(rows$gs_subcollection[[1]]),
      "; description=", sanitize(rows$gs_description[[1]]),
      "; pmid=", sanitize(rows$gs_pmid[[1]]),
      "; url=", sanitize(rows$gs_url[[1]]),
      sep = ""
    )
    writeLines(paste(c(nm, desc, genes), collapse = "\t"), con = con)
  }
}

rules <- read_tsv(rules_path)
required <- c("rule_id", "atlas_layer", "layer_name", "source_keys", "include_regex", "exclude_regex", "enabled")
missing <- setdiff(required, colnames(rules))
if (length(missing) > 0) {
  stop(sprintf("Rules file missing required columns: %s", paste(missing, collapse = ", ")))
}
rules <- rules[tolower(rules$enabled) %in% c("true", "1", "yes"), , drop = FALSE]
if (nrow(rules) == 0) {
  stop("No enabled atlas rules.")
}

source_keys <- sort(unique(unlist(strsplit(paste(rules$source_keys, collapse = "|"), "\\|"))))
source_keys <- source_keys[source_keys != ""]
source_tables <- lapply(source_keys, pull_source)
all_sets <- do.call(rbind, source_tables)
if (is.null(all_sets) || nrow(all_sets) == 0) {
  stop("No MSigDB rows were pulled from requested sources.")
}

all_sets$search_text <- toupper(paste(
  all_sets$gs_name,
  all_sets$gs_description,
  all_sets$gs_exact_source,
  sep = " "
))
set_sizes <- aggregate(gene_symbol ~ source_key + gs_name, data = all_sets, FUN = function(x) length(unique(x)))
colnames(set_sizes)[colnames(set_sizes) == "gene_symbol"] <- "n_genes"
all_sets <- merge(all_sets, set_sizes, by = c("source_key", "gs_name"), all.x = TRUE)

atlas_rows <- list()
provenance_rows <- list()
summary_rows <- list()
registry_rows <- list()

for (idx in seq_len(nrow(rules))) {
  rule <- rules[idx, , drop = FALSE]
  rule_sources <- strsplit(rule$source_keys[[1]], "\\|")[[1]]
  include_regex <- toupper(rule$include_regex[[1]])
  exclude_regex <- toupper(rule$exclude_regex[[1]])

  selected <- all_sets[all_sets$source_key %in% rule_sources, , drop = FALSE]
  selected <- selected[grepl(include_regex, selected$search_text, perl = TRUE), , drop = FALSE]
  if (!is.na(exclude_regex) && exclude_regex != "") {
    selected <- selected[!grepl(exclude_regex, selected$search_text, perl = TRUE), , drop = FALSE]
  }
  selected <- selected[selected$n_genes >= min_size & selected$n_genes <= max_size, , drop = FALSE]
  selected$atlas_layer <- rule$atlas_layer[[1]]
  selected$rule_id <- rule$rule_id[[1]]

  layer_file <- file.path(out_dir, paste0(rule$atlas_layer[[1]], ".gmt"))
  write_gmt(selected, layer_file)

  if (nrow(selected) > 0) {
    unique_sets <- selected[!duplicated(paste(selected$source_key, selected$gs_name)), , drop = FALSE]
    provenance_rows[[length(provenance_rows) + 1]] <- data.frame(
      rule_id = unique_sets$rule_id,
      atlas_layer = unique_sets$atlas_layer,
      gene_set_id = unique_sets$gs_name,
      source_key = unique_sets$source_key,
      gs_collection = unique_sets$gs_collection,
      gs_subcollection = unique_sets$gs_subcollection,
      gs_description = sanitize(unique_sets$gs_description),
      gs_pmid = sanitize(unique_sets$gs_pmid),
      gs_url = sanitize(unique_sets$gs_url),
      gs_exact_source = sanitize(unique_sets$gs_exact_source),
      n_genes = unique_sets$n_genes,
      db_version = sanitize(unique_sets$db_version),
      include_regex = rule$include_regex[[1]],
      exclude_regex = rule$exclude_regex[[1]],
      stringsAsFactors = FALSE
    )
    atlas_rows[[length(atlas_rows) + 1]] <- selected
  }

  summary_rows[[length(summary_rows) + 1]] <- data.frame(
    rule_id = rule$rule_id[[1]],
    atlas_layer = rule$atlas_layer[[1]],
    layer_name = rule$layer_name[[1]],
    source_keys = rule$source_keys[[1]],
    n_gene_sets = length(unique(selected$gs_name)),
    n_gene_rows = nrow(selected),
    min_size = min_size,
    max_size = max_size,
    gmt_path = layer_file,
    stringsAsFactors = FALSE
  )

  rel_path <- layer_file
  if (!grepl("^/", rel_path)) {
    rel_path <- layer_file
  }
  registry_rows[[length(registry_rows) + 1]] <- data.frame(
    gene_set_id = paste0("EXPANDED_", rule$rule_id[[1]]),
    gene_set_layer = rule$atlas_layer[[1]],
    gene_set_name = rule$layer_name[[1]],
    gmt_path = rel_path,
    source = "MSigDB/msigdbr programmatic subset",
    enabled = "true",
    notes = paste0("Rule ", rule$rule_id[[1]], "; no manual gene membership."),
    stringsAsFactors = FALSE
  )
}

combined <- if (length(atlas_rows) > 0) do.call(rbind, atlas_rows) else all_sets[0, , drop = FALSE]
combined_gmt <- file.path(out_dir, "MSIGDB_GO_REACTOME_EXPANDED_IMMUNE_ATLAS.gmt")
write_gmt(combined, combined_gmt)

summary_df <- do.call(rbind, summary_rows)
provenance_df <- if (length(provenance_rows) > 0) do.call(rbind, provenance_rows) else data.frame()
registry_df <- do.call(rbind, registry_rows)

write_tsv(summary_df, file.path(out_dir, "expanded_atlas_summary.tsv"))
write_tsv(provenance_df, file.path(out_dir, "gene_set_provenance.tsv"))
write_tsv(registry_df, file.path(out_dir, "expanded_registry_rows.tsv"))

if (base_registry != "" && file.exists(base_registry) && registry_out != "") {
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

cat("Wrote expanded atlas to:", out_dir, "\n")
cat("Wrote combined GMT:", combined_gmt, "\n")
cat("Wrote provenance:", file.path(out_dir, "gene_set_provenance.tsv"), "\n")
if (registry_out != "") {
  cat("Wrote expanded registry:", registry_out, "\n")
}
