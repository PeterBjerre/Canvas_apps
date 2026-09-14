# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY,
                        C_WHITE, C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT, SHELL_W)
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


def section_header(name, title, desc, step_label):
    t = text_ctrl(f"{name}Title", f"\"{title}\"", size=19, weight="Semibold", height=26, wrap="false")
    d = text_ctrl(f"{name}Desc", f"\"{desc}\"", size=13, color=C_MUTED, height=20, wrap="false")
    if step_label:
        left = group(f"{name}Left", [t, d], direction="Vertical", gap=2, height=48, fill_portions=1,
                     width="Parent.Width - 64 - 12")
        right = badge(f"{name}Badge", f"\"{step_label}\"", width=64)
        return group(f"{name}", [left, right], direction="Horizontal", gap=12, height=48, align_items="Center")
    left = group(f"{name}Left", [t, d], direction="Vertical", gap=2, height=48, fill_portions=1)
    return group(f"{name}", [left], direction="Horizontal", gap=12, height=48, align_items="Center")


def build_plan_header():
    header = section_header("conVhpPlanHead", "Plan Header",
                            "Vedligeholdelsesplanens stamdata og tidsparametre.", "Step 1")

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
        item_display="ThisItem.Key & \" - \" & ThisItem.Name",
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
                  hint_text="\"Strategiplan henter cyklus fra strategiens pakker.\""),
        field_cell("conVhpCellStrategy", "Maintenance Strategy", drpStrategy,
                  container_w=CW, cols=PLAN_COLS,
                  hint_text="If(varVhpPlan.PlanType = \"Strategy\", \"Pakkerne vises i Strategy Packages nedenfor.\", \"Kun relevant for strategiplaner.\")"),
        field_cell("conVhpCellPlant", "Plant", drpPlant, required=True, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellStatus", "Status", drpStatus, required=True, container_w=CW, cols=PLAN_COLS),
    ], container_w=CW)
    row1 = row_n("conVhpPlanRow1", [
        field_cell("conVhpCellPlanText", "Plan Text", txtPlanText, required=True, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellSortField", "Sort Field", drpSortField, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellCycle", "Cycle", numCycle, required=True, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellUnit", "Unit", drpUnit, required=True, container_w=CW, cols=PLAN_COLS),
    ], container_w=CW)
    row2 = row_n("conVhpPlanRow2", [
        field_cell("conVhpCellCallHorizon", "Call Horizon", drpCallHorizon, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellSchedInd", "Scheduling Indicator", txtSchedInd, container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellFirstCallDay", "First Call Day", numFirstCallDay, required=True,
                  container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellFirstCallMonth", "First Call Month", numFirstCallMonth,
                  required=True, container_w=CW, cols=PLAN_COLS),
    ], container_w=CW)
    row3 = row_n("conVhpPlanRow3", [
        field_cell("conVhpCellFirstCallYear", "First Call Year", numFirstCallYear, required=True,
                  container_w=CW, cols=PLAN_COLS),
        field_cell("conVhpCellStatutorySortField", "Statutory Sort Field", txtStatutorySortField,
                  container_w=CW, cols=PLAN_COLS),
        group("conVhpPlanRow3SpacerA", [], height=62, width=col_width(CW, PLAN_COLS)),
        group("conVhpPlanRow3SpacerB", [], height=62, width=col_width(CW, PLAN_COLS)),
    ], container_w=CW)

    grid = group("conVhpPlanGrid", [row0, row1, row2, row3],
                 direction="Vertical", gap=16)

    planMeta = text_ctrl(
        "txtVhpPlanMeta",
        "If(varVhpPlanCommitted, \"Plan created \" & Text(varVhpPlanCreatedAt, \"dd-mm-yyyy hh:mm\"), \"\")",
        size=12, color=C_MUTED, height=18, wrap="false")
    optionsState = text_ctrl(
        "txtVhpPlanOptionsState",
        "\"Reference lists loaded: 14 option lists, \" & Text(CountRows(colVhpTasklists)) & \" tasklists, \" & Text(CountRows(colVhpStrategies)) & \" strategies, \" & Text(CountRows(colVhpFunctionalLocations)) & \" functional locations (offline data).\"",
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

    return card("conVhpPlanCard", [header, lockState, grid, footer])
