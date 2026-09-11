Attribute VB_Name = "modLoadSheet"
Option Explicit
'==============================================================================
' modLoadSheet - loader fra arktabellerne (ListObjects), som Power Query
' fylder fra SharePoint-listerne.
'
' Dette er den primaere kilde. modLoadJson er alternativet, naar en enkelt
' anmodning skal koeres fra en fil uden adgang til SharePoint.
'
' Arkene er formet som SAP-SKAERMENE, ikke som datamodellen. Derfor er
' T_Package bred: een raekke pr. operation, een KOLONNE pr. pakke - praecis
' som pakkeallokeringsskaermen i IA01 ser ud.
'==============================================================================

'--- Indlaes alle planer. Returnerer en Collection af plan-Dictionaries. ------
' onlyGuid: udfyld for at koere en enkelt anmodning.
Public Function LoadPlans(Optional ByVal onlyGuid As String = "") As Collection
    Dim plans As Object, result As Collection
    Dim lo As ListObject, c As Object, r As Range
    Dim guid As String, key As String
    Dim plan As Object, tl As Object, op As Object, it As Object
    Dim pkgDef As Object

    Set plans = modContract.NewDict()
    Set result = New Collection

    '--- 1. Planhoveder -------------------------------------------------------
    Set lo = GetTable(SH_PLAN)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        For Each r In lo.DataBodyRange.Rows
            guid = Txt(r, c, "RequestGuid")
            If Len(guid) > 0 And (onlyGuid = "" Or StrComp(guid, onlyGuid, vbTextCompare) = 0) Then
                Set plan = modContract.NewPlan()
                plan("RequestGuid") = guid
                plan("RequestNo") = Txt(r, c, "RequestNo")
                plan("PlanType") = Dflt(Txt(r, c, "PlanType"), "Strategy")
                plan("Description") = Txt(r, c, "Description")
                plan("PlanCategory") = Dflt(Txt(r, c, "PlanCategory"), "PM")
                plan("Plant") = Txt(r, c, "Plant")
                plan("StrategyKey") = Txt(r, c, "StrategyKey")
                plan("SortField") = Dflt(Txt(r, c, "SortField"), Left$(guid, 8))
                plan("CycleStartDate") = Dt(r, c, "CycleStartDate")
                plan("RowIndex") = r.Row
                plan("PlanStatus") = Txt(r, c, "PLAN_Status")
                Set plans(guid) = plan
            End If
        Next r
    End If

    '--- 2. Pakkedefinitioner: ShortCode -> PackageNo -------------------------
    Set pkgDef = LoadPackageDef()

    '--- 3. Arbejdsplaner -----------------------------------------------------
    Set lo = GetTable(SH_TASKLIST)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        For Each r In lo.DataBodyRange.Rows
            guid = Txt(r, c, "RequestGuid")
            If plans.Exists(guid) Then
                Set tl = modContract.NewTaskList()
                tl("TempKey") = Txt(r, c, "TempKey")
                tl("Description") = Txt(r, c, "Description")
                tl("Type") = Dflt(Txt(r, c, "Type"), "E")
                tl("StrategyKey") = Txt(r, c, "StrategyKey")
                tl("Plant") = Txt(r, c, "Plant")
                tl("Usage") = Txt(r, c, "Usage")
                tl("WorkCenter") = Txt(r, c, "WorkCenter")
                tl("PlannerGroup") = Txt(r, c, "PlannerGroup")
                tl("Equipment") = Txt(r, c, "Equipment")
                tl("SapGroup") = Txt(r, c, "TL_Group")
                tl("Status") = Txt(r, c, "TL_Status")
                tl("RowIndex") = r.Row
                plans(guid)("TaskLists").Add tl
            End If
        Next r
    End If

    '--- 4. Operationer -------------------------------------------------------
    Set lo = GetTable(SH_OPERATION)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        For Each r In lo.DataBodyRange.Rows
            guid = Txt(r, c, "RequestGuid")
            If plans.Exists(guid) Then
                Set tl = modContract.FindTaskList(plans(guid), Txt(r, c, "TempKey"))
                If Not tl Is Nothing Then
                    Set op = modContract.NewOperation()
                    op("OperationNo") = PadOp(Txt(r, c, "OperationNo"))
                    op("Description") = Txt(r, c, "Description")
                    op("ControlKey") = Txt(r, c, "ControlKey")
                    op("WorkCenter") = Txt(r, c, "WorkCenter")
                    op("Work") = Txt(r, c, "Work")
                    op("WorkUnit") = Txt(r, c, "WorkUnit")
                    op("NumberOfPeople") = Txt(r, c, "NumberOfPeople")
                    op("Duration") = Txt(r, c, "Duration")
                    op("DurationUnit") = Txt(r, c, "DurationUnit")
                    tl("Operations").Add op
                End If
            End If
        Next r
    End If

    '--- 5. Pakkeallokering: den brede tabel foldes ud til tal ----------------
    Set lo = GetTable(SH_PACKAGE)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        Dim colIdx As Long, hdr As String, opNo As String
        For Each r In lo.DataBodyRange.Rows
            guid = Txt(r, c, "RequestGuid")
            If plans.Exists(guid) Then
                Set tl = modContract.FindTaskList(plans(guid), Txt(r, c, "TempKey"))
                If Not tl Is Nothing Then
                    opNo = PadOp(Txt(r, c, "OperationNo"))
                    Set op = FindOperation(tl, opNo)
                    If Not op Is Nothing Then
                        ' Hver kolonne, der IKKE er en af noeglekolonnerne, er en pakke.
                        For colIdx = 1 To lo.ListColumns.Count
                            hdr = CStr(lo.ListColumns(colIdx).Name)
                            If Not IsKeyColumn(hdr) Then
                                If Len(Trim$(CStr(r.Cells(1, colIdx).value & ""))) > 0 Then
                                    key = UCase$(plans(guid)("StrategyKey") & "|" & hdr)
                                    If pkgDef.Exists(key) Then
                                        op("Packages").Add CLng(pkgDef(key))
                                    Else
                                        Err.Raise vbObjectError + 20, "modLoadSheet", _
                                            "Pakkekolonnen '" & hdr & "' findes ikke i " & SH_PACKAGEDEF & _
                                            " for strategi " & plans(guid)("StrategyKey") & "."
                                    End If
                                End If
                            End If
                        Next colIdx
                    End If
                End If
            End If
        Next r
    End If

    '--- 6. Positioner --------------------------------------------------------
    Set lo = GetTable(SH_ITEM)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        For Each r In lo.DataBodyRange.Rows
            guid = Txt(r, c, "RequestGuid")
            If plans.Exists(guid) Then
                Set it = modContract.NewItem()
                it("ItemNo") = Txt(r, c, "ItemNo")
                it("Description") = Txt(r, c, "Description")
                it("ObjectType") = Dflt(Txt(r, c, "ObjectType"), "Equipment")
                it("Equipment") = Txt(r, c, "Equipment")
                it("FunctionalLocation") = Txt(r, c, "FunctionalLocation")
                it("PlannerGroup") = Txt(r, c, "PlannerGroup")
                it("OrderType") = Txt(r, c, "OrderType")
                it("WorkCenter") = Txt(r, c, "WorkCenter")
                it("Plant") = Txt(r, c, "Plant")
                it("TaskListMode") = Dflt(Txt(r, c, "TaskListMode"), "New")
                it("TaskListRef") = Txt(r, c, "TaskListRef")
                it("TaskListType") = Txt(r, c, "TaskListType")
                it("TaskListGroup") = Txt(r, c, "TaskListGroup")
                it("TaskListCounter") = Txt(r, c, "TaskListCounter")
                plans(guid)("Items").Add it
            End If
        Next r
    End If

    '--- Til Collection i stabil raekkefoelge ---------------------------------
    Dim k As Variant
    For Each k In plans.Keys
        result.Add plans(k)
    Next k
    Set LoadPlans = result
End Function

'==============================================================================
' Pakkedefinitioner
'==============================================================================

' Noegle: "STRATEGI|SHORTCODE" -> PackageNo
Public Function LoadPackageDef() As Object
    Dim lo As ListObject, c As Object, r As Range, d As Object
    Set d = modContract.NewDict()
    Set lo = GetTable(SH_PACKAGEDEF)
    Set c = ColMap(lo)
    If lo.DataBodyRange Is Nothing Then Set LoadPackageDef = d: Exit Function

    For Each r In lo.DataBodyRange.Rows
        If Len(Txt(r, c, "ShortCode")) > 0 Then
            d(UCase$(Txt(r, c, "StrategyKey") & "|" & Txt(r, c, "ShortCode"))) = _
                CLng(Val(Txt(r, c, "PackageNo")))
        End If
    Next r
    Set LoadPackageDef = d
End Function

' Pakkerne for een strategi, sorteret efter PackageNo. Bruges til at bestemme
' kolonnernes raekkefoelge i IA01's pakke-table-control.
Public Function PackagesForStrategy(ByVal strategyKey As String) As Collection
    Dim lo As ListObject, c As Object, r As Range
    Dim res As Collection, tmp As Collection, i As Long, j As Long
    Dim rec As Object, swapped As Boolean

    Set tmp = New Collection
    Set lo = GetTable(SH_PACKAGEDEF)
    Set c = ColMap(lo)
    If Not lo.DataBodyRange Is Nothing Then
        For Each r In lo.DataBodyRange.Rows
            If StrComp(Txt(r, c, "StrategyKey"), strategyKey, vbTextCompare) = 0 Then
                Set rec = modContract.NewDict()
                rec("PackageNo") = CLng(Val(Txt(r, c, "PackageNo")))
                rec("ShortCode") = Txt(r, c, "ShortCode")
                rec("Hierarchy") = Val(Txt(r, c, "Hierarchy"))
                tmp.Add rec
            End If
        Next r
    End If

    ' Boblesortering paa PackageNo. Der er 3-8 pakker; enhver anden
    ' sorteringsalgoritme ville vaere overkill her.
    Set res = New Collection
    Dim arr() As Object, n As Long
    n = tmp.Count
    If n = 0 Then Set PackagesForStrategy = res: Exit Function
    ReDim arr(1 To n)
    For i = 1 To n
        Set arr(i) = tmp(i)
    Next i
    Do
        swapped = False
        For i = 1 To n - 1
            If arr(i)("PackageNo") > arr(i + 1)("PackageNo") Then
                Set rec = arr(i): Set arr(i) = arr(i + 1): Set arr(i + 1) = rec
                swapped = True
            End If
        Next i
    Loop While swapped
    For i = 1 To n
        res.Add arr(i)
    Next i
    Set PackagesForStrategy = res
End Function

'==============================================================================
' Hjaelpere
'==============================================================================

Public Function GetTable(ByVal tableName As String) As ListObject
    Dim ws As Worksheet, lo As ListObject
    For Each ws In ThisWorkbook.Worksheets
        For Each lo In ws.ListObjects
            If StrComp(lo.Name, tableName, vbTextCompare) = 0 Then
                Set GetTable = lo
                Exit Function
            End If
        Next lo
    Next ws
    Err.Raise vbObjectError + 21, "modLoadSheet", _
        "Tabellen '" & tableName & "' findes ikke i projektmappen."
End Function

' Kolonnenavn -> kolonneindeks i tabellen
Private Function ColMap(ByVal lo As ListObject) As Object
    Dim d As Object, i As Long
    Set d = modContract.NewDict()
    For i = 1 To lo.ListColumns.Count
        d(CStr(lo.ListColumns(i).Name)) = i
    Next i
    Set ColMap = d
End Function

' Tom streng for kolonner, der ikke findes. Saa faar en manglende valgfri
' kolonne ikke hele batchen til at vaelte.
Private Function Txt(ByVal r As Range, ByVal c As Object, ByVal col As String) As String
    If Not c.Exists(col) Then Exit Function
    Txt = Trim$(CStr(r.Cells(1, CLng(c(col))).value & ""))
End Function

Private Function Dt(ByVal r As Range, ByVal c As Object, ByVal col As String) As Variant
    Dim v As Variant
    Dt = Empty
    If Not c.Exists(col) Then Exit Function
    v = r.Cells(1, CLng(c(col))).value
    If IsDate(v) Then Dt = CDate(v)
End Function

Private Function Dflt(ByVal v As String, ByVal fallback As String) As String
    Dflt = IIf(Len(v) = 0, fallback, v)
End Function

' SAP forventer operationsnumre med foranstillede nuller: 10 -> "0010"
Private Function PadOp(ByVal v As String) As String
    If Len(v) = 0 Then Exit Function
    If IsNumeric(v) Then
        PadOp = Format$(CLng(v), "0000")
    Else
        PadOp = v
    End If
End Function

Private Function IsKeyColumn(ByVal hdr As String) As Boolean
    Select Case UCase$(hdr)
        Case "REQUESTGUID", "REQUESTNO", "TEMPKEY", "OPERATIONNO", "DESCRIPTION"
            IsKeyColumn = True
    End Select
End Function

Private Function FindOperation(ByVal tl As Object, ByVal opNo As String) As Object
    Dim op As Object
    For Each op In tl("Operations")
        If StrComp(op("OperationNo"), opNo, vbTextCompare) = 0 Then
            Set FindOperation = op
            Exit Function
        End If
    Next op
End Function
