Attribute VB_Name = "Initial_Entry"
Option Explicit

Sub VerifyInputsAndClassDeterminationNew()
    Dim regex As Object, ws As Worksheet
    Dim lastRowA As Long, i As Long, j As Long
    Dim cell As Range, valueA As String
    Dim matchFound As Boolean, matchedPattern As String
    Dim classDict As Object, classDict2 As Object, functionKeyDict As Object, br18Key17Rules As Object
    Dim seenDict As Object, cellErrors As Object
    Dim patterns As Variant
    Dim aHasError As Boolean  ' sporer om kolonne A har fejl for rï¿½kken
    Dim prevScr As Boolean, prevEvt As Boolean, prevCalc As XlCalculation

    On Error GoTo Fail

    ' Performance
    prevScr = Application.ScreenUpdating
    prevCalc = Application.Calculation
    prevEvt = Application.EnableEvents
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    Application.EnableEvents = False

    ' KKS-mï¿½nstre (centraliseret)
    patterns = KKSRules.GetKKSPatterns()

    ' Dictionaries
    Set classDict = CreateObject("Scripting.Dictionary")
    Set classDict2 = CreateObject("Scripting.Dictionary")
    Set functionKeyDict = CreateObject("Scripting.Dictionary")
    Set br18Key17Rules = CreateObject("Scripting.Dictionary")
    Set seenDict = CreateObject("Scripting.Dictionary")
    Set cellErrors = CreateObject("Scripting.Dictionary")  ' key: "row|col" -> Collection of strings

    LoadClassDictionary "ClassDeterminationComponentKey", classDict
    LoadClassDictionary "ClassDeterminationAggregateKey", classDict2
    LoadClassDictionary "FunctionKeyDict", functionKeyDict
    LoadBR18Key17Rules "BR18_Keys", br18Key17Rules

    ' Ark og omrï¿½de
    Set ws = ThisWorkbook.Sheets("Initial Entry")
    lastRowA = ws.Cells(ws.Rows.count, "A").End(xlUp).Row

    ' Ryd farver og gamle noter/kommentarer i A:C
    ClearColors ws, lastRowA
    If lastRowA >= 6 Then ws.Range("A6:C" & lastRowA).ClearComments

    ' RegEx
    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = True

    ' --- KOLONNE A: KKS + duplikat + mï¿½nster ---
    For i = 6 To lastRowA
        Set cell = ws.Cells(i, 1)
        valueA = cell.value
        matchFound = False
        matchedPattern = ""
        aHasError = False

        ' Duplikat (ignorer tomme)
        If Len(valueA) > 0 Then
            If seenDict.exists(valueA) Then
                HighlightError cell
                AddCellError cellErrors, i, 1, ValidationMessages.DuplicateKKSCode()
                aHasError = True
            Else
                seenDict.Add valueA, True
            End If
        End If

        ' Mï¿½nster-validering
        For j = LBound(patterns) To UBound(patterns)
            regex.pattern = patterns(j)
            If regex.Test(valueA) Then
                matchFound = True
                matchedPattern = patterns(j)
                Exit For
            End If
        Next j

        If matchFound Then
            AssignKKSClass ws, i, matchedPattern
            If Not aHasError Then HighlightValid cell
        ElseIf KKSRules.IsLegacyHyphenFNumbering(valueA) Then
            AddCellError cellErrors, i, 1, ValidationMessages.LegacyNumberingOnlyAcceptedIfExistingInPlant()
            If Not aHasError Then HighlightWarning cell
            ws.Cells(i, 4).value = "KKS"
            ws.Cells(i, 4).Interior.Color = RGB(144, 238, 144)
        Else
            HighlightError cell
            AddCellError cellErrors, i, 1, ValidationMessages.InvalidKKSCode()
        End If
    Next i

    ' --- KOLONNE B: Beskrivelse ---
    Dim desc As String
    For i = 6 To lastRowA
        Set cell = ws.Cells(i, 2)
        desc = CStr(cell.value)

        If Len(desc) = 0 Then
            HighlightError cell
            AddCellError cellErrors, i, 2, ValidationMessages.DescriptionIsEmpty()
        ElseIf Len(desc) > 40 Then
            HighlightError cell
            AddCellError cellErrors, i, 2, " Max length exceeded (" & Len(desc) & "/" & 40 & ")"
        Else
            HighlightValid cell
        End If
    Next i

    ' --- KOLONNE C: Klassebestemmelse + key-validering ---
    Dim classOk As Boolean
    Dim detailMsg As String
    For i = 6 To lastRowA
        detailMsg = ""
        classOk = DetermineClassEx(ws, i, classDict, classDict2, functionKeyDict, br18Key17Rules, detailMsg)
        If Not classOk Then
            HighlightError ws.Cells(i, 1)
            HighlightError ws.Cells(i, 3)
            If Len(detailMsg) > 0 Then
                AddDetailErrors cellErrors, i, 1, detailMsg
            Else
                AddCellError cellErrors, i, 1, ValidationMessages.NoClassDetermined()
            End If
        End If
    Next i

    ' --- SKRIV NOTER/COMMENTS Pï¿½ DE CELLER MED FEJL ---
    Dim k As Variant, rowNum As Long, colNum As Long
    Dim noteText As String
    For Each k In cellErrors.keys
        rowNum = CLng(Split(k, "|")(0))
        colNum = CLng(Split(k, "|")(1))
        noteText = BuildErrorText(cellErrors(k))
        AddCellComment ws.Cells(rowNum, colNum), noteText
    Next k


    ' --- Sï¿½t status i kolonne E pr. rï¿½kke ---
    Dim r As Long
    For r = 6 To lastRowA
        If RowHasErrors(cellErrors, r) Then
            ws.Cells(r, 5).value = ValidationMessages.StatusErrorNotReadyForSAP()
        Else
            ws.Cells(r, 5).value = ValidationMessages.StatusReadyForSAP()
        End If
    Next


    ' Restore
SafeExit:
    Application.ScreenUpdating = prevScr
    Application.Calculation = prevCalc
    Application.EnableEvents = prevEvt
    Exit Sub

Fail:
    MsgBox ValidationMessages.ErrorVerifyInputsAndClassDeterminationNew(Err.description), vbExclamation
    Resume SafeExit
End Sub

Public Sub LoadBR18Key17Rules(ByVal tableName As String, ByVal dict As Object)
    Dim ws As Worksheet
    Dim lo As ListObject
    Dim dataRange As Range
    Dim i As Long
    Dim aggregateKey As String
    Dim key17 As String
    Dim key17Description As String
    Dim allowedSet As Object

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("DictionaryTable")
    On Error GoTo 0
    If ws Is Nothing Then
        Err.Raise vbObjectError + 2001, "LoadBR18Key17Rules", ValidationMessages.DictionarySheetNotFound()
    End If

    On Error Resume Next
    Set lo = ws.ListObjects(tableName)
    On Error GoTo 0
    If lo Is Nothing Then
        Err.Raise vbObjectError + 2002, "LoadBR18Key17Rules", ValidationMessages.DictionaryTableNotFound(tableName)
    End If

    Set dataRange = lo.DataBodyRange
    If dataRange Is Nothing Then Exit Sub

    For i = 1 To dataRange.Rows.count
        aggregateKey = UCase$(Trim$(CStr(dataRange.Cells(i, 1).value)))
        key17 = UCase$(Trim$(CStr(dataRange.Cells(i, 2).value)))
        key17Description = Trim$(CStr(dataRange.Cells(i, 3).Value2))

        If Len(aggregateKey) > 0 And Len(key17) > 0 Then
            If dict.exists(aggregateKey) Then
                Set allowedSet = dict(aggregateKey)
            Else
                Set allowedSet = CreateObject("Scripting.Dictionary")
                dict.Add aggregateKey, allowedSet
            End If

            allowedSet(key17) = key17Description
        End If
    Next i
End Sub

' Returnerer True, hvis der findes mindst ï¿½n fejl for rï¿½kken (uanset kolonne)
Function RowHasErrors(errDict As Object, rowNum As Long) As Boolean
    Dim k As Variant, prefix As String
    Dim errCol As Collection

    prefix = CStr(rowNum) & "|"
    For Each k In errDict.keys
        If Left$(CStr(k), Len(prefix)) = prefix Then
            Set errCol = errDict(k)
            If HasBlockingErrors(errCol) Then
                RowHasErrors = True
                Exit Function
            End If
        End If
    Next k

End Function

Private Function HasBlockingErrors(ByVal errCol As Collection) As Boolean
    Dim i As Long
    Dim msg As String

    If errCol Is Nothing Then Exit Function
    If errCol.count = 0 Then Exit Function

    For i = 1 To errCol.count
        msg = Trim$(CStr(errCol(i)))
        If StrComp(msg, ValidationMessages.LegacyNumberingOnlyAcceptedIfExistingInPlant(), vbTextCompare) <> 0 Then
            HasBlockingErrors = True
            Exit Function
        End If
    Next i
End Function


'-------------------- Hjï¿½lpefunktioner --------------------

Sub LoadClassDictionary(tableName As String, dict As Object)
    Dim ws As Worksheet, tableRange As Range, keys As Variant, values As Variant, i As Long

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("DictionaryTable")
    On Error GoTo 0
    If ws Is Nothing Then
        Err.Raise vbObjectError + 2001, "LoadClassDictionary", ValidationMessages.DictionarySheetNotFound()
    End If

    On Error Resume Next
    Set tableRange = ws.ListObjects(tableName).Range
    On Error GoTo 0

    If tableRange Is Nothing Then
        Err.Raise vbObjectError + 2002, "LoadClassDictionary", ValidationMessages.DictionaryTableNotFound(tableName)
    End If

    keys = Application.Transpose(tableRange.Columns(1).value)
    values = Application.Transpose(tableRange.Columns(2).value)
    For i = LBound(keys) To UBound(keys)
        If Not IsEmpty(keys(i)) Then dict(keys(i)) = values(i)
    Next i
End Sub

Sub AddCellComment(cell As Range, msg As String)
    If Len(msg) > 0 Then
        Verification_Functions.AddCellComment cell, "Validation:" & vbCrLf & msg
    Else
        Verification_Functions.AddCellComment cell, ""
    End If
End Sub

Sub HighlightError(cell As Range)
    Verification_Functions.HighlightError cell
End Sub

Sub HighlightValid(cell As Range)
    Verification_Functions.HighlightValid cell
End Sub

Sub HighlightWarning(cell As Range)
    Verification_Functions.HighlightWarning cell
End Sub

Sub AssignKKSClass(ws As Worksheet, rowNum As Long, pattern As String)
    With ws
        Select Case pattern
            Case "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{1}\d{4}$"
                .Cells(rowNum, 4).value = "KKSKV"
                .Cells(rowNum, 3).value = "KAB"
            Case "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\s{3}\d{4}$"
                .Cells(rowNum, 4).value = "KKSKV"
                .Cells(rowNum, 3).value = "KAB"
            Case "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{4}$"
                .Cells(rowNum, 4).value = "KKSKA"
                .Cells(rowNum, 3).value = "KAB"
            Case Else
                .Cells(rowNum, 4).value = "KKS"
        End Select
        .Cells(rowNum, 3).Interior.Color = RGB(144, 238, 144)
        .Cells(rowNum, 4).Interior.Color = RGB(144, 238, 144)
    End With
End Sub


Sub ClearColors(ws As Worksheet, lastRow As Long)

    If lastRow >= 6 Then
        ' Fjern farver i A:D
        ws.Range("A6:D" & lastRow).Interior.ColorIndex = xlNone

        ' Slet indhold i C og D
        ws.Range("C6:D" & lastRow).ClearContents
    End If

End Sub


Public Function DetermineClassEx( _
    ws As Worksheet, _
    rowNum As Long, _
    dict1 As Object, _
    dict2 As Object, _
    FunctionKeys As Object, _
    br18Key17Rules As Object, _
    Optional ByRef detailMsg As String _
) As Boolean

    Dim valueA As String
    Dim key18 As String, key12 As String, key7 As String, key0 As String, key17 As String
    Dim status As Long, functionKeyStatus As Long, br18Status As Long
    Dim classOk As Boolean
    Dim hasErrors As Boolean
    Dim syntaxClassIsKAB As Boolean
    Dim stepMsg As String
    
    valueA = CStr(ws.Cells(rowNum, 1).value)
    
    ' Udtrï¿½k nï¿½gler (tom hvis for kort)
    key0 = Left$(valueA, 3)
    key18 = Mid$(valueA, 18, 2)
    key12 = Mid$(valueA, 12, 2)
    key7 = Mid$(valueA, 7, 3)
    key17 = Mid$(valueA, 17, 2)

    detailMsg = ""
    hasErrors = False
    classOk = False
    syntaxClassIsKAB = (UCase$(Trim$(CStr(ws.Cells(rowNum, 3).Value2))) = "KAB")

    ' 1) Verificer key0 (station code)
    If Not IsAllowedKey0(key0, stepMsg) Then
        hasErrors = True
        AppendDetailMessage detailMsg, stepMsg
    End If
    
    ' 2) Kontroller om Function Key kan bruges
    functionKeyStatus = DetermineValidFunctionKey(ws, rowNum, key7, FunctionKeys, stepMsg)
    If functionKeyStatus = 0 Then
        hasErrors = True
        AppendDetailMessage detailMsg, stepMsg
    End If

    ' 2b) BR18 UF/UE rule: key7 must start with U and key17 must be allowed for key12
    br18Status = DetermineValidBR18Key17(key12, key17, key7, valueA, br18Key17Rules, stepMsg)
    If br18Status = 0 Then
        hasErrors = True
        AppendDetailMessage detailMsg, stepMsg
    End If
    
    If syntaxClassIsKAB Then
        ' Business rule: KAB assigned by syntax must not be rejected by key12/key18 checks.
        classOk = True
    Else
        ' 3) Fï¿½rst: forsï¿½g via key18-reglen (hï¿½rdt krav hvis key18 findes)
        status = DetermineClass_ByKey18(ws, rowNum, key18, key12, dict1, dict2, stepMsg)
        
        ' status:  1 = succes, 0 = fejl, -1 = ikke relevant (key18 mangler)
        If status <> -1 Then
            classOk = (status = 1)
            If Not classOk Then
                hasErrors = True
                AppendDetailMessage detailMsg, stepMsg
            End If
        Else
            ' 4) Hvis key18 ikke var relevant: kï¿½r key12 + regex fallback
            classOk = DetermineClass_ByKey12(ws, rowNum, valueA, key12, dict2, stepMsg)
            If Not classOk Then
                hasErrors = True
                AppendDetailMessage detailMsg, stepMsg
            End If
        End If
    End If
    
    DetermineClassEx = (classOk And Not hasErrors)

End Function

Private Function DetermineValidBR18Key17( _
    ByVal key12 As String, _
    ByVal key17 As String, _
    ByVal key7 As String, _
    ByVal functionalLocation As String, _
    ByVal br18Key17Rules As Object, _
    Optional ByRef detailMsg As String = "" _
) As Long

    Dim key12Norm As String
    Dim key17Norm As String
    Dim key7Norm As String
    Dim flBase As String
    Dim allowedSet As Object
    Dim allowedValues As String

    key12Norm = UCase$(Trim$(key12))
    key17Norm = UCase$(Trim$(key17))
    key7Norm = UCase$(Trim$(key7))
    flBase = GetBR18FunctionalLocationBase(functionalLocation)
    detailMsg = ""

    If key12Norm <> "UF" And key12Norm <> "UE" Then
        DetermineValidBR18Key17 = -1
        Exit Function
    End If

    If Len(key7Norm) = 0 Or Left$(key7Norm, 1) <> "U" Then
        detailMsg = ValidationMessages.FunctionKeyMustStartWithUForAggregateKey(key12Norm, key7Norm)
    End If

    If Not br18Key17Rules.exists(key12Norm) Then
        If Len(detailMsg) > 0 Then detailMsg = detailMsg & vbCrLf
        detailMsg = detailMsg & ValidationMessages.NoKey17RulesConfiguredForAggregateKey(key12Norm)
        DetermineValidBR18Key17 = 0
        Exit Function
    End If

    Set allowedSet = br18Key17Rules(key12Norm)
    allowedValues = BuildBR18AllowedValuesText(allowedSet, flBase)

    If Not allowedSet.exists(key17Norm) Then
        If Len(detailMsg) > 0 Then detailMsg = detailMsg & vbCrLf
        detailMsg = detailMsg & ValidationMessages.Key17NotAcceptedForAggregateKey(key12Norm, key17Norm, allowedValues)
    End If

    If Len(detailMsg) > 0 Then
        DetermineValidBR18Key17 = 0
    Else
        DetermineValidBR18Key17 = 1
    End If

End Function

Private Function GetBR18FunctionalLocationBase(ByVal functionalLocation As String) As String
    Dim fl As String

    fl = UCase$(Trim$(functionalLocation))
    If Len(fl) > 16 Then
        fl = Left$(fl, 16)
    End If

    GetBR18FunctionalLocationBase = fl
End Function

Private Function BuildBR18AllowedValuesText(ByVal allowedSet As Object, ByVal flBase As String) As String
    Dim items() As String
    Dim key As Variant
    Dim description As String
    Dim keyText As String
    Dim idx As Long

    If allowedSet Is Nothing Then Exit Function
    If allowedSet.count = 0 Then Exit Function

    ReDim items(0 To allowedSet.count - 1)
    idx = 0

    For Each key In allowedSet.keys
        keyText = CStr(key)
        If Len(flBase) > 0 Then keyText = flBase & keyText

        description = Trim$(CStr(allowedSet(key)))
        If Len(description) > 0 Then
            items(idx) = keyText & " - " & description
        Else
            items(idx) = keyText
        End If
        idx = idx + 1
    Next key

    BuildBR18AllowedValuesText = Join(items, ", ")
End Function

Private Sub AppendDetailMessage(ByRef destination As String, ByVal detailPart As String)
    If Len(Trim$(detailPart)) = 0 Then Exit Sub
    If Len(destination) > 0 Then destination = destination & vbCrLf
    destination = destination & Trim$(detailPart)
End Sub

Private Sub AddDetailErrors(errDict As Object, rowNum As Long, colNum As Long, detailMsg As String)
    Dim lines() As String
    Dim i As Long
    Dim lineText As String
    Dim currentMsg As String
    Dim inAllowedBlock As Boolean

    If Len(Trim$(detailMsg)) = 0 Then Exit Sub

    lines = Split(detailMsg, vbCrLf)
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
                If Len(currentMsg) > 0 Then AddCellError errDict, rowNum, colNum, currentMsg
                currentMsg = ""
                inAllowedBlock = False
            End If
        End If

        If Len(currentMsg) > 0 Then AddCellError errDict, rowNum, colNum, currentMsg
        currentMsg = lineText

ContinueLoop:
    Next i

    If Len(currentMsg) > 0 Then AddCellError errDict, rowNum, colNum, currentMsg
End Sub

Private Function IsAllowedKey0(ByVal key0 As String, Optional ByRef detailMsg As String = "") As Boolean
    Select Case UCase$(Trim$(key0))
        Case "AVV", "ASV", "HEV", "KYV", "SSV", "SKV", "HCV", "SMV"
            IsAllowedKey0 = True
        Case Else
            IsAllowedKey0 = False
            detailMsg = ValidationMessages.PlantKeyNotAccepted(key0)
    End Select
End Function

Public Function DetermineClass_ByKey12( _
    ws As Worksheet, _
    rowNum As Long, _
    valueA As String, _
    key12 As String, _
    dict2 As Object, _
    Optional ByRef detailMsg As String _
) As Boolean

    Dim foundDict2 As Boolean
    Dim regex As Object, k As Long
    Dim shortPatterns As Variant
    
    ' Opslag pï¿½ key12 hvis lï¿½ngde 2
    If Len(key12) = 2 Then
        foundDict2 = dict2.exists(key12)
    Else
        foundDict2 = False
    End If
    
    ' --- key18 mangler: dict2-match kan vï¿½re nok ---
    If foundDict2 Then
        ws.Cells(rowNum, 3).value = dict2(key12)
        HighlightValid ws.Cells(rowNum, 3)
        DetermineClass_ByKey12 = True
        Exit Function
    End If
    
    ' --- Regex-fallback: MKP/FP KUN hvis foundDict2 = True (som i din logik) ---
    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = True
    
    ' MKP (krï¿½ver foundDict2 = True)
    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FD|FG|FH|FW|FC)$"
    If regex.Test(valueA) Then
        detailMsg = ValidationMessages.EquipmentKeyNotAccepted(key12) & vbCrLf
        DetermineClass_ByKey12 = False
        Exit Function
    End If
    
    ' FP -> NO CLASS (krï¿½ver foundDict2 = True)
    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FP)$"
    If regex.Test(valueA) Then
        detailMsg = ValidationMessages.EquipmentKeyNotAccepted(key12) & vbCrLf
        DetermineClass_ByKey12 = False
        Exit Function
    End If
    
    ' --- Short patterns: sï¿½tter "NO CLASS" uden dict2-krav (som du skrev) ---
    shortPatterns = Array( _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{2}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{1}$", _
        "^[A-Z]{3}\d{2,3}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}$", _
        "^[A-Z]{3}\d{2}[\d\s][C-Z][A-Z]{2}\d{2}$" _
    )
    
    For k = LBound(shortPatterns) To UBound(shortPatterns)
        regex.pattern = shortPatterns(k)
        If regex.Test(valueA) Then
            ws.Cells(rowNum, 3).value = "NO CLASS"
            HighlightValid ws.Cells(rowNum, 3)
            DetermineClass_ByKey12 = True
            Exit Function
        End If
    Next k
    
    ' Sidste specifikke: ELF
    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-B][A-Z]{2}\d{2}$"
    If regex.Test(valueA) Then
        ws.Cells(rowNum, 3).value = "ELF"
        HighlightValid ws.Cells(rowNum, 3)
        DetermineClass_ByKey12 = True
        Exit Function
    End If
    
    ' Intet matchede
    detailMsg = ValidationMessages.ClassNotDeterminedByEquipmentKey(key12)
    DetermineClass_ByKey12 = False

End Function

Public Function DetermineClass_ByKey18( _
    ws As Worksheet, _
    rowNum As Long, _
    key18 As String, _
    key12 As String, _
    dict1 As Object, _
    dict2 As Object, _
    Optional ByRef detailMsg As String _
) As Long

    Dim foundDict1 As Boolean, foundDict2 As Boolean
    
    ' Kun relevant hvis key18 har lï¿½ngde 2
    If Len(key18) <> 2 Then
        DetermineClass_ByKey18 = -1
        Exit Function
    End If
    
    foundDict1 = dict1.exists(key18)
    foundDict2 = (Len(key12) = 2 And dict2.exists(key12))
    
    ' --- KRAV: hvis key18 findes, SKAL bï¿½de dict1 og dict2 findes ---
    If foundDict1 And foundDict2 Then
        ws.Cells(rowNum, 3).value = dict1(key18)   ' prioritet til dict1
        HighlightValid ws.Cells(rowNum, 3)
        DetermineClass_ByKey18 = 1
    Else
        detailMsg = ""
        If Not foundDict1 Then detailMsg = detailMsg & ValidationMessages.ComponentKeyNotAccepted(key18) & vbCrLf
        If Not foundDict2 Then detailMsg = detailMsg & ValidationMessages.EquipmentKeyNotAccepted(key12) & vbCrLf
        DetermineClass_ByKey18 = 0
    End If

End Function

Public Function DetermineValidFunctionKey( _
    ws As Worksheet, _
    rowNum As Long, _
    key7 As String, _
    functionKeyDict As Object, _
    Optional ByRef detailMsg As String _
) As Long

    Dim foundFunctionKey As Boolean
    
    foundFunctionKey = functionKeyDict.exists(key7)
    
    If foundFunctionKey Then
    
        DetermineValidFunctionKey = 1
    Else
        detailMsg = ""
        If Not foundFunctionKey Then detailMsg = detailMsg & ValidationMessages.FunctionKeyNotAccepted(key7) & vbCrLf
        DetermineValidFunctionKey = 0
    End If

End Function

' --- Fejlhï¿½ndtering pr. celle ---

' Tilfï¿½j fejltekst til en celle (key "row|col")
Sub AddCellError(errDict As Object, rowNum As Long, colNum As Long, msg As String)
    Dim key As String, col As Collection
    key = CStr(rowNum) & "|" & CStr(colNum)
    If Not errDict.exists(key) Then
        Set col = New Collection
        errDict.Add key, col
    End If
    errDict(key).Add msg
End Sub

' Lav multilinje tekst med punkter til note/kommentar
Function BuildErrorText(errCol As Collection) As String
    Dim k As Long, i As Long
    Dim s As String
    Dim lines() As String
    Dim lineText As String

    s = ""
    For k = 1 To errCol.count
        lines = Split(CStr(errCol(k)), vbCrLf)
        For i = LBound(lines) To UBound(lines)
            lineText = Trim$(lines(i))
            If Len(lineText) > 0 Then
                If i = LBound(lines) Then
                    s = s & ChrW(&H26A0) & " " & lineText
                Else
                    s = s & lineText
                End If
                s = s & vbCrLf
            End If
        Next i

        If Right$(s, 2) = vbCrLf Then
            s = Left$(s, Len(s) - 2)
        End If

        If k < errCol.count Then s = s & vbCrLf
    Next k
    BuildErrorText = s
End Function

Sub TransferData()
    Dim srcWorkbook As Workbook
    Dim srcSheet As Worksheet
    Dim destSheet As Worksheet
    Dim srcRow As Long
    Dim destRow As Long
    Dim sheetName As String
    Dim cellColor As Long
    Dim warningColor As Long
    Dim exists As Boolean
    Dim destCell As Range
    Dim sourceCommentText As String
    Dim startTime As Double
    Dim elapsedTime As Double
    Dim remainingTime As Double
    Dim totalRows As Long
    Dim processedRows As Long
    Dim appState As AppExecutionState
    Dim affected As Collection
    Set affected = New Collection

    On Error GoTo Fail

    CaptureAppState appState
    ApplySafeExecution disableEvents:=True, disableScreenUpdating:=True

    
    ' Sï¿½t kildearbejdsbog og ark
    Set srcWorkbook = ThisWorkbook
    Set srcSheet = srcWorkbook.Sheets("Initial Entry")
    
    ' Find total antal rï¿½kker
    totalRows = srcSheet.Cells(srcSheet.Rows.count, 1).End(xlUp).Row - 5
    
    ' Initialiser progress bar
    Progress_Show totalRows, "Transferring Initial Entry data..."
    
    startTime = Timer
    
    Worksheets("Initial Entry").CheckBoxes("Button_CREATE_AUTO_VERIFY").value = xlOff
    
    ' Start loop
    srcRow = 6
    processedRows = 0
    
    Do While srcRow <= srcSheet.Cells(srcSheet.Rows.count, 2).End(xlUp).Row
        sheetName = srcSheet.Cells(srcRow, 3).value
        If sheetName = "" Then sheetName = "NO CLASS"
        
        ' Tjek om kolonne A og B er grï¿½nne (valid)
        cellColor = RGB(144, 238, 144)
        warningColor = RGB(255, 255, 153)
        If (srcSheet.Cells(srcRow, 1).Interior.Color = cellColor Or srcSheet.Cells(srcRow, 1).Interior.Color = warningColor) And _
           srcSheet.Cells(srcRow, 2).Interior.Color = cellColor Then
           
            ' Tjek om destinationsarket findes
            On Error Resume Next
            Set destSheet = srcWorkbook.Sheets(sheetName)
            On Error GoTo 0
            
            If Not destSheet Is Nothing Then
                ' Hvis skjult, gï¿½r synligt
                If destSheet.Visible = xlSheetHidden Then destSheet.Visible = xlSheetVisible
                
                ' Tjek om KKS allerede findes i kolonne D
                exists = False
                For Each destCell In destSheet.Range("D1:D" & destSheet.Cells(destSheet.Rows.count, 4).End(xlUp).Row)
                    If destCell.value = srcSheet.Cells(srcRow, 1).value Then
                        exists = True
                        Exit For
                    End If
                Next destCell
                
                If Not exists Then
                    ' Find nï¿½ste ledige rï¿½kke i destination
                    destRow = destSheet.Cells(destSheet.Rows.count, 4).End(xlUp).Row + 1

                    sourceCommentText = GetCellCommentText(srcSheet.Cells(srcRow, 1))
                    
                    ' Kopier data
                    destSheet.Cells(destRow, 5).value = srcSheet.Cells(srcRow, 2).value ' Beskrivelse
                    destSheet.Cells(destRow, 4).value = srcSheet.Cells(srcRow, 1).value ' KKS
                    destSheet.Cells(destRow, 3).value = srcSheet.Cells(srcRow, 4).value ' Type
                    destSheet.Cells(destRow, 4).Interior.Color = srcSheet.Cells(srcRow, 1).Interior.Color

                    If Len(sourceCommentText) > 0 Then
                        Verification_Functions.AddCellComment destSheet.Cells(destRow, 4), sourceCommentText
                    End If
                    
                    
                    ' NYT: registrï¿½r den berï¿½rte klasse
                    AddUniqueClass affected, sheetName

                    
                    ' Slet rï¿½kken fra kildedata
                    srcSheet.Rows(srcRow).Delete
                    GoTo SkipIncrement
                Else
                    ' ? Brug tooltip i stedet for Errors-ark
                    HighlightError srcSheet.Cells(srcRow, 1)
                    AddCellComment srcSheet.Cells(srcRow, 1), ValidationMessages.TransferAlreadyExistsInDestination()
                    srcSheet.Cells(srcRow, 5).value = ValidationMessages.StatusErrorNotTransferred()
                End If
            Else
                ' ? Hvis destinationsark ikke findes
                HighlightError srcSheet.Cells(srcRow, 3)
                AddCellComment srcSheet.Cells(srcRow, 3), ValidationMessages.TransferDestinationSheetMissing()
                srcSheet.Cells(srcRow, 5).value = ValidationMessages.StatusErrorNotTransferred()
            End If
        Else
            ' ? Hvis rï¿½kken ikke er grï¿½n (ikke valideret)
            AddCellComment srcSheet.Cells(srcRow, 1), ValidationMessages.TransferRowNotValidated()
            srcSheet.Cells(srcRow, 5).value = ValidationMessages.StatusErrorNotTransferred()
        End If
        
        ' Nï¿½ste rï¿½kke
        srcRow = srcRow + 1
SkipIncrement:
        processedRows = processedRows + 1
        
        ' Opdater progress bar
        elapsedTime = Timer - startTime
        remainingTime = (elapsedTime / processedRows) * (totalRows - processedRows)
        Progress_Update processedRows, ValidationMessages.ProgressProcessingRow(processedRows, totalRows, remainingTime / 60)
        DoEvents
    Loop
    
    Worksheets("Initial Entry").CheckBoxes("Button_CREATE_AUTO_VERIFY").value = xlOn
    ' >>> NYT: Verificï¿½r KUN de ark, vi har skrevet til. Bypasser E2 (manuel-mode).
    VerifyAffectedClassSheets affected, respectE2:=False

    
    ' Afslut
    MsgBox ValidationMessages.TransferCompleteMessage(), vbInformation, ValidationMessages.TransferCompleteTitle()
    Progress_End ValidationMessages.ProgressDataTransferComplete()

SafeExit:
    RestoreAppState appState
    Exit Sub

Fail:
    MsgBox ValidationMessages.ErrorTransferData(Err.description), vbExclamation
    Progress_End ValidationMessages.ProgressAborted()
    Resume SafeExit

End Sub

Private Function GetCellCommentText(ByVal targetCell As Range) As String
    On Error Resume Next
    If Not targetCell.Comment Is Nothing Then
        GetCellCommentText = targetCell.Comment.text
    End If
    On Error GoTo 0
End Function


