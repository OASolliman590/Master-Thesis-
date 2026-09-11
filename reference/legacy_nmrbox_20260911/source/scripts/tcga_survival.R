#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
arg_map <- list()
if (length(args) > 0) {
  for (i in seq(1, length(args), by = 2)) {
    key <- args[[i]]
    val <- args[[i + 1]]
    if (is.null(val)) { val <- "" }
    arg_map[[key]] <- val
  }
}

input_path <- arg_map[["--input"]]
out_stats_path <- arg_map[["--out-stats"]]
out_plot_path <- arg_map[["--out-plot"]]
project_name <- arg_map[["--project"]]
score_col <- arg_map[["--score-col"]]
group_col <- arg_map[["--group-col"]]

if (is.null(input_path) || is.null(out_stats_path) || is.null(out_plot_path)) {
  stop("Missing required arguments: --input, --out-stats, --out-plot")
}
if (is.null(project_name)) {
  project_name <- "TCGA"
}
if (is.null(score_col) || score_col == "") {
  score_col <- "signature_score_z"
}
if (is.null(group_col) || group_col == "") {
  group_col <- "signature_group"
}

suppressMessages(library(survival))
has_survminer <- requireNamespace("survminer", quietly = TRUE)

df <- read.table(input_path, header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# Ensure survival columns are numeric and drop NAs
df$OS.time <- as.numeric(df$OS.time)
df$OS <- as.numeric(df$OS)
df <- df[!is.na(df$OS.time) & !is.na(df$OS), ]

if (nrow(df) < 10) {
  stop("Not enough valid survival data points to run Cox/KM analysis.")
}

if (!(score_col %in% colnames(df))) {
  stop(sprintf("Missing score column for continuous Cox: %s", score_col))
}

# Ensure factor ordering so Hazard Ratio is High vs Low for KM plot only.
if (group_col %in% colnames(df)) {
  df[[group_col]] <- factor(df[[group_col]], levels = c("Low", "High"))
}

age_candidates <- c("age", "age_at_diagnosis", "age_years", "Age")
stage_candidates <- c("ajcc_pathologic_stage", "pathologic_stage", "clinical_stage", "tumor_stage", "stage")

age_cov <- NULL
for (cand in age_candidates) {
  if (cand %in% colnames(df)) {
    age_vals <- suppressWarnings(as.numeric(df[[cand]]))
    if (sum(!is.na(age_vals)) >= 10) {
      df$age_cov <- age_vals
      age_cov <- "age_cov"
      break
    }
  }
}

stage_cov <- NULL
for (cand in stage_candidates) {
  if (cand %in% colnames(df)) {
    stage_vals <- trimws(as.character(df[[cand]]))
    stage_vals[stage_vals == ""] <- NA
    if (sum(!is.na(stage_vals)) >= 10) {
      stage_fac <- factor(stage_vals)
      if (nlevels(droplevels(stage_fac)) >= 2) {
        df$stage_cov <- stage_fac
        stage_cov <- "stage_cov"
        break
      }
    }
  }
}

surv_obj <- Surv(time = df$OS.time, event = df$OS)
if (group_col %in% colnames(df)) {
  fit <- survfit(as.formula(paste0("surv_obj ~ ", group_col)), data = df)
} else {
  df$signature_group <- ifelse(df[[score_col]] >= median(df[[score_col]], na.rm = TRUE), "High", "Low")
  df$signature_group <- factor(df$signature_group, levels = c("Low", "High"))
  fit <- survfit(surv_obj ~ signature_group, data = df)
  group_col <- "signature_group"
}

# Continuous Cox Regression for prognostic framing
cox_terms <- c(score_col)
if (!is.null(age_cov)) {
  cox_terms <- c(cox_terms, age_cov)
}
if (!is.null(stage_cov)) {
  cox_terms <- c(cox_terms, stage_cov)
}

cox_formula <- as.formula(paste0("surv_obj ~ ", paste(cox_terms, collapse = " + ")))
cox <- coxph(cox_formula, data = df)
cox_sum <- summary(cox)

p_val <- cox_sum$sctest["pvalue"]
hr <- cox_sum$conf.int[1, "exp(coef)"]
lower_ci <- cox_sum$conf.int[1, "lower .95"]
upper_ci <- cox_sum$conf.int[1, "upper .95"]

# Write stats
out_stats <- data.frame(
  project = project_name,
  endpoint = "OS",
  model_type = "continuous_cox",
  score_column = score_col,
  model_covariates = paste(c("signature_score_z_continuous", if (!is.null(age_cov)) "age", if (!is.null(stage_cov)) "stage"), collapse = "+"),
  n_samples = nrow(df),
  hazard_ratio = hr,
  lower_95_ci = lower_ci,
  upper_95_ci = upper_ci,
  p_value = p_val
)
write.table(out_stats, file = out_stats_path, sep = "\t", row.names = FALSE, quote = FALSE)

png(out_plot_path, width = 6, height = 6, units = "in", res = 300)
if (has_survminer) {
  p <- survminer::ggsurvplot(
    fit,
    data = df,
    pval = TRUE,
    conf.int = FALSE,
    title = paste(project_name, "Survival by Signature (Prognostic)"),
    xlab = "Time (Days)",
    palette = c("#377EB8", "#E41A1C"),
    legend.title = "Signature",
    legend.labs = c("Low", "High"),
    risk.table = TRUE,
    ggtheme = ggplot2::theme_classic()
  )
  print(p)
} else {
  plot(
    fit,
    col = c("#377EB8", "#E41A1C"),
    lwd = 2,
    xlab = "Time (Days)",
    ylab = "Overall survival probability",
    main = paste(project_name, "Survival by Signature (Prognostic)")
  )
  legend("bottomleft", legend = c("Low", "High"), col = c("#377EB8", "#E41A1C"), lwd = 2, bty = "n")
  logrank_p <- NA_real_
  if (group_col %in% colnames(df)) {
    sd <- survdiff(as.formula(paste0("surv_obj ~ ", group_col)), data = df)
    logrank_p <- pchisq(sd$chisq, df = length(sd$n) - 1, lower.tail = FALSE)
  }
  mtext(sprintf("Log-rank p = %s", ifelse(is.na(logrank_p), "NA", signif(logrank_p, 3))), side = 3, line = 0.2, cex = 0.8)
}
invisible(dev.off())
