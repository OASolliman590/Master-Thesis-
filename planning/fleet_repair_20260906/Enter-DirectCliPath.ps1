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
$claudePackageCandidates = @()
$winGetPackageRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
if (Test-Path -LiteralPath $winGetPackageRoot -PathType Container) {
    $claudePackageCandidates = Get-ChildItem -LiteralPath $winGetPackageRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'Anthropic.ClaudeCode_*' } |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object { Join-Path $_.FullName 'claude.exe' }
}

$claudePath = Get-FirstDirectCliCandidate -Candidates @(
    $claudeCommandPath
    (Join-Path $env:USERPROFILE '.local\bin\claude.exe')
    $claudePackageCandidates
)

$grokCommand = Get-Command grok.exe -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$grokCommandPath = if ($grokCommand) { $grokCommand.Source } else { $null }
$grokPath = Get-FirstDirectCliCandidate -Candidates @(
    $grokCommandPath
    (Join-Path $env:USERPROFILE '.local\bin\grok.exe')
    (Join-Path $env:USERPROFILE '.grok\bin\grok.exe')
)

$resolved = @(
    [pscustomobject]@{ Name = 'claude'; Path = $claudePath }
    [pscustomobject]@{ Name = 'grok'; Path = $grokPath }
)

$pathSegments = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]($env:Path -split ';' | Where-Object { $_ }),
    [System.StringComparer]::OrdinalIgnoreCase
)

foreach ($cli in $resolved) {
    if (-not $cli.Path) {
        Write-Warning "$($cli.Name) executable was not found."
        continue
    }

    $cliDirectory = Split-Path -Parent $cli.Path
    if ($pathSegments.Add($cliDirectory)) {
        $env:Path = "$cliDirectory;$env:Path"
    }
}

if ($claudePath) {
    $env:CLAUDE_DIRECT_EXE = $claudePath
}
if ($grokPath) {
    $env:GROK_DIRECT_EXE = $grokPath
}

$resolved | Format-Table -AutoSize
