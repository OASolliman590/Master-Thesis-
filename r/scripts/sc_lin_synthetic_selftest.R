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

fixture_profile <- function(profile_id, patient_id, sample_id, layer, n_cells = 8L) {
  data.frame(
    profile_id = profile_id, patient_id = patient_id, patient = patient_id,
    sample_id = sample_id, sample = sample_id, cohort = "Synthetic_SC",
    study = "Synthetic_SC", cancer = "synthetic", treatment = "aPD1",
    response_metric = "RECIST", response = "R", outcome_label = "R",
    endpoint_family = "RECIST", compartment = "T/NK", n_cells = n_cells,
    total_umis = 6000, library_size = 6000, reason = "", eligible = TRUE,
    status = "eligible", count_layer = layer, fraction_cells_total = 0.5,
    baseline = TRUE, stringsAsFactors = FALSE
  )
}
left_profiles <- rbind(
  fixture_profile("synthetic_only_left", "synthetic_patient_left", "synthetic_sample_left", "layer_one"),
  fixture_profile("synthetic_shared", "synthetic_patient_shared", "synthetic_sample_shared", "layer_one")
)
right_profiles <- rbind(
  fixture_profile("synthetic_shared", "synthetic_patient_shared", "synthetic_sample_shared", "layer_two"),
  fixture_profile("synthetic_only_right", "synthetic_patient_right", "synthetic_sample_right", "layer_two")
)
left_counts <- Matrix::Matrix(matrix(
  c(2, 5, 7, 3, 11, 13), nrow = 3,
  dimnames = list(c("COMMON", "ONLY_LEFT", "NONFINITE"), left_profiles$profile_id)
), sparse = TRUE)
right_counts <- Matrix::Matrix(matrix(
  c(17, 19, Inf, 29, 31, 37), nrow = 3,
  dimnames = list(c("COMMON", "ONLY_RIGHT", "NONFINITE"), right_profiles$profile_id)
), sparse = TRUE)
left_detection <- Matrix::Matrix(matrix(
  c(1, 2, 3, 4, 5, 6), nrow = 3,
  dimnames = list(c("COMMON", "ONLY_LEFT", "NONFINITE"), left_profiles$profile_id)
), sparse = TRUE)
right_detection <- Matrix::Matrix(matrix(
  c(7, 8, Inf, 9, 10, 11), nrow = 3,
  dimnames = list(c("COMMON", "ONLY_RIGHT", "NONFINITE"), right_profiles$profile_id)
), sparse = TRUE)
merge_fixture <- list(
  layer_one = list(counts = left_counts, detection = left_detection, clinical = left_profiles),
  layer_two = list(counts = right_counts, detection = right_detection, clinical = right_profiles)
)
reference_merge <- function(slot_name) {
  profile_ids <- unique(unlist(lapply(merge_fixture, function(layer) layer$clinical$profile_id), use.names = FALSE))
  genes <- unique(unlist(lapply(merge_fixture, function(layer) rownames(layer[[slot_name]])), use.names = FALSE))
  output <- matrix(NA_real_, nrow = length(genes), ncol = length(profile_ids),
    dimnames = list(genes, profile_ids))
  for (profile_id in profile_ids) {
    sources <- names(merge_fixture)[vapply(merge_fixture, function(layer) {
      profile_id %in% layer$clinical$profile_id
    }, logical(1))]
    for (gene in genes) {
      if (!all(vapply(sources, function(source) gene %in% rownames(merge_fixture[[source]][[slot_name]]), logical(1)))) next
      values <- vapply(sources, function(source) {
        as.numeric(merge_fixture[[source]][[slot_name]][gene, profile_id])
      }, numeric(1))
      if (all(is.finite(values))) output[gene, profile_id] <- sum(values)
    }
  }
  output
}
merged_fixture <- sc_lin_merge_layer_profiles(merge_fixture, min_cells = 0L, min_umis = 0L)
vectorized_merge_matches_reference <-
  isTRUE(all.equal(merged_fixture$layers$merged$counts, reference_merge("counts"), tolerance = 0)) &&
  isTRUE(all.equal(merged_fixture$layers$merged$detection, reference_merge("detection"), tolerance = 0))
merged_counts <- merged_fixture$layers$merged$counts
vectorized_merge_explicit_cases <-
  merged_counts["COMMON", "synthetic_only_left"] == 2 &&
  merged_counts["COMMON", "synthetic_shared"] == 20 &&
  merged_counts["COMMON", "synthetic_only_right"] == 29 &&
  is.na(merged_counts["ONLY_LEFT", "synthetic_shared"]) &&
  is.na(merged_counts["ONLY_RIGHT", "synthetic_shared"]) &&
  is.na(merged_counts["NONFINITE", "synthetic_shared"])
if (!vectorized_merge_matches_reference || !vectorized_merge_explicit_cases) {
  stop("Vectorized Lin layer merge differs from the per-gene reference result")
}
jsonlite::write_json(list(two_count_layers = TRUE, weighted_layer_markers = marker_weights_ok,
  cross_layer_patient_profile = TRUE, gate0_identity_mismatch_refused = identity_mismatch_refused,
  vectorized_merge_matches_reference = vectorized_merge_matches_reference,
  vectorized_merge_explicit_cases = vectorized_merge_explicit_cases),
  file.path(config$output_dir, "checks.json"), auto_unbox = TRUE, pretty = TRUE)
bridge_write_session(config$output_dir)
