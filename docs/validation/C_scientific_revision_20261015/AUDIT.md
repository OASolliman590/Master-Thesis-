# Paper C scientific-revision validation audit

**Validation date:** 2026-10-15  
**Baseline:** `a8278c776da7c6b096cc14139d729979db286b50`  
**Scope:** documentation, contracts, schemas, synthetic fixtures and review pointers only. No perturbation outcome, model fit, candidate ranking or wet-lab result was generated.

## Environment

- Python: 3.13.5
- `jsonschema`: 4.26.0
- Test runner: standard-library `unittest`
- Schema dialect: JSON Schema Draft 2020-12

## Red-to-green record

Initial command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest specs/C/revision_20261015/tests/test_revision_contracts.py -v
```

The initial run executed 10 tests and produced one failure: the revision README linked to this audit before the audit file existed. The package was corrected by adding the audit and package-hash manifest. No scientific rule was weakened.

## Final verification

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest specs/C/revision_20261015/tests/test_revision_contracts.py -v
```

Result: **10 tests passed, 0 failures, 0 errors, 0 skips** (`Ran 10 tests in 0.062s`, final fresh run).

The suite checks:

- required package files;
- JSON Schema validity and fixture conformance;
- approved versus proposed decision states;
- unique source/decision identifiers;
- explicit `UNKNOWN` source counts;
- paired endpoint and biological-unit wording;
- equal query budgets/no padding/leakage boundaries;
- C1 demotion and no comparative-efficacy claim;
- absence of biological-completion claims;
- relative link resolution;
- unresolved-question preservation.

## Hashes

`PACKAGE_HASHES.tsv` contains SHA-256 and byte counts for all substantive changed files generated before this receipt. It intentionally excludes itself and this audit to avoid circular self-hashing.

## Claim ceiling

Passing these tests establishes internal documentation/schema consistency only. It does not validate source eligibility, numerical scorer parity, biological truth, translational feasibility or publication readiness.
