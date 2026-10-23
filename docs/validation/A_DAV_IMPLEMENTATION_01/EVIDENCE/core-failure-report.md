# DAV core malformed-input failure-path fix

## Scope

Changed only `tools/a_dav/core.py` and `tests/a_dav_implementation/test_core.py` for the implementation and regression coverage. Added this report and focused command logs under `.superpowers/implement/2026-10-23-dav-all/` as requested.

## Change

- `check_packet` now validates the branch as a string before checking the fixed branch enum. Invalid or unhashable branch values produce `UNSUPPORTED_BRANCH`.
- `finish` computes the config digest independently and substitutes the fixed SHA-256 digest of canonical JSON `null` only when canonicalization rejects the config. The input digest keeps its existing fallback behavior. Valid configs retain their ordinary config hash.
- `finish` includes a branch ID only when it is a member of the fixed enum; malformed branch values become `None` in the sealed receipt.
- Added decorated-stage regressions for NaN, set, bytes, cyclic config, and an invalid list branch, plus direct `finish` fallback coverage. Stage failures are checked for empty records, false release flags, and a verifiable receipt.

The malformed-payload fallback catches the canonicalization `DavError`; the change does not broaden the stage boundary to swallow arbitrary programmer exceptions.

## Results

- RED regression run: four expected failures before the fix. See `core-failure-red.log`.
- Focused core tests: `10 passed in 11.84s`. See `core-failure-green.log`.
- Strict mypy on `tools/a_dav/core.py`: `Success: no issues found in 1 source file`. See `core-failure-mypy.log`.

Commands used:

```sh
/private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -q -p no:cacheprovider tests/a_dav_implementation/test_core.py
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --explicit-package-bases --ignore-missing-imports --follow-imports=silent tools/a_dav/core.py
```
