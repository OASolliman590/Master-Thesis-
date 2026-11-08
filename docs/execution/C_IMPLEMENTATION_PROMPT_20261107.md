# Implementation prompt: Paper C with the merged C-VIRTUAL module

Paste this to the implementing agent. It is written as goals, not as a task list: each goal names what "done" looks like, so the agent decides the steps.

---

## Role and setting

You implement **Paper C** of an MSc thesis ("Epigenetic priming for enhanced immunotherapy: a multi-omics strategy to sensitise prostate cancer to immune checkpoint inhibitors", author Omar Soliman). Paper D has been merged into Paper C as one conditional secondary module, `C-VIRTUAL`.

Work in `/Volumes/PortableSSD/Master_Thesis/worktrees/paper-c-spec`, branch `codex/paper-c-spec` (pushed at `ca2ed75`). Python is `/Volumes/PortableSSD/Master_Thesis/envs/dav-pipeline/bin/python`.

**Source of truth, in this order.** Read these before writing any code. Where this prompt and a spec disagree, the spec wins.

| What | Path |
| --- | --- |
| Signed Paper C specification v2.1 | `specs/C/SPEC_v2.md` |
| Draft C-VIRTUAL amendment (unsigned) | `specs/C/AMENDMENT_C_VIRTUAL_20261104.md` |
| PC3 test-unit inventory | `specs/C/c_virtual_pc3_inventory_20261104.tsv` |
| Independent review already applied | `specs/C/REVIEW_ASTRA_HIGH_20261103.md` |
| Framework decisions | `docs/decisions/C_FRAMEWORK_20261015.md` |
| Paper D evidence (read-only, on `codex/paper-d-spec`) | `docs/research/D_SPEC_V2_EVIDENCE_20261103.md` |

Do not edit `tools/`, `specs/A`, `specs/A1`, `specs/B`, `specs/D` or `specs/amendments/`. Read them only.

---

## Goal 0 — Do not start blocked work

**Done when** you have confirmed, and told the user, which of these is true:

- Paper C v2.1 is signed, so C's own implementation may proceed as soon as its inputs exist.
- The C-VIRTUAL amendment is **unsigned**. Questions Q1 and Q3 to Q12 in its section 11 are open. **Write no C-VIRTUAL code until the user signs it.**
- C-P cannot be built until Paper B releases Tier 1+2 lists, its single-cell rule and the TCGA-PRAD methylation model inputs, with hashes.

If the user has not answered the open questions, ask once, by number, with your recommendation per question, and stop. Do not invent an answer and do not treat a recommendation as a decision.

---

## Goal 1 — A reproducible skeleton before any science

**Done when** a fresh clone can run the pipeline end to end on fixtures, with no real outcome data present, and every stage writes a hashed manifest.

- One command per stage. Stages resume by key `(spec, code, environment, input, seed)`.
- Every input is a *source object*: one exact file, identified by SHA-256, with its locator and version recorded in Git. The data itself is not in Git.
- Pin `singscore` and record the exact resolved environment.
- Synthetic fixtures prove the code runs. **A fixture never validates biology** — say so in the test names.

---

## Goal 2 — The frozen query release

**Done when** `c_gene_direction_table.tsv` and `c_query_release.json` exist, are hashed, and are committed, and no perturbation outcome has been read.

- Build pool P by the three filters of `SPEC_v2.md` §3.1, in order. "Not supported" must always mean tested and not supported.
- Apply Paper B's frozen single-cell rule to **every** pool gene, not only to B's association-positive genes.
- Give every gene a desirability label with one written reason each, with precedence unfavourable > ambiguous > favourable. The user's C-Q3 decision keeps M4, M5, M6, the negative-weight Ayers genes and all HOPE_18 genes in the pool, so the primary scores **re-expression (up)**, and only `C-FAV` may speak of a desired direction.
- Match Q_E to Q_M inside the panel stratum, caliper 0.5 log2, no gene used twice, and publish the balance table. Unmatched Q_M genes leave both lists and are listed.
- The primary needs at least 10 matched pairs.

**This release is the freeze point.** After it, changing a list requires a dated amendment.

---

## Goal 3 — The source admission audit, from metadata only

**Done when** every candidate accession has an audit row with an admit or reject decision and the reason, and no expression value was read to decide.

- Apply the seven admission rules of `SPEC_v2.md` §4.1, including at least 3 independent cultures per arm. Wells, time points and cell lines are not cultures.
- Record exact chemical identity: azacitidine and decitabine are different exposures.
- `GSE216053` stays blocked: its titles say decitabine, its genotype field says DNMT1 knockout.
- Freeze the contrast registry.
- **Report the count to the user before the LINCS download.** Fewer than three admitted DNMTi studies means C-P is descriptive and C stays a thesis chapter; the standalone-paper decision is then the user's.

---

## Goal 4 — C-P and C-FAV

**Done when** Δ_Q, its interval and the full diagnostic set are produced from frozen inputs, and a second clean run reconstructs them.

- singscore per sample, up direction, unweighted, each gene once; `D_i = S_i(Q_M) − S_i(Q_E)`.
- OLS per study with explicit context contrasts, equal weights across contexts; then the equal-study mean, with a Welch–Satterthwaite t interval.
- Do not use limma moderation. One score per sample has nothing to borrow across genes.
- **Always report S(Q_M) and S(Q_E) separately.** If both fall, a positive difference is not re-expression.
- Always report leave-one-study-out results and the seven prespecified sensitivities.
- Use the result wording of `SPEC_v2.md` §5.3 exactly: supported, inconclusive, expression-only advantage, descriptive only. Never convert "inconclusive" into a negative finding.
- The cell-line methylation check tells "hypothesis failed" apart from "this line had no methylation to remove". **It is never cut.**

---

## Goal 5 — The secondaries and the handoff

**Done when** C-CLASS, C2, C1, the context lookups, the pharmacology table and the candidate matrix exist, each answering its own question.

- C-CLASS runs HDACi and EZH2i as separate families, with Holm correction across studies within a family, and no expectation fixed in advance.
- C2 is discovery. Most immune genes in L1000 are inferred, not measured, and that must be visible wherever a C2 number appears. C1 is a software and provenance check, not a drug comparison.
- Keep toxicity, mechanism, model fit and dose in separate columns. **Produce no single total score.** A missing fact stays `UNKNOWN`, never zero, never imputed.
- The handoff gives tiers and a Pareto set, plus separate picks (best re-expression, best mechanism, best translational, feasible pilot, control). It does not change the registered wet-lab protocol.

---

## Goal 6 — C-VIRTUAL, only if signed

**Done when** the module has either produced theta with its interval, or stopped at a gate and been reported as "not run" with the gate named and the evidence attached. Both outcomes are complete results.

Gates V0 to V7 of the amendment run in order. The ones that decide the module:

- **V2, the gene list.** State's ordered 2,000-gene list is not released, and the two routes in the D evidence file are closed. Try the untested count-matching route described in the amendment §2. A public question to Arc needs the user's approval first. If both fail, stop as "not run".
- **V4, the baseline.** The comparator is the same drug at the same label, averaged over the **45** training lines. Tahoe `expression_data` is 338 GB against 244 GiB free, so stream and filter; never copy it whole. A drug with no training contexts is blocked, not swapped for a weaker baseline.
- **V7, the run.** Measured PC3 outcomes are read only here, and only after C gates 3 and 4.

Fixed points:

- Model: State `ST-HVG-Tahoe`, revision `ca6b751972493f8448e3256d1340ae70ad43e1e7`, `checkpoints/final.ckpt`, seed 42, weights frozen, no fine-tuning.
- Dose: the user decided on 5 Nov 2026 to accept the nearest Tahoe label within 3-fold, for model and baseline alike. This gives **14 test compounds**. No compound matches an exact Tahoe dose, so an exact-dose sensitivity is impossible; use the other neighbouring label instead.
- **Assert, do not trust.** State can silently replace an unknown drug label with a control label and still exit zero. The adapter must fail loudly if any label is missing or any control is unmatched.
- Fewer than 10 drugs after quality control makes the result descriptive only.
- Stop at 15 h if gates V1 to V5 have not passed. Bulk or L1000 data never substitute for the primary test.

---

## The firewall, which overrides every goal above

- No model output enters C-P, C-FAV, C-CLASS, C2, the evidence tiers, the Pareto set or the wet-lab nomination. A prediction is never Level 2 evidence and never corroborates another prediction.
- No C result is used to choose, tune or filter the model, its genes or its drugs.
- No C gate waits on C-VIRTUAL.
- C-VIRTUAL is the first thing cut when time runs short, before TISMO.

---

## Claim discipline

Write results in the language of `SPEC_v2.md` §8 and amendment §8. In particular, never claim that methylation causes silencing, that a deficit was restored, that one drug or class is superior, that immune killing or ICI synergy follows, anything about prostate ICI patients, or that a LINCS-inferred gene was measured. For C-VIRTUAL, never claim that virtual cells replace an experiment, and never write "digital twin".

A useful framing to keep visible in the discussion: a DNMTi can raise immune genes **directly**, by demethylating each gene's own promoter, or **indirectly**, through viral mimicry and an interferon response (Chiappinelli 2015, Cell 162:974; Roulois 2015, Cell 162:961). C-P as signed does not separate these. An "inconclusive" Δ_Q is therefore a real mechanistic finding, not a failure. A prespecified secondary that separates the two routes has been offered to the user and not yet accepted; do not add it unasked.

---

## Working rules

- Lean process: do the data checks, at most one review, no review loops, and report plainly.
- Verify every AI-supplied lead against the primary record before it enters a spec or a result.
- No patient-level data, sample IDs or absolute data paths in Git. Never read or print credentials. No CAPTCHA bypass. Deletions go to the Trash.
- IMvigor210 is `UNTOUCHED_FINAL_TEST` and C never reads it in any modality. No CPC-GENE outcome, no Paper A final-test result, no reserved A.1 data.
- Record every exposure to outcome data, even an accidental one, with what was seen and why it does not compromise the freeze.
- The SSD is exFAT: no symlinks, and run `dot_clean -m` before committing.
- Commit and push only `codex/paper-c-spec`. End commit messages with the attribution line your harness specifies.
- Report failures and nulls with the same completeness as positive results. If a step is skipped, say so.

## Budget

About 190 h for Paper C, plus at most 55 h for C-VIRTUAL (15 h feasibility, then go/no-go, then 40 h), so 245 h at most. Cut order: C-VIRTUAL, then TISMO, then Perturb-CITE-seq, then the C1 display. The cell-line methylation check is never cut.
