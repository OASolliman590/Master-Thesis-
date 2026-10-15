# Model and checkpoint registry

## Required record

Every model entry includes repository, code commit/release, model family, checkpoint path/hash, task type, input representation, output representation, gene order, perturbation vocabulary, context vocabulary, training sources, splits, overlap status, licence, resource requirements, deterministic/stochastic behaviour, known fallbacks, and validation role.

## Candidate disposition

| Candidate | Role | Status |
|---|---|---|
| STATE ST-HVG-Tahoe | first D1 candidate | audit first; historical pin retained; weights/runtime/lineage still gated |
| STATE ST-SE-Tahoe | alternative requiring separate SE/ST compatibility | conditional amendment |
| Tahoe-x1 | possible representation/prediction comparator | exact task/checkpoint/licence capability UNKNOWN |
| PIE | possible unseen-context/perturbation comparator | exact applicability and release provenance UNKNOWN |
| Ridge / linear / nearest-neighbour | strong D1 baselines | mandatory where compatible |
| Nonspatial count/ODE model | D2 baseline | mandatory |
| PhysiCell | spatial D2 engine | version/runtime to resolve before implementation |
| PhysiBoSS | intracellular logic option | use only if a justified network adds testable value |

No model is selected from final-test performance. Unknown labels, global-control fallback, unchanged output, or missing feature order fail closed.
