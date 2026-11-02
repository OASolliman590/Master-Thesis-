# Debate review of the v2 spec drafts (A, A.1, B), 3 Nov 2026

Run with the debate-review skill (`--local`): main reviewer Claude, debate reviewer Codex gpt-6-astra at high effort. Kept verbatim. **All four agreed findings were applied** to `specs/A1/SPEC_v2.md` (change-score model primary, ANCOVA as a labelled sensitivity), `specs/B/SPEC_v2.md` (conditional composition clause; B-ICIM global-methylation change made explicit) and `docs/decisions/A_P2_MEASUREMENT_20261102.md` (GSE176307 assay accounting).

<!-- debate-review head=982403b9906d0de21690434dd064e2e1038d98de main=claude debate=codex agreed=4 contested=0 p0=0 p1=1 p2=3 -->
| Level | Count |
| --- | ---: |
| P0 | 0 |
| P1 | 1 |
| P2 | 3 |
| contested | 0 |

**debate-review** on `982403b`, main `claude`, second `codex`.

Not ready to sign. One blocking issue remains in the Paper A.1 draft: section 1 defines the estimand as the unadjusted difference in mean change, but the primary model is a baseline-adjusted ANCOVA. These two quantities diverge when baseline expression differs by response class, which is exactly what Paper A expects. Three non-blocking items stand. Paper B's claim ceiling states independence from composition that only a sensitivity analysis tests. B-ICIM is called 'as signed' while it adds a global-methylation term. The GSE176307 assay count leaves one column unexplained. The bootstrap-seed open-gate finding was withdrawn because the gate refers to register entries that are still open.

Findings outside the diff (could not be anchored inline):

- **P2, agreed.** `docs/decisions/A_P2_MEASUREMENT_20261102.md:14` The GSE176307 assay accounting does not add up: 88 patients, one with two assays, plus 2 unkeyed columns gives 91 assays, not the stated 92.


===== specs/A1/SPEC_v2.md:37-39 =====
<!-- debate-review:F1 status=agreed severity=blocking level=P1 -->
> [!WARNING]
> **P1, agreed by both reviewers.** The primary ANCOVA model does not estimate the central estimand defined in section 1.

Line 13 defines the estimand as "Δ = E[X_on − X_pre | R] − E[X_on − X_pre | NR]", the unadjusted difference in mean change. Line 39 makes the primary "d = α + β·R + covariates" with the baseline value as a covariate (ANCOVA), and line 38 calls β "the differential change". With X_pre in the model, β is the response difference in change conditional on baseline. It equals Δ only when mean baseline is equal across R and NR or when the baseline coefficient is zero (Lord's paradox). A toy dataset with NR (baseline, change) = (0,0),(2,1) and R = (2,2),(4,3) gives Δ = 2 but adjusted β = 1. Paper A hypothesises baseline differences by response, so this is the expected case.

Suggested: Pick one. Either redefine the central estimand as the baseline-conditional differential change and keep ANCOVA primary, or keep Δ as written and make the plain change-score model primary with ANCOVA as a sensitivity. In either case, state that the two diverge when baseline differs by response class.

_The challenge confirmed the mismatch with a worked numeric example and noted only that divergence also needs a nonzero baseline coefficient, so the finding stands as blocking._


===== specs/B/SPEC_v2.md:71 =====
<!-- debate-review:F3 status=agreed severity=non-blocking level=P2 -->
> [!NOTE]
> **P2, agreed by both reviewers.** The permitted claim says the association is independent of methylation-estimated cell composition, but composition adjustment is only a sensitivity analysis and is not part of the primary.

Line 54 calls the MethylCIBERSORT adjustment a "Pre-specified sensitivity" and says "The primary stays as frozen". Line 48 puts only purity, copy number and global methylation in the primary baseline. Line 71 still says "The association is independent of purity, copy number (if available), global methylation and methylation-estimated cell composition". The signed rule-7 wording at line 78 governs how each result is labelled, but it does not make the claim-ceiling sentence conditional. If the sensitivity attenuates the effect, the template would still assert independence.

Suggested: Make the composition clause conditional on the sensitivity result (for example, "and, in a pre-specified sensitivity, robust to methylation-estimated cell composition"), or drop it from the claim ceiling.

_The challenge argued that line 78's result-dependent wording reduces the risk of overclaiming; the finding was already non-blocking and stays so, because the unconditional sentence at line 71 is unchanged._


===== specs/B/SPEC_v2.md:67 =====
<!-- debate-review:F4 status=agreed severity=non-blocking level=P2 -->
> [!NOTE]
> **P2, agreed by both reviewers.** B-ICIM is described "as signed" while adding a global-methylation adjustment that the signed amendment does not include.

Line 67 says "as signed. Jung first (27 pairs), with purity and global methylation". The signed amendment (specs/amendments/2026-11-02-paper-b-ici-methylation/AMENDMENT.md:42) adjusts "for purity (and for histology or preservation only if frozen and estimable)" and has no global-methylation term. Someone signing on the strength of "as signed" would not see that the covariate set changed.

Suggested: Either drop global methylation from the B-ICIM line, or list it explicitly as a change to the signed B-ICIM so the v2 signature covers it.

_The challenge confirmed that the added covariate contradicts the "as signed" description, so the finding stands unchanged._


