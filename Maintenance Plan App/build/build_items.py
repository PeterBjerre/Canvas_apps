# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
                        C_NEUTRAL_FG, C_NEUTRAL_BG, FONT, SHELL_W, EDITOR_W, RAIL_W, SPLIT_GAP)
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, two_col_row, badge, card)
from build_plan_header import section_header

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
REQ_ITEM = "varVhpItemValidated"

# Items-skinnens og editorens indholdsbredde (kortbredde minus 18+18 polstring).
RAIL_CW = RAIL_W - 36
EDITOR_CW = f"({EDITOR_W} - 36)"

# Gallerihoejde: TemplateSize + TemplatePadding pr. raekke. Den oprindelige
# formel regnede kun med TemplateSize og klippede derfor den sidste raekke.
ITEM_ROW_H = 88 + 6
ITEMS_GAL_H = f"Max(CountRows(colVhpItems), 1) * {ITEM_ROW_H}"

RESET_EDITOR_CONTROLS = (
    "Reset(txtVhpItemFL); Reset(txtVhpItemShortText); Reset(drpVhpItemMainWorkCenter); "
    "Reset(drpVhpItemActivityType); Reset(txtVhpItemObjectList); Reset(drpVhpItemRevision); "
    "Reset(txtVhpItemOrstedResponsible); Reset(txtVhpItemInitials); Reset(txtVhpItemLongText); "
    "Reset(drpVhpItemTasklist)"
)


def build_items_rail():
    header = section_header("conVhpItemsHead", "Items",
                            "Hvert item har eget FL, tasklist-binding og operationer.", "Step 2")

    btnAdd = button(
        "btnVhpAddItem", "\"Add item\"",
        (
            "If(\n"
            "    !varVhpPlanCommitted,\n"
            "    Set(varVhpRuntimeInfo, \"Save the plan before adding items.\"),\n"
            "\n"
            "    Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
            "    Collect(\n"
            "        colVhpItems,\n"
            "        {\n"
            "            ItemId: varVhpNextItemId, ShortText: \"\", FunctionalLocation: \"\", FlDescription: \"\",\n"
            "            MainWorkCenter: \"\", ActivityType: \"\", ObjectList: \"\", Revision: \"\",\n"
            "            OrstedResponsible: \"\", Initials: \"\", LongText: \"\", TasklistKey: \"\", TasklistName: \"\",\n"
            "            Status: \"draft\"\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpActiveItemId, varVhpNextItemId);\n"
            "    Set(varVhpItemValidated, false);\n"
            "    Set(varVhpFlMeta, \"\");\n"
            f"    {RESET_EDITOR_CONTROLS};\n"
            "    Set(varVhpRuntimeInfo, \"Item \" & Text(varVhpNextItemId) & \" added.\")\n"
            ")"
        ))

    btnCopy = button(
        "btnVhpCopyItem", "\"Copy item\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId) || CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "    Set(varVhpRuntimeInfo, \"Select an item to copy first.\"),\n"
            "\n"
            "    With(\n"
            "        { src: LookUp(colVhpItems, ItemId = varVhpActiveItemId) },\n"
            "        Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
            "        Collect(\n"
            "            colVhpItems,\n"
            "            {\n"
            "                ItemId: varVhpNextItemId, ShortText: src.ShortText, FunctionalLocation: \"\",\n"
            "                FlDescription: \"\", MainWorkCenter: src.MainWorkCenter, ActivityType: src.ActivityType,\n"
            "                ObjectList: src.ObjectList, Revision: src.Revision,\n"
            "                OrstedResponsible: src.OrstedResponsible, Initials: src.Initials, LongText: src.LongText,\n"
            "                TasklistKey: src.TasklistKey, TasklistName: src.TasklistName, Status: \"draft\"\n"
            "            }\n"
            "        );\n"
            "        ForAll(\n"
            "            Filter(colVhpOperations, ItemId = varVhpActiveItemId),\n"
            "            Collect(\n"
            "                colVhpOperations,\n"
            "                {\n"
            "                    ItemId: varVhpNextItemId, OperationNo: OperationNo,\n"
            "                    OperationShortText: OperationShortText, WorkHours: WorkHours,\n"
            "                    DurationHours: DurationHours, MainWorkCenter: MainWorkCenter, Vendor: Vendor,\n"
            "                    LongText: LongText, PackagesKey: PackagesKey, Selected: false\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        Set(varVhpActiveItemId, varVhpNextItemId);\n"
            f"        {RESET_EDITOR_CONTROLS};\n"
            "        Set(varVhpRuntimeInfo, \"Item copied. Functional Location cleared on the copied item.\")\n"
            "    )\n"
            ")"
        ))

    btnRemove = button(
        "btnVhpRemoveItem", "\"Remove item\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item to remove first.\"),\n"
            "\n"
            "    RemoveIf(colVhpOperations, ItemId = varVhpActiveItemId);\n"
            "    RemoveIf(colVhpItems, ItemId = varVhpActiveItemId);\n"
            "    Set(varVhpActiveItemId, If(CountRows(colVhpItems) > 0, First(colVhpItems).ItemId, Blank()));\n"
            f"    {RESET_EDITOR_CONTROLS};\n"
            "    Set(varVhpRuntimeInfo, \"Item removed.\")\n"
            ")"
        ), danger=True)

    # Knapperne deler bredden ligeligt, saa raekken aldrig ombryder.
    btnRow = button_row("conVhpItemButtonRow", [btnAdd, btnCopy, btnRemove], RAIL_CW)

    # --- item card template -------------------------------------------------
    cardTitle = text_ctrl(
        "txtVhpItemCardTitle",
        "If(IsBlank(ThisItem.ShortText), \"Item \" & Text(ThisItem.ItemId), ThisItem.ShortText)",
        size=14, weight="Semibold", height=20, wrap="false")
    cardFl = text_ctrl(
        "txtVhpItemCardFl",
        "\"FL: \" & If(IsBlank(ThisItem.FunctionalLocation), \"No FL\", ThisItem.FunctionalLocation)",
        size=12, color=C_MUTED, height=18, wrap="false")
    cardTasklist = text_ctrl(
        "txtVhpItemCardTasklist",
        "If(IsBlank(ThisItem.TasklistName), \"No tasklist\", ThisItem.TasklistName) & \" | Ops: \" & Text(CountRows(Filter(colVhpOperations, ItemId = ThisItem.ItemId)))",
        size=12, color=C_MUTED, height=18, wrap="false")
    cardTextCol = group("conVhpItemCardText", [cardTitle, cardFl, cardTasklist], direction="Vertical", gap=2,
                        fill_portions=1, width="Parent.Width - 70 - 10")
    cardStatus = text_ctrl(
        "txtVhpItemCardStatus", "Upper(ThisItem.Status)", size=11, weight="Semibold", height=22, width=66,
        wrap="false",
        extra={
            "Align": "Align.Center", "AlignInContainer": "AlignInContainer.Center",
            "Color": f"Switch(ThisItem.Status, \"valid\", {C_VALID_FG}, \"invalid\", {C_INVALID_FG}, {C_MUTED})",
            "Fill": f"Switch(ThisItem.Status, \"valid\", {C_VALID_BG}, \"invalid\", {C_INVALID_BG}, {C_NEUTRAL_BG})",
            "PaddingLeft": "6", "PaddingRight": "6",
            "RadiusBottomLeft": "10", "RadiusBottomRight": "10", "RadiusTopLeft": "10", "RadiusTopRight": "10",
        })
    btnOpen = button(
        "btnVhpItemOpen", "\"Open\"",
        (
            "Set(varVhpActiveItemId, ThisItem.ItemId);\n"
            "Set(varVhpItemValidated, false);\n"
            "Set(varVhpFlMeta, \"\");\n"
            f"{RESET_EDITOR_CONTROLS}"
        ), width=70, height=30)
    cardRight = group("conVhpItemCardRight", [cardStatus, btnOpen], direction="Vertical", gap=6,
                      align_items="End", width=70)

    itemCard = group(
        "conVhpItemCard", [cardTextCol, cardRight], direction="Horizontal", gap=10,
        height="Parent.TemplateHeight - 2",
        fill=f"If(ThisItem.ItemId = varVhpActiveItemId, {C_INFO_BG}, {C_CARD_BG})",
        border_color=f"If(ThisItem.ItemId = varVhpActiveItemId, {C_INFO_FG}, {C_CARD_BORDER})",
        border_thickness=1, radius=10, pad=(10, 12, 10, 12), width="Parent.TemplateWidth",
        align_items="Center")

    gallery = Ctrl(
        "galVhpItemsRail", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"VH-plan items\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": "RGBA(0, 0, 0, 0)",
            "FillPortions": "0",
            "Height": ITEMS_GAL_H,
            "Items": "Sort(colVhpItems, ItemId)",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "6",
            "TemplateSize": "88",
            "Width": "Parent.Width",
            "WrapCount": "1",
        },
        children=[itemCard], h=ITEMS_GAL_H)

    emptyState = text_ctrl(
        "txtVhpItemsEmpty", "\"No items yet. Use Add item to create the first item for this plan.\"",
        size=13, color=C_MUTED, height=40, wrap="true",
        visible="IfError(CountRows(colVhpItems) = 0, true)")

    return card("conVhpItemsCard", [header, btnRow, gallery, emptyState], gap=12)


def build_item_editor():
    header = section_header("conVhpEditorHead", "Item Editor",
                            "Fulde itemfelter med reference-opslag af Functional Location.", "")

    txtFl = text_input("txtVhpItemFL", "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation",
                       placeholder="\"e.g. SSV10 KAB10AP001\"", max_length=40,
                       required_formula=REQ_ITEM, display_mode=DM_ITEM, ttype="Search",
                       width="Parent.Width - 110 - 8")
    btnVerify = button(
        "btnVhpVerifyFl", "\"Verify FL\"",
        (
            "With(\n"
            "    { code: Upper(Trim(txtVhpItemFL.Text)), match: LookUp(colVhpFunctionalLocations, Code = Upper(Trim(txtVhpItemFL.Text))) },\n"
            "    If(\n"
            "        IsBlank(code),\n"
            "        Set(varVhpFlMeta, \"Enter a Functional Location first.\"),\n"
            "        If(\n"
            "            IsBlank(match),\n"
            "            Set(varVhpFlMeta, \"Functional Location not found in reference data.\"),\n"
            "            Set(varVhpFlMeta, \"Verified: \" & match.Code & \" - \" & match.Description & \" (\" & match.Plant & \").\")\n"
            "        )\n"
            "    )\n"
            ")"
        ), width=110, height=36)
    flRow = group("conVhpItemFlRow", [txtFl, btnVerify], direction="Horizontal", gap=8, height=36,
                  align_items="Center")
    flLabelRow = label_row("conVhpItemFlLabel", "Functional Location", required=True)
    flDescription = text_ctrl(
        "txtVhpItemFlDescription",
        "With({ code: Upper(Trim(txtVhpItemFL.Text)) }, Coalesce(LookUp(colVhpFunctionalLocations, Code = code).Description, \"No match in reference data. Free text FL is still allowed.\"))",
        size=12, color=C_MUTED, height=18, wrap="true")
    flMeta = text_ctrl("txtVhpItemFlMeta", "varVhpFlMeta", size=12, color=C_MUTED, height=18, wrap="true")
    flBlock = group("conVhpItemFlBlock", [flLabelRow, flRow, flDescription, flMeta], direction="Vertical",
                    gap=6, width="Parent.Width")

    drpMwc = dropdown("drpVhpItemMainWorkCenter", "colVhpMainWorkCenterItemOptions",
                      "LookUp(colVhpMainWorkCenterItemOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).MainWorkCenter)",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    drpAct = dropdown("drpVhpItemActivityType", "colVhpActivityTypeOptions",
                      "LookUp(colVhpActivityTypeOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType)",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    txtShort = text_input("txtVhpItemShortText",
                          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ShortText", max_length=40,
                          required_formula=REQ_ITEM, display_mode=DM_ITEM)
    txtObjList = text_input("txtVhpItemObjectList",
                            "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ObjectList", display_mode=DM_ITEM)
    drpRevision = dropdown("drpVhpItemRevision", "colVhpRevisionOptions",
                           "LookUp(colVhpRevisionOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).Revision)",
                           display_mode=DM_ITEM)
    txtOrstedResp = text_input("txtVhpItemOrstedResponsible",
                               "LookUp(colVhpItems, ItemId = varVhpActiveItemId).OrstedResponsible",
                               display_mode=DM_ITEM)
    txtInitials = text_input("txtVhpItemInitials",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).Initials", max_length=12,
                             display_mode=DM_ITEM)

    CW = EDITOR_CW
    row1 = two_col_row("conVhpItemRow1",
                       field_cell("conVhpCellItemShortText", "Item Short Text", txtShort, required=True,
                                  container_w=CW),
                       field_cell("conVhpCellItemMwc", "Main Work Center", drpMwc, required=True,
                                  container_w=CW), container_w=CW)
    row2 = two_col_row("conVhpItemRow2",
                       field_cell("conVhpCellItemAct", "Maintenance Activity Type", drpAct, required=True,
                                  container_w=CW),
                       field_cell("conVhpCellItemObjList", "Object List", txtObjList, container_w=CW),
                       container_w=CW)
    row3 = two_col_row("conVhpItemRow3",
                       field_cell("conVhpCellItemRevision", "Revision", drpRevision, container_w=CW),
                       field_cell("conVhpCellItemOrstedResp", "Orsted Responsible", txtOrstedResp,
                                  container_w=CW), container_w=CW)
    row4 = two_col_row("conVhpItemRow4",
                       field_cell("conVhpCellItemInitials", "Initials", txtInitials, container_w=CW),
                       group("conVhpCellItemSpacer", [], height=62,
                             width=f"If({CW} < 640, {CW}, ({CW} - 20) / 2)"),
                       container_w=CW)

    fieldsGrid = group("conVhpItemFieldsGrid", [row1, row2, row3, row4], direction="Vertical", gap=16)

    txtLongText = text_input("txtVhpItemLongText",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).LongText", height=80,
                             display_mode=DM_ITEM, ttype="Multiline")
    longTextCell = field_cell("conVhpCellItemLongText", "Item Long Text", txtLongText,
                              width="Parent.Width", container_w=CW, fill_portions_formula="0")

    itemMeta = text_ctrl(
        "txtVhpItemMeta",
        "If(IsBlank(varVhpActiveItemId), \"No item selected.\", \"Item \" & Text(varVhpActiveItemId) & \" - status: \" & Upper(LookUp(colVhpItems, ItemId = varVhpActiveItemId).Status))",
        size=12, color=C_MUTED, height=18, wrap="true")
    btnSaveItem = button(
        "btnVhpSaveItem", "\"Save\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select or add an item first.\"),\n"
            "\n"
            "    Set(varVhpItemValidated, true);\n"
            "    If(\n"
            "        IsBlank(Trim(txtVhpItemShortText.Text)) || Len(Trim(txtVhpItemShortText.Text)) > 40 ||\n"
            "        IsBlank(drpVhpItemMainWorkCenter.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemActivityType.Selected.Value) ||\n"
            "        IsBlank(Trim(txtVhpItemFL.Text)),\n"
            "        UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, { Status: \"invalid\" });\n"
            "        Set(varVhpRuntimeInfo, \"Item contains issues. Fix required fields (marked with *).\"),\n"
            "\n"
            "        With(\n"
            "            { code: Upper(Trim(txtVhpItemFL.Text)) },\n"
            "            UpdateIf(\n"
            "                colVhpItems,\n"
            "                ItemId = varVhpActiveItemId,\n"
            "                {\n"
            "                    ShortText: Trim(txtVhpItemShortText.Text),\n"
            "                    FunctionalLocation: code,\n"
            "                    FlDescription: Coalesce(LookUp(colVhpFunctionalLocations, Code = code).Description, \"\"),\n"
            "                    MainWorkCenter: drpVhpItemMainWorkCenter.Selected.Value,\n"
            "                    ActivityType: drpVhpItemActivityType.Selected.Value,\n"
            "                    ObjectList: Trim(txtVhpItemObjectList.Text),\n"
            "                    Revision: drpVhpItemRevision.Selected.Value,\n"
            "                    OrstedResponsible: Trim(txtVhpItemOrstedResponsible.Text),\n"
            "                    Initials: Trim(txtVhpItemInitials.Text),\n"
            "                    LongText: Trim(txtVhpItemLongText.Text),\n"
            "                    Status: \"valid\"\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        Set(varVhpRuntimeInfo, \"Item saved: \" & Trim(txtVhpItemShortText.Text) & \".\")\n"
            "    )\n"
            ")"
        ), primary=True, width=110,
        display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conVhpEditorFooter", [itemMeta, btnSaveItem], direction="Horizontal", gap=16, height=36,
                   align_items="Center")

    return card("conVhpEditorCard", [header, flBlock, fieldsGrid, longTextCell, footer])


def build_items_section():
    rail = build_items_rail()
    editor = build_item_editor()
    # Hoejden er de to korts BEREGNEDE hoejder - ikke .Height paa kontrollerne.
    # Det var netop den reference, der gav cirkelreferencen og kaskade-vaeksten.
    h = (f"If(App.Width < 1000, ({rail.h}) + {SPLIT_GAP} + ({editor.h}), "
         f"Max(({rail.h}), ({editor.h})))")
    rail.props["Width"] = f"If(App.Width < 1000, Parent.Width, {RAIL_W})"
    editor.props["Width"] = EDITOR_W
    return group("conVhpItemsSplit", [rail, editor], direction="Horizontal", gap=SPLIT_GAP,
                 height=h, wrap="true")
