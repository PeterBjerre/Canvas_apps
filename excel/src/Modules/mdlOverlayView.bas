Attribute VB_Name = "mdlOverlayView"
Option Explicit

Public Const OVERLAY_SHEET_NAME As String = "OverlayView"

Public Const OP_TOP As String = "A1"
Public Const COM_TOP As String = "A30"
Public Const OBJ_TOP As String = "A60"
Public Const ADD_TOP As String = "A90"
Public Const PLN_TOP As String = "A120"

Public Const OP_GHOST_TOP As String = "A200"
Public Const COM_GHOST_TOP As String = "A230"
Public Const OBJ_GHOST_TOP As String = "A260"
Public Const ADD_GHOST_TOP As String = "A290"
Public Const PLN_GHOST_TOP As String = "A320"

Public Sub EnsureOverlaySheet()
    On Error Resume Next
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(OVERLAY_SHEET_NAME)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.name = OVERLAY_SHEET_NAME
    End If

    On Error Resume Next
    ws.Visible = xlSheetVeryHidden
    On Error GoTo 0
End Sub

Public Sub PrimeOverlayHeaders()
    On Error Resume Next
    EnsureOverlaySheet
    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(OVERLAY_SHEET_NAME)
    ws.Range(OP_TOP).Resize(1, 1).Value = ""
    ws.Range(COM_TOP).Resize(1, 1).Value = ""
    ws.Range(OBJ_TOP).Resize(1, 1).Value = ""
    ws.Range(ADD_TOP).Resize(1, 1).Value = ""
    ws.Range(PLN_TOP).Resize(1, 1).Value = ""
End Sub

Public Sub BindListBox(ByVal lb As MSForms.ListBox, ByRef headerNames() As String, ByRef dataArr As Variant, ByVal topLeftCell As String)
    On Error GoTo EH

    EnsureOverlaySheet

    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(OVERLAY_SHEET_NAME)
    Dim startCell As Range: Set startCell = ws.Range(topLeftCell)

    Dim cols As Long
    cols = UBound(headerNames)

    Application.EnableEvents = False
    Application.ScreenUpdating = False

    lb.rowSource = vbNullString

    startCell.Resize(1, cols).Value = headerNames

    Dim bodyArea As Range
    Dim rows As Long

    If Not IsEmpty(dataArr) Then
        rows = UBound(dataArr, 1)
        startCell.Offset(1, 0).Resize(rows, cols).Value = dataArr
        Set bodyArea = startCell.Offset(1, 0).Resize(rows, cols)
    Else
        startCell.Offset(1, 0).Resize(1, cols).Value = ""
        Set bodyArea = startCell.Offset(1, 0).Resize(1, cols)
    End If

    ' Kritisk: MSForms ListBox viser kun 1 kolonne hvis ColumnCount ikke sættes korrekt.
    ' Vi sætter den til hele området (inkl. _RowIndex kolonnen), så UI bliver generisk korrekt.
    lb.ColumnCount = cols

    lb.ColumnHeads = True
    lb.rowSource = OVERLAY_SHEET_NAME & "!" & bodyArea.Address(False, False)

CleanExit:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub

EH:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
End Sub

Public Sub BindHeaderOnlyGhost(ByVal lb As MSForms.ListBox, ByVal ghostTopLeft As String, ByVal cols As Long)
    On Error Resume Next

    EnsureOverlaySheet
    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(OVERLAY_SHEET_NAME)

    Dim startCell As Range: Set startCell = ws.Range(ghostTopLeft)
    Dim bodyArea As Range: Set bodyArea = startCell.Offset(1, 0).Resize(1, cols)

    lb.ColumnCount = cols
    lb.ColumnHeads = True
    lb.rowSource = OVERLAY_SHEET_NAME & "!" & bodyArea.Address(False, False)
End Sub

Public Function RangeFromRowSource(ByVal rowSource As String, ByRef wsOut As Worksheet) As Range
    On Error Resume Next
    Dim p() As String: p = Split(rowSource, "!")
    If UBound(p) = 1 Then
        Dim sh As String, addr As String
        sh = Replace(p(0), "'", "")
        addr = p(1)
        Set wsOut = ThisWorkbook.Worksheets(sh)
        Set RangeFromRowSource = wsOut.Range(addr)
    End If
End Function

Public Function HeaderRangeFromBody(ByVal bodyRng As Range) As Range
    On Error Resume Next
    Set HeaderRangeFromBody = bodyRng.Offset(-1, 0).Resize(1, bodyRng.Columns.Count)
End Function

Public Function SheetByName(ByVal nm As String) As Worksheet
    On Error Resume Next
    Set SheetByName = ThisWorkbook.Worksheets(nm)
End Function
