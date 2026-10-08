<#
.SYNOPSIS
    Opretter GitHub-issues fra de sager i Issue Board, som en admin har
    godkendt (status Triaged).

.DESCRIPTION
    UAT-processen: en tester melder et fund i Issue Board, en admin
    vurderer det og saetter status til Triaged, naar aendringen skal laves.
    Dette script henter de sager og opretter eet GitHub-issue pr. sag i
    repoet. Issue-rutinen tager issuet op ved naeste koersel, fordi det er
    oprettet med din konto.

    HVAD DER KOMMER MED
        Titel:  [ISS-000123] <sagens titel>
        Tekst:  Application, Section, alvor, prioritet, relateret
                anmodning, What happened, Steps to reproduce, Expected
                result, Actual result og navnene paa vedhaeftningerne.
        Label:  uat (oprettes, hvis den ikke findes).

    HVAD DER IKKE KOMMER MED
        Rapportoerens navn og e-mail, tildelingen, kommentarerne og selve
        filerne. Siden issue #193 staar rapportoerens navn synligt paa
        sagen i Issue Board - men scriptet henter KUN kolonnerne i $FIELDS
        (ingen ReporterEmail, ReporterName, AssignedTo*, Author eller
        Editor), saa navnet kan ikke komme med. tests/test_issue_board.py
        holder det sadan.
        REPOET ER OFFENTLIGT: alt, der sendes, kan alle laese. Scriptet
        viser hver sag, foer den sendes, og advarer, hvis teksten
        indeholder en e-mailadresse.

    DOBBELTE ISSUES
        Scriptet slaar sagsnummeret op i de issues, der har label uat
        (aabne og lukkede). Findes det, springes sagen over. Scriptet kan
        derfor koeres igen og igen.

    SCRIPTET AENDRER INTET I SHAREPOINT
        Det laeser kun IB_Tickets. Saet selv sagen til In progress i
        Issue Board (Edit), og skriv gerne GitHub-linket som kommentar -
        saa kommer aendringen i sagens Activity.

    ADGANG
        Du skal kunne laese IB_Tickets - siden issue #193 kan alle Members
        det (kommentarerne laeses ikke). Paa GitHub skal du bruge
        et token med Issues: Read and write paa repoet (fine-grained
        personal access token). Tokenet gemmes ALDRIG i repoet.

.PARAMETER SiteUrl
    Sitet med BIO SAP-listerne.

.PARAMETER Repo
    owner/navn paa GitHub. Standard: PeterBjerre/Canvas_apps

.PARAMETER Status
    Den status, der betyder "godkendt". Standard: Triaged

.PARAMETER TicketNo
    Kun disse sager, fx -TicketNo ISS-000123,ISS-000130. Sagen skal
    stadig have status -Status.

.PARAMETER Label
    Label paa de oprettede issues. Standard: uat

.PARAMETER Token
    GitHub-token. Uden parameteren bruges $env:GITHUB_TOKEN, og findes den
    ikke, spoerger scriptet (input vises ikke).

.PARAMETER Yes
    Spoerg ikke for hver sag.

.PARAMETER WhatIfOnly
    Toerloeb: vis hvad der ville blive oprettet, opret intet.

.EXAMPLE
    .\Send-IssueBoardToGitHub.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -WhatIfOnly

.EXAMPLE
    $env:GITHUB_TOKEN = '<dit token>'
    .\Send-IssueBoardToGitHub.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"

.NOTES
    Kraever PnP.PowerShell (samme login som provisioneringen, se
    ..\provision\_Common.psm1). Kolonnenavnene staar ogsaa i
    "Issue Board/build/ib_config.py"; tests/test_issue_board.py holder dem
    i trit.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string] $Repo = 'PeterBjerre/Canvas_apps',
    [string] $Status = 'Triaged',
    [string[]] $TicketNo,
    [string] $Label = 'uat',
    [string] $Token,
    [switch] $Yes,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

$TICKETS = 'IB_Tickets'
$FIELDS = 'ID', 'Title', 'TicketNo', 'Description', 'ReproSteps', 'ExpectedResult',
          'ActualResult', 'Application', 'Section', 'OtherContext', 'RelatedRequestNo',
          'Severity', 'Priority', 'Status', 'IsArchived', 'Attachments'
$API = 'https://api.github.com'
$MARK = '<!-- issue-board: {0} -->'

# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------
function Get-PlainToken {
    if ($Token) { return $Token }
    if ($env:GITHUB_TOKEN) { return $env:GITHUB_TOKEN }
    $s = Read-Host 'GitHub-token (Issues: Read and write paa repoet)' -AsSecureString
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

function Invoke-GitHub {
    param([string]$Method, [string]$Path, $Body)
    $p = @{
        Method  = $Method
        Uri     = "$API$Path"
        Headers = @{
            Authorization          = "Bearer $script:GhToken"
            Accept                 = 'application/vnd.github+json'
            'X-GitHub-Api-Version' = '2022-11-28'
            'User-Agent'           = 'BioSap-IssueBoard'
        }
    }
    if ($null -ne $Body) {
        # Bytes, saa Windows PowerShell 5.1 ikke sender teksten som Latin-1.
        $p.Body = [Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Depth 5))
        $p.ContentType = 'application/json; charset=utf-8'
    }
    # Via en variabel: Windows PowerShell 5.1 skriver et JSON-array som EET objekt.
    $r = Invoke-RestMethod @p
    return $r
}

function Get-ExistingTicketNos {
    # Sagsnumre, der allerede har et issue med labelen (aabne og lukkede).
    $found = @{}
    $page = 1
    do {
        $label = [Uri]::EscapeDataString($Label)
        $batch = @(Invoke-GitHub GET "/repos/$Repo/issues?labels=$label&state=all&per_page=100&page=$page")
        foreach ($i in $batch) {
            if ($i.pull_request) { continue }
            if ($i.title -match '^\[(ISS-\d+)\]') { $found[$Matches[1]] = $i.html_url }
            if ($i.body -and $i.body -match '<!-- issue-board: (ISS-\d+) -->') { $found[$Matches[1]] = $i.html_url }
        }
        $page++
    } while ($batch.Count -eq 100)
    return $found
}

function Confirm-Label {
    try {
        Invoke-GitHub GET "/repos/$Repo/labels/$([Uri]::EscapeDataString($Label))" | Out-Null
    }
    catch {
        if ($WhatIfOnly) {
            Write-Host "  ? ville oprette labelen '$Label'" -ForegroundColor Yellow
            return
        }
        Invoke-GitHub POST "/repos/$Repo/labels" @{
            name = $Label; color = '5319e7'; description = 'Fund fra UAT via Issue Board'
        } | Out-Null
        Write-Host "  + Label '$Label' oprettet" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# Sagen -> issuet
# ---------------------------------------------------------------------------
function Get-Text {
    param($Item, [string]$Name)
    $v = $Item[$Name]
    if ($null -eq $v) { return '' }
    return ([string]$v).Trim()
}

function New-IssueBody {
    param($Item, [string]$No, [string[]]$Files)
    $app = Get-Text $Item 'Application'
    $sec = Get-Text $Item 'Section'
    $other = Get-Text $Item 'OtherContext'
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("Fra Issue Board: **$No**, godkendt af en admin (status $Status).")
    $lines.Add('')
    $lines.Add("- **Application:** $app")
    $lines.Add("- **Section:** $sec")
    if ($other) { $lines.Add("- **Where (Other):** $other") }
    $lines.Add("- **Severity:** $(Get-Text $Item 'Severity')")
    $lines.Add("- **Priority:** $(Get-Text $Item 'Priority')")
    $rel = Get-Text $Item 'RelatedRequestNo'
    if ($rel) { $lines.Add("- **Related request:** $rel") }
    foreach ($s in @(
            @('What happened', 'Description'),
            @('Steps to reproduce', 'ReproSteps'),
            @('Expected result', 'ExpectedResult'),
            @('Actual result', 'ActualResult'))) {
        $t = Get-Text $Item $s[1]
        if ($t) {
            $lines.Add('')
            $lines.Add("### $($s[0])")
            $lines.Add('')
            $lines.Add($t)
        }
    }
    if ($Files.Count) {
        $lines.Add('')
        $lines.Add('### Vedhaeftninger')
        $lines.Add('')
        $lines.Add("Filerne ligger paa sagen $No i Issue Board og er ikke kopieret hertil, fordi repoet er offentligt:")
        foreach ($f in $Files) { $lines.Add("- $f") }
    }
    $lines.Add('')
    $lines.Add('Naar rettelsen er deployet, saetter en admin sagen til Ready for retest i Issue Board, saa testeren faar besked.')
    $lines.Add('')
    $lines.Add(($MARK -f $No))
    return ($lines -join "`n")
}

function Get-FileNames {
    param($Item)
    if (-not $Item['Attachments']) { return @() }
    $files = Get-PnPProperty -ClientObject $Item -Property AttachmentFiles
    return @($files | ForEach-Object { $_.FileName })
}

# ---------------------------------------------------------------------------
# Koersel
# ---------------------------------------------------------------------------
Import-Module (Join-Path $PSScriptRoot '..\provision\_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

Write-Host ""
Write-Host "Henter sager med status '$Status' fra $TICKETS ..." -ForegroundColor Cyan
$items = @(Get-PnPListItem -List $TICKETS -PageSize 500 -Fields $FIELDS | Where-Object {
        (Get-Text $_ 'Status') -eq $Status -and -not $_['IsArchived']
    })
if ($TicketNo) {
    $want = $TicketNo | ForEach-Object { $_.Trim().ToUpperInvariant() }
    $items = @($items | Where-Object { $want -contains (Get-Text $_ 'TicketNo').ToUpperInvariant() })
}
$items = @($items | Sort-Object { [int]$_['ID'] })
Write-Host "  $($items.Count) sag(er) har status '$Status'."
if (-not $items.Count) { return }

$script:GhToken = Get-PlainToken
Write-Host "Slaar eksisterende issues op i $Repo ..." -ForegroundColor Cyan
$existing = Get-ExistingTicketNos
Confirm-Label

$created = New-Object System.Collections.Generic.List[string]
$all = [bool]$Yes
foreach ($it in $items) {
    $no = Get-Text $it 'TicketNo'
    if (-not $no) { $no = 'ISS-{0:000000}' -f [int]$it['ID'] }
    if ($existing.ContainsKey($no)) {
        Write-Host "  = $no har allerede et issue: $($existing[$no])" -ForegroundColor DarkGray
        continue
    }
    $title = "[$no] $(Get-Text $it 'Title')"
    $body = New-IssueBody $it $no (Get-FileNames $it)

    Write-Host ""
    Write-Host "---- $title" -ForegroundColor White
    Write-Host $body
    if ($body -match '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}') {
        Write-Host "  ! Teksten indeholder en e-mailadresse. Repoet er offentligt." -ForegroundColor Red
    }
    if ($WhatIfOnly) {
        Write-Host "  ? ville oprette issuet" -ForegroundColor Yellow
        continue
    }
    if (-not $all) {
        # Ingen switch: break og continue i en switch gaelder switchen, ikke loekken.
        $a = (Read-Host "Opret issuet? [j]a / [n]ej / [a]lle / [s]top").Trim().ToLowerInvariant()
        if ($a -eq 's') { break }
        if ($a -eq 'a') { $all = $true }
        elseif ($a -ne 'j') {
            Write-Host "  - sprunget over" -ForegroundColor DarkGray
            continue
        }
    }
    $issue = Invoke-GitHub POST "/repos/$Repo/issues" @{ title = $title; body = $body; labels = @($Label) }
    Write-Host "  + $no -> $($issue.html_url)" -ForegroundColor Green
    $created.Add("$no  $($issue.html_url)")
}

Write-Host ""
if ($created.Count) {
    Write-Host "Oprettet $($created.Count) issue(s). Saet sagerne til In progress i Issue Board og skriv linket som kommentar:" -ForegroundColor Cyan
    $created | ForEach-Object { Write-Host "  $_" }
} elseif (-not $WhatIfOnly) {
    Write-Host "Ingen nye issues." -ForegroundColor Cyan
}
