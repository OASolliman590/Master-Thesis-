# B-F1 Standards review

Reviewed the **staged** nine-file diff against `43efda19bff062a2e9e140fadd84ab32c88cee71`, not HEAD. Standards: AGENTS.md, CONTEXT.md, issue-tracker.md, M1_ASTRA_DISPOSITION.md B-F1 release and B_F1_INITIAL_ROOT_REVIEW.md. Read-only inspection; no tests or network calls by this reviewer. Root reports 14 tests passed locally on Python 3.12; Python 3.11/AIU verification remains pending.

## Documented-standard breaches

1. **P2 — output creation is not atomically exclusive.** `tools/b_formats/__main__.py:549` uses `os.replace(temp_name, path)` after an earlier existence check. Two inspectors targeting the same initially absent output can both pass validation; the later writer then overwrites the first successful summary. This violates the initial review's requirement to “define atomic existing-output behavior that prevents stale success attribution” (`docs/reviews/B_F1_INITIAL_ROOT_REVIEW.md:18`). Publish with a no-clobber atomic operation, fail if the destination appeared, and test the collision. A second pre-write existence check alone still races.

2. **P2 — the checksum need not describe the inspected bytes.** `tools/b_formats/__main__.py:582–583` hashes the input, closes it, then separately reopens it for parsing; byte size is obtained earlier again. If a source is replaced/updated during this interval, the summary can attest the supplied hash while counting different bytes. The release requires “Full hashed input bytes are checked” and checksummed summaries (`M1_ASTRA_DISPOSITION.md`, B-F1 release). Hash, measure and decode the same acquired byte snapshot, or detect source changes and reject before publication; add a deterministic changed-input regression. This is a conditional integrity defect, not evidence that the current fixtures changed.

## Optional smell

**Possible duplicated source of truth:** `tests/b_formats/test_bf1_cli.py:95` hardcodes fixture paths/hashes and expected results also stored in `docs/validation/B_formats/{fixture_manifest,real_summaries_expected}.json`. Drift is already visible: the latter expects CPC `value_columns`, which the implementation does not emit and tests do not assert. Load the reviewed manifests or clearly designate one authoritative oracle and verify consistency.

Imports are Python-3.11-compatible stdlib; ownership and scientific-scope restrictions are respected by the reviewed diff. Parent biological gates remain closed.

**Totals:** 2 standards findings; 1 optional smell. Both findings concern conditional provenance integrity.
