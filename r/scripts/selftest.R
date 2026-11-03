source("R/bridge.R")
bridge_require(c("jsonlite", "BiocManager"))
config <- bridge_config()

counts <- read.delim(config$inputs$counts, check.names = FALSE, row.names = 1)
sums <- colSums(counts)
result <- data.frame(sample = names(sums), sum = unname(sums))
write.table(
  result,
  file = file.path(config$output_dir, "sums.tsv"),
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)
bridge_write_session(config$output_dir)
