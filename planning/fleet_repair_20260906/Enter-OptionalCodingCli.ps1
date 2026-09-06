[CmdletBinding()]
param()

# Dot-source this script. Changes apply only to the current PowerShell process.
$optionalZcodeCandidates = @(
    (Join-Path $env:ProgramFiles 'ZCode\resources\glm\zcode.cjs'),
    (Join-Path $env:LOCALAPPDATA 'Programs\ZCode\resources\glm\zcode.cjs')
)
$optionalZcodePath = $optionalZcodeCandidates | Where-Object {
    Test-Path -LiteralPath $_ -PathType Leaf
} | Select-Object -First 1
if ($optionalZcodePath) {
    $env:ZCODE_CLI = $optionalZcodePath
    Write-Output "ZCode relay bundle: $optionalZcodePath"
} else {
    Write-Warning 'ZCode bundle not found; do not dispatch.'
}

$optionalAgyPath = Join-Path $env:LOCALAPPDATA 'Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\agy\bin\agy.exe'
if (Test-Path -LiteralPath $optionalAgyPath -PathType Leaf) {
    $optionalAgyDirectory = Split-Path -Parent $optionalAgyPath
    if (($env:Path -split ';') -notcontains $optionalAgyDirectory) {
        $env:Path = "$optionalAgyDirectory;$env:Path"
    }
    Write-Output "Antigravity executable: $optionalAgyPath"
} else {
    Write-Warning 'Previously verified Antigravity CLI path is absent.'
}

$optionalGrokDirectory = Join-Path $env:USERPROFILE '.local\bin'
if ((Test-Path -LiteralPath (Join-Path $optionalGrokDirectory 'grok.exe')) -and
    (($env:Path -split ';') -notcontains $optionalGrokDirectory)) {
    $env:Path = "$optionalGrokDirectory;$env:Path"
}
# This script neither authenticates nor changes model/provider/fleet configuration.
