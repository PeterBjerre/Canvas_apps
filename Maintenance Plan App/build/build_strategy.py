# -*- coding: utf-8 -*-
"""
Strategiplan-delen: pakkematricen.

DOMAENET
--------
I SAP ligger de tre ting i tre forskellige objekter:

  Vedligeholdsstrategi (IP11)  ejer PAKKERNE            - masterdata
  Arbejdsplan (IA01)           ejer ALLOKERINGEN op->pakke
  Vedligeholdsplan (IP42)      peger bare paa begge dele

Brugeren opfinder altsaa ikke pakker - de kommer fra strategien. Og
allokeringen hoerer til arbejdsplanens OPERATIONER, ikke til planen. Derfor
ligger matricen paa colVhpOperations og ikke paa colVhpItems.

LAGRINGSFORMAT
--------------
Allokeringen gemmes som een streng pr. operation, PackagesKey, paa formen
";1;3;5;". Sentinel-separatoren i begge ender er ikke kosmetik: uden den
ville testen for pakke 1 (";1;") ogsaa matche inde i ";12;". Med den er en
simpel substring-test korrekt, og der skal ikke parses i hver celle.

INVARIANT: PackagesKey er aldrig tom - en operation uden pakker har ";".
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_NEUTRAL_BG, C_DIVIDER, C_VALID_FG, C_INVALID_FG,
                        C_TRANSPARENT, FONT, SHELL_W)
from build_helpers import text_ctrl, group, button, button_row, badge, card
from build_plan_header import section_header, help_panel

IS_STRATEGY = "(varVhpPlan.PlanType = \"Strategy\")"
PKGS = "Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy)"
PKGS_SORTED = f"Sort({PKGS}, PackageNo)"
OPS_ACTIVE = "Filter(colVhpOperations, ItemId = varVhpActiveItemId)"

OPS_CW = f"({SHELL_W} - 36)"

# Matricens maal. Label-kolonnen er fast; pakkekolonnerne kommer fra
# strategien, saa bredden er dynamisk.
LBL_W = 260
CELL_W = 64
ROW_H = 40
GAL_ROW_H = ROW_H + 2
MATRIX_W = f"{LBL_W} + CountRows({PKGS}) * {CELL_W}"

# Indtil pakkerne er hentet fra SAP (IP11) er MD_StrategyPackage tom. Saa
# skal matricen IKKE tegnes som et tomt gitter - den skal sige hvorfor.
# Eet udtryk styrer begge dele, saa de ikke kan vise sig samtidig.
HAS_PKGS = f"CountRows({PKGS}) > 0"
HAS_OPS = f"CountRows({OPS_ACTIVE}) > 0"
CAN_DRAW = f"(!IsBlank(varVhpPlan.Strategy) && {HAS_PKGS} && {HAS_OPS})"

# Hierarki-udfyld maa KUN bruges paa en strategi, hvor pakkerne er indlejrede
# i hinanden - 1-3-6-12, hvor den maanedlige opgave ogsaa skal laves ved
# kvartals- og aarsgennemgangen.
#
# Strategi 128 ("Aar 1, 2, 3, 1, 2, 3") er det modsatte: alle tre pakker har
# cykluslaengde 3 YR med offset 0, 1 og 2, saa de falder ALDRIG sammen. Fylder
# man op efter hierarki der, bliver en treaarig opgave aarlig.
#
# Derfor er knappen bundet til MD_Strategy.Hierarchical. Er den ikke sat til
# "Ja", er knappen slaaet fra. "Ikke afklaret" er altsaa ikke det samme som
# "nej" - det betyder, at ingen har taget stilling, og saa gaettes der ikke.
STRATEGY_IS_HIER = ("(LookUp(colVhpStrategies, Key = varVhpPlan.Strategy).Hierarchical "
                    "= \"Ja\")")


def _pkg_cell_gallery(name, template, items=PKGS_SORTED, template_size=CELL_W, height=ROW_H):
    return Ctrl(
        name, "Gallery", variant="Horizontal",
        props={
            "AccessibleLabel": "\"Vedligeholdelsespakker\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_TRANSPARENT,
            "FillPortions": "0",
            "Height": str(height),
            "Items": items,
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "0",
            "TemplateSize": str(template_size),
            "Width": f"CountRows({PKGS}) * {CELL_W}",
            "WrapCount": "1",
        },
        children=[template], h=height)


def build_strategy_body():
    """Pakkematricen UDEN eget kort og overskrift.

    Laa foer som Step 4, et kort for sig. Den hoerer til arbejdsplanen -
    allokeringen er operation -> pakke - saa den er flyttet ind som en fane
    i Tasklist-sektionen sammen med operationerne, materialerne og
    dokumenterne. Hjaelpepanelet foelger med derind."""
    helpPanel = help_panel("conVhpPkgHelp", "pkg")

    strategyMeta = text_ctrl(
        "txtVhpPkgMeta",
        (
            "If(\n"
            "    IsBlank(varVhpPlan.Strategy), \"Choose a strategy in the plan header first.\",\n"
            "    \"Strategi \" & varVhpPlan.Strategy & \" - \" &\n"
            "    Coalesce(LookUp(colVhpStrategies, Key = varVhpPlan.Strategy).Name, \"\") & \": \" &\n"
            f"    Concat({PKGS_SORTED}, ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit & \")\", \", \") & \".\"\n"
            ")"
        ), size=13, color=C_MUTED, height=20, wrap="true")

    # En knap, der er graa uden forklaring, ligner en fejl. Denne linje siger
    # hvorfor, og hvad der skal goeres ved det.
    hierNote = text_ctrl(
        "txtVhpPkgHierNote",
        (
            "With(\n"
            "    { h: LookUp(colVhpStrategies, Key = varVhpPlan.Strategy).Hierarchical },\n"
            "    If(\n"
            "        h = \"Ja\", \"\",\n"
            "        h = \"Nej\",\n"
            "        \"Hierarchy fill is off: the packages in this strategy are not \" &\n"
            "            \"nested, so they must be ticked one by one.\",\n"
            "        \"Hierarchy fill is off: it is not settled whether this \" &\n"
            "            \"strategy is hierarchical. Set the Hierarchical field in MD_Strategy.\"\n"
            "    )\n"
            ")"
        ), size=12, color=C_MUTED, height=32, wrap="true",
        visible=f"IfError({CAN_DRAW} && !{STRATEGY_IS_HIER}, false)")

    # --- hjaelpehandlinger ---------------------------------------------------
    allPkgKey = f"\";\" & Concat({PKGS_SORTED}, Text(PackageNo) & \";\")"

    btnAll = button(
        "btnVhpPkgAll", "\"Alle pakker\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    UpdateIf(\n"
            "        colVhpOperations, ItemId = varVhpActiveItemId,\n"
            f"        {{ PackagesKey: {allPkgKey} }}\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"All packages ticked on every operation.\")\n"
            ")"
        ), display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")

    # Et 1/3/6/12-moenster fungerer saadan, at en operation der hoerer til den
    # maanedlige pakke naesten altid ogsaa skal udfoeres ved kvartals-,
    # halvaars- og aarsgennemgangen. Brugeren markerer derfor kun den laveste
    # pakke, og denne knap fylder resten ud efter hierarki.
    btnHier = button(
        "btnVhpPkgHierarchy", "\"Hierarki-udfyld\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            f"    ForAll(\n"
            f"        {OPS_ACTIVE} As OP,\n"
            "        With(\n"
            "            {\n"
            "                minH: Min(\n"
            f"                    Filter({PKGS} As P, \";\" & Text(P.PackageNo) & \";\" in Coalesce(OP.PackagesKey, \";\")),\n"
            "                    Hierarchy\n"
            "                )\n"
            "            },\n"
            "            If(\n"
            "                !IsBlank(minH),\n"
            "                UpdateIf(\n"
            "                    colVhpOperations,\n"
            "                    ItemId = OP.ItemId && OperationNo = OP.OperationNo,\n"
            "                    {\n"
            "                        PackagesKey:\n"
            f"                            \";\" & Concat(Sort(Filter({PKGS}, Hierarchy >= minH), PackageNo), Text(PackageNo) & \";\")\n"
            "                    }\n"
            "                )\n"
            "            )\n"
            "        )\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Pakker fyldt op efter hierarki.\")\n"
            ")"
        ), primary=True,
        display_mode=(f"If(\n"
                      f"    IsBlank(varVhpActiveItemId) || !{STRATEGY_IS_HIER},\n"
                      f"    DisplayMode.Disabled,\n"
                      f"    DisplayMode.Edit\n"
                      f")"))

    btnClear = button(
        "btnVhpPkgClear", "\"Ryd pakker\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item first.\"),\n"
            "    UpdateIf(colVhpOperations, ItemId = varVhpActiveItemId, { PackagesKey: \";\" });\n"
            "    Set(varVhpRuntimeInfo, \"Pakkemarkeringer ryddet.\")\n"
            ")"
        ), danger=True,
        display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")

    actionRow = button_row("conVhpPkgActionRow", [btnHier, btnAll, btnClear], OPS_CW)

    # --- matrix-overskrift ---------------------------------------------------
    headLbl = text_ctrl("txtVhpPkgHeadLabel", "\"OPERATION\"", size=11, weight="Semibold", color=C_MUTED,
                        height=ROW_H, width=LBL_W, wrap="false")
    headCellText = text_ctrl(
        "txtVhpPkgHeadCell",
        # Kun pakkekoden - cyklussen staar paa meta-linjen over matricen, og
        # "M12 (12 MON)" ville blive klippet i en kolonne paa 64 px.
        "ThisItem.ShortCode",
        size=12, weight="Semibold", height=ROW_H, width=CELL_W, wrap="false",
        extra={"Align": "Align.Center"})
    headCell = group("conVhpPkgHeadCell", [headCellText], direction="Horizontal", gap=0, height=ROW_H,
                     align_items="Center", justify="Center", width="Parent.TemplateWidth")
    headGal = _pkg_cell_gallery("galVhpPkgHead", headCell)
    matrixHead = group("conVhpPkgHeadRow", [headLbl, headGal], direction="Horizontal", gap=0,
                       height=ROW_H, align_items="Center", width=MATRIX_W)
    divider = group("conVhpPkgDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal",
                    width=MATRIX_W)

    # --- matrix-raekker ------------------------------------------------------
    # Den skjulte labels tekst er den eneste maade at laese den YDRE gallerys
    # raekke inde fra den INDRE gallery: en kontrolreference inde i en
    # skabelon oploeses til den aktuelle raekkes instans.
    rowOpNo = text_ctrl("txtVhpPkgRowOpNo", "ThisItem.OperationNo", size=12, color=C_MUTED, height=ROW_H,
                        width=56, wrap="false")
    rowText = text_ctrl("txtVhpPkgRowText",
                        "If(IsBlank(ThisItem.OperationShortText), \"(uden tekst)\", ThisItem.OperationShortText)",
                        size=13, height=ROW_H, width=LBL_W - 56, wrap="false")
    cur_key = ("Coalesce(LookUp(colVhpOperations, ItemId = varVhpActiveItemId "
               "&& OperationNo = ThisItem.OpNo).PackagesKey, \";\")")

    chkCell = Ctrl(
        "chkVhpPkgCell", "ModernCheckbox",
        props={
            "AccessibleLabel": ("\"Pakke \" & ThisItem.ShortCode & \" on operation \" & ThisItem.OpNo"),
            "AlignInContainer": "AlignInContainer.Center",
            "Default": f"\";\" & Text(ThisItem.PackageNo) & \";\" in {cur_key}",
            "Height": "24",
            "OnCheck": (
                "With(\n"
                "    { pkg: Text(ThisItem.PackageNo), op: ThisItem.OpNo },\n"
                "    UpdateIf(\n"
                "        colVhpOperations,\n"
                "        ItemId = varVhpActiveItemId && OperationNo = op,\n"
                "        {\n"
                "            PackagesKey:\n"
                "                If(\n"
                "                    \";\" & pkg & \";\" in Coalesce(PackagesKey, \";\"),\n"
                "                    Coalesce(PackagesKey, \";\"),\n"
                "                    Coalesce(PackagesKey, \";\") & pkg & \";\"\n"
                "                )\n"
                "        }\n"
                "    )\n"
                ")"
            ),
            "OnUncheck": (
                "With(\n"
                "    { pkg: Text(ThisItem.PackageNo), op: ThisItem.OpNo },\n"
                "    UpdateIf(\n"
                "        colVhpOperations,\n"
                "        ItemId = varVhpActiveItemId && OperationNo = op,\n"
                "        { PackagesKey: Substitute(Coalesce(PackagesKey, \";\"), \";\" & pkg & \";\", \";\") }\n"
                "    )\n"
                ")"
            ),
            "Width": "30",
        }, h=24)
    cellWrap = group("conVhpPkgCell", [chkCell], direction="Horizontal", gap=0, height=ROW_H,
                     align_items="Center", justify="Center", width="Parent.TemplateWidth")
    cell_items = (
        "With(\n"
        "    { op: ThisItem.OperationNo },\n"
        f"    ForAll(\n"
        f"        {PKGS_SORTED} As P,\n"
        "        { PackageNo: P.PackageNo, ShortCode: P.ShortCode, OpNo: op }\n"
        "    )\n"
        ")"
    )
    cellsGal = _pkg_cell_gallery("galVhpPkgCells", cellWrap, items=cell_items)

    matrixRow = group("conVhpPkgRow", [rowOpNo, rowText, cellsGal], direction="Horizontal", gap=0,
                      height="Parent.TemplateHeight - 2", align_items="Center",
                      width="Parent.TemplateWidth")

    rowsGal = Ctrl(
        "galVhpPkgRows", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Pakkematrix\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_TRANSPARENT,
            "FillPortions": "0",
            "Height": f"Max(CountRows({OPS_ACTIVE}), 1) * {GAL_ROW_H}",
            "Items": f"Sort({OPS_ACTIVE}, Value(OperationNo))",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": str(ROW_H),
            "Width": MATRIX_W,
            "WrapCount": "1",
        },
        children=[matrixRow], h=f"Max(CountRows({OPS_ACTIVE}), 1) * {GAL_ROW_H}")

    # Matricen har fast bredde (label + een kolonne pr. pakke). Paa smalle
    # skaerme scroller den vandret i stedet for at klippe kolonner af.
    matrixWrap = group("conVhpPkgMatrixWrap", [matrixHead, divider, rowsGal], direction="Vertical", gap=4,
                       overflow_x="Scroll", width="Parent.Width",
                       align_items="Start",
                       visible=f"IfError({CAN_DRAW}, false)")

    # Tre grunde til at matricen ikke kan tegnes, i den raekkefoelge brugeren
    # moeder dem. Den midterste er den, der gaelder lige nu: strategierne er
    # hentet fra SAP, men pakkerne er ikke.
    emptyState = text_ctrl(
        "txtVhpPkgEmpty",
        (
            "If(\n"
            "    IsBlank(varVhpPlan.Strategy),\n"
            "    \"Choose a strategy in the plan header.\",\n"
            "\n"
            f"    {HAS_PKGS} = false,\n"
            "    \"Strategi \" & varVhpPlan.Strategy & \" har ingen pakker i MD_StrategyPackage endnu, \" &\n"
            "        \"so there is nothing to allocate. The packages come from SAP (IP11). \" &\n"
            "        \"The plan can still be saved and submitted without a package allocation.\",\n"
            "\n"
            "    \"No operations on the active item yet. \" &\n"
            "        \"Add operations under Tasklist and Operations.\"\n"
            ")"
        ), size=13, color=C_MUTED, height=40, wrap="true",
        visible=f"IfError(!{CAN_DRAW}, true)")

    # S4/S5: en operation uden pakke ville aldrig blive udfoert, og en pakke
    # uden operationer kalder en tom ordre.
    warn = text_ctrl(
        "txtVhpPkgWarnings",
        (
            "With(\n"
            "    {\n"
            f"        noPkg: Filter({OPS_ACTIVE}, Len(Coalesce(PackagesKey, \";\")) <= 1),\n"
            f"        emptyPkg: Filter({PKGS} As P,\n"
            f"            CountRows(Filter({OPS_ACTIVE}, \";\" & Text(P.PackageNo) & \";\" in Coalesce(PackagesKey, \";\"))) = 0)\n"
            "    },\n"
            "    If(\n"
            "        CountRows(noPkg) = 0 && CountRows(emptyPkg) = 0,\n"
            "        \"Every operation has at least one package, and every package has operations.\",\n"
            "        If(CountRows(noPkg) > 0,\n"
            "            \"S4: \" & Concat(noPkg, OperationNo, \", \") & \" has no package and would never be carried out. \",\n"
            "            \"\"\n"
            "        ) &\n"
            "        If(CountRows(emptyPkg) > 0,\n"
            "            \"S5: pakke \" & Concat(emptyPkg, ShortCode, \", \") & \" indeholder ingen operationer.\",\n"
            "            \"\"\n"
            "        )\n"
            "    )\n"
            ")"
        ),
        size=12, height=32, wrap="true",
        color=(
            "With(\n"
            "    {\n"
            f"        bad: CountRows(Filter({OPS_ACTIVE}, Len(Coalesce(PackagesKey, \";\")) <= 1))\n"
            "    },\n"
            f"    If(bad > 0, {C_INVALID_FG}, {C_VALID_FG})\n"
            ")"
        ),
        visible=f"IfError({CAN_DRAW}, false)")

    actionRow.vis = f"IfError({CAN_DRAW}, false)"

    return group("conVhpPkgPane",
                 [helpPanel, strategyMeta, actionRow, hierNote, matrixWrap, emptyState, warn],
                 direction="Vertical", gap=12, width="Parent.Width")
