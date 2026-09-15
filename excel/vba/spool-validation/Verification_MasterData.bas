Attribute VB_Name = "Verification_MasterData"
Option Explicit

Public Sub Verify_Master_Data_FL_Core(ByVal Class As String)
    Dim ws As Worksheet
    Dim formatColumns As Object, maxLengths As Object
    Dim specialColumns As Object
    Dim regex As Object
    Dim lastColumn As Long, col As Integer
    Dim i As Long
    Dim value As String
    Dim key As Variant

    Set ws = ThisWorkbook.Sheets(Class)

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Manufacturer", Array(30, ".*")
    formatColumns.Add "Description", Array(40, ".*", True)
    formatColumns.Add "Model Number", Array(20, ".*")
    formatColumns.Add "Manufacturer Part Number", Array(30, ".*")
    formatColumns.Add "Manufacturer Serial Number", Array(30, ".*")
    formatColumns.Add "Sort Field", Array(30, ".*")
    formatColumns.Add "Room", Array(8, ".*")

    Set maxLengths = CreateObject("Scripting.Dictionary")
    maxLengths.Add "Warranty Start", 10
    maxLengths.Add "Warranty End", 10

    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Atex", Array("X", "")
    specialColumns.Add "Risiko", Array("X", "")
    specialColumns.Add "Asbestos", Array("X", "")
    specialColumns.Add "PTW", Array("X", "")
    specialColumns.Add "ABC Indic.", Array("A", "")
    specialColumns.Add "StrIndicator", Array("KKS", "AKS", "ROS", "KKSKV", "KKSKA")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns

    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = False

    For Each key In maxLengths.keys
        col = Verification_Functions.FindColumn(ws, CStr(key), lastColumn)
        If col = 0 Then
            MsgBox ValidationMessages.HeaderColumnNotFound(CStr(key))
            Exit Sub
        End If

        i = 4
        Do While Len(Trim$(CStr(ws.Cells(i, 4).Value2))) > 0
            value = ws.Cells(i, col).value

            If key = "Warranty Start" Or key = "Warranty End" Then
                regex.pattern = "^\d{8}$|^\d{2}[.]\d{2}[.]\d{4}$"
                If value = "" Then
                    Verification_Functions.HighlightValid ws.Cells(i, col)
                ElseIf regex.Test(value) Then
                    Dim dateCheck As String
                    dateCheck = Replace(value, ".", "/")
                    If IsDate(dateCheck) Then
                        Verification_Functions.HighlightValid ws.Cells(i, col)
                    Else
                        Verification_Functions.HighlightError ws.Cells(i, col)
                        Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidDateValueNotRealDate()
                    End If
                Else
                    Verification_Functions.HighlightError ws.Cells(i, col)
                    Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.InvalidDateFormatUseDDMMYYYY()
                End If

            ElseIf key = "Description" Then
                If Len(value) > 0 And Len(value) <= maxLengths(key) Then
                    Verification_Functions.HighlightValid ws.Cells(i, col)
                Else
                    Verification_Functions.HighlightError ws.Cells(i, col)
                    Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.DescriptionRequiredMaxChars(maxLengths(key))
                End If
            Else
                If Len(value) <= maxLengths(key) Then
                    Verification_Functions.HighlightValid ws.Cells(i, col)
                Else
                    Verification_Functions.HighlightError ws.Cells(i, col)
                    Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.MaxLengthChars(maxLengths(key))
                End If
            End If

            i = i + 1
        Loop
    Next key

    For Each key In specialColumns.keys
        col = Verification_Functions.FindColumn(ws, CStr(key), lastColumn)
        If col = 0 Then
            MsgBox ValidationMessages.HeaderColumnNotFound(CStr(key))
            Exit Sub
        End If

        i = 4
        Do While Len(Trim$(CStr(ws.Cells(i, 4).Value2))) > 0
            value = ws.Cells(i, col).value
            If Verification.IsInArray2(value, specialColumns(key)) Then
                Verification_Functions.HighlightValid ws.Cells(i, col)
            Else
                Verification_Functions.HighlightError ws.Cells(i, col)
                Verification_Functions.AddCellComment ws.Cells(i, col), ValidationMessages.AllowedValuesList(specialColumns(key))
            End If
            i = i + 1
        Loop
    Next key
End Sub

