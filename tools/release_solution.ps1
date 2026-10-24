<#
.SYNOPSIS
    Flyt solution BIO SAP fra DEV til PROD som managed - fra din egen PC,
    med dit eget login. Se docs/46-release-til-prod.md.

.DESCRIPTION
    Kaeden er:

        pac auth create             log ind (kun foerste gang, eller -SkipAuth)
        pac solution online-version saet versionen i DEV (kun med -Version)
        pac solution publish        publicer alt i DEV, saa eksporten er den nyeste
        pac solution export         hent en MANAGED zip ned i releases\<version>\
        pac solution list           laes versionen i PROD og stop, hvis den
                                    nye ikke er hoejere
        bekraeftelse                skriv PROD for at fortsaette
        pac solution import         importer i PROD med settings-filen

    Settings-filen baerer miljoevariablernes vaerdier og forbindelses-
    referencernes forbindelser til PROD. Den indeholder e-mailadresser og
    URL'er og maa ALDRIG ligge i repoet. Scriptet naegter at bruge en fil,
    git ville tage med. Lav den foerste gang med -NewSettings.

    SharePoint-listerne flyttes ikke her. Koer provisioning-scripts mod
    PROD-sitet foer importen, hvis releasen kraever nye kolonner.

.PARAMETER Solution
    Solutionens unikke navn. Standard: BIOSAP.

.PARAMETER SettingsFile
    Stien til settings-filen for PROD. Skal ligge uden for repoet (eller
    vaere ignoreret af git).

.PARAMETER Version
    Ny version, fx 1.2.0.0. Saettes paa solutionen i DEV foer eksporten.
    Uden den bruges DEV's nuvaerende version.

.PARAMETER NewSettings
    Eksporter fra DEV og skriv en tom settings-fil til -SettingsFile, som
    du udfylder. Importerer ikke.

.PARAMETER WhatIfOnly
    Eksporter og tjek alt, men importer IKKE i PROD.

.PARAMETER Check
    Koer Power Apps solution checker paa zip-filen foer importen.

.PARAMETER SourceEnvironment
    DEV-miljoeets id. Standard: environments.dev i tools/canvas_apps.json.

.PARAMETER TargetEnvironment
    PROD-miljoeets id. Standard: environments.prod i tools/canvas_apps.json.

.EXAMPLE
    .\tools\release_solution.ps1 -NewSettings -SettingsFile "$HOME\BioSap\settings.prod.json"
    .\tools\release_solution.ps1 -SettingsFile "$HOME\BioSap\settings.prod.json" -Version 1.2.0.0 -WhatIfOnly
    .\tools\release_solution.ps1 -SettingsFile "$HOME\BioSap\settings.prod.json" -Version 1.2.0.0
#>
[CmdletBinding()]
param(
    [string]$Solution = "BIOSAP",
    [Parameter(Mandatory = $true)][string]$SettingsFile,
    [string]$Version,
    [switch]$NewSettings,
    [switch]$WhatIfOnly,
    [switch]$Check,
    [string]$SourceEnvironment,
    [string]$TargetEnvironment,
    [switch]$SkipAuth
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$guid = '^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$'
# Relativ sti regnes fra den mappe, du koerer fra - derfor FOER Push-Location.
$settingsAbs = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SettingsFile)

function Get-ConfigEnvironment {
    param([string]$Name)
    $cfgPath = Join-Path $PSScriptRoot "canvas_apps.json"
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    $id = $cfg.environments.$Name.environment_id
    if (-not $id -or $id -notmatch $guid) {
        throw ("Miljoeet '$Name' har intet environment_id i tools/canvas_apps.json. " +
               "Udfyld det, eller angiv det med -" + $(if ($Name -eq 'dev') { 'SourceEnvironment' } else { 'TargetEnvironment' }))
    }
    return $id
}

# Versioner sammenlignes tal for tal: 1.10.0.0 er hoejere end 1.9.0.0.
function ConvertTo-VersionObject {
    param([string]$Text)
    $v = $null
    if ([version]::TryParse($Text, [ref]$v)) { return $v }
    throw "'$Text' er ikke et versionsnummer som 1.2.0.0"
}

Push-Location $root
try {
    if (-not $SourceEnvironment) { $SourceEnvironment = Get-ConfigEnvironment "dev" }
    if (-not $NewSettings -and -not $TargetEnvironment) { $TargetEnvironment = Get-ConfigEnvironment "prod" }
    if ($TargetEnvironment -and $TargetEnvironment -eq $SourceEnvironment) {
        throw "DEV og PROD er det samme miljoe ($SourceEnvironment). Stopper."
    }
    if ($Version) { ConvertTo-VersionObject $Version | Out-Null }

    # --- settings-filen maa aldrig kunne komme i git --------------------
    if ($settingsAbs.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        & git check-ignore -q -- $settingsAbs 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw ("Settings-filen ligger i repoet og er ikke ignoreret af git: $settingsAbs`n" +
                   "Laeg den uden for repoet, fx i `$HOME\BioSap\settings.prod.json")
        }
    }
    if ($NewSettings -and (Test-Path $settingsAbs)) {
        throw "Settings-filen findes allerede: $settingsAbs. Slet den eller vaelg en anden sti."
    }
    if (-not $NewSettings -and -not (Test-Path $settingsAbs)) {
        throw "Settings-filen findes ikke: $settingsAbs. Lav den foerst med -NewSettings."
    }

    # --- pac: installeret, eller hentet paa stedet med dnx ---------------
    # Samme opslag som tools/export_solution.ps1.
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

    # Versionen af solutionen i et miljoe, eller $null hvis den ikke er der.
    function Get-OnlineVersion {
        param([string]$Environment)
        $raw = & $exe @($pre + @("solution", "list", "--json", "--environment", $Environment))
        if ($LASTEXITCODE -ne 0) { throw "pac solution list fejlede i $Environment (exitkode $LASTEXITCODE)" }
        # pac skriver statuslinjer foer JSON'en - tag kun fra den foerste [.
        $text = ($raw -join "`n")
        $start = $text.IndexOf("[")
        if ($start -lt 0) { throw "pac solution list --json gav ingen JSON i $Environment" }
        $items = $text.Substring($start) | ConvertFrom-Json
        foreach ($item in $items) {
            $props = $item.PSObject.Properties
            $name = ($props | Where-Object { $_.Name -match 'UniqueName' } | Select-Object -First 1).Value
            if ($name -eq $Solution) {
                return ($props | Where-Object { $_.Name -match 'Version' } | Select-Object -First 1).Value
            }
        }
        return $null
    }

    # --- login ------------------------------------------------------------
    # Een profil med dit eget login; hvert kald naevner miljoeet selv.
    if (-not $SkipAuth) {
        Write-Host ""
        Write-Host "Logger ind (samme konto bruges til DEV og PROD) ..." -ForegroundColor Cyan
        Invoke-Pac @("auth", "create", "--environment", $SourceEnvironment)
    }

    # --- git: hvilken kode er det, der udrulles ---------------------------
    $commit = (& git rev-parse --short HEAD 2>$null)
    $dirty = (& git status --porcelain 2>$null)
    if ($dirty) {
        Write-Host ""
        Write-Host "Advarsel: der er uncommittede aendringer i repoet. Releasen kommer fra DEV, ikke fra filerne her," -ForegroundColor Yellow
        Write-Host "men noter dig, hvad der er deployet til DEV, der ikke er committet." -ForegroundColor Yellow
    }

    # --- version i DEV ----------------------------------------------------
    if ($Version) {
        Write-Host ""
        Write-Host "Saetter versionen paa $Solution i DEV til $Version ..." -ForegroundColor Cyan
        Invoke-Pac @("solution", "online-version", "--solution-name", $Solution,
                     "--solution-version", $Version, "--environment", $SourceEnvironment)
    }
    $devVersion = Get-OnlineVersion $SourceEnvironment
    if (-not $devVersion) { throw "Solutionen $Solution findes ikke i DEV ($SourceEnvironment)." }
    Write-Host "Version i DEV: $devVersion"

    # --- publicer og eksporter --------------------------------------------
    Write-Host ""
    Write-Host "Publicerer alle tilpasninger i DEV ..." -ForegroundColor Cyan
    Invoke-Pac @("solution", "publish", "--environment", $SourceEnvironment)

    # releases\ staar i .gitignore: en managed zip baerer DEV's nuvaerende
    # vaerdier for miljoevariablerne, og de hoerer ikke paa GitHub.
    $releaseDir = Join-Path $root (Join-Path "releases" $devVersion)
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
    $zip = Join-Path $releaseDir ("{0}_{1}_managed.zip" -f $Solution, ($devVersion -replace '\.', '_'))

    Write-Host ""
    Write-Host "Eksporterer $Solution $devVersion som managed ..." -ForegroundColor Cyan
    Invoke-Pac @("solution", "export", "--name", $Solution, "--path", $zip, "--managed",
                 "--overwrite", "--async", "--environment", $SourceEnvironment)

    if ($NewSettings) {
        $dir = Split-Path -Parent $settingsAbs
        if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        Invoke-Pac @("solution", "create-settings", "--solution-zip", $zip, "--settings-file", $settingsAbs)
        Write-Host ""
        Write-Host "Settings-filen er skrevet: $settingsAbs" -ForegroundColor Green
        Write-Host "Udfyld Value for hver miljoevariabel og ConnectionId for hver forbindelsesreference"
        Write-Host "med PROD-vaerdierne, og koer saa scriptet igen uden -NewSettings."
        return
    }

    # --- settings-filen skal vaere udfyldt helt ---------------------------
    # En tom vaerdi betyder, at PROD faar DEV's vaerdi fra zip-filen - eller
    # ingen. Begge dele skal stoppe releasen, ikke opdages af en bruger.
    $settings = Get-Content $settingsAbs -Raw | ConvertFrom-Json
    $missing = @()
    foreach ($ev in @($settings.EnvironmentVariables)) {
        if ($ev -and [string]::IsNullOrWhiteSpace([string]$ev.Value)) { $missing += "miljoevariabel $($ev.SchemaName)" }
    }
    foreach ($cr in @($settings.ConnectionReferences)) {
        if ($cr -and [string]::IsNullOrWhiteSpace([string]$cr.ConnectionId)) { $missing += "forbindelse $($cr.LogicalName)" }
    }
    # En skabelon fra den nye zip viser variabler og forbindelser, der er
    # kommet til siden settings-filen blev lavet.
    & $exe @($pre + @("solution", "create-settings", "--solution-zip", $zip,
                      "--settings-file", (Join-Path $releaseDir "settings.template.json"))) | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $tpl = Get-Content (Join-Path $releaseDir "settings.template.json") -Raw | ConvertFrom-Json
        $have = @($settings.EnvironmentVariables | ForEach-Object { $_.SchemaName })
        foreach ($ev in @($tpl.EnvironmentVariables)) {
            if ($ev -and $have -notcontains $ev.SchemaName) { $missing += "miljoevariabel $($ev.SchemaName) (ny i solutionen)" }
        }
        $haveCr = @($settings.ConnectionReferences | ForEach-Object { $_.LogicalName })
        foreach ($cr in @($tpl.ConnectionReferences)) {
            if ($cr -and $haveCr -notcontains $cr.LogicalName) { $missing += "forbindelse $($cr.LogicalName) (ny i solutionen)" }
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "Settings-filen mangler vaerdier:" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        throw "Udfyld $settingsAbs og koer igen."
    }

    # --- solution checker (valgfri) ---------------------------------------
    if ($Check) {
        Write-Host ""
        Write-Host "Koerer solution checker ..." -ForegroundColor Cyan
        Invoke-Pac @("solution", "check", "--path", $zip, "--geo", "Europe",
                     "--outputDirectory", (Join-Path $releaseDir "checker"))
    }

    # --- PROD: hvad staar der nu ------------------------------------------
    $prodVersion = Get-OnlineVersion $TargetEnvironment
    if ($prodVersion) {
        Write-Host "Version i PROD: $prodVersion"
        if ((ConvertTo-VersionObject $devVersion) -le (ConvertTo-VersionObject $prodVersion)) {
            throw "DEV's version $devVersion er ikke hoejere end PROD's $prodVersion. Koer igen med -Version <hoejere>."
        }
    }
    else {
        Write-Host "Version i PROD: ingen - det er foerste import."
    }

    $notes = @(
        "# Release $Solution $devVersion",
        "",
        "Skrevet af tools/release_solution.ps1 - ret ikke i haanden.",
        "",
        "| | |",
        "|---|---|",
        "| Dato | $(Get-Date -Format 'yyyy-MM-dd HH:mm') |",
        "| Version i DEV | $devVersion |",
        "| Version i PROD foer | $(if ($prodVersion) { $prodVersion } else { 'ingen' }) |",
        "| Git-commit | $commit$(if ($dirty) { ' (med uncommittede aendringer)' }) |",
        "| Zip | $(Split-Path -Leaf $zip) |",
        "| Udfoert af | $env:USERNAME |"
    )

    if ($WhatIfOnly) {
        Set-Content -Path (Join-Path $releaseDir "RELEASE.md") -Value ($notes + "| Resultat | -WhatIfOnly, ikke importeret |") -Encoding utf8
        Write-Host ""
        Write-Host "-WhatIfOnly: alt er tjekket, intet er importeret i PROD." -ForegroundColor Yellow
        Write-Host "Zip: $zip"
        return
    }

    # --- bekraeftelse -----------------------------------------------------
    Write-Host ""
    Write-Host "Klar til at importere $Solution $devVersion i PROD ($TargetEnvironment)." -ForegroundColor Yellow
    Write-Host "Har releasen nye kolonner eller lister, skal provisioning vaere koert mod PROD-sitet nu." -ForegroundColor Yellow
    $answer = Read-Host "Skriv PROD for at fortsaette"
    if ($answer -cne "PROD") {
        Write-Host "Afbrudt - intet er importeret."
        return
    }

    # --- import -----------------------------------------------------------
    # Findes solutionen allerede, opgraderes den: komponenter, der er
    # fjernet i DEV, slettes ogsaa i PROD. Ved foerste import er der intet
    # at opgradere.
    $importArgs = @("solution", "import", "--path", $zip, "--environment", $TargetEnvironment,
                    "--settings-file", $settingsAbs, "--activate-plugins", "--publish-changes",
                    "--async", "--max-async-wait-time", "60")
    if ($prodVersion) { $importArgs += "--stage-and-upgrade" }

    Write-Host ""
    Write-Host "Importerer i PROD ..." -ForegroundColor Cyan
    Invoke-Pac $importArgs

    $after = Get-OnlineVersion $TargetEnvironment
    Set-Content -Path (Join-Path $releaseDir "RELEASE.md") -Value ($notes + "| Version i PROD efter | $after |") -Encoding utf8

    Write-Host ""
    Write-Host "Faerdig: $Solution $after koerer i PROD." -ForegroundColor Green
    Write-Host "Aabn appen i PROD og tjek, at flows er slaaet til, og at appen er delt med brugerne."
    Write-Host "Zip og RELEASE.md ligger i $releaseDir - gem dem, de er det, du ruller tilbage til."
}
finally {
    Pop-Location
}
