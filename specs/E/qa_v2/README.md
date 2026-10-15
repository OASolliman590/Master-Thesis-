# V2 specification reference QA

Run from the distribution root: `python specs/E/qa_v2/run_checks.py`.

These are declared-contract/schema checks, **not** production E0–E7/X0–X5 implementation, ODE tests or scientific validation. `fixture_mode=True` exists solely for the synthetic examples; the normal path rejects synthetic releases. Even a fully satisfied declared contract returns eligible-for-review, never scientific authorisation. A future production auditor must actually resolve hashes, permissions, data provenance, independent units and scientific reviews.

The suite enumerates 4,096 combinations of 12 selected interacting capability flags; this is not a probability model and is not a claim to exhaust every possible experiment. It separately tests unknown states, permission/QC, role/freeze boundaries, one-donor limits and result-sign nonselection. The same 42 tests are included in both standalone distributions for independence checking; repeated passes are not independent scientific validation or distinct test cases.

The local SHA-256 helper detects a changed byte-level fixture. It does not prove an external timestamp/witness, clinical validity, licence or institutional approval. No real model-fit held-out-isolation test has run; only declaration-input noninterference is tested here.

`run_checks.py` records fresh local test results and environment versions. No network or real experimental data is accessed. Exact dependencies are listed in `requirements.lock.txt`; this lock describes the checked environment, not a final production pharmacometric backend.
