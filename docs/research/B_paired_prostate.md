# Paper B: paired prostate evidence and mechanism audit

Audit date: 2026-09-05. Status: public metadata feasibility verified; analysis matrices, QC, covariate completeness and scientific results not yet verified. This note is an evidence input to the spec, not a completed analysis or preregistration.

## Answer that changes the next action

A feasible discovery/external-validation route exists: current GDC metadata identifies **497 TCGA-PRAD primary-tumour cases** with open RNA quantification and 450K methylation, while **210 CPC-GENE patient codes** join GSE107298 methylation to GSE107299 expression. These are pre-QC case/patient-code intersections, not a promise of 497+210 final patients. The older GSE84043 route yields only73 paired codes and is nested in the expanded CPC-GENE route. Use one CPC-GENE validation cohort, not multiple apparently independent GEO accessions. These counts were computed from actual source records, saved below, rather than inferred from publication totals.

## Bounded real-data check

The executable [inspect_metadata.py](B_paired_prostate/inspect_metadata.py) retrieves metadata only using GEO's documented `targ=gsm&view=brief&form=text` interface and the GDC `/files` endpoint with project/data-type filters. It rejects metadata responses above12MB and truncated GDC result pages. No expression or methylation matrices, IDAT archives, sequencing reads or controlled data were downloaded. [GEO documentation](https://www.ncbi.nlm.nih.gov/geo/info/download.html), [GDC API documentation](https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/).

Artifacts:

- [summary.json](B_paired_prostate/summary.json): complete intersections, platform counts and GDC case/sample IDs.
- [CPCG_patient_pairs.tsv](B_paired_prostate/CPCG_patient_pairs.tsv):210 patient-code rows with both modalities' GSMs, expression platform and old-series membership.
- [geo_samples.json](B_paired_prostate/geo_samples.json): parsed source records, titles, characteristics, processing and reanalysis relationships.
- Four `*_sample_metadata.soft` files: original GEO metadata responses.
- [gdc_files.json](B_paired_prostate/gdc_files.json): complete1107-file GDC metadata response.
- [provenance.json](B_paired_prostate/provenance.json): actual request URLs, retrieval time, file sizes and SHA256 hashes.

| Resource/question | Verified records | Distinct unit and overlap | Appropriate role |
|---|---:|---|---|
| TCGA-PRAD RNA |554 open STAR-Counts files|497 primary-tumour cases|Discovery molecular endpoint; not ICI response|
| TCGA-PRAD methylation |553 open SeSAMe 450K beta files|498 primary-tumour cases|Discovery methylation predictors|
| TCGA intersection |501 shared primary-tumour sample IDs|497 shared cases; repeated samples require resolution|Maximum metadata-supported discovery case count|
| GSE83917, methylation subseries of GSE84043 |160 GPL13534 records|104 CPCG patient codes; all overlap GSE107298|Historical provenance;73 have expression in GSE107299|
| GSE84042, expression subseries of GSE84043 |73 records:17 GPL16686,56 GPL17586|73 CPCG codes, all present in GSE107299|Historical provenance, not a second validation cohort|
| GSE107298 expanded methylation |394 GPL13534 records|286 CPCG codes; repeated profiles and explicit reanalysis links|Preferred external methylation source|
| GSE107299 expression |213 records:147 GPL16686,66 GPL17586|213 CPCG codes|Preferred external RNA-abundance source; these are arrays, not RNA-seq|
| GSE107298 × GSE107299 |210 exact CPCG-code pairs|Pre-QC patient-code matches, not verified same tissue aliquots|Preferred external validation cohort|

Source metadata: [GSE84043](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE84043), [GSE83917](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE83917), [GSE84042](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE84042), [GSE107298](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107298), [GSE107299](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299), GDC request archived in provenance.

### Pairing and independence

Join CPC-GENE on exact `CPCG` plus digits extracted from sample titles; retain accession/GSM, original title and all replicate suffixes. Zero records in these four retrieved sets failed that ID extraction. For example, original methylation GSM2221447 (CPCG0099_rep1) explicitly links to reanalysis GSM2863990. Reanalysis does not create a new patient. GSE107298 contains300 records with explicit `Reanalysis` relations; the remainder must still undergo patient-level deduplication. [Original/reanalysis source record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM2863990).

Match TCGA through actual case and sample entities returned by GDC, restricting samples to `Primary Tumor`. Do not count files as patients, combine tumour with normal, or assume all same-case specimens are interchangeable. The501 shared sample IDs belong to497 cases: keep all associations in the manifest and choose a predeclared one-specimen-per-case rule only after portion/aliquot and QC inspection. Do not resolve replicate choice using association strength.

CPC-GENE and TCGA are separate named projects in the inspected records, with different identifier namespaces. That supports external-cohort design but does not establish biological independence solely through unequal strings. Audit publication recruitment/site metadata and known source reuse. Do not use a publication's pooled TCGA+CPC-GENE analysis as an additional independent cohort. Never add GSE83917/GSE84042 to GSE107298/GSE107299 as separate test patients. The originating proteogenomic paper explicitly points to the latter paired accessions. [Author-hosted primary paper](https://escholarship.org/content/qt35z033sq/qt35z033sq.pdf).

## Compatibility and coverage gates

**Methylation:** current GDC results are SeSAMe estimates; CPC-GENE records describe dasen processing. Common450K technology does not remove preprocessing differences. Pin file UUIDs, workflow/release and probe annotation; use a common eligible CpG universe. Avoid pretending current GDC files are the old liftover-format tables: current beta files contain probe IDs and beta values, so promoter coordinates require a separately pinned annotation. A common raw-data reprocessing sensitivity is possible later, subject to access/time, not performed here. [GDC methylation specification](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Methylation_Pipeline/).

**Expression:** CPC-GENE records describe RMA, Entrez custom CDF v18 and author batch adjustment; TCGA is RNA-seq. Archive those author processing choices rather than claim de novo uniform processing. Freeze gene mapping, transcript/probe collapse and a scoring definition valid across platforms. An externally reported R² requires a genuinely comparable endpoint scale; fitting an outcome rescaling/calibration to the held-out cohort changes the validation and must not be hidden. Inspect within-sample gene-rank scoring or a strictly prespecified transport transformation before locking the endpoint. This is a design requirement, not a proven method advantage. [GSE107299](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299).

**Covariates:** source sample metadata includes CPCG tissue, risk group and expression batch, but this audit did not establish complete Gleason, age, gene-level copy number, tumour purity or clinical outcome coverage for the210 pairs. Full covariate availability is a remaining gate for the planned adjusted model. Source papers point to clinical/genomic repositories and supplementary data; controlled raw WGS is unnecessary if suitable public derived covariates exist, but their availability must be checked rather than assumed. [CPC-GENE data-availability statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC8556363/).

**Cell origin:** bulk methylation/expression associations can arise from differing cell proportions. An immune RNA score is a molecular endpoint, not independent proof of tumour-cell silencing or immunotherapy response. Retain purity/composition sensitivity and orthogonal malignant-cell expression evidence. Exact eight-gene program and retained CpGs remain to be checked in downloaded matrices; metadata pairing alone cannot guarantee feature coverage.

## Guo2023: the mandatory counterexample

[Guo et al., Cell2023, DOI10.1016/j.cell.2023.05.028](https://doi.org/10.1016/j.cell.2023.05.028) was checked beyond the title using full text from [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10436379/fullTextXML), saved as `B_paired_prostate/Guo_2023.xml`.

The study identifies early hypomethylated domains containing silenced immune genes, notably CD1A–IFI16. It links suppression to H3K27me3-associated chromatin changes. In BPH-1,5-azacytidine produced demethylation with reduced CD1 expression; GSK126 restored locus genes in22Rv1, LNCaP and VCaP after six days. Ectopic restoration of mouse Cd1d1/Ifi204 suppressed tumour formation in immune-competent models. It is not evidence that decitabine necessarily has the same effect in every malignant prostate context, nor a clinical ICI-response validation.

Implication: a hypermethylated-promoter plus negative-correlation filter captures only one candidate mechanism. Retain positive and negative associations, distinguish promoter loci from domain methylation, and explicitly annotate published PMDs. Do not rename a450K domain proxy as a new whole-genome PMD call. Bidirectional findings and drug-induced suppression must remain reportable. The existing study also narrows novelty: merely showing methylation-associated loss of prostate immune genes or EZH2-mediated restoration is already preceded.

## Evidence-backed grilling ledger

| Question | Factual answer / boundary | Action for specification |
|---|---|---|
| Is actual independent paired external data available? |210 exact CPCG patient codes pair expanded methylation/expression; specimen identity/QC remain unchecked.|Proceed with external-cohort feasibility, keep final N provisional.|
| Are233 GSE84043 entries233 patients? |No: two assay subseries include repeated methylation profiles.|Use patient mapping table; no accession-level sample inflation.|
| Is GSE107298 independent of GSE83917? |No: all104 older methylation patient codes overlap, with explicit reanalysis provenance.|One CPC-GENE test cohort only.|
| Can preprocessing be treated as identical? |No: GDC SeSAMe versus CPC-GENE dasen; RNA-seq versus author-processed arrays.|Pin methods and platform-aware validation; do not label everything uniformly normalised.|
| Can the adjusted primary endpoint run today? |Not yet: matrices and completeness of shared covariates are unverified.|Complete feature/covariate manifest before freezing a fully adjusted external ΔR² endpoint.|
| Does promoter methylation always suppress immune genes? |No universal rule is supported; the verified counterexample above concerns domain hypomethylation and repression.|Preserve both signs and region classes; prohibit a hard expected-biology recovery gate.|
| Does a promoter anti-correlation prove causation? |No intervention is present in this proposed patient association design.|Use 'associated'; reserve causal/mechanistic support for relevant independent experiments.|
| Is low gene recovery necessarily a pipeline fault? |No; absent coverage or a false biological assumption can also explain it.|Synthetic direction tests gate code; observed biology is reported, not forced.|
| Is B blocked by inability to fetch huge GEO SOFT? |No: the official metadata-only route works and was used successfully.|Use brief metadata audit, then targeted matrices/IDATs only when justified.|

## Recommended next bounded milestone

1. Fetch headers and limited feature coverage from expanded CPC-GENE processed files and pin their checksums; do not rerun already completed metadata counting.
2. Recover public patient covariates and an explicit replicate/specimen policy; quantify missingness before selecting the final baseline model.
3. Freeze the candidate program, probe annotation and cross-platform endpoint scale without external outcome-driven tuning.
4. Keep TCGA development and CPC-GENE validation separate. Publish negative incremental results if obtained; do not tune until significance.
5. Include this evidence and the mechanistic counterexample in the B/C grilling and scientific review before spec approval.

No inferential analysis, model validation, server test, effect-size result, manuscript claim or GitHub push was performed by this audit.
