<#
.SYNOPSIS
    Holder PlantList ajour: alle vaerker og deres SAP-plantnummer.

.DESCRIPTION
    PlantList er listen over vaerker i VH-plan appens Plant-dropdown. Den
    havde seks vaerker; den gamle app havde otte. HCV og SMV laaner AVV's
    standardtaskliste (sp_config.TASKLIST_FALLBACK), indtil de faar deres
    egen i MD_StandardTaskOperations.

    Kolonnen PlantNumber (tekst) er SAP-plantnummeret (fx 2806 for AVV).
    Lager-API'et (flowet BioSap-Integration-MaterialStock, docs/44) kalder
    med plantnummeret, ikke med vaerkets forkortelse.

    Idempotent: et vaerk, der mangler, oprettes; et vaerk, hvis PlantNumber
    er tomt eller anderledes, opdateres; resten springes over.

.PARAMETER SiteUrl
    Sitet listen ligger paa.

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville ske, aendr intet (R2-060).

.EXAMPLE
    .\Provision-PlantList.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        se MdDefaultClientId i _Common.psm1
    Saet PNP_CLIENT_ID som miljoevariabel, eller giv -ClientId.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

# Vaerk -> SAP-plantnummer (Peter, 2026-10-23).
$PLANTS = [ordered]@{
    'AVV' = '2806'
    'ASV' = '2805'
    'HEV' = '2810'
    'KYV' = '2808'
    'SKV' = '2801'
    'SSV' = '2804'
    'HCV' = '2807'
    'SMV' = '2808'
}

Write-Host "`nPlantList" -ForegroundColor Cyan
New-MdField 'PlantList' 'PlantNumber' Text -Description 'SAP plant number, e.g. 2806. Used by the inventory API.'

$have = @{}
foreach ($it in (Get-PnPListItem -List 'PlantList' -PageSize 500)) {
    $have[([string]$it.FieldValues.Title).Trim().ToUpper()] = $it
}
foreach ($p in $PLANTS.Keys) {
    $number = $PLANTS[$p]
    if (-not $have.ContainsKey($p)) {
        if ($WhatIfOnly) {
            Write-Host "    ? ville tilfoeje $p ($number)" -ForegroundColor Yellow
            continue
        }
        Add-PnPListItem -List 'PlantList' -Values @{ Title = $p; PlantNumber = $number } | Out-Null
        Write-Host "    + $p ($number)" -ForegroundColor Green
        continue
    }
    $current = ([string]$have[$p].FieldValues.PlantNumber).Trim()
    if ($current -eq $number) {
        Write-Host "    = $p ($number)" -ForegroundColor DarkGray
        continue
    }
    if ($WhatIfOnly) {
        Write-Host "    ? ville saette $p PlantNumber '$current' -> $number" -ForegroundColor Yellow
        continue
    }
    Set-PnPListItem -List 'PlantList' -Identity $have[$p].Id -Values @{ PlantNumber = $number } | Out-Null
    Write-Host "    ~ $p PlantNumber '$current' -> $number" -ForegroundColor Green
}

Write-Host "`nFaerdig." -ForegroundColor Green
