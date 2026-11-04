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
| Astra review of draft 2 | Research | the above | Open |
| Hallmark coverage rule: override or keep strict? | Grilling (user) | Astra review | Open |
| M5/M6 family, seed streams, solver | Grilling (user) | Astra review | Open |
| Sign the freeze | Grilling (user) | the two above | Open |

## Decisions so far

- [Evidence review](../../research/NUMERICAL_FREEZE_EVIDENCE_20261104.md): no coverage threshold is validated; a separate M5/M6 family is stratified FDR; seeds need named streams; the glmnet objective matches but `thresh` and `maxit` belong in `control`.
- Coverage audit, outcome-free: 9 of 20 studies have all 200 IFN-gamma genes and 14 have at least 180. Draft 1's "1 of 20" was a naming artefact. Across the 50 Hallmark sets, studies had 0 to 47 sets complete before the alias fix; this needs recounting after it.
- Software checks on synthetic data: fgsea repeats with the same seed, also at `nproc = 2`, and differs with another seed; the glmnet result follows.
- glmnet with the proposed call, synthetic data (n = 300, 4 features): `control ok jerr 0 npasses 15 maxdiff 2.097088e-09 KKT 8.571364e-10`.

## Not yet specified

- Whether GSE145996 (176) and GSE122220 (177) gain genes from a fuller Entrez-level audit.
- Which OSF template to use at signing.

## Out of scope

- Paper B's Tier 1-3 gene lists: separate effort, sources not yet obtained.
- A-LONG windows and the quanTIseq pin: their own gates.
