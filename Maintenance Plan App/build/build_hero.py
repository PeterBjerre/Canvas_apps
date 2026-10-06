# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, SHELL_W, C_PRIMARY, C_CARD_BORDER, C_VALID_FG, C_MUTED
import layout_tokens as lay
from build_helpers import (group, fit_button_width, text_ctrl, text_px,
                           flow_row, page_icon, PAGE_ICON, ICON_W, top_bar, grow,
                           button, confirm_modal, icon_on_mobile, edit_button, delete_button, delete_modal)
from layout_tokens import if_below, at_least, below
from design_tokens import ref_hex
from build_items import FL_CODE, SEED_FL_PICKER, RESET_EDITOR_CONTROLS
from build_plan_header import PLAN_CONTROLS
from build_load import EMPTY_ITEM_FIELDS, _record, cfg as _cfg
from generate_app_onstart import VARS_BLOCK

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
    "        Trim(inpVhpItemShortText.Text & \"\") <> Trim(it.ShortText & \"\") ||\n"
    "        (drpVhpItemMainWorkCenter.Selected.Value & \"\") <> (it.MainWorkCenter & \"\") ||\n"
    "        (drpVhpItemActivityType.Selected.Value & \"\") <> (it.ActivityType & \"\") ||\n"
    "        tglVhpItemRevision.Value <> !IsBlank(it.Revision) ||\n"
    "        (drpVhpItemNonFlowStatus.Selected.Value & \"\") <> (it.NonFlowUserStatus & \"\") ||\n"
    f"        ({FL_CODE} & \"\") <> (it.FunctionalLocation & \"\") ||\n"
    "        Trim(inpVhpItemInitials.Text & \"\") <> Trim(it.Initials & \"\")\n"
    "    )\n"
    ")"
)

IS_STRAT = 'varVhpPlan.PlanType = "Strategy"'

# FOER OG EFTER SUBMIT (issue #88)
# --------------------------------
# Foer Submit viser de fire trin, hvor langt planen er, og om den kan
# indsendes. Efter Submit viser de SAMME fire billeder, hvor sagen er:
#
#   foer:   Plan       Item             Task list + ops   Ready to submit
#   efter:  Submitted  System approval  Quality review    SAP creation
#                      (Cost approval)                    (Created in SAP)
#
# Det sidste trin hed "Save". Det sluttede bjaelken paa en knap, man
# allerede havde trykket paa, og efter Submit var det ikke laengere sandt.
# "Ready to submit" er groent praecis naar Submit er aktiv (CAN_SUBMIT) -
# samme betingelse, saa trin og knap kan ikke sige noget forskelligt.
#
# Efter Submit laeses trinene af varVhpFlow (build_status: VhpSubmitted,
# VhpApprovalDone, VhpQualityDone, VhpInSap). Godkendelse og teknisk
# oprettelse i SAP er hver sit trin.
#
# KLIK = FREMHAEV, IKKE SETFOCUS (issue #59). SetFocus kan ikke naa en
# kontrol i en container, og alt paa skaermen staar i containere - compile
# afviste alle fem. Canvas apps kan heller ikke scrolle en container fra en
# formel. Et klik saetter derfor varVhpFocusStep, og sektionen, trinnet
# hoerer til, faar en tyk kant i primaerfarven (focus_border nedenfor).
# Tasklist- og Operations-trinnet vaelger ogsaa den rigtige fane.

# Submit er aktiv, naar planen kan indsendes - og intet i Item Editoren
# venter paa at blive gemt. VhpCanSubmit er falsk, naar planen er indsendt.
CAN_SUBMIT = f"VhpCanSubmit && !({ITEM_DIRTY})"

# HVAD MANGLER - EEN liste (trin, mangler, besked). Trinenes tooltips,
# Submits tooltip og linjen under trinene bygges alle af den, og
# betingelserne er de navngivne formler, Submit selv bruger. Saa kan en
# besked ikke sige noget andet end knappen.
MISSING = [
    (1, "!VhpStepPlanDone", '"Save the plan header."'),
    (2, "!VhpStepItemDone", '"Add at least one item and save every item as valid."'),
    (2, ITEM_DIRTY, '"Save the changes in the Item Editor."'),
    (3, "!VhpStepTasklistDone", '"Choose a task list for every item."'),
    (3, "!VhpStepOpsDone",
     f'If({IS_STRAT}, "Give every item operations, each with a package.", '
     '"Give every item at least one operation.")'),
    (4, "!IsBlank(VhpValidationErrors)",
     'With({ n: CountRows(Split(VhpValidationErrors, Char(10))) }, '
     '"Fix " & n & If(n = 1, " plan rule", " plan rules") & "{hint}.")'),
]

# Navnet, ITEM_DIRTY faar i en With - saa regnes den een gang pr. formel.
DIRTY = "vhpDirty"


def with_dirty(expr):
    """expr med ITEM_DIRTY regnet een gang i en With."""
    return ("With(\n    { %s: %s },\n    %s\n)"
            % (DIRTY, ITEM_DIRTY, expr.replace(ITEM_DIRTY, DIRTY)))


def missing_list(steps=None, sep='Char(10)', bullet='"- "', hint=""):
    """De beskeder i MISSING, der gaelder nu - for trinene i steps
    (alle, naar steps er None). Tom tekst, naar intet mangler. hint
    staar efter regelbeskeden, hvor reglerne ikke selv er listet."""
    parts = [f"If({cond}, {bullet} & {msg.replace('{hint}', hint)} & {sep}, \"\")"
             for st, cond, msg in MISSING if steps is None or st in steps]
    return " &\n        ".join(parts)


# (label foer, faerdig foer, label efter, faerdig efter, klik)
STEPS = [
    ('"Plan"', "VhpStepPlanDone",
     '"Submitted"', "true",
     "Set(varVhpFocusStep, 1)"),
    ('"Item"', f"VhpStepItemDone && !({ITEM_DIRTY})",
     'If(varVhpFlow.Stage = "Cost", "Cost approval", '
     'VhpApprovalDone, "Approved", "System approval")', "VhpApprovalDone",
     "Set(varVhpFocusStep, 2)"),
    (f'If({IS_STRAT}, "Task list + pkgs", "Task list + ops")',
     "VhpStepTasklistDone && VhpStepOpsDone",
     '"Quality review"', "VhpQualityDone",
     f'Set(varVhpOpsTab, If({IS_STRAT}, "pkg", "ops"));\nSet(varVhpFocusStep, 3)'),
    ('"Ready to submit"', CAN_SUBMIT,
     'If(VhpInSap, "Created in SAP", "SAP creation")', "VhpInSap",
     "Set(varVhpFocusStep, 4)"),
]

# Hvad hvert trin betyder EFTER Submit - tooltippen paa billedet.
AFTER_TIPS = [
    '"Submitted for approval."',
    'If(VhpApprovalDone, "System and cost approval are done.", '
    'varVhpFlow.Stage = "Cost", "Waiting for cost approval.", '
    '"Waiting for the system owners to approve the items.")',
    'If(VhpQualityDone, "Quality review is done.", VhpApprovalDone, '
    '"Waiting for the quality review.", "The quality review follows the system and cost approval.")',
    'If(VhpInSap, "Created in SAP.", VhpQualityDone, '
    '"Approved - waiting for Master Data to create the plan in SAP.", '
    '"Master Data creates the plan in SAP once it is approved.")',
]


def _label(i):
    pre, _d, post, _pd, _a = STEPS[i]
    return f"If(VhpSubmitted, {post}, {pre})"


def _done(i):
    _l, pre, _p, post, _a = STEPS[i]
    return f"If(VhpSubmitted, {post}, {pre})"


def _step_tooltip(i):
    """Foer Submit: hvad der mangler i trinet (eller at det er faerdigt).
    Efter Submit: hvor sagen er."""
    last = i == len(STEPS) - 1
    # "Ready to submit" kraever det hele - dets tooltip er hele listen og
    # reglerne selv.
    lst = (missing_list(hint=":") + ' &\n        VhpValidationErrors') if last else missing_list(steps=(i + 1,))
    done_tip = '"Ready - Submit is available."' if last else '"Done."'
    tip = (f"If(\n    VhpSubmitted, {AFTER_TIPS[i]},\n    d{i + 1}, {done_tip},\n"
           f"    \"Missing:\" & Char(10) &\n        {lst}\n)")
    return with_dirty(tip) if ITEM_DIRTY in tip else tip


def focus_border(ctrl, steps, normal):
    """Kanten paa en sektion, der hoerer til trinene i steps: tyk og i
    primaerfarven, naar et af dem er klikket i progressbaren."""
    on = " || ".join(f"varVhpFocusStep = {n}" for n in steps)
    on = f"IfError({on}, false)"
    ctrl.props["BorderColor"] = f"If({on}, {C_PRIMARY}, {normal})"
    ctrl.props["BorderThickness"] = f"If({on}, 2, 1)"
    return ctrl


STEP_W, STEP_H, R = 104, 56, 13
# Et trin maa ikke blive smallere end det her - saa kan navnet ikke laeses.
# Er der ikke plads til fem af dem mellem titlen og knapperne, stables
# bjaelken (issue #73): titel, trin i fuld bredde, knapper.
STEP_MIN = 88

# { d1: ..., d4: ... } - trinenes status, som hvert billede laeser.
_STATE = "{ " + ",\n      ".join("d%d: %s" % (i + 1, _done(i)) for i in range(len(STEPS))) + " }"


def _hx(name):
    """En farvetoken midt i en SVG-streng."""
    return '" & %s & "' % ref_hex(name)


def _step_image(i, label, done, prev_done, current, action, width, suffix="", height=None):
    """Eet trin: cirklen, dets navn og de to halve streger ud til naboerne.

    Stregen til venstre er faerdig, naar det FORRIGE trin er faerdigt,
    stregen til hoejre, naar DETTE er. Saa moedes de to halvdele midt
    imellem, som da trinene var eet billede.

    ANIMERET, MEN STILLE (issue #73)
    --------------------------------
    - Den faerdige streg TEGNES frem (stroke-dashoffset) med en svag
      gradient i ok-farven - venstre halvdel foerst, saa hoejre, saa
      fremdriften loeber fra trin til trin.
    - Det aktive trins ring pulserer i 5 sekunder (4 gange a 1,25 s) og
      staar derefter stille. Billedet tegnes forfra, naar trinet skifter.
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
           "animation:pulse 1.25s ease-in-out 4 forwards}"
           "@keyframes draw{to{stroke-dashoffset:0}}"
           "@keyframes pulse{0%,100%{opacity:.7;transform:scale(1)}"
           "50%{opacity:.95;transform:scale(1.08)}}"
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
    cur = (f"<circle class='p' cx='{cx}' cy='{cy}' r='{R + 4}' fill='none' opacity='.7' "
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
              % (cx, cy + R + 20, font, done, text, current, info, grey, label))
    fx.append('"</svg>"')
    img = '"data:image/svg+xml;utf8," & EncodeUrl(\n    ' + " &\n    ".join(fx) + "\n)"
    state = f'If({done}, "done", {current}, "current step", "not done")'
    # Trinenes status regnes EEN gang pr. billede (With), ikke een gang pr.
    # sted, SVG'en bruger den.
    wrap = "With(\n    %s,\n    %s\n)"
    return Ctrl(f"imgVhpStep{i + 1}{suffix}", "Image", props={
        "AccessibleLabel": wrap % (_STATE, f'"Go to step {i + 1}, " & {label} & " - " & {state}'),
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(height or STEP_H),
        "Image": wrap % (_STATE, img),
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": action,
        "TabIndex": "0",
        "Tooltip": wrap % (_STATE, _step_tooltip(i)),
        "Width": width,
    }, h=height or STEP_H)


def _submit_tooltip():
    """Samme liste som trinene (MISSING) - og reglerne selv til sidst."""
    return with_dirty(f"If(\n    VhpSubmitted, \"Already submitted - see the progress bar.\",\n"
            f"    {CAN_SUBMIT},\n    \"Submit the plan for approval.\",\n"
            f"    \"Not ready to submit:\" & Char(10) &\n        {missing_list(hint=':')} &\n"
            f"        VhpValidationErrors\n)")


# LINJEN UNDER TRINENE (issue #88): det, der mangler, uden at man skal
# holde musen over noget - eller, efter Submit, hvor sagen ligger. Samme
# liste (MISSING) og samme betingelse (CAN_SUBMIT) som trin og Submit.
# Hvor sagen ligger efter Submit - een linje.
AFTER_LINE = (
    'If(VhpInSap, "Created in SAP.", '
    'VhpQualityDone, "Approved - waiting for Master Data to create the plan in SAP.", '
    'VhpApprovalDone, "Waiting for the quality review.", '
    'varVhpFlow.Stage = "Cost", "Waiting for cost approval.", '
    '"Waiting for the system owners to approve the items.")'
)
_INLINE = missing_list(sep='" "', bullet='""', hint=" - hover Submit to see them")
READINESS = with_dirty(
    "If(\n"
    "    VhpSubmitted,\n"
    f'    "Submitted. " & {AFTER_LINE},\n'
    '    varVhpFlow.Status = "Returned",\n'
    '    "Returned to you" & If(IsBlank(varVhpFlow.ReturnComment), ".", ": " & varVhpFlow.ReturnComment) &\n'
    '        " Correct the plan and submit it again.",\n'
    '    varVhpViewOnly,\n'
    '    "View only - this plan has not been submitted.",\n'
    f"    {CAN_SUBMIT},\n"
    '    "Ready to submit.",\n'
    '    "Before you can submit: " &\n'
    f"        {_INLINE}\n"
    ")")
READY_OK = f"(VhpSubmitted || ({CAN_SUBMIT}))"


# Save draft og Submit - bredderne bruges af knapperne.
# "Save draft" sagde ikke, om man oprettede eller opdaterede (issue #88).
# Knappen hedder nu det, den goer; status i SharePoint er stadig Draft.
DRAFT_TEXT = 'If(IsBlank(varVhpPlanKey), "Create draft", "Update draft")'
SAVE_W = fit_button_width('"Update draft"') + ICON_W
SUB_W = fit_button_width('"Submit"', min_w=72)
SUBTITLE = '"Plan header, items, task lists and operations - submitted to SAP master data."'
NEW_W = fit_button_width('"New request"') + ICON_W
EDIT_W = fit_button_width('"Edit"') + ICON_W
NOTES_W = 40

RESET_COLLECTIONS = ("colVhpItems", "colVhpOperations", "colVhpItemObjects", "colVhpObjDraft",
                     "colVhpMaterials", "colVhpAttachments")

NEW_PLAN_FX = (
    VARS_BLOCK[:VARS_BLOCK.index("// Brugeren")].strip() + "\n"
    'Set(varVhpSavedJson, ""); Set(varVhpPrevPlant, ""); Set(varVhpPlanSpId, 0);\n'
    'Set(varVhpPlanKey, ""); Set(varVhpPlanModified, Blank()); Set(varVhpRequestGuid, "");\n'
    "Set(varVhpFocusStep, 0);\n"
    + "".join(f"Clear({c});\n" for c in RESET_COLLECTIONS)
    + f"Collect(colVhpItems, {_record(EMPTY_ITEM_FIELDS, 4)});\n"
    + SEED_FL_PICKER + ";\n"
    + RESET_EDITOR_CONTROLS + ";\n"
    + "; ".join(f"Reset({c})" for c in PLAN_CONTROLS) + ";\n"
    'Notify("New request started.", NotificationType.Success)'
)

HAS_UNSAVED = (
    f"(varVhpPlanCommitted || CountRows(colVhpItems) > 1 || "
    f"!IsBlank(Trim(First(colVhpItems).ShortText))) && "
    f"!(VhpStepSaveDone && varVhpPlanLocked && !({ITEM_DIRTY}))"
)

def readiness_line():
    """Linjen under trinene: hvad der mangler foer Submit, eller hvor sagen
    ligger efter. Groen, naar planen er klar eller indsendt. Skjult, naar
    planen kun vises og ikke er indsendt, staar der blot det. Linjen er
    altid synlig, saa headerens hoejde kun afhaenger af skaermbredden."""
    ok = f"(VhpSubmitted || ({CAN_SUBMIT}))"
    ctrl = text_ctrl("txtVhpReadiness", READINESS, size=12,
                     color=with_dirty(f"If({ok}, {C_VALID_FG}, {C_MUTED})"),
                     wrap="true", align="Center", height=20,
                     accessible='"Submission status: " & Self.Text')
    ctrl.props["Width"] = "Parent.Width"
    # To linjer paa en telefon - beskeden er for lang til een.
    ctrl.props["Height"] = ctrl.h = if_below("Tablet", "36", "20")
    return ctrl


# Bjaelkens elementer - samme opbevaring som assemble_screen skal bruge.
CONFIRM = []


def build_top_bar():
    """VH-planens topbjaelke - to raekker, saa intet kan klippes:

        [ikon] VH-plan                                  [Save draft][Submit]
               undertekst
                 (1)-----(2)-----(3)-----(4)-----(5)
                 Plan    Item    Task    Ops     Save

    Foerste raekke er den SAMME titelbjaelke som paa alle andre sider
    (build_helpers.top_bar), saa ikonet staar det samme sted overalt.
    Trinene staar under den, i fuld bredde og med fast hoejde. Help og tema
    staar i sidebaren."""
    from build_save import save_buttons, NOTES_OPEN_VIEW, NOTES_HAVE
    btnDraft, btnSubmit, confirm = save_buttons(CAN_SUBMIT)
    # Noterne ved Submit, skrivebeskyttet (issue #115): kun naar planen har
    # en note, brugeren maa se. Kun ikonet, saa knaprakken ikke vokser.
    btnNotes = button("btnVhpNotes", '"Notes"', NOTES_OPEN_VIEW, width=NOTES_W, height=36,
                      icon="Note", accessible='"View the submission notes"', tooltip='"View notes"',
                      visible=NOTES_HAVE)
    btnNotes.props["Layout"] = "ButtonLayout.IconOnly"
    btnNotes.props["AlignInContainer"] = "AlignInContainer.Center"
    btnNotes.props["LayoutMinWidth"] = str(NOTES_W)
    btnNew = button("btnVhpNewRequest", '"New request"',
                    f"If({HAS_UNSAVED}, Set(varVhpConfirmNew, true), {NEW_PLAN_FX})",
                    width=NEW_W, height=36, icon="Add",
                    accessible='"Start a new blank request"')
    btnNew.props["AlignInContainer"] = "AlignInContainer.Center"
    btnNew.props["LayoutMinWidth"] = str(NEW_W)
    btnNew.vis = at_least("Tablet")
    # Den faelles Edit (build_helpers.edit_button). Den skifter KUN til Edit
    # mode (issue #103): de gemte sektioner forbliver sammenklappede, og hver
    # aabnes med sin egen Edit - foer laaste denne knap ogsaa Plan Header op.
    btnEdit = edit_button("btnVhpEdit", "varVhpViewOnly", "varVhpCanEdit",
                          "Set(varVhpViewOnly, false)")
    confirmNew = confirm_modal(
        "VhpNew", "varVhpConfirmNew", "Start a new request?",
        '"Unsaved work on this request is discarded. Save a draft first to keep it."',
        "Discard and start new", NEW_PLAN_FX, "btnVhpNewConfirm", icon="Add")
    CONFIRM[:] = confirm + confirmNew + delete_modal("Vhp", "varVhpRequestGuid", _cfg.L_INDEX, "MaintenancePlan")
    btnDelete = delete_button("Vhp", "varVhpViewOnly", "varVhpRequestGuid")
    btnDraft.props["Width"] = str(SAVE_W)
    btnDraft.props["Text"] = DRAFT_TEXT
    btnDraft.props["AccessibleLabel"] = (
        'If(IsBlank(varVhpPlanKey), "Create the plan as a draft", "Update the saved draft")')
    btnDraft.props["Tooltip"] = (
        "If(\n"
        "    varVhpSaving, \"Saving ...\",\n"
        "    IsBlank(varVhpPlanKey), \"Not saved yet. Create a draft so you can come back to it.\",\n"
        "    \"Saved as draft \" & varVhpPlanKey & \". Update draft saves your changes to the same plan, items and operations.\"\n"
        ")")
    focus_border(btnDraft, (4,), C_CARD_BORDER)
    btnSubmit.props["Width"] = str(SUB_W)
    btnSubmit.props["Tooltip"] = _submit_tooltip()
    title_bar = top_bar("Vhp", '"Maintenance Plan"', SUBTITLE, [], icon="vhplan", mode_var="varVhpViewOnly",
                     num_var="varVhpPlanKey")
    # Nye navne: Studio beholdt bjaelkens gamle tilstand paa conVhpBar fra foer redesignet.
    title_bar.name = "conVhpTitleRow"
    title_bar.children[1].name = "conVhpTitleText"
    title_bar.props["AlignInContainer"] = "AlignInContainer.Center"
    title_bar.children[1].props["AlignInContainer"] = "AlignInContainer.Center"
    btnDraft.props["AlignInContainer"] = "AlignInContainer.Center"
    btnSubmit.props["AlignInContainer"] = "AlignInContainer.Center"
    btnDraft.props["LayoutMinWidth"] = str(SAVE_W)
    btnSubmit.props["LayoutMinWidth"] = str(SUB_W)
    for b_ in (btnNew, btnDraft):
        icon_on_mobile(b_)
    narrow = below("Tablet")
    new_m_w = fit_button_width('"New"', min_w=0) + 8
    btnNew.props["Text"] = f'If({narrow}, "New", "New request")'
    btnNew.props["Width"] = f"If({narrow}, {new_m_w}, {NEW_W})"
    btnNew.props["LayoutMinWidth"] = btnNew.props["Width"]
    btnNew.props["Layout"] = f"If({narrow}, ButtonLayout.TextOnly, ButtonLayout.IconBefore)"
    btnNew.vis = None
    btnDraft.vis = None

    n = len(STEPS)
    step_w = f"Min({STEP_W}, {SHELL_W} / {n})"
    done = ["d%d" % (i + 1) for i in range(n)]
    imgs = []
    for i in range(n):
        before = " && ".join(done[:i]) or "true"
        current = f"(!{done[i]} && {before})"
        prev = done[i - 1] if i else "false"
        imgs.append(_step_image(i, _label(i), done[i], prev, current, STEPS[i][4], step_w))
    steps_w = n * STEP_W
    steps = group("conVhpStepRow", imgs, direction="Horizontal", gap=0, height=STEP_H,
                  width=str(steps_w), justify="Center", align_items="Center",
                  layout_min_width=steps_w)
    steps.vis = at_least("Desktop")
    # Mobile: the same step images (same STEPS logic) in a full-width row above the buttons.
    m_h = f"Min({STEP_H}, ({SHELL_W}) / {n} * {STEP_H} / {STEP_W})"
    m_imgs = [_step_image(i, _label(i), done[i], done[i - 1] if i else "false",
                          f"(!{done[i]} && {' && '.join(done[:i]) or 'true'})", STEPS[i][4],
                          f"{SHELL_W} / {n}", suffix="M", height=m_h)
              for i in range(n)]
    m_steps = group("conVhpStepRowM", m_imgs, direction="Horizontal", gap=0, height=m_h,
                    width=SHELL_W, justify="Center", align_items="Start",
                    visible=below("Tablet"))
    # Trinene staar midt paa linjen: titelblokken har samme bredde som den
    # tomme rest efter dem, og resten tager en afstandsholder.
    side_min = SAVE_W + SUB_W + NEW_W + EDIT_W + 32 + 40
    side_w = if_below(
        "Desktop", if_below("Tablet", str(SUB_W + 80 + new_m_w + 24 + 48), str(side_min)),
        f"Max({side_min}, ({SHELL_W} - {steps_w}) / 2 - 16)")
    # Tablet: trinene er skjult, saa titlen faar resten efter knapperne (mindst
    # 220 som foer) - ellers klippes "Maintenance Plan" paa en bred tablet,
    # selv om linjen har plads (issue #93).
    tab_w = f"Max(220, {SHELL_W} - {side_min} - 16)"
    title_bar.props["Width"] = if_below("Tablet", "56", if_below("Desktop", tab_w, f"Max({side_min}, ({SHELL_W} - {steps_w}) / 2 - 16)"))
    title_bar.props["LayoutMinWidth"] = if_below("Tablet", "56", "220")
    btns = group("conVhpHeadBtns", [btnNotes, btnEdit, btnDelete, btnNew, btnDraft, btnSubmit], direction="Horizontal", gap=8,
                 height=44, width=side_w, justify="End", align_items="Center")
    head = group("conVhpHeadLine", [title_bar, steps, btns],
                 height=if_below("Tablet", "60", str(STEP_H + 28)),
                 direction="Horizontal", gap=16, align_items="Center", justify="SpaceBetween")
    title_bar.vis = at_least("Tablet")
    head.props["LayoutJustifyContent"] = ("If(%s, LayoutJustifyContent.End, LayoutJustifyContent.SpaceBetween)" % below("Tablet"))
    spacer = group("conVhpHeadSpace", [], direction="Horizontal", height=if_below("Tablet", "10", "8"))
    head = group("conVhpHeadStack", [m_steps, head, readiness_line(), spacer], direction="Vertical", gap=0)
    if os.environ.get("VHP_DEBUG_LAYOUT"):
        # Midlertidig diagnose: hver container faar sin egen baggrund.
        for ctl, tok in ((head, "state-info-bg"), (title_bar, "state-warn-bg"),
                         (title_bar.children[1], "state-error-bg"), (steps, "state-ok-bg")):
            ctl.props["Fill"] = "C.'%s'" % tok
    return head
