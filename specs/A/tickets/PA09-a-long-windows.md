# PA09: A-LONG: register windows, verify pairs, sign N12/N13

**Status:** Research, then your decisions. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
A change between baseline and on-treatment biopsies only means something if the timing is defined before outcomes are seen. Otherwise windows could be tuned to the result.

## Authority
`specs/A1/SPEC_v2.md` §3, §9; `docs/decisions/PROPOSED_A_LONG_N12_N13_20261107.md`.

## Change
Register a window per study (index event, day bounds or verified category, tie rule, lesion and platform policy) for Riaz, Gide, GSE165278, GSE145996 and GSE168204. Verify the on-treatment roster and day distances outcome-free.

Research (19 Nov) proposes:
- **Riaz:** baseline 1–7 days before the first dose; on-treatment "cycle 1, day 29 (days 23–29)", which is 22–28 days after the first dose if day 1 is the first dose. The source gives a schedule only, with no per-specimen days. Keep ipi-naive and ipi-progressed separate.
- **Gide:** EDT 7–14 days after treatment start; no lower bound for PRE; same lesion not stated. The paper reports 9 monotherapy pairs, which does not match the 14-run crosswalk.
- **GSE165278 and GSE145996:** not pairable. The sources describe one tumour per patient, and pre-treatment samples only.
- **GSE168204:** blocked. No on-treatment day bound, mixed preservation, two sequencers.

If accepted, only Riaz and Gide monotherapy remain. Their windows differ (about day 29 vs days 7–14), so pooling them is itself a decision.

## Done when
Windows file signed; roster check receipt; N12 and N13 signed.

## Needs from the user
The 12 open items in the research note, mainly: the Riaz day convention; the Gide PRE bound and the crosswalk count (14 runs vs 9 published pairs); dropping GSE165278 and GSE145996; the GSE168204 rule; whether Riaz and Gide may be pooled. Then sign N12, N13 and the windows.

## Depends on
PA05

## Research
`docs/research/A_TICKETS_20261119/a_long_windows.md` (done 19 Nov).
