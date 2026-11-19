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

## Bindings

The record binds the inputs by SHA-256. It does **not** bind this decision document: the document is the human-readable signature, and binding it to itself is circular.

Filled on 19 Nov 2026 from `prepare-development` on the private built inputs. That run read patient identity columns and the GEO `io.therapy` field only; outcome gate `NOT_OPENED`. Re-verified with `--check-only`. All four packages: structural status PASS, no blocking overlap pair. The private outputs stay under `.scratch/runtime/a_p2/` (ignored by Git).

| Object | SHA-256 |
| --- | --- |
| Original built `features.tsv` (408 patients) | `75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a` |
| Built-input receipt `manifest.json` | `16365f3783661488aec82fb40d70b5eae97614da0f84b6b0961bf287ff86a376` |
| Pinned GSE176307 family SOFT | `ea242fbb98aa104c384a97a3d1f0baaa938031e91a5a3872b065982d73b1bf72` |
| A1 exclusion artifact (33 of 87 excluded) | `39f09294c87b6977fea81e807a9f91706f71ea7d8890f87cc94b0d632962e11d` |
| Excluded-token list | `8e58c8d851921059452a11721d80ded9afab9985bc652c3e59448f2ec4196372` |
| Derived table without the exclusions (375 patients) | `d5ce82f0ac5d6a38e75aeb78e7a8c0addcfad9f497482b8b8642bd3ce75eed12` |
| Input manifest, main | `ad2b1968b1af4537face8cb05299561253cfbf1502fb3f6b0de36d49ca3dd984` |
| Input manifest, conservative | `97dedde27afbc9ed61c76f4b18e57e949a21eb443d3743280a4f0f845afbdd9e` |
| Input manifest, bladder sensitivity | `23c8bcb473863f0b968c057bb4e844dd7937f2032157001e7551ca422711cd7b` |
| Input manifest, freeze | `316e8586654919988253ba62f0ff8e319c03cef86739b88b3913a491a0adab6b` |
| Identity sidecar, main / conservative | `f80535f7520e9bc9db595c32de47d49be6c6d1576eca73c03c1275f2fc210751` / `9d37bff2749ed2f726c874b336f038410fa4c75434a9e033e9fbb243a4886d0e` |
| Identity sidecar, bladder sensitivity and freeze | `74dcfd1ef149663d6cc04c642438695d669461cbde9a459cae170317c736b48a` |
| Source / publication-family / overlap registry | `86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88` / `fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b` / `fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440` |
| Preparer code `tools/a_p2/prepare.py` | `97ecd9a94f53e23b455f6c0bf288e752cecc805423a576a0341f066f80efd65c` |

Any later edit to the overlap registry or the preparer changes these hashes, and the preparation must be re-run before signing.

## Must be true before signing

1. **Done 19 Nov 2026.** Every development pair and every development-vs-IMvigor210 pair has a non-blocking status. The six melanoma or gastric pairs are Tier 3 (user-confirmed), and GSE176307 vs IMvigor210 is `RESOLVED_BY_SOURCE_RULE`.
2. **Done 19 Nov 2026.** The A1 exclusion artifact and the derived table exist and are hash-verified (33 of 87, 375 patients), as the signed amendment states.
3. **Done 19 Nov 2026.** The preparer reports no blocking pair, and its manifests match the bindings above.
4. Code follow-up: `tools/a_p2/prepare.py` still emits one `a_p2_user_release_v2` form per run and binds the superseded proposal with a pending decision hash. It must emit one record for the four runs, binding inputs only. This is a separate ticket; nothing was changed here.

## Signature

Release decision: approve the four runs above ____ / do not approve ____

Signed: ____________________  Date: __________
