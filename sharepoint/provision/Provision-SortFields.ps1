<#
.SYNOPSIS
    Saetter SAP's sorteringsnoegler (010, 020 ...) i SortFieldList.

.DESCRIPTION
    VH-planens sorteringsfelt (MaintenancePlans.SortField) er et opslag i
    SortFieldList. Listen havde kun beskrivelsen i Title, fx "Power tools -
    single insulation", og den gik videre til SAP-ordren. SAP's felt
    RMIPM-PLAN_SORT forventer noeglen med tre cifre, fx 010.

    Scriptet goer Title til noeglen og flytter beskrivelsen til en ny
    kolonne, SortFieldDescription. Raekkerne findes paa beskrivelsen (uden
    hensyn til store og smaa bogstaver) eller paa en noegle, der allerede
    staar i Title, saa scriptet kan koeres igen. ID'erne bevares, saa
    planernes opslag peger paa de samme raekker og viser noeglen bagefter.
    Raekker, der mangler, laegges til.

    Raekkerne kommer fra sharepoint/seed/SortFieldList.csv.

    Power Fx binder paa VISNINGSNAVNET: kolonnen hedder SortFieldDescription
    baade internt og i visningen.

.PARAMETER SiteUrl
    Sitet listen ligger paa.

.PARAMETER WhatIfOnly
    Vis hvad der ville blive rettet, uden at rette noget.

.EXAMPLE
    .\Provision-SortFields.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -WhatIfOnly

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        se MdDefaultClientId i _Common.psm1
    Saet PNP_CLIENT_ID som miljoevariabel, eller giv -ClientId.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $WhatIfOnly,
    [string] $SeedPath,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Navnet skal vaere ORDRET det samme som L_SORTFIELDS i
# "Maintenance Plan App/build/sp_config.py".
$LIST = 'SortFieldList'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\SortFieldList.csv' }
if (-not (Test-Path $SeedPath)) { throw "Finder ikke $SeedPath" }

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

Write-Host "`n=== $LIST ===" -ForegroundColor Cyan
if (-not (Get-PnPList -Identity $LIST -ErrorAction SilentlyContinue)) {
    throw "Listen $LIST findes ikke paa $SiteUrl"
}

$hasDesc = [bool](Get-PnPField -List $LIST -Identity 'SortFieldDescription' -ErrorAction SilentlyContinue)
if ($WhatIfOnly) {
    if (-not $hasDesc) { Write-Host "    + SortFieldDescription (Text) - oprettes" -ForegroundColor Yellow }
} else {
    New-MdField 'SortFieldList' 'SortFieldDescription' Text
    $hasDesc = $true
}

$rows = Import-Csv -Path $SeedPath -Encoding UTF8

# Eksisterende raekker paa baade beskrivelse og noegle.
$byText = @{}
foreach ($it in (Get-PnPListItem -List $LIST -PageSize 500)) {
    $t = ([string]$it['Title']).Trim().ToUpper()
    if ($t) { $byText[$t] = $it }
    if ($hasDesc) {
        $d = ([string]$it['SortFieldDescription']).Trim().ToUpper()
        if ($d -and -not $byText.ContainsKey($d)) { $byText[$d] = $it }
    }
}

$added = 0; $changed = 0; $same = 0
foreach ($r in $rows) {
    $key  = ([string]$r.SortKey).Trim()
    $desc = ([string]$r.Description).Trim()
    if ($key -notmatch '^\d{3}$') { throw "SortKey '$key' i $SeedPath er ikke tre cifre" }
    $values = @{ Title = $key; SortFieldDescription = $desc }

    $it = $null
    if ($byText.ContainsKey($key)) { $it = $byText[$key] }
    elseif ($byText.ContainsKey($desc.ToUpper())) { $it = $byText[$desc.ToUpper()] }

    if ($it) {
        $oldDesc = if ($hasDesc) { ([string]$it['SortFieldDescription']).Trim() } else { '' }
        if (([string]$it['Title']).Trim() -eq $key -and $oldDesc -ceq $desc) { $same++; continue }
        Write-Host ("    ~ ID {0}: '{1}' -> {2} {3}" -f $it.Id, $it['Title'], $key, $desc)
        if (-not $WhatIfOnly) { Set-PnPListItem -List $LIST -Identity $it.Id -Values $values | Out-Null }
        $changed++
    } else {
        Write-Host ("    + {0} {1}" -f $key, $desc) -ForegroundColor Green
        if (-not $WhatIfOnly) { Add-PnPListItem -List $LIST -Values $values | Out-Null }
        $added++
    }
}

$mode = if ($WhatIfOnly) { ' (WhatIfOnly - intet er rettet)' } else { '' }
Write-Host ("    {0} rettet, {1} tilfoejet, {2} var i forvejen rigtige{3}" -f $changed, $added, $same, $mode) -ForegroundColor Green

# Raekker i listen, som CSV'en ikke kender, roeres ikke - men de ville
# sende en beskrivelse til SAP.
$known = @{}
foreach ($r in $rows) { $known[([string]$r.SortKey).Trim()] = $true; $known[([string]$r.Description).Trim().ToUpper()] = $true }
foreach ($it in (Get-PnPListItem -List $LIST -PageSize 500)) {
    $t = ([string]$it['Title']).Trim()
    if (-not ($known.ContainsKey($t) -or $known.ContainsKey($t.ToUpper()))) {
        Write-Host ("    ! ID {0} '{1}' findes ikke i CSV'en og har ingen SAP-noegle" -f $it.Id, $t) -ForegroundColor Yellow
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Deploy BIO SAP og Publish (dropdown'en viser noegle og beskrivelse)."
Write-Host "  2. Koer sharepoint/inspect/Export-ListSchema.ps1, saa check_datasources.py"
Write-Host "     kan efterproeve kolonnen."
