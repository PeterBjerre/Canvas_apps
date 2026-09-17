Attribute VB_Name = "GUI_Script"
Option Explicit

Public SapGuiAuto As Object
Public WScript As Object
Public msgcol As Variant
Public objGui  As GuiApplication
Public objConn As GuiConnection
Public objSess As GuiSession
Public objSBar As GuiStatusbar
Public objSheet As Worksheet
Public W_System As String
Public PlantDict As Object
Public WorkCenterDict As Object

Private Const READY_PLAN_STATUS As String = "ready for creation in sap"

Private mCreateScopeReady As Boolean
Private mReadyPlanSet As Object
Private mReadyItemSet As Object
Private mReadyTlGroupSet As Object


Sub StartExtract()
    Dim W_Ret As Boolean

    ' Forbind til SAP via GUI_Session (læser system fra Setup-ark)
    W_Ret = Attach_Session_Core()
    If Not W_Ret Then Exit Sub

    ResetCreateScope

    CreateGlobalDictionaries
    
'     Run the GUI script

    CreateTLH

    CreateItems

    CreatePlans

    SyncSelectedCreatedRowsToSharePoint

    ' End the GUI session
    objSess.EndTransaction


End Sub


Function Attach_Session() As Boolean
Dim il, it
Dim W_conn, W_Sess

If W_System = "" Then
   Attach_Session = False
   Exit Function
End If

If Not objSess Is Nothing Then
    If objSess.Info.SystemName & objSess.Info.Client = W_System Then
        Attach_Session = True
        Exit Function
    End If
End If

If objGui Is Nothing Then
   Set SapGuiAuto = GetObject("SAPGUI")
   Set objGui = SapGuiAuto.GetScriptingEngine
End If

For il = 0 To objGui.Children.Count - 1
    Set W_conn = objGui.Children(il + 0)
    For it = 0 To W_conn.Children.Count - 1
        Set W_Sess = W_conn.Children(it + 0)
        If W_Sess.Info.SystemName & W_Sess.Info.Client = W_System Then
            Set objConn = objGui.Children(il + 0)
            Set objSess = objConn.Children(it + 0)
            Exit For
        End If
    Next
Next

If objSess Is Nothing Then
   MsgBox "No active session to system " + W_System + ", or scripting is not enabled.", vbCritical + vbOKOnly
   Attach_Session = False
   Exit Function
End If

If IsObject(WScript) Then
   WScript.ConnectObject objSess, "on"
   WScript.ConnectObject objGui, "on"
End If

Set objSBar = objSess.FindById("wnd[0]/sbar")
Attach_Session = True


End Function

Sub CreateGlobalDictionaries()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim plantName As String, plantKey As String
    Dim workCenterName As String, serviceValue As String, matgrValue As String
    Dim values As Object
    
    Set ws = ThisWorkbook.Sheets(WS_CALL_HORIZON_TABLE)
    
    ' Find sidste r�kke i kolonne E (Plant)
    lastRow = ws.Cells(ws.Rows.Count, "F").End(xlUp).Row
    
    ' Opret dictionaries som globale objekter
    Set PlantDict = CreateObject("Scripting.Dictionary")
    Set WorkCenterDict = CreateObject("Scripting.Dictionary")
    
    ' Loop gennem r�kkerne
    For i = 2 To lastRow
        plantName = Trim(ws.Cells(i, "F").Value)
        plantKey = Trim(ws.Cells(i, "G").Value)
        workCenterName = Trim(ws.Cells(i, "I").Value)
        serviceValue = Trim(ws.Cells(i, "J").Value)
        matgrValue = Trim(ws.Cells(i, "K").Value)
        
        ' Tilf�j til PlantDict (Plant ? PlantKey)
        If plantName <> "" And plantKey <> "" Then
            If Not PlantDict.Exists(plantName) Then
                PlantDict.Add plantName, plantKey
            End If
        End If
        
        ' Tilf�j til WorkCenterDict (WorkCenterEnd ? {Service, MatGrp})
        If workCenterName <> "" And serviceValue <> "" Then
            If Not WorkCenterDict.Exists(workCenterName) Then
                Set values = CreateObject("Scripting.Dictionary")
                values.Add "Service", serviceValue
                values.Add "MatGrp", matgrValue
                WorkCenterDict.Add workCenterName, values
            End If
        End If
    Next i
    
End Sub

Private Sub ResetCreateScope()
    mCreateScopeReady = False
    Set mReadyPlanSet = Nothing
    Set mReadyItemSet = Nothing
    Set mReadyTlGroupSet = Nothing
End Sub

Private Sub EnsureCreateScope()
    If mCreateScopeReady Then Exit Sub

    BuildCreateScope
    mCreateScopeReady = True
End Sub

Private Sub BuildCreateScope()
    Dim wsPlans As Worksheet
    Dim wsItems As Worksheet
    Dim wsTl As Worksheet
    Dim planCols As Object
    Dim itemCols As Object
    Dim tlCols As Object
    Dim i As Long
    Dim lastRow As Long
    Dim planKey As String
    Dim listIdKey As String
    Dim itemKey As String
    Dim tlGroup As String
    Dim planLink As String
    Dim itemLink As String
    Dim includePlan As Boolean
    Dim selectedRaw As String

    Set mReadyPlanSet = CreateObject("Scripting.Dictionary")
    mReadyPlanSet.CompareMode = vbTextCompare
    Set mReadyItemSet = CreateObject("Scripting.Dictionary")
    mReadyItemSet.CompareMode = vbTextCompare
    Set mReadyTlGroupSet = CreateObject("Scripting.Dictionary")
    mReadyTlGroupSet.CompareMode = vbTextCompare

    Set wsPlans = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    Set wsTl = ThisWorkbook.Worksheets(WS_MAINTENANCE_TL)

    Set planCols = BuildPlansColumnMap(wsPlans)
    RequireColumn CLng(planCols("PLAN_KEY")), "PlanID", wsPlans.name
    RequireColumn CLng(planCols("STATUS")), "Status", wsPlans.name

    lastRow = GetLastDataRow(wsPlans, CLng(planCols("PLAN_KEY")), 1)
    For i = CLng(planCols("ROW_START")) To lastRow
        planKey = NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(planCols("PLAN_KEY"))))
        If Len(planKey) = 0 Then GoTo NextPlanRow

        includePlan = False
        If IsReadyStatus(GetMapValue(wsPlans, i, CLng(planCols("STATUS")))) Then
            includePlan = True

            If CLng(planCols("CREATE_SELECTED")) > 0 Then
                selectedRaw = GetMapValue(wsPlans, i, CLng(planCols("CREATE_SELECTED")), False)
                includePlan = IsPlanSelectedForCreate(selectedRaw)
            End If
        End If

        If includePlan Then
            AddDictionaryKey mReadyPlanSet, planKey
            listIdKey = NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(planCols("LIST_ID"))))
            AddDictionaryKey mReadyPlanSet, listIdKey
        End If
NextPlanRow:
    Next i

    Set itemCols = BuildItemsColumnMap(wsItems)
    RequireColumn CLng(itemCols("ITEM_KEY")), "ItemID", wsItems.name
    RequireColumn CLng(itemCols("PLAN_KEY")), "MaintenancePlanNo", wsItems.name

    lastRow = GetLastDataRow(wsItems, CLng(itemCols("ITEM_KEY")), 1)
    For i = CLng(itemCols("ROW_START")) To lastRow
        itemKey = NormalizeKeyValue(GetMapValue(wsItems, i, CLng(itemCols("ITEM_KEY"))))
        planLink = NormalizeKeyValue(GetMapValue(wsItems, i, CLng(itemCols("PLAN_KEY"))))

        If Len(itemKey) > 0 And Len(planLink) > 0 Then
            If mReadyPlanSet.Exists(planLink) Then AddDictionaryKey mReadyItemSet, itemKey
        End If
    Next i

    Set tlCols = BuildTlColumnMap(wsTl)
    RequireColumn CLng(tlCols("TL_GROUP")), "SAPGroupNumber", wsTl.name

    lastRow = GetLastDataRow(wsTl, CLng(tlCols("TL_GROUP")), 1)
    For i = CLng(tlCols("ROW_START")) To lastRow
        tlGroup = NormalizeKeyValue(GetMapValue(wsTl, i, CLng(tlCols("TL_GROUP"))))
        If Len(tlGroup) = 0 Then GoTo NextTlRow

        planLink = NormalizeKeyValue(GetMapValue(wsTl, i, CLng(tlCols("PLAN_LINK"))))
        itemLink = NormalizeKeyValue(GetMapValue(wsTl, i, CLng(tlCols("ITEM_LINK"))))

        If (Len(planLink) > 0 And mReadyPlanSet.Exists(planLink)) Or _
           (Len(itemLink) > 0 And mReadyItemSet.Exists(itemLink)) Then
            AddDictionaryKey mReadyTlGroupSet, tlGroup
        End If
NextTlRow:
    Next i
End Sub

Private Function BuildTlhColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "TL_GROUP", ResolveColumn(headerIndex, Array("TaskID", "Task_List_Group", "TL_Group", "TaskListGroup", "TaskList"), 3)
    map.Add "PLAN_LINK", ResolveColumn(headerIndex, Array("PlanID", "MaintenancePlanIDId", "MaintenancePlanNo", "MaintenancePlanNoId", "Plan_ID"), 0)
    map.Add "ITEM_LINK", ResolveColumn(headerIndex, Array("ItemID", "MaintenanceItemNoId", "MaintenanceItemNo", "TaskItemID", "Item_ID"), 0)
    map.Add "DESCRIPTION", ResolveColumn(headerIndex, Array("Title", "Description", "KTEXT"), 4)
    map.Add "PLANT_NAME", ResolveColumn(headerIndex, Array("PlantInitial", "Plant_Name", "PlantName"), 5)
    map.Add "WORK_CENTER", ResolveColumn(headerIndex, Array("Work Center", "WorkCtr", "Work_Center", "WorkCenter", "ARBPL"), 6)
    map.Add "PLANT_KEY", ResolveColumn(headerIndex, Array("Profile", "Plant_Key", "PlantKey", "Plant"), 7)
    map.Add "STATUS_CODE", ResolveColumn(headerIndex, Array("Status_Code", "StatusCode"), 8)
    map.Add "TL_GROUP_NUMBER", ResolveColumn(headerIndex, Array("TL_Group_Number", "TLGroupNumber", "PLNNR", "SAP_Task_List_Number", "Task_LstGrp", "RMIPM-PLNNR"), 9)
    map.Add "TL_COUNTER", ResolveColumn(headerIndex, Array("TL_Counter", "TLCounter", "PLNAL", "GrpCr", "RMIPM-PLNAL"), 10)
    map.Add "STATUS_MESSAGE", ResolveColumn(headerIndex, Array("Status_Message", "StatusMessage"), 11)

    Set BuildTlhColumnMap = map
End Function

Private Function BuildTlColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 2
    map.Add "TL_GROUP", ResolveColumn(headerIndex, Array("TaskID", "Task_List_Group", "TL_Group", "SAPGroupNumber", "Task_LstGrp/GrpCr", "Task_LstGrp", "PLNNR"), 4)
    map.Add "OP_ID", ResolveColumn(headerIndex, Array("TaskItemID", "Index", "Operation_ID", "Act", "VORNR"), 3)
    map.Add "WORK_CENTER", ResolveColumn(headerIndex, Array("WorkCtr", "Work_Center", "Work_Ctr", "ARBPL"), 4)
    map.Add "CTRL", ResolveColumn(headerIndex, Array("Ctrl", "Control_Key", "STEUS"), 5)
    map.Add "SHORT_TEXT", ResolveColumn(headerIndex, Array("OperationShortText", "Short_Text", "Operation_Description", "LTXA1", "Title"), 6)
    map.Add "WORK", ResolveColumn(headerIndex, Array("Work", "Work_Quantity", "ARBEI"), 7)
    map.Add "NUM", ResolveColumn(headerIndex, Array("Num", "Component_Quantity", "No", "ANZZL"), 8)
    map.Add "DURATION", ResolveColumn(headerIndex, Array("Duration", "BMVRG"), 9)
    map.Add "VENDOR", ResolveColumn(headerIndex, Array("Vendor", "LIFNR", "Supplier"), 10)
    map.Add "VENDOR_PM02", ResolveColumn(headerIndex, Array("VendorID", "Vendor_PM02"), 11)
    map.Add "LONG_TEXT", ResolveColumn(headerIndex, Array("LongText", "Long_Text", "Operation_Long_Text"), 12)
    map.Add "PLANT", ResolveColumn(headerIndex, Array("PlantInitial", "Plant", "Plant_Name"), 13)
    map.Add "PLAN_LINK", ResolveColumn(headerIndex, Array("MaintenancePlanIDId", "MaintenancePlanNo", "Plan_ID", "TaskID"), 2)
    map.Add "ITEM_LINK", ResolveColumn(headerIndex, Array("MaintenanceItemNoId", "ItemID", "Maintenance_Item", "TaskItemID"), 3)

    Set BuildTlColumnMap = map
End Function

Private Function BuildItemsColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "ITEM_KEY", ResolveColumn(headerIndex, Array("ItemID", "Item_ID", "Maintenance_item"), 1)
    map.Add "PLAN_KEY", ResolveColumn(headerIndex, Array("MaintenancePlanNo", "Plan_ID", "PlanID", "MaintenancePlanNoId"), 2)
    map.Add "SHORT_TEXT", ResolveColumn(headerIndex, Array("Title", "Item_Description", "ItemDescription"), 4)
    map.Add "LONG_TEXT", ResolveColumn(headerIndex, Array("ItemDescription", "Long_Text", "LongText"), 5)
    map.Add "FUNC_LOC", ResolveColumn(headerIndex, Array("FunctionalLocation", "Functional_Location"), 8)
    map.Add "ORDER_TYPE", ResolveColumn(headerIndex, Array("OrderType", "Order_Type"), 12)
    map.Add "ILART", ResolveColumn(headerIndex, Array("MaintenanceActivityTypeId", "Work_Item_Type", "ILART"), 9)
    map.Add "GEWERK", ResolveColumn(headerIndex, Array("MainWorkCenterId", "MainWorkCenter", "Trade", "Gewerk", "GEWERK"), 0)
    map.Add "PRIORITY", ResolveColumn(headerIndex, Array("Priority", "PRIOK", "PriorityKey"), 16)
    map.Add "STATUS", ResolveColumn(headerIndex, Array("UserStatus", "Status"), 6)
    map.Add "NON_FLOW_STATUS", ResolveColumn(headerIndex, Array("NonFlowUserStatus", "Non_Flow_Status"), 7)
    map.Add "REVISION", ResolveColumn(headerIndex, Array("Revision", "Revision_Number", "REVNR"), 13)
    map.Add "REV_BY", ResolveColumn(headerIndex, Array("InitialOrstedResponsible", "Changed_By", "ZZREVBY"), 3)
    map.Add "SAP_OUTPUT", ResolveColumn(headerIndex, Array("SAPNumber", "Item_Number", "ItemNumber"), 14)

    Set BuildItemsColumnMap = map
End Function

Private Function BuildObjectListColumnMap(ByVal ws As Worksheet) As Object
    Dim headerIndex As Object
    Dim map As Object

    Set headerIndex = BuildHeaderIndex(ws)
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "ROW_START", 3
    map.Add "ITEM_KEY", ResolveColumn(headerIndex, Array("ItemID", "MaintenanceItemNo", "Maintenance Item No", "Item_ID"), 1)
    map.Add "FUNC_LOC", ResolveColumn(headerIndex, Array("ObjectList", "FunctionalLocation", "Functional Location"), 2)

    Set BuildObjectListColumnMap = map
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
    map.Add "STATUS", ResolveColumn(headerIndex, Array("Status", "Plan_Status"), 3)
    map.Add "CREATE_SELECTED", ResolveColumn(headerIndex, Array("CreateInSAP", "CreateSelected", "Create", "SelectForCreate"), 0)
    map.Add "DESCRIPTION", ResolveColumn(headerIndex, Array("Title", "Plan_Description", "PlanDescription"), 2)
    map.Add "CYCLE", ResolveColumn(headerIndex, Array("Cycle", "Cycle_Value"), 3)
    map.Add "UNIT", ResolveColumn(headerIndex, Array("Unit", "Cycle_Unit"), 4)
    map.Add "PLANNED_DATE", ResolveColumn(headerIndex, Array("PlannedDate", "Start_Date", "StartDate"), 7)
    map.Add "SORT", ResolveColumn(headerIndex, Array("SortFieldId", "Plan_Sort_Strategy", "PlanSortStrategy"), 8)
    map.Add "SAP_OUTPUT", ResolveColumn(headerIndex, Array("SAPNum", "Plan_Number", "PlanNumber"), 9)
    map.Add "HORIZ_QUALIFIER", ResolveColumn(headerIndex, Array("Horizon_Unit", "HORIZ_QUALIFIER", "HorizonQualifier"), 6)

    Set BuildPlansColumnMap = map
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
        If Len(key) > 0 And headerIndex.Exists(key) Then
            ResolveColumn = CLng(headerIndex(key))
            Exit Function
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

Private Function NormalizeStatusValue(ByVal rawValue As Variant) As String
    Dim s As String

    s = LCase$(Trim$(CStr(rawValue)))
    Do While InStr(1, s, "  ", vbBinaryCompare) > 0
        s = Replace(s, "  ", " ")
    Loop

    NormalizeStatusValue = s
End Function

Private Function IsReadyStatus(ByVal rawStatus As Variant) As Boolean
    IsReadyStatus = (NormalizeStatusValue(rawStatus) = READY_PLAN_STATUS)
End Function

Private Function IsPlanSelectedForCreate(ByVal rawSelection As Variant) As Boolean
    Dim s As String

    s = UCase$(Trim$(CStr(rawSelection)))
    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    Select Case s
        Case UCase$(ChrW(&H2611)), "TRUE", "SAND", "YES", "JA", "1", "X"
            IsPlanSelectedForCreate = True
    End Select
End Function

Private Function GetMapValue(ByVal ws As Worksheet, ByVal rowIndex As Long, ByVal colIndex As Long, Optional ByVal trimValue As Boolean = True) As String
    If colIndex <= 0 Then Exit Function

    If trimValue Then
        GetMapValue = Trim$(CStr(ws.Cells(rowIndex, colIndex).Value))
    Else
        GetMapValue = CStr(ws.Cells(rowIndex, colIndex).Value)
    End If
End Function

Private Sub SetMapValue(ByVal ws As Worksheet, ByVal rowIndex As Long, ByVal colIndex As Long, ByVal valueText As String)
    If colIndex <= 0 Then Exit Sub
    ws.Cells(rowIndex, colIndex).Value = valueText
End Sub

Private Function GetLastDataRow(ByVal ws As Worksheet, ByVal primaryCol As Long, Optional ByVal fallbackCol As Long = 1) As Long
    Dim colToUse As Long

    colToUse = primaryCol
    If colToUse <= 0 Then colToUse = fallbackCol
    If colToUse <= 0 Then colToUse = 1

    GetLastDataRow = ws.Cells(ws.Rows.Count, colToUse).End(xlUp).Row
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

Private Function IsReadyPlanKey(ByVal planKey As String) As Boolean
    If mReadyPlanSet Is Nothing Then Exit Function
    IsReadyPlanKey = mReadyPlanSet.Exists(NormalizeKeyValue(planKey))
End Function

Private Function IsReadyItemKey(ByVal itemKey As String) As Boolean
    If mReadyItemSet Is Nothing Then Exit Function
    IsReadyItemKey = mReadyItemSet.Exists(NormalizeKeyValue(itemKey))
End Function

Private Function IsReadyTlGroup(ByVal tlGroup As String) As Boolean
    If mReadyTlGroupSet Is Nothing Then Exit Function
    IsReadyTlGroup = mReadyTlGroupSet.Exists(NormalizeKeyValue(tlGroup))
End Function

Private Function IsDigitsOnly(ByVal valueText As String) As Boolean
    Dim i As Long
    Dim ch As String

    valueText = Trim$(valueText)
    If Len(valueText) = 0 Then Exit Function

    For i = 1 To Len(valueText)
        ch = Mid$(valueText, i, 1)
        If ch < "0" Or ch > "9" Then Exit Function
    Next i

    IsDigitsOnly = True
End Function

Private Function NormalizeItemIlartValue(ByVal rawValue As String) As String
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

    If Len(s) > 3 Then
        s = Left$(s, 3)
    End If

    NormalizeItemIlartValue = Trim$(s)
End Function

Private Function NormalizeItemPriorityValue(ByVal rawValue As String) As String
    Dim s As String
    Dim parts() As String
    Dim normalized As String

    s = Trim$(CStr(rawValue))
    If Len(s) = 0 Then Exit Function

    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    If InStr(1, s, ";#", vbBinaryCompare) > 0 Then
        parts = Split(s, ";#")
        s = Trim$(parts(UBound(parts)))
        If Len(s) = 0 Then s = Trim$(parts(0))
    End If

    normalized = LCase$(s)
    normalized = Replace(normalized, vbCrLf, " ")
    normalized = Replace(normalized, vbCr, " ")
    normalized = Replace(normalized, vbLf, " ")
    Do While InStr(1, normalized, "  ", vbBinaryCompare) > 0
        normalized = Replace(normalized, "  ", " ")
    Loop

    If InStr(1, normalized, "yellow", vbTextCompare) > 0 Then
        NormalizeItemPriorityValue = "3 Yellow"
    ElseIf InStr(1, normalized, "purple", vbTextCompare) > 0 Then
        NormalizeItemPriorityValue = "6 Purple"
    ElseIf InStr(1, normalized, "red", vbTextCompare) > 0 Or _
           InStr(1, normalized, "statutory", vbTextCompare) > 0 Or _
           InStr(1, normalized, "sceq", vbTextCompare) > 0 Then
        NormalizeItemPriorityValue = "1 Red"
    Else
        Select Case Left$(normalized, 1)
            Case "1"
                NormalizeItemPriorityValue = "1 Red"
            Case "3"
                NormalizeItemPriorityValue = "3 Yellow"
            Case "6"
                NormalizeItemPriorityValue = "6 Purple"
            Case Else
                NormalizeItemPriorityValue = Trim$(s)
        End Select
    End If
End Function

Private Function NormalizeItemRevisionValue(ByVal rawValue As String) As String
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

    Select Case UCase$(Trim$(s))
        Case "YES", "TRUE", "JA", "1", "X"
            NormalizeItemRevisionValue = "REV"

        Case "NO", "FALSE", "NEJ", "0"
            NormalizeItemRevisionValue = vbNullString

        Case Else
            NormalizeItemRevisionValue = Trim$(s)
    End Select
End Function

Private Function ExtractPriorityKey(ByVal priorityValue As String) As String
    Dim s As String
    Dim ch As String

    s = Trim$(priorityValue)
    If Len(s) = 0 Then Exit Function

    ch = Left$(s, 1)
    If ch >= "0" And ch <= "9" Then
        ExtractPriorityKey = ch
    End If
End Function

Private Function ResolvePlanStartDate(ByVal rawPlannedDate As String, ByVal rawCycleValue As String, ByVal rawCycleUnit As String) As String
    Dim plannedDate As Date
    Dim cycleCount As Long
    Dim intervalToken As String

    If Not TryParsePlanDate(rawPlannedDate, plannedDate) Then
        ResolvePlanStartDate = rawPlannedDate
        Exit Function
    End If

    cycleCount = ParseCycleCount(rawCycleValue)
    If cycleCount <= 0 Then
        ResolvePlanStartDate = Format$(plannedDate, "dd.mm.yyyy")
        Exit Function
    End If

    intervalToken = ResolveCycleInterval(rawCycleUnit)
    If Len(intervalToken) = 0 Then
        ResolvePlanStartDate = Format$(plannedDate, "dd.mm.yyyy")
        Exit Function
    End If

    ResolvePlanStartDate = Format$(DateAdd(intervalToken, -cycleCount, plannedDate), "dd.mm.yyyy")
End Function

Private Function TryParsePlanDate(ByVal rawValue As String, ByRef parsedDate As Date) As Boolean
    Dim s As String
    Dim datePart As String
    Dim parts() As String

    On Error GoTo ParseFailed

    s = Trim$(CStr(rawValue))
    If Len(s) = 0 Then Exit Function

    If IsDate(s) Then
        parsedDate = CDate(s)
        TryParsePlanDate = True
        Exit Function
    End If

    datePart = Split(s, " ")(0)
    datePart = Replace(datePart, "/", ".")
    datePart = Replace(datePart, "-", ".")

    Do While InStr(1, datePart, "..", vbBinaryCompare) > 0
        datePart = Replace(datePart, "..", ".")
    Loop

    parts = Split(datePart, ".")
    If UBound(parts) <> 2 Then Exit Function

    If Len(parts(0)) = 4 Then
        parsedDate = DateSerial(CLng(parts(0)), CLng(parts(1)), CLng(parts(2)))
    Else
        parsedDate = DateSerial(CLng(parts(2)), CLng(parts(1)), CLng(parts(0)))
    End If

    TryParsePlanDate = True
    Exit Function

ParseFailed:
    TryParsePlanDate = False
End Function

Private Function ParseCycleCount(ByVal rawCycleValue As String) As Long
    Dim s As String
    Dim i As Long
    Dim ch As String
    Dim digits As String

    s = Trim$(CStr(rawCycleValue))
    If Len(s) = 0 Then Exit Function

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch >= "0" And ch <= "9" Then
            digits = digits & ch
        ElseIf Len(digits) > 0 Then
            Exit For
        End If
    Next i

    If Len(digits) = 0 Then Exit Function
    ParseCycleCount = CLng(digits)
End Function

Private Function ResolveCycleInterval(ByVal rawCycleUnit As String) As String
    Dim unitToken As String

    unitToken = UCase$(Trim$(CStr(rawCycleUnit)))
    unitToken = Replace(unitToken, " ", vbNullString)

    Select Case unitToken
        Case "YR", "Y", "YEAR", "YEARS", "AAR", "AR"
            ResolveCycleInterval = "yyyy"

        Case "MON", "MO", "M", "MONTH", "MONTHS"
            ResolveCycleInterval = "m"

        Case "WK", "W", "WEEK", "WEEKS"
            ResolveCycleInterval = "ww"

        Case "DAY", "D", "DAYS", "DAG"
            ResolveCycleInterval = "d"
    End Select
End Function

Public Sub CreateTLH()
    Dim ws As Worksheet
    Dim mapTlh As Object
    Dim i As Long
    Dim lastRow As Long
    Dim TL As String
    Dim linkedPlan As String
    Dim linkedItem As String
    Dim plantName As String
    Dim plantValue As String
    Dim hasExplicitLinks As Boolean
    Dim includeTlhRow As Boolean

    Set ws = Worksheets(WS_MAINTENANCE_TLH) ' Aktivér arket
    ws.Activate

    On Error GoTo myerr

    ResetCreateScope
    EnsureCreateScope

    If mReadyTlGroupSet Is Nothing Or mReadyTlGroupSet.Count = 0 Then
        MsgBox "Ingen Task Lists er knyttet til planer med status 'Ready for creation in SAP' og markeret til oprettelse.", vbInformation + vbOKOnly
        Exit Sub
    End If

    Set mapTlh = BuildTlhColumnMap(ws)
    RequireColumn CLng(mapTlh("TL_GROUP")), "Task_List_Group", ws.name
    RequireColumn CLng(mapTlh("PLANT_KEY")), "Plant_Key", ws.name
    RequireColumn CLng(mapTlh("DESCRIPTION")), "Description", ws.name
    RequireColumn CLng(mapTlh("PLANT_NAME")), "Plant_Name", ws.name
    RequireColumn CLng(mapTlh("WORK_CENTER")), "Work_Center", ws.name

    lastRow = GetLastDataRow(ws, CLng(mapTlh("TL_GROUP")), 1)

    ' Start SAP-transaktion
    objSess.FindById("wnd[0]/tbar[0]/okcd").Text = TX_IA05
    objSess.FindById("wnd[0]").sendVKey 0

    For i = CLng(mapTlh("ROW_START")) To lastRow
        TL = GetMapValue(ws, i, CLng(mapTlh("TL_GROUP")))
        If Len(TL) = 0 Then GoTo NextRow

        linkedPlan = vbNullString
        If CLng(mapTlh("PLAN_LINK")) > 0 Then
            linkedPlan = NormalizeKeyValue(GetMapValue(ws, i, CLng(mapTlh("PLAN_LINK"))))
        End If

        linkedItem = vbNullString
        If CLng(mapTlh("ITEM_LINK")) > 0 Then
            linkedItem = NormalizeKeyValue(GetMapValue(ws, i, CLng(mapTlh("ITEM_LINK"))))
        End If

        hasExplicitLinks = (Len(linkedPlan) > 0 Or Len(linkedItem) > 0)
        If hasExplicitLinks Then
            includeTlhRow = (Len(linkedPlan) > 0 And IsReadyPlanKey(linkedPlan)) Or _
                            (Len(linkedItem) > 0 And IsReadyItemKey(linkedItem))
        Else
            includeTlhRow = IsReadyTlGroup(TL)
        End If

        If Not includeTlhRow Then
            If Len(GetMapValue(ws, i, CLng(mapTlh("STATUS_MESSAGE")))) = 0 Then
                SetMapValue ws, i, CLng(mapTlh("STATUS_MESSAGE")), "SKIPPED: Plan not selected/ready"
            End If
            GoTo NextRow
        End If
        
        ' Ryd planl�gningsnummer
        objSess.FindById("wnd[0]/usr/ctxtRC271-PLNNR").Text = ""

        ' Indl�s data fra regnearket
        objSess.FindById("wnd[0]/usr/ctxtRC271-PROFIDNETZ").Text = GetMapValue(ws, i, CLng(mapTlh("PLANT_KEY")))
        objSess.FindById("wnd[0]/usr/ctxtRC271-STTAG").Text = DEFAULT_SAP_DATE
        objSess.FindById("wnd[0]").sendVKey 0

        ' Gem status og planl�gningsdata
        SetMapValue ws, i, CLng(mapTlh("STATUS_CODE")), "A"
        SetMapValue ws, i, CLng(mapTlh("TL_GROUP_NUMBER")), objSess.FindById("wnd[0]/usr/ctxtPLKOD-PLNNR").Text
        SetMapValue ws, i, CLng(mapTlh("TL_COUNTER")), objSess.FindById("wnd[0]/usr/txtPLKOD-PLNAL").Text

        ' Inds�t beskrivelse og arbejdssted
        objSess.FindById("wnd[0]/usr/txtPLKOD-KTEXT").Text = GetMapValue(ws, i, CLng(mapTlh("DESCRIPTION")))

        plantName = GetMapValue(ws, i, CLng(mapTlh("PLANT_NAME")))
        plantValue = plantName
        If Not PlantDict Is Nothing Then
            If PlantDict.Exists(plantName) Then plantValue = CStr(PlantDict(plantName))
        End If

        objSess.FindById("wnd[0]/usr/ctxtPLKOD-WERKS").Text = plantValue
        objSess.FindById("wnd[0]/usr/ctxtRCR01-ARBPL").Text = GetMapValue(ws, i, CLng(mapTlh("WORK_CENTER")))
        
        objSess.FindById("wnd[0]/tbar[1]/btn[16]").press

        AddOperations (TL)

        ' Gem og registrer status
        objSess.FindById("wnd[0]/tbar[0]/btn[11]").press
        SetMapValue ws, i, CLng(mapTlh("STATUS_MESSAGE")), objSess.FindById("wnd[0]/sbar").Text
NextRow:
    Next i

    Exit Sub

myerr:
    On Error Resume Next
    If Not mapTlh Is Nothing Then
        SetMapValue ws, i, CLng(mapTlh("STATUS_CODE")), vbNullString
        SetMapValue ws, i, CLng(mapTlh("TL_GROUP_NUMBER")), vbNullString
        SetMapValue ws, i, CLng(mapTlh("TL_COUNTER")), vbNullString
    End If
    On Error GoTo 0
    MsgBox "Der opstod en fejl under oprettelse af TLH-data", vbCritical + vbOKOnly
End Sub

Public Sub AddOperations(TL As String)

    Dim ws As Worksheet
    Dim mapTl As Object
    Dim lastRow As Long
    Dim subDict As Object
    Dim i As Long
    Dim o As Long
    Dim mainKey As String
    Dim plantKey As String
    Dim subKey As Variant
    Dim values As Object
    Dim Service As String
    Dim html As String
    Dim opPath As String
    Dim wcSuffix As String
    Dim wcInfo As Object
    Dim targetTl As String
    
    On Error GoTo myerr

    Set ws = ThisWorkbook.Sheets(WS_MAINTENANCE_TL)
    Set mapTl = BuildTlColumnMap(ws)

    RequireColumn CLng(mapTl("TL_GROUP")), "SAPGroupNumber", ws.name
    RequireColumn CLng(mapTl("WORK_CENTER")), "WorkCtr", ws.name
    RequireColumn CLng(mapTl("CTRL")), "Ctrl", ws.name

    targetTl = NormalizeKeyValue(TL)
    lastRow = GetLastDataRow(ws, CLng(mapTl("TL_GROUP")), 1)
    
    ' Opret sub-dictionary
    Set subDict = CreateObject("Scripting.Dictionary")
    
    ' Loop gennem r�kkerne og tilf�j kun TL
    For i = CLng(mapTl("ROW_START")) To lastRow
        mainKey = NormalizeKeyValue(GetMapValue(ws, i, CLng(mapTl("TL_GROUP"))))
        If mainKey = targetTl Then
            subKey = GetMapValue(ws, i, CLng(mapTl("OP_ID")))
            If Len(CStr(subKey)) = 0 Then subKey = CStr(i)
            
            ' Opret dictionary med feltnavne
            Set values = CreateObject("Scripting.Dictionary")
            values.Add "Workcenter", GetMapValue(ws, i, CLng(mapTl("WORK_CENTER")))
            values.Add "Ctrl", GetMapValue(ws, i, CLng(mapTl("CTRL")))
            values.Add "ShortText", GetMapValue(ws, i, CLng(mapTl("SHORT_TEXT")))
            values.Add "Work", GetMapValue(ws, i, CLng(mapTl("WORK")))
            values.Add "Num", GetMapValue(ws, i, CLng(mapTl("NUM")))
            values.Add "Duration", GetMapValue(ws, i, CLng(mapTl("DURATION")))
            values.Add "Vendor", GetMapValue(ws, i, CLng(mapTl("VENDOR")))
            values.Add "VendorPM02", GetMapValue(ws, i, CLng(mapTl("VENDOR_PM02")))
            values.Add "Plant", GetMapValue(ws, i, CLng(mapTl("PLANT")))
            values.Add "LongText", GetMapValue(ws, i, CLng(mapTl("LONG_TEXT")), False)
            
            If Not subDict.Exists(subKey) Then
                subDict.Add subKey, values
            End If
        End If
    Next i
    
    ' Kun loop hvis vi har fundet noget
    If subDict.Count = 0 Then
        MsgBox "Ingen operationer fundet for TL: " & TL
        Exit Sub
    End If
    
    ' Loop gennem alle subkeys
    opPath = "wnd[0]/usr/tblSAPLCPDITCTRL_3400/"
    o = 0
    For Each subKey In subDict.Keys
        Set values = subDict(subKey)
        
        If values("Ctrl") = "PM01" Or values("Ctrl") = "ZB01" Then
            objSess.FindById(opPath & "ctxtPLPOD-ARBPL[2," & o & "]").Text = values("Workcenter")
            objSess.FindById(opPath & "ctxtPLPOD-STEUS[4," & o & "]").Text = values("Ctrl")
            objSess.FindById(opPath & "txtPLPOD-LTXA1[5," & o & "]").Text = values("ShortText")
            objSess.FindById(opPath & "txtPLPOD-ARBEI[8," & o & "]").Text = values("Work")
            objSess.FindById("wnd[0]").sendVKey 0
            
        ElseIf values("Ctrl") = "PM02" Then
            objSess.FindById(opPath & "ctxtPLPOD-ARBPL[2," & o & "]").Text = values("Workcenter")
            objSess.FindById(opPath & "ctxtPLPOD-STEUS[4," & o & "]").Text = values("Ctrl")
            objSess.FindById(opPath & "txtPLPOD-LTXA1[5," & o & "]").Text = values("ShortText")
            objSess.FindById(opPath & "txtPLPOD-ARBEI[8," & o & "]").Text = values("Work")
            objSess.FindById(opPath & "txtPLPOD-ANZZL[10," & o & "]").Text = values("Num")
            objSess.FindById(opPath & "txtPLPOD-BMVRG[30," & o & "]").Text = "1"
            objSess.FindById(opPath & "ctxtPLPOD-BMEIH[31," & o & "]").Text = "AU"
            objSess.FindById(opPath & "txtPLPOD-PREIS[32," & o & "]").Text = values("Work") * 1000
            objSess.FindById(opPath & "txtPLPOD-PEINH[34," & o & "]").Text = "1"
            objSess.FindById(opPath & "ctxtPLPOD-MATKL[37," & o & "]").Text = "B08.06"
            objSess.FindById(opPath & "ctxtPLPOD-LIFNR[39," & o & "]").Text = Left(values("VendorPM02"), 6)
            objSess.FindById("wnd[0]").sendVKey 0
            
        ElseIf values("Ctrl") = "PM03" Then
            wcSuffix = Right(values("Workcenter"), 5)
                        Set wcInfo = Nothing
                        If Not WorkCenterDict Is Nothing Then
                            If WorkCenterDict.Exists(wcSuffix) Then
                                Set wcInfo = WorkCenterDict(wcSuffix)
                            ElseIf WorkCenterDict.Exists(values("Workcenter")) Then
                                Set wcInfo = WorkCenterDict(values("Workcenter"))
                            End If
                        End If

            objSess.FindById(opPath & "ctxtPLPOD-ARBPL[2," & o & "]").Text = values("Workcenter")
            objSess.FindById(opPath & "ctxtPLPOD-STEUS[4," & o & "]").Text = values("Ctrl")
            objSess.FindById(opPath & "txtPLPOD-LTXA1[5," & o & "]").Text = values("ShortText")
            objSess.FindById(opPath & "txtPLPOD-ARBEI[8," & o & "]").Text = values("Work")
            objSess.FindById(opPath & "txtPLPOD-ANZZL[10," & o & "]").Text = values("Num")
                        If Not wcInfo Is Nothing Then objSess.FindById(opPath & "ctxtPLPOD-MATKL[37," & o & "]").Text = wcInfo("MatGrp")
            objSess.FindById(opPath & "ctxtPLPOD-LIFNR[39," & o & "]").Text = values("Vendor")
            objSess.FindById("wnd[0]").sendVKey 0
            
            objSess.FindById("wnd[0]/tbar[1]/btn[13]").press
                        plantKey = values("Plant")
                        If Not PlantDict Is Nothing Then
                            If PlantDict.Exists(values("Plant")) Then plantKey = CStr(PlantDict(values("Plant")))
                        End If
            objSess.FindById("wnd[1]/usr/ctxtRM11P-MUSTER_LV").Text = plantKey
            objSess.FindById("wnd[1]/tbar[0]/btn[0]").press
            
                        If Not wcInfo Is Nothing Then
                            Service = wcInfo("Service")
                            FindAndSelectAllMatchesScroll Service
                        End If
            
            objSess.FindById("wnd[0]/tbar[1]/btn[9]").press
            objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/txtESLL-MENGE[4,0]").Text = values("Work")
            objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/txtESLL-MENGE[4,0]").SetFocus
            objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/txtESLL-MENGE[4,0]").caretPosition = 1
            objSess.FindById("wnd[0]/tbar[0]/btn[3]").press

            
        End If
        
        If values("LongText") <> "" Then
        
        html = values("LongText")
            
            ConvertHtmlToSAPITF_Dynamic html, False
        
        objSess.FindById(opPath & "chkRC270-TXTKZ[6," & o & "]").SetFocus
        objSess.FindById("wnd[0]").sendVKey 2
        objSess.FindById("wnd[0]/mbar/menu[0]/menu[5]").Select
        objSess.FindById("wnd[1]/usr/btnSPOP-OPTION1").press
        objSess.FindById("wnd[0]/mbar/menu[0]/menu[3]").Select
        objSess.FindById("wnd[1]/usr/radITCTK-TDITF").Select
        objSess.FindById("wnd[1]/usr/radITCTK-TDITF").SetFocus
        objSess.FindById("wnd[1]/tbar[0]/btn[0]").press
        objSess.FindById("wnd[2]/usr/ctxtITCTK-TDFILENAME").Text = SAP_LONGTEXT_ITF_PATH
        objSess.FindById("wnd[2]/tbar[0]/btn[0]").press
        objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
        
        End If
        
        o = o + 1
        
    Next subKey
    
Exit Sub

myerr:
    MsgBox "Der opstod en fejl under rediger Task List", vbCritical + vbOKOnly

End Sub

Sub FindAndSelectAllMatchesScroll(Service As String)
    Dim SAPTable As Object
    Dim matches As Long
    Dim i As Long

    
    Set SAPTable = objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW")
          
    i = 0
       Do Until objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/ctxtESLL-SRVPOS[2," & i & "]").Text = ""
            If objSess.FindById("wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/ctxtESLL-SRVPOS[2," & i & "]").Text = Service Then
                SAPTable.GetAbsoluteRow(i).Selected = True
                matches = matches + 1
            End If
         i = i + 1
    Loop

    

End Sub

Sub CreateNestedDictionaryForKey(filterKey As String)
    
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim mainDict As Object
    Dim subDict As Object
    Dim i As Long
    Dim mainKey As String, subKey As String
    Dim dataArr As Variant
    
    ' S�t reference til arket
    Set ws = ThisWorkbook.Sheets(WS_MAINTENANCE_TL)
    
    ' Find sidste r�kke i kolonne A
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    
    ' Opret hoved-dictionary
    Set mainDict = CreateObject("Scripting.Dictionary")
    
    ' Loop gennem r�kkerne
    For i = 2 To lastRow
        mainKey = ws.Cells(i, "A").Value ' Tasklist Group
        If mainKey = filterKey Then
            subKey = ws.Cells(i, "C").Value  ' Operation ID
            
            ' Gem v�rdier fra de bl� kolonner i et array
            dataArr = Array( _
                ws.Cells(i, "D").Value, _
                ws.Cells(i, "E").Value, _
                ws.Cells(i, "F").Value, _
                ws.Cells(i, "G").Value, _
                ws.Cells(i, "H").Value, _
                ws.Cells(i, "I").Value, _
                ws.Cells(i, "J").Value)
            
            ' Hvis hovedn�glen ikke findes, opret en ny sub-dictionary
            If Not mainDict.Exists(mainKey) Then
                Set subDict = CreateObject("Scripting.Dictionary")
                mainDict.Add mainKey, subDict
            Else
                Set subDict = mainDict(mainKey)
            End If
            
            ' Tilf�j subKey og data til sub-dictionary
            If Not subDict.Exists(subKey) Then
                subDict.Add subKey, dataArr
            End If
        End If
    Next i
    
    ' Test: Udskriv i Immediate Window
    Dim k As Variant, sk As Variant
    For Each k In mainDict.Keys
        Debug.Print "Main Key: " & k
        For Each sk In mainDict(k).Keys
        Next sk
    Next k
    
End Sub
Public Sub CreateItems()

    '=== Deklarationer ===
    Dim ws As Worksheet, wsTL As Worksheet, wsOBJ As Worksheet, wsTlOps As Worksheet
    Dim itemCols As Object, tlhCols As Object, objCols As Object, tlCols As Object
    Dim statusText As String, itemNumber As String
    Dim regex As Object, matches As Object
    Dim MI_TL_dict As Object, MI_OBJ_dict As Object
    Dim tlhInfoByGroup As Object, itemToGroup As Object
    Dim key As Variant
    Dim arr As Variant, objArr As Variant
    Dim i As Long, j As Long
    Dim lastRowTL As Long, lastRowOBJ As Long, lastRowItems As Long, lastRowTlOps As Long
    Dim itemKey As String, objValue As String
    Dim groupKey As String
    Dim html As String
    Dim itemDesc As String, itemFuncLoc As String
    Dim itemOrderType As String, itemILART As String, itemGewerk As String
    Dim itemPrio As String, itemPrioKey As String, itemStatus As String, itemNonFlowStatus As String
    Dim itemRev As String, itemRevBy As String, itemLongText As String
    Dim sapOutCol As Long
    
    '=== Initialisering ===
    Set ws = Worksheets(WS_MAINTENANCE_ITEMS)
    Set wsTL = Worksheets(WS_MAINTENANCE_TLH)
    Set wsOBJ = Worksheets(WS_OBJECT_LIST)
    Set wsTlOps = Worksheets(WS_MAINTENANCE_TL)
    ws.Activate
    On Error GoTo myerr

    ResetCreateScope
    EnsureCreateScope

    If mReadyItemSet Is Nothing Or mReadyItemSet.Count = 0 Then
        MsgBox "Ingen Maintenance Items er knyttet til planer med status 'Ready for creation in SAP' og markeret til oprettelse.", vbInformation + vbOKOnly
        Exit Sub
    End If

    Set itemCols = BuildItemsColumnMap(ws)
    Set tlhCols = BuildTlhColumnMap(wsTL)
    Set objCols = BuildObjectListColumnMap(wsOBJ)
    Set tlCols = BuildTlColumnMap(wsTlOps)

    RequireColumn CLng(itemCols("ITEM_KEY")), "ItemID", ws.name
    RequireColumn CLng(itemCols("SAP_OUTPUT")), "SAPNumber", ws.name
    RequireColumn CLng(tlhCols("TL_GROUP")), "Task_List_Group", wsTL.name
    RequireColumn CLng(tlhCols("STATUS_CODE")), "Status_Code", wsTL.name
    RequireColumn CLng(tlhCols("TL_GROUP_NUMBER")), "TL_Group_Number", wsTL.name
    RequireColumn CLng(tlhCols("TL_COUNTER")), "TL_Counter", wsTL.name
    RequireColumn CLng(tlCols("TL_GROUP")), "SAPGroupNumber", wsTlOps.name
    RequireColumn CLng(tlCols("ITEM_LINK")), "MaintenanceItemNoId", wsTlOps.name

    sapOutCol = CLng(itemCols("SAP_OUTPUT"))
    
    '=== Opret dictionary: Maintenance Item ? Task List info ===
    Set tlhInfoByGroup = CreateObject("Scripting.Dictionary")
    tlhInfoByGroup.CompareMode = vbTextCompare
    Set MI_TL_dict = CreateObject("Scripting.Dictionary")
    MI_TL_dict.CompareMode = vbTextCompare
    Set itemToGroup = CreateObject("Scripting.Dictionary")
    itemToGroup.CompareMode = vbTextCompare

    lastRowTL = GetLastDataRow(wsTL, CLng(tlhCols("TL_GROUP")), 1)
    
    For i = CLng(tlhCols("ROW_START")) To lastRowTL
        groupKey = NormalizeKeyValue(GetMapValue(wsTL, i, CLng(tlhCols("TL_GROUP"))))
        If Len(groupKey) > 0 Then
            arr = Array( _
                GetMapValue(wsTL, i, CLng(tlhCols("STATUS_CODE"))), _
                GetMapValue(wsTL, i, CLng(tlhCols("TL_GROUP_NUMBER"))), _
                GetMapValue(wsTL, i, CLng(tlhCols("TL_COUNTER"))))
            If Not tlhInfoByGroup.Exists(groupKey) Then tlhInfoByGroup.Add groupKey, arr
        End If
    Next i

    lastRowTlOps = GetLastDataRow(wsTlOps, CLng(tlCols("ITEM_LINK")), 1)
    For i = CLng(tlCols("ROW_START")) To lastRowTlOps
        itemKey = NormalizeKeyValue(GetMapValue(wsTlOps, i, CLng(tlCols("ITEM_LINK"))))
        groupKey = NormalizeKeyValue(GetMapValue(wsTlOps, i, CLng(tlCols("TL_GROUP"))))

        If Len(itemKey) > 0 And Len(groupKey) > 0 Then
            If IsReadyItemKey(itemKey) Then
                If Not itemToGroup.Exists(itemKey) Then itemToGroup.Add itemKey, groupKey
            End If
        End If
    Next i

    For Each key In itemToGroup.Keys
        groupKey = CStr(itemToGroup(key))
        If tlhInfoByGroup.Exists(groupKey) Then
            MI_TL_dict(CStr(key)) = tlhInfoByGroup(groupKey)
        End If
    Next key
    
    '=== Opret dictionary: Maintenance Item ? Object List ===
    Set MI_OBJ_dict = CreateObject("Scripting.Dictionary")
    MI_OBJ_dict.CompareMode = vbTextCompare
    lastRowOBJ = GetLastDataRow(wsOBJ, CLng(objCols("ITEM_KEY")), 1)
    
    For i = CLng(objCols("ROW_START")) To lastRowOBJ
        objValue = GetMapValue(wsOBJ, i, CLng(objCols("FUNC_LOC")))
        itemKey = NormalizeKeyValue(GetMapValue(wsOBJ, i, CLng(objCols("ITEM_KEY"))))
        
        If objValue <> "" And itemKey <> "" Then
            If IsReadyItemKey(itemKey) Then
                If Not MI_OBJ_dict.Exists(itemKey) Then
                MI_OBJ_dict.Add itemKey, Array(objValue)
                Else
                    objArr = MI_OBJ_dict(itemKey)
                    ReDim Preserve objArr(UBound(objArr) + 1)
                    objArr(UBound(objArr)) = objValue
                    MI_OBJ_dict(itemKey) = objArr
                End If
            End If
        End If
    Next i

    '=== Loop gennem Maintenance_Items ===
    lastRowItems = GetLastDataRow(ws, CLng(itemCols("ITEM_KEY")), 1)
    
    For i = CLng(itemCols("ROW_START")) To lastRowItems
        itemKey = NormalizeKeyValue(GetMapValue(ws, i, CLng(itemCols("ITEM_KEY"))))
        If itemKey = "" Then GoTo NextItem

        If Not IsReadyItemKey(itemKey) Then
            If Len(GetMapValue(ws, i, sapOutCol)) = 0 Then
                SetMapValue ws, i, sapOutCol, "SKIPPED: Plan status not ready"
            End If
            GoTo NextItem
        End If

        itemDesc = GetMapValue(ws, i, CLng(itemCols("SHORT_TEXT")))
        itemFuncLoc = GetMapValue(ws, i, CLng(itemCols("FUNC_LOC")))
        itemOrderType = GetMapValue(ws, i, CLng(itemCols("ORDER_TYPE")))
        itemILART = GetMapValue(ws, i, CLng(itemCols("ILART")))
        itemILART = NormalizeItemIlartValue(itemILART)
        itemGewerk = GetMapValue(ws, i, CLng(itemCols("GEWERK")))
        itemPrio = GetMapValue(ws, i, CLng(itemCols("PRIORITY")))
        itemPrio = NormalizeItemPriorityValue(itemPrio)
        itemStatus = GetMapValue(ws, i, CLng(itemCols("STATUS")))
        itemNonFlowStatus = GetMapValue(ws, i, CLng(itemCols("NON_FLOW_STATUS")))
        itemRev = GetMapValue(ws, i, CLng(itemCols("REVISION")))
        itemRev = NormalizeItemRevisionValue(itemRev)
        itemRevBy = GetMapValue(ws, i, CLng(itemCols("REV_BY")))
        itemLongText = GetMapValue(ws, i, CLng(itemCols("LONG_TEXT")), False)
        
        ' Hent Task List info
        If MI_TL_dict.Exists(itemKey) Then
            arr = MI_TL_dict(itemKey)
        Else
            SetMapValue ws, i, sapOutCol, "Ingen Task List fundet"
            GoTo NextItem
        End If
        
        ' Hent Object List info
        If MI_OBJ_dict.Exists(itemKey) Then
            objArr = MI_OBJ_dict(itemKey)
        Else
            objArr = Array() ' Tomt array
        End If
        
        '=== Start SAP-transaktion ===
        objSess.FindById("wnd[0]/tbar[0]/okcd").Text = TX_IP04
        objSess.FindById("wnd[0]").sendVKey 0

        '=== SAP GUI Handling ===
        objSess.FindById("wnd[0]/usr/cmbRMIPM-MPTYP").key = "PM"
        objSess.FindById("wnd[0]").sendVKey 0

        ' Marker "Ingen ordreoprettelse"
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/chkMPOS-NO_AUFRELKZ").Selected = True

        ' Hoveddata
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/txtRMIPM-PSTXT").Text = itemDesc
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_1:SAPLIWO1:0100/ctxtRIWO1-TPLNR").Text = itemFuncLoc
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-AUART").Text = itemOrderType
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-ILART").Text = itemILART
        objSess.FindById("wnd[0]").sendVKey 0

        ' Arbejdssted og prioritet
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-GEWERK").Text = itemGewerk
        If Len(itemPrio) > 0 Then
            itemPrioKey = ExtractPriorityKey(itemPrio)

            On Error Resume Next
            If Len(itemPrioKey) > 0 Then
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/cmbRMIPM-PRIOK").key = itemPrioKey
            Else
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/cmbRMIPM-PRIOK").Text = itemPrio
            End If

            If Err.Number <> 0 Then
                Err.Clear
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/cmbRMIPM-PRIOK").Text = itemPrio
            End If
            On Error GoTo myerr
        End If

        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNTY").Text = arr(0) 'Task List Type
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNNR").Text = arr(1) 'Group
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNAL").Text = arr(2) 'Counter
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNAL").SetFocus
        objSess.FindById("wnd[0]").sendVKey 0


        ' Tilf�j Object List

        If UBound(objArr) >= 0 Then

        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12").Select

            For j = LBound(objArr) To UBound(objArr)

                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12/ssubSUBSCREEN_BODY2:SAPLIWP3:8023/subOBJECT:SAPLIWOL:0400/btnBTN_IFLO").press
                objSess.FindById("wnd[0]/usr/btn%_STRNO_%_APP_%-VALU_PUSH").press
                objSess.FindById("wnd[1]/tbar[0]/btn[16]").press
                objSess.FindById("wnd[1]/usr/tabsTAB_STRIP/tabpSIVA/ssubSCREEN_HEADER:SAPLALDB:3010/tblSAPLALDBSINGLE/ctxtRSCSEL_255-SLOW_I[1,0]").Text = objArr(j)
                objSess.FindById("wnd[1]/tbar[0]/btn[8]").press
                objSess.FindById("wnd[0]/tbar[1]/btn[8]").press

            Next j
        End If

        ' Status og revision
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17").Select
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_STATUS").Text = itemStatus
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_NON_FLOW_USER_STAT").Text = itemNonFlowStatus
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_REVNR").Text = itemRev
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/txtCI_MPOS-ZZLREVY").Text = Year(Date)
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/txtCI_MPOS-ZZREVBY").Text = itemRevBy

        ' Gem
        objSess.FindById("wnd[0]/tbar[0]/btn[11]").press

        '=== Udtr�k og gem oprettet item-nummer ===
        statusText = objSess.FindById("wnd[0]/sbar").Text
        Set regex = CreateObject("VBScript.RegExp")
        regex.Pattern = "\d+"
        Set matches = regex.Execute(statusText)

        If matches.Count > 0 Then
            itemNumber = matches(0).Value
            SetMapValue ws, i, sapOutCol, itemNumber
            
            html = itemLongText
            
            ConvertHtmlToSAPITF_Dynamic html, True
            
        objSess.FindById("wnd[0]/tbar[0]/okcd").Text = TX_IP05
        objSess.FindById("wnd[0]").sendVKey 0

        objSess.FindById("wnd[0]/usr/ctxtRMIPM-WAPOS").Text = itemNumber
        objSess.FindById("wnd[0]").sendVKey 0
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/btnRMIPM-LTPOS_ICON").press
        objSess.FindById("wnd[0]/mbar/menu[0]/menu[3]").Select
        objSess.FindById("wnd[1]/usr/radITCTK-TDITF").Select
        objSess.FindById("wnd[1]/usr/radITCTK-TDITF").SetFocus
        objSess.FindById("wnd[1]/tbar[0]/btn[0]").press
        objSess.FindById("wnd[2]/usr/ctxtITCTK-TDFILENAME").Text = SAP_LONGTEXT_ITF_PATH
        objSess.FindById("wnd[2]/usr/ctxtITCTK-TDFILENAME").caretPosition = 27
        objSess.FindById("wnd[2]/tbar[0]/btn[0]").press
        objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
        objSess.FindById("wnd[0]/tbar[0]/btn[11]").press




        Else
            SetMapValue ws, i, sapOutCol, statusText
        End If
        
        
        
NextItem:
    Next i
    
    Exit Sub

'=== Fejlh�ndtering ===
myerr:
    MsgBox "Der opstod en fejl under oprettelse af Items", vbCritical + vbOKOnly

End Sub


Public Sub CreatePlans()

    '===Deklarationer===
    Dim wsPlans As Worksheet, wsMI As Worksheet
    Dim planCols As Object, itemCols As Object
    Dim statusText As String, planNumber As String
    Dim regex As Object, matches As Object
    Dim MP_MI_dict As Object                        ' Plan -> MI dictionary
    Dim CallHorizonDict As Object                   ' cycle/unit -> (A-D) dictionary
    Dim key As Variant
    Dim arr As Variant
    Dim i As Long, j As Long
    Dim lastRow As Long
    Dim planRowDict As Object
    Dim planId As String
    Dim planListId As String
    Dim planRow As Long
    Dim readyStatus As String
    Dim cycleVal As String
    Dim unitVal As String
    Dim sortVal As String
    Dim plannedDateVal As String
    Dim horizonQualifier As String
    Dim sapOutCol As Long
    Dim planLinkCol As Long
    Dim itemKeyCol As Long
    Dim itemSapCol As Long

    '===Initialisering===
    Set wsPlans = Worksheets(WS_MAINTENANCE_PLANS)
    Set wsMI = Worksheets(WS_MAINTENANCE_ITEMS)
    wsPlans.Activate
    On Error GoTo myerr

    ResetCreateScope
    EnsureCreateScope

    If mReadyPlanSet Is Nothing Or mReadyPlanSet.Count = 0 Then
        MsgBox "Ingen planer er markeret til oprettelse med status 'Ready for creation in SAP'.", vbInformation + vbOKOnly
        Exit Sub
    End If

    Set planCols = BuildPlansColumnMap(wsPlans)
    Set itemCols = BuildItemsColumnMap(wsMI)

    RequireColumn CLng(planCols("PLAN_KEY")), "PlanID", wsPlans.name
    RequireColumn CLng(planCols("STATUS")), "Status", wsPlans.name
    RequireColumn CLng(planCols("DESCRIPTION")), "Title", wsPlans.name
    RequireColumn CLng(planCols("CYCLE")), "Cycle", wsPlans.name
    RequireColumn CLng(planCols("UNIT")), "Unit", wsPlans.name
    RequireColumn CLng(planCols("PLANNED_DATE")), "PlannedDate", wsPlans.name
    RequireColumn CLng(planCols("SAP_OUTPUT")), "SAPNum", wsPlans.name

    RequireColumn CLng(itemCols("PLAN_KEY")), "MaintenancePlanNo", wsMI.name
    RequireColumn CLng(itemCols("ITEM_KEY")), "ItemID", wsMI.name
    RequireColumn CLng(itemCols("SAP_OUTPUT")), "SAPNumber", wsMI.name

    sapOutCol = CLng(planCols("SAP_OUTPUT"))
    planLinkCol = CLng(itemCols("PLAN_KEY"))
    itemKeyCol = CLng(itemCols("ITEM_KEY"))
    itemSapCol = CLng(itemCols("SAP_OUTPUT"))

    '----------------------------------------------------------------------
    ' Opret dictionary ud fra tabellen Call_Horizon (A-D)
    ' N�gle: kolonne A (cycle/unit, fx "10WK")
    ' V�rdi: array(1..4) = (A=cycle/unit, B=FCD, C=scheduling period, D=scheduling period Unit)
    '----------------------------------------------------------------------
    Set CallHorizonDict = CreateObject("Scripting.Dictionary")
    BuildCallHorizonDict CallHorizonDict

    '===Opret dictionary med Maintenance Plan -> Maintenance Items===
    Set MP_MI_dict = CreateObject("Scripting.Dictionary")
    MP_MI_dict.CompareMode = vbTextCompare
    Set planRowDict = CreateObject("Scripting.Dictionary")
    planRowDict.CompareMode = vbTextCompare

    lastRow = GetLastDataRow(wsMI, itemKeyCol, 1)

    For i = CLng(itemCols("ROW_START")) To lastRow
        Dim planKey As String, itemValue As String
        Dim readyItemKey As String

        readyItemKey = NormalizeKeyValue(GetMapValue(wsMI, i, itemKeyCol))
        If Len(readyItemKey) = 0 Then GoTo NextItemRow
        If Not IsReadyItemKey(readyItemKey) Then GoTo NextItemRow

        planKey = NormalizeKeyValue(GetMapValue(wsMI, i, planLinkCol))
        itemValue = GetMapValue(wsMI, i, itemSapCol)

        If planKey <> "" And itemValue <> "" Then
            If IsReadyPlanKey(planKey) Then
                If IsDigitsOnly(itemValue) Then
                    If Not MP_MI_dict.Exists(planKey) Then
                        MP_MI_dict.Add planKey, Array(itemValue)
                    Else
                        ' Tilf�j nyt item til eksisterende array
                        arr = MP_MI_dict(planKey)
                        ReDim Preserve arr(UBound(arr) + 1)
                        arr(UBound(arr)) = itemValue
                        MP_MI_dict(planKey) = arr
                    End If
                End If
            End If
        End If
NextItemRow:
    Next i

    ' Cache plan row positions to avoid repeated linear searches
    For i = CLng(planCols("ROW_START")) To GetLastDataRow(wsPlans, CLng(planCols("PLAN_KEY")), 1)
        planId = NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(planCols("PLAN_KEY"))))
        planListId = NormalizeKeyValue(GetMapValue(wsPlans, i, CLng(planCols("LIST_ID"))))
        readyStatus = GetMapValue(wsPlans, i, CLng(planCols("STATUS")))

        If IsReadyStatus(readyStatus) Then
            If planId <> "" Then planRowDict(planId) = i
            If planListId <> "" Then planRowDict(planListId) = i
        Else
            If Len(GetMapValue(wsPlans, i, sapOutCol)) = 0 Then
                SetMapValue wsPlans, i, sapOutCol, "SKIPPED: Status not ready"
            End If
        End If
    Next i

    '===Start SAP-transaktion===
    objSess.FindById("wnd[0]/tbar[0]/okcd").Text = TX_IP01
    objSess.FindById("wnd[0]").sendVKey 0

    '===Loop gennem alle keys i dictionary===
    For Each key In MP_MI_dict.Keys
        ' Find rækken i Maintenance_Plans for denne key via lookup dictionary
        planRow = 0
        If planRowDict.Exists(CStr(key)) Then
            planRow = CLng(planRowDict(CStr(key)))
        End If

        If planRow > 0 Then
            arr = MP_MI_dict(key)

            '===Loop gennem alle Maintenance Items for denne plan===
            ' SAP GUI handlinger
            objSess.FindById("wnd[0]/usr/cmbRMIPM-MPTYP").key = "PM"
            objSess.FindById("wnd[0]/usr/ctxtRMIPM-WSTRA").Text = ""

            objSess.FindById("wnd[0]").sendVKey 0

            '--- Sl� Call_Horizon-oplysninger op baseret p� cycle/unit i planen ---
            Dim cycleUnitKey As String
            cycleVal = GetMapValue(wsPlans, planRow, CLng(planCols("CYCLE")))
            unitVal = GetMapValue(wsPlans, planRow, CLng(planCols("UNIT")))
            plannedDateVal = GetMapValue(wsPlans, planRow, CLng(planCols("PLANNED_DATE")))
            plannedDateVal = ResolvePlanStartDate(plannedDateVal, cycleVal, unitVal)
            sortVal = GetMapValue(wsPlans, planRow, CLng(planCols("SORT")))
            If Left$(sortVal, 1) = "'" Then sortVal = Mid$(sortVal, 2)
            If InStr(1, sortVal, ";#", vbBinaryCompare) > 0 Then sortVal = Split(sortVal, ";#")(0)
            sortVal = Trim$(sortVal)
            cycleUnitKey = UCase$(Trim$(cycleVal) & Trim$(unitVal))

            Dim chArr As Variant
            Dim hasCH As Boolean
            hasCH = False
            If CallHorizonDict.Exists(cycleUnitKey) Then
                chArr = CallHorizonDict(cycleUnitKey) ' (A,B,C,D) = (cycle/unit, FCD, sched period, sched unit)
                hasCH = True
            End If

            If Not hasCH Then
                SetMapValue wsPlans, planRow, sapOutCol, "SKIPPED: Call_Horizon mangler for " & cycleUnitKey
                GoTo NextPlan
            End If

            For j = LBound(arr) To UBound(arr)

                ' --- Tekst og cyklus fra Maintenance_Plans ---
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6000/txtRMIPM-WPTXT").Text = GetMapValue(wsPlans, planRow, CLng(planCols("DESCRIPTION")))
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/txtRMIPM-ZYKL1").Text = cycleVal
                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/ctxtRMIPM-ZEIEH").Text = unitVal

                objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_MAINT_ITEM_TEXT:SAPLIWP3:6005/btnITEM_LINK").press

                If j = 0 Then
                    objSess.FindById("wnd[1]").sendVKey 0
                End If

                objSess.FindById("wnd[0]/usr/txtWAPOS-LOW").Text = arr(j)
                objSess.FindById("wnd[0]/tbar[1]/btn[8]").press
                objSess.FindById("wnd[0]/usr/cntlGRID1/shellcont/shell").SelectedRows = "0"
                objSess.FindById("wnd[0]/tbar[1]/btn[42]").press

            Next j

            ' Udfyld plan-data fra Maintenance_Plans
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6000/txtRMIPM-WPTXT").Text = GetMapValue(wsPlans, planRow, CLng(planCols("DESCRIPTION")))
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/txtRMIPM-ZYKL1").Text = cycleVal
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/ctxtRMIPM-ZEIEH").Text = unitVal
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/ctxtRMIPM-ZEIEH").SetFocus

            '=== Tab: Scheduling Parameters ===
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02").Select

            horizonQualifier = "FCD"

            ' chArr(2) = FCD, chArr(3) = scheduling period, chArr(4) = scheduling period unit
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/txtRMIPM-HORIZ").Text = chArr(2)
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/ctxtRMIPM-HORIZ_QUALIFIER").Text = horizonQualifier
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/txtRMIPM-ABRHO").Text = chArr(3)
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/ctxtRMIPM-HUNIT").Text = chArr(4)

            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/ctxtRMIPM-STADT").Text = plannedDateVal ' Start dato
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/radRMIPM-STICH").Select
            
            If sortVal <> "" Then
            
            '=== Tab: Sort ===
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\03").Select
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\03/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0113/cmbRMIPM-PLAN_SORT").key = sortVal
            objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\03/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0113/cmbRMIPM-PLAN_SORT").SetFocus
            
            End If
            
            objSess.FindById("wnd[0]/tbar[0]/btn[11]").press

            '===Udtr�k og gem oprettet Plan-nummer===
            statusText = objSess.FindById("wnd[0]/sbar").Text
            Set regex = CreateObject("VBScript.RegExp")
            regex.Pattern = "\d+"
            Set matches = regex.Execute(statusText)

            If matches.Count > 0 Then
                planNumber = matches(0).Value
                SetMapValue wsPlans, planRow, sapOutCol, planNumber
            Else
                SetMapValue wsPlans, planRow, sapOutCol, statusText
            End If
        End If
NextPlan:
    Next key

    MsgBox "Alle planer er oprettet!"
    Exit Sub

'===Fejlh�ndtering===
myerr:
    MsgBox "Der opstod en fejl under oprettelse af planer", vbCritical + vbOKOnly

End Sub


'===============================================================================
' Hj�lperoutine: bygger Dictionary ud fra tabellen Call_Horizon p� ark Call_Horizon_Table
' Forventer en tabel (ListObject) med navnet "Call_Horizon"
'===============================================================================
Private Sub BuildCallHorizonDict(ByRef dict As Object)
    Dim wsCH As Worksheet
    Dim loCH As ListObject
    Dim r As Long
    Dim k As String
    Dim rowArr(1 To 4) As Variant

    Set wsCH = ThisWorkbook.Worksheets(WS_CALL_HORIZON_TABLE)
    Set loCH = wsCH.ListObjects(LO_CALL_HORIZON)  ' Sørg for at tabellen hedder præcis sådan

    For r = 1 To loCH.ListRows.Count
        k = UCase(Trim(CStr(loCH.DataBodyRange(r, 1).Value)))   ' A: cycle/unit, fx "10WK"
        If Len(k) > 0 Then
            rowArr(1) = loCH.DataBodyRange(r, 1).Value          ' A: cycle/unit
            rowArr(2) = loCH.DataBodyRange(r, 2).Value          ' B: FCD
            rowArr(3) = loCH.DataBodyRange(r, 3).Value          ' C: scheduling period
            rowArr(4) = loCH.DataBodyRange(r, 4).Value          ' D: scheduling period Unit
            dict(k) = rowArr
        End If
    Next r
End Sub


Sub ConvertHtmlToSAPITF_Dynamic(html As String, Optional ByVal preserveLeadingBreakForItemDescription As Boolean = False)
    Dim filePath As String
    Dim objectType As String, objectKey As String, language As String
    Dim fileNum As Integer, lines() As String, i As Long
    Dim formattedText As String
    Dim preserveLeadingBreak As Boolean
    
    ' === INPUT ===
    language = "E"               ' E = English, D = German, etc.
    filePath = SAP_LONGTEXT_ITF_PATH
    preserveLeadingBreak = (preserveLeadingBreakForItemDescription And TextStartsWithLineBreak(html))
    
    ' === KONVERTER HTML TIL SAP-TAGS ===
    formattedText = NormalizeSapLineBreaks(HtmlToSAPText(html))

    If preserveLeadingBreak Then
        Do While Len(formattedText) > 0 And Left$(formattedText, 1) = vbLf
            formattedText = Mid$(formattedText, 2)
        Loop

        formattedText = vbLf & formattedText
    End If

    lines = Split(formattedText, vbLf)
    
    ' === SKRIV ITF-FIL ===
    fileNum = FreeFile
    Open filePath For Output As #fileNum
    
    ' Header
    Print #fileNum, "/HTEXT"
    Print #fileNum, "/:OBJECT"
    Print #fileNum, "/:NAME"
    Print #fileNum, "/:ID LTXT"
    Print #fileNum, "/:LANGUAGE " & language
    Print #fileNum, "/:FORM SYSTEM"
    Print #fileNum, "/:STYLE"
    Print #fileNum, "/:FIRST-USER"
    Print #fileNum, "/:FIRST-DATE"
    Print #fileNum, "/:FIRST-TIME"
    Print #fileNum, "/:LAST-USER"
    Print #fileNum, "/:LAST-DATE"
    Print #fileNum, "/:LAST-TIME"
    Print #fileNum, "/:TITLE"
    Print #fileNum, "/:TITLE1"
    Print #fileNum, "/:TITLE2"
    
    ' Tekstsektion
    Print #fileNum, "/MTEXT"
    For i = LBound(lines) To UBound(lines)
        WriteSapItfTextLine fileNum, lines(i)
    Next i
    
    Close #fileNum
End Sub

Private Function TextStartsWithLineBreak(ByVal textValue As String) As Boolean
    Dim s As String

    s = Replace(textValue, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)

    If Len(s) = 0 Then Exit Function
    TextStartsWithLineBreak = (Left$(s, 1) = vbLf)
End Function

Private Function NormalizeSapLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    s = Replace(s, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)

    Do While InStr(1, s, vbLf & vbLf & vbLf, vbBinaryCompare) > 0
        s = Replace(s, vbLf & vbLf & vbLf, vbLf & vbLf)
    Loop

    NormalizeSapLineBreaks = s
End Function

Private Sub WriteSapItfTextLine(ByVal fileNum As Integer, ByVal textLine As String)
    Const MAX_ITF_TEXT_CHARS As Long = 120

    Dim lineText As String
    lineText = Replace(textLine, vbTab, " ")
    lineText = Replace(lineText, Chr$(160), " ")
    lineText = RTrim$(lineText)

    If Len(lineText) = 0 Then
        Print #fileNum, "*"
        Exit Sub
    End If

    Do While Len(lineText) > MAX_ITF_TEXT_CHARS
        Dim splitPos As Long
        splitPos = InStrRev(Left$(lineText, MAX_ITF_TEXT_CHARS + 1), " ")
        If splitPos <= 0 Then splitPos = MAX_ITF_TEXT_CHARS

        Print #fileNum, "* " & Left$(lineText, splitPos)
        lineText = LTrim$(Mid$(lineText, splitPos + 1))
    Loop

    Print #fileNum, "* " & lineText
End Sub




Function HtmlToSAPText(ByVal HtmlString As String) As String
    Dim temp As String
    Dim RE As Object
    Dim lines() As String
    Dim lineIndex As Long

    ' 1) Decode HTML entities (&lt; &gt; &amp;nbsp;)
    If InStr(1, HtmlString, "<", vbBinaryCompare) > 0 Or _
       InStr(1, HtmlString, "&", vbBinaryCompare) > 0 Then
        temp = HtmlDecode(HtmlString)
    Else
        temp = HtmlString
    End If

    temp = Replace(temp, vbCrLf, vbLf)
    temp = Replace(temp, vbCr, vbLf)

    Set RE = CreateObject("VBScript.RegExp")
    RE.Global = True
    RE.IgnoreCase = True

    ' 2) Normalize line breaks from HTML
    RE.Pattern = "<br\s*/?>"
    temp = RE.Replace(temp, vbLf)

    ' 3) Erstat HTML-tags med SAP-tags (åbne og lukke)
    RE.Pattern = "<(strong|b)>"
    temp = RE.Replace(temp, "<H>")
    RE.Pattern = "</(strong|b)>"
    temp = RE.Replace(temp, "</>")
    RE.Pattern = "<u>"
    temp = RE.Replace(temp, "<U>")
    RE.Pattern = "</u>"
    temp = RE.Replace(temp, "</>")

    ' 4) Fjern alle <span ...> og </span>
    RE.Pattern = "<span[^>]*>|</span>"
    temp = RE.Replace(temp, "")

    ' 5) Fjern <div ...> og </div>
    RE.Pattern = "<div[^>]*>|</div>"
    temp = RE.Replace(temp, "")

    ' 6) Erstat <p ...> og </p> med linjeskift
    RE.Pattern = "<p[^>]*>"
    temp = RE.Replace(temp, vbLf)
    RE.Pattern = "</p>"
    temp = RE.Replace(temp, vbLf)

    ' 7) Fjern <ul> og </ul>
    RE.Pattern = "</?ul>"
    temp = RE.Replace(temp, "")

    ' 8) Punktopstilling
    RE.Pattern = "<li[^>]*>"
    temp = RE.Replace(temp, vbLf & "-")
    RE.Pattern = "</li>"
    temp = RE.Replace(temp, vbLf)

    ' 9) Erstat non-breaking spaces med mellemrum
    temp = Replace(temp, "&nbsp;", " ")
    temp = Replace(temp, Chr$(160), " ")

    ' 10) Fjern alle resterende HTML-tags undtagen SAP-tags (<H>, <U>, </>)
    RE.Pattern = "<(?!/?(H|U)>)\/?\w+[^>]*>"
    temp = RE.Replace(temp, "")

    ' 11) Trim linjer og fjern ekstra linjeskift
    lines = Split(temp, vbLf)
    For lineIndex = 0 To UBound(lines)
        lines(lineIndex) = Trim(lines(lineIndex))
    Next lineIndex
    temp = Join(lines, vbLf)

    ' 12) Begræns kun overdrevne blanklinjer, men bevar afsnit
    RE.MultiLine = False
    RE.Pattern = "(\n){3,}"
    temp = RE.Replace(temp, vbLf & vbLf)

    Do While Len(temp) > 0 And Left$(temp, 1) = vbLf
        temp = Mid$(temp, 2)
    Loop

    Do While Len(temp) > 0 And Right$(temp, 1) = vbLf
        temp = Left$(temp, Len(temp) - 1)
    Loop

    HtmlToSAPText = temp
End Function

' HTML decode helper
Function HtmlDecode(ByVal s As String) As String
    Dim html As Object
    Dim decoded As String

    If Len(s) = 0 Then
        HtmlDecode = ""
        Exit Function
    End If

    Set html = CreateObject("htmlfile")
    html.Open
    html.Write s
    html.Close

    If Not html Is Nothing And Not html.Body Is Nothing Then
        decoded = html.Body.innerHTML
        decoded = Replace(decoded, Chr$(160), " ")
        HtmlDecode = decoded
    Else
        HtmlDecode = s
    End If
End Function

