# Riaz baseline scope and author BOR decision

**Status:** baseline-only scope and author BOR approved by the user on 26 October 2026 (Cairo). QC rules are proposed separately, not approved by this decision. The user said: “go ahead with baseline only and author BOR. propose the QC rules and implement what can proceed”. The same instruction prohibits frozen-spec changes, biological analysis and signing on the user's behalf.

## Approved behavior

- Prepare a new `A_BASELINE_BIO` packet using source-supported pretreatment specimens and their linked patients, assays, original outcomes and treatment context. Preserve the original ingestion packet, source objects and all source inventory. On-treatment issues remain visible for A.1; they do not silently become corrected identities.
- Use the pinned author clinical table's BOR as source of record. Preserve raw BOR and corroborating GEO labels. Apply the existing endpoint ontology: CR/PR objective responder, SD/PD objective nonresponder, NE/unknown unevaluable. Preserve unevaluable source records; they cannot receive a negative ORR label.
- Rebuild metadata-stage dependencies under the complete new configuration and write a new unsigned worksheet. The software must not copy an old signature or mark source admission approved.

These are metadata preparation decisions. They do not select a numerical expression representation, pass assay QC, resolve cross-study overlap or prior-model exposure, approve a final analytical denominator, or authorize analysis. They do not inherit the author's unexplained four exclusions or the separate publication PCA exclusion.

## Evidence and remaining decisions

The source evidence is in the [nine-question review](../research/A_DAV_RIAZ_DECISIONS_20261026.md), [clinical review](../research/A_DAV_RIAZ_CLINICAL_REVIEW_20261026.md) and [identity review](../research/A_DAV_RIAZ_IDENTITY_REVIEW_20261026.md). The [frozen endpoint ontology](../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md) governs the categorical mapping. The [QC proposal](../research/A_DAV_RIAZ_QC_PROPOSAL_20261026.md) lists the checks and remaining choices.

The frozen [episode-binding schema](../../specs/A_DATA_ACQUISITION_VALIDATION/schemas/episode_binding.schema.json) requires a reviewer and review time for a VERIFIED binding. No human name, date or signature will be fabricated to satisfy it. Public-source evidence can support a proposal; it cannot supply a signature. Source-binding review and V7 approval remain unsigned.

## Implementation and verification

Luna implemented `tools/a_dav/baseline_policy.py` and invented-data boundary tests. The command applies the approved scope and BOR mapping to a copy of canonical ingestion records, requires the pinned Riaz source identities, preserves raw labels and source inventory, retains all nine source questions, and rebuilds a matching unsigned reviewer worksheet. It applies no proposed QC or exclusion rule.

The parent ran the command on the retained public-source metadata. The new private bundle is `.scratch/runtime/riaz_gse91061/baseline-bor-20261026/`. It contains 51 patients, 51 baseline specimens, 102 assay records (two representations per specimen), and all nine source objects. Both NE records remain present with null ORR; 49 is only the upper bound with evaluable source BOR categories before later gates. No endpoint rows or analytical matrix were materialized. The original packet's hash is unchanged, and the generated worksheet's context matches its packet. Its nine source questions and nine gate questions remain unsigned.

Registries are READY. The endpoint policy is now configured, but endpoints remain blocked by `ENDPOINT_EPISODE_UNKNOWN`: no reviewed treatment-response binding exists. Timing remains `INDEX_TREATMENT_UNRESOLVED`; assays, overlap and prior exposure remain `ASSAY_POLICY_UNKNOWN`, `OVERLAP_POLICY_UNKNOWN` and `EXPOSURE_POLICY_UNKNOWN`. These are outstanding evidence, policy or human-review inputs; the command does not turn them into fabricated facts or approvals.

QC approval and selection between the retained author hg19 FPKM and NCBI GRCh38 TPM are the next policy choices. After those choices, implement and run the approved technical checks, finish source-supported treatment/timing and overlap/exposure review, regenerate the final worksheet, and obtain the legitimate human signature. Public-source review does not require another custody search or two-reader rehearsal under the accepted public-reviewer amendment.

Parent verification: the initial combined policy/preparation/worksheet/ingestion suite passed 36 tests with one opt-in tracer skipped. Astra found one conflict-preservation defect: a narrow NE/UNK crosswalk could clear another substantive disagreement. Luna fixed it and added regression coverage; all 8 focused policy tests passed after the fix, and Astra confirmed the finding closed without expanding the review. Strict mypy passed all four checked production modules. The parent reran the real metadata command after the fix and checked counts, null NE, unsigned worksheet context, unchanged original packet and source inventory. All 1,343 frozen/historical file hashes matched the saved snapshot; `git diff --check` passed and private outputs are ignored. No biological analysis, signing, admission or commit occurred.
