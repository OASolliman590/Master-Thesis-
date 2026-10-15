# Implementation reconciliation and migration authority

## Fresh evidence in this revision

The live acquisition review head is 58ac943acbe8c981c7c8c269103c602b4425bd50, draft PR #9. Its exported artifact (run 38723922278, artifact 11966788962, source commit 293130281db0a827cda0e975aec3b823403df68f) has SHA-256 17b987192b2ea8ac080ae748bcb58618c1a181efb9a88d672756a4b8b12fa169. The head's subsequent commit removes the temporary export workflow. The acquisition package is present canonically; it is not merely the older staged/bootstrap snapshot. This is file/provenance verification, not source admission or clinical testing.

The pre-revision A tree d6136db3bd0f70000e8eb0770799f36f5ae9baec is preserved at ../../reference/specs_A_before_20261015. The shared 20-row implementation_reconciliation.tsv and prior appraisal component table remain historical audit inputs. Their claims about old tests or code behavior are not freshly rerun by this document.

## Required three-way inventory

For each function/module record active path/version/hash, historical GitHub path/version/hash, NMRbox path/version/hash, functional role, data dependency, existing tests and historical outputs, fresh test command/log/status, scientific compatibility, risk, disposition, port target and owner. Use exact byte SHA-256 and function-level comparison where possible; 'similar file name' is not equivalence. If a repository/object is inaccessible, put UNKNOWN and a precise retrieval task, never invent a hash.

| Component | Disposition before characterization | Scientific change required |
|---|---|---|
| Retrieval/checksums/atomic output/resume | Reuse after tests or adapt | Complete-object hashes, interruption and version invalidation |
| Source parser scaffolding | Adapt | Preserve exact IDs, raw labels, provenance; no coercion/default clinical assumptions |
| Patient manifest | Replace authoritative semantics, salvage utilities | Normalized study/episode/specimen/assay store, not sample-level identity |
| Allocation/reporting | Adapt | Branch-specific membership and distinct patient/specimen/assay counts |
| Contrast resolver | Replace incompatible routing | Deterministic multiwindow pairing; no last-row overwrite or generic POST |
| Assay/missing-data routing | Replace unsafe defaults | Missing differs from zero; unknown assay fails closed; TPM not counts |
| DE/meta infrastructure | Characterize and adapt | Compatible effect scales, direct estimable contrasts, source dependence |
| Legacy signature | Replace for A-P2 | Fully nested study-held-out training and immutable final model |
| Immune scores | Source-qualify and adapt/replace | Exact published method, unit, reference and licence; no renamed approximation |
| TCGA mapping | Adapt | Molecular characterization only; no fabricated ICI labels |
| Run/report builders | Reuse after tests | Evidence status and hash receipts, no stale result promotion |

## Unreproduced risk register

Previously reported risks include zero-fill, permissive assay fallback, row-order follow-up selection, include_flag ambiguity, duplicate parser columns, conflicting outcomes accepted during execution, assumed timing/response labels, multiple follow-ups overwritten and non-ICI data entering ICI analyses. For every risk, write a minimal adversarial test against the pinned original function, record observed behavior, then decide the port. Until rerun, label HISTORICAL_OR_STATIC_FINDING_NOT_REPRODUCED. A documented report without source matrix is not reproducible real-data validation.

Data recovery is a distinct ticket from code recovery. Search only authorized mounted/cache/AIU/NMRbox locations; this session does not assert access to those remote stores. Preserve source bytes, complete/hash/terms/mapping/exposure; do not redownload a verified valid object. The bounded first packet stops before patient analysis. No active A production workflow or current real-data validation is claimed by the new specs.
