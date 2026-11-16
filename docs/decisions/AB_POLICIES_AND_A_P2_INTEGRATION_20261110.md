# A/B policies and local A-P2 integration — 10 November 2026

Status: user-approved policies, recorded from the chat; no agent signature. This record adds to existing decisions and does not edit frozen specifications.

User instruction: “yes approve those policies with the two additions and merge A-P2 locally, no push. reuse the existing reviews, write the A3 decision sheet, and keep real outcomes and the real rebuild locked”.

| ID | Approved scope |
| --- | --- |
| A1 | Preserve original expression tables. Resolve duplicate rows only with verified annotation; exclude unresolved ambiguous genes from derived tables rather than averaging them automatically. Mark affected panels unavailable if required coverage fails. Record this resolution rule in the register before any outcome read. If Van Allen or GSE145996 contribute to A-P2, compare the relevant input, mapping, membership and feature hashes before and after any approved transformation; record changed hashes and their cause. A change does not authorize regeneration or the deferred real rebuild. |
| A2 | Admit longitudinal pairs only with verified patient identity, the same treatment episode and study-specific documented sampling windows. Unknown dates stay unknown. Gide's unverified early-treatment mapping remains pending; verified pairs elsewhere may progress under their source-specific record. This policy does not sign unknown N12/N13 parameter values or admit an unverified pair. |
| A3 | Prepare a decision sheet for clinical adjustment, post-meta ranking and the A-to-B/C handoff. No blanket approval of its proposed choices. |
| A4 | Defer the unsigned A-RCT Change 1 and CIBERSORTx; do not drop them from scope. |
| B1 | One independently verified patient contribution, with compatible tumour specimens linked across RNA and methylation. Prefer the primary tumour where a patient has several specimens. The deciding evidence is the original study's specimen/pathology record and assay linkage; for TCGA, use the GDC biospecimen/sample-type record. Derived portal labels and name/suffix similarity cannot overrule the source record. Conflicting records or multiple eligible primary specimens remain unresolved until a source-specific selection or technical-replicate rule is accepted; do not average distinct tumours. |
| B2 | Retain the signed Tier 1–2 primary family and Tier 3 exploratory role. Present the actual gene, promoter, purity-source and global-methylation probe lists for signature after verification. The lists themselves are not approved by this policy. |
| B3 | Finish matched RNA/methylation tables and the primary per-gene pipeline first, then the main cross-cancer comparison and descriptive prostate cell context. Defer exploratory multi-omics and B-METHRESP until the core is ready; B-METHRESP stays last/first cut under the existing budget order. |

The companion `AB_POLICY_REGISTER_20261110.tsv` records A1 before any new transformation or outcome access. No source rows, matrices, patient records or existing admission worksheets were changed to record these policies. If regenerated worksheet items differ, show the difference to the user and stop before accepting it.

## Local integration scope and observed state

Only the existing A-P2 commit `bd8efb5221bd43068b211b0b4f9001565e160cda` is authorized for local integration into `codex/a-dav-01`. No other worktree commit, merge or push is authorized by this instruction. Reuse the completed reviews; no new Astra review was started.

At this turn's first check, the destination branch already contained local merge `e032ff7768f8660536165a7b6edf2093d31c558e`, with parents `336094c00fc98e453fc4a109623f2e4a31b34d73` and the approved A-P2 commit. Its tree equals the A-P2 commit's tree. This turn verifies that existing merge; it does not recreate it or claim to have performed it. The merge's nine source files are checked against the approved commit and the previously tested combined checkout. New policy/register/sheet documents remain uncommitted.

## Locks retained

Real outcomes remain locked, including class counts and feature–outcome summaries under the current user lock. The real A-P2 rebuild remains deferred. IMvigor210 remains UNTOUCHED_FINAL_TEST across papers and representations. No final-test or cohort admission is released. Existing source, exposure and scientific gates remain open. No private key or server handover access; AIU stays deferred. No push is performed.
