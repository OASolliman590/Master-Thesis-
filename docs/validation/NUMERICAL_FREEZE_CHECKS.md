# Numerical freeze software checks

These checks use fixed synthetic inputs to compare software behavior. They
are not biological validation.

## Command and environment

```sh
python -m pytest -q -rs tests/freeze_audit/test_software_checks.py
```

Result: `1 passed`. Pytest marks the test `requires_r`; the test calls the
committed R script through `tools.r_bridge.run_r` and does not skip when R is
unavailable. Root seed: `20261102`. The R bridge recorded R `4.6.1` and
Bioconductor `3.23`.

Package versions: `BiocManager 1.30.27`, `BiocParallel 1.46.0`,
`fgsea 1.38.0`, `glmnet 5.2`, `jsonlite 2.0.0`, and `singscore 1.32.0`.

## Results

| Check | Seed or setting | Result |
|---|---:|---:|
| glmnet `jerr` | 20261102 | 0 |
| glmnet `npasses` | 20261102 | 14 |
| glmnet vs direct optimizer, max coefficient difference | tolerance 1e-6 | 2.2756113e-7 |
| glmnet maximum KKT residual | tolerance 1e-6 | 2.1866548e-9 |
| glmnet single lambda vs lambda path, max coefficient difference | tolerance 1e-6 | 6.9168659e-9 |
| fgsea repeated run, maximum numeric difference | seed 20261104 | 0 |
| fgsea `nproc = 1` vs `nproc = 2`, maximum numeric difference | seed 20261104 | 0 |
| fgsea different-seed maximum numeric difference | seed 20261105 | 0.0953073 |
| singscore score independent of seed | 20261106 vs 20261206 | true |
| singscore changes when rank background changes | all mapped expression rows vs first 12 rows | true |
| singscore changes when direction arguments change | `upSet`, `downSet`, `knownDirection` | true |
| singscore changes when centering changes | `centerScore` | true |

The glmnet call uses the draft's binomial ridge settings: `alpha = 0`,
`lambda = 0.1`, `standardize = FALSE`, `intercept = TRUE`,
`thresh = 1e-10`, and `maxit = 1e6`. Its synthetic input has 300 rows and four
predictors. The direct optimizer minimizes mean logistic loss plus the ridge
penalty. Any nonzero `jerr`, optimizer nonconvergence, or checked difference
above `1e-6` fails the test.

The fgsea fixture has 500 ranked genes and four fixed gene sets. It checks a
same-seed repeat, process counts 1 and 2, and a second seed. The script sets
`options(ports = 32567)` because the managed runner cannot use BiocParallel's
default port scan.

The singscore fixture has 30 genes and 12 samples. The rank background is all
mapped expression rows passed to `rankGenes`; direction uses `upSet`,
`downSet`, and `knownDirection`; centering is controlled by `centerScore`.
Singscore does not use a random seed for these scores.
