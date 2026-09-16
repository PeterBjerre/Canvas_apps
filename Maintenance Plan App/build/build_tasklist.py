# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_INVALID_FG,
                        C_DIVIDER, C_TRANSPARENT, C_INPUT_BG, FONT, SHELL_W)
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, two_col_row, badge, card)
from build_plan_header import section_header, help_panel
import build_help as bh
from build_strategy import build_strategy_body, IS_STRATEGY

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
    ("PACKAGES", 110),
]
OPS_GAP = 10
OPS_TABLE_W = sum(w for _, w in OPS_COLS) + OPS_GAP * (len(OPS_COLS) - 1)


def _ops_header_html():
    cols = " ".join(f"{w}px" for _, w in OPS_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in OPS_COLS)
    # <style>-blokken nulstiller iframe'ens standard body-margin (den er der,
    # selvom kontrollens egen Padding er sat til 0), og det er den margin,
    # der fik HtmlViewer til at vise en (unoedvendig) scrollbar under
    # overskriften. Selve raekken er 1 px lavere end kontrollens Height, saa
    # afrundingsfejl ikke ogsaa udloeser en scrollbar.
    return (
        "\"<style>html,body{margin:0;padding:0;overflow:hidden}</style>"
        f"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:{OPS_GAP}px;align-items:center;height:21px;line-height:21px;overflow:hidden;"
        "color:#59667A;font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
        f"{spans}</div>\""
    )


# ---------------------------------------------------------------------------
# Faner
# ---------------------------------------------------------------------------
# Operationerne, pakkerne, materialerne og dokumenterne hoerer alle til
# arbejdsplanen. De laa foer som to kort med hver sit trin, og der var ikke
# plads til to mere. Nu er de fire faner i eet kort.
#
# Maintenance packages vises KUN paa en strategiplan - en tidsplan har ingen
# pakker at allokere til. Materials og Attachments vises altid.
TABS = [
    ("ops", "Operations", None),
    ("pkg", "Maintenance packages", IS_STRATEGY),
    ("mat", "Materials", None),
    ("att", "Attachments", None),
]


def _tab_on(key):
    return f'IfError(varVhpOpsTab = "{key}", false)'


def _tab_bar():
    kids = []
    for key, label, cond in TABS:
        on = _tab_on(key)
        b = button(f"btnVhpTab{key.capitalize()}", f'"{label}"',
                   f'Set(varVhpOpsTab, "{key}")', width=168, height=34)
        b.props["Appearance"] = f"If({on}, ButtonAppearance.Primary, ButtonAppearance.Secondary)"
        b.props["BasePaletteColor"] = C_PRIMARY
        b.props["Color"] = f"If({on}, {C_WHITE}, {C_TITLE})"
        b.props["BorderColor"] = C_CARD_BORDER
        b.props["BorderThickness"] = "1"
        b.props["Size"] = "13"
        if cond:
            b.vis = f"IfError({cond}, false)"
        kids.append(b)
    return group("conVhpOpsTabBar", kids, direction="Horizontal", gap=6, height=34,
                 align_items="Center", width="Parent.Width", wrap="true")


# Bliver planen lavet om fra strategi- til tidsplan, mens man staar paa
# pakkefanen, forsvinder baade knappen og ruden - og kortet ville staa tomt.
# Operationsruden overtager derfor den tilstand.
OPS_PANE_ON = (f'IfError({_tab_on("ops")} || '
               f'({_tab_on("pkg")} && !{IS_STRATEGY}), false)')
PKG_PANE_ON = f'IfError({_tab_on("pkg")} && {IS_STRATEGY}, false)'


# ---------------------------------------------------------------------------
# Materialer
# ---------------------------------------------------------------------------
# Description og Unit er tomme i dag. De fyldes ud af et materialeopslag mod
# SAP senere - kolonnerne staar der allerede, saa opslaget kun skal skrive i
# dem og ikke flytte rundt paa tabellen.
MAT_COLS = [("SEL", 30), ("MATERIAL", 110), ("DESCRIPTION", 230), ("QTY", 70),
            ("UNIT", 60), ("OPERATION", 120)]
MAT_GAP = 10
MAT_TABLE_W = sum(w for _, w in MAT_COLS) + MAT_GAP * (len(MAT_COLS) - 1)
MAT_ROW_H = 34
MAT_ACTIVE = "Filter(colVhpMaterials, ItemId = varVhpActiveItemId)"


def _mat_header_html():
    cols = " ".join(f"{w}px" for _, w in MAT_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in MAT_COLS)
    return ("\"<style>html,body{margin:0;padding:0;overflow:hidden}</style>"
            f"<div style='display:grid;grid-template-columns:{cols};"
            f"column-gap:{MAT_GAP}px;align-items:center;height:21px;line-height:21px;"
            "overflow:hidden;color:#59667A;font-family:Segoe UI;font-size:11px;"
            f"font-weight:600;white-space:nowrap;'>{spans}</div>\"")


def _materials_pane():
    w = {t: wd for t, wd in MAT_COLS}

    btnAdd = button(
        "btnVhpAddMaterial", '"Add material"',
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    Collect(\n"
            "        colVhpMaterials,\n"
            "        {\n"
            "            ItemId: varVhpActiveItemId,\n"
            f"            LineId: Coalesce(Max({MAT_ACTIVE}, LineId), 0) + 1,\n"
            "            MaterialNo: \"\",\n"
            "            Description: \"\",\n"
            "            Unit: \"\",\n"
            "            Quantity: 1,\n"
            # Et materiale hoerer til EN operation. En ny linje arver derfor
            # itemets foerste operation i stedet for at staa tom - en
            # materialelinje uden operation har ingen plads i SAP.
            "            OperationNo: Coalesce(\n"
            "                First(Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId),\n"
            "                      Value(OperationNo))).OperationNo,\n"
            "                \"\"\n"
            "            ),\n"
            "            Selected: false\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Material line added.\")\n"
            ")"
        ), primary=True, display_mode=DM_ITEM)

    btnRemove = button(
        "btnVhpRemoveMaterial", '"Remove material"',
        (
            "If(\n"
            f"    CountRows(Filter({MAT_ACTIVE}, Selected = true)) = 0,\n"
            "    Set(varVhpRuntimeInfo, \"Select one or more material lines to remove.\"),\n"
            "    RemoveIf(colVhpMaterials, ItemId = varVhpActiveItemId, Selected = true);\n"
            "    Set(varVhpRuntimeInfo, \"Removed selected material line(s).\")\n"
            ")"
        ), danger=True, display_mode=DM_ITEM)

    actions = button_row("conVhpMatActions", [btnAdd, btnRemove], OPS_CW)

    header = Ctrl("conVhpMatHeaderHtml", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": _mat_header_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(MAT_TABLE_W),
    }, h=22)
    divider = group("conVhpMatDivider", [], height=1, fill=C_DIVIDER,
                    direction="Horizontal", width=str(MAT_TABLE_W))

    chkSel = Ctrl("chkVhpMatSel", "ModernCheckbox", props={
        "AccessibleLabel": '"Select material line"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colVhpMaterials, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colVhpMaterials, ThisItem, { Selected: false })",
        "Width": str(w["SEL"]),
    }, h=24)
    txtNo = text_input("txtVhpMatNo", "ThisItem.MaterialNo", width=w["MATERIAL"], height=30,
                       onchange="Patch(colVhpMaterials, ThisItem, { MaterialNo: Self.Text })")
    # Kommer fra materialeopslaget, ikke fra brugeren.
    txtDesc = text_ctrl("txtVhpMatDesc",
                        'If(IsBlank(ThisItem.Description), "-", ThisItem.Description)',
                        size=12, color=C_MUTED, height=30, width=w["DESCRIPTION"], wrap="false")
    numQty = number_input("numVhpMatQty", "ThisItem.Quantity", width=w["QTY"], height=30)
    numQty.props["OnChange"] = "Patch(colVhpMaterials, ThisItem, { Quantity: Self.Value })"
    txtUnit = text_ctrl("txtVhpMatUnit",
                        'If(IsBlank(ThisItem.Unit), "-", ThisItem.Unit)',
                        size=12, color=C_MUTED, height=30, width=w["UNIT"], wrap="false")
    drpOp = dropdown(
        "drpVhpMatOp",
        "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
        "LookUp(Filter(colVhpOperations, ItemId = varVhpActiveItemId), OperationNo = ThisItem.OperationNo)",
        item_display="ThisItem.OperationNo", value_field="OperationNo",
        width=w["OPERATION"], height=30)
    drpOp.props["OnChange"] = ("Patch(colVhpMaterials, ThisItem, "
                               "{ OperationNo: Self.Selected.OperationNo })")

    row = group("conVhpMatRow", [chkSel, txtNo, txtDesc, numQty, txtUnit, drpOp],
                direction="Horizontal", gap=MAT_GAP, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    gal_h = f"Max(CountRows({MAT_ACTIVE}), 1) * {MAT_ROW_H + 2}"
    gallery = Ctrl("galVhpMaterials", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Materials for active item"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BORDER,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({MAT_ACTIVE}, LineId)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(MAT_ROW_H),
        "Width": str(MAT_TABLE_W),
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtVhpMatEmpty",
                      '"No materials on this item yet. Use Add material to add one."',
                      size=13, color=C_MUTED, height=24, wrap="false",
                      visible=f"IfError(!IsBlank(varVhpActiveItemId) && CountRows({MAT_ACTIVE}) = 0, false)")

    note = text_ctrl("txtVhpMatNote",
                     '"Description and Unit are filled in by the material lookup. '
                     'Until it is in place they stay empty."',
                     size=12, color=C_MUTED, height=18, wrap="true")

    table = group("conVhpMatTableWrap", [header, divider, gallery, empty],
                  direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width")

    return group("conVhpMatPane", [actions, note, table], direction="Vertical", gap=12,
                 width="Parent.Width")


# ---------------------------------------------------------------------------
# Dokumenter
# ---------------------------------------------------------------------------
# Et dokument kan hoere til HELE planen (ingen operation valgt) eller til en
# eller flere operationer. Koblingen ligger i OperationsKey, ";0010;0020;",
# praecis som PackagesKey paa operationslinjen - samme moenster, saa der
# ikke er to maader at gemme et maengdevalg paa i den samme app.
ATT_ROW_H = 34
ATT_CELL_W = 64
ATT_ACTIVE = "Filter(colVhpAttachments, ItemId = varVhpActiveItemId)"
ATT_OPS = "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))"


def _att_ops_cell():
    """Een afkrydsning pr. operation, inde i dokumentets raekke.

    Den INDRE gallery kan ikke laese den YDRE raekkes data - ThisItem er
    skygget. Loesningen er den samme som i pakkematricen: den ydre raekkes
    noegle baeres MED ind i hver indre record, saa afkrydsningen kun ser paa
    sin egen ThisItem. Ingen krydsreference mellem to gallerier."""
    cur = ("Coalesce(LookUp(colVhpAttachments, ItemId = varVhpActiveItemId "
           "&& LineId = ThisItem.LineId).OperationsKey, \";\")")
    return Ctrl("chkVhpAttOp", "ModernCheckbox", props={
        "AccessibleLabel": '"Attach to operation " & ThisItem.OperationNo',
        "AlignInContainer": "AlignInContainer.Center",
        "Default": f'";" & ThisItem.OperationNo & ";" in {cur}',
        "Height": "22",
        "Label": "ThisItem.OperationNo",
        "OnCheck": (
            "With(\n"
            "    { op: ThisItem.OperationNo, lid: ThisItem.LineId },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && LineId = lid,\n"
            "        {\n"
            "            OperationsKey:\n"
            "                If(\n"
            "                    \";\" & op & \";\" in Coalesce(OperationsKey, \";\"),\n"
            "                    Coalesce(OperationsKey, \";\"),\n"
            "                    Coalesce(OperationsKey, \";\") & op & \";\"\n"
            "                )\n"
            "        }\n"
            "    )\n"
            ")"
        ),
        "OnUncheck": (
            "With(\n"
            "    { op: ThisItem.OperationNo, lid: ThisItem.LineId },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && LineId = lid,\n"
            "        { OperationsKey: Substitute(Coalesce(OperationsKey, \";\"), \";\" & op & \";\", \";\") }\n"
            "    )\n"
            ")"
        ),
        "Width": str(ATT_CELL_W),
    }, h=22)


def _attachments_pane():
    # Selve filvalget mangler. Se docs/18-materialer-og-attachments.md:
    # drag and drop fra stifinderen kraever Attachment-kontrollen, og den
    # lever kun i en formular bundet til en liste med vedhaeftninger. Hvilken
    # liste det skal vaere, afhaenger af hvad flowet vil have ind, og det er
    # ikke afklaret endnu. Resten af fanen virker uden.
    dropZone = group(
        "conVhpAttDropZone",
        [text_ctrl("txtVhpAttDropTitle", '"Drop documents here"', size=14,
                   weight="Semibold", height=22, wrap="false", color=C_MUTED),
         text_ctrl("txtVhpAttDropHint",
                   '"The file picker is added once the attachment flow contract is known. '
                   'Everything below already works."',
                   size=12, color=C_MUTED, height=32, wrap="true")],
        direction="Vertical", gap=4, height=86, width="Parent.Width",
        align_items="Center", justify="Center",
        fill=C_INPUT_BG, border_color=C_CARD_BORDER, border_thickness=1, radius=10)

    btnRemove = button(
        "btnVhpRemoveAttachment", '"Remove document"',
        (
            "If(\n"
            f"    CountRows(Filter({ATT_ACTIVE}, Selected = true)) = 0,\n"
            "    Set(varVhpRuntimeInfo, \"Select one or more documents to remove.\"),\n"
            "    RemoveIf(colVhpAttachments, ItemId = varVhpActiveItemId, Selected = true);\n"
            "    Set(varVhpRuntimeInfo, \"Removed selected document(s).\")\n"
            ")"
        ), danger=True, display_mode=DM_ITEM)
    actions = button_row("conVhpAttActions", [btnRemove], OPS_CW)

    chkSel = Ctrl("chkVhpAttSel", "ModernCheckbox", props={
        "AccessibleLabel": '"Select document"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colVhpAttachments, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colVhpAttachments, ThisItem, { Selected: false })",
        "Width": "30",
    }, h=24)
    txtName = text_ctrl("txtVhpAttName", "ThisItem.FileName", size=13, height=30,
                        width=260, wrap="false")
    txtScope = text_ctrl(
        "txtVhpAttScope",
        (
            "If(\n"
            "    Len(Coalesce(ThisItem.OperationsKey, \";\")) <= 1,\n"
            "    \"Whole item\",\n"
            "    \"Operations: \" & Substitute(Mid(ThisItem.OperationsKey, 2), \";\", \" \")\n"
            ")"
        ), size=12, color=C_MUTED, height=30, width=240, wrap="false")

    opsGal = Ctrl("galVhpAttOps", "Gallery", variant="Horizontal", props={
        "AccessibleLabel": '"Operations for this document"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": "26",
        # Den ydre raekkes LineId baeres med ind i hver record - se
        # _att_ops_cell.
        "Items": ("With(\n"
                  "    { lid: ThisItem.LineId },\n"
                  f"    ForAll({ATT_OPS} As O, {{ OperationNo: O.OperationNo, LineId: lid }})\n"
                  ")"),
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TemplatePadding": "0",
        "TemplateSize": str(ATT_CELL_W),
        "Width": "Parent.Width - 540",
        "WrapCount": "1",
    }, children=[_att_ops_cell()], h=26)

    row = group("conVhpAttRow", [chkSel, txtName, txtScope, opsGal],
                direction="Horizontal", gap=10, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    gal_h = f"Max(CountRows({ATT_ACTIVE}), 1) * {ATT_ROW_H + 2}"
    gallery = Ctrl("galVhpAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents for active item"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BORDER,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({ATT_ACTIVE}, LineId)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ATT_ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtVhpAttEmpty",
                      '"No documents on this item yet."',
                      size=13, color=C_MUTED, height=24, wrap="false",
                      visible=f"IfError(!IsBlank(varVhpActiveItemId) && CountRows({ATT_ACTIVE}) = 0, false)")

    note = text_ctrl("txtVhpAttNote",
                     '"Leave every operation unticked to attach the document to the whole item."',
                     size=12, color=C_MUTED, height=18, wrap="true")

    return group("conVhpAttPane", [dropZone, actions, note, gallery, empty],
                 direction="Vertical", gap=12, width="Parent.Width")


def build_tasklist_section():
    header = section_header("conVhpOpsHead", "Tasklist and Operations",
                            "Link a task list to the active item and add operation lines.", "Step 3",
                            help_section="ops")
    helpPanel = help_panel("conVhpOpsHelp", "ops")

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

    # Operationerne redigeres i et galleri, saa der er ingen field_cell at
    # haenge en hint paa. Den staar i stedet over tabellen og daekker linjen.
    opsHint = text_ctrl("txtVhpOpsHint", bh.hint("Operations"), size=12, color=C_MUTED,
                        height=32, wrap="true",
                        visible="IfError(varVhpShowHints && !IsBlank(varVhpActiveItemId), false)")

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
        size=12, height=32, width=w["PACKAGES"], wrap="false",
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

    # Operationstabellen og dens hjaelpelinje er fanen Operations. De
    # oevrige tre faner ligger ved siden af, hver i sin rude.
    opsPane = group("conVhpOpsPane", [opsHint, opsTableWrap], direction="Vertical",
                    gap=8, width="Parent.Width", visible=OPS_PANE_ON)
    pkgPane = build_strategy_body()
    pkgPane.vis = PKG_PANE_ON
    matPane = _materials_pane()
    matPane.vis = _tab_on("mat")
    attPane = _attachments_pane()
    attPane.vis = _tab_on("att")

    return card("conVhpOpsCard",
                [header, helpPanel, toolbar, tasklistMeta, _tab_bar(),
                 opsPane, pkgPane, matPane, attPane])


def build_dispatch_section():
    header = section_header("conVhpDispatchHead", "Dispatch and Control",
                            "Validation status before reporting via an email draft.", "Step 5")
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
            "        \"Maintenance plan ready for creation in SAP:\" & Char(10) &\n"
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
