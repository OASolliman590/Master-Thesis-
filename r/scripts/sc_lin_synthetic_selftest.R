source("R/bridge.R")
bridge_require(c(SeuratObject = "5.4.0", qs2 = "0.4.0"))
bridge_require(c("jsonlite", "BiocManager"))
config <- bridge_config()

make_cells <- function(prefix, count) paste0(prefix, seq_len(count))
cells_a <- make_cells("synthetic_a_", 15)
cells_b <- make_cells("synthetic_b_", 15)
cells_c <- make_cells("synthetic_c_", 15)
mat_a <- Matrix::Matrix(matrix(rep(c(250, 250), 15), nrow = 2,
  dimnames = list(c("GENEA", "GENEB"), cells_a)), sparse = TRUE)
mat_b <- Matrix::Matrix(matrix(rep(c(10, 10), 15), nrow = 2,
  dimnames = list(c("GENEA", "GENEB"), cells_b)), sparse = TRUE)
mat_c <- Matrix::Matrix(matrix(rep(c(250, 250), 15), nrow = 2,
  dimnames = list(c("GENEB", "GENEC"), cells_c)), sparse = TRUE)
layer_one <- cbind(mat_a, mat_b)
layer_two <- mat_c
metadata <- data.frame(
  patient = c(rep("synthetic_a", 15), rep("synthetic_b", 15), rep("synthetic_c", 15)),
  sample = c(rep("synthetic_specimen_a", 15), rep("synthetic_specimen_b", 15), rep("synthetic_specimen_c", 15)),
  cohort = "PCa_Hawley",
  time_point = "Pre",
  treatment = "aPD1",
  response = rep(c("R", "NR", "NR"), each = 15),
  res_metric = "RECIST",
  celltype_main = "CD8+T",
  row.names = c(cells_a, cells_b, cells_c),
  stringsAsFactors = FALSE
)
object <- SeuratObject::CreateSeuratObject(
  counts = list(layer_one = layer_one, layer_two = layer_two),
  meta.data = metadata,
  min.cells = 0,
  min.features = 0
)
layers <- SeuratObject::Layers(object[["RNA"]], search = "^counts($|[.])")
if (length(layers) != 2L) stop("Synthetic Seurat object did not retain two count layers")
qs2::qs_save(object, file.path(config$output_dir, "synthetic_seurat.qs2"))
write.table(data.frame(cohort = "PCa_Hawley", cancer = "prostate", stringsAsFactors = FALSE),
  file.path(config$output_dir, "cohort_map.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
write.table(data.frame(source_field = "celltype_main", source_label = "CD8+T", compartment = "T/NK", stringsAsFactors = FALSE),
  file.path(config$output_dir, "compartment_map.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
write.table(data.frame(panel_id = "synthetic_panel", gene = c("GENEA", "GENEB", "GENEC"), stringsAsFactors = FALSE),
  file.path(config$output_dir, "panel_membership.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)
jsonlite::write_json(list(two_count_layers = TRUE), file.path(config$output_dir, "checks.json"), auto_unbox = TRUE, pretty = TRUE)
bridge_write_session(config$output_dir)
