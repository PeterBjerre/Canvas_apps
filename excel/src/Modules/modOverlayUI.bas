Attribute VB_Name = "modOverlayUI"
Option Explicit

Public Const UI_FONT_NAME As String = "Calibri"

Public Const UI_BG As Long = 16249582
Public Const UI_PANEL As Long = 16116965
Public Const UI_LABEL As Long = 4864815
Public Const UI_INPUT_BG As Long = 16777215
Public Const UI_BORDER As Long = 14866125

Public Const UI_MUTED As Long = 8421504
Public Const UI_ACCENT As Long = 16755320
Public Const UI_ACCENT_DARK As Long = 16755320

Public Const UI_BTN_BG As Long = 16380394
Public Const UI_BTN_HOVER_BG As Long = 16050141
Public Const UI_BTN_TXT As Long = 3351571
Public Const UI_BTN_HOVER_TXT As Long = 16777215

Public Const UI_TRACK_BG As Long = 15393500
Public Const UI_BAR_BG As Long = 16755320

Public Sub ApplyPalette(ByVal f As Object)
    On Error Resume Next
    f.BackColor = UI_BG
    Dim ctl As Object
    For Each ctl In f.Controls
        ApplyPaletteToControl ctl
    Next ctl
    On Error GoTo 0
End Sub

Private Sub ApplyPaletteToControl(ByVal ctl As Object)
    On Error Resume Next
    Select Case TypeName(ctl)
        Case "Frame"
            ctl.BackColor = UI_PANEL
            ctl.SpecialEffect = fmSpecialEffectFlat
            Dim c As Object
            For Each c In ctl.Controls
                ApplyPaletteToControl c
            Next c
        Case "Label"
            ctl.ForeColor = UI_LABEL
            ctl.BackStyle = fmBackStyleTransparent
        Case "TextBox"
            ctl.BackColor = UI_INPUT_BG
            ctl.ForeColor = UI_LABEL
            ctl.BorderStyle = fmBorderStyleSingle
            ctl.SpecialEffect = fmSpecialEffectFlat
        Case "ListBox"
            ctl.BackColor = UI_INPUT_BG
            ctl.ForeColor = UI_LABEL
            ctl.BorderStyle = fmBorderStyleSingle
            ctl.SpecialEffect = fmSpecialEffectFlat
            ctl.IntegralHeight = False
        Case "ComboBox"
            ctl.BackColor = UI_INPUT_BG
            ctl.ForeColor = UI_LABEL
        Case "CommandButton"
            StyleButton ctl
    End Select
    On Error GoTo 0
End Sub

Public Sub ApplyFontUniform(ByVal f As Object, Optional ByVal sizePt As Single = 10!, Optional ByVal isBold As Boolean = False)
    On Error Resume Next
    Dim ctl As Object
    For Each ctl In f.Controls
        ApplyFontToControl ctl, sizePt, isBold
    Next ctl
    On Error GoTo 0
End Sub

Private Sub ApplyFontToControl(ByVal ctl As Object, ByVal sizePt As Single, ByVal isBold As Boolean)
    On Error Resume Next
    ctl.Font.name = UI_FONT_NAME
    ctl.Font.Size = sizePt
    ctl.Font.Bold = isBold
    If TypeName(ctl) = "Frame" Then
        Dim c As Object
        For Each c In ctl.Controls
            ApplyFontToControl c, sizePt, isBold
        Next c
    End If
    On Error GoTo 0
End Sub

Public Sub StyleButton(ByVal Btn As Object)
    On Error Resume Next
    Btn.BackColor = UI_BTN_BG
    Btn.ForeColor = UI_BTN_TXT
    Btn.SpecialEffect = fmSpecialEffectFlat
    Btn.TakeFocusOnClick = False
    Btn.Font.name = UI_FONT_NAME
    Btn.Font.Size = 9
    Btn.Font.Bold = False
    On Error GoTo 0
End Sub

Public Sub StyleListBox(ByVal lb As Object)
    On Error Resume Next
    lb.BackColor = UI_INPUT_BG
    lb.ForeColor = UI_LABEL
    lb.BorderStyle = fmBorderStyleSingle
    lb.SpecialEffect = fmSpecialEffectFlat
    lb.IntegralHeight = False
    lb.MultiSelect = fmMultiSelectSingle
    On Error GoTo 0
End Sub

Public Sub StyleTextBox(ByVal tb As Object, Optional ByVal multiline As Boolean = False, Optional ByVal vScroll As Boolean = False, Optional ByVal locked As Boolean = False)
    On Error Resume Next
    tb.BackColor = UI_INPUT_BG
    tb.ForeColor = UI_LABEL
    tb.BorderStyle = fmBorderStyleSingle
    tb.SpecialEffect = fmSpecialEffectFlat
    tb.multiline = multiline
    If vScroll Then tb.ScrollBars = fmScrollBarsVertical
    tb.locked = locked
    On Error GoTo 0
End Sub

Public Sub FixZOrder(ByVal f As Object)
    On Error Resume Next
    Dim ctl As Object
    For Each ctl In f.Controls
        If TypeName(ctl) = "Label" Then ctl.ZOrder 0
    Next ctl
    For Each ctl In f.Controls
        If TypeName(ctl) = "CommandButton" Then ctl.ZOrder 0
    Next ctl
    On Error GoTo 0
End Sub

Public Sub ForceRefresh(ByVal f As Object)
    On Error Resume Next
    DoEvents
    f.Repaint
    On Error GoTo 0
End Sub

Public Function HookHoverButtons(ByVal frm As Object) As Collection
    Dim col As Collection
    Set col = New Collection
    AttachHoverRecursive frm, frm, col
    Set HookHoverButtons = col
End Function

Private Sub AttachHoverRecursive(ByVal root As Object, ByVal parent As Object, ByVal col As Collection)
    On Error Resume Next
    Dim ctl As Object
    For Each ctl In parent.Controls
        If TypeName(ctl) = "CommandButton" Then
            Dim hb As clsHoverButton
            Set hb = New clsHoverButton
            hb.Init root, ctl, UI_BTN_BG, UI_BTN_HOVER_BG, UI_BTN_TXT, UI_BTN_HOVER_TXT
            col.Add hb
        ElseIf TypeName(ctl) = "Frame" Then
            AttachHoverRecursive root, ctl, col
        End If
    Next ctl
    On Error GoTo 0
End Sub

Public Sub ResetHoverButtons(ByVal hoverButtons As Collection)
    On Error Resume Next
    If hoverButtons Is Nothing Then Exit Sub
    Dim i As Long
    For i = 1 To hoverButtons.Count
        hoverButtons(i).ApplyNormal
    Next i
    On Error GoTo 0
End Sub
