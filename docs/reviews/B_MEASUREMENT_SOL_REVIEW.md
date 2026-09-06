# Paper B measurement checkpoint — Sol integration review

6 September 2026. Review base: `cce0c5d02d6d698293cf81f37190362f80065ccb`; target: the unpublished working-tree changes under `specs/B`, `docs/execution/PROGRESS.md`, `docs/research/B_MEASUREMENT_CHECKPOINT.md`, and `docs/research/B_measurement/`.

## Verdict

**Publication-blocked on evidence packaging; no biological or primary-selection defect found.** The numerical source claims checked here agree with the retained machine-readable summaries and the two outer peer reviews. The checkpoint consistently leaves B-P/B-R, final U, final Q, specimen policy, final eligible N, covariate comparability and precision unselected. No molecular score/model, scientific implementation or change to B-F1 is present in the reviewed delta.

This review does not establish AIU validation or the outstanding final Opus recheck.

## Standards axis

### High — advertised artifact inventory is absent

`docs/research/B_MEASUREMENT_CHECKPOINT.md:36` says `B_measurement/ARTIFACTS.json` inventories the committed checkpoint, but that file is absent. The repository therefore has no authoritative inventory tying the selected copied files to their roles, hashes, omitted cache inputs and outer originals. Add the promised inventory, including the two peer-review receipts below, or remove the claim and replace it with an exact equivalent manifest before publication.

### Medium — copied helper does not retain its original cache resolution

`docs/research/B_measurement/B_promoter_semantics/audit_promoters.py:16-24` derives `B_annotation` as a sibling of its current script directory. After copying, that resolves to missing `docs/research/B_measurement/B_annotation/`, not the existing outer cache at `E:/Master_Thesis/planning/next_evidence/B_annotation/`. `crosscheck_transcripts.py:17-33` and `B_expression_platform_contract/inspect_annotations.py:7-16,27-35` also require omitted cached/generated inputs. The general warning in checkpoint line 36 is directionally correct, and `PROVENANCE.json`/`hash_register.json` disclose many hashes and outer paths, but the statement that the helpers retain their original paths is not correct for the promoter helper. Document an exact restore layout/command or make input roots explicit; do not present the copied scripts as directly rerunnable.

### Medium — cached TCGA helper can rewrite retrieval provenance

`docs/research/B_measurement/B_TCGA_cellularity/retrieve.py:6-14` reuses an existing cached body but always writes the current time into `retrieved_utc`. A cache-only rerun would therefore overwrite the original retrieval time with a false fresh-retrieval timestamp. Preserve the original `retrieved_utc` and record a separate `verified_utc`, or require a new response before updating retrieval time. Do not run this copied helper to repair the checkpoint.

### Low — copied reports retain stale location statements

`B_expression_platform_contract/REPORT.md:3` says all artifacts remain outside the canonical repository, and `B_promoter_semantics/REPORT.md:78` says candidate exports/scripts remain outside it. Selected artifacts are now copied into the repository. Mark these sentences as historical audit-time statements or add a wrapper note distinguishing byte-identical copied evidence from omitted outer-cache inputs.

### Low — the pending tracked diff fails whitespace validation

`git diff --check HEAD` reports trailing whitespace on the added lines in `ANALYSIS.md`, `DATA_AND_SOURCES.md`, `PREREGISTRATION_AND_LEDGER.md`, `README.md`, `REPRODUCE_AND_READINESS.md`, `SOURCE_MANIFEST.json` and `TICKETS_AND_TESTS.md`. On this Windows checkout the symptom is consistent with line-ending conversion on newly written lines, but the publication diff still fails the repository-level check. Normalize only the affected files/lines without changing content and rerun `git diff --check` before publication.

### Judgement call — provenance helper naming is opaque

`docs/research/B_measurement/B_TCGA_cellularity/audit.py:3-10` uses `p`, `s`, `c`, `v`, `pr`, `vm`, `vc` and `rr` for provenance-critical entities. This is possible **Mysterious Name**, not a hard violation; descriptive names would reduce review risk if the helper is ever promoted beyond a historical audit snapshot. No other applicable Fowler smell was found in this documentation/source-only delta.

## Spec and evidence axis

### Medium — two completed independent review receipts are not integrated

The checkpoint links the expression and promoter source reports but only the TCGA independent recount (`docs/research/B_MEASUREMENT_CHECKPOINT.md:17-20`). The completed reviews remain outside Git:

- `E:/Master_Thesis/planning/next_evidence/B_promoter_semantics/EXPRESSION_REVIEW.md`, SHA-256 `4a3f5fd4bfb27e1c2990c72ed5912d140bd7f1338fee74345eaa5e1c55663ca7`.
- `E:/Master_Thesis/planning/next_evidence/B_cellularity_methods/PROMOTER_REVIEW.md`, SHA-256 `f3b75087b2e3bac29e520a8de75fe3c589ee2a6ade185f740ef47fba14c08966`.

Copy/link/hash these receipts in the canonical package before treating expression and promoter independent verification as integrated. Both reviews report no material counting error while preserving the same limitations; neither establishes AIU or Opus validation.

### Medium — spec headers overstate proposed contracts as verified

Six edited spec headers, for example `specs/B/DATA_AND_SOURCES.md:3`, call the link “verified platform, promoter and cellularity contracts.” The checkpoint itself says “source evidence and proposed measurement contracts” (`docs/research/B_MEASUREMENT_CHECKPOINT.md:3`) and leaves the annotation policy, estimator comparability and specimen linkage open. Change the headers to “verified source facts refining proposed contracts” or equivalent.

### Medium — promoter definition still reads as a selected manufacturer-category rule

`specs/B/DATA_AND_SOURCES.md:37` still defines candidates using a TSS200/TSS1500 annotation category, while the checkpoint distinguishes manufacturer category from source-label/CDS-span literal-distance policies and says none is frozen (`docs/research/B_MEASUREMENT_CHECKPOINT.md:9,26`). Recast the old sentence as one unselected option or state a neutral decision gate. Otherwise a future implementer could silently use manufacturer categories even though the new evidence explicitly treats that as a separate, undecided policy.

### Low — source-manifest snapshot label is stale

`specs/B/SOURCE_MANIFEST.json:301` still describes the snapshot as the 5 September expression/B-F1 update, while lines 315-343 add the 6 September measurement checkpoint. Update the snapshot label or add a measurement-specific version field so the human-readable version agrees with the payload.

## Confirmed invariants and source checks

- All 26 copied checkpoint files are byte-identical to their same-named outer audit originals; no copied file differed.
- JSON parsing succeeded for `specs/B/SOURCE_MANIFEST.json` and every copied JSON artifact.
- Retained summaries reproduce: 213 distinct expression patients; 24,937 common candidate v18 Entrez IDs; all eight targets present in both databases; 403/288 literal source-label promoter memberships/unique probes; 318/203 positive-CDS alternative memberships/unique probes; and 469 called plus 16 blank matching TCGA primary sample-vials.
- The copied artifacts are aggregate metadata/annotation evidence. The reviewed delta contains no patient molecular matrix, biological score, association, fitted model or changed B-F1 code.
- B-P and B-R remain explicitly unselected. `SOURCE_MANIFEST.json` keeps `final_U_frozen=false`, `promoter_policy_frozen=false`, and `final_eligible_N=null`; the prose repeatedly states final U/Q and N are open.
- No contradiction or lost scope was found for A/C/D labels, the wet-lab requirement, CNA/mechanistic limits, LUAD conditional secondary work or the prohibition on treating portal WGS agreement/Cancer DNA fraction as automatic purity.

## Exact remaining readiness gates

1. **Evidence-package gate:** add/fix the checkpoint inventory; integrate the expression and promoter independent-review receipts; state exact cache restore layout; preserve retrieval timestamps; correct stale canonical-location wording.
2. **Primary gate:** obtain the reviewed user decision between B-P and B-R. Do not let the retained predictive `ANALYSIS.md` row imply selection.
3. **Expression/U gate:** intersect actual CPC processed feature IDs with both historical v18 dictionaries and a pinned TCGA crosswalk; adjudicate NULL/conflicting/retired/many-to-one IDs; assess platform/score transport and HLA specificity; freeze ordered U and its hash.
4. **Promoter/Q gate:** choose and review source-label versus CDS/canonical/manufacturer/window/shared-probe rules; retain shared memberships without transcript weighting; complete cohort probe availability, mask, missingness and detection-P QC; freeze per-gene Q and hashes.
5. **Biological-unit gate:** resolve CPC focus/replicate/specimen linkage and TCGA portion/analyte/aliquot matching; freeze deterministic one-patient rules, valid-call/missingness policy and exclusions.
6. **Covariate gate:** justify Qpure/ABSOLUTE construct transport for B-P or approve an explicit cohort-specific B-R amendment; preserve estimator, field, scale and call status; never substitute WGS agreement or Cancer DNA fraction automatically.
7. **Population/precision/inference gate:** derive final eligible N only after the preceding rules; freeze the target population, minimum meaningful effect/precision target, estimand/threshold, B-R rank-aware inference if selected, and the historical-access/amendment ledger.
8. **Engineering/release gate:** only after signed scientific freeze, implement/review the selected feature and model tickets, run the approved AIU/Python environment and cohort validation, complete the still-pending final Opus recheck, then add repository/GitHub/Notion publication receipts. A clean Sol review cannot satisfy any of those execution or independent-model-review gates.

## Axis summary

Standards: 1 high, 2 medium, 2 low and 1 judgement-call finding; worst issue is the missing advertised artifact inventory. Spec/evidence: 3 medium and 1 low finding; worst issues are incomplete review integration and ambiguous/overstated contract wording. Scientific selection boundaries pass this review but remain intentionally unresolved.
