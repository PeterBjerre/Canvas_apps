# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, SHELL_W, C_PRIMARY, C_CARD_BORDER, C_VALID_FG, C_MUTED,
                        C_DIVIDER, C_MODAL_BG, C_PRIMARY_SOFT, stack_height)
import layout_tokens as lay
from build_helpers import (group, fit_button_width, text_ctrl, text_px,
                           flow_row, page_icon, PAGE_ICON, ICON_W, top_bar, grow,
                           button, confirm_modal, edit_button, delete_modal, tap_backdrop)
from build_status import MISSING_NAMES, join_lines
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
    # Revision og Non Flow (issue #141): en tom kladde er uroert = gemt.
    "        (!IsBlank(varVhpItemRevPick) && varVhpItemRevPick <> !IsBlank(it.Revision)) ||\n"
    "        (!IsBlank(varVhpItemNfPick) && (varVhpItemNfPick.Value & \"\") <> (it.NonFlowUserStatus & \"\")) ||\n"
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

# HVAD MANGLER (issue #220) - grupperet efter sektion. Kilden er de
# navngivne formler VhpPlanMissing, VhpItemMissing og VhpOpsMissing
# (build_status.py): trinenes beskeder plus sektionens linjer fra
# VhpValidationErrors - de samme betingelser, som Submit, progressbaren og
# badgerne bruger. Skaermen laegger kun usavede aendringer i Item Editoren
# til (ITEM_DIRTY), som ingen formel kan se. Trinenes tooltips, Submits
# tooltip, linjen under trinene og listen "Before you can submit" bygges
# alle af GROUPS. Foer stod der "Fix 1 plan rule - hover Submit to see
# them" - nu staar selve reglerne der.
DIRTY_MSG = '"Save the changes in the Item Editor."'
# (overskrift = sektionens titel, tekst med een linje pr. krav, trin)
GROUPS = [
    ("Plan Header", MISSING_NAMES["Plan"], 1),
    ("Items", join_lines([MISSING_NAMES["Item"], f'If({ITEM_DIRTY}, {DIRTY_MSG}, "")']), 2),
    ("Tasklist and Operations", MISSING_NAMES["Ops"], 3),
]
# Listen "Before you can submit" (missing_modal) har een tekst pr. gruppe.
# De tekster ER skaermens kilde: ITEM_DIRTY regnes kun der, og linjen under
# trinene, info-ikonet, trinenes tooltips og Submits tooltip laeser dem.
# Teksterne regnes, ogsaa naar popuppen er lukket.
MISS_TXT = ("txtVhpMissingPlan", "txtVhpMissingItem", "txtVhpMissingOps")
GT = [f"{n}.Text" for n in MISS_TXT]
BULLET = "\u2022 "

# Navnet, ITEM_DIRTY faar i en With - saa regnes den een gang pr. formel.
DIRTY = "vhpDirty"


def with_dirty(expr):
    """expr med ITEM_DIRTY regnet een gang i en With."""
    return ("With(\n    { %s: %s },\n    %s\n)"
            % (DIRTY, ITEM_DIRTY, expr.replace(ITEM_DIRTY, DIRTY)))


def bullets(text):
    """Een punkttegn-linje pr. krav."""
    return f'"{BULLET}" & Substitute({text}, Char(10), Char(10) & "{BULLET}")'


# Alle krav som en tabel (Value, med punkttegn) - til den foerste linje
# og antallet.
ALL_MISSING = ("Filter(Split(%s, Char(10)), !IsBlank(Value))"
               % " & Char(10) & ".join(GT))
# Alle krav, grupperet: "Plan Header:" og kravene under, osv.
GROUPED = ("Concat(\n        Filter(Table(%s), !IsBlank(t)),\n"
           "        h & \":\" & Char(10) & t,\n        Char(10)\n    )"
           % ", ".join('{ h: "%s", t: %s }' % (h, t) for t, (h, _f, _s) in zip(GT, GROUPS)))


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
    """Foer Submit: hvad der mangler i trinets sektion (eller at det er
    faerdigt). Efter Submit: hvor sagen er. Tooltippen er en ekstra vej -
    det hele staar ogsaa under trinene og i listen bag info-ikonet."""
    if i == len(STEPS) - 1:
        # "Ready to submit" kraever det hele - hele listen, grupperet.
        return (f"If(\n    VhpSubmitted, {AFTER_TIPS[i]},\n"
                f"    d{i + 1}, \"Ready - Submit is available.\",\n"
                f"    \"Before you can submit:\" & Char(10) & {GROUPED}\n)")
    # Sektionens krav - ogsaa naar trinet er groent, men en regel i
    # sektionen fejler. Saa siger tooltip og badge det samme.
    return (f"If(\n    VhpSubmitted, {AFTER_TIPS[i]},\n"
            f"    !IsBlank({GT[i]}), \"Missing:\" & Char(10) & {GT[i]},\n"
            f"    \"Done.\"\n)")


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
    """Samme grupperede liste som "Before you can submit" (GROUPS)."""
    # View mode foerst (issue #211): Submit staar graa, til man vaelger Edit.
    return with_dirty(f"If(\n    VhpSubmitted, \"Already submitted - see the progress bar.\",\n"
            f"    IfError(varVhpViewOnly, false), \"View mode - select Edit to change or submit the plan.\",\n"
            f"    {CAN_SUBMIT},\n    \"Submit the plan for approval.\",\n"
            f"    varVhpSaving, \"Saving ...\",\n"
            f"    \"Before you can submit:\" & Char(10) & {GROUPED}\n)")


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
# Det foerste krav staar paa linjen - specifikt og uden hover. Info-ikonet
# ved siden af aabner hele listen, grupperet (missing_modal).
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
    '    varVhpSaving,\n'
    '    "Saving ...",\n'
    f'    "Before you can submit: " & Mid(First({ALL_MISSING}).Value, {len(BULLET) + 1})\n'
    ")")
# Planen er ikke indsendt og staar i Edit mode: kravene giver mening, og
# info-ikonet staar ved linjen (issue #230). Er alt i orden, siger listen
# det - saa ikonet bliver staaende, ogsaa ved "Ready to submit."
INFO_VIS = "(!VhpSubmitted && !IfError(varVhpViewOnly, false))"
READY_OK = f"(VhpSubmitted || ({CAN_SUBMIT}))"


# Save draft og Submit - bredderne bruges af knapperne.
# "Save draft" sagde ikke, om man oprettede eller opdaterede (issue #88).
# Knappen hedder nu det, den goer; status i SharePoint er stadig Draft.
DRAFT_TEXT = 'If(IsBlank(varVhpPlanKey), "Create draft", "Update draft")'
SAVE_W = fit_button_width('"Update draft"') + ICON_W
# Submit har ikonet foran teksten - det skal ogsaa have plads, ellers
# klippes "Submit" (issue #211).
SUB_W = fit_button_width('"Submit"', min_w=72) + ICON_W
SUBTITLE = '"Plan header, items, task lists and operations - submitted to SAP master data."'
NEW_W = fit_button_width('"New request"') + ICON_W
EDIT_W = fit_button_width('"Edit"') + ICON_W

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

MISSING_ON = "IfError(varVhpMissingOn, false)"
MISSING_CLOSE = "Set(varVhpMissingOn, false)"
# Info-ikonet ved linjen (issue #230) - kvadratisk, mindst 30 px (regel 25).
INFO_W = 32
# Raekkens hoejde: kun skaermbredden (check_layout 23b). To linjer tekst
# paa en telefon - beskeden kan vaere for lang til een.
READY_H = if_below("Tablet", "40", "32")


def readiness_line():
    """Linjen under trinene: det foerste, der mangler foer Submit - eller
    hvor sagen ligger efter. Groen, naar planen er klar eller indsendt.

    INFO-IKONET (issue #230). Foer stod "Show all (n)" yderst til hoejre i
    raekken. Nu staar et info-ikon lige efter teksten - "Ready to submit."
    eller det foerste krav - og aabner den samme liste "Before you can
    submit" (missing_modal). Det er en knap, saa den kan naas med mus,
    tastatur (Tab, Enter) og touch; tooltip og tilgaengeligt navn siger,
    hvad den goer. Teksten er saa bred som sit indhold (hoejst raekkens
    bredde minus ikonet), og raekken er centreret, saa ikonet staar ved
    teksten paa alle skaermbredder. Raekken er altid synlig, saa headerens
    hoejde kun afhaenger af skaermbredden."""
    ok = f"(VhpSubmitted || ({CAN_SUBMIT}))"
    ctrl = text_ctrl("txtVhpReadiness", READINESS, size=12,
                     color=with_dirty(f"If({ok}, {C_VALID_FG}, {C_MUTED})"),
                     wrap="true", align="Center", height=20,
                     accessible='"Submission status: " & Self.Text',
                     extra={"VerticalAlign": "VerticalAlign.Middle"})
    # Tekstens bredde: et skoen over laengden (12 px Segoe, lidt for bredt
    # hellere end klippet) - hoejst pladsen ved siden af ikonet.
    ctrl.props["Width"] = (f"Min({SHELL_W} - {INFO_W + 8}, "
                           f"RoundUp(Len(Self.Text) * 7, 0) + 12)")
    ctrl.props["LayoutMinWidth"] = "0"
    ctrl.props["Height"] = ctrl.h = READY_H
    info = button("btnVhpShowMissing", '""', "Set(varVhpMissingOn, true)",
                  width=INFO_W, height=INFO_W, icon="Info",
                  accessible='"Show the submission requirements"',
                  tooltip='"Show what is needed before you can submit"',
                  visible=INFO_VIS)
    info.props["Layout"] = "ButtonLayout.IconOnly"
    info.props["LayoutMinWidth"] = str(INFO_W)
    info.props["BorderColor"] = f"If({MISSING_ON}, {C_PRIMARY}, {C_CARD_BORDER})"
    return group("conVhpReadyRow", [ctrl, info], direction="Horizontal", gap=8,
                 height=READY_H, align_items="Center", justify="Center")


def _lines_h(text, width, px=7.2, line_h=19):
    """Hoejden af en ombrudt tekst: linjer regnet af laengden og
    linjeskiftene (som Issue Boardets). Hellere en linje luft for meget."""
    cpl = f"Max(12, RoundDown(({width}) / {px}, 0))"
    return (f"With({{ t: {text} }}, (RoundUp(Len(t) / {cpl}, 0) + "
            f"CountRows(Split(t, Char(10))) - 1) * {line_h} + 2)")


MODAL_W = "Min(520, App.Width - 24)"
MODAL_PAD = 18


def missing_modal():
    """"Before you can submit" (issue #220) - [sloer, popup].

    Alt, der mangler, grupperet efter sektion: Plan Header, Items og
    Tasklist and Operations. Samme kilde som linjen under trinene, Submits
    tooltip og trinene (GROUPS), saa listen kan ikke sige noget andet end
    knappen. Den regnes om, mens brugeren retter - et krav forsvinder,
    naar det er opfyldt, og er alt i orden, siger popuppen det. Indholdet
    scroller, hvis listen er hoejere end skaermen; Close kan altid naas."""
    vis = MISSING_ON
    backdrop = tap_backdrop("conVhpMissingBackdrop", vis, MISSING_CLOSE)
    title = text_ctrl("txtVhpMissingTitle", '"Before you can submit"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    intro = text_ctrl("txtVhpMissingIntro",
                      f'If(IsEmpty({ALL_MISSING}), "Everything is in place. You can submit the plan now.", '
                      '"Complete the steps below. The list updates as you fix them.")',
                      size=13, color=f"If(IsEmpty({ALL_MISSING}), {C_VALID_FG}, {C_MUTED})",
                      height=38, wrap="true")
    text_w = f"{MODAL_W} - {2 * MODAL_PAD} - {lay.SCROLLBAR_W}"
    blocks = []
    for (head, fx, _st), name, ref in zip(GROUPS, MISS_TXT, GT):
        h = text_ctrl(f"{name}H", f'"{head}"', size=13, weight="Semibold",
                      height=20, wrap="false")
        body_fx = f"With(\n    {{ t: {fx} }},\n    If(IsBlank(t), \"\", {bullets('t')})\n)"
        if ITEM_DIRTY in body_fx:
            body_fx = with_dirty(body_fx)
        body = text_ctrl(name, body_fx, size=13, height=_lines_h("Self.Text", text_w), wrap="true",
                         accessible=f'"{head}: " & Self.Text')
        # Gruppens hoejde laeser tekstens Text, ikke dens Height (check_layout 1).
        body.h = _lines_h(ref, text_w)
        blocks.append(group(f"conVhpMissing{name[len('txtVhpMissing'):]}", [h, body],
                            direction="Vertical", gap=4, visible=f"!IsBlank({ref})"))
    fixed = 26 + 38 + 36 + 3 * 12 + 2 * MODAL_PAD
    natural = stack_height(blocks, 12)
    body = group("conVhpMissingBody", blocks, direction="Vertical", gap=12,
                 height=f"Max(0, Min({natural}, App.Height - 40 - {fixed}))", overflow_y="Scroll")
    close = button("btnVhpMissingClose", '"Close"', MISSING_CLOSE,
                   width=fit_button_width('"Close"'), height=36)
    footer = group("conVhpMissingFooter", [close], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    modal = group("conVhpMissingModal", [title, intro, body, footer], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(MODAL_PAD,) * 4, width=MODAL_W, drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]


# Bjaelkens elementer - samme opbevaring som assemble_screen skal bruge.
CONFIRM = []

# KNAPPERNE I HEADEREN (issue #211)
# ---------------------------------
# Foer stod seks knapper paa een linje (Notes, Edit, Delete, New request,
# Save draft, Submit), og bredden var regnet for fem af dem. I Edit mode
# med noter blev linjen bredere end pladsen, og Submit blev klippet i
# hoejre kant. Nu:
#
#   [+ New request] | [Edit / Update draft] [Submit] [notes] [delete]
#
#   New request   til venstre for en lodret streg - den starter en NY
#                 anmodning og roerer ikke planen, man staar i.
#   Edit          kun i View mode, naar brugeren maa aendre planen.
#   Update draft  kun i Edit mode, foer planen er indsendt. Edit og
#                 Update draft er aldrig synlige samtidig.
#   Submit        den primaere knap, til planen er indsendt. I View mode
#                 staar den graa og siger, at Edit kommer foerst.
#   notes         View notes - kun ikonet, naar planen har noter.
#   delete        Delete request - kun ikonet, sidst og i fare-farven, med
#                 den samme bekraeftelse som foer.
#
# MORE ACTIONS ER FJERNET (issue #230). Menuen (...) indeholdt i praksis
# kun Delete request, saa sletningen laa et klik for dybt. Delete og View
# notes staar nu som ikon-knapper direkte i headeren - samme navne,
# synlighed, DisplayMode, tooltip og bekraeftelse som i menuen.
#
# Er der ikke plads til teksterne, er New request, Edit og Update draft
# kun deres ikon (COMPACT). Submit beholder altid sin tekst. Hvornaar det
# sker, afhaenger kun af skaermbredden - se COMPACT nedenfor.
ICON_BTN = 40
SEP_W = 1
BTN_GAP = 8
# Titlen maa ikke blive smallere end det her, foer knapperne skifter til ikoner.
TITLE_MIN = 220
# Plan-knapperne: Edit og Update draft deler een plads.
PLAN_W = max(EDIT_W, SAVE_W)
# Notes og Delete er to ikon-knapper i enden (issue #230).
FULL_W = NEW_W + SEP_W + PLAN_W + SUB_W + 2 * ICON_BTN + 5 * BTN_GAP
COMPACT_W = ICON_BTN + SEP_W + ICON_BTN + SUB_W + 2 * ICON_BTN + 5 * BTN_GAP
# En telefon har kun plads til EEN af de to: staar Delete der (Edit mode),
# viger View notes - noterne kan stadig laeses i View mode, og et
# returneringsnotat staar i linjen under trinene.
PHONE_W = ICON_BTN + SEP_W + ICON_BTN + SUB_W + ICON_BTN + 4 * BTN_GAP
STEPS_W = len(STEPS) * STEP_W
# Pladsen til titel + knapper paa linjen (trinene og to gaps er trukket fra).
LINE_REST = if_below("Desktop", f"({SHELL_W} - 16)", f"({SHELL_W} - {STEPS_W} - 32)")
COMPACT = f"({below('Tablet')} || {LINE_REST} - {FULL_W} < {TITLE_MIN})"
# Synligheden af planens handlinger - samme betingelser som foer, plus
# status: efter Submit er der intet at gemme eller indsende.
EDIT_VIS = "IfError(varVhpViewOnly && varVhpCanEdit, false)"
DRAFT_VIS = "(!IfError(varVhpViewOnly, true) && !VhpSubmitted)"
SUBMIT_VIS = "(!VhpSubmitted && (!IfError(varVhpViewOnly, true) || IfError(varVhpCanEdit, false)))"
DELETE_VIS = "(!IfError(varVhpViewOnly, true) && !IsBlank(varVhpRequestGuid))"


def _compact(btn, full_w):
    """Tekst og ikon, naar der er plads - ellers kun ikonet."""
    btn.props["Width"] = f"If({COMPACT}, {ICON_BTN}, {full_w})"
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    btn.props["Layout"] = f"If({COMPACT}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    btn.props["AlignInContainer"] = "AlignInContainer.Center"
    return btn


def _icon_only(btn):
    """En kvadratisk ikon-knap i headeren - teksten staar i tooltip og
    tilgaengeligt navn."""
    btn.props["Text"] = '""'
    btn.props["Layout"] = "ButtonLayout.IconOnly"
    btn.props["LayoutMinWidth"] = str(ICON_BTN)
    btn.props["AlignInContainer"] = "AlignInContainer.Center"
    return btn


def _header_actions(notes_vis, notes_fx):
    """View notes og Delete request som ikon-knapper i headeren (issue
    #230). Foer laa de i More actions-menuen (issue #211). Rettigheder,
    synlighed, DisplayMode, tooltip og bekraeftelse er de samme: Delete
    aabner stadig delete_modal (varVhpDeleteOpen) og er graa, mens planen er
    indsendt eller gemmes - tooltippen siger hvorfor."""
    notes = button("btnVhpNotes", '"View notes"', notes_fx,
                   width=ICON_BTN, height=36, icon="Note",
                   accessible='"View the submission notes"',
                   tooltip='"Read the notes added when the plan was submitted"',
                   visible=f"{notes_vis} && !({below('Tablet')} && {DELETE_VIS})")
    blocked = "(VhpSubmitted || varVhpSaving)"
    delete = button("btnVhpDeleteRequest", '"Delete request"', "Set(varVhpDeleteOpen, true)",
                    width=ICON_BTN, height=36, icon="Delete", danger=True,
                    visible=DELETE_VIS, accessible='"Delete this request"',
                    display_mode=f"If({blocked}, DisplayMode.Disabled, DisplayMode.Edit)",
                    tooltip=('If(VhpSubmitted, "A submitted plan cannot be deleted.", '
                             'varVhpSaving, "Saving ... - wait until saving is done.", '
                             '"Delete this draft request - you are asked to confirm first")'))
    return _icon_only(notes), _icon_only(delete)


def build_top_bar():
    """VH-planens topbjaelke - to raekker, saa intet kan klippes:

        [ikon] VH-plan              [+ New request] | [Update draft][Submit][...]
               undertekst
                 (1)-----(2)-----(3)-----(4)
                 Plan    Item    Task    Ready

    Foerste raekke er den SAMME titelbjaelke som paa alle andre sider
    (build_helpers.top_bar), saa ikonet staar det samme sted overalt.
    Trinene staar under den, i fuld bredde og med fast hoejde. Help og tema
    staar i sidebaren. Knapperne: se KNAPPERNE I HEADEREN ovenfor."""
    from build_save import save_buttons, NOTES_OPEN_VIEW, NOTES_HAVE, SAVEABLE_COUNT
    btnDraft, btnSubmit, confirm = save_buttons(CAN_SUBMIT)
    btnNew = button("btnVhpNewRequest", '"New request"',
                    f"If({HAS_UNSAVED}, Set(varVhpConfirmNew, true), {NEW_PLAN_FX})",
                    width=NEW_W, height=36, icon="Add",
                    accessible='"Start a new blank request"',
                    tooltip='"Start a new blank request"')
    _compact(btnNew, NEW_W)
    # Den faelles Edit (build_helpers.edit_button). Den skifter KUN til Edit
    # mode (issue #103): sektionerne er altid foldet ud (issue #192), og Plan
    # Header laases op med sin egen Edit - foer laaste denne knap ogsaa den op.
    btnEdit = edit_button("btnVhpEdit", "varVhpViewOnly", "varVhpCanEdit",
                          "Set(varVhpViewOnly, false)",
                          tooltip='"Switch to Edit mode to change or submit the plan"')
    _compact(btnEdit, EDIT_W)
    confirmNew = confirm_modal(
        "VhpNew", "varVhpConfirmNew", "Start a new request?",
        '"Unsaved work on this request is discarded. Save a draft first to keep it."',
        "Discard and start new", NEW_PLAN_FX, "btnVhpNewConfirm", icon="Add")
    CONFIRM[:] = (confirm + confirmNew + delete_modal("Vhp", "varVhpRequestGuid", _cfg.L_INDEX, "MaintenancePlan")
                  + missing_modal())
    btnNotes, btnDelete = _header_actions(NOTES_HAVE, NOTES_OPEN_VIEW)
    more_vis = f"({NOTES_HAVE} || {DELETE_VIS})"
    btnDraft.props["Text"] = DRAFT_TEXT
    btnDraft.props["AccessibleLabel"] = (
        'If(IsBlank(varVhpPlanKey), "Create the plan as a draft", "Update the saved draft")')
    # Hvorfor knappen er graa - samme betingelser som build_save.DRAFT_DM.
    btnDraft.props["Tooltip"] = (
        "If(\n"
        "    varVhpSaving, \"Saving ...\",\n"
        "    !varVhpPlanCommitted, \"Save the plan header first - then you can create the draft.\",\n"
        f"    {SAVEABLE_COUNT} = 0, \"Add at least one item with a short text or functional location first.\",\n"
        "    IsBlank(varVhpPlanKey), \"Not saved yet. Create a draft so you can come back to it.\",\n"
        "    \"Saved as draft \" & varVhpPlanKey & \". Update draft saves your changes to the same plan, items and operations.\"\n"
        ")")
    btnDraft.props["Visible"] = btnDraft.vis = DRAFT_VIS
    focus_border(btnDraft, (4,), C_CARD_BORDER)
    _compact(btnDraft, SAVE_W)
    btnSubmit.props["Width"] = str(SUB_W)
    btnSubmit.props["LayoutMinWidth"] = str(SUB_W)
    btnSubmit.props["AlignInContainer"] = "AlignInContainer.Center"
    btnSubmit.props["Tooltip"] = _submit_tooltip()
    btnSubmit.props["Visible"] = btnSubmit.vis = SUBMIT_VIS
    # Stregen mellem New request og planens handlinger.
    sep = group("conVhpHeadSep", [], direction="Horizontal", height=24, width=str(SEP_W),
                fill=C_DIVIDER, layout_min_width=SEP_W,
                visible=f"{EDIT_VIS} || {DRAFT_VIS} || {SUBMIT_VIS} || {more_vis}")
    sep.props["AlignInContainer"] = "AlignInContainer.Center"
    title_bar = top_bar("Vhp", '"Maintenance Plan"', SUBTITLE, [], icon="vhplan", mode_var="varVhpViewOnly",
                     num_var="varVhpPlanKey")
    # Nye navne: Studio beholdt bjaelkens gamle tilstand paa conVhpBar fra foer redesignet.
    title_bar.name = "conVhpTitleRow"
    title_bar.children[1].name = "conVhpTitleText"
    title_bar.props["AlignInContainer"] = "AlignInContainer.Center"
    title_bar.children[1].props["AlignInContainer"] = "AlignInContainer.Center"

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
    # BREDDERNE (issue #211). Knapperne faar praecis den plads, de bruger
    # (FULL_W eller COMPACT_W), og titlen resten. Trinene staar midt paa
    # linjen, naar der er plads til det: saa er knapblokken lige saa bred
    # som titlen. Ingen af bredderne kan tilsammen blive bredere end linjen.
    btn_w = f"If({below('Tablet')}, {PHONE_W}, {COMPACT}, {COMPACT_W}, {FULL_W})"
    side_w = if_below("Desktop", btn_w, f"Max({btn_w}, {LINE_REST} / 2)")
    title_bar.props["Width"] = if_below("Tablet", "56", f"{LINE_REST} - {side_w}")
    title_bar.props["LayoutMinWidth"] = "0"
    btns = group("conVhpHeadBtns", [btnNew, sep, btnEdit, btnDraft, btnSubmit,
                                       btnNotes, btnDelete],
                 direction="Horizontal", gap=BTN_GAP, height=44, width=side_w,
                 justify="End", align_items="Center")
    btns.props["LayoutMinWidth"] = btns.props["Width"]
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
