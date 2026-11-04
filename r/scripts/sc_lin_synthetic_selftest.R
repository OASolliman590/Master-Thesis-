source("R/bridge.R")
bridge_require(c(SeuratObject = "5.4.0", qs2 = "0.4.0"))
bridge_require(c("jsonlite", "BiocManager"))
source("R/sc_lin.R")
config <- bridge_config()

make_cells <- function(prefix, count) paste0(prefix, seq_len(count))
cells_a <- make_cells("synthetic_a_", 15)
cells_b <- make_cells("synthetic_b_", 15)
cells_c <- make_cells("synthetic_c_", 15)
cells_bad <- make_cells("synthetic_bad_", 15)
cells_unmapped_a <- make_cells("synthetic_a_unmapped_", 15)
cells_merge_left <- make_cells("synthetic_merge_left_", 8)
cells_merge_right <- make_cells("synthetic_merge_right_", 8)
mat_a <- Matrix::Matrix(matrix(rep(c(250, 250, 10), 15), nrow = 3,
  dimnames = list(c("GENEA", "GENEB", "CD3D"), cells_a)), sparse = TRUE)
mat_b <- Matrix::Matrix(matrix(rep(c(10, 10, 10), 15), nrow = 3,
  dimnames = list(c("GENEA", "GENEB", "CD3D"), cells_b)), sparse = TRUE)
mat_c <- Matrix::Matrix(matrix(rep(c(250, 250, 10), 15), nrow = 3,
  dimnames = list(c("GENEB", "GENEC", "CD3D"), cells_c)), sparse = TRUE)
mat_bad <- Matrix::Matrix(matrix(rep(c(250.5, 250, 10), 15), nrow = 3,
  dimnames = list(c("GENEB", "GENEC", "CD3D"), cells_bad)), sparse = TRUE)
mat_unmapped_a <- Matrix::Matrix(matrix(rep(c(250, 250, 10), 15), nrow = 3,
  dimnames = list(c("GENEA", "GENEB", "CD3D"), cells_unmapped_a)), sparse = TRUE)
mat_merge_left <- Matrix::Matrix(matrix(rep(c(250, 250, 10), 8), nrow = 3,
  dimnames = list(c("GENEA", "GENEB", "CD3D"), cells_merge_left)), sparse = TRUE)
mat_merge_right <- Matrix::Matrix(matrix(rep(c(250, 10, 250), 8), nrow = 3,
  dimnames = list(c("GENEB", "GENEC", "CD3D"), cells_merge_right)), sparse = TRUE)
layer_one <- cbind(mat_a, mat_b, mat_unmapped_a, mat_merge_left)
layer_two <- cbind(mat_c, mat_bad, mat_merge_right)
metadata <- data.frame(
  patient = c(rep("synthetic_a", 15), rep("synthetic_b", 15), rep("synthetic_c", 15),
    rep("synthetic_bad", 15), rep("synthetic_a", 15), rep("synthetic_merge", 8), rep("synthetic_merge", 8)),
  sample = c(rep("synthetic_specimen_a", 15), rep("synthetic_specimen_b", 15),
    rep("synthetic_specimen_c", 15), rep("synthetic_specimen_bad", 15), rep("synthetic_specimen_a", 15),
    rep("synthetic_specimen_merge", 8), rep("synthetic_specimen_merge", 8)),
  cohort = "PCa_Hawley",
  time_point = "Pre",
  treatment = "aPD1",
  response = c(rep("R", 15), rep("NR", 45), rep("R", 15), rep("NR", 16)),
  res_metric = "RECIST",
  celltype_main = c(rep("CD8+T", 60), rep("Cycling", 15), rep("CD8+T", 16)),
  row.names = c(cells_a, cells_b, cells_c, cells_bad, cells_unmapped_a, cells_merge_left, cells_merge_right),
  stringsAsFactors = FALSE
)
object <- SeuratObject::CreateSeuratObject(
  counts = list(layer_one = layer_one, layer_two = layer_two),
  meta.data = metadata,
  min.cells = 0,
  min.features = 0
)
wrong_metadata <- object[[]]
wrong_metadata$patient[[1]] <- "synthetic_wrong_patient"
identity_mismatch_refused <- inherits(try(sc_lin_validate_loaded_object(object, wrong_metadata), silent = TRUE), "try-error")
if (!identity_mismatch_refused) stop("Gate 0 identity mismatch was not refused")
layers <- SeuratObject::Layers(object[["RNA"]], search = "^counts($|[.])")
if (length(layers) != 2L) stop("Synthetic Seurat object did not retain two count layers")
qs2::qs_save(object, file.path(config$output_dir, "synthetic_seurat.qs2"))
saveRDS(object@meta.data, file.path(config$output_dir, "metadata.rds"))
write.table(data.frame(cohort = "PCa_Hawley", cancer = "prostate", stringsAsFactors = FALSE),
  file.path(config$output_dir, "cohort_map.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
write.table(data.frame(source_field = "celltype_main", source_label = "CD8+T", compartment = "T/NK", stringsAsFactors = FALSE),
  file.path(config$output_dir, "compartment_map.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
write.table(data.frame(panel_id = "synthetic_panel", gene = c("GENEA", "GENEB", "GENEC"), stringsAsFactors = FALSE),
  file.path(config$output_dir, "panel_membership.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
marker_records <- list(
  data.frame(author_label = "Synthetic T", gene = "CD3D", percent_cells_detected = 20,
    mean_log2_cpm_plus1 = 1, n_cells = 10),
  data.frame(author_label = "Synthetic T", gene = "CD3D", percent_cells_detected = 40,
    mean_log2_cpm_plus1 = 3, n_cells = 30)
)
combined_marker <- sc_lin_combine_marker_summaries(marker_records)
marker_weights_ok <- nrow(combined_marker) == 1L &&
  abs(combined_marker$percent_cells_detected[[1]] - 35) < 1e-8 &&
  abs(combined_marker$mean_log2_cpm_plus1[[1]] - 2.5) < 1e-8 &&
  combined_marker$n_cells[[1]] == 40
if (!marker_weights_ok) stop("Marker summaries were not weighted across count layers")
jsonlite::write_json(list(two_count_layers = TRUE, weighted_layer_markers = marker_weights_ok,
  cross_layer_patient_profile = TRUE, gate0_identity_mismatch_refused = identity_mismatch_refused),
  file.path(config$output_dir, "checks.json"), auto_unbox = TRUE, pretty = TRUE)
bridge_write_session(config$output_dir)
