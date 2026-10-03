Attribute VB_Name = "VhpSteps"
Option Explicit
'==============================================================================
' VhpSteps - de fire ting, der sker i SAP for en plan:
'
'   CreateTaskList      IA05  een generel arbejdsplan pr. item, med itemets
'                             operationer og deres langtekster
'   CreateItem          IP04  vedligeholdspositionen, der peger paa
'                             arbejdsplanen, med objektliste og status
'   UploadItemLongText  IP05  itemets langtekst
'   CreatePlan          IP01  planen med alle positionerne, cyklus,
'                             kaldshorisont, startdato og sorteringsfelt
'
' Raekkefoelgen af felter og knapper er det gamle GUI-scripts
' (excel/src/Modules/GUI_Script.bas), som har oprettet planer i jeres SAP.
' Det nye er:
'
'   * Een arbejdsplan pr. item. Det gamle script samlede operationer paa
'     TaskID, som appen ikke laengere skriver - nye planer fik derfor ingen
'     arbejdsplan.
'   * Operationsoversigten rulles, naar et item har flere operationer, end
'     der er synlige linjer. Foer fejlede operation nummer 16 eller 17.
'   * Ydelseslisten ved PM03 rulles ogsaa.
'   * PM02 faar prisen og varegruppen fra appen. Foer stod prisen i feltet
'     for timer og blev ganget med 1000, og varegruppen var fast B08.06.
'   * Statuslinjens TYPE afgoer, om noget er gemt, og et nummer laeses kun
'     fra et svar, der siger succes. En dialog efter Gem giver "kraever
'     kontrol" i stedet for et gaet.
'
' Alle procedurer rejser en fejl, naar noget gaar galt. VhpRun fanger den,
' skriver den i statusfilen og gaar videre med naeste plan.
'==============================================================================

'==============================================================================
' IA05 - arbejdsplan
'==============================================================================
Public Sub CreateTaskList(ByVal sess As Object, ByVal item As Object, ByVal ctx As Object, _
                          ByRef outGroup As String, ByRef outCounter As String)
    Dim what As String
    Dim headerGroup As String
    Dim headerCounter As String
    Dim op As Object
    Dim row As Long

    what = "IA05 " & VhpOrder.ItemLabel(item)

    VhpSap.StartTransaction sess, TX_TASKLIST
    VhpSap.SetText sess, IA05_INIT_GROUP, ""
    VhpSap.SetText sess, IA05_INIT_PROFILE, CStr(ctx("profile"))
    VhpSap.SetText sess, IA05_INIT_KEYDATE, CStr(ctx("keyDate"))
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (startbillede)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (startbillede)")

    ' Det gamle script laeste gruppe og taeller her, foer gem.
    headerGroup = Trim$(VhpSap.GetText(sess, IA05_HDR_GROUP))
    headerCounter = Trim$(VhpSap.GetText(sess, IA05_HDR_COUNTER))

    VhpSap.SetText sess, IA05_HDR_TEXT, VhpUtil.Clip(VhpUtil.JStr(item, "title"), 40)
    VhpSap.SetText sess, IA05_HDR_PLANT, CStr(ctx("sapPlant"))
    VhpSap.SetText sess, IA05_HDR_WORKCENTER, VhpMap.WorkCenter(VhpUtil.JStr(item, "mainWorkCenter"))
    VhpSap.Press sess, IA05_BTN_OPERATIONS
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (hoved)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (hoved)")

    row = 0
    For Each op In VhpOrder.Operations(item)
        EnterOperation sess, op, row, ctx, what
        row = row + 1
    Next op

    ConfirmSave ctx, VhpUtil.Dk("Arbejdsplanen for ") & VhpOrder.ItemLabel(item) & " (" & _
        VhpUtil.Clip(VhpUtil.JStr(item, "title"), 40) & VhpUtil.Dk(") er udfyldt i SAP med ") & row & _
        VhpUtil.Dk(" operation(er).")

    VhpSap.Press sess, ID_BTN_SAVE
    ReadTaskListNumbers sess, what, headerGroup, headerCounter, outGroup, outCounter
End Sub

' Gruppenummeret er det, SAP viste paa hovedet (som i det gamle script). Var
' det ikke et tal, tages det fra et succes-svar paa statuslinjen.
Private Sub ReadTaskListNumbers(ByVal sess As Object, ByVal what As String, _
                                ByVal headerGroup As String, ByVal headerCounter As String, _
                                ByRef outGroup As String, ByRef outCounter As String)
    Dim t As String
    Dim msg As String
    Dim num As String
    Dim hint As String

    hint = VhpUtil.Dk(" Se i IA07, om arbejdsplanen blev gemt, f{oe}r planen k{oe}res igen.")

    If VhpSap.HasPopup(sess) Then
        Err.Raise ERR_NEEDS_CHECK, "VhpSteps", what & VhpUtil.Dk(": SAP viste en dialog efter Gem (") & _
            VhpSap.PopupText(sess) & ")." & hint
    End If

    t = VhpSap.StatusType(sess)
    msg = VhpSap.StatusText(sess)
    If t = "E" Or t = "A" Then
        Err.Raise ERR_SAP, "VhpSteps", what & ": " & msg
    End If

    If VhpUtil.IsAllDigits(headerGroup) Then
        outGroup = headerGroup
    Else
        num = VhpMap.LongestDigitRun(msg)
        If t = "S" And Len(num) >= 4 Then
            outGroup = num
        Else
            Err.Raise ERR_NEEDS_CHECK, "VhpSteps", what & VhpUtil.Dk(": SAP svarede '") & msg & _
                VhpUtil.Dk("', og gruppenummeret kunne ikke l{ae}ses.") & hint
        End If
    End If

    If VhpUtil.IsAllDigits(headerCounter) Then
        outCounter = headerCounter
    Else
        outCounter = "1"
    End If
End Sub

' Een operation i oversigten. rowIndex er operationens nummer i listen
' (0, 1, 2 ...); den synlige linje findes af VisibleOperationRow.
Private Sub EnterOperation(ByVal sess As Object, ByVal op As Object, ByVal rowIndex As Long, _
                           ByVal ctx As Object, ByVal what As String)
    Dim vis As Long
    Dim ctrl As String
    Dim cellBase As String
    Dim dec As String
    Dim persons As Double
    Dim matGroup As String
    Dim vendor As String
    Dim svc As Object
    Dim opWhat As String

    opWhat = what & " " & VhpOrder.OpLabel(op)
    dec = CStr(ctx("decimalSep"))
    ctrl = UCase$(Trim$(VhpUtil.JStr(op, "controlKey")))
    persons = VhpUtil.JNum(op, "persons", 1)
    If persons < 1 Then persons = 1
    vendor = VhpMap.VendorNo(VhpUtil.JStr(op, "vendor"))
    matGroup = Trim$(VhpUtil.JStr(op, "materialGroup"))

    vis = VisibleOperationRow(sess, rowIndex)
    cellBase = IA05_OP_TABLE & "/"

    VhpSap.SetText sess, cellBase & IA05_COL_WORKCENTER & vis & "]", VhpMap.WorkCenter(VhpUtil.JStr(op, "workCenter"))
    VhpSap.SetText sess, cellBase & IA05_COL_CONTROLKEY & vis & "]", ctrl
    VhpSap.SetText sess, cellBase & IA05_COL_SHORTTEXT & vis & "]", VhpUtil.Clip(VhpUtil.JStr(op, "shortText"), 40)
    VhpSap.SetText sess, cellBase & IA05_COL_WORK & vis & "]", VhpMap.SapNumber(VhpUtil.JNum(op, "work"), dec)

    Select Case ctrl
        Case "PM01", "ZB01"
            ' Det gamle script satte ikke antal her. Er der flere personer
            ' paa, saettes det, saa SAP regner varigheden rigtigt.
            If persons > 1 Then
                VhpSap.SetText sess, cellBase & IA05_COL_PERSONS & vis & "]", VhpMap.SapNumber(persons, dec)
            End If

        Case "PM02"
            If Len(matGroup) = 0 Then matGroup = CStr(ctx("pm02MatGroup"))
            VhpSap.SetText sess, cellBase & IA05_COL_PERSONS & vis & "]", VhpMap.SapNumber(persons, dec)
            VhpSap.SetText sess, cellBase & IA05_COL_ORDERQTY & vis & "]", "1"
            VhpSap.SetText sess, cellBase & IA05_COL_ORDERUNIT & vis & "]", "AU"
            VhpSap.SetText sess, cellBase & IA05_COL_PRICE & vis & "]", VhpMap.SapNumber(VhpUtil.JNum(op, "price"), dec)
            VhpSap.SetText sess, cellBase & IA05_COL_PRICEUNIT & vis & "]", "1"
            VhpSap.SetText sess, cellBase & IA05_COL_MATGROUP & vis & "]", matGroup
            If Len(vendor) > 0 Then
                VhpSap.SetText sess, cellBase & IA05_COL_VENDOR & vis & "]", vendor
            End If

        Case "PM03"
            Set svc = VhpLookup.Service(ctx("lookups"), VhpUtil.JStr(op, "workCenter"))
            If Len(matGroup) = 0 And Not svc Is Nothing Then matGroup = VhpUtil.JStr(svc, "matGroup")
            VhpSap.SetText sess, cellBase & IA05_COL_PERSONS & vis & "]", VhpMap.SapNumber(persons, dec)
            If Len(matGroup) > 0 Then
                VhpSap.SetText sess, cellBase & IA05_COL_MATGROUP & vis & "]", matGroup
            End If
            If Len(vendor) > 0 Then
                VhpSap.SetText sess, cellBase & IA05_COL_VENDOR & vis & "]", vendor
            End If

        Case Else
            ' Valideringen stopper ukendte noegler, foer der aabnes en
            ' transaktion. Kommer vi alligevel hertil, stopper vi her.
            Err.Raise ERR_SAP, "VhpSteps", opWhat & VhpUtil.Dk(": ukendt kontroln{oe}gle '") & ctrl & "'."
    End Select

    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, opWhat
    VhpSap.FailOnError sess, opWhat

    If ctrl = "PM03" Then AddService sess, op, rowIndex, ctx, opWhat

    If VhpItf.HasText(VhpUtil.JStr(op, "longText")) Then
        UploadOperationText sess, op, rowIndex, ctx, opWhat
    End If
End Sub

' Operationsoversigten viser kun de linjer, der er plads til. Ligger
' operationen uden for, rulles der, og tabellen hentes igen - referencen er
' ugyldig efter en rulning. Er den synlig, roeres intet (som foer).
Private Function VisibleOperationRow(ByVal sess As Object, ByVal rowIndex As Long) As Long
    Dim tbl As Object
    Dim pos As Long
    Dim visibleRows As Long

    Set tbl = VhpSap.Fnd(sess, IA05_OP_TABLE)
    visibleRows = tbl.VisibleRowCount
    pos = tbl.VerticalScrollbar.Position

    If rowIndex >= pos And rowIndex < pos + visibleRows Then
        VisibleOperationRow = rowIndex - pos
        Exit Function
    End If

    tbl.VerticalScrollbar.Position = rowIndex
    Set tbl = VhpSap.Fnd(sess, IA05_OP_TABLE)
    pos = tbl.VerticalScrollbar.Position
    If rowIndex < pos Or rowIndex >= pos + visibleRows Then
        Err.Raise ERR_SAP, "VhpSteps", VhpUtil.Dk("IA05: kunne ikke rulle til operation nr. ") & (rowIndex + 1) & _
            VhpUtil.Dk(". G{oe}r SAP-vinduet st{oe}rre, og k{oe}r planen igen.")
    End If
    VisibleOperationRow = rowIndex - pos
End Function

' PM03: ydelsen fra modelydelsesspecifikationen, med timerne som maengde.
Private Sub AddService(ByVal sess As Object, ByVal op As Object, ByVal rowIndex As Long, _
                       ByVal ctx As Object, ByVal what As String)
    Dim vis As Long
    Dim svc As Object
    Dim serviceNo As String
    Dim found As Long

    Set svc = VhpLookup.Service(ctx("lookups"), VhpUtil.JStr(op, "workCenter"))
    If svc Is Nothing Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": ydelsesnummer mangler i Opslag.")
    End If
    serviceNo = VhpUtil.JStr(svc, "serviceNo")

    ' Knappen virker paa den linje, markoeren staar i.
    vis = VisibleOperationRow(sess, rowIndex)
    VhpSap.Focus sess, IA05_OP_TABLE & "/" & IA05_COL_SHORTTEXT & vis & "]"
    VhpSap.Press sess, IA05_BTN_SERVICES
    VhpSap.SetText sess, IA05_SRV_MODELSPEC, CStr(ctx("serviceSpec"))
    VhpSap.Press sess, IA05_SRV_MODELSPEC_OK
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (ydelser)")

    found = SelectServiceLines(sess, serviceNo)
    If found = 0 Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": ydelsen ") & serviceNo & _
            VhpUtil.Dk(" findes ikke i modelydelsesspecifikationen ") & CStr(ctx("serviceSpec")) & "."
    End If

    VhpSap.Press sess, IA05_SRV_ADOPT
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (ydelser)")
    VhpSap.SetText sess, IA05_SRV_QUANTITY, VhpMap.SapNumber(VhpUtil.JNum(op, "work"), CStr(ctx("decimalSep")))
    VhpSap.Focus sess, IA05_SRV_QUANTITY
    VhpSap.Press sess, ID_BTN_BACK
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (ydelser)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (ydelser)")
End Sub

' Marker alle linjer med ydelsesnummeret. Listen gennemgaas side for side;
' den slutter ved den foerste tomme linje (som i det gamle script).
Private Function SelectServiceLines(ByVal sess As Object, ByVal serviceNo As String) As Long
    Dim tbl As Object
    Dim visibleRows As Long
    Dim pos As Long
    Dim v As Long
    Dim cellText As String
    Dim hits As Long
    Dim pages As Long
    Dim cellId As String

    Set tbl = VhpSap.Fnd(sess, IA05_SRV_TABLE)
    visibleRows = tbl.VisibleRowCount
    pos = tbl.VerticalScrollbar.Position

    Do
        For v = 0 To visibleRows - 1
            cellId = IA05_SRV_TABLE & "/" & IA05_SRV_COL_SERVICE & v & "]"
            If Not VhpSap.Exists(sess, cellId) Then Exit Do
            cellText = Trim$(VhpSap.GetText(sess, cellId))
            If Len(cellText) = 0 Then Exit Do
            If cellText = serviceNo Then
                tbl.GetAbsoluteRow(pos + v).Selected = True
                hits = hits + 1
            End If
        Next v

        pages = pages + 1
        If pages > 100 Then Exit Do
        If pos + visibleRows >= tbl.RowCount Then Exit Do

        tbl.VerticalScrollbar.Position = pos + visibleRows
        Set tbl = VhpSap.Fnd(sess, IA05_SRV_TABLE)
        If tbl.VerticalScrollbar.Position = pos Then Exit Do
        pos = tbl.VerticalScrollbar.Position
    Loop

    SelectServiceLines = hits
End Function

' Operationens langtekst: editoren aabnes, kortteksten i foerste linje
' slettes, og ITF-filen uploades.
Private Sub UploadOperationText(ByVal sess As Object, ByVal op As Object, ByVal rowIndex As Long, _
                                ByVal ctx As Object, ByVal what As String)
    Dim vis As Long
    Dim path As String

    path = CStr(ctx("itfPath"))
    VhpItf.WriteItfFile path, VhpUtil.JStr(op, "longText"), False

    vis = VisibleOperationRow(sess, rowIndex)
    VhpSap.Focus sess, IA05_OP_TABLE & "/" & IA05_COL_LONGTEXT & vis & "]"
    VhpSap.VKey sess, 2
    VhpSap.SelectItem sess, LT_MENU_DELETE
    VhpSap.Press sess, LT_DELETE_CONFIRM
    UploadItf sess, path, what
    VhpSap.Press sess, ID_BTN_BACK
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (langtekst)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (langtekst)")
End Sub

' Tekst > Upload > ITF > filnavn. Editoren skal vaere aaben.
Private Sub UploadItf(ByVal sess As Object, ByVal path As String, ByVal what As String)
    VhpSap.SelectItem sess, LT_MENU_UPLOAD
    VhpSap.SelectItem sess, LT_FORMAT_ITF
    VhpSap.Focus sess, LT_FORMAT_ITF
    VhpSap.Press sess, LT_FORMAT_OK
    VhpSap.SetText sess, LT_FILENAME, path
    VhpSap.Press sess, LT_FILENAME_OK
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (upload af langtekst)")
End Sub

'==============================================================================
' IP04 - vedligeholdsposition
'==============================================================================
Public Function CreateItem(ByVal sess As Object, ByVal item As Object, ByVal ctx As Object, _
                           ByVal tlGroup As String, ByVal tlCounter As String) As String
    Dim what As String
    Dim prio As String
    Dim fl As Variant
    Dim entries As Collection

    what = "IP04 " & VhpOrder.ItemLabel(item)

    VhpSap.StartTransaction sess, TX_ITEM
    If Not VhpSap.SelectCombo(sess, IP04_CATEGORY, Array(CStr(ctx("planCategory")))) Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": plankategorien ") & CStr(ctx("planCategory")) & _
            VhpUtil.Dk(" findes ikke i SAP's liste.")
    End If
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what
    VhpSap.FailOnError sess, what

    ' Ingen ordreoprettelse - som det gamle script.
    VhpSap.SetChecked sess, IP04_NO_RELEASE, True
    VhpSap.SetText sess, IP04_TEXT, VhpUtil.Clip(VhpUtil.JStr(item, "title"), 40)
    VhpSap.SetText sess, IP04_FUNCLOC, Trim$(VhpUtil.JStr(item, "functionalLocation"))
    VhpSap.SetText sess, IP04_ORDERTYPE, Trim$(VhpUtil.JStr(item, "orderType"))
    VhpSap.SetText sess, IP04_ACTIVITY, VhpMap.ActivityCode(VhpUtil.JStr(item, "activityType"))
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what
    VhpSap.FailOnError sess, what

    VhpSap.SetText sess, IP04_WORKCENTER, VhpMap.WorkCenter(VhpUtil.JStr(item, "mainWorkCenter"))
    prio = VhpMap.PriorityKey(VhpUtil.JStr(item, "priority"))
    If Len(prio) > 0 Then
        If Not VhpSap.SelectCombo(sess, IP04_PRIORITY, Array(prio), VhpUtil.JStr(item, "priority")) Then
            AddStepWarning ctx, VhpOrder.ItemLabel(item) & VhpUtil.Dk(": prioriteten ") & prio & _
                VhpUtil.Dk(" kunne ikke v{ae}lges i SAP. S{ae}t den i IP05.")
        End If
    End If

    VhpSap.SetText sess, IP04_TL_TYPE, CStr(ctx("taskListType"))
    VhpSap.SetText sess, IP04_TL_GROUP, tlGroup
    VhpSap.SetText sess, IP04_TL_COUNTER, tlCounter
    VhpSap.Focus sess, IP04_TL_COUNTER
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (arbejdsplan)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (arbejdsplan)")

    ' Objektlisten: een funktionsplads ad gangen gennem udvaelgelsen.
    Set entries = VhpMap.ObjectListEntries(VhpUtil.JStr(item, "objectList"))
    If entries.Count > 0 Then
        VhpSap.SelectItem sess, IP04_TAB_OBJECTS
        For Each fl In entries
            VhpSap.Press sess, IP04_OBJ_ADD_FL
            VhpSap.Press sess, IP04_OBJ_MULTI
            VhpSap.Press sess, IP04_OBJ_CLEAR
            VhpSap.SetText sess, IP04_OBJ_VALUE, CStr(fl)
            VhpSap.Press sess, IP04_OBJ_TAKE
            VhpSap.Press sess, ID_BTN_EXECUTE
            VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (objektliste ") & CStr(fl) & ")"
            VhpSap.FailOnError sess, what & VhpUtil.Dk(" (objektliste ") & CStr(fl) & ")"
        Next fl
    End If

    ' Status og revision
    VhpSap.SelectItem sess, IP04_TAB_CUSTOM
    VhpSap.SetText sess, IP04_USER_STATUS, Trim$(VhpUtil.JStr(item, "userStatus"))
    VhpSap.SetText sess, IP04_NONFLOW_STATUS, Trim$(VhpUtil.JStr(item, "nonFlowUserStatus"))
    VhpSap.SetText sess, IP04_REVISION, VhpMap.RevisionValue(VhpUtil.JBool(item, "revision"), VhpUtil.JStr(item, "revisionMark"))
    VhpSap.SetText sess, IP04_REV_YEAR, CStr(Year(Date))
    VhpSap.SetText sess, IP04_REV_BY, UCase$(Trim$(VhpUtil.JStr(item, "responsibleInitials")))

    ConfirmSave ctx, VhpUtil.Dk("Positionen for ") & VhpOrder.ItemLabel(item) & VhpUtil.Dk(" er udfyldt i SAP (arbejdsplan ") & _
        tlGroup & "/" & tlCounter & ", " & entries.Count & VhpUtil.Dk(" objekt(er) p{aa} objektlisten).")

    CreateItem = SaveAndReadNumber(sess, what, 3, _
        VhpUtil.Dk(" Se i IP06, om positionen blev oprettet, f{oe}r planen k{oe}res igen."))
End Function

'==============================================================================
' IP05 - itemets langtekst
'==============================================================================
Public Sub UploadItemLongText(ByVal sess As Object, ByVal item As Object, ByVal ctx As Object, _
                              ByVal sapItemNo As String)
    Dim what As String
    Dim path As String
    Dim t As String

    what = "IP05 " & VhpOrder.ItemLabel(item) & " (" & sapItemNo & ")"
    path = CStr(ctx("itfPath"))
    VhpItf.WriteItfFile path, VhpUtil.JStr(item, "longText"), True

    VhpSap.StartTransaction sess, TX_ITEM_CHANGE
    VhpSap.SetText sess, IP05_ITEM_NO, sapItemNo
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what
    VhpSap.FailOnError sess, what

    VhpSap.Press sess, IP05_LONGTEXT
    UploadItf sess, path, what
    VhpSap.Press sess, ID_BTN_BACK
    VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (langtekst)")
    VhpSap.FailOnError sess, what & VhpUtil.Dk(" (langtekst)")

    ConfirmSave ctx, VhpUtil.Dk("Langteksten for ") & VhpOrder.ItemLabel(item) & _
        VhpUtil.Dk(" er uploadet til position ") & sapItemNo & "."

    VhpSap.Press sess, ID_BTN_SAVE
    If VhpSap.HasPopup(sess) Then
        Err.Raise ERR_NEEDS_CHECK, "VhpSteps", what & VhpUtil.Dk(": SAP viste en dialog efter Gem (") & _
            VhpSap.PopupText(sess) & VhpUtil.Dk("). Se i IP03, om langteksten blev gemt.")
    End If
    t = VhpSap.StatusType(sess)
    If t = "E" Or t = "A" Then
        Err.Raise ERR_SAP, "VhpSteps", what & ": " & VhpSap.StatusText(sess)
    End If
End Sub

'==============================================================================
' IP01 - vedligeholdsplan
'==============================================================================
Public Function CreatePlan(ByVal sess As Object, ByVal order As Object, ByVal itemNos As Collection, _
                           ByVal ctx As Object) As String
    Dim plan As Object
    Dim what As String
    Dim title As String
    Dim cycle As Double
    Dim cycleText As String
    Dim unitText As String
    Dim firstDue As Date
    Dim hz As Object
    Dim j As Long
    Dim dec As String
    Dim sortId As String
    Dim sortText As String

    Set plan = VhpUtil.JObj(order, "plan")
    what = "IP01 " & VhpUtil.JStr(plan, "planId")
    dec = CStr(ctx("decimalSep"))

    title = VhpUtil.Clip(VhpUtil.JStr(plan, "title"), 40)
    cycle = VhpUtil.JNum(plan, "cycle")
    cycleText = VhpMap.SapNumber(cycle, dec)
    unitText = VhpMap.NormalizeUnit(VhpUtil.JStr(plan, "unit"))
    If Not VhpUtil.TryParseYmd(VhpUtil.JStr(plan, "plannedDate"), firstDue) Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": ugyldig dato for f{oe}rste forfald.")
    End If
    Set hz = VhpLookup.Horizon(ctx("lookups"), cycle, unitText)
    If hz Is Nothing Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": kaldshorisont mangler i Opslag.")
    End If

    VhpSap.StartTransaction sess, TX_PLAN
    If Not VhpSap.SelectCombo(sess, IP01_CATEGORY, Array(CStr(ctx("planCategory")))) Then
        Err.Raise ERR_SAP, "VhpSteps", what & VhpUtil.Dk(": plankategorien ") & CStr(ctx("planCategory")) & _
            VhpUtil.Dk(" findes ikke i SAP's liste.")
    End If
    VhpSap.SetText sess, IP01_STRATEGY, ""
    VhpSap.Enter sess
    VhpSap.FailOnPopup sess, what
    VhpSap.FailOnError sess, what

    ' Positionerne knyttes til planen een for een (som i det gamle script).
    For j = 1 To itemNos.Count
        VhpSap.SetText sess, IP01_TEXT, title
        VhpSap.SetText sess, IP01_CYCLE, cycleText
        VhpSap.SetText sess, IP01_CYCLE_UNIT, unitText
        VhpSap.Press sess, IP01_ITEM_LINK
        ' Foerste gang spoerger SAP; det gamle script svarede med Enter.
        If j = 1 And VhpSap.HasPopup(sess) Then VhpSap.VKey sess, 0, "wnd[1]"
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"

        VhpSap.SetText sess, IP01_ITEM_NO, CStr(itemNos(j))
        VhpSap.Press sess, ID_BTN_EXECUTE
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        VhpSap.FailOnError sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        VhpSap.Fnd(sess, IP01_ITEM_GRID).SelectedRows = "0"
        VhpSap.Press sess, IP01_ITEM_CHOOSE
        VhpSap.FailOnPopup sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
        VhpSap.FailOnError sess, what & VhpUtil.Dk(" (position ") & CStr(itemNos(j)) & ")"
    Next j

    VhpSap.SetText sess, IP01_TEXT, title
    VhpSap.SetText sess, IP01_CYCLE, cycleText
    VhpSap.SetText sess, IP01_CYCLE_UNIT, unitText
    VhpSap.Focus sess, IP01_CYCLE_UNIT

    ' Planlaegningsparametre
    VhpSap.SelectItem sess, IP01_TAB_SCHEDULING
    VhpSap.SetText sess, IP01_HORIZON, VhpUtil.JStr(hz, "horizon")
    VhpSap.SetText sess, IP01_HORIZON_QUALIFIER, CStr(ctx("horizonQualifier"))
    VhpSap.SetText sess, IP01_SCHED_PERIOD, VhpUtil.JStr(hz, "period")
    VhpSap.SetText sess, IP01_SCHED_UNIT, VhpUtil.JStr(hz, "periodUnit")
    VhpSap.SetText sess, IP01_START_DATE, VhpMap.SapDate(VhpMap.StartDate(firstDue, cycle, unitText))
    VhpSap.SelectItem sess, IP01_KEY_DATE

    ' Sorteringsfeltet. Det gamle script satte opslagets Id som noegle. Her
    ' proeves Id'et, Id'et med nuller foran og til sidst teksten.
    sortId = VhpUtil.JStr(plan, "sortFieldId")
    sortText = VhpUtil.JStr(plan, "sortField")
    If Len(sortId) > 0 Or Len(sortText) > 0 Then
        VhpSap.SelectItem sess, IP01_TAB_SORT
        If VhpSap.SelectCombo(sess, IP01_SORT_FIELD, SortKeys(sortId), sortText) Then
            VhpSap.Focus sess, IP01_SORT_FIELD
        Else
            AddStepWarning ctx, VhpUtil.JStr(plan, "planId") & VhpUtil.Dk(": sorteringsfeltet '") & sortText & _
                VhpUtil.Dk("' kunne ikke v{ae}lges i SAP. S{ae}t det i IP02.")
        End If
    End If

    ConfirmSave ctx, VhpUtil.Dk("Planen ") & VhpUtil.JStr(plan, "planId") & " (" & title & VhpUtil.Dk(") er udfyldt i SAP med ") & _
        itemNos.Count & VhpUtil.Dk(" position(er), cyklus ") & cycleText & " " & unitText & _
        VhpUtil.Dk(" og startdato ") & VhpMap.SapDate(VhpMap.StartDate(firstDue, cycle, unitText)) & "."

    CreatePlan = SaveAndReadNumber(sess, what, 3, _
        VhpUtil.Dk(" Se i IP03, om planen blev oprettet, f{oe}r den k{oe}res igen."))
End Function

Private Function SortKeys(ByVal sortId As String) As Variant
    If Len(sortId) = 0 Then
        SortKeys = Array("")
    ElseIf VhpUtil.IsAllDigits(sortId) Then
        SortKeys = Array(sortId, Format$(CLng(sortId), "000"), Format$(CLng(sortId), "00"))
    Else
        SortKeys = Array(sortId)
    End If
End Function

'==============================================================================
' Faelles
'==============================================================================

' Gem og laes nummeret paa det, der blev oprettet. Et nummer tages KUN fra et
' svar af typen S eller W. E/A betyder, at intet blev gemt. Alt andet - en
' dialog, et svar uden nummer - betyder, at nogen skal se efter i SAP, foer
' planen koeres igen. Ellers kunne den samme position blive oprettet to gange.
Private Function SaveAndReadNumber(ByVal sess As Object, ByVal what As String, ByVal minDigits As Long, _
                                   ByVal checkHint As String) As String
    Dim t As String
    Dim msg As String
    Dim num As String

    VhpSap.Press sess, ID_BTN_SAVE

    If VhpSap.HasPopup(sess) Then
        Err.Raise ERR_NEEDS_CHECK, "VhpSteps", what & VhpUtil.Dk(": SAP viste en dialog efter Gem (") & _
            VhpSap.PopupText(sess) & ")." & checkHint
    End If

    t = VhpSap.StatusType(sess)
    msg = VhpSap.StatusText(sess)
    If t = "E" Or t = "A" Then
        Err.Raise ERR_SAP, "VhpSteps", what & ": " & msg
    End If

    num = VhpMap.LongestDigitRun(msg)
    If (t = "S" Or t = "W") And Len(num) >= minDigits Then
        SaveAndReadNumber = num
        Exit Function
    End If

    Err.Raise ERR_NEEDS_CHECK, "VhpSteps", what & VhpUtil.Dk(": SAP svarede '") & msg & "' (" & t & _
        VhpUtil.Dk("), og nummeret kunne ikke l{ae}ses.") & checkHint
End Function

' Bekraeft hvert gem (indstillingen ConfirmSave). Ja gemmer. Nej springer
' planen eller anmodningen over uden at gemme. Annuller stopper hele
' koerslen. Bruges ogsaa af VhpFlSteps.
Public Sub ConfirmSave(ByVal ctx As Object, ByVal text As String)
    Dim answer As VbMsgBoxResult

    If Not CBool(ctx("confirmSave")) Then Exit Sub

    answer = MsgBox(text & vbLf & vbLf & _
        VhpUtil.Dk("Se SAP-vinduet igennem. Skal det gemmes nu?") & vbLf & vbLf & _
        VhpUtil.Dk("Ja = gem i SAP") & vbLf & _
        VhpUtil.Dk("Nej = spring denne plan/anmodning over (der gemmes ikke)") & vbLf & _
        VhpUtil.Dk("Annuller = stop hele k{oe}rslen"), _
        vbYesNoCancel + vbQuestion + vbSystemModal, VHP_APP_NAME)

    Select Case answer
        Case vbYes
            ' videre
        Case vbNo
            Err.Raise ERR_SKIP_PLAN, "VhpSteps", VhpUtil.Dk("Sprunget over: der blev svaret Nej til at gemme.")
        Case Else
            Err.Raise ERR_STOP_RUN, "VhpSteps", VhpUtil.Dk("K{oe}rslen blev stoppet.")
    End Select
End Sub

Private Sub AddStepWarning(ByVal ctx As Object, ByVal msg As String)
    ctx("warnings").Add msg
End Sub
