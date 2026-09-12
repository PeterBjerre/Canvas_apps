# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE, \
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_INVALID_FG, FONT
from build_helpers import text_ctrl, group, button, text_input, number_input, dropdown, label_row, \
    field_cell, two_col_row, badge
from build_plan_header import section_header

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"

OPS_HEADER_HTML = (
    "\"<div style='display:grid;grid-template-columns:40px 64px 230px 70px 70px 120px 120px 200px;"
    "column-gap:10px;align-items:center;height:22px;line-height:22px;overflow:hidden;color:#59667A;"
    "font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
    "<span>SEL</span><span>OP NO.</span><span>OPERATION SHORT TEXT</span><span>WORK (H)</span>"
    "<span>DUR. (H)</span><span>MAIN WORK CENTER</span><span>VENDOR</span><span>LONG TEXT</span></div>\""
)


def build_tasklist_section():
    header = section_header("conVhpOpsHead", "Tasklist and Operations",
                             "Bind tasklist til aktivt item og tilfoej operationslinjer.", "Step 3-4")

    drpTasklist = dropdown(
        "drpVhpItemTasklist", "Filter(colVhpTasklists, Plant = varVhpPlan.Plant)",
        "LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey)",
        item_display="ThisItem.Name", display_mode=DM_ITEM, width=340, value_field="Key")
    tasklistCell = field_cell("conVhpCellTasklist", "Tasklist For Active Item", drpTasklist, required=True,
                              width="If(App.Width < 720, Parent.Width, 360)", fill_portions_formula="0")

    btnApply = button(
        "btnVhpApplyTasklist", "\"Apply tasklist\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    If(\n"
            "        IsBlank(drpVhpItemTasklist.Selected.Key),\n"
            "        Set(varVhpRuntimeInfo, \"Select a tasklist first.\"),\n"
            "        UpdateIf(\n"
            "            colVhpItems, ItemId = varVhpActiveItemId,\n"
            "            { TasklistKey: drpVhpItemTasklist.Selected.Key, TasklistName: drpVhpItemTasklist.Selected.Name }\n"
            "        );\n"
            "        Set(varVhpRuntimeInfo, \"Tasklist \" & drpVhpItemTasklist.Selected.Key & \" applied to item.\")\n"
            "    )\n"
            ")"
        ), width=118, display_mode=DM_ITEM)

    btnAddLines = button(
        "btnVhpAddTasklistLines", "\"Add lines from tasklist\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        Set(varVhpRuntimeInfo, \"Apply a tasklist first.\"),\n"
            "        Clear(colVhpPickerSelected);\n"
            "        Reset(txtVhpPickerSearch);\n"
            "        Set(varVhpTasklistPickerOpen, true)\n"
            "    )\n"
            ")"
        ), primary=True, width=168, display_mode=DM_ITEM)

    btnAddOp = button(
        "btnVhpAddOperation", "\"Add operation\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    Collect(\n"
            "        colVhpOperations,\n"
            "        {\n"
            "            ItemId: varVhpActiveItemId,\n"
            "            OperationNo: Text(Coalesce(Max(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo)), 0) + 10, \"0000\"),\n"
            "            OperationShortText: \"\",\n"
            "            WorkHours: 1,\n"
            "            DurationHours: 1,\n"
            "            MainWorkCenter: \"\",\n"
            "            Vendor: \"\",\n"
            "            LongText: \"\",\n"
            "            Selected: false\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Operation line added.\")\n"
            ")"
        ), width=120, display_mode=DM_ITEM)

    btnRemoveOp = button(
        "btnVhpRemoveOperation", "\"Remove operation\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    If(\n"
            "        CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId, Selected = true)) = 0,\n"
            "        Set(varVhpRuntimeInfo, \"Select one or more operation lines to remove (Sel column).\"),\n"
            "        RemoveIf(colVhpOperations, ItemId = varVhpActiveItemId, Selected = true);\n"
            "        Set(varVhpRuntimeInfo, \"Removed selected operation line(s).\")\n"
            "    )\n"
            ")"
        ), danger=True, width=140, display_mode=DM_ITEM)

    actionRow = group("conVhpOpsActionRow", [btnApply, btnAddLines, btnAddOp, btnRemoveOp], direction="Horizontal",
                      gap=8, height=36, wrap="true", width="Parent.Width - 360 - 16", align_items="Center")

    toolbar = group("conVhpOpsToolbar", [tasklistCell, actionRow], direction="Horizontal", gap=16, height=62,
                    wrap="true", align_items="End")

    tasklistMeta = text_ctrl(
        "txtVhpTasklistMeta",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId), \"Select an item to manage its tasklist and operations.\",\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        \"No tasklist linked yet.\",\n"
            "        \"Tasklist \" & LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistName & \" linked. \" &\n"
            "        Text(CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))) & \" operation line(s) on this item.\"\n"
            "    )\n"
            ")"
        ), size=12, color=C_MUTED, height=18, wrap="true")

    opsHeader = Ctrl("conVhpOpsHeaderHtml", "HtmlViewer", props={
        "Fill": "RGBA(0, 0, 0, 0)", "Height": "22", "HtmlText": OPS_HEADER_HTML,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0", "Width": "914",
    })
    opsDivider = group("conVhpOpsDivider", [], height=1, fill="RGBA(228, 233, 241, 1)", direction="Horizontal")

    # -- row template ---------------------------------------------------------
    chkSel = Ctrl("chkVhpOpSel", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select operation line\"",
        "Default": "ThisItem.Selected",
        "Height": "24",
        "OnCheck": "Patch(colVhpOperations, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colVhpOperations, ThisItem, { Selected: false })",
        "Width": "30",
    })
    txtOpNo = text_ctrl("txtVhpOpNo", "ThisItem.OperationNo", size=13, height=32, width=60, wrap="false")
    txtOpShort = text_input("txtVhpOpShortText", "ThisItem.OperationShortText", width=220, height=32,
                             onchange="Patch(colVhpOperations, ThisItem, { OperationShortText: Self.Text })")
    numOpWork = number_input("numVhpOpWork", "ThisItem.WorkHours", width=64, height=32)
    numOpWork.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { WorkHours: Self.Value })"
    numOpDur = number_input("numVhpOpDur", "ThisItem.DurationHours", width=64, height=32)
    numOpDur.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { DurationHours: Self.Value })"
    txtOpMwc = text_input("txtVhpOpMwc", "ThisItem.MainWorkCenter", width=110, height=32,
                           onchange="Patch(colVhpOperations, ThisItem, { MainWorkCenter: Self.Text })")
    txtOpVendor = text_input("txtVhpOpVendor", "ThisItem.Vendor", width=110, height=32,
                              onchange="Patch(colVhpOperations, ThisItem, { Vendor: Self.Text })")
    txtOpLongText = text_input("txtVhpOpLongText", "ThisItem.LongText", width=190, height=32,
                                onchange="Patch(colVhpOperations, ThisItem, { LongText: Self.Text })")

    opRow = group("conVhpOpRow", [chkSel, txtOpNo, txtOpShort, numOpWork, numOpDur, txtOpMwc, txtOpVendor,
                                   txtOpLongText], direction="Horizontal", gap=10, height="Parent.TemplateHeight - 2",
                 align_items="Center", width="Parent.TemplateWidth")

    gallery = Ctrl(
        "galVhpOps", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Tasklist operations for active item\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": "RGBA(215, 222, 232, 1)",
            "FillPortions": "0",
            "Height": "IfError(Max(CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)), 1) * 40, 40)",
            "Items": "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": "38",
            "Width": "Parent.Width",
            "WrapCount": "1",
        },
        children=[opRow])

    opsEmpty = text_ctrl("txtVhpOpsEmpty", "\"No operation lines yet on this item.\"", size=13, color=C_MUTED,
                         height=24, wrap="false",
                         visible="IfError(!IsBlank(varVhpActiveItemId) && CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)) = 0, false)")

    opsTableWrap = group("conVhpOpsTableWrap", [opsHeader, opsDivider, gallery, opsEmpty], direction="Vertical",
                        gap=4, height="IfError(22 + 4 + 1 + Max(CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)), 1) * 40 + 4 + 24, 100)",
                        overflow_y="Scroll", width="Parent.Width")

    card = group(
        "conVhpOpsCard", [header, toolbar, tasklistMeta, opsTableWrap], direction="Vertical", gap=14,
        height="IfError(48 + 14 + 62 + 14 + 18 + 14 + (22 + 4 + 1 + Max(CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)), 1) * 40 + 4 + 24), 300)",
        fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(18, 18, 18, 18))
    return card


def build_dispatch_section():
    header = section_header("conVhpDispatchHead", "Dispatch and Control",
                             "Kontrolstatus foer indberetning via mailkladde.", "Step 5")
    statusInline = text_ctrl(
        "txtVhpDispatchStatus",
        (
            "IfError(\n"
            "    If(\n"
            "        !varVhpPlanCommitted, \"Create the plan, then add items and operations.\",\n"
            "        Text(CountRows(colVhpItems)) & \" item(s), \" &\n"
            "        Text(CountRows(Filter(colVhpItems, Status = \"valid\"))) & \" valid, \" &\n"
            "        Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid, \" &\n"
            "        Text(CountRows(colVhpOperations)) & \" operation line(s) in total.\"\n"
            "    ),\n"
            "    \"Create the plan, then add items and operations.\"\n"
            ")"
        ), size=13, color=C_MUTED, height=20, wrap="true")
    hintInline = text_ctrl(
        "txtVhpDispatchHint",
        "\"Tasklist operations are linked to each item and included in the mail draft summary.\"",
        size=12, color=C_MUTED, height=18, wrap="true")
    validationReport = text_ctrl(
        "txtVhpValidationReport",
        "If(IsBlank(varVhpLastValidationErrors), \"No validation issues found.\", varVhpLastValidationErrors)",
        size=12, color=f"If(IsBlank(varVhpLastValidationErrors), {C_VALID_FG}, {C_INVALID_FG})", height=40,
        wrap="true", visible="IfError(varVhpPlanValidated, false)")
    card = group("conVhpDispatchCard", [header, statusInline, hintInline, validationReport], direction="Vertical",
                gap=10, height=48 + 10 + 20 + 10 + 18 + 10 + 40,
                fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(18, 18, 18, 18))
    return card


def build_email_fab():
    btn = button(
        "btnVhpSendEmail", "\"Send as email\"",
        (
            "Launch(\n"
            "    \"mailto:sapvedligehold@orsted.com\" &\n"
            "    \"?subject=\" & EncodeUrl(\"VH-plan \" & varVhpPlan.Plant & \" \" & varVhpPlan.PlanText & \" (\" & Text(Today(), \"dd-mm-yyyy\") & \")\") &\n"
            "    \"&body=\" & EncodeUrl(\n"
            "        \"Hej SAP vedligehold,\" & Char(10) & Char(10) &\n"
            "        \"VH-plan klar til oprettelse i SAP:\" & Char(10) &\n"
            "        \"Plant: \" & varVhpPlan.Plant & Char(10) &\n"
            "        \"Plan text: \" & varVhpPlan.PlanText & Char(10) &\n"
            "        \"Status: \" & varVhpPlan.Status & Char(10) &\n"
            "        \"Cycle: \" & Text(varVhpPlan.Cycle) & \" \" & varVhpPlan.Unit & Char(10) &\n"
            "        \"Items: \" & Text(CountRows(colVhpItems)) & \" (\" & Text(CountRows(Filter(colVhpItems, Status = \"valid\"))) & \" valid, \" & Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid)\" & Char(10) &\n"
            "        \"Operations: \" & Text(CountRows(colVhpOperations)) & Char(10) & Char(10) &\n"
            "        Concat(\n"
            "            FirstN(Sort(colVhpItems, ItemId), 15),\n"
            "            \"- \" & If(IsBlank(ShortText), \"Item \" & Text(ItemId), ShortText) & \" | FL \" & Coalesce(FunctionalLocation, \"-\") & \" | \" & Upper(Status),\n"
            "            Char(10)\n"
            "        ) & Char(10) & Char(10) &\n"
            "        \"Sendt fra VH-plan appen den \" & Text(Now(), \"dd-mm-yyyy hh:mm\")\n"
            "    )\n"
            ");\n"
            "Set(varVhpRuntimeInfo, \"Email draft prepared: \" & Text(CountRows(colVhpItems)) & \" item(s).\")"
        ),
        primary=True, width=190, height=44,
        display_mode="If(varVhpPlanCommitted, DisplayMode.Edit, DisplayMode.Disabled)")
    btn.props["X"] = "App.Width - 210"
    btn.props["Y"] = "App.Height - 70"
    btn.props["RadiusBottomLeft"] = "22"
    btn.props["RadiusBottomRight"] = "22"
    btn.props["RadiusTopLeft"] = "22"
    btn.props["RadiusTopRight"] = "22"
    return btn
