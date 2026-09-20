<#
.SYNOPSIS
    Tilfoejer de kolonner, VH-plan appen mangler, til de tre eksisterende
    transaktionslister - og rydder op i et navnerod i MaintenancePlans.

.DESCRIPTION
    Alt her er ADDITIVT. Den kaerende app mister ingenting og mangler
    ingenting bagefter. Se docs/10-datamodel-forslag.md 3.

        TaskListMain.OperationNo            SAP-operationsnummeret (10,20,30)
        TaskListMain.PackagesKey            pakkeallokering ";1;3;5;"
        MaintenanceItems.OrstedResponsible-
            Email                           delegerbart alternativ til
                                            Person-kolonnen
        MaintenancePlans                    CallHorizon-choicen omdoebes

    OPERATIONSNUMMERET
    ------------------
    TaskListMain har i dag INTET operationsnummer. Index er udfyldt paa 90
    af 306 raekker, og Num er et antal (277 raekker har vaerdien 1) og ikke
    en sekvens. Uden et nummer og en paalidelig raekkefoelge kan
    GUI-scriptet ikke laegge operationerne ind i IA01 i rigtig orden.

    -Backfill udfylder OperationNo paa de eksisterende raekker: 10, 20, 30
    pr. maintenance item, sorteret efter Index hvor det findes og ellers
    efter ID. Kun raekker UDEN OperationNo roeres, saa den kan koeres igen.

    NAVNERODET
    ----------
        internt CallHorizon    -> visningsnavn 'CallHorizonOLD'  (Choice, gammel)
        internt CallHorizon0   -> visningsnavn 'CallHorizon'     (Number, i brug)

    Visningsnavnet paa den ene er den andens interne navn. Power Fx binder
    paa visningsnavn, saa appen rammer rigtigt - men et migreringsscript,
    der bruger interne navne, rammer forkert. Choicen omdoebes til
    'CallHorizonChoiceOLD', saa kollisionen forsvinder. Det aendrer intet
    for appen, som allerede skriver CallHorizonOLD.

.EXAMPLE
    .\Provision-VHPlanColumns.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -WhatIfOnly

.EXAMPLE
    .\Provision-VHPlanColumns.ps1 -SiteUrl "https://..." -Backfill

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        9bc3ab49-b65d-410a-85ad-de819febfddc
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Backfill,
    [switch] $FixMainWorkCenterNames,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

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

function Add-Col {
    param([string]$List, [string]$Name, [string]$Type, [string]$Description,
          [switch]$Indexed)
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name findes allerede" -ForegroundColor DarkGray
        return
    }
    if ($WhatIfOnly) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    }
    Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type $Type `
                 -AddToDefaultView | Out-Null
    $v = @{}
    if ($Description) { $v.Description = $Description }
    if ($Indexed)     { $v.Indexed = $true }
    if ($v.Count) { Set-PnPField -List $List -Identity $Name -Values $v }
    Write-Host "    + $Name ($Type)" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== TaskListMain ===" -ForegroundColor Cyan
Add-Col 'TaskListMain' 'OperationNo' Number -Indexed `
    -Description 'SAP-operationsnummer: 10, 20, 30. Bestemmer ogsaa raekkefoelgen. Erstatter Index.'
Add-Col 'TaskListMain' 'PackagesKey' Text `
    -Description 'Pakkeallokering for strategiplaner, fx ";1;3;5;". Sentinel i begge ender, saa ";1;" aldrig matcher inde i ";12;".'

Write-Host "`n=== MaintenancePlans ===" -ForegroundColor Cyan
# Appens strategi kommer fra MD_Strategy ("128"). Den kan IKKE skrives til
# MaintenancePlans.StandardStrategy, som er et opslag i den gamle
# StandardStrategyList med tre raekker - strategi 128 findes ikke der.
# En tekstkolonne med SAP-noeglen er den enkleste vej, og den er additiv.
#
# En udfyldt StrategyKey betyder samtidig, at planen ER en strategiplan.
# MaintenancePlans.PlanType kan ikke bruges til det: dens eneste valgvaerdi
# er "PM".
Add-Col 'MaintenancePlans' 'StrategyKey' Text -Indexed `
    -Description 'SAP-strateginoegle fra MD_Strategy, fx 128. Udfyldt = strategiplan (IP42), tom = single cycle (IP41).'

Write-Host "`n=== MaintenanceItems ===" -ForegroundColor Cyan
Add-Col 'MaintenanceItems' 'OrstedResponsibleEmail' Text -Indexed `
    -Description 'Samme person som OrstedResponsible, men som indekseret tekst. Person-kolonner kan ikke filtreres delegerbart.'

# ---------------------------------------------------------------------------
Write-Host "`n=== MaintenancePlans: navnerodet ===" -ForegroundColor Cyan
$old = Get-PnPField -List 'MaintenancePlans' -Identity 'CallHorizon' -ErrorAction SilentlyContinue
if (-not $old) {
    Write-Host "  ! Fandt ikke kolonnen 'CallHorizon' - er der ryddet op allerede?" -ForegroundColor Yellow
} elseif ($old.Title -eq 'CallHorizonChoiceOLD') {
    Write-Host "  = Allerede omdoebt" -ForegroundColor DarkGray
} elseif ($WhatIfOnly) {
    Write-Host "  ? ville omdoebe visningsnavnet '$($old.Title)' -> 'CallHorizonChoiceOLD'" -ForegroundColor Yellow
} else {
    Set-PnPField -List 'MaintenancePlans' -Identity 'CallHorizon' `
                 -Values @{ Title = 'CallHorizonChoiceOLD' }
    Write-Host "  ~ '$($old.Title)' -> 'CallHorizonChoiceOLD'" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# MainWorkCenters: visningsnavne der ikke kan bruges fra Power Fx
# ---------------------------------------------------------------------------
# field_1 har visningsnavnet 'Description' efterfulgt af 33 MELLEMRUM. Power Fx
# binder paa visningsnavn, saa kolonnen kun kan naas ved at skrive praecis det
# antal mellemrum inde i enkelte anfoerselstegn. Det er i praksis ubrugeligt.
#
# Appen undgaar problemet ved kun at bruge Title og 'Plant Key'. Omdoebningen
# er derfor VALGFRI - men den gamle app kan bruge kolonnen, saa den skal
# vaelges bevidst.
if ($FixMainWorkCenterNames) {
    Write-Host "`n=== MainWorkCenters: visningsnavne ===" -ForegroundColor Cyan
    $f = Get-PnPField -List 'MainWorkCenters' -Identity 'field_1' -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "  ! field_1 findes ikke" -ForegroundColor Yellow
    } elseif ($f.Title -eq 'WorkCenterDescription') {
        Write-Host "  = Allerede omdoebt" -ForegroundColor DarkGray
    } elseif ($WhatIfOnly) {
        Write-Host "  ? ville omdoebe '$($f.Title.TrimEnd())...' -> 'WorkCenterDescription'" -ForegroundColor Yellow
    } else {
        Set-PnPField -List 'MainWorkCenters' -Identity 'field_1' `
                     -Values @{ Title = 'WorkCenterDescription' }
        Write-Host "  ~ field_1 -> 'WorkCenterDescription'" -ForegroundColor Green
        Write-Host "    ADVARSEL: bruger den GAMLE app denne kolonne, skal den rettes der." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Backfill af OperationNo
# ---------------------------------------------------------------------------
if ($Backfill) {
    Write-Host "`n=== Udfylder OperationNo ===" -ForegroundColor Cyan
    $items = Get-PnPListItem -List 'TaskListMain' -PageSize 500

    # Grupper paa maintenance item. Raekker uden item faar deres egen gruppe,
    # saa de ogsaa faar et nummer i stedet for at blive sprunget over.
    $groups = @{}
    foreach ($it in $items) {
        $lv = $it.FieldValues.MaintenanceItemNo
        $key = if ($lv) { "I$($lv.LookupId)" } else { "X$($it.Id)" }
        if (-not $groups.ContainsKey($key)) { $groups[$key] = @() }
        $groups[$key] += $it
    }

    $set = 0; $kept = 0
    foreach ($key in $groups.Keys) {
        # Index hvor det findes, ellers ID. Raekker MED Index kommer foerst,
        # i Index-orden; resten bagefter i ID-orden. Det bevarer den
        # raekkefoelge, nogen faktisk har valgt.
        $sorted = $groups[$key] | Sort-Object `
            @{ Expression = { if ($null -eq $_.FieldValues.Index) { 1 } else { 0 } } },
            @{ Expression = { $_.FieldValues.Index } },
            @{ Expression = { $_.Id } }

        $no = 0
        foreach ($it in $sorted) {
            $no += 10
            if ($null -ne $it.FieldValues.OperationNo) { $kept++; continue }
            if ($WhatIfOnly) { $set++; continue }
            Set-PnPListItem -List 'TaskListMain' -Identity $it.Id `
                            -Values @{ OperationNo = $no } | Out-Null
            $set++
        }
    }
    $verb = if ($WhatIfOnly) { 'ville saette' } else { 'sat' }
    Write-Host "  $verb OperationNo paa $set raekker i $($groups.Count) grupper" -ForegroundColor Green
    if ($kept) { Write-Host "  $kept raekker havde den i forvejen og blev ikke roert" -ForegroundColor DarkGray }
}

# ---------------------------------------------------------------------------
Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Write-Host "Det var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
} elseif (-not $Backfill) {
    Write-Host "Kolonnerne er oprettet, men OperationNo er TOM paa de" -ForegroundColor Yellow
    Write-Host "eksisterende raekker. Koer igen med -Backfill for at udfylde den."
}
Write-Host "`nHusk: nye kolonner ses foerst i appen, naar datakilden er"
Write-Host "opdateret i Studio (fjern og tilfoej listen igen, og GEM)."
