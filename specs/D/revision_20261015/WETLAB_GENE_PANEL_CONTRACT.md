# Wet-lab gene and readout panel contract

No final discovery panel is frozen by this package. Four separate versioned panels are required.

## Panel T — tumour-cell priming

Candidate assay-qualification anchors from the internal protocol include antigen presentation (`HLA-A/B/C`, `B2M`, `TAP1/2`, `NLRC5`), interferon/viral mimicry (`STAT1`, `IFIT1`, `ISG15`, `OAS1`, `DDX58`, `IFIH1`, `TMEM173`), chemokines (`CXCL9/10/11`), checkpoint/adhesion (`CD274`, `ICAM1`), and prostate antigen/lineage (`FOLH1`, `KLK3`, `ACP3`). Inclusion in the final panel requires assay and evidence review.

## Panel I — immune-cell effects

Separate by CD8, CD4/Treg, myeloid, DC, or B-cell compartment. D2-PAIR initially supports only the qualified cytotoxic immune compartment. Do not infer immune-cell benefit from tumour-only exposure.

## Panel R — favourable functional/ICI-response

Must combine frozen A/A.1/Lin evidence with protein/function readouts. Candidate functional axes include HLA-dependent recognition, productive contact, degranulation, IFN-gamma/TNF, granzyme, and increased checkpoint-dependent killing.

## Panel F — failure/resistance

Detect toxicity/stress, antigen/HLA loss, absent receptor/ligand engagement, persistent exhaustion, compensatory checkpoints, and unsupported stromal/myeloid mechanisms.

## Entry fields

Gene/protein, cell type, programme, expected direction, evidence source, A/B/C/D provenance, measured/predicted status, assay, suitability, functional relevance, alternatives, controls, confidence, inventory status, and version.

RNA change is never treated as protein or function. A gene is not selected solely for model importance.
