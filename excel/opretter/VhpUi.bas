Attribute VB_Name = "VhpUi"
Option Explicit
'==============================================================================
' VhpUi - det, brugeren ser: arket Start med knapperne og listen over ordrer
' (VH-planer og FL-anmodninger), arket Detaljer, opslagene, indstillingerne
' og loggen.
'
' Setup bygger det hele i en tom projektmappe. Den kan koeres igen: knapperne
' og Start-arket bygges forfra, men tabellerne i Opslag og Indstillinger
' roeres ikke, hvis de findes - det er jeres data.
'==============================================================================

' Office-konstanter som tal: projektmappen skal ikke afhaenge af, hvilke
' referencer der er sat.
Private Const SHAPE_ROUNDED_RECT As Long = 5
Private Const ALIGN_CENTER As Long = 2
Private Const ANCHOR_MIDDLE As Long = 3
Private Const DIALOG_FILE_PICKER As Long = 3
Private Const DIALOG_FOLDER_PICKER As Long = 4

Private Const ORDERS_FIRST_ROW As Long = 9
Private Const ORDER_COLS As Long = 11

'==============================================================================
' Knapperne
'==============================================================================
Public Sub BtnRefresh()
    RefreshList
End Sub

Public Sub BtnPreview()
    Dim path As String
    path = ActiveOrderPath()
    If Len(path) = 0 Then
        MsgBox VhpUtil.Dk("Klik p{aa} en r{ae}kke i listen f{oe}rst."), vbInformation, VHP_APP_NAME
        Exit Sub
    End If
    ShowPreview path
End Sub

Public Sub BtnCreate()
    Dim paths As Collection
    Dim names As String
    Dim p As Variant

    Set paths = SelectedOrderPaths()
    If paths.Count = 0 Then
        MsgBox VhpUtil.Dk("S{ae}t et x i kolonnen V{ae}lg ud for det, der skal oprettes {-} eller klik p{aa} en r{ae}kke."), _
            vbInformation, VHP_APP_NAME
        Exit Sub
    End If

    For Each p In paths
        names = names & "  " & VhpFiles.BaseNameOf(CStr(p)) & vbLf
    Next p

    If MsgBox(VhpUtil.Dk("Opret ") & paths.Count & VhpUtil.Dk(" ordre(r) i SAP ") & _
              VhpConfig.Setting(SET_SAP_SYSTEM) & "?" & vbLf & vbLf & names & vbLf & _
              VhpUtil.Dk("Opretteren arbejder nu i et SAP-vindue. R{oe}r ikke SAP eller Excel, f{oe}r den er f{ae}rdig.") & _
              IIf(VhpConfig.SettingIsYes(SET_CONFIRM_SAVE), vbLf & vbLf & _
                  VhpUtil.Dk("Du bliver spurgt, f{oe}r hvert gem i SAP."), ""), _
              vbOKCancel + vbQuestion, VHP_APP_NAME) <> vbOK Then Exit Sub

    VhpRun.CreateOrders paths
End Sub

Public Sub BtnImport()
    Dim root As String
    Dim fd As Object
    Dim i As Long
    Dim o As Object
    Dim n As Long
    Dim errors As String

    root = RequireRoot()
    If Len(root) = 0 Then Exit Sub

    Set fd = Application.FileDialog(DIALOG_FILE_PICKER)
    fd.Title = VhpUtil.Dk("V{ae}lg ordrefil(er) {-} fx gemt fra mailen")
    fd.AllowMultiSelect = True
    fd.Filters.Clear
    fd.Filters.Add "JSON", "*.json"
    If fd.Show <> -1 Then Exit Sub

    For i = 1 To fd.SelectedItems.Count
        Set o = Nothing
        On Error Resume Next
        Set o = VhpOrder.LoadOrder(fd.SelectedItems(i))
        If Err.Number <> 0 Then
            errors = errors & VhpFiles.FileNameOf(fd.SelectedItems(i)) & ": " & Err.Description & vbLf
            Err.Clear
        End If
        On Error GoTo 0
        If Not o Is Nothing Then
            VhpFiles.CopyIntoOrders root, fd.SelectedItems(i)
            n = n + 1
        End If
    Next i

    RefreshList
    If Len(errors) > 0 Then
        MsgBox n & VhpUtil.Dk(" fil(er) lagt i Til oprettelse.") & vbLf & vbLf & _
            VhpUtil.Dk("Ikke en ordre:") & vbLf & errors, vbExclamation, VHP_APP_NAME
    End If
End Sub

Public Sub BtnFolder()
    Dim fd As Object
    Dim chosen As String

    Set fd = Application.FileDialog(DIALOG_FOLDER_PICKER)
    fd.Title = VhpUtil.Dk("V{ae}lg den synkroniserede mappe SAP-oprettelse")
    If Len(VhpFiles.RootFolder()) > 0 Then fd.InitialFileName = VhpFiles.RootFolder() & "\"
    If fd.Show <> -1 Then Exit Sub

    chosen = VhpFiles.NormalizeRoot(fd.SelectedItems(1))
    VhpFiles.SaveRootFolder chosen
    VhpFiles.EnsureSubfolders chosen
    RefreshList
End Sub

Public Sub BtnOpenFolder()
    Dim root As String
    root = RequireRoot()
    If Len(root) = 0 Then Exit Sub
    Shell "explorer.exe """ & root & """", vbNormalFocus
End Sub

Public Sub BtnTestSap()
    VhpRun.TestConnection
End Sub

Public Sub BtnSelfTest()
    VhpTest.RunSelfTest
End Sub

Private Function RequireRoot() As String
    RequireRoot = VhpFiles.RootFolder()
    If Len(RequireRoot) = 0 Then
        MsgBox VhpUtil.Dk("Mappen er ikke valgt. Tryk V{ae}lg mappe og find den synkroniserede mappe ") & _
            FOLDER_LIBRARY & ".", vbExclamation, VHP_APP_NAME
    End If
End Function

'==============================================================================
' Listen over planer
'==============================================================================
Public Sub RefreshList()
    Dim ws As Worksheet
    Dim lo As ListObject
    Dim root As String
    Dim lk As Object
    Dim files As Collection
    Dim f As Variant
    Dim infos As New Collection
    Dim info As Object
    Dim newest As Object
    Dim key As String
    Dim lr As ListRow

    On Error GoTo Failed
    Set ws = ThisWorkbook.Worksheets(SH_START)
    Set lo = ws.ListObjects(LO_ORDERS)
    Application.ScreenUpdating = False

    If Not lo.DataBodyRange Is Nothing Then lo.DataBodyRange.Delete
    root = VhpFiles.RootFolder()
    WriteHeaderInfo ws, root
    If Len(root) = 0 Then GoTo Done

    Set lk = VhpLookup.Load()
    Set files = VhpFiles.ListOrderFiles(root)
    Set newest = VhpUtil.NewDict()

    ' Foerste gennemloeb: laes alle, og find den nyeste ordre pr. plan eller
    ' anmodning.
    For Each f In files
        Set info = ReadOrderInfo(CStr(f), lk)
        infos.Add info
        key = UCase$(CStr(info("id")))
        If Len(key) > 0 Then
            If Not newest.Exists(key) Then
                newest.Add key, CStr(info("createdOn"))
            ElseIf CStr(info("createdOn")) > CStr(newest(key)) Then
                newest(key) = CStr(info("createdOn"))
            End If
        End If
    Next f

    For Each info In infos
        key = UCase$(CStr(info("id")))
        If Len(key) > 0 And CStr(info("state")) = VhpUtil.Dk("Klar") Then
            If CStr(info("createdOn")) < CStr(newest(key)) Then
                info("state") = "Erstattet"
                info("message") = VhpUtil.Dk("Der er en nyere ordre for samme ") & _
                    IIf(info("type") = "FL", "anmodning", "plan") & VhpUtil.Dk(" {-} brug den.")
            End If
        End If
        Set lr = lo.ListRows.Add
        lr.Range.Value = Array("", info("type"), info("id"), info("title"), info("plant"), _
            info("content"), info("environment"), info("received"), info("state"), info("message"), info("file"))
        ColorState lr.Range.Cells(1, 9), CStr(info("state"))
    Next info

Done:
    Application.ScreenUpdating = True
    Exit Sub

Failed:
    Application.ScreenUpdating = True
    MsgBox VhpUtil.Dk("Listen kunne ikke opdateres: ") & Err.Description, vbExclamation, VHP_APP_NAME
End Sub

' Det, listen viser om een ordrefil.
Private Function ReadOrderInfo(ByVal path As String, ByVal lk As Object) As Object
    Dim info As Object
    Dim order As Object
    Dim plan As Object
    Dim rows As Collection
    Dim first As Object
    Dim v As Object
    Dim status As Object
    Dim errText As String

    Set info = VhpUtil.NewDict()
    info.Add "file", VhpFiles.FileNameOf(path)
    info.Add "type", ""
    info.Add "id", ""
    info.Add "title", ""
    info.Add "plant", ""
    info.Add "content", ""
    info.Add "environment", ""
    info.Add "received", ""
    info.Add "createdOn", ""
    info.Add "state", ""
    info.Add "message", ""
    Set ReadOrderInfo = info

    On Error Resume Next
    Set order = VhpOrder.LoadOrder(path)
    If Err.Number <> 0 Then errText = Err.Description
    On Error GoTo 0
    If order Is Nothing Then
        info("state") = VhpUtil.Dk("Ugyldig fil")
        info("message") = errText
        Exit Function
    End If

    info("id") = VhpOrder.OrderKey(order)
    If VhpOrder.IsFl(order) Then
        info("type") = "FL"
        Set rows = VhpUtil.JList(order, "rows")
        If rows.Count > 0 Then
            Set first = rows(1)
            info("title") = VhpUtil.JStr(first, "functionalLocation") & "  " & VhpUtil.JStr(first, "description") & _
                IIf(rows.Count > 1, "  (+" & (rows.Count - 1) & ")", "")
            info("plant") = UCase$(Left$(VhpUtil.JStr(first, "functionalLocation"), 3))
        End If
        info("content") = rows.Count & " FL"
    Else
        info("type") = "VH-plan"
        Set plan = VhpUtil.JObj(order, "plan")
        info("title") = VhpUtil.JStr(plan, "title")
        info("plant") = VhpUtil.JStr(plan, "plant")
        info("content") = VhpUtil.JList(order, "items").Count & " items, " & _
            VhpUtil.JList(order, "operations").Count & " operationer"
    End If
    info("environment") = VhpUtil.JStr(order, "environment")
    info("createdOn") = VhpUtil.JStr(order, "createdOn")
    info("received") = VhpUtil.IsoToDisplay(VhpUtil.JStr(order, "createdOn"))

    If VhpFiles.FileExists(VhpFiles.StatusPathFor(path)) Then
        On Error Resume Next
        Set status = VhpFiles.ReadJson(VhpFiles.StatusPathFor(path))
        On Error GoTo 0
    End If

    If Not status Is Nothing Then
        Select Case VhpUtil.JStr(status, "state")
            Case "InProgress"
                info("state") = VhpUtil.Dk("I gang (") & VhpUtil.JStr(status, "lockedBy") & ")"
                info("message") = VhpUtil.Dk("Sidst skrevet ") & VhpUtil.JStr(status, "updatedOn")
            Case "Partial"
                info("state") = VhpUtil.Dk("Delvist oprettet")
                info("message") = VhpUtil.JStr(status, "lastError")
            Case "Failed"
                info("state") = VhpUtil.Dk("Fejlede")
                info("message") = VhpUtil.JStr(status, "lastError")
            Case "NeedsCheck"
                info("state") = VhpUtil.Dk("Kr{ae}ver kontrol")
                info("message") = VhpUtil.JStr(status, "lastError")
            Case "Created"
                info("state") = Trim$(VhpUtil.Dk("Oprettet ") & VhpUtil.JStr(status, "sapPlanNo"))
                info("message") = VhpUtil.Dk("Flyttes til Oprettet ved n{ae}ste k{oe}rsel.")
        End Select
        If Len(CStr(info("state"))) > 0 Then Exit Function
    End If

    Set v = VhpOrder.Validate(order, lk)
    If v("errors").Count > 0 Then
        info("state") = VhpUtil.Dk("Kan ikke oprettes")
        info("message") = v("errors")(1)
        If v("errors").Count > 1 Then
            info("message") = info("message") & VhpUtil.Dk(" (+") & (v("errors").Count - 1) & VhpUtil.Dk(" {-} se Vis detaljer)")
        End If
    Else
        info("state") = VhpUtil.Dk("Klar")
        If v("warnings").Count > 0 Then
            info("message") = v("warnings").Count & VhpUtil.Dk(" advarsel(er): ") & v("warnings")(1)
        End If
    End If
End Function

Private Sub WriteHeaderInfo(ByVal ws As Worksheet, ByVal root As String)
    Dim sysName As String
    ws.Range("B6").Value = IIf(Len(root) > 0, root, VhpUtil.Dk("(ikke valgt {-} tryk V{ae}lg mappe)"))
    sysName = VhpConfig.Setting(SET_SAP_SYSTEM)
    ws.Range("B7").Value = sysName & VhpUtil.Dk(", klient ") & VhpConfig.Setting(SET_SAP_CLIENT) & _
        IIf(VhpConfig.IsProductionSystem(sysName), VhpUtil.Dk("  {-}  PRODUKTION"), VhpUtil.Dk("  {-}  test")) & _
        IIf(VhpConfig.SettingIsYes(SET_CONFIRM_SAVE), VhpUtil.Dk("  {-}  du bliver spurgt f{oe}r hvert gem"), "")
End Sub

Private Sub ColorState(ByVal cell As Range, ByVal state As String)
    Dim c As Long
    Select Case True
        Case state = VhpUtil.Dk("Klar")
            c = RGB(223, 246, 221)
        Case Left$(state, 8) = "Oprettet"
            c = RGB(223, 246, 221)
        Case state = VhpUtil.Dk("Kan ikke oprettes"), state = VhpUtil.Dk("Fejlede"), state = VhpUtil.Dk("Ugyldig fil")
            c = RGB(253, 231, 233)
        Case state = VhpUtil.Dk("Kr{ae}ver kontrol"), state = VhpUtil.Dk("Delvist oprettet")
            c = RGB(255, 244, 206)
        Case Else
            c = RGB(237, 235, 233)
    End Select
    cell.Interior.Color = c
End Sub

' Raekkerne med x i Vaelg. Er der ingen, den raekke markoeren staar i.
Private Function SelectedOrderPaths() As Collection
    Dim result As New Collection
    Dim lo As ListObject
    Dim r As Long
    Dim root As String
    Dim one As String

    Set SelectedOrderPaths = result
    root = VhpFiles.RootFolder()
    If Len(root) = 0 Then Exit Function

    Set lo = ThisWorkbook.Worksheets(SH_START).ListObjects(LO_ORDERS)
    If lo.DataBodyRange Is Nothing Then Exit Function

    For r = 1 To lo.ListRows.Count
        If UCase$(Trim$(CStr(lo.DataBodyRange.Cells(r, 1).Value))) = "X" Then
            result.Add VhpFiles.OrdersFolder(root) & "\" & CStr(lo.DataBodyRange.Cells(r, ORDER_COLS).Value)
        End If
    Next r

    If result.Count = 0 Then
        one = ActiveOrderPath()
        If Len(one) > 0 Then result.Add one
    End If
End Function

' Ordren i den raekke, markoeren staar i paa Start-arket.
Private Function ActiveOrderPath() As String
    Dim lo As ListObject
    Dim r As Long
    Dim root As String

    root = VhpFiles.RootFolder()
    If Len(root) = 0 Then Exit Function
    If ActiveSheet Is Nothing Then Exit Function
    If ActiveSheet.Name <> SH_START Then Exit Function

    Set lo = ThisWorkbook.Worksheets(SH_START).ListObjects(LO_ORDERS)
    If lo.DataBodyRange Is Nothing Then Exit Function
    r = ActiveCell.Row - lo.DataBodyRange.Row + 1
    If r < 1 Or r > lo.ListRows.Count Then Exit Function
    ActiveOrderPath = VhpFiles.OrdersFolder(root) & "\" & CStr(lo.DataBodyRange.Cells(r, ORDER_COLS).Value)
End Function

'==============================================================================
' Detaljer - det, der kommer til at staa i SAP, felt for felt
'==============================================================================
Public Sub ShowPreview(ByVal path As String)
    Dim ws As Worksheet
    Dim order As Object
    Dim lk As Object
    Dim v As Object
    Dim status As Object

    On Error GoTo Failed
    Set order = VhpOrder.LoadOrder(path)
    Set lk = VhpLookup.Load()
    Set v = VhpOrder.Validate(order, lk)
    If VhpFiles.FileExists(VhpFiles.StatusPathFor(path)) Then
        On Error Resume Next
        Set status = VhpFiles.ReadJson(VhpFiles.StatusPathFor(path))
        On Error GoTo Failed
    End If

    Set ws = ThisWorkbook.Worksheets(SH_PREVIEW)
    Application.ScreenUpdating = False
    ws.Cells.Clear

    If VhpOrder.IsFl(order) Then
        PreviewFl ws, path, order, lk, v, status
    Else
        PreviewPlan ws, path, order, lk, v, status
    End If

    ws.Columns("A").ColumnWidth = 24
    ws.Columns("B").ColumnWidth = 44
    ws.Columns("C:K").ColumnWidth = 14
    ws.Columns("B").WrapText = False
    Application.ScreenUpdating = True
    ws.Activate
    ws.Range("A1").Select
    Exit Sub

Failed:
    Application.ScreenUpdating = True
    MsgBox VhpUtil.Dk("Ordren kan ikke vises: ") & Err.Description, vbExclamation, VHP_APP_NAME
End Sub

' Fejl, advarsler og status fra statusfilen.
Private Sub WriteChecks(ByVal ws As Worksheet, ByRef r As Long, ByVal v As Object, ByVal status As Object, _
                        ByVal okText As String)
    Dim msg As Variant

    Section ws, r, "Kontrol"
    If v("errors").Count = 0 And v("warnings").Count = 0 Then
        ws.Cells(r, 1).Value = okText
        r = r + 1
    End If
    For Each msg In v("errors")
        ws.Cells(r, 1).Value = "Fejl"
        ws.Cells(r, 2).Value = msg
        ws.Range(ws.Cells(r, 1), ws.Cells(r, 2)).Interior.Color = RGB(253, 231, 233)
        r = r + 1
    Next msg
    For Each msg In v("warnings")
        ws.Cells(r, 1).Value = "Advarsel"
        ws.Cells(r, 2).Value = msg
        ws.Range(ws.Cells(r, 1), ws.Cells(r, 2)).Interior.Color = RGB(255, 244, 206)
        r = r + 1
    Next msg
    If Not status Is Nothing Then
        ws.Cells(r, 1).Value = "Status"
        ws.Cells(r, 2).Value = VhpUtil.JStr(status, "state") & "  " & VhpUtil.JStr(status, "lastError")
        r = r + 1
    End If
    r = r + 1
End Sub

'--- VH-plan ------------------------------------------------------------------
Private Sub PreviewPlan(ByVal ws As Worksheet, ByVal path As String, ByVal order As Object, _
                        ByVal lk As Object, ByVal v As Object, ByVal status As Object)
    Dim plan As Object
    Dim r As Long
    Dim item As Object
    Dim op As Object
    Dim m As Object
    Dim plantRec As Object
    Dim hz As Object
    Dim firstDue As Date
    Dim cycle As Double
    Dim unitText As String
    Dim svc As Object
    Dim fl As Variant
    Dim flText As String
    Dim st As Object
    Dim cand As Object
    Dim n As Long

    Set plan = VhpUtil.JObj(order, "plan")
    Set plantRec = VhpLookup.Plant(lk, VhpUtil.JStr(plan, "plant"))
    cycle = VhpUtil.JNum(plan, "cycle")
    unitText = VhpMap.NormalizeUnit(VhpUtil.JStr(plan, "unit"))
    Set hz = VhpLookup.Horizon(lk, cycle, unitText)

    r = 1
    ws.Cells(r, 1).Value = VhpUtil.JStr(plan, "planId") & "  " & ChrW$(8211) & "  " & VhpUtil.JStr(plan, "title")
    ws.Cells(r, 1).Font.Size = 16
    ws.Cells(r, 1).Font.Bold = True
    r = r + 1
    ws.Cells(r, 1).Value = VhpUtil.Dk("Fil: ") & VhpFiles.FileNameOf(path) & VhpUtil.Dk("    Milj{oe}: ") & _
        VhpUtil.JStr(order, "environment") & VhpUtil.Dk("    Modtaget: ") & VhpUtil.IsoToDisplay(VhpUtil.JStr(order, "createdOn")) & _
        VhpUtil.Dk("    Indmeldt af: ") & VhpUtil.JStr(plan, "requesterName")
    r = r + 2

    WriteChecks ws, r, v, status, VhpUtil.Dk("Ingen fejl. Planen kan oprettes.")

    '--- Planen ---------------------------------------------------------------
    Section ws, r, VhpUtil.Dk("Planen {-} IP01")
    Pair ws, r, "Plankategori", VhpConfig.Setting(SET_PLAN_CATEGORY) & VhpUtil.Dk(" (ingen strategi)")
    Pair ws, r, "Tekst", VhpUtil.Clip(VhpUtil.JStr(plan, "title"), 40)
    Pair ws, r, "Cyklus", VhpMap.NumberKey(cycle) & " " & unitText
    If VhpUtil.TryParseYmd(VhpUtil.JStr(plan, "plannedDate"), firstDue) Then
        Pair ws, r, VhpUtil.Dk("F{oe}rste forfald"), VhpMap.SapDate(firstDue)
        Pair ws, r, VhpUtil.Dk("Startdato i SAP"), VhpMap.SapDate(VhpMap.StartDate(firstDue, cycle, unitText)) & _
            VhpUtil.Dk("  (en cyklus f{oe}r f{oe}rste forfald)")
    End If
    If Not hz Is Nothing Then
        Pair ws, r, "Kaldshorisont", VhpUtil.JStr(hz, "horizon") & " " & VhpConfig.Setting(SET_HORIZON_QUALIFIER)
        Pair ws, r, VhpUtil.Dk("Planl{ae}gningsperiode"), VhpUtil.JStr(hz, "period") & " " & VhpUtil.JStr(hz, "periodUnit")
    End If
    Pair ws, r, "Sorteringsfelt", VhpUtil.JStr(plan, "sortField") & IIf(VhpUtil.JHas(plan, "sortFieldId"), _
        " (Id " & VhpUtil.JStr(plan, "sortFieldId") & ")", "")
    If Not plantRec Is Nothing Then
        Pair ws, r, VhpUtil.Dk("V{ae}rk"), VhpUtil.JStr(plan, "plant") & VhpUtil.Dk(" {-} SAP-v{ae}rk ") & _
            VhpUtil.JStr(plantRec, "sapPlant") & ", profil " & VhpUtil.JStr(plantRec, "profile")
    End If
    r = r + 1

    '--- Items ----------------------------------------------------------------
    For Each item In VhpUtil.JList(order, "items")
        Set st = Nothing
        If Not status Is Nothing Then
            For Each cand In VhpUtil.JList(status, "items")
                If VhpUtil.JLng(cand, "spId") = VhpUtil.JLng(item, "spId") Then
                    Set st = cand
                    Exit For
                End If
            Next cand
        End If

        Section ws, r, VhpOrder.ItemLabel(item) & "  " & ChrW$(8211) & "  " & VhpUtil.JStr(item, "title")
        Pair ws, r, VhpUtil.Dk("Position (IP04)"), VhpUtil.Clip(VhpUtil.JStr(item, "title"), 40)
        Pair ws, r, "Funktionsplads", VhpUtil.JStr(item, "functionalLocation")
        flText = ""
        For Each fl In VhpMap.ObjectListEntries(VhpUtil.JStr(item, "objectList"))
            flText = flText & IIf(Len(flText) > 0, "; ", "") & CStr(fl)
        Next fl
        Pair ws, r, "Objektliste", flText
        Pair ws, r, "Ordreart", VhpUtil.JStr(item, "orderType")
        Pair ws, r, "Aktivitetstype (ILART)", VhpMap.ActivityCode(VhpUtil.JStr(item, "activityType")) & _
            "  (" & VhpUtil.JStr(item, "activityType") & ")"
        Pair ws, r, "Arbejdscenter", VhpMap.WorkCenter(VhpUtil.JStr(item, "mainWorkCenter"))
        Pair ws, r, "Prioritet", VhpMap.PriorityKey(VhpUtil.JStr(item, "priority")) & "  (" & VhpUtil.JStr(item, "priority") & ")"
        Pair ws, r, "Brugerstatus", VhpUtil.JStr(item, "userStatus") & "  " & VhpUtil.JStr(item, "nonFlowUserStatus")
        Pair ws, r, "Revision", VhpMap.RevisionValue(VhpUtil.JBool(item, "revision"), VhpUtil.JStr(item, "revisionMark"))
        Pair ws, r, "Revideret af", UCase$(VhpUtil.JStr(item, "responsibleInitials"))
        Pair ws, r, "Langtekst (IP05)", Replace(VhpItf.HtmlToSapText(VhpUtil.JStr(item, "longText")), vbLf, " / ")
        If Not plantRec Is Nothing Then
            Pair ws, r, "Arbejdsplan (IA05)", VhpUtil.Dk("profil ") & VhpUtil.JStr(plantRec, "profile") & _
                VhpUtil.Dk(", v{ae}rk ") & VhpUtil.JStr(plantRec, "sapPlant") & _
                ", arbejdscenter " & VhpMap.WorkCenter(VhpUtil.JStr(item, "mainWorkCenter")) & _
                ", beskrivelse '" & VhpUtil.Clip(VhpUtil.JStr(item, "title"), 40) & "'"
        End If
        If Not st Is Nothing Then
            Pair ws, r, VhpUtil.Dk("Oprettet indtil nu"), VhpUtil.Dk("arbejdsplan ") & VhpUtil.JStr(st, "taskListGroup") & _
                "/" & VhpUtil.JStr(st, "taskListCounter") & VhpUtil.Dk(", position ") & VhpUtil.JStr(st, "sapItemNo")
        End If

        Header ws, r, Array("#", "Kort tekst", "Arbejdscenter", VhpUtil.Dk("Kontroln{oe}gle"), "Timer", "Antal", _
            "Pris", "Varegruppe", VhpUtil.Dk("Leverand{oe}r"), "Ydelse (PM03)", "Langtekst")
        n = 0
        For Each op In VhpOrder.Operations(item)
            n = n + 1
            Set svc = Nothing
            If UCase$(VhpUtil.JStr(op, "controlKey")) = "PM03" Then Set svc = VhpLookup.Service(lk, VhpUtil.JStr(op, "workCenter"))
            ws.Range(ws.Cells(r, 1), ws.Cells(r, 11)).Value = Array( _
                Format$(n * 10, "0000"), VhpUtil.Clip(VhpUtil.JStr(op, "shortText"), 40), _
                VhpMap.WorkCenter(VhpUtil.JStr(op, "workCenter")), UCase$(VhpUtil.JStr(op, "controlKey")), _
                VhpUtil.JNum(op, "work"), VhpUtil.JNum(op, "persons", 1), VhpUtil.JNum(op, "price"), _
                VhpUtil.JStr(op, "materialGroup"), VhpMap.VendorNo(VhpUtil.JStr(op, "vendor")), _
                IIf(svc Is Nothing, "", VhpUtil.JStr(svc, "serviceNo")), _
                IIf(VhpItf.HasText(VhpUtil.JStr(op, "longText")), "ja", ""))
            r = r + 1
        Next op

        If VhpOrder.Materials(item).Count > 0 Then
            r = r + 1
            Header ws, r, Array("Materiale", "Antal", "Enhed", "Operation", "Tekst", VhpUtil.Dk("{-} oprettes IKKE automatisk, tilf{oe}j i IA06"))
            For Each m In VhpOrder.Materials(item)
                ws.Range(ws.Cells(r, 1), ws.Cells(r, 5)).Value = Array("'" & VhpUtil.JStr(m, "materialNo"), _
                    VhpUtil.JNum(m, "quantity"), VhpUtil.JStr(m, "unit"), "'" & VhpUtil.JStr(m, "operationNo"), _
                    VhpUtil.JStr(m, "text"))
                r = r + 1
            Next m
        End If
        r = r + 1
    Next item

End Sub

'--- FL-anmodning -------------------------------------------------------------
Private Sub PreviewFl(ByVal ws As Worksheet, ByVal path As String, ByVal order As Object, _
                      ByVal lk As Object, ByVal v As Object, ByVal status As Object)
    Dim req As Object
    Dim rows As Collection
    Dim row As Object
    Dim r As Long
    Dim st As Object
    Dim cand As Object
    Dim cls As String
    Dim chars As Object
    Dim k As Variant
    Dim extras As String
    Dim x As Variant
    Dim warranty As String

    Set req = VhpUtil.JObj(order, "request")
    Set rows = VhpUtil.JList(order, "rows")

    r = 1
    ws.Cells(r, 1).Value = VhpUtil.JStr(req, "requestNo") & "  " & ChrW$(8211) & "  " & rows.Count & " functional location(s)"
    ws.Cells(r, 1).Font.Size = 16
    ws.Cells(r, 1).Font.Bold = True
    r = r + 1
    ws.Cells(r, 1).Value = VhpUtil.Dk("Fil: ") & VhpFiles.FileNameOf(path) & VhpUtil.Dk("    Milj{oe}: ") & _
        VhpUtil.JStr(order, "environment") & VhpUtil.Dk("    Modtaget: ") & VhpUtil.IsoToDisplay(VhpUtil.JStr(order, "createdOn")) & _
        VhpUtil.Dk("    Indmeldt af: ") & VhpUtil.JStr(req, "requesterName")
    r = r + 1
    ws.Cells(r, 1).Value = VhpUtil.Dk("Hver FL oprettes med IL01. Findes den allerede, {ae}ndres den med IL02 {-} som i SPOOL-arket. ") & _
        VhpUtil.Dk("Et tomt felt bliver ogs{aa} tomt i SAP.")
    ws.Cells(r, 1).Font.Color = RGB(96, 94, 92)
    r = r + 2

    WriteChecks ws, r, v, status, VhpUtil.Dk("Ingen fejl. Anmodningen kan oprettes.")

    For Each row In rows
        Set st = Nothing
        If Not status Is Nothing Then
            For Each cand In VhpUtil.JList(status, "rows")
                If VhpUtil.JLng(cand, "spId") = VhpUtil.JLng(row, "spId") Then
                    Set st = cand
                    Exit For
                End If
            Next cand
        End If

        cls = VhpFl.ClassOf(row)
        extras = ""
        For Each x In VhpFl.ExtraClasses(row)
            extras = extras & " + " & CStr(x)
        Next x

        Section ws, r, VhpFl.RowLabel(row) & "  " & ChrW$(8211) & "  " & VhpUtil.JStr(row, "description")
        Pair ws, r, "Strukturindikator", UCase$(VhpUtil.JStr(row, "strIndicator"))
        Pair ws, r, "Klasse", cls & extras & IIf(VhpFl.HasClassAssignment(cls) Or Len(extras) > 0, "", VhpUtil.Dk("  (ingen klassetildeling)"))
        Pair ws, r, "Beskrivelse", VhpUtil.JStr(row, "description")
        Pair ws, r, "Producent", VhpFl.FieldValue(row, FLF_MANUFACTURER)
        Pair ws, r, "Model", VhpFl.FieldValue(row, FLF_MODEL)
        Pair ws, r, "Partnummer", VhpFl.FieldValue(row, FLF_PARTNO)
        Pair ws, r, "Serienummer", VhpFl.FieldValue(row, FLF_SERIAL)
        Pair ws, r, "Rum", VhpFl.FieldValue(row, FLF_ROOM)
        Pair ws, r, "ABC", VhpFl.FieldValue(row, FLF_ABC)
        Pair ws, r, "Sorteringsfelt", VhpFl.FieldValue(row, FLF_SORTFIELD)
        warranty = VhpFl.SapDateText(VhpFl.FieldValue(row, FLF_WARRANTY_START))
        If Len(VhpFl.FieldValue(row, FLF_WARRANTY_END)) > 0 Then
            warranty = warranty & "  " & ChrW$(8211) & "  " & VhpFl.SapDateText(VhpFl.FieldValue(row, FLF_WARRANTY_END))
        End If
        Pair ws, r, "Garanti", warranty
        If cls = "KAB" Then Pair ws, r, "Overordnet FL", VhpFl.FieldValue(row, FLF_SUPERIOR)
        Pair ws, r, "Tilladelser", JoinItems(VhpFl.Permits(row), ", ")

        Set chars = VhpFl.CharacteristicMap(row, lk)
        If chars.Count > 0 Then
            Header ws, r, Array("Karakteristik", VhpUtil.Dk("V{ae}rdi"), "")
            For Each k In chars.Keys
                ws.Cells(r, 1).Value = CStr(k)
                ws.Cells(r, 2).Value = "'" & Replace(CStr(chars(k)), "|", "; ")
                If VhpFl.IsSpecialCharacteristic(CStr(k)) And VhpFl.SplitValues(CStr(chars(k))).Count > 1 Then
                    ws.Cells(r, 3).Value = VhpUtil.Dk("v{ae}lges i v{ae}rdidialogen (F4)")
                End If
                r = r + 1
            Next k
        Else
            Pair ws, r, "Karakteristikker", VhpUtil.Dk("(ingen)")
        End If

        If VhpFl.UnusedFields(row, lk).Count > 0 Then
            Pair ws, r, VhpUtil.Dk("Overf{oe}res ikke"), JoinItems(VhpFl.UnusedFields(row, lk), "; ")
        End If
        If Not st Is Nothing Then
            If VhpUtil.JBool(st, "done") Then
                Pair ws, r, "I SAP", VhpUtil.JStr(st, "result") & ": " & VhpUtil.JStr(st, "sapMessage")
            ElseIf Len(VhpUtil.JStr(st, "lastError")) > 0 Then
                Pair ws, r, "Sidste fejl", VhpUtil.JStr(st, "lastError")
            End If
        End If
        r = r + 1
    Next row
End Sub

Private Function JoinItems(ByVal c As Collection, ByVal sep As String) As String
    Dim x As Variant
    For Each x In c
        JoinItems = JoinItems & IIf(Len(JoinItems) > 0, sep, "") & CStr(x)
    Next x
End Function

Private Sub Section(ByVal ws As Worksheet, ByRef r As Long, ByVal title As String)
    ws.Cells(r, 1).Value = title
    ws.Cells(r, 1).Font.Bold = True
    ws.Cells(r, 1).Font.Size = 12
    ws.Range(ws.Cells(r, 1), ws.Cells(r, 11)).Borders(9).LineStyle = 1   ' bund
    r = r + 1
End Sub

Private Sub Pair(ByVal ws As Worksheet, ByRef r As Long, ByVal label As String, ByVal value As String)
    ws.Cells(r, 1).Value = label
    ws.Cells(r, 1).Font.Color = RGB(96, 94, 92)
    ws.Cells(r, 2).Value = "'" & value
    r = r + 1
End Sub

Private Sub Header(ByVal ws As Worksheet, ByRef r As Long, ByVal titles As Variant)
    Dim i As Long
    For i = LBound(titles) To UBound(titles)
        ws.Cells(r, 1 + i - LBound(titles)).Value = titles(i)
        ws.Cells(r, 1 + i - LBound(titles)).Font.Bold = True
        ws.Cells(r, 1 + i - LBound(titles)).Interior.Color = RGB(237, 235, 233)
    Next i
    r = r + 1
End Sub

'==============================================================================
' Loggen
'==============================================================================
Public Sub LogLine(ByVal planId As String, ByVal text As String)
    Dim lo As ListObject
    Dim lr As ListRow

    On Error Resume Next
    Set lo = ThisWorkbook.Worksheets(SH_LOG).ListObjects(LO_LOG)
    If lo Is Nothing Then Exit Sub
    Set lr = lo.ListRows.Add
    lr.Range.Value = Array(Format$(Now, "yyyy-mm-dd hh:nn:ss"), planId, VhpUtil.UserName(), text)
    ' Loggen i projektmappen er til at foelge med; statusfilerne er arkivet.
    If lo.ListRows.Count > 3000 Then lo.ListRows(1).Delete
End Sub

'==============================================================================
' Opsaetning
'==============================================================================
Public Sub Setup()
    SetupQuiet
    ThisWorkbook.Worksheets(SH_START).Activate
    RefreshList

    MsgBox VhpUtil.Dk("Ops{ae}tningen er f{ae}rdig.") & vbLf & vbLf & _
        VhpUtil.Dk("1. Udfyld de tomme felter i arket Opslag (ydelsesnumre og de v{ae}rker, der mangler). ") & _
        VhpUtil.Dk("Tabellen Karakteristikker er SPOOL-arkets og kan bruges, som den er.") & vbLf & _
        VhpUtil.Dk("2. Tjek arket Indstillinger.") & vbLf & _
        VhpUtil.Dk("3. Gem projektmappen som Excel-projektmappe med makroer (.xlsm).") & vbLf & _
        VhpUtil.Dk("4. Tryk Selvtest i arket Indstillinger."), vbInformation, VHP_APP_NAME
End Sub

' Samme opsaetning uden beskeder. Build-Opretter.ps1 kalder den, naar den
' bygger projektmappen fra .bas-filerne - en MsgBox ville staa og vente paa
' et klik, ingen kan se.
Public Sub SetupQuiet()
    Application.ScreenUpdating = False

    RenameOldSheet SH_PREVIEW_OLD, SH_PREVIEW
    EnsureSheet SH_START, 1
    EnsureSheet SH_PREVIEW, 2
    EnsureSheet SH_LOOKUP, 3
    EnsureSheet SH_SETTINGS, 4
    EnsureSheet SH_LOG, 5
    RemoveEmptyDefaultSheets

    BuildStart
    BuildLookups
    BuildSettings
    BuildLog

    Application.ScreenUpdating = True
End Sub

' Et ark, der har skiftet navn mellem to udgaver, beholder sin plads.
Private Sub RenameOldSheet(ByVal oldName As String, ByVal newName As String)
    Dim ws As Worksheet
    Dim wsNew As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(oldName)
    Set wsNew = ThisWorkbook.Worksheets(newName)
    On Error GoTo 0
    If ws Is Nothing Or Not wsNew Is Nothing Then Exit Sub
    ws.Name = newName
End Sub

Private Sub EnsureSheet(ByVal sheetName As String, ByVal position As Long)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
    If ws Is Nothing Then
        If position <= ThisWorkbook.Worksheets.Count Then
            Set ws = ThisWorkbook.Worksheets.Add(Before:=ThisWorkbook.Worksheets(position))
        Else
            Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        End If
        ws.Name = sheetName
    End If
End Sub

' Ark1 / Sheet1 fra en ny projektmappe, hvis det er tomt.
Private Sub RemoveEmptyDefaultSheets()
    Dim ws As Worksheet
    Dim i As Long
    For i = ThisWorkbook.Worksheets.Count To 1 Step -1
        Set ws = ThisWorkbook.Worksheets(i)
        Select Case ws.Name
            Case SH_START, SH_PREVIEW, SH_LOOKUP, SH_SETTINGS, SH_LOG
            Case Else
                If Application.WorksheetFunction.CountA(ws.UsedRange) = 0 And ThisWorkbook.Worksheets.Count > 5 Then
                    Application.DisplayAlerts = False
                    ws.Delete
                    Application.DisplayAlerts = True
                End If
        End Select
    Next i
End Sub

Private Sub BuildStart()
    Dim ws As Worksheet
    Dim x As Double
    Dim y As Double
    Dim lo As ListObject

    Set ws = ThisWorkbook.Worksheets(SH_START)
    DeleteShapes ws

    ws.Range("A1").Value = VhpUtil.Dk("VH-planer og FL ") & ChrW$(8594) & " SAP"
    ws.Range("A1").Font.Size = 20
    ws.Range("A1").Font.Bold = True
    ws.Range("A2").Value = VhpUtil.Dk("VH-planer og FL-anmodninger, der er klar til oprettelse. Klik p{aa} en r{ae}kke og tryk Vis detaljer for at se, hvad der kommer i SAP. ") & _
        VhpUtil.Dk("S{ae}t x i V{ae}lg og tryk Opret i SAP.")
    ws.Range("A2").Font.Color = RGB(96, 94, 92)
    ws.Range("A6").Value = "Mappe:"
    ws.Range("A7").Value = "SAP:"
    ws.Range("A6:A7").Font.Bold = True

    x = ws.Range("A4").Left
    y = ws.Range("A4").Top
    AddButton ws, "btnVhpRefresh", VhpUtil.Dk("Opdater liste"), "VhpUi.BtnRefresh", x, y, 110, RGB(0, 120, 212)
    x = x + 116
    AddButton ws, "btnVhpPreview", VhpUtil.Dk("Vis detaljer"), "VhpUi.BtnPreview", x, y, 100, RGB(0, 120, 212)
    x = x + 106
    AddButton ws, "btnVhpCreate", VhpUtil.Dk("Opret i SAP"), "VhpUi.BtnCreate", x, y, 120, RGB(16, 124, 16)
    x = x + 136
    AddButton ws, "btnVhpImport", VhpUtil.Dk("Import{e}r fil{...}"), "VhpUi.BtnImport", x, y, 110, RGB(96, 94, 92)
    x = x + 116
    AddButton ws, "btnVhpFolder", VhpUtil.Dk("V{ae}lg mappe{...}"), "VhpUi.BtnFolder", x, y, 110, RGB(96, 94, 92)
    x = x + 116
    AddButton ws, "btnVhpOpenFolder", VhpUtil.Dk("{AA}bn mappen"), "VhpUi.BtnOpenFolder", x, y, 100, RGB(96, 94, 92)
    x = x + 106
    AddButton ws, "btnVhpTestSap", VhpUtil.Dk("Test SAP"), "VhpUi.BtnTestSap", x, y, 90, RGB(96, 94, 92)
    ws.Rows(4).RowHeight = 30

    On Error Resume Next
    Set lo = ws.ListObjects(LO_ORDERS)
    On Error GoTo 0
    If lo Is Nothing Then
        ws.Range(ws.Cells(ORDERS_FIRST_ROW, 1), ws.Cells(ORDERS_FIRST_ROW, ORDER_COLS)).Value = OrderHeaders()
        Set lo = ws.ListObjects.Add(xlSrcRange, ws.Range(ws.Cells(ORDERS_FIRST_ROW, 1), _
            ws.Cells(ORDERS_FIRST_ROW + 1, ORDER_COLS)), , xlYes)
        lo.Name = LO_ORDERS
        lo.TableStyle = "TableStyleLight9"
    Else
        ' Overskrifterne fra version 1.0 (Plan, Items, Operationer) skiftes ud.
        lo.HeaderRowRange.Value = OrderHeaders()
    End If

    ws.Columns(1).ColumnWidth = 7
    ws.Columns(2).ColumnWidth = 9
    ws.Columns(3).ColumnWidth = 11
    ws.Columns(4).ColumnWidth = 42
    ws.Columns(5).ColumnWidth = 7
    ws.Columns(6).ColumnWidth = 20
    ws.Columns(7).ColumnWidth = 8
    ws.Columns(8).ColumnWidth = 19
    ws.Columns(9).ColumnWidth = 20
    ws.Columns(10).ColumnWidth = 70
    ws.Columns(11).ColumnWidth = 36
End Sub

' Listens kolonner. Fil skal vaere den sidste (ORDER_COLS), Status nr. 9.
Private Function OrderHeaders() As Variant
    OrderHeaders = Array(VhpUtil.Dk("V{ae}lg"), "Type", "ID", "Titel", VhpUtil.Dk("V{ae}rk"), "Indhold", _
        VhpUtil.Dk("Milj{oe}"), "Modtaget", "Status", "Besked", "Fil")
End Function

' Baglaens: sletter man i en For Each, springes hver anden figur over.
Private Sub DeleteShapes(ByVal ws As Worksheet)
    Dim i As Long
    For i = ws.Shapes.Count To 1 Step -1
        ws.Shapes(i).Delete
    Next i
End Sub

Private Sub AddButton(ByVal ws As Worksheet, ByVal shapeName As String, ByVal caption As String, _
                      ByVal macro As String, ByVal x As Double, ByVal y As Double, _
                      ByVal w As Double, ByVal color As Long)
    Dim shp As Shape
    Set shp = ws.Shapes.AddShape(SHAPE_ROUNDED_RECT, x, y, w, 28)
    shp.Name = shapeName
    shp.OnAction = macro
    shp.Fill.ForeColor.RGB = color
    shp.Line.Visible = False
    With shp.TextFrame2
        .VerticalAnchor = ANCHOR_MIDDLE
        .TextRange.Text = caption
        .TextRange.Font.Size = 11
        .TextRange.Font.Bold = True
        .TextRange.Font.Fill.ForeColor.RGB = RGB(255, 255, 255)
        .TextRange.ParagraphFormat.Alignment = ALIGN_CENTER
    End With
End Sub

Private Sub BuildLookups()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(SH_LOOKUP)

    ws.Range("A1").Value = VhpUtil.Dk("Opslag {-} det SAP-specifikke, appen ikke ved noget om. Svarer til fanen Call_Horizon_Table i det gamle regneark.")
    ws.Range("A1").Font.Bold = True

    If Not TableExists(ws, LO_PLANTS) Then
        CreateTable ws, "A3", LO_PLANTS, _
            Array(VhpUtil.Dk("V{ae}rk"), VhpUtil.Dk("SAP-v{ae}rk"), "Arbejdsplanprofil", "Modelydelsesspec.", VhpUtil.Dk("Bem{ae}rkning")), _
            Array( _
                Array("ASV", "2805", "PMASV", "2805", ""), _
                Array("AVV", "2806", "PMAVV", "2806", ""), _
                Array("HCV", "", "PMHCV", "", VhpUtil.Dk("SAP-v{ae}rk mangler")), _
                Array("HEV", "2810", "PMHEV", "2810", ""), _
                Array("KYV", "2808", "PMKYV", "2808", ""), _
                Array("SKV", "2801", "PMSKV", "2801", ""), _
                Array("SMV", "", "PMSMV", "", VhpUtil.Dk("SAP-v{ae}rk mangler")), _
                Array("SSV", "2804", "PMSSV", "2804", ""))
    End If

    If Not TableExists(ws, LO_HORIZON) Then
        CreateTable ws, "H3", LO_HORIZON, _
            Array("Cyklus", "Enhed", "Kaldshorisont", VhpUtil.Dk("Planl{ae}gningsperiode"), "Periodeenhed"), _
            Array( _
                Array("1", "WK", "2", "2", "YR"), Array("2", "WK", "7", "2", "YR"), _
                Array("6", "WK", "20", "2", "YR"), Array("1", "MON", "15", "2", "YR"), _
                Array("2", "MON", "40", "2", "YR"), Array("3", "MON", "40", "2", "YR"), _
                Array("4", "MON", "40", "2", "YR"), Array("6", "MON", "45", "2", "YR"), _
                Array("1", "YR", "55", "2", "YR"), Array("2", "YR", "60", "4", "YR"), _
                Array("3", "YR", "65", "6", "YR"), Array("4", "YR", "70", "8", "YR"), _
                Array("5", "YR", "80", "10", "YR"), Array("6", "YR", "80", "12", "YR"), _
                Array("8", "YR", "100", "16", "YR"))
    End If

    If Not TableExists(ws, LO_SERVICES) Then
        CreateTable ws, "N3", LO_SERVICES, _
            Array("Arbejdscenter (endelse)", "Ydelsesnr.", "Varegruppe", VhpUtil.Dk("Bem{ae}rkning")), _
            Array( _
                Array("XSTIL", "3000002", "B11.08", "Stillads"), Array("XISOL", "3000001", "B11.02", "Isolering"), _
                Array("XELEK", "3000100", "B09.03", "El"), Array("XINDU", "3000360", "B11.01", "Industriservice"), _
                Array("XSMED", "3000000", "B08.04", "Smed"), Array("XSVEJ", "3000050", "B08.04", VhpUtil.Dk("Svejsning")), _
                Array("XSPEC", "", "", "Special"))
        ws.Range("N2").Value = VhpUtil.Dk("Standardvaerdier for PM03-ydelser er seedet i builderen.")
        ws.Range("N2").Font.Color = RGB(96, 94, 92)
    End If

    If Not TableExists(ws, LO_FL_CHARS) Then
        CreateTable ws, "S3", LO_FL_CHARS, _
            Array("Klasse", "Karakteristik (navnet i SAP)", "SAP-navn", VhpUtil.Dk("Bem{ae}rkning")), _
            CharacteristicRows()
        ws.Range("S2").Value = VhpUtil.Dk("FL: hvilke felter der er karakteristikker for hvilken klasse {-} fra SPOOL-arkets DictionaryTable.")
        ws.Range("S2").Font.Color = RGB(96, 94, 92)
    End If

    ws.Columns("A:W").AutoFit
End Sub

' SPOOL-arkets DictionaryTable som raekker til CreateTable.
Private Function CharacteristicRows() As Variant
    Dim seed As Collection
    Dim rowsData() As Variant
    Dim i As Long

    Set seed = VhpFl.CharacteristicSeed()
    ReDim rowsData(0 To seed.Count - 1)
    For i = 1 To seed.Count
        rowsData(i - 1) = Array(seed(i)(0), seed(i)(1), seed(i)(2), "")
    Next i
    CharacteristicRows = rowsData
End Function

Private Sub BuildSettings()
    Dim ws As Worksheet
    Dim lo As ListObject
    Dim rowsToAdd As Variant
    Dim i As Long
    Dim lr As ListRow

    Set ws = ThisWorkbook.Worksheets(SH_SETTINGS)
    ws.Range("A1").Value = VhpUtil.Dk("Indstillinger {-} f{ae}lles for alle, der bruger projektmappen. Mappen huskes pr. bruger.")
    ws.Range("A1").Font.Bold = True

    rowsToAdd = Array( _
        Array(SET_SAP_SYSTEM, "SAP-system", VhpUtil.Dk("Systemet, opretteren logger p{aa}. GQ1 = test, GP1 = produktion.")), _
        Array(SET_SAP_CLIENT, "Klient", ""), _
        Array(SET_PROD_SYSTEMS, "Produktionssystemer", VhpUtil.Dk("Kommasepareret. DEV- og TEST-ordrer kan ikke oprettes her, PROD-ordrer kun her.")), _
        Array(SET_LOGON_TEST, "SAP Logon, test", VhpUtil.Dk("Forbindelsens navn i SAP Logon. Bruges, hvis SAP ikke er {aa}bent.")), _
        Array(SET_LOGON_PROD, "SAP Logon, produktion", VhpUtil.Dk("Forbindelsens navn i SAP Logon.")), _
        Array(SET_NEW_SESSION, "Eget SAP-vindue", VhpUtil.Dk("Ja: opretteren {aa}bner sit eget SAP-vindue, s{aa} dit arbejde i de andre ikke forstyrres.")), _
        Array(SET_CONFIRM_SAVE, VhpUtil.Dk("Bekr{ae}ft hvert gem"), VhpUtil.Dk("Ja: opretteren sp{oe}rger f{oe}r hvert gem i SAP. S{ae}t til Nej, n{aa}r I stoler p{aa} den.")), _
        Array(SET_ITF_PATH, "Langtekstfil", VhpUtil.Dk("Samme sti som det gamle regneark {-} SAP GUI's sikkerhedsregel kender den.")), _
        Array(SET_KEY_DATE, VhpUtil.Dk("N{oe}gledato (IA05)"), ""), _
        Array(SET_HORIZON_QUALIFIER, "Kaldshorisont-kvalifikator", ""), _
        Array(SET_TASKLIST_TYPE, "Arbejdsplantype", "A = generel arbejdsplan"), _
        Array(SET_PM02_MATGROUP, "Varegruppe ved PM02 uden varegruppe", VhpUtil.Dk("Det gamle regneark brugte altid B08.06.")), _
        Array(SET_DECIMAL_SEP, "Decimaltegn i SAP", VhpUtil.Dk("Som i SAP-brugerprofilen (System > Brugerprofil > Egne data > Standardv{ae}rdier).")), _
        Array(SET_PLAN_CATEGORY, "Plankategori", ""))

    If Not TableExists(ws, LO_SETTINGS) Then
        ws.Range("A3:D3").Value = Array(VhpUtil.Dk("N{oe}gle"), "Indstilling", VhpUtil.Dk("V{ae}rdi"), "Forklaring")
        Set lo = ws.ListObjects.Add(xlSrcRange, ws.Range("A3:D4"), , xlYes)
        lo.Name = LO_SETTINGS
        lo.TableStyle = "TableStyleLight9"
        lo.ListColumns(3).DataBodyRange.NumberFormat = "@"
        lo.ListRows(1).Delete
    Else
        Set lo = ws.ListObjects(LO_SETTINGS)
    End If

    ' Manglende noegler tilfoejes; eksisterende vaerdier roeres ikke.
    For i = LBound(rowsToAdd) To UBound(rowsToAdd)
        If Not SettingRowExists(lo, CStr(rowsToAdd(i)(0))) Then
            Set lr = lo.ListRows.Add
            lr.Range.Cells(1, 3).NumberFormat = "@"
            lr.Range.Value = Array(rowsToAdd(i)(0), rowsToAdd(i)(1), VhpConfig.DefaultSetting(CStr(rowsToAdd(i)(0))), rowsToAdd(i)(2))
        End If
    Next i

    ws.Columns(1).ColumnWidth = 18
    ws.Columns(2).ColumnWidth = 34
    ws.Columns(3).ColumnWidth = 44
    ws.Columns(4).ColumnWidth = 90

    DeleteShapes ws
    AddButton ws, "btnVhpSelfTest", "Selvtest", "VhpUi.BtnSelfTest", _
        ws.Range("F1").Left, ws.Range("F1").Top, 100, RGB(96, 94, 92)
End Sub

Private Function SettingRowExists(ByVal lo As ListObject, ByVal key As String) As Boolean
    Dim r As Long
    If lo.DataBodyRange Is Nothing Then Exit Function
    For r = 1 To lo.ListRows.Count
        If StrComp(Trim$(CStr(lo.DataBodyRange.Cells(r, 1).Value)), key, vbTextCompare) = 0 Then
            SettingRowExists = True
            Exit Function
        End If
    Next r
End Function

Private Sub BuildLog()
    Dim ws As Worksheet
    Dim lo As ListObject
    Set ws = ThisWorkbook.Worksheets(SH_LOG)
    If TableExists(ws, LO_LOG) Then
        ws.ListObjects(LO_LOG).HeaderRowRange.Value = Array("Tidspunkt", "ID", "Bruger", "Besked")
        Exit Sub
    End If
    ws.Range("A1:D1").Value = Array("Tidspunkt", "ID", "Bruger", "Besked")
    Set lo = ws.ListObjects.Add(xlSrcRange, ws.Range("A1:D2"), , xlYes)
    lo.Name = LO_LOG
    lo.TableStyle = "TableStyleLight9"
    lo.ListRows(1).Delete
    ws.Columns(1).ColumnWidth = 20
    ws.Columns(2).ColumnWidth = 10
    ws.Columns(3).ColumnWidth = 10
    ws.Columns(4).ColumnWidth = 120
End Sub

Private Function TableExists(ByVal ws As Worksheet, ByVal tableName As String) As Boolean
    Dim lo As ListObject
    On Error Resume Next
    Set lo = ws.ListObjects(tableName)
    On Error GoTo 0
    TableExists = Not (lo Is Nothing)
End Function

' Tabel med overskrifter og startraekker. Alle celler er tekst, saa "2805"
' og "01.01.2020" ikke bliver til tal og datoer.
Private Sub CreateTable(ByVal ws As Worksheet, ByVal topLeft As String, ByVal tableName As String, _
                        ByVal headers As Variant, ByVal rowsData As Variant)
    Dim r0 As Long
    Dim c0 As Long
    Dim nCols As Long
    Dim nRows As Long
    Dim i As Long
    Dim lo As ListObject

    r0 = ws.Range(topLeft).Row
    c0 = ws.Range(topLeft).Column
    nCols = UBound(headers) - LBound(headers) + 1
    nRows = UBound(rowsData) - LBound(rowsData) + 1

    ws.Range(ws.Cells(r0, c0), ws.Cells(r0 + nRows, c0 + nCols - 1)).NumberFormat = "@"
    ws.Range(ws.Cells(r0, c0), ws.Cells(r0, c0 + nCols - 1)).Value = headers
    For i = 0 To nRows - 1
        ws.Range(ws.Cells(r0 + 1 + i, c0), ws.Cells(r0 + 1 + i, c0 + nCols - 1)).Value = rowsData(LBound(rowsData) + i)
    Next i

    Set lo = ws.ListObjects.Add(xlSrcRange, ws.Range(ws.Cells(r0, c0), ws.Cells(r0 + nRows, c0 + nCols - 1)), , xlYes)
    lo.Name = tableName
    lo.TableStyle = "TableStyleLight9"
End Sub
