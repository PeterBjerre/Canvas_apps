Attribute VB_Name = "GUI_SCRIPT"
Option Explicit

Public SapGuiAuto As Object
Public WScript As Object
Public msgcol As Variant
Public objGui  As GuiApplication
Public objConn As GuiConnection
Public objSess As GuiSession
Public objSBar As GuiStatusbar
Public objSheet As Worksheet
Public W_System As String
Const iRow = 4
Private Const CHARACTERISTIC_CONTAINER_ID As String = "wnd[0]/usr/tabsTABSTRIP/tabpT\06/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1090/subSUB_1090A:SAPLCTMS:5110/sub:SAPLCTMS:5110"
Private Const CHARACTERISTIC_NEXT_BUTTON_ID As String = "wnd[0]/usr/tabsTABSTRIP/tabpT\06/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1090/subSUB_1090A:SAPLCTMS:5110/btnOES_PDOWN"
Private Const CHARACTERISTIC_MODE_WRITE_NORMAL As String = "WriteNormal"
Private Const CHARACTERISTIC_MODE_WRITE_SPECIAL As String = "WriteSpecialPopup"
Private Const CHARACTERISTIC_MODE_EXTRACT As String = "Extract"
Private Const CHARACTERISTIC_SCOPE_FULL As String = "FULL"
Private Const CHARACTERISTIC_SCOPE_TAB As String = "TAB_SCOPE"
Private Const CHARACTERISTIC_SCOPE_PAGE As String = "PAGE_SCOPE"
Private Const CHARACTERISTIC_CACHE_LOG_VERBOSE As Boolean = False
Private Const CHARACTERISTIC_CACHE_LOG_GUARD_FAILURES As Boolean = True

Private mCharacteristicMetadataCache As Object
Private mCharacteristicCacheEpoch As Long

Public Sub SAP_AutoLogin()
    GUI_Session.SAP_AutoLogin_Core
End Sub

Private Sub EnsureCharacteristicCache()
    If mCharacteristicMetadataCache Is Nothing Then
        Set mCharacteristicMetadataCache = CreateObject("Scripting.Dictionary")
    End If
End Sub

Private Sub BeginCharacteristicCacheRowScope()
    EnsureCharacteristicCache
    mCharacteristicMetadataCache.RemoveAll
    mCharacteristicCacheEpoch = mCharacteristicCacheEpoch + 1
End Sub

Private Sub InvalidateCharacteristicCache(ByVal scope As String, ByVal reason As String)
    EnsureCharacteristicCache

    Select Case UCase$(scope)
        Case CHARACTERISTIC_SCOPE_FULL, CHARACTERISTIC_SCOPE_TAB, CHARACTERISTIC_SCOPE_PAGE
            mCharacteristicMetadataCache.RemoveAll
        Case Else
            mCharacteristicMetadataCache.RemoveAll
    End Select

    mCharacteristicCacheEpoch = mCharacteristicCacheEpoch + 1
    If CHARACTERISTIC_CACHE_LOG_VERBOSE And Len(reason) > 0 Then
        Debug.Print ValidationMessages.DebugCharacteristicCacheInvalidated(scope, reason)
    End If
End Sub

Private Function BuildCharacteristicCacheKey(ByVal mode As String, ByVal objContainer As Object) As String
    Dim sessionId As String
    Dim flId As String
    Dim classSignature As String
    Dim tabId As String
    Dim pageAnchor As String

    sessionId = GetSessionIdentity()
    flId = GetActiveFunctionalLocation()
    classSignature = GetCurrentClassSignature()
    tabId = CHARACTERISTIC_CONTAINER_ID
    pageAnchor = GetPageAnchor(objContainer)

    BuildCharacteristicCacheKey = sessionId & "|" & flId & "|" & classSignature & "|" & tabId & "|" & pageAnchor & "|" & mode & "|" & CStr(mCharacteristicCacheEpoch)
End Function

Private Function GetSessionIdentity() As String
    On Error Resume Next
    GetSessionIdentity = CStr(objSess.ID)
    If Len(GetSessionIdentity) = 0 Then
        GetSessionIdentity = CStr(objSess.Info.SystemName) & ":" & CStr(objSess.Info.Client) & ":" & CStr(objSess.Info.User)
    End If
    On Error GoTo 0
End Function

Private Function GetActiveFunctionalLocation() As String
    GetActiveFunctionalLocation = GetSapFieldText("wnd[0]/usr/ctxtIFLO-TPLNR")

    If Len(GetActiveFunctionalLocation) = 0 Then
        GetActiveFunctionalLocation = GetSapFieldText("wnd[0]/usr/txtIFLOS-STRNO")
    End If
End Function

Private Function GetSapFieldText(ByVal fieldId As String) As String
    Dim ctrl As Object

    On Error Resume Next
    Set ctrl = objSess.FindById(fieldId)
    On Error GoTo 0

    If Not ctrl Is Nothing Then
        On Error Resume Next
        GetSapFieldText = Trim(CStr(ctrl.text))
        On Error GoTo 0
    End If
End Function

Private Function GetCurrentClassSignature() As String
    Dim primaryClass As String
    Dim classValues As Collection
    Dim i As Long
    Dim classValue As String

    Set classValues = New Collection
    primaryClass = GetSapFieldText("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1020/txtITOBATTR-KLASSE")
    If Len(primaryClass) > 0 Then
        classValues.Add primaryClass
    End If

    For i = 0 To 20
        classValue = GetSapFieldText("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0," & CStr(i) & "]")
        If Len(classValue) > 0 Then
            AddUniqueText classValues, classValue
        End If
    Next i

    GetCurrentClassSignature = JoinSortedCollection(classValues)
End Function

Private Sub AddUniqueText(ByVal values As Collection, ByVal valueText As String)
    Dim item As Variant

    For Each item In values
        If StrComp(CStr(item), valueText, vbTextCompare) = 0 Then Exit Sub
    Next item

    values.Add valueText
End Sub

Private Function JoinSortedCollection(ByVal values As Collection) As String
    Dim arr() As String
    Dim i As Long
    Dim j As Long
    Dim tmp As String

    If values Is Nothing Then Exit Function
    If values.count = 0 Then Exit Function

    ReDim arr(1 To values.count)
    For i = 1 To values.count
        arr(i) = CStr(values(i))
    Next i

    For i = 1 To UBound(arr) - 1
        For j = i + 1 To UBound(arr)
            If StrComp(arr(i), arr(j), vbTextCompare) > 0 Then
                tmp = arr(i)
                arr(i) = arr(j)
                arr(j) = tmp
            End If
        Next j
    Next i

    JoinSortedCollection = Join(arr, ",")
End Function

Private Function GetPageAnchor(ByVal objContainer As Object) As String
    Dim firstKey As String
    Dim childCount As Long

    firstKey = GetFirstVisibleCharacteristicKey(objContainer)

    On Error Resume Next
    childCount = CLng(objContainer.Children.count)
    On Error GoTo 0

    GetPageAnchor = firstKey & "#" & CStr(childCount)
End Function

Private Function BuildCharacteristicPageMetadata(ByVal objContainer As Object) As Object
    Dim metadata As Object
    Dim keysCol As Collection
    Dim keyIndexesCol As Collection
    Dim mwertControls As Collection
    Dim mwertIndexesCol As Collection
    Dim objChild As Object

    Set metadata = CreateObject("Scripting.Dictionary")
    Set keysCol = New Collection
    Set keyIndexesCol = New Collection
    Set mwertControls = New Collection
    Set mwertIndexesCol = New Collection

    For Each objChild In objContainer.Children
        If InStr(objChild.ID, "MNAME") > 0 Then
            keysCol.Add Trim(CStr(objChild.text))
            keyIndexesCol.Add CLng(GetIndexFromID(CStr(objChild.ID)))
        ElseIf InStr(objChild.ID, "MWERT") > 0 Then
            mwertControls.Add objChild
            mwertIndexesCol.Add CLng(GetIndexFromID(CStr(objChild.ID)))
        End If
    Next objChild

    metadata("keys") = CollectionToVariantArray(keysCol)
    metadata("keyIndexes") = CollectionToVariantArray(keyIndexesCol)
    metadata("mwertIndexes") = CollectionToVariantArray(mwertIndexesCol)
    Set metadata("mwertControls") = mwertControls
    metadata("countKeys") = CLng(keysCol.count)
    metadata("pageAnchor") = GetPageAnchor(objContainer)

    Set BuildCharacteristicPageMetadata = metadata
End Function

Private Function CollectionToVariantArray(ByVal values As Collection) As Variant
    Dim arr() As Variant
    Dim i As Long

    If values Is Nothing Then
        CollectionToVariantArray = Array()
        Exit Function
    End If

    If values.count = 0 Then
        CollectionToVariantArray = Array()
        Exit Function
    End If

    ReDim arr(1 To values.count)
    For i = 1 To values.count
        arr(i) = values(i)
    Next i

    CollectionToVariantArray = arr
End Function

Private Sub LogCharacteristicCacheMiss(ByVal reason As String, ByVal mode As String, ByVal cacheKey As String)
    If reason = "cache_key_not_found" And Not CHARACTERISTIC_CACHE_LOG_VERBOSE Then Exit Sub
    If reason <> "cache_key_not_found" And Not CHARACTERISTIC_CACHE_LOG_GUARD_FAILURES Then Exit Sub

    Debug.Print ValidationMessages.DebugCharacteristicCacheMiss(mode, reason, cacheKey)
End Sub

Private Function CanResolveControl(ByVal controlId As String) As Boolean
    Dim ctrl As Object

    On Error Resume Next
    Set ctrl = objSess.FindById(controlId)
    CanResolveControl = Not (ctrl Is Nothing)
    On Error GoTo 0
End Function

Private Function IsCharacteristicMetadataReusable(ByVal objContainer As Object, ByVal metadata As Object, ByRef missReason As String) As Boolean
    Dim currentAnchor As String
    Dim expectedAnchor As String
    Dim mwertControls As Collection

    If metadata Is Nothing Then
        missReason = "metadata_nothing"
        Exit Function
    End If

    currentAnchor = GetPageAnchor(objContainer)

    If Not metadata.exists("pageAnchor") Then
        missReason = "metadata_missing_anchor"
        Exit Function
    End If

    expectedAnchor = CStr(metadata("pageAnchor"))
    If StrComp(currentAnchor, expectedAnchor, vbTextCompare) <> 0 Then
        missReason = "page_anchor_mismatch"
        Exit Function
    End If

    If Not metadata.exists("mwertControls") Then
        missReason = "metadata_missing_mwert_controls"
        Exit Function
    End If

    Set mwertControls = metadata("mwertControls")
    If mwertControls Is Nothing Then
        missReason = "metadata_mwert_controls_nothing"
        Exit Function
    End If

    If mwertControls.count > 0 Then
        If Not CanResolveControl(CStr(mwertControls(1).ID)) Then
            missReason = "stale_mwert_control"
            Exit Function
        End If
    End If

    IsCharacteristicMetadataReusable = True
End Function

Private Function GetCharacteristicPageMetadata(ByVal objContainer As Object, ByVal mode As String) As Object
    Dim cacheKey As String
    Dim metadata As Object
    Dim missReason As String

    EnsureCharacteristicCache
    cacheKey = BuildCharacteristicCacheKey(mode, objContainer)

    If mCharacteristicMetadataCache.exists(cacheKey) Then
        Set metadata = mCharacteristicMetadataCache(cacheKey)

        If IsCharacteristicMetadataReusable(objContainer, metadata, missReason) Then
            Set GetCharacteristicPageMetadata = metadata
            Exit Function
        End If

        InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_PAGE, "cache_guard: " & missReason
        EnsureCharacteristicCache
        cacheKey = BuildCharacteristicCacheKey(mode, objContainer)
        LogCharacteristicCacheMiss missReason, mode, cacheKey
    Else
        LogCharacteristicCacheMiss "cache_key_not_found", mode, cacheKey
    End If

    Set metadata = BuildCharacteristicPageMetadata(objContainer)
    Set mCharacteristicMetadataCache(cacheKey) = metadata
    Set GetCharacteristicPageMetadata = metadata
End Function


Public Function Attach_Session() As Boolean
    Attach_Session = GUI_Session.Attach_Session_Core
End Function

Public Sub CharacteristicCacheInvalidateFull(ByVal reason As String)
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, reason
End Sub

Public Sub CharacteristicCacheInvalidateTab(ByVal reason As String)
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_TAB, reason
End Sub

Public Sub CharacteristicCacheInvalidatePage(ByVal reason As String)
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_PAGE, reason
End Sub

Public Sub SelectCharacteristicsTab()
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_TAB, "Switch to characteristics tab"
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\06").Select
End Sub

Public Sub RunGUIScript(ByVal Class As String)
    GUI_RunCreate.RunGUIScript_Core Class
End Sub





Public Sub FillCharacteristic(searchText As String, fieldText As String)
    Dim characteristicMap As Object

    Set characteristicMap = CreateObject("Scripting.Dictionary")
    characteristicMap(searchText) = fieldText

    FillCharacteristicsBatch characteristicMap
End Sub

Public Sub FillCharacteristicsBatch(ByVal characteristicMap As Object)
    Dim pending As Object
    Dim key As Variant
    Dim specialKeys As Collection
    Dim hasNextPage As Boolean
    Dim btnNext As Object
    Dim objContainer As Object
    Dim prevFirstKey As String
    Dim currentFirstKey As String

    If characteristicMap Is Nothing Then Exit Sub

    BeginCharacteristicCacheRowScope

    Set pending = CreateObject("Scripting.Dictionary")

    For Each key In characteristicMap.keys
        pending(CStr(key)) = CStr(characteristicMap(key))
    Next key

    If pending.count = 0 Then Exit Sub

    Set specialKeys = New Collection

    ' Keep original popup behavior for the special characteristic fields.
    For Each key In pending.keys
        If IsSpecialCharacteristic(CStr(key)) Then
            WriteSpecialCharacteristic CStr(key), CStr(pending(key))
            specialKeys.Add CStr(key)
        End If
    Next key

    For Each key In specialKeys
        pending.Remove CStr(key)
    Next key

    If pending.count = 0 Then Exit Sub

    prevFirstKey = ""

    Do
        If Not TryGetCharacteristicContainer(objContainer) Then Exit Do
        currentFirstKey = GetFirstVisibleCharacteristicKey(objContainer)

        If currentFirstKey <> "" Then
            If currentFirstKey = prevFirstKey Then Exit Do
            prevFirstKey = currentFirstKey
        End If

        WriteCharacteristicsOnCurrentPage objContainer, pending

        If pending.count = 0 Then Exit Do

        hasNextPage = TryMoveToNextCharacteristicPage(btnNext)
    Loop While hasNextPage

    If pending.count > 0 Then
        LogUnwrittenCharacteristics pending
    End If
End Sub

Private Sub WriteCharacteristicsOnCurrentPage(ByVal objContainer As Object, ByVal pending As Object)
    Dim metadata As Object
    Dim keys As Variant
    Dim keyIndexes As Variant
    Dim mwertIndexes As Variant
    Dim mwertControls As Collection
    Dim i As Long
    Dim countKeys As Long
    Dim keyName As String
    Dim nextIndex As Long
    Dim values As Variant
    Dim valueCounter As Long
    Dim idx As Long
    Dim mwertPos As Long

    Set metadata = GetCharacteristicPageMetadata(objContainer, CHARACTERISTIC_MODE_WRITE_NORMAL)
    countKeys = CLng(metadata("countKeys"))

    If countKeys = 0 Then Exit Sub

    keys = metadata("keys")
    keyIndexes = metadata("keyIndexes")
    mwertIndexes = metadata("mwertIndexes")
    Set mwertControls = metadata("mwertControls")

    For i = 1 To countKeys
        keyName = CStr(keys(i))

        If keyName <> "" And pending.exists(keyName) Then
            If i < countKeys Then
                nextIndex = CLng(keyIndexes(i + 1))
            Else
                nextIndex = 9999
            End If

            values = Split(CStr(pending(keyName)), "|")
            valueCounter = 0

            For mwertPos = 1 To mwertControls.count
                idx = CLng(mwertIndexes(mwertPos))

                If idx >= CLng(keyIndexes(i)) And idx < nextIndex Then
                    If valueCounter <= UBound(values) Then
                        mwertControls(mwertPos).text = Trim(CStr(values(valueCounter)))
                        valueCounter = valueCounter + 1
                    Else
                        Exit For
                    End If
                End If
            Next mwertPos

            pending.Remove keyName
            If pending.count = 0 Then Exit Sub
        End If
    Next i
End Sub

Private Sub ScanCharacteristicKeysAndIndexes(ByVal objContainer As Object, ByRef keys() As String, ByRef keyIndexes() As Long, ByRef countKeys As Long)
    Dim objChild As Object
    Dim writePos As Long

    countKeys = 0

    For Each objChild In objContainer.Children
        If InStr(objChild.ID, "MNAME") > 0 Then
            countKeys = countKeys + 1
        End If
    Next objChild

    If countKeys = 0 Then Exit Sub

    ReDim keys(1 To countKeys)
    ReDim keyIndexes(1 To countKeys)

    writePos = 0
    For Each objChild In objContainer.Children
        If InStr(objChild.ID, "MNAME") > 0 Then
            writePos = writePos + 1
            keys(writePos) = Trim(objChild.text)
            keyIndexes(writePos) = GetIndexFromID(objChild.ID)
        End If
    Next objChild
End Sub

Private Function GetFirstVisibleCharacteristicKey(ByVal objContainer As Object) As String
    Dim objChild As Object

    For Each objChild In objContainer.Children
        If InStr(objChild.ID, "MNAME") > 0 Then
            GetFirstVisibleCharacteristicKey = Trim(objChild.text)
            Exit Function
        End If
    Next objChild

    GetFirstVisibleCharacteristicKey = ""
End Function

Private Function IsSpecialCharacteristic(ByVal searchText As String) As Boolean
    IsSpecialCharacteristic = (searchText = "Remarks" Or searchText = "Supply from" Or searchText = "Safety Critical Equipment")
End Function

Private Function TryGetCharacteristicContainer(ByRef objContainer As Object) As Boolean
    On Error Resume Next
    Set objContainer = objSess.FindById(CHARACTERISTIC_CONTAINER_ID)
    TryGetCharacteristicContainer = Not (objContainer Is Nothing)
    On Error GoTo 0
End Function

Private Function TryMoveToNextCharacteristicPage(ByRef btnNext As Object) As Boolean
    Set btnNext = Nothing

    On Error Resume Next
    Set btnNext = objSess.FindById(CHARACTERISTIC_NEXT_BUTTON_ID)
    On Error GoTo 0

    If Not btnNext Is Nothing Then
        If btnNext.Changeable Then
            btnNext.Press
            objSess.FindById("wnd[0]").SendVKey 0
            InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_PAGE, "Characteristic page changed"
            TryMoveToNextCharacteristicPage = True
            Exit Function
        End If
    End If

    TryMoveToNextCharacteristicPage = False
End Function

Private Sub LogUnwrittenCharacteristics(ByVal pending As Object)
    Dim key As Variant

    For Each key In pending.keys
        Debug.Print ValidationMessages.DebugCharacteristicNotFoundOnClassScreen(CStr(key))
    Next key
End Sub

Private Sub WriteSpecialCharacteristic(ByVal searchText As String, ByVal fieldText As String)
    Dim parts As Variant
    Dim subParts() As String
    Dim chunk As String
    Dim i As Long
    Dim j As Long
    Dim mwertFieldId As String

    parts = Split(fieldText, "|")

    mwertFieldId = GetSpecialCharacteristicMWERTFieldId(searchText)

    If UBound(parts) > LBound(parts) Then
        InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_PAGE, "Open special characteristic popup"
        objSess.FindById(mwertFieldId).SetFocus
        objSess.FindById("wnd[0]").SendVKey 4

        If StrComp(searchText, "Safety Critical Equipment", vbTextCompare) = 0 Then
            SelectSafetyCriticalEquipmentValuesInPopup parts
        Else
            For i = LBound(parts) To UBound(parts)
                chunk = Trim(CStr(parts(i)))

                If Len(chunk) > 30 Then
                    subParts = SplitByLength(chunk, 30)
                    For j = LBound(subParts) To UBound(subParts)
                        SendToSAP Trim(CStr(subParts(j))), objSess
                    Next j
                Else
                    SendToSAP chunk, objSess
                End If
            Next i
        End If

        objSess.FindById("wnd[1]/tbar[0]/btn[8]").Press
        objSess.FindById("wnd[0]").SendVKey 0
        InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_PAGE, "Close special characteristic popup"
    Else
        objSess.FindById(mwertFieldId).text = Trim(CStr(parts(LBound(parts))))
    End If
End Sub

Private Sub SelectSafetyCriticalEquipmentValuesInPopup(ByVal values As Variant)
    Dim wanted As Object
    Dim i As Long
    Dim valueText As String
    Dim rowIndex As Long
    Dim textCtrl As Object
    Dim checkCtrl As Object
    Dim textId As String
    Dim checkId As String
    Dim rowValue As String
    Dim tbl As Object
    Dim hasNextPage As Boolean
    Dim scanGuard As Long

    Set wanted = CreateObject("Scripting.Dictionary")
    wanted.compareMode = vbTextCompare

    For i = LBound(values) To UBound(values)
        valueText = Trim$(CStr(values(i)))
        If Len(valueText) > 0 Then
            If Not wanted.exists(valueText) Then
                wanted(valueText) = True
            End If
        End If
    Next i

    If wanted.count = 0 Then Exit Sub

    Set tbl = objSess.FindById("wnd[1]/usr/tblSAPLCTMSVALUE_S")
    If tbl Is Nothing Then Exit Sub

    scanGuard = 0
    Do
        scanGuard = scanGuard + 1
        If scanGuard > 200 Then Exit Do

        For rowIndex = 0 To 99
            textId = "wnd[1]/usr/tblSAPLCTMSVALUE_S/txtRCTMS-ATWTB[3," & CStr(rowIndex) & "]"
            checkId = "wnd[1]/usr/tblSAPLCTMSVALUE_S/chkRCTMS-SEL01[0," & CStr(rowIndex) & "]"

            Set textCtrl = objSess.FindById(textId, False)
            If textCtrl Is Nothing Then Exit For

            rowValue = Trim$(CStr(textCtrl.text))
            If Len(rowValue) > 0 Then
                If wanted.exists(rowValue) Then
                    Set checkCtrl = objSess.FindById(checkId, False)
                    If Not checkCtrl Is Nothing Then
                        checkCtrl.selected = True
                        wanted.Remove rowValue
                        If wanted.count = 0 Then Exit Sub
                    End If
                End If
            End If
        Next rowIndex

        hasNextPage = MoveToNextPopupTablePage(tbl)
    Loop While hasNextPage
End Sub

Private Function MoveToNextPopupTablePage(ByVal tbl As Object) As Boolean
    Dim currentPos As Long
    Dim maxPos As Long
    Dim pageSize As Long
    Dim nextPos As Long

    On Error Resume Next
    currentPos = CLng(tbl.VerticalScrollbar.Position)
    maxPos = CLng(tbl.VerticalScrollbar.Maximum)
    pageSize = CLng(tbl.VisibleRowCount)
    On Error GoTo 0

    If pageSize <= 0 Then pageSize = 10
    If currentPos >= maxPos Then Exit Function

    nextPos = currentPos + pageSize
    If nextPos > maxPos Then nextPos = maxPos
    If nextPos = currentPos Then Exit Function

    On Error Resume Next
    tbl.VerticalScrollbar.Position = nextPos
    objSess.FindById("wnd[1]").SendVKey 0
    MoveToNextPopupTablePage = True
    On Error GoTo 0
End Function

Private Function GetSpecialCharacteristicMWERTFieldId(ByVal searchText As String) As String
    Dim objContainer As Object
    Dim metadata As Object
    Dim keys As Variant
    Dim keyIndexes As Variant
    Dim mwertIndexes As Variant
    Dim mwertControls As Collection
    Dim countKeys As Long
    Dim i As Long
    Dim idx As Long
    Dim nextIndex As Long
    Dim mwertPos As Long

    GetSpecialCharacteristicMWERTFieldId = "wnd[0]/usr/subSUBSCR_BEWERT:SAPLCTMS:5000/tabsTABSTRIP_CHAR/tabpTAB1/ssubTABSTRIP_CHAR_GR:SAPLCTMS:5100/tblSAPLCTMSCHARS_S/ctxtRCTMS-MWERT[1,0]"

    If Not TryGetCharacteristicContainer(objContainer) Then Exit Function

    Set metadata = GetCharacteristicPageMetadata(objContainer, CHARACTERISTIC_MODE_WRITE_SPECIAL)
    countKeys = CLng(metadata("countKeys"))

    If countKeys = 0 Then Exit Function

    keys = metadata("keys")
    keyIndexes = metadata("keyIndexes")
    mwertIndexes = metadata("mwertIndexes")
    Set mwertControls = metadata("mwertControls")

    For i = 1 To countKeys
        If StrComp(CStr(keys(i)), searchText, vbTextCompare) = 0 Then
            If i < countKeys Then
                nextIndex = CLng(keyIndexes(i + 1))
            Else
                nextIndex = 9999
            End If

            For mwertPos = 1 To mwertControls.count
                idx = CLng(mwertIndexes(mwertPos))
                If idx >= CLng(keyIndexes(i)) And idx < nextIndex Then
                    GetSpecialCharacteristicMWERTFieldId = CStr(mwertControls(mwertPos).ID)
                    Exit Function
                End If
            Next mwertPos
        End If
    Next i

    If mwertControls.count > 0 Then
        GetSpecialCharacteristicMWERTFieldId = CStr(mwertControls(1).ID)
    End If
End Function






Public Sub WCM(ByVal Search_SL As Variant, ByVal SL As Variant)
    Dim characteristicMap As Object

    AddWCMClass
    SelectCharacteristicsTab

    Set characteristicMap = CreateObject("Scripting.Dictionary")
    AddLegacyCharacteristic characteristicMap, CStr(Search_SL), SL

    If characteristicMap.count > 0 Then
        FillCharacteristicsBatch characteristicMap
    End If
End Sub

Public Sub AddWCMClass()
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Add WCM class"
    objSess.FindById("wnd[0]/usr/btn%#AUTOTEXT003").Press
    objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,1]").text = "WCM"
    objSess.FindById("wnd[0]").SendVKey 0
End Sub


Function SplitByLength(ByVal txt As String, ByVal maxLen As Long) As Variant
    Dim result() As String
    Dim pos As Long
    Dim count As Long
    Dim chunkCount As Long

    If maxLen <= 0 Then
        SplitByLength = Array()
        Exit Function
    End If

    If Len(txt) = 0 Then
        SplitByLength = Array()
        Exit Function
    End If

    chunkCount = (Len(txt) + maxLen - 1) \ maxLen
    ReDim result(0 To chunkCount - 1)

    count = 0
    pos = 1
    Do While pos <= Len(txt)
        result(count) = Mid(txt, pos, maxLen)
        count = count + 1
        pos = pos + maxLen
    Loop

    SplitByLength = result
End Function


Sub SendToSAP(ByVal txt As String, ByVal objSess As Object)
    objSess.FindById("wnd[1]/usr/tblSAPLCTMSVALUE_S/txtRCTMS-ATWRT[1,0]").text = txt
    objSess.FindById("wnd[1]").SendVKey 0
End Sub


    
    
    






Public Sub TRMNEW(ByVal Search_EX_Marking As Variant, ByVal EX_Marking As Variant, ByVal Safety_Critical_Equipment As Variant, ByVal Search_FIRE As Variant, ByVal FIRE As Variant, ByVal Search_FIRESEALTYPE As Variant, ByVal FIRESEALTYPE As Variant, ByVal Search_FIRESEALPRODUCT As Variant, ByVal FIRESEALPRODUCT As Variant, ByVal Class As Variant)
    Dim characteristicMap As Object
    Dim className As String

    AddTRMClass
    SelectCharacteristicsTab

    Set characteristicMap = CreateObject("Scripting.Dictionary")
    AddLegacyCharacteristic characteristicMap, CStr(Search_EX_Marking), EX_Marking
    AddLegacyCharacteristic characteristicMap, "Safety Critical Equipment", Safety_Critical_Equipment

    className = UCase$(Trim$(CStr(Class)))
    If className = "MKP" Then
        AddLegacyCharacteristic characteristicMap, ResolveLegacyKey(CStr(Search_FIRE), "Fire Classification"), FIRE
        AddLegacyCharacteristic characteristicMap, ResolveLegacyKey(CStr(Search_FIRESEALTYPE), "Fire Sealing Type"), FIRESEALTYPE
        AddLegacyCharacteristic characteristicMap, ResolveLegacyKey(CStr(Search_FIRESEALPRODUCT), "Fire Sealing Product"), FIRESEALPRODUCT
    End If

    If characteristicMap.count > 0 Then
        FillCharacteristicsBatch characteristicMap
    End If
       
End Sub

Private Sub AddLegacyCharacteristic(ByVal characteristicMap As Object, ByVal characteristicKey As String, ByVal characteristicValue As Variant)
    Dim normalizedKey As String
    Dim normalizedValue As String

    normalizedKey = Trim$(characteristicKey)
    normalizedValue = Trim$(CStr(characteristicValue))

    If Len(normalizedKey) = 0 Then Exit Sub
    If Len(normalizedValue) = 0 Then Exit Sub

    characteristicMap(normalizedKey) = normalizedValue
End Sub

Private Function ResolveLegacyKey(ByVal preferredKey As String, ByVal fallbackKey As String) As String
    If Len(Trim$(preferredKey)) > 0 Then
        ResolveLegacyKey = Trim$(preferredKey)
    Else
        ResolveLegacyKey = fallbackKey
    End If
End Function

Public Sub AddTRMClass()
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Add TRM class"
    objSess.FindById("wnd[0]/usr/btn%#AUTOTEXT003").Press
    objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,1]").text = "TRM"
    objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,1]").CaretPosition = 3
    objSess.FindById("wnd[0]").SendVKey 0
End Sub


Public Sub FillMasterdataFields(ByVal Functional_Location As Variant, ByVal Functional_Location_Description As Variant, ByVal Manufacturer As Variant, ByVal Model_Number As Variant, ByVal Manufacturer_Part_Number As Variant, ByVal Manufacturer_Serial As Variant, ByVal Room As Variant, ByVal ABC_Ind As Variant, ByVal Sort_Field As Variant, ByVal Warranty_Start As Variant, ByVal Warranty_End As Variant, ByVal ATEX As Variant, ByVal Risiko As Variant, ByVal Asbestos As Variant, ByVal PTW As Variant, ByVal StrIndicator As Variant, ByVal className As Variant, ByVal Superior_FL As Variant)
    
    Dim ExistingClass As String
    Dim W_Ret As Boolean
    Dim Update As Long
    Dim permits As Collection
    Dim permitName As Variant
    Dim permitRow As Long
    Dim shouldOpenPermitWindow As Boolean
    Dim permitDeleteButton As Object
    Dim permitSelectAllButton As Object
    Dim isKABClass As Boolean
    Dim superiorFlInput As String
    Dim currentSuperiorFl As String
    
    ' Connect to SAP
    W_Ret = Attach_Session
    If Not W_Ret Then
        Exit Sub
    End If
    
    On Error GoTo myerr
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Start FillMasterdataFields transaction flow"
    

    objSess.FindById("wnd[0]/tbar[0]/okcd").text = "/NIL01"
    objSess.FindById("wnd[0]").SendVKey 0
    
    
    objSess.FindById("wnd[0]/usr/txtIFLOS-STRNO").text = Functional_Location
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").text = StrIndicator
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").SetFocus
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").CaretPosition = 3
    objSess.FindById("wnd[0]").SendVKey 0
    
    
    ' Check if FL Exsists, if it does den go to change
    
     If objSess.FindById("wnd[0]/sbar").text = "Functional location " & Functional_Location & " already exists" Then
    
        objSess.FindById("wnd[0]/tbar[0]/okcd").text = "/NIL02"
        objSess.FindById("wnd[0]").SendVKey 0

        objSess.FindById("wnd[0]/usr/ctxtIFLO-TPLNR").text = Functional_Location
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").text = "KKS"
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").SetFocus
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").CaretPosition = 3
        objSess.FindById("wnd[0]").SendVKey 0
        
        Update = 1
    
    End If

    
    'FL Description
    objSess.FindById("wnd[0]/usr/txtIFLO-PLTXT").text = Functional_Location_Description
    
    ExistingClass = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1020/txtITOBATTR-KLASSE").text
    
    'Fill General Tab
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1020/subSUB_1020A:SAPLITO0:1025/ctxtITOB-EQART").text = "s"
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-HERST").text = Manufacturer
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-TYPBZ").text = Model_Number
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-MAPAR").text = Manufacturer_Part_Number
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-SERGE").text = Manufacturer_Serial
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-SERGE").SetFocus
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-SERGE").CaretPosition = 10
    
    'Fill Location Tab
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02").Select
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/txtITOB-MSGRP").text = Room
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/ctxtITOB-ABCKZ").text = ABC_Ind
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/txtITOB-EQFNR").text = Sort_Field
    
    'Warranty Information
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLDT_I").text = Warranty_Start
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLEN_I").text = Warranty_End
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/chkWCHECK_V_H-WAGET_I").selected = True
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/chkWCHECK_V_H-GAERB_I").selected = True
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLEN_I").SetFocus
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLEN_I").CaretPosition = 8
    objSess.FindById("wnd[0]").SendVKey 0

    isKABClass = (StrComp(Trim$(CStr(className)), "KAB", vbTextCompare) = 0)
    superiorFlInput = Trim$(CStr(Superior_FL))

    If isKABClass And Len(superiorFlInput) > 0 Then
        objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04").Select
        currentSuperiorFl = Trim$(CStr(objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1060/subSUB_1060A:SAPLITO0:1066/txtITOB-TPLMA").text))

        If StrComp(currentSuperiorFl, superiorFlInput, vbTextCompare) <> 0 Then
            objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1060/subSUB_1060A:SAPLITO0:1066/btnFCODE_CHM").Press
            objSess.FindById("wnd[1]/usr/ctxtIFLO-TPLMA").text = superiorFlInput
            HandlePopupUntilClosed 25
        End If
    End If
    
    
    Set permits = New Collection

    If ATEX = "X" Then permits.Add "ATEX"
    If Risiko = "X" Then permits.Add "Risiko"
    If Asbestos = "X" Then permits.Add "ASBEST"
    If PTW = "X" Then permits.Add "PTW"

    shouldOpenPermitWindow = (Update = 1 Or permits.count > 0)

    If shouldOpenPermitWindow Then
        objSess.FindById("wnd[0]/mbar/menu[2]/menu[6]").Select

        If Update = 1 Then
            Set permitDeleteButton = objSess.FindById("wnd[1]/tbar[0]/btn[8]", False)
            If Not permitDeleteButton Is Nothing Then
                permitDeleteButton.Press
            End If

            Set permitSelectAllButton = objSess.FindById("wnd[1]/tbar[0]/btn[14]", False)
            If Not permitSelectAllButton Is Nothing Then
                permitSelectAllButton.Press
            End If
        End If

        If permits.count > 0 Then
            permitRow = 1
            For Each permitName In permits
                If permitRow > 4 Then Exit For

                objSess.FindById("wnd[1]/usr/tblSAPLIMSPTCTRL_1000/ctxtRM63S-PMSOG[0," & CStr(permitRow) & "]").text = CStr(permitName)
                permitRow = permitRow + 1
            Next permitName

            objSess.FindById("wnd[1]").SendVKey 0
        End If

        objSess.FindById("wnd[1]/tbar[0]/btn[11]").Press
    End If
    
    If Update = 1 And ExistingClass <> "" Then
    
            'Delete Exsisting classes
            
            objSess.FindById("wnd[0]/tbar[1]/btn[20]").Press
            objSess.FindById("wnd[0]/usr/btnICON_MARKALL").Press
            objSess.FindById("wnd[0]/usr/btnICON_DELETE").Press

              ConfirmPopupOption1 4
            
    End If
    
    
  Exit Sub
    
myerr:
    MsgBox ValidationMessages.ErrorOccurredWhileRetrievingData(), vbCritical + vbOKOnly
    

End Sub

Private Sub HandlePopupUntilClosed(Optional ByVal maxAttempts As Long = 25)
    Dim attempt As Long
    Dim Button As Object
    Dim wnd1 As Object

    If maxAttempts <= 0 Then Exit Sub

    For attempt = 1 To maxAttempts
        Set wnd1 = objSess.FindById("wnd[1]", False)
        If wnd1 Is Nothing Then Exit For

        Set Button = objSess.FindById("wnd[1]/usr/btnSPOP-OPTION1", False)
        If Not Button Is Nothing Then
            Button.Press
            GoTo ContinueLoop
        End If

        Set Button = objSess.FindById("wnd[1]/tbar[0]/btn[0]", False)
        If Not Button Is Nothing Then
            Button.Press
            GoTo ContinueLoop
        End If

        Set Button = objSess.FindById("wnd[1]/tbar[0]/btn[1]", False)
        If Not Button Is Nothing Then
            Button.Press
            GoTo ContinueLoop
        End If

        Set Button = objSess.FindById("wnd[2]/tbar[0]/btn[0]", False)
        If Not Button Is Nothing Then
            Button.Press
            GoTo ContinueLoop
        End If

        Exit For
ContinueLoop:
    Next attempt
End Sub

Private Sub ConfirmPopupOption1(Optional ByVal maxAttempts As Long = 4)
    Dim attempt As Long
    Dim popupButton As Object

    If maxAttempts <= 0 Then Exit Sub

    For attempt = 1 To maxAttempts
        If objSess.ActiveWindow.name <> "wnd[1]" Then Exit For

        Set popupButton = objSess.FindById("wnd[1]/usr/btnSPOP-OPTION1", False)
        If popupButton Is Nothing Then Exit For

        popupButton.Press
    Next attempt
End Sub

Private Function IsClassAssignmentOpen() As Boolean
    Dim classField As Object

    Set classField = objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,0]", False)
    IsClassAssignmentOpen = Not (classField Is Nothing)
End Function

Public Sub FillMasterdataFieldsInitial(ByVal Functional_Location As Variant, ByVal Functional_Location_Description As Variant, ByVal StrIndicator As Variant)
    
    Dim W_Ret As Boolean
    Dim Update As Long
    
    
    ' Connect to SAP
    W_Ret = Attach_Session
    If Not W_Ret Then
        Exit Sub
    End If
    
    On Error GoTo myerr
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Start FillMasterdataFieldsInitial transaction flow"
    

    objSess.FindById("wnd[0]/tbar[0]/okcd").text = "/NIL01"
    objSess.FindById("wnd[0]").SendVKey 0
    
    
    objSess.FindById("wnd[0]/usr/txtIFLOS-STRNO").text = Functional_Location
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").text = StrIndicator
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").SetFocus
    objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").CaretPosition = 3
    objSess.FindById("wnd[0]").SendVKey 0
    
    
    ' Check if FL Exsists, if it does den go to change
    
     If objSess.FindById("wnd[0]/sbar").text = "Functional location " & Functional_Location & " already exists" Then
    
        objSess.FindById("wnd[0]/tbar[0]/okcd").text = "/NIL02"
        objSess.FindById("wnd[0]").SendVKey 0

        objSess.FindById("wnd[0]/usr/ctxtIFLO-TPLNR").text = Functional_Location
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").text = StrIndicator
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").SetFocus
        objSess.FindById("wnd[0]/usr/ctxtRILO0-TPLKZ").CaretPosition = 3
        objSess.FindById("wnd[0]").SendVKey 0
        
        Update = 1
    
    End If

    
    'FL Description
    objSess.FindById("wnd[0]/usr/txtIFLO-PLTXT").text = Functional_Location_Description
    
    'Fill General Tab
    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1020/subSUB_1020A:SAPLITO0:1025/ctxtITOB-EQART").text = "s"
    
    If Update = 1 Then
    
            'Delete Exsisting classes
            
            objSess.FindById("wnd[0]/tbar[1]/btn[20]").Press
            objSess.FindById("wnd[0]/usr/btnICON_MARKALL").Press
            objSess.FindById("wnd[0]/usr/btnICON_DELETE").Press
            
            If objSess.FindById("wnd[0]/sbar").text = "Place the cursor on a valid line" Then
            
                objSess.FindById("wnd[0]/tbar[0]/btn[3]").Press
            
            End If
            
              ConfirmPopupOption1 4
            

    End If
    
    
  Exit Sub
    
myerr:
    MsgBox ValidationMessages.ErrorOccurredWhileRetrievingData(), vbCritical + vbOKOnly
    

End Sub
    

Public Sub GoToClassAssignment(ByVal Class As Variant)

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Enter class assignment"

        If Not IsClassAssignmentOpen() Then
            objSess.FindById("wnd[0]/tbar[1]/btn[20]").Press
        End If
        objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,0]").text = Class
        objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,0]").CaretPosition = 3
        objSess.FindById("wnd[0]").SendVKey 0



End Sub
Public Sub GoToClassAssignmentOnly()

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Enter class assignment only"

        If Not IsClassAssignmentOpen() Then
            objSess.FindById("wnd[0]/tbar[1]/btn[20]").Press
        End If




End Sub

Public Sub EndClassAssignment()

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Exit class assignment"

        If IsClassAssignmentOpen() Then
            objSess.FindById("wnd[0]/tbar[0]/btn[3]").Press
        End If

End Sub

Public Sub SaveFLAndGetStatus(ByVal i As Variant, ByVal Class As Variant)

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Save FL and get status"

        objSess.FindById("wnd[0]/tbar[0]/btn[11]").Press
        
        If objSess.ActiveWindow.name = "wnd[1]" Then
            Worksheets(Class).Cells(i, 1) = "FL NOT CREATED: " & objSess.FindById("wnd[1]/usr/txtMESSTXT1").text & " " & objSess.FindById("wnd[1]/usr/txtMESSTXT2").text
            Worksheets(Class).Cells(i, 1).Interior.Color = RGB(255, 182, 193)
            objSess.FindById("wnd[1]/tbar[0]/btn[0]").Press
            objSess.FindById("wnd[0]/tbar[0]/btn[15]").Press
            objSess.FindById("wnd[1]/usr/btnSPOP-OPTION2").Press

        Else

        Worksheets(Class).Cells(i, 1) = objSess.FindById("wnd[0]/sbar").text
        Worksheets(Class).Cells(i, 1).Interior.Color = RGB(144, 238, 144)
        
        End If


End Sub

Public Sub SaveFLAndGetStatusInitial(ByVal i As Variant)

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Save FL initial"

        objSess.FindById("wnd[0]/tbar[0]/btn[11]").Press
        
        If objSess.ActiveWindow.name = "wnd[1]" Then
            Worksheets("Initial Entry").Cells(i, 6) = "FL NOT CREATED: " & objSess.FindById("wnd[1]/usr/txtMESSTXT1").text & " " & objSess.FindById("wnd[1]/usr/txtMESSTXT2").text
            Worksheets("Initial Entry").Cells(i, 6).Interior.Color = RGB(255, 182, 193)
            objSess.FindById("wnd[1]/tbar[0]/btn[0]").Press
            objSess.FindById("wnd[0]/tbar[0]/btn[15]").Press
            objSess.FindById("wnd[1]/usr/btnSPOP-OPTION2").Press

        Else

        Worksheets("Initial Entry").Cells(i, 6) = objSess.FindById("wnd[0]/sbar").text
        Worksheets("Initial Entry").Cells(i, 6).Interior.Color = RGB(144, 238, 144)
        
        End If


End Sub


Public Sub EndTransaction()

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "End transaction"

        objSess.EndTransaction
    
End Sub


Public Sub AddGIV_EXT()

    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Add GIV_EXT class"

        objSess.FindById("wnd[0]/usr/btn%#AUTOTEXT003").Press
        objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,1]").text = "GIV_EXT"
        objSess.FindById("wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,1]").CaretPosition = 3
        objSess.FindById("wnd[0]").SendVKey 0
        
End Sub

Public Sub CreateMaterials()
    GUI_CreateMaterials.CreateMaterials_Core
End Sub

Public Sub CreateFLBOM()
    GUI_FLBOM.CreateFLBOM_Grouped_Arr
End Sub

Public Sub AttatchMaterialDocuments()
    GUI_Documents.AttatchMaterialDocuments_Core
End Sub

Private Function MergePipeValues(ByVal existingValues As String, ByVal newValues As String) As String
    Dim seen As Object
    Dim resultParts As Collection
    Dim source As Variant
    Dim tokens As Variant
    Dim token As Variant
    Dim cleaned As String
    Dim i As Long
    Dim resultText As String

    Set seen = CreateObject("Scripting.Dictionary")
    seen.compareMode = vbTextCompare
    Set resultParts = New Collection

    For Each source In Array(existingValues, newValues)
        If Len(Trim$(CStr(source))) > 0 Then
            tokens = Split(CStr(source), "|")
            For Each token In tokens
                cleaned = Trim$(CStr(token))
                If Len(cleaned) > 0 Then
                    If Not seen.exists(cleaned) Then
                        seen(cleaned) = True
                        resultParts.Add cleaned
                    End If
                End If
            Next token
        End If
    Next source

    For i = 1 To resultParts.count
        If i = 1 Then
            resultText = CStr(resultParts(i))
        Else
            resultText = resultText & "|" & CStr(resultParts(i))
        End If
    Next i

    MergePipeValues = resultText
End Function



Public Sub ExtractAndWriteClassCharacteristics(Class As String, writeRow As Long, colIndex As Dictionary, ws As Worksheet)

    Dim objContainer As Object
    Dim metadata As Object
    Dim dict As Object
    Dim k As Variant
    Dim hasNextPage As Boolean
    Dim btnNext As Object
    Dim prevFirstKey As String
    Dim keys As Variant
    Dim keyIndexes As Variant
    Dim mwertIndexes As Variant
    Dim mwertControls As Collection
    Dim i As Long
    Dim countKeys As Long
    Dim mwertPos As Long
    Dim idx As Long
    Dim nextIndex As Long
    Dim combinedValues As String
    
    BeginCharacteristicCacheRowScope
    prevFirstKey = ""
    
    Do
        ' Genindl?s containeren for den aktuelle side
        If Not TryGetCharacteristicContainer(objContainer) Then Exit Do

        ' Opret dictionary til MNAME/MWERT-par
        Set dict = CreateObject("Scripting.Dictionary")
        
        Set metadata = GetCharacteristicPageMetadata(objContainer, CHARACTERISTIC_MODE_EXTRACT)
        keys = metadata("keys")
        keyIndexes = metadata("keyIndexes")
        mwertIndexes = metadata("mwertIndexes")
        Set mwertControls = metadata("mwertControls")
        countKeys = CLng(metadata("countKeys"))
        
        ' For hver n?gle, saml MWERT indtil n?ste n?gle
        For i = 1 To countKeys
            combinedValues = ""
            
            If i < countKeys Then
                nextIndex = CLng(keyIndexes(i + 1))
            Else
                nextIndex = 9999 ' stort tal for sidste n?gle
            End If
            
            For mwertPos = 1 To mwertControls.count
                idx = CLng(mwertIndexes(mwertPos))

                If idx >= CLng(keyIndexes(i)) And idx < nextIndex Then
                    If Trim(CStr(mwertControls(mwertPos).text)) <> "" Then
                        If combinedValues = "" Then
                            combinedValues = Trim(CStr(mwertControls(mwertPos).text))
                        Else
                            combinedValues = combinedValues & "|" & Trim(CStr(mwertControls(mwertPos).text))
                        End If
                    End If
                End If
            Next mwertPos
            
            If CStr(keys(i)) <> "" And combinedValues <> "" Then
                If dict.exists(CStr(keys(i))) Then
                    dict(CStr(keys(i))) = MergePipeValues(CStr(dict(CStr(keys(i)))), combinedValues)
                Else
                    dict(CStr(keys(i))) = combinedValues
                End If
            End If
        Next i

        ' Stop hvis vi er p? samme side som f?r
        If dict.count > 0 Then
            If prevFirstKey = dict.keys()(0) Then Exit Do
            prevFirstKey = dict.keys()(0)
        End If

        ' Skriv til arket
        For Each k In dict.keys
            If colIndex.exists(k) Then
                ws.Cells(writeRow, colIndex(k)).value = MergePipeValues(CStr(ws.Cells(writeRow, colIndex(k)).value), CStr(dict(k)))
            End If
        Next k

        ' Tjek om der er en "N?ste side"-knap
        hasNextPage = TryMoveToNextCharacteristicPage(btnNext)

    Loop While hasNextPage

End Sub

' Funktion til at hente korrekt index fra ID
Function GetIndexFromID(ByVal idText As String) As Long
    Dim lastBracketPos As Long, endPos As Long, bracketContent As String
    Dim parts() As String

    lastBracketPos = InStrRev(idText, "[")
    endPos = InStrRev(idText, "]")

    If lastBracketPos > 0 And endPos > lastBracketPos Then
        bracketContent = Mid(idText, lastBracketPos + 1, endPos - lastBracketPos - 1)
        parts = Split(bracketContent, ",")
        GetIndexFromID = CLng(parts(0))
    Else
        GetIndexFromID = -1
    End If
End Function



Public Function ExtractMasterdataFields(ByVal fl As String) As Object
    Dim W_Ret As Boolean
    Dim W_System As String
    Dim Functional_Location As String
    Dim fullTitle As String
    Dim shortTitle As String
    Dim i As Long
    Dim cellId As String
    Dim result As Object
    Set result = CreateObject("Scripting.Dictionary")

    On Error GoTo myerr
    InvalidateCharacteristicCache CHARACTERISTIC_SCOPE_FULL, "Start ExtractMasterdataFields transaction flow"

    Functional_Location = fl

    objSess.FindById("wnd[0]/tbar[0]/okcd").text = "/NIL03"
    objSess.FindById("wnd[0]").SendVKey 0

    objSess.FindById("wnd[0]/usr/ctxtIFLO-TPLNR").text = Functional_Location
    objSess.FindById("wnd[0]").SendVKey 0

    If objSess.FindById("wnd[0]/sbar").text = "" Then

    result("Status") = objSess.FindById("wnd[0]/sbar").text

    ' Ekstraher data fra SAP GUI og gem i dictionary
    result("Functional_Location") = Functional_Location
    result("Act_Class") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1020/txtITOBATTR-KLASSE").text
    result("Functional_Location_Description") = objSess.FindById("wnd[0]/usr/txtIFLO-PLTXT").text
    result("Manufacturer") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-HERST").text
    result("Model_Number") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-TYPBZ").text
    result("Manufacturer_Part_Number") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-MAPAR").text
    result("Manufacturer_Serial") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\01/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102C:SAPLITO0:1022/txtITOB-SERGE").text

    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02").Select

    result("Room") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/txtITOB-MSGRP").text
    result("ABC_Ind") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/ctxtITOB-ABCKZ").text
    result("Sort_Field") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1050/txtITOB-EQFNR").text
    result("Warranty_Start") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLDT_I").text
    result("Warranty_End") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\02/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/ctxtWCHECK_V_H-GWLEN_I").text

    objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04").Select

    result("StrIndicator") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1060/subSUB_1060A:SAPLITO0:1066/txtITOBATTR-TPLKZ").text
    result("Superior_FL") = objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\04/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1060/subSUB_1060A:SAPLITO0:1066/txtITOB-TPLMA").text


    ' ?bn menu for Permits
    objSess.FindById("wnd[0]/mbar/menu[2]/menu[6]").Select

    ' Hent vinduets titel
        fullTitle = objSess.FindById("wnd[1]").text
        shortTitle = Trim(Mid(fullTitle, InStrRev(fullTitle, "-") + 1))
        
        If shortTitle = "Display Permits Assigned" Then
            ' Loop gennem r?kker i permit-tabellen
            For i = 0 To 6
                cellId = "wnd[1]/usr/tblSAPLIMSPTCTRL_1000/ctxtRM63S-PMSOG[0," & i & "]"
                Select Case objSess.FindById(cellId).text
                    Case "ATEX", "RISIKO", "ASBEST", "PTW"
                        result(objSess.FindById(cellId).text) = "X"
                End Select
            Next
            objSess.FindById("wnd[1]/tbar[0]/btn[11]").Press
        Else
            objSess.FindById("wnd[1]").Close
        End If

    Else: result("Status") = objSess.FindById("wnd[0]/sbar").text

    End If

    Set ExtractMasterdataFields = result
    Exit Function

myerr:
    MsgBox ValidationMessages.ErrorOccurredWhileExtractingData(), vbCritical + vbOKOnly
    Set ExtractMasterdataFields = Nothing
End Function

Public Function ExtractCharacteristic(searchText As String) As String
    Dim result As String

    On Error GoTo myerr

    ' ?bn s?gevinduet for karakteristikker
    objSess.FindById("wnd[0]/usr/subSUBSCR_BEWERT:SAPLCTMS:5000/tabsTABSTRIP_CHAR/tabpTAB1/ssubTABSTRIP_CHAR_GR:SAPLCTMS:5100/btnRCTMS-AUFS").Press

    ' S?g efter karakteristikken
    objSess.FindById("wnd[1]/usr/txtCLHP-CR_STATUS_TEXT").text = searchText
    objSess.FindById("wnd[1]").SendVKey 0
    
    If searchText = "EX" And objSess.ActiveWindow.name = "wnd[2]" Then
    
    objSess.FindById("wnd[2]/tbar[0]/btn[0]").Press
    objSess.FindById("wnd[1]").Close
    
    result = "NO_TRM"
    ExtractCharacteristic = result
    Exit Function
    
    End If

    
    ' L?s v?rdien fra f?rste r?kke i tabellen
    result = objSess.FindById("wnd[0]/usr/subSUBSCR_BEWERT:SAPLCTMS:5000/tabsTABSTRIP_CHAR/tabpTAB1/ssubTABSTRIP_CHAR_GR:SAPLCTMS:5100/tblSAPLCTMSCHARS_S/ctxtRCTMS-MWERT[1,0]").text
    
    
    ExtractCharacteristic = result
    Exit Function

myerr:
    MsgBox ValidationMessages.ErrorExtractingCharacteristic(searchText), vbExclamation
    ExtractCharacteristic = ""
End Function

Public Sub RunGUIScript_Extract()
    Const MAX_ROWS_PER_EXTRACT As Long = 50000

    Dim wsExtract As Worksheet
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
    Dim Data As Object
    Dim writeRow As Long
    Dim classDict As Object, classDict2 As Object
    Dim classKeys As Variant, classValues As Variant
    Dim tableRange As Range, tableColumn As Range
    Dim SearchKeys As Dictionary
    Dim Class As String
    Dim W_Ret As Boolean
    Dim affected As Collection
    Dim rowGuard As Long

    On Error GoTo myerr

    CaptureAppState appState
    ApplySafeExecution disableEvents:=True, disableScreenUpdating:=True
    Set affected = New Collection

    Set wsExtract = Worksheets("Extract Data")
    wsExtract.Activate

    W_Ret = Attach_Session
    If Not W_Ret Then
        MsgBox ValidationMessages.SapSessionCouldNotBeAttached(), vbCritical
        GoTo Cleanup
    End If

    totalRows = wsExtract.Cells(wsExtract.rows.count, "A").End(xlUp).Row - 3

    Progress_Show totalRows, "Starting data extraction..."

    startTime = Timer
    i = 4
    processedRows = 0

    ' Load dictionary tables
    Set classDict = CreateObject("Scripting.Dictionary")
    Set classDict2 = CreateObject("Scripting.Dictionary")
    Set ws = ThisWorkbook.Sheets("DictionaryTable")

    ' ComponentKey dictionary
    Set tableRange = ws.ListObjects("ClassDeterminationComponentKey").Range
    Set tableColumn = tableRange.Columns(1)
    classKeys = Application.Transpose(tableColumn.value)
    Set tableColumn = tableRange.Columns(2)
    classValues = Application.Transpose(tableColumn.value)
    For i = LBound(classKeys) To UBound(classKeys)
        classDict.Add classKeys(i), classValues(i)
    Next i

    ' AggregateKey dictionary
    Set tableRange = ws.ListObjects("ClassDeterminationAggregateKey").Range
    Set tableColumn = tableRange.Columns(1)
    classKeys = Application.Transpose(tableColumn.value)
    Set tableColumn = tableRange.Columns(2)
    classValues = Application.Transpose(tableColumn.value)
    For i = LBound(classKeys) To UBound(classKeys)
        classDict2.Add classKeys(i), classValues(i)
    Next i
    
    i = 4

    ' Start loop
    Do Until wsExtract.Cells(i, "A").value = ""
        rowGuard = rowGuard + 1
        If rowGuard > MAX_ROWS_PER_EXTRACT Then
            Err.Raise vbObjectError + 2201, "RunGUIScript_Extract", "Row guard exceeded. Stopping extract to prevent memory exhaustion."
        End If

        Dim fl As String
        fl = wsExtract.Cells(i, "A").value

        Set Data = ExtractMasterdataFields(fl)
        
        If Data("Status") = "" Then

                ' Bestem Class hvis Act_Class er tom
                If Data("Act_Class") = "" Or Data("Act_Class") = "TRM" Then
                    Dim compKey As String, aggKey As String
                    compKey = Mid(fl, 18, 2)
                    aggKey = Mid(fl, 12, 2)
        
                    If classDict.exists(compKey) Then
                        Class = classDict(compKey)
                    ElseIf classDict2.exists(aggKey) Then
                        Class = classDict2(aggKey)
                    Else
                        Class = "NO CLASS"
                    End If
                Else
                    Class = Data("Act_Class")
                End If
        
                Set ws = Worksheets(Class)
        
                If ws.Visible <> xlSheetVisible Then
                    ws.Visible = xlSheetVisible
                End If
                ws.Activate
        
                Set headerRow = ws.rows(3)
                Set colIndex = New Dictionary
        
                For Each cell In headerRow.Cells
                    If Not IsEmpty(cell.value) Then
                        colIndex(cell.value) = cell.Column
                    End If
                Next cell
        
                writeRow = ws.Cells(ws.rows.count, colIndex("Functional Location")).End(xlUp).Row + 1
                If writeRow < 4 Then writeRow = 4
        
                ws.Cells(writeRow, colIndex("Functional Location")).value = Data("Functional_Location")
                ws.Cells(writeRow, colIndex("Description")).value = Data("Functional_Location_Description")
                ws.Cells(writeRow, colIndex("Manufacturer")).value = Data("Manufacturer")
                ws.Cells(writeRow, colIndex("Model Number")).value = Data("Model_Number")
                ws.Cells(writeRow, colIndex("Manufacturer Part Number")).value = Data("Manufacturer_Part_Number")
                ws.Cells(writeRow, colIndex("Manufacturer Serial Number")).value = Data("Manufacturer_Serial")
                ws.Cells(writeRow, colIndex("Room")).value = Data("Room")
                ws.Cells(writeRow, colIndex("ABC Indic.")).value = Data("ABC_Ind")
                ws.Cells(writeRow, colIndex("Sort Field")).value = Data("Sort_Field")
                ws.Cells(writeRow, colIndex("Warranty Start")).value = Data("Warranty_Start")
                ws.Cells(writeRow, colIndex("Warranty End")).value = Data("Warranty_End")
                ws.Cells(writeRow, colIndex("Atex")).value = Data("ATEX")
                ws.Cells(writeRow, colIndex("Risiko")).value = Data("RISIKO")
                ws.Cells(writeRow, colIndex("Asbestos")).value = Data("ASBEST")
                ws.Cells(writeRow, colIndex("PTW")).value = Data("PTW")
                ws.Cells(writeRow, colIndex("StrIndicator")).value = Data("StrIndicator")
                ws.Cells(writeRow, colIndex("Superior FL")).value = Data("Superior_FL")

                AddUniqueClass affected, ws.name

                Class = Data("Act_Class")
                
                 ' Create dictionaries from the table
                If Class <> "NO CLASS" And Class <> "" Then
                
                SelectCharacteristicsTab
                
                Call ExtractAndWriteClassCharacteristics(Class, writeRow, colIndex, ws)
                
                End If
        
        Else:
        
                writeRow = wsExtract.Cells(wsExtract.rows.count, "D").End(xlUp).Row + 1
                        If writeRow < 4 Then writeRow = 4
                
                wsExtract.Cells(writeRow, "D").value = fl
                wsExtract.Cells(writeRow, "E").value = Data("Status")
        
        End If

        processedRows = processedRows + 1

        elapsedTime = Timer - startTime
        remainingTime = (elapsedTime / processedRows) * (totalRows - processedRows)

        Progress_Update processedRows, ValidationMessages.ProgressExtractingRow(processedRows, totalRows, remainingTime / 60)

        DoEvents
        i = i + 1
        wsExtract.Activate
    Loop


    ' Ryd kolonne A efter data er extractet
    wsExtract.Range("A4:A" & wsExtract.Cells(wsExtract.rows.count, "A").End(xlUp).Row).ClearContents

    If Not affected Is Nothing Then
        If affected.count > 0 Then
            VerifyAffectedClassSheets affected, respectE2:=False
        End If
    End If


    MsgBox ValidationMessages.DataExtractionCompleted(), vbOKOnly

Cleanup:
    Progress_End ValidationMessages.ProgressDataExtractionCompleted()
    RestoreAppState appState
    Exit Sub

myerr:
    MsgBox ValidationMessages.ErrorOccurredDuringDataExtraction(), vbCritical + vbOKOnly
    Resume Cleanup
End Sub




Public Sub DocumentationAttach(ByVal DokNum As Variant, ByVal ExistingClass As String)

On Error GoTo myerr
        
        If ExistingClass = "" Then
        
        objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\05").Select
        objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\05/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1100/subSUB_1100A:SAPLCV140:0204/subDOC_ALV:SAPLCV140:0207/tblSAPLCV140SUB_DOC/ctxtDRAW-DOKNR[1,0]").SetFocus
        
            Else
            
            objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\06").Select
            objSess.FindById("wnd[0]/usr/tabsTABSTRIP/tabpT\06/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1100/subSUB_1100A:SAPLCV140:0204/subDOC_ALV:SAPLCV140:0207/tblSAPLCV140SUB_DOC/ctxtDRAW-DOKNR[1,0]").SetFocus
            
        End If
                
        
        objSess.FindById("wnd[0]").SendVKey 4
        objSess.FindById("wnd[1]/usr/tabsG_SELONETABSTRIP/tabpTAB005/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[2,24]").text = "AVV"
        objSess.FindById("wnd[1]/usr/tabsG_SELONETABSTRIP/tabpTAB005/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[3,24]").text = "55"
        objSess.FindById("wnd[1]/usr/tabsG_SELONETABSTRIP/tabpTAB005/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[4,24]").text = "HDA*" 'DokNum
        objSess.FindById("wnd[1]/usr/tabsG_SELONETABSTRIP/tabpTAB005/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[9,24]").text = "TDO"
        objSess.FindById("wnd[1]/tbar[0]/btn[0]").Press
        
        Dim props
        props = Array("Id", "Text", "Type", "IconName")

'        Dim json1 As String
'        Dim json As String
'
'        json1 = objSess.GetObjectTree("", props)
'
'        json = JsonConverter.ParseJson(json1)
'
'        MsgBox json
        
        Dim i, cellId, Dok

        For i = 3 To 100 ' Antal r?kker at tjekke (just?r efter behov)
            cellId = "wnd[1]/usr/lbl[61," & i & "]"
            
            ' Tjek om cellen findes (for at undg? fejl)
'            If objSess.findById(cellId, False) Is Nothing Then
'                Exit For ' Stop hvis der ikke er flere r?kker
'            End If
        
            ' L?s v?rdien
            Dok = objSess.FindById(cellId).text
        
            ' Hvis Dok starter med HDA, stop loop
            If Dok = DokNum Then
                Exit For
            End If
            
          Next
            
        objSess.FindById(cellId).SetFocus
        objSess.FindById("wnd[1]/tbar[0]/btn[0]").Press

Exit Sub

myerr:
    MsgBox ValidationMessages.ErrorOccurredWhileRetrievingData(), vbCritical + vbOKOnly
    

End Sub




Public Sub WriteClassCharacteristics(ByVal dict As Variant)
    FillCharacteristicsBatch dict
End Sub


