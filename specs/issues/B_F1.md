Released bounded child of Paper B: https://github.com/OASolliman590/Master-Thesis-/issues/2

Authority: M1_ASTRA_DISPOSITION.md at reviewed commit 43efda19bff062a2e9e140fadd84ab32c88cee71. All four kits received review; scientific analyses remain blocked.

Exact contract: https://github.com/OASolliman590/Master-Thesis-/blob/43efda19bff062a2e9e140fadd84ab32c88cee71/specs/B/TICKETS_AND_TESTS.md

Implement a Python 3.11 standard-library subprocess CLI for tcga-star-expression, tcga-methylation-beta, cpc-expression and cpc-methylation. Hash actual input bytes before parsing. Accept only uncompressed UTF-8 TSV. Record declared full/bounded-prefix scope, count/schema summaries and documented header repair. Reject malformed widths, duplicates, invalid numeric fields, mismatched beta/detection-P pairs and wrong hashes. NA is not zero. Preserve IDs and keep STAR summary records separate.

Owned paths: tools/b_formats/, tests/b_formats/, docs/validation/B_formats/. No downloads, environment mutation, analysis scores, normalization, patient joins, gene/probe selection or models. Real fixtures are read in place and excluded from Git; commit only synthetic fixtures, code and permitted aggregate evidence.

Gate: python -m unittest discover -s tests/b_formats -v. Test CLI success/failure and stale-output/atomic semantics. Independently rerun all four already audited real fixtures locally and on AIU; retain version/command/checksum/count receipts. Local tests cannot substitute for an unrun AIU check.

Review: Spark implementation, orchestrator diff/test checks, Opus code review, fixes as needed, Astra final review, then reviewed commit/push and Notion update. No implementer commits. A passing ticket means format tooling implemented, not Paper B implemented.
## WIP checkpoint — 6 September 2026

Spark implementation and Astra corrections are locally checked: 19 tests passed on Python3.12; the final complete-width swapped-header fixture correction passed its affected test again. Four separate real-format runs have actual summaries and code/input/output hashes. Standards and Spec rechecks are recorded; the remaining fixture correction is resolved.

The initial substantive Opus review requested changes, now addressed. Final Opus recheck is incomplete because the provider quota was exhausted; exit0 is not treated as approval. AIU SSH times out and no B-F1 remote job started. Keep this issue OPEN until final Opus recheck and AIU/Python3.11 checks complete. No scientific analysis or full paper is implemented. See docs/reviews/B_F1_ASTRA_DISPOSITION.md and docs/execution/pending_validation.json in the WIP checkpoint.
