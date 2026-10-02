Attribute VB_Name = "VhpMap"
Option Explicit
'==============================================================================
' VhpMap - oversaettelsen fra SharePoint-vaerdier til SAP-felter.
'
' Reglerne er flyttet fra det gamle GUI-script (NormalizeItemIlartValue,
' NormalizeItemPriorityValue, NormalizeItemRevisionValue, ResolvePlanStartDate,
' NormalizeObjectListEntry) og samlet ET sted. De staar ikke ogsaa i flowet
' eller i Power Query - to udgaver af samme regel glider fra hinanden
' (docs/20-excel-vhplan-plan.md, "Og de indeholder den samme logik som VBA").
'
' Alt her er rene funktioner: ingen SAP, ingen ark, ingen filer. De afproeves
' i LibreOffice af tests/test_vba_runner.py og i Excel af VhpTest.RunSelfTest.
'==============================================================================

' "2;#102 - Predetermined Maintenance" -> "102 - Predetermined Maintenance".
' Det gamle REST-format for opslag. Flowet sender det ikke, men en haandlavet
' fil kan have det.
Public Function StripLookupId(ByVal s As String) As String
    Dim p As Long
    s = Trim$(s)
    p = InStr(1, s, ";#", vbBinaryCompare)
    If p > 0 Then s = Trim$(Mid$(s, p + 2))
    StripLookupId = s
End Function

' Aktivitetstype -> ILART: "102 - Predetermined Maintenance" -> "102".
Public Function ActivityCode(ByVal s As String) As String
    Dim p As Long
    s = StripLookupId(s)
    p = InStr(1, s, " - ", vbBinaryCompare)
    If p > 0 Then s = Left$(s, p - 1)
    s = Trim$(s)
    If Len(s) > 3 Then s = Left$(s, 3)
    ActivityCode = s
End Function

' Prioritet -> noeglen i SAP's prioritetsfelt.
'
'   Red (Statutory and SCEq)               -> 1
'   Yellow (default)                       -> 3
'   Blue (standing order)                  -> 6
'   (Kun notification) 3 Within a week     -> 3   (foerste ciffer)
'
' Tom streng, naar teksten ikke kan oversaettes. Saa efterlades feltet, som
' SAP saetter det, og valideringen siger det som en advarsel.
Public Function PriorityKey(ByVal s As String) As String
    Dim n As String
    Dim i As Long
    Dim c As String

    n = LCase$(StripLookupId(s))
    If Len(n) = 0 Then Exit Function

    If InStr(1, n, "yellow", vbBinaryCompare) > 0 Then
        PriorityKey = "3"
    ElseIf InStr(1, n, "blue", vbBinaryCompare) > 0 Or _
           InStr(1, n, "purple", vbBinaryCompare) > 0 Or _
           InStr(1, n, "standing", vbBinaryCompare) > 0 Then
        PriorityKey = "6"
    ElseIf InStr(1, n, "red", vbBinaryCompare) > 0 Or _
           InStr(1, n, "statutory", vbBinaryCompare) > 0 Or _
           InStr(1, n, "sceq", vbBinaryCompare) > 0 Then
        PriorityKey = "1"
    Else
        For i = 1 To Len(n)
            c = Mid$(n, i, 1)
            If c >= "0" And c <= "9" Then
                PriorityKey = c
                Exit Function
            End If
        Next i
    End If
End Function

' Revision -> GV_REVNR. Ja-feltet eller valget "REV - General Revision Mark".
Public Function RevisionValue(ByVal revision As Boolean, ByVal revisionMark As String) As String
    If revision Or UCase$(Left$(Trim$(StripLookupId(revisionMark)), 3)) = "REV" Then
        RevisionValue = "REV"
    End If
End Function

' Arbejdscenter: opslagsteksten har efterfoelgende mellemrum ("SSVAP   ").
Public Function WorkCenter(ByVal s As String) As String
    WorkCenter = UCase$(Trim$(StripLookupId(s)))
End Function

' De sidste fem tegn af arbejdscentret, fx SSVXSTIL -> XSTIL. Det er den
' noegle, ydelsen slaas op paa - samme regel som det gamle WorkCenterDict.
Public Function ServiceSuffix(ByVal workCenterText As String) As String
    Dim s As String
    s = WorkCenter(workCenterText)
    If Len(s) > 5 Then s = Right$(s, 5)
    ServiceSuffix = s
End Function

' Leverandoernummeret er de foranstillede cifre: "101985 - PERSOLIT" -> "101985".
' "0" og tom er "ingen leverandoer".
Public Function VendorNo(ByVal s As String) As String
    Dim i As Long
    Dim c As String
    Dim out As String

    s = Trim$(s)
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If c >= "0" And c <= "9" Then
            out = out & c
        Else
            Exit For
        End If
    Next i

    If Len(Replace(out, "0", "")) = 0 Then out = vbNullString
    VendorNo = out
End Function

'==============================================================================
' Cyklus og datoer
'==============================================================================

' Enheden, som SAP og opslaget kender den: DAY, WK, MON, YR eller H.
Public Function NormalizeUnit(ByVal s As String) As String
    s = UCase$(Replace(Trim$(s), " ", ""))
    Select Case s
        Case "D", "DAY", "DAYS", "DAG", "DAGE"
            NormalizeUnit = "DAY"
        Case "W", "WK", "WEEK", "WEEKS", "UGE", "UGER"
            NormalizeUnit = "WK"
        Case "M", "MO", "MON", "MONTH", "MONTHS", "MD", "MDR"
            NormalizeUnit = "MON"
        Case "Y", "YR", "YEAR", "YEARS", "AAR"
            NormalizeUnit = "YR"
        Case "H", "HR", "HOUR", "HOURS", "T", "TIME", "TIMER"
            NormalizeUnit = "H"
        Case Else
            NormalizeUnit = s
    End Select
End Function

' Noeglen i kaldshorisont-tabellen: 1 + WK -> "1WK", 2.5 + MON -> "2.5MON".
Public Function CycleKey(ByVal cycle As Double, ByVal unitText As String) As String
    CycleKey = NumberKey(cycle) & NormalizeUnit(unitText)
End Function

' Tal som tekst med punktum og uden overfloedige decimaler: 1 -> "1".
Public Function NumberKey(ByVal x As Double) As String
    Dim s As String
    s = Trim$(Str$(Round(x, 3)))
    If Left$(s, 1) = "." Then s = "0" & s
    If Left$(s, 2) = "-." Then s = "-0" & Mid$(s, 2)
    NumberKey = s
End Function

' Startdatoen i SAP er EEN cyklus foer foerste forfald. Appen spoerger efter
' foerste forfald (PlannedDate); SAP regner forfaldet som start + cyklus.
' Samme regel som det gamle ResolvePlanStartDate. Ved en enhed, der ikke er
' en tidsenhed (fx H), bruges datoen, som den er.
Public Function StartDate(ByVal firstDue As Date, ByVal cycle As Double, ByVal unitText As String) As Date
    Dim interval As String
    Dim n As Long

    StartDate = firstDue
    n = CLng(Int(cycle))
    If n <= 0 Then Exit Function

    Select Case NormalizeUnit(unitText)
        Case "DAY": interval = "d"
        Case "WK": interval = "ww"
        Case "MON": interval = "m"
        Case "YR": interval = "yyyy"
        Case Else: Exit Function
    End Select

    StartDate = DateAdd(interval, -n, firstDue)
End Function

' Dato i SAP-brugerens format. Det gamle script brugte dd.mm.yyyy.
Public Function SapDate(ByVal d As Date) As String
    SapDate = Format$(d, "dd") & "." & Format$(d, "mm") & "." & Format$(d, "yyyy")
End Function

' Tal til et SAP-felt: heltal uden decimaler, ellers med SAP-brugerens
' decimaltegn. Format$ bruges ikke: det tager Windows' decimaltegn, og det
' er ikke noedvendigvis det samme som SAP-brugerens.
Public Function SapNumber(ByVal x As Double, ByVal decimalSep As String) As String
    If Len(decimalSep) = 0 Then decimalSep = ","
    SapNumber = Replace(NumberKey(x), ".", decimalSep)
End Function

'==============================================================================
' Objektlisten
'==============================================================================

' Objektlisten som FL-koder, i raekkefoelge og uden dubletter.
'
' To formater findes i listen:
'   ny app      "SSV13 HFC10; SSV13 HFC20AT002"
'   gammel app  "AVV50 CYT25GS001 -H02 - CO DETEKTION|||AVV50 AKT10 - Bygge..."
'
' FL-koder kan indeholde mellemrum og " -H02", men aldrig ";" eller " - "
' (mellemrum, bindestreg, mellemrum). Alt efter " - " er beskrivelsen.
Public Function ObjectListEntries(ByVal raw As String) As Collection
    Dim result As New Collection
    Dim parts() As String
    Dim i As Long
    Dim e As String
    Dim seen As String

    raw = Replace(raw, vbCrLf, vbLf)
    raw = Replace(raw, vbCr, vbLf)
    raw = Replace(raw, "|||", vbLf)
    raw = Replace(raw, ";", vbLf)

    parts = Split(raw, vbLf)
    seen = "|"
    For i = LBound(parts) To UBound(parts)
        e = ObjectEntry(parts(i))
        If Len(e) > 0 Then
            If InStr(1, seen, "|" & UCase$(e) & "|", vbBinaryCompare) = 0 Then
                result.Add e
                seen = seen & UCase$(e) & "|"
            End If
        End If
    Next i

    Set ObjectListEntries = result
End Function

Private Function ObjectEntry(ByVal s As String) As String
    Dim p As Long
    s = Replace(s, vbTab, " ")
    s = Replace(s, ChrW$(160), " ")
    s = Trim$(s)
    p = InStr(1, s, " - ", vbBinaryCompare)
    If p > 0 Then s = Left$(s, p - 1)
    ObjectEntry = Trim$(CollapseSpaces(s))
End Function

Public Function CollapseSpaces(ByVal s As String) As String
    Do While InStr(1, s, "  ", vbBinaryCompare) > 0
        s = Replace(s, "  ", " ")
    Loop
    CollapseSpaces = s
End Function

'==============================================================================
' Statuslinjen
'==============================================================================

' Det laengste tal i en tekst. "Task list 50012345 saved, counter 1" ->
' "50012345". Et objektnummer er laengere end de andre tal i en
' statusbesked (taellere, positioner).
Public Function LongestDigitRun(ByVal s As String) As String
    Dim i As Long
    Dim c As String
    Dim cur As String
    Dim best As String

    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If c >= "0" And c <= "9" Then
            cur = cur & c
        Else
            If Len(cur) > Len(best) Then best = cur
            cur = vbNullString
        End If
    Next i
    If Len(cur) > Len(best) Then best = cur
    LongestDigitRun = best
End Function
