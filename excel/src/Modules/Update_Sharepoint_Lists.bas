Attribute VB_Name = "Update_Sharepoint_Lists"
Option Explicit

Private Const PLAN_PUBLISHED_STATUS As String = "Published"
Private Const SYNC_STATUS_SENT As String = "SENT"
Private Const SYNC_STATUS_SKIPPED As String = "SKIPPED"
Private Const SYNC_STATUS_ERROR As String = "ERROR"
Private Const SYNC_ROW_RETRY_MAX As Long = 1
Private Const SYNC_ROW_RETRY_WAIT_MS As Long = 1200

Public Sub SyncSelectedCreatedRowsToSharePoint()
    Dim wsPlans As Worksheet
    Dim wsItems As Worksheet
    Dim wsTaskLists As Worksheet
    Dim selectedPlanSet As Object

    Dim authHeader As String
    Dim requestDigest As String
    Dim plansItemsUrl As String
    Dim itemsItemsUrl As String
    Dim tlItemsUrl As String

    Dim plansSent As Long
    Dim plansSkipped As Long
    Dim plansFailed As Long
    Dim itemsSent As Long
    Dim itemsSkipped As Long
    Dim itemsFailed As Long
    Dim tlSent As Long
    Dim tlSkipped As Long
    Dim tlFailed As Long

    On Error GoTo SyncError

    Set wsPlans = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    Set wsTaskLists = ThisWorkbook.Worksheets(WS_MAINTENANCE_TL)

    Set selectedPlanSet = BuildSelectedPlanSet(wsPlans)
    If selectedPlanSet Is Nothing Then
        MsgBox "Ingen planer er markeret med CreateInSAP. Ingen SharePoint-opdateringer udfoert.", vbInformation + vbOKOnly
        Exit Sub
    End If

    If selectedPlanSet.Count = 0 Then
        MsgBox "Ingen planer er markeret med CreateInSAP. Ingen SharePoint-opdateringer udfoert.", vbInformation + vbOKOnly
        Exit Sub
    End If

    authHeader = GetSharePointAuthHeaderForSync()
    plansItemsUrl = Trim$(GetSharePointPlansItemsUrlForSync())
    itemsItemsUrl = Trim$(GetSharePointItemsItemsUrlForSync())
    tlItemsUrl = Trim$(GetSharePointTlItemsUrlForSync())

    If Len(plansItemsUrl) = 0 Or Len(itemsItemsUrl) = 0 Or Len(tlItemsUrl) = 0 Then
        MsgBox "SharePoint URL mangler. Kontroller konfigurationen i modSharePointImport.", vbCritical + vbOKOnly
        Exit Sub
    End If

    requestDigest = GetSharePointRequestDigest(plansItemsUrl, authHeader)
    If Len(requestDigest) = 0 Then
        MsgBox "Kunne ikke hente SharePoint request digest (contextinfo). Sync afbrudt.", vbCritical + vbOKOnly
        Exit Sub
    End If

    SyncMaintenancePlans wsPlans, plansItemsUrl, authHeader, requestDigest, selectedPlanSet, plansSent, plansSkipped, plansFailed
    SyncMaintenanceItems wsItems, itemsItemsUrl, authHeader, requestDigest, selectedPlanSet, itemsSent, itemsSkipped, itemsFailed
    SyncMaintenanceTaskLists wsTaskLists, tlItemsUrl, authHeader, requestDigest, selectedPlanSet, tlSent, tlSkipped, tlFailed

    MsgBox BuildSyncSummary(plansSent, plansSkipped, plansFailed, itemsSent, itemsSkipped, itemsFailed, tlSent, tlSkipped, tlFailed), vbInformation + vbOKOnly
    Exit Sub

SyncError:
    MsgBox "SharePoint sync fejl: " & Err.Description, vbCritical + vbOKOnly
End Sub

Public Sub RunSharePointSyncFromButton()
    SyncSelectedCreatedRowsToSharePoint
End Sub

Public Sub SendMultipleTablesToPowerAutomate()
    ' Legacy entry point kept to avoid breaking existing macro bindings.
    SyncSelectedCreatedRowsToSharePoint
End Sub

Private Sub SyncMaintenancePlans( _
    ByVal ws As Worksheet, _
    ByVal itemsUrl As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByVal selectedPlanSet As Object, _
    ByRef sent As Long, _
    ByRef skipped As Long, _
    ByRef failed As Long)

    Dim map As Object
    Dim lastRow As Long
    Dim i As Long
    Dim statusCol As Long
    Dim msgCol As Long
    Dim atCol As Long

    Set map = BuildPlansColumnMap(ws)

    RequireColumn CLng(map("LIST_ID")), "Id", ws.Name
    RequireColumn CLng(map("PLAN_KEY")), "PlanID", ws.Name
    RequireColumn CLng(map("SAP_OUTPUT")), "SAPNum", ws.Name

    EnsureSyncColumns ws, statusCol, msgCol, atCol
    lastRow = GetLastDataRow(ws, CLng(map("PLAN_KEY")), CLng(map("LIST_ID")), CLng(map("ROW_START")))

    For i = CLng(map("ROW_START")) To lastRow
        On Error GoTo PlanRowError

        Dim planKey As String
        Dim planListIdKey As String
        Dim inScope As Boolean

        planKey = NormalizeKeyValue(GetMapValue(ws, i, CLng(map("PLAN_KEY"))))
        planListIdKey = NormalizeKeyValue(GetMapValue(ws, i, CLng(map("LIST_ID"))))

        If Len(planKey) = 0 And Len(planListIdKey) = 0 Then GoTo NextPlan

        inScope = False
        If Len(planKey) > 0 Then inScope = selectedPlanSet.Exists(planKey)
        If Not inScope And Len(planListIdKey) > 0 Then inScope = selectedPlanSet.Exists(planListIdKey)
        If Not inScope Then GoTo NextPlan

        Dim listItemId As Long
        Dim sapValue As String

        listItemId = ParseListItemId(GetMapValue(ws, i, CLng(map("LIST_ID")), False))
        sapValue = Trim$(GetMapValue(ws, i, CLng(map("SAP_OUTPUT")), False))

        If listItemId <= 0 Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Mangler gyldigt SharePoint Id"
            GoTo NextPlan
        End If

        If Not IsSyncableSapValue(sapValue) Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Ingen gyldig SAPNum at synkronisere"
            GoTo NextPlan
        End If

        Dim payload As String
        Dim errMessage As String

        payload = BuildJsonPayload("SAPNum", sapValue, "Status", PLAN_PUBLISHED_STATUS)

        If TryMergeSharePointItem(itemsUrl, listItemId, payload, authHeader, requestDigest, errMessage) Then
            sent = sent + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SENT, "SAPNum og Status opdateret"
        Else
            If IsSharePointAccessDenied(errMessage) Then
                HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
            Else
                failed = failed + 1
                WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, errMessage
            End If
        End If

NextPlan:
        On Error GoTo 0
    Next i

    Exit Sub

PlanRowError:
    If IsSharePointAccessDenied(Err.Description) Then
        HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
    Else
        failed = failed + 1
        WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, "Uventet raekke-fejl: " & Err.Description
    End If
    Err.Clear
    Resume NextPlan
End Sub

Private Sub SyncMaintenanceItems( _
    ByVal ws As Worksheet, _
    ByVal itemsUrl As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByVal selectedPlanSet As Object, _
    ByRef sent As Long, _
    ByRef skipped As Long, _
    ByRef failed As Long)

    Dim map As Object
    Dim lastRow As Long
    Dim i As Long
    Dim statusCol As Long
    Dim msgCol As Long
    Dim atCol As Long

    Set map = BuildItemsColumnMap(ws)

    RequireColumn CLng(map("LIST_ID")), "Id", ws.Name
    RequireColumn CLng(map("PLAN_KEY")), "MaintenancePlanNo", ws.Name
    RequireColumn CLng(map("SAP_OUTPUT")), "SAPNumber", ws.Name

    EnsureSyncColumns ws, statusCol, msgCol, atCol
    lastRow = GetLastDataRow(ws, CLng(map("PLAN_KEY")), CLng(map("LIST_ID")), CLng(map("ROW_START")))

    For i = CLng(map("ROW_START")) To lastRow
        On Error GoTo ItemRowError

        Dim planLink As String
        planLink = NormalizeKeyValue(GetMapValue(ws, i, CLng(map("PLAN_KEY"))))

        If Len(planLink) = 0 Then GoTo NextItem
        If Not selectedPlanSet.Exists(planLink) Then GoTo NextItem

        Dim listItemId As Long
        Dim sapValue As String

        listItemId = ParseListItemId(GetMapValue(ws, i, CLng(map("LIST_ID")), False))
        sapValue = Trim$(GetMapValue(ws, i, CLng(map("SAP_OUTPUT")), False))

        If listItemId <= 0 Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Mangler gyldigt SharePoint Id"
            GoTo NextItem
        End If

        If Not IsSyncableSapValue(sapValue) Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Ingen gyldig SAPNumber at synkronisere"
            GoTo NextItem
        End If

        Dim errMessage As String

        If TryMergeItemSapField(itemsUrl, listItemId, sapValue, authHeader, requestDigest, errMessage) Then
            sent = sent + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SENT, "SAPNumber opdateret"
        Else
            If IsSharePointAccessDenied(errMessage) Then
                HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
            Else
                failed = failed + 1
                WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, errMessage
            End If
        End If

NextItem:
        On Error GoTo 0
    Next i

    Exit Sub

ItemRowError:
    If IsSharePointAccessDenied(Err.Description) Then
        HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
    Else
        failed = failed + 1
        WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, "Uventet raekke-fejl: " & Err.Description
    End If
    Err.Clear
    Resume NextItem
End Sub

Private Function TryMergeItemSapField( _
    ByVal itemsUrl As String, _
    ByVal listItemId As Long, _
    ByVal sapValue As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByRef errorText As String) As Boolean

    Dim candidates As Variant
    Dim i As Long
    Dim payload As String
    Dim lastErr As String
    Dim numericValue As Double
    Dim hasNumericValue As Boolean

    candidates = ItemSapFieldCandidates()
    hasNumericValue = TryParseSyncNumericValue(sapValue, numericValue)

    For i = LBound(candidates) To UBound(candidates)
        payload = BuildJsonPayload(CStr(candidates(i)), sapValue)
        If TryMergeSharePointItem(itemsUrl, listItemId, payload, authHeader, requestDigest, lastErr) Then
            TryMergeItemSapField = True
            Exit Function
        End If

        If IsSharePointAccessDenied(lastErr) Then
            errorText = lastErr
            Exit Function
        End If

        If hasNumericValue Then
            payload = BuildJsonPayloadValue(CStr(candidates(i)), numericValue)
            If TryMergeSharePointItem(itemsUrl, listItemId, payload, authHeader, requestDigest, lastErr) Then
                TryMergeItemSapField = True
                Exit Function
            End If

            If IsSharePointAccessDenied(lastErr) Then
                errorText = lastErr
                Exit Function
            End If
        End If
    Next i

    errorText = "Kunne ikke opdatere SAPNumber. " & lastErr
End Function

Private Function ItemSapFieldCandidates() As Variant
    ItemSapFieldCandidates = Array( _
        "SAPNumber", _
        "SAP_x0020_Number", _
        "SAP_x005f_Number", _
        "SAP_Number")
End Function

Private Function TryParseSyncNumericValue(ByVal rawValue As String, ByRef outNumber As Double) As Boolean
    Dim s As String

    s = Trim$(rawValue)
    If Len(s) = 0 Then Exit Function
    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    If InStr(1, s, ",", vbBinaryCompare) > 0 Then
        s = Replace(s, ".", vbNullString)
        s = Replace(s, ",", ".")
    End If

    If Not IsNumeric(s) Then Exit Function

    On Error GoTo ParseFail
    outNumber = CDbl(s)
    TryParseSyncNumericValue = True
    Exit Function

ParseFail:
End Function

Private Sub SyncMaintenanceTaskLists( _
    ByVal ws As Worksheet, _
    ByVal itemsUrl As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByVal selectedPlanSet As Object, _
    ByRef sent As Long, _
    ByRef skipped As Long, _
    ByRef failed As Long)

    Dim map As Object
    Dim tlhMap As Object
    Dim taskSapMap As Object
    Dim lastRow As Long
    Dim i As Long
    Dim statusCol As Long
    Dim msgCol As Long
    Dim atCol As Long

    Set map = BuildTlColumnMap(ws)
    Set tlhMap = BuildTlhColumnMap(ThisWorkbook.Worksheets(WS_MAINTENANCE_TLH))
    Set taskSapMap = BuildTaskSapMap(ThisWorkbook.Worksheets(WS_MAINTENANCE_TLH), tlhMap)

    RequireColumn CLng(map("LIST_ID")), "Id", ws.Name
    RequireColumn CLng(map("PLAN_LINK")), "MaintenancePlanIDId", ws.Name
    RequireColumn CLng(map("SAP_OUTPUT")), "SAPGroupNumber", ws.Name

    EnsureSyncColumns ws, statusCol, msgCol, atCol
    lastRow = GetLastDataRow(ws, CLng(map("PLAN_LINK")), CLng(map("LIST_ID")), CLng(map("ROW_START")))

    For i = CLng(map("ROW_START")) To lastRow
        On Error GoTo TlRowError

        Dim planLink As String
        planLink = NormalizeKeyValue(GetMapValue(ws, i, CLng(map("PLAN_LINK"))))

        If Len(planLink) = 0 Then GoTo NextTask
        If Not selectedPlanSet.Exists(planLink) Then GoTo NextTask

        Dim listItemId As Long
        Dim sapValue As String
        Dim taskKey As String

        listItemId = ParseListItemId(GetMapValue(ws, i, CLng(map("LIST_ID")), False))
        sapValue = Trim$(GetMapValue(ws, i, CLng(map("SAP_OUTPUT")), False))

        If Not IsSyncableSapValue(sapValue) Then
            taskKey = NormalizeKeyValue(GetMapValue(ws, i, CLng(map("TASK_KEY"))))
            If Len(taskKey) > 0 Then
                If Not taskSapMap Is Nothing Then
                    If taskSapMap.Exists(taskKey) Then
                        sapValue = CStr(taskSapMap(taskKey))
                        If CLng(map("SAP_OUTPUT")) > 0 Then
                            ws.Cells(i, CLng(map("SAP_OUTPUT"))).Value = sapValue
                        End If
                    End If
                End If
            End If
        End If

        If listItemId <= 0 Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Mangler gyldigt SharePoint Id"
            GoTo NextTask
        End If

        If Not IsSyncableSapValue(sapValue) Then
            skipped = skipped + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, "Ingen gyldig SAP Task List at synkronisere"
            GoTo NextTask
        End If

        Dim errMessage As String

        If TryMergeTaskListSapField(itemsUrl, listItemId, sapValue, authHeader, requestDigest, errMessage) Then
            sent = sent + 1
            WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_SENT, "SAP Task List opdateret"
        Else
            If IsSharePointAccessDenied(errMessage) Then
                HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
            Else
                failed = failed + 1
                WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, errMessage
            End If
        End If

NextTask:
        On Error GoTo 0
    Next i

    Exit Sub

TlRowError:
    If IsSharePointAccessDenied(Err.Description) Then
        HandleAccessDeniedRow ws, i, statusCol, msgCol, atCol, skipped
    Else
        failed = failed + 1
        WriteSyncState ws, i, statusCol, msgCol, atCol, SYNC_STATUS_ERROR, "Uventet raekke-fejl: " & Err.Description
    End If
    Err.Clear
    Resume NextTask
End Sub

Private Function TryMergeTaskListSapField( _
    ByVal itemsUrl As String, _
    ByVal listItemId As Long, _
    ByVal sapValue As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByRef errorText As String) As Boolean

    Dim candidates As Variant
    Dim i As Long
    Dim payload As String
    Dim lastErr As String

    candidates = TaskListSapFieldCandidates()

    For i = LBound(candidates) To UBound(candidates)
        payload = BuildJsonPayload(CStr(candidates(i)), sapValue)

        If TryMergeSharePointItem(itemsUrl, listItemId, payload, authHeader, requestDigest, lastErr) Then
            TryMergeTaskListSapField = True
            Exit Function
        End If

        If IsSharePointAccessDenied(lastErr) Then
            errorText = lastErr
            Exit Function
        End If
    Next i

    errorText = "Kunne ikke opdatere SAP Task List. " & lastErr
End Function

Private Function TaskListSapFieldCandidates() As Variant
    TaskListSapFieldCandidates = Array("SAPGroupNumber")
End Function

Private Function BuildTaskSapMap(ByVal wsTlh As Worksheet, ByVal map As Object) As Object
    Dim out As Object
    Dim lastRow As Long
    Dim i As Long

    Set out = CreateObject("Scripting.Dictionary")
    out.CompareMode = vbTextCompare

    If wsTlh Is Nothing Then
        Set BuildTaskSapMap = out
        Exit Function
    End If

    If map Is Nothing Then
        Set BuildTaskSapMap = out
        Exit Function
    End If

    If CLng(map("TASK_KEY")) <= 0 Or CLng(map("SAP_GROUP")) <= 0 Then
        Set BuildTaskSapMap = out
        Exit Function
    End If

    lastRow = GetLastDataRow(wsTlh, CLng(map("TASK_KEY")), CLng(map("SAP_GROUP")), CLng(map("ROW_START")))

    For i = CLng(map("ROW_START")) To lastRow
        Dim taskKey As String
        Dim groupValue As String
        Dim counterValue As String
        Dim sapValue As String

        taskKey = NormalizeKeyValue(GetMapValue(wsTlh, i, CLng(map("TASK_KEY"))))
        groupValue = Trim$(GetMapValue(wsTlh, i, CLng(map("SAP_GROUP")), False))

        If CLng(map("SAP_COUNTER")) > 0 Then
            counterValue = Trim$(GetMapValue(wsTlh, i, CLng(map("SAP_COUNTER")), False))
        End If

        sapValue = ComposeTaskListSapValue(groupValue, counterValue)

        If Len(taskKey) > 0 And IsSyncableSapValue(sapValue) Then
            out(taskKey) = sapValue
        End If
    Next i

    Set BuildTaskSapMap = out
End Function

Private Function ComposeTaskListSapValue(ByVal groupValue As String, ByVal counterValue As String) As String
    Dim g As String
    Dim c As String

    g = Trim$(groupValue)
    c = Trim$(counterValue)

    If Len(g) = 0 Then Exit Function

    If Left$(g, 1) = "'" Then g = Mid$(g, 2)
    If Left$(c, 1) = "'" Then c = Mid$(c, 2)

    ' Already formatted in source.
    If UCase$(Left$(g, 2)) = "A-" And InStr(3, g, "-", vbBinaryCompare) > 0 Then
        ComposeTaskListSapValue = g
        Exit Function
    End If

    If Len(c) = 0 Then Exit Function

    ComposeTaskListSapValue = "A-" & g & "-" & c
End Function

Private Function BuildTlhColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "TASK_KEY", ResolveColumn(headerIndex, Array("TaskID", "Task_List_Group", "TL_Group", "TaskListGroup", "TaskList"), 3)
    map.Add "SAP_GROUP", ResolveColumn(headerIndex, Array("TL_Group_Number", "TLGroupNumber", "PLNNR", "SAP_Task_List_Number", "SAPTaskList", "SAPGroupNumber", "TaskListGroup"), 9)
    map.Add "SAP_COUNTER", ResolveColumn(headerIndex, Array("TL_Counter", "TLCounter", "TaskListGroupCounter", "Counter", "PLNAL"), 10)

    Set BuildTlhColumnMap = map
End Function

Private Function BuildSelectedPlanSet(ByVal wsPlans As Worksheet) As Object
    Dim map As Object
    Dim selectedPlans As Object
    Dim lastRow As Long
    Dim i As Long

    Set map = BuildPlansColumnMap(wsPlans)
    RequireColumn CLng(map("PLAN_KEY")), "PlanID", wsPlans.Name
    RequireColumn CLng(map("LIST_ID")), "Id", wsPlans.Name
    RequireColumn CLng(map("CREATE_SELECTED")), "CreateInSAP", wsPlans.Name

    Set selectedPlans = CreateObject("Scripting.Dictionary")
    selectedPlans.CompareMode = vbTextCompare

    lastRow = GetLastDataRow(wsPlans, CLng(map("PLAN_KEY")), CLng(map("LIST_ID")), CLng(map("ROW_START")))

    For i = CLng(map("ROW_START")) To lastRow
        If IsPlanSelectedForSync(GetMapValue(wsPlans, i, CLng(map("CREATE_SELECTED")), False)) Then
            AddDictionaryKey selectedPlans, NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(map("PLAN_KEY"))))
            AddDictionaryKey selectedPlans, NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(map("LIST_ID"))))
        End If
    Next i

    Set BuildSelectedPlanSet = selectedPlans
End Function

Private Function TryMergeSharePointItem( _
    ByVal itemsUrl As String, _
    ByVal listItemId As Long, _
    ByVal payloadJson As String, _
    ByVal authHeader As String, _
    ByRef requestDigest As String, _
    ByRef errorText As String) As Boolean

    Dim attempt As Long
    Dim responseText As String
    Dim updateUrl As String

    updateUrl = BuildListItemUpdateUrl(itemsUrl, listItemId)

    For attempt = 0 To SYNC_ROW_RETRY_MAX
        responseText = vbNullString
        On Error GoTo MergeError

        Call HttpSendJson( _
            "POST", _
            updateUrl, _
            payloadJson, _
            authHeader, _
            "application/json;odata=nometadata", _
            "application/json;odata=nometadata", _
            "*", _
            "MERGE", _
            responseText, _
            requestDigest)

        TryMergeSharePointItem = True
        Exit Function

MergeRetry:
        If IsSharePointAccessDenied(errorText) Then
            Exit Function
        End If

        If attempt < SYNC_ROW_RETRY_MAX Then
            If ShouldRefreshDigest(errorText) Then
                On Error Resume Next
                requestDigest = GetSharePointRequestDigest(itemsUrl, authHeader)
                On Error GoTo 0
            End If

            PauseMilliseconds SYNC_ROW_RETRY_WAIT_MS
        End If
    Next attempt

    Exit Function

MergeError:
    errorText = Err.Description
    If Len(responseText) > 0 Then
        errorText = errorText & " | " & responseText
    End If

    Err.Clear
    On Error GoTo 0
    GoTo MergeRetry

UnexpectedMergeError:
    errorText = Err.Description
    If Len(responseText) > 0 Then
        errorText = errorText & " | " & responseText
    End If
    Err.Clear
End Function

Private Function BuildJsonPayload( _
    ByVal primaryField As String, _
    ByVal primaryValue As String, _
    Optional ByVal secondaryField As String = vbNullString, _
    Optional ByVal secondaryValue As String = vbNullString) As String

    BuildJsonPayload = BuildJsonPayloadValue(primaryField, primaryValue, secondaryField, secondaryValue)
End Function

Private Function BuildJsonPayloadValue( _
    ByVal primaryField As String, _
    ByVal primaryValue As Variant, _
    Optional ByVal secondaryField As String = vbNullString, _
    Optional ByVal secondaryValue As Variant = Empty) As String

    Dim payload As Object
    Set payload = CreateObject("Scripting.Dictionary")

    payload.Add primaryField, primaryValue
    If Len(Trim$(secondaryField)) > 0 Then
        payload.Add secondaryField, secondaryValue
    End If

    BuildJsonPayloadValue = JsonConverter.ConvertToJson(payload)
End Function

Private Function BuildListItemUpdateUrl(ByVal itemsUrl As String, ByVal listItemId As Long) As String
    Dim baseUrl As String

    baseUrl = Trim$(itemsUrl)
    If Right$(baseUrl, 1) = "/" Then baseUrl = Left$(baseUrl, Len(baseUrl) - 1)

    BuildListItemUpdateUrl = baseUrl & "(" & CStr(listItemId) & ")"
End Function

Private Function GetSharePointRequestDigest(ByVal itemsUrl As String, ByVal authHeader As String) As String
    Dim contextUrl As String
    Dim responseText As String
    Dim root As Object

    contextUrl = BuildContextInfoUrl(itemsUrl)
    If Len(contextUrl) = 0 Then
        Err.Raise 1006, , "Kunne ikke aflede contextinfo URL fra: " & itemsUrl
    End If

    Call HttpSendJson( _
        "POST", _
        contextUrl, _
        vbNullString, _
        authHeader, _
        "application/json;odata=verbose", _
        "application/json;odata=verbose", _
        vbNullString, _
        vbNullString, _
        responseText)

    Set root = JsonConverter.ParseJson(responseText)
    GetSharePointRequestDigest = ExtractContextInfoDigest(root)

    If Len(GetSharePointRequestDigest) = 0 Then
        Err.Raise 1007, , "SharePoint contextinfo returnerede ingen FormDigestValue."
    End If
End Function

Private Function BuildContextInfoUrl(ByVal itemsUrl As String) As String
    Dim baseUrl As String
    Dim p As Long

    baseUrl = Trim$(itemsUrl)
    p = InStr(1, baseUrl, "/_api/", vbTextCompare)
    If p <= 0 Then Exit Function

    BuildContextInfoUrl = Left$(baseUrl, p - 1) & "/_api/contextinfo"
End Function

Private Function ExtractContextInfoDigest(ByVal root As Object) As String
    On Error GoTo SafeExit

    Dim d As Object
    Dim info As Object

    If root Is Nothing Then Exit Function
    If TypeName(root) <> "Dictionary" Then Exit Function

    If root.Exists("FormDigestValue") Then
        ExtractContextInfoDigest = Trim$(CStr(root("FormDigestValue")))
        If Len(ExtractContextInfoDigest) > 0 Then Exit Function
    End If

    If root.Exists("GetContextWebInformation") Then
        If IsObject(root("GetContextWebInformation")) Then
            Set info = root("GetContextWebInformation")
            If TypeName(info) = "Dictionary" Then
                If info.Exists("FormDigestValue") Then
                    ExtractContextInfoDigest = Trim$(CStr(info("FormDigestValue")))
                    If Len(ExtractContextInfoDigest) > 0 Then Exit Function
                End If
            End If
        End If
    End If

    If root.Exists("d") Then
        If IsObject(root("d")) Then
            Set d = root("d")
            If TypeName(d) = "Dictionary" Then
                If d.Exists("FormDigestValue") Then
                    ExtractContextInfoDigest = Trim$(CStr(d("FormDigestValue")))
                    If Len(ExtractContextInfoDigest) > 0 Then Exit Function
                End If

                If d.Exists("GetContextWebInformation") Then
                    If IsObject(d("GetContextWebInformation")) Then
                        Set info = d("GetContextWebInformation")
                        If TypeName(info) = "Dictionary" Then
                            If info.Exists("FormDigestValue") Then
                                ExtractContextInfoDigest = Trim$(CStr(info("FormDigestValue")))
                                If Len(ExtractContextInfoDigest) > 0 Then Exit Function
                            End If
                        End If
                    End If
                End If
            End If
        End If
    End If

SafeExit:
End Function

Private Function ShouldRefreshDigest(ByVal errorText As String) As Boolean
    Dim lowered As String

    If IsSharePointAccessDenied(errorText) Then Exit Function

    lowered = LCase$(Trim$(errorText))
    If Len(lowered) = 0 Then Exit Function

    ShouldRefreshDigest = (InStr(1, lowered, "security validation", vbTextCompare) > 0) Or _
                          (InStr(1, lowered, "requestdigest", vbTextCompare) > 0) Or _
                          (InStr(1, lowered, "formdigest", vbTextCompare) > 0)
End Function

Private Function IsSharePointAccessDenied(ByVal errorText As String) As Boolean
    Dim lowered As String

    lowered = LCase$(Trim$(errorText))
    If Len(lowered) = 0 Then Exit Function

    IsSharePointAccessDenied = (InStr(1, lowered, "http 403", vbTextCompare) > 0) Or _
                               (InStr(1, lowered, "access is denied", vbTextCompare) > 0) Or _
                               (InStr(1, lowered, "e_accessdenied", vbTextCompare) > 0) Or _
                               (InStr(1, lowered, "unauthorizedaccessexception", vbTextCompare) > 0)
End Function

Private Function AccessDeniedSkipMessage() As String
    AccessDeniedSkipMessage = "Ingen write-adgang (403). Raekken er sandsynligvis allerede opdateret eller laast i SharePoint."
End Function

Private Sub HandleAccessDeniedRow( _
    ByVal ws As Worksheet, _
    ByVal rowIndex As Long, _
    ByVal statusCol As Long, _
    ByVal msgCol As Long, _
    ByVal atCol As Long, _
    ByRef skipped As Long)

    Dim existingStatus As String

    If ws Is Nothing Then Exit Sub
    If statusCol > 0 Then
        existingStatus = UCase$(Trim$(CStr(ws.Cells(rowIndex, statusCol).Value)))
    End If

    If existingStatus = SYNC_STATUS_SENT Then
        If atCol > 0 Then ws.Cells(rowIndex, atCol).Value = Now
        Exit Sub
    End If

    skipped = skipped + 1
    WriteSyncState ws, rowIndex, statusCol, msgCol, atCol, SYNC_STATUS_SKIPPED, AccessDeniedSkipMessage()
End Sub

Private Sub PauseMilliseconds(ByVal milliseconds As Long)
    If milliseconds <= 0 Then Exit Sub

    Dim startTick As Double
    Dim elapsed As Double

    startTick = Timer

    Do
        DoEvents
        elapsed = Timer - startTick
        If elapsed < 0 Then elapsed = elapsed + 86400#
    Loop While elapsed * 1000# < milliseconds
End Sub

Private Function BuildSyncSummary( _
    ByVal plansSent As Long, _
    ByVal plansSkipped As Long, _
    ByVal plansFailed As Long, _
    ByVal itemsSent As Long, _
    ByVal itemsSkipped As Long, _
    ByVal itemsFailed As Long, _
    ByVal tlSent As Long, _
    ByVal tlSkipped As Long, _
    ByVal tlFailed As Long) As String

    BuildSyncSummary = "SharePoint update faerdig." & vbCrLf & _
                       "Scope: Kun markerede planer (CreateInSAP) samt deres items/tasklists." & vbCrLf & vbCrLf & _
                       "MaintenancePlans - SENT: " & CStr(plansSent) & ", SKIPPED: " & CStr(plansSkipped) & ", ERROR: " & CStr(plansFailed) & vbCrLf & _
                       "MaintenanceItems - SENT: " & CStr(itemsSent) & ", SKIPPED: " & CStr(itemsSkipped) & ", ERROR: " & CStr(itemsFailed) & vbCrLf & _
                       "TaskListMain - SENT: " & CStr(tlSent) & ", SKIPPED: " & CStr(tlSkipped) & ", ERROR: " & CStr(tlFailed)
End Function

Private Sub EnsureSyncColumns(ByVal ws As Worksheet, ByRef statusCol As Long, ByRef msgCol As Long, ByRef atCol As Long)
    statusCol = EnsureHeaderColumn(ws, "Sync_Status")
    msgCol = EnsureHeaderColumn(ws, "Sync_Message")
    atCol = EnsureHeaderColumn(ws, "Sync_At")
End Sub

Private Sub WriteSyncState( _
    ByVal ws As Worksheet, _
    ByVal rowIndex As Long, _
    ByVal statusCol As Long, _
    ByVal msgCol As Long, _
    ByVal atCol As Long, _
    ByVal statusValue As String, _
    ByVal messageValue As String)

    If statusCol > 0 Then ws.Cells(rowIndex, statusCol).Value = statusValue
    If msgCol > 0 Then ws.Cells(rowIndex, msgCol).Value = messageValue
    If atCol > 0 Then ws.Cells(rowIndex, atCol).Value = Now
End Sub

Private Function EnsureHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim idx As Long
    idx = FindHeaderColumn(ws, headerName)
    If idx > 0 Then
        EnsureHeaderColumn = idx
        Exit Function
    End If

    Dim lastCol As Long
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If Len(Trim$(CStr(ws.Cells(1, 1).Value))) = 0 Then lastCol = 0

    EnsureHeaderColumn = lastCol + 1
    ws.Cells(1, EnsureHeaderColumn).Value = headerName
End Function

Private Function FindHeaderColumn(ByVal ws As Worksheet, ByVal headerName As String) As Long
    Dim headerIndex As Object
    Dim key As String

    Set headerIndex = BuildHeaderIndex(ws)
    key = NormalizeHeaderToken(headerName)

    If Len(key) > 0 Then
        If headerIndex.Exists(key) Then FindHeaderColumn = CLng(headerIndex(key))
    End If
End Function

Private Function BuildPlansColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "LIST_ID", ResolveColumn(headerIndex, Array("Id", "ID"), 1)
    map.Add "PLAN_KEY", ResolveColumn(headerIndex, Array("PlanID", "Plan_ID", "PlanId"), 1)
    map.Add "CREATE_SELECTED", ResolveColumn(headerIndex, Array("CreateInSAP", "CreateSelected", "Create", "SelectForCreate"), 0)
    map.Add "SAP_OUTPUT", ResolveColumn(headerIndex, Array("SAPNum", "Plan_Number", "PlanNumber"), 9)

    Set BuildPlansColumnMap = map
End Function

Private Function BuildItemsColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "LIST_ID", ResolveColumn(headerIndex, Array("Id", "ID"), 1)
    map.Add "PLAN_KEY", ResolveColumn(headerIndex, Array("MaintenancePlanNo", "Plan_ID", "PlanID", "MaintenancePlanNoId"), 2)
    map.Add "SAP_OUTPUT", ResolveColumn(headerIndex, Array("SAPNumber", "Item_Number", "ItemNumber"), 14)

    Set BuildItemsColumnMap = map
End Function

Private Function BuildTlColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 2
    map.Add "LIST_ID", ResolveColumn(headerIndex, Array("Id", "ID"), 1)
    map.Add "PLAN_LINK", ResolveColumn(headerIndex, Array("MaintenancePlanIDId", "MaintenancePlanNo", "Plan_ID", "PlanID", "TaskID"), 2)
    map.Add "TASK_KEY", ResolveColumn(headerIndex, Array("TaskID", "Task_List_Group", "TL_Group", "TaskListGroup", "TaskList"), 4)
    map.Add "SAP_OUTPUT", ResolveColumn(headerIndex, Array("SAP_Task_List_Number", "SAP Task List", "SAPTaskList", "SAPTaskListNumber", "SAP_x0020_Task_x0020_List", "SAPGroupNumber", "TL_Group_Number", "Task_LstGrp", "PLNNR"), 6)

    Set BuildTlColumnMap = map
End Function

Private Function BuildHeaderIndex(ByVal ws As Worksheet) As Object
    Dim map As Object
    Dim lastCol As Long
    Dim c As Long
    Dim key As String

    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    For c = 1 To lastCol
        key = NormalizeHeaderToken(CStr(ws.Cells(1, c).Value))
        If Len(key) > 0 Then
            If Not map.Exists(key) Then map.Add key, c
        End If
    Next c

    Set BuildHeaderIndex = map
End Function

Private Function ResolveColumn(ByVal headerIndex As Object, ByVal candidates As Variant, Optional ByVal fallbackCol As Long = 0) As Long
    Dim i As Long
    Dim key As String

    For i = LBound(candidates) To UBound(candidates)
        key = NormalizeHeaderToken(CStr(candidates(i)))
        If Len(key) > 0 Then
            If headerIndex.Exists(key) Then
                ResolveColumn = CLng(headerIndex(key))
                Exit Function
            End If
        End If
    Next i

    ResolveColumn = fallbackCol
End Function

Private Function NormalizeHeaderToken(ByVal valueText As String) As String
    Dim s As String
    Dim i As Long
    Dim ch As String
    Dim out As String

    s = LCase$(Trim$(valueText))
    s = Replace(s, "_x0020_", "_")
    s = Replace(s, "_x005f_", "_")

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        Select Case AscW(ch)
            Case 48 To 57, 65 To 90, 97 To 122
                out = out & LCase$(ch)
        End Select
    Next i

    NormalizeHeaderToken = out
End Function

Private Function NormalizeKeyValue(ByVal rawValue As Variant) As String
    Dim s As String
    Dim parts() As String

    s = Trim$(CStr(rawValue))
    If Len(s) = 0 Then Exit Function

    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    If InStr(1, s, ";#", vbBinaryCompare) > 0 Then
        parts = Split(s, ";#")
        s = Trim$(parts(UBound(parts)))
        If Len(s) = 0 Then s = Trim$(parts(0))
    End If

    NormalizeKeyValue = UCase$(Trim$(s))
End Function

Private Function GetMapValue(ByVal ws As Worksheet, ByVal rowIndex As Long, ByVal colIndex As Long, Optional ByVal trimValue As Boolean = True) As String
    If colIndex <= 0 Then Exit Function

    If trimValue Then
        GetMapValue = Trim$(CStr(ws.Cells(rowIndex, colIndex).Value))
    Else
        GetMapValue = CStr(ws.Cells(rowIndex, colIndex).Value)
    End If
End Function

Private Function GetLastDataRow(ByVal ws As Worksheet, ByVal primaryCol As Long, ByVal secondaryCol As Long, ByVal rowStart As Long) As Long
    Dim lastRow As Long

    lastRow = rowStart - 1

    If primaryCol > 0 Then
        lastRow = ws.Cells(ws.Rows.Count, primaryCol).End(xlUp).Row
    End If

    If secondaryCol > 0 Then
        Dim altLastRow As Long
        altLastRow = ws.Cells(ws.Rows.Count, secondaryCol).End(xlUp).Row
        If altLastRow > lastRow Then lastRow = altLastRow
    End If

    If lastRow < rowStart Then
        lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    End If

    GetLastDataRow = lastRow
End Function

Private Sub RequireColumn(ByVal colIndex As Long, ByVal fieldName As String, ByVal sheetName As String)
    If colIndex <= 0 Then
        Err.Raise 5, , "Ark '" & sheetName & "' mangler noedvendig kolonne: " & fieldName
    End If
End Sub

Private Sub AddDictionaryKey(ByVal dict As Object, ByVal keyText As String)
    If dict Is Nothing Then Exit Sub
    If Len(keyText) = 0 Then Exit Sub
    dict(keyText) = True
End Sub

Private Function ParseListItemId(ByVal rawValue As Variant) As Long
    Dim s As String
    Dim parts() As String

    s = Trim$(CStr(rawValue))
    If Len(s) = 0 Then Exit Function

    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    If InStr(1, s, ";#", vbBinaryCompare) > 0 Then
        parts = Split(s, ";#")
        s = Trim$(parts(0))
    End If

    If IsNumeric(s) Then ParseListItemId = CLng(Val(s))
End Function

Private Function IsSyncableSapValue(ByVal rawValue As String) As Boolean
    Dim s As String

    s = Trim$(rawValue)
    If Len(s) = 0 Then Exit Function

    Dim upperText As String
    upperText = UCase$(s)

    If Left$(upperText, 7) = "SKIPPED" Then Exit Function
    If Left$(upperText, 5) = "ERROR" Then Exit Function
    If InStr(1, upperText, "INGEN TASK LIST", vbTextCompare) > 0 Then Exit Function

    IsSyncableSapValue = True
End Function

Private Function IsPlanSelectedForSync(ByVal rawSelection As Variant) As Boolean
    Dim s As String

    s = UCase$(Trim$(CStr(rawSelection)))
    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    Select Case s
        Case UCase$(ChrW(&H2611)), "TRUE", "SAND", "YES", "JA", "1", "X"
            IsPlanSelectedForSync = True
    End Select
End Function

