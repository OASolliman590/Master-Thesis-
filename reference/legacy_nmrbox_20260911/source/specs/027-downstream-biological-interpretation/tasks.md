# Tasks: Downstream Biological Interpretation

FR traceability in brackets. Each task is independently testable. Default input =
reviewed run root `results/analysis_id_runs_t7_20260607_stage07_scale_provenance`.

## Phase 0 — Audit & contracts
- [x] T001 Confirm input columns exist in `meta_effects.tsv` / `responder_signature_tiered.tsv` across all active analysis_ids. [FR-016]
- [x] T002 Add `modules/10_interpretation/contracts.py` — output schemas + `claim_class` stamping helper. [FR-019]
- [x] T003 Create `interpretation/` layout + a read-only guard that refuses writes outside it. [FR-016, FR-017]
- [x] T004 Add SC-006 checksum test: frozen signature + run root unchanged after any interpret run. [FR-017]

## Phase 1 — M1 Enrichment
- [x] T010 `enrich.py` + `scripts/interpret/fgsea_enrich.R`: ranked GSEA on `meta_effect_random` per analysis_id. [FR-001]
- [x] T011 ORA on tiered signature (secondary view). [FR-002]
- [x] T012 Wire collections from gene-set registry/atlas (Hallmark/Reactome/GO/KEGG/immune). [FR-003]
- [x] T013 Emit `enrichment/<analysis_id>/{gsea.tsv,ora.tsv,dotplot_data.tsv}` + provenance. [FR-004]
- [x] T014 `interpret enrich` subparser + unit + integration tests. [FR-001..004, SC-001]

## Phase 2 — M2 Network & hubs
- [x] T020 `network.py`: build network from ranked genes (co-expression/PPI extension remains a future backend; current reviewed root gates before hub emission). [FR-005]
- [x] T021 Hub detection + node-degree permutation FDR + `min_signal_floor` gate → `insufficient_signal` path. [FR-006, SC-002]
- [x] T022 R-vs-NR topology contrast where expression available; current reviewed root records thin-signal topology as not evaluable. [FR-007]
- [x] T023 Emit `network/<analysis_id>/{edges.tsv,hub_genes.tsv,hub_difference.tsv}`. [FR-008]
- [x] T024 `interpret network` subparser + tests incl. a thin-signal test that asserts no fabricated hubs. [FR-006]

## Phase 3 — M3 Cross-cancer hub meta
- [x] T030 `hub_meta.py`: meta-analyze hub effects with cancer as low-dim moderator when hubs pass; current reviewed root propagates `insufficient_signal`. [FR-009]
- [x] T031 Classify pan-cancer vs cancer-specific; emit `hub_meta/{cross_cancer_hub_meta.tsv,forest_data.tsv}`. [FR-010]
- [x] T032 `interpret hub-meta` subparser + tests. [FR-009, FR-010]

## Phase 4 — M4 Immunophenotype
- [x] T040 `immunophenotype.py`: extend Stage 09 scoring + phenotype class (hot/cold/IFN-gamma/TIS-like). [FR-011]
- [x] T041 `configs/immunophenotype_criteria_registry.tsv` — SEEDED with HOPE-RNA decomposition (checkpoint expr, MSI/dMMR proxy, T-cell-inflamed GEP, CYT, IFN-gamma, composite) + flagged non-RNA rows (TMB/PD-L1-IHC/ECOG/iRECIST). [FR-012]
- [x] T042 Phenotype→response association across cohorts; degrade to score-based + audit if expression offline. [FR-013, edge case]
- [x] T043 `interpret immunophenotype` subparser + tests. [FR-011..013, SC-003]
- [x] T044 Score the RNA-derivable HOPE criteria + emit `hope_composite_rna` (claim_class=mechanism_hypothesis); skip `rna_derivable=no` rows with a recorded reason. Equal-weight/proxy handling documented in audit. [FR-012]

## Phase 5 — M5 RNA-inferred epigenetic state
- [x] T050 Decide pilot method(s) (regulator activity / methylation-proxy) — record in research.md. [FR-014]
- [x] T051 `epi_infer.py` + backend: per-sample epigenetic-state proxy from bulk RNA-seq. [FR-014]
- [x] T052 Relate inferred state to response + epigenetic signature; emit `epigenetic/{inferred_scores.tsv,epi_response_assoc.tsv,epi_input_audit.tsv}`. [FR-015, SC-004]
- [x] T053 `interpret epi-infer` subparser + tests; label all outputs as proxy/hypothesis. [FR-019, SC-004]

## Phase 6 — Integration, reproducibility, docs, sign-off
- [x] T060 Reproducibility bundle per module (`commands.sh`+`environment.yml`+`checksums.sha256`). [FR-020]
- [x] T061 Scoped interpretation pytest green: `PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache python3.13 -m pytest tests -k interpretation -q` -> 14 passed, 185 deselected on 2026-07-04 after adding post-run interpretation-contract and pre-approval packet regressions. Bare `pytest -k interpretation` is not usable in this dirty workspace because archived canary bundles under `results/` are collected first. [SC-007]
- [x] T062 Runbook `docs/runbooks/stage_10_interpretation.md` + CHANGELOG entry.
- [x] T063 Spec status Draft → implemented; streamlined index pointer updated.
- [x] T064 Quickstart hardened to use copy-paste-safe `python3.13 -m src.pipeline.cli` commands plus a read-only dashboard verification path; dashboard now guards the quickstart command shape. [SC-007]

## Deferred (do NOT start here)
- [ ] Prediction layer (RNA-seq → response classifier / AUC) — separate spec.
- [ ] MOFA / TCGA multi-omics — spec 020.
- [ ] TCGA survival/clinical — spec 020 continuation.

---

## Paste-ready Codex prompt

```text
Build spec 027 (downstream biological interpretation) in
"2-Experimental/Computation Arm/06_analysis_pipeline_repo".

Read first:
- specs/027-downstream-biological-interpretation/{spec,plan,research,tasks,quickstart,benchmarks}.md
- configs/immunophenotype_criteria_registry.tsv  (HOPE-RNA decomposition)

Build the `interpret` CLI verb group + src/pipeline/modules/10_interpretation/
modules M1–M5, in tasks.md phase order (Phase 0 audit/contracts FIRST).

Hard constraints — do not violate:
- Read the reviewed run root READ-ONLY; write only under <root>/interpretation/.
- Never mutate the frozen signature or any committed results/ run root (SC-006 checksum test).
- Enrichment/network run on the RANKED meta statistic; hub detection MUST emit
  "insufficient_signal" rather than fabricate hubs on thin input.
- Cancer is a moderator, never a per-cancer subgroup claim.
- HOPE: score only rna_derivable=yes registry rows; skip rna_derivable=no rows
  (TMB / PD-L1-IHC / ECOG) with a recorded reason — those are the spec 020 WES handoff.
- Every output carries claim_class in {mechanism_hypothesis, discovery}; never "validated".
- DO NOT build the prediction layer (deferred) or TCGA/MOFA (spec 020).

Verify with the quickstart commands and `pytest -k interpretation`.
Ask before any HPC action or before running against a mid-flight run root.
```
