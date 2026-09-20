<#
.SYNOPSIS
    Provisionerer SharePoint-listerne til VH-plans appen.

.DESCRIPTION
    Idempotent: kan koeres flere gange. Eksisterende lister og kolonner
    springes over, saa scriptet ogsaa kan bruges til at tilfoeje nye felter
    senere.

    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser

.EXAMPLE
    .\Provision-VHPlanLists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/VHPlan"

.NOTES
    Koer mod DEV foerst. Kolonnernes INTERNE navne laases ved oprettelse og kan
    ikke aendres bagefter - derfor saetter scriptet -InternalName eksplicit.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $SeedMasterData,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Her stod kaldet helt uden, og saa fejler MSAL med
# "User canceled authentication" - hvilket lyder som om brugeren trykkede
# fortryd, men ikke er det.
# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

# ---------------------------------------------------------------------------
# Hjaelpefunktioner
# ---------------------------------------------------------------------------

function New-VhList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Set-PnPList -Identity $Title -Description $Description
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
}

function New-VhField {
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

# Note-kolonner (flerlinjet tekst) skal oprettes som "Note" og saettes til
# plain text - rich text goer JSON-payloaden ulaeselig, fordi SharePoint
# indsaetter HTML-tags.
function New-VhNoteField {
    param([string]$List, [string]$Name)
    if (-not (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue)) {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type Note | Out-Null
        Write-Host "    + $Name (Note, plain)" -ForegroundColor Green
    }
    Set-PnPField -List $List -Identity $Name -Values @{ RichText = $false; NumberOfLines = 6 }
}

Write-Host "`n=== Masterdata ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# MD_Strategy
# ---------------------------------------------------------------------------
New-VhList 'MD_Strategy' 'Vedligeholdsstrategier (spejlet fra SAP IP11)'
New-VhField 'MD_Strategy' 'StrategyText'        Text
New-VhField 'MD_Strategy' 'SchedIndicator'      Choice -Choices 'TIME','TIME_KEYDATE','TIME_FACTCAL','PERFORMANCE'
New-VhField 'MD_Strategy' 'PerformanceUnit'     Text
New-VhField 'MD_Strategy' 'CallHorizonPct'      Number
New-VhField 'MD_Strategy' 'SchedPeriod'         Number
New-VhField 'MD_Strategy' 'SchedPeriodUnit'     Choice -Choices 'DAY','WK','MON','YR'
New-VhField 'MD_Strategy' 'ShiftFactorLatePct'  Number
New-VhField 'MD_Strategy' 'ShiftFactorEarlyPct' Number
New-VhField 'MD_Strategy' 'ToleranceLatePct'    Number
New-VhField 'MD_Strategy' 'ToleranceEarlyPct'   Number
New-VhField 'MD_Strategy' 'FactoryCalendar'     Text
New-VhField 'MD_Strategy' 'Plant'               Text   -Indexed
New-VhField 'MD_Strategy' 'IsActive'            Boolean -Indexed
New-VhField 'MD_Strategy' 'SortOrder'           Number
Set-PnPField -List 'MD_Strategy' -Identity 'Title' -Values @{ Title = 'StrategyKey'; EnforceUniqueValues = $true; Indexed = $true }

# ---------------------------------------------------------------------------
# MD_StrategyPackage
# ---------------------------------------------------------------------------
New-VhList 'MD_StrategyPackage' 'Pakker pr. strategi'
New-VhField 'MD_StrategyPackage' 'StrategyKey'      Text   -Indexed -Required
New-VhField 'MD_StrategyPackage' 'PackageNo'        Number -Indexed -Required
New-VhField 'MD_StrategyPackage' 'CycleLength'      Number -Required
New-VhField 'MD_StrategyPackage' 'CycleUnit'        Choice -Choices 'DAY','WK','MON','YR','H','KM'
New-VhField 'MD_StrategyPackage' 'PackageText'      Text
New-VhField 'MD_StrategyPackage' 'ShortCode'        Text
New-VhField 'MD_StrategyPackage' 'Hierarchy'        Number
New-VhField 'MD_StrategyPackage' 'Offset'           Number
New-VhField 'MD_StrategyPackage' 'PrelimBufferDays' Number
New-VhField 'MD_StrategyPackage' 'SubseqBufferDays' Number
New-VhField 'MD_StrategyPackage' 'ColorHex'         Text
New-VhField 'MD_StrategyPackage' 'IsActive'         Boolean
# Titlen er den sammensatte noegle <strategi>-<pakkenr>. SharePoint kan kun
# haandhaeve unikhed paa een kolonne, saa det er den, der bruges til det.
Set-PnPField -List 'MD_StrategyPackage' -Identity 'Title' -Values @{ Title = 'PackageKey'; EnforceUniqueValues = $true; Indexed = $true }

# ---------------------------------------------------------------------------
# MD_ValueHelp - een generisk opslagsliste i stedet for otte smaa
# ---------------------------------------------------------------------------
New-VhList 'MD_ValueHelp' 'Generel opslagsliste - koder pr. domaene'
New-VhField 'MD_ValueHelp' 'Domain'      Text -Indexed -Required
New-VhField 'MD_ValueHelp' 'DisplayText' Text
New-VhField 'MD_ValueHelp' 'Plant'       Text -Indexed
New-VhField 'MD_ValueHelp' 'ParentCode'  Text
New-VhField 'MD_ValueHelp' 'IsActive'    Boolean -Indexed
New-VhField 'MD_ValueHelp' 'SortOrder'   Number
Set-PnPField -List 'MD_ValueHelp' -Identity 'Title' -Values @{ Title = 'Code'; Indexed = $true }

Write-Host "`n=== Transaktionsdata ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# VHP_Request
# ---------------------------------------------------------------------------
New-VhList 'VHP_Request' 'Anmodninger om nye vedligeholdsplaner'
New-VhField 'VHP_Request' 'RequestGuid'         Text -Indexed
New-VhField 'VHP_Request' 'Status'              Choice -Indexed -Choices 'Kladde','Indsendt','UnderBehandling','Afvist','KlarTilSAP','OprettetISAP','Fejlet','Annulleret'
New-VhField 'VHP_Request' 'PlanType'            Choice -Indexed -Choices 'SingleCycle','Strategy','MultipleCounter'
New-VhField 'VHP_Request' 'PlanDescription'     Text
New-VhField 'VHP_Request' 'PlanCategory'        Text
New-VhField 'VHP_Request' 'PlanSortField'       Text
New-VhField 'VHP_Request' 'PlanningPlant'       Text -Indexed
New-VhField 'VHP_Request' 'StrategyKey'         Text -Indexed
New-VhField 'VHP_Request' 'StrategyTextSnapshot' Text
New-VhField 'VHP_Request' 'SingleCycleLength'   Number
New-VhField 'VHP_Request' 'SingleCycleUnit'     Text
New-VhField 'VHP_Request' 'SchedIndicator'      Text
New-VhField 'VHP_Request' 'CycleStartDate'      DateTime
New-VhField 'VHP_Request' 'CallHorizonPct'      Number
New-VhField 'VHP_Request' 'SchedPeriod'         Number
New-VhField 'VHP_Request' 'SchedPeriodUnit'     Text
New-VhField 'VHP_Request' 'ShiftFactorLatePct'  Number
New-VhField 'VHP_Request' 'ShiftFactorEarlyPct' Number
New-VhField 'VHP_Request' 'ToleranceLatePct'    Number
New-VhField 'VHP_Request' 'ToleranceEarlyPct'   Number
New-VhField 'VHP_Request' 'CycleModFactor'      Number
New-VhField 'VHP_Request' 'CompletionRequired'  Boolean
New-VhField 'VHP_Request' 'FactoryCalendar'     Text
New-VhField 'VHP_Request' 'Requester'           User
New-VhField 'VHP_Request' 'RequesterDept'       Text
New-VhNoteField 'VHP_Request' 'Justification'
New-VhField 'VHP_Request' 'ApprovedBy'          User
New-VhField 'VHP_Request' 'ApprovedOn'          DateTime
New-VhNoteField 'VHP_Request' 'RejectReason'
New-VhNoteField 'VHP_Request' 'PayloadJson'
New-VhField 'VHP_Request' 'SapMaintPlanNo'      Text -Indexed
New-VhField 'VHP_Request' 'SapTaskListGroups'   Text
New-VhField 'VHP_Request' 'SapCreatedOn'        DateTime
New-VhField 'VHP_Request' 'SapCreatedBy'        Text
New-VhField 'VHP_Request' 'IntegrationStatus'   Choice -Choices 'NotSent','Sent','Ack','Error'
New-VhNoteField 'VHP_Request' 'IntegrationMessage'
New-VhField 'VHP_Request' 'IntegrationRetries'  Number
Set-PnPField -List 'VHP_Request' -Identity 'Title' -Values @{ Title = 'RequestNo'; Indexed = $true }

# PayloadJson maa ALDRIG med i standardvisningen - Note-kolonner goer
# galleriets datahentning markant tungere.
Set-PnPField -List 'VHP_Request' -Identity 'PayloadJson' -Values @{ Hidden = $false }
$view = Get-PnPView -List 'VHP_Request' -Identity 'All Items' -ErrorAction SilentlyContinue
if ($view -and $view.ViewFields -contains 'PayloadJson') {
    $view.ViewFields.Remove('PayloadJson'); $view.Update(); Invoke-PnPQuery
}

# ---------------------------------------------------------------------------
# VHP_Item
# ---------------------------------------------------------------------------
New-VhList 'VHP_Item' 'Vedligeholdspositioner'
New-VhField 'VHP_Item' 'RequestId'        Number -Indexed -Required
New-VhField 'VHP_Item' 'ItemNo'           Number
New-VhField 'VHP_Item' 'ObjectType'       Choice -Choices 'FunctionalLocation','Equipment','Assembly','NoObject'
New-VhField 'VHP_Item' 'FunctionalLocation' Text
New-VhField 'VHP_Item' 'EquipmentNo'      Text
New-VhField 'VHP_Item' 'AssemblyNo'       Text
New-VhField 'VHP_Item' 'PlannerGroupCode' Text
New-VhField 'VHP_Item' 'MainWorkCenter'   Text
New-VhField 'VHP_Item' 'OrderType'        Text
New-VhField 'VHP_Item' 'ActivityType'     Text
New-VhField 'VHP_Item' 'BusinessArea'     Text
New-VhField 'VHP_Item' 'Priority'         Text
New-VhField 'VHP_Item' 'NotifType'        Text
New-VhField 'VHP_Item' 'TaskListMode'     Choice -Choices 'Existing','New','None'
New-VhField 'VHP_Item' 'TaskListType'     Text
New-VhField 'VHP_Item' 'TaskListGroup'    Text
New-VhField 'VHP_Item' 'TaskListCounter'  Text
New-VhField 'VHP_Item' 'TaskListId'       Number -Indexed

# ---------------------------------------------------------------------------
# VHP_ItemObject
# ---------------------------------------------------------------------------
New-VhList 'VHP_ItemObject' 'Objektliste pr. position'
New-VhField 'VHP_ItemObject' 'ItemId'     Number -Indexed -Required
New-VhField 'VHP_ItemObject' 'RequestId'  Number -Indexed
New-VhField 'VHP_ItemObject' 'ObjectType' Choice -Choices 'FunctionalLocation','Equipment','Assembly'
New-VhField 'VHP_ItemObject' 'ObjectNo'   Text
New-VhField 'VHP_ItemObject' 'SortNo'     Number

# ---------------------------------------------------------------------------
# VHP_TaskList
# ---------------------------------------------------------------------------
New-VhList 'VHP_TaskList' 'Oenskede nye arbejdsplaner'
New-VhField 'VHP_TaskList' 'RequestId'        Number -Indexed -Required
New-VhField 'VHP_TaskList' 'TaskListType'     Text
New-VhField 'VHP_TaskList' 'StrategyKey'      Text
New-VhField 'VHP_TaskList' 'Plant'            Text
New-VhField 'VHP_TaskList' 'UsageCode'        Text
New-VhField 'VHP_TaskList' 'PlannerGroupCode' Text
New-VhField 'VHP_TaskList' 'WorkCenter'       Text
New-VhField 'VHP_TaskList' 'SystemCondition'  Text
New-VhField 'VHP_TaskList' 'ExistingGroup'    Text

# ---------------------------------------------------------------------------
# VHP_Operation - baerer pakkeallokeringen i PackagesKey
# ---------------------------------------------------------------------------
New-VhList 'VHP_Operation' 'Operationer og pakkeallokering'
New-VhField 'VHP_Operation' 'TaskListId'      Number -Indexed -Required
New-VhField 'VHP_Operation' 'RequestId'       Number -Indexed
New-VhField 'VHP_Operation' 'OperationNo'     Text
New-VhNoteField 'VHP_Operation' 'LongText'
New-VhField 'VHP_Operation' 'WorkCenter'      Text
New-VhField 'VHP_Operation' 'ControlKey'      Text
New-VhField 'VHP_Operation' 'Plant'           Text
New-VhField 'VHP_Operation' 'Work'            Number
New-VhField 'VHP_Operation' 'WorkUnit'        Text
New-VhField 'VHP_Operation' 'NumberOfPeople'  Number
New-VhField 'VHP_Operation' 'Duration'        Number
New-VhField 'VHP_Operation' 'DurationUnit'    Text
New-VhField 'VHP_Operation' 'SystemCondition' Text
# Formatet er ";1;3;5;" - sentinel-separator i begge ender, saa ";1;" aldrig
# matcher inde i ";12;". Standardvaerdien er ";", aldrig tom.
New-VhField 'VHP_Operation' 'PackagesKey'     Text
New-VhField 'VHP_Operation' 'PackagesDisplay' Text
New-VhField 'VHP_Operation' 'SortOrder'       Number
Set-PnPField -List 'VHP_Operation' -Identity 'PackagesKey' -Values @{ DefaultValue = ';'; MaxLength = 255 }

# ---------------------------------------------------------------------------
# VHP_StatusLog
# ---------------------------------------------------------------------------
New-VhList 'VHP_StatusLog' 'Statushistorik'
New-VhField 'VHP_StatusLog' 'RequestId'  Number -Indexed -Required
New-VhField 'VHP_StatusLog' 'FromStatus' Text
New-VhField 'VHP_StatusLog' 'ToStatus'   Text
New-VhField 'VHP_StatusLog' 'ActionBy'   User
New-VhField 'VHP_StatusLog' 'ActionOn'   DateTime
New-VhNoteField 'VHP_StatusLog' 'Comment'

# ---------------------------------------------------------------------------
# VHP_ClientLog - uden denne er fejlsoegning i produktion gaetteri
# ---------------------------------------------------------------------------
New-VhList 'VHP_ClientLog' 'Klientfejl fra appen'
New-VhField 'VHP_ClientLog' 'RequestId' Number -Indexed
New-VhField 'VHP_ClientLog' 'Screen'    Text
New-VhField 'VHP_ClientLog' 'UserEmail' Text
New-VhNoteField 'VHP_ClientLog' 'ErrorText'

# ---------------------------------------------------------------------------
# Seed af masterdata (valgfrit)
# ---------------------------------------------------------------------------
if ($SeedMasterData) {
    Write-Host "`n=== Seed ===" -ForegroundColor Cyan
    $seedDir = Join-Path $PSScriptRoot '..\seed'

    foreach ($f in @(
        @{ File = 'MD_Strategy.csv';        List = 'MD_Strategy'        },
        @{ File = 'MD_StrategyPackage.csv'; List = 'MD_StrategyPackage' },
        @{ File = 'MD_ValueHelp.csv';       List = 'MD_ValueHelp'       }
    )) {
        $path = Join-Path $seedDir $f.File
        if (-not (Test-Path $path)) { Write-Warning "Springer over: $path"; continue }

        Import-Csv $path | ForEach-Object {
            $values = @{}
            $_.PSObject.Properties | ForEach-Object {
                if ($_.Value -ne '') {
                    # Boolean-kolonner skal sendes som $true/$false, ikke "TRUE"
                    $values[$_.Name] = switch -Regex ($_.Value) {
                        '^(?i)true$'  { $true }
                        '^(?i)false$' { $false }
                        default       { $_.Value }
                    }
                }
            }
            Add-PnPListItem -List $f.List -Values $values | Out-Null
        }
        Write-Host "  + $($f.List) seedet fra $($f.File)" -ForegroundColor Green
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Saet item-level permissions paa VHP_Request"
Write-Host "     (Listeindstillinger > Avanceret > kun egne elementer)."
Write-Host "  2. Verificer i Power Apps, at Filter(MD_ValueHelp, Domain = ...)"
Write-Host "     IKKE giver en delegationsadvarsel."
