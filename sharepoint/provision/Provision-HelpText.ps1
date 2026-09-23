<#
.SYNOPSIS
    Provisionerer MD_HelpText - appernes hjaelpetekster.

.DESCRIPTION
    Hjaelpeteksterne stod i "Maintenance Plan App/build/build_help.py" og
    kunne kun rettes af den, der kunne bygge appen. Nu staar de i en liste,
    saa de kan rettes af dem, der kender fagligheden.

    TO SLAGS RAEKKER
        Kind = Hint     een linje under et felt. HelpKey er feltets navn
                        ("PlanType", "Plant", "Status" ...).
        Kind = Panel    et afsnit i det panel, ?-knappen folder ud. HelpKey
                        er sektionen ("plan", "item", "ops", "pkg"), og
                        SortOrder er raekkefoelgen i panelet.

    EN TOM RAEKKE ER INGEN TEKST
    Findes noeglen ikke, viser appen ingenting - der falder ikke noget
    tilbage paa en kopi i koden, for der ER ingen kopi. Det er med vilje:
    saa er det synligt, naar nogen har slettet en raekke.

    DE DYNAMISKE HINTS ER IKKE HER
    Syv af hintene er Power Fx og ikke tekst - de saetter fx vaerkskoden ind
    i beskeden og skifter efter, hvad brugeren har valgt. De bliver i koden.
    tools/check_helptext.py naegter at bygge, hvis den samme noegle staar
    begge steder.

    Scriptet er idempotent og kan koeres igen, naar der kommer nye kolonner.

.PARAMETER SiteUrl
    Url til det SharePoint-site, listen skal ligge paa.

.PARAMETER Seed
    Indlaeser sharepoint/seed/MD_HelpText.csv. Raekker, der findes i
    forvejen (samme HelpKey + Kind + SortOrder), OPDATERES ikke - de er
    SharePoints nu. Kun nye noegler laegges til.

.PARAMETER Force
    Med -Seed: overskriv ogsaa de raekker, der findes. Bruges kun, naar
    listen skal saettes tilbage til det, koden havde.

.EXAMPLE
    .\Provision-HelpText.ps1 -SiteUrl "https://orsted.sharepoint.com/sites/SAPMasterdata"

.EXAMPLE
    .\Provision-HelpText.ps1 -SiteUrl "https://..." -Seed

.NOTES
    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Seed,
    [switch] $Force,
    [string] $SeedPath,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Navnet skal vaere ORDRET det samme som L_HELP i sp_config.py.
$LIST_NAME = 'MD_HelpText'

# Title genbruges som noeglen. Den er obligatorisk i forvejen, saa der er
# ingen vej udenom at bruge den til noget fornuftigt. Power Fx binder paa
# VISNINGSNAVN - den samme streng staar som C_HELP_KEY i sp_config.py.
$COL_KEY = 'HelpKey'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\MD_HelpText.csv' }

# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

# --- listen ---------------------------------------------------------------
if (Get-PnPList -Identity $LIST_NAME -ErrorAction SilentlyContinue) {
    Write-Host "  = Liste '$LIST_NAME' findes allerede" -ForegroundColor DarkGray
} else {
    New-PnPList -Title $LIST_NAME -Template GenericList -OnQuickLaunch:$true | Out-Null
    Write-Host "  + Liste '$LIST_NAME' oprettet" -ForegroundColor Green
}
$DESC = 'Hjaelpetekster til masterdata-apperne. Kind=Hint er linjen under et felt, ' +
        'Kind=Panel er et afsnit i hjaelpepanelet. En slettet raekke betyder INGEN ' +
        'tekst i appen.'
Set-PnPList -Identity $LIST_NAME -Description $DESC

function New-HelpField {
    param([string]$Name, [string]$Type, [string[]]$Choices,
          [switch]$Indexed, [switch]$Required)
    if (Get-PnPField -List $LIST_NAME -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        $p = @{ List = $LIST_NAME; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    $values = @{}
    if ($Indexed)  { $values.Indexed  = $true }
    if ($Required) { $values.Required = $true }
    if ($values.Count) { Set-PnPField -List $LIST_NAME -Identity $Name -Values $values }
}

Write-Host "  Kolonner:" -ForegroundColor Cyan
Set-PnPField -List $LIST_NAME -Identity 'Title' -Values @{ Title = $COL_KEY; Indexed = $true }

# Samme vaerdier som Domain i MD_RequestIndex, saa de fem apps kan dele
# listen uden at laese hinandens tekster.
# Samme vaerdier som Domain i MD_RequestIndex. Kommaet fortsaetter selv
# linjen - en backtick er baade overfloedig og let at braekke.
$APP_AREAS = 'FunctionalLocation','Equipment','MeasuringPoint','Material',
             'MaintenancePlan'
New-HelpField 'AppArea' Choice -Choices $APP_AREAS -Indexed -Required
New-HelpField 'Kind'      Choice -Choices 'Hint','Panel' -Required
New-HelpField 'Heading'   Text
# Note, ikke Text: et panelafsnit er 2-4 saetninger og sprang 255 tegn.
New-HelpField 'Body'      Note -Required
New-HelpField 'SortOrder' Number

# Flersidet ren tekst. Uden det gemmer SharePoint HTML, og appen ville
# vise <div>-maerker midt i hjaelpeteksten.
Set-PnPField -List $LIST_NAME -Identity 'Body' -Values @{ RichText = $false; NumberOfLines = 6 }

# --- seed -----------------------------------------------------------------
if ($Seed) {
    if (-not (Test-Path $SeedPath)) {
        throw "Finder ikke $SeedPath. Koer 'python3 tools/gen_helptext_seed.py' foerst."
    }
    Write-Host "  Seed fra $SeedPath" -ForegroundColor Cyan
    $rows = Import-Csv -Path $SeedPath -Encoding UTF8
    $existing = Get-PnPListItem -List $LIST_NAME -PageSize 500
    $index = @{}
    foreach ($it in $existing) {
        $k = '{0}|{1}|{2}' -f $it['Title'], $it['Kind'], $it['SortOrder']
        $index[$k] = $it
    }
    $added = 0; $kept = 0; $updated = 0
    foreach ($r in $rows) {
        $k = '{0}|{1}|{2}' -f $r.HelpKey, $r.Kind, $r.SortOrder
        $values = @{
            Title     = $r.HelpKey
            AppArea   = $r.AppArea
            Kind      = $r.Kind
            Heading   = $r.Heading
            Body      = $r.Body
            SortOrder = [int]$r.SortOrder
        }
        if ($index.ContainsKey($k)) {
            if ($Force) {
                Set-PnPListItem -List $LIST_NAME -Identity $index[$k].Id -Values $values | Out-Null
                $updated++
            } else {
                $kept++
            }
        } else {
            Add-PnPListItem -List $LIST_NAME -Values $values | Out-Null
            $added++
        }
    }
    $msg = "    {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
    Write-Host $msg -ForegroundColor Green
    if ($kept -and -not $Force) {
        Write-Host "    Raekker, der fandtes i forvejen, er IKKE rettet." -ForegroundColor DarkGray
        Write-Host "    De er SharePoints nu. Skal de tilbage til det, koden" -ForegroundColor DarkGray
        Write-Host "    havde: koer igen med -Force." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Faerdig. Naeste skridt:" -ForegroundColor Cyan
Write-Host "  1. Koer sharepoint/inspect/Export-ListSchema.ps1, saa skemaet kender listen"
Write-Host "  2. python3 tools/build_all.py"
