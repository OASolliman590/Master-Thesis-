# Paper B implementation manager

**Updated:** 7 September 2026

**Canonical repository:** `E:\Master_Thesis\master-thesis`

**Primary analysis:** TCGA-only development of the frozen baseline and extended ridge models, followed by one no-refit CPC-GENE evaluation of paired external `Delta_R2`.

**Scientific status:** not released. No real TCGA or CPC-GENE result is claimed here.

## Verified implementation state

| Checkpoint | Current evidence | Status |
|---|---|---|
| B-F1 format inspection | Local Python 3.12.10: 19 tests passed in 7.947 s. AIU Python 3.11.16: the same hash-matched tool/tests passed 19 tests in 2.232 s from a unique scratch root. See `docs/validation/B_formats/AIU_20260907.md`. | Local and AIU Python/POSIX software gates pass. Final milestone publication remains separate. |
| B-P1 prediction engine | The continued Grok session `01a07894-13aa-7ad1-8b6f-a17ad2af5203` completed the released-ticket correction. Parent review added engine/patient-set locks and strengthened discriminating tests. Final local Python 3.12.10 combined gate: B-F1 19 tests in 7.252 s and B-P1 16 tests in 51.822 s; fresh synthetic `develop` and `evaluate` exited 0. Receipts are under `docs/validation/B_prediction/`. | Parent-accepted local synthetic software checkpoint. AIU B-P1 is pending after two pre-authentication SSH timeouts; no remote state was created. No scientific release. |
| Real-cohort workflow | No approved numeric TCGA/CPC feature tables, scientific lock, or AIU run receipt exists. | Blocked by E1-E4/E6 and B-I1/B-I2. |

## B-P1 correction gate

Closed locally. The same Grok session completed the single correction brief, and parent review verified exact-byte bundle integrity, strict alpha ties, explicit scientific/evaluation locks, the required private sklearn fitting stack, fit-free evaluation, and independent numerical oracles. Exact hashes and delegation receipts are in `docs/validation/B_prediction/`. AIU verification remains an explicit portability gate rather than a condition for mislabeling the local result.

## Sequential coding queue

| Order | Ticket/stage | Implementation boundary | Release condition |
|---:|---|---|---|
| 1 | B-P1 | Numeric validated-patient-table engine only. | Local software checkpoint accepted; reviewed commit/push is the current publication step. AIU numerical receipt remains pending due VPN timeout. |
| 2 | Source/specimen/covariate ingestion (B-R2/B-I2 seam) | Preserve source identity, reanalysis edges, one approved specimen per patient, covariate meanings, exclusions, and hashes. Reject portal WGS agreement as purity. | Synthetic identity/provenance tests plus signed upstream rules; unresolved focus records remain explicit. |
| 3 | Gene-set registry/scoring (B-R1/B-I2 seam) | Primary eight-gene registry; Ayers GEP-18; full official IFNG hallmark; HOPE_18; separate approved-immunotherapy target registry and saved GMTs. | Exact source/version/hash, membership, signs/weights where known, coverage and missing/duplicate rules. Unknown weights/signs stay invalid or deferred, never inferred. |
| 4 | Promoter/QC/features (B-R1/B-R3/B-I2) | Literal U/Q, aligned annotation mapping, fold-safe TCGA-trained promoter features, assay QC and eligibility exports. | Frozen schemas and metamorphic leakage tests; no external outcome-dependent selection. |
| 5 | TCGA workflow (B-I1/B-I3) | Isolated AIU environment, approved TCGA feature table, nested development and immutable model freeze. | Resolved dependency lock, TCGA-only fit traces, fold sentinels, bundle hashes and independent review. |
| 6 | Locked external evaluation (B-I4) | One approved CPC-GENE evaluation using frozen models and identical paired patients. | Signed evaluation lock; exact SSE/SST/R2/Delta_R2; paired bootstrap; immutable completion receipt. |
| 7 | Secondary/target analyses and C handoff (B-I5) | Prespecified secondary programs and exploratory target-locus analyses; separately frozen TCGA-only C query. | Declared inference/multiplicity, lineage audit, no replacement of a null primary, no CPC-selected C features. |
| 8 | Figures/reproduction (B-I6) | Four required evidence figures, patient-safe tables and manifest-driven reconstruction. | Source/config/code hashes match; exclusions and null/negative results remain visible; AIU rerun and review pass. |

## Scientific locks that must remain unresolved in code

- final literal expression universe U and promoter probe sets Q;
- one-specimen-per-patient and external eligible-population rules;
- purity/covariate comparability and accepted measurement sources;
- primary and secondary score definitions, including any unavailable weights/signs;
- precision/minimum-effect contract and valid secondary multiplicity procedure;
- approved runtime lock, decision commit, reviewer receipt, and first-access ledger; and
- TCGA-only C-selection thresholds.

Implementations may validate and carry these values once supplied, but must not manufacture defaults or treat synthetic output as biological evidence.
