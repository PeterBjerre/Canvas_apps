VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsOverlayNavSink"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

Public WithEvents Btn As MSForms.CommandButton
Attribute Btn.VB_VarHelpID = -1
Private mHost As Object
Private mIndex As Long

Public Sub Init(ByVal host As Object, ByVal Button As MSForms.CommandButton, ByVal index As Long)
    Set mHost = host
    Set Btn = Button
    mIndex = index
End Sub

Private Sub Btn_Click()
    On Error Resume Next
    CallByName mHost, "OnOverlayTabChanged", VbMethod, mIndex
End Sub
