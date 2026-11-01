# One usable data repository: goal and reorganization plan, 1 Nov 2026

**Status: APPROVED by the user on 1 Nov 2026:**
- the plan as written ("Approve plan");
- the signer's name stays in the decision files ("Keep my name");
- T7: copy the useful parts out, and the user deletes the rest ("Copy useful, list rest").

## Goal (user, 1 Nov 2026)
Turn all the data sources we discussed into **one usable data repository**, using Terra (implementation) and Luna (mechanical, cohort-by-cohort work), **without over-engineering**: make the data usable first, improve it afterwards. The ICBatlas parse is the cornerstone index. It includes the bulk RNA-seq cohorts and the user's source decisions, and a single-cell catalogue.

**Done means:**
- every cohort in the registry has `expression.tsv`, `clinical.tsv`, `caveats.md` and `manifest.json` from one loader command;
- the registry shows its status;
- one folder holds it all;
- GitHub is updated with code and docs only (no data).

## Locations found (1 Nov)
| Location | Size | What it is |
| --- | ---: | --- |
| The project folder on the internal disk | ≈9.2 GB | The active project. `work/a-dav-01` (7.6 GB with `.scratch` data) is a git **worktree** of `work/thesis-speckits-20261015`; also about 50 old one-off folders (`paper-a-*`), envs, reports and orchestration |
| The `Master_Thesis` folder on the portable SSD | ≈75 GB | An older `master-thesis` checkout of the same GitHub repo (44 GB, of which 42 GB is `tmp/`); `data_store/` (TCGA-PRAD, 9.9 GB); `.venvs` (9.4 GB); `.codex_tmp` (3.4 GB); old packages, backups, planning (2.6 GB), PDFs |
| The thesis folder on the T7 drive | 116 GB | March–June 2026 work: `runs/` (102 GB, GEO harmonization runs of 21 March), `retrieval/` (13 GB, including a 47-cohort reconciled list), **`tcga_gdc_hub_20260607/`** (516 MB: STAR counts plus survival for 11 TCGA projects including SKCM, LUAD, LUSC, KIRC, HNSC, STAD, PRAD), `gene_sets/` |
| GitHub `OASolliman590/Master-Thesis-` | — | **PUBLIC** repository; default branch `main`; our work is on `codex/a-dav-01` |

## Proposed layout (all under The `Master_Thesis` folder on the portable SSD)
```
Master_Thesis/
  repo/          the single Git checkout (fresh clone of codex/a-dav-01 after push);
                 its .scratch/runtime/ (git-ignored) holds all cohort data and outputs
  envs/          recreated Python envs (dav-pipeline); venvs cannot be moved, they hard-code paths
  data_store/    TCGA-PRAD (already here) + TCGA hub counts copied from T7
  papers/        PDFs (existing folder + the papers the user supplied)
  archive/       everything superseded: the old master-thesis checkout, paper-a-* one-off folders,
                 MIGRATION_BACKUP, assessment_2026-09-05, planning, old packages, and the old project folder from the internal disk
```

## Move steps (in this order, after the user's OK)
1. Wait for the running loader round to finish (it writes into the current repo).
2. Commit the outstanding work on `codex/a-dav-01`, then run a **public-repo scan**: no patient-level data, no sample or run IDs, no absolute paths, no credentials. Note that the decision files quote the signer's name.
3. Push `codex/a-dav-01` to GitHub. Do not merge to `main` unless asked.
4. Fresh clone into `Master_Thesis/repo`. Copy `.scratch/runtime/` across, verifying hashes against each store `MANIFEST.json`. Recreate the env in `Master_Thesis/envs/`. Run the test gates there.
5. Move the old folders into `archive/` (moves, not deletions). The internal-disk project folder goes to `archive/` only after step 4 passes.
6. **T7:** keep `tcga_gdc_hub_20260607/` (copied into `data_store/`) and the 47-cohort list (copied into `repo/docs/cohorts/legacy/`, patient-free parts only). The user decides on the rest, or deletes it; the coordinator does not hard-delete anything.

## Then the data goal (Terra + Luna)
- **Terra:** the shared loader and anything tricky (Gide crosswalk, Braun streaming, recount3).
- **Luna:** one cohort at a time from the registry (pin, fetch, load), plus the remaining ICBatlas sets and the new open cohorts.
- **Single-cell:** a catalogue first, in `docs/cohorts/SINGLE_CELL.tsv`; loading follows the minimal SC-1 plan.
- One user sign-off per batch.
