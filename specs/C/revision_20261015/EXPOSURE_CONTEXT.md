# Exposure, time and cellular-context contract

## Discovery tensor

C2 results remain indexed by:

`parent compound × model × exact dose/unit × duration × treatment sequence × project/experiment × release`.

Do not collapse this tensor into one compound mean when coverage is unequal.

## Exposure rules

- exact numeric dose and unit are preserved;
- rounded labels never substitute for exact values;
- unmeasured doses/times are not interpolated and called observed;
- nominal extracellular concentration is not equated with free medium, intracellular, plasma or tumour exposure;
- mechanism-aware windows are chosen from prior biology/metadata, not outcome strength;
- different windows permit within-compound interpretation but not unqualified drug superiority.

## Mechanism-aware interpretation

### DNMT inhibition

Replication dependence, drug instability and cumulative exposure are explicit. A 24-hour signature is an acute transcriptional observation, not proof of adequate demethylation. Longer/repeated exposures and target engagement are required for mechanistic interpretation.

### HDAC inhibition

Rapid transcriptional responses may coexist with cell-cycle arrest, apoptosis and stress. Immune-programme changes are interpreted alongside viability and stress signatures.

### EZH2/PRC2 modulation

Delayed H3K27me3 depletion and chromatin response are expected in many settings. A 24-hour transcriptome cannot stand in for confirmed PRC2 target engagement. EED and catalytic EZH2 mechanisms remain separate.

## Model relevance

For every model record:

- authenticated identity and source;
- prostate lineage and disease state;
- androgen-receptor status;
- major genetic context;
- baseline `Q_E`/`Q_M` programme state;
- methylation/chromatin state where available;
- target expression;
- programme inducibility under a positive control;
- relation to the planned wet-lab model.

PC3 is not automatically primary because it has the greatest LINCS coverage. AR-positive and AR-negative contexts may both be required if the B barrier spans them.

## Non-prostate contexts

A non-prostate model can support mechanism or immune-pathway coherence. It cannot be labelled direct prostate validation. Species, lineage and intervention type remain visible.

## Wet-lab alignment

Computational model relevance is assessed before local availability. The later feasibility layer records whether PC3, 22Rv1, LNCaP or another model is actually available, authenticated, mycoplasma-negative and assay-qualified.
