# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_MUTED, C_REQUIRED, C_INFO_BG, SHELL_W, C_DISABLED_BG, C_DIVIDER,
                        C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG, C_NEUTRAL_BG)
import build_help as bh
import layout_tokens as lay
from build_helpers import (child_name, text_min_height, text_ctrl, group, button, text_input, number_input,
                           themed_dropdown, field_cell, col_width, badge, card, grow,
                           row_n, text_px, fit_button_width, ICON_W)

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_PLAN = "varVhpPlanValidated"


def section_footer(name, info, buttons, cw):
    """Sektionens fod (issue #192): teksten til venstre og knapperne til
    hoejre i een raekke fra Tablet og op. Paa en telefon ville knapperne
    kun efterlade et par tegn pr. linje til teksten, saa den blev klippet;
    der staar teksten i fuld bredde og knapperne under den, hoejrestillet.

    info: en lodret gruppe med fodens tekst (evt. med .vis).
    buttons: knapperne med fast bredde, i raekkefoelge.
    cw: kortets indholdsbredde.

    Hoejden er skrevet ud, saa kortet omkring foelger med."""
    narrow = lay.below("Tablet")
    btn_w = " + ".join(f"({b.props['Width']})" for b in buttons) + f" + {8 * (len(buttons) - 1)}"
    row = group(f"{name}Btns", buttons, direction="Horizontal", gap=8, height=36,
                align_items="Center", justify="End", width=btn_w)
    row.props["AlignInContainer"] = f"If({narrow}, AlignInContainer.End, AlignInContainer.Center)"
    info.props["Width"] = f"Max(0, If({narrow}, {cw}, {cw} - ({btn_w}) - 8 - 2))"
    info.props["LayoutMinWidth"] = "0"
    footer = group(name, [info, row], direction="Horizontal", gap=8, align_items="Center")
    footer.props["LayoutDirection"] = (f"If({narrow}, LayoutDirection.Vertical, "
                                       "LayoutDirection.Horizontal)")
    iv = f"({info.vis})" if info.vis else "true"
    h = f"If({narrow}, If({iv}, ({info.h}) + 8, 0) + 36, Max(If({iv}, {info.h}, 0), 36))"
    footer.props["Height"] = h
    footer.h = h
    return footer


def step_badge(name, step_label, valid_fx, attention_fx=None):
    """Sektionens badge (issue #123): "Step N", indtil sektionen er
    faerdig OG opfylder valideringen - saa "Valid" i ok-farverne. Samme
    badge og samme farver paa alle tre sektioner.

    valid_fx er den eksisterende validering (build_status: VhpPlanValid,
    VhpItemsValid, VhpOpsValid), aldrig blot "gemt".
    attention_fx: hvornaar der i stedet skal staa "Invalid" (fx et item,
    der er gemt som ugyldigt)."""
    text = (f'If({valid_fx}, "Valid", ' + (f'{attention_fx}, "Invalid", ' if attention_fx else "")
            + f'"{step_label}")')
    b = badge(name, text, width=72)
    # Self.Text: formlen bag teksten regnes een gang, ikke tre.
    b.props["Color"] = f'Switch(Self.Text, "Valid", {C_VALID_FG}, "Invalid", {C_INVALID_FG}, {C_MUTED})'
    b.props["Fill"] = f'Switch(Self.Text, "Valid", {C_VALID_BG}, "Invalid", {C_INVALID_BG}, {C_NEUTRAL_BG})'
    b.props["AccessibleLabel"] = (f'If(Self.Text = "Valid", "{step_label}: valid", '
                                  f'"{step_label}: " & If(Self.Text = "Invalid", "invalid", "not complete yet"))')
    return b


# Indholdsbredden i et kort: skaermens indholdsbredde minus kortets polstring.
PLAN_CW = f"({SHELL_W} - 36)"
# Save/Edit-knappens bredde.
PLAN_SAVE_W = fit_button_width("\"Save\"", min_w=96) + ICON_W

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


def section_header(name, title, step_label, extra_right=(), extra_left=(), valid_fx=None,
                   attention_fx=None):
    """Sektionsoverskrift: titlen til venstre (evt. med noget lige efter
    den, fx "* Required"), og et trin-badge til hoejre.

    valid_fx (issue #123): badget skifter fra "Step N" til "Valid", naar
    sektionen opfylder valideringen (step_badge).

    Beskrivelsen under titlen er fjernet (issue #54). Den gentog blot det,
    sektionen viser, og kostede en linje paa hvert kort."""
    t = text_ctrl(child_name("txt", name, "Title"), f"\"{title}\"", size=lay.SIZE_CARD_TITLE, weight="Semibold",
                  height=text_min_height(lay.SIZE_CARD_TITLE),
                  width=text_px(title, lay.SIZE_CARD_TITLE), wrap="false")
    t.props["LayoutMinWidth"] = t.props["Width"]

    right = list(extra_right)
    if step_label and valid_fx:
        right.append(step_badge(child_name("txt", name, "Badge"), step_label, valid_fx, attention_fx))
    elif step_label:
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
    header = section_header("conVhpPlanHead", "Plan Header", "Step 1", valid_fx="VhpPlanValid",
                            extra_left=[required_legend()])
    helpPanel = help_panel("conVhpPlanHelp", "plan")

    # Statusbanneret ("Plan is open for editing" / "Plan locked ...") er
    # fjernet (issue #54). At planen er laast, ses paa de graa felter og paa
    # knappen, der hedder Edit i stedet for Save.

    drpPlant = themed_dropdown("drpVhpPlant", "colVhpPlantCodes",
                               "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant).Value",
                               required_formula=REQ_PLAN, display_mode=DM_PLAN)
    # STATUS (issue #113, #137). En plan oprettes altid som New, og feltet
    # kan ikke aendres: det er altid laast (Disabled -> View i input_theme,
    # saa listen aldrig foldes ud). Change og Deleted (SharePoints valg i
    # MaintenanceItems.Status) staar stadig i Items til senere brug, men
    # kan ikke vaelges.
    # Default er New, naar planen ingen status har (ny plan). En gemt plan
    # beholder sin status: varVhpPlan.Status er det gemte (build_load).
    # ItemDisplayText er ThisItem.Value (themed_dropdown) - den maa ikke
    # laese variabler (issue #133): Studio afviser det, og listen blev tom
    # med kun et flueben (issue #137).
    drpStatus = themed_dropdown("drpVhpStatus", "colVhpPlanStatusOptions",
                         'Coalesce(varVhpPlan.Status, "New")',
                         display_mode="DisplayMode.Disabled")

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

    # RAEKKE-ORDEN (issue #142). Planhovedet er fire kolonner og to raekker:
    #   Raekke 1: Plan Type | Status | Plant | Plan Text
    #   Raekke 2: Sort Field | Cycle | Unit | First Call
    # Cycle, Unit og First Call er een planlaegningsgruppe og staar samlet i
    # raekke 2. Foer (issue #54, #113) blev felterne lagt i kolonne-orden.
    # Hver raekke er en row_n, saa felterne under braekpunktet stables i
    # netop denne laeseraekkefoelge - ogsaa tab-raekkefoelgen foelger den.
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

    row1 = row_n("conVhpPlanRow1", [
        cell("conVhpCellPlanType", "Plan Type", drpPlanType, "PlanType", True),
        cell("conVhpCellStatus", "Status", drpStatus, "Status", True),
        cell("conVhpCellPlant", "Plant", drpPlant, "Plant", True),
        cell("conVhpCellPlanText", "Plan Text", txtPlanText, "PlanText", True),
    ], container_w=CW)
    row2 = row_n("conVhpPlanRow2", [
        cell("conVhpCellSortField", "Sort Field", drpSortField, "SortField"),
        cell("conVhpCellCycle", "Cycle", numCycle, "Cycle", True),
        cell("conVhpCellUnit", "Unit", drpUnit, "Unit", True),
        cell("conVhpCellFirstCall", "First Call (dd / mm / yyyy)", firstCallRow,
             "FirstCall", True),
    ], container_w=CW)
    # Maintenance Strategy vises kun for plantypen Strategy. Den staar da i
    # sin egen raekke under de to faste raekker, i kolonne 1, saa de otte
    # felters orden og placering aldrig flytter sig. Gruppens hoejde
    # taeller kun synlige boern, saa sektionen vokser, naar feltet vises.
    grid = group("conVhpPlanGrid", [row1, row2, cellStrategy],
                 direction="Vertical", gap=10, align_items="Stretch")

    planMeta = text_ctrl(
        "txtVhpPlanMeta",
        f"If(varVhpPlanCommitted, \"Plan created \" & Text(varVhpPlanCreatedAt, \"{lay.DATETIME_FMT}\"), \"\")",
        size=12, color=C_MUTED, height=24, wrap="false")
    footerInfo = group("conVhpPlanFooterInfo", [planMeta], direction="Vertical",
                       gap=0, justify="Center")

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
            "            IsBlank(drpVhpPlanType.Selected.Key) ||\n"
            "            (isStrat && IsBlank(drpVhpStrategy.Selected.Key)) ||\n"
            "            IsBlank(Trim(inpVhpPlanText.Text)) || Len(Trim(inpVhpPlanText.Text)) > 40 ||\n"
            "            (!isStrat && (IsBlank(numVhpCycle.Value) || numVhpCycle.Value <= 0)) ||\n"
            "            (!isStrat && IsBlank(drpVhpUnit.Selected.Value)) ||\n"
            "            IsBlank(numVhpFirstCallDay.Value) || numVhpFirstCallDay.Value < 1 || numVhpFirstCallDay.Value > 31 ||\n"
            "            IsBlank(numVhpFirstCallMonth.Value) || numVhpFirstCallMonth.Value < 1 || numVhpFirstCallMonth.Value > 12 ||\n"
            "            IsBlank(numVhpFirstCallYear.Value) || numVhpFirstCallYear.Value < 2020 || numVhpFirstCallYear.Value > 2100 ||\n"
            # Dagen skal findes i maaneden (den gamle app: dage pr. maaned
            # og skudaar). Date(2027; 2; 31) giver 3. marts, og saa var
            # foerste kald stille og roligt flyttet.
            "            Month(Date(numVhpFirstCallYear.Value, numVhpFirstCallMonth.Value, numVhpFirstCallDay.Value)) <> numVhpFirstCallMonth.Value,\n"
            "            Notify(\"Plan contains issues. Fix plan fields before creating items.\", NotificationType.Warning),\n"
            "\n"
            # Vaerket FOER gemningen - se plantskiftet nedenfor.
            "            Set(varVhpPrevPlant, varVhpPlan.Plant);\n"
            "            Set(\n"
            "                varVhpPlan,\n"
            "                {\n"
            "                    Plant: drpVhpPlant.Selected.Value,\n"
            # Feltet er laast (issue #137): New, eller den gemte status.
            # Coalesce, saa en tom valgliste aldrig blokerer gemning.
            "                    Status: Coalesce(drpVhpStatus.Selected.Value, varVhpPlan.Status, \"New\"),\n"
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
    btnSave.props["Width"] = str(PLAN_SAVE_W)

    # ALTID FOLDET UD (issue #192): felterne, hjaelpepanelet og Reset staar
    # der i alle tilstande. Efter Save er felterne laast (graa, DM_PLAN), og
    # Edit laaser dem op igen.
    footer = section_footer("conVhpPlanFooter", footerInfo, [btnReset, btnSave], PLAN_CW)

    return card("conVhpPlanCard", [header, helpPanel, grid, footer], gap=10, pad_y=12)
