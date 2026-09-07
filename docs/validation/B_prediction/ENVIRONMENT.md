# B-P1 environment receipt

## Verified local synthetic environment

Recorded 7 September 2026 for `purpose=synthetic-test`:

- Python 3.12.10
- NumPy 2.5.2
- SciPy 1.18.1
- scikit-learn 1.9.0
- threadpoolctl 3.6.0
- thread limits: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`

These imported versions describe the local test environment; they are not an approved scientific runtime lock.

## AIU status

The intended AIU interpreter is Python 3.11.16. Two SSH attempts to `10.55.205.205:22` timed out before authentication, so B-P1 was not copied or executed and no remote scratch directory or job was created by these attempts. AIU numerical verification is pending; it is not passed or failed.

No TCGA or CPC-GENE cohort table was accessed.
