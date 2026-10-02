Attribute VB_Name = "VhpItf"
Option Explicit
'==============================================================================
' VhpItf - langtekst fra appen (HTML) til SAPscript (ITF), som SAP uploader.
'
' Erstatter HtmlToSAPText / ConvertHtmlToSAPITF_Dynamic fra det gamle
' GUI-script. Formaterne er de samme - <H> for fed og <U> for understreget,
' som SAP-formularen SYSTEM kender - og ITF-filens hoved er ordret det gamle.
'
' Tre ting er anderledes, og de er rettelser:
'
'   1. Ingen VBScript.RegExp og ingen "htmlfile". Begge er Windows-
'      komponenter, Microsoft er ved at udfase (VBScript), og de kan ikke
'      afproeves uden for Windows. Teksten gennemgaas her tegn for tegn.
'   2. Punktopstillinger beholder deres niveau. Underpunkter blev foer til
'      linjer med "-" uden indrykning, saa man ikke kunne se, hvad der var
'      under hvad (docs/20, "underpunkter forsvinder"). Nummererede lister
'      faar numre.
'   3. HTML-tegnkoder som &amp; og &aelig; bliver til tegnet. Foer stod de
'      i SAP som "&amp;".
'
' Et "<" eller ">" i selve teksten ville SAPscript laese som starten paa et
' format. De skrives som de typografisk naesten ens tegn U+2039 og U+203A,
' der findes i Windows' tegnsaet.
'==============================================================================

Private Const LF As String = vbLf
' Indrykning for punktopstillinger skal overleve, at hver linje trimmes.
' Et tegn fra Unicodes private omraade bruges som markoer og erstattes til
' sidst af to mellemrum.
Private Const INDENT_CODE As Long = &HE000&
Private Const MAX_LINE As Long = 120
Private Const MAX_DEPTH As Long = 20

' HTML (eller ren tekst) -> SAP-tekst med <H>, <U> og </> og LF som linjeskift.
Public Function HtmlToSapText(ByVal html As String) As String
    Dim s As String
    Dim out As String
    Dim i As Long
    Dim j As Long
    Dim n As Long
    Dim tagText As String
    Dim tagName As String
    Dim closing As Boolean
    Dim runEnd As Long
    Dim depth As Long
    Dim listKind(1 To MAX_DEPTH) As String
    Dim listCount(1 To MAX_DEPTH) As Long

    s = Replace(html, vbCrLf, LF)
    s = Replace(s, vbCr, LF)
    If Len(s) = 0 Then Exit Function

    ' Ren tekst - fx en operations langtekst skrevet i et tekstfelt. Ingen
    ' tegnkoder afkodes: "&" i ren tekst er et "&".
    If Not LooksLikeHtml(s) Then
        HtmlToSapText = Finish(EscapeText(s))
        Exit Function
    End If

    n = Len(s)
    i = 1
    Do While i <= n
        If Mid$(s, i, 1) = "<" And IsTagStart(s, i) Then
            ' Kommentar <!-- ... -->
            If Mid$(s, i, 4) = "<!--" Then
                j = InStr(i + 4, s, "-->", vbBinaryCompare)
                If j = 0 Then Exit Do
                i = j + 3
            Else
                j = InStr(i + 1, s, ">", vbBinaryCompare)
                If j = 0 Then
                    out = out & EscapeText(Mid$(s, i))
                    Exit Do
                End If
                tagText = Mid$(s, i + 1, j - i - 1)
                closing = (Left$(tagText, 1) = "/")
                tagName = TagNameOf(tagText)
                i = j + 1

                Select Case tagName
                    Case "b", "strong"
                        out = out & IIf(closing, "</>", "<H>")
                    Case "u"
                        out = out & IIf(closing, "</>", "<U>")
                    Case "br"
                        ' Et <br> er altid et linjeskift - to i traek er en tom linje.
                        out = out & LF
                    Case "p"
                        ' Afsnit: en tom linje efter, som det gamle script gav.
                        out = SoftBreak(out)
                        If closing Then out = out & LF
                    Case "div", "tr", "table", "blockquote", "pre"
                        out = SoftBreak(out)
                    Case "h1", "h2", "h3", "h4", "h5", "h6"
                        If closing Then
                            out = SoftBreak(out & "</>")
                        Else
                            out = SoftBreak(out) & "<H>"
                        End If
                    Case "td", "th"
                        If closing Then out = out & " "
                    Case "ul", "ol"
                        If closing Then
                            If depth > 0 Then depth = depth - 1
                        ElseIf depth < MAX_DEPTH Then
                            depth = depth + 1
                            listKind(depth) = tagName
                            listCount(depth) = 0
                        End If
                        out = SoftBreak(out)
                    Case "li"
                        out = SoftBreak(out)
                        If Not closing Then out = out & ListMarker(depth, listKind, listCount)
                    Case "script", "style"
                        If Not closing Then
                            j = InStr(i, LCase$(s), "</" & tagName, vbBinaryCompare)
                            If j = 0 Then Exit Do
                            i = j
                        End If
                    Case Else
                        ' span, font, em, a ... fjernes, teksten bliver
                End Select
            End If
        Else
            ' En tekstbid frem til naeste "<", der starter et tag.
            runEnd = i
            Do While runEnd <= n
                If Mid$(s, runEnd, 1) = "<" Then
                    If IsTagStart(s, runEnd) Then Exit Do
                End If
                runEnd = runEnd + 1
            Loop
            out = out & EscapeText(CollapseRun(DecodeEntities(Mid$(s, i, runEnd - i))))
            i = runEnd
        End If
    Loop

    HtmlToSapText = Finish(out)
End Function

' Er der overhovedet tekst, efter formateringen er fjernet?
Public Function HasText(ByVal html As String) As Boolean
    Dim t As String
    t = HtmlToSapText(html)
    t = Replace(t, "<H>", "")
    t = Replace(t, "<U>", "")
    t = Replace(t, "</>", "")
    t = Replace(t, LF, "")
    HasText = Len(Trim$(t)) > 0
End Function

' ITF-linjerne uden filhoved: "* tekst", "*" for en tom linje, og lange linjer
' delt ved et mellemrum, som det gamle WriteSapItfTextLine gjorde.
'
' keepLeadingBreak: itemets langtekst. Starter HTML'en med et linjeskift,
' beholdes ET - samme regel som det gamle script (preserveLeadingBreak).
Public Function ItfBody(ByVal html As String, Optional ByVal keepLeadingBreak As Boolean = False) As Collection
    Dim body As New Collection
    Dim text As String
    Dim lines() As String
    Dim i As Long

    text = HtmlToSapText(html)
    If keepLeadingBreak And StartsWithBreak(html) Then text = LF & text

    lines = Split(text, LF)
    For i = LBound(lines) To UBound(lines)
        AddItfLine body, lines(i)
    Next i

    Set ItfBody = body
End Function

' Hele ITF-filen. Hovedet er ordret det, det gamle script skrev, og som SAP
' har taget imod. Filen skrives i Windows' tegnsaet (Print #), som SAP GUI
' forventer ved upload.
Public Sub WriteItfFile(ByVal path As String, ByVal html As String, _
                        Optional ByVal keepLeadingBreak As Boolean = False, _
                        Optional ByVal language As String = "E")
    Dim fileNum As Integer
    Dim body As Collection
    Dim line As Variant
    Dim failText As String

    Set body = ItfBody(html, keepLeadingBreak)

    On Error GoTo Failed
    fileNum = FreeFile
    Open path For Output As #fileNum
    Print #fileNum, "/HTEXT"
    Print #fileNum, "/:OBJECT"
    Print #fileNum, "/:NAME"
    Print #fileNum, "/:ID LTXT"
    Print #fileNum, "/:LANGUAGE " & language
    Print #fileNum, "/:FORM SYSTEM"
    Print #fileNum, "/:STYLE"
    Print #fileNum, "/:FIRST-USER"
    Print #fileNum, "/:FIRST-DATE"
    Print #fileNum, "/:FIRST-TIME"
    Print #fileNum, "/:LAST-USER"
    Print #fileNum, "/:LAST-DATE"
    Print #fileNum, "/:LAST-TIME"
    Print #fileNum, "/:TITLE"
    Print #fileNum, "/:TITLE1"
    Print #fileNum, "/:TITLE2"
    Print #fileNum, "/MTEXT"
    For Each line In body
        Print #fileNum, CStr(line)
    Next line
    Close #fileNum
    Exit Sub

Failed:
    ' Beskeden gemmes, og fejlhaandteringen afsluttes med Resume. En fejl
    ' INDE i en aktiv fejlhaandtering kan proceduren ikke selv fange.
    failText = Err.Description
    Resume CleanUp
CleanUp:
    On Error Resume Next
    Close #fileNum
    On Error GoTo 0
    Err.Raise vbObjectError + 1101, "VhpItf", _
        VhpUtil.Dk("Langtekstfilen kunne ikke skrives (") & path & "): " & failText
End Sub

'==============================================================================
' Indre
'==============================================================================

Private Sub AddItfLine(ByVal body As Collection, ByVal lineText As String)
    Dim splitPos As Long

    lineText = Replace(lineText, vbTab, " ")
    lineText = Replace(lineText, ChrW$(160), " ")
    lineText = RTrim$(lineText)

    If Len(lineText) = 0 Then
        body.Add "*"
        Exit Sub
    End If

    Do While Len(lineText) > MAX_LINE
        splitPos = InStrRev(Left$(lineText, MAX_LINE + 1), " ")
        If splitPos <= 0 Then splitPos = SafeHardSplit(lineText, MAX_LINE)
        body.Add "* " & Left$(lineText, splitPos)
        lineText = LTrim$(Mid$(lineText, splitPos + 1))
    Loop
    body.Add "* " & lineText
End Sub

' En linje uden mellemrum skal deles midt i et ord. Ikke midt i <H>, <U> eller
' </> - saa ville SAP se et halvt format.
Private Function SafeHardSplit(ByVal s As String, ByVal maxLen As Long) As Long
    Dim p As Long
    p = maxLen
    Dim lt As Long
    lt = InStrRev(Left$(s, p), "<")
    If lt > 0 And lt > p - 3 Then
        If InStr(lt, Left$(s, p), ">", vbBinaryCompare) = 0 Then p = lt - 1
    End If
    If p < 1 Then p = maxLen
    SafeHardSplit = p
End Function

' Er teksten HTML? Ja, hvis den har et sluttag ("</") eller et af de tags,
' rich text-felterne i appen og SharePoint laver. En operations langtekst
' skrevet som ren tekst kan godt indeholde "<Enter>" eller "< 5 bar" - det
' er tekst og ikke et tag.
Private Function LooksLikeHtml(ByVal s As String) As Boolean
    Dim known As Variant
    Dim i As Long

    s = LCase$(s)
    If InStr(1, s, "</", vbBinaryCompare) > 0 Then
        LooksLikeHtml = True
        Exit Function
    End If
    If InStr(1, s, "&nbsp;", vbBinaryCompare) > 0 Then
        LooksLikeHtml = True
        Exit Function
    End If

    known = Array("<br", "<p>", "<p ", "<div", "<span", "<b>", "<strong", "<u>", "<ul", "<ol", _
                  "<li", "<table", "<tr", "<td", "<h1", "<h2", "<h3", "<h4", "<em", "<i>", "<font", "<a ")
    For i = LBound(known) To UBound(known)
        If InStr(1, s, known(i), vbBinaryCompare) > 0 Then
            LooksLikeHtml = True
            Exit Function
        End If
    Next i
End Function

' "<" starter et tag, naar det efterfoelges af et bogstav, "/" eller "!".
' "a < b" og "<3" er tekst.
Private Function IsTagStart(ByVal s As String, ByVal pos As Long) As Boolean
    Dim c As String
    If pos >= Len(s) Then Exit Function
    c = LCase$(Mid$(s, pos + 1, 1))
    IsTagStart = (c >= "a" And c <= "z") Or c = "/" Or c = "!"
End Function

Private Function TagNameOf(ByVal tagText As String) As String
    Dim i As Long
    Dim c As String
    Dim nm As String

    tagText = LCase$(Trim$(tagText))
    If Left$(tagText, 1) = "/" Then tagText = Mid$(tagText, 2)
    For i = 1 To Len(tagText)
        c = Mid$(tagText, i, 1)
        If (c >= "a" And c <= "z") Or (c >= "0" And c <= "9") Then
            nm = nm & c
        Else
            Exit For
        End If
    Next i
    TagNameOf = nm
End Function

Private Function ListMarker(ByVal depth As Long, ByRef listKind() As String, ByRef listCount() As Long) As String
    Dim pad As String
    Dim k As Long

    If depth < 1 Then
        ListMarker = "- "
        Exit Function
    End If

    For k = 2 To depth
        pad = pad & ChrW$(INDENT_CODE)
    Next k

    If listKind(depth) = "ol" Then
        listCount(depth) = listCount(depth) + 1
        ListMarker = pad & CStr(listCount(depth)) & ". "
    Else
        ListMarker = pad & "- "
    End If
End Function

' I HTML er et linjeskift i teksten et mellemrum, og flere mellemrum er eet.
' Linjeskift i SAP-teksten kommer fra <br>, <p>, <li> og de andre blok-tags -
' det er dem, brugeren saa i appen. (Det gamle script beholdt linjeskiftene og
' gav derfor tomme linjer mellem punkterne i en opstilling.)
Private Function CollapseRun(ByVal s As String) As String
    s = Replace(s, LF, " ")
    s = Replace(s, vbTab, " ")
    Do While InStr(1, s, "  ", vbBinaryCompare) > 0
        s = Replace(s, "  ", " ")
    Loop
    CollapseRun = s
End Function

' Linjeskift, men kun hvis teksten ikke allerede slutter med et. Saa giver
' "</li><li>" og "</div><div>" ikke tomme linjer.
Private Function SoftBreak(ByVal s As String) As String
    If Len(s) > 0 And Right$(s, 1) <> LF Then s = s & LF
    SoftBreak = s
End Function

Private Function EscapeText(ByVal s As String) As String
    s = Replace(s, "<", ChrW$(8249))
    s = Replace(s, ">", ChrW$(8250))
    EscapeText = s
End Function

' Sidste oprydning: hver linje trimmes, tomme formater fjernes, mere end een
' tom linje i traek bliver til een, og der startes og sluttes ikke med tomme
' linjer.
Private Function Finish(ByVal s As String) As String
    Dim lines() As String
    Dim i As Long

    s = Replace(s, ChrW$(160), " ")
    s = Replace(s, "<H></>", "")
    s = Replace(s, "<U></>", "")

    lines = Split(s, LF)
    For i = LBound(lines) To UBound(lines)
        lines(i) = Replace(Trim$(lines(i)), ChrW$(INDENT_CODE), "  ")
    Next i
    s = Join(lines, LF)

    Do While InStr(1, s, LF & LF & LF, vbBinaryCompare) > 0
        s = Replace(s, LF & LF & LF, LF & LF)
    Loop
    Do While Left$(s, 1) = LF
        s = Mid$(s, 2)
    Loop
    Do While Right$(s, 1) = LF
        s = Left$(s, Len(s) - 1)
    Loop

    Finish = s
End Function

Private Function StartsWithBreak(ByVal html As String) As Boolean
    Dim s As String
    s = LTrim$(Replace(Replace(html, vbCrLf, LF), vbCr, LF))
    If Left$(s, 1) = LF Then
        StartsWithBreak = True
    ElseIf LCase$(Left$(s, 3)) = "<br" Then
        StartsWithBreak = True
    End If
End Function

'==============================================================================
' Tegnkoder
'==============================================================================

Private Function DecodeEntities(ByVal s As String) As String
    Dim out As String
    Dim i As Long
    Dim semi As Long
    Dim nm As String
    Dim ch As String

    i = 1
    Do While i <= Len(s)
        ch = Mid$(s, i, 1)
        If ch = "&" Then
            semi = InStr(i + 1, s, ";", vbBinaryCompare)
            If semi > 0 And semi - i <= 10 Then
                nm = Mid$(s, i + 1, semi - i - 1)
                ch = EntityChar(nm)
                If Len(ch) > 0 Or nm = "shy" Then
                    out = out & ch
                    i = semi + 1
                Else
                    out = out & "&"
                    i = i + 1
                End If
            Else
                out = out & "&"
                i = i + 1
            End If
        Else
            out = out & ch
            i = i + 1
        End If
    Loop

    DecodeEntities = out
End Function

' Tegnet for en HTML-tegnkode, eller "" hvis koden er ukendt.
Private Function EntityChar(ByVal nm As String) As String
    Dim code As Long

    If Left$(nm, 1) = "#" Then
        If LCase$(Mid$(nm, 2, 1)) = "x" Then
            If Not IsHex(Mid$(nm, 3)) Then Exit Function
            code = CLng("&H" & Mid$(nm, 3))
        Else
            If Not VhpUtil.IsAllDigits(Mid$(nm, 2)) Then Exit Function
            If Len(Mid$(nm, 2)) > 6 Then Exit Function
            code = CLng(Mid$(nm, 2))
        End If
        If code > 0 And code < 65536 Then EntityChar = ChrW$(code)
        Exit Function
    End If

    Select Case nm
        Case "amp": code = 38
        Case "lt": code = 60
        Case "gt": code = 62
        Case "quot": code = 34
        Case "apos": code = 39
        Case "nbsp": code = 160
        Case "aelig": code = 230
        Case "AElig": code = 198
        Case "oslash": code = 248
        Case "Oslash": code = 216
        Case "aring": code = 229
        Case "Aring": code = 197
        Case "auml": code = 228
        Case "Auml": code = 196
        Case "ouml": code = 246
        Case "Ouml": code = 214
        Case "uuml": code = 252
        Case "Uuml": code = 220
        Case "eacute": code = 233
        Case "Eacute": code = 201
        Case "egrave": code = 232
        Case "ndash": code = 8211
        Case "mdash": code = 8212
        Case "bull": code = 8226
        Case "middot": code = 183
        Case "hellip": code = 8230
        Case "lsquo": code = 8216
        Case "rsquo": code = 8217
        Case "ldquo": code = 8220
        Case "rdquo": code = 8221
        Case "laquo": code = 171
        Case "raquo": code = 187
        Case "deg": code = 176
        Case "plusmn": code = 177
        Case "sup2": code = 178
        Case "sup3": code = 179
        Case "frac12": code = 189
        Case "times": code = 215
        Case "micro": code = 181
        Case "euro": code = 8364
        Case "copy": code = 169
        Case "reg": code = 174
        Case "trade": code = 8482
        Case "shy": code = 0
        Case Else: code = 0
    End Select

    If code > 0 Then EntityChar = ChrW$(code)
End Function

Private Function IsHex(ByVal s As String) As Boolean
    Dim i As Long
    Dim c As String
    If Len(s) = 0 Or Len(s) > 4 Then Exit Function
    For i = 1 To Len(s)
        c = LCase$(Mid$(s, i, 1))
        If Not ((c >= "0" And c <= "9") Or (c >= "a" And c <= "f")) Then Exit Function
    Next i
    IsHex = True
End Function
