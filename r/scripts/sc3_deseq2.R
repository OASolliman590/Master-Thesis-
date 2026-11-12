source("R/bridge.R")

reject_symlink_components <- function(path) {
  reject_forbidden <- function(value) {
    slash_path <- gsub(intToUtf8(92), "/", as.character(value), fixed = TRUE)
    parts <- strsplit(slash_path, "/", fixed = TRUE)[[1]]
    tokens <- tolower(gsub("[^[:alnum:]]", "", parts, perl = TRUE))
    if (any(grepl("imvigor210", tokens, fixed = TRUE)) ||
        any(grepl("ingestionpacketjson", tokens, fixed = TRUE))) {
      stop("SC-3 paths cannot reference forbidden protected paths")
    }
  }
  expanded <- path.expand(as.character(path))
  reject_forbidden(as.character(path))
  reject_forbidden(expanded)
  if (!startsWith(expanded, "/")) expanded <- file.path(getwd(), expanded)
  reject_forbidden(expanded)

  resolve_links <- function(value, depth = 0L) {
    if (depth > 40L) stop("SC-3 path symlink resolution exceeded its safe depth")
    slash_path <- gsub(intToUtf8(92), "/", as.character(value), fixed = TRUE)
    if (!startsWith(slash_path, "/")) slash_path <- file.path(getwd(), slash_path)
    parts <- strsplit(slash_path, "/", fixed = TRUE)[[1]]
    components <- if (length(parts) > 1L) parts[-1L] else character()
    current <- "/"
    for (index in seq_along(components)) {
      part <- components[[index]]
      if (!nzchar(part) || part == ".") next
      if (part == "..") {
        current <- dirname(current)
        next
      }
      current <- file.path(current, part)
      target <- Sys.readlink(current)
      if (!is.na(target) && nzchar(target)) {
        reject_forbidden(target)
        target_path <- if (startsWith(target, "/")) target else file.path(dirname(current), target)
        if (index < length(components)) {
          target_path <- do.call(file.path, as.list(c(target_path, components[(index + 1L):length(components)])))
        }
        return(resolve_links(target_path, depth + 1L))
      }
    }
    current
  }

  resolved <- resolve_links(expanded)
  reject_forbidden(resolved)
  parts <- strsplit(expanded, "/", fixed = TRUE)[[1]]
  current <- "/"
  if (length(parts) > 1L) {
    for (part in parts[-1L]) {
      if (!nzchar(part) || part == ".") next
      if (part == "..") {
        current <- dirname(current)
        next
      }
      current <- file.path(current, part)
      target <- Sys.readlink(current)
      if (!is.na(target) && nzchar(target)) stop("SC-3 paths cannot contain symlinks")
    }
  }
  invisible(expanded)
}

script_args <- commandArgs(trailingOnly = TRUE)
if (length(script_args) == 1L) reject_symlink_components(script_args[[1]])
config <- bridge_config()
authorization <- config$config$authorization
data_classification <- as.character(authorization$data_classification %||% "")
synthetic_mode <- identical(data_classification, "synthetic")
released_mode <- data_classification %in% c("real", "source_derived_test_fixture")
if (!synthetic_mode && !released_mode) {
  stop("SC-3 requires verified invented provenance or a bound source-derived release")
}
if (released_mode && !isTRUE(authorization$allow_outcomes)) {
  stop("SC-3 source-derived outcomes require explicit opt-in and a scoped release record")
}
if (released_mode && !nzchar(as.character(authorization$release_record %||% ""))) {
  stop("SC-3 source-derived outcomes require a scoped release record")
}
if (!setequal(names(config$inputs), c("counts", "clinical"))) {
  stop("SC-3 requires only named counts and clinical inputs")
}
invisible(lapply(unlist(config$inputs, use.names = FALSE), reject_symlink_components))
provenance_value <- as.character(authorization$provenance_manifest %||% "")
if (!nzchar(provenance_value)) stop("SC-3 provenance manifest is missing")
reject_symlink_components(provenance_value)
if (released_mode) reject_symlink_components(authorization$release_record)
reject_symlink_components(config$output_dir)

normalized_existing_path <- function(path, label, is_directory = FALSE) {
  reject_symlink_components(path)
  if (!file.exists(path)) stop(label, " does not exist")
  info <- file.info(path)
  if (is.na(info$isdir) || is_directory != isTRUE(info$isdir)) stop(label, " has the wrong file type")
  normalizePath(path, winslash = "/", mustWork = TRUE)
}

is_same_or_child <- function(candidate, parent) {
  identical(candidate, parent) || startsWith(candidate, paste0(sub("/$", "", parent), "/"))
}

input_names <- names(config$inputs)
input_paths <- vapply(config$inputs, normalized_existing_path, character(1), label = "SC-3 input", is_directory = FALSE)
manifest_path <- provenance_value
manifest_norm <- normalized_existing_path(manifest_path, "SC-3 provenance manifest", is_directory = FALSE)
release_norm <- if (released_mode) {
  normalized_existing_path(authorization$release_record, "SC-3 release record", is_directory = FALSE)
} else character()
output_path <- normalized_existing_path(config$output_dir, "SC-3 output directory", is_directory = TRUE)
all_input_paths <- c(unname(input_paths), manifest_norm, release_norm)
if (anyDuplicated(all_input_paths)) stop("SC-3 input, provenance, and release paths must be distinct")
if (any(vapply(all_input_paths, is_same_or_child, logical(1), parent = output_path))) {
  stop("SC-3 output directory cannot contain an input or provenance file")
}
output_targets <- file.path(output_path, c("de_results.tsv", "de_refusals.tsv"))
invisible(lapply(output_targets, reject_symlink_components))
if (any(file.exists(output_targets))) stop("SC-3 output files must be new and cannot alias inputs or provenance")

fdr_threshold <- suppressWarnings(as.numeric(config$config$fdr %||% 0.10))
if (length(fdr_threshold) != 1L || !is.finite(fdr_threshold) || fdr_threshold <= 0 || fdr_threshold >= 1) {
  stop("SC-3 FDR threshold must be between zero and one")
}
bridge_require(c(DESeq2 = "1.52.0", digest = "0.6.39"))
bridge_require(c("jsonlite", "BiocManager"))

read_header <- function(path) {
  header_line <- readLines(path, n = 1L, warn = FALSE)
  if (!length(header_line)) stop("TSV input has no header")
  strsplit(header_line[[1]], "\t", fixed = TRUE)[[1]]
}

read_named_tsv <- function(path, columns, classes = NULL) {
  header <- read_header(path)
  missing <- setdiff(columns, header)
  if (length(missing)) stop("TSV input is missing required named columns: ", paste(missing, collapse = ", "))
  col_classes <- rep("NULL", length(header))
  names(col_classes) <- header
  for (column in columns) {
    col_classes[match(column, header)] <- if (is.null(classes)) "character" else classes[[column]]
  }
  result <- utils::read.delim(path, check.names = FALSE, stringsAsFactors = FALSE,
    na.strings = c("NA", ""), colClasses = unname(col_classes))
  result[, columns, drop = FALSE]
}

script_argument <- grep("^--file=", commandArgs(FALSE), value = TRUE)
if (length(script_argument) != 1L) stop("Cannot locate the SC-3 repository root for provenance checks")
script_path <- normalizePath(sub("^--file=", "", script_argument[[1]]), winslash = "/", mustWork = TRUE)
repo_root <- normalizePath(file.path(dirname(script_path), "../.."), winslash = "/", mustWork = TRUE)
read_registry_ids <- function(path, column) read_named_tsv(path, column)[[column]]
is_locked_identity <- function(value) {
  token <- tolower(gsub("[^[:alnum:]]", "", as.character(value), perl = TRUE))
  grepl("imvigor210", token, fixed = TRUE)
}

path_within <- function(candidate, root, label) {
  if (!is_same_or_child(candidate, root)) stop("SC-3 ", label, " must remain inside the test-only fixture root")
}
test_only_root <- ""
test_registry_root <- ""
release_record <- NULL
decision_path <- ""
if (released_mode) {
  test_only_root <- as.character(authorization$test_only_root %||% "")
  test_mode <- nzchar(test_only_root)
  expected_classification <- if (test_mode) "source_derived_test_fixture" else "real"
  if (!identical(data_classification, expected_classification)) {
    stop("SC-3 source-derived classification does not match the execution mode")
  }
  if (test_mode) {
    reject_symlink_components(test_only_root)
    test_only_root <- normalizePath(test_only_root, winslash = "/", mustWork = TRUE)
    test_registry_root <- as.character(authorization$test_registry_root %||% "")
    if (!nzchar(test_registry_root)) stop("SC-3 test-only release requires an explicit fixture registry root")
    reject_symlink_components(test_registry_root)
    test_registry_root <- normalizePath(test_registry_root, winslash = "/", mustWork = TRUE)
    path_within(test_registry_root, test_only_root, "test registry")
    for (path in c(unname(input_paths), manifest_norm, release_norm, output_path)) {
      path_within(path, test_only_root, "test-only path")
    }
  } else if (nzchar(as.character(authorization$test_registry_root %||% ""))) {
    stop("SC-3 registry overrides are available only for test-only fixtures")
  }

  tryCatch({
    release_record <- jsonlite::fromJSON(release_norm, simplifyVector = FALSE)
  }, error = function(error) stop("SC-3 release record is malformed: ", conditionMessage(error)))
  expected_record_fields <- c(
    "record_type", "record_status", "real_authorization", "release_scope", "operation",
    "input_manifest_sha256", "input_sha256", "cohorts", "source_family_by_cohort",
    "source_resolution_status", "overlap_resolution_status", "metric_resolution_status",
    "outcome_fields", "decision"
  )
  if (!is.list(release_record) || !setequal(names(release_record), expected_record_fields)) {
    stop("SC-3 release record has missing or contradictory fields")
  }
  expected_status <- if (test_mode) "TEST_ONLY_APPROVED" else "APPROVED"
  if (!identical(release_record$record_type, "sc3_user_release_v1") ||
      !identical(release_record$record_status, expected_status) ||
      !identical(release_record$real_authorization, !test_mode) ||
      !identical(release_record$release_scope, "SC3_REAL_OUTCOME_ACCESS") ||
      !identical(release_record$operation, "sc3-analysis")) {
    stop("SC-3 release record is not approved for this operation and execution mode")
  }
  if (!is.list(release_record$cohorts)) stop("SC-3 release record needs an exact cohort array")
  release_cohort_values <- unlist(release_record$cohorts, use.names = FALSE)
  release_cohorts <- sort(release_cohort_values)
  if (!length(release_cohorts) || anyDuplicated(release_cohort_values) ||
      anyNA(release_cohort_values) || any(!nzchar(release_cohort_values)) ||
      any(vapply(release_cohorts, is_locked_identity, logical(1)))) {
    stop("SC-3 refuses the locked IMvigor210 final test")
  }
  decision <- release_record$decision
  if (!is.list(decision) || !setequal(names(decision), c("identity", "path", "sha256")) ||
      !is.character(decision$identity) || length(decision$identity) != 1L || !nzchar(decision$identity) ||
      !is.character(decision$path) || length(decision$path) != 1L ||
      !startsWith(decision$path, "docs/decisions/") ||
      grepl("(^|/)\\.\\.?(/|$)", decision$path) ||
      !is.character(decision$sha256) || length(decision$sha256) != 1L ||
      !grepl("^[0-9a-f]{64}$", decision$sha256)) {
    stop("SC-3 release decision reference is incomplete")
  }
  decision_root <- if (test_mode) test_only_root else repo_root
  decision_path <- file.path(decision_root, decision$path)
  reject_symlink_components(decision_path)
  decision_path <- normalized_existing_path(decision_path, "SC-3 release decision", is_directory = FALSE)
  if (!identical(tools::file_path_sans_ext(basename(decision_path)), decision$identity)) {
    stop("SC-3 release decision identity does not match its path")
  }
  decisions_root <- normalizePath(file.path(decision_root, "docs/decisions"), winslash = "/", mustWork = TRUE)
  path_within(decision_path, decisions_root, "release decision")
  if (any(vapply(c(unname(input_paths), manifest_norm, release_norm), function(path) identical(path, decision_path), logical(1))) ||
      is_same_or_child(decision_path, output_path)) {
    stop("SC-3 release decision cannot alias an input or output")
  }
  if (test_mode) path_within(decision_path, test_only_root, "test-only decision")
  decision_hash <- digest::digest(decision_path, algo = "sha256", file = TRUE)
  if (!identical(decision_hash, decision$sha256)) stop("SC-3 release decision identity or exact file hash does not match")
}

manifest_hash <- digest::digest(manifest_norm, algo = "sha256", file = TRUE)
if (released_mode && !identical(manifest_hash, as.character(release_record$input_manifest_sha256))) {
  stop("SC-3 release record does not bind this exact input manifest")
}
manifest <- jsonlite::fromJSON(manifest_norm, simplifyVector = FALSE)
if (synthetic_mode) {
  if (!identical(as.integer(manifest$manifest_version), 1L) ||
      !identical(manifest$producer, "tools.a_meta.synthetic_fixture") ||
      !identical(manifest$data_classification, "synthetic") ||
      !identical(manifest$kind, "sc3_r_input")) {
    stop("SC-3 synthetic provenance header is invalid")
  }
} else {
  if (!identical(as.integer(manifest$manifest_version), 1L) ||
      !identical(manifest$producer, "tools.sc.sc3_source_provenance") ||
      !identical(manifest$data_classification, data_classification) ||
      !identical(manifest$kind, "sc3_input")) {
    stop("SC-3 requires hash-matched source-derived input provenance")
  }
  if (!identical(manifest$source_resolution_status, "RESOLVED") ||
      !identical(manifest$overlap_resolution_status, "RESOLVED") ||
      !identical(manifest$metric_resolution_status, "RESOLVED")) {
    stop("SC-3 source, overlap, or metric mapping remains unresolved")
  }
  if (!identical(release_record$source_resolution_status, manifest$source_resolution_status) ||
      !identical(release_record$overlap_resolution_status, manifest$overlap_resolution_status) ||
      !identical(release_record$metric_resolution_status, manifest$metric_resolution_status)) {
    stop("SC-3 release record does not bind source, overlap, and metric resolution")
  }
  allowed_outcomes <- c("endpoint_family", "outcome_label", "response", "response_metric")
  if (!identical(unlist(release_record$outcome_fields, use.names = FALSE), allowed_outcomes)) {
    stop("SC-3 release record does not authorize the exact named outcome fields")
  }
}

if (released_mode && !is.list(manifest$cohort_ids)) stop("SC-3 source provenance needs a cohort array")
manifest_cohort_values <- unlist(manifest$cohort_ids, use.names = FALSE)
declared_cohorts <- sort(manifest_cohort_values)
if (!length(declared_cohorts) || anyDuplicated(manifest_cohort_values) ||
    anyNA(manifest_cohort_values) || any(!nzchar(manifest_cohort_values)) ||
    any(vapply(declared_cohorts, is_locked_identity, logical(1)))) {
  stop("SC-3 refuses the locked IMvigor210 final test")
}
if (released_mode && !identical(declared_cohorts, release_cohorts)) {
  stop("SC-3 release cohort set does not match source provenance")
}
source_family_by_cohort <- unlist(manifest$source_family_by_cohort, use.names = TRUE)
if (released_mode) {
  if (!is.list(manifest$source_family_by_cohort) || !is.list(release_record$source_family_by_cohort)) {
    stop("SC-3 release source-family mapping must be an explicit object")
  }
  record_source_map <- unlist(release_record$source_family_by_cohort, use.names = TRUE)
  if (!identical(source_family_by_cohort[sort(names(source_family_by_cohort))],
                 record_source_map[sort(names(record_source_map))]) ||
      !setequal(names(source_family_by_cohort), declared_cohorts)) {
    stop("SC-3 release source-family mapping does not match source provenance")
  }
  source_manifest_hashes <- unlist(manifest$input_sha256, use.names = TRUE)
  release_input_hashes <- unlist(release_record$input_sha256, use.names = TRUE)
  if (!setequal(names(source_manifest_hashes), c("clinical", "expression")) ||
      !setequal(names(release_input_hashes), c("clinical", "expression")) ||
      anyDuplicated(names(source_manifest_hashes)) || anyDuplicated(names(release_input_hashes)) ||
      anyNA(source_manifest_hashes) || anyNA(release_input_hashes) ||
      any(!grepl("^[0-9a-f]{64}$", source_manifest_hashes)) ||
      any(!grepl("^[0-9a-f]{64}$", release_input_hashes)) ||
      !identical(release_input_hashes[sort(names(release_input_hashes))],
                 source_manifest_hashes[sort(names(source_manifest_hashes))])) {
    stop("SC-3 release record does not bind the exact source input hashes")
  }
}

if (test_registry_root != "") {
  registry_root <- test_registry_root
} else {
  registry_root <- repo_root
}
registry_path <- file.path(registry_root, "docs/cohorts/REGISTRY.tsv")
lin_map_path <- file.path(registry_root, "tools/sc/lin_cohort_map.tsv")
reject_symlink_components(registry_path)
reject_symlink_components(lin_map_path)
registry <- read_registry_ids(registry_path, "cohort_id")
lin_cohorts <- read_registry_ids(lin_map_path, "cohort")
real_cohorts <- unique(c(registry, lin_cohorts, "prostate_hormone_naive_atlas"))
if (synthetic_mode && length(intersect(declared_cohorts, real_cohorts))) {
  stop("SC-3 synthetic provenance contradicts a known real cohort")
}
if (released_mode && length(setdiff(declared_cohorts, real_cohorts))) {
  stop("SC-3 source mapping is unresolved for unregistered cohorts")
}

clinical_header <- read_header(config$inputs$clinical)
if (anyDuplicated(clinical_header)) stop("SC-3 clinical header contains duplicate names")
allowed_clinical <- c("profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
  "endpoint_family", "response_metric", "outcome_label", "response", "eligible", "baseline", "treatment",
  "drug_class", "sc3_group_id", "n_cells", "total_umis", "library_size", "cancer", "fraction_cells_total")
if (length(setdiff(clinical_header, allowed_clinical))) stop("SC-3 clinical header contains unsupported protected columns")
if (released_mode && "sc3_group_id" %in% clinical_header) {
  stop("SC-3 source-derived input cannot preassign internal analysis group IDs")
}
identity_columns <- c("cohort", "source_family", "profile_id", "patient_id", "sample_id")
identity <- read_named_tsv(config$inputs$clinical, identity_columns)
if (anyNA(identity) || any(!nzchar(as.matrix(identity)))) stop("SC-3 identity columns contain missing values")
cohort_ids <- sort(unique(as.character(identity$cohort)))
if (any(vapply(cohort_ids, is_locked_identity, logical(1)))) {
  stop("SC-3 refuses known-real or protected clinical cohort identities; IMvigor210 is locked")
}
if (synthetic_mode && length(intersect(cohort_ids, real_cohorts))) {
  stop("SC-3 refuses known-real clinical cohort identities in synthetic fixtures")
}
if (released_mode && length(setdiff(cohort_ids, real_cohorts))) {
  stop("SC-3 source mapping is unresolved for unregistered clinical cohorts")
}
if (!identical(cohort_ids, declared_cohorts)) {
  stop("SC-3 manifest cohort IDs do not match named clinical identities")
}
cohort_source_counts <- tapply(identity$source_family, identity$cohort, function(x) length(unique(x)))
source_cohort_counts <- tapply(identity$cohort, identity$source_family, function(x) length(unique(x)))
if (any(cohort_source_counts != 1L) || any(source_cohort_counts != 1L)) {
  stop("SC-3 source-family metadata must map one cohort to one source family")
}
stable_identity <- paste(identity$patient_id, identity$sample_id, sep = "\x1f")
identity_cohorts <- tapply(identity$cohort, stable_identity, function(x) length(unique(x)))
identity_sources <- tapply(identity$source_family, stable_identity, function(x) length(unique(x)))
if (any(identity_cohorts > 1L) || any(identity_sources > 1L)) {
  stop("SC-3 stable patient/specimen identities occur in multiple source cohorts")
}
if (anyDuplicated(identity$profile_id)) stop("SC-3 profile identities must be unique")
if (released_mode) {
  actual_source_map <- tapply(identity$source_family, identity$cohort, function(values) unique(values)[[1]])
  actual_source_map <- actual_source_map[sort(names(actual_source_map))]
  expected_source_map <- source_family_by_cohort[sort(names(source_family_by_cohort))]
  if (!identical(as.character(actual_source_map), as.character(expected_source_map)) ||
      !identical(names(actual_source_map), names(expected_source_map))) {
    stop("SC-3 source-family mapping does not match named clinical identities")
  }
}

counts_hash <- digest::digest(config$inputs$counts, algo = "sha256", file = TRUE)
clinical_hash <- digest::digest(config$inputs$clinical, algo = "sha256", file = TRUE)
manifest_hashes <- unlist(manifest$input_sha256, use.names = TRUE)
if (synthetic_mode) {
  if (!setequal(names(manifest_hashes), c("counts", "clinical")) ||
      !identical(as.character(manifest_hashes[["counts"]]), counts_hash) ||
      !identical(as.character(manifest_hashes[["clinical"]]), clinical_hash)) {
    stop("SC-3 synthetic provenance does not bind the verified counts and clinical inputs")
  }
  payload <- paste0("counts:", counts_hash, "\nclinical:", clinical_hash,
    "\ncohorts:", paste(declared_cohorts, collapse = ","), "\n")
  payload_hash <- digest::digest(payload, algo = "sha256", serialize = FALSE)
  if (!identical(manifest$payload_sha256, payload_hash)) stop("SC-3 synthetic provenance does not match input hashes")
} else {
  release_hashes <- unlist(release_record$input_sha256, use.names = TRUE)
  if (!setequal(names(manifest_hashes), c("clinical", "expression")) ||
      !identical(as.character(manifest_hashes[["clinical"]]), clinical_hash) ||
      !identical(as.character(manifest_hashes[["expression"]]), counts_hash) ||
      !identical(release_hashes[sort(names(release_hashes))], manifest_hashes[sort(names(manifest_hashes))])) {
    stop("SC-3 source-derived provenance does not bind the exact clinical and expression inputs")
  }
}

metric_family <- function(value) {
  key <- tolower(gsub("_", " ", trimws(as.character(value))))
  if (key %in% c("recist", "objective response", "orr")) return("RECIST")
  if (key %in% c("pathology", "pathological response", "pathology response")) return("pathology")
  if (key %in% c("expansion", "t cell expansion", "t-cell expansion")) return("expansion")
  NA_character_
}

classify_treatment <- function(value) {
  tokens <- unlist(strsplit(tolower(trimws(as.character(value))), "\\s*(\\+|&|;|,|/| and )\\s*", perl = TRUE))
  tokens <- gsub("[^a-z0-9]", "", tokens)
  if (!length(tokens) || any(!nzchar(tokens))) return("OTHER_EXCLUDED")
  classes <- vapply(tokens, function(token) {
    if (token %in% c("apd1", "antipd1", "nivolumab", "pembrolizumab")) return("ANTI_PD1")
    if (token %in% c("apdl1", "antipdl1", "atezolizumab", "durvalumab", "avelumab")) return("ANTI_PDL1")
    if (token %in% c("actla4", "antictla4", "ipilimumab", "tremelimumab")) return("ANTI_CTLA4")
    "OTHER_EXCLUDED"
  }, character(1))
  if (any(classes == "OTHER_EXCLUDED")) return("OTHER_EXCLUDED")
  classes <- unique(classes)
  if (length(classes) == 1L && classes[[1]] == "ANTI_CTLA4") return("ANTI_CTLA4")
  if (length(classes) == 1L && classes[[1]] %in% c("ANTI_PD1", "ANTI_PDL1")) return("ANTI_PD_L1_AXIS")
  if (setequal(classes, c("ANTI_PD1", "ANTI_CTLA4")) || setequal(classes, c("ANTI_PDL1", "ANTI_CTLA4"))) {
    return("DUAL_PD1_CTLA4")
  }
  "OTHER_EXCLUDED"
}

clinical_columns <- intersect(allowed_clinical, clinical_header)
required <- c("profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
  "outcome_label", "eligible", "baseline", "treatment", "n_cells", "total_umis", "library_size")
if (synthetic_mode) required <- c(required, "sc3_group_id")
if (length(setdiff(required, clinical_header)) || !any(c("response_metric", "endpoint_family") %in% clinical_header)) {
  stop("SC-3 clinical profiles are missing required safe grouping fields")
}
clinical <- read_named_tsv(config$inputs$clinical, clinical_columns)
if (!identical(sort(unique(as.character(clinical$cohort))), declared_cohorts)) {
  stop("SC-3 clinical values differ from the preflight cohort identities")
}
if (anyNA(clinical$patient_id) || anyNA(clinical$sample_id) || any(!nzchar(clinical$patient_id)) ||
    any(!nzchar(clinical$sample_id)) || anyNA(clinical$source_family) || any(!nzchar(clinical$source_family))) {
  stop("SC-3 patient, specimen, and source-family identities must be non-empty")
}
cohort_source_counts <- tapply(clinical$source_family, clinical$cohort, function(x) length(unique(x)))
source_cohort_counts <- tapply(clinical$cohort, clinical$source_family, function(x) length(unique(x)))
if (any(cohort_source_counts != 1L) || any(source_cohort_counts != 1L)) {
  stop("SC-3 source-family metadata must map one cohort to one source family")
}
stable_identity <- paste(clinical$patient_id, clinical$sample_id, sep = "\x1f")
identity_cohorts <- tapply(clinical$cohort, stable_identity, function(x) length(unique(x)))
identity_sources <- tapply(clinical$source_family, stable_identity, function(x) length(unique(x)))
if (any(identity_cohorts > 1L) || any(identity_sources > 1L)) {
  stop("SC-3 stable patient/specimen identities occur in multiple source cohorts")
}
if (anyDuplicated(clinical$profile_id)) stop("SC-3 profile IDs must be unique")
if (released_mode) {
  validated_groups <- config$config$validated_groups
  if (is.null(validated_groups) || !length(validated_groups)) stop("SC-3 requires verified groups after release authorization")
  profile_to_group <- unlist(lapply(validated_groups, function(row) {
    setNames(rep(as.character(row$group_id), length(unlist(row$profile_ids, use.names = FALSE))),
      as.character(unlist(row$profile_ids, use.names = FALSE)))
  }), use.names = TRUE)
  if (anyDuplicated(names(profile_to_group)) || any(!names(profile_to_group) %in% clinical$profile_id)) {
    stop("SC-3 released group membership contains duplicate or unknown profile identities")
  }
  clinical$sc3_group_id <- unname(profile_to_group[as.character(clinical$profile_id)])
  if (!"endpoint_family" %in% names(clinical) && "response_metric" %in% names(clinical)) {
    clinical$endpoint_family <- vapply(clinical$response_metric, metric_family, character(1))
  }
}

count_header <- read_header(config$inputs$counts)
if (anyDuplicated(count_header) || !identical(count_header[[1]], "gene")) stop("SC-3 expression header is invalid")
profile_columns <- unique(as.character(clinical$profile_id))
if (length(setdiff(profile_columns, count_header[-1]))) stop("SC-3 expression columns do not align to clinical profiles")
count_columns <- c("gene", profile_columns)
count_classes <- c(gene = "character", stats::setNames(rep("integer", length(profile_columns)), profile_columns))
counts_frame <- read_named_tsv(config$inputs$counts, count_columns, classes = count_classes)
rownames(counts_frame) <- as.character(counts_frame$gene)
counts_frame$gene <- NULL
if (anyDuplicated(rownames(counts_frame)) || anyDuplicated(colnames(counts_frame))) stop("SC-3 count gene and profile identities must be unique")

aliases <- unlist(config$config$frozen_aliases, use.names = TRUE)
if (is.null(names(aliases)) || !length(aliases)) stop("SC-3 requires the frozen gene alias map")
canonical_gene <- function(gene) {
  current <- as.character(gene)
  visited <- character()
  while (current %in% names(aliases)) {
    if (current %in% visited) stop("Frozen SC-3 gene aliases contain a cycle")
    visited <- c(visited, current)
    current <- as.character(aliases[[current]])
  }
  current
}
canonical_genes <- vapply(rownames(counts_frame), canonical_gene, character(1))
if (anyDuplicated(canonical_genes)) stop("SC-3 expression identities collide after frozen alias resolution")
rownames(counts_frame) <- canonical_genes

if ("response" %in% colnames(clinical)) {
  expansion <- vapply(clinical$endpoint_family, function(value) identical(metric_family(value), "expansion"), logical(1))
  response_values <- toupper(trimws(as.character(clinical$response)))
  response_values[is.na(response_values)] <- ""
  if (any(expansion & response_values %in% c("R", "NR"))) stop("T-cell expansion labels cannot be stored as clinical response")
}
metric_values <- if ("response_metric" %in% colnames(clinical)) clinical$response_metric else clinical$endpoint_family
mapped_metrics <- vapply(metric_values, metric_family, character(1))
declared_metrics <- vapply(clinical$endpoint_family, metric_family, character(1))
grouped_rows <- !is.na(clinical$sc3_group_id) & nzchar(as.character(clinical$sc3_group_id))
if (anyNA(mapped_metrics[grouped_rows]) || anyNA(declared_metrics[grouped_rows]) ||
    any(mapped_metrics[grouped_rows] != declared_metrics[grouped_rows])) {
  stop("SC-3 response metric and endpoint family disagree")
}

validated_groups <- config$config$validated_groups
if (is.null(validated_groups) || !length(validated_groups)) stop("SC-3 requires validated groups from Python")
expected_ids <- vapply(validated_groups, function(row) as.character(row$group_id), character(1))
actual_group_ids <- unique(as.character(clinical$sc3_group_id[grouped_rows]))
if (anyDuplicated(expected_ids) || !setequal(actual_group_ids, expected_ids)) {
  stop("SC-3 group IDs do not match the validated Python group contract")
}
groups <- split(which(grouped_rows), as.character(clinical$sc3_group_id[grouped_rows]))
de_rows <- list()
for (expected in validated_groups) {
  group_id <- as.character(expected$group_id)
  selected <- groups[[group_id]]
  if (is.null(selected)) stop("A validated SC-3 group is absent from clinical profiles")
  frame <- clinical[selected, , drop = FALSE]
  if (length(unique(frame$cohort)) != 1L || length(unique(frame$source_family)) != 1L ||
      length(unique(frame$compartment)) != 1L || length(unique(mapped_metrics[selected])) != 1L ||
      !identical(as.character(frame$cohort[[1]]), as.character(expected$cohort)) ||
      !identical(as.character(frame$source_family[[1]]), as.character(expected$source_family)) ||
      !identical(as.character(frame$compartment[[1]]), as.character(expected$compartment)) ||
      !identical(as.character(mapped_metrics[selected[[1]]]), as.character(expected$endpoint_family))) {
    stop("SC-3 group identity differs from the validated Python contract")
  }
  if (anyDuplicated(frame$patient_id)) stop("SC-3 requires one profile per patient in every analysis group")
  if (anyDuplicated(frame$sample_id)) stop("SC-3 requires unique specimens in every analysis group")
  baseline <- tolower(trimws(as.character(frame$baseline)))
  eligible <- tolower(trimws(as.character(frame$eligible)))
  n_cells <- suppressWarnings(as.numeric(frame$n_cells))
  total_umis <- suppressWarnings(as.numeric(frame$total_umis))
  library_size <- suppressWarnings(as.numeric(frame$library_size))
  treatment_class <- vapply(frame$treatment, classify_treatment, character(1))
  if (any(!baseline %in% c("true", "1", "yes")) || any(!eligible %in% c("true", "1", "yes")) ||
      anyNA(n_cells) || anyNA(total_umis) || anyNA(library_size) || any(n_cells < 15) ||
      any(total_umis < 5000) || any(library_size <= 0) || any(treatment_class == "OTHER_EXCLUDED")) {
    stop("SC-3 groups may contain only eligible baseline ICI profiles meeting the 15-cell/5000-UMI floors")
  }
  if (any(!frame$outcome_label %in% c("R", "NR"))) stop("SC-3 validated groups may contain only R/NR profiles")
  n_r <- length(unique(frame$patient_id[frame$outcome_label == "R"]))
  n_nr <- length(unique(frame$patient_id[frame$outcome_label == "NR"]))
  profile_hash <- digest::digest(paste(sort(as.character(frame$profile_id)), collapse = "\n"),
    algo = "sha256", serialize = FALSE)
  if (n_r != as.integer(expected$n_R) || n_nr != as.integer(expected$n_NR) ||
      nrow(frame) != as.integer(expected$profile_count) ||
      !identical(profile_hash, as.character(expected$profile_ids_sha256))) {
    stop("SC-3 arm counts or profile membership differ from the validated Python contract")
  }
  if (n_r < 3L || n_nr < 3L) stop("SC-3 requires at least three distinct patients per arm")

  profile_ids <- as.character(frame$profile_id)
  current <- as.matrix(counts_frame[, profile_ids, drop = FALSE])
  complete <- rowSums(is.na(current)) == 0L
  current <- current[complete, , drop = FALSE]
  nonzero <- rowSums(current) > 0
  current <- current[nonzero, , drop = FALSE]
  if (nrow(current) < 2L) next
  if (any(!is.finite(current)) || any(current < 0) || any(current != trunc(current))) {
    stop("DESeq2 input must contain non-negative integer UMIs")
  }
  storage.mode(current) <- "integer"
  col_data <- data.frame(response = factor(frame$outcome_label, levels = c("NR", "R")), row.names = profile_ids)
  if (anyNA(col_data$response)) stop("Response levels are not exactly R and NR")
  attempt <- tryCatch({
    dds <- DESeq2::DESeqDataSetFromMatrix(current, colData = col_data, design = ~ response)
    dds <- DESeq2::DESeq(dds, quiet = TRUE)
    result <- as.data.frame(DESeq2::results(
      dds, contrast = c("response", "R", "NR"), pAdjustMethod = "BH",
      alpha = fdr_threshold, independentFiltering = FALSE
    ))
    result$gene <- rownames(result)
    result$comparison_id <- group_id
    result$cohort <- as.character(frame$cohort[[1]])
    result$compartment <- as.character(frame$compartment[[1]])
    result$endpoint_family <- as.character(mapped_metrics[selected[[1]]])
    result$status <- ifelse(is.na(result$pvalue), "pvalue_unavailable", "tested")
    result$reason <- ifelse(is.na(result$pvalue), "pvalue_NA_after_default_DESeq2_Cook_filter_or_model", "")
    result$padj_status <- ifelse(is.na(result$padj), "not_adjusted_pvalue_unavailable", "BH10_adjusted")
    if (any(!is.na(result$pvalue) & is.na(result$padj))) stop("Finite DESeq2 p-values must receive BH adjustment")
    result[, c("comparison_id", "cohort", "compartment", "endpoint_family", "gene", "baseMean",
      "log2FoldChange", "lfcSE", "stat", "pvalue", "padj", "status", "reason", "padj_status")]
  }, error = function(error) error)
  if (inherits(attempt, "error")) stop("DESeq2 failed for validated SC-3 group ", group_id, ": ", conditionMessage(attempt))
  de_rows[[length(de_rows) + 1L]] <- attempt
}
de_results <- if (length(de_rows)) do.call(rbind, de_rows) else data.frame(
  comparison_id = character(), cohort = character(), compartment = character(), endpoint_family = character(), gene = character(),
  baseMean = numeric(), log2FoldChange = numeric(), lfcSE = numeric(), stat = numeric(), pvalue = numeric(), padj = numeric(),
  status = character(), reason = character(), padj_status = character(), stringsAsFactors = FALSE
)
de_refusals <- data.frame(cohort = character(), compartment = character(), endpoint_family = character(), n_R = integer(),
  n_NR = integer(), reason = character(), detail = character(), stringsAsFactors = FALSE)
write.table(de_results, file.path(config$output_dir, "de_results.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
write.table(de_refusals, file.path(config$output_dir, "de_refusals.tsv"), sep = "\t", row.names = FALSE, quote = FALSE, na = "NA")
bridge_write_session(config$output_dir)
