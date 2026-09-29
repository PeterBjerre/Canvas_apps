<#
.SYNOPSIS
    Fase 1 af godkendelsesflowet for VH-planer: kolonner paa
    MaintenancePlans, listerne MD_Approver og MD_ApprovalLog, og
    omkostningsgraensen i AppSettings.

.DESCRIPTION
    Se docs/32-godkendelsesflow.md, afsnit 5, 6 og 11. Scriptet er
    idempotent og ADDITIVT: det sletter ingenting, og appen og de
    eksisterende flows virker uaendret bagefter.

    MaintenancePlans
        ApprovalStage       Choice System/Cost/Quality/Done, indekseret
        SubmittedOn         DateTime
        StageRunId          Text   - spaerre mod dobbeltkoersel
        ReturnComment       Note
        MasterDataNotified  Yes/No - spaerre for mailen til Master Data
        RequesterNotified   Yes/No - spaerre for mailen ved Published
        Status              faar valget 'Returned'

    MD_Approver             alle godkendere: system 1-16, vaerk, COST
    MD_ApprovalLog          revisionsspor og hukommelse pr. item
    AppSettings             Option CostApprovalThresholdDkk = 300000

    DE TO SPAERRER PAA EKSISTERENDE PLANER
    --------------------------------------
    MasterDataNotified og RequesterNotified er TOMME paa de planer, der
    findes i dag. Naar PlanPublished-flowet faar sin spaerre, ville alle
    publicerede planer derfor opfylde betingelsen igen, og rekvirenterne
    ville faa mailen en gang til, naeste gang nogen roerer planen.

    Scriptet saetter derfor:
        RequesterNotified  = Ja  paa planer i Published
        MasterDataNotified = Ja  paa planer i Ready for creation in SAP
                                 og Published
    Kun raekker, der ikke allerede staar til Ja, roeres. -SkipBackfill
    springer det over.

    ApprovalStage saettes IKKE paa eksisterende planer. Godkendelsesflowene
    starter kun, naar ApprovalStage = System, saa planer, der staar i
    In Progress i dag, bliver ikke sendt til godkendelse af sig selv.

    MD_APPROVER
    -----------
    Seedes fra sharepoint/seed/MD_Approver.csv. Raekker, der FINDES i
    listen, roeres IKKE - de er listens nu, og koeres scriptet igen, maa
    det ikke saette testinitialerne tilbage oven i dem, der er skiftet.
    -Force overskriver alligevel.

.PARAMETER SiteUrl
    Sitet med MaintenancePlans og AppSettings.

.PARAMETER Environment
    DEV, TEST eller PROD. Bestemmer, hvilken AppSettings-raekke graensen
    skrives til.

.PARAMETER SeedPath
    Standard: ..\seed\MD_Approver.csv

.PARAMETER Force
    Overskriv MD_Approver-raekker, der findes i forvejen.

.PARAMETER SkipBackfill
    Saet ikke spaerrerne paa eksisterende planer.

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville ske, aendr intet.

.EXAMPLE
    .\Provision-VHPlanApproval.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -Environment DEV -WhatIfOnly

.EXAMPLE
    .\Provision-VHPlanApproval.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -Environment DEV

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        9bc3ab49-b65d-410a-85ad-de819febfddc
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [Parameter(Mandatory = $true)][ValidateSet('DEV', 'TEST', 'PROD')][string] $Environment,
    [string] $SeedPath,
    [switch] $Force,
    [switch] $SkipBackfill,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\MD_Approver.csv' }

$PLANS     = 'MaintenancePlans'
$APPROVER  = 'MD_Approver'
$LOG       = 'MD_ApprovalLog'
$SETTINGS  = 'AppSettings'

# Samme strenge som i docs/32 og i flowenes trigger conditions. Et
# stavefejl her giver en trigger, der aldrig rammer - ikke en fejl.
$STAGES    = 'System', 'Cost', 'Quality', 'Done'
$RETURNED  = 'Returned'
$THRESHOLD_OPTION = 'CostApprovalThresholdDkk'
$THRESHOLD_VALUE  = 300000

# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Et client id er ikke en hemmelighed - se
# docs/08-datamapning.md 6B.
$conn = @{ Url = $SiteUrl; Interactive = $true }
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
$conn.ClientId = $ClientId
Connect-PnPOnline @conn

# ---------------------------------------------------------------------------
# Hjaelpere
# ---------------------------------------------------------------------------
function New-List {
    param([string]$Title, [string]$Description)
    if (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
        return
    }
    if ($WhatIfOnly) {
        Write-Host "  ? ville oprette listen '$Title'" -ForegroundColor Yellow
        return
    }
    New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
    Set-PnPList -Identity $Title -Description $Description | Out-Null
    Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
}

function Add-Col {
    param([string]$List, [string]$Name, [string]$Type, [string]$Description,
          [string[]]$Choices, [switch]$Indexed)
    # I et toerloeb findes en ny liste ikke endnu, og Get-PnPField paa en
    # liste, der ikke findes, fejler i stedet for at svare tomt.
    if ($WhatIfOnly -and -not (Get-PnPList -Identity $List -ErrorAction SilentlyContinue)) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    }
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name findes allerede" -ForegroundColor DarkGray
        return
    }
    if ($WhatIfOnly) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    }
    $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
    if ($Choices) { $p.Choices = $Choices }
    Add-PnPField @p -AddToDefaultView | Out-Null
    $v = @{}
    if ($Description) { $v.Description = $Description }
    if ($Indexed)     { $v.Indexed = $true }
    if ($v.Count) { Set-PnPField -List $List -Identity $Name -Values $v }
    Write-Host "    + $Name ($Type)" -ForegroundColor Green
}

function Add-Choice {
    # Tilfoejer et valg til en eksisterende Choice-kolonne uden at roere de
    # valg, der er der i forvejen.
    param([string]$List, [string]$Name, [string]$Choice)
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $Name findes ikke paa $List" -ForegroundColor Yellow
        return
    }
    $current = [string[]]$f.Choices
    if ($current -contains $Choice) {
        Write-Host "    = $Name har allerede '$Choice'" -ForegroundColor DarkGray
        return
    }
    if ($WhatIfOnly) {
        Write-Host "    ? ville tilfoeje '$Choice' til $Name" -ForegroundColor Yellow
        return
    }
    Set-PnPField -List $List -Identity $Name -Values @{ Choices = [string[]]($current + $Choice) }
    Write-Host "    + $Name faar valget '$Choice'" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $PLANS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
Add-Col $PLANS 'ApprovalStage' Choice -Choices $STAGES -Indexed `
    -Description 'Godkendelsestrin under In Progress. Appen saetter System ved Submit; flowene resten. Se docs/32.'
Add-Col $PLANS 'SubmittedOn' DateTime `
    -Description 'Saettes af appen ved Submit. Afgraenser denne indsendelse i MD_ApprovalLog.'
Add-Col $PLANS 'StageRunId' Text `
    -Description 'Koersels-id for det flow, der ejer trinnet. Spaerre mod dobbeltkoersel. Skrives kun af flows.'
Add-Col $PLANS 'ReturnComment' Note `
    -Description 'Kommentarerne ved Send retur, en linje pr. item. Skrives kun af flows.'
Add-Col $PLANS 'MasterDataNotified' Boolean `
    -Description 'Spaerre: mailen til Master Data er sendt. IKKE det samme som InitialEmailSent.'
Add-Col $PLANS 'RequesterNotified' Boolean `
    -Description 'Spaerre: rekvirenten har faaet mailen ved Published.'
Add-Choice $PLANS 'Status' $RETURNED

# ---------------------------------------------------------------------------
Write-Host "`n=== $APPROVER ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
New-List $APPROVER 'Godkendere til VH-plan: systemnummer 1-16, vaerkskode (kvalitet) og COST (omkostning). Se docs/32.'
if (-not $WhatIfOnly) {
    # Unik noegle: der maa ikke kunne staa to raekker for samme system
    # eller vaerk. EnforceUniqueValues kraever, at kolonnen er indekseret.
    Set-PnPField -List $APPROVER -Identity 'Title' `
        -Values @{ Title = 'ApproverKey'; Indexed = $true; EnforceUniqueValues = $true }
    Write-Host "    ~ Title -> ApproverKey (unik, indekseret)" -ForegroundColor Green
}
Add-Col $APPROVER 'Approver1' Text -Description '1. godkender, initialer. Mail = initialer + @ + BioSap-EmailDomain.'
Add-Col $APPROVER 'Approver2' Text -Description '2. godkender, initialer. Bruges ved fravaer.'
Add-Col $APPROVER 'Approver1Absent' Boolean -Description 'Ja = godkendelser gaar til 2. godkender.'
Add-Col $APPROVER 'Notes' Text -Description 'Fri tekst. Bruges ikke af flowene.'

# ---------------------------------------------------------------------------
Write-Host "`n=== $LOG ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
New-List $LOG 'Revisionsspor for godkendelser af VH-planer. Skrives KUN af flows. Se docs/32.'
if (-not $WhatIfOnly) {
    # Flowet skriver en laesbar titel, fx "MP0068 System". Den maa ikke
    # vaere paakraevet, saa en raekke aldrig afvises paa den.
    Set-PnPField -List $LOG -Identity 'Title' -Values @{ Required = $false }
}
Add-Col $LOG 'RequestGuid' Text -Indexed
Add-Col $LOG 'PlanId' Number -Indexed -Description 'ID i MaintenancePlans.'
Add-Col $LOG 'Stage' Text -Indexed -Description 'System, Cost, Quality eller SapCreated.'
Add-Col $LOG 'ItemText' Text -Description 'Itemets korttekst og FL, til visning.'
Add-Col $LOG 'Fingerprint' Text -Indexed -Description 'System: SystemNo|FL|korttekst. Cost: FL|korttekst. Tom for Quality.'
Add-Col $LOG 'Decision' Text -Description 'Approve, Return eller Skipped.'
Add-Col $LOG 'Detail' Text -Description 'Fx systemnummer, beloeb eller grunden til Skipped.'
Add-Col $LOG 'DecidedByEmail' Text
Add-Col $LOG 'DecidedOn' DateTime
Add-Col $LOG 'Comment' Note

# ---------------------------------------------------------------------------
Write-Host "`n=== $APPROVER - seed ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
if (-not (Test-Path $SeedPath)) { throw "Finder ikke $SeedPath" }
$seed = Import-Csv -Path $SeedPath -Encoding UTF8
if ($WhatIfOnly) {
    Write-Host "  ? ville seede $($seed.Count) raekker fra $SeedPath" -ForegroundColor Yellow
} else {
    $index = @{}
    foreach ($it in (Get-PnPListItem -List $APPROVER -PageSize 500)) {
        $index[[string]$it.FieldValues.Title] = $it
    }
    $added = 0; $kept = 0; $updated = 0
    foreach ($r in $seed) {
        $values = @{
            Title           = $r.ApproverKey.Trim()
            Approver1       = $r.Approver1.Trim().ToUpper()
            Approver2       = $r.Approver2.Trim().ToUpper()
            Approver1Absent = [bool]::Parse($r.Approver1Absent)
            Notes           = $r.Notes
        }
        if ($index.ContainsKey($values.Title)) {
            if ($Force) {
                Set-PnPListItem -List $APPROVER -Identity $index[$values.Title].Id -Values $values | Out-Null
                $updated++
            } else {
                $kept++
            }
        } else {
            Add-PnPListItem -List $APPROVER -Values $values | Out-Null
            $added++
        }
    }
    $msg = "  {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
    Write-Host $msg -ForegroundColor Green
    if ($kept -and -not $Force) {
        Write-Host "  Raekker, der fandtes i forvejen, er IKKE rettet. Brug -Force for at" -ForegroundColor DarkGray
        Write-Host "  saette dem tilbage til csv'en." -ForegroundColor DarkGray
    }
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $SETTINGS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
# Option er en Choice-kolonne, saa vaerdien skal findes som valg, foer
# raekken kan skrives.
Add-Choice $SETTINGS 'Option' $THRESHOLD_OPTION
if ($WhatIfOnly) {
    Write-Host "  ? ville saette $THRESHOLD_OPTION = $THRESHOLD_VALUE for $Environment" -ForegroundColor Yellow
} else {
    $row = Get-PnPListItem -List $SETTINGS -PageSize 500 | Where-Object {
        $_.FieldValues.Option -eq $THRESHOLD_OPTION -and $_.FieldValues.Environment -eq $Environment
    } | Select-Object -First 1
    if ($row) {
        # Graensen er en forretningsbeslutning. Staar der en anden vaerdi,
        # har nogen sat den med vilje - den overskrives ikke.
        Write-Host "  = $THRESHOLD_OPTION findes for $Environment ($($row.FieldValues.Value)) - roeres ikke" -ForegroundColor DarkGray
    } else {
        Add-PnPListItem -List $SETTINGS -Values @{
            Option      = $THRESHOLD_OPTION
            Environment = $Environment
            Value       = $THRESHOLD_VALUE
            Notes       = 'Omkostning pr. udfoerelse pr. item, over hvilken VH-planen kraever omkostningsgodkendelse. Se docs/32.'
        } | Out-Null
        Write-Host "  + $THRESHOLD_OPTION = $THRESHOLD_VALUE for $Environment" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
if (-not $SkipBackfill) {
    Write-Host "`n=== $PLANS - spaerrer paa eksisterende planer ===" -ForegroundColor Cyan
    if ($WhatIfOnly -and -not (Get-PnPField -List $PLANS -Identity 'RequesterNotified' -ErrorAction SilentlyContinue)) {
        Write-Host "  ? kolonnerne findes ikke endnu - optaelling springes over i toerloebet" -ForegroundColor Yellow
    } else {
        $setReq = 0; $setMd = 0
        foreach ($it in (Get-PnPListItem -List $PLANS -PageSize 500)) {
            $status = [string]$it.FieldValues.Status
            $v = @{}
            if ($status -eq 'Published' -and $it.FieldValues.RequesterNotified -ne $true) {
                $v.RequesterNotified = $true
            }
            if (($status -eq 'Published' -or $status -eq 'Ready for creation in SAP') -and
                $it.FieldValues.MasterDataNotified -ne $true) {
                $v.MasterDataNotified = $true
            }
            if (-not $v.Count) { continue }
            if ($v.ContainsKey('RequesterNotified'))  { $setReq++ }
            if ($v.ContainsKey('MasterDataNotified')) { $setMd++ }
            if ($WhatIfOnly) { continue }
            # SystemUpdate: Modified og Modified By bliver staaende, og der
            # oprettes ingen ny version. En almindelig opdatering ville
            # ellers se ud, som om nogen havde rettet 40 planer i dag.
            Set-PnPListItem -List $PLANS -Identity $it.Id -Values $v -UpdateType SystemUpdate | Out-Null
        }
        $verb = if ($WhatIfOnly) { 'ville saette' } else { 'sat' }
        Write-Host "  $verb RequesterNotified paa $setReq og MasterDataNotified paa $setMd planer" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Write-Host "Det var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
    return
}
Write-Host "Naeste skridt, som scriptet IKKE goer:" -ForegroundColor Yellow
Write-Host "  1. Rettigheder paa ${LOG}: bryd nedarvningen og giv brugerne Read."
Write-Host "     Kun flowenes servicekonto skal kunne skrive. Se docs/32, afsnit 6."
Write-Host "  2. Rettigheder paa ${APPROVER}: kun dem, der vedligeholder godkendere,"
Write-Host "     maa kunne rette. Flowenes konto skal kunne laese."
Write-Host "  3. Miljoevariabler i solution BIO SAP (docs/32, afsnit 6, Parametre):"
Write-Host "       BioSap-EmailDomain        orsted.com"
Write-Host "       BioSap-MasterDataEmail    sapvedligehold@orsted.com"
Write-Host "       BioSap-List-Approver      $APPROVER"
Write-Host "       BioSap-List-ApprovalLog   $LOG"
Write-Host "       BioSap-PowerBI-WorkspaceId, BioSap-PowerBI-DatasetId"
Write-Host "  4. Koer sharepoint/inspect/Export-ListSchema.ps1, saa schema.md kender"
Write-Host "     de nye kolonner og lister."
Write-Host "  5. Nye kolonner ses foerst i appen, naar MaintenancePlans er opdateret"
Write-Host "     som datakilde i Studio."
