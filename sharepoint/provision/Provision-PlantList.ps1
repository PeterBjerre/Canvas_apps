<#
.SYNOPSIS
    Tilfoejer de vaerker, PlantList mangler (HCV og SMV).

.DESCRIPTION
    PlantList er listen over vaerker i VH-plan appens Plant-dropdown. Den
    havde seks vaerker; den gamle app havde otte. HCV og SMV laaner AVV's
    standardtaskliste (sp_config.TASKLIST_FALLBACK), indtil de faar deres
    egen i MD_StandardTaskOperations.

    Idempotent: et vaerk, der allerede staar i listen, springes over.

.PARAMETER SiteUrl
    Sitet listen ligger paa.

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
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

$PLANTS = @('HCV', 'SMV')

Write-Host "`nPlantList" -ForegroundColor Cyan
$have = @{}
foreach ($it in (Get-PnPListItem -List 'PlantList' -PageSize 500)) {
    $have[([string]$it.FieldValues.Title).Trim().ToUpper()] = $true
}
foreach ($p in $PLANTS) {
    if ($have.ContainsKey($p)) {
        Write-Host "    = $p" -ForegroundColor DarkGray
        continue
    }
    Add-PnPListItem -List 'PlantList' -Values @{ Title = $p } | Out-Null
    Write-Host "    + $p" -ForegroundColor Green
}

Write-Host "`nFaerdig." -ForegroundColor Green
