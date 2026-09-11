# Research: Spec 021 — Stage 12 TCGA Projection Framing

## 1. Framing Constraint
TCGA cohorts are not ICB-treated cohorts. Therefore this stage is prognostic context, not predictive validation.

## 2. Scoring Constraint
Raw mean expression scores can be dominated by high-baseline genes. Standardizing to per-project z-score reduces this dominance for cross-gene aggregation.

## 3. Survival Constraint
Continuous Cox retains more information than hard median splits. KM grouping remains descriptive.

## 4. Layer-4 Context
The defensible spec-007 TCGA objective is epigenetic Layer-4 association with Thorsson immune subtypes, not claims of ICB-response validation.

## 5. Covariate Refinement
Where available, include age/stage covariates in the continuous Cox model and record model terms in output contracts.
