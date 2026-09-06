# Paper B measurement checkpoint — Sol fix disposition

6 September 2026. Bounded follow-up to `docs/reviews/B_MEASUREMENT_SOL_REVIEW.md`. No commit or push; parent Astra owns final review and publication.

## Outcome

All concrete evidence-packaging findings from the Sol review are resolved in the working tree. Scientific choices remain unchanged: neither B-P nor B-R is selected; final U, Q and eligible N remain open; no biological score, association or model was run. This repair does not establish AIU validation or the outstanding final Opus recheck.

## Finding dispositions

| Original finding | Disposition |
|---|---|
| Missing `B_measurement/ARTIFACTS.json` | Resolved. The new manifest inventories all31 retained files except itself with exact bytes, SHA-256 and roles, plus17 omitted dependencies with exact paths/hashes and consumers. A complete programmatic recount found31 declared/31 actual and zero errors. |
| Copied helpers lacked an exact restore contract | Resolved. `B_measurement/README.md` states the historical-snapshot boundary and exact original-layout commands, input locations, generated intermediates and cache dependencies. |
| TCGA cache reuse overwrote `retrieved_utc` | Resolved. `retrieve.py` now preserves the existing retrieval timestamp, adds `verified_utc`, validates the expected/body/receipt digests and URL, rejects cached bodies without receipts, and accepts an explicit output root. `retrieve_original_20260906.py` is byte-identical to the original helper (SHA-256 `39a5bd4bf7b9347207e81181ef162daae319c41818f5449a752562ee73baed94`). The historical `retrieval.json` remained byte-identical and was not rewritten. |
| Expression/promoter peer receipts absent | Resolved. `EXPRESSION_REVIEW.md` and `PROMOTER_REVIEW.md` were copied into their subject folders byte-identically; hashes are `4a3f5fd4bfb27e1c2990c72ed5912d140bd7f1338fee74345eaa5e1c55663ca7` and `f3b75087b2e3bac29e520a8de75fe3c589ee2a6ade185f740ef47fba14c08966`. The checkpoint now links both. |
| Audit-time reports said artifacts remained outside Git | Resolved without altering the hashed reports. The package wrapper identifies those sentences as audit-time statements and distinguishes copied files from omitted outer-cache inputs. |
| “Verified contracts” overstated source evidence | Resolved in all six affected spec headers: they now say verified source facts refine proposed contracts. |
| Manufacturer promoter category read as selected | Resolved. `DATA_AND_SOURCES.md` now presents manufacturer-category, source-label and positive-CDS-span rules as distinct unselected options. |
| Stale source-manifest snapshot label | Resolved with a 6 September measurement-checkpoint label that keeps scientific choices open. |
| Reported CRLF trailing-whitespace defect | Disposed as a Windows line-ending false positive. `git -c core.whitespace=cr-at-eol diff --check HEAD` passes. No hashed audit artifact was normalized merely to silence the default check. |
| Possible mysterious names in historical `audit.py` | Retained as a byte-identical historical helper, explicitly not a production command. Renaming it would break snapshot identity without improving this checkpoint's scientific readiness. |

## Diagnosis and regression evidence

The minimal pre-fix synthetic-cache test reproduced the exact defect: a receipt containing `retrieved_utc=2026-09-05T23:31:00+00:00` was rewritten to the current time during cache reuse. The correct hypothesis was the unconditional receipt reconstruction; the hard-coded output root also prevented safe isolated testing, while missing digest enforcement allowed unverifiable cache state.

`docs/research/B_measurement/B_TCGA_cellularity/test_retrieve_cache.py` exercises the real fixed CLI against disposable cache directories under the writable checkpoint folder. Its URLs use the reserved invalid `.test` domain, and every case starts with a cached body, so no network path is taken. It checks:

1. cache reuse preserves `retrieved_utc` and adds `verified_utc`;
2. expected-digest mismatch fails without rewriting the receipt;
3. receipt/body digest disagreement fails without rewriting the receipt; and
4. a cached body without a receipt fails without network or mutation.

## Actual verification

```text
python -B docs/research/B_measurement/B_TCGA_cellularity/test_retrieve_cache.py
....
Ran 4 tests in 1.843s
OK

python -B docs/research/B_measurement/B_TCGA_cellularity/test_retrieve_cache.py
....
Ran 4 tests in 1.856s
OK
```

- `retrieve.py --help`: exit0 and exposes explicit output/source/hash arguments without source access.
- JSON parse:13/13 parsed (`ARTIFACTS.json`, all other checkpoint JSON files, and `specs/B/SOURCE_MANIFEST.json`).
- Artifact recount:31 retained declared,31 retained actual,17 omitted dependencies checked,0 missing/extra/byte/hash errors.
- Byte identity: both copied peer receipts, the original retrieval-helper snapshot and historical `retrieval.json` match their outer originals.
- Wording scan:0 old “verified platform, promoter and cellularity contracts” headers; the promoter policy is explicitly unselected.
- Scientific-state scan: `final_U_frozen=false`, `promoter_policy_frozen=false`, `final_eligible_N=null`, and the checkpoint still states neither B-P nor B-R is selected.
- `git -c safe.directory=E:/Master_Thesis/master-thesis -c core.whitespace=cr-at-eol diff --check HEAD`: PASS.
- Cleanup:0 temporary cache directories and0 `[DEBUG-...]` markers remain.

## Remaining gates not changed by this repair

Parent Astra must still perform final integration review and publication synchronization. The previously listed scientific gates—primary choice, U/Q freeze, specimen/aliquot policy, Qpure/ABSOLUTE strategy, final eligible N/precision/inference, then reviewed AIU implementation—and the final Opus recheck remain open.
