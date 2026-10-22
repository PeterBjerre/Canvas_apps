# -*- coding: utf-8 -*-
import display_text as dt
import status_chip as sc
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, row_height, C_CARD_BG, C_MUTED,
                        C_MODAL_BG, C_PRIMARY_SOFT,
                        C_INVALID_FG, C_DIVIDER, C_TRANSPARENT, C_WARN_FG,
                        C_NEUTRAL_BG, C_TITLE)
import layout_tokens as lay
import icons
from build_helpers import (ensure_hit, popup_head, empty_state, table_surface, flow_row, text_ctrl,
                           group, button, text_input, number_field, num_value, themed_dropdown,
                           card, pin_widths, grow, row_hit,
                           fit_button_width, ICON_W, flow_ok, mark_done,
                           tab_list, tabs_w, confirm_modal)
from build_plan_header import section_header, help_panel, section_footer, mobile_head, status_icon
from build_helpers import mobile_pad
from build_helpers import modern_badge  # issue #545: Duration-maerket
import mobile
from build_helpers import act_fx, act_mark, act_button
from gen_screen import lock_section, SCROLLBAR_NOT_MOBILE

# Talfeltets vaerdi (UX-review T10): heltal, Blank() ved tomt felt eller ikke-tal.
NV = num_value()
from build_status import HAS_PKGS, PLANT, tasklist_plant_conflict
import build_help as bh
from build_strategy import build_strategy_body, IS_STRATEGY, pkg_pills, PILLS_W
import sp_config as cfg
from design_tokens import ref_hex
from layout_tokens import SCROLLBAR_W, fits, TWO_COL_MIN, below, at_least

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
# VIEW-TILSTAND LAASER ALT (issue #390): knapper, der aendrer data, er
# slaaet fra; afkrydsninger staar i View, saa deres flueben stadig ses.
VIEW_LOCK = "If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)"
VIEW_READONLY = "If(varVhpViewOnly, DisplayMode.View, DisplayMode.Edit)"
# Task list and operations er gemt med Save og laast, til der trykkes Edit (#433).
OPS_LOCKED = cfg.section_locked("Ops")
# Skaermens handlingstilstand (build_hero.ACT) - Saving... i knappen.
ACT = "varVhpAct"
# Paa en telefon er kortets polstring 12 i hver side (issue #508).
OPS_CW = lay.CARD_INNER_W

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
    # 1080P (issue #477): Long text, Docs og Action er smallere, saa hele
    # tabellen staar uden vandret scroll ved 1920 x 1080 - ogsaa med
    # Packages. Long text-knappen har intet ikon i tabellen (kolonnens
    # overskrift siger, hvad den er); de groenne kanter viser stadig, om der
    # er tekst. Se OPS_FIT_MIN_APP_W nedenfor.
    ("LONG TEXT", 120),
    # Plads til syv smalle pakke-piller (build_strategy.pkg_pills).
    ("PACKAGES", PILLS_W),
    # Knapper, som Details og Docs i Equipments liste (issue #54). De
    # aabner materialerne og dokumenterne for NETOP denne operation.
    ("MATERIALS", 110),
    ("DOCS", 80),
    # Slet-knappen er Max(40, H.hit) - hoejst 44 px.
    ("ACTION", 48),
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
    # Telefonen (issue #508): raekker paa 44 px (klikflade), og listen
    # bruger den hoejde, popuppen har (den eneste scroll i popuppen).
    row_h_m = mobile.TOUCH + 2
    row_h_fx = lay.mobile_or(row_h_m, row_h)
    line = grow(text_ctrl("txtVhpMgRow", "ThisItem.Display", size=13, height=24, wrap="false"))
    row = group("conVhpMgRow", [line], direction="Horizontal", height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth",
                fill=f"If(ThisItem.Value = {cur_v}, {C_PRIMARY_SOFT}, {C_CARD_BG})",
                pad=(0, 8, 0, 8))
    hit = row_hit("btnVhpMgHit",
                  f"Patch(colVhpOperations, {MG_OP}, {{ MaterialGroup: ThisItem.Value }});\n{MG_CLOSE}",
                  '"Use material group " & ThisItem.Display', "Parent.TemplateWidth",
                  "Parent.TemplateHeight - 2")
    # Popup'en aabnes kun fra en knap, der er slaaet fra i View - men et
    # klik paa listen maa heller ikke skrive der (issue #390).
    hit.props["DisplayMode"] = VIEW_READONLY
    gal_h = lay.mobile_or(f"Min(CountRows(colVhpMaterialGroups) * {row_h_m}, Max(160, App.Height - 150))",
                          f"Min(CountRows(colVhpMaterialGroups) * {row_h}, Max(160, App.Height - 220))")
    gal = Ctrl("galVhpMatGroups", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Material groups - select one to use it"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": "colVhpMaterialGroups",
        "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "2",
        "TemplateSize": f"({row_h_fx}) - 2", "Width": MODAL_CW, "WrapCount": "1",
    }, children=[row, hit], h=gal_h)
    return _modal("VhpMg", '"Material group · Operation " & varVhpMgOpNo', MG_OPEN,
                  MG_CLOSE, [cur, gal])


def cost_expr(work):
    return (f'If(\n'
            f'            {HOURLY_RATE},\n'
            f'            {work} * Coalesce(ThisItem.UnitCost, 0),\n'
            f'            ThisItem.Cost\n'
            f'        )')
# PACKAGES KUN VED EN STRATEGIPLAN (issue #477). Uden strategi er der
# ingen pakker at allokere til, og kolonnen stod med "-" paa hver linje.
# Nu er cellen skjult - og galleriets udfoldning (gen_screen._place) giver
# en skjult celle hverken bredde eller mellemrum - og overskriften,
# kolonnesummen og antallet af mellemrum foelger samme betingelse.
PKG_COL_ON = IS_STRATEGY
OPS_GAP_MIN = 12
OPS_COLS_W_ALL = sum(w for _, w in OPS_COLS)
OPS_COLS_W_NOPKG = OPS_COLS_W_ALL - dict(OPS_COLS)["PACKAGES"]
OPS_COLS_W = f"If({PKG_COL_ON}, {OPS_COLS_W_ALL}, {OPS_COLS_W_NOPKG})"
OPS_N_GAPS = f"If({PKG_COL_ON}, {len(OPS_COLS) - 1}, {len(OPS_COLS) - 2})"
OPS_GAP = (f"Max({OPS_GAP_MIN}, Int(({OPS_CW} - 8 - {OPS_COLS_W}) / {OPS_N_GAPS}))")
OPS_TABLE_W = f"({OPS_COLS_W} + {OPS_GAP} * {OPS_N_GAPS})"
# Den mindste App.Width, hvor hele tabellen (med Packages og mindste
# mellemrum) staar uden vandret scroll: OPS_CW - 8 >= tabellen. SHELL_W er
# App.Width - 56 (skinnen) - 64 (SHELL_INSET) uden sidepanel.
OPS_FIT_MIN_APP_W = (OPS_COLS_W_ALL + OPS_GAP_MIN * (len(OPS_COLS) - 1)
                     + 8 + 36 + 56 + 64)
assert OPS_FIT_MIN_APP_W <= 1860, (
    "Operationstabellen passer ikke ved 1080p (1920 px) med luft til browserens "
    "kant og scrollbar: kraever App.Width >= %d (issue #477)" % OPS_FIT_MIN_APP_W)


def _ops_header_html():
    def cols_of(pkg):
        return " ".join(f"{w}px" for t, w in OPS_COLS if pkg or t != "PACKAGES")

    def spans_of(pkg):
        return "".join(f"<span>{t}</span>" for t, _ in OPS_COLS if pkg or t != "PACKAGES")
    cols = f"\" & If({PKG_COL_ON}, \"{cols_of(True)}\", \"{cols_of(False)}\") & \""
    spans = f"\" & If({PKG_COL_ON}, \"{spans_of(True)}\", \"{spans_of(False)}\") & \""
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
# Noegletal: itemets Total item cost (Item) og Duration (her)
# ---------------------------------------------------------------------------
# Summerne stod foer i en raekke under operationstabellen ("Total for this
# item"), derefter i et kort i denne sektions overskrift med Total cost og
# Duration (issue #529). ISSUE #545 (Uffe): itemets omkostning hoerer til
# ITEMET - den staar nu som "Total item cost"-maerket oeverst til hoejre i
# Item-sektionen (build_items.item_cost_badge). Her staar kun Duration
# tilbage: varigheden er operationernes og nyttig, mens man bygger dem.
# Summerne gaelder det valgte item - det er dets operationer, tabellen viser.
OPS_ACTIVE = "Filter(colVhpOperations, ItemId = varVhpActiveItemId)"

# Tom tabel har ingen sum at vise - saa er maerket skjult.
TOTALS_ON = ("IfError(!IsBlank(varVhpActiveItemId) && "
             f"CountRows({OPS_ACTIVE}) > 0, false)")

# Planens samlede omkostning og graensen staar i build_plan_header (issue
# #529): advarslen hoerer til planen og vises KUN paa planens Total
# cost-maerke (tooltip) - aldrig her og aldrig paa itemets maerke.

# Timer og kroner i appens ENE talformat (layout_tokens.num_text, UX-review
# B2): "7" og "1,192" - ikke "7," og "1.192,00".
ITEM_DUR_TEXT = ('"Duration: " & ' + lay.num_text(f"Sum({OPS_ACTIVE}, DurationHours)") + ' & " h"')

# ITEMETS TOTAL COST (issue #545): summen af ALLE det valgte items
# operationer. Coalesce: et item uden operationer viser "0 DKK" (Sum af en
# tom tabel er Blank) - maerket staar, saa snart et item er valgt, og
# opdateres af sig selv, naar operationer, priser eller det valgte item
# skifter (det er en formel, ingen variabel at holde ved lige).
ITEM_COST = f"Coalesce(Sum({OPS_ACTIVE}, Cost), 0)"
ITEM_COST_TEXT = '"Total item cost: " & ' + lay.num_text(ITEM_COST) + ' & " DKK"'
ITEM_COST_ON = "IfError(!IsBlank(varVhpActiveItemId), false)"
ITEM_COST_TIP = '"Combined cost from Task list and operations"'

# Et maerke, der er saa bredt som teksten (som planens Total cost-maerke):
# ca. 7 px pr. tegn i 12 px Semibold og 10 px luft i hver side.
def badge_w(text_fx):
    return f"Len({text_fx}) * 7 + 24"


DUR_BADGE_H = 24
# Til pladsregnestykket ved titlen: "Duration: 1,234.5 h" (19 tegn).
DUR_BADGE_MAX_W = 19 * 7 + 24

# Overskriftsmaerket staar fra Tablet og op. Paa en telefon er der ikke
# plads ved titlen, saa telefonen har maerket nederst i task-list-raekken
# (issue #508), under knapperne.
TOTALS_HEAD_ON = lay.mobile_or("false", TOTALS_ON)
TOTALS_PHONE_ON = lay.mobile_or(TOTALS_ON, "false")


def totals_card(name="bdgVhpOpsDuration", phone=False):
    """Maerket med det valgte items Duration (issue #545: Total cost er
    flyttet til Item-sektionen). phone=False: i sektionsoverskriften (Tablet
    og op); phone=True: i task-list-raekken paa en telefon. Aldrig planens
    advarsel om omkostningsgodkendelse."""
    vis = TOTALS_PHONE_ON if phone else TOTALS_HEAD_ON
    w = badge_w(ITEM_DUR_TEXT)
    c = modern_badge(
        name, ITEM_DUR_TEXT, color=C_TITLE, fill=C_NEUTRAL_BG,
        width=w, height=DUR_BADGE_H, size=12, pad=(10, 10),
        accessible='"Item " & ' + ITEM_DUR_TEXT, visible=vis,
        extra={"AlignInContainer": "AlignInContainer.Center"})
    if phone:
        # Fra Tablet og op er maerket skjult og maa ikke taelle med i
        # raekkens bredde/hoejde. Paa telefonen staar det til venstre, med
        # en fast bredde: raekkens flow_ok-graense (og check_layout regel
        # 4d) skal kunne regne bredden ud uden at kende teksten.
        c.props["Width"] = lay.mobile_or(DUR_BADGE_MAX_W, 0)
        c.props["LayoutMinWidth"] = "0"
        c.props["Height"] = lay.mobile_or(DUR_BADGE_H, 0)
        c.h = c.props["Height"]
        c.props["AlignInContainer"] = "AlignInContainer.Start"
    else:
        c.props["LayoutMinWidth"] = c.props["Width"]
        c.h = lay.mobile_or(0, f"If({TOTALS_ON}, {DUR_BADGE_H}, 0)")
    return c


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
    tl = tab_list("tabVhpOps", "varVhpOpsTab", tabs, label="Task list sections",
                  width=OPS_CW)
    # 44 px paa en telefon (issue #508).
    return mobile.touch(tl)


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
#
# EN KLADDE MED SAVE (issue #451). Popuppen rettede foer direkte i
# colVhpMaterials, og en SEL-kolonne + "Remove material" slettede. Man kunne
# ikke se, hvad der var nyt, rettet eller gemt. Nu foelger den appens andre
# popupper (Long text: kladde + "Save text"; Object list: kladde + "Use
# selected"; X kasserer, issue #237): popuppen arbejder i colVhpMatDraft,
# og foerst Save skriver i colVhpMaterials. Hver linje har en statuschip
# (tools/status_chip.py - den ene statuschip i appen):
#   Saved    staar i colVhpMaterials og er uaendret
#   New      tilfoejet, ikke gemt endnu
#   Edited   rettet, ikke gemt endnu
#   Deleted  slettes ved Save - kan fortrydes til da
# En gemt linje er skrivebeskyttet, til der trykkes Edit paa den - samme
# model som en gemt sektion (issue #433). SEL er erstattet af ACTIONS:
# Edit/Undo og Delete paa selve linjen. Delete af en gemt linje er en
# ugemt aendring (chip + Undo), ikke en sletning med det samme, saa den
# kraever ingen bekraeftelse; X med ugemte aendringer goer (confirm_modal).
MAT_LINE = [
    ("saved", "Saved", icons.STATUS_READY, "ok"),
    ("new", "New", icons.STATUS_DRAFT, "info"),
    ("edited", "Edited", icons.EDIT, "warn"),
    ("deleted", "Deleted", icons.DELETE, "error"),
]
MAT_ACT_W = 2 * lay.HIT_TOUCH + 4
MAT_COLS = [("MATERIAL", 120), ("DESCRIPTION", 150), ("QTY", 60), ("UNIT", 50),
            ("STATUS", sc.table_width(MAT_LINE)), ("ACTIONS", MAT_ACT_W)]
MAT_GAP = 10
MAT_TABLE_W = sum(w for _, w in MAT_COLS) + MAT_GAP * (len(MAT_COLS) - 1)
# Een linje: et felt (32) og Edit/Delete paa H.hit (44 paa touch).
MAT_ROW_H = lay.HIT_TOUCH
MAT_ACTIVE = "Filter(colVhpMaterials, ItemId = varVhpActiveItemId)"
# Materialerne paa den operation, popup'en er aabnet for (de GEMTE).
MAT_OP = ("Filter(colVhpMaterials, ItemId = varVhpActiveItemId && "
          "OperationNo = varVhpMatOpNo)")


def mat_changed(r=""):
    """Er linjen en ugemt aendring? r: "ThisItem." eller "" (i Filter)."""
    return (f"({r}Deleted || {r}IsNew || {r}MaterialNo <> {r}OrigMaterialNo || "
            f"{r}Quantity <> {r}OrigQuantity)")


def mat_state(r="ThisItem."):
    return (f'If({r}Deleted, "deleted", {r}IsNew, "new", '
            f'{r}MaterialNo <> {r}OrigMaterialNo || {r}Quantity <> {r}OrigQuantity, '
            f'"edited", "saved")')


# Antallet af ugemte aendringer i kladden.
MAT_CHANGES = f"CountRows(Filter(colVhpMatDraft, {mat_changed()}))"
MAT_DIRTY = f"IfError({MAT_CHANGES} > 0, false)"
# Linjer, Save afviser: intet materialenummer eller intet antal over 0.
MAT_INVALID = ("Filter(colVhpMatDraft, !Deleted && (IsBlank(Trim(MaterialNo)) || "
               "IsBlank(Quantity) || Quantity <= 0))")


def mat_open_fx(op_no):
    """Materials-knappen: kladden er operationens gemte linjer, som de staar."""
    return (
        "Set(varVhpMatTried, false);\n"
        "ClearCollect(\n"
        "    colVhpMatDraft,\n"
        "    ForAll(\n"
        f"        Filter(colVhpMaterials, ItemId = varVhpActiveItemId && OperationNo = {op_no}) As M,\n"
        "        {\n"
        "            LineId: M.LineId, MaterialNo: M.MaterialNo, Description: M.Description,\n"
        "            Unit: M.Unit, Quantity: M.Quantity,\n"
        "            OrigMaterialNo: M.MaterialNo, OrigQuantity: M.Quantity,\n"
        "            IsNew: false, Editing: false, Deleted: false\n"
        "        }\n"
        "    )\n"
        ");\n"
        f"Set(varVhpMatOpNo, {op_no})"
    )


# Luk uden at gemme: kladden glemmes.
MAT_DISCARD_FX = 'Set(varVhpMatTried, false);\nClear(colVhpMatDraft);\nSet(varVhpMatOpNo, "")'
# X (og sloeret paa mobil): med ugemte aendringer spoerges der foerst.
MAT_CLOSE_FX = (f"If(\n    {MAT_DIRTY},\n    Set(varVhpMatDiscardOpen, true),\n"
                + "\n".join("    " + l for l in MAT_DISCARD_FX.split("\n")) + "\n)")


def mat_summary(mats):
    """Tooltip paa Materials-knappen (issue #451): de foerste fem linjer.
    Tom, naar der intet er gemt - saa er der ingen tooltip."""
    return (
        f"With(\n    {{ ms: Sort({mats}, LineId) }},\n"
        "    If(\n        CountRows(ms) = 0,\n        \"\",\n"
        f"        {dt.plural('CountRows(ms)', 'material')} & \": \" & Concat(\n"
        "            FirstN(ms, 5),\n"
        "            MaterialNo & \" x \" & Text(Quantity) & If(IsBlank(Unit), \"\", \" \" & Unit),\n"
        "            \", \"\n"
        "        ) & If(CountRows(ms) > 5, \", ...\", \"\")\n"
        "    )\n)")


def docs_summary(op):
    """Tooltip paa Docs-knappen (issue #451): antal og de foerste filnavne.
    Tom, til antallet kendes (#336), og naar der ingen filer er."""
    return (f"If(Coalesce({op}.FileCount, 0) = 0, \"\", "
            f"{dt.plural(op + '.FileCount', 'document')} & \": \" & {op}.FileNames)")


def docs_done(op):
    """Docs (n) er groen, naar der er gemte filer - som Long text."""
    return f"Coalesce({op}.FileCount, 0) > 0"


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
    # TELEFONEN (issue #508): popuppen er skaermens bredde minus 2 x 8 med
    # 12 px polstring i siderne (MODAL_CW), og en popup med meget indhold
    # (scroll/cap) staar oeverst og bruger hele hoejden minus 2 x 8.
    if scroll:
        body_h = lay.mobile_or(f"App.Height - {2 * lay.MOBILE_POP_MARGIN + 36 + HEAD_H + 12}",
                               f"Max(200, App.Height - {150 + HEAD_H - 32})")
        body = group(f"con{name}Body", kids, direction="Vertical", gap=8, height=body_h,
                     overflow_y="Scroll")
        kids = [body]
    elif cap:
        cap_h = lay.mobile_or(f"App.Height - {2 * lay.MOBILE_POP_MARGIN} - 36 - {HEAD_H} - 12",
                              f"App.Height - 40 - 36 - {HEAD_H} - 12")
        kids = [du.capped_body(f"con{name}Body", kids, cap_h, gap=8)]
    modal = group(f"con{name}Modal", [head] + kids, direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width=lay.popup_w(width, 40),
                  drop_shadow="ExtraBold", visible=f"IfError({open_var}, false)")
    mobile_pad(modal, x=mobile.CARD_PAD)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    desk_y = "20" if scroll else "Max(20, (App.Height - Self.Height) / 3)"
    modal.props["Y"] = mobile.sheet_y(desk_y) if (scroll or cap) else desk_y
    return modal


ATT_OPEN = "!IsBlank(varVhpAttOpNo)"
# Popup'ernes indholdsbredde: 620 minus 18 + 18.
# Paa en telefon: App.Width - 2 x 8 (popup_w) - 2 x 12 (polstringen).
MODAL_CW = lay.mobile_or(f"App.Width - {2 * lay.MOBILE_POP_MARGIN + 2 * lay.MOBILE_CARD_PAD}",
                         "(Min(620, App.Width - 40) - 36)")


MAT_OPEN = "!IsBlank(varVhpMatOpNo)"
# Materials-popuppen er bredere: STATUS og ACTIONS skal vaere der (#451).
MAT_MODAL_W = MAT_TABLE_W + 4 + SCROLLBAR_W + 36


def _materials_modal():
    """Materialer paa EEN operation - aabnet fra operationens Materials-knap.

    Popup'en hoerer til operationen, saa en ny linje faar dens nummer, og
    listen viser kun dens linjer (issue #54). Den arbejder i kladden
    colVhpMatDraft; Save skriver kladden i colVhpMaterials, og planens Save
    draft gemmer dem som foer (issue #451)."""
    w = {t: wd for t, wd in MAT_COLS}
    ro = "varVhpViewOnly"

    btnAdd = button(
        "btnVhpAddMaterial", '"Add material"',
        (
            "Collect(\n"
            "    colVhpMatDraft,\n"
            "    {\n"
            # LineId er unik pr. ITEM, ikke pr. operation - og ikke kun
            # blandt de gemte: kladden kan have nye linjer.
            f"        LineId: Max(Coalesce(Max({MAT_ACTIVE}, LineId), 0), "
            "Coalesce(Max(colVhpMatDraft, LineId), 0)) + 1,\n"
            "        MaterialNo: \"\",\n"
            "        Description: \"\",\n"
            "        Unit: \"\",\n"
            "        Quantity: 1,\n"
            "        OrigMaterialNo: \"\",\n"
            "        OrigQuantity: 1,\n"
            "        IsNew: true,\n"
            "        Editing: true,\n"
            "        Deleted: false\n"
            "    }\n"
            ")"
        ), primary=True, width=fit_button_width('"Add material"') + ICON_W, icon="Add",
        display_mode=VIEW_LOCK, visible=f"!{ro}")

    mobile.touch(btnAdd)
    actions = group("conVhpMatActions", [btnAdd], direction="Horizontal", gap=8,
                    height=lay.mobile_or(mobile.TOUCH, 36), align_items="Center", visible=f"!{ro}")

    header = Ctrl("htmVhpMatHeader", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "22", "HtmlText": _mat_header_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": str(MAT_TABLE_W),
    }, h=22)
    divider = group("conVhpMatDivider", [], height=1, fill=C_DIVIDER,
                    direction="Horizontal", width=str(MAT_TABLE_W))

    # Felterne kan rettes paa en ny linje, og paa en gemt linje efter Edit.
    # En linje, der slettes, og alt i View er skrivebeskyttet.
    row_mode = (f"If({ro} || ThisItem.Deleted || !(ThisItem.IsNew || ThisItem.Editing), "
                "DisplayMode.View, DisplayMode.Edit)")
    tried = "(varVhpMatTried && !ThisItem.Deleted)"
    txtNo = text_input("inpVhpMatNo", "ThisItem.MaterialNo", width=w["MATERIAL"], height=32,
                       required_formula=tried, display_mode=row_mode,
                       onchange="Patch(colVhpMatDraft, ThisItem, { MaterialNo: Trim(Self.Text) })",
                       label='"Material number"')
    # Kommer fra materialeopslaget, ikke fra brugeren.
    txtDesc = text_ctrl("txtVhpMatDesc",
                        'If(IsBlank(ThisItem.Description), "-", ThisItem.Description)',
                        size=12, color=C_MUTED, height=30, width=w["DESCRIPTION"], wrap="false")
    numQty = number_field("inpVhpMatQty", "ThisItem.Quantity", width=w["QTY"], height=32,
                          label="\"Quantity\"", required_formula=tried, display_mode=row_mode,
                          onchange=f"Patch(colVhpMatDraft, ThisItem, {{ Quantity: {NV} }})")
    txtUnit = text_ctrl("txtVhpMatUnit",
                        'If(IsBlank(ThisItem.Unit), "-", ThisItem.Unit)',
                        size=12, color=C_MUTED, height=30, width=w["UNIT"], wrap="false")
    chip = sc.status_chip("imgVhpMatStatus", mat_state(), MAT_LINE, width=w["STATUS"])

    # ACTIONS: Edit (gemt linje) eller Undo (rettet eller slettet linje), og
    # Delete. En ny linje har kun Delete - den kan rettes direkte.
    undo = "(ThisItem.Editing || ThisItem.Deleted)"
    btnEdit = button(
        "btnVhpMatEdit", '""',
        (f"If(\n    {undo},\n"
         "    Patch(colVhpMatDraft, ThisItem, { MaterialNo: ThisItem.OrigMaterialNo, "
         "Quantity: ThisItem.OrigQuantity, Editing: false, Deleted: false }),\n"
         "    Patch(colVhpMatDraft, ThisItem, { Editing: true })\n)"),
        width=40, height=32, icon="Edit", display_mode=VIEW_LOCK,
        visible=f"!{ro} && (!ThisItem.IsNew || ThisItem.Deleted)",
        accessible=(f'If(ThisItem.Deleted, "Restore material line ", {undo}, '
                    '"Undo changes to material line ", "Edit material line ") & ThisItem.MaterialNo'))
    btnEdit.props["Icon"] = f'If({undo}, "ArrowReset", "Edit")'
    btnEdit.props["Layout"] = "ButtonLayout.IconOnly"
    btnEdit.props["Tooltip"] = (f'If(ThisItem.Deleted, "Restore this line", {undo}, '
                                '"Undo the unsaved changes to this line", "Edit this line")')
    ensure_hit(btnEdit)
    btnDel = button(
        "btnVhpMatDelete", '""',
        ("If(\n    ThisItem.IsNew,\n    Remove(colVhpMatDraft, ThisItem),\n"
         "    Patch(colVhpMatDraft, ThisItem, { Deleted: true, Editing: false })\n)"),
        danger=True, width=40, height=32, icon="Delete", display_mode=VIEW_LOCK,
        visible=f"!{ro} && !ThisItem.Deleted",
        accessible='"Delete material line " & ThisItem.MaterialNo')
    btnDel.props["Layout"] = "ButtonLayout.IconOnly"
    btnDel.props["Tooltip"] = ('If(ThisItem.IsNew, "Remove this new line", '
                               '"Delete this line - it is removed when you choose Save")')
    ensure_hit(btnDel)
    cellAct = group("conVhpMatRowActions", [btnEdit, btnDel], direction="Horizontal", gap=4,
                    height=lay.HIT_TOUCH, width=w["ACTIONS"], align_items="Center")

    row = group("conVhpMatRow", pin_widths([txtNo, txtDesc, numQty, txtUnit, chip, cellAct]),
                direction="Horizontal", gap=MAT_GAP, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    MAT_ROWS = 6
    # TELEFONEN (issue #508): tabellen (620 px) er et kort pr. linje -
    # materialenummeret og Edit/Delete oeverst, antal, enhed og status
    # under, beskrivelsen nederst. Galleriet er saa hoejt som sine kort og
    # scroller ikke selv; det er popuppens indhold, der scroller (een
    # scroll). Fra Tablet og op er tabellen uaendret.
    MAT_ROW_H_M = 118
    n_mat = "CountRows(colVhpMatDraft)"
    gal_h = lay.mobile_or(f"{n_mat} * {MAT_ROW_H_M}", MAT_ROWS * (MAT_ROW_H + 2))
    tpl_w_m = f"(({MODAL_CW}) - 4)"
    pad_m = 8
    act_w = 2 * lay.HIT_TOUCH + 4
    for c in (txtNo, numQty):
        mobile.touch(c)
    mobile.gallery_place(txtNo, x=pad_m, y=4, w=f"{tpl_w_m} - {2 * pad_m + act_w + 8}",
                         h=mobile.TOUCH)
    mobile.gallery_place(cellAct, x=f"{tpl_w_m} - {pad_m + act_w}", y=4)
    mobile.gallery_place(numQty, x=pad_m, y=52, w=80, h=mobile.TOUCH)
    mobile.gallery_place(txtUnit, x=pad_m + 88, y=59, w=60)
    mobile.gallery_place(chip, x=f"{tpl_w_m} - {pad_m} - {w['STATUS']}", y=63)
    mobile.gallery_place(txtDesc, x=pad_m, y=98, w=f"{tpl_w_m} - {2 * pad_m}", h=18)
    gallery = Ctrl("galVhpMaterials", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Materials for this operation"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": str(gal_h),
        "Items": "Sort(colVhpMatDraft, LineId)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": SCROLLBAR_NOT_MOBILE,
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(MAT_ROW_H),
        "Width": lay.mobile_or(MODAL_CW, str(MAT_TABLE_W + 4 + SCROLLBAR_W)),
        "WrapCount": "1",
    }, children=[row], h=gal_h)
    # Neutral flade og een streg pr. raekke - ikke graat fyld (issue #78).
    table_surface(gallery, "rctVhpMatRule")
    # Kortets hoejde paa en telefon - EFTER table_surface, som regner med et tal.
    gallery.props["TemplateSize"] = lay.mobile_or(MAT_ROW_H_M - 2, gallery.props["TemplateSize"])
    gallery.children[-1].props["Y"] = lay.mobile_or(MAT_ROW_H_M - 2 - 1,
                                                    gallery.children[-1].props["Y"])
    for c in (header, divider):
        mobile.hide_on_mobile(c)

    # Tom tilstand (UX-review F4) - knappen Add material staar lige over.
    empty = empty_state("conVhpMatEmpty",
                        f'If({ro}, "No materials on this operation.", '
                        '"No materials on this operation yet - choose Add material.")',
                        icon_path=icons.MATERIAL,
                        visible="IfError(CountRows(colVhpMatDraft) = 0, false)")

    note = text_ctrl("txtVhpMatNote",
                     lay.mobile_or('"Description and unit come from the material lookup later."',
                                   '"Description and unit are filled in by the material lookup. '
                                   'Until it is in place they stay empty."'),
                     size=12, color=C_MUTED, height=32, wrap="true")

    # Start, ikke Stretch: tabellen har sin egen bredde og scroller vandret
    # paa en smal skaerm i stedet for at blive klemt sammen.
    table = group("conVhpMatTableWrap", [header, divider, gallery, empty],
                  direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                  align_items="Start")

    # Bunden: hvad der venter paa Save - og Save. X er popuppens eneste luk
    # (issue #237) og kasserer kladden, efter en bekraeftelse.
    info = text_ctrl(
        "txtVhpMatChanges",
        (f"If(\n    {ro},\n    \"Read-only.\",\n"
         f"    With(\n        {{ c: {MAT_CHANGES} }},\n"
         "        If(c = 0, \"No unsaved changes.\", "
         f"{dt.plural('c', 'unsaved change')} & \" - choose Save to keep them.\")\n    )\n)"),
        size=12, color=f"If({MAT_DIRTY}, {C_WARN_FG}, {C_MUTED})", height=18, wrap="false")
    grow(info)
    btnSave = button(
        "btnVhpMatSave", '"Save"',
        (
            "If(\n"
            f"    CountRows({MAT_INVALID}) > 0,\n"
            "    Set(varVhpMatTried, true);\n"
            "    Notify(\"Each material line needs a material number and a quantity above 0.\", "
            "NotificationType.Error),\n"
            f"    !({MAT_DIRTY}),\n"
            + "\n".join("    " + l for l in MAT_DISCARD_FX.split("\n")) + ",\n"
            "    RemoveIf(colVhpMaterials, ItemId = varVhpActiveItemId && OperationNo = varVhpMatOpNo);\n"
            "    Collect(\n"
            "        colVhpMaterials,\n"
            "        ForAll(\n"
            "            Filter(colVhpMatDraft, !Deleted) As D,\n"
            "            {\n"
            "                ItemId: varVhpActiveItemId, LineId: D.LineId,\n"
            "                MaterialNo: Trim(D.MaterialNo), Description: D.Description,\n"
            "                Unit: D.Unit, Quantity: D.Quantity,\n"
            "                OperationNo: varVhpMatOpNo, Selected: false\n"
            "            }\n"
            "        )\n"
            "    );\n"
            "    Notify(\"Materials saved for operation \" & varVhpMatOpNo & \".\", "
            "NotificationType.Success);\n"
            + "\n".join("    " + l for l in MAT_DISCARD_FX.split("\n")) + "\n"
            ")"
        ), primary=True, width=fit_button_width('"Save"') + ICON_W, icon="Save",
        # Altid slaaet til (uden for View): et felt skriver foerst i kladden,
        # naar det forlades, saa en Save, der var slaaet fra indtil da, ville
        # sluge det klik, der forlader feltet. Uden aendringer lukker Save blot.
        display_mode=VIEW_LOCK, visible=f"!{ro}")
    mobile.touch(btnSave)
    footer = group("conVhpMatFooter", [info, btnSave], direction="Horizontal", gap=8,
                   height=lay.mobile_or(mobile.TOUCH, 36), align_items="Center")

    return _modal("VhpMat", '"Materials - operation " & varVhpMatOpNo', MAT_OPEN,
                  MAT_CLOSE_FX, [actions, note, table, footer], width=MAT_MODAL_W, cap=True)


def build_mat_discard_confirm():
    """X med ugemte aendringer i Materials-popuppen (issue #451) - appens
    bekraeftelse (confirm_modal), som "Start a new request?". X i
    bekraeftelsen lader popuppen og kladden staa."""
    return confirm_modal(
        "VhpMatDiscard", "varVhpMatDiscardOpen", "Discard unsaved changes?",
        '"The new, edited and deleted material lines on this operation are not saved."',
        "Discard changes", MAT_DISCARD_FX, "btnVhpMatDiscardConfirm", icon=None, danger=True)


# ---------------------------------------------------------------------------
# Dokumenter
# ---------------------------------------------------------------------------
# Dokumenterne er SharePoint-vedhaeftninger paa OPERATIONENS raekke i
# TaskListMain (issue #300, build_attflows.py). Den moderne Attachments-
# kontrol er bundet til raekkens Attachments og viser, aabner og fjerner
# selv filerne; "Save documents" gemmer dem med een Patch.
#
# De aeldre dokumentraekker i MD_TasklistAttachment (colVhpAttachments,
# OperationsKey ";0010;0020;") hentes, men gemningen roerer dem ikke
# laengere (R2-071) - og de vises ikke i ruden.


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
                    direction="Horizontal", gap=8, height=lay.mobile_or(lay.TOUCH_MIN, 36),
                    justify="End",
                    align_items="Center", visible=edit)
    ro = du.readonly_note("txtVhpAttReadOnly", f"!{edit}")

    # Popuppen: 20 + 20 luft til skaermkanten, 18 + 18 polstring, hovedet
    # (HEAD_H) og afstanden (12) - resten er indholdet.
    body = du.capped_body("conVhpAttBody",
                          [pick, limits, not_saved, actions, ro],
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
        placeholder=vs.PLACEHOLDER, search_accessible='"Search vendor"',
        # Telefonen (issue #508): feltet over Search - comboboksen var 120 px.
        stack_search=True)
    for nm in (VEN_COMBO, "btnVhpVenSearch", "spnVhpVenBusy"):
        mobile.touch(mobile.find(picker, nm))
    ven_row = mobile.find(picker, "conVhpVenInput")
    ven_row.props["Height"] = lay.mobile_or(2 * mobile.TOUCH + 8 + 4, ven_row.props["Height"])
    ven_row.h = ven_row.props["Height"]
    mobile.refit(picker)
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
    for b in (use, remove):
        mobile.touch(b)
    actions = flow_row("conVhpVenActions", [use, remove], MODAL_CW, gap=8)
    return _modal("VhpVen", '"Vendor · Operation " & varVhpVenOpNo', VEN_OPEN,
                  VEN_CLOSE, [cur, picker, msg, actions])


OPM_OPEN = "!IsBlank(varVhpOpMNo)"
OPM = "LookUp(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo)"


# LONG TEXT PAA EEN LINJE (issue #361)
#
# Long text-knappen i operationsraekken braekkede om paa flere linjer, naar
# teksten var lang eller indeholdt linjeskift - saa blev raekken hoejere end
# de andre. Knappen (ModernButton) har ingen Wrap-egenskab, saa udsnittet
# skal selv vaere kort nok til at staa paa een linje: linjeskift bliver til
# mellemrum (Trim samler dem), og teksten afkortes med "...".
#
# Kolonnen er 120 px (issue #477; foer 170 px med ikon). Minus knappens
# luft (2 x 16) og "..." er der ca. 76 px til teksten. 9 tegn i 12 px
# Segoe UI Semibold er ca. 75 px - ogsaa naar SAP-teksten staar med store
# bogstaver. Hele teksten staar i popuppen.
LT_PREVIEW_CHARS = 9


def longtext_preview(op, chars):
    """Long text-knappens tekst: "Add text..." uden tekst, ellers de foerste
    `chars` tegn paa een linje med "..." efter, naar der er mere."""
    return (
        "With(\n"
        "    {\n"
        f"        lt: Trim(Substitute(Substitute(Coalesce({op}.LongText, \"\"), "
        "Char(13), \" \"), Char(10), \" \"))\n"
        "    },\n"
        "    If(\n"
        "        IsBlank(lt),\n"
        "        \"Add text...\",\n"
        f"        If(Len(lt) > {chars}, Left(lt, {chars}) & \"...\", lt)\n"
        "    )\n"
        ")"
    )


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
    opm_mats = "Filter(colVhpMaterials, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo)"
    mats = button("btnVhpOpMMat", f'"Materials (" & Text(CountRows({opm_mats})) & ")"',
                  mat_open_fx("varVhpOpMNo"),
                  width=fit_button_width('"Materials (00)"'), height=32,
                  tooltip=mat_summary(opm_mats))
    docs = button("btnVhpOpMDocs", docs_label(f"{OPM}.FileCount"),
                  att.open_fx("varVhpOpMNo"),
                  width=fit_button_width('"Docs (00)"'), height=32,
                  tooltip=docs_summary(OPM))
    # Udfyldt = groen kant, som Long text (issue #451).
    mark_done(mats, f"CountRows({opm_mats}) > 0")
    mark_done(docs, docs_done(OPM))
    rem = button("btnVhpOpMRemove", '"Remove"',
                 "RemoveIf(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo);\n"
                 'Set(varVhpOpMNo, "")', danger=True, width=fit_button_width('"Remove"'), height=32,
                 display_mode=DM_ITEM)
    # TELEFONEN (issue #508) - popuppen aabnes kun fra mobillisten: alle
    # felter og knapper er 44 px hoeje, og Remove (sletter linjen) staar for
    # sig selv under Materials og Docs i fuld bredde, ikke klos op ad dem.
    rem.props["Width"] = MODAL_CW
    for b in (mats, docs, rem):
        mobile.touch(b)
    actions = flow_row("conVhpOpMActions", [mats, docs], MODAL_CW, gap=8)

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
        longtext_preview(OPM, 24),
        ('Set(varVhpLongTextTarget, "op");\n'
         'Set(varVhpLongTextItemId, varVhpActiveItemId);\n'
         'Set(varVhpLongTextOpNo, varVhpOpMNo);\n'
         f'Set(varVhpLongTextDraft, Coalesce({OPM}.LongText, ""));\n'
         'Reset(inpVhpLongTextBox);\n'
         'Set(varVhpLongTextOpen, true)'),
        width=MODAL_CW, height=32, icon="DocumentText",
        display_mode=(f"If(varVhpViewOnly && IsBlank(Trim(Coalesce({OPM}.LongText, \"\"))), "
                      "DisplayMode.Disabled, DisplayMode.Edit)"),
        accessible='"Edit long text for operation " & varVhpOpMNo')
    # Samme piller som i tabellens raekke (build_strategy.pkg_pills).
    m_pills = f"({IS_STRATEGY} && {HAS_PKGS})"
    packages_txt = text_ctrl(
        "txtVhpOpMPackages",
        'If(varVhpPlan.PlanType <> "Strategy", "-", "(no packages)")',
        size=13, height=20, wrap="false", visible=f"!{m_pills}")
    packages_gal = pkg_pills("VhpOpM", "varVhpOpMNo", f"{OPM}.PackagesKey")
    # Telefonen (issue #508): hver pille kan trykkes paa 44 px hoejde.
    pill, pill_hit = packages_gal.children
    packages_gal.props["Height"] = lay.mobile_or(mobile.TOUCH + 4, packages_gal.props["Height"])
    packages_gal.h = packages_gal.props["Height"]
    pill.props["Y"] = lay.mobile_or((mobile.TOUCH - 26) // 2, pill.props["Y"])
    pill_hit.props["Y"] = lay.mobile_or("0", pill_hit.props["Y"])
    pill_hit.props["Height"] = lay.mobile_or(mobile.TOUCH, pill_hit.props["Height"])
    packages_gal.props["Visible"] = m_pills
    packages_gal.vis = m_pills
    packages = group("conVhpOpMPackages", [packages_txt, packages_gal], direction="Vertical", gap=0)
    for c in (opno, short, ctrl, vendor, price, matgrp, longtext):
        mobile.touch(c)
    for unit_row in (work, persons):
        # number_field med enhed er en raekke [felt, enhed] - foelg feltets hoejde.
        for k in unit_row.children:
            if k.control != "ModernText":
                mobile.touch(k)
        mobile.refit(unit_row)
    rem_gap = group("conVhpOpMRemoveGap", [], direction="Horizontal", height=12)
    return _modal("VhpOpM", '"Operation " & varVhpOpMNo', OPM_OPEN, 'Set(varVhpOpMNo, "")',
                  [label("L0", "Operation no."), opno, label("L1", "Short text"), short, label("L2", "Work (h)"), work,
                   label("L3", "Number of people"), persons, dur,
                   label("L4", "Control key"), ctrl, label("L5", "Supplier"), vendor,
                   label("L6", "Price"), price, label("L7", "Material group"), matgrp,
                   label("L8", "Long text"), longtext, label("L9", "Packages"), packages,
                   actions, rem_gap, rem], scroll=True)


def _ops_list_mobile():
    """Operationerne som kort under Tablet: et kort pr. operation, et tryk
    aabner popup'en (_op_detail_modal).

    Issue #508: to linjer i stedet for een afkortet - nummer og kort tekst
    oeverst, arbejde, personer, kontrolnoegle og materialer under, og en
    pil til hoejre. Listen er saa hoej som sine kort (ingen indre scroll)."""
    n_ops = "CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))"
    has_ops = f"IfError(!IsBlank(varVhpActiveItemId) && {n_ops} > 0, false)"
    row_h = 64
    line1 = text_ctrl(
        "txtVhpOpMRow",
        'ThisItem.OperationNo & "  " & If(IsBlank(Trim(ThisItem.OperationShortText)), '
        '"(no short text)", ThisItem.OperationShortText)',
        size=14, weight="Semibold", height=22, wrap="false",
        accessible='"Operation " & ThisItem.OperationNo & ": " & ThisItem.OperationShortText')
    mats = ("CountRows(Filter(colVhpMaterials, ItemId = ThisItem.ItemId && "
            "OperationNo = ThisItem.OperationNo))")
    line2 = text_ctrl(
        "txtVhpOpMRowMeta",
        (lay.num_text("ThisItem.WorkHours") + ' & " h  \u00b7  " & '
         'Text(Coalesce(ThisItem.Persons, 1)) & If(Coalesce(ThisItem.Persons, 1) = 1, " person", " people") & '
         '"  \u00b7  " & Coalesce(ThisItem.ControlKey, "-") & '
         f'If({mats} > 0, "  \u00b7  " & Text({mats}) & " mat.", "")'),
        size=12, color=C_MUTED, height=18, wrap="false")
    text_col = grow(group("conVhpOpMRowText", [line1, line2], direction="Vertical", gap=4))
    chev = text_ctrl("txtVhpOpMChev", '"\u203a"', size=lay.SIZE_CARD_TITLE, color=C_MUTED, height=24, width=16,
                     wrap="false")
    row = group("conVhpOpMRow", [text_col, chev], direction="Horizontal", gap=8,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth", fill=C_CARD_BG, pad=(0, 8, 0, 8))
    hit = row_hit("btnVhpOpMHit", "Set(varVhpOpMNo, ThisItem.OperationNo)",
                  '"Open operation " & ThisItem.OperationNo', "Parent.TemplateWidth",
                  "Parent.TemplateHeight - 2")
    from build_helpers import row_rule
    rule = row_rule("rctVhpOpMRule", row_h - 2)
    vis = f"{has_ops} && {below('Tablet')}"
    # + 2: TemplatePadding over foerste raekke (issue #506, se galVhpOps).
    gal_h = f"{n_ops} * {row_h} + 2"
    gal = Ctrl("galVhpOpsM", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Operations - select one to open it"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h,
        "Items": "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
        "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "2",
        "TemplateSize": str(row_h - 2), "Visible": vis, "Width": OPS_CW, "WrapCount": "1",
        "AlignInContainer": "AlignInContainer.Start",
    }, children=[row, rule, hit], h=gal_h, vis=vis)
    return gal


def build_ops_modals():
    """Popupperne fra operationsraekkens Materials- og Docs-knapper."""
    # Leverandoerpopup'en SIDST: den kan aabnes fra operationspopup'en
    # (smalle skaerme) og skal ligge oven paa den. Det samme for varegruppens.
    # Gemt sektion (issue #433): popupperne fra en laast sektion er
    # skrivebeskyttede, som i View. Dokumenterne gemmes for sig selv i
    # SharePoint (issue #300) og foelger ikke laasen.
    locked = lock_section([_op_detail_modal(), _materials_modal(), _vendor_modal(),
                           _matgrp_modal()], "varVhpViewOnly", OPS_LOCKED)
    return locked[:2] + [_attachments_modal()] + locked[2:]


# Tasklisterne til det valgte vaerk - Plant i Plan Header er den faelles
# kontekst (issue #54). Upper paa begge sider, saa store og smaa bogstaver
# ikke skjuler en gyldig liste. VhpPlant er det, der STAAR i Plan Header -
# ogsaa foer Save (issue #453). colVhpTasklists er en indlaest samling, saa
# filteret er lokalt (ingen delegering).
TL_ITEMS = f"Filter(colVhpTasklists, Upper(Plant) = Upper({PLANT}))"

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
    # OVERSKRIFTEN (issue #529), som Plan header: det groenne flueben
    # (status_icon) staar lige foran titlen, KUN naar sektionen er gyldig -
    # samme validering som det tidligere Valid-maerke (VhpOpsValid). Selve
    # maerket er vaek; til hoejre staar itemets Duration (issue #545: Total
    # cost staar nu i Item-sektionen).
    totals = totals_card()
    header = section_header("conVhpOpsHead", "Task list and operations", None,
                            extra_right=[totals])
    # Telefonen (issue #508): "Task list" - den lange titel og badget var
    # 324 px i et kort paa 248-288 px.
    mobile_head(header, short_title="Task list")
    # Et smalt tablet-vindue: titel, flueben og maerket (DUR_BADGE_MAX_W) kan
    # ikke staa paa een linje med den lange titel - saa den korte, ligesom
    # paa telefonen.
    title = header.children[0]
    full, short = mobile.desk(title.props["Text"]), mobile.phone(title.props["Text"])
    full_w, short_w = mobile.desk(title.props["Width"]), mobile.phone(title.props["Width"])
    need = f"{20 + int(full_w) + DUR_BADGE_MAX_W + 3 * 12}"
    title.props["Text"] = lay.mobile_or(short, fits(OPS_CW, need, short, full))
    title.props["Width"] = lay.mobile_or(short_w, fits(OPS_CW, need, short_w, full_w))
    title.props["LayoutMinWidth"] = title.props["Width"]
    ok = status_icon("icoVhpOpsHeadStatus", "VhpOpsValid", label_ok="Task list and operations: valid")
    ok.props["Visible"] = "IfError(VhpOpsValid, false)"
    ok.vis = ok.props["Visible"]
    ok.props["AlignInContainer"] = "AlignInContainer.Center"
    header.children.insert(0, ok)
    # Fast hoejde, naar maerket vises (DUR_BADGE_H) - se totals_card.
    # (mobile.refit kan ikke bruges: overskriftens LayoutGap er en mobil-If.)
    header.props["Height"] = str(row_height(header.children))
    header.h = header.props["Height"]
    header._auto = ("Horizontal", header.props["Height"])
    helpPanel = help_panel("conVhpOpsHelp", "ops")

    # Default slaar op i den FILTREREDE liste: en tasklist fra et andet
    # vaerk vises som tom, naar vaerket er skiftet, i stedet for som et
    # gyldigt valg.
    drpTasklist = themed_dropdown(
        "drpVhpItemTasklist", TL_ITEMS,
        f"LookUp({TL_ITEMS}, Key = LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey).Name",
        display_mode=DM_ITEM, value_col="Key", display_col="Name",
        # Itemets tasklist hoerer til et andet vaerk (issue #453): feltet
        # staar tomt (Default slaar op i den filtrerede liste) og roedt.
        required_formula="(" + tasklist_plant_conflict(
            "LookUp(colVhpItems, ItemId = varVhpActiveItemId).") + ")")
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
    mobile.touch(drpTasklist)
    # INGEN ETIKET (issue #542): "Task list *" og dens linje over feltet er
    # vaek - dropdownen staar direkte i raekken med knapperne, lige under
    # overskriften (der selv hedder Task list). Kravet er det samme: feltet
    # bliver roedt (BorderColor/ValidationState via required_formula), og
    # Save siger "Select a task list first.". Skaermlaeseren faar etiketten
    # og "required", som field_cell gav den.
    drpTasklist.props["Width"] = TL_W
    drpTasklist.props["LayoutMinWidth"] = TL_W
    drpTasklist.props["AccessibleLabel"] = '"Task list, required"'
    tasklistCell = drpTasklist

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
    # TELEFONEN (issue #508): de to knapper staar ogsaa paa en telefon - i
    # fuld bredde og 44 px hoeje under task listen. Foer var de gemt i en
    # dropdown ("Task list actions"), som man skulle vide, var en menu.
    for b in add_btns:
        b.props["Width"] = str(fit_button_width(b.props["Text"]) + ICON_W)
        b.props["LayoutMinWidth"] = b.props["Width"]
        b.vis = lay.mobile_or("true", at_least("Tablet"))
        mobile.touch(b)
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
    # Afloest af knapperne paa en telefon (se ovenfor). Kontrollen bliver
    # staaende (skjult), saa intet, der naevner den, brydes.
    opsMenu.vis = lay.mobile_or("false", below("Tablet"))
    # Duration-maerket staar i sektionsoverskriften (issue #529, #545).
    # Raekken her er kun task listen og knapperne - de staar paa samme
    # linje, bundjusteret med dropdownen. Telefonen: maerket nederst i
    # raekken (TOTALS_PHONE_ON).
    totalsPhone = totals_card("bdgVhpOpsDurationPhone", phone=True)
    tb_kids = [tasklistCell, btnAddLines, btnAddOp, opsMenu, totalsPhone]
    on_line = flow_ok(tb_kids, OPS_CW, 12)
    for b in [drpTasklist] + add_btns + [opsMenu]:
        b.props["AlignInContainer"] = f"If({on_line}, AlignInContainer.End, AlignInContainer.Start)"
    toolbar = flow_row("conVhpOpsToolbar", tb_kids, OPS_CW, gap=12)

    # Reset (kun dropdownen tilbage) er fjernet (UX-review): task listen
    # vaelges bare om. Sektionen afsluttes med Save (beslutning 1a,
    # 2026-10-13): kun Save draft skriver til SharePoint.
    #
    # SAVE/EDIT (issue #433), som Plan header: Save (foer Done) siger
    # "Saving..." mens den gemmer, og laaser sektionen for det aktive
    # item, naar den er gemt - knappen hedder saa Edit, og Edit laaser op
    # igen. Mangler der noget, er sektionen stadig aaben.
    save_fx = (
            "If(\n"
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
            # Gemt: sektionen laases. Ingen besked om Save draft (#433).
            "            Collect(colVhpSectionLocks, { ItemId: varVhpActiveItemId, Section: \"Ops\" });\n"
            f"            {act_mark(ACT, 'ops')}\n"
            "        )\n"
            "    )\n"
            ")"
    )
    btnTlSave = button(
        "btnVhpTasklistSave", f'If({OPS_LOCKED}, "Edit", "Save")',
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            f"    {OPS_LOCKED},\n"
            "    RemoveIf(colVhpSectionLocks, ItemId = varVhpActiveItemId && Section = \"Ops\"),\n"
            "\n"
            + act_fx(ACT, "ops", save_fx) + "\n"
            ")"
        ), primary=True, icon=f'If({OPS_LOCKED}, "Edit", "Checkmark")',
        # Bredt nok til "Saving..." (issue #433), saa foden staar stille.
        width=fit_button_width("\"Saving...\"", min_w=96) + ICON_W, height=36,
        display_mode=("If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, "
                      "btnVhpSaveDraft.DisplayMode)"))
    btnTlSave.props["AccessibleLabel"] = (f'If({OPS_LOCKED}, "Edit the task list and operations", '
                                          '"Save the task list and operations")')
    act_button(btnTlSave, ACT, "ops", text="Saving...", grow=False)

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
        longtext_preview("ThisItem", LT_PREVIEW_CHARS),
        (
            "Set(varVhpLongTextTarget, \"op\");\n"
            "Set(varVhpLongTextItemId, ThisItem.ItemId);\n"
            "Set(varVhpLongTextOpNo, ThisItem.OperationNo);\n"
            "Set(varVhpLongTextDraft, Coalesce(ThisItem.LongText, \"\"));\n"
            "Reset(inpVhpLongTextBox);\n"
            "Set(varVhpLongTextOpen, true)"
        ),
        width=w["LONG TEXT"], height=32,
        display_mode=("If(varVhpViewOnly && IsBlank(Trim(Coalesce(ThisItem.LongText, \"\"))), "
                      "DisplayMode.Disabled, DisplayMode.Edit)"),
        accessible='"Edit long text for operation " & ThisItem.OperationNo')
    mark_done(btnOpLongText, "!IsBlank(Trim(Coalesce(ThisItem.LongText, \"\")))")
    # Samme 12 px som de andre knapper i raekken (Vendor, Materials, Docs).
    btnOpLongText.props["Size"] = "12"

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
                           gap=0, height=32, width=w["PACKAGES"], align_items="Center",
                           visible=PKG_COL_ON)

    OP_MATS = ("Filter(colVhpMaterials, ItemId = ThisItem.ItemId && "
               "OperationNo = ThisItem.OperationNo)")
    btnOpMat = button(
        "btnVhpOpMaterials", f'"Materials (" & Text(CountRows({OP_MATS})) & ")"',
        mat_open_fx("ThisItem.OperationNo"), width=w["MATERIALS"], height=32,
        accessible='"Materials for operation " & ThisItem.OperationNo',
        tooltip=mat_summary(OP_MATS))
    btnOpDocs = button(
        # Dokumenterne er vedhaeftninger paa operationens raekke (issue
        # #300) og hentes foerst, naar popuppen aabnes. Antallet kendes
        # foerst derefter (FileCount, #336) - indtil da blot "Docs".
        "btnVhpOpDocs", docs_label("ThisItem.FileCount"),
        att.open_fx("ThisItem.OperationNo"), width=w["DOCS"], height=32,
        accessible='"Documents for operation " & ThisItem.OperationNo',
        tooltip=docs_summary("ThisItem"))
    for b_ in (btnOpMat, btnOpDocs):
        b_.props["Size"] = "12"
    mark_done(btnOpMat, f"CountRows({OP_MATS}) > 0")
    # Docs (n) ogsaa groen, naar der er gemte filer (issue #451).
    mark_done(btnOpDocs, docs_done("ThisItem"))

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
    # INGEN INDRE SCROLL (issue #506). Med TemplatePadding 2 fylder n
    # raekker n x (44 + 2) + 2: der er ogsaa padding over foerste raekke.
    # Var hoejden kun n x 46, var indholdet 2 px hoejere end galleriet, og
    # musehjulet over operationerne rullede galleriet et lille hak i stedet
    # for siden. Nu er galleriet praecis saa hoejt som sit indhold.
    n_ops = "CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))"
    has_ops = f"IfError(!IsBlank(varVhpActiveItemId) && {n_ops} > 0, false)"
    gal_h = f"{n_ops} * {OPS_ROW_H} + 2"
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

    # Tabellen har fast bredde (summen af kolonnerne). Paa smalle skaerme
    # scroller den vandret i stedet for at klippe kolonner af.
    opsTableWrap = group("conVhpOpsTableWrap",
                         [opsHeader, opsDivider, gallery, opsEmpty],
                         direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                         align_items="Start", visible=at_least("Tablet"))

    # Operationstabellen er fanen Operations - sammen med tasklist-vaelgeren
    # og de fire operationsknapper. De laa foer i kortet uden for ruderne, og
    # saa blev "Add operation" staaende paa materialefanen, hvor den ikke
    # hoerer hjemme. Hver fane ejer nu sine egne knapper, praecis som
    # materialeruden allerede gjorde.
    opsEmptyM = empty_state("conVhpOpsEmptyM", OPS_EMPTY, icon_path=icons.LIST,
                            visible=f"!{has_ops} && {below('Tablet')}")
    opsPane = group("conVhpOpsPane", [toolbar, tasklistMeta, opsHint, opsTableWrap, _ops_list_mobile(),
                                      opsEmptyM],
                    direction="Vertical", gap=8, width="Parent.Width",
                    visible=OPS_PANE_ON)
    pkgPane = build_strategy_body()
    pkgPane.vis = PKG_PANE_ON
    tabBar = _tab_bar_if_strategy()

    # Fanebjaelken staar oeverst, lige under sektionshovedet: foerst vaelger
    # man fanen, saa ser man dens indhold. Den laa foer under baade
    # tasklist-vaelgeren og knapraekken, og saa stod selve skiftet nederst i
    # den halvdel af kortet, der ikke aendrede sig.
    # GEMT = SKRIVEBESKYTTET (issue #433): task listen, operationerne,
    # pakkerne og materialerne laases, som i View mode, til der trykkes Edit.
    lock_section([opsPane, pkgPane, opsFooter], "varVhpViewOnly", OPS_LOCKED,
                 keep={"btnVhpTasklistSave"})
    return card("conVhpOpsCard",
                [header, helpPanel, tabBar,
                 opsPane, pkgPane, opsFooter])
