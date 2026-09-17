Attribute VB_Name = "modEnvironment"
Option Explicit

' ===========================================================================
' Miljoevalg: SharePoint-site og SAP-system
' ===========================================================================
' Regnearket arbejder i to miljoeer, og de haenger sammen paa tvaers af tre
' systemer:
'
'     Power Apps   BioEnergy Solution DEV   BioEnergy Solution PROD
'     SharePoint   BioSapDEV                BioSap
'     SAP          GQ1 Quality              GP1 Production
'
' VAELGEREN FANDTES ALLEREDE, MEN KUN TIL HALVDELEN
' -------------------------------------------------
' Setup!D3 har hele tiden styret SAP-systemet - GetSystemPrefix laeser den.
' Setup har ogsaa celler til SharePoint-URL'erne (D6-D9), men
' modSharePointImport holdt op med at bruge dem og lagde i stedet
' konstanter i koden. Kommentaren der sagde det selv:
'
'     ' Code-based config (ingen Setup-ark afhaengighed)
'
' Det er derfor GUI-delen kan skifte miljoe, og SharePoint-delen ikke kan.
' Her foeres afhaengigheden tilbage - og de fire URL'er REGNES UD af site
' plus listenavn i stedet for at staa som fire celler, der kan drive fra
' hinanden.
'
' DEN KOMBINATION DER IKKE MAA FINDES
' ------------------------------------
' De to akser giver fire par. Tre er i orden:
'
'     DEV  + GQ1   test
'     PROD + GP1   drift
'     PROD + GQ1   toerproeve - rigtige planer, oprettet i testsystemet
'
' Det fjerde er ikke:
'
'     DEV  + GP1   TESTDATA OPRETTET I PRODUKTIONS-SAP
'
' Den spaerres haardt. Ikke en advarsel man kan klikke forbi - der er ingen
' opgave, hvor den er den rigtige, og konsekvensen kan ikke rulles tilbage
' fra Excel.
' ===========================================================================

Public Const ENV_DEV As String = "DEV"
Public Const ENV_PROD As String = "PROD"

Private Const SITE_DEV As String = "https://orsted.sharepoint.com/teams/BioSAPDEV"
Private Const SITE_PROD As String = "https://orsted.sharepoint.com/teams/BioSAP"

Private Const SAP_PREFIX_PROD As String = "GP1"
Private Const SAP_PREFIX_DEV As String = "GQ1"

' Setup!F3, med etiketten i F2 - samme moenster som "SAP Client" i D2 og
' vaerdien i D3. Kolonne D er optaget hele vejen ned: D2/D3 er SAP-systemet,
' og D5-D13 er reserveret i Constants.bas til flow-URL og SharePoint-celler,
' selv om de staar tomme i dag. Kolonne F er fri paa hele arket.
Public Const SETUP_ENVIRONMENT_ROW As Long = 3
Public Const SETUP_ENVIRONMENT_COL As Long = 6

Private Const STAMP_PREFIX As String = "EnvStamp_"

' Saettes af BeginEnvironmentRun, saa StartExtract ikke spoerger to gange -
' een gang for sig selv og een gang for den sync, den selv kalder til sidst.
' Spaerren mod DEV+GP1 gaelder uanset dette flag.
Private mRunConfirmed As Boolean


' --- miljoeet -------------------------------------------------------------

' Adressen staar eet sted. Flytter cellen sig, flytter beskederne med.
Public Function EnvironmentCellAddress() As String
    EnvironmentCellAddress = WS_SETUP & "!" & _
        ThisWorkbook.Worksheets(WS_SETUP) _
            .Cells(SETUP_ENVIRONMENT_ROW, SETUP_ENVIRONMENT_COL) _
            .Address(False, False)
End Function

Public Function SapCellAddress() As String
    SapCellAddress = WS_SETUP & "!" & _
        ThisWorkbook.Worksheets(WS_SETUP) _
            .Cells(SETUP_SYSTEM_ROW, SETUP_SYSTEM_COL) _
            .Address(False, False)
End Function

Public Function GetEnvironment() As String
    Dim raw As String
    raw = UCase$(Trim$(CStr(ThisWorkbook.Worksheets(WS_SETUP).Cells(SETUP_ENVIRONMENT_ROW, SETUP_ENVIRONMENT_COL).value)))

    Select Case raw
        Case ENV_DEV, ENV_PROD
            GetEnvironment = raw
        Case vbNullString
            ' Tom celle er IKKE det samme som DEV. Et tomt felt, der stille
            ' blev laest som "det ufarlige", er praecis den slags antagelse,
            ' der en dag rammer det forkerte miljoe.
            Err.Raise 3001, "modEnvironment", _
                "Miljoeet er ikke valgt. Saet " & EnvironmentCellAddress() & _
                " til " & ENV_DEV & " eller " & ENV_PROD & "."
        Case Else
            Err.Raise 3002, "modEnvironment", _
                "Ukendt miljoe '" & raw & "' i " & EnvironmentCellAddress() & _
                ". Gyldige vaerdier: " & ENV_DEV & ", " & ENV_PROD & "."
    End Select
End Function

Public Function GetSiteUrl() As String
    If GetEnvironment() = ENV_PROD Then
        GetSiteUrl = SITE_PROD
    Else
        GetSiteUrl = SITE_DEV
    End If
End Function

' Een kilde til de fire liste-URL'er. De kan ikke laengere pege hver sin vej.
Public Function GetListUrl(ByVal listTitle As String) As String
    GetListUrl = GetSiteUrl() & "/_api/web/lists/getbytitle('" & listTitle & "')/items"
End Function

' SAP-systemet staar i Setup!D3 og kan overstyres, saa PROD+GQ1 er mulig.
' Er cellen tom, foelger den miljoeet.
Public Function GetSapPrefix() As String
    Dim raw As String
    raw = UCase$(Trim$(CStr(ThisWorkbook.Worksheets(WS_SETUP).Cells(SETUP_SYSTEM_ROW, SETUP_SYSTEM_COL).value)))

    If raw = SAP_PREFIX_PROD Or raw = SAP_PREFIX_DEV Then
        GetSapPrefix = raw
    ElseIf GetEnvironment() = ENV_PROD Then
        GetSapPrefix = SAP_PREFIX_PROD
    Else
        GetSapPrefix = SAP_PREFIX_DEV
    End If
End Function

Public Function DescribeEnvironment() As String
    DescribeEnvironment = "SharePoint " & GetEnvironment() & _
        " (" & SiteShortName() & ")  -  SAP " & GetSapPrefix()
End Function

Private Function SiteShortName() As String
    Dim url As String
    url = GetSiteUrl()
    SiteShortName = Mid$(url, InStrRev(url, "/") + 1)
End Function


' --- spaerren -------------------------------------------------------------

' Kaldes foer ENHVER handling, der aendrer noget uden for regnearket.
' actionText bruges i bekraeftelsen, saa brugeren kan se HVAD der sker, og
' ikke bare at noget sker.
Public Function AssertEnvironmentSafe(ByVal actionText As String) As Boolean
    Dim env As String
    Dim sap As String

    ' GetEnvironment kaster, hvis D2 er tom eller ukendt. Den skal ende som
    ' en besked og et False - ikke som en ubehandlet fejl i StartExtract,
    ' der jo foerst saetter sin egen fejlhaandtering bagefter.
    On Error GoTo Fail

    env = GetEnvironment()
    sap = GetSapPrefix()

    ' Den forbudte kombination. Ingen vej udenom.
    If env = ENV_DEV And sap = SAP_PREFIX_PROD Then
        MsgBox _
            "Spaerret." & vbCrLf & vbCrLf & _
            "Data er hentet fra SharePoint " & ENV_DEV & ", men SAP staar paa " & _
            SAP_PREFIX_PROD & " (Production)." & vbCrLf & vbCrLf & _
            "Testdata maa ikke oprettes i produktions-SAP." & vbCrLf & vbCrLf & _
            "Skift enten miljoeet til " & ENV_PROD & " i " & EnvironmentCellAddress() & _
            ", eller SAP-systemet til " & SAP_PREFIX_DEV & " i " & SapCellAddress() & ".", _
            vbCritical + vbOKOnly, "Forkert miljoekombination"
        AssertEnvironmentSafe = False
        Exit Function
    End If

    ' Er den allerede bekraeftet for denne koersel, spoerges der ikke igen.
    If mRunConfirmed Then
        AssertEnvironmentSafe = True
        Exit Function
    End If

    ' Produktion spoerger. De oevrige kombinationer koerer uden dialog -
    ' en bekraeftelse, man ser hver gang, holder man op med at laese.
    If env = ENV_PROD Or sap = SAP_PREFIX_PROD Then
        If MsgBox( _
            actionText & vbCrLf & vbCrLf & _
            DescribeEnvironment() & vbCrLf & vbCrLf & _
            "Fortsaet?", _
            vbExclamation + vbYesNo + vbDefaultButton2, "Produktion") <> vbYes Then
            AssertEnvironmentSafe = False
            Exit Function
        End If
    End If

    AssertEnvironmentSafe = True
    Exit Function

Fail:
    MsgBox Err.Description, vbCritical + vbOKOnly, "Miljoeet kan ikke afgoeres"
    AssertEnvironmentSafe = False
End Function


' --- stempling ------------------------------------------------------------

' Uden stemplet er der intet, der forhindrer: hent fra DEV, skift til PROD,
' opret. Arket ser ens ud i begge tilfaelde.
'
' Stemplet ligger som et defineret navn og ikke i en celle, saa fanernes
' layout er uroert - importkoden regner med bestemte raekker og kolonner.

Public Sub StampSheetEnvironment(ByVal ws As Worksheet)
    StampSheetAs ws, GetEnvironment()
End Sub

Public Sub StampSheetAs(ByVal ws As Worksheet, ByVal env As String)
    On Error Resume Next
    ThisWorkbook.Names.Add _
        Name:=STAMP_PREFIX & ws.CodeName, _
        RefersTo:="=""" & UCase$(Trim$(env)) & "|" & Format$(Now, "yyyy-mm-dd hh:nn") & """", _
        Visible:=False
    On Error GoTo 0
End Sub

Public Function GetSheetEnvironment(ByVal ws As Worksheet) As String
    Dim nm As Name
    Dim raw As String

    On Error Resume Next
    Set nm = ThisWorkbook.Names(STAMP_PREFIX & ws.CodeName)
    On Error GoTo 0

    If nm Is Nothing Then Exit Function

    raw = nm.RefersTo
    raw = Replace$(Replace$(raw, "=", ""), """", "")
    If InStr(raw, "|") > 0 Then raw = Left$(raw, InStr(raw, "|") - 1)

    GetSheetEnvironment = UCase$(Trim$(raw))
End Function

' True naar arket maa bruges. Et ustemplet ark slipper igennem - saa er
' regnearket lige blevet bygget om, og der er ikke noget at modsige.
Public Function AssertSheetMatchesEnvironment(ByVal ws As Worksheet) As Boolean
    Dim stamped As String
    Dim current As String

    On Error GoTo Fail

    stamped = GetSheetEnvironment(ws)
    current = GetEnvironment()

    If Len(stamped) = 0 Then
        AssertSheetMatchesEnvironment = True
        Exit Function
    End If

    If stamped = current Then
        AssertSheetMatchesEnvironment = True
        Exit Function
    End If

    MsgBox _
        "Arket '" & ws.Name & "' indeholder data hentet fra " & stamped & "," & vbCrLf & _
        "men miljoeet staar nu paa " & current & "." & vbCrLf & vbCrLf & _
        "Hent data igen, eller skift tilbage til " & stamped & ".", _
        vbCritical + vbOKOnly, "Data og miljoe stemmer ikke"

    AssertSheetMatchesEnvironment = False
    Exit Function

Fail:
    MsgBox Err.Description, vbCritical + vbOKOnly, "Miljoeet kan ikke afgoeres"
    AssertSheetMatchesEnvironment = False
End Function


Public Sub BeginEnvironmentRun()
    mRunConfirmed = True
End Sub

Public Sub EndEnvironmentRun()
    mRunConfirmed = False
End Sub


' --- arkene ---------------------------------------------------------------

' De ark, der indeholder data hentet fra SharePoint. Object_list er afledt
' af Maintenance_Items og foelger med.
Private Function DataSheetNames() As Variant
    DataSheetNames = Array( _
        WS_MAINTENANCE_PLANS, _
        WS_MAINTENANCE_ITEMS, _
        WS_MAINTENANCE_TLH, _
        WS_MAINTENANCE_TL, _
        WS_OBJECT_LIST)
End Function

Private Function TryGetSheet(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set TryGetSheet = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
End Function

Public Sub StampDataSheetsAs(ByVal env As String)
    Dim names As Variant
    Dim i As Long
    Dim ws As Worksheet

    names = DataSheetNames()
    For i = LBound(names) To UBound(names)
        Set ws = TryGetSheet(CStr(names(i)))
        If Not ws Is Nothing Then StampSheetAs ws, env
        Set ws = Nothing
    Next i
End Sub

' False saa snart eet ark baerer et andet miljoe end det valgte. Det er
' scenariet: hent fra DEV, skift til PROD, opret - hvor arket ser ens ud.
Public Function AssertDataSheetsMatchEnvironment() As Boolean
    Dim names As Variant
    Dim i As Long
    Dim ws As Worksheet

    names = DataSheetNames()
    For i = LBound(names) To UBound(names)
        Set ws = TryGetSheet(CStr(names(i)))
        If Not ws Is Nothing Then
            If Not AssertSheetMatchesEnvironment(ws) Then
                AssertDataSheetsMatchEnvironment = False
                Exit Function
            End If
        End If
        Set ws = Nothing
    Next i

    AssertDataSheetsMatchEnvironment = True
End Function


' --- opsaetning -----------------------------------------------------------

' Koeres een gang. Miljoecellen findes ikke i det regneark, der ligger i dag
' - SAP-systemet har vaeret det eneste valg. Den her skriver etiketten,
' laegger en rulleliste paa cellen og saetter en startvaerdi, saa den ikke
' staar tom (og GetEnvironment dermed fejler) foerste gang.
Public Sub SetupEnvironmentCell(Optional ByVal defaultEnvironment As String = ENV_DEV)
    Dim ws As Worksheet
    Dim envCell As Range
    Dim labelCell As Range

    On Error GoTo Failed

    Set ws = ThisWorkbook.Worksheets(WS_SETUP)
    Set envCell = ws.Cells(SETUP_ENVIRONMENT_ROW, SETUP_ENVIRONMENT_COL)
    Set labelCell = ws.Cells(SETUP_ENVIRONMENT_ROW - 1, SETUP_ENVIRONMENT_COL)

    If Len(Trim$(CStr(labelCell.value))) = 0 Then
        labelCell.value = "SharePoint site"
    End If

    ' Rullelisten er en bekvemmelighed. Er arket beskyttet, saa den ikke kan
    ' laegges paa, er valget stadig gyldigt - GetEnvironment laeser cellen og
    ' afviser selv alt andet end DEV og PROD.
    On Error Resume Next
    envCell.Validation.Delete
    envCell.Validation.Add _
        Type:=xlValidateList, _
        AlertStyle:=xlValidAlertStop, _
        Operator:=xlBetween, _
        Formula1:=ENV_DEV & "," & ENV_PROD
    envCell.Validation.InputTitle = "Miljoe"
    envCell.Validation.InputMessage = _
        ENV_DEV & " henter fra BioSapDEV, " & ENV_PROD & " henter fra BioSap."
    On Error GoTo Failed

    If Len(Trim$(CStr(envCell.value))) = 0 Then
        envCell.value = UCase$(Trim$(defaultEnvironment))
    End If

    ' Det, der allerede ligger i arkene, er hentet med de gamle hardkodede
    ' URL'er - og de pegede alle fire paa BioSap. Arkene stemples derfor som
    ' PROD, uanset hvad der lige er valgt i D2. Stempler man dem som det nye
    ' valg, paastaar man noget om data, man ikke ved.
    StampDataSheetsAs ENV_PROD

    MsgBox _
        EnvironmentCellAddress() & " er klar." & vbCrLf & vbCrLf & _
        DescribeEnvironment() & vbCrLf & vbCrLf & _
        "Arkene er markeret som " & ENV_PROD & ", fordi de er hentet fra BioSap" & vbCrLf & _
        "med den gamle kode. Hent data igen, foer der oprettes noget.", _
        vbInformation + vbOKOnly, "Miljoevalg"
    Exit Sub

Failed:
    ' Adressen slaas ikke op her. Naar vi er havnet i en fejlhaandtering,
    ' er det maaske netop Setup-arket, der ikke kunne naas.
    MsgBox "Kunne ikke saette miljoecellen: " & Err.Description, _
        vbCritical + vbOKOnly, "Miljoevalg"
End Sub
