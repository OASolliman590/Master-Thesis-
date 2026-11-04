source("R/bridge.R")
bridge_require(c(Seurat = "5.6.0", SeuratObject = "5.4.0", qs2 = "0.4.0", muscat = "1.26.0"))
bridge_require(c(digest = "0.6.39"))
bridge_require(c("ggplot2", "jsonlite", "BiocManager"))
source("R/sc_lin.R")
config <- bridge_config()
options(future.globals.maxSize = 2 * 1024^3)
cohort_map <- read.delim(config$inputs$cohort_map, check.names = FALSE, stringsAsFactors = FALSE)
compartment_map <- read.delim(config$inputs$compartment_map, check.names = FALSE, stringsAsFactors = FALSE)
panel_genes <- read.delim(config$inputs$panels, check.names = FALSE, stringsAsFactors = FALSE)
mode <- config$config$mode
minimum_cells <- as.integer(config$config$minimum_cells)
minimum_umis <- as.integer(config$config$minimum_umis)
minimum_donors <- as.integer(config$config$minimum_donors_to_show)

if (mode == "labels") {
  object <- qs2::qs_read(config$inputs$seurat)
  if (!inherits(object, "Seurat")) stop("The qs2 source is not a Seurat object")
  message("Lin Seurat object loaded for label check")
  metadata <- readRDS(config$inputs$metadata)
  marker_data <- sc_lin_marker_summary(object, panel_genes, metadata[, "celltype_main", drop = FALSE])
  write.table(marker_data, file.path(config$output_dir, "labels_markers.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
  sc_lin_write_dotplot(marker_data, file.path(config$output_dir, "labels_dotplot.png"), "author_label", "Lin author cell labels and canonical markers")
} else {
  metadata <- readRDS(config$inputs$metadata)
  if (!is.data.frame(metadata)) stop("The Lin metadata RDS is not a data frame")
  message("Lin process started")
  processed <- sc_lin_process(config$inputs$seurat, metadata, cohort_map, compartment_map,
    panel_genes, minimum_cells, minimum_umis, config$inputs$metadata,
    config$config$source_sha256, config$config$metadata_sha256)
  message("Lin process complete")
  for (index in seq_along(sc_lin_compartments)) {
    compartment <- sc_lin_compartments[[index]]
    slug <- sc_lin_slugs[[index]]
    counts <- sc_lin_layer_matrix_by_compartment(processed$layers, "counts", compartment)
    clinical <- processed$clinical[processed$clinical$compartment == compartment, , drop = FALSE]
    if (mode == "pseudobulk") {
      ineligible <- clinical$profile_id[!clinical$eligible]
      if (length(ineligible)) counts[, ineligible] <- NA_real_
      expression_output <- data.frame(gene = rownames(counts), counts, check.names = FALSE)
      write.table(expression_output, file.path(config$output_dir, paste0("expression__", slug, ".tsv")),
        sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
      write.table(clinical, file.path(config$output_dir, paste0("clinical__", slug, ".tsv")),
        sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    }
  }
  if (mode == "pseudobulk") {
    write.table(processed$compartment_qc, file.path(config$output_dir, "compartment_qc.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    write.table(processed$gene_coverage, file.path(config$output_dir, "gene_coverage.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    write.table(processed$data_quality, file.path(config$output_dir, "data_quality.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
  }
  if (mode %in% c("pseudobulk", "compartments")) {
    write.table(processed$expression, file.path(config$output_dir, "compartment_expression.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    write.table(processed$pcahawley_patient_expression,
      file.path(config$output_dir, "pcahawley_per_patient_expression.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    sc_lin_write_dotplot(processed$expression, file.path(config$output_dir, "compartment_dotplot.png"),
      "compartment", "Lin patient-level compartment expression", "median_log2_cpm_plus1")
  }
  if (mode == "pseudobulk") {
    write.table(processed$marker_map, file.path(config$output_dir, "labels_markers.tsv"),
      sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
    sc_lin_write_dotplot(processed$marker_map, file.path(config$output_dir, "labels_dotplot.png"),
      "author_label", "Lin author cell labels and canonical markers")
  }
}
bridge_write_session(config$output_dir)
