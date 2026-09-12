# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_INVALID_FG,
                        C_DIVIDER, C_TRANSPARENT, FONT, SHELL_W)
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, two_col_row, badge, card)
from build_plan_header import section_header

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
OPS_CW = f"({SHELL_W} - 36)"

# ---------------------------------------------------------------------------
# Operationstabellens kolonner.
#
# EEN kilde til bredderne. Tidligere var overskrifts-HTML'en skrevet i haanden
# med andre bredder end kontrollerne i raekken (914 px mod 918 px, og andre
# kolonnebredder), saa overskrifterne stod forskudt i forhold til felterne.
# Nu genereres begge dele herfra.
# ---------------------------------------------------------------------------
OPS_COLS = [
    ("SEL", 30),
    ("OP NO.", 60),
    ("OPERATION SHORT TEXT", 220),
    ("WORK (H)", 64),
    ("DUR. (H)", 64),
    ("MAIN WORK CENTER", 110),
    ("VENDOR", 110),
    ("LONG TEXT", 190),
    ("PAKKER", 110),
]
OPS_GAP = 10
OPS_TABLE_W = sum(w for _, w in OPS_COLS) + OPS_GAP * (len(OPS_COLS) - 1)


def _ops_header_html():
    cols = " ".join(f"{w}px" for _, w in OPS_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in OPS_COLS)
    return (
        f"\"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:{OPS_GAP}px;align-items:center;height:22px;line-height:22px;overflow:hidden;"
        "color:#59667A;font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
        f"{spans}</div>\""
    )


def build_tasklist_section():
    header = section_header("conVhpOpsHead", "Tasklist and Operations",
                            "Bind tasklist til aktivt item og tilfoej operationslinjer.", "Step 3")

    drpTasklist = dropdown(
        "drpVhpItemTasklist", "Filter(colVhpTasklists, Plant = varVhpPlan.Plant)",
        "LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey)",
        item_display="ThisItem.Name", display_mode=DM_ITEM, value_field="Key")
    tasklistCell = field_cell("conVhpCellTasklist", "Tasklist For Active Item", drpTasklist, required=True,
                              width=f"If({OPS_CW} < 640, {OPS_CW}, 360)", container_w=OPS_CW,
                              fill_portions_formula="0")

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
        ), display_mode=DM_ITEM)

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
        ), primary=True, display_mode=DM_ITEM)

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
            "            PackagesKey: \";\",\n"
            "            Selected: false\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Operation line added.\")\n"
            ")"
        ), display_mode=DM_ITEM)

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
        ), danger=True, display_mode=DM_ITEM)

    # Knapperne laa foer paa samme linje som tasklist-dropdownen i en raekke
    # med fast hoejde 62 - dropdownen blev klippet helt vaek. Nu har de hver
    # sin linje, og knapperne deler bredden, saa de aldrig ombryder.
    actionRow = button_row("conVhpOpsActionRow", [btnApply, btnAddLines, btnAddOp, btnRemoveOp], OPS_CW)
    toolbar = group("conVhpOpsToolbar", [tasklistCell, actionRow], direction="Vertical", gap=12)

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
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": _ops_header_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(OPS_TABLE_W),
    }, h=22)
    opsDivider = group("conVhpOpsDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal",
                       width=str(OPS_TABLE_W))

    # -- row template ---------------------------------------------------------
    w = {t: wd for t, wd in OPS_COLS}
    chkSel = Ctrl("chkVhpOpSel", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select operation line\"",
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": "\"\"",
        "OnCheck": "Patch(colVhpOperations, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colVhpOperations, ThisItem, { Selected: false })",
        "Width": str(w["SEL"]),
    }, h=24)
    txtOpNo = text_ctrl("txtVhpOpNo", "ThisItem.OperationNo", size=13, height=32, width=w["OP NO."], wrap="false")
    txtOpShort = text_input("txtVhpOpShortText", "ThisItem.OperationShortText", width=w["OPERATION SHORT TEXT"],
                            height=32,
                            onchange="Patch(colVhpOperations, ThisItem, { OperationShortText: Self.Text })")
    numOpWork = number_input("numVhpOpWork", "ThisItem.WorkHours", width=w["WORK (H)"], height=32)
    numOpWork.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { WorkHours: Self.Value })"
    numOpDur = number_input("numVhpOpDur", "ThisItem.DurationHours", width=w["DUR. (H)"], height=32)
    numOpDur.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { DurationHours: Self.Value })"
    txtOpMwc = text_input("txtVhpOpMwc", "ThisItem.MainWorkCenter", width=w["MAIN WORK CENTER"], height=32,
                          onchange="Patch(colVhpOperations, ThisItem, { MainWorkCenter: Self.Text })")
    txtOpVendor = text_input("txtVhpOpVendor", "ThisItem.Vendor", width=w["VENDOR"], height=32,
                             onchange="Patch(colVhpOperations, ThisItem, { Vendor: Self.Text })")
    txtOpLongText = text_input("txtVhpOpLongText", "ThisItem.LongText", width=w["LONG TEXT"], height=32,
                               onchange="Patch(colVhpOperations, ThisItem, { LongText: Self.Text })")

    # Pakkerne redigeres i matricen nedenfor - her vises kun resultatet, saa
    # operationslinjen og allokeringen kan laeses samme sted.
    txtOpPackages = text_ctrl(
        "txtVhpOpPackages",
        (
            "If(\n"
            "    varVhpPlan.PlanType <> \"Strategy\", \"-\",\n"
            "    With(\n"
            "        { sel: Filter(colVhpStrategyPackages As P, P.StrategyKey = varVhpPlan.Strategy && \";\" & Text(P.PackageNo) & \";\" in Coalesce(ThisItem.PackagesKey, \";\")) },\n"
            "        If(CountRows(sel) = 0, \"(ingen)\", Concat(Sort(sel, PackageNo), ShortCode, \", \"))\n"
            "    )\n"
            ")"
        ),
        size=12, height=32, width=w["PAKKER"], wrap="false",
        color=(
            "If(varVhpPlan.PlanType = \"Strategy\" && Len(Coalesce(ThisItem.PackagesKey, \";\")) <= 1, "
            f"{C_INVALID_FG}, {C_MUTED})"
        ))

    opRow = group("conVhpOpRow", [chkSel, txtOpNo, txtOpShort, numOpWork, numOpDur, txtOpMwc, txtOpVendor,
                                  txtOpLongText, txtOpPackages], direction="Horizontal", gap=OPS_GAP,
                  height="Parent.TemplateHeight - 2", align_items="Center", width="Parent.TemplateWidth")

    OPS_ROW_H = 38 + 2
    gal_h = f"Max(CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)), 1) * {OPS_ROW_H}"
    gallery = Ctrl(
        "galVhpOps", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Tasklist operations for active item\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_CARD_BORDER,
            "FillPortions": "0",
            "Height": gal_h,
            "Items": "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": "38",
            "Width": str(OPS_TABLE_W),
            "WrapCount": "1",
        },
        children=[opRow], h=gal_h)

    opsEmpty = text_ctrl("txtVhpOpsEmpty", "\"No operation lines yet on this item.\"", size=13, color=C_MUTED,
                         height=24, wrap="false",
                         visible="IfError(!IsBlank(varVhpActiveItemId) && CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId)) = 0, false)")

    # Tabellen har fast bredde (summen af kolonnerne). Paa smalle skaerme
    # scroller den vandret i stedet for at klippe kolonner af.
    opsTableWrap = group("conVhpOpsTableWrap", [opsHeader, opsDivider, gallery, opsEmpty],
                         direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width")

    return card("conVhpOpsCard", [header, toolbar, tasklistMeta, opsTableWrap])


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
            "        Text(CountRows(colVhpOperations)) & \" operation line(s) in total.\" &\n"
            "        If(\n"
            "            varVhpPlan.PlanType = \"Strategy\",\n"
            "            \" Strategi \" & varVhpPlan.Strategy & \" med \" &\n"
            "            Text(CountRows(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy))) & \" pakker.\",\n"
            "            \"\"\n"
            "        )\n"
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
        size=12, color=f"If(IsBlank(varVhpLastValidationErrors), {C_VALID_FG}, {C_INVALID_FG})", height=60,
        wrap="true", visible="IfError(varVhpPlanValidated, false)")
    return card("conVhpDispatchCard", [header, statusInline, hintInline, validationReport], gap=10)


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
            "        \"Plan type: \" & If(varVhpPlan.PlanType = \"Strategy\", \"Strategiplan (IP42)\", \"Single cycle (IP41)\") & Char(10) &\n"
            "        If(\n"
            "            varVhpPlan.PlanType = \"Strategy\",\n"
            "            \"Strategi: \" & varVhpPlan.Strategy & Char(10) &\n"
            "            \"Pakker: \" & Concat(Sort(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy), PackageNo), ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit & \")\", \", \") & Char(10),\n"
            "            \"Cycle: \" & Text(varVhpPlan.Cycle) & \" \" & varVhpPlan.Unit & Char(10)\n"
            "        ) &\n"
            "        \"Items: \" & Text(CountRows(colVhpItems)) & \" (\" & Text(CountRows(Filter(colVhpItems, Status = \"valid\"))) & \" valid, \" & Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid)\" & Char(10) &\n"
            "        \"Operations: \" & Text(CountRows(colVhpOperations)) & Char(10) & Char(10) &\n"
            "        Concat(\n"
            "            FirstN(Sort(colVhpItems, ItemId), 15),\n"
            "            \"- \" & If(IsBlank(ShortText), \"Item \" & Text(ItemId), ShortText) & \" | FL \" & Coalesce(FunctionalLocation, \"-\") & \" | \" & Upper(Status),\n"
            "            Char(10)\n"
            "        ) & Char(10) & Char(10) &\n"
            "        If(\n"
            "            varVhpPlan.PlanType = \"Strategy\",\n"
            "            \"Pakkeallokering pr. operation:\" & Char(10) &\n"
            "            Concat(\n"
            "                FirstN(Sort(colVhpOperations, ItemId), 40),\n"
            "                \"  Item \" & Text(ItemId) & \" op \" & OperationNo & \": \" &\n"
            "                With(\n"
            "                    { k: Coalesce(PackagesKey, \";\") },\n"
            "                    If(\n"
            "                        Len(k) <= 1, \"(ingen pakke)\",\n"
            "                        Concat(Sort(Filter(colVhpStrategyPackages As P, P.StrategyKey = varVhpPlan.Strategy && \";\" & Text(P.PackageNo) & \";\" in k), PackageNo), ShortCode, \", \")\n"
            "                    )\n"
            "                ),\n"
            "                Char(10)\n"
            "            ) & Char(10) & Char(10),\n"
            "            \"\"\n"
            "        ) &\n"
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
