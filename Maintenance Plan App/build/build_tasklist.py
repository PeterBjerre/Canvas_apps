# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_INVALID_FG,
                        C_DIVIDER, C_TRANSPARENT, C_INPUT_BG, FONT, SHELL_W)
from build_helpers import (flow_row, text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, two_col_row, badge, card, pin_widths)
from build_plan_header import section_header, help_panel
import build_help as bh
from build_strategy import build_strategy_body, IS_STRATEGY
import sp_config as cfg
from design_tokens import ref_hex
from layout_tokens import fits, TWO_COL_MIN

# HTML kender ikke RGBA(). ref_hex giver den SAMME token som hex.
MUT_HEX = ref_hex("text-muted")
PRI_HEX = ref_hex("text-primary")
import build_attflows

# Flowkontrakten staar i tools/attflows.py; kun rudens egne navne
# og dens refresh_fx() staar i build_attflows.py.
att = build_attflows.PANE

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
        f"column-gap:{OPS_GAP}px;align-items:center;height:23px;line-height:23px;overflow:hidden;"
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
            "overflow:hidden;color:\" & " + MUT_HEX + " & \";font-family:Segoe UI;font-size:11px;"
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
                       onchange="Patch(colVhpMaterials, ThisItem, { MaterialNo: Self.Text })", label="\"Materialenummer\"")
    # Kommer fra materialeopslaget, ikke fra brugeren.
    txtDesc = text_ctrl("txtVhpMatDesc",
                        'If(IsBlank(ThisItem.Description), "-", ThisItem.Description)',
                        size=12, color=C_MUTED, height=30, width=w["DESCRIPTION"], wrap="false")
    numQty = number_input("numVhpMatQty", "ThisItem.Quantity", width=w["QTY"], height=30, label="\"Number\"")
    numQty.props["OnChange"] = "Patch(colVhpMaterials, ThisItem, { Quantity: Self.Value })"
    txtUnit = text_ctrl("txtVhpMatUnit",
                        'If(IsBlank(ThisItem.Unit), "-", ThisItem.Unit)',
                        size=12, color=C_MUTED, height=30, width=w["UNIT"], wrap="false")
    drpOp = dropdown(
        "drpVhpMatOp",
        "Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo))",
        "LookUp(Filter(colVhpOperations, ItemId = varVhpActiveItemId), OperationNo = ThisItem.OperationNo)",
        item_display="ThisItem.OperationNo", value_field="OperationNo",
        width=w["OPERATION"], height=30, label="\"Operation\"")
    drpOp.props["OnChange"] = ("Patch(colVhpMaterials, ThisItem, "
                               "{ OperationNo: Self.Selected.OperationNo })")

    row = group("conVhpMatRow", pin_widths([chkSel, txtNo, txtDesc, numQty, txtUnit, drpOp]),
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

    # align_items="Start": i en LODRET container tvinger Stretch boernene
    # ned i containerens bredde. Tabellen er bredere end kortet MED VILJE,
    # saa Stretch klemte raekkens felter sammen - kun den bredeste kolonne
    # var laesbar - og overflow_x udloestes aldrig, fordi intet overfloed.
    # Start lader tabellen beholde sin bredde, saa den scroller som taenkt.
    table = group("conVhpMatTableWrap", [header, divider, gallery, empty],
                  direction="Vertical", gap=4, overflow_x="Scroll", width="Parent.Width",
                  align_items="Start")

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
           "&& FileName = ThisItem.FileName).OperationsKey, \";\")")
    return Ctrl("chkVhpAttOp", "ModernCheckbox", props={
        "AccessibleLabel": '"Attach to operation " & ThisItem.OperationNo',
        "AlignInContainer": "AlignInContainer.Center",
        "Default": f'";" & ThisItem.OperationNo & ";" in {cur}',
        "Height": "22",
        "Label": "ThisItem.OperationNo",
        "OnCheck": (
            "With(\n"
            "    { op: ThisItem.OperationNo, fn: ThisItem.FileName },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && FileName = fn,\n"
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
            "    { op: ThisItem.OperationNo, fn: ThisItem.FileName },\n"
            "    UpdateIf(\n"
            "        colVhpAttachments,\n"
            "        ItemId = varVhpActiveItemId && FileName = fn,\n"
            "        { OperationsKey: Substitute(Coalesce(OperationsKey, \";\"), \";\" & op & \";\", \";\") }\n"
            "    )\n"
            ")"
        ),
        "Width": str(ATT_CELL_W),
    }, h=22)


def _attachments_pane():
    # Filvalget. Attachments-kontrollen er den eneste, der tager en
    # vilkaarlig fil fra stifinderen - og den virker FRIT paa skaermen.
    # Her stod foer, at den kun lever i en formular bundet til en liste med
    # vedhaeftninger; det er ikke rigtigt. Den gamle app "BioSap Maintenance
    # Plans" bruger den praecis saadan, uden formular, mod de samme flows.
    #
    # Value ER filens indhold. Flowet vil have { name, contentBytes }, og
    # ForAll over kontrollens Attachments giver begge dele.
    #
    # Versionen staar i selve kontrolnavnet - "Attachments@2.3.0" - og ikke
    # som en Variant ved siden af. Det er den form, den gamle app har, og
    # kontroltypens version skal matche paa tvaers af appen; en Variant-linje
    # ved siden af er en anden konstruktion, og den er ikke bevist her.
    picker = Ctrl(att.picker, "Attachments@2.3.0", props={
        "AccessibleLabel": '"Choose documents"',
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "Height": "120",
        "MaxAttachments": "10",
        "MaxAttachmentSize": "50",
        "NoAttachmentsText": '"Drop documents here, or browse"',
        "PaddingBottom": "5", "PaddingLeft": "5",
        "PaddingRight": "5", "PaddingTop": "5",
        "Width": "Parent.Width",
    }, h=120)

    btnUpload = button("btnVhpAttUpload", '"Upload to SharePoint"',
                       att.upload_fx(), primary=True, display_mode=DM_ITEM)
    btnRefresh = button("btnVhpAttRefresh", '"Refresh from SharePoint"',
                        att.refresh_button_fx(), display_mode=DM_ITEM)

    btnRemove = button(
        "btnVhpRemoveAttachment", '"Remove document"',
        att.delete_fx(), danger=True, display_mode=DM_ITEM)
    actions = button_row("conVhpAttActions",
                         [btnUpload, btnRefresh, btnRemove], OPS_CW)

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
        # Den ydre raekkes FILNAVN baeres med ind i hver record - se
        # _att_ops_cell.
        "Items": ("With(\n"
                  "    { fn: ThisItem.FileName },\n"
                  f"    ForAll({ATT_OPS} As O, {{ OperationNo: O.OperationNo, FileName: fn }})\n"
                  ")"),
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        # TabIndex 0 - som de fjorten andre gallerier i repoet.
        #
        # Den manglede HER og kun her, og App checker fangede det ved
        # deploy: "galVhpAttOps.TabIndex: Missing tab stop". En Gallery er
        # en interaktiv kontrol for tastaturet, ogsaa naar Selectable er
        # false - uden et tab stop kan man ikke naa dens indhold uden mus.
        #
        # check_layout regel 18 haandhaever det nu, saa det ikke skal
        # opdages af en deploy-runde igen.
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(ATT_CELL_W),
        "Width": "Parent.Width - 540",
        "WrapCount": "1",
    }, children=[_att_ops_cell()], h=26)

    row = group("conVhpAttRow", pin_widths([chkSel, txtName, txtScope, opsGal]),
                direction="Horizontal", gap=10, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth")

    gal_h = f"Max(CountRows({ATT_ACTIVE}), 1) * {ATT_ROW_H + 2}"
    gallery = Ctrl("galVhpAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents for active item"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BORDER,
        "FillPortions": "0",
        "Height": gal_h,
        # Filnavnet er noeglen paa raekken - der ER ingen LineId paa
        # dokumenterne. Her stod "Sort(..., LineId)", og den kolonne
        # findes ikke i colVhpAttachments: Items gav en fejl, galleriet
        # stod tomt, og fordi raekkerne var der, skjulte den tomme
        # besked sig ogsaa. Derfor saa en uploadet fil ud som ingenting.
        "Items": f"Sort({ATT_ACTIVE}, FileName)",
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

    empty = text_ctrl("txtVhpAttEmpty", att.empty_text_fx(),
                      size=13, color=C_MUTED, height=36, wrap="true",
                      visible=f"IfError(!IsBlank(varVhpActiveItemId) && CountRows({ATT_ACTIVE}) = 0, false)")

    note = text_ctrl("txtVhpAttNote",
                     '"Leave every operation unticked to attach the document to the whole item."',
                     size=12, color=C_MUTED, height=18, wrap="true")

    return group("conVhpAttPane", [picker, actions, note, gallery, empty],
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
    # Valget ER handlingen. Der laa foer en "Apply tasklist"-knap ved siden
    # af, som skrev det valgte paa itemet - et ekstra klik for at bekraefte
    # noget, brugeren lige havde besluttet.
    #
    # Betingelsen er ikke pynt. Skift af item koerer Reset(drpVhpItemTasklist)
    # (build_items.py), og en Reset kan udloese OnChange. Uden
    # sammenligningen ville det skrive den FORRIGE liste paa det NYE item.
    # Efter en Reset er Selected lig med itemets egen vaerdi, saa
    # betingelsen er falsk og OnChange en ren nulhandling.
    drpTasklist.props["OnChange"] = (
        "If(\n"
        "    !IsBlank(varVhpActiveItemId) &&\n"
        "        Self.Selected.Key <> LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey,\n"
        "    UpdateIf(\n"
        "        colVhpItems, ItemId = varVhpActiveItemId,\n"
        "        { TasklistKey: Self.Selected.Key, TasklistName: Self.Selected.Name }\n"
        "    );\n"
        "    Set(varVhpRuntimeInfo, \"Tasklist \" & Self.Selected.Key & \" selected for this item.\")\n"
        ")")
    tasklistCell = field_cell("conVhpCellTasklist", "Tasklist For Active Item", drpTasklist, required=True,
                              width=fits(OPS_CW, TWO_COL_MIN, OPS_CW, "360"), container_w=OPS_CW,
                              fill_portions_formula="0")

    btnAddLines = button(
        "btnVhpAddTasklistLines", "\"Add lines from tasklist\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    If(\n"
            "        IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).TasklistKey),\n"
            "        Set(varVhpRuntimeInfo, \"Select a tasklist first.\"),\n"
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
            "            Persons: 1,\n"
            "            DurationHours: 1,\n"
            "            MainWorkCenter: \"\",\n"
            "            ControlKey: \"\",\n"
            "            Vendor: \"\",\n"
            "            Cost: 0,\n"
            "            Currency: \"\",\n"
            "            CostElement: 0,\n"
            "            MaterialGroup: \"\",\n"
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
    actionRow = button_row("conVhpOpsActionRow", [btnAddLines, btnAddOp, btnRemoveOp], OPS_CW)
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
                            onchange="Patch(colVhpOperations, ThisItem, { OperationShortText: Self.Text })", label="\"Operationstekst\"")
    # Work og No. skriver BEGGE varigheden, fordi den er regnet af dem
    # begge. Gjorde kun den ene det, ville et skift i den anden efterlade en
    # varighed, der ikke passer til linjen - og det er varigheden, der
    # gemmes i TaskListMain.Duration og sendes videre til SAP.
    numOpWork = number_input("numVhpOpWork", "ThisItem.WorkHours", width=w["WORK (H)"], height=32, label="\"Arbejdstimer\"")
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
                            display_mode="DisplayMode.View", label="\"Varighed\"")
    # Arbejdscenteret kommer fra standardarbejdsplanen og bestemmer baade
    # kontrolnoeglen og indkoebsfelterne. Kan man rette det i hoejre hus,
    # skifter de andre felters regler under haanden paa en linje, SAP i
    # forvejen har bestemt. Det laeses nu - og ser graat ud som resten af
    # det, man ikke kan redigere.
    txtOpMwc = text_input("txtVhpOpMwc", "ThisItem.MainWorkCenter", width=w["MAIN WORK CENTER"],
                          height=32, display_mode="DisplayMode.View", label="\"Plant\"")
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
    drpOpCtrl = dropdown(
        "drpVhpOpCtrl", ctrl_items,
        'LookUp(' + ctrl_items + ', Value = ThisItem.ControlKey)',
        width=w["CTRL"], height=32, display_mode=DM_CTRL, label="\"Styringsnoegle\"")
    drpOpCtrl.props["OnChange"] = ("Patch(colVhpOperations, ThisItem, "
                                   "{ ControlKey: Self.Selected.Value })")

    txtOpVendor = text_input("txtVhpOpVendor", "ThisItem.Vendor", width=w["VENDOR"], height=32,
                             display_mode=DM_PURCHASE,
                             onchange="Patch(colVhpOperations, ThisItem, { Vendor: Self.Text })", label="\"Supplier\"")
    numOpCost = number_input("numVhpOpCost", "ThisItem.Cost", width=w["COST"], height=32,
                             display_mode=DM_PURCHASE, label="\"Price\"")
    numOpCost.props["OnChange"] = "Patch(colVhpOperations, ThisItem, { Cost: Self.Value })"
    txtOpMatGrp = text_input("txtVhpOpMatGrp", "ThisItem.MaterialGroup", width=w["MAT.GRP"],
                             height=32, display_mode=DM_PURCHASE,
                             onchange="Patch(colVhpOperations, ThisItem, { MaterialGroup: Self.Text })", label="\"Materialegruppe\"")
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
            "Set(varVhpLongTextItemId, ThisItem.ItemId);\n"
            "Set(varVhpLongTextOpNo, ThisItem.OperationNo);\n"
            "Set(varVhpLongTextDraft, Coalesce(ThisItem.LongText, \"\"));\n"
            "Reset(txtVhpLongTextBox);\n"
            "Set(varVhpLongTextOpen, true)"
        ),
        width=w["LONG TEXT"], height=32,
        accessible='"Edit long text for operation " & ThisItem.OperationNo')

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

    opRow = group("conVhpOpRow",
                  pin_widths([chkSel, txtOpNo, txtOpShort, numOpWork, numOpPersons, numOpDur, txtOpMwc,
                              drpOpCtrl, txtOpVendor, numOpCost, txtOpMatGrp,
                              btnOpLongText, txtOpPackages]), direction="Horizontal", gap=OPS_GAP,
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

    opsTotalsDivider = group("conVhpOpsTotalsDivider", [], height=1, fill=C_DIVIDER,
                             direction="Horizontal", width=str(OPS_TABLE_W),
                             visible=TOTALS_ON)
    opsTotals = Ctrl("conVhpOpsTotalsHtml", "HtmlViewer", props={
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
                         align_items="Start")

    # Operationstabellen er fanen Operations - sammen med tasklist-vaelgeren
    # og de fire operationsknapper. De laa foer i kortet uden for ruderne, og
    # saa blev "Add operation" staaende paa materialefanen, hvor den ikke
    # hoerer hjemme. Hver fane ejer nu sine egne knapper, praecis som
    # materialeruden allerede gjorde.
    opsPane = group("conVhpOpsPane", [toolbar, tasklistMeta, opsHint, opsTableWrap],
                    direction="Vertical", gap=8, width="Parent.Width",
                    visible=OPS_PANE_ON)
    pkgPane = build_strategy_body()
    pkgPane.vis = PKG_PANE_ON
    matPane = _materials_pane()
    matPane.vis = _tab_on("mat")
    attPane = _attachments_pane()
    attPane.vis = _tab_on("att")

    # Fanebjaelken staar oeverst, lige under sektionshovedet: foerst vaelger
    # man fanen, saa ser man dens indhold. Den laa foer under baade
    # tasklist-vaelgeren og knapraekken, og saa stod selve skiftet nederst i
    # den halvdel af kortet, der ikke aendrede sig.
    return card("conVhpOpsCard",
                [header, helpPanel, _tab_bar(),
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
            "            \" Strategy \" & varVhpPlan.Strategy & \" with \" &\n"
            "            Text(CountRows(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy))) & \" packages.\",\n"
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
            "            \"Strategy: \" & varVhpPlan.Strategy & Char(10) &\n"
            "            \"Packages: \" & Concat(Sort(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy), PackageNo), ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit & \")\", \", \") & Char(10),\n"
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
            "                        Len(k) <= 1, \"(no package)\",\n"
            "                        Concat(Sort(Filter(colVhpStrategyPackages As P, P.StrategyKey = varVhpPlan.Strategy && \";\" & Text(P.PackageNo) & \";\" in k), PackageNo), ShortCode, \", \")\n"
            "                    )\n"
            "                ),\n"
            "                Char(10)\n"
            "            ) & Char(10) & Char(10),\n"
            "            \"\"\n"
            "        ) &\n"
            "        \"Sent from the VH-plan app on \" & Text(Now(), \"dd-mm-yyyy hh:mm\")\n"
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
