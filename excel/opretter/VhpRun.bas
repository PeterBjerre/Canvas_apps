Attribute VB_Name = "VhpRun"
Option Explicit
'==============================================================================
' VhpRun - koerslen: de valgte ordrer, een ad gangen, med statusfil.
'
' VH-planer koeres her (ProcessOrder), FL-anmodninger i VhpFlRun. De deler
' kontrollerne foer SAP (miljoe, nyere ordre, laas) og statusfilens
' hjaelpere, som derfor er Public.
'
' GENOPTAGELIG, IKKE ATOMAR. GUI scripting kan fejle midt i en plan - en
' laast funktionsplads, en dialog, et netvaerk der hakker. Derfor skrives
' statusfilen (<ordre>.status.json) efter HVERT objekt, SAP har gemt:
'
'   arbejdsplan -> position -> langtekst      (pr. item)
'   ... -> plan
'
' Koeres planen igen, springes alt over, der allerede staar i statusfilen.
' Genkoersel er den normale fejlrettelse: ret aarsagen, tryk Opret igen.
'
' Naar planen er oprettet, skrives kvitteringen i mappen Kvitteringer (flowet
' skriver numrene tilbage i SharePoint), og ordren flyttes til Oprettet.
'
' MILJOE. Ordren siger, om den kommer fra DEV, TEST eller PROD. DEV og TEST
' oprettes kun i et testsystem; PROD kun i et produktionssystem (Indstillinger,
' ProdSystems). Der er ingen "proeve i testsystemet" af en PROD-plan:
' kvitteringen ville skrive et testnummer paa en rigtig plan.
'
' LAAS. Statusfilen siger, hvem der koerer planen. En kollega, der trykker
' Opret samtidig, faar besked i stedet for en dublet. En koersel, der ikke
' har skrevet i statusfilen i LOCK_STALE_MINUTES minutter, regnes for doed.
'==============================================================================

Private mProdConfirmed As Boolean

' Opret ordrerne i paths (fulde stier til ordrefiler).
Public Sub CreateOrders(ByVal paths As Collection)
    Dim root As String
    Dim lk As Object
    Dim sess As Object
    Dim createdNew As Boolean
    Dim p As Variant
    Dim result As String
    Dim lines As String
    Dim nOk As Long
    Dim nFail As Long
    Dim nCheck As Long
    Dim nSkip As Long
    Dim msg As String

    If paths Is Nothing Then Exit Sub
    If paths.Count = 0 Then
        MsgBox VhpUtil.Dk("Der er ikke valgt noget. S{ae}t et x i kolonnen V{ae}lg."), vbInformation, VHP_APP_NAME
        Exit Sub
    End If

    root = VhpFiles.RootFolder()
    If Len(root) = 0 Then
        MsgBox VhpUtil.Dk("Mappen med ordrerne er ikke valgt. Tryk V{ae}lg mappe f{oe}rst."), vbExclamation, VHP_APP_NAME
        Exit Sub
    End If
    VhpFiles.EnsureSubfolders root
    Set lk = VhpLookup.Load()

    On Error GoTo NoSap
    Set sess = VhpSap.Connect(VhpConfig.Setting(SET_SAP_SYSTEM), VhpConfig.Setting(SET_SAP_CLIENT), _
                              VhpConfig.SettingIsYes(SET_NEW_SESSION), createdNew)
    On Error GoTo 0

    mProdConfirmed = False
    VhpUi.LogLine "", VhpUtil.Dk("Start: ") & paths.Count & VhpUtil.Dk(" ordre(r), SAP ") & _
        VhpSap.SystemName(sess) & "/" & VhpSap.ClientOf(sess) & ", " & VhpUtil.UserName()

    For Each p In paths
        result = SafeProcessOrder(CStr(p), root, sess, lk)
        Select Case Left$(result, 3)
            Case "OK:": nOk = nOk + 1
            Case "CK:": nCheck = nCheck + 1
            Case "SK:", "ST:": nSkip = nSkip + 1
            Case Else: nFail = nFail + 1
        End Select
        lines = lines & Mid$(result, 4) & vbLf
        If Left$(result, 3) = "ST:" Then Exit For
    Next p

    Application.StatusBar = False

    If createdNew And nFail = 0 And nCheck = 0 Then VhpSap.CloseSession sess

    msg = VhpUtil.Dk("Oprettet: ") & nOk & "    " & VhpUtil.Dk("Fejl: ") & nFail & "    " & _
          VhpUtil.Dk("Kr{ae}ver kontrol: ") & nCheck & "    " & VhpUtil.Dk("Sprunget over: ") & nSkip & _
          vbLf & vbLf & lines
    If nFail + nCheck > 0 Then
        msg = msg & vbLf & VhpUtil.Dk("SAP-vinduet er ladt {aa}bent, s{aa} du kan se, hvor det stoppede. ") & _
              VhpUtil.Dk("Detaljer st{aa}r i arket Log.")
    End If
    VhpUi.LogLine "", VhpUtil.Dk("Slut. Oprettet ") & nOk & VhpUtil.Dk(", fejl ") & nFail & _
        VhpUtil.Dk(", kr{ae}ver kontrol ") & nCheck & VhpUtil.Dk(", sprunget over ") & nSkip

    MsgBox msg, IIf(nFail + nCheck > 0, vbExclamation, vbInformation), VHP_APP_NAME
    VhpUi.RefreshList
    Exit Sub

NoSap:
    Application.StatusBar = False
    MsgBox Err.Description, vbExclamation, VHP_APP_NAME
End Sub

' ProcessOrder og VhpFlRun.ProcessFlOrder fanger selv fejlene fra SAP. Det her
' er nettet under: en fejl, ingen havde forudset (en fil, OneDrive holder
' laast, et ark, der er slettet), maa stoppe EEN ordre, ikke hele koerslen
' med en VBA-fejldialog.
Private Function SafeProcessOrder(ByVal path As String, ByVal root As String, _
                                  ByVal sess As Object, ByVal lk As Object) As String
    Dim msg As String
    On Error GoTo Unexpected
    If VhpOrder.IsFlFile(path) Then
        SafeProcessOrder = VhpFlRun.ProcessFlOrder(path, root, sess, lk)
    Else
        SafeProcessOrder = ProcessOrder(path, root, sess, lk)
    End If
    Exit Function

Unexpected:
    msg = Err.Description
    Resume Report
Report:
    VhpSap.Recover sess
    Application.StatusBar = False
    VhpUi.LogLine VhpFiles.FileNameOf(path), VhpUtil.Dk("Uventet fejl: ") & msg
    SafeProcessOrder = "FE:" & VhpFiles.FileNameOf(path) & VhpUtil.Dk(": uventet fejl {-} ") & msg
End Function

'==============================================================================
' Een ordre
'
' Returnerer "XX:tekst", hvor XX er OK, FE (fejl), CK (kraever kontrol),
' SK (sprunget over) eller ST (stop hele koerslen).
'==============================================================================
Private Function ProcessOrder(ByVal path As String, ByVal root As String, _
                              ByVal sess As Object, ByVal lk As Object) As String
    Dim order As Object
    Dim plan As Object
    Dim planId As String
    Dim v As Object
    Dim reason As String
    Dim statusPath As String
    Dim status As Object
    Dim ctx As Object
    Dim item As Object
    Dim st As Object
    Dim grp As String
    Dim cnt As String
    Dim itemNo As String
    Dim itemNos As Collection
    Dim planNo As String
    Dim w As Variant
    Dim errNo As Long
    Dim errMsg As String

    '--- 1. Indlaes og valider ------------------------------------------------
    On Error GoTo LoadFailed
    Set order = VhpOrder.LoadOrder(path)
    On Error GoTo 0

    Set plan = VhpUtil.JObj(order, "plan")
    planId = VhpUtil.JStr(plan, "planId")
    Progress planId, VhpUtil.Dk("kontrolleres")

    Set v = VhpOrder.Validate(order, lk)
    If v("errors").Count > 0 Then
        VhpUi.LogLine planId, VhpUtil.Dk("Kan ikke oprettes: ") & v("errors")(1)
        ProcessOrder = "FE:" & planId & VhpUtil.Dk(": kan ikke oprettes {-} ") & v("errors")(1) & _
            IIf(v("errors").Count > 1, VhpUtil.Dk(" (og ") & (v("errors").Count - 1) & VhpUtil.Dk(" mere {-} se Vis detaljer)"), "")
        Exit Function
    End If

    '--- 2. Miljoe, nyere ordre, laas ----------------------------------------
    reason = CheckEnvironment(order, VhpSap.SystemName(sess))
    If Len(reason) > 0 Then
        VhpUi.LogLine planId, Mid$(reason, 2)
        ProcessOrder = IIf(Left$(reason, 1) = "!", "ST:", "SK:") & planId & ": " & Mid$(reason, 2)
        Exit Function
    End If

    reason = CheckOtherOrders(root, path, planId, VhpUtil.JStr(order, "createdOn"), False)
    If Len(reason) > 0 Then
        VhpUi.LogLine planId, reason
        ProcessOrder = "SK:" & planId & ": " & reason
        Exit Function
    End If

    reason = CheckAlreadyCreated(root, planId, VhpSap.SystemName(sess))
    If Len(reason) > 0 Then
        VhpUi.LogLine planId, reason
        ProcessOrder = "SK:" & planId & ": " & reason
        Exit Function
    End If

    statusPath = VhpFiles.StatusPathFor(path)
    If VhpFiles.FileExists(statusPath) Then
        On Error GoTo LoadFailed
        Set status = VhpFiles.ReadJson(statusPath)
        On Error GoTo 0
        reason = CheckStatus(status, order, VhpSap.SystemName(sess), planId)
        If Len(reason) > 0 Then
            VhpUi.LogLine planId, reason
            ProcessOrder = IIf(VhpUtil.JStr(status, "state") = "NeedsCheck", "CK:", "SK:") & planId & ": " & reason
            Exit Function
        End If
    Else
        Set status = NewStatus(order, path)
    End If

    ' Allerede oprettet, men ikke flyttet (fx afbrudt lige efter planen)?
    If VhpUtil.JStr(status, "state") = "Created" Then
        On Error GoTo FinishFailed
        FinishOrder root, path, status
        On Error GoTo 0
        ProcessOrder = "OK:" & planId & VhpUtil.Dk(": var allerede oprettet som plan ") & VhpUtil.JStr(status, "sapPlanNo")
        Exit Function
    End If

    status("state") = "InProgress"
    status("sapSystem") = VhpSap.SystemName(sess)
    status("sapClient") = VhpSap.ClientOf(sess)
    status("lockedBy") = VhpUtil.UserName()
    status("lockedOn") = VhpUtil.IsoNow()
    status("lastError") = Null
    Set status("warnings") = New Collection
    For Each w In v("warnings")
        status("warnings").Add CStr(w)
    Next w
    AddLog status, planId, VhpUtil.Dk("Start (") & VhpSap.SystemName(sess) & "/" & VhpSap.ClientOf(sess) & _
        ", " & VhpUtil.UserName() & ")"
    SaveStatus status, statusPath

    Set ctx = BuildContext(order, lk)

    '--- 3. SAP ---------------------------------------------------------------
    On Error GoTo StepFailed

    Set itemNos = New Collection
    For Each item In VhpUtil.JList(order, "items")
        Set st = StatusItem(status, item)

        If Not VhpUtil.JHas(st, "taskListGroup") Then
            Progress planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": arbejdsplan (IA05)")
            VhpSteps.CreateTaskList sess, item, ctx, grp, cnt
            st("taskListType") = CStr(ctx("taskListType"))
            st("taskListGroup") = grp
            st("taskListCounter") = cnt
            AddLog status, planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": arbejdsplan ") & grp & "/" & cnt & " oprettet"
            SaveStatus status, statusPath
        End If

        If Not VhpUtil.JHas(st, "sapItemNo") Then
            Progress planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": position (IP04)")
            itemNo = VhpSteps.CreateItem(sess, item, ctx, VhpUtil.JStr(st, "taskListGroup"), VhpUtil.JStr(st, "taskListCounter"))
            st("sapItemNo") = itemNo
            AddLog status, planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": position ") & itemNo & " oprettet"
            SaveStatus status, statusPath
        End If

        If Not VhpUtil.JBool(st, "longTextDone") Then
            If VhpItf.HasText(VhpUtil.JStr(item, "longText")) Then
                Progress planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": langtekst (IP05)")
                VhpSteps.UploadItemLongText sess, item, ctx, VhpUtil.JStr(st, "sapItemNo")
                AddLog status, planId, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": langtekst uploadet")
            End If
            st("longTextDone") = True
            SaveStatus status, statusPath
        End If

        itemNos.Add VhpUtil.JStr(st, "sapItemNo")
    Next item

    If Not VhpUtil.JHas(status, "sapPlanNo") Then
        Progress planId, VhpUtil.Dk("plan (IP01)")
        planNo = VhpSteps.CreatePlan(sess, order, itemNos, ctx)
        status("sapPlanNo") = planNo
        AddLog status, planId, VhpUtil.Dk("Plan ") & planNo & VhpUtil.Dk(" oprettet")
        SaveStatus status, statusPath
    End If

    On Error GoTo 0

    '--- 4. Faerdig -----------------------------------------------------------
    MergeStepWarnings status, ctx
    status("state") = "Created"
    status("finishedOn") = VhpUtil.IsoNow()
    SaveStatus status, statusPath

    ' Planen ER oprettet. Kan kvitteringen ikke skrives, staar statusfilen
    ' paa Created, og naeste koersel proever kun kvitteringen igen.
    On Error GoTo FinishFailed
    FinishOrder root, path, status
    On Error GoTo 0

    ProcessOrder = "OK:" & planId & VhpUtil.Dk(": oprettet som plan ") & VhpUtil.JStr(status, "sapPlanNo") & _
        IIf(status("warnings").Count > 0, " (" & status("warnings").Count & VhpUtil.Dk(" advarsel(er) {-} se kvitteringen)"), "")
    Exit Function

FinishFailed:
    errMsg = Err.Description
    Resume FinishCleanup
FinishCleanup:
    On Error GoTo 0
    VhpUi.LogLine planId, VhpUtil.Dk("Oprettet, men kvitteringen kunne ikke skrives: ") & errMsg
    ProcessOrder = "CK:" & planId & VhpUtil.Dk(": oprettet som plan ") & VhpUtil.JStr(status, "sapPlanNo") & _
        VhpUtil.Dk(", men kvitteringen kunne ikke skrives (") & errMsg & _
        VhpUtil.Dk("). Tryk Opret igen for kun at skrive kvitteringen.")
    Exit Function

LoadFailed:
    errMsg = Err.Description
    Resume LoadCleanup
LoadCleanup:
    On Error GoTo 0
    VhpUi.LogLine VhpFiles.FileNameOf(path), errMsg
    ProcessOrder = "FE:" & VhpFiles.FileNameOf(path) & ": " & errMsg
    Exit Function

StepFailed:
    errNo = Err.Number
    errMsg = Err.Description
    Resume StepCleanup
StepCleanup:
    On Error Resume Next
    VhpSap.Recover sess
    MergeStepWarnings status, ctx
    Select Case errNo
        Case ERR_NEEDS_CHECK
            status("state") = "NeedsCheck"
        Case Else
            status("state") = IIf(AnythingCreated(status), "Partial", "Failed")
    End Select
    status("lastError") = errMsg
    AddLog status, planId, VhpUtil.Dk("STOP: ") & errMsg
    SaveStatus status, statusPath
    Application.StatusBar = False
    On Error GoTo 0

    Select Case errNo
        Case ERR_STOP_RUN
            ProcessOrder = "ST:" & planId & ": " & errMsg
        Case ERR_SKIP_PLAN
            ProcessOrder = "SK:" & planId & ": " & errMsg
        Case ERR_NEEDS_CHECK
            ProcessOrder = "CK:" & planId & VhpUtil.Dk(": kr{ae}ver kontrol {-} ") & errMsg
        Case Else
            ProcessOrder = "FE:" & planId & ": " & errMsg & _
                IIf(VhpUtil.JStr(status, "state") = "Partial", _
                    VhpUtil.Dk(" (delvist oprettet {-} ret fejlen og tryk Opret igen)"), "")
    End Select
End Function

'==============================================================================
' Kontroller foer SAP
'==============================================================================

' "" = ok. "!tekst" = stop hele koerslen. "-tekst" = spring ordren over.
Public Function CheckEnvironment(ByVal order As Object, ByVal systemName As String) As String
    Dim env As String
    Dim isProd As Boolean

    env = UCase$(VhpUtil.JStr(order, "environment"))
    isProd = VhpConfig.IsProductionSystem(systemName)

    If (env = "DEV" Or env = "TEST") And isProd Then
        CheckEnvironment = "-" & VhpUtil.Dk("Sp{ae}rret: ordren er fra ") & env & VhpUtil.Dk(", men SAP er ") & systemName & _
            VhpUtil.Dk(" (produktion). Testdata m{aa} ikke oprettes i produktions-SAP.")
        Exit Function
    End If

    If env = "PROD" And Not isProd Then
        CheckEnvironment = "-" & VhpUtil.Dk("Sp{ae}rret: ordren er fra PROD, men SAP er ") & systemName & _
            VhpUtil.Dk(" (test). En PROD-ordre oprettes i produktion {-} ellers ville SharePoint f{aa} et testresultat.")
        Exit Function
    End If

    If env = "PROD" And isProd And Not mProdConfirmed Then
        If MsgBox(VhpUtil.Dk("Du opretter nu i PRODUKTION (") & systemName & ")." & vbLf & vbLf & _
                  VhpUtil.Dk("Forts{ae}t?"), vbYesNo + vbExclamation + vbDefaultButton2 + vbSystemModal, _
                  VHP_APP_NAME) <> vbYes Then
            CheckEnvironment = "!" & VhpUtil.Dk("Stoppet: der blev ikke svaret ja til produktion.")
            Exit Function
        End If
        mProdConfirmed = True
    End If
End Function

' Er der en nyere ordre for samme plan eller anmodning, er denne erstattet.
' Er en AELDRE delvist oprettet, skal den afklares foerst - ellers kunne en
' VH-plan ende i SAP to gange. For FL (allowOlderPartial) er det ufarligt: en
' FL, der findes, aendres. Der stoppes kun, mens en aeldre koerer.
Public Function CheckOtherOrders(ByVal root As String, ByVal path As String, _
                                 ByVal key As String, ByVal createdOn As String, _
                                 ByVal allowOlderPartial As Boolean) As String
    Dim other As Variant
    Dim o As Object
    Dim s As Object
    Dim otherCreated As String
    Dim state As String

    For Each other In VhpFiles.ListOrderFiles(root)
        If StrComp(CStr(other), path, vbTextCompare) <> 0 Then
            Set o = Nothing
            On Error Resume Next
            Set o = VhpFiles.ReadJson(CStr(other))
            On Error GoTo 0
            If Not o Is Nothing Then
                If StrComp(VhpOrder.OrderKey(o), key, vbTextCompare) = 0 Then
                    otherCreated = VhpUtil.JStr(o, "createdOn")
                    If otherCreated > createdOn Then
                        CheckOtherOrders = VhpUtil.Dk("erstattet af en nyere ordre (") & VhpFiles.FileNameOf(CStr(other)) & _
                            VhpUtil.Dk("). Brug den.")
                        Exit Function
                    End If
                    If VhpFiles.FileExists(VhpFiles.StatusPathFor(CStr(other))) Then
                        Set s = Nothing
                        On Error Resume Next
                        Set s = VhpFiles.ReadJson(VhpFiles.StatusPathFor(CStr(other)))
                        On Error GoTo 0
                        state = VhpUtil.JStr(s, "state")
                        If state = "InProgress" Or (Not allowOlderPartial And (state = "Partial" Or state = "NeedsCheck")) Then
                            CheckOtherOrders = VhpUtil.Dk("en {ae}ldre ordre for samme ") & _
                                IIf(VhpOrder.IsFl(o), "anmodning", "plan") & " (" & _
                                VhpFiles.FileNameOf(CStr(other)) & VhpUtil.Dk(") er delvist oprettet eller i gang. Afklar den f{oe}rst.")
                            Exit Function
                        End If
                    End If
                End If
            End If
        End If
    Next other
End Function

' Er planen allerede oprettet i dette SAP-system af en tidligere ordre? Den
' ordre ligger i "Oprettet" sammen med sin statusfil (state Created). En plan
' oprettes kun een gang - en rettelse bagefter laves i SAP. Fanger fx en
' ordre, der blev koert, mens planen var trukket tilbage i appen.
Private Function CheckAlreadyCreated(ByVal root As String, ByVal planId As String, _
                                     ByVal systemName As String) As String
    Dim folder As String
    Dim f As Object
    Dim nm As String
    Dim s As Object

    folder = VhpFiles.DoneFolder(root)
    If Not VhpFiles.Fso().FolderExists(folder) Then Exit Function

    For Each f In VhpFiles.Fso().GetFolder(folder).Files
        nm = f.Name
        ' Navnet begynder med plan-ID'et (evt. efter et tidsstempel), saa
        ' kun de faa filer for denne plan skal laeses.
        If LCase$(Right$(nm, Len(SUFFIX_STATUS))) = LCase$(SUFFIX_STATUS) And _
           InStr(1, nm, planId & "_", vbTextCompare) > 0 Then
            Set s = Nothing
            On Error Resume Next
            Set s = VhpFiles.ReadJson(CStr(f.Path))
            On Error GoTo 0
            If Not s Is Nothing Then
                If VhpUtil.JStr(s, "state") = "Created" And _
                   StrComp(VhpUtil.JStr(s, "planId"), planId, vbTextCompare) = 0 And _
                   StrComp(VhpUtil.JStr(s, "sapSystem"), systemName, vbTextCompare) = 0 Then
                    CheckAlreadyCreated = VhpUtil.Dk("planen er allerede oprettet i ") & systemName & _
                        VhpUtil.Dk(" som plan ") & VhpUtil.JStr(s, "sapPlanNo") & " (" & nm & _
                        VhpUtil.Dk(" i Oprettet). Ret den i SAP (IP02) i stedet for at oprette den igen.")
                    Exit Function
                End If
            End If
        End If
    Next f
End Function

' Kan en eksisterende statusfil koeres videre? "" = ja. label er planens
' eller anmodningens nummer, til beskederne.
Public Function CheckStatus(ByVal status As Object, ByVal order As Object, ByVal systemName As String, _
                            ByVal label As String) As String
    Dim state As String
    Dim who As String
    Dim minutes As Double

    If StrComp(VhpUtil.JStr(status, "orderGuid"), VhpUtil.JStr(order, "orderGuid"), vbTextCompare) <> 0 Then
        CheckStatus = VhpUtil.Dk("statusfilen h{oe}rer til en anden ordre (orderGuid passer ikke). Kontakt den, der vedligeholder opretteren.")
        Exit Function
    End If

    state = VhpUtil.JStr(status, "state")
    If state = "NeedsCheck" Then
        CheckStatus = VhpUtil.Dk("kr{ae}ver kontrol i SAP: ") & VhpUtil.JStr(status, "lastError")
        Exit Function
    End If

    If VhpUtil.JHas(status, "sapSystem") And AnythingCreated(status) Then
        If StrComp(VhpUtil.JStr(status, "sapSystem"), systemName, vbTextCompare) <> 0 Then
            CheckStatus = VhpUtil.Dk("den er p{aa}begyndt i ") & VhpUtil.JStr(status, "sapSystem") & _
                VhpUtil.Dk(", men du er logget p{aa} ") & systemName & "."
            Exit Function
        End If
    End If

    If state = "InProgress" Then
        who = VhpUtil.JStr(status, "lockedBy")
        If StrComp(who, VhpUtil.UserName(), vbTextCompare) <> 0 Then
            minutes = MinutesSince(VhpUtil.JStr(status, "updatedOn"))
            If minutes < LOCK_STALE_MINUTES Then
                CheckStatus = VhpUtil.Dk("er i gang hos ") & who & VhpUtil.Dk(" (sidst skrevet ") & _
                    VhpUtil.JStr(status, "updatedOn") & VhpUtil.Dk("). Vent, eller sp{oe}rg ") & who & "."
                Exit Function
            End If
            If MsgBox(label & VhpUtil.Dk(" blev startet af ") & who & _
                      VhpUtil.Dk(" og har ikke r{oe}rt sig i ") & CLng(minutes) & VhpUtil.Dk(" minutter.") & vbLf & vbLf & _
                      VhpUtil.Dk("Tag over og forts{ae}t, hvor den slap?"), vbYesNo + vbQuestion + vbSystemModal, _
                      VHP_APP_NAME) <> vbYes Then
                CheckStatus = VhpUtil.Dk("ikke overtaget fra ") & who & "."
            End If
        End If
    End If
End Function

Private Function MinutesSince(ByVal iso As String) As Double
    Dim d As Date
    If Not VhpUtil.TryParseYmd(Left$(iso, 10), d) Then
        MinutesSince = 1000000#
        Exit Function
    End If
    If Len(iso) >= 19 Then
        d = d + TimeSerial(Val(Mid$(iso, 12, 2)), Val(Mid$(iso, 15, 2)), Val(Mid$(iso, 18, 2)))
    End If
    MinutesSince = (Now - d) * 24# * 60#
End Function

'==============================================================================
' Statusfilen (samme form som kvitteringen: schema/vhplan-sap-receipt.schema.json)
'==============================================================================

Private Function NewStatus(ByVal order As Object, ByVal path As String) As Object
    Dim s As Object
    Dim plan As Object
    Dim items As New Collection
    Dim item As Object

    Set plan = VhpUtil.JObj(order, "plan")
    Set s = VhpUtil.NewDict()
    s.Add "kind", RECEIPT_KIND
    s.Add "version", 1
    s.Add "orderGuid", VhpUtil.JStr(order, "orderGuid")
    s.Add "orderFile", VhpFiles.FileNameOf(path)
    s.Add "planSpId", VhpUtil.JLng(plan, "spId")
    s.Add "planId", VhpUtil.JStr(plan, "planId")
    s.Add "state", "InProgress"
    s.Add "sapSystem", Null
    s.Add "sapClient", Null
    s.Add "sapPlanNo", Null
    s.Add "lockedBy", Null
    s.Add "lockedOn", Null
    s.Add "updatedOn", Null
    s.Add "finishedOn", Null
    For Each item In VhpUtil.JList(order, "items")
        items.Add NewStatusItem(item)
    Next item
    s.Add "items", items
    s.Add "warnings", New Collection
    s.Add "lastError", Null
    s.Add "log", New Collection
    Set NewStatus = s
End Function

Private Function NewStatusItem(ByVal item As Object) As Object
    Dim st As Object
    Set st = VhpUtil.NewDict()
    st.Add "spId", VhpUtil.JLng(item, "spId")
    st.Add "itemId", VhpUtil.JStr(item, "itemId")
    st.Add "taskListType", Null
    st.Add "taskListGroup", Null
    st.Add "taskListCounter", Null
    st.Add "sapItemNo", Null
    st.Add "longTextDone", False
    Set NewStatusItem = st
End Function

' Itemets raekke i statusfilen. Mangler den (ordren har faaet et item mere,
' siden statusfilen blev skrevet), tilfoejes den.
Private Function StatusItem(ByVal status As Object, ByVal item As Object) As Object
    Dim st As Object
    For Each st In VhpUtil.JList(status, "items")
        If VhpUtil.JLng(st, "spId") = VhpUtil.JLng(item, "spId") Then
            Set StatusItem = st
            Exit Function
        End If
    Next st
    Set st = NewStatusItem(item)
    status("items").Add st
    Set StatusItem = st
End Function

' Er noget gemt i SAP? VH: plan, arbejdsplan eller position. FL: en raekke.
Public Function AnythingCreated(ByVal status As Object) As Boolean
    Dim st As Object
    If VhpUtil.JHas(status, "sapPlanNo") Then
        AnythingCreated = True
        Exit Function
    End If
    For Each st In VhpUtil.JList(status, "items")
        If VhpUtil.JHas(st, "taskListGroup") Or VhpUtil.JHas(st, "sapItemNo") Then
            AnythingCreated = True
            Exit Function
        End If
    Next st
    For Each st In VhpUtil.JList(status, "rows")
        If VhpUtil.JBool(st, "done") Then
            AnythingCreated = True
            Exit Function
        End If
    Next st
End Function

Public Sub SaveStatus(ByVal status As Object, ByVal statusPath As String)
    status("updatedOn") = VhpUtil.IsoNow()
    VhpFiles.WriteJson statusPath, status
End Sub

' Loggen i statusfilen holdes under 300 linjer, saa en plan, der er koert
' mange gange, ikke vokser uden graense.
Public Sub AddLog(ByVal status As Object, ByVal planId As String, ByVal text As String)
    Dim entry As Object
    Dim lg As Collection

    Set entry = VhpUtil.NewDict()
    entry.Add "at", VhpUtil.IsoNow()
    entry.Add "text", text
    Set lg = VhpUtil.JList(status, "log")
    If Not status.Exists("log") Then status.Add "log", lg
    lg.Add entry
    Do While lg.Count > 300
        lg.Remove 1
    Loop
    VhpUi.LogLine planId, text
End Sub

Public Sub MergeStepWarnings(ByVal status As Object, ByVal ctx As Object)
    Dim w As Variant
    If ctx Is Nothing Then Exit Sub
    For Each w In ctx("warnings")
        status("warnings").Add CStr(w)
    Next w
    Set ctx("warnings") = New Collection
End Sub

' Kvitteringen til flowet, og ordren ud af "Til oprettelse".
Private Sub FinishOrder(ByVal root As String, ByVal path As String, ByVal status As Object)
    VhpFiles.WriteJson VhpFiles.ReceiptPathFor(root, path), status
    VhpFiles.MoveToDone root, path
End Sub

' AEldre ordrer for samme noegle (fx en FL-anmodning, der blev sendt retur og
' indsendt igen) flyttes til Oprettet, naar den nyeste er gemt. Ellers ville
' de staa i listen som Erstattet eller Delvist oprettet for altid.
Public Sub RetireOlderOrders(ByVal root As String, ByVal path As String, ByVal key As String, _
                             ByVal createdOn As String)
    Dim other As Variant
    Dim o As Object

    For Each other In VhpFiles.ListOrderFiles(root)
        If StrComp(CStr(other), path, vbTextCompare) <> 0 Then
            Set o = Nothing
            On Error Resume Next
            Set o = VhpFiles.ReadJson(CStr(other))
            On Error GoTo 0
            If Not o Is Nothing Then
                If StrComp(VhpOrder.OrderKey(o), key, vbTextCompare) = 0 Then
                    If VhpUtil.JStr(o, "createdOn") < createdOn Then VhpFiles.MoveToDone root, CStr(other)
                End If
            End If
        End If
    Next other
End Sub

'==============================================================================
' Konteksten til VhpSteps: indstillinger og opslag for denne ordre
'==============================================================================
Private Function BuildContext(ByVal order As Object, ByVal lk As Object) As Object
    Dim ctx As Object
    Dim plantRec As Object

    Set plantRec = VhpLookup.Plant(lk, VhpUtil.JStr(VhpUtil.JObj(order, "plan"), "plant"))

    Set ctx = VhpUtil.NewDict()
    ctx.Add "lookups", lk
    ctx.Add "sapPlant", VhpUtil.JStr(plantRec, "sapPlant")
    ctx.Add "profile", VhpUtil.JStr(plantRec, "profile")
    ctx.Add "serviceSpec", VhpUtil.JStr(plantRec, "serviceSpec")
    ctx.Add "keyDate", VhpConfig.Setting(SET_KEY_DATE)
    ctx.Add "itfPath", VhpConfig.Setting(SET_ITF_PATH)
    ctx.Add "decimalSep", VhpConfig.Setting(SET_DECIMAL_SEP)
    ctx.Add "pm02MatGroup", VhpConfig.Setting(SET_PM02_MATGROUP)
    ctx.Add "taskListType", VhpConfig.Setting(SET_TASKLIST_TYPE)
    ctx.Add "horizonQualifier", VhpConfig.Setting(SET_HORIZON_QUALIFIER)
    ctx.Add "planCategory", VhpConfig.Setting(SET_PLAN_CATEGORY)
    ctx.Add "confirmSave", VhpConfig.SettingIsYes(SET_CONFIRM_SAVE)
    ctx.Add "warnings", New Collection
    Set BuildContext = ctx
End Function

Public Sub Progress(ByVal planId As String, ByVal text As String)
    Application.StatusBar = VHP_APP_NAME & ": " & planId & " " & ChrW$(8211) & " " & text & ChrW$(8230)
    DoEvents
End Sub

'==============================================================================
' Test af forbindelsen (knappen Test SAP)
'==============================================================================
Public Sub TestConnection()
    Dim sess As Object
    Dim createdNew As Boolean
    Dim sysName As String

    On Error GoTo Failed
    Set sess = VhpSap.Connect(VhpConfig.Setting(SET_SAP_SYSTEM), VhpConfig.Setting(SET_SAP_CLIENT), False, createdNew)
    sysName = VhpSap.SystemName(sess)
    MsgBox VhpUtil.Dk("Forbindelsen virker.") & vbLf & vbLf & _
        "System: " & sysName & IIf(VhpConfig.IsProductionSystem(sysName), VhpUtil.Dk(" (PRODUKTION)"), " (test)") & vbLf & _
        "Klient: " & VhpSap.ClientOf(sess) & vbLf & _
        VhpUtil.Dk("Bruger: ") & sess.Info.User & vbLf & _
        "Transaktion: " & sess.Info.Transaction, vbInformation, VHP_APP_NAME
    Exit Sub

Failed:
    MsgBox Err.Description, vbExclamation, VHP_APP_NAME
End Sub
