# B-F1 integration disposition

6 September 2026. **Reviewed WIP; ticket remains open.** Spark implemented the released format-only slice; Astra inspected and corrected the candidate, exercised regression tests, and integrated separate Standards and Spec reviews. This is not completion of Paper B or approval of a scientific primary.

## Findings resolved

- Input length, SHA256 and parsing now describe one immutable byte snapshot. A deterministic filesystem-boundary regression reproduced the previous mismatch before the fix.
- Completed JSON publication refuses a concurrent destination. Windows rename and POSIX hard linking are the selected platform operations; unsupported operations fail without an overwriting fallback. The collision regression reproduced the old overwrite before the fix. POSIX execution remains pending.
- STAR structural blanks are limited to normalized fields in its four recognized summary records; empty counts and unknown summary identifiers fail. Blank-record diagnostics identify the actual row.
- CPC methylation rejects header-only files; detection-P diagnostics are distinct from beta diagnostics. The summary emits all expected fields, and tests consume the reviewed expected-field contract.
- Both retained CPC text prefixes were independently re-derived byte-for-byte from their respective 256,000-byte compressed prefixes. The expression-parent hash was corrected; the later 24MB target audit is a different artifact.
- Synthetic STAR summary values now match the documented structural absence. The final Spec recheck's swapped-header fixture was corrected to contain all four assay values. Its exact affected test passed again in 0.570 seconds; no parser change followed the 19-test run.

## Verification evidence

The full local Python 3.12 suite passed 19 tests in 7.638 seconds before the final one-line test-fixture correction. The affected test then passed independently. Four separate real-format CLI runs passed and have actual summaries, commands, input lengths/checksums, code/contract hashes and output hashes in `docs/validation/B_formats/local_20260906/`. Both recheck reviewers independently matched all five recorded code/contract hashes and four summary hashes. Their checks are static receipt verification, not additional test execution.

Real fixtures remain outside Git. Synthetic fixtures test software behaviour and provide no biological evidence. No score, methylation association, drug ranking, patient join or model was run.

## Opus review and corrections to its report

The substantive first Opus review through Antigravity is preserved verbatim in `B_F1_OPUS_RAW.md`. It requested changes; its valid findings are resolved above. Its downgrade of the two integrity races is not accepted: actual deterministic regressions demonstrated contract violations.

Three reviewer statements are not facts: Python hard links are not POSIX-only (the local E: filesystem separately rejected them); the retained CPC expression fixture did not derive from the later 24MB audit; and Python `str.splitlines()` does not leave bare CR record separators intact. No change is justified by those assertions.

The first headless attempt ended at a denied terminal call and did not deliver a review. A resumed direct-file review did. The final recheck attempt returned exit 0 with only an acknowledgement, but its log shows `RESOURCE_EXHAUSTED`/429. Therefore **final Opus recheck remains incomplete**. No credits or subscription changes were made. Receipt metadata preserves this distinction without publishing raw CLI/network logs.

The substantive resumed review's relay reports `readOnlyViolation: true`: the shared checkout changed while Astra was correcting the candidate. The fingerprint flag alone cannot attribute edits to Opus. Preserve it as a concurrent-work limitation; do not claim an isolated immutable review snapshot for that run. Later Standards/Spec rechecks examined the updated staged candidate.

## Remaining gates and release decision

AIU SSH timed out on the latest attempt; no remote B-F1 job started. Last verified AIU state is clean M1 `43efda19bff062a2e9e140fadd84ab32c88cee71`. Python 3.11 tests, the POSIX output branch and four real-format checks on AIU remain pending. Resume Opus final recheck when its quota is available. `pending_validation.json` records exact next actions.

Astra approves a clearly labelled WIP backup under the user's interrupted-milestone authorization. Do not close issue #5, tag this validated, release a dependent scientific analysis, or represent the final Opus check as passed. The approved AGENTS.md and fleet setup remain in force; no repeat permission is needed.
