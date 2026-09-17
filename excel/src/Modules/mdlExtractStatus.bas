Attribute VB_Name = "mdlExtractStatus"
Option Explicit

Public gExtractStatus As ufExtractStatus

Public Function EnsureExtractStatusForm(Optional ByVal formCaption As String = "Extract status") As Boolean
    On Error GoTo EH

    If gExtractStatus Is Nothing Then
        Set gExtractStatus = New ufExtractStatus
        gExtractStatus.Init formCaption
        gExtractStatus.Show 0
    Else
        gExtractStatus.Init formCaption
    End If

    EnsureExtractStatusForm = True
    Exit Function

EH:
    EnsureExtractStatusForm = False
End Function

Public Sub UpdateExtractStatus(ByVal pct As Long, ByVal statusText As String)
    On Error Resume Next
    If gExtractStatus Is Nothing Then Exit Sub

    gExtractStatus.UpdateStatus pct, statusText

    On Error GoTo 0
End Sub

Public Sub FinishExtractStatus(Optional ByVal statusText As String = "Done")
    On Error Resume Next
    If gExtractStatus Is Nothing Then Exit Sub

    gExtractStatus.FinishStatus statusText

    On Error GoTo 0
End Sub

Public Sub CloseExtractStatus()
    On Error Resume Next

    If Not gExtractStatus Is Nothing Then
        gExtractStatus.Hide
        Unload gExtractStatus
        Set gExtractStatus = Nothing
    End If

    On Error GoTo 0
End Sub
