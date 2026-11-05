# Wayfinder: numerical freeze for Papers A and A-LONG (4 Nov 2026)

Local map, as for earlier efforts. Scope is small enough for this file; no GitHub issues.

## Destination

A signed `specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md`, so that gates 1 and 2 of Paper A are closed before any outcome is examined.

## Notes

Skills: research, wayfinder, grilling. Lean process. Signed constraints: strict coverage for panels (panel-coverage amendment), A-P2 settings (validation amendment), A-META statistics (analysis modules), one seed for the A-P2 bootstrap. IMvigor210 stays untouched.

## Tickets

| Ticket | Type | Blocked by | Status |
|---|---|---|---|
| What do tools and papers do about missing genes? | Research | none | Closed |
| How many studies really have the Hallmark genes? | Task | none | Closed |
| Do fgsea and glmnet behave as the draft assumes? | Task | none | Closed |
| Astra review of draft 2 | Research | the above | Closed |
| Hallmark coverage rule: override or keep strict? | Grilling (user) | Astra review | Closed |
| Full 50-set audit | Task | coverage rule | Closed |
| Families, seeds, settings: draft 3 | Grilling (user) | audit | With user at signing |
| Sign the freeze | Grilling (user) | the two above | Open |

## Decisions so far

- [Evidence review](../../research/NUMERICAL_FREEZE_EVIDENCE_20261104.md): no coverage threshold is validated; a separate M5/M6 family is stratified FDR; seeds need named streams; the glmnet objective matches but `thresh` and `maxit` belong in `control`.
- Coverage rule: on 4 Nov the user chose strict as the main rule, with the audit to follow.
- Coverage audit, outcome-free: IFN-gamma is 8 of 20 complete and 14 at 90% or more ([table](../../cohorts/HALLMARK_COVERAGE.tsv)). Earlier figures of 1 and 9 were wrong: the first missed aliases, and the second assumed an unsupported TXNIP mapping.
- [Astra review of draft 2](../../../specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md): no High findings; its gaps are closed in draft 3, which has not had a second review.
- Software checks on synthetic data: rerunnable receipts in [NUMERICAL_FREEZE_CHECKS.md](../../validation/NUMERICAL_FREEZE_CHECKS.md).

## Not yet specified

- Which OSF template to use at signing.

## Out of scope

- Paper B's Tier 1-3 gene lists: separate effort, sources not yet obtained.
- A-LONG windows and the quanTIseq pin: their own gates.
