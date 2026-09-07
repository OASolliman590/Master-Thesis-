# B-P1 handoff — parent-accepted local software checkpoint

**Disposition, 7 September 2026:** accepted for the bounded local synthetic software checkpoint. This is not a scientific release: no TCGA/CPC-GENE cohort table was fitted or evaluated, no biological result is claimed, and no real scientific lock was created.

## Implemented boundary

- `develop` accepts a validated numeric patient table and an explicit contract, performs TCGA-side nested ridge development, and freezes a deterministic numeric bundle.
- `evaluate` consumes only that frozen bundle, an exact evaluation lock, and a validated external table. It contains no fitting path.
- Bundle integrity includes the exact raw `checksums.json` byte hash, the development patient-set hash, and the exact engine-source hash.
- Scientific mode requires explicit decision, reviewer, eligibility, universe, promoter-set, feature, external-population, precision, and runtime locks. Tests use dummy values only; the software supplies no scientific defaults.
- Development uses the required private `Pipeline` / `ColumnTransformer` / `StandardScaler` / `VarianceThreshold(0.0)` / `GridSearchCV` stack. Selection uses strict mean-MSE ordering and only exact equality invokes the larger-alpha tie rule.
- Independent closed-form ridge and PCG64 paired-bootstrap oracles cover the numerical paths; an induced single-candidate fit failure proves `error_score="raise"` behavior.

## Parent verification

Local Python 3.12.10 syntax checks and the final combined Paper B gate passed: B-F1 **19 tests in 7.252 seconds** and B-P1 **16 tests in 51.822 seconds**, all exit 0. A clean synthetic B-P1 `develop` and `evaluate` also both exited 0.

- engine SHA-256: `2c2006c951e6433f1d7f84cd912ac85eaa2732fdaddfeb83bae71654fc6bdec1`
- test-module SHA-256: `a57da3e782e5514e4fdb224a9291c8b183e20af80bf283759b7012d69217fad3`
- synthetic bundle SHA-256: `436e6050762bdd071636e2f492c74c1592397b9a5b252a1055dc908b55814534`
- synthetic evaluation-lock SHA-256: `7cd63877eaafbf1d9f4e057c8f9be8dc99e5c2987e51121252fa59cff3739dc4`
- synthetic evaluation SHA-256: `fa3a529d6e2ea4333402bfcb965f0eb6814d6567ec363b25ee6b9b4d58110ca3`

See `TEST_RUN.md`, `ENVIRONMENT.md`, and `PARENT_VERIFICATION.md` for the commands, environment, delegation receipt, and limits.

## Pending

- AIU B-P1 numerical verification: connection to `10.55.205.205:22` timed out twice before authentication or remote-state creation. No B-P1 scratch directory or job was created by these attempts.
- All real-cohort work remains blocked by the unresolved E1–E4/E6 and B-I1/B-I2 scientific inputs and approvals.
