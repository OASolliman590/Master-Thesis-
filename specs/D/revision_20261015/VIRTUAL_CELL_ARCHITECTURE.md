# Virtual-cell and virtual tumour–immune architecture

## D0-M — provenance controller

Resolves sources, model/checkpoint identity, feature order, perturbation vocabulary, controls, splits, licences, hashes, and overlap.

## D0-O — observer module

Maps source-native cell/programme labels to versioned state probabilities. Lin-dependent observer work is independent of D1.

## D1 — molecular benchmark

Frozen model and baselines predict held-out measured expression effects. Truth remains unavailable to inference/baseline workers until evaluation.

## D2-PAIR — measured-driver tumour–T-cell model

This two-cell assay model is **not a full TME**.

Initial agents:

1. qualified prostate tumour cells;
2. qualified cytotoxic immune cells.

Initial processes:

- tumour proliferation/death;
- immune motility where measured/required;
- contact formation;
- recognition eligibility;
- contact-dependent killing;
- checkpoint inhibition/blockade;
- direct epigenetic-drug effects represented from measured calibration;
- assay observation model.

## D2-TISSUE — conditional extension

Add one compartment or field at a time only when its measurements and held-out endpoint exist. Candidate additions: suppressive myeloid cells, fibroblast/stromal barriers, a recruitment field, oxygen, or selected cytokine fields.

## D2-LEARNED — conditional coupling

Substitute or augment measured drivers with frozen D1 programme predictions only after D1 and bridge gates pass. Run ablation against measured-driver and rule-only versions.

## D-FUTURE

Patient-specific calibration, systemic scheduling, virtual clinical populations, and individualized recommendations are outside Paper D; Paper E owns systemic pharmacology and population scheduling.
