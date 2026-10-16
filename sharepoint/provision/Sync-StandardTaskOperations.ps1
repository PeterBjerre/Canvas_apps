<#
.SYNOPSIS
    Standardoperationerne (MD_StandardTaskOperations) ud i Excel og ind igen.

.DESCRIPTION
    VH-plan appen henter standardoperationerne pr. vaerk fra listen
    MD_StandardTaskOperations. Det er nemmere at rette 176 raekker i Excel
    end i SharePoint, saa scriptet har to trin:

      1. -Export  skriver listen til en .xlsx-fil, een raekke pr. operation.
      2. -Import  laeser den rettede fil og opdaterer listen.

    Excel-filen har kolonnerne ID, Plant, OperationNo og derefter felterne
    i $COLUMNS nedenfor - samme navne som i listen. TaskLabel (Title)
    staar ikke i filen; den saettes altid til "<Plant> <OperationNo>",
    ligesom Provision-StandardTaskOperations.ps1 goer.

    MATCH
      En raekke med ID opdaterer det element, der har det ID. Saadan kan
      man ogsaa omnummerere en operation (rette OperationNo eller Plant).
      En raekke UDEN ID matches paa Plant + OperationNo. Findes der intet
      element med den noegle, oprettes et nyt. Saadan seedes en tom liste.

    HVAD DER AENDRES
      Kun kolonner, der STAAR i filen, sammenlignes og skrives. Sletter man
      en kolonne i Excel, roeres feltet ikke. En TOM celle i en kolonne, der
      staar i filen, toemmer feltet.

    RAEKKER, DER MANGLER I FILEN
      Elementer i listen, som ikke er i filen, meldes - de slettes ikke.
      Med -DeleteMissing flyttes de til papirkurven (kan gendannes derfra).
      Kun vaerker, der har mindst een raekke i filen, kigges paa, saa en
      fil med kun ASV roerer ikke de andre vaerker.

    SIKKERHED
      Hele filen tjekkes foer der skrives noget: vaerk findes som valg,
      OperationNo er et helt tal, tal er tal, ingen dubletter af Plant +
      OperationNo, intet ID der ikke findes. Er der een fejl, skrives
      INTET. Med -WhatIfOnly vises aendringerne uden at skrive.

.PARAMETER Export
    Skriv listen til -Path.

.PARAMETER Import
    Opdater listen fra -Path.

.PARAMETER Path
    .xlsx-filen.

.PARAMETER Plant
    Kun ved -Export: tag kun disse vaerker med, fx -Plant ASV,HEV.

.PARAMETER WorksheetName
    Kun ved -Import: arket, der laeses. Standard er det foerste ark.

.PARAMETER WhatIfOnly
    Vis hvad der ville ske, uden at skrive til SharePoint.

.PARAMETER DeleteMissing
    Flyt elementer, der ikke er i filen, til papirkurven.

.PARAMETER Force
    Kun ved -Export: overskriv en eksisterende fil.

.EXAMPLE
    .\Sync-StandardTaskOperations.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -Export -Path .\StandardOps.xlsx

.EXAMPLE
    .\Sync-StandardTaskOperations.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -Import -Path .\StandardOps.xlsx -WhatIfOnly

.EXAMPLE
    .\Sync-StandardTaskOperations.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -Import -Path .\StandardOps.xlsx

.NOTES
    Kraever PnP.PowerShell og ImportExcel. ImportExcel bruger ikke Excel
    selv og installeres med:
        Install-Module ImportExcel -Scope CurrentUser
    ClientId: se MdDefaultClientId i _Common.psm1.
    Listen oprettes af Provision-StandardTaskOperations.ps1 (og ServiceNo
    af Provision-TasklistLists.ps1). Scriptet her opretter ingen kolonner.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Export,
    [switch] $Import,
    [Parameter(Mandatory = $true)][string] $Path,
    [string[]] $Plant,
    [string] $WorksheetName,
    [switch] $WhatIfOnly,
    [switch] $DeleteMissing,
    [switch] $Force,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

$LIST = 'MD_StandardTaskOperations'

# Kolonnerne i filen, i den raekkefoelge de staar. Navn og type er listens
# egne - se sharepoint/inspect/out/schema.md. De felter appen bruger
# (colVhpStdOps i BIO SAP App/App.pa.yaml) staar foerst.
$COLUMNS = @(
    @{ Name = 'OperationShortText'; Type = 'Text'   }
    @{ Name = 'WorkCenter';         Type = 'Text'   }
    @{ Name = 'ControlKey';         Type = 'Text'   }
    @{ Name = 'Work';               Type = 'Number' }
    @{ Name = 'NumberOfCapacities'; Type = 'Number' }
    @{ Name = 'VendorNo';           Type = 'Text'   }
    @{ Name = 'ServiceNo';          Type = 'Text'   }
    @{ Name = 'MaterialGroup';      Type = 'Text'   }
    @{ Name = 'Price';              Type = 'Number' }
    @{ Name = 'Currency';           Type = 'Text'   }
    @{ Name = 'CostElement';        Type = 'Number' }
    @{ Name = 'SapPlant';           Type = 'Text'   }
    @{ Name = 'WorkUnit';           Type = 'Text'   }
    @{ Name = 'DurationUnit';       Type = 'Text'   }
    @{ Name = 'ActivityType';       Type = 'Text'   }
    @{ Name = 'StandardTextKey';    Type = 'Text'   }
    @{ Name = 'CalculationKey';     Type = 'Number' }
    @{ Name = 'PercentageWork';     Type = 'Number' }
    @{ Name = 'DistributionFactor'; Type = 'Number' }
    @{ Name = 'OrderQuantity';      Type = 'Number' }
    @{ Name = 'OrderUnit';          Type = 'Text'   }
    @{ Name = 'PriceUnit';          Type = 'Number' }
    @{ Name = 'PurchasingGroup';    Type = 'Text'   }
    @{ Name = 'PurchasingOrg';      Type = 'Text'   }
)
$KEY_COLUMNS = @('ID', 'Plant', 'OperationNo')

# Bruges kun, hvis valgene ikke kan laeses fra feltet.
$DEFAULT_PLANTS = @('ASV', 'AVV', 'HEV', 'HCV', 'KYV', 'SKV', 'SMV', 'SSV')

if ($Export -eq $Import) { throw 'Angiv enten -Export eller -Import.' }
if ($Import -and $Plant) { throw '-Plant bruges kun ved -Export. Ved -Import styrer filens raekker, hvilke vaerker der roeres.' }
if ($Export -and ($WhatIfOnly -or $DeleteMissing)) { throw '-WhatIfOnly og -DeleteMissing bruges kun ved -Import.' }

if (-not (Get-Module -ListAvailable -Name ImportExcel)) {
    throw 'Modulet ImportExcel mangler. Installer det med: Install-Module ImportExcel -Scope CurrentUser'
}
Import-Module ImportExcel

$inv = [System.Globalization.CultureInfo]::InvariantCulture

# --- hjaelpere --------------------------------------------------------------

# Tom celle, tom streng og kun mellemrum er alle "ingen vaerdi".
function Test-Blank($v) {
    return ($null -eq $v) -or ([string]$v).Trim() -eq ''
}

# Tekst fra Excel: et tal, der er tastet i en tekstcelle, kommer som double.
# 186572 skal blive '186572', ikke '186572.0' eller '186.572'.
function ConvertTo-MdText($v) {
    if (Test-Blank $v) { return $null }
    if ($v -is [double] -or $v -is [int] -or $v -is [long] -or $v -is [decimal]) {
        return ([double]$v).ToString($inv)
    }
    return ([string]$v).Trim()
}

# Tal fra Excel. Er cellen tekst, accepteres baade 1.5 og 1,5 (dansk Excel).
# Returnerer $true/$false; vaerdien i $Result.
function ConvertTo-MdNumber($v, [ref]$Result) {
    $Result.Value = $null
    if (Test-Blank $v) { return $true }
    if ($v -is [double] -or $v -is [int] -or $v -is [long] -or $v -is [decimal]) {
        $Result.Value = [double]$v; return $true
    }
    $s = ([string]$v).Trim() -replace '\s', ''
    if ($s.Contains(',') -and -not $s.Contains('.')) { $s = $s.Replace(',', '.') }
    $d = 0.0
    if ([double]::TryParse($s, [System.Globalization.NumberStyles]::Float, $inv, [ref]$d)) {
        $Result.Value = $d; return $true
    }
    return $false
}

function Format-MdValue($v) {
    if ($null -eq $v) { return '(tom)' }
    if ($v -is [double]) { return $v.ToString($inv) }
    return "'$v'"
}

# Vaerdien i SharePoint, normaliseret som Excel-vaerdien, saa de kan
# sammenlignes: tal som double, tekst trimmet, tomt som $null.
function Get-MdSpValue($item, [string]$Name, [string]$Type) {
    $v = $item.FieldValues[$Name]
    if (Test-Blank $v) { return $null }
    if ($Type -eq 'Number') { return [double]$v }
    return ([string]$v).Trim()
}

function Test-MdEqual($a, $b) {
    if ($null -eq $a -and $null -eq $b) { return $true }
    if ($null -eq $a -or $null -eq $b) { return $false }
    if ($a -is [double] -and $b -is [double]) { return [math]::Abs($a - $b) -lt 1e-9 }
    return [string]::Equals([string]$a, [string]$b, [System.StringComparison]::Ordinal)
}

# --- login og listen --------------------------------------------------------

Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

Write-Host "`n=== $LIST ===" -ForegroundColor Cyan
if (-not (Get-PnPList -Identity $LIST -ErrorAction SilentlyContinue)) {
    throw "Listen $LIST findes ikke. Koer Provision-StandardTaskOperations.ps1 foerst."
}

# Valgene for Plant laeses fra feltet, saa et nyt vaerk i listen ogsaa
# kan bruges i Excel uden at rette scriptet.
$plants = @()
$pf = Get-PnPField -List $LIST -Identity 'Plant' -ErrorAction SilentlyContinue
if ($pf -and $pf.PSObject.Properties['Choices'] -and $pf.Choices) { $plants = @($pf.Choices) }
if (-not $plants.Count) { $plants = $DEFAULT_PLANTS }

# Kolonner, der ikke findes i listen (fx ServiceNo, hvis
# Provision-TasklistLists.ps1 ikke er koert), springes over med en advarsel.
$cols = @()
foreach ($c in $COLUMNS) {
    if (Get-PnPField -List $LIST -Identity $c.Name -ErrorAction SilentlyContinue) {
        $cols += $c
    } else {
        Write-Host "  ! Kolonnen $($c.Name) findes ikke i listen - springes over" -ForegroundColor Yellow
    }
}

$fieldNames = @('Title', 'Plant', 'OperationNo') + @($cols | ForEach-Object { $_.Name })
$items = @(Get-PnPListItem -List $LIST -PageSize 500 -Fields $fieldNames)
Write-Host "  $($items.Count) elementer i listen" -ForegroundColor DarkGray

# --- eksport ----------------------------------------------------------------

if ($Export) {
    if ((Test-Path $Path) -and -not $Force) {
        throw "$Path findes allerede. Brug -Force for at overskrive den - eller et andet filnavn, saa dine rettelser ikke gaar tabt."
    }
    if ((Test-Path $Path) -and $Force) { Remove-Item $Path }

    $rows = foreach ($it in $items) {
        $p = [string]$it.FieldValues['Plant']
        if ($Plant -and ($Plant -notcontains $p)) { continue }
        $o = [ordered]@{
            ID          = [int]$it.Id
            Plant       = $p
            OperationNo = $it.FieldValues['OperationNo']
        }
        foreach ($c in $cols) { $o[$c.Name] = $it.FieldValues[$c.Name] }
        [pscustomobject]$o
    }
    $rows = @($rows | Sort-Object Plant, OperationNo)

    if (-not $rows.Count) {
        Write-Host '  Ingen raekker at skrive.' -ForegroundColor Yellow
        return
    }

    # Tekstkolonner skal blive tekst. Ellers goer Excel '0' og '1004' til
    # tal - og et nummer med foranstillet nul mister nullet.
    $textCols = @('Plant') + @($cols | Where-Object { $_.Type -eq 'Text' } | ForEach-Object { $_.Name })

    $xl = @{
        Path               = $Path
        WorksheetName      = 'Operations'
        TableName          = 'StandardOps'
        AutoSize           = $true
        FreezeTopRow       = $true
        BoldTopRow         = $true
        NoNumberConversion = $textCols
    }
    $rows | Export-Excel @xl
    Write-Host "  $($rows.Count) raekker skrevet til $Path" -ForegroundColor Green
    Write-Host "`nRet i filen, gem den, og koer derefter:" -ForegroundColor Yellow
    Write-Host "  .\Sync-StandardTaskOperations.ps1 -SiteUrl `"$SiteUrl`" -Import -Path `"$Path`" -WhatIfOnly"
    Write-Host "Lad ID-kolonnen staa. Nye operationer faar en tom ID-celle."
    return
}

# --- import: laes og tjek hele filen foerst --------------------------------

if (-not (Test-Path $Path)) { throw "Finder ikke $Path" }
$xlIn = @{ Path = $Path }
if ($WorksheetName) { $xlIn.WorksheetName = $WorksheetName }
$sheet = @(Import-Excel @xlIn)
Write-Host "  $($sheet.Count) raekker i $Path" -ForegroundColor DarkGray
if (-not $sheet.Count) { throw 'Filen har ingen raekker.' }

$headers = @($sheet[0].PSObject.Properties | ForEach-Object { $_.Name })
foreach ($k in @('Plant', 'OperationNo')) {
    if ($headers -notcontains $k) { throw "Filen mangler kolonnen $k." }
}
$known = $KEY_COLUMNS + @($COLUMNS | ForEach-Object { $_.Name })
foreach ($h in $headers) {
    if ($known -notcontains $h) {
        Write-Host "  ! Kolonnen '$h' kendes ikke - ignoreres" -ForegroundColor Yellow
    }
}
# Kun kolonner, der baade er i filen og i listen, sammenlignes.
$useCols = @($cols | Where-Object { $headers -contains $_.Name })
$skipped = @($cols | Where-Object { $headers -notcontains $_.Name } | ForEach-Object { $_.Name })
if ($skipped.Count) {
    Write-Host "  Kolonner, der ikke er i filen og derfor ikke roeres: $($skipped -join ', ')" -ForegroundColor DarkGray
}
$hasId = $headers -contains 'ID'

$byId = @{}
$byKey = @{}
foreach ($it in $items) {
    $byId[[int]$it.Id] = $it
    $k = "$($it.FieldValues['Plant'])|$($it.FieldValues['OperationNo'])"
    if (-not $byKey.ContainsKey($k)) { $byKey[$k] = $it }
}

$errors = New-Object System.Collections.Generic.List[string]
$plan = New-Object System.Collections.Generic.List[object]
$keysInFile = @{}
$plantsInFile = @{}

# Trin 1: laes og tjek hver raekke for sig.
$rowNo = 1   # Excel-raekke 1 er overskriften
foreach ($r in $sheet) {
    $rowNo++
    $where = "Raekke $rowNo"

    # Helt tomme raekker (fx under tabellen) springes over.
    $allBlank = $true
    foreach ($h in $headers) { if (-not (Test-Blank $r.$h)) { $allBlank = $false; break } }
    if ($allBlank) { continue }

    $p = ConvertTo-MdText $r.Plant
    if (-not $p) { $errors.Add("${where}: Plant er tom"); continue }
    $p = $p.ToUpper()
    if ($plants -notcontains $p) { $errors.Add("${where}: Plant '$p' er ikke et valg i listen ($($plants -join ', '))"); continue }

    $op = $null
    if (-not (ConvertTo-MdNumber $r.OperationNo ([ref]$op)) -or $null -eq $op -or $op -ne [math]::Floor($op) -or $op -le 0) {
        $errors.Add("${where}: OperationNo '$($r.OperationNo)' er ikke et positivt helt tal"); continue
    }
    $op = [int]$op
    $where = "Raekke $rowNo ($p $op)"

    $key = "$p|$op"
    if ($keysInFile.ContainsKey($key)) {
        $errors.Add("${where}: $p $op staar ogsaa i raekke $($keysInFile[$key])"); continue
    }
    $keysInFile[$key] = $rowNo
    $plantsInFile[$p] = $true

    $vals = [ordered]@{}
    $bad = $false
    foreach ($c in $useCols) {
        $raw = $r.($c.Name)
        if ($c.Type -eq 'Number') {
            $n = $null
            if (-not (ConvertTo-MdNumber $raw ([ref]$n))) {
                $errors.Add("${where}: $($c.Name) '$raw' er ikke et tal"); $bad = $true; continue
            }
            $vals[$c.Name] = $n
        } else {
            $vals[$c.Name] = ConvertTo-MdText $raw
        }
    }
    if ($bad) { continue }

    $id = $null
    $idRaw = if ($hasId) { $r.ID } else { $null }
    if (-not (Test-Blank $idRaw)) {
        $idNum = $null
        if (-not (ConvertTo-MdNumber $idRaw ([ref]$idNum)) -or $idNum -ne [math]::Floor($idNum)) {
            $errors.Add("${where}: ID '$idRaw' er ikke et helt tal"); continue
        }
        $id = [int]$idNum
        if (-not $byId.ContainsKey($id)) {
            $errors.Add("${where}: ID $id findes ikke i listen. Toem ID-cellen, hvis raekken skal oprettes som ny."); continue
        }
    }

    $plan.Add([pscustomobject]@{ Row = $rowNo; Plant = $p; Op = $op; Key = $key; Vals = $vals; Id = $id; Target = $null })
}

# Trin 2: raekker MED ID rammer deres element. De goeres foerst, saa en
# omnummereret operation (30 -> 40) ikke bliver ramt af en ny raekke 30.
$targeted = @{}
foreach ($x in $plan) {
    if ($null -eq $x.Id) { continue }
    if ($targeted.ContainsKey($x.Id)) {
        $errors.Add("Raekke $($x.Row): ID $($x.Id) staar ogsaa i raekke $($targeted[$x.Id])"); continue
    }
    $targeted[$x.Id] = $x.Row
    $x.Target = $byId[$x.Id]
}

# Trin 3: raekker UDEN ID matches paa Plant + OperationNo. Er elementet
# med den noegle allerede ramt af en raekke med ID, flytter den raekke det
# vaek (ellers var noeglen dobbelt i filen), og raekken her bliver ny.
foreach ($x in $plan) {
    if ($null -ne $x.Id) { continue }
    $hit = $byKey[$x.Key]
    if ($hit -and -not $targeted.ContainsKey([int]$hit.Id)) {
        $targeted[[int]$hit.Id] = $x.Row
        $x.Target = $hit
    }
}

# En raekke med ID kan flytte et element til en noegle, som et ANDET
# element i listen har, og som filen ikke roerer. Saa ville der staa to
# ens operationer i listen.
foreach ($x in $plan) {
    if ($null -eq $x.Id) { continue }
    $other = $byKey[$x.Key]
    if ($other -and $other.Id -ne $x.Target.Id -and -not $targeted.ContainsKey([int]$other.Id)) {
        $errors.Add("Raekke $($x.Row): $($x.Plant) $($x.Op) findes allerede i listen (ID $($other.Id)), og det element er ikke i filen")
    }
}

if ($errors.Count) {
    Write-Host "`n  $($errors.Count) fejl i filen - INTET er skrevet:" -ForegroundColor Red
    foreach ($e in $errors) { Write-Host "    $e" -ForegroundColor Red }
    throw 'Ret filen og koer igen.'
}

# --- import: skriv ----------------------------------------------------------

$added = 0; $updated = 0; $same = 0; $missing = 0; $deleted = 0

Write-Host ''
foreach ($x in $plan) {
    $label = "$($x.Plant) $($x.Op)"

    if (-not $x.Target) {
        $values = @{ Title = $label; Plant = $x.Plant; OperationNo = $x.Op }
        foreach ($n in $x.Vals.Keys) { if ($null -ne $x.Vals[$n]) { $values[$n] = $x.Vals[$n] } }
        Write-Host "  + $label (ny)" -ForegroundColor Green
        if (-not $WhatIfOnly) { Add-PnPListItem -List $LIST -Values $values | Out-Null }
        $added++
        continue
    }

    $it = $x.Target
    $changes = @{}
    $lines = @()
    $oldPlant = [string]$it.FieldValues['Plant']
    $oldOp = Get-MdSpValue $it 'OperationNo' 'Number'
    if ($oldPlant -ne $x.Plant) {
        $changes['Plant'] = $x.Plant
        $lines += "Plant: '$oldPlant' -> '$($x.Plant)'"
    }
    if (-not (Test-MdEqual $oldOp ([double]$x.Op))) {
        $changes['OperationNo'] = $x.Op
        $lines += "OperationNo: $(Format-MdValue $oldOp) -> $($x.Op)"
    }
    if ([string]$it.FieldValues['Title'] -ne $label) {
        $changes['Title'] = $label
        $lines += "TaskLabel: '$($it.FieldValues['Title'])' -> '$label'"
    }
    foreach ($c in $useCols) {
        $old = Get-MdSpValue $it $c.Name $c.Type
        $new = $x.Vals[$c.Name]
        if (-not (Test-MdEqual $old $new)) {
            $changes[$c.Name] = $new
            $lines += "$($c.Name): $(Format-MdValue $old) -> $(Format-MdValue $new)"
        }
    }

    if (-not $changes.Count) { $same++; continue }
    Write-Host "  ~ $label (ID $($it.Id))" -ForegroundColor Cyan
    foreach ($l in $lines) { Write-Host "      $l" }
    if (-not $WhatIfOnly) { Set-PnPListItem -List $LIST -Identity $it.Id -Values $changes | Out-Null }
    $updated++
}

# Elementer i de vaerker, filen daekker, som ingen raekke ramte.
foreach ($it in ($items | Sort-Object { [string]$_.FieldValues['Plant'] }, { [double]$_.FieldValues['OperationNo'] })) {
    $p = [string]$it.FieldValues['Plant']
    if (-not $plantsInFile.ContainsKey($p)) { continue }
    if ($targeted.ContainsKey([int]$it.Id)) { continue }
    $label = "$p $($it.FieldValues['OperationNo'])"
    if ($DeleteMissing) {
        Write-Host "  - $label (ID $($it.Id)) til papirkurven" -ForegroundColor Magenta
        if (-not $WhatIfOnly) { Remove-PnPListItem -List $LIST -Identity $it.Id -Recycle -Force | Out-Null }
        $deleted++
    } else {
        Write-Host "  ? $label (ID $($it.Id)) er ikke i filen - roeres ikke" -ForegroundColor Yellow
        $missing++
    }
}

Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
$sum = if ($WhatIfOnly) {
    "  Ville oprette $added, opdatere $updated og slette $deleted. $same er uaendrede."
} else {
    "  Oprettet $added, opdateret $updated, slettet $deleted. $same er uaendrede."
}
Write-Host $sum -ForegroundColor Green
if ($missing) {
    Write-Host "  $missing elementer er ikke i filen og er IKKE slettet. Brug -DeleteMissing for at slette dem." -ForegroundColor Yellow
}
if ($WhatIfOnly) {
    Write-Host "`nDet var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
} elseif ($added -or $updated -or $deleted) {
    Write-Host "`nAppen laeser listen ved opstart. Genstart VH-plan appen for at se aendringerne."
}
