# Immune-programme amendment v1 — 16 October 2026

## Authority, status and precedence

The user authorized expanded immune-programme coverage for A/A.1 and alignment with B, original-source verification and an updated overview. This additive specification amendment applies on top of `specs/thesis-20261015-v1-rc2`. It preserves every file covered by `docs/integration/20261015/FREEZE_MANIFEST.json`; that baseline remains reproducible. It changes prospective programme scope and interpretation, not RC2 bytes or scientific execution status. It is not institutional approval, preregistration, source admission, statistical release or evidence of completed biology.

For the expanded programme catalogue and corrected source interpretation use this packet. For existing primaries, acquisition identity, source admission, protected patients, estimands and unresolved numerical settings, RC2 continues to control. A-P2 and B-P are unchanged. The deliberately explicit CYT naming correction below governs interpretation of the preserved comparator ID. Parent publication and PDF are separate outputs; no analysis, training or pipeline rebuild is authorized by this packet.

Read `programme_registry.v1.json`, `SOURCE_VERIFICATION.md`, `INTERFACES_AND_GATES.md`, and `VALIDATION.md` together. A programme can be biologically defined yet not executable: membership, measurement, scoring, patient admission and statistical release are distinct gates.

## Reconcile the original five layers

The recovered original repository contains five configured layers, with multiple GMT entries in the hallmark and epigenetic layers. Their source bytes and hashes are archived under `legacy/` and `legacy_provenance.json`; the recovered bytes match Git blob identities at original commit `96c16794bafc8946ae9f0bdcef81d5f3a599542b`.

| Legacy layer | Amendment disposition |
|---|---|
| T-cell-inflamed GEP18 | Retain recovered membership as a conditional named comparator; published weighted score and normalization must be pinned. Do not equate it with the other 18-gene expanded-immune signature in the same paper. |
| C7-style exhaustion/checkpoint core | Preserve as a historical custom candidate, not an official MSigDB C7 release or a validated exhaustion score. |
| Hallmark mini proxies | Preserve for provenance only; do not substitute them for official full Hallmark sets. Acquire release, exact members and source bytes before prospective use. |
| Epigenetic immune priming/checkpoint panels | Mixed custom candidates, not validated universal activation scores. Regulator expression does not measure chromatin activity. |
| HOPE18 | Correct historical classifier language: exact prognostic membership is verified; an established single 18-gene ICI-predictive classifier is not established by that source. |

Legacy code used cohort medians for CD274/CD8B types, filled absent markers with zeros and averaged the available HOPE genes. These operational shortcuts are not accepted here. In particular, an absent marker could become positive because zero equals its zero median. Missing features must produce an explicit unscorable/indeterminate reason, not a biological state. Hashes authenticate recovered bytes, not their scientific correctness.

## Expanded prospective coverage

Preserve the existing proposed eight-gene antigen-presentation P without alteration: HLA-A, HLA-B, HLA-C, B2M, TAP1, TAP2, PSMB8, PSMB9. Its membership/assay release remains pending the B P/U/Q gates; preserving this proposal does not freeze it. It remains the existing B component rather than a universal representation of all antigen presentation. Expand the catalogue separately to source-qualified extended antigen processing, class-II presentation, IFN signalling, T-cell recruitment and cytotoxicity, activation/checkpoint states, cell composition, and stromal/metabolic immune-evasion context.

The existing B M0–M6 candidates remain inspectable with their exact existing lists and candidate status. Wider scopes with unresolved memberships use null membership, never an invented certified list. MHC-I and MHC-II, recruitment and cytotoxicity, checkpoint expression and exhaustion, and cell fractions and cellular states remain separate quantities. Shared genes create overlapping hypotheses; programme agreement is not independent replication. Broad evasion programmes are hypothesis-generating and require a mechanism-specific evidence table before any mechanism label.

HOPE18 is retained in full. HAVCR2 has the opposite survival association to the other 17 in the source; this is not permission to invent prognostic weights or flip a gene for an ICI score. A later unweighted enrichment must have its own exploratory identifier and method contract. No common all-positive score is called the published HOPE classifier.

## Four TME types and cell composition

Store the two continuous axes before any categorization. The sign order below is PD-L1, infiltration; HOPE uses CD8B expression whereas Teng's framework uses TIL presence. These are related labels with different measurement bases.

| Axis signs | Teng type | HOPE label | Descriptive framework label |
|---|---|---|---|
| +,+ | I | A | adaptive immune resistance |
| −,− | II | C | immunological ignorance |
| +,− | III | B | intrinsic induction |
| −,+ | IV | D | tolerance |

These labels describe a framework; RNA proxies cannot establish their mechanisms, PD-L1 protein positivity, or spatial T-cell exclusion. Any transcriptomic implementation must be named a proxy, declare axes/reference, cutoffs/ties/uncertainty and transport policy, and return indeterminate when either axis is missing or insufficiently measured. Cohort-median types are a separately labelled operational sensitivity, not verified source reproduction. Continuous values are primary for this descriptive module; categories are secondary.

Cell typing means qualified bulk composition estimation. A method/reference must support the stated cells and assay, distinguish relative fractions from absolute/abundance scores, and retain uncertainty and unsupported types. A broad LM22 setting in old YAML is not readiness evidence. TCF7 expression alone cannot identify a progenitor-exhausted population; checkpoint expression alone cannot separate activation from exhaustion. RNA-derived composition and RNA programmes share data and are not orthogonal validation. B's MethylCIBERSORT remains separately qualified and cannot silently replace purity.

## Preserved primary and source divergence

RC2 `CYT_Rooney_TPM_v1` is exactly `sqrt(GZMA_TPM * PRF1_TPM)` with no pseudocount. Original Rooney methods add 0.01 to TPM before the geometric mean. Preserve the existing mathematical comparator and A-P2/A-P1 contracts. In this amendment it is described as the **thesis-defined unoffset CYT variant**, not an exact Rooney reproduction. `CYT_ROONEY_OFFSET_REFERENCE` is a distinct source-method candidate; it neither replaces the primary nor becomes an authorized sensitivity without its own release. The offset can alter rankings near zero, so equivalence must not be assumed.

B-P remains external incremental R-squared for the existing fixed APM component. Broader immune-barrier evidence in B remains separately qualified secondary/exploratory work; no new composite primary or outcome-driven promotion is created.
