# Riaz baseline policy

`baseline_policy.py` builds a new `A_BASELINE_BIO` packet from a canonical ingestion
packet and then calls `review_prepare` to rebuild registries and metadata stages. The
branch packet includes identity-verified `PRE_INDEX_BASELINE` specimens and their linked
patients, assays, outcomes, treatment episodes, exposures and bindings. It preserves the
complete source inventory and the original ingestion questions. `On` records remain in
the raw source objects and their questions stay visible as outside this branch.

The endpoint configuration uses author clinical `BOR` as the source of record and RECIST
v1.1 as documented by the original article. CR/PR map to positive ORR, SD/PD to negative
ORR, and NE/unknown to null. Raw BOR and corroborating GEO labels remain available in the
source evidence. Only a specifically evidenced NE/UNK vocabulary pair receives a
proposed discrepancy crosswalk; other conflicts remain unresolved. The endpoint mapping
version is set on both configuration and derived source outcomes before registry rebuild.

## QC proposal

The QC rules and remaining decisions are recorded in [the Riaz QC proposal](../../docs/research/A_DAV_RIAZ_QC_PROPOSAL_20261026.md).
That proposal is pending reviewer decision and is not applied by this tool. It keeps
source retention, assay QC, ORR evaluability and admission separate; it also leaves the
four script removals and separate PCA exclusion as historical flags. Numerical matrix
checks and representation selection remain pending.

The implementation does not apply these QC proposals, choose an assay representation,
infer dates, resolve overlap or prior exposure, or set admission flags. This version
rejects populated overlap/prior-exposure tables rather than silently dropping them from
branch scope. `review_prepare` emits a fresh unsigned worksheet. The frozen
`episode_binding` schema requires a human reviewer and review time for VERIFIED
bindings; the CLI creates no such binding, signature or reviewer date. Endpoint mapping
therefore remains blocked until source-supported bindings receive legitimate review.
