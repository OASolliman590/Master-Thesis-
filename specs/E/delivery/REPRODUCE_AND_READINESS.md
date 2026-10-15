# Reproduction and readiness levels

**Specification complete** means the draft defines both branches and their unresolved decisions. **Software contract checked** means local schema/readiness tests passed. Neither means real model software, admitted study data, calibrated parameters, independent biological evaluation or prospective validation exists.

Run the supplied checkers from the package root:

```
python specs/E/qa/validate_kit.py
python -m unittest discover -s specs/E/qa_v2 -p 'test_*.py' -v
```

The first checks retained compatibility schemas/examples and their bounded semantic tests. The second checks v2 profile/capability/noninterference contracts. Read current logs/receipts for exact counts and limitations. Production ODE, parity, AIU, calibration, scientific independence and clinical tests are not executed by these commands.

For a future actual core release, reproduce from public allowed objects in a clean isolated environment with E_LAST/internal storage absent. Verify all artifact hashes, licences, roles, events, model structure, solver tolerances, randomness, numerical parity and reported figures. Resume must revalidate cache/input integrity; never quietly reuse a model trained on a changed evidence set.

Core completion follows CORE_COMPLETION_CONTRACT and the accepted scientific profile. An E_LAST delay/failure is not a core gate. A missing public quantitative foundation is a core gate. No required-data absence is turned into an executable default.

The release is not a promise of journal acceptance, nor confirmation that the university biological requirement has been satisfied. Open decisions are listed with owners and resolution paths.
