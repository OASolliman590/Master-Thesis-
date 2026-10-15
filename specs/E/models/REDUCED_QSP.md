# Reduced tumour–immune QSP under public constraints

## Question and minimal state set

Can exposure-dependent tumour changes, direct toxicity, immune impairment and checkpoint blockade jointly explain admitted observations, and do unresolved mechanisms change the sequence contrast? The initial model does not add APC/Treg/myeloid/lymph-node modules without a specific observable/question.

States: viable tumour T [cells or declared burden unit], effector E [cells], competent fraction F [0,1], and the selected PD state P [relative assay scale]. If an aggregate tumour-volume model is used, explicitly map cell/burden units and never combine volume with count parameters. Antibody occupancy O is a dimensionless observer or a mass-consistent binding state, not both.

```
dT/dt = rT(C_T)*T*(1-T/KT) - ddir(C_T)*T - Kimmune
dE/dt = (gE - dE0 - dEdrug(C_I))*E + sE(t)
dF/dt = krec*(F0-F) - kimp(C_I)*F + kact(C_I)*(1-F)
Kimmune = kkill * T * [E/(KE+E)] * F * R(P) * chi
R(P) = exp(betaR*(P/P0-1))
chi = 1/[1 + eta*L*(1-kappa*O)]
```

rT,gE,dE0,ddir,dEdrug,krec,kimp,kact,kkill are h^-1, sE is cells/h, KT has tumour units, KE cells; F0,kappa in [0,1], eta>=0, L>=0 is a defined dimensionless checkpoint-suppression proxy. R(P)>0 is a hypothesis with explicit extrapolation limits, not measured antigen recognition. Baseline P0>0 and bounded betaR require evidence/assumption records. Source-specific cytostasis and death should be distinct only where measurements distinguish them; otherwise use an identifiable net-growth model and weaken mechanism claims.

No values are supplied as biological defaults. Growth saturation, immune supply/expansion, activation and all extra states are optional model structures, not mandatory free parameters. For a culture experiment with no immune-cell addition/trafficking, sE=0 is a structural context definition supported by its protocol, not a universal human parameter.

## Checkpoint binding versus function

For rapidly equilibrating single-site binding, `O=CAb_site/(KD+CAb_site)` is allowed only with a justified timescale/site/free-concentration interpretation. Otherwise `dO/dt=kon*CAb_site*(1-O)-koff*O` is a non-depleting receptor-fraction observer. KD concentration, kon concentration^-1 h^-1, koff h^-1. A mass-depleting binding model needs receptor amount, bound drug and internalisation balances. Do not add binding clearance to a PK model twice.

kappa converts occupancy to functional relief and is not fixed to one by affinity. eta and L also need functional/measurement support. If evidence does not identify blockade, compare explicit no-effect and functional-effect structures; do not label the latter validated. CTLA-4 or LAG-3 cannot enter by renaming PD-1 terms.

## Observation contracts and limiting cases

Observe tumour-specific counts/death, immune counts/viability/function, actual ligand/receptor assay output and antibody contrasts where published. Mixed viability signals do not identify T and E separately. A lysis percentage over an interval needs its denominator, spontaneous/max-release controls and assay mapping, not an instantaneous death rate by default.

Require nonnegative T/E and F invariance within [0,1]. Check E=0 gives no immune killing; kkill=0 separates direct effects; betaR=0 removes priming-recognition coupling; eta=0 removes checkpoint inhibition; O=0 gives no blockade; C=0 returns the defined untreated dynamics. Do not project negative states to zero silently to conceal solver errors.

## Context separation

Each context has its own baseline, encounter conditions, growth/immune availability and observation mapping. Public culture calibration is not human tumour efficacy validation. Human exposure projection couples only through an explicitly uncertain bridge. All parameter transfers receive an evidence/assumption label and domain-shift sensitivity; tumour partitioning is never tuned solely to obtain a favourable immune outcome.

C-SCHEDULING requires relevant public functional constraints. C-IDENTIFIABILITY examines which equally compatible assignments generate unresolved contrasts. Neither requires original local assays. Missing checkpoint response does not demonstrate clinical resistance; a null result in an unqualified assay is not evidence of zero kappa.
