<#
.SYNOPSIS
    Byg og synkroniser en canvas app til Power Apps Studio - uden VS Code.

.DESCRIPTION
    Tynd skal omkring tools/canvas_mcp.py. Den tjekker forudsaetningerne
    (Python og .NET 10 SDK) foerst, saa fejlen kommer med det samme og med
    en besked, der siger hvad der mangler.

    Studio-fanen skal vaere aaben med coauthoring slaaet til
    (Settings -> Updates -> Coauthoring), mens scriptet koerer. Serveren
    taler med appen gennem netop den session.

.PARAMETER App
    Noeglen i tools/canvas_apps.json. Standard: vhplan.

.PARAMETER Command
    deploy (byg, compile, synk), pull (hent Studios tilstand), check,
    tools eller raw. Standard: deploy.

.EXAMPLE
    .\tools\Deploy-CanvasApp.ps1
    .\tools\Deploy-CanvasApp.ps1 -App vhplan -Command pull
    .\tools\Deploy-CanvasApp.ps1 -Rest @('--no-build','-v')
#>
[CmdletBinding()]
param(
    [string]$App = "vhplan",
    [ValidateSet("deploy", "pull", "check", "tools", "raw")]
    [string]$Command = "deploy",
    [string[]]$Rest = @()
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Python: py -3 paa de fleste Windows-maskiner, ellers python.
$python = $null
$pyArgs = @()
foreach ($candidate in @("py", "python", "python3")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        $python = $cmd.Source
        if ($candidate -eq "py") { $pyArgs = @("-3") } else { $pyArgs = @() }
        break
    }
}
if (-not $python) {
    throw "Python blev ikke fundet i PATH. Byggescripterne kraever Python 3."
}

# .NET 10 SDK - ikke kun runtime. Uden den starter MCP-serveren ikke.
$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    throw ("dotnet blev ikke fundet i PATH. Installer .NET 10 SDK fra " +
           "https://dotnet.microsoft.com/download/dotnet/10.0")
}
$sdks = & dotnet --list-sdks
$hasTen = $false
foreach ($line in $sdks) {
    if ($line -match '^(\d+)\.') {
        if ([int]$Matches[1] -ge 10) { $hasTen = $true }
    }
}
if (-not $hasTen) {
    Write-Warning ("Ingen .NET 10 SDK fundet. MCP-serveren kraever SDK'et " +
                   "(ikke kun runtime): https://dotnet.microsoft.com/download/dotnet/10.0")
}

$script = Join-Path $PSScriptRoot "canvas_mcp.py"
$argv = $pyArgs + @($script, $Command, "--app", $App) + $Rest

Write-Host ""
Write-Host "Husk: Studio-fanen skal vaere aaben med coauthoring slaaet til." -ForegroundColor Yellow
Write-Host ""

Push-Location $root
try {
    & $python @argv
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $code
