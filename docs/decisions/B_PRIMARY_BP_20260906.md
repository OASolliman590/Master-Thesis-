# Paper B primary decision: external prediction improvement

Decision date: 6 September 2026. Status: USER SELECTED B-P; technical and measurement readiness gates remain separate.

The user explicitly chose B-P and requested a spec update followed by coding. This selects external prediction improvement, not the previously recommended B-R replicated-association primary. Preserve B-R as an unselected historical alternative; do not treat it as a co-primary or silently switch back to it.

## Selected scientific claim

Does adding the specified promoter-methylation features improve prediction of a defined immune-expression program in an independent prostate cohort, beyond the approved clinical/tumour-content baseline?

Develop and tune both models within TCGA-PRAD. Freeze the baseline and methylation-extended models and all fitted transformations. Evaluate them in the same eligible CPC-GENE patients without refitting or recalibrating on CPC outcomes. The primary estimand is Delta_R2=(SSE_baseline-SSE_extended)/SST. Report negative, null and undefined results honestly. This predicts a molecular expression endpoint, not clinical ICI response or a causal treatment effect.

## What this decision freezes

The primary scientific direction is selected. The proposed eight-gene antigen-presentation program, common expression universe U, promoter lists Q, specimen/replicate policy, covariate measurement comparability, final eligible population and precision thresholds are not automatically approved by choosing B-P. Routine engineering choices can proceed through the bounded implementation contract. Do not evaluate an unsupported biological endpoint merely to show a result.

The user also requested a bounded read-only inspection of multiple historical gene lists on AIU. Distinguish their generating runs, discovery data, direction/weights, identifiers, prior test-set exposure and errors. They are candidate reusable inputs, not approved replacements. A list chosen using CPC-GENE outcomes cannot serve as an independently frozen endpoint on those same outcomes. Old-pipeline repair is not a prerequisite.

## Execution assignments

- Existing Sol High task 01a075b4-a503-7593-a092-3825be736e2a: coordinate the B-P spec amendment and one runnable prediction-engine coding ticket, reusing current evidence. Return the concrete contract for one parent release review, followed by Spark implementation. No new broad research/review cycle.
- Sol High task 01a07603-056a-7fb1-9c6b-234fae3a0430: bounded AIU historical gene-list inventory and reuse recommendation; write no pipeline/data changes. Use local audited evidence if VPN is unavailable and state the limit.
- Parent Astra: own this decision, Notion synchronization, final integration and milestone publication. Spark handles released coding. Only Paper B production is active.

## Tangible next milestone

One runnable development-and-locked-evaluation engine with a defined patient-feature input contract, serialized frozen model bundle, paired prediction/metric outputs and meaningful leakage/arithmetic checks. Follow with a real TCGA discovery result and then the prespecified external evaluation when measured-input gates pass. Synthetic software checks do not count as biological results, and a TCGA-only figure is not the completed external primary result.

This decision preserves A/C/D, every agreed Paper C source and the registered wet lab. No model run, test pass, paper implementation or new biological finding is claimed by this record.
