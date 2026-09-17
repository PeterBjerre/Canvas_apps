Option Explicit

Private Const MENU_NAME As String = "EAM Tasklist Extractor"
Private mToolbar As CommandBar

Public Sub AddMenu()
    On Error Resume Next
    RemoveMenu
    On Error GoTo 0

    Dim cb As CommandBar
    Set cb = Application.CommandBars("Worksheet Menu Bar") ' fallback i �ldre
    Set mToolbar = Application.CommandBars.Add(name:=MENU_NAME, Position:=msoBarTop, Temporary:=True)
    If Not mToolbar Is Nothing Then
        Dim btn As CommandBarButton
        Set btn = mToolbar.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn
            .Caption = "Hent ordredata (Extract Data D4:D)"
            .Style = msoButtonIconAndCaption
            .OnAction = "'" & ThisWorkbook.name & "'!Export_Order_All"
            .FaceId = 734   ' vilk�rligt ikon
        End With

        Dim btnCockpit As CommandBarButton
        Set btnCockpit = mToolbar.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btnCockpit
            .Caption = "Aabn compare cockpit (UserForm)"
            .Style = msoButtonIconAndCaption
            .OnAction = "'" & ThisWorkbook.name & "'!ShowCockpitOverlayUserForm"
            .FaceId = 59
        End With

        Dim btnApply As CommandBarButton
        Set btnApply = mToolbar.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btnApply
            .Caption = "Apply compare decisions"
            .Style = msoButtonIconAndCaption
            .OnAction = "'" & ThisWorkbook.name & "'!ApplyCockpitDecisionsFromMenu"
            .FaceId = 368
        End With

        Dim btnPush As CommandBarButton
        Set btnPush = mToolbar.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btnPush
            .Caption = "Push ready compare decisions"
            .Style = msoButtonIconAndCaption
            .OnAction = "'" & ThisWorkbook.name & "'!PushCockpitDecisions"
            .FaceId = 534
        End With

        Dim btnPreviewPush As CommandBarButton
        Set btnPreviewPush = mToolbar.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btnPreviewPush
            .Caption = "Preview push payload"
            .Style = msoButtonIconAndCaption
            .OnAction = "'" & ThisWorkbook.name & "'!PreviewCockpitPush"
            .FaceId = 552
        End With
        mToolbar.Visible = True
    End If

    ' Alternativt: tilf�j under "Add-Ins" (Ribbon-kompatibel):
    Dim addinsBar As CommandBar
    On Error Resume Next
    Set addinsBar = Application.CommandBars("Add-Ins")
    On Error GoTo 0
    If Not addinsBar Is Nothing Then
        Dim existing As CommandBarControl
        For Each existing In addinsBar.Controls
            If existing.Caption = MENU_NAME Then existing.Delete
        Next
        Dim pop As CommandBarPopup
        Set pop = addinsBar.Controls.Add(Type:=msoControlPopup, Temporary:=True)
        pop.Caption = MENU_NAME

        Dim btn2 As CommandBarButton
        Set btn2 = pop.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn2
            .Caption = "Hent ordredata (Extract Data D4:D)"
            .OnAction = "'" & ThisWorkbook.name & "'!Export_Order_All"
            .FaceId = 734
        End With

        Dim btn3 As CommandBarButton
        Set btn3 = pop.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn3
            .Caption = "Aabn compare cockpit (UserForm)"
            .OnAction = "'" & ThisWorkbook.name & "'!ShowCockpitOverlayUserForm"
            .FaceId = 59
        End With

        Dim btn4 As CommandBarButton
        Set btn4 = pop.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn4
            .Caption = "Apply compare decisions"
            .OnAction = "'" & ThisWorkbook.name & "'!ApplyCockpitDecisionsFromMenu"
            .FaceId = 368
        End With

        Dim btn5 As CommandBarButton
        Set btn5 = pop.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn5
            .Caption = "Push ready compare decisions"
            .OnAction = "'" & ThisWorkbook.name & "'!PushCockpitDecisions"
            .FaceId = 534
        End With

        Dim btn6 As CommandBarButton
        Set btn6 = pop.Controls.Add(Type:=msoControlButton, Temporary:=True)
        With btn6
            .Caption = "Preview push payload"
            .OnAction = "'" & ThisWorkbook.name & "'!PreviewCockpitPush"
            .FaceId = 552
        End With
    End If
End Sub

Public Sub ShowCockpitOverlayUserForm()
    On Error GoTo EH

    mdlFormOverlay.OpenOverlayForCompareCockpit
    Exit Sub

EH:
    MsgBox "Kunne ikke aabne compare cockpit: " & Err.Description, vbExclamation, APP_TITLE
End Sub

Public Sub ApplyCockpitDecisionsFromMenu()
    On Error GoTo EH

    modCockpit.ApplyCockpitDecisions
    Exit Sub

EH:
    MsgBox "Kunne ikke apply decisions: " & Err.Description, vbExclamation, APP_TITLE
End Sub

Public Sub PushCockpitDecisions()
    On Error GoTo EH

    modCockpit.PushReadyDecisionsToPowerAutomate
    Exit Sub

EH:
    MsgBox "Kunne ikke pushe decisions: " & Err.Description, vbExclamation, APP_TITLE
End Sub

Public Sub PreviewCockpitPush()
    On Error GoTo EH

    modCockpit.PreviewPushReadyDecisions
    Exit Sub

EH:
    MsgBox "Kunne ikke lave push preview: " & Err.Description, vbExclamation, APP_TITLE
End Sub

Public Sub RemoveMenu()
    On Error Resume Next
    If Not mToolbar Is Nothing Then mToolbar.Delete
    Dim addinsBar As CommandBar: Set addinsBar = Application.CommandBars("Add-Ins")
    If Not addinsBar Is Nothing Then
        Dim ctl As CommandBarControl
        For Each ctl In addinsBar.Controls
            If ctl.Caption = MENU_NAME Then ctl.Delete
        Next
    End If
    On Error GoTo 0
End Sub
