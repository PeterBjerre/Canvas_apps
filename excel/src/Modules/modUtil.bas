'===========================
' modUtil  (REN VERSION)
'===========================
Option Explicit

Public gWB As Workbook   ' den ENESTE globale reference til output-workbook

Public Function EnsureOutputWorkbook(Optional ByVal forceNew As Boolean = False) As Workbook
    ' Eksport skal altid skrives i den workbook der indeholder koden.
    Set gWB = ThisWorkbook
    Set EnsureOutputWorkbook = gWB
End Function

Public Sub BindOutputWorkbook(Optional ByVal wb As Workbook)
    ' Backward-compatible binder used by older call sites.
    If wb Is Nothing Then
        Set gWB = ThisWorkbook
    Else
        Set gWB = wb
    End If
End Sub

Public Sub PrepareSheet(ByVal name As String)
    Dim ws As Worksheet
    If gWB Is Nothing Then Set gWB = EnsureOutputWorkbook()

    On Error Resume Next
    Set ws = gWB.Worksheets(name)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = gWB.Worksheets.Add(After:=gWB.Sheets(gWB.Sheets.Count))
        On Error Resume Next
        ws.name = name
        On Error GoTo 0
    Else
        ws.Cells.Clear
    End If
End Sub

Public Sub WriteTableToSheet(ByVal sheetName As String, ByVal rows As Variant, ByVal cols As Object)
    Dim ws As Worksheet
    If gWB Is Nothing Then Set gWB = EnsureOutputWorkbook()

    On Error Resume Next
    Set ws = gWB.Worksheets(sheetName)
    If ws Is Nothing Then
        Set ws = gWB.Worksheets.Add(After:=gWB.Sheets(gWB.Sheets.Count))
        ws.name = sheetName
    End If
    On Error GoTo 0

    ws.Cells.Clear

    Dim colCount As Long: colCount = cols.Count
    Dim rCount As Long
    If IsEmpty(rows) Then
        rCount = 0
    Else
        rCount = UBound(rows, 1)
    End If

    If colCount = 0 Then
        ws.Range("A1").value = "(ingen data)"
        Exit Sub
    End If

    ' Overskrifter
    Dim headers() As Variant
    ReDim headers(1 To 1, 1 To colCount)
    Dim k As Variant, i As Long: i = 0
    For Each k In cols.Keys
        i = i + 1
        headers(1, i) = CStr(k)
    Next k
    ws.Range("A1").Resize(1, colCount).value = headers

    ' R�kker
    If rCount > 0 Then
        ws.Range("A2").Resize(rCount, colCount).value = rows
    End If

    With ws.UsedRange
        .Columns.AutoFit
        .rows(1).Font.Bold = True
        .rows(1).Interior.Color = RGB(240, 240, 240)
    End With
End Sub

Public Sub WriteTableToSheetAppend(ByVal sheetName As String, ByVal rows As Variant, ByVal cols As Object)
    Dim ws As Worksheet
    Dim allCols As Object
    Dim k As Variant
    Dim headerCol As Long
    Dim newColCount As Long
    Dim existingLastRow As Long
    Dim startRow As Long
    Dim rCount As Long
    Dim outRows() As Variant
    Dim srcCol As Long
    Dim dstCol As Long
    Dim r As Long

    If gWB Is Nothing Then Set gWB = EnsureOutputWorkbook()

    On Error Resume Next
    Set ws = gWB.Worksheets(sheetName)
    If ws Is Nothing Then
        Set ws = gWB.Worksheets.Add(After:=gWB.Sheets(gWB.Sheets.Count))
        ws.Name = sheetName
    End If
    On Error GoTo 0

    Set allCols = CreateObject("Scripting.Dictionary")

    headerCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If Len(CStr(ws.Cells(1, 1).Value)) = 0 Then headerCol = 0

    If headerCol > 0 Then
        For newColCount = 1 To headerCol
            k = CStr(ws.Cells(1, newColCount).Value)
            If Len(CStr(k)) > 0 Then
                If Not allCols.Exists(CStr(k)) Then allCols.Add CStr(k), allCols.Count + 1
            End If
        Next newColCount
    End If

    For Each k In cols.Keys
        If Not allCols.Exists(CStr(k)) Then allCols.Add CStr(k), allCols.Count + 1
    Next k

    newColCount = allCols.Count
    If newColCount = 0 Then Exit Sub

    Dim headers() As Variant
    ReDim headers(1 To 1, 1 To newColCount)
    Dim i As Long
    i = 0
    For Each k In allCols.Keys
        i = i + 1
        headers(1, i) = CStr(k)
    Next k
    ws.Range("A1").Resize(1, newColCount).Value = headers

    If IsEmpty(rows) Then
        With ws.UsedRange
            .Columns.AutoFit
            .Rows(1).Font.Bold = True
            .Rows(1).Interior.Color = RGB(240, 240, 240)
        End With
        Exit Sub
    End If

    rCount = UBound(rows, 1)
    If rCount <= 0 Then Exit Sub

    existingLastRow = GetLastUsedRow(ws)
    If existingLastRow < 2 Then
        startRow = 2
    Else
        startRow = existingLastRow + 1
    End If

    ReDim outRows(1 To rCount, 1 To newColCount)

    For Each k In cols.Keys
        srcCol = CLng(cols(CStr(k)))
        dstCol = CLng(allCols(CStr(k)))
        For r = 1 To rCount
            outRows(r, dstCol) = rows(r, srcCol)
        Next r
    Next k

    ws.Range("A" & CStr(startRow)).Resize(rCount, newColCount).Value = outRows

    With ws.UsedRange
        .Columns.AutoFit
        .Rows(1).Font.Bold = True
        .Rows(1).Interior.Color = RGB(240, 240, 240)
    End With
End Sub

Private Function GetLastUsedRow(ByVal ws As Worksheet) As Long
    Dim lastCell As Range
    On Error Resume Next
    Set lastCell = ws.Cells.Find(What:="*", After:=ws.Cells(1, 1), LookIn:=xlFormulas, _
                                 LookAt:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious, _
                                 MatchCase:=False)
    On Error GoTo 0

    If lastCell Is Nothing Then
        GetLastUsedRow = 0
    Else
        GetLastUsedRow = lastCell.Row
    End If
End Function

Public Function AppendRows(ByVal baseRows As Variant, ByVal newRows As Variant) As Variant
    Dim baseCount As Long
    Dim newCount As Long
    Dim baseCols As Long
    Dim newCols As Long
    Dim outCols As Long
    Dim r As Long
    Dim c As Long
    Dim outRows() As Variant

    baseCount = SafeRowCount(baseRows)
    newCount = SafeRowCount(newRows)

    If baseCount = 0 Then
        If newCount = 0 Then
            AppendRows = Empty
        Else
            AppendRows = newRows
        End If
        Exit Function
    End If

    If newCount = 0 Then
        AppendRows = baseRows
        Exit Function
    End If

    baseCols = SafeColCount(baseRows)
    newCols = SafeColCount(newRows)
    outCols = IIf(baseCols > newCols, baseCols, newCols)
    If outCols <= 0 Then
        AppendRows = Empty
        Exit Function
    End If

    ReDim outRows(1 To baseCount + newCount, 1 To outCols)

    For r = 1 To baseCount
        For c = 1 To baseCols
            outRows(r, c) = baseRows(r, c)
        Next c
    Next r

    For r = 1 To newCount
        For c = 1 To newCols
            outRows(baseCount + r, c) = newRows(r, c)
        Next c
    Next r

    AppendRows = outRows
End Function

Public Sub CollectDistinctValues(ByRef target As Collection, ByVal rows As Variant, ByVal cols As Object, ByVal columnName As String)
    Dim seen As Object
    Dim idx As Long
    Dim r As Long
    Dim valueText As String
    Dim i As Long

    If target Is Nothing Then Set target = New Collection

    Set seen = CreateObject("Scripting.Dictionary")
    seen.CompareMode = vbTextCompare

    On Error Resume Next
    For i = 1 To target.Count
        valueText = Trim$(CStr(target(i)))
        If Len(valueText) > 0 Then
            If Not seen.Exists(valueText) Then seen.Add valueText, True
        End If
    Next i
    On Error GoTo 0

    If cols Is Nothing Then Exit Sub
    If Not cols.Exists(columnName) Then Exit Sub

    idx = CLng(cols(columnName))
    If idx <= 0 Then Exit Sub

    If SafeRowCount(rows) = 0 Then Exit Sub
    If SafeColCount(rows) < idx Then Exit Sub

    For r = 1 To UBound(rows, 1)
        valueText = Trim$(CStr(rows(r, idx)))
        If Len(valueText) > 0 Then
            If Not seen.Exists(valueText) Then
                seen.Add valueText, True
                target.Add valueText
            End If
        End If
    Next r
End Sub

Public Function UrlEncode(ByVal text As String) As String
    Dim i As Long
    Dim ch As String
    Dim code As Long
    Dim out As String

    For i = 1 To Len(text)
        ch = Mid$(text, i, 1)
        code = AscW(ch)

        Select Case code
            Case 48 To 57, 65 To 90, 97 To 122
                out = out & ch
            Case 45, 46, 95, 126
                out = out & ch
            Case 32
                out = out & "%20"
            Case 0 To 255
                out = out & "%" & Right$("0" & Hex$(code), 2)
            Case Else
                out = out & "%3F"
        End Select
    Next i

    UrlEncode = out
End Function

Private Function SafeRowCount(ByVal rows As Variant) As Long
    On Error GoTo Fail
    If IsEmpty(rows) Then Exit Function
    SafeRowCount = UBound(rows, 1)
    Exit Function
Fail:
    SafeRowCount = 0
End Function

Private Function SafeColCount(ByVal rows As Variant) As Long
    On Error GoTo Fail
    If IsEmpty(rows) Then Exit Function
    SafeColCount = UBound(rows, 2)
    Exit Function
Fail:
    SafeColCount = 0
End Function
