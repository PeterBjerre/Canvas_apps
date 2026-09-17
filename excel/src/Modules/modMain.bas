Option Explicit

Public Sub Export_Order_All()
    On Error GoTo EH

    Dim orders As Collection
    Dim i As Long
    Dim aufnr As String
    Dim successCount As Long
    Dim failCount As Long
    Dim errMsg As String
    Dim errorLog As String
    Dim compareWarning As String
    Dim exportWarning As String
    Dim cockpitWarning As String
    Dim waposCount As Long
    Dim waposItems As Collection
    Dim summary As String
    Dim extractStatusActive As Boolean
    Dim orderPhaseStart As Double
    Dim comparePhaseStart As Double
    Dim compareStep As Long

    Const ORDER_PHASE_BASE As Long = 0
    Const ORDER_PHASE_SPAN As Long = 50
    Const SAP_PHASE_BASE As Long = 50
    Const SAP_PHASE_SPAN As Long = 35
    Const COMPARE_PHASE_BASE As Long = 85
    Const COMPARE_PHASE_SPAN As Long = 15

    Set orders = ReadOrderNumbersFromExtractData()
    If orders Is Nothing Or orders.Count = 0 Then
        MsgBox "Ingen ordrenumre fundet i '" & WS_EXTRACT_DATA & "' kolonne D fra række 4.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    extractStatusActive = mdlExtractStatus.EnsureExtractStatusForm("Extract status")
    orderPhaseStart = Timer
    UpdateMainExtractStatus extractStatusActive, ORDER_PHASE_BASE, ORDER_PHASE_SPAN, 0, orders.Count, "Order fetch", "Starting...", orderPhaseStart

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    Set modUtil.gWB = modUtil.EnsureOutputWorkbook()
    Debug.Print "Output workbook = [" & modUtil.gWB.Name & "]"

    modUtil.PrepareSheet WS_RAW_ORDRE_HEADER
    modUtil.PrepareSheet WS_RAW_ORDRE_OPERATIONS
    modUtil.PrepareSheet WS_RAW_ORDRE_OBJECTS
    modUtil.PrepareSheet WS_RAW_ORDRE_ATTACHMENTS
    modUtil.PrepareSheet WS_RAW_ORDRE_COMPONENTS

    For i = 1 To orders.Count
        aufnr = CStr(orders(i))
        errMsg = vbNullString
        If ProcessSingleOrder(aufnr, errMsg) Then
            successCount = successCount + 1
        Else
            failCount = failCount + 1
            If Len(errorLog) > 0 Then errorLog = errorLog & vbCrLf
            errorLog = errorLog & errMsg
        End If

        UpdateMainExtractStatus extractStatusActive, ORDER_PHASE_BASE, ORDER_PHASE_SPAN, i, orders.Count, "Order fetch", aufnr, orderPhaseStart
    Next i

    Set waposItems = CollectIw33WaposFromHeader()
    If Not waposItems Is Nothing Then waposCount = waposItems.Count
    UpdateMainExtractStatus extractStatusActive, SAP_PHASE_BASE, SAP_PHASE_SPAN, 0, 1, "SAP extract", "Preparing...", Timer

    If waposCount > 0 Then
        On Error Resume Next
        StartExport waposItems, True, SAP_PHASE_BASE, SAP_PHASE_SPAN, False
        If Err.Number <> 0 Then
            exportWarning = "StartExport fejlede: " & Err.Description
            Err.Clear
        End If
        On Error GoTo EH
    Else
        exportWarning = "StartExport overstaet: ingen Maintenance_item vaerdier fundet i Raw_Ordre_Header."
        UpdateMainExtractStatus extractStatusActive, SAP_PHASE_BASE, SAP_PHASE_SPAN, 1, 1, "SAP extract", "Skipped (no Maintenance_item values)", Timer
    End If

    comparePhaseStart = Timer
    compareStep = 0
    UpdateMainExtractStatus extractStatusActive, COMPARE_PHASE_BASE, COMPARE_PHASE_SPAN, compareStep, 2, "Compare", "Starting compare engine...", comparePhaseStart

    compareWarning = RunCompareEngineWithFallback()
    compareStep = 1
    UpdateMainExtractStatus extractStatusActive, COMPARE_PHASE_BASE, COMPARE_PHASE_SPAN, compareStep, 2, "Compare", "Compare engine done", comparePhaseStart

    If Len(compareWarning) = 0 Then
        On Error Resume Next
        modCockpit.BuildCompareCockpit
        If Err.Number <> 0 Then
            cockpitWarning = "Cockpit opbygning fejlede: " & Err.Description
            Err.Clear
        End If
        On Error GoTo EH
        compareStep = 2
        UpdateMainExtractStatus extractStatusActive, COMPARE_PHASE_BASE, COMPARE_PHASE_SPAN, compareStep, 2, "Compare", "Cockpit done", comparePhaseStart
    Else
        compareStep = 2
        UpdateMainExtractStatus extractStatusActive, COMPARE_PHASE_BASE, COMPARE_PHASE_SPAN, compareStep, 2, "Compare", "Cockpit skipped", comparePhaseStart
    End If

    If Len(exportWarning) > 0 Then
        If Len(compareWarning) > 0 Then
            compareWarning = exportWarning & vbCrLf & compareWarning
        Else
            compareWarning = exportWarning
        End If
    End If

    If Len(cockpitWarning) > 0 Then
        If Len(compareWarning) > 0 Then
            compareWarning = compareWarning & vbCrLf & cockpitWarning
        Else
            compareWarning = cockpitWarning
        End If
    End If

    summary = "Ordrebehandling fuldført." & vbCrLf & _
              "Fundet i input: " & CStr(orders.Count) & vbCrLf & _
              "Succes: " & CStr(successCount) & vbCrLf & _
              "Fejl: " & CStr(failCount)

    If failCount > 0 Then
        summary = summary & vbCrLf & vbCrLf & "Fejl pr. ordre:" & vbCrLf & errorLog
    End If

    If Len(compareWarning) > 0 Then
        summary = summary & vbCrLf & vbCrLf & "Compare-note:" & vbCrLf & compareWarning
    End If

    If extractStatusActive Then
        mdlExtractStatus.FinishExtractStatus "Done - preparing summary..."
        mdlExtractStatus.CloseExtractStatus
        extractStatusActive = False
    End If

    MsgBox summary, IIf(failCount = 0, vbInformation, vbExclamation), APP_TITLE

    On Error Resume Next
    mdlFormOverlay.OpenOverlayForCompareCockpit
    On Error GoTo EH

CleanExit:
    If extractStatusActive Then mdlExtractStatus.CloseExtractStatus
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub

EH:
    If extractStatusActive Then
        mdlExtractStatus.UpdateExtractStatus 100, "Flow failed: " & Err.Description
        mdlExtractStatus.CloseExtractStatus
        extractStatusActive = False
    End If
    MsgBox "Fejl: " & Err.Number & vbCrLf & Err.Description, vbCritical, APP_TITLE
    Resume CleanExit
End Sub

Private Function ProcessSingleOrder(ByVal aufnr As String, ByRef errMsg As String) As Boolean
    On Error GoTo EH

    Dim url As String
    Dim movementUrl As String
    Dim movementWarning As String
    Dim iw33Status As String
    Dim iw33Wapos As String
    Dim root As Object

    url = BASE_URL & "WorkOrderHeaderSet('" & aufnr & "')?$format=json"
    Debug.Print "FINAL URL = [" & url & "]"

    Set root = HttpGetJson(url)
    modOrderParserJson.ParseOrderJSON root, aufnr

    movementUrl = modMovementParser.BuildMovementsUrlForOrder(aufnr)
    Debug.Print "MOVEMENTS URL = [" & movementUrl & "]"

    On Error Resume Next
    modMovementParser.ParseMovementsFromUrl movementUrl, aufnr
    If Err.Number <> 0 Then
        movementWarning = WS_RAW_ORDRE_COMPONENTS & " for ordre " & aufnr & " fejlede: " & Err.Description
        Debug.Print movementWarning
        Err.Clear
    End If
    On Error GoTo EH

    ' Skip IW33 SAP GUI call if OData already provided Maintenance_item (WAPOS)
    If Not HasExistingWapos(aufnr) Then
        iw33Wapos = FetchOrderItemFromIw33(aufnr, iw33Status)
        UpdateOrderHeaderIw33Link aufnr, iw33Wapos, iw33Status
    Else
        Debug.Print "IW33 overstaet for " & aufnr & " - WAPOS fra OData"
    End If

    ProcessSingleOrder = True
    Exit Function

EH:
    errMsg = "Ordre " & aufnr & ": " & Err.Description
    ProcessSingleOrder = False
End Function

Private Function FetchOrderItemFromIw33(ByVal aufnr As String, ByRef statusText As String) As String
    Const tabIhplId As String = "wnd[0]/usr/subSUB_ALL:SAPLCOIH:3001/ssubSUB_LEVEL:SAPLCOIH:1100/tabsTS_1100/tabpIHPL"
    Const waposFieldId As String = "wnd[0]/usr/subSUB_ALL:SAPLCOIH:3001/ssubSUB_LEVEL:SAPLCOIH:1100/tabsTS_1100/tabpIHPL/ssubSUB_AUFTRAG:SAPLCOIH:1160/ctxtCAUFVD-WAPOS"

    On Error GoTo EH

    statusText = vbNullString

    If Not Attach_Session_Core() Then
        statusText = "IW33_FEJL: Ingen aktiv SAP-session"
        Exit Function
    End If

    If objSess Is Nothing Then
        statusText = "IW33_FEJL: SAP-session ikke tilgaengelig"
        Exit Function
    End If

    NavigateToTransactionLocal TX_IW33
    objSess.FindById("wnd[0]/usr/ctxtCAUFVD-AUFNR").Text = aufnr
    objSess.FindById("wnd[0]").sendVKey 0

    objSess.FindById(tabIhplId).Select
    FetchOrderItemFromIw33 = Trim$(CStr(objSess.FindById(waposFieldId).Text))
    If Len(FetchOrderItemFromIw33) > 0 Then
        statusText = "IW33_OK"
    Else
        statusText = "IW33_MANGLER_WAPOS"
    End If

    On Error Resume Next
    objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
    On Error GoTo 0
    Exit Function

EH:
    statusText = "IW33_FEJL: " & Err.Description
    On Error Resume Next
    objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
    On Error GoTo 0
End Function

Private Sub NavigateToTransactionLocal(ByVal transactionCode As String)
    objSess.FindById("wnd[0]/tbar[0]/okcd").Text = transactionCode
    objSess.FindById("wnd[0]").sendVKey 0
End Sub

Private Sub UpdateOrderHeaderIw33Link(ByVal aufnr As String, ByVal wapos As String, ByVal statusText As String)
    Dim ws As Worksheet
    Dim colAufnr As Long
    Dim colWapos As Long
    Dim lastRow As Long
    Dim targetRow As Long
    Dim r As Long

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_RAW_ORDRE_HEADER)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    colAufnr = EnsureHeaderColumn(ws, "Order_number")
    colWapos = EnsureHeaderColumn(ws, "Maintenance_item")

    lastRow = ws.Cells(ws.Rows.Count, colAufnr).End(xlUp).Row
    If lastRow < 2 Then lastRow = 1

    targetRow = 0
    For r = 2 To lastRow
        If Trim$(CStr(ws.Cells(r, colAufnr).Value)) = aufnr Then
            targetRow = r
            Exit For
        End If
    Next r

    If targetRow = 0 Then
        targetRow = lastRow + 1
        ws.Cells(targetRow, colAufnr).Value = aufnr
    End If

    ws.Cells(targetRow, colWapos).Value = wapos
End Sub

Private Function HasExistingWapos(ByVal aufnr As String) As Boolean
    ' Check if Raw_Ordre_Header already has a non-empty Maintenance_item for this order
    Dim ws As Worksheet
    Dim colAufnr As Long, colWapos As Long
    Dim lastRow As Long, r As Long, existing As String

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_RAW_ORDRE_HEADER)
    On Error GoTo 0
    If ws Is Nothing Then Exit Function

    colAufnr = FindHeaderColumn(ws, "Order_number")
    colWapos = FindHeaderColumn(ws, "Maintenance_item")
    If colAufnr = 0 Or colWapos = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, colAufnr).End(xlUp).Row
    For r = 2 To lastRow
        If Trim$(CStr(ws.Cells(r, colAufnr).Value)) = aufnr Then
            existing = Trim$(CStr(ws.Cells(r, colWapos).Value))
            HasExistingWapos = (Len(existing) > 0)
            Exit Function
        End If
    Next r
End Function

Private Function FindHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim lastCol As Long, c As Long
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(1, c).Value)), headerName, vbTextCompare) = 0 Then
            FindHeaderColumn = c
            Exit Function
        End If
    Next c
End Function

Private Function EnsureHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim lastCol As Long
    Dim c As Long

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If Len(Trim$(CStr(ws.Cells(1, 1).Value))) = 0 Then lastCol = 0

    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(1, c).Value)), headerName, vbTextCompare) = 0 Then
            EnsureHeaderColumn = c
            Exit Function
        End If
    Next c

    EnsureHeaderColumn = lastCol + 1
    ws.Cells(1, EnsureHeaderColumn).Value = headerName
    ws.Rows(1).Font.Bold = True
End Function

Private Function ReadOrderNumbersFromExtractData() As Collection
    Dim ws As Worksheet
    Dim rowNo As Long
    Dim aufnr As String
    Dim values As Collection

    Set values = New Collection

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_EXTRACT_DATA)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ReadOrderNumbersFromExtractData = values
        Exit Function
    End If

    For rowNo = 4 To ws.Rows.Count
        aufnr = Trim(CStr(ws.Cells(rowNo, "D").Value))
        If Len(aufnr) = 0 Then Exit For
        values.Add aufnr
    Next rowNo

    Set ReadOrderNumbersFromExtractData = values
End Function

Private Function RunCompareEngineWithFallback() As String
    On Error GoTo UseVbaCompare

    If Not USE_PYTHON_COMPARE Then
        RunCompareEngineWithFallback = modCompare.RunCompareWithStatus()
        Exit Function
    End If

    ' Avoid direct module reference so compile does not fail if Python compare module is absent.
    RunCompareEngineWithFallback = CStr(Application.Run("RunPythonCompareWithStatus"))
    Exit Function

UseVbaCompare:
    Err.Clear
    RunCompareEngineWithFallback = modCompare.RunCompareWithStatus()
End Function

Private Function EnsureOutputWorkbook() As Workbook
    Set EnsureOutputWorkbook = ThisWorkbook
End Function

Private Function CollectIw33WaposFromHeader() As Collection
    Dim wsHeader As Worksheet
    Dim cWapos As Long
    Dim lastRow As Long
    Dim r As Long
    Dim wapos As String
    Dim seen As Object
    Dim result As Collection

    Set result = New Collection

    On Error Resume Next
    Set wsHeader = ThisWorkbook.Worksheets(WS_RAW_ORDRE_HEADER)
    On Error GoTo 0

    If wsHeader Is Nothing Then
        Set CollectIw33WaposFromHeader = result
        Exit Function
    End If

    cWapos = EnsureHeaderColumn(wsHeader, "Maintenance_item")
    lastRow = wsHeader.Cells(wsHeader.Rows.Count, cWapos).End(xlUp).Row
    If lastRow < 2 Then
        Set CollectIw33WaposFromHeader = result
        Exit Function
    End If

    Set seen = CreateObject("Scripting.Dictionary")

    For r = 2 To lastRow
        wapos = Trim$(CStr(wsHeader.Cells(r, cWapos).Value))
        If Len(wapos) > 0 Then
            If Not seen.Exists(wapos) Then
                seen.Add wapos, True
                result.Add wapos
            End If
        End If
    Next r

    Set CollectIw33WaposFromHeader = result
End Function

Private Sub UpdateMainExtractStatus(ByVal statusActive As Boolean, _
                                    ByVal basePct As Long, _
                                    ByVal spanPct As Long, _
                                    ByVal currentCount As Long, _
                                    ByVal totalCount As Long, _
                                    ByVal phaseName As String, _
                                    ByVal detail As String, _
                                    ByVal phaseStart As Double)
    Dim pct As Long

    If Not statusActive Then Exit Sub

    pct = MainResolvePhasePercent(basePct, spanPct, currentCount, totalCount)
    mdlExtractStatus.UpdateExtractStatus pct, MainBuildProgressText(phaseName, currentCount, totalCount, detail, phaseStart)
End Sub

Private Function MainResolvePhasePercent(ByVal basePct As Long, _
                                         ByVal spanPct As Long, _
                                         ByVal currentCount As Long, _
                                         ByVal totalCount As Long) As Long
    Dim ratio As Double
    Dim value As Long

    basePct = MainClampPct(basePct)
    spanPct = MainClampPct(spanPct)

    If totalCount <= 0 Then
        value = basePct + spanPct
    Else
        If currentCount < 0 Then currentCount = 0
        If currentCount > totalCount Then currentCount = totalCount
        ratio = CDbl(currentCount) / CDbl(totalCount)
        value = basePct + CLng(CDbl(spanPct) * ratio)
    End If

    MainResolvePhasePercent = MainClampPct(value)
End Function

Private Function MainBuildProgressText(ByVal phaseName As String, _
                                       ByVal currentCount As Long, _
                                       ByVal totalCount As Long, _
                                       ByVal detail As String, _
                                       ByVal phaseStart As Double) As String
    Dim safeCurrent As Long
    Dim safeTotal As Long
    Dim msg As String

    safeCurrent = currentCount
    safeTotal = totalCount

    If safeCurrent < 0 Then safeCurrent = 0
    If safeTotal < 0 Then safeTotal = 0
    If safeTotal > 0 And safeCurrent > safeTotal Then safeCurrent = safeTotal

    msg = phaseName & ": " & CStr(safeCurrent) & "/" & CStr(safeTotal)
    If Len(Trim$(detail)) > 0 Then msg = msg & " - " & detail

    MainBuildProgressText = msg & " | " & MainBuildEtaText(phaseStart, safeCurrent, safeTotal)
End Function

Private Function MainBuildEtaText(ByVal phaseStart As Double, _
                                  ByVal currentCount As Long, _
                                  ByVal totalCount As Long) As String
    Dim elapsedSeconds As Double
    Dim secondsPerUnit As Double
    Dim remainingSeconds As Double
    Dim etaTimestamp As Date

    If totalCount <= 0 Then
        MainBuildEtaText = "ETA n/a"
        Exit Function
    End If

    If currentCount <= 1 Then
        MainBuildEtaText = "ETA calculating..."
        Exit Function
    End If

    elapsedSeconds = MainElapsedSeconds(phaseStart)
    If elapsedSeconds <= 0 Then
        MainBuildEtaText = "ETA calculating..."
        Exit Function
    End If

    secondsPerUnit = elapsedSeconds / CDbl(currentCount)
    remainingSeconds = secondsPerUnit * CDbl(totalCount - currentCount)
    If remainingSeconds < 0 Then remainingSeconds = 0

    etaTimestamp = Now + (remainingSeconds / 86400#)
    MainBuildEtaText = "ETA " & Format$(etaTimestamp, "hh:nn:ss") & " (ca. " & MainFormatDurationHms(remainingSeconds) & " tilbage)"
End Function

Private Function MainElapsedSeconds(ByVal phaseStart As Double) As Double
    Dim nowStamp As Double

    nowStamp = Timer
    If nowStamp < phaseStart Then nowStamp = nowStamp + 86400#

    MainElapsedSeconds = nowStamp - phaseStart
End Function

Private Function MainFormatDurationHms(ByVal totalSeconds As Double) As String
    Dim wholeSeconds As Long
    Dim hours As Long
    Dim minutes As Long
    Dim seconds As Long

    If totalSeconds < 0 Then totalSeconds = 0

    wholeSeconds = CLng(totalSeconds + 0.5)
    hours = wholeSeconds \ 3600
    minutes = (wholeSeconds Mod 3600) \ 60
    seconds = wholeSeconds Mod 60

    MainFormatDurationHms = Right$("00" & CStr(hours), 2) & ":" & _
                            Right$("00" & CStr(minutes), 2) & ":" & _
                            Right$("00" & CStr(seconds), 2)
End Function

Private Function MainClampPct(ByVal value As Long) As Long
    If value < 0 Then
        MainClampPct = 0
    ElseIf value > 100 Then
        MainClampPct = 100
    Else
        MainClampPct = value
    End If
End Function
