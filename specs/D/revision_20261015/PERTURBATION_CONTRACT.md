# Perturbation identity and inference contract

## Identity tuple

`canonical parent structure + salt/form + concentration value/unit + duration + schedule/sequence + context + control definition + checkpoint token`

## Hard rules

- Unknown drug tokens fail before model invocation.
- Alias mapping requires evidence; name similarity is insufficient.
- Salt/parent conversion is explicit.
- Dose equality permits exact unit conversion, not nearest-dose matching or interpolation.
- Duration is mandatory even when the model token omits it.
- Combination tokens are unsupported unless represented and validated.
- Controls must match the declared context/plate/experiment contract.
- Global-control fallback does not silently satisfy matched-control requirements.
- A successful process exit is not semantic validation.

## D1 supported task

The primary task is context transfer for **checkpoint-supported chemical–dose labels** at a compatible documented collection duration in human prostate contexts. It is not globally unseen-drug prediction.

## Failure classes

`UNKNOWN_DRUG`, `ALIAS_COLLISION`, `WRONG_SALT`, `DOSE_MISMATCH`, `DURATION_UNKNOWN`, `UNSUPPORTED_COMBINATION`, `CONTROL_MISMATCH`, `CONTEXT_UNSUPPORTED`, `FEATURE_MISMATCH`, `OUTPUT_UNCHANGED`, `UPSTREAM_FALLBACK`, `TRAINING_OVERLAP_UNKNOWN`.
