#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
for (i in seq(1, length(args), by = 2)) {
  key <- args[[i]]
  val <- args[[i + 1]]
  if (is.null(val)) { val <- "" }
  arg_map[[key]] <- val
}

out_dir <- arg_map[["--out-dir"]]
if (is.null(out_dir) || out_dir == "") {
  stop("Missing required argument: --out-dir")
}

species <- arg_map[["--species"]]
if (is.null(species) || species == "") {
  species <- "Homo sapiens"
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

suppressMessages(library(msigdbr))

write_gmt <- function(df, out_path) {
  con <- file(out_path, open = "wt", encoding = "UTF-8")
  on.exit(close(con), add = TRUE)
  split_sets <- split(df$gene_symbol, df$gs_name)
  for (nm in names(split_sets)) {
    genes <- unique(split_sets[[nm]])
    line <- paste(c(nm, "na", genes), collapse = "\t")
    writeLines(line, con = con)
  }
}

safe_pull <- function(collection, subcollection = NULL) {
  if (is.null(subcollection)) {
    return(msigdbr(species = species, collection = collection))
  }
  return(msigdbr(species = species, collection = collection, subcollection = subcollection))
}

hallmark <- safe_pull("H")
kegg <- safe_pull("C2", "CP:KEGG_MEDICUS")
if (nrow(kegg) == 0) {
  kegg <- safe_pull("C2", "CP:KEGG_LEGACY")
}
c7 <- safe_pull("C7")
reactome <- safe_pull("C2", "CP:REACTOME")

write_gmt(hallmark, file.path(out_dir, "MSIGDB_HALLMARK_Hs.gmt"))
write_gmt(kegg, file.path(out_dir, "MSIGDB_KEGG_Hs.gmt"))
write_gmt(c7, file.path(out_dir, "MSIGDB_C7_IMMUNESIGDB_Hs.gmt"))
write_gmt(reactome, file.path(out_dir, "MSIGDB_REACTOME_Hs.gmt"))

summary_df <- data.frame(
  layer = c("HALLMARK", "KEGG", "C7_IMMUNESIGDB", "REACTOME"),
  n_rows = c(nrow(hallmark), nrow(kegg), nrow(c7), nrow(reactome)),
  n_gene_sets = c(length(unique(hallmark$gs_name)),
                  length(unique(kegg$gs_name)),
                  length(unique(c7$gs_name)),
                  length(unique(reactome$gs_name))),
  stringsAsFactors = FALSE
)

write.table(
  summary_df,
  file = file.path(out_dir, "msigdb_layers_summary.tsv"),
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)

cat("Wrote MSigDB layered GMT exports to:", out_dir, "\n")
