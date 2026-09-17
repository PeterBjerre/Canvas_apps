Attribute VB_Name = "modSharePointImport"
Option Explicit

Private Const START_ROW_DEFAULT As Long = 3
Private Const START_ROW_TL As Long = 2
Private Const PLAN_SELECTION_HEADER As String = "CreateInSAP"
Private Const PLAN_READY_STATUS As String = "ready for creation in sap"

' Listerne staar som NAVNE, ikke som URL'er. Sitet kommer fra
' modEnvironment.GetSiteUrl(), saa alle fire foelger miljoevalget i
' Setup!D2 og ikke kan pege hver sin vej. De fire hardkodede
' BioSAP-URL'er, der stod her, var grunden til at kun GUI-delen kunne
' skifte miljoe.
Private Const CFG_LIST_PLANS As String = "MaintenancePlans"
Private Const CFG_LIST_ITEMS As String = "MaintenanceItems"
Private Const CFG_LIST_TLH As String = "TaskListMain"
Private Const CFG_LIST_TL As String = "TaskListMain"

' Tom = auto: bruger Environ("USERNAME"), fx PKBJE
Private Const CFG_SHAREPOINT_CREDENTIAL_TARGET As String = ""
Private Const CFG_SHAREPOINT_CREDENTIAL_PREFIX As String = ""
Private Const CFG_SHAREPOINT_CREDENTIAL_SUFFIX As String = ""
Private Const CFG_SHAREPOINT_TOKEN_FALLBACK As String = ""
Private Const CFG_SHAREPOINT_ALLOW_NO_TOKEN As Boolean = True
Private Const CFG_SHAREPOINT_TLH_FILTER As String = ""
Private Const CFG_SHAREPOINT_TL_FILTER As String = ""
Private Const ITEMS_SELECT_EXPAND_CLAUSE As String = "$select=*,FieldValuesAsText&$expand=FieldValuesAsText"

Private Const CRED_TYPE_GENERIC As Long = 1

#If VBA7 Then
    Private Type FILETIME
        dwLowDateTime As Long
        dwHighDateTime As Long
    End Type

    Private Type CREDENTIALW
        Flags As Long
        CredType As Long
        TargetName As LongPtr
        Comment As LongPtr
        LastWritten As FILETIME
        CredentialBlobSize As Long
        CredentialBlob As LongPtr
        Persist As Long
        AttributeCount As Long
        Attributes As LongPtr
        TargetAlias As LongPtr
        UserName As LongPtr
    End Type

    Private Declare PtrSafe Function CredReadW Lib "advapi32.dll" ( _
        ByVal TargetName As LongPtr, _
        ByVal CredType As Long, _
        ByVal Flags As Long, _
        ByRef Credential As LongPtr) As Long

    Private Declare PtrSafe Sub CredFree Lib "advapi32.dll" (ByVal Buffer As LongPtr)

    Private Declare PtrSafe Sub CopyMemory Lib "kernel32" Alias "RtlMoveMemory" ( _
        Destination As Any, _
        Source As Any, _
        ByVal Length As LongPtr)
#Else
    Private Type FILETIME
        dwLowDateTime As Long
        dwHighDateTime As Long
    End Type

    Private Type CREDENTIALW
        Flags As Long
        CredType As Long
        TargetName As Long
        Comment As Long
        LastWritten As FILETIME
        CredentialBlobSize As Long
        CredentialBlob As Long
        Persist As Long
        AttributeCount As Long
        Attributes As Long
        TargetAlias As Long
        UserName As Long
    End Type

    Private Declare Function CredReadW Lib "advapi32.dll" ( _
        ByVal TargetName As Long, _
        ByVal CredType As Long, _
        ByVal Flags As Long, _
        ByRef Credential As Long) As Long

    Private Declare Sub CredFree Lib "advapi32.dll" (ByVal Buffer As Long)

    Private Declare Sub CopyMemory Lib "kernel32" Alias "RtlMoveMemory" ( _
        Destination As Any, _
        Source As Any, _
        ByVal Length As Long)
#End If

Public Sub ImportSharePointMaintenanceData(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim stage As String
    stage = "Init"

    Dim authHeader As String
    stage = "Auth"
    authHeader = GetSharePointAuthHeader()

    Dim cntPlans As Long
    Dim cntItems As Long
    Dim cntObjectList As Long
    Dim cntTlh As Long
    Dim cntTl As Long

    stage = WS_MAINTENANCE_PLANS
    cntPlans = ImportSharePointListToSheet( _
        GetSharePointPlansUrl(), _
        vbNullString, _
        WS_MAINTENANCE_PLANS, _
        START_ROW_DEFAULT, _
        DefaultHeadersPlans(), _
        BuildAliasMapPlans(), _
        authHeader)

    stage = "MaintenancePlansPostProcessing"
    ApplyMaintenancePlansPostProcessing authHeader

    stage = WS_MAINTENANCE_ITEMS
    cntItems = ImportSharePointListToSheet( _
        GetSharePointItemsUrl(), _
        ITEMS_SELECT_EXPAND_CLAUSE, _
        WS_MAINTENANCE_ITEMS, _
        START_ROW_DEFAULT, _
        DefaultHeadersItems(), _
        BuildAliasMapItems(), _
        authHeader)

    stage = "MaintenanceItemsLookupText"
    ApplyMaintenanceItemsLookupText authHeader

    stage = "MaintenanceItemsPlanDisplay"
    ApplyMaintenanceItemsPlanNoDisplayAndColors

    stage = WS_OBJECT_LIST
    cntObjectList = RefreshObjectListFromMaintenanceItems()

    stage = WS_MAINTENANCE_TLH
    cntTlh = ImportSharePointListToSheet( _
        GetSharePointTlhUrl(), _
        GetSharePointTlhFilter(), _
        WS_MAINTENANCE_TLH, _
        START_ROW_DEFAULT, _
        DefaultHeadersTlh(), _
        BuildAliasMapTlh(), _
        authHeader)

    stage = "MaintenanceTlhPostProcessing"
    ApplyMaintenanceTlhPostProcessing

    stage = WS_MAINTENANCE_TL
    cntTl = ImportSharePointListToSheet( _
        GetSharePointTlUrl(), _
        GetSharePointTlFilter(), _
        WS_MAINTENANCE_TL, _
        START_ROW_TL, _
        DefaultHeadersTl(), _
        BuildAliasMapTl(), _
        authHeader)

    stage = "MaintenanceTlPostProcessing"
    ApplyMaintenanceTlDisplayAndColors

    If showSummary Then
        MsgBox modEnvironment.DescribeEnvironment() & vbCrLf & vbCrLf & _
               "SharePoint import faerdig." & vbCrLf & _
               WS_MAINTENANCE_PLANS & ": " & CStr(cntPlans) & vbCrLf & _
               WS_MAINTENANCE_ITEMS & ": " & CStr(cntItems) & vbCrLf & _
               WS_OBJECT_LIST & ": " & CStr(cntObjectList) & vbCrLf & _
               WS_MAINTENANCE_TLH & ": " & CStr(cntTlh) & vbCrLf & _
               WS_MAINTENANCE_TL & ": " & CStr(cntTl), vbInformation + vbOKOnly
    End If

    Exit Sub
EH:
    MsgBox "Import fejl i stage '" & stage & "':" & vbCrLf & _
           CStr(Err.Number) & " - " & Err.Description, vbCritical + vbOKOnly
End Sub

Public Sub RefreshSharePointDataFromButton()
    ImportSharePointMaintenanceData True
End Sub

Public Sub CreateMaintenancePlansFromButton()
    On Error GoTo EH

    StartExtract
    Exit Sub
EH:
    MsgBox "Kunne ikke starte oprettelse af Maintenance Plans: " & Err.Description, vbExclamation + vbOKOnly
End Sub

Public Sub EnforceMaintenancePlansSelectionForRange(ByVal target As Range)
    On Error GoTo SafeExit

    If target Is Nothing Then Exit Sub

    Dim ws As Worksheet
    Set ws = target.Worksheet
    If ws Is Nothing Then Exit Sub

    If StrComp(ws.Name, WS_MAINTENANCE_PLANS, vbTextCompare) <> 0 Then Exit Sub

    Dim selectionCol As Long
    Dim statusCol As Long
    If Not TryGetMaintenancePlansSelectionColumns(ws, selectionCol, statusCol) Then Exit Sub

    Dim changedSelection As Range
    Set changedSelection = Intersect(target, ws.Columns(selectionCol))
    If changedSelection Is Nothing Then Exit Sub

    Dim eventsWasEnabled As Boolean
    eventsWasEnabled = Application.EnableEvents
    Application.EnableEvents = False

    Dim cell As Range
    For Each cell In changedSelection.Cells
        If cell.Row >= START_ROW_DEFAULT Then
            ApplyMaintenancePlanSelectionForCell ws, cell, statusCol, False
        End If
    Next cell

SafeExit:
    On Error Resume Next
    Application.EnableEvents = eventsWasEnabled
End Sub

Public Function ToggleMaintenancePlansSelectionByCell(ByVal targetCell As Range) As Boolean
    On Error GoTo SafeExit

    If targetCell Is Nothing Then Exit Function
    If targetCell.CountLarge <> 1 Then Exit Function

    Dim ws As Worksheet
    Set ws = targetCell.Worksheet
    If ws Is Nothing Then Exit Function

    If StrComp(ws.Name, WS_MAINTENANCE_PLANS, vbTextCompare) <> 0 Then Exit Function

    Dim selectionCol As Long
    Dim statusCol As Long
    If Not TryGetMaintenancePlansSelectionColumns(ws, selectionCol, statusCol) Then Exit Function

    If targetCell.Column <> selectionCol Then Exit Function
    If targetCell.Row < START_ROW_DEFAULT Then
        ToggleMaintenancePlansSelectionByCell = True
        Exit Function
    End If

    Dim eventsWasEnabled As Boolean
    eventsWasEnabled = Application.EnableEvents
    Application.EnableEvents = False

    Dim isReady As Boolean
    isReady = IsReadyPlanStatusValue(CStr(ws.Cells(targetCell.Row, statusCol).Value))

    If isReady Then
        If IsPlanSelectionChecked(CStr(targetCell.Value)) Then
            targetCell.Value = PlanSelectionUncheckedMarker()
        Else
            targetCell.Value = PlanSelectionCheckedMarker()
        End If
    Else
        targetCell.Value = PlanSelectionUncheckedMarker()
    End If

    ApplyMaintenancePlanSelectionValidationForCell ws, targetCell, isReady
    ToggleMaintenancePlansSelectionByCell = True

SafeExit:
    On Error Resume Next
    Application.EnableEvents = eventsWasEnabled
End Function

Public Sub EnsureMaintenancePlansImportButton()
    Const BTN_IMPORT_NAME As String = "btnImportSharePointData"
    Const BTN_IMPORT_CAPTION As String = "Opdater SharePoint-data"
    Const BTN_CREATE_NAME As String = "btnCreateMaintenancePlans"
    Const BTN_CREATE_CAPTION As String = "Create Maintenance Plans"
    Const BTN_SYNC_NAME As String = "btnSyncSapToSharePoint"
    Const BTN_SYNC_CAPTION As String = "Sync SAP-nummer til SharePoint"

    On Error GoTo EH

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)

    On Error Resume Next
    ws.Shapes(BTN_IMPORT_NAME).Delete
    ws.Shapes(BTN_CREATE_NAME).Delete
    ws.Shapes(BTN_SYNC_NAME).Delete
    On Error GoTo EH

    Dim btnLeft As Double
    Dim btnTop As Double
    Dim btnWidth As Double
    Dim btnHeight As Double
    Dim btnGap As Double

    btnLeft = ws.Range("N1").Left
    btnTop = ws.Range("N1").Top
    btnWidth = 220
    btnHeight = 24
    btnGap = 4

    Dim shpImport As Shape
    Set shpImport = ws.Shapes.AddShape(msoShapeRoundedRectangle, btnLeft, btnTop, btnWidth, btnHeight)

    shpImport.Name = BTN_IMPORT_NAME
    shpImport.OnAction = "'" & ThisWorkbook.Name & "'!RefreshSharePointDataFromButton"
    shpImport.Placement = xlMove

    shpImport.TextFrame.Characters.Text = BTN_IMPORT_CAPTION
    shpImport.TextFrame.HorizontalAlignment = xlHAlignCenter
    shpImport.TextFrame.VerticalAlignment = xlVAlignCenter

    shpImport.Line.Visible = msoFalse
    shpImport.Fill.ForeColor.RGB = RGB(0, 120, 215)
    shpImport.TextFrame.Characters.Font.Color = RGB(255, 255, 255)
    shpImport.TextFrame.Characters.Font.Bold = True

    Dim shpCreate As Shape
    Set shpCreate = ws.Shapes.AddShape(msoShapeRoundedRectangle, btnLeft, btnTop + btnHeight + btnGap, btnWidth, btnHeight)

    shpCreate.Name = BTN_CREATE_NAME
    shpCreate.OnAction = "'" & ThisWorkbook.Name & "'!CreateMaintenancePlansFromButton"
    shpCreate.Placement = xlMove

    shpCreate.TextFrame.Characters.Text = BTN_CREATE_CAPTION
    shpCreate.TextFrame.HorizontalAlignment = xlHAlignCenter
    shpCreate.TextFrame.VerticalAlignment = xlVAlignCenter

    shpCreate.Line.Visible = msoFalse
    shpCreate.Fill.ForeColor.RGB = RGB(0, 153, 90)
    shpCreate.TextFrame.Characters.Font.Color = RGB(255, 255, 255)
    shpCreate.TextFrame.Characters.Font.Bold = True

    Dim shpSync As Shape
    Set shpSync = ws.Shapes.AddShape(msoShapeRoundedRectangle, btnLeft, btnTop + ((btnHeight + btnGap) * 2), btnWidth, btnHeight)

    shpSync.Name = BTN_SYNC_NAME
    shpSync.OnAction = "'" & ThisWorkbook.Name & "'!RunSharePointSyncFromButton"
    shpSync.Placement = xlMove

    shpSync.TextFrame.Characters.Text = BTN_SYNC_CAPTION
    shpSync.TextFrame.HorizontalAlignment = xlHAlignCenter
    shpSync.TextFrame.VerticalAlignment = xlVAlignCenter

    shpSync.Line.Visible = msoFalse
    shpSync.Fill.ForeColor.RGB = RGB(255, 140, 0)
    shpSync.TextFrame.Characters.Font.Color = RGB(255, 255, 255)
    shpSync.TextFrame.Characters.Font.Bold = True

    Exit Sub
EH:
    MsgBox "Kunne ikke oprette knapper pa '" & WS_MAINTENANCE_PLANS & "': " & Err.Description, vbExclamation + vbOKOnly
End Sub

Public Sub ImportSharePointMaintenancePlans(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim cnt As Long
    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    cnt = ImportSharePointListToSheet( _
        GetSharePointPlansUrl(), _
        vbNullString, _
        WS_MAINTENANCE_PLANS, _
        START_ROW_DEFAULT, _
        DefaultHeadersPlans(), _
        BuildAliasMapPlans(), _
        authHeader)

    ApplyMaintenancePlansPostProcessing authHeader

    If showSummary Then MsgBox WS_MAINTENANCE_PLANS & " importeret: " & CStr(cnt) & " raekker.", vbInformation + vbOKOnly
    Exit Sub
EH:
    MsgBox "Import fejl (" & WS_MAINTENANCE_PLANS & "): " & Err.Description, vbCritical + vbOKOnly
End Sub

Public Sub ImportSharePointMaintenancePlansAllFields(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim stage As String
    stage = "Fetch"

    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    Dim items As Collection
    Set items = FetchSharePointItems( _
        GetSharePointPlansUrl(), _
        vbNullString, _
        authHeader)

    stage = "Headers"
    Dim headers As Variant
    headers = BuildAllFieldHeaders(items)

    stage = "Rows"
    Dim rows As Variant
    rows = BuildRowsFromItems(items, headers, Nothing)

    stage = "Write"
    WriteImportRows WS_MAINTENANCE_PLANS, START_ROW_DEFAULT, headers, rows

    stage = "MaintenancePlansPostProcessing"
    ApplyMaintenancePlansPostProcessing authHeader

    If showSummary Then
        MsgBox WS_MAINTENANCE_PLANS & " all-fields importeret: " & CStr(CollectionCount(items)) & _
               " raekker og " & CStr(HeaderCount(headers)) & " kolonner.", vbInformation + vbOKOnly
    End If
    Exit Sub
EH:
    Dim errText As String
    errText = "Import fejl (" & WS_MAINTENANCE_PLANS & " all-fields) i stage '" & stage & "': " & _
              CStr(Err.Number) & " - " & Err.Description

    If showSummary Then
        MsgBox errText, vbCritical + vbOKOnly
    Else
        Err.Raise Err.Number, , errText
    End If
End Sub

Public Sub ImportSharePointMaintenanceItems(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim cnt As Long
    Dim cntObjectList As Long
    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    cnt = ImportSharePointListToSheet( _
        GetSharePointItemsUrl(), _
        ITEMS_SELECT_EXPAND_CLAUSE, _
        WS_MAINTENANCE_ITEMS, _
        START_ROW_DEFAULT, _
        DefaultHeadersItems(), _
        BuildAliasMapItems(), _
        authHeader)

    ApplyMaintenanceItemsLookupText authHeader
    ApplyMaintenanceItemsPlanNoDisplayAndColors

    cntObjectList = RefreshObjectListFromMaintenanceItems()

    If showSummary Then
        MsgBox WS_MAINTENANCE_ITEMS & " importeret: " & CStr(cnt) & " raekker." & vbCrLf & _
               WS_OBJECT_LIST & ": " & CStr(cntObjectList) & " raekker.", vbInformation + vbOKOnly
    End If
    Exit Sub
EH:
    Dim errText As String
    errText = "Import fejl (" & WS_MAINTENANCE_ITEMS & "): " & CStr(Err.Number) & " - " & Err.Description

    If showSummary Then
        MsgBox errText, vbCritical + vbOKOnly
    Else
        Err.Raise Err.Number, , errText
    End If
End Sub

Public Function RunImportSharePointMaintenanceItemsSafe() As String
    On Error GoTo EH

    ImportSharePointMaintenanceItems False
    RunImportSharePointMaintenanceItemsSafe = "OK"
    Exit Function
EH:
    RunImportSharePointMaintenanceItemsSafe = CStr(Err.Number) & " - " & Err.Description
End Function

Public Sub ImportSharePointMaintenanceItemsAllFields(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim stage As String
    stage = "Fetch"

    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    Dim items As Collection
    Set items = FetchSharePointItems( _
        GetSharePointItemsUrl(), _
        "$select=*,FieldValuesAsText&$expand=FieldValuesAsText", _
        authHeader)

    stage = "Headers"
    Dim headers As Variant
    headers = BuildAllFieldHeaders(items)

    stage = "Rows"
    Dim rows As Variant
    rows = BuildRowsFromItems(items, headers, Nothing)

    stage = "Write"
    WriteImportRows WS_MAINTENANCE_ITEMS, START_ROW_DEFAULT, headers, rows

    stage = "MaintenanceItemsLookupText"
    ApplyMaintenanceItemsLookupText authHeader

    stage = "MaintenanceItemsPlanDisplay"
    ApplyMaintenanceItemsPlanNoDisplayAndColors

    stage = WS_OBJECT_LIST
    Dim cntObjectList As Long
    cntObjectList = RefreshObjectListFromMaintenanceItems()

    If showSummary Then
        MsgBox WS_MAINTENANCE_ITEMS & " all-fields importeret: " & CStr(CollectionCount(items)) & _
               " raekker og " & CStr(HeaderCount(headers)) & " kolonner." & vbCrLf & _
               WS_OBJECT_LIST & ": " & CStr(cntObjectList) & " raekker.", vbInformation + vbOKOnly
    End If
    Exit Sub
EH:
    Dim errText As String
    errText = "Import fejl (" & WS_MAINTENANCE_ITEMS & " all-fields) i stage '" & stage & "': " & _
              CStr(Err.Number) & " - " & Err.Description

    If showSummary Then
        MsgBox errText, vbCritical + vbOKOnly
    Else
        Err.Raise Err.Number, , errText
    End If
End Sub

Public Sub ImportSharePointMaintenanceTLH(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim cnt As Long
    cnt = ImportSharePointListToSheet( _
        GetSharePointTlhUrl(), _
        GetSharePointTlhFilter(), _
        WS_MAINTENANCE_TLH, _
        START_ROW_DEFAULT, _
        DefaultHeadersTlh(), _
        BuildAliasMapTlh(), _
        GetSharePointAuthHeader())

    ApplyMaintenanceTlhPostProcessing

    If showSummary Then MsgBox WS_MAINTENANCE_TLH & " importeret: " & CStr(cnt) & " raekker.", vbInformation + vbOKOnly
    Exit Sub
EH:
    MsgBox "Import fejl (" & WS_MAINTENANCE_TLH & "): " & Err.Description, vbCritical + vbOKOnly
End Sub

Public Sub ImportSharePointMaintenanceTL(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim cnt As Long
    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    cnt = ImportSharePointListToSheet( _
        GetSharePointTlUrl(), _
        GetSharePointTlFilter(), _
        WS_MAINTENANCE_TL, _
        START_ROW_TL, _
        DefaultHeadersTl(), _
        BuildAliasMapTl(), _
        authHeader)

    ApplyMaintenanceTlDisplayAndColors

    If showSummary Then MsgBox WS_MAINTENANCE_TL & " importeret: " & CStr(cnt) & " raekker.", vbInformation + vbOKOnly
    Exit Sub
EH:
    MsgBox "Import fejl (" & WS_MAINTENANCE_TL & "): " & Err.Description, vbCritical + vbOKOnly
End Sub

Public Sub ImportSharePointMaintenanceTLAllFields(Optional ByVal showSummary As Boolean = True)
    On Error GoTo EH

    Dim stage As String
    stage = "Fetch"

    Dim authHeader As String
    authHeader = GetSharePointAuthHeader()

    Dim tlClause As String
    tlClause = BuildAllFieldsClause(GetSharePointTlFilter())

    Dim items As Collection
    Set items = FetchSharePointItems( _
        GetSharePointTlUrl(), _
        tlClause, _
        authHeader)

    stage = "Headers"
    Dim headers As Variant
    headers = BuildAllFieldHeaders(items)

    stage = "Rows"
    Dim rows As Variant
    rows = BuildRowsFromItems(items, headers, Nothing)

    stage = "Write"
    WriteImportRows WS_MAINTENANCE_TL, START_ROW_TL, headers, rows

    stage = "MaintenanceTlPostProcessing"
    ApplyMaintenanceTlDisplayAndColors

    If showSummary Then
        MsgBox WS_MAINTENANCE_TL & " all-fields importeret: " & CStr(CollectionCount(items)) & _
               " raekker og " & CStr(HeaderCount(headers)) & " kolonner.", vbInformation + vbOKOnly
    End If
    Exit Sub
EH:
    Dim errText As String
    errText = "Import fejl (" & WS_MAINTENANCE_TL & " all-fields) i stage '" & stage & "': " & _
              CStr(Err.Number) & " - " & Err.Description

    If showSummary Then
        MsgBox errText, vbCritical + vbOKOnly
    Else
        Err.Raise Err.Number, , errText
    End If
End Sub

Private Function BuildAllFieldsClause(ByVal rawClause As String) As String
    Dim clause As String
    clause = Trim$(rawClause)

    If Len(clause) = 0 Then
        BuildAllFieldsClause = "$select=*,FieldValuesAsText&$expand=FieldValuesAsText"
        Exit Function
    End If

    If LCase$(Left$(clause, 1)) <> "$" Then
        clause = "$filter=" & clause
    End If

    BuildAllFieldsClause = clause & "&$select=*,FieldValuesAsText&$expand=FieldValuesAsText"
End Function

Private Function ImportSharePointListToSheet( _
    ByVal sourceUrl As String, _
    ByVal filterClause As String, _
    ByVal targetSheetName As String, _
    ByVal startRow As Long, _
    ByVal headers As Variant, _
    ByVal aliasMap As Object, _
    ByVal authHeader As String) As Long

    Dim items As Collection
    Set items = FetchSharePointItems(sourceUrl, filterClause, authHeader)

    Dim rows As Variant
    rows = BuildRowsFromItems(items, headers, aliasMap)

    WriteImportRows targetSheetName, startRow, headers, rows
    ImportSharePointListToSheet = CollectionCount(items)
End Function

Private Function FetchSharePointItems(ByVal sourceUrl As String, ByVal filterClause As String, ByVal authHeader As String) As Collection
    Dim resolvedUrl As String
    resolvedUrl = NormalizeSourceUrl(sourceUrl)

    If Len(resolvedUrl) = 0 Then
        Err.Raise 2001, , "SharePoint URL mangler."
    End If

    Dim nextUrl As String
    nextUrl = BuildInitialFetchUrl(resolvedUrl, filterClause)

    Dim allItems As New Collection

    Do While Len(nextUrl) > 0
        Dim root As Object
        Set root = HttpGetJson(nextUrl, authHeader)
        If root Is Nothing Then
            Err.Raise 2003, , "Tom JSON-respons fra: " & nextUrl
        End If

        Dim pageItems As Collection
        Set pageItems = ExtractItemsFromResponse(root)
        AppendCollection allItems, pageItems

        nextUrl = ResolveNextUrl(ExtractNextLink(root), nextUrl)
    Loop

    Set FetchSharePointItems = allItems
End Function

Private Function BuildRowsFromItems(ByVal items As Collection, ByVal headers As Variant, ByVal aliasMap As Object) As Variant
    Dim itemCount As Long
    itemCount = CollectionCount(items)

    If itemCount = 0 Then
        BuildRowsFromItems = Empty
        Exit Function
    End If

    Dim colCount As Long
    colCount = HeaderCount(headers)
    If colCount = 0 Then
        BuildRowsFromItems = Empty
        Exit Function
    End If

    Dim outRows() As Variant
    ReDim outRows(1 To itemCount, 1 To colCount)

    Dim r As Long
    For r = 1 To itemCount
        Dim itm As Object
        Set itm = Nothing
        If IsObject(items(r)) Then Set itm = items(r)

        Dim normalizedIndex As Object
        Set normalizedIndex = BuildNormalizedKeyIndex(itm)

        Dim c As Long
        For c = 1 To colCount
            Dim targetHeader As String
            targetHeader = CStr(headers(c - 1))

            If Len(Trim$(targetHeader)) = 0 Then
                outRows(r, c) = vbNullString
            Else
                Dim srcKey As String
                srcKey = ResolveSourceKey(targetHeader, aliasMap, normalizedIndex)

                If ShouldComposeTlLongText(targetHeader, aliasMap) Then
                    outRows(r, c) = ComposeTlLongTextValue(itm, aliasMap, normalizedIndex, srcKey)
                    GoTo NextColumn
                End If

                If Not itm Is Nothing Then
                    If Len(srcKey) > 0 Then
                        Dim rawValue As Variant
                        If TryGetItemValue(itm, srcKey, rawValue) Then
                            Dim coercedValue As Variant
                            coercedValue = CoerceSharePointValue(rawValue)
                            coercedValue = ApplyPm02VendorIdFallback(targetHeader, itm, aliasMap, normalizedIndex, coercedValue)
                            outRows(r, c) = TransformImportedFieldValue(targetHeader, coercedValue)
                        Else
                            outRows(r, c) = vbNullString
                        End If
                    Else
                        outRows(r, c) = vbNullString
                    End If
                Else
                    outRows(r, c) = vbNullString
                End If
            End If
NextColumn:
        Next c
    Next r

    BuildRowsFromItems = outRows
End Function

Private Function ApplyPm02VendorIdFallback( _
    ByVal targetHeader As String, _
    ByVal item As Object, _
    ByVal aliasMap As Object, _
    ByVal normalizedIndex As Object, _
    ByVal fieldValue As Variant) As Variant

    ApplyPm02VendorIdFallback = fieldValue

    If NormalizeFieldName(targetHeader) <> "vendorid" Then Exit Function
    If item Is Nothing Then Exit Function
    If aliasMap Is Nothing Then Exit Function

    Dim ctrlValue As String
    ctrlValue = UCase$(Trim$(GetResolvedFieldText(item, "Ctrl", aliasMap, normalizedIndex)))
    If ctrlValue <> "PM02" Then Exit Function

    If Not IsZeroVendorIdValue(fieldValue) Then Exit Function

    Dim vendorValue As String
    Dim vendorIdFromVendor As String
    vendorValue = GetResolvedFieldText(item, "Vendor", aliasMap, normalizedIndex)
    vendorIdFromVendor = ExtractVendorIdFromVendorText(vendorValue)

    If Len(vendorIdFromVendor) > 0 Then
        ApplyPm02VendorIdFallback = vendorIdFromVendor
    End If
End Function

Private Function IsZeroVendorIdValue(ByVal valueToCheck As Variant) As Boolean
    If IsNull(valueToCheck) Or IsEmpty(valueToCheck) Then Exit Function

    Dim s As String
    s = Trim$(CStr(valueToCheck))
    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    Select Case s
        Case "0", "0.0", "0,0"
            IsZeroVendorIdValue = True
    End Select
End Function

Private Function ExtractVendorIdFromVendorText(ByVal vendorText As String) As String
    Dim s As String
    Dim separatorPos As Long

    s = Trim$(vendorText)
    If Len(s) = 0 Then Exit Function

    separatorPos = InStr(1, s, " - ", vbTextCompare)
    If separatorPos > 0 Then
        s = Left$(s, separatorPos - 1)
    End If

    s = Trim$(s)
    If Left$(s, 1) = "'" Then s = Mid$(s, 2)

    ExtractVendorIdFromVendorText = Trim$(s)
End Function

Private Function ShouldComposeTlLongText(ByVal targetHeader As String, ByVal aliasMap As Object) As Boolean
    If aliasMap Is Nothing Then Exit Function
    If Not aliasMap.Exists("OperationShortText") Then Exit Function
    If Not aliasMap.Exists("LongText") Then Exit Function

    ShouldComposeTlLongText = (NormalizeFieldName(targetHeader) = "longtext")
End Function

Private Function ComposeTlLongTextValue(ByVal item As Object, ByVal aliasMap As Object, ByVal normalizedIndex As Object, ByVal longTextSourceKey As String) As String
    If item Is Nothing Then Exit Function

    Dim operationShortText As String
    operationShortText = GetResolvedFieldText(item, "OperationShortText", aliasMap, normalizedIndex)

    Dim longTextRaw As Variant
    Dim rawLongText As String
    If Len(longTextSourceKey) = 0 Then
        longTextSourceKey = ResolveSourceKey("LongText", aliasMap, normalizedIndex)
    End If

    If Len(longTextSourceKey) = 0 Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    Dim convertedLongText As String
    If Not TryGetItemValue(item, longTextSourceKey, longTextRaw) Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    rawLongText = CStr(CoerceSharePointValue(longTextRaw))
    If Len(NormalizeTlCompareText(rawLongText)) = 0 Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    convertedLongText = CStr(TransformImportedFieldValue("LongText", rawLongText))
    If Len(NormalizeTlCompareText(convertedLongText)) = 0 Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    ' If short text and long text are the same, keep LongText cell empty.
    If AreTlTextsEqual(operationShortText, rawLongText) Or _
       AreTlTextsEqual(operationShortText, convertedLongText) Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    operationShortText = Replace(operationShortText, vbCrLf, vbLf)
    operationShortText = Replace(operationShortText, vbCr, vbLf)
    convertedLongText = TrimEdgeLineBreaks(NormalizeCellLineBreaks(convertedLongText))
    convertedLongText = RemoveTlOperationPrefix(operationShortText, convertedLongText)

    If Len(NormalizeTlCompareText(convertedLongText)) = 0 Then
        ComposeTlLongTextValue = vbNullString
        Exit Function
    End If

    If Len(operationShortText) > 0 Then
        ComposeTlLongTextValue = operationShortText & vbLf & vbLf & convertedLongText
    Else
        ComposeTlLongTextValue = convertedLongText
    End If
End Function

Private Function AreTlTextsEqual(ByVal leftText As String, ByVal rightText As String) As Boolean
    Dim leftNorm As String
    Dim rightNorm As String

    leftNorm = NormalizeTlCompareText(leftText)
    rightNorm = NormalizeTlCompareText(rightText)

    If Len(leftNorm) = 0 Or Len(rightNorm) = 0 Then Exit Function

    AreTlTextsEqual = (StrComp(leftNorm, rightNorm, vbTextCompare) = 0)
End Function

Private Function NormalizeTlCompareText(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    s = Replace(s, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)
    s = Replace(s, Chr$(160), " ")
    s = TrimEdgeLineBreaks(s)

    NormalizeTlCompareText = Trim$(s)
End Function

Private Function RemoveTlOperationPrefix(ByVal operationShortText As String, ByVal longTextValue As String) As String
    Dim opNorm As String
    Dim longNorm As String

    opNorm = NormalizeTlCompareText(operationShortText)
    longNorm = NormalizeTlCompareText(longTextValue)

    If Len(longNorm) = 0 Then
        RemoveTlOperationPrefix = vbNullString
        Exit Function
    End If

    If Len(opNorm) = 0 Then
        RemoveTlOperationPrefix = longNorm
        Exit Function
    End If

    If Len(longNorm) >= Len(opNorm) Then
        If StrComp(Left$(longNorm, Len(opNorm)), opNorm, vbTextCompare) = 0 Then
            longNorm = Mid$(longNorm, Len(opNorm) + 1)
            longNorm = TrimLeadingWhitespaceAndLineBreaks(longNorm)
        End If
    End If

    RemoveTlOperationPrefix = TrimEdgeLineBreaks(longNorm)
End Function

Private Function TrimLeadingWhitespaceAndLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    Do While Len(s) > 0
        Select Case Left$(s, 1)
            Case " ", vbTab, vbLf, vbCr
                s = Mid$(s, 2)
            Case Else
                Exit Do
        End Select
    Loop

    TrimLeadingWhitespaceAndLineBreaks = s
End Function

Private Function GetResolvedFieldText(ByVal item As Object, ByVal targetHeader As String, ByVal aliasMap As Object, ByVal normalizedIndex As Object) As String
    If item Is Nothing Then Exit Function

    Dim sourceKey As String
    sourceKey = ResolveSourceKey(targetHeader, aliasMap, normalizedIndex)
    If Len(sourceKey) = 0 Then Exit Function

    Dim rawValue As Variant
    If Not TryGetItemValue(item, sourceKey, rawValue) Then Exit Function

    If IsNull(rawValue) Or IsEmpty(rawValue) Then Exit Function
    GetResolvedFieldText = CStr(CoerceSharePointValue(rawValue))
End Function

Private Function TransformImportedFieldValue(ByVal targetHeader As String, ByVal fieldValue As Variant) As Variant
    If IsNull(fieldValue) Or IsEmpty(fieldValue) Then
        TransformImportedFieldValue = fieldValue
        Exit Function
    End If

    If ShouldNormalizeObjectListLineBreaks(targetHeader) Then
        If VarType(fieldValue) = vbString Then
            TransformImportedFieldValue = NormalizeObjectListLineBreaks(CStr(fieldValue))
            Exit Function
        End If
    End If

    If ShouldFormatAsPlannedDate(targetHeader) Then
        TransformImportedFieldValue = FormatPlannedDateValue(fieldValue)
        Exit Function
    End If

    If ShouldForceTextField(targetHeader) Then
        Dim textValue As String
        textValue = CStr(fieldValue)
        If Left$(textValue, 1) = "'" Then
            TransformImportedFieldValue = textValue
        Else
            TransformImportedFieldValue = "'" & textValue
        End If
        Exit Function
    End If

    If ShouldConvertHtmlToText(targetHeader) Then
        If VarType(fieldValue) = vbString Then
            Dim convertedText As String
            convertedText = ConvertHtmlToPlainText(CStr(fieldValue))

            If IsItemDescriptionField(targetHeader) Or IsLongTextField(targetHeader) Then
                convertedText = NormalizeRichTextLineBreaks(convertedText)
            End If

            If IsItemDescriptionField(targetHeader) Then
                convertedText = ApplyDefaultItemDescriptionStyles(convertedText)
            End If

            If ShouldForceLeadingLineBreak(targetHeader) Then
                convertedText = EnsureLeadingLineBreak(convertedText)
            End If

            TransformImportedFieldValue = convertedText
            Exit Function
        End If
    End If

    If ShouldForceLeadingLineBreak(targetHeader) Then
        If VarType(fieldValue) = vbString Then
            Dim fallbackText As String
            fallbackText = CStr(fieldValue)

            If IsItemDescriptionField(targetHeader) Then
                fallbackText = NormalizeRichTextLineBreaks(fallbackText)
            End If

            TransformImportedFieldValue = EnsureLeadingLineBreak(fallbackText)
            Exit Function
        End If
    End If

    If IsLongTextField(targetHeader) Then
        If VarType(fieldValue) = vbString Then
            TransformImportedFieldValue = NormalizeRichTextLineBreaks(CStr(fieldValue))
            Exit Function
        End If
    End If

    TransformImportedFieldValue = fieldValue
End Function

Private Function IsItemDescriptionField(ByVal targetHeader As String) As Boolean
    Dim normalized As String
    normalized = NormalizeFieldName(targetHeader)

    IsItemDescriptionField = (normalized = "itemdescription" Or normalized = "fieldvaluesastextitemdescription")
End Function

Private Function IsLongTextField(ByVal targetHeader As String) As Boolean
    Dim normalized As String
    normalized = NormalizeFieldName(targetHeader)

    IsLongTextField = (normalized = "longtext" Or normalized = "fieldvaluesastextlongtext")
End Function

Private Function NormalizeRichTextLineBreaks(ByVal textValue As String) As String
    NormalizeRichTextLineBreaks = NormalizeItemDescriptionLineBreaks(textValue)
End Function

Private Function NormalizeItemDescriptionLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = Replace(textValue, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)

    If CountLineFeeds(s) <= 1 Then
        s = RegexReplaceText(s, "\.\s*([A-ZÆØÅ])", "." & vbLf & vbLf & "$1")
        s = RegexReplaceText(s, "\.\s*([0-9]+\))", "." & vbLf & vbLf & "$1")
        s = Replace(s, ":*", ":" & vbLf & "- ")

        If InStr(1, s, "*", vbBinaryCompare) > 0 Then
            s = Replace(s, "*", vbLf & "- ")
        End If
    End If

    s = NormalizeItemDescriptionSections(s)

    NormalizeItemDescriptionLineBreaks = NormalizeCellLineBreaks(s)
End Function

Private Function ApplyDefaultItemDescriptionStyles(ByVal textValue As String) As String
    Dim s As String
    s = Replace(textValue, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)

    If InStr(1, s, "<H>", vbBinaryCompare) > 0 Then
        ApplyDefaultItemDescriptionStyles = s
        Exit Function
    End If

    If InStr(1, s, "<U>", vbBinaryCompare) > 0 Then
        ApplyDefaultItemDescriptionStyles = s
        Exit Function
    End If

    Dim lines() As String
    lines = Split(s, vbLf)

    Dim firstIdx As Long
    Dim secondIdx As Long
    firstIdx = -1
    secondIdx = -1

    Dim i As Long
    For i = LBound(lines) To UBound(lines)
        If Len(Trim$(CStr(lines(i)))) > 0 Then
            If firstIdx = -1 Then
                firstIdx = i
            Else
                secondIdx = i
                Exit For
            End If
        End If
    Next i

    If firstIdx = -1 Then
        ApplyDefaultItemDescriptionStyles = s
        Exit Function
    End If

    Dim firstLine As String
    Dim secondLine As String
    firstLine = Trim$(CStr(lines(firstIdx)))
    If secondIdx <> -1 Then secondLine = Trim$(CStr(lines(secondIdx)))

    If ShouldPromoteItemDescriptionTitle(firstLine, secondLine) Then
        lines(firstIdx) = "<H>" & firstLine & "</>"
        ApplyDefaultItemDescriptionStyles = Join(lines, vbLf)
    Else
        ApplyDefaultItemDescriptionStyles = s
    End If
End Function

Private Function ShouldPromoteItemDescriptionTitle(ByVal firstLine As String, ByVal secondLine As String) As Boolean
    firstLine = Trim$(firstLine)
    secondLine = Trim$(secondLine)

    If Len(firstLine) < 12 Or Len(firstLine) > 180 Then Exit Function
    If IsBulletLine(firstLine) Or IsNumberedLine(firstLine) Then Exit Function
    If Right$(firstLine, 1) = ":" Then Exit Function

    If Len(secondLine) = 0 Then Exit Function

    Dim colonPos As Long
    colonPos = InStr(1, secondLine, ":", vbBinaryCompare)
    If colonPos = 0 Then Exit Function
    If colonPos < 4 Or colonPos > 60 Then Exit Function

    ShouldPromoteItemDescriptionTitle = True
End Function

Private Function NormalizeItemDescriptionSections(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    ' Repair glued words that lost separators during plain-text flattening.
    s = RegexReplaceText(s, "([a-zæøå])([A-ZÆØÅ])", "$1 $2")

    ' Create paragraph boundaries for numbered blocks and heading-like labels.
    s = RegexReplaceText(s, "([\.!\?])\s*([0-9]+[\)\.])", "$1" & vbLf & vbLf & "$2")
    s = RegexReplaceText(s, "([a-zæøå0-9\)])([A-ZÆØÅ][^:\n]{2,40}:)", "$1" & vbLf & vbLf & "$2")
    s = RegexReplaceText(s, "([\.!\?])\s*([A-ZÆØÅ][^:\n]{2,40}:)", "$1" & vbLf & vbLf & "$2")

    ' Convert lightweight rich-text markers to list lines.
    s = RegexReplaceText(s, ":\s*\*", ":" & vbLf & "- ")
    s = Replace(s, "*", vbLf & "- ")

    ' Put asset-like identifiers on separate lines.
    s = RegexReplaceText(s, "\s+([A-Z]{2,}[0-9]{2}\s+[A-Z0-9]{5,})", vbLf & "$1")
    s = RegexReplaceText(s, "([0-9])([A-Z]{2,}[0-9]{2}\s+[A-Z0-9]{5,})", "$1" & vbLf & "$2")

    NormalizeItemDescriptionSections = ApplyGenericListLayout(s)
End Function

Private Function ApplyGenericListLayout(ByVal textValue As String) As String
    Dim src() As String
    src = Split(textValue, vbLf)

    Dim out As String
    Dim i As Long
    Dim prevHeading As Boolean
    Dim prevBulletHeading As Boolean

    For i = LBound(src) To UBound(src)
        Dim t As String
        t = Trim$(CStr(src(i)))

        If Len(t) = 0 Then
            If Len(out) = 0 Then GoTo NextLine
            If Right$(out, 1) <> vbLf Then out = out & vbLf
            out = out & vbLf
            prevHeading = False
            prevBulletHeading = False
            GoTo NextLine
        End If

        If IsLikelyHeadingLine(t) Then
            If Len(out) > 0 And Right$(out, 2) <> vbLf & vbLf Then out = out & vbLf
            out = out & t & vbLf
            prevHeading = True
            prevBulletHeading = False
            GoTo NextLine
        End If

        If IsNumberedLine(t) Then
            out = out & t & vbLf
            prevHeading = False
            prevBulletHeading = False
            GoTo NextLine
        End If

        If IsBulletLine(t) Then
            out = out & t & vbLf
            prevHeading = False
            prevBulletHeading = EndsWithColon(t)
            GoTo NextLine
        End If

        If prevBulletHeading Then
            out = out & "  - " & t & vbLf
        ElseIf prevHeading And Not LooksLikeSentence(t) Then
            out = out & "- " & t & vbLf
        Else
            out = out & t & vbLf
        End If

        prevHeading = False
        prevBulletHeading = False
NextLine:
    Next i

    ApplyGenericListLayout = TrimTrailingLineFeeds(out)
End Function

Private Function IsLikelyHeadingLine(ByVal lineText As String) As Boolean
    Dim t As String
    t = Trim$(lineText)

    If Len(t) = 0 Then Exit Function
    If Len(t) > 60 Then Exit Function
    If Right$(t, 1) <> ":" Then Exit Function
    If IsBulletLine(t) Then Exit Function
    If IsNumberedLine(t) Then Exit Function

    IsLikelyHeadingLine = True
End Function

Private Function IsBulletLine(ByVal lineText As String) As Boolean
    Dim t As String
    t = Trim$(lineText)

    IsBulletLine = (Left$(t, 2) = "- " Or Left$(t, 2) = "* " Or Left$(t, 3) = "• ")
End Function

Private Function IsNumberedLine(ByVal lineText As String) As Boolean
    IsNumberedLine = (RegexReplaceText(Trim$(lineText), "^([0-9]+[\)\.]).*$", "$1") <> Trim$(lineText) Or _
                      RegexIsMatch(Trim$(lineText), "^[0-9]+[\)\.]\s+"))
End Function

Private Function EndsWithColon(ByVal lineText As String) As Boolean
    EndsWithColon = (Right$(Trim$(lineText), 1) = ":")
End Function

Private Function LooksLikeSentence(ByVal lineText As String) As Boolean
    Dim t As String
    t = Trim$(lineText)

    LooksLikeSentence = (InStr(1, t, ".", vbBinaryCompare) > 0 Or _
                         InStr(1, t, ",", vbBinaryCompare) > 0 Or _
                         InStr(1, t, ";", vbBinaryCompare) > 0 Or _
                         Len(t) > 90)
End Function

Private Function TrimTrailingLineFeeds(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    Do While Len(s) > 0
        If Right$(s, 1) = vbLf Or Right$(s, 1) = vbCr Then
            s = Left$(s, Len(s) - 1)
        Else
            Exit Do
        End If
    Loop

    TrimTrailingLineFeeds = s
End Function

Private Function RegexIsMatch(ByVal inputText As String, ByVal pattern As String) As Boolean
    On Error GoTo NoMatch

    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Global = False
    re.IgnoreCase = False
    re.MultiLine = True
    re.Pattern = pattern

    RegexIsMatch = re.Test(inputText)
    Exit Function

NoMatch:
    RegexIsMatch = False
End Function

Private Function CountLineFeeds(ByVal textValue As String) As Long
    If Len(textValue) = 0 Then Exit Function
    CountLineFeeds = Len(textValue) - Len(Replace(textValue, vbLf, vbNullString))
End Function

Private Function RegexReplaceText(ByVal inputText As String, ByVal pattern As String, ByVal replacement As String) As String
    On Error GoTo UseInput

    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Global = True
    re.IgnoreCase = False
    re.MultiLine = True
    re.Pattern = pattern

    RegexReplaceText = re.Replace(inputText, replacement)
    Exit Function

UseInput:
    RegexReplaceText = inputText
End Function

Private Function RegexReplaceTextIgnoreCase(ByVal inputText As String, ByVal pattern As String, ByVal replacement As String) As String
    On Error GoTo UseInput

    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")
    re.Global = True
    re.IgnoreCase = True
    re.MultiLine = True
    re.Pattern = pattern

    RegexReplaceTextIgnoreCase = re.Replace(inputText, replacement)
    Exit Function

UseInput:
    RegexReplaceTextIgnoreCase = inputText
End Function

Private Function ShouldNormalizeObjectListLineBreaks(ByVal targetHeader As String) As Boolean
    Dim normalized As String
    normalized = NormalizeFieldName(targetHeader)

    ShouldNormalizeObjectListLineBreaks = (normalized = "objectlist" Or normalized = "fieldvaluesastextobjectlist")
End Function

Private Function NormalizeObjectListLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = Replace(textValue, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)
    s = Replace(s, "|||", vbLf)

    NormalizeObjectListLineBreaks = NormalizeCellLineBreaks(s)
End Function

Private Function ShouldForceTextField(ByVal targetHeader As String) As Boolean
    Dim normalized As String
    normalized = NormalizeFieldName(targetHeader)

    Select Case normalized
        Case "id", "sortfieldid", "vendorid"
            ShouldForceTextField = True
    End Select
End Function

Private Function ShouldFormatAsPlannedDate(ByVal targetHeader As String) As Boolean
    ShouldFormatAsPlannedDate = (NormalizeFieldName(targetHeader) = "planneddate")
End Function

Private Function FormatPlannedDateValue(ByVal fieldValue As Variant) As Variant
    Dim parsedDate As Date
    If TryExtractDateValue(fieldValue, parsedDate) Then
        FormatPlannedDateValue = Format$(parsedDate, "dd.mm.yyyy")
    Else
        FormatPlannedDateValue = fieldValue
    End If
End Function

Private Function TryExtractDateValue(ByVal valueToParse As Variant, ByRef outDate As Date) As Boolean
    On Error GoTo Fail

    If IsDate(valueToParse) Then
        outDate = CDate(valueToParse)
        TryExtractDateValue = True
        Exit Function
    End If

    If VarType(valueToParse) = vbString Then
        Dim s As String
        s = Trim$(CStr(valueToParse))
        If Len(s) = 0 Then Exit Function

        If Left$(s, 6) = "/Date(" Then
            Dim parsed As Variant
            parsed = ParseODataDate(s)
            If IsDate(parsed) Then
                outDate = CDate(parsed)
                TryExtractDateValue = True
                Exit Function
            End If
        End If

        If TryParseIsoDateTime(s, outDate) Then
            TryExtractDateValue = True
            Exit Function
        End If

        If IsDate(s) Then
            outDate = CDate(s)
            TryExtractDateValue = True
            Exit Function
        End If
    End If

    Exit Function
Fail:
    TryExtractDateValue = False
End Function

Private Function ShouldForceLeadingLineBreak(ByVal targetHeader As String) As Boolean
    ShouldForceLeadingLineBreak = (NormalizeFieldName(targetHeader) = "itemdescription")
End Function

Private Function EnsureLeadingLineBreak(ByVal textValue As String) As String
    Dim s As String
    s = Replace(textValue, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)

    If Len(s) = 0 Then
        EnsureLeadingLineBreak = vbNullString
        Exit Function
    End If

    Do While Len(s) > 0
        If Left$(s, 1) = vbLf Then
            s = Mid$(s, 2)
        Else
            Exit Do
        End If
    Loop

    EnsureLeadingLineBreak = vbLf & s
End Function

Private Function ShouldConvertHtmlToText(ByVal targetHeader As String) As Boolean
    Dim normalized As String
    normalized = NormalizeFieldName(targetHeader)

    Select Case normalized
        Case "itemdescription", "fieldvaluesastextitemdescription", "item_description", _
             "longtext", "fieldvaluesastextlongtext", "long_text"
            ShouldConvertHtmlToText = True
    End Select
End Function

Private Function ConvertHtmlToPlainText(ByVal htmlText As String) As String
    Dim raw As String
    raw = Trim$(htmlText)

    If Len(raw) = 0 Then
        ConvertHtmlToPlainText = vbNullString
        Exit Function
    End If

    Dim decodedHtml As String
    decodedHtml = DecodeBasicHtmlEntities(raw)

    If InStr(1, raw, "<", vbBinaryCompare) = 0 Or InStr(1, raw, ">", vbBinaryCompare) = 0 Then
        If InStr(1, decodedHtml, "<", vbBinaryCompare) = 0 Or InStr(1, decodedHtml, ">", vbBinaryCompare) = 0 Then
            ConvertHtmlToPlainText = NormalizeCellLineBreaks(decodedHtml)
            Exit Function
        End If
        raw = decodedHtml
    End If

    On Error GoTo Fallback

    Dim doc As Object
    Set doc = CreateObject("htmlfile")
    doc.Open
    doc.Write "<html><body></body></html>"
    doc.Close
    doc.body.innerHTML = raw

    Dim rendered As String
    rendered = RenderHtmlNode(doc.body, 0)

    ConvertHtmlToPlainText = TrimEdgeLineBreaks(NormalizeCellLineBreaks(rendered))
    Exit Function

Fallback:
    ConvertHtmlToPlainText = TrimEdgeLineBreaks(NormalizeCellLineBreaks(StripHtmlTagsFallback(raw)))
End Function

Private Function RenderHtmlNode(ByVal node As Object, ByVal listLevel As Long) As String
    On Error GoTo SafeExit

    If node Is Nothing Then Exit Function

    Dim nodeType As Long
    nodeType = CLng(node.nodeType)

    Select Case nodeType
        Case 3 ' Text node
            RenderHtmlNode = DecodeHtmlTextValue(CStr(node.nodeValue))
            Exit Function

        Case 1 ' Element node
            Dim tagName As String
            tagName = LCase$(CStr(node.tagName))

            Dim content As String
            Select Case tagName
                Case "br"
                    RenderHtmlNode = vbLf

                Case "p", "div", "section", "article"
                    content = TrimEdgeLineBreaks(RenderHtmlChildren(node, listLevel))
                    If Len(content) > 0 Then
                        RenderHtmlNode = content & vbLf & vbLf
                    Else
                        RenderHtmlNode = vbLf
                    End If

                Case "ul"
                    RenderHtmlNode = RenderHtmlList(node, listLevel, False) & vbLf

                Case "ol"
                    RenderHtmlNode = RenderHtmlList(node, listLevel, True) & vbLf

                Case "li"
                    content = TrimEdgeLineBreaks(RenderHtmlChildren(node, listLevel + 1))
                    If Len(content) > 0 Then
                        Dim bulletPrefix As String
                        bulletPrefix = String$(listLevel * 2, " ") & "- "
                        RenderHtmlNode = bulletPrefix & IndentWrappedLines(content, Len(bulletPrefix)) & vbLf
                    End If

                Case "strong", "b"
                    content = TrimEdgeLineBreaks(RenderHtmlChildren(node, listLevel))
                    If Len(content) > 0 Then
                        RenderHtmlNode = "<H>" & content & "</>"
                    End If

                Case "u"
                    content = TrimEdgeLineBreaks(RenderHtmlChildren(node, listLevel))
                    If Len(content) > 0 Then
                        RenderHtmlNode = "<U>" & content & "</>"
                    End If

                Case "em", "i"
                    content = TrimEdgeLineBreaks(RenderHtmlChildren(node, listLevel))
                    If Len(content) > 0 Then
                        RenderHtmlNode = "_" & content & "_"
                    End If

                Case Else
                    content = RenderHtmlChildren(node, listLevel)
                    If Len(content) > 0 Then
                        Dim markerPrefix As String
                        Dim markerSuffix As String

                        If NodeHasBoldStyle(node) Then
                            markerPrefix = markerPrefix & "<H>"
                            markerSuffix = "</>" & markerSuffix
                        End If

                        If NodeHasUnderlineStyle(node) Then
                            markerPrefix = markerPrefix & "<U>"
                            markerSuffix = "</>" & markerSuffix
                        End If

                        content = markerPrefix & content & markerSuffix
                    End If
                    RenderHtmlNode = content
            End Select
    End Select

SafeExit:
End Function

Private Function RenderHtmlChildren(ByVal node As Object, ByVal listLevel As Long) As String
    On Error GoTo Done

    If node Is Nothing Then Exit Function

    Dim child As Object
    Dim out As String

    For Each child In node.childNodes
        out = out & RenderHtmlNode(child, listLevel)
    Next child

    RenderHtmlChildren = out
Done:
End Function

Private Function RenderHtmlList(ByVal listNode As Object, ByVal listLevel As Long, ByVal ordered As Boolean) As String
    On Error GoTo Done

    If listNode Is Nothing Then Exit Function

    Dim out As String
    Dim index As Long
    index = 1

    Dim child As Object
    For Each child In listNode.childNodes
        If IsElementTag(child, "li") Then
            Dim itemText As String
            itemText = TrimEdgeLineBreaks(RenderHtmlChildren(child, listLevel + 1))

            If Len(itemText) > 0 Then
                Dim prefix As String
                prefix = String$(listLevel * 2, " ")
                If ordered Then
                    prefix = prefix & CStr(index) & ". "
                Else
                    prefix = prefix & "- "
                End If

                out = out & prefix & IndentWrappedLines(itemText, Len(prefix)) & vbLf
                index = index + 1
            End If
        End If
    Next child

    RenderHtmlList = out
Done:
End Function

Private Function IsElementTag(ByVal node As Object, ByVal tagName As String) As Boolean
    On Error GoTo Fail

    If node Is Nothing Then Exit Function
    If CLng(node.nodeType) <> 1 Then Exit Function

    IsElementTag = (StrComp(LCase$(CStr(node.tagName)), LCase$(tagName), vbBinaryCompare) = 0)
    Exit Function
Fail:
End Function

Private Function NodeHasBoldStyle(ByVal node As Object) As Boolean
    Dim styleText As String
    styleText = NormalizeCssText(GetNodeAttributeText(node, "style"))

    If Len(styleText) = 0 Then Exit Function

    NodeHasBoldStyle = (InStr(1, styleText, "font-weight:bold", vbBinaryCompare) > 0 Or _
                        InStr(1, styleText, "font-weight:bolder", vbBinaryCompare) > 0 Or _
                        InStr(1, styleText, "font-weight:700", vbBinaryCompare) > 0 Or _
                        InStr(1, styleText, "font-weight:800", vbBinaryCompare) > 0 Or _
                        InStr(1, styleText, "font-weight:900", vbBinaryCompare) > 0)
End Function

Private Function NodeHasUnderlineStyle(ByVal node As Object) As Boolean
    Dim styleText As String
    styleText = NormalizeCssText(GetNodeAttributeText(node, "style"))

    If Len(styleText) = 0 Then Exit Function

    NodeHasUnderlineStyle = (InStr(1, styleText, "text-decoration:underline", vbBinaryCompare) > 0 Or _
                             InStr(1, styleText, "text-decoration-line:underline", vbBinaryCompare) > 0)
End Function

Private Function GetNodeAttributeText(ByVal node As Object, ByVal attributeName As String) As String
    On Error GoTo SafeExit

    If node Is Nothing Then Exit Function

    Dim attrValue As Variant
    attrValue = node.getAttribute(attributeName)

    If IsNull(attrValue) Or IsEmpty(attrValue) Then Exit Function

    GetNodeAttributeText = CStr(attrValue)
    Exit Function

SafeExit:
End Function

Private Function NormalizeCssText(ByVal cssText As String) As String
    Dim s As String
    s = LCase$(cssText)

    s = Replace(s, vbTab, vbNullString)
    s = Replace(s, " ", vbNullString)
    s = Replace(s, vbCr, vbNullString)
    s = Replace(s, vbLf, vbNullString)

    NormalizeCssText = s
End Function

Private Function IndentWrappedLines(ByVal textValue As String, ByVal indentCount As Long) As String
    If indentCount <= 0 Then
        IndentWrappedLines = textValue
        Exit Function
    End If

    Dim indentText As String
    indentText = String$(indentCount, " ")
    IndentWrappedLines = Replace(textValue, vbLf, vbLf & indentText)
End Function

Private Function TrimEdgeLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    Do While Len(s) > 0
        If Left$(s, 1) = vbLf Or Left$(s, 1) = vbCr Then
            s = Mid$(s, 2)
        Else
            Exit Do
        End If
    Loop

    Do While Len(s) > 0
        If Right$(s, 1) = vbLf Or Right$(s, 1) = vbCr Then
            s = Left$(s, Len(s) - 1)
        Else
            Exit Do
        End If
    Loop

    TrimEdgeLineBreaks = Trim$(s)
End Function

Private Function DecodeHtmlTextValue(ByVal textValue As String) As String
    Dim s As String
    s = textValue
    s = Replace(s, Chr$(160), " ")
    DecodeHtmlTextValue = s
End Function

Private Function DecodeBasicHtmlEntities(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    s = Replace(s, "&nbsp;", " ")
    s = Replace(s, "&#160;", " ")
    s = Replace(s, "&lt;", "<")
    s = Replace(s, "&gt;", ">")
    s = Replace(s, "&amp;", "&")

    DecodeBasicHtmlEntities = s
End Function

Private Function StripHtmlTagsFallback(ByVal htmlText As String) As String
    Dim txt As String
    txt = DecodeBasicHtmlEntities(htmlText)

    ' Preserve style markers while stripping generic HTML tags.
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*(strong|b)\b[^>]*>", "__H_OPEN__")
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*(strong|b)\s*>", "__H_CLOSE__")
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*u\b[^>]*>", "__U_OPEN__")
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*u\s*>", "__U_CLOSE__")
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*(em|i)\b[^>]*>", "__I_OPEN__")
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*(em|i)\s*>", "__I_CLOSE__")

    txt = RegexReplaceTextIgnoreCase(txt, "<\s*br\s*/?\s*>", vbLf)
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*p\s*>", vbLf)
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*div\s*>", vbLf)
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*/\s*li\s*>", vbLf)
    txt = RegexReplaceTextIgnoreCase(txt, "<\s*li\b[^>]*>", vbLf & "- ")

    Dim i As Long
    Dim ch As String
    Dim inTag As Boolean
    Dim out As String

    For i = 1 To Len(txt)
        ch = Mid$(txt, i, 1)
        If ch = "<" Then
            inTag = True
        ElseIf ch = ">" Then
            inTag = False
        ElseIf Not inTag Then
            out = out & ch
        End If
    Next i

    out = DecodeBasicHtmlEntities(out)

    out = Replace(out, "__H_OPEN__", "<H>")
    out = Replace(out, "__H_CLOSE__", "</>")
    out = Replace(out, "__U_OPEN__", "<U>")
    out = Replace(out, "__U_CLOSE__", "</>")
    out = Replace(out, "__I_OPEN__", "_")
    out = Replace(out, "__I_CLOSE__", "_")

    StripHtmlTagsFallback = out
End Function

Private Function NormalizeCellLineBreaks(ByVal textValue As String) As String
    Dim s As String
    s = textValue

    s = Replace(s, vbCrLf, vbLf)
    s = Replace(s, vbCr, vbLf)
    s = Replace(s, Chr$(160), " ")
    s = CollapseRepeatedSpacesByLine(s)

    Do While InStr(1, s, vbLf & vbLf & vbLf, vbBinaryCompare) > 0
        s = Replace(s, vbLf & vbLf & vbLf, vbLf & vbLf)
    Loop

    NormalizeCellLineBreaks = s
End Function

Private Function CollapseRepeatedSpacesByLine(ByVal textValue As String) As String
    If Len(textValue) = 0 Then
        CollapseRepeatedSpacesByLine = vbNullString
        Exit Function
    End If

    Dim lines() As String
    lines = Split(textValue, vbLf)

    Dim i As Long
    For i = LBound(lines) To UBound(lines)
        lines(i) = CollapseRepeatedSpacesInLine(CStr(lines(i)))
    Next i

    CollapseRepeatedSpacesByLine = Join(lines, vbLf)
End Function

Private Function CollapseRepeatedSpacesInLine(ByVal lineText As String) As String
    If Len(lineText) = 0 Then
        CollapseRepeatedSpacesInLine = vbNullString
        Exit Function
    End If

    Dim p As Long
    p = 1
    Do While p <= Len(lineText)
        If Mid$(lineText, p, 1) <> " " Then Exit Do
        p = p + 1
    Loop

    If p > Len(lineText) Then
        CollapseRepeatedSpacesInLine = lineText
        Exit Function
    End If

    Dim leading As String
    Dim body As String

    leading = Left$(lineText, p - 1)
    body = RTrim$(Mid$(lineText, p))

    Do While InStr(1, body, "  ", vbBinaryCompare) > 0
        body = Replace(body, "  ", " ")
    Loop

    CollapseRepeatedSpacesInLine = leading & body
End Function

Private Function BuildAllFieldHeaders(ByVal items As Collection) As Variant
    Dim seen As Object
    Set seen = CreateObject("Scripting.Dictionary")
    seen.CompareMode = vbTextCompare

    Dim ordered As New Collection

    Dim r As Long
    For r = 1 To CollectionCount(items)
        If IsObject(items(r)) Then
            If TypeName(items(r)) = "Dictionary" Then
                CollectHeadersFromDictionary items(r), vbNullString, ordered, seen
            End If
        End If
    Next r

    If ordered.Count = 0 Then
        BuildAllFieldHeaders = Empty
        Exit Function
    End If

    Dim out() As Variant
    ReDim out(0 To ordered.Count - 1)

    Dim i As Long
    For i = 1 To ordered.Count
        out(i - 1) = CStr(ordered(i))
    Next i

    BuildAllFieldHeaders = out
End Function

Private Sub CollectHeadersFromDictionary(ByVal dict As Object, ByVal prefix As String, ByVal ordered As Collection, ByVal seen As Object)
    If dict Is Nothing Then Exit Sub
    If TypeName(dict) <> "Dictionary" Then Exit Sub

    Dim k As Variant
    For Each k In dict.Keys
        Dim keyName As String
        keyName = CStr(k)

        If Left$(keyName, 2) <> "__" Then
            Dim fullKey As String
            If Len(prefix) > 0 Then
                fullKey = prefix & "/" & keyName
            Else
                fullKey = keyName
            End If

            If IsObject(dict(k)) Then
                Dim childObj As Object
                Set childObj = dict(k)

                If TypeName(childObj) = "Dictionary" Then
                    CollectHeadersFromDictionary childObj, fullKey, ordered, seen
                Else
                    AddHeaderUnique ordered, seen, fullKey
                End If
            Else
                AddHeaderUnique ordered, seen, fullKey
            End If
        End If
    Next k
End Sub

Private Sub AddHeaderUnique(ByVal ordered As Collection, ByVal seen As Object, ByVal headerName As String)
    Dim key As String
    key = Trim$(headerName)
    If Len(key) = 0 Then Exit Sub

    If Not seen.Exists(key) Then
        seen.Add key, True
        ordered.Add key
    End If
End Sub

Private Sub WriteImportRows(ByVal sheetName As String, ByVal startRow As Long, ByVal headers As Variant, ByVal rows As Variant)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = sheetName
    End If

    ' Hvert ark baerer, hvilket miljoe dets data kom fra. Stemplet saettes
    ' her, fordi alle importstier - baade standard og all-fields - skriver
    ' arket gennem denne ene procedure. Ogsaa naar der ingen raekker er:
    ' arket er ryddet, og det tomme resultat gaelder det valgte miljoe.
    modEnvironment.StampSheetEnvironment ws

    Dim colCount As Long
    colCount = HeaderCount(headers)

    ' Remove stale headers from earlier imports (e.g., all-fields mode).
    ws.Rows(1).ClearContents

    If colCount > 0 Then
        Dim headerRow() As Variant
        ReDim headerRow(1 To 1, 1 To colCount)

        Dim c As Long
        For c = 1 To colCount
            headerRow(1, c) = CStr(headers(c - 1))
        Next c

        ws.Range("A1").Resize(1, colCount).Value = headerRow
    End If

    ws.Range(ws.Rows(startRow), ws.Rows(ws.Rows.Count)).ClearContents

    If IsEmpty(rows) Then Exit Sub

    Dim rowCount As Long
    rowCount = SafeRowCount(rows)
    If rowCount <= 0 Then Exit Sub

    ws.Range("A" & CStr(startRow)).Resize(rowCount, colCount).Value = rows
End Sub

Private Sub ApplyMaintenancePlansPostProcessing(ByVal authHeader As String)
    On Error GoTo SafeExit

    ApplyMaintenancePlansSortFieldText authHeader
    SortMaintenancePlansByStatusDescending
    ApplyMaintenancePlansStatusColors
    ApplyMaintenancePlansSelectionDefaults

SafeExit:
End Sub

Private Sub SortMaintenancePlansByStatusDescending()
    On Error GoTo SafeExit

    Dim ws As Worksheet
    Set ws = Nothing
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    Const STATUS_COL As Long = 3

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim statusLastRow As Long
    statusLastRow = ws.Cells(ws.Rows.Count, STATUS_COL).End(xlUp).Row
    If statusLastRow > lastRow Then lastRow = statusLastRow

    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim lastCol As Long
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If lastCol < STATUS_COL Then Exit Sub

    Dim sortRange As Range
    Set sortRange = ws.Range(ws.Cells(START_ROW_DEFAULT, 1), ws.Cells(lastRow, lastCol))

    sortRange.Sort Key1:=ws.Cells(START_ROW_DEFAULT, STATUS_COL), _
                   Order1:=xlDescending, _
                   Header:=xlNo, _
                   Orientation:=xlTopToBottom, _
                   MatchCase:=False

SafeExit:
End Sub

Private Sub ApplyMaintenancePlansSelectionDefaults()
    On Error GoTo SafeExit

    Dim ws As Worksheet
    Set ws = Nothing
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    Dim selectionCol As Long
    Dim statusCol As Long
    If Not TryGetMaintenancePlansSelectionColumns(ws, selectionCol, statusCol) Then Exit Sub

    Dim planCol As Long
    planCol = FindHeaderColumnAny(ws, "PlanID")

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, statusCol).End(xlUp).Row
    If planCol > 0 Then
        Dim planLastRow As Long
        planLastRow = ws.Cells(ws.Rows.Count, planCol).End(xlUp).Row
        If planLastRow > lastRow Then lastRow = planLastRow
    End If

    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim eventsWasEnabled As Boolean
    eventsWasEnabled = Application.EnableEvents
    Application.EnableEvents = False

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        ApplyMaintenancePlanSelectionForCell ws, ws.Cells(r, selectionCol), statusCol, True
    Next r

    ws.Columns(selectionCol).HorizontalAlignment = xlCenter
    ws.Columns(selectionCol).ColumnWidth = 4

SafeExit:
    On Error Resume Next
    Application.EnableEvents = eventsWasEnabled
End Sub

Private Function TryGetMaintenancePlansSelectionColumns(ByVal ws As Worksheet, ByRef selectionCol As Long, ByRef statusCol As Long) As Boolean
    If ws Is Nothing Then Exit Function

    selectionCol = FindHeaderColumnAny(ws, PLAN_SELECTION_HEADER, "CreateSelected", "Create")
    statusCol = FindHeaderColumnAny(ws, "Status", "FieldValuesAsText/Status")

    TryGetMaintenancePlansSelectionColumns = (selectionCol > 0 And statusCol > 0)
End Function

Private Sub ApplyMaintenancePlanSelectionForCell(ByVal ws As Worksheet, ByVal targetCell As Range, ByVal statusCol As Long, ByVal resetReadyToChecked As Boolean)
    If ws Is Nothing Then Exit Sub
    If targetCell Is Nothing Then Exit Sub
    If targetCell.Row < START_ROW_DEFAULT Then Exit Sub

    Dim isReady As Boolean
    isReady = IsReadyPlanStatusValue(CStr(ws.Cells(targetCell.Row, statusCol).Value))

    If isReady Then
        If resetReadyToChecked Then
            targetCell.Value = PlanSelectionCheckedMarker()
        Else
            targetCell.Value = NormalizePlanSelectionValue(targetCell.Value, False)
        End If
    Else
        targetCell.Value = PlanSelectionUncheckedMarker()
    End If

    ApplyMaintenancePlanSelectionValidationForCell ws, targetCell, isReady
End Sub

Private Sub ApplyMaintenancePlanSelectionValidationForCell(ByVal ws As Worksheet, ByVal targetCell As Range, ByVal isReady As Boolean)
    If ws Is Nothing Then Exit Sub
    If targetCell Is Nothing Then Exit Sub

    On Error Resume Next
    targetCell.Validation.Delete
    On Error GoTo 0

    If Not isReady Then Exit Sub

    Dim formulaList As String
    formulaList = PlanSelectionCheckedMarker() & "," & PlanSelectionUncheckedMarker()

    On Error Resume Next
    targetCell.Validation.Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, Operator:=xlBetween, Formula1:=formulaList
    targetCell.Validation.IgnoreBlank = True
    targetCell.Validation.InCellDropdown = True
    On Error GoTo 0
End Sub

Private Function IsReadyPlanStatusValue(ByVal rawStatus As String) As Boolean
    IsReadyPlanStatusValue = (NormalizePlanStatusText(rawStatus) = PLAN_READY_STATUS)
End Function

Private Function NormalizePlanStatusText(ByVal rawStatus As String) As String
    Dim s As String
    s = LCase$(Trim$(CStr(rawStatus)))
    s = Replace(s, vbCrLf, " ")
    s = Replace(s, vbCr, " ")
    s = Replace(s, vbLf, " ")

    Do While InStr(1, s, "  ", vbBinaryCompare) > 0
        s = Replace(s, "  ", " ")
    Loop

    NormalizePlanStatusText = s
End Function

Private Function PlanSelectionCheckedMarker() As String
    PlanSelectionCheckedMarker = ChrW(&H2611)
End Function

Private Function PlanSelectionUncheckedMarker() As String
    PlanSelectionUncheckedMarker = ChrW(&H2610)
End Function

Private Function IsPlanSelectionChecked(ByVal rawValue As String) As Boolean
    Dim normalized As String
    normalized = UCase$(Trim$(rawValue))
    If Left$(normalized, 1) = "'" Then normalized = Mid$(normalized, 2)

    Select Case normalized
        Case UCase$(PlanSelectionCheckedMarker()), "TRUE", "SAND", "YES", "JA", "1", "X"
            IsPlanSelectionChecked = True
    End Select
End Function

Private Function NormalizePlanSelectionValue(ByVal rawValue As Variant, Optional ByVal defaultChecked As Boolean = False) As String
    If IsPlanSelectionChecked(CStr(rawValue)) Then
        NormalizePlanSelectionValue = PlanSelectionCheckedMarker()
        Exit Function
    End If

    Dim normalized As String
    normalized = UCase$(Trim$(CStr(rawValue)))
    If Left$(normalized, 1) = "'" Then normalized = Mid$(normalized, 2)

    Select Case normalized
        Case UCase$(PlanSelectionUncheckedMarker()), "FALSE", "FALSK", "NO", "NEJ", "0", vbNullString
            NormalizePlanSelectionValue = PlanSelectionUncheckedMarker()
        Case Else
            If defaultChecked Then
                NormalizePlanSelectionValue = PlanSelectionCheckedMarker()
            Else
                NormalizePlanSelectionValue = PlanSelectionUncheckedMarker()
            End If
    End Select
End Function

Private Sub ApplyMaintenancePlansSortFieldText(ByVal authHeader As String)
    ' Keep SortFieldId as numeric key; GUI_Script uses this value for SAP PLAN_SORT.
    Dim unusedAuthHeader As String
    unusedAuthHeader = authHeader
End Sub

Private Sub ApplyMaintenancePlansStatusColors()
    On Error GoTo SafeExit

    Dim ws As Worksheet
    Set ws = Nothing
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    Dim statusCol As Long
    statusCol = FindHeaderColumnAny(ws, "Status", "FieldValuesAsText/Status")
    If statusCol = 0 Then Exit Sub

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, statusCol).End(xlUp).Row
    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        ApplyStatusColorToCell ws.Cells(r, statusCol), CStr(ws.Cells(r, statusCol).Value)
    Next r

SafeExit:
End Sub

Private Sub ApplyStatusColorToCell(ByVal targetCell As Range, ByVal rawStatus As String)
    If targetCell Is Nothing Then Exit Sub

    Dim normalized As String
    normalized = CStr(rawStatus)
    normalized = Replace(normalized, vbCrLf, " ")
    normalized = Replace(normalized, vbCr, " ")
    normalized = Replace(normalized, vbLf, " ")
    normalized = LCase$(Trim$(normalized))

    With targetCell
        .Interior.ColorIndex = xlColorIndexNone
        .Font.ColorIndex = xlColorIndexAutomatic

        Select Case normalized
            Case "draft"
                .Interior.Color = RGB(214, 69, 69)
                .Font.Color = RGB(255, 255, 255)

            Case "in progress"
                .Interior.Color = RGB(242, 220, 164)
                .Font.Color = RGB(79, 54, 0)

            Case "ready for creation in sap"
                .Interior.Color = RGB(77, 140, 32)
                .Font.Color = RGB(255, 255, 255)

            Case "published"
                .Interior.Color = RGB(0, 120, 215)
                .Font.Color = RGB(255, 255, 255)
        End Select
    End With
End Sub

Private Sub ApplyMaintenanceItemsPlanNoDisplayAndColors()
    On Error GoTo SafeExit

    Dim wsItems As Worksheet
    Dim wsPlans As Worksheet

    Set wsItems = Nothing
    Set wsPlans = Nothing

    On Error Resume Next
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    Set wsPlans = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    On Error GoTo 0

    If wsItems Is Nothing Then Exit Sub
    If wsPlans Is Nothing Then Exit Sub

    Dim itemsPlanCol As Long
    Dim itemsItemIdCol As Long
    itemsPlanCol = FindHeaderColumnAny(wsItems, "MaintenancePlanNo", "FieldValuesAsText/MaintenancePlanNo", "MaintenancePlanNoId")
    itemsItemIdCol = FindHeaderColumnAny(wsItems, "ItemID", "FieldValuesAsText/ItemID")
    If itemsPlanCol = 0 Then Exit Sub

    Dim plansIdCol As Long
    Dim plansPlanIdCol As Long
    Dim plansStatusCol As Long

    plansIdCol = FindHeaderColumnAny(wsPlans, "Id", "ID")
    plansPlanIdCol = FindHeaderColumnAny(wsPlans, "PlanID")
    plansStatusCol = FindHeaderColumnAny(wsPlans, "Status", "FieldValuesAsText/Status")

    If plansPlanIdCol = 0 Or plansStatusCol = 0 Then Exit Sub

    Dim planIdByListId As Object
    Dim statusByPlanId As Object
    Set planIdByListId = CreateObject("Scripting.Dictionary")
    Set statusByPlanId = CreateObject("Scripting.Dictionary")
    planIdByListId.CompareMode = vbTextCompare
    statusByPlanId.CompareMode = vbTextCompare

    Dim lastPlanRow As Long
    lastPlanRow = wsPlans.Cells(wsPlans.Rows.Count, plansPlanIdCol).End(xlUp).Row

    Dim r As Long
    For r = START_ROW_DEFAULT To lastPlanRow
        Dim planIdValue As String
        Dim statusValue As String

        planIdValue = Trim$(CStr(wsPlans.Cells(r, plansPlanIdCol).Value))
        statusValue = Trim$(CStr(wsPlans.Cells(r, plansStatusCol).Value))

        If Len(planIdValue) > 0 Then
            statusByPlanId(NormalizePlanKey(planIdValue)) = statusValue
        End If

        If plansIdCol > 0 Then
            Dim listIdValue As String
            listIdValue = Trim$(CStr(wsPlans.Cells(r, plansIdCol).Value))

            Dim listIdKey As String
            listIdKey = NormalizeLookupIdKey(listIdValue)

            If Len(listIdKey) > 0 And Len(planIdValue) > 0 Then
                planIdByListId(listIdKey) = planIdValue
            End If
        End If
    Next r

    Dim lastItemRow As Long
    lastItemRow = wsItems.Cells(wsItems.Rows.Count, itemsPlanCol).End(xlUp).Row
    If lastItemRow < START_ROW_DEFAULT Then Exit Sub

    For r = START_ROW_DEFAULT To lastItemRow
        Dim rawPlanValue As String
        rawPlanValue = Trim$(CStr(wsItems.Cells(r, itemsPlanCol).Value))
        If Len(rawPlanValue) = 0 Then
            ApplyStatusColorToCell wsItems.Cells(r, itemsPlanCol), vbNullString
            If itemsItemIdCol > 0 Then ApplyStatusColorToCell wsItems.Cells(r, itemsItemIdCol), vbNullString
            GoTo NextItemRow
        End If

        Dim resolvedPlanId As String
        resolvedPlanId = rawPlanValue

        Dim rawPlanKey As String
        rawPlanKey = NormalizeLookupIdKey(rawPlanValue)
        If Len(rawPlanKey) > 0 Then
            If planIdByListId.Exists(rawPlanKey) Then
                resolvedPlanId = CStr(planIdByListId(rawPlanKey))
                wsItems.Cells(r, itemsPlanCol).Value = resolvedPlanId
            End If
        End If

        Dim statusKey As String
        statusKey = NormalizePlanKey(resolvedPlanId)

        Dim itemStatus As String
        If Len(statusKey) > 0 And statusByPlanId.Exists(statusKey) Then
            itemStatus = CStr(statusByPlanId(statusKey))
        Else
            itemStatus = vbNullString
        End If

        ApplyStatusColorToCell wsItems.Cells(r, itemsPlanCol), itemStatus
        If itemsItemIdCol > 0 Then
            ApplyStatusColorToCell wsItems.Cells(r, itemsItemIdCol), itemStatus
        End If
NextItemRow:
    Next r

SafeExit:
End Sub

Private Sub ApplyMaintenanceTlhPostProcessing()
    On Error GoTo SafeExit

    Dim wsTlh As Worksheet
    Dim wsItems As Worksheet
    Dim wsPlans As Worksheet

    Set wsTlh = Nothing
    Set wsItems = Nothing
    Set wsPlans = Nothing

    On Error Resume Next
    Set wsTlh = ThisWorkbook.Worksheets(WS_MAINTENANCE_TLH)
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    Set wsPlans = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    On Error GoTo 0

    If wsTlh Is Nothing Then Exit Sub

    Dim planIdCol As Long
    Dim itemIdCol As Long
    Dim taskIdCol As Long
    Dim plantInitialCol As Long
    Dim workCenterCol As Long
    Dim profileCol As Long

    planIdCol = FindHeaderColumnAny(wsTlh, "PlanID", "MaintenancePlanIDId", "MaintenancePlanNo")
    itemIdCol = FindHeaderColumnAny(wsTlh, "ItemID", "MaintenanceltemNo", "MaintenanceItemNoId", "FieldValuesAsText/MaintenanceItemNo")
    taskIdCol = FindHeaderColumnAny(wsTlh, "TaskID", "Task_List_Group", "TL_Group")
    plantInitialCol = FindHeaderColumnAny(wsTlh, "PlantInitial", "Plant_Name", "PlantName")
    workCenterCol = FindHeaderColumnAny(wsTlh, "Work Center", "WorkCtr", "Work_Center", "WorkCenter")
    profileCol = FindHeaderColumnAny(wsTlh, "Profile", "Plant_Key", "PlantKey")

    Dim lastRow As Long
    lastRow = wsTlh.Cells(wsTlh.Rows.Count, 1).End(xlUp).Row

    If taskIdCol > 0 Then
        Dim taskLastRow As Long
        taskLastRow = wsTlh.Cells(wsTlh.Rows.Count, taskIdCol).End(xlUp).Row
        If taskLastRow > lastRow Then lastRow = taskLastRow
    End If

    If planIdCol > 0 Then
        Dim planLastRow As Long
        planLastRow = wsTlh.Cells(wsTlh.Rows.Count, planIdCol).End(xlUp).Row
        If planLastRow > lastRow Then lastRow = planLastRow
    End If

    If itemIdCol > 0 Then
        Dim itemLastRow As Long
        itemLastRow = wsTlh.Cells(wsTlh.Rows.Count, itemIdCol).End(xlUp).Row
        If itemLastRow > lastRow Then lastRow = itemLastRow
    End If

    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim itemIdByListId As Object
    Dim workCenterByItemId As Object
    Dim planByItemId As Object
    Dim planIdByListId As Object
    Dim statusByPlanId As Object

    Set itemIdByListId = CreateObject("Scripting.Dictionary")
    Set workCenterByItemId = CreateObject("Scripting.Dictionary")
    Set planByItemId = CreateObject("Scripting.Dictionary")
    Set planIdByListId = CreateObject("Scripting.Dictionary")
    Set statusByPlanId = CreateObject("Scripting.Dictionary")
    itemIdByListId.CompareMode = vbTextCompare
    workCenterByItemId.CompareMode = vbTextCompare
    planByItemId.CompareMode = vbTextCompare
    planIdByListId.CompareMode = vbTextCompare
    statusByPlanId.CompareMode = vbTextCompare

    BuildMaintenancePlanMaps wsPlans, planIdByListId, statusByPlanId
    BuildMaintenanceItemMaps wsItems, itemIdByListId, workCenterByItemId, planByItemId

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        Dim resolvedItemId As String
        resolvedItemId = vbNullString

        If itemIdCol > 0 Then
            Dim rawItemId As String
            rawItemId = Trim$(CStr(wsTlh.Cells(r, itemIdCol).Value))
            resolvedItemId = rawItemId

            Dim itemLookupKey As String
            itemLookupKey = NormalizeLookupIdKey(rawItemId)
            If Len(itemLookupKey) > 0 Then
                If itemIdByListId.Exists(itemLookupKey) Then
                    resolvedItemId = CStr(itemIdByListId(itemLookupKey))
                    wsTlh.Cells(r, itemIdCol).Value = resolvedItemId
                End If
            End If

            If Len(resolvedItemId) > 0 Then
                wsTlh.Cells(r, itemIdCol).Value = resolvedItemId
            End If
        End If

        Dim resolvedPlanId As String
        resolvedPlanId = vbNullString

        If planIdCol > 0 Then
            Dim rawPlanId As String
            rawPlanId = Trim$(CStr(wsTlh.Cells(r, planIdCol).Value))
            resolvedPlanId = ResolvePlanIdFromRaw(rawPlanId, planIdByListId)
        End If

        If Len(resolvedPlanId) = 0 Then
            Dim planFromItemKey As String
            planFromItemKey = NormalizePlanKey(resolvedItemId)
            If Len(planFromItemKey) > 0 Then
                If planByItemId.Exists(planFromItemKey) Then
                    resolvedPlanId = ResolvePlanIdFromRaw(CStr(planByItemId(planFromItemKey)), planIdByListId)
                End If
            End If
        End If

        If planIdCol > 0 Then
            wsTlh.Cells(r, planIdCol).Value = resolvedPlanId
        End If

        If workCenterCol > 0 Then
            wsTlh.Cells(r, workCenterCol).Value = vbNullString

            Dim itemKey As String
            itemKey = NormalizePlanKey(resolvedItemId)
            If Len(itemKey) > 0 Then
                If workCenterByItemId.Exists(itemKey) Then
                    wsTlh.Cells(r, workCenterCol).Value = CStr(workCenterByItemId(itemKey))
                End If
            End If
        End If

        If profileCol > 0 And plantInitialCol > 0 Then
            Dim plantInitial As String
            plantInitial = Trim$(CStr(wsTlh.Cells(r, plantInitialCol).Value))
            wsTlh.Cells(r, profileCol).Value = BuildMaintenanceTlhProfile(plantInitial)
        End If
    Next r

    If taskIdCol > 0 Then
        RemoveMaintenanceTlhDuplicateTaskIds wsTlh, taskIdCol
    End If

    lastRow = wsTlh.Cells(wsTlh.Rows.Count, 1).End(xlUp).Row
    If taskIdCol > 0 Then
        Dim dedupTaskLastRow As Long
        dedupTaskLastRow = wsTlh.Cells(wsTlh.Rows.Count, taskIdCol).End(xlUp).Row
        If dedupTaskLastRow > lastRow Then lastRow = dedupTaskLastRow
    End If

    For r = START_ROW_DEFAULT To lastRow
        Dim tlhPlanId As String
        tlhPlanId = vbNullString

        If planIdCol > 0 Then
            tlhPlanId = Trim$(CStr(wsTlh.Cells(r, planIdCol).Value))
        End If

        If Len(tlhPlanId) = 0 And itemIdCol > 0 Then
            Dim rowItemKey As String
            rowItemKey = NormalizePlanKey(Trim$(CStr(wsTlh.Cells(r, itemIdCol).Value)))
            If Len(rowItemKey) > 0 Then
                If planByItemId.Exists(rowItemKey) Then
                    tlhPlanId = ResolvePlanIdFromRaw(CStr(planByItemId(rowItemKey)), planIdByListId)
                    If planIdCol > 0 Then wsTlh.Cells(r, planIdCol).Value = tlhPlanId
                End If
            End If
        End If

        Dim tlhStatusKey As String
        tlhStatusKey = NormalizePlanKey(tlhPlanId)

        Dim tlhStatus As String
        If Len(tlhStatusKey) > 0 And statusByPlanId.Exists(tlhStatusKey) Then
            tlhStatus = CStr(statusByPlanId(tlhStatusKey))
        Else
            tlhStatus = vbNullString
        End If

        If planIdCol > 0 Then ApplyStatusColorToCell wsTlh.Cells(r, planIdCol), tlhStatus
        If itemIdCol > 0 Then ApplyStatusColorToCell wsTlh.Cells(r, itemIdCol), tlhStatus
        If taskIdCol > 0 Then ApplyStatusColorToCell wsTlh.Cells(r, taskIdCol), tlhStatus
    Next r

SafeExit:
End Sub

Private Sub BuildMaintenancePlanMaps(ByVal wsPlans As Worksheet, ByVal planIdByListId As Object, ByVal statusByPlanId As Object)
    If wsPlans Is Nothing Then Exit Sub
    If planIdByListId Is Nothing Then Exit Sub
    If statusByPlanId Is Nothing Then Exit Sub

    Dim plansIdCol As Long
    Dim plansPlanIdCol As Long
    Dim plansStatusCol As Long

    plansIdCol = FindHeaderColumnAny(wsPlans, "Id", "ID")
    plansPlanIdCol = FindHeaderColumnAny(wsPlans, "PlanID")
    plansStatusCol = FindHeaderColumnAny(wsPlans, "Status", "FieldValuesAsText/Status")

    If plansPlanIdCol = 0 Or plansStatusCol = 0 Then Exit Sub

    Dim lastRow As Long
    lastRow = wsPlans.Cells(wsPlans.Rows.Count, plansPlanIdCol).End(xlUp).Row
    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        Dim planIdText As String
        Dim statusText As String

        planIdText = Trim$(CStr(wsPlans.Cells(r, plansPlanIdCol).Value))
        statusText = Trim$(CStr(wsPlans.Cells(r, plansStatusCol).Value))

        If Len(planIdText) > 0 Then
            statusByPlanId(NormalizePlanKey(planIdText)) = statusText
        End If

        If plansIdCol > 0 And Len(planIdText) > 0 Then
            Dim listIdKey As String
            listIdKey = NormalizeLookupIdKey(Trim$(CStr(wsPlans.Cells(r, plansIdCol).Value)))
            If Len(listIdKey) > 0 Then
                planIdByListId(listIdKey) = planIdText
            End If
        End If
    Next r
End Sub

Private Sub BuildMaintenanceItemMaps(ByVal wsItems As Worksheet, ByVal itemIdByListId As Object, ByVal workCenterByItemId As Object, ByVal planByItemId As Object)
    If wsItems Is Nothing Then Exit Sub
    If itemIdByListId Is Nothing Then Exit Sub
    If workCenterByItemId Is Nothing Then Exit Sub
    If planByItemId Is Nothing Then Exit Sub

    Dim itemListIdCol As Long
    Dim itemIdCol As Long
    Dim itemWorkCenterCol As Long
    Dim itemPlanCol As Long

    itemListIdCol = FindHeaderColumnAny(wsItems, "Id", "ID")
    itemIdCol = FindHeaderColumnAny(wsItems, "ItemID", "FieldValuesAsText/ItemID")
    itemWorkCenterCol = FindHeaderColumnAny(wsItems, "MainWorkCenterId", "MainWorkCenter", "Work Center", "WorkCtr", "FieldValuesAsText/MainWorkCenter")
    itemPlanCol = FindHeaderColumnAny(wsItems, "MaintenancePlanNo", "FieldValuesAsText/MaintenancePlanNo", "MaintenancePlanNoId")

    If itemIdCol = 0 Then Exit Sub

    Dim lastRow As Long
    lastRow = wsItems.Cells(wsItems.Rows.Count, itemIdCol).End(xlUp).Row

    If itemWorkCenterCol > 0 Then
        Dim wcLastRow As Long
        wcLastRow = wsItems.Cells(wsItems.Rows.Count, itemWorkCenterCol).End(xlUp).Row
        If wcLastRow > lastRow Then lastRow = wcLastRow
    End If

    If itemPlanCol > 0 Then
        Dim planLastRow As Long
        planLastRow = wsItems.Cells(wsItems.Rows.Count, itemPlanCol).End(xlUp).Row
        If planLastRow > lastRow Then lastRow = planLastRow
    End If

    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        Dim itemIdText As String
        itemIdText = Trim$(CStr(wsItems.Cells(r, itemIdCol).Value))
        If Len(itemIdText) = 0 Then GoTo NextRow

        Dim itemKey As String
        itemKey = NormalizePlanKey(itemIdText)
        If Len(itemKey) = 0 Then GoTo NextRow

        If itemWorkCenterCol > 0 Then
            Dim workCenterText As String
            workCenterText = Trim$(CStr(wsItems.Cells(r, itemWorkCenterCol).Value))
            If Len(workCenterText) > 0 Then
                If Not workCenterByItemId.Exists(itemKey) Then
                    workCenterByItemId.Add itemKey, workCenterText
                End If
            End If
        End If

        If itemPlanCol > 0 Then
            Dim planText As String
            planText = Trim$(CStr(wsItems.Cells(r, itemPlanCol).Value))
            If Len(planText) > 0 Then
                If Not planByItemId.Exists(itemKey) Then
                    planByItemId.Add itemKey, planText
                End If
            End If
        End If

        If itemListIdCol > 0 Then
            Dim listIdKey As String
            listIdKey = NormalizeLookupIdKey(Trim$(CStr(wsItems.Cells(r, itemListIdCol).Value)))
            If Len(listIdKey) > 0 Then
                itemIdByListId(listIdKey) = itemIdText
            End If
        End If
NextRow:
    Next r
End Sub

Private Function ResolvePlanIdFromRaw(ByVal rawPlanValue As String, ByVal planIdByListId As Object) As String
    Dim resolvedPlan As String
    resolvedPlan = Trim$(rawPlanValue)

    Dim planLookupKey As String
    planLookupKey = NormalizeLookupIdKey(resolvedPlan)

    If Len(planLookupKey) > 0 Then
        If Not planIdByListId Is Nothing Then
            If planIdByListId.Exists(planLookupKey) Then
                resolvedPlan = CStr(planIdByListId(planLookupKey))
            End If
        End If
    End If

    ResolvePlanIdFromRaw = Trim$(resolvedPlan)
End Function

Private Function BuildMaintenanceTlhProfile(ByVal plantInitial As String) As String
    Dim normalizedPlant As String
    normalizedPlant = Trim$(plantInitial)
    If Len(normalizedPlant) = 0 Then Exit Function

    BuildMaintenanceTlhProfile = "PM" & normalizedPlant
End Function

Private Sub RemoveMaintenanceTlhDuplicateTaskIds(ByVal wsTlh As Worksheet, ByVal taskIdCol As Long)
    If wsTlh Is Nothing Then Exit Sub
    If taskIdCol <= 0 Then Exit Sub

    Dim lastRow As Long
    lastRow = wsTlh.Cells(wsTlh.Rows.Count, taskIdCol).End(xlUp).Row
    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim firstRowByTask As Object
    Set firstRowByTask = CreateObject("Scripting.Dictionary")
    firstRowByTask.CompareMode = vbTextCompare

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        Dim taskIdText As String
        taskIdText = Trim$(CStr(wsTlh.Cells(r, taskIdCol).Value))

        Dim taskKey As String
        taskKey = NormalizePlanKey(taskIdText)

        If Len(taskKey) > 0 Then
            If Not firstRowByTask.Exists(taskKey) Then
                firstRowByTask.Add taskKey, r
            End If
        End If
    Next r

    For r = lastRow To START_ROW_DEFAULT Step -1
        Dim currentTask As String
        currentTask = Trim$(CStr(wsTlh.Cells(r, taskIdCol).Value))

        Dim currentKey As String
        currentKey = NormalizePlanKey(currentTask)

        If Len(currentKey) > 0 Then
            If firstRowByTask.Exists(currentKey) Then
                If CLng(firstRowByTask(currentKey)) <> r Then
                    wsTlh.Rows(r).Delete
                End If
            End If
        End If
    Next r
End Sub

Private Sub ApplyMaintenanceTlDisplayAndColors()
    On Error GoTo SafeExit

    Dim wsTl As Worksheet
    Dim wsPlans As Worksheet
    Dim wsItems As Worksheet

    Set wsTl = Nothing
    Set wsPlans = Nothing
    Set wsItems = Nothing

    On Error Resume Next
    Set wsTl = ThisWorkbook.Worksheets(WS_MAINTENANCE_TL)
    Set wsPlans = ThisWorkbook.Worksheets(WS_MAINTENANCE_PLANS)
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    On Error GoTo 0

    If wsTl Is Nothing Then Exit Sub
    If wsPlans Is Nothing Then Exit Sub

    Dim tlPlanCol As Long
    Dim tlItemCol As Long
    Dim tlTaskCol As Long
    Dim tlTaskItemCol As Long

    tlPlanCol = FindHeaderColumnAny(wsTl, "MaintenancePlanIDId", "FieldValuesAsText/MaintenancePlanID")
    tlItemCol = FindHeaderColumnAny(wsTl, "MaintenanceItemNoId", "FieldValuesAsText/MaintenanceItemNo")
    tlTaskCol = FindHeaderColumnAny(wsTl, "TaskID", "FieldValuesAsText/TaskID")
    tlTaskItemCol = FindHeaderColumnAny(wsTl, "TaskItemID", "FieldValuesAsText/TaskItemID")

    If tlPlanCol = 0 And tlItemCol = 0 And tlTaskCol = 0 And tlTaskItemCol = 0 Then Exit Sub

    Dim planIdByListId As Object
    Dim statusByPlanId As Object
    Set planIdByListId = CreateObject("Scripting.Dictionary")
    Set statusByPlanId = CreateObject("Scripting.Dictionary")
    planIdByListId.CompareMode = vbTextCompare
    statusByPlanId.CompareMode = vbTextCompare

    Dim plansIdCol As Long
    Dim plansPlanIdCol As Long
    Dim plansStatusCol As Long
    plansIdCol = FindHeaderColumnAny(wsPlans, "Id", "ID")
    plansPlanIdCol = FindHeaderColumnAny(wsPlans, "PlanID")
    plansStatusCol = FindHeaderColumnAny(wsPlans, "Status", "FieldValuesAsText/Status")

    If plansPlanIdCol = 0 Or plansStatusCol = 0 Then Exit Sub

    Dim lastPlanRow As Long
    lastPlanRow = wsPlans.Cells(wsPlans.Rows.Count, plansPlanIdCol).End(xlUp).Row

    Dim r As Long
    For r = START_ROW_DEFAULT To lastPlanRow
        Dim planIdValue As String
        Dim statusValue As String

        planIdValue = Trim$(CStr(wsPlans.Cells(r, plansPlanIdCol).Value))
        statusValue = Trim$(CStr(wsPlans.Cells(r, plansStatusCol).Value))

        If Len(planIdValue) > 0 Then
            statusByPlanId(NormalizePlanKey(planIdValue)) = statusValue
        End If

        If plansIdCol > 0 Then
            Dim listIdValue As String
            listIdValue = Trim$(CStr(wsPlans.Cells(r, plansIdCol).Value))

            Dim listIdKey As String
            listIdKey = NormalizeLookupIdKey(listIdValue)

            If Len(listIdKey) > 0 And Len(planIdValue) > 0 Then
                planIdByListId(listIdKey) = planIdValue
            End If
        End If
    Next r

    Dim itemIdByListId As Object
    Dim planByItemId As Object
    Set itemIdByListId = CreateObject("Scripting.Dictionary")
    Set planByItemId = CreateObject("Scripting.Dictionary")
    itemIdByListId.CompareMode = vbTextCompare
    planByItemId.CompareMode = vbTextCompare

    If Not wsItems Is Nothing Then
        Dim itemsIdCol As Long
        Dim itemsItemIdCol As Long
        Dim itemsPlanCol As Long

        itemsIdCol = FindHeaderColumnAny(wsItems, "Id", "ID")
        itemsItemIdCol = FindHeaderColumnAny(wsItems, "ItemID", "FieldValuesAsText/ItemID")
        itemsPlanCol = FindHeaderColumnAny(wsItems, "MaintenancePlanNo", "FieldValuesAsText/MaintenancePlanNo", "MaintenancePlanNoId")

        If itemsItemIdCol > 0 Then
            Dim lastItemRow As Long
            lastItemRow = wsItems.Cells(wsItems.Rows.Count, itemsItemIdCol).End(xlUp).Row

            For r = START_ROW_DEFAULT To lastItemRow
                Dim itemIdValue As String
                Dim itemPlanValue As String

                itemIdValue = Trim$(CStr(wsItems.Cells(r, itemsItemIdCol).Value))
                If Len(itemIdValue) > 0 Then
                    If itemsPlanCol > 0 Then
                        itemPlanValue = Trim$(CStr(wsItems.Cells(r, itemsPlanCol).Value))
                        If Len(itemPlanValue) > 0 Then
                            planByItemId(NormalizePlanKey(itemIdValue)) = itemPlanValue
                        End If
                    End If

                    If itemsIdCol > 0 Then
                        Dim itemListId As String
                        itemListId = Trim$(CStr(wsItems.Cells(r, itemsIdCol).Value))
                        Dim itemListKey As String
                        itemListKey = NormalizeLookupIdKey(itemListId)

                        If Len(itemListKey) > 0 Then
                            itemIdByListId(itemListKey) = itemIdValue
                        End If
                    End If
                End If
            Next r
        End If
    End If

    Dim lastTlRow As Long
    lastTlRow = wsTl.Cells(wsTl.Rows.Count, 1).End(xlUp).Row
    If lastTlRow < START_ROW_TL Then Exit Sub

    For r = START_ROW_TL To lastTlRow
        Dim resolvedPlanId As String
        resolvedPlanId = vbNullString

        If tlPlanCol > 0 Then
            Dim rawTlPlan As String
            rawTlPlan = Trim$(CStr(wsTl.Cells(r, tlPlanCol).Value))
            Dim tlPlanKey As String
            tlPlanKey = NormalizeLookupIdKey(rawTlPlan)

            resolvedPlanId = rawTlPlan
            If Len(tlPlanKey) > 0 Then
                If planIdByListId.Exists(tlPlanKey) Then
                    resolvedPlanId = CStr(planIdByListId(tlPlanKey))
                    wsTl.Cells(r, tlPlanCol).Value = resolvedPlanId
                End If
            End If
        End If

        If tlItemCol > 0 Then
            Dim rawTlItem As String
            rawTlItem = Trim$(CStr(wsTl.Cells(r, tlItemCol).Value))
            Dim tlItemKey As String
            tlItemKey = NormalizeLookupIdKey(rawTlItem)

            Dim resolvedItemId As String
            resolvedItemId = rawTlItem

            If Len(tlItemKey) > 0 Then
                If itemIdByListId.Exists(tlItemKey) Then
                    resolvedItemId = CStr(itemIdByListId(tlItemKey))
                    wsTl.Cells(r, tlItemCol).Value = resolvedItemId
                End If
            End If

            If Len(Trim$(resolvedPlanId)) = 0 Then
                Dim itemStatusKey As String
                itemStatusKey = NormalizePlanKey(resolvedItemId)
                If Len(itemStatusKey) > 0 Then
                    If planByItemId.Exists(itemStatusKey) Then
                        resolvedPlanId = CStr(planByItemId(itemStatusKey))
                    End If
                End If
            End If
        End If

        If tlTaskCol > 0 Then
            Dim rawTask As String
            rawTask = Trim$(CStr(wsTl.Cells(r, tlTaskCol).Value))
            Dim taskKey As String
            taskKey = NormalizeLookupIdKey(rawTask)
            If Len(taskKey) > 0 Then
                If planIdByListId.Exists(taskKey) Then
                    Dim taskPlanId As String
                    taskPlanId = CStr(planIdByListId(taskKey))
                    wsTl.Cells(r, tlTaskCol).Value = taskPlanId
                    If Len(Trim$(resolvedPlanId)) = 0 Then resolvedPlanId = taskPlanId
                End If
            End If
        End If

        If tlTaskItemCol > 0 Then
            Dim rawTaskItem As String
            rawTaskItem = Trim$(CStr(wsTl.Cells(r, tlTaskItemCol).Value))
            Dim taskItemKey As String
            taskItemKey = NormalizeLookupIdKey(rawTaskItem)

            Dim resolvedTaskItemId As String
            resolvedTaskItemId = rawTaskItem

            If Len(taskItemKey) > 0 Then
                If itemIdByListId.Exists(taskItemKey) Then
                    resolvedTaskItemId = CStr(itemIdByListId(taskItemKey))
                    wsTl.Cells(r, tlTaskItemCol).Value = resolvedTaskItemId
                End If
            End If

            If Len(Trim$(resolvedPlanId)) = 0 Then
                Dim taskItemStatusKey As String
                taskItemStatusKey = NormalizePlanKey(resolvedTaskItemId)
                If Len(taskItemStatusKey) > 0 Then
                    If planByItemId.Exists(taskItemStatusKey) Then
                        resolvedPlanId = CStr(planByItemId(taskItemStatusKey))
                    End If
                End If
            End If
        End If

        Dim tlStatus As String
        Dim tlStatusKey As String
        tlStatusKey = NormalizePlanKey(resolvedPlanId)

        If Len(tlStatusKey) > 0 And statusByPlanId.Exists(tlStatusKey) Then
            tlStatus = CStr(statusByPlanId(tlStatusKey))
        Else
            tlStatus = vbNullString
        End If

        If tlPlanCol > 0 Then ApplyStatusColorToCell wsTl.Cells(r, tlPlanCol), tlStatus
        If tlItemCol > 0 Then ApplyStatusColorToCell wsTl.Cells(r, tlItemCol), tlStatus
        If tlTaskCol > 0 Then ApplyStatusColorToCell wsTl.Cells(r, tlTaskCol), tlStatus
        If tlTaskItemCol > 0 Then ApplyStatusColorToCell wsTl.Cells(r, tlTaskItemCol), tlStatus
    Next r

SafeExit:
End Sub

Private Sub ApplyMaintenanceItemsLookupText(ByVal authHeader As String)
    On Error GoTo SafeExit

    Dim ws As Worksheet
    Set ws = Nothing
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    Dim idCol As Long
    Dim mainWorkCenterCol As Long
    Dim maintenanceActivityTypeCol As Long
    idCol = FindHeaderColumnAny(ws, "Id", "ID")
    mainWorkCenterCol = FindHeaderColumnAny(ws, "MainWorkCenterId")
    maintenanceActivityTypeCol = FindHeaderColumnAny(ws, "MaintenanceActivityTypeId")

    If idCol = 0 Then Exit Sub
    If mainWorkCenterCol = 0 And maintenanceActivityTypeCol = 0 Then Exit Sub

    Dim mainWorkCenterTitles As Object
    Dim activityTitles As Object

    Set mainWorkCenterTitles = BuildLookupTitleMapForItemsField("MainWorkCenter", authHeader)
    Set activityTitles = BuildLookupTitleMapForItemsField("MaintenanceActivityType", authHeader)

    If Not HasDictionaryEntries(mainWorkCenterTitles) And Not HasDictionaryEntries(activityTitles) Then Exit Sub

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, idCol).End(xlUp).Row
    If lastRow < START_ROW_DEFAULT Then Exit Sub

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        If mainWorkCenterCol > 0 Then
            Dim wcRaw As String
            wcRaw = Trim$(CStr(ws.Cells(r, mainWorkCenterCol).Value))

            Dim wcKey As String
            wcKey = NormalizeLookupIdKey(wcRaw)

            If Len(wcKey) > 0 And HasDictionaryEntries(mainWorkCenterTitles) Then
                If mainWorkCenterTitles.Exists(wcKey) Then
                    ws.Cells(r, mainWorkCenterCol).Value = CStr(mainWorkCenterTitles(wcKey))
                End If
            End If
        End If

        If maintenanceActivityTypeCol > 0 Then
            Dim actRaw As String
            actRaw = Trim$(CStr(ws.Cells(r, maintenanceActivityTypeCol).Value))

            Dim actKey As String
            actKey = NormalizeLookupIdKey(actRaw)

            If Len(actKey) > 0 And HasDictionaryEntries(activityTitles) Then
                If activityTitles.Exists(actKey) Then
                    ws.Cells(r, maintenanceActivityTypeCol).Value = CStr(activityTitles(actKey))
                End If
            End If
        End If
NextRow:
    Next r

SafeExit:
End Sub

Private Function BuildLookupTitleMapForItemsField(ByVal fieldInternalName As String, ByVal authHeader As String) As Object
    On Error GoTo FailBuild

    Dim lookupListGuid As String
    lookupListGuid = GetLookupListGuidFromItemsField(fieldInternalName, authHeader)
    If Len(lookupListGuid) = 0 Then Exit Function

    Dim siteRoot As String
    siteRoot = GetSiteRootFromApiUrl(GetSharePointItemsUrl())
    If Len(siteRoot) = 0 Then Exit Function

    Dim sourceUrl As String
    sourceUrl = siteRoot & "/_api/web/lists(guid'" & lookupListGuid & "')/items"

    Dim sourceItems As Collection
    Set sourceItems = FetchSharePointItems(sourceUrl, "$select=Id,Title", authHeader)

    Dim titleByLookupId As Object
    Set titleByLookupId = CreateObject("Scripting.Dictionary")
    titleByLookupId.CompareMode = vbTextCompare

    Dim i As Long
    For i = 1 To CollectionCount(sourceItems)
        If Not IsObject(sourceItems(i)) Then GoTo NextSourceItem

        Dim itm As Object
        Set itm = sourceItems(i)

        Dim rawId As Variant
        Dim rawTitle As Variant
        If Not TryGetItemValue(itm, "Id", rawId) Then GoTo NextSourceItem
        If Not TryGetItemValue(itm, "Title", rawTitle) Then GoTo NextSourceItem

        Dim idKey As String
        Dim titleText As String
        idKey = NormalizeLookupIdKey(CStr(CoerceSharePointValue(rawId)))
        titleText = Trim$(CStr(CoerceSharePointValue(rawTitle)))

        If Len(idKey) > 0 And Len(titleText) > 0 Then
            titleByLookupId(idKey) = titleText
        End If
NextSourceItem:
    Next i

    Set BuildLookupTitleMapForItemsField = titleByLookupId
    Exit Function

FailBuild:
    Set BuildLookupTitleMapForItemsField = Nothing
End Function

Private Function BuildLookupTitleMapForPlansField(ByVal fieldInternalName As String, ByVal authHeader As String) As Object
    On Error GoTo FailBuild

    Dim lookupListGuid As String
    lookupListGuid = GetLookupListGuidFromPlansField(fieldInternalName, authHeader)
    If Len(lookupListGuid) = 0 Then Exit Function

    Dim siteRoot As String
    siteRoot = GetSiteRootFromApiUrl(GetSharePointPlansUrl())
    If Len(siteRoot) = 0 Then Exit Function

    Dim sourceUrl As String
    sourceUrl = siteRoot & "/_api/web/lists(guid'" & lookupListGuid & "')/items"

    Dim sourceItems As Collection
    Set sourceItems = FetchSharePointItems(sourceUrl, "$select=Id,Title", authHeader)

    Dim titleByLookupId As Object
    Set titleByLookupId = CreateObject("Scripting.Dictionary")
    titleByLookupId.CompareMode = vbTextCompare

    Dim i As Long
    For i = 1 To CollectionCount(sourceItems)
        If Not IsObject(sourceItems(i)) Then GoTo NextSourceItem

        Dim itm As Object
        Set itm = sourceItems(i)

        Dim rawId As Variant
        Dim rawTitle As Variant
        If Not TryGetItemValue(itm, "Id", rawId) Then GoTo NextSourceItem
        If Not TryGetItemValue(itm, "Title", rawTitle) Then GoTo NextSourceItem

        Dim idKey As String
        Dim titleText As String
        idKey = NormalizeLookupIdKey(CStr(CoerceSharePointValue(rawId)))
        titleText = Trim$(CStr(CoerceSharePointValue(rawTitle)))

        If Len(idKey) > 0 And Len(titleText) > 0 Then
            titleByLookupId(idKey) = titleText
        End If
NextSourceItem:
    Next i

    Set BuildLookupTitleMapForPlansField = titleByLookupId
    Exit Function

FailBuild:
    Set BuildLookupTitleMapForPlansField = Nothing
End Function

Private Function GetLookupListGuidFromItemsField(ByVal fieldInternalName As String, ByVal authHeader As String) As String
    On Error GoTo FailLookup

    Dim listRootUrl As String
    listRootUrl = GetListRootFromItemsUrl(GetSharePointItemsUrl())
    If Len(listRootUrl) = 0 Then Exit Function

    Dim queryUrl As String
    queryUrl = listRootUrl & "/fields/getbyinternalnameortitle('" & fieldInternalName & "')?$select=LookupList"

    Dim root As Object
    Set root = HttpGetJson(queryUrl, authHeader)

    Dim fieldDict As Object
    Set fieldDict = UnwrapODataDictionary(root)
    If fieldDict Is Nothing Then Exit Function
    If Not HasDictKey(fieldDict, "LookupList") Then Exit Function

    Dim guidValue As String
    guidValue = Trim$(CStr(fieldDict("LookupList")))
    guidValue = Replace(guidValue, "{", vbNullString)
    guidValue = Replace(guidValue, "}", vbNullString)

    GetLookupListGuidFromItemsField = guidValue
    Exit Function

FailLookup:
End Function

Private Function GetLookupListGuidFromPlansField(ByVal fieldInternalName As String, ByVal authHeader As String) As String
    On Error GoTo FailLookup

    Dim listRootUrl As String
    listRootUrl = GetListRootFromItemsUrl(GetSharePointPlansUrl())
    If Len(listRootUrl) = 0 Then Exit Function

    Dim queryUrl As String
    queryUrl = listRootUrl & "/fields/getbyinternalnameortitle('" & fieldInternalName & "')?$select=LookupList"

    Dim root As Object
    Set root = HttpGetJson(queryUrl, authHeader)

    Dim fieldDict As Object
    Set fieldDict = UnwrapODataDictionary(root)
    If fieldDict Is Nothing Then Exit Function
    If Not HasDictKey(fieldDict, "LookupList") Then Exit Function

    Dim guidValue As String
    guidValue = Trim$(CStr(fieldDict("LookupList")))
    guidValue = Replace(guidValue, "{", vbNullString)
    guidValue = Replace(guidValue, "}", vbNullString)

    GetLookupListGuidFromPlansField = guidValue
    Exit Function

FailLookup:
End Function

Private Function UnwrapODataDictionary(ByVal root As Object) As Object
    If root Is Nothing Then Exit Function
    If TypeName(root) <> "Dictionary" Then Exit Function

    If HasDictKey(root, "d") Then
        If IsObject(root("d")) Then
            Set UnwrapODataDictionary = root("d")
            Exit Function
        End If
    End If

    Set UnwrapODataDictionary = root
End Function

Private Function GetListRootFromItemsUrl(ByVal itemsUrl As String) As String
    Dim work As String
    work = Trim$(itemsUrl)
    If Len(work) = 0 Then Exit Function

    Dim p As Long
    p = InStrRev(work, "/items", -1, vbTextCompare)
    If p <= 0 Then Exit Function

    GetListRootFromItemsUrl = Left$(work, p - 1)
End Function

Private Function GetSiteRootFromApiUrl(ByVal apiUrl As String) As String
    Dim work As String
    work = Trim$(apiUrl)
    If Len(work) = 0 Then Exit Function

    Dim p As Long
    p = InStr(1, work, "/_api/", vbTextCompare)
    If p <= 0 Then Exit Function

    GetSiteRootFromApiUrl = Left$(work, p - 1)
End Function

Private Function NormalizeLookupIdKey(ByVal rawValue As String) As String
    Dim s As String
    s = Trim$(rawValue)
    If Len(s) = 0 Then Exit Function

    If Left$(s, 1) = "'" Then
        s = Mid$(s, 2)
    End If

    If IsNumeric(s) Then
        NormalizeLookupIdKey = CStr(CLng(Val(s)))
    Else
        NormalizeLookupIdKey = s
    End If
End Function

Private Function NormalizePlanKey(ByVal rawValue As String) As String
    Dim s As String
    s = Trim$(rawValue)
    If Len(s) = 0 Then Exit Function

    If Left$(s, 1) = "'" Then
        s = Mid$(s, 2)
    End If

    NormalizePlanKey = UCase$(Trim$(s))
End Function

Private Function HasDictionaryEntries(ByVal dict As Object) As Boolean
    On Error GoTo FailCheck

    If dict Is Nothing Then Exit Function
    If TypeName(dict) <> "Dictionary" Then Exit Function

    HasDictionaryEntries = (dict.Count > 0)
    Exit Function

FailCheck:
    HasDictionaryEntries = False
End Function

Private Function RefreshObjectListFromMaintenanceItems() As Long
    Dim wsItems As Worksheet
    Set wsItems = Nothing
    On Error Resume Next
    Set wsItems = ThisWorkbook.Worksheets(WS_MAINTENANCE_ITEMS)
    On Error GoTo 0

    Dim outHeaders As Variant
    outHeaders = Array("ItemID", "ObjectList")

    If wsItems Is Nothing Then
        WriteImportRows WS_OBJECT_LIST, START_ROW_DEFAULT, outHeaders, Empty
        Exit Function
    End If

    Dim itemIdCol As Long
    Dim objectListCol As Long
    itemIdCol = FindHeaderColumnAny(wsItems, "ItemID", "FieldValuesAsText/ItemID")
    objectListCol = FindHeaderColumnAny(wsItems, "ObjectList", "FieldValuesAsText/ObjectList")

    If itemIdCol = 0 Or objectListCol = 0 Then
        WriteImportRows WS_OBJECT_LIST, START_ROW_DEFAULT, outHeaders, Empty
        Exit Function
    End If

    Dim lastRow As Long
    lastRow = wsItems.Cells(wsItems.Rows.Count, itemIdCol).End(xlUp).Row
    Dim lastObjectRow As Long
    lastObjectRow = wsItems.Cells(wsItems.Rows.Count, objectListCol).End(xlUp).Row
    If lastObjectRow > lastRow Then lastRow = lastObjectRow

    If lastRow < START_ROW_DEFAULT Then
        WriteImportRows WS_OBJECT_LIST, START_ROW_DEFAULT, outHeaders, Empty
        Exit Function
    End If

    Dim entries As Collection
    Set entries = New Collection

    Dim r As Long
    For r = START_ROW_DEFAULT To lastRow
        Dim itemId As String
        itemId = Trim$(CStr(wsItems.Cells(r, itemIdCol).Value))
        If Len(itemId) = 0 Then GoTo NextItemRow

        Dim rawObjectList As String
        rawObjectList = CStr(wsItems.Cells(r, objectListCol).Value)
        If Len(Trim$(rawObjectList)) = 0 Then GoTo NextItemRow

        CollectObjectListEntries entries, itemId, rawObjectList
NextItemRow:
    Next r

    If entries.Count = 0 Then
        WriteImportRows WS_OBJECT_LIST, START_ROW_DEFAULT, outHeaders, Empty
        Exit Function
    End If

    Dim outRows() As Variant
    ReDim outRows(1 To entries.Count, 1 To 2)

    Dim i As Long
    For i = 1 To entries.Count
        Dim pair As Variant
        pair = entries(i)
        outRows(i, 1) = CStr(pair(1))
        outRows(i, 2) = CStr(pair(2))
    Next i

    WriteImportRows WS_OBJECT_LIST, START_ROW_DEFAULT, outHeaders, outRows
    RefreshObjectListFromMaintenanceItems = entries.Count
End Function

Private Sub CollectObjectListEntries(ByRef entries As Collection, ByVal itemId As String, ByVal rawObjectList As String)
    If entries Is Nothing Then Exit Sub

    Dim normalized As String
    normalized = Replace(rawObjectList, vbCrLf, vbLf)
    normalized = Replace(normalized, vbCr, vbLf)
    normalized = Replace(normalized, "|||", vbLf)

    Dim parts() As String
    parts = Split(normalized, vbLf)

    Dim i As Long
    For i = LBound(parts) To UBound(parts)
        Dim cleaned As String
        cleaned = NormalizeObjectListEntry(CStr(parts(i)))
        If Len(cleaned) = 0 Then GoTo NextPart

        Dim pair(1 To 2) As String
        pair(1) = itemId
        pair(2) = cleaned
        entries.Add pair
NextPart:
    Next i
End Sub

Private Function NormalizeObjectListEntry(ByVal entryText As String) As String
    Dim s As String
    s = Replace(entryText, vbTab, " ")
    s = Replace(s, Chr$(160), " ")
    s = Trim$(s)
    If Len(s) = 0 Then Exit Function

    Dim descPos As Long
    descPos = InStr(1, s, " - ", vbTextCompare)
    If descPos > 0 Then
        s = Left$(s, descPos - 1)
    End If

    s = CollapseRepeatedSpacesInLine(s)
    NormalizeObjectListEntry = Trim$(s)
End Function

Private Function FindHeaderColumnAny(ByVal ws As Worksheet, ParamArray headerCandidates() As Variant) As Long
    If ws Is Nothing Then Exit Function

    Dim lastCol As Long
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    If lastCol <= 0 Then Exit Function

    Dim candidateMap As Object
    Set candidateMap = CreateObject("Scripting.Dictionary")
    candidateMap.CompareMode = vbTextCompare

    Dim i As Long
    For i = LBound(headerCandidates) To UBound(headerCandidates)
        Dim candidate As String
        candidate = NormalizeFieldName(CStr(headerCandidates(i)))
        If Len(candidate) > 0 Then candidateMap(candidate) = True
    Next i

    Dim c As Long
    For c = 1 To lastCol
        Dim normalizedHeader As String
        normalizedHeader = NormalizeFieldName(CStr(ws.Cells(1, c).Value))
        If Len(normalizedHeader) > 0 Then
            If candidateMap.Exists(normalizedHeader) Then
                FindHeaderColumnAny = c
                Exit Function
            End If
        End If
    Next c
End Function

Private Function BuildInitialFetchUrl(ByVal baseUrl As String, ByVal filterClause As String) As String
    Dim query As String
    Dim signature As String

    query = "$top=" & CStr(SHAREPOINT_DEFAULT_PAGE_SIZE) & "&$format=json"
    signature = LCase$(baseUrl & "&" & filterClause)

    ' Maintenance plans/items include lookup/date fields that are most reliable via FieldValuesAsText.
    If IsMaintenancePlansUrl(baseUrl) Or IsMaintenanceItemsUrl(baseUrl) Then
        If InStr(1, signature, "$select=", vbTextCompare) = 0 Then
            query = query & "&$select=*,FieldValuesAsText"
        End If
        If InStr(1, signature, "$expand=", vbTextCompare) = 0 Then
            query = query & "&$expand=FieldValuesAsText"
        End If
    End If

    If Len(Trim$(filterClause)) > 0 Then
        If LCase$(Left$(Trim$(filterClause), 1)) = "$" Then
            query = query & "&" & Trim$(filterClause)
        ElseIf LCase$(Left$(Trim$(filterClause), 8)) = "$filter=" Then
            query = query & "&" & Trim$(filterClause)
        Else
            query = query & "&$filter=" & Trim$(filterClause)
        End If
    End If

    BuildInitialFetchUrl = AppendQuery(baseUrl, query)
End Function

Private Function IsMaintenancePlansUrl(ByVal sourceUrl As String) As Boolean
    Dim urlLower As String
    urlLower = LCase$(Trim$(sourceUrl))

    IsMaintenancePlansUrl = _
        (InStr(1, urlLower, "getbytitle('maintenanceplans')", vbTextCompare) > 0) Or _
        (InStr(1, urlLower, "/lists/maintenanceplans/", vbTextCompare) > 0)
End Function

Private Function IsMaintenanceItemsUrl(ByVal sourceUrl As String) As Boolean
    Dim urlLower As String
    urlLower = LCase$(Trim$(sourceUrl))

    IsMaintenanceItemsUrl = _
        (InStr(1, urlLower, "getbytitle('maintenanceitems')", vbTextCompare) > 0) Or _
        (InStr(1, urlLower, "/lists/maintenanceitems/", vbTextCompare) > 0)
End Function

Private Function AppendQuery(ByVal url As String, ByVal queryText As String) As String
    If InStr(1, url, "?", vbTextCompare) > 0 Then
        AppendQuery = url & "&" & queryText
    Else
        AppendQuery = url & "?" & queryText
    End If
End Function

Private Function NormalizeSourceUrl(ByVal rawUrl As String) As String
    Dim sourceUrl As String
    sourceUrl = Trim$(rawUrl)
    If Len(sourceUrl) = 0 Then Exit Function

    If InStr(1, sourceUrl, "/_api/", vbTextCompare) > 0 Then
        NormalizeSourceUrl = sourceUrl
        Exit Function
    End If

    Dim posLists As Long
    posLists = InStr(1, sourceUrl, "/Lists/", vbTextCompare)
    If posLists = 0 Then
        NormalizeSourceUrl = sourceUrl
        Exit Function
    End If

    Dim listNameStart As Long
    listNameStart = posLists + Len("/Lists/")

    Dim listNameEnd As Long
    listNameEnd = InStr(listNameStart, sourceUrl, "/", vbTextCompare)
    If listNameEnd = 0 Then
        listNameEnd = Len(sourceUrl) + 1
    End If

    Dim listToken As String
    listToken = Mid$(sourceUrl, listNameStart, listNameEnd - listNameStart)

    Dim siteRoot As String
    siteRoot = Left$(sourceUrl, posLists - 1)

    Dim listName As String
    listName = Replace(DecodeListToken(listToken), "'", "''")

    NormalizeSourceUrl = siteRoot & "/_api/web/lists/getbytitle('" & listName & "')/items"
End Function

Private Function DecodeListToken(ByVal token As String) As String
    Dim out As String
    out = token
    out = Replace(out, "%20", " ")
    out = Replace(out, "%2D", "-")
    out = Replace(out, "%2d", "-")
    out = Replace(out, "%5F", "_")
    out = Replace(out, "%5f", "_")
    out = Replace(out, "%27", "'")
    DecodeListToken = out
End Function

Private Function ExtractItemsFromResponse(ByVal root As Object) As Collection
    Dim out As New Collection

    If root Is Nothing Then
        Set ExtractItemsFromResponse = out
        Exit Function
    End If

    Dim dataObj As Object
    Set dataObj = root
    If TypeName(root) = "Dictionary" Then
        If HasDictKey(root, "d") Then
            If IsObject(root("d")) Then
                Set dataObj = root("d")
            End If
        End If
    End If

    Select Case TypeName(dataObj)
        Case "Dictionary"
            If HasDictKey(dataObj, "results") Then
                AppendCollection out, ToCollection(dataObj("results"))
            ElseIf HasDictKey(dataObj, "value") Then
                AppendCollection out, ToCollection(dataObj("value"))
            Else
                out.Add dataObj
            End If
        Case "Collection"
            AppendCollection out, dataObj
    End Select

    Set ExtractItemsFromResponse = out
End Function

Private Function ExtractNextLink(ByVal root As Object) As String
    If TypeName(root) <> "Dictionary" Then Exit Function

    If HasDictKey(root, "@odata.nextLink") Then
        ExtractNextLink = CStr(root("@odata.nextLink"))
        Exit Function
    End If
    If HasDictKey(root, "odata.nextLink") Then
        ExtractNextLink = CStr(root("odata.nextLink"))
        Exit Function
    End If
    If HasDictKey(root, "__next") Then
        ExtractNextLink = CStr(root("__next"))
        Exit Function
    End If

    If HasDictKey(root, "d") Then
        Dim d As Object
        Set d = root("d")
        If TypeName(d) = "Dictionary" Then
            If HasDictKey(d, "__next") Then
                ExtractNextLink = CStr(d("__next"))
            ElseIf HasDictKey(d, "@odata.nextLink") Then
                ExtractNextLink = CStr(d("@odata.nextLink"))
            ElseIf HasDictKey(d, "odata.nextLink") Then
                ExtractNextLink = CStr(d("odata.nextLink"))
            End If
        End If
    End If
End Function

Private Function ResolveNextUrl(ByVal nextLink As String, ByVal currentUrl As String) As String
    Dim url As String
    url = Trim$(nextLink)
    If Len(url) = 0 Then Exit Function

    If LCase$(Left$(url, 4)) = "http" Then
        ResolveNextUrl = url
        Exit Function
    End If

    Dim schemePos As Long
    schemePos = InStr(1, currentUrl, "://", vbTextCompare)
    If schemePos = 0 Then
        ResolveNextUrl = url
        Exit Function
    End If

    Dim hostStart As Long
    hostStart = schemePos + 3

    Dim pathStart As Long
    pathStart = InStr(hostStart, currentUrl, "/", vbTextCompare)

    Dim hostRoot As String
    If pathStart = 0 Then
        hostRoot = currentUrl
    Else
        hostRoot = Left$(currentUrl, pathStart - 1)
    End If

    If Left$(url, 1) = "/" Then
        ResolveNextUrl = hostRoot & url
    Else
        ResolveNextUrl = hostRoot & "/" & url
    End If
End Function

Private Function BuildNormalizedKeyIndex(ByVal dict As Object) As Object
    Dim out As Object
    Set out = CreateObject("Scripting.Dictionary")
    out.CompareMode = vbTextCompare

    If TypeName(dict) <> "Dictionary" Then
        Set BuildNormalizedKeyIndex = out
        Exit Function
    End If

    Dim k As Variant
    For Each k In dict.Keys
        Dim raw As String
        raw = CStr(k)

        Dim normalized As String
        normalized = NormalizeFieldName(raw)

        If Len(normalized) > 0 Then
            If Not out.Exists(normalized) Then out.Add normalized, raw
        End If

        If IsObject(dict(k)) Then
            AddNormalizedNestedKeys out, raw, dict(k)
        End If
    Next k

    Set BuildNormalizedKeyIndex = out
End Function

Private Sub AddNormalizedNestedKeys(ByVal indexMap As Object, ByVal parentKey As String, ByVal node As Object)
    If indexMap Is Nothing Then Exit Sub
    If node Is Nothing Then Exit Sub

    If TypeName(node) <> "Dictionary" Then Exit Sub

    Dim child As Variant
    For Each child In node.Keys
        Dim childKey As String
        childKey = CStr(child)

        If Left$(childKey, 2) <> "__" Then
            Dim path As String
            path = parentKey & "/" & childKey

            Dim normalizedChild As String
            normalizedChild = NormalizeFieldName(childKey)
            If Len(normalizedChild) > 0 Then
                If Not indexMap.Exists(normalizedChild) Then indexMap.Add normalizedChild, path
            End If

            Dim normalizedPath As String
            normalizedPath = NormalizeFieldName(path)
            If Len(normalizedPath) > 0 Then
                If Not indexMap.Exists(normalizedPath) Then indexMap.Add normalizedPath, path
            End If

            If IsObject(node(child)) Then
                AddNormalizedNestedKeys indexMap, path, node(child)
            End If
        End If
    Next child
End Sub

Private Function ResolveSourceKey(ByVal targetHeader As String, ByVal aliasMap As Object, ByVal normalizedIndex As Object) As String
    Dim normalizedTarget As String
    normalizedTarget = NormalizeFieldName(targetHeader)

    If Not aliasMap Is Nothing Then
        If aliasMap.Exists(targetHeader) Then
            Dim aliases As Variant
            aliases = aliasMap(targetHeader)

            Dim i As Long
            For i = LBound(aliases) To UBound(aliases)
                Dim candidate As String
                candidate = NormalizeFieldName(CStr(aliases(i)))
                If Len(candidate) > 0 And normalizedIndex.Exists(candidate) Then
                    ResolveSourceKey = CStr(normalizedIndex(candidate))
                    Exit Function
                End If
            Next i
        End If
    End If

    If normalizedIndex.Exists(normalizedTarget) Then
        ResolveSourceKey = CStr(normalizedIndex(normalizedTarget))
        Exit Function
    End If
End Function

Private Function TryGetItemValue(ByVal item As Object, ByVal sourceKey As String, ByRef outValue As Variant) As Boolean
    If item Is Nothing Then Exit Function

    Dim keyPath As String
    keyPath = Trim$(sourceKey)
    If Len(keyPath) = 0 Then Exit Function

    If TypeName(item) = "Dictionary" Then
        If HasDictKey(item, keyPath) Then
            If IsObject(item(keyPath)) Then
                outValue = ExtractSharePointObjectValue(item(keyPath))
            Else
                outValue = item(keyPath)
            End If
            TryGetItemValue = True
            Exit Function
        End If
    End If

    keyPath = Replace(keyPath, ".", "/")
    If InStr(1, keyPath, "/", vbBinaryCompare) = 0 Then Exit Function

    Dim parts() As String
    parts = Split(keyPath, "/")

    Dim current As Object
    Set current = item

    Dim i As Long
    For i = LBound(parts) To UBound(parts)
        Dim part As String
        part = Trim$(parts(i))
        If Len(part) = 0 Then Exit Function

        If TypeName(current) <> "Dictionary" Then Exit Function
        If Not HasDictKey(current, part) Then Exit Function

        If i = UBound(parts) Then
            If IsObject(current(part)) Then
                outValue = ExtractSharePointObjectValue(current(part))
            Else
                outValue = current(part)
            End If
            TryGetItemValue = True
            Exit Function
        End If

        If Not IsObject(current(part)) Then Exit Function
        Set current = current(part)
    Next i
End Function

Private Function NormalizeFieldName(ByVal text As String) As String
    Dim work As String
    Dim i As Long
    Dim ch As String
    Dim out As String

    work = LCase$(Trim$(text))
    work = Replace(work, "_x0020_", "_")
    work = Replace(work, "_x005f_", "_")
    work = Replace(work, "_x002d_", "-")
    work = Replace(work, "_x0028_", "(")
    work = Replace(work, "_x0029_", ")")

    ' Keep tokens readable before stripping non-alnum.
    work = Replace(work, " x0020 ", " ")
    work = Replace(work, "x0020", vbNullString)

    For i = 1 To Len(work)
        ch = Mid$(work, i, 1)
        Select Case AscW(ch)
            Case 48 To 57, 65 To 90, 97 To 122
                out = out & LCase$(ch)
        End Select
    Next i

    NormalizeFieldName = out
End Function

Private Function CoerceSharePointValue(ByVal v As Variant) As Variant
    If IsObject(v) Then
        Dim objValue As Variant
        objValue = ExtractSharePointObjectValue(v)

        If IsObject(objValue) Then
            CoerceSharePointValue = vbNullString
        ElseIf IsNull(objValue) Or IsEmpty(objValue) Then
            CoerceSharePointValue = vbNullString
        Else
            CoerceSharePointValue = CoerceSharePointValue(objValue)
        End If
        Exit Function
    End If

    If IsNull(v) Or IsEmpty(v) Then
        CoerceSharePointValue = vbNullString
        Exit Function
    End If

    If VarType(v) = vbString Then
        Dim s As String
        s = Trim$(CStr(v))

        If Len(s) = 0 Then
            CoerceSharePointValue = vbNullString
            Exit Function
        End If

        If Left$(s, 6) = "/Date(" Then
            CoerceSharePointValue = ParseODataDate(s)
            Exit Function
        End If

        Dim parsedDate As Date
        If TryParseIsoDateTime(s, parsedDate) Then
            CoerceSharePointValue = parsedDate
            Exit Function
        End If

        CoerceSharePointValue = s
        Exit Function
    End If

    CoerceSharePointValue = v
End Function

Private Function ExtractSharePointObjectValue(ByVal obj As Object) As Variant
    On Error GoTo Fallback

    Select Case TypeName(obj)
        Case "Dictionary"
            If HasDictKey(obj, "Value") Then
                If IsObject(obj("Value")) Then
                    ExtractSharePointObjectValue = ExtractSharePointObjectValue(obj("Value"))
                Else
                    ExtractSharePointObjectValue = obj("Value")
                End If
                Exit Function
            End If
            If HasDictKey(obj, "Label") Then
                If IsObject(obj("Label")) Then
                    ExtractSharePointObjectValue = ExtractSharePointObjectValue(obj("Label"))
                Else
                    ExtractSharePointObjectValue = obj("Label")
                End If
                Exit Function
            End If
            If HasDictKey(obj, "Title") Then
                If IsObject(obj("Title")) Then
                    ExtractSharePointObjectValue = ExtractSharePointObjectValue(obj("Title"))
                Else
                    ExtractSharePointObjectValue = obj("Title")
                End If
                Exit Function
            End If
            If HasDictKey(obj, "LookupValue") Then
                If IsObject(obj("LookupValue")) Then
                    ExtractSharePointObjectValue = ExtractSharePointObjectValue(obj("LookupValue"))
                Else
                    ExtractSharePointObjectValue = obj("LookupValue")
                End If
                Exit Function
            End If
            If HasDictKey(obj, "Name") Then
                If IsObject(obj("Name")) Then
                    ExtractSharePointObjectValue = ExtractSharePointObjectValue(obj("Name"))
                Else
                    ExtractSharePointObjectValue = obj("Name")
                End If
                Exit Function
            End If
            If HasDictKey(obj, "results") Then
                If IsObject(obj("results")) Then
                    ExtractSharePointObjectValue = JoinSharePointCollectionValues(obj("results"))
                Else
                    ExtractSharePointObjectValue = obj("results")
                End If
                Exit Function
            End If

            Dim k As Variant
            For Each k In obj.Keys
                If Left$(CStr(k), 2) <> "__" Then
                    If Not IsObject(obj(k)) Then
                        ExtractSharePointObjectValue = obj(k)
                        Exit Function
                    Else
                        Dim nested As Variant
                        nested = ExtractSharePointObjectValue(obj(k))
                        If Not IsObject(nested) Then
                            If Not IsEmpty(nested) Then
                                ExtractSharePointObjectValue = nested
                                Exit Function
                            End If
                        End If
                    End If
                End If
            Next k

        Case "Collection"
            ExtractSharePointObjectValue = JoinSharePointCollectionValues(obj)
            Exit Function
    End Select

Fallback:
End Function

Private Function JoinSharePointCollectionValues(ByVal items As Object) As String
    On Error GoTo FailJoin

    Dim i As Long
    Dim piece As String
    Dim joined As String

    For i = 1 To items.Count
        Dim itemValue As Variant
        If IsObject(items(i)) Then
            itemValue = ExtractSharePointObjectValue(items(i))
        Else
            itemValue = items(i)
        End If

        If IsObject(itemValue) Then
            itemValue = ExtractSharePointObjectValue(itemValue)
        End If

        If Not IsObject(itemValue) Then
            piece = Trim$(CStr(itemValue))
            If Len(piece) > 0 Then
                If Len(joined) = 0 Then
                    joined = piece
                Else
                    joined = joined & "; " & piece
                End If
            End If
        End If
    Next i

    JoinSharePointCollectionValues = joined
    Exit Function

FailJoin:
    JoinSharePointCollectionValues = vbNullString
End Function

Private Function ParseODataDate(ByVal dateText As String) As Variant
    On Error GoTo Fallback

    Dim p1 As Long
    Dim p2 As Long
    Dim ms As Double

    p1 = InStr(1, dateText, "(")
    p2 = InStr(1, dateText, ")")
    If p1 > 0 And p2 > p1 Then
        ms = CDbl(Val(Mid$(dateText, p1 + 1, p2 - p1 - 1)))
        ParseODataDate = CDate(#1/1/1970# + (ms / 86400000#))
        Exit Function
    End If

Fallback:
    ParseODataDate = dateText
End Function

Private Function TryParseIsoDateTime(ByVal dateText As String, ByRef outDate As Date) As Boolean
    On Error GoTo Fail

    If Len(dateText) < 10 Then Exit Function
    If Mid$(dateText, 5, 1) <> "-" Or Mid$(dateText, 8, 1) <> "-" Then Exit Function

    Dim yyyy As Long
    Dim mm As Long
    Dim dd As Long

    yyyy = CLng(Left$(dateText, 4))
    mm = CLng(Mid$(dateText, 6, 2))
    dd = CLng(Mid$(dateText, 9, 2))

    outDate = DateSerial(yyyy, mm, dd)

    If Len(dateText) >= 19 Then
        If Mid$(dateText, 11, 1) = "T" Or Mid$(dateText, 11, 1) = " " Then
            Dim hh As Long
            Dim nn As Long
            Dim ss As Long

            hh = CLng(Mid$(dateText, 12, 2))
            nn = CLng(Mid$(dateText, 15, 2))
            ss = CLng(Mid$(dateText, 18, 2))

            outDate = outDate + TimeSerial(hh, nn, ss)
        End If
    End If

    TryParseIsoDateTime = True
    Exit Function

Fail:
    TryParseIsoDateTime = False
End Function

Private Function GetSharePointAuthHeader() As String
    Dim token As String
    token = Trim$(ReadCredentialSecretMulti(GetSharePointCredentialTarget()))

    If Len(token) = 0 Then token = GetSharePointTokenFallback()
    If Len(token) = 0 Then
        If CFG_SHAREPOINT_ALLOW_NO_TOKEN Then
            GetSharePointAuthHeader = vbNullString
            Exit Function
        End If
        Err.Raise 2002, , "SharePoint token mangler. Saet CFG_SHAREPOINT_CREDENTIAL_TARGET eller CFG_SHAREPOINT_TOKEN_FALLBACK i modSharePointImport.bas, eller saet CFG_SHAREPOINT_ALLOW_NO_TOKEN=True."
    End If

    If LCase$(Left$(token, 7)) = "bearer " Then
        GetSharePointAuthHeader = token
    Else
        GetSharePointAuthHeader = "Bearer " & token
    End If
End Function

Private Function ReadCredentialSecretMulti(ByVal target As String) As String
    Dim cleanTarget As String
    cleanTarget = Trim$(target)
    If Len(cleanTarget) = 0 Then Exit Function

    Dim candidates As Collection
    Set candidates = New Collection
    AddCandidateTarget candidates, cleanTarget

    If InStr(1, cleanTarget, "LegacyGeneric:target=", vbTextCompare) = 0 Then
        AddCandidateTarget candidates, "LegacyGeneric:target=" & cleanTarget
    End If

    Dim i As Long
    For i = 1 To candidates.Count
        Dim secret As String
        secret = Trim$(ReadCredentialSecret(CStr(candidates(i))))
        If Len(secret) > 0 Then
            ReadCredentialSecretMulti = secret
            Exit Function
        End If
    Next i
End Function

Private Sub AddCandidateTarget(ByVal candidates As Collection, ByVal value As String)
    Dim candidate As String
    candidate = Trim$(value)
    If Len(candidate) = 0 Then Exit Sub

    Dim i As Long
    For i = 1 To candidates.Count
        If StrComp(CStr(candidates(i)), candidate, vbTextCompare) = 0 Then Exit Sub
    Next i

    candidates.Add candidate
End Sub

Private Function ReadCredentialSecret(ByVal target As String) As String
    If Len(Trim$(target)) = 0 Then Exit Function

    On Error GoTo FailRead

#If VBA7 Then
    Dim pCred As LongPtr
#Else
    Dim pCred As Long
#End If

    If CredReadW(StrPtr(target), CRED_TYPE_GENERIC, 0, pCred) = 0 Then Exit Function

    Dim cred As CREDENTIALW
    CopyMemory cred, ByVal pCred, LenB(cred)

    If cred.CredentialBlobSize > 0 Then
        ReadCredentialSecret = PtrToUnicodeString(cred.CredentialBlob, cred.CredentialBlobSize)
    End If

    CredFree pCred
    Exit Function

FailRead:
    If pCred <> 0 Then CredFree pCred
End Function

#If VBA7 Then
Private Function PtrToUnicodeString(ByVal valuePtr As LongPtr, ByVal byteLen As Long) As String
#Else
Private Function PtrToUnicodeString(ByVal valuePtr As Long, ByVal byteLen As Long) As String
#End If
    If valuePtr = 0 Or byteLen <= 0 Then Exit Function

    Dim charLen As Long
    charLen = byteLen \ 2
    If charLen <= 0 Then Exit Function

    Dim s As String
    s = String$(charLen, vbNullChar)
    CopyMemory ByVal StrPtr(s), ByVal valuePtr, byteLen

    If Len(s) > 0 Then
        If Right$(s, 1) = vbNullChar Then s = Left$(s, Len(s) - 1)
    End If

    PtrToUnicodeString = s
End Function

Private Function GetSharePointCredentialTarget() As String
    Dim configuredTarget As String
    configuredTarget = Trim$(CFG_SHAREPOINT_CREDENTIAL_TARGET)
    If Len(configuredTarget) > 0 Then
        GetSharePointCredentialTarget = configuredTarget
        Exit Function
    End If

    Dim userInitials As String
    userInitials = UCase$(Trim$(Environ$("USERNAME")))
    If Len(userInitials) = 0 Then Exit Function

    GetSharePointCredentialTarget = CFG_SHAREPOINT_CREDENTIAL_PREFIX & userInitials & CFG_SHAREPOINT_CREDENTIAL_SUFFIX
End Function

Private Function GetSharePointTokenFallback() As String
    GetSharePointTokenFallback = Trim$(CFG_SHAREPOINT_TOKEN_FALLBACK)
End Function

Private Function GetSharePointPlansUrl() As String
    GetSharePointPlansUrl = modEnvironment.GetListUrl(CFG_LIST_PLANS)
End Function

Private Function GetSharePointItemsUrl() As String
    GetSharePointItemsUrl = modEnvironment.GetListUrl(CFG_LIST_ITEMS)
End Function

Private Function GetSharePointTlhUrl() As String
    GetSharePointTlhUrl = modEnvironment.GetListUrl(CFG_LIST_TLH)
End Function

Private Function GetSharePointTlUrl() As String
    GetSharePointTlUrl = modEnvironment.GetListUrl(CFG_LIST_TL)
End Function

Private Function GetSharePointTlhFilter() As String
    GetSharePointTlhFilter = Trim$(CFG_SHAREPOINT_TLH_FILTER)
End Function

Private Function GetSharePointTlFilter() As String
    GetSharePointTlFilter = Trim$(CFG_SHAREPOINT_TL_FILTER)
End Function

Public Function GetSharePointAuthHeaderForSync() As String
    GetSharePointAuthHeaderForSync = GetSharePointAuthHeader()
End Function

Public Function GetSharePointPlansItemsUrlForSync() As String
    GetSharePointPlansItemsUrlForSync = GetSharePointPlansUrl()
End Function

Public Function GetSharePointItemsItemsUrlForSync() As String
    GetSharePointItemsItemsUrlForSync = GetSharePointItemsUrl()
End Function

Public Function GetSharePointTlItemsUrlForSync() As String
    GetSharePointTlItemsUrlForSync = GetSharePointTlUrl()
End Function

Private Function DefaultHeadersPlans() As Variant
    DefaultHeadersPlans = Array( _
    "Id", "PlanID", "Status", PLAN_SELECTION_HEADER, "PlanType", "PlantsInitial", "Title", _
    "Cycle", "Unit", "PlannedDate", "SortFieldId", "SAPNum")
End Function

Private Function DefaultHeadersItems() As Variant
    DefaultHeadersItems = Array( _
    "Id", "MaintenancePlanNo", "ItemID", "SAPNumber", "Title", "ItemDescription", _
    "FunctionalLocation", "ObjectList", "UserStatus", "NonFlowUserStatus", "Priority", _
    "MainWorkCenterId", "MaintenanceActivityTypeId", "OrderType", "Revision", _
    "InitialOrstedResponsible", "SCEqFL", "SCEqOL")
End Function

Private Function DefaultHeadersTlh() As Variant
    DefaultHeadersTlh = Array( _
    "PlanID", "ItemID", "TaskID", "Title", "PlantInitial", "Work Center", "Profile", _
        "Status_Code", "TL_Group_Number", "TL_Counter", "Status_Message")
End Function

Private Function DefaultHeadersTl() As Variant
    DefaultHeadersTl = Array( _
    "Id", "MaintenancePlanIDId", "MaintenanceItemNoId", "TaskID", "TaskItemID", "SAPGroupNumber", _
    "Title", "Index", "WorkCtr", "Ctrl", "OperationShortText", _
    "Work", "Num", "Duration", "Vendor", "VendorID", "Price", "Currency", _
    "CostElem", "LongText", "Materials", "PlantInitial", _
    "StandartTasklistInitials", "StandardTaskItemID")
End Function

Private Function BuildAliasMapPlans() As Object
    Dim map As Object
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "Id", Array("FieldValuesAsText/ID", "ID", "Id")
    map.Add "Title", Array("Title", "FieldValuesAsText/Title")
    map.Add "Status", Array("Status", "FieldValuesAsText/Status")
    map.Add "Cycle", Array("Cycle", "FieldValuesAsText/Cycle")
    map.Add "Unit", Array("Unit", "FieldValuesAsText/Unit")
    map.Add "PlannedDate", Array("PlannedDate", "FieldValuesAsText/PlannedDate")
    map.Add "PlantsInitial", Array("PlantsInitial", "FieldValuesAsText/PlantsInitial")
    map.Add "SortFieldId", Array("SortFieldId", "SortField/Id", "FieldValuesAsText/SortField", "SortField")
    map.Add "PlanID", Array("PlanID", "FieldValuesAsText/PlanID")
    map.Add "PlanType", Array("PlanType", "FieldValuesAsText/PlanType")
    map.Add "SAPNum", Array("SAPNum", "FieldValuesAsText/SAPNum")

    Set BuildAliasMapPlans = map
End Function

Private Function BuildAliasMapItems() As Object
    Dim map As Object
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "Id", Array("Id", "ID", "FieldValuesAsText/ID")
    map.Add "MaintenancePlanNo", Array("FieldValuesAsText/MaintenancePlanNo", "MaintenancePlanNo", "MaintenancePlanNoId")
    map.Add "ItemID", Array("ItemID", "FieldValuesAsText/ItemID")
    map.Add "SAPNumber", Array("SAPNumber", "FieldValuesAsText/SAPNumber")
    map.Add "Title", Array("Title", "FieldValuesAsText/Title")
    map.Add "ItemDescription", Array("ItemDescription", "FieldValuesAsText/ItemDescription")
    map.Add "FunctionalLocation", Array("FunctionalLocation", "FieldValuesAsText/FunctionalLocation")
    map.Add "ObjectList", Array("ObjectList", "FieldValuesAsText/ObjectList")
    map.Add "UserStatus", Array("UserStatus", "FieldValuesAsText/UserStatus")
    map.Add "NonFlowUserStatus", Array("NonFlowUserStatus", "FieldValuesAsText/NonFlowUserStatus")
    map.Add "Priority", Array("Priority", "FieldValuesAsText/Priority")
    map.Add "MainWorkCenterId", Array("MainWorkCenter/Title", "MainWorkCenter", "FieldValuesAsText/MainWorkCenter", "MainWorkCenterId")
    map.Add "MaintenanceActivityTypeId", Array("MaintenanceActivityType/Title", "MaintenanceActivityType", "FieldValuesAsText/MaintenanceActivityType", "MaintenanceActivityTypeId")
    map.Add "OrderType", Array("OrderType", "FieldValuesAsText/OrderType")
    map.Add "Revision", Array("Revision", "FieldValuesAsText/Revision")
    map.Add "InitialOrstedResponsible", Array("InitialOrstedResponsible", "FieldValuesAsText/InitialOrstedResponsible")
    map.Add "SCEqFL", Array("SCEqFL", "FieldValuesAsText/SCEqFL")
    map.Add "SCEqOL", Array("SCEqOL", "FieldValuesAsText/SCEqOL")

    Set BuildAliasMapItems = map
End Function

Private Function BuildAliasMapTlh() As Object
    Dim map As Object
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "PlanID", Array("PlanID", "MaintenancePlanIDId", "FieldValuesAsText/MaintenancePlanID", "MaintenancePlanNoId", "FieldValuesAsText/MaintenancePlanNo")
    map.Add "ItemID", Array("ItemID", "FieldValuesAsText/ItemID", "FieldValuesAsText/MaintenanceItemNo", "MaintenanceItemNoId", "TaskItemID")
    map.Add "TaskID", Array("TaskID", "FieldValuesAsText/TaskID", "SAPGroupNumber", "FieldValuesAsText/SAPGroupNumber")
    map.Add "Title", Array("Title", "Description", "KTEXT", "FieldValuesAsText/Title")
    map.Add "PlantInitial", Array("PlantInitial", "Plant_Name", "PlantName", "FieldValuesAsText/PlantInitial")
    map.Add "Work Center", Array("WorkCtr", "Work_Center", "WorkCenter", "ARBPL", "FieldValuesAsText/WorkCtr")
    map.Add "Profile", Array("StandartTasklistInitials", "FieldValuesAsText/StandartTasklistInitials", "Profile", "FieldValuesAsText/Profile")
    map.Add "Status_Code", Array("Status_Code", "StatusCode")
    map.Add "TL_Group_Number", Array("TL_Group_Number", "TLGroupNumber", "PLNNR", "SAP_Task_List_Number")
    map.Add "TL_Counter", Array("TL_Counter", "TLCounter", "PLNAL")
    map.Add "Status_Message", Array("Status_Message", "StatusMessage")

    Set BuildAliasMapTlh = map
End Function

Private Function BuildAliasMapTl() As Object
    Dim map As Object
    Set map = CreateObject("Scripting.Dictionary")
    map.CompareMode = vbTextCompare

    map.Add "Id", Array("Id", "ID", "FieldValuesAsText/ID")
    map.Add "Title", Array("Title", "FieldValuesAsText/Title")
    map.Add "Index", Array("Index", "FieldValuesAsText/Index")
    map.Add "WorkCtr", Array("WorkCtr", "FieldValuesAsText/WorkCtr")
    map.Add "Ctrl", Array("Ctrl", "FieldValuesAsText/Ctrl")
    map.Add "OperationShortText", Array("OperationShortText", "FieldValuesAsText/OperationShortText")
    map.Add "Work", Array("Work", "FieldValuesAsText/Work")
    map.Add "Num", Array("Num", "FieldValuesAsText/Num")
    map.Add "Duration", Array("Duration", "FieldValuesAsText/Duration")
    map.Add "Vendor", Array("Vendor", "FieldValuesAsText/Vendor")
    map.Add "VendorID", Array("VendorID", "FieldValuesAsText/VendorID")
    map.Add "Price", Array("Price", "FieldValuesAsText/Price")
    map.Add "Currency", Array("Currency", "FieldValuesAsText/Currency")
    map.Add "CostElem", Array("CostElem", "FieldValuesAsText/CostElem")
    map.Add "LongText", Array("LongText", "FieldValuesAsText/LongText")
    map.Add "Materials", Array("Materials", "FieldValuesAsText/Materials")
    map.Add "TaskID", Array("FieldValuesAsText/TaskID", "TaskID")
    map.Add "TaskItemID", Array("FieldValuesAsText/TaskItemID", "TaskItemID")
    map.Add "PlantInitial", Array("PlantInitial", "FieldValuesAsText/PlantInitial")
    map.Add "StandartTasklistInitials", Array("StandartTasklistInitials", "FieldValuesAsText/StandartTasklistInitials")
    map.Add "StandardTaskItemID", Array("StandardTaskItemID", "FieldValuesAsText/StandardTaskItemID")
    map.Add "MaintenanceItemNoId", Array("FieldValuesAsText/MaintenanceItemNo", "MaintenanceItemNoId")
    map.Add "MaintenancePlanIDId", Array("FieldValuesAsText/MaintenancePlanID", "MaintenancePlanIDId")
    map.Add "SAPGroupNumber", Array("FieldValuesAsText/SAPGroupNumber", "SAPGroupNumber", _
                                      "FieldValuesAsText/SAP_Task_List_Number", "SAP_Task_List_Number", _
                                      "FieldValuesAsText/SAPTaskList", "SAPTaskList", _
                                      "FieldValuesAsText/SAPTaskListNumber", "SAPTaskListNumber", _
                                      "FieldValuesAsText/SAP_x0020_Task_x0020_List", "SAP_x0020_Task_x0020_List")

    Set BuildAliasMapTl = map
End Function

Private Sub AppendCollection(ByVal destination As Collection, ByVal source As Collection)
    If destination Is Nothing Then Exit Sub
    If source Is Nothing Then Exit Sub

    Dim i As Long
    For i = 1 To source.Count
        destination.Add source(i)
    Next i
End Sub

Private Function ToCollection(ByVal value As Variant) As Collection
    Dim out As New Collection

    If IsObject(value) Then
        If TypeName(value) = "Collection" Then
            AppendCollection out, value
        ElseIf TypeName(value) = "Dictionary" Then
            out.Add value
        End If
    End If

    Set ToCollection = out
End Function

Private Function HasDictKey(ByVal dict As Object, ByVal keyName As String) As Boolean
    On Error Resume Next
    HasDictKey = dict.Exists(keyName)
    On Error GoTo 0
End Function

Private Function HeaderCount(ByVal headers As Variant) As Long
    On Error GoTo Fail
    HeaderCount = UBound(headers) - LBound(headers) + 1
    Exit Function
Fail:
    HeaderCount = 0
End Function

Private Function SafeRowCount(ByVal rows As Variant) As Long
    On Error GoTo Fail
    If IsEmpty(rows) Then Exit Function
    SafeRowCount = UBound(rows, 1)
    Exit Function
Fail:
    SafeRowCount = 0
End Function

Private Function CollectionCount(ByVal items As Collection) As Long
    If items Is Nothing Then Exit Function
    CollectionCount = items.Count
End Function
