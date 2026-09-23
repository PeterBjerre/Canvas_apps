# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
                        C_PRIMARY, C_WHITE, C_NEUTRAL_BG, C_INFO_FG, SHELL_W)
from build_helpers import text_ctrl, group, button, card, theme_button
from design_tokens import theme_query
from layout_tokens import below, if_below, fits
import sp_config as cfg

HERO_CW = f"({SHELL_W} - 32)"

# Bredden af handlingsraekken i heroen, REGNET UD af de knapper, den
# indeholder - ikke skrevet af.
#
# Det er ikke pedanteri. Da temaknappen kom til, blev raekken 102 px
# bredere, mens venstresiden stadig reserverede den gamle plads. De to tal
# stod i hver sin ende af filen, og intet knyttede dem sammen. Nu goer det:
# tilfoejes en knap, foelger begge sider med.
HERO_BTNS = [("btnVhpTheme", 92), ("btnVhpBackToHub", 120),
             ("btnVhpValidate", 110), ("btnVhpExport", 130)]
HERO_BTN_GAP = 10
ACTIONS_W = (sum(w for _, w in HERO_BTNS)
             + HERO_BTN_GAP * (len(HERO_BTNS) - 1))
BW = dict(HERO_BTNS)   # knapperne bygges af DEN HER, ikke af egne tal

# Navnene skal vaere de kontroller, raekken faktisk indeholder. Er de det
# ikke, regner ACTIONS_W paa noget andet end det, der staar paa skaermen -
# og saa er hele koblingen ingenting vaerd. build_hero() efterproever det
# nedenfor, naar raekken er samlet.

# Procesindikatorens fem chips. Ombryder naar de ikke kan staa paa een
# linje - en CONTAINER-graense, ikke en enhedsklasse: fem chips fylder det
# samme, uanset om skaermen er en telefon eller en 4K-skaerm.
CHIP_W, CHIP_GAP, N_CHIPS = 118, 8, 5
CHIPS_W = CHIP_W * N_CHIPS + CHIP_GAP * (N_CHIPS - 1)


def build_hero():
    eyebrow = text_ctrl("txtVhpEyebrow", "\"VH-PLAN\"", size=12, color=C_MUTED, weight="Semibold", height=20)
    title = text_ctrl("txtVhpTitle", "\"VH-plan\"", size=28, color=C_TITLE, weight="Semibold", height=42,
                      layout_min_width=220)
    subtitle = text_ctrl(
        "txtVhpSubtitle",
        "\"Create the plan header, lock the plan, add items, link a task list per item, then report via an email draft.\"",
        size=14, color=C_MUTED, height=40, wrap="true")

    heroLeft = group("conVhpHeroLeft", [eyebrow, title, subtitle], direction="Vertical", gap=6,
                     align_items="Stretch", fill_portions=1,
                     # 352 = 250 + de 102 px, temaknappen og dens gap lagde
                     # til conVhpHeroActionsRow. Tallet skal foelge den
                     # raekkes bredde, ellers regner de to sider med den
                     # samme plads.
                     width=if_below("Desktop", "Parent.Width",
                                    f"Parent.Width - {ACTIONS_W} - 16"))

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

    row = [btnTheme, btnHub, btnValidate, btnExport]
    # ACTIONS_W er regnet af HERO_BTNS. Passer listen ikke paa raekken,
    # regner den paa noget andet end det, der tegnes.
    got = [(c.name, int(c.props["Width"])) for c in row]
    if got != HERO_BTNS:
        raise SystemExit("HERO_BTNS passer ikke paa handlingsraekken:\n"
                         "  HERO_BTNS: %s\n  raekken:   %s" % (HERO_BTNS, got))

    actionsRow = group("conVhpHeroActionsRow", row,
                       direction="Horizontal", gap=HERO_BTN_GAP,
                       height=36, justify="End", width=ACTIONS_W, align_items="Center")
    heroActions = group("conVhpHeroActions", [actionsRow], direction="Vertical", gap=8, width=ACTIONS_W,
                        align_items="End")

    heroGrid = group("conVhpHeroGrid", [heroLeft, heroActions], direction="Horizontal", gap=16,
                     height=if_below("Desktop",
                                     f"({heroLeft.h}) + 16 + ({heroActions.h})",
                                     f"Max(({heroLeft.h}), ({heroActions.h}))"),
                     wrap="true")

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
                         height=fits(HERO_CW, CHIPS_W, "26 + 8 + 26", "26"))

    runtimeInfo = text_ctrl("txtVhpRuntimeInfo", "varVhpRuntimeInfo", size=13, color=C_MUTED, height=36,
                            wrap="true")

    legendStar = text_ctrl("txtVhpLegendStar", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                           height=20, width=10, wrap="false")
    legendText = text_ctrl("txtVhpLegendText", "\"Required\"", size=13, color=C_MUTED, height=20,
                           width=110, wrap="false")
    # EEN knap slaar alle feltforklaringer til og fra. Foer havde hvert felt
    # sit eget i-ikon - 21 knapper for at vise 21 linjer er en knap for
    # meget pr. linje, og de fyldte selv i raekken af labels.
    #
    # Den staar i hero-kortet ved siden af stjerne-legenden, fordi det er
    # der man i forvejen kigger for at forstaa, hvordan skaermen laeses.
    btnHints = button(
        "btnVhpToggleHints",
        'If(IfError(varVhpShowHints, false), "Hide field help", "Show field help")',
        "Set(varVhpShowHints, !IfError(varVhpShowHints, false))",
        width=150, height=28)
    btnHints.props["Appearance"] = ("If(IfError(varVhpShowHints, false), "
                                    "ButtonAppearance.Primary, ButtonAppearance.Outline)")
    btnHints.props["BasePaletteColor"] = C_INFO_FG
    btnHints.props["Color"] = f"If(IfError(varVhpShowHints, false), {C_WHITE}, {C_INFO_FG})"
    btnHints.props["BorderColor"] = C_CARD_BORDER
    btnHints.props["BorderThickness"] = "1"
    btnHints.props["Size"] = "12"

    legend = group("conVhpLegend", [legendStar, legendText, btnHints], direction="Horizontal",
                   gap=3, height=28, align_items="Center", width=285)

    return group("conVhpHero", [heroGrid, processStrip, runtimeInfo, legend], direction="Vertical", gap=12,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(16, 16, 16, 16))
