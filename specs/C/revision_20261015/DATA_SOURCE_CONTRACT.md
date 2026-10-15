# Data and source contract

## Source-role principle

Every source answers one declared question. A source may have multiple roles only when the exact objects, units and overlap are explicitly separated. A mirror, reprocessed release or derived portal does not create an independent study.

## Required source record

Every source record must include:

- original study and persistent identifier;
- repository/release/object URL and hash where available;
- assay and feature space;
- intervention, parent compound/target and combination status;
- model, lineage, species and provenance;
- dose, unit, duration, sequence and washout;
- control definition;
- sample/experiment identifiers;
- biological unit;
- verified total `N` and independent `N`;
- processed-object availability;
- access and licence;
- overlap with LINCS, B discovery and other C sources;
- Paper C question answered;
- admission status and blocker;
- claim ceiling.

The machine-readable representation is `schemas/source_record.schema.json`. Candidate source roles are listed in `manifests/source_roles.tsv`; catalogue totals are not eligible `N`.

## Source families

| Family | Primary role | Not permitted to establish |
|---|---|---|
| Paper A/B handoff | Clinical direction, prostate deficit and regulatory evidence | Drug response or reversibility |
| LINCS/CMap | C2 discovery and C1 calibration | Biological population efficacy or independent validation |
| Independent GEO/SRA/BioStudies experiments | Proposed primary and Level 2 validation | Clinical benefit or ICI interaction unless directly designed |
| CCLE/DepMap | Model relevance and baseline target/programme context | Drug-induced restoration |
| PRISM/GDSC/CTRP | Viability/growth context | Immune restoration |
| Genetic perturbation/Perturb-CITE-seq | Target/mechanistic coherence | Equivalence to chemical inhibition |
| TISMO/immune-combination studies | Native immune-context or interaction evidence | Human prostate clinical response |
| ChEMBL/PubChem/DrugBank | Identity, mechanism and assay annotation | Regulatory approval or clinical feasibility by category alone |
| Regulatory/primary human PK sources | Status, formulation and exposure | Tumour exposure when not measured |
| Wet-lab records | Prospective Level 5 validation | Evidence before experiment execution |

## Independent measured primary admission

A source enters the proposed primary only when all apply:

1. human prostate malignant model, organoid or explicitly justified ex-vivo model;
2. exact epigenetic intervention or target perturbation in the approved universe;
3. identifiable control and source-specific contrast;
4. full measured feature universe, not only a selected DE-gene table;
5. at least three independent biological replicates/blocks per primary arm; two-replicate studies are secondary only;
6. replicate identity and shared-control structure are reconstructable;
7. treatment metadata are outcome-blindly frozen;
8. no overlap with B patients and no reuse of the same experiment as LINCS-independent evidence;
9. query coverage passes `ANALYSIS_CONTRACT.md`;
10. raw/processed access and lawful use are documented.

A source failing one rule remains visible with `blocked`, `secondary_only` or `unavailable` status.

## Current high-priority source dispositions

- **LINCS2020:** metadata audit complete; expression matrix/scoring route remains gated. Discovery only.
- **GSE199800:** all named candidate rows were observed, but the authoritative row-to-GSM/plate/control join is unresolved. Blocked for the intended matched-control primary contrast.
- **GSE35242/GSE35246:** strong admission candidate with prostate expression/methylation perturbation and independent-day triplicates. Full contrast/platform QC remains required.
- **GSE216053:** candidate source; exact intervention/genotype/control/replicate contract remains unresolved.
- **Perturb-CITE-seq:** orthogonal Level 3 genetic/immune-context evidence only.
- **TISMO:** source-native mouse immune-context evidence only.

## Deduplication and overlap

Preserve original study, project, plate, experiment, instance, sample and release IDs. Exact or partial instance overlap across LINCS releases is not independent evidence. A source derived from OncoLoop cannot validate an OncoLoop-derived discovery object without explicit dependence disclosure.

## Data placement

Large matrices, raw sequencing, restricted data and credentials remain outside Git. Git stores lawful compact manifests, hashes, schemas, code, source-specific receipts and derived non-sensitive tables.
