<#
.SYNOPSIS
    Slaar de seks "<VAERK> Standard Tasklist" sammen til een liste,
    MD_StandardTaskOperations, med rigtige kolonnenavne.

.DESCRIPTION
    De seks lister har 42 af 42 identiske kolonner (AVV har een tom rest,
    Test1). De er oprettet med "opret liste fra Excel", saa de interne navne
    er field_1 ... field_36, og visningsnavnene er SAP's egne overskrifter
    fra IA01 - heriblandt "Un.", "Uni.", "Int. distr" og een kolonne, der
    hedder "/".

    Af de 36 er 13 TOMME i alle 176 raekker paa tvaers af de seks lister.
    De tages ikke med. De 23 med indhold faar rigtige navne, og SAP's egen
    overskrift gemmes som kolonnens beskrivelse, saa oversaettelsen kan
    efterproeves - nogle af dem er min tolkning af en SAP-forkortelse.

    OPERATIONSNUMMERET ligger i Title (10, 20, 30, ...), ikke i field_1
    (SOp), som er tom overalt. Hver af de seks lister er EEN arbejdsplan
    med een sekvens.

    De seks lister roeres ikke. De bliver staaende, til den gamle app er
    slukket. Se docs/10-datamodel-forslag.md 4 og 7.

    Idempotent: en raekke med samme Plant + OperationNo springes over.

.EXAMPLE
    .\Provision-StandardTaskOperations.ps1 -SiteUrl "https://..." -WhatIfOnly

.EXAMPLE
    .\Provision-StandardTaskOperations.ps1 -SiteUrl "https://..." -Migrate

.NOTES
    Kraever PnP.PowerShell. ClientId findes i tenanten:
        se MdDefaultClientId i _Common.psm1
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [switch] $Migrate,
    [switch] $WhatIfOnly,
    [string] $ClientId = $env:PNP_CLIENT_ID
)

$ErrorActionPreference = 'Stop'

$TARGET = 'MD_StandardTaskOperations'

# Kildeliste -> vaerkskode. Vaerket staar kun i listens NAVN, ikke i raekkerne.
$SOURCES = [ordered]@{
    'ASV Standard Tasklist' = 'ASV'
    'AVV Standard Tasklist' = 'AVV'
    'HEV Standard Tasklist' = 'HEV'
    'KYV Standard Tasklist' = 'KYV'
    'SKV Standard Tasklist' = 'SKV'
    'SSV Standard Tasklist' = 'SSV'
}

# field_N -> nyt navn, type, SAP-overskrift (gemmes som beskrivelse).
#
# De ni oeverste bruger appen. Resten er SAP-felter, der fulgte med
# eksporten; de tages med, fordi de har indhold, og fordi det er
# uigenkaldeligt at smide dem vaek.
#
# Navnene paa 'No.', 'Calc', 'Pct', 'Fac' og '/' er min tolkning af SAP's
# forkortelser. Derfor staar originalen i beskrivelsen.
$MAP = @(
    @{ From='field_2';  To='WorkCenter';         Type='Text';   Sap='Work Ctr';             Trim=$true }
    @{ From='field_4';  To='ControlKey';         Type='Text';   Sap='Ctrl';                 Trim=$true }
    @{ From='field_5';  To='OperationShortText'; Type='Text';   Sap='Operation short text'; Trim=$true }
    @{ From='field_6';  To='Work';               Type='Number'; Sap='Work' }
    @{ From='field_7';  To='WorkUnit';           Type='Text';   Sap='Un.';                  Trim=$true }
    @{ From='field_10'; To='DurationUnit';       Type='Text';   Sap='Uni.';                 Trim=$true }
    @{ From='field_15'; To='ActivityType';       Type='Text';   Sap='ActTyp';               Trim=$true }
    @{ From='field_16'; To='StandardTextKey';    Type='Text';   Sap='StTextKy';             Trim=$true }
    @{ From='field_3';  To='SapPlant';           Type='Text';   Sap='Plnt' }

    @{ From='field_8';  To='NumberOfCapacities'; Type='Number'; Sap='No.' }
    @{ From='field_11'; To='CalculationKey';     Type='Number'; Sap='Calc' }
    @{ From='field_12'; To='PercentageWork';     Type='Number'; Sap='Pct' }
    @{ From='field_14'; To='DistributionFactor'; Type='Number'; Sap='Fac' }
    @{ From='field_26'; To='OrderQuantity';      Type='Number'; Sap='OrdQuantity' }
    @{ From='field_27'; To='OrderUnit';          Type='Text';   Sap='Unit';                 Trim=$true }
    @{ From='field_28'; To='Price';              Type='Number'; Sap='Price' }
    @{ From='field_29'; To='Currency';           Type='Text';   Sap='Crcy';                 Trim=$true }
    @{ From='field_30'; To='PriceUnit';          Type='Number'; Sap='/' }
    @{ From='field_32'; To='CostElement';        Type='Number'; Sap='Cost elem.' }
    @{ From='field_33'; To='MaterialGroup';      Type='Text';   Sap='Matl Group';           Trim=$true }
    @{ From='field_34'; To='PurchasingGroup';    Type='Text';   Sap='PGr';                  Trim=$true }
    @{ From='field_35'; To='VendorNo';           Type='Text';   Sap='Vendor';               Trim=$true }
    @{ From='field_36'; To='PurchasingOrg';      Type='Text';   Sap='POrg';                 Trim=$true }
)

# Login og de faelles hjaelpefunktioner (REVIEW.md E8).
Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId
Set-MdWhatIf $WhatIfOnly

# ---------------------------------------------------------------------------
Write-Host "`n=== $TARGET ===" -ForegroundColor Cyan

# Listen og kolonnerne gaar gennem _Common.psm1 (toerloeb: Set-MdWhatIf).
New-MdList $TARGET 'Standardoperationer pr. vaerk. Erstatter de seks "<VAERK> Standard Tasklist".'

if (-not $WhatIfOnly) {
    Set-PnPField -List $TARGET -Identity 'Title' -Values @{ Title = 'TaskLabel' }
}

# Vaerket er det, alt filtreres paa. Derfor indekseret.
New-MdField $TARGET 'Plant' Choice -Choices 'ASV','AVV','HEV','HCV','KYV','SKV','SMV','SSV' -Indexed `
    -Description 'Vaerkskode. Kommer fra navnet paa kildelisten.'
New-MdField $TARGET 'OperationNo' Number -Indexed `
    -Description 'SAP-operationsnummer: 10, 20, 30. Laa i Title i kildelisterne - field_1 (SOp) var tom overalt.'

foreach ($m in $MAP) {
    New-MdField $TARGET $m.To $m.Type -Description "SAP: $($m.Sap)  (var $($m.From) i kildelisten)"
}

# ---------------------------------------------------------------------------
if ($Migrate) {
    Write-Host "`n=== Migrerer ===" -ForegroundColor Cyan

    $seen = @{}
    if (-not $WhatIfOnly) {
        foreach ($it in (Get-PnPListItem -List $TARGET -PageSize 500)) {
            $seen["$($it.FieldValues.Plant)|$($it.FieldValues.OperationNo)"] = $true
        }
    }

    $added = 0; $skipped = 0; $noop = 0
    foreach ($src in $SOURCES.Keys) {
        $plant = $SOURCES[$src]
        if (-not (Get-PnPList -Identity $src -ErrorAction SilentlyContinue)) {
            Write-Host "  ! Kildelisten '$src' findes ikke - springes over" -ForegroundColor Yellow
            continue
        }
        $rows = Get-PnPListItem -List $src -PageSize 500
        $n = 0
        foreach ($r in $rows) {
            $fv = $r.FieldValues

            # Operationsnummeret ligger i Title. Er det ikke et tal, er
            # raekken ikke en operation - spring den over frem for at gaette.
            $opNo = 0
            if (-not [int]::TryParse([string]$fv.Title, [ref]$opNo)) {
                Write-Host "    ! $src ID $($r.Id): Title '$($fv.Title)' er ikke et tal - springes over" -ForegroundColor Yellow
                $noop++; continue
            }

            if ($seen.ContainsKey("$plant|$opNo")) { $skipped++; continue }

            $vals = @{ Plant = $plant; OperationNo = $opNo }
            foreach ($m in $MAP) {
                $v = $fv[$m.From]
                if ($null -eq $v -or "$v" -eq '') { continue }
                # SAP-eksporten er polstret med mellemrum: 'SSVAP   '.
                # Utrimmet matcher opslag ikke.
                if ($m.Trim) { $v = ([string]$v).Trim() }
                if ("$v" -eq '') { continue }
                $vals[$m.To] = $v
            }
            $vals['Title'] = "$plant $opNo"

            if (-not $WhatIfOnly) {
                Add-PnPListItem -List $TARGET -Values $vals | Out-Null
            }
            $seen["$plant|$opNo"] = $true
            $added++; $n++
        }
        Write-Host ("  {0,-24} {1,3} raekker" -f $src, $n) -ForegroundColor Green
    }

    $verb = if ($WhatIfOnly) { 'ville oprette' } else { 'oprettet' }
    Write-Host "`n  $verb $added raekker" -ForegroundColor Green
    if ($skipped) { Write-Host "  $skipped fandtes i forvejen" -ForegroundColor DarkGray }
    if ($noop)    { Write-Host "  $noop raekker uden gyldigt operationsnummer" -ForegroundColor Yellow }
}

# ---------------------------------------------------------------------------
Write-Host "`nFaerdig.`n" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Write-Host "Det var et toerloeb. Koer uden -WhatIfOnly for at gennemfoere." -ForegroundColor Yellow
} elseif (-not $Migrate) {
    Write-Host "Listen er oprettet, men TOM. Koer igen med -Migrate." -ForegroundColor Yellow
} else {
    Write-Host "De seks kildelister er UROERT. Slet dem foerst, naar den gamle"
    Write-Host "app er slukket - se docs/10-datamodel-forslag.md 7."
}
