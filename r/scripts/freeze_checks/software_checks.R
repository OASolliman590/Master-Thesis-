source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager", "glmnet", "fgsea", "singscore"))
bridge <- bridge_config()
cfg <- bridge$config
out_dir <- bridge$output_dir

required_seed <- as.integer(cfg$seed)
if (length(required_seed) != 1L || is.na(required_seed)) {
  stop("A fixed integer seed is required")
}

glmnet_seed <- required_seed
set.seed(glmnet_seed)
n <- 300L
p <- 4L
x <- matrix(stats::rnorm(n * p), nrow = n, ncol = p)
truth <- c(0.6, -0.4, 0.2, 0.7)
y <- stats::rbinom(n, size = 1L, prob = stats::plogis(-0.2 + x %*% truth))
lambda <- 0.1
fit <- glmnet::glmnet(
  x, y, family = "binomial", alpha = 0, lambda = lambda,
  standardize = FALSE, intercept = TRUE,
  control = list(thresh = 1e-10, maxit = 1e6)
)
glmnet_coef <- as.numeric(stats::coef(fit, s = lambda))

objective <- function(par) {
  eta <- par[[1L]] + drop(x %*% par[-1L])
  mean(pmax(eta, 0) + log1p(exp(-abs(eta))) - y * eta) +
    lambda * sum(par[-1L]^2) / 2
}
gradient <- function(par) {
  eta <- par[[1L]] + drop(x %*% par[-1L])
  residual <- stats::plogis(eta) - y
  c(mean(residual), drop(crossprod(x, residual)) / n + lambda * par[-1L])
}
direct <- stats::optim(
  par = rep(0, p + 1L), fn = objective, gr = gradient,
  method = "BFGS", control = list(reltol = 1e-13, maxit = 100000L)
)
kkt <- max(abs(gradient(glmnet_coef)))
direct_max_difference <- max(abs(glmnet_coef - direct$par))
glmnet_jerr <- as.integer(fit$jerr)
glmnet_npasses <- as.integer(fit$npasses)

path <- glmnet::glmnet(
  x, y, family = "binomial", alpha = 0, lambda = c(0.3, 0.1, 0.03),
  standardize = FALSE, intercept = TRUE,
  control = list(thresh = 1e-10, maxit = 1e6)
)
path_coef <- as.numeric(stats::coef(path, s = lambda))
path_max_difference <- max(abs(glmnet_coef - path_coef))

fgsea_seed <- required_seed + 2L
# BiocParallel's default port probe is unavailable in the managed runner.
options(ports = 32567L)
genes <- sprintf("G%04d", seq_len(500L))
statistics <- sin(seq_len(500L) / 13) + cos(seq_len(500L) / 29) +
  seq_len(500L) / 5000
names(statistics) <- genes
pathways <- list(
  H_SET_A = genes[1:35],
  H_SET_B = genes[71:123],
  H_SET_C = genes[201:254],
  H_SET_D = genes[401:447]
)
run_fgsea <- function(seed, nproc) {
  set.seed(seed)
  as.data.frame(fgsea::fgseaMultilevel(
    pathways = pathways,
    stats = statistics,
    minSize = 15L,
    maxSize = 100L,
    eps = 0,
    nproc = nproc
  ))
}
fgsea_one <- run_fgsea(fgsea_seed, 1L)
fgsea_repeat <- run_fgsea(fgsea_seed, 1L)
fgsea_parallel <- run_fgsea(fgsea_seed, 2L)
fgsea_other_seed <- run_fgsea(fgsea_seed + 1L, 1L)
numeric_columns <- c("pval", "padj", "ES", "NES", "log2err")
fgsea_order <- function(value) value[order(value$pathway), c("pathway", numeric_columns), drop = FALSE]
fgsea_one <- fgsea_order(fgsea_one)
fgsea_repeat <- fgsea_order(fgsea_repeat)
fgsea_parallel <- fgsea_order(fgsea_parallel)
fgsea_other_seed <- fgsea_order(fgsea_other_seed)
max_numeric_difference <- function(left, right) {
  delta <- abs(as.matrix(left[, numeric_columns, drop = FALSE]) -
                 as.matrix(right[, numeric_columns, drop = FALSE]))
  if (all(is.na(delta))) return(NA_real_)
  max(delta, na.rm = TRUE)
}
fgsea_repeat_diff <- max_numeric_difference(fgsea_one, fgsea_repeat)
fgsea_nproc_diff <- max_numeric_difference(fgsea_one, fgsea_parallel)
fgsea_seed_diff <- max_numeric_difference(fgsea_one, fgsea_other_seed)

score_seed <- required_seed + 4L
gene_count <- 30L
sample_count <- 12L
expression <- outer(seq_len(gene_count), seq_len(sample_count), function(i, j) {
  sin(i * j / 5) + cos(i + j / 3) + i * j / 100
})
rownames(expression) <- sprintf("S%03d", seq_len(gene_count))
colnames(expression) <- sprintf("sample_%03d", seq_len(sample_count))
signature <- rownames(expression)[1:8]
ranked_all <- singscore::rankGenes(expression, tiesMethod = "min")
set.seed(score_seed)
score_seed_a <- singscore::simpleScore(
  ranked_all, upSet = signature, knownDirection = TRUE, centerScore = FALSE
)$TotalScore
set.seed(score_seed + 100L)
score_seed_b <- singscore::simpleScore(
  ranked_all, upSet = signature, knownDirection = TRUE, centerScore = FALSE
)$TotalScore
ranked_background <- singscore::rankGenes(expression[1:12, , drop = FALSE], tiesMethod = "min")
score_background <- singscore::simpleScore(
  ranked_background, upSet = signature, knownDirection = TRUE, centerScore = FALSE
)$TotalScore
opposite_signature <- rownames(expression)[9:16]
score_direction_up <- singscore::simpleScore(
  ranked_all, upSet = signature, downSet = opposite_signature,
  knownDirection = TRUE, centerScore = FALSE
)$TotalScore
score_direction_down <- singscore::simpleScore(
  ranked_all, upSet = opposite_signature, downSet = signature,
  knownDirection = TRUE, centerScore = FALSE
)$TotalScore
score_centered <- singscore::simpleScore(
  ranked_all, upSet = signature, knownDirection = TRUE, centerScore = TRUE
)$TotalScore
singscore_seed_independent <- isTRUE(all.equal(score_seed_a, score_seed_b, tolerance = 0))
singscore_background_changes <- any(abs(score_seed_a - score_background) > 1e-12)
singscore_direction_changes <- any(abs(score_direction_up - score_direction_down) > 1e-12)
singscore_centering_changes <- any(abs(score_seed_a - score_centered) > 1e-12)

checks <- data.frame(
  check = c(
    "glmnet_seed", "glmnet_jerr", "glmnet_npasses", "glmnet_direct_max_difference",
    "glmnet_kkt_max_residual", "glmnet_lambda_path_max_difference",
    "fgsea_seed", "fgsea_repeat_max_difference", "fgsea_nproc_1_vs_2_max_difference",
    "fgsea_different_seed_max_difference", "singscore_seed", "singscore_seed_independent",
    "singscore_background_changes_score", "singscore_direction_changes_score",
    "singscore_centering_changes_score", "singscore_background",
    "singscore_direction_arguments", "singscore_centering_argument"
  ),
  value = c(
    glmnet_seed, glmnet_jerr, glmnet_npasses, direct_max_difference, kkt,
    path_max_difference, fgsea_seed, fgsea_repeat_diff, fgsea_nproc_diff,
    fgsea_seed_diff, score_seed,
    singscore_seed_independent,
    singscore_background_changes,
    singscore_direction_changes,
    singscore_centering_changes,
    "all mapped expression rows passed to rankGenes",
    "upSet, downSet, knownDirection",
    "centerScore"
  ),
  stringsAsFactors = FALSE
)

if (glmnet_jerr != 0L || direct$convergence != 0L ||
    direct_max_difference > 1e-6 || kkt > 1e-6 || path_max_difference > 1e-6) {
  stop("glmnet objective, KKT, convergence, or path check failed")
}
if (!is.finite(fgsea_repeat_diff) || fgsea_repeat_diff > 1e-12 ||
    !is.finite(fgsea_nproc_diff) || fgsea_nproc_diff > 1e-8 ||
    !is.finite(fgsea_seed_diff) || fgsea_seed_diff <= 1e-12) {
  stop("fgsea seed or process-count check failed")
}
if (!singscore_seed_independent || !singscore_background_changes ||
    !singscore_direction_changes || !singscore_centering_changes) {
  stop("singscore seed or scoring-argument check failed")
}

utils::write.table(
  checks, file.path(out_dir, "checks.tsv"), sep = "\t", row.names = FALSE,
  col.names = TRUE, quote = FALSE, na = "NA"
)
bridge_write_session(out_dir)
