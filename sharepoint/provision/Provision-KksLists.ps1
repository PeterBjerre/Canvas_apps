<#
.SYNOPSIS
    Provisionerer SharePoint-listen bag KKS-opslaget (KKS App / BIO SAP).

.DESCRIPTION
    Idempotent: kan koeres flere gange. Eksisterende lister og kolonner
    springes over.

    KKS-skaermen laeser tre noegleomraader. To af dem GENBRUGES:

      MD_FLKey              aggregat- og komponentnoeglerne (KeyType
                            'Aggregate'/'Component' med Description).
                            Oprettes og seedes af
                            Provision-FunctionalLocationLists.ps1 - IKKE her.
                            Scriptet tjekker kun, at den er der.

    Den tredje er ny:

      MD_KksFunctionKey     funktionsnoegle-vejledningen: 2.913 raekker med
                            sektion (HOME, A-Z), kode og beskrivelse.
                            MD_FLKey's Function-raekker kan ikke bruges:
                            de er de gyldige noegler UDEN tekst. Se
                            tools/gen_kks_seed.py.

    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser

.PARAMETER SiteUrl
    Url til det SharePoint-site, listerne skal ligge paa.

.PARAMETER SeedMasterData
    Seeder MD_KksFunctionKey fra sharepoint/seed/MD_KksFunctionKey.csv.
    Sker kun, naar listen er TOM - ellers ville hver koersel lave dubletter.

.PARAMETER Reseed
    Sletter alle raekker i MD_KksFunctionKey og seeder forfra. Brug det,
    naar html/kks.generated.js er aendret, og seedet er skrevet igen med:
        python3 tools/gen_kks_seed.py

.EXAMPLE
    .\Provision-KksLists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/SAPMasterdata" -SeedMasterData

.NOTES
    Appen henter listen i bidder paa 500 raekker efter SortNo (indekseret
    tal), saa hver forespoergsel kan delegeres og holder sig under
    datagraensen. SortNo SKAL derfor vaere 1, 2, 3 ... uden huller - det
    er den i seedet. Antallet af bidder regnes af builderen ud fra seedet
    (KKS App/build/kks_config.py).

    Power Fx binder paa VISNINGSNAVNET: Title hedder Code.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $SeedMasterData,
    [switch] $Reseed,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

$LIST = 'MD_KksFunctionKey'

Write-Host "`n=== KKS-opslag ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# MD_KksFunctionKey - funktionsnoegle-vejledningen
# ---------------------------------------------------------------------------
New-MdList 'MD_KksFunctionKey' 'KKS funktionsnoegler med beskrivelse (html/kks.generated.js)'
New-MdField 'MD_KksFunctionKey' 'Section'   Text   -Indexed -Required
New-MdField 'MD_KksFunctionKey' 'SortNo'    Number -Indexed -Required
# 48 beskrivelser er laengere end 255 tegn - derfor Note, ikke Text.
New-MdNoteField 'MD_KksFunctionKey' 'Description' 4
Rename-MdTitle 'MD_KksFunctionKey' 'Code'

# ---------------------------------------------------------------------------
# MD_FLKey - genbruges, oprettes ikke her
# ---------------------------------------------------------------------------
$fl = Get-PnPList -Identity 'MD_FLKey' -ErrorAction SilentlyContinue
if (-not $fl) {
    Write-Host "  ! MD_FLKey findes ikke. KKS-skaermens aggregat- og komponentnoegler" -ForegroundColor Yellow
    Write-Host "    kommer derfra. Koer:" -ForegroundColor Yellow
    Write-Host "      .\Provision-FunctionalLocationLists.ps1 -SiteUrl $SiteUrl -SeedMasterData" -ForegroundColor Yellow
} elseif ($fl.ItemCount -eq 0) {
    Write-Host "  ! MD_FLKey er tom - seed den med Provision-FunctionalLocationLists.ps1 -SeedMasterData" -ForegroundColor Yellow
} else {
    Write-Host "  = MD_FLKey findes ($($fl.ItemCount) raekker) - genbruges til aggregat og komponent" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------------------
# Seed af MD_KksFunctionKey
# ---------------------------------------------------------------------------
if ($SeedMasterData -or $Reseed) {
    Write-Host "`n=== Seed $LIST ===" -ForegroundColor Cyan
    $path = Join-Path $PSScriptRoot '..\seed\MD_KksFunctionKey.csv'
    if (-not (Test-Path $path)) { throw "Finder ikke $path" }

    $existing = (Get-PnPList -Identity $LIST).ItemCount
    if ($existing -gt 0 -and -not $Reseed) {
        Write-Host "  = $LIST har allerede $existing raekker - springer over (brug -Reseed)" -ForegroundColor DarkGray
    } else {
        if ($existing -gt 0) {
            Write-Host "  - sletter $existing raekker" -ForegroundColor Yellow
            $del = New-PnPBatch
            Get-PnPListItem -List $LIST -PageSize 2000 | ForEach-Object {
                Remove-PnPListItem -List $LIST -Identity $_.Id -Batch $del
            }
            Invoke-PnPBatch -Batch $del
        }
        # 2.913 raekker: i batch, ellers er det 2.913 rundture.
        $batch = New-PnPBatch
        $n = 0
        Import-Csv $path -Encoding UTF8 | ForEach-Object {
            $values = @{
                Title       = $_.Code
                Section     = $_.Section
                SortNo      = [int]$_.SortNo
                Description = $_.Description
            }
            Add-PnPListItem -List $LIST -Values $values -Batch $batch
            $n++
            if ($n % 500 -eq 0) { Invoke-PnPBatch -Batch $batch; $batch = New-PnPBatch; Write-Host "    $n ..." }
        }
        Invoke-PnPBatch -Batch $batch
        Write-Host "  + $LIST seedet med $n raekker" -ForegroundColor Green
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Tilfoej MD_KksFunctionKey og MD_FLKey som datakilder i BIO SAP i Studio."
Write-Host "  2. Koer sharepoint/inspect/Export-ListSchema.ps1, saa check_datasources.py"
Write-Host "     kan efterproeve kolonnerne."
