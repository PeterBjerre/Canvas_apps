# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY,
                        C_WHITE, C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT, SHELL_W)
import build_help as bh
from build_helpers import (text_ctrl, group, button, text_input, number_input, dropdown, label_row,
                           field_cell, row_n, col_width, badge, card, grow,
                           column_grid, text_px, fit_button_width)

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_PLAN = "varVhpPlanValidated"

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
    t = text_ctrl(f"{name}Title", f"\"{title}\"", size=19, weight="Semibold", height=29,
                  width=text_px(title, 19), wrap="false")
    t.props["LayoutMinWidth"] = t.props["Width"]

    right = list(extra_right)
    if step_label:
        right.append(badge(f"{name}Badge", f"\"{step_label}\"", width=64))

    left = grow(group(f"{name}Left", [t] + list(extra_left), direction="Horizontal",
                      gap=12, align_items="Center"))
    return group(f"{name}", [left] + right, direction="Horizontal", gap=12,
                 align_items="Center")


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
    head = text_ctrl(f"{name}H", "ThisItem.Heading", size=13, weight="Semibold",
                     height=18, wrap="false",
                     visible='!IsBlank(ThisItem.Heading)')
    body = text_ctrl(f"{name}B", "ThisItem.Body", size=12, color=C_MUTED,
                     height=HELP_LINE_H - 18 - 6, wrap="true")
    tmpl = group(f"{name}Row", [head, body], direction="Vertical", gap=2,
                 width="Parent.TemplateWidth",
                 height="Parent.TemplateHeight - 2")
    gal = Ctrl(f"{name}Gal", "Gallery", variant="Vertical", props={
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
        f"{name}Empty",
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
                 "txtVhpPlanText", "drpVhpSortField", "numVhpCycle", "drpVhpUnit",
                 "drpVhpCallHorizon", "txtVhpSchedInd", "txtVhpStatutorySortField",
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

    drpPlant = dropdown("drpVhpPlant", "colVhpPlantCodes", "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant)",
                        item_display="ThisItem.Value", required_formula=REQ_PLAN, display_mode=DM_PLAN)
    drpStatus = dropdown("drpVhpStatus", "colVhpPlanStatusOptions",
                         "LookUp(colVhpPlanStatusOptions, Value = varVhpPlan.Status)",
                         required_formula=REQ_PLAN, display_mode=DM_PLAN)

    # --- Plantype og strategi ------------------------------------------------
    drpPlanType = dropdown("drpVhpPlanType", "colVhpPlanTypeOptions",
                           "LookUp(colVhpPlanTypeOptions, Key = varVhpPlan.PlanType)",
                           item_display="ThisItem.Value", required_formula=REQ_PLAN,
                           display_mode=DM_PLAN, value_field="Key")
    drpStrategy = dropdown(
        "drpVhpStrategy", "colVhpStrategyOptions",
        "LookUp(colVhpStrategyOptions, Key = varVhpPlan.Strategy)",
        item_display="ThisItem.Value",
        required_formula=f"(varVhpPlanValidated && {LIVE_IS_STRATEGY})",
        display_mode=f"If(varVhpPlanLocked || {LIVE_NOT_STRATEGY}, DisplayMode.Disabled, DisplayMode.Edit)",
        value_field="Key")

    txtPlanText = text_input("txtVhpPlanText", "varVhpPlan.PlanText", max_length=40,
                             required_formula=REQ_PLAN, display_mode=DM_PLAN)
    drpSortField = dropdown("drpVhpSortField", "colVhpSortFieldOptions",
                            "LookUp(colVhpSortFieldOptions, Value = varVhpPlan.SortField)",
                            display_mode=DM_PLAN)
    numCycle = number_input("numVhpCycle", "varVhpPlan.Cycle", min_v=1, required_formula=REQ_CYCLE,
                            display_mode=DM_CYCLE)
    drpUnit = dropdown("drpVhpUnit", "colVhpUnitOptions", "LookUp(colVhpUnitOptions, Value = varVhpPlan.Unit)",
                       required_formula=REQ_CYCLE, display_mode=DM_CYCLE)
    drpCallHorizon = dropdown("drpVhpCallHorizon", "colVhpCallHorizonOptions",
                              "LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon)",
                              display_mode=DM_PLAN)
    txtSchedInd = text_input("txtVhpSchedInd", "varVhpPlan.SchedulingIndicator", display_mode=DM_PLAN)
    numFirstCallDay = number_input("numVhpFirstCallDay", "varVhpPlan.FirstCallDay", min_v=1, max_v=31,
                                   required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"Foerste kald, dag\"")
    numFirstCallMonth = number_input("numVhpFirstCallMonth", "varVhpPlan.FirstCallMonth", min_v=1, max_v=12,
                                     required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"Foerste kald, maaned\"")
    numFirstCallYear = number_input("numVhpFirstCallYear", "varVhpPlan.FirstCallYear", min_v=2020, max_v=2100,
                                    required_formula=REQ_PLAN, display_mode=DM_PLAN, label="\"Foerste kald, aar\"")
    txtStatutorySortField = text_input("txtVhpStatutorySortField", "varVhpPlan.StatutorySortField",
                                       display_mode=DM_PLAN)

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

    grid = column_grid("conVhpPlanGrid", [
        [cell("conVhpCellPlanType", "Plan Type", drpPlanType, "PlanType", True),
         cell("conVhpCellStrategy", "Maintenance Strategy", drpStrategy, "Strategy"),
         cell("conVhpCellPlant", "Plant", drpPlant, "Plant", True)],
        [cell("conVhpCellStatus", "Status", drpStatus, "Status", True),
         cell("conVhpCellPlanText", "Plan Text", txtPlanText, "PlanText", True),
         cell("conVhpCellSortField", "Sort Field", drpSortField, "SortField")],
        [cell("conVhpCellCycle", "Cycle", numCycle, "Cycle", True),
         cell("conVhpCellUnit", "Unit", drpUnit, "Unit", True),
         cell("conVhpCellCallHorizon", "Call Horizon", drpCallHorizon, "CallHorizon")],
        [cell("conVhpCellSchedInd", "Scheduling Indicator", txtSchedInd, "SchedInd"),
         cell("conVhpCellStatutorySortField", "Statutory Sort Field",
              txtStatutorySortField, "StatutorySortField"),
         cell("conVhpCellFirstCall", "First Call (dd / mm / yyyy)", firstCallRow,
              "FirstCall", True)],
    ], container_w=CW, row_gap=10)

    planMeta = text_ctrl(
        "txtVhpPlanMeta",
        "If(varVhpPlanCommitted, \"Plan created \" & Text(varVhpPlanCreatedAt, \"dd-mm-yyyy hh:mm\"), \"\")",
        size=12, color=C_MUTED, height=18, wrap="false")
    # Hvad der faktisk er hentet. Tallene taelles paa de navngivne formler,
    # saa de er rigtige i stedet for en haardkodet paastand om "14 option lists".
    # Antallet af strategier UDEN pakker naevnes eksplicit - ellers ser en kort
    # strategiliste ud som en fejl i stedet for som en mangel i masterdata.
    optionsState = text_ctrl(
        "txtVhpPlanOptionsState",
        (
            "\"Data: \" & Text(CountRows(colVhpTasklists)) & \" task lists, \" &\n"
            "Text(CountRows(colVhpStrategies)) & \" strategies\" &\n"
            "With(\n"
            "    { mangler: CountRows(Filter(colVhpStrategies, !PackagesLoaded)) },\n"
            "    If(mangler > 0, \" (\" & Text(mangler) & \" without packages)\", \"\")\n"
            ") & \", \" &\n"
            "Text(CountRows(colVhpMainWorkCenters)) & \" work centres.\""
        ),
        size=12, color=C_MUTED, height=18, wrap="true")
    footerInfo = grow(group("conVhpPlanFooterInfo", [planMeta, optionsState], direction="Vertical",
                            gap=2, height=40))

    btnSave = button(
        "btnVhpPlanSave", "If(varVhpPlanLocked, \"Edit\", \"Save\")",
        (
            "If(\n"
            "    varVhpPlanLocked,\n"
            "    Set(varVhpPlanLocked, false);\n"
            "    Set(varVhpRuntimeInfo, \"Plan unlocked for editing.\"),\n"
            "\n"
            "    Set(varVhpPlanValidated, true);\n"
            "    With(\n"
            "        { isStrat: drpVhpPlanType.Selected.Key = \"Strategy\" },\n"
            "        If(\n"
            "            IsBlank(drpVhpPlant.Selected.Value) ||\n"
            "            IsBlank(drpVhpStatus.Selected.Value) ||\n"
            "            IsBlank(drpVhpPlanType.Selected.Key) ||\n"
            "            (isStrat && IsBlank(drpVhpStrategy.Selected.Key)) ||\n"
            "            IsBlank(Trim(txtVhpPlanText.Text)) || Len(Trim(txtVhpPlanText.Text)) > 40 ||\n"
            "            (!isStrat && (IsBlank(numVhpCycle.Value) || numVhpCycle.Value <= 0)) ||\n"
            "            (!isStrat && IsBlank(drpVhpUnit.Selected.Value)) ||\n"
            "            IsBlank(numVhpFirstCallDay.Value) || numVhpFirstCallDay.Value < 1 || numVhpFirstCallDay.Value > 31 ||\n"
            "            IsBlank(numVhpFirstCallMonth.Value) || numVhpFirstCallMonth.Value < 1 || numVhpFirstCallMonth.Value > 12 ||\n"
            "            IsBlank(numVhpFirstCallYear.Value) || numVhpFirstCallYear.Value < 2020 || numVhpFirstCallYear.Value > 2100,\n"
            "            Set(varVhpRuntimeInfo, \"Plan contains issues. Fix plan fields before creating items.\"),\n"
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
            "                    PlanText: Trim(txtVhpPlanText.Text),\n"
            "                    SortField: drpVhpSortField.Selected.Value,\n"
            "                    Cycle: If(isStrat, 0, numVhpCycle.Value),\n"
            "                    Unit: If(isStrat, \"\", drpVhpUnit.Selected.Value),\n"
            "                    CallHorizon: drpVhpCallHorizon.Selected.Value,\n"
            "                    SchedulingIndicator: Trim(txtVhpSchedInd.Text),\n"
            "                    FirstCallDay: numVhpFirstCallDay.Value,\n"
            "                    FirstCallMonth: numVhpFirstCallMonth.Value,\n"
            "                    FirstCallYear: numVhpFirstCallYear.Value,\n"
            "                    StatutorySortField: Trim(txtVhpStatutorySortField.Text)\n"
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
            "                Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemTasklist); Reset(txtVhpFlQuery);\n"
            "                Notify(\n"
            "                    \"Plant changed to \" & drpVhpPlant.Selected.Value &\n"
            "                        \". Check work centre, task list and functional location on existing items.\",\n"
            "                    NotificationType.Warning\n"
            "                )\n"
            "            );\n"
            "            Set(\n"
            "                varVhpRuntimeInfo,\n"
            "                \"Plan saved and locked: \" & drpVhpPlant.Selected.Value & \" \" & Trim(txtVhpPlanText.Text) &\n"
            "                If(isStrat, \" (strategy \" & drpVhpStrategy.Selected.Key & \").\", \".\")\n"
            "            )\n"
            "        )\n"
            "    )\n"
            ")"
        ),
        primary=True, width=140, height=36)

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
    btnSave.props["Width"] = str(fit_button_width("\"Save\"", min_w=96))

    footer = group("conVhpPlanFooter", [footerInfo, btnReset, btnSave], direction="Horizontal",
                   gap=8, height=40, align_items="Center")

    # Kompakt (issue #54): 10 px mellem titel, felter og fod i stedet for 14.
    return card("conVhpPlanCard", [header, helpPanel, grid, footer], gap=10, pad_y=12)
