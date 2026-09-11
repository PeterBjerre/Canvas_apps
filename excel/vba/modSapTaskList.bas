Attribute VB_Name = "modSapTaskList"
Option Explicit
'==============================================================================
' modSapTaskList - opretter en arbejdsplan i IA01 inkl. pakkeallokering.
'
' Rejser en fejl ved problemer. modRunner fanger den og afbryder DEN ENE
' raekke, ikke hele batchen.
'
' Returnerer det gruppenummer, SAP tildelte.
'==============================================================================

Public Function CreateTaskList(ByVal tl As Object, ByVal plan As Object) As String
    Dim grp As String

    modSapSession.StartTransaction TCODE_TASKLIST

    '--- Startskaerm ----------------------------------------------------------
    modSapSession.SetText IA01_EQUIPMENT, tl("Equipment")
    modSapSession.SetText IA01_PLANT, Dflt(tl("Plant"), plan("Plant"))
    modSapSession.SetText IA01_PROFILE, ""      ' profil styres af brugerparameter
    modSapSession.PressEnter
    modSapSession.GuardPopup "IA01 startskaerm"
    FailIfError "IA01 startskaerm"

    '--- Hoveddata ------------------------------------------------------------
    modSapSession.SetText IA01_DESCRIPTION, Left$(tl("Description"), 40)
    modSapSession.SetText IA01_USAGE, tl("Usage")
    modSapSession.SetText IA01_PLANNERGRP, tl("PlannerGroup")
    modSapSession.SetText IA01_WORKCENTER, tl("WorkCenter")

    ' Strategien SKAL saettes her. Uden den findes pakkeskaermen ikke, og
    ' hele allokeringen er meningsloes (regel S3).
    If plan("PlanType") = "Strategy" Then
        modSapSession.SetText IA01_STRATEGY, tl("StrategyKey")
    End If

    modSapSession.PressEnter
    modSapSession.GuardPopup "IA01 hoveddata"
    FailIfError "IA01 hoveddata"

    '--- Operationer ----------------------------------------------------------
    EnterOperations tl

    '--- Pakkeallokering ------------------------------------------------------
    If plan("PlanType") = "Strategy" Then
        AllocatePackages tl, plan
    End If

    '--- Gem ------------------------------------------------------------------
    If DRY_RUN Then
        modSapSession.ResetToMenu
        CreateTaskList = "DRYRUN"
        Exit Function
    End If

    modSapSession.PressSave
    modSapSession.GuardPopup "IA01 gem"
    FailIfError "IA01 gem"

    grp = modSapSession.ExtractNumber(modSapSession.StatusText())
    If Len(grp) = 0 Then
        Err.Raise vbObjectError + 40, "modSapTaskList", _
            "Arbejdsplanen blev muligvis gemt, men gruppenummeret kunne ikke " & _
            "laeses af statuslinjen: " & modSapSession.StatusText()
    End If

    CreateTaskList = grp
End Function

'==============================================================================
' Operationsoversigten
'
' Table controls indeholder kun de SYNLIGE raekker, og SAP tilfoejer kun nye
' tomme raekker, naar der trykkes Enter. Derfor Enter for hver side.
' Dette er den del, der oftest skal justeres pr. release.
'==============================================================================
Private Sub EnterOperations(ByVal tl As Object)
    Dim tbl As Object, op As Object
    Dim i As Long, visRow As Long, visibleRows As Long
    Dim cOpNo As Long, cText As Long, cCtrl As Long, cWc As Long
    Dim cWork As Long, cNum As Long, cDur As Long

    Set tbl = modSapSession.Session.FindById(IA01_TC_OPER)
    visibleRows = tbl.VisibleRowCount

    cOpNo = ColOrFail(tbl, IA01_COL_OPNO)
    cText = ColOrFail(tbl, IA01_COL_TEXT)
    cCtrl = ColOrFail(tbl, IA01_COL_CTRLKEY)
    cWc = modSapSession.ColumnIndex(tbl, IA01_COL_WORKCTR)
    cWork = modSapSession.ColumnIndex(tbl, IA01_COL_WORK)
    cNum = modSapSession.ColumnIndex(tbl, IA01_COL_NUMPER)
    cDur = modSapSession.ColumnIndex(tbl, IA01_COL_DURAT)

    i = 0
    For Each op In tl("Operations")
        Set tbl = modSapSession.ScrollToRow(IA01_TC_OPER, i, visRow)

        tbl.GetCell(visRow, cOpNo).Text = op("OperationNo")
        tbl.GetCell(visRow, cText).Text = Left$(op("Description"), 40)
        tbl.GetCell(visRow, cCtrl).Text = op("ControlKey")
        If cWc >= 0 Then SetIfAny tbl, visRow, cWc, op("WorkCenter")
        If cWork >= 0 Then SetIfAny tbl, visRow, cWork, op("Work")
        If cNum >= 0 Then SetIfAny tbl, visRow, cNum, op("NumberOfPeople")
        If cDur >= 0 Then SetIfAny tbl, visRow, cDur, op("Duration")

        i = i + 1

        ' Enter naar siden er fuld, saa SAP validerer og tilfoejer tomme raekker
        If i Mod (visibleRows - 1) = 0 Then
            modSapSession.PressEnter
            modSapSession.GuardPopup "IA01 operation " & op("OperationNo")
            FailIfError "IA01 operation " & op("OperationNo")
        End If
    Next op

    modSapSession.PressEnter
    modSapSession.GuardPopup "IA01 operationer"
    FailIfError "IA01 operationer"
End Sub

'==============================================================================
' Pakkeallokeringen
'
' Skaermen er et table control med EEN kolonne pr. pakke og et flueben i
' cellen. Raekkefoelgen er den samme som operationsoversigten.
'==============================================================================
Private Sub AllocatePackages(ByVal tl As Object, ByVal plan As Object)
    Dim tbl As Object, op As Object, pkgs As Collection
    Dim colOf As Object, i As Long, v As Variant

    modSapSession.SelectMenu IA01_MENU_PKG
    modSapSession.GuardPopup "IA01 pakkeskaerm"

    Set pkgs = modLoadSheet.PackagesForStrategy(plan("StrategyKey"))
    If pkgs.Count = 0 Then
        Err.Raise vbObjectError + 41, "modSapTaskList", _
            "Ingen pakker defineret for strategi " & plan("StrategyKey") & _
            " i arket " & SH_PACKAGEDEF & "."
    End If

    Set tbl = modSapSession.Session.FindById(IA01_TC_PKG)
    Set colOf = ResolvePackageColumns(tbl, pkgs)

    i = 0
    For Each op In tl("Operations")
        For Each v In colOf.Keys
            If modContract.HasPackage(op, CLng(v)) Then
                modSapSession.SetCellChecked IA01_TC_PKG, i, CLng(colOf(v)), True
            End If
        Next v
        i = i + 1
    Next op

    modSapSession.PressEnter
    modSapSession.GuardPopup "IA01 pakkeallokering"
    FailIfError "IA01 pakkeallokering"
End Sub

'--- Pakkenummer -> kolonneindeks i table controlet.
'    Proev foerst at matche paa kolonnens navn/titel. Lykkes det ikke, falder
'    vi tilbage paa fast offset + pakkens raekkefoelge, som er den maade SAP
'    normalt viser dem. Koer modSapInspect.DumpTableColumns for at se, hvad
'    kolonnerne rent faktisk hedder hos jer. --------------------------------
Private Function ResolvePackageColumns(ByVal tbl As Object, ByVal pkgs As Collection) As Object
    Dim d As Object, i As Long, idx As Long, rec As Object
    Set d = modContract.NewDict()

    i = 0
    For Each rec In pkgs
        idx = modSapSession.ColumnIndex(tbl, rec("ShortCode"))
        If idx < 0 Then idx = TitleIndex(tbl, rec("ShortCode"))
        If idx < 0 Then idx = IA01_PKG_COL0 + i     ' fallback: raekkefoelge
        d(CLng(rec("PackageNo"))) = idx
        i = i + 1
    Next rec

    Set ResolvePackageColumns = d
End Function

Private Function TitleIndex(ByVal tbl As Object, ByVal title As String) As Long
    Dim i As Long, t As String
    TitleIndex = -1
    On Error Resume Next
    For i = 0 To tbl.Columns.Count - 1
        t = ""
        t = tbl.Columns(i).title & ""
        If StrComp(t, title, vbTextCompare) = 0 Then
            TitleIndex = i
            Exit Function
        End If
    Next i
End Function

'==============================================================================
' Smaa hjaelpere
'==============================================================================
Private Function ColOrFail(ByVal tbl As Object, ByVal colName As String) As Long
    ColOrFail = modSapSession.ColumnIndex(tbl, colName)
    If ColOrFail < 0 Then
        Err.Raise vbObjectError + 42, "modSapTaskList", _
            "Kolonnen '" & colName & "' findes ikke i table controlet. " & _
            "Koer modSapInspect.DumpTableColumns og ret modConfig."
    End If
End Function

Private Sub SetIfAny(ByVal tbl As Object, ByVal visRow As Long, _
                     ByVal col As Long, ByVal value As Variant)
    If Len(Trim$(CStr(value & ""))) = 0 Then Exit Sub
    tbl.GetCell(visRow, col).Text = CStr(value)
End Sub

Private Sub FailIfError(ByVal context As String)
    If modSapSession.StatusIsError() Then
        Err.Raise vbObjectError + 43, "modSapTaskList", _
            context & ": " & modSapSession.StatusText()
    End If
End Sub

Private Function Dflt(ByVal v As String, ByVal fallback As String) As String
    Dflt = IIf(Len(Trim$(v)) = 0, fallback, v)
End Function
