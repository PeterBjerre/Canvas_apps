VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ufOrderOverlay 
   Caption         =   "UserForm1"
   ClientHeight    =   3015
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   4560
   OleObjectBlob   =   "ufOrderOverlay.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ufOrderOverlay"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Const POPUP_NAME As String = "OverlayRowMenu"

Private Const SH_HDR As String = "WorkOrderHeader"
Private Const SH_OPS As String = "WorkOrderOperations"
Private Const SH_OPLT As String = "WorkOrderOperationLongText"
Private Const SH_OBJ As String = "WorkOrderObjects"
Private Const SH_ATTACH As String = "Attachment"
Private Const SH_STATUS As String = "WorkOrderStatus"

Private Const F_AUFNR As String = "Aufnr"
Private Const F_OBJNR As String = "Objnr"
Private Const F_LONGTEXT As String = "Longtext"
Private Const F_PRI As String = "Priok"
Private Const F_VAPLZ As String = "Vaplz"
Private Const F_PERSINIT As String = "PersonResponsibleInitials"
Private Const F_GSTRP As String = "GstrpUtc"
Private Const F_GLTRP As String = "GltrpUtc"
Private Const F_TPLNR As String = "Tplnr"
Private Const F_EQUNR As String = "Equnr"
Private Const F_AUART As String = "Auart"
Private Const F_SWERK As String = "Swerk"

Private Const TAGMAP_PAIR_SEP As String = ";"
Private Const TAGMAP_KV_SEP As String = vbTab
Private Const HDR_COMPARE_TOP As String = "A350"
Private Const HDR_COMPARE_GRID_TOP As Single = 174
Private Const HDR_COMPARE_ROW_H As Single = 20
Private Const HDR_COMPARE_MAX_ROWS As Long = 8
Private Const LT_LINE_H As Single = 18
Private Const LT_MAX_LINES As Long = 250
Private Const LT_ORDER_TOP As String = "A230"
Private Const LT_ITEM_TOP As String = "A260"
Private Const HDR_OBJ_ORDER_TOP As String = "A290"
Private Const HDR_OBJ_ITEM_TOP As String = "A320"
Private Const COMP_TOP As String = "A30"
Private Const DEC_TOP As String = "A120"
Private Const CMP_KEY_OP As String = "OP"
Private Const CMP_KEY_COMP As String = "COMP"
Private Const CMP_KEY_ATT As String = "ATT"
Private Const CMP_TAB_ROW_H As Single = 20

Private Const LT_GLYPH As String = "�"

Private Const MIN_FRAME_H As Single = 260
Private Const PAD As Single = 8
Private Const GAP As Single = 10
Private Const BOTTOM_PAD As Single = 10

Private mInitFailed As Boolean
Private mInitErrStep As String
Private mInitErrNumber As Long
Private mInitErrDescription As String
Private mInitErrSource As String

Private mOrder As String
Private mPrevCalc As XlCalculation
Private mLongTextEdit As Boolean
Private mHeaderEdit As Boolean
Private mActiveIdx As Long
Private mPopupReady As Boolean
Private mCompareMode As Boolean
Private mHasDecisionDiffs As Boolean
Private mHasLongTextDiffs As Boolean
Private mIsLoading As Boolean
Private mIsRendering As Boolean

Private mUI As Object
Private mNavSinks As Collection

Private mOpLongTextMap As Object
Private mMeasureLbl As MSForms.Label
Private mLtOrderLines As Collection
Private mLtItemLines As Collection
Private mCmpFieldRows As Object
Private mCmpOrderRows As Object
Private mCmpItemRows As Object
Private mCmpRowCounts As Object

Private WithEvents txtOrder As MSForms.TextBox
Attribute txtOrder.VB_VarHelpID = -1
Private WithEvents cmdLoad As MSForms.CommandButton
Attribute cmdLoad.VB_VarHelpID = -1
Private WithEvents cmdClear As MSForms.CommandButton
Attribute cmdClear.VB_VarHelpID = -1
Private WithEvents cmdClose As MSForms.CommandButton
Attribute cmdClose.VB_VarHelpID = -1
Private WithEvents cmdEditHeader As MSForms.CommandButton
Attribute cmdEditHeader.VB_VarHelpID = -1
Private WithEvents cmdEditLongText As MSForms.CommandButton
Attribute cmdEditLongText.VB_VarHelpID = -1
Private WithEvents cmdEditRow As MSForms.CommandButton
Attribute cmdEditRow.VB_VarHelpID = -1
Private WithEvents cmdAddRow As MSForms.CommandButton
Attribute cmdAddRow.VB_VarHelpID = -1
Private WithEvents cmdDeleteRow As MSForms.CommandButton
Attribute cmdDeleteRow.VB_VarHelpID = -1

Private WithEvents lstOperations As MSForms.ListBox
Attribute lstOperations.VB_VarHelpID = -1
Private WithEvents lstPermits As MSForms.ListBox
Attribute lstPermits.VB_VarHelpID = -1
Private WithEvents lstObjects As MSForms.ListBox
Attribute lstObjects.VB_VarHelpID = -1
Private WithEvents lstAttachments As MSForms.ListBox
Attribute lstAttachments.VB_VarHelpID = -1
Private WithEvents lstPlanning As MSForms.ListBox
Attribute lstPlanning.VB_VarHelpID = -1

Private btnTab0 As MSForms.CommandButton
Private btnTab1 As MSForms.CommandButton
Private btnTab2 As MSForms.CommandButton
Private btnTab3 As MSForms.CommandButton
Private btnTab4 As MSForms.CommandButton
Private btnTab5 As MSForms.CommandButton

Private cmbPriority As MSForms.ComboBox
Private cmbPlannerGrp As MSForms.ComboBox

Private txtMainWorkCtr As MSForms.TextBox
Private txtPersonResp As MSForms.TextBox
Private txtBasicStart As MSForms.TextBox
Private txtBasicFin As MSForms.TextBox
Private txtFuncLoc As MSForms.TextBox
Private txtEquipment As MSForms.TextBox
Private txtRevision As MSForms.TextBox
Private txtNotifNo As MSForms.TextBox

Private txtLongText As MSForms.TextBox
Private lblStatusShort As MSForms.Label
Private lstHeaderCompare As MSForms.ListBox
Private txtCmpOrderLongText As MSForms.TextBox
Private txtCmpItemLongText As MSForms.TextBox
Private lstObjOrder As MSForms.ListBox
Private lstObjOrderEq As MSForms.ListBox
Private lstObjItem As MSForms.ListBox
Private lstObjItemEq As MSForms.ListBox
Private fraLongTextOrder As MSForms.Frame
Private fraLongTextItem As MSForms.Frame
Private lblLongTextOrder As MSForms.Label
Private lblLongTextItem As MSForms.Label

Private fraProg As MSForms.Frame
Private lblProgText As MSForms.Label
Private lblProgTrack As MSForms.Label
Private lblProgBar As MSForms.Label
Private lblProgPct As MSForms.Label

Private txtOrderType As MSForms.TextBox
Private txtMaintPlant As MSForms.TextBox

Public Property Get InitFailed() As Boolean: InitFailed = mInitFailed: End Property
Public Property Get InitErrStep() As String: InitErrStep = mInitErrStep: End Property
Public Property Get InitErrNumber() As Long: InitErrNumber = mInitErrNumber: End Property
Public Property Get InitErrDescription() As String: InitErrDescription = mInitErrDescription: End Property
Public Property Get InitErrSource() As String: InitErrSource = mInitErrSource: End Property

Public Sub EnableCompareMode()
    On Error GoTo EH

    mCompareMode = True

    txtOrder.ControlTipText = "Order_number from compare queue"
    cmdLoad.caption = "Refresh"

    If Not cmdEditHeader Is Nothing Then cmdEditHeader.Visible = False
    If Not cmdEditLongText Is Nothing Then cmdEditLongText.Visible = False
    ToggleHeaderCompareView True

    If Not btnTab0 Is Nothing Then btnTab0.Enabled = True
    If Not btnTab1 Is Nothing Then btnTab1.Enabled = True
    If Not btnTab2 Is Nothing Then btnTab2.Enabled = True
    If Not btnTab3 Is Nothing Then btnTab3.Enabled = True
    If Not btnTab4 Is Nothing Then btnTab4.Enabled = True

    If Len(Trim$(txtOrder.text)) = 0 Then
        txtOrder.text = FirstOrderFromCompareQueue()
    End If

    If Len(Trim$(txtOrder.text)) > 0 Then
        mOrder = CleanKey(txtOrder.text)

        mIsLoading = True
        SafeLoad True
        SetProgress 5, "Loading compare..."
        LoadAllData mOrder
        SetProgress 100, "Done"
        DoEvents
        HideProgress
        SafeLoad False
        mIsLoading = False

        RefreshCompareDecisionState
    Else
        lblStatusShort.caption = "Compare mode: ingen data"
        BindEmptyAll
        HideProgress
    End If

    OnOverlayTabChanged 0
    Exit Sub

EH:
    mIsLoading = False
    SafeLoad False
    HideProgress
    lblStatusShort.caption = "Compare mode fejl: " & Err.Description
End Sub

Private Sub UserForm_Initialize()
    On Error GoTo EH

    Dim initStep As String
    initStep = "start"

    mInitFailed = False
    mInitErrStep = vbNullString
    mInitErrNumber = 0
    mInitErrDescription = vbNullString
    mInitErrSource = vbNullString

    mPopupReady = False
    mActiveIdx = 0

    initStep = "BuildOverlayUI"
    Set mUI = modOverlayUiBuild.BuildOverlayUI(Me)

    initStep = "LayoutOverlay"
    modOverlayUiLayout.LayoutOverlay Me, mUI

    initStep = "BindControlRefs"
    BindControlRefs
    initStep = "EnsureStatusShortUI"
    EnsureStatusShortUI
    initStep = "EnsureProgressUI"
    EnsureProgressUI
    initStep = "EnsureHeaderPlainTextFieldsUI"
    EnsureHeaderPlainTextFieldsUI
    initStep = "EnsureHeaderCompareVisualUI"
    EnsureHeaderCompareVisualUI
    initStep = "EnsureLongTextLineUi"
    EnsureLongTextLineUi
    initStep = "ToggleHeaderCompareView"
    ToggleHeaderCompareView True
    If Not cmdEditHeader Is Nothing Then cmdEditHeader.Visible = False

    initStep = "HookNavSinks"
    HookNavSinks
    initStep = "EnsureOverlaySheet"
    mdlOverlayView.EnsureOverlaySheet

    initStep = "BindEmptyAll"
    BindEmptyAll
    initStep = "LayoutBottomArea"
    LayoutBottomArea
    initStep = "OnOverlayTabChanged"
    OnOverlayTabChanged 0

    Exit Sub

EH:
    mInitFailed = True
    mInitErrStep = "UserForm_Initialize > " & initStep
    mInitErrNumber = Err.Number
    mInitErrDescription = Err.Description
    mInitErrSource = Err.Source
End Sub

Private Sub UserForm_Terminate()
    On Error Resume Next
    Application.CommandBars(POPUP_NAME).Delete
    On Error GoTo 0
End Sub

Private Sub UserForm_Resize()
    On Error Resume Next
    LayoutBottomArea
    On Error GoTo 0
End Sub

Private Sub BindControlRefs()
    Set txtOrder = mUI("txtOrder")
    Set cmdLoad = mUI("cmdLoad")
    Set cmdClear = mUI("cmdClear")
    Set cmdClose = mUI("cmdClose")
    Set txtLongText = mUI("txtLongText")
    Set cmdEditLongText = mUI("cmdEditLongText")
    Set btnTab0 = mUI("btnTab0")
    Set btnTab1 = mUI("btnTab1")
    Set btnTab2 = mUI("btnTab2")
    Set btnTab3 = mUI("btnTab3")
    Set btnTab4 = mUI("btnTab4")
    Set btnTab5 = mUI("btnTab5")
    Set cmdEditRow = mUI("cmdEditRow")
    Set cmdAddRow = mUI("cmdAddRow")
    Set cmdDeleteRow = mUI("cmdDeleteRow")
    Set cmdEditHeader = mUI("cmdEditHeader")
    Set lstOperations = mUI("lstOperations")
    Set lstPermits = mUI("lstPermits")
    Set lstObjects = mUI("lstObjects")
    Set lstAttachments = mUI("lstAttachments")
    Set lstPlanning = mUI("lstPlanning")
    Set cmbPriority = mUI("cmbPriority")
    Set cmbPlannerGrp = mUI("cmbPlannerGrp")
    Set txtMainWorkCtr = mUI("txtMainWorkCtr")
    Set txtPersonResp = mUI("txtPersonResp")
    Set txtBasicStart = mUI("txtBasicStart")
    Set txtBasicFin = mUI("txtBasicFin")
    Set txtFuncLoc = mUI("txtFuncLoc")
    Set txtEquipment = mUI("txtEquipment")
    Set txtRevision = mUI("txtRevision")
    Set txtNotifNo = mUI("txtNotifNo")
    Set lstHeaderCompare = Nothing
    Set lstObjOrder = Nothing
    Set lstObjOrderEq = Nothing
    Set lstObjItem = Nothing
    Set lstObjItemEq = Nothing
    Set fraLongTextOrder = Nothing
    Set fraLongTextItem = Nothing
    Set lblLongTextOrder = Nothing
    Set lblLongTextItem = Nothing
    On Error Resume Next
    Set lstHeaderCompare = mUI("lstHeaderCompare")
    Set lstObjOrder = mUI("lstObjOrder")
    Set lstObjOrderEq = mUI("lstObjOrderEq")
    Set lstObjItem = mUI("lstObjItem")
    Set lstObjItemEq = mUI("lstObjItemEq")
    Set fraLongTextOrder = mUI("fraLongTextOrder")
    Set fraLongTextItem = mUI("fraLongTextItem")
    Set lblLongTextOrder = mUI("frames")("LongText").Controls("lblLongTextOrder")
    Set lblLongTextItem = mUI("frames")("LongText").Controls("lblLongTextItem")
    Set txtCmpOrderLongText = mUI("frames")("HeaderData").Controls("txtCmpOrderLongText")
    Set txtCmpItemLongText = mUI("frames")("HeaderData").Controls("txtCmpItemLongText")
    On Error GoTo 0
End Sub

Private Sub EnsureStatusShortUI()
    On Error Resume Next
    Dim o As Object
    Set o = Me.Controls("lblStatusShort")
    If o Is Nothing Then
        Set o = Me.Controls.Add("Forms.Label.1", "lblStatusShort", True)
    End If
    o.Left = 300
    o.Top = 42
    o.Width = 670
    o.Height = 18
    o.caption = vbNullString
    o.BackStyle = fmBackStyleTransparent
    o.ForeColor = modOverlayUI.UI_LABEL
    o.Font.name = modOverlayUI.UI_FONT_NAME
    o.Font.Size = 10
    o.Font.Bold = True
    Set lblStatusShort = o
    On Error GoTo 0
End Sub

Private Sub EnsureProgressUI()
    On Error Resume Next

    Set fraProg = Nothing
    Set fraProg = Me.Controls("fraProg")
    If fraProg Is Nothing Then
        Set fraProg = Me.Controls.Add("Forms.Frame.1", "fraProg", True)
    End If

    fraProg.caption = vbNullString
    fraProg.SpecialEffect = fmSpecialEffectFlat
    fraProg.BackColor = modOverlayUI.UI_BG
    fraProg.Visible = False

    Set lblProgText = Nothing
    Set lblProgText = fraProg.Controls("lblProgText")
    If lblProgText Is Nothing Then
        Set lblProgText = fraProg.Controls.Add("Forms.Label.1", "lblProgText", True)
    End If
    lblProgText.Left = 6
    lblProgText.Top = 5
    lblProgText.Width = 260
    lblProgText.Height = 16
    lblProgText.caption = vbNullString
    lblProgText.BackStyle = fmBackStyleTransparent
    lblProgText.ForeColor = modOverlayUI.UI_LABEL
    lblProgText.Font.name = modOverlayUI.UI_FONT_NAME
    lblProgText.Font.Size = 9
    lblProgText.Font.Bold = False
    lblProgText.AutoSize = False
    lblProgText.WordWrap = False

    Set lblProgPct = Nothing
    Set lblProgPct = fraProg.Controls("lblProgPct")
    If lblProgPct Is Nothing Then
        Set lblProgPct = fraProg.Controls.Add("Forms.Label.1", "lblProgPct", True)
    End If
    lblProgPct.Top = 5
    lblProgPct.Width = 44
    lblProgPct.Height = 16
    lblProgPct.Left = fraProg.Width - 48
    lblProgPct.caption = vbNullString
    lblProgPct.BackStyle = fmBackStyleTransparent
    lblProgPct.ForeColor = modOverlayUI.UI_LABEL
    lblProgPct.Font.name = modOverlayUI.UI_FONT_NAME
    lblProgPct.Font.Size = 9
    lblProgPct.Font.Bold = False

    Set lblProgTrack = Nothing
    Set lblProgTrack = fraProg.Controls("lblProgTrack")
    If lblProgTrack Is Nothing Then
        Set lblProgTrack = fraProg.Controls.Add("Forms.Label.1", "lblProgTrack", True)
    End If
    lblProgTrack.Top = 9
    lblProgTrack.Height = 8
    lblProgTrack.caption = vbNullString
    lblProgTrack.BackStyle = fmBackStyleOpaque
    lblProgTrack.BackColor = modOverlayUI.UI_TRACK_BG

    Set lblProgBar = Nothing
    Set lblProgBar = fraProg.Controls("lblProgBar")
    If lblProgBar Is Nothing Then
        Set lblProgBar = fraProg.Controls.Add("Forms.Label.1", "lblProgBar", True)
    End If
    lblProgBar.Top = lblProgTrack.Top
    lblProgBar.Height = lblProgTrack.Height
    lblProgBar.Width = 0
    lblProgBar.caption = vbNullString
    lblProgBar.BackStyle = fmBackStyleOpaque
    lblProgBar.BackColor = modOverlayUI.UI_BAR_BG

    Dim textRight As Single
    textRight = lblProgText.Left + lblProgText.Width

    lblProgPct.Left = fraProg.Width - 48

    lblProgTrack.Left = textRight + 10
    lblProgTrack.Width = lblProgPct.Left - 10 - lblProgTrack.Left
    If lblProgTrack.Width < 40 Then lblProgTrack.Width = 40

    lblProgBar.Left = lblProgTrack.Left
    lblProgBar.Width = 0

    On Error GoTo 0
End Sub
Private Sub SetProgress(ByVal pct As Long, ByVal text As String)
    On Error Resume Next

    If pct < 0 Then pct = 0
    If pct > 100 Then pct = 100
    If fraProg Is Nothing Then Exit Sub

    fraProg.Visible = True

    lblProgText.WordWrap = False
    lblProgText.caption = text

    lblProgText.AutoSize = True
    Dim wantW As Single
    wantW = lblProgText.Width
    lblProgText.AutoSize = False

    lblProgPct.caption = CStr(pct) & "%"
    lblProgPct.Left = fraProg.Width - 48

    Dim maxTextW As Single
    maxTextW = (lblProgPct.Left - 10) - lblProgText.Left - 10
    If maxTextW < 60 Then maxTextW = 60

    If wantW > maxTextW Then
        lblProgText.Width = maxTextW
    ElseIf wantW < 40 Then
        lblProgText.Width = 40
    Else
        lblProgText.Width = wantW
    End If

    Dim textRight As Single
    textRight = lblProgText.Left + lblProgText.Width

    lblProgTrack.Left = textRight + 10
    lblProgTrack.Width = lblProgPct.Left - 10 - lblProgTrack.Left
    If lblProgTrack.Width < 40 Then lblProgTrack.Width = 40

    lblProgBar.Left = lblProgTrack.Left
    lblProgBar.Top = lblProgTrack.Top
    lblProgBar.Height = lblProgTrack.Height
    lblProgBar.Width = lblProgTrack.Width * (pct / 100#)

    DoEvents

    On Error GoTo 0
End Sub

Private Sub HideProgress()
    On Error Resume Next
    If fraProg Is Nothing Then Exit Sub
    fraProg.Visible = False
    lblProgText.caption = vbNullString
    lblProgPct.caption = vbNullString
    lblProgBar.Width = 0
    On Error GoTo 0
End Sub

Private Sub EnsureHeaderPlainTextFieldsUI()
    On Error Resume Next

    Dim frames As Object
    Set frames = mUI("frames")
    Dim host As Object
    Set host = frames("HeaderData")
    If host Is Nothing Then Exit Sub

    Dim cbPri As Object, cbPlan As Object
    Set cbPri = host.Controls("cmbPriority")
    Set cbPlan = host.Controls("cmbPlannerGrp")

    Dim tbPri As Object, tbPlan As Object
    Set tbPri = host.Controls("txtPriorityText")
    If tbPri Is Nothing And Not cbPri Is Nothing Then
        Set tbPri = host.Controls.Add("Forms.TextBox.1", "txtPriorityText", True)
        tbPri.Left = cbPri.Left
        tbPri.Top = cbPri.Top
        tbPri.Width = cbPri.Width
        tbPri.Height = cbPri.Height
        tbPri.locked = True
        modOverlayUI.StyleTextBox tbPri, False, False, True
        cbPri.Visible = False
    End If

    Set tbPlan = host.Controls("txtPlannerGrpText")
    If tbPlan Is Nothing And Not cbPlan Is Nothing Then
        Set tbPlan = host.Controls.Add("Forms.TextBox.1", "txtPlannerGrpText", True)
        tbPlan.Left = cbPlan.Left
        tbPlan.Top = cbPlan.Top
        tbPlan.Width = cbPlan.Width
        tbPlan.Height = cbPlan.Height
        tbPlan.locked = True
        modOverlayUI.StyleTextBox tbPlan, False, False, True
        cbPlan.Visible = False
    End If

    On Error GoTo 0
End Sub

Private Sub EnsureHeaderCompareVisualUI()
    On Error Resume Next

    Dim host As Object
    Set host = mUI("frames")("HeaderData")
    If host Is Nothing Then Exit Sub

    Dim lbl As Object
    Dim tb As Object
    Dim i As Long

    Set lbl = EnsureHeaderLabel(host, "lblCmpHdrField", "Field")
    lbl.Font.Bold = True
    Set lbl = EnsureHeaderLabel(host, "lblCmpHdrOrder", "Order")
    lbl.Font.Bold = True
    Set lbl = EnsureHeaderLabel(host, "lblCmpHdrItem", "Item")
    lbl.Font.Bold = True

    For i = 1 To HDR_COMPARE_MAX_ROWS
        Set lbl = EnsureHeaderLabel(host, "lblCmpField" & CStr(i), vbNullString)
        lbl.Visible = False

        Set tb = EnsureHeaderTextBox(host, "txtCmpOrder" & CStr(i), False)
        tb.Visible = False

        Set tb = EnsureHeaderTextBox(host, "txtCmpItem" & CStr(i), False)
        tb.Visible = False
    Next i

    Set lbl = EnsureHeaderLabel(host, "lblCmpOrderLong", "Order Long Text")
    lbl.Font.Bold = False
    Set lbl = EnsureHeaderLabel(host, "lblCmpItemLong", "Item Long Text")
    lbl.Font.Bold = False

    Set txtCmpOrderLongText = EnsureHeaderTextBox(host, "txtCmpOrderLongText", True)
    Set txtCmpItemLongText = EnsureHeaderTextBox(host, "txtCmpItemLongText", True)

    Set lbl = EnsureHeaderLabel(host, "lblObjOrderCol1", "Functional loc.")
    lbl.Font.Bold = True
    lbl.Visible = False
    Set lbl = EnsureHeaderLabel(host, "lblObjOrderCol2", "Equipment")
    lbl.Font.Bold = True
    lbl.Visible = False
    Set lbl = EnsureHeaderLabel(host, "lblObjItemCol1", "Functional loc.")
    lbl.Font.Bold = True
    lbl.Visible = False
    Set lbl = EnsureHeaderLabel(host, "lblObjItemCol2", "Equipment")
    lbl.Font.Bold = True
    lbl.Visible = False

    txtCmpOrderLongText.EnterKeyBehavior = True
    txtCmpOrderLongText.WordWrap = True
    txtCmpOrderLongText.ScrollBars = fmScrollBarsVertical

    txtCmpItemLongText.EnterKeyBehavior = True
    txtCmpItemLongText.WordWrap = True
    txtCmpItemLongText.ScrollBars = fmScrollBarsVertical

    txtCmpOrderLongText.Visible = False
    txtCmpItemLongText.Visible = False

    On Error GoTo 0
End Sub

Private Function EnsureHeaderLabel(ByVal host As Object, ByVal controlName As String, ByVal captionText As String) As Object
    Dim lbl As Object

    Set lbl = Nothing
    On Error Resume Next
    Set lbl = host.Controls(controlName)
    On Error GoTo 0

    If lbl Is Nothing Then
        Set lbl = host.Controls.Add("Forms.Label.1", controlName, True)
    End If

    lbl.caption = captionText
    lbl.BackStyle = fmBackStyleTransparent
    lbl.ForeColor = modOverlayUI.UI_LABEL
    lbl.Font.name = modOverlayUI.UI_FONT_NAME
    lbl.Font.Size = 10

    Set EnsureHeaderLabel = lbl
End Function

Private Function EnsureHeaderTextBox(ByVal host As Object, ByVal controlName As String, ByVal multiline As Boolean) As Object
    Dim tb As Object

    Set tb = Nothing
    On Error Resume Next
    Set tb = host.Controls(controlName)
    On Error GoTo 0

    If tb Is Nothing Then
        Set tb = host.Controls.Add("Forms.TextBox.1", controlName, True)
    End If

    modOverlayUI.StyleTextBox tb, multiline, multiline, True
    tb.locked = True

    Set EnsureHeaderTextBox = tb
End Function

Private Sub EnsureCompareTripletCaches()
    If mCmpFieldRows Is Nothing Then
        Set mCmpFieldRows = CreateObject("Scripting.Dictionary")
        mCmpFieldRows.CompareMode = vbTextCompare
    End If

    If mCmpOrderRows Is Nothing Then
        Set mCmpOrderRows = CreateObject("Scripting.Dictionary")
        mCmpOrderRows.CompareMode = vbTextCompare
    End If

    If mCmpItemRows Is Nothing Then
        Set mCmpItemRows = CreateObject("Scripting.Dictionary")
        mCmpItemRows.CompareMode = vbTextCompare
    End If

    If mCmpRowCounts Is Nothing Then
        Set mCmpRowCounts = CreateObject("Scripting.Dictionary")
        mCmpRowCounts.CompareMode = vbTextCompare
    End If
End Sub

Private Function CompareRowsCollection(ByVal store As Object, ByVal tabKey As String) As Collection
    Dim rows As Collection

    If store Is Nothing Then Exit Function

    If Not store.Exists(tabKey) Then
        Set rows = New Collection
        store.Add tabKey, rows
    End If

    Set CompareRowsCollection = store(tabKey)
End Function

Private Function CompareFieldRows(ByVal tabKey As String) As Collection
    EnsureCompareTripletCaches
    Set CompareFieldRows = CompareRowsCollection(mCmpFieldRows, tabKey)
End Function

Private Function CompareOrderRows(ByVal tabKey As String) As Collection
    EnsureCompareTripletCaches
    Set CompareOrderRows = CompareRowsCollection(mCmpOrderRows, tabKey)
End Function

Private Function CompareItemRows(ByVal tabKey As String) As Collection
    EnsureCompareTripletCaches
    Set CompareItemRows = CompareRowsCollection(mCmpItemRows, tabKey)
End Function

Private Sub SetCompareRowCount(ByVal tabKey As String, ByVal rowCount As Long)
    EnsureCompareTripletCaches
    mCmpRowCounts(tabKey) = CLng(rowCount)
End Sub

Private Function GetCompareRowCount(ByVal tabKey As String) As Long
    EnsureCompareTripletCaches
    If mCmpRowCounts.Exists(tabKey) Then GetCompareRowCount = CLng(mCmpRowCounts(tabKey))
End Function

Private Function CompareFrameByKey(ByVal tabKey As String) As Object
    Dim frames As Object

    On Error Resume Next
    Set frames = mUI("frames")
    On Error GoTo 0
    If frames Is Nothing Then Exit Function

    Select Case UCase$(tabKey)
        Case CMP_KEY_OP: Set CompareFrameByKey = frames("Operations")
        Case CMP_KEY_COMP: Set CompareFrameByKey = frames("Components")
        Case CMP_KEY_ATT: Set CompareFrameByKey = frames("Attachments")
    End Select
End Function

Private Function CompareListByKey(ByVal tabKey As String) As MSForms.ListBox
    Select Case UCase$(tabKey)
        Case CMP_KEY_OP: Set CompareListByKey = lstOperations
        Case CMP_KEY_COMP: Set CompareListByKey = lstObjects
        Case CMP_KEY_ATT: Set CompareListByKey = lstAttachments
    End Select
End Function

Private Function CompareFieldHeaderName(ByVal tabKey As String) As String
    CompareFieldHeaderName = "lblCmp" & UCase$(tabKey) & "HdrField"
End Function

Private Function CompareOrderHeaderName(ByVal tabKey As String) As String
    CompareOrderHeaderName = "lblCmp" & UCase$(tabKey) & "HdrOrder"
End Function

Private Function CompareItemHeaderName(ByVal tabKey As String) As String
    CompareItemHeaderName = "lblCmp" & UCase$(tabKey) & "HdrItem"
End Function

Private Function CompareOrderCaptionName(ByVal tabKey As String) As String
    CompareOrderCaptionName = "lblCmp" & UCase$(tabKey) & "CapOrder"
End Function

Private Function CompareItemCaptionName(ByVal tabKey As String) As String
    CompareItemCaptionName = "lblCmp" & UCase$(tabKey) & "CapItem"
End Function

Private Function CompareFieldRowName(ByVal tabKey As String, ByVal idx As Long) As String
    CompareFieldRowName = "lblCmp" & UCase$(tabKey) & "Field" & CStr(idx)
End Function

Private Function CompareOrderRowName(ByVal tabKey As String, ByVal idx As Long) As String
    CompareOrderRowName = "txtCmp" & UCase$(tabKey) & "Order" & CStr(idx)
End Function

Private Function CompareItemRowName(ByVal tabKey As String, ByVal idx As Long) As String
    CompareItemRowName = "txtCmp" & UCase$(tabKey) & "Item" & CStr(idx)
End Function

Private Sub EnsureCompareTripletTabUI(ByVal tabKey As String)
    Dim host As Object
    Dim lbl As Object

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    Set lbl = EnsureHeaderLabel(host, CompareFieldHeaderName(tabKey), "Field")
    lbl.Font.Bold = True
    Set lbl = EnsureHeaderLabel(host, CompareOrderHeaderName(tabKey), "Order")
    lbl.Font.Bold = True
    Set lbl = EnsureHeaderLabel(host, CompareItemHeaderName(tabKey), "Item")
    lbl.Font.Bold = True

    Set lbl = EnsureHeaderLabel(host, CompareOrderCaptionName(tabKey), "Order")
    lbl.Font.Bold = False
    Set lbl = EnsureHeaderLabel(host, CompareItemCaptionName(tabKey), "Item")
    lbl.Font.Bold = False

    ToggleCompareTripletTabView tabKey, False

    On Error Resume Next
    host.ScrollBars = fmScrollBarsVertical
    On Error GoTo 0
End Sub

Private Sub EnsureCompareTripletRowControls(ByVal tabKey As String, ByVal rowCount As Long)
    Dim host As Object
    Dim fieldRows As Collection
    Dim orderRows As Collection
    Dim itemRows As Collection
    Dim idx As Long
    Dim lbl As Object
    Dim tb As Object

    If rowCount < 1 Then Exit Sub

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    Set fieldRows = CompareFieldRows(tabKey)
    Set orderRows = CompareOrderRows(tabKey)
    Set itemRows = CompareItemRows(tabKey)

    Do While fieldRows.Count < rowCount
        idx = fieldRows.Count + 1

        Set lbl = EnsureHeaderLabel(host, CompareFieldRowName(tabKey, idx), vbNullString)
        lbl.Visible = False

        Set tb = EnsureHeaderTextBox(host, CompareOrderRowName(tabKey, idx), False)
        tb.Visible = False
        orderRows.Add tb

        Set tb = EnsureHeaderTextBox(host, CompareItemRowName(tabKey, idx), False)
        tb.Visible = False
        itemRows.Add tb

        fieldRows.Add lbl
    Loop
End Sub

Private Sub SetCompareTripletCaptions(ByVal tabKey As String, ByVal orderCaption As String, ByVal itemCaption As String)
    Dim host As Object

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    host.Controls(CompareOrderCaptionName(tabKey)).caption = orderCaption
    host.Controls(CompareItemCaptionName(tabKey)).caption = itemCaption
End Sub

Private Sub ToggleCompareTripletTabView(ByVal tabKey As String, ByVal showCompare As Boolean)
    Dim host As Object
    Dim lb As MSForms.ListBox
    Dim fieldRows As Collection
    Dim orderRows As Collection
    Dim itemRows As Collection
    Dim i As Long

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    Set lb = CompareListByKey(tabKey)
    If Not lb Is Nothing Then lb.Visible = Not showCompare

    SetHeaderControlVisible host, CompareFieldHeaderName(tabKey), showCompare
    SetHeaderControlVisible host, CompareOrderHeaderName(tabKey), showCompare
    SetHeaderControlVisible host, CompareItemHeaderName(tabKey), showCompare
    SetHeaderControlVisible host, CompareOrderCaptionName(tabKey), showCompare
    SetHeaderControlVisible host, CompareItemCaptionName(tabKey), showCompare

    Set fieldRows = CompareFieldRows(tabKey)
    Set orderRows = CompareOrderRows(tabKey)
    Set itemRows = CompareItemRows(tabKey)

    For i = 1 To fieldRows.Count
        fieldRows(i).Visible = showCompare And (Len(Trim$(CStr(fieldRows(i).caption))) > 0)
        orderRows(i).Visible = fieldRows(i).Visible
        itemRows(i).Visible = fieldRows(i).Visible
    Next i
End Sub

Private Function CompareDataRowCount(ByVal dataArr As Variant) As Long
    On Error GoTo Done
    If IsEmpty(dataArr) Then Exit Function
    CompareDataRowCount = UBound(dataArr, 1)
Done:
End Function

Private Sub LayoutCompareTripletTab(ByVal tabKey As String)
    Dim host As Object
    Dim fieldRows As Collection
    Dim orderRows As Collection
    Dim itemRows As Collection
    Dim rowCount As Long
    Dim totalW As Single
    Dim fieldW As Single
    Dim valueW As Single
    Dim headTop As Single
    Dim capTop As Single
    Dim rowsTop As Single
    Dim i As Long

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    rowCount = GetCompareRowCount(tabKey)
    If rowCount < 1 Then Exit Sub

    EnsureCompareTripletRowControls tabKey, rowCount

    Set fieldRows = CompareFieldRows(tabKey)
    Set orderRows = CompareOrderRows(tabKey)
    Set itemRows = CompareItemRows(tabKey)

    totalW = host.Width - 2 * PAD
    If totalW < 360 Then totalW = 360
    fieldW = totalW * 0.44
    valueW = (totalW - fieldW) / 2

    headTop = PAD
    capTop = headTop + 16
    rowsTop = capTop + 18

    SetHeaderControlRect host, CompareFieldHeaderName(tabKey), PAD, headTop, fieldW, 16
    SetHeaderControlRect host, CompareOrderHeaderName(tabKey), PAD + fieldW, headTop, valueW, 16
    SetHeaderControlRect host, CompareItemHeaderName(tabKey), PAD + fieldW + valueW, headTop, valueW, 16
    SetHeaderControlRect host, CompareOrderCaptionName(tabKey), PAD + fieldW, capTop, valueW, 14
    SetHeaderControlRect host, CompareItemCaptionName(tabKey), PAD + fieldW + valueW, capTop, valueW, 14

    For i = 1 To rowCount
        SetHeaderControlRect host, CStr(fieldRows(i).Name), PAD + 2, rowsTop + (i - 1) * CMP_TAB_ROW_H + 2, fieldW - 4, CMP_TAB_ROW_H - 4
        SetHeaderControlRect host, CStr(orderRows(i).Name), PAD + fieldW + 1, rowsTop + (i - 1) * CMP_TAB_ROW_H + 1, valueW - 2, CMP_TAB_ROW_H - 2
        SetHeaderControlRect host, CStr(itemRows(i).Name), PAD + fieldW + valueW + 1, rowsTop + (i - 1) * CMP_TAB_ROW_H + 1, valueW - 2, CMP_TAB_ROW_H - 2
    Next i

    On Error Resume Next
    host.ScrollBars = fmScrollBarsVertical
    host.ScrollHeight = rowsTop + rowCount * CMP_TAB_ROW_H + PAD
    On Error GoTo 0
End Sub

Private Sub RenderCompareTripletTab(ByVal tabKey As String, ByVal orderCaption As String, ByVal itemCaption As String, ByVal dataArr As Variant)
    Dim host As Object
    Dim fieldRows As Collection
    Dim orderRows As Collection
    Dim itemRows As Collection
    Dim dataRows As Long
    Dim rowCount As Long
    Dim i As Long
    Dim fieldName As String
    Dim orderValue As String
    Dim itemValue As String

    Set host = CompareFrameByKey(tabKey)
    If host Is Nothing Then Exit Sub

    EnsureCompareTripletTabUI tabKey
    SetCompareTripletCaptions tabKey, orderCaption, itemCaption

    dataRows = CompareDataRowCount(dataArr)
    rowCount = dataRows
    If rowCount < 1 Then rowCount = 1

    EnsureCompareTripletRowControls tabKey, rowCount
    SetCompareRowCount tabKey, rowCount
    LayoutCompareTripletTab tabKey
    ToggleCompareTripletTabView tabKey, True

    Set fieldRows = CompareFieldRows(tabKey)
    Set orderRows = CompareOrderRows(tabKey)
    Set itemRows = CompareItemRows(tabKey)

    For i = 1 To rowCount
        fieldName = vbNullString
        orderValue = vbNullString
        itemValue = vbNullString

        If i <= dataRows Then
            fieldName = CStr(dataArr(i, 1))
            orderValue = CStr(dataArr(i, 2))
            itemValue = CStr(dataArr(i, 3))
        ElseIf i = 1 Then
            fieldName = "(ingen data)"
        End If

        fieldRows(i).caption = fieldName
        orderRows(i).text = orderValue
        itemRows(i).text = itemValue

        fieldRows(i).Visible = (Len(Trim$(fieldName)) > 0)
        orderRows(i).Visible = fieldRows(i).Visible
        itemRows(i).Visible = fieldRows(i).Visible

        PaintComparePair host, CStr(orderRows(i).Name), CStr(itemRows(i).Name), orderValue, itemValue
    Next i

    For i = rowCount + 1 To fieldRows.Count
        fieldRows(i).caption = vbNullString
        orderRows(i).text = vbNullString
        itemRows(i).text = vbNullString
        fieldRows(i).Visible = False
        orderRows(i).Visible = False
        itemRows(i).Visible = False
    Next i

    On Error Resume Next
    host.ScrollTop = 0
    On Error GoTo 0
End Sub

Private Function CompareItemCaption(ByVal maintenanceItem As String) As String
    maintenanceItem = Trim$(maintenanceItem)
    If Len(maintenanceItem) > 0 Then
        CompareItemCaption = "Item " & maintenanceItem
    Else
        CompareItemCaption = "Item (mangler)"
    End If
End Function

Private Sub HookNavSinks()
    Set mNavSinks = New Collection
    Dim s As clsOverlayNavSink
    Set s = New clsOverlayNavSink: s.Init Me, btnTab0, 0: mNavSinks.Add s
    Set s = New clsOverlayNavSink: s.Init Me, btnTab1, 1: mNavSinks.Add s
    Set s = New clsOverlayNavSink: s.Init Me, btnTab2, 2: mNavSinks.Add s
    Set s = New clsOverlayNavSink: s.Init Me, btnTab3, 3: mNavSinks.Add s
    Set s = New clsOverlayNavSink: s.Init Me, btnTab4, 4: mNavSinks.Add s
End Sub

Public Sub OnOverlayTabChanged(ByVal idx As Long)
    If mIsLoading Then Exit Sub
    On Error Resume Next
    If idx < 0 Then idx = 0
    If idx > 4 Then idx = 4
    mActiveIdx = idx
    modOverlayUiBuild.ShowFrame mUI, mActiveIdx
    UpdateNavHighlight
    UpdateActionVisibility
    On Error GoTo 0
End Sub

Private Sub UpdateNavHighlight()
    Dim normalBg As Long: normalBg = RGB(226, 232, 240)
    Dim activeBg As Long: activeBg = RGB(200, 220, 255)
    Dim diffBg As Long: diffBg = RGB(255, 224, 224)
    Dim activeDiffBg As Long: activeDiffBg = RGB(255, 194, 194)

    If Not btnTab0 Is Nothing Then btnTab0.BackColor = IIf(mActiveIdx = 0, activeBg, normalBg)

    If Not btnTab1 Is Nothing Then btnTab1.BackColor = IIf(mActiveIdx = 1, activeBg, normalBg)
    If Not btnTab2 Is Nothing Then btnTab2.BackColor = IIf(mActiveIdx = 2, activeBg, normalBg)
    If Not btnTab3 Is Nothing Then btnTab3.BackColor = IIf(mActiveIdx = 3, activeBg, normalBg)

    If Not btnTab4 Is Nothing Then
        If mHasDecisionDiffs Then
            btnTab4.BackColor = IIf(mActiveIdx = 4, activeDiffBg, diffBg)
        Else
            btnTab4.BackColor = IIf(mActiveIdx = 4, activeBg, normalBg)
        End If
    End If
End Sub

Private Sub UpdateActionVisibility()
    If mCompareMode Then
        cmdEditRow.Visible = True
        cmdAddRow.Visible = True
        cmdDeleteRow.Visible = True

        cmdEditRow.caption = "Apply"
        cmdAddRow.caption = "Preview"
        cmdDeleteRow.caption = "Push"

        cmdEditRow.Enabled = True
        cmdAddRow.Enabled = True
        cmdDeleteRow.Enabled = (CountPushReadyRowsForOrder(mOrder) > 0)
        Exit Sub
    End If

    cmdEditRow.caption = "Edit Row"
    cmdAddRow.caption = "Add Row"
    cmdDeleteRow.caption = "Delete Row"

    Dim showListActions As Boolean
    showListActions = (mActiveIdx = 1)

    cmdEditRow.Visible = showListActions
    cmdAddRow.Visible = showListActions
    cmdDeleteRow.Visible = showListActions

    Dim lb As MSForms.ListBox
    Set lb = ActiveListBox()

    If Not lb Is Nothing Then
        cmdEditRow.Enabled = (lb.ListIndex >= 0)
        cmdDeleteRow.Enabled = (lb.ListIndex >= 0)
        cmdAddRow.Enabled = True
    Else
        cmdEditRow.Enabled = False
        cmdDeleteRow.Enabled = False
        cmdAddRow.Enabled = False
    End If
End Sub

Private Function ActiveListBox() As MSForms.ListBox
    Select Case mActiveIdx
        Case 1: Set ActiveListBox = lstOperations
        Case 2: Set ActiveListBox = lstObjects
        Case 3: Set ActiveListBox = lstAttachments
        Case 4: Set ActiveListBox = lstPlanning
        Case Else: Set ActiveListBox = Nothing
    End Select
End Function

Private Function ActiveSheetName() As String
    Select Case mActiveIdx
        Case 1: ActiveSheetName = SH_OPS
        Case 2: ActiveSheetName = WS_RAW_ORDRE_COMPONENTS
        Case 3: ActiveSheetName = WS_RAW_ORDRE_ATTACHMENTS
        Case 4: ActiveSheetName = WS_COCKPIT_DECISIONS
        Case Else: ActiveSheetName = vbNullString
    End Select
End Function

Private Function ActiveKeyField() As String
    ActiveKeyField = F_AUFNR
End Function

Private Function ActiveKeyValue() As String
    ActiveKeyValue = mOrder
End Function

Private Sub LayoutBottomArea()
    On Error Resume Next

    Dim formH As Single
    formH = Me.InsideHeight

    Dim clearY As Single
    clearY = formH - BOTTOM_PAD - cmdClear.Height
    If clearY < 0 Then clearY = 0

    cmdClear.Top = clearY
    cmdClose.Top = clearY

    Dim rowY As Single
    rowY = clearY - GAP - cmdEditRow.Height
    If rowY < 0 Then rowY = 0

    cmdEditRow.Top = rowY
    cmdAddRow.Top = rowY
    cmdDeleteRow.Top = rowY

    If Not fraProg Is Nothing Then fraProg.Top = rowY

    Dim frames As Object
    Set frames = mUI("frames")

    Dim frameTop As Single
    frameTop = frames("HeaderData").Top

    Dim newFrameH As Single
    newFrameH = rowY - GAP - frameTop
    If newFrameH < MIN_FRAME_H Then newFrameH = MIN_FRAME_H

    Dim k As Variant
    For Each k In frames.Keys
        frames(k).Height = newFrameH
    Next k

    LayoutLongTextPanel frames("LongText")
    ResizeFrameList frames("Operations"), "lstOperations"
    ResizeFrameList frames("Components"), "lstObjects"
    ResizeFrameList frames("Attachments"), "lstAttachments"
    ResizeFrameList frames("Decisions"), "lstPlanning"
    LayoutHeaderCompareList frames("HeaderData")
    LayoutCompareTripletTab CMP_KEY_OP
    LayoutCompareTripletTab CMP_KEY_COMP
    LayoutCompareTripletTab CMP_KEY_ATT

    cmdEditHeader.Top = frames("HeaderData").Height - PAD - cmdEditHeader.Height

    On Error GoTo 0
End Sub

Private Sub LayoutLongTextPanel(ByVal fra As Object)
    On Error Resume Next

    Dim totalW As Single
    Dim paneW As Single
    Dim paneTop As Single
    Dim paneH As Single

    totalW = fra.Width - 2 * PAD
    If totalW < 360 Then totalW = 360

    paneW = (totalW - GAP) / 2
    paneTop = 26
    paneH = fra.Height - paneTop - PAD
    If paneH < 120 Then paneH = 120

    SetHeaderControlRect fra, "lblLongTextOrder", PAD, 8, paneW, 16
    SetHeaderControlRect fra, "lblLongTextItem", PAD + paneW + GAP, 8, paneW, 16

    If Not fraLongTextOrder Is Nothing Then
        fraLongTextOrder.Left = PAD
        fraLongTextOrder.Top = paneTop
        fraLongTextOrder.Width = paneW
        fraLongTextOrder.Height = paneH
    End If

    If Not fraLongTextItem Is Nothing Then
        fraLongTextItem.Left = PAD + paneW + GAP
        fraLongTextItem.Top = paneTop
        fraLongTextItem.Width = paneW
        fraLongTextItem.Height = paneH
    Else
        fra.ScrollBars = fmScrollBarsVertical
    End If

    On Error GoTo 0
End Sub

Private Sub ResizeFrameList(ByVal fra As Object, ByVal listName As String)
    On Error Resume Next
    Dim lb As Object
    Set lb = fra.Controls(listName)
    If lb Is Nothing Then Exit Sub
    lb.Left = PAD
    lb.Top = PAD
    lb.Width = fra.Width - 2 * PAD
    lb.Height = fra.Height - 2 * PAD
    On Error GoTo 0
End Sub

Private Sub LayoutHeaderCompareList(ByVal fra As Object)
    On Error Resume Next

    Dim totalW As Single
    Dim fieldW As Single
    Dim valueW As Single
    Dim orderColLeft As Single
    Dim itemColLeft As Single
    Dim orderColW As Single
    Dim itemColW As Single
    Dim objTop As Single
    Dim objHeadTop As Single
    Dim objListTop As Single
    Dim objListH As Single
    Dim orderListW As Single
    Dim itemListW As Single
    Dim objGap As Single
    Dim orderRightLimit As Single
    Dim itemRightLimit As Single
    Dim orderHalfW As Single
    Dim itemHalfW As Single
    Dim innerGap As Single
    Dim objHeaderTop As Single
    Dim headTop As Single
    Dim row1Top As Single
    Dim longTop As Single
    Dim longBoxTop As Single
    Dim longBoxH As Single
    Dim afterLongTop As Single
    Dim detailRows As Long
    Dim rowCount As Long
    Dim i As Long

    totalW = fra.Width - 2 * PAD
    If totalW < 360 Then totalW = 360

    fieldW = 180
    valueW = (totalW - fieldW) / 2
    If valueW < 90 Then valueW = 90

    orderColLeft = PAD + fieldW + 1
    itemColLeft = PAD + fieldW + valueW + 1
    orderListW = valueW - 2
    itemListW = valueW - 2
    If orderListW < 90 Then orderListW = 90
    If itemListW < 90 Then itemListW = 90

    headTop = PAD
    row1Top = headTop + 18

    longTop = row1Top + HDR_COMPARE_ROW_H + 8
    longBoxTop = longTop
    longBoxH = 110
    If fra.Height < 420 Then longBoxH = 82

    SetHeaderControlRect fra, "lblCmpHdrField", PAD, headTop, fieldW, 16
    SetHeaderControlRect fra, "lblCmpHdrOrder", PAD + fieldW, headTop, valueW, 16
    SetHeaderControlRect fra, "lblCmpHdrItem", PAD + fieldW + valueW, headTop, valueW, 16

    SetHeaderControlRect fra, "lblCmpField1", PAD + 2, row1Top + 2, fieldW - 4, HDR_COMPARE_ROW_H - 4
    SetHeaderControlRect fra, "txtCmpOrder1", PAD + fieldW + 1, row1Top + 1, valueW - 2, HDR_COMPARE_ROW_H - 2
    SetHeaderControlRect fra, "txtCmpItem1", PAD + fieldW + valueW + 1, row1Top + 1, valueW - 2, HDR_COMPARE_ROW_H - 2

    ' Align object lists with the actual Order/Item value columns.
    orderColLeft = fra.Controls("txtCmpOrder1").Left
    itemColLeft = fra.Controls("txtCmpItem1").Left
    orderColW = fra.Controls("txtCmpOrder1").Width
    itemColW = fra.Controls("txtCmpItem1").Width
    objGap = 8
    orderRightLimit = itemColLeft - objGap
    itemRightLimit = fra.Width - PAD - 2

    orderListW = orderRightLimit - orderColLeft
    itemListW = itemRightLimit - itemColLeft

    ' Keep list widths aligned to their value-column controls.
    If orderListW > (orderColW - 2) Then orderListW = orderColW - 2
    If itemListW > (itemColW - 2) Then itemListW = itemColW - 2

    ' Hard stop: never allow Order list to intrude into Item area.
    If (orderColLeft + orderListW + objGap) > itemColLeft Then
        orderListW = itemColLeft - orderColLeft - objGap
    End If

    If orderListW < 70 Then orderListW = 70
    If itemListW < 70 Then itemListW = 70

    fra.Controls("lblCmpOrderLong").caption = "Long Text"
    SetHeaderControlRect fra, "lblCmpOrderLong", PAD + 2, longTop + 2, fieldW - 4, 16
    SetHeaderControlRect fra, "txtCmpOrderLongText", PAD + fieldW + 1, longBoxTop + 1, valueW - 2, longBoxH
    SetHeaderControlRect fra, "txtCmpItemLongText", PAD + fieldW + valueW + 1, longBoxTop + 1, valueW - 2, longBoxH

    SetHeaderControlVisible fra, "lblCmpOrderLong", True
    SetHeaderControlVisible fra, "lblCmpItemLong", False
    SetHeaderControlVisible fra, "txtCmpOrderLongText", True
    SetHeaderControlVisible fra, "txtCmpItemLongText", True

    afterLongTop = longBoxTop + longBoxH + 10

    If Not lstHeaderCompare Is Nothing Then
        lstHeaderCompare.Left = PAD
        lstHeaderCompare.Top = afterLongTop
        lstHeaderCompare.Width = totalW
        lstHeaderCompare.Height = fra.Height - lstHeaderCompare.Top - PAD
        If lstHeaderCompare.Height < 120 Then lstHeaderCompare.Height = 120
        ApplyHeaderCompareColumnWidths
    End If

    rowCount = HeaderCompareFieldCount()
    If rowCount < 1 Then rowCount = 1

    For i = 2 To HDR_COMPARE_MAX_ROWS
        SetHeaderControlRect fra, "lblCmpField" & CStr(i), PAD + 2, afterLongTop + (i - 2) * HDR_COMPARE_ROW_H + 2, fieldW - 4, HDR_COMPARE_ROW_H - 4
        SetHeaderControlRect fra, "txtCmpOrder" & CStr(i), PAD + fieldW + 1, afterLongTop + (i - 2) * HDR_COMPARE_ROW_H + 1, valueW - 2, HDR_COMPARE_ROW_H - 2
        SetHeaderControlRect fra, "txtCmpItem" & CStr(i), PAD + fieldW + valueW + 1, afterLongTop + (i - 2) * HDR_COMPARE_ROW_H + 1, valueW - 2, HDR_COMPARE_ROW_H - 2
    Next i

    detailRows = rowCount - 1
    If detailRows < 0 Then detailRows = 0

    objTop = afterLongTop + detailRows * HDR_COMPARE_ROW_H + 18
    objHeadTop = objTop + 16
    objHeaderTop = objHeadTop + 1
    objListTop = objHeadTop + 18
    objListH = fra.Height - objListTop - PAD
    If objListH < 90 Then objListH = 90

    SetHeaderControlRect fra, "lblObjSection", PAD + 2, objTop + 1, fieldW - 4, 16
    SetHeaderControlVisible fra, "lblObjOrder", False
    SetHeaderControlVisible fra, "lblObjItem", False

    innerGap = 2
    orderHalfW = CSng(Int((orderListW - innerGap) / 2))
    itemHalfW = CSng(Int((itemListW - innerGap) / 2))
    If orderHalfW < 36 Then orderHalfW = 36
    If itemHalfW < 36 Then itemHalfW = 36

    SetHeaderControlRect fra, "lblObjOrderCol1", orderColLeft + 2, objHeaderTop, orderHalfW - 4, 14
    SetHeaderControlRect fra, "lblObjOrderCol2", orderColLeft + orderHalfW + innerGap + 2, objHeaderTop, orderListW - orderHalfW - innerGap - 4, 14
    SetHeaderControlRect fra, "lblObjItemCol1", itemColLeft + 2, objHeaderTop, itemHalfW - 4, 14
    SetHeaderControlRect fra, "lblObjItemCol2", itemColLeft + itemHalfW + innerGap + 2, objHeaderTop, itemListW - itemHalfW - innerGap - 4, 14
    SetHeaderControlVisible fra, "lblObjOrderCol1", True
    SetHeaderControlVisible fra, "lblObjOrderCol2", True
    SetHeaderControlVisible fra, "lblObjItemCol1", True
    SetHeaderControlVisible fra, "lblObjItemCol2", True

    If Not lstObjOrder Is Nothing Then
        lstObjOrder.Left = orderColLeft
        lstObjOrder.Top = objListTop
        lstObjOrder.Width = orderHalfW
        lstObjOrder.Height = objListH
        lstObjOrder.ColumnCount = 1
        lstObjOrder.ColumnHeads = False
        lstObjOrder.Visible = True
    End If

    If Not lstObjOrderEq Is Nothing Then
        lstObjOrderEq.Left = orderColLeft + orderHalfW + innerGap
        lstObjOrderEq.Top = objListTop
        lstObjOrderEq.Width = orderListW - orderHalfW - innerGap
        lstObjOrderEq.Height = objListH
        lstObjOrderEq.ColumnCount = 1
        lstObjOrderEq.ColumnHeads = False
        lstObjOrderEq.Visible = True
    End If

    If Not lstObjItem Is Nothing Then
        lstObjItem.Left = itemColLeft
        lstObjItem.Top = objListTop
        lstObjItem.Width = itemHalfW
        lstObjItem.Height = objListH
        lstObjItem.ColumnCount = 1
        lstObjItem.ColumnHeads = False
        lstObjItem.Visible = True
    End If

    If Not lstObjItemEq Is Nothing Then
        lstObjItemEq.Left = itemColLeft + itemHalfW + innerGap
        lstObjItemEq.Top = objListTop
        lstObjItemEq.Width = itemListW - itemHalfW - innerGap
        lstObjItemEq.Height = objListH
        lstObjItemEq.ColumnCount = 1
        lstObjItemEq.ColumnHeads = False
        lstObjItemEq.Visible = True
    End If

    On Error GoTo 0
End Sub

Private Sub ApplyHeaderObjectColumnWidths(ByVal lb As MSForms.ListBox)
    On Error Resume Next
    Dim totalW As Single
    Dim usableW As Single
    Dim colWLeft As Long
    Dim colWRight As Long

    totalW = lb.Width
    usableW = totalW - 6
    If usableW < 20 Then Exit Sub

    colWLeft = CLng(Int(usableW / 2))
    colWRight = CLng(Int(usableW - colWLeft))

    lb.ColumnCount = 2
    lb.ColumnWidths = vbNullString
    lb.ColumnWidths = CStr(colWLeft) & ";" & CStr(colWRight)
    On Error GoTo 0
End Sub

Private Sub SetHeaderControlRect(ByVal host As Object, ByVal controlName As String, ByVal leftPos As Single, ByVal topPos As Single, ByVal widthVal As Single, ByVal heightVal As Single)
    On Error Resume Next
    host.Controls(controlName).Left = leftPos
    host.Controls(controlName).Top = topPos
    host.Controls(controlName).Width = widthVal
    host.Controls(controlName).Height = heightVal
    On Error GoTo 0
End Sub

Private Function HeaderCompareFieldCount() As Long
    Dim defs As Collection

    On Error Resume Next
    Set defs = HeaderCompareFields()
    On Error GoTo 0

    If defs Is Nothing Then Exit Function

    HeaderCompareFieldCount = defs.Count
    If HeaderCompareFieldCount > HDR_COMPARE_MAX_ROWS Then HeaderCompareFieldCount = HDR_COMPARE_MAX_ROWS
End Function

Private Sub cmdLoad_Click()
    On Error GoTo EH

    If mIsLoading Then Exit Sub

    Dim inputOrder As String
    inputOrder = Trim$(txtOrder.text)

    If mCompareMode Then
        If Len(inputOrder) = 0 Then inputOrder = FirstOrderFromCompareQueue()
        If Len(inputOrder) = 0 Then
            MsgBox "Ingen compare data fundet. Koer compare cockpit foerst.", vbExclamation, "Compare"
            Exit Sub
        End If

        mOrder = CleanKey(inputOrder)
        txtOrder.text = mOrder

        mIsLoading = True
        SafeLoad True
        SetProgress 10, "Loading compare queue..."
        LoadAllData mOrder
        SetProgress 100, "Done"
        DoEvents
        HideProgress
        SafeLoad False
        mIsLoading = False
        Exit Sub
    End If

    If Len(inputOrder) = 0 Then Exit Sub

    mOrder = CleanKey(inputOrder)

    mIsLoading = True
    SafeLoad True
    SetProgress 2, "Fetching order..."

    ClearHeaderFields
    ClearAllLists
    lblStatusShort.caption = vbNullString

    Dim errText As String
    If Not FetchWorkOrderAll(mOrder, errText) Then
        SetProgress 0, "Failed"
        SafeLoad False
        HideProgress
        mIsLoading = False
        MsgBox errText, vbExclamation, "Load"
        Exit Sub
    End If

    SetProgress 55, "Preparing..."
    BuildOpLongTextMap mOrder
    LoadAllData mOrder

    SetProgress 100, "Done"
    DoEvents
    HideProgress
    SafeLoad False
    mIsLoading = False
    Exit Sub

EH:
    mIsLoading = False
    SafeLoad False
    HideProgress
    MsgBox "Load fejlede: " & Err.Description, vbExclamation, "Load"
End Sub

Private Sub txtOrder_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If KeyCode = vbKeyReturn Then cmdLoad_Click
End Sub

Private Sub cmdClear_Click()
    ClearHeaderFields
    ClearAllLists
    txtOrder.text = vbNullString
    txtLongText.text = vbNullString
    lblStatusShort.caption = vbNullString
    BindEmptyAll
    BindEmptyHeaderCompare
End Sub

Private Sub cmdClose_Click()
    On Error Resume Next

    If mCompareMode Then
        Dim pending As Long
        pending = CountPendingDecisionsForOrder(mOrder)
        If pending > 0 Then
            MsgBox "Der er stadig " & CStr(pending) & " diff-linjer uden beslutning." & vbCrLf & _
                   "Tag stilling i Decisions/LongText foer du lukker.", vbExclamation, "Compare"
            Exit Sub
        End If
    End If

    mdlFormOverlay.CloseOverlay
End Sub

Private Sub cmdEditHeader_Click()
    If Not mHeaderEdit Then
        mHeaderEdit = True
        cmdEditHeader.caption = "Save"
        LockHeaderFields False
        Exit Sub
    End If

    mHeaderEdit = False
    cmdEditHeader.caption = "Edit"
    SaveHeaderEdits
    LockHeaderFields True
End Sub

Private Sub cmdEditLongText_Click()
    If Not mLongTextEdit Then
        mLongTextEdit = True
        cmdEditLongText.caption = "Save"
        txtLongText.locked = False
        Exit Sub
    End If

    mLongTextEdit = False
    cmdEditLongText.caption = "Edit"
    txtLongText.locked = True
    SaveLongText
End Sub

Private Sub lstOperations_MouseUp(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    If Button = 2 Then
        ShowPopup
        Exit Sub
    End If
    If Button = 1 Then
        HandleLtClick X
    End If
End Sub

Private Sub lstPermits_MouseUp(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    If Button = 2 Then ShowPopup
End Sub

Private Sub lstObjects_MouseUp(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    If Button = 2 Then ShowPopup
End Sub

Private Sub lstAttachments_MouseUp(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    If Button = 2 Then ShowPopup
End Sub

Private Sub lstPlanning_MouseUp(ByVal Button As Integer, ByVal Shift As Integer, ByVal X As Single, ByVal Y As Single)
    If Button = 2 Then ShowPopup
End Sub

Private Sub EnsurePopupMenu()
    If mPopupReady Then Exit Sub
    BuildPopupMenu
    mPopupReady = True
End Sub

Private Sub BuildPopupMenu()
    On Error Resume Next
    Application.CommandBars(POPUP_NAME).Delete
    On Error GoTo 0

    Dim cb As CommandBar
    Set cb = Application.CommandBars.Add(POPUP_NAME, msoBarPopup, False, True)
    If cb Is Nothing Then Exit Sub

    With cb.Controls.Add(msoControlButton)
        .caption = "Edit"
        .OnAction = "OverlayRowMenu_Edit"
    End With

    With cb.Controls.Add(msoControlButton)
        .caption = "Add Row"
        .OnAction = "OverlayRowMenu_Add"
    End With

    With cb.Controls.Add(msoControlButton)
        .caption = "Delete Row"
        .OnAction = "OverlayRowMenu_Delete"
    End With
End Sub

Private Sub ShowPopup()
    EnsurePopupMenu
    On Error Resume Next
    Application.CommandBars(POPUP_NAME).ShowPopup
End Sub

Private Sub cmdEditRow_Click()
    If mCompareMode Then
        ApplyCompareDecisionsNow
        Exit Sub
    End If
    EditSelectedRow
End Sub

Private Sub cmdAddRow_Click()
    If mCompareMode Then
        PreviewComparePushNow
        Exit Sub
    End If
    AddRowToActiveTab
End Sub

Private Sub cmdDeleteRow_Click()
    If mCompareMode Then
        PushCompareNow
        Exit Sub
    End If
    DeleteSelectedRow
End Sub

Public Sub EditSelectedRow()
    On Error GoTo EH

    Dim lb As MSForms.ListBox
    Set lb = ActiveListBox()
    If lb Is Nothing Then Exit Sub
    If lb.ListIndex < 0 Then Exit Sub
    If Len(lb.rowSource) = 0 Then Exit Sub

    Dim sheetName As String
    sheetName = ActiveSheetName()
    If Len(sheetName) = 0 Then Exit Sub

    Dim dlg As New ufRowEditorPanel
    dlg.InitHost Me, lb, sheetName
    dlg.Show vbModal
    Unload dlg

    ReloadActiveTab
    Exit Sub

EH:
    MsgBox "EditSelectedRow failed: " & Err.Number & " - " & Err.Description, vbExclamation, "Edit Row"
End Sub

Public Sub AddRowToActiveTab()
    On Error GoTo EH

    Dim sheetName As String
    sheetName = ActiveSheetName()
    If Len(sheetName) = 0 Then Exit Sub

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(sheetName)

    Dim keyField As String, keyValue As String
    keyField = ActiveKeyField()
    keyValue = ActiveKeyValue()

    Dim lastRow As Long
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row + 1

    Dim colKey As Long
    colKey = FindHeaderIndex(ws, keyField)
    If colKey > 0 Then ws.Cells(lastRow, colKey).Value2 = keyValue

    ReloadActiveTab
    Exit Sub

EH:
    MsgBox "AddRowToActiveTab failed: " & Err.Number & " - " & Err.Description, vbExclamation, "Add Row"
End Sub

Public Sub DeleteSelectedRow()
    On Error GoTo EH

    Dim lb As MSForms.ListBox
    Set lb = ActiveListBox()
    If lb Is Nothing Then Exit Sub
    If lb.ListIndex < 0 Then Exit Sub
    If Len(lb.rowSource) = 0 Then Exit Sub

    Dim wsOV As Worksheet, bodyRng As Range
    Set bodyRng = mdlOverlayView.RangeFromRowSource(lb.rowSource, wsOV)
    If bodyRng Is Nothing Then Exit Sub

    Dim srcRow As Long
    srcRow = CLng(lb.List(lb.ListIndex, bodyRng.Columns.Count - 1))

    Dim sheetName As String
    sheetName = ActiveSheetName()
    If Len(sheetName) = 0 Then Exit Sub

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(sheetName)

    Application.DisplayAlerts = False
    ws.rows(srcRow).Delete
    Application.DisplayAlerts = True

    ReloadActiveTab
    Exit Sub

EH:
    Application.DisplayAlerts = True
    MsgBox "DeleteSelectedRow failed: " & Err.Number & " - " & Err.Description, vbExclamation, "Delete Row"
End Sub

Private Sub ReloadActiveTab()
    If mIsLoading Then Exit Sub

    If mCompareMode Then
        Select Case mActiveIdx
            Case 0: LoadHeaderData mOrder
            Case 1: LoadOperations mOrder
            Case 2: LoadComponents mOrder
            Case 3: LoadAttachments mOrder
            Case 4: LoadDecisions mOrder
        End Select
        RefreshCompareDecisionState
        Exit Sub
    End If

    Select Case mActiveIdx
        Case 1: LoadOperations mOrder
        Case 2: LoadComponents mOrder
        Case 3: LoadAttachments mOrder
        Case 4: LoadDecisions mOrder
    End Select
End Sub

Private Sub LoadAllData(ByVal orderNo As String)
    If mCompareMode Then
        SetProgress 40, "Header"
        LoadHeaderData orderNo
        SetProgress 62, "Operations"
        LoadOperations orderNo
        SetProgress 76, "Components"
        LoadComponents orderNo
        SetProgress 88, "Attachments"
        LoadAttachments orderNo
        SetProgress 96, "Decisions"
        LoadDecisions orderNo
        RefreshCompareDecisionState
        Exit Sub
    End If

    SetProgress 60, "Header"
    LoadHeaderData orderNo
    SetProgress 72, "Operations"
    LoadOperations orderNo
    SetProgress 84, "Components"
    LoadComponents orderNo
    SetProgress 90, "Attachments"
    LoadAttachments orderNo
    SetProgress 95, "Decisions"
    LoadDecisions orderNo
End Sub

Private Sub LoadHeaderData(ByVal orderNo As String)
    Dim ws As Worksheet
    Set ws = SheetByName(SH_HDR)

    Dim r As Long
    r = 0
    If Not ws Is Nothing Then
        r = FindFirstRowByKey(ws, F_AUFNR, orderNo)
    End If

    If r > 0 Then
        txtLongText.text = GetRowValue(ws, r, F_LONGTEXT)

        Dim host As Object
        Set host = mUI("frames")("HeaderData")

        Dim tbPri As Object
        Set tbPri = Nothing
        On Error Resume Next
        Set tbPri = host.Controls("txtPriorityText")
        On Error GoTo 0
        If Not tbPri Is Nothing Then tbPri.text = Trim$(GetRowValue(ws, r, "Priok") & " " & GetRowValue(ws, r, "Priokx"))

        Dim tbPlan As Object
        Set tbPlan = Nothing
        On Error Resume Next
        Set tbPlan = host.Controls("txtPlannerGrpText")
        On Error GoTo 0
        If Not tbPlan Is Nothing Then tbPlan.text = GetRowValue(ws, r, "Ingrp")

        txtMainWorkCtr.text = GetRowValue(ws, r, F_VAPLZ)
        txtPersonResp.text = GetRowValue(ws, r, F_PERSINIT)
        txtBasicStart.text = FormatSerialDate(GetRowValue(ws, r, F_GSTRP))
        txtBasicFin.text = FormatSerialDate(GetRowValue(ws, r, F_GLTRP))
        txtOrderType.text = GetRowValue(ws, r, F_AUART)
        txtMaintPlant.text = GetRowValue(ws, r, F_SWERK)
        txtFuncLoc.text = GetRowValue(ws, r, F_TPLNR)
        txtEquipment.text = FirstValueFromSheet(orderNo, SH_OBJ, F_AUFNR, F_EQUNR)
    Else
        ClearHeaderFields
    End If

    LoadCompareHeaderGrid orderNo
    LoadHeaderObjectCompare orderNo

    Dim maintenanceItem As String
    Dim orderLongText As String
    Dim itemLongText As String

    ResolveOrderItemLongText orderNo, maintenanceItem, orderLongText, itemLongText
    SetHeaderOrderItemCaptions orderNo, maintenanceItem
    RenderHeaderCompareLongText orderLongText, itemLongText

    mHasLongTextDiffs = (NormalizeCompareValue(orderLongText) <> NormalizeCompareValue(itemLongText))
    If mCompareMode Then
        mHasLongTextDiffs = mHasLongTextDiffs Or (CountRowsByKeyInSheet(WS_COCKPIT_LONGTEXT_EDITOR, "Order_number", orderNo) > 0)
    End If

    If mCompareMode Then
        ApplyHeaderDiffHighlights orderNo
    ElseIf r > 0 Then
        lblStatusShort.caption = GetStatusShort(orderNo)
        lblStatusShort.ForeColor = modOverlayUI.UI_LABEL
    End If
End Sub

Private Sub LoadCompareHeaderGrid(ByVal orderNo As String)
    Dim wsOrder As Worksheet
    Dim wsItem As Worksheet
    Dim orderRow As Long
    Dim itemRow As Long
    Dim maintenanceItem As String
    Dim dataArr() As Variant
    Dim fieldDefs As Collection
    Dim fieldDef As Variant
    Dim i As Long

    Set wsOrder = SheetByName(WS_RAW_ORDRE_HEADER)
    Set wsItem = SheetByName(WS_ITEM_EXTRACT)
    If wsOrder Is Nothing Then
        SetHeaderOrderItemCaptions orderNo, vbNullString
        BindEmptyHeaderCompare
        Exit Sub
    End If

    orderRow = FindFirstRowByAnyKey(wsOrder, Array("Order_number", "Aufnr", "AUFNR"), orderNo)
    If orderRow = 0 Then
        SetHeaderOrderItemCaptions orderNo, vbNullString
        BindEmptyHeaderCompare
        Exit Sub
    End If

    maintenanceItem = GetRowValueAny(wsOrder, orderRow, Array("Maintenance_item", "IW33_WAPOS"))
    If Not wsItem Is Nothing And Len(CleanKey(maintenanceItem)) > 0 Then
        itemRow = FindFirstRowByAnyKey(wsItem, Array("Maintenance_item", "Source_Item_Number", "RMIPM-WAPOS"), maintenanceItem)
    End If

    SetHeaderOrderItemCaptions orderNo, maintenanceItem

    Set fieldDefs = HeaderCompareFields()
    If fieldDefs Is Nothing Then
        BindEmptyHeaderCompare
        Exit Sub
    End If

    If fieldDefs.Count = 0 Then
        BindEmptyHeaderCompare
        Exit Sub
    End If

    ReDim dataArr(1 To fieldDefs.Count, 1 To 3)

    For i = 1 To fieldDefs.Count
        fieldDef = fieldDefs(i)
        dataArr(i, 1) = CStr(fieldDef(0))
        dataArr(i, 2) = GetRowValueAny(wsOrder, orderRow, fieldDef(1))
        dataArr(i, 3) = GetRowValueAny(wsItem, itemRow, fieldDef(2))
    Next i

    BindHeaderCompareRows dataArr
    RenderHeaderCompareVisualRows dataArr
End Sub

' Update this list to control exactly which fields appear and in what order.
Private Function HeaderCompareFields() As Collection
    Dim out As Collection
    Set out = New Collection

    out.Add Array("Short_Text", Array("Short_Text", "ShortText", "Ktext", "Description"), Array("Short_Text", "ShortText", "Ktext", "Description"))
    out.Add Array("Main_WorkCtr", Array("Main_WorkCtr", "Main_Work_Ctr", "Vaplz"), Array("Main_WorkCtr", "Main_Work_Ctr", "Vaplz"))
    out.Add Array("Functional_loc", Array("Functional_loc", "Functional_Loc", "Tplnr"), Array("Functional_loc", "Functional_Loc", "Tplnr"))
    out.Add Array("MaintActivityType", Array("MaintActivityType", "MaintenanceActivityType", "Maint_Activity_Type", "Ilart"), Array("MaintActivityType", "MaintenanceActivityType", "Maint_Activity_Type", "Ilart"))
    out.Add Array("Priority", Array("Priority", "Priok"), Array("Priority", "Priok"))

    Set HeaderCompareFields = out
End Function

Private Sub BindHeaderCompareRows(ByRef dataArr As Variant)
    Dim headers(1 To 3) As String

    If lstHeaderCompare Is Nothing Then Exit Sub

    headers(1) = "Field"
    headers(2) = "Order"
    headers(3) = "Item"

    mdlOverlayView.BindListBox lstHeaderCompare, headers, dataArr, HDR_COMPARE_TOP
    ApplyHeaderCompareColumnWidths
End Sub

Private Sub BindEmptyHeaderCompare()
    Dim blank(1 To 1, 1 To 3) As Variant
    blank(1, 1) = vbNullString
    blank(1, 2) = vbNullString
    blank(1, 3) = vbNullString

    BindHeaderCompareRows blank
    RenderHeaderCompareVisualRows blank
End Sub

Private Sub SetHeaderOrderItemCaptions(ByVal orderNo As String, ByVal maintenanceItem As String)
    Dim host As Object
    Set host = mUI("frames")("HeaderData")

    On Error Resume Next
    host.Controls("lblCmpHdrOrder").caption = "Order " & orderNo
    host.Controls("lblCmpHdrItem").caption = IIf(Len(Trim$(maintenanceItem)) > 0, "Item " & maintenanceItem, "Item (mangler)")
    If Not lblLongTextOrder Is Nothing Then lblLongTextOrder.caption = "Order " & orderNo
    If Not lblLongTextItem Is Nothing Then lblLongTextItem.caption = IIf(Len(Trim$(maintenanceItem)) > 0, "Item " & maintenanceItem, "Item (mangler)")
    On Error GoTo 0
End Sub

Private Sub ApplyHeaderCompareColumnWidths()
    On Error Resume Next

    If lstHeaderCompare Is Nothing Then Exit Sub

    Dim totalW As Single
    Dim fieldW As Single
    Dim valueW As Single

    totalW = lstHeaderCompare.Width - 12
    If totalW < 360 Then totalW = 360

    fieldW = 180
    valueW = (totalW - fieldW) / 2
    If valueW < 90 Then valueW = 90

    lstHeaderCompare.ColumnWidths = CStr(fieldW) & ";" & CStr(valueW) & ";" & CStr(valueW)
    On Error GoTo 0
End Sub

Private Sub ToggleHeaderCompareView(ByVal showCompare As Boolean)
    Dim host As Object
    Dim names As Variant
    Dim i As Long

    Set host = mUI("frames")("HeaderData")

    names = Array( _
        "lblMWC", "txtMainWorkCtr", _
        "lblPriority", "cmbPriority", "txtPriorityText", _
        "lblPlanner", "cmbPlannerGrp", "txtPlannerGrpText", _
        "lblNotif", "txtNotifNo", _
        "lblPR", "txtPersonResp", _
        "lblStart", "txtBasicStart", _
        "lblFinish", "txtBasicFin", _
        "lblOrderType", "txtOrderType", _
        "lblMaintPlant", "txtMaintPlant", _
        "lblFuncLoc", "txtFuncLoc", _
        "lblEquip", "txtEquipment", _
        "lblRev", "txtRevision" _
    )

    For i = LBound(names) To UBound(names)
        SetHeaderControlVisible host, CStr(names(i)), Not showCompare
    Next i

    SetHeaderControlVisible host, "lblHeaderCompare", False
    If Not lstHeaderCompare Is Nothing Then lstHeaderCompare.Visible = False
    SetHeaderCompareVisualVisible host, showCompare
End Sub

Private Sub SetHeaderControlVisible(ByVal host As Object, ByVal controlName As String, ByVal isVisible As Boolean)
    On Error Resume Next
    host.Controls(controlName).Visible = isVisible
    On Error GoTo 0
End Sub

Private Sub SetHeaderCompareVisualVisible(ByVal host As Object, ByVal isVisible As Boolean)
    Dim i As Long

    SetHeaderControlVisible host, "lblCmpHdrField", isVisible
    SetHeaderControlVisible host, "lblCmpHdrOrder", isVisible
    SetHeaderControlVisible host, "lblCmpHdrItem", isVisible

    For i = 1 To HDR_COMPARE_MAX_ROWS
        SetHeaderControlVisible host, "lblCmpField" & CStr(i), isVisible
        SetHeaderControlVisible host, "txtCmpOrder" & CStr(i), isVisible
        SetHeaderControlVisible host, "txtCmpItem" & CStr(i), isVisible
    Next i

    SetHeaderControlVisible host, "lblObjOrderCol1", isVisible
    SetHeaderControlVisible host, "lblObjOrderCol2", isVisible
    SetHeaderControlVisible host, "lblObjItemCol1", isVisible
    SetHeaderControlVisible host, "lblObjItemCol2", isVisible
    SetHeaderControlVisible host, "lstObjOrder", isVisible
    SetHeaderControlVisible host, "lstObjOrderEq", isVisible
    SetHeaderControlVisible host, "lstObjItem", isVisible
    SetHeaderControlVisible host, "lstObjItemEq", isVisible
End Sub

Private Sub RenderHeaderCompareVisualRows(ByRef dataArr As Variant)
    Dim host As Object
    Dim i As Long
    Dim rowCount As Long
    Dim fieldName As String
    Dim orderVal As String
    Dim itemVal As String

    Set host = mUI("frames")("HeaderData")
    If host Is Nothing Then Exit Sub

    rowCount = 0
    On Error Resume Next
    rowCount = UBound(dataArr, 1)
    On Error GoTo 0
    If rowCount > HDR_COMPARE_MAX_ROWS Then rowCount = HDR_COMPARE_MAX_ROWS

    For i = 1 To HDR_COMPARE_MAX_ROWS
        fieldName = vbNullString
        orderVal = vbNullString
        itemVal = vbNullString

        If i <= rowCount Then
            fieldName = CStr(dataArr(i, 1))
            orderVal = CStr(dataArr(i, 2))
            itemVal = CStr(dataArr(i, 3))
        End If

        If Len(Trim$(fieldName)) > 0 Then
            host.Controls("lblCmpField" & CStr(i)).caption = fieldName
            host.Controls("txtCmpOrder" & CStr(i)).text = orderVal
            host.Controls("txtCmpItem" & CStr(i)).text = itemVal

            PaintComparePair host, "txtCmpOrder" & CStr(i), "txtCmpItem" & CStr(i), orderVal, itemVal

            SetHeaderControlVisible host, "lblCmpField" & CStr(i), True
            SetHeaderControlVisible host, "txtCmpOrder" & CStr(i), True
            SetHeaderControlVisible host, "txtCmpItem" & CStr(i), True
        Else
            host.Controls("lblCmpField" & CStr(i)).caption = vbNullString
            host.Controls("txtCmpOrder" & CStr(i)).text = vbNullString
            host.Controls("txtCmpItem" & CStr(i)).text = vbNullString

            SetHeaderControlVisible host, "lblCmpField" & CStr(i), False
            SetHeaderControlVisible host, "txtCmpOrder" & CStr(i), False
            SetHeaderControlVisible host, "txtCmpItem" & CStr(i), False
        End If
    Next i
End Sub

Private Sub RenderHeaderCompareLongText(ByVal orderLongText As String, ByVal itemLongText As String)
    Dim host As Object

    Set host = mUI("frames")("HeaderData")
    If host Is Nothing Then Exit Sub

    host.Controls("txtCmpOrderLongText").text = orderLongText
    host.Controls("txtCmpItemLongText").text = itemLongText

    PaintComparePair host, "txtCmpOrderLongText", "txtCmpItemLongText", orderLongText, itemLongText
    PaintCompareEditorText host, "txtCmpOrderLongText", "txtCmpItemLongText", orderLongText, itemLongText
End Sub

Private Sub PaintCompareEditorText(ByVal host As Object, ByVal leftControlName As String, ByVal rightControlName As String, ByVal leftValue As String, ByVal rightValue As String)
    Dim isSame As Boolean

    isSame = (NormalizeCompareValue(leftValue) = NormalizeCompareValue(rightValue))

    On Error Resume Next
    If isSame Then
        host.Controls(leftControlName).ForeColor = modOverlayUI.UI_LABEL
        host.Controls(rightControlName).ForeColor = modOverlayUI.UI_LABEL
    Else
        host.Controls(leftControlName).ForeColor = RGB(192, 0, 0)
        host.Controls(rightControlName).ForeColor = RGB(192, 0, 0)
    End If
    On Error GoTo 0
End Sub

Private Sub PaintComparePair(ByVal host As Object, ByVal leftControlName As String, ByVal rightControlName As String, ByVal leftValue As String, ByVal rightValue As String)
    Dim bgColor As Long
    Dim leftNorm As String
    Dim rightNorm As String

    leftNorm = NormalizeCompareValue(leftValue)
    rightNorm = NormalizeCompareValue(rightValue)

    If Len(leftNorm) = 0 And Len(rightNorm) = 0 Then
        bgColor = modOverlayUI.UI_INPUT_BG
    ElseIf leftNorm = rightNorm Then
        bgColor = RGB(226, 239, 218)
    Else
        bgColor = RGB(255, 199, 206)
    End If

    On Error Resume Next
    host.Controls(leftControlName).BackColor = bgColor
    host.Controls(rightControlName).BackColor = bgColor
    On Error GoTo 0
End Sub

Private Function NormalizeCompareValue(ByVal rawValue As String) As String
    Dim out As String

    out = CStr(rawValue)
    out = Replace$(out, vbCrLf, " ")
    out = Replace$(out, vbCr, " ")
    out = Replace$(out, vbLf, " ")
    out = Replace$(out, vbTab, " ")
    out = LCase$(Trim$(out))

    Do While InStr(1, out, "  ", vbBinaryCompare) > 0
        out = Replace$(out, "  ", " ")
    Loop

    NormalizeCompareValue = out
End Function

Private Function GetStatusShort(ByVal orderNo As String) As String
    Dim wsS As Worksheet
    Set wsS = SheetByName(SH_STATUS)
    If wsS Is Nothing Then Exit Function
    Dim r As Long
    r = FindFirstRowByKey(wsS, F_AUFNR, orderNo)
    If r = 0 Then Exit Function
    Dim s As String
    s = GetRowValue(wsS, r, "StatusShort")
    If Len(s) = 0 Then s = GetRowValue(wsS, r, "Txt04")
    If Len(s) = 0 Then s = GetRowValue(wsS, r, "Statxt")
    GetStatusShort = s
End Function

Private Sub LoadOperations(ByVal orderNo As String)
    If mCompareMode Then
        LoadOperationsCompareRows orderNo
        Exit Sub
    End If

    ToggleCompareTripletTabView CMP_KEY_OP, False

    Dim baseSpec As Variant
    baseSpec = modUiFieldMap.GetColumns_Operations()
    Dim colSpec As Variant
    colSpec = PrependLTColumn(baseSpec)
    LoadListFromSheetEx lstOperations, mdlOverlayView.OP_TOP, SH_OPS, F_AUFNR, orderNo, colSpec, True
End Sub

Private Sub LoadOperationsCompareRows(ByVal orderNo As String)
    Dim maintenanceItem As String
    Dim taskKey As String
    Dim orderRow As Long
    Dim itemRow As Long
    Dim rows As Variant

    ResolveOrderTaskContext orderNo, maintenanceItem, taskKey, orderRow, itemRow
    SetHeaderOrderItemCaptions orderNo, maintenanceItem

    rows = BuildOperationTripletRows(orderNo, taskKey)
    RenderCompareTripletTab CMP_KEY_OP, "Order " & orderNo, CompareItemCaption(maintenanceItem), rows
End Sub

Private Sub LoadLongTextTab(ByVal orderNo As String)
    Dim maintenanceItem As String
    Dim orderLongText As String
    Dim itemLongText As String

    ResolveOrderItemLongText orderNo, maintenanceItem, orderLongText, itemLongText
    SetHeaderOrderItemCaptions orderNo, maintenanceItem
    RenderHeaderCompareLongText orderLongText, itemLongText
    ClearLongTextLinePanels

    mHasLongTextDiffs = (NormalizeCompareValue(orderLongText) <> NormalizeCompareValue(itemLongText))
    If mCompareMode Then
        mHasLongTextDiffs = mHasLongTextDiffs Or (CountRowsByKeyInSheet(WS_COCKPIT_LONGTEXT_EDITOR, "Order_number", orderNo) > 0)
    End If
End Sub

Private Sub LoadComponents(ByVal orderNo As String)
    LoadComponentsCompareRows orderNo
End Sub

Private Sub LoadDecisions(ByVal orderNo As String)
    Dim keyValue As String

    keyValue = CleanKey(orderNo)
    If Len(keyValue) = 0 Then keyValue = FirstOrderFromCompareQueue()

    If Len(keyValue) = 0 Then
        BindEmptyList lstPlanning, DEC_TOP, CompareDecisionColumns()
        mHasDecisionDiffs = False
        Exit Sub
    End If

    LoadListFromSheetEx lstPlanning, DEC_TOP, WS_COCKPIT_DECISIONS, "Order_number", keyValue, CompareDecisionColumns(), False
    mHasDecisionDiffs = (CountRowsByKeyInSheet(WS_COCKPIT_DECISIONS, "Order_number", keyValue) > 0)
End Sub

Private Sub LoadAttachments(ByVal orderNo As String)
    LoadAttachmentsCompareRows orderNo
End Sub

Private Sub EnsureLongTextLineUi()
    On Error Resume Next

    Dim host As MSForms.Frame
    Set host = LongTextHostFrame()
    If host Is Nothing Then Exit Sub

    If Not fraLongTextOrder Is Nothing And Not fraLongTextItem Is Nothing Then
        fraLongTextOrder.caption = vbNullString
        fraLongTextItem.caption = vbNullString
        fraLongTextOrder.ScrollBars = fmScrollBarsVertical
        fraLongTextItem.ScrollBars = fmScrollBarsVertical
    Else
        host.caption = vbNullString
        host.ScrollBars = fmScrollBarsVertical
    End If

    If mLtOrderLines Is Nothing Then Set mLtOrderLines = New Collection
    If mLtItemLines Is Nothing Then Set mLtItemLines = New Collection

    On Error GoTo 0
End Sub

Private Sub ClearLongTextLinePanels()
    HideLongTextLines mLtOrderLines
    HideLongTextLines mLtItemLines
End Sub

Private Sub HideLongTextLines(ByVal lines As Collection)
    On Error Resume Next
    If lines Is Nothing Then Exit Sub

    Dim i As Long
    For i = 1 To lines.Count
        lines(i).Visible = False
        lines(i).text = vbNullString
    Next i
    On Error GoTo 0
End Sub

Private Function EnsureLongTextLineControl(ByVal host As MSForms.Frame, ByRef cache As Collection, ByVal idx As Long, ByVal prefix As String) As MSForms.TextBox
    Dim tb As MSForms.TextBox

    If cache Is Nothing Then Set cache = New Collection

    Do While cache.Count < idx
        Set tb = host.Controls.Add("Forms.TextBox.1", prefix & CStr(cache.Count + 1), True)
        modOverlayUI.StyleTextBox tb, False, False, True
        tb.BorderStyle = fmBorderStyleSingle
        tb.SpecialEffect = fmSpecialEffectFlat
        tb.Font.name = modOverlayUI.UI_FONT_NAME
        tb.Font.Size = 9
        tb.Visible = False
        cache.Add tb
    Loop

    Set EnsureLongTextLineControl = cache(idx)
End Function

Private Sub RenderLongTextCompareLines(ByVal orderLongText As String, ByVal itemLongText As String)
    Dim host As MSForms.Frame
    Dim useNestedFrames As Boolean
    Dim totalW As Single
    Dim paneW As Single
    Dim paneTop As Single
    Dim orderLines As Variant
    Dim itemLines As Variant
    Dim orderCount As Long
    Dim itemCount As Long
    Dim lineCount As Long
    Dim i As Long
    Dim orderLine As String
    Dim itemLine As String
    Dim bgColor As Long
    Dim tbOrder As MSForms.TextBox
    Dim tbItem As MSForms.TextBox

    If mIsRendering Then Exit Sub
    mIsRendering = True
    On Error GoTo CleanExit

    EnsureLongTextLineUi

    Set host = LongTextHostFrame()
    If host Is Nothing Then GoTo CleanExit

    useNestedFrames = (Not fraLongTextOrder Is Nothing And Not fraLongTextItem Is Nothing)

    totalW = host.Width - 2 * PAD
    If totalW < 360 Then totalW = 360
    paneW = (totalW - GAP) / 2
    paneTop = 26

    orderLines = SplitTextToLines(orderLongText)
    itemLines = SplitTextToLines(itemLongText)
    orderCount = SafeArrayLength(orderLines)
    itemCount = SafeArrayLength(itemLines)
    lineCount = IIf(orderCount > itemCount, orderCount, itemCount)
    If lineCount < 1 Then lineCount = 1
    If lineCount > LT_MAX_LINES Then lineCount = LT_MAX_LINES

    For i = 1 To lineCount
        orderLine = ArrayLineValue(orderLines, i)
        itemLine = ArrayLineValue(itemLines, i)

        If useNestedFrames Then
            Set tbOrder = EnsureLongTextLineControl(fraLongTextOrder, mLtOrderLines, i, "ltOrdLine")
            Set tbItem = EnsureLongTextLineControl(fraLongTextItem, mLtItemLines, i, "ltItmLine")

            tbOrder.Left = 4
            tbOrder.Top = 2 + (i - 1) * LT_LINE_H
            tbOrder.Width = fraLongTextOrder.Width - 18
            If tbOrder.Width < 40 Then tbOrder.Width = 40
            tbOrder.Height = LT_LINE_H - 2
            tbOrder.text = orderLine
            tbOrder.Visible = True

            tbItem.Left = 4
            tbItem.Top = 2 + (i - 1) * LT_LINE_H
            tbItem.Width = fraLongTextItem.Width - 18
            If tbItem.Width < 40 Then tbItem.Width = 40
            tbItem.Height = LT_LINE_H - 2
            tbItem.text = itemLine
            tbItem.Visible = True
        Else
            Set tbOrder = EnsureLongTextLineControl(host, mLtOrderLines, i, "ltOrdLine")
            Set tbItem = EnsureLongTextLineControl(host, mLtItemLines, i, "ltItmLine")

            tbOrder.Left = PAD
            tbOrder.Top = paneTop + 2 + (i - 1) * LT_LINE_H
            tbOrder.Width = paneW - 8
            If tbOrder.Width < 40 Then tbOrder.Width = 40
            tbOrder.Height = LT_LINE_H - 2
            tbOrder.text = orderLine
            tbOrder.Visible = True

            tbItem.Left = PAD + paneW + GAP
            tbItem.Top = paneTop + 2 + (i - 1) * LT_LINE_H
            tbItem.Width = paneW - 8
            If tbItem.Width < 40 Then tbItem.Width = 40
            tbItem.Height = LT_LINE_H - 2
            tbItem.text = itemLine
            tbItem.Visible = True
        End If

        If Len(NormalizeCompareValue(orderLine)) = 0 And Len(NormalizeCompareValue(itemLine)) = 0 Then
            bgColor = modOverlayUI.UI_INPUT_BG
        ElseIf NormalizeCompareValue(orderLine) = NormalizeCompareValue(itemLine) Then
            bgColor = RGB(226, 239, 218)
        Else
            bgColor = RGB(255, 199, 206)
        End If

        tbOrder.BackColor = bgColor
        tbItem.BackColor = bgColor
    Next i

    HideLongTextFromIndex mLtOrderLines, lineCount + 1
    HideLongTextFromIndex mLtItemLines, lineCount + 1

    If useNestedFrames Then
        fraLongTextOrder.ScrollHeight = 8 + lineCount * LT_LINE_H
        fraLongTextItem.ScrollHeight = 8 + lineCount * LT_LINE_H
    Else
        host.ScrollHeight = paneTop + 8 + lineCount * LT_LINE_H
    End If

CleanExit:
    mIsRendering = False
End Sub

Private Sub HideLongTextFromIndex(ByVal lines As Collection, ByVal startIdx As Long)
    On Error Resume Next
    If lines Is Nothing Then Exit Sub

    Dim i As Long
    For i = startIdx To lines.Count
        lines(i).Visible = False
        lines(i).text = vbNullString
    Next i
    On Error GoTo 0
End Sub

Private Function SplitTextToLines(ByVal txt As String) As Variant
    Dim normalized As String
    normalized = Replace$(txt, vbCrLf, vbLf)
    normalized = Replace$(normalized, vbCr, vbLf)

    If Len(normalized) = 0 Then
        SplitTextToLines = Array()
    Else
        SplitTextToLines = Split(normalized, vbLf)
    End If
End Function

Private Function SafeArrayLength(ByVal arr As Variant) As Long
    On Error GoTo Fail
    SafeArrayLength = UBound(arr) - LBound(arr) + 1
    Exit Function
Fail:
    SafeArrayLength = 0
End Function

Private Function ArrayLineValue(ByVal arr As Variant, ByVal oneBasedIndex As Long) As String
    Dim idx As Long
    If oneBasedIndex <= 0 Then Exit Function
    If SafeArrayLength(arr) = 0 Then Exit Function

    idx = LBound(arr) + oneBasedIndex - 1
    If idx > UBound(arr) Then Exit Function
    ArrayLineValue = CStr(arr(idx))
End Function

Private Sub ResolveOrderTaskContext(ByVal orderNo As String, ByRef maintenanceItem As String, ByRef taskKey As String, ByRef orderRow As Long, ByRef itemRow As Long)
    Dim wsOrder As Worksheet
    Dim wsItem As Worksheet

    maintenanceItem = vbNullString
    taskKey = vbNullString
    orderRow = 0
    itemRow = 0

    Set wsOrder = SheetByName(WS_RAW_ORDRE_HEADER)
    Set wsItem = SheetByName(WS_ITEM_EXTRACT)
    If wsOrder Is Nothing Then Exit Sub

    orderRow = FindFirstRowByAnyKey(wsOrder, Array("Order_number", "Aufnr", "AUFNR"), orderNo)
    If orderRow = 0 Then Exit Sub

    maintenanceItem = GetRowValueAny(wsOrder, orderRow, Array("Maintenance_item", "IW33_WAPOS"))
    If wsItem Is Nothing Then Exit Sub
    If Len(CleanKey(maintenanceItem)) = 0 Then Exit Sub

    itemRow = FindFirstRowByAnyKey(wsItem, Array("Maintenance_item", "Source_Item_Number", "RMIPM-WAPOS"), maintenanceItem)
    If itemRow = 0 Then Exit Sub

    taskKey = BuildTaskKey( _
        GetRowValueAny(wsItem, itemRow, Array("Task_LstGrp", "RMIPM-PLNNR")), _
        GetRowValueAny(wsItem, itemRow, Array("GrpCr", "RMIPM-PLNAL")) _
    )
End Sub

Private Function BuildTaskKey(ByVal plnnr As String, ByVal plnal As String) As String
    plnnr = Trim$(plnnr)
    plnal = Trim$(plnal)
    If Len(plnnr) = 0 Or Len(plnal) = 0 Then Exit Function
    BuildTaskKey = plnnr & "/" & plnal
End Function

Private Sub ResolveOrderItemLongText(ByVal orderNo As String, ByRef maintenanceItem As String, ByRef orderLongText As String, ByRef itemLongText As String)
    Dim wsOrder As Worksheet
    Dim wsItem As Worksheet
    Dim orderRow As Long
    Dim itemRow As Long
    Dim taskKey As String
    Dim wsHdr As Worksheet
    Dim hdrRow As Long

    orderLongText = vbNullString
    itemLongText = vbNullString

    ResolveOrderTaskContext orderNo, maintenanceItem, taskKey, orderRow, itemRow

    Set wsOrder = SheetByName(WS_RAW_ORDRE_HEADER)
    Set wsItem = SheetByName(WS_ITEM_EXTRACT)

    If Not wsOrder Is Nothing And orderRow > 0 Then
        orderLongText = GetRowValueAny(wsOrder, orderRow, Array("Long_Text", "Header_LongText", "LongText", "Longtext"))
    End If

    If Not wsItem Is Nothing And itemRow > 0 Then
        itemLongText = GetRowValueAny(wsItem, itemRow, Array("Long_Text", "Item_LongText", "LongText", "Longtext"))
    End If

    If Len(orderLongText) = 0 Then
        Set wsHdr = SheetByName(SH_HDR)
        If Not wsHdr Is Nothing Then
            hdrRow = FindFirstRowByKey(wsHdr, F_AUFNR, orderNo)
            If hdrRow > 0 Then orderLongText = GetRowValue(wsHdr, hdrRow, F_LONGTEXT)
        End If
    End If

    txtLongText.text = orderLongText
End Sub

Private Sub LoadHeaderObjectCompare(ByVal orderNo As String)
    Dim maintenanceItem As String
    Dim taskKey As String
    Dim orderRow As Long
    Dim itemRow As Long
    Dim orderObjects As Variant
    Dim itemObjects As Variant
    ResolveOrderTaskContext orderNo, maintenanceItem, taskKey, orderRow, itemRow
    SetHeaderOrderItemCaptions orderNo, maintenanceItem

    orderObjects = BuildTwoColFilteredArray( _
        SheetByName(WS_RAW_ORDRE_OBJECTS), _
        Array("Order_number", "Aufnr", "AUFNR"), _
        orderNo, _
        Array("Functional_loc", "Tplnr", "Functional_Loc"), _
        Array("Equipment", "Equnr") _
    )

    itemObjects = BuildTwoColFilteredArray( _
        SheetByName(WS_RAW_ITEM_OBJECTS), _
        Array("Maintenance_item", "Source_Item_Number", "RMIPM-WAPOS"), _
        maintenanceItem, _
        Array("Functional_Loc", "Functional_loc", "Tplnr"), _
        Array("Equipment", "Equnr") _
    )

    BindHeaderObjectColumnList lstObjOrder, orderObjects, 1
    BindHeaderObjectColumnList lstObjOrderEq, orderObjects, 2
    BindHeaderObjectColumnList lstObjItem, itemObjects, 1
    BindHeaderObjectColumnList lstObjItemEq, itemObjects, 2
End Sub

Private Sub LoadComponentsCompareRows(ByVal orderNo As String)
    Dim maintenanceItem As String
    Dim taskKey As String
    Dim orderRow As Long
    Dim itemRow As Long
    Dim rows As Variant

    ResolveOrderTaskContext orderNo, maintenanceItem, taskKey, orderRow, itemRow
    SetHeaderOrderItemCaptions orderNo, maintenanceItem

    rows = BuildComponentTripletRows(orderNo, taskKey)

    If mCompareMode Then
        RenderCompareTripletTab CMP_KEY_COMP, "Order " & orderNo, CompareItemCaption(maintenanceItem), rows
    Else
        ToggleCompareTripletTabView CMP_KEY_COMP, False
        BindTripletList lstObjects, COMP_TOP, rows
    End If
End Sub

Private Sub LoadAttachmentsCompareRows(ByVal orderNo As String)
    Dim maintenanceItem As String
    Dim taskKey As String
    Dim orderRow As Long
    Dim itemRow As Long
    Dim rows As Variant

    ResolveOrderTaskContext orderNo, maintenanceItem, taskKey, orderRow, itemRow
    SetHeaderOrderItemCaptions orderNo, maintenanceItem

    rows = BuildAttachmentTripletRows(orderNo, taskKey)

    If mCompareMode Then
        RenderCompareTripletTab CMP_KEY_ATT, "Order " & orderNo, CompareItemCaption(maintenanceItem), rows
    Else
        ToggleCompareTripletTabView CMP_KEY_ATT, False
        BindTripletList lstAttachments, mdlOverlayView.ADD_TOP, rows
    End If
End Sub

Private Sub BindTripletList(ByVal lb As MSForms.ListBox, ByVal topLeftCell As String, ByVal dataArr As Variant)
    Dim headers(1 To 3) As String
    Dim totalW As Single
    Dim fieldW As Single
    Dim valueW As Single

    If lb Is Nothing Then Exit Sub

    headers(1) = "Field"
    headers(2) = "Order"
    headers(3) = "Item"

    mdlOverlayView.BindListBox lb, headers, dataArr, topLeftCell

    totalW = lb.Width - 12
    If totalW < 360 Then totalW = 360
    fieldW = totalW * 0.44
    valueW = (totalW - fieldW) / 2
    lb.ColumnCount = 3
    lb.ColumnWidths = CStr(fieldW) & ";" & CStr(valueW) & ";" & CStr(valueW)
End Sub

Private Function BuildOperationTripletRows(ByVal orderNo As String, ByVal taskKey As String) As Variant
    Dim wsOrder As Worksheet
    Dim wsTask As Worksheet
    Dim mapOrder As Object
    Dim mapTask As Object
    Dim keys As Object
    Dim rows As Collection
    Dim k As Variant
    Dim orderRow As Long
    Dim taskRow As Long
    Dim opNo As String
    Dim cOSteus As Long, cTSteus As Long
    Dim cOArbpl As Long, cTArbpl As Long
    Dim cOLtxa As Long, cTLtxa As Long
    Dim cOArbei As Long, cTArbei As Long
    Dim cOLong As Long, cTLong As Long
    Dim cOSup As Long, cTSup As Long

    Set wsOrder = SheetByName(WS_RAW_ORDRE_OPERATIONS)
    Set wsTask = SheetByName(WS_TASKLIST_EXTRACT)
    Set mapOrder = BuildOperationRowMap(wsOrder, Array("Order_number", "Aufnr", "AUFNR"), orderNo, Array("Act", "Vornr", "VORNR", "Operation"))
    Set mapTask = BuildOperationRowMap(wsTask, Array("Task_LstGrp/GrpCr", "Source_Item_Number"), taskKey, Array("Act", "PLPOD-VORNR", "VORNR", "Operation"))
    Set keys = UnionKeysLocal(mapOrder, mapTask)
    Set rows = New Collection

    cOSteus = FindHeaderIndexAny(wsOrder, Array("Ctrl", "Steus", "STEUS", "ControlKey", "Control_key"))
    cTSteus = FindHeaderIndexAny(wsTask, Array("Ctrl", "PLPOD-STEUS", "STEUS", "ControlKey", "Control_key"))
    cOArbpl = FindHeaderIndexAny(wsOrder, Array("Work_Ctr", "Arbpl", "ARBPL", "WorkCenter", "Work_center"))
    cTArbpl = FindHeaderIndexAny(wsTask, Array("Work_Ctr", "PLPOD-ARBPL", "Arbpl", "ARBPL", "WorkCenter"))
    cOLtxa = FindHeaderIndexAny(wsOrder, Array("Operation_Description", "Ltxa1", "LTXA1", "Description"))
    cTLtxa = FindHeaderIndexAny(wsTask, Array("Operation_Description", "PLPOD-LTXA1", "Ltxa1", "LTXA1", "Description"))
    cOArbei = FindHeaderIndexAny(wsOrder, Array("Work", "Arbei", "ARBEI", "WorkQty"))
    cTArbei = FindHeaderIndexAny(wsTask, Array("Work", "PLPOD-ARBEI", "Arbei", "ARBEI", "WorkQty"))
    cOLong = FindHeaderIndexAny(wsOrder, Array("Operation_Long_Text", "Operation_LongText", "LongText", "Longtext"))
    cTLong = FindHeaderIndexAny(wsTask, Array("Operation_Long_Text", "Operation_LongText", "LongText", "Longtext"))
    cOSup = FindHeaderIndexAny(wsOrder, Array("Supplier", "Lifnr", "LIFNR", "Vendor"))
    cTSup = FindHeaderIndexAny(wsTask, Array("Supplier", "Lifnr", "LIFNR", "Vendor"))

    For Each k In keys.Keys
        orderRow = DictRow(mapOrder, CStr(k))
        taskRow = DictRow(mapTask, CStr(k))
        opNo = CStr(k)

        AddTripletRow rows, opNo & " | STEUS", CellValueOrMissing(wsOrder, orderRow, cOSteus), CellValueOrMissing(wsTask, taskRow, cTSteus)
        AddTripletRow rows, opNo & " | ARBPL", CellValueOrMissing(wsOrder, orderRow, cOArbpl), CellValueOrMissing(wsTask, taskRow, cTArbpl)
        AddTripletRow rows, opNo & " | LTXA1", CellValueOrMissing(wsOrder, orderRow, cOLtxa), CellValueOrMissing(wsTask, taskRow, cTLtxa)
        AddTripletRow rows, opNo & " | ARBEI", CellValueOrMissing(wsOrder, orderRow, cOArbei), CellValueOrMissing(wsTask, taskRow, cTArbei)
        AddTripletRow rows, opNo & " | LONGTEXT", CellValueOrMissing(wsOrder, orderRow, cOLong), CellValueOrMissing(wsTask, taskRow, cTLong)

        If cOSup > 0 Or cTSup > 0 Then
            AddTripletRow rows, opNo & " | LIFNR", CellValueOrMissing(wsOrder, orderRow, cOSup), CellValueOrMissing(wsTask, taskRow, cTSup)
        End If
    Next k

    BuildOperationTripletRows = RowsTo2DArray(rows, 3)
End Function

Private Function BuildComponentTripletRows(ByVal orderNo As String, ByVal taskKey As String) As Variant
    Dim wsOrder As Worksheet
    Dim wsTask As Worksheet
    Dim mapOrder As Object
    Dim mapTask As Object
    Dim keys As Object
    Dim rows As Collection
    Dim k As Variant
    Dim orderRow As Long
    Dim taskRow As Long
    Dim opNo As String
    Dim material As String
    Dim cOQty As Long, cTQty As Long
    Dim cOUn As Long, cTUn As Long
    Dim cODesc As Long, cTDesc As Long

    Set wsOrder = SheetByName(WS_RAW_ORDRE_COMPONENTS)
    Set wsTask = SheetByName(WS_RAW_TASKLIST_COMPONENTS)
    Set mapOrder = BuildDualKeyRowMap(wsOrder, Array("Order_number", "Aufnr", "AUFNR"), orderNo, Array("Act", "Vornr", "Operation"), Array("Material", "MaterialNumber", "IDNRK"))
    Set mapTask = BuildDualKeyRowMap(wsTask, Array("Task_LstGrp/GrpCr", "Source_Item_Number"), taskKey, Array("Act", "VORNR", "Operation"), Array("Material", "MaterialNumber", "IDNRK"))
    Set keys = UnionKeysLocal(mapOrder, mapTask)
    Set rows = New Collection

    cOQty = FindHeaderIndexAny(wsOrder, Array("Quantity", "Menge", "MENGE"))
    cTQty = FindHeaderIndexAny(wsTask, Array("Quantity", "Menge", "MENGE"))
    cOUn = FindHeaderIndexAny(wsOrder, Array("Un", "Unit", "MEINS"))
    cTUn = FindHeaderIndexAny(wsTask, Array("Un", "Unit", "MEINS"))
    cODesc = FindHeaderIndexAny(wsOrder, Array("Component_Description", "Description", "Maktx"))
    cTDesc = FindHeaderIndexAny(wsTask, Array("Component_Description", "Description", "Maktx"))

    For Each k In keys.Keys
        orderRow = DictRow(mapOrder, CStr(k))
        taskRow = DictRow(mapTask, CStr(k))
        opNo = DualKeyOpPart(CStr(k))
        material = DualKeySubPart(CStr(k))

        AddTripletRow rows, opNo & " | " & material & " | Quantity", CellValueOrMissing(wsOrder, orderRow, cOQty), CellValueOrMissing(wsTask, taskRow, cTQty)
        AddTripletRow rows, opNo & " | " & material & " | Unit", CellValueOrMissing(wsOrder, orderRow, cOUn), CellValueOrMissing(wsTask, taskRow, cTUn)
        AddTripletRow rows, opNo & " | " & material & " | Description", CellValueOrMissing(wsOrder, orderRow, cODesc), CellValueOrMissing(wsTask, taskRow, cTDesc)
    Next k

    BuildComponentTripletRows = RowsTo2DArray(rows, 3)
End Function

Private Function BuildAttachmentTripletRows(ByVal orderNo As String, ByVal taskKey As String) As Variant
    Dim wsOrder As Worksheet
    Dim wsTask As Worksheet
    Dim mapOrder As Object
    Dim mapTask As Object
    Dim keys As Object
    Dim rows As Collection
    Dim k As Variant
    Dim orderRow As Long
    Dim taskRow As Long
    Dim opNo As String
    Dim docNo As String
    Dim cODesc As Long, cTDesc As Long
    Dim cOOrig As Long, cTOrig As Long

    Set wsOrder = SheetByName(WS_RAW_ORDRE_ATTACHMENTS)
    Set wsTask = SheetByName(WS_RAW_TASKLIST_ATTACHMENTS)
    Set mapOrder = BuildDualKeyRowMap(wsOrder, Array("Order_number", "Aufnr", "AUFNR"), orderNo, Array("Act", "Vornr", "Operation"), Array("Document", "DocumentNumber", "DOKNR"))
    Set mapTask = BuildDualKeyRowMap(wsTask, Array("Task_LstGrp/GrpCr", "Source_Item_Number"), taskKey, Array("Act", "VORNR", "Operation"), Array("Document", "DocumentNumber", "DOKNR"))
    Set keys = UnionKeysLocal(mapOrder, mapTask)
    Set rows = New Collection

    cODesc = FindHeaderIndexAny(wsOrder, Array("Description", "DKTXT"))
    cTDesc = FindHeaderIndexAny(wsTask, Array("Description", "DKTXT"))
    cOOrig = FindHeaderIndexAny(wsOrder, Array("Original", "Url", "FILEP"))
    cTOrig = FindHeaderIndexAny(wsTask, Array("Original", "Url", "FILEP"))

    For Each k In keys.Keys
        orderRow = DictRow(mapOrder, CStr(k))
        taskRow = DictRow(mapTask, CStr(k))
        opNo = DualKeyOpPart(CStr(k))
        docNo = DualKeySubPart(CStr(k))

        AddTripletRow rows, opNo & " | " & docNo & " | Description", CellValueOrMissing(wsOrder, orderRow, cODesc), CellValueOrMissing(wsTask, taskRow, cTDesc)
        AddTripletRow rows, opNo & " | " & docNo & " | Original", CellValueOrMissing(wsOrder, orderRow, cOOrig), CellValueOrMissing(wsTask, taskRow, cTOrig)
    Next k

    BuildAttachmentTripletRows = RowsTo2DArray(rows, 3)
End Function

Private Function BuildTwoColFilteredArray(ByVal ws As Worksheet, ByVal keyHeaders As Variant, ByVal keyValue As String, ByVal leftHeaders As Variant, ByVal rightHeaders As Variant) As Variant
    Dim cKey As Long
    Dim cLeft As Long
    Dim cRight As Long
    Dim lastRow As Long
    Dim r As Long
    Dim hits As Long
    Dim outArr() As Variant

    If ws Is Nothing Then Exit Function
    If Len(CleanKey(keyValue)) = 0 Then Exit Function

    cKey = FindHeaderIndexAny(ws, keyHeaders)
    cLeft = FindHeaderIndexAny(ws, leftHeaders)
    cRight = FindHeaderIndexAny(ws, rightHeaders)
    If cKey = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, cKey).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cKey).Value2) = CleanKey(keyValue) Then hits = hits + 1
    Next r
    If hits = 0 Then Exit Function

    ReDim outArr(1 To hits, 1 To 2)
    hits = 0

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cKey).Value2) = CleanKey(keyValue) Then
            hits = hits + 1
            If cLeft > 0 Then outArr(hits, 1) = ws.Cells(r, cLeft).Value2
            If cRight > 0 Then outArr(hits, 2) = ws.Cells(r, cRight).Value2
        End If
    Next r

    BuildTwoColFilteredArray = outArr
End Function

Private Function BuildOperationRowMap(ByVal ws As Worksheet, ByVal keyHeaders As Variant, ByVal keyValue As String, ByVal opHeaders As Variant) As Object
    Dim out As Object
    Dim cKey As Long
    Dim cOp As Long
    Dim lastRow As Long
    Dim r As Long
    Dim opKey As String

    Set out = CreateObject("Scripting.Dictionary")
    out.CompareMode = vbTextCompare

    If ws Is Nothing Then
        Set BuildOperationRowMap = out
        Exit Function
    End If

    If Len(CleanKey(keyValue)) = 0 Then
        Set BuildOperationRowMap = out
        Exit Function
    End If

    cKey = FindHeaderIndexAny(ws, keyHeaders)
    cOp = FindHeaderIndexAny(ws, opHeaders)

    If cKey = 0 Or cOp = 0 Then
        Set BuildOperationRowMap = out
        Exit Function
    End If

    lastRow = ws.Cells(ws.rows.Count, cKey).End(xlUp).Row
    If lastRow < 2 Then
        Set BuildOperationRowMap = out
        Exit Function
    End If

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cKey).Value2) = CleanKey(keyValue) Then
            opKey = NormalizeOpToken(ws.Cells(r, cOp).Value2)
            If Len(opKey) > 0 Then
                If Not out.Exists(opKey) Then out.Add opKey, r
            End If
        End If
    Next r

    Set BuildOperationRowMap = out
End Function

Private Function BuildDualKeyRowMap(ByVal ws As Worksheet, ByVal keyHeaders As Variant, ByVal keyValue As String, ByVal opHeaders As Variant, ByVal subHeaders As Variant) As Object
    Dim out As Object
    Dim cKey As Long
    Dim cOp As Long
    Dim cSub As Long
    Dim lastRow As Long
    Dim r As Long
    Dim opKey As String
    Dim subKey As String
    Dim dualKey As String

    Set out = CreateObject("Scripting.Dictionary")
    out.CompareMode = vbTextCompare

    If ws Is Nothing Then
        Set BuildDualKeyRowMap = out
        Exit Function
    End If

    If Len(CleanKey(keyValue)) = 0 Then
        Set BuildDualKeyRowMap = out
        Exit Function
    End If

    cKey = FindHeaderIndexAny(ws, keyHeaders)
    cOp = FindHeaderIndexAny(ws, opHeaders)
    cSub = FindHeaderIndexAny(ws, subHeaders)

    If cKey = 0 Or cSub = 0 Then
        Set BuildDualKeyRowMap = out
        Exit Function
    End If

    lastRow = ws.Cells(ws.rows.Count, cKey).End(xlUp).Row
    If lastRow < 2 Then
        Set BuildDualKeyRowMap = out
        Exit Function
    End If

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cKey).Value2) = CleanKey(keyValue) Then
            opKey = NormalizeOpToken(IIf(cOp > 0, ws.Cells(r, cOp).Value2, vbNullString))
            subKey = UCase$(Trim$(CStr(ws.Cells(r, cSub).Value2)))
            If Len(subKey) > 0 Then
                dualKey = opKey & "|" & subKey
                If Not out.Exists(dualKey) Then out.Add dualKey, r
            End If
        End If
    Next r

    Set BuildDualKeyRowMap = out
End Function

Private Function NormalizeOpToken(ByVal v As Variant) As String
    Dim s As String

    s = Trim$(CStr(v))
    If Len(s) = 0 Then Exit Function

    If IsNumeric(s) Then
        NormalizeOpToken = CStr(CLng(val(s)))
    Else
        NormalizeOpToken = UCase$(s)
    End If
End Function

Private Function UnionKeysLocal(ByVal leftDict As Object, ByVal rightDict As Object) As Object
    Dim out As Object
    Dim k As Variant

    Set out = CreateObject("Scripting.Dictionary")
    out.CompareMode = vbTextCompare

    If Not leftDict Is Nothing Then
        For Each k In leftDict.Keys
            out(k) = True
        Next k
    End If

    If Not rightDict Is Nothing Then
        For Each k In rightDict.Keys
            out(k) = True
        Next k
    End If

    Set UnionKeysLocal = out
End Function

Private Function DictRow(ByVal d As Object, ByVal keyValue As String) As Long
    If d Is Nothing Then Exit Function
    If d.Exists(keyValue) Then DictRow = CLng(d(keyValue))
End Function

Private Function DualKeyOpPart(ByVal keyValue As String) As String
    Dim p As Long
    p = InStr(1, keyValue, "|", vbBinaryCompare)
    If p <= 0 Then
        DualKeyOpPart = keyValue
    Else
        DualKeyOpPart = Left$(keyValue, p - 1)
    End If
End Function

Private Function DualKeySubPart(ByVal keyValue As String) As String
    Dim p As Long
    p = InStr(1, keyValue, "|", vbBinaryCompare)
    If p <= 0 Then Exit Function
    DualKeySubPart = Mid$(keyValue, p + 1)
End Function

Private Sub AddTripletRow(ByVal rows As Collection, ByVal fieldName As String, ByVal orderValue As String, ByVal itemValue As String)
    Dim rowData(0 To 2) As Variant
    rowData(0) = fieldName
    rowData(1) = orderValue
    rowData(2) = itemValue
    rows.Add rowData
End Sub

Private Function RowsTo2DArray(ByVal rows As Collection, ByVal colCount As Long) As Variant
    Dim outArr() As Variant
    Dim i As Long
    Dim c As Long
    Dim rowData As Variant

    If rows Is Nothing Then Exit Function
    If rows.Count = 0 Then Exit Function

    ReDim outArr(1 To rows.Count, 1 To colCount)

    For i = 1 To rows.Count
        rowData = rows(i)
        For c = 0 To UBound(rowData)
            If c + 1 <= colCount Then outArr(i, c + 1) = rowData(c)
        Next c
    Next i

    RowsTo2DArray = outArr
End Function

Private Function CellValueOrMissing(ByVal ws As Worksheet, ByVal rowNo As Long, ByVal colNo As Long) As String
    If rowNo <= 0 Then
        CellValueOrMissing = "(mangler)"
        Exit Function
    End If
    If ws Is Nothing Or colNo <= 0 Then Exit Function
    CellValueOrMissing = CStr(ws.Cells(rowNo, colNo).Value2)
End Function

Private Sub RefreshCompareDecisionState()
    If Not mCompareMode Then Exit Sub

    Dim pending As Long
    pending = CountPendingDecisionsForOrder(mOrder)

    If pending > 0 Then
        lblStatusShort.caption = "Compare mode: " & CStr(pending) & " afventer beslutning"
        lblStatusShort.ForeColor = RGB(192, 0, 0)
    Else
        lblStatusShort.caption = "Compare mode: alle diff er afklaret"
        lblStatusShort.ForeColor = RGB(0, 128, 0)
    End If

    UpdateNavHighlight
    UpdateActionVisibility
End Sub

Private Sub ApplyCompareDecisionsNow()
    On Error GoTo EH

    modCockpit.ApplyCockpitDecisions

    If Len(mOrder) > 0 Then
        LoadDecisions mOrder
        LoadHeaderData mOrder
        ApplyHeaderDiffHighlights mOrder
    End If
    RefreshCompareDecisionState
    Exit Sub

EH:
    MsgBox "Apply fejlede: " & Err.Description, vbExclamation, "Compare"
End Sub

Private Sub PreviewComparePushNow()
    On Error GoTo EH

    modCockpit.PreviewPushReadyDecisions
    RefreshCompareDecisionState
    Exit Sub

EH:
    MsgBox "Preview fejlede: " & Err.Description, vbExclamation, "Compare"
End Sub

Private Sub PushCompareNow()
    On Error GoTo EH

    If CountPendingDecisionsForOrder(mOrder) > 0 Then
        MsgBox "Der er uafklarede diff-linjer. Koer Apply foerst.", vbExclamation, "Compare"
        Exit Sub
    End If

    modCockpit.PushReadyDecisionsToPowerAutomate
    RefreshCompareDecisionState
    Exit Sub

EH:
    MsgBox "Push fejlede: " & Err.Description, vbExclamation, "Compare"
End Sub

Private Function CountRowsByKeyInSheet(ByVal sheetName As String, ByVal keyHeader As String, ByVal keyValue As String) As Long
    Dim ws As Worksheet
    Dim cKey As Long
    Dim lastRow As Long
    Dim r As Long

    Set ws = SheetByName(sheetName)
    If ws Is Nothing Then Exit Function

    cKey = FindHeaderIndex(ws, keyHeader)
    If cKey = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, cKey).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cKey).Value2) = CleanKey(keyValue) Then
            CountRowsByKeyInSheet = CountRowsByKeyInSheet + 1
        End If
    Next r
End Function

Private Function CountPendingDecisionsForOrder(ByVal orderNo As String) As Long
    Dim ws As Worksheet
    Dim cAuf As Long
    Dim cResolved As Long
    Dim lastRow As Long
    Dim r As Long

    Set ws = SheetByName(WS_DATA_DECISION_FACTS)
    If ws Is Nothing Then Exit Function

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cResolved = FindHeaderIndex(ws, "Is_Resolved")
    If cAuf = 0 Or cResolved = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, cAuf).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cAuf).Value2) = CleanKey(orderNo) Then
            If UCase$(Trim$(CStr(ws.Cells(r, cResolved).Value2))) <> "Y" Then
                CountPendingDecisionsForOrder = CountPendingDecisionsForOrder + 1
            End If
        End If
    Next r
End Function

Private Function CountPushReadyRowsForOrder(ByVal orderNo As String) As Long
    Dim ws As Worksheet
    Dim cAuf As Long
    Dim cReady As Long
    Dim cStatus As Long
    Dim lastRow As Long
    Dim r As Long

    Set ws = SheetByName(WS_DATA_DECISION_FACTS)
    If ws Is Nothing Then Exit Function

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cReady = FindHeaderIndex(ws, "Push_Ready")
    cStatus = FindHeaderIndex(ws, "Push_Status")
    If cAuf = 0 Or cReady = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, cAuf).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cAuf).Value2) = CleanKey(orderNo) Then
            If UCase$(Trim$(CStr(ws.Cells(r, cReady).Value2))) = "Y" Then
                If cStatus = 0 Or UCase$(Trim$(CStr(ws.Cells(r, cStatus).Value2))) <> "SENT" Then
                    CountPushReadyRowsForOrder = CountPushReadyRowsForOrder + 1
                End If
            End If
        End If
    Next r
End Function

Private Sub ApplyHeaderDiffHighlights(ByVal orderNo As String)
    ResetHeaderDiffHighlights

    Dim ws As Worksheet
    Dim cAuf As Long
    Dim cScope As Long
    Dim cField As Long
    Dim cResolved As Long
    Dim lastRow As Long
    Dim r As Long
    Dim fieldName As String

    Set ws = SheetByName(WS_DATA_DECISION_FACTS)
    If ws Is Nothing Then Exit Sub

    cAuf = FindHeaderIndex(ws, "AUFNR")
    cScope = FindHeaderIndex(ws, "Scope")
    cField = FindHeaderIndex(ws, "Field")
    cResolved = FindHeaderIndex(ws, "Is_Resolved")
    If cAuf = 0 Or cScope = 0 Or cField = 0 Or cResolved = 0 Then Exit Sub

    lastRow = ws.Cells(ws.rows.Count, cAuf).End(xlUp).Row
    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, cAuf).Value2) = CleanKey(orderNo) Then
            If UCase$(Trim$(CStr(ws.Cells(r, cResolved).Value2))) <> "Y" Then
                If UCase$(Trim$(CStr(ws.Cells(r, cScope).Value2))) = "ITEM" Then
                    fieldName = UCase$(Trim$(CStr(ws.Cells(r, cField).Value2)))
                    Select Case fieldName
                        Case "MAIN_WORKCTR": txtMainWorkCtr.BackColor = RGB(255, 235, 156)
                        Case "FUNCTIONAL_LOC": txtFuncLoc.BackColor = RGB(255, 235, 156)
                        Case "PRIORITY"
                            On Error Resume Next
                            mUI("frames")("HeaderData").Controls("txtPriorityText").BackColor = RGB(255, 235, 156)
                            On Error GoTo 0
                        Case "HEADER_LONGTEXT": txtLongText.BackColor = RGB(255, 235, 156)
                    End Select
                End If
            End If
        End If
    Next r
End Sub

Private Sub ResetHeaderDiffHighlights()
    On Error Resume Next
    txtMainWorkCtr.BackColor = modOverlayUI.UI_INPUT_BG
    txtFuncLoc.BackColor = modOverlayUI.UI_INPUT_BG
    txtLongText.BackColor = modOverlayUI.UI_INPUT_BG
    mUI("frames")("HeaderData").Controls("txtPriorityText").BackColor = modOverlayUI.UI_INPUT_BG
    On Error GoTo 0
End Sub

Private Sub BindEmptyCompareTab(ByVal tabIdx As Long)
    Select Case tabIdx
        Case 0
            ClearHeaderFields
            txtLongText.text = vbNullString
            BindEmptyHeaderCompare
            BindEmptyHeaderObjects
            RenderHeaderCompareLongText vbNullString, vbNullString
        Case 1
            BindEmptyList lstOperations, mdlOverlayView.OP_TOP, PrependLTColumn(modUiFieldMap.GetColumns_Operations())
        Case 2
            BindEmptyList lstObjects, COMP_TOP, ComponentCompareColumns()
        Case 3
            BindEmptyList lstAttachments, mdlOverlayView.ADD_TOP, AttachmentCompareColumns()
        Case 4
            BindEmptyList lstPlanning, DEC_TOP, CompareDecisionColumns()
    End Select
End Sub

Private Function FirstOrderFromCompareQueue() As String
    Dim ws As Worksheet
    Dim cOrder As Long
    Dim lastRow As Long
    Dim r As Long
    Dim v As String

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(WS_COCKPIT_DECISIONS)
    On Error GoTo 0
    If ws Is Nothing Then Exit Function

    cOrder = FindHeaderIndex(ws, "Order_number")
    If cOrder = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, cOrder).End(xlUp).Row
    For r = 2 To lastRow
        v = CleanKey(ws.Cells(r, cOrder).Value2)
        If Len(v) > 0 Then
            FirstOrderFromCompareQueue = v
            Exit Function
        End If
    Next r
End Function

Private Function CompareDecisionColumns() As Variant
    CompareDecisionColumns = MakeColumnsLocal(Array( _
        "Scope", "Scope", _
        "Operation", "VORNR", _
        "Sub key", "Sub_Key", _
        "Field", "Field", _
        "Decision", "Decision", _
        "Manual", "Manual_Value", _
        "Changed by", "Changed_By", _
        "Changed at", "Changed_At", _
        "Comment", "Comment" _
    ))
End Function

Private Function CompareOperationsColumns() As Variant
    CompareOperationsColumns = MakeColumnsLocal(Array( _
        "Operation", "VORNR", _
        "Status", "Compare_Status", _
        "Reasons", "Mismatch_Reasons" _
    ))
End Function

Private Function RawOrderOperationsColumns() As Variant
    RawOrderOperationsColumns = MakeColumnsLocal(Array( _
        "Operation", "Act", _
        "Work center", "Work_center", _
        "Control key", "Control_key", _
        "Short text", "Description", _
        "Work", "Work", _
        "Unit", "Un", _
        "No.", "No", _
        "Personnel no.", "Personnel_no", _
        "Vendor", "Vendor" _
    ))
End Function

Private Function ComponentCompareColumns() As Variant
    ComponentCompareColumns = MakeColumnsLocal(Array( _
        "Field", "Field", _
        "Order", "Order_Value", _
        "Item", "Item_Value" _
    ))
End Function

Private Function AttachmentCompareColumns() As Variant
    AttachmentCompareColumns = MakeColumnsLocal(Array( _
        "Field", "Field", _
        "Order", "Order_Value", _
        "Item", "Item_Value" _
    ))
End Function

Private Function MakeColumnsLocal(ByVal flat As Variant) As Variant
    Dim n As Long
    Dim out() As Variant
    Dim i As Long
    Dim p As Long

    n = (UBound(flat) - LBound(flat) + 1) \ 2
    ReDim out(1 To n, 1 To 2)

    p = LBound(flat)
    For i = 1 To n
        out(i, 1) = CStr(flat(p)): p = p + 1
        out(i, 2) = CStr(flat(p)): p = p + 1
    Next i

    MakeColumnsLocal = out
End Function

Private Sub LoadListFromSheetEx(ByVal lb As MSForms.ListBox, ByVal topLeftCell As String, ByVal sheetName As String, ByVal keyField As String, ByVal keyValue As String, ByVal colSpec As Variant, ByVal opsMode As Boolean)
    Dim ws As Worksheet
    Set ws = SheetByName(sheetName)
    If ws Is Nothing Then
        BindEmptyList lb, topLeftCell, colSpec
        Exit Sub
    End If

    Dim headers() As String
    headers = BuildHeadersFromSpec(colSpec)
    lb.Tag = BuildTagMapFromSpec(colSpec)

    Dim outArr As Variant
    outArr = BuildOutArrayFilteredEx(ws, keyField, keyValue, colSpec, opsMode)

    If IsEmpty(outArr) Then
        BindEmptyList lb, topLeftCell, colSpec
        Exit Sub
    End If

    mdlOverlayView.BindListBox lb, headers, outArr, topLeftCell
    ApplyColumnWidthsSafe lb, opsMode
End Sub

Private Function PrependLTColumn(ByVal baseSpec As Variant) As Variant
    Dim n As Long
    n = UBound(baseSpec, 1)
    Dim out() As Variant
    ReDim out(1 To n + 1, 1 To 2)
    out(1, 1) = "LT"
    out(1, 2) = "__LT__"
    Dim i As Long
    For i = 1 To n
        out(i + 1, 1) = baseSpec(i, 1)
        out(i + 1, 2) = baseSpec(i, 2)
    Next i
    PrependLTColumn = out
End Function

Private Function BuildHeadersFromSpec(ByVal colSpec As Variant) As String()
    Dim n As Long, i As Long
    n = UBound(colSpec, 1)
    Dim headers() As String
    ReDim headers(1 To n + 1)
    For i = 1 To n
        headers(i) = CStr(colSpec(i, 1))
    Next i
    headers(n + 1) = "_RowIndex"
    BuildHeadersFromSpec = headers
End Function

Private Function BuildTagMapFromSpec(ByVal colSpec As Variant) As String
    Dim n As Long, i As Long
    n = UBound(colSpec, 1)
    Dim s As String
    For i = 1 To n
        If Len(s) > 0 Then s = s & TAGMAP_PAIR_SEP
        s = s & Replace$(CStr(colSpec(i, 1)), TAGMAP_PAIR_SEP, ",") & TAGMAP_KV_SEP & CStr(colSpec(i, 2))
    Next i
    BuildTagMapFromSpec = s
End Function

Private Function BuildOutArrayFilteredEx(ByVal ws As Worksheet, ByVal keyField As String, ByVal keyValue As String, ByVal colSpec As Variant, ByVal opsMode As Boolean) As Variant
    Dim colKey As Long
    colKey = FindHeaderIndex(ws, keyField)
    If colKey = 0 Then Exit Function

    Dim lastRow As Long
    lastRow = ws.Cells(ws.rows.Count, colKey).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    Dim n As Long
    n = UBound(colSpec, 1)

    Dim fieldCols() As Long
    ReDim fieldCols(1 To n)

    Dim i As Long
    For i = 1 To n
        Dim f As String
        f = CStr(colSpec(i, 2))
        If opsMode And LCase$(f) = "__lt__" Then
            fieldCols(i) = -1
        Else
            fieldCols(i) = FindHeaderIndex(ws, f)
        End If
    Next i

    Dim hits As Long, r As Long
    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, colKey).Value2) = CleanKey(keyValue) Then hits = hits + 1
    Next r
    If hits = 0 Then Exit Function

    Dim outArr() As Variant
    ReDim outArr(1 To hits, 1 To n + 1)

    Dim outR As Long, c As Long
    outR = 0

    Dim colVornr As Long
    If opsMode Then colVornr = FindHeaderIndex(ws, "Vornr")

    For r = 2 To lastRow
        If CleanKey(ws.Cells(r, colKey).Value2) = CleanKey(keyValue) Then
            outR = outR + 1

            Dim vornr As String
            vornr = vbNullString
            If opsMode And colVornr > 0 Then vornr = NormVornr(ws.Cells(r, colVornr).Value2)

            For c = 1 To n
                If opsMode And fieldCols(c) = -1 Then
                    outArr(outR, c) = IIf(HasOpLongText(keyValue, vornr), LT_GLYPH, vbNullString)
                ElseIf fieldCols(c) > 0 Then
                    outArr(outR, c) = ws.Cells(r, fieldCols(c)).Value2
                Else
                    outArr(outR, c) = vbNullString
                End If
            Next c

            outArr(outR, n + 1) = r
        End If
    Next r

    BuildOutArrayFilteredEx = outArr
End Function

Private Sub ApplyColumnWidthsSafe(ByVal lb As MSForms.ListBox, ByVal opsMode As Boolean)
    On Error GoTo CleanFail
    If lb Is Nothing Then Exit Sub
    If lb.ColumnCount <= 1 Then Exit Sub

    Dim cols As Long
    cols = lb.ColumnCount
    Dim visCols As Long
    visCols = cols - 1
    If visCols < 1 Then Exit Sub

    Dim widths() As Single
    ReDim widths(0 To visCols - 1)

    Dim i As Long
    For i = 0 To visCols - 1
        widths(i) = 60
    Next i

    If opsMode Then widths(0) = 26

    Dim maxScan As Long
    maxScan = lb.ListCount - 1
    If maxScan > 500 Then maxScan = 500

    Dim r As Long
    For i = 0 To visCols - 1
        Dim maxW As Single
        maxW = widths(i)

        Dim hdr As String
        hdr = GetListHeaderCaption(lb, i)
        If Len(hdr) > 0 Then maxW = MaxSingle(maxW, MeasureTextWidthPts(hdr, lb.Font.name, lb.Font.Size, lb.Font.Bold) + 10)

        For r = 0 To maxScan
            Dim cell As String
            cell = CStr(lb.List(r, i))
            If opsMode And i = 0 Then
                If cell = LT_GLYPH Then maxW = MaxSingle(maxW, 18)
            Else
                If Len(cell) > 0 Then maxW = MaxSingle(maxW, MeasureTextWidthPts(cell, lb.Font.name, lb.Font.Size, lb.Font.Bold) + 12)
            End If
        Next r

        widths(i) = maxW
    Next i

    Dim totalW As Single
    totalW = 0
    For i = 0 To visCols - 1
        totalW = totalW + widths(i)
    Next i

    Dim lbW As Single
    lbW = lb.Width - 12
    If lbW < 120 Then lbW = 120

    If totalW < lbW Then
        Dim slack As Single
        slack = lbW - totalW

        Dim denom As Long
        denom = visCols
        If opsMode Then denom = visCols - 1
        If denom < 1 Then denom = 1

        Dim addEach As Single
        addEach = slack / denom

        For i = 0 To visCols - 1
            If opsMode And i = 0 Then
            Else
                widths(i) = widths(i) + addEach
            End If
        Next i
    End If

    Dim s As String
    For i = 0 To visCols - 1
        If Len(s) > 0 Then s = s & ";"
        s = s & CStr(widths(i))
    Next i
    s = s & ";0"
    lb.ColumnWidths = s

    Exit Sub

CleanFail:
    On Error Resume Next
End Sub

Private Function MeasureTextWidthPts(ByVal txt As String, ByVal fontName As String, ByVal fontSize As Single, ByVal isBold As Boolean) As Single
    EnsureMeasureLabel
    With mMeasureLbl
        .Font.name = fontName
        .Font.Size = fontSize
        .Font.Bold = isBold
        .caption = txt
        .AutoSize = True
        MeasureTextWidthPts = .Width
        .AutoSize = False
        .caption = vbNullString
    End With
End Function

Private Sub EnsureMeasureLabel()
    On Error Resume Next
    If Not mMeasureLbl Is Nothing Then Exit Sub
    Set mMeasureLbl = Me.Controls.Add("Forms.Label.1", "lblMeasure__", True)
    mMeasureLbl.Visible = False
    mMeasureLbl.Left = 0
    mMeasureLbl.Top = 0
    mMeasureLbl.Width = 10
    mMeasureLbl.Height = 10
    mMeasureLbl.BackStyle = fmBackStyleTransparent
End Sub

Private Function GetListHeaderCaption(ByVal lb As MSForms.ListBox, ByVal colIdx As Long) As String
    On Error GoTo out
    Dim wsOV As Worksheet, bodyRng As Range
    Set bodyRng = mdlOverlayView.RangeFromRowSource(lb.rowSource, wsOV)
    If bodyRng Is Nothing Then GoTo out
    Dim hdr As Range
    Set hdr = mdlOverlayView.HeaderRangeFromBody(bodyRng)
    If hdr Is Nothing Then GoTo out
    GetListHeaderCaption = CStr(hdr.Cells(1, colIdx + 1).Value2)
    Exit Function
out:
    GetListHeaderCaption = vbNullString
End Function

Private Function MaxSingle(ByVal a As Single, ByVal b As Single) As Single
    If b > a Then MaxSingle = b Else MaxSingle = a
End Function

Private Sub BuildOpLongTextMap(ByVal orderNo As String)
    Set mOpLongTextMap = CreateObject("Scripting.Dictionary")
    mOpLongTextMap.CompareMode = vbTextCompare

    Dim ws As Worksheet
    Set ws = SheetByName(SH_OPLT)
    If ws Is Nothing Then Exit Sub

    Dim colAufnr As Long, colVornr As Long, colLT As Long
    colAufnr = FindHeaderIndex(ws, "Aufnr")
    colVornr = FindHeaderIndex(ws, "Vornr")
    colLT = FindHeaderIndex(ws, "Longtext")
    If colLT = 0 Then colLT = FindHeaderIndex(ws, "LongText")

    If colAufnr = 0 Or colVornr = 0 Or colLT = 0 Then Exit Sub

    Dim lastRow As Long
    lastRow = ws.Cells(ws.rows.Count, colAufnr).End(xlUp).Row
    If lastRow < 2 Then Exit Sub

    Dim rr As Long
    For rr = 2 To lastRow
        If CleanKey(ws.Cells(rr, colAufnr).Value2) = CleanKey(orderNo) Then
            Dim vornr As String
            vornr = NormVornr(ws.Cells(rr, colVornr).Value2)
            If Len(vornr) > 0 Then
                Dim lt As String
                lt = Trim$(CStr(ws.Cells(rr, colLT).Value2))
                If Len(lt) > 0 Then
                    Dim k As String
                    k = CleanKey(orderNo) & vbLf & vornr
                    If Not mOpLongTextMap.Exists(k) Then mOpLongTextMap.Add k, lt
                End If
            End If
        End If
    Next rr
End Sub

Private Function HasOpLongText(ByVal orderNo As String, ByVal vornr As String) As Boolean
    On Error Resume Next
    If mOpLongTextMap Is Nothing Then Exit Function
    HasOpLongText = mOpLongTextMap.Exists(CleanKey(orderNo) & vbLf & NormVornr(vornr))
End Function

Private Function GetOpLongText(ByVal orderNo As String, ByVal vornr As String) As String
    On Error Resume Next
    If mOpLongTextMap Is Nothing Then Exit Function
    Dim k As String
    k = CleanKey(orderNo) & vbLf & NormVornr(vornr)
    If mOpLongTextMap.Exists(k) Then GetOpLongText = CStr(mOpLongTextMap(k))
End Function

Private Function NormVornr(ByVal v As Variant) As String
    NormVornr = CStr(CLng(val(Trim$(CStr(v)))))
End Function

Private Sub HandleLtClick(ByVal xPos As Single)
    On Error Resume Next
    If lstOperations Is Nothing Then Exit Sub
    If lstOperations.ListIndex < 0 Then Exit Sub

    Dim w0 As Single
    w0 = GetFirstColumnWidth(lstOperations)
    If w0 <= 0 Then w0 = 26
    If xPos > (w0 + 2) Then Exit Sub

    Dim glyph As String
    glyph = Trim$(CStr(lstOperations.List(lstOperations.ListIndex, 0)))
    If glyph <> LT_GLYPH Then Exit Sub

    Dim vornr As String
    vornr = Trim$(CStr(lstOperations.List(lstOperations.ListIndex, 1)))
    If Len(vornr) = 0 Then Exit Sub

    Dim lt As String
    lt = GetOpLongText(mOrder, vornr)
    If Len(Trim$(lt)) = 0 Then Exit Sub

    Dim f As ufOpLongTextPopup
    Set f = New ufOpLongTextPopup
    f.Init Me, "Operation " & vornr & " long text", lt
    f.Show vbModal
    Unload f
End Sub

Private Function GetFirstColumnWidth(ByVal lb As MSForms.ListBox) As Single
    On Error GoTo out
    Dim s As String
    s = CStr(lb.ColumnWidths)
    If InStr(1, s, ";", vbTextCompare) > 0 Then s = Split(s, ";")(0)
    s = Replace$(s, "pt", vbNullString)
    s = Replace$(s, " ", vbNullString)
    If Len(s) = 0 Then GoTo out
    GetFirstColumnWidth = CSng(val(s))
    Exit Function
out:
    GetFirstColumnWidth = 0
End Function

Private Sub SaveLongText()
    If Len(mOrder) = 0 Then Exit Sub
    Dim ws As Worksheet: Set ws = SheetByName(SH_HDR)
    If ws Is Nothing Then Exit Sub
    Dim r As Long: r = FindFirstRowByKey(ws, F_AUFNR, mOrder)
    If r = 0 Then Exit Sub
    Dim colLT As Long: colLT = FindHeaderIndex(ws, F_LONGTEXT)
    If colLT > 0 Then ws.Cells(r, colLT).Value2 = txtLongText.text
End Sub

Private Sub SaveHeaderEdits()
    If Len(mOrder) = 0 Then Exit Sub
    Dim ws As Worksheet: Set ws = SheetByName(SH_HDR)
    If ws Is Nothing Then Exit Sub
    Dim r As Long: r = FindFirstRowByKey(ws, F_AUFNR, mOrder)
    If r = 0 Then Exit Sub
    WriteIfExists ws, r, F_VAPLZ, txtMainWorkCtr.text
    WriteIfExists ws, r, F_PERSINIT, txtPersonResp.text
    WriteIfExists ws, r, F_GSTRP, txtBasicStart.text
    WriteIfExists ws, r, F_GLTRP, txtBasicFin.text
    WriteIfExists ws, r, F_TPLNR, txtFuncLoc.text
End Sub

Private Sub WriteIfExists(ByVal ws As Worksheet, ByVal r As Long, ByVal headerName As String, ByVal val As String)
    Dim c As Long
    c = FindHeaderIndex(ws, headerName)
    If c > 0 Then ws.Cells(r, c).Value2 = val
End Sub

Private Sub LockHeaderFields(ByVal makeLocked As Boolean)
    On Error Resume Next
    If Not cmbPriority Is Nothing Then cmbPriority.locked = makeLocked
    If Not cmbPlannerGrp Is Nothing Then cmbPlannerGrp.locked = makeLocked
    txtMainWorkCtr.locked = makeLocked
    txtPersonResp.locked = makeLocked
    txtBasicStart.locked = makeLocked
    txtBasicFin.locked = makeLocked
    txtRevision.locked = makeLocked
    txtFuncLoc.locked = makeLocked
    txtNotifNo.locked = makeLocked
    On Error GoTo 0
End Sub

Private Sub SafeLoad(ByVal startState As Boolean)
    On Error Resume Next
    If startState Then
        Application.StatusBar = "Loading..."
        Application.Cursor = xlWait
        Application.EnableEvents = False
        Application.ScreenUpdating = False
        mPrevCalc = Application.Calculation
        Application.Calculation = xlCalculationManual
    Else
        Application.StatusBar = False
        Application.Cursor = xlDefault
        Application.ScreenUpdating = True
        Application.EnableEvents = True
        Application.Calculation = mPrevCalc
        LockHeaderFields True
        txtLongText.locked = True
        mLongTextEdit = False
        cmdEditLongText.caption = "Edit"
        mHeaderEdit = False
        cmdEditHeader.caption = "Edit"
    End If
End Sub

Private Sub ClearHeaderFields()
    On Error Resume Next
    txtMainWorkCtr.text = vbNullString
    txtPersonResp.text = vbNullString
    txtBasicStart.text = vbNullString
    txtBasicFin.text = vbNullString
    txtOrderType.text = vbNullString
    txtMaintPlant.text = vbNullString
    txtRevision.text = vbNullString
    txtFuncLoc.text = vbNullString
    txtEquipment.text = vbNullString
    txtNotifNo.text = vbNullString
    txtLongText.text = vbNullString

    Dim host As Object
    Set host = mUI("frames")("HeaderData")
    If Not host Is Nothing Then
        host.Controls("txtPriorityText").text = vbNullString
        host.Controls("txtPlannerGrpText").text = vbNullString
    End If
    On Error GoTo 0
End Sub

Private Sub ClearAllLists()
    lstOperations.rowSource = vbNullString: lstOperations.Clear
    lstPermits.rowSource = vbNullString: lstPermits.Clear
    lstObjects.rowSource = vbNullString: lstObjects.Clear
    lstAttachments.rowSource = vbNullString: lstAttachments.Clear
    lstPlanning.rowSource = vbNullString: lstPlanning.Clear
    If Not lstObjOrder Is Nothing Then
        lstObjOrder.rowSource = vbNullString
        lstObjOrder.Clear
    End If
    If Not lstObjOrderEq Is Nothing Then
        lstObjOrderEq.rowSource = vbNullString
        lstObjOrderEq.Clear
    End If
    If Not lstObjItem Is Nothing Then
        lstObjItem.rowSource = vbNullString
        lstObjItem.Clear
    End If
    If Not lstObjItemEq Is Nothing Then
        lstObjItemEq.rowSource = vbNullString
        lstObjItemEq.Clear
    End If
    ClearLongTextLinePanels
End Sub

Private Sub BindEmptyAll()
    If mCompareMode Then
        RenderCompareTripletTab CMP_KEY_OP, "Order", "Item", Empty
        RenderCompareTripletTab CMP_KEY_COMP, "Order", "Item", Empty
        RenderCompareTripletTab CMP_KEY_ATT, "Order", "Item", Empty
    Else
        ToggleCompareTripletTabView CMP_KEY_OP, False
        ToggleCompareTripletTabView CMP_KEY_COMP, False
        ToggleCompareTripletTabView CMP_KEY_ATT, False
        BindEmptyList lstOperations, mdlOverlayView.OP_TOP, PrependLTColumn(modUiFieldMap.GetColumns_Operations())
        BindEmptyList lstObjects, COMP_TOP, ComponentCompareColumns()
        BindEmptyList lstAttachments, mdlOverlayView.ADD_TOP, AttachmentCompareColumns()
    End If

    BindEmptyList lstPlanning, DEC_TOP, CompareDecisionColumns()
    BindEmptyHeaderObjects
    RenderHeaderCompareLongText vbNullString, vbNullString
End Sub

Private Sub BindEmptyHeaderObjects()
    BindHeaderObjectColumnList lstObjOrder, Empty, 1
    BindHeaderObjectColumnList lstObjOrderEq, Empty, 2
    BindHeaderObjectColumnList lstObjItem, Empty, 1
    BindHeaderObjectColumnList lstObjItemEq, Empty, 2
End Sub

Private Sub BindHeaderObjectColumnList(ByVal lb As MSForms.ListBox, ByRef dataArr As Variant, ByVal valueCol As Long)
    Dim colArr As Variant

    If lb Is Nothing Then Exit Sub

    On Error Resume Next
    lb.rowSource = vbNullString
    lb.Clear
    lb.ColumnCount = 1
    lb.ColumnHeads = False
    If Not IsEmpty(dataArr) Then
        colArr = BuildSingleColumnArray(dataArr, valueCol)
        If Not IsEmpty(colArr) Then lb.List = colArr
    End If
    On Error GoTo 0
End Sub

Private Function BuildSingleColumnArray(ByRef srcArr As Variant, ByVal valueCol As Long) As Variant
    Dim rMax As Long
    Dim r As Long
    Dim outArr() As Variant

    On Error GoTo EH
    rMax = UBound(srcArr, 1)
    If rMax < 1 Then Exit Function
    If valueCol < 1 Then Exit Function

    ReDim outArr(1 To rMax, 1 To 1)
    For r = 1 To rMax
        outArr(r, 1) = srcArr(r, valueCol)
    Next r

    BuildSingleColumnArray = outArr
    Exit Function
EH:
End Function

Private Sub BindEmptyList(ByVal lb As MSForms.ListBox, ByVal topLeftCell As String, ByVal colSpec As Variant)
    Dim headers() As String
    headers = BuildHeadersFromSpec(colSpec)
    lb.Tag = BuildTagMapFromSpec(colSpec)
    mdlOverlayView.BindListBox lb, headers, Empty, topLeftCell
    ApplyColumnWidthsSafe lb, (lb Is lstOperations)
End Sub

Private Function ListHasRealData(ByVal lb As MSForms.ListBox) As Boolean
    Dim r As Long
    Dim c As Long
    Dim maxCol As Long

    If lb Is Nothing Then Exit Function
    If lb.ListCount <= 0 Then Exit Function

    maxCol = lb.ColumnCount - 1
    If maxCol < 0 Then maxCol = 0

    For r = 0 To lb.ListCount - 1
        For c = 0 To maxCol
            If Len(Trim$(CStr(lb.List(r, c)))) > 0 Then
                ListHasRealData = True
                Exit Function
            End If
        Next c
    Next r
End Function

Private Function LongTextHostFrame() As MSForms.Frame
    On Error Resume Next
    Set LongTextHostFrame = mUI("frames")("LongText")
    On Error GoTo 0
End Function

Private Function SheetByName(ByVal nm As String) As Worksheet
    On Error Resume Next
    Set SheetByName = ThisWorkbook.Worksheets(nm)
    On Error GoTo 0
End Function

Private Function FindHeaderIndex(ByVal ws As Worksheet, ByVal headerName As String, Optional ByVal headerRow As Long = 1) As Long
    Dim lastCol As Long, c As Long
    If ws Is Nothing Then Exit Function
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(headerRow, c).Value2)), headerName, vbTextCompare) = 0 Then
            FindHeaderIndex = c
            Exit Function
        End If
    Next c
End Function

Private Function FindFirstRowByKey(ByVal ws As Worksheet, ByVal keyHeader As String, ByVal keyValue As String, Optional ByVal headerRow As Long = 1) As Long
    Dim colKey As Long
    colKey = FindHeaderIndex(ws, keyHeader, headerRow)
    If colKey = 0 Then Exit Function
    Dim lastRow As Long, r As Long
    lastRow = ws.Cells(ws.rows.Count, colKey).End(xlUp).Row
    For r = headerRow + 1 To lastRow
        If CleanKey(ws.Cells(r, colKey).Value2) = CleanKey(keyValue) Then
            FindFirstRowByKey = r
            Exit Function
        End If
    Next r
End Function

Private Function FindFirstRowByAnyKey(ByVal ws As Worksheet, ByVal keyHeaders As Variant, ByVal keyValue As String, Optional ByVal headerRow As Long = 1) As Long
    Dim colKey As Long
    Dim lastRow As Long
    Dim r As Long

    colKey = FindHeaderIndexAny(ws, keyHeaders, headerRow)
    If colKey = 0 Then Exit Function

    lastRow = ws.Cells(ws.rows.Count, colKey).End(xlUp).Row
    For r = headerRow + 1 To lastRow
        If CleanKey(ws.Cells(r, colKey).Value2) = CleanKey(keyValue) Then
            FindFirstRowByAnyKey = r
            Exit Function
        End If
    Next r
End Function

Private Function FindHeaderIndexAny(ByVal ws As Worksheet, ByVal headerNames As Variant, Optional ByVal headerRow As Long = 1) As Long
    Dim i As Long

    If ws Is Nothing Then Exit Function

    For i = LBound(headerNames) To UBound(headerNames)
        FindHeaderIndexAny = FindHeaderIndex(ws, CStr(headerNames(i)), headerRow)
        If FindHeaderIndexAny > 0 Then Exit Function
    Next i
End Function

Private Function GetRowValue(ByVal ws As Worksheet, ByVal rowIdx As Long, ByVal headerName As String, Optional ByVal headerRow As Long = 1) As String
    Dim colIdx As Long
    colIdx = FindHeaderIndex(ws, headerName, headerRow)
    If colIdx > 0 And rowIdx > 0 Then GetRowValue = CStr(ws.Cells(rowIdx, colIdx).Value2)
End Function

Private Function GetRowValueAny(ByVal ws As Worksheet, ByVal rowIdx As Long, ByVal headerNames As Variant, Optional ByVal headerRow As Long = 1) As String
    Dim colIdx As Long

    If ws Is Nothing Then Exit Function
    If rowIdx <= 0 Then Exit Function

    colIdx = FindHeaderIndexAny(ws, headerNames, headerRow)
    If colIdx > 0 Then GetRowValueAny = CStr(ws.Cells(rowIdx, colIdx).Value2)
End Function

Private Function CleanKey(ByVal v As Variant) As String
    CleanKey = Replace(Trim$(CStr(v)), " ", "")
End Function

Private Function ObjectNumberFromHeader(ByVal orderNo As String) As String
    Dim ws As Worksheet: Set ws = SheetByName(SH_HDR)
    If ws Is Nothing Then Exit Function
    Dim r As Long: r = FindFirstRowByKey(ws, F_AUFNR, orderNo)
    If r = 0 Then Exit Function
    ObjectNumberFromHeader = GetRowValue(ws, r, F_OBJNR)
End Function

Private Function FirstValueFromSheet(ByVal keyValue As String, ByVal sheetName As String, ByVal keyHeader As String, ByVal valueHeader As String) As String
    Dim ws As Worksheet: Set ws = SheetByName(sheetName)
    If ws Is Nothing Then Exit Function
    Dim r As Long: r = FindFirstRowByKey(ws, keyHeader, keyValue)
    If r = 0 Then Exit Function
    FirstValueFromSheet = GetRowValue(ws, r, valueHeader)
End Function

Private Function FormatSerialDate(ByVal v As Variant) As String
    Dim s As String
    s = Trim$(CStr(v))
    If Len(s) = 0 Then Exit Function
    Dim d As Double
    If TryParseSerial(s, d) Then
        If d > 20000# And d < 90000# Then
            Dim dt As Date
            dt = DateSerial(1899, 12, 30) + d
            FormatSerialDate = Format$(dt, "yyyy-mm-dd HH:nn")
            Exit Function
        End If
    End If
    If IsDate(s) Then
        FormatSerialDate = Format$(CDate(s), "yyyy-mm-dd HH:nn")
    Else
        FormatSerialDate = s
    End If
End Function

Private Function TryParseSerial(ByVal s As String, ByRef outD As Double) As Boolean
    On Error GoTo Fail
    s = Replace$(s, " ", vbNullString)
    If InStr(1, s, ".", vbTextCompare) > 0 And InStr(1, s, ",", vbTextCompare) > 0 Then s = Replace$(s, ".", vbNullString)
    outD = CDbl(s)
    TryParseSerial = True
    Exit Function
Fail:
    TryParseSerial = False
End Function
