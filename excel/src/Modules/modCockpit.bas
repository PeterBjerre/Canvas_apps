Option Explicit

Public Sub BuildCompareCockpit()
    On Error GoTo EH

    Dim wsCompareDiff As Worksheet
    Dim wsCompareSummary As Worksheet
    Dim wsCompareMap As Worksheet
    Dim wsCompareComponents As Worksheet
    Dim wsCompareAttachments As Worksheet
    Dim wsCompareLongText As Worksheet

    Dim wsCockpitDiffs As Worksheet
    Dim wsCockpitHome As Worksheet
    Dim wsCockpitOrder As Worksheet
    Dim wsCockpitDecisions As Worksheet
    Dim wsCockpitLongText As Worksheet
    Dim wsDataDiffFacts As Worksheet
    Dim wsDataDecisionFacts As Worksheet

    Set wsCompareDiff = GetWorksheetIfExists(WS_COMPARE_DIFF)
    Set wsCompareSummary = GetWorksheetIfExists(WS_COMPARE_SUMMARY)
    Set wsCompareMap = GetWorksheetIfExists(WS_COMPARE_MAP)
    Set wsCompareComponents = GetWorksheetIfExists(WS_COMPARE_COMPONENTS)
    Set wsCompareAttachments = GetWorksheetIfExists(WS_COMPARE_ATTACHMENTS)
    Set wsCompareLongText = GetWorksheetIfExists(WS_COMPARE_LONGTEXT)

    Set wsCockpitDiffs = EnsureSheet(WS_COCKPIT_DIFFS, True)
    Set wsCockpitHome = EnsureSheet(WS_COCKPIT_HOME, True)
    Set wsCockpitOrder = EnsureSheet(WS_COCKPIT_ORDER, True)
    Set wsCockpitDecisions = EnsureSheet(WS_COCKPIT_DECISIONS, False)
    Set wsCockpitLongText = EnsureSheet(WS_COCKPIT_LONGTEXT_EDITOR, False)
    Set wsDataDiffFacts = EnsureSheet(WS_DATA_DIFF_FACTS, True)
    Set wsDataDecisionFacts = EnsureSheet(WS_DATA_DECISION_FACTS, False)

    SyncDecisionFactsFromQueues wsDataDecisionFacts, wsCockpitDecisions, wsCockpitLongText

    If Not wsCompareDiff Is Nothing Then
        CopySheetValues wsCompareDiff, wsCockpitDiffs
    Else
        wsCockpitDiffs.Range("A1").Value = "Info"
        wsCockpitDiffs.Range("A2").Value = "Ingen data i " & WS_COMPARE_DIFF
        wsCockpitDiffs.Columns("A:B").AutoFit
    End If

    BuildCockpitHome wsCockpitHome, wsCompareDiff, wsCompareSummary
    BuildOrderSheet wsCockpitOrder, wsCompareMap
    BuildDiffFactsSheet wsDataDiffFacts, wsCompareDiff, wsCompareComponents, wsCompareAttachments, wsCompareLongText
    BuildDecisionFactsSheet wsDataDecisionFacts, wsDataDiffFacts
    PopulateDecisionQueueSheet wsCockpitDecisions, wsDataDecisionFacts
    PopulateLongTextQueueSheet wsCockpitLongText, wsDataDecisionFacts
    AddDecisionMetricsToHome wsCockpitHome, wsDataDecisionFacts

    Exit Sub
EH:
    Err.Raise Err.Number, "BuildCompareCockpit", Err.Description
End Sub

Private Function EnsureSheet(ByVal sheetName As String, ByVal clearIfExists As Boolean) As Worksheet
    On Error Resume Next
    Set EnsureSheet = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If EnsureSheet Is Nothing Then
        Set EnsureSheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        EnsureSheet.Name = sheetName
    ElseIf clearIfExists Then
        EnsureSheet.Cells.Clear
    End If
End Function

Private Function GetWorksheetIfExists(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set GetWorksheetIfExists = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
End Function

Private Sub CopySheetValues(ByVal sourceSheet As Worksheet, ByVal targetSheet As Worksheet)
    Dim sourceRange As Range
    Set sourceRange = GetUsedRange(sourceSheet)

    targetSheet.Cells.Clear

    If sourceRange Is Nothing Then Exit Sub

    targetSheet.Range("A1").Resize(sourceRange.Rows.Count, sourceRange.Columns.Count).Value = sourceRange.Value
    targetSheet.Rows(1).Font.Bold = True
    targetSheet.Rows(1).Interior.Color = RGB(240, 240, 240)
    targetSheet.Columns.AutoFit
End Sub

Private Function GetUsedRange(ByVal ws As Worksheet) As Range
    Dim lastRowCell As Range
    Dim lastColCell As Range

    On Error Resume Next
    Set lastRowCell = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    Set lastColCell = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    On Error GoTo 0

    If lastRowCell Is Nothing Or lastColCell Is Nothing Then Exit Function

    Set GetUsedRange = ws.Range(ws.Cells(1, 1), ws.Cells(lastRowCell.Row, lastColCell.Column))
End Function

Private Sub BuildCockpitHome(ByVal wsHome As Worksheet, ByVal wsDiff As Worksheet, ByVal wsSummary As Worksheet)
    wsHome.Cells.Clear

    wsHome.Range("A1").Value = "Metric"
    wsHome.Range("B1").Value = "Value"

    wsHome.Range("A2").Value = "Generated_At"
    wsHome.Range("B2").Value = Now

    wsHome.Range("A3").Value = "Diff_Rows"
    wsHome.Range("B3").Value = CountDataRows(wsDiff)

    wsHome.Range("A4").Value = "Orders_In_Summary"
    wsHome.Range("B4").Value = CountDataRows(wsSummary)

    wsHome.Range("A5").Value = "Compared_Total"
    wsHome.Range("B5").Value = SumSummaryMetric(wsSummary, "Compared")

    wsHome.Range("A6").Value = "Matched_Total"
    wsHome.Range("B6").Value = SumSummaryMetric(wsSummary, "Matched")

    wsHome.Range("A7").Value = "Mismatched_Total"
    wsHome.Range("B7").Value = SumSummaryMetric(wsSummary, "Mismatched")

    wsHome.Range("A8").Value = "MissingInOrder_Total"
    wsHome.Range("B8").Value = SumSummaryMetric(wsSummary, "MissingInOrder")

    wsHome.Range("A9").Value = "MissingInTask_Total"
    wsHome.Range("B9").Value = SumSummaryMetric(wsSummary, "MissingInTask")

    wsHome.Rows(1).Font.Bold = True
    wsHome.Rows(1).Interior.Color = RGB(240, 240, 240)
    wsHome.Columns("A:B").AutoFit
End Sub

Private Sub AddDecisionMetricsToHome(ByVal wsHome As Worksheet, ByVal wsDecisionFacts As Worksheet)
    Dim totalRows As Long
    Dim resolvedRows As Long

    totalRows = CountDataRows(wsDecisionFacts)
    resolvedRows = CountResolvedDecisions(wsDecisionFacts)

    wsHome.Range("A10").Value = "Decision_Rows"
    wsHome.Range("B10").Value = totalRows

    wsHome.Range("A11").Value = "Decision_Resolved"
    wsHome.Range("B11").Value = resolvedRows

    wsHome.Range("A12").Value = "Decision_Pending"
    wsHome.Range("B12").Value = totalRows - resolvedRows

    wsHome.Columns("A:B").AutoFit
End Sub

Private Function CountDataRows(ByVal ws As Worksheet) As Long
    Dim lastRow As Long

    If ws Is Nothing Then Exit Function

    lastRow = GetLastUsedRow(ws)
    If lastRow >= 2 Then CountDataRows = lastRow - 1
End Function

Private Function GetLastUsedRow(ByVal ws As Worksheet) As Long
    Dim lastCell As Range

    On Error Resume Next
    Set lastCell = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    On Error GoTo 0

    If Not lastCell Is Nothing Then GetLastUsedRow = lastCell.Row
End Function

Private Function CountResolvedDecisions(ByVal ws As Worksheet) As Long
    Dim cResolved As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function

    cResolved = FindHeaderIndex(ws, "Is_Resolved")
    If cResolved = 0 Then Exit Function

    lastRow = GetLastUsedRow(ws)
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If UCase$(Trim$(CStr(ws.Cells(r, cResolved).Value2))) = "Y" Then
            CountResolvedDecisions = CountResolvedDecisions + 1
        End If
    Next r
End Function

Private Function FindHeaderIndex(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim lastCol As Long
    Dim c As Long

    If ws Is Nothing Then Exit Function

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If lastCol < 1 Then Exit Function

    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(1, c).Value2)), headerName, vbTextCompare) = 0 Then
            FindHeaderIndex = c
            Exit Function
        End If
    Next c
End Function

Private Function SumSummaryMetric(ByVal ws As Worksheet, ByVal headerName As String) As Double
    Dim colIdx As Long
    Dim lastRow As Long
    Dim r As Long
    Dim v As Variant

    If ws Is Nothing Then Exit Function

    colIdx = FindHeaderIndex(ws, headerName)
    If colIdx = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, colIdx).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        v = ws.Cells(r, colIdx).Value2
        If IsNumeric(v) Then SumSummaryMetric = SumSummaryMetric + CDbl(v)
    Next r
End Function

Private Sub BuildOrderSheet(ByVal wsOrder As Worksheet, ByVal wsCompareMap As Worksheet)
    Dim headers As Variant
    Dim rows As Collection
    Dim cAuf As Long
    Dim cTask As Long
    Dim cMap As Long
    Dim lastRow As Long
    Dim r As Long

    headers = Array("Order_number", "Tasklist_Key", "Map_Status")
    Set rows = New Collection

    If Not wsCompareMap Is Nothing Then
        cAuf = FindHeaderIndex(wsCompareMap, "AUFNR")
        cTask = FindHeaderIndex(wsCompareMap, "Tasklist_Key")
        cMap = FindHeaderIndex(wsCompareMap, "Map_Status")

        If cAuf > 0 And cTask > 0 And cMap > 0 Then
            lastRow = GetLastUsedRow(wsCompareMap)
            For r = 2 To lastRow
                rows.Add Array(GetCellText(wsCompareMap, r, cAuf), _
                               GetCellText(wsCompareMap, r, cTask), _
                               GetCellText(wsCompareMap, r, cMap))
            Next r
        End If
    End If

    WriteRows wsOrder, headers, rows
End Sub

Private Sub BuildDiffFactsSheet(ByVal wsOut As Worksheet, _
                                ByVal wsCompareDiff As Worksheet, _
                                ByVal wsCompareComponents As Worksheet, _
                                ByVal wsCompareAttachments As Worksheet, _
                                ByVal wsCompareLongText As Worksheet)
    Dim headers As Variant
    Dim rows As Collection

    headers = Array("Diff_Key", "AUFNR", "Tasklist_Key", "Scope", "VORNR", "Sub_Key", "Field", "SAP_Value", "VH_Value", "ReasonCode")
    Set rows = New Collection

    AppendFactsFromCompareDiff rows, wsCompareDiff
    AppendFactsFromComponentSheet rows, wsCompareComponents
    AppendFactsFromAttachmentSheet rows, wsCompareAttachments
    AppendFactsFromLongTextSheet rows, wsCompareLongText

    WriteRows wsOut, headers, rows
    EnsureNamedTable wsOut, LO_DIFF_FACTS
End Sub

Private Sub AppendFactsFromCompareDiff(ByVal rows As Collection, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cVornr As Long
    Dim cField As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cReason As Long
    Dim cScope As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim scopeName As String
    Dim vornr As String
    Dim fieldName As String
    Dim sapVal As String
    Dim vhVal As String
    Dim reasonCode As String
    Dim diffKey As String

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cField = FindHeaderIndex(ws, "Field")
    cSap = FindHeaderIndex(ws, "SAP_Value")
    cVh = FindHeaderIndex(ws, "VH_Value")
    cReason = FindHeaderIndex(ws, "ReasonCode")
    cScope = FindHeaderIndex(ws, "Scope")

    If cAuf = 0 Or cTask = 0 Or cField = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        scopeName = GetCellText(ws, r, cScope)
        vornr = GetCellText(ws, r, cVornr)
        fieldName = GetCellText(ws, r, cField)
        sapVal = GetCellText(ws, r, cSap)
        vhVal = GetCellText(ws, r, cVh)
        reasonCode = GetCellText(ws, r, cReason)

        If Len(scopeName) = 0 Then scopeName = "Operation"

        Select Case UCase$(scopeName)
            Case "COMPONENT", "ATTACHMENT", "LONGTEXT"
                GoTo NextRow
        End Select

        If Len(auf) = 0 Or Len(fieldName) = 0 Then GoTo NextRow

        diffKey = BuildDiffKey(auf, task, scopeName, vornr, vbNullString, fieldName)
        rows.Add Array(diffKey, auf, task, scopeName, vornr, vbNullString, fieldName, sapVal, vhVal, reasonCode)
NextRow:
    Next r
End Sub

Private Sub AppendFactsFromComponentSheet(ByVal rows As Collection, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cVornr As Long
    Dim cMaterial As Long
    Dim cStatus As Long
    Dim cOrderQty As Long
    Dim cTaskQty As Long
    Dim cOrderUn As Long
    Dim cTaskUn As Long
    Dim cOrderDesc As Long
    Dim cTaskDesc As Long
    Dim cReasons As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim vornr As String
    Dim material As String
    Dim status As String
    Dim mismatchReasons As String
    Dim sapVal As String
    Dim vhVal As String
    Dim fieldName As String
    Dim reasonCode As String
    Dim token As Variant
    Dim tokens As Collection
    Dim diffKey As String
    Dim addedAny As Boolean

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cMaterial = FindHeaderIndex(ws, "Material")
    cStatus = FindHeaderIndex(ws, "Compare_Status")
    cOrderQty = FindHeaderIndex(ws, "Order_Quantity")
    cTaskQty = FindHeaderIndex(ws, "Task_Quantity")
    cOrderUn = FindHeaderIndex(ws, "Order_Un")
    cTaskUn = FindHeaderIndex(ws, "Task_Un")
    cOrderDesc = FindHeaderIndex(ws, "Order_Description")
    cTaskDesc = FindHeaderIndex(ws, "Task_Description")
    cReasons = FindHeaderIndex(ws, "Mismatch_Reasons")

    If cAuf = 0 Or cTask = 0 Or cStatus = 0 Or cMaterial = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        status = UCase$(GetCellText(ws, r, cStatus))
        If Len(status) = 0 Or status = "MATCH" Then GoTo NextRow

        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        vornr = GetCellText(ws, r, cVornr)
        material = GetCellText(ws, r, cMaterial)

        If status = "MISSING_IN_ORDER" Then
            diffKey = BuildDiffKey(auf, task, "Component", vornr, material, "COMPONENT")
            rows.Add Array(diffKey, auf, task, "Component", vornr, material, "COMPONENT", vbNullString, material, status)
            GoTo NextRow
        End If

        If status = "MISSING_IN_TASKLIST" Then
            diffKey = BuildDiffKey(auf, task, "Component", vornr, material, "COMPONENT")
            rows.Add Array(diffKey, auf, task, "Component", vornr, material, "COMPONENT", material, vbNullString, status)
            GoTo NextRow
        End If

        mismatchReasons = GetCellText(ws, r, cReasons)
        Set tokens = ParseReasonTokens(mismatchReasons)
        addedAny = False

        For Each token In tokens
            fieldName = vbNullString
            sapVal = vbNullString
            vhVal = vbNullString
            reasonCode = "MISMATCH"

            Select Case CStr(token)
                Case "QTY"
                    fieldName = "COMPONENT_QTY"
                    sapVal = GetCellText(ws, r, cOrderQty)
                    vhVal = GetCellText(ws, r, cTaskQty)
                Case "UNIT"
                    fieldName = "COMPONENT_UN"
                    sapVal = GetCellText(ws, r, cOrderUn)
                    vhVal = GetCellText(ws, r, cTaskUn)
                Case "DESC"
                    fieldName = "COMPONENT_DESC"
                    sapVal = GetCellText(ws, r, cOrderDesc)
                    vhVal = GetCellText(ws, r, cTaskDesc)
                Case Else
                    fieldName = "COMPONENT_" & CStr(token)
            End Select

            If Len(fieldName) > 0 Then
                diffKey = BuildDiffKey(auf, task, "Component", vornr, material, fieldName)
                rows.Add Array(diffKey, auf, task, "Component", vornr, material, fieldName, sapVal, vhVal, reasonCode)
                addedAny = True
            End If
        Next token

        If Not addedAny Then
            diffKey = BuildDiffKey(auf, task, "Component", vornr, material, "COMPONENT")
            rows.Add Array(diffKey, auf, task, "Component", vornr, material, "COMPONENT", _
                           GetCellText(ws, r, cOrderQty), GetCellText(ws, r, cTaskQty), status)
        End If
NextRow:
    Next r
End Sub

Private Sub AppendFactsFromAttachmentSheet(ByVal rows As Collection, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cVornr As Long
    Dim cDoc As Long
    Dim cStatus As Long
    Dim cOrderDesc As Long
    Dim cTaskDesc As Long
    Dim cOrderOrig As Long
    Dim cTaskOrig As Long
    Dim cReasons As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim vornr As String
    Dim docId As String
    Dim status As String
    Dim mismatchReasons As String
    Dim token As Variant
    Dim tokens As Collection
    Dim fieldName As String
    Dim sapVal As String
    Dim vhVal As String
    Dim reasonCode As String
    Dim diffKey As String
    Dim addedAny As Boolean

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cDoc = FindHeaderIndex(ws, "Document")
    cStatus = FindHeaderIndex(ws, "Compare_Status")
    cOrderDesc = FindHeaderIndex(ws, "Order_Description")
    cTaskDesc = FindHeaderIndex(ws, "Task_Description")
    cOrderOrig = FindHeaderIndex(ws, "Order_Original")
    cTaskOrig = FindHeaderIndex(ws, "Task_Original")
    cReasons = FindHeaderIndex(ws, "Mismatch_Reasons")

    If cAuf = 0 Or cTask = 0 Or cStatus = 0 Or cDoc = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        status = UCase$(GetCellText(ws, r, cStatus))
        If Len(status) = 0 Or status = "MATCH" Then GoTo NextRow

        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        vornr = GetCellText(ws, r, cVornr)
        docId = GetCellText(ws, r, cDoc)

        If status = "MISSING_IN_ORDER" Then
            diffKey = BuildDiffKey(auf, task, "Attachment", vornr, docId, "ATTACHMENT")
            rows.Add Array(diffKey, auf, task, "Attachment", vornr, docId, "ATTACHMENT", vbNullString, docId, status)
            GoTo NextRow
        End If

        If status = "MISSING_IN_TASKLIST" Then
            diffKey = BuildDiffKey(auf, task, "Attachment", vornr, docId, "ATTACHMENT")
            rows.Add Array(diffKey, auf, task, "Attachment", vornr, docId, "ATTACHMENT", docId, vbNullString, status)
            GoTo NextRow
        End If

        mismatchReasons = GetCellText(ws, r, cReasons)
        Set tokens = ParseReasonTokens(mismatchReasons)
        addedAny = False

        For Each token In tokens
            fieldName = vbNullString
            sapVal = vbNullString
            vhVal = vbNullString
            reasonCode = "MISMATCH"

            Select Case CStr(token)
                Case "DESC"
                    fieldName = "ATTACH_DESC"
                    sapVal = GetCellText(ws, r, cOrderDesc)
                    vhVal = GetCellText(ws, r, cTaskDesc)
                Case "ORIGINAL"
                    fieldName = "ATTACH_ORIGINAL"
                    sapVal = GetCellText(ws, r, cOrderOrig)
                    vhVal = GetCellText(ws, r, cTaskOrig)
                Case Else
                    fieldName = "ATTACH_" & CStr(token)
            End Select

            If Len(fieldName) > 0 Then
                diffKey = BuildDiffKey(auf, task, "Attachment", vornr, docId, fieldName)
                rows.Add Array(diffKey, auf, task, "Attachment", vornr, docId, fieldName, sapVal, vhVal, reasonCode)
                addedAny = True
            End If
        Next token

        If Not addedAny Then
            diffKey = BuildDiffKey(auf, task, "Attachment", vornr, docId, "ATTACHMENT")
            rows.Add Array(diffKey, auf, task, "Attachment", vornr, docId, "ATTACHMENT", _
                           GetCellText(ws, r, cOrderDesc), GetCellText(ws, r, cTaskDesc), status)
        End If
NextRow:
    Next r
End Sub

Private Sub AppendFactsFromLongTextSheet(ByVal rows As Collection, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cVornr As Long
    Dim cField As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cReason As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim vornr As String
    Dim fieldName As String
    Dim sapVal As String
    Dim vhVal As String
    Dim reasonCode As String
    Dim diffKey As String

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cField = FindHeaderIndex(ws, "Field")
    cSap = FindHeaderIndex(ws, "SAP_Value")
    cVh = FindHeaderIndex(ws, "VH_Value")
    cReason = FindHeaderIndex(ws, "ReasonCode")

    If cAuf = 0 Or cTask = 0 Or cField = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        vornr = GetCellText(ws, r, cVornr)
        fieldName = GetCellText(ws, r, cField)
        sapVal = GetCellText(ws, r, cSap)
        vhVal = GetCellText(ws, r, cVh)
        reasonCode = GetCellText(ws, r, cReason)

        If Len(auf) = 0 Or Len(fieldName) = 0 Then GoTo NextRow

        diffKey = BuildDiffKey(auf, task, "LongText", vornr, vbNullString, fieldName)
        rows.Add Array(diffKey, auf, task, "LongText", vornr, vbNullString, fieldName, sapVal, vhVal, reasonCode)
NextRow:
    Next r
End Sub

Private Sub BuildDecisionFactsSheet(ByVal wsOut As Worksheet, ByVal wsDiffFacts As Worksheet)
    Dim previous As Object
    Dim headers As Variant
    Dim rows As Collection
    Dim cKey As Long
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cReason As Long
    Dim lastRow As Long
    Dim r As Long
    Dim diffKey As String
    Dim auf As String
    Dim task As String
    Dim scopeName As String
    Dim vornr As String
    Dim subKey As String
    Dim fieldName As String
    Dim sapVal As String
    Dim vhVal As String
    Dim reasonCode As String
    Dim decision As String
    Dim manualValue As String
    Dim changedBy As String
    Dim changedAt As Variant
    Dim comment As String
    Dim prevVals As Variant

    headers = Array("Diff_Key", "AUFNR", "Tasklist_Key", "Scope", "VORNR", "Sub_Key", "Field", "SAP_Value", "VH_Value", "ReasonCode", _
                    "Decision", "Manual_Value", "Changed_By", "Changed_At", "Comment", "Is_Resolved")

    Set previous = ReadExistingDecisionValues(wsOut)
    Set rows = New Collection

    If wsDiffFacts Is Nothing Then
        WriteRows wsOut, headers, rows
        EnsureNamedTable wsOut, LO_DECISION_FACTS
        Exit Sub
    End If

    cKey = FindHeaderIndex(wsDiffFacts, "Diff_Key")
    cAuf = FindHeaderIndex(wsDiffFacts, "AUFNR")
    cTask = FindHeaderIndex(wsDiffFacts, "Tasklist_Key")
    cScope = FindHeaderIndex(wsDiffFacts, "Scope")
    cVornr = FindHeaderIndex(wsDiffFacts, "VORNR")
    cSub = FindHeaderIndex(wsDiffFacts, "Sub_Key")
    cField = FindHeaderIndex(wsDiffFacts, "Field")
    cSap = FindHeaderIndex(wsDiffFacts, "SAP_Value")
    cVh = FindHeaderIndex(wsDiffFacts, "VH_Value")
    cReason = FindHeaderIndex(wsDiffFacts, "ReasonCode")

    If cAuf = 0 Or cTask = 0 Or cField = 0 Then
        WriteRows wsOut, headers, rows
        EnsureNamedTable wsOut, LO_DECISION_FACTS
        Exit Sub
    End If

    lastRow = GetLastUsedRow(wsDiffFacts)
    For r = 2 To lastRow
        diffKey = GetCellText(wsDiffFacts, r, cKey)
        auf = GetCellText(wsDiffFacts, r, cAuf)
        task = GetCellText(wsDiffFacts, r, cTask)
        scopeName = GetCellText(wsDiffFacts, r, cScope)
        vornr = GetCellText(wsDiffFacts, r, cVornr)
        subKey = GetCellText(wsDiffFacts, r, cSub)
        fieldName = GetCellText(wsDiffFacts, r, cField)
        sapVal = GetCellText(wsDiffFacts, r, cSap)
        vhVal = GetCellText(wsDiffFacts, r, cVh)
        reasonCode = GetCellText(wsDiffFacts, r, cReason)

        If Len(diffKey) = 0 Then
            diffKey = BuildDiffKey(auf, task, scopeName, vornr, subKey, fieldName)
        End If

        decision = vbNullString
        manualValue = vbNullString
        changedBy = vbNullString
        changedAt = vbNullString
        comment = vbNullString

        If previous.Exists(diffKey) Then
            prevVals = previous(diffKey)
            decision = CStr(prevVals(0))
            manualValue = CStr(prevVals(1))
            changedBy = CStr(prevVals(2))
            changedAt = prevVals(3)
            comment = CStr(prevVals(4))
        End If

        rows.Add Array(diffKey, auf, task, scopeName, vornr, subKey, fieldName, sapVal, vhVal, reasonCode, _
                       decision, manualValue, changedBy, changedAt, comment, IIf(DecisionIsResolved(decision, manualValue), "Y", "N"))
    Next r

    WriteRows wsOut, headers, rows
    EnsureNamedTable wsOut, LO_DECISION_FACTS
End Sub

Private Sub SyncDecisionFactsFromQueues(ByVal wsDecisionFacts As Worksheet, _
                                        ByVal wsDecisionQueue As Worksheet, _
                                        ByVal wsLongTextQueue As Worksheet)
    Dim updates As Object
    Dim cKey As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cComment As Long
    Dim cResolved As Long
    Dim lastRow As Long
    Dim r As Long
    Dim keyVal As String
    Dim oldDecision As String
    Dim oldManual As String
    Dim oldComment As String
    Dim newDecision As String
    Dim newManual As String
    Dim newComment As String
    Dim changedByVal As String
    Dim changedAtVal As Variant
    Dim updateVals As Variant
    Dim hasChange As Boolean

    If wsDecisionFacts Is Nothing Then Exit Sub

    Set updates = CreateObject("Scripting.Dictionary")
    updates.CompareMode = vbTextCompare

    LoadQueueUpdatesFromDecisionSheet updates, wsDecisionQueue
    LoadQueueUpdatesFromLongTextSheet updates, wsLongTextQueue

    If updates.Count = 0 Then Exit Sub

    cKey = FindHeaderIndex(wsDecisionFacts, "Diff_Key")
    cDecision = FindHeaderIndex(wsDecisionFacts, "Decision")
    cManual = FindHeaderIndex(wsDecisionFacts, "Manual_Value")
    cChangedBy = FindHeaderIndex(wsDecisionFacts, "Changed_By")
    cChangedAt = FindHeaderIndex(wsDecisionFacts, "Changed_At")
    cComment = FindHeaderIndex(wsDecisionFacts, "Comment")
    cResolved = FindHeaderIndex(wsDecisionFacts, "Is_Resolved")

    If cKey = 0 Or cDecision = 0 Or cManual = 0 Then Exit Sub

    lastRow = GetLastUsedRow(wsDecisionFacts)
    If lastRow < 2 Then Exit Sub

    For r = 2 To lastRow
        keyVal = GetCellText(wsDecisionFacts, r, cKey)
        If Len(keyVal) = 0 Then GoTo NextRow
        If Not updates.Exists(keyVal) Then GoTo NextRow

        updateVals = updates(keyVal)
        newDecision = CStr(updateVals(0))
        newManual = CStr(updateVals(1))
        changedByVal = CStr(updateVals(2))
        changedAtVal = updateVals(3)
        newComment = CStr(updateVals(4))

        oldDecision = GetCellText(wsDecisionFacts, r, cDecision)
        oldManual = GetCellText(wsDecisionFacts, r, cManual)
        oldComment = GetCellText(wsDecisionFacts, r, cComment)

        hasChange = (StrComp(oldDecision, newDecision, vbTextCompare) <> 0) Or _
                    (StrComp(oldManual, newManual, vbBinaryCompare) <> 0) Or _
                    (StrComp(oldComment, newComment, vbBinaryCompare) <> 0)

        If hasChange Then
            wsDecisionFacts.Cells(r, cDecision).Value = newDecision
            wsDecisionFacts.Cells(r, cManual).Value = newManual
            If cComment > 0 Then wsDecisionFacts.Cells(r, cComment).Value = newComment

            If cChangedBy > 0 Then
                If Len(changedByVal) = 0 Then changedByVal = Environ$("Username")
                wsDecisionFacts.Cells(r, cChangedBy).Value = changedByVal
            End If

            If cChangedAt > 0 Then
                If Len(Trim$(CStr(changedAtVal))) = 0 Then changedAtVal = Now
                wsDecisionFacts.Cells(r, cChangedAt).Value = changedAtVal
            End If
        End If

        If cResolved > 0 Then
            wsDecisionFacts.Cells(r, cResolved).Value = IIf(DecisionIsResolved(newDecision, newManual), "Y", "N")
        End If
NextRow:
    Next r
End Sub

Private Sub LoadQueueUpdatesFromDecisionSheet(ByVal updates As Object, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cComment As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim scopeName As String
    Dim vornr As String
    Dim subKey As String
    Dim fieldName As String
    Dim decision As String
    Dim manualValue As String
    Dim changedByVal As String
    Dim changedAtVal As Variant
    Dim commentText As String
    Dim keyVal As String

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "Order_number")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cScope = FindHeaderIndex(ws, "Scope")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cSub = FindHeaderIndex(ws, "Sub_Key")
    cField = FindHeaderIndex(ws, "Field")
    cDecision = FindHeaderIndex(ws, "Decision")
    cManual = FindHeaderIndex(ws, "Manual_Value")
    cChangedBy = FindHeaderIndex(ws, "Changed_By")
    cChangedAt = FindHeaderIndex(ws, "Changed_At")
    cComment = FindHeaderIndex(ws, "Comment")

    If cAuf = 0 Or cTask = 0 Or cScope = 0 Or cField = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        decision = UCase$(GetCellText(ws, r, cDecision))
        manualValue = GetCellText(ws, r, cManual)
        commentText = GetCellText(ws, r, cComment)

        If Len(decision) = 0 And Len(manualValue) = 0 And Len(commentText) = 0 Then GoTo NextRow

        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        scopeName = GetCellText(ws, r, cScope)
        vornr = GetCellText(ws, r, cVornr)
        subKey = GetCellText(ws, r, cSub)
        fieldName = GetCellText(ws, r, cField)

        If Len(scopeName) = 0 Then scopeName = "Operation"

        keyVal = BuildDiffKey(auf, task, scopeName, vornr, subKey, fieldName)
        If Len(keyVal) = 0 Then GoTo NextRow

        changedByVal = GetCellText(ws, r, cChangedBy)
        changedAtVal = vbNullString
        If cChangedAt > 0 Then changedAtVal = ws.Cells(r, cChangedAt).Value

        updates(keyVal) = Array(decision, manualValue, changedByVal, changedAtVal, commentText)
NextRow:
    Next r
End Sub

Private Sub LoadQueueUpdatesFromLongTextSheet(ByVal updates As Object, ByVal ws As Worksheet)
    Dim cAuf As Long
    Dim cTask As Long
    Dim cVornr As Long
    Dim cField As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim lastRow As Long
    Dim r As Long
    Dim auf As String
    Dim task As String
    Dim vornr As String
    Dim fieldName As String
    Dim decision As String
    Dim manualValue As String
    Dim keyVal As String
    Dim existing As Variant

    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "Order_number")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cField = FindHeaderIndex(ws, "Scope")
    cDecision = FindHeaderIndex(ws, "Decision")
    cManual = FindHeaderIndex(ws, "Manual_Value")

    If cAuf = 0 Or cTask = 0 Or cField = 0 Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    For r = 2 To lastRow
        decision = UCase$(GetCellText(ws, r, cDecision))
        manualValue = GetCellText(ws, r, cManual)
        If Len(decision) = 0 And Len(manualValue) = 0 Then GoTo NextRow

        auf = GetCellText(ws, r, cAuf)
        task = GetCellText(ws, r, cTask)
        vornr = GetCellText(ws, r, cVornr)
        fieldName = GetCellText(ws, r, cField)

        keyVal = BuildDiffKey(auf, task, "LongText", vornr, vbNullString, fieldName)
        If Len(keyVal) = 0 Then GoTo NextRow

        If updates.Exists(keyVal) Then
            existing = updates(keyVal)
            updates(keyVal) = Array(decision, manualValue, CStr(existing(2)), existing(3), CStr(existing(4)))
        Else
            updates(keyVal) = Array(decision, manualValue, vbNullString, vbNullString, vbNullString)
        End If
NextRow:
    Next r
End Sub

Private Function ReadExistingDecisionValues(ByVal ws As Worksheet) As Object
    Dim d As Object
    Dim cKey As Long
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cComment As Long
    Dim lastRow As Long
    Dim r As Long
    Dim keyVal As String
    Dim changedAtValue As Variant

    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    If ws Is Nothing Then
        Set ReadExistingDecisionValues = d
        Exit Function
    End If

    lastRow = GetLastUsedRow(ws)
    If lastRow < 2 Then
        Set ReadExistingDecisionValues = d
        Exit Function
    End If

    cKey = FindHeaderIndex(ws, "Diff_Key")
    cAuf = FindHeaderIndex(ws, "AUFNR")
    cTask = FindHeaderIndex(ws, "Tasklist_Key")
    cScope = FindHeaderIndex(ws, "Scope")
    cVornr = FindHeaderIndex(ws, "VORNR")
    cSub = FindHeaderIndex(ws, "Sub_Key")
    cField = FindHeaderIndex(ws, "Field")
    cDecision = FindHeaderIndex(ws, "Decision")
    cManual = FindHeaderIndex(ws, "Manual_Value")
    cChangedBy = FindHeaderIndex(ws, "Changed_By")
    cChangedAt = FindHeaderIndex(ws, "Changed_At")
    cComment = FindHeaderIndex(ws, "Comment")

    For r = 2 To lastRow
        keyVal = GetCellText(ws, r, cKey)
        If Len(keyVal) = 0 Then
            keyVal = BuildDiffKey(GetCellText(ws, r, cAuf), _
                                  GetCellText(ws, r, cTask), _
                                  GetCellText(ws, r, cScope), _
                                  GetCellText(ws, r, cVornr), _
                                  GetCellText(ws, r, cSub), _
                                  GetCellText(ws, r, cField))
        End If

        If Len(keyVal) = 0 Then GoTo NextRow

        changedAtValue = vbNullString
        If cChangedAt > 0 Then changedAtValue = ws.Cells(r, cChangedAt).Value

        d(keyVal) = Array(GetCellText(ws, r, cDecision), _
                          GetCellText(ws, r, cManual), _
                          GetCellText(ws, r, cChangedBy), _
                          changedAtValue, _
                          GetCellText(ws, r, cComment))
NextRow:
    Next r

    Set ReadExistingDecisionValues = d
End Function

Private Sub PopulateDecisionQueueSheet(ByVal wsQueue As Worksheet, ByVal wsDecisionFacts As Worksheet)
    Dim headers As Variant
    Dim rows As Collection
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cComment As Long
    Dim lastRow As Long
    Dim r As Long

    headers = Array("Order_number", "Tasklist_Key", "Scope", "VORNR", "Sub_Key", "Field", "Decision", "Manual_Value", "Changed_By", "Changed_At", "Comment")
    Set rows = New Collection

    If Not wsDecisionFacts Is Nothing Then
        cAuf = FindHeaderIndex(wsDecisionFacts, "AUFNR")
        cTask = FindHeaderIndex(wsDecisionFacts, "Tasklist_Key")
        cScope = FindHeaderIndex(wsDecisionFacts, "Scope")
        cVornr = FindHeaderIndex(wsDecisionFacts, "VORNR")
        cSub = FindHeaderIndex(wsDecisionFacts, "Sub_Key")
        cField = FindHeaderIndex(wsDecisionFacts, "Field")
        cDecision = FindHeaderIndex(wsDecisionFacts, "Decision")
        cManual = FindHeaderIndex(wsDecisionFacts, "Manual_Value")
        cChangedBy = FindHeaderIndex(wsDecisionFacts, "Changed_By")
        cChangedAt = FindHeaderIndex(wsDecisionFacts, "Changed_At")
        cComment = FindHeaderIndex(wsDecisionFacts, "Comment")

        lastRow = GetLastUsedRow(wsDecisionFacts)
        For r = 2 To lastRow
            rows.Add Array(GetCellText(wsDecisionFacts, r, cAuf), _
                           GetCellText(wsDecisionFacts, r, cTask), _
                           GetCellText(wsDecisionFacts, r, cScope), _
                           GetCellText(wsDecisionFacts, r, cVornr), _
                           GetCellText(wsDecisionFacts, r, cSub), _
                           GetCellText(wsDecisionFacts, r, cField), _
                           GetCellText(wsDecisionFacts, r, cDecision), _
                           GetCellText(wsDecisionFacts, r, cManual), _
                           GetCellText(wsDecisionFacts, r, cChangedBy), _
                           GetCellText(wsDecisionFacts, r, cChangedAt), _
                           GetCellText(wsDecisionFacts, r, cComment))
        Next r
    End If

    WriteRows wsQueue, headers, rows

    If rows.Count > 0 Then
        With wsQueue.Range("G2:G" & CStr(rows.Count + 1)).Validation
            .Delete
            .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, Operator:=xlBetween, Formula1:="SAP,VH,MANUAL"
            .IgnoreBlank = True
            .InCellDropdown = True
            .ErrorTitle = "Ugyldigt valg"
            .ErrorMessage = "Vaelg SAP, VH eller MANUAL"
        End With
    End If

    EnsureNamedTable wsQueue, LO_DECISION_QUEUE
End Sub

Private Sub PopulateLongTextQueueSheet(ByVal wsQueue As Worksheet, ByVal wsDecisionFacts As Worksheet)
    Dim headers As Variant
    Dim rows As Collection
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cField As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim lastRow As Long
    Dim r As Long

    headers = Array("Order_number", "Tasklist_Key", "VORNR", "Scope", "SAP_Value", "VH_Value", "Decision", "Manual_Value")
    Set rows = New Collection

    If Not wsDecisionFacts Is Nothing Then
        cAuf = FindHeaderIndex(wsDecisionFacts, "AUFNR")
        cTask = FindHeaderIndex(wsDecisionFacts, "Tasklist_Key")
        cScope = FindHeaderIndex(wsDecisionFacts, "Scope")
        cVornr = FindHeaderIndex(wsDecisionFacts, "VORNR")
        cField = FindHeaderIndex(wsDecisionFacts, "Field")
        cSap = FindHeaderIndex(wsDecisionFacts, "SAP_Value")
        cVh = FindHeaderIndex(wsDecisionFacts, "VH_Value")
        cDecision = FindHeaderIndex(wsDecisionFacts, "Decision")
        cManual = FindHeaderIndex(wsDecisionFacts, "Manual_Value")

        lastRow = GetLastUsedRow(wsDecisionFacts)
        For r = 2 To lastRow
            If UCase$(GetCellText(wsDecisionFacts, r, cScope)) = "LONGTEXT" Then
                rows.Add Array(GetCellText(wsDecisionFacts, r, cAuf), _
                               GetCellText(wsDecisionFacts, r, cTask), _
                               GetCellText(wsDecisionFacts, r, cVornr), _
                               GetCellText(wsDecisionFacts, r, cField), _
                               GetCellText(wsDecisionFacts, r, cSap), _
                               GetCellText(wsDecisionFacts, r, cVh), _
                               GetCellText(wsDecisionFacts, r, cDecision), _
                               GetCellText(wsDecisionFacts, r, cManual))
            End If
        Next r
    End If

    WriteRows wsQueue, headers, rows

    If rows.Count > 0 Then
        With wsQueue.Range("G2:G" & CStr(rows.Count + 1)).Validation
            .Delete
            .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, Operator:=xlBetween, Formula1:="SAP,VH,MANUAL"
            .IgnoreBlank = True
            .InCellDropdown = True
            .ErrorTitle = "Ugyldigt valg"
            .ErrorMessage = "Vaelg SAP, VH eller MANUAL"
        End With
    End If

    EnsureNamedTable wsQueue, LO_LONGTEXT_QUEUE
End Sub

Private Sub WriteRows(ByVal ws As Worksheet, ByVal headers As Variant, ByVal rows As Collection)
    Dim colCount As Long
    Dim hdrArr() As Variant
    Dim arrOut() As Variant
    Dim i As Long
    Dim r As Long
    Dim c As Long
    Dim rowArr As Variant

    ws.Cells.Clear

    colCount = UBound(headers) - LBound(headers) + 1
    ReDim hdrArr(1 To 1, 1 To colCount)

    For i = LBound(headers) To UBound(headers)
        hdrArr(1, i - LBound(headers) + 1) = headers(i)
    Next i

    ws.Range("A1").Resize(1, colCount).Value = hdrArr

    If rows.Count > 0 Then
        ReDim arrOut(1 To rows.Count, 1 To colCount)
        For r = 1 To rows.Count
            rowArr = rows(r)
            For c = 0 To UBound(rowArr)
                If c < colCount Then arrOut(r, c + 1) = rowArr(c)
            Next c
        Next r
        ws.Range("A2").Resize(rows.Count, colCount).Value = arrOut
    End If

    With ws.UsedRange
        .Columns.AutoFit
        .Rows(1).Font.Bold = True
        .Rows(1).Interior.Color = RGB(240, 240, 240)
    End With
End Sub

Private Function ParseReasonTokens(ByVal reasonList As String) As Collection
    Dim tokens As Collection
    Dim parts() As String
    Dim i As Long
    Dim token As String

    Set tokens = New Collection
    reasonList = Trim$(reasonList)

    If Len(reasonList) = 0 Then
        Set ParseReasonTokens = tokens
        Exit Function
    End If

    parts = Split(reasonList, ",")
    For i = LBound(parts) To UBound(parts)
        token = UCase$(Trim$(parts(i)))
        If Len(token) > 0 Then tokens.Add token
    Next i

    Set ParseReasonTokens = tokens
End Function

Private Function BuildDiffKey(ByVal auf As String, ByVal task As String, ByVal scopeName As String, _
                              ByVal vornr As String, ByVal subKey As String, ByVal fieldName As String) As String
    BuildDiffKey = UCase$(Trim$(auf)) & "|" & UCase$(Trim$(task)) & "|" & UCase$(Trim$(scopeName)) & "|" & _
                   UCase$(Trim$(vornr)) & "|" & UCase$(Trim$(subKey)) & "|" & UCase$(Trim$(fieldName))
End Function

Private Function DecisionIsResolved(ByVal decision As String, ByVal manualValue As String) As Boolean
    decision = UCase$(Trim$(decision))
    manualValue = Trim$(manualValue)

    Select Case decision
        Case "SAP", "VH"
            DecisionIsResolved = True
        Case "MANUAL"
            DecisionIsResolved = (Len(manualValue) > 0)
    End Select
End Function

Private Function GetCellText(ByVal ws As Worksheet, ByVal rowNo As Long, ByVal colNo As Long) As String
    If ws Is Nothing Then Exit Function
    If colNo <= 0 Then Exit Function
    GetCellText = Trim$(CStr(ws.Cells(rowNo, colNo).Value2))
End Function

Private Sub EnsureNamedTable(ByVal ws As Worksheet, ByVal tableName As String)
    Dim lastRow As Long
    Dim lastCol As Long
    Dim rng As Range
    Dim lo As ListObject

    If ws Is Nothing Then Exit Sub

    DeleteNamedTableIfExists tableName

    lastRow = GetLastUsedRow(ws)
    If lastRow = 0 Then Exit Sub

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If lastCol = 0 Then Exit Sub

    Set rng = ws.Range(ws.Cells(1, 1), ws.Cells(lastRow, lastCol))
    Set lo = ws.ListObjects.Add(xlSrcRange, rng, , xlYes)
    lo.Name = tableName

    On Error Resume Next
    lo.TableStyle = "TableStyleLight9"
    On Error GoTo 0
End Sub

Private Sub DeleteNamedTableIfExists(ByVal tableName As String)
    Dim ws As Worksheet
    Dim lo As ListObject

    For Each ws In ThisWorkbook.Worksheets
        For Each lo In ws.ListObjects
            If StrComp(lo.Name, tableName, vbTextCompare) = 0 Then
                lo.Delete
                Exit Sub
            End If
        Next lo
    Next ws
End Sub

Public Sub ApplyCockpitDecisions()
    On Error GoTo EH

    Dim wsFacts As Worksheet
    Dim wsQueue As Worksheet
    Dim wsLongText As Worksheet
    Dim wsHome As Worksheet
    Dim cDecision As Long
    Dim cManual As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cResolved As Long
    Dim cFinal As Long
    Dim cAction As Long
    Dim cPushReady As Long
    Dim cAppliedAt As Long
    Dim lastRow As Long
    Dim r As Long
    Dim decision As String
    Dim manualValue As String
    Dim finalValue As String
    Dim actionCode As String
    Dim pushReady As String
    Dim resolvedCount As Long
    Dim pendingCount As Long

    Set wsFacts = GetWorksheetIfExists(WS_DATA_DECISION_FACTS)
    If wsFacts Is Nothing Then
        MsgBox "Ingen beslutningsdata fundet. Koer compare cockpit foerst.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    Set wsQueue = EnsureSheet(WS_COCKPIT_DECISIONS, False)
    Set wsLongText = EnsureSheet(WS_COCKPIT_LONGTEXT_EDITOR, False)
    Set wsHome = EnsureSheet(WS_COCKPIT_HOME, False)

    SyncDecisionFactsFromQueues wsFacts, wsQueue, wsLongText

    cDecision = FindHeaderIndex(wsFacts, "Decision")
    cManual = FindHeaderIndex(wsFacts, "Manual_Value")
    cSap = FindHeaderIndex(wsFacts, "SAP_Value")
    cVh = FindHeaderIndex(wsFacts, "VH_Value")
    cChangedBy = FindHeaderIndex(wsFacts, "Changed_By")
    cChangedAt = FindHeaderIndex(wsFacts, "Changed_At")
    cResolved = FindHeaderIndex(wsFacts, "Is_Resolved")
    cFinal = EnsureHeaderColumn(wsFacts, "Final_Value")
    cAction = EnsureHeaderColumn(wsFacts, "Apply_Action")
    cPushReady = EnsureHeaderColumn(wsFacts, "Push_Ready")
    cAppliedAt = EnsureHeaderColumn(wsFacts, "Applied_At")

    If cDecision = 0 Or cManual = 0 Or cSap = 0 Or cVh = 0 Then
        MsgBox "Data_Decision_Facts mangler noedvendige kolonner.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    lastRow = GetLastUsedRow(wsFacts)
    If lastRow < 2 Then
        MsgBox "Ingen rækker at anvende i Data_Decision_Facts.", vbInformation, APP_TITLE
        Exit Sub
    End If

    For r = 2 To lastRow
        decision = UCase$(GetCellText(wsFacts, r, cDecision))
        manualValue = GetCellText(wsFacts, r, cManual)
        finalValue = vbNullString
        actionCode = "PENDING_DECISION"
        pushReady = "N"

        Select Case decision
            Case "SAP"
                finalValue = GetCellText(wsFacts, r, cSap)
                actionCode = "USE_SAP"
                pushReady = "Y"
            Case "VH"
                finalValue = GetCellText(wsFacts, r, cVh)
                actionCode = "USE_VH"
                pushReady = "Y"
            Case "MANUAL"
                If Len(Trim$(manualValue)) > 0 Then
                    finalValue = manualValue
                    actionCode = "USE_MANUAL"
                    pushReady = "Y"
                Else
                    actionCode = "MANUAL_MISSING_VALUE"
                    pushReady = "N"
                End If
            Case Else
                actionCode = "PENDING_DECISION"
                pushReady = "N"
        End Select

        wsFacts.Cells(r, cFinal).Value = finalValue
        wsFacts.Cells(r, cAction).Value = actionCode
        wsFacts.Cells(r, cPushReady).Value = pushReady
        wsFacts.Cells(r, cAppliedAt).Value = Now

        If cResolved > 0 Then
            wsFacts.Cells(r, cResolved).Value = IIf(pushReady = "Y", "Y", "N")
        End If

        If cChangedBy > 0 Then
            If Len(Trim$(CStr(wsFacts.Cells(r, cChangedBy).Value))) = 0 And Len(decision) > 0 Then
                wsFacts.Cells(r, cChangedBy).Value = Environ$("Username")
            End If
        End If

        If cChangedAt > 0 Then
            If Len(Trim$(CStr(wsFacts.Cells(r, cChangedAt).Value))) = 0 And Len(decision) > 0 Then
                wsFacts.Cells(r, cChangedAt).Value = Now
            End If
        End If

        If pushReady = "Y" Then
            resolvedCount = resolvedCount + 1
        Else
            pendingCount = pendingCount + 1
        End If
    Next r

    EnsureNamedTable wsFacts, LO_DECISION_FACTS
    PopulateDecisionQueueSheet wsQueue, wsFacts
    PopulateLongTextQueueSheet wsLongText, wsFacts
    AddDecisionMetricsToHome wsHome, wsFacts

    MsgBox "Apply fuldfoert." & vbCrLf & _
           "Klar til push: " & CStr(resolvedCount) & vbCrLf & _
           "Afventer beslutning: " & CStr(pendingCount), vbInformation, APP_TITLE
    Exit Sub

EH:
    MsgBox "ApplyCockpitDecisions fejlede: " & Err.Description, vbExclamation, APP_TITLE
End Sub

Public Sub PushReadyDecisionsToPowerAutomate()
    ExecutePushReadyDecisions False
End Sub

Public Sub PreviewPushReadyDecisions()
    ExecutePushReadyDecisions True
End Sub

Private Sub ExecutePushReadyDecisions(ByVal dryRun As Boolean)
    On Error GoTo EH

    Dim wsFacts As Worksheet
    Dim wsHome As Worksheet
    Dim cPushReady As Long
    Dim cApplyAction As Long
    Dim cPushStatus As Long
    Dim cPushedAt As Long
    Dim r As Long
    Dim readyRows As Collection
    Dim payload As String
    Dim url As String
    Dim http As Object

    Set wsFacts = GetWorksheetIfExists(WS_DATA_DECISION_FACTS)
    If wsFacts Is Nothing Then
        MsgBox "Data_Decision_Facts findes ikke. Koer compare cockpit foerst.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    cPushReady = FindHeaderIndex(wsFacts, "Push_Ready")
    cApplyAction = FindHeaderIndex(wsFacts, "Apply_Action")
    If cPushReady = 0 Or cApplyAction = 0 Then
        MsgBox "Push-kolonner mangler. Koer 'Apply compare decisions' foerst.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    cPushStatus = EnsureHeaderColumn(wsFacts, "Push_Status")
    cPushedAt = EnsureHeaderColumn(wsFacts, "Pushed_At")

    Set readyRows = New Collection
    CollectReadyPushRows wsFacts, cPushReady, cPushStatus, readyRows

    If readyRows.Count = 0 Then
        MsgBox "Ingen rækker er klar til push (eller alle er allerede sendt).", vbInformation, APP_TITLE
        Exit Sub
    End If

    payload = BuildDecisionPushPayload(wsFacts, readyRows)

    url = GetPowerAutomateUrlForCockpit()
    If Len(url) = 0 Then
        MsgBox "Power Automate URL mangler i Setup.", vbExclamation, APP_TITLE
        Exit Sub
    End If

    If dryRun Then
        WritePushPreviewSheet wsFacts, readyRows, payload, url
        MsgBox "Preview klar i arket 'Cockpit_Push_Preview'. Ingen data er sendt.", vbInformation, APP_TITLE
        Exit Sub
    End If

    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json"
    http.send payload

    If http.Status = 200 Or http.Status = 202 Then
        For r = 1 To readyRows.Count
            wsFacts.Cells(CLng(readyRows(r)), cPushStatus).Value = "SENT"
            wsFacts.Cells(CLng(readyRows(r)), cPushedAt).Value = Now
        Next r

        EnsureNamedTable wsFacts, LO_DECISION_FACTS

        Set wsHome = GetWorksheetIfExists(WS_COCKPIT_HOME)
        If Not wsHome Is Nothing Then AddDecisionMetricsToHome wsHome, wsFacts

        MsgBox "Push fuldfoert. Sendte rækker: " & CStr(readyRows.Count), vbInformation, APP_TITLE
    Else
        For r = 1 To readyRows.Count
            wsFacts.Cells(CLng(readyRows(r)), cPushStatus).Value = "ERROR " & CStr(http.Status)
        Next r

        MsgBox "Push fejlede: HTTP " & CStr(http.Status) & " - " & http.responseText, vbExclamation, APP_TITLE
    End If

    Exit Sub

EH:
    If dryRun Then
        MsgBox "Preview push fejlede: " & Err.Description, vbExclamation, APP_TITLE
    Else
        MsgBox "PushReadyDecisionsToPowerAutomate fejlede: " & Err.Description, vbExclamation, APP_TITLE
    End If
End Sub

Private Sub CollectReadyPushRows(ByVal wsFacts As Worksheet, _
                                 ByVal cPushReady As Long, _
                                 ByVal cPushStatus As Long, _
                                 ByRef readyRows As Collection)
    Dim lastRow As Long
    Dim r As Long

    lastRow = GetLastUsedRow(wsFacts)
    If lastRow < 2 Then Exit Sub

    For r = 2 To lastRow
        If UCase$(GetCellText(wsFacts, r, cPushReady)) = "Y" Then
            If UCase$(GetCellText(wsFacts, r, cPushStatus)) <> "SENT" Then
                readyRows.Add r
            End If
        End If
    Next r
End Sub

Private Sub WritePushPreviewSheet(ByVal wsFacts As Worksheet, _
                                  ByVal readyRows As Collection, _
                                  ByVal payload As String, _
                                  ByVal url As String)
    Const WS_PUSH_PREVIEW As String = "Cockpit_Push_Preview"

    Dim wsPreview As Worksheet
    Dim headers As Variant
    Dim arrOut() As Variant
    Dim i As Long
    Dim rowNo As Long

    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cFinal As Long
    Dim cAction As Long
    Dim cPushReady As Long
    Dim cPushStatus As Long

    Set wsPreview = EnsureSheet(WS_PUSH_PREVIEW, True)

    wsPreview.Range("A1").Value = "Generated_At"
    wsPreview.Range("B1").Value = Now
    wsPreview.Range("A2").Value = "Mode"
    wsPreview.Range("B2").Value = "DRY_RUN"
    wsPreview.Range("A3").Value = "URL"
    wsPreview.Range("B3").Value = url
    wsPreview.Range("A4").Value = "RowCount"
    wsPreview.Range("B4").Value = readyRows.Count
    wsPreview.Range("A6").Value = "Payload_JSON"
    wsPreview.Range("B6").Value = Left$(payload, 32000)
    If Len(payload) > 32000 Then
        wsPreview.Range("B7").Value = "Payload truncated to 32000 chars in preview sheet"
    End If

    wsPreview.Range("B6").WrapText = False

    headers = Array("Order_number", "Tasklist_Key", "Scope", "VORNR", "Sub_Key", "Field", "Decision", "Manual_Value", "Final_Value", "Apply_Action", "Push_Ready", "Push_Status")

    wsPreview.Range("A9").Resize(1, UBound(headers) - LBound(headers) + 1).Value = headers
    wsPreview.Rows(9).Font.Bold = True
    wsPreview.Rows(9).Interior.Color = RGB(240, 240, 240)

    cAuf = FindHeaderIndex(wsFacts, "AUFNR")
    cTask = FindHeaderIndex(wsFacts, "Tasklist_Key")
    cScope = FindHeaderIndex(wsFacts, "Scope")
    cVornr = FindHeaderIndex(wsFacts, "VORNR")
    cSub = FindHeaderIndex(wsFacts, "Sub_Key")
    cField = FindHeaderIndex(wsFacts, "Field")
    cDecision = FindHeaderIndex(wsFacts, "Decision")
    cManual = FindHeaderIndex(wsFacts, "Manual_Value")
    cFinal = FindHeaderIndex(wsFacts, "Final_Value")
    cAction = FindHeaderIndex(wsFacts, "Apply_Action")
    cPushReady = FindHeaderIndex(wsFacts, "Push_Ready")
    cPushStatus = FindHeaderIndex(wsFacts, "Push_Status")

    If readyRows.Count > 0 Then
        ReDim arrOut(1 To readyRows.Count, 1 To 12)

        For i = 1 To readyRows.Count
            rowNo = CLng(readyRows(i))
            arrOut(i, 1) = GetCellText(wsFacts, rowNo, cAuf)
            arrOut(i, 2) = GetCellText(wsFacts, rowNo, cTask)
            arrOut(i, 3) = GetCellText(wsFacts, rowNo, cScope)
            arrOut(i, 4) = GetCellText(wsFacts, rowNo, cVornr)
            arrOut(i, 5) = GetCellText(wsFacts, rowNo, cSub)
            arrOut(i, 6) = GetCellText(wsFacts, rowNo, cField)
            arrOut(i, 7) = GetCellText(wsFacts, rowNo, cDecision)
            arrOut(i, 8) = GetCellText(wsFacts, rowNo, cManual)
            arrOut(i, 9) = GetCellText(wsFacts, rowNo, cFinal)
            arrOut(i, 10) = GetCellText(wsFacts, rowNo, cAction)
            arrOut(i, 11) = GetCellText(wsFacts, rowNo, cPushReady)
            arrOut(i, 12) = GetCellText(wsFacts, rowNo, cPushStatus)
        Next i

        wsPreview.Range("A10").Resize(readyRows.Count, 12).Value = arrOut
    End If

    wsPreview.Columns.AutoFit
End Sub

Private Function BuildDecisionPushPayload(ByVal wsFacts As Worksheet, ByVal readyRows As Collection) As String
    Dim root As Object
    Dim items As Collection
    Dim item As Object
    Dim rowNo As Long

    Dim cKey As Long
    Dim cAuf As Long
    Dim cTask As Long
    Dim cScope As Long
    Dim cVornr As Long
    Dim cSub As Long
    Dim cField As Long
    Dim cSap As Long
    Dim cVh As Long
    Dim cReason As Long
    Dim cDecision As Long
    Dim cManual As Long
    Dim cFinal As Long
    Dim cAction As Long
    Dim cComment As Long
    Dim cChangedBy As Long
    Dim cChangedAt As Long
    Dim cAppliedAt As Long
    Dim cPushReady As Long

    cKey = FindHeaderIndex(wsFacts, "Diff_Key")
    cAuf = FindHeaderIndex(wsFacts, "AUFNR")
    cTask = FindHeaderIndex(wsFacts, "Tasklist_Key")
    cScope = FindHeaderIndex(wsFacts, "Scope")
    cVornr = FindHeaderIndex(wsFacts, "VORNR")
    cSub = FindHeaderIndex(wsFacts, "Sub_Key")
    cField = FindHeaderIndex(wsFacts, "Field")
    cSap = FindHeaderIndex(wsFacts, "SAP_Value")
    cVh = FindHeaderIndex(wsFacts, "VH_Value")
    cReason = FindHeaderIndex(wsFacts, "ReasonCode")
    cDecision = FindHeaderIndex(wsFacts, "Decision")
    cManual = FindHeaderIndex(wsFacts, "Manual_Value")
    cFinal = FindHeaderIndex(wsFacts, "Final_Value")
    cAction = FindHeaderIndex(wsFacts, "Apply_Action")
    cComment = FindHeaderIndex(wsFacts, "Comment")
    cChangedBy = FindHeaderIndex(wsFacts, "Changed_By")
    cChangedAt = FindHeaderIndex(wsFacts, "Changed_At")
    cAppliedAt = FindHeaderIndex(wsFacts, "Applied_At")
    cPushReady = FindHeaderIndex(wsFacts, "Push_Ready")

    Set root = CreateObject("Scripting.Dictionary")
    Set items = New Collection

    root.Add "Source", "CompareCockpit"
    root.Add "GeneratedAt", Format$(Now, "yyyy-mm-dd\THH:nn:ss")
    root.Add "Workbook", ThisWorkbook.Name
    root.Add "RowCount", readyRows.Count
    root.Add "Rows", items

    For rowNo = 1 To readyRows.Count
        Set item = CreateObject("Scripting.Dictionary")

        item.Add "Diff_Key", GetCellText(wsFacts, CLng(readyRows(rowNo)), cKey)
        item.Add "Order_number", GetCellText(wsFacts, CLng(readyRows(rowNo)), cAuf)
        item.Add "Tasklist_Key", GetCellText(wsFacts, CLng(readyRows(rowNo)), cTask)
        item.Add "Scope", GetCellText(wsFacts, CLng(readyRows(rowNo)), cScope)
        item.Add "VORNR", GetCellText(wsFacts, CLng(readyRows(rowNo)), cVornr)
        item.Add "Sub_Key", GetCellText(wsFacts, CLng(readyRows(rowNo)), cSub)
        item.Add "Field", GetCellText(wsFacts, CLng(readyRows(rowNo)), cField)
        item.Add "SAP_Value", GetCellText(wsFacts, CLng(readyRows(rowNo)), cSap)
        item.Add "VH_Value", GetCellText(wsFacts, CLng(readyRows(rowNo)), cVh)
        item.Add "ReasonCode", GetCellText(wsFacts, CLng(readyRows(rowNo)), cReason)
        item.Add "Decision", GetCellText(wsFacts, CLng(readyRows(rowNo)), cDecision)
        item.Add "Manual_Value", GetCellText(wsFacts, CLng(readyRows(rowNo)), cManual)
        item.Add "Final_Value", GetCellText(wsFacts, CLng(readyRows(rowNo)), cFinal)
        item.Add "Apply_Action", GetCellText(wsFacts, CLng(readyRows(rowNo)), cAction)
        item.Add "Comment", GetCellText(wsFacts, CLng(readyRows(rowNo)), cComment)
        item.Add "Changed_By", GetCellText(wsFacts, CLng(readyRows(rowNo)), cChangedBy)
        If cChangedAt > 0 Then
            item.Add "Changed_At", FormatForJsonDate(wsFacts.Cells(CLng(readyRows(rowNo)), cChangedAt).Value)
        Else
            item.Add "Changed_At", vbNullString
        End If
        If cAppliedAt > 0 Then
            item.Add "Applied_At", FormatForJsonDate(wsFacts.Cells(CLng(readyRows(rowNo)), cAppliedAt).Value)
        Else
            item.Add "Applied_At", vbNullString
        End If
        item.Add "Push_Ready", GetCellText(wsFacts, CLng(readyRows(rowNo)), cPushReady)

        items.Add item
    Next rowNo

    BuildDecisionPushPayload = JsonConverter.ConvertToJson(root)
End Function

Private Function GetPowerAutomateUrlForCockpit() As String
    Dim setupValue As String

    On Error Resume Next
    setupValue = Trim$(CStr(Worksheets(WS_SETUP).Cells(SETUP_FLOW_URL_ROW, SETUP_FLOW_URL_COL).Value2))
    On Error GoTo 0

    If Len(setupValue) > 0 Then
        GetPowerAutomateUrlForCockpit = setupValue
    Else
        GetPowerAutomateUrlForCockpit = Trim$(POWER_AUTOMATE_URL)
    End If
End Function

Private Function FormatForJsonDate(ByVal v As Variant) As String
    If IsDate(v) Then
        FormatForJsonDate = Format$(CDate(v), "yyyy-mm-dd\THH:nn:ss")
    Else
        FormatForJsonDate = Trim$(CStr(v))
    End If
End Function

Private Function EnsureHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim colIdx As Long
    Dim lastCol As Long

    colIdx = FindHeaderIndex(ws, headerName)
    If colIdx > 0 Then
        EnsureHeaderColumn = colIdx
        Exit Function
    End If

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If Len(Trim$(CStr(ws.Cells(1, 1).Value2))) = 0 Then lastCol = 0

    EnsureHeaderColumn = lastCol + 1
    ws.Cells(1, EnsureHeaderColumn).Value = headerName
End Function
