# Process simplification for Paper A, 18 November 2026

User-approved administrative decision, recorded from chat ("Simplify items 2, 5, 6", 18 Nov 2026), after the read-only simplify review (private notes, outside Git). No scientific design changes, no signature and no release. Signed specifications, amendments and the numerical freeze are unchanged.

| Item | Decision | Replaces | Risk accepted |
| --- | --- | --- | --- |
| 2. Test gate | The full suite runs once, with `THESIS_RUNTIME` pointed at an empty folder (`python -m tools.gate tests`). Module tests only while working. | Two full runs, `THESIS_RUNTIME` set and unset (about 73 min each). | A defect that appears only with the variable unset. The second mode never found one: its only one-mode failure (8 Nov) was a random-order fixture. Tests that depend on the variable set or clear it themselves. |
| 5. Exposure-log scope | `DEVIATIONS.md` covers reads of real thesis cohort data only. Published reference examples and invented fixtures are not exposure. Restored to the gate: `tests/a_meta/test_meta_rma_r.py::test_meta_rma_normand1999_and_two_stage_equal_weight_real_variance` and `tests/a_cohorts/test_loader.py::test_admitted_product_bundle_digest_detects_tampering`. | Deselecting both tests in Cycle 01 (`specs/A/cycles/01-a-p2-release-prep/DEVIATIONS.md`, which stays as a historical record). | None to validity; both tests protect it (meta-analysis known answer, tamper detection). |
| 6. Paperwork | One gate-written receipt per merge (outside Git). In Git, per ticket: `spec.md` and `review.md`, plus `DEVIATIONS.md` only when needed. Rules live in `docs/process/HARD_RULES.md`, and briefs link to it. A scripted privacy scan of staged files (`python -m tools.gate privacy`). | Per-step source snapshots and acceptance JSONs; `plan.md`, `tasks.md` and `TRANSFER.md` per cycle; rules pasted into every brief; manual privacy receipts. | Less step-by-step provenance between merges; the merge receipt, Git history and review record remain. This supersedes the Spec Kit four-file cycle layout of `CLEANUP_AND_PAPER_THREADS_APPROVED_20261116.md` for Paper A. |

Verification on 18 Nov 2026, on an isolated copy of the commit:
- The restored tests passed.
- With the hash check disabled and the meta-analysis switched from REML to DL (deliberate breaks), both failed, and the gate exited 1.
- The full one-mode gate result is in the private merge receipt.
