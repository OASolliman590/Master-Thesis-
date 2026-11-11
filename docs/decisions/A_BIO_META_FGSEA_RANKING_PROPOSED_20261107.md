# A-BIO post-meta fgsea ranking — PROPOSED / PENDING

**Status: PROPOSED. No ranking statistic or analysis release is signed.**

The signed module spec requires “fgsea on the meta-analysed gene ranking, Hallmark and Reactome (descriptive)” (`specs/amendments/2026-11-03-analysis-modules/SPEC.md`, §2.3(ii)). The signed numerical freeze specifies `fgseaMultilevel`, `minSize = 15`, `maxSize = 500`, `eps = 0`, ties by gene symbol and missing-statistic removal, and says the per-study ranking uses the DE statistic (`specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md`, §6). It does not identify the statistic or transformation for the pooled meta-gene ranking.

Before a real post-meta enrichment stage can run, the user must choose and sign:

1. The pooled gene field and transformation used to rank (for example pooled Hedges-g estimate, estimate divided by its standard error, or another declared statistic).
2. How direction and ties are ordered, including the symbol tie-break.
3. Which meta rows are eligible, including endpoint-definition partition, synthesis stratum, pooled status and k rule, and how missing or non-finite statistics are handled.
4. The symbol mapping provenance and duplicate/ambiguous/unmapped policy applied to the ranked units.

Until signed, A-BIO records the Hallmark and Reactome post-meta stages as unavailable with reason `pending_meta_ranking_statistic_decision`. An explicit ranking contract is accepted only for invented-data software checks; it does not set a real-analysis default. The existing per-study DE enrichment remains separately defined by the signed DE-statistic rule. Hedges-g synthesis is unchanged.
