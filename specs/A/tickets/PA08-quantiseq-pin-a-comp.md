# PA08: Pin quanTIseq (N15) and run A-COMP

**Status:** Research, then your decision and a release. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
Cell-composition estimates are supporting evidence. They are only reproducible if the exact tool version and options are frozen, and the same pin is shared with Paper B.

## Authority
`specs/A/SPEC_v2.md` §4.4, §11 gate 5; freeze register N15.

## Change
Record N15 as the research proposes: Bioconductor `quantiseqr` 1.20.0 (Bioconductor 3.23), called directly as `run_quantiseq(tpm, signature_matrix="TIL10", is_arraydata=FALSE, is_tumordata=TRUE, scale_mRNA=TRUE, method="lsei", rm_genes="default")`. Set `is_tumordata` explicitly, because its default is FALSE. Call quantiseqr, not immunedeconv, which renames `Other`. Add a guard: a sample whose immune fractions are all zero returns NaN in 1.20.0 (fixed only in devel); report it and exclude it. Keep the 90% gene-coverage floor as a project rule (the authors give none). Wire into `tools/a_comp`. Run only on the 12 signed cohorts, after a signed release. CIBERSORTx stays "not run" unless you register.

## Done when
N15 filled and signed; a known-answer check on the package's own example data; A-COMP receipt.

## Needs from the user
Sign N15 (pin 1.20.0 plus the NaN guard, or wait for a release carrying the fix); note that Paper B's array mode needs its own option record; sign the A-COMP run release; decide on CIBERSORTx registration.

## Depends on
PA05

## Research
`docs/research/A_TICKETS_20261119/quantiseq_pin.md` (done 19 Nov: pin, call, input rules, caveats, licences GPL-3).
