# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, SHELL_W, C_PRIMARY, C_CARD_BORDER
from build_helpers import (group, fit_button_width, text_ctrl, text_px,
                           flow_row, page_icon, PAGE_ICON, ICON_W)
from layout_tokens import if_below, at_least
from design_tokens import ref_hex
from build_items import FL_CODE

# Topbjaelken er ALT, der er tilbage af hero-kortet.
#
# Heroen var et kort oeverst i kroppen med beskrivelse, procestrin,
# statuslinje, "* Required" og "Show field help". Det er forenklet:
#
#   procestrin        -> trinindikatoren under titlen (stepper)
#   Show field help   -> EEN Help-kontakt i sidebaren. Den slaar baade
#   + de fire ? Help     feltforklaringerne og sektionernes hjaelpepaneler
#                        til og fra (varVhpShowHints).
#   * Required        -> Plan Header-kortet, lige efter titlen
#   beskrivelse       -> slettet
#   statuslinje       -> slettet (txtVhpRuntimeInfo)
#
# Validate og Dispatch and Control er fjernet (issue #54). Reglerne er de
# samme og ligger i VhpValidationErrors (build_status.py); Submit er graa,
# indtil de er opfyldt. Save draft og Submit staar her i bjaelken, for
# enden af progressbaren.

# EEN hjaelpekontakt. Foer var der fem: "Show field help" i heroen og en
# "? Help" i hver af de fire sektioner. De slaar nu alle det samme til.
# Den staar i sidebarens fod ved temakontakten (tools/side_nav.py) - se
# assemble_screen.py.
HELP_ON = "IfError(varVhpShowHints, false)"
HELP_ACTION = f"Set(varVhpShowHints, !{HELP_ON})"


# ---------------------------------------------------------------------------
# Progressbaren
# ---------------------------------------------------------------------------
# Fem trin og Submit (issue #54):
#
#   (1)---(2)---(3)---(4)---(5)  [ Submit ]
#   Plan  Item  Task  Ops   Save
#
# Dispatch er fjernet - Dispatch and Control-sektionen findes ikke laengere.
#
# Hvert trin er sit EGET billede og kan klikkes: det flytter fokus til
# sektionen (SetFocus paa en knap i den, saa skaermen scroller derhen - der
# findes ingen "scroll til" i canvas apps). Tasklist- og Operations-trinnet
# vaelger ogsaa den rigtige fane.
#
# GROENT = faerdigt OG gemt. Betingelserne er navngivne formler
# (build_status.py), saa de regnes om, hver gang data aendres. Items har een
# betingelse mere, som kun skaermen kan se: usavede aendringer i Item
# Editoren (ITEM_DIRTY). Aktuelt trin = det foerste, der ikke er faerdigt.

# Item Editoren er aendret siden sidste Save. "& \"\"" goer blank til tom
# tekst paa begge sider, saa et tomt felt og en tom kolonne er ens.
ITEM_DIRTY = (
    "With(\n"
    "    { it: LookUp(colVhpItems, ItemId = varVhpActiveItemId) },\n"
    "    !IsBlank(varVhpActiveItemId) && (\n"
    "        Trim(txtVhpItemShortText.Text & \"\") <> Trim(it.ShortText & \"\") ||\n"
    "        (drpVhpItemMainWorkCenter.Selected.Value & \"\") <> (it.MainWorkCenter & \"\") ||\n"
    "        (drpVhpItemActivityType.Selected.Value & \"\") <> (it.ActivityType & \"\") ||\n"
    "        tglVhpItemRevision.Value <> !IsBlank(it.Revision) ||\n"
    f"        ({FL_CODE} & \"\") <> (it.FunctionalLocation & \"\") ||\n"
    "        Trim(txtVhpItemInitials.Text & \"\") <> Trim(it.Initials & \"\")\n"
    "    )\n"
    ")"
)

IS_STRAT = 'varVhpPlan.PlanType = "Strategy"'

# (label, faerdig, klik)
#
# KLIK = FREMHAEV, IKKE SETFOCUS (issue #59). SetFocus kan ikke naa en
# kontrol i en container, og alt paa skaermen staar i containere - compile
# afviste alle fem. Canvas apps kan heller ikke scrolle en container fra en
# formel. Et klik saetter derfor varVhpFocusStep, og sektionen, trinnet
# hoerer til, faar en tyk kant i primaerfarven (focus_border nedenfor).
# Tasklist- og Operations-trinnet vaelger ogsaa den rigtige fane.
STEPS = [
    ('"Plan"', "VhpStepPlanDone", "Set(varVhpFocusStep, 1)"),
    ('"Item"', f"VhpStepItemDone && !({ITEM_DIRTY})", "Set(varVhpFocusStep, 2)"),
    ('"Task list"', "VhpStepTasklistDone",
     'Set(varVhpOpsTab, "ops");\nSet(varVhpFocusStep, 3)'),
    (f'If({IS_STRAT}, "Packages", "Operations")', "VhpStepOpsDone",
     f'Set(varVhpOpsTab, If({IS_STRAT}, "pkg", "ops"));\nSet(varVhpFocusStep, 4)'),
    ('"Save"', f"VhpStepSaveDone && varVhpPlanLocked && !({ITEM_DIRTY})",
     "Set(varVhpFocusStep, 5)"),
]


def focus_border(ctrl, steps, normal):
    """Kanten paa en sektion, der hoerer til trinene i steps: tyk og i
    primaerfarven, naar et af dem er klikket i progressbaren."""
    on = " || ".join(f"varVhpFocusStep = {n}" for n in steps)
    on = f"IfError({on}, false)"
    ctrl.props["BorderColor"] = f"If({on}, {C_PRIMARY}, {normal})"
    ctrl.props["BorderThickness"] = f"If({on}, 2, 1)"
    return ctrl


STEP_W, STEP_H, R = 120, 64, 13
# Et trin maa ikke blive smallere end det her - saa kan navnet ikke laeses.
# Er der ikke plads til fem af dem mellem titlen og knapperne, stables
# bjaelken (issue #73): titel, trin i fuld bredde, knapper.
STEP_MIN = 88

# Submit er aktiv, naar planen kan indsendes - og intet i Item Editoren
# venter paa at blive gemt.
CAN_SUBMIT = f"VhpCanSubmit && !({ITEM_DIRTY})"


# { d1: ..., d5: ... } - trinenes status, som hvert billede laeser.
_STATE = "{ " + ",\n      ".join("d%d: %s" % (i + 1, d) for i, (_l, d, _a) in enumerate(STEPS)) + " }"


def _hx(name):
    """En farvetoken midt i en SVG-streng."""
    return '" & %s & "' % ref_hex(name)


def _step_image(i, label, done, prev_done, current, action, width):
    """Eet trin: cirklen, dets navn og de to halve streger ud til naboerne.

    Stregen til venstre er faerdig, naar det FORRIGE trin er faerdigt,
    stregen til hoejre, naar DETTE er. Saa moedes de to halvdele midt
    imellem, som da trinene var eet billede.

    ANIMERET, MEN STILLE (issue #73)
    --------------------------------
    - Den faerdige streg TEGNES frem (stroke-dashoffset) med en svag
      gradient i ok-farven - venstre halvdel foerst, saa hoejre, saa
      fremdriften loeber fra trin til trin.
    - Det aktive trin har en ring, der langsomt pulserer.
    - Tjekmaerket tegnes frem, naar et trin bliver faerdigt.
    - Alt slaas fra under prefers-reduced-motion.
    Animationen er CSS inde i SVG'en - Image-kontrollen tegner den som et
    billede i browseren, saa der er ingen timer og ingen tilstand i appen.

    Etiketten staar lige under sin cirkel, midt paa trinets bredde, og
    billedet er hoejt nok til den (STEP_H) - den kan ikke skjules af
    sektionen nedenunder."""
    n = len(STEPS)
    cx, cy = STEP_W // 2, R + 6
    grey = ref_hex("text-muted")
    text = ref_hex("text-primary")
    info = ref_hex("state-info-fg")
    surface = _hx("bg-surface")
    okc = _hx("state-ok-fg")
    infoc = _hx("state-info-fg")
    font = "font-family='Segoe UI, sans-serif' text-anchor='middle'"
    css = ("<style>"
           ".d{stroke-dasharray:80;stroke-dashoffset:80;"
           "animation:draw .6s ease-out forwards}"
           ".r{animation-delay:.3s}"
           ".c{stroke-dasharray:20;stroke-dashoffset:20;"
           "animation:draw .35s .15s ease-out forwards}"
           ".p{transform-origin:center;transform-box:fill-box;"
           "animation:pulse 1.8s ease-in-out infinite}"
           "@keyframes draw{to{stroke-dashoffset:0}}"
           "@keyframes pulse{0%,100%{opacity:.35;transform:scale(.92)}"
           "50%{opacity:.9;transform:scale(1.06)}}"
           "@media (prefers-reduced-motion:reduce){.d,.c{animation:none;"
           "stroke-dashoffset:0}.p{animation:none;opacity:.7}}"
           "</style>")
    grad = ("<defs><linearGradient id='g' x1='0' x2='1' y1='0' y2='0'>"
            f"<stop offset='0' stop-color='{okc}' stop-opacity='.75'/>"
            f"<stop offset='1' stop-color='{okc}'/></linearGradient></defs>")
    fx = ['"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'%d\' height=\'%d\' '
          'viewBox=\'0 0 %d %d\'>%s%s"' % (STEP_W, STEP_H, STEP_W, STEP_H, css, grad)]

    def seg(x1, x2, is_done, cls):
        # Sporet ligger altid under; den faerdige streg tegnes oven paa.
        track = (f"<line x1='{x1}' y1='{cy}' x2='{x2}' y2='{cy}' stroke-width='4' "
                 f"stroke-linecap='round' stroke='{_hx('border-default')}'/>")
        fill = (f"<line class='d {cls}' x1='{x1}' y1='{cy}' x2='{x2}' y2='{cy}' "
                f"stroke-width='4' stroke-linecap='round' stroke='url(#g)'/>")
        return '"%s" & If(%s, "%s", "")' % (track, is_done, fill)

    if i > 0:
        fx.append(seg(0, cx - R - 5, prev_done, "l"))
    if i < n - 1:
        fx.append(seg(cx + R + 5, STEP_W, done, "r"))
    check = (f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='{okc}'/>"
             f"<path class='c' d='M{cx - 5} {cy} l3.5 3.5 l6.5 -7' fill='none' "
             f"stroke='{surface}' stroke-width='2.4' stroke-linecap='round' "
             f"stroke-linejoin='round'/>")
    cur = (f"<circle class='p' cx='{cx}' cy='{cy}' r='{R + 4}' fill='none' "
           f"stroke='{infoc}' stroke-width='2'/>"
           f"<circle cx='{cx}' cy='{cy}' r='{R - 1}' fill='{surface}' stroke='{infoc}' "
           f"stroke-width='2.5'/>"
           f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
           f"fill='{infoc}'>{i + 1}</text>")
    later = (f"<circle cx='{cx}' cy='{cy}' r='{R - 1}' fill='{surface}' "
             f"stroke='{_hx('border-default')}' stroke-width='2'/>"
             f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
             f"fill='{_hx('text-muted')}'>{i + 1}</text>")
    fx.append('If(%s, "%s", %s, "%s", "%s")' % (done, check, current, cur, later))
    fx.append('"<text x=\'%d\' y=\'%d\' %s font-size=\'12\' font-weight=\'600\' '
              'fill=\'" & If(%s, %s, %s, %s, %s) & "\'>" & %s & "</text>"'
              % (cx, STEP_H - 10, font, done, text, current, info, grey, label))
    fx.append('"</svg>"')
    img = '"data:image/svg+xml;utf8," & EncodeUrl(\n    ' + " &\n    ".join(fx) + "\n)"
    state = f'If({done}, "done", {current}, "current step", "not done")'
    # Trinenes status regnes EEN gang pr. billede (With), ikke een gang pr.
    # sted, SVG'en bruger den.
    wrap = "With(\n    %s,\n    %s\n)"
    return Ctrl(f"imgVhpStep{i + 1}", "Image", props={
        "AccessibleLabel": wrap % (_STATE, f'"Go to step {i + 1}, " & {label} & " - " & {state}'),
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(STEP_H),
        "Image": wrap % (_STATE, img),
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": action,
        "TabIndex": "0",
        "Width": width,
    }, h=STEP_H)


def _submit_tooltip():
    reasons = " &\n    ".join([
        'If(!VhpStepPlanDone, "Save the plan header. ", "")',
        f'If(!VhpStepItemDone || ({ITEM_DIRTY}), "Save every item. ", "")',
        'If(!VhpStepTasklistDone, "Give every item a task list. ", "")',
        'If(!VhpStepOpsDone, "Give every item operations. ", "")',
        'If(IsBlank(VhpValidationErrors), "", Char(10) & VhpValidationErrors)',
    ])
    return (f"If(\n    {CAN_SUBMIT},\n    \"Submit the plan for processing.\",\n"
            f"    \"Not ready to submit: \" &\n    {reasons}\n)")


# Save draft og Submit - bredderne bruges baade af knapperne og af
# bjaelkens to sider, saa progressbaren staar i midten.
SAVE_W = fit_button_width('"Save draft"') + ICON_W
SUB_W = fit_button_width('"Submit"', min_w=96) + ICON_W
# Titlen og domaeneikonet foran den (issue #74).
TITLE_W = text_px("VH-plan", 22) + 4 + PAGE_ICON + 10
# Hoejre side: begge knapper; under Tablet kun Submit (Save draft skjules).
RIGHT_W = if_below("Tablet", str(SUB_W), str(SAVE_W + 8 + SUB_W))
# Venstre side er lige saa bred som hoejre, saa trinene staar midt i
# bjaelken. Under Tablet er der ikke plads til at spilde - saa kun titlen.
LEFT_W = if_below("Tablet", str(TITLE_W), str(SAVE_W + 8 + SUB_W))

# Bjaelkens elementer - samme opbevaring som assemble_screen skal bruge.
CONFIRM = []


def build_top_bar():
    """VH-planens topbjaelke (issue #54):

        VH-plan        (1)--(2)--(3)--(4)--(5)        [Save draft][Submit]

    Titlen til venstre, progressbaren CENTRERET, og Save draft og Submit
    samlet til hoejre. Venstre og hoejre side er lige brede, saa midten er
    bjaelkens midte. Help og tema staar i sidebaren."""
    from build_save import save_buttons
    btnDraft, btnSubmit, confirm = save_buttons(CAN_SUBMIT)
    CONFIRM[:] = confirm
    btnDraft.props["Width"] = str(SAVE_W)
    btnDraft.props["Tooltip"] = (
        "If(\n"
        "    varVhpSaving, \"Saving ...\",\n"
        "    IsBlank(varVhpPlanKey), \"Not saved yet. Save as draft so you can come back to it.\",\n"
        "    \"Saved as \" & varVhpPlanKey & \". The next save overwrites items and operations on the same plan.\"\n"
        ")")
    btnDraft.vis = at_least("Tablet")
    focus_border(btnDraft, (5,), C_CARD_BORDER)
    btnSubmit.props["Width"] = str(SUB_W)
    btnSubmit.props["Tooltip"] = _submit_tooltip()
    for b in (btnDraft, btnSubmit):
        b.props["LayoutMinWidth"] = b.props["Width"]
    right = group("conVhpBarRight", [btnDraft, btnSubmit], direction="Horizontal", gap=8,
                  width=RIGHT_W, justify="End", align_items="Center", height=36)
    right.props["LayoutMinWidth"] = RIGHT_W

    title = text_ctrl("txtVhpTitle", '"VH-plan"', size=22, weight="Semibold",
                      height=33, width=TITLE_W - PAGE_ICON - 10, wrap="false")
    icon = page_icon("imgVhpTitleIcon", "vhplan")
    left = group("conVhpBarLeft", [icon, title], direction="Horizontal", width=LEFT_W,
                 align_items="Center", gap=10)
    left.props["LayoutMinWidth"] = LEFT_W

    n = len(STEPS)
    # EN RAEKKE ELLER TRE (issue #73). Foer stod trinene ALTID mellem
    # titlen og knapperne, og under Desktop blev de regnet til 10-16 px
    # brede - progressbaren var i praksis vaek paa tablet og mobil. Nu
    # stables bjaelken med flow_row, naar fem trin paa STEP_MIN ikke kan
    # staa i midten: titel, trinene i fuld bredde, knapperne til hoejre.
    kids = [left, None, right]
    avail = f"{SHELL_W} - ({LEFT_W}) - ({RIGHT_W}) - 24"
    one_row = f"({avail}) >= {n * STEP_MIN}"
    step_w = f"If({one_row}, Min({STEP_W}, ({avail}) / {n}), Min({STEP_W}, {SHELL_W} / {n}))"
    done = ["d%d" % (i + 1) for i in range(n)]
    imgs = []
    for i, (label, _d, action) in enumerate(STEPS):
        before = " && ".join(done[:i]) or "true"
        current = f"(!{done[i]} && {before})"
        prev = done[i - 1] if i else "false"
        imgs.append(_step_image(i, label, done[i], prev, current, action, step_w))
    steps = group("conVhpSteps", imgs, direction="Horizontal", gap=0, height=STEP_H,
                  justify="Center", align_items="Center")
    kids[1] = steps
    bar = flow_row("conVhpBar", kids, SHELL_W, gap=12, flex=steps,
                   flex_min=n * STEP_MIN)
    # Stablet: titlen og knapperne fylder ikke hele linjen.
    left.props["AlignInContainer"] = "AlignInContainer.Start"
    right.props["AlignInContainer"] = "AlignInContainer.End"
    return bar
