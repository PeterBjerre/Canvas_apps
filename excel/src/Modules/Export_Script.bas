Option Explicit

Private mCombinedEtaActive As Boolean
Private mCombinedEtaStart As Double
Private mCombinedEtaBasePct As Long
Private mCombinedEtaSpanPct As Long

'===============================================================================
' Export_Script.bas
' SAP PM Maintenance Plan SPOOL - Export module
'
' Reads existing VH-plans from SAP and populates Excel worksheets.
' Data flow: SAP -> Excel (reverse of GUI_Script.bas)
'
' SAP Transactions used:
'   IP03 - Display Maintenance Plan
'   IP06 - Display Maintenance Item
'   IA05 - Display Task List (General Maintenance)
'
' Dependencies:
'   Attach_Session()           - defined in GUI_Script.bas
'   CreateGlobalDictionaries() - defined in GUI_Script.bas
'   objSess, objSBar           - public vars in GUI_Script.bas
'
' Long text export is NOT handled here - deferred to a separate issue.
'===============================================================================

Public Sub StartExport(Optional ByRef itemNumbers As Collection, _
                       Optional ByVal statusManagedExternally As Boolean = False, _
                       Optional ByVal statusBasePct As Long = 0, _
                       Optional ByVal statusSpanPct As Long = 100, _
                       Optional ByVal showCompletionMessage As Boolean = True)

    On Error GoTo EH

    ' Connect to SAP via GUI_Session (reads system from Setup sheet)
    Dim W_Ret As Boolean
    Dim ownsStatus As Boolean
    Dim itemSpanPct As Long
    Dim tasklistSpanPct As Long

    ownsStatus = Not statusManagedExternally
    statusBasePct = ClampProgressPct(statusBasePct)
    statusSpanPct = ClampProgressPct(statusSpanPct)
    If statusBasePct + statusSpanPct > 100 Then statusSpanPct = 100 - statusBasePct

    mCombinedEtaActive = True
    mCombinedEtaStart = Timer
    mCombinedEtaBasePct = statusBasePct
    mCombinedEtaSpanPct = statusSpanPct
    If mCombinedEtaSpanPct <= 0 Then mCombinedEtaSpanPct = 1

    If ownsStatus Then
        mdlExtractStatus.EnsureExtractStatusForm "Extract status"
        mdlExtractStatus.UpdateExtractStatus statusBasePct, "SAP extract: preparing... ETA calculating..."
    End If

    W_Ret = Attach_Session_Core()
    If Not W_Ret Then
        mdlExtractStatus.UpdateExtractStatus statusBasePct, "SAP extract: no active SAP session."
        GoTo CleanExit
    End If

    CreateGlobalDictionaries

    itemSpanPct = CLng(statusSpanPct * 0.55)
    If itemSpanPct < 0 Then itemSpanPct = 0
    If itemSpanPct > statusSpanPct Then itemSpanPct = statusSpanPct
    tasklistSpanPct = statusSpanPct - itemSpanPct

    ' Run the export sequence
    ExportItemExtract itemNumbers, statusBasePct, itemSpanPct
    ExportTL statusBasePct + itemSpanPct, tasklistSpanPct
'    ExportPlans

    objSess.EndTransaction

    mdlExtractStatus.FinishExtractStatus "SAP extract done."

    If showCompletionMessage Then
        MsgBox "Eksport afsluttet.", vbInformation + vbOKOnly
    End If

CleanExit:
    ResetCombinedEtaContext
    If ownsStatus Then mdlExtractStatus.CloseExtractStatus
    Exit Sub

EH:
    mdlExtractStatus.UpdateExtractStatus statusBasePct, "SAP extract failed: " & Err.Description
    ResetCombinedEtaContext
    If showCompletionMessage Then
        MsgBox "Eksport fejl: " & Err.Description, vbExclamation + vbOKOnly
    End If
    Resume CleanExit
End Sub

'===============================================================================
' ExportItemExtract
' Reads Item data from SAP (IP06) and writes all requested fields to Item Extract.
'
' Input:  Optional in-memory list of SAP item numbers. If not supplied, column A in Extract Data is used (from A4 until first blank).
' Output: Sheet Item Extract is recreated/cleared and filled with one row per item.
'===============================================================================
Public Sub ExportItemExtract(Optional ByRef itemNumbers As Collection, _
                             Optional ByVal statusBasePct As Long = 0, _
                             Optional ByVal statusSpanPct As Long = 50)

    Dim wsSource As Worksheet, wsOut As Worksheet, wsObj As Worksheet
    Dim outRow As Long, outObjRow As Long
    Dim itemNumber As String
    Dim tab2Pairs As String
    Dim itemsToExport As Collection
    Dim itemValue As Variant
    Dim totalItems As Long, processedItems As Long
    Dim phaseStart As Double

    Set wsOut = EnsureItemExtractSheet()
    Set wsObj = EnsureItemObjectsSheet()
    If wsOut Is Nothing Then Exit Sub
    If wsObj Is Nothing Then Exit Sub

    Set itemsToExport = BuildItemNumberList(itemNumbers)
    If itemsToExport Is Nothing Then Exit Sub
    If itemsToExport.Count = 0 Then Exit Sub

    totalItems = itemsToExport.Count
    processedItems = 0
    phaseStart = Timer
    ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedItems, totalItems, "Items", "Starting...", phaseStart

    If Not EnsureSapSession() Then Exit Sub
    On Error GoTo myerr

    NavigateToTransaction TX_IP06
    outRow = 2
    outObjRow = 2

    For Each itemValue In itemsToExport
        itemNumber = Trim$(CStr(itemValue))
        If itemNumber = "" Then GoTo NextItem

        processedItems = processedItems + 1
        ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedItems, totalItems, "Items", itemNumber, phaseStart

        objSess.FindById("wnd[0]/usr/ctxtRMIPM-WAPOS").Text = itemNumber
        objSess.FindById("wnd[0]").sendVKey 0

        wsOut.Cells(outRow, "A").Value = itemNumber
        wsOut.Cells(outRow, "B").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/txtRMIPM-PSTXT")
        wsOut.Cells(outRow, "C").Value = SafeGuiKey("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/cmbRMIPM-MPTYP")
        wsOut.Cells(outRow, "AA").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/ctxtRMIPM-WSTRA")

        ' Tab 1
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11").Select

        wsOut.Cells(outRow, "D").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_1:SAPLIWO1:0100/ctxtRIWO1-TPLNR")
        wsOut.Cells(outRow, "E").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_1:SAPLIWO1:0100/ctxtRIWO1-EQUNR")
        wsOut.Cells(outRow, "F").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-IWERK")
        wsOut.Cells(outRow, "G").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-AUART")
        wsOut.Cells(outRow, "H").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-ILART")
        wsOut.Cells(outRow, "I").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-GEWERK")
        wsOut.Cells(outRow, "J").Value = SafeGuiKey("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/cmbRMIPM-PRIOK")
        wsOut.Cells(outRow, "K").Value = SafeGuiSelected("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/chkMPOS-NO_AUFRELKZ")
        wsOut.Cells(outRow, "L").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNTY")
        wsOut.Cells(outRow, "M").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNNR")
        wsOut.Cells(outRow, "N").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNAL")
        wsOut.Cells(outRow, "O").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_ITEM_2:SAPLIWP3:0500/subSUBSCREEN_MLAN_ITEM:SAPLIWP3:6006/txtRMIPM-WARPL")

        ' Tab 2 - collect column 2 and 4 values from the 8023 container
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12").Select
        tab2Pairs = ExtractTab2ObjectPairs()
        WriteItemObjectRows wsObj, outObjRow, itemNumber, tab2Pairs

        ' Tab 4
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17").Select
        wsOut.Cells(outRow, "P").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_STATUS")
        wsOut.Cells(outRow, "Q").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_NON_FLOW_USER_STAT")
        wsOut.Cells(outRow, "R").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtGV_REVNR")
        wsOut.Cells(outRow, "S").Value = SafeGuiSelected("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/radGV_WCM_YES")
        wsOut.Cells(outRow, "T").Value = SafeGuiSelected("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/radGV_WCM_NO")
        wsOut.Cells(outRow, "U").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/txtCI_MPOS-ZZNREVY")
        wsOut.Cells(outRow, "V").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/ctxtCI_MPOS-ZZNREVM")
        wsOut.Cells(outRow, "W").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/txtCI_MPOS-ZZLREVY")
        wsOut.Cells(outRow, "X").Value = SafeGuiText("wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/txtCI_MPOS-ZZREVBY")
        wsOut.Cells(outRow, "Z").Value = ReadItemLongText()
        wsOut.Cells(outRow, "Y").Value = "Exporteret"

        outRow = outRow + 1
        NavigateToTransaction TX_IP06

NextItem:
    Next itemValue

    ReportExtractPhaseProgress statusBasePct, statusSpanPct, totalItems, totalItems, "Items", "Done", phaseStart

    wsOut.Columns("A:AA").VerticalAlignment = xlVAlignTop
    wsObj.Columns("A:C").VerticalAlignment = xlVAlignTop
    wsOut.Columns("A:AA").EntireColumn.AutoFit
    wsObj.Columns("A:C").EntireColumn.AutoFit
    Exit Sub

myerr:
    ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedItems, totalItems, "Items", "Error on " & itemNumber, phaseStart
    If Not wsOut Is Nothing Then
        wsOut.Cells(outRow, "A").Value = itemNumber
        wsOut.Cells(outRow, "Y").Value = "FEJL: " & Err.Description
        wsOut.Cells(outRow, "Z").Value = ""
        outRow = outRow + 1
    End If
    NavigateToTransaction TX_IP06
    Resume NextItem

End Sub

Private Function BuildItemNumberList(Optional ByRef itemNumbers As Collection) As Collection
    Dim wsSource As Worksheet
    Dim rowNo As Long
    Dim sourceItem As Variant
    Dim itemNumber As String
    Dim result As Collection
    Dim seen As Object

    Set result = New Collection
    Set seen = CreateObject("Scripting.Dictionary")

    If Not itemNumbers Is Nothing Then
        For Each sourceItem In itemNumbers
            itemNumber = Trim$(CStr(sourceItem))
            If Len(itemNumber) > 0 Then
                If Not seen.Exists(itemNumber) Then
                    seen.Add itemNumber, True
                    result.Add itemNumber
                End If
            End If
        Next sourceItem
        Set BuildItemNumberList = result
        Exit Function
    End If

    On Error Resume Next
    Set wsSource = Worksheets(WS_EXTRACT_DATA)
    On Error GoTo 0
    If wsSource Is Nothing Then
        Set BuildItemNumberList = result
        Exit Function
    End If

    For rowNo = 4 To wsSource.Rows.Count
        itemNumber = Trim$(CStr(wsSource.Cells(rowNo, "A").Value))
        If itemNumber = "" Then Exit For
        If Not seen.Exists(itemNumber) Then
            seen.Add itemNumber, True
            result.Add itemNumber
        End If
    Next rowNo

    Set BuildItemNumberList = result
End Function

'===============================================================================
' ExportPlans
' Reads Maintenance Plans from SAP (IP03) into the Maintenance_Plans worksheet.
'
' Input:  Column I in Maintenance_Plans contains the SAP plan numbers to export.
' Output: Columns B, C, D, E, F, G are populated from SAP.
'===============================================================================
Public Sub ExportPlans()

    Dim ws As Worksheet
    Dim i As Long, lastRow As Long
    Dim planNumber As String

    Set ws = Worksheets(WS_MAINTENANCE_PLANS)
    ws.Activate
    If Not EnsureSapSession() Then Exit Sub
    On Error GoTo myerr

    ' Navigate to IP03
    NavigateToTransaction TX_IP03

    lastRow = ws.Cells(ws.Rows.Count, "I").End(xlUp).Row

    For i = 3 To lastRow
        planNumber = Trim(ws.Cells(i, "I").Value)
        If planNumber = "" Then GoTo NextPlan

        ' Enter plan number and open
        objSess.FindById("wnd[0]/usr/ctxtRMIPM-WARPL").Text = planNumber
        objSess.FindById("wnd[0]").sendVKey 0

        ' --- Tab 1: Cycle ---
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01").Select

        ' Plan description (header)
        ws.Cells(i, "B").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6000/txtRMIPM-WPTXT").Text

        ' Cycle value and unit
        ws.Cells(i, "C").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/txtRMIPM-ZYKL1").Text
        ws.Cells(i, "D").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/ctxtRMIPM-ZEIEH").Text

        ' --- Tab 2: Scheduling Parameters ---
        objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02").Select

        ' FCD / Horizon
        ws.Cells(i, "E").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/txtRMIPM-HORIZ").Text
        ' Horizon qualifier (unit, e.g. YR)
        ws.Cells(i, "F").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/ctxtRMIPM-HORIZ_QUALIFIER").Text
        ' Start date
        ws.Cells(i, "G").Value = objSess.FindById("wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/ctxtRMIPM-STADT").Text

        ' Mark as exported
        SetRowStatus ws, i, "K", "Exporteret"

        ' Return to IP03 entry screen for next plan
        NavigateToTransaction TX_IP03

NextPlan:
        i = i ' label target - no-op
    Next i

    Exit Sub

myerr:
    SetRowStatus ws, i, "K", "FEJL: " & Err.Description
    Resume NextPlan

End Sub


'===============================================================================
' ExportTLH
' Reads Task List Headers from SAP (IA05 display) into Maintenance_TLH worksheet.
'
' Input:  Column H in Maintenance_TLH contains the SAP TL group numbers.
' Output: Columns C, D, E, F are populated from SAP (description, plant, WC, PC).
'===============================================================================
Public Sub ExportTLH()

    Dim ws As Worksheet
    Dim i As Long, lastRow As Long
    Dim tlGroup As String

    Set ws = Worksheets(WS_MAINTENANCE_TLH)
    ws.Activate
    If Not EnsureSapSession() Then Exit Sub
    On Error GoTo myerr

    ' Navigate to IA05 display
    NavigateToTransaction TX_IA05

    lastRow = ws.Cells(ws.Rows.Count, "H").End(xlUp).Row

    For i = 3 To lastRow
        tlGroup = Trim(ws.Cells(i, "H").Value)
        If tlGroup = "" Then GoTo NextTLH

        ' Enter TL group number (PLNNR) and counter from sheet
        objSess.FindById("wnd[0]/usr/ctxtRC271-PLNNR").Text = tlGroup
        objSess.FindById("wnd[0]/usr/ctxtRC271-PROFIDNETZ").Text = ws.Cells(i, "F").Value
        objSess.FindById("wnd[0]/usr/ctxtRC271-STTAG").Text = DEFAULT_SAP_DATE
        objSess.FindById("wnd[0]").sendVKey 0

        ' Read header fields
        ws.Cells(i, "C").Value = objSess.FindById("wnd[0]/usr/txtPLKOD-KTEXT").Text        ' Description
        ws.Cells(i, "E").Value = objSess.FindById("wnd[0]/usr/ctxtRCR01-ARBPL").Text       ' Work Center

        ' Plant: reverse lookup from PlantDict (value -> key)
        Dim plantKey As String
        plantKey = objSess.FindById("wnd[0]/usr/ctxtPLKOD-WERKS").Text
        ws.Cells(i, "D").Value = ReverseLookupPlant(plantKey)

        ' Store TL number and counter if not already present
        If ws.Cells(i, "H").Value = "" Then
            ws.Cells(i, "H").Value = objSess.FindById("wnd[0]/usr/ctxtPLKOD-PLNNR").Text
            ws.Cells(i, "I").Value = objSess.FindById("wnd[0]/usr/txtPLKOD-PLNAL").Text
        End If

        ' Mark as exported
        SetRowStatus ws, i, "G", "E"
        SetRowStatus ws, i, "J", "Exporteret"

        ' Return to IA05 entry screen
        NavigateToTransaction TX_IA05

NextTLH:
        i = i ' label target - no-op
    Next i

    Exit Sub

myerr:
    SetRowStatus ws, i, "J", "FEJL: " & Err.Description
    Resume NextTLH

End Sub

'===============================================================================
' ExportTL
' Reads Task List Operations and Materials from SAP (IA07 display)
' into a dedicated extract sheet with one row per operation.
'
' Input:  Task_LstGrp og GrpCr i Item Extract indeholder task list references.
' Output: Tasklist_Extract is recreated/cleared and filled with operation rows.
'===============================================================================
Public Sub ExportTL(Optional ByVal statusBasePct As Long = 50, _
                    Optional ByVal statusSpanPct As Long = 50)

    Dim wsSource As Worksheet, wsOut As Worksheet
    Dim wsComp As Worksheet, wsDocs As Worksheet, wsPack As Worksheet
    Dim i As Long, lastRow As Long, outRow As Long
    Dim outCompRow As Long, outDocRow As Long, outPackRow As Long
    Dim tlGroup As String, tlCounter As String, sourceKey As String
    Dim strategyValue As String
    Dim operations As Collection
    Dim op As Variant
    Dim matsByOp As Object, matData As Object
    Dim docsByOp As Object
    Dim docRows As Collection
    Dim wildcardDocs As Collection
    Dim lastOp As String, currentOp As String, nextOp As String
    Dim firstOpKey As String
    Dim idList As String, qtyList As String, uomList As String, descList As String
    Dim guard As Long
    Dim cTlGroup As Long, cTlCounter As Long, cStrategy As Long
    Dim opVisibleRows As Long
    Dim matPageMarker As String, matNextPageMarker As String
    Dim totalTasklists As Long, processedTasklists As Long
    Dim phaseStart As Double

    Set wsSource = Worksheets(WS_ITEM_EXTRACT)
    Set wsOut = EnsureTasklistExtractSheet()
    Set wsComp = EnsureTasklistComponentsSheet()
    Set wsDocs = EnsureTasklistAttachmentsSheet()
    Set wsPack = EnsureTasklistMaintPackSheet()
    If wsOut Is Nothing Then Exit Sub
    If wsComp Is Nothing Then Exit Sub
    If wsDocs Is Nothing Then Exit Sub
    If wsPack Is Nothing Then Exit Sub

    cTlGroup = FindHeaderIndex(wsSource, Array("Task_LstGrp", "RMIPM-PLNNR"))
    cTlCounter = FindHeaderIndex(wsSource, Array("GrpCr", "RMIPM-PLNAL"))
    cStrategy = FindHeaderIndex(wsSource, Array("Strategy", "RMIPM-WSTRA"))
    If cTlGroup = 0 Or cTlCounter = 0 Then
        Err.Raise 5, , "Raw_Item_Header mangler noedvendige kolonner til tasklist eksport (Task_LstGrp/GrpCr)."
    End If

    If Not EnsureSapSession() Then Exit Sub
    On Error GoTo myerr

    NavigateToTransaction TX_IA07

    lastRow = wsSource.Cells(wsSource.Rows.Count, cTlGroup).End(xlUp).Row
    outRow = 2
    outCompRow = 2
    outDocRow = 2
    outPackRow = 1
    totalTasklists = CountTasklistRowsToExport(wsSource, cTlGroup, cTlCounter, lastRow)
    processedTasklists = 0
    phaseStart = Timer
    ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedTasklists, totalTasklists, "Tasklists", "Starting...", phaseStart

    For i = 2 To lastRow
        tlGroup = Trim(CStr(wsSource.Cells(i, cTlGroup).Value))
        tlCounter = Trim(CStr(wsSource.Cells(i, cTlCounter).Value))
        strategyValue = ""
        If cStrategy > 0 Then strategyValue = Trim$(CStr(wsSource.Cells(i, cStrategy).Value))
        sourceKey = tlGroup & "/" & tlCounter
        If tlGroup = "" Or tlCounter = "" Then GoTo NextItem

        processedTasklists = processedTasklists + 1
        ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedTasklists, totalTasklists, "Tasklists", sourceKey, phaseStart

        objSess.FindById("wnd[0]/usr/ctxtRC271-PLNNR").Text = tlGroup
        objSess.FindById("wnd[0]/usr/txtRC271-PLNAL").Text = tlCounter
        objSess.FindById("wnd[0]/tbar[1]/btn[7]").press

        Set operations = ExtractOperationsFromTaskList()
        Set matsByOp = CreateObject("Scripting.Dictionary")
        Set docsByOp = CreateObject("Scripting.Dictionary")

        If operations.Count > 0 Then
            lastOp = NormalizeOperationNumber(CStr(operations(operations.Count)("VORNR")))

            ' Components must be read page-by-page; otherwise only first operation page is captured.
            opVisibleRows = 13
            On Error Resume Next
            opVisibleRows = CLng(objSess.FindById("wnd[0]/usr/tblSAPLCPDITCTRL_3400").VisibleRowCount)
            If opVisibleRows <= 0 Then opVisibleRows = 13
            On Error GoTo myerr

            TryPress "wnd[0]/tbar[0]/btn[80]"
            DoEvents

            Do
                If Not TryPress("wnd[0]/tbar[1]/btn[34]") Then Exit Do
                If Not TryPress("wnd[0]/usr/btnTEXT_DRUCKTASTE_MAT") Then Exit Do

                currentOp = NormalizeOperationNumber(GetCurrentMaterialOperationNumber())
                guard = 0

                Do While currentOp <> "" And guard <= operations.Count + 10
                    idList = ""
                    qtyList = ""
                    uomList = ""
                    descList = ""
                    ReadCurrentOperationMaterials idList, qtyList, uomList, descList

                    Set matData = CreateObject("Scripting.Dictionary")
                    matData("IDNRK") = idList
                    matData("MENGE") = qtyList
                    matData("MEINS") = uomList
                    matData("MAKTX") = descList
                    If matsByOp.Exists(currentOp) Then
                        Set matsByOp(currentOp) = matData
                    Else
                        matsByOp.Add currentOp, matData
                    End If

                    If currentOp = lastOp Then Exit Do
                    If Not TryPress("wnd[0]/tbar[1]/btn[19]") Then Exit Do

                    nextOp = NormalizeOperationNumber(GetCurrentMaterialOperationNumber())
                    If nextOp = "" Then Exit Do
                    If nextOp = currentOp Then Exit Do

                    currentOp = nextOp
                    guard = guard + 1
                Loop

                TryPress "wnd[0]/tbar[0]/btn[3]"

                matPageMarker = GetOperationPageMarker("wnd[0]/usr/tblSAPLCPDITCTRL_3400/", opVisibleRows)
                If Len(matPageMarker) = 0 Then Exit Do

                If Not TryPress("wnd[0]/tbar[0]/btn[82]") Then Exit Do
                DoEvents

                matNextPageMarker = GetOperationPageMarker("wnd[0]/usr/tblSAPLCPDITCTRL_3400/", opVisibleRows)
                If Len(matNextPageMarker) = 0 Then Exit Do
                If StrComp(matNextPageMarker, matPageMarker, vbTextCompare) = 0 Then Exit Do
            Loop

            Set docsByOp = ExtractTaskListDocuments()
            firstOpKey = NormalizeOperationNumber(CStr(DictionaryValue(operations(1), "VORNR")))

            ' Docs without VORNR (*) should only be assigned to the first operation.
            If firstOpKey <> "" And docsByOp.Exists("*") Then
                Set wildcardDocs = docsByOp("*")

                If docsByOp.Exists(firstOpKey) Then
                    Set docRows = docsByOp(firstOpKey)
                Else
                    Set docRows = New Collection
                    docsByOp.Add firstOpKey, docRows
                End If

                AppendDocumentRows docRows, wildcardDocs

                docsByOp.Remove "*"
            End If

            For Each op In operations
                wsOut.Cells(outRow, "A").Value = sourceKey
                wsOut.Cells(outRow, "B").Value = DictionaryValue(op, "VORNR")
                wsOut.Cells(outRow, "C").Value = DictionaryValue(op, "ARBPL")
                wsOut.Cells(outRow, "D").Value = DictionaryValue(op, "STEUS")
                wsOut.Cells(outRow, "E").Value = DictionaryValue(op, "LTXA1")
                wsOut.Cells(outRow, "F").Value = DictionaryValue(op, "TXTKZ")
                wsOut.Cells(outRow, "G").Value = DictionaryValue(op, "ARBEI")
                wsOut.Cells(outRow, "H").Value = DictionaryValue(op, "ARBEH")
                wsOut.Cells(outRow, "I").Value = DictionaryValue(op, "ANZZL")
                wsOut.Cells(outRow, "J").Value = DictionaryValue(op, "DAUNO")
                wsOut.Cells(outRow, "K").Value = DictionaryValue(op, "DAUNE")
                wsOut.Cells(outRow, "L").Value = DictionaryValue(op, "INDET")
                wsOut.Cells(outRow, "M").Value = DictionaryValue(op, "PRZNT")
                wsOut.Cells(outRow, "N").Value = DictionaryValue(op, "BMVRG")
                wsOut.Cells(outRow, "O").Value = DictionaryValue(op, "BMEIH")
                wsOut.Cells(outRow, "P").Value = DictionaryValue(op, "PREIS")
                wsOut.Cells(outRow, "Q").Value = DictionaryValue(op, "WAERS")
                wsOut.Cells(outRow, "R").Value = DictionaryValue(op, "PEINH")
                wsOut.Cells(outRow, "S").Value = DictionaryValue(op, "SAKTO")
                wsOut.Cells(outRow, "T").Value = DictionaryValue(op, "MATKL")
                wsOut.Cells(outRow, "U").Value = DictionaryValue(op, "EKGRP")
                wsOut.Cells(outRow, "V").Value = DictionaryValue(op, "LIFNR")
                wsOut.Cells(outRow, "W").Value = DictionaryValue(op, "EKORG")
                wsOut.Cells(outRow, "X").Value = DictionaryValue(op, "SLWID")

                If matsByOp.Exists(NormalizeOperationNumber(CStr(DictionaryValue(op, "VORNR")))) Then
                    Set matData = matsByOp(NormalizeOperationNumber(CStr(DictionaryValue(op, "VORNR"))))
                    WriteTasklistComponentRows wsComp, outCompRow, sourceKey, DictionaryValue(op, "VORNR"), matData
                End If

                If docsByOp.Exists(NormalizeOperationNumber(CStr(DictionaryValue(op, "VORNR")))) Then
                    Set docRows = docsByOp(NormalizeOperationNumber(CStr(DictionaryValue(op, "VORNR"))))
                    WriteTasklistAttachmentRows wsDocs, outDocRow, sourceKey, docRows
                End If

                wsOut.Cells(outRow, "Y").Value = "Exporteret"
                wsOut.Cells(outRow, "Z").Value = DictionaryValue(op, "OP_LONGTEXT")
                outRow = outRow + 1
            Next op
        Else
            wsOut.Cells(outRow, "A").Value = sourceKey
            wsOut.Cells(outRow, "Y").Value = "Ingen operationer fundet"
            wsOut.Cells(outRow, "Z").Value = ""
            outRow = outRow + 1
        End If

        ' Last step in tasklist export: maintenance packages for items with Strategy.
        If Len(strategyValue) > 0 Then
            ExportTasklistMaintPackages wsPack, outPackRow, sourceKey, strategyValue
        End If

        NavigateToTransaction TX_IA07

NextItem:
        i = i ' label target - no-op
    Next i

    ReportExtractPhaseProgress statusBasePct, statusSpanPct, totalTasklists, totalTasklists, "Tasklists", "Done", phaseStart

    wsOut.Columns("A:Z").VerticalAlignment = xlVAlignTop
    wsComp.Columns("A:F").VerticalAlignment = xlVAlignTop
    wsDocs.Columns("A:F").VerticalAlignment = xlVAlignTop
    wsPack.Cells.VerticalAlignment = xlVAlignTop
    wsOut.Columns("A:Z").EntireColumn.AutoFit
    wsComp.Columns("A:F").EntireColumn.AutoFit
    wsDocs.Columns("A:F").EntireColumn.AutoFit
    wsPack.Cells.EntireColumn.AutoFit

    Exit Sub

myerr:
    ReportExtractPhaseProgress statusBasePct, statusSpanPct, processedTasklists, totalTasklists, "Tasklists", "Error on " & sourceKey, phaseStart
    If Not wsOut Is Nothing Then
        wsOut.Cells(outRow, "A").Value = sourceKey
        wsOut.Cells(outRow, "Y").Value = "FEJL: " & Err.Description
        wsOut.Cells(outRow, "Z").Value = ""
        outRow = outRow + 1
    End If
    NavigateToTransaction TX_IA07
    Resume NextItem

End Sub

Private Function CountTasklistRowsToExport(ByVal wsSource As Worksheet, _
                                           ByVal cTlGroup As Long, _
                                           ByVal cTlCounter As Long, _
                                           ByVal lastRow As Long) As Long
    Dim i As Long

    If wsSource Is Nothing Then Exit Function
    If cTlGroup <= 0 Or cTlCounter <= 0 Then Exit Function

    For i = 2 To lastRow
        If Len(Trim$(CStr(wsSource.Cells(i, cTlGroup).Value))) > 0 And _
           Len(Trim$(CStr(wsSource.Cells(i, cTlCounter).Value))) > 0 Then
            CountTasklistRowsToExport = CountTasklistRowsToExport + 1
        End If
    Next i
End Function

Private Function EnsureTasklistMaintPackSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets("Raw_Tasklist_Maint_Pack")
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = "Raw_Tasklist_Maint_Pack"
    End If

    ws.Cells.Clear

    Set EnsureTasklistMaintPackSheet = ws
End Function

Private Sub ExportTasklistMaintPackages(ByVal wsPack As Worksheet, ByRef outPackRow As Long, ByVal sourceKey As String, ByVal strategyValue As String)
    Const tableId As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3600"
    Const tablePath As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3600/"

    Dim tbl As Object
    Dim visibleRows As Long
    Dim colCount As Long
    Dim vRow As Long, absRow As Long
    Dim hasDataOnPage As Boolean
    Dim c As Long
    Dim headerText As String
    Dim cellValue As String
    Dim opValue As String
    Dim rowHasData As Boolean
    Dim stopRows As Boolean
    Dim headerRow As Long
    Dim seenRows As Object
    Dim rowSignature As String
    Dim pageMarker As String
    Dim nextPageMarker As String

    If wsPack Is Nothing Then Exit Sub

    On Error GoTo cleanup

    outPackRow = FindFirstEmptyRowFrom(wsPack, outPackRow)
    headerRow = outPackRow

    If Not TryPress("wnd[0]/usr/btnTEXT_DRUCKTASTE_WP") Then Exit Sub

    On Error Resume Next
    Set tbl = objSess.FindById(tableId)
    If Err.Number <> 0 Or tbl Is Nothing Then
        Err.Clear
        GoTo cleanup
    End If

    visibleRows = CLng(tbl.VisibleRowCount)
    colCount = CLng(tbl.Columns.Count)
    If Err.Number <> 0 Then
        Err.Clear
        GoTo cleanup
    End If
    On Error GoTo cleanup

    If visibleRows <= 0 Then visibleRows = 13
    If colCount <= 0 Then GoTo cleanup
    Set seenRows = CreateObject("Scripting.Dictionary")

    ' Always start from first maint-pack page to avoid carrying over last page state.
    TryPress "wnd[0]/tbar[0]/btn[80]"
    DoEvents

    wsPack.Cells(headerRow, "A").Value = "Task_LstGrp/GrpCr"
    wsPack.Cells(headerRow, "B").Value = "Strategy"

    For c = 0 To colCount - 1
        Select Case c
            Case 0
                headerText = "Op."
            Case 1
                headerText = "SOp"
            Case 2
                headerText = "Operation Description"
            Case Else
                headerText = GetMaintPackColumnHeader(tbl, c)
        End Select
        If Len(headerText) = 0 Then headerText = "COL_" & CStr(c + 1)
        wsPack.Cells(headerRow, c + 3).Value = headerText
    Next c

    wsPack.Rows(headerRow).Font.Bold = True
    outPackRow = headerRow + 1

    Do
        pageMarker = GetMaintPackPageMarker(tbl, tablePath, visibleRows)

        hasDataOnPage = False
        For vRow = 0 To visibleRows - 1
            absRow = vRow

            opValue = GetMaintPackCellValue(tbl, tablePath, 0, absRow, vRow)
            If IsMaintPackOpStop(opValue) Then
                stopRows = True
                Exit For
            End If

            rowHasData = (Len(Trim$(opValue)) > 0)
            rowSignature = Trim$(opValue)

            For c = 1 To colCount - 1
                cellValue = GetMaintPackCellValue(tbl, tablePath, c, absRow, vRow)
                rowSignature = rowSignature & "|" & Trim$(cellValue)
                If Len(Trim$(cellValue)) > 0 Then rowHasData = True
            Next c

            If rowHasData Then
                hasDataOnPage = True
                If Not seenRows.Exists(rowSignature) Then
                    seenRows.Add rowSignature, True
                    wsPack.Cells(outPackRow, "A").Value = sourceKey
                    wsPack.Cells(outPackRow, "B").Value = strategyValue
                    wsPack.Cells(outPackRow, 3).Value = opValue

                    For c = 1 To colCount - 1
                        cellValue = GetMaintPackCellValue(tbl, tablePath, c, absRow, vRow)
                        wsPack.Cells(outPackRow, c + 3).Value = cellValue
                    Next c

                    outPackRow = outPackRow + 1
                End If
            End If
        Next vRow

        If stopRows Then Exit Do
        If Not hasDataOnPage Then Exit Do

        If Not TryPress("wnd[0]/tbar[0]/btn[82]") Then Exit Do
        DoEvents

        nextPageMarker = GetMaintPackPageMarker(tbl, tablePath, visibleRows)
        If Len(nextPageMarker) = 0 Then Exit Do
        If StrComp(nextPageMarker, pageMarker, vbTextCompare) = 0 Then Exit Do
    Loop

cleanup:
    On Error Resume Next
    If Not tbl Is Nothing Then tbl.VerticalScrollbar.Position = 0
    objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
    outPackRow = FindFirstEmptyRowFrom(wsPack, outPackRow)
    On Error GoTo 0
End Sub

Private Function GetMaintPackPageMarker(ByVal tbl As Object, ByVal tablePath As String, ByVal visibleRows As Long) As String
    Dim r As Long
    Dim opValue As String

    If visibleRows <= 0 Then visibleRows = 13

    For r = 0 To visibleRows - 1
        opValue = NormalizeOperationNumber(GetMaintPackCellValue(tbl, tablePath, 0, r, r))
        If Len(opValue) > 0 Then
            GetMaintPackPageMarker = opValue
            Exit Function
        End If
    Next r
End Function

Private Function FindFirstEmptyRowFrom(ByVal ws As Worksheet, ByVal startRow As Long) As Long
    Dim r As Long

    If ws Is Nothing Then
        FindFirstEmptyRowFrom = startRow
        Exit Function
    End If

    If startRow < 1 Then startRow = 1
    r = startRow

    Do While Application.WorksheetFunction.CountA(ws.Rows(r)) > 0
        r = r + 1
    Loop

    FindFirstEmptyRowFrom = r
End Function

Private Function IsMaintPackOpStop(ByVal opValue As String) As Boolean
    Dim marker As String

    marker = Trim$(opValue)
    If Len(marker) = 0 Then
        IsMaintPackOpStop = False
        Exit Function
    End If

    marker = Replace(marker, " ", "")
    marker = Replace(marker, "_", "")

    IsMaintPackOpStop = (Len(marker) = 0)
End Function

Private Function GetMaintPackColumnHeader(ByVal tbl As Object, ByVal colIndex As Long) As String
    Dim colObj As Object

    On Error Resume Next
    Set colObj = tbl.Columns(CLng(colIndex))
    If Err.Number <> 0 Or colObj Is Nothing Then
        Err.Clear
        Exit Function
    End If

    GetMaintPackColumnHeader = CStr(CallByName(colObj, "Title", VbGet))
    If Err.Number = 0 And Len(Trim$(GetMaintPackColumnHeader)) > 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear

    GetMaintPackColumnHeader = CStr(CallByName(colObj, "Name", VbGet))
    If Err.Number = 0 Then
        GetMaintPackColumnHeader = Trim$(GetMaintPackColumnHeader)
    Else
        Err.Clear
        GetMaintPackColumnHeader = ""
    End If
    On Error GoTo 0
End Function

Private Function GetMaintPackColumnName(ByVal tbl As Object, ByVal colIndex As Long) As String
    Dim colObj As Object

    On Error Resume Next
    Set colObj = tbl.Columns(CLng(colIndex))
    If Err.Number <> 0 Or colObj Is Nothing Then
        Err.Clear
        Exit Function
    End If

    GetMaintPackColumnName = CStr(CallByName(colObj, "Name", VbGet))
    If Err.Number <> 0 Then
        Err.Clear
        GetMaintPackColumnName = ""
    End If
    On Error GoTo 0
End Function

Private Function GetMaintPackCellValue(ByVal tbl As Object, ByVal tablePath As String, ByVal colIndex As Long, ByVal absRowIndex As Long, ByVal visibleRowIndex As Long) As String
    Dim colName As String
    Dim cellId As String
    Dim controlId As String
    Dim pref As Variant
    Dim markIdx As Long
    Dim markToken As String

    colName = GetMaintPackColumnName(tbl, colIndex)

    ' First 3 columns are stable across strategies.
    Select Case colIndex
        Case 0
            GetMaintPackCellValue = SafeGuiText(tablePath & "txtPLPOD-VORNR[0," & CStr(visibleRowIndex) & "]")
            If Len(GetMaintPackCellValue) > 0 Then Exit Function
        Case 1
            GetMaintPackCellValue = SafeGuiText(tablePath & "txtPLPOD-UVORN[1," & CStr(visibleRowIndex) & "]")
            If Len(GetMaintPackCellValue) > 0 Then Exit Function
        Case 2
            GetMaintPackCellValue = SafeGuiText(tablePath & "txtPLPOD-LTXA1[2," & CStr(visibleRowIndex) & "]")
            If Len(GetMaintPackCellValue) > 0 Then Exit Function
    End Select

    ' Strategy package columns are commonly rendered as MARKxx checkboxes.
    If colIndex >= 3 Then
        markIdx = colIndex - 2
        markToken = Right$("00" & CStr(markIdx), 2)

        cellId = tablePath & "chkRIHSTRAT-MARK" & markToken & "[" & CStr(colIndex) & "," & CStr(visibleRowIndex) & "]"
        GetMaintPackCellValue = SafeGuiSelected(cellId)
        If Len(GetMaintPackCellValue) > 0 Then Exit Function

        cellId = tablePath & "chkRIHSTRAT-MARK" & CStr(markIdx) & "[" & CStr(colIndex) & "," & CStr(visibleRowIndex) & "]"
        GetMaintPackCellValue = SafeGuiSelected(cellId)
        If Len(GetMaintPackCellValue) > 0 Then Exit Function
    End If

    On Error Resume Next
    GetMaintPackCellValue = CStr(CallByName(tbl, "GetCellValue", VbMethod, absRowIndex, colIndex))
    If Err.Number = 0 And Len(GetMaintPackCellValue) > 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear

    If Len(colName) > 0 Then
        GetMaintPackCellValue = CStr(CallByName(tbl, "GetCellValue", VbMethod, absRowIndex, colName))
    End If
    If Err.Number = 0 And Len(GetMaintPackCellValue) > 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear

    GetMaintPackCellValue = CStr(CallByName(tbl, "GetCellValue", VbMethod, visibleRowIndex, colIndex))
    If Err.Number = 0 And Len(GetMaintPackCellValue) > 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Err.Clear

    If Len(colName) > 0 Then
        controlId = colName
        pref = Array("", "txt", "ctxt", "cmb", "chk", "btn")
        For Each pref In pref
            If CStr(pref) = "" Then
                cellId = tablePath & controlId & "[" & CStr(colIndex) & "," & CStr(visibleRowIndex) & "]"
            Else
                cellId = tablePath & CStr(pref) & controlId & "[" & CStr(colIndex) & "," & CStr(visibleRowIndex) & "]"
            End If

            GetMaintPackCellValue = SafeGuiText(cellId)
            If Len(GetMaintPackCellValue) > 0 Then Exit For
            GetMaintPackCellValue = SafeGuiKey(cellId)
            If Len(GetMaintPackCellValue) > 0 Then Exit For
            GetMaintPackCellValue = SafeGuiSelected(cellId)
            If Len(GetMaintPackCellValue) > 0 Then Exit For
        Next pref
    End If
    On Error GoTo 0
End Function

Private Function FindHeaderIndex(ByVal ws As Worksheet, ByVal candidates As Variant) As Long
    Dim lastCol As Long
    Dim c As Long
    Dim i As Long
    Dim headerText As String

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    For c = 1 To lastCol
        headerText = Trim$(CStr(ws.Cells(1, c).Value))
        If Len(headerText) > 0 Then
            For i = LBound(candidates) To UBound(candidates)
                If StrComp(headerText, CStr(candidates(i)), vbTextCompare) = 0 Then
                    FindHeaderIndex = c
                    Exit Function
                End If
            Next i
        End If
    Next c
End Function

Private Function EnsureTasklistExtractSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets(WS_TASKLIST_EXTRACT)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = WS_TASKLIST_EXTRACT
    End If

    ws.Cells.Clear
    ws.Range("A1").Value = "Task_LstGrp/GrpCr"
    ws.Range("B1").Value = "Act"
    ws.Range("C1").Value = "Work_Ctr"
    ws.Range("D1").Value = "Ctrl"
    ws.Range("E1").Value = "Operation_Description"
    ws.Range("F1").Value = "LT"
    ws.Range("G1").Value = "Work"
    ws.Range("H1").Value = "Work_unit"
    ws.Range("I1").Value = "No"
    ws.Range("J1").Value = "Duration"
    ws.Range("K1").Value = "Duration_unit"
    ws.Range("L1").Value = "Calc"
    ws.Range("M1").Value = "Pct"
    ws.Range("N1").Value = "OrdQuantity"
    ws.Range("O1").Value = "OrdQuantity_unit"
    ws.Range("P1").Value = "Net_Price"
    ws.Range("Q1").Value = "Crcy"
    ws.Range("R1").Value = "Per"
    ws.Range("S1").Value = "Cost_Elem"
    ws.Range("T1").Value = "Mat_Grp"
    ws.Range("U1").Value = "PGr"
    ws.Range("V1").Value = "Supplier"
    ws.Range("W1").Value = "POrg"
    ws.Range("X1").Value = "Fld_key"
    ws.Range("Y1").Value = "Status"
    ws.Range("Z1").Value = "Operation_Long_Text"

    ws.Rows(1).Font.Bold = True
    ws.Columns("Z").WrapText = True
    Set EnsureTasklistExtractSheet = ws
End Function

Private Function EnsureItemObjectsSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets(WS_RAW_ITEM_OBJECTS)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = WS_RAW_ITEM_OBJECTS
    End If

    ws.Cells.Clear
    ws.Range("A1").Value = "Maintenance_item"
    ws.Range("B1").Value = "Functional_Loc"
    ws.Range("C1").Value = "Equipment"
    ws.Rows(1).Font.Bold = True

    Set EnsureItemObjectsSheet = ws
End Function

Private Sub WriteItemObjectRows(ByVal wsObj As Worksheet, ByRef outObjRow As Long, ByVal maintenanceItem As String, ByVal tab2Pairs As String)
    Dim lines As Variant
    Dim i As Long
    Dim lineText As String
    Dim functionalLoc As String
    Dim equipment As String
    Dim lineCount As Long

    lines = SplitAggregateLines(tab2Pairs)
    lineCount = AggregateArrayLength(lines)

    For i = 1 To lineCount
        lineText = AggregateArrayValue(lines, i)
        If ParseTab2PairLine(lineText, functionalLoc, equipment) Then
            wsObj.Cells(outObjRow, "A").Value = maintenanceItem
            wsObj.Cells(outObjRow, "B").Value = functionalLoc
            wsObj.Cells(outObjRow, "C").Value = equipment
            outObjRow = outObjRow + 1
        End If
    Next i
End Sub

Private Function ParseTab2PairLine(ByVal lineText As String, ByRef functionalLoc As String, ByRef equipment As String) As Boolean
    Dim s As String
    Dim splitPos As Long

    s = Trim$(lineText)
    If Len(s) = 0 Then Exit Function

    splitPos = InStr(1, s, vbTab)
    If splitPos > 0 Then
        functionalLoc = Trim$(Left$(s, splitPos - 1))
        equipment = Trim$(Mid$(s, splitPos + Len(vbTab)))
    Else
        functionalLoc = s
        equipment = vbNullString
    End If

    ParseTab2PairLine = (Len(functionalLoc) > 0 Or Len(equipment) > 0)
End Function

Private Function EnsureTasklistComponentsSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets(WS_RAW_TASKLIST_COMPONENTS)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = WS_RAW_TASKLIST_COMPONENTS
    End If

    ws.Cells.Clear
    ws.Range("A1").Value = "Task_LstGrp/GrpCr"
    ws.Range("B1").Value = "Act"
    ws.Range("C1").Value = "Material"
    ws.Range("D1").Value = "Quantity"
    ws.Range("E1").Value = "Un"
    ws.Range("F1").Value = "Component_Description"
    ws.Rows(1).Font.Bold = True

    Set EnsureTasklistComponentsSheet = ws
End Function

Private Sub WriteTasklistComponentRows(ByVal wsComp As Worksheet, ByRef outCompRow As Long, ByVal sourceKey As String, ByVal vornr As String, ByVal matData As Object)
    Dim mats As Variant, qtys As Variant, uoms As Variant, descs As Variant
    Dim i As Long, maxLines As Long
    Dim mat As String, qty As String, uom As String, desc As String

    mats = SplitAggregateLines(DictionaryValue(matData, "IDNRK"))
    qtys = SplitAggregateLines(DictionaryValue(matData, "MENGE"))
    uoms = SplitAggregateLines(DictionaryValue(matData, "MEINS"))
    descs = SplitAggregateLines(DictionaryValue(matData, "MAKTX"))
    maxLines = MaxArrayLength4(mats, qtys, uoms, descs)

    For i = 1 To maxLines
        mat = AggregateArrayValue(mats, i)
        qty = AggregateArrayValue(qtys, i)
        uom = AggregateArrayValue(uoms, i)
        desc = AggregateArrayValue(descs, i)

        If Len(mat) = 0 And Len(qty) = 0 And Len(uom) = 0 And Len(desc) = 0 Then
            GoTo NextComponent
        End If

        wsComp.Cells(outCompRow, "A").Value = sourceKey
        wsComp.Cells(outCompRow, "B").Value = vornr
        wsComp.Cells(outCompRow, "C").Value = mat
        wsComp.Cells(outCompRow, "D").Value = qty
        wsComp.Cells(outCompRow, "E").Value = uom
        wsComp.Cells(outCompRow, "F").Value = desc
        outCompRow = outCompRow + 1

NextComponent:
        i = i ' label target - no-op
    Next i
End Sub

Private Function EnsureTasklistAttachmentsSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets(WS_RAW_TASKLIST_ATTACHMENTS)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = WS_RAW_TASKLIST_ATTACHMENTS
    End If

    ws.Cells.Clear
    ws.Range("A1").Value = "Task_LstGrp/GrpCr"
    ws.Range("B1").Value = "Act"
    ws.Range("C1").Value = "Document"
    ws.Range("D1").Value = "Description"
    ws.Range("E1").Value = "User"
    ws.Range("F1").Value = "Original"
    ws.Rows(1).Font.Bold = True

    Set EnsureTasklistAttachmentsSheet = ws
End Function

Private Sub WriteTasklistAttachmentRows(ByVal wsDocs As Worksheet, ByRef outDocRow As Long, ByVal sourceKey As String, ByVal docRows As Collection)
    Dim docData As Object
    Dim doknr As String, docVornr As String, dktxt As String, dwnam As String, filep As String
    Dim linkCell As Range

    If docRows Is Nothing Then Exit Sub

    For Each docData In docRows
        doknr = DictionaryValue(docData, "DOKNR")
        docVornr = DictionaryValue(docData, "VORNR")
        dktxt = DictionaryValue(docData, "DKTXT")
        dwnam = DictionaryValue(docData, "DWNAM")
        filep = DictionaryValue(docData, "FILEP")

        If Len(doknr) = 0 And Len(docVornr) = 0 And Len(dktxt) = 0 And Len(dwnam) = 0 And Len(filep) = 0 Then
            GoTo NextAttachment
        End If

        wsDocs.Cells(outDocRow, "A").Value = sourceKey
        wsDocs.Cells(outDocRow, "B").Value = docVornr
        wsDocs.Cells(outDocRow, "C").Value = doknr
        wsDocs.Cells(outDocRow, "D").Value = dktxt
        wsDocs.Cells(outDocRow, "E").Value = dwnam
        Set linkCell = wsDocs.Cells(outDocRow, "F")
        linkCell.Value = filep
        If Len(filep) > 0 Then
            On Error Resume Next
            wsDocs.Hyperlinks.Add Anchor:=linkCell, Address:=filep, TextToDisplay:=filep
            Err.Clear
            On Error GoTo 0
        End If
        outDocRow = outDocRow + 1

NextAttachment:
    Next docData
End Sub

Private Sub AppendDocumentRows(ByVal targetRows As Collection, ByVal sourceRows As Collection)
    Dim docData As Object

    If targetRows Is Nothing Then Exit Sub
    If sourceRows Is Nothing Then Exit Sub

    For Each docData In sourceRows
        targetRows.Add docData
    Next docData
End Sub

Private Function SplitAggregateLines(ByVal txt As String) As Variant
    Dim normalized As String

    normalized = Replace(txt, vbCrLf, vbLf)
    normalized = Replace(normalized, vbCr, vbLf)

    If Len(normalized) = 0 Then
        SplitAggregateLines = Array()
    Else
        SplitAggregateLines = Split(normalized, vbLf)
    End If
End Function

Private Function AggregateArrayValue(ByVal arr As Variant, ByVal oneBasedIndex As Long) As String
    Dim idx As Long

    If oneBasedIndex <= 0 Then Exit Function
    If AggregateArrayLength(arr) = 0 Then Exit Function

    idx = LBound(arr) + oneBasedIndex - 1
    If idx < LBound(arr) Or idx > UBound(arr) Then Exit Function

    AggregateArrayValue = Trim$(CStr(arr(idx)))
End Function

Private Function AggregateArrayLength(ByVal arr As Variant) As Long
    On Error GoTo EH
    AggregateArrayLength = UBound(arr) - LBound(arr) + 1
    Exit Function
EH:
    AggregateArrayLength = 0
End Function

Private Function MaxArrayLength5(ByVal a As Variant, ByVal b As Variant, ByVal c As Variant, ByVal d As Variant, ByVal e As Variant) As Long
    MaxArrayLength5 = Application.Max(AggregateArrayLength(a), AggregateArrayLength(b), AggregateArrayLength(c), AggregateArrayLength(d), AggregateArrayLength(e))
End Function

Private Function MaxArrayLength4(ByVal a As Variant, ByVal b As Variant, ByVal c As Variant, ByVal d As Variant) As Long
    MaxArrayLength4 = Application.Max(AggregateArrayLength(a), AggregateArrayLength(b), AggregateArrayLength(c), AggregateArrayLength(d))
End Function

Private Function BuildAttachmentKey(ByVal docVornr As String, ByVal doknr As String, ByVal filep As String, ByVal dwnam As String, ByVal dktxt As String) As String
    Dim baseKey As String

    baseKey = Trim$(doknr)
    If Len(baseKey) = 0 Then baseKey = Trim$(filep)
    If Len(baseKey) = 0 Then baseKey = Trim$(dwnam)
    If Len(baseKey) = 0 Then baseKey = Trim$(dktxt)
    If Len(baseKey) = 0 Then Exit Function

    BuildAttachmentKey = NormalizeOperationNumber(docVornr) & "|" & UCase$(baseKey)
End Function

Private Function ExtractOperationsFromTaskList() As Collection
    Const tableId As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3400"
    Const tablePath As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3400/"

    Dim result As Collection
    Dim tbl As Object
    Dim seenOps As Object
    Dim visibleRows As Long
    Dim vRow As Long
    Dim hasDataOnPage As Boolean
    Dim stopOps As Boolean
    Dim op As Object
    Dim opNum As String
    Dim pageMarker As String
    Dim nextPageMarker As String

    Set result = New Collection
    On Error GoTo fail

    Set tbl = objSess.FindById(tableId)
    Set seenOps = CreateObject("Scripting.Dictionary")

    On Error Resume Next
    visibleRows = CLng(tbl.VisibleRowCount)
    On Error GoTo fail

    If visibleRows <= 0 Then visibleRows = 13

    Do
        pageMarker = GetOperationPageMarker(tablePath, visibleRows)

        hasDataOnPage = False
        For vRow = 0 To visibleRows - 1
            opNum = NormalizeOperationNumber(SafeTableText(tablePath, "txtPLPOD-VORNR", 0, vRow))
            If opNum = "" Then
                stopOps = True
                Exit For
            End If

            hasDataOnPage = True
            If Not seenOps.Exists(opNum) Then
                Set op = CreateObject("Scripting.Dictionary")
                op("VORNR") = opNum
                op("ARBPL") = SafeTableText(tablePath, "ctxtPLPOD-ARBPL", 2, vRow)
                op("STEUS") = SafeTableText(tablePath, "ctxtPLPOD-STEUS", 4, vRow)
                op("LTXA1") = SafeTableText(tablePath, "txtPLPOD-LTXA1", 5, vRow)
                op("TXTKZ") = SafeTableSelected(tablePath, "chkRC270-TXTKZ", 6, vRow)
                If LCase$(CStr(op("TXTKZ"))) = "true" Then
                    op("OP_LONGTEXT") = ReadOperationLongTextFromRow(vRow, opNum)
                Else
                    op("OP_LONGTEXT") = ""
                End If
                op("ARBEI") = SafeTableText(tablePath, "txtPLPOD-ARBEI", 8, vRow)
                op("ARBEH") = SafeTableText(tablePath, "ctxtPLPOD-ARBEH", 9, vRow)
                op("ANZZL") = SafeTableText(tablePath, "txtPLPOD-ANZZL", 10, vRow)
                op("DAUNO") = SafeTableText(tablePath, "txtPLPOD-DAUNO", 11, vRow)
                op("DAUNE") = SafeTableText(tablePath, "ctxtPLPOD-DAUNE", 12, vRow)
                op("INDET") = SafeTableText(tablePath, "ctxtPLPOD-INDET", 13, vRow)
                op("PRZNT") = SafeTableText(tablePath, "txtPLPOD-PRZNT", 14, vRow)
                op("BMVRG") = SafeTableText(tablePath, "txtPLPOD-BMVRG", 30, vRow)
                op("BMEIH") = SafeTableText(tablePath, "ctxtPLPOD-BMEIH", 31, vRow)
                op("PREIS") = SafeTableText(tablePath, "txtPLPOD-PREIS", 32, vRow)
                op("WAERS") = SafeTableText(tablePath, "ctxtPLPOD-WAERS", 33, vRow)
                op("PEINH") = SafeTableText(tablePath, "txtPLPOD-PEINH", 34, vRow)
                op("SAKTO") = SafeTableText(tablePath, "ctxtPLPOD-SAKTO", 36, vRow)
                op("MATKL") = SafeTableText(tablePath, "ctxtPLPOD-MATKL", 37, vRow)
                If CStr(op("MATKL")) = "" Then
                    op("MATKL") = SafeTableText(tablePath, "ctxtPLPOD-MATKL", 37, 1)
                End If
                op("EKGRP") = SafeTableText(tablePath, "ctxtPLPOD-EKGRP", 38, vRow)
                op("LIFNR") = SafeTableText(tablePath, "ctxtPLPOD-LIFNR", 39, vRow)
                op("EKORG") = SafeTableText(tablePath, "ctxtPLPOD-EKORG", 40, vRow)
                op("SLWID") = SafeTableText(tablePath, "ctxtPLPOD-SLWID", 46, vRow)

                seenOps(opNum) = True
                result.Add op
            End If
        Next vRow

        If stopOps Then Exit Do
        If Not hasDataOnPage Then Exit Do

        If Not TryPress("wnd[0]/tbar[0]/btn[82]") Then Exit Do
        DoEvents

        nextPageMarker = GetOperationPageMarker(tablePath, visibleRows)
        If Len(nextPageMarker) = 0 Then Exit Do
        If StrComp(nextPageMarker, pageMarker, vbTextCompare) = 0 Then Exit Do
    Loop

    On Error Resume Next
    tbl.VerticalScrollbar.Position = 0
    On Error GoTo 0

    Set ExtractOperationsFromTaskList = result
    Exit Function

fail:
    Set ExtractOperationsFromTaskList = result
End Function

Private Function GetOperationPageMarker(ByVal tablePath As String, ByVal visibleRows As Long) As String
    Dim r As Long
    Dim opValue As String

    If visibleRows <= 0 Then visibleRows = 13

    For r = 0 To visibleRows - 1
        opValue = NormalizeOperationNumber(SafeTableText(tablePath, "txtPLPOD-VORNR", 0, r))
        If Len(opValue) > 0 Then
            GetOperationPageMarker = opValue
            Exit Function
        End If
    Next r
End Function

Private Sub ReadCurrentOperationMaterials(ByRef idList As String, ByRef qtyList As String, ByRef uomList As String, ByRef descList As String)
    Const tableId As String = "wnd[0]/usr/tblSAPLCMDITCTRL_3500"
    Const tablePath As String = "wnd[0]/usr/tblSAPLCMDITCTRL_3500/"

    Dim tbl As Object
    Dim seen As Object
    Dim visibleRows As Long, rowCount As Long
    Dim pageStart As Long, vRow As Long, absRow As Long
    Dim currentPos As Long, lastPos As Long
    Dim hasDataOnPage As Boolean
    Dim idnrk As String, menge As String, meins As String, maktx As String
    Dim lineKey As String

    idList = ""
    qtyList = ""
    uomList = ""
    descList = ""

    On Error GoTo fail
    Set tbl = objSess.FindById(tableId)
    Set seen = CreateObject("Scripting.Dictionary")

    On Error Resume Next
    visibleRows = CLng(tbl.VisibleRowCount)
    rowCount = CLng(tbl.RowCount)
    On Error GoTo fail

    If visibleRows <= 0 Then visibleRows = 13

    If rowCount > 0 Then
        For pageStart = 0 To rowCount - 1 Step visibleRows
            On Error Resume Next
            tbl.VerticalScrollbar.Position = pageStart
            On Error GoTo fail

            For vRow = 0 To visibleRows - 1
                absRow = pageStart + vRow
                If absRow > rowCount - 1 Then Exit For

                idnrk = Trim$(SafeTableText(tablePath, "ctxtRIHSTPX-IDNRK", 0, vRow))
                If idnrk = "" Then GoTo NextMaterialByCount

                menge = SafeTableText(tablePath, "txtRIHSTPX-MENGE", 1, vRow)
                meins = SafeTableText(tablePath, "ctxtRIHSTPX-MEINS", 2, vRow)
                maktx = SafeTableText(tablePath, "txtRIHSTPX-MAKTX", 5, vRow)
                lineKey = idnrk & "|" & menge & "|" & meins & "|" & maktx

                If Not seen.Exists(lineKey) Then
                    seen(lineKey) = True
                    idList = AppendAggregateValue(idList, idnrk)
                    qtyList = AppendAggregateValue(qtyList, menge)
                    uomList = AppendAggregateValue(uomList, meins)
                    descList = AppendAggregateValue(descList, maktx)
                End If

NextMaterialByCount:
                vRow = vRow
            Next vRow
        Next pageStart
    Else
        pageStart = 0
        lastPos = -1
        Do
            On Error Resume Next
            tbl.VerticalScrollbar.Position = pageStart
            currentPos = CLng(tbl.VerticalScrollbar.Position)
            On Error GoTo fail

            If currentPos = lastPos Then Exit Do
            lastPos = currentPos

            hasDataOnPage = False
            For vRow = 0 To visibleRows - 1
                idnrk = Trim$(SafeTableText(tablePath, "ctxtRIHSTPX-IDNRK", 0, vRow))
                If idnrk <> "" Then
                    hasDataOnPage = True
                    menge = SafeTableText(tablePath, "txtRIHSTPX-MENGE", 1, vRow)
                    meins = SafeTableText(tablePath, "ctxtRIHSTPX-MEINS", 2, vRow)
                    maktx = SafeTableText(tablePath, "txtRIHSTPX-MAKTX", 5, vRow)
                    lineKey = idnrk & "|" & menge & "|" & meins & "|" & maktx

                    If Not seen.Exists(lineKey) Then
                        seen(lineKey) = True
                        idList = AppendAggregateValue(idList, idnrk)
                        qtyList = AppendAggregateValue(qtyList, menge)
                        uomList = AppendAggregateValue(uomList, meins)
                        descList = AppendAggregateValue(descList, maktx)
                    End If
                End If
            Next vRow

            If Not hasDataOnPage Then Exit Do
            pageStart = currentPos + visibleRows
        Loop
    End If

    On Error Resume Next
    tbl.VerticalScrollbar.Position = 0
    On Error GoTo 0
    Exit Sub

fail:
    On Error Resume Next
    If Not tbl Is Nothing Then tbl.VerticalScrollbar.Position = 0
    On Error GoTo 0
End Sub

Private Function SafeTableText(ByVal tablePath As String, ByVal fieldId As String, ByVal colIndex As Long, ByVal rowIndex As Long) As String
    SafeTableText = SafeGuiText(tablePath & fieldId & "[" & CStr(colIndex) & "," & CStr(rowIndex) & "]")
End Function

Private Function SafeTableSelected(ByVal tablePath As String, ByVal fieldId As String, ByVal colIndex As Long, ByVal rowIndex As Long) As String
    SafeTableSelected = SafeGuiSelected(tablePath & fieldId & "[" & CStr(colIndex) & "," & CStr(rowIndex) & "]")
End Function

Private Function AppendAggregateValue(ByVal existingValue As String, ByVal newValue As String) As String
    If Trim$(newValue) = "" Then
        AppendAggregateValue = existingValue
    ElseIf existingValue = "" Then
        AppendAggregateValue = newValue
    Else
        AppendAggregateValue = existingValue & vbLf & newValue
    End If
End Function

Private Function GetCurrentMaterialOperationNumber() As String
    GetCurrentMaterialOperationNumber = Trim$(SafeGuiText("wnd[0]/usr/txtPLPOD-VORNR"))
End Function

Private Function ReadOperationLongTextFromRow(ByVal rowIndex As Long, Optional ByVal expectedOpNo As String = "") As String
    Const tablePath As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3400/"

    Dim textValue As String
    Dim popupHandled As Boolean
    Dim editorOpened As Boolean
    Dim targetRow As Long
    Dim retryCount As Long

    On Error GoTo fail

    targetRow = rowIndex
    If Len(Trim$(expectedOpNo)) > 0 Then
        targetRow = ResolveVisibleOperationRow(expectedOpNo, rowIndex)
    End If

    objSess.FindById(tablePath & "chkRC270-TXTKZ[6," & CStr(targetRow) & "]").SetFocus
    objSess.FindById("wnd[0]").sendVKey 2

    ' SAP can respond a bit slowly on first operations; wait briefly for popup/editor state.
    For retryCount = 1 To 10
        popupHandled = DismissTopDialogIfPresent()
        If popupHandled Then
            ReadOperationLongTextFromRow = ""
            Exit Function
        End If

        editorOpened = Not IsOperationTableVisible()
        If editorOpened Then Exit For

        If IsEditorShellVisible() Then
            editorOpened = True
            Exit For
        End If

        DoEvents
    Next retryCount

    If Not editorOpened Then
        ReadOperationLongTextFromRow = ""
        Exit Function
    End If

    textValue = ReadSapEditorShellText()
    If textValue = "" Then
        textValue = DownloadLongTextFromEditor()
    End If

    If editorOpened Then
        On Error Resume Next
        objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
        On Error GoTo 0
    End If

    ReadOperationLongTextFromRow = textValue
    Exit Function

fail:
    DismissTopDialogIfPresent

    If Not IsOperationTableVisible() Then
        On Error Resume Next
        objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
        On Error GoTo 0
    End If

    ReadOperationLongTextFromRow = ""
End Function

Private Function IsEditorShellVisible() As Boolean
    Dim shell As Object

    On Error Resume Next
    Set shell = objSess.FindById("wnd[0]/usr/shell")
    IsEditorShellVisible = (Err.Number = 0 And Not shell Is Nothing)
    Err.Clear
    On Error GoTo 0
End Function

Private Function ResolveVisibleOperationRow(ByVal expectedOpNo As String, ByVal fallbackRow As Long) As Long
    Const tablePath As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3400/"

    Dim visibleRows As Long
    Dim tbl As Object
    Dim r As Long
    Dim opAtRow As String
    Dim expectedNorm As String

    ResolveVisibleOperationRow = fallbackRow
    expectedNorm = NormalizeOperationKey(expectedOpNo)
    If Len(expectedNorm) = 0 Then Exit Function

    On Error Resume Next
    Set tbl = objSess.FindById("wnd[0]/usr/tblSAPLCPDITCTRL_3400")
    visibleRows = CLng(tbl.VisibleRowCount)
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    On Error GoTo 0

    If visibleRows <= 0 Then visibleRows = 13

    For r = 0 To visibleRows - 1
        opAtRow = NormalizeOperationKey(SafeTableText(tablePath, "txtPLPOD-VORNR", 0, r))
        If StrComp(opAtRow, expectedNorm, vbTextCompare) = 0 Then
            ResolveVisibleOperationRow = r
            Exit Function
        End If
    Next r
End Function

Private Function NormalizeOperationKey(ByVal rawValue As String) As String
    Dim s As String

    s = Trim$(rawValue)
    If Len(s) = 0 Then Exit Function

    If IsNumeric(s) Then
        NormalizeOperationKey = CStr(CLng(Val(s)))
    Else
        NormalizeOperationKey = UCase$(s)
    End If
End Function

Private Function IsOperationTableVisible() As Boolean
    Dim tbl As Object

    On Error Resume Next
    Set tbl = objSess.FindById("wnd[0]/usr/tblSAPLCPDITCTRL_3400")
    IsOperationTableVisible = (Err.Number = 0 And Not tbl Is Nothing)
    Err.Clear
    On Error GoTo 0
End Function

Private Function DismissTopDialogIfPresent() As Boolean
    Dim popup As Object

    On Error Resume Next
    Set popup = objSess.FindById("wnd[1]")
    If Err.Number <> 0 Or popup Is Nothing Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If

    popup.sendVKey 0
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If

    Set popup = Nothing
    Set popup = objSess.FindById("wnd[1]")
    If Err.Number = 0 And Not popup Is Nothing Then
        popup.sendVKey 0
        If Err.Number <> 0 Then
            Err.Clear
            On Error GoTo 0
            Exit Function
        End If
    Else
        Err.Clear
    End If

    Set popup = Nothing
    Set popup = objSess.FindById("wnd[1]")
    If Err.Number <> 0 Or popup Is Nothing Then
        Err.Clear
        DismissTopDialogIfPresent = True
        Exit Function
    End If
    Err.Clear

    objSess.FindById("wnd[1]/tbar[0]/btn[0]").press
    If Err.Number = 0 Then
        DismissTopDialogIfPresent = True
        Exit Function
    End If
    Err.Clear

    On Error GoTo 0
End Function

Private Function ExtractTaskListDocuments() As Object
    Const alvPath As String = "wnd[1]/usr/subSUB_0100:SAPLEAMCC_DOC_ALV:0100/cntlDVS_ALV/shellcont/shell"

    Dim docsByOp As Object
    Dim shell As Object
    Dim rowCount As Long, r As Long
    Dim opKey As String
    Dim doknr As String, vornr As String, dktxt As String, dwnam As String, filep As String
    Dim docRows As Collection

    Set docsByOp = CreateObject("Scripting.Dictionary")

    On Error GoTo fail
    If Not TryPress("wnd[0]/tbar[1]/btn[36]") Then
        Set ExtractTaskListDocuments = docsByOp
        Exit Function
    End If

    Set shell = objSess.FindById(alvPath)
    rowCount = GetAlvRowCount(shell)

    If rowCount <= 0 Then
        TryPress "wnd[1]/tbar[0]/btn[0]"
        Set ExtractTaskListDocuments = docsByOp
        Exit Function
    End If

    For r = 0 To rowCount - 1
        doknr = GetAlvCellText(shell, r, "DOKNR")
        vornr = NormalizeOperationNumber(GetAlvCellText(shell, r, "VORNR"))
        dktxt = GetAlvCellText(shell, r, "DKTXT")
        dwnam = GetAlvCellText(shell, r, "DWNAM")
        filep = GetAlvCellText(shell, r, "FILEP")

        If doknr = "" And vornr = "" And dktxt = "" And dwnam = "" And filep = "" Then GoTo NextDocRow

        opKey = vornr
        If opKey = "" Then opKey = "*"

        If docsByOp.Exists(opKey) Then
            Set docRows = docsByOp(opKey)
        Else
            Set docRows = New Collection
            docsByOp.Add opKey, docRows
        End If

        AddTaskListDocumentRow docRows, doknr, vornr, dktxt, dwnam, filep

NextDocRow:
        r = r ' label target - no-op
    Next r

    TryPress "wnd[1]/tbar[0]/btn[0]"
    Set ExtractTaskListDocuments = docsByOp
    Exit Function

fail:
    On Error Resume Next
    TryPress "wnd[1]/tbar[0]/btn[0]"
    On Error GoTo 0
    Set ExtractTaskListDocuments = docsByOp
End Function

Private Sub AddTaskListDocumentRow(ByVal docRows As Collection, ByVal doknr As String, ByVal vornr As String, ByVal dktxt As String, ByVal dwnam As String, ByVal filep As String)
    Dim docData As Object

    If docRows Is Nothing Then Exit Sub

    Set docData = CreateObject("Scripting.Dictionary")
    docData("DOKNR") = doknr
    docData("VORNR") = vornr
    docData("DKTXT") = dktxt
    docData("DWNAM") = dwnam
    docData("FILEP") = filep
    docRows.Add docData
End Sub

Private Function GetAlvRowCount(ByVal shell As Object) As Long
    On Error Resume Next
    GetAlvRowCount = CLng(CallByName(shell, "RowCount", VbGet))
    If Err.Number <> 0 Then
        Err.Clear
        GetAlvRowCount = 0
    End If
    On Error GoTo 0
End Function

Private Function GetAlvCellText(ByVal shell As Object, ByVal rowIndex As Long, ByVal columnName As String) As String
    On Error Resume Next
    GetAlvCellText = CStr(CallByName(shell, "GetCellValue", VbMethod, rowIndex, columnName))
    If Err.Number <> 0 Then
        Err.Clear
        GetAlvCellText = ""
    End If
    On Error GoTo 0
End Function

Private Function NormalizeOperationNumber(ByVal rawValue As String) As String
    Dim t As String
    Dim marker As String

    t = Trim$(rawValue)
    marker = Replace(t, "_", "")
    marker = Replace(marker, "-", "")
    marker = Replace(marker, " ", "")

    If marker = "" Then
        NormalizeOperationNumber = ""
    Else
        NormalizeOperationNumber = t
    End If
End Function

Private Function TryPress(ByVal id As String) As Boolean
    On Error Resume Next
    objSess.FindById(id).press
    TryPress = (Err.Number = 0)
    Err.Clear
    On Error GoTo 0
End Function

Private Function EnsureSapSession() As Boolean
    If objSess Is Nothing Then
        MsgBox "Ingen aktiv SAP-session. Kør SAP-login/attach først.", vbCritical + vbOKOnly
        EnsureSapSession = False
        Exit Function
    End If
    EnsureSapSession = True
End Function

Private Sub NavigateToTransaction(ByVal transactionCode As String)
    objSess.FindById("wnd[0]/tbar[0]/okcd").Text = transactionCode
    objSess.FindById("wnd[0]").sendVKey 0
End Sub

Private Sub SetRowStatus(ByVal ws As Worksheet, ByVal rowIndex As Long, ByVal columnRef As String, ByVal statusText As String)
    If ws Is Nothing Then Exit Sub
    If rowIndex < 1 Then Exit Sub
    If rowIndex > ws.Rows.Count Then Exit Sub
    ws.Cells(rowIndex, columnRef).Value = statusText
End Sub

'===============================================================================
' Helper: ReverseLookupPlant
' Finds the plant name from a plant key by doing a reverse lookup in PlantDict.
' Falls back to returning the key itself if not found.
'===============================================================================
Private Function ReverseLookupPlant(plantKey As String) As String
    Dim k As Variant
    For Each k In PlantDict.Keys
        If PlantDict(k) = plantKey Then
            ReverseLookupPlant = k
            Exit Function
        End If
    Next k
    ReverseLookupPlant = plantKey ' fallback: return the key if no name found
End Function

'===============================================================================
' Helper: DeleteExistingTLRows
' Removes all rows in the Maintenance_TL sheet where column A matches tlKey.
' Called before writing fresh operation data to avoid duplicates.
'===============================================================================
Private Sub DeleteExistingTLRows(ws As Worksheet, tlKey As String)
    Dim lastRow As Long, r As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    For r = lastRow To 2 Step -1
        If Trim(ws.Cells(r, "A").Value) = tlKey Then
            ws.Rows(r).Delete
        End If
    Next r
End Sub

Private Function EnsureItemExtractSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = Worksheets(WS_ITEM_EXTRACT)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = Worksheets.Add(After:=Worksheets(Worksheets.Count))
        ws.Name = WS_ITEM_EXTRACT
    End If

    ws.Cells.Clear
    ws.Range("A1").Value = "Maintenance_item"
    ws.Range("B1").Value = "Short_Text"
    ws.Range("C1").Value = "Maint_plan_cat"
    ws.Range("D1").Value = "Functional_loc"
    ws.Range("E1").Value = "Equipment"
    ws.Range("F1").Value = "Planning_plant"
    ws.Range("G1").Value = "Order_Type"
    ws.Range("H1").Value = "MaintActivityType"
    ws.Range("I1").Value = "Main_WorkCtr"
    ws.Range("J1").Value = "Priority"
    ws.Range("K1").Value = "Do_Not_Rel.Immediately"
    ws.Range("L1").Value = "Typ"
    ws.Range("M1").Value = "Task_LstGrp"
    ws.Range("N1").Value = "GrpCr"
    ws.Range("O1").Value = "MaintenancePlan"
    ws.Range("P1").Value = "Flow_User_Status"
    ws.Range("Q1").Value = "Non_Flow_User_Status"
    ws.Range("R1").Value = "Revision"
    ws.Range("S1").Value = "WCM_Required_Yes"
    ws.Range("T1").Value = "WCM_Required_No"
    ws.Range("U1").Value = "Next_Review_year"
    ws.Range("V1").Value = "Next_Review_month"
    ws.Range("W1").Value = "Last_Review_year"
    ws.Range("X1").Value = "Reviewed_by"
    ws.Range("Y1").Value = "Status"
    ws.Range("Z1").Value = "Long_Text"
    ws.Range("AA1").Value = "Strategy"

    ws.Rows(1).Font.Bold = True
    ws.Columns("Z").WrapText = True
    Set EnsureItemExtractSheet = ws
End Function

Private Function SafeGuiText(ByVal id As String) As String
    On Error Resume Next
    SafeGuiText = objSess.FindById(id).Text
    If Err.Number <> 0 Then
        SafeGuiText = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Private Function SafeGuiKey(ByVal id As String) As String
    On Error Resume Next
    SafeGuiKey = objSess.FindById(id).Key
    If Err.Number <> 0 Then
        SafeGuiKey = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Private Function SafeGuiSelected(ByVal id As String) As String
    On Error Resume Next
    If objSess.FindById(id).Selected Then
        SafeGuiSelected = "True"
    Else
        SafeGuiSelected = "False"
    End If
    If Err.Number <> 0 Then
        SafeGuiSelected = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Private Function ReadItemLongText() As String
    Dim textValue As String

    On Error GoTo fail

    ' Open item long text editor.
    objSess.FindById("wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/btnRMIPM-LTPOS_ICON").press
    textValue = ReadSapEditorShellText()
    If textValue = "" Then
        textValue = DownloadLongTextFromEditor()
    End If

    On Error Resume Next
    objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
    On Error GoTo 0

    ReadItemLongText = textValue
    Exit Function

fail:
    On Error Resume Next
    objSess.FindById("wnd[0]/tbar[0]/btn[3]").press
    On Error GoTo 0
    ReadItemLongText = ""
End Function

Private Function DownloadLongTextFromEditor() As String
    Dim filePath As String

    On Error GoTo fail
    filePath = Environ$("TEMP") & "\SAP_PM_Item_LongText_ASCII.txt"

    On Error Resume Next
    If Dir$(filePath) <> "" Then Kill filePath
    On Error GoTo fail

    ' Download from the SAP editor (Text -> Download).
    objSess.FindById("wnd[0]/mbar/menu[0]/menu[4]").Select

    ' Prefer ASCII format; fallback to ITF if ASCII id differs per system.
    If Not TrySelectGuiRadio("wnd[1]/usr/radITCTK-TDASC") Then
        If Not TrySelectGuiRadio("wnd[1]/usr/radITCTK-TDASCII") Then
            TrySelectGuiRadio "wnd[1]/usr/radITCTK-TDITF"
        End If
    End If

    objSess.FindById("wnd[1]/tbar[0]/btn[0]").press
    objSess.FindById("wnd[2]/usr/ctxtITCTK-TDFILENAME").Text = filePath
    objSess.FindById("wnd[2]/tbar[0]/btn[0]").press

    DownloadLongTextFromEditor = ReadTextFileContent(filePath)

    On Error Resume Next
    If Dir$(filePath) <> "" Then Kill filePath
    On Error GoTo 0
    Exit Function

fail:
    On Error Resume Next
    If Dir$(filePath) <> "" Then
        DownloadLongTextFromEditor = ReadTextFileContent(filePath)
        Kill filePath
    Else
        DownloadLongTextFromEditor = ""
    End If

    ' Close dialogs if still open.
    objSess.FindById("wnd[2]/tbar[0]/btn[12]").press
    objSess.FindById("wnd[1]/tbar[0]/btn[12]").press
    On Error GoTo 0
End Function

Private Function TrySelectGuiRadio(ByVal id As String) As Boolean
    On Error Resume Next
    objSess.FindById(id).Select
    objSess.FindById(id).SetFocus
    TrySelectGuiRadio = (Err.Number = 0)
    Err.Clear
    On Error GoTo 0
End Function

Private Function ReadTextFileContent(ByVal filePath As String) As String
    Dim stm As Object
    Dim txt As String
    Dim fileNum As Integer
    Dim raw As String

    If Dir$(filePath) = "" Then Exit Function

    On Error GoTo fallback

    ' Decode with explicit UTF-8 so Danish characters (ÆØÅ) are preserved.
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2 ' text
    stm.Mode = 3 ' read/write
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile filePath
    txt = stm.ReadText(-1)
    stm.Close

    ' Remove UTF-8 BOM if present.
    If Len(txt) > 0 Then
        If AscW(Left$(txt, 1)) = &HFEFF Then
            txt = Mid$(txt, 2)
        End If
    End If

    ReadTextFileContent = NormalizeLongTextLineBreaks(txt)
    Exit Function

fallback:
    On Error Resume Next
    If Not stm Is Nothing Then
        If stm.State <> 0 Then stm.Close
    End If

    ' Fallback: old binary read.
    fileNum = FreeFile
    Open filePath For Binary As #fileNum
    If LOF(fileNum) > 0 Then
        raw = Space$(LOF(fileNum))
        Get #fileNum, , raw
    End If
    Close #fileNum

    ReadTextFileContent = NormalizeLongTextLineBreaks(raw)
End Function

Private Function NormalizeLongTextLineBreaks(ByVal txt As String) As String
    txt = Replace(txt, vbCrLf, vbLf)
    txt = Replace(txt, vbCr, vbLf)
    NormalizeLongTextLineBreaks = txt
End Function

Private Function ReadSapEditorShellText() As String
    Dim shell As Object
    Dim txt As String

    On Error GoTo fail
    Set shell = objSess.FindById("wnd[0]/usr/shell")

    txt = ""
    On Error Resume Next
    txt = CStr(CallByName(shell, "GetText", VbMethod))
    If Err.Number <> 0 Then
        Err.Clear
        txt = ""
    End If
    On Error GoTo fail

    If txt = "" Then
        On Error Resume Next
        txt = CStr(CallByName(shell, "Text", VbGet))
        If Err.Number <> 0 Then
            Err.Clear
            txt = ""
        End If
        On Error GoTo fail
    End If

    txt = Trim$(txt)
    If LCase$(txt) = "sapeditor.sapeditorctrl.1" Then txt = ""
    ReadSapEditorShellText = txt
    Exit Function

fail:
    ReadSapEditorShellText = ""
End Function

Private Function ExtractTab2ObjectPairs() As String
    Const tablePath As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12/ssubSUBSCREEN_BODY2:SAPLIWP3:8023/subOBJECT:SAPLIWOL:0400/tblSAPLIWOLOBJK_400/"

    Dim tbl As Object
    Dim result As String
    Dim visibleRows As Long, rowCount As Long
    Dim pageStart As Long, vRow As Long, absRow As Long
    Dim tplnr As String, equnr As String
    Dim foundOnPage As Boolean
    Dim pairKey As String
    Dim seenPairs As Object
    Dim currentPos As Long, lastPos As Long

    On Error GoTo fail
    Set tbl = objSess.FindById(Left$(tablePath, Len(tablePath) - 1))
    Set seenPairs = CreateObject("Scripting.Dictionary")

    On Error Resume Next
    visibleRows = CLng(tbl.VisibleRowCount)
    rowCount = CLng(tbl.RowCount)
    On Error GoTo fail

    If visibleRows <= 0 Then visibleRows = 13

    If rowCount > 0 Then
        For pageStart = 0 To rowCount - 1 Step visibleRows
            On Error Resume Next
            tbl.VerticalScrollbar.Position = pageStart
            On Error GoTo fail

            For vRow = 0 To visibleRows - 1
                absRow = pageStart + vRow
                If absRow > rowCount - 1 Then Exit For

                tplnr = SafeGuiText(tablePath & "ctxtRIWOL-TPLNR[1," & CStr(vRow) & "]")
                equnr = SafeGuiText(tablePath & "ctxtRIWOL-EQUNR[3," & CStr(vRow) & "]")
                tplnr = CleanTab2Value(tplnr)
                equnr = CleanTab2Value(equnr)

                If tplnr <> "" Or equnr <> "" Then
                    pairKey = BuildTab2Line(tplnr, equnr)
                    If Not seenPairs.Exists(pairKey) Then
                        seenPairs(pairKey) = True
                        If result <> "" Then result = result & vbLf
                        result = result & pairKey
                    End If
                End If
            Next vRow
        Next pageStart
    Else
        pageStart = 0
        lastPos = -1
        Do
            On Error Resume Next
            tbl.VerticalScrollbar.Position = pageStart
            currentPos = CLng(tbl.VerticalScrollbar.Position)
            On Error GoTo fail

            ' Prevent duplicates/infinite loop when SAP clamps scrollbar at last page.
            If currentPos = lastPos Then Exit Do
            lastPos = currentPos

            foundOnPage = False
            For vRow = 0 To visibleRows - 1
                tplnr = SafeGuiText(tablePath & "ctxtRIWOL-TPLNR[1," & CStr(vRow) & "]")
                equnr = SafeGuiText(tablePath & "ctxtRIWOL-EQUNR[3," & CStr(vRow) & "]")
                tplnr = CleanTab2Value(tplnr)
                equnr = CleanTab2Value(equnr)

                If tplnr <> "" Or equnr <> "" Then
                    pairKey = BuildTab2Line(tplnr, equnr)
                    If Not seenPairs.Exists(pairKey) Then
                        seenPairs(pairKey) = True
                        foundOnPage = True
                        If result <> "" Then result = result & vbLf
                        result = result & pairKey
                    End If
                End If
            Next vRow

            If Not foundOnPage Then Exit Do
            pageStart = currentPos + visibleRows
        Loop
    End If

    On Error Resume Next
    tbl.VerticalScrollbar.Position = 0
    On Error GoTo 0

    ExtractTab2ObjectPairs = result
    Exit Function

fail:
    ExtractTab2ObjectPairs = ""
End Function

Private Function BuildTab2Line(ByVal tplnr As String, ByVal equnr As String) As String
    If tplnr <> "" And equnr <> "" Then
        BuildTab2Line = tplnr & vbTab & equnr
    ElseIf tplnr <> "" Then
        BuildTab2Line = tplnr
    Else
        BuildTab2Line = equnr
    End If
End Function

Private Function CleanTab2Value(ByVal rawValue As String) As String
    Dim t As String
    Dim marker As String

    t = Trim(rawValue)
    If t = "" Then
        CleanTab2Value = ""
        Exit Function
    End If

    marker = Replace(t, "_", "")
    marker = Replace(marker, "-", "")
    marker = Replace(marker, " ", "")
    If marker = "" Then
        CleanTab2Value = ""
    Else
        CleanTab2Value = t
    End If
End Function

Private Function DictionaryValue(ByVal dict As Object, ByVal key As String) As String
    If dict Is Nothing Then Exit Function
    If dict.Exists(key) Then DictionaryValue = CStr(dict(key))
End Function

Private Sub ReportExtractPhaseProgress(ByVal basePct As Long, _
                                       ByVal spanPct As Long, _
                                       ByVal currentCount As Long, _
                                       ByVal totalCount As Long, _
                                       ByVal phaseName As String, _
                                       ByVal detail As String, _
                                       ByVal phaseStart As Double)
    Dim pct As Long

    pct = ResolvePhasePercent(basePct, spanPct, currentCount, totalCount)
    mdlExtractStatus.UpdateExtractStatus pct, BuildExtractProgressText(phaseName, currentCount, totalCount, detail, phaseStart, pct)
End Sub

Private Function ResolvePhasePercent(ByVal basePct As Long, _
                                     ByVal spanPct As Long, _
                                     ByVal currentCount As Long, _
                                     ByVal totalCount As Long) As Long
    Dim ratio As Double
    Dim value As Long

    basePct = ClampProgressPct(basePct)
    spanPct = ClampProgressPct(spanPct)

    If totalCount <= 0 Then
        value = basePct + spanPct
    Else
        If currentCount < 0 Then currentCount = 0
        If currentCount > totalCount Then currentCount = totalCount
        ratio = CDbl(currentCount) / CDbl(totalCount)
        value = basePct + CLng(CDbl(spanPct) * ratio)
    End If

    ResolvePhasePercent = ClampProgressPct(value)
End Function

Private Function BuildExtractProgressText(ByVal phaseName As String, _
                                          ByVal currentCount As Long, _
                                          ByVal totalCount As Long, _
                                          ByVal detail As String, _
                                          ByVal phaseStart As Double, _
                                          ByVal absolutePct As Long) As String
    Dim safeCurrent As Long
    Dim safeTotal As Long
    Dim msg As String

    safeCurrent = currentCount
    safeTotal = totalCount

    If safeCurrent < 0 Then safeCurrent = 0
    If safeTotal < 0 Then safeTotal = 0
    If safeTotal > 0 And safeCurrent > safeTotal Then safeCurrent = safeTotal

    msg = phaseName & ": " & CStr(safeCurrent) & "/" & CStr(safeTotal)
    If Len(Trim$(detail)) > 0 Then msg = msg & " - " & detail

    BuildExtractProgressText = msg & " | " & BuildCombinedEtaText(absolutePct, phaseStart, safeCurrent, safeTotal)
End Function

Private Function BuildCombinedEtaText(ByVal absolutePct As Long, _
                                      ByVal phaseStart As Double, _
                                      ByVal currentCount As Long, _
                                      ByVal totalCount As Long) As String
    Dim elapsedSeconds As Double
    Dim remainingSeconds As Double
    Dim etaTimestamp As Date
    Dim progressRatio As Double

    If Not mCombinedEtaActive Then
        BuildCombinedEtaText = BuildEtaText(phaseStart, currentCount, totalCount)
        Exit Function
    End If

    progressRatio = CDbl(absolutePct - mCombinedEtaBasePct) / CDbl(mCombinedEtaSpanPct)
    If progressRatio < 0# Then progressRatio = 0#
    If progressRatio > 1# Then progressRatio = 1#

    If progressRatio <= 0.02 Then
        BuildCombinedEtaText = "ETA calculating..."
        Exit Function
    End If

    elapsedSeconds = ElapsedSecondsFromTimer(mCombinedEtaStart)
    If elapsedSeconds <= 0 Then
        BuildCombinedEtaText = "ETA calculating..."
        Exit Function
    End If

    remainingSeconds = elapsedSeconds * ((1# - progressRatio) / progressRatio)
    If remainingSeconds < 0 Then remainingSeconds = 0

    etaTimestamp = Now + (remainingSeconds / 86400#)
    BuildCombinedEtaText = "ETA " & Format$(etaTimestamp, "hh:nn:ss") & " (ca. " & FormatDurationHms(remainingSeconds) & " tilbage)"
End Function

Private Function BuildEtaText(ByVal phaseStart As Double, _
                              ByVal currentCount As Long, _
                              ByVal totalCount As Long) As String
    Dim elapsedSeconds As Double
    Dim secondsPerUnit As Double
    Dim remainingSeconds As Double
    Dim etaTimestamp As Date

    If totalCount <= 0 Then
        BuildEtaText = "ETA n/a"
        Exit Function
    End If

    If currentCount <= 1 Then
        BuildEtaText = "ETA calculating..."
        Exit Function
    End If

    elapsedSeconds = ElapsedSecondsFromTimer(phaseStart)
    If elapsedSeconds <= 0 Then
        BuildEtaText = "ETA calculating..."
        Exit Function
    End If

    secondsPerUnit = elapsedSeconds / CDbl(currentCount)
    remainingSeconds = secondsPerUnit * CDbl(totalCount - currentCount)
    If remainingSeconds < 0 Then remainingSeconds = 0

    etaTimestamp = Now + (remainingSeconds / 86400#)
    BuildEtaText = "ETA " & Format$(etaTimestamp, "hh:nn:ss") & " (ca. " & FormatDurationHms(remainingSeconds) & " tilbage)"
End Function

Private Function ElapsedSecondsFromTimer(ByVal phaseStart As Double) As Double
    Dim nowStamp As Double

    nowStamp = Timer
    If nowStamp < phaseStart Then nowStamp = nowStamp + 86400#

    ElapsedSecondsFromTimer = nowStamp - phaseStart
End Function

Private Function FormatDurationHms(ByVal totalSeconds As Double) As String
    Dim wholeSeconds As Long
    Dim hours As Long
    Dim minutes As Long
    Dim seconds As Long

    If totalSeconds < 0 Then totalSeconds = 0

    wholeSeconds = CLng(totalSeconds + 0.5)
    hours = wholeSeconds \ 3600
    minutes = (wholeSeconds Mod 3600) \ 60
    seconds = wholeSeconds Mod 60

    FormatDurationHms = Right$("00" & CStr(hours), 2) & ":" & _
                        Right$("00" & CStr(minutes), 2) & ":" & _
                        Right$("00" & CStr(seconds), 2)
End Function

Private Function ClampProgressPct(ByVal value As Long) As Long
    If value < 0 Then
        ClampProgressPct = 0
    ElseIf value > 100 Then
        ClampProgressPct = 100
    Else
        ClampProgressPct = value
    End If
End Function

Private Sub ResetCombinedEtaContext()
    mCombinedEtaActive = False
    mCombinedEtaStart = 0
    mCombinedEtaBasePct = 0
    mCombinedEtaSpanPct = 0
End Sub
