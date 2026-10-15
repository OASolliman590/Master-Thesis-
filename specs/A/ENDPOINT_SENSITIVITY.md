# A-P1 — CYT-led fixed-score endpoint sensitivity

## Population, score and direction

A-P1 is secondary to A-P2 and does not depend on successful model learning. Use fixed CYT=sqrt(TPM_GZMA×TPM_PRF1) under its qualified abundance contract. Higher score orientation is fixed. The principal analysis requires source-supported O=CR/PR, SD and PD categories on the same index episode and the same patients for both endpoints. Define ORR=1 for O and 0 for SD/PD; DCR=1 for O/SD and 0 for PD. Estimate delta=AUC(s,DCR)−AUC(s,ORR). Preserve source criteria, evaluation window and the three category counts.

## Category-composition decomposition

Let A(U,V)=Pr(s_U>s_V)+0.5 Pr(s_U=s_V), estimated over all cross-category patient pairs. With category counts n_O,n_SD,n_PD:

AUC_ORR=[n_SD A(O,SD)+n_PD A(O,PD)]/(n_SD+n_PD).
AUC_DCR=[n_O A(O,PD)+n_SD A(SD,PD)]/(n_O+n_SD).

This algebra shows why endpoint prevalence/composition can change apparent discrimination without changing the score. Report the three pairwise A values and category fractions where estimable. Do not imply a biological effect of relabelling a patient. If SD is absent and O/PD exist, the two endpoints coincide and delta is structurally zero; report that cohort only in the prespecified no-SD sensitivity, not as informative endpoint-definition evidence. Without O or PD, one or both AUCs can be undefined. A binary R/NR source cannot supply SD by assumption.

## Synthesis and uncertainty

Use the prospectively declared A-P1 collection, with cancer/study weighting recorded separately from A-P2; proposed default preserves equal cancer/equal study within cancer when estimable. Freeze the roster before score/outcome exploration. Within-study uncertainty resamples patients jointly with their fixed score and original category, stratifying by O/SD/PD for the principal conditional analysis. Recompute both endpoint AUCs from each identical resample. Do not apply a two-score paired-DeLong calculation across different response labels. State that category-stratified intervals condition on category counts. Repetitions/interval levels and any unconditional composition sensitivity remain numerical freeze items.

## Learned-score secondary

Apply the single final frozen learned score to patients not used in its feature selection, fitting or tuning and with the required endpoint categories. Do not fit ORR and DCR models separately, change weights between endpoints, choose a more favourable score, or treat differently fitted outer-fold scores as a single frozen score. A learning-procedure endpoint sensitivity would require a distinct specification. This secondary can be unavailable while CYT-based A-P1 remains valid. Reserved test data can only be used through its predeclared evaluation release, never to revise the B/C handoff.

## Required outputs and tests

Output patient N, category counts, both AUCs, delta and interval, pairwise category discrimination, exact score hash, endpoint mapping version and exclusions. Test positive/zero/negative synthetic contrasts, tied scores, category relabelling, no-SD structural zero, absent PD/O nonestimability, and bootstrap row-pairing. No effect direction or magnitude is a publication gate.
