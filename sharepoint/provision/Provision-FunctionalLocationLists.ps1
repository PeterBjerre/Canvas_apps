<#
.SYNOPSIS
    Provisionerer SharePoint-listerne bag "Functional Location App".

.DESCRIPTION
    Idempotent: kan koeres flere gange. Eksisterende lister og kolonner
    springes over, saa scriptet ogsaa bruges, naar der kommer nye felter.

    Tre lister:

      FunctionalLocationRequests   anmodningshovedet - status, taellere og
                                   det frosne JSON-snapshot ved indsend
      FunctionalLocationItems      een raekke pr. FL, med spool-felterne
                                   som JSON (SpoolValuesJson)
      MD_FLKey                     noeglerne bag klassebestemmelsen. Appen
                                   slaar KUN funktionsnoeglerne op her - de
                                   er 6.441 og kan ikke ligge i appen. De
                                   tre smaa tabeller ligger som navngivne
                                   formler (docs/31, PX5).

    Indeksraekken paa landingssiden (MD_RequestIndex) oprettes af
    Provision-RequestIndex.ps1. Domaenet 'FunctionalLocation' findes der
    i forvejen.

    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser

.PARAMETER SiteUrl
    Url til det SharePoint-site, listerne skal ligge paa.

.PARAMETER SeedMasterData
    Seeder MD_FLKey fra sharepoint/seed/MD_FLKey.csv (6.733 noegler). Sker
    kun, naar listen er TOM - ellers ville hver koersel lave dubletter.
    Brug -ReseedKeys for at toemme og seede forfra.

.PARAMETER ReseedKeys
    Sletter alle raekker i MD_FLKey og seeder forfra. Brug det, naar
    html/lookups.generated.js er aendret, og MD_FLKey.csv er genereret
    igen med: node tools/fl/harness.js seed

.EXAMPLE
    .\Provision-FunctionalLocationLists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/SAPMasterdata" -SeedMasterData

.NOTES
    Koer mod DEV foerst. Kolonnernes INTERNE navne laases ved oprettelse og
    kan ikke aendres bagefter - derfor saetter scriptet -InternalName
    eksplicit. Power Fx binder paa VISNINGSNAVNET: Title hedder RequestNo,
    RowGuid og KeyValue i de tre lister, og det er de navne, appen bruger.
    Se docs/02-datamodel-sharepoint.md, afsnit 5.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $SeedMasterData,
    [switch] $ReseedKeys,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Uden et fejler MSAL med "User canceled
# authentication" - hvilket lyder som om brugeren trykkede fortryd.
# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

# ---------------------------------------------------------------------------
# Hjaelpefunktioner - samme form som Provision-VHPlanLists.ps1. Navnene
# er repoets (New-MdList/New-MdField/New-MdNoteField): tools/check_datasources.py
# laeser dem og ved derfor, at listerne og kolonnerne kommer herfra.
# ---------------------------------------------------------------------------

function New-MdList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Set-PnPList -Identity $Title -Description $Description
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
}

function New-MdField {
    param(
        [string]$List, [string]$Name, [string]$Type,
        [string[]]$Choices, [switch]$Indexed, [switch]$Required
    )
    $existing = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    # Indeksering skal ske FOER listen passerer 5.000 elementer.
    if ($Indexed) { Set-PnPField -List $List -Identity $Name -Values @{ Indexed = $true } }
    if ($Required) { Set-PnPField -List $List -Identity $Name -Values @{ Required = $true } }
}

# Flerlinjet tekst som REN tekst. Rich text ville lade SharePoint saette
# HTML-tags ind i JSON'en, og saa kan hverken appen eller flowet laese den.
function New-MdNoteField {
    param([string]$List, [string]$Name)
    if (-not (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue)) {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type Note | Out-Null
        Write-Host "    + $Name (Note, plain)" -ForegroundColor Green
    }
    Set-PnPField -List $List -Identity $Name -Values @{ RichText = $false; NumberOfLines = 6 }
}

# Note-kolonner maa ikke staa i standardvisningen - de goer hver
# datahentning tungere.
function Remove-FromDefaultView {
    param([string]$List, [string]$Name)
    $view = Get-PnPView -List $List | Where-Object { $_.DefaultView } | Select-Object -First 1
    if ($view -and $view.ViewFields -contains $Name) {
        $view.ViewFields.Remove($Name); $view.Update(); Invoke-PnPQuery
        Write-Host "    ~ $Name fjernet fra standardvisningen" -ForegroundColor Green
    }
}

# Statusordforraadet - ORDRET det samme som i MD_RequestIndex
# (Provision-RequestIndex.ps1) og hub_config.py. Hubben slaar op paa
# vaerdierne; en stavefejl giver en raekke uden farve.
$REQUEST_STATUS = 'Kladde','Indsendt','UnderBehandling','AfventerInfo','KlarTilSAP',
                  'OprettetISAP','Afvist','Annulleret'

# Raekkens status - ORDRET controllerens (app-functional-location.js:1129-1135
# og 928). Draft-raekker gemmes ikke (docs/31, FL3), men vaerdien er med,
# saa en raekke aldrig kan faa en status, listen ikke kender.
$ROW_STATUS = 'draft','valid','warning','invalid'

Write-Host "`n=== Functional Location ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# FunctionalLocationRequests - hovedet
# ---------------------------------------------------------------------------
New-MdList 'FunctionalLocationRequests' 'Anmodninger om nye Functional Locations (SPOOL)'
New-MdField 'FunctionalLocationRequests' 'RequestGuid'    Text     -Indexed -Required
New-MdField 'FunctionalLocationRequests' 'Status'         Choice   -Indexed -Choices $REQUEST_STATUS
New-MdField 'FunctionalLocationRequests' 'RequesterEmail' Text     -Indexed
New-MdField 'FunctionalLocationRequests' 'RequesterName'  Text
New-MdField 'FunctionalLocationRequests' 'RowCount'       Number
New-MdField 'FunctionalLocationRequests' 'ReadyCount'     Number
New-MdField 'FunctionalLocationRequests' 'IssueCount'     Number
New-MdField 'FunctionalLocationRequests' 'WarningCount'   Number
New-MdField 'FunctionalLocationRequests' 'SubmittedOn'    DateTime
New-MdField 'FunctionalLocationRequests' 'IndexItemId'    Number
New-MdNoteField 'FunctionalLocationRequests' 'PayloadJson'
Set-PnPField -List 'FunctionalLocationRequests' -Identity 'Title' -Values @{ Title = 'RequestNo'; Indexed = $true }
Remove-FromDefaultView 'FunctionalLocationRequests' 'PayloadJson'

# ---------------------------------------------------------------------------
# FunctionalLocationItems - een raekke pr. FL
# ---------------------------------------------------------------------------
New-MdList 'FunctionalLocationItems' 'Functional Locations pr. anmodning, med spool-felter'
New-MdField 'FunctionalLocationItems' 'RequestGuid'             Text   -Indexed -Required
New-MdField 'FunctionalLocationItems' 'RequestId'               Number -Indexed
New-MdField 'FunctionalLocationItems' 'RowNo'                   Number
New-MdField 'FunctionalLocationItems' 'FunctionalLocation'      Text   -Indexed
New-MdField 'FunctionalLocationItems' 'Description'             Text
New-MdField 'FunctionalLocationItems' 'KksType'                 Text
New-MdField 'FunctionalLocationItems' 'AssignedClass'           Text   -Indexed
New-MdField 'FunctionalLocationItems' 'RowStatus'               Choice -Indexed -Choices $ROW_STATUS
New-MdField 'FunctionalLocationItems' 'FirstIssue'              Text
New-MdField 'FunctionalLocationItems' 'IssueCount'              Number
# Tre spool-felter staar OGSAA som egne kolonner, saa de kan filtreres i
# SharePoint. SCE er den, VH-plans prioritetsregel venter paa (docs/16).
New-MdField 'FunctionalLocationItems' 'TrmAssignment'           Text
New-MdField 'FunctionalLocationItems' 'AbcIndic'                Text
New-MdField 'FunctionalLocationItems' 'SafetyCriticalEquipment' Text   -Indexed
New-MdField 'FunctionalLocationItems' 'RequesterEmail'          Text   -Indexed
New-MdNoteField 'FunctionalLocationItems' 'SpoolValuesJson'
# Title er raekkens klientnoegle (GUID). Den er appens join-noegle mellem
# samlingen og listen, og det er den, der goer gem GENOPTAGELIGT: en raekke,
# der blev oprettet foer en fejl, findes igen paa RowGuid og oprettes ikke
# to gange. Se powerfx/04-submit-patch.fx.
Set-PnPField -List 'FunctionalLocationItems' -Identity 'Title' -Values @{ Title = 'RowGuid'; Indexed = $true }
Remove-FromDefaultView 'FunctionalLocationItems' 'SpoolValuesJson'

# ---------------------------------------------------------------------------
# MD_FLKey - noeglerne bag klassebestemmelsen (docs/16)
# ---------------------------------------------------------------------------
New-MdList 'MD_FLKey' 'Noegler til klassebestemmelse af Functional Locations (FL_LOOKUPS)'
New-MdField 'MD_FLKey' 'KeyType'     Text -Indexed -Required
New-MdField 'MD_FLKey' 'Value'       Text
New-MdField 'MD_FLKey' 'Description' Text
# Opslaget i appen er LookUp(MD_FLKey, KeyType = "Function" && KeyValue = k).
# Begge kolonner SKAL vaere indekseret: der er 6.441 funktionsnoegler, og
# uden indeks afviser SharePoint forespoergslen over 5.000 elementer.
Set-PnPField -List 'MD_FLKey' -Identity 'Title' -Values @{ Title = 'KeyValue'; Indexed = $true }

# ---------------------------------------------------------------------------
# Seed af MD_FLKey
# ---------------------------------------------------------------------------
if ($SeedMasterData -or $ReseedKeys) {
    Write-Host "`n=== Seed MD_FLKey ===" -ForegroundColor Cyan
    $path = Join-Path $PSScriptRoot '..\seed\MD_FLKey.csv'
    if (-not (Test-Path $path)) { throw "Finder ikke $path" }

    $existing = (Get-PnPList -Identity 'MD_FLKey').ItemCount
    if ($existing -gt 0 -and -not $ReseedKeys) {
        Write-Host "  = MD_FLKey har allerede $existing raekker - springer over (brug -ReseedKeys)" -ForegroundColor DarkGray
    } else {
        if ($existing -gt 0) {
            Write-Host "  - sletter $existing raekker" -ForegroundColor Yellow
            $del = New-PnPBatch
            Get-PnPListItem -List 'MD_FLKey' -PageSize 2000 | ForEach-Object {
                Remove-PnPListItem -List 'MD_FLKey' -Identity $_.Id -Batch $del
            }
            Invoke-PnPBatch -Batch $del
        }
        # 6.733 raekker: i batch, ellers er det 6.733 rundture.
        $batch = New-PnPBatch
        $n = 0
        Import-Csv $path -Encoding UTF8 | ForEach-Object {
            $values = @{ Title = $_.KeyValue; KeyType = $_.KeyType }
            if ($_.Value -ne '')       { $values.Value = $_.Value }
            if ($_.Description -ne '') { $values.Description = $_.Description }
            Add-PnPListItem -List 'MD_FLKey' -Values $values -Batch $batch
            $n++
            if ($n % 500 -eq 0) { Invoke-PnPBatch -Batch $batch; $batch = New-PnPBatch; Write-Host "    $n ..." }
        }
        Invoke-PnPBatch -Batch $batch
        Write-Host "  + MD_FLKey seedet med $n raekker" -ForegroundColor Green
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Tilfoej de tre lister + MD_RequestIndex som datakilder i appen i Studio."
Write-Host "  2. Koer sharepoint/inspect/Export-ListSchema.ps1, saa check_datasources.py"
Write-Host "     kan efterproeve kolonnerne."
Write-Host "  3. Verificer i Studio, at LookUp(MD_FLKey, KeyType = ""Function"" && KeyValue = ...)"
Write-Host "     IKKE giver en delegationsadvarsel."
