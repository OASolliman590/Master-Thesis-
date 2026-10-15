# Molecular-to-phenotype bridge

This is the most scientifically vulnerable layer. It is optional for initial measured-driver D2-PAIR.

## Mapping record

Each mapping specifies:

- cell type;
- programme and genes/proteins;
- source evidence and context;
- measured perturbation evidence;
- mapping function and direction;
- parameter name/unit/range;
- uncertainty and structural alternatives;
- calibration source;
- held-out validation source;
- permitted interpretation.

## Initial eligible behaviours

- tumour proliferation/death;
- surface antigen-presentation eligibility;
- tumour–immune contact recognition;
- immune killing probability/rate;
- checkpoint-dependent inhibition/restoration;
- immune persistence/activation where measured.

Recruitment, macrophage polarization, fibroblast exclusion, phagocytosis, and B/TLS biology are conditional.

## Prohibited mappings

- one gene directly determines a complex behaviour without evidence;
- RNA change is treated as protein/function;
- a model-importance score becomes a biological coefficient;
- a 24-hour expression prediction is extrapolated into an unvalidated time course;
- weakly identified parameters are interpreted as measured biology.

## Learned-coupling gate

Learned predictions must improve a held-out functional/composition endpoint beyond measured-driver and rule baselines. Otherwise report the negative result and retain measured drivers.
