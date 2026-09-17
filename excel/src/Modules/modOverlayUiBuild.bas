Attribute VB_Name = "modOverlayUiBuild"
Option Explicit

Public Const UI_TAB_HEADER As Long = 0
Public Const UI_TAB_OPER As Long = 1
Public Const UI_TAB_COMP As Long = 2
Public Const UI_TAB_ATTACH As Long = 3
Public Const UI_TAB_DECISIONS As Long = 4

Public Function BuildOverlayUI(ByVal frm As Object) As Object
    Dim ui As Object
    Set ui = CreateObject("Scripting.Dictionary")

    On Error Resume Next
    frm.caption = "Change Order"
    frm.Width = 1010
    frm.Height = 700
    frm.StartUpPosition = 0
    frm.BackColor = modOverlayUI.UI_BG
    frm.BorderStyle = fmBorderStyleSingle
    On Error GoTo 0

    Set ui("btnTab0") = AddButton(frm, "btnTab0", "HeaderData", 12, 8, 190, 24)
    Set ui("btnTab1") = AddButton(frm, "btnTab1", "Operations", 208, 8, 190, 24)
    Set ui("btnTab2") = AddButton(frm, "btnTab2", "Components", 404, 8, 190, 24)
    Set ui("btnTab3") = AddButton(frm, "btnTab3", "Attachments", 600, 8, 190, 24)
    Set ui("btnTab4") = AddButton(frm, "btnTab4", "Decisions", 796, 8, 190, 24)
    Set ui("btnTab5") = AddButton(frm, "btnTab5", "", 0, 0, 1, 1)
    ui("btnTab5").Visible = False

    AddLabel frm, "lblOrder", "Order", 12, 42, 45, 16
    Set ui("txtOrder") = AddTextBox(frm, "txtOrder", "", 60, 38, 150, 22)

    Set ui("cmdLoad") = AddButton(frm, "cmdLoad", "Refresh", 220, 38, 70, 24)
    Set ui("cmdClear") = AddButton(frm, "cmdClear", "Clear", 12, 646, 70, 26)
    Set ui("cmdClose") = AddButton(frm, "cmdClose", "Close", 910, 646, 70, 26)

    Set ui("txtLongText") = AddTextBox(frm, "txtLongText", "", 300, 38, 2, 2)
    modOverlayUI.StyleTextBox ui("txtLongText"), True, True, True
    ui("txtLongText").Visible = False
    Set ui("cmdEditLongText") = AddButton(frm, "cmdEditLongText", "Edit", 306, 38, 2, 2)
    ui("cmdEditLongText").Visible = False

    Dim frames As Object
    Set frames = CreateObject("Scripting.Dictionary")
    Set frames("HeaderData") = AddFrame(frm, "fraHeader", 12, 100, 960, 505)
    Set frames("LongText") = AddFrame(frm, "fraLongText", 12, 100, 960, 505)
    Set frames("Operations") = AddFrame(frm, "fraOperations", 12, 100, 960, 505)
    Set frames("Components") = AddFrame(frm, "fraComponents", 12, 100, 960, 505)
    Set frames("Attachments") = AddFrame(frm, "fraAttachments", 12, 100, 960, 505)
    Set frames("Decisions") = AddFrame(frm, "fraDecisions", 12, 100, 960, 505)
    Set ui("frames") = frames

    BuildHeaderPanel frames("HeaderData"), ui

    AddLabel frames("LongText"), "lblLongTextOrder", "Order", 8, 8, 460, 16
    AddLabel frames("LongText"), "lblLongTextItem", "Item", 476, 8, 460, 16
    ' Nested runtime frames can fail in some Excel hosts; longtext line controls are rendered directly in fraLongText.

    Set ui("lstOperations") = AddListBox(frames("Operations"), "lstOperations", 8, 8, 944, 430)
    Set ui("lstPermits") = AddListBox(frames("LongText"), "lstPermits", 8, 8, 944, 430)
    ui("lstPermits").Visible = False
    Set ui("lstObjects") = AddListBox(frames("Components"), "lstObjects", 8, 8, 944, 430)
    Set ui("lstAttachments") = AddListBox(frames("Attachments"), "lstAttachments", 8, 8, 944, 430)
    Set ui("lstPlanning") = AddListBox(frames("Decisions"), "lstPlanning", 8, 8, 944, 430)

    Set ui("cmdEditHeader") = AddButton(frames("HeaderData"), "cmdEditHeader", "Edit", 880, 455, 60, 24)

    Set ui("cmdEditRow") = AddButton(frm, "cmdEditRow", "Edit Row", 12, 610, 90, 26)
    Set ui("cmdAddRow") = AddButton(frm, "cmdAddRow", "Add Row", 110, 610, 90, 26)
    Set ui("cmdDeleteRow") = AddButton(frm, "cmdDeleteRow", "Delete Row", 208, 610, 90, 26)

    modOverlayUI.ApplyPalette frm
    modOverlayUI.ApplyFontUniform frm, 10, False
    modOverlayUI.FixZOrder frm

    HideAllFrames ui
    ShowFrame ui, UI_TAB_HEADER

    Set BuildOverlayUI = ui
End Function

Public Sub HideAllFrames(ByVal ui As Object)
    Dim frames As Object
    Set frames = ui("frames")

    frames("HeaderData").Visible = False
    frames("LongText").Visible = False
    frames("Operations").Visible = False
    frames("Components").Visible = False
    frames("Attachments").Visible = False
    frames("Decisions").Visible = False
End Sub

Public Sub ShowFrame(ByVal ui As Object, ByVal tabIndex As Long)
    HideAllFrames ui

    Dim frames As Object
    Set frames = ui("frames")

    Select Case tabIndex
        Case UI_TAB_HEADER: frames("HeaderData").Visible = True
        Case UI_TAB_OPER: frames("Operations").Visible = True
        Case UI_TAB_COMP: frames("Components").Visible = True
        Case UI_TAB_ATTACH: frames("Attachments").Visible = True
        Case UI_TAB_DECISIONS: frames("Decisions").Visible = True
        Case Else: frames("HeaderData").Visible = True
    End Select

    ui("activeFrame") = tabIndex
End Sub

Private Sub BuildHeaderPanel(ByVal host As Object, ByVal ui As Object)
    On Error Resume Next
    host.caption = vbNullString
    On Error GoTo 0

    AddLabel host, "lblMWC", "Main Work Ctr", 10, 10, 110, 16
    Set ui("txtMainWorkCtr") = AddTextBox(host, "txtMainWorkCtr", "", 10, 28, 110, 20)

    AddLabel host, "lblPriority", "Priority", 140, 10, 110, 16
    Set ui("cmbPriority") = AddCombo(host, "cmbPriority", 140, 28, 110, 20)

    AddLabel host, "lblPlanner", "Planner Group", 270, 10, 120, 16
    Set ui("cmbPlannerGrp") = AddCombo(host, "cmbPlannerGrp", 270, 28, 120, 20)

    AddLabel host, "lblNotif", "Notification", 410, 10, 110, 16
    Set ui("txtNotifNo") = AddTextBox(host, "txtNotifNo", "", 410, 28, 110, 20)

    AddLabel host, "lblPR", "Person Responsible", 540, 10, 140, 16
    Set ui("txtPersonResp") = AddTextBox(host, "txtPersonResp", "", 540, 28, 140, 20)

    AddLabel host, "lblStart", "Basic Start", 10, 60, 110, 16
    Set ui("txtBasicStart") = AddTextBox(host, "txtBasicStart", "", 10, 78, 110, 20)

    AddLabel host, "lblFinish", "Basic Finish", 140, 60, 110, 16
    Set ui("txtBasicFin") = AddTextBox(host, "txtBasicFin", "", 140, 78, 110, 20)

    AddLabel host, "lblOrderType", "Order type", 270, 60, 110, 16
    Set ui("txtOrderType") = AddTextBox(host, "txtOrderType", "", 270, 78, 80, 20)
    ui("txtOrderType").locked = True

    AddLabel host, "lblMaintPlant", "Maint. plant", 370, 60, 110, 16
    Set ui("txtMaintPlant") = AddTextBox(host, "txtMaintPlant", "", 370, 78, 80, 20)
    ui("txtMaintPlant").locked = True

    AddLabel host, "lblFuncLoc", "Functional Location", 10, 110, 160, 16
    Set ui("txtFuncLoc") = AddTextBox(host, "txtFuncLoc", "", 10, 128, 160, 20)

    AddLabel host, "lblEquip", "Equipment", 190, 110, 110, 16
    Set ui("txtEquipment") = AddTextBox(host, "txtEquipment", "", 190, 128, 160, 20)

    AddLabel host, "lblRev", "Revision", 370, 110, 110, 16
    Set ui("txtRevision") = AddTextBox(host, "txtRevision", "", 370, 128, 110, 20)

    AddLabel host, "lblHeaderCompare", "Field / Order / Item", 10, 156, 220, 16
    Set ui("lstHeaderCompare") = AddListBox(host, "lstHeaderCompare", 10, 174, 940, 140)
    ui("lstHeaderCompare").Visible = False

    AddLabel host, "lblObjSection", "Object list", 10, 322, 220, 16
    AddLabel host, "lblObjOrder", "Order", 10, 340, 460, 16
    AddLabel host, "lblObjItem", "Item", 490, 340, 460, 16
    Set ui("lstObjOrder") = AddListBox(host, "lstObjOrder", 10, 358, 460, 102)
    Set ui("lstObjOrderEq") = AddListBox(host, "lstObjOrderEq", 240, 358, 230, 102)
    Set ui("lstObjItem") = AddListBox(host, "lstObjItem", 490, 358, 460, 102)
    Set ui("lstObjItemEq") = AddListBox(host, "lstObjItemEq", 720, 358, 230, 102)
End Sub

Private Function AddFrame(ByVal parent As Object, ByVal nm As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single) As Object
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.Frame.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddFrame", "Kunne ikke oprette/frame: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    c.caption = vbNullString
    c.SpecialEffect = fmSpecialEffectFlat
    On Error GoTo 0
    Set AddFrame = c
End Function

Private Function AddListBox(ByVal parent As Object, ByVal nm As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single) As Object
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.ListBox.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddListBox", "Kunne ikke oprette listbox: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    c.ColumnHeads = True
    c.MultiSelect = fmMultiSelectSingle
    c.IntegralHeight = False
    On Error GoTo 0
    modOverlayUI.StyleListBox c
    Set AddListBox = c
End Function

Private Function AddTextBox(ByVal parent As Object, ByVal nm As String, ByVal txt As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single) As Object
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.TextBox.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddTextBox", "Kunne ikke oprette textbox: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    c.text = txt
    On Error GoTo 0
    modOverlayUI.StyleTextBox c, False, False, False
    Set AddTextBox = c
End Function

Private Function AddCombo(ByVal parent As Object, ByVal nm As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single) As Object
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.ComboBox.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddCombo", "Kunne ikke oprette combo: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    On Error GoTo 0
    c.BackColor = modOverlayUI.UI_INPUT_BG
    c.ForeColor = modOverlayUI.UI_LABEL
    c.Font.name = modOverlayUI.UI_FONT_NAME
    c.Font.Size = 10
    Set AddCombo = c
End Function

Private Function AddButton(ByVal parent As Object, ByVal nm As String, ByVal cap As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single) As Object
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.CommandButton.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddButton", "Kunne ikke oprette button: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    c.caption = cap
    c.SpecialEffect = fmSpecialEffectFlat
    On Error GoTo 0
    modOverlayUI.StyleButton c
    Set AddButton = c
End Function

Private Sub AddLabel(ByVal parent As Object, ByVal nm As String, ByVal cap As String, ByVal l As Single, ByVal t As Single, ByVal w As Single, ByVal h As Single)
    Dim c As Object
    Set c = EnsureControl(parent, "Forms.Label.1", nm)
    If c Is Nothing Then Err.Raise 5, "modOverlayUiBuild.AddLabel", "Kunne ikke oprette label: " & nm
    On Error Resume Next
    c.Left = l
    c.Top = t
    c.Width = w
    c.Height = h
    c.caption = cap
    c.BackStyle = fmBackStyleTransparent
    c.ForeColor = modOverlayUI.UI_LABEL
    c.Font.name = modOverlayUI.UI_FONT_NAME
    c.Font.Size = 10
    c.Font.Bold = False
    On Error GoTo 0
End Sub

Private Function EnsureControl(ByVal parent As Object, ByVal progId As String, ByVal nm As String) As Object
    Dim c As Object

    On Error Resume Next
    Set c = parent.Controls(nm)
    On Error GoTo 0

    If c Is Nothing Then
        On Error Resume Next
        Set c = parent.Controls.Add(progId, nm, True)
        If c Is Nothing Then Set c = parent.Controls.Add(progId, nm)
        On Error GoTo 0
    End If

    Set EnsureControl = c
End Function
