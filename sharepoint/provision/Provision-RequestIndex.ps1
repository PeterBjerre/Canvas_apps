<#
.SYNOPSIS
    Provisionerer MD_RequestIndex - den faelles indeksliste bag landingssiden
    (appen "Masterdata Hub").

.DESCRIPTION
    Landingssiden laeser KUN denne liste. De fem domaeneapps skriver hver en
    opsummeringsraekke hertil fra deres submit-flow, naar status aendrer sig.
    Se docs/07-landingsside.md.

    Scriptet er idempotent og kan koeres igen, naar der kommer nye kolonner.

.PARAMETER SiteUrl
    Url til det SharePoint-site, listen skal ligge paa.

.PARAMETER IncludeArchive
    Opretter ogsaa MD_RequestIndexArchive med samme kolonner, til afsluttede
    indmeldinger aeldre end 12 maaneder.

.PARAMETER AddSampleRows
    Laegger fire proeveraekker i listen, saa landingssiden kan afproeves,
    foer de fem submit-flows er bygget. Koer scriptet igen UDEN dette flag,
    naar de rigtige data begynder at komme ind, og slet proeveraekkerne.

.EXAMPLE
    .\Provision-RequestIndex.ps1 -SiteUrl "https://orsted.sharepoint.com/sites/SAPMasterdata"

.EXAMPLE
    .\Provision-RequestIndex.ps1 -SiteUrl "https://..." -AddSampleRows

.NOTES
    Kraever PnP.PowerShell:
        Install-Module PnP.PowerShell -Scope CurrentUser
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $IncludeArchive,
    [switch] $AddSampleRows,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Listen hedder det samme som LIST i "Masterdata Hub/build/hub_config.py".
$LIST_NAME = 'MD_RequestIndex'

# Den indbyggede Title-kolonne doebes om, saa listen er laesbar for dem der
# aabner den direkte. Power Fx binder paa VISNINGSNAVN, saa den samme streng
# staar som COL_NO i hub_config.py. Aendrer du den ene, skal du aendre begge.
$COL_NO = 'RequestNo'

# PnP.PowerShell 2.x har ikke laengere en faelles app-registrering, saa
# -Interactive kraever et ClientId. Saet PNP_CLIENT_ID som miljoevariabel,
# eller giv -ClientId. Har du ingen app endnu, opretter denne den:
#     Register-PnPEntraIDAppForInteractiveLogin ``
#         -ApplicationName "PnP Masterdata" -Tenant <tenant>.onmicrosoft.com -Interactive
$conn = @{ Url = $SiteUrl; Interactive = $true }
if ($ClientId) { $conn.ClientId = $ClientId }
Connect-PnPOnline @conn

function New-IdxList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
    Set-PnPList -Identity $Title -Description $Description
}

function New-IdxField {
    param([string]$List, [string]$Name, [string]$Type, [string[]]$Choices,
          [switch]$Indexed, [switch]$Required)
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    $values = @{}
    if ($Indexed)  { $values.Indexed  = $true }
    if ($Required) { $values.Required = $true }
    if ($values.Count) { Set-PnPField -List $List -Identity $Name -Values $values }
}

# Vaerdierne skal vaere ORDRET de samme som i hub_config.py (DOMAINS/STATUS).
# Landingssiden slaar op paa dem; en stavefejl giver en raekke uden farve og
# uden navn i stedet for en fejl man kan se.
$DOMAINS = 'FunctionalLocation','Equipment','MeasuringPoint','Material','MaintenancePlan'
$STATUS  = 'Kladde','Indsendt','UnderBehandling','AfventerInfo','KlarTilSAP',
           'OprettetISAP','Afvist','Annulleret'

function Add-IndexColumns {
    param([string]$List)

    # --- Nummeret ---------------------------------------------------------
    # Title genbruges som indmeldingsnummer. Den er obligatorisk i forvejen,
    # saa der er ingen vej udenom at bruge den til noget fornuftigt.
    Set-PnPField -List $List -Identity 'Title' -Values @{ Title = $COL_NO; Indexed = $true }

    # --- Det landingssiden grupperer og filtrerer paa ---------------------
    New-IdxField $List 'Domain'     Choice -Choices $DOMAINS -Indexed -Required
    New-IdxField $List 'Status'     Choice -Choices $STATUS  -Indexed -Required

    # 1-5. Hubben tegner forloebet uden at kende domaenespecifikke vaerdier.
    # 0 = afsluttet uden oprettelse (Afvist/Annulleret).
    New-IdxField $List 'StatusStep' Number

    # Et enkelt indekseret boolsk felt ER delegerbart. En raekke OR'ede
    # statusvaerdier er det IKKE - og koeen i landingssiden filtrerer paa
    # praecis dette felt. Saettes af submit-flowet sammen med Status.
    New-IdxField $List 'IsOpen'     Boolean -Indexed

    # --- Hvem ------------------------------------------------------------
    # TEKST, ikke Person. Person-kolonner kan ikke filtreres delegerbart i
    # SharePoint, og det er praecis det filter, "Mine indmeldinger" bygger
    # paa. Skriv User().Email i smaa bogstaver fra flowet.
    New-IdxField $List 'RequesterEmail'  Text -Indexed -Required
    New-IdxField $List 'RequesterName'   Text
    New-IdxField $List 'AssignedToEmail' Text -Indexed
    New-IdxField $List 'AssignedToName'  Text

    # --- Indholdet i raekken ---------------------------------------------
    New-IdxField $List 'ShortText'    Text            # vises som raekkens titel
    New-IdxField $List 'Plant'        Text -Indexed   # vaerk
    New-IdxField $List 'ItemCount'    Number
    New-IdxField $List 'SapObjectNo'  Text            # udfyldes naar SAP har oprettet

    # --- Tilbage til domaeneappen ----------------------------------------
    # RequestGuid saettes af domaeneappen og haenges paa AppUrl som ?reqid=,
    # saa "Aabn" lander paa den rigtige indmelding og ikke bare i appen.
    New-IdxField $List 'RequestGuid'  Text -Indexed
    New-IdxField $List 'SourceItemId' Number
    New-IdxField $List 'AppUrl'       Text

    # --- Sortering --------------------------------------------------------
    New-IdxField $List 'LastActionOn' DateTime -Indexed
    New-IdxField $List 'LastActionBy' Text
}

function Set-IdxView {
    param([string]$List)
    $cols = @($COL_NO, 'Domain', 'ShortText', 'Plant', 'Status', 'StatusStep',
              'IsOpen', 'RequesterEmail', 'LastActionOn', 'SapObjectNo')
    $view = Get-PnPView -List $List | Where-Object { $_.DefaultView } | Select-Object -First 1
    if ($view) {
        Set-PnPView -List $List -Identity $view.Id -Fields $cols -Values @{
            RowLimit = 50
            ViewQuery = "<OrderBy><FieldRef Name='LastActionOn' Ascending='FALSE'/></OrderBy>"
        }
        Write-Host "    ~ standardvisning sat" -ForegroundColor Green
    }
}

Write-Host "`n=== $LIST_NAME ===" -ForegroundColor Cyan
New-IdxList $LIST_NAME 'Faelles indeks over alle masterdata-indmeldinger. Laeses af landingssiden (Masterdata Hub).'
Add-IndexColumns $LIST_NAME
Set-IdxView $LIST_NAME

if ($IncludeArchive) {
    Write-Host "`n=== ${LIST_NAME}Archive ===" -ForegroundColor Cyan
    New-IdxList "${LIST_NAME}Archive" 'Afsluttede indmeldinger aeldre end 12 maaneder.'
    Add-IndexColumns "${LIST_NAME}Archive"
    Set-IdxView "${LIST_NAME}Archive"
}

if ($AddSampleRows) {
    Write-Host "`n=== Proeveraekker ===" -ForegroundColor Cyan
    # Den indloggede brugers mail, hentet eksplicit - CurrentUser kommer ikke
    # med Email udfyldt, foer den er loadet.
    $ctx = Get-PnPContext
    $cu  = $ctx.Web.CurrentUser
    $ctx.Load($cu)
    $ctx.ExecuteQuery()
    $me = if ($cu.Email) { $cu.Email.ToLower() } else { ($cu.LoginName -split '\|')[-1].ToLower() }
    Write-Host "    proeveraekkerne oprettes paa $me" -ForegroundColor DarkGray
    $rows = @(
        @{ Title='VHP-000101'; Domain='MaintenancePlan';    Status='Indsendt';        StatusStep=2; IsOpen=$true;
           ShortText='SSV Aarlig Rundering';        Plant='1000'; ItemCount=2; Days=0 },
        @{ Title='FL-000455';  Domain='FunctionalLocation'; Status='UnderBehandling'; StatusStep=3; IsOpen=$true;
           ShortText='HRN-01-ST-001 Stilladsplads';  Plant='1000'; ItemCount=1; Days=1 },
        @{ Title='EQ-000912';  Domain='Equipment';          Status='AfventerInfo';    StatusStep=3; IsOpen=$true;
           ShortText='Pumpe P-204 udskiftning';      Plant='2000'; ItemCount=1; Days=4 },
        @{ Title='MAT-001233'; Domain='Material';           Status='OprettetISAP';    StatusStep=5; IsOpen=$false;
           ShortText='Pakning DN80 EPDM';            Plant='2000'; ItemCount=3; Days=9 }
    )
    foreach ($r in $rows) {
        $q = "<View><Query><Where><Eq><FieldRef Name='Title'/>" +
             "<Value Type='Text'>$($r.Title)</Value></Eq></Where></Query></View>"
        $existing = Get-PnPListItem -List $LIST_NAME -Query $q
        if ($existing) {
            Write-Host "    = $($r.Title)" -ForegroundColor DarkGray
            continue
        }
        Add-PnPListItem -List $LIST_NAME -Values @{
            Title          = $r.Title
            Domain         = $r.Domain
            Status         = $r.Status
            StatusStep     = $r.StatusStep
            IsOpen         = $r.IsOpen
            ShortText      = $r.ShortText
            Plant          = $r.Plant
            ItemCount      = $r.ItemCount
            RequesterEmail = $me
            RequesterName  = 'Proevedata'
            RequestGuid    = [guid]::NewGuid().ToString()
            LastActionOn   = (Get-Date).AddDays(-1 * $r.Days)
            LastActionBy   = $me
        } | Out-Null
        Write-Host "    + $($r.Title)" -ForegroundColor Green
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Giv alle indmeldere Contribute paa listen. Hubben skriver ikke selv,"
Write-Host "     men de fem submit-flows goer."
Write-Host "  2. Tilfoej listen '$LIST_NAME' som datakilde i appen 'Masterdata Hub'."
Write-Host "  3. Verificer i Power Apps at"
Write-Host "       Filter('$LIST_NAME', RequesterEmail = Lower(User().Email))"
Write-Host "     og"
Write-Host "       Filter('$LIST_NAME', IsOpen = true)"
Write-Host "     IKKE giver en delegationsadvarsel (den blaa bolge under formlen)."
Write-Host "  4. Laeg opdateringen af indeksraekken i hvert domaenes SUBMIT-FLOW,"
Write-Host "     ikke i appen - saa kan den ikke glemmes ved et statusskift."
Write-Host "  5. Naar en domaeneapp er bygget: indsaet dens play-URL i DOMAINS i"
Write-Host "     'Masterdata Hub/build/hub_config.py', byg og synk. Flisen skifter"
Write-Host "     selv fra 'Kommer snart' til 'Opret ny'."
