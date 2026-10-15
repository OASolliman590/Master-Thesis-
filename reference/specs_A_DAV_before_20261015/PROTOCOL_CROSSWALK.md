# University protocol crosswalk

## Purpose

The submitted protocol is a binding historical commitment, not a frozen implementation. This crosswalk records what is retained, corrected, expanded, partly feasible, unsupported or deferred. No accession is retained in a response analysis merely because it was named in the proposal.

The machine-readable crosswalk is `protocol_crosswalk.tsv`.

## Key reconciliations

### ICI response datasets

The responder/nonresponder transcriptomic objective is retained. Admission now requires an originating study, a patient-level treatment and endpoint route, an eligible specimen and an interpretable assay. Publications and repository records are evidence, not independent cohorts.

### Six cohorts and approximately 200 patient samples

The proposal lists seven accession strings. `GSE91061` and `SRP094781` are aliases of one originating Riaz/CA209-038 study, provisionally reconciling the list to six study families. “Approximately 200 patient samples” is an original estimate, not a quota. Patients, specimens and assay profiles must be reported separately.

### Named accessions

| Source family | Current classification | Required resolution before admission |
|---|---|---|
| Riaz: `GSE91061` / `SRP094781` | baseline and longitudinal candidate | full object QC, patient/specimen mapping, original BOR, prior-ipilimumab stratum, source/QC exclusions, overlap and exposure |
| Hugo: `GSE78220` / `SRP070710` | baseline candidate | exact patient/site rule, endpoint criteria, full matrix QC and overlap |
| Rose: `GSE176307` | baseline candidate | repeat-sequencing rule, matrix-version/header mapping, specimen timing, endpoint adjudication |
| Kim NSCLC: `GSE135222` / `SRP217040` | assay available; ORR branch blocked | prove a patient-level objective-response route or assign only to a separately named endpoint branch |
| MGH/IMPRES-associated: `GSE115821` / `SRP150548` | baseline/longitudinal lead | resolve publication family, treatment episodes, response source, repeat assays and exact time windows |
| Cho: `GSE126044` / `SRP183455`, linked `GSE126043` | baseline and paired-multiomics lead | construct patient/specimen intersection; same study does not prove pairing |

### Pre-versus-on-treatment

Retained as candidate Paper A.1 work. The revised contract distinguishes scheduled on-treatment, late on-treatment, response assessment, progression, post-treatment, post-discontinuation and after-regimen-change samples.

### Prostate and methylation work

Retained as downstream interfaces. This acquisition kit supplies frozen provenance and data contracts; it does not perform the prostate analysis or drug prioritization.

### Corrections requiring explicit disclosure

- TCGA-LUAD is a molecular comparator, not an observed ICI-positive control.
- Equal sample sizes are not an acquisition requirement.
- Cross-cancer ComBat is not an acquisition default.
- Processed-first acquisition replaces automatic raw-data reprocessing.
- Methylation detection-P filtering must remove poor-quality probes based on high, not low, detection P values; the exact threshold belongs to the assay-specific analysis contract.
- Hypomethylation and domain-level mechanisms remain in scope; promoter hypermethylation is not the only allowed regulatory mechanism.

## Deviation reporting

Every deviation record includes:

```text
protocol item
original commitment
current evidence
source status
patient-level feasibility
revised acquisition route
reason
status
approval or discussion requirement
```

No deviation is silently normalized into the new design.
