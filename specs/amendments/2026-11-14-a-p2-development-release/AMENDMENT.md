# Amendment: patient overlap rule and gate order for the A-P2 development run (signed 15 Nov 2026)

**Status: SIGNED by the user on 15 Nov 2026 ("Sign with A1"), draft 2, all sections, section 5 option A1.** Signing releases no outcome and no run. Written by the coordinator after the user's instruction of 12 Nov 2026 ("make sure we are ready to have some real results"). Reviewed by Astra (twice, high effort), Grok 4.7 (high effort) and the coordinator; reports are in `work_notes/coordinator_20261112/` (outside Git). Draft 2 takes in those reviews.

It amends two things only: how A-P2 satisfies the signed validation amendment's "deduplicated across study families" (`specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md`, section 3), and the order of the Paper A gates in `specs/A/SPEC_v2.md` section 11. The signed formal primary is unchanged: the IMvigor210 paired AUROC difference. Signing releases no outcome. Each run still needs its own approved release record, filed under `docs/decisions/`.

## 1. Why

No included cohort publishes a cross-study patient roster. The built patient IDs are study-namespaced tokens, so ID matching can show token uniqueness only, never that two people differ. If "deduplicated" means "proven distinct", A-P2 can never run. This amendment says what evidence is enough, how the design limits the remaining risk, and how that risk is reported.

## 2. Evidence rule

Every pair of selected development cohorts (21 pairs for 7 cohorts), and every pair of a development cohort with IMvigor210, gets one status in `docs/validation/A_P2_IDENTITY/OVERLAP_REGISTRY.tsv`. Status comes from primary sources only: recruitment sites, enrolment periods, trials, treatment history and author statements. The same standard applies to every pair. The code refuses a missing pair.

| Tier | When | Status | Effect |
| --- | --- | --- | --- |
| 1 | Shared senior author group or institution that ran both cohorts | `OVERLAP_RISK_GROUPED` | One study family in every analysis |
| 2 | Shared investigator institution in a multi-site trial, or US melanoma cohorts whose site rosters are incomplete | `CONSERVATIVE_SENSITIVITY` | Separate in the main analysis; grouped in a prespecified second run |
| 3 | Different cancer types, or different countries and institutions with no documented link | `NO_OVERLAP_DOCUMENTED` | Separate; the residual risk is stated |
| — | Development cohort against the final test | `RESOLVED_BY_SOURCE_RULE` | Only with an executed, hash-bound rule (section 5) |
| — | No usable evidence or rule | `UNRESOLVED` | Blocks the run |

New source evidence of shared patients moves a pair up a tier before any further outcome read. The change is logged.

## 3. Statuses

- **Tier 1: Liu 2019 and Van Allen 2015.** Shared author group, DFCI, and German accrual on both sides. Van Allen patients received anti-CTLA-4 and many Liu patients had prior ipilimumab, so one person can appear in both. **Main analysis: 6 families.**
- **Tier 2: Riaz 2017 with Liu, Van Allen and Hugo; Hugo with Liu and Van Allen.** Riaz is the multi-site CheckMate 038 cohort with Dana-Farber investigators and prior-ipilimumab patients. Hugo lists UCLA and Vanderbilt, and the US melanoma site rosters are incomplete. **Conservative run: Liu, Van Allen, Riaz and Hugo form one family, so 4 families** (US-linked melanoma, Gide, Kim, GSE176307).
- **Tier 3:** Gide 2019 (Melanoma Institute Australia) against each other melanoma cohort, and Kim 2018 (Korean gastric) and GSE176307 (US bladder) against every cohort of a different cancer.
- **Final-test pair:** GSE176307 against IMvigor210, under section 5.

Both the main and the conservative results are reported, whatever their direction. If they differ in direction, the manuscript reports both and does not choose. Every training-set class floor (at least 20 responders and 20 non-responders) is enforced by the code before any fit. A fold below the floor is reported as unavailable, never refitted differently.

## 4. Residual risk, stated with every development result

Grouping keeps a family's patients together when that family is held out. It does not remove every effect of an unknown shared person:
- **Other folds and the final fit:** a shared person still counts twice in every training set that contains both studies, and in the freeze fit.
- **Averaged study AUROCs:** when a grouped family is held out, a shared person contributes to two study AUROCs in the equal-study average.
- **The 20 repeated 70/30 splits:** Van Allen has fewer than 10 responders, so it is always in training. A shared person whose Liu record falls in the 30% test slice is on both sides of that split. These splits are already a secondary validation-setting contrast. This limitation is added to their report.
- **Transfer differences:** anti-CTLA-4 against anti-PD-(L)1 treatment, treatment sequence and source-specific response assessment remain limitations of any cross-study result.
The size of unknown overlap cannot be bounded from the sources, so none of these is called "small".

## 5. Development data against the final test (GSE176307 and IMvigor210)

GSE176307 (Rose 2021; one US academic centre; immunotherapy 2014–2018) could include patients who enrolled in IMvigor210 (atezolizumab; 2014–2015). This is settled before development, without touching IMvigor210.

**Fact (14 Nov, outcome-free; GEO family SOFT fields `io.therapy` and `io.lot` only; logged in `DEVIATIONS.md`):** GSE176307 records the agent and line of therapy but no start date and no trial field. By sample: atezolizumab 35, pembrolizumab 47, nivolumab 5, durvalumab 2, avelumab 1. GEO lists 90 patients; the analysis set holds 87 of them (the builder dropped 3 for timing, label or assay reasons), and the preparer checks that every one of the 87 is found in GEO. Under the rule below, **33 of the 87 patients** are excluded from the freeze fit (atezolizumab recorded, or agent missing or conflicting); 54 remain. The excluded list and the derived table are private and bound by hash.

**Option A1 (recommended): rule `A_P2_ATEZO_FREEZE_EXCLUSION_V1`.**
- A GSE176307 patient is excluded from the **freeze** fit if any of their samples records atezolizumab, or if the agent is missing or conflicting. The list is built from GEO metadata and patient identities only, before any outcome read, and bound by hash. The frozen equation, the only fit that ever touches IMvigor210, is fitted on a derived table without these patients.
- **Development** (leave-one-family-out and splits) keeps them, because development never touches IMvigor210, and the whole procedure is fixed before any outcome is seen. One prespecified development sensitivity uses the derived table, to show the effect of the smaller bladder cohort.
- **Residual risk, stated with the final result:** the recorded agent is the treatment Rose analysed. A patient who joined IMvigor210 earlier and was later recorded under another drug cannot be excluded from these fields. The final-test result is reported with this qualification.

**Option A2:** exclude the same patients from development too. Simpler to explain; development loses part of the only bladder cohort. Same residual risk.

**Option B:** exclude GSE176307 from A-P2. No residual risk, but no bladder cohort in training, so IMvigor210 tests transfer to an unseen cancer.

**Option C:** keep everyone and qualify the final test as possibly overlapping. Not recommended, because the final test could no longer be called untouched.

## 6. Gate order

Section 11 item 3 of `specs/A/SPEC_v2.md` (the prior-exposure audit) stays a gate. It is required **before the final-test release and before any comparator or novelty claim**, not before the A-P2 development and freeze runs. Reason: the four panels, the penalty and CYT are already frozen, and development compares the refit score only with CYT inside the development cohorts. It uses no additional published comparator. The audit (`docs/validation/PAPER_A_PRIOR_EXPOSURE.md`, PROPOSED_INCOMPLETE) continues in parallel. This deferral does not defer patient-overlap protection, which sections 2 to 5 settle first. Items 4 and 5 of section 11 are unchanged.

## 7. Runs a later release may cover (under option A1)

| Run | Input table | Families |
| --- | --- | --- |
| Development, main | original built table (`features.tsv` 75b3b1b0…26a, 408 patients) | 6 |
| Development, conservative | original built table | 4 |
| Development, bladder sensitivity | derived table without the excluded patients (375 patients) | 6 |
| Freeze | derived table without the excluded patients (375 patients) | 6 |

Each run includes the signed cohort-adaptive sensitivity on the same 7 cohorts. Braun's cohort-adaptive sensitivity needs separate implementation and a later release. IMvigor210 stays `UNTOUCHED_FINAL_TEST`, and `final-evaluate` needs a separate release. Under option A2 every row uses the derived table. Under option B GSE176307 leaves every table, and the family counts become 5 (main) and 3 (conservative).

## Signature

Signed by the user on 15 Nov 2026 ("Sign with A1").

- [x] Sections 2–4 (evidence rule, statuses, residual risk)
- [x] Section 5, option: A1 (rule `A_P2_ATEZO_FREEZE_EXCLUSION_V1`)
- [x] Section 6 (gate order)
- [x] Section 7 (runs a later release may cover)
