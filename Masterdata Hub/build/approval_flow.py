# -*- coding: utf-8 -*-
"""
Approval flow of a VH plan on the hub: the stage strip in the list and the
popup that opens from it.

Source of truth is MD_ApprovalLog (one row per decision, written by the flows
BioSap-VhPlan-SystemApproval / CostApproval / QualityReview / ToMasterData).
MD_Approver only says who is asked: key = system number, plant code or COST;
Approver1 decides, Approver2 when Approver1Absent. docs/32-godkendelsesflow.md.

Stages, in order:
  System   one approver per item, items run in parallel
  Cost     one approver (COST) per item, items run in parallel
  Quality  one approver for the whole plan (the plant)
  SAP      Master Data creates the plan; no approval, read from the index status

A stage is complete when every expected decision exists. An item decided twice
(Return, then Approve after a fix) counts by its latest row. There is no
"Rejected" in the process: an approver can only Approve or Return.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_OVERLAY, C_MODAL_BG, C_PRIMARY_SOFT, C_MUTED, C_TITLE,
                        C_MUTED_BG, C_TRANSPARENT, C_PRIMARY, C_INFO_BG, C_INFO_FG,
                        C_WARN_FG, C_WARN_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_VALID_BG,
                        C_INVALID_FG, C_INVALID_BG, C_CARD_BORDER, C_ROW_HOVER, C_ROW_PRESSED)
from build_helpers import group, text_ctrl, button, grow, spinner_svg, row_hit, text_px, text_input
from hub_config import DOMAINS
from design_tokens import ref_hex
import icons
import layout_tokens as lay
import admin_log as alog
import submission_notes as sn
import display_text as dt
from layout_tokens import if_below, at_least

OPEN = "IfError(varMdAprOpen, false)"
CLOSE = "Set(varMdAprOpen, false)"
ROW_H = 48
MAX_ROWS = 11
POP_MAX_W = 720
POP_PAD = 16
SVG_FONT = "font-family='Segoe UI, sans-serif'"

STAGES = [
    ("System", "System approval", "S1"),
    ("Cost", "Cost approval", "S2"),
    ("Quality", "Quality review", "S3"),
]
# Farverne paa forloebets knuder og striben i listen (SVG, derfor hex).
# Badgefarverne staar ved popuppen (BADGE_FG/BADGE_BG). "Admin": en admins
# aendring i en andens anmodning (tools/admin_log.py) - samme advarselsfarve
# som Returned, saa den skiller sig ud i forloebet.
STATE_HEX = {"Approved": "state-ok-fg", "Done": "state-ok-fg", "Skipped": "state-neutral-fg",
             "In progress": "state-info-fg", "Returned": "state-warn-fg",
             "Pending": "text-muted", "Admin": "state-warn-fg", "Note": "color-brand-primary"}
# Kun popuppens tidslinje kan vise en lukket anmodnings udfald.
RAIL_HEX = {**STATE_HEX, "Rejected": "state-error-fg", "Cancelled": "state-neutral-fg"}
PASSED = '(%s = "Approved" || %s = "Skipped" || %s = "Done")'


def _switch(value, table, fallback):
    body = ",\n    ".join(f'"{k}", {v}' for k, v in table.items())
    return f"Switch(\n    {value},\n    {body},\n    {fallback}\n)"


def _hex_switch(value):
    return _switch(value, {k: ref_hex(t) for k, t in STATE_HEX.items()}, ref_hex("text-muted"))


# ---------------------------------------------------------------------------
# State logic - one definition, used by the strip and by the popup.
# ---------------------------------------------------------------------------
def latest(log, stage):
    """The latest decision per item for one stage (per plan for Quality)."""
    s = f'Filter({log}, Stage = "{stage}")'
    newest = 'SortByColumns(%s, "DecidedOn", SortOrder.Descending)'
    if stage == "Quality":
        return f"FirstN({newest % s}, 1)"
    return (f'ForAll(GroupBy({s}, ItemGuid, colgrp), '
            f'First(SortByColumns(colgrp, "DecidedOn", SortOrder.Descending)))')


def expected(stage, req):
    return "1" if stage == "Quality" else f"Max(1, {req}.ItemCount)"


def stage_state(table, exp, prev):
    """Returned > Skipped > Approved > In progress > Pending."""
    return ("With({T: %s}, With({n: CountRows(T), r: CountRows(Filter(T, Decision = \"Return\")), "
            "k: CountRows(Filter(T, Decision = \"Skipped\"))}, If(\n"
            "    r > 0, \"Returned\",\n"
            "    n > 0 && n >= %s && k = n, \"Skipped\",\n"
            "    n > 0 && n >= %s, \"Approved\",\n"
            "    n > 0, \"In progress\",\n"
            "    %s, \"In progress\",\n"
            "\"Pending\"\n)))") % (table, exp, exp, "true" if prev == "true" else PASSED % ((prev,) * 3))


def sap_state(req):
    return (f'Switch({req}.Status.Value, "OprettetISAP", "Done", "KlarTilSAP", "In progress", '
            f'"Pending")')


def applies(req):
    return f'{req}.Domain.Value = "MaintenancePlan" && {req}.Status.Value <> "Kladde"'


# ---------------------------------------------------------------------------
# The strip in the list row: four nodes on a line, coloured by state.
# ---------------------------------------------------------------------------
STRIP_W, STRIP_H = 270, 30


NOT_STARTED = (
    '"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'%d\' height=\'%d\' viewBox=\'0 0 %d %d\'>'
    '<text x=\'4\' y=\'19\' %s font-size=\'12\' fill=\'" & %s & "\'>Not required</text></svg>"'
    % (STRIP_W, STRIP_H, STRIP_W, STRIP_H, SVG_FONT, ref_hex("text-muted")))


# GODKENDELSESLOGGEN HENTES EEN GANG (2026-10-05)
#
# Striben i listen stod som Filter(MD_ApprovalLog, RequestGuid =
# ThisItem.RequestGuid) i HVER raekke - og i to kontroller (bred og
# kompakt). Det var et kald pr. synlig VH-plan, to hvis begge blev
# evalueret. Nu hentes de tre godkendelsestrins raekker een gang, naar
# hubben vises (build_hub.HUB_ON_VISIBLE), og striben laeser samlingen.
# Stage er indekseret, og Or paa lighed delegeres til SharePoint. Nyeste
# foerst: rammer listen appens data row limit, er det de AELDSTE
# beslutninger, der mangler - og for en raekke uden beslutninger i
# samlingen spoerges der saa direkte, som foer.
#
# EN VARIABEL, IKKE EN SAMLING (issue #165): tabellen hentes paany ved
# hver visning, men aendres aldrig imellem. App checker meldte samlingen
# (CollectingReadOnlyTable) - en samling koster ekstra sporing, som en
# variabel ikke har. Samme kald, samme tidspunkt, samme raekker.
LOG_LIMIT = 500   # appens Data row limit (som build_hub.ROW_LIMIT)
LOG_REFRESH = ('Set(varMdAprAll, SortByColumns(Filter(MD_ApprovalLog, '
               'Stage = "System" || Stage = "Cost" || Stage = "Quality"), "ID", '
               'SortOrder.Descending))')
ROW_LOG = ('With({ c: Filter(varMdAprAll, RequestGuid = ThisItem.RequestGuid) }, '
           f'If(IsEmpty(c) && CountRows(varMdAprAll) >= {LOG_LIMIT}, '
           'Filter(MD_ApprovalLog, RequestGuid = ThisItem.RequestGuid), c))')


# Knuderne i striben (issue #139): r 6 i stedet for 4, saa der er plads til
# et symbol. Stregen er 1,6 px paa skaermen ved et 12 px symbol.
NODE_R = 6
NODE_STROKE = 3.2


def _strip_glyph(value):
    """Symbolet for en knude i striben - de tilstande, striben kan have."""
    states = ("Approved", "Done", "Skipped", "In progress", "Returned")
    return ("Switch(%s, " % value
            + ", ".join('"%s", "%s"' % (k, icons.WORKFLOW[k]) for k in states)
            + ', "%s")' % icons.WORKFLOW_DEFAULT)


def row_svg():
    """Power Fx text for the strip's SVG, or "" when the request has no approval flow."""
    req = "ThisItem"
    xs = [33, 99, 165, 231]
    names = ["System", "Cost", "Quality", "SAP"]
    var = ["a", "b", "c", "d"]
    parts = ['"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'%d\' height=\'%d\' '
             'viewBox=\'0 0 %d %d\'>"' % (STRIP_W, STRIP_H, STRIP_W, STRIP_H)]
    y = 23
    for i in range(3):
        parts.append(
            f'"<line x1=\'{xs[i]}\' y1=\'{y}\' x2=\'{xs[i + 1]}\' y2=\'{y}\' stroke-width=\'2\' '
            f'stroke-linecap=\'round\' stroke=\'" & If({PASSED % ((var[i],) * 3)}, '
            f'{ref_hex("state-ok-fg")}, {ref_hex("border-default")}) & "\'/>"')
    for i, nm in enumerate(names):
        col = _hex_switch(var[i])
        hollow = f'{var[i]} = "Pending"'
        parts.append(
            f'"<circle cx=\'{xs[i]}\' cy=\'{y}\' r=\'{NODE_R}\' stroke-width=\'1.5\' stroke=\'" & {col} & '
            f'"\' fill=\'" & If({hollow}, "none", {col}) & "\'/>"')
        # Symbolet i knuden (issue #139): farven alene skiller ikke Approved
        # fra In progress. Samme symboler som popuppens tidslinje.
        parts.append(
            f'If({hollow}, "", "<g transform=\'translate({xs[i] - NODE_R} {y - NODE_R}) '
            f'scale({NODE_R / 12:g})\' fill=\'none\' stroke=\'" & {ref_hex("text-on-primary")} & '
            f'"\' stroke-width=\'{NODE_STROKE:g}\' stroke-linecap=\'round\' stroke-linejoin=\'round\'>'
            f'<path d=\'" & {_strip_glyph(var[i])} & "\'/></g>")')
        parts.append(
            f'"<text x=\'{xs[i]}\' y=\'12\' text-anchor=\'middle\' {SVG_FONT} font-size=\'11\' '
            f'font-weight=\'600\' fill=\'" & {col} & "\'>{nm}</text>"')
    parts.append('"</svg>"')
    body = " &\n".join(parts)

    def pick(stage):
        return latest("L", stage)

    inner = (
        f"With({{a: {stage_state(pick('System'), expected('System', req), 'true')}}},\n"
        f"With({{b: {stage_state(pick('Cost'), expected('Cost', req), 'a')}}},\n"
        f"With({{c: {stage_state(pick('Quality'), expected('Quality', req), 'b')}}},\n"
        f"With({{d: {sap_state(req)}}},\n{body}))))")
    return ("If(\n    !(" + applies(req) + '), ' + NOT_STARTED + ',\n'
            f"    With(\n        {{ L: {ROW_LOG} }},\n"
            f"        {inner}\n    )\n)")


# ---------------------------------------------------------------------------
# Opening the popup: build the collections the gallery reads.
# ---------------------------------------------------------------------------
R = "varMdAprReq"
# EEN RAEKKEMODEL FOR BEGGE POPUPS (issue #90)
#
#   Kind   H = trinoverskrift (kun Approval flow), D = haendelse/beslutning,
#          X = fortsaettelseslinje, naar en raekke er foldet ud (smal skaerm)
#   Title  overskriftens navn (H) - eller AKTOEREN (D): et bruger-id
#          (UFFES) eller en automatisk afsender (SYSTEM, Master Data)
#   Act    handlingen eller rollen ved siden af aktoeren
#   Sub    stoettende detaljer (kommentar, detalje, item) - egen linje
#   Stamp  tidsstemplet - egen kolonne til hoejre, ikke en del af Sub
#   Human  true = en bestemt bruger handlede: personikon og fast kort.
#          false = automatisk/system: intet ikon, stiplet kort, rude i
#          tidslinjen. Afgjort af de vaerdier, flowene faktisk skriver:
#          DecidedByEmail er "system" (uden @) for automatiske raekker.
COLS = ("Kind", "Stage", "Title", "State", "Label", "Rule", "Cur", "Sub", "Act", "Stamp", "Human")
_DEFAULTS = {"Cur": "false", "Human": "false"}


def _rec(**f):
    vals = []
    for c in COLS:
        v = f.get(c, _DEFAULTS.get(c, '""'))
        vals.append(f"{c}: {v}")
    return "{ " + ", ".join(vals) + " }"


def _q(s):
    return '"%s"' % s


INDEX_ROWS = [
    "ClearCollect(colMdAprTmp, colMdAprRows)",
    "ClearCollect(colMdAprRows, ForAll(Sequence(CountRows(colMdAprTmp)) As S, "
    "With({ q: Index(colMdAprTmp, S.Value) }, { " + ", ".join(f"{c}: q.{c}" for c in COLS) +
    ", Idx: S.Value, L1: \"\", L2: \"\", IsLast: false })))",
]


_RULES = {
    "System": '"One approver per item - " & Max(1, %s.ItemCount) & If(Max(1, %s.ItemCount) = 1, '
              '" item", " items in parallel") & ", all must pass"' % (R, R),
    "Cost": '"One approver per item - items under the threshold are skipped, all must pass"',
    "Quality": '"One approver for the whole plan - the plant"',
}

STAMP = '"dd-mm-yyyy hh:mm"'


def _who(email):
    """Bruger-id af en e-mail: delen foer @, med store bogstaver
    (uffes@orsted.com -> UFFES). En vaerdi uden @ (et id som PKBJE i
    MD_Approver, eller "system") bliver blot til store bogstaver."""
    return f'Upper(First(Split(Coalesce({email}, "unknown"), "@")).Value)'


def _by(text):
    """LastActionBy er en e-mail, naar appen skrev den, og et navn, naar et
    flow gjorde ("Quality review", "SAP"). Kun e-mailen goeres til id;
    navnet vises paa engelsk (aeldre raekker: "systemgodkendelsen", #162)."""
    return f'If("@" in Coalesce({text}, ""), {_who(text)}, {dt.log(text)})'


# Trinets navn i aktivitetsloggen. Stage-vaerdierne er dem, flowene og
# appen skriver i MD_ApprovalLog (SapCreated: ToMasterData/SapReceipt,
# Admin: tools/admin_log.py); en ukendt vaerdi vises som den er.
STAGE_ACT = {"System": "System approval", "Cost": "Cost approval", "Quality": "Quality review",
             "SapCreated": "Creation in SAP", alog.STAGE: "Admin change"}


def _decision_rows(stage, tbl, timeline=False):
    state = ('Switch(Decision, "Approve", "Approved", "Skipped", "Skipped", '
             f'"{alog.EDIT}", "Admin", "{alog.DELETE}", "Admin", "Returned")')
    label = (f'Switch(Decision, "{alog.EDIT}", "Admin edit", "{alog.DELETE}", "Admin delete", '
             f'{state})')
    # Detail (og ItemText) er flowets tekst og vises paa engelsk (#162).
    # Comment er godkenderens egen tekst og vises som den er - undtagen naar
    # flowet har skrevet sin egen tekst i begge (fx en FL-fejl).
    note = ('If(!IsBlank(Comment) && Comment <> Coalesce(Detail, ""), '
            f'Substitute(Comment, Char(10), " "), {dt.log("Detail")})')
    item = dt.log("ItemText")
    if timeline:
        act = ("Switch(Stage, " + ", ".join(f'"{k}", "{v}"' for k, v in STAGE_ACT.items()) +
               ", Stage)")
        sub = (f'With({{ n: {note} }}, If(IsBlank(ItemText), n, '
               f'{item} & If(IsBlank(n), "", "  ·  " & n)))')
    else:
        act = '"Whole plan"' if stage == "Quality" else item
        sub = note
    rec = _rec(Kind=_q("D"), Stage=_q(stage), Title=_who("DecidedByEmail"), State=state,
               Label=label, Sub=sub, Act=act, Stamp=f"Text(DecidedOn, {STAMP})",
               Human='"@" in Coalesce(DecidedByEmail, "")')
    return f'ForAll(SortByColumns({tbl}, "DecidedOn"), {rec})'


def _waiting_row(stage, svar):
    n = f'CountRows(Filter(colMdAprLatest, Stage = "{stage}"))'
    exp = expected(stage, R)
    if stage == "System":
        rec = _rec(Kind=_q("D"), Stage=_q(stage), Title='"System manager of each item"',
                   State=_q("Pending"), Label=_q("Awaiting"),
                   Sub=f'({exp} - {n}) & " of " & {exp} & " awaiting a decision"')
        return f'If({svar} = "In progress" && {n} < {exp}, Collect(colMdAprRows, {rec}))'
    # Godkenderen slaas op EEN gang - og kun naar trinet venter.
    key = '"COST"' if stage == "Cost" else f"Upper(Left({R}.Plant, 3))"
    who = (f'If(IsBlank(a), "Approver not set", '
           f'{_who("If(a.Approver1Absent, a.Approver2, a.Approver1)")})')
    act = 'If(IsBlank(a), "", If(a.Approver1Absent, "2nd approver", "1st approver"))'
    sub = (f'If(IsBlank(a), "No row in MD_Approver for " & {key}, '
           'If(a.Approver1Absent, "1st approver absent", ""))')
    rec = _rec(Kind=_q("D"), Stage=_q(stage), Title=who, State=_q("Pending"), Label=_q("Awaiting"),
               Sub=sub, Act=act, Human="!IsBlank(a)")
    return (f'If({svar} = "In progress" && {n} < {exp}, '
            f'With({{a: LookUp(MD_Approver, ApproverKey = {key})}}, Collect(colMdAprRows, {rec})))')


META_FX = (
    "Concat(\n"
    "    Filter(\n"
    "        Table(\n"
    '            { v: If(!IsBlank(%(r)s.RequesterEmail), "Requested by " & %(who)s) },\n'
    "            { v: If(%(r)s.ItemCount > 0, Text(%(r)s.ItemCount) &\n"
    '                    If(%(r)s.ItemCount = 1, " item", " items")) },\n'
    '            { v: If(!IsBlank(%(r)s.SapObjectNo), "SAP " & %(r)s.SapObjectNo) },\n'
    '            { v: If(!IsBlank(%(r)s.LastActionBy), "last change by " & %(by)s) }\n'
    "        ),\n"
    "        !IsBlank(v)\n"
    "    ),\n"
    "    v,\n"
    '    "  ·  "\n'
    ")"
) % {"r": R, "who": _who(R + ".RequesterEmail"),
       "by": _by(R + ".LastActionBy")}

IS_TIMELINE = 'IfError(varMdAprMode, "") = "T"'


def _status_label(value):
    """Den engelske etiket for en statusvaerdi (tools/display_text.py)."""
    return dt.status(value)


# NOTERNE VED INDSENDELSEN (issue #115) - en haendelse i Activity, ikke en
# kommentar eller en beslutning. Raekken viser kun, AT der er noter, og
# hvilke brugeren maa se; teksten aabnes fra raekken (sn.hub_open_fx).
# Planen slaas op een gang og kun, naar der er en note at vise.
NOTE_STAGE = "N"


def _notes_row():
    show_a = f"{R}.{sn.FLAG} && {sn.hub_may_approver(R)}"
    show_s = f"{sn.has_self(R + '.RequestGuid', 'varMdSelfNotes')} && {sn.hub_may_self(R)}"
    which = (f'Concat(Filter(Table({{ v: If({show_a}, "{sn.T_APPROVER}", "") }}, '
             f'{{ v: If({show_s}, "{sn.T_SELF}", "") }}), !IsBlank(v)), v, " and ")')
    rec = _rec(Kind=_q("D"), Stage=_q(NOTE_STAGE),
               Title=_who(f"Coalesce(p.{sn.COL_BY}, {R}.RequesterEmail)"),
               Act=_q("Added submission notes"), State=_q("Note"), Label=_q("Notes"),
               Sub=f'{which} & " - select to read"',
               Stamp=f"Text(p.SubmittedOn, {STAMP})", Human="true")
    return (f'If({R}.Domain.Value = "MaintenancePlan" && (({show_a}) || ({show_s})), '
            f"With({{ p: LookUp({sn.PLANS}, ID = {R}.SourceItemId) }}, "
            f"Collect(colMdAprRows, {rec})))")


def timeline_fx():
    """Activity of one request. One filtered query. For plans it holds the
    approvals; for every domain it holds an admin's changes (Stage "Admin",
    tools/admin_log.py) - so it is read for all domains, not only plans."""
    st = f"{R}.Status.Value"
    lines = [
        "Set(varMdAprBusy, true)",
        "Set(varMdAprExp, 0)",
        "Set(varMdAprExtra, 0)",
        'Set(varMdAprMode, "T")',
        "Set(varMdAprOpen, true)",
        f"Set({R}, ThisItem)",
        "ClearCollect(colMdAprLog, Filter(MD_ApprovalLog, RequestGuid = ThisItem.RequestGuid))",
        "ClearCollect(colMdAprRows, " + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=_who(R + ".RequesterEmail"),
            Act=_q("Created the request"), State=_q("Done"), Label=_q("Created"),
            Stamp=f"Text({R}.Created, {STAMP})", Human="true") + ")",
        _notes_row(),
        "Collect(colMdAprRows, " + _decision_rows("T", "colMdAprLog", timeline=True) + ")",
        f'If(!IsBlank({R}.SapObjectNo), Collect(colMdAprRows, ' + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=_q("SAP"), Act=_q("Created in SAP"),
            State=_q("Done"), Label=_q("Created"), Sub=f'"SAP " & {R}.SapObjectNo') + "))",
        f'If({R}.IsOpen && !IsBlank({R}.AssignedToEmail), Collect(colMdAprRows, ' + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=_who(R + ".AssignedToEmail"),
            Act=_q("Assigned to"), State=_q("In progress"), Label=_q("Waiting"),
            Human="true") + "))",
        "Collect(colMdAprRows, " + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=_q("Status"), Act=_status_label(st),
            State=f'If({R}.IsOpen, "In progress", {st} = "Afvist", "Rejected", '
                  f'{st} = "Annulleret", "Cancelled", "Done")',
            Label=f'If({R}.IsOpen, "Open", "Closed")',
            Stamp=f"Text({R}.LastActionOn, {STAMP})",
            Sub=f'If(IsBlank({R}.LastActionBy), "Last change", '
                f'"Last change by " & {_by(R + ".LastActionBy")})') + ")",
        *INDEX_ROWS,
        "Set(varMdAprBusy, false)",
    ]
    return ";\n".join(lines)


def open_fx():
    log = "colMdAprLog"
    lines = [
        "Set(varMdAprBusy, true)",
        "Set(varMdAprExp, 0)",
        "Set(varMdAprExtra, 0)",
        'Set(varMdAprMode, "A")',
        "Set(varMdAprOpen, true)",
        f"Set({R}, ThisItem)",
        # Note to approver (issue #115): kun naar der er en, og brugeren maa se den.
        f'Set(varMdAprNote, If({R}.{sn.FLAG} && {sn.hub_may_approver(R)}, '
        f'Coalesce(LookUp({sn.PLANS}, ID = {R}.SourceItemId).{sn.COL_APPROVER}, ""), ""))',
        f"ClearCollect({log}, Filter(MD_ApprovalLog, RequestGuid = ThisItem.RequestGuid))",
    ]
    for i, (stage, _t, _v) in enumerate(STAGES):
        verb = "ClearCollect" if i == 0 else "Collect"
        lines.append(f"{verb}(colMdAprLatest, {latest(log, stage)})")
    prev = "true"
    for stage, _t, v in STAGES:
        tbl = f'Filter(colMdAprLatest, Stage = "{stage}")'
        lines.append(f"Set(varMdApr{v}, {stage_state(tbl, expected(stage, R), prev)})")
        prev = f"varMdApr{v}"
    lines.append(f"Set(varMdAprS4, {sap_state(R)})")
    lines.append(
        'Set(varMdAprCur, If(varMdAprS1 = "In progress" || varMdAprS1 = "Returned", "System", '
        'varMdAprS2 = "In progress" || varMdAprS2 = "Returned", "Cost", '
        'varMdAprS3 = "In progress" || varMdAprS3 = "Returned", "Quality", '
        'varMdAprS4 = "In progress", "SAP", ""))')
    for i, (stage, title, v) in enumerate(STAGES):
        sv = f"varMdApr{v}"
        lines.append(("ClearCollect" if i == 0 else "Collect") + "(colMdAprRows, " + _rec(
            Kind=_q("H"), Stage=_q(stage), Title=_q(title), State=sv, Label=sv, Rule=_RULES[stage],
            Cur=f'varMdAprCur = "{stage}"') + ")")
        lines.append("Collect(colMdAprRows, " +
                     _decision_rows(stage, f'Filter(colMdAprLatest, Stage = "{stage}")') + ")")
        lines.append(_waiting_row(stage, sv))
    lines.append("Collect(colMdAprRows, " + _rec(
        Kind=_q("H"), Stage=_q("SAP"), Title=_q("Creation in SAP"), State="varMdAprS4",
        Label="varMdAprS4", Rule=_q("Master Data creates the plan - no approval"),
        Cur='varMdAprCur = "SAP"') + ")")
    lines.append(
        'If(varMdAprS4 <> "Pending", Collect(colMdAprRows, ' + _rec(
            Kind=_q("D"), Stage=_q("SAP"), Title=_q("Master Data"), State="varMdAprS4",
            Label='If(varMdAprS4 = "Done", "Created", "Awaiting")',
            Act='If(varMdAprS4 = "Done", "Created the plan", "Ready - waiting for creation in SAP")',
            Sub=f'If(varMdAprS4 = "Done", "SAP " & {R}.SapObjectNo, "")')
        + "))")
    lines.extend(INDEX_ROWS)
    lines.append("Set(varMdAprBusy, false)")
    return ";\n".join(lines)


def strip_hits(act_width, x_expr, compact=None):
    """One pill-shaped hit zone over the whole strip; the stages only show status."""
    t = C_TRANSPARENT
    hit_h = 40
    props = {
        "Align": "Align.Right",
        "BorderColor": t, "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Color": t, "Fill": t, "Font": "Font.'Segoe UI'", "Size": "16",
        "FocusedBorderColor": C_PRIMARY, "FocusedBorderThickness": "2",
        "Height": str(hit_h),
        "HoverBorderColor": t, "HoverColor": C_MUTED, "HoverFill": C_ROW_HOVER,
        "OnSelect": open_fx(),
        "PaddingRight": "8", "PaddingLeft": "0", "PaddingTop": "0", "PaddingBottom": "0",
        "PressedBorderColor": t, "PressedColor": C_PRIMARY, "PressedFill": C_ROW_PRESSED,
        "RadiusBottomLeft": "20", "RadiusBottomRight": "20", "RadiusTopLeft": "20",
        "RadiusTopRight": "20",
        "TabIndex": "0",
        "Text": '"\u203a"',
        "Visible": f"({applies('ThisItem')}) && {at_least('Tablet')}",
        "Width": str(act_width), "X": x_expr,
        "Y": f"(Parent.TemplateHeight - 1 - {hit_h}) / 2",
    }
    if compact:
        props["Width"] = if_below("Wide", f"({compact['zone']}) * 4", str(act_width))
        props["X"] = if_below("Wide", compact["x"], x_expr)
        props["Y"] = if_below("Wide", compact["y"], props["Y"])
    return [Ctrl("btnMdRowApproval", "Classic/Button", props=props, h=hit_h, vis=props["Visible"])]


# ---------------------------------------------------------------------------
# The popups: Approval flow (Mode "A") and Activity (Mode "T") are the SAME
# component (issue #90) - one header with the title and a request-number
# badge in the domain's colour, one rail, one row layout, one badge system.
# What differs is the content: Approval flow groups decisions under a
# header per stage; Activity is a flat, chronological list of events.
#
# Row layout (D rows), left to right:
#   rail  | [person icon] ACTOR  action          | timestamp | [ BADGE ]
#         |   supporting details (own line)      |  column   |  column
# Badge and timestamp are vertically centred in the row; both sit in fixed
# right-hand columns, so they line up from row to row. Below Tablet there
# is no room for the timestamp column: it leads the details line instead.
# ---------------------------------------------------------------------------
POP_W = f"Min({POP_MAX_W}, App.Width - 24)"
GW = f"({POP_W} - {2 * POP_PAD})"
TW = f"({GW} - 20)"
CHIP_W = 92
CHIP_H = 22
STAMP_W = 104
LX = 48            # where the row text starts (card at 38 + 10 padding)
ICON_W = 16
PERSON = icons.PERSON

# Badge colours, by State. One table for both popups. Tinted background,
# readable foreground - no solid fills:
#   green     Approved, Done (Created, Closed)
#   blue      In progress (Open, Waiting)
#   blue-grey Pending (Awaiting) - blue text on the neutral tint
#   grey      Skipped, Cancelled
#   amber     Returned, Admin
#   red       Rejected
BADGE_FG = {"Approved": C_VALID_FG, "Done": C_VALID_FG, "Skipped": C_MUTED,
            "Cancelled": C_MUTED, "In progress": C_INFO_FG, "Returned": C_WARN_FG,
            "Pending": C_INFO_FG, "Admin": C_WARN_FG, "Rejected": C_INVALID_FG,
            "Note": C_TITLE}
BADGE_BG = {"Approved": C_VALID_BG, "Done": C_VALID_BG, "Skipped": C_MUTED_BG,
            "Cancelled": C_MUTED_BG, "In progress": C_INFO_BG, "Returned": C_WARN_BG,
            "Pending": C_NEUTRAL_BG, "Admin": C_WARN_BG, "Rejected": C_INVALID_BG,
            "Note": C_PRIMARY_SOFT}


def _rail_svg():
    col = _switch("ThisItem.State", {k: ref_hex(t) for k, t in RAIL_HEX.items()}, ref_hex("text-muted"))
    c = ROW_H // 2
    line = ref_hex("border-default")
    # Symbolet i knuden: tools/icons.WORKFLOW (issue #139) - hver tilstand
    # sit eget, ogsaa Rejected, Cancelled og Pending, der foer kun var en prik.
    node_glyph = _switch(
        "ThisItem.State",
        {k: '"%s"' % v for k, v in icons.WORKFLOW.items()},
        '"%s"' % icons.WORKFLOW_DEFAULT)
    head = (f'"<circle cx=\'16\' cy=\'{c}\' r=\'11\' fill=\'" & {col} & "\'/>'
            f'<g transform=\'translate(4 {c - 12})\' fill=\'none\' stroke=\'" & {ref_hex("text-on-primary")} & '
            f'"\' stroke-width=\'2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'><path d=\'" & '
            f'{node_glyph} & "\'/></g>"')
    fill = f'If(ThisItem.State = "Pending", "none", {col})'
    # Een bruger handlede: en prik. Automatisk/system: en rude - samme
    # farve, anden form, saa forskellen ikke kun er farven.
    marker = (f'If(ThisItem.Human, "<circle cx=\'16\' cy=\'{c}\' r=\'5\' stroke-width=\'2\' stroke=\'" & '
              f'{col} & "\' fill=\'" & {fill} & "\'/>", '
              f'"<rect x=\'12\' y=\'{c - 4}\' width=\'8\' height=\'8\' rx=\'1\' '
              f'transform=\'rotate(45 16 {c})\' stroke-width=\'2\' stroke=\'" & {col} & '
              f'"\' fill=\'" & {fill} & "\'/>")')
    dot = (f'"<line x1=\'16\' y1=\'{c}\' x2=\'30\' y2=\'{c}\' stroke=\'" & {line} & "\' stroke-width=\'1.5\'/>" & '
           f'{marker}')
    svg = ('"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'32\' height=\'%d\' viewBox=\'0 0 32 %d\'>'
           '<line x1=\'16\' y1=\'0\' x2=\'16\' y2=\'%d\' stroke=\'" & %s & "\' stroke-width=\'2\'/>"'
           ' & If(ThisItem.Kind = "H", %s, If(ThisItem.Kind = "X", "", %s)) & "</svg>"') % (ROW_H, ROW_H, ROW_H, line, head, dot)
    return f'"data:image/svg+xml;utf8," & EncodeUrl({svg})'


def _is(kind):
    return f'ThisItem.Kind = "{kind}"'


def _number_badge(name):
    """The request number as the request app shows it (build_helpers.
    number_badge): a 88 x 26 pill in the domain's colour on a 12 % tint
    of it. The colour follows the request's domain - the same tokens as
    the hub's domain icons (hub_config.DOMAINS)."""
    col = ("Switch(" + R + ".Domain.Value, " +
           ", ".join(f'"{d["key"]}", {ref_hex(d["token"])}' for d in DOMAINS) +
           f', {ref_hex("text-muted")})')
    svg = ('"data:image/svg+xml;utf8," & EncodeUrl("<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'88\' '
           'height=\'26\' viewBox=\'0 0 88 26\'><rect width=\'88\' height=\'26\' rx=\'13\' fill=\'" & c & '
           '"\' fill-opacity=\'0.12\'/><text x=\'44\' y=\'17.5\' text-anchor=\'middle\' '
           'font-family=\'Segoe UI, sans-serif\' font-size=\'12\' font-weight=\'600\' fill=\'" & c & '
           '"\'>" & ' + R + '.RequestNo & "</text></svg>")')
    return Ctrl(name, "Image", props={
        "AccessibleLabel": f'"Request " & {R}.RequestNo',
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0", "Fill": C_TRANSPARENT,
        "Height": "26", "Image": f'If(IsBlank({R}.RequestNo), "", With({{ c: {col} }}, {svg}))',
        "ImagePosition": "ImagePosition.Fit", "LayoutMinWidth": "88",
        "OnSelect": "false", "TabIndex": "0", "Width": "88",
    }, h=26)


NOTE_IN_H = 76


def _note_panel(busy):
    """Note to approver i Approval flow (issue #115): over trinene, saa
    godkenderen laeser den foer en beslutning - i sin egen ramme, adskilt
    fra beslutningernes kommentarer og forloebet. Note to self vises
    aldrig her."""
    vis = f'!{busy} && !({IS_TIMELINE}) && !IsBlank(IfError(varMdAprNote, ""))'
    t = text_ctrl("txtMdAprNoteTitle", f'"{sn.T_APPROVER}"', size=14, weight="Semibold",
                  color=C_PRIMARY, height=20, wrap="false")
    hint = text_ctrl("txtMdAprNoteHint", '"From the requester, added at submission."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=17, wrap="false")
    body = text_input("inpMdAprNote", 'IfError(varMdAprNote, "")', height=NOTE_IN_H,
                      ttype="Multiline", display_mode="DisplayMode.View", label=f'"{sn.T_APPROVER}"')
    panel = group("conMdAprNote", [t, hint, body], direction="Vertical", gap=4,
                  border_color=C_PRIMARY, radius=8, pad=(10, 12, 10, 12), width=GW, visible=vis)
    return panel, vis, panel.h


def build_popup():
    n = lambda kind, base: f"{kind}MdApr{base}"
    narrow = lay.below("Tablet")
    wide = lay.at_least("Tablet")
    exp = "IfError(varMdAprExp, 0)"
    is_open = f"{exp} = ThisItem.Idx"
    d_or_x = f"{_is('D')} || {_is('X')}"

    # Hoejre kant af tekstomraadet: foran tidskolonnen (bred) eller
    # direkte foran badget (smal).
    chip_x = f"{TW} - {CHIP_W} - 10"
    stamp_x = f"{chip_x} - 12 - {STAMP_W}"
    right = f"If({wide}, {stamp_x}, {chip_x}) - 12"
    actor_x = f"If(ThisItem.Human, {LX + ICON_W + 6}, {LX})"
    actor_w = f"Min(Len(ThisItem.Title) * 8 + 4, ({right} - {LX}) / 2)"
    act_x = f"{actor_x} + {actor_w} + 8"
    act_w = f"Max(0, {right} - ({act_x}))"
    # Detaljelinjen: under Tablet foerer tidsstemplet linjen.
    stamp_sep = 'If(IsBlank(%(q)s.Stamp) || IsBlank(%(q)s.Sub), "", "  ·  ")'
    line2 = (f'If({narrow}, ThisItem.Stamp & {stamp_sep % {"q": "ThisItem"}} & ThisItem.Sub, '
             'ThisItem.Sub)')
    one_line = f"IsBlank({line2})"

    # Udfoldning (kun smal skaerm, uaendret mekanik): handlingen og
    # detaljelinjen i fuld laengde over saa mange linjer, som de skal bruge.
    cpl = f"RoundDown(({TW} - {LX + 8}) / 5.8, 0)"
    sub_fit = cpl
    act_fit = (f"RoundDown(({chip_x} - 12 - ({actor_x.replace('ThisItem', 'Q')} + "
               f"{actor_w.replace('ThisItem', 'Q').replace(right, '(' + chip_x + ' - 12)')} + 8)) / 6.6, 0)")
    long_act = f"Len(ThisItem.Act) > {act_fit.replace('Q.', 'ThisItem.')}"
    full = ('If(Len(Q.Act) > %s, Q.Act & "  ·  ", "") & Q.Stamp & %s & Q.Sub'
            % (act_fit, stamp_sep % {"q": "Q"}))
    lines_n = "RoundUp(Len(t) / (2 * c), 0)"
    x_rec = ", ".join(f'{c}: {"Q.State" if c == "State" else "Q.Human" if c == "Human" else _DEFAULTS.get(c, chr(34) * 2)}'
                      for c in COLS)
    x_rec = x_rec.replace('Kind: ""', 'Kind: "X"')
    expanded = (
        f"With({{t: {full}, c: {cpl}}}, Ungroup(Table({{r: Table(Q)}}, {{r: ForAll("
        f"Sequence({lines_n}) As S, {{ {x_rec}, Idx: Q.Idx, "
        f"L1: Mid(t, (S.Value - 1) * 2 * c + 1, c), L2: Mid(t, (S.Value - 1) * 2 * c + c + 1, c), "
        f"IsLast: S.Value = {lines_n} }})}}), r))")
    items = f"Ungroup(ForAll(colMdAprRows As Q, {{ r: If(Q.Idx = {exp}, {expanded}, Table(Q)) }}), r)"
    n_new = f"With({{t: {full.replace('Q.', 'ThisItem.')}, c: {cpl}}}, {lines_n})"
    expandable = (f'{_is("D")} && {narrow} && (Len({line2}) > {sub_fit} || {long_act})')
    toggle = (f'If({_is("X")} || {is_open}, Set(varMdAprExp, 0); Set(varMdAprExtra, 0), '
              f'Set(varMdAprExp, ThisItem.Idx); Set(varMdAprExtra, {n_new}))')

    # Kortet: en bruger = fast, toned flade. Automatisk/system og det,
    # der venter = stiplet kant uden flade.
    solid = f'ThisItem.Human && ThisItem.State <> "Pending"'
    row_bg = f"If(({d_or_x}) && {solid}, {C_MUTED_BG}, {C_TRANSPARENT})"
    card = Ctrl(n("btn", "Card"), "Classic/Button", props={
        "BorderColor": f"If({solid}, {C_TRANSPARENT}, {C_CARD_BORDER})",
        "BorderStyle": "BorderStyle.Dashed",
        "BorderThickness": f"If({solid}, 0, 1)", "Color": C_TRANSPARENT,
        "Fill": row_bg, "HoverFill": row_bg, "PressedFill": row_bg,
        "HoverBorderColor": f"If({solid}, {C_TRANSPARENT}, {C_CARD_BORDER})",
        "PressedBorderColor": f"If({solid}, {C_TRANSPARENT}, {C_CARD_BORDER})",
        "HoverColor": C_TRANSPARENT, "PressedColor": C_TRANSPARENT,
        "DisplayMode": "DisplayMode.View",
        "Height": f"If({_is('X')}, If(ThisItem.IsLast, {ROW_H - 4}, {ROW_H}), If({is_open}, {ROW_H - 4}, {ROW_H - 8}))",
        "Width": f"{TW} - 38", "X": "38", "Y": f"If({_is('X')}, 0, 4)",
        "RadiusTopLeft": f"If({_is('X')}, 0, 8)", "RadiusTopRight": f"If({_is('X')}, 0, 8)",
        "RadiusBottomLeft": f"If({_is('X')}, If(ThisItem.IsLast, 8, 0), If({is_open}, 0, 8))",
        "RadiusBottomRight": f"If({_is('X')}, If(ThisItem.IsLast, 8, 0), If({is_open}, 0, 8))",
        "TabIndex": "0", "Text": '""', "Visible": d_or_x,
    }, h=ROW_H - 8, vis=d_or_x)
    rail = Ctrl(n("img", "Rail"), "Image", props={
        "AccessibleLabel": '"Approval timeline"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": str(ROW_H), "Image": _rail_svg(),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "0",
        "Width": "32", "X": "0", "Y": "0",
    }, h=ROW_H)

    # Det aktuelle trin: en smal streg i informationsfarven foran trinets
    # navn - i stedet for et "Current"-maerke ved siden af "In progress".
    cur_bar = text_ctrl(n("txt", "CurBar"), '""', size=lay.SIZE_MICRO, height=26, width=3,
                        fill=C_INFO_FG, visible=f"{_is('H')} && ThisItem.Cur",
                        accessible='"Current stage"',
                        extra={"X": "34", "Y": str((ROW_H - 26) // 2),
                               "RadiusBottomLeft": "2", "RadiusBottomRight": "2",
                               "RadiusTopLeft": "2", "RadiusTopRight": "2"})
    h_title = text_ctrl(n("txt", "HTitle"), "ThisItem.Title", size=14, weight="Semibold", height=20,
                        visible=_is("H"), width=f"{chip_x} - 12 - 42",
                        extra={"X": "42", "Y": "5"})
    h_rule = text_ctrl(n("txt", "HRule"), "ThisItem.Rule", size=lay.SIZE_MICRO, color=C_MUTED,
                       height=17, visible=_is("H"), width=f"{chip_x} - 12 - 42",
                       extra={"X": "42", "Y": "26"})

    y1 = f"If({one_line}, {(ROW_H - 20) // 2}, 6)"
    person = Ctrl(n("img", "Person"), "Image", props={
        "AccessibleLabel": '"User"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": str(ICON_W),
        "Image": ('"data:image/svg+xml;utf8," & EncodeUrl("<svg xmlns=\'http://www.w3.org/2000/svg\' '
                  'width=\'24\' height=\'24\' viewBox=\'0 0 24 24\'><path d=\'' + PERSON +
                  '\' fill=\'none\' stroke=\'" & ' + ref_hex("text-muted") +
                  ' & "\' stroke-width=\'%g\' stroke-linecap=\'round\' stroke-linejoin=\'round\'/></svg>")'
                  % icons.stroke(ICON_W)),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "0",
        "Width": str(ICON_W), "X": str(LX), "Y": f"{y1} + 2",
        "Visible": f"{_is('D')} && ThisItem.Human",
    }, h=ICON_W, vis=f"{_is('D')} && ThisItem.Human")
    actor = text_ctrl(n("txt", "DTitle"), "ThisItem.Title", size=lay.SIZE_BODY, weight="Semibold",
                      color=f"If(ThisItem.Human, {C_TITLE}, {C_MUTED})", height=20,
                      visible=_is("D"), width=actor_w,
                      accessible='If(ThisItem.Human, "User ", "Automated: ") & ThisItem.Title',
                      extra={"X": actor_x, "Y": y1})
    act = text_ctrl(n("txt", "DAct"), "ThisItem.Act", size=lay.SIZE_BODY, height=20,
                    visible=f"{_is('D')} && !IsBlank(ThisItem.Act)", width=act_w,
                    extra={"X": act_x, "Y": y1})
    d_sub = text_ctrl(n("txt", "DSub"), line2, size=lay.SIZE_SMALL, color=C_MUTED,
                      height=17, visible=f'{_is("D")} && !({is_open}) && !({one_line})',
                      width=f"{right} - {LX}", extra={"X": str(LX), "Y": "25"})
    stamp = text_ctrl(n("txt", "Stamp"), "ThisItem.Stamp", size=lay.SIZE_SMALL, color=C_MUTED,
                      height=20, align="Right", width=STAMP_W,
                      visible=f"{_is('D')} && {wide} && !IsBlank(ThisItem.Stamp)",
                      extra={"X": stamp_x, "Y": str((ROW_H - 20) // 2)})
    x1 = text_ctrl(n("txt", "X1"), "ThisItem.L1", size=lay.SIZE_SMALL, color=C_MUTED, height=17,
                   visible=_is("X"), width=f"{TW} - {LX + 8}", extra={"X": str(LX), "Y": "4"})
    x2 = text_ctrl(n("txt", "X2"), "ThisItem.L2", size=lay.SIZE_SMALL, color=C_MUTED, height=17,
                   visible=_is("X"), width=f"{TW} - {LX + 8}", extra={"X": str(LX), "Y": "22"})
    sw = lambda table: _switch("ThisItem.State", table, C_NEUTRAL_FG)
    chip = text_ctrl(n("txt", "Chip"), "ThisItem.Label", size=lay.SIZE_MICRO, weight="Semibold",
                     height=CHIP_H, align="Center", color=sw(BADGE_FG),
                     fill=_switch("ThisItem.State", BADGE_BG, C_NEUTRAL_BG),
                     width=CHIP_W,
                     accessible='"Status " & ThisItem.Label & If(ThisItem.Cur, ", current stage", "")',
                     visible=f'!({_is("X")})',
                     extra={"X": chip_x, "Y": str((ROW_H - CHIP_H) // 2),
                            "VerticalAlign": "VerticalAlign.Middle",
                            "PaddingLeft": "8", "PaddingRight": "8",
                            "RadiusBottomLeft": "6", "RadiusBottomRight": "6",
                            "RadiusTopLeft": "6", "RadiusTopRight": "6"})
    # Noteraekken (issue #115) aabner noterne i stedet for at folde ud.
    is_note = f'{_is("D")} && ThisItem.Stage = "{NOTE_STAGE}"'
    hit = row_hit(n("btn", "Expand"), f"If({is_note}, {sn.hub_open_fx(R)}, {toggle})",
                  f'If({is_note}, "Read the submission notes", "Show or hide the full text")',
                  f"{TW} - 38", ROW_H - 8)
    hit.props["X"] = "38"
    hit.props["Y"] = f"If({_is('X')}, 0, 4)"
    hit.props["Height"] = f"If({_is('X')}, {ROW_H}, {ROW_H - 8})"
    hit.vis = f"{expandable} || {_is('X')} || ({is_note})"

    gh = f"(Min(CountRows(colMdAprRows), {MAX_ROWS}) + IfError(varMdAprExtra, 0)) * {ROW_H}"
    gal = Ctrl(n("gal", "Rows"), "Gallery", variant="Vertical", props={
        "AccessibleLabel": f'If({IS_TIMELINE}, "Activity", "Approval flow")',
        "AlignInContainer": "AlignInContainer.Start",
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gh, "Items": items, "LayoutMinWidth": "0",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Width": GW, "WrapCount": "1",
    }, children=[card, rail, cur_bar, h_title, h_rule, person, actor, act, d_sub, stamp,
                 x1, x2, chip, hit],
        h=MAX_ROWS * ROW_H)

    # Overskriften: titlen, saa nummeret som badge i domaenets farve, og
    # Close yderst til hoejre. Titlen er sin egen tekst - nummeret staar
    # ikke laengere i den.
    # Samme maal som sidetitlen ved appens nummerbadge (top_bar).
    tw_a = int(text_px("Approval flow", lay.SIZE_CARD_TITLE) * 0.86) + 2
    tw_t = int(text_px("Activity", lay.SIZE_CARD_TITLE) * 0.86) + 2
    title = text_ctrl(n("txt", "Title"), f'If({IS_TIMELINE}, "Activity", "Approval flow")',
                      size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false",
                      width=f"If({IS_TIMELINE}, {tw_t}, {tw_a})")
    title.props["LayoutMinWidth"] = str(min(tw_a, tw_t))
    no_badge = _number_badge(n("img", "No"))
    spacer = grow(text_ctrl(n("txt", "HeadGap"), '""', size=lay.SIZE_MICRO, height=20,
                            accessible='"Spacer"'))
    btnClose = button(n("btn", "Close"), '"Close"', CLOSE, width=84, height=32)
    head = group(n("con", "Head"), [title, no_badge, spacer, btnClose], direction="Horizontal",
                 gap=10, height=32, align_items="Center")
    sub = text_ctrl(
        n("txt", "Sub"),
        f'If({IS_TIMELINE}, {META_FX}, {R}.ShortText & "  ·  Plant " & {R}.Plant & "  ·  " & '
        'If(varMdAprCur = "", If(varMdAprS4 = "Done", "Completed", "No active stage"), '
        '"Now at: " & varMdAprCur))',
        size=lay.SIZE_SMALL, color=C_MUTED, height=20, wrap="false")

    busy = "IfError(varMdAprBusy, false)"
    gal.props["Visible"] = f"!{busy}"
    sub.props["Visible"] = f"!{busy}"
    note, note_vis, note_h = _note_panel(busy)
    spin = Ctrl(n("img", "Spinner"), "Image", props={
        "AccessibleLabel": f'If({IS_TIMELINE}, "Loading activity", "Loading approval flow")',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0", "Fill": C_TRANSPARENT, "Height": "110",
        "Image": spinner_svg(), "ImagePosition": "ImagePosition.Center",
        "TabIndex": "0", "Visible": busy, "Width": GW,
    }, h=110, vis=busy)

    modal = group(n("con", "Modal"), [head, sub, note, spin, gal], direction="Vertical", gap=10,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=POP_W, drop_shadow="ExtraBold",
                  align_in_container="Center")
    modal.props["Height"] = (f"{2 * POP_PAD + 32 + 2 * 10} + If({busy}, 110, 20 + 10 + {gh}) + "
                             f"If({note_vis}, {note_h} + 10, 0)")
    backdrop = group(n("con", "Backdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=OPEN,
                     justify="Start", align_items="Center", pad=(16, 0, 16, 0), overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return [backdrop]
