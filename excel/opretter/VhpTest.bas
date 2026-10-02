Attribute VB_Name = "VhpTest"
Option Explicit
'==============================================================================
' VhpTest - selvtest uden SAP.
'
' RunSelfTest (knappen Selvtest i arket Indstillinger) afproever
' oversaettelserne, langteksten, JSON-delen og valideringen. Den roerer
' hverken SAP, mappen eller arkene. Koer den efter hver ny udgave af
' modulerne - en fejl her ville ellers foerst vise sig midt i SAP.
'
' SelfTestPure bruger kun rene VBA-funktioner og koeres ogsaa af
' tests/test_vba_runner.py i LibreOffice. SelfTestJson kraever
' Scripting.Dictionary og derfor Windows.
'==============================================================================

Private mFails As String
Private mCount As Long

Public Sub RunSelfTest()
    Dim pure As String
    Dim json As String

    pure = SelfTestPure()
    json = SelfTestJson()

    If Left$(pure, 2) = "OK" And Left$(json, 2) = "OK" Then
        MsgBox VhpUtil.Dk("Selvtesten er gr{oe}n.") & vbLf & vbLf & pure & vbLf & json, vbInformation, VHP_APP_NAME
    Else
        MsgBox VhpUtil.Dk("Selvtesten fandt fejl:") & vbLf & vbLf & pure & vbLf & vbLf & json, vbCritical, VHP_APP_NAME
    End If
End Sub

'==============================================================================
' Rene funktioner
'==============================================================================
Public Function SelfTestPure() As String
    Dim d As Date
    Dim c As Collection
    Dim body As Collection
    Dim longLine As String

    mFails = vbNullString
    mCount = 0

    '--- VhpUtil --------------------------------------------------------------
    Check "Dk", VhpUtil.Dk("V{ae}lg {oe} {aa}"), "V" & ChrW$(230) & "lg " & ChrW$(248) & " " & ChrW$(229)
    Check "Clip", VhpUtil.Clip("  abcdef  ", 3), "abc"
    Check "IsAllDigits 0123", VhpUtil.IsAllDigits("0123"), True
    Check "IsAllDigits 12a", VhpUtil.IsAllDigits("12a"), False
    Check "IsAllDigits tom", VhpUtil.IsAllDigits(""), False
    Check "TryParseYmd 2027-02-28", VhpUtil.TryParseYmd("2027-02-28", d), True
    Check "TryParseYmd dato", Format$(d, "yyyy-mm-dd"), "2027-02-28"
    Check "TryParseYmd 2027-02-31", VhpUtil.TryParseYmd("2027-02-31", d), False
    Check "TryParseYmd tekst", VhpUtil.TryParseYmd("31-12-2027", d), False
    Check "IsoToDisplay", VhpUtil.IsoToDisplay("2026-10-02T08:42:33Z"), "02-10-2026 08:42 UTC"

    '--- VhpMap ---------------------------------------------------------------
    Check "ActivityCode", VhpMap.ActivityCode("102 - Predetermined Maintenance"), "102"
    Check "ActivityCode gammelt format", VhpMap.ActivityCode("2;#101 - Maintenance"), "101"
    Check "ActivityCode tom", VhpMap.ActivityCode(""), ""
    Check "PriorityKey Red", VhpMap.PriorityKey("Red (Statutory and SCEq)"), "1"
    Check "PriorityKey Yellow", VhpMap.PriorityKey("Yellow (default)"), "3"
    Check "PriorityKey Blue", VhpMap.PriorityKey("Blue (standing order)"), "6"
    Check "PriorityKey 3", VhpMap.PriorityKey("(Kun notification) 3 Within a week"), "3"
    Check "PriorityKey 4", VhpMap.PriorityKey("(Kun notification) 4 Within a month"), "4"
    Check "PriorityKey ukendt", VhpMap.PriorityKey("Haster"), ""
    Check "RevisionValue ja", VhpMap.RevisionValue(True, ""), "REV"
    Check "RevisionValue valg", VhpMap.RevisionValue(False, "REV - General Revision Mark"), "REV"
    Check "RevisionValue nej", VhpMap.RevisionValue(False, ""), ""
    Check "WorkCenter", VhpMap.WorkCenter("AVVAP   "), "AVVAP"
    Check "ServiceSuffix", VhpMap.ServiceSuffix("SSVXSTIL"), "XSTIL"
    Check "ServiceSuffix kort", VhpMap.ServiceSuffix("XSTIL"), "XSTIL"
    Check "VendorNo navn", VhpMap.VendorNo("101985 - PERSOLIT"), "101985"
    Check "VendorNo nul", VhpMap.VendorNo("0"), ""
    Check "VendorNo tom", VhpMap.VendorNo(""), ""
    Check "VendorNo tal", VhpMap.VendorNo("12654"), "12654"
    Check "NormalizeUnit wk", VhpMap.NormalizeUnit("wk"), "WK"
    Check "NormalizeUnit Mon", VhpMap.NormalizeUnit("Mon"), "MON"
    Check "CycleKey", VhpMap.CycleKey(1, "WK"), "1WK"
    Check "CycleKey decimal", VhpMap.CycleKey(2.5, "mon"), "2.5MON"
    Check "StartDate WK", Format$(VhpMap.StartDate(DateSerial(2027, 9, 20), 1, "WK"), "yyyy-mm-dd"), "2027-09-13"
    Check "StartDate YR", Format$(VhpMap.StartDate(DateSerial(2027, 3, 1), 1, "YR"), "yyyy-mm-dd"), "2026-03-01"
    Check "StartDate MON", Format$(VhpMap.StartDate(DateSerial(2027, 3, 31), 1, "MON"), "yyyy-mm-dd"), "2027-02-28"
    Check "StartDate DAY", Format$(VhpMap.StartDate(DateSerial(2027, 1, 1), 20, "DAY"), "yyyy-mm-dd"), "2026-12-12"
    Check "StartDate H", Format$(VhpMap.StartDate(DateSerial(2027, 1, 1), 1, "H"), "yyyy-mm-dd"), "2027-01-01"
    Check "SapDate", VhpMap.SapDate(DateSerial(2026, 3, 1)), "01.03.2026"
    Check "SapNumber komma", VhpMap.SapNumber(1.5, ","), "1,5"
    Check "SapNumber heltal", VhpMap.SapNumber(49400, ","), "49400"
    Check "SapNumber punktum", VhpMap.SapNumber(0.25, "."), "0.25"
    Check "LongestDigitRun", VhpMap.LongestDigitRun("Task list 50012345 saved, counter 1"), "50012345"
    Check "LongestDigitRun tom", VhpMap.LongestDigitRun("Ingen tal"), ""

    Set c = VhpMap.ObjectListEntries("SSV13 HFC10; SSV13 HFC20AT002;; SSV13 HFC10")
    Check "Objektliste ny app, antal", c.Count, 2
    Check "Objektliste ny app, 2", c(2), "SSV13 HFC20AT002"
    Set c = VhpMap.ObjectListEntries("AVV50 CYT25GS001 -H02 - CO DETEKTION|||AVV50 AKT10 - Byggeplads")
    Check "Objektliste gammel app, antal", c.Count, 2
    Check "Objektliste gammel app, 1", c(1), "AVV50 CYT25GS001 -H02"
    Check "Objektliste gammel app, 2", c(2), "AVV50 AKT10"
    Check "Objektliste tom", VhpMap.ObjectListEntries("").Count, 0

    '--- VhpItf ---------------------------------------------------------------
    Check "Itf liste", VhpItf.HtmlToSapText("<div class=""x""><p><strong>Form&aring;l:</strong> kontrol &amp; test.</p>" & _
        "<ul><li>A</li><li>B<ul><li>C</li></ul></li></ul></div>"), _
        "<H>Form" & ChrW$(229) & "l:</> kontrol & test." & vbLf & vbLf & "- A" & vbLf & "- B" & vbLf & "  - C"
    Check "Itf afsnit", VhpItf.HtmlToSapText("<p>a</p><p>b</p>"), "a" & vbLf & vbLf & "b"
    Check "Itf br", VhpItf.HtmlToSapText("a<br>b<br/><br>c"), "a" & vbLf & "b" & vbLf & vbLf & "c"
    Check "Itf nummereret", VhpItf.HtmlToSapText("<ol><li>en</li><li>to</li></ol>"), "1. en" & vbLf & "2. to"
    Check "Itf understreget", VhpItf.HtmlToSapText("<u>under</u> og <b>fed</b>"), "<U>under</> og <H>fed</>"
    Check "Itf ren tekst", VhpItf.HtmlToSapText("Linje 1" & vbCrLf & "Linje 2 <ok> & mere"), _
        "Linje 1" & vbLf & "Linje 2 " & ChrW$(8249) & "ok" & ChrW$(8250) & " & mere"
    Check "Itf tegnkoder", VhpItf.HtmlToSapText("<p>&#230;&#xF8;&aring; &lt;5 bar&gt;</p>"), _
        ChrW$(230) & ChrW$(248) & ChrW$(229) & " " & ChrW$(8249) & "5 bar" & ChrW$(8250)
    Check "Itf tom div", VhpItf.HtmlToSapText("<div></div>"), ""
    Check "Itf HasText tom", VhpItf.HasText("<div class=""ExternalClass1""></div>"), False
    Check "Itf HasText", VhpItf.HasText("<div>sfsef</div>"), True
    Check "Itf linjeskift i HTML", VhpItf.HtmlToSapText("<p>et" & vbLf & "  to</p>"), "et to"

    Set body = VhpItf.ItfBody("<p>a</p><p></p><p>b</p>")
    Check "ItfBody antal", body.Count, 3
    Check "ItfBody tom linje", body(2), "*"
    Check "ItfBody linje", body(1), "* a"

    longLine = String$(100, "a") & " " & String$(40, "b")
    Set body = VhpItf.ItfBody(longLine)
    Check "ItfBody lang linje, antal", body.Count, 2
    Check "ItfBody lang linje, 2", body(2), "* " & String$(40, "b")

    Set body = VhpItf.ItfBody("<br>Tekst", True)
    Check "ItfBody beholdt linjeskift", body(1), "*"

    SelfTestPure = Result("Funktioner")
End Function

'==============================================================================
' JSON og validering (kraever Windows: Scripting.Dictionary)
'==============================================================================
Public Function SelfTestJson() As String
    Dim o As Object
    Dim lk As Object
    Dim v As Object
    Dim item As Object
    Dim back As Object
    Dim s As String

    mFails = vbNullString
    mCount = 0

    On Error GoTo Failed

    Set o = JsonConverter.ParseJson(SampleOrderJson(True))
    VhpOrder.Prepare o
    Check "JSON plan", VhpUtil.JStr(VhpUtil.JObj(o, "plan"), "planId"), "MP0133"
    Check "JSON null", VhpUtil.JStr(VhpUtil.JObj(o, "plan"), "strategyKey"), ""
    Check "JSON tal", VhpUtil.JNum(VhpUtil.JObj(o, "plan"), "cycle"), 1
    Check "JSON bogstaver", VhpUtil.JStr(VhpUtil.JObj(o, "plan"), "title"), "SSV kulm" & ChrW$(248) & "ller"
    Set item = VhpUtil.JList(o, "items")(1)
    Check "Operationer paa item", VhpOrder.Operations(item).Count, 3
    Check "Operationer sorteret", VhpUtil.JStr(VhpOrder.Operations(item)(1), "controlKey"), "PM01"
    Check "Materialer paa item", VhpOrder.Materials(item).Count, 1

    Set lk = SampleLookups()
    Set v = VhpOrder.Validate(o, lk)
    Check "Gyldig ordre: fejl", v("errors").Count, 0
    Check "Gyldig ordre: advarsel om materiale", v("warnings").Count >= 1, True

    Set o = JsonConverter.ParseJson(SampleOrderJson(False))
    VhpOrder.Prepare o
    Set v = VhpOrder.Validate(o, lk)
    Check "Ugyldig ordre: fejl", v("errors").Count, 2

    s = JsonConverter.ConvertToJson(VhpUtil.JObj(o, "plan"), 2)
    Set back = JsonConverter.ParseJson(s)
    Check "JSON frem og tilbage", VhpUtil.JStr(back, "title"), VhpUtil.JStr(VhpUtil.JObj(o, "plan"), "title")

    SelfTestJson = Result("JSON og validering")
    Exit Function

Failed:
    SelfTestJson = "FEJL JSON og validering: " & Err.Description
End Function

' En lille ordre som i schema/example-sap-order.json. Apostroffer bliver til
' anfoerselstegn, saa teksten kan laeses. valid = False giver en ordre med
' to fejl: en operation uden kontrolnoegle og et item uden funktionsplads.
Private Function SampleOrderJson(ByVal valid As Boolean) As String
    Dim s As String
    s = "{'kind':'vhplan-sap-order','version':1,'orderGuid':'3f2b8c1e-9d4a-4e6b-8a7c-5d1e2f3a4b5c'," & _
        "'createdOn':'2026-10-02T08:42:33Z','environment':'DEV','site':null," & _
        "'plan':{'spId':138,'planId':'MP0133','title':'SSV kulm\u00f8ller','plant':'SSV','strategyKey':null," & _
        "'cycle':1,'unit':'WK','plannedDate':'2027-09-20','sortField':'Boiler Control Category A','sortFieldId':3}," & _
        "'items':[{'spId':185,'itemId':'MI0179','title':'HFC kulm\u00f8lle 1','longText':'<p>Tekst</p>'," & _
        "'functionalLocation':'" & IIf(valid, "SSV13 HFC10", "") & "','objectList':'SSV13 HFC20AT002','orderType':'ZPRE'," & _
        "'activityType':'101 - Maintenance','mainWorkCenter':'SSVSUP','priority':'Yellow (default)'," & _
        "'userStatus':'REPL','nonFlowUserStatus':null,'revision':false,'revisionMark':null,'responsibleInitials':'PKBJE'}]," & _
        "'operations':[" & _
        "{'spId':438,'itemSpId':185,'operationNo':30,'shortText':'Stillads op:','workCenter':'SSVXSTIL','controlKey':'PM03','work':100,'persons':1}," & _
        "{'spId':436,'itemSpId':185,'operationNo':10,'shortText':'Timer','workCenter':'SSVAP','controlKey':'PM01','work':1,'persons':1}," & _
        "{'spId':439,'itemSpId':185,'operationNo':170,'shortText':'Fast pris','workCenter':'SSVLEV','controlKey':'" & _
        IIf(valid, "PM02", "") & "','work':1,'persons':1,'price':5000,'materialGroup':'B08.04','vendor':'12654'}]," & _
        "'materials':[{'spId':6,'itemId':'MI0179','taskItemId':'TI0438','operationNo':'0170','materialNo':'000000000010203945','quantity':2,'unit':'ST'}]}"
    SampleOrderJson = Replace(s, "'", """")
End Function

Private Function SampleLookups() As Object
    Dim lk As Object
    Dim d As Object
    Dim rec As Object

    Set lk = VhpUtil.NewDict()

    Set d = VhpUtil.NewDict()
    Set rec = VhpUtil.NewDict()
    rec.Add "sapPlant", "2804"
    rec.Add "profile", "PMSSV"
    rec.Add "serviceSpec", "2804"
    d.Add "SSV", rec
    lk.Add "plants", d

    Set d = VhpUtil.NewDict()
    Set rec = VhpUtil.NewDict()
    rec.Add "horizon", "2"
    rec.Add "period", "2"
    rec.Add "periodUnit", "YR"
    d.Add "1WK", rec
    lk.Add "horizons", d

    Set d = VhpUtil.NewDict()
    Set rec = VhpUtil.NewDict()
    rec.Add "serviceNo", "3000001"
    rec.Add "matGroup", "F01.02"
    d.Add "XSTIL", rec
    lk.Add "services", d

    Set SampleLookups = lk
End Function

'==============================================================================
' Hjaelpere
'==============================================================================
Private Sub Check(ByVal testName As String, ByVal actual As Variant, ByVal expected As Variant)
    mCount = mCount + 1
    If CStr(actual) <> CStr(expected) Then
        mFails = mFails & testName & ": fik [" & CStr(actual) & "], ventede [" & CStr(expected) & "]" & vbLf
    End If
End Sub

Private Function Result(ByVal area As String) As String
    If Len(mFails) = 0 Then
        Result = "OK " & area & ": " & mCount & " tjek"
    Else
        Result = "FEJL " & area & ":" & vbLf & mFails
    End If
End Function
