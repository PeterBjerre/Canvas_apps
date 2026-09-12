# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE, \
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT
from build_helpers import text_ctrl, group, button, text_input

VISIBLE_OPS = (
    "Filter(\n"
    "    LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey).Operations,\n"
    "    IsBlank(Trim(txtVhpPickerSearch.Text)) || Trim(txtVhpPickerSearch.Text) in (OperationNo & \" \" & OperationShortText & \" \" & MainWorkCenter & \" \" & ControlKey)\n"
    ")"
)

# Kolonnerne i pickeren. EEN kilde til bredderne, saa overskrifts-HTML'en og
# kontrollerne i raekken ikke kan komme til at staa forskudt - de gjorde det
# med 6 px pr. kolonne, fordi de var skrevet hver for sig.
PICKER_COLS = [
    ("SEL", 26),
    ("OP NO.", 54),
    ("OPERATION SHORT TEXT", 234),
    ("MAIN WORK CENTER", 114),
    ("CTRL", 54),
    ("WORK", 54),
    ("DUR.", 54),
]
PICKER_GAP = 10


def _picker_header_html():
    cols = " ".join(f"{w}px" for _, w in PICKER_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in PICKER_COLS)
    return (
        f"\"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:{PICKER_GAP}px;align-items:center;height:22px;line-height:22px;overflow:hidden;"
        "color:#59667A;font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
        f"{spans}</div>\""
    )


PICKER_HEADER_HTML = _picker_header_html()


def build_tasklist_picker_modal():
    title = text_ctrl("txtVhpPickerTitle", "\"Select tasklist lines\"", size=17, weight="Semibold", height=24,
                      wrap="false")
    btnClose = button(
        "btnVhpPickerClose", "\"Close\"",
        "Set(varVhpTasklistPickerOpen, false); Clear(colVhpPickerSelected)", width=80, height=32)
    headRow = group("conVhpPickerHeadRow", [title, btnClose], direction="Horizontal", gap=12, height=32,
                    justify="SpaceBetween", align_items="Center")

    txtSearch = text_input("txtVhpPickerSearch", "\"\"", placeholder="\"Search operation no, text, work center\"",
                            width="Parent.Width - 220", height=36)
    chkSelectAll = Ctrl("chkVhpPickerSelectAll", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select all visible\"",
        "Default": (
            f"IfError(CountRows({VISIBLE_OPS}) > 0 && "
            f"CountRows(Filter({VISIBLE_OPS}, CountRows(Filter(colVhpPickerSelected, OperationNo = OperationNo)) > 0)) = CountRows({VISIBLE_OPS}), false)"
        ),
        "Height": "36",
        "Label": "\"Select all visible\"",
        "OnCheck": f"ForAll({VISIBLE_OPS}, If(CountRows(Filter(colVhpPickerSelected, OperationNo = OperationNo)) = 0, Collect(colVhpPickerSelected, {{ OperationNo: OperationNo }})))",
        "OnUncheck": f"ForAll({VISIBLE_OPS}, RemoveIf(colVhpPickerSelected, OperationNo = OperationNo))",
        "Width": "200",
    })
    toolbar = group("conVhpPickerToolbar", [txtSearch, chkSelectAll], direction="Horizontal", gap=12, height=36,
                    align_items="Center")

    infoText = text_ctrl(
        "txtVhpPickerInfo",
        (
            f"Text(CountRows(Filter({VISIBLE_OPS}, CountRows(Filter(colVhpPickerSelected, OperationNo = OperationNo)) > 0))) & \"/\" & "
            f"Text(CountRows({VISIBLE_OPS})) & \" visible selected (\" & Text(CountRows(colVhpPickerSelected)) & \" total selected).\""
        ), size=12, color=C_MUTED, height=18, wrap="false")

    headHtml = Ctrl("conVhpPickerHeaderHtml", "HtmlViewer", props={
        "Fill": "RGBA(0, 0, 0, 0)", "Height": "22", "HtmlText": PICKER_HEADER_HTML,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0", "Width": "636",
    }, h=22)
    divider = group("conVhpPickerDivider", [], height=1, fill="RGBA(228, 233, 241, 1)", direction="Horizontal")

    chkRowSel = Ctrl("chkVhpPickerRowSel", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select line\"",
        "Default": "CountRows(Filter(colVhpPickerSelected, OperationNo = ThisItem.OperationNo)) > 0",
        "Height": "24",
        "OnCheck": "Collect(colVhpPickerSelected, { OperationNo: ThisItem.OperationNo })",
        "OnUncheck": "RemoveIf(colVhpPickerSelected, OperationNo = ThisItem.OperationNo)",
        "Width": "26",
    })
    txtRowOpNo = text_ctrl("txtVhpPickerOpNo", "ThisItem.OperationNo", size=13, height=28, width=54, wrap="false")
    txtRowShort = text_ctrl("txtVhpPickerShortText", "ThisItem.OperationShortText", size=13, height=28, width=234,
                            wrap="false")
    txtRowMwc = text_ctrl("txtVhpPickerMwc", "ThisItem.MainWorkCenter", size=13, height=28, width=114, wrap="false")
    txtRowCtrl = text_ctrl("txtVhpPickerCtrl", "ThisItem.ControlKey", size=13, height=28, width=54, wrap="false")
    txtRowWork = text_ctrl("txtVhpPickerWork", "Text(ThisItem.WorkHours)", size=13, height=28, width=54,
                           wrap="false")
    txtRowDur = text_ctrl("txtVhpPickerDur", "Text(ThisItem.DurationHours)", size=13, height=28, width=54,
                          wrap="false")
    pickerRow = group(
        "conVhpPickerRow",
        [chkRowSel, txtRowOpNo, txtRowShort, txtRowMwc, txtRowCtrl, txtRowWork, txtRowDur],
        direction="Horizontal", gap=10, height="Parent.TemplateHeight - 2", align_items="Center",
        width="Parent.TemplateWidth")

    gallery = Ctrl(
        "galVhpPicker", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Tasklist line picker\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": "RGBA(215, 222, 232, 1)",
            "FillPortions": "0",
            "Height": "280",
            "Items": VISIBLE_OPS,
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": "32",
            "Width": "636",
            "WrapCount": "1",
        },
        children=[pickerRow], h=280)

    listWrap = group("conVhpPickerListWrap", [headHtml, divider, gallery], direction="Vertical", gap=4,
                     overflow_y="Scroll", width=636)

    btnCancel = button("btnVhpPickerCancel", "\"Cancel\"",
                       "Set(varVhpTasklistPickerOpen, false); Clear(colVhpPickerSelected)", width=100, height=36)
    btnAddSelected = button(
        "btnVhpPickerAddSelected", "\"Add selected lines\"",
        (
            "If(\n"
            "    CountRows(colVhpPickerSelected) = 0,\n"
            "    Set(varVhpRuntimeInfo, \"Select one or more lines first.\"),\n"
            "    With(\n"
            "        { tl: LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey) },\n"
            "        ForAll(\n"
            "            Filter(\n"
            "                tl.Operations As TLOP,\n"
            "                CountRows(Filter(colVhpPickerSelected As SEL, SEL.OperationNo = TLOP.OperationNo)) > 0\n"
            "            ),\n"
            "            Collect(\n"
            "                colVhpOperations,\n"
            "                {\n"
            "                    ItemId: varVhpActiveItemId, OperationNo: TLOP.OperationNo,\n"
            "                    OperationShortText: TLOP.OperationShortText, WorkHours: TLOP.WorkHours,\n"
            "                    DurationHours: TLOP.DurationHours, MainWorkCenter: TLOP.MainWorkCenter,\n"
            "                    Vendor: TLOP.Vendor, LongText: TLOP.LongText,\n"
            "                    PackagesKey: \";\", Selected: false\n"
            "                }\n"
            "            )\n"
            "        )\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Added \" & Text(CountRows(colVhpPickerSelected)) & \" operation line(s) from tasklist.\");\n"
            "    Clear(colVhpPickerSelected);\n"
            "    Set(varVhpTasklistPickerOpen, false)\n"
            ")"
        ), primary=True, width=170, height=36)
    footer = group("conVhpPickerFooter", [btnCancel, btnAddSelected], direction="Horizontal", gap=10, height=36,
                  justify="End", align_items="Center")

    modal = group(
        "conVhpPickerModal", [headRow, toolbar, infoText, listWrap, footer], direction="Vertical", gap=12,
        fill="RGBA(255, 255, 255, 0.98)", border_color="RGBA(198, 224, 249, 1)", radius=16,
        pad=(18, 18, 18, 18), width=680, drop_shadow="ExtraBold", visible="varVhpTasklistPickerOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return modal


def build_modal_backdrop():
    return Ctrl("conVhpPickerBackdrop", "GroupContainer", variant="AutoLayout", props={
        "BorderStyle": "BorderStyle.None",
        "DropShadow": "DropShadow.None",
        "Fill": "RGBA(15, 23, 42, 0.35)",
        "Height": "App.Height",
        "LayoutDirection": "LayoutDirection.Vertical",
        "Visible": "varVhpTasklistPickerOpen",
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, children=[])
