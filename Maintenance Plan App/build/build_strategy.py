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
from gen_screen import (Ctrl, C_MUTED, C_DIVIDER, C_VALID_FG, C_INVALID_FG,
                        C_TRANSPARENT, SHELL_W)
from build_helpers import text_ctrl, group, button, button_row, row_hit, text_input, pin_widths
from design_tokens import ref_hex
from build_plan_header import help_panel

IS_STRATEGY = "(varVhpPlan.PlanType = \"Strategy\")"
PKGS = "Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy)"
PKGS_SORTED = f"Sort({PKGS}, PackageNo)"
OPS_ACTIVE = "Filter(colVhpOperations, ItemId = varVhpActiveItemId)"

OPS_CW = f"({SHELL_W} - 36)"

# Matricens maal. Label-kolonnen er fast; pakkekolonnerne kommer fra
# strategien, saa bredden er dynamisk.
# Samme maal som operationstabellen (build_tasklist.OPS_COLS): OP NO. 60,
# OPERATION SHORT TEXT 200, felter paa 32 px i raekker paa 44 px.
OPNO_W = 60
TEXT_W = 200
LBL_GAP = 8
LBL_W = OPNO_W + LBL_GAP + TEXT_W + LBL_GAP
CELL_W = 64
ROW_H = 44
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
            "AccessibleLabel": "\"Maintenance packages\"",
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


# PAKKE-PILLERNE (designforslaget "BIO SAP UX-review", VH-mockup)
# ------------------------------------------------------------------
# Operationslinjen viser strategiens pakker som piller - 1M 3M 6M 12M - og
# et klik slaar pakken til eller fra paa netop den operation. Valgt: lys
# violet flade, violet kant og tekst. Ikke valgt: kortets flade, graa kant og
# daempet tekst. Har operationen INGEN pakke, er kanterne roede - det samme
# signal som "(none)" i roedt foer.
#
# Pillen er et Image med en SVG, som hjaelpe- og temakontakten
# (build_helpers.help_toggle): foerste udgave var en ModernButton med
# Appearance Primary og BasePaletteColor = den lyse violet, men Fluent
# tegnede fladen naesten sort, og knappen blev klippet i toppen af
# galleriets scrollbar. En container kan ikke staa i et galleri (den foldes
# ud til et Rectangle uden runde hjoerner), saa SVG'en er den eneste maade
# at tegne PRAECIS pillen i appens egne farver.
#
# Allokeringen skrives i PackagesKey paa samme maade som matricen
# (chkVhpPkgCell) - matricen og pillerne er to visninger af samme streng.
PILL_H = 26
PILL_W = 40
# Har strategien flere end fire pakker, bliver pillerne smallere, saa op
# til syv kan staa i cellen. Koderne er hoejst to tegn ("12", "6M").
PILL_W_COMPACT = 26
PILL_PAD = 2
PILL_FIT = 4
PILL_FIT_COMPACT = 7
PILLS_W = PILL_FIT_COMPACT * (PILL_W_COMPACT + 2 * PILL_PAD)
_IS_COMPACT = f"CountRows({PKGS}) > {PILL_FIT}"


def _pill_svg(w, h=PILL_H):
    """SVG-strengen (Power Fx) for een pille. Laeser ThisItem.Sel,
    ThisItem.NoPkg og ThisItem.ShortCode i pille-galleriet."""
    fill = f'" & If(ThisItem.Sel, {ref_hex("state-violet-bg")}, {ref_hex("bg-card")}) & "'
    edge = (f'" & If(ThisItem.Sel, {ref_hex("state-violet-fg")}, ThisItem.NoPkg, '
            f'{ref_hex("border-error")}, {ref_hex("border-input")}) & "')
    ink = f'" & If(ThisItem.Sel, {ref_hex("state-violet-fg")}, {ref_hex("text-muted")}) & "'
    r = (h - 1) / 2
    return ('"' +
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' "
            f"viewBox='0 0 {w} {h}'>"
            f"<rect x='0.5' y='0.5' width='{w - 1}' height='{h - 1}' rx='{r}' "
            f"fill='{fill}' stroke='{edge}'/>"
            f"<text x='{w / 2}' y='{h / 2 + 4}' text-anchor='middle' "
            f"font-family='Segoe UI, sans-serif' font-size='12' font-weight='600' "
            f"fill='{ink}'>\" & ThisItem.ShortCode & \"</text>"
            "</svg>" + '"')


def _pill_parts(prefix, pill_w, img, tpl_h, x="0"):
    """Pillen (Image) og kliklaget oven paa den for een pakke paa een
    operation. Laeser ThisItem.PackageNo, OpNo, Sel og ShortCode i det
    galleri, pillen staar i - operationsraekken eller pakkefanen."""
    sel = "ThisItem.Sel"
    on_select = (
        "If(!varVhpViewOnly,\n"
        "    With(\n"
        "        { pkg: Text(ThisItem.PackageNo), op: ThisItem.OpNo, was: ThisItem.Sel },\n"
        "        UpdateIf(\n"
        "            colVhpOperations,\n"
        "            ItemId = varVhpActiveItemId && OperationNo = op,\n"
        "            {\n"
        "                PackagesKey:\n"
        "                    If(\n"
        "                        was,\n"
        "                        Substitute(Coalesce(PackagesKey, \";\"), \";\" & pkg & \";\", \";\"),\n"
        "                        Coalesce(PackagesKey, \";\") & pkg & \";\"\n"
        "                    )\n"
        "            }\n"
        "        )\n"
        "    )\n"
        ")"
    )
    y = str((tpl_h - PILL_H) // 2)
    # Billedet tegner kun pillen; klikket er et gennemsigtigt lag oven paa
    # (build_helpers.row_hit) med pillens runde hjoerner - samme moenster
    # som VH-planens item-kort. Det giver tone ved hover og tryk og kant
    # ved fokus, og laget er ikke en ikonknap (regel 40 kraever 32-44 px).
    pill = Ctrl(
        f"img{prefix}Pill", "Image",
        props={
            # I View er kliklaget vaek, saa billedet siger selv, om pakken
            # er valgt (skaermlaeseren).
            "AccessibleLabel": ('ThisItem.ShortCode & If(varVhpViewOnly, '
                                'If(ThisItem.Sel, ", selected", ", not selected"), "")'),
            "BorderStyle": "BorderStyle.None",
            "BorderThickness": "0",
            "Fill": C_TRANSPARENT,
            "Height": str(PILL_H),
            "Image": img,
            "ImagePosition": "ImagePosition.Fit",
            "TabIndex": "0",
            "Width": pill_w,
            "X": x,
            "Y": y,
        }, h=PILL_H)
    hit = row_hit(
        f"btn{prefix}PillHit", on_select,
        (f'"Package " & ThisItem.ShortCode & " on operation " & ThisItem.OpNo & '
         f'If({sel}, ", selected", ", not selected")'),
        pill_w, PILL_H, radius=PILL_H // 2)
    hit.props["X"] = x
    hit.props["Y"] = y
    # View: pillerne viser valget, men et klik aendrer intet (issue #390).
    #
    # Issue #408: det var ikke nok. Med DisplayMode.View stod kliklaget
    # stadig oven paa pillen - en klassisk knap tegner sin tryk-tilstand og
    # sit fokus, og et klik paa en valgt pakke lod noget dukke op ved
    # siden af den. Nu er laget slet ikke der i View: pillen (billedet)
    # tegnes som foer i sine gemte farver, men der er intet at klikke,
    # holde over, tabbe til eller trykke paa - og intet tooltip. OnSelect
    # er stadig vagtet af varVhpViewOnly, hvis laget skulle blive synligt.
    hit.props["DisplayMode"] = "If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)"
    hit.props["Visible"] = "!varVhpViewOnly"
    hit.props["Tooltip"] = ('ThisItem.ShortCode & " - " & Text(ThisItem.CycleLength) & " " & '
                            'ThisItem.CycleUnit')
    return pill, hit


def pkg_pills(prefix, op_no, key, width=PILLS_W):
    """Pillerne for een operation. op_no og key er Power Fx-udtryk for
    operationens nummer og PackagesKey, set fra der hvor galleriet staar
    (raekken i operationstabellen eller popup'en)."""
    pill_w = f"If({_IS_COMPACT}, {PILL_W_COMPACT}, {PILL_W})"
    img = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({_IS_COMPACT},\n'
           f'    {_pill_svg(PILL_W_COMPACT)},\n    {_pill_svg(PILL_W)}\n))')
    tpl_h = PILL_H + 2   # galleriets hoejde minus TemplatePadding
    pill, hit = _pill_parts(prefix, "Parent.TemplateWidth", img, tpl_h)
    items = (
        "With(\n"
        f"    {{ op: {op_no}, k: Coalesce({key}, \";\") }},\n"
        "    ForAll(\n"
        f"        {PKGS_SORTED} As P,\n"
        "        {\n"
        "            PackageNo: P.PackageNo, ShortCode: P.ShortCode,\n"
        "            CycleLength: P.CycleLength, CycleUnit: P.CycleUnit, OpNo: op,\n"
        "            Sel: \";\" & Text(P.PackageNo) & \";\" in k,\n"
        "            NoPkg: Len(k) <= 1\n"
        "        }\n"
        "    )\n"
        ")"
    )
    gal_h = tpl_h + 2 * PILL_PAD
    return Ctrl(
        f"gal{prefix}Pills", "Gallery", variant="Horizontal",
        props={
            "AccessibleLabel": f'"Maintenance packages for operation " & {op_no}',
            "BorderStyle": "BorderStyle.None",
            "Fill": C_TRANSPARENT,
            "FillPortions": "0",
            "Height": str(gal_h),
            "Items": items,
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            # Ingen scrollbar: den lagde sig over pillerne og klippede dem.
            # Strategier med flere end syv pakker kan scrolles med hjul
            # eller finger; matricen under Packages viser altid dem alle.
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": str(PILL_PAD),
            "TemplateSize": pill_w,
            "Width": str(width),
            "WrapCount": "1",
        },
        children=[pill, hit], h=gal_h)


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
            "    \"Strategy \" & varVhpPlan.Strategy & \" - \" &\n"
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
        "btnVhpPkgAll", "\"All packages\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    UpdateIf(\n"
            "        colVhpOperations, ItemId = varVhpActiveItemId,\n"
            f"        {{ PackagesKey: {allPkgKey} }}\n"
            "    );\n"
            "    Notify(\"All packages ticked on every operation.\", NotificationType.Success)\n"
            ")"
        ), display_mode="If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")

    # Et 1/3/6/12-moenster fungerer saadan, at en operation der hoerer til den
    # maanedlige pakke naesten altid ogsaa skal udfoeres ved kvartals-,
    # halvaars- og aarsgennemgangen. Brugeren markerer derfor kun den laveste
    # pakke, og denne knap fylder resten ud efter hierarki.
    btnHier = button(
        "btnVhpPkgHierarchy", "\"Fill by hierarchy\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            # EEN skrivning, ikke een pr. operation.
            #
            # Her stod ForAll(operationer, UpdateIf(colVhpOperations, ...)).
            # App checker: ForAllWithMutation - hver skrivning faar alt, der
            # afhaenger af samlingen, til at genberegne, saa en plan med 40
            # operationer gav 40 runder.
            #
            # ForAll returnerer en TABEL, saa de to tabeller - raekkerne og
            # aendringerne - regnes faerdige foerst og skrives i eet Patch.
            # Formen er dokumenteret: Patch(kilde, raekker, aendringer).
            #
            # Raekker uden pakker faar deres egen noegle tilbage. Foer blev
            # de sprunget over med et If; nu skrives den samme vaerdi, og
            # resultatet er det samme.
            f"    With(\n"
            f"        {{ src: {OPS_ACTIVE} }},\n"
            "        Patch(\n"
            "            colVhpOperations,\n"
            "            src,\n"
            "            ForAll(\n"
            "                src As OP,\n"
            "                {\n"
            "                    PackagesKey:\n"
            "                        With(\n"
            "                            {\n"
            "                                minH: Min(\n"
            f"                                    Filter({PKGS} As P, \";\" & Text(P.PackageNo) & \";\" in Coalesce(OP.PackagesKey, \";\")),\n"
            "                                    Hierarchy\n"
            "                                )\n"
            "                            },\n"
            "                            If(\n"
            "                                IsBlank(minH),\n"
            "                                Coalesce(OP.PackagesKey, \";\"),\n"
            f"                                \";\" & Concat(Sort(Filter({PKGS}, Hierarchy >= minH), PackageNo), Text(PackageNo) & \";\")\n"
            "                            )\n"
            "                        )\n"
            "                }\n"
            "            )\n"
            "        )\n"
            "    );\n"
            "    Notify(\"Packages filled in by hierarchy.\", NotificationType.Success)\n"
            ")"
        ), primary=True,
        display_mode=(f"If(\n"
                      f"    varVhpViewOnly || IsBlank(varVhpActiveItemId) || !{STRATEGY_IS_HIER},\n"
                      f"    DisplayMode.Disabled,\n"
                      f"    DisplayMode.Edit\n"
                      f")"))

    btnClear = button(
        "btnVhpPkgClear", "\"Clear packages\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
            "    UpdateIf(colVhpOperations, ItemId = varVhpActiveItemId, { PackagesKey: \";\" });\n"
            "    Notify(\"Package selections cleared.\", NotificationType.Success)\n"
            ")"
        ), danger=True,
        display_mode="If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")

    actionRow = button_row("conVhpPkgActionRow", [btnHier, btnAll, btnClear], OPS_CW)

    # --- matrix-overskrift ---------------------------------------------------
    # SAMME DESIGN SOM OPERATIONSTABELLEN (Peter 2026-10-19): overskriften er
    # en HtmlViewer med daempede versaler paa en afrundet flade
    # (build_tasklist._ops_header_html), og hver celle er en pakke-pille som
    # paa operationslinjen - ikke et flueben. Pakkernes koder staar
    # centreret over deres kolonne; kolonnerne kommer fra strategien, saa
    # den del af HTML'en bygges i appen med Concat.
    mut = ref_hex("text-muted")
    bg = ref_hex("bg-muted")
    head_html = (
        "\"<style>html,body{margin:0;padding:0;overflow:hidden}"
        "span{flex:none;box-sizing:border-box;overflow:hidden;text-overflow:ellipsis}</style>"
        "<div style='display:flex;align-items:center;height:30px;line-height:30px;overflow:hidden;"
        "border-radius:8px;background:\" & " + bg + " & \";"
        "color:\" & " + mut + " & \";font-family:Segoe UI;font-size:11px;font-weight:600;white-space:nowrap;'>"
        f"<span style='width:{OPNO_W + LBL_GAP}px;padding-left:8px'>OP NO.</span>"
        f"<span style='width:{TEXT_W + LBL_GAP}px;padding-left:8px'>OPERATION SHORT TEXT</span>\" &\n"
        f"Concat({PKGS_SORTED}, \"<span style='width:{CELL_W}px;text-align:center'>\" & ShortCode & \"</span>\") &\n"
        "\"</div>\""
    )
    matrixHead = Ctrl("htmVhpPkgHeader", "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": "34", "HtmlText": head_html,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": MATRIX_W,
    }, h=34)
    divider = group("conVhpPkgDivider", [], height=1, fill=C_DIVIDER, direction="Horizontal",
                    width=MATRIX_W)

    # --- matrix-raekker ------------------------------------------------------
    # Nummer og tekst er de samme felter som paa operationslinjen, men laast:
    # her vaelges kun pakker. De rettes under Operations.
    rowOpNo = text_input("inpVhpPkgRowOpNo", "ThisItem.OperationNo", width=OPNO_W, height=32,
                         display_mode="DisplayMode.View",
                         label='"Operation number " & ThisItem.OperationNo')
    rowText = text_input("inpVhpPkgRowText",
                         "If(IsBlank(ThisItem.OperationShortText), \"(no text)\", ThisItem.OperationShortText)",
                         width=TEXT_W, height=32, display_mode="DisplayMode.View",
                         label='"Operation text"')
    cur_key = ("Coalesce(LookUp(colVhpOperations, ItemId = varVhpActiveItemId "
               "&& OperationNo = ThisItem.OperationNo).PackagesKey, \";\")")

    # Een pille pr. celle, centreret i kolonnen. Klikket slaar pakken til
    # eller fra paa operationen - samme handling som pillerne paa
    # operationslinjen (_pill_parts), saa de to visninger ikke kan glide fra
    # hinanden.
    cell_img = f'"data:image/svg+xml;utf8," & EncodeUrl({_pill_svg(PILL_W)})'
    cellPill, cellHit = _pill_parts("VhpPkg", str(PILL_W), cell_img, ROW_H,
                                    x=str((CELL_W - PILL_W) // 2))
    cell_items = (
        "With(\n"
        f"    {{ op: ThisItem.OperationNo, k: {cur_key} }},\n"
        f"    ForAll(\n"
        f"        {PKGS_SORTED} As P,\n"
        "        {\n"
        "            PackageNo: P.PackageNo, ShortCode: P.ShortCode,\n"
        "            CycleLength: P.CycleLength, CycleUnit: P.CycleUnit, OpNo: op,\n"
        "            Sel: \";\" & Text(P.PackageNo) & \";\" in k,\n"
        "            NoPkg: Len(k) <= 1\n"
        "        }\n"
        "    )\n"
        ")"
    )
    cellsGal = _pkg_cell_gallery("galVhpPkgCells", None, items=cell_items)
    cellsGal.children = [cellPill, cellHit]

    # Hele skabelonens hoejde, ikke "- 2": cellerne er ROW_H hoeje, og
    # skabelonen er ROW_H. Med "- 2" var raekken 38 px til 40 px indhold.
    # Det kunne foerst ses, da skabelonens hoejde blev skrevet ud som et
    # tal (gen_screen.resolve_templates) i stedet for Parent.TemplateHeight.
    lblGap = group("conVhpPkgRowGap", [], direction="Horizontal", height=0, width=str(LBL_GAP))
    lblGap2 = group("conVhpPkgRowGap2", [], direction="Horizontal", height=0, width=str(LBL_GAP))
    matrixRow = group("conVhpPkgRow", pin_widths([rowOpNo, lblGap, rowText, lblGap2, cellsGal]),
                      direction="Horizontal", gap=0,
                      height="Parent.TemplateHeight", align_items="Center",
                      width="Parent.TemplateWidth")

    # + 2: TemplatePadding over foerste raekke. Uden den var indholdet 2 px
    # hoejere end galleriet, og det rullede et hak med musehjulet (#506).
    rows_h = f"Max(CountRows({OPS_ACTIVE}), 1) * {GAL_ROW_H} + 2"
    rowsGal = Ctrl(
        "galVhpPkgRows", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Package matrix\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_TRANSPARENT,
            "FillPortions": "0",
            "Height": rows_h,
            "Items": f"Sort({OPS_ACTIVE}, Value(OperationNo))",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": str(ROW_H),
            "Width": f"{MATRIX_W} + 4",   # + TemplatePadding i begge sider
            "WrapCount": "1",
        },
        children=[matrixRow], h=rows_h)

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
            "    \"Strategy \" & varVhpPlan.Strategy & \" has no packages in MD_StrategyPackage yet, \" &\n"
            "        \"so there is nothing to allocate. The packages come from SAP (IP11). \" &\n"
            "        \"The plan can still be saved and submitted without a package allocation.\",\n"
            "\n"
            "    \"No operations on the active item yet. \" &\n"
            "        \"Add operations under Task list and operations.\"\n"
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
            "            \"S5: package \" & Concat(emptyPkg, ShortCode, \", \") & \" contains no operations.\",\n"
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
