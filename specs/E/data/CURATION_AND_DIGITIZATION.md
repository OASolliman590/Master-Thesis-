# Curation, duplication and figure extraction
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Original-study identity

Resolve publication family → original study → cohort/experiment → regimen → specimen/assay → observation. Link preprint/final/supplement/regulatory review/database mirror through evidence, not title similarity alone. Record shared trials, controls, repeated figures and upstream calibration/training overlap. An unresolved duplicate relationship blocks independence claims, not preservation of the source.

For every extracted number retain raw text/value/unit, canonical value/unit, statistic, denominator, biological unit/N, source page/table/panel/row, extraction method, curator, verification, transformation, uncertainty and permitted role. Null N is accompanied by a reason; repeated timepoints are not subjects. Never synthesize individuals from a mean profile.

## PK-specific extraction

Retain parent/metabolite, analyte, total/unbound, plasma/serum/blood/tissue, dose basis, route/formulation, administration/infusion duration, prior regimen, steady-state definition, fed/fasted, population/concomitants, time origin and assay limits. CL differs from CL/F; V from V/F; AUC0–t, AUC0–inf and AUCtau differ. Geometric means/medians are not arithmetic means. Unit conversion does not authorize a statistic conversion.

If SD/SE/error-bar meaning or denominator is unknown, preserve UNKNOWN. A reported parameter and its underlying curve are not independent evidence; link dependency IDs and use either a justified joint likelihood or one primary representation. Group-mean curves cannot identify random-effect covariance.

## Digitisation protocol

Prefer numeric tables. For an open figure, record original article/version/page/panel, axis scale and units, calibration points, observation-symbol legend and error-bar meaning. Preserve a permitted crop/reference, digitisation project/settings, exported points and tool version. Distinguish measured symbols from fitted/predicted curves. A predicted curve cannot be biological validation.

For log axes calibrate in log space and back-transform explicitly; nonpositive calibration values are invalid. Independently check representative early/peak/late points and error bars, including units and time origin. Record rounding, pixel/calibration uncertainty and extraction disagreement. Do not silently convert confidence intervals into SD or symmetrize log-scale intervals. A second curator's extraction review is data QC, not independent experimental validation.

## Observation likelihood and extraction uncertainty

Retain point-level extraction uncertainty separately from reported sampling uncertainty and between-experiment variability. Avoid treating digitisation error as known biological SD. For summary curves use a source-appropriate joint/aggregate likelihood or an explicit approximate weighting sensitivity; do not infer sample-level precision from the number of digitised points. Sensitivity to uncertain error-bar interpretation is reported, not resolved by selecting the most favourable version.

## Admission and correction

Second review checks numeric fidelity and scientific context. A discrepancy creates a versioned correction with original value retained. Data-role assignments are frozen before fitting. Missing/BLQ values preserve limits and reasons; no zero substitution. Excluded observations retain the reason and intended role. Unavailable sources remain discoverable in the registry with an exact next action; do not repeatedly retry blocked resources.
