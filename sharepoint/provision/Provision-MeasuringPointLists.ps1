<#
.SYNOPSIS
    Provisionerer de SharePoint-lister, Measuring Point-appen skal skrive
    i og laese fra (issue #210, fase 0).

.DESCRIPTION
    TRE TING
    --------
        MeasuringPointItems    een raekke pr. maalepunkt. Skrives af
                               Measuring Point-skaermen i BIO SAP App
                               (colDomRows -> Patch, samme moenster som
                               EquipmentItems og MaterialItems).
        MD_MpCharacteristic    opslagslisten bag feltet Characteristic.
                               Karakteristik og enhed haenger sammen
                               (issue #210 Q3): man vaelger
                               karakteristikken, og enheden foelger med.
                               Indholdet er Master Datas udtraek fra SAP
                               (Q18) - seedet i repoet er faa tydelige
                               eksempler og to pladsholdere.
        MD_Approver            raekker til PRODOS/SRO-opretteren, een pr.
                               vaerk (Q17). De ligger i den EKSISTERENDE
                               godkendertabel med noeglen 'PRODOS-<vaerk>',
                               saa der hverken skal en ny kolonne eller en
                               ny liste til. Listen og dens kolonner
                               oprettes af Provision-VHPlanApproval.ps1;
                               her laegges kun raekkerne.

    FELTERNE ER LAEST AF APPEN, IKKE VALGT HER
    ------------------------------------------
    Hver kolonne svarer til eet felt i
    "Measuring Point App/build/domain_config.py" (SECTIONS, READ_FIELDS).
    tools/check_datasources.py efterproever det ved hver bygning - saa
    snart listen er med i et nyt skemaudtraek.

    Scriptet er idempotent og kan koeres igen, naar der kommer et felt mere.

    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser

.PARAMETER SiteUrl
    Url til SharePoint-sitet. Det SKAL vaere det samme site, som
    miljoevariablen BioSap-SiteUrl peger paa - ellers finder
    attachment-flowene ikke dokumentbiblioteket.

.PARAMETER Seed
    Indlaeser sharepoint/seed/MD_MpCharacteristic.csv og
    sharepoint/seed/MD_Approver_MeasuringPoint.csv. Raekker, der findes i
    forvejen, OPDATERES ikke - de er SharePoints nu.

.PARAMETER Force
    Med -Seed: overskriv ogsaa de raekker, der findes.

.PARAMETER CharacteristicSeedPath
    Et andet udtraek end seedet i repoet - fx Master Datas egen fil med
    de karakteristikker, der bruges til maalepunkter i SAP (CT04).
    Kolonnerne skal hedde det samme som i seedet.

.EXAMPLE
    .\Provision-MeasuringPointLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDev"

.EXAMPLE
    .\Provision-MeasuringPointLists.ps1 -SiteUrl "https://..." -Seed

.EXAMPLE
    .\Provision-MeasuringPointLists.ps1 -SiteUrl "https://..." -Seed -CharacteristicSeedPath C:\temp\CT04-udtraek.csv

.NOTES
    Kolonnernes INTERNE navne laases ved oprettelse og kan ikke aendres
    bagefter - derfor saettes -InternalName eksplicit overalt (New-MdField).

    Power Fx binder paa VISNINGSNAVN. Title bliver omdoebt til Description
    paa MeasuringPointItems, og appen bruger det NYE navn i sine Patch-kald.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Seed,
    [switch] $Force,
    [string] $CharacteristicSeedPath,
    [string] $ApproverSeedPath,
    [string] $ClientId = $env:PNP_CLIENT_ID,
    [switch] $DeviceLogin
)

$ErrorActionPreference = 'Stop'

# Raekkens egen tilstand i appen - IKKE det faelles statusordforraad fra
# MD_RequestIndex. Praecis de samme tre vaerdier som EquipmentItems og
# MaterialItems, fordi raekkerne haandteres af de samme byggeklodser
# (tools/domain_parts.py).
$ROWSTATUS = 'draft', 'valid', 'submitted'

# Ja/nej-spoergsmaalene gemmes som TEKST ("Yes"/"No"), ikke Boolean: en
# Boolean kan ikke skelne "ikke besvaret" fra "No", og saa kan "kraevet"
# ikke kontrolleres (plan #210 afsnit 4).
$YESNO = 'Yes', 'No'

# Maalepunktets type. Appens ordforraad; Counter er en taeller, og
# Measuring Point er en maaling (issue #210 Q1).
$MPTYPE = 'Counter', 'MeasuringPoint'

# Hvor en manglende taeller skal oprettes (Q7).
$COUNTERIN = 'PRODOS', 'SRO'

# Vaerkerne med en PRODOS/SRO-opretter (Q7). De samme seks som i PlantList.
$PLANTS = 'AVV', 'ASV', 'HEV', 'KYV', 'SKV', 'SSV'

# Dokumentbiblioteket. De tre attachment-flows er haardkodet til det, og
# domaenerne holdes fra hinanden paa MAPPENAVNET (raekkens ItemKey).
$LIBRARY = 'TaskListDocuments'

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId -DeviceLogin:$DeviceLogin

if (-not $CharacteristicSeedPath) {
    $CharacteristicSeedPath = Join-Path $PSScriptRoot '..\seed\MD_MpCharacteristic.csv'
}
if (-not $ApproverSeedPath) {
    $ApproverSeedPath = Join-Path $PSScriptRoot '..\seed\MD_Approver_MeasuringPoint.csv'
}

# ---------------------------------------------------------------------------
# MeasuringPointItems
#
# Faelleskolonnerne er de samme som i Provision-EqMatLists.ps1. De staar
# skrevet ud her med listenavnet som litteral, saa
# tools/check_datasources.py kan se dem.
# ---------------------------------------------------------------------------
function New-MeasuringPointList {
    Write-Host "`n=== MeasuringPointItems ===" -ForegroundColor Cyan
    New-MdList 'MeasuringPointItems' 'Een raekke pr. maalepunkt. Skrives af Measuring Point-skaermen i BIO SAP App (issue #210).'

    # Description er raekkens tekst og dermed Title - som i EquipmentItems.
    Rename-MdTitle 'MeasuringPointItems' 'Description'

    # --- det, der binder en portion raekker sammen -------------------------
    New-MdField 'MeasuringPointItems' 'RowId'            Number
    New-MdField 'MeasuringPointItems' 'RequestNo'        Text -Indexed
    New-MdField 'MeasuringPointItems' 'RequestGuid'      Text -Indexed

    # ItemKey er raekkens noegle OG mappenavnet i dokumentbiblioteket.
    # INDEKSERET, IKKE UNIK: noeglen er "MP-" & raekkens eget ID og kan
    # derfor foerst dannes, NAAR raekken findes. Med EnforceUniqueValues
    # ville raekke nummer to blive afvist paa den tomme vaerdi.
    New-MdField 'MeasuringPointItems' 'ItemKey'          Text -Indexed
    Set-PnPField -List 'MeasuringPointItems' -Identity 'ItemKey' -Values @{ EnforceUniqueValues = $false }

    New-MdField 'MeasuringPointItems' 'AttachmentFolder' Text
    New-MdField 'MeasuringPointItems' 'FileCount'        Number

    # TEKST, ikke Person: et Person-filter kan ikke delegeres, og det er
    # praecis det filter, "mine raekker" bygger paa.
    New-MdField 'MeasuringPointItems' 'RequesterEmail'   Text -Indexed
    New-MdField 'MeasuringPointItems' 'RequesterName'    Text
    New-MdField 'MeasuringPointItems' 'SubmittedOn'      DateTime -Indexed
    New-MdField 'MeasuringPointItems' 'RowStatus'        Choice -Choices $ROWSTATUS -Indexed

    # --- hvor maalepunktet sidder ----------------------------------------
    New-MdField 'MeasuringPointItems' 'Plant'              Text -Indexed
    # Der vaelges altid en funktionsplads (Q4). Udstyrsmaalepunkter kommer
    # senere, og EquipmentNumber provisioneres derfor ikke endnu.
    New-MdField 'MeasuringPointItems' 'FunctionalLocation' Text -Indexed

    # --- findes det allerede? --------------------------------------------
    New-MdField 'MeasuringPointItems' 'ExistsInSap'        Choice -Choices $YESNO
    # Samme navn som den gamle kolonne i MaintenanceItems, saa ordforraadet
    # er det samme paa tvaers af apperne.
    New-MdField 'MeasuringPointItems' 'MeasuringPoint'     Text -Indexed

    # --- type og karakteristik -------------------------------------------
    New-MdField 'MeasuringPointItems' 'MeasuringPointType' Choice -Choices $MPTYPE
    # Karakteristikken, beskrivelsen og enheden KOPIERES fra
    # MD_MpCharacteristic ved valg, saa raekken er selvstaendig, hvis
    # opslagslisten senere aendres.
    New-MdField 'MeasuringPointItems' 'Characteristic'     Text -Indexed
    New-MdField 'MeasuringPointItems' 'CharacteristicDescription'     Text
    New-MdField 'MeasuringPointItems' 'CharacteristicUnit'            Text
    New-MdField 'MeasuringPointItems' 'CharacteristicUnitDescription' Text
    New-MdField 'MeasuringPointItems' 'DecimalPlaces'      Number
    # Afledt af typen (Q14) - appen skriver den, men viser den ikke som et
    # felt, man kan saette.
    New-MdField 'MeasuringPointItems' 'IsCounter'          Boolean

    # --- maalingens vaerdier (kun type Measuring Point) -------------------
    New-MdField 'MeasuringPointItems' 'TargetValue'        Number
    New-MdField 'MeasuringPointItems' 'LowerLimit'         Number
    New-MdField 'MeasuringPointItems' 'UpperLimit'         Number

    # --- taelleren (kun type Counter) ------------------------------------
    New-MdField 'MeasuringPointItems' 'ExpectedAnnualUsage' Number

    # --- hvor aflaesningen kommer fra ------------------------------------
    New-MdField 'MeasuringPointItems' 'InProdos'            Choice -Choices $YESNO
    # Samme betydning som MaintenanceItems.PRODOSTAG.
    New-MdField 'MeasuringPointItems' 'ProdosTag'           Text -Indexed
    New-MdField 'MeasuringPointItems' 'ProdosCounterExists' Choice -Choices $YESNO
    New-MdField 'MeasuringPointItems' 'CounterCreateIn'     Choice -Choices $COUNTERIN

    # --- godkendelse og de to eksterne trin ------------------------------
    # Skrives af appen ved gem (ny Counter = godkendelse, Q1/Q16) og
    # fastfryses, naar raekken laases ved Submit.
    New-MdField 'MeasuringPointItems' 'ApprovalRequired'   Boolean
    # Saettes, naar PRODOS/SRO-taelleren er markeret oprettet (Q7).
    New-MdField 'MeasuringPointItems' 'CounterCreatedOn'   DateTime
    New-MdField 'MeasuringPointItems' 'CounterCreatedBy'   Text
    # Nummeret fra SAP. Udfyldes i foerste version i haanden af Master Data
    # eller en admin i Details (Q8, Q19); senere af kvitteringsflowet.
    New-MdField 'MeasuringPointItems' 'CreatedMeasuringPointNo' Text -Indexed

    New-MdNoteField 'MeasuringPointItems' 'Remarks'  6
    New-MdNoteField 'MeasuringPointItems' 'SapResult' 6
}

# ---------------------------------------------------------------------------
# MD_MpCharacteristic - karakteristik og enhed (Q3, Q18)
# ---------------------------------------------------------------------------
function New-CharacteristicList {
    Write-Host "`n=== MD_MpCharacteristic ===" -ForegroundColor Cyan
    New-MdList 'MD_MpCharacteristic' 'Karakteristikker til maalepunkter (SAP CT04). Karakteristikken bestemmer enheden. Vedligeholdes af Master Data (issue #210).'

    # Title er karakteristikkens navn, som det staar i SAP (RUNNING_HOURS).
    # Den er obligatorisk i forvejen og bruges derfor til noeglen.
    Set-PnPField -List 'MD_MpCharacteristic' -Identity 'Title' -Values @{ Indexed = $true; Required = $true }
    Write-Host "    ~ Title: indekseret og kraevet" -ForegroundColor Green

    New-MdField 'MD_MpCharacteristic' 'Description'          Text
    New-MdField 'MD_MpCharacteristic' 'Unit'                 Text -Required
    New-MdField 'MD_MpCharacteristic' 'UnitDescription'      Text
    # Tom = karakteristikken kan bruges til begge typer.
    New-MdField 'MD_MpCharacteristic' 'MeasuringPointType'   Choice -Choices $MPTYPE
    New-MdField 'MD_MpCharacteristic' 'DefaultDecimalPlaces' Number
    New-MdField 'MD_MpCharacteristic' 'Active'               Boolean
}

# ---------------------------------------------------------------------------
# Standardvisninger
#
# Fields er INTERNE navne. Den omdoebte Title-kolonne hedder stadig 'Title'
# indeni - en visning bygget paa 'Description' ville fejle.
# ---------------------------------------------------------------------------
function Set-MdView {
    param([string]$List, [string[]]$Fields)
    $view = Get-PnPView -List $List | Where-Object { $_.DefaultView } | Select-Object -First 1
    if (-not $view) { return }
    Set-PnPView -List $List -Identity $view.Id -Fields $Fields -Values @{
        RowLimit  = 50
        ViewQuery = "<OrderBy><FieldRef Name='Modified' Ascending='FALSE'/></OrderBy>"
    }
    Write-Host "    ~ standardvisning sat paa $List" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
function Seed-Characteristics {
    if (-not (Test-Path $CharacteristicSeedPath)) {
        throw "Finder ikke $CharacteristicSeedPath"
    }
    Write-Host "`n=== MD_MpCharacteristic - seed ===" -ForegroundColor Cyan
    Write-Host "  Fra $CharacteristicSeedPath" -ForegroundColor DarkGray
    $rows = Import-Csv -Path $CharacteristicSeedPath -Encoding UTF8
    $index = @{}
    foreach ($it in (Get-PnPListItem -List 'MD_MpCharacteristic' -PageSize 500)) {
        $index[[string]$it.FieldValues.Title] = $it
    }
    $added = 0; $kept = 0; $updated = 0
    foreach ($r in $rows) {
        $key = $r.Title.Trim()
        if (-not $key) { continue }
        $values = @{
            Title                 = $key
            Description           = $r.Description
            Unit                  = $r.Unit
            UnitDescription       = $r.UnitDescription
            DefaultDecimalPlaces  = [int]$r.DefaultDecimalPlaces
            Active                = [bool]::Parse($r.Active)
        }
        # Tom type betyder "begge typer" - saa skal kolonnen ikke saettes.
        if ($r.MeasuringPointType -and $r.MeasuringPointType.Trim()) {
            $values.MeasuringPointType = $r.MeasuringPointType.Trim()
        }
        if ($index.ContainsKey($key)) {
            if ($Force) {
                Set-PnPListItem -List 'MD_MpCharacteristic' -Identity $index[$key].Id -Values $values | Out-Null
                $updated++
            } else {
                $kept++
            }
        } else {
            Add-PnPListItem -List 'MD_MpCharacteristic' -Values $values | Out-Null
            $added++
        }
    }
    $msg = "  {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
    Write-Host $msg -ForegroundColor Green
    Write-Host "  Seedet i repoet er EKSEMPLER og pladsholdere. Laeg Master Datas" -ForegroundColor Yellow
    Write-Host "  udtraek ind med -CharacteristicSeedPath <fil> -Force." -ForegroundColor Yellow
}

function Seed-ProdosCreators {
    if (-not (Test-Path $ApproverSeedPath)) { throw "Finder ikke $ApproverSeedPath" }
    if (-not (Get-PnPList -Identity 'MD_Approver' -ErrorAction SilentlyContinue)) {
        Write-Host "`n! MD_Approver findes ikke. Koer Provision-VHPlanApproval.ps1 foerst." -ForegroundColor Red
        return
    }
    Write-Host "`n=== MD_Approver - PRODOS/SRO-opretter pr. vaerk ===" -ForegroundColor Cyan
    Write-Host "  Fra $ApproverSeedPath" -ForegroundColor DarkGray
    $rows = Import-Csv -Path $ApproverSeedPath -Encoding UTF8
    $index = @{}
    foreach ($it in (Get-PnPListItem -List 'MD_Approver' -PageSize 500)) {
        $index[[string]$it.FieldValues.Title] = $it
    }
    $added = 0; $kept = 0; $updated = 0
    foreach ($r in $rows) {
        $key = $r.ApproverKey.Trim()
        if (-not $key) { continue }
        # Noeglen er rollen OG vaerket: PRODOS-SSV. Systemgodkenderne hedder
        # 1-16, vaerksgodkenderne SSV, og omkostningsgodkenderen COST - saa
        # rollen kan skelnes uden en ny kolonne (Q17).
        if ($key -notmatch '^PRODOS-[A-Z]{3}$') {
            throw "Noeglen '$key' er ikke paa formen PRODOS-<vaerk>."
        }
        $plant = $key.Substring(7)
        if ($PLANTS -notcontains $plant) {
            Write-Host "  ! $key - '$plant' er ikke et af vaerkerne $($PLANTS -join ', ')" -ForegroundColor Yellow
        }
        $values = @{
            Title           = $key
            Approver1       = $r.Approver1.Trim().ToUpper()
            Approver2       = $r.Approver2.Trim().ToUpper()
            Approver1Absent = [bool]::Parse($r.Approver1Absent)
            Notes           = $r.Notes
        }
        if ($index.ContainsKey($key)) {
            if ($Force) {
                Set-PnPListItem -List 'MD_Approver' -Identity $index[$key].Id -Values $values | Out-Null
                $updated++
            } else {
                $kept++
            }
        } else {
            Add-PnPListItem -List 'MD_Approver' -Values $values | Out-Null
            $added++
        }
    }
    $msg = "  {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
    Write-Host $msg -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`nProvisionerer mod $SiteUrl" -ForegroundColor Cyan

New-MeasuringPointList
Set-MdView 'MeasuringPointItems' @('Title', 'RequestNo', 'Plant', 'FunctionalLocation',
                                   'MeasuringPoint', 'MeasuringPointType', 'Characteristic',
                                   'RowStatus', 'RequesterEmail', 'SubmittedOn')

New-CharacteristicList
Set-MdView 'MD_MpCharacteristic' @('Title', 'Description', 'Unit', 'UnitDescription',
                                   'MeasuringPointType', 'DefaultDecimalPlaces', 'Active')

if ($Seed) {
    Seed-Characteristics
    Seed-ProdosCreators
}

$lib = Get-PnPList -Identity $LIBRARY -ErrorAction SilentlyContinue
Write-Host "`n=== Dokumentbibliotek ===" -ForegroundColor Cyan
if ($lib) {
    Write-Host "  = '$LIBRARY' findes ($($lib.ItemCount) element(er))" -ForegroundColor DarkGray
} else {
    Write-Host "  ! '$LIBRARY' findes IKKE paa $SiteUrl - dokumentruden kan ikke bruges" -ForegroundColor Red
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Giv indmelderne Contribute paa MeasuringPointItems og Read paa MD_MpCharacteristic."
Write-Host "  2. Koer sharepoint/inspect/Export-ListSchema.ps1, saa skemaet kender de to lister."
Write-Host "  3. Tilfoej MeasuringPointItems og MD_MpCharacteristic som datakilder i BIO SAP App i Studio."
Write-Host "  4. Laeg Master Datas CT04-udtraek i MD_MpCharacteristic - appen kan ikke oprette"
Write-Host "     nye maalepunkter, foer listen har karakteristikker."
