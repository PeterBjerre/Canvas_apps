VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsHoverButton"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

Public WithEvents Btn As MSForms.CommandButton
Attribute Btn.VB_VarHelpID = -1

Private mOwner As Object
Private mNormalBg As Long
Private mHoverBg As Long
Private mNormalFg As Long
Private mHoverFg As Long

Public Sub Init(ByVal owner As Object, ByVal Button As MSForms.CommandButton, ByVal normalBg As Long, ByVal hoverBg As Long, ByVal normalFg As Long, ByVal hoverFg As Long)
    Set mOwner = owner
    Set Btn = Button
    mNormalBg = normalBg
    mHoverBg = hoverBg
    mNormalFg = normalFg
    mHoverFg = hoverFg
    ApplyNormal
End Sub

Public Sub ApplyNormal()
    On Error Resume Next
    If Btn Is Nothing Then Exit Sub
    Btn.BackColor = mNormalBg
    Btn.ForeColor = mNormalFg
    Btn.SpecialEffect = fmSpecialEffectFlat
    On Error GoTo 0
End Sub

Public Sub ApplyHover()
    On Error Resume Next
    If Btn Is Nothing Then Exit Sub
    Btn.BackColor = mHoverBg
    Btn.ForeColor = mHoverFg
    Btn.SpecialEffect = fmSpecialEffectFlat
    On Error GoTo 0
End Sub

Private Sub Btn_MouseMove(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    On Error Resume Next

    If Not mOwner Is Nothing Then
        CallByName mOwner, "Hover_Activate", VbMethod, Btn.name
    End If

    ApplyHover

    On Error GoTo 0
End Sub
