Attribute VB_Name = "modSapInspect"
Option Explicit
'==============================================================================
' modSapInspect - find felt-ID'erne paa den aktive SAP-skaerm.
'
' Koer DumpScreen mens du staar paa skaermen. Den gaar hele objekttraeet
' igennem og skriver hvert ID, type, navn og indhold ud i arket "Inspect".
'
' Hurtigere og mere paalideligt end script-optageren, fordi du faar ALLE
' felter - ogsaa dem du ikke roerte, og dem der er tomme.
'==============================================================================

Private mWs As Worksheet
Private mRow As Long

'--- Dump hele det aktive vindue ----------------------------------------------
Public Sub DumpScreen()
    DumpFrom "wnd[0]"
End Sub

'--- Dump kun et undertrae. Brug det, naar wnd[0] giver for mange raekker:
'    fx DumpFrom "wnd[0]/usr" eller ID'et paa et table control. ---------------
Public Sub DumpFrom(ByVal rootId As String)
    Dim root As Object

    On Error GoTo Fail
    Set root = modSapSession.Session.FindById(rootId)

    Set mWs = EnsureSheet(SH_INSPECT)
    mWs.Cells.Clear
    mWs.Range("A1:F1").value = Array("Niveau", "ID", "Type", "Navn", "Tekst", "Aendringsbar")
    mWs.Range("A1:F1").Font.Bold = True
    mRow = 2

    Walk root, 0

    mWs.Columns("A:F").AutoFit
    mWs.Columns("B").ColumnWidth = 90
    mWs.Rows(1).AutoFilter
    mWs.Activate
    MsgBox mRow - 2 & " elementer skrevet til arket '" & SH_INSPECT & "'.", vbInformation
    Exit Sub

Fail:
    MsgBox "Kunne ikke laese skaermen: " & Err.Description, vbExclamation
End Sub

'--- Rekursiv gennemgang. ContainerType siger om elementet har boern. ---------
Private Sub Walk(ByVal comp As Object, ByVal level As Long)
    Dim sId As String, sType As String, sName As String
    Dim sText As String, sChange As String
    Dim isContainer As Boolean
    Dim child As Object

    On Error Resume Next
    sId = comp.Id & ""
    sType = comp.Type & ""
    sName = comp.Name & ""
    sText = comp.Text & ""
    sChange = ""
    sChange = CStr(comp.Changeable)
    isContainer = False
    isContainer = comp.ContainerType
    On Error GoTo 0

    mWs.Cells(mRow, 1).value = level
    mWs.Cells(mRow, 2).value = "'" & sId      ' apostrof: undgaa autoformatering
    mWs.Cells(mRow, 3).value = sType
    mWs.Cells(mRow, 4).value = sName
    mWs.Cells(mRow, 5).value = Left$(sText, 120)
    mWs.Cells(mRow, 6).value = sChange
    mRow = mRow + 1

    If Not isContainer Then Exit Sub
    If mRow > 20000 Then Exit Sub             ' sikkerhedsstop

    On Error Resume Next
    For Each child In comp.Children
        Walk child, level + 1
    Next child
End Sub

'--- Kolonnenavnene i et table control. Dem skal du bruge til pakkeskaermen. --
Public Sub DumpTableColumns(ByVal tableId As String)
    Dim tbl As Object, i As Long, ws As Worksheet

    On Error GoTo Fail
    Set tbl = modSapSession.Session.FindById(tableId)
    Set ws = EnsureSheet(SH_INSPECT)
    ws.Cells.Clear
    ws.Range("A1:C1").value = Array("Indeks", "Navn", "Titel")
    ws.Range("A1:C1").Font.Bold = True

    For i = 0 To tbl.Columns.Count - 1
        ws.Cells(i + 2, 1).value = i
        On Error Resume Next
        ws.Cells(i + 2, 2).value = tbl.Columns(i).Name & ""
        ws.Cells(i + 2, 3).value = tbl.Columns(i).Title & ""
        On Error GoTo 0
    Next i

    ws.Columns("A:C").AutoFit
    ws.Activate
    MsgBox tbl.Columns.Count & " kolonner. Synlige raekker: " & tbl.VisibleRowCount & _
           ", raekker i alt: " & tbl.RowCount, vbInformation
    Exit Sub

Fail:
    MsgBox "Kunne ikke laese table controlet: " & Err.Description, vbExclamation
End Sub

Private Function EnsureSheet(ByVal nm As String) As Worksheet
    On Error Resume Next
    Set EnsureSheet = ThisWorkbook.Worksheets(nm)
    On Error GoTo 0
    If EnsureSheet Is Nothing Then
        Set EnsureSheet = ThisWorkbook.Worksheets.Add( _
            After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        EnsureSheet.Name = nm
    End If
End Function
