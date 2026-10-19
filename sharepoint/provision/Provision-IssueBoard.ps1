<#
.SYNOPSIS
    Issue Board (issue #114, trin 1 og 2, issue #193): de tre lister, deres
    rettigheder og konfigurationen af Application/Section.

.DESCRIPTION
    Et midlertidigt sags- og feedbacksystem til udviklings- og testfasen.
    Scriptet er idempotent og ADDITIVT: det sletter ingen lister og ingen
    raekker, og en liste, der findes, beholder sine data. Eneste undtagelse
    er -RemoveSharedIssues (se nedenfor).

    IB_Tickets          sagerne. Siden issue #193 opretter appen sagen selv
                        med Patch (brugerens egen forbindelse), og ALLE
                        Members kan laese alle sager - ingen anonymisering.
                        Listen: Members Contribute, "Read access: All items"
                        og "Create and Edit access: Create items and edit
                        items that were created by the user". En bruger kan
                        derfor oprette sager og kun rette (og slette) sine
                        egne - det haandhaever SharePoint. Admins faar
                        Design paa listen, saa de kan rette alle sager
                        (WriteSecurity omgaas kun med Manage Lists).
                        Flowet BioSap-IssueBoard-OnCreated saetter nummeret
                        (TicketNo) og rapportoeren ud fra Created By og
                        sender mail til admins og rapportoeren.
                        Vedhaeftninger ligger som SharePoint-vedhaeftninger
                        PAA raekken og arver listens rettigheder: alle kan
                        laese dem. Siden issue #300 laegger appen dem selv
                        paa med Patch (brugerens egen forbindelse) - det
                        kraever, at rapportoeren er raekkens Created By.
    IB_TicketComments   kommentarer og haendelser, een raekke pr. haendelse
                        (aldrig en samlet tekst). PRIVAT: kun ejerne og
                        flowets konto paa listen. Hver raekke faar sine egne
                        rettigheder af flowet BioSap-IssueBoard-Submit:
                        sagens rapportoer Read (ikke ved Internal) og admins
                        Contribute. Kun rapportoeren og admins kan derfor
                        laese en sags kommentarer - ogsaa en admins.
    IB_AppSections      konfigurationen: Application og Section, raekkefoelge,
                        aktiv, skaerm, farve og ikon. Alle kan LAESE; kun
                        ejerne kan rette. Seedes fra
                        sharepoint/seed/IB_AppSections.csv.

    IB_SharedIssues (den anonyme kopi foer #193) oprettes ikke laengere.
    Den findes stadig paa sites, hvor scriptet er koert foer; den bruges
    ikke af appen eller flowene. -RemoveSharedIssues sletter den.

    GAMLE SAGER
    -----------
    Sager oprettet foer #193 har unikke rettigheder paa raekken
    (rapportoeren Read, admins Contribute). Scriptet nulstiller dem, saa
    de arver listen og ses af alle (besluttet i #193). Kun raekker med
    unikke rettigheder roeres.

    De sager blev oprettet af FLOWET, saa Created By er flowets konto, og
    "Edit own items" lader ikke rapportoeren rette dem - heller ikke
    vedhaefte filer (issue #300: "En bruger maa gerne redigere sit eget
    issue"). Scriptet saetter Created By til rapportoeren (ReporterEmail)
    paa de sager, hvor de to ikke er den samme. Modified roeres ikke.

    ADMINS
    ------
    Admins er de samme som i resten af BIO SAP: listen UserAndGroups,
    Title = Admin, Member = e-mail (tools/permissions.py). Flowene slaar
    dem op ved hver sag. Scriptet giver dem Design paa IB_Tickets. Bliver
    en admin tilfoejet, koeres scriptet igen; bliver en fjernet, tages
    hans Design af listen i haanden (scriptet fjerner ingen personer).

.PARAMETER SiteUrl
    Sitet med BIO SAP-listerne.

.PARAMETER FlowAccount
    E-mail paa den konto, flowets SharePoint-forbindelse
    (orsted_BioSapSharePointConn) koerer som. Den faar Full Control paa
    de tre lister, fordi den skal kunne bryde nedarvningen og give
    rettigheder paa en raekke. Uden parameteren roeres kontoen ikke - saa
    skal den have Full Control paa sitet i forvejen.

.PARAMETER SeedPath
    Standard: ..\seed\IB_AppSections.csv

.PARAMETER Force
    Overskriv IB_AppSections-raekker, der findes i forvejen.

.PARAMETER SkipPermissions
    Opret lister og kolonner, men roer ikke rettighederne.

.PARAMETER RemoveSharedIssues
    Slet listen IB_SharedIssues (den anonyme kopi foer #193) med alt dens
    indhold. Kun med denne switch - aldrig ved et uheld. Den kan ikke
    fortrydes (listen ligger dog i papirkurven paa sitet).

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville ske, aendr intet.

.EXAMPLE
    .\Provision-IssueBoard.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -FlowAccount "svc-konto@<domaene>" -WhatIfOnly

.EXAMPLE
    .\Provision-IssueBoard.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -FlowAccount "svc-konto@<domaene>"

.EXAMPLE
    .\Provision-IssueBoard.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -FlowAccount "svc-konto@<domaene>" -RemoveSharedIssues

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        se MdDefaultClientId i _Common.psm1
    Navnene staar ogsaa i "Issue Board/build/ib_config.py" og i flowet.
    tests/test_issue_board.py holder de tre i trit.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $FlowAccount,
    [string] $SeedPath,
    [switch] $Force,
    [switch] $SkipPermissions,
    [switch] $RemoveSharedIssues,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

if (-not $SeedPath) { $SeedPath = Join-Path $PSScriptRoot '..\seed\IB_AppSections.csv' }

$TICKETS  = 'IB_Tickets'
$COMMENTS = 'IB_TicketComments'
$SECTIONS = 'IB_AppSections'
# Den anonyme kopi foer #193 - kun til -RemoveSharedIssues.
$SHARED   = 'IB_SharedIssues'
$ADMINS   = 'UserAndGroups'

# Samme vaerdier som "Issue Board/build/ib_config.py". Et stavefejl her
# giver en sag, flowet ikke kan skrive - ikke en fejl i scriptet.
$STATUS     = 'New', 'Reopened', 'Triaged', 'In progress', 'Ready for retest', 'Closed'
$SEVERITY   = 'Blocker', 'Major', 'Minor', 'Cosmetic'
$PRIORITY   = 'Urgent', 'High', 'Normal', 'Low'
$EVENTTYPE  = 'Comment', 'StatusChange', 'Assignment', 'PriorityChange', 'Attachment', 'Reopened', 'Closed', 'Archived', 'System'
$AUTHORROLE = 'Reporter', 'Admin', 'System'
$VISIBILITY = 'Reporter', 'Internal'

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

# ---------------------------------------------------------------------------
# Hjaelpere - samme moenster som Provision-VHPlanApproval.ps1
# ---------------------------------------------------------------------------
# New-MdList, New-MdField og New-MdNoteField staar i _Common.psm1 og
# respekterer toerloebet (Set-MdWhatIf, R2-060). Rettighedshjaelperne
# (Get-MdRoleName, Remove-MdGroupFromList, Set-MdReadOnlyList) ligeledes -
# de bruges ogsaa af Provision-AdminLists.ps1 (R2-024).

function Set-TitleOptional {
    # Flowet skriver Title. Den maa ikke vaere paakraevet, saa en raekke
    # aldrig afvises paa den alene.
    param([string]$List)
    if ($WhatIfOnly) { return }
    Set-PnPField -List $List -Identity 'Title' -Values @{ Required = $false }
}

function Set-PrivateList {
    # Kun ejerne og flowets konto. Raekkerne faar deres egne rettigheder
    # af flowet.
    param([string]$List)
    if ($WhatIfOnly) {
        Write-Host "    ? ville lukke $List for Members og Visitors" -ForegroundColor Yellow
        return
    }
    if (-not (Test-MdUniquePermissions $List)) {
        Set-PnPList -Identity $List -BreakRoleInheritance -CopyRoleAssignments | Out-Null
        Write-Host "    ~ nedarvning brudt (kopieret)" -ForegroundColor Green
    }
    Remove-MdGroupFromList $List (Get-PnPGroup -AssociatedMemberGroup)
    Remove-MdGroupFromList $List (Get-PnPGroup -AssociatedVisitorGroup)
    $owners = Get-PnPGroup -AssociatedOwnerGroup
    Set-PnPListPermission -Identity $List -Group $owners -AddRole $ROLE_FULL | Out-Null
    if ($FlowAccount) {
        Set-PnPListPermission -Identity $List -User $FlowAccount -AddRole $ROLE_FULL | Out-Null
        Write-Host "    + $FlowAccount har Full Control" -ForegroundColor Green
    }
}

function Get-AdminEmails {
    # Samme admins som appen og flowene: UserAndGroups, Title = Admin.
    $items = Get-PnPListItem -List $ADMINS -PageSize 500 -Fields 'Title', 'Member'
    return @($items | Where-Object { $_.FieldValues.Title -eq 'Admin' -and $_.FieldValues.Member } |
        ForEach-Object { ([string]$_.FieldValues.Member).Trim().ToLowerInvariant() } | Sort-Object -Unique)
}

function Set-OpenTicketList {
    # Issue #193: alle Members laeser alle sager og opretter selv; hver
    # retter kun sine egne. Admins (Design) retter alle. Visitors har intet.
    param([string]$List)
    if ($WhatIfOnly) {
        Write-Host "    ? ville give Members Contribute, Read all / Edit own og admins Design paa $List" -ForegroundColor Yellow
        return
    }
    if (-not (Test-MdUniquePermissions $List)) {
        Set-PnPList -Identity $List -BreakRoleInheritance -CopyRoleAssignments | Out-Null
        Write-Host "    ~ nedarvning brudt (kopieret)" -ForegroundColor Green
    }
    $members = Get-PnPGroup -AssociatedMemberGroup
    Remove-MdGroupFromList $List $members
    Set-PnPListPermission -Identity $List -Group $members -AddRole $ROLE_CONTRIBUTE | Out-Null
    Write-Host "    ~ $($members.Title) har Contribute" -ForegroundColor Green
    Remove-MdGroupFromList $List (Get-PnPGroup -AssociatedVisitorGroup)
    $owners = Get-PnPGroup -AssociatedOwnerGroup
    Set-PnPListPermission -Identity $List -Group $owners -AddRole $ROLE_FULL | Out-Null
    if ($FlowAccount) {
        Set-PnPListPermission -Identity $List -User $FlowAccount -AddRole $ROLE_FULL | Out-Null
        Write-Host "    + $FlowAccount har Full Control" -ForegroundColor Green
    }
    # 1 = Read all items, 2 = Create items and edit items that were created by the user.
    Set-PnPList -Identity $List -ReadSecurity 1 -WriteSecurity 2 | Out-Null
    Write-Host "    ~ Read access: All items / Create and Edit access: Own items" -ForegroundColor Green
    foreach ($a in (Get-AdminEmails)) {
        try {
            Set-PnPListPermission -Identity $List -User $a -AddRole $ROLE_DESIGN | Out-Null
            Write-Host "    + admin $a har Design" -ForegroundColor Green
        }
        catch {
            Write-Host "    ! admin $a kunne ikke faa Design: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

function Reset-TicketItemPermissions {
    # Sager fra foer #193 har unikke rettigheder paa raekken. De nulstilles,
    # saa raekken arver listen. Kun raekker med unikke rettigheder roeres.
    param([string]$List)
    $items = Get-PnPListItem -List $List -PageSize 500 -Fields 'ID'
    $n = 0
    foreach ($it in $items) {
        $unique = Get-PnPProperty -ClientObject $it -Property HasUniqueRoleAssignments
        if (-not $unique) { continue }
        if ($WhatIfOnly) {
            Write-Host "    ? ville nulstille rettighederne paa sag $($it.Id)" -ForegroundColor Yellow
        } else {
            $it.ResetRoleInheritance()
            Invoke-PnPQuery
        }
        $n++
    }
    Write-Host "    ~ $n gamle sag(er) arver nu listens rettigheder" -ForegroundColor Green
}

function Set-TicketAuthors {
    # Issue #300: rapportoeren retter selv sin sag (og dens vedhaeftninger)
    # med Patch, og listen tillader kun "edit own items". Sager, flowet
    # oprettede foer #193, har flowets konto som Created By - her saettes
    # Created By til rapportoeren. Kun sager, hvor de to er forskellige.
    param([string]$List)
    $items = Get-PnPListItem -List $List -PageSize 500 -Fields 'ID', 'Author', 'ReporterEmail'
    $n = 0
    foreach ($it in $items) {
        $reporter = ([string]$it.FieldValues.ReporterEmail).Trim().ToLowerInvariant()
        if (-not $reporter) { continue }
        $author = $it.FieldValues.Author
        $authorEmail = if ($author) { ([string]$author.Email).Trim().ToLowerInvariant() } else { '' }
        if ($authorEmail -eq $reporter) { continue }
        if ($WhatIfOnly) {
            Write-Host "    ? ville saette Created By = $reporter paa sag $($it.Id)" -ForegroundColor Yellow
        } else {
            try {
                Set-PnPListItem -List $List -Identity $it.Id -Values @{ Author = $reporter } `
                    -UpdateType UpdateOverwriteVersion | Out-Null
            }
            catch {
                Write-Host "    ! sag $($it.Id): $($_.Exception.Message)" -ForegroundColor Red
                continue
            }
        }
        $n++
    }
    Write-Host "    ~ $n sag(er) har nu rapportoeren som Created By" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $TICKETS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
New-MdList $TICKETS 'Issue Board: sagerne. Alle kan laese; hver opretter og retter sine egne, admins alle. Se issue #114 og #193.'
Set-TitleOptional $TICKETS
New-MdField 'IB_Tickets' 'TicketNo' Text -Indexed -Description 'Sagens nummer, fx ISS-000142. Saettes af flowet BioSap-IssueBoard-OnCreated ud fra ID.'
New-MdNoteField 'IB_Tickets' 'Description' -Description 'What happened?'
New-MdNoteField 'IB_Tickets' 'ReproSteps' -Description 'Steps to reproduce.'
New-MdNoteField 'IB_Tickets' 'ExpectedResult'
New-MdNoteField 'IB_Tickets' 'ActualResult'
New-MdField 'IB_Tickets' 'Application' Text -Indexed -Description 'IB_AppSections.Application.'
New-MdField 'IB_Tickets' 'Section' Text -Indexed -Description 'IB_AppSections.Section.'
New-MdField 'IB_Tickets' 'OtherContext' Text -Description 'Beskrivelsen, naar Application eller Section er Other.'
New-MdField 'IB_Tickets' 'RelatedRequestNo' Text -Description 'Anmodningsnummeret, sagen handler om (valgfrit).'
New-MdField 'IB_Tickets' 'LayoutContext' Text -Description 'Hvor sagen blev meldt fra: skaerm, layout og stoerrelse.'
New-MdField 'IB_Tickets' 'ClientContext' Text -Description 'Styresystem og browser/Power Apps-afspiller.'
New-MdField 'IB_Tickets' 'Severity' Choice -Choices $SEVERITY
New-MdField 'IB_Tickets' 'Priority' Choice -Choices $PRIORITY
New-MdField 'IB_Tickets' 'Status' Choice -Choices $STATUS -Indexed
New-MdField 'IB_Tickets' 'ReporterEmail' Text -Indexed -Description 'Rapportoeren med smaa bogstaver. Flowet BioSap-IssueBoard-OnCreated saetter den ud fra Created By.'
New-MdField 'IB_Tickets' 'ReporterName' Text
New-MdField 'IB_Tickets' 'AssignedToEmail' Text -Indexed -Description 'Admin, sagen er tildelt (trin 2).'
New-MdField 'IB_Tickets' 'AssignedToName' Text
New-MdField 'IB_Tickets' 'LastActivityOn' DateTime -Indexed -Description 'Seneste aendring eller kommentar.'
New-MdField 'IB_Tickets' 'ResolvedOn' DateTime
New-MdField 'IB_Tickets' 'ClosedOn' DateTime
New-MdField 'IB_Tickets' 'IsArchived' Boolean -Indexed -Description 'Arkiveret: ude af de aktive visninger, men ikke slettet (trin 2).'
New-MdNoteField 'IB_Tickets' 'Resolution'
New-MdField 'IB_Tickets' 'SharedItemId' Number -Description 'Udgaaet (#193): ID i den tidligere anonyme kopi IB_SharedIssues. Skrives ikke laengere.'
# Trin 2: vedhaeftningerne ligger paa raekken. Det er SharePoints standard,
# men slaas til her, saa ingen kan have slaaet det fra.
if (-not $WhatIfOnly -and (Get-PnPList -Identity $TICKETS -ErrorAction SilentlyContinue)) {
    Set-PnPList -Identity $TICKETS -EnableAttachments $true | Out-Null
    Write-Host "    ~ vedhaeftninger slaaet til" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $COMMENTS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
New-MdList $COMMENTS 'Issue Board: kommentarer og haendelser, een raekke pr. haendelse. Privat - kun sagens rapportoer og admins kan laese en raekke. Skrives KUN af flowet.'
Set-TitleOptional $COMMENTS
New-MdField 'IB_TicketComments' 'TicketId' Number -Indexed -Description 'ID i IB_Tickets.'
New-MdField 'IB_TicketComments' 'TicketNo' Text -Indexed
New-MdField 'IB_TicketComments' 'AuthorEmail' Text
New-MdField 'IB_TicketComments' 'AuthorName' Text
New-MdField 'IB_TicketComments' 'AuthorRole' Choice -Choices $AUTHORROLE
New-MdField 'IB_TicketComments' 'EventType' Choice -Choices $EVENTTYPE
New-MdField 'IB_TicketComments' 'Visibility' Choice -Choices $VISIBILITY -Description 'Reporter: rapportoeren og admins. Internal: kun admins.'
New-MdNoteField 'IB_TicketComments' 'Content'
New-MdField 'IB_TicketComments' 'PreviousStatus' Text
New-MdField 'IB_TicketComments' 'NewStatus' Text
New-MdField 'IB_TicketComments' 'EventOn' DateTime -Indexed
# Trin 2: en Attachment-haendelse fortaeller, hvilken fil, hvor stor, og om
# den kom med indmeldingen eller senere. Selve filen ligger paa IB_Tickets.
New-MdField 'IB_TicketComments' 'FileName' Text -Description 'Filnavnet ved EventType = Attachment.'
New-MdField 'IB_TicketComments' 'FileSizeKb' Number -Description 'Filens stoerrelse i KB (afrundet op).'
New-MdField 'IB_TicketComments' 'AtSubmission' Boolean -Description 'Ja = filen kom med indmeldingen.'

# ---------------------------------------------------------------------------
Write-Host "`n=== $SECTIONS ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
New-MdList $SECTIONS 'Issue Board: Application og Section. Een raekke pr. Section. Seedes fra sharepoint/seed/IB_AppSections.csv.'
if (-not $WhatIfOnly) {
    # Title er Application, saa listen kan laeses direkte i SharePoint.
    Set-PnPField -List $SECTIONS -Identity 'Title' -Values @{ Title = 'Application'; Indexed = $true }
    Write-Host "    ~ Title -> Application" -ForegroundColor Green
}
New-MdField 'IB_AppSections' 'Section' Text
New-MdField 'IB_AppSections' 'AppOrder' Number -Description 'Applications raekkefoelge.'
New-MdField 'IB_AppSections' 'SectionOrder' Number -Description 'Sectionens raekkefoelge under sin Application.'
New-MdField 'IB_AppSections' 'IsActive' Boolean -Indexed -Description 'Nej = vises ikke i appen.'
New-MdField 'IB_AppSections' 'ScreenKey' Text -Description 'Noeglen i tools/canvas_apps.json for skaermen (fx vhplan). Bruges til at foreslaa Application.'
New-MdField 'IB_AppSections' 'DomainColor' Text -Description 'Farvetoken (tools/design_tokens.py), valgfri.'
New-MdField 'IB_AppSections' 'IconRef' Text -Description 'Ikonnoegle (tools/icons.py), valgfri.'

# ---------------------------------------------------------------------------
Write-Host "`n=== $SHARED (udgaaet, #193) ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
# Den anonyme kopi bruges ikke laengere. Den slettes KUN med
# -RemoveSharedIssues - aldrig ved et uheld.
if (-not (Get-PnPList -Identity $SHARED -ErrorAction SilentlyContinue)) {
    Write-Host "  = Listen findes ikke" -ForegroundColor DarkGray
} elseif (-not $RemoveSharedIssues) {
    Write-Host "  = Listen findes stadig og bruges ikke. Koer med -RemoveSharedIssues for at slette den." -ForegroundColor Yellow
} elseif ($WhatIfOnly) {
    Write-Host "  ? ville slette listen '$SHARED'" -ForegroundColor Yellow
} else {
    Remove-PnPList -Identity $SHARED -Recycle -Force
    Write-Host "  - Listen '$SHARED' er slettet (ligger i sitets papirkurv)" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== $SECTIONS - seed ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
if (-not (Test-Path $SeedPath)) { throw "Finder ikke $SeedPath" }
$seed = Import-Csv -Path $SeedPath -Encoding UTF8
if ($WhatIfOnly) {
    Write-Host "  ? ville seede $($seed.Count) raekker fra $SeedPath" -ForegroundColor Yellow
} else {
    $index = @{}
    foreach ($it in (Get-PnPListItem -List $SECTIONS -PageSize 500)) {
        $index[('{0}|{1}' -f $it.FieldValues.Title, $it.FieldValues.Section)] = $it
    }
    $added = 0; $kept = 0; $updated = 0
    foreach ($r in $seed) {
        $values = @{
            Title        = $r.Application.Trim()
            Section      = $r.Section.Trim()
            AppOrder     = [int]$r.AppOrder
            SectionOrder = [int]$r.SectionOrder
            ScreenKey    = $r.ScreenKey
            DomainColor  = $r.DomainColor
            IconRef      = $r.IconRef
            IsActive     = [bool]::Parse($r.IsActive)
        }
        $key = '{0}|{1}' -f $values.Title, $values.Section
        if ($index.ContainsKey($key)) {
            if ($Force) {
                Set-PnPListItem -List $SECTIONS -Identity $index[$key].Id -Values $values | Out-Null
                $updated++
            } else {
                $kept++
            }
        } else {
            Add-PnPListItem -List $SECTIONS -Values $values | Out-Null
            $added++
        }
    }
    $msg = "  {0} tilfoejet, {1} roert ikke, {2} overskrevet" -f $added, $kept, $updated
    Write-Host $msg -ForegroundColor Green
}

# ---------------------------------------------------------------------------
Write-Host "`n=== Rettigheder ===" -ForegroundColor Cyan
# ---------------------------------------------------------------------------
if ($SkipPermissions) {
    Write-Host "  springes over (-SkipPermissions)" -ForegroundColor Yellow
} else {
    $ROLE_READ = Get-MdRoleName 'Reader'
    $ROLE_CONTRIBUTE = Get-MdRoleName 'Contributor'
    $ROLE_DESIGN = Get-MdRoleName 'WebDesigner'
    $ROLE_FULL = Get-MdRoleName 'Administrator'
    Write-Host "  $TICKETS (alle laeser, hver retter sine egne, admins alle)"
    Set-OpenTicketList $TICKETS
    if (Get-PnPList -Identity $TICKETS -ErrorAction SilentlyContinue) {
        Write-Host "  $TICKETS - gamle sagers rettigheder"
        Reset-TicketItemPermissions $TICKETS
        Write-Host "  $TICKETS - rapportoeren som Created By (issue #300)"
        Set-TicketAuthors $TICKETS
    }
    Write-Host "  $COMMENTS (privat)"
    Set-PrivateList $COMMENTS
    Write-Host "  $SECTIONS (alle laeser)"
    Set-MdReadOnlyList $SECTIONS $FlowAccount
}

# ---------------------------------------------------------------------------
Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Write-Host "Det var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
    return
}
Write-Host "Naeste skridt, som scriptet IKKE goer:" -ForegroundColor Yellow
Write-Host "  1. Kontroller under Listeindstillinger > Tilladelser, at $COMMENTS kun"
Write-Host "     har ejerne og flowets konto, og at $TICKETS har ejerne, Members"
Write-Host "     (Contribute), flowets konto og admins (Design). Andre personer, der var"
Write-Host "     tilfoejet direkte paa sitet, er kopieret med og skal fjernes i haanden."
Write-Host "  2. Importer solution BIO SAP med flowene BioSap-IssueBoard-Submit og"
Write-Host "     BioSap-IssueBoard-OnCreated, saet deres forbindelser til servicekontoen,"
Write-Host "     og slaa BioSap-IssueBoard-OnCreated til."
Write-Host "  3. Datakilderne i Studio: $TICKETS, $COMMENTS, $SECTIONS og flowet"
Write-Host "     BioSap-IssueBoard-Submit. $SHARED bruges ikke laengere."
Write-Host "     Appen vedhaefter filer med Patch paa $TICKETS (issue #300) - flowets"
Write-Host "     handling attach bruges ikke laengere."
Write-Host "  4. Koer sharepoint/inspect/Export-ListSchema.ps1, saa schema.md kender"
Write-Host "     listerne."
