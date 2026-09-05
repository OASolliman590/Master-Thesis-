# B-F1 Spec review

Fixed base `43efda19bff062a2e9e140fadd84ab32c88cee71`; reviewed staged candidate, with no unstaged differences in the owned paths. **Changes required.** No production files edited.

1. **[P1] Hash and parsed bytes can differ.** Requirement: “actual local input bytes before parsing” (`specs/B/TICKETS_AND_TESTS.md:30`). `tools/b_formats/__main__.py:579–583` stats, hashes, then reopens the pathname. A deterministic synthetic replacement between hash and parsing produced a successful two-row summary bearing the original one-row file's hash. Parse the same byte snapshot that was hashed; obtain its length from that snapshot.

2. **[P1] Concurrent output creation is overwritten.** Requirement: “refuse any existing output path … and preserve it” (`planning/delegation_runs/B_F1_spark_delta.txt`, item 3). The precheck at `tools/b_formats/__main__.py:94–106` does not protect `os.replace` at line 549. Injecting another completed output after validation resulted in exit 0 and replacement of that output. Publication must atomically refuse a competing destination, preserving its contents.

3. **[P2] STAR structural blanks are over-permitted.** Requirement: “Validate the documented summary-row schema separately” (delta item 1); initial review specifies populated count fields. `tools/b_formats/__main__.py:198–214` accepts blank raw-count fields and arbitrary `N_` identifiers. A summary row with all six numeric fields empty succeeds. Restrict structural blanks to documented normalized-expression columns and recognize the supported summary records.

4. **[P2] CPC methylation header-only input succeeds.** Requirement: “Reject empty/header-only input” (delta item 5). `tools/b_formats/__main__.py:362–435` lacks the data-row guard; a valid assay header alone produces exit 0, zero rows and a completed artifact. Add this missing adversarial case.

5. **[P2] Incorrect parent provenance.** Requirement: “local hash and parent compressed-prefix hash required” (`TICKETS_AND_TESTS.md:36`). `docs/validation/B_formats/fixture_manifest.json:21–22` associates the 194-row expression fixture with the later 24 MB audit. `docs/research/B_readiness/fetch_log.json:129–135` identifies its actual parent: 256,000 bytes, SHA256 `ccb85485c521a3e02d8fd0d9edb5e15f096d9726a486da67f2e24e24b4b7099c`.

6. **[P2] Portable run documentation missing.** Requirement: “Explicitly document the portable Linux command and Windows temporary-root option” (delta paragraph 2). The staged delivery has no run guide; `tests/b_formats/test_bf1_cli.py:23–25` implements `BF1_TEST_TMP_ROOT` without documenting invocation or local-versus-AIU status.

Evidence: four tiny synthetic probes under the authorized temporary root, Python 3.12, subprocess timeout 10 seconds; all reproduced the stated behaviours. Parent-reported 14 passing tests do not cover these cases. AIU/Python 3.11 remain pending.
