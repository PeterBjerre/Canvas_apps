Attribute VB_Name = "modCompare"
'===========================
' modCompare  –  Ren VBA Compare Engine
'
' Erstatter modPythonCompare: sammenligner ordre-operationer
' med taskliste-operationer felt-for-felt, uden PY()-afhaengighed.
'
' Output-ark:
'   Compare_Map      – AUFNR → Tasklist_Key mapping
'   Compare_Results  – Operation-niveau status (MATCH/MISMATCH/MISSING)
'   Compare_Diff     – Kun afvigelser (input til Cockpit)
'   Compare_Summary  – Aggregerede tael per AUFNR
'===========================
Option Explicit

' ---------------------------------------------------------------
'  PUBLIC ENTRY POINT  (same signature as RunPythonCompareWithStatus)
' ---------------------------------------------------------------
Public Function RunCompareWithStatus() As String
    On Error GoTo EH

    Dim missingInputs As String
    missingInputs = ValidateInputSheets()
    If Len(missingInputs) > 0 Then
        RunCompareWithStatus = "Compare overstaet: mangler input-ark: " & missingInputs
        Exit Function
    End If

    Dim wsHeader As Worksheet:   Set wsHeader = ThisWorkbook.Worksheets(WS_RAW_ORDRE_HEADER)
    Dim wsItem As Worksheet:     Set wsItem = ThisWorkbook.Worksheets(WS_ITEM_EXTRACT)
    Dim wsOrderOps As Worksheet: Set wsOrderOps = ThisWorkbook.Worksheets(WS_RAW_ORDRE_OPERATIONS)
    Dim wsTaskOps As Worksheet:  Set wsTaskOps = ThisWorkbook.Worksheets(WS_TASKLIST_EXTRACT)

    Dim wsOrderComp As Worksheet: Set wsOrderComp = GetWorksheetIfExists(WS_RAW_ORDRE_COMPONENTS)
    Dim wsTaskComp As Worksheet:  Set wsTaskComp = GetWorksheetIfExists(WS_RAW_TASKLIST_COMPONENTS)
    Dim wsOrderAtt As Worksheet:  Set wsOrderAtt = GetWorksheetIfExists(WS_RAW_ORDRE_ATTACHMENTS)
    Dim wsTaskAtt As Worksheet:   Set wsTaskAtt = GetWorksheetIfExists(WS_RAW_TASKLIST_ATTACHMENTS)

    ' Read all input data into memory arrays (single .Value read per sheet)
    Dim hdrData As Variant: hdrData = ReadSheetData(wsHeader)
    Dim itmData As Variant: itmData = ReadSheetData(wsItem)
    Dim oopData As Variant: oopData = ReadSheetData(wsOrderOps)
    Dim topData As Variant: topData = ReadSheetData(wsTaskOps)
    Dim ocomData As Variant: ocomData = ReadSheetData(wsOrderComp)
    Dim tcomData As Variant: tcomData = ReadSheetData(wsTaskComp)
    Dim oattData As Variant: oattData = ReadSheetData(wsOrderAtt)
    Dim tattData As Variant: tattData = ReadSheetData(wsTaskAtt)

    ' Resolve column indices via fuzzy header matching
    Dim hdrCols As Object: Set hdrCols = BuildColumnMap(hdrData)
    Dim itmCols As Object: Set itmCols = BuildColumnMap(itmData)
    Dim oopCols As Object: Set oopCols = BuildColumnMap(oopData)
    Dim topCols As Object: Set topCols = BuildColumnMap(topData)
    Dim ocomCols As Object: Set ocomCols = BuildColumnMap(ocomData)
    Dim tcomCols As Object: Set tcomCols = BuildColumnMap(tcomData)
    Dim oattCols As Object: Set oattCols = BuildColumnMap(oattData)
    Dim tattCols As Object: Set tattCols = BuildColumnMap(tattData)

    ' Header columns
    Dim c_auf As Long:  c_auf = ResolveCol(hdrCols, Array("Order_number", "Aufnr", "AUFNR"))
    Dim c_wap As Long:  c_wap = ResolveCol(hdrCols, Array("Maintenance_item", "IW33_WAPOS"))
    Dim c_hlt As Long:  c_hlt = ResolveCol(hdrCols, Array("LongText", "Longtext", "Long_Text"))
    Dim c_hpr As Long:  c_hpr = ResolveCol(hdrCols, Array("Priority", "Priok"))
    Dim c_hmw As Long:  c_hmw = ResolveCol(hdrCols, Array("Main_WorkCtr", "Main_Work_Ctr", "Vaplz"))
    Dim c_hfl As Long:  c_hfl = ResolveCol(hdrCols, Array("Functional_loc", "Functional_Loc", "Tplnr"))

    ' Item columns
    Dim c_iwap As Long: c_iwap = ResolveCol(itmCols, Array("Maintenance_item", "Source_Item_Number", "RMIPM-WAPOS"))
    Dim c_pln As Long:  c_pln = ResolveCol(itmCols, Array("Task_LstGrp", "RMIPM-PLNNR"))
    Dim c_pal As Long:  c_pal = ResolveCol(itmCols, Array("GrpCr", "RMIPM-PLNAL"))
    Dim c_ilt As Long:  c_ilt = ResolveCol(itmCols, Array("Long_Text", "Item_LongText", "LongText", "Longtext"))
    Dim c_ipr As Long:  c_ipr = ResolveCol(itmCols, Array("Priority", "Priok"))
    Dim c_imw As Long:  c_imw = ResolveCol(itmCols, Array("Main_WorkCtr", "Main_Work_Ctr", "Vaplz"))
    Dim c_ifl As Long:  c_ifl = ResolveCol(itmCols, Array("Functional_loc", "Functional_Loc", "Tplnr"))

    ' Order operation columns
    Dim c_oauf As Long: c_oauf = ResolveCol(oopCols, Array("Order_number", "Aufnr", "AUFNR"))
    Dim c_ovor As Long: c_ovor = ResolveCol(oopCols, Array("Act", "VORNR", "Vornr", "Operation"))
    Dim c_oste As Long: c_oste = ResolveCol(oopCols, Array("Ctrl", "Steus", "STEUS", "ControlKey"))
    Dim c_oarb As Long: c_oarb = ResolveCol(oopCols, Array("Work_Ctr", "Arbpl", "ARBPL", "WorkCenter"))
    Dim c_oltx As Long: c_oltx = ResolveCol(oopCols, Array("Operation_Description", "Ltxa1", "LTXA1"))
    Dim c_oarb2 As Long: c_oarb2 = ResolveCol(oopCols, Array("Work", "Arbei", "ARBEI", "WorkQty"))
    Dim c_olng As Long: c_olng = ResolveCol(oopCols, Array("Operation_Long_Text", "LongText", "Longtext"))
    Dim c_osup As Long: c_osup = ResolveCol(oopCols, Array("Supplier", "Lifnr", "LIFNR"))

    ' Task operation columns
    Dim c_tsrc As Long: c_tsrc = ResolveCol(topCols, Array("Task_LstGrp/GrpCr", "Source_Item_Number"))
    Dim c_tvor As Long: c_tvor = ResolveCol(topCols, Array("Act", "PLPOD-VORNR", "VORNR"))
    Dim c_tste As Long: c_tste = ResolveCol(topCols, Array("Ctrl", "PLPOD-STEUS", "STEUS"))
    Dim c_tarb As Long: c_tarb = ResolveCol(topCols, Array("Work_Ctr", "PLPOD-ARBPL", "ARBPL"))
    Dim c_tltx As Long: c_tltx = ResolveCol(topCols, Array("Operation_Description", "PLPOD-LTXA1", "LTXA1"))
    Dim c_tarb2 As Long: c_tarb2 = ResolveCol(topCols, Array("Work", "PLPOD-ARBEI", "ARBEI"))
    Dim c_tlng As Long: c_tlng = ResolveCol(topCols, Array("Operation_Long_Text", "Operation_LongText", "LongText"))
    Dim c_tsup As Long: c_tsup = ResolveCol(topCols, Array("Supplier", "LIFNR"))

    ' Order component columns
    Dim c_ocom_auf As Long: c_ocom_auf = ResolveCol(ocomCols, Array("Order_number", "Aufnr", "AUFNR"))
    Dim c_ocom_vor As Long: c_ocom_vor = ResolveCol(ocomCols, Array("Act", "VORNR", "Vornr", "Operation", "Activity"))
    Dim c_ocom_mat As Long: c_ocom_mat = ResolveCol(ocomCols, Array("Material", "MaterialNumber", "IDNRK"))
    Dim c_ocom_qty As Long: c_ocom_qty = ResolveCol(ocomCols, Array("Quantity", "Menge", "MENGE"))
    Dim c_ocom_un As Long: c_ocom_un = ResolveCol(ocomCols, Array("Un", "Unit", "MEINS", "BaseUnitOfMeasure"))
    Dim c_ocom_des As Long: c_ocom_des = ResolveCol(ocomCols, Array("Component_Description", "MaterialDescription", "Description", "Maktx"))

    ' Task component columns
    Dim c_tcom_tsk As Long: c_tcom_tsk = ResolveCol(tcomCols, Array("Task_LstGrp/GrpCr", "Source_Item_Number"))
    Dim c_tcom_vor As Long: c_tcom_vor = ResolveCol(tcomCols, Array("Act", "VORNR", "Vornr", "Operation"))
    Dim c_tcom_mat As Long: c_tcom_mat = ResolveCol(tcomCols, Array("Material", "MaterialNumber", "IDNRK"))
    Dim c_tcom_qty As Long: c_tcom_qty = ResolveCol(tcomCols, Array("Quantity", "Menge", "MENGE"))
    Dim c_tcom_un As Long: c_tcom_un = ResolveCol(tcomCols, Array("Un", "Unit", "MEINS"))
    Dim c_tcom_des As Long: c_tcom_des = ResolveCol(tcomCols, Array("Component_Description", "Description", "Maktx"))

    ' Order attachment columns
    Dim c_oatt_auf As Long: c_oatt_auf = ResolveCol(oattCols, Array("Order_number", "Aufnr", "AUFNR"))
    Dim c_oatt_vor As Long: c_oatt_vor = ResolveCol(oattCols, Array("Act", "VORNR", "Vornr", "Operation"))
    Dim c_oatt_doc As Long: c_oatt_doc = ResolveCol(oattCols, Array("Document", "DocumentNumber", "DOKNR"))
    Dim c_oatt_des As Long: c_oatt_des = ResolveCol(oattCols, Array("Description", "DKTXT"))
    Dim c_oatt_org As Long: c_oatt_org = ResolveCol(oattCols, Array("Original", "Url", "FILEP"))

    ' Task attachment columns
    Dim c_tatt_tsk As Long: c_tatt_tsk = ResolveCol(tattCols, Array("Task_LstGrp/GrpCr", "Source_Item_Number"))
    Dim c_tatt_vor As Long: c_tatt_vor = ResolveCol(tattCols, Array("Act", "VORNR", "Vornr", "Operation"))
    Dim c_tatt_doc As Long: c_tatt_doc = ResolveCol(tattCols, Array("Document", "DocumentNumber", "DOKNR"))
    Dim c_tatt_des As Long: c_tatt_des = ResolveCol(tattCols, Array("Description", "DKTXT"))
    Dim c_tatt_org As Long: c_tatt_org = ResolveCol(tattCols, Array("Original", "Url", "FILEP"))

    If c_auf = 0 Or c_wap = 0 Then Err.Raise 5, , "Compare mangler noedvendige kolonner i " & WS_RAW_ORDRE_HEADER
    If c_iwap = 0 Or c_pln = 0 Or c_pal = 0 Then Err.Raise 5, , "Compare mangler noedvendige kolonner i " & WS_ITEM_EXTRACT
    If c_oauf = 0 Or c_ovor = 0 Then Err.Raise 5, , "Compare mangler noedvendige kolonner i " & WS_RAW_ORDRE_OPERATIONS
    If c_tsrc = 0 Or c_tvor = 0 Then Err.Raise 5, , "Compare mangler noedvendige kolonner i " & WS_TASKLIST_EXTRACT

    ' Build lookup dictionaries
    Dim itemByWap As Object:     Set itemByWap = BuildItemByWapos(itmData, c_iwap)
    Dim oopByOrder As Object:    Set oopByOrder = BuildOpsByKey(oopData, c_oauf, c_ovor)
    Dim topByTask As Object:     Set topByTask = BuildOpsByKey(topData, c_tsrc, c_tvor)
    Dim ocomByOrder As Object:   Set ocomByOrder = BuildRowsByDualKey(ocomData, c_ocom_auf, c_ocom_vor, c_ocom_mat)
    Dim tcomByTask As Object:    Set tcomByTask = BuildRowsByDualKey(tcomData, c_tcom_tsk, c_tcom_vor, c_tcom_mat)
    Dim oattByOrder As Object:   Set oattByOrder = BuildRowsByDualKey(oattData, c_oatt_auf, c_oatt_vor, c_oatt_doc)
    Dim tattByTask As Object:    Set tattByTask = BuildRowsByDualKey(tattData, c_tatt_tsk, c_tatt_vor, c_tatt_doc)

    ' Output accumulators  (Collection of Variant arrays)
    Dim rowsMap As Collection:     Set rowsMap = New Collection
    Dim rowsRes As Collection:     Set rowsRes = New Collection
    Dim rowsDiff As Collection:    Set rowsDiff = New Collection
    Dim rowsComp As Collection:    Set rowsComp = New Collection
    Dim rowsAtt As Collection:     Set rowsAtt = New Collection
    Dim rowsLong As Collection:    Set rowsLong = New Collection
    Dim sumByOrder As Object:      Set sumByOrder = CreateObject("Scripting.Dictionary")

    ' ---------------------------------------------------------------
    '  MAIN COMPARE LOOP  –  iterate header rows
    ' ---------------------------------------------------------------
    Dim r As Long
    Dim auf As String, wap As String, task As String, mstat As String
    Dim pln As String, pal As String
    Dim itmRow As Long
    Dim ordOps As Object, tskOps As Object
    Dim opKeys As Object, opKey As Variant
    Dim ooRow As Long, ttRow As Long
    Dim hlt As String, ilt As String
    Dim itemMm As String
    Dim ordComp As Object, tskComp As Object, compKeys As Object
    Dim ordAtt As Object, tskAtt As Object, attKeys As Object

    If IsEmpty(hdrData) Then GoTo WriteOutput

    For r = 2 To UBound(hdrData, 1)
        auf = NormVal(hdrData, r, c_auf)
        If Len(auf) = 0 Then GoTo NextHeader

        wap = NormVal(hdrData, r, c_wap)

        ' Lookup item by WAPOS
        itmRow = 0
        task = vbNullString
        If itemByWap.Exists(wap) Then
            itmRow = CLng(itemByWap(wap))
            pln = NormVal(itmData, itmRow, c_pln)
            pal = NormVal(itmData, itmRow, c_pal)
            If Len(pln) > 0 And Len(pal) > 0 Then task = pln & "/" & pal
        End If

        ' Determine map status
        mstat = "OK"
        If Len(wap) = 0 Then
            mstat = "MISSING_WAPOS"
        ElseIf itmRow = 0 Then
            mstat = "ITEM_NOT_FOUND"
        ElseIf Len(task) = 0 Then
            mstat = "MISSING_TASK_KEY"
        End If

        ' Get operation dictionaries for this order/task
        Set ordOps = GetNestedDict(oopByOrder, auf)
        Set tskOps = GetNestedDict(topByTask, task)
        Set ordComp = GetNestedDict(ocomByOrder, auf)
        Set tskComp = GetNestedDict(tcomByTask, task)
        Set ordAtt = GetNestedDict(oattByOrder, auf)
        Set tskAtt = GetNestedDict(tattByTask, task)

        ' Map row
        rowsMap.Add Array(auf, wap, task, ordOps.Count, tskOps.Count, mstat)

        ' Union of operation keys
        Set opKeys = UnionKeys(ordOps, tskOps)

        Dim k As Variant
        For Each k In opKeys.Keys
            ooRow = 0: ttRow = 0
            If ordOps.Exists(k) Then ooRow = CLng(ordOps(k))
            If tskOps.Exists(k) Then ttRow = CLng(tskOps(k))

            If ooRow = 0 Then
                ' Missing in order
                BumpSummary sumByOrder, auf, "Compared"
                BumpSummary sumByOrder, auf, "MissingInOrder"
                rowsRes.Add Array(auf, task, CStr(k), "MISSING_IN_ORDER", "Operation findes ikke i ordre")
                rowsDiff.Add Array(auf, task, CStr(k), "Operation", vbNullString, NormVal(topData, ttRow, c_tltx), "MISSING_IN_ORDER", "Operation")
                GoTo NextOp
            End If

            If ttRow = 0 Then
                ' Missing in tasklist
                BumpSummary sumByOrder, auf, "Compared"
                BumpSummary sumByOrder, auf, "MissingInTask"
                rowsRes.Add Array(auf, task, CStr(k), "MISSING_IN_TASKLIST", "Operation findes ikke i tasklist")
                rowsDiff.Add Array(auf, task, CStr(k), "Operation", NormVal(oopData, ooRow, c_oltx), vbNullString, "MISSING_IN_TASKLIST", "Operation")
                GoTo NextOp
            End If

            ' Compare fields
            Dim mm As String: mm = vbNullString
            BumpSummary sumByOrder, auf, "Compared"

            CompareField oopData, ooRow, c_oste, topData, ttRow, c_tste, "STEUS", "Operation", auf, task, CStr(k), mm, rowsDiff
            CompareField oopData, ooRow, c_oarb, topData, ttRow, c_tarb, "ARBPL", "Operation", auf, task, CStr(k), mm, rowsDiff
            CompareField oopData, ooRow, c_oltx, topData, ttRow, c_tltx, "LTXA1", "Operation", auf, task, CStr(k), mm, rowsDiff
            CompareField oopData, ooRow, c_oarb2, topData, ttRow, c_tarb2, "ARBEI", "Operation", auf, task, CStr(k), mm, rowsDiff
            If c_osup > 0 And c_tsup > 0 Then
                CompareField oopData, ooRow, c_osup, topData, ttRow, c_tsup, "LIFNR", "Operation", auf, task, CStr(k), mm, rowsDiff
            End If

            Dim opLongSAP As String, opLongVH As String
            opLongSAP = NormVal(oopData, ooRow, c_olng)
            opLongVH = NormVal(topData, ttRow, c_tlng)
            If NormText(opLongSAP) <> NormText(opLongVH) Then
                If Len(mm) > 0 Then mm = mm & ","
                mm = mm & "LONGTEXT"
                rowsDiff.Add Array(auf, task, CStr(k), "LONGTEXT", opLongSAP, opLongVH, "MISMATCH", "LongText")
                rowsLong.Add Array(auf, task, CStr(k), "OP_LONGTEXT", opLongSAP, opLongVH, "MISMATCH")
            End If

            If Len(mm) > 0 Then
                BumpSummary sumByOrder, auf, "Mismatched"
                rowsRes.Add Array(auf, task, CStr(k), "MISMATCH", mm)
            Else
                BumpSummary sumByOrder, auf, "Matched"
                rowsRes.Add Array(auf, task, CStr(k), "MATCH", vbNullString)
            End If
NextOp:
        Next k

        ' Compare item fields (Order header vs Item)
        itemMm = vbNullString
        If itmRow > 0 Then
            If c_hpr > 0 And c_ipr > 0 Then
                CompareField hdrData, r, c_hpr, itmData, itmRow, c_ipr, "PRIORITY", "Item", auf, task, vbNullString, itemMm, rowsDiff
            End If
            If c_hmw > 0 And c_imw > 0 Then
                CompareField hdrData, r, c_hmw, itmData, itmRow, c_imw, "MAIN_WORKCTR", "Item", auf, task, vbNullString, itemMm, rowsDiff
            End If
            If c_hfl > 0 And c_ifl > 0 Then
                CompareField hdrData, r, c_hfl, itmData, itmRow, c_ifl, "FUNCTIONAL_LOC", "Item", auf, task, vbNullString, itemMm, rowsDiff
            End If
        End If

        ' Compare header longtext vs item longtext
        hlt = NormVal(hdrData, r, c_hlt)
        ilt = vbNullString
        If itmRow > 0 Then ilt = NormVal(itmData, itmRow, c_ilt)
        If itmRow > 0 And (Len(hlt) > 0 Or Len(ilt) > 0) Then
            If NormText(hlt) <> NormText(ilt) Then
                rowsDiff.Add Array(auf, task, vbNullString, "Header_LongText", hlt, ilt, "MISMATCH", "LongText")
                rowsLong.Add Array(auf, task, vbNullString, "ITEM_LONGTEXT", hlt, ilt, "MISMATCH")
            End If
        End If

        ' Compare components by Operation + Material
        Set compKeys = UnionKeys(ordComp, tskComp)
        Dim ck As Variant
        For Each ck In compKeys.Keys
            Dim ocRow As Long, tcRow As Long
            Dim compVornr As String, compMaterial As String
            Dim oq As String, tq As String, ou As String, tu As String, od As String, td As String
            Dim compMm As String

            ocRow = 0: tcRow = 0
            If ordComp.Exists(ck) Then ocRow = CLng(ordComp(ck))
            If tskComp.Exists(ck) Then tcRow = CLng(tskComp(ck))

            compVornr = DualKeyOp(CStr(ck))
            compMaterial = DualKeySub(CStr(ck))

            If ocRow = 0 Then
                tq = NormVal(tcomData, tcRow, c_tcom_qty)
                tu = NormVal(tcomData, tcRow, c_tcom_un)
                td = NormVal(tcomData, tcRow, c_tcom_des)
                rowsComp.Add Array(auf, task, compVornr, compMaterial, "MISSING_IN_ORDER", vbNullString, tq, vbNullString, tu, vbNullString, td, "MISSING_IN_ORDER")
                rowsDiff.Add Array(auf, task, compVornr, "COMPONENT", vbNullString, compMaterial, "MISSING_IN_ORDER", "Component")
                GoTo NextComp
            End If

            If tcRow = 0 Then
                oq = NormVal(ocomData, ocRow, c_ocom_qty)
                ou = NormVal(ocomData, ocRow, c_ocom_un)
                od = NormVal(ocomData, ocRow, c_ocom_des)
                rowsComp.Add Array(auf, task, compVornr, compMaterial, "MISSING_IN_TASKLIST", oq, vbNullString, ou, vbNullString, od, vbNullString, "MISSING_IN_TASKLIST")
                rowsDiff.Add Array(auf, task, compVornr, "COMPONENT", compMaterial, vbNullString, "MISSING_IN_TASKLIST", "Component")
                GoTo NextComp
            End If

            oq = NormVal(ocomData, ocRow, c_ocom_qty)
            tq = NormVal(tcomData, tcRow, c_tcom_qty)
            ou = NormVal(ocomData, ocRow, c_ocom_un)
            tu = NormVal(tcomData, tcRow, c_tcom_un)
            od = NormVal(ocomData, ocRow, c_ocom_des)
            td = NormVal(tcomData, tcRow, c_tcom_des)

            compMm = vbNullString
            If NormText(oq) <> NormText(tq) Then
                compMm = "QTY"
                rowsDiff.Add Array(auf, task, compVornr, "COMPONENT_QTY", oq, tq, "MISMATCH", "Component")
            End If
            If NormText(ou) <> NormText(tu) Then
                If Len(compMm) > 0 Then compMm = compMm & ","
                compMm = compMm & "UNIT"
                rowsDiff.Add Array(auf, task, compVornr, "COMPONENT_UN", ou, tu, "MISMATCH", "Component")
            End If
            If NormText(od) <> NormText(td) Then
                If Len(compMm) > 0 Then compMm = compMm & ","
                compMm = compMm & "DESC"
                rowsDiff.Add Array(auf, task, compVornr, "COMPONENT_DESC", od, td, "MISMATCH", "Component")
            End If

            If Len(compMm) > 0 Then
                rowsComp.Add Array(auf, task, compVornr, compMaterial, "MISMATCH", oq, tq, ou, tu, od, td, compMm)
            Else
                rowsComp.Add Array(auf, task, compVornr, compMaterial, "MATCH", oq, tq, ou, tu, od, td, vbNullString)
            End If
NextComp:
        Next ck

        ' Compare attachments by Operation + Document
        Set attKeys = UnionKeys(ordAtt, tskAtt)
        Dim ak As Variant
        For Each ak In attKeys.Keys
            Dim oaRow As Long, taRow As Long
            Dim attVornr As String, attDoc As String
            Dim odc As String, tdc As String, oor As String, tor As String
            Dim attMm As String

            oaRow = 0: taRow = 0
            If ordAtt.Exists(ak) Then oaRow = CLng(ordAtt(ak))
            If tskAtt.Exists(ak) Then taRow = CLng(tskAtt(ak))

            attVornr = DualKeyOp(CStr(ak))
            attDoc = DualKeySub(CStr(ak))

            If oaRow = 0 Then
                tdc = NormVal(tattData, taRow, c_tatt_des)
                tor = NormVal(tattData, taRow, c_tatt_org)
                rowsAtt.Add Array(auf, task, attVornr, attDoc, "MISSING_IN_ORDER", vbNullString, tdc, vbNullString, tor, "MISSING_IN_ORDER")
                rowsDiff.Add Array(auf, task, attVornr, "ATTACHMENT", vbNullString, attDoc, "MISSING_IN_ORDER", "Attachment")
                GoTo NextAtt
            End If

            If taRow = 0 Then
                odc = NormVal(oattData, oaRow, c_oatt_des)
                oor = NormVal(oattData, oaRow, c_oatt_org)
                rowsAtt.Add Array(auf, task, attVornr, attDoc, "MISSING_IN_TASKLIST", odc, vbNullString, oor, vbNullString, "MISSING_IN_TASKLIST")
                rowsDiff.Add Array(auf, task, attVornr, "ATTACHMENT", attDoc, vbNullString, "MISSING_IN_TASKLIST", "Attachment")
                GoTo NextAtt
            End If

            odc = NormVal(oattData, oaRow, c_oatt_des)
            tdc = NormVal(tattData, taRow, c_tatt_des)
            oor = NormVal(oattData, oaRow, c_oatt_org)
            tor = NormVal(tattData, taRow, c_tatt_org)

            attMm = vbNullString
            If NormText(odc) <> NormText(tdc) Then
                attMm = "DESC"
                rowsDiff.Add Array(auf, task, attVornr, "ATTACH_DESC", odc, tdc, "MISMATCH", "Attachment")
            End If
            If NormText(oor) <> NormText(tor) Then
                If Len(attMm) > 0 Then attMm = attMm & ","
                attMm = attMm & "ORIGINAL"
                rowsDiff.Add Array(auf, task, attVornr, "ATTACH_ORIGINAL", oor, tor, "MISMATCH", "Attachment")
            End If

            If Len(attMm) > 0 Then
                rowsAtt.Add Array(auf, task, attVornr, attDoc, "MISMATCH", odc, tdc, oor, tor, attMm)
            Else
                rowsAtt.Add Array(auf, task, attVornr, attDoc, "MATCH", odc, tdc, oor, tor, vbNullString)
            End If
NextAtt:
        Next ak
NextHeader:
    Next r

    ' ---------------------------------------------------------------
    '  WRITE OUTPUT SHEETS
    ' ---------------------------------------------------------------
WriteOutput:
    WriteOutputSheet WS_COMPARE_MAP, _
        Array("AUFNR", "Maintenance_item", "Tasklist_Key", "OrderOpCount", "TaskOpCount", "Map_Status"), _
        rowsMap

    WriteOutputSheet WS_COMPARE_RESULTS, _
        Array("AUFNR", "Tasklist_Key", "VORNR", "Compare_Status", "Mismatch_Reasons"), _
        rowsRes

    WriteOutputSheet WS_COMPARE_DIFF, _
        Array("AUFNR", "Tasklist_Key", "VORNR", "Field", "SAP_Value", "VH_Value", "ReasonCode", "Scope"), _
        rowsDiff

    WriteOutputSheet WS_COMPARE_COMPONENTS, _
        Array("AUFNR", "Tasklist_Key", "VORNR", "Material", "Compare_Status", "Order_Quantity", "Task_Quantity", "Order_Un", "Task_Un", "Order_Description", "Task_Description", "Mismatch_Reasons"), _
        rowsComp

    WriteOutputSheet WS_COMPARE_ATTACHMENTS, _
        Array("AUFNR", "Tasklist_Key", "VORNR", "Document", "Compare_Status", "Order_Description", "Task_Description", "Order_Original", "Task_Original", "Mismatch_Reasons"), _
        rowsAtt

    WriteOutputSheet WS_COMPARE_LONGTEXT, _
        Array("AUFNR", "Tasklist_Key", "VORNR", "Field", "SAP_Value", "VH_Value", "ReasonCode"), _
        rowsLong

    WriteSummarySheet sumByOrder

    RunCompareWithStatus = vbNullString
    Exit Function
EH:
    RunCompareWithStatus = "Compare fejlede: " & Err.Description
End Function


' ---------------------------------------------------------------
'  INPUT VALIDATION
' ---------------------------------------------------------------
Private Function ValidateInputSheets() As String
    Dim names As Variant, i As Long, ws As Worksheet, missing As String
    names = Array(WS_RAW_ORDRE_HEADER, WS_ITEM_EXTRACT, WS_RAW_ORDRE_OPERATIONS, WS_TASKLIST_EXTRACT)

    For i = LBound(names) To UBound(names)
        On Error Resume Next
        Set ws = ThisWorkbook.Worksheets(CStr(names(i)))
        On Error GoTo 0
        If ws Is Nothing Then
            If Len(missing) > 0 Then missing = missing & ", "
            missing = missing & CStr(names(i))
        End If
        Set ws = Nothing
    Next i
    ValidateInputSheets = missing
End Function


' ---------------------------------------------------------------
'  SHEET DATA READER  (single bulk read)
' ---------------------------------------------------------------
Private Function ReadSheetData(ByVal ws As Worksheet) As Variant
    Dim lr As Long, lc As Long, lastCell As Range

    On Error Resume Next
    Set lastCell = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    On Error GoTo 0
    If lastCell Is Nothing Then Exit Function
    lr = lastCell.Row

    On Error Resume Next
    Set lastCell = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    On Error GoTo 0
    If lastCell Is Nothing Then Exit Function
    lc = lastCell.Column

    If lr < 2 Or lc < 1 Then Exit Function
    ReadSheetData = ws.Range(ws.Cells(1, 1), ws.Cells(lr, lc)).Value
End Function


' ---------------------------------------------------------------
'  COLUMN RESOLUTION  (normalised header name → column index)
' ---------------------------------------------------------------
Private Function BuildColumnMap(ByRef data As Variant) As Object
    Dim d As Object
    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    If IsEmpty(data) Then
        Set BuildColumnMap = d
        Exit Function
    End If

    Dim c As Long
    For c = 1 To UBound(data, 2)
        Dim hdr As String
        hdr = NormText(CStr(data(1, c)))
        If Len(hdr) > 0 Then
            If Not d.Exists(hdr) Then d.Add hdr, c
        End If
    Next c

    Set BuildColumnMap = d
End Function

Private Function ResolveCol(ByVal colMap As Object, ByVal candidates As Variant) As Long
    Dim i As Long
    For i = LBound(candidates) To UBound(candidates)
        Dim key As String
        key = NormText(CStr(candidates(i)))
        If colMap.Exists(key) Then
            ResolveCol = CLng(colMap(key))
            Exit Function
        End If
    Next i
End Function


' ---------------------------------------------------------------
'  LOOKUP DICTIONARIES
' ---------------------------------------------------------------
Private Function BuildItemByWapos(ByRef data As Variant, ByVal colWapos As Long) As Object
    Dim d As Object
    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    If IsEmpty(data) Or colWapos = 0 Then
        Set BuildItemByWapos = d
        Exit Function
    End If

    Dim r As Long, w As String
    For r = 2 To UBound(data, 1)
        w = Trim$(CStr(data(r, colWapos)))
        If Len(w) > 0 Then
            If Not d.Exists(w) Then d.Add w, r
        End If
    Next r

    Set BuildItemByWapos = d
End Function

Private Function BuildOpsByKey(ByRef data As Variant, ByVal colKey As Long, ByVal colVornr As Long) As Object
    ' Returns nested Dictionary:  key → { normalised_vornr → row_number }
    Dim d As Object
    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    If IsEmpty(data) Or colKey = 0 Or colVornr = 0 Then
        Set BuildOpsByKey = d
        Exit Function
    End If

    Dim r As Long, k As String, v As String, inner As Object
    For r = 2 To UBound(data, 1)
        k = Trim$(CStr(data(r, colKey)))
        v = NormOpNumber(CStr(data(r, colVornr)))
        If Len(k) > 0 And Len(v) > 0 Then
            If Not d.Exists(k) Then
                Set inner = CreateObject("Scripting.Dictionary")
                inner.CompareMode = vbTextCompare
                d.Add k, inner
            End If
            If Not d(k).Exists(v) Then d(k).Add v, r
        End If
    Next r

    Set BuildOpsByKey = d
End Function

Private Function BuildRowsByDualKey(ByRef data As Variant, ByVal colGroup As Long, ByVal colOp As Long, ByVal colSub As Long) As Object
    ' Returns nested Dictionary: groupKey -> { op|sub -> row_number }
    Dim d As Object
    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    If IsEmpty(data) Or colGroup = 0 Or colSub = 0 Then
        Set BuildRowsByDualKey = d
        Exit Function
    End If

    Dim r As Long
    Dim g As String, opNo As String, subKey As String
    Dim key As String
    Dim inner As Object

    For r = 2 To UBound(data, 1)
        g = Trim$(CStr(data(r, colGroup)))
        opNo = NormVal(data, r, colOp)
        opNo = NormOpNumber(opNo)
        subKey = UCase$(NormVal(data, r, colSub))

        If Len(g) = 0 Or Len(subKey) = 0 Then GoTo NextRow

        key = BuildDualKey(opNo, subKey)
        If Not d.Exists(g) Then
            Set inner = CreateObject("Scripting.Dictionary")
            inner.CompareMode = vbTextCompare
            d.Add g, inner
        End If
        If Not d(g).Exists(key) Then d(g).Add key, r
NextRow:
    Next r

    Set BuildRowsByDualKey = d
End Function

Private Function BuildDualKey(ByVal opNo As String, ByVal subKey As String) As String
    BuildDualKey = Trim$(opNo) & "|" & Trim$(subKey)
End Function

Private Function DualKeyOp(ByVal key As String) As String
    Dim p As Long
    p = InStr(1, key, "|", vbBinaryCompare)
    If p <= 0 Then
        DualKeyOp = key
    Else
        DualKeyOp = Left$(key, p - 1)
    End If
End Function

Private Function DualKeySub(ByVal key As String) As String
    Dim p As Long
    p = InStr(1, key, "|", vbBinaryCompare)
    If p <= 0 Then
        DualKeySub = vbNullString
    Else
        DualKeySub = Mid$(key, p + 1)
    End If
End Function

Private Function GetWorksheetIfExists(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set GetWorksheetIfExists = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
End Function

Private Function GetNestedDict(ByVal outer As Object, ByVal key As String) As Object
    If Len(key) > 0 And outer.Exists(key) Then
        Set GetNestedDict = outer(key)
    Else
        Set GetNestedDict = CreateObject("Scripting.Dictionary")
    End If
End Function

Private Function UnionKeys(ByVal d1 As Object, ByVal d2 As Object) As Object
    Dim d As Object, k As Variant
    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    For Each k In d1.Keys
        If Not d.Exists(k) Then d.Add k, 1
    Next k
    For Each k In d2.Keys
        If Not d.Exists(k) Then d.Add k, 1
    Next k

    Set UnionKeys = d
End Function


' ---------------------------------------------------------------
'  FIELD COMPARISON
' ---------------------------------------------------------------
Private Sub CompareField(ByRef srcData As Variant, ByVal srcRow As Long, ByVal srcCol As Long, _
                         ByRef tgtData As Variant, ByVal tgtRow As Long, ByVal tgtCol As Long, _
                         ByVal fieldName As String, ByVal scopeName As String, _
                         ByVal auf As String, ByVal task As String, ByVal vornr As String, _
                         ByRef mmList As String, ByVal rowsDiff As Collection)
    Dim lv As String, rv As String
    lv = NormVal(srcData, srcRow, srcCol)
    rv = NormVal(tgtData, tgtRow, tgtCol)

    If NormText(lv) <> NormText(rv) Then
        If Len(mmList) > 0 Then mmList = mmList & ","
        mmList = mmList & fieldName
        rowsDiff.Add Array(auf, task, vornr, fieldName, lv, rv, "MISMATCH", scopeName)
    End If
End Sub


' ---------------------------------------------------------------
'  SUMMARY COUNTER
' ---------------------------------------------------------------
Private Sub BumpSummary(ByVal d As Object, ByVal orderNo As String, ByVal key As String)
    Dim inner As Object
    If Not d.Exists(orderNo) Then
        Set inner = CreateObject("Scripting.Dictionary")
        inner.Add "Compared", CLng(0)
        inner.Add "Matched", CLng(0)
        inner.Add "Mismatched", CLng(0)
        inner.Add "MissingInOrder", CLng(0)
        inner.Add "MissingInTask", CLng(0)
        d.Add orderNo, inner
    End If
    d(orderNo)(key) = CLng(d(orderNo)(key)) + 1
End Sub


' ---------------------------------------------------------------
'  OUTPUT WRITERS  (bulk array writes)
' ---------------------------------------------------------------
Private Sub WriteOutputSheet(ByVal sheetName As String, ByVal headers As Variant, ByVal rows As Collection)
    Dim ws As Worksheet
    Set ws = EnsureCompareSheet(sheetName)
    ws.Cells.Clear

    Dim colCount As Long
    colCount = UBound(headers) - LBound(headers) + 1

    ' Write headers
    Dim hdrArr() As Variant
    ReDim hdrArr(1 To 1, 1 To colCount)
    Dim i As Long
    For i = LBound(headers) To UBound(headers)
        hdrArr(1, i - LBound(headers) + 1) = headers(i)
    Next i
    ws.Range("A1").Resize(1, colCount).Value = hdrArr

    ' Write data rows
    If rows.Count > 0 Then
        Dim arrOut() As Variant
        ReDim arrOut(1 To rows.Count, 1 To colCount)
        Dim r As Long, c As Long
        Dim rowArr As Variant
        For r = 1 To rows.Count
            rowArr = rows(r)
            For c = 0 To UBound(rowArr)
                If c < colCount Then arrOut(r, c + 1) = rowArr(c)
            Next c
        Next r
        ws.Range("A2").Resize(rows.Count, colCount).Value = arrOut
    End If

    ' Format
    With ws.UsedRange
        .Columns.AutoFit
        .rows(1).Font.Bold = True
        .rows(1).Interior.Color = RGB(240, 240, 240)
    End With
End Sub

Private Sub WriteSummarySheet(ByVal sumByOrder As Object)
    Dim ws As Worksheet
    Set ws = EnsureCompareSheet(WS_COMPARE_SUMMARY)
    ws.Cells.Clear

    Dim headers As Variant
    headers = Array("AUFNR", "Compared", "Matched", "Mismatched", "MissingInOrder", "MissingInTask")
    Dim colCount As Long: colCount = 6

    Dim hdrArr() As Variant
    ReDim hdrArr(1 To 1, 1 To colCount)
    Dim i As Long
    For i = 0 To 5
        hdrArr(1, i + 1) = headers(i)
    Next i
    ws.Range("A1").Resize(1, colCount).Value = hdrArr

    If sumByOrder.Count > 0 Then
        Dim arrOut() As Variant
        ReDim arrOut(1 To sumByOrder.Count, 1 To colCount)
        Dim keys As Variant, r As Long
        keys = sumByOrder.Keys
        For r = 0 To sumByOrder.Count - 1
            arrOut(r + 1, 1) = keys(r)
            arrOut(r + 1, 2) = sumByOrder(keys(r))("Compared")
            arrOut(r + 1, 3) = sumByOrder(keys(r))("Matched")
            arrOut(r + 1, 4) = sumByOrder(keys(r))("Mismatched")
            arrOut(r + 1, 5) = sumByOrder(keys(r))("MissingInOrder")
            arrOut(r + 1, 6) = sumByOrder(keys(r))("MissingInTask")
        Next r
        ws.Range("A2").Resize(sumByOrder.Count, colCount).Value = arrOut
    End If

    With ws.UsedRange
        .Columns.AutoFit
        .rows(1).Font.Bold = True
        .rows(1).Interior.Color = RGB(240, 240, 240)
    End With
End Sub


' ---------------------------------------------------------------
'  NORMALISATION HELPERS
' ---------------------------------------------------------------
Private Function NormVal(ByRef data As Variant, ByVal r As Long, ByVal c As Long) As String
    If c = 0 Then Exit Function
    If IsEmpty(data) Then Exit Function
    If r < 1 Or r > UBound(data, 1) Then Exit Function
    If c < 1 Or c > UBound(data, 2) Then Exit Function

    Dim v As Variant
    v = data(r, c)
    If IsNull(v) Or IsEmpty(v) Then Exit Function
    If IsError(v) Then Exit Function
    NormVal = Trim$(CStr(v))
End Function

Private Function NormText(ByVal s As String) As String
    ' Normalise for comparison: lowercase, collapse whitespace
    Dim result As String, i As Long, ch As String, lastWasSpace As Boolean
    s = Trim$(s)
    If Len(s) = 0 Then Exit Function

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch = " " Or ch = vbTab Or ch = vbCr Or ch = vbLf Then
            If Not lastWasSpace Then
                result = result & " "
                lastWasSpace = True
            End If
        Else
            result = result & ch
            lastWasSpace = False
        End If
    Next i

    NormText = LCase$(result)
End Function

Private Function NormOpNumber(ByVal s As String) As String
    ' Extract numeric part from operation number, strip leading zeros
    Dim digits As String, i As Long, ch As String
    s = Trim$(s)
    If Len(s) = 0 Then Exit Function

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch >= "0" And ch <= "9" Then digits = digits & ch
    Next i

    If Len(digits) = 0 Then
        NormOpNumber = LCase$(Trim$(s))
    Else
        NormOpNumber = CStr(CLng(digits))
    End If
End Function


' ---------------------------------------------------------------
'  SHEET HELPER
' ---------------------------------------------------------------
Private Function EnsureCompareSheet(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set EnsureCompareSheet = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If EnsureCompareSheet Is Nothing Then
        Set EnsureCompareSheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        EnsureCompareSheet.Name = sheetName
    End If
End Function
