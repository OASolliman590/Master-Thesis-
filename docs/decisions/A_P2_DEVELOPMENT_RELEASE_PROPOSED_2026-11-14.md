# A-P2 development and freeze release proposal

> **SUPERSEDED on 19 Nov 2026** by `A_P2_DEVELOPMENT_RELEASE_DRAFT_2026-11-19.md` (one release record for the four development runs; still unapproved). Reason: the Paper A process simplification (item 3) replaces four per-run records with one. The 90-versus-87 identity count below is not a live mismatch (the signed 15 Nov amendment, section 5). Kept unchanged below as a historical record. `tools/a_p2/prepare.py` still refers to this file until its follow-up ticket.

**Status: PROPOSED / UNAPPROVED. No run or outcome access is authorized.** Updated 18 November 2026 to reflect the signed 15 November amendment. This is not a release record and must not be signed as one.

## Scope and interpretation

The signed design permits four separately bound future packages: main development (408 patients, six families), conservative development (408, four families), reduced bladder sensitivity (375, six families), and freeze (375, six families). The full and reduced development sets and freeze have distinct scientific roles. Every package needs its own user-signed run release. The seven-cohort adaptive sensitivity is included; Braun requires separate implementation and release. Final evaluation and IMvigor210 remain locked under a separate gate. Prior-exposure audit is required before final-test release or comparator/novelty claims.

The A1 source rule removes from the freeze representation any GSE176307 patient with any atezolizumab, missing or conflicting agent. The signed amendment records 33 exclusions among 87 built bladder patients and states the important residual risk of prior unrecorded atezolizumab. The presence of 90 source tokens and 87 built tokens is not itself a mismatch: each built token must be found in the source. These are signed historical aggregate facts; this cycle did not verify them against real inputs.

## Outstanding bindings and release gate

No real preparer or input was accessed. Full current SHA-256 bindings for the original and derived inputs, build receipt, A1 exclusion artifact, source, manifest, identity sidecar, registries, code, and signed decision must be verified from patient-free receipts and actual authorized artifacts; none is asserted here. The historical shortened feature hash is not a release binding. The six non-bladder development/final-test pairs presently lack pair-specific evidence in the transferred registry and remain UNRESOLVED. The bladder/final-test pair is UNRESOLVED until the A1 artifact and derived freeze input are executed and verified under a separately authorized scope. Missing evidence blocks the release.

The generated `a_p2_user_release_v2` shape binds operation, role, manifest, input, sidecar, registries, cohort list, outcome field and decision record. Each must remain UNAPPROVED until the user signs the exact per-run record. No real form was regenerated in this cycle: no synthetic hash may be placed on one. Before accepting any regenerated worksheet or form, compare its items with the applicable existing form and show material differences to the user; no such comparison or acceptance is claimed here.

## Exact next action

The parent should first obtain patient-free receipts for full current hashes and complete pair-specific source evidence without opening final-test data. Review and resolve any form-item differences, then prepare the first development-run record with real, verified bindings for the user's signature. A user-signed amendment alone is not permission to run; the real rebuild remains deferred.

## Historical worksheet items — retained, pending user review

The following unchecked items are reproduced as historical worksheet text; the signed amendment supersedes the stated mismatch, and the real rebuild remains deferred. Their removal or change has not been accepted.

- [ ] **Use the existing hash-verified inputs.** The feature table remains unchanged. Preparation must first resolve the exact 90-versus-87 identity-token discrepancy outcome-free; only then can hash-bound manifests, sidecars, and release templates be generated.
- [ ] **Defer a fresh rebuild until separately authorized.** A rebuild would produce new input and receipt hashes and require the identity comparison to be repeated. The current builder still has no Braun branch, so rebuilding cannot supply Braun.

**Historical user input choice:** existing inputs ____ / defer rebuild ____  **Signature:** ____________________  **Date:** __________

## Historical full-hash provenance (14 November; not current release bindings)

| Object | SHA-256 |
| --- | --- |
| Built `features.tsv` | `75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a` |
| Built-input receipt `manifest.json` | `16365f3783661488aec82fb40d70b5eae97614da0f84b6b0961bf287ff86a376` |
| Pinned GSE176307 family SOFT | `ea242fbb98aa104c384a97a3d1f0baaa938031e91a5a3872b065982d73b1bf72` |
| Source registry | `86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88` |
| Publication-family registry | `fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b` |
| Overlap registry | `caab01717f04b62934ac92f5049844b566237ee7379a8c5e32119fc787e3ca21` |
| Frozen programme registry | `747c8264b36e2c06dc378d27f5f33136d05339163a553899becf64319d692cd2` |
| Frozen gene-alias table | `96dc5e0299e31527350ba5a3f7bfbd7f18131a4db2c91e19a0f18078d895c4e0` |
| Receipt builder source object (`tools/a_p2/build.py`) | `6ea818d75b049b596222db4bd641861b5a2bed1b2679174a0487f427f044f7b9` |

The historical proposal reported that the builder hash was verified against reachable historical git content at `c179c6d`; it is intentionally not compared with the current working copy of `build.py`.

The historical proposal stated that eventual manifests would declare `data_classification = PRIVATE_PATIENT_LEVEL`, `role = development`, the exact input-table path and SHA-256, the source-derived cohort map and transform contract, and the product's frozen CYT definition `sqrt(TPM_GZMA * TPM_PRF1)`. Frozen panel-membership hashes are:

| Feature | Membership SHA-256 |
| --- | --- |
| `P_ANTIGEN_PRESENTATION` | `824b243b5c3ff237a00b3cc60b88590e253424ebe542546c90d521f778a6caaa` |
| `M2_CYTOTOXICITY` | `66aed07c891c806c0bbb810fd4f707259520b2198c7c9644b36cd86c5a8a2801` |
| `M3_VIRAL_MIMICRY` | `fcdb5ffab621cc3a921c247f8e171f66b3beb4a2146ed330c68f75a87a296895` |
| `M4_EXCLUSION` | `fcede329b70df14024eed1a3413f283646fb02d14b5420e189ff3c4e09e3c387` |


These values are transcribed historical provenance, not verified current bindings; do not put them into a real release form without current verification.
