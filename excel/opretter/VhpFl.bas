Attribute VB_Name = "VhpFl"
Option Explicit
'==============================================================================
' VhpFl - FL-ordren (schema/fl-sap-order.schema.json): felter, klasser,
' karakteristikker, tilladelser og validering.
'
' Reglerne er SPOOL-arkets (excel/vba/spool-gui/GUI_RunCreate.bas):
'
'   klassen            tildeles, undtagen NO CLASS og SIGNAL
'   TRM                ekstra klasse, naar TRM assignment = X
'   WCM                ekstra klasse paa ELF
'   GIV_EXT            ekstra klasse paa GIV, naar GIV_EXT assignment = X
'   karakteristikker   TRM's, GIV_EXT's og klassens egne, efter tabellen
'                      Karakteristikker i Opslag (SPOOL: DictionaryTable)
'   tilladelser        Atex -> ATEX, Risiko -> Risiko, Asbestos -> ASBEST,
'                      PTW -> PTW, naar feltet er X
'
' Feltnavnene i ordren er appens: versaler (POWER [KW]). Karakteristikkerne
' paa SAP-skaermen hedder som SPOOL-kolonnerne (Power [kW]). Der sammenlignes
' uden hensyn til store og smaa bogstaver.
'
' De rene funktioner (SapDateText, IsFlDate, SplitValues, ChunkText,
' IsSpecialCharacteristic, CharacteristicSeed) bruger hverken Dictionaries
' eller VhpConfig og afproeves ogsaa i LibreOffice (VhpTest.SelfTestPure).
'==============================================================================

'==============================================================================
' Indlaesning
'==============================================================================

' Raekkerne sorteres efter RowNo, og hver faar et opslag felt -> vaerdi.
Public Sub Prepare(ByVal order As Object)
    Dim sorted As New Collection
    Dim row As Object
    Dim i As Long
    Dim placed As Boolean

    For Each row In VhpUtil.JList(order, "rows")
        BuildValueIndex row
        placed = False
        For i = 1 To sorted.Count
            If VhpUtil.JLng(row, "rowNo", 999999) < VhpUtil.JLng(sorted(i), "rowNo", 999999) Then
                sorted.Add row, Before:=i
                placed = True
                Exit For
            End If
        Next i
        If Not placed Then sorted.Add row
    Next row

    If order.Exists("rows") Then order.Remove "rows"
    order.Add "rows", sorted
End Sub

' Feltnavn (versaler) -> vaerdi. Staar et felt to gange, vinder den foerste
' udfyldte.
Private Sub BuildValueIndex(ByVal row As Object)
    Dim vals As Object
    Dim v As Object
    Dim key As String
    Dim value As String

    Set vals = VhpUtil.NewDict()
    For Each v In VhpUtil.JList(row, "values")
        key = UCase$(Trim$(VhpUtil.JStr(v, "field")))
        value = Trim$(VhpUtil.JStr(v, "value"))
        If Len(key) > 0 Then
            If Not vals.Exists(key) Then
                vals.Add key, value
            ElseIf Len(CStr(vals(key))) = 0 Then
                vals(key) = value
            End If
        End If
    Next v

    If row.Exists("_vals") Then row.Remove "_vals"
    row.Add "_vals", vals
End Sub

' Vaerdien af et felt i raekken, fx FieldValue(row, "MANUFACTURER"). Tom, hvis
' feltet ikke er udfyldt.
Public Function FieldValue(ByVal row As Object, ByVal field As String) As String
    Dim vals As Object
    If row Is Nothing Then Exit Function
    If Not row.Exists("_vals") Then BuildValueIndex row
    Set vals = row("_vals")
    field = UCase$(Trim$(field))
    If vals.Exists(field) Then FieldValue = CStr(vals(field))
End Function

Public Function RowLabel(ByVal row As Object) As String
    RowLabel = Trim$(VhpUtil.JStr(row, "functionalLocation"))
    If Len(RowLabel) = 0 Then RowLabel = VhpUtil.Dk("r{ae}kke ") & VhpUtil.JStr(row, "rowNo")
End Function

'==============================================================================
' Klasser, karakteristikker og tilladelser
'==============================================================================

Public Function ClassOf(ByVal row As Object) As String
    ClassOf = UCase$(Trim$(VhpUtil.JStr(row, "assignedClass")))
End Function

' Faar raekken en klasse i klassetildelingen? Ikke NO CLASS og SIGNAL.
Public Function HasClassAssignment(ByVal cls As String) As Boolean
    cls = UCase$(Trim$(cls))
    HasClassAssignment = (Len(cls) > 0 And cls <> FL_CLASS_NONE And cls <> FL_CLASS_SIGNAL)
End Function

Public Function WantsTrm(ByVal row As Object) As Boolean
    WantsTrm = (UCase$(FieldValue(row, FLF_TRM)) = "X")
End Function

Public Function WantsGivExt(ByVal row As Object) As Boolean
    WantsGivExt = (ClassOf(row) = "GIV" And UCase$(FieldValue(row, FLF_GIVEXT)) = "X")
End Function

' De ekstra klasser i SPOOL's raekkefoelge: TRM, WCM (ELF), GIV_EXT (GIV).
Public Function ExtraClasses(ByVal row As Object) As Collection
    Dim c As New Collection
    If WantsTrm(row) Then c.Add "TRM"
    If ClassOf(row) = "ELF" Then c.Add "WCM"
    If WantsGivExt(row) Then c.Add "GIV_EXT"
    Set ExtraClasses = c
End Function

' Karakteristik (navnet paa SAP-skaermen) -> vaerdi, kun de udfyldte. Samme
' raekkefoelge som SPOOL: TRM, GIV_EXT, klassens egne.
Public Function CharacteristicMap(ByVal row As Object, ByVal lk As Object) As Object
    Dim m As Object
    Set m = VhpUtil.NewDict()
    If WantsTrm(row) Then AddCharacteristics m, row, VhpLookup.FlCharacteristics(lk, "TRM")
    If WantsGivExt(row) Then AddCharacteristics m, row, VhpLookup.FlCharacteristics(lk, "GIV_EXT")
    If HasClassAssignment(ClassOf(row)) Then AddCharacteristics m, row, VhpLookup.FlCharacteristics(lk, ClassOf(row))
    Set CharacteristicMap = m
End Function

Private Sub AddCharacteristics(ByVal m As Object, ByVal row As Object, ByVal names As Collection)
    Dim nm As Variant
    Dim value As String
    For Each nm In names
        value = FieldValue(row, CStr(nm))
        If Len(value) > 0 And Not m.Exists(CStr(nm)) Then m.Add CStr(nm), value
    Next nm
End Sub

' Tilladelserne (Permits) i SPOOL's raekkefoelge og stavning.
Public Function Permits(ByVal row As Object) As Collection
    Dim c As New Collection
    If UCase$(FieldValue(row, FLF_ATEX)) = "X" Then c.Add "ATEX"
    If UCase$(FieldValue(row, FLF_RISIKO)) = "X" Then c.Add "Risiko"
    If UCase$(FieldValue(row, FLF_ASBESTOS)) = "X" Then c.Add "ASBEST"
    If UCase$(FieldValue(row, FLF_PTW)) = "X" Then c.Add "PTW"
    Set Permits = c
End Function

' Felter med en vaerdi, som opretteren IKKE overfoerer til SAP - fx Long text
' og dokumentfelterne. SPOOL overfoerte dem heller ikke. De vises under
' Detaljer, saa det er synligt, hvad der bliver i appen.
Public Function UnusedFields(ByVal row As Object, ByVal lk As Object) As Collection
    Dim c As New Collection
    Dim used As Object
    Dim v As Object
    Dim key As String
    Dim nm As Variant
    Dim value As String

    Set used = VhpUtil.NewDict()
    For Each nm In Array(FLF_MANUFACTURER, FLF_MODEL, FLF_PARTNO, FLF_SERIAL, FLF_ROOM, FLF_ABC, _
                         FLF_SORTFIELD, FLF_WARRANTY_START, FLF_WARRANTY_END, FLF_ATEX, FLF_RISIKO, _
                         FLF_ASBESTOS, FLF_PTW, FLF_TRM, FLF_GIVEXT, "FUNCTIONAL LOCATION", "DESCRIPTION", _
                         "STRINDICATOR", "STR. INDICATOR", "SAP STATUS", "INFO")
        MarkUsed used, CStr(nm)
    Next nm
    If ClassOf(row) = "KAB" Then MarkUsed used, FLF_SUPERIOR
    For Each nm In CharacteristicMap(row, lk).Keys
        MarkUsed used, CStr(nm)
    Next nm

    For Each v In VhpUtil.JList(row, "values")
        key = UCase$(Trim$(VhpUtil.JStr(v, "field")))
        value = Trim$(VhpUtil.JStr(v, "value"))
        If Len(key) > 0 And Len(value) > 0 And Not used.Exists(key) Then
            c.Add VhpUtil.JStr(v, "field") & " = " & value
        End If
    Next v
    Set UnusedFields = c
End Function

Private Sub MarkUsed(ByVal used As Object, ByVal nm As String)
    nm = UCase$(Trim$(nm))
    If Not used.Exists(nm) Then used.Add nm, True
End Sub

'==============================================================================
' Validering
'==============================================================================

' Resultat: Dictionary med "errors" og "warnings", som VhpOrder.Validate.
' En fejl stopper anmodningen, foer noget roeres i SAP.
Public Function Validate(ByVal order As Object, ByVal lk As Object) As Object
    Dim res As Object
    Dim req As Object
    Dim env As String
    Dim rows As Collection
    Dim row As Object
    Dim seen As Object
    Dim label As String
    Dim fl As String
    Dim desc As String
    Dim cls As String
    Dim rowStatus As String

    Set res = VhpUtil.NewDict()
    res.Add "errors", New Collection
    res.Add "warnings", New Collection
    Set Validate = res

    env = UCase$(VhpUtil.JStr(order, "environment"))
    If env <> "DEV" And env <> "TEST" And env <> "PROD" Then
        res("errors").Add VhpUtil.Dk("Ordren siger ikke, om den kommer fra DEV, TEST eller PROD (environment er '") & env & "')."
    End If

    Set req = VhpUtil.JObj(order, "request")
    If req Is Nothing Then
        res("errors").Add VhpUtil.Dk("Ordren har ingen anmodning (request).")
        Exit Function
    End If
    If Len(VhpUtil.JStr(req, "requestNo")) = 0 Then
        res("errors").Add VhpUtil.Dk("Anmodningen har intet nummer (requestNo).")
    End If

    Set rows = VhpUtil.JList(order, "rows")
    If rows.Count = 0 Then
        res("errors").Add VhpUtil.Dk("Anmodningen har ingen functional locations.")
        Exit Function
    End If

    If Not VhpLookup.FlClassKnown(lk, "TRM") Then
        res("warnings").Add VhpUtil.Dk("Tabellen Karakteristikker i Opslag har ingen r{ae}kker for TRM.")
    End If

    Set seen = VhpUtil.NewDict()
    For Each row In rows
        label = RowLabel(row)
        fl = Trim$(VhpUtil.JStr(row, "functionalLocation"))
        desc = Trim$(VhpUtil.JStr(row, "description"))
        cls = ClassOf(row)
        rowStatus = LCase$(VhpUtil.JStr(row, "rowStatus"))

        If Len(fl) = 0 Then
            res("errors").Add label & VhpUtil.Dk(": mangler functional location.")
        ElseIf Len(fl) > 40 Then
            res("errors").Add label & VhpUtil.Dk(": m{ae}rket er ") & Len(fl) & VhpUtil.Dk(" tegn. SAP har plads til 40.")
        ElseIf seen.Exists(UCase$(fl)) Then
            res("errors").Add label & VhpUtil.Dk(": st{aa}r to gange i anmodningen.")
        Else
            seen.Add UCase$(fl), True
        End If

        If Len(desc) = 0 Then
            res("errors").Add label & VhpUtil.Dk(": mangler beskrivelse.")
        ElseIf Len(desc) > 40 Then
            res("errors").Add label & VhpUtil.Dk(": beskrivelsen er ") & Len(desc) & VhpUtil.Dk(" tegn. SAP har plads til 40.")
        End If

        Select Case UCase$(Trim$(VhpUtil.JStr(row, "strIndicator")))
            Case "KKS", "KKSKV", "KKSKA", "AKS", "ROS"
            Case Else
                res("errors").Add label & VhpUtil.Dk(": mangler strukturindikator (KKS, KKSKV eller KKSKA). ") & _
                    VhpUtil.Dk("Appen har ikke kunnet genkende m{ae}rket.")
        End Select

        If Len(cls) = 0 Then
            res("errors").Add label & VhpUtil.Dk(": har ingen klasse.")
        ElseIf HasClassAssignment(cls) And Not VhpLookup.FlClassKnown(lk, cls) Then
            res("errors").Add label & VhpUtil.Dk(": klassen ") & cls & _
                VhpUtil.Dk(" st{aa}r ikke i Opslag (tabellen Karakteristikker).")
        End If

        If rowStatus = "invalid" Then
            res("errors").Add label & VhpUtil.Dk(": appen markerede r{ae}kken med en fejl: ") & VhpUtil.JStr(row, "firstIssue")
        ElseIf rowStatus = "warning" And Len(VhpUtil.JStr(row, "firstIssue")) > 0 Then
            res("warnings").Add label & VhpUtil.Dk(": appen advarede: ") & VhpUtil.JStr(row, "firstIssue")
        End If

        CheckMax res, label, "Manufacturer", FieldValue(row, FLF_MANUFACTURER), 30
        CheckMax res, label, "Model Number", FieldValue(row, FLF_MODEL), 20
        CheckMax res, label, "Manufacturer Part Number", FieldValue(row, FLF_PARTNO), 30
        CheckMax res, label, "Manufacturer Serial Number", FieldValue(row, FLF_SERIAL), 30
        CheckMax res, label, "Room", FieldValue(row, FLF_ROOM), 8
        CheckMax res, label, "Sort Field", FieldValue(row, FLF_SORTFIELD), 30

        If Not IsFlDate(FieldValue(row, FLF_WARRANTY_START)) Then
            res("errors").Add label & VhpUtil.Dk(": Warranty Start skal v{ae}re DD.MM.YYYY eller YYYYMMDD ('") & _
                FieldValue(row, FLF_WARRANTY_START) & "')."
        End If
        If Not IsFlDate(FieldValue(row, FLF_WARRANTY_END)) Then
            res("errors").Add label & VhpUtil.Dk(": Warranty End skal v{ae}re DD.MM.YYYY eller YYYYMMDD ('") & _
                FieldValue(row, FLF_WARRANTY_END) & "')."
        End If

        If Len(FieldValue(row, FLF_SUPERIOR)) > 0 And cls <> "KAB" Then
            res("warnings").Add label & VhpUtil.Dk(": Superior FL bruges kun ved KAB, som i SPOOL-arket, og overf{oe}res ikke.")
        End If
    Next row
End Function

Private Sub CheckMax(ByVal res As Object, ByVal label As String, ByVal fieldName As String, _
                     ByVal value As String, ByVal maxLen As Long)
    If Len(value) > maxLen Then
        res("errors").Add label & ": " & fieldName & VhpUtil.Dk(" er ") & Len(value) & _
            VhpUtil.Dk(" tegn. SAP har plads til ") & maxLen & "."
    End If
End Sub

'==============================================================================
' Rene funktioner (ogsaa i LibreOffice)
'==============================================================================

' Garantidatoen til SAP: DD.MM.YYYY. Appen tillader ogsaa YYYYMMDD
' (docs/31, FL34). Andet gives videre, som det er - valideringen har sagt fra.
Public Function SapDateText(ByVal s As String) As String
    s = Trim$(s)
    If Len(s) = 8 And VhpUtil.IsAllDigits(s) Then
        SapDateText = Mid$(s, 7, 2) & "." & Mid$(s, 5, 2) & "." & Left$(s, 4)
    Else
        SapDateText = s
    End If
End Function

' Tom, DD.MM.YYYY eller YYYYMMDD - og en dato, der findes.
Public Function IsFlDate(ByVal s As String) As Boolean
    Dim d As Long
    Dim mo As Long
    Dim y As Long

    s = Trim$(s)
    If Len(s) = 0 Then
        IsFlDate = True
        Exit Function
    End If

    If Len(s) = 8 And VhpUtil.IsAllDigits(s) Then
        y = CLng(Left$(s, 4))
        mo = CLng(Mid$(s, 5, 2))
        d = CLng(Right$(s, 2))
    ElseIf Len(s) = 10 And Mid$(s, 3, 1) = "." And Mid$(s, 6, 1) = "." Then
        If Not VhpUtil.IsAllDigits(Left$(s, 2) & Mid$(s, 4, 2) & Right$(s, 4)) Then Exit Function
        d = CLng(Left$(s, 2))
        mo = CLng(Mid$(s, 4, 2))
        y = CLng(Right$(s, 4))
    Else
        Exit Function
    End If

    If y < 1900 Or y > 9999 Or mo < 1 Or mo > 12 Or d < 1 Then Exit Function
    If d > Day(DateSerial(y, mo + 1, 0)) Then Exit Function
    IsFlDate = True
End Function

' Et felt med flere vaerdier: "a|b" (SPOOL's skilletegn). Tomme dele springes over.
Public Function SplitValues(ByVal s As String) As Collection
    Dim c As New Collection
    Dim parts() As String
    Dim i As Long
    Dim t As String

    parts = Split(s, "|")
    For i = LBound(parts) To UBound(parts)
        t = Trim$(parts(i))
        If Len(t) > 0 Then c.Add t
    Next i
    Set SplitValues = c
End Function

' Tekst i stykker paa hoejst n tegn (SPOOL: SplitByLength, 30 i vaerdidialogen).
Public Function ChunkText(ByVal s As String, ByVal n As Long) As Collection
    Dim c As New Collection
    Dim pos As Long

    Set ChunkText = c
    If n <= 0 Then Exit Function
    pos = 1
    Do While pos <= Len(s)
        c.Add Mid$(s, pos, n)
        pos = pos + n
    Loop
End Function

' SPOOL skriver de tre med vaerdidialogen (F4), naar der er flere vaerdier.
Public Function IsSpecialCharacteristic(ByVal nm As String) As Boolean
    Select Case LCase$(Trim$(nm))
        Case "remarks", "supply from", "safety critical equipment"
            IsSpecialCharacteristic = True
    End Select
End Function

' Tabellen Karakteristikker i Opslag, som den staar i SPOOL-arkets
' DictionaryTable: Array(klasse, felt, SAP-navn). Bruges kun til at fylde
' tabellen, naar den oprettes - derefter er det tabellen, der gaelder.
' tests/test_sap_contract.py sammenligner den med SPOOL-arket.
Public Function CharacteristicSeed() As Collection
    Dim s As String
    Dim c As New Collection
    Dim recs() As String
    Dim f() As String
    Dim i As Long

    s = s & "ELF|Full load current [A]|K0535;ELF|IP class|K1200;ELF|Power [kW]|K0430;ELF|Remarks|K0270;ELF|Supply from|K0475;ELF|Voltage [V]|K1030;"
    s = s & "GIV|IP class|K1200;GIV|Junction box|K1250;GIV|Mechanical measur. range from|K0770;GIV|Mechanical measuring range to|K0780;"
    s = s & "GIV|Mechanical measuring range uom|K0830;GIV|Operating pressure|K0400;GIV|Operating pressure uom|K0410;GIV|Operating temperature|K0370;"
    s = s & "GIV|Operating temperature uom|K0380;GIV|Output value|K1220;GIV|Output value uom|K1230;GIV|Remarks|K0270;GIV|Signal applications|K0990;"
    s = s & "GIV|Supply from|K0475;GIV|Test Method|K1430;GIV|Test Method 2|K1440;GIV|Typekredse|K1420;GIV_EXT|Other Information|K3000;GIV_EXT|Owner|K3001;"
    s = s & "KAB|Cable type|K0680;KAB|Dimension|K0320;KAB|Dimension uom|K0330;KAB|Drawn cable length [m]|K1285;KAB|From functional location|K0480;"
    s = s & "KAB|Remarks|K0270;KAB|To functional location|K1150;KAB|Voltage [V]|K1030;MKP|Remarks|K0270;MKP_AC|Close torque in Nm|K1400;"
    s = s & "MKP_AC|Drive time requirements in sec|K1390;MKP_AC|Open torque in Nm|K1410;MKP_AC|Remarks|K0270;MKP_FA|Design flow|K0060;MKP_FA|Design flow uom|K0070;"
    s = s & "MKP_FA|Design pressure|K0200;MKP_FA|Design pressure uom|K0210;MKP_FA|Design temperature|K0180;MKP_FA|Design temperature uom|K0190;MKP_FA|Medium|K0750;"
    s = s & "MKP_FA|Remarks|K0270;MKP_FI|Control class (lovpligtig)|H0930;MKP_FI|Design flow|K0060;MKP_FI|Design flow uom|K0070;MKP_FI|Design pressure|K0200;"
    s = s & "MKP_FI|Design pressure uom|K0210;MKP_FI|Design temperature|K0180;MKP_FI|Design temperature uom|K0190;MKP_FI|DN/Volume|K1095;MKP_FI|Medium|K0750;"
    s = s & "MKP_FI|Remarks|K0270;MKP_HE|Design flow|K0060;MKP_HE|Design flow uom|K0070;MKP_HE|Design press. second. side uom|K0250;"
    s = s & "MKP_HE|Design pressure prim. side uom|K0230;MKP_HE|Design pressure primary side|K0220;MKP_HE|Design pressure secondary side|K0240;"
    s = s & "MKP_HE|Design temp. primary side|K0140;MKP_HE|Design temp. primary side uom|K0150;MKP_HE|Design temp. second. side uom|K0170;"
    s = s & "MKP_HE|Design temp. secondary side|K0160;MKP_HE|Medium|K0750;MKP_HE|Primary medium|K0950;MKP_HE|Remarks|K0270;MKP_HE|Secondary medium|K0760;"
    s = s & "MKP_PI|Control class (lovpligtig)|H0930;MKP_PI|Design pressure|K0200;MKP_PI|Design pressure uom|K0210;MKP_PI|Design temperature|K0180;"
    s = s & "MKP_PI|Design temperature uom|K0190;MKP_PI|DN/Volume|K1095;MKP_PI|Medium|K0750;MKP_PI|Remarks|K0270;MKP_PU|Design flow|K0060;"
    s = s & "MKP_PU|Design flow uom|K0070;MKP_PU|Design lifting height|K0080;MKP_PU|Design lifting height uom|K0090;MKP_PU|Design pressure|K0200;"
    s = s & "MKP_PU|Design pressure uom|K0210;MKP_PU|Design temperature|K0180;MKP_PU|Design temperature uom|K0190;MKP_PU|Medium|K0750;MKP_PU|Remarks|K0270;"
    s = s & "MKP_TA|Control class (lovpligtig)|H0930;MKP_TA|Design pressure|K0200;MKP_TA|Design pressure uom|K0210;MKP_TA|Design temperature|K0180;"
    s = s & "MKP_TA|Design temperature uom|K0190;MKP_TA|DN/Volume|K1095;MKP_TA|Medium|K0750;MKP_TA|Remarks|K0270;MKP_VA|Design flow|K0060;"
    s = s & "MKP_VA|Design flow uom|K0070;MKP_VA|Design pressure|K0200;MKP_VA|Design pressure uom|K0210;MKP_VA|Design temperature|K0180;"
    s = s & "MKP_VA|Design temperature uom|K0190;MKP_VA|DN/Volume|K1095;MKP_VA|Medium|K0750;MKP_VA|Remarks|K0270;MAA|Design pressure|K0200;"
    s = s & "MAA|Design pressure uom|K0210;MAA|Design temperature|K0180;MAA|Design temperature uom|K0190;MAA|Medium|K0750;MAA|Remarks|K0270;"
    s = s & "RBR|Design pos cold|K0120;RBR|Design pos warm|K0130;RBR|Direction of movement|K0030;RBR|Remarks|K0270;RBR|Setting cold vertical [kN]|K0590;"
    s = s & "RBR|Setting cold vertical [mm]|K0600;RBR|Setting warm vertical [kN]|K0610;RBR|Setting warm vertical [mm]|K0620;TAF|Consumer FL|K0020;"
    s = s & "TAF|Nominel current, compartment|K1100;TAF|Remarks|K0270;TAF|Voltage [V]|K1030;TRM|EX-Marking|EX;TRM|Fire Classification|FIRE;"
    s = s & "TRM|Fire Sealing Product|FIRESEALPRO;TRM|Fire Sealing Type|FIRESEAL;TRM|Safety Critical Equipment|SCEQ;UNF|Remarks|K0270;"
    s = s & "WCM|Switching location|CONTROL;"

    recs = Split(s, ";")
    For i = LBound(recs) To UBound(recs)
        If Len(recs(i)) > 0 Then
            f = Split(recs(i), "|")
            c.Add Array(f(0), f(1), f(2))
        End If
    Next i
    Set CharacteristicSeed = c
End Function
