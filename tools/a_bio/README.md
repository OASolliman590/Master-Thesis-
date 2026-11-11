# Paper A A-BIO runner

`python -m tools.a_bio run` runs one of two routes over the existing cohort materialization. The outcome-free route sends each study through `tools.a_bulk` QC, PCA, and panel correlations. The outcomes route composes `tools.a_meta` features, within-study effects, and synthesis with per-study DE and descriptive fgsea from `tools.a_bulk`.

## Reproducible invented run

These commands create a fully invented cohort and run both routes. Set `THESIS_RUNTIME` to the same invented runtime so shared modules do not inspect another runtime. Results and patient-level synthetic tables stay under `.scratch/`.

```sh
python -m tools.a_bio fixture --runtime .scratch/a_bio_demo/runtime --cohort invented_a_bio_demo
THESIS_RUNTIME=.scratch/a_bio_demo/runtime python -m tools.a_bio run \
  --route outcome-free \
  --cohort invented_a_bio_demo \
  --runtime .scratch/a_bio_demo/runtime \
  --synthetic-manifest .scratch/a_bio_demo/runtime/invented_a_bio_demo/simple/manifest.json \
  --results .scratch/a_bio_demo/results
THESIS_RUNTIME=.scratch/a_bio_demo/runtime python -m tools.a_bio run \
  --route outcomes \
  --cohort invented_a_bio_demo \
  --runtime .scratch/a_bio_demo/runtime \
  --synthetic-manifest .scratch/a_bio_demo/runtime/invented_a_bio_demo/simple/manifest.json \
  --results .scratch/a_bio_demo/results
```

The fixture has a small gene universe: all frozen panel genes, the full IFNγ membership, its fixed common-gene subset, and 15 genes from a frozen Reactome set. It hashes each simple materialization output and records explicit invented provenance. Synthetic results are software checks, never biological evidence; pathway coverage for other sets remains unavailable in this demonstration.

## Data and analysis boundaries

- Outcome-free input uses typed cohort metadata and the simple expression/clinical files. It names and projects only identity, drug-class, batch, and biopsy columns, plus GSE176307's explicit `sample_id` assay join key. It verifies the simple-output hashes and patient/expression alignment and does not call the packet-opening cohort validator or open an ingestion packet. Its manifest marks source-input hashes as not revalidated.
- The outcomes route reads only the declared endpoint fields in addition to the named outcome-free covariates. Real outcome routes refuse before clinical or expression access unless a future explicit release is supplied. Adjusted models refuse while the clinical adjustment sets remain unsigned.
- The eight frozen families stay separate: `panel`, `m5m6_gene`, `gene`, `pathway`, `panel_coverage90`, `pathway_coverage90`, `pathway_common`, and `targeted_subset`. Strict coverage is the main analysis; the 90% and common-gene families remain sensitivities. The signed targeted subset remains per-study with no pooling or FDR. Endpoint definitions stay separate; bulk DE projections remove `OTHER_EXCLUDED`, and per-study DE rankings are mapped by the A-META identifier rules before Hallmark/Reactome fgsea. `source_label` remains per-study only. Synthesis preserves the four declared strata and existing low-k rules.
- The post-meta Hallmark/Reactome stage is recorded as pending until the user signs the pooled ranking statistic and tie/missingness rules. The `--meta-ranking-contract-id` and `--meta-ranking-statistic` options exercise that route only on invented fixtures; they do not set a real-data default. Runs without a signed statistic report this stage as unavailable and remain partial.
- `fraction` is unavailable pending the signed quanTIseq pin (N15). CIBERSORTx is not run. Every run keeps unavailable cohorts and families with reasons in its summary tables.

Output is written under `<results>/A/a_bio/<route>/<run_id>/`. The patient-free summary and manifest sit at the run root. The outcomes route also writes family availability, per-unit coverage, endpoint DE/fgsea status, per-study effects, and one synthesis directory for each stratum.

R bridge stages are retained in a hidden sibling work directory by default. Set `--retention-dir` to choose another private location; it must be separate from the public run tree and is excluded from the run manifest.

## Method sources

- The runner reuses the existing [bulk module contract](../a_bulk/README.md), including its DESeq2, limma, and fgsea references and pinned R bridge.
- Singscore: Foroutan M, Bhuva DD, Lyu R, et al. “Single sample scoring of molecular phenotypes.” *BMC Bioinformatics*. 2018;19:404. [Paper](https://doi.org/10.1186/s12859-018-2435-4), [official Bioconductor package documentation](https://bioconductor.org/packages/release/bioc/html/singscore.html).
- Meta-analysis: Viechtbauer W. “Conducting Meta-Analyses in R with the metafor Package.” *Journal of Statistical Software*. 2010;36(3):1–48. [Paper](https://doi.org/10.18637/jss.v036.i03), [official CRAN package documentation](https://cran.r-project.org/web/packages/metafor/index.html).
