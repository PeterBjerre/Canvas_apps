<#
.SYNOPSIS
    Hent solution BIO SAP ned som laesbare filer - flows, miljoevariabler,
    connection references - og rens den, foer den committes.

.DESCRIPTION
    Kaeden er:

        pac auth create     log ind i miljoeet (kun foerste gang)
        pac solution list   find solutionens UNIKKE navn
        pac solution clone  hent den udpakket ned i .\solution
        scrub_solution.py   fjern hemmeligheder FOER git ser dem

    Eksporten er LAESESTOF. De to canvas apps bygges stadig af Python-
    builderne i hver app-mappe - .msapp-filerne i eksporten er et
    oejebliksbillede, ikke en kilde. Se docs/22-solution-eksport.md.

.PARAMETER Solution
    Solutionens unikke navn (ikke visningsnavnet). Kender du det ikke, saa
    koer med -List foerst.

.PARAMETER List
    Vis solutions i miljoeet og stop. Brug den til at finde det unikke navn.

.PARAMETER Environment
    Miljoeets id. Standard er det, der staar i tools/canvas_apps.json.

.PARAMETER OutputDirectory
    Hvor eksporten lander. Standard: .\solution

.PARAMETER ReportOnly
    Hent ned, men ret ingenting - vis kun hvad rensningen ville fjerne.

.EXAMPLE
    .\tools\export_solution.ps1 -List
    .\tools\export_solution.ps1 -Solution BIOSAP
#>
[CmdletBinding()]
param(
    [string]$Solution,
    [switch]$List,
    [string]$Environment,
    [string]$OutputDirectory = "solution",
    [switch]$ReportOnly,
    [switch]$SkipAuth
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    # --- miljoe-id fra konfigurationen, saa det staar eet sted ------------
    if (-not $Environment) {
        $cfgPath = Join-Path $PSScriptRoot "canvas_apps.json"
        if (Test-Path $cfgPath) {
            $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
            $Environment = $cfg.environment_id
        }
    }
    if (-not $Environment) {
        throw "Intet miljoe-id. Angiv -Environment, eller saet environment_id i tools/canvas_apps.json"
    }

    # --- pac: installeret, eller hentet paa stedet med dnx ---------------
    $pacCmd = Get-Command pac -ErrorAction SilentlyContinue
    if ($pacCmd) {
        $exe = $pacCmd.Source
        $pre = @()
    }
    else {
        $dnx = Get-Command dnx -ErrorAction SilentlyContinue
        if ($dnx) {
            $exe = $dnx.Source
            $pre = @("Microsoft.PowerApps.CLI.Tool", "--yes")
        }
        else {
            $dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
            if (-not $dotnet) {
                throw ("Hverken pac, dnx eller dotnet findes i PATH. Installer .NET 10 SDK fra " +
                       "https://dotnet.microsoft.com/download/dotnet/10.0")
            }
            $exe = $dotnet.Source
            $pre = @("dnx", "Microsoft.PowerApps.CLI.Tool", "--yes")
        }
    }

    function Invoke-Pac {
        param([string[]]$PacArgs)
        & $exe @($pre + $PacArgs)
        if ($LASTEXITCODE -ne 0) {
            throw ("pac " + ($PacArgs -join " ") + " fejlede (exitkode $LASTEXITCODE)")
        }
    }

    # --- login ------------------------------------------------------------
    if (-not $SkipAuth) {
        Write-Host ""
        Write-Host "Logger ind i miljoeet $Environment ..." -ForegroundColor Cyan
        Invoke-Pac @("auth", "create", "--environment", $Environment)
    }

    if ($List) {
        Write-Host ""
        Write-Host "Solutions i miljoeet - brug kolonnen med det UNIKKE navn:" -ForegroundColor Cyan
        Invoke-Pac @("solution", "list")
        Write-Host ""
        Write-Host "Koer derefter:  .\tools\export_solution.ps1 -Solution <uniktnavn>"
        return
    }

    if (-not $Solution) {
        throw "Angiv -Solution <uniktnavn>. Kender du det ikke, saa koer med -List foerst."
    }

    # --- hent den ned -----------------------------------------------------
    $outAbs = Join-Path $root $OutputDirectory
    if (Test-Path $outAbs) {
        Write-Host ""
        Write-Host "Rydder $outAbs, saa eksporten er hel og ikke en blanding." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $outAbs
    }
    New-Item -ItemType Directory -Path $outAbs | Out-Null

    Write-Host ""
    Write-Host "Henter solution $Solution ..." -ForegroundColor Cyan
    Invoke-Pac @("solution", "clone", "--name", $Solution, "--outputDirectory", $outAbs)

    # --- rens FOER git ser den -------------------------------------------
    Write-Host ""
    Write-Host "Renser eksporten ..." -ForegroundColor Cyan
    $python = $null
    $pyArgs = @()
    foreach ($candidate in @("py", "python", "python3")) {
        $c = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($c) {
            $python = $c.Source
            if ($candidate -eq "py") { $pyArgs = @("-3") }
            break
        }
    }
    if (-not $python) { throw "Python blev ikke fundet i PATH - kan ikke rense eksporten." }

    $scrub = @($pyArgs + @((Join-Path $PSScriptRoot "scrub_solution.py"), $outAbs))
    if ($ReportOnly) { $scrub += "--report-only" }
    & $python @scrub
    $scrubCode = $LASTEXITCODE

    Write-Host ""
    if ($ReportOnly) {
        Write-Host "-ReportOnly: der er IKKE renset. Koer uden flaget, foer du committer." -ForegroundColor Yellow
    }
    else {
        Write-Host "Faerdig. Laes flow-definitionerne igennem, og commit saa:" -ForegroundColor Green
        Write-Host "  git add $OutputDirectory"
        Write-Host "  git commit -m ""Solution-eksport <dato>"""
    }
    exit $scrubCode
}
finally {
    Pop-Location
}
