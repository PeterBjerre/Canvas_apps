Attribute VB_Name = "modSapSession"
Option Explicit
'==============================================================================
' modSapSession - forbindelse til en koerende SAP GUI-session, plus de
' hjaelpere resten af koden bruger.
'
' Alt er late binding (Object). Saet ingen reference til SAP GUI-biblioteket -
' saa kan modulerne importeres i en hvilken som helst projektmappe.
'
' FORUDSAETNING: scripting skal vaere slaaet til BEGGE steder.
'   Serverside : profilparameter sapgui/user_scripting = TRUE (Basis-opgave,
'                kraever genstart af instansen)
'   Klientside : Options > Accessibility & Scripting > Scripting > enable.
'                Slaa ogsaa "Notify when a script attaches to SAP GUI" og
'                "...opens a connection" fra - ellers kommer der en modal
'                dialog midt i batchen, som scriptet ikke kan se.
'==============================================================================

Private mSession As Object

'--- Egenskab: den aktive session --------------------------------------------
Public Property Get Session() As Object
    If mSession Is Nothing Then Connect
    Set Session = mSession
End Property

'--- Forbind til en ALLEREDE aaben og indlogget SAP GUI-session ---------------
' Vi logger bevidst ikke ind fra kode: det ville kraeve adgangskoden i klartekst
' i projektmappen. Brugeren logger ind, og makroen tager over.
Public Sub Connect()
    Dim sapGuiAuto As Object, app As Object, conn As Object

    On Error Resume Next
    Set sapGuiAuto = GetObject("SAPGUI")
    On Error GoTo 0
    If sapGuiAuto Is Nothing Then
        Err.Raise vbObjectError + 1, "modSapSession", _
            "SAP GUI koerer ikke. Log ind i SAP foerst og proev igen."
    End If

    Set app = sapGuiAuto.GetScriptingEngine
    If app.Connections.Count = 0 Then
        Err.Raise vbObjectError + 2, "modSapSession", _
            "Ingen aaben SAP-forbindelse."
    End If

    Set conn = app.Children(0)
    If conn.Children.Count = 0 Then
        Err.Raise vbObjectError + 3, "modSapSession", _
            "Forbindelsen har ingen session."
    End If

    Set mSession = conn.Children(0)
    mSession.FindById("wnd[0]").Maximize
End Sub

Public Sub Disconnect()
    Set mSession = Nothing
End Sub

'==============================================================================
' Skaermhandlinger
'==============================================================================

'--- Start en transaktion -----------------------------------------------------
Public Sub StartTransaction(ByVal tcode As String)
    Session.FindById(ID_OKCODE).Text = tcode
    Session.FindById("wnd[0]").SendVKey 0
    WaitScreen
    GuardPopup "Start af " & tcode
End Sub

'--- Saet tekst i et felt. Tom vaerdi springes over, saa SAP's egne defaults
'    ikke bliver overskrevet med blank. ------------------------------------
Public Sub SetText(ByVal fieldId As String, ByVal value As Variant)
    If Len(Trim$(CStr(value & ""))) = 0 Then Exit Sub
    Session.FindById(fieldId).Text = CStr(value)
End Sub

Public Sub SetDate(ByVal fieldId As String, ByVal value As Variant)
    If Not IsDate(value) Then Exit Sub
    Session.FindById(fieldId).Text = Format$(CDate(value), SAP_DATE_FMT)
End Sub

Public Sub PressEnter()
    Session.FindById("wnd[0]").SendVKey 0
    WaitScreen
End Sub

Public Sub PressSave()
    Session.FindById("wnd[0]").SendVKey 11
    WaitScreen
End Sub

Public Sub PressButton(ByVal buttonId As String)
    Session.FindById(buttonId).Press
    WaitScreen
End Sub

Public Sub SelectMenu(ByVal menuId As String)
    Session.FindById(menuId).Select
    WaitScreen
End Sub

'--- GUI scripting er synkront, men enkelte transaktioner returnerer foer
'    skaermen er faerdigtegnet. En kort pause er billigere end en flaky batch. --
Public Sub WaitScreen()
    If SCREEN_WAIT <= 0 Then Exit Sub
    Dim t As Double
    t = Timer
    Do While Timer < t + SCREEN_WAIT
        DoEvents
        If Timer < t Then Exit Do   ' midnat
    Loop
End Sub

'==============================================================================
' Statuslinjen - det eneste svar SAP giver
'==============================================================================

' S = success, W = warning, E = error, A = abort, tom = ingen besked
Public Function StatusType() As String
    On Error Resume Next
    StatusType = UCase$(Session.FindById(ID_STATUSBAR).MessageType & "")
End Function

Public Function StatusText() As String
    On Error Resume Next
    StatusText = Session.FindById(ID_STATUSBAR).Text & ""
End Function

Public Function StatusIsError() As Boolean
    Dim t As String
    t = StatusType()
    StatusIsError = (t = "E" Or t = "A")
End Function

'--- Traek det foerste tal paa mindst minLen cifre ud af statusteksten.
'    "Vedligeholdsplan 000000000123 oprettet" -> "000000000123"
'    Antag aldrig at et gem lykkedes, fordi der ikke kom en exception. --------
Public Function ExtractNumber(ByVal s As String, Optional ByVal minLen As Long = 4) As String
    Dim i As Long, runStart As Long, runLen As Long
    runStart = 0: runLen = 0
    For i = 1 To Len(s) + 1
        If i <= Len(s) And Mid$(s, i, 1) Like "#" Then
            If runLen = 0 Then runStart = i
            runLen = runLen + 1
        Else
            If runLen >= minLen Then
                ExtractNumber = Mid$(s, runStart, runLen)
                Exit Function
            End If
            runLen = 0
        End If
    Next i
End Function

'==============================================================================
' Popups
'==============================================================================

'--- Et uventet vindue i wnd[1] faar alt derefter til at fejle. Rejs en fejl
'    med popup-teksten, saa runneren kan afbryde DEN ENE raekke og gaa videre. -
Public Sub GuardPopup(ByVal context As String)
    If Session.Children.Count <= 1 Then Exit Sub

    Dim txt As String, title As String
    On Error Resume Next
    title = Session.FindById("wnd[1]").Text & ""
    txt = Session.FindById("wnd[1]/usr/txtMESSTXT1").Text & ""
    If Len(txt) = 0 Then txt = Session.FindById("wnd[1]/usr/txtMESSAGE").Text & ""
    On Error GoTo 0

    CloseAllPopups
    Err.Raise vbObjectError + 10, "modSapSession", _
        "Uventet popup ved " & context & ": " & title & " " & txt
End Sub

Public Sub CloseAllPopups()
    Dim guard As Long
    On Error Resume Next
    Do While Session.Children.Count > 1 And guard < 10
        Session.FindById("wnd[1]").SendVKey 12   ' Escape
        guard = guard + 1
    Loop
End Sub

'--- Bring sessionen tilbage til en kendt tilstand efter en fejl, saa den
'    naeste raekke i batchen starter rent. ------------------------------------
Public Sub ResetToMenu()
    On Error Resume Next
    CloseAllPopups
    Session.FindById(ID_OKCODE).Text = "/n"
    Session.FindById("wnd[0]").SendVKey 0
End Sub

'==============================================================================
' Table controls
'
' VIGTIGT: et table control indeholder kun de SYNLIGE raekker. Raekke 40
' findes ikke i objekttraeet, foer der er scrollet. Og referencen bliver
' ugyldig efter scroll - tabellen SKAL hentes igen med FindById.
'==============================================================================

'--- Scroll saa absolut raekke absRow er synlig, og returner tabellen paa ny.
'    Ud-parameteren visRow er raekkens indeks i det synlige vindue. -----------
Public Function ScrollToRow(ByVal tableId As String, ByVal absRow As Long, _
                            ByRef visRow As Long) As Object
    Dim tbl As Object, pos As Long, visible As Long

    Set tbl = Session.FindById(tableId)
    visible = tbl.VisibleRowCount
    pos = tbl.VerticalScrollbar.Position

    If absRow < pos Or absRow >= pos + visible Then
        tbl.VerticalScrollbar.Position = absRow
        WaitScreen
        ' Referencen er ugyldig efter scroll - hent den igen.
        Set tbl = Session.FindById(tableId)
        pos = tbl.VerticalScrollbar.Position
    End If

    visRow = absRow - pos
    Set ScrollToRow = tbl
End Function

'--- Find kolonneindeks ud fra kolonnens navn. Returnerer -1 hvis den ikke
'    findes, saa kalderen kan falde tilbage paa et fast indeks. --------------
Public Function ColumnIndex(ByVal tbl As Object, ByVal colName As String) As Long
    Dim i As Long, nm As String
    ColumnIndex = -1
    On Error Resume Next
    For i = 0 To tbl.Columns.Count - 1
        nm = ""
        nm = tbl.Columns(i).Name & ""
        If StrComp(nm, colName, vbTextCompare) = 0 Then
            ColumnIndex = i
            Exit Function
        End If
    Next i
End Function

'--- Saet en celle i et table control ud fra det ABSOLUTTE raekkenummer. ------
Public Sub SetCell(ByVal tableId As String, ByVal absRow As Long, _
                   ByVal colIndex As Long, ByVal value As Variant)
    If Len(Trim$(CStr(value & ""))) = 0 Then Exit Sub
    Dim tbl As Object, visRow As Long
    Set tbl = ScrollToRow(tableId, absRow, visRow)
    tbl.GetCell(visRow, colIndex).Text = CStr(value)
End Sub

'--- Saet et flueben i en celle. Checkbox-celler har .Selected, ikke .Text. ---
Public Sub SetCellChecked(ByVal tableId As String, ByVal absRow As Long, _
                          ByVal colIndex As Long, ByVal checked As Boolean)
    Dim tbl As Object, visRow As Long
    Set tbl = ScrollToRow(tableId, absRow, visRow)
    tbl.GetCell(visRow, colIndex).Selected = checked
End Sub
