# Paper A — Immune-signature robustness and prostate transferability

Status: **proposed specification, not implementation-ready**. Version0.2, 5 September2026. This draft specifies both the original responder-signature discovery scope and the proposed endpoint-sensitivity analysis, with a separate prostate transport module. The competing primary choice is unresolved; no narrowing is approved. No endpoint, result, publication claim or ticket is frozen by this document.

## Problem and proposed contribution

An ICI signature may appear to work differently when the outcome definition or cohort changes. Untreated prostate expression can describe a molecular state, but cannot validate response to treatment. This paper would quantify these distinctions using the same baseline patients for comparisons of outcome definitions, then characterize transport to prostate without changing the endpoint's meaning.

Broad biomarker benchmarking and response harmonization already have direct precedents: Kang 2023, DOI10.3390/cancers15164094; Luo 2022, DOI10.1016/j.annonc.2022.04.450. ICBatlas and current external-validation benchmarks also overlap. See ../../docs/research/A_clinical_transfer.md. The proposed addition is a reproducible, patient-paired account of how endpoint definitions change a fixed signature's discrimination, with original label provenance, uncertainty and an explicit boundary around prostate transfer. This remains a candidate contribution; a formula alone does not establish novelty.

## Scope and thesis mapping

- Retain clinical immune-signature robustness, clinical endpoint definitions and prostate transferability. Historical label: Paper3; original cross-cancer responder analysis in the submitted protocol.
- Competing proposed primaries: A-P1, signed change in CYT discrimination between disease control and objective response on identical patients; A-P2, independent-test incremental ORR discrimination of the discovered signature over CYT. Select exactly one before scoring, preserving the other as a declared secondary module.
- Retain discovery-derived responder signatures as a conditional full module in DISCOVERY.md, with regularised cohort-held-out development, an independent-test contract and a frozen gene/coefficient handoff. This draft does not claim that fixed CYT implements discovery or that the required cohorts are already available.
- Prostate: untreated TCGA/PCaDB molecular characterization; a trial cohort only for its actual regimen-specific endpoint after source verification. COMBAT is not evidence isolating ICI efficacy. Publicly reusable Guan expression/label linkage is unresolved.
- No treatment recommendation, causal treatment-effect estimate, wet-lab replacement or guaranteed standalone manuscript.

## Decision criteria

Proceed only after the primary choice is approved, response definitions/timing and independent patient membership are reconciled, score units are established and precision is assessed. Require at least two independently sourced eligible cohorts to use the term replication, and more than one cancer to claim a cross-cancer summary; these are minimum design conditions, not power claims. Label same-cancer reproducibility separately from cross-context transport. The proposed tuned discovery additionally requires at least three qualifying development cohorts and separately reserved independent final-test data; neither is verified today. Report source/cohort estimates even if broader aggregation is unsupported.

Narrow only by an explicit reviewed decision if a transport or durable-benefit arm lacks data. Recommend combining with thesis methods/B if the result adds little beyond existing endpoint-sensitivity work or precision is too poor. A recommendation does not cancel A. Do not require a nonzero or favorable result to proceed.

## Package map

- DATA.md: source-by-question coverage, access and mappings.
- ANALYSIS.md: competing primary decision, detailed A-P1 estimand, composition decomposition and uncertainty.
- DISCOVERY.md: retained discovery branch, A-P2 competing estimand, regularised learner, splits and B/C handoff.
- TRANSPORT.md: exact molecular/clinical prostate statistics and cohort-specific admission gates.
- FIGURES.md: four-figure evidence contract and permitted claims.
- ENGINEERING.md: interfaces, environment requirements, workflow and reproduction.
- PREREGISTRATION.md: exposure, decision ledger and readiness checklist.
- REVIEW_RESPONSE.md: disposition of eight independent review findings.
- tickets/: bounded proposed vertical slices; none are ready-for-agent.

Read ../../docs/execution/GOAL.md and root AGENTS.md first. All four design packages need independent review before any paper's production implementation.
