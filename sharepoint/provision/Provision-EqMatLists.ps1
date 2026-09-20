<#
.SYNOPSIS
    Provisionerer de SharePoint-lister, Equipment- og Materials-appen skal
    skrive i.

.DESCRIPTION
    FELTERNE ER LAEST AF APPERNE, IKKE VALGT HER
    -------------------------------------------
    Hver kolonne nedenfor svarer til eet felt i den Collect(), appen koerer,
    naar der trykkes "Save row":

        colEquipmentRows   ScreenEquipment.pa.yaml
        colMaterialRows    ScreenMaterialer.pa.yaml

    Begge samlinger lever KUN i hukommelsen. Lukker brugeren appen, er
    raekkerne vaek - der er ikke eet Patch mod en datakilde i nogen af de to
    apps. Det er praecis det hul, listerne her lukker.

    EEN LISTE PR. DOMAENE
    --------------------
    Apperne har ingen "indmeldingshoved" - der er een flad formular og en
    liste af raekker. Derfor er der ogsaa kun een liste pr. domaene. Det,
    der binder en portion raekker sammen, er RequestNo og RequestGuid, som
    skrives paa HVER raekke ved indsendelse, sammen med een raekke i
    MD_RequestIndex til landingssiden.

    En header-liste ville vaere en tom skal, saa laenge apperne ser saadan ud.

    Scriptet er idempotent og kan koeres igen, naar der kommer et felt mere.

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

.PARAMETER ClientId
    App-registreringen, logins skal gaa igennem. Standard er den app,
    resten af scriptene i mappen bruger. Kan ogsaa saettes med
    miljoevariablen PNP_CLIENT_ID.

.PARAMETER DeviceLogin
    Log ind med en kode i en browser i stedet for et popup-vindue. Brug
    den, naar det almindelige login-vindue ikke kan aabnes eller lukker
    sig selv.

.EXAMPLE
    .\Provision-EqMatLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDev"

.EXAMPLE
    .\Provision-EqMatLists.ps1 -SiteUrl "https://..." -Domain Equipment -WhatIfReport

.NOTES
    Kolonnernes INTERNE navne laases ved oprettelse og kan ikke aendres
    bagefter - derfor saettes -InternalName eksplicit overalt.

    Power Fx binder paa VISNINGSNAVN. Title bliver omdoebt, og appen skal
    bruge det NYE navn i sine Patch-kald. Et Patch med { Title: ... } rammer
    ved siden af. Samme faelde som i MD_RequestIndex.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [ValidateSet('Equipment', 'Material', 'Both')][string] $Domain = 'Both',
    [switch] $SkipLibrary,
    [string] $ClientId = $env:PNP_CLIENT_ID,
    [switch] $DeviceLogin
)

$ErrorActionPreference = 'Stop'

# Raekkens egen tilstand i appen - IKKE det faelles statusordforraad fra
# MD_RequestIndex. De to er forskellige ting: den her siger om raekken er
# udfyldt og afsendt, den anden siger hvor indmeldingen er i SAP-forloebet.
# Apperne skriver praecis disse to vaerdier og ingen andre.
$ROWSTATUS = 'valid', 'submitted'

# Dokumentbiblioteket. De tre attachment-flows er HAARDKODET til dette
# bibliotek - upload-flowet skriver i /TaskListDocuments/<mappe>/, og
# get-flowet slaar biblioteket op paa miljoevariablen
# BioSap-Library-TaskListDocuments. Derfor deler alle tre domaeneapps det
# samme bibliotek og holdes fra hinanden paa MAPPENAVNET.
$LIBRARY = 'TaskListDocuments'

# PnP.PowerShell 2.x har ikke laengere en faelles app-registrering, saa
# -Interactive KRAEVER et ClientId. Uden et gaar MSAL i gang mod en app,
# tenanten ikke kender, og fejler med "User canceled authentication" -
# hvilket lyder som om brugeren trykkede fortryd, men ikke er det.
#
# Appen nedenfor findes allerede i tenanten og bruges af de oevrige
# scripts i mappen. Et client id er ikke en hemmelighed; det er et navn,
# ikke en noegle - se docs/08-datamapning.md 6B.
$PNP_APP = '9bc3ab49-b65d-410a-85ad-de819febfddc'
if (-not $ClientId) { $ClientId = $PNP_APP }

$conn = @{ Url = $SiteUrl; ClientId = $ClientId }
if ($DeviceLogin) { $conn.DeviceLogin = $true } else { $conn.Interactive = $true }

try {
    Connect-PnPOnline @conn
}
catch {
    Write-Host ""
    Write-Host "Login mislykkedes: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "'User canceled authentication' betyder EN af to ting:" -ForegroundColor Yellow
    Write-Host "  1. Browservinduet blev lukket, foer login var faerdigt."
    Write-Host "  2. Appen $ClientId er ikke godkendt i tenanten, saa"
    Write-Host "     browseren viste 'Needs admin approval' i stedet for et login."
    Write-Host ""
    Write-Host "Virker browservinduet ikke, saa brug enhedslogin i stedet:" -ForegroundColor Yellow
    Write-Host "  .\sharepoint\provision\Provision-EqMatLists.ps1 ``"
    Write-Host "      -SiteUrl '$SiteUrl' -DeviceLogin"
    Write-Host ""
    Write-Host "Har du en anden app-registrering, saa giv den med:" -ForegroundColor Yellow
    Write-Host "  -ClientId <app id>"
    Write-Host ""
    Write-Host "Har du ingen, kan du oprette en:" -ForegroundColor Yellow
    Write-Host "  Register-PnPEntraIDAppForInteractiveLogin ``"
    Write-Host "      -ApplicationName 'PnP Masterdata' ``"
    Write-Host "      -Tenant <tenant>.onmicrosoft.com -Interactive"
    throw
}

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
    param([string]$List, [string]$NewName)
    Set-PnPField -List $List -Identity 'Title' -Values @{ Title = $NewName; Indexed = $true }
    Write-Host "    ~ Title -> $NewName" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Det der binder en portion raekker sammen
#
# Apperne har ingen header-formular, saa portionen findes kun som de samme
# vaerdier gentaget paa hver raekke. Det er ikke paent normaliseret, men det
# er hvad apperne kan levere - og det er nok til at finde en indmelding igen
# og til at haenge dokumenter paa den enkelte raekke.
# ---------------------------------------------------------------------------
function Add-BatchColumns {
    param([string]$List)

    # RowId er appens EGET loebenummer i colXxxRows. Det er ikke unikt paa
    # tvaers af indmeldinger - kun inden for een.
    New-MdField $List 'RowId'          Number

    New-MdField $List 'RequestNo'      Text -Indexed
    New-MdField $List 'RequestGuid'    Text -Indexed

    # ItemKey er raekkens noegle OG mappenavnet i dokumentbiblioteket.
    #
    # INDEKSERET, IKKE UNIK - og det er ikke en slendrian.
    #
    # Noeglen er "EQ-" & raekkens eget ID. Den kan derfor foerst dannes,
    # NAAR raekken findes, saa appen skriver raekken foerst og noeglen
    # bagefter. Med EnforceUniqueValues faldt det fra hinanden paa raekke
    # nummer to: SharePoint regner TOM som en vaerdi, og to raekker maa
    # ikke dele den - saa den anden raekke blev afvist med "this value
    # already exists", mens den foerste gik igennem.
    #
    # Og der er intet at beskytte: ID er unikt i forvejen, og noeglen er
    # lavet af det. Praefikset holder den fra hinanden paa tvaers af
    # domaener.
    #
    # -Values saettes eksplicit, saa en KOER IGEN ogsaa fjerner kravet fra
    # en liste, der allerede er oprettet med det.
    New-MdField $List 'ItemKey'        Text -Indexed
    Set-PnPField -List $List -Identity 'ItemKey' -Values @{ EnforceUniqueValues = $false }

    # Skrives eksplicit, selv om den kan regnes ud af ItemKey. Flowet
    # gaetter ikke, og den, der aabner listen i browseren, kan se hvor
    # dokumenterne ligger.
    New-MdField $List 'AttachmentFolder' Text
    New-MdField $List 'FileCount'      Number

    # TEKST, ikke Person. Person-kolonner kan ikke filtreres delegerbart,
    # og det er praecis det filter, "Mine indmeldinger" bygger paa.
    New-MdField $List 'RequesterEmail' Text -Indexed
    New-MdField $List 'RequesterName'  Text
    New-MdField $List 'SubmittedOn'    DateTime -Indexed

    # Raekkens egen tilstand. Apperne skriver "valid" ved Save row og
    # "submitted" ved Submit.
    New-MdField $List 'RowStatus'      Choice -Choices $ROWSTATUS -Indexed
}

# ---------------------------------------------------------------------------
# EQUIPMENT
#
# Kolonnerne er raekke for raekke den Collect(), ScreenEquipment.pa.yaml
# koerer ved "Save row". Staar der et felt her, som ikke er i appen, eller
# omvendt, er det en fejl - ikke en udvidelse.
# ---------------------------------------------------------------------------
function New-EquipmentList {
    Write-Host "`n=== EquipmentItems ===" -ForegroundColor Cyan
    New-MdList 'EquipmentItems' 'Een raekke pr. udstyr. Skrives af appen Equipments (colEquipmentRows).'

    # Description er raekkens tekst og dermed Title.
    Rename-TitleTo 'EquipmentItems' 'Description'
    Add-BatchColumns 'EquipmentItems'

    # Dropdown mod colEqRequestTypeOptions. Den samling defineres ikke i
    # appen (se .NOTES nederst), saa ordforraadet kendes ikke - kun at
    # standardvaerdien er "new". Derfor TEKST og ikke Choice: en
    # valgkolonne med gaettede vaerdier ville afvise alt andet.
    New-MdField 'EquipmentItems' 'RequestType'        Text -Indexed

    New-MdField 'EquipmentItems' 'Plant'              Text -Indexed
    New-MdField 'EquipmentItems' 'EquipmentNumber'    Text -Indexed
    New-MdField 'EquipmentItems' 'EquipmentCategory'  Text
    New-MdField 'EquipmentItems' 'Manufacturer'       Text
    New-MdField 'EquipmentItems' 'TypeDesignation'    Text
    New-MdField 'EquipmentItems' 'SerialNumber'       Text -Indexed

    New-MdField 'EquipmentItems' 'FunctionalLocation'  Text -Indexed
    New-MdField 'EquipmentItems' 'FunctionalLocation1' Text
    New-MdField 'EquipmentItems' 'FunctionalLocation2' Text

    New-MdField 'EquipmentItems' 'ClassData'          Text
    New-MdField 'EquipmentItems' 'RoomCoordinates'    Text
    New-MdField 'EquipmentItems' 'Placement'          Text

    # DATO, ikke tekst. Appen gemmer i dag
    #     Text(txtEqWarrantyStart.SelectedDate, "dd/mm/yyyy")
    # altsaa en formateret STRENG. Den kan ikke sorteres, ikke filtreres
    # paa interval, og betyder noget forskelligt alt efter hvilket
    # landeformat der laeser den. Kolonnen er en rigtig dato her, og appen
    # skal sende .SelectedDate direkte.
    New-MdField 'EquipmentItems' 'WarrantyStart'      DateTime
    New-MdField 'EquipmentItems' 'WarrantyEnd'        DateTime

    # DocumentType og DocumentLink er BEVIDST ikke her.
    #
    # De to felter er et link, brugeren selv skal skaffe - ikke en fil, der
    # ligger nogen steder. Dokumenterne haandteres i stedet af de tre
    # attachment-flows mod TaskListDocuments/<ItemKey>/, og saa er
    # ItemKey + AttachmentFolder + FileCount ovenfor hele modellen.
    #
    # Skal dokumenttypen overleve som en KATEGORI pr. fil (Datablad,
    # Manual, Tegning), hoerer den til som en kolonne paa biblioteket - paa
    # filen - og ikke paa udstyrsraekken. Det er en anden opgave.

    New-MdNoteField 'EquipmentItems' 'LongText' 10
}

# ---------------------------------------------------------------------------
# MATERIAL
#
# Samme regel: kolonnerne er den Collect(), ScreenMaterialer.pa.yaml koerer.
#
# Bemaerk at det IKKE er SAP's materialestamdata (MM01). Der er hverken
# materialenummer, materialetype eller materialegruppe. Det, appen samler
# ind, er reservedelsoplysninger: leverandoer, pris, leveringstid og
# anbefalet lager - knyttet til en funktionsplads.
# ---------------------------------------------------------------------------
function New-MaterialList {
    Write-Host "`n=== MaterialItems ===" -ForegroundColor Cyan
    New-MdList 'MaterialItems' 'Een raekke pr. materiale. Skrives af appen Materials (colMaterialRows).'

    Rename-TitleTo 'MaterialItems' 'MaterialDescription'
    Add-BatchColumns 'MaterialItems'

    New-MdField 'MaterialItems' 'Plant'               Text -Indexed
    New-MdField 'MaterialItems' 'FunctionalLocation'  Text -Indexed

    New-MdField 'MaterialItems' 'Manufacturer'        Text
    New-MdField 'MaterialItems' 'ModelNumber'         Text
    New-MdField 'MaterialItems' 'ManufacturerPartNo'  Text -Indexed

    New-MdField 'MaterialItems' 'Supplier'            Text
    New-MdField 'MaterialItems' 'SupplierPartNo'      Text

    # Tal, ikke tekst - appen sender allerede Value(...) og Blank().
    New-MdField 'MaterialItems' 'Price'               Number
    New-MdField 'MaterialItems' 'PriceUnit'           Text
    New-MdField 'MaterialItems' 'StockUnit'           Text
    New-MdField 'MaterialItems' 'DeliveringTime'      Number
    New-MdField 'MaterialItems' 'RecommendedStock'    Number

    # Dropdowns mod colYesNo, som heller ikke defineres i appen. Tekst af
    # samme grund som RequestType ovenfor - ikke Boolean: appen sender
    # .Selected.Value, altsaa etiketten, ikke sand/falsk.
    New-MdField 'MaterialItems' 'StrategicPart'       Text
    New-MdField 'MaterialItems' 'WearPart'            Text

    # Documentation er BEVIDST ikke her - samme grund som DocumentType og
    # DocumentLink paa udstyret.
    #
    # Feltet er i oevrigt vaerre end et link: ved siden af det staar
    # addMatFilePicker, som ved valg af en fil gemmer Self.FileName i
    # varFormDocumentation og ikke andet. Filen bliver ALDRIG lagt op.
    # Appen ser ud til at vedhaefte og gemmer et filnavn.
    New-MdNoteField 'MaterialItems' 'LongText' 10
}

# ---------------------------------------------------------------------------
# Standardvisninger
#
# Fields er INTERNE navne. Den omdoebte Title-kolonne hedder stadig 'Title'
# indeni - omdoebningen aendrer kun visningsnavnet, og en visning bygget paa
# 'Description' ville fejle med "kolonnen findes ikke".
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
# Dokumentbiblioteket
#
# Det oprettes ikke her, det KONTROLLERES. Findes det ikke, er sitet et
# andet end det, miljoevariablen BioSap-SiteUrl peger paa - og saa hjaelper
# det ikke at oprette et nyt tomt bibliotek ved siden af; saa ville
# VH-plan-appens dokumenter ligge et tredje sted.
# ---------------------------------------------------------------------------
function Test-DocumentLibrary {
    $lib = Get-PnPList -Identity $LIBRARY -ErrorAction SilentlyContinue
    Write-Host "`n=== Dokumentbibliotek ===" -ForegroundColor Cyan
    if ($lib) {
        Write-Host "  = '$LIBRARY' findes ($($lib.ItemCount) element(er))" -ForegroundColor DarkGray
        Write-Host "    id: $($lib.Id)" -ForegroundColor DarkGray
        Write-Host "    Hold det op mod miljoevariablen" -ForegroundColor DarkGray
        Write-Host "    BioSap-Library-TaskListDocuments." -ForegroundColor DarkGray
    } else {
        Write-Host "  ! '$LIBRARY' findes IKKE paa $SiteUrl" -ForegroundColor Red
        Write-Host ""
        Write-Host "    De tre attachment-flows er haardkodet til det bibliotek." -ForegroundColor Yellow
        Write-Host "    Enten er sitet et andet end det, BioSap-SiteUrl peger paa," -ForegroundColor Yellow
        Write-Host "    eller ogsaa er biblioteket ikke oprettet endnu. Ret det" -ForegroundColor Yellow
        Write-Host "    FOER dokumentruden tages i brug - ellers lander filerne" -ForegroundColor Yellow
        Write-Host "    ingen steder, og flowet svarer alligevel 'ingen filer'." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
Write-Host "`nProvisionerer mod $SiteUrl" -ForegroundColor Cyan

if ($Domain -eq 'Equipment' -or $Domain -eq 'Both') {
    New-EquipmentList
    Set-MdView 'EquipmentItems' @('Title', 'RequestNo', 'Plant', 'EquipmentNumber',
                                  'FunctionalLocation', 'SerialNumber', 'RowStatus',
                                  'RequesterEmail', 'SubmittedOn')
}

if ($Domain -eq 'Material' -or $Domain -eq 'Both') {
    New-MaterialList
    Set-MdView 'MaterialItems' @('Title', 'RequestNo', 'Plant', 'FunctionalLocation',
                                 'ManufacturerPartNo', 'Supplier', 'Price', 'RowStatus',
                                 'RequesterEmail', 'SubmittedOn')
}

if (-not $SkipLibrary) { Test-DocumentLibrary }

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Giv indmelderne Contribute paa listerne."
Write-Host "  2. Tilfoej listen som datakilde i appen i Studio."
Write-Host "  3. Apperne skriver INTET til SharePoint i dag - alt ligger i"
Write-Host "     colEquipmentRows / colMaterialRows og forsvinder, naar appen"
Write-Host "     lukkes. Gem-knappen skal have et Patch mod listen her."
Write-Host "  4. WarrantyStart/WarrantyEnd er DATO-kolonner. Appen sender i dag"
Write-Host "     Text(..., ""dd/mm/yyyy"") - send .SelectedDate direkte i stedet."
Write-Host "  5. Dokumentfelterne er ikke provisioneret. Dokumenter hoerer i"
Write-Host "     TaskListDocuments/<ItemKey>/ via de tre flows - se"
Write-Host "     docs/24-eq-mat-persistering.md."
