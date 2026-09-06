[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-FirstDirectCliCandidate {
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [AllowEmptyString()]
        [string[]]$Candidates
    )

    foreach ($candidate in $Candidates | Where-Object { $_ } | Select-Object -Unique) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Get-Item -LiteralPath $candidate).FullName
        }
    }

    return $null
}

$claudeCommand = Get-Command claude.exe -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$claudeCommandPath = if ($claudeCommand) { $claudeCommand.Source } else { $null }
$claudeDirectEnvPath = if (Test-Path Env:CLAUDE_DIRECT_EXE) { $env:CLAUDE_DIRECT_EXE } else { $null }
$claudePackageCandidates = @()
$winGetPackageRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
if (Test-Path -LiteralPath $winGetPackageRoot -PathType Container) {
    $claudePackageCandidates = Get-ChildItem -LiteralPath $winGetPackageRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'Anthropic.ClaudeCode_*' } |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object { Join-Path $_.FullName 'claude.exe' }
}

$claudePath = Get-FirstDirectCliCandidate -Candidates @(
    $claudeDirectEnvPath
    $claudeCommandPath
    (Join-Path $env:USERPROFILE '.local\bin\claude.exe')
    $claudePackageCandidates
)

$grokCommand = Get-Command grok.exe -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$grokCommandPath = if ($grokCommand) { $grokCommand.Source } else { $null }
$grokDirectEnvPath = if (Test-Path Env:GROK_DIRECT_EXE) { $env:GROK_DIRECT_EXE } else { $null }
$grokPath = Get-FirstDirectCliCandidate -Candidates @(
    $grokDirectEnvPath
    $grokCommandPath
    (Join-Path $env:USERPROFILE '.local\bin\grok.exe')
    (Join-Path $env:USERPROFILE '.grok\bin\grok.exe')
)

$claudeResult = [ordered]@{
    Name = 'claude'
    Path = $claudePath
    Version = $null
    VersionExitCode = $null
    AuthState = 'missing'
    AuthExitCode = $null
    AuthMethod = $null
    ApiProvider = $null
}

if ($claudePath) {
    $claudeVersionOutput = @(& $claudePath --version 2>&1)
    $claudeResult.VersionExitCode = $LASTEXITCODE
    $claudeResult.Version = $claudeVersionOutput -join "`n"

    $claudeAuthOutput = @(& $claudePath auth status 2>&1)
    $claudeResult.AuthExitCode = $LASTEXITCODE
    try {
        $claudeAuth = ($claudeAuthOutput -join "`n") | ConvertFrom-Json
        $claudeResult.AuthState = if ($claudeAuth.loggedIn) { 'authenticated' } else { 'unauthenticated' }
        $claudeResult.AuthMethod = $claudeAuth.authMethod
        $claudeResult.ApiProvider = $claudeAuth.apiProvider
    }
    catch {
        $claudeResult.AuthState = 'probe_failed'
    }
}

$grokResult = [ordered]@{
    Name = 'grok'
    Path = $grokPath
    Version = $null
    VersionExitCode = $null
    AuthState = 'missing'
    AuthExitCode = $null
}

if ($grokPath) {
    $grokVersionOutput = @(& $grokPath version 2>&1)
    $grokResult.VersionExitCode = $LASTEXITCODE
    $grokResult.Version = $grokVersionOutput -join "`n"

    # Grok 1.0.13 can return exit 0 and cached models while also reporting no auth.
    # A one-turn, no-tools-requested response is therefore the tight functional auth
    # check. Stderr is suppressed so credential-store paths and unrelated local
    # integration warnings are never emitted by this script.
    $grokModelsOutput = @(
        & $grokPath --no-auto-update --no-subagents --disable-web-search `
            --sandbox read-only --permission-mode plan --output-format json `
            --max-turns 1 -p 'Reply exactly AUTH_OK. Do not use tools.' 2>$null
    )
    $grokResult.AuthExitCode = $LASTEXITCODE
    $grokModelsText = $grokModelsOutput -join "`n"
    if ($grokModelsText -match 'not authenticated|No auth credentials|Run `grok login`') {
        $grokResult.AuthState = 'unauthenticated'
    }
    elseif ($grokResult.AuthExitCode -eq 0 -and $grokModelsText -match '"text"\s*:\s*"AUTH_OK"') {
        $grokResult.AuthState = 'authenticated'
    }
    else {
        $grokResult.AuthState = 'probe_failed'
    }
}

[pscustomobject]$claudeResult
[pscustomobject]$grokResult

$allReady = (
    $claudeResult.VersionExitCode -eq 0 -and
    $claudeResult.AuthState -eq 'authenticated' -and
    $grokResult.VersionExitCode -eq 0 -and
    $grokResult.AuthState -eq 'authenticated'
)

if (-not $allReady) {
    exit 1
}
