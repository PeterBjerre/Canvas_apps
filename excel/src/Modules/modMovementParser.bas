Option Explicit

Public Function BuildMovementsUrlForOrder(ByVal aufnr As String) As String
    Dim safeAufnr As String
    Dim filterExpr As String

    safeAufnr = Replace(aufnr, "'", "''")
    filterExpr = "WorkOrderNumber eq '" & safeAufnr & "' and (MovementType eq '" & MOVEMENT_TYPE_ISSUE & "' or MovementType eq '" & MOVEMENT_TYPE_RETURN & "')"

    BuildMovementsUrlForOrder = INVENTORY_BASE_URL & INVENTORY_MOVEMENTS_ENTITY_SET & "?$filter=" & filterExpr & "&$format=json"
End Function

Public Sub ParseMovementsFromUrl(ByVal url As String, ByVal aufnr As String)
    Dim allRows As Collection
    Dim pageRoot As Object
    Dim pageRows As Collection
    Dim nextUrl As String
    Dim i As Long

    Set allRows = New Collection
    nextUrl = url

    Do While Len(nextUrl) > 0
        Set pageRoot = HttpGetJson(nextUrl)
        Set pageRows = ExtractMovementRows(pageRoot)

        If Not pageRows Is Nothing Then
            For i = 1 To pageRows.Count
                allRows.Add pageRows(i)
            Next i
        End If

        nextUrl = GetNextUrl(pageRoot)
    Loop

    If allRows.Count > 0 Then
        WriteMovementsToSheet WS_RAW_ORDRE_COMPONENTS, allRows, aufnr
    End If
End Sub

Public Sub ParseMovementsJSON(ByVal root As Object, ByVal aufnr As String)
    Dim rows As Collection

    Set rows = ExtractMovementRows(root)
    If rows Is Nothing Then Exit Sub
    If rows.Count = 0 Then Exit Sub

    WriteMovementsToSheet WS_RAW_ORDRE_COMPONENTS, rows, aufnr
End Sub

Private Function GetNextUrl(ByVal root As Object) As String
    Dim d As Object
    Dim rawNext As String

    If root Is Nothing Then Exit Function

    If HasKey(root, "d") Then
        Set d = root("d")
    Else
        Set d = root
    End If

    If d Is Nothing Then Exit Function
    If TypeName(d) <> "Dictionary" Then Exit Function
    If Not HasKey(d, "__next") Then Exit Function

    rawNext = CStr(d("__next"))
    GetNextUrl = ToAbsoluteInventoryUrl(rawNext)
End Function

Private Function ToAbsoluteInventoryUrl(ByVal rawUrl As String) As String
    Dim rootUrl As String

    If Len(rawUrl) = 0 Then Exit Function

    If InStr(1, rawUrl, "http", vbTextCompare) = 1 Then
        ToAbsoluteInventoryUrl = rawUrl
        Exit Function
    End If

    rootUrl = Left$(INVENTORY_BASE_URL, InStr(1, INVENTORY_BASE_URL, "/sap/opu/odata/", vbTextCompare) - 1)

    If Left$(rawUrl, 1) = "/" Then
        ToAbsoluteInventoryUrl = rootUrl & rawUrl
    Else
        ToAbsoluteInventoryUrl = INVENTORY_BASE_URL & rawUrl
    End If
End Function

Private Function ExtractMovementRows(ByVal root As Object) As Collection
    Dim d As Object
    Dim results As Object

    Set ExtractMovementRows = New Collection

    If root Is Nothing Then Exit Function

    If HasKey(root, "d") Then
        Set d = root("d")
    Else
        Set d = root
    End If

    If d Is Nothing Then Exit Function

    If TypeName(d) = "Dictionary" And HasKey(d, "results") Then
        Set results = d("results")
        AppendRowsFromVariant ExtractMovementRows, results
    Else
        AppendRowsFromVariant ExtractMovementRows, d
    End If
End Function

Private Sub AppendRowsFromVariant(ByRef acc As Collection, ByVal v As Variant)
    Dim i As Long

    If IsObject(v) Then
        Select Case TypeName(v)
            Case "Collection"
                For i = 1 To v.Count
                    If IsObject(v(i)) Then acc.Add v(i)
                Next i
            Case "Dictionary"
                acc.Add v
        End Select
    End If
End Sub

Private Sub WriteMovementsToSheet(ByVal sheetName As String, ByVal arr As Collection, ByVal aufnr As String)
    Dim cols As Object
    Dim normalizedRows As Collection
    Dim normalizedItem As Object
    Dim rows() As Variant
    Dim itm As Object
    Dim k As Variant
    Dim mappedName As String
    Dim r As Long
    Dim c As Long

    Set cols = CreateObject("Scripting.Dictionary")
    Set normalizedRows = New Collection

    For r = 1 To arr.Count
        Set itm = arr(r)
        Set normalizedItem = CreateObject("Scripting.Dictionary")

        If TypeName(itm) = "Dictionary" Then
            For Each k In itm.Keys
                If IsScalar(itm(k)) Then
                    mappedName = MapRawOrderComponentFieldName(CStr(k))
                    If Len(mappedName) > 0 Then
                        If Not normalizedItem.Exists(mappedName) Then
                            normalizedItem.Add mappedName, CoerceValue(itm(k))
                        End If
                    End If
                End If
            Next k
        End If

        If normalizedItem.Exists("Order_number") Then
            normalizedItem("Order_number") = aufnr
        Else
            normalizedItem.Add "Order_number", aufnr
        End If

        normalizedRows.Add normalizedItem

        For Each k In normalizedItem.Keys
            If Not cols.Exists(CStr(k)) Then cols.Add CStr(k), cols.Count + 1
        Next k
    Next r

    If cols.Count = 0 Then
        modUtil.WriteTableToSheetAppend sheetName, Empty, cols
        Exit Sub
    End If

    ReDim rows(1 To normalizedRows.Count, 1 To cols.Count)

    For r = 1 To normalizedRows.Count
        Set normalizedItem = normalizedRows(r)
        c = 0
        For Each k In cols.Keys
            c = c + 1
            If normalizedItem.Exists(CStr(k)) Then
                rows(r, c) = normalizedItem(CStr(k))
            Else
                rows(r, c) = Empty
            End If
        Next k
    Next r

    modUtil.WriteTableToSheetAppend sheetName, rows, cols
End Sub

Private Function MapRawOrderComponentFieldName(ByVal sourceName As String) As String
    Select Case Trim$(sourceName)
        Case "AUFNR"
            MapRawOrderComponentFieldName = "Order_number"
        Case "MaterialDocument", "MaterialDocumentYear", "MaterialDocumentItem", "WorkOrderNumber", "PostingDate", "Plant", _
             "StorageLocation", "DebitCreditIndicator", "AmountInLocalCurrency", "Currency", "UserName", "ReversalMovementType"
            MapRawOrderComponentFieldName = vbNullString
        Case "MaterialNumber"
            MapRawOrderComponentFieldName = "Material"
        Case "Quantity"
            MapRawOrderComponentFieldName = "Quantity"
        Case "BaseUnitOfMeasure"
            MapRawOrderComponentFieldName = "Un"
        Case "MaterialDescription"
            MapRawOrderComponentFieldName = "Component_Description"
        Case "MovementType"
            MapRawOrderComponentFieldName = "Movement_Type"
        Case "MovementTypeText"
            MapRawOrderComponentFieldName = "Movement_Type_Text"
        Case Else
            MapRawOrderComponentFieldName = sourceName
    End Select
End Function

Private Function HasKey(ByVal dict As Object, ByVal key As String) As Boolean
    On Error Resume Next
    HasKey = dict.Exists(key)
    On Error GoTo 0
End Function

Private Function IsScalar(ByVal v As Variant) As Boolean
    If IsObject(v) Then
        IsScalar = False
    Else
        IsScalar = True
    End If
End Function

Private Function CoerceValue(ByVal v As Variant) As Variant
    If IsObject(v) Then
        CoerceValue = TypeName(v)
        Exit Function
    End If

    If IsEmpty(v) Or IsNull(v) Then
        CoerceValue = vbNullString
        Exit Function
    End If

    If VarType(v) = vbString Then
        Dim s As String
        s = CStr(v)

        If Left$(s, 6) = "/Date(" Then
            Dim p1 As Long
            Dim p2 As Long
            Dim ms As Double

            p1 = InStr(1, s, "(")
            p2 = InStr(1, s, ")")
            If p1 > 0 And p2 > p1 Then
                ms = CDbl(Val(Mid$(s, p1 + 1, p2 - p1 - 1)))
                CoerceValue = CDate(#1/1/1970# + (ms / 86400000#))
                Exit Function
            End If
        End If
    End If

    CoerceValue = v
End Function