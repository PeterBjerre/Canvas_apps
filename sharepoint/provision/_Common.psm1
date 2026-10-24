<#
.SYNOPSIS
    Faelles hjaelpefunktioner til provisioneringsscripterne.

.DESCRIPTION
    New-MdList stod fire gange, New-MdField i tre udgaver, og app-id'et
    til login ti steder (REVIEW.md E8). Nu staar de her:

        Import-Module (Join-Path $PSScriptRoot '_Common.psm1') -Force
        Connect-MdSite -SiteUrl $SiteUrl -ClientId $ClientId

    Scripterne KALDER stadig New-MdList/New-MdField med listen og kolonnen
    som foerste argumenter - tools/check_datasources.py laeser kaldene og
    ved derfor, hvilke lister og kolonner provisioneringen opretter.

    Toerloeb: Set-MdWhatIf $WhatIfOnly lige efter Connect-MdSite (R2-060).

    Filen skal vaere ren ASCII med BOM (tools/check_ps1.py).
#>

# PnP.PowerShell 2.x har ingen faelles app-registrering, saa -Interactive
# KRAEVER et ClientId. Uden et fejler MSAL med "User canceled
# authentication" - hvilket lyder som om brugeren trykkede fortryd, men
# ikke er det. Appen nedenfor findes i tenanten. Et client id er ikke en
# hemmelighed; det er et navn, ikke en noegle - se docs/08-datamapning.md 6B.
$MdDefaultClientId = '9bc3ab49-b65d-410a-85ad-de819febfddc'

function Connect-MdSite {
    param(
        [Parameter(Mandatory = $true)][string] $SiteUrl,
        [string] $ClientId,
        [switch] $DeviceLogin
    )
    if (-not $ClientId) { $ClientId = $MdDefaultClientId }
    $conn = @{ Url = $SiteUrl; ClientId = $ClientId }
    if ($DeviceLogin) { $conn.DeviceLogin = $true } else { $conn.Interactive = $true }
    try {
        Connect-PnPOnline @conn
    }
    catch {
        Write-Host ""
        Write-Host "Login mislykkedes: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "'User canceled authentication' betyder EN af to ting:" -ForegroundColor Yellow
        Write-Host "  1. Browservinduet blev lukket, foer login var faerdigt."
        Write-Host "  2. Appen $ClientId er ikke godkendt i tenanten, saa"
        Write-Host "     browseren viste 'Needs admin approval' i stedet for et login."
        Write-Host ""
        Write-Host "Har du en anden app-registrering, saa giv den med -ClientId <app id>." -ForegroundColor Yellow
        Write-Host "Har du ingen, kan du oprette en:" -ForegroundColor Yellow
        Write-Host "  Register-PnPEntraIDAppForInteractiveLogin -ApplicationName 'PnP Masterdata' -Tenant <tenant>.onmicrosoft.com -Interactive"
        throw
    }
}

# ---------------------------------------------------------------------------
# TOERLOEB (-WhatIfOnly, R2-060)
#
# Hvert script tager [switch] $WhatIfOnly og kalder lige efter
# Connect-MdSite:
#
#     Set-MdWhatIf $WhatIfOnly
#
# Saa skriver hjaelperne nedenfor kun "? ville ..." og roerer intet. Det,
# scriptet selv skriver (seed, visninger, rettigheder), pakkes i
# if (-not $WhatIfOnly) { ... } - eller spoerger Test-MdWhatIf.
#
# Foer stod -WhatIfOnly i 7 af 16 scripts, og selv der oprettede
# New-MdList/New-MdField lister og kolonner, fordi hjaelperne ikke kendte
# parameteren. Et toerloeb, der skriver, er vaerre end intet toerloeb.
# ---------------------------------------------------------------------------
$script:MdWhatIf = $false

function Set-MdWhatIf {
    param([bool]$On)
    $script:MdWhatIf = $On
    if ($On) {
        Write-Host "TOERLOEB (-WhatIfOnly): intet skrives til SharePoint." -ForegroundColor Yellow
    }
}

function Test-MdWhatIf { return $script:MdWhatIf }

# Findes listen? I et toerloeb er en ny liste ikke oprettet endnu, og
# Get-PnPField paa en liste, der ikke findes, fejler i stedet for at svare
# tomt. Derfor spoerges der foerst.
function Test-MdList {
    param([string]$Title)
    return [bool](Get-PnPList -Identity $Title -ErrorAction SilentlyContinue)
}

function New-MdList {
    param([string]$Title, [string]$Description)
    if (Test-MdList $Title) {
        Write-Host "  = Liste '$Title' findes allerede" -ForegroundColor DarkGray
        if ($Description -and -not $script:MdWhatIf) {
            Set-PnPList -Identity $Title -Description $Description | Out-Null
        }
        return
    }
    if ($script:MdWhatIf) {
        Write-Host "  ? ville oprette listen '$Title'" -ForegroundColor Yellow
        return
    }
    New-PnPList -Title $Title -Template GenericList -OnQuickLaunch:$false | Out-Null
    if ($Description) { Set-PnPList -Identity $Title -Description $Description | Out-Null }
    Write-Host "  + Liste '$Title' oprettet" -ForegroundColor Green
}

function New-MdField {
    param(
        [string]$List, [string]$Name, [string]$Type,
        [string[]]$Choices, [switch]$Indexed, [switch]$Required, [switch]$Unique,
        [string]$Description
    )
    if ($script:MdWhatIf -and -not (Test-MdList $List)) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    }
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if ($f -and $Choices) {
        # Feltet findes: tilfoej de valg, der mangler (R2-012). Listerne fra
        # foer et nyt valg (fx RowStatus 'draft', issue #204) fik det ellers
        # aldrig. Eksisterende valg og deres raekkefoelge beholdes; nye
        # saettes bagefter. Se Set-MdChoices nedenfor.
        $current = Get-MdChoices $f
        $missing = [string[]]@($Choices | Where-Object { $current -notcontains $_ })
        if (-not $missing.Count) {
            Write-Host "    = $Name" -ForegroundColor DarkGray
        } elseif ($script:MdWhatIf) {
            Write-Host "    ? ville tilfoeje valg paa ${Name}: $($missing -join ', ')" -ForegroundColor Yellow
        } else {
            Set-MdChoices $List $Name ([string[]]($current + $missing))
            Write-Host "    ~ $Name (choices +$($missing -join ', +'))" -ForegroundColor Green
        }
    } elseif ($f) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
    } elseif ($script:MdWhatIf) {
        Write-Host "    ? ville oprette $Name ($Type)" -ForegroundColor Yellow
        return
    } else {
        $p = @{ List = $List; DisplayName = $Name; InternalName = $Name; Type = $Type }
        if ($Choices) { $p.Choices = $Choices }
        Add-PnPField @p -AddToDefaultView | Out-Null
        # Beskrivelsen saettes kun ved oprettelsen; en beskrivelse, nogen
        # har rettet i SharePoint, overskrives ikke.
        if ($Description) { Set-PnPField -List $List -Identity $Name -Values @{ Description = $Description } }
        Write-Host "    + $Name ($Type)" -ForegroundColor Green
    }
    # Unikhed kraever indeksering, og indekseringen skal vaere paa plads FOER
    # listen passerer 5.000 elementer.
    $values = @{}
    if (($Indexed -or $Unique) -and -not ($f -and $f.Indexed)) { $values.Indexed = $true }
    if ($Required -and -not ($f -and $f.Required))             { $values.Required = $true }
    if ($Unique -and -not ($f -and $f.EnforceUniqueValues))    { $values.EnforceUniqueValues = $true }
    if (-not $values.Count) { return }
    if ($script:MdWhatIf) {
        Write-Host "    ? ville saette $($values.Keys -join ', ') paa $Name" -ForegroundColor Yellow
        return
    }
    # Indeksering foerst - EnforceUniqueValues kraever, at den er der.
    $needUnique = $values.ContainsKey('EnforceUniqueValues')
    $values.Remove('EnforceUniqueValues')
    if ($values.Count) { Set-PnPField -List $List -Identity $Name -Values $values }
    if ($needUnique) {
        Set-PnPField -List $List -Identity $Name -Values @{ EnforceUniqueValues = $true }
    }
}

# ---------------------------------------------------------------------------
# VALG PAA EN EKSISTERENDE CHOICE-KOLONNE
#
# Foer blev Choices sat direkte med Set-PnPField -Values. Det virker ikke
# paa alle PnP-versioner: Get-PnPField/Set-PnPField arbejder paa den
# generelle Field og ikke FieldChoice, saa egenskaben 'Choices' findes
# ikke. PnP skriver en gul advarsel ("No property 'Choices' found ... will
# be ignored"), scriptet fortsaetter og skriver groent "~ RowStatus
# (choices +draft)" - og intet er aendret. Det var grunden til, at
# EquipmentItems/MaterialItems.RowStatus blev ved med at mangle 'draft',
# uanset hvor mange gange scriptet blev koert.
#
# Nu rettes valgene i kolonnens SchemaXml, som findes paa ALLE felttyper,
# og bagefter LAESES kolonnen igen. Mangler et valg stadig, stopper
# scriptet med en roed fejl i stedet for at melde succes.
# ---------------------------------------------------------------------------
function Get-MdChoices {
    param($Field)
    # Get-PnPField henter ikke .Choices - kun SchemaXml.
    return [string[]]@(([xml]$Field.SchemaXml).Field.CHOICES.CHOICE | Where-Object { $_ })
}

function Set-MdChoices {
    # Saetter kolonnens valg til PRAECIS $Choices i den raekkefoelge. Kalderen
    # bestemmer, om eksisterende valg skal med (det skal de naesten altid).
    param([string]$List, [string]$Name, [string[]]$Choices)
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction Stop
    $xml = [xml]$f.SchemaXml
    $node = $xml.Field.SelectSingleNode('CHOICES')
    if (-not $node) {
        $node = $xml.CreateElement('CHOICES')
        [void]$xml.Field.AppendChild($node)
    }
    $node.RemoveAll()
    foreach ($c in $Choices) {
        $e = $xml.CreateElement('CHOICE')
        $e.InnerText = $c
        [void]$node.AppendChild($e)
    }
    Set-PnPField -List $List -Identity $Name -Values @{ SchemaXml = $xml.OuterXml }

    $after = Get-MdChoices (Get-PnPField -List $List -Identity $Name -ErrorAction Stop)
    $still = @($Choices | Where-Object { $after -notcontains $_ })
    if ($still.Count) {
        throw "Valgene paa $List.$Name blev IKKE opdateret - mangler stadig: $($still -join ', '). Nu: $($after -join ', ')"
    }
}

# Flerlinjet tekst som REN tekst. Rich text ville lade SharePoint saette
# HTML-tags ind i JSON'en, og saa kan hverken appen, flowet eller SAP's
# langtekstfelt laese den.
function New-MdNoteField {
    param([string]$List, [string]$Name, [int]$Lines = 6, [string]$Description, [switch]$Indexed)
    if ($script:MdWhatIf -and -not (Test-MdList $List)) {
        Write-Host "    ? ville oprette $Name (Note, plain)" -ForegroundColor Yellow
        return
    }
    if (Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue) {
        Write-Host "    = $Name" -ForegroundColor DarkGray
        if ($script:MdWhatIf) { return }
    } elseif ($script:MdWhatIf) {
        Write-Host "    ? ville oprette $Name (Note, plain)" -ForegroundColor Yellow
        return
    } else {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name -Type Note -AddToDefaultView | Out-Null
        if ($Description) { Set-PnPField -List $List -Identity $Name -Values @{ Description = $Description } }
        Write-Host "    + $Name (Note, plain)" -ForegroundColor Green
    }
    Set-PnPField -List $List -Identity $Name -Values @{ RichText = $false; NumberOfLines = $Lines }
}

# Title doebes om, saa listen er laesbar for dem, der aabner den direkte.
# Power Fx binder paa VISNINGSNAVNET.
function Rename-MdTitle {
    param([string]$List, [string]$NewName)
    if ($script:MdWhatIf) {
        Write-Host "    ? ville omdoebe Title -> $NewName (og indeksere)" -ForegroundColor Yellow
        return
    }
    Set-PnPField -List $List -Identity 'Title' -Values @{ Title = $NewName; Indexed = $true }
    Write-Host "    ~ Title -> $NewName" -ForegroundColor Green
}

# Indeksering af en kolonne, der findes i forvejen. Et filter paa en
# kolonne uden indeks fejler, naar listen passerer 5.000 elementer.
# -WhatIfOnly paa kaldet virker stadig, men Set-MdWhatIf er nok.
function Set-MdIndexed {
    param([string]$List, [string]$Name, [switch]$WhatIfOnly)
    if ($script:MdWhatIf -and -not (Test-MdList $List)) {
        Write-Host "    ? $List findes ikke endnu - $Name ville blive indekseret" -ForegroundColor Yellow
        return
    }
    $f = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if (-not $f) {
        Write-Host "    ! $List.$Name findes ikke - springes over" -ForegroundColor Yellow
    } elseif ($f.Indexed) {
        Write-Host "    = $List.$Name er indekseret" -ForegroundColor DarkGray
    } elseif ($WhatIfOnly -or $script:MdWhatIf) {
        Write-Host "    ? $List.$Name ville blive indekseret" -ForegroundColor Yellow
    } else {
        Set-PnPField -List $List -Identity $Name -Values @{ Indexed = $true }
        Write-Host "    + $List.$Name indekseret" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# RETTIGHEDER PAA EN LISTE (R2-024, R2-032)
#
# Samme moenster som Issue Board (Provision-IssueBoard.ps1): nedarvningen
# brydes med en KOPI af sitets rettigheder, og saa justeres grupperne. En
# person, der var tilfoejet direkte paa sitet, kopieres med og fjernes ikke
# - scriptet fjerner ingen personer.
# ---------------------------------------------------------------------------

# Rollernes navne er sprogafhaengige (Read/Laese ...). Typen er ikke.
function Get-MdRoleName {
    param([string]$Kind)
    $r = Get-PnPRoleDefinition | Where-Object { $_.RoleTypeKind -eq $Kind } | Select-Object -First 1
    if (-not $r) { throw "Finder ingen rolle af typen $Kind paa sitet." }
    return $r.Name
}

function Test-MdUniquePermissions {
    param([string]$List)
    $l = Get-PnPList -Identity $List -Includes HasUniqueRoleAssignments
    return [bool]$l.HasUniqueRoleAssignments
}

# Fjerner HELE gruppens rolletildeling paa listen (alle roller).
function Remove-MdGroupFromList {
    param([string]$List, $Group)
    if (-not $Group) { return }
    $l = Get-PnPList -Identity $List -Includes RoleAssignments
    $ctx = Get-PnPContext
    try {
        $ra = $l.RoleAssignments.GetByPrincipalId($Group.Id)
        $ctx.Load($ra)
        $ra.DeleteObject()
        Invoke-PnPQuery
        Write-Host "    - $($Group.Title) har ikke laengere adgang" -ForegroundColor Green
    }
    catch {
        Write-Host "    = $($Group.Title) havde ingen adgang" -ForegroundColor DarkGray
    }
}

function Set-MdOwnersAndFlow {
    param([string]$List, [string]$FlowAccount)
    $full = Get-MdRoleName 'Administrator'
    $owners = Get-PnPGroup -AssociatedOwnerGroup
    Set-PnPListPermission -Identity $List -Group $owners -AddRole $full | Out-Null
    Write-Host "    + $($owners.Title) har Full Control" -ForegroundColor Green
    if ($FlowAccount) {
        Set-PnPListPermission -Identity $List -User $FlowAccount -AddRole $full | Out-Null
        Write-Host "    + $FlowAccount har Full Control" -ForegroundColor Green
    }
}

# Alle LAESER, kun ejerne og flowets konto skriver. Til lister, der styrer
# rettigheder (UserAndGroups, MD_Approver ...): med Contribute kunne enhver
# bruger goere sig selv til admin eller godkender.
function Set-MdReadOnlyList {
    param([string]$List, [string]$FlowAccount)
    if (-not (Test-MdList $List)) {
        Write-Host "    ! $List findes ikke - springes over" -ForegroundColor Yellow
        return
    }
    if ($script:MdWhatIf) {
        Write-Host "    ? ville goere $List skrivebeskyttet: Members Read, Owners$(if ($FlowAccount) { ' + ' + $FlowAccount }) Full Control" -ForegroundColor Yellow
        return
    }
    if (-not (Test-MdUniquePermissions $List)) {
        Set-PnPList -Identity $List -BreakRoleInheritance -CopyRoleAssignments | Out-Null
        Write-Host "    ~ nedarvning brudt (kopieret)" -ForegroundColor Green
    }
    $members = Get-PnPGroup -AssociatedMemberGroup
    Remove-MdGroupFromList $List $members
    Set-PnPListPermission -Identity $List -Group $members -AddRole (Get-MdRoleName 'Reader') | Out-Null
    Write-Host "    ~ $($members.Title) kan kun laese" -ForegroundColor Green
    Set-MdOwnersAndFlow $List $FlowAccount
}

# Alle laeser alt og opretter selv; hver retter kun SINE EGNE raekker
# ("Create and Edit access: Create items and edit items that were created
# by the user"). Ejerne og flowets konto (Full Control = Manage Lists)
# er ikke bundet af det.
function Set-MdOwnItemsList {
    param([string]$List, [string]$FlowAccount)
    if (-not (Test-MdList $List)) {
        Write-Host "    ! $List findes ikke - springes over" -ForegroundColor Yellow
        return
    }
    if ($script:MdWhatIf) {
        Write-Host "    ? ville give Members Contribute med 'kun egne raekker' paa $List, Owners$(if ($FlowAccount) { ' + ' + $FlowAccount }) Full Control" -ForegroundColor Yellow
        return
    }
    if (-not (Test-MdUniquePermissions $List)) {
        Set-PnPList -Identity $List -BreakRoleInheritance -CopyRoleAssignments | Out-Null
        Write-Host "    ~ nedarvning brudt (kopieret)" -ForegroundColor Green
    }
    $members = Get-PnPGroup -AssociatedMemberGroup
    Remove-MdGroupFromList $List $members
    Set-PnPListPermission -Identity $List -Group $members -AddRole (Get-MdRoleName 'Contributor') | Out-Null
    Write-Host "    ~ $($members.Title) har Contribute" -ForegroundColor Green
    Set-MdOwnersAndFlow $List $FlowAccount
    # 1 = Read all items, 2 = Create items and edit items that were created by the user.
    Set-PnPList -Identity $List -ReadSecurity 1 -WriteSecurity 2 | Out-Null
    Write-Host "    ~ Read access: All items / Create and Edit access: Own items" -ForegroundColor Green
}

Export-ModuleMember -Function Connect-MdSite, Set-MdWhatIf, Test-MdWhatIf, Test-MdList,
    New-MdList, New-MdField, New-MdNoteField, Get-MdChoices, Set-MdChoices, Rename-MdTitle, Set-MdIndexed,
    Get-MdRoleName, Test-MdUniquePermissions, Remove-MdGroupFromList,
    Set-MdReadOnlyList, Set-MdOwnItemsList -Variable MdDefaultClientId
