Attribute VB_Name = "modInitialEntryValidation"
Option Explicit

' *** Konfiguration ***
Public Const FIRST_DATA_ROW As Long = 6

' *** Lazy init ***
Private isInit As Boolean
Private patterns As Variant
Private classDict As Object, classDict2 As Object
Private functionKeyDict As Object
Private br18Key17Rules As Object

' ============================================================
' Init: loader regexmï¿½nstre og klassedictionaries ï¿½n gang
' ============================================================
Public Sub InitValidation()
    If isInit Then Exit Sub
    
    patterns = KKSRules.GetKKSPatterns()
    
    Set classDict = CreateObject("Scripting.Dictionary")
    Set classDict2 = CreateObject("Scripting.Dictionary")
    Set functionKeyDict = CreateObject("Scripting.Dictionary")
    Set br18Key17Rules = CreateObject("Scripting.Dictionary")
    
    LoadClassDictionary "ClassDeterminationComponentKey", classDict
    LoadClassDictionary "ClassDeterminationAggregateKey", classDict2
    LoadClassDictionary "FunctionKeyDict", functionKeyDict
    Initial_Entry.LoadBR18Key17Rules "BR18_Keys", br18Key17Rules
    
    isInit = True
End Sub

' ============================================================
' Valider KUN EN rï¿½kke (uden Undo)
' ============================================================
Public Sub ValidateRowIncremental(ByVal ws As Worksheet, ByVal rowNum As Long)
    InitValidation
    
    Dim lastRow As Long: lastRow = ws.Cells(ws.Rows.count, "A").End(xlUp).Row
    If rowNum < FIRST_DATA_ROW Or rowNum > lastRow Then Exit Sub
    
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    ' Ryd visuelle ting for KUN denne rï¿½kke (farver, kommentarer, C:D indhold)
    ClearRowVisuals ws, rowNum
    
    ' ---------- Kolonne A: KKS ----------
    Dim regex As Object: Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False: regex.Global = True
    
    Dim valA As String: valA = CStr(ws.Cells(rowNum, "A").value)
    Dim isLegacyWarning As Boolean
    Dim aErrors As Collection: Set aErrors = New Collection
    
    Dim j As Long, matchFound As Boolean, matchedPattern As String
    matchFound = False: matchedPattern = ""
    
    For j = LBound(patterns) To UBound(patterns)
        regex.pattern = patterns(j)
        If regex.Test(valA) Then
            matchFound = True
            matchedPattern = patterns(j)
            Exit For
        End If
    Next j
    
    isLegacyWarning = KKSRules.IsLegacyHyphenFNumbering(valA)

    If Not matchFound Then
        If Len(valA) > 0 Then
            If isLegacyWarning Then
                aErrors.Add ValidationMessages.LegacyNumberingOnlyAcceptedIfExistingInPlant()
            Else
                aErrors.Add ValidationMessages.InvalidKKSCode()
            End If
        Else
            aErrors.Add ValidationMessages.KKSIsEmpty()
        End If
    End If
    
    ' Dublet-tjek for denne rï¿½kke
    If Len(valA) > 0 Then
        Dim countA As Long
        countA = Application.WorksheetFunction.CountIf(ws.Range("A" & FIRST_DATA_ROW & ":A" & lastRow), valA)
        If countA > 1 Then aErrors.Add ValidationMessages.DuplicateKKSCode()
    End If
    
    ' Skriv klasse ved KKS-pattern match (dette er KKS-type/klasse ï¿½ ikke den endelige kolonne C klasse)
    If matchFound Then AssignKKSClass ws, rowNum, matchedPattern
    If isLegacyWarning Then
        ws.Cells(rowNum, "D").value = "KKS"
        ws.Cells(rowNum, "D").Interior.Color = RGB(144, 238, 144)
    End If
    
    ' Skriv A-validering (inkl. evt. dubletfejl)
    ' WriteCellValidation hÃ¥ndterer selv gul farve (HasOnlyLegacyWarning) â€” kald HighlightWarning kun nÃ¥r KKS ikke matcher noget gyldigt mÃ¸nster
    WriteCellValidation ws.Cells(rowNum, "A"), aErrors
    If isLegacyWarning And Not matchFound Then
        Verification_Functions.HighlightWarning ws.Cells(rowNum, "A")
    End If
    
    ' ---------- Kolonne B: Beskrivelse ----------
    Dim valB As String: valB = CStr(ws.Cells(rowNum, "B").value)
    Dim bErrors As Collection: Set bErrors = New Collection
    
    If Len(valB) = 0 Then
        bErrors.Add ValidationMessages.DescriptionIsEmpty()
    ElseIf Len(valB) > 40 Then
        bErrors.Add "Max length exceeded (" & Len(valB) & "/40)"
    End If
    WriteCellValidation ws.Cells(rowNum, "B"), bErrors
    
    ' ---------- Kolonne C: Klassebestemmelse ----------
    ' Krav: hvis key18 findes, SKAL bï¿½de dict1 og dict2 matche (ellers fejl)
    ' Fejl skrives/markeres i A (KKS), IKKE i C.
    Dim detail As String
    Dim classOk As Boolean: classOk = True
    
    If Not Initial_Entry.DetermineClassEx(ws, rowNum, classDict, classDict2, functionKeyDict, br18Key17Rules, detail) Then
        classOk = False
    End If
    
    If Not classOk Then
        ' Tilfï¿½j klassefejl til Aï¿½s eksisterende fejl (sï¿½ de samles ï¿½t sted)
        Dim aErrors2 As Collection
        Set aErrors2 = ReadErrorsFromComment(ws.Cells(rowNum, "A"))
        If Len(Trim$(detail)) = 0 Then detail = ValidationMessages.NoClassDetermined()
        AddDetailMessagesToCollection aErrors2, detail
        WriteCellValidation ws.Cells(rowNum, "A"), aErrors2    ' note + farve i A
    End If
    
    ' ---------- Status (kolonne E) ----------
    Dim hasErr As Boolean
    hasErr = (CellHasBlockingValidationIssue(ws.Cells(rowNum, "A")) Or _
              CellHasBlockingValidationIssue(ws.Cells(rowNum, "B")) Or _
              CellHasBlockingValidationIssue(ws.Cells(rowNum, "C")))
    
    ws.Cells(rowNum, "E").value = IIf(hasErr, ChrW(&H26A0) & " " & ValidationMessages.StatusErrorNotReadyForSAP(), ChrW(&H2714) & " " & ValidationMessages.StatusReadyForSAP())
    
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
End Sub

' ============================================================
' Dublet-hï¿½ndtering
' ============================================================
' Opdater duplicate-flag kun for rï¿½kker med samme KKS
Public Sub RefreshDuplicateGroup(ByVal ws As Worksheet, ByVal kks As String, ByVal excludeRow As Long)
    If Len(kks) = 0 Then Exit Sub
    Dim lastRow As Long: lastRow = ws.Cells(ws.Rows.count, "A").End(xlUp).Row
    
    Dim cnt As Long
    cnt = Application.WorksheetFunction.CountIf(ws.Range("A" & FIRST_DATA_ROW & ":A" & lastRow), kks)
    
    Dim r As Long
    For r = FIRST_DATA_ROW To lastRow
        If r <> excludeRow Then
            If ws.Cells(r, "A").value = kks Then
                UpdateDuplicateFlagForRow ws, r, (cnt > 1)
            End If
        End If
    Next r
End Sub

' Reberegn duplicate-flag for HELE kolonne A (bruges ved multi-cell ï¿½ndringer)
Public Sub RefreshAllDuplicateFlags(ByVal ws As Worksheet)
    Dim lastRow As Long: lastRow = ws.Cells(ws.Rows.count, "A").End(xlUp).Row
    Dim dict As Object: Set dict = CreateObject("Scripting.Dictionary")
    
    Dim r As Long, valA As String
    For r = FIRST_DATA_ROW To lastRow
        valA = ws.Cells(r, "A").value
        If valA <> "" Then dict(valA) = dict(valA) + 1
    Next r
    
    For r = FIRST_DATA_ROW To lastRow
        valA = ws.Cells(r, "A").value
        UpdateDuplicateFlagForRow ws, r, (valA <> "" And dict.exists(valA) And dict(valA) > 1)
    Next r
End Sub

' Sï¿½t/fjern "Duplicate KKS-code" i kommentaren og opdatï¿½r status E
Private Sub UpdateDuplicateFlagForRow(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal isDup As Boolean)
    Dim c As Range: Set c = ws.Cells(rowNum, "A")
    Dim msgs As Collection: Set msgs = ReadErrorsFromComment(c)
    
    RemoveMsg msgs, ValidationMessages.DuplicateKKSCode()
    If isDup Then msgs.Add ValidationMessages.DuplicateKKSCode()
    WriteCellValidation c, msgs
    
    Dim hasErr As Boolean
    hasErr = (CellHasBlockingValidationIssue(ws.Cells(rowNum, "A")) Or _
              CellHasBlockingValidationIssue(ws.Cells(rowNum, "B")) Or _
              CellHasBlockingValidationIssue(ws.Cells(rowNum, "C")))
    
    ws.Cells(rowNum, "E").value = IIf(hasErr, ChrW(&H26A0) & " " & ValidationMessages.StatusErrorNotReadyForSAP(), ChrW(&H2714) & " " & ValidationMessages.StatusReadyForSAP())
End Sub

' ============================================================
' Kommentar/Notes utils
' ============================================================
Private Function ReadErrorsFromComment(ByVal cell As Range) As Collection
    Dim col As New Collection
    Dim currentMsg As String
    On Error Resume Next
        Dim txt As String: txt = cell.Comment.text
    On Error GoTo 0
    
    If Len(txt) = 0 Then
        Set ReadErrorsFromComment = col
        Exit Function
    End If
    
    Dim body As String
    If Left$(txt, 11) = "Validation:" Then
        body = Mid$(txt, 12)
    Else
        body = txt
    End If
    
    Dim lines() As String, i As Long, line As String
    lines = Split(body, vbCrLf)
    For i = LBound(lines) To UBound(lines)
        line = Trim$(lines(i))
        If Len(line) > 0 Then
            line = Replace(line, "ï¿½ ", "")
            If Left$(line, 2) = ChrW(&H26A0) & " " Then
                If Len(currentMsg) > 0 Then col.Add currentMsg
                currentMsg = Mid$(line, 3)
            ElseIf Len(currentMsg) > 0 Then
                currentMsg = currentMsg & vbCrLf & line
            Else
                currentMsg = line
            End If
        End If
    Next i

    If Len(currentMsg) > 0 Then col.Add currentMsg
    
    Set ReadErrorsFromComment = col
End Function

Private Sub RemoveMsg(ByRef col As Collection, ByVal msg As String)
    Dim i As Long
    For i = col.count To 1 Step -1
        If StrComp(CStr(col(i)), msg, vbTextCompare) = 0 Then
            col.Remove i
            Exit For
        End If
    Next i
End Sub

Private Sub WriteCellValidation(ByVal cell As Range, ByVal msgs As Collection)
    On Error Resume Next
        cell.ClearComments
    On Error GoTo 0
    
    If msgs Is Nothing Or msgs.count = 0 Then
        HighlightValid cell
    Else
        If HasOnlyLegacyWarning(msgs) Then
            Verification_Functions.HighlightWarning cell
        Else
            HighlightError cell
        End If
        Dim s As String, i As Long, j As Long
        Dim lines() As String
        Dim lineText As String
        s = "Validation:" & vbCrLf
        For i = 1 To msgs.count
            lines = Split(CStr(msgs(i)), vbCrLf)
            For j = LBound(lines) To UBound(lines)
                lineText = Trim$(lines(j))
                If Len(lineText) > 0 Then
                    If j = LBound(lines) Then
                        s = s & ChrW(&H26A0) & " " & lineText
                    Else
                        s = s & lineText
                    End If
                    s = s & vbCrLf
                End If
            Next j

            If Right$(s, 2) = vbCrLf Then s = Left$(s, Len(s) - 2)
            If i < msgs.count Then s = s & vbCrLf
        Next i
        cell.AddComment s
        cell.Comment.Visible = False
        With cell.Comment.Shape
            .TextFrame.AutoSize = True
            If .Width > 200 Then
                .Width = 200
                .TextFrame.AutoSize = True
            End If
        End With
    End If
End Sub

Private Function HasOnlyLegacyWarning(ByVal msgs As Collection) As Boolean
    Dim i As Long
    Dim warningText As String

    If msgs Is Nothing Then Exit Function
    If msgs.count = 0 Then Exit Function

    warningText = ValidationMessages.LegacyNumberingOnlyAcceptedIfExistingInPlant()

    For i = 1 To msgs.count
        If StrComp(Trim$(CStr(msgs(i))), warningText, vbTextCompare) <> 0 Then
            Exit Function
        End If
    Next i

    HasOnlyLegacyWarning = True
End Function

Private Function CellHasBlockingValidationIssue(ByVal cell As Range) As Boolean
    Dim msgs As Collection

    If cell Is Nothing Then Exit Function
    If Not CellHasComment(cell) Then Exit Function

    Set msgs = ReadErrorsFromComment(cell)
    If msgs Is Nothing Then Exit Function
    If msgs.count = 0 Then Exit Function

    CellHasBlockingValidationIssue = Not HasOnlyLegacyWarning(msgs)
End Function

' ============================================================
' Dine eksisterende helpers
' ============================================================
Public Sub LoadClassDictionary(tableName As String, dict As Object)
    Initial_Entry.LoadClassDictionary tableName, dict
End Sub

Private Sub HighlightError(cell As Range)
    Verification_Functions.HighlightError cell
End Sub

Private Sub HighlightValid(cell As Range)
    Verification_Functions.HighlightValid cell
End Sub

Public Sub AssignKKSClass(ws As Worksheet, rowNum As Long, pattern As String)
    Initial_Entry.AssignKKSClass ws, rowNum, pattern
End Sub

Private Sub ClearRowVisuals(ByVal ws As Worksheet, ByVal rowNum As Long)
    ws.Range("A" & rowNum & ":D" & rowNum).Interior.ColorIndex = xlNone
    ws.Range("C" & rowNum & ":D" & rowNum).ClearContents
    On Error Resume Next
        ws.Range("A" & rowNum & ":C" & rowNum).ClearComments
    On Error GoTo 0
End Sub


'Public Function DetermineClassEx( _
'    ws As Worksheet, _
'    rowNum As Long, _
'    dict1 As Object, _
'    dict2 As Object, _
'    Optional ByRef detailMsg As String _
') As Boolean
'
'    Dim valueA As String
'    Dim key18 As String, key12 As String
'    Dim foundDict1 As Boolean, foundDict2 As Boolean
'    Dim classSet As Boolean
'    Dim regex As Object, k As Long
'    Dim shortPatterns As Variant
'
'    valueA = CStr(ws.Cells(rowNum, 1).value)
'
'    ' Udtrï¿½k nï¿½gler (tom hvis for kort)
'    key18 = Mid$(valueA, 18, 2)
'    key12 = Mid$(valueA, 12, 2)
'
'    ' Opslag hvis nï¿½gler har lï¿½ngde 2
'    If Len(key18) = 2 Then foundDict1 = dict1.exists(key18)
'    If Len(key12) = 2 Then foundDict2 = dict2.exists(key12)
'
'    ' --- KRAV: hvis key18 findes, SKAL bï¿½de dict1 og dict2 findes ---
'    If Len(key18) = 2 Then
'        If foundDict1 And foundDict2 Then
'            ws.Cells(rowNum, 3).value = dict1(key18)   ' prioritet til dict1 ved succes
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'        Else
'            detailMsg = ""
'            If Not foundDict1 Then detailMsg = detailMsg & "'" & key18 & "' is not an accepted Component key" & vbCrLf
'            If Not foundDict2 Then detailMsg = detailMsg & "'" & key12 & "' is not an accepted Equipment key" & vbCrLf
'            DetermineClassEx = False
'        End If
'        Exit Function
'    End If
'
'    ' --- key18 mangler: ï¿½t ordbogs-match kan vï¿½re nok ---
'    If Not classSet Then
'        If foundDict1 Then
'            ws.Cells(rowNum, 3).value = dict1(key18)   ' (key18 er tom; behold for kompatibilitet hvis dict1("") bruges)
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'            Exit Function
'        ElseIf foundDict2 Then
'            ws.Cells(rowNum, 3).value = dict2(key12)
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'            Exit Function
'        End If
'    End If
'
'    ' --- Regex-fallback: MKP/FP KUN hvis foundDict2 = True ---
'    Set regex = CreateObject("VBScript.RegExp")
'    regex.IgnoreCase = False
'    regex.Global = True
'
'    ' MKP
'    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FD|FG|FH|FW|FC)$"
'    If regex.Test(valueA) Then
'        If foundDict2 Then
'            ws.Cells(rowNum, 3).value = "MKP"
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'            Exit Function
'        Else
'            detailMsg = "'" & key12 & "' is not an accepted Equipment key" & vbCrLf
'            DetermineClassEx = False
'            Exit Function
'        End If
'    End If
'
'    ' FP -> tom (OK)  (krï¿½ver ogsï¿½ foundDict2 = True)
'    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FP)$"
'    If regex.Test(valueA) Then
'        If foundDict2 Then
'            ws.Cells(rowNum, 3).value = "NO CLASS"   ' eksplicit tom klasse
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'            Exit Function
'        Else
'            detailMsg = "'" & key12 & "' is not an accepted Equipment key" & vbCrLf
'            DetermineClassEx = False
'            Exit Function
'        End If
'    End If
'
'    ' --- (Valgfrit) yderligere "short patterns"
'    ' Beholdt som tidligere ï¿½ de sï¿½tter tom klasse "" uden dict2-krav.
'    ' Hvis du ogsï¿½ vil gate dem bag foundDict2, kopier samme mï¿½nster som overfor.
'    shortPatterns = Array( _
'        "^[A-Z]{3}\d{2}[\d\s][A-Z]{2}$", _
'        "^[A-Z]{3}\d{2}[\d\s][A-Z]{1}$", _
'        "^[A-Z]{3}\d{2,3}$", _
'        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}$", _
'        "^[A-Z]{3}\d{2}[\d\s][C-Z][A-Z]{2}\d{2}$" _
'    )
'    For k = LBound(shortPatterns) To UBound(shortPatterns)
'        regex.pattern = shortPatterns(k)
'        If regex.Test(valueA) Then
'            ws.Cells(rowNum, 3).value = "NO CLASS"
'            HighlightValid ws.Cells(rowNum, 3)
'            DetermineClassEx = True
'            Exit Function
'        End If
'    Next k
'
'    ' Sidste specifikke: ELF
'    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-B][A-Z]{2}\d{2}$"
'    If regex.Test(valueA) Then
'        ws.Cells(rowNum, 3).value = "ELF"
'        HighlightValid ws.Cells(rowNum, 3)
'        DetermineClassEx = True
'        Exit Function
'    End If
'
'    ' Intet matchede
'    detailMsg = "Class not determined: '" & key12 & "' is not an accepted Equipment key"
'    DetermineClassEx = False
'End Function

Public Function DetermineClassEx( _
    ws As Worksheet, _
    rowNum As Long, _
    dict1 As Object, _
    dict2 As Object, _
    Optional ByRef detailMsg As String _
) As Boolean

    Dim valueA As String
    Dim key18 As String, key12 As String, key7 As String, key0 As String
    Dim status As Long
    Dim syntaxClassIsKAB As Boolean
    
    valueA = CStr(ws.Cells(rowNum, 1).value)
    
    ' Udtrï¿½k nï¿½gler (tom hvis for kort)
    key18 = Mid$(valueA, 18, 2)
    key12 = Mid$(valueA, 12, 2)
    key7 = Mid$(valueA, 7, 3)
    key0 = Left(valueA, 3)
    syntaxClassIsKAB = (UCase$(Trim$(CStr(ws.Cells(rowNum, 3).Value2))) = "KAB")

    If syntaxClassIsKAB Then
        DetermineClassEx = True
        Exit Function
    End If
    
    ' 1) Fï¿½rst: forsï¿½g via key18-reglen (hï¿½rdt krav hvis key18 findes)
    status = DetermineClass_ByKey18(ws, rowNum, key18, key12, dict1, dict2, detailMsg)
    
    ' status:  1 = succes, 0 = fejl, -1 = ikke relevant (key18 mangler)
    If status <> -1 Then
        DetermineClassEx = (status = 1)
        Exit Function
    End If
    
    ' 2) Hvis key18 ikke var relevant: kï¿½r key12 + regex fallback
    DetermineClassEx = DetermineClass_ByKey12(ws, rowNum, valueA, key12, dict2, detailMsg)

End Function

Private Sub AddDetailMessagesToCollection(ByRef msgs As Collection, ByVal detail As String)
    Dim lines() As String
    Dim i As Long
    Dim lineText As String
    Dim currentMsg As String
    Dim inAllowedBlock As Boolean

    If Len(Trim$(detail)) = 0 Then Exit Sub

    lines = Split(detail, vbCrLf)
    For i = LBound(lines) To UBound(lines)
        lineText = Trim$(lines(i))
        If Len(lineText) = 0 Then GoTo ContinueLoop

        If lineText = "Allowed:" Then
            If Len(currentMsg) = 0 Then currentMsg = lineText Else currentMsg = currentMsg & vbCrLf & lineText
            inAllowedBlock = True
            GoTo ContinueLoop
        End If

        If inAllowedBlock Then
            If InStr(1, lineText, " - ", vbTextCompare) > 0 Then
                currentMsg = currentMsg & vbCrLf & lineText
                GoTo ContinueLoop
            Else
                If Len(currentMsg) > 0 Then msgs.Add currentMsg
                currentMsg = ""
                inAllowedBlock = False
            End If
        End If

        If Len(currentMsg) > 0 Then msgs.Add currentMsg
        currentMsg = lineText

ContinueLoop:
    Next i

    If Len(currentMsg) > 0 Then msgs.Add currentMsg
End Sub

Public Function DetermineClass_ByKey18( _
    ws As Worksheet, _
    rowNum As Long, _
    key18 As String, _
    key12 As String, _
    dict1 As Object, _
    dict2 As Object, _
    Optional ByRef detailMsg As String _
) As Long

    DetermineClass_ByKey18 = Initial_Entry.DetermineClass_ByKey18(ws, rowNum, key18, key12, dict1, dict2, detailMsg)

End Function

Public Function DetermineClass_ByKey12( _
    ws As Worksheet, _
    rowNum As Long, _
    valueA As String, _
    key12 As String, _
    dict2 As Object, _
    Optional ByRef detailMsg As String _
) As Boolean

    DetermineClass_ByKey12 = Initial_Entry.DetermineClass_ByKey12(ws, rowNum, valueA, key12, dict2, detailMsg)

End Function



Private Function CellHasComment(ByVal cell As Range) As Boolean
    On Error Resume Next
        CellHasComment = Not cell.Comment Is Nothing
    On Error GoTo 0
End Function


