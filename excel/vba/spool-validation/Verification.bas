Attribute VB_Name = "Verification"
Option Explicit

Private Const iColumn As Long = 3
Private Const iRow As Long = 4

Public Sub ClearVarification(ByVal Class As String)

 Dim ws As Worksheet
    Dim gateCol As Long
    Dim statusCol As Long
    Set ws = ThisWorkbook.Sheets(Class)
    gateCol = Verification_Functions.GetPrimaryDataColumn(ws)

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.count, gateCol).End(xlUp).Row + 1
    If lastRow < iRow Then lastRow = iRow
    statusCol = Verification_Functions.GetStatusColumn(ws)

    Dim i As Long
    For i = iRow To lastRow
        ws.Rows(i).Interior.ColorIndex = xlNone
        
    Next i

    ws.Range(ws.Cells(iRow, statusCol), ws.Cells(lastRow, statusCol)).Clear

End Sub

Public Sub ClearVarificationRows(ByVal Class As String, ByVal changedRows As Object)
    Dim ws As Worksheet
    Dim rowKey As Variant
    Dim r As Long
    Dim gateCol As Long
    Dim statusCol As Long
    Dim gateColColor As Long

    If changedRows Is Nothing Then
        ClearVarification Class
        Exit Sub
    End If

    Set ws = ThisWorkbook.Sheets(Class)
    gateCol = Verification_Functions.GetPrimaryDataColumn(ws)
    statusCol = Verification_Functions.GetStatusColumn(ws)

    For Each rowKey In changedRows.keys
        r = CLng(rowKey)
        If r >= iRow Then
            gateColColor = ws.Cells(r, gateCol).Interior.Color
            ws.Rows(r).Interior.ColorIndex = xlNone
            ws.Cells(r, gateCol).Interior.Color = gateColColor
            ws.Cells(r, statusCol).Clear
        End If
    Next rowKey
End Sub

Public Sub Verify_Master_Data_FL(ByVal Class As String)
    Verification_MasterData.Verify_Master_Data_FL_Core Class
End Sub

Public Function IsInArray2(ByVal val As String, ByVal arr As Variant) As Boolean
    IsInArray2 = Verification_Functions.IsInArray(val, arr)
End Function

Public Sub Typekreds(ByVal Class As String) 'SAP Char K
    Verification_ClassRules.Typekreds_Core Class
End Sub

Public Sub TestMethod(ByVal Class As String) 'SAP Char K
    Verification_ClassRules.TestMethod_Core Class
End Sub

Public Sub Design_pressure_(ByVal Class As String)
    Verification_ClassBlocks.Design_pressure_Core Class
End Sub

Public Sub Operating_pressure_(ByVal Class As String)
    Verification_ClassBlocks.Operating_pressure_Core Class
End Sub

Public Sub Design_temperature_(ByVal Class As String)
    Verification_ClassBlocks.Design_temperature_Core Class
End Sub

Public Sub Operating_temperature_(ByVal Class As String)
    Verification_ClassBlocks.Operating_temperature_Core Class
End Sub

Public Sub Design_flow_(ByVal Class As String)
    Verification_ClassBlocks.Design_flow_Core Class
End Sub

Public Sub ELF(ByVal Class As String)
    Verification_ClassBlocks.ELF_Core Class
End Sub

Public Sub GIV(ByVal Class As String)
    Verification_ClassBlocks.GIV_Core Class
End Sub

Public Sub KAB(ByVal Class As String)
    Verification_ClassBlocks.KAB_Core Class
End Sub

Public Sub MAA(ByVal Class As String)
    Verification_ClassBlocks.MAA_Core Class
End Sub

Public Sub MKP(ByVal Class As String)
    Verification_ClassBlocks.MKP_Core Class
End Sub

Public Sub MKP_AC(ByVal Class As String)
    Verification_ClassBlocks.MKP_AC_Core Class
End Sub

Public Sub MKP_FA(ByVal Class As String)
    Verification_ClassBlocks.MKP_FA_Core Class
End Sub

Public Sub MKP_FI(ByVal Class As String)
    Verification_ClassBlocks.MKP_FI_Core Class
End Sub

Public Sub MKP_HE(ByVal Class As String)
    Verification_ClassBlocks.MKP_HE_Core Class
End Sub

Public Sub MKP_PI(ByVal Class As String)
    Verification_ClassBlocks.MKP_PI_Core Class
End Sub

Public Sub MKP_PU(ByVal Class As String)
    Verification_ClassBlocks.MKP_PU_Core Class
End Sub

Public Sub MKP_TA(ByVal Class As String)
    Verification_ClassBlocks.MKP_TA_Core Class
End Sub

Public Sub MKP_VA(ByVal Class As String)
    Verification_ClassBlocks.MKP_VA_Core Class
End Sub

Public Sub RBR(ByVal Class As String)
    Verification_ClassBlocks.RBR_Core Class
End Sub

Public Sub TAF(ByVal Class As String)
    Verification_ClassBlocks.TAF_Core Class
End Sub

Public Sub UNF(ByVal Class As String)
    Verification_ClassBlocks.UNF_Core Class
End Sub

Public Sub TRMNEW(ByVal Class As String)
    Verification_ClassBlocks.TRMNEW_Core Class
End Sub

Public Sub Equipment_Numbers(ByVal Class As String)
    Verification_EquipmentNumbers.Equipment_Numbers_Core Class
End Sub

Sub VerifyFunctionalLocationClasses(ByVal Class As String)
    Verification_ClassBlocks.VerifyFunctionalLocationClasses_Core Class
End Sub


'===========================
' Verification ï¿½ DATA-DREVET ORCHESTRATOR
'===========================
'Option Explicit

' Kï¿½rer alle verifikationstrin for en given Class ud fra tabel/konfig.
Public Sub VerifyByClass(ByVal Class As String)
    Dim steps As Variant, s As Variant

    On Error GoTo Fail

    ' >>> NYT: init cache pr. kï¿½rsel
    Verification_Cache.BeginRun Class

    steps = Verification_StepsConfig.GetVerifyStepsFor(Class)
    ClearVarification Class

    For Each s In steps
        s = Trim$(CStr(s))
        If Len(s) > 0 Then
            On Error Resume Next
            Application.Run "Verification." & s, Class
            If Err.Number <> 0 Then
                Debug.Print ValidationMessages.DebugVerifyStepFailed(CStr(s), Class, Err.description)
                Err.Clear
            End If
            On Error GoTo 0
        End If
    Next s

SafeExit:
    Exit Sub

Fail:
    Debug.Print ValidationMessages.DebugVerifyByClassFailed(Class, Err.description)
    Resume SafeExit
End Sub

Public Sub VerifyByClassRows(ByVal Class As String, ByVal changedRows As Object, Optional ByVal runKKSFull As Boolean = False)
    Dim steps As Variant, s As Variant

    On Error GoTo Fail

    If changedRows Is Nothing Then
        VerifyByClass Class
        Exit Sub
    End If

    If changedRows.count = 0 Then Exit Sub

    Verification_Cache.BeginRun Class
    Verification_Functions.SetScopedChangedRows changedRows
    ClearVarificationRows Class, changedRows

    steps = Verification_StepsConfig.GetVerifyStepsFor(Class)

    For Each s In steps
        s = Trim$(CStr(s))
        If Len(s) > 0 Then
            If ShouldRunScopedStep(CStr(s), runKKSFull) Then
                On Error Resume Next
                Application.Run "Verification." & s, Class
                If Err.Number <> 0 Then
                    Debug.Print ValidationMessages.DebugVerifyStepFailed(CStr(s), Class, Err.description)
                    Err.Clear
                End If
                On Error GoTo 0
            End If
        End If
    Next s

SafeExit:
    Verification_Functions.ClearScopedChangedRows
    Exit Sub

Fail:
    Debug.Print ValidationMessages.DebugVerifyByClassFailed(Class, Err.description)
    Resume SafeExit
End Sub

Private Function ShouldRunScopedStep(ByVal stepName As String, ByVal runKKSFull As Boolean) As Boolean
    Select Case UCase$(Trim$(stepName))
        Case "KKS_SYNTAX"
            ShouldRunScopedStep = True
        Case "VERIFYFUNCTIONALLOCATIONCLASSES"
            ShouldRunScopedStep = False
        Case Else
            ShouldRunScopedStep = True
    End Select
End Function

' Step-konfiguration ligger nu i Verification_StepsConfig-modulet.
'--- KKS-syntaks-kontrol for klasseark (kolonne D) ---
'  - Matcher KKS-mï¿½nstre som i Initial Entry
'  - Finder dubletter i kolonne D (rï¿½kke 4..sidste)
'  - Farver grï¿½n/rï¿½d og tilfï¿½jer kommentar ved fejl
Public Sub KKS_Syntax(ByVal Class As String)
    Verification_KKS.KKS_Syntax Class
End Sub

' --- Auto-sï¿½t / ryd TRM assignment + ABC Indic. baseret pï¿½ TRM-kolonner ---
' Sï¿½tter:
'   TRM assignment = "X", hvis mindst ï¿½n af TRM-kolonnerne har vï¿½rdi pï¿½ rï¿½kken.
'   ABC Indic.     = "A", nï¿½r TRM assignment sï¿½ttes til "X".
' Rydder:
'   TRM assignment = ""  hvis ALLE TRM-kolonner er tomme pï¿½ rï¿½kken.
'
' TRM-kolonner (sï¿½ges via header i rï¿½kke 3):
'   "EX-Marking", "Safety Critical Equipment", "Fire Classification", "Fire Sealing Type", "Fire Sealing Product"
'
' Bemï¿½rk:
'   - Vi ï¿½ndrer som standard IKKE "ABC Indic." tilbage, nï¿½r TRM assignment ryddes
'     (sig til, hvis du ogsï¿½ vil have ABC ryddet/ï¿½ndret i den situation).
Public Sub AutoSetTRMAndABC(ByVal Class As String)
    Verification_KKS.AutoSetTRMAndABC Class
End Sub

