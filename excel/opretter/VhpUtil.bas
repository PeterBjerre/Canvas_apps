Attribute VB_Name = "VhpUtil"
Option Explicit
'==============================================================================
' VhpUtil - smaa hjaelpere, som resten af opretteren bruger.
'
' Ingen af dem roerer SAP, ark eller filer. Derfor kan de afproeves uden
' Excel: tests/test_vba_runner.py koerer dem i LibreOffice.
'==============================================================================

' Dansk tekst til skaermen. Kildekoden er ren ASCII (VBA-editoren laeser
' .bas-filer i Windows' tegnsaet), saa bogstaverne skrives som koder:
'
'   {ae} {oe} {aa}  ->  ae oe aa som rigtige bogstaver (og {AE} {OE} {AA})
'   {e}             ->  e med accent, som i "en" = 1
'   {-}             ->  tankestreg
'   {...}           ->  ellipse
Public Function Dk(ByVal s As String) As String
    s = Replace(s, "{ae}", ChrW$(230))
    s = Replace(s, "{oe}", ChrW$(248))
    s = Replace(s, "{aa}", ChrW$(229))
    s = Replace(s, "{AE}", ChrW$(198))
    s = Replace(s, "{OE}", ChrW$(216))
    s = Replace(s, "{AA}", ChrW$(197))
    s = Replace(s, "{e}", ChrW$(233))
    s = Replace(s, "{-}", ChrW$(8211))
    s = Replace(s, "{...}", ChrW$(8230))
    Dk = s
End Function

'==============================================================================
' JSON-vaerdier
'
' VBA-JSON giver Scripting.Dictionary for objekter, Collection for arrays og
' Null for null. At LAESE en noegle, der ikke findes, i en Dictionary OPRETTER
' den (med Empty) - derfor gaar alle opslag gennem Exists her.
'==============================================================================
Public Function JHas(ByVal d As Object, ByVal key As String) As Boolean
    If d Is Nothing Then Exit Function
    If Not d.Exists(key) Then Exit Function
    If IsObject(d(key)) Then
        JHas = Not (d(key) Is Nothing)
        Exit Function
    End If
    If IsNull(d(key)) Or IsEmpty(d(key)) Then Exit Function
    If VarType(d(key)) = vbString Then
        JHas = Len(Trim$(d(key))) > 0
    Else
        JHas = True
    End If
End Function

' Tekst. Tom streng for en manglende noegle, null og objekter.
Public Function JStr(ByVal d As Object, ByVal key As String) As String
    If d Is Nothing Then Exit Function
    If Not d.Exists(key) Then Exit Function
    If IsObject(d(key)) Then Exit Function
    If IsNull(d(key)) Or IsEmpty(d(key)) Then Exit Function
    If VarType(d(key)) = vbBoolean Then
        JStr = IIf(d(key), "true", "false")
    ElseIf VarType(d(key)) = vbString Then
        JStr = d(key)
    Else
        ' Et tal. Str$ giver punktum som decimaltegn uanset Windows' sprog,
        ' og Trim$ fjerner det foranstillede mellemrum, Str$ laver.
        JStr = Trim$(Str$(d(key)))
    End If
End Function

Public Function JNum(ByVal d As Object, ByVal key As String, Optional ByVal dflt As Double = 0) As Double
    JNum = dflt
    If Not JHas(d, key) Then Exit Function
    If VarType(d(key)) = vbString Then
        If IsNumeric(d(key)) Then JNum = Val(Replace(d(key), ",", "."))
    ElseIf VarType(d(key)) <> vbBoolean Then
        JNum = CDbl(d(key))
    End If
End Function

Public Function JLng(ByVal d As Object, ByVal key As String, Optional ByVal dflt As Long = 0) As Long
    JLng = CLng(JNum(d, key, dflt))
End Function

Public Function JBool(ByVal d As Object, ByVal key As String) As Boolean
    If Not JHas(d, key) Then Exit Function
    If VarType(d(key)) = vbBoolean Then
        JBool = d(key)
    Else
        Select Case UCase$(Trim$(CStr(d(key))))
            Case "TRUE", "YES", "JA", "1", "X"
                JBool = True
        End Select
    End If
End Function

Public Function JObj(ByVal d As Object, ByVal key As String) As Object
    If d Is Nothing Then Exit Function
    If Not d.Exists(key) Then Exit Function
    If IsObject(d(key)) Then Set JObj = d(key)
End Function

' Altid en Collection - tom, hvis noeglen mangler eller er null.
Public Function JList(ByVal d As Object, ByVal key As String) As Collection
    Dim o As Object
    Set o = JObj(d, key)
    If o Is Nothing Then
        Set JList = New Collection
    ElseIf TypeName(o) = "Collection" Then
        Set JList = o
    Else
        Set JList = New Collection
    End If
End Function

Public Function NewDict() As Object
    Set NewDict = CreateObject("Scripting.Dictionary")
End Function

'==============================================================================
' Tekst
'==============================================================================

' Trimmet og afkortet til SAP-feltets laengde.
Public Function Clip(ByVal s As String, ByVal maxLen As Long) As String
    s = Trim$(s)
    If Len(s) > maxLen Then s = Left$(s, maxLen)
    Clip = s
End Function

' Er strengen tom eller kun mellemrum?
Public Function IsBlank(ByVal s As String) As Boolean
    IsBlank = (Len(Trim$(s)) = 0)
End Function

' Windows-brugernavnet med store bogstaver, fx PKBJE.
Public Function UserName() As String
    UserName = UCase$(Environ$("USERNAME"))
End Function

'==============================================================================
' Datoer
'==============================================================================

' Lokal tid som ISO-tekst uden tidszone: 2026-10-02T11:05:12
Public Function IsoNow() As String
    IsoNow = IsoDateTime(Now)
End Function

Public Function IsoDateTime(ByVal d As Date) As String
    IsoDateTime = Format$(d, "yyyy-mm-dd") & "T" & Format$(d, "hh:nn:ss")
End Function

' "2027-09-20" -> dato. False, hvis teksten ikke er en gyldig dato.
Public Function TryParseYmd(ByVal s As String, ByRef d As Date) As Boolean
    Dim y As Long, m As Long, dd As Long

    s = Trim$(s)
    If Len(s) < 10 Then Exit Function
    If Mid$(s, 5, 1) <> "-" Or Mid$(s, 8, 1) <> "-" Then Exit Function
    If Not IsAllDigits(Left$(s, 4)) Then Exit Function
    If Not IsAllDigits(Mid$(s, 6, 2)) Then Exit Function
    If Not IsAllDigits(Mid$(s, 9, 2)) Then Exit Function

    y = CLng(Left$(s, 4))
    m = CLng(Mid$(s, 6, 2))
    dd = CLng(Mid$(s, 9, 2))
    If m < 1 Or m > 12 Or dd < 1 Or dd > 31 Then Exit Function

    d = DateSerial(y, m, dd)
    ' DateSerial(2027, 2, 31) giver 3. marts uden at sige noget.
    If Month(d) <> m Or Day(d) <> dd Then Exit Function
    TryParseYmd = True
End Function

' ISO-tidsstempel fra flowet (UTC, fx 2026-10-02T08:42:33Z) til lokal visning.
' Sommertid regnes ikke ud; visningen er kun til orientering.
Public Function IsoToDisplay(ByVal s As String) As String
    Dim d As Date
    If TryParseYmd(Left$(s, 10), d) Then
        IsoToDisplay = Format$(d, "dd-mm-yyyy")
        If Len(s) >= 16 And Mid$(s, 11, 1) = "T" Then
            IsoToDisplay = IsoToDisplay & " " & Mid$(s, 12, 5)
            If Right$(s, 1) = "Z" Then IsoToDisplay = IsoToDisplay & " UTC"
        End If
    Else
        IsoToDisplay = s
    End If
End Function

Public Function IsAllDigits(ByVal s As String) As Boolean
    Dim i As Long
    Dim c As String

    If Len(s) = 0 Then Exit Function
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If c < "0" Or c > "9" Then Exit Function
    Next i
    IsAllDigits = True
End Function
