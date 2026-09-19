<#
.SYNOPSIS
    Provisionerer de SharePoint-lister, Equipment- og Materials-appen
    skriver i.

.DESCRIPTION
    De to apps er de domaeneapps, der mangler bag EQ- og MAT-fliserne paa
    landingssiden. De arbejder som VH-plan-appen:

        een INDMELDING (header)  ->  EquipmentRequests / MaterialRequests
        een eller flere POSTER   ->  EquipmentItems    / MaterialItems
        een raekke i indekset    ->  MD_RequestIndex   (allerede provisioneret)

    Indekset roeres IKKE her - det hoerer til Provision-RequestIndex.ps1 og
    deles af alle fem domaener.

    Scriptet er idempotent. Eksisterende lister og kolonner springes over,
    saa det ogsaa kan koeres igen, naar der kommer et felt mere.

    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser

.PARAMETER SiteUrl
    Url til SharePoint-sitet. Det SKAL vaere det samme site, som
    miljoevariablen BioSap-SiteUrl peger paa - ellers finder
    attachment-flowene ikke dokumentbiblioteket.

.PARAMETER Domain
    Equipment, Material eller Both. Standard er Both.

.PARAMETER SkipLibrary
    Spring kontrollen af dokumentbiblioteket over.

.EXAMPLE
    .\Provision-EqMatLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDev"

.EXAMPLE
    .\Provision-EqMatLists.ps1 -SiteUrl "https://..." -Domain Equipment

.NOTES
    Kolonnernes INTERNE navne laases ved oprettelse og kan ikke aendres
    bagefter - derfor saettes -InternalName eksplicit overalt.

    Power Fx binder paa VISNINGSNAVN. Title bliver derfor omdoebt, og
    appen skal bruge det NYE navn i sine Patch-kald. Et Patch med
    { Title: ... } rammer ved siden af. Samme faelde som i MD_RequestIndex.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [ValidateSet('Equipment', 'Material', 'Both')][string] $Domain = 'Both',
    [switch] $SkipLibrary,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Det faelles ordforraad. ORDRET det samme som i Provision-RequestIndex.ps1
# og i "Masterdata Hub/build/hub_config.py". En stavefejl her giver en
# raekke uden farve og uden navn paa landingssiden - ikke en fejl, man kan se.
# ---------------------------------------------------------------------------
$STATUS = 'Kladde', 'Indsendt', 'UnderBehandling', 'AfventerInfo', 'KlarTilSAP',
          'OprettetISAP', 'Afvist', 'Annulleret'

# Dokumentbiblioteket. De tre attachment-flows er HAARDKODET til dette
# bibliotek - upload-flowet skriver i /TaskListDocuments/<mappe>/, og
# get-flowet slaar biblioteket op paa miljoevariablen
# BioSap-Library-TaskListDocuments. Derfor deler alle tre domaeneapps det
# samme bibliotek og holdes fra hinanden paa MAPPENAVNET i stedet.
# Se docs/23-eq-mat-apps.md.
$LIBRARY = 'TaskListDocuments'

$conn = @{ Url = $SiteUrl; Interactive = $true }
if ($ClientId) { $conn.ClientId = $ClientId }
Connect-PnPOnline @conn

# ---------------------------------------------------------------------------
# Hjaelpefunktioner
# ---------------------------------------------------------------------------

function New-MdList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
    Set-PnPList -Identity $Title -Description $Description
}

function New-MdField {
    param(
        [string]$List, [string]$Name, [string]$Type,
        [string[]]$Choices, [switch]$Indexed, [switch]$Required, [switch]$Unique
    )
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    # Unikhed kraever indeksering, og indekseringen skal vaere paa plads FOER
    # listen passerer 5.000 elementer.
    $values = @{}
    if ($Indexed -or $Unique) { $values.Indexed = $true }
    if ($Required)            { $values.Required = $true }
    if ($values.Count)        { Set-PnPField -List $List -Identity $Name -Values $values }
    if ($Unique) {
        Set-PnPField -List $List -Identity $Name -Values @{ EnforceUniqueValues = $true }
    }
}

# Flerlinjet tekst skal vaere PLAIN. Rich text goer JSON-payloaden ulaeselig,
# fordi SharePoint indsaetter HTML-tags - og det er den tekst, der skal
# videre til SAP's langtekstfelt.
function New-MdNoteField {
    param([string]$List, [string]$Name, [int]$Lines = 6)
    if (-not (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue)) {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type Note | Out-Null
        Write-Host "    + $Name (Note, plain)" -ForegroundColor Green
    } else {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    }
    Set-PnPField -List $List -Identity $Name -Values @{ RichText = $false; NumberOfLines = $Lines }
}

function Rename-TitleTo {
    param([string]$List, [string]$NewName, [switch]$Unique)
    $values = @{ Title = $NewName; Indexed = $true }
    if ($Unique) { $values.EnforceUniqueValues = $true }
    Set-PnPField -List $List -Identity 'Title' -Values $values
    Write-Host "    ~ Title -> $NewName" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Headeren. Den er ENS for de to domaener - det er posterne, der er
# forskellige. Derfor een funktion og ikke to naesten ens blokke.
# ---------------------------------------------------------------------------
function Add-RequestHeader {
    param([string]$List)

    # Indmeldingsnummeret, fx EQ-000912. Kolonnen hedder det SAMME som i
    # MD_RequestIndex - RequestNo - saa den, der laeser paa tvaers, ikke
    # skal holde styr paa to navne for det samme tal. Praefikset sidder i
    # VAERDIEN, ikke i kolonnenavnet.
    Rename-TitleTo $List 'RequestNo' -Unique

    # Saettes af appen og haenges paa play-URL'en som ?reqid=, saa "Open"
    # paa landingssiden lander paa den rigtige indmelding.
    New-MdField $List 'RequestGuid'      Text -Indexed

    New-MdField $List 'Status'           Choice -Choices $STATUS -Indexed -Required
    New-MdField $List 'StatusStep'       Number
    New-MdField $List 'IsOpen'           Boolean -Indexed

    # TEKST, ikke Person. Person-kolonner kan ikke filtreres delegerbart, og
    # det er praecis det filter, "Mine indmeldinger" bygger paa. Skriv
    # Lower(User().Email).
    New-MdField $List 'RequesterEmail'   Text -Indexed -Required
    New-MdField $List 'RequesterName'    Text
    New-MdField $List 'AssignedToEmail'  Text -Indexed
    New-MdField $List 'AssignedToName'   Text

    New-MdField $List 'Plant'            Text -Indexed
    New-MdField $List 'ShortText'        Text
    New-MdField $List 'ItemCount'        Number

    New-MdField $List 'SubmittedOn'      DateTime
    New-MdField $List 'LastActionOn'     DateTime -Indexed
    New-MdField $List 'LastActionBy'     Text

    New-MdNoteField $List 'Comments'
}

# Faelles for begge postlister: koblingen op til headeren, og mappen i
# dokumentbiblioteket.
function Add-ItemCommon {
    param([string]$List)

    New-MdField $List 'RequestNo' Text   -Indexed -Required
    New-MdField $List 'RequestId' Number -Indexed
    New-MdField $List 'LineId'    Number

    # ItemKey er postens noegle OG mappenavnet i dokumentbiblioteket -
    # samme konstruktion som MI0007 i VH-plan-appen. Den skal derfor vaere
    # unik paa tvaers af HELE listen, ikke bare inden for indmeldingen:
    # to mapper med samme navn ville dele dokumenter.
    New-MdField $List 'ItemKey'            Text -Unique -Required

    # Skrives eksplicit, selv om den kan regnes ud af ItemKey. Flowet
    # gaetter ikke, og den, der aabner listen i browseren, kan se hvor
    # dokumenterne ligger.
    New-MdField $List 'AttachmentFolder'   Text

    New-MdField $List 'FileCount'          Number
}

# ---------------------------------------------------------------------------
# EQUIPMENT
#
# Felterne foelger SAP's udstyrsstamdata (IE01). De er grupperet som
# fanerne i SAP, saa listen kan holdes op mod skaermbilledet felt for felt.
# Koder er TEKST, ikke Choice: de kommer fra SAP og aendrer sig uden at
# nogen spoerger SharePoint. Kun de vokabularer, der er lukkede i SAP
# selv, staar som Choice.
# ---------------------------------------------------------------------------
function New-EquipmentLists {
    Write-Host "`n=== EquipmentRequests ===" -ForegroundColor Cyan
    New-MdList 'EquipmentRequests' 'Indmeldinger af udstyrsstamdata (EQ). Headeren - posterne staar i EquipmentItems.'
    Add-RequestHeader 'EquipmentRequests'

    Write-Host "`n=== EquipmentItems ===" -ForegroundColor Cyan
    New-MdList 'EquipmentItems' 'Een raekke pr. udstyr i en EQ-indmelding.'

    # EQKTX. 40 tegn i SAP - SharePoint haandhaever det ikke, appen goer.
    Rename-TitleTo 'EquipmentItems' 'EquipmentText'
    Add-ItemCommon 'EquipmentItems'

    # --- hvad der skal ske ------------------------------------------------
    New-MdField 'EquipmentItems' 'ChangeType' Choice -Choices 'Create','Change','Dismantle','Scrap' -Required
    # Tom ved Create - udfyldes af SAP, og skrives tilbage af flowet.
    New-MdField 'EquipmentItems' 'EquipmentNo'       Text -Indexed

    # --- generelt ---------------------------------------------------------
    # EQTYP. Lukket vokabular i SAP.
    New-MdField 'EquipmentItems' 'EquipmentCategory' Choice -Choices 'M','S','P','Q','F' -Required
    New-MdField 'EquipmentItems' 'TechObjectType'    Text     # EQART
    New-MdField 'EquipmentItems' 'InventoryNo'       Text
    New-MdField 'EquipmentItems' 'SerialNumber'      Text
    New-MdField 'EquipmentItems' 'Quantity'          Number
    New-MdField 'EquipmentItems' 'BaseUnit'          Text
    New-MdField 'EquipmentItems' 'StartUpDate'       DateTime
    New-MdField 'EquipmentItems' 'AcquisitionValue'  Number
    New-MdField 'EquipmentItems' 'Currency'          Text
    New-MdField 'EquipmentItems' 'AcquisitionDate'   DateTime
    New-MdField 'EquipmentItems' 'ManufacturerName'  Text     # HERST
    New-MdField 'EquipmentItems' 'ManufPartNo'       Text     # TYPBZ
    New-MdField 'EquipmentItems' 'ManufSerialNo'     Text     # SERGE
    New-MdField 'EquipmentItems' 'ManufCountry'      Text     # HERLD
    New-MdField 'EquipmentItems' 'ConstructionYear'  Number   # BAUJJ
    New-MdField 'EquipmentItems' 'ConstructionMonth' Number   # BAUMM
    New-MdField 'EquipmentItems' 'SizeDimension'     Text     # GROES
    New-MdField 'EquipmentItems' 'Weight'            Number
    New-MdField 'EquipmentItems' 'WeightUnit'        Text

    # --- placering --------------------------------------------------------
    New-MdField 'EquipmentItems' 'MaintPlant'        Text -Indexed   # SWERK
    New-MdField 'EquipmentItems' 'Location'          Text            # STORT
    New-MdField 'EquipmentItems' 'Room'              Text            # MSGRP
    New-MdField 'EquipmentItems' 'PlantSection'      Text            # BEBER
    New-MdField 'EquipmentItems' 'WorkCenter'        Text            # INGRP-arbejdsplads
    New-MdField 'EquipmentItems' 'ABCIndicator'      Choice -Choices 'A','B','C'
    New-MdField 'EquipmentItems' 'SortField'         Text            # EQFNR

    # --- organisation -----------------------------------------------------
    New-MdField 'EquipmentItems' 'PlanningPlant'     Text            # IWERK
    New-MdField 'EquipmentItems' 'PlannerGroup'      Text            # INGRP
    New-MdField 'EquipmentItems' 'MainWorkCenter'    Text            # GEWRK
    New-MdField 'EquipmentItems' 'CatalogProfile'    Text            # RBNR
    New-MdField 'EquipmentItems' 'BusinessArea'      Text            # GSBER
    New-MdField 'EquipmentItems' 'CostCenter'        Text            # KOSTL
    New-MdField 'EquipmentItems' 'CompanyCode'       Text            # BUKRS
    New-MdField 'EquipmentItems' 'WBSElement'        Text            # PROID

    # --- struktur ---------------------------------------------------------
    New-MdField 'EquipmentItems' 'FunctionalLocation'  Text -Indexed # TPLNR
    New-MdField 'EquipmentItems' 'SuperiorEquipment'   Text          # HEQUI
    New-MdField 'EquipmentItems' 'PositionInFl'        Text          # HEQNR

    New-MdNoteField 'EquipmentItems' 'LongText' 10
}

# ---------------------------------------------------------------------------
# MATERIAL
#
# Felterne foelger SAP's materialestamdata (MM01), grupperet efter de
# visninger, der skal udfyldes for et reservedelsmateriale: Grunddata,
# Indkoeb, Disponering, Lager og Regnskab.
# ---------------------------------------------------------------------------
function New-MaterialLists {
    Write-Host "`n=== MaterialRequests ===" -ForegroundColor Cyan
    New-MdList 'MaterialRequests' 'Indmeldinger af materialestamdata (MAT). Headeren - posterne staar i MaterialItems.'
    Add-RequestHeader 'MaterialRequests'

    Write-Host "`n=== MaterialItems ===" -ForegroundColor Cyan
    New-MdList 'MaterialItems' 'Een raekke pr. materiale i en MAT-indmelding.'

    # MAKTX. 40 tegn i SAP.
    Rename-TitleTo 'MaterialItems' 'MaterialText'
    Add-ItemCommon 'MaterialItems'

    # --- hvad der skal ske ------------------------------------------------
    # Extend = materialet findes, men skal udvides til et nyt vaerk eller
    # lagersted. Det er en anden transaktion i SAP end en aendring.
    New-MdField 'MaterialItems' 'ChangeType' Choice -Choices 'Create','Change','Extend','Block' -Required
    # Tom ved Create - udfyldes af SAP.
    New-MdField 'MaterialItems' 'MaterialNo'       Text -Indexed

    # --- grunddata --------------------------------------------------------
    New-MdField 'MaterialItems' 'MaterialType'     Choice -Choices 'ERSA','HIBE','NLAG','UNBW','DIEN','HALB','FERT','ROH' -Required
    New-MdField 'MaterialItems' 'IndustrySector'   Choice -Choices 'M','C','P','A' -Required
    New-MdField 'MaterialItems' 'MaterialGroup'    Text -Indexed -Required   # MATKL
    New-MdField 'MaterialItems' 'BaseUnit'         Text -Required            # MEINS
    New-MdField 'MaterialItems' 'OldMaterialNo'    Text                      # BISMT
    New-MdField 'MaterialItems' 'ManufacturerName' Text                      # MFRNR
    New-MdField 'MaterialItems' 'ManufPartNo'      Text                      # MFRPN
    New-MdField 'MaterialItems' 'GrossWeight'      Number
    New-MdField 'MaterialItems' 'NetWeight'        Number
    New-MdField 'MaterialItems' 'WeightUnit'       Text
    New-MdField 'MaterialItems' 'Volume'           Number
    New-MdField 'MaterialItems' 'VolumeUnit'       Text
    New-MdField 'MaterialItems' 'SizeDimension'    Text
    New-MdField 'MaterialItems' 'EAN'              Text

    # --- hvor ------------------------------------------------------------
    New-MdField 'MaterialItems' 'Plant'            Text -Indexed -Required   # WERKS
    New-MdField 'MaterialItems' 'StorageLocation'  Text                      # LGORT
    New-MdField 'MaterialItems' 'StorageBin'       Text                      # LGPBE

    # --- indkoeb ----------------------------------------------------------
    New-MdField 'MaterialItems' 'PurchasingGroup'      Text                  # EKGRP
    New-MdField 'MaterialItems' 'PurchaseOrderUnit'    Text                  # BSTME
    New-MdField 'MaterialItems' 'PlannedDeliveryTime'  Number                # PLIFZ
    New-MdField 'MaterialItems' 'GRProcessingTime'     Number                # WEBAZ
    New-MdField 'MaterialItems' 'PreferredVendor'      Text

    # --- disponering ------------------------------------------------------
    New-MdField 'MaterialItems' 'MRPType'            Text                    # DISMM
    New-MdField 'MaterialItems' 'MRPController'      Text                    # DISPO
    New-MdField 'MaterialItems' 'ProcurementType'    Choice -Choices 'E','F','X'
    New-MdField 'MaterialItems' 'SpecialProcurement' Text                    # SOBSL
    New-MdField 'MaterialItems' 'LotSizeKey'         Text                    # DISLS
    New-MdField 'MaterialItems' 'ReorderPoint'       Number                  # MINBE
    New-MdField 'MaterialItems' 'SafetyStock'        Number                  # EISBE
    New-MdField 'MaterialItems' 'MinLotSize'         Number
    New-MdField 'MaterialItems' 'MaxLotSize'         Number
    New-MdField 'MaterialItems' 'RoundingValue'      Number

    # --- regnskab ---------------------------------------------------------
    New-MdField 'MaterialItems' 'ValuationClass' Text                        # BKLAS
    New-MdField 'MaterialItems' 'PriceControl'   Choice -Choices 'S','V'
    New-MdField 'MaterialItems' 'StandardPrice'  Number
    New-MdField 'MaterialItems' 'PriceUnit'      Number
    New-MdField 'MaterialItems' 'Currency'       Text

    # --- styring ----------------------------------------------------------
    New-MdField 'MaterialItems' 'SerialNoProfile' Text                       # SERNP
    New-MdField 'MaterialItems' 'BatchManaged'    Boolean                    # XCHPF
    New-MdField 'MaterialItems' 'ABCIndicator'    Choice -Choices 'A','B','C'
    New-MdField 'MaterialItems' 'IsSpare'         Boolean

    # --- hvad det sidder i ------------------------------------------------
    # Et reservedelsmateriale giver foerst mening, naar man ved hvad det
    # hoerer til. Begge er tekst og ikke opslag: udstyret kan vaere meldt
    # ind i samme ombaering og har derfor ikke noget SAP-nummer endnu.
    New-MdField 'MaterialItems' 'FunctionalLocation' Text -Indexed
    New-MdField 'MaterialItems' 'EquipmentNo'        Text -Indexed

    New-MdNoteField 'MaterialItems' 'LongText' 10
}

# ---------------------------------------------------------------------------
# Standardvisninger. Uden dem viser listen Title og intet andet, og saa er
# den ubrugelig for den, der aabner den i browseren for at se hvad appen
# har skrevet.
# ---------------------------------------------------------------------------
# Fields er INTERNE navne. Den omdoebte Title-kolonne hedder stadig 'Title'
# indeni - omdoebningen aendrer kun visningsnavnet, og en visning bygget paa
# 'RequestNo' ville fejle med "kolonnen findes ikke".
function Set-MdView {
    param([string]$List, [string[]]$Fields, [string]$OrderBy)
    $view = Get-PnPView -List $List | Where-Object { $_.DefaultView } | Select-Object -First 1
    if (-not $view) { return }
    Set-PnPView -List $List -Identity $view.Id -Fields $Fields -Values @{
        RowLimit  = 50
        ViewQuery = "<OrderBy><FieldRef Name='$OrderBy' Ascending='FALSE'/></OrderBy>"
    }
    Write-Host "    ~ standardvisning sat paa $List" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Dokumentbiblioteket
#
# Det oprettes ikke her, det KONTROLLERES. Findes det ikke, er det fordi
# sitet er et andet end det, miljoevariablen BioSap-SiteUrl peger paa - og
# saa hjaelper det ikke at oprette et nyt tomt bibliotek ved siden af; saa
# ville VH-plan-appens dokumenter ligge et tredje sted.
# ---------------------------------------------------------------------------
function Test-DocumentLibrary {
    $lib = Get-PnPList -Identity $LIBRARY -ErrorAction SilentlyContinue
    Write-Host "`n=== Dokumentbibliotek ===" -ForegroundColor Cyan
    if ($lib) {
        Write-Host "  = '$LIBRARY' findes ($($lib.ItemCount) element(er))" -ForegroundColor DarkGray
        Write-Host "    id: $($lib.Id)" -ForegroundColor DarkGray
        Write-Host "    Det er dette id, miljoevariablen" -ForegroundColor DarkGray
        Write-Host "    BioSap-Library-TaskListDocuments skal have." -ForegroundColor DarkGray
    } else {
        Write-Host "  ! '$LIBRARY' findes IKKE paa $SiteUrl" -ForegroundColor Red
        Write-Host ""
        Write-Host "    De tre attachment-flows er haardkodet til det bibliotek." -ForegroundColor Yellow
        Write-Host "    Enten er sitet et andet end det, BioSap-SiteUrl peger paa," -ForegroundColor Yellow
        Write-Host "    eller ogsaa er biblioteket ikke oprettet endnu. Ret det" -ForegroundColor Yellow
        Write-Host "    FOER appene tages i brug - ellers lander dokumenterne" -ForegroundColor Yellow
        Write-Host "    ingen steder, og flowet svarer alligevel 'ingen filer'." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
Write-Host "`nProvisionerer mod $SiteUrl" -ForegroundColor Cyan

$headerView = @('Title', 'Status', 'ShortText', 'Plant', 'ItemCount',
                'RequesterEmail', 'LastActionOn')

if ($Domain -eq 'Equipment' -or $Domain -eq 'Both') {
    New-EquipmentLists
    Set-MdView 'EquipmentRequests' $headerView 'LastActionOn'
    Set-MdView 'EquipmentItems' @('Title', 'RequestNo', 'ItemKey', 'ChangeType',
                                  'EquipmentCategory', 'FunctionalLocation', 'MaintPlant',
                                  'EquipmentNo') 'Modified'
}

if ($Domain -eq 'Material' -or $Domain -eq 'Both') {
    New-MaterialLists
    Set-MdView 'MaterialRequests' $headerView 'LastActionOn'
    Set-MdView 'MaterialItems' @('Title', 'RequestNo', 'ItemKey', 'ChangeType',
                                 'MaterialType', 'MaterialGroup', 'Plant',
                                 'MaterialNo') 'Modified'
}

if (-not $SkipLibrary) { Test-DocumentLibrary }

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Giv indmelderne Contribute paa de fire lister."
Write-Host "  2. Tilfoej listerne som datakilder i de to apps i Studio."
Write-Host "  3. Tilfoej de tre flows som datakilder i BEGGE apps:"
Write-Host "       BioSap-TaskListAttachment"
Write-Host "       BioSap-GetSubmittedAttachments"
Write-Host "       BioSap-DeleteSubmittedAttachments"
Write-Host "  4. Koer  python3 tools/build_all.py  og deploy med"
Write-Host "       python tools/canvas_mcp.py deploy --app equipment"
Write-Host "       python tools/canvas_mcp.py deploy --app material"
