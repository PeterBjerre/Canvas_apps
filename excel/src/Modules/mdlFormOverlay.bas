Attribute VB_Name = "mdlFormOverlay"
Option Explicit

Public gOverlay As ufOrderOverlay

Public Sub OpenOverlayForFormSheet(Optional ByVal compareMode As Boolean = False)
    On Error GoTo EH

    ' Ensure stale instance is fully unloaded before building a new runtime UI.
    CloseOverlay

    Dim f As ufOrderOverlay
    Set f = New ufOrderOverlay

    If f.InitFailed Then
        Dim stepName As String
        Dim num As Long
        Dim desc As String
        Dim src As String

        stepName = f.InitErrStep
        num = f.InitErrNumber
        desc = f.InitErrDescription
        src = f.InitErrSource

        On Error Resume Next
        Unload f
        On Error GoTo 0

        MsgBox "Init fejlede i: " & stepName & vbCrLf & _
               "Fejl: " & CStr(num) & " - " & desc & vbCrLf & _
               "Source: " & src, vbExclamation, "Overlay"
        Exit Sub
    End If

    If compareMode Then
        f.EnableCompareMode
    End If

    Set gOverlay = f
    CenterForm gOverlay
    gOverlay.Show 0
    Exit Sub

EH:
    MsgBox "OpenOverlayForFormSheet fejl: " & CStr(Err.Number) & " - " & Err.Description & vbCrLf & _
           "Source: " & Err.Source, vbExclamation, "Overlay"
End Sub

Public Sub OpenOverlayForCompareCockpit()
    OpenOverlayForFormSheet True
End Sub

' Compatibility wrappers for legacy extract-status calls.
' Extract status now runs through its own userform manager (mdlExtractStatus).
Public Function EnsureExtractStatusOverlay(Optional ByVal formCaption As String = "Extract status") As Boolean
    EnsureExtractStatusOverlay = mdlExtractStatus.EnsureExtractStatusForm(formCaption)
End Function

Public Sub UpdateExtractStatusOverlay(ByVal pct As Long, ByVal statusText As String)
    mdlExtractStatus.UpdateExtractStatus pct, statusText
End Sub

Public Sub FinishExtractStatusOverlay(Optional ByVal statusText As String = "Done")
    mdlExtractStatus.FinishExtractStatus statusText
End Sub

Public Sub CloseExtractStatusOverlay()
    mdlExtractStatus.CloseExtractStatus
End Sub

Public Sub CloseOverlay()
    On Error Resume Next
    If Not gOverlay Is Nothing Then
        gOverlay.Hide
        Unload gOverlay
        Set gOverlay = Nothing
    End If
    On Error GoTo 0
End Sub

Public Sub CenterForm(ByVal frm As Object)
    On Error Resume Next
    If frm Is Nothing Then Exit Sub
    frm.StartUpPosition = 0
    frm.Left = Application.Left + (Application.Width - frm.Width) / 2
    frm.Top = Application.Top + (Application.Height - frm.Height) / 2
    On Error GoTo 0
End Sub


