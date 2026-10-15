# Paper C Scientific Revision Report

**Date:** 15 October 2026  
**Status:** framework approved; exact endpoint and biological execution remain gated  
**Baseline:** `main` at `a8278c776da7c6b096cc14139d729979db286b50`

## 1. Executive verdict

Paper C should be an evidence-based experimental-prioritisation study, not a three-drug LINCS comparison. The approved architecture is C3 at paper level, a bounded C2 screen for discovery and C1 as secondary calibration. The proposed primary asks whether a methylation-supported query (`Q_M`) is more molecularly responsive in the desired direction than a matched expression-only query (`Q_E`) in independent measured prostate perturbation experiments.

The main knowledge contribution is not the use of LINCS, more databases or recovery of known HDAC/DNMT/EZH2 drugs. It is a leakage-controlled test of whether patient regulatory evidence changes the experimentally observed reversibility and interpretation of clinically anchored prostate immune barriers.

## 2. Live-state conclusion

The main branch contains a September 2026 Paper C design draft, metadata audits and source work but no production biological scoring. The existing draft explicitly described its primary as proposed and its package as not implementation-ready. The complete LINCS metadata audit established common-condition coverage and major unit/project limitations without inspecting expression effects. The open evidence-expansion and Paper B revision pull requests are proposals rather than merged dependencies. No Paper C revision branch existed before this work.

Unpublished local or AIU work that is not in the repository cannot be verified and is not treated as evidence.

## 3. Current-design audit

### Retain

- versioned B-to-C handoff and leakage controls;
- matched expression-only comparator;
- patient methylation as a hypothesis-generating regulatory layer;
- compound identity and release-overlap curation;
- full-universe WTCS with reference parity for LINCS;
- landmark/inferred/absent L1000 coverage reporting;
- independent measured validation;
- CCLE/DepMap model context;
- PRISM/GDSC/CTRP as viability context rather than immune validation;
- mechanistic/genetic evidence with intervention type preserved;
- pharmacology and formulation review;
- transparent evidence matrix and prospective wet-lab handoff.

### Revise

- the disease query into matched programme-aware `Q_E` and `Q_M` products;
- primary inference so biological replicates, not genes or collapsed signatures, support uncertainty;
- broader screening into a bounded, curated C2 discovery module;
- IFNG analysis into a state-resemblance secondary analysis;
- class analysis into an identifiability-gated secondary;
- candidate integration into rule-based tiers and Pareto reasoning.

### Replace

- C1 as the primary;
- a common 24-hour exposure as a general biological comparison across mechanisms;
- any total weighted score that hides missing or contradictory evidence;
- any claim that drug sensitivity, target essentiality or signature reversal proves immune restoration.

### Conditional

- one-sided query scoring;
- class-level models;
- TISMO, Perturb-CITE-seq and combination studies;
- IFNG references;
- random-effects synthesis;
- additional epigenetic classes beyond DNMT/HDAC/PRC2.

### Remove

- automatic use of the fixed eight-gene B endpoint as the complete C query;
- tau terminology without the exact reference distribution and implementation;
- gene or well bootstrap as biological replication;
- virtual predictions as independent validation;
- availability-driven computational selection.

## 4. Protocol crosswalk

The submitted protocol commits to computationally selected prostate models, epigenetic-drug treatment and molecular/possible functional assessment. The accessible protocol text gives DNMT and HDAC inhibitors as examples; it does not prove that decitabine, entinostat and tazemetostat are a permanently registered three-compound set.

The later wet-lab plan is more specific and mechanism-aware. It proposes repeated decitabine exposure, shorter entinostat exposure and delayed tazemetostat exposure, with target-engagement and post-washout viability gates. That plan supports a mechanism-aware C3 handoff and contradicts interpreting one common 24-hour condition as biologically equivalent.

Actual physical inventory, formulation, lot and certificate status remain `UNKNOWN` until a receipt-level inventory is supplied. Commercial tablets are not automatically suitable cell-culture reagents.

## 5. Competing framings

### C1 — sentinel common-condition assay

C1 is simple and reproducible but supports only a finite assay-context description. Sparse independent experiments, different project identity and mechanism-inappropriate timing prevent comparative efficacy inference. It remains valuable as calibration.

### C2 — broad curated screen

C2 can discover unexpected compounds and context dependence. Without a frozen universe, identity rules and independent validation, it degenerates into an uneven database ranking. It is retained as the discovery engine only.

### C3 — evidence-based prioritisation

C3 directly serves the thesis chain and the wet lab. Its main risk is arbitrary evidence integration; this is controlled by keeping evidence dimensions separate, using explicit tiers and avoiding a default total score.

## 6. Exact revised aim

**Primary aim:** determine whether patient-methylation-supported, clinically anchored prostate immune-barrier programmes show greater desired-direction molecular responsiveness to independently measured epigenetic perturbation than a matched expression-only query.

**Secondary aims:** characterise discovery connectivity and context dependence; distinguish restoration from toxicity/stress; assess mechanism; evaluate pharmacological plausibility; nominate prospective experiments.

## 7. Primary-endpoint appraisal

The former endpoint was negative mean WTCS for decitabine, entinostat and tazemetostat in PC3 at 24 hours and 1.11111 micromolar. Metadata support the existence of those signatures, but not biological equivalence or treatment superiority. Tazemetostat is project-confounded at the anchor, and a collapsed signature is not an independent patient or trial.

C1 therefore moves to secondary calibration.

## 8. Proposed primary endpoint

Each independent measured study receives two frozen, equally budgeted queries. Directional sample-level rank scores are computed over the full measured feature universe. For sample `i`, `S_i(Q_M)` and `S_i(Q_E)` represent the desired-state scores. The paired score is:

`D_i = S_i(Q_M) - S_i(Q_E)`.

A source-specific limma model estimates the treatment effect on `D_i`, respecting blocking, shared controls and declared covariates. A positive contrast means the treatment shifts the methylation-supported query further toward the desired state than the expression-only query. Separate effects on `Q_M` and `Q_E` must be shown so a positive difference cannot hide deterioration of both.

Original studies, not genes, are the cross-source units. The finite-set source-equal summary is `Delta_Q`; it is not a drug-efficacy effect or clinical sensitisation estimate.

## 9. Disease-query architecture

A provides clinically associated programme direction. B provides prostate deficit, methylation association, composition sensitivity, genetic alternatives and cellular localisation. C may not independently reselect A/B genes using perturbation outcomes.

`Q_E` and `Q_M` must share discovery patients, programme/direction quotas, total size, tumour-cell eligibility and expression-ranking rule. `Q_M` differs by a frozen methylation-support gate. If a programme lacks enough supported genes, it is ineligible rather than padded. One-sided biology is permitted with an approved one-sided scorer; the missing direction must not be invented.

## 10. Novelty assessment

Prior prostate work already covers HDAC transcriptional responses, CMap/network prioritisation, model matching, EZH2–STING/interferon biology and multi-layer EZH2 immune context. A 2026 CRPC study also reported tazemetostat perturbation with H3K27me3 and transcriptomic readouts. Therefore, neither an EZH2/HDAC finding nor a larger database stack is a sufficient contribution.

The defensible contribution is the fair methylation-supported-versus-expression-only reversibility test and the explicit demonstration of how independent evidence, context and pharmacology change interpretation. A negative result remains publishable in principle if the design is rigorous; publication is not guaranteed.

## 11. Data/source architecture

Sources are assigned non-overlapping roles: patient discovery, perturbation discovery, independent measured validation, model context, viability, mechanism, immune function and pharmacology. Database mirrors do not create independent evidence. Original study, intervention, control, biological unit, verified and independent `N`, access, licence and overlap are required fields.

GSE199800 remains blocked for its intended plate-matched validation until an authoritative row-to-GSM/plate/control mapping is available. GSE35242 is a strong admission candidate because it includes prostate expression/methylation perturbations and independent-day triplicates, but it still requires a full source-specific contract. GSE216053 remains unresolved until exact intervention and design metadata are verified.

## 12. Drug universe and identity

The primary protocol-aligned universe is direct DNMT inhibition, HDAC inhibition with selectivity preserved, and EZH2/PRC2 modulation. Additional chromatin classes require a predeclared biological link and measured coverage. Parent molecule, salt, formulation, aliases, structure, direct/indirect targets, polypharmacology and clinical status remain distinct.

Multiple BRD IDs, salts, batches, wells and release duplicates are not independent compounds. Raw mechanism labels are never sufficient for class assignment.

## 13. LINCS/scoring contract

LINCS discovery uses the complete ordered feature universe. Raw WTCS may be used only after parity against the pinned official call path and adversarial fixtures for ties, zero enrichment, missing features and same-direction sets. A query with one biological direction uses an approved one-sided score rather than fabricated genes. Tau is prohibited unless its exact reference normalisation is implemented.

Every result reports landmark, best-inferred, other-inferred and absent coverage. Inferred immune-gene responses are not called directly measured expression.

## 14. Exposure/time/cell-context design

Discovery output is a compound-by-model-by-dose-by-time-by-project matrix. Context-specific results are retained. Mechanism-aware windows are secondary analyses and do not support direct superiority when exposures differ.

PC3 is not automatically the representative prostate model. Model eligibility depends on lineage, disease state, androgen-receptor context, baseline programme deficit, target expression, chromatin lesion, inducibility and identity. Non-prostate contexts are mechanistic corroboration, not direct prostate validation.

## 15. Replication and uncertainty

A LINCS Level 5 signature is a collapsed assay object, not a biological population sample. Independent measured data require identifiable culture/experiment replicates and complete feature space. Primary inference uses biological replicates and source design. Genes, wells and cells are not promoted to independent studies.

A source with inadequate replication may contribute descriptive evidence but not the primary. Cross-release LINCS overlap is audited at instance level.

## 16. Viability/stress strategy

Programme restoration, cell cycle, apoptosis, general stress and viability are separate outputs. PRISM, GDSC and CTRP retain their native scales. Strong growth inhibition cannot be relabelled as immune restoration, and target dependency cannot prove direct regulation of a query gene.

## 17. Independent measured validation

Eligible contrasts are frozen before direction is inspected. Primary sources must provide exact intervention, control, model, dose, time, independent replicates and full measured feature space. Measured disagreement is retained. If fewer than three independent originating studies pass admission, the primary remains descriptive and prospective wet-lab evidence becomes more important for a standalone paper.

## 18. Immune/combination evidence

Molecular change, immune-mediated function and ICI interaction are three distinct claims. Perturb-CITE-seq and TISMO may supply orthogonal evidence in their native species/model/intervention settings. Synergy requires a factorial or otherwise valid interaction design; separate single-agent datasets cannot establish it.

## 19. IFNG reference

An IFNG reference tests resemblance to an inflammatory state, not prostate specificity, target dependence or immune killing. The proposed LJP4 source remains gated until payload, controls, cell context, feature space and overlap are verified.

## 20. Pharmacology

Shortlisted compounds require primary human PK/regulatory extraction: formulation, route, regimen, total/unbound exposure, binding, metabolites, sampling time and tissue data where available. Nominal culture concentration is not equated with free plasma, free medium, intracellular or tumour exposure. This layer describes plausibility and uncertainty; it does not recommend dosing.

Tazemetostat's US accelerated-approval indications were withdrawn in June 2026 after a safety-driven market withdrawal. It may remain a mechanistic research compound, but it must not be labelled currently FDA-approved.

## 21. Evidence integration

A transparent evidence matrix precedes any prioritisation. The recommended output is rule-based evidence tiers plus a Pareto set, with separate roles for best molecular restorer, best mechanistic candidate, best translational candidate and best feasible pilot. Missing evidence is unknown, not neutral.

## 22. A-to-B-to-C boundaries

A clinical coefficients are not automatically restoration directions. B methylation association is not proof of reversibility. C RNA change is not proof of immune function. Versioned handoffs preserve each evidence type and prevent outcome leakage.

## 23. C-to-wet-lab handoff

The handoff specifies exact compound identity/formulation, model, baseline programme, expected direction, mechanism, exposure rationale, controls, target-engagement readouts, viability gates and interpretations of positive/null/contradictory outcomes. Scientific priority, procurement and immediate feasibility are separate.

## 24. Four-figure design

1. Query and evidence architecture.
2. Bounded measured perturbation discovery and C1 calibration.
3. Independent paired `Q_M` versus `Q_E` validation plus mechanism/stress.
4. Translational evidence matrix and prospective handoff.

Every panel declares source, unit, `N`, analysis, uncertainty and claim ceiling. Missing validation remains visible.

## 25. Feasibility, blockers and publication assessment

Documentation, identity curation, source metadata admission, scorer parity, schemas and synthetic/adversarial tests can proceed now. Biological scoring is blocked by the unfrozen B handoff and incomplete independent-source contracts. Actual inventory is also unresolved.

Standalone publication requires independent measured evidence that tests what methylation adds, not merely a known drug ranking. If that evidence cannot be obtained, C should be combined with B or retained as a thesis module. No publication outcome is guaranteed.

## Decision

The user approved C3, bounded C2 and secondary C1, and approved development of the paired independent-measured `Q_M` versus `Q_E` endpoint as the proposed primary. No real perturbation effect was inspected to make this decision.
