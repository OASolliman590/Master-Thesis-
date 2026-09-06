# Optional coding backends: bounded access check

User requested Grok, Antigravity Claude/Gemini and ZCode as optional coding backends after stopping expensive multi-layer delegation. No coding task or new agent was launched by this check. Only one implementer should work on any accepted ticket.

## Verified findings

- ZCode CLI 0.16.5 is installed at `C:\Program Files\ZCode\resources\glm\zcode.cjs`. The delegation package's Windows fallback only checks the per-user Programs directory. The project-local `Enter-OptionalCodingCli.ps1` sets the documented `ZCODE_CLI` override in the current process; no global configuration is modified.
- `node --max-old-space-size=4096 <bundle> doctor --json` passed using Node24.19.0. Earlier sandboxed help ran out of memory. A successful launch is not proof of model access.
- The installed CLI advertises `--max-turns` but rejects it. Do not rely on that flag for a cost limit in this build.
- Headless turn failed with trace `8944e5b4-a716-4741-92d3-227d43c0cf37`; the local structured log's underlying cause is `Model provider is missing an API key: zai` (`provider_not_configured`). Sanitized configuration inspection showed main `zai/glm-5.1`, configured model names `glm-5.1` and `glm-5.3`, and no inline API key. The actual failed turn establishes that no usable key resolved. No credentials were displayed or copied.
- The official `login --no-browser` command failed with `Error: fetch failed`; no completed login or model entitlement is claimed. Do not insert an API key or switch endpoints: whether CLI calls consume the user's reported included ZCode balance remains unverified. GLM-5.3-Flash selection is not verified.
- Antigravity `models` at the previously verified executable returned exit1: `Please sign in to view available models`. Historical Claude/Gemini identifiers do not establish current authenticated availability or remaining quota.
- Grok1.0.13 still launches. Its earlier same-day fixed-response authentication smoke succeeded; this check did not spend another model request or assert a new coding-quality result.

## Operating proposal

Sol High owns one bounded ticket and direct acceptance checks. Once access is verified, ZCode/GLM is the first candidate for implementation using the user's reported temporary allowance. Grok and Antigravity Claude/Gemini are optional alternatives, never automatically chained or run together. Claude scientific consultation is reserved for a concrete unresolved issue. No automatic paid fallback.

The existing approved fleet JSON remains unchanged because a working authenticated replacement has not been established. Spark is not restarted. The path helper is ready; ZCode authentication/network and Antigravity sign-in remain blocked. This record is a diagnosis and launcher fix, not a completed fleet activation or thesis result.

## Local documentation used

Installed `delegate-setup` schema and `zcode-delegate` dispatch reference document `ZCODE_CLI`/`--zcode-path`; installed ZCode `--help` and `doctor` provide the actual runtime contract. Installed `agy-delegate` requires a successful authenticated `agy models` check before dispatch. Current runtime observations take precedence over historical skill assumptions.
