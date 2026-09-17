Option Explicit

Public Sub ParseOrderXML(xml As Object, ByVal Aufnr As String)
    Dim entry As Object
    Set entry = xml.SelectSingleNode("/*[local-name()='entry']")
    If entry Is Nothing Then
        MsgBox "Ingen data fundet for ordre " & Aufnr, vbExclamation, APP_TITLE
        Exit Sub
    End If

    ' Header (prefiks-fri, relativ ift. entry)
    Dim props As Object
    Set props = entry.SelectSingleNode(".//*[local-name()='content']/*[local-name()='properties']")
    If Not props Is Nothing Then
        WriteSingleEntity WS_RAW_ORDRE_HEADER, props
    End If

    ' Subfeeds (rel-navne = pr�cis som dit dump)
    ExtractSubFeed entry, "WorkOrderOperationsSet", WS_RAW_ORDRE_OPERATIONS
    ExtractSubFeed entry, "Objects", WS_RAW_ORDRE_OBJECTS

    ' Hvis du ogs� vil have disse med:
    ExtractSubFeed entry, "Attachment", WS_RAW_ORDRE_ATTACHMENTS
End Sub


Private Sub ExtractSubFeed(entry As Object, relName As String, sheetName As String)
    ' 0) Find <link> for relationen (prefiks-frit)
    Dim linkNode As Object
    Set linkNode = entry.SelectSingleNode( _
        "*[local-name()='link' and @rel='http://schemas.microsoft.com/ado/2007/08/dataservices/related/" & relName & "']")
    If linkNode Is Nothing Then Exit Sub

    ' 1) Pr�v inline FEED
    Dim feed As Object
    Set feed = linkNode.SelectSingleNode("/*[local-name()='inline']/*[local-name()='feed']")

    ' 2) Hvis ikke feed, pr�v inline ENTRY (1:1)
    If feed Is Nothing Then
        Dim inlineEntry As Object
        Set inlineEntry = linkNode.SelectSingleNode("/*[local-name()='inline']/*[local-name()='entry']")
        If Not inlineEntry Is Nothing Then
            ' Wrap entry i syntetisk feed, s� vi kan genbruge feed-parseren
            Dim dom As Object
            Set dom = CreateObject("MSXML2.DOMDocument.6.0")
            dom.LoadXML "<feed xmlns='http://www.w3.org/2005/Atom'></feed>"
            dom.DocumentElement.appendChild dom.importNode(inlineEntry, True)
            Set feed = dom.DocumentElement
        End If
    End If

    ' 3) Hvis inline mangler helt, f�lg linkets href
    If feed Is Nothing Then
        Dim hrefAttr As Object, href As String
        Set hrefAttr = linkNode.Attributes.getNamedItem("href")
        If hrefAttr Is Nothing Then Exit Sub

        href = MakeAbsoluteUrl(CStr(hrefAttr.Text))
        Debug.Print "FOLLOW HREF:", href

        Dim xml As Object
        Set xml = HttpGetAsXml(href)   ' henter eksternt

        Dim target As Object
        If Not xml.SelectSingleNode("/*[local-name()='feed']") Is Nothing Then
            Set target = xml.SelectSingleNode("/*[local-name()='feed']")
        Else
            ' Eksternt svar var et entry ? wrap i syntetisk feed
            Dim dom2 As Object, e2 As Object
            Set dom2 = CreateObject("MSXML2.DOMDocument.6.0")
            dom2.LoadXML "<feed xmlns='http://www.w3.org/2005/Atom'></feed>"
            Set e2 = xml.SelectSingleNode("/*[local-name()='entry']")
            If Not e2 Is Nothing Then dom2.DocumentElement.appendChild dom2.importNode(e2, True)
            Set target = dom2.DocumentElement
        End If

        Dim rowsX As Variant, colsX As Object
        ParseODataFeed target, rowsX, colsX
        modUtil.WriteTableToSheet sheetName, rowsX, colsX
        Exit Sub
    End If

    ' 4) Vi har et FEED (rigtigt eller syntetisk) ? parse & skriv
    Dim rows As Variant, cols As Object
    ParseODataFeed feed, rows, cols
    modUtil.WriteTableToSheet sheetName, rows, cols
End Sub

Private Function MakeAbsoluteUrl(ByVal href As String) As String
    ' Byg absolut URL af relativen href fra <link>, mht. slut/foranstillet "/"
    If Len(href) = 0 Then
        MakeAbsoluteUrl = ""
    ElseIf InStr(1, href, "http", vbTextCompare) = 1 Then
        MakeAbsoluteUrl = href
    ElseIf Right$(BASE_URL, 1) = "/" And Left$(href, 1) = "/" Then
        MakeAbsoluteUrl = Left$(BASE_URL, Len(BASE_URL) - 1) & href
    Else
        MakeAbsoluteUrl = BASE_URL & href
    End If
End Function

Private Sub WriteSingleEntity(sheetName As String, props As Object)
    Dim cols As Object: Set cols = CreateObject("Scripting.Dictionary")
    Dim rows() As Variant, cnt As Long
    Dim p As Object

    ' T�l felter
    For Each p In props.ChildNodes
        If p.NodeType = 1 Then cnt = cnt + 1
    Next
    If cnt = 0 Then
        modUtil.WriteTableToSheet sheetName, Empty, cols
        Exit Sub
    End If

    ' Dimension�r og fyld
    ReDim rows(1 To 1, 1 To cnt)
    Dim i As Long: i = 0
    For Each p In props.ChildNodes
        If p.NodeType = 1 Then
            i = i + 1
            cols.Add p.BaseName, i
            rows(1, i) = p.Text
        End If
    Next

    modUtil.WriteTableToSheet sheetName, rows, cols
End Sub

