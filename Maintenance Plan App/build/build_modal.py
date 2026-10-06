# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_MUTED, C_TRANSPARENT, C_DIVIDER, C_MODAL_BG,
                        C_PRIMARY_SOFT, C_OVERLAY, C_PRIMARY, C_WHITE)
import layout_tokens as lay
from layout_tokens import at_least, if_below
from build_helpers import tap_backdrop, text_ctrl, group, button, text_input, grow, ICON_SAVE, checkbox_theme, table_surface
from design_tokens import ref_hex

MUT_HEX = ref_hex("text-muted")

VISIBLE_OPS = (
    "Filter(\n"
    "    LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey).Operations,\n"
    "    IsBlank(Trim(inpVhpPickerSearch.Text)) || Trim(inpVhpPickerSearch.Text) in (OperationNo & \" \" & OperationShortText & \" \" & MainWorkCenter & \" \" & ControlKey)\n"
    ")"
)

# Kolonnerne i pickeren. EEN kilde til bredderne, saa overskrifts-HTML'en og
# kontrollerne i raekken ikke kan komme til at staa forskudt - de gjorde det
# med 6 px pr. kolonne, fordi de var skrevet hver for sig.
PICKER_COLS = [
    ("SEL", 26),
    ("OP NO.", 54),
    # 198, ikke 234: raekken skal kunne staa i galleriets 636 px minus
    # TemplatePadding og scrollbar (614). Ved 234 laa varigheden under
    # scrollbaren.
    ("OPERATION SHORT TEXT", 198),
    ("MAIN WORK CENTER", 114),
    ("CTRL", 54),
    ("WORK", 54),
    ("DUR.", 54),
]
PICKER_GAP = 10


def _picker_header_html(cols_def=PICKER_COLS):
    cols = " ".join(f"{w}px" for _, w in cols_def)
    spans = "".join(f"<span>{t}</span>" for t, _ in cols_def)
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

# DESKTOP (issue #109): "Select all" sidder i tabeloverskriften, over
# raekkernes afkrydsning i SEL-kolonnen. Overskriften er derfor en raekke:
# afkrydsningen (SEL-bredden) + HTML'en for resten af kolonnerne med samme
# mellemrum. Under desktop er alt som foer: hele HTML'en med SEL-teksten.
# Den fulde HTML staar SIDST i If'en - check_layout regel 5 laeser den.
DESK = at_least("Desktop")
SEL_W = PICKER_COLS[0][1]
PICKER_HEADER_DESK_HTML = _picker_header_html(PICKER_COLS[1:])
PICKER_HEADER_HTML_ANY = f"If({DESK}, {PICKER_HEADER_DESK_HTML}, {PICKER_HEADER_HTML})"

# Antal synlige raekker og hvor mange af dem, der er valgt. Delt af
# afkrydsningerne og den delvise tilstand, saa de ikke kan komme i utakt.
VISIBLE_N = f"CountRows({VISIBLE_OPS})"
VISIBLE_SEL_N = (f"CountRows(Filter({VISIBLE_OPS} As VOP, "
                 "CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) > 0))")
ALL_VISIBLE_SELECTED = f"IfError({VISIBLE_N} > 0 && {VISIBLE_SEL_N} = {VISIBLE_N}, false)"
SOME_VISIBLE_SELECTED = f"IfError({VISIBLE_SEL_N} > 0 && {VISIBLE_SEL_N} < {VISIBLE_N}, false)"

# EEN SKRIVNING HVER VEJ
#
# Her stod to ForAll med en mutation indeni. Begrundelsen var, at
# maalet er en samling i hukommelsen, saa der ikke var noget
# netvaerkskald at spare. App checker melder dem alligevel
# (ForAllWithMutation), og den har ret i det, begrundelsen ikke
# naevnte: hver enkelt skrivning faar ALT, der afhaenger af
# samlingen, til at genberegne - og her afhaenger baade
# afkrydsningen i hver raekke og "vaelg alle"s egen Default af den.
#
# Den gamle note var i tvivl om RemoveIf med to raekkescopes. Det
# spoergsmaal er der ikke laengere: Remove(DataSource, Table) er en
# dokumenteret form, og tabellen er raekker fra samlingen selv, saa
# de matcher helt.
SELECT_ALL_VISIBLE = (
    "Collect(\n"
    "    colVhpPickerSelected,\n"
    "    ForAll(\n"
    f"        Filter(\n"
    f"            {VISIBLE_OPS} As VOP,\n"
    "            CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) = 0\n"
    "        ) As NEW,\n"
    "        { OperationNo: NEW.OperationNo }\n"
    "    )\n"
    ")"
)
CLEAR_ALL_VISIBLE = (
    "Remove(\n"
    "    colVhpPickerSelected,\n"
    "    Filter(\n"
    "        colVhpPickerSelected As SEL,\n"
    f"        CountRows(Filter({VISIBLE_OPS} As VOP, VOP.OperationNo = SEL.OperationNo)) > 0\n"
    "    )\n"
    ")"
)

# Galleriets raekkehoejde efter table_surface (TemplateSize 32 + padding 2).
PICKER_ROW_H = 34
# Popuppens faste dele paa desktop: padding 18+18, hoved 32, soegefelt 36,
# info 18, kolonneoverskrift 22 + streg 1 + 2 x 4 gap, knapraekke 36 og
# 4 x 12 gap mellem sektionerne = 237. Plus 32 luft over og under.
PICKER_FIXED_H = 237
PICKER_EDGE = 32


def build_tasklist_picker_modal():
    title = text_ctrl("txtVhpPickerTitle", "\"Select tasklist lines\"", size=lay.SIZE_CARD_TITLE, weight="Semibold", height=24,
                      wrap="false")
    btnClose = button(
        "btnVhpPickerClose", "\"Close\"",
        "Set(varVhpTasklistPickerOpen, false); Clear(colVhpPickerSelected)", width=80, height=32)
    headRow = group("conVhpPickerHeadRow", [title, btnClose], direction="Horizontal", gap=12, height=32,
                    justify="SpaceBetween", align_items="Center")

    txtSearch = text_input("inpVhpPickerSearch", "\"\"", placeholder="\"Search operation no, text, work center\"",
                            height=36, label="\"Search operations\"")
    grow(txtSearch)
    # Under desktop: "Select all visible" ved soegefeltet som foer. Paa
    # desktop sidder "Select all" i tabeloverskriften (issue #109).
    chkSelectAll = Ctrl("chkVhpPickerSelectAll", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": "\"Select all visible\"",
        "Default": ALL_VISIBLE_SELECTED,
        "Height": "36",
        "Label": "\"Select all visible\"",
        "OnCheck": SELECT_ALL_VISIBLE,
        "OnUncheck": CLEAR_ALL_VISIBLE,
        "Width": "200",
    }), vis=if_below("Desktop", "true", "false"))
    toolbar = group("conVhpPickerToolbar", [txtSearch, chkSelectAll], direction="Horizontal", gap=12, height=36,
                    align_items="Center")

    infoText = text_ctrl(
        "txtVhpPickerInfo",
        (
            f"Text(CountRows(Filter({VISIBLE_OPS} As VOP, CountRows(Filter(colVhpPickerSelected, OperationNo = VOP.OperationNo)) > 0))) & \"/\" & "
            f"Text(CountRows({VISIBLE_OPS})) & \" visible selected (\" & Text(CountRows(colVhpPickerSelected)) & \" total selected).\""
        ), size=12, color=C_MUTED, height=18, wrap="false")

    headHtml = Ctrl("htmVhpPickerHeader", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": PICKER_HEADER_HTML_ANY,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": if_below("Desktop", "636", str(636 - SEL_W - PICKER_GAP)),
    }, h=22)
    # "Select all" i SEL-kolonnen (desktop). Tre tilstande: ingen valgt =
    # tom boks, alle synlige valgt = afkrydset boks. En moderne checkboks
    # har ingen delvis tilstand, saa naar NOGLE er valgt, staar en lille
    # knap med et minus i boksens sted; et tryk paa den vaelger alle.
    chkHeadAll = Ctrl("chkVhpPickerHeadAll", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": "\"Select all\"",
        "Default": ALL_VISIBLE_SELECTED,
        "Height": "22",
        "OnCheck": SELECT_ALL_VISIBLE,
        "OnUncheck": CLEAR_ALL_VISIBLE,
        "Tooltip": "\"Select all\"",
        "Width": str(SEL_W),
    }), h=22, vis=f"{DESK} && !{SOME_VISIBLE_SELECTED}")
    btnHeadPartial = Ctrl("btnVhpPickerHeadPartial", "Classic/Button", props={
        "BorderColor": C_PRIMARY, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
        "Color": C_WHITE, "Fill": C_PRIMARY, "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2", "FontWeight": "FontWeight.Bold",
        "Height": "18", "HoverColor": C_WHITE, "HoverFill": C_PRIMARY,
        "OnSelect": SELECT_ALL_VISIBLE,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "PressedColor": C_WHITE, "PressedFill": C_PRIMARY,
        "RadiusBottomLeft": "4", "RadiusBottomRight": "4", "RadiusTopLeft": "4", "RadiusTopRight": "4",
        "Size": "12", "TabIndex": "0",
        # Den klassiske knap har ingen AccessibleLabel - skaermlaeseren
        # laeser Text og Tooltip.
        "Text": "\"\u2212\"",
        "Tooltip": "\"Some lines selected - select all\"",
        "Width": "18",
    }, h=18, vis=f"{DESK} && {SOME_VISIBLE_SELECTED}")
    # Lodret, ikke vandret: der er altid kun EEN af de to synlig, og de
    # deler SEL-kolonnens 26 px.
    headSel = group("conVhpPickerHeadSel", [chkHeadAll, btnHeadPartial], direction="Vertical", gap=0,
                    height=22, width=SEL_W, align_items="Center", justify="Center", visible=DESK)
    colHead = group("conVhpPickerColHead", [headSel, headHtml], direction="Horizontal", gap=PICKER_GAP,
                    height=22, width=636, align_items="Center")
    divider = group("conVhpPickerDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal",
                    width=636)

    chkRowSel = Ctrl("chkVhpPickerRowSel", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": "\"Select line\"",
        "Default": "CountRows(Filter(colVhpPickerSelected, OperationNo = ThisItem.OperationNo)) > 0",
        "Height": "24",
        "OnCheck": "Collect(colVhpPickerSelected, { OperationNo: ThisItem.OperationNo })",
        "OnUncheck": "RemoveIf(colVhpPickerSelected, OperationNo = ThisItem.OperationNo)",
        "Width": "26",
    }))
    txtRowOpNo = text_ctrl("txtVhpPickerOpNo", "ThisItem.OperationNo", size=13, height=28, width=54, wrap="false")
    txtRowShort = text_ctrl("txtVhpPickerShortText", "ThisItem.OperationShortText", size=13, height=28, width=dict(PICKER_COLS)["OPERATION SHORT TEXT"],
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
            "Fill": C_MODAL_BG,
            "FillPortions": "0",
            # Desktop: saa hoej som raekkerne, med et loft fra skaermhoejden,
            # saa popuppen aldrig gaar ud over skaermen. Foerst naar raekkerne
            # ikke kan staa der, scroller galleriet (issue #109).
            "Height": if_below("Desktop", "280",
                               f"Min(Max({VISIBLE_N}, 1) * {PICKER_ROW_H}, "
                               f"Max(3 * {PICKER_ROW_H}, App.Height - {PICKER_FIXED_H + 2 * PICKER_EDGE}))"),
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
        children=[pickerRow], h=None)
    gallery.h = gallery.props["Height"]
    # Neutral flade og een streg pr. raekke - ikke graat fyld (issue #78).
    table_surface(gallery, "rctVhpPickerRule", surface=C_MODAL_BG)

    # Ingen scroll her: beholderen er praecis saa hoej som sit indhold, og
    # galleriet scroller selv. To scrollbarer oven i hinanden tog 18 px
    # ekstra af bredden, og sidste kolonne laa under dem.
    listWrap = group("conVhpPickerListWrap", [colHead, divider, gallery], direction="Vertical", gap=4,
                     width=636, align_items="Start")
    # POPUPPEN FOELGER SKAERMEN (REVIEW.md A16). Den var fast 740 px og gik
    # ud over en telefon. Nu er den Min(740, App.Width - 40) som de andre
    # popups; listen beholder sine 636 px og scroller VANDRET i en smallere
    # popup - i stedet for at kolonnerne klemmes.
    listScroll = group("conVhpPickerListScroll", [listWrap], direction="Vertical", gap=0,
                       align_items="Start",
                       overflow_x="Scroll", width="Parent.Width")

    btnCancel = button("btnVhpPickerCancel", "\"Cancel\"",
                       "Set(varVhpTasklistPickerOpen, false); Clear(colVhpPickerSelected)", width=100, height=36,
                       visible=if_below("Desktop", "true", "false"))
    btnAddSelected = button(
        "btnVhpPickerAddSelected", "\"Add selected lines\"",
        (
            "If(\n"
            "    CountRows(colVhpPickerSelected) = 0,\n"
            "    Notify(\"Select one or more lines first.\", NotificationType.Warning),\n"
            "    With(\n"
            "        { tl: LookUp(colVhpTasklists, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey) },\n"
            # Collect UDEN OM ForAll - eet kald i stedet for eet pr. linje.
            "        Collect(\n"
            "            colVhpOperations,\n"
            "            ForAll(\n"
            "                Filter(\n"
            "                    tl.Operations As TLOP,\n"
            "                    CountRows(Filter(colVhpPickerSelected As SEL, "
            "SEL.OperationNo = TLOP.OperationNo)) > 0 &&\n"
            # En linje, itemet allerede har, tilfoejes ikke igen. OperationNo
            # antages unik pr. item i pakkematricen og materialekoblingen.
            "                    !(TLOP.OperationNo in "
            "Filter(colVhpOperations, ItemId = varVhpActiveItemId).OperationNo)\n"
            "                ) As TLOP,\n"
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
            "    Notify(\"Added \" & Text(CountRows(colVhpPickerSelected)) & \" operation line(s) from tasklist.\", NotificationType.Success);\n"
            "    Clear(colVhpPickerSelected);\n"
            "    Set(varVhpTasklistPickerOpen, false)\n"
            ")"
        ), primary=True, width=170, height=36,
        # Desktop: graa, til der er valgt mindst een linje (issue #109).
        display_mode=f"If({DESK} && CountRows(colVhpPickerSelected) = 0, DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conVhpPickerFooter", [btnCancel, btnAddSelected], direction="Horizontal", gap=10, height=36,
                  justify="End", align_items="Center")

    modal = group(
        "conVhpPickerModal", [headRow, toolbar, infoText, listScroll, footer], direction="Vertical", gap=12,
        fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
        pad=(18, 18, 18, 18), width="Min(740, App.Width - 40)", drop_shadow="ExtraBold",
        visible="varVhpTasklistPickerOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    # Desktop: hoejt oppe med fast luft til toppen, ikke centreret.
    modal.props["Y"] = if_below("Desktop", "Max(20, (App.Height - Self.Height) / 3)", str(PICKER_EDGE))
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
                      'If(varVhpLongTextTarget = "item", "Long text - item " & Text(varVhpLongTextItemId), '
                      '"Long text - operation " & varVhpLongTextOpNo)',
                      size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false")
    btnCancel = button("btnVhpLongTextCancel", '"Close"',
                       "Set(varVhpLongTextOpen, false)", width=90, height=32)
    headRow = group("conVhpLongTextHeadRow", [title, btnCancel], direction="Horizontal",
                    gap=12, height=32, justify="SpaceBetween", align_items="Center")

    box = text_input("inpVhpLongTextBox", "varVhpLongTextDraft",
                     placeholder='"Instructions for this operation"',
                     width="Parent.Width", height=260, ttype="Multiline", label="\"Long text\"")

    # Gemmer paa knappen, ikke paa hvert tastetryk. Et OnChange pr. tegn ville
    # skrive i samlingen, mens man skriver - og Annuller ville ikke kunne
    # fortryde noget.
    btnSave = button(
        "btnVhpLongTextSave", '"Save text"',
        (
            # Samme popup til itemets lange tekst (issue #54) - maalet er
            # varVhpLongTextTarget.
            "If(\n"
            "    varVhpLongTextTarget = \"item\",\n"
            "    UpdateIf(colVhpItems, ItemId = varVhpLongTextItemId,\n"
            "             { LongText: Trim(inpVhpLongTextBox.Text) }),\n"
            "    UpdateIf(\n"
            "        colVhpOperations,\n"
            f"        {LT_TARGET},\n"
            "        { LongText: inpVhpLongTextBox.Text }\n"
            "    )\n"
            ");\n"
            "Set(varVhpLongTextOpen, false)"
        ), primary=True, width=150, height=36, icon=ICON_SAVE,
        display_mode="If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conVhpLongTextFooter", [btnSave], direction="Horizontal", gap=10,
                   height=36, justify="End", align_items="Center")

    modal = group(
        "conVhpLongTextModal", [headRow, box, footer], direction="Vertical", gap=12,
        fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
        pad=(18, 18, 18, 18), width="Min(620, App.Width - 40)", drop_shadow="ExtraBold",
        visible="varVhpLongTextOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return modal


def build_modal_backdrop():
    vis = ("varVhpTasklistPickerOpen || varVhpLongTextOpen || varVhpObjListOpen || "
           "!IsBlank(varVhpMatOpNo) || !IsBlank(varVhpAttOpNo) || !IsBlank(varVhpOpMNo)")
    inner = ("varVhpTasklistPickerOpen || varVhpLongTextOpen || varVhpObjListOpen || "
             "!IsBlank(varVhpMatOpNo) || !IsBlank(varVhpAttOpNo)")
    return tap_backdrop("conVhpPickerBackdrop", vis,
                        f"If({inner}, Set(varVhpTasklistPickerOpen, false); Set(varVhpLongTextOpen, false); "
                        "Set(varVhpObjListOpen, false); Set(varVhpMatOpNo, \"\"); Set(varVhpAttOpNo, \"\"), "
                        "Set(varVhpOpMNo, \"\"))")
