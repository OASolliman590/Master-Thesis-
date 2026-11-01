# Simple mode for cohort intake: amendment, 31 Oct 2026

**Status: decided by the user in chat on 31 Oct 2026 ("Yes, simplify").** The user said intake had become more complicated than any published pooled ICI study (Litchfield 2021, Bareche 2022, PredictIO/ORCESTRA). It replaces the per-cohort V0–V8 worksheet ceremony for **new and pending** cohorts. Cohorts already admitted (Riaz, Hugo, GSE168204, Liu) keep their admissions. RC2 and the 29 Oct amendment are otherwise unchanged.

## What stays (these protect the results)
1. **Pinned sources.** Every file comes through `tools/a_dav/retrieval.py` with a fetch plan and a recorded SHA-256.
2. **Response labels are checked against the paper**, with the original categories kept. ORR and each clinical-benefit definition are separate endpoints, never merged. Unknown is never counted as non-response.
3. **One pre-treatment sample per patient** for the baseline analyses, with a written rule when a patient has several.
4. **IMvigor210 stays locked** (UNTOUCHED_FINAL_TEST), and is never loaded for development.
5. **Combination cohorts** (ICI plus a non-ICI drug) stay out of the A/B response analyses.
6. **No merging of raw expression across studies.** Analysis is per study.
7. **Caveats are written down:** unknown tool versions, undocumented processing, uncertain timing, possible overlap.

## What changes
- **One registry file**, `docs/cohorts/REGISTRY.tsv` (study level, Git-bound), with one row per cohort. It records source, files, representation, endpoints, n, role and caveats. It is the single place to see cohort status.
- **One loader** writes, for each cohort, `expression.tsv` (genes × patients) and `clinical.tsv` (one row per patient: endpoints, drug class, prior ICI, timing) into `.scratch/runtime/<c>/simple/`, plus a short `caveats.md`.
- **Unknown processing facts are caveats, not blockers.** V3 becomes a recorded check, not a gate, except for a wrong scale (for example counts treated as TPM), which is still a hard stop.
- **One user sign-off per batch:** the user reviews the registry rows and the caveats for a batch and signs once in chat. No per-cohort worksheet rounds, and no stops when an already-answered question drops out.
- **The final test is still protected in code:** the loader refuses IMvigor210.

## One writer (user, 1 Nov 2026)
Cohort work continues in the Claude coordinator session only ("Continue here"). The user's Codex session that ran on 30 Oct 22:25–22:37 (it added `tools/a_dav/recount3.py` and the recount3 tables, see `docs/research/cohort_sources/RECOUNT3_ROUND_20261030.md`) stays idle on this repo. Its outputs are reused, not redone. A partial `tools/a_cohorts/core.py` from a failed 31 Oct round exists and is to be completed.
