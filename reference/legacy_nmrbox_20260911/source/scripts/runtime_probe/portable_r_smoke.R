#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
out_dir <- Sys.getenv("PORTABLE_R_SMOKE_OUT", unset = "runtime_audits/local_smoke")

if (length(args) > 0) {
  for (i in seq_along(args)) {
    if (args[[i]] == "--out-dir" && i < length(args)) {
      out_dir <- args[[i + 1]]
    }
  }
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

required_packages <- c(
  "GSVA",
  "limma",
  "edgeR",
  "DESeq2",
  "GSEABase",
  "BiocParallel",
  "sva",
  "survival",
  "ggplot2",
  "msigdbr",
  "yaml"
)

package_rows <- lapply(required_packages, function(pkg) {
  available <- requireNamespace(pkg, quietly = TRUE)
  version <- if (available) as.character(utils::packageVersion(pkg)) else "missing"
  data.frame(package = pkg, available = available, version = version, stringsAsFactors = FALSE)
})
package_versions <- do.call(rbind, package_rows)
utils::write.table(
  package_versions,
  file = file.path(out_dir, "r_package_versions.tsv"),
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

missing_packages <- package_versions$package[!package_versions$available]
if (length(missing_packages) > 0) {
  writeLines(
    c(
      "# Portable R Runtime Smoke Audit",
      "",
      paste0("Status: failed"),
      paste0("Missing packages: ", paste(missing_packages, collapse = ", "))
    ),
    con = file.path(out_dir, "runtime_smoke_audit.md")
  )
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

suppressPackageStartupMessages({
  library(GSVA)
  library(limma)
})

expr <- matrix(
  c(
    8.0, 8.2, 5.1, 5.3,
    7.5, 7.7, 4.8, 5.0,
    6.1, 6.0, 6.2, 6.1,
    3.0, 3.2, 7.1, 7.4,
    4.2, 4.0, 4.1, 4.2,
    5.3, 5.5, 5.2, 5.4
  ),
  nrow = 6,
  byrow = TRUE
)
rownames(expr) <- c("CXCL9", "CXCL10", "IFNG", "DUSP13B", "ACTB", "GAPDH")
colnames(expr) <- c("responder_1", "responder_2", "non_responder_1", "non_responder_2")

group <- factor(c("responder", "responder", "non_responder", "non_responder"))
design <- model.matrix(~ 0 + group)
colnames(design) <- levels(group)
fit <- limma::lmFit(expr, design)
contrast <- limma::makeContrasts(responder - non_responder, levels = design)
fit2 <- limma::eBayes(limma::contrasts.fit(fit, contrast), trend = TRUE)
limma_results <- limma::topTable(fit2, number = Inf, sort.by = "none")
limma_results$gene <- rownames(limma_results)
limma_results <- limma_results[, c("gene", setdiff(colnames(limma_results), "gene"))]
utils::write.table(
  limma_results,
  file = file.path(out_dir, "limma_smoke_results.tsv"),
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

gene_sets <- list(
  ICB_INFLAMED_SMOKE = c("CXCL9", "CXCL10", "IFNG"),
  EPIGENETIC_SMOKE = c("DUSP13B", "ACTB", "GAPDH")
)

gsva_namespace <- asNamespace("GSVA")
if (exists("ssgseaParam", envir = gsva_namespace, inherits = FALSE)) {
  param <- GSVA::ssgseaParam(expr, gene_sets)
  scores <- GSVA::gsva(param, verbose = FALSE)
} else {
  scores <- GSVA::gsva(expr, gene_sets, method = "ssgsea", ssgsea.norm = TRUE, verbose = FALSE)
}

score_df <- data.frame(gene_set = rownames(scores), as.data.frame(scores), check.names = FALSE)
utils::write.table(
  score_df,
  file = file.path(out_dir, "gsva_smoke_scores.tsv"),
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

audit_lines <- c(
  "# Portable R Runtime Smoke Audit",
  "",
  "Status: passed",
  paste0("R version: ", R.version.string),
  paste0("Output directory: ", normalizePath(out_dir, mustWork = FALSE)),
  "",
  "Generated files:",
  "- `r_package_versions.tsv`",
  "- `limma_smoke_results.tsv`",
  "- `gsva_smoke_scores.tsv`"
)
writeLines(audit_lines, con = file.path(out_dir, "runtime_smoke_audit.md"))

cat("portable_r_smoke_ok\n")
