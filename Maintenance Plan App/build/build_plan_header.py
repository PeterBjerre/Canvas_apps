# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, row_height, C_MUTED, C_TITLE, C_REQUIRED, C_INFO_BG, C_DISABLED_BG, C_DIVIDER,
                        C_VALID_FG, C_INVALID_FG, C_NEUTRAL_BG, C_WARN_FG, C_WARN_BG,
                        C_BORDER_ERROR, C_CARD_BORDER)
import build_help as bh
import build_status as st
import layout_tokens as lay
import mobile
from build_helpers import (child_name, text_ctrl, group, button, text_input, number_field, num_value,
                           themed_dropdown, field_cell, col_width, card,
                           row_n, text_px, fit_button_width, ICON_W, date_picker, modern_badge)
# Sektionsoverskriften og dens trin-badge staar i build_helpers (issue #228),
# saa Materials kan bruge samme overskrift som Item Editor.
from build_helpers import section_header  # noqa: F401
from build_helpers import fluent, fluent_icon
from build_helpers import act_fx, act_mark, act_button, reset_click_fx, reset_confirm
from build_helpers import grow

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_PLAN = "varVhpPlanValidated"

# FIRST CALL MAA IKKE LIGGE FOER I DAG (issue #565). Today() - ikke en fast
# dato. Kun i redigering: en gemt plan med en gammel First call vises
# (View, eller laast efter Save) uden fejl og uden at datoen roeres. Laases
# planhovedet op med Edit, staar beskeden ved feltet, og Save afvises, til
# datoen er i dag eller senere. Submit afvises af reglen i build_status.
FIRST_CALL_MSG = "First call cannot be before today"
FIRST_CALL_PAST = ("(!IsBlank(dteVhpFirstCall.SelectedDate) && "
                   "dteVhpFirstCall.SelectedDate < Today())")
FIRST_CALL_ERR = f"(!varVhpViewOnly && !varVhpPlanLocked && {FIRST_CALL_PAST})"


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
    # TELEFONEN (issue #508): knapperne er 44 px hoeje og deler kortets fulde
    # bredde ligeligt mellem de synlige - foer var raekken summen af alle
    # tre bredder (307 px) og gik ud over et 288 px kort. Fra Tablet og op
    # uaendret.
    n_vis = " + ".join(f"If({b.vis}, 1, 0)" if b.vis else "1" for b in buttons)
    each = f"(({cw}) - 8 * (Max(1, {n_vis}) - 1)) / Max(1, {n_vis})"
    for b in buttons:
        mobile.touch(b)
        b.props["Width"] = lay.mobile_or(each, b.props["Width"])
        if "LayoutMinWidth" in b.props:
            b.props["LayoutMinWidth"] = lay.mobile_or("0", b.props["LayoutMinWidth"])
    row_h = lay.mobile_or(mobile.TOUCH, 36)
    btn_w = lay.mobile_or(cw, btn_w)
    row = group(f"{name}Btns", buttons, direction="Horizontal", gap=8, height=row_h,
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
    h = (f"If({narrow}, If({iv}, ({info.h}) + 8, 0) + {row_h}, "
         f"Max(If({iv}, {info.h}, 0), {row_h}))")
    footer.props["Height"] = h
    footer.h = h
    return footer


# Indholdsbredden i et kort: skaermens indholdsbredde minus kortets polstring.
# Paa en telefon er kortets polstring 12 (lay.CARD_INNER_W, issue #508).
PLAN_CW = lay.CARD_INNER_W
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


def mobile_head(header, short_title=None, hide=()):
    """Sektionsoverskriften paa en telefon (issue #508): 8 px mellem
    delene i stedet for 12, evt. en kortere titel, og dele, der kan
    undvaeres (hide), skjules. Titel, trin-badge og knapper skulle ellers
    bruge 300-410 px i et kort, der er 248-288 px bredt - og blev klippet.
    Fra Tablet og op er overskriften uaendret."""
    header.props["LayoutGap"] = lay.mobile_or(8, header.props.get("LayoutGap", "12"))
    t = header.children[0]
    if short_title:
        full = t.props["Text"]
        t.props["Text"] = lay.mobile_or(f'"{short_title}"', full)
        sw = text_px(short_title, lay.SIZE_CARD_TITLE)
        t.props["Width"] = lay.mobile_or(sw, t.props["Width"])
        t.props["LayoutMinWidth"] = t.props["Width"]
        # Skaermlaeseren faar stadig hele titlen.
        t.props["AccessibleLabel"] = full
    for c in hide:
        v = c.props.get("Visible")
        c.props["Visible"] = lay.mobile_or("false", v or "true")
        c.vis = c.props["Visible"]
    return header


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
# Telefonen (issue #508): plads til syv linjer broedtekst.
HELP_LINE_H_M = 18 + 7 * 16 + 6


def help_panel(name, section):
    """Foldet ud af ?-knappen. Afsnittene kommer fra MD_HelpText.

    Teksten kan dermed rettes af dem, der kender fagligheden, uden at
    nogen skal bygge appen. Se build_help.py."""
    v = help_var(section)
    # Paa en telefon er linjerne kortere, saa et afsnit fylder flere linjer:
    # hoejere raekker der (issue #508), ellers blev teksten klippet.
    line_h = lay.mobile_or(HELP_LINE_H_M, HELP_LINE_H)
    head = text_ctrl(child_name("txt", name, "H"), "ThisItem.Heading", size=13, weight="Semibold",
                     height=18, wrap="false",
                     visible='!IsBlank(ThisItem.Heading)')
    body = text_ctrl(child_name("txt", name, "B"), "ThisItem.Body", size=12, color=C_MUTED,
                     height=f"({line_h}) - 18 - 6", wrap="true")
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
        "TemplateSize": line_h,
        "Width": "Parent.Width",
        # Tom liste skal stadig fylde EEN raekke, ellers bliver panelet
        # et farvet baand uden indhold, som ingen kan forklare.
        "Height": f"Max(CountRows({bh.panel(section)}), 1) * ({line_h})",
    }, children=[tmpl],
        h=f"Max(CountRows({bh.panel(section)}), 1) * ({line_h})")
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


# Planhovedets Reset (issue #54): felterne tilbage til deres Default. Var
# planen gemt, laases den igen. Koeres fra bekraeftelsen (issue #450).
PLAN_RESET_FX = ("; ".join(f"Reset({c})" for c in PLAN_CONTROLS) + ";\n"
                 # Det gemte vaerk gaelder igen (issue #453).
                 f"Set({st.LIVE_PLANT_VAR}, \"\");\n"
                 "Set(varVhpPlanValidated, false);\n"
                 "If(varVhpPlanCommitted, Set(varVhpPlanLocked, true))")
PLAN_RESET_ASK = "varVhpPlanResetAsk"
# Er planhovedet aendret siden sidst gemt? Saettes af build_plan_header.
PLAN_DIRTY = [None]


def plan_reset_confirm():
    """Planhovedets Reset-bekraeftelse (issue #450) - efter build_plan_header."""
    return reset_confirm("VhpPlanReset", PLAN_RESET_ASK, PLAN_RESET_FX, PLAN_DIRTY[0],
                         "the plan header",
                         guard="!varVhpViewOnly && !varVhpPlanLocked")


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

# Resumeet ombrydes (issue #287). Hoejden regnes af tekstens laengde og
# bredden - som build_hero._lines_h. 7.5 px pr. tegn er rummeligt for 13 px
# Segoe UI, saa der hellere er en linje luft for meget, end at den sidste
# vaerdi bliver klippet.
#
# INGEN SHOW/HIDE (issue #548): chevronen yderst til hoejre i overskriften
# er det eneste tegn paa, at planhovedet kan foldes, og hele overskriften
# klapper ud og sammen (mobile.fold_head).
#
# RESUMEET STAAR I OVERSKRIFTEN (issue #559): fra Tablet og op lige efter
# "Plan header" paa samme linje - Total cost og chevronen bliver til
# hoejre. Den ekstra resume-raekke under overskriften (og dens hoejde) er
# vaek. Resumeet tager resten af raekken (grow) og ombrydes dér; raekken -
# og den klikbare overskrift - bliver saa hoej som resumeet. Paa en
# telefon (kortet er 248-288 px) er der kun ca. 90 px ved titlen, saa dér
# staar resumeet som foer paa sin egen linje under overskriften
# (txtVhpPlanFoldSummaryM) i kortets fulde bredde.
SUMMARY_LINE_H = 20          # 13 px * 1.5
SUMMARY_W = f"({PLAN_CW})"


def summary_height(text_ref, width_ref=SUMMARY_W):
    cpl = f"Max(12, RoundDown(({width_ref}) / 7.5, 0))"
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


# Planens samlede omkostning: alle items' operationer. Den er det,
# omkostningsgodkendelsen sammenligner med graensen (docs/32 §2 #7).
# build_tasklist importerer herfra. Blank (ingen operationer) og 0 giver
# begge false.
PLAN_COST = "Sum(colVhpOperations, Cost)"
FOLD_COST_ON = f"IfError({PLAN_COST} > 0, false)"
PLAN_COST_TEXT = '"Total cost: " & ' + lay.num_text(PLAN_COST) + ' & " DKK"'

# OVER OMKOSTNINGSGRAENSEN (docs/32, R2-082; issue #529). PLANENS sum over
# graensen fra AppSettings (sp_config: VhpCostThreshold). Kun information -
# godkendelsesflowet (COST-trinnet paa hele planen) regner selv.
COST_OVER_ON = f"IfError({PLAN_COST} > VhpCostThreshold, false)"
COST_OVER_TEXT = ('"Plan over " & ' + lay.num_text("VhpCostThreshold") +
                  ' & " DKK - needs cost approval"')


def plan_cost_badge(name, visible):
    """Planens Total cost-maerke (issue #529), i Plan header - udfoldet og
    foldet. Over graensen staar maerket i advarselsfarverne (state-warn-fg
    paa state-warn-bg - de farver, advarslen i Task list-kortet havde), og
    hele advarslen er maerkets Tooltip (hover og fokus) - ikke en ekstra
    linje. Under graensen: de normale farver og intet tooltip.

    ModernBadge har Tooltip efter Microsoft Learn ("Badge modern control in
    canvas apps", den opdaterede Badge; check_layout regel 16e tillader
    den). Skaermlaeseren faar advarslen i AccessibleLabel."""
    return modern_badge(
        name, PLAN_COST_TEXT,
        color=f"If({COST_OVER_ON}, {C_WARN_FG}, {C_TITLE})",
        fill=f"If({COST_OVER_ON}, {C_WARN_BG}, {C_NEUTRAL_BG})",
        width=f"Len({PLAN_COST_TEXT}) * 7 + 24", height=24, size=12,
        pad=(10, 10),
        accessible=(f'"Plan " & {PLAN_COST_TEXT} & '
                    f'If({COST_OVER_ON}, ". " & {COST_OVER_TEXT}, "")'),
        visible=visible,
        extra={"AlignInContainer": "AlignInContainer.Center",
               "Tooltip": f'If({COST_OVER_ON}, {COST_OVER_TEXT}, "")'})


def plan_head_summary(fold):
    """Resumeet I overskriften (issue #559): alle otte vaerdier lige efter
    titlen, paa samme linje som Total cost og chevronen. Det tager resten af
    raekken (grow) og ombrydes; hoejden foelger teksten og bredden. Udfoldet
    og paa en telefon er teksten tom, og kontrollen er kun det, der holder
    Total cost og chevronen ude til hoejre (den tomme gruppe, der stod der
    foer). Skaermlaeseren faar intet fra den tomme tekst."""
    on = f"!({lay.MOBILE}) && ({fold})"
    text = f'If({on}, "\u00b7  " & {PLAN_SUMMARY}, "")'
    summary = text_ctrl("txtVhpPlanFoldSummary", text, size=lay.SIZE_BODY, color=C_MUTED,
                        height=f"If(Len(Self.Text) = 0, {SUMMARY_LINE_H}, "
                               f"{summary_height('Self.Text', 'Self.Width')})",
                        wrap="true",
                        accessible=f'If({on}, "Plan header summary: " & {PLAN_SUMMARY}, "")',
                        extra={"AlignInContainer": "AlignInContainer.Center"})
    grow(summary)
    ref = "txtVhpPlanFoldSummary"
    summary.h = (f"If(Len({ref}.Text) = 0, {SUMMARY_LINE_H}, "
                 f"{summary_height(ref + '.Text', ref + '.Width')})")
    return summary


def plan_fold_summary(fold):
    """Telefonens foldede planhoved (UX-review M5, issue #287): alle otte
    vaerdier som een ombrudt tekst under overskriften, i kortets fulde
    bredde. Fra Tablet og op staar resumeet i overskriften
    (plan_head_summary, issue #559), saa denne linje er kun paa en telefon.
    Kortets hoejde foelger med (stack_height)."""
    summary = text_ctrl("txtVhpPlanFoldSummaryM", PLAN_SUMMARY, size=lay.SIZE_BODY, color=C_MUTED,
                        height=summary_height("Self.Text"), width=SUMMARY_W, wrap="true",
                        accessible='"Plan header summary: " & Self.Text',
                        extra={"LayoutMinWidth": "0"},
                        visible=f"{lay.MOBILE} && ({fold})")
    summary.h = summary_height("txtVhpPlanFoldSummaryM.Text")
    return summary


# PLANT STYRER MED DET SAMME (issue #453). Et nyt valg i Plant gaelder fra
# det oejeblik, det er valgt - ikke foerst efter Save i Plan header:
# varVhpLivePlant er det, build_status.VhpPlant laeser, og VhpPlant er det,
# arbejdscentre, tasklister, FL-soegningen og reglerne filtrerer paa.
#
# Items, der har vaerdier fra det gamle vaerk, MARKERES - de slettes ikke
# (build_status.ITEM_PLANT_CONFLICTS). Item Editorens felter nulstilles, saa
# de viser det nye vaerks liste; en dropdown skriver aldrig et tomt valg paa
# itemet (build_items.write_item), saa itemets vaerdi bliver staaende som
# en fejl, til brugeren vaelger en ny. Beskeden kun ved et RIGTIGT skift -
# en Reset eller en indlaest plan, der saetter samme vaerk, siger intet.
# FL-soegningens gamle svar hoerer til det gamle vaerk og ryddes.
_NP = "Self.Selected.Value"
_N_CONFLICTS = (f"CountRows(Filter(VhpSaveableItems, "
                f"{st.any_plant_conflict(p='np')}))")
PLANT_ONCHANGE = (
    "With(\n"
    f"    {{ prev: {st.PLANT}, np: {_NP} }},\n"
    f"    Set({st.LIVE_PLANT_VAR}, np);\n"
    "    If(\n"
    "        !IsBlank(prev) && !IsBlank(np) && Upper(prev) <> Upper(np),\n"
    "        Set(varVhpFlQuery, \"\"); Set(varVhpFlLast, \"\"); Set(varVhpFlMsg, \"\");\n"
    "        Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemTasklist); Reset(cmbVhpItemFL);\n"
    f"        With(\n            {{ n: {_N_CONFLICTS} }},\n"
    "            If(\n"
    "                n = 0,\n"
    "                Notify(\"Plant changed to \" & np & \".\", NotificationType.Information),\n"
    "                Notify(\n"
    "                    \"Plant changed to \" & np & \". \" & Text(n) & If(n = 1, \" item has\", \" items have\") &\n"
    "                        \" a work center, functional location or task list from another plant - marked to fix.\",\n"
    "                    NotificationType.Warning\n"
    "                )\n"
    "            )\n"
    "        )\n"
    "    )\n"
    ")"
)


def build_plan_header():
    # Foldet: planen er gemt (laast), og Show er ikke slaaet til.
    fold = f"varVhpPlanLocked && !IfError({SHOW_VAR}, false)"
    toggle_set = f"Set({SHOW_VAR}, !IfError({SHOW_VAR}, false))"
    # "* Required" staar lige efter titlen i venstre side. I hoejre side,
    # mellem titlen og trin-badget, blev den klippet (issue #54).
    legend = required_legend()
    legend.props["Visible"] = f"!({fold})"
    legend.vis = legend.props["Visible"]
    # PLANENS TOTAL COST (issue #529): hoejrestillet i overskriften - foldet
    # og udfoldet, nu i den SAMME overskrift (issue #548). Over graensen i
    # advarselsfarverne med advarslen som tooltip (plan_cost_badge).
    costHead = plan_cost_badge("bdgVhpPlanHeadCost", FOLD_COST_ON)
    # EEN OVERSKRIFT, FOLDET OG UDFOLDET (issue #548): flueben, titel, Total
    # cost og chevronen yderst til hoejre. Chevronen staar samme sted i
    # begge tilstande og skifter kun retning (ned = foldet, op = udfoldet).
    # Den er der kun, naar planhovedet KAN foldes (gemt og laast) - som
    # Show/Hide foer. Show/Hide-teksten er vaek.
    chev = mobile.chevron_toggle("btnVhpPlanFold", "Plan header", SHOW_VAR,
                                 open_expr=f"!({fold})", everywhere=True)
    chev.props["OnSelect"] = toggle_set
    chev.props["Visible"] = "varVhpPlanLocked"
    chev.vis = chev.props["Visible"]
    # INTET VALID-MAERKE (issue #548): det groenne flueben foran titlen er
    # valideringens eneste tegn - som i Task list and operations (#529).
    header = section_header("conVhpPlanHead", "Plan header", None,
                            extra_left=[legend], extra_right=[costHead, chev])
    # Telefonen: stjernerne ved felterne bliver; forklaringen "* Required"
    # skjules, saa titel og badge kan staa paa een linje (issue #508).
    # Total cost-maerket (op til ~200 px) er der heller ikke plads til ved
    # titlen og Valid i et kort paa 248-288 px - telefonen har det paa sin
    # egen linje lige under overskriften (bdgVhpPlanHeadCostPhone).
    mobile_head(header, hide=[legend, costHead])
    # Fluebenet lige foran titlen, KUN naar planhovedet er gyldigt (samme
    # validering som det tidligere Valid-maerke, VhpPlanValid) - samme sted,
    # foldet og udfoldet. Ugyldigt: intet ikon.
    ok = status_icon("icoVhpPlanHeadStatus", "VhpPlanValid", label_ok="Plan header: valid")
    ok.props["Visible"] = "IfError(VhpPlanValid, false)"
    ok.vis = ok.props["Visible"]
    ok.props["AlignInContainer"] = "AlignInContainer.Center"
    header.children.insert(0, ok)
    # Resumeet i overskriften (issue #559) tager den tomme gruppes plads -
    # lige efter titlen (og "* Required", der kun ses udfoldet).
    gaps = [k for k in header.children if k.name == "conVhpPlanHeadGap"]
    assert len(gaps) == 1
    header.children[header.children.index(gaps[0])] = plan_head_summary(fold)
    header.props["Height"] = str(row_height(header.children))
    header.h = header.props["Height"]
    # HELE OVERSKRIFTEN FOLDER (issue #548, mobile.fold_head) - kun naar
    # planhovedet kan foldes. Laget ligger over Total cost-maerket, saa
    # maerkets advarsel over graensen staar ogsaa i lagets tooltip.
    label = chev.props["AccessibleLabel"]
    head = mobile.fold_head("conVhpPlanHeadFold", header, toggle_set, label,
                            visible="varVhpPlanLocked",
                            tooltip=f"If({COST_OVER_ON}, {COST_OVER_TEXT}, {label})")
    costPhone = plan_cost_badge("bdgVhpPlanHeadCostPhone", lay.mobile_or(FOLD_COST_ON, "false"))
    costPhone.props["AlignInContainer"] = "AlignInContainer.Start"
    helpPanel = help_panel("conVhpPlanHelp", "plan")

    # Statusbanneret ("Plan is open for editing" / "Plan locked ...") er
    # fjernet (issue #54). At planen er laast, ses paa de graa felter og paa
    # knappen, der hedder Edit i stedet for Save.

    drpPlant = themed_dropdown("drpVhpPlant", "colVhpPlantCodes",
                               "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant).Value",
                               required_formula=REQ_PLAN, display_mode=DM_PLAN,
                               onchange=PLANT_ONCHANGE)
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
    # Kalenderen tilbyder ikke dage foer i dag (StartDate, dokumenteret for
    # den moderne datovaelger). Er den gemte dato aeldre, starter kalenderen
    # dér, saa den gemte dato stadig kan vises og aldrig ryddes; Save
    # afviser den saa (FIRST_CALL_ERR). Indtastes en dato i haanden,
    # fanger samme regel den.
    dteFirstCall.props["StartDate"] = (
        f"If(IsBlank({FIRST_CALL_DEFAULT}) || {FIRST_CALL_DEFAULT} >= Today(), "
        f"Today(), {FIRST_CALL_DEFAULT})")
    # Roed kant ved beskeden. View-kanten saettes her selv: gen_screen
    # springer kanter over, der allerede naevner varVhpViewOnly.
    dteFirstCall.props["BorderColor"] = (
        f"If(varVhpViewOnly, {C_CARD_BORDER}, "
        f"If({FIRST_CALL_ERR}, {C_BORDER_ERROR}, {dteFirstCall.props['BorderColor']}))")
    # Beskeden ved feltet - i alle tre layouts, under datovaelgeren.
    txtFirstCallErr = text_ctrl("txtVhpFirstCallErr", f'"{FIRST_CALL_MSG}"', size=12,
                                color=C_INVALID_FG, weight="Semibold", height=32,
                                wrap="true", visible=FIRST_CALL_ERR)

    # UGEMTE AENDRINGER I PLANHOVEDET (issue #450): et felt staar ikke paa
    # sin Default - den senest gemte plan (varVhpPlan). Hvert felt sammenlignes
    # med det, Reset() ville give det, saa "aendret" og Reset er enige.
    # Status er altid laast og taeller ikke med. Strategien taeller kun paa
    # en strategiplan.
    PLAN_DIRTY[0] = (
        "(\n"
        '    (drpVhpPlanType.Selected.Key & "") <> (varVhpPlan.PlanType & "") ||\n'
        '    (drpVhpPlanType.Selected.Key = "Strategy" && '
        '(drpVhpStrategy.Selected.Key & "") <> (varVhpPlan.Strategy & "")) ||\n'
        '    (drpVhpPlant.Selected.Value & "") <> (varVhpPlan.Plant & "") ||\n'
        f'    Trim(inpVhpPlanText.Text & "") <> Trim(({pt_default}) & "") ||\n'
        '    (drpVhpSortField.Selected.Value & "") <> (varVhpPlan.SortField & "") ||\n'
        '    Trim(inpVhpCycle.Text & "") <> If(IsBlank(varVhpPlan.Cycle), "", Text(varVhpPlan.Cycle)) ||\n'
        '    (drpVhpUnit.Selected.Value & "") <> (varVhpPlan.Unit & "") ||\n'
        '    (Text(dteVhpFirstCall.SelectedDate, "yyyymmdd") & "") <> '
        f'(Text({FIRST_CALL_DEFAULT}, "yyyymmdd") & "")\n'
        ")")

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

    def cell(name, label, ctrl, hint, required=False, error=None):
        # 44 px paa en telefon (issue #508); cellens hoejde regnes af feltet.
        mobile.touch(ctrl)
        return field_cell(name, label, ctrl, required=required, width=FC_CELL,
                          container_w=CW, fill_portions_formula="0",
                          hint_text=bh.hint(hint), hints_on=bh.HINTS_ON,
                          error_ctrl=error)


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
             "FirstCall", True, error=txtFirstCallErr),
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
            # Issue #565: First call foer i dag gemmes ikke.
            f"            {FIRST_CALL_PAST},\n"
            f"            Notify(\"{FIRST_CALL_MSG}.\", NotificationType.Warning),\n"
            "\n"
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
            # PLANT ER FAELLES KONTEKST (issue #54, #453). Plantskiftet er
            # allerede vist, da Plant blev valgt (PLANT_ONCHANGE) - nu er det
            # gemte vaerk det gaeldende, og det usavede valg ryddes.
            f"            Set({st.LIVE_PLANT_VAR}, \"\")\n"
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
    # Spoerger foerst, naar der er ugemte aendringer (issue #450).
    btnReset = button(
        "btnVhpPlanReset", "\"Reset\"",
        reset_click_fx(PLAN_RESET_ASK, PLAN_DIRTY[0], PLAN_RESET_FX),
        width=fit_button_width("\"Reset\""), height=36,
        display_mode="If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)",
        visible="!varVhpViewOnly")
    btnSave.props["Width"] = str(PLAN_SAVE_W)
    act_button(btnSave, ACT, "plan", text="Saving...", grow=False)

    planMeta.props["Visible"] = f"!({fold})"
    planMeta.vis = f"!({fold})"
    foldSummary = plan_fold_summary(fold)
    info = group("conVhpPlanFooterInfo", [planMeta], direction="Vertical", gap=0,
                 justify="Center")
    footer = section_footer("conVhpPlanFooter", info, [btnReset, btnSave], PLAN_CW)
    footer.props["Visible"] = f"!({fold})"
    footer.vis = footer.props["Visible"]

    # Foldet: overskriften og resumeet. Udfoldet: overskriften, hjaelp,
    # felter og fod som foer. Telefonens Total cost-linje staar i begge.
    for part in (helpPanel, grid):
        v = part.props.get("Visible")
        part.props["Visible"] = f"!({fold})" if not v else f"!({fold}) && ({v})"
        part.vis = part.props["Visible"]

    return card("conVhpPlanCard", [head, costPhone, helpPanel, grid, foldSummary, footer], gap=10,
                pad_y=12)
