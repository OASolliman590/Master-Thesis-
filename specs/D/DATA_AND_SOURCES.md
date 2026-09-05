# D data and sources

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** Metadata evidence was inspected on 2026-09-05; no matrices, weights or predictions were generated. SOURCE_MANIFEST.json preserves bounded retrieval evidence and its limits.

## Coverage by question

| Question | Candidate source | Verified evidence | Eligible D coverage and gap |
|---|---|---|---|
| Does a chemical predictor exist? | [ST-HVG-Tahoe](https://huggingface.co/arcinstitute/ST-HVG-Tahoe) | Pinned model manifest lists config, checkpoint files and mappings. | Assets exist; downloaded weights, runtime and binary-training lineage are unverified. |
| Can the candidate represent a drug condition? | Pinned vocabulary and config in manifest | 1,138 decoded labels: 379 drug names × three categorical doses plus vehicle. Literal decitabine labels exist; queried entinostat/tazemetostat aliases absent. | Not a structure-level identity audit. Unknown labels are excluded as unsupported, never negative effects. |
| Is a released held-out context prostate? | Pinned zeroshot split | C32, HOP62, HepG2/C3A, Hs 766T and PANC-1 are named test contexts. | **No prostate context is named in that split.** It is reproduction evidence only. |
| Is there independent prostate response ground truth? | [GSE199800](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE199800), [GSE216053](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE216053) | Earlier audit identified prostate bulk perturbation profiles. | Native single-cell input/endpoint compatibility not established; bulk rows cannot be copied into pseudo-cells. |
| Can L1000 serve as the primary test? | [GSE70138 metadata](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz), [gene-space documentation](https://clue.io/connectopedia/pdf/l1000_gene_space) | Earlier audit reports prostate perturbation signatures; L1000 distinguishes measured and inferred features. | Perturbation z-scores are not native per-cell expression. Exact categorical exposure matches and output genes unresolved. External transfer, if justified, is secondary. |
| Is Tahoe a new independent validation source? | [Tahoe resource](https://huggingface.co/datasets/tahoebio/Tahoe-100M) | Author resource and released split are present. | Tahoe trains the candidate transition model. Arbitrary reused rows are not external validation. Viewer metadata are partial, not a complete eligible-cohort manifest. |
| Can controls/replicates/training effects be audited? | Selected test study and checkpoint training rows | No complete joined manifest acquired. | **Unknown; blocking**. Baseline expression alone lacks measured response ground truth. |

The canonical antecedent evidence report is [D_virtual_benchmark.md](../../docs/research/D_virtual_benchmark.md); SOURCE_MANIFEST retains original local audit paths for provenance and source URLs for retrieval. Its older LINCS coverage is supplemented by [the complete 2020 audit](../../docs/research/C_lincs2020_readiness.md), which establishes PC3 coverage of all three planned drugs but does not establish native State compatibility. This kit makes no new eligible D patient/cell/condition count claim.

## Representative actual metadata

The pinned config explicitly declares `embed_key=X_hvg`, `pert_rep=onehot`, `pert_col=drugname_drugconc`, `cell_type_key=cell_name`, `batch_col=plate`, `output_space=gene` and `int_counts=false`. It contains no demonstrated duration input. The actual vocabulary contains the literal key `[('Decitabine', 0.5, 'uM')]`; its vehicle key is `[('DMSO_TF', 0.0, 'uM')]`, whereas the saved configuration uses `DMSO_TF`. These are observed metadata differences, not recommended experimental exposures. [Pinned config](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/zeroshot/state_generalization_zeroshot_X_hvg/config.yaml), [vocabulary](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/zeroshot/state_generalization_zeroshot_X_hvg/pert_onehot_map.pt).

The local metadata audit used pickle opcode inspection, not arbitrary object loading. Reinspection must retain this distinction. Dimensions metadata indicate 2,000 input/output features, but the ordered identifiers and transform have not been established; a count is not a feature contract.

## Identity, access and eligibility contract

Preserve source sample/barcode names and add stable internal IDs; never replace source identities with a bare gene symbol or drug label. Compound mapping requires source ID, canonical structure identifier, salt/parent handling, exact serialized vocabulary key and reviewed alias provenance. Numerical dose unit conversion may establish equality only when exact identity and units are documented; no nearest-dose matching or interpolation in the primary task. Collection duration must match the intended compatible task by documented source metadata, even though the model label has no duration input.

The ordered model-output gene list must map unambiguously to measured test features. All declared primary features must be available and finite after the frozen transform; missing features cannot be zero-padded, imputed from test outcomes or replaced with inferred L1000 expression. If the full output list is not measurable, redesign the primary feature estimand through an explicit pre-test amendment. Do not quietly shrink it to favourable immune genes.

Document separate terms for code, checkpoints, source data and derived outputs. State's repository distinguishes code and model licences; audit the selected revision and checkpoint terms rather than assuming software licensing covers weights. [Official licensing](https://github.com/ArcInstitute/state#licenses), [model licence](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/MODEL_LICENSE.md). Exact permissible redistribution remains a gate. Git/Notion store manifests and permitted summaries; large/restricted data stay in authorised AIU storage.

A complete source manifest must eventually enumerate every file actually used, its URL/access route, release, bytes, checksum, terms, source-study ID, processing history and verification state. The present manifest is an **audit-artifact manifest only**. It is not an analysis data manifest.
