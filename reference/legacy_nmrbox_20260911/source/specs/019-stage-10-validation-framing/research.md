# Research: Spec 019 — Stage 10 Validation Framing

## 1. Framing Defect
Indirect-vs-mega agreement uses the same discovery cohorts and cannot be called independent validation. It is a robustness check.

## 2. Contract Separation
- **Robustness:** concordance between internal analytical paths.
- **External validation:** held-out or nested evaluation with explicit predictive metrics.

## 3. Held-out Contract
Required columns:
- `auc` (numeric, bounded [0,1])
- `effect_concordance` (numeric, bounded [0,1])

The command fails loudly on malformed or out-of-range values.

## 4. Scientific Validity
This avoids overstating evidence and keeps predictive claims tethered to genuinely unseen data.
