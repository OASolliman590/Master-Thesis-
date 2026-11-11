source("R/bridge.R")
source("R/random_streams.R")
config <- bridge_config()

required_packages <- c("jsonlite", "BiocManager", "digest", "immunedeconv", "quantiseqr", "limSolve")
bridge_require(required_packages)

reference_files <- c(
  "TIL10_signature.txt",
  "TIL10_mRNA_scaling.txt",
  "TIL10_rmgenes.txt",
  "TIL10_TCGA_aberrant_immune_genes.txt",
  "HGNC_genenames_20170418.txt.gz"
)
reference_path <- system.file("extdata", package = "quantiseqr", mustWork = TRUE)
reference_hashes <- setNames(
  vapply(reference_files, function(name) {
    path <- file.path(reference_path, name)
    if (!file.exists(path)) stop("Missing locked quanTIseq reference: ", name)
    digest::digest(file = path, algo = "sha256", serialize = FALSE)
  }, character(1)),
  reference_files
)
native_method_default <- eval(formals(quantiseqr::run_quantiseq)$method)
if (!identical(native_method_default, "lsei")) {
  stop("Locked quantiseqr native method default is not lsei")
}

allowed_cohorts <- c(
  "riaz_gse91061", "hugo_gse78220", "gse168204", "liu2019",
  "gide2019", "vanallen2015", "gse135222", "gse176307",
  "kim2018", "gse145996", "gse165278", "gse218989"
)
project_root <- normalizePath(as.character(config$config$project_root), mustWork = TRUE)
if (!file.exists(file.path(project_root, "docs", "cohorts", "REGISTRY.tsv"))) {
  stop("A-COMP project root has no cohort registry")
}

identity_token <- function(value) {
  tolower(gsub("[^[:alnum:]]", "", enc2utf8(as.character(value))))
}

read_named_tsv_columns <- function(path, columns, label) {
  header <- names(utils::read.delim(
    path, nrows = 0L, check.names = FALSE, stringsAsFactors = FALSE
  ))
  if (anyDuplicated(header) || any(!columns %in% header)) {
    stop(label, " is missing a named read-boundary column")
  }
  column_classes <- ifelse(header %in% columns, "character", "NULL")
  selected <- utils::read.delim(
    path, check.names = FALSE, stringsAsFactors = FALSE,
    colClasses = column_classes
  )
  selected <- selected[, columns, drop = FALSE]
  if (!identical(names(selected), columns)) stop(label, " selected columns changed order")
  selected
}

known_cohort_ids <- function() {
  registry <- read_named_tsv_columns(
    file.path(project_root, "docs", "cohorts", "REGISTRY.tsv"),
    "cohort_id", "Cohort registry"
  )
  as.character(registry$cohort_id)
}

known_real_alias <- function(value) {
  token <- identity_token(value)
  known <- unique(identity_token(known_cohort_ids()))
  any(grepl("imvigor|braun", token)) || any(vapply(known, function(item) {
    nzchar(item) && (identical(item, token) || grepl(item, token, fixed = TRUE))
  }, logical(1)))
}

has_symlink <- function(path) {
  link <- Sys.readlink(path)
  length(link) > 0L && !is.na(link[[1L]]) && nzchar(link[[1L]])
}

assert_no_symlink_ancestry <- function(path, label) {
  expanded <- path.expand(as.character(path))
  if (!startsWith(expanded, "/")) expanded <- file.path(getwd(), expanded)
  expanded <- gsub("\\\\", "/", expanded)
  parts <- strsplit(sub("^/", "", expanded), "/", fixed = TRUE)[[1L]]
  current <- "/"
  for (part in parts) {
    if (!nzchar(part) || identical(part, ".")) next
    if (identical(part, "..")) {
      if (has_symlink(current)) stop(label, " path has symlink ancestry")
      current <- dirname(current)
      next
    }
    current <- file.path(current, part)
    if (has_symlink(current)) stop(label, " path has symlink ancestry")
  }
}

guard_external_paths <- function(paths, data_classification) {
  if (!data_classification %in% c("real", "synthetic")) stop("Invalid A-COMP data classification")
  known <- unique(identity_token(known_cohort_ids()))
  protected <- setdiff(known, identity_token(allowed_cohorts))
  for (label in names(paths)) {
    original <- path.expand(as.character(paths[[label]]))
    assert_no_symlink_ancestry(original, label)
    resolved <- normalizePath(original, winslash = "/", mustWork = FALSE)
    components <- unique(c(
      identity_token(strsplit(gsub("\\\\", "/", original), "/", fixed = TRUE)[[1L]]),
      identity_token(strsplit(gsub("\\\\", "/", resolved), "/", fixed = TRUE)[[1L]])
    ))
    if (any(grepl("imvigor|braun|ingestionpacket|freshingest|^ingest-", components))) {
      stop(label, " path is inside an ingestion or protected-family path")
    }
    blocked <- if (data_classification == "synthetic") known else protected
    if (any(vapply(blocked, function(identifier) {
      nzchar(identifier) && any(grepl(identifier, components, fixed = TRUE))
    }, logical(1)))) {
      stop(label, " path contains a real or protected cohort identity")
    }
  }
  invisible(TRUE)
}

canonicalize_json <- function(value) {
  if (!is.list(value)) return(value)
  names_value <- names(value)
  if (!is.null(names_value) && length(names_value) == length(value)) {
    value <- value[order(names_value, method = "radix")]
    return(lapply(value, canonicalize_json))
  }
  lapply(value, canonicalize_json)
}

canonical_json <- function(value) {
  as.character(jsonlite::toJSON(
    canonicalize_json(value), auto_unbox = TRUE, null = "null", na = "null",
    digits = NA, pretty = FALSE, force = TRUE
  ))
}

manifest_from_path <- function(path, label) {
  if (!file.exists(path) || dir.exists(path)) stop(label, " is missing or not a file")
  manifest <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  if (!is.list(manifest)) stop(label, " must be a JSON object")
  manifest
}

snapshot_verified_file <- function(path, label, data_classification, expected_hash = NULL) {
  guard_external_paths(setNames(list(path), label), data_classification)
  source <- path.expand(as.character(path))
  source_link <- Sys.readlink(source)
  if (!file.exists(source) || dir.exists(source) ||
      (length(source_link) && !is.na(source_link[[1L]]) && nzchar(source_link[[1L]]))) {
    stop(label, " must be a regular, non-symlink file")
  }
  before <- digest::digest(file = source, algo = "sha256", serialize = FALSE)
  if (!is.null(expected_hash) && !identical(before, as.character(expected_hash))) {
    stop(label, " hash does not match its admission record")
  }
  stage_root <- dirname(config$output_dir)
  snapshot_dir <- file.path(stage_root, "verified_inputs")
  guard_external_paths(c(snapshot_dir = snapshot_dir), data_classification)
  dir.create(snapshot_dir, recursive = TRUE, showWarnings = FALSE)
  extension <- tools::file_ext(source)
  suffix <- if (nzchar(extension)) paste0(".", extension) else ".bin"
  destination <- file.path(snapshot_dir, paste0(label, "_", substr(before, 1L, 16L), suffix))
  guard_external_paths(c(snapshot = destination), data_classification)
  if (file.exists(destination)) {
    if (dir.exists(destination) || !identical(
      digest::digest(file = destination, algo = "sha256", serialize = FALSE), before
    )) stop(label, " verified snapshot already exists with different bytes")
  } else if (!file.copy(source, destination, overwrite = FALSE)) {
    stop("Could not snapshot verified ", label)
  }
  after <- digest::digest(file = source, algo = "sha256", serialize = FALSE)
  copied <- digest::digest(file = destination, algo = "sha256", serialize = FALSE)
  if (!identical(before, after) || !identical(before, copied)) {
    stop(label, " changed while its verified snapshot was being created")
  }
  list(path = destination, sha256 = copied)
}

verify_fixture_manifest <- function(manifest_path, input_path, kind, role, expected_columns) {
  manifest_snapshot <- snapshot_verified_file(
    manifest_path, paste0(role, "_manifest"), "synthetic"
  )
  manifest <- manifest_from_path(manifest_snapshot$path, "Synthetic provenance manifest")
  if (!identical(manifest$producer, "tools.a_meta.synthetic_fixture") ||
      !identical(manifest$data_classification, "synthetic") ||
      is.na(suppressWarnings(as.integer(manifest$manifest_version))) ||
      as.integer(manifest$manifest_version) != 1L || !identical(manifest$kind, kind)) {
    stop("A-META synthetic-fixture provenance record is required")
  }
  cohort_ids <- unlist(manifest$cohort_ids, use.names = FALSE)
  if (!length(cohort_ids) || anyDuplicated(cohort_ids) ||
      any(!startsWith(as.character(cohort_ids), "invented_")) ||
      any(vapply(cohort_ids, known_real_alias, logical(1)))) {
    stop("Synthetic provenance cannot authorize known real or protected cohort identities")
  }
  declaration <- manifest$declaration
  if (!is.list(declaration) || !identical(
    digest::digest(canonical_json(declaration), algo = "sha256", serialize = FALSE),
    manifest$payload_sha256
  )) stop("Synthetic provenance declaration hash mismatch")
  if (!setequal(as.character(unlist(declaration$cohort_ids, use.names = FALSE)), as.character(cohort_ids))) {
    stop("Synthetic provenance cohort declaration mismatch")
  }
  input_hashes <- unlist(declaration$input_sha256, use.names = TRUE)
  if (is.null(names(input_hashes)) || !role %in% names(input_hashes)) {
    stop("Synthetic provenance does not declare the input hash")
  }
  input_snapshot <- snapshot_verified_file(
    input_path, role, "synthetic", expected_hash = input_hashes[[role]]
  )
  actual_hash <- input_snapshot$sha256
  header <- names(utils::read.delim(
    input_snapshot$path, nrows = 0L, check.names = FALSE, stringsAsFactors = FALSE
  ))
  if (!identical(header, expected_columns)) {
    stop("Synthetic input columns must exactly match the named read boundary")
  }
  identity_columns <- intersect(c("study_id", "sample_id"), expected_columns)
  identity_rows <- read_named_tsv_columns(
    input_snapshot$path, identity_columns, "Synthetic input"
  )
  observed_ids <- unique(as.character(identity_rows$study_id))
  if (!setequal(observed_ids, as.character(cohort_ids)) ||
      any(!startsWith(observed_ids, "invented_")) ||
      any(vapply(c(observed_ids, as.character(identity_rows$sample_id)), known_real_alias, logical(1))) ||
      ("sample_id" %in% identity_columns && any(!startsWith(identity_rows$sample_id, "invented_")))) {
    stop("Synthetic input study identity contradicts its provenance or names a real cohort")
  }
  selected <- read_named_tsv_columns(
    input_snapshot$path, expected_columns, "Synthetic input"
  )
  list(data = selected, manifest = manifest, input_path = input_snapshot$path,
       manifest_path = manifest_snapshot$path)
}

read_n15_pin <- function(path) {
  lines <- readLines(path, warn = FALSE)
  text <- paste(lines, collapse = "\n")
  match <- regexec("(?s)```json[[:space:]]*(\\{.*\\})[[:space:]]*```", text, perl = TRUE)
  chunks <- regmatches(text, match)[[1L]]
  if (length(chunks) != 2L) stop("N15 document has no machine-readable JSON contract")
  pin <- jsonlite::fromJSON(chunks[[2L]], simplifyVector = FALSE)
  if (!identical(pin$status, "SIGNED")) stop("N15 pin status is ", pin$status, "; direct R execution requires SIGNED")
  if (!is.list(pin$signature) || !nzchar(as.character(pin$signature$signed_by)) ||
      !nzchar(as.character(pin$signature$signed_on))) stop("N15 signature record is incomplete")
  contract <- pin[setdiff(names(pin), c("status", "signature", "contract_sha256"))]
  hash <- digest::digest(canonical_json(contract), algo = "sha256", serialize = FALSE)
  if (!identical(hash, pin$contract_sha256)) stop("N15 contract hash mismatch at the R boundary")
  packages <- list(
    immunedeconv = "2.1.4", quantiseqr = "1.20.0", limSolve = "2.0.3"
  )
  installed <- as.list(vapply(names(packages), function(package) {
    as.character(utils::packageVersion(package))
  }, character(1)))
  if (!identical(as.character(getRversion()), "4.6.1") ||
      !identical(as.character(BiocManager::version()), "3.23") || !identical(installed, packages) ||
      !identical(as.list(reference_hashes), pin$reference_files)) {
    stop("N15 runtime or reference identities do not match the direct R process")
  }
  expected_method <- list(
    wrapper = "immunedeconv::deconvolute", method = "quantiseq",
    signature_matrix = "TIL10", native_method = "lsei", tumor = TRUE,
    arrays = FALSE, scale_mrna = TRUE, rmgenes = NULL, rm_genes = NULL,
    rna_rm_genes_behavior = "packaged default noisy-gene removal",
    tumor_exclusions = "packaged aberrant immune-gene list"
  )
  if (!identical(pin$method, expected_method) ||
      !identical(unlist(pin$input_policy$cohorts, use.names = FALSE), allowed_cohorts)) {
    stop("N15 method or cohort scope is incomplete at the R boundary")
  }
  pin
}

read_signature <- function() {
  path <- file.path(reference_path, "TIL10_signature.txt")
  signature <- read.delim(path, header = TRUE, row.names = 1, check.names = FALSE)
  signature <- as.matrix(signature)
  storage.mode(signature) <- "double"
  if (any(!is.finite(signature)) || any(signature < 0)) {
    stop("Locked TIL10 signature has invalid numeric values")
  }
  signature
}

read_effective_exclusions <- function() {
  rm_path <- file.path(reference_path, "TIL10_rmgenes.txt")
  tumor_path <- file.path(reference_path, "TIL10_TCGA_aberrant_immune_genes.txt")
  unique(c(readLines(rm_path, warn = FALSE), readLines(tumor_path, warn = FALSE)))
}

canonical_cell_type <- function(value) {
  mapping <- c(
    "B cell" = "B cell",
    "Macrophage M1" = "Macrophage M1",
    "Macrophage M2" = "Macrophage M2",
    "Monocyte" = "Monocyte",
    "Neutrophil" = "Neutrophil",
    "NK cell" = "NK cell",
    "T cell CD4+ (non-regulatory)" = "T cell CD4+ (non-regulatory)",
    "T cell CD8+" = "T cell CD8+",
    "T cell regulatory (Tregs)" = "T cell regulatory (Tregs)",
    "Myeloid dendritic cell" = "Myeloid dendritic cell",
    "uncharacterized cell" = "Other"
  )
  result <- unname(mapping[value])
  if (length(result) != 1L || is.na(result)) stop("Unexpected quanTIseq cell type: ", value)
  result
}

signature_cell_type <- function(value) {
  mapping <- c(
    "B.cells" = "B cell",
    "Macrophages.M1" = "Macrophage M1",
    "Macrophages.M2" = "Macrophage M2",
    "Monocytes" = "Monocyte",
    "Neutrophils" = "Neutrophil",
    "NK.cells" = "NK cell",
    "T.cells.CD4" = "T cell CD4+ (non-regulatory)",
    "T.cells.CD8" = "T cell CD8+",
    "Tregs" = "T cell regulatory (Tregs)",
    "Dendritic.cells" = "Myeloid dendritic cell"
  )
  result <- unname(mapping[value])
  if (length(result) != 1L || is.na(result)) stop("Unexpected TIL10 signature cell type: ", value)
  result
}

coverage_table <- function(genes, study_id, signature, floor) {
  exclusions <- read_effective_exclusions()
  weak <- c("B cell", "Macrophage M2", "T cell regulatory (Tregs)")
  rows <- lapply(seq_len(ncol(signature)), function(index) {
    native_name <- colnames(signature)[[index]]
    cell_name <- signature_cell_type(native_name)
    all_signature_genes <- rownames(signature)[signature[, index] != 0]
    eligible_genes <- setdiff(all_signature_genes, exclusions)
    before_found <- intersect(all_signature_genes, genes)
    after_found <- intersect(eligible_genes, genes)
    before_total <- length(all_signature_genes)
    after_total <- length(eligible_genes)
    before_coverage <- if (before_total) length(before_found) / before_total else NA_real_
    after_coverage <- if (after_total) length(after_found) / after_total else NA_real_
    status <- if (!after_total || is.na(after_coverage) || after_coverage < floor) "unavailable" else "available"
    data.frame(
      study_id = study_id,
      cell_type = cell_name,
      signature_genes_before = before_total,
      present_before = length(before_found),
      coverage_before = before_coverage,
      signature_genes_after_effective_exclusions = after_total,
      present_after_effective_exclusions = length(after_found),
      coverage_after_effective_exclusions = after_coverage,
      unavailable = status == "unavailable",
      weak_type_flag = cell_name %in% weak,
      status = status,
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, rows)
}

run_deconvolution <- function(expression, study_id, floor) {
  signature <- read_signature()
  genes <- rownames(expression)
  coverage <- coverage_table(genes, study_id, signature, floor)
  unavailable <- coverage$cell_type[coverage$status != "available"]
  if (length(unavailable)) {
    return(list(
      coverage = coverage,
      fractions = data.frame(sample_id = character(), cell_type = character(), fraction = numeric()),
      status = list(
        status = "refused",
        reason = paste0("proposed coverage floor failed for: ", paste(unavailable, collapse = ", ")),
        coverage_floor = floor,
        coverage_floor_is_project_proposal = TRUE,
        renormalized = FALSE
      )
    ))
  }
  native_method_default <- eval(formals(quantiseqr::run_quantiseq)$method)
  if (!identical(native_method_default, "lsei")) stop("Native quanTIseq method must be lsei")
  result <- immunedeconv::deconvolute(
    gene_expression = expression,
    method = "quantiseq",
    tumor = TRUE,
    arrays = FALSE,
    column = "gene_symbol",
    rmgenes = NULL,
    scale_mrna = TRUE,
    signature_matrix = "TIL10",
    rm_genes = NULL
  )
  if (!is.data.frame(result) || !identical(names(result)[[1L]], "cell_type")) {
    stop("immunedeconv returned an unexpected quanTIseq result shape")
  }
  sample_ids <- names(result)[-1L]
  expected_types <- c(
    "B cell", "Macrophage M1", "Macrophage M2", "Monocyte", "Neutrophil",
    "NK cell", "T cell CD4+ (non-regulatory)", "T cell CD8+",
    "T cell regulatory (Tregs)", "Myeloid dendritic cell", "Other"
  )
  result$cell_type <- vapply(result$cell_type, canonical_cell_type, character(1))
  if (!setequal(result$cell_type, expected_types) || anyDuplicated(result$cell_type)) {
    stop("quanTIseq did not return all ten immune cell types plus Other")
  }
  fraction_rows <- do.call(rbind, lapply(seq_len(nrow(result)), function(row_index) {
    data.frame(
      sample_id = sample_ids,
      cell_type = result$cell_type[[row_index]],
      fraction = as.numeric(result[row_index, -1L, drop = TRUE]),
      stringsAsFactors = FALSE
    )
  }))
  value_rows <- split(fraction_rows$fraction, fraction_rows$sample_id)
  for (sample in names(value_rows)) {
    values <- value_rows[[sample]]
    if (any(!is.finite(values)) || any(values < -1e-6 | values > 1 + 1e-6)) {
      stop("quanTIseq returned an inadmissible fraction")
    }
    if (abs(sum(values) - 1) > 1e-6) {
      stop("quanTIseq fractions including Other do not sum to one within 1e-6")
    }
  }
  list(
    coverage = coverage,
    fractions = fraction_rows,
    status = list(
      status = "complete",
      reason = "",
      coverage_floor = floor,
      coverage_floor_is_project_proposal = TRUE,
      fraction_sum_tolerance = 1e-6,
      fraction_range_tolerance = 1e-6,
      renormalized = FALSE,
      wrapper_method = "quantiseq",
      native_method = "lsei",
      signature_matrix = "TIL10",
      tumor = TRUE,
      arrays = FALSE,
      scale_mrna = TRUE,
      rmgenes = NULL,
      rm_genes = NULL,
      rna_rm_genes_behavior = "packaged default noisy-gene removal",
      tumor_exclusions = "packaged aberrant immune-gene list"
    )
  )
}

write_tsv <- function(value, path) {
  utils::write.table(value, path, sep = "\t", row.names = FALSE, col.names = TRUE, quote = FALSE, na = "NA")
}

write_json <- function(value, path) {
  jsonlite::write_json(value, path, auto_unbox = TRUE, pretty = TRUE, null = "null")
}

operation <- as.character(config$config$operation)
if (operation == "preflight") {
  guard_external_paths(c(output = config$output_dir), "synthetic")
  report <- list(
    r_version = as.character(getRversion()),
    bioconductor_version = as.character(BiocManager::version()),
    package_versions = as.list(vapply(c("immunedeconv", "quantiseqr", "limSolve"), function(package) {
      as.character(utils::packageVersion(package))
    }, character(1))),
    package_licenses = as.list(vapply(c("immunedeconv", "quantiseqr", "limSolve"), function(package) {
      as.character(utils::packageDescription(package, fields = "License")[[1L]])
    }, character(1))),
    reference_files = as.list(reference_hashes),
    native_method_default = native_method_default,
    input_contract = "unlogged nonnegative finite full-source gene-symbol TPM",
    removal_contract = "RNA rm_genes=NULL uses packaged default; tumor mode adds packaged aberrant-gene removal"
  )
  write_json(report, file.path(config$output_dir, "reference_report.json"))
  bridge_write_session(config$output_dir)
} else if (operation == "deconvolve") {
  guard_external_paths(c(
    expression = config$inputs$expression,
    input_manifest = config$inputs$input_manifest,
    n15_pin = config$inputs$n15_pin,
    output = config$output_dir
  ), "real")
  pin_snapshot <- snapshot_verified_file(
    config$inputs$n15_pin, "n15_pin", "real"
  )
  pin <- read_n15_pin(pin_snapshot$path)
  cohort_id <- as.character(config$config$cohort_id)
  if (length(cohort_id) != 1L || !cohort_id %in% allowed_cohorts) {
    stop("Direct R deconvolution cohort identity is outside the admitted A-COMP set")
  }
  manifest_snapshot <- snapshot_verified_file(
    config$inputs$input_manifest, "input_manifest", "real"
  )
  input_manifest <- manifest_from_path(manifest_snapshot$path, "Real TPM input manifest")
  if (!identical(input_manifest$manifest_version, 1) ||
      !identical(input_manifest$data_classification, "real") ||
      !identical(as.character(input_manifest$cohort_id), cohort_id) ||
      !identical(as.character(input_manifest$n15_pin_sha256), digest::digest(
        file = pin_snapshot$path, algo = "sha256", serialize = FALSE
      ))) {
    stop("Real input provenance does not bind classification, cohort identity, and N15")
  }
  representation <- input_manifest$representation
  if (!is.list(representation) || !identical(representation$platform, "RNA-seq") ||
      !identical(representation$unit, "TPM") || !identical(representation$transform, "unlogged linear") ||
      !identical(representation$feature_id, "HGNC gene symbol") || !isTRUE(representation$full_source)) {
    stop("Real TPM input manifest does not declare full-source unlogged gene-symbol TPM")
  }
  source_provenance <- input_manifest$source_provenance
  decision_path <- file.path(project_root, "docs", "decisions", "A_P2_MEASUREMENT_20261102.md")
  decision_hash <- digest::digest(file = decision_path, algo = "sha256", serialize = FALSE)
  if (!is.list(source_provenance) ||
      !identical(source_provenance$decision_id, "A_P2_MEASUREMENT_20261102") ||
      !identical(as.character(source_provenance$decision_sha256), decision_hash) ||
      !identical(as.character(source_provenance$source_route_id), as.character(representation$route_id)) ||
      length(source_provenance$source_manifest_sha256) != 1L ||
      !grepl("^[0-9a-f]{64}$", as.character(source_provenance$source_manifest_sha256))) {
    stop("Real TPM admission requires the hash-bound A-P2 decision and source-manifest provenance")
  }
  if (length(input_manifest$expression_sha256) != 1L ||
      !grepl("^[0-9a-f]{64}$", as.character(input_manifest$expression_sha256))) {
    stop("Real TPM provenance requires a declared expression SHA256")
  }
  stop("Real A-COMP source admission is not implemented; the TPM expression payload remains unopened")
} else if (operation == "synthetic_demo") {
  guard_external_paths(c(
    panel_definitions = config$inputs$panel_definitions,
    panel_manifest = config$inputs$panel_manifest,
    output = config$output_dir
  ), "synthetic")
  manifest_snapshot <- snapshot_verified_file(
    config$inputs$panel_manifest, "panel_manifest", "synthetic"
  )
  panel_manifest <- manifest_from_path(manifest_snapshot$path, "Synthetic panel provenance")
  declared_studies <- sprintf("invented_cohort_%02d", 1:4)
  if (!identical(panel_manifest$producer, "tools.a_meta.synthetic_fixture") ||
      !identical(panel_manifest$data_classification, "synthetic") ||
      is.na(suppressWarnings(as.integer(panel_manifest$manifest_version))) ||
      as.integer(panel_manifest$manifest_version) != 1L ||
      !identical(panel_manifest$kind, "a_comp_panel_definitions") ||
      any(vapply(unlist(panel_manifest$cohort_ids, use.names = FALSE), known_real_alias, logical(1))) ||
      !setequal(as.character(unlist(panel_manifest$cohort_ids, use.names = FALSE)), declared_studies)) {
    stop("Synthetic panel definitions require hash-bound invented cohort provenance")
  }
  declaration <- panel_manifest$declaration
  if (!is.list(declaration) || !identical(
    digest::digest(canonical_json(declaration), algo = "sha256", serialize = FALSE),
    panel_manifest$payload_sha256
  )) stop("Synthetic panel declaration hash mismatch")
  if (!identical(declaration$schema, "A_COMP_PANEL_DEFINITIONS_V1") ||
      !setequal(as.character(unlist(declaration$cohort_ids, use.names = FALSE)), declared_studies)) {
    stop("Synthetic panel declaration identities or schema do not match the fixture")
  }
  panel_expected_hash <- unlist(declaration$input_sha256, use.names = TRUE)[["panel_definitions"]]
  panel_snapshot <- snapshot_verified_file(
    config$inputs$panel_definitions, "panel_definitions", "synthetic",
    expected_hash = panel_expected_hash
  )
  panel_hash <- panel_snapshot$sha256
  if (!identical(as.character(unlist(declaration$input_sha256)[["panel_definitions"]]), panel_hash)) {
    stop("Synthetic panel-definition file hash mismatch")
  }
  panel_header <- names(utils::read.delim(
    panel_snapshot$path, nrows = 0L, check.names = FALSE, stringsAsFactors = FALSE
  ))
  if (!identical(panel_header, c("panel", "gene_symbol"))) {
    stop("Synthetic panel definitions must contain only the named columns")
  }
  panel_definitions <- read_named_tsv_columns(
    panel_snapshot$path, c("panel", "gene_symbol"), "Synthetic panel definitions"
  )
  if (!all(c("panel", "gene_symbol") %in% names(panel_definitions)) ||
      any(!nzchar(panel_definitions$gene_symbol))) {
    stop("Synthetic panel definition table is malformed")
  }
  signature <- read_signature()
  panel_genes <- unique(c(as.character(panel_definitions$gene_symbol), "GZMA", "PRF1"))
  all_genes <- unique(c(rownames(signature), panel_genes))
  studies <- sprintf("invented_cohort_%02d", 1:4)
  cancers <- c("melanoma", "bladder", "melanoma", "melanoma")
  drug_classes <- c("ANTI_PD_L1_AXIS", "ANTI_PD_L1_AXIS", "ANTI_CTLA4", "ANTI_PD_L1_AXIS")
  orr_responders <- list(
    c(1, 2, 5, 7, 10, 12), c(2, 3, 6, 8, 9, 11),
    c(1, 4, 5, 8, 10, 11), c(1, 3, 5, 8, 9, 11)
  )
  benefit_responders <- list(
    c(1, 3, 4, 6, 8, 11), c(1, 4, 5, 7, 9, 12),
    c(2, 3, 5, 6, 9, 10), c(2, 4, 6, 7, 10, 12)
  )
  source_responders <- list(
    c(2, 3, 6, 7, 9, 12), c(1, 2, 5, 6, 10, 11),
    c(1, 3, 4, 7, 8, 12), c(1, 4, 5, 6, 8, 10)
  )
  sample_groups <- list()
  all_expression <- matrix(0.01, nrow = length(all_genes), ncol = length(studies) * 12L,
                           dimnames = list(all_genes, character(length(studies) * 12L)))
  fractions <- list()
  coverages <- list()
  column_cursor <- 0L
  for (study_index in seq_along(studies)) {
    study_id <- studies[[study_index]]
    sample_ids <- sprintf("invented_%02d_%03d", study_index, 1:12)
    samples <- matrix(0, nrow = nrow(signature), ncol = length(sample_ids),
                      dimnames = list(rownames(signature), sample_ids))
    for (sample_index in seq_along(sample_ids)) {
      orr_responder <- sample_index %in% orr_responders[[study_index]]
      benefit_responder <- sample_index %in% benefit_responders[[study_index]]
      source_responder <- sample_index %in% source_responders[[study_index]]
      weights <- vapply(seq_len(ncol(signature)), function(cell_index) {
        baseline <- if (cell_index == 8L && orr_responder) 2.4 else if (cell_index == 8L) 0.5 else 1.0
        baseline * (0.35 + abs(sin(sample_index * 0.61 + study_index * 0.29 + cell_index * 0.43)))
      }, numeric(1))
      weights <- weights / sum(weights)
      samples[, sample_index] <- as.numeric(signature %*% weights)
      sample_groups[[length(sample_groups) + 1L]] <- data.frame(
        study_id = study_id,
        sample_id = sample_ids[[sample_index]],
        cancer = cancers[[study_index]],
        drug_class = drug_classes[[study_index]],
        orr_label = if (orr_responder) "CR" else "PD",
        clinical_benefit_label = if (benefit_responder) "DCB" else "NDB",
        source_label = if (source_responder) "Responder" else "Progressor",
        orr_definition = "ORR: CR/PR versus SD/PD; original best.resp category retained.",
        clinical_benefit_definition = "DCB/NDB",
        source_label_definition = "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST.",
        stringsAsFactors = FALSE
      )
    }
    extra_genes <- setdiff(all_genes, rownames(signature))
    if (length(extra_genes)) {
      for (gene_index in seq_along(extra_genes)) {
        gene <- extra_genes[[gene_index]]
        samples_row <- vapply(seq_along(sample_ids), function(sample_index) {
          0.25 + ((gene_index * 7L + sample_index * 3L + study_index * 5L) %% 19L) / 4
        }, numeric(1))
        samples <- rbind(samples, setNames(matrix(samples_row, nrow = 1L), sample_ids))
        rownames(samples)[nrow(samples)] <- gene
      }
    }
    if (anyDuplicated(rownames(samples))) stop("Synthetic TPM gene symbols are not unique")
    column_indexes <- column_cursor + seq_along(sample_ids)
    all_expression[, column_indexes] <- samples[all_genes, , drop = FALSE]
    colnames(all_expression)[column_indexes] <- sample_ids
    column_cursor <- max(column_indexes)

    cohort_result <- run_deconvolution(samples, study_id, 0.90)
    if (!identical(cohort_result$status$status, "complete")) {
      stop("Synthetic TIL10 coverage failed the test-only proposal: ", cohort_result$status$reason)
    }
    fractions[[length(fractions) + 1L]] <- transform(cohort_result$fractions, study_id = study_id)
    coverages[[length(coverages) + 1L]] <- cohort_result$coverage
  }
  group_table <- do.call(rbind, sample_groups)
  fraction_table <- do.call(rbind, fractions)
  coverage_table_out <- do.call(rbind, coverages)
  expression_table <- data.frame(gene_symbol = rownames(all_expression), all_expression,
                                 check.names = FALSE, stringsAsFactors = FALSE)
  names(expression_table) <- c("gene_symbol", colnames(all_expression))
  write_tsv(expression_table, file.path(config$output_dir, "tpm.tsv"))
  write_tsv(group_table, file.path(config$output_dir, "sample_groups.tsv"))
  write_tsv(fraction_table, file.path(config$output_dir, "fractions.tsv"))
  write_tsv(coverage_table_out, file.path(config$output_dir, "coverage.tsv"))
  write_json(list(
    data_classification = "synthetic",
    source_universe = "invented feature set generated only for software demonstration",
    full_source = TRUE,
    route_id = "INVENTED_FULL_SOURCE_TPM_V1",
    genes = nrow(all_expression),
    samples = ncol(all_expression),
    biology_validated = FALSE,
    quantiseq = list(signature = "TIL10", method = "lsei", tumor = TRUE, arrays = FALSE,
                     scale_mrna = TRUE, rm_genes = NULL, rna_rm_genes_behavior = "packaged default",
                     tumor_exclusions = "packaged aberrant immune-gene list"),
    cibersortx = "not run"
  ), file.path(config$output_dir, "quantiseq_run.json"))
  bridge_write_session(config$output_dir)
} else if (operation == "synthetic_incremental_auc") {
  auc_columns <- c(
    "study_id", "sample_id", "orr", "clinical_benefit", "source_label",
    "CYT", "synthetic_weighted_gep18",
    paste0("fraction__", c(
      "B cell", "Macrophage M1", "Macrophage M2", "Monocyte", "Neutrophil",
      "NK cell", "T cell CD4+ (non-regulatory)", "T cell CD8+",
      "T cell regulatory (Tregs)", "Myeloid dendritic cell", "Other"
    ))
  )
  guard_external_paths(c(
    auc_input = config$inputs$auc_input,
    auc_manifest = config$inputs$auc_manifest,
    output = config$output_dir
  ), "synthetic")
  admitted_auc <- verify_fixture_manifest(
    config$inputs$auc_manifest, config$inputs$auc_input,
    "a_comp_incremental_auc_input", "auc_input", auc_columns
  )
  input <- admitted_auc$data
  if (!identical(admitted_auc$manifest$declaration$schema, "A_COMP_SYNTHETIC_AUC_INPUT_V1") ||
      !identical(as.character(unlist(admitted_auc$manifest$declaration$input_columns, use.names = FALSE)), auc_columns) ||
      !identical(as.character(unlist(admitted_auc$manifest$declaration$clinical_columns, use.names = FALSE)),
                 c("study_id", "sample_id", "orr", "clinical_benefit", "source_label"))) {
    stop("Synthetic incremental-AUROC declaration does not bind its exact schema and named endpoints")
  }
  input$study_id <- as.character(input$study_id)
  input$sample_id <- as.character(input$sample_id)
  numeric_columns <- setdiff(auc_columns, c("study_id", "sample_id"))
  for (column in numeric_columns) input[[column]] <- suppressWarnings(as.numeric(input[[column]]))
  if (any(!nzchar(input$sample_id)) || any(!startsWith(input$sample_id, "invented_")) ||
      any(vapply(c(input$study_id, input$sample_id), known_real_alias, logical(1))) ||
      anyDuplicated(paste(input$study_id, input$sample_id, sep = "\x1f"))) {
    stop("Synthetic incremental-AUROC sample identities must be unique and invented")
  }
  if (any(!is.finite(as.matrix(input[, numeric_columns, drop = FALSE])))) {
    stop("Synthetic incremental-AUROC inputs must be finite numeric values")
  }
  for (endpoint in c("orr", "clinical_benefit", "source_label")) {
    if (!all(input[[endpoint]] %in% c(0, 1))) stop("Synthetic endpoint must be binary")
    input[[endpoint]] <- as.integer(input[[endpoint]])
  }
  fractions <- auc_columns[startsWith(auc_columns, "fraction__")]
  auc_rank <- function(y, score) {
    n_pos <- sum(y == 1L)
    n_neg <- sum(y == 0L)
    if (!n_pos || !n_neg) return(NA_real_)
    ranks <- rank(score, ties.method = "average")
    (sum(ranks[y == 1L]) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
  }
  fit_predictions <- function(y, predictors) {
    data <- as.data.frame(predictors, check.names = FALSE)
    data$outcome <- y
    terms <- paste0("`", names(predictors), "`")
    formula <- stats::as.formula(paste("outcome ~", paste(terms, collapse = " + ")))
    warnings <- character()
    fit <- tryCatch(
      withCallingHandlers(
        stats::glm(formula, data = data, family = stats::binomial()),
        warning = function(condition) {
          warnings <<- unique(c(warnings, conditionMessage(condition)))
          invokeRestart("muffleWarning")
        }
      ),
      error = function(condition) condition
    )
    if (inherits(fit, "error")) {
      return(list(status = "not_estimable", reason = paste("glm_error", conditionMessage(fit), sep = ":")))
    }
    if (!isTRUE(fit$converged)) {
      return(list(status = "not_estimable", reason = "glm_did_not_converge"))
    }
    if (length(warnings)) {
      return(list(status = "not_estimable", reason = paste("glm_warning", paste(warnings, collapse = " | "), sep = ":")))
    }
    if (any(!is.finite(stats::coef(fit)))) {
      return(list(status = "not_estimable", reason = "glm_nonfinite_coefficients"))
    }
    predictions <- tryCatch(
      as.numeric(stats::predict(fit, newdata = data, type = "response")),
      error = function(condition) condition
    )
    if (inherits(predictions, "error") || any(!is.finite(predictions))) {
      reason <- if (inherits(predictions, "error")) conditionMessage(predictions) else "nonfinite_predictions"
      return(list(status = "not_estimable", reason = paste("prediction_error", reason, sep = ":")))
    }
    list(status = "ok", reason = "", predictions = predictions)
  }
  main_assignments <- list()
  second_assignments <- list()
  result_rows <- list()
  prediction_rows <- list()
  task_seeds <- list()
  studies <- sort(unique(as.character(input$study_id)), method = "radix")
  endpoints <- c("orr", "clinical_benefit", "source_label")
  bases <- c("CYT", "synthetic_weighted_gep18")
  task_number <- 0L
  for (study_id in studies) {
    study_rows <- input[input$study_id == study_id, , drop = FALSE]
    order_index <- order(enc2utf8(as.character(study_rows$sample_id)), method = "radix")
    study_rows <- study_rows[order_index, , drop = FALSE]
    if (anyDuplicated(study_rows$sample_id)) stop("Synthetic bootstrap sample keys must be unique")
    for (endpoint in endpoints) {
      y <- as.integer(study_rows[[endpoint]])
      if (!all(y %in% c(0L, 1L))) stop("Synthetic endpoints must be binary")
      for (base in bases) {
        for (fraction_name in fractions) {
          task_number <- task_number + 1L
          task_id <- paste("a_comp_synthetic_demo_v2", study_id, endpoint, base, fraction_name, sep = "|")
          fraction_values <- as.numeric(study_rows[[fraction_name]])
          status <- "ok"
          reason <- ""
          if (sum(y == 1L) < 2L || sum(y == 0L) < 2L) {
            status <- "not_estimable"
            reason <- "fewer than two cases in an outcome class"
          } else if (length(unique(fraction_values)) < 2L) {
            status <- "not_estimable"
            reason <- "fraction is constant within this invented study"
          }
          baseline_predictions <- NULL
          augmented_predictions <- NULL
          baseline_auc <- augmented_auc <- NA_real_
          if (status == "ok") {
            baseline_fit <- fit_predictions(
              y, setNames(list(as.numeric(study_rows[[base]])), base)
            )
            augmented_predictors <- setNames(
              list(as.numeric(study_rows[[base]]), fraction_values),
              c(base, fraction_name)
            )
            augmented_fit <- fit_predictions(y, augmented_predictors)
            if (baseline_fit$status != "ok") {
              status <- "not_estimable"
              reason <- paste("baseline", baseline_fit$reason, sep = ":")
            } else if (augmented_fit$status != "ok") {
              status <- "not_estimable"
              reason <- paste("augmented", augmented_fit$reason, sep = ":")
            } else {
              baseline_predictions <- baseline_fit$predictions
              augmented_predictions <- augmented_fit$predictions
              baseline_auc <- auc_rank(y, baseline_predictions)
              augmented_auc <- auc_rank(y, augmented_predictions)
            }
          }
          if (status == "ok") {
            prediction_rows[[length(prediction_rows) + 1L]] <- data.frame(
              task_id = task_id, study = study_id, endpoint_family = endpoint,
              baseline_model = base, fraction = sub("^fraction__", "", fraction_name),
              row_index = seq_along(y), sample_id = as.character(study_rows$sample_id),
              outcome = y, baseline_prediction = baseline_predictions,
              augmented_prediction = augmented_predictions,
              stringsAsFactors = FALSE
            )
            main_seed_hex <- digest::digest(paste0(config$config$primary_synthetic_seed, "|", task_id),
                                            algo = "sha256", serialize = FALSE)
            main_seed <- strtoi(substr(main_seed_hex, 1L, 7L), base = 16L)
            set.seed(main_seed, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
            primary_deltas <- numeric(as.integer(config$config$bootstrap_repetitions))
            for (replicate in seq_along(primary_deltas)) {
              pos <- which(y == 1L)
              neg <- which(y == 0L)
              sampled <- c(pos[sample.int(length(pos), length(pos), replace = TRUE)],
                           neg[sample.int(length(neg), length(neg), replace = TRUE)])
              primary_deltas[[replicate]] <- auc_rank(y[sampled], augmented_predictions[sampled]) -
                auc_rank(y[sampled], baseline_predictions[sampled])
              main_assignments[[length(main_assignments) + 1L]] <- data.frame(
                task_id = task_id, check = "primary_synthetic_only", replicate = replicate,
                draw = seq_along(sampled), row_index = sampled, stringsAsFactors = FALSE
              )
            }
            second_task_id <- paste(config$config$second_check_task_id, study_id, endpoint, base, fraction_name, sep = "|")
            second_result <- bootstrap_indices(
              strata = ifelse(y == 1L, "R", "NR"),
              row_key = as.character(study_rows$sample_id),
              study = rep(study_id, length(y)),
              stream = "second_check",
              task_id = second_task_id,
              repetitions = as.integer(config$config$second_check_repetitions)
            )
            second_deltas <- numeric(as.integer(config$config$second_check_repetitions))
            for (replicate in seq_along(second_deltas)) {
              sampled <- second_result$indices$row_index[second_result$indices$replicate == replicate]
              second_deltas[[replicate]] <- auc_rank(y[sampled], augmented_predictions[sampled]) -
                auc_rank(y[sampled], baseline_predictions[sampled])
            }
            second_assignments[[length(second_assignments) + 1L]] <- transform(
              second_result$indices,
              task_id = task_id,
              check = "second_check_report_only"
            )[, c("task_id", "check", "replicate", "draw", "row_index"), drop = FALSE]
            main_interval <- as.numeric(stats::quantile(primary_deltas, c(0.025, 0.975), names = FALSE, type = 7))
            second_interval <- as.numeric(stats::quantile(second_deltas, c(0.025, 0.975), names = FALSE, type = 7))
            endpoint_shift <- max(abs(main_interval - second_interval))
            second_flag <- endpoint_shift > 0.01
            main_delta <- augmented_auc - baseline_auc
            second_seed <- random_seed_for_task("second_check", second_task_id)
            task_seeds[[length(task_seeds) + 1L]] <- data.frame(
              task_id = task_id, primary_seed = main_seed,
              second_check_task_id = second_task_id, second_check_seed = second_seed,
              stringsAsFactors = FALSE
            )
            result_rows[[length(result_rows) + 1L]] <- data.frame(
              study = study_id, endpoint_family = endpoint, baseline_model = base,
              fraction = sub("^fraction__", "", fraction_name),
              auc_baseline = baseline_auc, auc_augmented = augmented_auc,
              delta_auc = main_delta, ci_lb = main_interval[[1L]], ci_ub = main_interval[[2L]],
              second_check_ci_lb = second_interval[[1L]], second_check_ci_ub = second_interval[[2L]],
              second_check_endpoint_shift = endpoint_shift,
              second_check_flag_gt_0_01 = second_flag,
              second_check_reported_only = TRUE, second_check_replaced_main = FALSE,
              outcome_based_rerun = FALSE, model_refit = FALSE,
              evaluation = "same outcome-stratified resample of fixed full-data predictions",
              method_id = if (base == "CYT") "CYT_SQRT_TPM_GZMA_PRF1_NO_OFFSET" else "SYNTHETIC_WEIGHTED_GEP18_DEMO",
              gep_is_published = FALSE, status = status, reason = reason,
              stringsAsFactors = FALSE
            )
          } else {
            result_rows[[length(result_rows) + 1L]] <- data.frame(
              study = study_id, endpoint_family = endpoint, baseline_model = base,
              fraction = sub("^fraction__", "", fraction_name),
              auc_baseline = baseline_auc, auc_augmented = augmented_auc,
              delta_auc = NA_real_, ci_lb = NA_real_, ci_ub = NA_real_,
              second_check_ci_lb = NA_real_, second_check_ci_ub = NA_real_,
              second_check_endpoint_shift = NA_real_, second_check_flag_gt_0_01 = NA,
              second_check_reported_only = TRUE, second_check_replaced_main = FALSE,
              outcome_based_rerun = FALSE, model_refit = FALSE,
              evaluation = "synthetic-only contract; not estimable",
              method_id = if (base == "CYT") "CYT_SQRT_TPM_GZMA_PRF1_NO_OFFSET" else "SYNTHETIC_WEIGHTED_GEP18_DEMO",
              gep_is_published = FALSE, status = status, reason = reason,
              stringsAsFactors = FALSE
            )
          }
        }
      }
    }
  }
  result_table <- do.call(rbind, result_rows)
  assignments <- rbind(do.call(rbind, main_assignments), do.call(rbind, second_assignments))
  predictions <- if (length(prediction_rows)) do.call(rbind, prediction_rows) else data.frame(
    task_id = character(), study = character(), endpoint_family = character(),
    baseline_model = character(), fraction = character(), row_index = integer(),
    sample_id = character(), outcome = integer(), baseline_prediction = numeric(),
    augmented_prediction = numeric(), stringsAsFactors = FALSE
  )
  write_tsv(result_table, file.path(config$output_dir, "incremental_auc.tsv"))
  write_tsv(assignments, file.path(config$output_dir, "bootstrap_assignments.tsv"))
  write_tsv(predictions, file.path(config$output_dir, "auc_predictions.tsv"))
  assignment_hash <- digest::digest(file = file.path(config$output_dir, "bootstrap_assignments.tsv"),
                                    algo = "sha256", serialize = FALSE)
  receipt <- list(
    contract_id = "a_comp_synthetic_demo_v2",
    primary_stream = "a_comp_synthetic_demo_v2 (synthetic-only; not added to signed register)",
    primary_seed_root = config$config$primary_synthetic_seed,
    primary_repetitions = config$config$bootstrap_repetitions,
    second_check_stream = "second_check",
    second_check_repetitions = config$config$second_check_repetitions,
    rng = list(kind = "Mersenne-Twister", normal_kind = "Inversion", sample_kind = "Rejection"),
    assignment_sha256 = assignment_hash,
    task_seeds = task_seeds,
    second_check_reporting = "report only; flag if either 95% interval endpoint shifts by >0.01 AUROC",
    replaced_main_result = FALSE,
    outcome_based_rerun = FALSE,
    model_refit = FALSE,
    evaluation = "same outcome-stratified resample of fixed full-data predictions",
    paired_evaluation = "baseline and augmented AUROC use identical row_index assignments",
    published_gep_used = FALSE
  )
  write_json(receipt, file.path(config$output_dir, "bootstrap_receipt.json"))
  bridge_write_session(config$output_dir)
} else {
  stop("Unknown A-COMP R operation")
}
