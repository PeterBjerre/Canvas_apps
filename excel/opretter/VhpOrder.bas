Attribute VB_Name = "VhpOrder"
Option Explicit
'==============================================================================
' VhpOrder - ordrefilen: indlaesning, gruppering og validering.
'
' Ordren er flad, som SharePoint-listerne (schema/vhplan-sap-order.schema.json):
' plan, items, operations og materials hver for sig. Prepare haenger
' operationerne og materialerne paa deres item, saa resten af koden kan
' arbejde item for item - een arbejdsplan pr. item.
'
' Validate finder ALT, der ville faa SAP-delen til at stoppe halvvejs, FOER
' der oprettes noget. En fejl fanget her koster sekunder; den samme fejl
' fanget i IP01 koster arbejdsplaner og positioner uden en plan.
'==============================================================================

Public Function LoadOrder(ByVal path As String) As Object
    Dim o As Object
    Dim msg As String

    On Error GoTo BadJson
    Set o = VhpFiles.ReadJson(path)
    On Error GoTo 0

    If o Is Nothing Then Err.Raise ERR_ORDER, "VhpOrder", VhpUtil.Dk("Filen er tom.")
    If TypeName(o) <> "Dictionary" Then Err.Raise ERR_ORDER, "VhpOrder", VhpUtil.Dk("Filen er ikke en ordre.")
    If VhpUtil.JStr(o, "kind") <> ORDER_KIND Then
        Err.Raise ERR_ORDER, "VhpOrder", VhpUtil.Dk("Filen er ikke en VH-plan-ordre (kind er '") & _
            VhpUtil.JStr(o, "kind") & "')."
    End If
    If VhpUtil.JLng(o, "version") <> 1 Then
        Err.Raise ERR_ORDER, "VhpOrder", VhpUtil.Dk("Ordren har version ") & VhpUtil.JStr(o, "version") & _
            VhpUtil.Dk(". Denne udgave af opretteren kender kun version 1 {-} hent den nyeste.")
    End If

    Prepare o
    Set LoadOrder = o
    Exit Function

BadJson:
    msg = Err.Description
    Err.Raise ERR_ORDER, "VhpOrder", VhpUtil.Dk("Filen kunne ikke l{ae}ses som JSON: ") & msg
End Function

' Operationer og materialer paa deres item. Operationerne sorteres efter
' operationsnummer - det er den raekkefoelge, de faar i SAP.
Public Sub Prepare(ByVal order As Object)
    Dim item As Object
    Dim op As Object
    Dim m As Object
    Dim owner As Object
    Dim orphanOps As New Collection
    Dim orphanMats As New Collection

    For Each item In VhpUtil.JList(order, "items")
        If item.Exists("_ops") Then item.Remove "_ops"
        If item.Exists("_mats") Then item.Remove "_mats"
        item.Add "_ops", New Collection
        item.Add "_mats", New Collection
    Next item

    For Each op In VhpUtil.JList(order, "operations")
        Set owner = FindItem(order, VhpUtil.JLng(op, "itemSpId", -1), VhpUtil.JStr(op, "itemId"))
        If owner Is Nothing Then
            orphanOps.Add op
        Else
            InsertOperation owner("_ops"), op
        End If
    Next op

    For Each m In VhpUtil.JList(order, "materials")
        Set owner = FindItem(order, -1, VhpUtil.JStr(m, "itemId"))
        If owner Is Nothing Then
            orphanMats.Add m
        Else
            owner("_mats").Add m
        End If
    Next m

    If order.Exists("_orphanOps") Then order.Remove "_orphanOps"
    If order.Exists("_orphanMats") Then order.Remove "_orphanMats"
    order.Add "_orphanOps", orphanOps
    order.Add "_orphanMats", orphanMats
End Sub

Private Function FindItem(ByVal order As Object, ByVal spId As Long, ByVal itemId As String) As Object
    Dim item As Object
    For Each item In VhpUtil.JList(order, "items")
        If spId >= 0 And VhpUtil.JLng(item, "spId", -2) = spId Then
            Set FindItem = item
            Exit Function
        End If
    Next item
    If Len(itemId) = 0 Then Exit Function
    For Each item In VhpUtil.JList(order, "items")
        If StrComp(VhpUtil.JStr(item, "itemId"), itemId, vbTextCompare) = 0 Then
            Set FindItem = item
            Exit Function
        End If
    Next item
End Function

Private Sub InsertOperation(ByVal ops As Collection, ByVal op As Object)
    Dim i As Long
    For i = 1 To ops.Count
        If OpComesBefore(op, ops(i)) Then
            ops.Add op, Before:=i
            Exit Sub
        End If
    Next i
    ops.Add op
End Sub

Private Function OpComesBefore(ByVal a As Object, ByVal b As Object) As Boolean
    Dim na As Double, nb As Double
    na = VhpUtil.JNum(a, "operationNo", 999999)
    nb = VhpUtil.JNum(b, "operationNo", 999999)
    If na <> nb Then
        OpComesBefore = (na < nb)
    Else
        OpComesBefore = (VhpUtil.JLng(a, "spId") < VhpUtil.JLng(b, "spId"))
    End If
End Function

Public Function Operations(ByVal item As Object) As Collection
    If item.Exists("_ops") Then
        Set Operations = item("_ops")
    Else
        Set Operations = New Collection
    End If
End Function

Public Function Materials(ByVal item As Object) As Collection
    If item.Exists("_mats") Then
        Set Materials = item("_mats")
    Else
        Set Materials = New Collection
    End If
End Function

'==============================================================================
' Etiketter til beskeder
'==============================================================================

Public Function PlanLabel(ByVal order As Object) As String
    PlanLabel = VhpUtil.JStr(VhpUtil.JObj(order, "plan"), "planId")
End Function

Public Function ItemLabel(ByVal item As Object) As String
    Dim s As String
    s = VhpUtil.JStr(item, "itemId")
    If Len(s) = 0 Then s = "item " & VhpUtil.JStr(item, "spId")
    ItemLabel = s
End Function

Public Function OpLabel(ByVal op As Object) As String
    Dim no As String
    no = VhpUtil.JStr(op, "operationNo")
    If Len(no) = 0 Then no = VhpUtil.JStr(op, "taskItemId")
    OpLabel = "operation " & no & " (" & VhpUtil.Clip(VhpUtil.JStr(op, "shortText"), 30) & ")"
End Function

'==============================================================================
' Validering
'==============================================================================

' Resultat: Dictionary med "errors" og "warnings" (Collections af tekster).
' En fejl stopper planen. En advarsel vises, men planen kan oprettes.
Public Function Validate(ByVal order As Object, ByVal lk As Object) As Object
    Dim res As Object
    Dim plan As Object
    Dim item As Object
    Dim op As Object
    Dim m As Object
    Dim env As String
    Dim plantRec As Object
    Dim hz As Object
    Dim cycle As Double
    Dim unitText As String
    Dim firstDue As Date
    Dim title As String

    Set res = VhpUtil.NewDict()
    res.Add "errors", New Collection
    res.Add "warnings", New Collection
    Set Validate = res

    Set plan = VhpUtil.JObj(order, "plan")
    If plan Is Nothing Then
        AddError res, VhpUtil.Dk("Ordren har ingen plan.")
        Exit Function
    End If

    '--- Planen ---------------------------------------------------------------
    env = UCase$(VhpUtil.JStr(order, "environment"))
    If env <> "DEV" And env <> "TEST" And env <> "PROD" Then
        AddError res, VhpUtil.Dk("Ordren siger ikke, om den kommer fra DEV, TEST eller PROD (environment er '") & env & "')."
    End If

    If VhpUtil.JHas(plan, "strategyKey") Then
        AddError res, VhpUtil.Dk("Planen er en strategiplan (") & VhpUtil.JStr(plan, "strategyKey") & _
            VhpUtil.Dk("). Opretteren kan endnu kun oprette planer med {e}n cyklus (IP01 uden strategi). Opret den i SAP i h{aa}nden.")
    End If

    title = Trim$(VhpUtil.JStr(plan, "title"))
    If Len(title) = 0 Then
        AddError res, VhpUtil.Dk("Planen har ingen tekst.")
    ElseIf Len(title) > 40 Then
        AddWarning res, VhpUtil.Dk("Planens tekst er ") & Len(title) & _
            VhpUtil.Dk(" tegn. SAP gemmer de f{oe}rste 40: '") & Left$(title, 40) & "'."
    End If

    cycle = VhpUtil.JNum(plan, "cycle")
    unitText = VhpMap.NormalizeUnit(VhpUtil.JStr(plan, "unit"))
    If cycle <= 0 Then AddError res, VhpUtil.Dk("Planen har ingen cyklus.")
    Select Case unitText
        Case "DAY", "WK", "MON", "YR"
        Case Else
            AddError res, VhpUtil.Dk("Cyklusenheden '") & VhpUtil.JStr(plan, "unit") & _
                VhpUtil.Dk("' kan ikke bruges. Opretteren laver tidsbaserede planer: DAY, WK, MON eller YR.")
    End Select

    If Not VhpUtil.TryParseYmd(VhpUtil.JStr(plan, "plannedDate"), firstDue) Then
        AddError res, VhpUtil.Dk("Planen har ingen gyldig dato for f{oe}rste forfald (plannedDate er '") & _
            VhpUtil.JStr(plan, "plannedDate") & "')."
    End If

    Set plantRec = VhpLookup.Plant(lk, VhpUtil.JStr(plan, "plant"))
    If plantRec Is Nothing Then
        AddError res, VhpUtil.Dk("V{ae}rket '") & VhpUtil.JStr(plan, "plant") & _
            VhpUtil.Dk("' st{aa}r ikke i Opslag (tabellen V{ae}rker).")
    Else
        If VhpUtil.IsBlank(VhpUtil.JStr(plantRec, "sapPlant")) Then
            AddError res, VhpUtil.Dk("V{ae}rket '") & VhpUtil.JStr(plan, "plant") & _
                VhpUtil.Dk("' mangler SAP-v{ae}rk i Opslag.")
        End If
        If VhpUtil.IsBlank(VhpUtil.JStr(plantRec, "profile")) Then
            AddError res, VhpUtil.Dk("V{ae}rket '") & VhpUtil.JStr(plan, "plant") & _
                VhpUtil.Dk("' mangler arbejdsplanprofil i Opslag.")
        End If
    End If

    If cycle > 0 Then
        Set hz = VhpLookup.Horizon(lk, cycle, unitText)
        If hz Is Nothing Then
            AddError res, VhpUtil.Dk("Kaldshorisont mangler for cyklus ") & VhpMap.NumberKey(cycle) & " " & unitText & _
                VhpUtil.Dk(". Tilf{oe}j en r{ae}kke i Opslag (tabellen Kaldshorisont).")
        ElseIf VhpUtil.JHas(plan, "schedulingPeriod") Then
            If VhpMap.NumberKey(VhpUtil.JNum(plan, "schedulingPeriod")) <> Replace(VhpUtil.JStr(hz, "period"), ",", ".") Then
                AddWarning res, VhpUtil.Dk("Appen har planl{ae}gningsperiode ") & VhpUtil.JStr(plan, "schedulingPeriod") & _
                    VhpUtil.Dk(", Opslag siger ") & VhpUtil.JStr(hz, "period") & " " & VhpUtil.JStr(hz, "periodUnit") & _
                    VhpUtil.Dk(" for cyklussen. Opslag bruges.")
            End If
        End If
    End If

    If Not VhpUtil.JHas(plan, "sortField") And Not VhpUtil.JHas(plan, "sortFieldId") Then
        AddWarning res, VhpUtil.Dk("Planen har intet sorteringsfelt og oprettes uden.")
    End If

    '--- Items ----------------------------------------------------------------
    If VhpUtil.JList(order, "items").Count = 0 Then
        AddError res, VhpUtil.Dk("Planen har ingen items.")
    End If

    For Each item In VhpUtil.JList(order, "items")
        ValidateItem res, item, plantRec, lk
    Next item

    For Each op In order("_orphanOps")
        AddError res, VhpUtil.Dk("Operationen ") & VhpUtil.JStr(op, "taskItemId") & " (" & _
            VhpUtil.JStr(op, "shortText") & VhpUtil.Dk(") h{oe}rer til et item, der ikke er i ordren.")
    Next op
    For Each m In order("_orphanMats")
        AddWarning res, VhpUtil.Dk("Materialet ") & VhpUtil.JStr(m, "materialNo") & _
            VhpUtil.Dk(" h{oe}rer til et item, der ikke er i ordren, og oprettes ikke.")
    Next m
End Function

Private Sub ValidateItem(ByVal res As Object, ByVal item As Object, ByVal plantRec As Object, ByVal lk As Object)
    Dim lbl As String
    Dim title As String
    Dim op As Object
    Dim m As Object

    lbl = ItemLabel(item) & ": "

    title = Trim$(VhpUtil.JStr(item, "title"))
    If Len(title) = 0 Then
        AddError res, lbl & VhpUtil.Dk("mangler kort tekst.")
    ElseIf Len(title) > 40 Then
        AddWarning res, lbl & VhpUtil.Dk("kort tekst er ") & Len(title) & _
            VhpUtil.Dk(" tegn. SAP gemmer de f{oe}rste 40.")
    End If

    If VhpUtil.IsBlank(VhpUtil.JStr(item, "functionalLocation")) Then
        AddError res, lbl & VhpUtil.Dk("mangler funktionsplads.")
    End If
    If VhpUtil.IsBlank(VhpUtil.JStr(item, "orderType")) Then
        AddError res, lbl & VhpUtil.Dk("mangler ordreart.")
    End If
    If Len(VhpMap.ActivityCode(VhpUtil.JStr(item, "activityType"))) = 0 Then
        AddError res, lbl & VhpUtil.Dk("mangler aktivitetstype.")
    End If
    If Len(VhpMap.WorkCenter(VhpUtil.JStr(item, "mainWorkCenter"))) = 0 Then
        AddError res, lbl & VhpUtil.Dk("mangler arbejdscenter.")
    End If
    If VhpUtil.JHas(item, "priority") Then
        If Len(VhpMap.PriorityKey(VhpUtil.JStr(item, "priority"))) = 0 Then
            AddWarning res, lbl & VhpUtil.Dk("prioriteten '") & VhpUtil.JStr(item, "priority") & _
                VhpUtil.Dk("' kan ikke overs{ae}ttes. Feltet efterlades, som SAP s{ae}tter det.")
        End If
    End If

    If Operations(item).Count = 0 Then
        AddError res, lbl & VhpUtil.Dk("har ingen operationer. Hvert item f{aa}r sin egen arbejdsplan, og den skal have mindst {e}n.")
    End If

    For Each op In Operations(item)
        ValidateOperation res, lbl, op, plantRec, lk
    Next op

    For Each m In Materials(item)
        AddWarning res, lbl & VhpUtil.Dk("materiale ") & VhpUtil.JStr(m, "materialNo") & " (" & _
            VhpUtil.JStr(m, "quantity") & " " & VhpUtil.JStr(m, "unit") & VhpUtil.Dk(") p{aa} operation ") & _
            VhpUtil.JStr(m, "operationNo") & VhpUtil.Dk(" oprettes ikke automatisk. Tilf{oe}j det i IA06 bagefter.")
    Next m
End Sub

Private Sub ValidateOperation(ByVal res As Object, ByVal lbl As String, ByVal op As Object, _
                              ByVal plantRec As Object, ByVal lk As Object)
    Dim ctrl As String
    Dim opLbl As String
    Dim svc As Object
    Dim shortText As String

    opLbl = lbl & OpLabel(op) & ": "
    ctrl = UCase$(Trim$(VhpUtil.JStr(op, "controlKey")))

    shortText = Trim$(VhpUtil.JStr(op, "shortText"))
    If Len(shortText) = 0 Then
        AddError res, opLbl & VhpUtil.Dk("mangler kort tekst.")
    ElseIf Len(shortText) > 40 Then
        AddWarning res, opLbl & VhpUtil.Dk("kort tekst er l{ae}ngere end 40 tegn og bliver afkortet.")
    End If

    If Len(VhpMap.WorkCenter(VhpUtil.JStr(op, "workCenter"))) = 0 Then
        AddError res, opLbl & VhpUtil.Dk("mangler arbejdscenter.")
    End If

    Select Case ctrl
        Case "PM01", "ZB01"
            ' Intern tid. Intet ekstra.
        Case "PM02"
            If VhpUtil.JNum(op, "price") <= 0 Then
                AddWarning res, opLbl & VhpUtil.Dk("PM02 uden pris.")
            End If
            If VhpUtil.IsBlank(VhpUtil.JStr(op, "materialGroup")) Then
                AddWarning res, opLbl & VhpUtil.Dk("PM02 uden varegruppe. ") & _
                    VhpConfig.Setting(SET_PM02_MATGROUP) & VhpUtil.Dk(" bruges (Indstillinger).")
            End If
        Case "PM03"
            If VhpUtil.JNum(op, "work") <= 0 Then
                AddError res, opLbl & VhpUtil.Dk("PM03 skal have timer {-} de er ydelsens m{ae}ngde.")
            End If
            Set svc = VhpLookup.Service(lk, VhpUtil.JStr(op, "workCenter"))
            If svc Is Nothing Then
                AddError res, opLbl & VhpUtil.Dk("ydelsesnummer mangler for arbejdscentret ") & _
                    VhpMap.WorkCenter(VhpUtil.JStr(op, "workCenter")) & _
                    VhpUtil.Dk(" i Opslag (tabellen Ydelser, endelsen ") & _
                    VhpMap.ServiceSuffix(VhpUtil.JStr(op, "workCenter")) & ")."
            ElseIf VhpUtil.IsBlank(VhpUtil.JStr(svc, "serviceNo")) Then
                AddError res, opLbl & VhpUtil.Dk("ydelsesnummeret for ") & _
                    VhpMap.ServiceSuffix(VhpUtil.JStr(op, "workCenter")) & VhpUtil.Dk(" er tomt i Opslag.")
            End If
            If Not plantRec Is Nothing Then
                If VhpUtil.IsBlank(VhpUtil.JStr(plantRec, "serviceSpec")) Then
                    AddError res, opLbl & VhpUtil.Dk("v{ae}rket mangler modelydelsesspecifikation i Opslag (PM03).")
                End If
            End If
        Case ""
            AddError res, opLbl & VhpUtil.Dk("mangler kontroln{oe}gle (PM01, ZB01, PM02 eller PM03).")
        Case Else
            AddError res, opLbl & VhpUtil.Dk("kontroln{oe}glen '") & ctrl & _
                VhpUtil.Dk("' kender opretteren ikke. Den kan PM01, ZB01, PM02 og PM03.")
    End Select
End Sub

Private Sub AddError(ByVal res As Object, ByVal msg As String)
    res("errors").Add msg
End Sub

Private Sub AddWarning(ByVal res As Object, ByVal msg As String)
    res("warnings").Add msg
End Sub
