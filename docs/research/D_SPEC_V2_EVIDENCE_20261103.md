# Paper D spec v2: primary-source evidence audit

> **Status note, 4 Nov 2026:** the user approved merging Paper D into Paper C as the conditional secondary module `C-VIRTUAL`, so no standalone `specs/D/SPEC_v2.md` was written. This file stays as the evidence for that module. Spot-checked by the session against primary records on 3 Nov: the State cell-line map has no prostate line (49 of 50 names decoded), the GEO record for GSE306429 names PC3, and `tahoebio/Rhaister` exists on Hugging Face. The other rows are as the research agent reported them. The user did not answer the open questions.

Evidence checked 3 November 2026. Scope: Arc State Tahoe checkpoints (code, configs and metadata), the Tahoe-100M cell-line and drug inventory, public single-cell chemical-perturbation datasets that contain prostate cancer cell lines, and other chemical-perturbation models with downloadable checkpoints. Only primary sources were used: official GitHub repositories and API, Hugging Face model and dataset manifests and cards, HF datasets-server row API, NCBI GEO/E-utilities records, figshare API and the original papers. No model weights, expression matrices or files over 50 MB were downloaded. Small metadata files (configs, TOML, pickles under 6 MB, parquet rows via the HF row API, GEO SOFT and hash/metadata tables, figshare README and supplementary xlsx) were fetched to a temporary scratch directory. Pickles were read with `pickletools` opcode parsing only and never unpickled. **VERIFIED** means seen directly in the cited source. **UNVERIFIED/UNKNOWN** means not confirmed in a primary source.

## Key findings for the spec

1. **Tahoe-100M and every released State Tahoe checkpoint contain no prostate cell line (VERIFIED).** The ST-HVG-Tahoe `cell_type_onehot_map.pkl` lists exactly 50 lines, none of them prostate. The Tahoe `cell_line_metadata` table (102 names) has no `Prostate` organ. A State prediction for PC-3, LNCaP, 22Rv1, DU145 or VCaP is therefore an unseen-cell-line extrapolation.
2. **The State repos and code have not changed since the earlier audit (VERIFIED).** ST-HVG-Tahoe is still at `ca6b7519…` and ST-SE-Tahoe at `03b1971d…`, both last modified 2026-05-29. GitHub `main` HEAD is still `9bbfe78a` (2026-07-24, `arc-state 0.11.3`), with zero commits since 2026-09-01. The latest release tag is v0.11.1 (2026-06-29). The arcinstitute HF org shows no new chemical-perturbation State checkpoint and no "State 2".
3. **No released file gives the ordered 2,000 HVG list (VERIFIED absence among listed files).** `var_dims.pkl` and `hparams.yaml` contain `gene_names` with **62,710** entries (the full Tahoe gene vocabulary), even though `input_dim = output_dim = hvg_dim = 2000`. The HVG column identity and order must be reconstructed. They are UNKNOWN from the released assets.
4. **The HVG transform in code is generic (VERIFIED).** At `9bbfe78`, `state tx preprocess_train` runs `sc.pp.normalize_total(adata)` with scanpy's default target (no `target_sum`), then `sc.pp.log1p`, then `sc.pp.highly_variable_genes(n_top_genes=2000)` with the default flavour, and stores `adata[:, highly_variable].X` in `.obsm['X_hvg']`. Whether the released Tahoe checkpoint was built with exactly this command is UNVERIFIED.
5. **The drug input is a categorical one-hot over 1,138 `drugname_drugconc` labels (VERIFIED).** These are 379 drugs × {0.05, 0.5, 5.0} µM plus `[('DMSO_TF', 0.0, 'uM')]`, with labels such as `"[('Decitabine', 0.05, 'uM')]"`. State Tahoe cannot represent an unseen drug or an unseen dose.
6. **Tahoe-100M epigenetic drugs (VERIFIED).** Present at 0.05/0.5/5 µM with 24 h exposure: Decitabine, 5-Azacytidine, Tucidinostat, Belinostat, Panobinostat, Procainamide HCl and carbamazepine (the last annotated as an HDACi). Also present: the AR antagonists darolutamide, bicalutamide and apalutamide, plus abiraterone acetate. **Absent: entinostat, vorinostat, tazemetostat and enzalutamide.**
7. **The State split configs hold out no prostate line (VERIFIED).** Zeroshot test lines are C32, HOP62, HepG2/C3A, Hs 766T and PANC-1, with no zeroshot validation line. Fewshot uses the same five lines with 56 val and 777–778 test labels each. Decitabine and tucidinostat are fewshot test labels in those five lines and are training labels elsewhere.
8. **The two strongest public prostate single-cell chemical sets are MIX-seq and GSE306429 (VERIFIED).** MIX-seq (figshare 10.6084/m9.figshare.10298696.v3) contains LNCaP in experiments 1, 3, 5 and 10, and PC3 and 22Rv1 in experiment 3 only. It has 13 drugs at single doses, 6/24 h, with **no DNMT/HDAC/EZH2 inhibitor**. GSE306429 (Science 2025, Cellarity) has **PC3 plus 104 compounds at 24 h in duplicate** and contains decitabine at 1.0 µM. That decitabine row was verified in A375. PC3 coverage is stated in the GEO summary but not verified row by row.
9. **sci-Plex (GSE139944) has no prostate line (VERIFIED).** Its cell lines are A549, K562 and MCF7, with A549 also at 72 h. It does contain entinostat, decitabine, azacitidine, tazemetostat and 12+ named HDACis at 10/100/1000/10000 nM for 24 h. These are useful non-prostate training references, not prostate test data.
10. **Model landscape.** Only SMILES or embedding models can represent unseen drugs: chemCPA (checkpoint zip reachable, MIT), PRnet (Apache-2.0, weight server unverified) and CellFlow (MIT, fingerprints, no released pretrained checkpoint found). State, CPA (one-hot by default) and Rhaister (Tahoe, Apache-2.0, June 2026) use observed-perturbation vocabularies. GEARS and the scGPT perturbation tutorial are genetic only. Tahoe-x1 (Apache-2.0) is an embedding foundation model. Rhaister is an explicit "observed statistics" baseline that its authors report beats State. It is directly relevant to the "drug mean in other lines" comparator.

## 1. Arc Institute State

### 1.1 Repository status

| Item | Value | Status / source |
|---|---|---|
| GitHub default branch HEAD | `9bbfe78a434a55205e4de834e1ea99f85f7a3add`, 2026-07-24, "Merge pull request #274 … raw-count-normalization-h5ad" | VERIFIED: [commits API](https://api.github.com/repos/ArcInstitute/state/commits?per_page=5) |
| Commits since 2026-09-01 on `main` | 0 | VERIFIED: [commits?since=2026-09-01](https://api.github.com/repos/ArcInstitute/state/commits?since=2026-09-01T00:00:00Z). Other branches not inspected. |
| Package version at HEAD | `arc-state 0.11.3` | VERIFIED: [pyproject.toml@9bbfe78](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/pyproject.toml) |
| Latest GitHub releases | v0.11.1 (2026-06-29, `cc22e694`), v0.11.0 (2026-06-29), v0.10.2 (2026-01-23) | VERIFIED: [releases API](https://api.github.com/repos/ArcInstitute/state/releases) |
| Code licence | CC BY-NC-SA 4.0 (README "Licenses"); GitHub API reports `NOASSERTION` | VERIFIED: [README](https://github.com/ArcInstitute/state#licenses) |
| Model/weights/output licence | "Arc Research Institute State Model Non-Commercial License". Non-commercial purpose only (§4.1). "Output" is defined as results of running the model or a derivative (§1.5). Fine-tunes count as Derivative Works (§1.2). Redistribution must carry the licence (§3). | VERIFIED: `MODEL_LICENSE.md` in [ST-HVG-Tahoe@ca6b751](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/blob/ca6b751972493f8448e3256d1340ae70ad43e1e7/MODEL_LICENSE.md) |

### 1.2 Hugging Face model repos (arcinstitute)

| Repo | Revision (sha) | Last modified | Chemical? | Status |
|---|---|---|---|---|
| `ST-HVG-Tahoe` | `ca6b751972493f8448e3256d1340ae70ad43e1e7` | 2026-05-29 | yes | VERIFIED [manifest](https://huggingface.co/api/models/arcinstitute/ST-HVG-Tahoe) |
| `ST-SE-Tahoe` | `03b1971d7cc93a7535fd2e957c6948dba267378b` | 2026-05-29 | yes (`X_state` input) | VERIFIED [manifest](https://huggingface.co/api/models/arcinstitute/ST-SE-Tahoe) |
| `ST-HVG-Parse`, `ST-SE-Parse` | `827df657…`, `fa458ffd…` | 2026-05-29 | not inspected (Parse PBMC) | VERIFIED existence |
| `ST-*-Replogle`, `st-se-replogle-full`, `st-x-replogle-full`, `PIE_replogle_*` (2026-10-05) | — | — | genetic (Replogle CRISPRi) | VERIFIED existence; PIE tags `perturbation-prediction`, contexts hepg2/jurkat/k562 |
| `SE-600M` (`5a9a80f4…`), `SE-100M` (`bc727023…`) | — | 2026-02/04 | embedding only | VERIFIED |
| `Stack-Large`, `Stack-Large-Aligned` | `6e1f352e…`, `b09f085d…` | 2026-06-18 | in-context foundation model (217M, scBaseCount pretraining); card shows only an embedding tutorial; non-commercial licence | VERIFIED [card](https://huggingface.co/arcinstitute/Stack-Large) |
| `bolero-models` | `4a7f25be…` | 2026-10-30 | sequence-to-ATAC (Borzoi-type), MIT | VERIFIED; not a drug model |

The listing comes from the [arcinstitute model listing API](https://huggingface.co/api/models?author=arcinstitute&limit=200). **No newer chemical-perturbation State checkpoint (no "State 2", no new Tahoe fine-tune) is listed (VERIFIED absence in org listing as of 2026-11-03).**

### 1.3 ST-HVG-Tahoe file inventory (revision `ca6b751`)

The top level holds `MODEL_LICENSE.md`, `MODEL_ACCEPTABLE_USE_POLICY.md`, `zeroshot/generalization.toml` (590 B) and `fewshot/generalization.toml` (150,876 B). Each run directory (`zeroshot/state_generalization_zeroshot_X_hvg/`, `fewshot/state_generalization_X_hvg/`) contains:

- `config.yaml` (2.7 KB), `version_0/hparams.yaml` (790 KB), `version_0/metrics.csv`, `wandb_path.txt`
- `var_dims.pkl` (978 KB), `pert_onehot_map.pt` (5.5 MB), `cell_type_onehot_map.pkl` (518 KB), `batch_onehot_map.pkl` (16 KB), `data_module.torch` (1.9 KB)
- `checkpoints/{best,final,last}.ckpt` (final.ckpt = 1.07 GB, not downloaded)
- `eval_best.ckpt/` and (fewshot) `eval_last.ckpt/` with per-line `{line}_agg_results.csv` (3.5 KB), `_results.csv` (468 KB), `_pred_de.csv` / `_real_de.csv` (~0.4 GB each), and `adata_pred.h5ad` / `adata_real.h5ad` (`adata_real.h5ad` = 111 GB)

ST-SE-Tahoe has the same layout with `X_state`, but **no `generalization.toml` files** and an `eval_last.ckpt` in both splits. VERIFIED from the manifests above.

**There is no `gene_names`, `hvg_genes`, `var_names` or HVG-list file in either repo (VERIFIED from sibling listing).** The `gene_names` key does exist inside `var_dims.pkl` and `hparams.yaml`:

| Field (zeroshot HVG run) | Value | Status |
|---|---|---|
| `input_dim`, `hvg_dim`, `gene_dim`, `output_dim` | 2000 | VERIFIED (pickletools; hparams.yaml) |
| `pert_dim` | 1138 | VERIFIED |
| `batch_dim` | 14 (plates) | VERIFIED |
| `gene_names` length | **62,710** unique entries (starts `TSPAN6, TNMD, DPM1…`, 20,930 bare `ENSG…` IDs, ends `…ENSG00000291316, TMEM276`) | VERIFIED. This is the full Tahoe gene vocabulary, **not** the 2,000 HVGs. |
| `pert_names` | 1138 labels | VERIFIED |
| `control_pert` in hparams | `"[('DMSO_TF', 0.0, 'uM')]"`; `config.yaml` says `control_pert: DMSO_TF` | VERIFIED |
| `embed_key` / `output_space` / `pert_rep` / `pert_col` / `cell_type_key` / `batch_col` | `X_hvg` / `gene` / `onehot` / `drugname_drugconc` / `cell_name` / `plate` | VERIFIED [config.yaml](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/zeroshot/state_generalization_zeroshot_X_hvg/config.yaml) |
| Model | `state`, LLaMA backbone 8 layers, hidden 768, `cell_set_len 256`, energy distributional loss, `predict_residual: true`, max_steps 200,000 | VERIFIED (config.yaml) |

**Consequence for the spec:** the ordered 2,000 HVG list is **UNKNOWN** from released assets. Three routes to reconstruct it exist, none verified: (a) recompute HVGs on Tahoe-100M with the `preprocess_train` recipe, which is not guaranteed to reproduce the column order or set used for training; (b) read the `var`/column names of `adata_real.h5ad` (111 GB, outside the download budget); (c) recover the gene names from the `*_real_de.csv` files (~0.4 GB each), which list genes but not necessarily input order. The spec should require a verified gene-order file before any inference and should treat this as a blocking item.

### 1.4 HVG transform definition in code

From [`src/state/_cli/_tx/_preprocess_train.py`@9bbfe78](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/src/state/_cli/_tx/_preprocess_train.py), lines 46–55 (VERIFIED):

```python
sc.pp.normalize_total(adata)          # scanpy default target_sum=None (median library size)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=num_hvgs)   # default flavor
adata.obsm["X_hvg"] = adata[:, adata.var.highly_variable].X.toarray()
```

The README documents `--num_hvgs 2000` (VERIFIED [README@9bbfe78](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/README.md)). Under this recipe the columns follow the original `adata.var` order restricted to HVGs. Whether the Tahoe release used this exact recipe, the same scanpy version and the same median-based target sum is **UNVERIFIED**. The State preprint could not be re-read in this session (bioRxiv returned HTTP 429). The latest commit (`13bc762`, "normalize raw counts in model workflows", 2026-07-24) touched raw-count handling. Its exact interaction with `tx infer` was not re-audited here.

### 1.5 Drug vocabulary format

The format is `drugname_drugconc` = Python-literal string of a list of one (name, concentration, unit) tuple, e.g. `"[('Decitabine', 0.05, 'uM')]"`. VERIFIED in the [Tahoe-100M card](https://huggingface.co/datasets/tahoebio/Tahoe-100M) (`sample_metadata` field description), in Tahoe `sample_metadata` rows and in the State `hparams.yaml` control string. Tahoe `sample_metadata` has 1,344 samples, 1,138 unique `drugname_drugconc`, 380 `drug` values (379 drugs + DMSO_TF) and 14 plates (VERIFIED via the [HF datasets-server rows API](https://datasets-server.huggingface.co/rows?dataset=tahoebio%2FTahoe-100M&config=sample_metadata&split=train&offset=0&length=100)). Concentrations used: 0.05, 0.5 and 5.0 µM only. A trametinib "(DMSO_TF solvate)" entry exists at all three doses.

## 2. Tahoe-100M

| Item | Value | Status / source |
|---|---|---|
| Dataset revision | `349e2a55f5538a3e73b32a06c6bdd8e9e87011e8`, last modified 2026-10-14; licence `cc0-1.0` | VERIFIED [API](https://huggingface.co/api/datasets/tahoebio/Tahoe-100M) |
| Paper | Zhang J, Ubas AA, de Borja R, … Goodarzi H, Yu J. *Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling*. bioRxiv doi:10.1101/2025.02.20.639398 | VERIFIED [bioRxiv](https://www.biorxiv.org/content/10.1101/2025.02.20.639398v1.full) |
| Cell lines | "50 cancer cell lines" (47 used in downstream analyses; 13 organs) | VERIFIED paper + `cell_type_onehot_map.pkl` |
| Drugs | 379 distinct drugs (Results); Methods say 380 compounds. `drug_metadata` has 379 rows. | VERIFIED |
| Doses | 0.05, 0.5, 5.0 µM | VERIFIED (sample_metadata; Fig. 6 caption) |
| Duration | "Cells were exposed to drug media for 24 hours" | VERIFIED (Methods) |
| Cells | 100.6 M pass minimal filters; 95.6 M pass full filters | VERIFIED (paper) |
| Controls | DMSO_TF vehicle, plate-matched; wells H11/H12 contain media without compound | VERIFIED (card + paper) |

### 2.1 The 50 cell lines used by State Tahoe (and Tahoe-100M)

From the decoded `cell_type_onehot_map.pkl` of ST-HVG-Tahoe zeroshot (VERIFIED):

A-172, A-427, A498, A549, AN3 CA, AsPC-1, BT-474, C-33 A, C32, CFPAC-1, CHP-212, COLO 205, H4, HCT15, HEC-1-A, HOP62, HS-578T, HT-29, HepG2/C3A, Hs 766T, J82, KATO III, LOX-IMVI, LS 180, LoVo, MIA PaCa-2, NCI-H1573, NCI-H1792, NCI-H2030, NCI-H2122, NCI-H23, NCI-H2347, NCI-H460, NCI-H596, NCI-H661, PANC-1, Panc 03.27, RKO, RPMI-7951, SHP-77, SK-MEL-2, SNU-1, SNU-423, SW 1088, SW 1271, SW 900, SW1417, SW48, SW480, hTERT-HPNE.

**Prostate lines: none (VERIFIED).** PC-3, DU145, 22Rv1, LNCaP, VCaP and NCI-H660 are all absent. The separate Tahoe `cell_line_metadata` table (1,000 driver-mutation rows, 102 cell names) has organs Bladder, Bowel, Breast, CNS, Cervix, Oesophagus/Stomach, Kidney, Liver, Lung, Ovary, Pancreas, PNS, Skin, Uterus and Vulva. There is **no Prostate** (VERIFIED, [rows API](https://datasets-server.huggingface.co/rows?dataset=tahoebio%2FTahoe-100M&config=cell_line_metadata&split=train&offset=0&length=100)). Note that this table includes lines not in the 50 (for example MCF-7, HCT116 and NCI-H1299), so it is not the screened panel.

### 2.2 State split configs

| Split | Training | Validation | Test | Prostate? |
|---|---|---|---|---|
| `zeroshot/generalization.toml` | all other lines in `tahoe_holdout` | none declared | C32, HOP62, HepG2/C3A, Hs 766T, PANC-1 (whole lines) | none (VERIFIED) |
| `fewshot/generalization.toml` | all lines; listed perturbations held out per line | 56 labels per held-out line | 777 (C32) / 778 labels per line | none (VERIFIED) |

Fewshot test labels in all five lines include Decitabine and Tucidinostat at all three doses. 5-Azacytidine, Belinostat and Panobinostat are not in val/test for those lines (VERIFIED by parsing the TOML), so they are training labels. Sources: [zeroshot TOML](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/zeroshot/generalization.toml), [fewshot TOML](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/fewshot/generalization.toml).

## 3. Epigenetic and prostate-relevant drugs in Tahoe-100M (Question 5)

Sources: `drug_metadata` and `sample_metadata` via the HF rows API at revision `349e2a55` (VERIFIED).

| Drug (Tahoe spelling) | MOA-fine / targets (Tahoe annotation) | Labels and plates | In State vocab |
|---|---|---|---|
| Decitabine | DNMTi; DNMT1/3A/3B | 0.05 (plate7), 0.5 (plate8), 5.0 µM (plate9) | yes |
| 5-Azacytidine (= azacitidine) | DNMTi; DNMT1 | 0.05 (plate10), 0.5 (plate11), 5.0 µM (plate12) | yes |
| Procainamide (hydrochloride) | annotated DNMTi | plates 7/8/9 | yes |
| γ-Oryzanol | annotated DNMTi | (doses not extracted) | yes |
| Tucidinostat (chidamide) | HDACi; HDAC1/2/3/8/10/11 | 0.05 (p4), 0.5 (p5), 5.0 µM (p6 and p14) | yes |
| Belinostat | HDACi | plates 10/11/12 | yes |
| Panobinostat | HDACi | plates 10/11/12 | yes |
| Carbamazepine | annotated "HDAC inhibitor" (questionable annotation; antiepileptic) | plates 10/11/12 | yes |
| Darolutamide, Bicalutamide | AR antagonist | plates 10/11/12 | yes |
| Apalutamide | AR antagonist | plates 7/8/9 | yes |
| Abiraterone acetate | CYP17A1 | plates 10/11/12 | yes |
| olaparib, Docetaxel | PARP / microtubule | three doses each | yes |
| **Entinostat (MS-275)** | — | **absent** | no |
| **Vorinostat (SAHA)** | — | **absent** | no |
| **Tazemetostat (EPZ-6438)**; any EZH2 inhibitor | — | **absent** (no EZH/EZH2 annotation in `drug_metadata`) | no |
| **Enzalutamide** | — | **absent** | no |

Absence is VERIFIED by name and by MOA/target string search over all 379 `drug_metadata` rows. A structure-level (SMILES/InChIKey) alias check was not run.

## 4. Public single-cell chemical-perturbation datasets with prostate lines

### 4.1 Summary table

| Dataset / accession | Prostate lines | Drugs, dose, time | Controls / replicates / cells | DNMT/HDAC/EZH2? | Status |
|---|---|---|---|---|---|
| **MIX-seq**, McFarland et al. 2020 *Nat Commun* 11:4296, doi:10.1038/s41467-020-17440-w; data [figshare 10.6084/m9.figshare.10298696.v3](https://api.figshare.com/v2/articles/10298696) (CC BY 4.0); no GEO accession for MIX-seq data | LNCaP clone FGC: expts 1, 3, 5, 10. PC3: expt 3. 22Rv1: expt 3. DU145: only "out_of_pool" (reference) | See 4.2. Single dose per drug; 6 and/or 24 h; trametinib time course 3–48 h | DMSO 0.2% vehicle per experiment and time point; untreated (expt 1); pools of 24–99 lines; ≈100 cells per line per condition in the 99-line pool (paper). No biological replicate number stated. | **None.** JQ1 (BET) is present in expt 10 (LNCaP pool). | VERIFIED (Supp. Tables 1–3 in figshare xlsx; paper [PMC7453022](https://pmc.ncbi.nlm.nih.gov/articles/PMC7453022/)) |
| **GSE306429**, DeMeo et al. 2025 *Science* 390:eadi8577, doi:10.1126/science.adi8577 (PMID 41129612) | **PC3** (plus A549, A375, HA1E, HEK293T, HepG2 and primary CD8+, CD34+, adipocytes, HBEC) | 104 compounds (88 from CMap), 24 h; `dose_uM` column in limma table; decitabine 1.0 µM present (row seen for A375, plate ILD1-001) | "in duplicate with library-matched controls"; 1,737 scRNA-seq samples; 1.26 M cells; hashed; 6 PC3 tarballs (ILD1-004/008, ILD2-005/006/017/018) | Decitabine: yes (A375 row VERIFIED; PC3 row UNVERIFIED). Others: UNKNOWN (full compound list not read; the limma table is 1.76 GB). | VERIFIED GEO summary, SOFT and first 3 MB of `GSE306429_combined_limma.csv.gz`, [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE306429) |
| **sci-Plex**, Srivatsan et al. 2020 *Science* (PMID 31806696), [GSE139944](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE139944) | **None.** A549, K562 and MCF7 (sciPlex3); HEK293T/NIH3T3 (sciPlex1); A549 (sciPlex2); A549/MCF7 HDACi (sciPlex4) | 188 compounds × 10/100/1000/10000 nM, 24 h; A549 also 72 h | Duplicate wells (rep1/rep2); vehicle wells; 649,340 cells | Yes: Entinostat (MS-275), Decitabine, Azacitidine, Tazemetostat (EPZ-6438), Panobinostat, Belinostat, Tucidinostat, Mocetinostat, Abexinostat, Pracinostat, Givinostat, Quisinostat, Dacinostat, Trichostatin A. **Vorinostat not in sciPlex3 metadata.** | VERIFIED from `GSM4150378_sciPlex3_A549_MCF7_K562_hashTable_metadata.txt.gz` (65 KB) and paper |
| sci-Plex variant: McFaline-Figueroa et al. 2024 (PMID 38645018), [GSE261618](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE261618) | None (glioblastoma A172, T98G, U87MG, BT112, BT228, BT333) | EGFR inhibitors | — | not checked | VERIFIED (GEO design) |
| Tahoe-100M | **None** | see §2–3 | see §2 | DNMTi/HDACi yes | VERIFIED |
| Tahoe EmeraldBay ([HF](https://huggingface.co/datasets/tahoebio/EmeraldBay), rev `752eb8f0`, CC BY 4.0, 2026-10-28) | **None.** 52 lines; organs as Tahoe, no Prostate | 27 anticancer drugs (KRAS/BRAF/EGFR/HER2/chemo), multiple doses incl. combinations, 5-day culture; 1.83 M cells | — | **None** | VERIFIED (card + rows API) |
| **Epiregulon drug set**, [GSE251977](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE251977) (SuperSeries GSE252883) | LNCaP clone FGC, VCaP, DU145, NCI-H660 | DMSO, enzalutamide 1 µM, ARV-110 1 µM, SMARCA2/4 degrader 0.1 µM; scMultiome (ATAC+RNA, hashed) | HTO-hashed; duration not stated in the protocol text read | No | VERIFIED (GEO SOFT); duration UNKNOWN |
| [GSE215943](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE215943) | LNCaP | enzalutamide 5 µM for 4, 7, 14 days vs DMSO; 4 samples | 1 sample per condition | No | VERIFIED (GEO SOFT) |
| [GSE266216](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE266216) (PMID 40456604) | VCaP | EtOH, dexamethasone, DHT, Dex+DHT; 4 samples | — | No (hormones) | VERIFIED (GEO) |
| [GSE283260](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE283260) | LNCaP, LNCaP95 (with breast lines) | endocrine therapy / CDK4/6 / CDK7 inhibitors; 2–7 days | 41 samples | No | VERIFIED (GEO design, truncated) |
| [GSE270568](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE270568) (PMID 39229204) | PC3 (with MDA-MB-231) | sublethal docetaxel or cisplatin; 1 or 10 days recovery | 605 samples (polyploid-cell study) | No | VERIFIED (GEO) |
| [GSE149681](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE149681) (PMID 34879849) | DU145, PC3 | docetaxel-sensitive vs resistant lines (not acute treatment) | 8 samples | No | VERIFIED |
| [GSE325232](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE325232) (2026-03-31) | LuCaP35CR **PDX tumours** (not a cell line) | enzalutamide, **EPZ-6438 (tazemetostat)**, combination | 1 GEO sample | EZH2i yes | VERIFIED (GEO title/summary); in vivo, not comparable to in-vitro 24 h |
| [GSE267346](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE267346) (2026-10-23) | LNCaP, VCaP and LuCaP-147 **xenografts** | castration, enzalutamide, TRIM24 degrader | 17 samples | No | VERIFIED (GEO) |
| [GSE311521](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE311521) | 60 pooled lines across 20 cancer types (prostate membership not checked) | baseline atlas (no drug stated) | — | — | VERIFIED summary only |

GEO searches used E-utilities (`db=gds`, GSE, Homo sapiens). Query families were: prostate × single-cell × prostate line names × treatment (2022–2026, 63 hits); prostate × single-cell × DNMT/HDAC/EZH2 drug names (5 hits); and pooled/hashed single-cell × drug × prostate (9 hits). **No 2023–2026 GEO series was found with prostate cell lines in vitro treated with decitabine, azacitidine, entinostat, vorinostat or tazemetostat and profiled by scRNA-seq (VERIFIED negative for these queries, not exhaustive).** The only EZH2-inhibitor hit is the PDX series GSE325232.

### 4.2 MIX-seq detail (Supplementary Tables 1–3, figshare v3)

| Expt | Pool size | Conditions (h) | Cells recovered | Prostate lines in pool |
|---|---|---|---|---|
| 1 | 24 | Untreated 6; DMSO 6, 24; Bortezomib 6, 24; Idasanutlin 6, 24; Trametinib 6, 24 | 2,056–3,097 per condition | LNCaP |
| 2 | 50 | sgLACZ, sgOR2J2, sgGPX4-1/-2 (72/96 h, genetic) | 6,517–7,567 | none |
| 3 | 99 | DMSO 6, 24; BRD3379 6, 24; Dabrafenib 24; Navitoclax 24; Trametinib 24 | 6,887–12,814 | LNCaP, PC3, 22Rv1 |
| 5 | 24 | Trametinib/DMSO time course 3, 6, 12, 24, 48 | 20,028 total | LNCaP |
| 10 | 98 | DMSO, Everolimus, Afatinib, Taselisib, AZD5991, JQ1, Gemcitabine, Trametinib, Prexasertib (all 24) | 2,093–7,098 | LNCaP |

Doses from Supp. Table 3 (µM): idasanutlin 2.5, bortezomib 2.5, navitoclax 5, BRD-3379 10, dabrafenib 0.1, everolimus 10, afatinib 0.5, prexasertib 1, taselisib 1, AZD5991 2, JQ1 2.5, gemcitabine 0.1, trametinib 0.1.

Overlap with the Tahoe vocabulary (VERIFIED by name): Trametinib, Bortezomib, Dabrafenib, Everolimus, Afatinib and Gemcitabine are in Tahoe. The Tahoe doses are 0.05/0.5/5 µM, and **none equals the MIX-seq dose** for these drugs, except that the 0.5 µM afatinib dose matches the Tahoe 0.5 µM label. That match was observed in the tables but not further verified as an analysis unit. Idasanutlin, navitoclax, prexasertib, taselisib, AZD5991, JQ1 and BRD-3379 are not in Tahoe.

**Data note (UNVERIFIED discrepancy):** MIX-seq Supp. Table 1 lists `LNCAPCLONEFGC_PROSTATE` with DepMap ID `ACH-000510`, while the Tahoe `cell_line_metadata` assigns `ACH-000510` to NCI-H1299. The correct ID must be resolved against Cellosaurus/DepMap before any cross-dataset join.

## 5. Other chemical/virtual-cell models with downloadable checkpoints

| Model | Predicts chemical perturbations? | Drug representation (can it represent unseen drugs?) | Training data | Checkpoint availability | Licence | Status |
|---|---|---|---|---|---|---|
| **State ST-Tahoe** (Arc) | yes | one-hot over 1,138 `drug@dose` labels. **No unseen drugs or doses.** | Tahoe-100M | HF, ~1.07 GB per ckpt | code CC BY-NC-SA 4.0; weights Arc non-commercial | VERIFIED |
| **Tahoe-x1** ([HF](https://huggingface.co/tahoebio/Tahoe-x1) `d218a580`, 2025-10-24; [GitHub](https://github.com/tahoebio/tahoe-x1)) | Card lists "Perturbation Prediction" as a benchmark task; the released interface is cell/gene **embeddings** (MLM transformer, 70M/1B/3B) | no drug token in the released inference interface (UNVERIFIED whether a drug-conditioned head exists) | 266 M cells (CellxGene, scBaseCamp, Tahoe-100M) | yes, HF safetensors | Apache-2.0 | VERIFIED card |
| **Rhaister** ([HF](https://huggingface.co/tahoebio/Rhaister) `75fed20a`, 2026-06-15; preprint doi:10.64898/2026.06.09.731197) | yes, on summary statistics (log2FC, MWU p, deltas) | an unseen perturbation is expressed as a linear combination of **observed panel perturbations** (fewshot). Rhaister-O (zeroshot) predicts unseen **cell lines** from DMSO baseline: y = β(p,g) + γ(p,g)·x(c*,g). Not an unseen-drug model. | Tahoe-100M (card says "384 drugs × 3 doses"), Parse PBMC, Replogle-Nadig, Emerald Bay, PRISM | code + config on HF; trains in seconds | Apache-2.0 | VERIFIED card; performance claims (reports beating STATE) UNVERIFIED |
| **CellFlow** ([GitHub theislab/CellFlow](https://github.com/theislab/CellFlow), MIT; v0.0.9 2026-04-08; preprint doi:10.1101/2025.04.11.648220) | yes (single and combinatorial drugs) | user-supplied embeddings; the combosciplex tutorial uses **molecular fingerprints from SMILES**, so it can represent unseen drugs | user-trained (tutorials: combo-sci-Plex, PBMC, zebrafish, iNeuron) | **no pretrained checkpoint found** (no theislab HF CellFlow model; none in repo tree) | MIT | VERIFIED repo; "no checkpoint" = not found |
| **chemCPA** ([GitHub](https://github.com/theislab/chemCPA), MIT; last push 2025-02-06) | yes | SMILES-based molecular encoders (RDKit and others), designed for unseen drugs | sci-Plex3 + LINCS (paper) | `chemCPA_models.zip` on Backblaze, HTTP 200, 254 MB (not downloaded) | MIT | VERIFIED link and licence |
| **CPA** ([GitHub](https://github.com/theislab/cpa), BSD-3; `cpa-tools`) | yes (drug, dose, combinations) | learned drug embeddings (categorical by default). README offers a tutorial using **external embeddings** for unseen drugs. | user-trained; tutorials on combo-sci-Plex | "Datasets and Pre-trained models" on Google Drive (not opened) | BSD-3-Clause | VERIFIED README; checkpoint contents UNVERIFIED |
| **PRnet** ([GitHub](https://github.com/Perturbation-Response-Prediction/PRnet), Apache-2.0) | yes | SMILES-based, designed for novel compounds | LINCS L1000 and sci-Plex (scripts `train_lincs.py`, `train_sciplex.py`) | weights at `prnet.drai.cn` (README: "temporarily unavailable"; HEAD returned 200 with empty body). [Zenodo 10.5281/zenodo.14230870](https://zenodo.org/records/14230870) holds **data only** (Sci_Plex.h5ad 333 MB, Lincs_L1000.h5ad 3.65 GB). | Apache-2.0 (code); Zenodo CC BY 4.0 | VERIFIED; weight availability UNVERIFIED |
| **biolord** ([GitHub](https://github.com/nitzanlab/biolord), BSD-3) | general attribute disentanglement; sci-Plex use in paper | known attributes as categorical/ordered; drug-embedding use not verified here | user-trained | no pretrained checkpoint in README | BSD-3-Clause | VERIFIED README; drug handling UNVERIFIED |
| **scGPT** ([GitHub](https://github.com/bowang-lab/scGPT), MIT) | perturbation tutorial (`tutorials/Tutorial_Perturbation.ipynb`) is GEARS-style **genetic**; no chemical head verified | — | 33 M human cells (whole-human checkpoint) | Google Drive checkpoints | MIT | VERIFIED repo; chemical capability: none found |
| **GEARS** ([GitHub](https://github.com/snap-stanford/GEARS), MIT) | **genetic only** ("single and multi-gene perturbations") | gene graph | Perturb-seq | `load_pretrained` in README | MIT | VERIFIED |
| Arc `Stack-Large` (2026-06) | in-context foundation model; card shows embedding only | — | scBaseCount ~150 M cells | HF | non-commercial | VERIFIED card; drug use UNVERIFIED |

## 6. Implications for the Paper D specification

All points below are evidence-based. They are recommendations, not user decisions.

- **Comparator definition.** For any prostate line, State Tahoe makes a zero-shot cell-line extrapolation, the same task family as the released zeroshot split, applied to a tissue absent from training. The "same drug's mean response in other training lines" baseline is computable directly from Tahoe for any of the 379 drugs. Rhaister-O is a published, open (Apache-2.0) stronger version of this baseline and should be named as a secondary comparator or at least discussed.
- **Test-data compatibility.** No public prostate single-cell dataset matches Tahoe's drug, dose and 24 h triplets for DNMT/HDAC/EZH2 inhibitors. The best-matched candidates are:
  - MIX-seq LNCaP/PC3/22Rv1 at 24 h for trametinib (0.1 µM vs Tahoe 0.05/0.5), dabrafenib (0.1), gemcitabine (0.1), everolimus (10), afatinib (0.5) and bortezomib (2.5). These are dose-mismatched except possibly afatinib 0.5 µM.
  - GSE306429 PC3 at 24 h, including decitabine 1.0 µM (Tahoe has 0.5 and 5.0 µM). The full PC3 compound and dose list must be extracted before the spec can fix test units.
- **Blocking items before preregistration:**
  1. Recover the exact ordered 2,000-gene HVG list of ST-HVG-Tahoe, or use ST-SE-Tahoe with SE-600M embeddings and settle the decoder gene space.
  2. Decide how to map off-vocabulary doses (nearest label vs exclusion). Exclusion is the conservative rule.
  3. Extract the GSE306429 PC3 compound × dose table from a sub-50 MB source, or justify downloading the 1.76 GB limma table.
  4. Resolve the LNCaP DepMap ID discrepancy.
  5. The State inference fallback for unknown labels (see `D_virtual_benchmark.md` §2) still applies at HEAD `9bbfe78`, unchanged since the earlier audit.
- **Licensing.** State outputs are "Output" under a non-commercial licence. A thesis is compatible as a non-commercial purpose. Redistributing predictions requires carrying the licence notice. Tahoe-100M is CC0 and EmeraldBay is CC BY 4.0. MIX-seq is CC BY 4.0.

## 7. Not verified in this session

- State preprint text on Tahoe preprocessing and split design (bioRxiv returned HTTP 429).
- Contents of the State `data_module.torch` (1.9 KB; not parsed).
- The full GSE306429 compound list and PC3-specific doses.
- MIX-seq per-line cell counts for prostate lines (needs `classifications.csv` inside the 20–290 MB zips).
- CPA and scGPT Google-Drive checkpoint contents; PRnet weight download.
- Exposure duration for GSE251977.
- Whether the 60-line pool in GSE311521 contains prostate lines.
