# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, SHELL_W, C_PRIMARY, C_CARD_BORDER
from build_helpers import (button, group, fit_button_width, text_ctrl, text_px, grow,
                           ICON_W)
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


STEP_W, STEP_H, R = 120, 60, 13

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

    Stregen til venstre er groen, naar det FORRIGE trin er faerdigt, stregen
    til hoejre, naar DETTE er. Saa moedes de to halvdele midt imellem i
    samme farve, som da trinene var eet billede."""
    n = len(STEPS)
    cx, cy = STEP_W // 2, R + 4
    ok, grey = ref_hex("state-ok-fg"), ref_hex("text-muted")
    line, text = ref_hex("border-default"), ref_hex("text-primary")
    surface = _hx("bg-surface")
    okc = _hx("state-ok-fg")
    font = "font-family='Segoe UI, sans-serif' text-anchor='middle'"
    fx = ['"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'%d\' height=\'%d\' '
          'viewBox=\'0 0 %d %d\'>"' % (STEP_W, STEP_H, STEP_W, STEP_H)]
    if i > 0:
        fx.append('"<line x1=\'0\' y1=\'%d\' x2=\'%d\' y2=\'%d\' stroke-width=\'3\' '
                  'stroke=\'" & If(%s, %s, %s) & "\'/>"' % (cy, cx - R - 4, cy, prev_done, ok, line))
    if i < n - 1:
        fx.append('"<line x1=\'%d\' y1=\'%d\' x2=\'%d\' y2=\'%d\' stroke-width=\'3\' '
                  'stroke=\'" & If(%s, %s, %s) & "\'/>"' % (cx + R + 4, cy, STEP_W, cy, done, ok, line))
    check = (f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='{okc}'/>"
             f"<path d='M{cx - 5} {cy} l3.5 3.5 l6.5 -7' fill='none' stroke='{surface}' "
             f"stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/>")
    cur = (f"<circle cx='{cx}' cy='{cy}' r='{R + 3}' fill='none' stroke='{okc}' "
           f"stroke-width='2'/>"
           f"<circle cx='{cx}' cy='{cy}' r='{R - 1}' fill='{surface}' stroke='{okc}' "
           f"stroke-width='2'/>"
           f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
           f"fill='{okc}'>{i + 1}</text>")
    later = (f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='{_hx('text-muted')}'/>"
             f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
             f"fill='{surface}'>{i + 1}</text>")
    fx.append('If(%s, "%s", %s, "%s", "%s")' % (done, check, current, cur, later))
    fx.append('"<text x=\'%d\' y=\'%d\' %s font-size=\'12\' font-weight=\'600\' '
              'fill=\'" & If(%s || %s, %s, %s) & "\'>" & %s & "</text>"'
              % (cx, STEP_H - 6, font, done, current, text, grey, label))
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
TITLE_W = text_px("VH-plan", 22) + 4
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
                      height=33, width=TITLE_W, wrap="false")
    left = group("conVhpBarLeft", [title], direction="Horizontal", width=LEFT_W,
                 align_items="Center")
    left.props["LayoutMinWidth"] = LEFT_W

    n = len(STEPS)
    avail = f"{SHELL_W} - ({LEFT_W}) - ({RIGHT_W}) - 24"
    step_w = f"Min({STEP_W}, ({avail}) / {n})"
    done = ["d%d" % (i + 1) for i in range(n)]
    imgs = []
    for i, (label, _d, action) in enumerate(STEPS):
        before = " && ".join(done[:i]) or "true"
        current = f"(!{done[i]} && {before})"
        prev = done[i - 1] if i else "false"
        imgs.append(_step_image(i, label, done[i], prev, current, action, step_w))
    steps = grow(group("conVhpSteps", imgs, direction="Horizontal", gap=0, height=STEP_H,
                       justify="Center", align_items="Center"))
    return group("conVhpBar", [left, steps, right], direction="Horizontal", gap=12,
                 align_items="Center")
