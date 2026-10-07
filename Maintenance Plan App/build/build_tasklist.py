# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_WHITE, C_MODAL_BG, C_PRIMARY_SOFT,
                        C_INVALID_FG, C_DIVIDER, C_TRANSPARENT, SHELL_W)
import layout_tokens as lay
from build_helpers import (checkbox_theme, table_surface, flow_row, text_ctrl,
                           group, button, text_input, number_input, themed_dropdown,
                           field_cell, card, pin_widths, grow, row_hit,
                           fit_button_width, fit_button_row, ICON_W, ICON_SAVE, flow_ok, mark_done)
from build_plan_header import (section_header, help_panel, summary_chips, summary_formula,
                               summary_width, collapse_footer)
from build_status import HAS_PKGS
import build_help as bh
from build_strategy import build_strategy_body, IS_STRATEGY
import sp_config as cfg
from design_tokens import ref_hex
from layout_tokens import SCROLLBAR_W, fits, TWO_COL_MIN, below, at_least, if_below

# HTML kender ikke RGBA(). ref_hex giver den SAMME token som hex.
MUT_HEX = ref_hex("text-muted")
BG_HEX = ref_hex("bg-muted")
PRI_HEX = ref_hex("text-primary")
import build_attflows
import doc_upload as du

# Flowkontrakten staar i tools/attflows.py; kun rudens egne navne
# og dens refresh_fx() staar i build_attflows.py.
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
    ("PACKAGES", 110),
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

# PM03 er eksternt arbejde, og prisen i standardarbejdsplanen er en TIMESATS
# (Work staar som 1 paa hver linje, og Price er satsen: SSVXSTIL 494,
# SSVXISOL 420). Beloebet er derfor timer gange sats, og det skal foelge med,
# naar timerne rettes. Ved PM02 taster man selv beloebet; ved PM01 og ZB01 er
# der ingen.
IS_PM03 = 'Upper(Coalesce(ThisItem.ControlKey, "")) = "PM03"'


def cost_expr(work):
    return (f'If(\n'
            f'            {IS_PM03},\n'
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

# Timer og antal kan vaere halve; kroner vises med to decimaler. Formatet er
# laast til en kultur, saa tusindtalsseparatoren ikke skifter med brugerens
# sprogindstilling midt i en tabel.
_TOTALS = {
    "WORK (H)": f'Text(Sum({OPS_ACTIVE}, WorkHours), "[$-en-US]#,##0.##")',
    "NO.":      f'Text(Sum({OPS_ACTIVE}, Persons), "[$-en-US]#,##0.##")',
    "DUR. (H)": f'Text(Sum({OPS_ACTIVE}, DurationHours), "[$-en-US]#,##0.##")',
    "COST":     f'Text(Sum({OPS_ACTIVE}, Cost), "[$-en-US]#,##0.00")',
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
TABS = [
    ("ops", "Operations", None),
    ("pkg", "Maintenance packages", IS_STRATEGY),
]


def _tab_on(key):
    return f'IfError(varVhpOpsTab = "{key}", false)'


def _tab_bar():
    kids = []
    for key, label, cond in TABS:
        on = _tab_on(key)
        b = button(f"btnVhpTab{key.capitalize()}", f'"{label}"',
                   f'Set(varVhpOpsTab, "{key}")', width=168, height=34)
        b.props["Appearance"] = f"If({on}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
        b.props["BasePaletteColor"] = C_PRIMARY
        b.props["Color"] = f"If({on}, {C_WHITE}, {C_TITLE})"
        b.props["BorderColor"] = C_CARD_BORDER
        b.props["BorderThickness"] = "1"
        b.props["Size"] = "13"
        if cond:
            b.vis = f"IfError({cond}, false)"
        kids.append(b)
    # Enten een linje, eller een fane pr. linje - build_helpers.flow_row.
    # wrap_row_height() regnede med hoejst to linjer; paa en smal skaerm
    # blev det fire, og de to nederste faner var klippet vaek.
    return flow_row("conVhpOpsTabBar", kids, OPS_CW, gap=6)


def _tab_bar_if_strategy():
    bar = _tab_bar()
    bar.vis = f"IfError({IS_STRATEGY}, false)"
    bar.props["Visible"] = bar.vis
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


def _modal(name, title, open_var, close_fx, kids, width=620, scroll=False):
    """En popup i appens moenster (som tasklist-pickeren): centreret,
    sloer bag (build_modal.build_modal_backdrop), titel og luk-knap.
    scroll: titel og Close staar fast, indholdet scroller."""
    t = grow(text_ctrl(f"txt{name}Title", title, size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26,
                       wrap="false"))
    close = button(f"btn{name}Close", '"Close"', close_fx,
                   width=fit_button_width('"Close"'), height=32)
    head = group(f"con{name}HeadRow", [t, close], direction="Horizontal", gap=12,
                 height=32, align_items="Center")
    if scroll:
        body_h = "Max(200, App.Height - 150)"
        body = group(f"con{name}Body", kids, direction="Vertical", gap=8, height=body_h,
                     overflow_y="Scroll")
        kids = [body]
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
            "Notify(\"Removed selected material line(s).\", NotificationType.Success)"
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
    numQty = number_input("numVhpMatQty", "ThisItem.Quantity", width=w["QTY"], height=30, label="\"Quantity\"")
    numQty.props["OnChange"] = "Patch(colVhpMaterials, ThisItem, { Quantity: Self.Value })"
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

    empty = text_ctrl("txtVhpMatEmpty",
                      '"No materials on this operation yet. Use Add material to add one."',
                      size=13, color=C_MUTED, height=24, wrap="false",
                      visible=f"IfError(CountRows({MAT_OP}) = 0, false)")

    note = text_ctrl("txtVhpMatNote",
                     '"Description and Unit are filled in by the material lookup. '
                     'Until it is in place they stay empty."',
                     size=12, color=C_MUTED, height=32, wrap="true")

    # Start, ikke Stretch: tabellen har sin egen bredde og scroller vandret
    # paa en smal skaerm i stedet for at blive klemt sammen.
    table = group("conVhpMatTableWrap", [header, divider, gallery, empty],
                  direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                  align_items="Start")

    return _modal("VhpMat", '"Materials - operation " & varVhpMatOpNo', MAT_OPEN,
                  'Set(varVhpMatOpNo, "")', [actions, note, table])


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


# Er dokumentet koblet til den operation, popup'en er aabnet for?
ATT_LINKED = "\";\" & varVhpAttOpNo & \";\" in Coalesce(ThisItem.OperationsKey, \";\")"


# Maa der laegges op, slettes og kobles? Ikke i View-tilstand, og ikke
# naar operationerne er gemt og laast (OPS_LOCKED) - koblingen gemmes med
# operationerne, og Save er spaerret, saa laenge de er laast (issue #134).
def _att_edit():
    return f"(!IfError(varVhpViewOnly, false) && !{OPS_LOCKED})"


# Luk dokumentpopuppen: glem de valgte filer og omgangens svar.
ATT_CLOSE = 'Set(varVhpAttOpNo, "");\n' + att.close_fx()


def _attachments_modal():
    """Dokumenter for EEN operation - aabnet fra operationens Docs-knap.

    Listen er itemets dokumenter, og afkrydsningen kobler et dokument til
    operationen eller fra den. Et dokument uden operationer hoerer til hele
    itemet - koblingen er stadig OperationsKey ";0010;0020;".

    Et dokument, der uploades HERFRA, kobles til operationen med det samme:
    colVhpAttUp er, hvad flowet svarede paa hver fil ved uploaden.

    Opbygningen (issue #134) er den faelles i tools/doc_upload.py: den
    moderne Attachments-kontrol, een Upload, og pr. dokument filtype, Open
    og Remove."""
    edit = _att_edit()
    pick = du.picker(att.picker, '"Choose documents for operation " & varVhpAttOpNo', 10, 50,
                     visible=edit,
                     display_mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    limits = du.limits_text("txtVhpAttLimits", 10, 50, visible=edit)

    link_new = (
        "UpdateIf(\n"
        "    colVhpAttachments,\n"
        "    ItemId = varVhpActiveItemId &&\n"
        "        FileName in Filter(colVhpAttUp, Ok).Name &&\n"
        "        !(\";\" & varVhpAttOpNo & \";\" in Coalesce(OperationsKey, \";\")),\n"
        "    { OperationsKey: Coalesce(OperationsKey, \";\") & varVhpAttOpNo & \";\" }\n"
        ")")
    btnUpload = du.upload_button("btnVhpAttUpload", att.picker,
                                 att.upload_fx() + ";\n" + link_new, att.busy, visible=edit)
    btnRefresh = button("btnVhpAttRefresh", '"Refresh"', att.refresh_button_fx(),
                        width=fit_button_width('"Refresh"'), height=36,
                        accessible='"Refresh the document list"',
                        display_mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    btnRefresh.props["LayoutMinWidth"] = btnRefresh.props["Width"]
    actions = group("conVhpAttActions", [btnRefresh, btnUpload],
                    direction="Horizontal", gap=8, height=36, justify="End",
                    align_items="Center")
    status = du.status_text("txtVhpAttStatus", att)
    confirm = du.remove_confirm("VhpAtt", att)

    file = "ThisItem.FileName"
    badge_ = du.type_badge("txtVhpAttType", file)
    txtName = grow(text_ctrl("txtVhpAttName", file, size=13, height=30, wrap="false"))
    wide = at_least("Tablet")
    txtScope = text_ctrl(
        "txtVhpAttScope",
        (
            "If(\n"
            "    Len(Coalesce(ThisItem.OperationsKey, \";\")) <= 1,\n"
            "    \"Whole item\",\n"
            "    \"Ops: \" & Substitute(Mid(ThisItem.OperationsKey, 2), \";\", \" \")\n"
            ")"
        ), size=12, color=C_MUTED, height=30, width=110, wrap="false", visible=wide)
    chkLink = Ctrl("chkVhpAttOp", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Attach " & ThisItem.FileName & " to operation " & varVhpAttOpNo',
        "Default": ATT_LINKED,
        "DisplayMode": f"If({edit} && !{att.busy}, DisplayMode.Edit, DisplayMode.View)",
        "Height": "24",
        # Paa en telefon er der ikke plads til ordene - noten over listen
        # siger, hvad boksen goer.
        "Label": f'If({wide}, "This operation", "")',
        "OnCheck": (
            "With(\n"
            "    { fn: ThisItem.FileName },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && FileName = fn &&\n"
            "            !(\";\" & varVhpAttOpNo & \";\" in Coalesce(OperationsKey, \";\")),\n"
            "        { OperationsKey: Coalesce(OperationsKey, \";\") & varVhpAttOpNo & \";\" }\n"
            "    )\n"
            ")"
        ),
        "OnUncheck": (
            "With(\n"
            "    { fn: ThisItem.FileName },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && FileName = fn,\n"
            "        { OperationsKey: Substitute(Coalesce(OperationsKey, \";\"), "
            "\";\" & varVhpAttOpNo & \";\", \";\") }\n"
            "    )\n"
            ")"
        ),
        "Width": f"If({wide}, 130, 32)",
    }), h=24)
    chkLink.props["LayoutMinWidth"] = chkLink.props["Width"]
    link = du.open_button("btnVhpAttOpen", "ThisItem.FileUrl", file)
    rem = du.remove_button("btnVhpAttRemove", att, file, edit)

    row = group("conVhpAttRow", pin_widths([badge_, txtName, txtScope, chkLink, link, rem]),
                direction="Horizontal", gap=8, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    # Hele listen staar i galleriet; er der flere, end popuppen kan vise,
    # scroller popuppens indhold - ikke galleriet i den.
    gal_h = f"CountRows({ATT_ACTIVE}) * {du.ROW_H}"
    gallery = Ctrl("galVhpAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents for active item"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": gal_h,
        # Filnavnet er noeglen paa raekken - der ER ingen LineId paa
        # dokumenterne.
        "Items": f"Sort({ATT_ACTIVE}, FileName)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "false",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(du.ROW_H - 2),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)
    table_surface(gallery, "rctVhpAttRule")

    empty = text_ctrl("txtVhpAttEmpty", att.empty_text_fx(),
                      size=13, color=C_MUTED, height=36, wrap="true",
                      visible=f"IfError(CountRows({ATT_ACTIVE}) = 0, false)")

    note = text_ctrl("txtVhpAttNote",
                     '"Tick the box on a document to attach it to operation " & varVhpAttOpNo & '
                     '". A document with no operations belongs to the whole item."',
                     size=12, color=C_MUTED, height=32, wrap="true",
                     visible=f"{edit} && CountRows({ATT_ACTIVE}) > 0")
    ro = du.readonly_note("txtVhpAttReadOnly", f"!{edit}")

    # Popuppen: 20 + 20 luft til skaermkanten, 18 + 18 polstring, hovedet
    # (32) og afstanden (12) - resten er indholdet.
    body = du.capped_body("conVhpAttBody",
                          [pick, limits, actions, status, confirm, note, gallery, empty, ro],
                          "App.Height - 40 - 36 - 32 - 12")
    modal = _modal("VhpAtt", '"Documents · Operation " & varVhpAttOpNo', ATT_OPEN,
                   ATT_CLOSE, [body])
    # Close er den eneste vej ud - men ikke midt i en upload.
    for c in modal.children[0].children:
        if c.name == "btnVhpAttClose":
            c.props["DisplayMode"] = f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)"
    return modal


OPM_OPEN = "!IsBlank(varVhpOpMNo)"
OPM = "LookUp(colVhpOperations, ItemId = varVhpActiveItemId && OperationNo = varVhpOpMNo)"


def _op_detail_modal():
    """En operationslinje i en popup - kun i smalle skaerme, hvor tabellen
    med femten kolonner ikke kan laeses. Samme felter som tabellens vigtigste
    kolonner, og de samme Patch-formler paa samme samling."""
    def label(name, text):
        return text_ctrl(f"txtVhpOpM{name}", f'"{text}"', size=12, color=C_MUTED,
                         height=18, wrap="false")

    short = text_input("inpVhpOpMText", f"{OPM}.OperationShortText", width=MODAL_CW, height=32,
                       onchange=f"Patch(colVhpOperations, {OPM}, {{ OperationShortText: Self.Text }})",
                       label='"Operation text"')
    work = number_input("numVhpOpMWork", f"{OPM}.WorkHours", width=MODAL_CW, height=32,
                        label='"Work hours"')
    cost = cost_expr("Self.Value").replace("ThisItem", "r")
    work.props["OnChange"] = (
        "With(\n    { r: " + OPM + " },\n    Patch(\n        colVhpOperations, r,\n"
        "        {\n            WorkHours: Self.Value,\n"
        f"            DurationHours: {cfg.duration_expr('Self.Value', 'r.Persons')},\n"
        f"            Cost: {cost}\n        }}\n    )\n)")
    persons = number_input("numVhpOpMPersons", f"{OPM}.Persons", width=MODAL_CW, height=32,
                           label='"Number of people"')
    persons.props["OnChange"] = (
        "With(\n    { r: " + OPM + " },\n    Patch(\n        colVhpOperations, r,\n"
        "        {\n            Persons: Self.Value,\n"
        f"            DurationHours: {cfg.duration_expr('r.WorkHours', 'Self.Value')}\n        }}\n    )\n)")
    dur = text_ctrl("txtVhpOpMDur",
                    f'"Duration: " & Text({OPM}.DurationHours, "[$-en-US]#,##0.##") & " h   Work center: " & '
                    f'Coalesce({OPM}.MainWorkCenter, "-")', size=13, color=C_MUTED, height=20,
                    wrap="false")
    mats = button("btnVhpOpMMat", f'"Materials (" & Text(CountRows(Filter(colVhpMaterials, ItemId = varVhpActiveItemId && '
                  f'OperationNo = varVhpOpMNo))) & ")"', "Set(varVhpMatOpNo, varVhpOpMNo)",
                  width=fit_button_width('"Materials (00)"'), height=32)
    docs = button("btnVhpOpMDocs", '"Docs"', "Set(varVhpAttOpNo, varVhpOpMNo)",
                  width=fit_button_width('"Docs"'), height=32)
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
    vendor = text_input("inpVhpOpMVendor", f"{OPM}.Vendor", width=MODAL_CW, height=32,
                        display_mode=on_op(DM_PURCHASE),
                        onchange=f"Patch(colVhpOperations, {OPM}, {{ Vendor: Self.Text }})",
                        label='"Supplier"')
    price = number_input("numVhpOpMCost", f"{OPM}.Cost", width=MODAL_CW, height=32,
                         display_mode=on_op(DM_PURCHASE), label='"Price"')
    price.props["OnChange"] = f"Patch(colVhpOperations, {OPM}, {{ Cost: Self.Value }})"
    matgrp = text_input("inpVhpOpMMatGrp", f"{OPM}.MaterialGroup", width=MODAL_CW, height=32,
                        display_mode=on_op(DM_PURCHASE),
                        onchange=f"Patch(colVhpOperations, {OPM}, {{ MaterialGroup: Self.Text }})",
                        label='"Material group"')
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
    packages = text_ctrl(
        "txtVhpOpMPackages",
        ('If(varVhpPlan.PlanType <> "Strategy", "-", With({ sel: Filter(colVhpStrategyPackages As P, '
         'P.StrategyKey = varVhpPlan.Strategy && ";" & Text(P.PackageNo) & ";" in '
         f'Coalesce({OPM}.PackagesKey, ";")) }}, If(CountRows(sel) = 0, "(none)", '
         'Concat(Sort(sel, PackageNo), ShortCode, ", "))))'),
        size=13, height=20, wrap="false")
    return _modal("VhpOpM", '"Operation " & varVhpOpMNo', OPM_OPEN, 'Set(varVhpOpMNo, "")',
                  [label("L1", "Short text"), short, label("L2", "Work (h)"), work,
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
        'Text(ThisItem.WorkHours, "[$-en-US]#,##0.##") & " h"',
        size=13, height=24, wrap="false"))
    chev = text_ctrl("txtVhpOpMChev", '"\u203a"', size=18, color=C_MUTED, height=24, width=16,
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
    return [_op_detail_modal(), _materials_modal(), _attachments_modal()]


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

# SAMLET SAMMEN, NAAR SEKTIONEN ER GEMT (issue #103) - Plan Headers
# moenster (varVhpPlanLocked) for Tasklist and Operations. Sektionen hoerer
# til det AKTIVE item, saa tilstanden er pr. item: colVhpOpsDone holder de
# items, hvis tasklist og operationer er gemt i SharePoint. Save saetter
# varVhpOpsSavePending, og foerst naar gemningen er lykkedes, kommer itemet i
# colVhpOpsDone (build_save.save_action). Edit tager det ud igen. En aabnet
# kladde starter med de items, der allerede er komplette (build_load).
# CountRows, saa layout-tjekket kan regne paa synligheden (se build_items).
OPS_LOCKED = ("(!IsBlank(varVhpActiveItemId) && "
              "CountRows(Filter(colVhpOpsDone, ItemId = varVhpActiveItemId)) > 0)")
# Det modsatte, skrevet ud: layout-tjekket kan ikke regne paa !( ... ).
OPS_OPEN = ("(IsBlank(varVhpActiveItemId) || "
            "CountRows(Filter(colVhpOpsDone, ItemId = varVhpActiveItemId)) = 0)")
# Linjen vises paa alle bredder (issue #123) - chipsene ombrydes.
OPS_SUMMARY_VIS = OPS_LOCKED

# Hvad der mangler, foer sektionen kan gemmes og klappes sammen - tom, naar
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


# Save/Edit-knappens bredde - linjen har resten af kortets bredde.
OPS_SAVE_W = fit_button_width("\"Save\"", min_w=96) + ICON_W


def ops_summary_fx():
    """Tasklist and Operations' sammenklappede linje (issue #123) for det
    valgte item. Tallene er operationstabellens egne (samme kolonner og
    format som _TOTALS) og kommer fra de samme samlinger som tabellen,
    materialeruden og dokumentruden. Et tal, der er nul, giver ingen chip."""
    num = '"[$-en-US]#,##0.##"'
    def tot(col, fmt=num):
        return f'With({{ t: Sum(ops, {col}) }}, If(Coalesce(t, 0) = 0, "", Text(t, {fmt})))'
    def cnt(tbl):
        return f'With({{ n: CountRows({tbl}) }}, If(n = 0, "", Text(n)))'
    segs = [('"TASK LIST"', 'Coalesce(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistName, "")'),
            ('"OPERATIONS"', cnt("ops")),
            ('"WORK (H)"', tot("WorkHours")),
            ('"DURATION (H)"', tot("DurationHours")),
            ('"PEOPLE"', tot("Persons")),
            ('"COST"', tot("Cost", '"[$-en-US]#,##0.00"')),
            ('"MATERIALS"', cnt(MAT_ACTIVE)),
            ('"DOCUMENTS"', cnt("Filter(colVhpAttachments, ItemId = varVhpActiveItemId)"))]
    return summary_formula(segs, summary_width(OPS_CW, OPS_SAVE_W), bind={"ops": OPS_ACTIVE})


def build_tasklist_section():
    # Trin-badget (issue #123): "Valid", naar alle items har tasklist og
    # operationer, og ingen tasklist-/operationsregel fejler.
    header = section_header("conVhpOpsHead", "Tasklist and Operations", "Step 3",
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
        "Notify(\"Tasklist \" & drpVhpItemTasklist.Selected.Key & \" selected for this item.\", NotificationType.Success)")
    drpTasklist.props["OnChange"] = (
        "If(\n"
        "    !IsBlank(varVhpActiveItemId) && !IsBlank(Self.Selected.Key) &&\n"
        "        Self.Selected.Key <> LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey,\n"
        + APPLY_TL.replace("\n", "\n    ").join(["    ", "\n"]) +
        ")")
    # Tasklist-feltet har en fast, begraenset bredde og staar til venstre.
    TL_W = fits(OPS_CW, TWO_COL_MIN, OPS_CW, "360")
    tasklistCell = field_cell("conVhpCellTasklist", "Tasklist For Active Item", drpTasklist, required=True,
                              width=TL_W, container_w=OPS_CW, fill_portions_formula="0")

    btnAddLines = button(
        "btnVhpAddTasklistLines", "\"Lines from tasklist\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        Notify(\"Select a tasklist first.\", NotificationType.Warning),\n"
            "        Clear(colVhpPickerSelected);\n"
            "        Reset(inpVhpPickerSearch);\n"
            "        Set(varVhpTasklistPickerOpen, true)\n"
            "    )\n"
            ")"
        # Sekundaer outline som Manual operation (issue #157): Save er
        # sektionens eneste primaere, blaa handling.
        ), display_mode=DM_ITEM, icon="Add",
        accessible="\"Add lines from the tasklist\"",
        tooltip="\"Add operation lines from the selected tasklist\"")

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
            "            OperationNo: Text(Coalesce(Max(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo)), 0) + 10, \"0000\"),\n"
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
        'Table({ Value: "Add lines from tasklist" }, { Value: "Add manual operation" })',
        '""', width="190", height=36, label='"Tasklist actions"',
        onchange=(
            "Switch(\n"
            "    Self.Selected.Value,\n"
            f"    \"Add lines from tasklist\", {btnAddLines.props['OnSelect']},\n"
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

    btnTlReset = button(
        "btnVhpTasklistReset", "\"Reset\"",
        "Reset(drpVhpItemTasklist);\n"
        "Notify(\"Tasklist selection reset.\", NotificationType.Information)",
        width=fit_button_width("\"Reset\""), height=36, display_mode=DM_ITEM)
    btnTlSave = button(
        "btnVhpTasklistSave", "\"Save\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    IsBlank(drpVhpItemTasklist.Selected.Key),\n"
            "    Notify(\"Select a tasklist first.\", NotificationType.Warning),\n"
            # Ufuldstaendig sektion: gem ikke, og bliv foldet ud (issue #103).
            "    With(\n"
            "        { issue: " + OPS_ISSUE.replace("\n", "\n        ") + " },\n"
            "        If(\n"
            "            !IsBlank(issue),\n"
            "            Notify(issue, NotificationType.Warning),\n"
            "            UpdateIf(\n"
            "                colVhpItems, ItemId = varVhpActiveItemId,\n"
            "                { TasklistKey: drpVhpItemTasklist.Selected.Key, TasklistName: drpVhpItemTasklist.Selected.Name }\n"
            "            );\n"
            # Sektionen klappes foerst sammen, naar gemningen er lykkedes
            # (build_save.save_action laeser varVhpOpsSavePending).
            "            Set(varVhpOpsSavePending, varVhpActiveItemId);\n"
            "            Select(btnVhpSaveDraft)\n"
            "        )\n"
            "    )\n"
            ")"
        ), primary=True, icon=ICON_SAVE,
        width=fit_button_width("\"Save\"", min_w=96) + ICON_W, height=36,
        display_mode=("If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, "
                      "btnVhpSaveDraft.DisplayMode)"))
    # SAVE ELLER EDIT (issue #103) - samme knap som i Plan Header. Edit
    # tager kun det aktive item ud af colVhpOpsDone; andre items og andre
    # sektioner roeres ikke. Edit vises kun i Edit mode.
    btnTlSave.props["Text"] = f'If({OPS_LOCKED}, "Edit", "Save")'
    btnTlSave.props["Icon"] = f'If({OPS_LOCKED}, "Edit", "{ICON_SAVE}")'
    btnTlSave.props["OnSelect"] = (
        f"If(\n    {OPS_LOCKED},\n    RemoveIf(colVhpOpsDone, ItemId = varVhpActiveItemId),\n\n"
        + btnTlSave.props["OnSelect"] + "\n)")
    btnTlSave.props["DisplayMode"] = (
        f"If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, "
        f"{OPS_LOCKED}, DisplayMode.Edit, btnVhpSaveDraft.DisplayMode)")
    btnTlSave.props["AccessibleLabel"] = (
        f'If({OPS_LOCKED}, "Edit the task list and operations", "Save the task list and operations")')
    btnTlSave.vis = f"(!varVhpViewOnly || {OPS_OPEN})"
    btnTlReset.vis = f"{OPS_OPEN}"

    # DEN SAMMENKLAPPEDE LINJE (issue #103, #123) - Plan Headers chips:
    # tasklisten og de vigtigste tal, ikke hele tabellen. Paa alle bredder;
    # layoutet er den navngivne formel VhpOpsSummary (ops_summary_fx).
    summary = summary_chips("htmVhpOpsSummary", "VhpOpsSummary", OPS_SUMMARY_VIS)
    # Foldet ud: hvad der mangler, foer sektionen kan gemmes.
    attention = text_ctrl(
        "txtVhpOpsAttention",
        f'With({{ issue: {OPS_ISSUE} }}, If(IsBlank(issue), "Save to collapse the section.", issue))',
        size=12, height=36, wrap="true",
        visible=f"({OPS_OPEN} && !IsBlank(varVhpActiveItemId) && !varVhpViewOnly)",
        extra={"Color": f"If(IsBlank({OPS_ISSUE}), {C_MUTED}, {C_INVALID_FG})",
               "VerticalAlign": "VerticalAlign.Middle"})
    footerInfo = grow(group("conVhpOpsFooterInfo", [summary, attention],
                            direction="Vertical", gap=0, justify="Center"))
    # Hoejden foelger linjen, naar chipsene ombrydes (issue #123).
    opsFooter = collapse_footer(
        group("conVhpOpsFooter", [footerInfo, btnTlReset, btnTlSave], direction="Horizontal",
              gap=8, align_items="Center", justify="End"),
        footerInfo, btnTlSave, OPS_LOCKED)

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
    txtOpNo = text_ctrl("txtVhpOpNo", "ThisItem.OperationNo", size=13, height=32, width=w["OP NO."], wrap="false")
    txtOpShort = text_input("inpVhpOpShortText", "ThisItem.OperationShortText", width=w["OPERATION SHORT TEXT"],
                            height=32,
                            onchange="Patch(colVhpOperations, ThisItem, { OperationShortText: Self.Text })", label="\"Operation text\"")
    # Work og No. skriver BEGGE varigheden, fordi den er regnet af dem
    # begge. Gjorde kun den ene det, ville et skift i den anden efterlade en
    # varighed, der ikke passer til linjen - og det er varigheden, der
    # gemmes i TaskListMain.Duration og sendes videre til SAP.
    numOpWork = number_input("numVhpOpWork", "ThisItem.WorkHours", width=w["WORK (H)"], height=32, label="\"Work hours\"")
    numOpWork.props["OnChange"] = (
        "Patch(\n"
        "    colVhpOperations, ThisItem,\n"
        "    {\n"
        "        WorkHours: Self.Value,\n"
        f"        DurationHours: {cfg.duration_expr('Self.Value', 'ThisItem.Persons')},\n"
        f"        Cost: {cost_expr('Self.Value')}\n"
        "    }\n"
        ")")
    numOpPersons = number_input("numVhpOpPersons", "ThisItem.Persons", width=w["NO."], height=32, label="\"Number of people\"")
    numOpPersons.props["OnChange"] = (
        "Patch(\n"
        "    colVhpOperations, ThisItem,\n"
        "    {\n"
        "        Persons: Self.Value,\n"
        f"        DurationHours: {cfg.duration_expr('ThisItem.WorkHours', 'Self.Value')}\n"
        "    }\n"
        ")")
    # Varigheden vises, men tastes ikke - den ER Work / No.
    numOpDur = number_input("numVhpOpDur", "ThisItem.DurationHours", width=w["DUR. (H)"], height=32,
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

    txtOpVendor = text_input("inpVhpOpVendor", "ThisItem.Vendor", width=w["VENDOR"], height=32,
                             display_mode=DM_PURCHASE,
                             onchange="Patch(colVhpOperations, ThisItem, { Vendor: Self.Text })", label="\"Supplier\"")
    numOpCost = number_input("numVhpOpCost", "ThisItem.Cost", width=w["COST"], height=32,
                             display_mode=DM_PURCHASE, label="\"Price\"")
    numOpCost.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { Cost: Self.Value })"
    txtOpMatGrp = text_input("inpVhpOpMatGrp", "ThisItem.MaterialGroup", width=w["MAT.GRP"],
                             height=32, display_mode=DM_PURCHASE,
                             onchange="Patch(colVhpOperations, ThisItem, { MaterialGroup: Self.Text })", label="\"Material group\"")
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

    # Pakkerne redigeres i matricen nedenfor - her vises kun resultatet, saa
    # operationslinjen og allokeringen kan laeses samme sted.
    txtOpPackages = text_ctrl(
        "txtVhpOpPackages",
        (
            "If(\n"
            "    varVhpPlan.PlanType <> \"Strategy\", \"-\",\n"
            "    With(\n"
            "        { sel: Filter(colVhpStrategyPackages As P, P.StrategyKey = varVhpPlan.Strategy && \";\" & Text(P.PackageNo) & \";\" in Coalesce(ThisItem.PackagesKey, \";\")) },\n"
            "        If(CountRows(sel) = 0, \"(none)\", Concat(Sort(sel, PackageNo), ShortCode, \", \"))\n"
            "    )\n"
            ")"
        ),
        size=12, height=32, width=w["PACKAGES"], wrap="false",
        color=(
            "If(varVhpPlan.PlanType = \"Strategy\" && Len(Coalesce(ThisItem.PackagesKey, \";\")) <= 1, "
            f"{C_INVALID_FG}, {C_MUTED})"
        ))

    OP_MATS = ("Filter(colVhpMaterials, ItemId = ThisItem.ItemId && "
               "OperationNo = ThisItem.OperationNo)")
    OP_DOCS = ("Filter(colVhpAttachments, ItemId = ThisItem.ItemId && "
               "\";\" & ThisItem.OperationNo & \";\" in Coalesce(OperationsKey, \";\"))")
    btnOpMat = button(
        "btnVhpOpMaterials", f'"Materials (" & Text(CountRows({OP_MATS})) & ")"',
        "Set(varVhpMatOpNo, ThisItem.OperationNo)", width=w["MATERIALS"], height=32,
        accessible='"Materials for operation " & ThisItem.OperationNo')
    btnOpDocs = button(
        "btnVhpOpDocs", f'"Docs (" & Text(CountRows({OP_DOCS})) & ")"',
        "Set(varVhpAttOpNo, ThisItem.OperationNo)", width=w["DOCS"], height=32,
        accessible='"Documents for operation " & ThisItem.OperationNo')
    for b_ in (btnOpMat, btnOpDocs):
        b_.props["Size"] = "12"
    mark_done(btnOpMat, f"CountRows({OP_MATS}) > 0")

    opRow = group("conVhpOpRow",
                  pin_widths([txtOpNo, txtOpShort, numOpWork, numOpPersons, numOpDur, txtOpMwc,
                              drpOpCtrl, txtOpVendor, numOpCost, txtOpMatGrp,
                              btnOpLongText, txtOpPackages, btnOpMat, btnOpDocs, btnOpDel]),
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
            "AccessibleLabel": "\"Tasklist operations for active item\"",
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

    opsEmpty = text_ctrl("txtVhpOpsEmpty", "\"No operation lines yet...\"", size=13, color=C_MUTED,
                         height=24, wrap="false", visible=f"!{has_ops}")

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
    opsEmptyM = text_ctrl("txtVhpOpsEmptyM", "\"No operation lines yet...\"", size=13, color=C_MUTED,
                          height=24, wrap="false", visible=f"!{has_ops} && {below('Tablet')}")
    # Sammenklappet (issue #103): fanerne, ruderne og hjaelpepanelet er
    # skjult - kun overskriften og linjen staar tilbage.
    OPEN_EDIT = f"{OPS_OPEN}"
    opsPane = group("conVhpOpsPane", [toolbar, tasklistMeta, opsHint, opsTableWrap, _ops_list_mobile(), opsEmptyM],
                    direction="Vertical", gap=8, width="Parent.Width",
                    visible=f"{OPEN_EDIT} && {OPS_PANE_ON}")
    pkgPane = build_strategy_body()
    pkgPane.vis = f"{OPEN_EDIT} && {PKG_PANE_ON}"
    tabBar = _tab_bar_if_strategy()
    tabBar.vis = f"{OPEN_EDIT} && {tabBar.vis}"
    helpPanel.vis = f"({OPEN_EDIT}) && IfError(varVhpShowHints, false)"

    # Fanebjaelken staar oeverst, lige under sektionshovedet: foerst vaelger
    # man fanen, saa ser man dens indhold. Den laa foer under baade
    # tasklist-vaelgeren og knapraekken, og saa stod selve skiftet nederst i
    # den halvdel af kortet, der ikke aendrede sig.
    return card("conVhpOpsCard",
                [header, helpPanel, tabBar,
                 opsPane, pkgPane, opsFooter])
