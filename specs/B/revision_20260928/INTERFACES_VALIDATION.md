# A→B, validation, B→C and experimental nomination

PROPOSED. No candidate is certified reversible by this interface.

## A→B product contract

| Product | Required contents | Permitted B use |
|---|---|---|
| Clinical gene effects | Canonical ID; exact R/NR definition; baseline/timing; regimen/cancer/study; effect scale and direction; estimate, SE/CI and multiplicity; heterogeneity; source and exposure hashes | Clinical relevance and directional hypothesis, not conditional classifier-weight interpretation |
| Clinical programme effects | Frozen membership, scoring/weights/directions, source gene universe and coverage, study-level effects and reproducibility | Programme-level clinical anchor |
| Frozen predictor | Full coefficients, intercept, transformations, feature order, training provenance and validation status | Separate transported research output; no truncation while retaining original model name |
| Biological annotations | Original curated source/version; tumour/immune context; evidence type and uncertainty | Annotation, not clinical proof or pharmacological instruction |
| Qualified longitudinal support | Within-patient identities, treatment windows, response-by-time estimand, missing follow-up and prior-treatment context | Pharmacodynamic corroboration; not independent baseline validation or causal treatment effect |

The accepted A specification currently emphasizes a gene/coefficient product; the expanded effect-estimate products remain to be delivered and frozen. B may prepare fixed APM/source infrastructure independently but cannot claim A-derived results before those products exist. A associations in treated cohorts do not by themselves estimate benefit from ICI versus no ICI.

Preserve full eligible gene effects or an explicitly frozen evidence universe, not only positive significant genes. B does not use A final-test results to select programmes or rewrite A's score. If a legacy product was exposed to reserved-test outcomes, record that exposure and restrict its confirmatory status.

## Validation levels

| Level | What is tested | What it does not establish |
|---|---|---|
| Discovery | Defined TCGA prostate contrasts and regulatory associations | Independent replication |
| External molecular | Frozen prediction in CPC, or separately declared association replication in another eligible cohort | Clinical ICI response or causal methylation |
| Orthogonal | Protein/ATAC/other assay corroboration | New independent cohort when patients overlap |
| Cellular/spatial | Compartment localization or regional organization | Same-cell methylation mechanism unless measured; functional immune benefit |
| Mechanistic literature | Existing experiments in a specific model/exposure | A new result in this patient population |
| Perturbational C | Measured expression/protein changes under interventions | Automatic immune killing or clinical efficacy |
| Wet-lab restoration/function | Planned molecular and functional experiment | Clinical sensitisation without appropriate subsequent evidence |

CPC tumour-only data can validate an eligible tumour molecular association; it cannot replicate a tumour-versus-normal difference without appropriate reference specimens. Different endpoints and populations must not be hidden under a generic “validated” label.

## Exposure and overlap ledgers

`overlap_ledger` records source A/source B, relation (independent recruitment, shared patient, shared specimen/different assay, different specimen/same patient, technical replicate, reanalysis, portal mirror, publication reuse, unresolved), supporting source, affected patients/assays and disposition. Cross-namespace ID differences alone are insufficient independence evidence.

Seeded relationships: old CPC GEO series overlap expanded GSE107298/GSE107299; Fraser's pooled portal includes TCGA; Sinha protein data belong to the CPC family; Arbet final atlas overlap needs exact inventory; Kiviaho reuses several single-cell studies including Hirz; WCDT data recur in later studies. Do not sum their reported sample sizes.

`exposure_ledger` records actor/date, source/object/hash, fields accessed, purpose (metadata/coverage/clinical outcome/molecular endpoint/association/model performance), external-reservation role, permitted action and contamination disposition. Historical CPC coverage access remains disclosed. Outcome-adjacent omics from reserved CPC patients cannot select discovery genes simply because the modality is protein rather than RNA.

## Two separate freezes

**Freeze D — discovery nomination:** freeze the TCGA-derived candidate IDs, exact comparison, direction, statistical selection rule, evidence fields and hashes before CPC/C results. A clinically anchored candidate must distinguish its clinical association from its prostate expression direction. No external information is used to repair an empty or inconvenient discovery set.

**Freeze V — evaluation:** freeze final TCGA-fitted B-P models, P/U/Q, transformations, eligibility, precision criterion and external population before endpoint/error evaluation. For association replication, freeze its family and model separately; external fitting is allowed only for that different estimand.

After evaluation, append external support/contradiction/missingness to a new evidence-table version without changing Freeze D's candidate membership or retrospective selection claims. A later revised candidate set is a new exploratory version, not the original independent handoff.

## B→C evidence table

Minimum fields: candidate_id; canonical gene/programme; A product/version and clinical effect/direction/uncertainty/context; B contrast ID and prostate effect/CI; promoter and domain methylation evidence; cognate expression association; composition sensitivity; CNA/genetic alternatives; cellular localization; protein/accessibility/spatial support; independent validation and overlap status; known mechanistic literature; assay availability; contradictions; proposed restoration direction with rationale or UNKNOWN; selection-rule/version/source hashes.

Use explicit evidence states: `supports`, `opposes`, `measured_inconclusive`, `not_measured`, `not_comparable`. Missing is not negative evidence; a nominal null with a wide CI is not a demonstrated absence. Keep effect sizes and uncertainty beside states. Do not combine these dimensions into an arbitrary weighted sum. A display can use gene ID or predefined programme order; an intervention ranking belongs to C.

Separate `disease_direction` from `restoration_direction`. For an A-associated gene, a coefficient or responder association alone does not justify pharmacologically increasing expression in every cell. Suppression of an inhibitory programme may be plausible, whereas some inflammatory signals indicate adaptive resistance rather than a beneficial target to increase.

The proposed within-prostate tumour/adjacent query and the registered PRAD/LUAD query are separate versions. C's bidirectional WTCS requires both directions from the same approved axis. No forced number of up/down genes and no canonical-recovery quota. If only one direction is supported, the current bidirectional C primary is blocked or requires an explicit one-sided amendment before scoring.

## Wet-lab nomination dossier, not a redesigned protocol

For each nominee provide: what RNA/protein/function to measure; its actual clinical association; appropriate prostate disease/model context; baseline expression and epigenetic state to verify; competing genetic/composition explanations; what directional molecular change would be consistent with restoration; and which functional tests remain necessary. A cell line's baseline must be measured or source-verified, not inferred from its cancer label.

A monoculture can test tumour-cell readouts but not restoration of absent immune populations. Re-expression does not establish peptide presentation; protein presentation does not alone establish T-cell killing; killing does not alone establish an ICI interaction. Preserve these stages and the registered experiment's separate approval requirements.
