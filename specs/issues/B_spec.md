Reviewed WIP specification; not ready for scientific production.

Measured prostate methylation-associated immune regulation

Reviewed milestone: 43efda19bff062a2e9e140fadd84ab32c88cee71.

Specification kit: https://github.com/OASolliman590/Master-Thesis-/tree/43efda19bff062a2e9e140fadd84ab32c88cee71/specs/B

Independent review and orchestrator disposition: https://github.com/OASolliman590/Master-Thesis-/blob/43efda19bff062a2e9e140fadd84ab32c88cee71/docs/reviews/M1_ASTRA_DISPOSITION.md

The linked kit contains the proposed scope/novelty, data coverage, estimand, validation, four-figure plan, preregistration decisions, engineering contracts and bounded tickets. Unresolved scientific choices and source gates remain explicit. This parent does not authorize implementation of blocked analyses.

Acceptance: B-P external prediction improvement is now the recorded single primary. Resolve the remaining measurement/population/readiness gates, review the resulting frozen scientific contract, and dispatch only explicitly released child tickets. Preserve all four papers and the separate registered wet-lab component.

Sequence: B, C, A, then D when feasible; one paper production active at a time. Format-only B-F1 has separate release authority; it cannot count as biological readiness or completion of B.

## Source-gate checkpoint, 6 September 2026

Reviewed source/specification update: 1999d7ec8e0a873cea2fd879ffb90262447cc2b4.

The CPC portal WGS_BASED_PURITY_ESTIMATION field is SNP-call agreement, not purity, and is prohibited as purity. Original clinical linkage gives114 candidate codes, including73 with stronger protocol support and Qpure present in72; none is a final eligible-N claim. This published source-gate checkpoint predated the later selection of B-P. Ordinary HC3 inference for estimated ranks was withdrawn from the historical B-R proposal; rank-aware inference remains unexecuted. Updated novelty and source/measurement gates remain explicit.

Current kit: https://github.com/OASolliman590/Master-Thesis-/tree/1999d7ec8e0a873cea2fd879ffb90262447cc2b4/specs/B

Review: https://github.com/OASolliman590/Master-Thesis-/blob/1999d7ec8e0a873cea2fd879ffb90262447cc2b4/docs/reviews/SOURCE_GATE_ASTRA_DISPOSITION.md

This parent remains OPEN and WIP. B-F1 code is unchanged; its AIU validation and final quota-limited Opus recheck remain pending. The source-gate commit did not freeze a primary; the later user decision below selected B-P.

## B-P primary selection and first engine ticket, 6 September 2026

The user selected B-P external prediction improvement as the one Paper B primary. Its estimand is independent CPC-GENE `Delta_R2=(SSE_baseline-SSE_extended)/SST` for an extended promoter-methylation ridge predictor versus a baseline covariate ridge predictor, both fitted/tuned only in TCGA and frozen before external evaluation. B-R is historical, not co-primary or an automatic response to a null result.

Selection does not approve the proposed eight-gene program, U/Q, specimen/replicate/purity policy, final eligible N, precision target or a biological run. `specs/B/tickets/BP1_prediction_engine.md` defines the bounded first implementation over validated patient feature tables. Synthetic implementation tests may proceed; source-feature ingestion and real TCGA/CPC execution remain blocked pending the signed scientific lock.
