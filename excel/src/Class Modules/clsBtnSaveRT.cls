VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsBtnSaveRT"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False

'===== clsBtnSaveRT =====
Option Explicit

Public WithEvents Btn As MSForms.CommandButton
Attribute Btn.VB_VarHelpID = -1
Public hostForm As Object
Public sheetName As String
Public RowIndex As Long

Private mHeaders() As String
Private mValues() As String

Public Sub SetArrays(ByRef headers() As String, ByRef values() As String)
    Dim i As Long
    ReDim mHeaders(1 To UBound(headers))
    ReDim mValues(1 To UBound(values))
    For i = 1 To UBound(headers)
        mHeaders(i) = headers(i)
        mValues(i) = values(i)
    Next i
End Sub

Public Property Get headers() As Variant
    headers = mHeaders
End Property

Public Property Get values() As Variant
    values = mValues
End Property

Private Sub Btn_Click()
    On Error Resume Next

    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(sheetName)
    If ws Is Nothing Then Exit Sub

    Dim lo As ListObject, dataRowIdx As Long
    Set lo = FindListObjectForRow(ws, RowIndex, dataRowIdx)

    Dim i As Long, col As Long, tb As MSForms.TextBox

    If Not lo Is Nothing And dataRowIdx > 0 Then
        For i = 1 To UBound(mHeaders)
            Set tb = hostForm.Controls("tb" & i)
            If Not tb Is Nothing Then
                If LCase$(mHeaders(i)) <> "order" Then
                    col = FindHeaderInListObject(lo, mHeaders(i))
                    If col > 0 Then lo.DataBodyRange.Cells(dataRowIdx, col).Value = tb.text
                End If
            End If
        Next i
    Else
        For i = 1 To UBound(mHeaders)
            Set tb = hostForm.Controls("tb" & i)
            If Not tb Is Nothing Then
                If LCase$(mHeaders(i)) <> "order" Then
                    col = FindHeaderIndex(ws, mHeaders(i))
                    If col > 0 Then ws.Cells(RowIndex, col).Value = tb.text
                End If
            End If
        Next i
    End If

    hostForm.Tag = "saved"
    hostForm.Hide
End Sub

Private Function FindHeaderIndex(ByVal ws As Worksheet, ByVal headerName As String, Optional ByVal headerRow As Long = 1) As Long
    Dim lastCol As Long, c As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(headerRow, c).Value)), headerName, vbTextCompare) = 0 Then
            FindHeaderIndex = c: Exit Function
        End If
    Next
End Function

Private Function FindListObjectForRow(ByVal ws As Worksheet, ByRef rowIdx As Long, ByRef dataRowIdx As Long) As ListObject
    On Error Resume Next
    Dim lo As ListObject
    For Each lo In ws.ListObjects
        If Not lo.DataBodyRange Is Nothing Then
            If rowIdx >= lo.DataBodyRange.Row And rowIdx < lo.DataBodyRange.Row + lo.DataBodyRange.rows.Count Then
                Set FindListObjectForRow = lo
                dataRowIdx = rowIdx - lo.DataBodyRange.Row + 1
                Exit Function
            End If
        End If
    Next lo
End Function

Private Function FindHeaderInListObject(ByVal lo As ListObject, ByVal headerName As String) As Long
    On Error Resume Next
    Dim lc As ListColumn
    For Each lc In lo.ListColumns
        If StrComp(Trim$(CStr(lc.Range.Cells(1, 1).Value)), headerName, vbTextCompare) = 0 Then
            FindHeaderInListObject = lc.index: Exit Function
        End If
    Next lc
End Function

