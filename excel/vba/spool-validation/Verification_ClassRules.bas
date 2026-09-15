Attribute VB_Name = "Verification_ClassRules"
Option Explicit

Private Const CLASS_HEADER_ROW As Long = 3
Private Const CLASS_FIRST_DATA_ROW As Long = 4

Public Sub Typekreds_Core(ByVal Class As String)
    Dim ws As Worksheet
    Dim listWs As Worksheet
    Dim i As Integer
    Dim lastColumn As Long
    Dim col As Integer
    Dim value As String
    Dim specialColumns As Object
    Dim Typekredse As Variant
    Dim tableRange As Range
    Dim tableColumn As Range
    Dim key As Variant

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(CLASS_HEADER_ROW, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("TypekredsTabel").Range
    Set tableColumn = tableRange.Columns(1)
    Typekredse = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Typekredse", Typekredse

    For Each key In specialColumns.keys
        col = FindColumn(ws, CStr(key), lastColumn)

        If col = 0 Then
            MsgBox ValidationMessages.HeaderColumnNotFoundInRow(CStr(key), CLASS_HEADER_ROW)
            Exit Sub
        End If

        i = CLASS_FIRST_DATA_ROW
        Do While HasFLValue(ws, i)
            value = ws.Cells(i, col).value

            If IsInArray(value, specialColumns(key)) Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            ElseIf ws.Cells(i, FindColumn(ws, "Typekredse", lastColumn)).value = "" Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            Else
                Verification_Functions.HighlightError ws.Cells(i, col)
                Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidTypekredsValue(value)
            End If

            i = i + 1
        Loop
    Next key
End Sub

Public Sub TestMethod_Core(ByVal Class As String)
    Dim ws As Worksheet
    Dim listWs As Worksheet
    Dim i As Integer
    Dim lastColumn As Long
    Dim col As Integer
    Dim value As String
    Dim specialColumns As Object
    Dim TestMethod As Variant
    Dim tableRange As Range
    Dim tableColumn As Range
    Dim key As Variant

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(CLASS_HEADER_ROW, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("TestMethod").Range
    Set tableColumn = tableRange.Columns(1)
    TestMethod = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Test Method", TestMethod
    specialColumns.Add "Test Method 2", TestMethod

    For Each key In specialColumns.keys
        col = FindColumn(ws, CStr(key), lastColumn)

        If col = 0 Then
            MsgBox ValidationMessages.HeaderColumnNotFoundInRow(CStr(key), CLASS_HEADER_ROW)
            Exit Sub
        End If

        i = CLASS_FIRST_DATA_ROW
        Do While HasFLValue(ws, i)
            value = ws.Cells(i, col).value

            If IsInArray(value, specialColumns(key)) Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            ElseIf ws.Cells(i, FindColumn(ws, "Test Method", lastColumn)).value = "" Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            Else
                Verification_Functions.HighlightError ws.Cells(i, col)
                Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidTestMethodValue(value)
            End If

            i = i + 1
        Loop
    Next key
End Sub

