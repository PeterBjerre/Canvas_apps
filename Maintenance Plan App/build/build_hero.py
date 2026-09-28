# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, SHELL_W
from build_helpers import button, top_bar, group, fit_button_width
from layout_tokens import if_below
from design_tokens import ref_hex

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
    "        (drpVhpItemRevision.Selected.Value & \"\") <> (it.Revision & \"\") ||\n"
    "        (drpVhpItemFL.Selected.Code & \"\") <> (it.FunctionalLocation & \"\") ||\n"
    "        Trim(txtVhpItemInitials.Text & \"\") <> Trim(it.Initials & \"\") ||\n"
    "        Trim(txtVhpItemLongText.Text & \"\") <> Trim(it.LongText & \"\")\n"
    "    )\n"
    ")"
)

IS_STRAT = 'varVhpPlan.PlanType = "Strategy"'

# (label, faerdig, klik)
STEPS = [
    ('"Plan"', "VhpStepPlanDone", "SetFocus(btnVhpPlanSave)"),
    ('"Item"', f"VhpStepItemDone && !({ITEM_DIRTY})", "SetFocus(btnVhpAddItem)"),
    ('"Task list"', "VhpStepTasklistDone",
     'Set(varVhpOpsTab, "ops");\nSetFocus(btnVhpTabOps)'),
    (f'If({IS_STRAT}, "Packages", "Operations")', "VhpStepOpsDone",
     f'If(\n    {IS_STRAT},\n    Set(varVhpOpsTab, "pkg"); SetFocus(btnVhpTabPkg),\n'
     f'    Set(varVhpOpsTab, "ops"); SetFocus(btnVhpTabOps)\n)'),
    ('"Save"', f"VhpStepSaveDone && varVhpPlanLocked && !({ITEM_DIRTY})",
     "SetFocus(btnVhpSaveDraft)"),
]
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


def build_top_bar():
    """VH-planens topbjaelke - den samme som i de tre andre apps
    (build_helpers.top_bar), med progressbaren under titlen og Save draft
    til hoejre. Help og tema staar i sidebaren."""
    from build_save import save_buttons
    btnDraft, btnSubmit = save_buttons(CAN_SUBMIT)
    save_w = fit_button_width('"Save draft"')
    sub_w = fit_button_width('"Submit"', min_w=96)
    btnDraft.props["Width"] = str(save_w)
    btnDraft.props["Tooltip"] = (
        "If(\n"
        "    varVhpSaving, \"Saving ...\",\n"
        "    IsBlank(varVhpPlanKey), \"Not saved yet. Save as draft so you can come back to it.\",\n"
        "    \"Saved as \" & varVhpPlanKey & \". The next save overwrites items and operations on the same plan.\"\n"
        ")")
    btnSubmit.props["Width"] = str(sub_w)
    btnSubmit.props["Tooltip"] = _submit_tooltip()
    btnSubmit.props["AlignInContainer"] = "AlignInContainer.Center"
    btnSubmit.props["LayoutMinWidth"] = str(sub_w)

    n = len(STEPS)
    avail = if_below("Tablet", f"{SHELL_W} - {sub_w} - 12",
                     f"{SHELL_W} - {save_w} - 10 - {sub_w} - 12")
    step_w = f"Min({STEP_W}, ({avail}) / {n})"
    done = ["d%d" % (i + 1) for i in range(n)]
    imgs = []
    for i, (label, _d, action) in enumerate(STEPS):
        before = " && ".join(done[:i]) or "true"
        current = f"(!{done[i]} && {before})"
        prev = done[i - 1] if i else "false"
        imgs.append(_step_image(i, label, done[i], prev, current, action, step_w))
    gap = group("conVhpStepsGap", [], direction="Horizontal", width=8, height=0)
    steps = group("conVhpSteps", imgs + [gap, btnSubmit], direction="Horizontal", gap=0,
                  height=STEP_H, align_items="Center",
                  width=f"{n} * ({step_w}) + 8 + {sub_w}")
    # Paa en smal skaerm er der kun plads til progressbaren og Submit.
    return top_bar("Vhp", '"VH-plan"', None, [btnDraft], sub=[steps],
                   narrow_hide=("btnVhpSaveDraft",))
