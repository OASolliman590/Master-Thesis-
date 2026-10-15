# E1 systemic PK/PBPK and antibody PK
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Question and architecture

What exposure does a documented systemic regimen generate, and how uncertain is exposure at the proposed site of action? Systemic PK is evaluated separately from prostate delivery and culture PD. Audit S001 and any actually recovered public asset before selecting physiological detail. A simpler PK model is a required comparator, not an inferior model by definition.

Every module follows `dx/dt=f(x,events,theta,context)` and `y=h(x,theta,assay)+error`. Internal canonical time is h; amount and concentration remain separate. A compound-specific molar conversion requires verified parent molecular weight and dose basis. No biological numeric parameters are released here.

## Open two-compartment small-molecule comparator

States: gut amount Ag [amount], central Ac [amount], peripheral Ap [amount]. Cc=Ac/Vc and Cp=Ap/Vp [amount/L]. Parameters ka [h^-1], F [fraction], CL,Q [L/h], Vc,Vp [L].

```
dAg/dt = -ka*Ag
dAc/dt = F*ka*Ag + uIV(t) - CL*Cc - Q*(Cc-Cp)
dAp/dt = Q*(Cc-Cp)
```

Oral events add documented dose to Ag; IV bolus adds to Ac; infusion is an amount/h input over the exact interval. For mass accounting, `(1-F)*ka*Ag` is unabsorbed/presystemic loss, not a second unexplained elimination. Do not infer F from oral-only CL/F data. If an apparent-parameter model is used, retain CL/F and V/F explicitly rather than relabelling them systemic CL/V.

Initial amounts are zero only for genuinely drug-naïve initial conditions. Otherwise reconstruct prior events or solve a justified periodic steady state. A source-reported steady-state label does not permit deleting dose history. Metabolites need their own analyte/formation/elimination evidence and amount balance; do not mix total parent-plus-metabolite observations with parent predictions.

## PBPK audit and generic tissue contract

For a perfusion-limited tissue i, `dAi/dt=Qi*(Ca-Cvi)-CLi*Celigible`, with `Cti=Ai/Vi` and a source-defined relation between Cvi, Cti, partitioning and binding. This is a design interface, not the complete S001 equation system. Arterial/venous pools, blood/plasma ratio, tissue flows/volumes, gut absorption, hepatic/renal elimination and any permeability-limited tissue must be transcribed from the selected source with consistent amount conservation. Flow sums and recirculation cannot be double counted.

S001's PK/HDAC/platelet framework is a reconstruction candidate. Its source tissue proxies must not become measured prostate tumour concentrations. Fit uncertain tumour partitioning neither to force HLA induction nor to manufacture immune benefit. More tissue compartments are justified only when they improve the question and have identifiable/source-supported inputs.

## Site-of-action observer

When direct tissue measurement is absent, an explicit uncertainty bridge may use:

`dCsite/dt = keq*(Ksite*Cu_plasma-Csite)`.

Csite is an effect-site observer [concentration], keq [h^-1], Ksite [dimensionless]; this does not remove drug from the PK mass balance. Do not simultaneously count the same compartment as a physiological distribution compartment. Ksite/keq are unresolved or bounded priors requiring a rationale, not fitted to desired tumour outcomes. Plasma total→unbound→tumour free→intracellular transitions each have a separate evidence/uncertainty record.

## Antibody comparator

Use a source-supported compartmental/population or PBPK model, not full PBPK solely for symmetry. A linear two-compartment amount model has the Ac/Ap equations above without gut absorption; actual route/absorption is selected from evidence. Time-varying clearance, target-mediated disposition or Fc-related handling enter only with source support and identifiability. Binding in a downstream occupancy observer must not be counted again as systemic elimination unless a mass-consistent target-mediated model is explicitly implemented.

Public antibody PK parameters must match molecule, population, assay and regimen. Convert mass to molarity only with the actual biologic molecular-mass basis. The antibody is not yet selected; all quantities remain unresolved.

## Observations and evaluation

Predict the actual observed analyte/matrix/total-or-unbound scale. Individual positive concentrations may use proportional/lognormal plus additive error if supported; aggregate means need an aggregate likelihood and known/unknown uncertainty treatment, not invented individual trajectories. BLQ uses a censored likelihood with the assay limit. Independent evaluation splits by original study/population/regimen as justified, not curve points.

Report AUC/Cmax/time-course metrics appropriate to the source, bias and predictive coverage with measurement/extraction uncertainty. No universal two-fold rule validates every context. Upstream parity, systemic evaluation and tumour exposure remain separate receipts. No native asset or real PK fit has been executed in this draft.
