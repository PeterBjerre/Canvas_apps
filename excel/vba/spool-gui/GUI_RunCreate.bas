Attribute VB_Name = "GUI_RunCreate"
Option Explicit

Public Sub RunGUIScript_Core(ByVal Class As String)
    Const MAX_ROWS_PER_RUN As Long = 50000
    Dim ws As Worksheet
    Dim headerRow As Range
    Dim colIndex As Dictionary
    Dim cell As Range
    Dim i As Long
    Dim startTime As Double
    Dim elapsedTime As Double
    Dim remainingTime As Double
    Dim totalRows As Long
    Dim processedRows As Long
    Dim appState As AppExecutionState
    Dim key As Variant
    Dim superiorFLValue As Variant

    Dim SearchKeys As Dictionary
    Dim dataFields As Dictionary
    Dim characteristicMap As Object
    Dim rowGuard As Long

    Set SearchKeys = New Dictionary
    Set dataFields = New Dictionary

    On Error GoTo myerr

    CaptureAppState appState
    ApplySafeExecution disableEvents:=True, disableScreenUpdating:=True
    ThisWorkbook.SuppressSafetyCriticalUi True

    Set ws = Worksheets(Class)
    ws.Activate

    Set headerRow = ws.rows(3)
    Set colIndex = New Dictionary

    totalRows = ws.Cells(ws.rows.count, 4).End(xlUp).Row - 3

    For Each cell In headerRow.Cells
        If Not IsEmpty(cell.value) Then
            colIndex(cell.value) = cell.Column
        End If
    Next cell

    DictionaryModule.CreateDictionaryFromTable Class, SearchKeys

    Progress_Show totalRows, "Creating/Updating Functional Locations..."

    startTime = Timer
    i = 4
    processedRows = 0

    Do Until ws.Cells(i, colIndex("Functional Location")).value = ""
        rowGuard = rowGuard + 1
        If rowGuard > MAX_ROWS_PER_RUN Then
            Err.Raise vbObjectError + 2101, "RunGUIScript_Core", "Row guard exceeded. Stopping run to prevent memory exhaustion."
        End If

        dataFields.RemoveAll

        For Each key In colIndex.keys
            dataFields(key) = ws.Cells(i, colIndex(key)).value
        Next key


        superiorFLValue = ""
        If dataFields.exists("Superior FL") Then
            superiorFLValue = dataFields("Superior FL")
        Else
            superiorFLValue = GetDictionaryValueNormalized(dataFields, "Superior FL")
        End If

        FillMasterdataFields dataFields("Functional Location"), dataFields("Description"), dataFields("Manufacturer"), dataFields("Model Number"), dataFields("Manufacturer Part Number"), dataFields("Manufacturer Serial Number"), dataFields("Room"), dataFields("ABC Indic."), dataFields("Sort Field"), dataFields("Warranty Start"), dataFields("Warranty End"), dataFields("Atex"), dataFields("Risiko"), dataFields("Asbestos"), dataFields("PTW"), dataFields("StrIndicator"), Class, superiorFLValue

        If Class <> "NO CLASS" And Class <> "SIGNAL" Then
            Set characteristicMap = CreateObject("Scripting.Dictionary")
            GoToClassAssignment Class

            If Class <> "KAB" Or Class <> "UNF" Then
                If dataFields("TRM assignment") = "X" Then
                    AddTRMClass
                End If
            End If

            If Class = "ELF" Then
                AddWCMClass
            End If

            If Class = "GIV" Then
                If dataFields("GIV_EXT assignment") = "X" Then
                    AddGIV_EXT
                End If
            End If

            EndClassAssignment

            GUI_SCRIPT.SelectCharacteristicsTab

            If dataFields("TRM assignment") = "X" Then
                AddTRMCharacteristicsToMap characteristicMap, dataFields
            End If

            If Class = "GIV" Then
                If dataFields("GIV_EXT assignment") = "X" Then
                    AddCharacteristicIfPresent characteristicMap, dataFields, "Owner"
                    AddCharacteristicIfPresent characteristicMap, dataFields, "Other Information"
                End If
            End If
            
            For Each key In SearchKeys.keys
                If dataFields(key) <> "" Then
                    characteristicMap(CStr(key)) = dataFields(key)
                End If
            Next key

            If characteristicMap.count > 0 Then
                FillCharacteristicsBatch characteristicMap
            End If


            SaveFLAndGetStatus i, Class
        Else
            If dataFields("TRM assignment") = "X" Then
                GoToClassAssignmentOnly
                AddTRMClass
                EndClassAssignment

                Set characteristicMap = CreateObject("Scripting.Dictionary")
                GUI_SCRIPT.SelectCharacteristicsTab
                AddTRMCharacteristicsToMap characteristicMap, dataFields
                If characteristicMap.count > 0 Then
                    FillCharacteristicsBatch characteristicMap
                End If
            End If
            SaveFLAndGetStatus i, Class
        End If

        processedRows = processedRows + 1

        elapsedTime = Timer - startTime
        remainingTime = (elapsedTime / processedRows) * (totalRows - processedRows)
        Progress_Update processedRows, ValidationMessages.ProgressProcessingRow(processedRows, totalRows, remainingTime / 60)

        DoEvents
        i = i + 1
    Loop

    EndTransaction
    MsgBox ValidationMessages.FunctionalLocationsCreatedUpdated(), vbOKOnly

Cleanup:
    ThisWorkbook.SuppressSafetyCriticalUi False
    Progress_End ValidationMessages.ProgressFunctionalLocationsCreatedUpdated()
    RestoreAppState appState
    Exit Sub

myerr:
    MsgBox ValidationMessages.ErrorOccurredWhileRetrievingDataFixedSpelling(), vbCritical + vbOKOnly
    Progress_End ValidationMessages.ProgressAborted()
    Resume Cleanup
End Sub

Private Function GetDictionaryValueNormalized(ByVal dataFields As Dictionary, ByVal targetKey As String) As Variant
    Dim key As Variant
    Dim normalizedTarget As String

    normalizedTarget = UCase$(Trim$(targetKey))
    GetDictionaryValueNormalized = ""

    For Each key In dataFields.keys
        If StrComp(UCase$(Trim$(CStr(key))), normalizedTarget, vbBinaryCompare) = 0 Then
            GetDictionaryValueNormalized = dataFields(key)
            Exit Function
        End If
    Next key
End Function

Private Sub AddTRMCharacteristicsToMap(ByVal characteristicMap As Object, ByVal dataFields As Dictionary)
    AddCharacteristicIfPresent characteristicMap, dataFields, "EX-Marking"
    AddCharacteristicIfPresent characteristicMap, dataFields, "Safety Critical Equipment"
    AddCharacteristicIfPresent characteristicMap, dataFields, "Fire Classification"
    AddCharacteristicIfPresent characteristicMap, dataFields, "Fire Sealing Type"
    AddCharacteristicIfPresent characteristicMap, dataFields, "Fire Sealing Product"
End Sub

Private Sub AddCharacteristicIfPresent(ByVal characteristicMap As Object, ByVal dataFields As Dictionary, ByVal fieldName As String)
    If dataFields.exists(fieldName) Then
        If CStr(dataFields(fieldName)) <> "" Then
            characteristicMap(fieldName) = dataFields(fieldName)
        End If
    End If
End Sub


