VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ufOpLongTextPopup 
   Caption         =   "UserForm1"
   ClientHeight    =   3015
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   4560
   OleObjectBlob   =   "ufOpLongTextPopup.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ufOpLongTextPopup"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Const PAD As Single = 12
Private Const BTN_H As Single = 26
Private Const BTN_W As Single = 90
Private Const GAP As Single = 10

Private mTitle As String
Private mBody As String
Private mOwner As Object
Private mBuilt As Boolean

Private lblTitle As MSForms.Label
Private txtBody As MSForms.TextBox
Private cmdClose As MSForms.CommandButton
Private cmdCopy As MSForms.CommandButton

Public Sub Init(Optional ByVal owner As Object, Optional ByVal titleText As String, Optional ByVal bodyText As String)
    Set mOwner = owner
    mTitle = titleText
    mBody = bodyText
End Sub

Public Sub SetContent(Optional ByVal titleText As String, Optional ByVal bodyText As String)
    mTitle = titleText
    mBody = bodyText
    If mBuilt Then ApplyContent
End Sub

Private Sub UserForm_Initialize()
    Me.caption = "Long text"
    Me.StartUpPosition = 0
    Me.BorderStyle = fmBorderStyleSingle
    Me.Width = 860
    Me.Height = 560

    BuildUi
    ApplyTheme
    ApplyContent
    PlaceLayout
    CenterOnOwnerOrScreen
End Sub

Private Sub UserForm_Resize()
    If Not mBuilt Then Exit Sub
    PlaceLayout
End Sub

Private Sub BuildUi()
    If mBuilt Then Exit Sub

    Set lblTitle = EnsureLabel("lblTitle")
    Set txtBody = EnsureTextBox("txtBody")
    Set cmdClose = EnsureButton("cmdClose", "Close")
    Set cmdCopy = EnsureButton("cmdCopy", "Copy")

    With lblTitle
        .caption = vbNullString
        .WordWrap = True
    End With

    With txtBody
        .multiline = True
        .ScrollBars = fmScrollBarsVertical
        .locked = True
        .EnterKeyBehavior = True
        .TabKeyBehavior = True
    End With

    mBuilt = True
End Sub

Private Sub ApplyTheme()
    modOverlayUI.ApplyPalette Me
    modOverlayUI.ApplyFontUniform Me, 10, False
    modOverlayUI.StyleTextBox txtBody, True, True, True
    modOverlayUI.StyleButton cmdClose
    modOverlayUI.StyleButton cmdCopy
    modOverlayUI.FixZOrder Me
End Sub

Private Sub ApplyContent()
    If Not mBuilt Then Exit Sub

    If Len(Trim$(mTitle)) > 0 Then
        lblTitle.caption = mTitle
        Me.caption = mTitle
    Else
        lblTitle.caption = "Long text"
        Me.caption = "Long text"
    End If

    txtBody.text = mBody
    txtBody.SelStart = 0
    txtBody.SelLength = 0
End Sub

Private Sub PlaceLayout()
    Dim iw As Single, ih As Single
    iw = Me.InsideWidth
    ih = Me.InsideHeight

    Dim topY As Single
    topY = PAD

    lblTitle.Left = PAD
    lblTitle.Top = topY
    lblTitle.Width = iw - 2 * PAD
    lblTitle.Height = 28

    txtBody.Left = PAD
    txtBody.Top = lblTitle.Top + lblTitle.Height + 8
    txtBody.Width = iw - 2 * PAD

    Dim btnRowTop As Single
    btnRowTop = ih - PAD - BTN_H
    If btnRowTop < txtBody.Top + 80 Then btnRowTop = txtBody.Top + 80

    txtBody.Height = btnRowTop - txtBody.Top - 10
    If txtBody.Height < 120 Then txtBody.Height = 120

    cmdClose.Width = BTN_W
    cmdClose.Height = BTN_H
    cmdClose.Top = btnRowTop
    cmdClose.Left = iw - PAD - cmdClose.Width

    cmdCopy.Width = BTN_W
    cmdCopy.Height = BTN_H
    cmdCopy.Top = btnRowTop
    cmdCopy.Left = cmdClose.Left - GAP - cmdCopy.Width
End Sub

Private Sub CenterOnOwnerOrScreen()
    On Error Resume Next

    Dim pL As Double, pT As Double, pW As Double, pH As Double
    If Not mOwner Is Nothing Then
        pL = mOwner.Left
        pT = mOwner.Top
        pW = mOwner.Width
        pH = mOwner.Height
    Else
        pL = Application.Left
        pT = Application.Top
        pW = Application.Width
        pH = Application.Height
    End If

    Me.Left = pL + (pW - Me.Width) / 2
    Me.Top = pT + (pH - Me.Height) / 2
End Sub

Private Function EnsureLabel(ByVal nm As String) As MSForms.Label
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then
        Set o = Me.Controls.Add("Forms.Label.1", nm, True)
    End If
    Set EnsureLabel = o
End Function

Private Function EnsureTextBox(ByVal nm As String) As MSForms.TextBox
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then
        Set o = Me.Controls.Add("Forms.TextBox.1", nm, True)
    End If
    Set EnsureTextBox = o
End Function

Private Function EnsureButton(ByVal nm As String, ByVal cap As String) As MSForms.CommandButton
    Dim o As Object
    On Error Resume Next
    Set o = Me.Controls(nm)
    On Error GoTo 0
    If o Is Nothing Then
        Set o = Me.Controls.Add("Forms.CommandButton.1", nm, True)
    End If
    o.caption = cap
    Set EnsureButton = o
End Function

Private Sub cmdClose_Click()
    Me.Hide
End Sub

Private Sub cmdCopy_Click()
    On Error Resume Next
    Dim d As Object
    Set d = CreateObject("MSForms.DataObject")
    d.SetText txtBody.text
    d.PutInClipboard
End Sub

