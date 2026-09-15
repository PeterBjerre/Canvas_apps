Attribute VB_Name = "Verification_StepsConfig"
Option Explicit

Public Function GetVerifyStepsFor(ByVal Class As String) As Variant
    Dim tbl As ListObject
    Dim raw As Variant
    Dim lookupKeys As Variant
    Dim key As Variant

    Class = Trim$(Class)

    Set tbl = FindClassVerifyConfigTable()

    If Not tbl Is Nothing Then
        lookupKeys = Array(Class, "DEFAULT", "*")
        For Each key In lookupKeys
            raw = TryGetStepsFromTable(tbl, CStr(key))
            If IsArray(raw) Then
                GetVerifyStepsFor = ValidateVerifySteps(raw, Class)
                Exit Function
            End If
        Next key
    End If

    Debug.Print ValidationMessages.DebugClassVerifyConfigMissingIncomplete(Class)
    GetVerifyStepsFor = ValidateVerifySteps(LegacyDefaultStepsFor(Class), Class)
End Function

Public Sub AuditClassVerifyConfig(Optional ByVal ShowSummary As Boolean = True)
    Dim tbl As ListObject
    Dim loRow As ListRow
    Dim classKey As String
    Dim stepsText As String
    Dim raw As Variant
    Dim valid As Object
    Dim seen As Object
    Dim s As Variant
    Dim stepName As String
    Dim invalidCount As Long
    Dim duplicateCount As Long
    Dim msg As String

    Set tbl = FindClassVerifyConfigTable()
    If tbl Is Nothing Or tbl.DataBodyRange Is Nothing Then
        If ShowSummary Then MsgBox ValidationMessages.ClassVerifyConfigMissingOrEmpty(), vbExclamation, ValidationMessages.AuditClassVerifyConfigTitle()
        Exit Sub
    End If

    Set valid = GetValidVerifyStepSet()

    For Each loRow In tbl.ListRows
        classKey = Trim$(CStr(loRow.Range(1, 1).value))
        stepsText = CStr(loRow.Range(1, 2).value)
        raw = SplitSteps(stepsText)

        Set seen = CreateObject("Scripting.Dictionary")
        seen.CompareMode = vbTextCompare

        For Each s In raw
            stepName = Trim$(CStr(s))
            If Len(stepName) > 0 Then
                If Not valid.exists(stepName) Then
                    invalidCount = invalidCount + 1
                    Debug.Print ValidationMessages.DebugClassVerifyConfigInvalidStep(stepName, classKey)
                Else
                    If seen.exists(stepName) Then
                        duplicateCount = duplicateCount + 1
                        Debug.Print ValidationMessages.DebugClassVerifyConfigDuplicateStep(stepName, classKey)
                    Else
                        seen(stepName) = True
                    End If
                End If
            End If
        Next s
    Next loRow

    If ShowSummary Then
        msg = ValidationMessages.AuditClassVerifyConfigSummary(invalidCount, duplicateCount)
        MsgBox msg, IIf(invalidCount = 0 And duplicateCount = 0, vbInformation, vbExclamation), ValidationMessages.AuditClassVerifyConfigTitle()
    End If
End Sub

Private Function FindClassVerifyConfigTable() As ListObject
    Dim ws As Worksheet
    Dim tbl As ListObject

    For Each ws In ThisWorkbook.Worksheets
        On Error Resume Next
        Set tbl = ws.ListObjects("ClassVerifyConfig")
        On Error GoTo 0
        If Not tbl Is Nothing Then
            Set FindClassVerifyConfigTable = tbl
            Exit Function
        End If
    Next ws
End Function

Private Function TryGetStepsFromTable(ByVal tbl As ListObject, ByVal classKey As String) As Variant
    Dim r As Range

    If tbl Is Nothing Then Exit Function
    If tbl.DataBodyRange Is Nothing Then Exit Function

    For Each r In tbl.DataBodyRange.Rows
        If StrComp(CStr(r.Cells(1, 1).value), classKey, vbTextCompare) = 0 Then
            TryGetStepsFromTable = SplitSteps(CStr(r.Cells(1, 2).value))
            Exit Function
        End If
    Next r
End Function

Private Function SplitSteps(ByVal stepsText As String) As Variant
    Dim tmp As String

    tmp = stepsText
    tmp = Replace(tmp, vbCrLf, ",")
    tmp = Replace(tmp, vbCr, ",")
    tmp = Replace(tmp, vbLf, ",")
    tmp = Replace(tmp, ";", ",")
    tmp = Replace(tmp, "|", ",")

    Do While InStr(tmp, "  ") > 0
        tmp = Replace(tmp, "  ", " ")
    Loop

    SplitSteps = Split(tmp, ",")
End Function

Private Function ValidateVerifySteps(ByVal rawSteps As Variant, ByVal Class As String) As Variant
    Dim valid As Object
    Dim cleaned() As String
    Dim s As Variant
    Dim n As Long
    Dim stepName As String

    Set valid = GetValidVerifyStepSet()
    n = -1

    For Each s In rawSteps
        stepName = Trim$(CStr(s))
        If Len(stepName) > 0 Then
            If valid.exists(stepName) Then
                n = n + 1
                ReDim Preserve cleaned(0 To n)
                cleaned(n) = stepName
            Else
                Debug.Print ValidationMessages.DebugClassVerifyConfigInvalidStepIgnored(stepName, Class)
            End If
        End If
    Next s

    If n < 0 Then
        Debug.Print ValidationMessages.DebugNoValidVerifyStepsUsingFallback(Class)
        ValidateVerifySteps = Array("Verify_Master_Data_FL", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    Else
        ValidateVerifySteps = cleaned
    End If
End Function

Private Function GetValidVerifyStepSet() As Object
    Dim d As Object

    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    d("Verify_Master_Data_FL") = True
    d("Typekreds") = True
    d("TestMethod") = True
    d("Design_pressure_") = True
    d("Operating_pressure_") = True
    d("Design_temperature_") = True
    d("Operating_temperature_") = True
    d("Design_flow_") = True
    d("ELF") = True
    d("GIV") = True
    d("KAB") = True
    d("MAA") = True
    d("MKP") = True
    d("MKP_AC") = True
    d("MKP_FA") = True
    d("MKP_FI") = True
    d("MKP_HE") = True
    d("MKP_PI") = True
    d("MKP_PU") = True
    d("MKP_TA") = True
    d("MKP_VA") = True
    d("RBR") = True
    d("TAF") = True
    d("UNF") = True
    d("TRMNEW") = True
    d("Equipment_Numbers") = True
    d("VerifyFunctionalLocationClasses") = True
    d("KKS_Syntax") = True

    Set GetValidVerifyStepSet = d
End Function

Private Function LegacyDefaultStepsFor(ByVal Class As String) As Variant
    Dim d As Object

    Set d = CreateObject("Scripting.Dictionary")
    d.CompareMode = vbTextCompare

    d("ELF") = Array("Verify_Master_Data_FL", "ELF", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("GIV") = Array("Verify_Master_Data_FL", "GIV", "TRMNEW", "Operating_temperature_", "Operating_pressure_", "TestMethod", "Typekreds", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("KAB") = Array("Verify_Master_Data_FL", "KAB", "KKS_Syntax")
    d("MAA") = Array("Verify_Master_Data_FL", "MAA", "Design_pressure_", "Design_temperature_", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP") = Array("Verify_Master_Data_FL", "MKP", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_AC") = Array("Verify_Master_Data_FL", "MKP_AC", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_FA") = Array("Verify_Master_Data_FL", "MKP_FA", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_FI") = Array("Verify_Master_Data_FL", "MKP_FI", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_HE") = Array("Verify_Master_Data_FL", "MKP_HE", "TRMNEW", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_PI") = Array("Verify_Master_Data_FL", "MKP_PI", "TRMNEW", "Design_pressure_", "Design_temperature_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_PU") = Array("Verify_Master_Data_FL", "MKP_PU", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_TA") = Array("Verify_Master_Data_FL", "MKP_TA", "TRMNEW", "Design_pressure_", "Design_temperature_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("MKP_VA") = Array("Verify_Master_Data_FL", "MKP_VA", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("RBR") = Array("Verify_Master_Data_FL", "RBR", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("TAF") = Array("Verify_Master_Data_FL", "TAF", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("UNF") = Array("Verify_Master_Data_FL", "UNF", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("NO CLASS") = Array("TRMNEW", "Verify_Master_Data_FL", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("SIGNAL") = Array("TRMNEW", "Verify_Master_Data_FL", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    d("Equipment Numbers") = Array("Equipment_Numbers")

    If d.exists(Class) Then
        LegacyDefaultStepsFor = d(Class)
    Else
        LegacyDefaultStepsFor = Array("Verify_Master_Data_FL", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax")
    End If
End Function
