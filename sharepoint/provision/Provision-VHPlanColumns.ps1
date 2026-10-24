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
        MaintenanceItems.NonFlowUserStatus  de manglende valg (issue #112)
        MaintenancePlans                    CallHorizon-choicen omdoebes
        MaintenanceItems                    fem kolonner goeres valgfri,
                                            saa en kladde kan gemmes med
                                            ufaerdige items (issue #566)
        MaintenanceItems.ItemDescription og
            TaskListMain.LongText           goeres til ren tekst (ikke rich
                                            text), saa lang tekst ikke
                                            kommer tilbage pakket i HTML

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
        se MdDefaultClientId i _Common.psm1
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

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

# Kolonnerne oprettes med New-MdField fra _Common.psm1 (toerloeb: Set-MdWhatIf).

function Add-Choices {
    # Sikrer, at alle oenskede valg findes paa en EKSISTERENDE Choice-kolonne,
    # i den raekkefoelge. Valg, der er der i forvejen og ikke er paa listen,
    # beholdes efter dem. Opretter aldrig kolonnen - findes den ikke, siges
    # det, og intet roeres (ingen dubletkolonne).
    param([string]$List, [string]$Name, [string[]]$Wanted)
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $Name findes ikke paa $List - roerer intet" -ForegroundColor Yellow
        return
    }
    # Get-PnPField henter ikke .Choices - kun SchemaXml (se
    # Provision-VHPlanApproval.ps1, Add-Choice).
    $current = [string[]]@(([xml]$f.SchemaXml).Field.CHOICES.CHOICE)
    $missing = @($Wanted | Where-Object { $current -notcontains $_ })
    if (-not $missing) {
        Write-Host "    = $Name har alle valg" -ForegroundColor DarkGray
        return
    }
    $new = [string[]]($Wanted + @($current | Where-Object { $_ -and ($Wanted -notcontains $_) }))
    if ($WhatIfOnly) {
        Write-Host "    ? ville tilfoeje $($missing -join ', ') til $Name" -ForegroundColor Yellow
        return
    }
    Set-MdChoices $List $Name $new
    Write-Host "    + $Name har nu: $($new -join ', ')" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== TaskListMain ===" -ForegroundColor Cyan
New-MdField 'TaskListMain' 'OperationNo' Number -Indexed `
    -Description 'SAP-operationsnummer: 10, 20, 30. Bestemmer ogsaa raekkefoelgen. Erstatter Index.'
New-MdField 'TaskListMain' 'PackagesKey' Text `
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
New-MdField 'MaintenancePlans' 'StrategyKey' Text -Indexed `
    -Description 'SAP-strateginoegle fra MD_Strategy, fx 128. Udfyldt = strategiplan (IP42), tom = single cycle (IP41).'

Write-Host "`n=== MaintenanceItems ===" -ForegroundColor Cyan
New-MdField 'MaintenanceItems' 'OrstedResponsibleEmail' Text -Indexed `
    -Description 'Samme person som OrstedResponsible, men som indekseret tekst. Person-kolonner kan ikke filtreres delegerbart.'

# Non Flow User Status (issue #112). Kolonnen FINDES (valg: ZBOW); her
# tilfoejes de manglende SAP-koder. Valget er koden alene: SAP-ordre-flowet
# sender NonFlowUserStatus.Value direkte til SAP. Beskrivelserne vises af
# appen (sp_config.NON_FLOW_STATUS_TEXT).
Add-Choices 'MaintenanceItems' 'NonFlowUserStatus' @(
    'INCD', 'ZBUN', 'ZMOC', 'WADO', 'ZBOW', 'OPHO', 'UNEX', 'OFIX', 'REWO')

# KLADDER MED UFAERDIGE ITEMS (issue #566). Save draft skal kunne gemme et
# item, der mangler kort tekst, funktionsplads, aktivitetstype eller
# arbejdscenter. Kolonnerne er paakraevede i listen, og SharePoint afviser
# saa hele Items-Patch'et (R2-008). De goeres valgfri HER - ingen ny
# kolonne. Appen haandhaever dem foer Submit (build_status, build_save.NO_REQ),
# saa en INDSENDT plan har dem stadig. ItemDescription er med, fordi appen
# skriver kort tekst/lang tekst i den, og begge kan vaere tomme i en kladde.
# Kan koeres igen: en kolonne, der allerede er valgfri, roeres ikke.
#
# Bagefter skal MaintenanceItems opdateres som datakilde i Studio (Refresh,
# eller fjern og tilfoej): Power Apps tjekker paakraevede kolonner mod sin
# gemte kopi af skemaet, foer Patch sendes.
Write-Host "`n=== MaintenanceItems: valgfri i kladder (issue #566) ===" -ForegroundColor Cyan
foreach ($name in @('Title', 'ItemDescription', 'FunctionalLocation',
                    'MaintenanceActivityType', 'MainWorkCenter')) {
    $f = Get-PnPField -List 'MaintenanceItems' -Identity $name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $name findes ikke paa MaintenanceItems - roerer intet" -ForegroundColor Yellow
    } elseif (-not $f.Required) {
        Write-Host "    = $name er valgfri" -ForegroundColor DarkGray
    } elseif ($WhatIfOnly) {
        Write-Host "    ? ville goere $name valgfri" -ForegroundColor Yellow
    } else {
        Set-PnPField -List 'MaintenanceItems' -Identity $name -Values @{ Required = $false }
        Write-Host "    ~ $name er nu valgfri" -ForegroundColor Green
    }
}

# LANG TEKST SOM REN TEKST. ItemDescription og LongText var rich text, saa
# SharePoint gav vaerdien tilbage som <div class="ExternalClass...">tekst</div>.
# Long text-popuppen viste taggene, og SAP-ordren fik dem med. Som ren tekst
# gemmes teksten praecis, som den er skrevet, med linjeskift. Raekker gemt
# foer da beholder deres HTML i listen; appen rydder den ved indlaesning
# (sp_config.plain_long_text) og skriver ren tekst ved naeste gem.
# Kan koeres igen: en kolonne, der allerede er ren tekst, roeres ikke.
Write-Host "`n=== Lang tekst som ren tekst ===" -ForegroundColor Cyan
foreach ($pair in @(@('MaintenanceItems', 'ItemDescription'), @('TaskListMain', 'LongText'))) {
    $list = $pair[0]; $name = $pair[1]
    $f = Get-PnPField -List $list -Identity $name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $list.$name findes ikke - roerer intet" -ForegroundColor Yellow
    } elseif (-not $f.RichText) {
        Write-Host "    = $list.$name er ren tekst" -ForegroundColor DarkGray
    } elseif ($WhatIfOnly) {
        Write-Host "    ? ville goere $list.$name til ren tekst" -ForegroundColor Yellow
    } else {
        Set-PnPField -List $list -Identity $name -Values @{ RichText = $false }
        Write-Host "    ~ $list.$name er nu ren tekst" -ForegroundColor Green
    }
}

# Opslagskolonnerne, appen filtrerer paa (REVIEW.md B14). MaintenancePlanNo
# og MaintenancePlanID findes i forvejen; de faar kun et indeks, saa
# filtrene holder, naar listerne passerer 5.000 elementer.
Write-Host "`n=== Indekser paa opslagskolonner ===" -ForegroundColor Cyan
Set-MdIndexed -List 'MaintenanceItems' -Name 'MaintenancePlanNo' -WhatIfOnly:$WhatIfOnly
Set-MdIndexed -List 'TaskListMain' -Name 'MaintenancePlanID' -WhatIfOnly:$WhatIfOnly

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
