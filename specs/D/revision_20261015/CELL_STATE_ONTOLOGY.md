# Versioned cell-state ontology

## Hierarchy

1. broad compartment;
2. major cell type;
3. fine subtype;
4. functional programme/state;
5. tumour programme;
6. TME archetype;
7. transition.

## Compartments

- malignant;
- T/NK;
- B/plasma;
- myeloid;
- dendritic/APC;
- stromal;
- endothelial.

## Mapping confidence

`EXACT`, `COMPATIBLE`, `BROADER_PARENT`, `AMBIGUOUS`, `UNSUPPORTED`.

Source-native labels are preserved. A transcriptomic label is not automatically a functional behaviour.

## D2 representation rule

D2-PAIR represents only the qualified tumour and cytotoxic immune compartments plus declared soluble/exposure variables. It therefore returns `UNSUPPORTED` for:

- B-cell/TLS abundance or transition;
- macrophage polarization;
- fibroblast exclusion;
- endothelial trafficking;
- dendritic priming;
- any full-TME state requiring absent compartments.

D2-TISSUE may add a compartment only after its state variables, observations, calibration data, and held-out validation endpoint are specified.
