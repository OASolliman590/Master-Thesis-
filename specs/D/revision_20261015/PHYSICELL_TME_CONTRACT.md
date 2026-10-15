# PhysiCell / PhysiBoSS contract

## Minimal D2-PAIR simulation

Required:

- bounded geometry matching the assay;
- tumour and immune cell definitions;
- mechanics/contact rules;
- migration only if required by the assay;
- proliferation and death;
- contact-dependent immune killing;
- checkpoint-blockade mechanism;
- measured/frozen drug driver;
- deterministic seed replay;
- observation/export layer matching wet-lab readouts.

## Fields

No diffusible field is included merely because it is biologically interesting. Initial fields are zero or one treatment/exposure driver and, only if measured/required, one signalling/recruitment field. Oxygen is included only if the experimental geometry creates a validated oxygen question.

## PhysiBoSS

Use only when a bounded intracellular Boolean network is source-supported, separately calibrated, and improves the target endpoint. Do not create a network for every agent.

## Required software tests

- unit consistency;
- boundary conditions;
- schedule timing;
- deterministic seed replay;
- restart/resume;
- nonnegative populations/rates;
- contact rule correctness;
- observation-model consistency;
- missing-compartment outputs return `UNSUPPORTED`.
