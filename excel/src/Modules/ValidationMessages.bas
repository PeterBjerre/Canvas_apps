Attribute VB_Name = "ValidationMessages"
Option Explicit

Public Function SapGuiNotRunning() As String
    SapGuiNotRunning = "SAP GUI kunne ikke startes eller findes."
End Function

Public Function SapAutoLoginFailed(ByVal details As String) As String
    SapAutoLoginFailed = "SAP auto-login fejlede: " & details
End Function

Public Function NoActiveSessionToSystem(ByVal systemId As String) As String
    NoActiveSessionToSystem = "Ingen aktiv SAP-session fundet for system " & systemId & "."
End Function

Public Function AttachSessionFailed(ByVal details As String) As String
    AttachSessionFailed = "Attach af SAP-session fejlede: " & details
End Function
