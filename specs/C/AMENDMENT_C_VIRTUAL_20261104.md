# Paper C amendment: secondary module C-VIRTUAL (Paper D merged into C)

**Status: DRAFT, 4 Nov 2026. NOT SIGNED.** The user approved the merge in principle ("Yes, merge them", relayed by the coordinator session on 4 Nov 2026). The user answered Q2 on 5 Nov 2026 ("Yes, within 3-fold"). The user has not yet approved this text or answered the other questions in section 11. Signed `specs/C/SPEC_v2.md` (v2.1) stays in force without change until the user signs this amendment.

## 0. What this amendment does
- **Adds** one conditional secondary module, `C-VIRTUAL`, to Paper C.
- **Does not change** any C v2.1 product: C-P, C-FAV, C-CLASS, C2, C-CONTEXT and C-HANDOFF. No C product, gate or claim depends on any model.
- **Replaces** "Paper D remains separate" in `docs/decisions/C_FRAMEWORK_20261015.md` item 8. The rest of item 8 stays: a virtual prediction does not corroborate another prediction, and it does not fill missing measured validation in C.
- **Result if the module fails:** it is reported as "not run", with the reason. C still stands.

**The main finding for the decision.** PC3 has no compound at an exact Tahoe dose. This includes decitabine: PC3 has 1.0 µM and Tahoe has 0.5 and 5.0 µM. Under the 15 Oct D rule, no primary test unit would exist. On 5 Nov 2026 the user accepted the nearest Tahoe label within 3-fold (Q2), which gives 14 test compounds. This decision replaces the 15 Oct rule once the amendment is signed.

## 1. Question
In PC3 prostate cancer cells at 24 h, does a frozen virtual-cell model predict the measured response to a drug better than the average response to the same drug in other cell lines?

This is the old D1 question, now limited to the one prostate data set that can answer it. D2-PAIR (the PhysiCell tumour and T-cell model) is not part of this module (Q10).

## 2. Facts re-checked on 4 Nov 2026
Each row was checked against the primary record in this session. Only labels and file structure were read, not PC3 expression values (section 9).

| Fact | Result | Source |
| --- | --- | --- |
| Model revision | `ST-HVG-Tahoe` at `ca6b751972493f8448e3256d1340ae70ad43e1e7`, last modified 2026-05-29 | Hugging Face manifest |
| Prostate line in the model | **None.** `cell_type_onehot_map.pkl` decodes to 50 lines; no PC-3, LNCaP, 22Rv1, DU145, VCaP or NCI-H660 | Zeroshot run directory |
| Training lines | **45** (50 less the 5 zeroshot test lines C32, HOP62, HepG2/C3A, Hs 766T, PANC-1) | `zeroshot/generalization.toml` |
| Drug vocabulary | 1,138 labels; 0.05, 0.5 and 5.0 µM only | Tahoe `sample_metadata`, 1,344 rows |
| Epigenetic labels in Tahoe | Decitabine, 5-azacytidine, belinostat, panobinostat, tucidinostat. No entinostat, vorinostat or tazemetostat | Same, by name |
| Ordered gene list | **Not released.** 87 files checked by file name. `var_dims.pkl` holds the full gene list (`gene_dim` 62,710) and `hvg_dim` 2,000 as a number only. `data_module.torch` is 1.9 kB | Hugging Face manifest and file reads |
| PC3 in GSE306429 | **Confirmed.** 85 compounds, 88 compound-dose conditions, six plates, 24 h | `GSE306429_combined_limma.csv.gz`, identity columns only |
| PC3 decitabine | **Confirmed.** 1.0 µM, two plates (ILD1-004, ILD1-008). Nearest Tahoe label 0.5 µM, 2-fold away | Same |
| Licence | Arc Research Institute State Model Non-Commercial License. Output may be distributed (§2.1). Sponsored research for a commercial entity is not a non-commercial purpose (§1.4) | `MODEL_LICENSE.md` at the pinned revision |

**PC3 inventory** (full table: `specs/C/c_virtual_pc3_inventory_20261104.tsv`):

| Step | Compounds left |
| --- | --- |
| PC3 compounds in GSE306429 | 85 |
| Also in the Tahoe vocabulary (name, then PubChem identity) | 20 |
| At an exact Tahoe dose | **0** |
| Within 3-fold of a Tahoe dose | 18 (bortezomib 16.7-fold and panobinostat 5-fold fail) |
| Within 3-fold and on at least 2 plates | **14** |

The 14 are belinostat, crizotinib, dabrafenib, decitabine, dexamethasone, doxorubicin, fedratinib (TG-101348), neratinib, niclosamide, penfluridol, resveratrol, rucaparib, sapanisertib and sildenafil. All are 1.67-fold or 2-fold from the nearest label.

Limits of this inventory:
- Eight PC3 names did not resolve in PubChem (`BRD-K76674262`, `CLT-MCD-037`, `CLT-MCD-046`, `JNK-9L (JNK Inhibitor)`, `NFkB Activation Inhibitor II`, `SC26196`, `T3364366`, `angiogenesis-inhibitor`), so they count as not in Tahoe.
- The 355 ILD2 conditions have blank `cell_id` and `replicate` fields. PC3 identity on ILD2 plates rests on the GEO tarball names and must be confirmed at gate V1.
- Sunitinib is on one plate and "Sunitinib Malate" on another. They could make a fifteenth compound if the audit accepts them as the same active drug.
- Rapamycin (ILD1-004) and temsirolimus (ILD1-008) each appear on one plate at 10 µM, so neither has a replicate.
- The inventory comes from the limma table. Raw-data quality checks can remove more conditions.

**Corrections to `docs/research/D_SPEC_V2_EVIDENCE_20261103.md`** (that file is on `codex/paper-d-spec` and is not edited here):
1. Section 1.3 gives `gene_dim` as 2,000. It is 62,710.
2. Gene-list route (b), `adata_real.h5ad`, is closed. Its `var` index is the integers 0 to 1,999, with no names.
3. Gene-list route (c), `*_real_de.csv`, is closed. Its `feature` column is also an integer.
4. Section 6 says redistributing predictions requires the licence notice. The complete licence copy is for the model and Derivative Works (§3). For Output, the requirement is a prominent citation of Adduri et al. (2025).
5. The 3 Nov status note says 49 of 50 names decoded. All 50 decode.

**New route to the gene list (untested).** `adata_real.h5ad` keeps real values in model column order. `X` is uncompressed and stored by row, so one cell costs an 8 kB byte-range read and the 111 GB file need not be downloaded. In four rows spread through the file, `expm1(x)` values were exact integer multiples of one per-cell unit. This shows the values are `log1p` of scaled integer counts, so the counts in each column can be recovered. Those columns can then be matched to Tahoe genes by comparing integer counts. The cell barcodes in this file (`cell_000000`) are local labels and do not join to Tahoe barcodes, so the match must use counts. Gate V2 tests this route.

## 3. Test units
- **Primary data:** GSE306429, PC3, 24 h, with library-matched controls on the same plate. Measured cells come from the raw data. The limma table is not the outcome.
- **Test unit:** one compound at one dose, with one label in the Tahoe vocabulary and at least 2 plates. The dose must be within 3-fold of the Tahoe label (Q2, decided 5 Nov 2026). The nearest label is used for model and baseline alike. The current count is 14.
- **Replicate:** plate. There are about 2 per compound. This is below C's rule of 3 independent cultures, so this data set **never** enters C-P (Q11).
- **Epigenetic subset:** decitabine and belinostat only. Two drugs is descriptive only. Absent drugs are reported as "not in model vocabulary".

## 4. Models
- **Primary:** State `ST-HVG-Tahoe`, zeroshot run, `checkpoints/final.ckpt`, seed 42, revision as in section 2. Weights are frozen. No fine-tuning.
- PC3 is an unseen line, so this is zero-shot extrapolation to a tissue absent from training.
- Input cells are the PC3 controls from the same plate, with the transform of gate V2.
- **Silent fallback is a stop.** `tx infer` can replace an unknown label with a default control label. The adapter must assert that every drug label is found and that matched controls exist. A process exit of zero does not pass this check.
- No other virtual-cell model is in the module. chemCPA, CellFlow, PRnet, Tahoe-x1, GEARS and scGPT stay out.

## 5. Baselines
- **Primary comparator, required (user's condition 4):** same drug, same Tahoe label, mean response across the 45 training lines:
  `B_cg = (1/|K_c|) Σ_k mean_r(delta_train,krg)`.
  It uses the same label, gene set and transform as the model. A drug with an empty K_c is blocked, not replaced.
- **Secondary, kept:** no change (zero); global mean over all drugs; the replicate-split ceiling (one plate predicts the other), which shows how much of the error is noise; Rhaister-O (Apache-2.0, `y = β(p,g) + γ(p,g)·x(c*,g)`) if it runs within budget. Its published claim of beating State is unverified, so this module neither repeats nor relies on that claim.
- **Dropped from the 15 Oct list to save time:** ridge, kNN, same-context other-drug mean.

## 6. Metrics
These are unchanged from `specs/D/ANALYSIS.md`:
- `delta_crg = mu_crg − mu_0crg`, where c is the condition, r the replicate, g the gene and 0 the matched control.
- `L_m(cr) = (1/|G|) Σ_g (delta_crg − m_crg)²`. G is the same genes for every model: recovered model genes also measured in GSE306429.
- `theta = (1/|D|) Σ_d [(1/|C_d|) Σ_c [(1/|R_c|) Σ_r {L_B(cr) − L_S(cr)}]]`. Positive favours State. Drug, condition and replicate have equal weights.
- **Interval:** 2,000 paired hierarchical bootstrap resamples, with the drug as the top unit.
- **Result labels:**
  - "better than baseline": the 95% interval for theta is above 0 and theta is at least `delta_min`;
  - "not better": the interval is at or below 0;
  - "inconclusive": any other result;
  - "descriptive only": fewer than 10 drugs;
  - "not run": a gate failed.
- **`delta_min`** is 10% of the mean baseline error (Q7), frozen before any PC3 outcome is read.
- **Dose sensitivity:** repeat with the other neighbouring Tahoe label, for model and baseline together.

## 7. Go/no-go
Each gate must pass in this order. A failure stops the module. Its report says "not run" and gives the gate and the evidence.

| Gate | Pass condition | Reads PC3 outcomes? |
| --- | --- | --- |
| V0 Sign-off | User signs this amendment; licence position confirmed (Q12) | No |
| V1 Test units | PC3 identity confirmed on ILD2 plates; control cells present on each plate; at least 10 drugs remain (below 10: descriptive only, and the decision returns to the user) | Metadata and cell counts only |
| V2 Gene list | At least 99% of the 2,000 columns map to one gene each, and counts agree on cells not used for the match; target sum and transform confirmed | No |
| V3 Software | Exact environment locked; checkpoint loads; output reproduces released results on a non-prostate line within a stated tolerance | No |
| V4 Baseline | Tahoe training responses computed for every test label across the training lines. Tahoe `expression_data` is 338 GB and the SSD has 244 GiB free, so it is streamed and filtered, not copied | No |
| V5 Gene overlap | At least 90% of recovered genes measured in PC3 | No |
| V6 Freeze | C gates 3 and 4 passed; test manifest, G, `delta_min` and code frozen and hashed | No |
| V7 Run | Inference finished, adapter assertions passed, no fallback used. Measured PC3 responses are read only now | **Yes** |

**Time rule:** if V1 to V5 do not pass within 15 h, the module stops as "not run". Bulk data or L1000 data never replace the primary test.

## 8. Claim ceiling
**Can claim:** in PC3 at 24 h, for the named drugs and at the nearest Tahoe dose, the frozen model's error was (or was not) lower than the same drug's average response in other lines.

**Cannot claim:**
- that virtual cells can replace an experiment;
- that the model works for prostate cancer in general: this is one line, and PC3 does not express the androgen receptor;
- anything at the exact measured dose;
- that a predicted response is evidence for a compound, a gene or a mechanism;
- any claim about immune effects, ICI response or patients;
- "digital twin", in any form.

## 9. Firewall between C-VIRTUAL and signed C
- No model output enters C-P, C-FAV, C-CLASS, C2, the evidence tiers, the Pareto set or the wet-lab nomination. Predictions are never Level 2 evidence.
- Q_M, Q_E and all C results are never used to choose, tune or filter the model, the genes or the drugs.
- No C gate waits for this module.
- PC3 outcomes in GSE306429 are read only after C gates 3 and 4.
- C-HANDOFF may hold one line of text saying what the module found. It carries no score.

**Exposure record (4 Nov 2026).** `GSE306429_combined_limma.csv.gz` (SHA-256 `1e36ee2bd0c16854c057be69855fd66a0c8b8c36b6cba4273718732ceca82d6b`) was read for its identity columns only. One header check displayed two A375 decitabine logFC rows (genes AL627309.1 and AL627309.5). They are non-prostate and are not query genes. No PC3 expression value was read. The file is now in the Trash. Four single-cell rows of non-prostate `adata_real.h5ad` were read to test the transform.

## 10. Budget and cut order
- **Hours:** 15 h feasibility (V1 to V5), then the go/no-go, then up to 40 h for the run and write-up. The maximum is 55 h, on top of C's 190 h, so **245 h**. If the module stops at the feasibility limit, the total is 205 h.
- **Priority:** C-P and C-FAV work goes first. No C-VIRTUAL hour is taken from C's 190 h.
- **Whole-paper cut order (amends SPEC_v2 §9):** C-VIRTUAL, then TISMO, Perturb-CITE-seq and the C1 display (parity kept). The cell-line methylation check is never cut.
- **Cut order inside the module:** MIX-seq (if kept, Q1), then Rhaister-O, then the dose sensitivity. The primary comparator, the no-change baseline and the replicate ceiling are never cut.

## 11. Questions for the user (answer by number)
Q2 is answered. The others are open: the coordinator's hand-over states that the user had answered none of them.

| # | Question | Recommendation |
| --- | --- | --- |
| Q1 | Which test set? | GSE306429 PC3 as primary. MIX-seq as descriptive only and first to cut: it has no replicates, no epigenetic drug and few matched doses. Its LNCaP ID `ACH-000510` conflicts with Tahoe, so resolve that before any join |
| Q2 | Dose rule? | **DECIDED by the user, 5 Nov 2026: "Yes, within 3-fold."** Nearest Tahoe label within 3-fold, for model and baseline alike. The claim says "nearest dose". This relaxes the 15 Oct rule (no neighbouring-dose switch). Exact dose would have given 0 units. An exact-dose sensitivity cannot work (0 units), so the other-neighbour sensitivity of section 6 is used |
| Q3 | Gene list route? | Try the count-matching route of section 2 at V2. Post a public issue to Arc only if that fails, and only with your approval. If both fail: no-go. ST-SE-Tahoe stays out, because it would be a different model |
| Q4 | Model? | State `ST-HVG-Tahoe` only, `final.ckpt`, seed 42 |
| Q5 | Baseline? | Same drug and label, mean over the 45 training lines. Rhaister-O as a secondary comparator |
| Q6 | Unit and interval? | Drug as top unit, 2,000 paired bootstrap resamples |
| Q7 | Success rule? | 95% interval for theta above 0, `delta_min` 10% of baseline error, fewer than 10 drugs is descriptive only. With 14 drugs now, losing 5 in quality control makes it descriptive |
| Q8 | Epigenetic subset? | Named descriptive secondary: decitabine and belinostat. Panobinostat fails the dose rule at 5-fold. Absent drugs reported as "not in model vocabulary" |
| Q9 | Budget and no-go? | 15 h, go/no-go, then 40 h. A no-go is a documented result |
| Q10 | What happens to D2-PAIR (PhysiCell), the Paper E interface, the Lin TIME reproduction and the 15 Oct prospective experiment family? The merge proposal does not cover them | Keep them out of C. Mark them deferred and keep `specs/D/` as the historical record. Paper E then needs a new input source, or a decision to defer it too |
| Q11 | GSE306429 has a PC3 decitabine arm, and C's audit rule says 2 cultures per arm is "descriptive only". Should it enter the C-P audit? | List it in the metadata audit as a row, with status "not admitted to Δ_Q". Plate independence is unknown, and C-VIRTUAL then cannot affect C-P. Do not add a descriptive C-P analysis |
| Q12 | Does your institution meet the licence's Non-Commercial Entity definition (§1.3), with no commercial sponsor for this work (§1.4)? | Only you can confirm this. Any commercial sponsor means the module does not run |

## 12. Effect on other records (on signature)
- `docs/decisions/C_FRAMEWORK_20261015.md` item 8: "separate" is replaced as in section 0. That file is not edited; this amendment supersedes that word.
- `specs/D/` stays as read-only history. Decisions D-A and D-F carry over as narrowed here. D-B, D-C and D-G follow the answer to Q10. D-D (D2 primary) lapses.
- G1 to G8 of `specs/D/REPRODUCE_AND_READINESS.md` are replaced by V0 to V7.

## 13. Proposed wording for `AGENTS.md` and `CONTEXT.md`
**Proposal only. Not applied.** These two files wait for the user's approval.

`AGENTS.md`, line 5:
- Now: "Preserve A/B/C/D labels and the full restored Paper C source architecture."
- Proposed: "Preserve A/B/C labels and the full restored Paper C source architecture. Paper D is merged into Paper C as the conditional secondary module C-VIRTUAL; keep `specs/D/` as read-only history."
- Now: "All four spec packages require review before production implementation; only one paper's production implementation is active at a time."
- Proposed: "All three spec packages require review before production implementation; only one paper's production implementation is active at a time."

`CONTEXT.md`, line 13, Paper C:
- Proposed: "**Paper C**: The pharmacological prioritisation study integrating signature reversal, model context and orthogonal functional/immune evidence, with one conditional secondary module, C-VIRTUAL. It is the third current paper and Claude's original Paper 4."

`CONTEXT.md`, line 15, Paper D:
- Proposed: "**Paper D**: Merged into Paper C on the user's decision of 4 Nov 2026. Its virtual-cell benchmark continues as **C-VIRTUAL**, the conditional comparison of a frozen virtual-cell model against the same drug's average response on measured prostate responses. No C result depends on it. `specs/D/` is history."

The wording about D2-PAIR and Paper E may change after Q10.

## 14. Check with your supervisor
Before you sign, check the registered thesis protocol with your supervisor. If it lists Papers C and D as separate papers, this merge changes the registered thesis structure. The signature here does not replace any approval that the protocol requires.

## 15. Signature
Signed by: ____________  Date: ____________  (The user signs by writing "I sign it" for this amendment.)
