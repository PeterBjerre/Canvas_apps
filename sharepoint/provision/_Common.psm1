<#
.SYNOPSIS
    Faelles hjaelpefunktioner til provisioneringsscripterne.

.DESCRIPTION
    New-MdList stod fire gange, New-MdField i tre udgaver, og app-id'et
    til login ti steder (REVIEW.md E8). Nu staar de her:

        Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
        Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

    Scripterne KALDER stadig New-MdList/New-MdField med listen og kolonnen
    som foerste argumenter - tools/check_datasources.py laeser kaldene og
    ved derfor, hvilke lister og kolonner provisioneringen opretter.

    Filen skal vaere ren ASCII med BOM (tools/check_ps1.py).
#>

# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Uden et fejler MSAL med "User canceled
# authentication" - hvilket lyder som om brugeren trykkede fortryd, men
# ikke er det. Appen nedenfor findes i tenanten. Et client id er ikke en
# hemmelighed; det er et navn, ikke en noegle - se docs/08-datamapning.md 6B.
$MdDefaultClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc'

function Connect-MdSite {
    param(
        [Parameter(Mandatory = $true)][string] $SiteUrl,
        [string] $ClientId,
        [switch] $DeviceLogin
    )
    if (-not $ClientId) { $ClientId = $MdDefaultClientId }
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
        Write-Host "Har du en anden app-registrering, saa giv den med -ClientId <app id>." -ForegroundColor Yellow
        Write-Host "Har du ingen, kan du oprette en:" -ForegroundColor Yellow
        Write-Host "  Register-PnPEntraIDAppForInteractiveLogin -ApplicationName 'PnP Masterdata' -Tenant <tenant>.onmicrosoft.com -Interactive"
        throw
    }
}

function New-MdList {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
    } else {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
        Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
    }
    if ($Description) { Set-PnPList -Identity $Title -Description $Description }
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

# Flerlinjet tekst som REN tekst. Rich text ville lade SharePoint saette
# HTML-tags ind i JSON'en, og saa kan hverken appen, flowet eller SAP's
# langtekstfelt laese den.
function New-MdNoteField {
    param([string]$List, [string]$Name, [int]$Lines = 6)
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } else {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type Note | Out-Null
        Write-Host "    + $Name (Note, plain)" -ForegroundColor Green
    }
    Set-PnPField -List $List -Identity $Name -Values @{ RichText = $false; NumberOfLines = $Lines }
}

# Title doebes om, saa listen er laesbar for dem, der aabner den direkte.
# Power Fx binder paa VISNINGSNAVNET.
function Rename-MdTitle {
    param([string]$List, [string]$NewName)
    Set-PnPField -List $List -Identity 'Title' -Values @{ Title = $NewName; Indexed = $true }
    Write-Host "    ~ Title -> $NewName" -ForegroundColor Green
}

# Indeksering af en kolonne, der findes i forvejen. Et filter paa en
# kolonne uden indeks fejler, naar listen passerer 5.000 elementer.
function Set-MdIndexed {
    param([string]$List, [string]$Name, [switch]$WhatIfOnly)
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $List.$Name findes ikke - springes over" -ForegroundColor Yellow
    } elseif ($f.Indexed) {
        Write-Host "    = $List.$Name er indekseret" -ForegroundColor DarkGray
    } elseif ($WhatIfOnly) {
        Write-Host "    ? $List.$Name ville blive indekseret" -ForegroundColor Yellow
    } else {
        Set-PnPField -List $List -Identity $Name -Values @{ Indexed = $true }
        Write-Host "    + $List.$Name indekseret" -ForegroundColor Green
    }
}

Export-ModuleMember -Function Connect-MdSite, New-MdList, New-MdField, New-MdNoteField,
    Rename-MdTitle, Set-MdIndexed -Variable MdDefaultClientId
