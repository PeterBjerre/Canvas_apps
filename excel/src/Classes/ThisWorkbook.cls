Option Explicit

Private Sub Workbook_Open()
  On Error Resume Next
  AddMenu
  EnsureMaintenancePlansImportButton
  On Error GoTo 0
End Sub

Private Sub Workbook_BeforeClose(Cancel As Boolean)
  On Error Resume Next
  RemoveMenu
  On Error GoTo 0
End Sub

Private Sub Workbook_SheetBeforeDoubleClick(ByVal Sh As Object, ByVal Target As Range, Cancel As Boolean)
  On Error GoTo SafeExit

  If Sh Is Nothing Then Exit Sub
  If Target Is Nothing Then Exit Sub

  Cancel = ToggleMaintenancePlansSelectionByCell(Target)

SafeExit:
End Sub

Private Sub Workbook_SheetChange(ByVal Sh As Object, ByVal Target As Range)
  On Error GoTo SafeExit

  If Sh Is Nothing Then Exit Sub
  If Target Is Nothing Then Exit Sub

  EnforceMaintenancePlansSelectionForRange Target

SafeExit:
End Sub
