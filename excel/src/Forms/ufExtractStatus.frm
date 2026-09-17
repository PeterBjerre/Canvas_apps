VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ufExtractStatus 
   Caption         =   "UserForm1"
   ClientHeight    =   3015
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   4560
   OleObjectBlob   =   "ufExtractStatus.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ufExtractStatus"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Const PAD As Single = 12
Private Const BAR_H As Single = 12
Private Const PCT_W As Single = 58

Private mBuilt As Boolean
Private mCurrentPct As Long
Private mFormCaption As String

Private lblStatus As MSForms.Label
Private lblPct As MSForms.Label
Private lblTrack As MSForms.Label
Private lblBar As MSForms.Label

Public Sub Init(Optional ByVal captionText As String = "Extract status")
    If Len(Trim$(captionText)) > 0 Then
        mFormCaption = captionText
    ElseIf Len(Trim$(mFormCaption)) = 0 Then
        mFormCaption = "Extract status"
    End If

    If mBuilt Then
        Me.Caption = mFormCaption
    End If
End Sub

Public Sub UpdateStatus(ByVal pct As Long, ByVal statusText As String)
    On Error Resume Next

    EnsureUi

    If Len(Trim$(mFormCaption)) = 0 Then mFormCaption = "Extract status"
    Me.Caption = mFormCaption

    mCurrentPct = ClampPct(pct)
    If Len(statusText) = 0 Then statusText = "Working..."

    lblStatus.Caption = statusText
    lblPct.Caption = CStr(mCurrentPct) & "%"

    LayoutProgress
    DoEvents

    On Error GoTo 0
End Sub

Public Sub FinishStatus(Optional ByVal statusText As String = "Done")
    UpdateStatus 100, statusText
End Sub

Private Sub UserForm_Initialize()
    If Len(Trim$(mFormCaption)) = 0 Then mFormCaption = "Extract status"

    Me.Caption = mFormCaption
    Me.StartUpPosition = 0
    Me.BorderStyle = fmBorderStyleSingle
    Me.Width = 780
    Me.Height = 160

    BuildUi
    CenterOnApplication
    UpdateStatus 0, "Starting..."
End Sub

Private Sub UserForm_Resize()
    If Not mBuilt Then Exit Sub
    LayoutProgress
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        Cancel = True
        Me.Hide
    End If
End Sub

Private Sub EnsureUi()
    If Not mBuilt Then BuildUi
End Sub

Private Sub BuildUi()
    If mBuilt Then Exit Sub

    Set lblStatus = EnsureLabel("lblStatus")
    Set lblPct = EnsureLabel("lblPct")
    Set lblTrack = EnsureLabel("lblTrack")
    Set lblBar = EnsureLabel("lblBar")

    lblStatus.Caption = vbNullString
    lblStatus.WordWrap = False
    lblStatus.BackStyle = fmBackStyleTransparent
    lblStatus.Font.Name = "Calibri"
    lblStatus.Font.Size = 10

    lblPct.Caption = vbNullString
    lblPct.BackStyle = fmBackStyleTransparent
    lblPct.TextAlign = fmTextAlignRight
    lblPct.Font.Name = "Calibri"
    lblPct.Font.Size = 10
    lblPct.Font.Bold = True

    lblTrack.Caption = vbNullString
    lblTrack.BackStyle = fmBackStyleOpaque
    lblTrack.BackColor = RGB(220, 220, 220)

    lblBar.Caption = vbNullString
    lblBar.BackStyle = fmBackStyleOpaque
    lblBar.BackColor = RGB(51, 122, 183)

    mBuilt = True
    LayoutProgress
End Sub

Private Sub LayoutProgress()
    Dim iw As Single
    iw = Me.InsideWidth

    lblStatus.Left = PAD
    lblStatus.Top = PAD
    lblStatus.Height = 18
    lblStatus.Width = iw - (PAD * 3) - PCT_W
    If lblStatus.Width < 120 Then lblStatus.Width = 120

    lblPct.Width = PCT_W
    lblPct.Height = 18
    lblPct.Left = iw - PAD - lblPct.Width
    lblPct.Top = lblStatus.Top

    lblTrack.Left = PAD
    lblTrack.Top = lblStatus.Top + lblStatus.Height + 10
    lblTrack.Width = iw - (PAD * 2)
    If lblTrack.Width < 120 Then lblTrack.Width = 120
    lblTrack.Height = BAR_H

    lblBar.Left = lblTrack.Left
    lblBar.Top = lblTrack.Top
    lblBar.Height = lblTrack.Height
    lblBar.Width = lblTrack.Width * (mCurrentPct / 100#)
End Sub

Private Sub CenterOnApplication()
    On Error Resume Next

    Me.Left = Application.Left + (Application.Width - Me.Width) / 2
    Me.Top = Application.Top + (Application.Height - Me.Height) / 2

    On Error GoTo 0
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

Private Function ClampPct(ByVal value As Long) As Long
    If value < 0 Then
        ClampPct = 0
    ElseIf value > 100 Then
        ClampPct = 100
    Else
        ClampPct = value
    End If
End Function
