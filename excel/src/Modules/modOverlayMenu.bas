Attribute VB_Name = "modOverlayMenu"
Option Explicit

Public Sub OverlayRowMenu_Edit()
    If Not mdlFormOverlay.gOverlay Is Nothing Then
        mdlFormOverlay.gOverlay.EditSelectedRow
    End If
End Sub

Public Sub OverlayRowMenu_Add()
    If Not mdlFormOverlay.gOverlay Is Nothing Then
        mdlFormOverlay.gOverlay.AddRowToActiveTab
    End If
End Sub

Public Sub OverlayRowMenu_Delete()
    If Not mdlFormOverlay.gOverlay Is Nothing Then
        mdlFormOverlay.gOverlay.DeleteSelectedRow
    End If
End Sub
