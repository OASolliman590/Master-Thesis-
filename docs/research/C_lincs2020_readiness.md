# Paper C — LINCS2020 metadata and local scoring readiness

Audit date: 5 September 2026. Status: **complete signature-metadata scan; no expression scoring or biological result**. This supports the restored Paper C architecture. It does not replace its patient signature, immune-context or pharmacology layers.

## Decision supported by these data

Proceed with a **condition-specific, compound-level reversal design**. All three thesis compounds have measured PC3/24-hour signatures at exactly 1.11111, 3.33333 and 10 micromolar. A broad DNMTi-versus-HDACi-versus-EZH2i superiority endpoint is not currently justified: mechanism labels need correction, BRD IDs require structure deduplication, model/time coverage is very unequal, and the three-drug comparison is confounded by experimental project. A fixed anchor can support a descriptive connectivity estimate for each compound; it does not create a randomized comparison or establish clinical exposure feasibility. These are design inferences from the metadata below, not frozen endpoints.

## Verified source and execution contract

The official [December 2020 release README](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/README.txt) describes an expansion of the 2017 release and identifies signature metadata, instance metadata, field definitions, separate matrices by level/perturbation type, and a public BigQuery dataset. It calls the release beta and allows later corrections. The actual accessible signature object is [siginfo_beta.txt](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/siginfo_beta.txt). Its directory listing and a guessed `.gz` alternative returned403; that does not prove the compressed object does not exist. `Accept-Encoding: gzip` did not produce compressed transfer.

HEAD established 465,242,319 bytes, Last-Modified `2021-12-07 13:24:26 GMT`, version `IdjZYad8vgq4Fste7egTLfio9nCf9bkI`, ETag `f1f854d7675f5dfd0a3ae3664640f70e-28`. The orchestrator explicitly raised this task's metadata allowance from200MB to500MB for this object. One full stream on AIU completed with strict byte-count/EOF verification:

| Measure | Observed |
|---|---:|
| Signature rows, excluding header | 1,201,944 |
| Exact `pert_type=trt_cp` rows | 720,216 |
| Bytes streamed | 465,242,319 |
| Runtime, including HEAD/read/filter/hash | 103.17 seconds |
| Start UTC | 2026-09-05T20:27:41.556716+00:00 |
| Full object SHA256 | `1a38d7ea2a804be79804af4a27aff9f2537af8f13d3c8af1fdc1fef780f40201` |
| Retained prostate-context or thesis-compound rows | 186,415 |
| Compressed retained file | 14,027,667 bytes |

No full metadata file was retained. No expression matrix, raw sequencing data or model weights were downloaded. The analysis ran at `/home/omics/projects/ici_thesis_pipeline/planning/2026-09-05/C_lincs2020_readiness` using the existing omics-py Python. The local evidence is in [C_lincs2020_readiness](./C_lincs2020_readiness/); `audit_summary.json` records response headers, complete state, counts and SHA; `run.log` records intermediate transfer counts. `audit_siginfo.py` reproduces the full metadata stream when placed alongside the already cached public compound dictionary and 2017 PhaseII signature metadata. Repeating it incurs the same465MB transfer; the retained-row recount scripts need no network. Existing local/SSH credentials were used only by approved connection machinery and must never be printed, copied into this evidence, or placed in delegation briefs.

## Actual prostate chemical coverage

These are rows in the complete signature file, not cell-dictionary membership or independent experiments. Exact curated `cell_iname` labels were used; RWPE1 and LHSAR were kept as explicit contextual labels without assuming malignant identity.

| Cell label | Chemical signature rows | Three-drug coverage |
|---|---:|---|
| PC3 | 55,253 | All three |
| VCAP | 35,442 | Decitabine, entinostat; most relevant entries fail QC |
| 22RV1 | 2,145 | Decitabine, entinostat; single-instance signatures |
| LNCAP | 1,094 | Entinostat; single-instance signatures |
| DU145 | 24 | None of the three |
| RWPE1, LHSAR | 0 | None |

Across all cell contexts, exact compound IDs have988 entinostat,542 decitabine and134 tazemetostat chemical signature rows. Tazemetostat is `BRD-K11215326`, **E-7438** in `cmap_name`; the prior [identity audit](./C_pharmacology_contracts.md) verified its dictionary InChIKey against ChEMBL3414621. Entinostat is `BRD-K77908580`; decitabine `BRD-K79254416`. Counts come from the full [original signature object](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/siginfo_beta.txt), joined to the [original compound dictionary](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/compoundinfo_beta.txt).

| Compound / context | Hours | Total / QC-pass / HIQ signatures |
|---|---:|---:|
| Decitabine / PC3 | 24 | 25 /24 /19 |
| Decitabine / PC3 | 6 | 2 /2 /0 |
| Decitabine /22RV1 | 24 | 3 /3 /0 |
| Decitabine /VCAP | 24;6 | 1 /0 /0 at each time |
| Entinostat /PC3 | 24 | 37 /32 /26 |
| Entinostat /PC3 | 6 | 11 /11 /7 |
| Entinostat /22RV1 | 24 | 2 /2 /0 |
| Entinostat /LNCAP | 24 | 3 /3 /0 |
| Entinostat /VCAP | 24 | 2 /0 /0 |
| Entinostat /VCAP | 6 | 2 /1 /1 |
| Tazemetostat /PC3 | 24 | 3 /3 /1 |

`epi_prostate_dose_time_qc.tsv` supplies the complete compound×line×exact dose×duration×QC×replicate-count grid for the initial panel. `thesis_anchor_summary.json` supplies all thesis contexts, dose sets and exact anchor IDs. For these three drugs there are no prostate durations beyond6/24h; tazemetostat has only24h. Absence in this complete release is observed coverage absence, not biological inactivity.

## Shared anchor and independent-unit limitations

All rows below pass `qc_pass`; doses are exact `pert_dose` values in uM, not rounded `pert_idose` matches.

| PC3/24h dose | Decitabine: signatures /HIQ /distinct instances | Entinostat | Tazemetostat |
|---|---:|---:|---:|
| 1.11111uM | 2 /2 /5 | 1 /1 /2 | 1 /0 /3 |
| 3.33333uM | 2 /2 /5 | 1 /1 /2 | 1 /0 /3 |
| 10uM | 4 /2 /11 | 6 /5 /18 | 1 /1 /3 |

There is no repeated `distil_id` within any compound×anchor group. But a Level5 signature is already a weighted aggregate, and individual well/profile identifiers do not certify independently cultured biological replicates. At1.11111uM, decitabine is `REP.A022_PC3_24H:B21` plus `PBIOA022_PC3_24H:O09`; entinostat `REP.A022_PC3_24H:A21`; tazemetostat `MOAR005_PC3_24H:E15`. Tazemetostat remains confined to MOAR005 at all three anchors; the other drugs use different projects even at10uM. Thus exposure matching leaves project confounding, and a random project effect cannot repair a wholly absent drug×project crossing.

**Proposal:** select the primary exposure rule using metadata and pharmacological rationale before reading expression results. Lowest shared QC-pass dose1.11111uM avoids selecting the strongest observed response but is not established as clinically achievable or biologically optimal.10uM is the only anchor with HIQ coverage for all three, but selecting it because of HIQ can favor detectable transcriptional activity. Report each drug's raw connectivity at the frozen condition, retain all QC-pass signatures with their project/instance provenance, and use other doses as predeclared sensitivity analyses. Do not bootstrap three wells as three independent studies or estimate a stable drug-specific between-experiment variance from one tazemetostat signature.

## QC semantics and class identifiability

The [official field-definition workbook](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/LINCS2020%20Release%20Metadata%20Field%20Definitions.xlsx), cached with SHA in `methods_manifest.json`, defines `nsample` as contributing Level4 profiles; `wt` gives their collapse weights; `cc_q75` measures replicate correlation in landmark space. Signature `qc_pass` means at least half its profiles pass processing QC. `is_hiq` additionally requires a replicate-recall rank threshold; it is explicitly technical **and functional** quality. `tas` combines signal strength and replicate correlation. Therefore HIQ/TAS cannot be described as purely technical exclusions. The workbook has apparent swapped prose for numeric `pert_time` versus string `pert_itime`; preserve actual typed fields, units and the documented discrepancy.

The initial panel uses exact dictionary MOA labels `DNA methyltransferase inhibitor` and `HDAC inhibitor`, plus explicitly sourced tazemetostat. It contains42BRD IDs. A retained-row supplement adds EI1 (`BRD-K91535048`, EI-1 alias), whose EZH2 mechanism is established by [Qi et al.2012](https://doi.org/10.1073/pnas.1210371110). EI1 has three PC3/24h QC-pass, non-HIQ rows at1.11111,3.33333,10uM. Its name/alias mapping is verified in LINCS; an external structure cross-check remains pending. The resulting43-ID panel is a **coverage probe**, not an exhaustive or mechanism-validated epigenetic compound universe.

| Raw annotation /context | Distinct BRD IDs | Signatures /QC-pass /HIQ |
|---|---:|---:|
| DNMTi /PC3 /24h | 8 | 90 /82 /36 |
| HDACi /PC3 /24h | 28 | 502 /359 /243 |
| Tazemetostat +EI1 /PC3 /24h | 2 | 6 /6 /1 |
| DNMTi /VCAP /24h | 6 | 13 /7 /2 |
| HDACi /VCAP /24h | 21 | 124 /76 /49 |

Crucially, the dictionary's DNMT label includes **BIX-01294**, whereas its original mechanism study identifies G9a histone methyltransferase inhibition. It also contains three azacitidine BRD IDs and two zebularine IDs. None should automatically count as independent class members. [BIX-01294 primary study](https://doi.org/10.1016/j.molcel.2007.01.017). The dictionary contains no nonempty target string including EZH, so searching that field alone misses known EZH2 compounds. Complete EZH2 discovery via structures/aliases remains unknown. `epi_panel_supplemented.json` preserves raw labels and explicit curation warnings rather than rewriting source data.

**Design consequence:** freeze curated structures, direct versus indirect mechanisms, multi-target membership, dose-unit rules and eligible condition blocks before a class analysis. Compound is the independent unit for class generalization; signatures/doses are repeated observations. With two currently found EZH2 compounds in one line/time and few projects, a three-class mixed model would not support broad biological superiority. Missing72h exposures cannot be fixed by a random dose/time term. Class patterns may be descriptive or conditional secondary analyses after curation; a negative24h DNMTi score cannot be generalized to adequately timed demethylation.

## Cross-release overlap

The complete2020 scan was compared with the cached [GSE70138 PhaseII2017 signature metadata](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz):118,050 rows and346,333 distinct instance IDs. Of those old signature IDs,112,188 recur in2020;81,445 have exactly the same instance set.292,419 old instance IDs recur across112,5722020 rows. This is direct experimental overlap, independent of changed signature names or reprocessing. Neither phase can serve as independent validation of the other without instance-level exclusion. Exact PhaseI overlap remains **unmeasured**.

Within the retained2020 prostate chemical subset,93,958 signature rows contain292,435 distinct instance IDs and no instance reused across those chemical rows. The broader retained subset includes genetic/consensus/control entries and does contain repeated instances; its duplication count must not be attributed to chemical signatures. Equal instance membership does not prove equal numeric expression after release reprocessing; no matrices were compared.

## Exact local scoring recommendation

Use the official **cmapM2.0.0-era QueryL1k source**, pinned to inspected commit `8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c`, as the reference implementation for parity. This is a source recommendation pending runtime validation, not a claim that it is installed or tested. [Pinned repository](https://github.com/cmap/cmapM/tree/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c). MATLAB requires the Statistics Toolbox; the official [Docker workflow](https://cmap.github.io/cmap-sig-tools/docker_demo/) supplies compiled SigTools without a commercial MATLAB license. AIU exposes Docker on PATH; no MATLAB/Octave was found on PATH. No image was pulled, daemon access tested, digest pinned or scoring job executed.

The inspected argument file declares `--metric wtcs`, `--es_tail both`, `--up`, `--down`, `--score`, `--rank`, `--sig_meta`, `--ncs_group`, and `--max_col`. Score and rank matrices must have identical IDs and ranks derived from the fixed full feature universe; subset-only reranking changes the statistic. The actual call path is `runCmapQuery → computeCmapScore → cmapScoreCore → fastESCore → getCombinedES`. `fastESCore` uses absolute expression weights, and combined bidirectional scores require opposed directions. Do not select the similarly named standalone `fastWTCSCore` without review: that inspected file has an undefined `exmax` reference and is not the demonstrated call path. [Pinned source tree](https://github.com/cmap/cmapM/tree/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c/sig_tools/%2Bmortar/%2Bcompute/%40Connectivity).

WTCS is raw signed connectivity; for a **disease-oriented** query, more-negative values indicate reversal. Negating it for a positive restoration display must be explicit. QueryL1k then calculates signed-mean `norm_cs` using `is_ncs_sig`, and FDR relative to `is_null_sig`. Its default `ncs_group` is empty/global. Missing normalization/null flags may fall back to all signatures, and normalization NaNs may become zero: a production adapter must reject missing reference flags, empty reference strata and invalid normalization rather than accept these fallbacks. The metadata places `sig_id` mid-table, while the documented input expects it first; construct a validated adapter. [Official QueryL1k demo and output semantics](https://github.com/cmap/cmapM/blob/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c/docs/SigToolDemo.md).

The retained PC3 metadata has47,230 chemical signatures flagged for normalization and2,448 vehicle controls flagged for normalization/null. Reference matrices have not been accessed. Restricting input to epigenetic hits alone changes normalization and removes the intended background; a matched-control/reference manifest is needed. `PC3_reference_flags.json` records actual flags, not proof of batch-matched null availability.

**Tau is not WTCS, normalized WTCS, FDR, or an empirical gene-permutation percentile.** Historical CLUE tau uses a reference distribution of normalized scores from a query collection. This QueryL1k workflow does not document an automatic tau output. Recommend raw WTCS as the auditable scoring layer and clearly named sensitivity metrics; report tau only if the exact required reference distribution and implementation are independently obtained and frozen. [CLUE analytical-method documentation](https://clue.io/connectopedia/category/Analytical%20Methods). The official [cmapPy repository](https://github.com/cmap/cmapPy) is focused on GCT/GCTX handling and is no longer actively maintained; it is not evidence of a tested WTCS/tau engine. A Python port would require numerical parity against the pinned reference and direction/tie/empty-query/null-stratum fixtures before production use. Two scoring algorithms on the same data are robustness checks, not independent biological validation.

## Fact-versus-design question ledger and readiness gates

| Question | Factual answer /unknown | Proposed specification impact |
|---|---|---|
| Are all three measured in prostate? | Yes, PC3/24h at three exact shared doses; no shared second line | Primary context can be PC3; broader lines secondary |
| Which shared dose is valid? | All three doses have processing-QC coverage;10uM alone has HIQ for all | Select by exposure rationale before expression, not favorable results |
| Can the three drugs be fairly compared? | Dose/time match; tazemetostat remains project-confounded and singly aggregated | Condition-specific estimates; no causal superiority claim |
| Is a DNMT/HDAC/EZH2 class endpoint ready? | No; raw labels include mechanism errors/duplicate names and missing EZH2 annotations | Curate first; retain descriptive or conditional class analysis |
| Can2017 validate2020? | Extensive exact instance overlap verified | Release sensitivity only unless disjoint instances are demonstrated |
| Is the scoring tool ready? | Pinned official code/options inspected; runtime/parity untested | Feasible implementation ticket, execution gate remains open |
| Can tau be promised? | Required historical reference collection not obtained | Do not label WTCS/permutation quantiles tau |
| Can immune priming be concluded? | No expression or immune-context results assessed here | Preserve C's orthogonal validation arms and thesis claim limits |

Before production: curate the complete panel; choose the metadata-based primary exposure rule; freeze the patient signature/gene universe; verify selected Level5 matrix columns and measured-versus-inferred coverage; specify project-aware aggregation and uncertainty; demonstrate independent validation source/instance disjointness; pin the executable/container digest and run reference numerical parity. Promoter association, transcript restoration, functional immune effects and clinical exposure remain separate evidence layers.
