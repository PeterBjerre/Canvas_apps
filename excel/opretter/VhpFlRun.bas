Attribute VB_Name = "VhpFlRun"
Option Explicit
'==============================================================================
' VhpFlRun - koerslen af en FL-anmodning: raekke for raekke, med statusfil.
'
' Som VH-planerne (VhpRun): miljoe, nyeste ordre, laas og en statusfil, der
' skrives efter HVER functional location, SAP har gemt. En ny koersel tager
' kun dem, der mangler.
'
' Forskellen: en raekke, SAP afviser, stopper ikke de andre - SPOOL-arket
' fortsatte ogsaa med naeste raekke. Anmodningen er foerst oprettet, naar
' ALLE raekker er gemt; indtil da er den Delvist oprettet.
'
' En FL kan ikke blive en dublet: findes den, aendres den (IL02). Derfor
' maa en ny ordre for samme anmodning koere, selv om en aeldre er delvist
' oprettet, og den aeldre flyttes til Oprettet, naar den nye er faerdig.
'==============================================================================

' Returnerer "XX:tekst" som VhpRun.ProcessOrder: OK, FE (fejl), SK (sprunget
' over) eller ST (stop hele koerslen).
Public Function ProcessFlOrder(ByVal path As String, ByVal root As String, _
                               ByVal sess As Object, ByVal lk As Object) As String
    Dim order As Object
    Dim key As String
    Dim v As Object
    Dim reason As String
    Dim statusPath As String
    Dim status As Object
    Dim ctx As Object
    Dim row As Object
    Dim st As Object
    Dim w As Variant
    Dim errNo As Long
    Dim stopNo As Long
    Dim stopMsg As String
    Dim nFailed As Long
    Dim firstError As String
    Dim label As String
    Dim errMsg As String

    '--- 1. Indlaes og valider ------------------------------------------------
    On Error GoTo LoadFailed
    Set order = VhpOrder.LoadOrder(path)
    On Error GoTo 0

    key = VhpOrder.OrderKey(order)
    VhpRun.Progress key, VhpUtil.Dk("kontrolleres")

    Set v = VhpFl.Validate(order, lk)
    If v("errors").Count > 0 Then
        VhpUi.LogLine key, VhpUtil.Dk("Kan ikke oprettes: ") & v("errors")(1)
        ProcessFlOrder = "FE:" & key & VhpUtil.Dk(": kan ikke oprettes {-} ") & v("errors")(1) & _
            IIf(v("errors").Count > 1, VhpUtil.Dk(" (og ") & (v("errors").Count - 1) & VhpUtil.Dk(" mere {-} se Vis detaljer)"), "")
        Exit Function
    End If

    '--- 2. Miljoe, nyere ordre, laas ----------------------------------------
    reason = VhpRun.CheckEnvironment(order, VhpSap.SystemName(sess))
    If Len(reason) > 0 Then
        VhpUi.LogLine key, Mid$(reason, 2)
        ProcessFlOrder = IIf(Left$(reason, 1) = "!", "ST:", "SK:") & key & ": " & Mid$(reason, 2)
        Exit Function
    End If

    reason = VhpRun.CheckOtherOrders(root, path, key, VhpUtil.JStr(order, "createdOn"), True)
    If Len(reason) > 0 Then
        VhpUi.LogLine key, reason
        ProcessFlOrder = "SK:" & key & ": " & reason
        Exit Function
    End If

    statusPath = VhpFiles.StatusPathFor(path)
    If VhpFiles.FileExists(statusPath) Then
        On Error GoTo LoadFailed
        Set status = VhpFiles.ReadJson(statusPath)
        On Error GoTo 0
        reason = VhpRun.CheckStatus(status, order, VhpSap.SystemName(sess), key)
        If Len(reason) > 0 Then
            VhpUi.LogLine key, reason
            ProcessFlOrder = "SK:" & key & ": " & reason
            Exit Function
        End If
    Else
        Set status = NewFlStatus(order, path)
    End If

    ' Alle raekker gemt, men ikke flyttet (fx afbrudt lige efter sidste)?
    If VhpUtil.JStr(status, "state") = "Created" Then
        On Error GoTo FinishFailed
        FinishFlOrder root, path, status, key, VhpUtil.JStr(order, "createdOn")
        On Error GoTo 0
        ProcessFlOrder = "OK:" & key & VhpUtil.Dk(": var allerede gemt i SAP")
        Exit Function
    End If

    status("state") = "InProgress"
    status("sapSystem") = VhpSap.SystemName(sess)
    status("sapClient") = VhpSap.ClientOf(sess)
    status("lockedBy") = VhpUtil.UserName()
    status("lockedOn") = VhpUtil.IsoNow()
    status("lastError") = Null
    Set status("warnings") = New Collection
    For Each w In v("warnings")
        status("warnings").Add CStr(w)
    Next w
    VhpRun.AddLog status, key, VhpUtil.Dk("Start (") & VhpSap.SystemName(sess) & "/" & VhpSap.ClientOf(sess) & _
        ", " & VhpUtil.UserName() & ")"
    VhpRun.SaveStatus status, statusPath

    Set ctx = VhpUtil.NewDict()
    ctx.Add "lookups", lk
    ctx.Add "confirmSave", VhpConfig.SettingIsYes(SET_CONFIRM_SAVE)
    ctx.Add "warnings", New Collection

    '--- 3. SAP, raekke for raekke --------------------------------------------
    For Each row In VhpUtil.JList(order, "rows")
        Set st = FlStatusRow(status, row)
        If Not VhpUtil.JBool(st, "done") Then
            label = VhpFl.RowLabel(row)
            VhpRun.Progress key, label
            errNo = SaveRow(sess, row, ctx, st)
            VhpRun.MergeStepWarnings status, ctx

            Select Case errNo
                Case 0
                    VhpRun.AddLog status, key, label & ": " & _
                        IIf(VhpUtil.JStr(st, "result") = "Updated", VhpUtil.Dk("fandtes, {ae}ndret"), "oprettet")
                    VhpRun.SaveStatus status, statusPath
                Case ERR_STOP_RUN, ERR_SKIP_PLAN
                    VhpSap.Recover sess
                    stopNo = errNo
                    stopMsg = VhpUtil.JStr(st, "lastError")
                    st("lastError") = Null
                    Exit For
                Case Else
                    VhpSap.Recover sess
                    nFailed = nFailed + 1
                    If Len(firstError) = 0 Then firstError = VhpUtil.JStr(st, "lastError")
                    VhpRun.AddLog status, key, label & ": FEJL: " & VhpUtil.JStr(st, "lastError")
                    VhpRun.SaveStatus status, statusPath
            End Select
        End If
    Next row
    Application.StatusBar = False

    '--- 4. Status ------------------------------------------------------------
    If stopNo = 0 And AllRowsDone(status) Then
        status("state") = "Created"
        status("finishedOn") = VhpUtil.IsoNow()
        status("lastError") = Null
        VhpRun.SaveStatus status, statusPath

        ' Alle FL er gemt. Kan kvitteringen ikke skrives, staar statusfilen paa
        ' Created, og naeste koersel proever kun kvitteringen igen.
        On Error GoTo FinishFailed
        FinishFlOrder root, path, status, key, VhpUtil.JStr(order, "createdOn")
        On Error GoTo 0
        ProcessFlOrder = "OK:" & key & ": " & DoneSummary(status) & _
            IIf(status("warnings").Count > 0, " (" & status("warnings").Count & VhpUtil.Dk(" advarsel(er) {-} se kvitteringen)"), "")
        Exit Function
    End If

    status("state") = IIf(VhpRun.AnythingCreated(status), "Partial", "Failed")
    If stopNo <> 0 Then
        status("lastError") = stopMsg
    Else
        status("lastError") = firstError
    End If
    VhpRun.AddLog status, key, "STOP: " & VhpUtil.JStr(status, "lastError")
    VhpRun.SaveStatus status, statusPath

    Select Case stopNo
        Case ERR_STOP_RUN
            ProcessFlOrder = "ST:" & key & ": " & stopMsg
        Case ERR_SKIP_PLAN
            ProcessFlOrder = "SK:" & key & ": " & stopMsg
        Case Else
            ProcessFlOrder = "FE:" & key & ": " & nFailed & VhpUtil.Dk(" FL fejlede (") & firstError & ")" & _
                IIf(VhpUtil.JStr(status, "state") = "Partial", _
                    VhpUtil.Dk(". De andre er gemt {-} ret fejlen og tryk Opret igen."), ".")
    End Select
    Exit Function

FinishFailed:
    errMsg = Err.Description
    Resume FinishCleanup
FinishCleanup:
    On Error GoTo 0
    VhpUi.LogLine key, VhpUtil.Dk("Gemt i SAP, men kvitteringen kunne ikke skrives: ") & errMsg
    ProcessFlOrder = "FE:" & key & VhpUtil.Dk(": gemt i SAP, men kvitteringen kunne ikke skrives (") & errMsg & _
        VhpUtil.Dk("). Tryk Opret igen for kun at skrive kvitteringen.")
    Exit Function

LoadFailed:
    errMsg = Err.Description
    Resume LoadCleanup
LoadCleanup:
    On Error GoTo 0
    VhpUi.LogLine VhpFiles.FileNameOf(path), errMsg
    ProcessFlOrder = "FE:" & VhpFiles.FileNameOf(path) & ": " & errMsg
End Function

' Een FL i SAP. 0 = gemt; ellers fejlnummeret, og teksten staar i
' statusraekkens lastError.
Private Function SaveRow(ByVal sess As Object, ByVal row As Object, ByVal ctx As Object, _
                         ByVal st As Object) As Long
    Dim res As Object

    On Error GoTo Failed
    Set res = VhpFlSteps.SaveFunctionalLocation(sess, row, ctx)
    st("done") = True
    st("result") = res("result")
    st("sapMessage") = res("message")
    st("lastError") = Null
    Exit Function

Failed:
    SaveRow = Err.Number
    If SaveRow = 0 Then SaveRow = ERR_SAP
    st("lastError") = Err.Description
    Resume Done
Done:
End Function

'==============================================================================
' Statusfilen (samme form som kvitteringen: schema/fl-sap-receipt.schema.json)
'==============================================================================

Private Function NewFlStatus(ByVal order As Object, ByVal path As String) As Object
    Dim s As Object
    Dim req As Object
    Dim rows As New Collection
    Dim row As Object

    Set req = VhpUtil.JObj(order, "request")
    Set s = VhpUtil.NewDict()
    s.Add "kind", FL_RECEIPT_KIND
    s.Add "version", 1
    s.Add "orderGuid", VhpUtil.JStr(order, "orderGuid")
    s.Add "orderFile", VhpFiles.FileNameOf(path)
    s.Add "requestSpId", VhpUtil.JLng(req, "spId")
    s.Add "requestNo", VhpUtil.JStr(req, "requestNo")
    s.Add "state", "InProgress"
    s.Add "sapSystem", Null
    s.Add "sapClient", Null
    s.Add "lockedBy", Null
    s.Add "lockedOn", Null
    s.Add "updatedOn", Null
    s.Add "finishedOn", Null
    For Each row In VhpUtil.JList(order, "rows")
        rows.Add NewFlStatusRow(row)
    Next row
    s.Add "rows", rows
    s.Add "warnings", New Collection
    s.Add "lastError", Null
    s.Add "log", New Collection
    Set NewFlStatus = s
End Function

Private Function NewFlStatusRow(ByVal row As Object) As Object
    Dim st As Object
    Set st = VhpUtil.NewDict()
    st.Add "spId", VhpUtil.JLng(row, "spId")
    st.Add "rowNo", VhpUtil.JLng(row, "rowNo")
    st.Add "functionalLocation", VhpUtil.JStr(row, "functionalLocation")
    st.Add "done", False
    st.Add "result", Null
    st.Add "sapMessage", Null
    st.Add "lastError", Null
    Set NewFlStatusRow = st
End Function

' Raekkens linje i statusfilen. Mangler den, tilfoejes den.
Private Function FlStatusRow(ByVal status As Object, ByVal row As Object) As Object
    Dim st As Object
    For Each st In VhpUtil.JList(status, "rows")
        If VhpUtil.JLng(st, "spId") = VhpUtil.JLng(row, "spId") Then
            Set FlStatusRow = st
            Exit Function
        End If
    Next st
    Set st = NewFlStatusRow(row)
    If Not status.Exists("rows") Then status.Add "rows", New Collection
    status("rows").Add st
    Set FlStatusRow = st
End Function

Private Function AllRowsDone(ByVal status As Object) As Boolean
    Dim st As Object
    If VhpUtil.JList(status, "rows").Count = 0 Then Exit Function
    For Each st In VhpUtil.JList(status, "rows")
        If Not VhpUtil.JBool(st, "done") Then Exit Function
    Next st
    AllRowsDone = True
End Function

' "3 FL gemt i SAP (2 oprettet, 1 aendret)"
Private Function DoneSummary(ByVal status As Object) As String
    Dim st As Object
    Dim nNew As Long
    Dim nChanged As Long
    For Each st In VhpUtil.JList(status, "rows")
        If VhpUtil.JStr(st, "result") = "Updated" Then
            nChanged = nChanged + 1
        Else
            nNew = nNew + 1
        End If
    Next st
    DoneSummary = (nNew + nChanged) & VhpUtil.Dk(" FL gemt i SAP (") & nNew & VhpUtil.Dk(" oprettet, ") & _
        nChanged & VhpUtil.Dk(" {ae}ndret)")
End Function

' Kvitteringen til flowet (Kvitteringer\FL), ordren og aeldre ordrer for samme
' anmodning ud af "Til oprettelse".
Private Sub FinishFlOrder(ByVal root As String, ByVal path As String, ByVal status As Object, _
                          ByVal key As String, ByVal createdOn As String)
    VhpFiles.WriteJson VhpFiles.FlReceiptPathFor(root, path), status
    VhpFiles.MoveToDone root, path
    VhpRun.RetireOlderOrders root, path, key, createdOn
End Sub
