Attribute VB_Name = "VhpFlSteps"
Option Explicit
'==============================================================================
' VhpFlSteps - een functional location i SAP, som SPOOL-arket goer det
' (excel/vba/spool-gui/GUI_SCRIPT.bas og GUI_RunCreate.bas):
'
'   1. IL01 med maerke og strukturindikator. Findes FL'en ("already exists"),
'      bruges IL02 - saa en anmodning kan koeres igen uden dubletter.
'   2. General: beskrivelse, objekttype, producent, model, part- og serienr.
'   3. Location: rum, ABC, sorteringsfelt, garanti.
'   4. Structure: overordnet FL - kun KAB.
'   5. Tilladelser (ATEX, Risiko, ASBEST, PTW). Ved IL02 ryddes de gamle.
'   6. Ved IL02 slettes de gamle klasser.
'   7. Klassen og de ekstra klasser (TRM, WCM, GIV_EXT).
'   8. Karakteristikkerne, efter navn, side for side.
'   9. Gem.
'
' Felt-ID'erne staar i VhpConfig (FL-afsnittet) og er SPOOL's, ordret.
'
' Forskellene fra SPOOL, og hvorfor:
'   - En fejl stopper RAEKKEN med SAP's besked, og SAP efterlades paa et kendt
'     billede (VhpSap.Recover). SPOOL viste en MsgBox og stoppede det hele.
'   - Efter en vaerdidialog (F4) laeses siden med karakteristikker forfra. SAP
'     tegner den om, og en gammel liste over felterne peger forkert (docs/15).
'   - En karakteristik, der ikke findes paa skaermen, skrives ALDRIG i et
'     andet felt. SPOOL kunne skrive en af de tre saerlige i sidens foerste
'     felt, hvis den laa paa en anden side. Den bliver nu en advarsel.
'   - Et Gem uden besked tjekkes i IL03, foer raekken regnes for gemt.
'   - IL02 bruger raekkens strukturindikator (SPOOL: altid KKS i den fulde vej).
'==============================================================================

' Opret eller aendr FL'en. Resultat: Dictionary med "result" (Created eller
' Updated) og "message" (statuslinjen efter Gem). En fejl rejses som ERR_SAP;
' Nej eller Annuller til Bekraeft gem som ERR_SKIP_PLAN eller ERR_STOP_RUN.
Public Function SaveFunctionalLocation(ByVal sess As Object, ByVal row As Object, _
                                       ByVal ctx As Object) As Object
    Dim fl As String
    Dim cls As String
    Dim isUpdate As Boolean
    Dim existingClass As String
    Dim chars As Object
    Dim res As Object

    fl = Trim$(VhpUtil.JStr(row, "functionalLocation"))
    cls = VhpFl.ClassOf(row)

    isUpdate = OpenFunctionalLocation(sess, row)
    existingClass = FillGeneral(sess, row)
    FillLocation sess, row, fl
    If cls = "KAB" Then FillSuperior sess, row
    FillPermits sess, row, isUpdate, fl
    If isUpdate And Len(existingClass) > 0 Then DeleteClasses sess

    AssignClasses sess, row, fl
    Set chars = VhpFl.CharacteristicMap(row, ctx("lookups"))
    If chars.Count > 0 Then FillCharacteristics sess, chars, ctx, fl

    VhpSteps.ConfirmSave ctx, fl & IIf(isUpdate, VhpUtil.Dk(" findes og bliver {ae}ndret (IL02)."), _
        VhpUtil.Dk(" bliver oprettet (IL01)."))
    Set res = SaveAndCheck(sess, fl)
    res.Add "result", IIf(isUpdate, "Updated", "Created")
    Set SaveFunctionalLocation = res
End Function

'==============================================================================
' 1-4. Indgangsbilledet og fanerne
'==============================================================================

' IL01 - eller IL02, hvis FL'en findes. True = IL02 (aendring).
Private Function OpenFunctionalLocation(ByVal sess As Object, ByVal row As Object) As Boolean
    Dim fl As String
    Dim strInd As String

    fl = Trim$(VhpUtil.JStr(row, "functionalLocation"))
    strInd = UCase$(Trim$(VhpUtil.JStr(row, "strIndicator")))

    VhpSap.StartTransaction sess, TX_FL_CREATE
    VhpSap.SetText sess, IL01_FL, fl
    VhpSap.SetText sess, IL01_STRIND, strInd
    VhpSap.Enter sess

    If InStr(1, VhpSap.StatusText(sess), FL_MSG_EXISTS, vbTextCompare) > 0 Then
        VhpSap.StartTransaction sess, TX_FL_CHANGE
        VhpSap.SetText sess, IL02_FL, fl
        VhpSap.SetText sess, IL02_STRIND, strInd
        VhpSap.Enter sess
        VhpSap.FailOnPopup sess, fl & " (IL02)"
        VhpSap.FailOnError sess, fl & " (IL02)"
        OpenFunctionalLocation = True
    Else
        VhpSap.FailOnPopup sess, fl & " (IL01)"
        VhpSap.FailOnError sess, fl & " (IL01)"
    End If

    If Not VhpSap.Exists(sess, FL_DESCRIPTION) Then
        Err.Raise ERR_SAP, "VhpFlSteps", fl & VhpUtil.Dk(": SAP viste ikke billedet med stamdata. ") & _
            VhpSap.StatusText(sess)
    End If
End Function

' Beskrivelse og fanen General. Returnerer den klasse, SAP viser for FL'en nu
' (tom for en ny) - ved IL02 skal den slettes, som i SPOOL.
Private Function FillGeneral(ByVal sess As Object, ByVal row As Object) As String
    VhpSap.SetText sess, FL_DESCRIPTION, Trim$(VhpUtil.JStr(row, "description"))
    FillGeneral = Trim$(VhpSap.GetText(sess, FL_CLASS_SHOWN))
    VhpSap.SetText sess, FL_OBJECT_TYPE, FL_OBJECT_TYPE_VALUE
    VhpSap.SetText sess, FL_MANUFACTURER, VhpFl.FieldValue(row, FLF_MANUFACTURER)
    VhpSap.SetText sess, FL_MODEL, VhpFl.FieldValue(row, FLF_MODEL)
    VhpSap.SetText sess, FL_PARTNO, VhpFl.FieldValue(row, FLF_PARTNO)
    VhpSap.SetText sess, FL_SERIAL, VhpFl.FieldValue(row, FLF_SERIAL)
End Function

Private Sub FillLocation(ByVal sess As Object, ByVal row As Object, ByVal fl As String)
    VhpSap.SelectItem sess, FL_TAB_LOCATION
    VhpSap.SetText sess, FL_ROOM, VhpFl.FieldValue(row, FLF_ROOM)
    VhpSap.SetText sess, FL_ABC, VhpFl.FieldValue(row, FLF_ABC)
    VhpSap.SetText sess, FL_SORTFIELD, VhpFl.FieldValue(row, FLF_SORTFIELD)
    VhpSap.SetText sess, FL_WARRANTY_START, VhpFl.SapDateText(VhpFl.FieldValue(row, FLF_WARRANTY_START))
    VhpSap.SetText sess, FL_WARRANTY_END, VhpFl.SapDateText(VhpFl.FieldValue(row, FLF_WARRANTY_END))
    VhpSap.SetChecked sess, FL_WARRANTY_INHERIT, True
    VhpSap.SetChecked sess, FL_WARRANTY_PASSON, True
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, fl & ": Location"
    VhpSap.FailOnError sess, fl & ": Location"
End Sub

' Overordnet FL - kun KAB, og kun hvis den er en anden end den, SAP viser.
Private Sub FillSuperior(ByVal sess As Object, ByVal row As Object)
    Dim superior As String

    superior = VhpFl.FieldValue(row, FLF_SUPERIOR)
    If Len(superior) = 0 Then Exit Sub

    VhpSap.SelectItem sess, FL_TAB_STRUCTURE
    If StrComp(Trim$(VhpSap.GetText(sess, FL_SUPERIOR)), superior, vbTextCompare) = 0 Then Exit Sub

    VhpSap.Press sess, FL_SUPERIOR_CHANGE
    VhpSap.SetText sess, FL_SUPERIOR_POPUP, superior
    HandlePopupUntilClosed sess, 25
End Sub

'==============================================================================
' 5-6. Tilladelser og de gamle klasser
'==============================================================================

Private Sub FillPermits(ByVal sess As Object, ByVal row As Object, ByVal isUpdate As Boolean, _
                        ByVal fl As String)
    Dim permits As Collection
    Dim p As Variant
    Dim n As Long

    Set permits = VhpFl.Permits(row)
    If Not isUpdate And permits.Count = 0 Then Exit Sub

    VhpSap.SelectItem sess, FL_MENU_PERMITS
    If isUpdate Then
        PressIfThere sess, FL_PERMIT_BTN_8
        PressIfThere sess, FL_PERMIT_BTN_14
    End If

    If permits.Count > 0 Then
        n = 1
        For Each p In permits
            If n > 4 Then Exit For
            VhpSap.SetText sess, FL_PERMIT_CELL & CStr(n) & "]", CStr(p)
            n = n + 1
        Next p
        VhpSap.VKey sess, 0, POPUP_WINDOW
    End If

    VhpSap.Press sess, FL_PERMIT_DONE
    VhpSap.FailOnPopup sess, fl & VhpUtil.Dk(": tilladelser")
    VhpSap.FailOnError sess, fl & VhpUtil.Dk(": tilladelser")
End Sub

Private Sub DeleteClasses(ByVal sess As Object)
    VhpSap.Press sess, FL_BTN_CLASSES
    VhpSap.Press sess, FL_CLASS_MARKALL
    VhpSap.Press sess, FL_CLASS_DELETE
    ConfirmPopupOption1 sess, 4
End Sub

'==============================================================================
' 7. Klassetildelingen
'==============================================================================

Private Sub AssignClasses(ByVal sess As Object, ByVal row As Object, ByVal fl As String)
    Dim cls As String
    Dim extras As Collection
    Dim extra As Variant

    cls = VhpFl.ClassOf(row)
    Set extras = VhpFl.ExtraClasses(row)
    If Not VhpFl.HasClassAssignment(cls) And extras.Count = 0 Then Exit Sub

    If Not ClassScreenOpen(sess) Then VhpSap.Press sess, FL_BTN_CLASSES

    If VhpFl.HasClassAssignment(cls) Then
        VhpSap.SetText sess, FL_CLASS_CELL & "0]", cls
        VhpSap.Enter sess
        VhpSap.FailOnPopup sess, fl & ": klasse " & cls
        VhpSap.FailOnError sess, fl & ": klasse " & cls
    End If

    ' Ekstra klasser: ny linje, og klassen i linje 1 - som i SPOOL.
    For Each extra In extras
        VhpSap.Press sess, FL_CLASS_NEWLINE
        VhpSap.SetText sess, FL_CLASS_CELL & "1]", CStr(extra)
        VhpSap.Enter sess
        VhpSap.FailOnPopup sess, fl & ": klasse " & CStr(extra)
        VhpSap.FailOnError sess, fl & ": klasse " & CStr(extra)
    Next extra

    If ClassScreenOpen(sess) Then VhpSap.Press sess, ID_BTN_BACK
End Sub

Private Function ClassScreenOpen(ByVal sess As Object) As Boolean
    ClassScreenOpen = VhpSap.Exists(sess, FL_CLASS_CELL & "0]")
End Function

'==============================================================================
' 8. Karakteristikkerne
'==============================================================================

' Skaermen viser en side ad gangen. Hver side laeses, det, der staar paa
' den, skrives, og der bladres videre. Efter en vaerdidialog laeses siden
' forfra. Det, der ikke blev fundet, bliver en advarsel - ikke skrevet et
' andet sted.
Private Sub FillCharacteristics(ByVal sess As Object, ByVal chars As Object, ByVal ctx As Object, _
                                ByVal fl As String)
    Dim pending As Object
    Dim k As Variant
    Dim pageGuard As Long
    Dim rescans As Long
    Dim firstKey As String

    Set pending = CreateObject("Scripting.Dictionary")
    pending.CompareMode = vbTextCompare
    For Each k In chars.Keys
        pending.Add CStr(k), CStr(chars(k))
    Next k

    VhpSap.SelectItem sess, FL_TAB_CHARS

    Do
        pageGuard = pageGuard + 1
        If pageGuard > 50 Then Exit Do

        rescans = 0
        Do
            rescans = rescans + 1
            If Not WriteCurrentPage(sess, pending, ctx, fl) Then Exit Do
        Loop While pending.Count > 0 And rescans < 30

        If pending.Count = 0 Then Exit Do
        firstKey = FirstCharacteristicOnPage(sess)
        If Not NextCharacteristicPage(sess) Then Exit Do
        If StrComp(FirstCharacteristicOnPage(sess), firstKey, vbTextCompare) = 0 Then Exit Do
    Loop

    For Each k In pending.Keys
        ctx("warnings").Add fl & VhpUtil.Dk(": karakteristikken '") & CStr(k) & _
            VhpUtil.Dk("' blev ikke fundet p{aa} sk{ae}rmen og er ikke skrevet.")
    Next k
End Sub

' Skriv de ventende karakteristikker, der staar paa siden. True, hvis en
' vaerdidialog blev brugt - saa er siden tegnet om og skal laeses igen.
Private Function WriteCurrentPage(ByVal sess As Object, ByVal pending As Object, ByVal ctx As Object, _
                                  ByVal fl As String) As Boolean
    Dim cont As Object
    Dim child As Object
    Dim names As New Collection
    Dim cells As New Collection
    Dim i As Long
    Dim j As Long
    Dim nm As String
    Dim fromIdx As Long
    Dim toIdx As Long
    Dim parts As Collection
    Dim p As Long
    Dim firstCell As Object

    Set cont = VhpSap.Fnd(sess, FL_CHAR_CONTAINER)
    For Each child In cont.Children
        If InStr(1, CStr(child.Id), "MNAME", vbBinaryCompare) > 0 Then
            names.Add Array(Trim$(CStr(child.Text)), IndexFromId(CStr(child.Id)))
        ElseIf InStr(1, CStr(child.Id), "MWERT", vbBinaryCompare) > 0 Then
            cells.Add Array(CStr(child.Id), IndexFromId(CStr(child.Id)))
        End If
    Next child

    For i = 1 To names.Count
        nm = CStr(names(i)(0))
        If Len(nm) > 0 Then
            If pending.Exists(nm) Then
                fromIdx = CLng(names(i)(1))
                If i < names.Count Then
                    toIdx = CLng(names(i + 1)(1))
                Else
                    toIdx = 9999
                End If

                Set parts = VhpFl.SplitValues(CStr(pending(nm)))
                Set firstCell = Nothing
                For j = 1 To cells.Count
                    If CLng(cells(j)(1)) >= fromIdx And CLng(cells(j)(1)) < toIdx Then
                        Set firstCell = VhpSap.Fnd(sess, CStr(cells(j)(0)))
                        Exit For
                    End If
                Next j

                If firstCell Is Nothing Then
                    ctx("warnings").Add fl & VhpUtil.Dk(": karakteristikken '") & nm & _
                        VhpUtil.Dk("' har intet v{ae}rdifelt p{aa} sk{ae}rmen og er ikke skrevet.")
                    pending.Remove nm
                ElseIf VhpFl.IsSpecialCharacteristic(nm) And parts.Count > 1 Then
                    ' Flere vaerdier i en af de tre saerlige: vaerdidialogen (F4).
                    firstCell.SetFocus
                    VhpSap.VKey sess, 4
                    If StrComp(nm, "Safety Critical Equipment", vbTextCompare) = 0 Then
                        SelectValuesInDialog sess, parts, ctx, fl, nm
                    Else
                        TypeValuesInDialog sess, parts
                    End If
                    VhpSap.Press sess, FL_VALUE_OK
                    VhpSap.Enter sess
                    VhpSap.FailOnPopup sess, fl & ": " & nm
                    pending.Remove nm
                    WriteCurrentPage = True
                    Exit Function
                Else
                    ' Een vaerdi pr. felt, i karakteristikkens felter paa siden.
                    p = 1
                    For j = 1 To cells.Count
                        If CLng(cells(j)(1)) >= fromIdx And CLng(cells(j)(1)) < toIdx Then
                            If p > parts.Count Then Exit For
                            VhpSap.SetText sess, CStr(cells(j)(0)), CStr(parts(p))
                            p = p + 1
                        End If
                    Next j
                    If p <= parts.Count Then
                        ctx("warnings").Add fl & VhpUtil.Dk(": karakteristikken '") & nm & "' fik " & (p - 1) & _
                            " af " & parts.Count & VhpUtil.Dk(" v{ae}rdier - der var ikke flere felter.")
                    End If
                    pending.Remove nm
                End If
            End If
        End If
    Next i
End Function

Private Function FirstCharacteristicOnPage(ByVal sess As Object) As String
    Dim cont As Object
    Dim child As Object

    If Not VhpSap.Exists(sess, FL_CHAR_CONTAINER) Then Exit Function
    Set cont = VhpSap.Fnd(sess, FL_CHAR_CONTAINER)
    For Each child In cont.Children
        If InStr(1, CStr(child.Id), "MNAME", vbBinaryCompare) > 0 Then
            FirstCharacteristicOnPage = Trim$(CStr(child.Text))
            Exit Function
        End If
    Next child
End Function

Private Function NextCharacteristicPage(ByVal sess As Object) As Boolean
    Dim btn As Object

    If Not VhpSap.Exists(sess, FL_CHAR_NEXT_PAGE) Then Exit Function
    Set btn = VhpSap.Fnd(sess, FL_CHAR_NEXT_PAGE)
    If Not btn.Changeable Then Exit Function
    btn.Press
    VhpSap.Enter sess
    NextCharacteristicPage = True
End Function

' Raekkens nummer i et felt-ID: "...MWERT[3,0]" -> 3 (SPOOL: GetIndexFromID).
Private Function IndexFromId(ByVal idText As String) As Long
    Dim openPos As Long
    Dim closePos As Long
    Dim parts() As String

    IndexFromId = -1
    openPos = InStrRev(idText, "[")
    closePos = InStrRev(idText, "]")
    If openPos > 0 And closePos > openPos Then
        parts = Split(Mid$(idText, openPos + 1, closePos - openPos - 1), ",")
        If IsNumeric(parts(0)) Then IndexFromId = CLng(parts(0))
    End If
End Function

' Remarks og Supply from: hver vaerdi skrives i dialogen, i stykker paa 30
' tegn - som SPOOL's SendToSAP.
Private Sub TypeValuesInDialog(ByVal sess As Object, ByVal parts As Collection)
    Dim part As Variant
    Dim chunk As Variant

    For Each part In parts
        For Each chunk In VhpFl.ChunkText(CStr(part), 30)
            VhpSap.SetText sess, FL_VALUE_CELL, Trim$(CStr(chunk))
            VhpSap.VKey sess, 0, POPUP_WINDOW
        Next chunk
    Next part
End Sub

' Safety Critical Equipment: vaerdierne vaelges i dialogens liste, side for
' side - som SPOOL's SelectSafetyCriticalEquipmentValuesInPopup.
Private Sub SelectValuesInDialog(ByVal sess As Object, ByVal parts As Collection, ByVal ctx As Object, _
                                 ByVal fl As String, ByVal nm As String)
    Dim wanted As Object
    Dim part As Variant
    Dim rowIndex As Long
    Dim textId As String
    Dim rowValue As String
    Dim guard As Long
    Dim k As Variant

    Set wanted = CreateObject("Scripting.Dictionary")
    wanted.CompareMode = vbTextCompare
    For Each part In parts
        If Not wanted.Exists(CStr(part)) Then wanted.Add CStr(part), True
    Next part

    Do
        guard = guard + 1
        If guard > 200 Then Exit Do
        For rowIndex = 0 To 99
            textId = FL_VALUE_TEXT & CStr(rowIndex) & "]"
            If Not VhpSap.Exists(sess, textId) Then Exit For
            rowValue = Trim$(VhpSap.GetText(sess, textId))
            If Len(rowValue) > 0 Then
                If wanted.Exists(rowValue) Then
                    VhpSap.SetChecked sess, FL_VALUE_CHECK & CStr(rowIndex) & "]", True
                    wanted.Remove rowValue
                    If wanted.Count = 0 Then Exit Sub
                End If
            End If
        Next rowIndex
    Loop While NextDialogPage(sess)

    For Each k In wanted.Keys
        ctx("warnings").Add fl & ": " & nm & VhpUtil.Dk(": v{ae}rdien '") & CStr(k) & _
            VhpUtil.Dk("' findes ikke i SAP's liste og er ikke valgt.")
    Next k
End Sub

Private Function NextDialogPage(ByVal sess As Object) As Boolean
    Dim tbl As Object
    Dim currentPos As Long
    Dim maxPos As Long
    Dim pageSize As Long
    Dim nextPos As Long

    If Not VhpSap.Exists(sess, FL_VALUE_TABLE) Then Exit Function
    Set tbl = VhpSap.Fnd(sess, FL_VALUE_TABLE)

    On Error Resume Next
    currentPos = CLng(tbl.VerticalScrollbar.Position)
    maxPos = CLng(tbl.VerticalScrollbar.Maximum)
    pageSize = CLng(tbl.VisibleRowCount)
    On Error GoTo 0

    If pageSize <= 0 Then pageSize = 10
    If currentPos >= maxPos Then Exit Function
    nextPos = currentPos + pageSize
    If nextPos > maxPos Then nextPos = maxPos
    If nextPos = currentPos Then Exit Function

    tbl.VerticalScrollbar.Position = nextPos
    VhpSap.VKey sess, 0, POPUP_WINDOW
    NextDialogPage = True
End Function

'==============================================================================
' 9. Gem
'==============================================================================

' En dialog efter Gem betyder, at FL'en IKKE blev gemt (SPOOL: "FL NOT
' CREATED"). Den lukkes som i SPOOL, og raekken fejler med SAP's tekst.
Private Function SaveAndCheck(ByVal sess As Object, ByVal fl As String) As Object
    Dim res As Object
    Dim msg As String
    Dim t As String

    VhpSap.Press sess, ID_BTN_SAVE

    If VhpSap.HasPopup(sess) Then
        msg = VhpSap.PopupText(sess)
        PressIfThere sess, POPUP_W1_BTN0
        PressIfThere sess, FL_BTN_EXIT
        PressIfThere sess, POPUP_OPTION2
        Err.Raise ERR_SAP, "VhpFlSteps", fl & VhpUtil.Dk(" blev ikke gemt: ") & msg
    End If

    t = VhpSap.StatusType(sess)
    msg = VhpSap.StatusText(sess)
    If t = "E" Or t = "A" Then
        Err.Raise ERR_SAP, "VhpFlSteps", fl & VhpUtil.Dk(" blev ikke gemt: ") & msg
    End If

    If t <> "S" And t <> "W" Then
        ' Intet svar, der siger succes. Se efter i IL03, foer raekken regnes
        ' for gemt.
        If Not FlExists(sess, fl) Then
            Err.Raise ERR_SAP, "VhpFlSteps", fl & VhpUtil.Dk(": SAP svarede '") & msg & _
                VhpUtil.Dk("', og FL'en findes ikke i IL03. Den er ikke gemt.")
        End If
        msg = Trim$(msg & VhpUtil.Dk(" (ingen besked fra SAP - FL'en findes i IL03)"))
    End If

    Set res = VhpUtil.NewDict()
    res.Add "message", msg
    Set SaveAndCheck = res
End Function

' Findes FL'en i SAP? IL03 viser stamdata, hvis den findes.
Private Function FlExists(ByVal sess As Object, ByVal fl As String) As Boolean
    On Error GoTo Failed
    VhpSap.StartTransaction sess, TX_FL_DISPLAY
    VhpSap.SetText sess, IL03_FL, fl
    VhpSap.Enter sess
    FlExists = (VhpSap.StatusType(sess) <> "E") And VhpSap.Exists(sess, FL_DESCRIPTION)
    Exit Function

Failed:
    Resume NotFound
NotFound:
    FlExists = False
End Function

'==============================================================================
' Dialoger
'==============================================================================

Private Sub PressIfThere(ByVal sess As Object, ByVal id As String)
    If VhpSap.Exists(sess, id) Then VhpSap.Press sess, id
End Sub

' Klik dialogerne vaek, som SPOOL's HandlePopupUntilClosed: Ja, OK, knap 1,
' OK i dialog nr. 2 - i den raekkefoelge.
Private Sub HandlePopupUntilClosed(ByVal sess As Object, ByVal maxAttempts As Long)
    Dim attempt As Long

    For attempt = 1 To maxAttempts
        If Not VhpSap.Exists(sess, POPUP_WINDOW) Then Exit Sub
        If VhpSap.Exists(sess, POPUP_OPTION1) Then
            VhpSap.Press sess, POPUP_OPTION1
        ElseIf VhpSap.Exists(sess, POPUP_W1_BTN0) Then
            VhpSap.Press sess, POPUP_W1_BTN0
        ElseIf VhpSap.Exists(sess, POPUP_W1_BTN1) Then
            VhpSap.Press sess, POPUP_W1_BTN1
        ElseIf VhpSap.Exists(sess, POPUP_W2_BTN0) Then
            VhpSap.Press sess, POPUP_W2_BTN0
        Else
            Exit Sub
        End If
    Next attempt
End Sub

' Svar Ja paa "slet klasserne?", som SPOOL's ConfirmPopupOption1.
Private Sub ConfirmPopupOption1(ByVal sess As Object, ByVal maxAttempts As Long)
    Dim attempt As Long

    For attempt = 1 To maxAttempts
        If Not VhpSap.Exists(sess, POPUP_OPTION1) Then Exit Sub
        VhpSap.Press sess, POPUP_OPTION1
    Next attempt
End Sub
