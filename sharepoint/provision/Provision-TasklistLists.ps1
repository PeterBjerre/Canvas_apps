<#
.SYNOPSIS
    Opretter MD_TasklistMaterial og MD_TasklistAttachment.

.DESCRIPTION
    Materialerne og dokumenterne hoerer til ARBEJDSPLANEN, ikke til planen -
    derfor Tasklist i navnet. Et materiale hoerer til EEN operation, et
    dokument til nul, een eller flere.

    HVORFOR IKKE BARE KOLONNER PAA TaskListMain
    -------------------------------------------
    Strategipakkerne ligger som en kolonne (PackagesKey, ";1;3;"), og det
    virker, fordi en pakke er en REFERENCE til en raekke i en anden liste.
    Et saet referencer fylder fint i en streng.

    Materialer kan ikke. Hver linje baerer sine EGNE vaerdier - nummer,
    maengde, enhed - og en maengde pr. materiale kan ikke ligge i en
    semikolonstreng uden at opfinde et miniformat, ingen anden kan laese
    eller filtrere paa. Derfor egne raekker.

    Dokumenter kan heller ikke, men af en anden grund: et dokument kan
    haenge paa FLERE operationer og skal kunne haenge paa INGEN. En kolonne
    paa TaskListMain har ingen raekke at bo paa i det tomme tilfaelde, og
    ville duplikere dokumentet i det fulde. Derfor egen liste - og saa er
    operationskoblingen en OperationsKey-kolonne der, samme moenster som
    PackagesKey.

    Idempotent: eksisterende lister og kolonner springes over.

.PARAMETER SiteUrl
    Sitet listerne skal ligge paa.

.EXAMPLE
    .\Provision-TasklistLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        9bc3ab49-b65d-410a-85ad-de819febfddc
    Saet PNP_CLIENT_ID som miljoevariabel, eller giv -ClientId.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

$conn = @{ Url = $SiteUrl; Interactive = $true }
if ($ClientId) { $conn.ClientId = $ClientId }
Connect-PnPOnline @conn

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
    $v = @{}
    if ($Indexed)  { $v.Indexed  = $true }
    if ($Required) { $v.Required = $true }
    if ($v.Count) { Set-PnPField -List $List -Identity $Name -Values $v }
}

# ---------------------------------------------------------------------------
# MD_TasklistMaterial - een raekke pr. materialelinje
# ---------------------------------------------------------------------------
Write-Host "`nMD_TasklistMaterial" -ForegroundColor Cyan
New-MdList -Title 'MD_TasklistMaterial' `
    -Description 'Materialer pr. operation paa arbejdsplanen. Skrives af VH-plan appen.'

# Title er materialenummeret. Saa viser standardvisningen noget brugbart,
# og der er ikke en tom Title-kolonne, nogen skal huske at ignorere.
Set-PnPField -List 'MD_TasklistMaterial' -Identity 'Title' `
    -Values @{ Title = 'MaterialNo'; Required = $true }

# Noeglerne. Indekseret, fordi appen filtrerer paa dem hver gang en plan
# aabnes - uindekseret ville det ramme delegeringsgraensen ved 2000 raekker.
New-MdField 'MD_TasklistMaterial' 'PlanKey' Text -Indexed
New-MdField 'MD_TasklistMaterial' 'ItemKey' Text -Indexed
New-MdField 'MD_TasklistMaterial' 'TaskItemID' Text -Indexed
New-MdField 'MD_TasklistMaterial' 'OperationNo' Text

New-MdField 'MD_TasklistMaterial' 'Quantity' Number -Required

# Udfyldes af materialeopslaget mod SAP, ikke af brugeren. De staar tomme,
# indtil opslaget er paa plads.
New-MdField 'MD_TasklistMaterial' 'MaterialText' Text
New-MdField 'MD_TasklistMaterial' 'Unit' Text

New-MdField 'MD_TasklistMaterial' 'LineId' Number

# ---------------------------------------------------------------------------
# MD_TasklistAttachment - een raekke pr. dokument
# ---------------------------------------------------------------------------
Write-Host "`nMD_TasklistAttachment" -ForegroundColor Cyan
New-MdList -Title 'MD_TasklistAttachment' `
    -Description 'Dokumenter til arbejdsplanen. Skrives af VH-plan appen.'

Set-PnPField -List 'MD_TasklistAttachment' -Identity 'Title' `
    -Values @{ Title = 'FileName'; Required = $true }

New-MdField 'MD_TasklistAttachment' 'PlanKey' Text -Indexed
New-MdField 'MD_TasklistAttachment' 'ItemKey' Text -Indexed

# ";0010;0020;" - samme moenster som PackagesKey paa TaskListMain. Tom (";")
# betyder hele itemet. En kolonne kan ikke laves om til en relation senere
# uden migrering, men her ER det et saet referencer, og det er praecis det
# moenster fungerer til.
New-MdField 'MD_TasklistAttachment' 'OperationsKey' Text

New-MdField 'MD_TasklistAttachment' 'FileUrl' Text
New-MdField 'MD_TasklistAttachment' 'FileSize' Number
New-MdField 'MD_TasklistAttachment' 'LineId' Number

# Saettes af attachments-flowet, ikke af appen. Appen skriver raekken med
# "Pending"; flowet retter til "Uploaded" eller "Failed", naar filen ligger
# i biblioteket.
New-MdField 'MD_TasklistAttachment' 'UploadStatus' Choice `
    -Choices @('Pending', 'Uploaded', 'Failed')

Write-Host "`nFaerdig." -ForegroundColor Green
Write-Host "Naeste skridt: koer sharepoint/inspect/Export-ListSchema.ps1 igen," -ForegroundColor Gray
Write-Host "saa check_datasources.py kan efterproeve de nye kolonner." -ForegroundColor Gray
