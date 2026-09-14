# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
                        C_PRIMARY, C_WHITE, C_NEUTRAL_BG, SHELL_W)
from build_helpers import text_ctrl, group, button, card

HERO_CW = f"({SHELL_W} - 32)"


def build_hero():
    eyebrow = text_ctrl("txtVhpEyebrow", "\"VH-PLAN\"", size=12, color=C_MUTED, weight="Semibold", height=20)
    title = text_ctrl("txtVhpTitle", "\"VH-plan\"", size=28, color=C_TITLE, weight="Semibold", height=42,
                      layout_min_width=220)
    subtitle = text_ctrl(
        "txtVhpSubtitle",
        "\"Opret planheader, laas planen, tilfoej items, bind tasklist pr. item, indberet via mailkladde.\"",
        size=14, color=C_MUTED, height=40, wrap="true")

    heroLeft = group("conVhpHeroLeft", [eyebrow, title, subtitle], direction="Vertical", gap=6,
                     align_items="Stretch", fill_portions=1,
                     width=f"If({HERO_CW} < 900, Parent.Width, Parent.Width - 250 - 16)")

    # ------------------------------------------------------------------
    # Validering. Reglerne er de samme som i oplaegget (docs/01) - S1, S3,
    # S4 og S5 gaelder kun strategiplaner.
    # ------------------------------------------------------------------
    btnValidate = button(
        "btnVhpValidate", "\"Validate\"",
        (
            "Set(varVhpPlanValidated, true);\n"
            "Set(varVhpItemValidated, true);\n"
            "With(\n"
            "    { isStrat: varVhpPlan.PlanType = \"Strategy\" },\n"
            "    With(\n"
            "        {\n"
            "            itemErr:\n"
            "                Concat(\n"
            "                    Filter(\n"
            "                        colVhpItems,\n"
            "                        IsBlank(ShortText) || IsBlank(MainWorkCenter) || IsBlank(ActivityType) || IsBlank(FunctionalLocation)\n"
            "                    ),\n"
            "                    \"Item \" & Text(ItemId) & \" (\" & Coalesce(ShortText, \"no short text\") & \"): missing required fields.\",\n"
            "                    Char(10)\n"
            "                ),\n"
            "            s1:\n"
            "                If(isStrat && IsBlank(varVhpPlan.Strategy),\n"
            "                    \"S1: Strategi skal vaelges paa en strategiplan.\", \"\"),\n"
            "            s3:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpItems, IsBlank(TasklistKey)),\n"
            "                        \"S3: Item \" & Text(ItemId) & \" mangler tasklist - pakkeallokeringen hoerer til arbejdsplanen.\",\n"
            "                        Char(10)\n"
            "                    ), \"\"),\n"
            "            s4:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpOperations, Len(Coalesce(PackagesKey, \";\")) <= 1),\n"
            "                        \"S4: Item \" & Text(ItemId) & \" operation \" & OperationNo &\n"
            "                        \" er ikke tildelt nogen pakke og ville aldrig blive udfoert.\",\n"
            "                        Char(10)\n"
            "                    ), \"\"),\n"
            "            s5:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(\n"
            "                            colVhpStrategyPackages As P,\n"
            "                            P.StrategyKey = varVhpPlan.Strategy &&\n"
            "                            CountRows(Filter(colVhpOperations, \";\" & Text(P.PackageNo) & \";\" in Coalesce(PackagesKey, \";\"))) = 0\n"
            "                        ),\n"
            "                        \"S5: Pakke \" & ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit &\n"
            "                        \") indeholder ingen operationer - planen vil kalde en tom ordre.\",\n"
            "                        Char(10)\n"
            "                    ), \"\")\n"
            "        },\n"
            "        Set(\n"
            "            varVhpLastValidationErrors,\n"
            "            Concat(\n"
            "                Filter(\n"
            "                    Table({ t: itemErr }, { t: s1 }, { t: s3 }, { t: s4 }, { t: s5 }),\n"
            "                    !IsBlank(t)\n"
            "                ),\n"
            "                t, Char(10)\n"
            "            )\n"
            "        )\n"
            "    )\n"
            ");\n"
            "Set(\n"
            "    varVhpRuntimeInfo,\n"
            "    \"Validated: \" & Text(CountRows(colVhpItems)) & \" item(s), \" &\n"
            "    Text(CountRows(colVhpOperations)) & \" operation line(s), \" &\n"
            "    Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid item(s).\" &\n"
            "    If(IsBlank(varVhpLastValidationErrors), \" No validation issues.\", \" See validation report.\")\n"
            ")"
        ),
        primary=True, width=110, height=36)

    btnExport = button(
        "btnVhpExport", "\"Export JSON\"",
        (
            "Set(\n"
            "    varVhpExportJson,\n"
            "    JSON(\n"
            "        {\n"
            "            plant: varVhpPlan.Plant,\n"
            "            planType: varVhpPlan.PlanType,\n"
            "            strategy: varVhpPlan.Strategy,\n"
            "            planText: varVhpPlan.PlanText,\n"
            "            cycle: varVhpPlan.Cycle,\n"
            "            unit: varVhpPlan.Unit,\n"
            "            packages:\n"
            "                ForAll(\n"
            "                    Sort(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy), PackageNo),\n"
            "                    { packageNo: PackageNo, shortCode: ShortCode, cycleLength: CycleLength,\n"
            "                      cycleUnit: CycleUnit, hierarchy: Hierarchy }\n"
            "                ),\n"
            "            items:\n"
            "                ForAll(\n"
            "                    Sort(colVhpItems, ItemId) As I,\n"
            "                    {\n"
            "                        itemId: I.ItemId, shortText: I.ShortText,\n"
            "                        functionalLocation: I.FunctionalLocation,\n"
            "                        mainWorkCenter: I.MainWorkCenter, activityType: I.ActivityType,\n"
            "                        tasklistKey: I.TasklistKey, status: I.Status,\n"
            "                        operations:\n"
            "                            ForAll(\n"
            "                                Sort(Filter(colVhpOperations, ItemId = I.ItemId), Value(OperationNo)) As OP,\n"
            "                                {\n"
            "                                    operationNo: OP.OperationNo,\n"
            "                                    shortText: OP.OperationShortText,\n"
            "                                    work: OP.WorkHours, duration: OP.DurationHours,\n"
            "                                    mainWorkCenter: OP.MainWorkCenter, vendor: OP.Vendor,\n"
            "                                    packages:\n"
            "                                        ForAll(\n"
            "                                            Sort(\n"
            "                                                Filter(\n"
            "                                                    colVhpStrategyPackages As P,\n"
            "                                                    P.StrategyKey = varVhpPlan.Strategy &&\n"
            "                                                    \";\" & Text(P.PackageNo) & \";\" in Coalesce(OP.PackagesKey, \";\")\n"
            "                                                ),\n"
            "                                                PackageNo\n"
            "                                            ),\n"
            "                                            { packageNo: PackageNo }\n"
            "                                        )\n"
            "                                }\n"
            "                            )\n"
            "                    }\n"
            "                )\n"
            "        },\n"
            "        JSONFormat.IndentFour\n"
            "    )\n"
            ");\n"
            "Set(varVhpRuntimeInfo, \"JSON exported: \" & Text(CountRows(colVhpItems)) & \" item(s), \" & Text(Len(varVhpExportJson)) & \" characters.\")"
        ),
        primary=False, width=130, height=36)

    actionsRow = group("conVhpHeroActionsRow", [btnValidate, btnExport], direction="Horizontal", gap=10,
                       height=36, justify="End", width=250, align_items="Center")
    heroActions = group("conVhpHeroActions", [actionsRow], direction="Vertical", gap=8, width=250,
                        align_items="End")

    heroGrid = group("conVhpHeroGrid", [heroLeft, heroActions], direction="Horizontal", gap=16,
                     height=f"If({HERO_CW} < 900, ({heroLeft.h}) + 16 + ({heroActions.h}), Max(({heroLeft.h}), ({heroActions.h})))",
                     wrap="true")

    step_defs = [
        ("txtVhpStep1", "\"1. Plan\"", "true"),
        ("txtVhpStep2", "\"2. Item\"", "varVhpPlanCommitted"),
        ("txtVhpStep3", "\"3. Tasklist\"", "varVhpPlanCommitted && CountRows(colVhpItems) > 0"),
        ("txtVhpStep4",
         "If(varVhpPlan.PlanType = \"Strategy\", \"4. Pakker\", \"4. Operations\")",
         "varVhpPlanCommitted && !IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId, TasklistKey))"),
        ("txtVhpStep5", "\"5. Dispatch\"",
         "varVhpPlanCommitted && CountRows(colVhpOperations) > 0"),
    ]
    steps = []
    for nm, lbl, active_formula in step_defs:
        steps.append(text_ctrl(
            nm, lbl, size=12, weight="Semibold", height=26, width=118, wrap="false",
            accessible=lbl,
            extra={
                "Align": "Align.Center",
                "AlignInContainer": "AlignInContainer.Center",
                "Color": f"If({active_formula}, {C_WHITE}, {C_MUTED})",
                "Fill": f"If({active_formula}, {C_PRIMARY}, {C_NEUTRAL_BG})",
                "PaddingLeft": "8", "PaddingRight": "8",
                "RadiusBottomLeft": "14", "RadiusBottomRight": "14",
                "RadiusTopLeft": "14", "RadiusTopRight": "14",
            }))
    # Fem chips a 118 px + 4 gaps a 8 = 622 px. Under det ombryder raekken
    # til to linjer, og hoejden skal foelge med.
    processStrip = group("conVhpProcessStrip", steps, direction="Horizontal", gap=8, wrap="true",
                         height=f"If({HERO_CW} < 622, 26 + 8 + 26, 26)")

    runtimeInfo = text_ctrl("txtVhpRuntimeInfo", "varVhpRuntimeInfo", size=13, color=C_MUTED, height=36,
                            wrap="true")

    legendStar = text_ctrl("txtVhpLegendStar", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                           height=20, width=10, wrap="false")
    legendText = text_ctrl("txtVhpLegendText", "\"Skal udfyldes\"", size=13, color=C_MUTED, height=20,
                           width=110, wrap="false")
    legend = group("conVhpLegend", [legendStar, legendText], direction="Horizontal", gap=3, height=20,
                   align_items="Center", width=123)

    return group("conVhpHero", [heroGrid, processStrip, runtimeInfo, legend], direction="Vertical", gap=12,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(16, 16, 16, 16))
