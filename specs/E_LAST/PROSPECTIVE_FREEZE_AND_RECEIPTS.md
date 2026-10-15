# Prediction freeze and prospective workflow

Before the challenge is generated or its outcomes are exposed, freeze: foundation/extension model structure, fitted/posterior/constraint state, public and original development data hashes, code/environment/solver, schedule/events/observation horizon, assay mapping, predicted values and uncertainty, single primary estimand, independent test units, allowable baseline conditioning, controls, exclusions/missingness and decision/falsification criteria.

Receipt fields include a trusted timestamp/witness reference, hashed prediction file, model/data/source-role identities, expected future experiment IDs, allowed pre-exposure covariates and the explicit outcomes-access state. Store on an immutable/version-controlled approved surface; a self-edited timestamp field alone is not proof of prospective order. Do not include identities or consent forms in a public receipt.

The validation loader is read-only with respect to frozen development inputs. It verifies receipt hashes before scoring. Changed receipts, overlapping biological units, test data used for tuning, altered outcome grids or post-outcome exclusions fail the prospective gate. Development results must be unchanged if test outcomes are modified in a software isolation test.

Report prediction first, actual observation next, error/uncertainty calibration and predefined failure criteria next. Null/adverse/contradictory outcomes are retained. Never regenerate predictions after seeing data and present them as the frozen ones.

A new schedule alone is not independent if it shares development donors/runs in a way inconsistent with the stated generalisation; define the intended interpolation versus new-donor claim. Repeated technical readings are not new prospective experiments. Prospective original evidence supports only its tested layer/context, not the entire PBPK–QSP chain.
