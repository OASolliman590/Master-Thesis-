# A-P2 development release: one record for four runs (DRAFT)

**Status: DRAFT / UNAPPROVED. Nothing here authorizes a run or any outcome access.** Drafted 19 Nov 2026 under item 3 of the Paper A process simplification, relayed from the main thread as approved ("Approve all"). It replaces the four separate per-run release records foreseen in `A_P2_DEVELOPMENT_RELEASE_PROPOSED_2026-11-14.md` (now superseded). The user signs it only after every binding below is filled from real, patient-free receipts and every blocker is closed.

Authority: the signed amendment `specs/amendments/2026-11-14-a-p2-development-release/AMENDMENT.md` (15 Nov 2026, option A1), sections 2 to 7. This draft changes none of it.

## What a signature would release

The four development runs of section 7 of the amendment, once each, with the code at the commit named below:

| Run | Input table | Patients | Families | Outcome field |
| --- | --- | --- | --- | --- |
| Development, main | original built table | 408 | 6 | `orr_class` |
| Development, conservative | original built table | 408 | 4 | `orr_class` |
| Development, bladder sensitivity | derived table without the A1 exclusions | 375 | 6 | `orr_class` |
| Freeze | derived table without the A1 exclusions | 375 | 6 | `orr_class` |

Each run includes the signed cohort-adaptive sensitivity on its 7 cohorts. Braun is out of scope (separate implementation and release). Both main and conservative results are reported whatever their direction.

**Not released:** IMvigor210 (`UNTOUCHED_FINAL_TEST`), `final-evaluate`, any comparator or novelty claim, and the real A-P2 rebuild (still deferred). The final test needs its own release, after the prior-exposure audit.

## Bindings (to be filled from patient-free receipts; none is asserted yet)

The record binds the inputs by SHA-256. It does **not** bind this decision document: the document is the human-readable signature, and binding it to itself is circular.

| Object | SHA-256 |
| --- | --- |
| Original built `features.tsv` | ____ |
| Built-input receipt `manifest.json` | ____ |
| A1 exclusion artifact (`A_P2_ATEZO_FREEZE_EXCLUSION_V1`) | ____ |
| Derived table without the exclusions | ____ |
| Input manifest, main / conservative / bladder sensitivity / freeze | ____ / ____ / ____ / ____ |
| Identity sidecar | ____ |
| Source, publication-family and overlap registries | ____ / ____ / ____ |
| Code commit | ____ |

The 14 Nov hashes in the superseded proposal are historical and must not be copied here unverified.

## Must be true before signing

1. Every development pair and every development-vs-IMvigor210 pair has a non-blocking status in `docs/validation/A_P2_IDENTITY/OVERLAP_REGISTRY.tsv`. On 19 Nov 2026 one is still `UNRESOLVED`: GSE176307 vs IMvigor210 (A1 source rule, below). The six melanoma or gastric vs IMvigor210 pairs were set to Tier 3 on the user's direct confirmation that day.
2. The A1 exclusion artifact and the derived table exist, are hash-verified, and GSE176307 vs IMvigor210 is `RESOLVED_BY_SOURCE_RULE`.
3. The preparer reports no blocking pair, and its emitted manifests match the bindings above.
4. Code follow-up: `tools/a_p2/prepare.py` still emits one `a_p2_user_release_v2` form per run and binds the superseded proposal with a pending decision hash. It must emit one record for the four runs, binding inputs only. This is a separate ticket; nothing was changed here.

## Signature

Release decision: approve the four runs above ____ / do not approve ____

Signed: ____________________  Date: __________
