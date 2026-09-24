# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
                        C_PRIMARY, C_WHITE, C_NEUTRAL_BG, C_INFO_FG, SHELL_W)
from build_helpers import text_ctrl, group, button, theme_button, top_bar
from design_tokens import theme_query
from layout_tokens import at_least
import sp_config as cfg

# Topbjaelken er ALT, der er tilbage af hero-kortet.
#
# Heroen var et kort oeverst i kroppen med beskrivelse, procestrin,
# statuslinje, "* Required" og "Show field help". Det er forenklet:
#
#   procestrin        -> under titlen i topbjaelken (i stedet for undertitlen)
#   Show field help   -> EEN Help-knap i topbjaelken. Den slaar baade
#   + de fire ? Help     feltforklaringerne og sektionernes hjaelpepaneler
#                        til og fra (varVhpShowHints).
#   * Required        -> Plan Header-kortet, ved siden af Step 1
#   beskrivelse       -> slettet
#   statuslinje       -> slettet (txtVhpRuntimeInfo)
BW = {"btnVhpHelp": 100, "btnVhpTheme": 92, "btnVhpBackToHub": 120,
      "btnVhpValidate": 110, "btnVhpExport": 130}
BAR_GAP = 10
NARROW_HIDE = ("btnVhpTheme", "btnVhpExport")

# De fem procestrin. Staar paa een linje under titlen, naar der er plads -
# ellers staar undertitlen der i stedet. Aldrig to linjer: bjaelken har en
# fast hoejde.
CHIP_W, CHIP_GAP, N_CHIPS = 118, 8, 5
CHIPS_W = N_CHIPS * CHIP_W + (N_CHIPS - 1) * CHIP_GAP      # 622


def _actions():
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
            "                    \"S1: A strategy must be chosen on a strategy plan.\", \"\"),\n"
            "            s3:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpItems, IsBlank(TasklistKey)),\n"
            "                        \"S3: Item \" & Text(ItemId) & \" has no task list - the package allocation belongs to the task list.\",\n"
            "                        Char(10)\n"
            "                    ), \"\"),\n"
            "            s4:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpOperations, Len(Coalesce(PackagesKey, \";\")) <= 1),\n"
            "                        \"S4: Item \" & Text(ItemId) & \" operation \" & OperationNo &\n"
            "                        \" has no package and would never be carried out.\",\n"
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
            "                        \"S5: Package \" & ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit &\n"
            "                        \") has no operations - the plan would call an empty order.\",\n"
            "                        Char(10)\n"
            "                    ), \"\")\n"
            ",\n"
            # --- Regler fra BIO_SAP_Fields.xlsx og "Den gode VH-plan" -------
            # R1: overskriften skal starte med vaerkskoden, saa planen kan
            # findes naar man ikke kan soege paa vaerk eller funktionsplads.
            "            r1:\n"
            "                If(\n"
            "                    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
            "                        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
            "                    \"R1: Plan Text should start with the plant code \" & varVhpPlan.Plant &\n"
            "                        \" - otherwise the plan cannot be found without searching by plant.\", \"\"),\n"
            # R2: sort field bruges kun ved lovpligtige eftersyn - men SKAL
            # udfyldes, saa snart et item er et.
            "            r2:\n"
            "                With(\n"
            "                    { n: CountRows(Filter(colVhpItems, StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))) },\n"
            "                    If(\n"
            "                        n > 0 && IsBlank(varVhpPlan.SortField),\n"
            "                        \"R2: Sort Field is required: \" & Text(n) &\n"
            "                            \" item(s) have activity type 110 or 115.\", \"\")),\n"
            # R3 er FJERNET. Den blokerede indsendelse, hvis et item med
            # activity type 110/115 ikke havde *SUP som arbejdscenter.
            # Peter har bekraeftet, at det ikke er rigtigt: lovpligtige
            # eftersyn sendes ikke altid til *SUP. Reglen blokerede altsaa
            # folk paa noget, der ikke er en regel, og den slags er vaerre
            # end ingen validering - den laerer folk at ignorere panelet.
            # Nummereringen R1, R2, R4, R5 staar urOErt, saa den fejl der
            # var, kan genkendes i docs/14 og i TEST-manuelt.md.
            # R4: revisionsopgaver kaldes 1/1, ellers rammer de ikke revisionen.
            "            r4:\n"
            "                With(\n"
            "                    { n: CountRows(Filter(colVhpItems, !IsBlank(Revision))) },\n"
            "                    If(\n"
            "                        n > 0 && (varVhpPlan.FirstCallDay <> 1 || varVhpPlan.FirstCallMonth <> 1),\n"
            "                        \"R4: \" & Text(n) & \" item(s) are marked as outage work. \" &\n"
            "                            \"First call must be 01/01, otherwise the task misses the outage.\", \"\")),\n"
            # R5: under 2 aars scheduling period virker den oekonomiske
            # simulering i BI-rapporten ikke.
            "            r5:\n"
            "                With(\n"
            "                    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },\n"
            "                    If(\n"
            "                        !IsBlank(varVhpPlan.CallHorizon) && m.SchedPeriod < 2,\n"
            "                        \"R5: Scheduling period must be at least 2 years because of \" &\n"
            "                            \"the cost simulation in the BI report.\", \"\"))\n"
            "        },\n"
            "        Set(\n"
            "            varVhpLastValidationErrors,\n"
            "            Concat(\n"
            "                Filter(\n"
            "                    Table(\n"
            "                        { t: itemErr }, { t: s1 }, { t: s3 }, { t: s4 }, { t: s5 },\n"
            "                        { t: r1 }, { t: r2 }, { t: r4 }, { t: r5 }\n"
            "                    ),\n"
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
        primary=True, width=BW["btnVhpValidate"], height=36)

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
        primary=False, width=BW["btnVhpExport"], height=36)

    # Tilbage til hubben. De to domaeneapps har den; VH-plan havde ingen vej
    # tilbage overhovedet - man skulle bruge browserens tilbageknap eller
    # kende URL'en.
    # Temaet foelger med tilbage. Uden det ville hubben skifte farve, fordi
    # brugeren gik retur - SaveData-lageret er isoleret pr. app-id.
    btnHub = button(
        "btnVhpBackToHub", "\"To the hub\"",
        f'Launch("{cfg.HUB_URL}" & {theme_query("?")}, {{ }}, LaunchTarget.Replace)',
        primary=False, width=BW["btnVhpBackToHub"], height=36)

    # Samme knap som i de tre andre apps - se build_helpers.theme_button.
    btnTheme = theme_button("btnVhpTheme", width=BW["btnVhpTheme"], height=36)

    # EEN hjaelpeknap. Foer var der fem: "Show field help" i heroen og en
    # "? Help" i hver af de fire sektioner. De slaar nu alle det samme til.
    on = "IfError(varVhpShowHints, false)"
    btnHelp = button(
        "btnVhpHelp", f'If({on}, "Hide help", "? Help")',
        f"Set(varVhpShowHints, !{on})",
        width=BW["btnVhpHelp"], height=36)
    btnHelp.props["Appearance"] = f"If({on}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
    btnHelp.props["BasePaletteColor"] = C_INFO_FG
    btnHelp.props["Color"] = f"If({on}, {C_WHITE}, {C_INFO_FG})"
    btnHelp.props["BorderColor"] = C_CARD_BORDER
    btnHelp.props["BorderThickness"] = "1"

    return [btnHelp, btnTheme, btnHub, btnValidate, btnExport]


def _steps():
    step_defs = [
        ("txtVhpStep1", "\"1. Plan\"", "true"),
        ("txtVhpStep2", "\"2. Item\"", "varVhpPlanCommitted"),
        ("txtVhpStep3", "\"3. Tasklist\"", "varVhpPlanCommitted && CountRows(colVhpItems) > 0"),
        ("txtVhpStep4",
         "If(varVhpPlan.PlanType = \"Strategy\", \"4. Packages\", \"4. Operations\")",
         "varVhpPlanCommitted && !IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId, TasklistKey))"),
        ("txtVhpStep5", "\"5. Dispatch\"",
         "varVhpPlanCommitted && CountRows(colVhpOperations) > 0"),
    ]
    steps = []
    for nm, lbl, active_formula in step_defs:
        steps.append(text_ctrl(
            nm, lbl, size=12, weight="Semibold", height=26, width=CHIP_W, wrap="false",
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
    return steps


def build_top_bar():
    """VH-planens topbjaelke - den samme som i de tre andre apps
    (build_helpers.top_bar), men med procestrinene under titlen."""
    actions = _actions()
    # Pladsen til venstre for knapperne - samme regnestykke som
    # gen_screen._resolve_grow, med de knapper, der er synlige.
    terms = []
    for a in actions:
        t = f"{a.props['Width']} + {BAR_GAP}"
        terms.append(f"If({at_least('Tablet')}, {t}, 0)" if a.name in NARROW_HIDE else t)
    room = f"({SHELL_W} - " + " - ".join(f"({t})" for t in terms) + " - 2)"
    chips_fit = f"{room} >= {CHIPS_W}"

    strip = group("conVhpProcessStrip", _steps(), direction="Horizontal", gap=CHIP_GAP,
                  height=26, width=CHIPS_W, align_items="Center", visible=chips_fit)
    fallback = text_ctrl("txtVhpSub", '"Maintenance plans for SAP PM"', size=13, color=C_MUTED,
                         height=26, wrap="false", visible=f"!({chips_fit})")
    sub = group("conVhpBarSub", [strip, fallback], direction="Horizontal", gap=0, height=26)
    return top_bar("Vhp", '"VH-plan"', None, actions, gap=BAR_GAP,
                   narrow_hide=NARROW_HIDE, sub=[sub])



