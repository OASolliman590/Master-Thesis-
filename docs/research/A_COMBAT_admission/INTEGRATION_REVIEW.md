# COMBAT and COMPASS integration review

Checked 6 September 2026. Bounded read-only review of canonical COMBAT evidence, Paper A DATA/TRANSPORT/PREREGISTRATION/README updates, and the COMPASS closest-study note. No canonical edits, matrix downloads, model execution, normalization or endpoint selection.

## Result

No material scientific integration discrepancy found. The canonical documents preserve both proposed A primaries and the conditional prostate branch. Direct pmeTPM admission is rejected; the actual export remains unresolved. Clinical labels are not silently promoted to a final-regimen endpoint, the 15-public versus 12-published RNA subset gate is retained, and the 352% versus 353% candidate discrepancy is not repaired. No stale statement that the COMBAT independent review is pending was found.

## Minor documentation correction

`specs/A/DATA.md:3` still gives 5 September as the evidence-check date, and `specs/A/PREREGISTRATION.md:28` says all cited sources were checked on 5 September. Both now include the 6 September COMBAT/COMPASS checkpoint. Qualify these as the original audit date and explicitly acknowledge the later update. This does not change the source conclusions or freeze a design choice.

The April 12, 2023 date in the retained GEO sample metadata is its submission/last-update date, not the date this team fetched it. The current COMBAT retrieval records are dated September 5 UTC, consistent with the September 6 Cairo review. These dates should remain distinguished.

## Provenance and links

- All six outer-artifact register entries resolve locally and match both recorded byte counts and SHA-256 values, including the outside report, independent review, COMPASS note and three audit helpers.
- Canonical `audit_summary.json`, `retrieval.json`, and `REVIEW.md` are byte-identical to their outside counterparts.
- Explicit research paths referenced by the four checked A specification files resolve, including COMBAT admission, COMPASS, the original clinical audit and B purity-field correction.
- The canonical COMBAT summary points to its completed retained review. Its outside scripts/workbook preview remain outside the repository and are not represented as production implementation.

## COMPASS verification scope

The original article identifies Shen et al.'s COMPASS as a published *Nature Medicine* article dated 3 July 2026. Its text reports TCGA pretraining, a 16-clinical-cohort benchmark, and evaluation across cohorts, cancers and treatments. The benchmark text classifies complete/partial response as responder and stable/progressive disease as nonresponder. These high-level statements in `A_COMPASS_2026.md` agree with the primary source. [Original COMPASS article](https://www.nature.com/articles/s41591-026-04502-7), publication heading, Results preceding and under “COMPASS achieves state-of-the-art performance across 16 immunotherapy cohorts,” and Methods.

This review did not reproduce COMPASS code, performance or patient-level splits, validate an accessible checkpoint, inspect original labels in all 16 cohorts, or establish absence of train/test overlap. The canonical note states these limits. Its novelty implications are correctly labeled inference, with detailed comparison still queued; it does not mandate a new comparator or choose A-P1 versus A-P2.

Other agents' outside source reports were not integrated or reviewed in this bounded check. The review applies to current working-tree contents and does not certify a Git commit.
