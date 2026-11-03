.bridge_state <- new.env(parent = emptyenv())
.bridge_state$package_versions <- list()

bridge_assert_project <- function() {
  requested <- Sys.getenv("RENV_PROJECT", unset = "")
  if (!nzchar(requested)) {
    stop("RENV_PROJECT is not set")
  }
  requested <- normalizePath(requested, mustWork = TRUE)
  active <- normalizePath(renv::project(), mustWork = TRUE)
  if (!identical(active, requested)) {
    stop("Active renv project does not match RENV_PROJECT: ", active)
  }

  library <- normalizePath(renv::paths$library(), mustWork = TRUE)
  first_library <- normalizePath(.libPaths()[[1]], mustWork = TRUE)
  if (!identical(first_library, library)) {
    stop("First .libPaths() entry is not the active renv project library")
  }
  list(project = active, library = library)
}

bridge_require <- function(pkgs) {
  active <- bridge_assert_project()
  if (!is.character(pkgs) || !length(pkgs) || any(!nzchar(pkgs))) {
    stop("bridge_require() expects package names as a non-empty character vector")
  }

  requested_names <- names(pkgs)
  if (!is.null(requested_names) && any(!nzchar(requested_names))) {
    stop("When versions are supplied, every package must have a name")
  }
  package_names <- if (is.null(requested_names)) unname(pkgs) else requested_names
  if (anyDuplicated(package_names)) {
    stop("bridge_require() received duplicate package names")
  }
  requested_versions <- if (is.null(requested_names)) NULL else unname(pkgs)

  lock <- renv::lockfile_read(file = file.path(active$project, "renv.lock"))
  versions <- list()
  for (index in seq_along(package_names)) {
    package <- package_names[[index]]
    record <- lock$Packages[[package]]
    if (is.null(record) || is.null(record$Version)) {
      stop("Package is not recorded in renv.lock: ", package)
    }
    locked_version <- as.character(record$Version)
    if (!is.null(requested_versions) &&
        !identical(as.character(requested_versions[[index]]), locked_version)) {
      stop(
        "Requested version for ", package, " (", requested_versions[[index]],
        ") does not match renv.lock version (", locked_version, ")"
      )
    }

    package_path <- find.package(package, lib.loc = active$library, quiet = TRUE)
    if (length(package_path) != 1L) {
      stop("Package is not installed in the active renv library: ", package)
    }
    namespace <- tryCatch(
      loadNamespace(package, lib.loc = active$library),
      error = function(error) stop(
        "Could not load package from the active renv library: ", package,
        ": ", conditionMessage(error)
      )
    )
    loaded_path <- normalizePath(getNamespaceInfo(namespace, "path"), mustWork = TRUE)
    recorded_path <- normalizePath(package_path, mustWork = TRUE)
    if (!identical(loaded_path, recorded_path)) {
      stop("Package was not loaded from the active renv library: ", package)
    }
    installed_version <- as.character(
      utils::packageVersion(package, lib.loc = active$library)
    )
    if (!identical(installed_version, locked_version)) {
      stop(
        "Package version mismatch for ", package, ": installed ",
        installed_version, ", renv.lock records ", locked_version
      )
    }
    versions[[package]] <- installed_version
  }

  for (package in names(versions)) {
    .bridge_state$package_versions[[package]] <- versions[[package]]
  }
  invisible(versions)
}

bridge_config <- function() {
  bridge_assert_project()
  bridge_require("jsonlite")
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) != 1L) {
    stop("Expected exactly one config.json path")
  }
  config <- jsonlite::fromJSON(args[[1]], simplifyVector = FALSE)
  if (is.null(config$output_dir) || !nzchar(config$output_dir)) {
    stop("config.json is missing output_dir")
  }
  config
}

bridge_write_session <- function(out_dir) {
  active <- bridge_assert_project()
  bridge_require(c("jsonlite", "BiocManager"))
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  session <- paste(capture.output(utils::sessionInfo()), collapse = "\n")
  writeLines(session, file.path(out_dir, "sessionInfo.txt"), useBytes = TRUE)

  library_path <- active$library
  home <- normalizePath(Sys.getenv("HOME"), mustWork = TRUE)
  if (identical(library_path, home)) {
    library_path <- "~"
  } else if (startsWith(library_path, paste0(home, .Platform$file.sep))) {
    library_path <- paste0("~", substring(library_path, nchar(home) + 1L))
  }
  runtime <- list(
    r_version = as.character(getRversion()),
    bioconductor_version = as.character(BiocManager::version()),
    r_library = library_path,
    package_versions = .bridge_state$package_versions
  )
  jsonlite::write_json(
    runtime,
    file.path(out_dir, "bridge-runtime.json"),
    auto_unbox = TRUE,
    pretty = TRUE
  )
  invisible(runtime)
}
