Attribute VB_Name = "VhpLookup"
Option Explicit
'==============================================================================
' VhpLookup - opslagene i arket "Opslag". Alt det SAP-specifikke, appen ikke
' ved noget om, staar her og kun her:
'
'   tblVaerker        vaerk (SSV) -> SAP-vaerk, arbejdsplanprofil og
'                     modelydelsesspecifikation
'   tblKaldshorisont  cyklus (1 WK) -> kaldshorisont og planlaegningsperiode
'   tblYdelser        arbejdscentrets endelse (XSTIL) -> ydelsesnummer til PM03
'
' Det svarer til fanen Call_Horizon_Table i det gamle regneark. Kolonnerne
' laeses efter PLADS, ikke efter overskrift, saa en omdoebt overskrift ikke
' faar opslaget til at give tomt.
'==============================================================================

' Alle tre tabeller som Dictionaries i en Dictionary.
Public Function Load() As Object
    Dim lk As Object
    Set lk = VhpUtil.NewDict()
    lk.Add "plants", ReadPlants()
    lk.Add "horizons", ReadHorizons()
    lk.Add "services", ReadServices()
    Set Load = lk
End Function

' Vaerkets raekke: sapPlant, profile, serviceSpec. Nothing, hvis vaerket
' ikke staar i tabellen.
Public Function Plant(ByVal lk As Object, ByVal plantCode As String) As Object
    Dim d As Object
    Set d = lk("plants")
    plantCode = UCase$(Trim$(plantCode))
    If d.Exists(plantCode) Then Set Plant = d(plantCode)
End Function

' Kaldshorisonten for en cyklus: horizon, period, periodUnit.
Public Function Horizon(ByVal lk As Object, ByVal cycle As Double, ByVal unitText As String) As Object
    Dim d As Object
    Dim key As String
    Set d = lk("horizons")
    key = VhpMap.CycleKey(cycle, unitText)
    If d.Exists(key) Then Set Horizon = d(key)
End Function

' Ydelsen for et PM03-arbejdscenter: serviceNo, matGroup.
Public Function Service(ByVal lk As Object, ByVal workCenterText As String) As Object
    Dim d As Object
    Dim full As String
    Dim suffix As String

    Set d = lk("services")
    full = VhpMap.WorkCenter(workCenterText)
    suffix = VhpMap.ServiceSuffix(workCenterText)
    ' Det fulde navn foerst - saa kan et enkelt vaerk have sin egen ydelse -
    ' og ellers endelsen, som det gamle WorkCenterDict.
    If d.Exists(full) Then
        Set Service = d(full)
    ElseIf d.Exists(suffix) Then
        Set Service = d(suffix)
    End If
End Function

'==============================================================================
' Indlaesning
'==============================================================================

Private Function ReadPlants() As Object
    Dim d As Object
    Dim vals As Variant
    Dim r As Long
    Dim key As String
    Dim rec As Object

    Set d = VhpUtil.NewDict()
    vals = TableValues(LO_PLANTS, 4)
    If IsEmpty(vals) Then
        Set ReadPlants = d
        Exit Function
    End If

    For r = LBound(vals, 1) To UBound(vals, 1)
        key = UCase$(Cell(vals, r, 1))
        If Len(key) > 0 And Not d.Exists(key) Then
            Set rec = VhpUtil.NewDict()
            rec.Add "sapPlant", Cell(vals, r, 2)
            rec.Add "profile", Cell(vals, r, 3)
            rec.Add "serviceSpec", Cell(vals, r, 4)
            d.Add key, rec
        End If
    Next r
    Set ReadPlants = d
End Function

Private Function ReadHorizons() As Object
    Dim d As Object
    Dim vals As Variant
    Dim r As Long
    Dim key As String
    Dim rec As Object
    Dim cycleText As String

    Set d = VhpUtil.NewDict()
    vals = TableValues(LO_HORIZON, 5)
    If IsEmpty(vals) Then
        Set ReadHorizons = d
        Exit Function
    End If

    For r = LBound(vals, 1) To UBound(vals, 1)
        cycleText = Replace(Cell(vals, r, 1), ",", ".")
        If Len(cycleText) > 0 And Len(Cell(vals, r, 2)) > 0 Then
            key = VhpMap.CycleKey(Val(cycleText), Cell(vals, r, 2))
            If Not d.Exists(key) Then
                Set rec = VhpUtil.NewDict()
                rec.Add "horizon", Cell(vals, r, 3)
                rec.Add "period", Cell(vals, r, 4)
                rec.Add "periodUnit", UCase$(Cell(vals, r, 5))
                d.Add key, rec
            End If
        End If
    Next r
    Set ReadHorizons = d
End Function

Private Function ReadServices() As Object
    Dim d As Object
    Dim vals As Variant
    Dim r As Long
    Dim key As String
    Dim rec As Object

    Set d = VhpUtil.NewDict()
    vals = TableValues(LO_SERVICES, 3)
    If IsEmpty(vals) Then
        Set ReadServices = d
        Exit Function
    End If

    For r = LBound(vals, 1) To UBound(vals, 1)
        key = UCase$(Cell(vals, r, 1))
        If Len(key) > 0 And Not d.Exists(key) Then
            Set rec = VhpUtil.NewDict()
            rec.Add "serviceNo", Cell(vals, r, 2)
            rec.Add "matGroup", Cell(vals, r, 3)
            d.Add key, rec
        End If
    Next r
    Set ReadServices = d
End Function

' Tabellens data som 2D-array (raekke, kolonne), mindst minCols kolonner.
' Empty, hvis tabellen mangler eller er tom.
Private Function TableValues(ByVal tableName As String, ByVal minCols As Long) As Variant
    Dim lo As ListObject
    Dim v As Variant

    On Error Resume Next
    Set lo = ThisWorkbook.Worksheets(SH_LOOKUP).ListObjects(tableName)
    On Error GoTo 0
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    If lo.ListColumns.Count < minCols Then Exit Function

    v = lo.DataBodyRange.Value
    ' En tabel med een celle giver en enkelt vaerdi, ikke et array.
    If Not IsArray(v) Then Exit Function
    TableValues = v
End Function

Private Function Cell(ByVal vals As Variant, ByVal r As Long, ByVal c As Long) As String
    If c > UBound(vals, 2) Then Exit Function
    If IsError(vals(r, c)) Then Exit Function
    Cell = Trim$(CStr(vals(r, c)))
End Function
