' ===========================================================================
'  RETTELSE: special characteristics blev nogle gange ikke skrevet
' ===========================================================================
'
'  Erstat WriteSpecialCharacteristicsOnCurrentPage i modulet GUI_SCRIPT med
'  udgaven nedenfor, og tilfoej konstanten oeverst i modulet.
'
'  ---------------------------------------------------------------------
'  FEJL 1: For-loekkens OEVRE GRAENSE laases ved loekkens start
'  ---------------------------------------------------------------------
'  Den gamle kode:
'
'      For i = 1 To countKeys
'          ...
'          Set metadata = GetCharacteristicPageMetadata(...)
'          countKeys = CLng(metadata("countKeys"))   ' <- ingen virkning
'          keys      = metadata("keys")              ' <- NY, kortere/laengere
'          i = 0                                     ' genstart
'      Next i
'
'  VBA evaluerer "To countKeys" EEN GANG, naar loekken startes. At saette
'  countKeys inde i kroppen aendrer IKKE hvornaar loekken stopper. Efter en
'  opdatering koerer loekken altsaa 1..DET GAMLE antal hen over de NYE
'  arrays - og BuildCharacteristicPageMetadata dimensionerer dem praecis
'  til det, der staar paa skaermen (ReDim arr(1 To values.count)).
'
'  Det giver to udfald, alt efter om popup'en aendrede antallet af raekker:
'
'      faerre raekker end foer  ->  keys(i) rammer uden for arrayet
'                                  -> "Subscript out of range", scriptet doer
'      flere raekker end foer   ->  de sidste besoeges aldrig
'                                  -> karakteristikken skrives ALDRIG, og
'                                     det ses kun i Debug.Print
'
'  Derfor virker det nogle gange og andre gange ikke: det afhaenger af, om
'  popup'en for den enkelte karakteristik indsatte eller fjernede raekker.
'
'  ---------------------------------------------------------------------
'  FEJL 2: objContainer er foraeldet efter popup'en
'  ---------------------------------------------------------------------
'  objContainer hentes EEN gang i FillCharacteristicsBatch, foer der skrives.
'  WriteSpecialCharacteristicWithControl aabner en popup (SendVKey 4) og
'  lukker den igen - og SAP genrenderer containeren. Den gamle kode
'  opdaterede metadata ud fra den SAMME, nu foraeldede objContainer.
'
'  Nedenfor hentes containeren forfra efter hver skrivning, med
'  TryGetCharacteristicContainer, praecis som FillCharacteristicsBatch selv
'  goer det ét niveau hoejere oppe.
'
'  ---------------------------------------------------------------------
'  HVAD DER IKKE ER FEJLEN
'  ---------------------------------------------------------------------
'  IsSpecialCharacteristic sammenligner med = og ikke StrComp(..., vbTextCompare),
'  og modulet har ikke Option Compare Text. Det ER en inkonsistens - resten af
'  modulet bruger vbTextCompare - men det er ikke aarsagen her: alle 35 ark i
'  projektmappen staver felterne ens ("Remarks", "Supply from",
'  "Safety Critical Equipment"). Rettes alligevel nedenfor, saa en fremtidig
'  stavevariant ikke stille og roligt sender vaerdien ned ad den forkerte vej.
' ===========================================================================


' --- Tilfoejes oeverst i modulet, ved siden af de oevrige Const ------------
Private Const MAX_SPECIAL_WRITE_PASSES As Long = 50


' --- Erstatter den eksisterende procedure ---------------------------------
Private Sub WriteSpecialCharacteristicsOnCurrentPage(ByVal objContainer As Object, ByVal specialPending As Object)
    Dim metadata As Object
    Dim keys As Variant
    Dim keyIndexes As Variant
    Dim mwertIndexes As Variant
    Dim mwertControls As Collection
    Dim i As Long
    Dim countKeys As Long
    Dim keyName As String
    Dim nextIndex As Long
    Dim idx As Long
    Dim mwertPos As Long
    Dim mwertField As Object
    Dim guard As Long
    Dim wroteOne As Boolean

    If specialPending Is Nothing Then Exit Sub
    If specialPending.count = 0 Then Exit Sub
    If objContainer Is Nothing Then Exit Sub

    Do
        ' Spaerre mod en uendelig loekke, hvis SAP bliver ved at vise den
        ' samme raekke uden at skrivningen faar effekt.
        guard = guard + 1
        If guard > MAX_SPECIAL_WRITE_PASSES Then Exit Do

        ' Metadata hentes forfra i HVERT gennemloeb. Det er her den gamle
        ' kode gik galt: den genbrugte loekkens oprindelige oevre graense.
        Set metadata = GetCharacteristicPageMetadata(objContainer, CHARACTERISTIC_MODE_WRITE_SPECIAL)
        countKeys = CLng(metadata("countKeys"))
        If countKeys = 0 Then Exit Do

        keys = metadata("keys")
        keyIndexes = metadata("keyIndexes")
        mwertIndexes = metadata("mwertIndexes")
        Set mwertControls = metadata("mwertControls")

        wroteOne = False

        For i = 1 To countKeys
            keyName = CStr(keys(i))

            If keyName <> "" Then
                If specialPending.exists(keyName) Then
                    If i < countKeys Then
                        nextIndex = CLng(keyIndexes(i + 1))
                    Else
                        nextIndex = 9999
                    End If

                    Set mwertField = Nothing
                    For mwertPos = 1 To mwertControls.count
                        idx = CLng(mwertIndexes(mwertPos))
                        If idx >= CLng(keyIndexes(i)) And idx < nextIndex Then
                            Set mwertField = mwertControls(mwertPos)
                            Exit For
                        End If
                    Next mwertPos

                    If Not mwertField Is Nothing Then
                        WriteSpecialCharacteristicWithControl keyName, CStr(specialPending(keyName)), mwertField
                        specialPending.Remove keyName
                        wroteOne = True

                        ' Een skrivning ad gangen. Popup'en kan have flyttet
                        ' raekkerne, saa baade keys og mwertControls skal
                        ' bygges op igen, foer der roeres ved den naeste.
                        Exit For
                    End If
                End If
            End If
        Next i

        If specialPending.count = 0 Then Exit Do

        ' Ingen af de resterende findes paa denne side. Kalderen gaar videre
        ' til naeste side.
        If Not wroteOne Then Exit Do

        ' Popup'en har genrenderet skaermen: hent containeren forfra, ellers
        ' peger objContainer paa et objekt, SAP har smidt vaek.
        If Not TryGetCharacteristicContainer(objContainer) Then Exit Do
        If objContainer Is Nothing Then Exit Do
    Loop
End Sub


' --- Ogsaa vaerd at rette: gjort ufoelsom over for store/smaa bogstaver ----
Private Function IsSpecialCharacteristic(ByVal searchText As String) As Boolean
    Dim s As String
    s = Trim$(searchText)

    IsSpecialCharacteristic = _
        (StrComp(s, "Remarks", vbTextCompare) = 0) Or _
        (StrComp(s, "Supply from", vbTextCompare) = 0) Or _
        (StrComp(s, "Safety Critical Equipment", vbTextCompare) = 0)
End Function
