Attribute VB_Name = "Verification_Functions"
Option Explicit

Private mScopedRows As Object

Public Sub SetScopedChangedRows(ByVal changedRows As Object)
    If changedRows Is Nothing Then
        Set mScopedRows = Nothing
        Exit Sub
    End If

    Dim rowKey As Variant
    Dim scoped As Object
    Set scoped = CreateObject("Scripting.Dictionary")

    For Each rowKey In changedRows.keys
        If CLng(rowKey) >= 4 Then scoped(CLng(rowKey)) = True
    Next rowKey

    If scoped.count = 0 Then
        Set mScopedRows = Nothing
    Else
        Set mScopedRows = scoped
    End If
End Sub

Public Sub ClearScopedChangedRows()
    Set mScopedRows = Nothing
End Sub

Public Function HasScopedChangedRows() As Boolean
    HasScopedChangedRows = Not (mScopedRows Is Nothing)
    If HasScopedChangedRows Then HasScopedChangedRows = (mScopedRows.count > 0)
End Function

Public Function GetScopedChangedRows() As Object
    Set GetScopedChangedRows = mScopedRows
End Function

Public Function GetPrimaryDataColumn(ByVal ws As Worksheet) As Long
    If ws Is Nothing Then
        GetPrimaryDataColumn = 4
    ElseIf Equipment_Numbers.IsEquipmentNumbersSheetName(CStr(ws.name)) Then
        GetPrimaryDataColumn = 2
    Else
        GetPrimaryDataColumn = 4
    End If
End Function

Public Function GetStatusColumn(ByVal ws As Worksheet) As Long
    If ws Is Nothing Then
        GetStatusColumn = 2
    ElseIf Equipment_Numbers.IsEquipmentNumbersSheetName(CStr(ws.name)) Then
        GetStatusColumn = 1
    Else
        GetStatusColumn = 2
    End If
End Function

Public Function HasFLValue(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim gateCol As Long

    gateCol = GetPrimaryDataColumn(ws)
    HasFLValue = (Len(Trim$(CStr(ws.Cells(rowNum, gateCol).Value2))) > 0)
End Function

Private Function ResolveTargetRows( _
    ByVal ws As Worksheet, _
    Optional ByVal rowStart As Long = 0, _
    Optional ByVal rowEnd As Long = 0, _
    Optional ByVal changedRows As Object = Nothing _
) As Object
    Dim resolved As Object
    Dim rowKey As Variant
    Dim firstRow As Long
    Dim lastRow As Long
    Dim gateCol As Long
    Dim i As Long

    Set resolved = CreateObject("Scripting.Dictionary")

    If Not changedRows Is Nothing Then
        For Each rowKey In changedRows.keys
            If CLng(rowKey) >= 4 Then resolved(CLng(rowKey)) = True
        Next rowKey
    ElseIf HasScopedChangedRows() Then
        For Each rowKey In mScopedRows.keys
            If CLng(rowKey) >= 4 Then resolved(CLng(rowKey)) = True
        Next rowKey
    Else
        gateCol = GetPrimaryDataColumn(ws)
        lastRow = ws.Cells(ws.Rows.count, gateCol).End(xlUp).Row
        If lastRow < 4 Then
            Set ResolveTargetRows = resolved
            Exit Function
        End If

        If rowStart > 0 Then
            firstRow = rowStart
        Else
            firstRow = 4
        End If

        If rowEnd > 0 Then
            lastRow = rowEnd
        End If

        If firstRow < 4 Then firstRow = 4
        If lastRow < firstRow Then
            Set ResolveTargetRows = resolved
            Exit Function
        End If

        For i = firstRow To lastRow
            resolved(i) = True
        Next i
    End If

    Set ResolveTargetRows = resolved
End Function

' === Hjï¿½lpefunktioner til fejlmeddelelser og celler ===

Function GetInvalidUnitMsg(value As String, allowedValues As Variant) As String
    GetInvalidUnitMsg = ValidationMessages.InvalidUnitMessage(allowedValues)
End Function

Function GetDetailedFormatErrorMsg(value As String, maxLen As Long, formatDesc As String, Optional lengthOk As Boolean = True, Optional formatOk As Boolean = True) As String
    GetDetailedFormatErrorMsg = ValidationMessages.DetailedFormatErrorMsg(maxLen, formatDesc, lengthOk, formatOk)
End Function

Public Sub HighlightError(cell As Range)
    cell.Interior.Color = RGB(255, 182, 193)
End Sub

Public Sub HighlightValid(cell As Range)
    cell.Interior.Color = RGB(144, 238, 144)
    On Error Resume Next
    cell.ClearComments
    On Error GoTo 0
End Sub

Public Sub HighlightWarning(cell As Range)
    cell.Interior.Color = RGB(255, 255, 153)
End Sub

Sub AddCellComment(cell As Range, msg As String)
    On Error Resume Next
    cell.ClearComments
    On Error GoTo 0
    cell.AddComment msg
    cell.Comment.Visible = False
    With cell.Comment.Shape
        .TextFrame.AutoSize = True
        If .Width > 200 Then
            .Width = 200
            .TextFrame.AutoSize = True
        End If
    End With
End Sub

Function IsInArray(val As String, arr As Variant) As Boolean
    Dim element As Variant
    Dim token As Variant
    Dim parts() As String
    Dim tokenText As String
    Dim cell As Range

    val = Trim$(val)
    If Len(val) = 0 Then
        IsInArray = True
        Exit Function
    End If

    If InStr(val, "|") > 0 Then
        parts = Split(val, "|")
        For Each token In parts
            tokenText = Trim$(CStr(token))
            If Len(tokenText) = 0 Then GoTo NextToken

            If Not IsInArray(tokenText, arr) Then
                IsInArray = False
                Exit Function
            End If
NextToken:
        Next token

        IsInArray = True
        Exit Function
    End If

    If IsObject(arr) Then
        Select Case TypeName(arr)
            Case "Range"
                For Each cell In arr.Cells
                    If StrComp(val, Trim$(CStr(cell.Value2)), vbTextCompare) = 0 Then
                        IsInArray = True
                        Exit Function
                    End If
                Next cell

            Case "Collection"
                For Each element In arr
                    If StrComp(val, Trim$(CStr(element)), vbTextCompare) = 0 Then
                        IsInArray = True
                        Exit Function
                    End If
                Next element

            Case Else
                If StrComp(val, Trim$(CStr(arr)), vbTextCompare) = 0 Then
                    IsInArray = True
                    Exit Function
                End If
        End Select
    Else
        If IsArray(arr) Then
            For Each element In arr
                If StrComp(val, Trim$(CStr(element)), vbTextCompare) = 0 Then
                    IsInArray = True
                    Exit Function
                End If
            Next element
        Else
            If StrComp(val, Trim$(CStr(arr)), vbTextCompare) = 0 Then
                IsInArray = True
                Exit Function
            End If
        End If
    End If

    IsInArray = False
End Function



Function GetFormatDescription(pattern As String) As String
    GetFormatDescription = ValidationMessages.FormatDescription(pattern)
End Function

Function FindColumn(ws As Worksheet, header As String, lastColumn As Long) As Long
    Dim col As Long
    For col = 1 To lastColumn
        If ws.Cells(3, col).value = header Then
            FindColumn = col
            Exit Function
        End If
    Next col
    FindColumn = 0
End Function

Private Function GetLengthForValidation(ByVal value As String) As Long
    Dim parts As Variant
    Dim token As Variant
    Dim tokenLen As Long
    Dim maxTokenLen As Long

    If InStr(value, "|") = 0 Then
        GetLengthForValidation = Len(value)
        Exit Function
    End If

    parts = Split(value, "|")
    For Each token In parts
        tokenLen = Len(Trim$(CStr(token)))
        If tokenLen > maxTokenLen Then maxTokenLen = tokenLen
    Next token

    GetLengthForValidation = maxTokenLen
End Function


' === Centraliseret valideringsprocedure ï¿½ MED REQUIRED-FLAG & CACHE ===
' formatColumns: Dictionary hvor key = kolonneoverskrift (rï¿½kke 3)
'   Value er en Array:
'       (0) MaxLength As Long
'       (1) Pattern    As String  (RegEx; brug ".*" for fri tekst)
'       (2) [VALGFRI] Required   As Boolean  (True = mï¿½ IKKE vï¿½re tom)
'
' specialColumns: Dictionary hvor key = kolonneoverskrift, value = Variant() af tilladte vï¿½rdier
'   Hvis vï¿½rdien er tom streng, godkendes cellen ogsï¿½.

Public Sub ValidateTable( _
    ByVal Class As String, _
    ByVal formatColumns As Object, _
    Optional ByVal specialColumns As Object = Nothing, _
    Optional ByVal rowStart As Long = 0, _
    Optional ByVal rowEnd As Long = 0, _
    Optional ByVal changedRows As Object = Nothing _
)
    Dim ws As Worksheet, colIndex As Object
    Dim col As Long, i As Long, key As Variant
    Dim regex As Object, value As String
    Dim lengthOk As Boolean, formatOk As Boolean, requiredOk As Boolean
    Dim valueLength As Long
    Dim maxLen As Long, pattern As String, required As Boolean
    Dim targetRows As Object
    Dim rowKey As Variant

    Set ws = ThisWorkbook.Sheets(Class)
    If ws Is Nothing Then Exit Sub

    ' Hent headerindeks fra cache (rï¿½kke 3)
    Set colIndex = Verification_Cache.GetColIndex(ws)

    Set targetRows = ResolveTargetRows(ws, rowStart, rowEnd, changedRows)
    If targetRows.count = 0 Then Exit Sub

    ' --- Vï¿½rdivalidering (dropdowns / lister) ---
    If Not specialColumns Is Nothing Then
        For Each key In specialColumns.keys
            col = Verification_Cache.LookupCol(colIndex, CStr(key))
            If col = 0 Then
                MsgBox ValidationMessages.HeaderColumnNotFound(CStr(key)), vbExclamation
                Exit Sub
            End If

            For Each rowKey In targetRows.keys
                i = CLng(rowKey)
                If Not HasFLValue(ws, i) Then GoTo NextSpecialRow
                value = ws.Cells(i, col).value
                If IsInArray(value, specialColumns(key)) Or Len(value) = 0 Then
                    HighlightValid ws.Cells(i, col)
                Else
                    HighlightError ws.Cells(i, col)
                    AddCellComment ws.Cells(i, col), GetInvalidUnitMsg(value, specialColumns(key))
                End If
NextSpecialRow:
            Next rowKey
        Next key
    End If

    ' --- Format & required-validering ---
    For Each key In formatColumns.keys
        col = Verification_Cache.LookupCol(colIndex, CStr(key))
        If col = 0 Then
            MsgBox ValidationMessages.HeaderColumnNotFound(CStr(key)), vbExclamation
            Exit Sub
        End If

        ' Lï¿½s regel-tripletten
        maxLen = CLng(formatColumns(key)(0))
        pattern = CStr(formatColumns(key)(1))
        required = False
        If UBound(formatColumns(key)) >= 2 Then
            ' (2) er valgfri; hvis angivet bruges den
            required = CBool(formatColumns(key)(2))
        End If

        Set regex = CreateObject("VBScript.RegExp")
        With regex
            .IgnoreCase = True
            .Global = True
            .pattern = pattern
        End With

        For Each rowKey In targetRows.keys
            i = CLng(rowKey)
            If Not HasFLValue(ws, i) Then GoTo NextFormatRow
            value = ws.Cells(i, col).value

            ' pï¿½krï¿½vet?
            requiredOk = (Not required) Or (Len(value) > 0)

            ' lÃ¦ngde for pipe-separerede vÃ¦rdier vurderes pr. segment mellem "|"
            valueLength = GetLengthForValidation(value)
            lengthOk = (valueLength <= maxLen)
            formatOk = (Len(value) = 0 And Not required) Or regex.Test(value)

            If requiredOk And lengthOk And formatOk Then
                HighlightValid ws.Cells(i, col)
            Else
                HighlightError ws.Cells(i, col)
                AddCellComment ws.Cells(i, col), _
                    BuildErrorMessage(CStr(key), valueLength, maxLen, pattern, requiredOk, lengthOk, formatOk)
            End If
NextFormatRow:
        Next rowKey
    Next key
End Sub

' Sammensï¿½t en mere prï¿½cis fejlbesked inkl. "required"
Private Function BuildErrorMessage( _
    ByVal header As String, ByVal valueLength As Long, _
    ByVal maxLen As Long, ByVal pattern As String, _
    ByVal requiredOk As Boolean, ByVal lengthOk As Boolean, ByVal formatOk As Boolean _
) As String
    Dim msg As String
    msg = ValidationMessages.ValidationForHeader(header) & vbCrLf

    If requiredOk Then
        
    Else
        msg = msg & ValidationMessages.RequiredValueMissingLine() & vbCrLf
    End If

    If lengthOk Then
        msg = msg & ValidationMessages.MaxLengthOkLine(maxLen) & vbCrLf
    Else
        msg = msg & ValidationMessages.MaxLengthExceededLine(valueLength, maxLen) & vbCrLf
    End If

    If formatOk Then
        msg = msg & ValidationMessages.FormatOkLine(GetFormatDescription(pattern))
    Else
        msg = msg & ValidationMessages.FormatInvalidLine(GetFormatDescription(pattern))
    End If

    BuildErrorMessage = msg
End Function



' === Central statuslinje/uppercase/ready-state ===
' forceRun:=True bruges af manuel Verify (knap) for at bypass'e E2-switch'en
Public Sub HandleWorksheetChange( _
    ByVal ws As Worksheet, _
    Optional ByVal forceRun As Boolean = False, _
    Optional ByVal rowStart As Long = 0, _
    Optional ByVal rowEnd As Long = 0, _
    Optional ByVal changedRows As Object = Nothing _
)
    Dim rowIndex As Long
    Dim redFound As Boolean
    Dim lastColWithHeader As Long
    Dim gateCol As Long
    Dim statusCol As Long
    Dim col As Long
    Dim targetRows As Object
    Dim rowKey As Variant
    Dim previousEnableEvents As Boolean
    Dim eventsGuardActive As Boolean
    Dim dValue As String
    Dim upperDValue As String
    Dim statusText As String

    ' --- Gate pï¿½ E2 for ALLE ark nï¿½r auto (forceRun=False) ---
    ' Kun nï¿½r forceRun=False skal vi respektere E2; ellers skal knappen kunne kï¿½re alt.
    If Not forceRun Then
        If ThisWorkbook.Sheets("Initial Entry").Range("E2").value <> True Then
            Exit Sub
        End If
    End If

    ' Find sidste kolonne med overskrift i rï¿½kke 3
    lastColWithHeader = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column
    gateCol = GetPrimaryDataColumn(ws)
    statusCol = GetStatusColumn(ws)

    Set targetRows = ResolveTargetRows(ws, rowStart, rowEnd, changedRows)
    If targetRows.count = 0 Then Exit Sub

    previousEnableEvents = Application.EnableEvents
    Application.EnableEvents = False
    eventsGuardActive = True
    On Error GoTo CleanFail

    ' Gennemgï¿½ ALLE rï¿½kker og sï¿½t Info (kolonne B)
    For Each rowKey In targetRows.keys
        rowIndex = CLng(rowKey)

        If Not IsEmpty(ws.Cells(rowIndex, gateCol).value) Then
            dValue = CStr(ws.Cells(rowIndex, gateCol).value)
            upperDValue = UCase$(dValue)
            If dValue <> upperDValue Then
                ws.Cells(rowIndex, gateCol).value = upperDValue
            End If
        End If

        If Not HasFLValue(ws, rowIndex) Then
            With ws.Cells(rowIndex, statusCol)
                statusText = ""
                If CStr(.value) <> statusText Then .value = statusText
                .Interior.ColorIndex = xlColorIndexNone
            End With
            GoTo NextRow
        End If

        redFound = False

        For col = 1 To lastColWithHeader
            If col = statusCol Then GoTo NextColorCol
            If ws.Cells(rowIndex, col).Interior.Color = RGB(255, 182, 193) Then
                redFound = True
                Exit For
            End If
NextColorCol:
        Next col

        With ws.Cells(rowIndex, statusCol)
            If redFound Then
                statusText = ChrW(&H26A0) & " " & ValidationMessages.ErrorInLineStatus()
                If CStr(.value) <> statusText Then .value = statusText
                .Interior.Color = RGB(255, 182, 193)
            Else
                statusText = ChrW(&H2714) & " " & ValidationMessages.StatusReadyForSAP()
                If CStr(.value) <> statusText Then .value = statusText
                .Interior.Color = RGB(144, 238, 144)
            End If
        End With

NextRow:
    Next rowKey

CleanExit:
    If eventsGuardActive Then
        Application.EnableEvents = previousEnableEvents
    End If
    Exit Sub

CleanFail:
    If eventsGuardActive Then
        Application.EnableEvents = previousEnableEvents
    End If
    Err.Raise Err.Number, Err.source, Err.description, Err.HelpFile, Err.HelpContext
End Sub




