# A-P1 locked-panel scoring release gap

**Status: PROPOSED / PENDING user decision. This note is not signed.**

The signed A-P1 scope requires repetition of endpoint sensitivity on the locked panels, but the numerical-freeze amendment limits the released custom panel means to A-BIO. No panel scores are calculated by A-P1 while its score contract remains unresolved.

## Source clauses

`specs/A/SPEC_v2.md`, §6:

> CYT is fixed, on identical category-evaluable patients: the AUROC under the clinical-benefit definition minus the AUROC under ORR. It is decomposed by response-category composition (`specs/A/ENDPOINT_SENSITIVITY.md`), then repeated for the locked panels. It is reported as a paired difference, never as "significant here, not there".

`specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md`, §7:

> All eleven are unweighted means with their own method IDs. Permitted use: per-study Hedges g and pooling in the `panel` and `panel_coverage90` families, for A-BIO only. This supersedes the listed registry status for that use only.

## Required user decision

Before A-P1 can repeat the endpoint sensitivity for locked panels, specify the A-P1 score definition for each panel, its fixed higher/lower score direction, and the expression qualification rules. This decision must identify the permitted feature version and mapping for the A-P1 endpoint analysis. The A-BIO custom means do not authorize panel scoring for A-P1.
