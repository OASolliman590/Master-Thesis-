# Direct Claude Code and Grok repair report

## Outcome

Claude Code's direct launcher is repaired. The previously observed 2.1.260 path belonged to a still-running Claude desktop child process, but the file and its parent directory no longer existed, so it was not a reusable CLI installation. The official WinGet package `Anthropic.ClaudeCode` is now installed at version 2.1.263, its binary passes `--version`, its Authenticode signature is valid for Anthropic, PBC, and WinGet registered its package directory in the user PATH for future shells.

Grok did not need an executable repair. Both discovered launchers run version 1.0.13 and are byte-identical. The earlier alternate-launcher failure was not reproduced. A one-turn, no-tools-requested `AUTH_OK` request succeeded with exit 0, establishing that the existing Grok session is functionally authenticated.

Claude Code is not authenticated. This is the only remaining activation gate and requires the account owner to complete Anthropic's interactive sign-in. One fixed-response Grok authentication smoke was sent after its model-list output proved ambiguous; it was not a quality/model evaluation. No subscription or credit state was changed, and no token file, key, or cookie was read or copied.

## Exact executables and verified states

| Tool | Executable | Version | Launch | Authentication |
| --- | --- | --- | --- | --- |
| Claude Code | `C:\Users\salma\AppData\Local\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\claude.exe` | `2.1.263 (Claude Code)` | Pass, exit 0 | `claude auth status`: exit 1, `loggedIn=false`, `authMethod=none`, `apiProvider=firstParty` |
| Grok primary | `C:\Users\salma\.local\bin\grok.exe` | `grok 1.0.13 (5e9a58528b76) [stable]` | Pass, exit 0 | Functionally authenticated: no-tools-requested one-turn request returned `AUTH_OK`, exit 0 |
| Grok alternate | `C:\Users\salma\.grok\bin\grok.exe` | same | Pass, exit 0 | Same credential store as primary |

The two Grok files have the same SHA256, `6CAF906D6EF968004B5FF33422C84E33D51A1CD7B4EE5ACD19FF695AAA92672E`. The Claude SHA256 is `0B35DF94C1307004F07B738390BFEF8DFCA5E9AF29AAF6517F305BF086B95B03`; WinGet also reported successful installer-hash verification.

## Diagnosis

The tight probe is [`Test-DirectCli.ps1`](../../../planning/fleet_repair_20260906/Test-DirectCli.ps1). It requires successful version probes, Claude's structured auth status, and one fixed-response, no-tools-requested Grok request. Its current expected verdict is red only for Claude until interactive sign-in is completed.

Ranked hypotheses were tested as follows:

1. Claude executable outside PATH: partly true. A desktop-spawned 2.1.260 process exposed a historical path, but that path was stale and absent on disk. There was no current npm-global or WinGet CLI install.
2. Stale or wrong Grok launcher: false. Both Grok paths launch and are byte-identical.
3. Healthy installs but unauthenticated sessions: true for Claude after the launcher repair. Claude's own status reports false. Grok initially emitted a transient unauthenticated model-refresh warning, but a tighter functional check succeeded; Grok is authenticated.
4. Native Windows launcher failure: false for the directly invoked binaries. Both version probes pass.
5. Account entitlement failure: not testable before sign-in and remains an external account gate, especially for Grok Build access.

The initial sandboxed Grok probe was not accepted as evidence because the sandbox denied the CLI access to its own credential store. An outside-sandbox `grok models` run then produced a transient unauthenticated warning while still returning cached model names with exit 0, proving that this command was not a reliable positive-auth check. The final one-turn functional probe returned `AUTH_OK` and is the accepted verdict.

## Changes made

- Installed the official targeted WinGet package `Anthropic.ClaudeCode` 2.1.263. No fleet configuration was changed.
- Added [`Enter-DirectCliPath.ps1`](../../../planning/fleet_repair_20260906/Enter-DirectCliPath.ps1), a reversible current-session PATH bootstrap. It discovers the WinGet Claude package and the two supported Grok locations without hard-pinning a version directory.
- Added the secret-safe [`Test-DirectCli.ps1`](../../../planning/fleet_repair_20260906/Test-DirectCli.ps1) feedback loop.
- Added this report, [`evidence.json`](evidence.json), and [`SOURCES.md`](SOURCES.md).

The installer made one targeted user-environment change: it registered the Claude package directory in user PATH. The already-running Codex shell retains its old PATH snapshot. A fresh terminal will inherit the repaired PATH; the project-local bootstrap provides an immediate alternative.

## Non-blocking follow-up warnings

The Grok authentication smoke returned `AUTH_OK`, but its startup also reported two independent local-integration warnings:

- Git rejected `E:/Master_Thesis/master-thesis` as dubious ownership because the filesystem does not record ownership. Repository status was verified with the one-command override `git -c safe.directory=E:/Master_Thesis/master-thesis status`; no global Git setting was changed. A production Grok relay may need the same per-process override or a separately approved protected Git configuration.
- Grok attempted to start a configured `railway` MCP server and reported that the program was not found. This did not affect direct authentication. The fleet/MCP configuration was deliberately left unchanged under this task's ownership boundary.

There were 38 pre-existing or concurrent changed paths outside the two assigned repair directories; all were preserved without edits.

## Minimal remaining user action

Open a fresh PowerShell terminal in the canonical repository and run:

```powershell
cd E:\Master_Thesis\master-thesis
. .\planning\fleet_repair_20260906\Enter-DirectCliPath.ps1
claude auth login --claudeai
& .\planning\fleet_repair_20260906\Test-DirectCli.ps1
```

`claude auth login --claudeai` is the Claude-subscription route and is the appropriate default when using a Claude Pro/Max/Team/Enterprise account. If this machine should instead use API-billed Anthropic Console access, use `claude auth login --console`. Do not move credentials from the Claude desktop app, Antigravity, or another product.

The final test should exit 0 only when both CLIs have working direct authentication. It sends one fixed `AUTH_OK` request to Grok with subagents and web search disabled; this is an authentication check, not a model evaluation. If Grok later becomes unauthenticated, the documented recovery is `grok login` (or `grok login --device-auth` on a headless machine). If login succeeds but the functional probe still fails, the remaining issue is likely account/team entitlement or network policy; no credits should be purchased and no subscription should be altered without a separate user decision.

## Sources and boundaries

Official vendor sources and version-specific local help receipts are listed in [`SOURCES.md`](SOURCES.md). Detailed sanitized observations are in [`evidence.json`](evidence.json). No scientific analysis, repository fleet configuration, global application settings, commit, or push was performed.

## Astra review and independent recheck

The parent independently reran the two-launcher check on6 September2026: Claude2.1.263 launches but remains unauthenticated (auth exit1); Grok1.0.13 returned the expected fixed response (exit0). The combined test intentionally exits1 while Claude requires sign-in. Local Claude auth-login help verifies --claudeai as the subscription/default option.

Correction to the initial report: the Grok prompt requests no tools and disables subagents/web search, but plan/read-only mode does not technically disable every read tool or configured MCP startup. The probe is evidence of a successful authenticated response, not proof of total tool isolation or a production coding run. The original repair brief restricted global-setting changes; the official WinGet install additionally registered a user-PATH entry, as disclosed above. No further global change was made by the parent.
