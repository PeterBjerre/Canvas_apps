# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_MUTED, C_REQUIRED, C_INFO_BG, SHELL_W, C_DISABLED_BG, C_DIVIDER
import build_help as bh
import layout_tokens as lay
from build_helpers import (child_name, text_min_height, text_ctrl, group, button, text_input, number_input,
                           themed_dropdown, field_cell, col_width, badge, card, grow,
                           column_grid, text_px, fit_button_width, ICON_W)

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
SUMMARY_VIS = "(varVhpPlanLocked && " + lay.at_least("Tablet") + ")"
INFO_VIS = "(varVhpPlanLocked && " + lay.below("Tablet") + ")"


def plan_info_modal():
    from build_helpers import text_modal
    body = ('"Plant: " & Text(varVhpPlan.Plant) & Char(10) & "Plan text: " & Coalesce(varVhpPlan.PlanText, "")'
            ' & Char(10) & If(' + IS_STRATEGY + ', "Strategy: " & Coalesce(varVhpPlan.Strategy, ""), '
            '"Cycle: Every " & Text(varVhpPlan.Cycle) & " " & varVhpPlan.Unit)'
            ' & Char(10) & "First call: " & Text(varVhpPlan.FirstCallDay) & "/" & Text(varVhpPlan.FirstCallMonth)'
            ' & "/" & Text(varVhpPlan.FirstCallYear)')
    return text_modal("VhpPlanInfo", "varVhpPlanInfoOpen", '"Plan header"', body, 96)
REQ_PLAN = "varVhpPlanValidated"


def summary_chips(name, segs, visible, label, max_w=None):
    """Den sammenklappede sektions linje (issue #54, #103): een "chip" pr.
    (etiket, vaerdi), tegnet som EEN SVG. Plan Header, Item Editor og
    Tasklist and Operations bruger den samme, saa de ser ens ud.

    max_w: hoejeste bredde. Er chipsene bredere, skaleres billedet ned
    (ImagePosition.Fit) i stedet for at blive klippet."""
    from design_tokens import ref_hex
    from gen_screen import Ctrl as _C
    esc = lambda e: f'Substitute(Substitute({e}, "&", "&amp;"), "<", "&lt;")'
    n = len(segs)
    binds, widths = [], []
    for i, (lab, val) in enumerate(segs, 1):
        binds.append(f"l{i}: {lab}")
        binds.append(f"v{i}: {val}")
        widths.append(f"w{i}: 30 + Len(l{i}) * 7 + Len(v{i}) * 7.4")
    head = ("With({ " + ", ".join(binds) + " },\n  With({ " + ", ".join(widths)
            + " },\n    %s\n))")
    tot = " + ".join(f"w{i}" for i in range(1, n + 1)) + f" + {8 * (n - 1)}"
    fill, line = ref_hex("state-neutral-bg"), ref_hex("border-default")
    mut, txt = ref_hex("text-muted"), ref_hex("text-primary")
    parts = ['"<svg xmlns=\'http://www.w3.org/2000/svg\' height=\'32\' width=\'" & (' + tot + ') & "\'>"']
    xs = ["0"] + [" + ".join(f"w{j}" for j in range(1, i)) + f" + {8 * (i - 1)}"
                  for i in range(2, n + 1)]
    for i in range(1, n + 1):
        x, w = xs[i - 1], f"w{i}"
        parts.append(
            f'"<rect x=\'" & ({x} + 1) & "\' y=\'2\' rx=\'14\' width=\'" & ({w} - 2) & "\' height=\'28\' '
            f'fill=\'" & {fill} & "\' stroke=\'" & {line} & "\'/>"')
        parts.append(
            f'"<text x=\'" & ({x} + 14) & "\' y=\'20\' font-family=\'Segoe UI, sans-serif\' font-size=\'10\' '
            f'font-weight=\'600\' letter-spacing=\'.5\' fill=\'" & {mut} & "\'>" & {esc("l%d" % i)} & "</text>"')
        parts.append(
            f'"<text x=\'" & ({x} + 20 + Len(l{i}) * 7) & "\' y=\'20\' font-family=\'Segoe UI, sans-serif\' '
            f'font-size=\'13\' font-weight=\'600\' fill=\'" & {txt} & "\'>" & {esc("v%d" % i)} & "</text>"')
    parts.append('"</svg>"')
    img = '"data:image/svg+xml;utf8," & EncodeUrl(\n        ' + " &\n        ".join(parts) + "\n    )"
    width = tot if max_w is None else f"Min({tot}, {max_w})"
    return _C(name, "Image", props={
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Height": "32", "Image": head % img, "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false", "TabIndex": "-1", "Visible": visible,
        "Width": head % width, "AlignInContainer": "AlignInContainer.Start",
    }, h=32, vis=visible)


def summary_info_button(name, text, open_var, accessible, visible):
    """Telefonens udgave af linjen: chipsene er for brede, saa en knap
    aabner de samme vaerdier i et laeseudsnit (build_helpers.text_modal)."""
    b = button(name, text, f"Set({open_var}, true)",
               width=fit_button_width(text) + 8, height=32, visible=visible,
               accessible=accessible)
    b.props["AlignInContainer"] = "AlignInContainer.Start"
    return b


def _summary_chips():
    first = ('Text(varVhpPlan.FirstCallDay) & "/" & Text(varVhpPlan.FirstCallMonth) & "/" & '
             'Text(varVhpPlan.FirstCallYear)')
    cycle = (f'If({IS_STRATEGY}, Coalesce(varVhpPlan.Strategy, ""), "Every " & Text(varVhpPlan.Cycle) '
             '& " " & varVhpPlan.Unit)')
    segs = [('"PLANT"', 'Text(varVhpPlan.Plant)'), ('"PLAN TEXT"', 'Coalesce(varVhpPlan.PlanText, "")'),
            (f'If({IS_STRATEGY}, "STRATEGY", "CYCLE")', cycle), ('"FIRST CALL"', first)]
    label = ('Coalesce(varVhpPlan.PlanText, "") & ", " & ' + cycle + ' & ", first call " & ' + first)
    return summary_chips("imgVhpPlanSummary", segs, SUMMARY_VIS, label)

# Indholdsbredden i et kort: skaermens indholdsbredde minus kortets polstring.
PLAN_CW = f"({SHELL_W} - 36)"

# En strategiplan henter sin cyklus fra strategiens pakker. Cycle/Unit paa
# planhovedet gaelder derfor kun single cycle-planer.
# Parenteserne er ikke pynt: i Power Fx binder ! haardere end =, saa
# !varVhpPlan.PlanType = "Strategy" ville blive laest som
# (!varVhpPlan.PlanType) = "Strategy".
IS_STRATEGY = "(varVhpPlan.PlanType = \"Strategy\")"
NOT_STRATEGY = "(varVhpPlan.PlanType <> \"Strategy\")"

# Editerbarheden af Strategy-dropdownen og Cycle/Unit skal foelge den VALGTE
# (endnu ikke gemte) Plan Type, ikke den gemte varVhpPlan.PlanType. Ellers
# opstaar en catch-22: brugeren skifter Plan Type til Strategiplan, men
# Strategy-dropdownen forbliver disabled indtil planen er gemt - og planen
# kan ikke gemmes foer der er valgt en strategi (Save kraever
# drpVhpStrategy.Selected.Key, naar Plan Type er Strategy).
LIVE_IS_STRATEGY = "(drpVhpPlanType.Selected.Key = \"Strategy\")"
LIVE_NOT_STRATEGY = "(drpVhpPlanType.Selected.Key <> \"Strategy\")"
DM_CYCLE = f"If(varVhpPlanLocked || {LIVE_IS_STRATEGY}, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_CYCLE = f"(varVhpPlanValidated && {LIVE_NOT_STRATEGY})"


def help_var(section):
    """Alle fire hjaelpepaneler foelger den ENE Help-knap i topbjaelken
    (build_hero.imgVhpHelp) - den samme variabel som feltforklaringerne.
    Foer havde hver sektion sin egen "? Help" og sin egen variabel."""
    return "varVhpShowHints"


def required_legend():
    """ "* Required" - forklaringen paa stjernerne. Stod i hero-kortet; nu i
    Plan Header, hvor de foerste stjerner staar."""
    star = text_ctrl("txtVhpLegendStar", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                     height=20, width=10, wrap="false")
    txt = text_ctrl("txtVhpLegendText", "\"Required\"", size=13, color=C_MUTED, height=20,
                    width=70, wrap="false")
    return group("conVhpLegend", [star, txt], direction="Horizontal", gap=3, height=20,
                 align_items="Center", width=83)


def section_header(name, title, step_label, extra_right=(), extra_left=()):
    """Sektionsoverskrift: titlen til venstre (evt. med noget lige efter
    den, fx "* Required"), og et trin-badge til hoejre.

    Beskrivelsen under titlen er fjernet (issue #54). Den gentog blot det,
    sektionen viser, og kostede en linje paa hvert kort."""
    t = text_ctrl(child_name("txt", name, "Title"), f"\"{title}\"", size=lay.SIZE_CARD_TITLE, weight="Semibold",
                  height=text_min_height(lay.SIZE_CARD_TITLE),
                  width=text_px(title, lay.SIZE_CARD_TITLE), wrap="false")
    t.props["LayoutMinWidth"] = t.props["Width"]

    right = list(extra_right)
    if step_label:
        right.append(badge(child_name("txt", name, "Badge"), f"\"{step_label}\"", width=64))

    # FLAD RAEKKE (issue #54 - titlerne manglede i Studio). Titlen staar
    # DIREKTE i overskriftens raekke, ikke i en indlejret gruppe, og en tom
    # gruppe tager resten af bredden. Da titlen flyttede fra en lodret til
    # en vandret indlejret gruppe, lagde Studio den ikke rigtigt om - det er
    # netop den flytning mellem foraeldre, deploy advarer om. Uden en
    # indlejret titelgruppe er der intet at flytte forkert.
    gap = group(f"{name}Gap", [], direction="Horizontal", height=0)
    grow(gap)
    return group(f"{name}", [t] + list(extra_left) + [gap] + right, direction="Horizontal",
                 gap=12, align_items="Center")


# Hoejden paa EET afsnit i hjaelpepanelet.
#
# FOER kunne den regnes: teksten stod i koden, og hoejden var
# 18 * (1 + len(body) // 95) - et gaet paa antallet af linjer ud fra
# antallet af tegn. Nu staar teksten i SharePoint, og laengden kendes
# ikke, naar appen bygges.
#
# Derfor et gallery med en FAST skabelonhoejde: overskrift 18 + fire
# linjer broedtekst a 16 + 6 px luft. Fire linjer daekker det laengste af
# de 21 afsnit, seedet blev lavet af (objektlisten, 312 tegn ~ 3,3
# linjer ved 95 tegn). Et laengere afsnit bliver klippet - det er prisen
# for at teksten kan rettes uden en build, og den staar her, saa den er
# til at se.
HELP_LINE_H = 18 + 4 * 16 + 6


def help_panel(name, section):
    """Foldet ud af ?-knappen. Afsnittene kommer fra MD_HelpText.

    Teksten kan dermed rettes af dem, der kender fagligheden, uden at
    nogen skal bygge appen. Se build_help.py."""
    v = help_var(section)
    head = text_ctrl(child_name("txt", name, "H"), "ThisItem.Heading", size=13, weight="Semibold",
                     height=18, wrap="false",
                     visible='!IsBlank(ThisItem.Heading)')
    body = text_ctrl(child_name("txt", name, "B"), "ThisItem.Body", size=12, color=C_MUTED,
                     height=HELP_LINE_H - 18 - 6, wrap="true")
    tmpl = group(f"{name}Row", [head, body], direction="Vertical", gap=2,
                 width="Parent.TemplateWidth",
                 height="Parent.TemplateHeight - 2")
    gal = Ctrl(child_name("gal", name), "Gallery", variant="Vertical", props={
        # Tilgaengelighedstjekket: en Gallery UDEN AccessibleLabel er fire
        # fejl i VH-plan - eet pr. hjaelpepanel. En skaermlaeser skal kunne
        # sige, hvad listen indeholder.
        "AccessibleLabel": f'"Help for {section}"',
        "DelayItemLoading": "false",
        "Items": bh.panel(section),
        "LoadingSpinner": "LoadingSpinner.None",
        "ShowScrollbar": "false",
        # Gallery uden TabIndex melder App checker som "Missing tab stop".
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(HELP_LINE_H),
        "Width": "Parent.Width",
        # Tom liste skal stadig fylde EEN raekke, ellers bliver panelet
        # et farvet baand uden indhold, som ingen kan forklare.
        "Height": f"Max(CountRows({bh.panel(section)}), 1) * {HELP_LINE_H}",
    }, children=[tmpl],
        h=f"Max(CountRows({bh.panel(section)}), 1) * {HELP_LINE_H}")
    empty = text_ctrl(
        child_name("txt", name, "Empty"),
        bh._q("No help text for this section yet - it is maintained in "
              "the SharePoint list MD_HelpText."),
        size=12, color=C_MUTED, height=32, wrap="true",
        visible=f"CountRows({bh.panel(section)}) = 0")
    return group(name, [gal, empty], direction="Vertical", gap=4,
                 pad=(12, 14, 12, 14), fill=C_INFO_BG, radius=10,
                 visible=f"IfError({v}, false)")


# Alle planhovedets kontroller - Reset-knappen nulstiller dem, og de har
# alle varVhpPlan som Default. Reset() giver derfor den senest gemte plan
# tilbage, eller appens startvaerdier, hvis planen aldrig er gemt.
PLAN_CONTROLS = ("drpVhpPlanType", "drpVhpStrategy", "drpVhpPlant", "drpVhpStatus",
                 "inpVhpPlanText", "drpVhpSortField", "numVhpCycle", "drpVhpUnit",
                 "numVhpFirstCallDay", "numVhpFirstCallMonth", "numVhpFirstCallYear")


def build_plan_header():
    # "* Required" staar lige efter titlen i venstre side. I hoejre side,
    # mellem titlen og trin-badget, blev den klippet (issue #54).
    header = section_header("conVhpPlanHead", "Plan Header", "Step 1",
                            extra_left=[required_legend()])
    helpPanel = help_panel("conVhpPlanHelp", "plan")

    # Statusbanneret ("Plan is open for editing" / "Plan locked ...") er
    # fjernet (issue #54). At planen er laast, ses paa de graa felter og paa
    # knappen, der hedder Edit i stedet for Save.

    drpPlant = themed_dropdown("drpVhpPlant", "colVhpPlantCodes",
                               "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant).Value",
                               required_formula=REQ_PLAN, display_mode=DM_PLAN)
    drpStatus = themed_dropdown("drpVhpStatus", "colVhpPlanStatusOptions",
                         "LookUp(colVhpPlanStatusOptions, Value = varVhpPlan.Status).Value",
                         required_formula=REQ_PLAN, display_mode=DM_PLAN)

    # --- Plantype og strategi ------------------------------------------------
    drpPlanType = themed_dropdown("drpVhpPlanType", "colVhpPlanTypeOptions",
                           "LookUp(colVhpPlanTypeOptions, Key = varVhpPlan.PlanType).Value",
                           required_formula=REQ_PLAN, display_mode=DM_PLAN,
                           value_col="Key", display_col="Value")
    drpStrategy = themed_dropdown(
        "drpVhpStrategy", "colVhpStrategyOptions",
        "LookUp(colVhpStrategyOptions, Key = varVhpPlan.Strategy).Value",
        required_formula=f"(varVhpPlanValidated && {LIVE_IS_STRATEGY})",
        display_mode=f"If(varVhpPlanLocked || {LIVE_NOT_STRATEGY}, DisplayMode.Disabled, DisplayMode.Edit)",
        value_col="Key", display_col="Value")
    off = "Self.DisplayMode <> DisplayMode.Edit"
    drpStrategy.props["Appearance"] = "Appearance.FilledDarker"
    drpStrategy.props["Fill"] = f"If({off}, {C_DISABLED_BG}, {drpStrategy.props['Fill']})"
    drpStrategy.props["BorderColor"] = f"If({off}, {C_DIVIDER}, {drpStrategy.props['BorderColor']})"
    drpStrategy.props["Color"] = f"If({off}, {C_MUTED}, {drpStrategy.props['Color']})"

    PT, PL = "varVhpPlan.PlanText", "drpVhpPlant.Selected.Value"
    pt_rest = (f'If(StartsWith(Upper({PT}), Upper(varVhpPlan.Plant) & " "), '
               f'Mid({PT}, Len(varVhpPlan.Plant) + 2), {PT})')
    pt_default = (f'If(\n    varVhpViewOnly || IsBlank({PL}), {PT},\n'
                  f'    Upper(Trim({PT})) = Upper({PL}), {PL} & " ",\n'
                  f'    StartsWith(Upper({PT}), Upper({PL}) & " "), {PT},\n'
                  f'    {PL} & " " & {pt_rest}\n)')
    txtPlanText = text_input("inpVhpPlanText", pt_default, max_length=40,
                             required_formula=REQ_PLAN, display_mode=DM_PLAN,
                             onchange=(f'If(!varVhpViewOnly && !IsBlank({PL}) && '
                                       f'!StartsWith(Upper(Self.Text), Upper({PL}) & " "), Reset(Self))'))
    drpSortField = themed_dropdown("drpVhpSortField", "colVhpSortFieldOptions",
                            "LookUp(colVhpSortFieldOptions, Value = varVhpPlan.SortField).Value",
                            display_mode=DM_PLAN)
    numCycle = number_input("numVhpCycle", "varVhpPlan.Cycle", min_v=1, required_formula=REQ_CYCLE,
                            display_mode=DM_CYCLE)
    drpUnit = themed_dropdown("drpVhpUnit", "colVhpUnitOptions", "LookUp(colVhpUnitOptions, Value = varVhpPlan.Unit).Value",
                       required_formula=REQ_CYCLE, display_mode=DM_CYCLE)
    numFirstCallDay = number_input("numVhpFirstCallDay", "varVhpPlan.FirstCallDay", min_v=1, max_v=31,
                                   required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"First call, day\"")
    numFirstCallMonth = number_input("numVhpFirstCallMonth", "varVhpPlan.FirstCallMonth", min_v=1, max_v=12,
                                     required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"First call, month\"")
    numFirstCallYear = number_input("numVhpFirstCallYear", "varVhpPlan.FirstCallYear", min_v=2020, max_v=2100,
                                    required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"First call, year\"")

    # KOLONNE-ORDEN (issue #54). Felterne udfyldes oppefra og ned i hver
    # kolonne, foer naeste kolonne begynder - Plan Type, Maintenance
    # Strategy og Plant staar under hinanden i kolonne 1. Foer stod de fire
    # og fire paa raekker.
    CW = PLAN_CW
    PLAN_COLS = 4
    FC_CELL = col_width(CW, PLAN_COLS)

    def cell(name, label, ctrl, hint, required=False):
        return field_cell(name, label, ctrl, required=required, width=FC_CELL,
                          container_w=CW, fill_portions_formula="0",
                          hint_text=bh.hint(hint))

    # Dag, maaned og aar er EEN dato, ikke tre felter. De staar derfor i
    # samme celle, paa samme raekke.
    FC_GAP = 8
    FC_W = f"(({FC_CELL} - {2 * FC_GAP}) / 3)"
    for ctrl in (numFirstCallDay, numFirstCallMonth, numFirstCallYear):
        ctrl.props["Width"] = FC_W
    firstCallRow = group("conVhpFirstCallRow",
                         [numFirstCallDay, numFirstCallMonth, numFirstCallYear],
                         direction="Horizontal", gap=FC_GAP, height=36,
                         align_items="Center", width="Parent.Width")

    cellStrategy = cell("conVhpCellStrategy", "Maintenance Strategy", drpStrategy, "Strategy")
    cellStrategy.props["Visible"] = LIVE_IS_STRATEGY
    cellStrategy.vis = LIVE_IS_STRATEGY

    grid = column_grid("conVhpPlanGrid", [
        [cell("conVhpCellPlanType", "Plan Type", drpPlanType, "PlanType", True),
         cell("conVhpCellPlant", "Plant", drpPlant, "Plant", True),
         cellStrategy],
        [cell("conVhpCellStatus", "Status", drpStatus, "Status", True),
         cell("conVhpCellPlanText", "Plan Text", txtPlanText, "PlanText", True)],
        [cell("conVhpCellSortField", "Sort Field", drpSortField, "SortField"),
         cell("conVhpCellCycle", "Cycle", numCycle, "Cycle", True)],
        [cell("conVhpCellUnit", "Unit", drpUnit, "Unit", True),
         cell("conVhpCellFirstCall", "First Call (dd / mm / yyyy)", firstCallRow,
              "FirstCall", True)],
    ], container_w=CW, row_gap=10)

    planMeta = text_ctrl(
        "txtVhpPlanMeta",
        f"If(varVhpPlanCommitted, \"Plan created \" & Text(varVhpPlanCreatedAt, \"{lay.DATETIME_FMT}\"), \"\")",
        size=12, color=C_MUTED, height=24, wrap="false", visible="!varVhpPlanLocked")
    summary = _summary_chips()
    info = summary_info_button("btnVhpPlanInfo", '"Plan details"', "varVhpPlanInfoOpen",
                               '"Show the plan header details"', INFO_VIS)
    footerInfo = grow(group("conVhpPlanFooterInfo", [summary, info, planMeta], direction="Vertical",
                            gap=0, height=32))

    btnSave = button(
        "btnVhpPlanSave", "If(varVhpPlanLocked, \"Edit\", \"Save\")",
        (
            "If(\n"
            "    varVhpPlanLocked,\n"
            "    Set(varVhpViewOnly, false);\n"
            "    Set(varVhpPlanLocked, false);\n"
            "    Notify(\"Plan unlocked for editing.\", NotificationType.Success),\n"
            "\n"
            "    Set(varVhpPlanValidated, true);\n"
            "    With(\n"
            "        { isStrat: drpVhpPlanType.Selected.Key = \"Strategy\" },\n"
            "        If(\n"
            "            IsBlank(drpVhpPlant.Selected.Value) ||\n"
            "            IsBlank(drpVhpStatus.Selected.Value) ||\n"
            "            IsBlank(drpVhpPlanType.Selected.Key) ||\n"
            "            (isStrat && IsBlank(drpVhpStrategy.Selected.Key)) ||\n"
            "            IsBlank(Trim(inpVhpPlanText.Text)) || Len(Trim(inpVhpPlanText.Text)) > 40 ||\n"
            "            (!isStrat && (IsBlank(numVhpCycle.Value) || numVhpCycle.Value <= 0)) ||\n"
            "            (!isStrat && IsBlank(drpVhpUnit.Selected.Value)) ||\n"
            "            IsBlank(numVhpFirstCallDay.Value) || numVhpFirstCallDay.Value < 1 || numVhpFirstCallDay.Value > 31 ||\n"
            "            IsBlank(numVhpFirstCallMonth.Value) || numVhpFirstCallMonth.Value < 1 || numVhpFirstCallMonth.Value > 12 ||\n"
            "            IsBlank(numVhpFirstCallYear.Value) || numVhpFirstCallYear.Value < 2020 || numVhpFirstCallYear.Value > 2100,\n"
            "            Notify(\"Plan contains issues. Fix plan fields before creating items.\", NotificationType.Warning),\n"
            "\n"
            # Vaerket FOER gemningen - se plantskiftet nedenfor.
            "            Set(varVhpPrevPlant, varVhpPlan.Plant);\n"
            "            Set(\n"
            "                varVhpPlan,\n"
            "                {\n"
            "                    Plant: drpVhpPlant.Selected.Value,\n"
            "                    Status: drpVhpStatus.Selected.Value,\n"
            "                    PlanType: drpVhpPlanType.Selected.Key,\n"
            "                    Strategy: If(isStrat, drpVhpStrategy.Selected.Key, \"\"),\n"
            "                    PlanText: Trim(inpVhpPlanText.Text),\n"
            "                    SortField: drpVhpSortField.Selected.Value,\n"
            "                    Cycle: If(isStrat, 0, numVhpCycle.Value),\n"
            "                    Unit: If(isStrat, \"\", drpVhpUnit.Selected.Value),\n"
            "                    FirstCallDay: numVhpFirstCallDay.Value,\n"
            "                    FirstCallMonth: numVhpFirstCallMonth.Value,\n"
            "                    FirstCallYear: numVhpFirstCallYear.Value\n"
            "                }\n"
            "            );\n"
            "            Set(varVhpPlanCommitted, true);\n"
            "            Set(varVhpPlanLocked, true);\n"
            "            Set(varVhpPlanCreatedAt, Now());\n"
            # PLANT ER FAELLES KONTEKST (issue #54). Arbejdscentre, tasklister
            # og FL-soegningen laeser varVhpPlan.Plant. Skifter vaerket, viser
            # de afhaengige felter kun det, der passer til det nye vaerk -
            # Reset henter deres Default, som slaar op i den FILTREREDE
            # liste, saa et ugyldigt valg bliver tomt. Gemte items roeres
            # ikke: de bliver roede, naar de gemmes igen, i stedet for at
            # blive slettet uden at nogen har bekraeftet det.
            "            If(\n"
            "                !IsBlank(varVhpPrevPlant) && Upper(varVhpPrevPlant) <> Upper(drpVhpPlant.Selected.Value),\n"
            "                Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemTasklist); Reset(cmbVhpItemFL);\n"
            "                Notify(\n"
            "                    \"Plant changed to \" & drpVhpPlant.Selected.Value &\n"
            "                        \". Check work centre, task list and functional location on existing items.\",\n"
            "                    NotificationType.Warning\n"
            "                )\n"
            "            );\n"
            "            Notify(\n"
            "                \"Plan saved and locked: \" & drpVhpPlant.Selected.Value & \" \" & Trim(inpVhpPlanText.Text) &\n"
            "                If(isStrat, \" (strategy \" & drpVhpStrategy.Selected.Key & \").\", \".\"),\n"
            "                NotificationType.Success\n"
            "            )\n"
            "        )\n"
            "    )\n"
            ")"
        ),
        primary=True, width=140, height=36,
        icon="If(varVhpPlanLocked, \"Edit\", \"Save\")",
        # Edit kun i Edit mode (issue #103) - i View mode skifter topbjaelkens
        # Edit (build_hero.btnVhpEdit) til Edit mode, som for de andre sektioner.
        visible="!varVhpViewOnly")

    # RESET (issue #54): de usavede aendringer i planhovedet tilbage til
    # den senest gemte plan - eller startvaerdierne, hvis planen aldrig er
    # gemt. Alle felterne har varVhpPlan som Default, saa Reset() ER
    # "senest gemt". Var planen gemt, laases den igen: den matcher nu det
    # gemte, og trinnet er faerdigt igen.
    btnReset = button(
        "btnVhpPlanReset", "\"Reset\"",
        "; ".join(f"Reset({c})" for c in PLAN_CONTROLS) + ";\n"
        "Set(varVhpPlanValidated, false);\n"
        "If(varVhpPlanCommitted, Set(varVhpPlanLocked, true))",
        width=fit_button_width("\"Reset\""), height=36,
        display_mode="If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)")
    btnSave.props["Width"] = str(fit_button_width("\"Save\"", min_w=96) + ICON_W)

    footer = group("conVhpPlanFooter", [footerInfo, btnReset, btnSave], direction="Horizontal",
                   gap=8, height=36, align_items="Center")

    # SAMLET SAMMEN, NAAR PLANEN ER GEMT. Felterne og hjaelpepanelet vises kun,
    # mens planen kan redigeres; derefter staar en linje med det vigtigste, og
    # Edit folder dem ud igen.
    OPEN_EDIT = "!varVhpPlanLocked"
    grid.props["Visible"] = OPEN_EDIT
    grid.vis = OPEN_EDIT
    helpPanel.vis = f"({OPEN_EDIT}) && IfError(varVhpShowHints, false)"
    helpPanel.props["Visible"] = helpPanel.vis
    btnReset.props["Visible"] = OPEN_EDIT
    btnReset.vis = OPEN_EDIT

    return card("conVhpPlanCard", [header, helpPanel, grid, footer], gap=10, pad_y=12)
