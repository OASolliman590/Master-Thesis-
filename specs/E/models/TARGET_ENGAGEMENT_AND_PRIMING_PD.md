# Public PD: engagement, induction and recovery

## Biological question

Which exposure-dependent response components are constrained by public measurements, and what recovery behaviour is still free? Published PBMC HDAC activity, tumour acetylation, HLA surface fluorescence and antigen-specific lysis are distinct observables. They cannot be used as synonymous measurements of one latent priming state.

Each module is `dx/dt=f(x,events,theta,context)` and `y=h(x,theta,assay)+error`. Canonical time is h. Exposure C is measured total/free/intracellular or explicitly nominal concentration, with its matrix label. Relative molecular/protein quantities are not absolute concentrations.

## Candidate HDAC templates, selected separately

```
I(C) = C^n/(IC50^n + C^n)
dH/dt = kH * (H0*(1 + aH*I(C)) - H)
dP/dt = kP * (P0*exp(beta*(H/H0-1)) - P)
```

H is a proximal measured activity/mark **only after the observation mapping is declared**; a mark-induction template is not automatically an activity-inhibition model. H0/P0 are source control scales; kH,kP are h^-1; IC50 matches C units; n is dimensionless. Signed beta is a hypothesis/evidence parameter. Exponential coupling requires bounded extrapolation/numerical safeguards. Do not use H and P simultaneously if public observations cannot distinguish them; the reduced direct `dP/dt=kP*(Ptarget(C)-P)` model is often the proper comparator.

An activity-specific alternative is `dA/dt=kinA-koutA*(1+sI*I(C))*A`, with actual activity units, kinA activity/h and A0=kinA/koutA. These are candidate phenomenological equations, not a claim to reproduce S001 verbatim. An effect compartment `dCe/dt=ke0*(C-Ce)` is optional; it must not duplicate an upstream site delay.

Initial values come from the documented source baseline and pre-exposure history. Withdrawal changes input/exposure according to the source protocol; it does not prove retained intracellular drug is zero. Carryover/stability uncertainty is distinct from PD persistence.

## Data-limited proof obligation

For a constant known exposure-effect input u during treatment and a first-order template:

```
P(te)-P0 = alpha*u*(1-exp(-k*te))
P(te+s)-P0 = (P(te)-P0)*exp(-k*s)  # after input ceases
```

If only the treated endpoint P(te) is known, then for any admissible k>0 an appropriate alpha can match that endpoint. This is a structural argument under the template, not an experimental observation. Actual bounds/other measurements may restrict the equivalence class. The core analysis must show whether the remaining k range changes the primary schedule contrast; it cannot infer that automatically. Use actual source values only after curation and admission, not illustrative biological constants.

## DNMT mechanisms remain separate

Azacitidine/decitabine/other DNMT candidates require compound-specific activation, RNA/DNA participation, incorporation/replication, DNMT loss/recovery and methylation evidence. No substitution of their data into an HDAC curve merely because both are epigenetic drugs. With inadequate intracellular data, use a named nominal-exposure phenotypic model and document what it cannot identify, rather than freely fitting an unobserved intracellular cascade.

## Fit/constraint strategy

Use admitted public data, study-specific observation models and preassigned development/evaluation roles. Estimate only identifiable combinations. Unobserved RNA intermediates are collapsed, fixed from admissible evidence with uncertainty, or omitted. Context transfer is a labelled assumption stratum. No universal priming threshold exists; an operational measured threshold requires an independent biological interpretation.

Tumour and immune PD must be kept separate. Absent immune data do not imply zero impairment; carry alternatives into the admissible set. Local data are unnecessary here and prohibited as silent calibration inputs. E_LAST can later fit a new context-specific version without changing the core release.
