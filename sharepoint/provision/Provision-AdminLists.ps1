<#
.SYNOPSIS
    Rettighederne paa de lister, der STYRER rettigheder: admins, godkendere,
    godkendelsessporet og SAP-oprettelsens bibliotek (R2-024, R2-032).

.DESCRIPTION
    Appens admin-regel (tools/permissions.py: IsAdmin) og godkenderrollen
    (IsApprover, og flowenes valg af godkender) laeser to lister:

        UserAndGroups   Title = Admin, Member = e-mail      -> admins
        MD_Approver     Approver1/Approver2 pr. noegle      -> godkendere

    Arver de sitets rettigheder, og har Members Contribute (standard paa et
    teamsite), kan enhver bruger goere sig selv til admin eller til
    godkender for et system - og dermed godkende sin egen plan. Scriptet
    lukker det:

    UserAndGroups        oprettes, hvis den mangler (Title + Member, begge
                         indekseret). Members: Read. Owners og flowets
                         konto: Full Control.
    MD_Approver          Members: Read. Owners, -MaintainerGroup (Master
                         Data) og flowets konto kan rette.
    MD_Approver_MeasuringPoint
                         samme som MD_Approver, hvis listen findes. (I dag
                         ligger PRODOS-raekkerne i MD_Approver selv.)
    SAP-oprettelse       biblioteket (Provision-SapCreation.ps1). Den, der
                         kan laegge en fil i Kvitteringer, kan faa en plan
                         markeret som oprettet. Members: Read; Owners,
                         -MaintainerGroup og flowets konto skriver.
    MD_ApprovalLog       revisionssporet (R2-032). Appen skriver selv to
                         slags raekker som brugeren (admin-loggen og
                         "Counter created"), saa brugerne kan ikke bare faa
                         Read. I stedet: Members Contribute med "Create and
                         Edit access: only their own" - en bruger kan oprette
                         raekker og rette sine egne, men ikke flowenes.
                         Kvalitetsflowet stoler kun paa System/Cost-raekker,
                         hvis Author er flowenes servicekonto (miljoevariablen
                         BioSap-ServiceAccountEmail). Se docs/32, afsnit 6.

    Nedarvningen brydes med en KOPI af sitets rettigheder, og saa justeres
    grupperne - samme moenster som Provision-IssueBoard.ps1. Personer, der
    er tilfoejet direkte paa sitet, kopieres med og fjernes ikke; se dem
    efter under Listeindstillinger > Tilladelser.

    Scriptet er idempotent: koer det igen efter hver ny liste eller ny
    servicekonto.

.PARAMETER SiteUrl
    Sitet med BIO SAP-listerne.

.PARAMETER FlowAccount
    E-mail paa flowenes servicekonto (SharePoint-forbindelsen). Den faar
    Full Control paa listerne. Uden parameteren roeres kontoen ikke - saa
    skal den have Full Control paa sitet i forvejen.

.PARAMETER MaintainerGroup
    Navnet paa en SharePoint-gruppe, der ud over Owners maa rette
    godkenderne og SAP-oprettelsens bibliotek (anbefalet: Master Data).
    Udelad for kun Owners.

.PARAMETER LibraryName
    Standard: SAP-oprettelse (samme som Provision-SapCreation.ps1).

.PARAMETER SkipPermissions
    Opret/indekser UserAndGroups, men roer ikke rettighederne.

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville ske, aendr intet.

.EXAMPLE
    .\Provision-AdminLists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/teams/<site>" -FlowAccount "<servicekonto>" -MaintainerGroup "Master Data" -WhatIfOnly

.EXAMPLE
    .\Provision-AdminLists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/teams/<site>" -FlowAccount "<servicekonto>" -MaintainerGroup "Master Data"

.NOTES
    Kraever PnP.PowerShell. ClientId: se MdDefaultClientId i _Common.psm1.
    Accepttest (R2-024): som almindelig bruger (Members) kan man ikke
    oprette en raekke i UserAndGroups; appens IsAdmin virker fortsat.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $FlowAccount,
    [string] $MaintainerGroup,
    [string] $LibraryName = 'SAP-oprettelse',
    [switch] $SkipPermissions,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

$ADMINS   = 'UserAndGroups'
$APPROVER = 'MD_Approver'
$APPROVER_MP = 'MD_Approver_MeasuringPoint'
$LOG      = 'MD_ApprovalLog'

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

function Add-Maintainers {
    # -MaintainerGroup faar Contribute paa listen ud over Owners.
    param([string]$List)
    if (-not $MaintainerGroup -or -not (Test-MdList $List)) { return }
    if ($WhatIfOnly) {
        Write-Host "    ? ville give gruppen '$MaintainerGroup' Contribute" -ForegroundColor Yellow
        return
    }
    $g = Get-PnPGroup -Identity $MaintainerGroup -ErrorAction SilentlyContinue
    if (-not $g) {
        Write-Host "    ! gruppen '$MaintainerGroup' findes ikke paa sitet - springes over" -ForegroundColor Red
        return
    }
    Set-PnPListPermission -Identity $List -Group $g -AddRole (Get-MdRoleName 'Contributor') | Out-Null
    Write-Host "    + $MaintainerGroup har Contribute" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $ADMINS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
# Listen fandtes kun i SharePoint og i intet script. Den oprettes her, saa
# et nyt miljoe (TEST/PROD) kan bygges fra repoet. Raekkerne (hvem der er
# admin) seedes IKKE - de er personer og hoerer ikke til i et offentligt
# repo (R2-025). Title = gruppen (Admin), Member = e-mail med smaa bogstaver.
New-MdList $ADMINS 'Roller i BIO SAP: Title = rollen (Admin), Member = e-mail med smaa bogstaver. Kun Owners retter. Se tools/permissions.py.'
Set-MdIndexed $ADMINS 'Title'
New-MdField 'UserAndGroups' 'Member' Text -Indexed

# ---------------------------------------------------------------------------
Write-Host "`n=== Rettigheder ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
if ($SkipPermissions) {
    Write-Host "  springes over (-SkipPermissions)" -ForegroundColor Yellow
} else {
    Write-Host "  $ADMINS (alle laeser, kun Owners retter)"
    Set-MdReadOnlyList $ADMINS $FlowAccount

    foreach ($l in @($APPROVER, $APPROVER_MP)) {
        if (-not (Test-MdList $l)) {
            if ($l -eq $APPROVER) {
                Write-Host "  ! $l findes ikke - koer Provision-VHPlanApproval.ps1 foerst" -ForegroundColor Yellow
            }
            continue
        }
        Write-Host "  $l (alle laeser, Owners$(if ($MaintainerGroup) { ' og ' + $MaintainerGroup }) retter)"
        Set-MdReadOnlyList $l $FlowAccount
        Add-Maintainers $l
    }

    if (Test-MdList $LibraryName) {
        Write-Host "  $LibraryName (alle laeser, Owners$(if ($MaintainerGroup) { ' og ' + $MaintainerGroup }) og flowet skriver)"
        Set-MdReadOnlyList $LibraryName $FlowAccount
        Add-Maintainers $LibraryName
    } else {
        Write-Host "  ! $LibraryName findes ikke - koer Provision-SapCreation.ps1 foerst" -ForegroundColor Yellow
    }

    if (Test-MdList $LOG) {
        Write-Host "  $LOG (alle laeser, hver opretter og retter kun egne raekker)"
        Set-MdOwnItemsList $LOG $FlowAccount
    } else {
        Write-Host "  ! $LOG findes ikke - koer Provision-VHPlanApproval.ps1 foerst" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Write-Host "Det var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
    return
}
Write-Host "Naeste skridt, som scriptet IKKE goer:" -ForegroundColor Yellow
Write-Host "  1. Listeindstillinger > Tilladelser paa listerne ovenfor: fjern personer,"
Write-Host "     der var tilfoejet direkte paa sitet og derfor er kopieret med."
Write-Host "  2. Test som almindelig bruger: 'Ny' i $ADMINS og $APPROVER er ikke"
Write-Host "     tilgaengelig, og appens admin-funktioner virker for de eksisterende admins."
Write-Host "  3. Saet miljoevariablen BioSap-ServiceAccountEmail til flowenes servicekonto"
Write-Host "     (docs/32, afsnit 6), saa kvalitetsflowet kun stoler paa flowenes egne"
Write-Host "     System/Cost-raekker i $LOG."
