<#
.SYNOPSIS
    Opretter MD_Strategy og MD_StrategyPackage, og indlaeser strategierne
    fra SAP-udtraekket.

.DESCRIPTION
    Strategipakkerne findes ikke i SharePoint i dag - StandardStrategyList
    har kun en Title, hvor pakkestrukturen staar som fritekst i navnet.
    Se docs/09-datamodel-fund.md 4 og docs/10-datamodel-forslag.md 4.

    Dette script opretter begge lister. MD_Strategy fyldes med de 67
    strategier fra sharepoint/seed/MD_Strategy.csv, og MD_StrategyPackage
    med de 238 pakker fra sharepoint/seed/MD_StrategyPackage.csv. Pakkerne
    laves af tools/gen_package_seed.py ud fra "Strategi pakker.xlsx".

    Idempotent: eksisterende lister, kolonner og raekker springes over, saa
    scriptet kan koeres igen, naar der kommer flere strategier.

    Hierarchical kommer fra csv'en, hvor tools/gen_strategy_seed.py udleder
    den af pakkernes hierarki. En strategi, der findes i forvejen, faar kun
    vaerdien, hvis den staar som "Ikke afklaret" - en vaerdi sat i haanden i
    SharePoint roeres ikke. Scriptet skriver til sidst, hvor mange der mangler.

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
        se MdDefaultClientId i _Common.psm1
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

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

# ---------------------------------------------------------------------------
# MD_Strategy
# ---------------------------------------------------------------------------
Write-Host "`n=== MD_Strategy ===" -ForegroundColor Cyan
New-MdList 'MD_Strategy' 'Vedligeholdsstrategier fra SAP (IP11). Title = SAP-strateginoeglen.'

# Title ER SAP-noeglen (100, 101, ...). Derfor indekseret - appen slaar op paa den.
Rename-MdTitle 'MD_Strategy' 'StrategyKey'

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
if (-not $WhatIfOnly) { Set-PnPField -List 'MD_StrategyPackage' -Identity 'Title' -Values @{ Title = 'PackageLabel' } }

New-MdField 'MD_StrategyPackage' 'StrategyKey'  Text -Indexed -Required
New-MdField 'MD_StrategyPackage' 'PackageNo'    Number -Required
New-MdField 'MD_StrategyPackage' 'ShortCode'    Text      # M1, M3, ...
New-MdField 'MD_StrategyPackage' 'CycleLength'  Number
New-MdField 'MD_StrategyPackage' 'CycleUnit'    Choice -Choices 'H','D','DAY','WK','MON','YR','COUNT'
# D (taellerdage) kom med "Strategi pakker.xlsx". New-MdField tilfoejer
# selv de valg, en eksisterende kolonne mangler (R2-012), saa den lokale
# rettelse, der stod her, er vaek (R2-060).
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
    foreach ($it in $(if (Test-MdList 'MD_Strategy') { Get-PnPListItem -List 'MD_Strategy' -PageSize 500 })) {
        $existing[[string]$it.FieldValues.Title] = $it
    }

    $added = 0; $skipped = 0; $hierSet = 0
    foreach ($r in $seed) {
        if ($existing.ContainsKey($r.Title)) {
            $skipped++
            # Kun "Ikke afklaret" (eller tom) udfyldes. Ja/Nej sat i haanden
            # i SharePoint vinder over csv'en.
            $it  = $existing[$r.Title]
            $cur = [string]$it.FieldValues.Hierarchical
            if (($cur -ne 'Ja' -and $cur -ne 'Nej') -and ($r.Hierarchical -eq 'Ja' -or $r.Hierarchical -eq 'Nej')) {
                $mark = if ($WhatIfOnly) { '?' } else { '~' }
                Write-Host "    $mark $($r.Title): Hierarchical '$cur' -> '$($r.Hierarchical)'" -ForegroundColor Yellow
                if (-not $WhatIfOnly) {
                    Set-PnPListItem -List 'MD_Strategy' -Identity $it.Id `
                                    -Values @{ Hierarchical = $r.Hierarchical } | Out-Null
                }
                $hierSet++
            }
            continue
        }
        if ($WhatIfOnly) {
            Write-Host "    ? ville oprette strategi $($r.Title) $($r.StrategyName)" -ForegroundColor Yellow
            $added++; continue
        }
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
    Write-Host "  + $added oprettet, = $skipped fandtes i forvejen, $hierSet fik Hierarchical" -ForegroundColor Green
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
    foreach ($it in $(if (Test-MdList 'MD_StrategyPackage') { Get-PnPListItem -List 'MD_StrategyPackage' -PageSize 500 })) {
        $havePkg["$($it.FieldValues.StrategyKey)|$($it.FieldValues.PackageNo)"] = $it
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
        $existingItem = $havePkg["$($r.StrategyKey)|$($r.PackageNo)"]
        if ($existingItem) {
            $existingId = $existingItem.Id
            # En TAVS overskrivning er farlig: har nogen rettet direkte i
            # listen, ruller csv'en rettelsen tilbage, uden at det kan ses.
            # Derfor listes hvert felt, der faktisk aendrer sig - og med
            # -WhatIfOnly skrives det uden at der roeres ved noget.
            # Raekken er allerede hentet ovenfor - intet ekstra kald pr. pakke.
            # (Get-PnPListItem tager -Id, ikke -Identity.)
            $cur = $existingItem.FieldValues
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
    foreach ($it in $(if (Test-MdList 'MD_Strategy') { Get-PnPListItem -List 'MD_Strategy' -PageSize 500 })) {
        $key = [string]$it.FieldValues.Title
        if (-not $touched.ContainsKey($key)) { continue }
        if ($it.FieldValues.PackagesLoaded -eq $true) { continue }
        $marked++
        if ($WhatIfOnly) {
            Write-Host "    ? strategi $key ville blive markeret som klar" -ForegroundColor Yellow
            continue
        }
        Set-PnPListItem -List 'MD_Strategy' -Identity $it.Id `
                        -Values @{ PackagesLoaded = $true } | Out-Null
        Write-Host "    ~ strategi $key markeret som klar" -ForegroundColor Green
    }
    if (-not $marked) { Write-Host "    ingen strategier skiftede status" -ForegroundColor DarkGray }
}

# ---------------------------------------------------------------------------
$unresolved = @($(if (Test-MdList 'MD_Strategy') { Get-PnPListItem -List 'MD_Strategy' -PageSize 500 }) |
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
Write-Host "  2. Saet Hierarchical i haanden paa dem, der stadig er 'Ikke afklaret'."
Write-Host "  3. Naar flere strategiers pakker er hentet: laeg dem i"
Write-Host "     sharepoint/seed/MD_StrategyPackage.csv og koer scriptet igen."
Write-Host "     PackagesLoaded saettes automatisk."
Write-Host "  4. Tilfoej begge lister som datakilder i appen, og GEM i Studio."
