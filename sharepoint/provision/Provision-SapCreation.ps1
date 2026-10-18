<#
.SYNOPSIS
    Det, oprettelsen i SAP har brug for i SharePoint: biblioteket
    SAP-oprettelse med sine mapper og kolonnerne til resultaterne fra SAP -
    for VH-planer og for FL-anmodninger.

.DESCRIPTION
    Se docs/34-sap-oprettelse.md, docs/35-flow-sap-ordre.md og
    docs/36-fl-sap-oprettelse.md. Scriptet er idempotent og ADDITIVT: det
    sletter ingenting, og appen virker uaendret bagefter.

    BIBLIOTEKET  SAP-oprettelse
        Til oprettelse\          flowet BioSap-VhPlan-SapOrder skriver een
                                 JSON-fil pr. plan, der er klar
        Kvitteringer\            VH-plan Opretter skriver kvitteringen
        Kvitteringer\Behandlet\  flowet BioSap-VhPlan-SapReceipt flytter
        Kvitteringer\Afvist\     kvitteringen hertil, naar den er laest
        Kvitteringer\FL\         FL-kvitteringerne - flowet
          Behandlet\, Afvist\    BioSap-FL-SapReceipt laeser dem
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
        SapWarnings     Note, ren tekst - kvitteringens advarsler, een pr.
                        linje: det, opretteren ikke kunne oprette, fx
                        materialer, der skal tilfoejes i IA06. Vises i
                        mailen "Created in SAP" (R2-018).

    MaintenanceItems
        SapItemNo       Text, indekseret - vedligeholdspositionens nummer.
                        Arbejdsplanens gruppe og taeller skrives i de
                        kolonner, der findes: TaskListGroup og
                        TaskListGroupCounter.

    FunctionalLocationRequests (kun hvis listen findes)
        SapOrderGuid, SapOrderFile, SapCreatedOn, SapCreatedBy - som paa
                        MaintenancePlans

    FunctionalLocationItems (kun hvis listen findes)
        SapResult       Text - Created (IL01) eller Updated (IL02)
        SapMessage      Text - SAP's statuslinje efter Gem

    RETTIGHEDER
    -----------
    Den, der kan laegge en fil i Kvitteringer, kan i princippet faa en plan
    markeret som oprettet. Flowet tjekker SapOrderGuid, status og SAP-system,
    men biblioteket boer kun kunne skrives af Master Data og flowets
    servicekonto. Rettighederne saettes af Provision-AdminLists.ps1
    (R2-024): Members Read, Owners og flowets konto Full Control, og
    -MaintainerGroup (Master Data) Contribute. Se docs/35, "Rettigheder".

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
Set-MdWhatIf $WhatIfOnly

# Kolonnerne oprettes med New-MdField fra _Common.psm1 (toerloeb: Set-MdWhatIf).

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
    foreach ($folder in @('Til oprettelse', 'Kvitteringer', 'Kvitteringer/Behandlet', 'Kvitteringer/Afvist',
                          'Kvitteringer/FL', 'Kvitteringer/FL/Behandlet', 'Kvitteringer/FL/Afvist', 'Oprettet')) {
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
New-MdField 'MaintenancePlans' 'SapOrderGuid' Text -Indexed `
    -Description 'Ordren til SAP-oprettelsen, flowet sidst skrev. Kvitteringen skal baere den samme. Toem den for at faa en ny ordre.'
New-MdField 'MaintenancePlans' 'SapOrderFile' Text `
    -Description 'Navnet paa ordrefilen i SAP-oprettelse/Til oprettelse.'
New-MdField 'MaintenancePlans' 'SapCreatedOn' DateTime `
    -Description 'Hvornaar kvitteringen fra VH-plan Opretter blev laest.'
New-MdField 'MaintenancePlans' 'SapCreatedBy' Text `
    -Description 'Initialerne paa den, der oprettede planen i SAP.'
# Note, ikke Text: en plan kan have mange advarsler, og de er laengere end
# 255 tegn tilsammen. Ren tekst - flowet skriver een advarsel pr. linje.
New-MdNoteField 'MaintenancePlans' 'SapWarnings' 6 `
    -Description 'Kvitteringens advarsler, een pr. linje - fx materialer, der skal tilfoejes i IA06. Skrives af kvitteringsflowet.'

Write-Host "`n=== MaintenanceItems ===" -ForegroundColor Cyan
New-MdField 'MaintenanceItems' 'SapItemNo' Text -Indexed `
    -Description 'Vedligeholdspositionens nummer i SAP (IP04). Skrives af kvitteringsflowet.'

# ---------------------------------------------------------------------------
# FL-anmodningerne. Listerne oprettes af Provision-FunctionalLocationLists.ps1;
# findes de ikke endnu, springes de over - koer det script foerst.
foreach ($pair in @(@('FunctionalLocationRequests', 'FL-anmodningerne'), @('FunctionalLocationItems', 'FL-raekkerne'))) {
    if (-not (Get-PnPList -Identity $pair[0] -ErrorAction SilentlyContinue)) {
        Write-Host "`n=== $($pair[0]) findes ikke - koer Provision-FunctionalLocationLists.ps1 foerst ===" -ForegroundColor Yellow
    }
}
if (Get-PnPList -Identity 'FunctionalLocationRequests' -ErrorAction SilentlyContinue) {
    Write-Host "`n=== FunctionalLocationRequests ===" -ForegroundColor Cyan
    New-MdField 'FunctionalLocationRequests' 'SapOrderGuid' Text -Indexed `
        -Description 'Ordren til SAP-oprettelsen, flowet sidst skrev. Kvitteringen skal baere den samme.'
    New-MdField 'FunctionalLocationRequests' 'SapOrderFile' Text `
        -Description 'Navnet paa ordrefilen i SAP-oprettelse/Til oprettelse.'
    New-MdField 'FunctionalLocationRequests' 'SapCreatedOn' DateTime `
        -Description 'Hvornaar kvitteringen fra SAP Opretter blev laest.'
    New-MdField 'FunctionalLocationRequests' 'SapCreatedBy' Text `
        -Description 'Initialerne paa den, der oprettede FL i SAP.'
}
if (Get-PnPList -Identity 'FunctionalLocationItems' -ErrorAction SilentlyContinue) {
    Write-Host "`n=== FunctionalLocationItems ===" -ForegroundColor Cyan
    New-MdField 'FunctionalLocationItems' 'SapResult' Text `
        -Description 'Created (oprettet med IL01) eller Updated (fandtes, aendret med IL02).'
    New-MdField 'FunctionalLocationItems' 'SapMessage' Text `
        -Description 'Statuslinjen i SAP efter Gem.'
}

Write-Host ""
Write-Host "Faerdig. Synkroniser biblioteket $LibraryName med OneDrive paa Master Datas pc'er," -ForegroundColor Cyan
Write-Host "Rettighederne paa biblioteket saettes af Provision-AdminLists.ps1 (Master Data og flowets servicekonto skriver)." -ForegroundColor Cyan
