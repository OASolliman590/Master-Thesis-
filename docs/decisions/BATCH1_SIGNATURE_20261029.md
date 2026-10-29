# Batch 1 sign-off: GSE248014, GSE168204, Hugo GSE78220 × A_BASELINE_BIO (29 Oct 2026)

The user (thesis author, omar soliman) signed in chat on 29 Oct 2026: "Sign corrected". This approved the corrected answers below, which the coordinator had checked against the source objects. Signature role: thesis author, public-source reviewer and integrator under the V7 public-reviewer amendment. Split role for all three: DEVELOPMENT. Real-response analysis is still not authorized.

## GSE248014 (PDAC, entinostat lead-in then entinostat + nivolumab, NCT03250273)
- V4: GEO `patient id` characteristic; 23 Baseline specimens from 23 distinct patients.
- V5: SOURCE_BINARY ORR-type endpoint (R = CR/PR by RECIST 1.1, from the trial results). Baseline biopsies precede all study treatment. Responders 3 of 23 (imbalance noted).
- V6: No shared identifiers with other cohorts. Prior ICI is excluded by trial eligibility (trial-level only); patient-level prior exposure stays UNKNOWN.

## GSE168204 (metastatic melanoma, MGH)
- V4: Title token maps to 10 distinct patients (one PRE specimen each).
- V5: SOURCE_BINARY clinical-benefit endpoint (R = CR/PR or SD with PFS > 180 days; RECIST version unstated). Never merged with ORR.
- Treatment correction: the baseline drug classes are anti-PD-1 5, anti-PD-L1 3, anti-PD-1 + anti-CTLA-4 2 (GEO `antibody`). The class is kept per patient and never pooled silently; the specific drugs remain UNKNOWN.
- Batch correction: the 10 baseline specimens span 4 sequencing batches (GEO `batch`). This is recorded as a known confounder.
- Feature universe: 75,205 retained rows, made up of about 21,000 gene symbols plus about 54,000 NONCODE lncRNA identifiers (`NONHSAG…`). Accepted as-is, because signatures look up genes by symbol and key immune genes are present.
- V6: Prior ICI UNKNOWN. Possible patient overlap with GSE115821 (also MGH melanoma, parked). This does not block single-cohort DEVELOPMENT, but it must be resolved before any joint split.

## Hugo GSE78220 (metastatic melanoma, pembrolizumab or nivolumab)
- V4: 26 patients. Pt27A is kept by the lowest-letter rule; Pt27B and the Pt16 on-treatment sample are outside this branch.
- V5: ORR from GEO CR/PR/PD (paper assessment irRECIST, not RECIST 1.1; noted). Biopsies are pretreatment per GEO.
- Representation: author FPKM, linear by LINEAR_FPKM_BY_RANGE.
- V6: Prior ICI UNKNOWN (prior MAPK inhibitor for some patients is not ICI). Overlap with Riaz: no shared identifiers; site-level independence UNKNOWN, as in RIAZ_QC_EXPRESSION_BINDING_20261026.md.

## Signature transfer (29 Oct 2026)
The user approved in chat ("Yes, move it") that, after the normalization, feature-scope and counts-lane fix, the 29 Oct signature and decisions may be transferred to the regenerated worksheets. The transfer applies only if the item set and questions are unchanged, apart from the hash and the newly declared normalization facts. If any item differs (GSE168204 included), the transfer stops and the difference goes to the user.

## Identity confirmation and GSE168204 transfer (29 Oct 2026)
The user approved both of the following in chat ("Yes, both"):
1. **Identity.** For GEO-only cohorts, admission may mark patient identity VERIFIED only on the signed path, when all of these hold: the signed worksheet's V4 decision is PASS, the field map's identity rule is source-backed (a GEO patient characteristic, or a title token that agrees with it), and that rule produced the patient. Provisional and unsigned runs never mark identity VERIFIED.
2. **GSE168204.** The signature may be transferred even though the regenerated worksheet no longer contains `FEATURE_UNIVERSE_UNRESOLVED`. That item had been answered NOT_APPLICABLE, and the feature-universe decision above still stands. Every other item must be unchanged.

## Signed answers clear the remaining stages (29 Oct 2026)
The user approved in chat ("Yes, one round"):
1. **Episode binding.** On the signed path, a signed V5 PASS marks each clinical outcome's binding to its index treatment episode VERIFIED for GSE248014, GSE168204 and Hugo. This matches the Riaz rule, where the binding becomes VERIFIED when the named reviewer signs.
2. **GSE168204 identity.** The title-token patient IDs are accepted on the strength of the signed V4 PASS (10 distinct patients, one PRE specimen each), with no separate GEO patient-ID characteristic required. The rule applies only to this cohort.
3. Any later admission stage that needs only an already-signed answer may be cleared the same way. A blocker that needs a new decision is reported, not decided.
Provisional and unsigned runs never mark any of this VERIFIED.

## Prior ICI, exposure and split declarations (29 Oct 2026)
The user decided in chat, for Hugo GSE78220 and GSE168204:
1. **Prior ICI UNKNOWN is allowed for DEVELOPMENT.** These cohorts may be admitted with prior ICI recorded as UNKNOWN per patient, carried as a covariate. A later sensitivity analysis excludes them. A cohort used as the final test still needs prior ICI known.
2. **Exposure: METADATA_ONLY.** Neither the user nor the earlier thesis project has examined these cohorts' expression or scores against response. Only sample metadata and table shapes were checked.
3. **Split policy: DEVELOPMENT**, as already signed.
4. GSE168204's non-baseline specimens are outside A_BASELINE_BIO (the signed V4: one PRE specimen per patient), as Hugo's Pt16 on-treatment sample is.
GSE248014 is no longer pursued for A/B admission (see COMBINATION_COHORTS_20261029.md).
