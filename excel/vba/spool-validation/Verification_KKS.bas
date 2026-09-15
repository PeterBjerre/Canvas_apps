Attribute VB_Name = "Verification_KKS"
Option Explicit

' Dedicated KKS-related verification rules extracted from Verification module.
Public Sub KKS_Syntax(ByVal Class As String)
    Dim ws As Worksheet
    Dim lastRow As Long, i As Long
    Dim fl As String
    Dim regex As Object, p As Variant
    Dim patterns As Variant
    Dim seen As Object
    Dim ok As Boolean

    Set ws = ThisWorkbook.Sheets(Class)
    If ws Is Nothing Then Exit Sub

    lastRow = ws.Cells(ws.Rows.count, "D").End(xlUp).Row
    If lastRow < 4 Then Exit Sub

    patterns = KKSRules.GetKKSPatterns()

    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = False

    Set seen = CreateObject("Scripting.Dictionary")
    seen.CompareMode = vbTextCompare

    For i = 4 To lastRow
        fl = CStr(ws.Cells(i, "D").Value2)
        fl = Replace(fl, Chr$(160), " ")
        fl = Replace(fl, vbCr, "")
        fl = Replace(fl, vbLf, "")

        Dim flUpper As String
        flUpper = UCase$(Trim$(fl))

        If Len(flUpper) = 0 Then
            ws.Cells(i, "D").Interior.ColorIndex = xlColorIndexNone
        Else
            If seen.exists(flUpper) Then
                Verification_Functions.HighlightError ws.Cells(i, "D")
                Verification_Functions.AddCellComment ws.Cells(i, "D"), ValidationMessages.DuplicateKKSSyntaxCode()
            Else
                seen.Add flUpper, True

                ok = False
                For Each p In patterns
                    regex.pattern = p
                    If regex.Test(flUpper) Then ok = True: Exit For
                Next p

                If ok Then
                    Verification_Functions.HighlightValid ws.Cells(i, "D")
                ElseIf KKSRules.IsLegacyHyphenFNumbering(flUpper) Then
                    Verification_Functions.HighlightWarning ws.Cells(i, "D")
                    Verification_Functions.AddCellComment ws.Cells(i, "D"), ValidationMessages.LegacyNumberingOnlyAcceptedIfExistingInPlant()
                Else
                    Verification_Functions.HighlightError ws.Cells(i, "D")
                    Verification_Functions.AddCellComment ws.Cells(i, "D"), ValidationMessages.InvalidKKSSyntax()
                End If
            End If
        End If
    Next i
End Sub

Public Sub AutoSetTRMAndABC(ByVal Class As String)
    Dim ws As Worksheet
    Dim colIndex As Object
    Dim colTRM As Long, colEX As Long, colSCE As Long, colFire As Long, colSealType As Long, colSealProd As Long
    Dim colABC As Long
    Dim lastRow As Long, i As Long
    Dim hasTRMValue As Boolean
    Dim v As String
    Dim prevEvt As Boolean
    Dim scopedRows As Object
    Dim rowKey As Variant

    On Error GoTo SafeExit

    Set ws = ThisWorkbook.Sheets(Class)
    If ws Is Nothing Then Exit Sub

    Set colIndex = Verification_Cache.GetColIndex(ws)

    colTRM = Verification_Cache.LookupCol(colIndex, "TRM assignment")
    colEX = Verification_Cache.LookupCol(colIndex, "EX-Marking")
    colSCE = Verification_Cache.LookupCol(colIndex, "Safety Critical Equipment")
    colFire = Verification_Cache.LookupCol(colIndex, "Fire Classification")
    colSealType = Verification_Cache.LookupCol(colIndex, "Fire Sealing Type")
    colSealProd = Verification_Cache.LookupCol(colIndex, "Fire Sealing Product")
    colABC = Verification_Cache.LookupCol(colIndex, "ABC Indic.")

    If colTRM = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.count, "D").End(xlUp).Row
    If lastRow < 4 Then Exit Sub

    prevEvt = Application.EnableEvents
    Application.EnableEvents = False

    Set scopedRows = Verification_Functions.GetScopedChangedRows()

    If Not scopedRows Is Nothing Then
        For Each rowKey In scopedRows.keys
            i = CLng(rowKey)
            If i >= 4 And i <= lastRow Then
                hasTRMValue = False

                If colEX > 0 Then
                    v = Trim$(CStr(ws.Cells(i, colEX).Value2))
                    If Len(v) > 0 Then hasTRMValue = True
                End If

                If Not hasTRMValue And colSCE > 0 Then
                    v = Trim$(CStr(ws.Cells(i, colSCE).Value2))
                    If Len(v) > 0 Then hasTRMValue = True
                End If

                If Not hasTRMValue And colFire > 0 Then
                    v = Trim$(CStr(ws.Cells(i, colFire).Value2))
                    If Len(v) > 0 Then hasTRMValue = True
                End If

                If Not hasTRMValue And colSealType > 0 Then
                    v = Trim$(CStr(ws.Cells(i, colSealType).Value2))
                    If Len(v) > 0 Then hasTRMValue = True
                End If

                If Not hasTRMValue And colSealProd > 0 Then
                    v = Trim$(CStr(ws.Cells(i, colSealProd).Value2))
                    If Len(v) > 0 Then hasTRMValue = True
                End If

                If hasTRMValue Then
                    ws.Cells(i, colTRM).value = "X"
                    ws.Cells(i, colTRM).Interior.Color = RGB(144, 238, 144)
                    If colABC > 0 Then ws.Cells(i, colABC).value = "A"
                Else
                    ws.Cells(i, colTRM).value = ""
                    If colABC > 0 Then ws.Cells(i, colABC).value = ""
                End If
            End If
        Next rowKey
        GoTo SafeExit
    End If

    For i = 4 To lastRow
        hasTRMValue = False

        If colEX > 0 Then
            v = Trim$(CStr(ws.Cells(i, colEX).Value2))
            If Len(v) > 0 Then hasTRMValue = True
        End If

        If Not hasTRMValue And colSCE > 0 Then
            v = Trim$(CStr(ws.Cells(i, colSCE).Value2))
            If Len(v) > 0 Then hasTRMValue = True
        End If

        If Not hasTRMValue And colFire > 0 Then
            v = Trim$(CStr(ws.Cells(i, colFire).Value2))
            If Len(v) > 0 Then hasTRMValue = True
        End If

        If Not hasTRMValue And colSealType > 0 Then
            v = Trim$(CStr(ws.Cells(i, colSealType).Value2))
            If Len(v) > 0 Then hasTRMValue = True
        End If

        If Not hasTRMValue And colSealProd > 0 Then
            v = Trim$(CStr(ws.Cells(i, colSealProd).Value2))
            If Len(v) > 0 Then hasTRMValue = True
        End If

        If hasTRMValue Then
            ws.Cells(i, colTRM).value = "X"
            ws.Cells(i, colTRM).Interior.Color = RGB(144, 238, 144)
            If colABC > 0 Then ws.Cells(i, colABC).value = "A"
        Else
            ws.Cells(i, colTRM).value = ""
            If colABC > 0 Then ws.Cells(i, colABC).value = ""
        End If
    Next i

SafeExit:
    Application.EnableEvents = prevEvt
End Sub
