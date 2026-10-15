# Culture–human translation and domain uncertainty
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Distinct contexts

Culture inputs: nominal or analytically measured medium concentration, actual volume, addition/removal events, protein content, viable target/effector counts, encounter conditions and assay timing. Human inputs: administered amount, route/formulation/infusion, systemic physiology, disease/treatment context and systemic disposition. A numerical match between nominal culture concentration and human total Cmax is not equivalence, safety or efficacy.

## Bridge chain

Administered amount → plasma total → plasma unbound → tumour interstitial/free → intracellular available exposure → proximal PD. Each transition has an empirical source, explicit uncertain prior or unresolved status. Culture nominal → culture free → intracellular exposure is a separate chain. Binding, stability, uptake/efflux, metabolites and protein content may matter for the selected compound; include only mechanisms justified by evidence and the question.

Define units and analyte at every edge. Fraction unbound multiplies total only in the matched matrix/context; a parent-salt mass correction requires verified composition. A partition coefficient is not a potency correction. If analytical measurement is unavailable, fit culture nominal-exposure PD and conduct explicit bridge sensitivity; do not claim an in-vitro–in-vivo extrapolation has been validated.

## What transfers and what does not

Source-supported chemical properties may transfer within their measurement conditions. Systemic PK parameters require population/route/formulation rationale. Tumour growth, immune encounter, antigen/HLA recognition, immune competence and checkpoint sensitivity are context-specific. Cell-line marker ratios are not patient receptor densities. Donor/culture random effects cannot become patient-wide biological covariance.

Maintain separate parameter namespaces (`culture.*`, `human.pk.*`, `human.bridge.*`, `human.qsp.*`) and context IDs. Coupling uses posterior/prior draws with dependency metadata, not point estimates. An uncertain site observer must not remove drug from systemic mass balance. The same distribution/elimination/binding process cannot be counted in two modules.

## Human-context exploration gate

Human simulations may describe conditional exposure plausibility and robustness of a mechanistic hypothesis once systemic PK is evaluated and assumptions are explicit. They do not produce a clinical regimen recommendation. Disease stage, prior treatment, concomitant therapy and population differences remain visible. Do not relabel simulated tumour count reduction as ORR/PFS/OS without a validated clinical observation bridge.

Report which uncertainty dominates: systemic PK, tumour delivery, intracellular bridge, priming persistence, immune impairment, checkpoint responsiveness or model structure. A stable rank under one narrow assumed bridge is not a robust clinical prediction. If supported alternatives reverse rankings, report no robust preference. More Monte Carlo draws reduce numerical sampling error, not source uncertainty.
