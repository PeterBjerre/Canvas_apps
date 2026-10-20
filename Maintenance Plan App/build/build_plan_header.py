# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_MUTED, C_TITLE, C_REQUIRED, C_INFO_BG, SHELL_W, C_DISABLED_BG, C_DIVIDER,
                        C_VALID_FG, C_INVALID_FG, C_NEUTRAL_BG)
import icons
import build_help as bh
import layout_tokens as lay
from build_helpers import (child_name, text_ctrl, group, button, text_input, number_field, num_value,
                           themed_dropdown, field_cell, col_width, card, grow,
                           row_n, text_px, fit_button_width, ICON_W, date_picker, modern_badge)
# Sektionsoverskriften og dens trin-badge staar i build_helpers (issue #228),
# saa Materials kan bruge samme overskrift som Item Editor.
from build_helpers import section_header  # noqa: F401
from build_helpers import fluent, fluent_icon
from build_helpers import act_fx, act_mark, act_button

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_PLAN = "varVhpPlanValidated"


def section_footer(name, info, buttons, cw, keep_inline=None, drop_in_fold=None):
    """Sektionens fod (issue #192): teksten til venstre og knapperne til
    hoejre i een raekke fra Tablet og op. Paa en telefon ville knapperne
    kun efterlade et par tegn pr. linje til teksten, saa den blev klippet;
    der staar teksten i fuld bredde og knapperne under den, hoejrestillet.

    info: en lodret gruppe med fodens tekst (evt. med .vis).
    buttons: knapperne med fast bredde, i raekkefoelge.
    cw: kortets indholdsbredde.

    Hoejden er skrevet ud, saa kortet omkring foelger med."""
    narrow = lay.below("Tablet")
    if keep_inline:
        narrow = f"({narrow} && !({keep_inline}))"
    btn_w = " + ".join(f"({b.props['Width']})" for b in buttons) + f" + {8 * (len(buttons) - 1)}"
    if drop_in_fold is not None:
        btn_w = f"({btn_w}) - If({keep_inline}, {drop_in_fold.props['Width']} + 8, 0)"
    row = group(f"{name}Btns", buttons, direction="Horizontal", gap=8, height=36,
                align_items="Center", justify="End", width=btn_w)
    row.props["AlignInContainer"] = f"If({narrow}, AlignInContainer.End, AlignInContainer.Center)"
    info.props["Width"] = f"Max(0, If({narrow}, {cw}, {cw} - ({btn_w}) - 8 - 2))"
    info.props["LayoutMinWidth"] = "0"
    # Knapperne staar ALTID nederst til hoejre (issue #449). Naar sektionen
    # er gemt, skjules teksten til venstre; uden End rykkede Reset + Edit
    # saa ud til venstre kant. Med End er raekkens hoejre kant den samme,
    # om teksten er der eller ej, saa skift mellem Save og Edit flytter
    # intet. Paa en telefon (lodret) er hoejderne skrevet ud, saa End
    # flytter intet der.
    footer = group(name, [info, row], direction="Horizontal", gap=8, align_items="Center",
                   justify="End")
    footer.props["LayoutDirection"] = (f"If({narrow}, LayoutDirection.Vertical, "
                                       "LayoutDirection.Horizontal)")
    iv = f"({info.vis})" if info.vis else "true"
    h = f"If({narrow}, If({iv}, ({info.h}) + 8, 0) + 36, Max(If({iv}, {info.h}, 0), 36))"
    footer.props["Height"] = h
    footer.h = h
    return footer


# Indholdsbredden i et kort: skaermens indholdsbredde minus kortets polstring.
PLAN_CW = f"({SHELL_W} - 36)"
# Save/Edit-knappens bredde.
# Bredt nok til "Saving..." (issue #433), saa foden staar stille, mens der gemmes.
PLAN_SAVE_W = fit_button_width("\"Saving...\"", min_w=96) + ICON_W
# Skaermens handlingstilstand (build_hero.ACT) - Saving... i knappen.
ACT = "varVhpAct"

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
# Cyklussen som tal (UX-review T10: feltet er tekst uden spin-pile).
CYCLE = num_value("inpVhpCycle")


def help_var(section):
    """Alle fire hjaelpepaneler foelger den ENE Help-knap i topbjaelken
    (build_hero.imgVhpHelp) - den samme variabel som feltforklaringerne.
    Foer havde hver sektion sin egen "? Help" og sin egen variabel."""
    return "varVhpShowHints"


def required_legend():
    """ "* Required" - forklaringen paa stjernerne. Stod i hero-kortet; nu i
    Plan header, hvor de foerste stjerner staar."""
    star = text_ctrl("txtVhpLegendStar", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                     height=20, width=10, wrap="false")
    txt = text_ctrl("txtVhpLegendText", "\"Required\"", size=13, color=C_MUTED, height=20,
                    width=70, wrap="false")
    return group("conVhpLegend", [star, txt], direction="Horizontal", gap=3, height=20,
                 align_items="Center", width=83)


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
                 "inpVhpPlanText", "drpVhpSortField", "inpVhpCycle", "drpVhpUnit",
                 "dteVhpFirstCall")


# Den foldede linje (UX-review M5) - laest af felterne.
# ALLE OTTE FELTER (issue #287): Plan type, Status, Plant, Plan text, Sort
# field, Cycle, Unit og First call - i felternes raekkefoelge. Foer stod
# kun Plant, Plan type, cyklus og First call. Hvert felt har sin label foran
# vaerdien, saa linjen kan laeses uden at folde ud. Et tomt felt vises som
# "-" (som foer), saa de otte altid staar - og staar samme sted.
# Strategien staar efter Plan type paa en strategiplan (som foer); Cycle og
# Unit er da tomme (planen tager cyklussen fra strategien) og vises som "-".
SHOW_VAR = "varVhpPlanShow"
_SEP = '"  \u00b7  "'


def _part(label, value_fx, first=False):
    sep = "" if first else _SEP + " & "
    return f'{sep}"{label} " & {value_fx}'


PLAN_SUMMARY = " & ".join([
    _part("Plan type", 'Coalesce(drpVhpPlanType.Selected.Value, "-")', first=True)
    + ' & If(drpVhpPlanType.Selected.Key = "Strategy", '
    + _SEP + ' & "Strategy " & Coalesce(drpVhpStrategy.Selected.Value, "-"), "")',
    _part("Status", 'Coalesce(drpVhpStatus.Selected.Value, "-")'),
    _part("Plant", 'Coalesce(drpVhpPlant.Selected.Value, "-")'),
    _part("Plan text", 'Coalesce(Trim(inpVhpPlanText.Text), "-")'),
    _part("Sort field", 'Coalesce(drpVhpSortField.Selected.Value, "-")'),
    _part("Cycle", 'If(IsBlank(varVhpPlan.Cycle) || varVhpPlan.Cycle <= 0, "-", Text(varVhpPlan.Cycle))'),
    _part("Unit", 'Coalesce(drpVhpUnit.Selected.Value, "-")'),
    _part("First call", 'If(IsBlank(dteVhpFirstCall.SelectedDate), "-", '
          f'Text(dteVhpFirstCall.SelectedDate, "{lay.DATE_FMT}"))'),
])

# Resumeet staar paa sin egen linje under titlen og ombrydes (issue #287).
# Hoejden regnes af tekstens laengde og bredden - som build_hero._lines_h.
# 7.5 px pr. tegn er rummeligt for 13 px Segoe UI, saa der hellere er en
# linje luft for meget, end at den sidste vaerdi bliver klippet.
#
# SHOW STAAR VED RESUMEET (issue #292): Show-knappen (med chevron) staar
# hoejrestillet i SAMME raekke som resumeet, lodret centreret paa det - ikke
# oppe i titelraekken. Resumeet faar derfor kortets bredde minus knappen og
# raekkens gap, og hoejden regnes af den smallere bredde. Ingen ekstra
# raekke: er resumeet een linje, er raekken knappens hoejde (36).
# Under Tablet (telefon) bliver knappen i raekken; resumeet mister i stedet
# indrykningen under titlen, saa teksten faar de 30 px tilbage.
SUMMARY_INDENT = 30          # statusikonet (20) + raekkens gap (10)
SUMMARY_LINE_H = 20          # 13 px * 1.5
SHOW_W = fit_button_width('"Hide"') + ICON_W
SHOW_GAP = 8
SUMMARY_W = f"({PLAN_CW} - {SHOW_W} - {SHOW_GAP})"
SUMMARY_PAD = f"If({lay.below('Tablet')}, 0, {SUMMARY_INDENT})"


def summary_height(text_ref):
    cpl = f"Max(12, RoundDown(({SUMMARY_W} - {SUMMARY_PAD}) / 7.5, 0))"
    return (f"Max(1, RoundUp(Len({text_ref}) / {cpl}, 0)) * {SUMMARY_LINE_H} + 2")


CHIP_H = 24
CHIP_CHAR_W = 7          # 12 px Segoe UI, en lidt rummelig gennemsnitsbredde
CHIP_PAD = 10


def status_icon(name, ok_fx, size=20, label_ok="Complete", label_bad="Needs attention"):
    """Et statusikon (issue #139): ring med flueben, naar ok_fx er sand, ellers
    ring med udraabstegn - FORM og farve, ikke farve alene. Pynt ved siden af
    en tekst: ingen hover og ingen klik.

    Fluents CheckmarkCircle/ErrorCircle paa den moderne Icon-kontrol (issue
    #306) - samme former som stregikonerne STATUS_READY/STATUS_AWAITING."""
    return fluent_icon(name, 'If(%s, %s, %s)' % (ok_fx, fluent("ok"), fluent("awaiting")),
                       "If(%s, %s, %s)" % (ok_fx, C_VALID_FG, C_INVALID_FG),
                       'If(%s, "%s", "%s")' % (ok_fx, label_ok, label_bad), size=size)


def value_chip(name, label, value_fx, label_w=None, value_chars=None, visible=None):
    """En lille pille: dæmpet label og vaerdien ved siden af, paa en neutral
    flade med runde hjoerner, 12 px tekst. Bredden regnes af teksten:
    label_w er labelens bredde (tal eller udtryk), vaerdien Len() * tegnbredde
    - eller value_chars tegn, naar vaerdiens laengde er kendt."""
    if label_w is None:
        label_w = text_px(label.strip('"'), 12, False) + 2
    lab = text_ctrl(f"txt{name[3:]}Label", label, size=12, color=C_MUTED, height=CHIP_H, width=label_w,
                    wrap="false", extra={"AlignInContainer": "AlignInContainer.Center"})
    vw = (str(value_chars * CHIP_CHAR_W) if value_chars is not None
          else f"Len({value_fx}) * {CHIP_CHAR_W} + 2")
    val = text_ctrl(f"txt{name[3:]}Value", value_fx, size=12, weight="Semibold", height=CHIP_H, width=vw,
                    wrap="false", extra={"AlignInContainer": "AlignInContainer.Center"})
    w = f"{2 * CHIP_PAD + 4} + ({label_w}) + ({vw})"
    return group(name, [lab, val], direction="Horizontal", gap=4, height=CHIP_H, width=w,
                 align_items="Center", fill=C_NEUTRAL_BG, radius=CHIP_H // 2,
                 border_color=C_DIVIDER, border_thickness="1",
                 pad=(0, CHIP_PAD, 0, CHIP_PAD), visible=visible)


# Planens samlede omkostning: alle items' operationer (som build_tasklist.
# PLAN_COST - den kan ikke importeres herfra, build_tasklist importerer os).
# Blank (ingen operationer) og 0 giver begge false.
PLAN_COST = "Sum(colVhpOperations, Cost)"
FOLD_COST_ON = f"IfError({PLAN_COST} > 0, false)"

FOLD_H = 24                  # titelraekken: ikon og titel (Show staar nu ved resumeet)


def plan_fold_row(fold, toggle_set, show):
    """Det foldede planhoved (UX-review M5): flueben og titel i den
    oeverste linje, og under den alle otte vaerdier som een ombrudt tekst
    (issue #287) med Show hoejrestillet i samme raekke, lodret centreret
    paa teksten (issue #292). Vises kun, naar planen er gemt og foldet."""
    ok = status_icon("icoVhpPlanFoldStatus", "VhpPlanValid")
    title_w = text_px("Plan header", lay.SIZE_BODY + 1) + 2
    title = text_ctrl("txtVhpPlanFoldTitle", '"Plan header"', size=lay.SIZE_BODY + 1, weight="Semibold",
                      height=24, width=title_w, accessible='"Plan header"')
    grow(title, title_w)
    # Planens samlede omkostning (Peter 2026-10-19): omkostningsgodkendelsen
    # gaelder hele planen, saa summen af alle items' operationer staar
    # hoejrestillet i titelraekken, ogsaa naar planhovedet er foldet.
    # Et ModernBadge (som Valid-maerkerne): en gruppe med to tekster blev
    # tegnet som en tom pille i Studio (Peter 2026-10-19).
    #
    # KUN NAAR DER ER EN SUM (issue #421): uden operationer - eller med en
    # sum paa 0 - stod der et tomt maerke over Show-knappen. Nu er det
    # skjult, og en skjult kontrol fylder intet i en auto-layout-raekke.
    cost_text = ('"Total cost: " & ' + lay.num_text(PLAN_COST) + ' & " DKK"')
    cost = modern_badge("bdgVhpPlanFoldCost", cost_text, color=C_TITLE, fill=C_NEUTRAL_BG,
                        width=f"Len({cost_text}) * 7 + 24", height=24, size=12,
                        pad=(10, 10), accessible='"Plan " & ' + cost_text,
                        visible=FOLD_COST_ON,
                        extra={"AlignInContainer": "AlignInContainer.Center"})
    top = group("conVhpPlanFoldTop", [ok, title, cost], direction="Horizontal", gap=10,
                height=FOLD_H, align_items="Center")
    # Alle otte vaerdier (issue #287): rykket ind under titlen, ombrudt og
    # med den hoejde, teksten skal bruge - paa desktop, tablet og telefon.
    # Bredden er kortets minus Show (issue #292). Kortets hoejde foelger med
    # (stack_height), saa det, der staar under kortet, flytter sig.
    summary = text_ctrl("txtVhpPlanFoldSummary", PLAN_SUMMARY, size=lay.SIZE_BODY, color=C_MUTED,
                        height=summary_height("Self.Text"), width=SUMMARY_W, wrap="true",
                        accessible='"Plan header summary: " & Self.Text',
                        extra={"PaddingLeft": SUMMARY_PAD, "LayoutMinWidth": "0"})
    summary.h = summary_height("txtVhpPlanFoldSummary.Text")
    show.props["AlignInContainer"] = "AlignInContainer.Center"
    body = group("conVhpPlanFoldBody", [summary, show], direction="Horizontal", gap=SHOW_GAP,
                 align_items="Center", justify="SpaceBetween")
    return group("conVhpPlanFoldRow", [top, body], direction="Vertical", gap=2,
                 align_items="Stretch", visible=fold)


def build_plan_header():
    # "* Required" staar lige efter titlen i venstre side. I hoejre side,
    # mellem titlen og trin-badget, blev den klippet (issue #54).
    header = section_header("conVhpPlanHead", "Plan header", "Step 1", valid_fx="VhpPlanValid",
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
                         # Laast er View, ikke Disabled: Disabled tegnede et
                         # hvidt felt i moerkt tema (screenshots 2026-10-13).
                         display_mode="DisplayMode.View")

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
    # Listen viser noegle og beskrivelse; Selected.Value er SAP-noeglen.
    drpSortField = themed_dropdown("drpVhpSortField", "colVhpSortFieldOptions",
                            "LookUp(colVhpSortFieldOptions, Value = varVhpPlan.SortField).Name",
                            display_mode=DM_PLAN, display_col="Name")
    # Tal som tekst uden spin-pile (UX-review T10); enheden er dropdown'en
    # ved siden af. Mindst 1 tjekkes ved gem (se nedenfor).
    numCycle = number_field("inpVhpCycle", "varVhpPlan.Cycle", required_formula=REQ_CYCLE,
                            display_mode=DM_CYCLE, label='"Cycle"')
    drpUnit = themed_dropdown("drpVhpUnit", "colVhpUnitOptions", "LookUp(colVhpUnitOptions, Value = varVhpPlan.Unit).Value",
                       required_formula=REQ_CYCLE, display_mode=DM_CYCLE)
    # FIRST CALL ER EEN DATO (UX-review F3). Her stod tre talfelter (dag,
    # maaned, aar) med "dd / mm / yyyy". Nu er det appens datovaelger i
    # appens format. Planen og SharePoint er uaendrede: varVhpPlan beholder
    # FirstCallDay/-Month/-Year, og gemningen skriver stadig PlannedDate
    # af de tre (build_save.py) - kalenderen kan bare ikke give en dato,
    # der ikke findes (31. februar).
    FIRST_CALL_DEFAULT = ("If(IsBlank(varVhpPlan.FirstCallYear), Blank(), "
                          "Date(varVhpPlan.FirstCallYear, varVhpPlan.FirstCallMonth, varVhpPlan.FirstCallDay))")
    dteFirstCall = date_picker("dteVhpFirstCall", FIRST_CALL_DEFAULT,
                               required_formula=REQ_PLAN, display_mode=DM_PLAN,
                               label='"First call"')

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
                          hint_text=bh.hint(hint), hints_on=bh.HINTS_ON)


    cellStrategy = cell("conVhpCellStrategy", "Maintenance strategy", drpStrategy, "Strategy")
    cellStrategy.props["Visible"] = LIVE_IS_STRATEGY
    cellStrategy.vis = LIVE_IS_STRATEGY

    row1 = row_n("conVhpPlanRow1", [
        cell("conVhpCellPlanType", "Plan type", drpPlanType, "PlanType", True),
        cell("conVhpCellStatus", "Status", drpStatus, "Status", True),
        cell("conVhpCellPlant", "Plant", drpPlant, "Plant", True),
        cell("conVhpCellPlanText", "Plan text", txtPlanText, "PlanText", True),
    ], container_w=CW)
    row2 = row_n("conVhpPlanRow2", [
        cell("conVhpCellSortField", "Sort field", drpSortField, "SortField"),
        cell("conVhpCellCycle", "Cycle", numCycle, "Cycle", True),
        cell("conVhpCellUnit", "Unit", drpUnit, "Unit", True),
        cell("conVhpCellFirstCall", "First call", dteFirstCall,
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

    # SAVE/EDIT (issue #433): knappen hedder Save (foer Done), siger
    # "Saving..." mens den gemmer, og bliver til Edit, naar planhovedet er
    # gemt og laast. Samme moenster i Item og Task list and operations.
    # Gemningen er stadig lokal (beslutning 1a): kun Save draft skriver til
    # SharePoint, og trin 5 siger selv, naar der er noget at gemme.
    save_fx = (
            "Set(varVhpPlanValidated, true);\n"
            "    With(\n"
            "        { isStrat: drpVhpPlanType.Selected.Key = \"Strategy\" },\n"
            "        If(\n"
            "            IsBlank(drpVhpPlant.Selected.Value) ||\n"
            "            IsBlank(drpVhpPlanType.Selected.Key) ||\n"
            "            (isStrat && IsBlank(drpVhpStrategy.Selected.Key)) ||\n"
            "            IsBlank(Trim(inpVhpPlanText.Text)) || Len(Trim(inpVhpPlanText.Text)) > 40 ||\n"
            "            (!isStrat && (IsBlank(" + CYCLE + ") || " + CYCLE + " <= 0)) ||\n"
            "            (!isStrat && IsBlank(drpVhpUnit.Selected.Value)) ||\n"
            # Datovaelgeren giver kun datoer, der findes (F3) - kun aaret
            # skal ligge i det interval, SAP-opretteren godtager.
            "            IsBlank(dteVhpFirstCall.SelectedDate) ||\n"
            "            Year(dteVhpFirstCall.SelectedDate) < 2020 || Year(dteVhpFirstCall.SelectedDate) > 2100,\n"
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
            "                    Cycle: If(isStrat, 0, " + CYCLE + "),\n"
            "                    Unit: If(isStrat, \"\", drpVhpUnit.Selected.Value),\n"
            "                    FirstCallDay: Day(dteVhpFirstCall.SelectedDate),\n"
            "                    FirstCallMonth: Month(dteVhpFirstCall.SelectedDate),\n"
            "                    FirstCallYear: Year(dteVhpFirstCall.SelectedDate)\n"
            "                }\n"
            "            );\n"
            "            Set(varVhpPlanCommitted, true);\n"
            "            Set(varVhpPlanLocked, true);\n"
            f"            {act_mark(ACT, 'plan')};\n"
            "            Set(varVhpPlanShow, false);\n"
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
            "            )\n"
            "        )\n"
            ")"
    )
    btnSave = button(
        "btnVhpPlanSave", "If(varVhpPlanLocked, \"Edit\", \"Save\")",
        (
            "If(\n"
            "    varVhpPlanLocked,\n"
            "    Set(varVhpViewOnly, false);\n"
            "    Set(varVhpPlanLocked, false);\n"
            "    Notify(\"Plan unlocked for editing.\", NotificationType.Success),\n"
            "\n"
            + act_fx(ACT, "plan", save_fx) + "\n"
            ")"
        ),
        primary=True, width=140, height=36,
        icon="If(varVhpPlanLocked, \"Edit\", \"Checkmark\")",
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
        display_mode="If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)",
        visible="!varVhpViewOnly")
    btnSave.props["Width"] = str(PLAN_SAVE_W)
    act_button(btnSave, ACT, "plan", text="Saving...", grow=False)

    fold = f"varVhpPlanLocked && !IfError({SHOW_VAR}, false)"
    planMeta.props["Visible"] = f"!({fold})"
    planMeta.vis = f"!({fold})"
    # Show/Hide: i den foldede linje hedder den "Show" (btnVhpPlanShow, chevron
    # ned); i en udfoldet, gemt plan staar "Hide" i foden (chevron op).
    toggle_set = f"Set({SHOW_VAR}, !IfError({SHOW_VAR}, false))"
    # Show/Hide er een knap: "Show" i den foldede linje, "Hide" i en udfoldet,
    # gemt plan. Staar i samme raekke som Reset og Edit.
    hide = button("btnVhpPlanHide", f'If({fold}, "Show", "Hide")', toggle_set,
                  width=fit_button_width('"Hide"') + ICON_W, height=36,
                  accessible=f'If({fold}, "Show the plan header fields", "Hide the plan header fields")',
                  visible="varVhpPlanLocked",
                  icon=f'If({fold}, "{icons.FLUENT["expand"]}", "{icons.FLUENT["collapse"]}")')
    hide.props["LayoutMinWidth"] = hide.props["Width"]
    hide.props["Appearance"] = "ButtonAppearance.Subtle"
    hide.props["BorderThickness"] = "0"
    hide.props["Color"] = C_TITLE
    hide.props["Visible"] = f"varVhpPlanLocked && !({fold})"
    hide.vis = hide.props["Visible"]
    # Foldet: titel oeverst, resumeet under den og Show til hoejre for resumeet.
    show = button("btnVhpPlanShow", '"Show"', toggle_set,
                  width=SHOW_W, height=36,
                  accessible='"Show the plan header fields"',
                  icon=f'"{icons.FLUENT["expand"]}"')
    show.props["LayoutMinWidth"] = show.props["Width"]
    show.props["Appearance"] = "ButtonAppearance.Subtle"
    show.props["BorderThickness"] = "0"
    show.props["Color"] = C_TITLE
    foldCard = plan_fold_row(fold, toggle_set, show)
    info = group("conVhpPlanFooterInfo", [planMeta], direction="Vertical", gap=0,
                 justify="Center")
    footer = section_footer("conVhpPlanFooter", info, [hide, btnReset, btnSave], PLAN_CW)
    footer.props["Visible"] = f"!({fold})"
    footer.vis = footer.props["Visible"]

    # Foldet: kun foldRow (check, titel, nogletal som chips, Show). Udfoldet:
    # overskrift, hjaelp, felter og fod som foer.
    for part in (header, helpPanel, grid):
        v = part.props.get("Visible")
        part.props["Visible"] = f"!({fold})" if not v else f"!({fold}) && ({v})"
        part.vis = part.props["Visible"]

    return card("conVhpPlanCard", [header, helpPanel, grid, foldCard, footer], gap=10,
                pad_y=12)
