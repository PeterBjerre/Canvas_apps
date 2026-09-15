# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY,
                        C_WHITE, C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT, SHELL_W)
import build_help as bh
from build_helpers import (text_ctrl, group, button, text_input, number_input, dropdown, label_row,
                           field_cell, row_n, col_width, badge, card)

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
    return f"varVhpHelp{section.capitalize()}"


def section_header(name, title, desc, step_label, help_section=None):
    """Sektionsoverskrift, evt. med et ? der folder hjaelpepanelet ud.

    Knappen skifter en variabel, og panelet ser paa den samme variabel. To
    kontroller, ingen tilstand at holde styr paa."""
    t = text_ctrl(f"{name}Title", f"\"{title}\"", size=19, weight="Semibold", height=26, wrap="false")
    d = text_ctrl(f"{name}Desc", f"\"{desc}\"", size=13, color=C_MUTED, height=20, wrap="false")

    right = []
    reserved = 0
    if help_section:
        v = help_var(help_section)
        btn = button(f"{name}Help", f"If({v}, \"Skjul hjaelp\", \"? Hjaelp\")",
                     f"Set({v}, !{v})", width=110, height=30)
        btn.props["Appearance"] = f"If({v}, ButtonAppearance.Primary, ButtonAppearance.Secondary)"
        btn.props["BasePaletteColor"] = C_INFO_FG
        btn.props["Color"] = f"If({v}, {C_WHITE}, {C_INFO_FG})"
        btn.props["BorderColor"] = C_CARD_BORDER
        btn.props["BorderThickness"] = "1"
        right.append(btn)
        reserved += 110 + 12
    if step_label:
        right.append(badge(f"{name}Badge", f"\"{step_label}\"", width=64))
        reserved += 64 + 12

    if right:
        left = group(f"{name}Left", [t, d], direction="Vertical", gap=2, height=48, fill_portions=1,
                     width=f"Parent.Width - {reserved}")
        return group(f"{name}", [left] + right, direction="Horizontal", gap=12, height=48,
                     align_items="Center")
    left = group(f"{name}Left", [t, d], direction="Vertical", gap=2, height=48, fill_portions=1)
    return group(f"{name}", [left], direction="Horizontal", gap=12, height=48, align_items="Center")


def help_panel(name, section):
    """Foldet ud af ?-knappen. Hoejden regnes af teksten, som alt andet.

    Afsnittene staar i build_help.PANELS, saa teksten kan rettes uden at
    nogen skal ind i layoutkoden."""
    v = help_var(section)
    kids = []
    # bh._q() dobler anfoerselstegn. Uden den braekkede kilde-linjen
    # udtrykket: teksten naevner "Den gode VH-plan" MED anfoerselstegn, og
    # de lukkede strengen midt i saetningen. Power Fx laeste resten som
    # navne og gav 18 fejl pr. egenskab.
    for i, (head, body) in enumerate(bh.PANELS[section]):
        kids.append(text_ctrl(f"{name}H{i}", bh._q(head), size=13, weight="Semibold",
                              height=18, wrap="false"))
        kids.append(text_ctrl(f"{name}B{i}", bh._q(body), size=12, color=C_MUTED,
                              height=(18 * (1 + len(body) // 95)), wrap="true"))
    kids.append(text_ctrl(f"{name}Src", bh._q(bh.SOURCE_NOTE), size=11, color=C_MUTED,
                          height=18, wrap="true"))
    return group(name, kids, direction="Vertical", gap=4, pad=(12, 14, 12, 14),
                 fill=C_INFO_BG, radius=10, visible=f"IfError({v}, false)")


def build_plan_header():
    header = section_header("conVhpPlanHead", "Plan Header",
                            "Vedligeholdelsesplanens stamdata og tidsparametre.", "Step 1",
                            help_section="plan")
    helpPanel = help_panel("conVhpPlanHelp", "plan")

    lockState = text_ctrl(
        "txtVhpPlanLockState",
        "If(varVhpPlanLocked, \"Plan locked: \" & varVhpPlan.Plant & \" \" & varVhpPlan.PlanText & \" (\" & varVhpPlan.Status & \"). Click Edit to make changes.\", \"Plan is open for editing.\")",
        size=13, color=f"If(varVhpPlanLocked, {C_INFO_FG}, {C_MUTED})", height=28, wrap="true",
        extra={"Fill": f"If(varVhpPlanLocked, {C_INFO_BG}, {C_NEUTRAL_BG})", "PaddingLeft": "10",
               "PaddingRight": "10", "PaddingTop": "4", "PaddingBottom": "4",
               "RadiusBottomLeft": "8", "RadiusBottomRight": "8", "RadiusTopLeft": "8", "RadiusTopRight": "8"})

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
        "drpVhpStrategy", "colVhpStrategies",
        "LookUp(colVhpStrategies, Key = varVhpPlan.Strategy)",
        item_display="ThisItem.Display",
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
                                   required_formula=REQ_PLAN, display_mode=DM_PLAN)
    numFirstCallMonth = number_input("numVhpFirstCallMonth", "varVhpPlan.FirstCallMonth", min_v=1, max_v=12,
                                     required_formula=REQ_PLAN, display_mode=DM_PLAN)
    numFirstCallYear = number_input("numVhpFirstCallYear", "varVhpPlan.FirstCallYear", min_v=2020, max_v=2100,
                                    required_formula=REQ_PLAN, display_mode=DM_PLAN)
    txtStatutorySortField = text_input("txtVhpStatutorySortField", "varVhpPlan.StatutorySortField",
                                       display_mode=DM_PLAN)

    # Fire kolonner i stedet for to. Rakkefoelgen af felter er uaendret -
    # de er bare grupperet 4 ad gangen i stedet for 2 ad gangen.
    CW = PLAN_CW
    PLAN_COLS = 4
    row0 = row_n("conVhpPlanRow0", [
        field_cell("conVhpCellPlanType", "Plan Type", drpPlanType, required=True,
                  container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("PlanType")),
        field_cell("conVhpCellStrategy", "Maintenance Strategy", drpStrategy,
                  container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("Strategy")),
        field_cell("conVhpCellPlant", "Plant", drpPlant, required=True, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("Plant")),
        field_cell("conVhpCellStatus", "Status", drpStatus, required=True, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("Status")),
    ], container_w=CW)
    row1 = row_n("conVhpPlanRow1", [
        field_cell("conVhpCellPlanText", "Plan Text", txtPlanText, required=True, container_w=CW,
                  cols=PLAN_COLS, hint_text=bh.hint("PlanText")),
        field_cell("conVhpCellSortField", "Sort Field", drpSortField, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("SortField")),
        field_cell("conVhpCellCycle", "Cycle", numCycle, required=True, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("Cycle")),
        field_cell("conVhpCellUnit", "Unit", drpUnit, required=True, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("Unit")),
    ], container_w=CW)
    # Dag, maaned og aar er EEN dato, ikke tre felter. De staar derfor i
    # samme celle, paa samme raekke, og fylder tilsammen den sidste af de
    # fire kolonner. Det frigiver samtidig hele row3, som kun indeholdt de
    # to overskydende felter og to tomme pladsholdere.
    FC_CELL = col_width(CW, PLAN_COLS)
    FC_GAP = 8
    FC_W = f"(({FC_CELL} - {2 * FC_GAP}) / 3)"
    for ctrl, w in ((numFirstCallDay, FC_W), (numFirstCallMonth, FC_W), (numFirstCallYear, FC_W)):
        ctrl.props["Width"] = w
    firstCallRow = group("conVhpFirstCallRow",
                         [numFirstCallDay, numFirstCallMonth, numFirstCallYear],
                         direction="Horizontal", gap=FC_GAP, height=36,
                         align_items="Center", width="Parent.Width")

    row2 = row_n("conVhpPlanRow2", [
        field_cell("conVhpCellCallHorizon", "Call Horizon", drpCallHorizon, container_w=CW,
                  cols=PLAN_COLS, hint_text=bh.hint("CallHorizon")),
        field_cell("conVhpCellSchedInd", "Scheduling Indicator", txtSchedInd, container_w=CW,
                  cols=PLAN_COLS, hint_text=bh.hint("SchedInd")),
        field_cell("conVhpCellStatutorySortField", "Statutory Sort Field", txtStatutorySortField,
                  container_w=CW, cols=PLAN_COLS, hint_text=bh.hint("StatutorySortField")),
        field_cell("conVhpCellFirstCall", "First Call  (dd / mm / aaaa)", firstCallRow,
                  required=True, container_w=CW, cols=PLAN_COLS,
                  hint_text=bh.hint("FirstCall")),
    ], container_w=CW)

    grid = group("conVhpPlanGrid", [row0, row1, row2],
                 direction="Vertical", gap=16)

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
            "\"Data: \" & Text(CountRows(colVhpTasklists)) & \" standardarbejdsplaner, \" &\n"
            "Text(CountRows(colVhpStrategies)) & \" strategier\" &\n"
            "With(\n"
            "    { mangler: CountRows(Filter(colVhpStrategies, !PackagesLoaded)) },\n"
            "    If(mangler > 0, \" (\" & Text(mangler) & \" uden pakker)\", \"\")\n"
            ") & \", \" &\n"
            "Text(CountRows(colVhpMainWorkCenters)) & \" arbejdscentre.\""
        ),
        size=12, color=C_MUTED, height=18, wrap="true")
    footerInfo = group("conVhpPlanFooterInfo", [planMeta, optionsState], direction="Vertical", gap=2, height=40,
                       fill_portions=1)

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

    footer = group("conVhpPlanFooter", [footerInfo, btnSave], direction="Horizontal", gap=16, height=40,
                   align_items="Center")

    return card("conVhpPlanCard", [header, helpPanel, lockState, grid, footer])
