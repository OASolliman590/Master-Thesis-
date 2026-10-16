# Amendment verification — 16 October 2026

Run from repository root:

```sh
python specs/amendments/2026-10-16-immune-programmes/validate_packet.py
```

Result: PASS. The read-only validator checks all 21 registry IDs, exact member hashes, null membership handling, pending releases, preservation of inherited B lists, HOPE/GEP/APM18 cardinality, distinction between offset and unoffset CYT, and seven archived legacy files. All 696 files in the RC2 freeze manifest match their recorded byte count and SHA-256. Four deliberate in-memory invalid mutations (false release, altered membership, broken hash and primary replacement) are rejected. `validation_result.json` is the machine-readable receipt.

Eight recovered objects, including the inspected but uncopied `old_cli.py`, were independently compared to Git blob hashes in the parent's retrieved upstream tree at commit `96c16794bafc8946ae9f0bdcef81d5f3a599542b`; all matched. Seven compact config/GMT objects are archived here. Inventor18 candidate membership was checked against recovered GEP membership; candidate weights are not promoted into a running scorer.

Manual reconciliation checked A/A.1 contrast and interface semantics, B primary versus broader scope, HOPE type map, source-defined versus operational-ready status, and absent-feature handling. Scientific source limitations and unresolved implementation choices remain in the source ledger and gates. No patient matrix, signature score, association, trained model, remote biological job or synthetic biological claim was produced. These checks validate the amendment's consistency and preserved bytes, not biological validity or independent review. Parent review/publication and updated PDF remain separate responsibilities.
