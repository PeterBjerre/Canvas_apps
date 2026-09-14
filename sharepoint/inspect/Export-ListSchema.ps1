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

    Om data: proeveraekkerne er rigtige data. Er der noget i listerne, der
    ikke maa forlade sitet, saa koer med -NoData foerste gang - saa kommer
    der kun kolonnestruktur med. Strukturen alene er nok til at vurdere
    datamodellen; proeveraekkerne er kun til at se, hvilken FORM vaerdierne
    har (staar der "SSVAP" eller "*PROD - Produktion" i et arbejdscenter?).

.PARAMETER SiteUrl
    Sitet listerne ligger paa.

.PARAMETER Lists
    Begraens til bestemte lister. Udelad for alle ikke-skjulte lister.

.PARAMETER SampleRows
    Antal raekker pr. liste (standard 8). Store lister tager ikke laengere
    tid - der bruges en CAML RowLimit, ikke et fuldt hent.

.PARAMETER NoData
    Spring proeveraekkerne over. Kun struktur.

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
    .\Export-ListSchema.ps1 -SiteUrl "https://..." -NoData

.NOTES
    Kraever PnP.PowerShell:  Install-Module PnP.PowerShell -Scope CurrentUser
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [string[]] $Lists,
    [int] $SampleRows = 8,
    [switch] $NoData,
    [string[]] $Exclude,
    [switch] $IncludeAll,
    [int] $MaxRowsForSample = 5000,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

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
if ($ClientId) { $conn.ClientId = $ClientId }
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
    includesData = (-not $NoData)
    skippedLists = $(if ($Lists -or $IncludeAll) { @() } else { $SKIP_LISTS })
    lists       = @()
}

$failed = @()

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
    if (-not $NoData -and $l.ItemCount -gt $MaxRowsForSample) {
        Write-Host ("    {0} raekker - springer proeveraekkerne over" -f $l.ItemCount) -ForegroundColor DarkYellow
    }
    elseif (-not $NoData -and $l.ItemCount -gt 0) {
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
        $rows | ConvertTo-Json -Depth 6 |
            Set-Content (Join-Path $OutDir "sample-$safe.json") -Encoding UTF8
    }
  }
  catch {
    $failed += [ordered]@{ list = $l.Title; error = $_.Exception.Message }
    Write-Host ("    FEJLEDE: {0}" -f $_.Exception.Message) -ForegroundColor Red
  }
}

$report.failedLists = $failed

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
