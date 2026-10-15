# Reference-check development record

Before `contract_checks.py` existed, the 40 test cases failed explicitly at the missing-checker assertion. After the reference checker was added, all 40 passed. Two additional receipt/source-reference tests then exposed a receipt-schema mismatch and missing admitted-object/review-reference guards (one failure and one error). After the documented contract/guard correction, all 42 passed.

This is a local bounded test-development record, not real data or scientific validation. Full final fresh logs are retained. The inherited 50 compatibility tests had one schema-check failure during decision-ledger migration; the registry was converted to its required decision fields and freshly revalidated. No original experimental value was created by that migration.
