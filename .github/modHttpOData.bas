Attribute VB_Name = "modHttpOData"
Option Explicit

Private Const MAX_RETRIES As Long = 2
Private Const RETRY_WAIT_MS As Long = 1000

' Returnerer HTTP response-tekst (ingen admin-krav; deler cert/proxy med Edge)
Public Function HttpGetText(ByVal url As String, Optional ByVal acceptHeader As String = "application/json", Optional ByVal authHeader As String = vbNullString) As String
    Dim attempt As Long
    Dim lastErr As String
    Dim preferServer As Boolean
    Dim transportName As String
    Dim currentAuthHeader As String
    Dim canDropAuthHeader As Boolean

    preferServer = False
    currentAuthHeader = Trim$(authHeader)
    canDropAuthHeader = (Len(currentAuthHeader) > 0)

    For attempt = 1 To MAX_RETRIES + 1
        On Error GoTo RetryCheck

        Dim http As Object
        Set http = CreateHttpRequestObject(preferServer, transportName)
        If http Is Nothing Then
            Err.Raise 1008, , "Kunne ikke oprette HTTP klient."
        End If

        ConfigureHttpTimeouts http

        http.Open "GET", url, False
        http.setRequestHeader "Accept", acceptHeader
        http.setRequestHeader "User-Agent", "ExcelVBA-OData"
        http.setRequestHeader "Connection", "close"
        If Len(currentAuthHeader) > 0 Then
            http.setRequestHeader "Authorization", currentAuthHeader
        End If

        http.send

        If http.Status < 200 Or http.Status >= 300 Then
            If (http.Status = 401 Or http.Status = 403) And canDropAuthHeader And attempt <= MAX_RETRIES Then
                lastErr = "HTTP " & http.Status & ": " & http.StatusText
                currentAuthHeader = vbNullString
                canDropAuthHeader = False
                preferServer = False
                Debug.Print "HTTP auth fallback retry " & attempt & "/" & MAX_RETRIES & " via XMLHTTP for " & url & " (" & lastErr & ")"
                WaitMilliseconds RETRY_WAIT_MS
                DoEvents
                GoTo NextAttempt
            End If

            ' Server errors (5xx) are retryable; client errors (4xx) are not
            If http.Status >= 500 And attempt <= MAX_RETRIES Then
                lastErr = "HTTP " & http.Status & ": " & http.StatusText
                Debug.Print "HTTP retry " & attempt & "/" & MAX_RETRIES & " via " & transportName & " for " & url & " (" & lastErr & ")"
                WaitMilliseconds RETRY_WAIT_MS
                DoEvents
                GoTo NextAttempt
            End If
            Err.Raise 1002, , "HTTP " & http.Status & ": " & http.StatusText & vbCrLf & url
        End If

        HttpGetText = CStr(http.responseText)
        Exit Function

RetryCheck:
        lastErr = Err.Description
        If attempt <= MAX_RETRIES Then
            If IsOperationAbortedError(lastErr) Then preferServer = Not preferServer
            Debug.Print "HTTP transport retry " & attempt & "/" & MAX_RETRIES & " via " & transportName & " for " & url & " (" & lastErr & ")"
            Err.Clear
            WaitMilliseconds RETRY_WAIT_MS
            DoEvents
        Else
            Err.Raise Err.Number, , "Transportfejl efter " & MAX_RETRIES & " forsog via " & transportName & ": " & lastErr & vbCrLf & "URL: " & url
        End If
NextAttempt:
    Next attempt
End Function

' Generic JSON sender for POST/MERGE/PATCH style calls.
Public Function HttpSendJson( _
    ByVal method As String, _
    ByVal url As String, _
    Optional ByVal payload As String = vbNullString, _
    Optional ByVal authHeader As String = vbNullString, _
    Optional ByVal contentType As String = "application/json", _
    Optional ByVal acceptHeader As String = "application/json", _
    Optional ByVal ifMatchHeader As String = vbNullString, _
    Optional ByVal xHttpMethodHeader As String = vbNullString, _
    Optional ByRef responseTextOut As String = vbNullString, _
    Optional ByVal requestDigestHeader As String = vbNullString) As Long

    Dim attempt As Long
    Dim lastErr As String
    Dim httpMethod As String
    Dim preferServer As Boolean
    Dim transportName As String

    httpMethod = UCase$(Trim$(method))
    If Len(httpMethod) = 0 Then
        Err.Raise 1004, , "HTTP metode mangler."
    End If

    preferServer = False

    For attempt = 1 To MAX_RETRIES + 1
        On Error GoTo RetryCheck

        Dim http As Object
        Set http = CreateHttpRequestObject(preferServer, transportName)
        If http Is Nothing Then
            Err.Raise 1008, , "Kunne ikke oprette HTTP klient."
        End If

        ConfigureHttpTimeouts http

        http.Open httpMethod, url, False

        If Len(Trim$(acceptHeader)) > 0 Then
            http.setRequestHeader "Accept", acceptHeader
        End If

        If Len(Trim$(contentType)) > 0 Then
            http.setRequestHeader "Content-Type", contentType
        End If

        http.setRequestHeader "User-Agent", "ExcelVBA-OData"
        http.setRequestHeader "Connection", "close"

        If Len(Trim$(authHeader)) > 0 Then
            http.setRequestHeader "Authorization", Trim$(authHeader)
        End If

        If Len(Trim$(ifMatchHeader)) > 0 Then
            http.setRequestHeader "If-Match", Trim$(ifMatchHeader)
        End If

        If Len(Trim$(xHttpMethodHeader)) > 0 Then
            http.setRequestHeader "X-HTTP-Method", Trim$(xHttpMethodHeader)
        End If

        If Len(Trim$(requestDigestHeader)) > 0 Then
            http.setRequestHeader "X-RequestDigest", Trim$(requestDigestHeader)
        End If

        If Len(payload) > 0 Then
            http.send payload
        Else
            http.send
        End If

        responseTextOut = CStr(http.responseText)
        HttpSendJson = CLng(http.Status)

        If HttpSendJson >= 200 And HttpSendJson < 300 Then
            Exit Function
        End If

        If HttpSendJson >= 500 And attempt <= MAX_RETRIES Then
            lastErr = "HTTP " & CStr(HttpSendJson) & ": " & CStr(http.StatusText)
            Debug.Print "HTTP retry " & attempt & "/" & MAX_RETRIES & " via " & transportName & " for " & url & " (" & lastErr & ")"
            WaitMilliseconds RETRY_WAIT_MS
            DoEvents
            GoTo NextAttempt
        End If

        Err.Raise 1005, , "HTTP " & CStr(HttpSendJson) & ": " & CStr(http.StatusText) & vbCrLf & url & vbCrLf & responseTextOut

RetryCheck:
        lastErr = Err.Description

        If attempt <= MAX_RETRIES Then
            If IsOperationAbortedError(lastErr) Then preferServer = Not preferServer
            Debug.Print "HTTP transport retry " & attempt & "/" & MAX_RETRIES & " via " & transportName & " for " & url & " (" & lastErr & ")"
            Err.Clear
            WaitMilliseconds RETRY_WAIT_MS
            DoEvents
        Else
            Err.Raise Err.Number, , "Transportfejl efter " & MAX_RETRIES & " forsog via " & transportName & ": " & lastErr & vbCrLf & "URL: " & url
        End If

NextAttempt:
    Next attempt
End Function

Private Function CreateHttpRequestObject(ByVal preferServer As Boolean, ByRef transportName As String) As Object
    On Error Resume Next

    ' Legacy/default path: XMLHTTP bruger WinINET-session (samme cookie-kontekst som Office/Edge).
    If preferServer Then
        Set CreateHttpRequestObject = CreateObject("MSXML2.ServerXMLHTTP.6.0")
        If Not CreateHttpRequestObject Is Nothing Then transportName = "ServerXMLHTTP"
        If CreateHttpRequestObject Is Nothing Then
            Set CreateHttpRequestObject = CreateObject("MSXML2.XMLHTTP.6.0")
            If Not CreateHttpRequestObject Is Nothing Then transportName = "XMLHTTP"
        End If
    Else
        Set CreateHttpRequestObject = CreateObject("MSXML2.XMLHTTP.6.0")
        If Not CreateHttpRequestObject Is Nothing Then transportName = "XMLHTTP"
        If CreateHttpRequestObject Is Nothing Then
            Set CreateHttpRequestObject = CreateObject("MSXML2.ServerXMLHTTP.6.0")
            If Not CreateHttpRequestObject Is Nothing Then transportName = "ServerXMLHTTP"
        End If
    End If

    ' Sidste fallback: WinHttp hvis MSXML-klienterne ikke kan oprettes.
    If CreateHttpRequestObject Is Nothing Then
        Set CreateHttpRequestObject = CreateObject("WinHttp.WinHttpRequest.5.1")
        If Not CreateHttpRequestObject Is Nothing Then
            transportName = "WinHttp"
            ' Aktiver automatisk Windows credentials (0 = AutoLogonPolicy_Always)
            CreateHttpRequestObject.SetAutoLogonPolicy 0
        End If
    End If

    On Error GoTo 0
End Function

Private Sub ConfigureHttpTimeouts(ByVal http As Object)
    On Error Resume Next
    http.setTimeouts 15000, 15000, 30000, 120000
    Err.Clear
    http.SetTimeouts 15000, 15000, 30000, 120000
    Err.Clear
    On Error GoTo 0
End Sub

Private Function IsOperationAbortedError(ByVal messageText As String) As Boolean
    Dim lowered As String

    lowered = LCase$(Trim$(messageText))
    If Len(lowered) = 0 Then Exit Function

    IsOperationAbortedError = (InStr(1, lowered, "operation aborted", vbTextCompare) > 0) Or _
                              (InStr(1, lowered, "afbrudt", vbTextCompare) > 0)
End Function

Private Sub WaitMilliseconds(ByVal milliseconds As Long)
    If milliseconds <= 0 Then Exit Sub

    Dim startTick As Double
    Dim elapsed As Double

    startTick = Timer

    Do
        DoEvents
        elapsed = Timer - startTick
        If elapsed < 0 Then elapsed = elapsed + 86400#
    Loop While elapsed * 1000# < milliseconds
End Sub


' Parser JSON-tekst til objekttrae (Dictionary/Collection) via JsonConverter.bas
Public Function HttpGetJson(ByVal url As String, Optional ByVal authHeader As String = vbNullString) As Object
    Dim txt As String
    Dim preview As String

    txt = HttpGetText(url, "application/json;odata=verbose,application/json", authHeader)

    On Error GoTo ParseFail
    Set HttpGetJson = JsonConverter.ParseJson(txt)
    On Error GoTo 0
    Exit Function

ParseFail:
    preview = Left$(Replace$(Replace$(txt, vbCr, " "), vbLf, " "), 220)
    Err.Raise Err.Number, , "JSON parse-fejl: " & Err.Description & vbCrLf & "URL: " & url & vbCrLf & "Response (preview): " & preview
End Function

' Backward-compatible XML fetch used by legacy OData feed parsers.
Public Function HttpGetAsXml(ByVal url As String, Optional ByVal authHeader As String = vbNullString) As Object
    Dim txt As String
    Dim dom As Object

    txt = HttpGetText(url, "application/atom+xml,application/xml,text/xml,*/*", authHeader)

    Set dom = CreateObject("MSXML2.DOMDocument.6.0")
    dom.async = False
    dom.validateOnParse = False
    dom.resolveExternals = False

    If Not dom.LoadXML(txt) Then
        Err.Raise 1003, , "XML parse-fejl: " & dom.parseError.Reason & vbCrLf & url
    End If

    Set HttpGetAsXml = dom
End Function
