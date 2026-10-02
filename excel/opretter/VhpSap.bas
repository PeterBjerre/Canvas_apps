Attribute VB_Name = "VhpSap"
Option Explicit
'==============================================================================
' VhpSap - forbindelsen til SAP GUI og de smaa handlinger, VhpSteps bygger af.
'
' Late binding hele vejen (Object). Projektmappen skal ikke have en reference
' til SAP GUI-biblioteket, og den kan saa aabnes paa en pc uden SAP uden at
' VBA melder "manglende reference".
'
' Forudsaetning (som for det gamle regneark): scripting er slaaet til i SAP
' (sapgui/user_scripting) og i SAP GUI (Optioner > Tilgaengelighed og
' scripting > Scripting). "Notify when a script attaches/opens a connection"
' skal vaere slaaet FRA, ellers kommer der en dialog, scriptet ikke kan se.
'
' Fire ting, der vaelter GUI scripting, og hvordan de er haandteret:
'   1. Et felt findes ikke  -> Fnd siger HVILKET og paa hvilken skaerm.
'   2. Statuslinjen er det eneste svar -> FailOnError laeser TYPEN (E/A).
'   3. En uventet dialog    -> FailOnPopup laeser teksten og lukker den.
'   4. Efter en fejl staar SAP et ukendt sted -> Recover lukker dialoger og
'      gaar til /n, saa naeste plan starter rent.
'==============================================================================

'==============================================================================
' Forbindelse
'==============================================================================

' Finder en indlogget session til systemet (fx GQ1, klient 450). Med
' newSession aabnes et nyt SAP-vindue til koerslen, saa brugerens eget
' arbejde i de andre vinduer ikke roeres. Kan der ikke aabnes flere (SAP
' tillader seks), bruges den fundne session.
Public Function Connect(ByVal systemName As String, ByVal client As String, _
                        ByVal newSession As Boolean, ByRef createdNew As Boolean) As Object
    Dim sapGui As Object
    Dim engine As Object
    Dim conn As Object
    Dim sess As Object
    Dim found As Object
    Dim foundConn As Object
    Dim t0 As Double

    createdNew = False

    Set sapGui = SapGuiObject()
    If sapGui Is Nothing Then
        ' Som det gamle SAP_AutoLogin_Core: start SAP Logon og vent.
        StartSapLogon
        Set sapGui = SapGuiObject()
    End If
    If sapGui Is Nothing Then
        Err.Raise ERR_SAP, "VhpSap", VhpUtil.Dk("SAP GUI k{oe}rer ikke. Start SAP Logon, log p{aa} ") & _
            systemName & VhpUtil.Dk(" (klient ") & client & VhpUtil.Dk("), og pr{oe}v igen.")
    End If

    On Error Resume Next
    Set engine = sapGui.GetScriptingEngine
    On Error GoTo 0
    If engine Is Nothing Then
        Err.Raise ERR_SAP, "VhpSap", VhpUtil.Dk("SAP GUI scripting er sl{aa}et fra. Sl{aa} det til under SAP GUI-indstillinger > Scripting.")
    End If

    FindSession engine, systemName, client, found, foundConn
    If found Is Nothing Then
        If OpenLogonConnection(engine, systemName) Then
            t0 = Timer
            Do While found Is Nothing And SecondsSince(t0) < 90
                DoEvents
                FindSession engine, systemName, client, found, foundConn
            Loop
        End If
    End If

    If found Is Nothing Then
        Err.Raise ERR_SAP, "VhpSap", VhpUtil.Dk("Der er ingen SAP-session til ") & systemName & _
            VhpUtil.Dk(" klient ") & client & VhpUtil.Dk(". Log p{aa} i SAP Logon, og pr{oe}v igen.")
    End If

    If newSession Then
        Set sess = OpenNewSession(foundConn, found)
        If Not sess Is Nothing Then
            Set found = sess
            createdNew = True
        End If
    End If

    On Error Resume Next
    found.FindById("wnd[0]").Maximize
    On Error GoTo 0

    Set Connect = found
End Function

' Den foerste session til systemet og klienten - helst en, der ikke er optaget.
Private Sub FindSession(ByVal engine As Object, ByVal systemName As String, ByVal client As String, _
                        ByRef found As Object, ByRef foundConn As Object)
    Dim conn As Object
    Dim sess As Object
    Dim c As Long
    Dim s As Long

    Set found = Nothing
    Set foundConn = Nothing
    On Error Resume Next
    For c = 0 To engine.Children.Count - 1
        Set conn = engine.Children(c + 0)
        For s = 0 To conn.Children.Count - 1
            Set sess = conn.Children(s + 0)
            If SessionMatches(sess, systemName, client) Then
                If found Is Nothing Then
                    Set found = sess
                    Set foundConn = conn
                ElseIf found.Busy And Not sess.Busy Then
                    Set found = sess
                    Set foundConn = conn
                End If
            End If
        Next s
    Next c
End Sub

Private Function SapGuiObject() As Object
    On Error Resume Next
    Set SapGuiObject = GetObject("SAPGUI")
End Function

Private Sub StartSapLogon()
    Dim candidates As Variant
    Dim i As Long
    Dim t0 As Double

    candidates = Array(Environ$("ProgramFiles") & "\SAP\FrontEnd\SAPGUI\saplogon.exe", _
                       Environ$("ProgramFiles(x86)") & "\SAP\FrontEnd\SAPGUI\saplogon.exe")
    For i = LBound(candidates) To UBound(candidates)
        If VhpFiles.FileExists(CStr(candidates(i))) Then
            Shell Chr$(34) & CStr(candidates(i)) & Chr$(34), vbNormalFocus
            t0 = Timer
            Do While SapGuiObject() Is Nothing And SecondsSince(t0) < 20
                DoEvents
            Loop
            Exit Sub
        End If
    Next i
End Sub

' Aabn forbindelsen i SAP Logon (Indstillinger: LogonTest/LogonProd), naar der
' ikke er en session. Med single sign-on logger SAP selv paa; ellers venter
' opretteren, mens brugeren logger paa.
Private Function OpenLogonConnection(ByVal engine As Object, ByVal systemName As String) As Boolean
    Dim desc As String

    If VhpConfig.IsProductionSystem(systemName) Then
        desc = VhpConfig.Setting(SET_LOGON_PROD)
    Else
        desc = VhpConfig.Setting(SET_LOGON_TEST)
    End If
    If Len(Trim$(desc)) = 0 Then Exit Function

    If MsgBox(VhpUtil.Dk("Der er ingen SAP-session til ") & systemName & "." & vbLf & vbLf & _
              VhpUtil.Dk("Skal opretteren {aa}bne '") & desc & VhpUtil.Dk("' i SAP Logon? Log p{aa}, hvis SAP beder om det."), _
              vbYesNo + vbQuestion + vbSystemModal, VHP_APP_NAME) <> vbYes Then Exit Function

    On Error Resume Next
    engine.OpenConnection desc, True
    OpenLogonConnection = (Err.Number = 0)
    On Error GoTo 0
End Function

Private Function SessionMatches(ByVal sess As Object, ByVal systemName As String, ByVal client As String) As Boolean
    Dim sysName As String
    Dim cl As String
    On Error Resume Next
    sysName = sess.Info.SystemName
    cl = sess.Info.Client
    On Error GoTo 0
    SessionMatches = (StrComp(sysName, systemName, vbTextCompare) = 0 And cl = client)
End Function

' Aabn et nyt vindue i samme forbindelse og vent paa det. Nothing, hvis det
' ikke lykkes inden for 20 sekunder.
Private Function OpenNewSession(ByVal conn As Object, ByVal fromSession As Object) As Object
    Dim before As Object
    Dim i As Long
    Dim sess As Object
    Dim sid As String
    Dim t0 As Double

    If conn.Children.Count >= 6 Then Exit Function

    Set before = VhpUtil.NewDict()
    For i = 0 To conn.Children.Count - 1
        before(CStr(conn.Children(i + 0).Id)) = True
    Next i

    On Error GoTo Failed
    fromSession.CreateSession

    t0 = Timer
    Do
        DoEvents
        For i = 0 To conn.Children.Count - 1
            Set sess = conn.Children(i + 0)
            sid = vbNullString
            On Error Resume Next
            sid = CStr(sess.Id)
            On Error GoTo Failed
            If Len(sid) > 0 And Not before.Exists(sid) Then
                Do While sess.Busy And SecondsSince(t0) < 20
                    DoEvents
                Loop
                Set OpenNewSession = sess
                Exit Function
            End If
        Next i
    Loop While SecondsSince(t0) < 20
    Exit Function

Failed:
    Set OpenNewSession = Nothing
End Function

' Luk et vindue, opretteren selv har aabnet.
Public Sub CloseSession(ByVal sess As Object)
    On Error Resume Next
    sess.Parent.CloseSession sess.Id
End Sub

Private Function SecondsSince(ByVal t0 As Double) As Double
    Dim t As Double
    t = Timer
    If t < t0 Then t = t + 86400#     ' midnat
    SecondsSince = t - t0
End Function

Public Function SystemName(ByVal sess As Object) As String
    On Error Resume Next
    SystemName = CStr(sess.Info.SystemName)
End Function

Public Function ClientOf(ByVal sess As Object) As String
    On Error Resume Next
    ClientOf = CStr(sess.Info.Client)
End Function

' Til fejlbeskeder: transaktion, program og skaermnummer.
Public Function ScreenInfo(ByVal sess As Object) As String
    On Error Resume Next
    ScreenInfo = sess.Info.Transaction & " " & sess.Info.Program & " " & sess.Info.ScreenNumber
End Function

'==============================================================================
' Felter og knapper
'==============================================================================

' FindById, men med en fejl, der siger hvilket felt og hvilken skaerm.
' "Objektet understoetter ikke egenskaben" fortaeller ingenting.
Public Function Fnd(ByVal sess As Object, ByVal id As String) As Object
    Dim o As Object
    On Error Resume Next
    Set o = sess.FindById(id, False)
    On Error GoTo 0
    If o Is Nothing Then
        Err.Raise ERR_SAP, "VhpSap", VhpUtil.Dk("SAP-feltet findes ikke p{aa} sk{ae}rmen: ") & id & _
            " [" & ScreenInfo(sess) & "]. " & StatusText(sess)
    End If
    Set Fnd = o
End Function

Public Function Exists(ByVal sess As Object, ByVal id As String) As Boolean
    Dim o As Object
    On Error Resume Next
    Set o = sess.FindById(id, False)
    On Error GoTo 0
    Exists = Not (o Is Nothing)
End Function

Public Sub SetText(ByVal sess As Object, ByVal id As String, ByVal value As String)
    Fnd(sess, id).Text = value
End Sub

Public Function GetText(ByVal sess As Object, ByVal id As String) As String
    GetText = CStr(Fnd(sess, id).Text)
End Function

Public Sub Press(ByVal sess As Object, ByVal id As String)
    Fnd(sess, id).Press
End Sub

' Faneblade, menupunkter og radioknapper.
Public Sub SelectItem(ByVal sess As Object, ByVal id As String)
    Fnd(sess, id).Select
End Sub

Public Sub SetChecked(ByVal sess As Object, ByVal id As String, ByVal checked As Boolean)
    Fnd(sess, id).Selected = checked
End Sub

Public Sub Focus(ByVal sess As Object, ByVal id As String)
    Fnd(sess, id).SetFocus
End Sub

Public Sub VKey(ByVal sess As Object, ByVal keyNo As Long, Optional ByVal windowId As String = "wnd[0]")
    Fnd(sess, windowId).SendVKey keyNo
End Sub

Public Sub Enter(ByVal sess As Object)
    VKey sess, 0
End Sub

Public Sub StartTransaction(ByVal sess As Object, ByVal tcode As String)
    SetText sess, ID_OKCODE, tcode
    Enter sess
    FailOnPopup sess, tcode
    FailOnError sess, tcode
End Sub

' Vaelg en vaerdi i en rulleliste. Proever noeglerne i raekkefoelge, og
' derefter en post, hvis TEKST er den givne. False, hvis intet passede.
Public Function SelectCombo(ByVal sess As Object, ByVal id As String, ByVal keys As Variant, _
                            Optional ByVal entryText As String = "") As Boolean
    Dim cmb As Object
    Dim i As Long
    Dim k As String
    Dim e As Object

    Set cmb = Fnd(sess, id)

    For i = LBound(keys) To UBound(keys)
        k = Trim$(CStr(keys(i)))
        If Len(k) > 0 Then
            On Error Resume Next
            cmb.Key = k
            If Err.Number = 0 Then
                If Trim$(CStr(cmb.Key)) = k Then
                    On Error GoTo 0
                    SelectCombo = True
                    Exit Function
                End If
            End If
            Err.Clear
            On Error GoTo 0
        End If
    Next i

    If Len(Trim$(entryText)) = 0 Then Exit Function

    On Error Resume Next
    For i = 0 To cmb.Entries.Count - 1
        Set e = cmb.Entries.Item(i + 0)
        If StrComp(Trim$(CStr(e.Value)), Trim$(entryText), vbTextCompare) = 0 Then
            cmb.Key = e.Key
            If Err.Number = 0 Then
                On Error GoTo 0
                SelectCombo = True
                Exit Function
            End If
            Err.Clear
        End If
    Next i
    On Error GoTo 0
End Function

'==============================================================================
' Statuslinjen og dialoger
'==============================================================================

' S succes, W advarsel, E fejl, A afbrudt, tom = ingen besked.
Public Function StatusType(ByVal sess As Object) As String
    On Error Resume Next
    StatusType = UCase$(Trim$(CStr(sess.FindById(ID_STATUSBAR).MessageType)))
End Function

Public Function StatusText(ByVal sess As Object) As String
    On Error Resume Next
    StatusText = Trim$(CStr(sess.FindById(ID_STATUSBAR).Text))
End Function

' E og A betyder, at det sidste trin IKKE gik igennem.
Public Sub FailOnError(ByVal sess As Object, ByVal context As String)
    Dim t As String
    t = StatusType(sess)
    If t = "E" Or t = "A" Then
        Err.Raise ERR_SAP, "VhpSap", context & ": " & StatusText(sess)
    End If
End Sub

Public Function HasPopup(ByVal sess As Object) As Boolean
    On Error Resume Next
    HasPopup = (sess.Children.Count > 1)
End Function

' En dialog, der ikke var ventet, laeses og lukkes, og der rejses en fejl med
' dens tekst. Saa star der i loggen, HVAD SAP spurgte om.
Public Sub FailOnPopup(ByVal sess As Object, ByVal context As String)
    Dim txt As String
    If Not HasPopup(sess) Then Exit Sub
    txt = PopupText(sess)
    ClosePopups sess
    Err.Raise ERR_SAP, "VhpSap", context & VhpUtil.Dk(": SAP viste en dialog: ") & txt
End Sub

Public Function PopupText(ByVal sess As Object) As String
    Dim w As String
    Dim ids As Variant
    Dim i As Long
    Dim o As Object
    Dim out As String

    On Error Resume Next
    w = "wnd[" & CStr(sess.Children.Count - 1) & "]"
    out = CStr(sess.FindById(w).Text)
    ids = Array("/usr/txtMESSTXT1", "/usr/txtMESSTXT2", "/usr/txtSPOP-TEXTLINE1", _
                "/usr/txtSPOP-TEXTLINE2", "/usr/txtSPOP-DIAGNOSE1", "/usr/txtMESSAGE")
    For i = LBound(ids) To UBound(ids)
        Set o = Nothing
        Set o = sess.FindById(w & ids(i), False)
        If Not o Is Nothing Then
            If Len(Trim$(CStr(o.Text))) > 0 Then out = out & " - " & Trim$(CStr(o.Text))
        End If
    Next i
    PopupText = out
End Function

Public Sub ClosePopups(ByVal sess As Object)
    Dim guard As Long
    On Error Resume Next
    Do While sess.Children.Count > 1 And guard < 6
        sess.FindById("wnd[" & CStr(sess.Children.Count - 1) & "]").Close
        guard = guard + 1
    Loop
End Sub

' Efter en fejl: luk dialoger og gaa ud af transaktionen uden at gemme.
' Naeste plan starter saa paa et kendt billede.
Public Sub Recover(ByVal sess As Object)
    On Error Resume Next
    If sess Is Nothing Then Exit Sub
    ClosePopups sess
    sess.FindById(ID_OKCODE).Text = "/n"
    sess.FindById("wnd[0]").SendVKey 0
    ' "/n" kan spoerge, om data skal gemmes. Svaret er nej - en fejlet plan
    ' maa ikke gemme et halvt udfyldt billede.
    ClosePopups sess
End Sub
