<#
.SYNOPSIS
    Udtraekker den KOMPLETTE struktur af SharePoint-listerne bag VH-plan
    appen, saa datamodellen kan gennemgaas uden adgang til sitet.

.DESCRIPTION
    Skriver til sharepoint/inspect/out/:

        schema.json      alt, maskinlaesbart
        schema.md        det samme som laesbare tabeller
        sample-<liste>.json   de foerste rows pr. liste

    Scriptet SKRIVER IKKE til SharePoint. Det laeser kun.

    Om data (R2-025): repoet er OFFENTLIGT. Som standard kommer der kun
    kolonnestruktur med - strukturen alene er nok til at vurdere
    datamodellen. Med -IncludeData kommer proeveraekker med, saa man kan se,
    hvilken FORM vaerdierne har (staar der "SSVAP" eller "*PROD -
    Produktion" i et arbejdscenter?), men personer pseudonymiseres FOER
    filen skrives:

      * Person-/User-kolonner, Author og Editor
      * Text-kolonner, hvis navn ender paa Email, By, Member, Responsible,
        <Requester|AssignedTo|Owner|Reporter|Author>Name eller er
        Approver1/Approver2
      * e-mailadresser, kendte navne og initialer i al anden tekst (og
        5-bogstavs initialer i MD_Approver-listernes noter)

    blive til userNN eller userNN@example.invalid. NN er en fast hash af
    vaerdien (MD5, 0-99), saa samme person faar samme pseudonym paa tvaers
    af listerne, og formen kan stadig ses.

.PARAMETER SiteUrl
    Sitet listerne ligger paa.

.PARAMETER Lists
    Begraens til bestemte lister. Udelad for alle ikke-skjulte lister.

.PARAMETER SampleRows
    Antal raekker pr. liste (standard 8). Store lister tager ikke laengere
    tid - der bruges en CAML RowLimit, ikke et fuldt hent.

.PARAMETER IncludeData
    Tag proeveraekker med (pseudonymiseret, se ovenfor). Uden den kun
    struktur.

.PARAMETER NoData
    Udgaaet - kun struktur er nu standarden. Vinder over -IncludeData.

.PARAMETER Exclude
    Yderligere lister der skal springes over. Laegges oveni standardlisten,
    som i forvejen udelader FunctionalLocations (~122.700 raekker, bruges ikke
    af appen og faar udtraekket til at haenge).

.PARAMETER IncludeAll
    Tag ogsaa de som standard udeladte lister med. Regn med lang ventetid.

.PARAMETER MaxRowsForSample
    Lister over denne stoerrelse faar hentet struktur, men ingen proeveraekker
    (standard 5000 = SharePoints listevisningsgraense). Over graensen kan selv
    en RowLimit-forespoergsel blive kvalt af throttling.

.EXAMPLE
    .\Export-ListSchema.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>"

.EXAMPLE
    .\Export-ListSchema.ps1 -SiteUrl "https://..." -IncludeData

.NOTES
    Kraever PnP.PowerShell:  Install-Module PnP.PowerShell -Scope CurrentUser
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string[]] $Lists,
    [int] $SampleRows = 8,
    [switch] $IncludeData,
    [switch] $NoData,
    [string[]] $Exclude,
    [switch] $IncludeAll,
    [int] $MaxRowsForSample = 5000,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

# Kun struktur, medmindre -IncludeData (R2-025). -NoData er udgaaet, men
# vinder stadig, saa et gammelt kald ikke pludselig tager data med.
$WithData = $IncludeData -and -not $NoData

$OutDir = Join-Path $PSScriptRoot 'out'
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# PnP.PowerShell 2.x har ikke laengere en faelles app-registrering, saa
# -Interactive kraever et ClientId. Saet PNP_CLIENT_ID som miljoevariabel,
# eller giv -ClientId. Appen findes allerede i tenanten:
#     9bc3ab49-b65d-410a-85ad-de819febfddc
# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
# Har du ingen app, opretter denne en ny:
#     Register-PnPEntraIDAppForInteractiveLogin ``
#         -ApplicationName "PnP Masterdata" -Tenant <tenant>.onmicrosoft.com -Interactive
$conn = @{ Url = $SiteUrl; Interactive = $true }
# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Uden et fejler MSAL med "User canceled
# authentication" - hvilket lyder som om brugeren trykkede fortryd, men
# ikke er det. Her stod "if ($ClientId) { ... }", saa scriptet koerte
# videre uden. Nu er der en standard.
# Et client id er ikke en hemmelighed - se docs/08-datamapning.md 6B.
if (-not $ClientId) { $ClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc' }
$conn.ClientId = $ClientId
Connect-PnPOnline @conn

# Systemkolonner udelades. De siger intet om datamodellen og fylder alt.
$SKIP = @(
    'ContentType','Attachments','Edit','LinkTitleNoMenu','LinkTitle','DocIcon',
    '_UIVersionString','_ComplianceFlags','_ComplianceTag','_ComplianceTagWrittenTime',
    '_ComplianceTagUserId','_IsRecord','AppAuthor','AppEditor','FolderChildCount',
    'ItemChildCount','_CommentCount','_CommentFlags','ComplianceAssetId','InstanceID',
    'Order','GUID','WorkflowVersion','WorkflowInstanceID','FileLeafRef','FileDirRef',
    'FSObjType','SortBehavior','PermMask','UniqueId','ProgId','ScopeId','MetaInfo',
    'owshiddenversion','_Level','_HasCopyDestinations','_CopySource','_ModerationStatus',
    '_ModerationComments','_UIVersion','Created_x0020_Date','Last_x0020_Modified',
    'SyncClientId','CheckedOutTitle','CheckedOutUserId','IsCheckedoutToLocal','SMTotalSize',
    'SMLastModifiedDate','SMTotalFileStreamSize','SMTotalFileCount','ParentVersionString',
    'ParentLeafName','ParentUniqueId','StreamHash','BSN','AccessPolicy','_ListSchemaVersion',
    '_Dirty','_Parsable','_StubFile','_VirusStatus','_VirusVendorID','_VirusInfo',
    'A2ODMountCount','_EditMenuTableStart','_EditMenuTableStart2','_EditMenuTableEnd',
    'ServerUrl','EncodedAbsUrl','BaseName','FileSizeDisplay','_ShortcutUrl',
    '_ShortcutSiteId','_ShortcutWebId','_ShortcutUniqueId','_ExtendedDescription',
    'TriggerFlowInfo','NoExecute','OriginatorId','HashCode','_activity','_Emoji',
    '_ColorTag','_ColorHex','_SourceUrl','_SharedFileIndex','_SPSelectedFlag',
    '_Restrictions','SelectFilename','TemplateUrl','xd_ProgID','xd_Signature',
    '_CheckinComment','_CopySource','CheckoutUser','VirusStatus'
)

function Get-ChoiceValues {
    param($xml)
    # Praecis <CHOICE>, ikke <CHOICE[^>]*> - det sidste matcher ogsaa den
    # omsluttende <CHOICES>, saa foerste vaerdi fik et '<CHOICE>'-praefiks.
    $m = [regex]::Matches($xml, '<CHOICE>(.*?)</CHOICE>')
    if ($m.Count -eq 0) { return $null }
    return @($m | ForEach-Object { [System.Net.WebUtility]::HtmlDecode($_.Groups[1].Value) })
}

function Get-XmlAttr {
    param($xml, $name)
    $m = [regex]::Match($xml, "$name=`"([^`"]*)`"")
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

# Lister der springes over som standard.
#
# FunctionalLocations har ~122.700 raekker. Appen bruger den IKKE - FL-soegningen
# gaar gennem flowet BioSap-Integration-FunctionalLocations, fordi 122.700 raekker
# er 61 gange delegationsloftet. At laese den koster lang ventetid og faar
# udtraekket til at fejle, uden at give noget igen.
#
# Skal den alligevel med: -IncludeAll, eller navngiv den med -Lists.
$SKIP_LISTS = @('FunctionalLocations')
if ($Exclude) { $SKIP_LISTS += $Exclude }

$all = Get-PnPList -Includes ItemCount, Hidden, BaseTemplate, DefaultViewUrl |
       Where-Object { -not $_.Hidden -and $_.BaseTemplate -eq 100 }
if ($Lists) {
    # Navngiver du lister eksplicit, er det dem du faar - ogsaa de udelukkede.
    $all = $all | Where-Object { $Lists -contains $_.Title }
} elseif (-not $IncludeAll) {
    $skipped = @($all | Where-Object { $SKIP_LISTS -contains $_.Title })
    foreach ($sk in $skipped) {
        Write-Host ("  springer over: {0} ({1} raekker)" -f $sk.Title, $sk.ItemCount) -ForegroundColor DarkYellow
    }
    $all = $all | Where-Object { $SKIP_LISTS -notcontains $_.Title }
}
$all = $all | Sort-Object Title

Write-Host "`n$($all.Count) lister`n" -ForegroundColor Cyan

$report = [ordered]@{
    site        = $SiteUrl
    exportedOn  = (Get-Date).ToString('yyyy-MM-dd HH:mm')
    includesData = $WithData
    pseudonymized = $WithData
    skippedLists = $(if ($Lists -or $IncludeAll) { @() } else { $SKIP_LISTS })
    lists       = @()
}

$failed = @()
# Proeveraekkerne samles foerst og skrives til sidst: pseudonymiseringen
# skal kende alle listers personer, foer den retter fri tekst.
$samples = [ordered]@{}

foreach ($l in $all) {
  # En enkelt liste, der ikke kan laeses (rettigheder, en kolonne med en
  # defekt definition), maa ikke vaelte hele udtraekket - og den maa
  # SLET ikke goere det i stilhed, saa et halvt schema.md bliver committet
  # som om alt var fint. Fejl samles og skrives til sidst OG til schema.json.
  try {
    Write-Host ("  {0,-34} {1,8} raekker" -f $l.Title, $l.ItemCount) -ForegroundColor Green

    $fields = @()
    foreach ($f in (Get-PnPField -List $l.Title)) {
        if ($SKIP -contains $f.InternalName) { continue }
        if ($f.Hidden -and $f.InternalName -notin @('Title')) { continue }

        $xml = $f.SchemaXml
        $entry = [ordered]@{
            internalName = $f.InternalName
            displayName  = $f.Title           # <- Power Fx binder PAA DETTE
            type         = $f.TypeAsString
            required     = [bool]$f.Required
            indexed      = [bool]$f.Indexed
            readOnly     = [bool]$f.ReadOnlyField
        }
        if ($f.Description) { $entry.description = $f.Description }

        $choices = Get-ChoiceValues $xml
        # ConvertTo-Json pakker et array med EEN vaerdi ud til en skalar.
        # [array] i feltet holder det som en liste hele vejen igennem.
        if ($choices) { $entry.choices = [array]$choices }

        if ($f.TypeAsString -like 'Lookup*' -or $f.TypeAsString -like 'User*') {
            $entry.lookupList  = Get-XmlAttr $xml 'List'
            $entry.lookupField = Get-XmlAttr $xml 'ShowField'
            $entry.allowMultiple = ($xml -match 'Mult="TRUE"')
        }
        if ($f.TypeAsString -eq 'Calculated') {
            $m = [regex]::Match($xml, '<Formula>(.*?)</Formula>', 'Singleline')
            if ($m.Success) { $entry.formula = [System.Net.WebUtility]::HtmlDecode($m.Groups[1].Value) }
        }
        $fields += $entry
    }

    $views = @()
    foreach ($v in (Get-PnPView -List $l.Title -Includes ViewFields)) {
        $views += [ordered]@{
            title       = $v.Title
            defaultView = [bool]$v.DefaultView
            rowLimit    = $v.RowLimit
            fields      = @($v.ViewFields | Where-Object { $SKIP -notcontains $_ })
        }
    }

    $report.lists += [ordered]@{
        title     = $l.Title
        itemCount = $l.ItemCount
        fields    = $fields
        views     = $views
    }

    # Over listevisningsgraensen kan selv en RowLimit-forespoergsel blive
    # kvalt af throttling. Strukturen hentes stadig - kun raekkerne springes over.
    if ($WithData -and $l.ItemCount -gt $MaxRowsForSample) {
        Write-Host ("    {0} raekker - springer proeveraekkerne over" -f $l.ItemCount) -ForegroundColor DarkYellow
    }
    elseif ($WithData -and $l.ItemCount -gt 0) {
        $caml = "<View><Query></Query><RowLimit>$SampleRows</RowLimit></View>"
        $rows = @()
        foreach ($it in (Get-PnPListItem -List $l.Title -Query $caml)) {
            $r = [ordered]@{}
            foreach ($fn in ($fields | ForEach-Object { $_.internalName })) {
                $v = $it.FieldValues[$fn]
                if ($null -eq $v) { $r[$fn] = $null; continue }
                # Lookup/User kommer som objekt - tag den laesbare vaerdi.
                if ($v -is [Microsoft.SharePoint.Client.FieldLookupValue]) {
                    $r[$fn] = "$($v.LookupId): $($v.LookupValue)"
                } elseif ($v -is [Microsoft.SharePoint.Client.FieldLookupValue[]]) {
                    $r[$fn] = @($v | ForEach-Object { "$($_.LookupId): $($_.LookupValue)" })
                } elseif ($v -is [Microsoft.SharePoint.Client.FieldUrlValue]) {
                    $r[$fn] = $v.Url
                } else {
                    $r[$fn] = $v
                }
            }
            $rows += $r
        }
        $safe = ($l.Title -replace '[^\w\-]', '_')
        $types = @{}
        foreach ($f in $fields) { $types[$f.internalName] = $f.type }
        $samples[$safe] = @{ rows = $rows; types = $types }
    }
  }
  catch {
    $failed += [ordered]@{ list = $l.Title; error = $_.Exception.Message }
    Write-Host ("    FEJLEDE: {0}" -f $_.Exception.Message) -ForegroundColor Red
  }
}

$report.failedLists = $failed

# --- Pseudonymisering (R2-025) ---------------------------------------------
# Samme regler som beskrevet oeverst. Repoet er offentligt: et navn, en
# adresse eller initialer (initialer + e-maildomaenet = adressen) maa ikke
# naa en sample-fil.
$RX_EMAIL    = [regex]'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
$RX_PERSON   = [regex]'(?i)(Email|By|Member|^Approver\d$|(Requester|AssignedTo|Owner|Reporter|Author)Name|Responsible)$'
$RX_INITIALS = [regex]'\b[A-Z]{5}\b'
$RX_KEEP     = [regex]'(?i)^(system|.*\bsvc[_-].*|svc_.*|)$'
$RX_USERVAL  = [regex]'^(\d+): (.*)$'
$RX_IDTOKEN  = [regex]'[A-Za-z]+(?=@)|^[A-Z]{4,8}$'
$md5 = [System.Security.Cryptography.MD5]::Create()

function Get-PseudoNum([string]$Key) {
    $b = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Key.Trim().ToLowerInvariant()))
    return ([int]$b[0] * 256 + [int]$b[1]) % 100
}

function Get-Pseudo([string]$Value) {
    if ($RX_KEEP.IsMatch($Value.Trim()) -or $Value.Contains('example.invalid')) { return $Value }
    if ($Value.Contains('@')) { return "user$(Get-PseudoNum ($Value.Split('@')[0]))@example.invalid" }
    return "user$(Get-PseudoNum $Value)"
}

function Test-UserField([string]$Name, [string]$Type) {
    return ($Type -like 'User*') -or $Name -eq 'Author' -or $Name -eq 'Editor'
}

# Pas 1: hvem er personerne? Visningsnavne fra Person-kolonnerne og
# id'er (initialer, adressens lokale del) fra person-tekstkolonnerne.
$names = New-Object 'System.Collections.Generic.HashSet[string]'
$ids   = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($safe in $samples.Keys) {
    $types = $samples[$safe].types
    foreach ($r in $samples[$safe].rows) {
        foreach ($k in @($r.Keys)) {
            foreach ($v in @($r[$k])) {
                if ($v -isnot [string]) { continue }
                if (Test-UserField $k $types[$k]) {
                    $m = $RX_USERVAL.Match($v)
                    $n = if ($m.Success) { $m.Groups[2].Value.Trim() } else { $v.Trim() }
                    if ($n.Contains(' ') -and -not $RX_KEEP.IsMatch($n)) { [void]$names.Add($n) }
                }
                if ($RX_PERSON.IsMatch($k)) {
                    foreach ($t in $RX_IDTOKEN.Matches($v.Trim())) {
                        if ($t.Value.Length -ge 4 -and $t.Value.Length -le 8) { [void]$ids.Add($t.Value.ToUpperInvariant()) }
                    }
                }
            }
        }
    }
}
function New-AltRegex($set) {
    if (-not $set.Count) { return $null }
    $alts = @($set | Sort-Object { $_.Length } -Descending | ForEach-Object { [regex]::Escape($_) })
    return [regex]($alts -join '|')
}
$RX_NAMES = New-AltRegex $names
$RX_IDS   = New-AltRegex $ids
$pseudoEval = [System.Text.RegularExpressions.MatchEvaluator] { param($m) Get-Pseudo $m.Value }

function Convert-FreeText([string]$Value, [bool]$Approver) {
    $v = $RX_EMAIL.Replace($Value, $pseudoEval)
    if ($RX_NAMES) { $v = $RX_NAMES.Replace($v, $pseudoEval) }
    if ($Approver) { $v = $RX_INITIALS.Replace($v, $pseudoEval) }
    if ($RX_IDS)   { $v = $RX_IDS.Replace($v, $pseudoEval) }
    return $v
}

function Convert-SampleValue([string]$Name, [string]$Type, $Value, [bool]$Approver) {
    if ($Value -is [array]) {
        return @($Value | ForEach-Object { Convert-SampleValue $Name $Type $_ $Approver })
    }
    if ($Value -isnot [string]) { return $Value }
    if (Test-UserField $Name $Type) {
        $m = $RX_USERVAL.Match($Value)
        if ($m.Success) { return "$($m.Groups[1].Value): $(Get-Pseudo $m.Groups[2].Value)" }
        return (Get-Pseudo $Value)
    }
    if ($RX_PERSON.IsMatch($Name) -and ($Type -eq 'Text' -or $Type -eq 'Note')) {
        if ($Value.Contains('@')) { return $RX_EMAIL.Replace($Value, $pseudoEval) }
        return (Get-Pseudo $Value)
    }
    return (Convert-FreeText $Value $Approver)
}

# Pas 2: ret og skriv.
foreach ($safe in $samples.Keys) {
    $types = $samples[$safe].types
    $approver = $safe.StartsWith('MD_Approver')
    foreach ($r in $samples[$safe].rows) {
        foreach ($k in @($r.Keys)) {
            $r[$k] = Convert-SampleValue $k $types[$k] $r[$k] $approver
        }
    }
    $samples[$safe].rows | ConvertTo-Json -Depth 6 |
        Set-Content (Join-Path $OutDir "sample-$safe.json") -Encoding UTF8
}

$report | ConvertTo-Json -Depth 8 |
    Set-Content (Join-Path $OutDir 'schema.json') -Encoding UTF8

# --- Laesbar udgave ---------------------------------------------------------
$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# SharePoint-lister bag VH-plan appen")
[void]$md.AppendLine()
[void]$md.AppendLine("Udtrukket $($report.exportedOn) fra $SiteUrl")
[void]$md.AppendLine()
[void]$md.AppendLine("| Liste | Raekker | Kolonner |")
[void]$md.AppendLine("|---|---:|---:|")
foreach ($l in $report.lists) {
    [void]$md.AppendLine("| ``$($l.title)`` | $($l.itemCount) | $($l.fields.Count) |")
}
foreach ($l in $report.lists) {
    [void]$md.AppendLine()
    [void]$md.AppendLine("## ``$($l.title)``  -  $($l.itemCount) raekker")
    [void]$md.AppendLine()
    [void]$md.AppendLine("| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |")
    [void]$md.AppendLine("|---|---|---|:-:|:-:|---|")
    foreach ($f in $l.fields) {
        $notes = @()
        if ($f.choices)    { $notes += "valg: " + (($f.choices | Select-Object -First 12) -join ', ') }
        if ($f.lookupList) { $notes += "opslag -> $($f.lookupList) ($($f.lookupField))" }
        if ($f.formula)    { $notes += "beregnet: ``$($f.formula)``" }
        if ($f.readOnly)   { $notes += "skrivebeskyttet" }
        $req = if ($f.required) { 'x' } else { '' }
        $idx = if ($f.indexed)  { 'x' } else { '' }
        $dn  = if ($f.displayName -ne $f.internalName) { "**$($f.displayName)**" } else { $f.displayName }
        [void]$md.AppendLine("| ``$($f.internalName)`` | $dn | $($f.type) | $req | $idx | $($notes -join '; ') |")
    }
}
$md.ToString() | Set-Content (Join-Path $OutDir 'schema.md') -Encoding UTF8

if ($failed.Count) {
    Write-Host "`n$($failed.Count) liste(r) FEJLEDE og mangler i udtraekket:" -ForegroundColor Red
    foreach ($f in $failed) { Write-Host "  - $($f.list): $($f.error)" -ForegroundColor Red }
    Write-Host "Commit IKKE udtraekket som fuldstaendigt. Rapporter fejlene." -ForegroundColor Red
}

Write-Host "`nSkrevet til $OutDir" -ForegroundColor Cyan
Write-Host "  schema.json   schema.md   sample-*.json`n"
Write-Host "Naeste skridt: commit mappen og push, saa kan modellen gennemgaas." -ForegroundColor Yellow
