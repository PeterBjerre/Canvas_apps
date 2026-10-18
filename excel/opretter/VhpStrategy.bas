Attribute VB_Name = "VhpStrategy"
Option Explicit
'==============================================================================
' VhpStrategy - strategiplaner (planer med en vedligeholdsstrategi, IP42).
'
' En strategiplan oprettes som en plan med een cyklus, med fire forskelle:
'
'   IA05  arbejdsplanens hoved faar strategien, og hver operation knyttes
'         til sine pakker (operationens packagesKey, fx ";1;3;") i
'         pakkeoversigten. Det er Export_Script.bas' ExportTasklistMaintPackages
'         vendt om: samme knap (btnTEXT_DRUCKTASTE_WP), samme tabel
'         (tblSAPLCPDITCTRL_3600) og samme afkrydsningsfelter
'         (chkRIHSTRAT-MARKnn i kolonne nn + 2).
'   IP04  positionen faar strategien (RMIPM-WSTRA, som Export_Script.bas
'         laeser i IP06's hoved).
'   IP01  planen oprettes med strategien i stedet for en cyklus. Startdatoen
'         er foerste forfald minus den korteste pakke, operationerne bruger.
'
' Kun tidsstrategier (pakker i DAY, WK, MON, YR). En taellerstrategi (H, D,
' COUNT) skal have et maalepunkt paa planen, og det er ikke klar endnu:
' valideringen stopper den.
'
' Felterne, der kun findes paa en strategiplans skaerme, findes paa NAVN
' (FindByName) og ikke paa den fulde sti: stien afhaenger af, hvilke
' underbilleder SAP viser for strategien, og den kendes ikke fra et script,
' der har koert. Navnene er SAP's feltnavne (RMIPM-STADT osv.). Stierne,
' der er kendt, staar i VhpConfig under STRATEGIPLANER - med en note om,
' hvilke der er bekraeftet.
'
' Plankategori, kaldshorisont, planlaegningsperiode og sorteringsfelt er som
' for en plan med een cyklus. Mangler appens kaldshorisont, beholdes den,
' SAP foreslaar fra strategien (IP11).
'==============================================================================

' Feltnavne paa strategiplanens skaerme (til FindByName).
Private Const FN_TL_STRATEGY As String = "PLKOD-STRAT"
Private Const FN_ITEM_STRATEGY As String = "RMIPM-WSTRA"
Private Const FN_PLAN_TEXT As String = "RMIPM-WPTXT"
Private Const FN_ITEM_LINK As String = "ITEM_LINK"
Private Const FN_HORIZON As String = "RMIPM-HORIZ"
Private Const FN_HORIZON_QUALIFIER As String = "RMIPM-HORIZ_QUALIFIER"
Private Const FN_SCHED_PERIOD As String = "RMIPM-ABRHO"
Private Const FN_SCHED_UNIT As String = "RMIPM-HUNIT"
Private Const FN_START_DATE As String = "RMIPM-STADT"
Private Const FN_SORT_FIELD As String = "RMIPM-PLAN_SORT"

'==============================================================================
' Ordren
'==============================================================================

Public Function IsStrategyOrder(ByVal order As Object) As Boolean
    IsStrategyOrder = Len(StrategyKey(order)) > 0
End Function

Public Function StrategyKey(ByVal order As Object) As String
    StrategyKey = Trim$(VhpUtil.JStr(VhpUtil.JObj(order, "plan"), "strategyKey"))
End Function

' Pakkenumrene i en operations packagesKey: ";1;3;" -> 1, 3. Tal, der ikke
' er tal, springes over (valideringen siger det).
Public Function PackageNos(ByVal op As Object) As Collection
    Dim parts As Variant
    Dim i As Long
    Dim s As String
    Dim res As New Collection

    parts = Split(VhpUtil.JStr(op, "packagesKey"), ";")
    For i = LBound(parts) To UBound(parts)
        s = Trim$(CStr(parts(i)))
        If Len(s) > 0 Then
            If VhpUtil.IsAllDigits(s) Then res.Add CLng(s)
        End If
    Next i
    Set PackageNos = res
End Function

' Pakken med nummeret fra ordrens strategyPackages (MD_StrategyPackage).
Public Function Package(ByVal order As Object, ByVal packageNo As Long) As Object
    Dim p As Object
    For Each p In VhpUtil.JList(order, "strategyPackages")
        If VhpUtil.JLng(p, "packageNo", -1) = packageNo Then
            Set Package = p
            Exit Function
        End If
    Next p
End Function

' TIME, COUNTER eller "" for en pakkes enhed. D er taellerdage ("166 Counter
' Days") - ikke DAY.
Public Function UnitKind(ByVal unitText As String) As String
    Select Case UCase$(Trim$(unitText))
        Case "DAY", "WK", "MON", "YR"
            UnitKind = "TIME"
        Case "H", "D", "COUNT"
            UnitKind = "COUNTER"
    End Select
End Function

' TIME, COUNTER, MIXED eller "" for de pakker, ordrens operationer bruger.
Public Function PlanKind(ByVal order As Object) As String
    Dim op As Object
    Dim n As Variant
    Dim p As Object
    Dim k As String
    Dim res As String

    For Each op In VhpUtil.JList(order, "operations")
        For Each n In PackageNos(op)
            Set p = Package(order, CLng(n))
            If Not p Is Nothing Then
                k = UnitKind(VhpUtil.JStr(p, "cycleUnit"))
                If Len(k) > 0 Then
                    If Len(res) = 0 Then
                        res = k
                    ElseIf res <> k Then
                        PlanKind = "MIXED"
                        Exit Function
                    End If
                End If
            End If
        Next n
    Next op
    PlanKind = res
End Function

' Den korteste tidspakke, operationerne bruger. Nothing, hvis ingen.
Public Function FirstTimePackage(ByVal order As Object) As Object
    Dim op As Object
    Dim n As Variant
    Dim p As Object
    Dim best As Object
    Dim bestDays As Double
    Dim d As Double

    For Each op In VhpUtil.JList(order, "operations")
        For Each n In PackageNos(op)
            Set p = Package(order, CLng(n))
            If Not p Is Nothing Then
                If UnitKind(VhpUtil.JStr(p, "cycleUnit")) = "TIME" Then
                    d = ApproxDays(VhpUtil.JNum(p, "cycleLength"), VhpUtil.JStr(p, "cycleUnit"))
                    If d > 0 And (best Is Nothing Or d < bestDays) Then
                        Set best = p
                        bestDays = d
                    End If
                End If
            End If
        Next n
    Next op
    Set FirstTimePackage = best
End Function

Private Function ApproxDays(ByVal length As Double, ByVal unitText As String) As Double
    Select Case UCase$(Trim$(unitText))
        Case "DAY": ApproxDays = length
        Case "WK": ApproxDays = length * 7
        Case "MON": ApproxDays = length * 30.4
        Case "YR": ApproxDays = length * 365
    End Select
End Function

' Startdatoen i SAP: foerste forfald minus den korteste tidspakke (SAP
' regner foerste kald som start + den pakke). Samme regel som
' VhpMap.StartDate for en plan med een cyklus.
Public Function StartDate(ByVal order As Object, ByVal firstDue As Date) As Date
    Dim p As Object
    Set p = FirstTimePackage(order)
    If p Is Nothing Then
        StartDate = firstDue
    Else
        StartDate = VhpMap.StartDate(firstDue, VhpUtil.JNum(p, "cycleLength"), VhpUtil.JStr(p, "cycleUnit"))
    End If
End Function

' "1 (6M, 6 MON), 2 (D, 166 D)" til Detaljer og bekraeftelsen.
Public Function PackageText(ByVal order As Object, ByVal op As Object) As String
    Dim n As Variant
    Dim p As Object
    Dim s As String
    For Each n In PackageNos(op)
        Set p = Package(order, CLng(n))
        s = s & IIf(Len(s) > 0, ", ", "") & CStr(n)
        If Not p Is Nothing Then
            s = s & " (" & VhpUtil.JStr(p, "shortCode") & ", " & VhpUtil.JStr(p, "cycleLength") & " " & _
                VhpUtil.JStr(p, "cycleUnit") & ")"
        End If
    Next n
    PackageText = s
End Function

'==============================================================================
' IA05 - strategi paa hovedet og operationerne paa pakkerne
'==============================================================================

' Paa arbejdsplanens hoved, foer operationsoversigten. Uden strategien har
' arbejdsplanen ingen pakkeoversigt.
Public Sub SetTaskListStrategy(ByVal sess As Object, ByVal ctx As Object, ByVal what As String)
    Dim id As String
    id = FieldId(sess, IA05_HDR_STRATEGY, FN_TL_STRATEGY, "GuiCTextField")
    If Len(id) = 0 Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": arbejdsplanens hoved har intet strategifelt (") & _
            FN_TL_STRATEGY & ") [" & VhpSap.ScreenInfo(sess) & "]."
    End If
    VhpSap.SetText sess, id, CStr(ctx("strategyKey"))
End Sub

' Fra operationsoversigten: aabn pakkeoversigten og saet krydserne.
' Raekkerne staar i den raekkefoelge, operationerne blev tastet (VhpOrder.
' Operations); kortteksten paa raekken tjekkes, saa et kryds aldrig havner
' paa en anden operation. Skaermen bliver staaende paa pakkeoversigten, saa
' den kan ses igennem, foer der gemmes.
Public Sub AssignPackages(ByVal sess As Object, ByVal item As Object, ByVal ctx As Object, _
                          ByVal what As String)
    Dim op As Object
    Dim row As Long
    Dim vis As Long
    Dim n As Variant
    Dim cellId As String
    Dim shown As String
    Dim want As String
    Dim opWhat As String

    VhpSap.Press sess, IA05_BTN_PACKAGES
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (pakkeoversigt)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (pakkeoversigt)")
    If Not VhpSap.Exists(sess, IA05_PKG_TABLE) Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": SAP {aa}bnede ikke pakkeoversigten [") & _
            VhpSap.ScreenInfo(sess) & "]. " & VhpSap.StatusText(sess)
    End If

    row = 0
    For Each op In VhpOrder.Operations(item)
        opWhat = what & " " & VhpOrder.OpLabel(op)
        vis = VisiblePackageRow(sess, row, what)

        shown = Trim$(SafeText(sess, IA05_PKG_TABLE & "/" & IA05_PKG_COL_SHORTTEXT & vis & "]"))
        want = Trim$(VhpUtil.Clip(VhpUtil.JStr(op, "shortText"), 40))
        If StrComp(shown, want, vbTextCompare) <> 0 Then
            Err.Raise ERR_SAP, "VhpStrategy", opWhat & VhpUtil.Dk(": r{ae}kke ") & (row + 1) & _
                VhpUtil.Dk(" i pakkeoversigten er '") & shown & VhpUtil.Dk("', ikke '") & want & "'."
        End If

        For Each n In PackageNos(op)
            cellId = PackageCell(sess, CLng(n), vis)
            If Len(cellId) = 0 Then
                Err.Raise ERR_SAP, "VhpStrategy", opWhat & VhpUtil.Dk(": pakke ") & CStr(n) & _
                    VhpUtil.Dk(" findes ikke i pakkeoversigten for strategi ") & CStr(ctx("strategyKey")) & _
                    VhpUtil.Dk(". Se strategien i IP12.")
            End If
            VhpSap.SetChecked sess, cellId, True
        Next n
        row = row + 1
    Next op

    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (pakker)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (pakker)")
End Sub

' Pakke nr. n er kolonne n + 2 (efter Op., SOp og kortteksten). Export_Script
' kender begge stavemaader af feltet: MARK01 og MARK1.
Private Function PackageCell(ByVal sess As Object, ByVal packageNo As Long, ByVal vis As Long) As String
    Dim pos As String
    Dim id As String

    pos = "[" & CStr(packageNo + 2) & "," & CStr(vis) & "]"
    id = IA05_PKG_TABLE & "/" & IA05_PKG_COL_MARK & Format$(packageNo, "00") & pos
    If VhpSap.Exists(sess, id) Then
        PackageCell = id
        Exit Function
    End If
    id = IA05_PKG_TABLE & "/" & IA05_PKG_COL_MARK & CStr(packageNo) & pos
    If VhpSap.Exists(sess, id) Then PackageCell = id
End Function

' Som VhpSteps' VisibleOperationRow, for pakkeoversigten.
Private Function VisiblePackageRow(ByVal sess As Object, ByVal rowIndex As Long, ByVal what As String) As Long
    Dim tbl As Object
    Dim pos As Long
    Dim visibleRows As Long

    Set tbl = VhpSap.Fnd(sess, IA05_PKG_TABLE)
    visibleRows = tbl.VisibleRowCount
    pos = tbl.VerticalScrollbar.Position

    If rowIndex >= pos And rowIndex < pos + visibleRows Then
        VisiblePackageRow = rowIndex - pos
        Exit Function
    End If

    tbl.VerticalScrollbar.Position = rowIndex
    Set tbl = VhpSap.Fnd(sess, IA05_PKG_TABLE)
    pos = tbl.VerticalScrollbar.Position
    If rowIndex < pos Or rowIndex >= pos + visibleRows Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": kunne ikke rulle til operation nr. ") & (rowIndex + 1) & _
            VhpUtil.Dk(" i pakkeoversigten. G{oe}r SAP-vinduet st{oe}rre, og k{oe}r planen igen.")
    End If
    VisiblePackageRow = rowIndex - pos
End Function

'==============================================================================
' IP04 - strategien paa positionen
'==============================================================================

' Efter indgangsbilledet. Positionen skal have planens strategi, ellers kan
' den ikke knyttes til planen.
Public Sub SetItemStrategy(ByVal sess As Object, ByVal ctx As Object, ByVal what As String)
    Dim id As String
    Dim key As String

    key = CStr(ctx("strategyKey"))
    id = FieldId(sess, IP04_STRATEGY, FN_ITEM_STRATEGY, "GuiCTextField")
    If Len(id) = 0 Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": positionen har intet strategifelt (") & _
            FN_ITEM_STRATEGY & ") [" & VhpSap.ScreenInfo(sess) & "]."
    End If
    If StrComp(Trim$(VhpSap.GetText(sess, id)), key, vbTextCompare) <> 0 Then
        VhpSap.SetText sess, id, key
        VhpSap.Enter sess
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (strategi)")
        VhpSap.FailOnError sess, what & VhpUtil.Dk(" (strategi)")
    End If
End Sub

'==============================================================================
' IP01 - strategiplanen
'==============================================================================
Public Function CreatePlan(ByVal sess As Object, ByVal order As Object, ByVal itemNos As Collection, _
                           ByVal ctx As Object) As String
    Dim plan As Object
    Dim what As String
    Dim title As String
    Dim key As String
    Dim kind As String
    Dim firstDue As Date
    Dim startText As String
    Dim hz As Object
    Dim firstPkg As Object
    Dim sortText As String
    Dim id As String
    Dim j As Long
    Dim summary As String

    Set plan = VhpUtil.JObj(order, "plan")
    what = "IP01 " & VhpUtil.JStr(plan, "planId")
    title = VhpUtil.Clip(VhpUtil.JStr(plan, "title"), 40)
    key = StrategyKey(order)
    kind = PlanKind(order)

    ' Valideringen har stoppet alt andet end tidsstrategier.
    If kind <> "TIME" Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": strategi ") & key & _
            VhpUtil.Dk(" er ikke en tidsstrategi. Opretteren kan kun tidsstrategier endnu.")
    End If
    If Not VhpUtil.TryParseYmd(VhpUtil.JStr(plan, "plannedDate"), firstDue) Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": ugyldig dato for f{oe}rste forfald.")
    End If
    startText = VhpMap.SapDate(StartDate(order, firstDue))

    ' Appens kaldshorisont, ellers Opslag for den korteste tidspakke, ellers
    ' det, SAP foreslaar fra strategien.
    Set firstPkg = FirstTimePackage(order)
    If firstPkg Is Nothing Then
        Set hz = VhpOrder.PlanHorizon(plan, ctx("lookups"), 0, "")
    Else
        Set hz = VhpOrder.PlanHorizon(plan, ctx("lookups"), VhpUtil.JNum(firstPkg, "cycleLength"), _
                                      VhpUtil.JStr(firstPkg, "cycleUnit"))
    End If

    VhpSap.StartTransaction sess, TX_PLAN
    If Not VhpSap.SelectCombo(sess, IP01_CATEGORY, Array(CStr(ctx("planCategory")))) Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": plankategorien ") & CStr(ctx("planCategory")) & _
            VhpUtil.Dk(" findes ikke i SAP's liste.")
    End If
    VhpSap.SetText sess, IP01_STRATEGY, key
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (strategi ") & key & ")"
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (strategi ") & key & ")"

    ' Positionerne knyttes een for een, som i en plan med een cyklus. SAP
    ' viser kun positioner med samme strategi.
    For j = 1 To itemNos.Count
        SetPlanText sess, title, what
        id = FieldId(sess, IP01_ITEM_LINK, FN_ITEM_LINK, "GuiButton")
        If Len(id) = 0 Then
            Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": knappen til at knytte positioner findes ikke [") & _
                VhpSap.ScreenInfo(sess) & "]."
        End If
        VhpSap.Press sess, id
        If j = 1 And VhpSap.HasPopup(sess) Then VhpSap.VKey sess, 0, "wnd[1]"
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"

        VhpSap.SetText sess, IP01_ITEM_NO, CStr(itemNos(j))
        VhpSap.Press sess, ID_BTN_EXECUTE
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        VhpSap.FailOnError sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        If Not VhpSap.Exists(sess, IP01_ITEM_GRID) Then
            Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": position ") & CStr(itemNos(j)) & _
                VhpUtil.Dk(" kan ikke knyttes til planen (") & VhpSap.StatusText(sess) & _
                VhpUtil.Dk("). Har den strategi ") & key & VhpUtil.Dk(", og er den ikke allerede knyttet til en plan? Se den i IP06.")
        End If
        VhpSap.Fnd(sess, IP01_ITEM_GRID).SelectedRows = "0"
        VhpSap.Press sess, IP01_ITEM_CHOOSE
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        VhpSap.FailOnError sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
    Next j
    SetPlanText sess, title, what

    ' Planlaegningsparametre
    If Not hz Is Nothing Then
        SetField sess, FN_HORIZON, "GuiTextField", VhpUtil.JStr(hz, "horizon"), what
        SetField sess, FN_HORIZON_QUALIFIER, "GuiCTextField", CStr(ctx("horizonQualifier")), what
        If Len(VhpUtil.JStr(hz, "period")) > 0 Then
            SetField sess, FN_SCHED_PERIOD, "GuiTextField", VhpUtil.JStr(hz, "period"), what
            SetField sess, FN_SCHED_UNIT, "GuiCTextField", VhpUtil.JStr(hz, "periodUnit"), what
        End If
    Else
        VhpSteps.AddStepWarning ctx, VhpUtil.JStr(plan, "planId") & _
            VhpUtil.Dk(": ingen kaldshorisont fra appen eller Opslag. SAP's forslag fra strategien er brugt; se den i IP03.")
    End If
    SetField sess, FN_START_DATE, "GuiCTextField", startText, what

    ' Sorteringsfeltet: SAP-noeglen (010, 020 ...), som i VhpSteps.CreatePlan.
    sortText = VhpUtil.JStr(plan, "sortField")
    If Len(sortText) > 0 Then
        ' Som PR #380 i VhpSteps: feltet paa navn, en liste eller et tekstfelt.
        id = FindField(sess, FN_SORT_FIELD, "GuiComboBox")
        If Len(id) > 0 Then
            If Not VhpSap.SelectCombo(sess, id, Array(VhpMap.SortKey(sortText)), sortText) Then id = ""
        Else
            id = FindField(sess, FN_SORT_FIELD, "GuiCTextField")
            If Len(id) = 0 Then id = FindField(sess, FN_SORT_FIELD, "GuiTextField")
            If Len(id) > 0 Then VhpSap.SetText sess, id, VhpMap.SortKey(sortText)
        End If
        If Len(id) = 0 Then
            VhpSteps.AddStepWarning ctx, VhpUtil.JStr(plan, "planId") & VhpUtil.Dk(": sorteringsfeltet '") & sortText & _
                VhpUtil.Dk("' kunne ikke v{ae}lges i SAP. S{ae}t det i IP02.")
        End If
    End If

    summary = VhpUtil.Dk("Strategiplanen ") & VhpUtil.JStr(plan, "planId") & " (" & title & VhpUtil.Dk(") er udfyldt i SAP med strategi ") & _
        key & ", " & itemNos.Count & VhpUtil.Dk(" position(er)")
    summary = summary & VhpUtil.Dk(" og startdato ") & startText
    VhpSteps.ConfirmSave ctx, summary & "."

    CreatePlan = VhpSteps.SaveAndReadNumberFor(sess, what, 3, _
        VhpUtil.Dk(" Se i IP03, om planen blev oprettet, f{oe}r den k{oe}res igen."))
End Function

Private Sub SetPlanText(ByVal sess As Object, ByVal title As String, ByVal what As String)
    Dim id As String
    id = FieldId(sess, IP01_TEXT, FN_PLAN_TEXT, "GuiTextField")
    If Len(id) = 0 Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": planens tekstfelt findes ikke [") & VhpSap.ScreenInfo(sess) & "]."
    End If
    VhpSap.SetText sess, id, title
End Sub

' Saet et felt, der kan staa paa et hvilket som helst faneblad.
Private Sub SetField(ByVal sess As Object, ByVal fieldName As String, ByVal guiType As String, _
                     ByVal value As String, ByVal what As String)
    Dim id As String
    id = FindField(sess, fieldName, guiType)
    If Len(id) = 0 Then
        Err.Raise ERR_SAP, "VhpStrategy", what & VhpUtil.Dk(": feltet ") & fieldName & _
            VhpUtil.Dk(" findes ikke p{aa} strategiplanens sk{ae}rm [") & VhpSap.ScreenInfo(sess) & "]."
    End If
    VhpSap.SetText sess, id, value
End Sub

'==============================================================================
' Felter paa navn
'==============================================================================

' Den kendte sti, hvis den findes; ellers feltet paa navn paa skaermen.
Private Function FieldId(ByVal sess As Object, ByVal knownId As String, ByVal fieldName As String, _
                         ByVal guiType As String) As String
    If Len(knownId) > 0 Then
        If VhpSap.Exists(sess, knownId) Then
            FieldId = knownId
            Exit Function
        End If
    End If
    FieldId = NameOnScreen(sess, fieldName, guiType)
End Function

' Feltet paa navn: foerst paa det, der vises, derefter paa hvert faneblad
' i planens og positionens fanebladsraekker. Et faneblad, der ikke er valgt,
' har ingen felter, saa hvert vaelges for sig. "" = findes ikke.
Private Function FindField(ByVal sess As Object, ByVal fieldName As String, ByVal guiType As String) As String
    Dim strips As Variant
    Dim s As Long
    Dim tabIds As Collection
    Dim t As Variant

    FindField = NameOnScreen(sess, fieldName, guiType)
    If Len(FindField) > 0 Then Exit Function

    strips = Array("TABSTRIP_HEAD", "TABSTRIP_ITEM")
    For s = LBound(strips) To UBound(strips)
        Set tabIds = TabIdsOf(sess, CStr(strips(s)))
        For Each t In tabIds
            On Error Resume Next
            sess.FindById(CStr(t)).Select
            On Error GoTo 0
            FindField = NameOnScreen(sess, fieldName, guiType)
            If Len(FindField) > 0 Then Exit Function
        Next t
    Next s
End Function

Private Function NameOnScreen(ByVal sess As Object, ByVal fieldName As String, ByVal guiType As String) As String
    Dim o As Object
    On Error Resume Next
    Set o = sess.FindById("wnd[0]/usr").FindByName(fieldName, guiType)
    If Not o Is Nothing Then NameOnScreen = RelativeId(CStr(o.Id))
    On Error GoTo 0
End Function

' Id'et fra FindByName er absolut (/app/con[0]/ses[0]/wnd[0]/...);
' sessionen vil have det fra wnd[0] (som SortFieldId i VhpSteps).
Private Function RelativeId(ByVal id As String) As String
    Dim p As Long
    RelativeId = id
    p = InStr(1, id, "wnd[")
    If p > 0 Then RelativeId = Mid$(id, p)
End Function

Private Function TabIdsOf(ByVal sess As Object, ByVal stripName As String) As Collection
    Dim strip As Object
    Dim i As Long
    Dim res As New Collection

    On Error Resume Next
    Set strip = sess.FindById("wnd[0]/usr").FindByName(stripName, "GuiTabStrip")
    If Not strip Is Nothing Then
        For i = 0 To strip.Children.Count - 1
            res.Add RelativeId(CStr(strip.Children.ElementAt(i).Id))
        Next i
    End If
    On Error GoTo 0
    Set TabIdsOf = res
End Function

Private Function SafeText(ByVal sess As Object, ByVal id As String) As String
    On Error Resume Next
    SafeText = CStr(sess.FindById(id).Text)
End Function
