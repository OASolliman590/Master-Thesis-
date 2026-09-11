# Paper B exploratory modules and extra data types

**11 September reconciliation:** [IMMUNE_BARRIER_FRAMEWORK.md](IMMUNE_BARRIER_FRAMEWORK.md) supplies the scientific role and MethylCIBERSORT implementation requirements. M0-M6 remain distinct exploratory functions; no automatic composite or promotion to primary predictors. A-derived signatures remain separately versioned. MethylCIBERSORT is a composition sensitivity, not a silent primary purity replacement.

**Amendment date:** 7 September 2026  
**Integrated:** 10 September 2026 as corrected v0.2  
**Status:** proposed, not frozen, not a primary change and not a real-cohort release  
**Decision:** [B_KIT_MODULES_20260907.md](../../docs/decisions/B_KIT_MODULES_20260907.md)  
**Registry:** [gene_set_registry.proposed.json](gene_set_registry.proposed.json) and [schema](gene_set_registry.schema.json)  
**Prior scope:** [SECONDARY_PROGRAMS.md](SECONDARY_PROGRAMS.md) and [source review](../../docs/research/B_SECONDARY_GENE_SET_PANEL.md)

This amendment places the requested mobility, mimicry, exclusion and context modules inside the existing B-P kit. The three planned secondary programs remain proposed until their sources and scoring contracts are frozen. M0-M6 and all extra data types below remain exploratory or sensitivity scope unless a later signed amendment says otherwise.

## Layer rules

| Layer | Programs | Predictor X | Cohorts | CPC outcome may select membership? |
|---|---|---|---|---|
| Primary | Proposed eight-gene `P` | Candidate eight promoter means of `P` only | TCGA-PRAD development; CPC-GENE no-refit test after freeze | No |
| Planned secondary | Ayers GEP-18; official Hallmark IFN-gamma; HOPE_18 | Same primary X unless separately amended before outcome access | Matched eligible populations; all fitting in TCGA | No |
| Exploratory | M0-M6 | Registry-only by default; optional M1 promoter candidates remain out | TCGA-PRAD context; qualified LUAD secondary | No |
| Excluded | Historical PAN ICI lists; Hallmark minis; unlabeled custom averages | CPC-selected probes | Pan-cancer hot/cold as B-P test | N/A |

Do not merge M0-M6 into an all-positive immune-activation score or promote the best exploratory result after inspecting CPC-GENE.

## Primary proposal, unchanged but unfrozen

`P`: `HLA-A HLA-B HLA-C B2M TAP1 TAP2 PSMB8 PSMB9`

This amendment neither alters nor freezes membership, signs, measurement mappings or predictors. Do not add `NLRC5`, `TAPBP`, `IRF1`, `STAT1`, chemokines, cytotoxic markers or any M0-M6 member to `P` without a recorded amendment made before CPC outcome access.

## Planned secondary programs

- Ayers GEP-18 membership was recovered. Its published score is weighted and signed, including negative `CD276`; the raw coefficient and normalization contract is not yet pinned. A membership-only adaptation must be renamed and exploratory.
- `HALLMARK_INTERFERON_GAMMA_RESPONSE` means the official 200-gene MSigDB collection from a pinned release, never the local 10-gene mini. Its membership is deliberately null in v0.2 until official source bytes are retained and hashed.
- HOPE_18 membership was recovered from a prognosis study. Study survival directions do not automatically define immune-activation signs or validated score weights; it is not an ICI-response signature.

## Exploratory modules admitted by this amendment

Symbols are raw proposed tokens. B-G1 applies the registry's pinned alias rules, reports mappings and coverage, and never invents directions or weights.

### M0 extra antigen presentation

Context around tumour visibility, not part of primary `P`:

`NLRC5 CIITA TAPBP CALR CANX PDIA3 IRF1 STAT1 HLA-E HLA-F HLA-G HLA-DRA HLA-DRB1 HLA-DPA1 HLA-DPB1 PSMB10`

`TAPBP` is distinct from `TAPBPL`. If a source supplies `TAPBPR`, canonicalize it to `TAPBPL`, never to `TAPBP`.

### M1 mobility and trafficking

Registry-only until source, direction and scoring rules are frozen:

`CXCL9 CXCL10 CXCL11 CXCR3 CCL5 CCR5 CXCR6 CXCL13 CXCR5 ICAM1 VCAM1 SELP SELE ITGAL ITGB2 ITGA4 ITGB1 SELL`

Candidate promoter loci `CXCL9 CXCL10 CXCL11 CXCR3 CCL5 ICAM1` remain out of primary X. Adding them requires a separate pre-outcome amendment.

### M2 T-cell and cytotoxicity context

Bulk infiltrate/effector context, not an independent tumour-cell silencing test:

`CD8A CD8B CD3D CD3E CD3G NKG7 GZMA GZMB GZMK PRF1 GNLY IFNG`

### M3 viral mimicry and IFN sensing

Paper C-relevant mechanism context:

`CGAS STING1 DDX58 IFIH1 MAVS IRF3 IRF7 IFNB1 OAS1 OAS2 MX1 ISG15 RSAD2`

Canonicalize `MB21D1 -> CGAS` and `TMEM173 -> STING1`, then deduplicate the canonical locus.

### M4 exclusion and cold stroma

An opposing/context program; retain as its own registry set unless a named composite later freezes its orientation:

`TGFB1 TGFB2 TGFBR1 TGFBR2 SMAD3 CXCL12 CXCR4 FAP ACTA2 COL1A1 COL1A2 LGALS1 VEGFA`

### M5 checkpoint candidates

Candidate checkpoint loci, not a certified approved-drug-target list and not one all-positive score:

`PDCD1 CD274 PDCD1LG2 CTLA4 LAG3 HAVCR2 TIGIT IDO1`

Approved-target status requires a separate table containing drug, regulator, evidence URL/version, approval date, indication, modality, molecular target, canonical gene and cell context. Until that table is reviewed, all members remain candidates.

### M6 epigenetic regulators

Expression context spanning writers, erasers and other regulators; expression is not chromatin activity:

`DNMT1 DNMT3A DNMT3B TET1 TET2 TET3 EZH2 EED SUZ12 HDAC1 HDAC2 HDAC3 KDM6A`

Do not average this program with immune-effector outputs.

## Extra data types proposed as sensitivities

| Data | Alignment key | Proposed use | Claim boundary |
|---|---|---|---|
| Gene-level CNA at `P` and optional module loci | Specimen | Copy-number sensitivity | Not a silent primary covariate; availability/comparability unfrozen |
| Simple mutations or HLA LOH, if source-backed | Specimen | Genetic-invisibility context | Never infer from RNA; source and assay unresolved |
| Thorsson subtype or leukocyte fraction | TCGA case | Expression-derived/integrative immune context | Not orthogonal validation; cannot independently validate the tested expression module |
| MethylCIBERSORT or published methylation fractions | Specimen | Composition sensitivity | Not proof of tumour-cell silencing |
| TCGA-LUAD STAR RNA plus SeSAMe 450K | LUAD case/sample | Qualified lineage secondary | Not a B-P test set; no unmodeled PRAD/LUAD pooling |
| Promoter annotation plus source-backed mask | Probe | Candidate `Q` construction | Never choose with CPC beta or outcomes |
| Detection p-value | Probe/sample | QC beside beta | Never recode missing beta as zero |

These are admissions to future design work, not assertions that data exist, align, pass QC or support inference.

## Scoring and multiplicity

- Primary scoring remains controlled by [ANALYSIS.md](ANALYSIS.md); this amendment does not freeze it.
- Planned secondary programs require their published/official method or an explicitly renamed exploratory adaptation.
- M0-M6 are registry-only in v0.2. No default rank mean, ssGSEA, signs, weights or module score is authorized.
- Any later secondary prediction comparison needs its own matched baseline/extended contract with all fitting in TCGA.
- No CPC-GENE value enters membership, mapping, probe, covariate, scoring or promotion decisions.

## Acceptance before any module scoring

For each program retain source/version and bytes, raw and canonical identifiers, alias rules, frozen-list hash, direction/weights or explicit unweighted status, scoring algorithm, missing/duplicate rule, finite coverage in each authorized universe, overlap with `P`, predictor status, population and multiple-testing family. B-G1 reports this registry and outcome-blind annotation coverage. A missing required annotation produces an explicit incomplete audit; it is not guessed or marked complete. B-I5 may score only a later frozen program that passes its own scientific gates.
