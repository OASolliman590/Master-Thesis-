# Pinned R environment

Restore the project library with:

```sh
Rscript -e 'renv::restore(project="r")'
```

The R version and package versions are pinned in `renv.lock` (R 4.6.1,
Bioconductor 3.23). `r/.Renviron` points the renv library and cache to
`~/.local/share/thesis-envs/r-renv/` so they stay off the exFAT worktree.
The bridge runs from `r/`, points `R_ENVIRON_USER` and `R_PROFILE_USER` at this
project, and clears inherited `R_LIBS*` overrides. It checks that renv activated
this project and that its library is first in `.libPaths()` before each script.

To add a package, install it in this project with `renv::install("package")`,
reference it from the R code, then update the lockfile with
`renv::snapshot(project="r")` after review.
