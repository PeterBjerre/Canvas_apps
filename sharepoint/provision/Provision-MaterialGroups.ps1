<#
.SYNOPSIS
    Provisionerer MD_MaterialGroup - varegrupperne til PM02-operationer.

.DESCRIPTION
    Issue #267. Varegruppen paa en tasklisteoperation med kontrolnoegle
    PM02 var et frit tekstfelt. Nu vaelges den i en dropdown i VH-plan
    appen, og listen her er dens valg.

    Kolonnerne svarer til SAP-oversigten:
        MaterialGroup             (Title, omdoebt)  B04.10
        MaterialGroupDescription  Transmission systems
        Description2              High/low voltage service
        CategoryDescription       Service on high and low voltage ...
        SearchWords               Bio

    Raekkerne kommer fra sharepoint/seed/MD_MaterialGroup.csv. En
    varegruppe, der allerede staar i listen, roeres ikke - den er
    SharePoints nu. Nye varegrupper laegges til. Med -Force overskrives
    ogsaa de eksisterende med CSV'ens tekster.

    Idempotent: kan koeres igen, naar der kommer nye varegrupper i CSV'en.

    Power Fx binder paa VISNINGSNAVNET: Title hedder MaterialGroup.

.PARAMETER SiteUrl
    Sitet listen skal ligge paa.

.PARAMETER Force
    Overskriv ogsaa de varegrupper, der findes i forvejen.

.EXAMPLE
    .\Provision-MaterialGroups.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        se MdDefaultClientId i _Common.psm1
    Saet PNP_CLIENT_ID som miljoevariabel, eller giv -ClientId.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Force,
    [string] $SeedPath,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Navnet skal vaere ORDRET det samme som L_MATGROUPS i
# "Maintenance Plan App/build/sp_config.py".
$LIST = 'MD_MaterialGroup'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\MD_MaterialGroup.csv' }

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

Write-Host "`n=== $LIST ===" -ForegroundColor Cyan

New-MdList 'MD_MaterialGroup' 'Varegrupper (SAP Matl Group) til PM02-operationer i VH-plan appens taskliste. Issue #267.'
Rename-MdTitle 'MD_MaterialGroup' 'MaterialGroup'
Set-PnPField -List $LIST -Identity 'Title' -Values @{ EnforceUniqueValues = $true }
New-MdField 'MD_MaterialGroup' 'MaterialGroupDescription' Text
New-MdField 'MD_MaterialGroup' 'Description2'             Text
# Den laengste beskrivelse er 186 tegn - taet paa Text-feltets 255.
New-MdNoteField 'MD_MaterialGroup' 'CategoryDescription' 3
New-MdField 'MD_MaterialGroup' 'SearchWords'              Text

# --- seed -----------------------------------------------------------------
if (-not (Test-Path $SeedPath)) { throw "Finder ikke $SeedPath" }
Write-Host "  Seed fra $SeedPath" -ForegroundColor Cyan
$rows = Import-Csv -Path $SeedPath -Encoding UTF8

$have = @{}
foreach ($it in (Get-PnPListItem -List $LIST -PageSize 500)) {
    $have[([string]$it['Title']).Trim().ToUpper()] = $it
}

$added = 0; $kept = 0; $updated = 0
foreach ($r in $rows) {
    $code = ([string]$r.MaterialGroup).Trim()
    if (-not $code) { continue }
    $values = @{
        Title                    = $code
        MaterialGroupDescription = $r.MaterialGroupDescription
        Description2             = $r.Description2
        CategoryDescription      = $r.CategoryDescription
        SearchWords              = $r.SearchWords
    }
    $key = $code.ToUpper()
    if ($have.ContainsKey($key)) {
        if ($Force) {
            Set-PnPListItem -List $LIST -Identity $have[$key].Id -Values $values | Out-Null
            $updated++
        } else {
            $kept++
        }
    } else {
        Add-PnPListItem -List $LIST -Values $values | Out-Null
        $added++
    }
}
$msg = "    {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
Write-Host $msg -ForegroundColor Green
if ($kept -and -not $Force) {
    Write-Host "    Varegrupper, der fandtes i forvejen, er IKKE rettet. Koer igen med -Force" -ForegroundColor DarkGray
    Write-Host "    for at saette dem tilbage til CSV'ens tekster." -ForegroundColor DarkGray
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Tilfoej MD_MaterialGroup som datakilde i BIO SAP i Studio."
Write-Host "  2. Koer sharepoint/inspect/Export-ListSchema.ps1, saa check_datasources.py"
Write-Host "     kan efterproeve kolonnerne."
