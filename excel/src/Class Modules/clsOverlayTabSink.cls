VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsOverlayTabSink"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

Private WithEvents mTabs As MSForms.TabStrip
Attribute mTabs.VB_VarHelpID = -1
Private mHost As Object

Public Sub Init(ByVal host As Object, ByVal tabs As MSForms.TabStrip)
    Set mHost = host
    Set mTabs = tabs
End Sub

Private Sub mTabs_Change()
    On Error Resume Next
    CallByName mHost, "OnOverlayTabChanged", VbMethod, CLng(mTabs.Value)
End Sub
