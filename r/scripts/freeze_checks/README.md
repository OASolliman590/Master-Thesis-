# Numerical-freeze software checks

`software_checks.R` is the fixed synthetic check for the draft numerical
freeze. Run it through the repository R bridge and locked `renv` project:

```sh
python -m pytest -q tests/freeze_audit/test_software_checks.py
```

The Python test calls `tools.r_bridge.run_r`; it does not skip when R is
unavailable. The script generates its synthetic inputs from fixed formulas and
seeds, writes only aggregate check values, and records R/package versions via
the bridge manifest.

The root seed is `20261102`. `glmnet` uses that seed, `fgsea` uses `20261104`
for repeated and process-count comparisons and `20261105` for its second-seed
check, and the seed-independence probe uses `20261106` and `20261206`.

The `fgsea` check compares `nproc = 1` and `nproc = 2` using the same local
BiocParallel worker setup. `options(ports = 32567)` supplies the manager port
directly because the managed runner does not permit BiocParallel's default
port scan. It does not change the ranking, pathway memberships, seed, or
fgsea scoring method.

The `glmnet` check compares the draft's ridge call with a directly optimized
mean logistic loss plus the ridge penalty, checks the maximum KKT residual at
`1e-6`, records `jerr` and `npasses`, and compares one lambda with a three-value
lambda path. The singscore check compares seeded repeats and demonstrates the
effects of the rank background, `upSet`/`downSet` plus `knownDirection`, and
`centerScore`.
