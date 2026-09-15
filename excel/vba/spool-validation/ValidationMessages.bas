Attribute VB_Name = "ValidationMessages"
Option Explicit

Public Function PlantKeyNotAccepted(ByVal key0 As String) As String
    PlantKeyNotAccepted = "'" & key0 & "' is not an accepted Plant key (allowed: AVV, ASV, HEV, KYV, SSV, SKV, HCV, SMV)"
End Function

Public Function EquipmentKeyNotAccepted(ByVal key12 As String) As String
    EquipmentKeyNotAccepted = "'" & key12 & "' is not an accepted Equipment key"
End Function

Public Function ComponentKeyNotAccepted(ByVal key18 As String) As String
    ComponentKeyNotAccepted = "'" & key18 & "' is not an accepted Component key"
End Function

Public Function FunctionKeyNotAccepted(ByVal key7 As String) As String
    FunctionKeyNotAccepted = "'" & key7 & "' is not an accepted Function key"
End Function

Public Function FunctionKeyMustStartWithUForAggregateKey(ByVal key12 As String, ByVal key7 As String) As String
    FunctionKeyMustStartWithUForAggregateKey = "Function key '" & key7 & "' must start with 'U' when Aggregate key is '" & key12 & "'"
End Function

Public Function NoKey17RulesConfiguredForAggregateKey(ByVal key12 As String) As String
    NoKey17RulesConfiguredForAggregateKey = "No BR18 Related key rules configured for Aggregate key '" & key12 & "'"
End Function

Public Function Key17NotAcceptedForAggregateKey(ByVal key12 As String, ByVal key17 As String, ByVal allowedValues As String) As String
    Dim allowedLines As String

    allowedLines = Replace(allowedValues, ", ", vbCrLf)
    Key17NotAcceptedForAggregateKey = "Accepted BR18 Related key for Aggregate key '" & key12 & "' is missing or incorrect" & vbCrLf & "Allowed:" & vbCrLf & allowedLines
End Function

Public Function MKPBR18FieldRequired(ByVal fieldName As String, ByVal key17 As String) As String
    MKPBR18FieldRequired = "'" & fieldName & "' is required for BR18-defined Functional Locations (BR18 Related key = '" & key17 & "')"
End Function

Public Function ClassNotDeterminedByEquipmentKey(ByVal key12 As String) As String
    ClassNotDeterminedByEquipmentKey = "Class not determined: " & EquipmentKeyNotAccepted(key12)
End Function

Public Function DuplicateKKSCode() As String
    DuplicateKKSCode = "Duplicate KKS-code"
End Function

Public Function DuplicateKKSSyntaxCode() As String
    DuplicateKKSSyntaxCode = "Duplicate KKS code"
End Function

Public Function InvalidKKSCode() As String
    InvalidKKSCode = "Invalid KKS code"
End Function

Public Function InvalidKKSSyntax() As String
    InvalidKKSSyntax = "Invalid KKS syntax"
End Function

Public Function KKSIsEmpty() As String
    KKSIsEmpty = "KKS is empty"
End Function

Public Function DescriptionIsEmpty() As String
    DescriptionIsEmpty = "Description is empty"
End Function

Public Function NoClassDetermined() As String
    NoClassDetermined = "No class determined"
End Function

Public Function StatusErrorNotReadyForSAP() As String
    StatusErrorNotReadyForSAP = "Error, not ready for SAP"
End Function

Public Function StatusReadyForSAP() As String
    StatusReadyForSAP = "Ready for SAP"
End Function

Public Function HeaderColumnNotFound(ByVal headerName As String) As String
    HeaderColumnNotFound = CStr(headerName) & " column not found in header row"
End Function

Public Function HeaderColumnNotFoundInRow(ByVal headerName As String, ByVal rowNumber As Long) As String
    HeaderColumnNotFoundInRow = CStr(headerName) & " column not found in row " & CStr(rowNumber)
End Function

Public Function DictionarySheetNotFound() As String
    DictionarySheetNotFound = "Sheet 'DictionaryTable' was not found."
End Function

Public Function DictionaryTableNotFound(ByVal tableName As String) As String
    DictionaryTableNotFound = "Table '" & tableName & "' was not found on sheet 'DictionaryTable'."
End Function

Public Function TransferAlreadyExistsInDestination() As String
    TransferAlreadyExistsInDestination = "Already exists in destination sheet"
End Function

Public Function TransferDestinationSheetMissing() As String
    TransferDestinationSheetMissing = "Destination sheet does not exist"
End Function

Public Function TransferRowNotValidated() As String
    TransferRowNotValidated = "Row not validated (column A must be green or yellow, and column B must be green)"
End Function

Public Function LegacyNumberingOnlyAcceptedIfExistingInPlant() As String
    LegacyNumberingOnlyAcceptedIfExistingInPlant = "This format is only accepted if the Functional Location is already numbered this way in our plant."
End Function

Public Function InvalidDateValueNotRealDate() As String
    InvalidDateValueNotRealDate = "Invalid date value (not a real date)"
End Function

Public Function InvalidDateFormatUseDDMMYYYY() As String
    InvalidDateFormatUseDDMMYYYY = "Invalid date format. Use dd.mm.yyyy"
End Function

Public Function DescriptionRequiredMaxChars(ByVal maxLen As Long) As String
    DescriptionRequiredMaxChars = "Description is required and max " & CStr(maxLen) & " chars"
End Function

Public Function MaxLengthChars(ByVal maxLen As Long) As String
    MaxLengthChars = "Max length is " & CStr(maxLen) & " chars"
End Function

Public Function AllowedValuesList(ByVal allowedValues As Variant) As String
    AllowedValuesList = "Allowed values: " & JoinAllowedValues(allowedValues, ", ")
End Function

Public Function InvalidTypekredsValue(ByVal value As String) As String
    InvalidTypekredsValue = "Invalid value: '" & value & "'. Must be a Typekreds selected from the cell dropdown."
End Function

Public Function InvalidTestMethodValue(ByVal value As String) As String
    InvalidTestMethodValue = "Invalid value: '" & value & "'. Must be a Test method selected from the cell dropdown."
End Function

Public Function ErrorOccurredWhileRetrievingData() As String
    ErrorOccurredWhileRetrievingData = "Error occurred while retrieving data"
End Function

Public Function ErrorOccurredWhileRetrievingDataFixedSpelling() As String
    ErrorOccurredWhileRetrievingDataFixedSpelling = "Error occurred while retrieving data"
End Function

Public Function ErrorOccurredWhileExtractingData() As String
    ErrorOccurredWhileExtractingData = "Error occurred while extracting data"
End Function

Public Function ErrorExtractingCharacteristic(ByVal searchText As String) As String
    ErrorExtractingCharacteristic = "Error extracting characteristic: " & searchText
End Function

Public Function SapSessionCouldNotBeAttached() As String
    SapSessionCouldNotBeAttached = "SAP session could not be attached."
End Function

Public Function DataExtractionCompleted() As String
    DataExtractionCompleted = "Data extraction completed"
End Function

Public Function ErrorOccurredDuringDataExtraction() As String
    ErrorOccurredDuringDataExtraction = "Error occurred during data extraction"
End Function

Public Function ErrorVerifyInputsAndClassDeterminationNew(ByVal errDescription As String) As String
    ErrorVerifyInputsAndClassDeterminationNew = "Error in VerifyInputsAndClassDeterminationNew: " & errDescription
End Function

Public Function TransferCompleteMessage() As String
    TransferCompleteMessage = "Data transfer complete!" & vbCrLf & "Hover over cells for error details."
End Function

Public Function TransferCompleteTitle() As String
    TransferCompleteTitle = "Transfer Complete"
End Function

Public Function ErrorTransferData(ByVal errDescription As String) As String
    ErrorTransferData = "Error in TransferData: " & errDescription
End Function

Public Function MaterialPathExceedsLimit() As String
    MaterialPathExceedsLimit = "The file path exceeds 128 characters"
End Function

Public Function FlBomNoRowsFound() As String
    FlBomNoRowsFound = "No rows found (starting from row 6)."
End Function

Public Function FlBomCreatedGrouped() As String
    FlBomCreatedGrouped = "FL BOMs created per KKS (multiple materials per BOM)"
End Function

Public Function ErrorCreateFlBomGroupedArr(ByVal errNumber As Long, ByVal errDescription As String) As String
    ErrorCreateFlBomGroupedArr = "Error in CreateFLBOM_Grouped_Arr: " & CStr(errNumber) & " - " & errDescription
End Function

Public Function DocumentsAttachedInSap() As String
    DocumentsAttachedInSap = "Documents Attached in SAP"
End Function

Public Function TableNotFound(ByVal tableName As String) As String
    TableNotFound = "The table '" & tableName & "' was not found."
End Function

Public Function ClassVerifyConfigMissingOrEmpty() As String
    ClassVerifyConfigMissingOrEmpty = "ClassVerifyConfig is missing or empty."
End Function

Public Function AuditClassVerifyConfigTitle() As String
    AuditClassVerifyConfigTitle = "AuditClassVerifyConfig"
End Function

Public Function NegativeTestcasesCreated() As String
    NegativeTestcasesCreated = "Negative test cases were created in ClassVerifyConfig (__TEST_MIXED, __TEST_ONLY_INVALID)."
End Function

Public Function ClassVerifyConfigCannotBeCreatedOrFound() As String
    ClassVerifyConfigCannotBeCreatedOrFound = "ClassVerifyConfig could not be created or found."
End Function

Public Function ErrorCreateDictionaryFromTable(ByVal errDescription As String) As String
    ErrorCreateDictionaryFromTable = "CreateDictionaryFromTable failed: " & errDescription
End Function

Public Function CannotFindFreeAreaForClassVerifyConfig() As String
    CannotFindFreeAreaForClassVerifyConfig = "Could not find a free area for the ClassVerifyConfig table."
End Function

Public Function ClassVerifyConfigTableReady(ByVal addressText As String) As String
    ClassVerifyConfigTableReady = "ClassVerifyConfig table is ready on the 'DictionaryTable' sheet in the range " & addressText
End Function

Public Function GuiElementsExtractionFinished() As String
    GuiElementsExtractionFinished = "Finished extracting GUI elements from all windows."
End Function

Public Function FunctionalLocationsCreatedUpdated() As String
    FunctionalLocationsCreatedUpdated = "Functional Locations Created/Updated"
End Function

Public Function SapGuiNotRunning() As String
    SapGuiNotRunning = "SAP GUI is not running. Please check SAP Logon path."
End Function

Public Function SapAutoLoginFailed(ByVal errDescription As String) As String
    SapAutoLoginFailed = "SAP auto-login failed: " & errDescription
End Function

Public Function NoActiveSessionToSystem(ByVal systemId As String) As String
    NoActiveSessionToSystem = "No active session to system " & systemId & ", or scripting is not enabled."
End Function

Public Function AttachSessionFailed(ByVal errDescription As String) As String
    AttachSessionFailed = "Attach session failed: " & errDescription
End Function

Public Function ErrorMaterialer(ByVal errDescription As String) As String
    ErrorMaterialer = "Error in Materialer: " & errDescription
End Function

Public Function PurchaseOrderTextColumnMissing() As String
    PurchaseOrderTextColumnMissing = "The column 'Purchase order text' was not found in row 3 on the 'Material Upload Template' sheet."
End Function

Public Function ErrorRemoveDuplicates(ByVal errDescription As String) As String
    ErrorRemoveDuplicates = "Error in RemoveDuplicates: " & errDescription
End Function

Public Function SheetNotFound(ByVal sheetName As String) As String
    SheetNotFound = "The sheet '" & sheetName & "' was not found."
End Function

Public Function MissingClassesInColumnQ() As String
    MissingClassesInColumnQ = "Missing classes in column Q"
End Function

Public Function SaveOriginalFileFirst() As String
    SaveOriginalFileFirst = "Please save the original file first."
End Function

Public Function SheetSavedAs(ByVal fileName As String) As String
    SheetSavedAs = "The sheet was saved as: " & fileName
End Function

Public Function ErrorGemMaterialUploadSomNyFil(ByVal errDescription As String) As String
    ErrorGemMaterialUploadSomNyFil = "Error in GemMaterialUploadSomNyFil: " & errDescription
End Function

Public Function ErrorInsertingSapData() As String
    ErrorInsertingSapData = "An error occurred while inserting SAP data."
End Function

Public Function ErrorFlytDataDrawingList(ByVal errDescription As String) As String
    ErrorFlytDataDrawingList = "Error in FlytDataDrawingList: " & errDescription
End Function

Public Function ErrorFlytDataFlBom(ByVal errDescription As String) As String
    ErrorFlytDataFlBom = "Error in FlytDataFLBOM: " & errDescription
End Function

Public Function MissingColumnsInDestinationSheet() As String
    MissingColumnsInDestinationSheet = "One or more columns are missing in the destination sheet. Check row 3 for correct column names."
End Function

Public Function ErrorFlytData(ByVal errDescription As String) As String
    ErrorFlytData = "Error in FlytData: " & errDescription
End Function

Public Function OnlyRunsOnDrawingListSheet() As String
    OnlyRunsOnDrawingListSheet = "Will only run on Sheet: 'Drawing List!'"
End Function

Public Function WrongSheetTitle() As String
    WrongSheetTitle = "Wrong sheet!"
End Function

Public Function ErrorCreateMdocXml(ByVal errDescription As String) As String
    ErrorCreateMdocXml = "Error in CreateMdocXML: " & errDescription
End Function

Public Function NoFolderChosenFileNotSaved() As String
    NoFolderChosenFileNotSaved = "No folder selected. The file was not saved."
End Function

Public Function TestMessageBody() As String
    TestMessageBody = "Message"
End Function

Public Function TestMessageTitle() As String
    TestMessageTitle = "Title"
End Function

Public Function ErrorUnderVerify(ByVal errDescription As String) As String
    ErrorUnderVerify = "Error during Verify: " & errDescription
End Function

Public Function NotAClassSheet() As String
    NotAClassSheet = "This sheet is not a class sheet."
End Function

Public Function CouldNotRunVerify(ByVal errDescription As String) As String
    CouldNotRunVerify = "Could not run Verify: " & errDescription
End Function

Public Function CouldNotEnsureEquipmentSheet(ByVal errDescription As String) As String
    CouldNotEnsureEquipmentSheet = "Could not ensure Equipment Numbers sheet: " & errDescription
End Function

Public Function EquipmentCreatePlaceholder() As String
    EquipmentCreatePlaceholder = "Create Equipment is not implemented yet. This button is reserved for phase 2."
End Function

Public Function InvalidUnitMessage(ByVal allowedValues As Variant) As String
    InvalidUnitMessage = "Must be one of the following: " & vbCrLf & JoinAllowedValues(allowedValues, vbCrLf)
End Function

Private Function JoinAllowedValues(ByVal allowedValues As Variant, ByVal separator As String) As String
    Dim parts() As String
    Dim idx As Long
    Dim v As Variant

    If IsObject(allowedValues) Then
        Select Case TypeName(allowedValues)
            Case "Collection"
                If allowedValues.count = 0 Then Exit Function
                ReDim parts(0 To allowedValues.count - 1)
                idx = 0
                For Each v In allowedValues
                    parts(idx) = CStr(v)
                    idx = idx + 1
                Next v
                JoinAllowedValues = Join(parts, separator)
                Exit Function

            Case "Dictionary"
                If allowedValues.count = 0 Then Exit Function
                ReDim parts(0 To allowedValues.count - 1)
                idx = 0
                For Each v In allowedValues.keys
                    parts(idx) = CStr(v)
                    idx = idx + 1
                Next v
                JoinAllowedValues = Join(parts, separator)
                Exit Function

            Case Else
                JoinAllowedValues = CStr(allowedValues)
                Exit Function
        End Select
    End If

    If IsArray(allowedValues) Then
        If (LBound(allowedValues) > UBound(allowedValues)) Then Exit Function
        ReDim parts(0 To UBound(allowedValues) - LBound(allowedValues))
        idx = 0
        For Each v In allowedValues
            parts(idx) = CStr(v)
            idx = idx + 1
        Next v
        JoinAllowedValues = Join(parts, separator)
        Exit Function
    End If

    If IsError(allowedValues) Then Exit Function
    If IsNull(allowedValues) Then Exit Function
    If Len(Trim$(CStr(allowedValues))) = 0 Then Exit Function

    JoinAllowedValues = CStr(allowedValues)
End Function

Public Function FormatDescription(ByVal pattern As String) As String
    Select Case pattern
        Case ".*"
            FormatDescription = "Free text allowed"
        Case "^[0-9,]*$"
            FormatDescription = "Valid characters: 0ï¿½9 and comma (,)"
        Case "^[a-zA-Z0-9,.]*$"
            FormatDescription = "Valid characters: Aï¿½Z, 0ï¿½9, comma (,), period (.)"
        Case "^[0-9.,\-\/\+]*$"
            FormatDescription = "Valid characters: 0ï¿½9, period (.), comma (,), hyphen (-), slash (/), plus (+)"
        Case Else
            FormatDescription = "A specific input format is required"
    End Select
End Function

Public Function DetailedFormatErrorMsg( _
    ByVal maxLen As Long, _
    ByVal formatDesc As String, _
    Optional ByVal lengthOk As Boolean = True, _
    Optional ByVal formatOk As Boolean = True _
) As String
    Dim msg As String
    msg = "Error" & vbCrLf & "Rules:" & vbCrLf

    If Not lengthOk Then
        msg = msg & ChrW(&H26A0) & " Maximum length: " & maxLen & " characters" & vbCrLf
    Else
        msg = msg & ChrW(&H2714) & " Maximum length: " & maxLen & " characters" & vbCrLf
    End If

    If Not formatOk Then
        msg = msg & ChrW(&H26A0) & " Format: " & formatDesc & vbCrLf
    Else
        msg = msg & ChrW(&H2714) & " Format: " & formatDesc & vbCrLf
    End If

    DetailedFormatErrorMsg = msg
End Function

Public Function ValidationForHeader(ByVal header As String) As String
    ValidationForHeader = "Validation for '" & header & "':"
End Function

Public Function RequiredValueMissingLine() As String
    RequiredValueMissingLine = ChrW(&H26A0) & " Required: value is missing"
End Function

Public Function MaxLengthOkLine(ByVal maxLen As Long) As String
    MaxLengthOkLine = ChrW(&H2714) & " Max length: " & maxLen & " characters"
End Function

Public Function MaxLengthExceededLine(ByVal valueLen As Long, ByVal maxLen As Long) As String
    MaxLengthExceededLine = ChrW(&H26A0) & " Max length exceeded (" & valueLen & "/" & maxLen & ")"
End Function

Public Function FormatOkLine(ByVal formatDesc As String) As String
    FormatOkLine = ChrW(&H2714) & " Format: " & formatDesc
End Function

Public Function FormatInvalidLine(ByVal formatDesc As String) As String
    FormatInvalidLine = ChrW(&H26A0) & " Format: " & formatDesc
End Function

Public Function ErrorInLineStatus() As String
    ErrorInLineStatus = "Error in line"
End Function

Public Function StatusErrorNotTransferred() As String
    StatusErrorNotTransferred = "Error, not transferred"
End Function

Public Function ProgressDataTransferComplete() As String
    ProgressDataTransferComplete = "Data transfer complete"
End Function

Public Function ProgressAborted() As String
    ProgressAborted = "Aborted"
End Function

Public Function ProgressDataExtractionCompleted() As String
    ProgressDataExtractionCompleted = "Data extraction completed"
End Function

Public Function ProgressFunctionalLocationsCreatedUpdated() As String
    ProgressFunctionalLocationsCreatedUpdated = "Functional Locations Created/Updated"
End Function

Public Function ProgressProcessingRow(ByVal processedRows As Long, ByVal totalRows As Long, ByVal remainingMinutes As Double) As String
    ProgressProcessingRow = "Processing row " & processedRows & " of " & totalRows & "." & vbCrLf & "Estimated time remaining: " & Format(remainingMinutes, "0.0") & " minutes."
End Function

Public Function ProgressExtractingRow(ByVal processedRows As Long, ByVal totalRows As Long, ByVal remainingMinutes As Double) As String
    ProgressExtractingRow = "Extracting row " & processedRows & " of " & totalRows & "." & vbCrLf & "Estimated time remaining: " & Format(remainingMinutes, "0.0") & " minutes."
End Function

Public Function VerifyStatusNoAffectedClassSheets() As String
    VerifyStatusNoAffectedClassSheets = "Verify: No affected class sheets."
End Function

Public Function VerifyStatusProgress(ByVal ClassName As String, ByVal current As Long, ByVal total As Long) As String
    VerifyStatusProgress = "Verify: " & ClassName & " (" & current & "/" & total & ")"
End Function

Public Function VerifyStatusDone() As String
    VerifyStatusDone = "Verify: done."
End Function

Public Function VerifyStatusNoData() As String
    VerifyStatusNoData = "Verify: no data to validate."
End Function

Public Function DebugVerifyStepFailed(ByVal stepName As String, ByVal ClassName As String, ByVal errDescription As String) As String
    DebugVerifyStepFailed = "Verify step FAILED: " & stepName & " (" & ClassName & "): " & errDescription
End Function

Public Function DebugVerifyByClassFailed(ByVal ClassName As String, ByVal errDescription As String) As String
    DebugVerifyByClassFailed = "VerifyByClass failed (" & ClassName & "): " & errDescription
End Function

Public Function DebugRunClassUploadFailed(ByVal ClassName As String, ByVal errDescription As String) As String
    DebugRunClassUploadFailed = "RunClassUpload failed for class " & ClassName & ": " & errDescription
End Function

Public Function DebugProgressShowFailed(ByVal errDescription As String) As String
    DebugProgressShowFailed = "Progress_Show failed: " & errDescription
End Function

Public Function DebugProgressEndFailed(ByVal errDescription As String) As String
    DebugProgressEndFailed = "Progress_End failed: " & errDescription
End Function

Public Function DebugClassVerifyConfigMissingIncomplete(ByVal ClassName As String) As String
    DebugClassVerifyConfigMissingIncomplete = "ClassVerifyConfig missing/incomplete for class: " & ClassName & ". Using legacy fallback."
End Function

Public Function DebugClassVerifyConfigInvalidStep(ByVal stepName As String, ByVal ClassName As String) As String
    DebugClassVerifyConfigInvalidStep = "ClassVerifyConfig INVALID step: " & stepName & " (class=" & ClassName & ")"
End Function

Public Function DebugClassVerifyConfigDuplicateStep(ByVal stepName As String, ByVal ClassName As String) As String
    DebugClassVerifyConfigDuplicateStep = "ClassVerifyConfig DUPLICATE step: " & stepName & " (class=" & ClassName & ")"
End Function

Public Function DebugClassVerifyConfigInvalidStepIgnored(ByVal stepName As String, ByVal ClassName As String) As String
    DebugClassVerifyConfigInvalidStepIgnored = "ClassVerifyConfig invalid step ignored: " & stepName & " (class=" & ClassName & ")"
End Function

Public Function DebugNoValidVerifyStepsUsingFallback(ByVal ClassName As String) As String
    DebugNoValidVerifyStepsUsingFallback = "No valid verify steps for class " & ClassName & ". Using minimal fallback."
End Function

Public Function AuditClassVerifyConfigSummary(ByVal invalidCount As Long, ByVal duplicateCount As Long) As String
    AuditClassVerifyConfigSummary = "AuditClassVerifyConfig" & vbCrLf & _
        "Invalid steps: " & invalidCount & vbCrLf & _
        "Duplicate steps: " & duplicateCount & vbCrLf & _
    "Details are written in the Immediate Window (Debug.Print)."
End Function

Public Function StatusSub(ByVal subName As String) As String
    StatusSub = "Sub " & subName & "()"
End Function

Public Function StatusPercentComplete() As String
    StatusPercentComplete = "100%"
End Function

Public Function StatusSavingXmlFile() As String
    StatusSavingXmlFile = "Saving XML file..."
End Function

Public Function DebugCreateMdocXmlStarted(ByVal timeValue As String) As String
    DebugCreateMdocXmlStarted = "Sub CreateMdocXML() Started:" & timeValue
End Function

Public Function DebugArrayLabel(ByVal labelText As String) As String
    DebugArrayLabel = labelText & ":"
End Function

Public Function DebugExtraDocumentDetailsHeader() As String
    DebugExtraDocumentDetailsHeader = "Extra - document details:"
End Function

Public Function DebugDocumentNumberNotFound() As String
    DebugDocumentNumberNotFound = "DOKUMENTNR is not found!!!"
End Function

Public Function DebugContinuesWithoutQualitycheck() As String
    DebugContinuesWithoutQualitycheck = "Continues without qualitycheck"
End Function

Public Function DebugFieldMissingInDataHeaders(ByVal fieldName As String) As String
    DebugFieldMissingInDataHeaders = "'" & fieldName & "' is not in the data-list headers"
End Function

Public Function DebugCharacteristicCacheInvalidated(ByVal scope As String, ByVal reason As String) As String
    DebugCharacteristicCacheInvalidated = "Characteristic cache invalidated [" & scope & "]: " & reason
End Function

Public Function DebugCharacteristicCacheMiss(ByVal mode As String, ByVal reason As String, ByVal cacheKey As String) As String
    DebugCharacteristicCacheMiss = "Characteristic cache miss [" & mode & "] reason=" & reason & " key=" & cacheKey
End Function

Public Function DebugCharacteristicNotFoundOnClassScreen(ByVal characteristicName As String) As String
    DebugCharacteristicNotFoundOnClassScreen = "Characteristic not found on class screen: " & characteristicName
End Function

Public Function DebugFieldCannotBeWrittenToXml() As String
    DebugFieldCannotBeWrittenToXml = "and therefore cannot be written to the XML-file!"
End Function

Public Function SaveXmlFolderPickerTitle() As String
    SaveXmlFolderPickerTitle = "Select folder to save the XML file"
End Function

Public Function XmlFileSavedPrompt(ByVal fullPath As String) As String
    XmlFileSavedPrompt = "The XML file was saved as:" & vbCrLf & fullPath & vbCrLf & vbCrLf & "Do you want to open the folder?"
End Function

Public Function XmlFileSavedTitle() As String
    XmlFileSavedTitle = "File saved"
End Function

Public Function TransferLogHeader() As String
    TransferLogHeader = "Data transfer log:" & vbCrLf & vbCrLf
End Function

Public Function TransferCompletedTitle() As String
    TransferCompletedTitle = "Transfer completed"
End Function

Public Function TransferRowsCopied(ByVal sheetName As String, ByVal rowsCopied As Long) As String
    TransferRowsCopied = sheetName & ": " & rowsCopied & " rows copied."
End Function

Public Function TransferRowsDeletedEmptyFile(ByVal rowsDeleted As Long) As String
    TransferRowsDeletedEmptyFile = rowsDeleted & " rows removed due to empty 'FILE' value."
End Function

Public Function TransferRowsRetainedTotal(ByVal rowsRetained As Long) As String
    TransferRowsRetainedTotal = "Total retained rows: " & rowsRetained
End Function

Public Function TransferUnknownFileTypesFound() As String
    TransferUnknownFileTypesFound = "Unknown file types found:"
End Function

Public Function TransferAllFileTypesRecognized() As String
    TransferAllFileTypesRecognized = "All file types were recognized."
End Function

