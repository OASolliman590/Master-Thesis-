 .guard_path <- function(path, label) {
  if (length(path) != 1L || is.na(path) || !nzchar(as.character(path))) stop("A-LONG ", label, " path is missing")
  original <- path.expand(as.character(path))
  if (!startsWith(original, .Platform$file.sep)) original <- file.path(getwd(), original)
  original <- gsub("/+", "/", original)
  parts <- strsplit(original, "/", fixed = TRUE)[[1L]]
  current <- "/"
  for (part in parts[nzchar(parts)]) {
    current <- file.path(current, part)
    link <- Sys.readlink(current)
    if (length(link) && nzchar(link)) stop("A-LONG ", label, " path has symlink ancestry")
  }
  resolved <- normalizePath(original, winslash = "/", mustWork = FALSE)
  for (part in c(parts, strsplit(resolved, "/", fixed = TRUE)[[1L]])) {
    token <- gsub("[^a-z0-9]", "", tolower(part))
    if (grepl("ingestionpacketjson", token, fixed = TRUE)) stop("A-LONG never reads ingestion_packet.json")
    if (grepl("imvigor210", token, fixed = TRUE)) stop("A-LONG always refuses IMvigor210 paths")
  }
  resolved
}

.args <- commandArgs(trailingOnly = TRUE)
if (length(.args) != 1L) stop("Expected exactly one A-LONG bridge config path")
.guard_path(.args[[1L]], "bridge config")
source(file.path("R", "bridge.R"), local = TRUE)

request <- bridge_config()
cfg <- request$config
output_dir <- request$output_dir
mode <- cfg$mode

.sha256 <- function(path) {
  path <- .guard_path(path, "hash input")
  command <- Sys.which("shasum")
  args <- c("-a", "256", shQuote(path))
  if (!nzchar(command)) {
    command <- Sys.which("sha256sum")
    args <- shQuote(path)
  }
  if (!nzchar(command)) stop("A-LONG SHA256 support is unavailable")
  result <- tryCatch(system2(command, args, stdout = TRUE, stderr = FALSE), error = function(error) character())
  if (!length(result) || !grepl("^[0-9a-f]{64}\\s", result[[1L]])) stop("A-LONG SHA256 verification failed")
  substr(result[[1L]], 1L, 64L)
}

.json <- function(path, label) {
  guarded <- .guard_path(path, label)
  jsonlite::fromJSON(guarded, simplifyVector = FALSE)
}

.canonical_json <- function(value) {
  if (is.null(value)) return("null")
  if (is.list(value)) {
    keys <- names(value)
    if (is.null(keys)) {
      if (!length(value)) return("[]")
      return(paste0("[", paste(vapply(value, .canonical_json, character(1)), collapse = ","), "]"))
    }
    if (!length(keys)) return("{}")
    order_index <- order(keys, method = "radix")
    keys <- keys[order_index]
    parts <- vapply(keys, function(key) {
      paste0(
        as.character(jsonlite::toJSON(enc2utf8(key), auto_unbox = TRUE, digits = NA)),
        ":", .canonical_json(value[[key]])
      )
    }, character(1))
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  if (length(value) != 1L) {
    return(paste0("[", paste(vapply(as.list(value), .canonical_json, character(1)), collapse = ","), "]"))
  }
  if (is.na(value)) return("null")
  if (is.logical(value)) return(if (value) "true" else "false")
  if (is.character(value)) {
    return(as.character(jsonlite::toJSON(enc2utf8(value), auto_unbox = TRUE, digits = NA)))
  }
  if (is.numeric(value)) {
    if (!is.finite(value)) stop("A-LONG policy contains a non-finite number")
    return(as.character(jsonlite::toJSON(value, auto_unbox = TRUE, digits = NA)))
  }
  stop("A-LONG policy contains an unsupported JSON value")
}

.canonical_sha256 <- function(value) {
  digest::digest(
    charToRaw(enc2utf8(.canonical_json(value))),
    algo = "sha256",
    serialize = FALSE
  )
}

.same_json <- function(left, right) identical(.canonical_json(left), .canonical_json(right))

.check_real_mode_scope <- function(mode, boundary) {
  contracts <- c(
    fit_two_timepoint = "N13_TWO_TIMEPOINT",
    fit_repeated = "N13_REPEATED",
    fit_randomized_arm = "N13_RANDOMIZED_ARM",
    synthesize = "N13_SYNTHESIS"
  )
  operations <- c(
    fit_two_timepoint = "fit_two_timepoint",
    fit_repeated = "fit_repeated_windows",
    fit_randomized_arm = "fit_randomized_arm",
    synthesize = "synthesize_effects"
  )
  if (length(names(contracts)[contracts == boundary$release_scope]) != 1L ||
      !(mode %in% names(contracts)) ||
      !identical(unname(contracts[[mode]]), boundary$release_scope) ||
      !identical(unname(operations[[mode]]), boundary$operation)) {
    stop("Direct A-LONG R mode, N13 scope, and operation do not match")
  }
  if (!isTRUE(boundary$allow_outcomes)) {
    stop("Real A-LONG outcome execution requires explicit allow_outcomes=true")
  }
}

.check_executable_policy <- function(cfg, boundary, record) {
  payload <- boundary$policy_payload
  if (is.null(payload) || !identical(.canonical_sha256(payload), record$policy_sha256)) {
    stop("Direct A-LONG R policy payload does not match the approved policy hash")
  }
  if (identical(cfg$mode, "fit_two_timepoint")) {
    expected <- list(
      covariates = payload$covariates,
      confidence_level = payload$confidence_level,
      min_per_response_group = payload$min_per_response_group,
      sensitivity_modes = payload$sensitivity_modes,
      tighter_timing_max_deviation_days = payload$tighter_timing_max_deviation_days,
      method_ids = list(
        delta = payload$delta_method_id, ancova = payload$ancova_method_id,
        df = payload$df_method_id,
        same_lesion_sensitivity = payload$same_lesion_sensitivity_method_id,
        exact_day_sensitivity = payload$exact_day_sensitivity_method_id,
        tighter_timing_sensitivity = payload$tighter_timing_sensitivity_method_id
      )
    )
    if (!is.null(cfg$requested_models) && !.same_json(cfg$requested_models, list("ancova_sensitivity"))) {
      stop("Direct A-LONG R requested model set is not an admitted two-timepoint product")
    }
  } else if (identical(cfg$mode, "fit_repeated")) {
    expected <- list(
      window_levels = payload$repeated_windows,
      repeated_selection_mode = payload$repeated_selection_mode,
      min_repeated_patients = payload$min_repeated_patients,
      min_per_response_group = payload$min_per_response_group,
      covariates = payload$covariates,
      confidence_level = payload$confidence_level,
      method_ids = list(repeated = payload$repeated_method_id, df = payload$df_method_id)
    )
  } else if (identical(cfg$mode, "fit_randomized_arm")) {
    admission <- payload$randomization_admission
    if (is.null(admission)) stop("Direct A-LONG R randomized admission is absent from the approved policy")
    expected <- list(
      comparative_estimand_id = admission$comparative_estimand_id,
      randomization_verified = admission$randomization_verified,
      min_per_randomized_arm = payload$min_per_randomized_arm,
      covariates = payload$covariates,
      confidence_level = payload$confidence_level,
      method_ids = list(randomized_arm = payload$randomized_arm_method_id, df = payload$df_method_id)
    )
    if (!isTRUE(admission$randomization_verified) ||
        !identical(boundary$scope_bindings$comparative_estimand_id, admission$comparative_estimand_id) ||
        !identical(boundary$scope_bindings$randomization_receipt_sha256, admission$receipt_sha256)) {
      stop("Direct A-LONG R randomized admission does not match its scoped record")
    }
  } else {
    expected <- list(
      method_id = payload$meta_method_id,
      confidence_level = payload$confidence_level,
      minimum_k_for_pooling = payload$min_meta_k_pool
    )
  }
  if (identical(cfg$mode, "synthesize")) {
    if (!identical(cfg$method_id, expected$method_id) ||
        !isTRUE(all.equal(as.numeric(cfg$confidence_level), as.numeric(expected$confidence_level))) ||
        !identical(as.integer(cfg$minimum_k_for_pooling), as.integer(expected$minimum_k_for_pooling))) {
      stop("Direct A-LONG R synthesis settings differ from the approved policy")
    }
  } else {
    for (name in names(expected)) {
      if (!.same_json(cfg[[name]], expected[[name]])) {
        stop("Direct A-LONG R executable setting differs from the approved policy: ", name)
      }
    }
  }
}

.validate_boundary <- function(request) {
  cfg <- request$config
  boundary <- cfg$boundary
  if (is.null(boundary) || !boundary$data_classification %in% c("synthetic", "real")) {
    stop("A-LONG R boundary requires explicit source classification and provenance")
  }
  input_paths <- lapply(request$inputs, function(path) .guard_path(path, "model input"))
  output_path <- .guard_path(request$output_dir, "R output")
  retention_path <- if (!is.null(boundary$retention_dir)) .guard_path(boundary$retention_dir, "R retention") else NULL
  if (is.null(retention_path)) stop("A-LONG R execution requires an explicit retention directory")
  if (boundary$data_classification == "real") .check_real_mode_scope(mode, boundary)
  synthetic_mode_roles <- list(
    fit_two_timepoint = "design",
    fit_repeated = "design",
    fit_randomized_arm = "design",
    synthesize = c("effects", "overlap_receipts", "groups")
  )
  required_synthetic_roles <- synthetic_mode_roles[[mode]]
  if (boundary$data_classification == "synthetic") {
    input_names <- names(input_paths)
    request_roles <- setdiff(input_names, "provenance_manifest")
    if (is.null(required_synthetic_roles) || is.null(input_names) || anyDuplicated(input_names) ||
        length(request_roles) != length(required_synthetic_roles) ||
        !setequal(request_roles, required_synthetic_roles)) {
      stop("Synthetic A-LONG request input roles do not match mode")
    }
  }
  source_paths <- list()
  if (boundary$data_classification == "real") {
    if (is.null(boundary$source_paths) || !length(boundary$source_paths)) {
      stop("Real A-LONG R input requires named released source paths")
    }
    source_paths <- lapply(boundary$source_paths, function(path) .guard_path(path, "released clinical source"))
  }
  all_input_paths <- c(input_paths, source_paths)
  .overlaps <- function(left, right) {
    identical(left, right) || startsWith(left, paste0(right, "/")) || startsWith(right, paste0(left, "/"))
  }
  stage_parent <- dirname(dirname(output_path))
  staged_output <- identical(basename(output_path), "outputs") &&
    identical(stage_parent, retention_path) &&
    startsWith(basename(dirname(output_path)), ".") &&
    grepl(".stage-", basename(dirname(output_path)), fixed = TRUE)
  if (any(vapply(all_input_paths, function(path) .overlaps(path, output_path), logical(1))) ||
      (!is.null(retention_path) && any(vapply(all_input_paths, function(path) .overlaps(path, retention_path), logical(1)))) ||
      (!is.null(retention_path) && .overlaps(output_path, retention_path) && !staged_output)) {
    stop("A-LONG R input, output, and retention paths overlap")
  }
  if (dir.exists(output_path) && length(list.files(output_path, all.files = TRUE, no.. = TRUE))) {
    stop("A-LONG R output directory must be empty")
  }
  outcome_operations <- c(
    N13_FEATURE_JOIN = "pair_to_analysis",
    N13_TWO_TIMEPOINT = "fit_two_timepoint",
    N13_REPEATED = "fit_repeated_windows",
    N13_RANDOMIZED_ARM = "fit_randomized_arm",
    N13_SYNTHESIS = "synthesize_effects"
  )
  if (boundary$data_classification == "real" && boundary$release_scope %in% names(outcome_operations)) {
    if (is.null(boundary$operation) || !identical(boundary$operation, unname(outcome_operations[[boundary$release_scope]]))) {
      stop("Real A-LONG outcome scope and operation do not match")
    }
    manifest_path <- input_paths[["provenance_manifest"]]
    if (is.null(manifest_path) || !identical(.sha256(manifest_path), boundary$manifest_sha256)) {
      stop("A-LONG real source manifest hash mismatch")
    }
    manifest <- .json(manifest_path, "released source manifest")
    cohort_values <- unlist(manifest$cohort_ids, use.names = FALSE)
    cohort_tokens <- gsub("[^a-z0-9]", "", tolower(cohort_values))
    if (!identical(manifest$schema, "a_long_release_input_manifest_v1") ||
        !identical(manifest$data_classification, "PRIVATE_PATIENT_LEVEL") ||
        any(grepl("imvigor210", cohort_tokens, fixed = TRUE)) ||
        !identical(sort(cohort_values), sort(unlist(boundary$cohorts, use.names = FALSE)))) {
      stop("A-LONG real source manifest classification or cohort identity is invalid")
    }
    if (!isTRUE(boundary$allow_outcomes)) {
      stop("Real A-LONG outcome execution requires explicit allow_outcomes=true")
    }
  }
  if (boundary$data_classification == "real") {
    root <- normalizePath(file.path(getwd(), ".."), winslash = "/", mustWork = TRUE)
    relative <- substring(output_path, nchar(root) + 2L)
    retention_relative <- substring(retention_path, nchar(root) + 2L)
    if ((!startsWith(output_path, paste0(root, "/"))) ||
        (!startsWith(relative, "results/") && !startsWith(relative, ".scratch/")) ||
        (!startsWith(retention_path, paste0(root, "/"))) ||
        (!startsWith(retention_relative, "results/") && !startsWith(retention_relative, ".scratch/"))) {
      stop("A-LONG real R output must stay under results/ or .scratch/")
    }
  } else {
    root <- normalizePath(file.path(getwd(), ".."), winslash = "/", mustWork = TRUE)
    for (path in c(output_path, retention_path)) {
      if (startsWith(path, paste0(root, "/"))) {
        relative <- substring(path, nchar(root) + 2L)
        if (!startsWith(relative, "results/") && !startsWith(relative, ".scratch/")) {
          stop("A-LONG patient-level R outputs inside the project must stay under results/ or .scratch/")
        }
      }
    }
  }
  if (boundary$data_classification == "synthetic") {
    manifest_path <- input_paths[["provenance_manifest"]]
    if (is.null(manifest_path)) stop("Synthetic A-LONG R input requires its provenance manifest")
    if (!identical(.sha256(manifest_path), boundary$manifest_sha256)) stop("A-LONG synthetic manifest hash mismatch")
    manifest <- .json(manifest_path, "synthetic provenance manifest")
    if (!identical(manifest$producer, "tools.a_meta.synthetic_fixture") ||
        !identical(manifest$data_classification, "synthetic") ||
        !identical(manifest$kind, boundary$manifest_kind) ||
        !setequal(unlist(manifest$cohort_ids, use.names = FALSE), unlist(boundary$cohorts, use.names = FALSE))) {
      stop("A-LONG synthetic manifest identity does not match the requested model")
    }
    source_names <- unlist(boundary$source_inputs, use.names = FALSE)
    source_role_map_names_match <- function(value, roles) {
      is.list(value) && !is.null(names(value)) && !anyDuplicated(names(value)) &&
        length(value) == length(roles) && setequal(names(value), roles)
    }
    if (!length(source_names) || anyDuplicated(source_names) ||
        !setequal(source_names, required_synthetic_roles) ||
        !source_role_map_names_match(boundary$input_sha256, required_synthetic_roles) ||
        !source_role_map_names_match(manifest$source_sha256, required_synthetic_roles) ||
        !source_role_map_names_match(manifest$identity_fields, required_synthetic_roles) ||
        !source_role_map_names_match(boundary$identity_fields, required_synthetic_roles) ||
        !source_role_map_names_match(boundary$input_fields, required_synthetic_roles)) {
      stop("A-LONG synthetic manifest does not bind its named payload hashes and identities")
    }
    if (!.same_json(boundary$identity_fields, manifest$identity_fields)) {
      stop("A-LONG synthetic boundary identity fields differ from its manifest")
    }
    if (!identical(.canonical_sha256(list(
      cohorts = as.list(sort(unlist(manifest$cohort_ids, use.names = FALSE))),
      source_sha256 = manifest$source_sha256
    )), manifest$payload_sha256)) {
      stop("A-LONG synthetic manifest payload hash does not match its cohort and source hashes")
    }
    identity_roles <- lapply(required_synthetic_roles, function(source_name) {
      unlist(manifest$identity_fields[[source_name]], use.names = FALSE)
    })
    names(identity_roles) <- required_synthetic_roles
    if (mode %in% c("fit_two_timepoint", "fit_repeated", "fit_randomized_arm")) {
      if (!"study_id" %in% identity_roles$design) {
        stop("Synthetic A-LONG identity roles do not match mode")
      }
    } else if (!all(c("study") %in% identity_roles$effects) ||
               !all(c("study_a", "study_b") %in% identity_roles$overlap_receipts) ||
               !all(c("analysis_group_id") %in% identity_roles$groups)) {
      stop("Synthetic A-LONG identity roles do not match mode")
    }
    required_fields <- switch(
      mode,
      fit_two_timepoint = list(design = c("patient_key", "unit", "response", "pre_value", "on_value")),
      fit_repeated = list(design = c("patient_key", "unit", "response", "window", "value")),
      fit_randomized_arm = list(design = c("patient_key", "unit", "arm", "pre_value", "on_value")),
      synthesize = list(
        effects = c(
          "study", "analysis_group_id", "source_family_id", "overlap_receipt_id", "unit_family", "unit", "panel_family",
          "multiplicity_family_id", "feature_method_id", "analysis_method_id", "endpoint_id", "regimen_id",
          "window_id", "assay_id", "effect_scale_id", "estimate", "se", "ci_lb", "ci_ub",
          "p_value", "status", "reason"
        ),
        overlap_receipts = c(
          "study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256"
        ),
        groups = c("analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status")
      )
    )
    model_modes <- c("fit_two_timepoint", "fit_repeated", "fit_randomized_arm")
    if (mode %in% model_modes) {
      required_fields$design <- c(required_fields$design, unlist(cfg$covariates, use.names = FALSE))
      if (identical(mode, "fit_two_timepoint")) {
        sensitivities <- unlist(cfg$sensitivity_modes, use.names = FALSE)
        if ("same_lesion" %in% sensitivities) required_fields$design <- c(required_fields$design, "same_lesion")
        if ("exact_day" %in% sensitivities) {
          required_fields$design <- c(required_fields$design, "pre_day_precision", "on_day_precision", "pre_day_numeric", "on_day_numeric")
        }
        if ("tighter_timing" %in% sensitivities) {
          required_fields$design <- c(required_fields$design, "on_day_precision", "day_distance_to_target")
        }
      }
    }
    for (source_name in required_synthetic_roles) {
      declared_fields <- unlist(boundary$input_fields[[source_name]], use.names = FALSE)
      identity_fields <- identity_roles[[source_name]]
      if (!length(declared_fields) || anyNA(declared_fields) || any(!nzchar(trimws(declared_fields))) ||
          anyDuplicated(declared_fields) || any(!required_fields[[source_name]] %in% declared_fields) ||
          !length(identity_fields) || anyNA(identity_fields) || any(!nzchar(trimws(identity_fields))) ||
          anyDuplicated(identity_fields) || any(!identity_fields %in% declared_fields)) {
        stop("Synthetic A-LONG field map is incomplete for mode role: ", source_name)
      }
    }
    root <- normalizePath(file.path(getwd(), ".."), winslash = "/", mustWork = TRUE)
    registry <- utils::read.delim(file.path(root, "docs", "cohorts", "REGISTRY.tsv"), check.names = FALSE)
    known <- tolower(registry$cohort_id)
    cohorts <- tolower(unlist(boundary$cohorts, use.names = FALSE))
    if (any(grepl("imvigor210", gsub("[^a-z0-9]", "", cohorts))) || any(cohorts %in% known)) {
      stop("Synthetic A-LONG provenance cannot name a protected or registered real cohort")
    }
    for (source_name in source_names) {
      source_path <- input_paths[[source_name]]
      source_hash <- if (is.null(source_path)) "" else .sha256(source_path)
      if (is.null(source_path) || !identical(source_hash, boundary$input_sha256[[source_name]]) ||
          !identical(source_hash, manifest$source_sha256[[source_name]])) {
        stop("A-LONG synthetic source hash mismatch")
      }
      identity_fields <- unlist(manifest$identity_fields[[source_name]], use.names = FALSE)
      declared_fields <- unlist(boundary$input_fields[[source_name]], use.names = FALSE)
      if (!length(identity_fields) || any(!nzchar(identity_fields)) || anyDuplicated(identity_fields) ||
          !all(identity_fields %in% declared_fields)) {
        stop("A-LONG synthetic identity allowlist is incomplete")
      }
      identity_rows <- .read_authorized_table(source_path, identity_fields)
      identity_names <- intersect(c("study_id", "study", "study_a", "study_b"), names(identity_rows))
      if (any(vapply(identity_rows[identity_fields], function(column) {
        any(is.na(column) | !nzchar(trimws(as.character(column))))
      }, logical(1)))) {
        stop("A-LONG synthetic payload identity fields are missing")
      }
      if (length(identity_names)) {
        actual_studies <- unique(unlist(lapply(identity_rows[identity_names], as.character), use.names = FALSE))
        actual_tokens <- gsub("[^a-z0-9]", "", tolower(actual_studies))
        if (any(grepl("imvigor210", actual_tokens, fixed = TRUE)) ||
            !all(actual_studies %in% unlist(boundary$cohorts, use.names = FALSE)) ||
            any(tolower(actual_studies) %in% known)) {
          stop("A-LONG synthetic payload identity is protected, registered, or outside its manifest")
        }
      } else if (!identical(source_name, "groups")) {
        stop("A-LONG synthetic payload lacks a named study identity field")
      }
    }
  } else {
    .validate_real_boundary(request, boundary, input_paths)
  }
  invisible(list(inputs = input_paths, output = output_path, boundary = boundary))
}

.validate_real_boundary <- function(request, boundary, input_paths) {
  if (is.null(boundary$release_record_path) || is.null(boundary$release_scope) || is.null(boundary$operation)) {
    stop("Real A-LONG R input requires a scoped user-release record before payload access")
  }
  if (boundary$release_scope %in% c(
    "N13_FEATURE_JOIN", "N13_TWO_TIMEPOINT", "N13_REPEATED",
    "N13_RANDOMIZED_ARM", "N13_SYNTHESIS"
  ) && !isTRUE(boundary$allow_outcomes)) {
    stop("Real A-LONG outcome execution requires explicit allow_outcomes=true")
  }
  record_path <- .guard_path(boundary$release_record_path, "user-release record")
  if (!identical(.sha256(record_path), boundary$release_record_sha256)) {
    stop("A-LONG R user-release record hash differs from the validated record")
  }
  source_paths <- lapply(boundary$source_paths, function(path) .guard_path(path, "released clinical source"))
  release_root <- .guard_path(boundary$release_root, "release decision root")
  decision_root <- .guard_path(boundary$decisions_dir, "release decisions directory")
  project_root <- normalizePath(file.path(getwd(), ".."), winslash = "/", mustWork = TRUE)
  expected_decisions <- normalizePath(file.path(project_root, "docs", "decisions"), winslash = "/", mustWork = TRUE)
  if (!identical(normalizePath(release_root, winslash = "/", mustWork = TRUE), project_root) ||
      !identical(normalizePath(decision_root, winslash = "/", mustWork = TRUE), expected_decisions)) {
    stop("A-LONG R user-release records must resolve inside this project docs/decisions directory")
  }
  record <- .json(record_path, "user-release record")
  if (!identical(record$record_type, "a_long_user_release_v1") ||
      !identical(record$record_status, "APPROVED") ||
      !identical(record$data_classification, "PRIVATE_PATIENT_LEVEL") ||
      !identical(record$release_scope, boundary$release_scope) ||
      !identical(record$operation, boundary$operation)) {
    stop("A-LONG R user-release record is not approved for this operation and scope")
  }
  if (!identical(boundary$policy_sha256, record$policy_sha256)) {
    stop("A-LONG R boundary policy hash differs from the approved record")
  }
  .check_executable_policy(request$config, boundary, record)
  decision <- record$decision
  if (!identical(sort(names(decision)), c("identity", "path", "sha256")) ||
      !startsWith(decision$path, "docs/decisions/")) stop("A-LONG R release decision reference is incomplete")
  decision_path <- .guard_path(file.path(release_root, decision$path), "decision record")
  decision_root <- normalizePath(decision_root, winslash = "/", mustWork = TRUE)
  if (!startsWith(decision_path, paste0(decision_root, "/")) ||
      tools::file_path_sans_ext(basename(decision_path)) != decision$identity ||
      !identical(.sha256(decision_path), decision$sha256)) stop("A-LONG R decision identity or hash mismatch")
  scope_operations <- c(
    N12_PAIRING = "pair",
    N12_GIDE_CROSSWALK = "accept_gide_crosswalk",
    N13_FEATURE_JOIN = "pair_to_analysis",
    N13_TWO_TIMEPOINT = "fit_two_timepoint",
    N13_REPEATED = "fit_repeated_windows",
    N13_RANDOMIZED_ARM = "fit_randomized_arm",
    N13_SYNTHESIS = "synthesize_effects"
  )
  if (!identical(unname(scope_operations[[boundary$release_scope]]), boundary$operation)) {
    stop("A-LONG R release scope is not bound to the requested operation")
  }
  scope_bindings <- list(
    N12_PAIRING = c("source_column_map_sha256", "window_policy_sha256"),
    N12_GIDE_CROSSWALK = c("crosswalk_sha256", "crosswalk_source_manifest_sha256"),
    N13_FEATURE_JOIN = c("feature_membership_sha256", "pair_manifest_sha256", "representation_sha256"),
    N13_TWO_TIMEPOINT = c("ancova_method_id", "covariate_contract_sha256", "delta_method_id"),
    N13_REPEATED = c("repeated_method_id", "selection_mode", "window_set_sha256"),
    N13_RANDOMIZED_ARM = c("comparative_estimand_id", "randomization_receipt_sha256", "randomized_method_id"),
    N13_SYNTHESIS = c("meta_method_id", "multiplicity_contract_sha256", "source_overlap_contract_sha256")
  )
  expected_bindings <- scope_bindings[[boundary$release_scope]]
  if (is.null(expected_bindings) || !identical(sort(names(boundary$scope_bindings)), sort(expected_bindings))) {
    stop("A-LONG R scope-specific release bindings are incomplete")
  }
  binding_hashes <- list(
    N12_PAIRING = c("source_column_map_sha256", "window_policy_sha256"),
    N12_GIDE_CROSSWALK = c("crosswalk_sha256", "crosswalk_source_manifest_sha256"),
    N13_FEATURE_JOIN = c("feature_membership_sha256", "pair_manifest_sha256", "representation_sha256"),
    N13_TWO_TIMEPOINT = "covariate_contract_sha256",
    N13_REPEATED = "window_set_sha256",
    N13_RANDOMIZED_ARM = "randomization_receipt_sha256",
    N13_SYNTHESIS = c("multiplicity_contract_sha256", "source_overlap_contract_sha256")
  )
  if (any(!vapply(binding_hashes[[boundary$release_scope]], function(name) {
    is.character(boundary$scope_bindings[[name]]) && grepl("^[0-9a-f]{64}$", boundary$scope_bindings[[name]])
  }, logical(1)))) {
    stop("A-LONG R scope-specific release hashes are malformed")
  }
  required_record_names <- c(
    "record_type", "record_status", "data_classification", "release_scope", "decision",
    "operation", "policy_sha256", "input_manifest_sha256", "source_sha256", "cohorts", "permitted_fields",
    names(boundary$scope_bindings)
  )
  if (is.null(boundary$scope_bindings) ||
      !identical(sort(names(record)), sort(unique(required_record_names))) ||
      !identical(boundary$manifest_kind, "a_long_release_input_manifest_v1")) {
    stop("A-LONG R user-release record has missing or contradictory scope fields")
  }
  manifest_path <- input_paths[["provenance_manifest"]]
  if (is.null(manifest_path) || !identical(.sha256(manifest_path), boundary$manifest_sha256)) {
    stop("A-LONG real source manifest hash mismatch")
  }
  manifest <- .json(manifest_path, "released source manifest")
  cohort_tokens <- gsub("[^a-z0-9]", "", tolower(unlist(manifest$cohort_ids, use.names = FALSE)))
  if (!identical(manifest$schema, "a_long_release_input_manifest_v1") ||
      !identical(manifest$data_classification, "PRIVATE_PATIENT_LEVEL") ||
      any(grepl("imvigor210", cohort_tokens, fixed = TRUE)) ||
      !identical(sort(unlist(manifest$cohort_ids, use.names = FALSE)), sort(unlist(boundary$cohorts, use.names = FALSE))) ||
      !identical(sort(names(manifest$source_files)), sort(names(source_paths))) ||
      !identical(manifest$identity_fields, boundary$source_identity_fields) ||
      !identical(manifest$field_maps, boundary$source_field_maps) ||
      !identical(sort(unlist(manifest$permitted_fields, use.names = FALSE)), sort(unlist(boundary$permitted_fields, use.names = FALSE))) ||
      !identical(manifest$scope_bindings, boundary$scope_bindings)) {
    stop("A-LONG real source manifest classification, identity, or field bindings are invalid")
  }
  source_roles <- list(
    N12_PAIRING = "specimens",
    N13_FEATURE_JOIN = c("pairs", "expression", "endpoint"),
    N13_TWO_TIMEPOINT = "design",
    N13_REPEATED = "design",
    N13_RANDOMIZED_ARM = "design",
    N13_SYNTHESIS = c("effects", "overlap_receipts")
  )
  if (!identical(sort(names(source_paths)), sort(source_roles[[boundary$release_scope]]))) {
    stop("A-LONG R released sources do not match the operation-specific source roles")
  }
  manifest_paths <- lapply(manifest$source_files, function(path) {
    candidate <- if (grepl("^/", path)) path else file.path(dirname(manifest_path), path)
    .guard_path(candidate, "manifest-declared clinical source")
  })
  if (!identical(sort(unlist(manifest_paths, use.names = TRUE)), sort(unlist(source_paths, use.names = TRUE)))) {
    stop("A-LONG released source paths differ from the hashed manifest")
  }
  if (!identical(record$policy_sha256, boundary$policy_sha256) ||
      !identical(record$input_manifest_sha256, boundary$manifest_sha256) ||
      !identical(sort(unlist(record$cohorts, use.names = FALSE)), sort(unlist(boundary$cohorts, use.names = FALSE))) ||
      !identical(sort(unlist(record$permitted_fields, use.names = FALSE)), sort(unlist(boundary$permitted_fields, use.names = FALSE))) ||
      !identical(record$source_sha256, boundary$source_sha256) ||
      any(!vapply(names(boundary$scope_bindings), function(name) identical(record[[name]], boundary$scope_bindings[[name]]), logical(1)))) {
    stop("A-LONG R release record does not bind the policy, manifest, cohort, and named fields")
  }
  expected_sources <- record$source_sha256
  source_names <- unlist(boundary$source_inputs, use.names = FALSE)
  if (!setequal(source_names, names(expected_sources))) stop("A-LONG real source names do not match the user record")
  for (source_name in source_names) {
    mapping <- boundary$source_field_maps[[source_name]]
    identity_fields <- unlist(boundary$source_identity_fields[[source_name]], use.names = FALSE)
    if (is.null(mapping) || !is.list(mapping) || is.null(names(mapping)) ||
        anyDuplicated(names(mapping)) || anyDuplicated(unlist(mapping, use.names = FALSE)) ||
        any(!nzchar(names(mapping))) || any(!nzchar(unlist(mapping, use.names = FALSE))) ||
        !length(identity_fields) || anyDuplicated(identity_fields) ||
        any(!paste0(source_name, ":", unlist(mapping, use.names = FALSE)) %in% boundary$permitted_fields) ||
        any(!paste0(source_name, ":", identity_fields) %in% boundary$permitted_fields)) {
      stop("A-LONG released field maps or identity columns exceed the approved named-field record")
    }
  }
  input_names <- setdiff(names(input_paths), "provenance_manifest")
  if (!setequal(input_names, names(boundary$input_sha256))) {
    stop("A-LONG R derived input names do not match their authorized hashes")
  }
  for (input_name in input_names) {
    if (!identical(.sha256(input_paths[[input_name]]), boundary$input_sha256[[input_name]])) {
      stop("A-LONG R derived input hash differs from its authorized release receipt")
    }
  }
  for (source_name in source_names) {
    source_path <- source_paths[[source_name]]
    if (is.null(source_path) || !identical(.sha256(source_path), expected_sources[[source_name]])) {
      stop("A-LONG real source hash is not authorized")
    }
  }
  for (source_name in source_names) {
    source_path <- source_paths[[source_name]]
    fields <- unlist(boundary$source_identity_fields[[source_name]], use.names = FALSE)
    identity <- .read_authorized_table(source_path, fields)
    mapped <- boundary$source_field_maps[[source_name]]
    study_field <- mapped$study_id
    if (is.null(study_field)) study_field <- mapped$study
    patient_field <- mapped$patient_id
    if (is.null(patient_field)) patient_field <- mapped$patient_key
    if (is.null(patient_field)) patient_field <- mapped$subject_id
    if (identical(boundary$release_scope, "N13_FEATURE_JOIN") && identical(source_name, "expression")) {
      patient_field <- mapped$sample_id
    }
    if (identical(boundary$release_scope, "N13_SYNTHESIS") && identical(source_name, "effects")) {
      patient_field <- mapped$source_family_id
    }
    if (identical(boundary$release_scope, "N13_SYNTHESIS") && identical(source_name, "overlap_receipts")) {
      study_fields <- unlist(mapped[c("study_a", "study_b")], use.names = FALSE)
      family_fields <- unlist(mapped[c("source_family_a", "source_family_b")], use.names = FALSE)
      if (length(study_fields) != 2L || length(family_fields) != 2L ||
          any(!study_fields %in% names(identity)) || any(!family_fields %in% names(identity)) ||
          any(!unlist(identity[study_fields], use.names = FALSE) %in% unlist(boundary$cohorts, use.names = FALSE)) ||
          any(!nzchar(as.character(unlist(identity[c(study_fields, family_fields)], use.names = FALSE))))) {
        stop("A-LONG synthesis overlap identities do not match the authorized cohorts")
      }
      next
    }
    if (is.null(study_field) || is.null(patient_field) ||
        !study_field %in% names(identity) || !patient_field %in% names(identity) ||
        any(!identity[[study_field]] %in% unlist(boundary$cohorts, use.names = FALSE)) ||
        any(!nzchar(as.character(identity[[patient_field]])))) {
      stop("A-LONG released clinical identity fields do not match the authorized cohort")
    }
  }
  if (boundary$release_scope %in% c("N13_TWO_TIMEPOINT", "N13_REPEATED", "N13_RANDOMIZED_ARM")) {
    .bind_released_model_input(request, boundary, manifest, source_paths, input_paths)
  } else if (identical(boundary$release_scope, "N13_SYNTHESIS")) {
    .bind_released_synthesis_inputs(request, boundary, manifest, source_paths, input_paths)
  }
  invisible(TRUE)
}

.read_authorized_table <- function(path, fields) {
  guarded <- .guard_path(path, "authorized model table")
  fields <- unlist(fields, use.names = FALSE)
  if (!length(fields) || any(!nzchar(fields)) || anyDuplicated(fields)) stop("A-LONG named-field allowlist is malformed")
  header <- names(utils::read.delim(guarded, check.names = FALSE, nrows = 0L, stringsAsFactors = FALSE))
  if (anyDuplicated(header) || !all(fields %in% header)) stop("A-LONG input is missing an authorized named field")
  keep <- header %in% fields
  classes <- ifelse(keep, NA, "NULL")
  names(classes) <- header
  utils::read.delim(
    guarded, check.names = FALSE, stringsAsFactors = FALSE,
    na.strings = c("", "NA"), colClasses = classes
  )
}

.bound_source_rows <- function(boundary, manifest, source_paths, source_name, canonical_fields) {
  mapping <- boundary$source_field_maps[[source_name]]
  permitted <- unlist(boundary$permitted_fields, use.names = FALSE)
  if (is.null(mapping) || !is.list(mapping) || anyDuplicated(names(mapping)) ||
      any(!nzchar(names(mapping))) || any(!nzchar(unlist(mapping, use.names = FALSE)))) {
    stop("A-LONG released source field map is incomplete")
  }
  if (!all(canonical_fields %in% names(mapping))) {
    stop("A-LONG released source does not map every derived model field")
  }
  raw_fields <- unlist(mapping[canonical_fields], use.names = FALSE)
  if (anyDuplicated(raw_fields) || any(!paste0(source_name, ":", raw_fields) %in% permitted)) {
    stop("A-LONG derived input requests fields outside its released named-field allowlist")
  }
  source_path <- source_paths[[source_name]]
  if (is.null(source_path)) stop("A-LONG released source path is missing")
  raw <- .read_authorized_table(source_path, raw_fields)
  output <- as.data.frame(
    setNames(lapply(canonical_fields, function(field) raw[[mapping[[field]]]]), canonical_fields),
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
  output
}

.model_input_fields <- function(cfg) {
  identity_fields <- c(
    "unit_family", "feature_method_id", "analysis_method_id", "endpoint_id", "regimen_id",
    "window_id", "assay_id", "effect_scale_id", "panel_family", "multiplicity_family_id",
    "source_family_id", "overlap_receipt_id", "overlap_status"
  )
  timing_fields <- c(
    "same_lesion", "pre_day_precision", "on_day_precision", "timing_ambiguity",
    "pre_day_numeric", "on_day_numeric", "day_distance_to_target", "pair_day_distance"
  )
  base <- c("study_id", "patient_key", "pair_id", "unit", identity_fields, timing_fields)
  if (identical(cfg$mode, "fit_two_timepoint")) {
    return(c(base, "pre_value", "on_value", "response", unlist(cfg$covariates, use.names = FALSE)))
  }
  if (identical(cfg$mode, "fit_repeated")) {
    return(c(base, "window", "value", "response", unlist(cfg$covariates, use.names = FALSE)))
  }
  if (identical(cfg$mode, "fit_randomized_arm")) {
    return(c(base, "pre_value", "on_value", "arm", unlist(cfg$covariates, use.names = FALSE)))
  }
  stop("A-LONG released model input mode is unsupported")
}

.opaque_key <- function(study, patient) {
  raw <- c(charToRaw(enc2utf8(study)), as.raw(0L), charToRaw(enc2utf8(patient)))
  substr(digest::digest(raw, algo = "sha256", serialize = FALSE), 1L, 24L)
}

.joined_key <- function(frame, fields) {
  if (!nrow(frame)) return(character())
  do.call(paste, c(lapply(frame[fields], as.character), list(sep = "\034")))
}

.same_bound_cells <- function(expected, observed, field, numeric_fields) {
  if (field %in% numeric_fields) {
    left <- suppressWarnings(as.numeric(as.character(expected)))
    right <- suppressWarnings(as.numeric(as.character(observed)))
    same_missing <- is.na(left) & is.na(right)
    same_value <- !is.na(left) & !is.na(right) & is.finite(left) & is.finite(right) & left == right
    return(all(same_missing | same_value))
  }
  left <- as.character(expected)
  right <- as.character(observed)
  left_missing <- is.na(left) | left == ""
  right_missing <- is.na(right) | right == ""
  all((left_missing & right_missing) | (!left_missing & !right_missing & left == right))
}

.bind_released_model_input <- function(request, boundary, manifest, source_paths, input_paths) {
  input_fields <- unlist(boundary$input_fields$design, use.names = FALSE)
  expected_fields <- .model_input_fields(request$config)
  if (anyDuplicated(input_fields) || !setequal(input_fields, expected_fields)) {
    stop("A-LONG released model input columns do not match the explicit operation schema")
  }
  mapping <- boundary$source_field_maps$design
  generated_defaults <- c(
    "same_lesion", "pre_day_precision", "on_day_precision", "timing_ambiguity",
    "pre_day_numeric", "on_day_numeric", "day_distance_to_target", "pair_day_distance"
  )
  source_fields <- setdiff(input_fields, "patient_key")
  missing_maps <- setdiff(source_fields, names(mapping))
  if (any(!missing_maps %in% generated_defaults)) {
    stop("A-LONG released model input contains a value without an authorized source-column mapping")
  }
  mapped_fields <- intersect(source_fields, names(mapping))
  source <- .bound_source_rows(boundary, manifest, source_paths, "design", c(mapped_fields, "patient_key"))
  source$patient_key <- mapply(.opaque_key, source$study_id, source$patient_key, USE.NAMES = FALSE)
  for (field in missing_maps) source[[field]] <- rep(NA_character_, nrow(source))
  derived <- .read_authorized_table(input_paths[["design"]], input_fields)
  key_fields <- c("study_id", "patient_key", "pair_id", "unit")
  if (identical(request$config$mode, "fit_repeated")) key_fields <- c(key_fields, "window")
  source_keys <- .joined_key(source, key_fields)
  derived_keys <- .joined_key(derived, key_fields)
  if (nrow(source) != nrow(derived) || anyDuplicated(source_keys) || anyDuplicated(derived_keys) ||
      !setequal(source_keys, derived_keys)) {
    stop("A-LONG derived model rows do not match the authorized source row identities")
  }
  source <- source[match(derived_keys, source_keys), , drop = FALSE]
  numeric_fields <- c(
    "pre_value", "on_value", "value", "pre_day_numeric", "on_day_numeric",
    "day_distance_to_target", "pair_day_distance"
  )
  if (any(vapply(input_fields, function(field) {
    !.same_bound_cells(source[[field]], derived[[field]], field, numeric_fields)
  }, logical(1)))) {
    stop("A-LONG derived model values do not match the authorized source contents")
  }
  identity_fields <- setdiff(expected_fields, c(
    "study_id", "patient_key", "pair_id", "unit", "response", "arm", "window", "value",
    "pre_value", "on_value", "same_lesion", "pre_day_precision", "on_day_precision",
    "timing_ambiguity", "pre_day_numeric", "on_day_numeric", "day_distance_to_target",
    "pair_day_distance", unlist(request$config$covariates, use.names = FALSE)
  ))
  identities <- request$config$identities
  units <- sort(unique(as.character(derived$unit)))
  if (!identical(sort(names(identities)), units)) stop("A-LONG model output identities do not match derived feature units")
  for (unit in units) {
    rows <- derived[derived$unit == unit, , drop = FALSE]
    identity <- identities[[unit]]
    if (length(unique(rows$study_id)) != 1L ||
        !identical(as.character(identity$study), as.character(rows$study_id[[1L]])) ||
        !identical(as.character(identity$patient_set_id), .canonical_sha256(unname(as.list(sort(unique(as.character(rows$patient_key)))))))) {
      stop("A-LONG derived model study or patient-set receipt is invalid for feature unit ", unit)
    }
    for (field in identity_fields) {
      values <- unique(as.character(rows[[field]]))
      if (length(values) != 1L || !identical(as.character(identity[[field]]), values[[1L]])) {
        stop("A-LONG model output identity differs from its authorized source values: ", field)
      }
    }
  }
}

.synthesis_family_fields <- c(
  "unit_family", "unit", "panel_family", "multiplicity_family_id", "feature_method_id",
  "analysis_method_id", "endpoint_id", "regimen_id", "window_id", "assay_id", "effect_scale_id"
)

.expected_synthesis_groups <- function(effects, overlap_receipts) {
  groups <- list()
  for (group in sort(unique(as.character(effects$analysis_group_id)))) {
    rows <- effects[effects$analysis_group_id == group, , drop = FALSE]
    reason <- ""
    if (anyDuplicated(as.character(rows$patient_set_id))) {
      reason <- "duplicate_patient_set_identity"
    } else if (!identical(sort(unique(as.character(rows$overlap_status))), "DISJOINT_VERIFIED")) {
      reason <- "source_independence_unresolved_or_overlapping"
    } else if (nrow(rows) > 1L) {
      for (left_index in seq_len(nrow(rows) - 1L)) {
        for (right_index in seq.int(left_index + 1L, nrow(rows))) {
          left <- rows[left_index, , drop = FALSE]
          right <- rows[right_index, , drop = FALSE]
          receipt <- overlap_receipts[
            (overlap_receipts$study_a == left$study & overlap_receipts$study_b == right$study) |
              (overlap_receipts$study_a == right$study & overlap_receipts$study_b == left$study),
            , drop = FALSE
          ]
          if (nrow(receipt) != 1L || !identical(as.character(receipt$overlap_status[[1L]]), "DISJOINT_VERIFIED")) {
            reason <- "source_independence_unresolved_or_overlapping"
          } else {
            expected_families <- c(as.character(left$source_family_id[[1L]]), as.character(right$source_family_id[[1L]]))
            observed_families <- if (identical(as.character(receipt$study_a[[1L]]), as.character(left$study[[1L]]))) {
              c(as.character(receipt$source_family_a[[1L]]), as.character(receipt$source_family_b[[1L]]))
            } else c(as.character(receipt$source_family_b[[1L]]), as.character(receipt$source_family_a[[1L]]))
            if (!identical(observed_families, expected_families)) reason <- "source_independence_unresolved_or_overlapping"
          }
        }
      }
    }
    eligible <- if (nzchar(reason)) 0L else sum(as.character(rows$status) == "ESTIMABLE")
    groups[[length(groups) + 1L]] <- data.frame(
      analysis_group_id = group,
      preflight_reason = reason,
      k = eligible,
      n_input = nrow(rows),
      n_excluded = nrow(rows) - eligible,
      independence_status = if (nzchar(reason)) "NOT_RESOLVED" else if (nrow(rows) == 1L) "SINGLE_STUDY_NO_CROSS_STUDY_CHECK" else "DISJOINT_VERIFIED",
      stringsAsFactors = FALSE
    )
  }
  if (!length(groups)) return(data.frame())
  do.call(rbind, groups)
}

.bind_released_synthesis_inputs <- function(request, boundary, manifest, source_paths, input_paths) {
  effect_fields <- unlist(boundary$input_fields$effects, use.names = FALSE)
  overlap_fields <- unlist(boundary$input_fields$overlap_receipts, use.names = FALSE)
  required_effects <- c(
    "study", "patient_set_id", "source_family_id", "overlap_receipt_id", "overlap_status",
    "unit_family", "unit", "panel_family", "multiplicity_family_id", "feature_method_id",
    "analysis_method_id", "endpoint_id", "regimen_id", "window_id", "assay_id", "effect_scale_id",
    "estimate", "se", "ci_lb", "ci_ub", "p_value", "status", "reason"
  )
  required_overlap <- c("study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256")
  if (anyDuplicated(effect_fields) || anyDuplicated(overlap_fields) ||
      !setequal(effect_fields, c(required_effects, "analysis_group_id")) ||
      !setequal(overlap_fields, required_overlap)) {
    stop("A-LONG released synthesis input columns do not match the explicit operation schema")
  }
  source_effects <- .bound_source_rows(boundary, manifest, source_paths, "effects", required_effects)
  source_overlap <- .bound_source_rows(boundary, manifest, source_paths, "overlap_receipts", required_overlap)
  derived_effects <- .read_authorized_table(input_paths[["effects"]], effect_fields)
  derived_overlap <- .read_authorized_table(input_paths[["overlap_receipts"]], overlap_fields)
  source_keys <- .joined_key(source_effects, c("study", .synthesis_family_fields))
  derived_keys <- .joined_key(derived_effects, c("study", .synthesis_family_fields))
  if (nrow(source_effects) != nrow(derived_effects) || anyDuplicated(source_keys) ||
      anyDuplicated(derived_keys) || !setequal(source_keys, derived_keys)) {
    stop("A-LONG released synthesis effects do not preserve their source family identities")
  }
  source_effects <- source_effects[match(derived_keys, source_keys), , drop = FALSE]
  for (index in seq_len(nrow(source_effects))) {
    key <- as.list(source_effects[index, .synthesis_family_fields, drop = FALSE])
    expected_group <- substr(.canonical_sha256(unname(lapply(key, as.character))), 1L, 24L)
    if (is.na(derived_effects$analysis_group_id[[index]]) ||
        !identical(as.character(derived_effects$analysis_group_id[[index]]), expected_group)) {
      stop("A-LONG synthesis family ID is not derived from the authorized effect identity")
    }
  }
  numeric_fields <- c("estimate", "se", "ci_lb", "ci_ub", "p_value")
  if (nrow(source_effects) != nrow(derived_effects) ||
      any(vapply(required_effects, function(field) {
        !.same_bound_cells(source_effects[[field]], derived_effects[[field]], field, numeric_fields)
      }, logical(1)))) {
    stop("A-LONG derived synthesis effects differ from the authorized source contents")
  }
  if (nrow(source_overlap) != nrow(derived_overlap) || any(vapply(required_overlap, function(field) {
    !.same_bound_cells(source_overlap[[field]], derived_overlap[[field]], field, character())
  }, logical(1)))) {
    stop("A-LONG derived source-overlap receipts differ from the authorized source contents")
  }
  derived_groups <- .read_authorized_table(input_paths[["groups"]], unlist(boundary$input_fields$groups, use.names = FALSE))
  expected_groups <- .expected_synthesis_groups(derived_effects, derived_overlap)
  group_fields <- c("analysis_group_id", "preflight_reason", "k", "n_input", "n_excluded", "independence_status")
  if (!setequal(names(derived_groups), group_fields) || nrow(derived_groups) != nrow(expected_groups)) {
    stop("A-LONG synthesis support groups do not match the authorized effects")
  }
  derived_groups <- derived_groups[match(expected_groups$analysis_group_id, derived_groups$analysis_group_id), , drop = FALSE]
  for (field in group_fields) {
    if (!.same_bound_cells(expected_groups[[field]], derived_groups[[field]], field, c("k", "n_input", "n_excluded"))) {
      stop("A-LONG synthesis support group differs from its authorized effect and overlap receipts: ", field)
    }
  }
}

.boundary <- .validate_boundary(request)

.write_output <- function(name, value) {
  utils::write.table(
    value,
    file.path(output_dir, name),
    sep = "\t",
    row.names = FALSE,
    col.names = TRUE,
    quote = FALSE,
    na = "NA",
    fileEncoding = "UTF-8"
  )
}

.number <- function(value) {
  if (length(value) != 1L || is.na(value) || !is.finite(value)) NA_real_ else as.numeric(value)
}

.numerically_positive_uncertainty <- function(se, values, observations) {
  if (length(se) != 1L || !is.finite(se) || se <= 0 || !length(values)) return(FALSE)
  finite_values <- values[is.finite(values)]
  if (!length(finite_values)) return(FALSE)
  value_scale <- max(abs(finite_values))
  rounding_bound <- .Machine$double.eps * value_scale * max(1L, as.integer(observations))
  se > rounding_bound
}

.identities <- function(unit) {
  value <- cfg$identities[[unit]]
  if (is.null(value)) stop("Missing explicit feature identity for unit ", unit)
  as.list(value)
}

.effect_row <- function(unit, model, contrast, effect_role, method_id, estimate = NA_real_,
                        se = NA_real_, ci_lb = NA_real_, ci_ub = NA_real_, df = NA_real_,
                        rank = NA_integer_, n = 0L, n_R = 0L, n_NR = 0L, p_value = NA_real_,
                        n_observations_fitted = n, n_observations_contrast = n,
                        n_arm_ici = 0L, n_arm_combination = 0L,
                        status = "NOT_ESTIMABLE", reason = "") {
  identity <- .identities(unit)
  identity$analysis_method_id <- method_id
  data.frame(
    unit = unit,
    as.data.frame(identity, stringsAsFactors = FALSE, check.names = FALSE),
    model = model,
    contrast = contrast,
    effect_role = effect_role,
    estimate = .number(estimate),
    se = .number(se),
    ci_lb = .number(ci_lb),
    ci_ub = .number(ci_ub),
    df = .number(df),
    rank = as.integer(rank),
    n = as.integer(n),
    n_R = as.integer(n_R),
    n_NR = as.integer(n_NR),
    n_observations_fitted = as.integer(n_observations_fitted),
    n_observations_contrast = as.integer(n_observations_contrast),
    n_arm_ici = as.integer(n_arm_ici),
    n_arm_combination = as.integer(n_arm_combination),
    p_value = .number(p_value),
    status = status,
    reason = reason,
    analysis_family = cfg$analysis_family,
    policy_status = cfg$policy_status,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
}

.empty_effects <- function() {
  data.frame(
    unit = character(), unit_family = character(), feature_method_id = character(),
    analysis_method_id = character(), endpoint_id = character(), regimen_id = character(),
    window_id = character(), assay_id = character(), effect_scale_id = character(),
    panel_family = character(), multiplicity_family_id = character(), source_family_id = character(),
    overlap_receipt_id = character(), overlap_status = character(), study = character(), patient_set_id = character(),
    model = character(), contrast = character(), effect_role = character(),
    estimate = numeric(), se = numeric(), ci_lb = numeric(), ci_ub = numeric(),
    df = numeric(), rank = integer(), n = integer(), n_R = integer(), n_NR = integer(),
    n_observations_fitted = integer(), n_observations_contrast = integer(),
    n_arm_ici = integer(), n_arm_combination = integer(),
    p_value = numeric(), status = character(), reason = character(),
    analysis_family = character(), policy_status = character(),
    stringsAsFactors = FALSE, check.names = FALSE
  )
}

.empty_within <- function() {
  data.frame(
    unit = character(), window = character(), response = character(), arm = character(),
    n = integer(), estimate = numeric(), se = numeric(), ci_lb = numeric(), ci_ub = numeric(),
    df = numeric(), effect_role = character(), status = character(), reason = character(),
    policy_status = character(),
    stringsAsFactors = FALSE, check.names = FALSE
  )
}

.empty_support <- function() {
  data.frame(
    unit = character(), n_input = integer(), n_complete = integer(),
    n_patients_input = integer(), n_patients_used = integer(), n_observations_used = integer(),
    n_missing_endpoint = integer(), n_missing_expression = integer(),
    n_R = integer(), n_NR = integer(), rank = integer(),
    n_arm_ici = integer(), n_arm_combination = integer(),
    residual_df = numeric(), status = character(), reason = character(),
    policy_status = character(),
    stringsAsFactors = FALSE, check.names = FALSE
  )
}

.fit_ols <- function(frame, outcome, predictors, response_counts, model_name,
                     contrast, effect_role, method_id) {
  frame <- frame[stats::complete.cases(frame[, c(outcome, predictors), drop = FALSE]), , drop = FALSE]
  frame$response <- factor(frame$response, levels = c("NR", "R"))
  n_R <- sum(frame$response == "R")
  n_NR <- sum(frame$response == "NR")
  x <- tryCatch(
    stats::model.matrix(stats::reformulate(predictors, response = outcome), data = frame),
    error = function(error) error
  )
  if (inherits(x, "error")) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      n = nrow(frame), n_R = n_R, n_NR = n_NR,
      status = "NOT_ESTIMABLE", reason = "model_matrix_error"
    ), rank = NA_integer_, residual_df = NA_real_))
  }
  rank <- qr(x)$rank
  residual_df <- nrow(x) - rank
  if (rank < ncol(x)) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      rank = rank, n = nrow(frame), n_R = n_R, n_NR = n_NR,
      status = "NOT_ESTIMABLE", reason = "rank_deficient_design"
    ), rank = rank, residual_df = residual_df))
  }
  if (residual_df <= 0L) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      rank = rank, n = nrow(frame), n_R = n_R, n_NR = n_NR,
      status = "NOT_ESTIMABLE", reason = "no_residual_df"
    ), rank = rank, residual_df = residual_df))
  }
  fit <- tryCatch(stats::lm(stats::reformulate(predictors, response = outcome), data = frame), error = function(error) error)
  if (inherits(fit, "error")) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      rank = rank, n = nrow(frame), n_R = n_R, n_NR = n_NR,
      status = "NOT_ESTIMABLE", reason = "model_fit_error"
    ), rank = rank, residual_df = residual_df))
  }
  summary_fit <- summary(fit)$coefficients
  term <- "responseR"
  if (!(term %in% rownames(summary_fit))) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      rank = rank, n = nrow(frame), n_R = n_R, n_NR = n_NR,
      status = "NOT_ESTIMABLE", reason = "response_contrast_missing"
    ), rank = rank, residual_df = residual_df))
  }
  estimate <- summary_fit[term, "Estimate"]
  se <- summary_fit[term, "Std. Error"]
  t_value <- if (is.finite(se) && se > 0) estimate / se else NA_real_
  p_value <- if (is.finite(t_value)) 2 * stats::pt(-abs(t_value), df = residual_df) else NA_real_
  level <- as.numeric(cfg$confidence_level)
  half_width <- if (is.finite(se) && se > 0 && is.finite(residual_df) && residual_df > 0) {
    stats::qt(1 - (1 - level) / 2, df = residual_df) * se
  } else NA_real_
  ci_lb <- estimate - half_width
  ci_ub <- estimate + half_width
  zero_uncertainty <- is.finite(se) && se > 0 &&
    !.numerically_positive_uncertainty(se, frame[[outcome]], nrow(frame))
  valid_inference <- is.finite(estimate) && .numerically_positive_uncertainty(se, frame[[outcome]], nrow(frame)) &&
    is.finite(p_value) && p_value >= 0 && p_value <= 1 &&
    is.finite(residual_df) && residual_df > 0 && is.finite(ci_lb) && is.finite(ci_ub) && ci_lb <= ci_ub
  if (!valid_inference) {
    return(list(row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      estimate = estimate, se = if (zero_uncertainty) NA_real_ else se,
      ci_lb = if (zero_uncertainty) NA_real_ else ci_lb,
      ci_ub = if (zero_uncertainty) NA_real_ else ci_ub,
      df = residual_df, rank = rank, n = nrow(frame), n_R = n_R, n_NR = n_NR,
      p_value = if (zero_uncertainty) NA_real_ else p_value,
      status = "NOT_ESTIMABLE",
      reason = if (zero_uncertainty) "zero_residual_uncertainty" else "invalid_inference_precision"
    ), rank = rank, residual_df = residual_df))
  }
  list(
    row = .effect_row(
      frame$unit[[1L]], model_name, contrast, effect_role, method_id,
      estimate = estimate, se = se, ci_lb = ci_lb,
      ci_ub = ci_ub, df = residual_df, rank = rank,
      n = nrow(frame), n_R = n_R, n_NR = n_NR, p_value = p_value,
      status = "ESTIMABLE", reason = ""
    ),
    rank = rank,
    residual_df = residual_df
  )
}

.within_summary <- function(unit, window, response = "", arm = "", values,
                            policy_status = cfg$policy_status) {
  values <- values[is.finite(values)]
  n <- length(values)
  estimate <- if (n) mean(values) else NA_real_
  se <- if (n >= 2L) stats::sd(values) / sqrt(n) else NA_real_
  df <- if (n >= 2L) n - 1L else NA_real_
  half <- if (n >= 2L) stats::qt(1 - (1 - as.numeric(cfg$confidence_level)) / 2, df) * se else NA_real_
  data.frame(
    unit = unit, window = window, response = response, arm = arm, n = n,
    estimate = .number(estimate), se = .number(se),
    ci_lb = .number(if (n >= 2L) estimate - half else NA_real_),
    ci_ub = .number(if (n >= 2L) estimate + half else NA_real_),
    df = .number(df), effect_role = "descriptive_within_group_change",
    status = if (n >= 2L) "DESCRIPTIVE_WITHIN_GROUP_CHANGE" else if (n == 1L) "POINT_ESTIMATE_NO_UNCERTAINTY" else "NOT_ESTIMABLE",
    reason = if (n >= 2L) "" else if (n == 1L) "one_observation_no_uncertainty_estimate" else "no_evaluable_observations",
    policy_status = policy_status,
    stringsAsFactors = FALSE
  )
}

.fit_two_timepoint <- function() {
  input <- .read_authorized_table(request$inputs$design, cfg$boundary$input_fields$design)
  covariates <- unlist(cfg$covariates, use.names = FALSE)
  effects <- .empty_effects()
  within <- .empty_within()
  support <- .empty_support()
  units <- names(cfg$identities)
  for (unit in units) {
    all_rows <- input[input$unit == unit, , drop = FALSE]
    all_rows$response <- as.character(all_rows$response)
    complete_value <- is.finite(all_rows$pre_value) & is.finite(all_rows$on_value)
    valid_response <- !is.na(all_rows$response) & all_rows$response %in% c("R", "NR")
    covariate_complete <- if (length(covariates)) {
      stats::complete.cases(all_rows[, covariates, drop = FALSE])
    } else rep(TRUE, nrow(all_rows))
    eligible <- complete_value & valid_response & covariate_complete
    frame <- all_rows[eligible, , drop = FALSE]
    frame$delta <- frame$on_value - frame$pre_value
    frame$response <- factor(frame$response, levels = c("NR", "R"))
    group_counts <- table(frame$response)
    n_R <- if ("R" %in% names(group_counts)) as.integer(group_counts[["R"]]) else 0L
    n_NR <- if ("NR" %in% names(group_counts)) as.integer(group_counts[["NR"]]) else 0L
    for (group in c("R", "NR")) {
      group_values <- frame$delta[frame$response == group]
      within <- rbind(within, .within_summary(unit, "baseline_to_on", response = group, values = group_values))
    }
    if (length(unique(frame$response)) < 2L) {
      effects <- rbind(effects,
        .effect_row(
          unit, "delta_primary", "R_minus_NR_change", "central_change_contrast",
          cfg$method_ids$delta, n = nrow(frame), n_R = n_R, n_NR = n_NR,
          status = "NOT_ESTIMABLE", reason = "single_response_group"
        ),
        .effect_row(
          unit, "ancova_sensitivity", "R_minus_NR_on_value_conditional_on_pre",
          "conditional_on_baseline_association", cfg$method_ids$ancova,
          n = nrow(frame), n_R = n_R, n_NR = n_NR,
          status = "NOT_ESTIMABLE", reason = "single_response_group"
        )
      )
      effects <- rbind(effects, .fit_delta_sensitivity_rows(all_rows, unit, covariates, "single_response_group"))
      support <- rbind(support, data.frame(
        unit = unit, n_input = nrow(all_rows), n_complete = nrow(frame),
        n_patients_input = length(unique(all_rows$patient_key)),
        n_patients_used = length(unique(frame$patient_key)), n_observations_used = nrow(frame),
        n_missing_endpoint = sum(!valid_response),
        n_missing_expression = sum(!complete_value),
        n_R = n_R, n_NR = n_NR, n_arm_ici = 0L, n_arm_combination = 0L,
        rank = NA_integer_, residual_df = NA_real_,
        status = "NOT_ESTIMABLE", reason = "single_response_group",
        policy_status = cfg$policy_status,
        stringsAsFactors = FALSE
      ))
      next
    }
    if (min(n_R, n_NR) < as.integer(cfg$min_per_response_group)) {
      reason <- "insufficient_response_group_precision_support"
      effects <- rbind(effects,
        .effect_row(
          unit, "delta_primary", "R_minus_NR_change", "central_change_contrast",
          cfg$method_ids$delta, n = nrow(frame), n_R = n_R, n_NR = n_NR,
          status = "NOT_ESTIMABLE", reason = reason
        ),
        .effect_row(
          unit, "ancova_sensitivity", "R_minus_NR_on_value_conditional_on_pre",
          "conditional_on_baseline_association", cfg$method_ids$ancova,
          n = nrow(frame), n_R = n_R, n_NR = n_NR,
          status = "NOT_ESTIMABLE", reason = reason
        )
      )
      effects <- rbind(effects, .fit_delta_sensitivity_rows(all_rows, unit, covariates, reason))
      support <- rbind(support, data.frame(
        unit = unit, n_input = nrow(all_rows), n_complete = nrow(frame),
        n_patients_input = length(unique(all_rows$patient_key)),
        n_patients_used = length(unique(frame$patient_key)), n_observations_used = nrow(frame),
        n_missing_endpoint = sum(!valid_response), n_missing_expression = sum(!complete_value),
        n_R = n_R, n_NR = n_NR, n_arm_ici = 0L, n_arm_combination = 0L,
        rank = NA_integer_, residual_df = NA_real_, status = "NOT_ESTIMABLE", reason = reason,
        policy_status = cfg$policy_status, stringsAsFactors = FALSE
      ))
      next
    }
    primary <- .fit_ols(
      frame, "delta", c("response", covariates), c(n_R, n_NR),
      "delta_primary", "R_minus_NR_change", "central_change_contrast",
      cfg$method_ids$delta
    )
    ancova <- .fit_ols(
      frame, "on_value", c("response", "pre_value", covariates), c(n_R, n_NR),
      "ancova_sensitivity", "R_minus_NR_on_value_conditional_on_pre",
      "conditional_on_baseline_association", cfg$method_ids$ancova
    )
    effects <- rbind(effects, primary$row, ancova$row)
    effects <- rbind(effects, .fit_delta_sensitivity_rows(all_rows, unit, covariates))
    support <- rbind(support, data.frame(
      unit = unit, n_input = nrow(all_rows), n_complete = nrow(frame),
      n_patients_input = length(unique(all_rows$patient_key)),
      n_patients_used = length(unique(frame$patient_key)), n_observations_used = nrow(frame),
      n_missing_endpoint = sum(!valid_response),
      n_missing_expression = sum(!complete_value),
      n_R = n_R, n_NR = n_NR, n_arm_ici = 0L, n_arm_combination = 0L,
      rank = primary$rank,
      residual_df = primary$residual_df,
      status = primary$row$status,
      reason = primary$row$reason,
      policy_status = cfg$policy_status,
      stringsAsFactors = FALSE
    ))
  }
  if (!is.null(cfg$requested_models)) {
    requested <- unlist(cfg$requested_models, use.names = FALSE)
    if (!length(requested) || any(!requested %in% c("delta_primary", "ancova_sensitivity"))) {
      stop("A-LONG requested two-timepoint model set is invalid")
    }
    effects <- effects[effects$model %in% requested, , drop = FALSE]
  }
  .write_output("effects.tsv", effects)
  .write_output("within_group_deltas.tsv", within)
  .write_output("model_support.tsv", support)
}

.fit_delta_sensitivity_rows <- function(all_rows, unit, covariates, inherited_reason = "") {
  modes <- unlist(cfg$sensitivity_modes, use.names = FALSE)
  if (!length(modes)) return(.empty_effects()[FALSE, , drop = FALSE])
  methods <- list(
    same_lesion = cfg$method_ids$same_lesion_sensitivity,
    exact_day = cfg$method_ids$exact_day_sensitivity,
    tighter_timing = cfg$method_ids$tighter_timing_sensitivity
  )
  effects <- .empty_effects()
  for (mode in modes) {
    covariate_complete <- if (length(covariates)) {
      stats::complete.cases(all_rows[, covariates, drop = FALSE])
    } else rep(TRUE, nrow(all_rows))
    frame <- all_rows[
      is.finite(all_rows$pre_value) & is.finite(all_rows$on_value) &
        !is.na(all_rows$response) & all_rows$response %in% c("R", "NR") &
        covariate_complete,
      , drop = FALSE
    ]
    if (identical(mode, "same_lesion")) {
      frame <- frame[tolower(as.character(frame$same_lesion)) %in% c("true", "1", "yes"), , drop = FALSE]
      method_name <- "delta_same_lesion_sensitivity"
      role <- "prespecified_same_lesion_sensitivity"
    } else if (identical(mode, "exact_day")) {
      exact <- function(value) tolower(as.character(value)) %in% c("exact", "day", "days")
      frame <- frame[exact(frame$pre_day_precision) & exact(frame$on_day_precision) &
                       is.finite(frame$pre_day_numeric) & is.finite(frame$on_day_numeric), , drop = FALSE]
      method_name <- "delta_exact_day_sensitivity"
      role <- "prespecified_exact_day_sensitivity"
    } else if (identical(mode, "tighter_timing")) {
      exact <- tolower(as.character(frame$on_day_precision)) %in% c("exact", "day", "days")
      frame <- frame[exact & is.finite(frame$day_distance_to_target) &
                       frame$day_distance_to_target <= as.numeric(cfg$tighter_timing_max_deviation_days), , drop = FALSE]
      method_name <- "delta_tighter_timing_sensitivity"
      role <- "prespecified_tighter_timing_sensitivity"
    } else {
      stop("A-LONG received an unsupported sensitivity mode")
    }
    frame$delta <- frame$on_value - frame$pre_value
    frame$response <- factor(frame$response, levels = c("NR", "R"))
    n_R <- sum(frame$response == "R", na.rm = TRUE)
    n_NR <- sum(frame$response == "NR", na.rm = TRUE)
    if (nzchar(inherited_reason)) {
      fitted <- .effect_row(
        unit, method_name, "R_minus_NR_change", role, methods[[mode]],
        n = nrow(frame), n_R = n_R, n_NR = n_NR,
        status = "NOT_ESTIMABLE", reason = inherited_reason
      )
    } else if (min(n_R, n_NR) < as.integer(cfg$min_per_response_group)) {
      fitted <- .effect_row(
        unit, method_name, "R_minus_NR_change", role, methods[[mode]],
        n = nrow(frame), n_R = n_R, n_NR = n_NR,
        status = "NOT_ESTIMABLE", reason = "insufficient_sensitivity_group_support"
      )
    } else {
      fit <- .fit_ols(
        frame, "delta", c("response", covariates), c(n_R, n_NR),
        method_name, "R_minus_NR_change", role, methods[[mode]]
      )
      fitted <- fit$row
    }
    fitted$analysis_family <- cfg$analysis_family
    effects <- rbind(effects, fitted)
  }
  effects
}

.fit_repeated <- function() {
  bridge_require(c(lme4 = "2.1-0", lmerTest = "3.2-1", pbkrtest = "0.5.5"))
  input <- .read_authorized_table(request$inputs$design, cfg$boundary$input_fields$design)
  levels <- unlist(cfg$window_levels, use.names = FALSE)
  covariates <- unlist(cfg$covariates, use.names = FALSE)
  effects <- .empty_effects()
  within <- .empty_within()
  support <- .empty_support()
  units <- names(cfg$identities)
  for (unit in units) {
    all_rows <- input[input$unit == unit, , drop = FALSE]
    all_rows$response <- as.character(all_rows$response)
    all_rows$window <- as.character(all_rows$window)
    covariate_complete <- if (length(covariates)) {
      stats::complete.cases(all_rows[, covariates, drop = FALSE])
    } else rep(TRUE, nrow(all_rows))
    rows <- all_rows[
      !is.na(all_rows$value) & is.finite(all_rows$value) &
        !is.na(all_rows$response) & all_rows$response %in% c("R", "NR") &
        all_rows$window %in% levels & covariate_complete,
      , drop = FALSE
    ]
    patient_rows <- split(rows, rows$patient_key)
    selection_mode <- as.character(cfg$repeated_selection_mode)
    if (identical(selection_mode, "complete_declared_windows")) {
      selected_patients <- names(Filter(function(patient) {
        setequal(unique(patient$window), levels) &&
          all(vapply(levels, function(level) sum(patient$window == level) == 1L, logical(1)))
      }, patient_rows))
    } else if (identical(selection_mode, "available_observations")) {
      selected_patients <- names(patient_rows)
    } else {
      stop("Unsupported repeated-window missingness selection mode")
    }
    frame <- rows[rows$patient_key %in% selected_patients, , drop = FALSE]
    frame$patient_key <- factor(frame$patient_key)
    frame$response <- factor(frame$response, levels = c("NR", "R"))
    frame$window <- factor(frame$window, levels = levels)
    fixed_terms <- c("patient_key", "response", covariates)
    fixed_design <- if (nrow(frame) && length(unique(frame$patient_key)) > 1L) {
      tryCatch(stats::model.matrix(stats::reformulate(fixed_terms), data = frame), error = function(error) error)
    } else matrix(numeric(), nrow = nrow(frame), ncol = 0L)
    fixed_design_error <- inherits(fixed_design, "error")
    fixed_rank <- if (fixed_design_error) NA_integer_ else if (ncol(fixed_design)) qr(fixed_design)$rank else 0L
    fixed_status <- if (fixed_design_error) "MODEL_MATRIX_ERROR" else if (fixed_rank < ncol(fixed_design)) "RANK_DEFICIENT" else "FULL_RANK"
    n_R <- length(unique(frame$patient_key[frame$response == "R"]))
    n_NR <- length(unique(frame$patient_key[frame$response == "NR"]))
    for (group in c("R", "NR")) {
      for (window in levels[-1L]) {
        selected <- rows[rows$response == group & rows$patient_key %in% selected_patients, , drop = FALSE]
        by_patient <- split(selected, selected$patient_key)
        changes <- unlist(lapply(by_patient, function(patient) {
          if (sum(patient$window == levels[[1L]]) != 1L || sum(patient$window == window) != 1L) return(numeric())
          baseline <- patient$value[patient$window == levels[[1L]]]
          on <- patient$value[patient$window == window]
          on - baseline
        }), use.names = FALSE)
        within <- rbind(within, .within_summary(unit, window, response = group, values = changes))
      }
    }
    base_reason <- ""
    if (nrow(frame) == 0L) base_reason <- "no_complete_patients"
    else if (length(unique(frame$response)) < 2L) base_reason <- "single_response_group"
    else if (length(unique(frame$patient_key)) < as.integer(cfg$min_repeated_patients)) base_reason <- "insufficient_patient_precision_support"
    else if (min(n_R, n_NR) < as.integer(cfg$min_per_response_group)) base_reason <- "insufficient_response_group_precision_support"
    else if (fixed_design_error) base_reason <- "model_matrix_error"
    else if (is.na(fixed_rank) || fixed_rank == 0L) base_reason <- "fixed_design_rank_unavailable"
    model <- NULL
    fit_reason <- base_reason
    model_rank <- NA_integer_
    convergence <- "not_fit"
    singular <- NA
    if (!nzchar(base_reason)) {
      fixed_rhs <- paste(c("response * window", covariates, "(1 | patient_key)"), collapse = " + ")
      fixed_formula <- stats::as.formula(paste("value ~", fixed_rhs))
      model <- tryCatch(
        suppressWarnings(lmerTest::lmer(
          fixed_formula,
          data = frame,
          REML = TRUE,
          control = lme4::lmerControl(check.rankX = "stop.deficient")
        )),
        error = function(error) error
      )
      if (inherits(model, "error")) {
        fit_reason <- "model_fit_error"
      } else {
        model_rank <- qr(lme4::getME(model, "X"))$rank
        singular <- lme4::isSingular(model, tol = 1e-4)
        conv <- model@optinfo$conv
        messages <- conv$lme4$messages
        optimizer_code <- conv$opt
        convergence <- if (length(messages) || (!is.null(optimizer_code) && any(optimizer_code != 0))) "failed" else "passed"
        if (model_rank < ncol(lme4::getME(model, "X"))) fit_reason <- "rank_deficient_design"
        else if (isTRUE(singular)) fit_reason <- "singular_random_intercept_fit"
        else if (convergence != "passed") fit_reason <- "convergence_failure"
      }
    }
    model_summary <- if (!inherits(model, "error") && !is.null(model) && !nzchar(fit_reason)) summary(model)$coefficients else NULL
    for (window in levels[-1L]) {
      window_id <- paste0(levels[[1L]], "_to_", window)
      contrast_rows <- rows[
        rows$patient_key %in% selected_patients & rows$window %in% c(levels[[1L]], window),
        , drop = FALSE
      ]
      contrast_by_patient <- split(contrast_rows, contrast_rows$patient_key)
      contrast_patients <- names(Filter(function(patient) {
        sum(patient$window == levels[[1L]]) == 1L && sum(patient$window == window) == 1L
      }, contrast_by_patient))
      contrast_frame <- contrast_rows[contrast_rows$patient_key %in% contrast_patients, , drop = FALSE]
      contrast_n_R <- length(unique(contrast_frame$patient_key[contrast_frame$response == "R"]))
      contrast_n_NR <- length(unique(contrast_frame$patient_key[contrast_frame$response == "NR"]))
      contrast_reason <- base_reason
      if (!nzchar(contrast_reason) && min(contrast_n_R, contrast_n_NR) < as.integer(cfg$min_per_response_group)) {
        contrast_reason <- "insufficient_response_group_precision_support_for_contrast"
      }
      term <- paste0("responseR:window", window)
      alt_term <- paste0("window", window, ":responseR")
      selected_term <- if (!is.null(model_summary) && term %in% rownames(model_summary)) term else alt_term
      if (nzchar(contrast_reason) || is.null(model_summary) || !(selected_term %in% rownames(model_summary))) {
        refusal_reason <- if (nzchar(contrast_reason)) contrast_reason else if (nzchar(fit_reason)) fit_reason else "interaction_contrast_missing"
        refusal_row <- .effect_row(
          unit, "repeated_response_by_window", paste0("R_minus_NR_at_", window, "_vs_", levels[[1L]]),
          "one_way_longitudinal_corroboration", cfg$method_ids$repeated,
          n = nrow(frame), n_R = contrast_n_R, n_NR = contrast_n_NR, rank = model_rank,
          n_observations_fitted = nrow(frame), n_observations_contrast = nrow(contrast_frame),
          status = "NOT_ESTIMABLE", reason = refusal_reason
        )
        refusal_row$window_id <- window_id
        effects <- rbind(effects, refusal_row)
        next
      }
      coefficient <- model_summary[selected_term, ]
      estimate <- coefficient[["Estimate"]]
      se <- coefficient[["Std. Error"]]
      df <- coefficient[["df"]]
      t_value <- coefficient[["t value"]]
      p_value <- coefficient[["Pr(>|t|)"]]
      critical <- stats::qt(1 - (1 - as.numeric(cfg$confidence_level)) / 2, df = df)
      ci_lb <- estimate - critical * se
      ci_ub <- estimate + critical * se
      zero_uncertainty <- is.finite(se) && se > 0 &&
        !.numerically_positive_uncertainty(se, frame$value, nrow(frame))
      valid_inference <- is.finite(estimate) && .numerically_positive_uncertainty(se, frame$value, nrow(frame)) &&
        is.finite(df) && df > 0 && is.finite(p_value) && p_value >= 0 && p_value <= 1 &&
        is.finite(ci_lb) && is.finite(ci_ub) && ci_lb <= ci_ub
      if (!valid_inference) {
        effect_row <- .effect_row(
          unit, "repeated_response_by_window", paste0("R_minus_NR_at_", window, "_vs_", levels[[1L]]),
          "one_way_longitudinal_corroboration", cfg$method_ids$repeated,
          estimate = estimate, se = if (zero_uncertainty) NA_real_ else se,
          ci_lb = if (zero_uncertainty) NA_real_ else ci_lb,
          ci_ub = if (zero_uncertainty) NA_real_ else ci_ub, df = df, rank = model_rank,
          n = nrow(frame), n_R = contrast_n_R, n_NR = contrast_n_NR,
          n_observations_fitted = nrow(frame), n_observations_contrast = nrow(contrast_frame),
          p_value = if (zero_uncertainty) NA_real_ else p_value,
          status = "NOT_ESTIMABLE",
          reason = if (zero_uncertainty) "zero_residual_uncertainty" else "invalid_inference_precision"
        )
        effect_row$window_id <- window_id
        effects <- rbind(effects, effect_row)
        next
      }
      effect_row <- .effect_row(
        unit, "repeated_response_by_window", paste0("R_minus_NR_at_", window, "_vs_", levels[[1L]]),
        "one_way_longitudinal_corroboration", cfg$method_ids$repeated,
        estimate = estimate, se = se, ci_lb = ci_lb,
        ci_ub = ci_ub, df = df, rank = model_rank,
        n = nrow(frame), n_R = contrast_n_R, n_NR = contrast_n_NR,
        n_observations_fitted = nrow(frame), n_observations_contrast = nrow(contrast_frame),
        p_value = p_value,
        status = "ESTIMABLE", reason = ""
      )
      effect_row$window_id <- window_id
      effects <- rbind(effects, effect_row)
    }
    support <- rbind(support, data.frame(
      unit = unit, n_input = nrow(all_rows), n_complete = nrow(frame),
      n_patients_input = length(unique(all_rows$patient_key)),
      n_patients_used = length(unique(frame$patient_key)), n_observations_used = nrow(frame),
      n_missing_windows = max(0L, length(unique(all_rows$patient_key)) * length(levels) - nrow(frame)),
      n_missing_endpoint = sum(is.na(all_rows$response) | !all_rows$response %in% c("R", "NR")),
      n_missing_expression = sum(is.na(all_rows$value) | !is.finite(all_rows$value)) + sum(!covariate_complete),
      n_R = n_R, n_NR = n_NR, rank = model_rank,
      n_arm_ici = 0L, n_arm_combination = 0L,
      residual_df = if (!is.null(model) && !inherits(model, "error") && !nzchar(fit_reason)) stats::df.residual(model) else NA_real_,
      status = if (nzchar(fit_reason)) "NOT_ESTIMABLE" else "ESTIMABLE",
      reason = fit_reason,
      patient_aware_model = cfg$method_ids$repeated,
      fixed_patient_response_covariate_rank = fixed_rank,
      fixed_patient_response_covariate_rank_status = fixed_status,
      convergence_status = convergence,
      singular = if (is.na(singular)) "" else as.character(singular),
      corroboration_role = "one_way_corroboration_only",
      repeated_selection_mode = selection_mode,
      policy_status = cfg$policy_status,
      stringsAsFactors = FALSE
    ))
  }
  .write_output("effects.tsv", effects)
  .write_output("within_group_deltas.tsv", within)
  .write_output("model_support.tsv", support)
}

.fit_randomized_arm <- function() {
  input <- .read_authorized_table(request$inputs$design, cfg$boundary$input_fields$design)
  covariates <- unlist(cfg$covariates, use.names = FALSE)
  effects <- .empty_effects()
  within <- .empty_within()
  support <- .empty_support()
  for (unit in names(cfg$identities)) {
    all_rows <- input[input$unit == unit, , drop = FALSE]
    all_rows$arm <- as.character(all_rows$arm)
    covariate_complete <- if (length(covariates)) {
      stats::complete.cases(all_rows[, covariates, drop = FALSE])
    } else rep(TRUE, nrow(all_rows))
    valid <- is.finite(all_rows$pre_value) & is.finite(all_rows$on_value) &
      !is.na(all_rows$arm) & all_rows$arm %in% c("ICI_ONLY", "COMBINATION") & covariate_complete
    frame <- all_rows[valid, , drop = FALSE]
    frame$delta <- frame$on_value - frame$pre_value
    frame$arm <- factor(frame$arm, levels = c("ICI_ONLY", "COMBINATION"))
    counts <- table(frame$arm)
    n_ici <- length(unique(frame$patient_key[frame$arm == "ICI_ONLY"]))
    n_combo <- length(unique(frame$patient_key[frame$arm == "COMBINATION"]))
    for (arm_name in c("ICI_ONLY", "COMBINATION")) {
      within <- rbind(within, .within_summary(
        unit, "baseline_to_on", arm = arm_name,
        values = frame$delta[frame$arm == arm_name]
      ))
    }
    if (n_ici == 0L || n_combo == 0L) {
      row <- .effect_row(
        unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
        "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
        n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
        status = "NOT_ESTIMABLE", reason = "single_randomized_arm"
      )
      fit_rank <- NA_integer_
      df <- NA_real_
    } else if (min(n_ici, n_combo) < as.integer(cfg$min_per_randomized_arm)) {
      reason <- "insufficient_randomized_arm_precision_support"
      row <- .effect_row(
        unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
        "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
        n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
        status = "NOT_ESTIMABLE", reason = reason
      )
      fit_rank <- NA_integer_
      df <- NA_real_
    } else {
      formula <- stats::reformulate(c("arm", covariates), response = "delta")
      x <- tryCatch(stats::model.matrix(stats::reformulate(c("arm", covariates)), data = frame), error = function(error) error)
      if (inherits(x, "error")) {
        fit_rank <- NA_integer_
        df <- NA_real_
        row <- .effect_row(
          unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
          "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
          n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
          status = "NOT_ESTIMABLE", reason = "model_matrix_error"
        )
      } else {
        fit_rank <- qr(x)$rank
        df <- nrow(x) - fit_rank
      }
      if (inherits(x, "error")) {
        NULL
      } else if (fit_rank < ncol(x)) {
        reason <- "rank_deficient_design"
        row <- .effect_row(
          unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
          "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
          rank = fit_rank, n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
          status = "NOT_ESTIMABLE", reason = reason
        )
      } else if (df <= 0L) {
        row <- .effect_row(
          unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
          "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
          rank = fit_rank, n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
          status = "NOT_ESTIMABLE", reason = "no_residual_df"
        )
      } else {
        fit <- tryCatch(stats::lm(formula, data = frame), error = function(error) error)
        if (inherits(fit, "error")) {
          row <- .effect_row(
            unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
            "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
            rank = fit_rank, n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
            status = "NOT_ESTIMABLE", reason = "model_fit_error"
          )
        } else {
          coef_table <- summary(fit)$coefficients
          if (!("armCOMBINATION" %in% rownames(coef_table))) {
            row <- .effect_row(
              unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
              "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
              rank = fit_rank, n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
              status = "NOT_ESTIMABLE", reason = "randomized_arm_contrast_missing"
            )
          } else {
            estimate <- coef_table["armCOMBINATION", "Estimate"]
            se <- coef_table["armCOMBINATION", "Std. Error"]
            p <- coef_table["armCOMBINATION", "Pr(>|t|)"]
            half <- if (is.finite(se) && se > 0 && is.finite(df) && df > 0) {
              stats::qt(1 - (1 - as.numeric(cfg$confidence_level)) / 2, df) * se
            } else NA_real_
            ci_lb <- estimate - half
            ci_ub <- estimate + half
            zero_uncertainty <- is.finite(se) && se > 0 &&
              !.numerically_positive_uncertainty(se, frame$delta, nrow(frame))
            valid_inference <- is.finite(estimate) && .numerically_positive_uncertainty(se, frame$delta, nrow(frame)) &&
              is.finite(df) && df > 0 && is.finite(p) && p >= 0 && p <= 1 &&
              is.finite(ci_lb) && is.finite(ci_ub) && ci_lb <= ci_ub
            row <- .effect_row(
              unit, "randomized_arm_change", "COMBINATION_minus_ICI_ONLY_change",
              "randomized_within_study_comparative_estimand", cfg$method_ids$randomized_arm,
              estimate = estimate, se = if (zero_uncertainty) NA_real_ else se,
              ci_lb = if (zero_uncertainty) NA_real_ else ci_lb,
              ci_ub = if (zero_uncertainty) NA_real_ else ci_ub,
              df = df, rank = fit_rank, n = nrow(frame), n_arm_ici = n_ici, n_arm_combination = n_combo,
              p_value = if (zero_uncertainty) NA_real_ else p,
              status = if (valid_inference) "ESTIMABLE" else "NOT_ESTIMABLE",
              reason = if (valid_inference) "" else if (zero_uncertainty) "zero_residual_uncertainty" else "invalid_inference_precision"
            )
          }
        }
      }
    }
    row$analysis_family <- "randomized_arm"
    row$comparative_estimand_id <- cfg$comparative_estimand_id
    row$randomization_verified <- cfg$randomization_verified
    effects <- rbind(effects, row)
    support <- rbind(support, data.frame(
      unit = unit, n_input = nrow(all_rows), n_complete = nrow(frame),
      n_patients_input = length(unique(all_rows$patient_key)),
      n_patients_used = length(unique(frame$patient_key)), n_observations_used = nrow(frame),
      n_missing_endpoint = sum(is.na(all_rows$arm) | !all_rows$arm %in% c("ICI_ONLY", "COMBINATION")),
      n_missing_expression = sum(!is.finite(all_rows$pre_value) | !is.finite(all_rows$on_value)) + sum(!covariate_complete),
      n_R = 0L, n_NR = 0L, n_arm_ici = n_ici, n_arm_combination = n_combo,
      rank = fit_rank, residual_df = df, status = row$status,
      reason = row$reason, policy_status = cfg$policy_status,
      stringsAsFactors = FALSE
    ))
  }
  .write_output("effects.tsv", effects)
  .write_output("within_group_deltas.tsv", within)
  .write_output("model_support.tsv", support)
}

.meta_row <- function(group, effect_rows, group_row) {
  unit <- effect_rows$unit[[1L]]
  eligible_rows <- effect_rows[effect_rows$status == "ESTIMABLE", , drop = FALSE]
  k <- as.integer(group_row$k[[1L]])
  n_input <- as.integer(group_row$n_input[[1L]])
  n_excluded <- as.integer(group_row$n_excluded[[1L]])
  independence_status <- as.character(group_row$independence_status[[1L]])
  reason <- as.character(group_row$preflight_reason[[1L]])
  if (is.na(reason)) reason <- ""
  base <- effect_rows[1L, c(
    "unit_family", "unit", "panel_family", "multiplicity_family_id", "feature_method_id", "analysis_method_id",
    "endpoint_id", "regimen_id", "window_id", "assay_id", "effect_scale_id"
  ), drop = FALSE]
  make <- function(estimate = NA_real_, se = NA_real_, ci_lb = NA_real_, ci_ub = NA_real_,
                   pi_lb = NA_real_, pi_ub = NA_real_, tau2 = NA_real_, i2 = NA_real_,
                   q_stat = NA_real_, p_value = NA_real_, status, reason = "") {
    data.frame(
      analysis_group_id = group,
      base,
      k = k,
      n_input = n_input,
      n_excluded = n_excluded,
      independence_status = independence_status,
      source_family_count = length(unique(eligible_rows$source_family_id)),
      overlap_receipt_count = length(unique(eligible_rows$overlap_receipt_id)),
      estimate = .number(estimate),
      se = .number(se),
      ci_lb = .number(ci_lb),
      ci_ub = .number(ci_ub),
      prediction_interval_lb = .number(pi_lb),
      prediction_interval_ub = .number(pi_ub),
      tau2 = .number(tau2),
      I2 = .number(i2),
      Q = .number(q_stat),
      p_value = .number(p_value),
      status = status,
      reason = reason,
      policy_status = cfg$policy_status,
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  }
  if (nzchar(reason)) return(make(status = "NOT_ESTIMABLE", reason = reason))
  if (k == 1L) {
    row <- eligible_rows[1L, , drop = FALSE]
    return(make(
      estimate = row$estimate, se = row$se,
      ci_lb = if ("ci_lb" %in% names(row)) row$ci_lb else NA_real_,
      ci_ub = if ("ci_ub" %in% names(row)) row$ci_ub else NA_real_,
      p_value = row$p_value,
      status = "single_study",
      reason = "one_study_effect_retained_without_pooling"
    ))
  }
  if (k == 0L) return(make(status = "NOT_ESTIMABLE", reason = "no_estimable_effects"))
  fit <- tryCatch(
    metafor::rma.uni(
      yi = eligible_rows$estimate,
      sei = eligible_rows$se,
      method = "REML",
      test = "adhoc",
      level = as.numeric(cfg$confidence_level) * 100
    ),
    error = function(error) error
  )
  if (inherits(fit, "error")) {
    return(make(status = "NOT_ESTIMABLE", reason = "meta_fit_error"))
  }
  ci <- c(fit$ci.lb, fit$ci.ub)
  pi <- c(NA_real_, NA_real_)
  if (k >= as.integer(cfg$minimum_k_for_pooling)) {
    prediction <- tryCatch(
      stats::predict(fit, level = as.numeric(cfg$confidence_level) * 100),
      error = function(error) NULL
    )
    if (!is.null(prediction)) pi <- c(prediction$pi.lb, prediction$pi.ub)
  }
  make(
    estimate = as.numeric(fit$b), se = fit$se,
    ci_lb = ci[[1L]], ci_ub = ci[[2L]],
    pi_lb = pi[[1L]], pi_ub = pi[[2L]],
    tau2 = fit$tau2, i2 = fit$I2, q_stat = fit$QE, p_value = fit$pval,
    status = if (k < as.integer(cfg$minimum_k_for_pooling)) "tentative_low_k" else "pooled_REML_modified_KH",
    reason = if (k < as.integer(cfg$minimum_k_for_pooling)) "prediction_interval_suppressed_below_minimum_k" else ""
  )
}

.synthesize <- function() {
  bridge_require("metafor")
  effects <- .read_authorized_table(request$inputs$effects, cfg$boundary$input_fields$effects)
  overlap_receipts <- .read_authorized_table(
    request$inputs$overlap_receipts,
    cfg$boundary$input_fields$overlap_receipts
  )
  groups <- .read_authorized_table(request$inputs$groups, cfg$boundary$input_fields$groups)
  if (nrow(overlap_receipts)) {
    if (!all(c("study_a", "study_b", "source_family_a", "source_family_b", "overlap_status", "receipt_sha256") %in% names(overlap_receipts)) ||
        any(!overlap_receipts$overlap_status %in% c("DISJOINT_VERIFIED", "OVERLAPPING", "UNRESOLVED")) ||
        any(!grepl("^[0-9a-f]{64}$", overlap_receipts$receipt_sha256))) {
      stop("A-LONG synthesis overlap receipts are malformed")
    }
  }
  for (index in seq_len(nrow(groups))) {
    group <- as.character(groups$analysis_group_id[[index]])
    rows <- effects[effects$analysis_group_id == group, , drop = FALSE]
    if (nrow(rows) < 2L) next
    if (length(unique(rows$study)) != nrow(rows)) stop("A-LONG synthesis has duplicate study effects in a family")
    pair_statuses <- character()
    for (left_index in seq_len(nrow(rows) - 1L)) {
      for (right_index in seq.int(left_index + 1L, nrow(rows))) {
        left <- rows[left_index, , drop = FALSE]
        right <- rows[right_index, , drop = FALSE]
        receipt <- overlap_receipts[
          (overlap_receipts$study_a == left$study & overlap_receipts$study_b == right$study) |
            (overlap_receipts$study_a == right$study & overlap_receipts$study_b == left$study),
          , drop = FALSE
        ]
        if (nrow(receipt) != 1L) {
          pair_statuses <- c(pair_statuses, "UNRESOLVED")
          next
        }
        expected_a <- if (identical(receipt$study_a[[1L]], left$study[[1L]])) left$source_family_id[[1L]] else right$source_family_id[[1L]]
        expected_b <- if (identical(receipt$study_b[[1L]], right$study[[1L]])) right$source_family_id[[1L]] else left$source_family_id[[1L]]
        if (!identical(receipt$source_family_a[[1L]], expected_a) ||
            !identical(receipt$source_family_b[[1L]], expected_b)) {
          pair_statuses <- c(pair_statuses, "UNRESOLVED")
        } else {
          pair_statuses <- c(pair_statuses, receipt$overlap_status[[1L]])
        }
      }
    }
    group_row <- groups[index, , drop = FALSE]
    if (any(pair_statuses != "DISJOINT_VERIFIED") &&
        (as.integer(group_row$k[[1L]]) > 0L || identical(group_row$independence_status[[1L]], "DISJOINT_VERIFIED"))) {
      stop("A-LONG synthesis groups contradict the pairwise source-overlap receipts")
    }
    if (all(pair_statuses == "DISJOINT_VERIFIED") &&
        !nzchar(as.character(group_row$preflight_reason[[1L]])) &&
        !identical(group_row$independence_status[[1L]], "DISJOINT_VERIFIED")) {
      stop("A-LONG synthesis groups omit pairwise disjointness established by source-overlap receipts")
    }
  }
  output <- data.frame()
  for (index in seq_len(nrow(groups))) {
    group <- as.character(groups$analysis_group_id[[index]])
    rows <- effects[effects$analysis_group_id == group, , drop = FALSE]
    output <- rbind(output, .meta_row(group, rows, groups[index, , drop = FALSE]))
  }
  .write_output("synthesis.tsv", output)
}

if (identical(mode, "fit_two_timepoint")) {
  .fit_two_timepoint()
} else if (identical(mode, "fit_repeated")) {
  .fit_repeated()
} else if (identical(mode, "fit_randomized_arm")) {
  .fit_randomized_arm()
} else if (identical(mode, "synthesize")) {
  .synthesize()
} else {
  stop("Unsupported A-LONG model mode")
}

bridge_write_session(output_dir)
