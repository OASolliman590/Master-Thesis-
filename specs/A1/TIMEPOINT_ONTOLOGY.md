# Timepoint and treatment-episode ontology

The shared treatment/time ontology is authoritative. A1 retains raw timing text and exact known dates/days alongside a canonical category; canonical labels must not erase timing. A relative day is measured against a named event/episode and has a source-derived precision class: exact, bounded interval, source-supported category, or unknown.

## Categories and semantics

PRE_INDEX_BASELINE: documented before the index episode; prior therapy may still exist. EARLY_ON_TREATMENT and LATE_ON_TREATMENT: source-supported exposure windows while the specified regimen is ongoing. RESPONSE_ASSESSMENT and MAXIMAL_RESPONSE: biopsies anchored to those events, not automatically scheduled on-treatment. PROGRESSION: progression-triggered sample. POST_TREATMENT/POST_DISCONTINUATION: after the treatment end/discontinuation event. AFTER_REGIMEN_CHANGE: following a different combination/sequence component. UNKNOWN: insufficient temporal evidence.

No universal early/late day cutoffs are frozen. A source-specific window registry must define index event, lower/upper boundary or supported categorical rule, component exposures, permissible interval uncertainty, tie rule, lesion/platform policy and scientific contrast. Unknown exact day can be eligible for a genuinely verified categorical window; it cannot be assigned the median day of other patients. Contradictory exact day and category triggers adjudication rather than automatic relabelling.

## Sequence examples as rules, not admitted patient data

A pre-nivolumab biopsy after ipilimumab is baseline for the nivolumab episode but not treatment-naive. COMBAT Pretx/C4D1 spans BAT before nivolumab in the inherited source evidence; that contrast cannot estimate nivolumab-induced molecular change. Induction followed by ICI must retain each component and timing. A later progression biopsy after a regimen switch cannot be paired to an earlier baseline as uncomplicated on-ICI change.

## Pooling windows

Pool only prospectively defined compatible event/window classes after biological justification. Record actual day distributions and range among included observations, sequence components and timing uncertainty. Run a prespecified tighter-window or exact-day sensitivity when feasible. Do not choose cutoffs producing the strongest interaction. Widely separated early and progression observations remain separate even if both were labelled 'post' in a catalogue.

Outcome assessment timing is stored separately from biopsy timing. Eventual best overall response can stratify retrospective change but is future information relative to some biopsies; no dynamic-prediction claim is allowed without a separately specified landmark, risk set and censoring design.
