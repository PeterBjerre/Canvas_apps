Attribute VB_Name = "modOverlayUiLayout"
Option Explicit

Private Const LC_OFFSET_Y As Single = 140

Public Sub LayoutOverlay(ByVal frm As Object, ByVal ui As Object)
    On Error Resume Next
    If frm Is Nothing Then Exit Sub
    If ui Is Nothing Then Exit Sub
    frm.StartUpPosition = 0
    PositionLeftCenter frm, LC_OFFSET_Y
    On Error GoTo 0
End Sub

Private Sub PositionLeftCenter(ByVal frm As Object, ByVal offsetY As Single)
    On Error Resume Next

    Dim w As Window
    Set w = Nothing
    Set w = ThisWorkbook.Windows(1)
    If w Is Nothing Then Set w = Application.ActiveWindow

    Dim marginLeft As Double
    marginLeft = 12

    If Not w Is Nothing Then
        frm.Left = w.Left + marginLeft
        frm.Top = w.Top + (w.Height / 2) - (frm.Height / 2) + offsetY
    Else
        frm.Left = marginLeft
        frm.Top = Application.UsableHeight / 2 - frm.Height / 2 + offsetY
    End If

    If frm.Top < 0 Then frm.Top = 0
    If frm.Left < 0 Then frm.Left = 0

    On Error GoTo 0
End Sub
