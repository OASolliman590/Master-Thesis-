# Research Notes: ICI Discovery + Immune-State Interpretation to PRAD Epigenetic Validation (v1)

## Purpose

Capture locked design decisions for the v1 thesis architecture before implementation.

## Locked Workstream Design

### Workstream A: Discovery

1. discovery cohort retrieval and intake
2. primary-source all-cancer cohort promotion audit
3. within-cohort DE and cross-cohort meta-analysis
4. signature freeze

### Workstream B: Immune-State Interpretation

1. ESTIMATE global context scoring
2. CIBERSORTx cell-composition scoring (absolute + relative)
3. ssGSEA immune-program scoring from frozen panel
4. HOPE A/B/C/D plus HOPE-18 overlay
5. marker correlations and cohort-level effects

### Workstream C: Mechanistic Validation

1. held-out signature validation without refit
2. PRAD/LUAD barcode-level GDC sample map
3. frozen-signature projection
4. TCIA IPS secondary annotation overlay
5. promoter methylation integration and candidate ranking

`PRE_RESPONSE` remains the primary discovery axis.

## Design Decisions

### Decision 1: Discovery source authority

- **Decision**: discovery inference remains cohort-first DE then meta-analysis from accession-resolved cohorts only.
- **Why**: preserves statistical validity and reproducibility.

### Decision 2: Immune-state layer role

- **Decision**: immune-state methods are interpretation modules downstream of signature freeze, not replacement discovery engines.
- **Why**: they are complementary views from the same transcriptome and should not supplant primary DE/meta inference.

### Decision 3: Method stack

- **Decision**: v1 method set is ESTIMATE + CIBERSORTx + ssGSEA + HOPE/HOPE-18.
- **Why**: provides global context, cellular composition, pathway activity, and interpretable immune typing.

### Decision 3A: Immune scoring must be gene-set driven, no proxies

- **Decision**: ssGSEA must be run against cohort-specific GMT gene sets (explicit registry); HOPE/HOPE-18 only computed when required gene sets are present; no proxy or placeholder scores are permitted.
- **Why**: immune-state outputs must be biologically anchored and reproducible with auditable gene-set provenance.

### Decision 4: Continuous-first policy

- **Decision**: continuous score models are primary; median/quartile splits are sensitivity-only outputs.
- **Why**: avoids information loss and unstable threshold-driven inference.

### Decision 5: TCIA role

- **Decision**: TCIA IPS is secondary annotation for TCGA records, not independent validation.
- **Why**: TCIA annotations are built on TCGA space and should be treated as supportive context.

### Decision 6: RNA eligibility guard

- **Decision**: immune-state modules run on RNA cohorts only; methylation-only cohorts are excluded with logged reasons.
- **Why**: prevents modality misuse and silent methodological drift.

### Decision 7: Non-standard cohort routing

- **Decision**: cohorts that are treatment-exposed but not valid responder/timing cohorts are routed to explicit special-method tracks instead of being squeezed into `PRE_RESPONSE`.
- **Why**: preserves biological value while preventing false discovery contrasts.

Locked examples for v1 development:

- `gse135222_srp217040_nsclc_pdl1`
  - role: comparative multi-omics NSCLC
  - data: RNA-seq (`GSE135222`) + linked methylation array (`GSE119144`)
  - method: expression-methylation integration, pathway concordance, immune-evasion program coupling
  - not a primary response cohort

- `gse202069_hcc_anti_pd1`
  - role: mixed HCC tumor-versus-adjacent cohort with a treated subset embedded inside
  - data: full tumor + adjacent RNA-seq series, plus a clinically treated anti-PD1 subset
  - method: full-series tumor-vs-adjacent analysis first, treated-subset extraction second
  - not a primary response cohort until the treated subset is explicitly curated

## GitHub MCP Archetype Scan (2026-03-21)

- `nf-core/fetchngs`: retrieval patterns for GEO/SRA/ENA accession-driven intake.
- `saketkc/pysradb`: accession crosswalk and metadata resolution commands.
- `seandavi/GEOquery`: processed GEO matrix retrieval patterns.
- `ncbi/sra-tools`: fallback read retrieval (`prefetch` and `fasterq-dump`).
- `nf-core/rnaseq`: stage boundaries and QC discipline for RNA-seq.
- `snakemake-workflows/rna-seq-star-deseq2`: practical DE workflow decomposition.
- `csoneson/ARMOR`: compact reproducible RNA-seq workflow architecture.
- `cran/metaRNASeq`: sensitivity meta-analysis method.

## Methods and Primary References (NCBI PubMed MCP)

Primary method citations used in the v1 pipeline:

- DESeq2 (RNA-seq differential expression): Love et al. Genome Biol 2014. PMID 25516281.
- edgeR (RNA-seq differential expression): Robinson et al. Bioinformatics 2010. PMID 19910308.
- GSVA / ssGSEA (gene set scoring): Hänzelmann et al. BMC Bioinformatics 2013. PMID 23323831.
- ESTIMATE (tumor purity/immune/stromal scores): Yoshihara et al. Nat Commun 2013. PMID 24113773.
- CIBERSORT (immune cell deconvolution): Newman et al. Nat Methods 2015. PMID 25822800.

These are the scientific anchors for the concrete DE and immune-state computations.

## GitHub MCP Code Reference Scan (2026-03-23)

Implementation-style references for DE workflows:

- Example DESeq2 scripts: `icbi-lab/luca` (`bin/run_deseq2.R`), `bioinformatics-core-shared-training/cruk-summer-school-2020` (`liveScripts/deseq2.R`).
- Example edgeR scripts: `vari-bbc/bbcRNA` (`R/edger_methods.R`).

These repositories were used to sanity-check typical DESeq2/edgeR pipeline structure and parameters.

## Non-Goals for v1

- replacing discovery statistics with third-party precomputed web outputs
- using immune-state scores as a replacement for DE/meta discovery
- treating dichotomized score groups as primary inference
- treating TCIA IPS as independent validation cohort evidence
- pooling PRAD/LUAD into discovery matrix for re-discovery
- refitting signatures on validation cohorts
- combining incompatible normalized and raw-count scales silently
