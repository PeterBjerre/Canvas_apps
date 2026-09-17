Attribute VB_Name = "modWriters"
Option Explicit

Public Sub FetchEntitySetToSheet(ByVal entitySet As String, ByVal filterExpr As String, _
                                 ByVal sheetName As String, ByVal optAennrList As Collection)

    Dim url As String: url = BASE_URL & entitySet
    If Len(filterExpr) > 0 Then url = url & "?Sfilter=" & filterExpr

    Dim allRows As Variant, allCols As Object
    Set allCols = CreateObject("Scripting.Dictionary")

    Dim nextUrl As String: nextUrl = url
    Do While Len(nextUrl) > 0
        Dim xmlDoc As Object
        Set xmlDoc = modHttpOData.HttpGetAsXml(nextUrl)

        Dim rows As Variant, cols As Object
        modODataParser.ParseODataFeed xmlDoc, rows, cols

        Dim k As Variant
        For Each k In cols.Keys
            If Not allCols.Exists(k) Then allCols.Add k, allCols.Count + 1
        Next k

        allRows = modUtil.AppendRows(allRows, rows)
        nextUrl = modODataParser.GetNextLink(xmlDoc)
    Loop

    modUtil.WriteTableToSheet sheetName, allRows, allCols

    If Not optAennrList Is Nothing And LCase$(entitySet) = LCase$(ES_HDR) Then
        modUtil.CollectDistinctValues optAennrList, allRows, allCols, "Aennr"
    End If
End Sub

Public Function BuildActionLogFilter(ByVal baseFilter As String, ByVal aennrList As Collection) As String
    Dim i As Long, parts As String
    If Not aennrList Is Nothing Then
        For i = 1 To Application.Min(8, aennrList.Count)
            parts = parts & IIf(Len(parts) = 0, "", " or ") & "Aennr eq '" & modUtil.UrlEncode(CStr(aennrList(i))) & "'"
        Next i
    End If
    If Len(parts) > 0 Then
        BuildActionLogFilter = "(" & baseFilter & ") and (" & parts & ")"
    Else
        BuildActionLogFilter = baseFilter
    End If
End Function

