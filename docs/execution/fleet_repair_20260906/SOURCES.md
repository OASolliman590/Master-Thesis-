# Direct CLI repair sources

Accessed 6 September 2026.

- Anthropic, [Advanced setup for Claude Code](https://code.claude.com/docs/en/getting-started): native Windows support; official PowerShell, CMD and WinGet installation methods; `claude --version`, `claude doctor`, and browser authentication guidance. The page documents `winget install Anthropic.ClaudeCode` and notes that a new terminal may be required after PATH changes.
- xAI, [Grok Build CLI reference](https://docs.x.ai/build/cli/reference): `grok login`, `grok login --device-auth`, `grok models`, and the supported CLI surface.
- xAI, [Grok Build enterprise deployments](https://docs.x.ai/build/enterprise): supported authentication methods and precedence; browser OIDC via `grok login`, device code via `grok login --device-auth`, and `XAI_API_KEY` for API-key authentication.
- xAI, [Headless and scripting](https://docs.x.ai/build/cli/headless-scripting): `--no-auto-update` for automation and the unauthenticated failure instruction to run `grok login` or set `XAI_API_KEY`.

Local command help was also treated as a version-specific primary source:

- Claude Code 2.1.263: `claude auth --help` and `claude auth login --help`.
- Grok 1.0.13: `grok --help` and `grok login --help`.

No credential file, token, key, or cookie was read or copied while producing these receipts.
