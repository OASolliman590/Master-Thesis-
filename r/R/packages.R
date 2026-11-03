# Explicit package references keep renv's implicit dependency record complete.
requireNamespace("jsonlite", quietly = TRUE)
requireNamespace("BiocManager", quietly = TRUE)
requireNamespace("metafor", quietly = TRUE)
requireNamespace("DESeq2", quietly = TRUE)
requireNamespace("limma", quietly = TRUE)
requireNamespace("fgsea", quietly = TRUE)
requireNamespace("msigdbr", quietly = TRUE)
requireNamespace("singscore", quietly = TRUE)
requireNamespace("Seurat", quietly = TRUE)
requireNamespace("SeuratObject", quietly = TRUE)
requireNamespace("qs2", quietly = TRUE)
requireNamespace("muscat", quietly = TRUE)
requireNamespace("immunedeconv", quietly = TRUE)

# Keep the already-locked recommended R packages visible to renv as well.
requireNamespace("foreign", quietly = TRUE)
requireNamespace("rpart", quietly = TRUE)
requireNamespace("spatial", quietly = TRUE)
