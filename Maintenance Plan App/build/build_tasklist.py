# -*- coding: utf-8 -*-
import display_text as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_WHITE, C_MODAL_BG, C_PRIMARY_SOFT,
                        C_INVALID_FG, C_DIVIDER, C_TRANSPARENT, SHELL_W)
import layout_tokens as lay
import icons
from build_helpers import (ensure_hit, popup_head, empty_state, checkbox_theme, table_surface, flow_row, text_ctrl,
                           group, button, text_input, number_field, num_value, themed_dropdown,
                           field_cell, card, pin_widths, grow, row_hit,
                           fit_button_width, fit_button_row, ICON_W, ICON_SAVE, flow_ok, mark_done,
                           tab_list, tabs_w)
from build_plan_header import section_header, help_panel, section_footer

# Talfeltets vaerdi (UX-review T10): heltal, Blank() ved tomt felt eller ikke-tal.
NV = num_value()
from build_status import HAS_PKGS
import build_help as bh
from build_strategy import build_strategy_body, IS_STRATEGY, pkg_pills, PILLS_W
import sp_config as cfg
from design_tokens import ref_hex
from layout_tokens import SCROLLBAR_W, fits, TWO_COL_MIN, below, at_least, if_below

# HTML kender ikke RGBA(). ref_hex giver den SAMME token som hex.
MUT_HEX = ref_hex("text-muted")
BG_HEX = ref_hex("bg-muted")
PRI_HEX = ref_hex("text-primary")
import build_attflows
import doc_upload as du
from fl_picker import fl_picker
import vendor_search as vs
from build_modal import NEXT_OP_BASE

# Vedhaeftningskontrakten staar i tools/attflows.py; kun rudens egne
# navne og listen staar i build_attflows.py (issue #300).
att = build_attflows.PANE

DM_ITEM = "If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
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
    ("OP NO.", 60),
    ("OPERATION SHORT TEXT", 200),
    ("WORK (H)", 64),
    ("NO.", 50),
    ("DUR. (H)", 64),
    ("MAIN WORK CENTER", 110),
    ("CTRL", 90),
    ("VENDOR", 110),
    ("COST", 80),
    ("MAT.GRP", 90),
    ("LONG TEXT", 170),
    # Plads til syv smalle pakke-piller (build_strategy.pkg_pills).
    ("PACKAGES", PILLS_W),
    # Knapper, som Details og Docs i Equipments liste (issue #54). De
    # aabner materialerne og dokumenterne for NETOP denne operation.
    ("MATERIALS", 110),
    ("DOCS", 90),
    ("ACTION", 64),
]

# ---------------------------------------------------------------------------
# Hvad der maa redigeres paa en operationslinje
# ---------------------------------------------------------------------------
# Reglerne kommer fra SAP-praksis, ikke fra appen:
#
#   Kontrolnoeglen kan kun aendres, naar arbejdet ligger paa et internt
#   arbejdscenter - *SUP eller *TECH. Der vaelges mellem ZB01 og PM01.
#   Alle andre arbejdscentre har noeglen givet af standardarbejdsplanen.
#
#   Indkoebsfelterne - leverandoer, pris og materialegruppe - skal kun
#   udfyldes ved PM02, hvor der laves en rekvisition. Ved alle andre
#   noegler staar de med standardplanens vaerdier og er skrivebeskyttede.
#
# Begge udtryk laeses pr. raekke, saa en aendring slaar igennem med det
# samme uden at nogen skal trykke noget.
CTRL_CHOICES = ("ZB01", "PM01")
# Reglen ledte foer efter "*SUP" og "*TECH" med stjerne. De navne findes
# ikke: arbejdscentrene hedder SSVSUP, AVVSUP, HEVSUP - vaerket foerst.
# Dropdownen kom derfor ALDRIG frem, og kontrolnoeglen var laast overalt.
#
# Udtraekket viser hvorfor netop SUP: det er det eneste arbejdscenter, hvor
# standardplanerne bruger baade ZB01 og PM01. De eksterne X-centre har PM03
# fast, LEV har PM02, og resten PM01.
WC_INTERNAL = 'EndsWith(Upper(Coalesce(ThisItem.MainWorkCenter, "")), "SUP")'
DM_CTRL = f'If({WC_INTERNAL}, DisplayMode.Edit, DisplayMode.View)'
IS_PM02 = 'Upper(Coalesce(ThisItem.ControlKey, "")) = "PM02"'
DM_PURCHASE = f'If({IS_PM02}, DisplayMode.Edit, DisplayMode.View)'
# PM02 UDEN BELOEB STAAR TOMT (Peter 2026-10-16): 0 vistes som et tal, man
# havde tastet. Et tomt felt med roed kant siger, at beloebet mangler; reglen
# pm02_cost i build_status holder Submit tilbage, til det er over 0.
PM02_COST = f'If({IS_PM02} && Coalesce(ThisItem.Cost, 0) = 0, Blank(), ThisItem.Cost)'

# PM03 er eksternt arbejde, og prisen i standardarbejdsplanen er en TIMESATS
# (Work staar som 1 paa hver linje, og Price er satsen: SSVXSTIL 494,
# SSVXISOL 420). Beloebet er derfor timer gange sats, og det skal foelge med,
# naar timerne rettes. De interne timer (PM01 og ZB01) har nu ogsaa en
# timesats i standardarbejdsplanen og regnes paa samme maade. Kun ved PM02
# taster man selv beloebet, saa det roeres ikke.
HOURLY_RATE = 'Upper(Trim(Coalesce(ThisItem.ControlKey, ""))) in ["PM01", "ZB01", "PM03"]'


# VAREGRUPPEN VAELGES I EN LISTE (issue #267, Peter 2026-10-16)
#
# Varegruppen paa en PM02-operation var et frit tekstfelt; saa en dropdown
# fra MD_MaterialGroup (colVhpMaterialGroups). Peter vil have, at FELTET
# kun viser koden og beholder sin bredde, mens LISTEN viser koden og
# beskrivelsen. ModernDropdown viser den samme tekst i feltet og i listen,
# saa feltet er nu en knap med koden (som leverandoeren), og den aabner en
# popup med alle varegrupperne som "kode - beskrivelse". Et klik paa en
# raekke vaelger den og lukker popup'en. Der gemmes stadig kun koden.
#
# En kode, der ikke staar i listen (fx B09.03 fra XELEK paa en PM03-linje),
# vises bare som koden i knappen.
MG_OPEN = "!IsBlank(varVhpMgOpNo)"
MG_OP = "LookUp(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpMgOpNo)"
# Popup'en lukkes - ogsaa fra sloeret (build_modal.build_modal_backdrop).
MG_CLOSE = 'Set(varVhpMgOpNo, "")'


# OP NO. KAN RETTES (Peter 2026-10-16). Operationerne staar sorteret efter
# nummeret, saa et nyt nummer flytter linjen. Nummeret er noeglen, som
# materialerne (OperationNo) og dokumenterne (OperationsKey ";0010;") kobler
# paa, saa de flyttes med. Gem finder raekken i TaskListMain paa SpId, ikke
# paa nummeret, saa en gemt operation opdateres og oprettes ikke igen.
# Nummeret skal vaere unikt pr. item: et nummer, der allerede findes, eller
# noget, der ikke er et heltal fra 1 til 9999, afvises, og feltet viser
# igen det gamle. "10" gemmes som "0010". OnChange koerer foerst, naar
# feltet forlades, ikke ved hvert tastetryk.

def docs_label(count):
    """ "Docs (n)", naar antallet er kendt; ellers "Docs" (#336)."""
    return f'With({{ n: {count} }}, If(IsBlank(n), "Docs", "Docs (" & Text(n) & ")"))'

def op_no_change(row, after=""):
    new_no = 'Text(n, "0000")'
    return (
        "With(\n"
        f"    {{ oldNo: {row}.OperationNo, raw: Trim(Self.Text) }},\n"
        "    With(\n"
        '        { n: If(IsMatch(raw, "\\d{1,4}"), Value(raw), 0) },\n'
        "        If(\n"
        "            n < 1,\n"
        '            Notify("Operation number must be a whole number from 1 to 9999.", NotificationType.Warning);\n'
        "            Reset(Self),\n"
        f"            {new_no} = oldNo,\n"
        "            Reset(Self),\n"
        f"            CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = {new_no})) > 0,\n"
        f'            Notify("Operation " & {new_no} & " already exists on this item.", NotificationType.Warning);\n'
        "            Reset(Self),\n"
        "            UpdateIf(\n"
        "                colVhpMaterials,\n"
        "                ItemId = varVhpActiveItemId && OperationNo = oldNo,\n"
        f"                {{ OperationNo: {new_no} }}\n"
        "            );\n"
        "            UpdateIf(\n"
        "                colVhpAttachments,\n"
        '                ItemId = varVhpActiveItemId && ";" & oldNo & ";" in Coalesce(OperationsKey, ";"),\n'
        f'                {{ OperationsKey: Substitute(OperationsKey, ";" & oldNo & ";", ";" & {new_no} & ";") }}\n'
        "            );\n"
        f"            Patch(colVhpOperations, {row}, {{ OperationNo: {new_no} }})"
        + (f";\n            {after}" if after else "") + "\n"
        "        )\n"
        "    )\n"
        ")"
    )


def matgrp_display(cur):
    """Koden og teksten for den varegruppe, linjen har, eller koden alene,
    naar den ikke staar i listen."""
    return f"Coalesce(LookUp(colVhpMaterialGroups, Value = {cur}).Display, {cur})"


def matgrp_button(name, op, op_no, width):
    """Varegruppens felt: en knap med koden. Paa en PM02-linje aabner den
    listen; ellers er den deaktiveret og viser standardplanens vaerdi."""
    pm02 = f'Upper(Coalesce({op}.ControlKey, "")) = "PM02"'
    v = f'Trim(Coalesce({op}.MaterialGroup, ""))'
    btn = button(
        name,
        f'If(IsBlank({v}), If({pm02}, "Select...", "-"), {v})',
        f"Set(varVhpMgOpNo, {op_no})", width=width, height=32,
        display_mode=(f"If({pm02} && !varVhpViewOnly, DisplayMode.Edit, DisplayMode.Disabled)"),
        accessible=f'"Material group for operation " & {op_no} & ": " & Coalesce({v}, "none")',
        tooltip=f'If(IsBlank({v}), "Select a material group", {matgrp_display(v)})')
    btn.props["Size"] = "12"
    # Issue #293: et almindeligt valgfelt, ikke en long text-knap - derfor
    # ingen groen "udfyldt"-kant (mark_done). Den neutrale outline-kant fra
    # button() bruges, uanset om der er valgt noget.
    return btn


def _matgrp_modal():
    """Popup'en med varegrupperne. Et klik paa en raekke skriver koden paa
    operationen og lukker; Close fortryder."""
    cur_v = f'Trim(Coalesce({MG_OP}.MaterialGroup, ""))'
    cur = text_ctrl(
        "txtVhpMgCurrent",
        f'"Current material group: " & If(IsBlank({cur_v}), "(none)", {matgrp_display(cur_v)})',
        size=12, color=C_MUTED, height=18, wrap="false")
    row_h = 36
    line = grow(text_ctrl("txtVhpMgRow", "ThisItem.Display", size=13, height=24, wrap="false"))
    row = group("conVhpMgRow", [line], direction="Horizontal", height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth",
                fill=f"If(ThisItem.Value = {cur_v}, {C_PRIMARY_SOFT}, {C_CARD_BG})",
                pad=(0, 8, 0, 8))
    hit = row_hit("btnVhpMgHit",
                  f"Patch(colVhpOperations, {MG_OP}, {{ MaterialGroup: ThisItem.Value }});\n{MG_CLOSE}",
                  '"Use material group " & ThisItem.Display', "Parent.TemplateWidth",
                  "Parent.TemplateHeight - 2")
    gal_h = f"Min(CountRows(colVhpMaterialGroups) * {row_h}, Max(160, App.Height - 220))"
    gal = Ctrl("galVhpMatGroups", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Material groups - select one to use it"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": "colVhpMaterialGroups",
        "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "2",
        "TemplateSize": str(row_h - 2), "Width": MODAL_CW, "WrapCount": "1",
    }, children=[row, hit], h=gal_h)
    return _modal("VhpMg", '"Material group · Operation " & varVhpMgOpNo', MG_OPEN,
                  MG_CLOSE, [cur, gal])


def cost_expr(work):
    return (f'If(\n'
            f'            {HOURLY_RATE},\n'
            f'            {work} * Coalesce(ThisItem.UnitCost, 0),\n'
            f'            ThisItem.Cost\n'
            f'        )')
OPS_GAP_MIN = 18
OPS_COLS_W = sum(w for _, w in OPS_COLS)
OPS_GAP = (f"Max({OPS_GAP_MIN}, Int(({OPS_CW} - 8 - {OPS_COLS_W}) / {len(OPS_COLS) - 1}))")
OPS_TABLE_W = f"({OPS_COLS_W} + {OPS_GAP} * {len(OPS_COLS) - 1})"


def _ops_header_html():
    cols = " ".join(f"{w}px" for _, w in OPS_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in OPS_COLS)
    # <style>-blokken nulstiller iframe'ens standard body-margin (den er der,
    # selvom kontrollens egen Padding er sat til 0), og det er den margin,
    # der fik HtmlViewer til at vise en (unoedvendig) scrollbar under
    # overskriften. Selve raekken er 1 px lavere end kontrollens Height, saa
    # afrundingsfejl ikke ogsaa udloeser en scrollbar.
    return (
        "\"<style>html,body{margin:0;padding:0;overflow:hidden}"
        "span{padding-left:8px;box-sizing:border-box;overflow:hidden;text-overflow:ellipsis}</style>"
        f"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:\" & {OPS_GAP} & \"px;align-items:center;height:30px;line-height:30px;overflow:hidden;"
        "border-radius:8px;background:\" & " + BG_HEX + " & \";"
        # Farven kommer fra den SAMME token som resten af appen. Foer stod
        # der "#59667A" - det rigtige tal, men uden nogen forbindelse til
        # 'text-muted'. I moerk tilstand blev overskriften staaende
        # moerkegraa paa moerk baggrund.
        "color:\" & " + MUT_HEX + " & \";font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
        f"{spans}</div>\""
    )


# ---------------------------------------------------------------------------
# Totaler
# ---------------------------------------------------------------------------
# Summerne staar i en HtmlViewer med PRAECIS samme grid som overskriften.
# En raekke almindelige kontroller ville skulle holde de tolv kolonnebredder
# ved lige for anden gang, og de gled fra hinanden sidst det blev proevet -
# det var derfor overskriften blev genereret herfra til at begynde med.
OPS_ACTIVE = "Filter(colVhpOperations, ItemId = varVhpActiveItemId)"

# Timer, antal og kroner i appens ENE talformat (layout_tokens.num_text,
# UX-review B2): "7" og "1,192" - ikke "7," og "1.192,00". Kulturen er
# givet som argument, saa separatoren ikke skifter med brugerens sprog.
_TOTALS = {
    "WORK (H)": lay.num_text(f"Sum({OPS_ACTIVE}, WorkHours)"),
    "NO.":      lay.num_text(f"Sum({OPS_ACTIVE}, Persons)"),
    "DUR. (H)": lay.num_text(f"Sum({OPS_ACTIVE}, DurationHours)"),
    "COST":     lay.num_text(f"Sum({OPS_ACTIVE}, Cost)"),
}


def _ops_totals_html():
    cols = " ".join(f"{w}px" for _, w in OPS_COLS)
    head = (
        "\"<style>html,body{margin:0;padding:0;overflow:hidden}"
        "span{overflow:hidden;text-overflow:ellipsis}</style>"
        f"<div style='display:grid;grid-template-columns:{cols};"
        f"column-gap:\" & {OPS_GAP} & \"px;align-items:center;height:23px;line-height:23px;overflow:hidden;"
        "color:\" & " + PRI_HEX + " & \";font-family:Segoe UI;font-size:12px;font-weight:700;white-space:nowrap;'>\""
    )
    parts = [head]
    for title, _ in OPS_COLS:
        if title == "OPERATION SHORT TEXT":
            parts.append("\"<span style='color:\" & " + MUT_HEX +
                         " & \";font-weight:600'>Total for this item</span>\"")
        elif title in _TOTALS:
            parts.append("\"<span>\" & " + _TOTALS[title] + " & \"</span>\"")
        else:
            parts.append("\"<span></span>\"")
    parts.append("\"</div>\"")
    return " &\n".join(parts)


# Tom tabel har ingen sum at vise - saa staar tomme-teksten der i stedet.
TOTALS_ON = ("IfError(!IsBlank(varVhpActiveItemId) && "
             f"CountRows({OPS_ACTIVE}) > 0, false)")


# ---------------------------------------------------------------------------
# Faner
# ---------------------------------------------------------------------------
# Operationerne, pakkerne, materialerne og dokumenterne hoerer alle til
# arbejdsplanen. De laa foer som to kort med hver sit trin, og der var ikke
# plads til to mere. Nu er de fire faner i eet kort.
#
# Maintenance packages vises KUN paa en strategiplan - en tidsplan har ingen
# pakker at allokere til. Materials og Attachments vises altid.
# (noegle, tekst, kort tekst, betingelse). Den korte tekst bruges, naar
# kortet er for smalt til de lange: fanerne ruller ikke (Learn).
TABS = [
    ("ops", "Operations", "Operations", None),
    ("pkg", "Maintenance packages", "Packages", IS_STRATEGY),
]


def _tab_on(key):
    return f'IfError(varVhpOpsTab = "{key}", false)'


def _tab_bar():
    """Fanerne (issue #303): EEN ModernTabList (build_helpers.tab_list) i
    stedet for to Primary/Outline-knapper. Samme variabel og vaerdier
    (varVhpOpsTab = "ops"/"pkg"); ruderne (OPS_PANE_ON/PKG_PANE_ON) laeser
    den som foer."""
    roomy = f"{OPS_CW} >= {tabs_w([t for _k, t, _s, _c in TABS])}"
    tabs = []
    for key, text, short, cond in TABS:
        fx = f'"{text}"' if text == short else f'If({roomy}, "{text}", "{short}")'
        tabs.append((key, fx) + ((f"IfError({cond}, false)",) if cond else ()))
    return tab_list("tabVhpOps", "varVhpOpsTab", tabs, label="Task list sections",
                    width=OPS_CW)


def _tab_bar_if_strategy():
    bar = _tab_bar()
    bar.vis = f"IfError({IS_STRATEGY}, false)"
    return bar


# Bliver planen lavet om fra strategi- til tidsplan, mens man staar paa
# pakkefanen, forsvinder baade knappen og ruden - og kortet ville staa tomt.
# Operationsruden overtager derfor den tilstand.
#
# Den daekker ogsaa et tredje tilfaelde: OnStart er IKKE blokerende som
# standard, saa skaermen kan naa at tegne, foer Set(varVhpOpsTab, "ops") er
# koert. Er variablen tom, ville INGEN fane vaere synlig, og kortet stod
# tomt i det oejeblik. Tom regnes derfor som "ops".
OPS_PANE_ON = (f'IfError(IsBlank(varVhpOpsTab) || {_tab_on("ops")} || '
               f'({_tab_on("pkg")} && !{IS_STRATEGY}), false)')
PKG_PANE_ON = f'IfError({_tab_on("pkg")} && {IS_STRATEGY}, false)'


# ---------------------------------------------------------------------------
# Materialer
# ---------------------------------------------------------------------------
# Description og Unit er tomme i dag. De fyldes ud af et materialeopslag mod
# SAP senere - kolonnerne staar der allerede, saa opslaget kun skal skrive i
# dem og ikke flytte rundt paa tabellen.
# OPERATION-kolonnen er vaek: materialerne vises nu pr. operation, i en
# popup fra operationens egen raekke (issue #54), saa operationen ER givet.
MAT_COLS = [("SEL", 30), ("MATERIAL", 110), ("DESCRIPTION", 230), ("QTY", 70),
            ("UNIT", 60)]
MAT_GAP = 10
MAT_TABLE_W = sum(w for _, w in MAT_COLS) + MAT_GAP * (len(MAT_COLS) - 1)
MAT_ROW_H = 34
MAT_ACTIVE = "Filter(colVhpMaterials, ItemId = varVhpActiveItemId)"
# Materialerne paa den operation, popup'en er aabnet for.
MAT_OP = ("Filter(colVhpMaterials, ItemId = varVhpActiveItemId && "
          "OperationNo = varVhpMatOpNo)")


def _mat_header_html():
    cols = " ".join(f"{w}px" for _, w in MAT_COLS)
    spans = "".join(f"<span>{t}</span>" for t, _ in MAT_COLS)
    return ("\"<style>html,body{margin:0;padding:0;overflow:hidden}</style>"
            f"<div style='display:grid;grid-template-columns:{cols};"
            f"column-gap:{MAT_GAP}px;align-items:center;height:21px;line-height:21px;"
            "overflow:hidden;color:\" & " + MUT_HEX + " & \";font-family:Segoe UI;font-size:11px;"
            f"font-weight:600;white-space:nowrap;'>{spans}</div>\"")


# Popuppens hoved: titel og X (icon_button, 44) - build_helpers.popup_head.
HEAD_H = lay.HIT_TOUCH


def _modal(name, title, open_var, close_fx, kids, width=620, scroll=False, cap=False,
           close_mode=None):
    """En popup i appens moenster (som tasklist-pickeren): centreret,
    sloer bag (build_modal.build_modal_backdrop), titel og X oeverst til
    hoejre (issue #343). scroll: titel og X staar fast, indholdet scroller.
    close_mode: X'ets DisplayMode (fx slukket midt i en gemning)."""
    t = text_ctrl(f"txt{name}Title", title, size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26,
                  wrap="false")
    head = popup_head(f"con{name}HeadRow", t, f"btn{name}Close", close_fx, mode=close_mode)
    if scroll:
        body_h = f"Max(200, App.Height - {150 + HEAD_H - 32})"
        body = group(f"con{name}Body", kids, direction="Vertical", gap=8, height=body_h,
                     overflow_y="Scroll")
        kids = [body]
    elif cap:
        kids = [du.capped_body(f"con{name}Body", kids, f"App.Height - 40 - 36 - {HEAD_H} - 12", gap=8)]
    modal = group(f"con{name}Modal", [head] + kids, direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width=f"Min({width}, App.Width - 40)",
                  drop_shadow="ExtraBold", visible=f"IfError({open_var}, false)")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "20" if scroll else "Max(20, (App.Height - Self.Height) / 3)"
    return modal


MAT_OPEN = "!IsBlank(varVhpMatOpNo)"
ATT_OPEN = "!IsBlank(varVhpAttOpNo)"
# Popup'ernes indholdsbredde: 620 minus 18 + 18.
MODAL_CW = "(Min(620, App.Width - 40) - 36)"


def _materials_modal():
    """Materialer paa EEN operation - aabnet fra operationens Materials-knap.

    Det var fanen Materials, med en OPERATION-kolonne pr. linje. Nu hoerer
    popup'en til operationen, saa en ny linje faar dens nummer, og listen
    viser kun dens linjer (issue #54). Linjerne er de samme i
    colVhpMaterials, og gemningen er uaendret."""
    w = {t: wd for t, wd in MAT_COLS}

    btnAdd = button(
        "btnVhpAddMaterial", '"Add material"',
        (
            "Collect(\n"
            "    colVhpMaterials,\n"
            "    {\n"
            "        ItemId: varVhpActiveItemId,\n"
            # LineId er unik pr. ITEM, ikke pr. operation.
            f"        LineId: Coalesce(Max({MAT_ACTIVE}, LineId), 0) + 1,\n"
            "        MaterialNo: \"\",\n"
            "        Description: \"\",\n"
            "        Unit: \"\",\n"
            "        Quantity: 1,\n"
            "        OperationNo: varVhpMatOpNo,\n"
            "        Selected: false\n"
            "    }\n"
            ");\n"
            "Notify(\"Material line added.\", NotificationType.Success)"
        ), primary=True, width=fit_button_width('"Add material"'))

    btnRemove = button(
        "btnVhpRemoveMaterial", '"Remove material"',
        (
            "RemoveIf(colVhpMaterials, ItemId = varVhpActiveItemId, "
            "OperationNo = varVhpMatOpNo, Selected = true);\n"
            "Notify(\"Removed the selected material lines.\", NotificationType.Success)"
        ), danger=True, width=fit_button_width('"Remove material"'),
        display_mode=(f"If(CountRows(Filter({MAT_OP}, Selected = true)) = 0, "
                      "DisplayMode.Disabled, DisplayMode.Edit)"))

    actions = group("conVhpMatActions", [btnAdd, btnRemove], direction="Horizontal", gap=8,
                    height=36, align_items="Center")

    header = Ctrl("htmVhpMatHeader", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": _mat_header_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(MAT_TABLE_W),
    }, h=22)
    divider = group("conVhpMatDivider", [], height=1, fill=C_DIVIDER,
                    direction="Horizontal", width=str(MAT_TABLE_W))

    chkSel = Ctrl("chkVhpMatSel", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Select material line"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colVhpMaterials, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colVhpMaterials, ThisItem, { Selected: false })",
        "Width": str(w["SEL"]),
    }), h=24)
    txtNo = text_input("inpVhpMatNo", "ThisItem.MaterialNo", width=w["MATERIAL"], height=30,
                       onchange="Patch(colVhpMaterials, ThisItem, { MaterialNo: Self.Text })", label="\"Material number\"")
    # Kommer fra materialeopslaget, ikke fra brugeren.
    txtDesc = text_ctrl("txtVhpMatDesc",
                        'If(IsBlank(ThisItem.Description), "-", ThisItem.Description)',
                        size=12, color=C_MUTED, height=30, width=w["DESCRIPTION"], wrap="false")
    numQty = number_field("inpVhpMatQty", "ThisItem.Quantity", width=w["QTY"], height=30,
                          label="\"Quantity\"",
                          onchange=f"Patch(colVhpMaterials, ThisItem, {{ Quantity: {NV} }})")
    txtUnit = text_ctrl("txtVhpMatUnit",
                        'If(IsBlank(ThisItem.Unit), "-", ThisItem.Unit)',
                        size=12, color=C_MUTED, height=30, width=w["UNIT"], wrap="false")

    row = group("conVhpMatRow", pin_widths([chkSel, txtNo, txtDesc, numQty, txtUnit]),
                direction="Horizontal", gap=MAT_GAP, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    MAT_ROWS = 7
    gal_h = MAT_ROWS * (MAT_ROW_H + 2)
    gallery = Ctrl("galVhpMaterials", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Materials for this operation"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": str(gal_h),
        "Items": f"Sort({MAT_OP}, LineId)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(MAT_ROW_H),
        "Width": str(MAT_TABLE_W + 4 + SCROLLBAR_W),
        "WrapCount": "1",
    }, children=[row], h=gal_h)
    # Neutral flade og een streg pr. raekke - ikke graat fyld (issue #78).
    table_surface(gallery, "rctVhpMatRule")

    # Tom tilstand (UX-review F4) - knappen Add material staar lige over.
    empty = empty_state("conVhpMatEmpty",
                        '"No materials on this operation yet - choose Add material."',
                        icon_path=icons.MATERIAL,
                        visible=f"IfError(CountRows({MAT_OP}) = 0, false)")

    note = text_ctrl("txtVhpMatNote",
                     '"Description and unit are filled in by the material lookup. '
                     'Until it is in place they stay empty."',
                     size=12, color=C_MUTED, height=32, wrap="true")

    # Start, ikke Stretch: tabellen har sin egen bredde og scroller vandret
    # paa en smal skaerm i stedet for at blive klemt sammen.
    table = group("conVhpMatTableWrap", [header, divider, gallery, empty],
                  direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                  align_items="Start")

    return _modal("VhpMat", '"Materials - operation " & varVhpMatOpNo', MAT_OPEN,
                  'Set(varVhpMatOpNo, "")', [actions, note, table], cap=True)


# ---------------------------------------------------------------------------
# Dokumenter
# ---------------------------------------------------------------------------
# Dokumenterne er SharePoint-vedhaeftninger paa OPERATIONENS raekke i
# TaskListMain (issue #300, build_attflows.py). Den moderne Attachments-
# kontrol er bundet til raekkens Attachments og viser, aabner og fjerner
# selv filerne; "Save documents" gemmer dem med een Patch.
#
# De aeldre dokumentraekker i MD_TasklistAttachment (colVhpAttachments,
# OperationsKey ";0010;0020;") hentes og gemmes som foer, saa gemningen
# ikke sletter dem - men de vises ikke i ruden.


# Maa der laegges op og fjernes? Ikke i View-tilstand (issue #134).
# Sektionen klappes ikke laengere sammen (issue #192), saa der er ingen
# laast tilstand ud over View.
def _att_edit():
    return "(!IfError(varVhpViewOnly, false))"


# Luk dokumentpopuppen: glem de valgte, ikke gemte aendringer og raekken.
ATT_CLOSE = 'Set(varVhpAttOpNo, "");\n' + att.close_fx()


def _attachments_modal():
    """Dokumenter for EEN operation - aabnet fra operationens Docs-knap.

    Opbygningen (issue #134, #300) er den faelles i tools/doc_upload.py:
    den moderne Attachments-kontrol paa operationens raekke og een
    "Save documents". En operation, der ikke er gemt endnu, har ingen
    raekke - saa er kontrollen spaerret, og teksten siger hvorfor."""
    edit = _att_edit()
    pick = du.picker(att.picker, '"Documents for operation " & varVhpAttOpNo', 10, 10,
                     att.items, display_mode=du.picker_mode(att, edit))
    limits = du.limits_text("txtVhpAttLimits", 10, 10, visible=edit)
    not_saved = du.not_saved_text("txtVhpAttNotSaved", att, visible=edit)
    btnSave = du.save_button("btnVhpAttUpload", att, visible=edit)
    actions = group("conVhpAttActions", [btnSave],
                    direction="Horizontal", gap=8, height=36, justify="End",
                    align_items="Center", visible=edit)
    status = du.status_text("txtVhpAttStatus", att)
    ro = du.readonly_note("txtVhpAttReadOnly", f"!{edit}")

    # Popuppen: 20 + 20 luft til skaermkanten, 18 + 18 polstring, hovedet
    # (HEAD_H) og afstanden (12) - resten er indholdet.
    body = du.capped_body("conVhpAttBody",
                          [pick, limits, not_saved, actions, status, ro],
                          f"App.Height - 40 - 36 - {HEAD_H} - 12")
    # Kontrollen fylder den plads, popuppen har tilbage (issue #344).
    du.fit_picker(pick, body.children, 12)
    # X er den eneste vej ud - men ikke midt i en gemning.
    return _modal("VhpAtt", '"Documents · Operation " & varVhpAttOpNo', ATT_OPEN,
                  ATT_CLOSE, [body],
                  close_mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")


# ---------------------------------------------------------------------------
# LEVERANDOERSOEGNING PAA PM02-OPERATIONER
# ---------------------------------------------------------------------------
# Leverandoeren SOEGES frem med flowet BioSap-Integration-VendorsAll i en
# popup - samme vaelger som Functional Location paa items (tools/fl_picker.py,
# tools/vendor_search.py). Cellen i tabellen er en knap med den valgte
# leverandoer; et tryk aabner popup'en. Kun PM02-linjer kan aendres (reglen
# DM_PURCHASE ovenfor); paa de andre linjer staar standardplanens vaerdi.
VEN_OPEN = "!IsBlank(varVhpVenOpNo)"
VEN_OP = "LookUp(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpVenOpNo)"
VEN_COMBO = "cmbVhpVendor"
VEN_RESULTS = "colVhpVendors"
VEN_BUSY = "varVhpVenBusy"
VEN_QUERY = "varVhpVenQuery"
VEN_LAST = "varVhpVenLast"
VEN_PICK = "varVhpVenPick"
VEN_MSG = "varVhpVenMsg"
VEN_RAW = "varVhpVenRaw"
# Popup'en lukkes - ogsaa fra sloeret (build_modal.build_modal_backdrop).
VEN_CLOSE = 'Set(varVhpVenOpNo, "")'


def _ven_open_fx(op, op_no):
    """Aabn popup'en for operationen op (record-udtryk) med nummeret op_no.
    Den gemte leverandoer laegges i listen og staar valgt, saa man kan se,
    hvad der er nu; en ny soegning rydder den."""
    return (
        f"With(\n"
        f"    {{ v: Trim(Coalesce({op}.Vendor, \"\")) }},\n"
        f"    Set(varVhpVenOpNo, {op_no});\n"
        f"    Set({VEN_QUERY}, \"\"); Set({VEN_LAST}, \"\"); Set({VEN_MSG}, \"\");\n"
        f"    Clear({VEN_RESULTS});\n"
        f"    If(!IsBlank(v), Collect({VEN_RESULTS}, {{ Code: v, Description: v, Display: v, "
        f"Maintainable: true, Level: \"\" }}));\n"
        f"    Set({VEN_PICK}, v);\n"
        f"    Reset({VEN_COMBO})\n"
        f")"
    )


def vendor_button(name, op, op_no, width, chars=12):
    """Leverandoerens felt: en knap med den valgte leverandoer. Paa en
    PM02-linje aabner den soegningen; ellers er den deaktiveret og viser
    standardplanens vaerdi."""
    pm02 = f'Upper(Coalesce({op}.ControlKey, "")) = "PM02"'
    v = f'Trim(Coalesce({op}.Vendor, ""))'
    btn = button(
        name,
        # Feltet viser kun nummeret (Peter 2026-10-16); navnet staar i
        # tooltip'en og i popup'ens liste. Der gemmes stadig "nummer - navn".
        (f'If(IsBlank({v}), If({pm02}, "Search...", "-"), '
         f'With({{ n: Trim(First(Split({v}, " - ")).Value) }}, '
         f'Left(n, {chars}) & If(Len(n) > {chars}, "...")))'),
        _ven_open_fx(op, op_no), width=width, height=32,
        display_mode=(f"If({pm02} && !varVhpViewOnly, DisplayMode.Edit, DisplayMode.Disabled)"),
        accessible=f'"Vendor for operation " & {op_no} & ": " & Coalesce({v}, "none")',
        tooltip=f'If(IsBlank({v}), "Search for a vendor", {v})')
    btn.props["Size"] = "12"
    # Issue #293: neutral kant som et almindeligt valgfelt (ingen mark_done).
    return btn


def _vendor_modal():
    """Popup'en med leverandoersoegningen. "Use vendor" skriver det valgte
    paa operationen; Close fortryder. "Remove vendor" toemmer feltet."""
    edit = "If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)"
    cur = text_ctrl(
        "txtVhpVenCurrent",
        f'"Current vendor: " & Coalesce(Trim(Coalesce({VEN_OP}.Vendor, "")), "(none)")',
        size=12, color=C_MUTED, height=18, wrap="false")
    picker = fl_picker(
        "Vhp", combo=VEN_COMBO, results=VEN_RESULTS, raw_var=VEN_RAW,
        msg_var=VEN_MSG, busy_var=VEN_BUSY, query_var=VEN_QUERY,
        last_var=VEN_LAST, pick_var=VEN_PICK,
        default_items=f"Filter({VEN_RESULTS}, Code = {VEN_PICK})",
        display_mode=edit, label="Vendor", width=MODAL_CW,
        min_len=vs.MIN_SEARCH_LEN, kind="Ven", searcher=vs.search_action,
        placeholder=vs.PLACEHOLDER, search_accessible='"Search vendor"')
    msg = text_ctrl("txtVhpVenMsg", VEN_MSG, size=12, color=C_MUTED, height=32,
                    wrap="true", visible=f"!IsBlank({VEN_MSG})")
    sel = f"{VEN_COMBO}.Selected.Code"
    use = button(
        "btnVhpVenUse", '"Use vendor"',
        f"Patch(colVhpOperations, {VEN_OP}, {{ Vendor: {sel} }});\n{VEN_CLOSE}",
        primary=True, width=fit_button_width('"Use vendor"'), height=32,
        display_mode=(f'If(varVhpViewOnly || {VEN_BUSY} || IsBlank({sel}) || '
                      f'{sel} = "?search", DisplayMode.Disabled, DisplayMode.Edit)'))
    remove = button(
        "btnVhpVenRemove", '"Remove vendor"',
        f'Patch(colVhpOperations, {VEN_OP}, {{ Vendor: \"\" }});\n{VEN_CLOSE}',
        danger=True, width=fit_button_width('"Remove vendor"'), height=32,
        display_mode=(f'If(varVhpViewOnly || {VEN_BUSY} || IsBlank(Trim(Coalesce({VEN_OP}.Vendor, ""))), '
                      'DisplayMode.Disabled, DisplayMode.Edit)'))
    actions = flow_row("conVhpVenActions", [use, remove], MODAL_CW, gap=8)
    return _modal("VhpVen", '"Vendor · Operation " & varVhpVenOpNo', VEN_OPEN,
                  VEN_CLOSE, [cur, picker, msg, actions])


OPM_OPEN = "!IsBlank(varVhpOpMNo)"
OPM = "LookUp(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo)"


def _op_detail_modal():
    """En operationslinje i en popup - kun i smalle skaerme, hvor tabellen
    med femten kolonner ikke kan laeses. Samme felter som tabellens vigtigste
    kolonner, og de samme Patch-formler paa samme samling."""
    def label(name, text):
        return text_ctrl(f"txtVhpOpM{name}", f'"{text}"', size=12, color=C_MUTED,
                         height=18, wrap="false")

    opno = text_input("inpVhpOpMNo", f"{OPM}.OperationNo", width=MODAL_CW, height=32, max_length=4,
                      onchange=op_no_change(OPM, 'Set(varVhpOpMNo, Text(n, "0000"))'),
                      label='"Operation number"')
    # SAP's LTXA1 er 40 tegn (schema/vhplan-sap-order.schema.json, R2-009).
    short = text_input("inpVhpOpMText", f"{OPM}.OperationShortText", width=MODAL_CW, height=32,
                       max_length=40,
                       onchange=f"Patch(colVhpOperations, {OPM}, {{ OperationShortText: Self.Text }})",
                       label='"Operation text"')
    cost = cost_expr(NV).replace("ThisItem", "r")
    work = number_field("inpVhpOpMWork", f"{OPM}.WorkHours", width=MODAL_CW, height=32,
                        label='"Work hours"', unit="h", onchange=(
        "With(\n    { r: " + OPM + " },\n    Patch(\n        colVhpOperations, r,\n"
        f"        {{\n            WorkHours: {NV},\n"
        f"            DurationHours: {cfg.duration_expr(NV, 'r.Persons')},\n"
        f"            Cost: {cost}\n        }}\n    )\n)"))
    persons = number_field("inpVhpOpMPersons", f"{OPM}.Persons", width=MODAL_CW, height=32,
                           label='"Number of people"', unit="people", onchange=(
        "With(\n    { r: " + OPM + " },\n    Patch(\n        colVhpOperations, r,\n"
        f"        {{\n            Persons: {NV},\n"
        f"            DurationHours: {cfg.duration_expr('r.WorkHours', NV)}\n        }}\n    )\n)"))
    dur = text_ctrl("txtVhpOpMDur",
                    f'"Duration: " & {lay.num_text(OPM + ".DurationHours")} & " h   Work center: " & '
                    f'Coalesce({OPM}.MainWorkCenter, "-")', size=13, color=C_MUTED, height=20,
                    wrap="false")
    mats = button("btnVhpOpMMat", f'"Materials (" & Text(CountRows(Filter(colVhpMaterials, ItemId = varVhpActiveItemId && '
                  f'OperationNo = varVhpOpMNo))) & ")"', "Set(varVhpMatOpNo, varVhpOpMNo)",
                  width=fit_button_width('"Materials (00)"'), height=32)
    docs = button("btnVhpOpMDocs", docs_label(f"{OPM}.FileCount"),
                  att.open_fx("varVhpOpMNo"),
                  width=fit_button_width('"Docs (00)"'), height=32)
    rem = button("btnVhpOpMRemove", '"Remove"',
                 "RemoveIf(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo);\n"
                 'Set(varVhpOpMNo, "")', danger=True, width=fit_button_width('"Remove"'), height=32)
    actions = flow_row("conVhpOpMActions", [mats, docs, rem], MODAL_CW, gap=8)

    on_op = lambda s: s.replace("ThisItem", OPM)
    ctrl_items = ("Filter(Distinct(Table("
                  + ", ".join('{ Value: "%s" }' % c for c in CTRL_CHOICES)
                  + f', {{ Value: Coalesce({OPM}.ControlKey, "") }}), Value), !IsBlank(Value))')
    ctrl = themed_dropdown("drpVhpOpMCtrl", ctrl_items,
                           f"LookUp({ctrl_items}, Value = {OPM}.ControlKey).Value",
                           width=MODAL_CW, height=32, display_mode=on_op(DM_CTRL),
                           label='"Control key"')
    ctrl.props["OnChange"] = (f"Patch(colVhpOperations, {OPM}, "
                              "{ ControlKey: Self.Selected.Value })")
    vendor = vendor_button("btnVhpOpMVendor", OPM, "varVhpOpMNo", MODAL_CW, chars=40)
    price = number_field("inpVhpOpMCost", on_op(PM02_COST), width=MODAL_CW, height=32,
                         required_formula=on_op(IS_PM02),
                         display_mode=on_op(DM_PURCHASE), label='"Price"',
                         onchange=f"Patch(colVhpOperations, {OPM}, {{ Cost: {NV} }})")
    matgrp = matgrp_button("btnVhpOpMMatGrp", OPM, "varVhpOpMNo", MODAL_CW)
    longtext = button(
        "btnVhpOpMLongText",
        (f'If(IsBlank(Trim(Coalesce({OPM}.LongText, ""))), "Add text...", '
         f'Left({OPM}.LongText, 24) & If(Len({OPM}.LongText) > 24, "..."))'),
        ('Set(varVhpLongTextTarget, "op");\n'
         'Set(varVhpLongTextItemId, varVhpActiveItemId);\n'
         'Set(varVhpLongTextOpNo, varVhpOpMNo);\n'
         f'Set(varVhpLongTextDraft, Coalesce({OPM}.LongText, ""));\n'
         'Reset(inpVhpLongTextBox);\n'
         'Set(varVhpLongTextOpen, true)'),
        width=MODAL_CW, height=32, icon="DocumentText",
        accessible='"Edit long text for operation " & varVhpOpMNo')
    # Samme piller som i tabellens raekke (build_strategy.pkg_pills).
    m_pills = f"({IS_STRATEGY} && {HAS_PKGS})"
    packages_txt = text_ctrl(
        "txtVhpOpMPackages",
        'If(varVhpPlan.PlanType <> "Strategy", "-", "(no packages)")',
        size=13, height=20, wrap="false", visible=f"!{m_pills}")
    packages_gal = pkg_pills("VhpOpM", "varVhpOpMNo", f"{OPM}.PackagesKey")
    packages_gal.props["Visible"] = m_pills
    packages_gal.vis = m_pills
    packages = group("conVhpOpMPackages", [packages_txt, packages_gal], direction="Vertical", gap=0)
    return _modal("VhpOpM", '"Operation " & varVhpOpMNo', OPM_OPEN, 'Set(varVhpOpMNo, "")',
                  [label("L0", "Operation no."), opno, label("L1", "Short text"), short, label("L2", "Work (h)"), work,
                   label("L3", "Number of people"), persons, dur,
                   label("L4", "Control key"), ctrl, label("L5", "Supplier"), vendor,
                   label("L6", "Price"), price, label("L7", "Material group"), matgrp,
                   label("L8", "Long text"), longtext, label("L9", "Packages"), packages,
                   actions], scroll=True)


def _ops_list_mobile():
    """Operationerne som en liste af knapper under Tablet: en linje pr.
    operation, et tryk aabner popup'en."""
    n_ops = "CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))"
    has_ops = f"IfError(!IsBlank(varVhpActiveItemId) && {n_ops} > 0, false)"
    row_h = 46
    line = grow(text_ctrl(
        "txtVhpOpMRow",
        'ThisItem.OperationNo & "  \u00b7  " & Coalesce(ThisItem.OperationShortText, "") & "  \u00b7  " & '
        + lay.num_text("ThisItem.WorkHours") + ' & " h"',
        size=13, height=24, wrap="false"))
    chev = text_ctrl("txtVhpOpMChev", '"\u203a"', size=lay.SIZE_CARD_TITLE, color=C_MUTED, height=24, width=16,
                     wrap="false")
    row = group("conVhpOpMRow", [line, chev], direction="Horizontal", gap=8,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth", fill=C_CARD_BG, pad=(0, 8, 0, 8))
    hit = row_hit("btnVhpOpMHit", "Set(varVhpOpMNo, ThisItem.OperationNo)",
                  '"Open operation " & ThisItem.OperationNo', "Parent.TemplateWidth",
                  "Parent.TemplateHeight - 2")
    vis = f"{has_ops} && {below('Tablet')}"
    gal_h = f"{n_ops} * {row_h}"
    gal = Ctrl("galVhpOpsM", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Operations - select one to open it"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h,
        "Items": "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
        "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "2",
        "TemplateSize": str(row_h - 2), "Visible": vis, "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row, hit], h=gal_h, vis=vis)
    return gal


def build_ops_modals():
    """Popupperne fra operationsraekkens Materials- og Docs-knapper."""
    # Leverandoerpopup'en SIDST: den kan aabnes fra operationspopup'en
    # (smalle skaerme) og skal ligge oven paa den. Det samme for varegruppens.
    return [_op_detail_modal(), _materials_modal(), _attachments_modal(), _vendor_modal(),
            _matgrp_modal()]


# Tasklisterne til det valgte vaerk - Plant i Plan Header er den faelles
# kontekst (issue #54). Upper paa begge sider, saa store og smaa bogstaver
# ikke skjuler en gyldig liste.
TL_ITEMS = "Filter(colVhpTasklists, Upper(Plant) = Upper(varVhpPlan.Plant))"

# FOERSTE TASKLIST VAELGES AUTOMATISK (issue #158). drpVhpItemTasklist har
# ingen egen tilstand: Default slaar itemets TasklistKey op i colVhpItems,
# og det er det felt, et manuelt valg (OnChange), Lines from tasklist,
# Save og trin 3 laeser. Det automatiske valg skriver derfor det samme
# felt - ikke en ekstra variabel ved siden af - og kun naar itemet har en
# Functional Location (er gemt), og dets tasklist er tom eller ikke
# laengere findes i listen. Et gemt eller manuelt valg, der stadig er
# gyldigt, roeres aldrig. TL_ITEMS er den navngivne formel, dropdownen
# selv viser - den hentes een gang og caches, saa her er intet nyt kald
# mod SharePoint. Betingelsen staar uden om With, saa et nyt, tomt item
# (Add item, Copy item) slet ikke evaluerer listen. Ingen tasklist: intet
# skrives, og den tomme tilstand bevares.
AUTO_SELECT_TL = (
    "With({ tlIt: LookUp(colVhpItems, ItemId = varVhpActiveItemId) }, "
    "If(!varVhpViewOnly && !IsBlank(tlIt.FunctionalLocation) && "
    f"(IsBlank(tlIt.TasklistKey) || IsBlank(LookUp({TL_ITEMS}, Key = tlIt.TasklistKey).Key)), "
    f"With({{ tlFirst: First({TL_ITEMS}) }}, If(!IsBlank(tlFirst.Key), "
    "UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, "
    "{ TasklistKey: tlFirst.Key, TasklistName: tlFirst.Name }); "
    "Reset(drpVhpItemTasklist)))))"
)
OPS_SELECTED = "Filter(colVhpOperations, ItemId = varVhpActiveItemId, Selected = true)"

# Hvad der mangler, foer sektionen kan gemmes - tom, naar
# intet mangler. Trin 3 og 4 (build_status) for det aktive item; pakke-
# reglen er S4 og bruger den samme HAS_PKGS.
OPS_ISSUE = (
    "If(\n"
    "    IsBlank(drpVhpItemTasklist.Selected.Key), \"Choose a task list.\",\n"
    f"    CountRows({OPS_ACTIVE}) = 0, \"Add at least one operation.\",\n"
    f"    {IS_STRATEGY} && {HAS_PKGS} &&\n"
    f"        CountRows(Filter({OPS_ACTIVE}, Len(Coalesce(PackagesKey, \";\")) <= 1)) > 0,\n"
    "    \"Give every operation a package.\",\n"
    "    \"\"\n"
    ")")


def build_tasklist_section():
    # Trin-badget (issue #123): "Valid", naar alle items har tasklist og
    # operationer, og ingen tasklist-/operationsregel fejler.
    header = section_header("conVhpOpsHead", "Task list and operations", "Step 3",
                            valid_fx="VhpOpsValid")
    helpPanel = help_panel("conVhpOpsHelp", "ops")

    # Default slaar op i den FILTREREDE liste: en tasklist fra et andet
    # vaerk vises som tom, naar vaerket er skiftet, i stedet for som et
    # gyldigt valg.
    drpTasklist = themed_dropdown(
        "drpVhpItemTasklist", TL_ITEMS,
        f"LookUp({TL_ITEMS}, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey).Name",
        display_mode=DM_ITEM, value_col="Key", display_col="Name")
    # Valget ER stadig handlingen - OnChange skriver listen paa itemet. Apply
    # Tasklist nedenfor goer det samme, for den, der leder efter en knap.
    #
    # Betingelsen er ikke pynt. Skift af item koerer Reset(drpVhpItemTasklist)
    # (build_items.py), og en Reset kan udloese OnChange. Det goer et
    # skift af vaerk ogsaa - og saa er Selected TOM, fordi itemets liste
    # hoerer til det gamle vaerk. !IsBlank(Self.Selected.Key) sikrer, at et
    # vaerksskift aldrig sletter itemets gemte tasklist. Uden
    # sammenligningen ville det skrive den FORRIGE liste paa det NYE item.
    # Efter en Reset er Selected lig med itemets egen vaerdi, saa
    # betingelsen er falsk og OnChange en ren nulhandling.
    APPLY_TL = (
        "UpdateIf(\n"
        "    colVhpItems, ItemId = varVhpActiveItemId,\n"
        "    { TasklistKey: drpVhpItemTasklist.Selected.Key, TasklistName: drpVhpItemTasklist.Selected.Name }\n"
        ");\n"
        "Notify(\"Task list \" & drpVhpItemTasklist.Selected.Key & \" selected for this item.\", NotificationType.Success)")
    drpTasklist.props["OnChange"] = (
        "If(\n"
        "    !IsBlank(varVhpActiveItemId) && !IsBlank(Self.Selected.Key) &&\n"
        "        Self.Selected.Key <> LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey,\n"
        + APPLY_TL.replace("\n", "\n    ").join(["    ", "\n"]) +
        ")")
    # Tasklist-feltet har en fast, begraenset bredde og staar til venstre.
    TL_W = fits(OPS_CW, TWO_COL_MIN, OPS_CW, "360")
    tasklistCell = field_cell("conVhpCellTasklist", "Task list", drpTasklist, required=True,
                              width=TL_W, container_w=OPS_CW, fill_portions_formula="0")

    btnAddLines = button(
        "btnVhpAddTasklistLines", "\"Add lines from task list\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        Notify(\"Select a task list first.\", NotificationType.Warning),\n"
            "        Clear(colVhpPickerSelected);\n"
            "        Reset(inpVhpPickerSearch);\n"
            "        Set(varVhpTasklistPickerOpen, true)\n"
            "    )\n"
            ")"
        # Sekundaer outline som Manual operation (issue #157): Save er
        # sektionens eneste primaere, blaa handling.
        ), display_mode=DM_ITEM, icon="Add",
        accessible="\"Add lines from the task list\"",
        tooltip="\"Add operation lines from the selected task list\"")

    btnAddOp = button(
        "btnVhpAddOperation", "\"Manual operation\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    Collect(\n"
            "        colVhpOperations,\n"
            "        {\n"
            "            ItemId: varVhpActiveItemId,\n"
            f"            OperationNo: Text({NEXT_OP_BASE} + 10, \"0000\"),\n"
            "            OperationShortText: \"\",\n"
            "            WorkHours: 1,\n"
            "            Persons: 1,\n"
            "            DurationHours: 1,\n"
            "            MainWorkCenter: \"\",\n"
            "            ControlKey: \"\",\n"
            "            Vendor: \"\",\n"
            "            Cost: 0,\n"
            "            Currency: \"\",\n"
            "            CostElement: 0,\n"
            "            MaterialGroup: \"\",\n"
            "            ServiceNo: \"\",\n"
            "            LongText: \"\",\n"
            "            PackagesKey: \";\",\n"
            "            Selected: false\n"
            "        }\n"
            "    );\n"
            "    Notify(\"Operation line added.\", NotificationType.Success)\n"
            ")"
        ), display_mode=DM_ITEM, icon="Add",
        accessible="\"Add a manual operation\"",
        tooltip="\"Add an empty operation line you fill in yourself\"")

    # The two row-creating buttons stand right after the tasklist field,
    # bottom-aligned with its dropdown while they share a line.
    add_btns = [btnAddLines, btnAddOp]
    for b in add_btns:
        b.props["Width"] = str(fit_button_width(b.props["Text"]) + ICON_W)
        b.props["LayoutMinWidth"] = b.props["Width"]
        b.vis = at_least("Tablet")
    opsMenu = themed_dropdown(
        "drpVhpOpsActions",
        'Table({ Value: "Add lines from task list" }, { Value: "Add manual operation" })',
        '""', width="190", height=36, label='"Task list actions"',
        onchange=(
            "Switch(\n"
            "    Self.Selected.Value,\n"
            f"    \"Add lines from task list\", {btnAddLines.props['OnSelect']},\n"
            f"    \"Add manual operation\", {btnAddOp.props['OnSelect']}\n"
            ");\nReset(Self)"))
    opsMenu.props["LayoutMinWidth"] = "190"
    opsMenu.vis = below("Tablet")
    opsMenu.props["Visible"] = below("Tablet")
    tb_kids = [tasklistCell, btnAddLines, btnAddOp, opsMenu]
    on_line = flow_ok(tb_kids, OPS_CW, 12)
    for b in add_btns + [opsMenu]:
        b.props["AlignInContainer"] = f"If({on_line}, AlignInContainer.End, AlignInContainer.Start)"
    toolbar = flow_row("conVhpOpsToolbar", tb_kids, OPS_CW, gap=12)

    # Reset (kun dropdownen tilbage) er fjernet (UX-review): task listen
    # vaelges bare om. Sektionen afsluttes med Done (beslutning 1a,
    # 2026-10-13): kun Save draft skriver til SharePoint.
    btnTlSave = button(
        "btnVhpTasklistSave", "\"Done\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    IsBlank(drpVhpItemTasklist.Selected.Key),\n"
            "    Notify(\"Select a task list first.\", NotificationType.Warning),\n"
            # Ufuldstaendig sektion: gem ikke (issue #103).
            "    With(\n"
            "        { issue: " + OPS_ISSUE.replace("\n", "\n        ") + " },\n"
            "        If(\n"
            "            !IsBlank(issue),\n"
            "            Notify(issue, NotificationType.Warning),\n"
            "            UpdateIf(\n"
            "                colVhpItems, ItemId = varVhpActiveItemId,\n"
            "                { TasklistKey: drpVhpItemTasklist.Selected.Key, TasklistName: drpVhpItemTasklist.Selected.Name }\n"
            "            );\n"
            "            Notify(\"Task list done. Save draft to keep it.\", NotificationType.Success)\n"
            "        )\n"
            "    )\n"
            ")"
        ), primary=True, icon='"Checkmark"',
        width=fit_button_width("\"Done\"", min_w=96) + ICON_W, height=36,
        display_mode=("If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, "
                      "btnVhpSaveDraft.DisplayMode)"))
    btnTlSave.props["AccessibleLabel"] = '"Done with the task list and operations"'

    # ALTID FOLDET UD (issue #192): fanerne og ruderne staar der altid.
    # Foden siger, hvad der mangler, foer sektionen kan gemmes.
    attention = text_ctrl(
        "txtVhpOpsAttention",
        f'With({{ issue: {OPS_ISSUE} }}, If(IsBlank(issue), "Ready to save.", issue))',
        size=12, height=36, wrap="true",
        visible="(!IsBlank(varVhpActiveItemId) && !varVhpViewOnly)",
        extra={"Color": f"If(IsBlank({OPS_ISSUE}), {C_MUTED}, {C_INVALID_FG})",
               "VerticalAlign": "VerticalAlign.Middle"})
    footerInfo = group("conVhpOpsFooterInfo", [attention], direction="Vertical", gap=0,
                       justify="Center", visible=attention.vis)
    opsFooter = section_footer("conVhpOpsFooter", footerInfo, [btnTlSave], OPS_CW)

    tasklistMeta = text_ctrl(
        "txtVhpTasklistMeta",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId), \"Select an item to manage its task list and operations.\",\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        \"No task list linked yet.\",\n"
            "        \"Tasklist \" & LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistName & \" linked. \" &\n"
            "        " + dt.plural("CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))", "operation") + " & \" on this item.\"\n"
            "    )\n"
            ")"
        ), size=12, color=C_MUTED, height=18, wrap="true")

    # Operationerne redigeres i et galleri, saa der er ingen field_cell at
    # haenge en hint paa. Den staar i stedet over tabellen og daekker linjen.
    opsHint = text_ctrl("txtVhpOpsHint", bh.hint("Operations"), size=12, color=C_MUTED,
                        height=32, wrap="true",
                        visible="IfError(varVhpShowHints && !IsBlank(varVhpActiveItemId), false)")

    opsHeader = Ctrl("htmVhpOpsHeader", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "34", "HtmlText": _ops_header_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(OPS_TABLE_W),
    }, h=34)
    opsDivider = group("conVhpOpsDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal",
                       width=str(OPS_TABLE_W))

    # -- row template ---------------------------------------------------------
    w = {t: wd for t, wd in OPS_COLS}
    btnOpDel = button(
        "btnVhpOpDelete", '"Delete"',
        (
            "RemoveIf(colVhpMaterials, ItemId = ThisItem.ItemId && OperationNo = ThisItem.OperationNo);\n"
            "RemoveIf(colVhpOperations, ItemId = ThisItem.ItemId && OperationNo = ThisItem.OperationNo);\n"
            "Notify(\"Operation line removed.\", NotificationType.Success)"
        ),
        danger=True, width=40, height=32, icon="Delete", display_mode=DM_ITEM,
        accessible='"Delete operation " & ThisItem.OperationNo')
    btnOpDel.props["Layout"] = "ButtonLayout.IconOnly"
    btnOpDel.props["Tooltip"] = '"Delete operation line"'
    ensure_hit(btnOpDel)               # H.hit (UX-review F6, regel 40)
    txtOpNo = text_input("inpVhpOpNo", "ThisItem.OperationNo", width=w["OP NO."], height=32,
                         max_length=4, onchange=op_no_change("ThisItem"),
                         label='"Operation number " & ThisItem.OperationNo')
    txtOpShort = text_input("inpVhpOpShortText", "ThisItem.OperationShortText", width=w["OPERATION SHORT TEXT"],
                            height=32, max_length=40,   # SAP's LTXA1 (R2-009)
                            onchange="Patch(colVhpOperations, ThisItem, { OperationShortText: Self.Text })", label="\"Operation text\"")
    # Work og No. skriver BEGGE varigheden, fordi den er regnet af dem
    # begge. Gjorde kun den ene det, ville et skift i den anden efterlade en
    # varighed, der ikke passer til linjen - og det er varigheden, der
    # gemmes i TaskListMain.Duration og sendes videre til SAP.
    numOpWork = number_field("inpVhpOpWork", "ThisItem.WorkHours", width=w["WORK (H)"], height=32,
                             label="\"Work hours\"", onchange=(
        "Patch(\n"
        "    colVhpOperations, ThisItem,\n"
        "    {\n"
        f"        WorkHours: {NV},\n"
        f"        DurationHours: {cfg.duration_expr(NV, 'ThisItem.Persons')},\n"
        f"        Cost: {cost_expr(NV)}\n"
        "    }\n"
        ")"))
    numOpPersons = number_field("inpVhpOpPersons", "ThisItem.Persons", width=w["NO."], height=32,
                                label="\"Number of people\"", onchange=(
        "Patch(\n"
        "    colVhpOperations, ThisItem,\n"
        "    {\n"
        f"        Persons: {NV},\n"
        f"        DurationHours: {cfg.duration_expr('ThisItem.WorkHours', NV)}\n"
        "    }\n"
        ")"))
    # Varigheden vises, men tastes ikke - den ER Work / No.
    numOpDur = number_field("inpVhpOpDur", "ThisItem.DurationHours", width=w["DUR. (H)"], height=32,
                            display_mode="DisplayMode.View", label="\"Duration hours\"")
    # Arbejdscenteret kommer fra standardarbejdsplanen og bestemmer baade
    # kontrolnoeglen og indkoebsfelterne. Kan man rette det i hoejre hus,
    # skifter de andre felters regler under haanden paa en linje, SAP i
    # forvejen har bestemt. Det laeses nu - og ser graat ud som resten af
    # det, man ikke kan redigere.
    txtOpMwc = text_input("inpVhpOpMwc", "ThisItem.MainWorkCenter", width=w["MAIN WORK CENTER"],
                          height=32, display_mode="DisplayMode.View", label="\"Main work center\"")
    # Kontrolnoeglen: kun to valg at SKIFTE imellem, men listen skal
    # ogsaa kunne VISE den vaerdi, linjen allerede har - fx PM02 eller PM03
    # fra standardplanen. Ellers stod cellen tom paa alle de linjer, man
    # ikke maa redigere.
    #
    # Foerste forsoeg var en dropdown og en skrivebeskyttet tekst oven i
    # hinanden, hvor kun een var synlig. Layout-tjekket afviste det med
    # rette: to kontroller paa 90 px i en celle paa 90 px. Een kontrol med
    # en dynamisk liste goer det samme uden overlay.
    ctrl_items = ("Filter(\n"
                  "    Distinct(\n"
                  "        Table(\n"
                  + "".join('            { Value: "%s" },\n' % c for c in CTRL_CHOICES) +
                  '            { Value: Coalesce(ThisItem.ControlKey, "") }\n'
                  "        ),\n"
                  "        Value\n"
                  "    ),\n"
                  "    !IsBlank(Value)\n"
                  ")")
    drpOpCtrl = themed_dropdown(
        "drpVhpOpCtrl", ctrl_items,
        'LookUp(' + ctrl_items + ', Value = ThisItem.ControlKey).Value',
        width=w["CTRL"], height=32, display_mode=DM_CTRL, label="\"Control key\"")
    drpOpCtrl.props["OnChange"] = ("Patch(colVhpOperations, ThisItem, "
                                   "{ ControlKey: Self.Selected.Value })")

    # Leverandoeren soeges frem i en popup (vendor_button, _vendor_modal).
    txtOpVendor = vendor_button("btnVhpOpVendor", "ThisItem", "ThisItem.OperationNo", w["VENDOR"])
    numOpCost = number_field("inpVhpOpCost", PM02_COST, width=w["COST"], height=32,
                             required_formula=IS_PM02,
                             display_mode=DM_PURCHASE, label="\"Price\"",
                             onchange=f"Patch(colVhpOperations, ThisItem, {{ Cost: {NV} }})")
    # Cellen viser kun koden; listen i popup'en viser ogsaa teksten.
    txtOpMatGrp = matgrp_button("btnVhpOpMatGrp", "ThisItem", "ThisItem.OperationNo", w["MAT.GRP"])
    # Cellen viser begyndelsen af teksten; skrivningen sker i popup'en, hvor
    # der er plads til en instruktion. Reset FOER popup'en aabnes, saa feltet
    # viser den linje, man klikkede paa, og ikke den forrige.
    btnOpLongText = button(
        "btnVhpOpLongText",
        (
            "If(\n"
            "    IsBlank(Trim(Coalesce(ThisItem.LongText, \"\"))),\n"
            "    \"Add text...\",\n"
            "    Left(ThisItem.LongText, 16) & If(Len(ThisItem.LongText) > 16, \"...\")\n"
            ")"
        ),
        (
            "Set(varVhpLongTextTarget, \"op\");\n"
            "Set(varVhpLongTextItemId, ThisItem.ItemId);\n"
            "Set(varVhpLongTextOpNo, ThisItem.OperationNo);\n"
            "Set(varVhpLongTextDraft, Coalesce(ThisItem.LongText, \"\"));\n"
            "Reset(inpVhpLongTextBox);\n"
            "Set(varVhpLongTextOpen, true)"
        ),
        width=w["LONG TEXT"], height=32, icon="DocumentText",
        display_mode=("If(varVhpViewOnly && IsBlank(Trim(Coalesce(ThisItem.LongText, \"\"))), "
                      "DisplayMode.Disabled, DisplayMode.Edit)"),
        accessible='"Edit long text for operation " & ThisItem.OperationNo')
    mark_done(btnOpLongText, "!IsBlank(Trim(Coalesce(ThisItem.LongText, \"\")))")

    # Pakkerne vises som piller (designforslaget), og et klik slaar en pakke
    # til eller fra paa linjen. Matricen under fanen Packages er den samme
    # allokering set fra pakkerne. Uden strategi - eller foer strategiens
    # pakker er hentet - staar der en tekst i stedet.
    show_pills = f"({IS_STRATEGY} && {HAS_PKGS})"
    txtOpPackages = text_ctrl(
        "txtVhpOpPackages",
        'If(varVhpPlan.PlanType <> "Strategy", "-", "(no packages)")',
        size=12, height=32, width=w["PACKAGES"], wrap="false", color=C_MUTED,
        visible=f"!{show_pills}")
    galOpPills = pkg_pills("VhpOp", "ThisItem.OperationNo", "ThisItem.PackagesKey",
                           width=w["PACKAGES"])
    galOpPills.props["Visible"] = show_pills
    galOpPills.vis = show_pills
    cellOpPackages = group("conVhpOpPackages", [txtOpPackages, galOpPills], direction="Horizontal",
                           gap=0, height=32, width=w["PACKAGES"], align_items="Center")

    OP_MATS = ("Filter(colVhpMaterials, ItemId = ThisItem.ItemId && "
               "OperationNo = ThisItem.OperationNo)")
    btnOpMat = button(
        "btnVhpOpMaterials", f'"Materials (" & Text(CountRows({OP_MATS})) & ")"',
        "Set(varVhpMatOpNo, ThisItem.OperationNo)", width=w["MATERIALS"], height=32,
        accessible='"Materials for operation " & ThisItem.OperationNo')
    btnOpDocs = button(
        # Dokumenterne er vedhaeftninger paa operationens raekke (issue
        # #300) og hentes foerst, naar popuppen aabnes. Antallet kendes
        # foerst derefter (FileCount, #336) - indtil da blot "Docs".
        "btnVhpOpDocs", docs_label("ThisItem.FileCount"),
        att.open_fx("ThisItem.OperationNo"), width=w["DOCS"], height=32,
        accessible='"Documents for operation " & ThisItem.OperationNo')
    for b_ in (btnOpMat, btnOpDocs):
        b_.props["Size"] = "12"
    mark_done(btnOpMat, f"CountRows({OP_MATS}) > 0")

    opRow = group("conVhpOpRow",
                  pin_widths([txtOpNo, txtOpShort, numOpWork, numOpPersons, numOpDur, txtOpMwc,
                              drpOpCtrl, txtOpVendor, numOpCost, txtOpMatGrp,
                              btnOpLongText, cellOpPackages, btnOpMat, btnOpDocs, btnOpDel]),
                  direction="Horizontal", gap=OPS_GAP,
                  height="Parent.TemplateHeight - 2", align_items="Center", width="Parent.TemplateWidth")

    OPS_ROW_H = 44 + 2
    # INGEN TOM RAEKKE (issue #73). Hoejden var Max(n, 1) raekker, og
    # galleriets fyld var kantfarven - uden operationer stod der derfor en
    # farvet bjaelke under kolonneoverskrifterne. Nu er galleriet kun
    # synligt, naar der ER raekker, og fyldet er kortets egen flade; saa
    # staar der kun "No operation lines yet..." under overskrifterne.
    n_ops = "CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))"
    has_ops = f"IfError(!IsBlank(varVhpActiveItemId) && {n_ops} > 0, false)"
    gal_h = f"{n_ops} * {OPS_ROW_H}"
    gallery = Ctrl(
        "galVhpOps", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Task list operations for the active item\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_CARD_BG,
            "FillPortions": "0",
            "Height": gal_h,
            "Items": "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": "44",
            # Tabellen + TemplatePadding + scrollbar. Var galleriet kun
            # tabellens bredde, laa sidste kolonne under scrollbaren.
            "Width": f"{OPS_TABLE_W} + 4",
            "Visible": has_ops,
            "WrapCount": "1",
        },
        children=[opRow], h=gal_h, vis=has_ops)

    # Tom tilstand (UX-review F4): hvad man goer - task listens linjer eller
    # en manuel operation (knapperne staar i vaerktoejslinjen over).
    OPS_EMPTY = ('"No operations yet - choose Add lines from task list or Manual operation."')
    opsEmpty = empty_state("conVhpOpsEmpty", OPS_EMPTY, icon_path=icons.LIST,
                           visible=f"!{has_ops}", width=str(OPS_TABLE_W))

    opsTotalsDivider = group("conVhpOpsTotalsDivider", [], height=1, fill=C_DIVIDER,
                             direction="Horizontal", width=str(OPS_TABLE_W),
                             visible=TOTALS_ON)
    opsTotals = Ctrl("htmVhpOpsTotals", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "24", "HtmlText": _ops_totals_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(OPS_TABLE_W),
    }, h=24)
    opsTotals.vis = TOTALS_ON

    # Tabellen har fast bredde (summen af kolonnerne). Paa smalle skaerme
    # scroller den vandret i stedet for at klippe kolonner af.
    opsTableWrap = group("conVhpOpsTableWrap",
                         [opsHeader, opsDivider, gallery, opsTotalsDivider, opsTotals, opsEmpty],
                         direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                         align_items="Start", visible=at_least("Tablet"))

    # Operationstabellen er fanen Operations - sammen med tasklist-vaelgeren
    # og de fire operationsknapper. De laa foer i kortet uden for ruderne, og
    # saa blev "Add operation" staaende paa materialefanen, hvor den ikke
    # hoerer hjemme. Hver fane ejer nu sine egne knapper, praecis som
    # materialeruden allerede gjorde.
    opsEmptyM = empty_state("conVhpOpsEmptyM", OPS_EMPTY, icon_path=icons.LIST,
                            visible=f"!{has_ops} && {below('Tablet')}")
    opsPane = group("conVhpOpsPane", [toolbar, tasklistMeta, opsHint, opsTableWrap, _ops_list_mobile(), opsEmptyM],
                    direction="Vertical", gap=8, width="Parent.Width",
                    visible=OPS_PANE_ON)
    pkgPane = build_strategy_body()
    pkgPane.vis = PKG_PANE_ON
    tabBar = _tab_bar_if_strategy()

    # Fanebjaelken staar oeverst, lige under sektionshovedet: foerst vaelger
    # man fanen, saa ser man dens indhold. Den laa foer under baade
    # tasklist-vaelgeren og knapraekken, og saa stod selve skiftet nederst i
    # den halvdel af kortet, der ikke aendrede sig.
    return card("conVhpOpsCard",
                [header, helpPanel, tabBar,
                 opsPane, pkgPane, opsFooter])
