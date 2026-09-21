# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE, \
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_TRANSPARENT, C_DIVIDER, \
    C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY, FONT
from build_helpers import text_ctrl, group, button, text_input
from design_tokens import ref_hex

MUT_HEX = ref_hex("text-muted")

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
    # Se _ops_header_html i build_tasklist.py: <style>-nulstillingen af
    # iframe'ens body-margin fjerner scrollbaren under overskriften.
    return (
        "\"<style>html,body{margin:0;padding:0;overflow:hidden}</style>"
        f"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:{PICKER_GAP}px;align-items:center;height:21px;line-height:21px;overflow:hidden;"
        "color:\" & " + MUT_HEX + " & \";font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
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
                            width="Parent.Width - 220", height=36, label="\"Soeg i operationer\"")
    chkSelectAll = Ctrl("chkVhpPickerSelectAll", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select all visible\"",
        "Default": (
            f"IfError(CountRows({VISIBLE_OPS}) > 0 && "
            f"CountRows(Filter({VISIBLE_OPS} As VOP, CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) > 0)) = CountRows({VISIBLE_OPS}), false)"
        ),
        "Height": "36",
        "Label": "\"Select all visible\"",
        "OnCheck": f"ForAll({VISIBLE_OPS} As VOP, If(CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) = 0, Collect(colVhpPickerSelected, {{ OperationNo: VOP.OperationNo }})))",
        "OnUncheck": f"ForAll({VISIBLE_OPS} As VOP, RemoveIf(colVhpPickerSelected, OperationNo = VOP.OperationNo))",
        "Width": "200",
    })
    toolbar = group("conVhpPickerToolbar", [txtSearch, chkSelectAll], direction="Horizontal", gap=12, height=36,
                    align_items="Center")

    infoText = text_ctrl(
        "txtVhpPickerInfo",
        (
            f"Text(CountRows(Filter({VISIBLE_OPS} As VOP, CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) > 0))) & \"/\" & "
            f"Text(CountRows({VISIBLE_OPS})) & \" visible selected (\" & Text(CountRows(colVhpPickerSelected)) & \" total selected).\""
        ), size=12, color=C_MUTED, height=18, wrap="false")

    headHtml = Ctrl("conVhpPickerHeaderHtml", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": PICKER_HEADER_HTML,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0", "Width": "636",
    }, h=22)
    divider = group("conVhpPickerDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal")

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
            "Fill": C_CARD_BORDER,
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
            "            ) As TLOP,\n"
            "            Collect(\n"
            "                colVhpOperations,\n"
            "                {\n"
            "                    ItemId: varVhpActiveItemId, OperationNo: TLOP.OperationNo,\n"
            "                    OperationShortText: TLOP.OperationShortText, WorkHours: TLOP.WorkHours,\n"
            "                    Persons: TLOP.Persons,\n"
            "                    DurationHours: TLOP.DurationHours, MainWorkCenter: TLOP.MainWorkCenter,\n"
            "                    Vendor: TLOP.Vendor, LongText: TLOP.LongText,\n"
            "                    ControlKey: TLOP.ControlKey, Cost: TLOP.Cost,\n"
            "                    UnitCost: TLOP.UnitCost,\n"
            "                    Currency: TLOP.Currency, CostElement: TLOP.CostElement,\n"
            "                    MaterialGroup: TLOP.MaterialGroup,\n"
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
        fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
        pad=(18, 18, 18, 18), width=680, drop_shadow="ExtraBold", visible="varVhpTasklistPickerOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return modal


# ---------------------------------------------------------------------------
# Lang tekst paa en operation
# ---------------------------------------------------------------------------
# Feltet laa som et enkeltlinjet input paa 170 px inde i operationsraekken.
# Der er ikke plads til en instruktion i 170 px, og raekken kan ikke vokse:
# alle tolv celler deler samme hoejde.
#
# Raekken har nu en knap, der viser begyndelsen af teksten, og selve
# skrivningen sker i en popup med et flerlinjet felt - samme konstruktion
# som tasklist-pickeren, saa der ikke kommer en tredje slags overlay ind i
# appen.
#
# Operationen udpeges af BEGGE noegler. OperationNo er kun unikt inden for
# et item, saa "0010" alene ville ramme samme operationsnummer paa hvert
# eneste item i planen.
LT_TARGET = "ItemId = varVhpLongTextItemId && OperationNo = varVhpLongTextOpNo"


def build_longtext_modal():
    title = text_ctrl("txtVhpLongTextTitle",
                      '"Long text - operation " & varVhpLongTextOpNo',
                      size=17, weight="Semibold", height=24, wrap="false")
    btnCancel = button("btnVhpLongTextCancel", '"Cancel"',
                       "Set(varVhpLongTextOpen, false)", width=90, height=32)
    headRow = group("conVhpLongTextHeadRow", [title, btnCancel], direction="Horizontal",
                    gap=12, height=32, justify="SpaceBetween", align_items="Center")

    hint = text_ctrl(
        "txtVhpLongTextHint",
        ('"The long text follows the operation to SAP. Write the instruction '
         'as the technician needs to read it - steps, safety notes and references."'),
        size=12, color=C_MUTED, height=32, wrap="true")

    box = text_input("txtVhpLongTextBox", "varVhpLongTextDraft",
                     placeholder='"Instructions for this operation"',
                     width="Parent.Width", height=260, ttype="Multiline", label="\"Langtekst\"")

    # Gemmer paa knappen, ikke paa hvert tastetryk. Et OnChange pr. tegn ville
    # skrive i samlingen, mens man skriver - og Annuller ville ikke kunne
    # fortryde noget.
    btnSave = button(
        "btnVhpLongTextSave", '"Save text"',
        (
            "UpdateIf(\n"
            "    colVhpOperations,\n"
            f"    {LT_TARGET},\n"
            "    { LongText: txtVhpLongTextBox.Text }\n"
            ");\n"
            "Set(varVhpRuntimeInfo, \"Long text saved on operation \" & varVhpLongTextOpNo & \".\");\n"
            "Set(varVhpLongTextOpen, false)"
        ), primary=True, width=150, height=36)
    footer = group("conVhpLongTextFooter", [btnSave], direction="Horizontal", gap=10,
                   height=36, justify="End", align_items="Center")

    modal = group(
        "conVhpLongTextModal", [headRow, hint, box, footer], direction="Vertical", gap=12,
        fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
        pad=(18, 18, 18, 18), width=620, drop_shadow="ExtraBold",
        visible="varVhpLongTextOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return modal


def build_modal_backdrop():
    return Ctrl("conVhpPickerBackdrop", "GroupContainer", variant="AutoLayout", props={
        "BorderStyle": "BorderStyle.None",
        "DropShadow": "DropShadow.None",
        "Fill": C_OVERLAY,
        "Height": "App.Height",
        "LayoutDirection": "LayoutDirection.Vertical",
        "Visible": "varVhpTasklistPickerOpen || varVhpLongTextOpen",
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, children=[])
