Attribute VB_Name = "Verification_ClassBlocks"
Option Explicit

Public Sub Design_pressure_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim designPressureUOM As Variant, tableRange As Range, tableColumn As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("Design_pressure_uom").Range
    Set tableColumn = tableRange.Columns(1)
    designPressureUOM = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Design pressure uom", designPressureUOM
    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Design pressure", Array(12, "^[0-9.,\-\/\+]*$")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
End Sub

Public Sub Operating_pressure_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim operatingPressureUOM As Variant, tableRange As Range, tableColumn As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("Design_pressure_uom").Range
    Set tableColumn = tableRange.Columns(1)
    operatingPressureUOM = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Operating pressure uom", operatingPressureUOM

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Operating pressure", Array(12, "^[0-9.,\-\/\+]*$")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
End Sub

Public Sub Design_temperature_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim designTemperatureUOM As Variant, tableRange As Range, tableColumn As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("Design_Temp_uom").Range
    Set tableColumn = tableRange.Columns(1)
    designTemperatureUOM = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Design temperature uom", designTemperatureUOM

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Design temperature", Array(8, "^[0-9.,\-\/\+]*$")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
End Sub

Public Sub Operating_temperature_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim operatingTemperatureUOM As Variant, tableRange As Range, tableColumn As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("Design_Temp_uom").Range
    Set tableColumn = tableRange.Columns(1)
    operatingTemperatureUOM = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Operating temperature uom", operatingTemperatureUOM

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Operating temperature", Array(10, "^[0-9.,\-\/\+]*$")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
End Sub

Public Sub Design_flow_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim designFlowUOM As Variant, tableRange As Range, tableColumn As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("Design_flow_uom").Range
    Set tableColumn = tableRange.Columns(1)
    designFlowUOM = Application.Transpose(tableColumn.value)

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Design flow uom", designFlowUOM

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Design flow", Array(10, "^[0-9.,\-\/\+]*$")

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
End Sub

Public Sub ELF_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Full load current [A]", Array(8, "^[0-9,]*$")
    formatColumns.Add "IP class", Array(30, ".*")
    formatColumns.Add "Power [kW]", Array(13, "^[0-9,]*$")
    formatColumns.Add "Remarks", Array(30, ".*")
    formatColumns.Add "Supply from", Array(30, ".*")
    formatColumns.Add "Voltage [V]", Array(7, "^[0-9,]*$")
    formatColumns.Add "Switching Location", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub GIV_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "IP class", Array(30, ".*")
    formatColumns.Add "Junction box", Array(18, ".*")
    formatColumns.Add "Mechanical measur. range from", Array(30, ".*")
    formatColumns.Add "Mechanical measuring range to", Array(12, ".*")
    formatColumns.Add "Mechanical measuring range uom", Array(17, ".*")
    formatColumns.Add "Output value", Array(30, ".*")
    formatColumns.Add "Output value uom", Array(18, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    formatColumns.Add "Signal applications", Array(20, ".*")
    formatColumns.Add "Supply from", Array(30, ".*")
    formatColumns.Add "Other Information", Array(30, ".*")
    formatColumns.Add "Owner", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub KAB_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Cable type", Array(18, ".*")
    formatColumns.Add "Dimension", Array(18, ".*")
    formatColumns.Add "Dimension uom", Array(15, ".*$")
    formatColumns.Add "Drawn cable length [m]", Array(5, "^[0-9,]*$")
    formatColumns.Add "From functional location", Array(30, ".*")
    formatColumns.Add "To functional location", Array(30, ".*")
    formatColumns.Add "Voltage [V]", Array(7, "^[0-9,]*$")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MAA_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_AC_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Close torque in Nm", Array(10, "^[0-9.,]*$")
    formatColumns.Add "Drive time requirements in sec", Array(10, "^[0-9.,]*$")
    formatColumns.Add "Open torque in Nm", Array(10, "^[0-9.,]*$")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_FA_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_FI_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Control class (lovpligtig)", Array(5, ".*")
    formatColumns.Add "DN/Volume", Array(15, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_HE_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Secondary medium", Array(30, ".*")
    formatColumns.Add "Primary medium", Array(20, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_PI_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Control class (lovpligtig)", Array(5, ".*")
    formatColumns.Add "DN/Volume", Array(15, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_PU_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Design lifting height", Array(8, "^[0-9.,]*$")
    formatColumns.Add "Design lifting height uom", Array(15, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_TA_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Control class (lovpligtig)", Array(5, ".*")
    formatColumns.Add "DN/Volume", Array(15, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub MKP_VA_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "DN/Volume", Array(15, ".*")
    formatColumns.Add "Medium", Array(20, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub RBR_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Design pos cold", Array(10, ".*")
    formatColumns.Add "Design pos warm", Array(10, ".*")
    formatColumns.Add "Direction of movement", Array(17, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    formatColumns.Add "Setting cold vertical [kN]", Array(17, "^[0-9.,]*$")
    formatColumns.Add "Setting cold vertical [mm]", Array(17, "^[0-9.,]*$")
    formatColumns.Add "Setting warm vertical [kN]", Array(17, "^[0-9.,]*$")
    formatColumns.Add "Setting warm vertical [mm]", Array(17, "^[0-9.,]*$")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub TAF_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Consumer FL", Array(30, ".*")
    formatColumns.Add "Nominel current, compartment", Array(10, ".*")
    formatColumns.Add "Remarks", Array(30, ".*")
    formatColumns.Add "Voltage [V]", Array(7, "^[0-9.,]*$")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub UNF_Core(ByVal Class As String)
    Dim formatColumns As Object

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "Remarks", Array(30, ".*")
    Verification_Functions.ValidateTable Class, formatColumns
End Sub

Public Sub TRMNEW_Core(ByVal Class As String)
    Dim ws As Worksheet, listWs As Worksheet
    Dim FireClass As Variant, FIRESEALTYPE As Variant, validSCEs As Variant
    Dim tableRange As Range, tableColumn As Range
    Dim sceTable As ListObject
    Dim sceColumn As ListColumn
    Dim sceData As Range
    Dim formatColumns As Object, specialColumns As Object, lastColumn As Long

    Set ws = ThisWorkbook.Sheets(Class)
    Set listWs = ThisWorkbook.Sheets("List data")
    lastColumn = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

    Set tableRange = listWs.ListObjects("FireClassification").Range
    Set tableColumn = tableRange.Columns(1)
    FireClass = Application.Transpose(tableColumn.value)

    Set tableRange = listWs.ListObjects("Table20").Range
    Set tableColumn = tableRange.Columns(1)
    FIRESEALTYPE = Application.Transpose(tableColumn.value)

    Set sceTable = ThisWorkbook.Sheets("List data").ListObjects("SCEq")
    If sceTable Is Nothing Then Exit Sub

    Set sceColumn = sceTable.ListColumns(Class)
    If sceColumn Is Nothing Then Exit Sub

    Set sceData = sceColumn.DataBodyRange
    If sceData Is Nothing Then
        validSCEs = Array()
    Else
        validSCEs = sceData.Value2
    End If

    Set specialColumns = CreateObject("Scripting.Dictionary")
    specialColumns.Add "Safety Critical Equipment", validSCEs

    If Class = "MKP" Or Class = "NO CLASS" Then
        specialColumns.Add "Fire Classification", FireClass
        specialColumns.Add "Fire Sealing Type", FIRESEALTYPE
    End If

    Set formatColumns = CreateObject("Scripting.Dictionary")
    formatColumns.Add "EX-Marking", Array(30, ".*")
    If Class = "MKP" Or Class = "NO CLASS" Then
        formatColumns.Add "Fire Sealing Product", Array(30, ".*")
    End If

    Verification_Functions.ValidateTable Class, formatColumns, specialColumns
    Verification.AutoSetTRMAndABC Class

    If UCase$(Trim$(Class)) = "MKP" Then
        ApplyMKPBR18TRMRule ws
    End If
End Sub

Private Sub ApplyMKPBR18TRMRule(ByVal ws As Worksheet)
    Dim colIndex As Object
    Dim colTRM As Long, colFire As Long, colSealType As Long, colSealProd As Long
    Dim lastRow As Long
    Dim scopedRows As Object
    Dim rowKey As Variant
    Dim i As Long

    Set colIndex = Verification_Cache.GetColIndex(ws)

    colTRM = Verification_Cache.LookupCol(colIndex, "TRM assignment")
    colFire = Verification_Cache.LookupCol(colIndex, "Fire Classification")
    colSealType = Verification_Cache.LookupCol(colIndex, "Fire Sealing Type")
    colSealProd = Verification_Cache.LookupCol(colIndex, "Fire Sealing Product")

    If colTRM = 0 Then
        MsgBox ValidationMessages.HeaderColumnNotFound("TRM assignment"), vbExclamation
        Exit Sub
    End If
    If colFire = 0 Then
        MsgBox ValidationMessages.HeaderColumnNotFound("Fire Classification"), vbExclamation
        Exit Sub
    End If
    If colSealType = 0 Then
        MsgBox ValidationMessages.HeaderColumnNotFound("Fire Sealing Type"), vbExclamation
        Exit Sub
    End If
    If colSealProd = 0 Then
        MsgBox ValidationMessages.HeaderColumnNotFound("Fire Sealing Product"), vbExclamation
        Exit Sub
    End If

    lastRow = ws.Cells(ws.Rows.count, "D").End(xlUp).Row
    If lastRow < 4 Then Exit Sub

    Set scopedRows = Verification_Functions.GetScopedChangedRows()
    If Not scopedRows Is Nothing Then
        For Each rowKey In scopedRows.keys
            i = CLng(rowKey)
            If i >= 4 And i <= lastRow Then
                ApplyMKPBR18RowRule ws, i, colTRM, colFire, colSealType, colSealProd
            End If
        Next rowKey
        Exit Sub
    End If

    For i = 4 To lastRow
        ApplyMKPBR18RowRule ws, i, colTRM, colFire, colSealType, colSealProd
    Next i
End Sub

Private Sub ApplyMKPBR18RowRule( _
    ByVal ws As Worksheet, _
    ByVal rowNum As Long, _
    ByVal colTRM As Long, _
    ByVal colFire As Long, _
    ByVal colSealType As Long, _
    ByVal colSealProd As Long _
)
    Dim fl As String
    Dim key12 As String
    Dim key17 As String

    fl = UCase$(Trim$(CStr(ws.Cells(rowNum, "D").Value2)))
    If Len(fl) < 13 Then Exit Sub

    key12 = Mid$(fl, 12, 2)
    ' BR18 auto-assignment applies only to aggregate key UE.
    If key12 <> "UE" Then Exit Sub

    key17 = ""
    If Len(fl) >= 18 Then key17 = Mid$(fl, 17, 2)

    ws.Cells(rowNum, colTRM).value = "X"
    Verification_Functions.HighlightValid ws.Cells(rowNum, colTRM)

    If key17 = "FP" Then
        ValidateMKPBR18RequiredField ws, rowNum, colFire, "Fire Classification", key17
        ValidateMKPBR18RequiredField ws, rowNum, colSealType, "Fire Sealing Type", key17
        ValidateMKPBR18RequiredField ws, rowNum, colSealProd, "Fire Sealing Product", key17
    Else
        ValidateMKPBR18RequiredField ws, rowNum, colFire, "Fire Classification", key17
    End If
End Sub

Private Sub ValidateMKPBR18RequiredField( _
    ByVal ws As Worksheet, _
    ByVal rowNum As Long, _
    ByVal colNum As Long, _
    ByVal fieldName As String, _
    ByVal key17 As String _
)
    Dim valueText As String

    valueText = Trim$(CStr(ws.Cells(rowNum, colNum).Value2))
    If Len(valueText) = 0 Then
        Verification_Functions.HighlightError ws.Cells(rowNum, colNum)
        Verification_Functions.AddCellComment ws.Cells(rowNum, colNum), ValidationMessages.MKPBR18FieldRequired(fieldName, key17)
    End If
End Sub

Public Sub VerifyFunctionalLocationClasses_Core(ByVal Class As String)
    Dim ws As Worksheet
    Dim tblComponent As ListObject, tblAggregate As ListObject
    Dim loRow As ListRow
    Dim classDictComponent As Object, classDictAggregate As Object
    Dim expectedClass As String
    Dim compKey As String
    Dim keyPartComponent As String, keyPartAggregate As String
    Dim actualClass As String
    Dim lastRow As Long, i As Long
    Dim matchFound As Boolean

    For Each ws In ThisWorkbook.Worksheets
        On Error Resume Next
        Set tblComponent = ws.ListObjects("ClassDeterminationComponentKey")
        Set tblAggregate = ws.ListObjects("ClassDeterminationAggregateKey")
        On Error GoTo 0
        If Not tblComponent Is Nothing And Not tblAggregate Is Nothing Then Exit For
    Next ws

    If tblComponent Is Nothing Then
        MsgBox ValidationMessages.TableNotFound("ClassDeterminationComponentKey"), vbCritical
        Exit Sub
    End If

    If tblAggregate Is Nothing Then
        MsgBox ValidationMessages.TableNotFound("ClassDeterminationAggregateKey"), vbCritical
        Exit Sub
    End If

    Set classDictComponent = CreateObject("Scripting.Dictionary")
    Set classDictAggregate = CreateObject("Scripting.Dictionary")

    For Each loRow In tblComponent.ListRows
        compKey = loRow.Range(1, 1).value
        expectedClass = loRow.Range(1, 2).value
        classDictComponent(compKey) = expectedClass
    Next loRow

    For Each loRow In tblAggregate.ListRows
        compKey = loRow.Range(1, 1).value
        expectedClass = loRow.Range(1, 2).value
        classDictAggregate(compKey) = expectedClass
    Next loRow

    Set ws = ThisWorkbook.Sheets(Class)
    If ws Is Nothing Then Exit Sub

    actualClass = ws.name
    lastRow = ws.Cells(ws.Rows.count, "D").End(xlUp).Row

    For i = 4 To lastRow
        compKey = ws.Cells(i, "D").value
        keyPartComponent = Mid(compKey, 18, 2)
        keyPartAggregate = Mid(compKey, 12, 2)
        matchFound = False

        If keyPartComponent <> "" Then
            If classDictComponent.exists(keyPartComponent) Then
                expectedClass = classDictComponent(keyPartComponent)
                matchFound = True
            End If
        End If

        If Not matchFound And keyPartAggregate <> "" Then
            If classDictAggregate.exists(keyPartAggregate) Then
                expectedClass = classDictAggregate(keyPartAggregate)
                matchFound = True
            End If
        End If
    Next i
End Sub
