# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_TRANSPARENT, C_MUTED, C_REQUIRED, C_INFO_BG, SHELL_W, C_DISABLED_BG, C_DIVIDER,
                        C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG, C_NEUTRAL_BG)
import build_help as bh
import layout_tokens as lay
from build_helpers import (child_name, text_min_height, text_ctrl, group, button, text_input, number_input,
                           themed_dropdown, field_cell, col_width, badge, card, grow,
                           row_n, text_px, fit_button_width, ICON_W)

DM_PLAN = "If(varVhpPlanLocked, DisplayMode.Disabled, DisplayMode.Edit)"
# Linjen vises, naar planen er gemt og laast - paa ALLE bredder (issue #123).
# Foer viste en telefon en "Plan details"-knap i stedet, fordi chipsene var
# for brede til een linje. Nu ombrydes de til flere raekker (summary_formula).
SUMMARY_VIS = "varVhpPlanLocked"
REQ_PLAN = "varVhpPlanValidated"

# Chipsenes maal (issue #136). En chip er 28 hoej med 2 px luft over og
# under, og raekkerne staar CHIP_PITCH fra hinanden - 8 px luft lodret som
# vandret. Bredden er et skoen: etiketten er 10 px versaler (ca. 7 px pr.
# tegn med bogstavafstanden), vaerdien 13 px halvfed - 8 px pr. tegn er
# rigeligt ogsaa til koder i versaler (FL, arbejdscentre). CHIP_PAD er
# polstring, kant og afstanden mellem etiket og vaerdi.
CHIP_H, CHIP_GAP, CHIP_PITCH = 32, 8, 36
CHIP_PAD, LABEL_PX, VALUE_PX = 34, 7, 8


def summary_formula(segs, max_w, bind=None):
    """Den sammenklappede sektions linje (issue #54, #103, #123, #136) som
    EEN navngiven formel: en post { Html, W, H }.

    segs: (etiket, vaerdi) - begge Power Fx-tekst. En tom vaerdi giver
    INGEN chip: ingen etiket uden vaerdi og intet tomt hul.
    max_w: den plads, linjen har. Chipsene laegges fra venstre og
    ombrydes til en ny raekke, naar den naeste ikke kan vaere der. En
    vaerdi, der alene er bredere end pladsen, afkortes med en ellipse i
    stedet for at blive klippet eller skaleret ned.
    bind: {navn: udtryk} - regnes een gang (fx det aktive item).

    Issue #136: linjen var et SVG-billede, og i appen stod der kun en
    tynd streg pr. chip - teksten og chippens flade blev aldrig vist. Nu
    er den HTML i en HtmlViewer (samme vej som operationstabellens
    overskrift og totaler), og raekkerne skrives ud her: chippens bredde
    og raekkeskiftene er de SAMME tal, som hoejden regnes af, saa kortet
    omkring altid passer til det, der staar. Alle tal er hele tal - et
    decimaltal ville blive skrevet med komma paa et dansk sprog.

    Formlen staar i App.Formulas, saa layoutet regnes een gang og deles af
    linjen og af hoejderne paa kortet omkring den (H). Hoejderne maa ikke
    laese kontrollens .Height (layout-tjekkets regel 1)."""
    from design_tokens import ref_hex
    esc = lambda e: f'Substitute(Substitute({e}, "&", "&amp;"), "<", "&lt;")'
    n = len(segs)
    rng = range(1, n + 1)
    lab = ", ".join(f"l{i}: {l}" for i, (l, _v) in enumerate(segs, 1))
    val = ", ".join(f"v{i}: {v}" for i, (_l, v) in enumerate(segs, 1))
    ell = "…"
    # Vaerdien, afkortet til pladsen (een tegnplads til ellipsen).
    disp = ",\n    ".join(
        f"d{i}: If(Len(v{i}) = 0, \"\", {CHIP_PAD} + Len(l{i}) * {LABEL_PX} + Len(v{i}) * {VALUE_PX} <= mw, v{i}, "
        f"Left(v{i}, Max(0, RoundDown((mw - {CHIP_PAD + VALUE_PX} - Len(l{i}) * {LABEL_PX}) / {VALUE_PX}, 0))) "
        f"& \"{ell}\")"
        for i in rng)
    wid = ", ".join(f"w{i}: If(Len(d{i}) = 0, 0, {CHIP_PAD} + Len(l{i}) * {LABEL_PX} + Len(d{i}) * {VALUE_PX})"
                    for i in rng)
    outer = dict(bind or {})
    outer["mw"] = f"RoundDown({max_w}, 0)"
    opens = ["With({ " + ", ".join(f"{k}: {v}" for k, v in outer.items()) + " },",
             f"With({{ {lab},\n    {val} }},",
             f"With({{ {disp} }},",
             f"With({{ {wid} }},"]
    # Placeringen: x og raekke r for chip i; c er der, hvor den naeste kan
    # starte. En tom chip (w = 0) flytter ingenting.
    for i in rng:
        if i == 1:
            opens.append(f"With({{ x1: 0, r1: 0, c1: If(w1 = 0, 0, w1 + {CHIP_GAP}) }},")
            continue
        pc, pr = f"c{i - 1}", f"r{i - 1}"
        wrap = f"w{i} > 0 && {pc} > 0 && {pc} + w{i} > mw"
        opens.append(f"With({{ x{i}: If({wrap}, 0, {pc}), r{i}: {pr} + If({wrap}, 1, 0) }},")
        opens.append(f"With({{ c{i}: If(w{i} = 0, x{i}, x{i} + w{i} + {CHIP_GAP}) }},")
    fill, line = ref_hex("state-neutral-bg"), ref_hex("border-default")
    mut, txt = ref_hex("text-muted"), ref_hex("text-primary")
    W = "Max(" + ", ".join(f"If(w{i} = 0, 0, x{i} + w{i})" for i in rng) + ", 1)"
    H = f"r{n} * {CHIP_PITCH} + {CHIP_H}"
    # Raekkerne er flex-raekker med faste chipbredder - de ombrydes ikke
    # selv; et raekkeskift staar, hvor formlen har lagt det (r stiger).
    style = (f'"<style>html,body{{margin:0;padding:0;overflow:hidden}}'
             f'.s{{padding:2px 0;font-family:Segoe UI,sans-serif}}'
             f'.r{{display:flex;height:28px;white-space:nowrap}}.r+.r{{margin-top:{CHIP_PITCH - 28}px}}'
             f'.c{{flex:none;box-sizing:border-box;height:28px;line-height:26px;padding:0 13px;'
             f'border:1px solid " & {line} & ";border-radius:14px;background:" & {fill} & ";'
             f'color:" & {txt} & ";font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis}}'
             f'.c+.c{{margin-left:{CHIP_GAP}px}}'
             f'.c b{{font-size:10px;font-weight:600;letter-spacing:.5px;margin-right:6px;color:" & {mut} & "}}'
             f'</style><div class=\'s\'><div class=\'r\'>"')
    parts = [style]
    for i in rng:
        brk = f'If(r{i} > r{i - 1}, "</div><div class=\'r\'>", "") & ' if i > 1 else ""
        parts.append(
            f'If(w{i} = 0, "", {brk}"<span class=\'c\' style=\'width:" & w{i} & "px\'><b>" & '
            f'{esc("l%d" % i)} & "</b>" & {esc("d%d" % i)} & "</span>")')
    parts.append('"</div></div>"')
    body = ("{\n    Html: " + " &\n        ".join(parts) + ",\n"
            f"    W: {W},\n    H: {H}\n}}")
    return "\n".join(opens) + "\n" + body + "\n" + ")" * len(opens)


def summary_chips(name, fx, visible):
    """HtmlViewer'en, der viser summary_formula'ens post fx (et navn i
    App.Formulas). Plan Header, Item Editor og Tasklist and Operations
    bruger den samme, saa de ser ens ud. h er fx.H: kortet omkring foelger
    linjens hoejde, naar den ombrydes."""
    return Ctrl(name, "HtmlViewer", props={
        "Fill": C_TRANSPARENT, "Height": f"{fx}.H", "HtmlText": f"{fx}.Html",
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Visible": visible, "Width": f"{fx}.W", "AlignInContainer": "AlignInContainer.Start",
    }, h=f"{fx}.H", vis=visible)


def summary_width(cw, edit_w):
    """Pladsen til linjen: kortets indholdsbredde minus Edit-knappen ved
    siden af - paa en telefon hele bredden, for der staar Edit under
    linjen (collapse_footer)."""
    return lay.if_below("Tablet", cw, f"{cw} - {edit_w + 8}")


def collapse_footer(footer, info, edit, locked):
    """Sektionens fod, naar den er klappet sammen (issue #123).

    Fra Tablet og op staar linjen til venstre og Edit til hoejre i samme
    raekke, og raekken er saa hoej som den hoejeste af dem. Paa en telefon
    ville Edit tage en tredjedel af bredden fra chipsene; der staar linjen
    i fuld bredde og Edit under den, stadig hoejrestillet. Hoejden er
    skrevet ud, saa kortet omkring foelger med - ogsaa naar Edit er skjult
    (View mode), saa der ikke staar et tomt hul under linjen."""
    stack = f"({lay.below('Tablet')} && {locked})"
    footer.props["LayoutDirection"] = (f"If({stack}, LayoutDirection.Vertical, "
                                       "LayoutDirection.Horizontal)")
    edit.props["AlignInContainer"] = (f"If({stack}, AlignInContainer.End, "
                                      "AlignInContainer.Center)")
    ev = f"({edit.vis})" if edit.vis else "true"
    h = (f"If({stack}, ({info.h}) + If({ev}, {footer.props['LayoutGap']} + 36, 0), "
         f"Max(({info.h}), 36))")
    footer.props["Height"] = h
    footer.h = h
    return footer


def step_badge(name, step_label, valid_fx, attention_fx=None):
    """Sektionens badge (issue #123): "Step N", indtil sektionen er
    faerdig OG opfylder valideringen - saa "Valid" i ok-farverne. Samme
    badge og samme farver paa alle tre sektioner.

    valid_fx er den eksisterende validering (build_status: VhpPlanValid,
    VhpItemsValid, VhpOpsValid), aldrig blot "gemt" eller "sammenklappet".
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


def plan_summary_segs():
    """Plan Headers linje: de gemte vaerdier, der kendetegner planen.
    Issue #136: kun vaerdier, der findes - en tom foerste kaldedato gav
    "//", og en manglende cyklus "Every  "; nu giver de ingen chip."""
    p = "varVhpPlan"
    first = (f'If(IsBlank({p}.FirstCallDay) || IsBlank({p}.FirstCallMonth) || IsBlank({p}.FirstCallYear), "", '
             f'Text({p}.FirstCallDay, "00") & "/" & Text({p}.FirstCallMonth, "00") & "/" & '
             f'Text({p}.FirstCallYear, "0"))')
    cycle = (f'If({IS_STRATEGY}, Coalesce({p}.Strategy, ""), '
             f'Coalesce({p}.Cycle, 0) <= 0 || IsBlank({p}.Unit), "", '
             f'"Every " & Text({p}.Cycle) & " " & {p}.Unit)')
    return [('"PLANT"', f'Coalesce({p}.Plant, "")'),
            ('"PLAN TEXT"', f'Coalesce({p}.PlanText, "")'),
            (f'If({IS_STRATEGY}, "STRATEGY", "CYCLE")', cycle), ('"FIRST CALL"', first),
            ('"STATUS"', f'Coalesce({p}.Status, "")'),
            ('"SORT FIELD"', f'Coalesce({p}.SortField, "")')]


def summary_formulas():
    """De tre linjers navngivne formler (generate_app_onstart.build_formulas)."""
    import build_items as bi
    import build_tasklist as bt
    return [
        ("VhpPlanSummary", summary_formula(plan_summary_segs(), summary_width(PLAN_CW, PLAN_SAVE_W)),
         "Plan Headers sammenklappede linje (issue #123): chips, bredde og hoejde."),
        ("VhpItemSummary", bi.item_summary_fx(),
         "Item Editorens sammenklappede linje for det valgte item (issue #123)."),
        ("VhpOpsSummary", bt.ops_summary_fx(),
         "Tasklist and Operations' sammenklappede linje for det valgte item (issue #123)."),
    ]


# Indholdsbredden i et kort: skaermens indholdsbredde minus kortets polstring.
PLAN_CW = f"({SHELL_W} - 36)"
# Save/Edit-knappens bredde - linjen har kortets bredde minus den.
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
        size=12, color=C_MUTED, height=24, wrap="false", visible="!varVhpPlanLocked")
    # Linjen (issue #123): chipsene ombrydes, og kortet foelger deres hoejde.
    summary = summary_chips("htmVhpPlanSummary", "VhpPlanSummary", SUMMARY_VIS)
    footerInfo = grow(group("conVhpPlanFooterInfo", [summary, planMeta], direction="Vertical",
                            gap=0, justify="Center"))

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

    # Hoejden er den hoejeste af linjen og knapperne: ombrydes chipsene,
    # vokser raekken med dem (issue #123).
    footer = collapse_footer(
        group("conVhpPlanFooter", [footerInfo, btnReset, btnSave], direction="Horizontal",
              gap=8, align_items="Center"),
        footerInfo, btnSave, "varVhpPlanLocked")

    # SAMLET SAMMEN, NAAR PLANEN ER GEMT. Felterne og hjaelpepanelet vises kun,
    # mens planen kan redigeres; derefter staar en linje med det vigtigste, og
    # Edit folder dem ud igen.
    OPEN_EDIT = "!varVhpPlanLocked"
    grid.props["Visible"] = OPEN_EDIT
    grid.vis = OPEN_EDIT
    helpPanel.vis = f"({OPEN_EDIT}) && IfError(varVhpShowHints, false)"
    helpPanel.props["Visible"] = helpPanel.vis
    btnReset.props["Visible"] = OPEN_EDIT
    btnReset.vis = OPEN_EDIT

    return card("conVhpPlanCard", [header, helpPanel, grid, footer], gap=10, pad_y=12)
