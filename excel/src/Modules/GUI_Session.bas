Attribute VB_Name = "GUI_Session"
Option Explicit

Private Function GetSystemPrefix() As String
    GetSystemPrefix = Trim(CStr(Worksheets(WS_SETUP).Cells(SETUP_SYSTEM_ROW, SETUP_SYSTEM_COL).Value))
End Function

Public Sub SAP_AutoLogin_Core()
    Dim SapGuiAuto As Object
    Dim SAPApp As Object
    Dim SapLogonPath As String
    Dim SapSystemName As String
    Dim systemPrefix As String

    On Error GoTo Fail

    SapLogonPath = SAP_LOGON_EXE_PATH
    systemPrefix = GetSystemPrefix()

    If systemPrefix = "GP1" Then
        SapSystemName = SAP_SYSTEM_GP1
    Else
        SapSystemName = SAP_SYSTEM_GQ1
    End If

    Shell SapLogonPath, vbNormalFocus
    Application.Wait (Now + TimeValue(SAP_WAIT_SECONDS))

    On Error Resume Next
    Set SapGuiAuto = GetObject("SAPGUI")
    If SapGuiAuto Is Nothing Then
        MsgBox ValidationMessages.SapGuiNotRunning(), vbCritical
        Exit Sub
    End If
    On Error GoTo 0

    Set SAPApp = SapGuiAuto.GetScriptingEngine
    SAPApp.AllowSystemMessages (False)
    SAPApp.OpenConnection SapSystemName, True
    Application.Wait (Now + TimeValue(SAP_WAIT_SECONDS))
    Exit Sub

Fail:
    MsgBox ValidationMessages.SapAutoLoginFailed(Err.Description), vbCritical
End Sub

Public Function Attach_Session_Core() As Boolean
    Dim il As Long, it As Long
    Dim W_conn As Object, W_Sess As Object
    Dim systemPrefix As String
    Dim systemId As String

    On Error GoTo Fail

    systemPrefix = GetSystemPrefix()
    systemId = systemPrefix & SAP_CLIENT_SUFFIX
    GUI_SCRIPT.W_System = systemId

    If systemId = "" Then
        Attach_Session_Core = False
        Exit Function
    End If

    If Not GUI_SCRIPT.objSess Is Nothing Then
        If GUI_SCRIPT.objSess.Info.SystemName & GUI_SCRIPT.objSess.Info.Client = systemId Then
            Attach_Session_Core = True
            Exit Function
        End If
    End If

    If GUI_SCRIPT.objGui Is Nothing Then
        On Error Resume Next
        Set GUI_SCRIPT.SapGuiAuto = GetObject("SAPGUI")
        If GUI_SCRIPT.SapGuiAuto Is Nothing Then
            SAP_AutoLogin_Core
            Set GUI_SCRIPT.SapGuiAuto = GetObject("SAPGUI")
            If GUI_SCRIPT.SapGuiAuto Is Nothing Then
                Attach_Session_Core = False
                Exit Function
            End If
        End If
        Set GUI_SCRIPT.objGui = GUI_SCRIPT.SapGuiAuto.GetScriptingEngine
        On Error GoTo 0
    End If

    For il = 0 To GUI_SCRIPT.objGui.Children.count - 1
        Set W_conn = GUI_SCRIPT.objGui.Children(il + 0)
        For it = 0 To W_conn.Children.count - 1
            Set W_Sess = W_conn.Children(it + 0)
            If W_Sess.Info.SystemName & W_Sess.Info.Client = systemId Then
                Set GUI_SCRIPT.objConn = GUI_SCRIPT.objGui.Children(il + 0)
                Set GUI_SCRIPT.objSess = GUI_SCRIPT.objConn.Children(it + 0)
                Exit For
            End If
        Next
        If Not GUI_SCRIPT.objSess Is Nothing Then Exit For
    Next

    If GUI_SCRIPT.objSess Is Nothing Then
        MsgBox ValidationMessages.NoActiveSessionToSystem(systemId), vbCritical + vbOKOnly
        Attach_Session_Core = False
        Exit Function
    End If

    If Not GUI_SCRIPT.WScript Is Nothing Then
        GUI_SCRIPT.WScript.ConnectObject GUI_SCRIPT.objSess, "on"
        GUI_SCRIPT.WScript.ConnectObject GUI_SCRIPT.objGui, "on"
    End If

    Set GUI_SCRIPT.objSBar = GUI_SCRIPT.objSess.FindById("wnd[0]/sbar")
    Attach_Session_Core = True
    Exit Function

Fail:
    MsgBox ValidationMessages.AttachSessionFailed(Err.Description), vbCritical + vbOKOnly
    Attach_Session_Core = False
End Function
