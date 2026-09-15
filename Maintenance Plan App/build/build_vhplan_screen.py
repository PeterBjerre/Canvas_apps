# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import Ctrl, render, render_screen, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, \
    C_REQUIRED, C_PRIMARY, C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_DISABLED_BG, C_DIVIDER, \
    C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG, C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT
from build_helpers import text_ctrl, group, button, text_input, number_input, dropdown, label_row, \
    field_cell, two_col_row, badge, OUT_DIR

# ===========================================================================
# HERO SECTION
# ===========================================================================

def build_hero():
    eyebrow = text_ctrl("txtVhpEyebrow", "\"VH-PLAN\"", size=12, color=C_MUTED, weight="Semibold", height=20)
    title = text_ctrl("txtVhpTitle", "\"VH-plan\"", size=28, color=C_TITLE, weight="Semibold", height=42,
                       layout_min_width=220)
    subtitle = text_ctrl(
        "txtVhpSubtitle",
        "\"Create the plan header, lock the plan, add items, link a task list per item, then report via an email draft.\"",
        size=14, color=C_MUTED, height=40, wrap="true")

    heroLeft = group("conVhpHeroLeft", [eyebrow, title, subtitle], direction="Vertical", gap=6, height=108,
                      align_items="Stretch", fill_portions=1)

    btnValidate = button(
        "btnVhpValidate", "\"Validate\"",
        (
            "Set(varVhpPlanValidated, true);\n"
            "Set(varVhpItemValidated, true);\n"
            "Set(\n"
            "    varVhpLastValidationErrors,\n"
            "    \"Plan: \" & Text(CountRows(Filter(colVhpPlanIssueList(), true))) & \" issue(s). \" &\n"
            "    \"Items: \" & Text(CountRows(colVhpItems)) & \" total, \" &\n"
            "    Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid.\"\n"
            ");\n"
            "Set(\n"
            "    varVhpRuntimeInfo,\n"
            "    \"Validated: \" & CountRows(colVhpItems) & \" item(s), \" &\n"
            "    CountRows(colVhpOperations) & \" operation line(s).\"\n"
            ")"
        ),
        primary=True, width=110, height=36)

    btnExport = button(
        "btnVhpExport", "\"Export JSON\"",
        (
            "Set(\n"
            "    varVhpExportJson,\n"
            "    \"{\" &\n"
            "    \"\"\"plant\"\":\"\"\" & varVhpPlan.Plant & \"\"\",\" &\n"
            "    \"\"\"planText\"\":\"\"\" & varVhpPlan.PlanText & \"\"\",\" &\n"
            "    \"\"\"items\"\":\" & Text(CountRows(colVhpItems)) & \",\" &\n"
            "    \"\"\"operations\"\":\" & Text(CountRows(colVhpOperations)) &\n"
            "    \"}\"\n"
            ");\n"
            "Set(varVhpRuntimeInfo, \"JSON exported: \" & CountRows(colVhpItems) & \" item(s), \" & Len(varVhpExportJson) & \" characters.\")"
        ),
        primary=False, width=130, height=36)

    actionsRow = group("conVhpHeroActionsRow", [btnValidate, btnExport], direction="Horizontal", gap=10,
                        height=36, justify="End")
    heroActions = group("conVhpHeroActions", [actionsRow], direction="Vertical", gap=8, height=36,
                         align_items="End", width="If(App.Width < 900, Parent.Width, 320)")

    heroGrid = group("conVhpHeroGrid", [heroLeft, heroActions],
                      direction="If(App.Width < 900, LayoutDirection.Vertical, LayoutDirection.Horizontal)".replace("If(App.Width < 900, LayoutDirection.Vertical, LayoutDirection.Horizontal)", "Horizontal"),
                      gap=16, height="If(App.Width < 900, 108 + 12 + 36, 108)", wrap="true")
    # NOTE: direction kept Horizontal with wrap=true so it stacks responsively without formula in enum slot.

    steps = []
    step_defs = [
        ("txtVhpStep1", "\"1. Plan\"", "true"),
        ("txtVhpStep2", "\"2. Item\"", "varVhpPlan.Committed"),
        ("txtVhpStep3", "\"3. Tasklist\"", "varVhpPlan.Committed && CountRows(colVhpItems) > 0"),
        ("txtVhpStep4", "\"4. Operations\"",
         "varVhpPlan.Committed && !IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId, TasklistKey))"),
        ("txtVhpStep5", "\"5. Dispatch\"",
         "varVhpPlan.Committed && CountRows(colVhpOperations) > 0"),
    ]
    for nm, lbl, active_formula in step_defs:
        steps.append(text_ctrl(
            nm, lbl, size=12, weight="Semibold", height=26, width=118, wrap="false",
            extra={
                "Align": "Align.Center",
                "AlignInContainer": "AlignInContainer.Center",
                "Color": f"If({active_formula}, {C_WHITE}, {C_MUTED})",
                "Fill": f"If({active_formula}, {C_PRIMARY}, {C_NEUTRAL_BG})",
                "PaddingLeft": "8", "PaddingRight": "8",
                "RadiusBottomLeft": "14", "RadiusBottomRight": "14",
                "RadiusTopLeft": "14", "RadiusTopRight": "14",
            }))
    processStrip = group("conVhpProcessStrip", steps, direction="Horizontal", gap=8, height=26, wrap="true")

    runtimeInfo = text_ctrl("txtVhpRuntimeInfo", "varVhpRuntimeInfo", size=13, color=C_MUTED, height=36, wrap="true")

    legendStar = text_ctrl("txtVhpLegendStar", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold", height=20,
                            width=10, wrap="false")
    legendText = text_ctrl("txtVhpLegendText", "\"Required\"", size=13, color=C_MUTED, height=20, width=110,
                            wrap="false")
    legend = group("conVhpLegend", [legendStar, legendText], direction="Horizontal", gap=3, height=20,
                   align_items="Center", width=110)

    hero = group(
        "conVhpHero", [heroGrid, processStrip, runtimeInfo, legend], direction="Vertical", gap=12,
        height="If(App.Width < 900, 108 + 12 + 36, 108) + 12 + 26 + 12 + 36 + 12 + 20 + 28",
        fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(16, 16, 16, 16))
    return hero


print("hero builder ready")
