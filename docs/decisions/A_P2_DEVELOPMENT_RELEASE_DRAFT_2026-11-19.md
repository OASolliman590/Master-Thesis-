# A-P2 development release: one record for four runs (DRAFT)

**Status: DRAFT / UNAPPROVED. Nothing here authorizes a run or any outcome access.** Drafted 19 Nov 2026 under item 3 of the Paper A process simplification, relayed from the main thread as approved ("Approve all"). It replaces the four separate per-run release records foreseen in `A_P2_DEVELOPMENT_RELEASE_PROPOSED_2026-11-14.md` (now superseded). The user signs it only after every binding below is filled from real, patient-free receipts and every blocker is closed.

Authority: the signed amendment `specs/amendments/2026-11-14-a-p2-development-release/AMENDMENT.md` (15 Nov 2026, option A1), sections 2 to 7. This draft changes none of it.

## What a signature would release

The four development runs of section 7 of the amendment, once each, with the reviewed code named in the block below (`execution_code_sha256`):

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

Filled on 19 Nov 2026 from `prepare-development` on the private built inputs; re-run on 20 Nov 2026 after the review fixes changed the preparer (the record now also binds the execution code). The data-level hashes (tables, excluded list, identity sidecars, registries) did not change, only those that record code hashes. That run read patient identity columns and the GEO `io.therapy` field only; outcome gate `NOT_OPENED`. Re-verified with `--check-only`. All four packages: structural status PASS, no blocking overlap pair. The private outputs stay under `.scratch/runtime/a_p2/` (ignored by Git).

| Object | SHA-256 |
| --- | --- |
| Original built `features.tsv` (408 patients) | `75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a` |
| Built-input receipt `manifest.json` | `16365f3783661488aec82fb40d70b5eae97614da0f84b6b0961bf287ff86a376` |
| Pinned GSE176307 family SOFT | `ea242fbb98aa104c384a97a3d1f0baaa938031e91a5a3872b065982d73b1bf72` |
| A1 exclusion artifact (33 of 87 excluded) | `0dcb4721e9f9c59c56429920b0f738b628acc9b72d12f138c018b92f01e87072` |
| Excluded-token list | `8e58c8d851921059452a11721d80ded9afab9985bc652c3e59448f2ec4196372` |
| Derived table without the exclusions (375 patients) | `d5ce82f0ac5d6a38e75aeb78e7a8c0addcfad9f497482b8b8642bd3ce75eed12` |
| Input manifest, main | `02b6ae382b25e91200a7f7b352dd64a56bac7c176b8f29394e144434c1533b0e` |
| Input manifest, conservative | `eb6f25465a13a5b9503d9e62e8cd13d69b5935fa538f5c8b32d54b5669e5a59d` |
| Input manifest, bladder sensitivity | `0e5ad02187604ae75edc906eadc27c803b23017440e1a6783e17b6eeb4a8f9ac` |
| Input manifest, freeze | `40790946ad6b10fdf9e45ccbe94b4539dcd2b037e7ae484d539548c5a9a21a44` |
| Identity sidecar, main / conservative | `f80535f7520e9bc9db595c32de47d49be6c6d1576eca73c03c1275f2fc210751` / `9d37bff2749ed2f726c874b336f038410fa4c75434a9e033e9fbb243a4886d0e` |
| Identity sidecar, bladder sensitivity and freeze | `74dcfd1ef149663d6cc04c642438695d669461cbde9a459cae170317c736b48a` |
| Source / publication-family / overlap registry | `86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88` / `fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b` / `fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440` |
| Preparer code `tools/a_p2/prepare.py` | `64c6a8f211eeba1f30edb3c98db2879cfba721ef7b1f4029d00ce6cb1bd5ae75` |

Any later edit to the overlap registry or the preparer changes these hashes, and the preparation must be re-run before signing.

## Must be true before signing

1. **Done 19 Nov 2026.** Every development pair and every development-vs-IMvigor210 pair has a non-blocking status. The six melanoma or gastric pairs are Tier 3 (user-confirmed), and GSE176307 vs IMvigor210 is `RESOLVED_BY_SOURCE_RULE`.
2. **Done 19 Nov 2026.** The A1 exclusion artifact and the derived table exist and are hash-verified (33 of 87, 375 patients), as the signed amendment states.
3. **Done 19 Nov 2026.** The preparer reports no blocking pair, and its manifests match the bindings above.
4. **Done 19 Nov 2026.** The code reads the single block below (PA03) and enforces the four signed table and grouping pairings (PA04). Since 20 Nov 2026 (review fixes) the code also requires the approval pin described below, binds the reviewed code, and lets each run execute once. A real run is still refused: there is no approval pin until the user signs.

## Machine-readable release record

The code reads exactly this block. Plain-language explanation: `A_P2_WHAT_YOU_ARE_APPROVING.md`.

To sign:

1. Change `record_status` from `UNAPPROVED` to `APPROVED` and sign below. Change nothing else in the block.
2. Save the approval pin: the SHA-256 of the block's JSON in canonical form (keys sorted, separators `,` and `:`, UTF-8), written as one lowercase hex line to `docs/decisions/A_P2_DEVELOPMENT_RELEASE_V3.approved.sha256`. Claude provides the one-line command at signing time.

Without the pin every real run is refused. After pinning, any edit inside the block (any run's row, any hash, the status) makes every run refuse; edits to the prose outside the block do not. Each run then executes once: before it reads any outcome, it records a claim for this approval and package, and a repeat is refused. A change to the analysis code changes `execution_code_sha256` and is refused too, so the block would need re-preparing and a new signature.

```a-p2-release-v3
{
 "a1_source_rule": {
  "derived_features_sha256": "d5ce82f0ac5d6a38e75aeb78e7a8c0addcfad9f497482b8b8642bd3ce75eed12",
  "exclusion_artifact_sha256": "0dcb4721e9f9c59c56429920b0f738b628acc9b72d12f138c018b92f01e87072",
  "rule_id": "A_P2_ATEZO_FREEZE_EXCLUSION_V1"
 },
 "data_classification": "PRIVATE_PATIENT_LEVEL",
 "execution_code_sha256": {
  "measurement_decision": "baa0637786ffe1b46641a5ece803e089423bb43c8a552afcf62f5261f04c6f02",
  "numerical_freeze_register": "0b0a39b96e4c391df792e363fa2d1a8309038f0ac87a71d52fdb6c0b054dd440",
  "panel_registry": "454a284292ea8b124a59767dd6a1024248ab1ed0b6013ecb948c762cda8979e9",
  "python_cli": "0113bf49a15f35a58b453a15085dbde68f1aee6d846e539d49cc958f5b39edb2",
  "python_product": "35695310f202c7ee56b1106a328336a173cf7ae420597dbb6363a92413d57e48",
  "r_bridge": "9add64989120e4c27667518f0b8363dfa0ebb0492a5b32c67412e3a87e4af679",
  "r_entrypoint": "e6e9a166132759951d51ff979b3a5e1526dcc776621f7e605ad5ba88bb78c815",
  "r_random_streams": "f4e69798059290964dadfccb5c49200cb48a5a8c39835dee62b15b76535fca5d",
  "renv_lock": "8ccd9f41d6e3e50cd0690202e1f1e3f442702f9439baf398687c26dc8d96f7bc",
  "validation_contract": "3ea7cd1548fbecf6f565b9e158e853589df451cd856da548677b8931a680b64e"
 },
 "record_status": "UNAPPROVED",
 "record_type": "a_p2_user_release_v3",
 "release_scope": "A_P2_REAL_OUTCOME_ACCESS",
 "runs": [
  {
   "cohorts": [
    "gide2019",
    "gse176307",
    "hugo_gse78220",
    "kim2018",
    "liu2019",
    "riaz_gse91061",
    "vanallen2015"
   ],
   "identity_sidecar_sha256": "f80535f7520e9bc9db595c32de47d49be6c6d1576eca73c03c1275f2fc210751",
   "input_manifest_sha256": "02b6ae382b25e91200a7f7b352dd64a56bac7c176b8f29394e144434c1533b0e",
   "input_role": "development",
   "input_sha256": "75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a",
   "operation": "development",
   "outcome_fields": [
    "orr_class"
   ],
   "overlap_registry_sha256": "fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440",
   "package_id": "main",
   "publication_family_registry_sha256": "fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b",
   "source_registry_sha256": "86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88"
  },
  {
   "cohorts": [
    "gide2019",
    "gse176307",
    "hugo_gse78220",
    "kim2018",
    "liu2019",
    "riaz_gse91061",
    "vanallen2015"
   ],
   "identity_sidecar_sha256": "74dcfd1ef149663d6cc04c642438695d669461cbde9a459cae170317c736b48a",
   "input_manifest_sha256": "40790946ad6b10fdf9e45ccbe94b4539dcd2b037e7ae484d539548c5a9a21a44",
   "input_role": "development",
   "input_sha256": "d5ce82f0ac5d6a38e75aeb78e7a8c0addcfad9f497482b8b8642bd3ce75eed12",
   "operation": "freeze",
   "outcome_fields": [
    "orr_class"
   ],
   "overlap_registry_sha256": "fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440",
   "package_id": "freeze",
   "publication_family_registry_sha256": "fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b",
   "source_registry_sha256": "86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88"
  },
  {
   "cohorts": [
    "gide2019",
    "gse176307",
    "hugo_gse78220",
    "kim2018",
    "liu2019",
    "riaz_gse91061",
    "vanallen2015"
   ],
   "identity_sidecar_sha256": "74dcfd1ef149663d6cc04c642438695d669461cbde9a459cae170317c736b48a",
   "input_manifest_sha256": "0e5ad02187604ae75edc906eadc27c803b23017440e1a6783e17b6eeb4a8f9ac",
   "input_role": "development",
   "input_sha256": "d5ce82f0ac5d6a38e75aeb78e7a8c0addcfad9f497482b8b8642bd3ce75eed12",
   "operation": "development",
   "outcome_fields": [
    "orr_class"
   ],
   "overlap_registry_sha256": "fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440",
   "package_id": "development_sensitivity",
   "publication_family_registry_sha256": "fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b",
   "source_registry_sha256": "86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88"
  },
  {
   "cohorts": [
    "gide2019",
    "gse176307",
    "hugo_gse78220",
    "kim2018",
    "liu2019",
    "riaz_gse91061",
    "vanallen2015"
   ],
   "identity_sidecar_sha256": "9d37bff2749ed2f726c874b336f038410fa4c75434a9e033e9fbb243a4886d0e",
   "input_manifest_sha256": "eb6f25465a13a5b9503d9e62e8cd13d69b5935fa538f5c8b32d54b5669e5a59d",
   "input_role": "development",
   "input_sha256": "75b3b1b04653d605a6bde1027bc8050cf3ff363e93fbd0fa5b2f72813d81726a",
   "operation": "development",
   "outcome_fields": [
    "orr_class"
   ],
   "overlap_registry_sha256": "fe7b341e40f5d608e71e6cded567d7038facbb584d8051246ecef53be0c60440",
   "package_id": "conservative",
   "publication_family_registry_sha256": "fd2c0b8e75451644d3e352ddba21ed1b5a189e33e76d813a169e3d047497ce3b",
   "source_registry_sha256": "86f5260a4fb4738a96d8a82bda80b673658327b855dcb1a64ca8596ea4551a88"
  }
 ]
}
```

## Signature

Release decision: approve the four runs above ____ / do not approve ____

Signed: ____________________  Date: __________
