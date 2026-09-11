Attribute VB_Name = "modSapMaintPlan"
Option Explicit
'==============================================================================
' modSapMaintPlan - opretter vedligeholdsplanen i IP42 (strategiplan) eller
' IP41 (single cycle).
'
' BEGRAENSNING I DENNE VERSION
'   Der oprettes EEN position pr. plan. Flere positioner kraever knappen
'   "Opret position" paa positionsoversigten, og dens ID kan ikke skrives
'   udefra - det afhaenger af release og skaermvariant.
'   Sub AddAdditionalItems nedenfor er stedet at udvide, naar ID'et er
'   optaget med modSapInspect.DumpScreen.
'   Indtil da rejser modulet en tydelig fejl frem for at oprette en plan,
'   der mangler positioner i stilhed.
'
' Returnerer det plannummer, SAP tildelte.
'==============================================================================

Public Function CreateMaintPlan(ByVal plan As Object) As String
    Dim nr As String, firstItem As Object

    If plan("Items").Count = 0 Then
        Err.Raise vbObjectError + 50, "modSapMaintPlan", "Planen har ingen positioner."
    End If
    If plan("Items").Count > 1 Then
        Err.Raise vbObjectError + 51, "modSapMaintPlan", _
            "Planen har " & plan("Items").Count & " positioner. Denne version " & _
            "opretter kun een. Udvid AddAdditionalItems med ID'et paa knappen " & _
            "'Opret position' - se modulets sidehoved."
    End If
    Set firstItem = plan("Items")(1)

    '--- Startskaerm ----------------------------------------------------------
    If plan("PlanType") = "SingleCycle" Then
        modSapSession.StartTransaction TCODE_PLAN_SC
    Else
        modSapSession.StartTransaction TCODE_PLAN
        modSapSession.SetText IP42_STRATEGY, plan("StrategyKey")
    End If
    modSapSession.SetText IP42_PLANCAT, plan("PlanCategory")
    modSapSession.PressEnter
    modSapSession.GuardPopup "IP42 startskaerm"
    FailIfError "IP42 startskaerm"

    '--- Planhoved ------------------------------------------------------------
    modSapSession.SetText IP42_DESCRIPTION, Left$(plan("Description"), 40)

    ' Sorteringsfeltet baerer RequestGuid videre til SAP. Det er det, der goer
    ' det muligt at finde planen tilbage og opdage en dublet efter en
    ' afbrudt koersel.
    modSapSession.SetText IP42_SORTFIELD, plan("SortField")
    modSapSession.SetDate IP42_CYCLESTART, plan("CycleStartDate")

    '--- Position -------------------------------------------------------------
    FillItem firstItem, plan

    modSapSession.PressEnter
    modSapSession.GuardPopup "IP42 position"
    FailIfError "IP42 position"

    '--- Gem ------------------------------------------------------------------
    If DRY_RUN Then
        modSapSession.ResetToMenu
        CreateMaintPlan = "DRYRUN"
        Exit Function
    End If

    modSapSession.PressSave
    modSapSession.GuardPopup "IP42 gem"
    FailIfError "IP42 gem"

    nr = modSapSession.ExtractNumber(modSapSession.StatusText())
    If Len(nr) = 0 Then
        Err.Raise vbObjectError + 52, "modSapMaintPlan", _
            "Planen blev muligvis gemt, men plannummeret kunne ikke laeses af " & _
            "statuslinjen: " & modSapSession.StatusText()
    End If

    CreateMaintPlan = nr
End Function

'==============================================================================
' Positionsdata
'==============================================================================
Private Sub FillItem(ByVal it As Object, ByVal plan As Object)
    modSapSession.SetText IP42_ITEM_TEXT, Left$(it("Description"), 40)

    Select Case it("ObjectType")
        Case "Equipment"
            modSapSession.SetText IP42_ITEM_EQUNR, it("Equipment")
        Case "FunctionalLocation"
            modSapSession.SetText IP42_ITEM_TPLNR, it("FunctionalLocation")
        Case "NoObject"
            ' bevidst tom
        Case Else
            modSapSession.SetText IP42_ITEM_EQUNR, it("Equipment")
            modSapSession.SetText IP42_ITEM_TPLNR, it("FunctionalLocation")
    End Select

    modSapSession.SetText IP42_ITEM_PLNGRP, it("PlannerGroup")
    modSapSession.SetText IP42_ITEM_ORDTYP, it("OrderType")
    modSapSession.SetText IP42_ITEM_WORKCT, it("WorkCenter")
    modSapSession.SetText IP42_ITEM_PLANT, Dflt(it("Plant"), plan("Plant"))

    '--- Arbejdsplantilknytning ----------------------------------------------
    Dim grp As String, cnt As String, typ As String

    If it("TaskListMode") = "Existing" Then
        typ = it("TaskListType")
        grp = it("TaskListGroup")
        cnt = it("TaskListCounter")
    ElseIf it("TaskListMode") = "New" Then
        ' Gruppenummeret kommer fra den arbejdsplan, modRunner netop oprettede.
        Dim tl As Object
        Set tl = modContract.FindTaskList(plan, it("TaskListRef"))
        If tl Is Nothing Then
            Err.Raise vbObjectError + 53, "modSapMaintPlan", _
                "Position " & it("ItemNo") & " peger paa arbejdsplan '" & _
                it("TaskListRef") & "', som ikke findes i anmodningen."
        End If
        If Len(tl("SapGroup")) = 0 Or tl("SapGroup") = "DRYRUN" Then
            If Not DRY_RUN Then
                Err.Raise vbObjectError + 54, "modSapMaintPlan", _
                    "Arbejdsplanen '" & tl("Description") & "' har intet " & _
                    "gruppenummer endnu. Den skal oprettes foer planen."
            End If
        End If
        typ = Dflt(tl("Type"), "E")
        grp = tl("SapGroup")
        cnt = "1"                       ' foerste taeller paa en ny arbejdsplan
    End If

    If Len(grp) > 0 Then
        modSapSession.SetText IP42_TL_TYPE, typ
        modSapSession.SetText IP42_TL_GROUP, grp
        modSapSession.SetText IP42_TL_COUNTER, cnt
    End If
End Sub

'==============================================================================
' Udvidelsespunkt: flere positioner pr. plan.
'
' Fremgangsmaade:
'   1. Opret en plan manuelt med to positioner.
'   2. Koer modSapInspect.DumpScreen paa positionsoversigten.
'   3. Find ID'et paa knappen "Opret position" og laeg det i modConfig.
'   4. Implementer loekken herunder og fjern fejlen i CreateMaintPlan.
'==============================================================================
Private Sub AddAdditionalItems(ByVal plan As Object)
    Err.Raise vbObjectError + 55, "modSapMaintPlan", _
        "Flere positioner er ikke implementeret - se modulets sidehoved."
End Sub

Private Sub FailIfError(ByVal context As String)
    If modSapSession.StatusIsError() Then
        Err.Raise vbObjectError + 56, "modSapMaintPlan", _
            context & ": " & modSapSession.StatusText()
    End If
End Sub

Private Function Dflt(ByVal v As String, ByVal fallback As String) As String
    Dflt = IIf(Len(Trim$(v)) = 0, fallback, v)
End Function
