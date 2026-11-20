# A-P2 development release: what you are approving (plain language)

Companion to `A_P2_DEVELOPMENT_RELEASE_DRAFT_2026-11-19.md`. It explains that record; it is not a second record and it authorizes nothing. You do not need to check any hash by hand: the code, the tests and the independent review do that. Your decision is scientific, and it is these three questions.

## In one sentence

> "I allow the computer to see which patients responded to immunotherapy, for these four runs, once each, using the data and code that were checked."

Until you sign, the code has never seen whether any patient responded. That is deliberate: the whole method (features, model, grouping, exclusions) was fixed first, so the results cannot be tuned to the answer.

## Question 1. Is the plan right? (the four runs)

All four use 7 development cohorts (6 melanoma or gastric, 1 bladder: GSE176307) and one outcome: responder or non-responder (`orr_class`).

| Run | Patients | Study groups | What it tells the paper |
| --- | --- | --- | --- |
| 1. Main development | 408 | 6 | Does the 4-feature score predict response better than the CYT benchmark, when each study group is held out in turn? The headline development result. |
| 2. Conservative development | 408 | 4 | The same, but treating four melanoma studies that might share patients (Liu, Van Allen, Riaz, Hugo) as one group. If results hold here, possible shared patients are not driving them. |
| 3. Bladder sensitivity | 375 | 6 | The same as run 1, without the 33 bladder patients excluded in step A1. Shows how much those patients matter. |
| 4. Freeze | 375 | 6 | Fits the final score once and locks its weights. Nothing is tested in this run; the locked score is what IMvigor210 will test later. |

Main and conservative are both reported, whichever way they come out. You already signed this list of runs in the amendment of 15 Nov 2026 (section 7); this record only puts it into effect.

## Question 2. Is it right to exclude the 33 bladder patients?

GSE176307 (one US centre, treated 2014–2018) could include patients who were also enrolled in IMvigor210 (atezolizumab, 2014–2015). To make sure no IMvigor210 patient helps build the frozen score, the 33 patients with atezolizumab recorded (or with the drug missing or unclear) are left out of the freeze. Development runs 1 and 2 keep them, because development never touches IMvigor210. One limit, stated with the final result: a patient who joined IMvigor210 earlier but was recorded under a different drug cannot be detected from the available fields. **You already signed this rule (A1, 15 Nov 2026).** The record only checks that the computer uses exactly that list (33 of 87).

## Question 3. Is IMvigor210 still untouched?

Yes. IMvigor210 is not in any of the four runs and stays `UNTOUCHED_FINAL_TEST`. Testing the frozen score on it is a separate, later decision, after the check of which published scores were trained on IMvigor210 (PredictIO and COMPASS were).

## What the safeguards guarantee (you do not have to verify these)

- **Exactly what you approved runs.** Every input file is identified by a fingerprint (the long hashes). A different or edited file is refused.
- **Your approval cannot be changed afterwards.** At signing, a fingerprint of the approved block is saved. Any later edit to the block makes every run refuse.
- **Once each, with the reviewed code.** Each run can be used only once, and only with the code version that was reviewed.
- **Test data never touches real data.** Test runs only read files from a marked test folder.

## What signing looks like

1. In the draft record, change `"record_status": "UNAPPROVED"` to `"APPROVED"`, then write your name and the date on the signature line.
2. Run one command (Claude will give it to you) that saves the approval fingerprint to `A_P2_DEVELOPMENT_RELEASE_V3.approved.sha256`. That file is the key: without it nothing runs.

If any answer above is "no" or "not sure", don't sign. Say which one, and it gets explained or changed first.
