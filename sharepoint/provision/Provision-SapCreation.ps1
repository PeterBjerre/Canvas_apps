<#
.SYNOPSIS
    Det, oprettelsen i SAP har brug for i SharePoint: biblioteket
    SAP-oprettelse med sine mapper og fem kolonner til numrene fra SAP.

.DESCRIPTION
    Se docs/34-sap-oprettelse.md og docs/35-flow-sap-ordre.md. Scriptet er
    idempotent og ADDITIVT: det sletter ingenting, og appen virker uaendret
    bagefter.

    BIBLIOTEKET  SAP-oprettelse
        Til oprettelse\          flowet BioSap-VhPlan-SapOrder skriver een
                                 JSON-fil pr. plan, der er klar
        Kvitteringer\            VH-plan Opretter skriver kvitteringen
        Kvitteringer\Behandlet\  flowet BioSap-VhPlan-SapReceipt flytter
        Kvitteringer\Afvist\     kvitteringen hertil, naar den er laest
        Oprettet\                opretteren flytter ordren hertil

    Biblioteket synkroniseres til Master Datas pc'er med OneDrive
    ("Synkroniser" eller "Tilfoej genvej til Mine filer"). Opretteren
    finder det selv.

    MaintenancePlans
        SapOrderGuid    Text, indekseret - ordren, flowet sidst skrev. En
                        kvittering skal baere den samme, ellers afvises den.
                        Toem den, og flowet skriver en ny ordre.
        SapOrderFile    Text - ordrefilens navn, til fejlsoegning
        SapCreatedOn    DateTime - hvornaar kvitteringen blev laest
        SapCreatedBy    Text - initialerne paa den, der oprettede planen

    MaintenanceItems
        SapItemNo       Text, indekseret - vedligeholdspositionens nummer.
                        Arbejdsplanens gruppe og taeller skrives i de
                        kolonner, der findes: TaskListGroup og
                        TaskListGroupCounter.

    RETTIGHEDER
    -----------
    Den, der kan laegge en fil i Kvitteringer, kan i princippet faa en plan
    markeret som oprettet. Flowet tjekker SapOrderGuid, status og SAP-system,
    men biblioteket boer kun kunne skrives af Master Data og flowets
    servicekonto. Scriptet saetter ikke rettighederne - det er en
    beslutning, ikke en opsaetning. Se docs/35, "Rettigheder".

.PARAMETER SiteUrl
    Sitet med MaintenancePlans og MaintenanceItems.

.PARAMETER LibraryName
    Standard: SAP-oprettelse. Opretteren leder efter en synkroniseret mappe,
    der hedder det samme (VhpConfig.FOLDER_LIBRARY).

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville ske, aendr intet.

.EXAMPLE
    .\Provision-SapCreation.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -WhatIfOnly

.EXAMPLE
    .\Provision-SapCreation.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell 2.x i PowerShell 7. ClientId: se _Common.psm1.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $LibraryName = 'SAP-oprettelse',
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

function Add-Col {
    param([string]$List, [string]$Name, [string]$Type, [string]$Description,
          [switch]$Indexed)
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name findes allerede" -ForegroundColor DarkGray
        return
    }
    if ($WhatIfOnly) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    }
    Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type $Type -AddToDefaultView | Out-Null
    $v = @{}
    if ($Description) { $v.Description = $Description }
    if ($Indexed)     { $v.Indexed = $true }
    if ($v.Count) { Set-PnPField -List $List -Identity $Name -Values $v }
    Write-Host "    + $Name ($Type)" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== Biblioteket $LibraryName ===" -ForegroundColor Cyan
$lib = Get-PnPList -Identity $LibraryName -ErrorAction SilentlyContinue
if (-not $lib) {
    if ($WhatIfOnly) {
        Write-Host "  ? ville oprette dokumentbiblioteket $LibraryName" -ForegroundColor Yellow
    } else {
        $lib = New-PnPList -Title $LibraryName -Url $LibraryName -Template DocumentLibrary -OnQuickLaunch
        Set-PnPList -Identity $LibraryName -Description 'Ordrer til VH-plan Opretter og kvitteringer tilbage. Se docs/34-sap-oprettelse.md.' | Out-Null
        Write-Host "  + $LibraryName oprettet" -ForegroundColor Green
    }
} else {
    Write-Host "  = $LibraryName findes allerede" -ForegroundColor DarkGray
}

if ($lib) {
    $rootFolder = Get-PnPProperty -ClientObject $lib -Property RootFolder
    $libUrl = $rootFolder.Name
    foreach ($folder in @('Til oprettelse', 'Kvitteringer', 'Kvitteringer/Behandlet', 'Kvitteringer/Afvist', 'Oprettet')) {
        if ($WhatIfOnly) {
            Write-Host "    ? mappen $folder" -ForegroundColor Yellow
        } else {
            Resolve-PnPFolder -SiteRelativePath "$libUrl/$folder" | Out-Null
            Write-Host "    = $folder" -ForegroundColor DarkGray
        }
    }
}

# ---------------------------------------------------------------------------
Write-Host "`n=== MaintenancePlans ===" -ForegroundColor Cyan
Add-Col 'MaintenancePlans' 'SapOrderGuid' Text -Indexed `
    -Description 'Ordren til SAP-oprettelsen, flowet sidst skrev. Kvitteringen skal baere den samme. Toem den for at faa en ny ordre.'
Add-Col 'MaintenancePlans' 'SapOrderFile' Text `
    -Description 'Navnet paa ordrefilen i SAP-oprettelse/Til oprettelse.'
Add-Col 'MaintenancePlans' 'SapCreatedOn' DateTime `
    -Description 'Hvornaar kvitteringen fra VH-plan Opretter blev laest.'
Add-Col 'MaintenancePlans' 'SapCreatedBy' Text `
    -Description 'Initialerne paa den, der oprettede planen i SAP.'

Write-Host "`n=== MaintenanceItems ===" -ForegroundColor Cyan
Add-Col 'MaintenanceItems' 'SapItemNo' Text -Indexed `
    -Description 'Vedligeholdspositionens nummer i SAP (IP04). Skrives af kvitteringsflowet.'

Write-Host ""
Write-Host "Faerdig. Synkroniser biblioteket $LibraryName med OneDrive paa Master Datas pc'er," -ForegroundColor Cyan
Write-Host "og saet rettighederne, saa kun Master Data og flowets servicekonto kan skrive." -ForegroundColor Cyan
