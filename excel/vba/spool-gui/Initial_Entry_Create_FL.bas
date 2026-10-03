Attribute VB_Name = "Initial_Entry_Create_FL"
Option Explicit


Sub Create_FL()

    Sheets("Initial Entry").Select

    ' Run the GUI script
    RunGUIScript

    




End Sub

Public Sub RunGUIScript()
    Dim ws As Worksheet
    Dim headerRow As Range
    Dim colIndex As Dictionary
    Dim cell As Range
    Dim i As Long
    Dim Functional_Location As String
    Dim StrIndicator As String
    Dim Class As String
    Dim FL_Description As String
    Dim startTime As Double
    Dim elapsedTime As Double
    Dim remainingTime As Double
    Dim totalRows As Long
    Dim processedRows As Long
    Dim appState As AppExecutionState
    
    On Error GoTo myerr

    CaptureAppState appState
    ApplySafeExecution disableEvents:=True, disableScreenUpdating:=True
    
    ' Set the worksheet and activate it
    Set ws = Worksheets("Initial Entry")
    ws.Activate
    
    ' Find header row (row 5) and initialize colIndex dictionary
    Set headerRow = ws.rows(5)
    
    ' Find the total number of rows to process
    totalRows = ws.Cells(ws.rows.count, 1).End(xlUp).Row - 5
    
    ' Initialize progress bar
    Progress_Show totalRows, "Creating Functional Locations..."
    
    startTime = Timer
    
    
    i = 6
    processedRows = 0
    
    ' Loop through each row until an empty cell is found in the "Functional Location" column
    Do Until ws.Cells(i, 1).value = ""
        
        Functional_Location = ws.Cells(i, 1).value
        StrIndicator = ws.Cells(i, 4).value
        Class = ws.Cells(i, 3).value
        FL_Description = ws.Cells(i, 2).value
        
        ' Fill master data fields using the GUI script
        GUI_SCRIPT.FillMasterdataFieldsInitial Functional_Location, FL_Description, StrIndicator
        
        If Class <> "NO CLASS" And Class <> "SIGNAL" Then
            ' Navigate to class assignment section
            GUI_SCRIPT.GoToClassAssignment Class
            
            If Class = "ELF" Then
                GUI_SCRIPT.WCM "CONTROL", ""
            End If
            
            ' End class assignment and save functional location status
            GUI_SCRIPT.EndClassAssignment
        End If
        
        GUI_SCRIPT.SaveFLAndGetStatusInitial i
        
        processedRows = processedRows + 1
        
        ' Update progress bar
        elapsedTime = Timer - startTime
        remainingTime = (elapsedTime / processedRows) * (totalRows - processedRows)
        Progress_Update processedRows, ValidationMessages.ProgressProcessingRow(processedRows, totalRows, remainingTime / 60)
        
        DoEvents ' Allow the UserForm to update
        
        i = i + 1
    Loop
    
    ' End the transaction and display a message
    GUI_SCRIPT.EndTransaction
    MsgBox ValidationMessages.FunctionalLocationsCreatedUpdated(), vbOKOnly
    
    Progress_End ValidationMessages.ProgressFunctionalLocationsCreatedUpdated()
    RestoreAppState appState
    
Exit Sub

myerr:
    ' Display an error message if an error occurs
    MsgBox ValidationMessages.ErrorOccurredWhileRetrievingDataFixedSpelling(), vbCritical + vbOKOnly
    Progress_End ValidationMessages.ProgressAborted()
    RestoreAppState appState
End Sub


