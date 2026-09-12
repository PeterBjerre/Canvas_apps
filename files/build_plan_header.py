# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE, \
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT
from build_helpers import text_ctrl, group, button, text_input, number_input, dropdown, label_row, \
    field_cell, two_col_row, badge

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_PLAN = "varVhpPlanValidated"


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
        size=13, color=f"If(varVhpPlanLocked, {C_INFO_FG}, {C_MUTED})", height=20, wrap="true",
        extra={"Fill": f"If(varVhpPlanLocked, {C_INFO_BG}, {C_NEUTRAL_BG})", "PaddingLeft": "10",
               "PaddingRight": "10", "PaddingTop": "4", "PaddingBottom": "4",
               "RadiusBottomLeft": "8", "RadiusBottomRight": "8", "RadiusTopLeft": "8", "RadiusTopRight": "8"})

    drpPlant = dropdown("drpVhpPlant", "colVhpPlantCodes", "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant)",
                         item_display="ThisItem.Value", required_formula=REQ_PLAN, display_mode=DM_PLAN)
    drpStatus = dropdown("drpVhpStatus", "colVhpPlanStatusOptions",
                          "LookUp(colVhpPlanStatusOptions, Value = varVhpPlan.Status)",
                          required_formula=REQ_PLAN, display_mode=DM_PLAN)
    txtPlanText = text_input("txtVhpPlanText", "varVhpPlan.PlanText", max_length=40,
                              required_formula=REQ_PLAN, display_mode=DM_PLAN)
    drpSortField = dropdown("drpVhpSortField", "colVhpSortFieldOptions",
                             "LookUp(colVhpSortFieldOptions, Value = varVhpPlan.SortField)",
                             display_mode=DM_PLAN)
    numCycle = number_input("numVhpCycle", "varVhpPlan.Cycle", min_v=1, required_formula=REQ_PLAN,
                             display_mode=DM_PLAN)
    drpUnit = dropdown("drpVhpUnit", "colVhpUnitOptions", "LookUp(colVhpUnitOptions, Value = varVhpPlan.Unit)",
                        required_formula=REQ_PLAN, display_mode=DM_PLAN)
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

    row1 = two_col_row("conVhpPlanRow1",
                        field_cell("conVhpCellPlant", "Plant", drpPlant, required=True),
                        field_cell("conVhpCellStatus", "Status", drpStatus, required=True))
    row2 = two_col_row("conVhpPlanRow2",
                        field_cell("conVhpCellPlanText", "Plan Text", txtPlanText, required=True),
                        field_cell("conVhpCellSortField", "Sort Field", drpSortField))
    row3 = two_col_row("conVhpPlanRow3",
                        field_cell("conVhpCellCycle", "Cycle", numCycle, required=True),
                        field_cell("conVhpCellUnit", "Unit", drpUnit, required=True))
    row4 = two_col_row("conVhpPlanRow4",
                        field_cell("conVhpCellCallHorizon", "Call Horizon", drpCallHorizon),
                        field_cell("conVhpCellSchedInd", "Scheduling Indicator", txtSchedInd))
    row5 = two_col_row("conVhpPlanRow5",
                        field_cell("conVhpCellFirstCallDay", "First Call Day", numFirstCallDay, required=True),
                        field_cell("conVhpCellFirstCallMonth", "First Call Month", numFirstCallMonth, required=True))
    row6 = two_col_row("conVhpPlanRow6",
                        field_cell("conVhpCellFirstCallYear", "First Call Year", numFirstCallYear, required=True),
                        field_cell("conVhpCellStatutorySortField", "Statutory Sort Field", txtStatutorySortField))

    grid = group("conVhpPlanGrid", [row1, row2, row3, row4, row5, row6], direction="Vertical", gap=16,
                 height="If(App.Width < 640, 6 * (2 * 62 + 20) + 5 * 16, 6 * 62 + 5 * 16)")

    planMeta = text_ctrl(
        "txtVhpPlanMeta",
        "If(varVhpPlanCommitted, \"Plan created \" & Text(varVhpPlanCreatedAt, \"dd-mm-yyyy hh:mm\"), \"\")",
        size=12, color=C_MUTED, height=18, wrap="false")
    optionsState = text_ctrl(
        "txtVhpPlanOptionsState",
        "\"Reference lists loaded: 13 option lists, \" & Text(CountRows(colVhpTasklists)) & \" tasklists, \" & Text(CountRows(colVhpFunctionalLocations)) & \" functional locations (offline data).\"",
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
            "    If(\n"
            "        IsBlank(drpVhpPlant.Selected.Value) ||\n"
            "        IsBlank(drpVhpStatus.Selected.Value) ||\n"
            "        IsBlank(Trim(txtVhpPlanText.Text)) || Len(Trim(txtVhpPlanText.Text)) > 40 ||\n"
            "        IsBlank(numVhpCycle.Value) || numVhpCycle.Value <= 0 ||\n"
            "        IsBlank(drpVhpUnit.Selected.Value) ||\n"
            "        IsBlank(numVhpFirstCallDay.Value) || numVhpFirstCallDay.Value < 1 || numVhpFirstCallDay.Value > 31 ||\n"
            "        IsBlank(numVhpFirstCallMonth.Value) || numVhpFirstCallMonth.Value < 1 || numVhpFirstCallMonth.Value > 12 ||\n"
            "        IsBlank(numVhpFirstCallYear.Value) || numVhpFirstCallYear.Value < 2020 || numVhpFirstCallYear.Value > 2100,\n"
            "        Set(varVhpRuntimeInfo, \"Plan contains issues. Fix plan fields before creating items.\"),\n"
            "\n"
            "        Set(\n"
            "            varVhpPlan,\n"
            "            {\n"
            "                Plant: drpVhpPlant.Selected.Value,\n"
            "                Status: drpVhpStatus.Selected.Value,\n"
            "                PlanText: Trim(txtVhpPlanText.Text),\n"
            "                SortField: drpVhpSortField.Selected.Value,\n"
            "                Cycle: numVhpCycle.Value,\n"
            "                Unit: drpVhpUnit.Selected.Value,\n"
            "                CallHorizon: drpVhpCallHorizon.Selected.Value,\n"
            "                SchedulingIndicator: Trim(txtVhpSchedInd.Text),\n"
            "                FirstCallDay: numVhpFirstCallDay.Value,\n"
            "                FirstCallMonth: numVhpFirstCallMonth.Value,\n"
            "                FirstCallYear: numVhpFirstCallYear.Value,\n"
            "                StatutorySortField: Trim(txtVhpStatutorySortField.Text)\n"
            "            }\n"
            "        );\n"
            "        Set(varVhpPlanCommitted, true);\n"
            "        Set(varVhpPlanLocked, true);\n"
            "        Set(varVhpPlanCreatedAt, Now());\n"
            "        Set(varVhpRuntimeInfo, \"Plan saved and locked: \" & drpVhpPlant.Selected.Value & \" \" & Trim(txtVhpPlanText.Text) & \".\")\n"
            "    )\n"
            ")"
        ),
        primary=True, width=140, height=36)

    footer = group("conVhpPlanFooter", [footerInfo, btnSave], direction="Horizontal", gap=16, height=40,
                   align_items="Center")

    card = group("conVhpPlanCard", [header, lockState, grid, footer], direction="Vertical", gap=14,
                 height=48 + 14 + 28 + 14 + (6 * 62 + 5 * 16) + 14 + 40 + 40,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(18, 18, 18, 18))
    return card
