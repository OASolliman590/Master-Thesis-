# Hard rules and the merge gate

Adopted 18 November 2026 (`docs/decisions/PROCESS_SIMPLIFICATION_A_20261118.md`). Briefs link to this file instead of copying the rules. Where an older brief says otherwise, this file applies; signed specifications and amendments always prevail over both.

## Rules that protect the results (never relaxed)

1. **Outcomes stay locked** until the user signs a release record for that run. Never pass `--allow-outcomes`. Tests use invented data.
2. **IMvigor210 is `UNTOUCHED_FINAL_TEST`** in every paper, modality and copy. Do not open, download or use it to settle overlap.
3. **The repository is public.** No patient-level data, real sample or run IDs (GSM, SRR/ERR, SRX, SAMN…), or absolute machine paths in Git. Study accessions (GSE, PRJ…) are fine. Run `python -m tools.gate privacy` on staged files before every commit, and stage by name, never `git add .`.
4. **Signed specs, amendments and the numerical freeze are authoritative.** Design changes need the user's signature; record decisions in `docs/decisions/` or `specs/amendments/`.
5. **Clinical tables are read by named columns only.** Agents never open a real `ingestion_packet.json` by hand.
6. **The real A-P2 rebuild stays deferred.**
7. **No permanent deletion** (Trash only; no `git worktree remove --force`, no `git branch -D`). Never read, print or send secrets, keys or server handovers. The SSD can disconnect: never recreate its mount point; check recent files for truncation on return.

## Exposure log: what counts

`DEVIATIONS.md` records reads of **real thesis cohort data** that come near outcomes (clinical columns, response labels, final-test material). These are **not** exposure and need no entry:
- invented fixtures, including an invented file that happens to be named `ingestion_packet.json` inside a test's temporary folder;
- published reference examples used as known-answer tests (for example the metafor Normand 1999 data);
- code, specs and patient-free registries.

Known-answer and tamper-detection tests are part of the gate. Do not deselect them.

## Merge gate (one run, one mode)

```bash
python -m tools.gate tests --receipt <work_notes path outside Git>
```

- Runs the Paper A suite **once**, with `THESIS_RUNTIME` set to a fresh empty folder. Any test that silently needs real data then fails instead of reading it. Tests that care about `THESIS_RUNTIME` set or clear it themselves, so the former second "unset" run is dropped. It then runs the single-cell suite in its own environment. Nothing is deselected.
- While working, run only the module's tests: `python -m tools.gate tests --targets tests/<module>`.
- Run the full gate once, on the final code, before merge.

## Paperwork

- **One receipt per merge**, written by the gate: commit, commands, test summaries, exit codes and the privacy result. Keep it in `work_notes/` (outside Git). Step-by-step source snapshots and per-step acceptance files are no longer produced.
- **Per ticket or cycle in Git:** `spec.md` and `review.md`; `DEVIATIONS.md` only when a real-data read under the rule above occurred.
- **Briefs** state the task and link here; they do not paste these rules.
