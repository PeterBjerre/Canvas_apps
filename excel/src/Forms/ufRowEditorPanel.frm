VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ufRowEditorPanel 
   Caption         =   "UserForm1"
   ClientHeight    =   3015
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   4560
   OleObjectBlob   =   "ufRowEditorPanel.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ufRowEditorPanel"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Const PAD As Single = 12
Private Const FORM_W_STD As Single = 860
Private Const FORM_H_STD As Single = 560
Private Const FORM_W_WIDE As Single = 1120
Private Const FORM_H_WIDE As Single = 580
Private Const BTN_H As Single = 28
Private Const BTN_GAP As Single = 12
Private Const BTN_W_MAX As Single = 130
Private Const BTN_W_MIN As Single = 90
Private Const MIN_IW As Single = 560
Private Const MIN_IH As Single = 440
Private Const MIN_GRID_H As Single = 220
Private Const MIN_TXT_H As Single = 22

Private Const CLR_BG As Long = &HF7F2EE
Private Const CLR_INPUT As Long = &HFFFFFF
Private Const CLR_LABEL As Long = &H332413
Private Const CLR_BTN_BG As Long = &HF9F1EA
Private Const CLR_BTN_TXT As Long = &H332413

Private cLB As MSForms.ListBox
Private cLbl As MSForms.Label
Private cTxt As MSForms.TextBox
Private cRec As MSForms.Label
Private cPrev As MSForms.CommandButton
Private cNext As MSForms.CommandButton
Private cSave As MSForms.CommandButton
Private cClose As MSForms.CommandButton

Private mHost As Object
Private mHostList As MSForms.ListBox
Private mSheetName As String
Private mColCount As Long
Private mTagMap As Object

Private vFieldW As Single
Private vEditMax As Single

Public Sub InitHost(ByVal host As Object, ByVal hostList As MSForms.ListBox, ByVal sheetName As String)
    Set mHost = host
    Set mHostList = hostList
    mSheetName = sheetName
End Sub

Private Sub UserForm_Initialize()
    Me.caption = "Edit Row"
    Me.Width = FORM_W_STD
    Me.Height = FORM_H_STD
    Me.StartUpPosition = 0

    vFieldW = 260
    vEditMax = 520

    BuildUi
    ApplyTheme
    PlaceLayout
    CenterOnOwnerOrScreen
    BuildFromSelection
    UpdateNavUI
End Sub

Private Sub UserForm_Resize()
    On Error Resume Next
    PlaceLayout
End Sub

Private Sub BuildUi()
    Set cLB = EnsureListBox("lbGrid")
    Set cLbl = EnsureLabel("lblField")
    Set cTxt = EnsureTextBox("txtEdit")
    Set cRec = EnsureLabel("lblRec")
    Set cPrev = EnsureButton("cmdPrev", "Prev")
    Set cNext = EnsureButton("cmdNext", "Next")
    Set cSave = EnsureButton("cmdSave", "Save")
    Set cClose = EnsureButton("cmdClose", "Close")

    With cLB
        .ColumnCount = 3
        .ColumnHeads = False
        .MultiSelect = fmMultiSelectSingle
        .IntegralHeight = False
    End With

    ApplyFontUniform
End Sub

Private Function EnsureListBox(ByVal nm As String) As MSForms.ListBox
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then Set o = Me.Controls.Add("Forms.ListBox.1", nm, True)
    Set EnsureListBox = o
End Function

Private Function EnsureTextBox(ByVal nm As String) As MSForms.TextBox
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then Set o = Me.Controls.Add("Forms.TextBox.1", nm, True)
    Set EnsureTextBox = o
End Function

Private Function EnsureLabel(ByVal nm As String) As MSForms.Label
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then Set o = Me.Controls.Add("Forms.Label.1", nm, True)
    Set EnsureLabel = o
End Function

Private Function EnsureButton(ByVal nm As String, ByVal cap As String) As MSForms.CommandButton
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then
        Set o = Me.Controls.Add("Forms.CommandButton.1", nm, True)
        o.caption = cap
    End If
    Set EnsureButton = o
End Function

Private Sub ApplyFontUniform()
    On Error Resume Next
    Dim ctl As MSForms.Control
    For Each ctl In Me.Controls
        ctl.Font.name = "Calibri"
        ctl.Font.Size = 10
        ctl.Font.Bold = False
    Next ctl
    On Error GoTo 0
End Sub

Private Sub ApplyTheme()
    Me.BackColor = CLR_BG

    cLB.BackColor = CLR_INPUT
    cLB.ForeColor = CLR_LABEL
    cLB.BorderStyle = fmBorderStyleSingle
    cLB.SpecialEffect = fmSpecialEffectFlat

    cLbl.BackStyle = fmBackStyleTransparent
    cLbl.ForeColor = CLR_LABEL

    cRec.BackStyle = fmBackStyleTransparent
    cRec.ForeColor = CLR_LABEL

    cTxt.BackColor = CLR_INPUT
    cTxt.ForeColor = CLR_LABEL
    cTxt.BorderStyle = fmBorderStyleSingle
    cTxt.SpecialEffect = fmSpecialEffectFlat

    StyleBtn cPrev
    StyleBtn cNext
    StyleBtn cSave
    StyleBtn cClose
End Sub

Private Sub StyleBtn(ByVal b As MSForms.CommandButton)
    If b Is Nothing Then Exit Sub
    b.BackColor = CLR_BTN_BG
    b.ForeColor = CLR_BTN_TXT
    b.SpecialEffect = fmSpecialEffectRaised
    b.TakeFocusOnClick = False
End Sub

Private Sub BuildFromSelection()
    If mHostList Is Nothing Then Exit Sub
    If mHostList.ListIndex < 0 Then Exit Sub
    If Len(mHostList.rowSource) = 0 Then Exit Sub

    Set mTagMap = ParseTagMap(mHostList.Tag)

    Dim wsOV As Worksheet, bodyRng As Range
    Set bodyRng = mdlOverlayView.RangeFromRowSource(mHostList.rowSource, wsOV)
    If bodyRng Is Nothing Then Exit Sub

    Dim headers2D As Variant
    headers2D = mdlOverlayView.HeaderRangeFromBody(bodyRng).Value2

    mColCount = bodyRng.Columns.Count
    If mColCount < 2 Then Exit Sub

    cLB.Clear

    Dim i As Long
    For i = 1 To mColCount - 1
        Dim caption As String, fieldName As String, val As String
        caption = CStr(headers2D(1, i))
        If LCase$(caption) = "_rowindex" Then GoTo NextCol

        fieldName = FieldFromCaption(caption)
        val = CStr(mHostList.List(mHostList.ListIndex, i - 1))

        cLB.AddItem caption
        cLB.List(cLB.ListCount - 1, 1) = val
        cLB.List(cLB.ListCount - 1, 2) = fieldName

NextCol:
    Next i

    cRec.caption = CStr(mHostList.ListIndex + 1) & " of " & CStr(mHostList.ListCount)

    If cLB.ListCount > 0 Then
        cLB.ListIndex = 0
        cLbl.caption = cLB.List(0, 0)
        cTxt.text = cLB.List(0, 1)
        cTxt.SelStart = 0
        cTxt.SelLength = Len(cTxt.text)
    Else
        cLbl.caption = vbNullString
        cTxt.text = vbNullString
    End If
End Sub

Private Function ParseTagMap(ByVal tagText As String) As Object
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    dict.CompareMode = vbTextCompare

    tagText = Trim$(tagText)
    If Len(tagText) = 0 Then
        Set ParseTagMap = dict
        Exit Function
    End If

    Dim parts() As String
    parts = Split(tagText, TAGMAP_PAIR_SEP)

    Dim i As Long
    For i = LBound(parts) To UBound(parts)
        Dim p As String
        p = Trim$(parts(i))
        If Len(p) = 0 Then GoTo NextPart

        Dim kv() As String
        kv = Split(p, TAGMAP_KV_SEP)

        If UBound(kv) = 1 Then
            Dim cap As String, fld As String
            cap = Trim$(kv(0))
            fld = Trim$(kv(1))
            If Len(cap) > 0 And Len(fld) > 0 Then dict(cap) = fld
        End If

NextPart:
    Next i

    Set ParseTagMap = dict
End Function

Private Function FieldFromCaption(ByVal caption As String) As String
    If Not mTagMap Is Nothing Then
        If mTagMap.Exists(caption) Then
            FieldFromCaption = CStr(mTagMap(caption))
            Exit Function
        End If
    End If
    FieldFromCaption = caption
End Function

Private Sub PlaceLayout()
    Dim iw As Single, ih As Single
    iw = Me.Width - 30
    ih = Me.Height - 60

    If iw < MIN_IW Then iw = MIN_IW
    If ih < MIN_IH Then ih = MIN_IH

    Dim gridH As Single
    gridH = ih - 200
    If gridH < MIN_GRID_H Then gridH = MIN_GRID_H

    cLB.Left = PAD
    cLB.Top = PAD
    cLB.Width = iw - 2 * PAD
    cLB.Height = gridH

    cLbl.Left = PAD
    cLbl.Top = cLB.Top + cLB.Height + 10
    cLbl.Width = vFieldW
    cLbl.Height = 20

    cTxt.Left = cLbl.Left + cLbl.Width + 8
    cTxt.Top = cLbl.Top
    cTxt.Width = vEditMax
    If cTxt.Left + cTxt.Width > PAD + cLB.Width Then
        cTxt.Width = (PAD + cLB.Width) - cTxt.Left
    End If
    If cTxt.Width < 120 Then cTxt.Width = 120
    cTxt.Height = MIN_TXT_H

    cRec.Left = (PAD + cLB.Width) - 110
    cRec.Top = PAD
    cRec.Width = 110
    cRec.Height = 20

    Dim availRowW As Single, btnW As Single, totalW As Single
    availRowW = cLB.Width
    btnW = (availRowW - 3 * BTN_GAP) / 4
    If btnW < BTN_W_MIN Then btnW = BTN_W_MIN
    If btnW > BTN_W_MAX Then btnW = BTN_W_MAX

    totalW = 4 * btnW + 3 * BTN_GAP

    Dim rowTop As Single, rowLeft As Single
    rowTop = ih - PAD - BTN_H
    If rowTop < (cLbl.Top + cLbl.Height + 8) Then rowTop = cLbl.Top + cLbl.Height + 8

    rowLeft = PAD + (availRowW - totalW) / 2
    If rowLeft < PAD Then rowLeft = PAD

    cPrev.Left = rowLeft
    cPrev.Top = rowTop
    cPrev.Width = btnW
    cPrev.Height = BTN_H

    cNext.Left = cPrev.Left + btnW + BTN_GAP
    cNext.Top = rowTop
    cNext.Width = btnW
    cNext.Height = BTN_H

    cSave.Left = cNext.Left + btnW + BTN_GAP
    cSave.Top = rowTop
    cSave.Width = btnW
    cSave.Height = BTN_H

    cClose.Left = cSave.Left + btnW + BTN_GAP
    cClose.Top = rowTop
    cClose.Width = btnW
    cClose.Height = BTN_H

    cLB.ColumnWidths = CStr(vFieldW) & ";" & CStr(cLB.Width - vFieldW - 30) & ";0"
End Sub

Private Sub CenterOnOwnerOrScreen()
    On Error Resume Next
    Dim pL As Double, pT As Double, pW As Double, pH As Double
    If Not mHost Is Nothing Then
        pL = mHost.Left
        pT = mHost.Top
        pW = mHost.Width
        pH = mHost.Height
    Else
        pL = Application.Left
        pT = Application.Top
        pW = Application.Width
        pH = Application.Height
    End If
    Me.Left = pL + (pW - Me.Width) / 2
    Me.Top = pT + (pH - Me.Height) / 2
End Sub

Private Sub UpdateNavUI()
    If mHostList Is Nothing Then Exit Sub
    cPrev.Enabled = (mHostList.ListIndex > 0)
    cNext.Enabled = (mHostList.ListIndex < mHostList.ListCount - 1)
End Sub

Private Sub cLB_Click()
    If cLB.ListIndex >= 0 Then
        cLbl.caption = cLB.List(cLB.ListIndex, 0)
        cTxt.text = cLB.List(cLB.ListIndex, 1)
        cTxt.SelStart = 0
        cTxt.SelLength = Len(cTxt.text)
        cTxt.SetFocus
    End If
End Sub

Private Sub cTxt_Change()
    If cLB.ListIndex >= 0 Then
        cLB.List(cLB.ListIndex, 1) = cTxt.text
    End If
End Sub

Private Sub cPrev_Click()
    If mHostList Is Nothing Then Exit Sub
    If mHostList.ListIndex > 0 Then
        mHostList.ListIndex = mHostList.ListIndex - 1
        BuildFromSelection
        UpdateNavUI
    End If
End Sub

Private Sub cNext_Click()
    If mHostList Is Nothing Then Exit Sub
    If mHostList.ListIndex < mHostList.ListCount - 1 Then
        mHostList.ListIndex = mHostList.ListIndex + 1
        BuildFromSelection
        UpdateNavUI
    End If
End Sub

Private Sub cClose_Click()
    Me.Hide
End Sub

Private Sub cSave_Click()
    DoSave
End Sub

Private Sub DoSave()
    On Error GoTo EH

    If mHostList Is Nothing Then Exit Sub
    If mHostList.ListIndex < 0 Then Exit Sub
    If Len(mHostList.rowSource) = 0 Then Exit Sub

    Dim wsOV As Worksheet, bodyRng As Range
    Set bodyRng = mdlOverlayView.RangeFromRowSource(mHostList.rowSource, wsOV)
    If bodyRng Is Nothing Then Exit Sub

    Dim srcRow As Long
    srcRow = CLng(mHostList.List(mHostList.ListIndex, bodyRng.Columns.Count - 1))

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(mSheetName)
    If ws Is Nothing Then Exit Sub

    Dim lo As ListObject, dataRowIdx As Long
    Set lo = FindListObjectForRow(ws, srcRow, dataRowIdx)

    Dim i As Long, Value As String, fieldName As String, col As Long
    For i = 0 To cLB.ListCount - 1
        Value = CStr(cLB.List(i, 1))
        fieldName = CStr(cLB.List(i, 2))
        If Len(fieldName) = 0 Then fieldName = CStr(cLB.List(i, 0))
        If IsKeyField(fieldName) Then GoTo NextI

        If Not lo Is Nothing And dataRowIdx > 0 Then
            col = FindHeaderInListObject(lo, fieldName)
            If col > 0 Then lo.DataBodyRange.Cells(dataRowIdx, col).Value2 = Value
        Else
            col = FindHeaderIndex(ws, fieldName)
            If col > 0 Then ws.Cells(srcRow, col).Value2 = Value
        End If

NextI:
    Next i

    Me.Hide
    Exit Sub

EH:
    MsgBox "Save failed: " & Err.Number & " - " & Err.Description, vbExclamation, "Save"
End Sub

Private Function IsKeyField(ByVal fieldName As String) As Boolean
    Dim f As String
    f = LCase$(Trim$(fieldName))
    IsKeyField = (f = "aufnr" Or f = "objnr" Or f = "vornr" Or f = "_rowindex")
End Function

Private Function FindHeaderIndex(ByVal ws As Worksheet, ByVal headerName As String, Optional ByVal headerRow As Long = 1) As Long
    Dim lastCol As Long, c As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(headerRow, c).Value2)), headerName, vbTextCompare) = 0 Then
            FindHeaderIndex = c
            Exit Function
        End If
    Next c
    FindHeaderIndex = 0
End Function

Private Function FindListObjectForRow(ByVal ws As Worksheet, ByVal rowIdx As Long, ByRef dataRowIdx As Long) As ListObject
    On Error Resume Next
    Dim lo As ListObject
    For Each lo In ws.ListObjects
        If Not lo.DataBodyRange Is Nothing Then
            If rowIdx >= lo.DataBodyRange.Row And rowIdx < lo.DataBodyRange.Row + lo.DataBodyRange.rows.Count Then
                Set FindListObjectForRow = lo
                dataRowIdx = rowIdx - lo.DataBodyRange.Row + 1
                Exit Function
            End If
        End If
    Next lo
    Set FindListObjectForRow = Nothing
    dataRowIdx = 0
End Function

Private Function FindHeaderInListObject(ByVal lo As ListObject, ByVal headerName As String) As Long
    On Error Resume Next
    Dim lc As ListColumn
    For Each lc In lo.ListColumns
        If StrComp(Trim$(CStr(lc.Range.Cells(1, 1).Value2)), headerName, vbTextCompare) = 0 Then
            FindHeaderInListObject = lc.index
            Exit Function
        End If
    Next lc
    FindHeaderInListObject = 0
End Function

Private Sub cTxt_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If KeyCode = vbKeyReturn Then cSave_Click
End Sub
