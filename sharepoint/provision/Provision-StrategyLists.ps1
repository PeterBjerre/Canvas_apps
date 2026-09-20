<#
.SYNOPSIS
    Opretter MD_Strategy og MD_StrategyPackage, og indlaeser strategierne
    fra SAP-udtraekket.

.DESCRIPTION
    Strategipakkerne findes ikke i SharePoint i dag - StandardStrategyList
    har kun en Title, hvor pakkestrukturen staar som fritekst i navnet.
    Se docs/09-datamodel-fund.md 4 og docs/10-datamodel-forslag.md 4.

    Dette script opretter begge lister. MD_Strategy fyldes med de 53
    strategier fra sharepoint/seed/MD_Strategy.csv. MD_StrategyPackage
    oprettes TOM - pakkerne hentes fra SAP (IP11) senere.

    Idempotent: eksisterende lister, kolonner og raekker springes over, saa
    scriptet kan koeres igen, naar der kommer flere strategier.

    Hierarchical saettes IKKE af scriptet. Alle raekker faar
    "Ikke afklaret", og feltet udfyldes i haanden i SharePoint. Et forkert
    default ville forplante sig hele vejen til SAP, uden at nogen opdagede
    det. Scriptet skriver til sidst, hvor mange der mangler.

.PARAMETER SiteUrl
    Sitet listerne skal ligge paa.

.PARAMETER SeedPath
    Sti til csv'en. Standard: ..\seed\MD_Strategy.csv

.PARAMETER SkipSeed
    Opret kun listerne, indlaes ikke strategierne.

.EXAMPLE
    .\Provision-StrategyLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        9bc3ab49-b65d-410a-85ad-de819febfddc
    Saet PNP_CLIENT_ID som miljoevariabel, eller giv -ClientId.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $SeedPath,
    [string] $PackageSeedPath,
    [switch] $SkipSeed,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\MD_Strategy.csv' }
if (-not $PackageSeedPath) { $PackageSeedPath = Join-Path $PSScriptRoot '..\seed\MD_StrategyPackage.csv' }

$conn = @{ Url = $SiteUrl; Interactive = $true }
# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Uden et fejler MSAL med "User canceled
# authentication" - hvilket lyder som om brugeren trykkede fortryd, men
# ikke er det. Her stod "if ($ClientId) { ... }", saa scriptet koerte
# videre uden. Nu er der en standard.
# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
$conn.ClientId = $ClientId
Connect-PnPOnline @conn

function New-MdList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
    Set-PnPList -Identity $Title -Description $Description
}

function New-MdField {
    param([string]$List, [string]$Name, [string]$Type, [string[]]$Choices,
          [switch]$Indexed, [switch]$Required)
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    $v = @{}
    if ($Indexed)  { $v.Indexed  = $true }
    if ($Required) { $v.Required = $true }
    if ($v.Count) { Set-PnPField -List $List -Identity $Name -Values $v }
}

# ---------------------------------------------------------------------------
# MD_Strategy
# ---------------------------------------------------------------------------
Write-Host "`n=== MD_Strategy ===" -ForegroundColor Cyan
New-MdList 'MD_Strategy' 'Vedligeholdsstrategier fra SAP (IP11). Title = SAP-strateginoeglen.'

# Title ER SAP-noeglen (100, 101, ...). Derfor indekseret - appen slaar op paa den.
Set-PnPField -List 'MD_Strategy' -Identity 'Title' -Values @{ Title = 'StrategyKey'; Indexed = $true }

New-MdField 'MD_Strategy' 'StrategyName' Text -Required

# Tid eller taeller. Gaettet ud fra strateginavnet i csv'en - efterproev mod IP11.
New-MdField 'MD_Strategy' 'SchedulingIndicator' Choice -Choices 'TIME','TIME_FACTOR','PERFORMANCE'

# Det felt, der skal saettes i haanden. Tre vaerdier og ikke ja/nej, saa en
# strategi, ingen har taget stilling til, ikke ligner et bevidst "nej".
New-MdField 'MD_Strategy' 'Hierarchical' Choice -Choices 'Ja','Nej','Ikke afklaret'

# Saettes, naar strategiens pakker er indlaest. Appen maa kun tilbyde
# strategier, hvor den er sand - ellers vaelger brugeren en strategi uden
# pakker, og matricen staar tom.
New-MdField 'MD_Strategy' 'PackagesLoaded' Boolean

New-MdField 'MD_Strategy' 'Notes' Note

# ---------------------------------------------------------------------------
# MD_StrategyPackage - oprettes tom
# ---------------------------------------------------------------------------
Write-Host "`n=== MD_StrategyPackage ===" -ForegroundColor Cyan
New-MdList 'MD_StrategyPackage' 'Pakker pr. strategi (SAP IP11). Fyldes naar pakkerne er hentet.'

# Title bruges ikke til noget her - noeglen er StrategyKey + PackageNo.
Set-PnPField -List 'MD_StrategyPackage' -Identity 'Title' -Values @{ Title = 'PackageLabel' }

New-MdField 'MD_StrategyPackage' 'StrategyKey'  Text -Indexed -Required
New-MdField 'MD_StrategyPackage' 'PackageNo'    Number -Required
New-MdField 'MD_StrategyPackage' 'ShortCode'    Text      # M1, M3, ...
New-MdField 'MD_StrategyPackage' 'CycleLength'  Number
New-MdField 'MD_StrategyPackage' 'CycleUnit'    Choice -Choices 'H','DAY','WK','MON','YR','COUNT'
# Hoejere tal = mere omfattende. Afgoer hvem der kalder, naar flere
# pakker forfalder samme dag.
New-MdField 'MD_StrategyPackage' 'Hierarchy'    Number
New-MdField 'MD_StrategyPackage' 'PackageText'  Text
New-MdField 'MD_StrategyPackage' 'OffsetValue'  Number

# ---------------------------------------------------------------------------
# Indlaesning
# ---------------------------------------------------------------------------
if (-not $SkipSeed) {
    Write-Host "`n=== Indlaeser strategier ===" -ForegroundColor Cyan
    if (-not (Test-Path $SeedPath)) {
        throw "Finder ikke $SeedPath. Koer 'python3 tools/gen_strategy_seed.py' foerst."
    }

    # Csv'en er UTF-8 MED BOM. Uden den laeser PowerShell 5.1 den som
    # Windows-1252, og "Taeller" bliver til noget andet i SharePoint.
    $seed = Import-Csv -Path $SeedPath -Encoding UTF8

    # Eet opslag i stedet for eet pr. raekke.
    $existing = @{}
    foreach ($it in (Get-PnPListItem -List 'MD_Strategy' -PageSize 500)) {
        $existing[[string]$it.FieldValues.Title] = $it.Id
    }

    $added = 0; $skipped = 0
    foreach ($r in $seed) {
        if ($existing.ContainsKey($r.Title)) { $skipped++; continue }
        Add-PnPListItem -List 'MD_Strategy' -Values @{
            Title               = $r.Title
            StrategyName        = $r.StrategyName
            SchedulingIndicator = $r.SchedulingIndicator
            Hierarchical        = $r.Hierarchical
            PackagesLoaded      = [bool]::Parse($r.PackagesLoaded)
            Notes               = $r.Notes
        } | Out-Null
        $added++
    }
    Write-Host "  + $added oprettet, = $skipped fandtes i forvejen" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Pakker
# ---------------------------------------------------------------------------
# Noeglen er StrategyKey + PackageNo, ikke Title. En strategi faar
# PackagesLoaded = sand, saa snart den har mindst een pakke - det er det,
# appen bruger til at maerke de strategier, der endnu ikke kan bruges.
if (-not $SkipSeed -and (Test-Path $PackageSeedPath)) {
    Write-Host "`n=== Indlaeser pakker ===" -ForegroundColor Cyan
    $pkgSeed = Import-Csv -Path $PackageSeedPath -Encoding UTF8

    # Noeglen er StrategyKey + PackageNo. En raekke der findes i forvejen,
    # OPDATERES i stedet for at blive sprunget over: saa retter en rettelse
    # i csv'en ogsaa listen, naar scriptet koeres igen. Sprang vi den over,
    # ville en forkert vaerdi blive liggende for evigt.
    $havePkg = @{}
    foreach ($it in (Get-PnPListItem -List 'MD_StrategyPackage' -PageSize 500)) {
        $havePkg["$($it.FieldValues.StrategyKey)|$($it.FieldValues.PackageNo)"] = $it.Id
    }

    $pAdded = 0; $pUpdated = 0; $pSame = 0
    $touched = @{}
    foreach ($r in $pkgSeed) {
        $touched[$r.StrategyKey] = $true
        $vals = @{
            Title       = $r.Title
            StrategyKey = $r.StrategyKey
            PackageNo   = [int]$r.PackageNo
            ShortCode   = $r.ShortCode
            CycleLength = [int]$r.CycleLength
            CycleUnit   = $r.CycleUnit
            Hierarchy   = [int]$r.Hierarchy
            PackageText = $r.PackageText
            OffsetValue = [int]$r.OffsetValue
        }
        $existingId = $havePkg["$($r.StrategyKey)|$($r.PackageNo)"]
        if ($existingId) {
            # En TAVS overskrivning er farlig: har nogen rettet direkte i
            # listen, ruller csv'en rettelsen tilbage, uden at det kan ses.
            # Derfor listes hvert felt, der faktisk aendrer sig - og med
            # -WhatIfOnly skrives det uden at der roeres ved noget.
            $cur = (Get-PnPListItem -List 'MD_StrategyPackage' -Identity $existingId).FieldValues
            $diff = @()
            foreach ($k in $vals.Keys) {
                $now = $cur[$k]
                if ($now -is [Microsoft.SharePoint.Client.FieldLookupValue]) { $now = $now.LookupValue }
                if ("$now" -ne "$($vals[$k])") { $diff += "$k '$now' -> '$($vals[$k])'" }
            }
            if ($diff.Count -eq 0) {
                $pSame++
            } else {
                $mark = if ($WhatIfOnly) { '?' } else { '~' }
                Write-Host "    $mark $($r.StrategyKey)-$($r.PackageNo): $($diff -join '; ')" -ForegroundColor Yellow
                if (-not $WhatIfOnly) {
                    Set-PnPListItem -List 'MD_StrategyPackage' -Identity $existingId -Values $vals | Out-Null
                }
                $pUpdated++
            }
        } else {
            if ($WhatIfOnly) {
                Write-Host "    ? ville oprette $($r.StrategyKey)-$($r.PackageNo)" -ForegroundColor Yellow
            } else {
                Add-PnPListItem -List 'MD_StrategyPackage' -Values $vals | Out-Null
            }
            $pAdded++
        }
    }
    $verb = if ($WhatIfOnly) { "ville blive" } else { "er" }
    Write-Host "  $pAdded oprettet, $pUpdated $verb aendret, $pSame uaendret" -ForegroundColor Green

    # Saet PackagesLoaded paa de strategier, der nu HAR pakker.
    $marked = 0
    foreach ($it in (Get-PnPListItem -List 'MD_Strategy' -PageSize 500)) {
        $key = [string]$it.FieldValues.Title
        if (-not $touched.ContainsKey($key)) { continue }
        if ($it.FieldValues.PackagesLoaded -eq $true) { continue }
        Set-PnPListItem -List 'MD_Strategy' -Identity $it.Id `
                        -Values @{ PackagesLoaded = $true } | Out-Null
        $marked++
        Write-Host "    ~ strategi $key markeret som klar" -ForegroundColor Green
    }
    if (-not $marked) { Write-Host "    ingen strategier skiftede status" -ForegroundColor DarkGray }
}

# ---------------------------------------------------------------------------
$unresolved = @(Get-PnPListItem -List 'MD_Strategy' -PageSize 500 |
    Where-Object { $_.FieldValues.Hierarchical -ne 'Ja' -and $_.FieldValues.Hierarchical -ne 'Nej' })

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($unresolved.Count) {
    Write-Host "$($unresolved.Count) strategier mangler Hierarchical." -ForegroundColor Yellow
    Write-Host "  Aabn MD_Strategy og saet Ja/Nej. Scriptet gaetter det ikke -"
    Write-Host "  et forkert default ville foelge med hele vejen til SAP."
}
Write-Host "`nNaeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Efterproev SchedulingIndicator mod IP11. Den er udledt af"
Write-Host "     strateginavnet (begynder det med 'Taeller' eller 'T.'"
Write-Host "     = PERFORMANCE), ikke laest i SAP."
Write-Host "  2. Saet Hierarchical paa de strategier, der skal kunne vaelges."
Write-Host "  3. Naar flere strategiers pakker er hentet: laeg dem i"
Write-Host "     sharepoint/seed/MD_StrategyPackage.csv og koer scriptet igen."
Write-Host "     PackagesLoaded saettes automatisk."
Write-Host "  4. Tilfoej begge lister som datakilder i appen, og GEM i Studio."
