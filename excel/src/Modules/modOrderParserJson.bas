Option Explicit

Public Sub ParseOrderJSON(ByVal root As Object, Optional ByVal aufnr As String = "")
    ' OData v2 JSON ? d + evt. results  (spec: outermost "d")  '
    Dim d As Object
    Set d = root("d")

    Dim header As Object
    If HasKey(d, "results") Then
        If d("results").Count = 0 Then Exit Sub
        Set header = d("results")(1)
    Else
        Set header = d
    End If
    
    ' --- Header (flad) ---
    WriteJsonObjectToSheet WS_RAW_ORDRE_HEADER, header, aufnr

    ' --- Relationer (brug pr�cis samme navne som i dit JSON-svar) ---
    Dim operations As Collection
    Set operations = ResolveRelationArray(header, "WorkOrderOperationsSet")

    If operations.Count > 0 Then
        EnrichOperationsWithLongText operations, aufnr
        WriteJsonArrayToSheet WS_RAW_ORDRE_OPERATIONS, operations, aufnr
        AppendOperationAttachments operations, aufnr
    End If

    ExtractRel header, "Objects", WS_RAW_ORDRE_OBJECTS, aufnr
    ExtractRel header, "Attachment", WS_RAW_ORDRE_ATTACHMENTS, aufnr
End Sub

Private Sub AppendOperationAttachments(ByVal operations As Collection, ByVal aufnr As String)
    Dim itm As Object
    Dim vornr As String
    Dim rows As Collection
    Dim rowItem As Object

    If operations Is Nothing Then Exit Sub
    If operations.Count = 0 Then Exit Sub

    For Each itm In operations
        vornr = vbNullString
        If TypeName(itm) = "Dictionary" Then
            If itm.Exists("Vornr") Then vornr = CStr(itm("Vornr"))
        End If
        If Len(Trim$(vornr)) = 0 Then GoTo NextOperation

        Set rows = FetchOperationAttachments(aufnr, vornr)
        If rows Is Nothing Then GoTo NextOperation
        If rows.Count = 0 Then GoTo NextOperation

        For Each rowItem In rows
            If TypeName(rowItem) = "Dictionary" Then
                If Not rowItem.Exists("Act") Then rowItem.Add "Act", Trim$(vornr)
            End If
        Next rowItem

        WriteJsonArrayToSheet WS_RAW_ORDRE_ATTACHMENTS, rows, aufnr

NextOperation:
    Next itm
End Sub


' Hent en relation: hvis udvidet ? skriv; ellers f�lg __deferred.uri og skriv (inkl. paging)
Private Sub ExtractRel(ByVal header As Object, ByVal relName As String, ByVal sheetName As String, ByVal aufnr As String)
    Dim relRows As Collection
    Set relRows = ResolveRelationArray(header, relName)
    If relRows.Count = 0 Then Exit Sub

    WriteJsonArrayToSheet sheetName, relRows, aufnr
End Sub

Private Function ResolveRelationArray(ByVal header As Object, ByVal relName As String) As Collection
    Dim relVal As Object
    Dim uri As String

    Set ResolveRelationArray = New Collection

    On Error Resume Next
    Set relVal = header(relName)
    On Error GoTo 0

    If relVal Is Nothing Then Exit Function

    If TypeName(relVal) = "Dictionary" And HasKey(relVal, "results") Then
        Set ResolveRelationArray = relVal("results")
        Exit Function
    End If

    If TypeName(relVal) = "Collection" Then
        Set ResolveRelationArray = relVal
        Exit Function
    End If

    If TypeName(relVal) = "Dictionary" And HasKey(relVal, "__deferred") Then
        uri = CStr(relVal("__deferred")("uri"))
        Debug.Print "FOLLOW JSON URI:", uri
        Set ResolveRelationArray = FetchJsonArrayPaged(uri)
        Debug.Print relName & " rows: ", ResolveRelationArray.Count
    End If
End Function

Private Sub EnrichOperationsWithLongText(ByVal operations As Collection, ByVal aufnr As String)
    Dim itm As Object
    Dim vornr As String
    Dim r As Long

    If operations Is Nothing Then Exit Sub
    If operations.Count = 0 Then Exit Sub

    For r = 1 To operations.Count
        Set itm = operations(r)
        vornr = vbNullString

        If TypeName(itm) = "Dictionary" Then
            If itm.Exists("Vornr") Then vornr = CStr(itm("Vornr"))
            itm("LongText") = FetchOperationLongtext(aufnr, vornr)
        End If
    Next r
End Sub

Private Function FetchOperationLongtext(ByVal aufnr As String, ByVal vornr As String) As String
    On Error GoTo EH

    Dim normalizedVornr As String
    Dim url As String
    Dim root As Object
    Dim d As Object

    normalizedVornr = NormalizeVornr(vornr)
    If Len(aufnr) = 0 Or Len(normalizedVornr) = 0 Then Exit Function

    url = BASE_URL & "WorkOrderOperationsSet(Aufnr='" & EscapeODataString(aufnr) & "',Vornr='" & EscapeODataString(normalizedVornr) & "')?$format=json"
    Set root = HttpGetJson(url)
    Set d = root("d")

    If HasKey(d, "Longtext") Then
        FetchOperationLongtext = CStr(CoerceValue(d("Longtext")))
    Else
        FetchOperationLongtext = vbNullString
    End If
    Exit Function

EH:
    Debug.Print "Longtext fetch failed for "; aufnr; "/"; vornr; ": "; Err.Description
    FetchOperationLongtext = vbNullString
End Function

Private Function FetchOperationAttachments(ByVal aufnr As String, ByVal vornr As String) As Collection
    On Error GoTo EH

    Dim normalizedVornr As String
    Dim url As String

    Set FetchOperationAttachments = New Collection

    normalizedVornr = NormalizeVornr(vornr)
    If Len(aufnr) = 0 Or Len(normalizedVornr) = 0 Then Exit Function

    url = BASE_URL & "WorkOrderOperationsSet(Aufnr='" & EscapeODataString(aufnr) & "',Vornr='" & EscapeODataString(normalizedVornr) & "')/Attachments"
    Set FetchOperationAttachments = FetchJsonArrayPaged(url)
    Exit Function

EH:
    Debug.Print "Attachment fetch failed for "; aufnr; "/"; vornr; ": "; Err.Description
    Set FetchOperationAttachments = New Collection
End Function

Private Function NormalizeVornr(ByVal vornr As String) As String
    Dim s As String

    s = Trim$(vornr)
    If Len(s) = 0 Then Exit Function

    If IsAllDigits(s) Then
        If Len(s) < 4 Then
            NormalizeVornr = Right$("0000" & s, 4)
        Else
            NormalizeVornr = s
        End If
    Else
        NormalizeVornr = s
    End If
End Function

Private Function IsAllDigits(ByVal value As String) As Boolean
    Dim i As Long
    Dim ch As String

    If Len(value) = 0 Then Exit Function

    For i = 1 To Len(value)
        ch = Mid$(value, i, 1)
        If ch < "0" Or ch > "9" Then Exit Function
    Next i

    IsAllDigits = True
End Function

Private Function EscapeODataString(ByVal value As String) As String
    EscapeODataString = Replace(value, "'", "''")
End Function


' Henter en hel entity set (feed) i JSON med paging (__next), og returnerer som Collection af Dictionary
Private Function FetchJsonArrayPaged(ByVal uri As String) As Object
    ' Samler alle poster fra et entity set (med paging via d.__next) i en 1-baseret VBA Collection
    Dim acc As Collection
    Set acc = New Collection

    Dim nextUrl As String: nextUrl = uri

    Do While Len(nextUrl) > 0
        ' Tving JSON (OData v2) via $format=json
        Dim fetchUrl As String
        fetchUrl = nextUrl & IIf(InStr(1, nextUrl, "?", vbTextCompare) > 0, "&", "?") & "$format=json"

        Dim root As Object, d As Object
        Set root = HttpGetJson(fetchUrl)
        Set d = root("d")

        If HasKey(d, "results") Then
            Dim i As Long
            For i = 1 To d("results").Count                  ' Collection er 1-baseret
                acc.Add d("results")(i)
            Next i
        Else
            ' single entry ? l�g den som et element i collection
            acc.Add d
        End If

        If HasKey(d, "__next") Then
            nextUrl = CStr(d("__next"))
        Else
            nextUrl = vbNullString
        End If
    Loop

    Set FetchJsonArrayPaged = acc
End Function


' ----------------- Fladning/skrivning -----------------

Private Sub WriteJsonObjectToSheet(ByVal sheetName As String, ByVal obj As Object, ByVal aufnr As String)
    Dim cols As Object: Set cols = CreateObject("Scripting.Dictionary")
    Dim normalized As Object: Set normalized = CreateObject("Scripting.Dictionary")
    Dim k As Variant, i As Long
    Dim mappedName As String

    If StrComp(sheetName, WS_RAW_ORDRE_HEADER, vbTextCompare) = 0 Then
        ' Raw_Ordre_Header requires explicit header renaming/removal.
        For Each k In obj.Keys
            If IsScalar(obj(k)) Then
                mappedName = MapRawOrderHeaderFieldName(CStr(k))
                If Len(mappedName) > 0 Then
                    If Not normalized.Exists(mappedName) Then
                        normalized.Add mappedName, CoerceValue(obj(k))
                    End If
                End If
            End If
        Next

        If Not normalized.Exists("Order_number") Then normalized.Add "Order_number", aufnr

        For Each k In normalized.Keys
            If Not cols.Exists(CStr(k)) Then cols.Add CStr(k), cols.Count + 1
        Next
    Else
        ' tag kun skalarer (underordnede objekter/Collections springes over)
        For Each k In obj.Keys
            If IsScalar(obj(k)) Then
                If Not cols.Exists(CStr(k)) Then cols.Add CStr(k), cols.Count + 1
            End If
        Next

        If Not cols.Exists("AUFNR") Then cols.Add "AUFNR", cols.Count + 1
    End If

    If cols.Count = 0 Then
        modUtil.WriteTableToSheetAppend sheetName, Empty, cols
        Exit Sub
    End If

    Dim rows() As Variant
    ReDim rows(1 To 1, 1 To cols.Count)

    i = 0
    For Each k In cols.Keys
        i = i + 1
        If StrComp(sheetName, WS_RAW_ORDRE_HEADER, vbTextCompare) = 0 Then
            If normalized.Exists(CStr(k)) Then
                rows(1, i) = normalized(CStr(k))
            Else
                rows(1, i) = Empty
            End If
        ElseIf CStr(k) = "AUFNR" Then
            rows(1, i) = aufnr
        Else
            rows(1, i) = CoerceValue(obj(k))
        End If
    Next

    modUtil.WriteTableToSheetAppend sheetName, rows, cols
End Sub

Private Function MapRawOrderHeaderFieldName(ByVal sourceName As String) As String
    Select Case UCase$(Trim$(sourceName))
        Case "MAINTENANCEACTIVITYTYPE"
            MapRawOrderHeaderFieldName = "MaintActivityType"
        Case "REFERENCEORDER"
            MapRawOrderHeaderFieldName = "Reference_Order"
        Case "AUART"
            MapRawOrderHeaderFieldName = "Order_Type"
        Case "AUFNR"
            MapRawOrderHeaderFieldName = "Order_number"
        Case "KTEXT"
            MapRawOrderHeaderFieldName = "Short_Text"
        Case "LONGTEXT"
            MapRawOrderHeaderFieldName = "Long_Text"
        Case "PRIOK"
            MapRawOrderHeaderFieldName = "Priority"
        Case "SWERK"
            MapRawOrderHeaderFieldName = "Planning_plant"
        Case "TPLNR"
            MapRawOrderHeaderFieldName = "Functional_loc"
        Case "VAPLZ"
            MapRawOrderHeaderFieldName = "Main_WorkCtr"
        Case "IW33_WAPOS"
            MapRawOrderHeaderFieldName = "Maintenance_item"
        Case "AEDATUTC", "ERDATUTC", "ERNAM", "ETAG", "GLTRPUTC", "GLTRSUTC", "GSTRPUTC", "GSTRSUTC", _
             "OBJNR", "PERSONRESPONSIBLEINITIALS", "PRIOKX", "TEXTETAG", "WAWRK", "IW33_STATUS"
            MapRawOrderHeaderFieldName = vbNullString
        Case Else
            MapRawOrderHeaderFieldName = sourceName
    End Select
End Function


Private Sub WriteJsonArrayToSheet(ByVal sheetName As String, ByVal arr As Object, ByVal aufnr As String)
    Dim cols As Object: Set cols = CreateObject("Scripting.Dictionary")
    Dim normalizedRows As Collection
    Dim normalizedItem As Object
    Dim i As Long, r As Long, c As Long
    Dim itm As Object, k As Variant
    Dim mappedName As String

    If StrComp(sheetName, WS_RAW_ORDRE_OPERATIONS, vbTextCompare) = 0 Or _
       StrComp(sheetName, WS_RAW_ORDRE_OBJECTS, vbTextCompare) = 0 Or _
       StrComp(sheetName, WS_RAW_ORDRE_ATTACHMENTS, vbTextCompare) = 0 Then
        Set normalizedRows = New Collection

        For i = 1 To arr.Count
            Set itm = arr(i)
            Set normalizedItem = CreateObject("Scripting.Dictionary")

            If TypeName(itm) = "Dictionary" Then
                For Each k In itm.Keys
                    If IsScalar(itm(k)) Then
                        If StrComp(sheetName, WS_RAW_ORDRE_OPERATIONS, vbTextCompare) = 0 Then
                            mappedName = MapRawOrderOperationFieldName(CStr(k))
                        ElseIf StrComp(sheetName, WS_RAW_ORDRE_OBJECTS, vbTextCompare) = 0 Then
                            mappedName = MapRawOrderObjectFieldName(CStr(k))
                        Else
                            mappedName = MapRawOrderAttachmentFieldName(CStr(k))
                        End If
                        If Len(mappedName) > 0 Then
                            If Not normalizedItem.Exists(mappedName) Then
                                normalizedItem.Add mappedName, CoerceValue(itm(k))
                            End If
                        End If
                    End If
                Next
            End If

            If Not normalizedItem.Exists("Order_number") Then normalizedItem.Add "Order_number", aufnr
            normalizedRows.Add normalizedItem
        Next i

        ' Build union of normalized scalar fields across all rows.
        For i = 1 To normalizedRows.Count
            Set normalizedItem = normalizedRows(i)
            For Each k In normalizedItem.Keys
                If Not cols.Exists(CStr(k)) Then cols.Add CStr(k), cols.Count + 1
            Next
        Next i

        If cols.Count = 0 Then
            modUtil.WriteTableToSheetAppend sheetName, Empty, cols
            Exit Sub
        End If

        Dim opRows() As Variant
        ReDim opRows(1 To normalizedRows.Count, 1 To cols.Count)

        For r = 1 To normalizedRows.Count
            Set normalizedItem = normalizedRows(r)
            c = 0
            For Each k In cols.Keys
                c = c + 1
                If normalizedItem.Exists(CStr(k)) Then
                    opRows(r, c) = normalizedItem(CStr(k))
                Else
                    opRows(r, c) = Empty
                End If
            Next
        Next r

        modUtil.WriteTableToSheetAppend sheetName, opRows, cols

        If StrComp(sheetName, WS_RAW_ORDRE_ATTACHMENTS, vbTextCompare) = 0 Then
            ApplyHyperlinksToColumn sheetName, "Original"
        End If

        Exit Sub
    End If

    
    
    ' Union af skalarfelter p� tv�rs af alle poster
    For i = 1 To arr.Count
        Set itm = arr(i)
        If TypeName(itm) = "Dictionary" Then
            For Each k In itm.Keys
                If IsScalar(itm(k)) Then
                    If Not cols.Exists(CStr(k)) Then cols.Add CStr(k), cols.Count + 1
                End If
            Next
        End If
    Next

    If Not cols.Exists("AUFNR") Then cols.Add "AUFNR", cols.Count + 1

    If arr.Count = 0 Then
        modUtil.WriteTableToSheetAppend sheetName, Empty, cols
        Exit Sub
    End If

    If cols.Count = 0 Then
        modUtil.WriteTableToSheetAppend sheetName, Empty, cols
        Exit Sub
    End If

    Dim rows() As Variant
    ReDim rows(1 To arr.Count, 1 To cols.Count)

    For r = 1 To arr.Count
        Set itm = arr(r)
        c = 0
        For Each k In cols.Keys
            c = c + 1
            If CStr(k) = "AUFNR" Then
                rows(r, c) = aufnr
            ElseIf TypeName(itm) = "Dictionary" And itm.Exists(k) Then
                rows(r, c) = CoerceValue(itm(k))
            Else
                rows(r, c) = Empty
            End If
        Next
    Next

    modUtil.WriteTableToSheetAppend sheetName, rows, cols
End Sub

Private Function MapRawOrderOperationFieldName(ByVal sourceName As String) As String
    Select Case Trim$(sourceName)
        Case "ActualHours"
            MapRawOrderOperationFieldName = "Actual_Hours"
        Case "Aufnr"
            MapRawOrderOperationFieldName = "Order_number"
        Case "Plnnr"
            MapRawOrderOperationFieldName = "Task_LstGrp"
        Case "Plnal"
            MapRawOrderOperationFieldName = "GrpCr"
        Case "Plnty"
            MapRawOrderOperationFieldName = "Typ"
        Case "Vornr"
            MapRawOrderOperationFieldName = "Act"
        Case "ShortText"
            MapRawOrderOperationFieldName = "Operation_Description"
        Case "Anzzl"
            MapRawOrderOperationFieldName = "No"
        Case "Steus"
            MapRawOrderOperationFieldName = "Ctrl"
        Case "Arbpl"
            MapRawOrderOperationFieldName = "Work_Ctr"
        Case "Arbei"
            MapRawOrderOperationFieldName = "Work"
        Case "Arbeh"
            MapRawOrderOperationFieldName = "Work_unit"
        Case "Lifnr"
            MapRawOrderOperationFieldName = "Supplier"
        Case "LongText"
            MapRawOrderOperationFieldName = "Operation_Long_Text"
        Case "StandardTextKey", "Plnkn", "Objnr", "Zaehl", "Aufpl", "Aplzl", "Larnt", "Pernr", "Ktsch", "Tplnr", _
             "Aedat", "Aezeit", "AedatUtc", "LatestScheduledFinishUTC", "EarliestScheduledStartUTC", "LatestScheduledStartUTC", _
             "EarliestScheduledFinishUTC", "StartConstrainKey", "FinishConstrainKey", "StartConstrainText", "StartConstrainUtc", _
             "FinishConstrainText", "FinishConstrainUtc", "TextEtag", "Etag", "Longtext", "UserStatusLong", "UserStatusShort", _
             "PersonResponsibleInitials", "MasterOperationObjectNumber", "AUFNR"
            MapRawOrderOperationFieldName = vbNullString
        Case Else
            MapRawOrderOperationFieldName = sourceName
    End Select
End Function

Private Function MapRawOrderAttachmentFieldName(ByVal sourceName As String) As String
    Select Case Trim$(sourceName)
        Case "Act", "Vornr"
            MapRawOrderAttachmentFieldName = "Act"
        Case "Url"
            MapRawOrderAttachmentFieldName = "Original"
        Case "DocumentType"
            MapRawOrderAttachmentFieldName = "Document_Type"
        Case "DocumentNumber"
            MapRawOrderAttachmentFieldName = "Document"
        Case "Description"
            MapRawOrderAttachmentFieldName = "Description"
        Case "AUFNR"
            MapRawOrderAttachmentFieldName = "Order_number"
        Case "Tplnr", "Objnr", "LongText", "Laboratory", "DocumentVersion", "DocumentPart"
            MapRawOrderAttachmentFieldName = vbNullString
        Case Else
            MapRawOrderAttachmentFieldName = sourceName
    End Select
End Function

Private Sub ApplyHyperlinksToColumn(ByVal sheetName As String, ByVal headerName As String)
    Dim ws As Worksheet
    Dim lastCol As Long
    Dim targetCol As Long
    Dim lastRow As Long
    Dim r As Long
    Dim cell As Range
    Dim address As String

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    For targetCol = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(1, targetCol).Value)), headerName, vbTextCompare) = 0 Then Exit For
    Next targetCol
    If targetCol > lastCol Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, targetCol).End(xlUp).Row
    If lastRow < 2 Then Exit Sub

    For r = 2 To lastRow
        Set cell = ws.Cells(r, targetCol)
        address = Trim$(CStr(cell.Value))
        If Len(address) > 0 Then
            If LCase$(Left$(address, 7)) = "http://" Or LCase$(Left$(address, 8)) = "https://" Or LCase$(Left$(address, 7)) = "file://" Then
                On Error Resume Next
                If cell.Hyperlinks.Count > 0 Then cell.Hyperlinks.Delete
                ws.Hyperlinks.Add Anchor:=cell, Address:=address, TextToDisplay:=address
                On Error GoTo 0
            End If
        End If
    Next r
End Sub

Private Function MapRawOrderObjectFieldName(ByVal sourceName As String) As String
    Select Case Trim$(sourceName)
        Case "FunctionalLocationObjectNumber"
            MapRawOrderObjectFieldName = "FL_Obj_nr"
        Case "Equnr"
            MapRawOrderObjectFieldName = "Equipment"
        Case "Tplnr"
            MapRawOrderObjectFieldName = "Functional_loc"
        Case "Pltxt"
            MapRawOrderObjectFieldName = "Functional_loc_Desc"
        Case "Aufnr"
            MapRawOrderObjectFieldName = "Order_number"
        Case "NewNotificationText", "DefaultNotificationLink", "Etag", "Objnr", "NewNotificationType", "Obknr", "Obzae", _
             "Ihnum", "Bautl", "Iloan", "Sortf", "Bearb", "Objvw", "Sernr", "Matnr", "Datum", "Eqsnr", "Taser", "Uii", _
             "Matktx", "Eqtxt", "Bautx", "Iwerk", "Qmtxt", "Qmart", "Qmknz", "Dbknz", "OObjnr", "Nodelflg", "DatumUtc", "AUFNR"
            MapRawOrderObjectFieldName = vbNullString
        Case Else
            MapRawOrderObjectFieldName = sourceName
    End Select
End Function


' ----------------- Hj�lpere -----------------

Private Function HasKey(ByVal dict As Object, ByVal key As String) As Boolean
    On Error Resume Next: HasKey = dict.Exists(key): On Error GoTo 0
End Function

Private Function IsScalar(ByVal v As Variant) As Boolean
    If IsObject(v) Then
        IsScalar = False
    Else
        IsScalar = True
    End If
End Function

' Konverter v�rdier p�nt � inkl. OData v2 /Date(�)/ til ISO / Excel-dato
Private Function CoerceValue(ByVal v As Variant) As Variant
    If IsObject(v) Then
        CoerceValue = TypeName(v)  ' fx "Dictionary"
        Exit Function
    End If

    If IsEmpty(v) Or IsNull(v) Then
        CoerceValue = vbNullString
        Exit Function
    End If

    Dim s As String
    s = CStr(v)

    ' OData v2 DateTime ? "/Date(1758889449000)/" ? konverter til Excel-dato (valgfrit)
    If Left$(s, 6) = "/Date(" And Right$(s, 2) = ")/" Then
        Dim ms As Double
        ms = CDbl(Mid$(s, 7, Len(s) - 8))  ' milliseconds since epoch 1970-01-01  '
        ' Excel-dato = (epoch+ms/86400000) + forskydning fra 1899 til 1970
        CoerceValue = CDate(#1/1/1970# + ms / 86400000#)
        Exit Function
    End If

    CoerceValue = v
End Function
