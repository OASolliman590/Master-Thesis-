# Paper A source checkpoint: Astra disposition

6 September 2026. Reviewed specification/source milestone, not cohort admission or scientific implementation. Both A-P1 and A-P2 remain proposals. The default B → C → A → conditional D production sequence and separate wet-lab requirement are unchanged.

## Accepted evidence and corrections

- Riaz: original author metadata recovers all 51 baseline subjects, original BOR and prior-ipilimumab strata. The real FPKM header matches all 109 GEO profiles. The 49 category-labelled ceiling is not the author's 45-subject analytical set: source exclusions and the Pt3 discrepancy remain unresolved. Distinct duplicate `Response` columns require positional meaning; no generic punctuation stripping is permitted.
- Hugo: 28 profiles contain one on-treatment specimen and two baseline sites from one patient, yielding 26 distinct baseline patient codes. Site selection, irRECIST/category-correction reconciliation, full workbook suitability and biological independence from Riaz remain open. No shared deposited assay IDs does not prove disjoint patients.
- Rose: 90 assays represent 89 patient codes, with 88 labelled. The current TPM header has 92 columns, two absent from the source key. Timing, clinical nonresponse exceptions, repeated-assay representation and full-matrix checks remain admission gates. The precision paragraph now uses patient ceilings, not assay counts.
- COMBAT: the actual 26,467-row workbook joins all 30 GEO titles/15 paired subjects and contains the two CYT genes. All column sums contradict unmodified standard pmeTPM; source count language does not prove the exact export or authorize a TPM conversion. Original C4D1 BAT response, later trial endpoint and public15/published12 selection remain distinct. The candidate 352%/353% clinical discrepancy is preserved, not repaired by assumption.
- COMPASS: the July2026 final publication adds a current direct precedent for cross-cancer transcriptomic prediction. The bounded note does not reproduce model code/results, select a primary or add a mandatory comparator.

## Review evidence

Two delegated original-source audits plus an independent COMBAT review are retained under docs/research/. Astra independently recounted Rose patients/categories/key mappings directly from raw SOFT and the official name key; checked original Rose clinical methods; recounted Riaz BOR/prior-treatment strata using positional CSV columns while verifying unique BAM names; and recounted Hugo baseline patient categories from raw SOFT. See `../research/A_ROOT_SOURCE_COUNTS.json`. COMBAT was independently recomputed using XLSX XML and Decimal arithmetic rather than the initial openpyxl implementation. Astra checked the original COMBAT RNA-methods/subset paragraphs and the published COMPASS date/description.

Final source-specific integration reviews are adjacent to the retained source reports. Their minor findings were resolved: stale all-5-September dating, the old Rose precision denominator, and A04's historical-only evidence locator. The original Riaz review retains its pre-fix locator suggestion as review history; current A04 links the new admission reports.

Scope limitations remain explicit. These are lightweight source/format/metadata checks, not tests of clinical discrimination, trained models, methylation effects or drug response. Small original article previews exposed published findings. No source expression workbook, complete clinical crosswalk, raw sequencing or model weights are committed. The copied audit helpers require their recorded outer source layout and are not a production implementation.

## Readiness and next actions

Keep Paper A's parent issue OPEN and WIP. Resolve the scientific primary separately; neither documentation nor available catalogue counts constitutes approval. Before any scoring: settle source-specific specimen/response rules, verify complete assay features/units, resolve required overlaps and exposure, freeze development/final-test roles, and assess precision for that exact design. Preserve unavailable sources in the coverage record rather than manufacturing labels or silently redefining the endpoint.

B-F1 code is unchanged. Its final Opus recheck remains pending after quota exhaustion. The AIU probe in this continuation timed out with exit1; no new remote job was started. Server tests remain queued against the exact existing code commit. No new biological or production test pass is claimed by this source checkpoint.
