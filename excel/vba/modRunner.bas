Attribute VB_Name = "modRunner"
Option Explicit
'==============================================================================
' modRunner - batchkoerslen.
'
' GENSTARTBAR, IKKE ATOMAR. En batch paa 30 planer fejler paa nummer 17. Det
' er normalen for GUI scripting, ikke et hypotetisk scenarie. Derfor:
'
'   * status skrives pr. OBJEKT (arbejdsplan og plan hver for sig), ikke pr.
'     anmodning. Blev arbejdsplanen oprettet og planen ikke, maa en genkoersel
'     ikke oprette arbejdsplanen igen.
'   * alt med status OK springes over.
'   * status skrives tilbage EFTER hvert objekt, ikke til sidst. Bliver Excel
'     lukket ned midt i det hele, er det der allerede er oprettet stadig
'     registreret.
'   * en fejl afbryder EEN anmodning, ikke batchen.
'
' Genkoersel er den normale fejlrettelse: ret arket, koer igen.
'==============================================================================

'--- Indgangspunkt: koer alt der ikke allerede er oprettet -------------------
Public Sub RunAll()
    RunPlans modLoadSheet.LoadPlans()
End Sub

'--- Indgangspunkt: koer een anmodning fra arket -----------------------------
Public Sub RunOne()
    Dim guid As String
    guid = Trim$(InputBox("RequestGuid paa den anmodning der skal oprettes:", "Koer een"))
    If Len(guid) = 0 Then Exit Sub
    RunPlans modLoadSheet.LoadPlans(guid)
End Sub

'--- Indgangspunkt: koer fra en JSON-fil -------------------------------------
Public Sub RunFromJsonFile()
    Dim plans As Collection
    Set plans = modLoadJson.LoadFromFileDialog()
    If plans Is Nothing Then Exit Sub
    RunPlans plans
End Sub

'==============================================================================
' Selve loekken
'==============================================================================
Public Sub RunPlans(ByVal plans As Collection)
    Dim plan As Object
    Dim nOk As Long, nSkip As Long, nErr As Long
    Dim msg As String, t0 As Double

    If plans Is Nothing Then Exit Sub
    If plans.Count = 0 Then
        MsgBox "Ingen anmodninger at koere.", vbInformation
        Exit Sub
    End If

    On Error GoTo Fatal
    modSapSession.Connect
    LogLine "=== Start, " & plans.Count & " anmodninger" & IIf(DRY_RUN, " (DRY_RUN)", "")
    t0 = Timer
    On Error GoTo 0

    For Each plan In plans
        ' Allerede oprettet? Spring over.
        If StrComp(NzStr(plan, "PlanStatus"), "OK", vbTextCompare) = 0 Then
            nSkip = nSkip + 1
            LogLine NzStr(plan, "RequestNo") & ": sprunget over, allerede oprettet"
        Else
            ' ProcessPlan har sin EGEN fejlhaandtering og returnerer en
            ' fejltekst frem for at rejse. Saa slipper vi for at haandtere
            ' fejl inde i en loekke: en fejlhaandler, der ikke afsluttes med
            ' Resume, forbliver aktiv, og saa ville den NAESTE fejl i samme
            ' procedure slippe forbi og afbryde hele batchen.
            msg = ProcessPlan(plan)
            If Len(msg) = 0 Then nOk = nOk + 1 Else nErr = nErr + 1
        End If
    Next plan

    LogLine "=== Slut. OK: " & nOk & ", sprunget over: " & nSkip & _
            ", fejl: " & nErr & ", tid: " & Format$(Timer - t0, "0") & " sek."

    If Len(FLOW_URL) > 0 And Not DRY_RUN And nOk > 0 Then SendReceipts plans

    MsgBox "Faerdig." & vbLf & vbLf & _
           "Oprettet: " & nOk & vbLf & _
           "Sprunget over: " & nSkip & vbLf & _
           "Fejl: " & nErr & vbLf & vbLf & _
           IIf(DRY_RUN, "DRY_RUN var slaaet til - der er IKKE gemt i SAP.", _
                        "Se arket '" & SH_LOG & "' for detaljer."), _
           IIf(nErr > 0, vbExclamation, vbInformation)
    Exit Sub

Fatal:
    LogLine "AFBRUDT: " & Err.Description
    MsgBox "Koerslen blev afbrudt: " & Err.Description, vbCritical
End Sub

'--- Een anmodning. Returnerer "" ved succes, ellers fejlteksten. ------------
'    Fejl afbryder DENNE anmodning, ikke batchen.
Private Function ProcessPlan(ByVal plan As Object) As String
    Dim tl As Object, planNo As String, msg As String

    ' Valider foer SAP. En fejl fanget her koster sekunder; den samme fejl
    ' fanget inde i IA01 koster en halvt oprettet arbejdsplan.
    msg = modContract.Validate(plan)
    If Len(msg) > 0 Then
        msg = "Validering: " & Replace(msg, vbLf, " | ")
        WritePlanStatus plan, "FEJL", "", msg
        LogLine NzStr(plan, "RequestNo") & ": VALIDERINGSFEJL - " & msg
        ProcessPlan = msg
        Exit Function
    End If

    On Error GoTo Failed

    '--- 1. Arbejdsplaner foerst: planen skal bruge gruppenummeret -----------
    For Each tl In plan("TaskLists")
        If StrComp(NzStr(tl, "Status"), "OK", vbTextCompare) = 0 Then
            LogLine NzStr(plan, "RequestNo") & " / " & tl("Description") & _
                    ": arbejdsplan allerede oprettet (" & tl("SapGroup") & ")"
        Else
            tl("SapGroup") = modSapTaskList.CreateTaskList(tl, plan)
            ' Skriv tilbage med det samme. Lukkes Excel ned midt i batchen,
            ' er det der allerede er oprettet stadig registreret.
            WriteTaskListStatus tl, "OK", tl("SapGroup"), ""
            LogLine NzStr(plan, "RequestNo") & " / " & tl("Description") & _
                    ": arbejdsplan " & tl("SapGroup") & " oprettet"
        End If
    Next tl

    '--- 2. Vedligeholdsplanen -----------------------------------------------
    planNo = modSapMaintPlan.CreateMaintPlan(plan)
    WritePlanStatus plan, "OK", planNo, ""
    LogLine NzStr(plan, "RequestNo") & ": plan " & planNo & " oprettet"
    Exit Function

Failed:
    ProcessPlan = Err.Description
    WritePlanStatus plan, "FEJL", "", Err.Description
    LogLine NzStr(plan, "RequestNo") & ": FEJL - " & Err.Description
    ' Tilbage til en kendt tilstand, saa naeste anmodning starter rent.
    modSapSession.ResetToMenu
End Function

'==============================================================================
' Tilbageskrivning til arket
'==============================================================================
Private Sub WritePlanStatus(ByVal plan As Object, ByVal status As String, _
                            ByVal planNo As String, ByVal msg As String)
    Dim lo As ListObject, r As Long

    ' Status skal ALTID i hukommelsen - kvitteringen laeser den herfra, og
    ' JSON-kilden har ingen raekke at skrive i.
    plan("PlanStatus") = status
    plan("SapPlanNo") = planNo

    r = CLng(Nz(plan, "RowIndex", 0))
    If r = 0 Then Exit Sub                  ' JSON-kilde: intet ark at skrive i

    Set lo = modLoadSheet.GetTable(SH_PLAN)
    SetCellByHeader lo, r, "PLAN_Status", status
    SetCellByHeader lo, r, "PLAN_No", planNo
    SetCellByHeader lo, r, "RunMsg", Left$(msg, 500)
    SetCellByHeader lo, r, "RunAt", Format$(Now, "yyyy-mm-dd hh:nn:ss")
End Sub

Private Sub WriteTaskListStatus(ByVal tl As Object, ByVal status As String, _
                                ByVal grp As String, ByVal msg As String)
    Dim lo As ListObject, r As Long

    tl("Status") = status
    r = CLng(Nz(tl, "RowIndex", 0))
    If r = 0 Then Exit Sub

    Set lo = modLoadSheet.GetTable(SH_TASKLIST)
    SetCellByHeader lo, r, "TL_Status", status
    SetCellByHeader lo, r, "TL_Group", grp
    SetCellByHeader lo, r, "RunMsg", Left$(msg, 500)
    SetCellByHeader lo, r, "RunAt", Format$(Now, "yyyy-mm-dd hh:nn:ss")
End Sub

Private Sub SetCellByHeader(ByVal lo As ListObject, ByVal sheetRow As Long, _
                            ByVal header As String, ByVal value As Variant)
    Dim i As Long
    For i = 1 To lo.ListColumns.Count
        If StrComp(lo.ListColumns(i).Name, header, vbTextCompare) = 0 Then
            lo.Range.Worksheet.Cells(sheetRow, lo.Range.Column + i - 1).value = value
            Exit Sub
        End If
    Next i
End Sub

'==============================================================================
' Kvittering til SharePoint via et HTTP-trigget Power Automate-flow
'
' ADVARSEL: FLOW_URL indeholder en signatur og ER adgangen - alle med URL'en
' kan kalde flowet. Lad flowet kun acceptere kendte RequestGuid-vaerdier og
' kun skrive Status, SapMaintPlanNo og SapCreatedOn.
'==============================================================================
Private Sub SendReceipts(ByVal plans As Collection)
    Dim http As Object, plan As Object, body As String, parts As String

    For Each plan In plans
        If StrComp(NzStr(plan, "PlanStatus"), "OK", vbTextCompare) = 0 Then
            If Len(parts) > 0 Then parts = parts & ","
            parts = parts & "{""requestGuid"":""" & JsEsc(NzStr(plan, "RequestGuid")) & """," & _
                    """sapMaintPlanNo"":""" & JsEsc(NzStr(plan, "SapPlanNo")) & """," & _
                    """status"":""OprettetISAP""}"
        End If
    Next plan
    If Len(parts) = 0 Then Exit Sub

    body = "{""createdBy"":""" & JsEsc(Environ$("USERNAME")) & """,""results"":[" & parts & "]}"

    On Error GoTo Failed
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.Open "POST", FLOW_URL, False
    http.setRequestHeader "Content-Type", "application/json; charset=utf-8"
    http.send body

    If http.status >= 200 And http.status < 300 Then
        LogLine "Kvittering sendt (" & http.status & ")"
    Else
        LogLine "Kvittering afvist: HTTP " & http.status & " " & Left$(http.responseText, 200)
    End If
    Exit Sub

Failed:
    LogLine "Kvittering kunne ikke sendes: " & Err.Description
End Sub

Private Function JsEsc(ByVal s As String) As String
    s = Replace(s, "\", "\\")
    s = Replace(s, """", "\""")
    s = Replace(s, vbCr, " ")
    s = Replace(s, vbLf, " ")
    JsEsc = s
End Function

'==============================================================================
' Log
'==============================================================================
Public Sub LogLine(ByVal txt As String)
    Dim ws As Worksheet, r As Long
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(SH_LOG)
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add( _
            After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = SH_LOG
        ws.Range("A1:B1").value = Array("Tidspunkt", "Besked")
        ws.Range("A1:B1").Font.Bold = True
    End If
    r = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    ws.Cells(r, 1).value = Format$(Now, "yyyy-mm-dd hh:nn:ss")
    ws.Cells(r, 2).value = txt
End Sub

Private Function Nz(ByVal d As Object, ByVal key As String, ByVal fallback As Variant) As Variant
    If d.Exists(key) Then Nz = d(key) Else Nz = fallback
End Function

Private Function NzStr(ByVal d As Object, ByVal key As String) As String
    If d.Exists(key) Then NzStr = CStr(d(key) & "")
End Function
