# Novelty comparison and contribution test

## Claims that are not novel enough

Paper C may not claim novelty from any of the following alone:

- use of CMap/LINCS or signature reversal;
- adding DrugBank, ChEMBL, PubChem, DepMap, PRISM or GDSC;
- ranking epigenetic compounds;
- recovering an HDAC, DNMT or EZH2 inhibitor;
- showing that HDAC inhibition can alter antigen-presentation genes;
- linking EZH2 inhibition to interferon/STING biology in prostate cancer;
- adding single-cell annotation;
- assembling more databases than an earlier paper.

## Closest precedents

| Study/resource | Established contribution | Boundary imposed on C |
|---|---|---|
| Kortenhorst et al., 2013 | Prostate HDAC perturbation transcriptomics, including MHC/cell-cycle responses | HDAC-associated antigen-presentation expression is precedent |
| MD-Miner, 2017 | LINCS/CMap, target/network and prostate growth-screen integration | LINCS plus target and sensitivity data is not a new framework |
| Morel et al., 2021 | EZH2 inhibition, dsRNA–STING–interferon and PD-1 response in prostate models | EZH2–immune/ICI rationale is established mechanistically |
| Chang et al., 2022 | Prostate immune-context repurposing using multiple reversal/sensitivity/network resources | Multi-database prostate immune ranking is already represented |
| OncoLoop, 2023 | Patient-to-model matching, activity inversion and prostate validation | Prostate model matching plus drug inversion is established |
| Xiong et al., 2026 | Bulk/single-cell EZH2 immune context and tazemetostat perturbation in C42 | Recent multi-layer EZH2 context further narrows novelty |
| scPerturb, 2024 | Harmonised single-cell perturbation resource | A catalogue/harmonisation layer is not independent validation |

The pre-existing repository comparison remains relevant: `docs/research/C_novelty_comparison.md`.

## Approved contribution hypothesis

The publication-level contribution is:

> A predeclared, leakage-controlled test of whether patient methylation support enriches clinically anchored prostate immune-barrier genes for independently measured desired-direction responsiveness, compared with an equally budgeted expression-only query, followed by transparent explanation of context, mechanism, stress, viability and pharmacological contradictions.

This contribution is **not yet demonstrated**.

## Result patterns that would be informative

1. `Q_M` shows reproducibly greater desired-direction responsiveness than `Q_E`.
2. `Q_M` adds value only in selected programmes or mechanisms.
3. `Q_M` changes candidates but those candidates fail viability or pharmacology checks.
4. `Q_E` performs as well as or better than `Q_M`, showing that methylation evidence did not enrich reversibility.
5. Both queries are highly context-dependent, undermining a context-free ranking.
6. Familiar compounds are recovered, but the evidence hierarchy identifies which claims remain unsupported.

A different ranking is not automatically an improvement. The primary paired endpoint, independent measured evidence and downstream claim restrictions determine whether the methylation layer added value.

## Standalone-paper decision

Proceed as a standalone manuscript only when the final evidence directly tests the contribution above. If the output is an annotated familiar-drug list or if independent evidence is insufficient, integrate C with Paper B or retain it as a thesis-only pharmacological chapter.

No “first study” statement is authorised by this review.
