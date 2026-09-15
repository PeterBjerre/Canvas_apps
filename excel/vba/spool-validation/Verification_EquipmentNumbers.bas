Attribute VB_Name = "Verification_EquipmentNumbers"
Option Explicit

Private Const SHEET_LIST_DATA As String = "List data"
Private Const TABLE_PLANT As String = "Plant"
Private Const TABLE_EQ_CAT As String = "EQ_Cat"

Private Const HEADER_PLANT As String = "Plant"
Private Const HEADER_GARANTI_START As String = "Garanti start"
Private Const HEADER_GARANTI_SLUT As String = "Garanti slut"

Private Const PLANT_KEY_COLUMN_NAME As String = "Plant Key"
Private Const EQ_CATEGORY_DESCRIPTION_COLUMN_NAME As String = "Equipment category description"

Private Const DATE_PATTERN_DDMMYYYY_DOTS As String = "^\d{2}[.]\d{2}[.]\d{4}$"

Public Sub Equipment_Numbers_Core(ByVal Class As String)
    Dim ws As Worksheet
    Dim formatColumns As Object
    Dim specialColumns As Object
    Dim plantValues As Variant
    Dim categoryValues As Variant

    On Error GoTo Fail

    Set ws = ThisWorkbook.Sheets(Class)
    If ws Is Nothing Then Exit Sub

    Set formatColumns = CreateObject("Scripting.Dictionary")
    Set specialColumns = CreateObject("Scripting.Dictionary")

    formatColumns.Add "Status", Array(40, ".*")
    formatColumns.Add HEADER_PLANT, Array(30, ".*", True)
    formatColumns.Add "Equipmentnummer", Array(30, "^[A-Z0-9._/\-]*$")
    formatColumns.Add "Beskrivelse", Array(40, ".*", True)
    formatColumns.Add "Equipment Category", Array(60, ".*", True)
    formatColumns.Add "Fabrikat", Array(30, ".*")
    formatColumns.Add "Type betegnelse", Array(30, ".*")
    formatColumns.Add "Serienummer", Array(30, ".*")
    formatColumns.Add "Func. location", Array(30, "^[A-Z0-9._/\-]*$", True)
    formatColumns.Add "Func. loc. 1", Array(30, "^[A-Z0-9._/\-]*$")
    formatColumns.Add "Functional location 2", Array(30, "^[A-Z0-9._/\-]*$")
    formatColumns.Add "Klasse data", Array(40, ".*")
    formatColumns.Add "ROOM (koordinater)", Array(8, ".*")
    formatColumns.Add "Placering", Array(30, ".*")
    formatColumns.Add HEADER_GARANTI_START, Array(10, DATE_PATTERN_DDMMYYYY_DOTS)
    formatColumns.Add HEADER_GARANTI_SLUT, Array(10, DATE_PATTERN_DDMMYYYY_DOTS)
    formatColumns.Add "Dokument type", Array(30, ".*")
    formatColumns.Add "Dokument link", Array(255, ".*")

    plantValues = GetPlantAllowedValues()
    If IsArray(plantValues) Then
        If UBound(plantValues) >= LBound(plantValues) Then
            specialColumns.Add HEADER_PLANT, plantValues
        End If
    End If

    categoryValues = GetEquipmentCategoryAllowedValues()
    If IsArray(categoryValues) Then
        If UBound(categoryValues) >= LBound(categoryValues) Then
            specialColumns.Add "Equipment Category", categoryValues
        End If
    End If

    ApplyEquipmentNumbersDropdowns ws

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
    ValidateDateColumn ws, HEADER_GARANTI_START, DATE_PATTERN_DDMMYYYY_DOTS
    ValidateDateColumn ws, HEADER_GARANTI_SLUT, DATE_PATTERN_DDMMYYYY_DOTS

SafeExit:
    Exit Sub

Fail:
    Debug.Print ValidationMessages.DebugVerifyStepFailed("Equipment_Numbers", Class, Err.description)
    Resume SafeExit
End Sub

Public Sub ApplyEquipmentNumbersDropdowns(Optional ByVal ws As Worksheet = Nothing)
    Dim plantSource As Range
    Dim categorySource As Range
    Dim plantCol As Long
    Dim categoryCol As Long

    On Error GoTo SafeExit

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets(Equipment_Numbers.SHEET_EQUIPMENT_NUMBERS)
    End If
    If ws Is Nothing Then Exit Sub

    If TryGetTableColumnRange(TABLE_PLANT, PLANT_KEY_COLUMN_NAME, 1, plantSource) Then
        plantCol = GetHeaderColumn(ws, HEADER_PLANT)
        If plantCol > 0 Then ApplyListValidation ws, plantCol, plantSource
    End If

    If TryGetTableColumnRange(TABLE_EQ_CAT, EQ_CATEGORY_DESCRIPTION_COLUMN_NAME, 2, categorySource) Then
        categoryCol = GetHeaderColumn(ws, "Equipment Category")
        If categoryCol > 0 Then ApplyListValidation ws, categoryCol, categorySource
    End If

SafeExit:
    Err.Clear
End Sub

Private Sub ValidateDateColumn(ByVal ws As Worksheet, ByVal headerName As String, ByVal datePattern As String)
    Dim colIndex As Object
    Dim col As Long
    Dim gateCol As Long
    Dim i As Long
    Dim lastRow As Long
    Dim valueText As String
    Dim dateCandidate As String
    Dim regex As Object

    Set colIndex = Verification_Cache.GetColIndex(ws)
    col = Verification_Cache.LookupCol(colIndex, headerName)
    If col = 0 Then Exit Sub

    gateCol = Verification_Functions.GetPrimaryDataColumn(ws)
    lastRow = ws.Cells(ws.Rows.count, gateCol).End(xlUp).Row
    If lastRow < 4 Then Exit Sub

    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = False
    regex.pattern = datePattern

    For i = 4 To lastRow
        If Len(Trim$(CStr(ws.Cells(i, gateCol).Value2))) = 0 Then GoTo NextRow

        valueText = Trim$(CStr(ws.Cells(i, col).Value2))
        If Len(valueText) = 0 Then
            Verification_Functions.HighlightValid ws.Cells(i, col)
            GoTo NextRow
        End If

        If regex.Test(valueText) Then
            dateCandidate = Replace(valueText, ".", "/")
            If IsDate(dateCandidate) Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            Else
                Verification_Functions.HighlightError ws.Cells(i, col)
                Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidDateValueNotRealDate()
            End If
        Else
            Verification_Functions.HighlightError ws.Cells(i, col)
            Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidDateFormatUseDDMMYYYY()
        End If

NextRow:
    Next i
End Sub

Private Function GetPlantAllowedValues() As Variant
    Dim sourceRange As Range

    If TryGetTableColumnRange(TABLE_PLANT, PLANT_KEY_COLUMN_NAME, 1, sourceRange) Then
        GetPlantAllowedValues = GetAllowedValuesFromRange(sourceRange)
    End If
End Function

Private Function GetEquipmentCategoryAllowedValues() As Variant
    Dim sourceRange As Range

    If TryGetTableColumnRange(TABLE_EQ_CAT, EQ_CATEGORY_DESCRIPTION_COLUMN_NAME, 2, sourceRange) Then
        GetEquipmentCategoryAllowedValues = GetAllowedValuesFromRange(sourceRange)
    End If
End Function

Private Function TryGetTableColumnRange( _
    ByVal tableName As String, _
    ByVal columnName As String, _
    ByVal fallbackColumnIndex As Long, _
    ByRef resultRange As Range _
) As Boolean
    Dim listWs As Worksheet
    Dim tbl As ListObject
    Dim tblCol As ListColumn

    On Error GoTo SafeExit

    Set listWs = ThisWorkbook.Sheets(SHEET_LIST_DATA)
    If listWs Is Nothing Then Exit Function

    Set tbl = listWs.ListObjects(tableName)
    If tbl Is Nothing Then Exit Function

    On Error Resume Next
    Set tblCol = tbl.ListColumns(columnName)
    On Error GoTo SafeExit

    If tblCol Is Nothing Then
        If fallbackColumnIndex < 1 Or fallbackColumnIndex > tbl.ListColumns.count Then Exit Function
        Set tblCol = tbl.ListColumns(fallbackColumnIndex)
    End If

    If tblCol.DataBodyRange Is Nothing Then Exit Function

    Set resultRange = tblCol.DataBodyRange
    TryGetTableColumnRange = True

SafeExit:
    Err.Clear
End Function

Private Function GetAllowedValuesFromRange(ByVal sourceRange As Range) As Variant
    Dim valuesMap As Object
    Dim cell As Range
    Dim valueText As String
    Dim arr() As String
    Dim key As Variant
    Dim i As Long

    If sourceRange Is Nothing Then Exit Function

    Set valuesMap = CreateObject("Scripting.Dictionary")
    valuesMap.CompareMode = vbTextCompare

    For Each cell In sourceRange.Cells
        valueText = Trim$(CStr(cell.Value2))
        If Len(valueText) > 0 Then
            If Not valuesMap.exists(valueText) Then valuesMap(valueText) = True
        End If
    Next cell

    If valuesMap.count = 0 Then Exit Function

    ReDim arr(0 To valuesMap.count - 1)
    i = 0
    For Each key In valuesMap.keys
        arr(i) = CStr(key)
        i = i + 1
    Next key

    GetAllowedValuesFromRange = arr
End Function

Private Function GetHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim colIndex As Object

    Set colIndex = Verification_Cache.GetColIndex(ws)
    GetHeaderColumn = Verification_Cache.LookupCol(colIndex, headerName)
End Function

Private Sub ApplyListValidation(ByVal ws As Worksheet, ByVal targetColumn As Long, ByVal sourceRange As Range)
    Dim targetRange As Range
    Dim validationFormula As String

    If ws Is Nothing Then Exit Sub
    If targetColumn <= 0 Then Exit Sub
    If sourceRange Is Nothing Then Exit Sub

    validationFormula = "='" & sourceRange.Worksheet.name & "'!" & sourceRange.Address(True, True)
    Set targetRange = ws.Range(ws.Cells(4, targetColumn), ws.Cells(ws.Rows.count, targetColumn))

    With targetRange.Validation
        .Delete
        .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, Operator:=xlBetween, Formula1:=validationFormula
        .IgnoreBlank = True
        .InCellDropdown = True
        .ShowInput = True
        .ShowError = True
    End With
End Sub

