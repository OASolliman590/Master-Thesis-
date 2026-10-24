# Prat synthetic two-reader walkthrough

**Invented form walkthrough complete; real-source approvals remain pending.** This exercises the proposed Prat procedure for `A_BASELINE_BIO` using three wholly invented cases. No Prat source object, patient record, sample header or molecular value was read. No biological calculation, score, model or analysis was run.

Two separately dispatched agents received the same [casebook](CASEBOOK_V1.json), [form](FORM_V1.json) and [training policy](POLICY_V1.json). Their hashes were fixed in [BASIS_LOCK.json](BASIS_LOCK.json) before dispatch. Each was instructed to read only these materials and write to its own directory without seeing the peer's work. Both self-reported no peer access and sealed their first pass before the parent opened either pass for comparison. [Dispatch record](DISPATCH.json), [comparison opening](COMPARISON_OPEN.json).

These are synthetic-process controls and self-reports, not authenticated proof of real reader independence, qualifications or appointments. The reader labels and all case IDs are invented. The exercise does not appoint the agents to actual Prat review.

## Observed results

| Invented case | Retained finding |
|---|---|
| Ambiguous lexical alias | Distinct aliases remain distinct; an unsupported normalized label cannot establish the assay/person/specimen join. |
| Different specimen/outcome episodes | The explicit episode bindings are retained. A same-person legacy proposal cannot transfer the outcome across episodes; native endpoint meaning remains unknown. |
| Equal legacy table bytes | Equality does not resolve the competing hypothetical episode interpretations. No actual reader disagreement was fabricated from those casebook alternatives. |

Each reader assessed all seven existing questions for each case. All **21 paired assessments used the same disposition codes**. Their prose and citation scope differed; the parent inspected every assertion against the invented lines and found consistent scoped findings. This is an observation from this toy exercise, not an agreement statistic, reliability estimate, semantic certification or admission decision. [Reader A](reader_a/first_pass.json), [Reader B](reader_b/first_pass.json), [parent comparison](COMPARISON.json). Both original passes and their seals remain intact.

The pilot exposed [four instruction clarifications](FORM_CLARIFICATIONS.md): distinguish unsupported proposals from source assertions; bound grouped support to its stated proposition; allow citations for explicit scoped absence; and distinguish hypothetical alternatives from reader disagreement. These proposed clarifications have not been repiloted. They do not change frozen rules or establish runtime defects.

Separately, the unchanged existing synthetic protocol test file passed **33 tests**. It includes changed-byte/basis/seal rejection, one-reader and early-comparison rejection, late-policy and outcome-input rejection, equal-legacy-hash disagreement handling, missing evidence, retained adjudication and count-free public summaries. These tests use their own pre-existing invented fixtures; they are not a conversion of the reader prose into clinical source records. [Exact command and exit](PROTOCOL_TEST_RUN.json), [stdout](protocol-tests.stdout.log). No full DAV suite or AIU job was rerun.

## Missing approvals and software fixes

The [custody/readiness check](../../evidence/A_DAV_PRAT_CUSTODY_READINESS_01/STATUS.json) remains the unchanged approval snapshot: custody authority and both reader appointments are not established. Actual appointed-reader familiarization, source authentication, first passes, adjudication and export remain `NOT_RUN`. No source-readiness or E01–E10 evidence gap is closed by this exercise. A real form pilot still requires the authorized readers and custody.

No new software defect was established. The form clarifications are documentation findings; missing approvals are operational/authority gaps. The existing synthetic-only APIs remain synthetic-only, and no real-data route was enabled. All actual-analysis flags remain false. [STATUS.json](STATUS.json) records the distinction.

This packet adds later evidence of an invented form exercise without rewriting the earlier plan's historical `NOT_RUN` snapshot. It does not establish completion of source-specific policy locking or real-reader readiness. Frozen specifications, runtime, old evidence and previous receipts remain unchanged.

## Verification and next step

Run `python3 -B docs/validation/A_DAV_PRAT_SYNTHETIC_WALKTHROUGH_01/VERIFY.py` from this worktree to check basis hashes, seals, question/citation coverage, comparison, software-test receipt and preservation. The verifier authenticates neither a person nor source permission. [VERIFICATION.json](VERIFICATION.json) records the result.

The next safe task is a separately versioned clarification of the training form if another synthetic pass is wanted. Actual Prat work still needs verified custody/use authority, two authorized reader appointments, the exact object set and the frozen review sequence. No real-data access or biological analysis is authorized by completing this walkthrough.
