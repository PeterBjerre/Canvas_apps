<#
.SYNOPSIS
    Provisionerer MD_RequestIndex - den faelles indeksliste bag landingssiden.

.DESCRIPTION
    Landingssiden laeser KUN denne liste. De fem domaeneapps skriver hver en
    opsummeringsraekke hertil, naar status aendrer sig. Se
    docs/07-landingsside.md.

    Idempotent: kan koeres flere gange.

.EXAMPLE
    .\Provision-RequestIndex.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/SAPMasterdata"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $IncludeArchive
)

$ErrorActionPreference = 'Stop'
Connect-PnPOnline -Url $SiteUrl -Interactive

function New-IdxList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Set-PnPList -Identity $Title -Description $Description
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
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
    if ($Indexed)  { Set-PnPField -List $List -Identity $Name -Values @{ Indexed = $true } }
    if ($Required) { Set-PnPField -List $List -Identity $Name -Values @{ Required = $true } }
}

$DOMAINS = 'FunctionalLocation','Equipment','MeasuringPoint','Material','MaintenancePlan'
$STATUS  = 'Kladde','Indsendt','UnderBehandling','AfventerInfo','KlarTilSAP',
           'OprettetISAP','Afvist','Annulleret'

function Add-IndexColumns {
    param([string]$List)

    # Domaene og status baerer hele oversigten - begge indekseret.
    New-IdxField $List 'Domain'      Choice -Choices $DOMAINS -Indexed -Required
    New-IdxField $List 'Status'      Choice -Choices $STATUS  -Indexed -Required
    # 1-5. Hubben tegner forloebet uden at kende domaenespecifikke vaerdier.
    New-IdxField $List 'StatusStep'  Number

    # Et enkelt indekseret boolsk felt er delegerbart. En raekke OR'ede
    # statusvaerdier er det ikke - og koeen i landingssiden filtrerer paa
    # praecis dette felt. Saettes af submit-flowet sammen med Status.
    New-IdxField $List 'IsOpen'      Boolean -Indexed

    New-IdxField $List 'RequestGuid' Text -Indexed

    # TEKST, ikke Person. Person-kolonner kan ikke filtreres delegerbart i
    # SharePoint, og det er praecis det filter, landingssiden bygger paa.
    New-IdxField $List 'RequesterEmail'  Text -Indexed -Required
    New-IdxField $List 'RequesterName'   Text
    New-IdxField $List 'AssignedToEmail' Text -Indexed
    New-IdxField $List 'AssignedToName'  Text

    New-IdxField $List 'ShortText'    Text
    New-IdxField $List 'Plant'        Text -Indexed
    New-IdxField $List 'ItemCount'    Number
    New-IdxField $List 'SapObjectNo'  Text
    New-IdxField $List 'SourceItemId' Number
    New-IdxField $List 'AppUrl'       Text
    New-IdxField $List 'LastActionOn' DateTime -Indexed
    New-IdxField $List 'LastActionBy' Text

    Set-PnPField -List $List -Identity 'Title' -Values @{ Title = 'RequestNo'; Indexed = $true }
}

Write-Host "`n=== MD_RequestIndex ===" -ForegroundColor Cyan
New-IdxList 'MD_RequestIndex' 'Faelles indeks over alle masterdata-indmeldinger. Laeses af landingssiden.'
Add-IndexColumns 'MD_RequestIndex'

if ($IncludeArchive) {
    Write-Host "`n=== MD_RequestIndexArchive ===" -ForegroundColor Cyan
    New-IdxList 'MD_RequestIndexArchive' 'Afsluttede indmeldinger aeldre end 12 maaneder.'
    Add-IndexColumns 'MD_RequestIndexArchive'
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
Write-Host "Naeste skridt:" -ForegroundColor Yellow
Write-Host "  1. Giv alle indmeldere Contribute paa listen - hubben skriver ikke,"
Write-Host "     men de fem submit-flows goer."
Write-Host "  2. Verificer i Power Apps at"
Write-Host "     Filter(MD_RequestIndex, RequesterEmail = User().Email)"
Write-Host "     IKKE giver en delegationsadvarsel."
Write-Host "  3. Laeg opdateringen af indeksraekken i hvert domaenes SUBMIT-FLOW,"
Write-Host "     ikke i appen - saa kan den ikke glemmes ved statusskift."
