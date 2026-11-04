sc_lin_compartments <- c(
  "T/NK", "B/plasma", "myeloid", "fibroblast/stromal", "endothelial", "malignant/epithelial"
)
sc_lin_slugs <- c(
  "t_nk", "b_plasma", "myeloid", "fibroblast_stromal", "endothelial", "malignant_epithelial"
)

sc_lin_metric_family <- function(metric) {
  value <- tolower(trimws(as.character(metric %||% "")))
  if (value %in% c("t-cell expansion", "t cell expansion")) return("expansion")
  if (value %in% c("recist", "objective response", "orr")) return("RECIST")
  if (startsWith(value, "pathology")) return("pathology")
  NA_character_
}

`%||%` <- function(left, right) if (is.null(left) || !length(left) || is.na(left[[1]])) right else left

sc_lin_drug_class <- function(treatment) {
  value <- tolower(gsub("\\s+", "", as.character(treatment %||% "")))
  if (grepl("chemo|tim3", value)) return("OTHER_EXCLUDED")
  if (value %in% c("apd1+ctla4", "apdl1+ctla4", "apd1+ipilimumab")) return("DUAL_PD1_CTLA4")
  if (value %in% c("actla4", "ipilimumab")) return("ANTI_CTLA4")
  if (value %in% c("apd1", "apdl1")) return("ANTI_PD_L1_AXIS")
  "UNMAPPED"
}

sc_lin_compartment <- function(metadata, compartment_map) {
  result <- rep(NA_character_, nrow(metadata))
  for (index in seq_len(nrow(compartment_map))) {
    field <- compartment_map$source_field[[index]]
    if (!field %in% colnames(metadata)) stop("Compartment source field is absent: ", field)
    selected <- !is.na(metadata[[field]]) & as.character(metadata[[field]]) == compartment_map$source_label[[index]]
    result[selected] <- compartment_map$compartment[[index]]
  }
  result[result == "unmapped"] <- NA_character_
  result
}

sc_lin_layer_components <- function(object, layer) {
  assay <- object[["RNA"]]
  if (!inherits(assay, "Assay5")) stop("The Lin RNA assay is not a Seurat v5 Assay5")
  layer_names <- names(assay@layers)
  if (is.null(layer_names) || !layer %in% layer_names) {
    stop("Requested Lin count layer is absent from the RNA assay")
  }
  matrix <- assay@layers[[layer]]
  cells <- SeuratObject::Cells(assay, layer = layer)
  features <- SeuratObject::Features(assay, layer = layer)
  if (length(cells) != ncol(matrix) || length(features) != nrow(matrix)) {
    stop("Lin assay layer mappings do not match the stored sparse matrix dimensions")
  }
  list(matrix = matrix, cells = cells, features = features)
}

sc_lin_invalid_count_columns <- function(matrix) {
  if (!inherits(matrix, "CsparseMatrix")) stop("A Lin count layer is not a column-compressed sparse matrix")
  values <- matrix@x
  invalid <- !is.finite(values) | values < 0 | values != trunc(values)
  invalid[is.na(invalid)] <- TRUE
  bad_entries <- which(invalid)
  invalid_columns <- logical(ncol(matrix))
  if (!length(bad_entries)) return(invalid_columns)
  bad_columns <- unique(findInterval(bad_entries - 1L, matrix@p))
  bad_columns <- bad_columns[bad_columns >= 1L & bad_columns <= ncol(matrix)]
  invalid_columns[bad_columns] <- TRUE
  invalid_columns
}

sc_lin_marker_summary <- function(object, marker_map, metadata) {
  markers <- list(
    "T/NK" = c("CD3D", "CD3E", "TRAC", "NKG7"),
    "B/plasma" = c("MS4A1", "CD79A", "MZB1", "JCHAIN"),
    "Myeloid" = c("LST1", "TYROBP", "FCER1G", "S100A9"),
    "Fibroblast/stromal" = c("COL1A1", "DCN", "ACTA2", "RGS5"),
    "Endothelial" = c("PECAM1", "VWF", "KDR", "EMCN"),
    "Epithelial/malignant" = c("EPCAM", "KRT8", "KRT18", "KRT5", "KRT14")
  )
  layers <- grep("^counts($|[.])", SeuratObject::Layers(object[["RNA"]]), value = TRUE)
  rows <- list()
  selected_genes <- unique(unlist(markers, use.names = FALSE))
  for (layer in layers) {
    components <- sc_lin_layer_components(object, layer)
    matrix <- components$matrix
    cells <- components$cells
    features <- components$features
    matched_features <- match(selected_genes, features)
    present <- which(!is.na(matched_features))
    if (!length(present)) next
    marker_features <- selected_genes[present]
    marker_matrix <- matrix[matched_features[present], , drop = FALSE]
    metadata_rows <- match(cells, rownames(metadata))
    labels <- as.character(metadata$celltype_main[metadata_rows])
    library_size <- Matrix::colSums(matrix)
    for (label in unique(labels[!is.na(labels)])) {
      label_cells <- which(labels == label & library_size > 0)
      if (!length(label_cells)) next
      label_counts <- as.matrix(marker_matrix[, label_cells, drop = FALSE])
      label_library_size <- library_size[label_cells]
      for (gene_index in seq_along(marker_features)) {
        gene <- marker_features[[gene_index]]
        counts <- as.numeric(label_counts[gene_index, , drop = TRUE])
        cpm <- counts / label_library_size * 1e6
        rows[[length(rows) + 1L]] <- data.frame(
          author_label = label,
          gene = gene,
          percent_cells_detected = mean(counts > 0) * 100,
          mean_log2_cpm_plus1 = mean(log2(cpm + 1)),
          n_cells = length(label_cells),
          count_layer = layer,
          stringsAsFactors = FALSE
        )
      }
      rm(label_counts, label_library_size)
    }
  }
  if (!length(rows)) return(data.frame())
  data <- do.call(rbind, rows)
  grouped <- split(data, paste(data$author_label, data$gene, sep = "\r"))
  do.call(rbind, lapply(grouped, function(frame) {
    weight <- frame$n_cells / sum(frame$n_cells)
    data.frame(
      author_label = frame$author_label[[1]],
      gene = frame$gene[[1]],
      percent_cells_detected = sum(frame$percent_cells_detected * weight),
      mean_log2_cpm_plus1 = sum(frame$mean_log2_cpm_plus1 * weight),
      n_cells = sum(frame$n_cells),
      stringsAsFactors = FALSE
    )
  }))
}

sc_lin_combine_marker_summaries <- function(marker_records) {
  nonempty <- Filter(function(frame) is.data.frame(frame) && nrow(frame) > 0L, marker_records)
  if (!length(nonempty)) return(data.frame())
  data <- do.call(rbind, nonempty)
  groups <- split(seq_len(nrow(data)), paste(data$author_label, data$gene, sep = "\r"))
  do.call(rbind, lapply(groups, function(indices) {
    frame <- data[indices, , drop = FALSE]
    weights <- frame$n_cells / sum(frame$n_cells)
    data.frame(
      author_label = frame$author_label[[1]],
      gene = frame$gene[[1]],
      percent_cells_detected = sum(frame$percent_cells_detected * weights),
      mean_log2_cpm_plus1 = sum(frame$mean_log2_cpm_plus1 * weights),
      n_cells = sum(frame$n_cells),
      stringsAsFactors = FALSE
    )
  }))
}

sc_lin_make_profile_id <- function(cohort, patient, sample, compartment) {
  slug <- gsub("[^a-z0-9]+", "_", tolower(compartment))
  paste(cohort, patient, sample, slug, sep = "__")
}

sc_lin_profile_layers <- function(seurat_path, metadata, cohort_map, compartment_map, panel_genes,
                                  min_cells = 15L, min_umis = 5000L) {
  metadata_all <- metadata
  required <- c("patient", "sample", "cohort", "time_point", "treatment", "response", "res_metric", "celltype_main")
  missing <- setdiff(required, colnames(metadata_all))
  if (length(missing)) stop("Required Lin metadata columns are missing: ", paste(missing, collapse = ", "))
  metadata_all <- metadata_all[, required, drop = FALSE]
  marker_metadata <- metadata_all[, "celltype_main", drop = FALSE]
  rm(metadata)
  cohort_index <- setNames(cohort_map$cancer, cohort_map$cohort)
  metadata_all$cancer <- unname(cohort_index[as.character(metadata_all$cohort)])

  treatment <- as.character(metadata_all$treatment)
  eligible_baseline <- tolower(as.character(metadata_all$time_point)) == "pre" &
    !as.character(metadata_all$cohort) %in% c("NSCLC_Yan", "TNBC_Zhang") &
    !grepl("chemo|^noici$", treatment, ignore.case = TRUE) &
    grepl("^aPD|CTLA4", treatment, ignore.case = TRUE) &
    !is.na(metadata_all$cancer)
  eligible_baseline[is.na(eligible_baseline)] <- FALSE
  selected_meta <- metadata_all[eligible_baseline, , drop = FALSE]
  rm(metadata_all)
  invisible(gc())
  if (!nrow(selected_meta)) stop("No baseline ICI-only cells remain after the signed exclusions")
  patient_samples <- unique(selected_meta[, c("cohort", "patient", "sample"), drop = FALSE])
  sample_counts <- aggregate(sample ~ cohort + patient, data = patient_samples, FUN = function(x) length(unique(x)))
  if (any(sample_counts$sample > 1L)) stop("A patient has more than one eligible baseline specimen")
  rm(patient_samples, sample_counts)
  invisible(gc())

  denominator <- table(paste(selected_meta$cohort, selected_meta$patient, sep = "\r"))
  selected_meta$compartment <- sc_lin_compartment(selected_meta, compartment_map)
  selected_meta <- selected_meta[!is.na(selected_meta$compartment), , drop = FALSE]
  layer_results <- vector("list", 2L)
  names(layer_results) <- character(2L)
  marker_records <- vector("list", 2L)
  for (layer_index in seq_len(2L)) {
    object <- qs2::qs_read(seurat_path)
    layers <- grep("^counts($|[.])", SeuratObject::Layers(object[["RNA"]]), value = TRUE)
    if (length(layers) != 2L) stop("The Lin atlas must retain its two original count layers")
    layer <- layers[[layer_index]]
    object <- Seurat::DietSeurat(object, assays = "RNA", layers = layer,
      dimreducs = NULL, graphs = NULL, misc = FALSE)
    remaining_layers <- grep("^counts($|[.])", SeuratObject::Layers(object[["RNA"]]), value = TRUE)
    if (length(remaining_layers) != 1L || !identical(remaining_layers[[1]], layer)) {
      stop("Could not isolate one Lin count layer for bounded-memory processing")
    }
    invisible(gc())
    names(layer_results)[[layer_index]] <- layer
    message("Lin profile layer ", layer_index, " isolated from the other count layer")
    marker_records[[layer_index]] <- sc_lin_marker_summary(object, panel_genes, marker_metadata)
    message("Lin profile layer ", layer_index, " aggregation started")
    components <- sc_lin_layer_components(object, layer)
    matrix <- components$matrix
    layer_cells <- components$cells
    layer_features <- components$features
    message("Lin profile layer ", layer_index, ": matrix loaded; features=", nrow(matrix), "; cells=", ncol(matrix), "; stored_values=", length(matrix@x))
    chunk_size <- 5000L
    chunk_starts <- seq.int(1L, ncol(matrix), by = chunk_size)
    message("Lin profile layer ", layer_index, ": profile discovery started")
    selected_rows <- match(layer_cells, rownames(selected_meta))
    selected_columns <- which(!is.na(selected_rows))
    message("Lin profile layer ", layer_index, ": matched baseline cells=", length(selected_columns))
    matched_rows <- selected_rows[selected_columns]
    submeta <- selected_meta[matched_rows, , drop = FALSE]
    keys <- paste(submeta$cohort, submeta$patient, submeta$sample, submeta$compartment, sep = "\r")
    profile_keys <- unique(keys)
    profile_rows <- matched_rows[match(profile_keys, keys)]
    rm(selected_columns, matched_rows, submeta, keys)
    invisible(gc())
    if (!length(profile_keys)) {
      message("Lin profile layer ", layer_index, ": no baseline ICI cells matched")
      rm(matrix, components, layer_cells, layer_features, chunk_starts, selected_rows, profile_keys, profile_rows,
        object, layers, remaining_layers)
      invisible(gc())
      next
    }
    profile_metadata <- selected_meta[profile_rows, , drop = FALSE]
    message("Lin profile layer ", layer_index, ": profiles=", length(profile_keys))
    profile_ids <- sc_lin_make_profile_id(
      profile_metadata$cohort, profile_metadata$patient, profile_metadata$sample, profile_metadata$compartment
    )
    if (anyDuplicated(profile_ids)) stop("A Lin pseudobulk profile key is not unique")
    profile_count <- length(profile_keys)
    aggregate_counts <- Matrix::sparseMatrix(i = integer(), j = integer(), x = numeric(),
      dims = c(length(layer_features), profile_count))
    detected <- Matrix::sparseMatrix(i = integer(), j = integer(), x = numeric(),
      dims = c(length(layer_features), profile_count))
    n_cells <- integer(profile_count)

    message("Lin profile layer ", layer_index, ": chunk aggregation started")
    invalid_profile <- logical(profile_count)
    for (chunk_start in chunk_starts) {
      chunk_end <- min(chunk_start + chunk_size - 1L, ncol(matrix))
      chunk_columns <- seq.int(chunk_start, chunk_end)
      chunk_rows <- selected_rows[chunk_columns]
      selected_columns <- which(!is.na(chunk_rows))
      if (!length(selected_columns)) next
      submeta <- selected_meta[chunk_rows[selected_columns], , drop = FALSE]
      selected_counts <- matrix[, chunk_columns[selected_columns], drop = FALSE]
      keys <- paste(submeta$cohort, submeta$patient, submeta$sample, submeta$compartment, sep = "\r")
      group_index <- match(keys, profile_keys)
      if (anyNA(group_index)) stop("Lin profile key was not discovered during the first layer pass")
      n_cells <- n_cells + tabulate(group_index, nbins = profile_count)
      invalid_cells <- sc_lin_invalid_count_columns(selected_counts)
      if (any(invalid_cells)) invalid_profile[unique(group_index[invalid_cells])] <- TRUE
      valid_cells <- !invalid_cells
      if (any(valid_cells)) {
        valid_counts <- selected_counts[, valid_cells, drop = FALSE]
        valid_groups <- group_index[valid_cells]
        assignment <- Matrix::sparseMatrix(
          i = seq_along(valid_groups), j = valid_groups, x = 1,
          dims = c(length(valid_groups), profile_count)
        )
        aggregate_counts <- aggregate_counts + valid_counts %*% assignment
        detected <- detected + (valid_counts > 0) %*% assignment
        rm(valid_counts, valid_groups, assignment)
      }
      rm(submeta, selected_counts, keys, group_index, invalid_cells, valid_cells, selected_columns, chunk_rows)
      if ((chunk_start - 1L) %/% chunk_size %% 20L == 19L) invisible(gc())
    }
    message("Lin profile layer ", layer_index, ": chunk aggregation complete")
    message("Lin profile layer ", layer_index, ": profiles with invalid raw count values=", sum(invalid_profile))
    library_size <- as.numeric(Matrix::colSums(aggregate_counts))
    library_size[invalid_profile] <- NA_real_
    eligible <- n_cells >= min_cells & !invalid_profile & library_size >= min_umis
    status <- ifelse(n_cells < min_cells, "below_cell_threshold",
      ifelse(invalid_profile, "invalid_raw_counts", ifelse(library_size < min_umis, "below_umi_threshold", "eligible")))
    count_matrix <- aggregate_counts
    detection_matrix <- detected
    colnames(count_matrix) <- profile_ids
    rownames(count_matrix) <- layer_features
    colnames(detection_matrix) <- profile_ids
    rownames(detection_matrix) <- layer_features
    profile_metadata$profile_id <- profile_ids
    profile_metadata$patient_id <- as.character(profile_metadata$patient)
    profile_metadata$study <- as.character(profile_metadata$cohort)
    profile_metadata$compartment <- as.character(profile_metadata$compartment)
    profile_metadata$response_metric <- as.character(profile_metadata$res_metric)
    profile_metadata$endpoint_family <- vapply(profile_metadata$response_metric, sc_lin_metric_family, character(1))
    labels <- toupper(trimws(as.character(profile_metadata$response)))
    profile_metadata$outcome_label <- ifelse(labels %in% c("R", "NR"), labels, NA_character_)
    profile_metadata$response <- ifelse(profile_metadata$endpoint_family == "expansion", NA_character_, profile_metadata$outcome_label)
    profile_metadata$treatment <- as.character(profile_metadata$treatment)
    profile_metadata$drug_class <- vapply(profile_metadata$treatment, sc_lin_drug_class, character(1))
    profile_metadata$n_cells <- n_cells
    profile_metadata$total_umis <- as.integer(library_size)
    profile_metadata$library_size <- as.integer(library_size)
    profile_metadata$reason <- ifelse(status == "invalid_raw_counts", "non_integer_or_invalid_raw_counts",
      ifelse(status == "below_cell_threshold", "below_minimum_cells",
        ifelse(status == "below_umi_threshold", "below_minimum_umis", "")))
    profile_metadata$eligible <- eligible
    profile_metadata$status <- status
    profile_metadata$count_layer <- layer
    denominator_key <- paste(profile_metadata$cohort, profile_metadata$patient, sep = "\r")
    profile_metadata$fraction_cells_total <- n_cells / as.numeric(denominator[denominator_key])
    profile_metadata$baseline <- TRUE
    keep <- c("profile_id", "patient_id", "patient", "sample", "cohort", "study", "cancer", "treatment", "drug_class",
      "response_metric", "response", "outcome_label", "endpoint_family", "compartment", "n_cells", "total_umis", "reason",
      "library_size", "eligible", "status", "count_layer", "fraction_cells_total", "baseline")
    profile_metadata <- profile_metadata[, keep, drop = FALSE]
    layer_results[[layer]] <- list(counts = count_matrix, detection = detection_matrix, clinical = profile_metadata)
    message("Lin profile layer ", layer_index, " aggregation complete")
    rm(matrix, components, layer_cells, layer_features, chunk_starts, profile_keys, profile_rows,
      selected_rows, profile_metadata, profile_ids, aggregate_counts, detected, count_matrix, detection_matrix,
      n_cells, library_size, eligible, status, denominator_key, object, layers, remaining_layers)
    invisible(gc())
  }
  nonempty <- Filter(Negate(is.null), layer_results)
  if (!length(nonempty)) stop("No baseline ICI-only pseudobulk profiles were created")
  all_profile_ids <- unlist(lapply(nonempty, function(x) colnames(x$counts)), use.names = FALSE)
  if (anyDuplicated(all_profile_ids)) stop("A patient-compartment profile occurs in both count layers")
  list(layers = nonempty, clinical = do.call(rbind, lapply(nonempty, `[[`, "clinical")),
    marker_map = sc_lin_combine_marker_summaries(marker_records))
}

sc_lin_layer_matrix_by_compartment <- function(layers, slot_name, compartment) {
  pieces <- lapply(layers, function(layer) {
    clinical <- layer$clinical
    ids <- clinical$profile_id[clinical$compartment == compartment]
    matrix <- layer[[slot_name]]
    matrix[, intersect(ids, colnames(matrix)), drop = FALSE]
  })
  pieces <- Filter(function(x) ncol(x) > 0L, pieces)
  if (!length(pieces)) return(matrix(numeric(), nrow = 0L, ncol = 0L))
  genes <- unique(unlist(lapply(pieces, rownames), use.names = FALSE))
  profiles <- unlist(lapply(pieces, colnames), use.names = FALSE)
  result <- matrix(NA_real_, nrow = length(genes), ncol = length(profiles), dimnames = list(genes, profiles))
  offset <- 0L
  for (piece in pieces) {
    columns <- seq.int(offset + 1L, offset + ncol(piece))
    result[rownames(piece), columns] <- as.matrix(piece)
    offset <- offset + ncol(piece)
  }
  result
}

sc_lin_expression_table <- function(layers, clinical, cohort_map, panel_genes, min_donors = 5L) {
  genes <- unique(as.character(panel_genes$gene))
  all_cohorts <- as.character(cohort_map$cohort)
  records <- list()
  for (compartment in sc_lin_compartments) {
    counts <- sc_lin_layer_matrix_by_compartment(layers, "counts", compartment)
    detection <- sc_lin_layer_matrix_by_compartment(layers, "detection", compartment)
    for (cohort in all_cohorts) {
      profiles <- clinical[clinical$cohort == cohort & clinical$compartment == compartment & clinical$eligible, , drop = FALSE]
      n_donors <- length(unique(profiles$patient_id))
      for (gene in genes) {
        gene_counts <- if (gene %in% rownames(counts)) counts[gene, , drop = TRUE] else rep(NA_real_, ncol(counts))
        names(gene_counts) <- colnames(counts)
        observed <- profiles$profile_id[profiles$profile_id %in% names(gene_counts) & !is.na(gene_counts[profiles$profile_id])]
        donor_values <- numeric()
        donor_cpm <- numeric()
        donor_detection <- numeric()
        for (profile_id in observed) {
          row <- profiles[profiles$profile_id == profile_id, , drop = FALSE]
          cpm <- as.numeric(gene_counts[[profile_id]]) / row$library_size[[1]] * 1e6
          donor_cpm <- c(donor_cpm, cpm)
          donor_values <- c(donor_values, log2(cpm + 1))
          if (gene %in% rownames(detection) && profile_id %in% colnames(detection)) {
            donor_detection <- c(donor_detection, detection[gene, profile_id] / row$n_cells[[1]] * 100)
          }
        }
        status <- if (!gene %in% rownames(counts)) "missing_from_layer" else if (n_donors < min_donors) "insufficient_donors" else if (length(observed) < min_donors) "insufficient_gene_coverage" else "shown"
        records[[length(records) + 1L]] <- data.frame(
          gene = gene, compartment = compartment, study = cohort,
          n_donors = n_donors, n_gene_donors = length(observed),
          median_log2_cpm_plus1 = if (status == "shown") median(donor_values) else NA_real_,
          q1_log2_cpm_plus1 = if (status == "shown") unname(quantile(donor_values, .25)) else NA_real_,
          q3_log2_cpm_plus1 = if (status == "shown") unname(quantile(donor_values, .75)) else NA_real_,
          median_cpm = if (status == "shown") median(donor_cpm) else NA_real_,
          median_percent_cells_detected = if (status == "shown" && length(donor_detection)) median(donor_detection) else NA_real_,
          status = status, detection_limit_tag = "not_assessed", stringsAsFactors = FALSE
        )
      }
    }
  }
  output <- do.call(rbind, records)
  key_groups <- split(seq_len(nrow(output)), paste(output$study, output$gene, sep = "\r"))
  for (indices in key_groups) {
    rows <- output[indices, , drop = FALSE]
    if (any(rows$status != "shown") || all(is.na(rows$median_cpm))) {
      tag <- "not_assessed"
    } else if (all(rows$median_cpm < 50)) {
      tag <- "below_scRNA_detection_limit"
    } else {
      tag <- "measured_at_or_above_detection_limit"
    }
    output$detection_limit_tag[indices] <- tag
  }
  output
}

sc_lin_pcahawley_patient_expression <- function(layers, clinical, panel_genes) {
  output_columns <- c(
    "cohort", "patient_id", "profile_id", "compartment", "gene", "panel_ids",
    "n_cells", "total_umis", "status", "log2_cpm_plus1",
    "percent_cells_detected", "detection_limit_tag"
  )
  patients <- clinical[clinical$cohort == "PCa_Hawley", , drop = FALSE]
  if (!nrow(patients)) {
    return(data.frame(matrix(nrow = 0, ncol = length(output_columns), dimnames = list(NULL, output_columns))))
  }
  genes <- unique(as.character(panel_genes$gene))
  panel_ids <- vapply(genes, function(gene) {
    paste(unique(as.character(panel_genes$panel_id[panel_genes$gene == gene])), collapse = ",")
  }, character(1))
  rows <- list()
  for (compartment in unique(patients$compartment)) {
    counts <- sc_lin_layer_matrix_by_compartment(layers, "counts", compartment)
    detection <- sc_lin_layer_matrix_by_compartment(layers, "detection", compartment)
    profiles <- patients[patients$compartment == compartment, , drop = FALSE]
    for (index in seq_len(nrow(profiles))) {
      profile <- profiles[index, , drop = FALSE]
      for (gene in genes) {
        status <- if (!isTRUE(profile$eligible[[1]])) as.character(profile$status[[1]]) else "eligible"
        detected <- NA_real_
        log_cpm <- NA_real_
        if (status == "eligible") {
          profile_id <- as.character(profile$profile_id[[1]])
          if (!gene %in% rownames(counts) || !profile_id %in% colnames(counts) ||
              is.na(counts[gene, profile_id])) {
            status <- "missing_from_layer"
          } else {
            count <- as.numeric(counts[gene, profile_id])
            log_cpm <- log2(count / as.numeric(profile$library_size[[1]]) * 1e6 + 1)
            if (gene %in% rownames(detection) && profile_id %in% colnames(detection)) {
              detected <- as.numeric(detection[gene, profile_id]) / as.numeric(profile$n_cells[[1]]) * 100
            }
          }
        }
        rows[[length(rows) + 1L]] <- data.frame(
          cohort = "PCa_Hawley", patient_id = as.character(profile$patient_id[[1]]),
          profile_id = as.character(profile$profile_id[[1]]), compartment = compartment,
          gene = gene, panel_ids = panel_ids[[gene]], n_cells = as.integer(profile$n_cells[[1]]),
          total_umis = as.integer(profile$total_umis[[1]]), status = status,
          log2_cpm_plus1 = log_cpm, percent_cells_detected = detected,
          detection_limit_tag = "not_assessed", stringsAsFactors = FALSE
        )
      }
    }
  }
  output <- if (length(rows)) do.call(rbind, rows) else data.frame()
  if (!nrow(output)) return(output)
  for (gene in genes) {
    gene_rows <- output[output$gene == gene, , drop = FALSE]
    compartment_medians <- vapply(unique(gene_rows$compartment), function(compartment) {
      measured <- gene_rows$log2_cpm_plus1[gene_rows$compartment == compartment]
      measured <- measured[is.finite(measured)]
      if (length(measured)) stats::median(2^measured - 1) else NA_real_
    }, numeric(1))
    all_compartments_measured <- all(sc_lin_compartments %in% names(compartment_medians)) && !anyNA(compartment_medians)
    tag <- if (all_compartments_measured && all(compartment_medians < 50)) {
      "below_scRNA_detection_limit"
    } else if (all_compartments_measured) {
      "measured_at_or_above_detection_limit"
    } else {
      "not_assessed"
    }
    output$detection_limit_tag[output$gene == gene] <- tag
  }
  output
}

sc_lin_compartment_qc <- function(clinical, cohort_map) {
  rows <- list()
  for (cohort in as.character(cohort_map$cohort)) {
    for (compartment in sc_lin_compartments) {
      current <- clinical[clinical$cohort == cohort & clinical$compartment == compartment, , drop = FALSE]
      rows[[length(rows) + 1L]] <- data.frame(
        cohort = cohort,
        compartment = compartment,
        profiles = nrow(current),
        eligible_donors = length(unique(current$patient_id[current$eligible])),
        na_profiles = sum(!current$eligible),
        stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, rows)
}

sc_lin_write_dotplot <- function(data, output, label_column, title, colour_column = "mean_log2_cpm_plus1") {
  plot_data <- data
  if ("study" %in% colnames(plot_data) && "status" %in% colnames(plot_data)) {
    plot_data <- plot_data[plot_data$status == "shown", , drop = FALSE]
  }
  if (nrow(plot_data)) {
    size_column <- if ("percent_cells_detected" %in% colnames(plot_data)) {
      "percent_cells_detected"
    } else if ("median_percent_cells_detected" %in% colnames(plot_data)) {
      "median_percent_cells_detected"
    } else {
      NULL
    }
    point <- ggplot2::geom_point(ggplot2::aes_string(colour = colour_column), na.rm = TRUE)
    if (!is.null(size_column)) {
      point <- ggplot2::geom_point(
        ggplot2::aes_string(size = size_column, colour = colour_column), na.rm = TRUE
      )
    }
    plot <- ggplot2::ggplot(plot_data, ggplot2::aes_string(x = "gene", y = label_column)) +
      point +
      ggplot2::scale_size_continuous(name = "% cells > 0", range = c(0.5, 6)) +
      ggplot2::scale_colour_gradient(name = "log2(CPM + 1)", low = "grey95", high = "purple4", na.value = "grey85") +
      ggplot2::labs(x = NULL, y = NULL, title = title) +
      ggplot2::theme_bw(base_size = 8) +
      ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 90, hjust = 1, vjust = 0.5))
    if ("study" %in% colnames(plot_data)) plot <- plot + ggplot2::facet_wrap(~study, ncol = 3)
    ggplot2::ggsave(output, plot, width = 16, height = 8, dpi = 180)
  } else {
    grDevices::png(output, width = 1200, height = 600)
    graphics::plot.new()
    graphics::title(main = title)
    grDevices::dev.off()
  }
}

sc_lin_process <- function(seurat_path, metadata, cohort_map, compartment_map, panel_genes,
                           min_cells = 15L, min_umis = 5000L) {
  message("Lin profile aggregation started")
  profiles <- sc_lin_profile_layers(seurat_path, metadata, cohort_map, compartment_map, panel_genes,
    min_cells, min_umis)
  message("Lin profile aggregation complete")
  marker_map <- profiles$marker_map
  message("Lin cohort expression summary started")
  expression <- sc_lin_expression_table(profiles$layers, profiles$clinical, cohort_map, panel_genes, min_donors = 5L)
  message("Lin cohort expression summary complete")
  list(
    layers = profiles$layers,
    clinical = profiles$clinical,
    marker_map = marker_map,
    expression = expression,
    pcahawley_patient_expression = sc_lin_pcahawley_patient_expression(
      profiles$layers, profiles$clinical, panel_genes
    ),
    compartment_qc = sc_lin_compartment_qc(profiles$clinical, cohort_map)
  )
}
