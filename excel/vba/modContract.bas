Attribute VB_Name = "modContract"
Option Explicit
'==============================================================================
' modContract - den faelles datastruktur mellem kilde og udfoerelse.
'
' ALLE loadere (ark, JSON, manuelt) producerer praecis denne struktur, og
' modRunner kender kun den. Det er hele pointen med lagdelingen: kilden kan
' skiftes uden at roere SAP-koden, og SAP-koden kan skiftes ud (BAPI, LSMW)
' uden at roere kilden.
'
' Alt er late binding (Scripting.Dictionary via CreateObject), saa modulerne
' kan importeres uden at saette referencer.
'
'   Plan (Dictionary)
'     RequestGuid, RequestNo, PlanType, Description, PlanCategory, Plant,
'     StrategyKey, CycleStartDate, SortField, RowIndex
'     Items     -> Collection af Dictionary
'     TaskLists -> Collection af Dictionary
'                    TempKey, Description, Type, StrategyKey, Plant, Usage,
'                    WorkCenter, PlannerGroup, RowIndex, SapGroup
'                    Operations -> Collection af Dictionary
'                                    OperationNo, Description, ControlKey,
'                                    WorkCenter, Work, WorkUnit,
'                                    NumberOfPeople, Duration, DurationUnit
'                                    Packages -> Collection af Long
'==============================================================================

Public Function NewDict() As Object
    Set NewDict = CreateObject("Scripting.Dictionary")
    NewDict.CompareMode = 1          ' TextCompare - noeglerne er ikke case-sensitive
End Function

Public Function NewPlan() As Object
    Dim p As Object
    Set p = NewDict()
    p("RequestGuid") = ""
    p("RequestNo") = ""
    p("PlanType") = "Strategy"
    p("Description") = ""
    p("PlanCategory") = "PM"
    p("Plant") = ""
    p("StrategyKey") = ""
    p("SortField") = ""
    p("CycleStartDate") = Empty
    p("RowIndex") = 0
    Set p("Items") = New Collection
    Set p("TaskLists") = New Collection
    Set NewPlan = p
End Function

Public Function NewTaskList() As Object
    Dim t As Object
    Set t = NewDict()
    t("TempKey") = ""
    t("Description") = ""
    t("Type") = "E"
    t("StrategyKey") = ""
    t("Plant") = ""
    t("Usage") = ""
    t("WorkCenter") = ""
    t("PlannerGroup") = ""
    t("Equipment") = ""
    t("SapGroup") = ""
    t("RowIndex") = 0
    Set t("Operations") = New Collection
    Set NewTaskList = t
End Function

Public Function NewOperation() As Object
    Dim o As Object
    Set o = NewDict()
    o("OperationNo") = ""
    o("Description") = ""
    o("ControlKey") = ""
    o("WorkCenter") = ""
    o("Work") = Empty
    o("WorkUnit") = ""
    o("NumberOfPeople") = Empty
    o("Duration") = Empty
    o("DurationUnit") = ""
    Set o("Packages") = New Collection
    Set NewOperation = o
End Function

Public Function NewItem() As Object
    Dim i As Object
    Set i = NewDict()
    i("ItemNo") = 0
    i("Description") = ""
    i("ObjectType") = "Equipment"
    i("Equipment") = ""
    i("FunctionalLocation") = ""
    i("PlannerGroup") = ""
    i("OrderType") = ""
    i("WorkCenter") = ""
    i("Plant") = ""
    i("TaskListMode") = "New"
    i("TaskListRef") = ""
    i("TaskListType") = ""
    i("TaskListGroup") = ""
    i("TaskListCounter") = ""
    Set NewItem = i
End Function

'==============================================================================
' Validering
'
' Samme regler som appen og submit-flowet (se powerfx/03-validering.fx).
' Den koeres HER igen, fordi arket kan vaere redigeret i haanden mellem
' udtraek og koersel - og fordi en fejl fanget foer SAP koster sekunder,
' mens en fejl fanget inde i IA01 koster en halvt oprettet arbejdsplan.
'==============================================================================

' Returnerer "" hvis planen er i orden, ellers alle fejl adskilt af vbLf.
Public Function Validate(ByVal plan As Object) As String
    Dim msg As String
    Dim tl As Object, op As Object, it As Object
    Dim nOps As Long

    If Len(plan("Description")) = 0 Then msg = msg & "Planbeskrivelse mangler." & vbLf
    If Len(plan("Description")) > 40 Then _
        msg = msg & "Planbeskrivelse er " & Len(plan("Description")) & " tegn, maks. 40." & vbLf
    If Len(plan("Plant")) = 0 Then msg = msg & "Planlaegningsvaerk mangler." & vbLf

    ' S1 - strategiplan kraever strategi
    If plan("PlanType") = "Strategy" And Len(plan("StrategyKey")) = 0 Then _
        msg = msg & "S1: Strategi mangler paa en strategiplan." & vbLf

    ' Mindst een position
    If plan("Items").Count = 0 Then msg = msg & "Der skal vaere mindst een position." & vbLf

    For Each it In plan("Items")
        If it("ObjectType") <> "NoObject" _
           And Len(it("Equipment")) = 0 And Len(it("FunctionalLocation")) = 0 Then
            msg = msg & "Position " & it("ItemNo") & ": teknisk objekt mangler." & vbLf
        End If
        If Len(it("PlannerGroup")) = 0 Or Len(it("OrderType")) = 0 Then
            msg = msg & "Position " & it("ItemNo") & ": planlaeggergruppe og ordretype er obligatoriske." & vbLf
        End If
        If it("TaskListMode") = "Existing" _
           And (Len(it("TaskListGroup")) = 0 Or Len(it("TaskListCounter")) = 0) Then
            msg = msg & "Position " & it("ItemNo") & ": gruppe og taeller mangler paa eksisterende arbejdsplan." & vbLf
        End If
    Next it

    For Each tl In plan("TaskLists")
        ' S3 - arbejdsplanens strategi skal matche planens
        If plan("PlanType") = "Strategy" Then
            If StrComp(tl("StrategyKey"), plan("StrategyKey"), vbTextCompare) <> 0 Then
                msg = msg & "S3: Arbejdsplan '" & tl("Description") & "' har strategi " & _
                      tl("StrategyKey") & ", men planen har " & plan("StrategyKey") & "." & vbLf
            End If
        End If

        nOps = tl("Operations").Count
        If nOps = 0 Then msg = msg & "Arbejdsplan '" & tl("Description") & "' har ingen operationer." & vbLf

        For Each op In tl("Operations")
            If Len(op("OperationNo")) = 0 Then msg = msg & "Operation uden nummer." & vbLf
            If Len(op("Description")) = 0 Then _
                msg = msg & "Operation " & op("OperationNo") & " mangler tekst." & vbLf
            If Len(op("ControlKey")) = 0 Then _
                msg = msg & "Operation " & op("OperationNo") & " mangler styringsnoegle." & vbLf

            ' S4 - operation uden pakke ville aldrig blive udfoert
            If plan("PlanType") = "Strategy" And op("Packages").Count = 0 Then
                msg = msg & "S4: Operation " & op("OperationNo") & _
                      " er ikke tildelt nogen pakke og ville aldrig blive udfoert." & vbLf
            End If
        Next op
    Next tl

    Validate = msg
End Function

'--- Find en arbejdsplan i planen ud fra positionens TaskListRef -------------
Public Function FindTaskList(ByVal plan As Object, ByVal tempKey As String) As Object
    Dim tl As Object
    For Each tl In plan("TaskLists")
        If StrComp(tl("TempKey"), tempKey, vbTextCompare) = 0 Then
            Set FindTaskList = tl
            Exit Function
        End If
    Next tl
End Function

'--- Er pakkenummeret allokeret til operationen? ------------------------------
Public Function HasPackage(ByVal op As Object, ByVal pkgNo As Long) As Boolean
    Dim v As Variant
    For Each v In op("Packages")
        If CLng(v) = pkgNo Then
            HasPackage = True
            Exit Function
        End If
    Next v
End Function
