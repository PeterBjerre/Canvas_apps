Attribute VB_Name = "modODataParser"
Option Explicit

' Parser en ATOM feed-node til (rows, cols)
Public Sub ParseODataFeed(ByVal xmlNode As Object, ByRef rows As Variant, ByRef cols As Object)
    Dim entries As Object
    Set entries = xmlNode.SelectNodes(".//*[local-name()='entry']")

    Set cols = CreateObject("Scripting.Dictionary")

    Dim e As Object, p As Object, colName As String
    For Each e In entries
        Dim props As Object
        Set props = e.SelectSingleNode(".//*[local-name()='content']/*[local-name()='properties']")
        If props Is Nothing Then GoTo NextE
        For Each p In props.ChildNodes
            If p.NodeType = 1 Then
                colName = p.BaseName: If Len(colName) = 0 Then colName = p.nodeName
                If Not cols.Exists(colName) Then cols.Add colName, cols.Count + 1
            End If
        Next p
NextE:
    Next e

    Dim colCount As Long: colCount = cols.Count
    If colCount = 0 Then rows = Empty: Exit Sub

    Dim tmpRows() As Variant
    ReDim tmpRows(1 To Application.Max(1, entries.Length), 1 To colCount)

    Dim i As Long: i = 0
    For Each e In entries
        Dim props2 As Object
        Set props2 = e.SelectSingleNode(".//*[local-name()='content']/*[local-name()='properties']")
        If props2 Is Nothing Then GoTo NextE2

        i = i + 1
        Dim c As Long
        For c = 1 To colCount: tmpRows(i, c) = Empty: Next c

        Dim q As Object, nm As String, idx As Long, txt As String
        For Each q In props2.ChildNodes
            If q.NodeType = 1 Then
                nm = q.BaseName: If Len(nm) = 0 Then nm = q.nodeName
                If cols.Exists(nm) Then
                    idx = cols(nm)
                    If q.Attributes Is Nothing Then
                        txt = q.Text
                    Else
                        Dim attr As Object
                        Set attr = q.Attributes.getNamedItem("m:null")
                        If Not attr Is Nothing And LCase$(attr.Text) = "true" Then
                            txt = vbNullString
                        Else
                            txt = q.Text
                        End If
                    End If
                    tmpRows(i, idx) = txt
                End If
            End If
        Next q
NextE2:
    Next e

    If i = 0 Then
        rows = Empty
    Else
        rows = tmpRows
    End If
End Sub

' (valgfrit – bruges hvis du senere følger server-driven paging på rene feeds)
Public Function GetNextLink(ByVal xmlDoc As Object) As String
    Dim nextNode As Object
    Set nextNode = xmlDoc.SelectSingleNode("/*[local-name()='feed']/*[local-name()='link' and @rel='next']/@href")
    If nextNode Is Nothing Then
        GetNextLink = vbNullString
    Else
        Dim href As String: href = CStr(nextNode.Text)
        If InStr(1, href, "http", vbTextCompare) = 1 Then
            GetNextLink = href
        Else
            If Right$(BASE_URL, 1) = "/" And Left$(href, 1) = "/" Then
                GetNextLink = Left$(BASE_URL, Len(BASE_URL) - 1) & href
            Else
                GetNextLink = BASE_URL & href
            End If
        End If
    End If
End Function
