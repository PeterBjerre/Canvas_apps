<#
.SYNOPSIS
    Bygger "SAP Opretter.xlsm" ud af modulerne i denne mappe. Version 1.0
    hed "VH-plan Opretter.xlsm"; -From tager gerne den gamle fil.

.DESCRIPTION
    Opretteren er kildekode (*.bas) i git. Projektmappen er et produkt af
    den og committes ikke. Scriptet:

      1. aabner Excel usynligt,
      2. tager en ny projektmappe - eller den, der gives med -From, saa
         arkene Opslag og Indstillinger og deres data bliver,
      3. fjerner de gamle Vhp*-moduler og JsonConverter og importerer
         modulerne herfra,
      4. koerer VhpUi.SetupQuiet (ark, tabeller, knapper),
      5. gemmer som .xlsm.

    Kraever Excel og at "Tillid til adgang til VBA-projektobjektmodellen" er
    slaaet til: Filer > Indstillinger > Center for sikkerhed og
    rettighedsadministration > Indstillinger for Center for sikkerhed og
    rettighedsadministration > Makroindstillinger. Den kan slaas fra igen
    bagefter.

.PARAMETER OutFile
    Standard: SAP Opretter.xlsm i denne mappe.

.PARAMETER From
    En eksisterende Opretter-projektmappe, der skal have nye moduler.
    Opslag og Indstillinger beholdes, som de er.

.EXAMPLE
    .\Build-Opretter.ps1

.EXAMPLE
    .\Build-Opretter.ps1 -From "C:\Users\pkbje\Oersted\BioSAP - SAP-oprettelse\VH-plan Opretter.xlsm" -OutFile "C:\Users\pkbje\Oersted\BioSAP - SAP-oprettelse\SAP Opretter.xlsm"
#>

[CmdletBinding()]
param(
    [string] $OutFile = (Join-Path $PSScriptRoot 'SAP Opretter.xlsm'),
    [string] $From
)

$ErrorActionPreference = 'Stop'
$modules = Get-ChildItem -Path $PSScriptRoot -Filter '*.bas' | Sort-Object Name
if (-not $modules) { throw "Fandt ingen .bas-filer i $PSScriptRoot" }

# VBA-editoren vil have CRLF. En fil hentet fra GitHub i browseren kan have LF.
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('vhp-build-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
foreach ($m in $modules) {
    $text = [IO.File]::ReadAllText($m.FullName)
    $text = $text -replace "`r`n", "`n" -replace "`n", "`r`n"
    [IO.File]::WriteAllText((Join-Path $tmp $m.Name), $text, [Text.Encoding]::ASCII)
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
    if ($From) {
        $wb = $excel.Workbooks.Open((Resolve-Path $From).Path)
    } else {
        $wb = $excel.Workbooks.Add()
    }

    try {
        $vbp = $wb.VBProject
        $null = $vbp.VBComponents.Count
    } catch {
        throw "Excel giver ikke adgang til VBA-projektet. Slaa 'Tillid til adgang til VBA-projektobjektmodellen' til (se Get-Help .\Build-Opretter.ps1)."
    }

    foreach ($c in @($vbp.VBComponents)) {
        if ($c.Type -eq 1 -and ($c.Name -like 'Vhp*' -or $c.Name -eq 'JsonConverter')) {
            $vbp.VBComponents.Remove($c)
        }
    }
    foreach ($m in $modules) {
        $null = $vbp.VBComponents.Import((Join-Path $tmp $m.Name))
        Write-Host "  + $($m.BaseName)" -ForegroundColor Green
    }

    $excel.Run("'" + $wb.Name + "'!SetupQuiet")

    if ($From -and ((Resolve-Path $From).Path -eq [IO.Path]::GetFullPath($OutFile))) {
        $wb.Save()
    } else {
        $wb.SaveAs([IO.Path]::GetFullPath($OutFile), 52)   # 52 = .xlsm
    }
    $wb.Close($false)
    Write-Host "Bygget: $OutFile" -ForegroundColor Cyan
    Write-Host "Aabn den, udfyld arket Opslag, og tryk Selvtest i arket Indstillinger." -ForegroundColor Cyan
}
finally {
    $excel.Quit()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
