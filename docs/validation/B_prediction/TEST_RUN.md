# B-P1 parent synthetic test receipt

**Purpose:** `synthetic-test`. These checks validate local software behavior only. They do not validate biology, TCGA fitting, CPC-GENE prediction, an eligible population, or AIU numerical identity.

Working directory: `E:\Master_Thesis\master-thesis`

## Final suite

```text
C:\Users\salma\AppData\Local\Programs\Python\Python312\python.exe -m py_compile tools/b_prediction/__init__.py tools/b_prediction/__main__.py tests/b_prediction/test_bprediction.py
C:\Users\salma\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests/b_prediction -v
```

Result: syntax check exit 0. The final combined Paper B gate passed B-F1 **19 tests in 7.252 seconds** and B-P1 **16 tests in 51.822 seconds**, all exit 0. B-P1 test scratch was rooted at `tmp/b_prediction/final_combined_gate`.

The suite covers exact-byte bundle integrity, engine-code and patient-set locks, exact alpha ties, required scientific and evaluation lock fields, runtime-lock mismatch, the required sklearn fitting stack, failure propagation, no-refit evaluation, patient overlap, constant outcomes, same-mask paired metrics, and independent ridge/bootstrap numerical oracles.

## Final clean synthetic CLI

```text
python -m tools.b_prediction develop --contract tmp\b_prediction\cli_contract.json --development tests\b_prediction\fixtures\synthetic_development.tsv --output tmp\b_prediction\cli_develop_parent_clean
python -m tools.b_prediction evaluate --bundle tmp\b_prediction\cli_develop_parent_clean\bundle --evaluation-lock tmp\b_prediction\cli_evaluation_lock_parent_clean.json --external tests\b_prediction\fixtures\synthetic_external.tsv --output tmp\b_prediction\cli_eval_parent_clean
```

Both commands exited 0. Exact synthetic artifact identifiers:

- development patient-set hash: `937e799c5e0ec24bd1b5c47aec85769ccd8142061061b29328ebfeab25fe790e`
- engine-code SHA-256: `2c2006c951e6433f1d7f84cd912ac85eaa2732fdaddfeb83bae71654fc6bdec1`
- bundle SHA-256: `436e6050762bdd071636e2f492c74c1592397b9a5b252a1055dc908b55814534`
- evaluation-lock SHA-256: `7cd63877eaafbf1d9f4e057c8f9be8dc99e5c2987e51121252fa59cff3739dc4`
- external-table SHA-256: `e078906672a9be9d2c6ec0b7e43456c5a67389d70cc36fce073d8fcd0b9e5f37`
- evaluation SHA-256: `fa3a529d6e2ea4333402bfcb965f0eb6814d6567ec363b25ee6b9b4d58110ca3`

The five-row synthetic result was `R2_baseline=-0.14406131654263166`, `R2_extended=-0.1440952104395521`, `Delta_R2=-0.00003389389692038505`, with paired-bootstrap interval `[-0.0011988779044082142, 0.0017491812151372889]`; 3/2000 resamples were undefined. These numbers are test-fixture outputs, not biological estimates.

## Not run

- AIU B-P1: SSH timed out twice before authentication or any remote directory/job creation.
- Any scientific-mode run or real TCGA/CPC-GENE table.
