Attribute VB_Name = "modLoadJson"
Option Explicit
'==============================================================================
' modLoadJson - loader fra en JSON-fil, der foelger
' schema/vhplan-request.schema.json.
'
' Alternativ til modLoadSheet, naar EN enkelt godkendt anmodning skal koeres
' paa en maskine uden adgang til SharePoint-listerne. Filen er samtidig
' arkivet: den viser praecis hvad der blev godkendt.
'
' AFHAENGIGHED
'   VBA-JSON (JsonConverter.bas) af Tim Hall - MIT-licens, eet modul:
'   https://github.com/VBA-tools/VBA-JSON
'   Importer JsonConverter.bas og saet en reference til
'   "Microsoft Scripting Runtime" (Tools > References).
'
' HVORFOR IKKE ScriptControl
'   De fleste JSON-eksempler til VBA bruger ScriptControl. Den findes KUN i
'   32-bit Office og fejler med "Cannot create an ActiveX component" paa
'   64-bit Office, som er standarden i dag. Brug ikke det moenster.
'==============================================================================

'--- Vaelg en fil og indlaes den ----------------------------------------------
Public Function LoadFromFileDialog() As Collection
    Dim fd As FileDialog, path As String

    Set fd = Application.FileDialog(msoFileDialogFilePicker)
    fd.Title = "Vaelg godkendt VH-plan anmodning (JSON)"
    fd.Filters.Clear
    fd.Filters.Add "JSON-filer", "*.json"
    fd.AllowMultiSelect = False
    If fd.Show <> -1 Then Exit Function

    path = fd.SelectedItems(1)
    Set LoadFromFileDialog = LoadFromFile(path)
End Function

'--- Indlaes en navngiven fil. Returnerer en Collection med een plan. ---------
Public Function LoadFromFile(ByVal path As String) As Collection
    Dim raw As String, root As Object, res As Collection

    raw = ReadTextUtf8(path)
    If Len(raw) = 0 Then
        Err.Raise vbObjectError + 30, "modLoadJson", "Filen er tom: " & path
    End If

    ' JsonConverter.ParseJson findes i VBA-JSON - se modulets sidehoved.
    Set root = JsonConverter.ParseJson(raw)

    Set res = New Collection
    res.Add MapPlan(root)
    Set LoadFromFile = res
End Function

'==============================================================================
' Mapning fra schema til den faelles kontrakt (modContract)
'==============================================================================
Private Function MapPlan(ByVal root As Object) As Object
    Dim plan As Object, jp As Object
    Dim jt As Object, jo As Object, ji As Object, jpk As Object
    Dim tl As Object, op As Object, it As Object

    Set plan = modContract.NewPlan()
    Set jp = root("plan")

    plan("RequestGuid") = Str2(root, "requestGuid")
    plan("RequestNo") = Str2(root, "requestNo")
    plan("PlanType") = Str2(jp, "planType")
    plan("Description") = Str2(jp, "description")
    plan("PlanCategory") = Str2(jp, "planCategory")
    plan("Plant") = Str2(jp, "planningPlant")
    plan("StrategyKey") = Str2(jp, "strategyKey")
    plan("SortField") = Left$(plan("RequestGuid"), 8)
    If Len(Str2(jp, "cycleStartDate")) > 0 Then
        plan("CycleStartDate") = CDate(Str2(jp, "cycleStartDate"))
    End If

    '--- Arbejdsplaner og operationer ----------------------------------------
    If Exists(root, "taskLists") Then
        For Each jt In root("taskLists")
            Set tl = modContract.NewTaskList()
            tl("TempKey") = Str2(jt, "tempKey")
            tl("Description") = Str2(jt, "description")
            tl("Type") = Str2(jt, "type")
            tl("StrategyKey") = Str2(jt, "strategyKey")
            tl("Plant") = Str2(jt, "plant")
            tl("Usage") = Str2(jt, "usage")
            tl("WorkCenter") = Str2(jt, "workCenter")

            If Exists(jt, "operations") Then
                For Each jo In jt("operations")
                    Set op = modContract.NewOperation()
                    op("OperationNo") = Str2(jo, "operationNo")
                    op("Description") = Str2(jo, "description")
                    op("ControlKey") = Str2(jo, "controlKey")
                    op("WorkCenter") = Str2(jo, "workCenter")
                    op("Work") = Str2(jo, "work")
                    op("WorkUnit") = Str2(jo, "workUnit")
                    op("NumberOfPeople") = Str2(jo, "numberOfPeople")
                    op("Duration") = Str2(jo, "duration")
                    op("DurationUnit") = Str2(jo, "durationUnit")

                    ' packages er [{packageNo: 1}, ...] - foldes til rene tal
                    If Exists(jo, "packages") Then
                        For Each jpk In jo("packages")
                            op("Packages").Add CLng(Val(Str2(jpk, "packageNo")))
                        Next jpk
                    End If
                    tl("Operations").Add op
                Next jo
            End If
            plan("TaskLists").Add tl
        Next jt
    End If

    '--- Positioner -----------------------------------------------------------
    If Exists(root, "items") Then
        For Each ji In root("items")
            Set it = modContract.NewItem()
            it("ItemNo") = Str2(ji, "itemNo")
            it("Description") = Str2(ji, "description")
            it("ObjectType") = Str2(ji, "objectType")
            it("Equipment") = Str2(ji, "equipment")
            it("FunctionalLocation") = Str2(ji, "functionalLocation")
            it("PlannerGroup") = Str2(ji, "plannerGroup")
            it("OrderType") = Str2(ji, "orderType")
            it("WorkCenter") = Str2(ji, "mainWorkCenter")
            it("Plant") = plan("Plant")
            it("TaskListMode") = Str2(ji, "taskListMode")
            it("TaskListRef") = Str2(ji, "taskListRef")
            If Exists(ji, "taskList") Then
                If Not ji("taskList") Is Nothing Then
                    it("TaskListType") = Str2(ji("taskList"), "type")
                    it("TaskListGroup") = Str2(ji("taskList"), "group")
                    it("TaskListCounter") = Str2(ji("taskList"), "counter")
                End If
            End If
            plan("Items").Add it
        Next ji
    End If

    Set MapPlan = plan
End Function

'==============================================================================
' Hjaelpere
'==============================================================================

'--- Laes som UTF-8. Open/Input laeser ANSI og oedelaegger ae, oe og aa. ------
Private Function ReadTextUtf8(ByVal path As String) As String
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2                  ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.LoadFromFile path
    ReadTextUtf8 = stm.ReadText(-1)
    stm.Close
End Function

' Tom streng frem for en fejl, naar noeglen mangler eller er null.
Private Function Str2(ByVal d As Object, ByVal key As String) As String
    On Error Resume Next
    If d Is Nothing Then Exit Function
    If Not d.Exists(key) Then Exit Function
    If IsNull(d(key)) Then Exit Function
    Str2 = Trim$(CStr(d(key) & ""))
End Function

Private Function Exists(ByVal d As Object, ByVal key As String) As Boolean
    On Error Resume Next
    If d Is Nothing Then Exit Function
    Exists = d.Exists(key)
    If Exists Then Exists = Not IsNull(d(key))
End Function
