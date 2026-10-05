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
                        C_MUTED_BG, C_TRANSPARENT, C_PRIMARY, C_WHITE, C_INFO_BG, C_INFO_FG,
                        C_WARN_FG, C_WARN_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_VALID_FG, C_VALID_BG,
                        C_DIVIDER, C_ROW_HOVER, C_ROW_PRESSED)
from build_helpers import group, text_ctrl, button, grow, spinner_svg, row_hit
from design_tokens import ref_hex
import layout_tokens as lay
import admin_log as alog
from layout_tokens import if_below, at_least

OPEN = "IfError(varMdAprOpen, false)"
CLOSE = "Set(varMdAprOpen, false)"
ROW_H = 46
MAX_ROWS = 11
POP_MAX_W = 640
POP_PAD = 16
SVG_FONT = "font-family='Segoe UI, sans-serif'"

STAGES = [
    ("System", "System approval", "S1"),
    ("Cost", "Cost approval", "S2"),
    ("Quality", "Quality review", "S3"),
]
# "Admin": en admins aendring i en andens anmodning (tools/admin_log.py) -
# samme advarselsfarve som Returned, saa den skiller sig ud i forloebet.
STATE_FG = {"Approved": C_VALID_FG, "Done": C_VALID_FG, "Skipped": C_NEUTRAL_FG,
            "In progress": C_INFO_FG, "Returned": C_WARN_FG, "Pending": C_NEUTRAL_FG,
            "Admin": C_WARN_FG}
STATE_BG = {"Approved": C_VALID_BG, "Done": C_VALID_BG, "Skipped": C_NEUTRAL_BG,
            "In progress": C_INFO_BG, "Returned": C_WARN_BG, "Pending": C_NEUTRAL_BG,
            "Admin": C_WARN_BG}
STATE_HEX = {"Approved": "state-ok-fg", "Done": "state-ok-fg", "Skipped": "state-neutral-fg",
             "In progress": "state-info-fg", "Returned": "state-warn-fg",
             "Pending": "text-muted", "Admin": "state-warn-fg"}
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
LOG_LIMIT = 500   # appens Data row limit (som build_hub.ROW_LIMIT)
LOG_REFRESH = ('ClearCollect(colMdAprAll, SortByColumns(Filter(MD_ApprovalLog, '
               'Stage = "System" || Stage = "Cost" || Stage = "Quality"), "ID", '
               'SortOrder.Descending))')
ROW_LOG = ('With({ c: Filter(colMdAprAll, RequestGuid = ThisItem.RequestGuid) }, '
           f'If(IsEmpty(c) && CountRows(colMdAprAll) >= {LOG_LIMIT}, '
           'Filter(MD_ApprovalLog, RequestGuid = ThisItem.RequestGuid), c))')


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
            f'"<circle cx=\'{xs[i]}\' cy=\'{y}\' r=\'4\' stroke-width=\'1.5\' stroke=\'" & {col} & '
            f'"\' fill=\'" & If({hollow}, "none", {col}) & "\'/>"')
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
COLS = ("Kind", "Stage", "Title", "State", "Label", "Rule", "Cur", "Sub")


def _rec(**f):
    f.setdefault("Cur", "false")
    vals = []
    for c in COLS:
        v = f.get(c, '""')
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


def _who(email):
    return f'Upper(First(Split(Coalesce({email}, "unknown@"), "@")).Value)'


def _decision_rows(stage, tbl, timeline=False):
    item = '' if stage == "Quality" else ' & If(!IsBlank(ItemText), "  \u00b7  " & ItemText, "")'
    state = ('Switch(Decision, "Approve", "Approved", "Skipped", "Skipped", '
             f'"{alog.EDIT}", "Admin", "{alog.DELETE}", "Admin", "Returned")')
    label = (f'Switch(Decision, "{alog.EDIT}", "Admin edit", "{alog.DELETE}", "Admin delete", '
             f'{state})')
    sub = ('Text(DecidedOn, "dd-mm-yyyy hh:mm") & '
           'If(!IsBlank(Comment), "  \u00b7  " & Substitute(Comment, Char(10), " "), '
           'If(!IsBlank(Detail), "  \u00b7  " & Detail, ""))')
    who = f"{_who('DecidedByEmail')}{item}"
    if timeline:
        who = f'Stage & "  \u00b7  " & {who}'
    rec = _rec(Kind=_q("D"), Stage=_q(stage), Title=who, State=state, Label=label, Sub=sub)
    return f'ForAll(SortByColumns({tbl}, "DecidedOn"), {rec})'


def _waiting_row(stage, svar):
    n = f'CountRows(Filter(colMdAprLatest, Stage = "{stage}"))'
    exp = expected(stage, R)
    if stage == "System":
        who = '"System manager of each item"'
        sub = f'({exp} - {n}) & " of " & {exp} & " awaiting a decision"'
    else:
        key = '"COST"' if stage == "Cost" else f"Upper(Left({R}.Plant, 3))"
        who = (f'With({{a: LookUp(MD_Approver, ApproverKey = {key})}}, If(IsBlank(a), "Approver not set", '
               f'Upper(If(a.Approver1Absent, a.Approver2, a.Approver1))))')
        sub = (f'With({{a: LookUp(MD_Approver, ApproverKey = {key})}}, If(IsBlank(a), "No row in MD_Approver for " & {key}, '
               f'If(a.Approver1Absent, "2nd approver - 1st approver absent", "1st approver")))' )
    rec = _rec(Kind=_q("D"), Stage=_q(stage), Title=who, State=_q("Pending"), Label=_q("Awaiting"),
               Sub=sub)
    return f'If({svar} = "In progress" && {n} < {exp}, Collect(colMdAprRows, {rec}))'


META_FX = (
    "Concat(\n"
    "    Filter(\n"
    "        Table(\n"
    '            { v: If(!IsBlank(%(r)s.RequesterName), "by " & %(r)s.RequesterName) },\n'
    "            { v: If(%(r)s.ItemCount > 0, Text(%(r)s.ItemCount) &\n"
    '                    If(%(r)s.ItemCount = 1, " item", " items")) },\n'
    '            { v: If(!IsBlank(%(r)s.SapObjectNo), "SAP " & %(r)s.SapObjectNo) },\n'
    '            { v: If(!IsBlank(%(r)s.LastActionBy), "last change by " & %(r)s.LastActionBy) }\n'
    "        ),\n"
    "        !IsBlank(v)\n"
    "    ),\n"
    "    v,\n"
    '    "  \u00b7  "\n'
    ")"
) % {"r": R}

IS_TIMELINE = 'IfError(varMdAprMode, "") = "T"'


def timeline_fx():
    """Activity of one request. One filtered query. For plans it holds the
    approvals; for every domain it holds an admin's changes (Stage "Admin",
    tools/admin_log.py) - so it is read for all domains, not only plans."""
    stamp = 'Text(%s.Created, "dd-mm-yyyy hh:mm")' % R
    lines = [
        "Set(varMdAprBusy, true)",
        "Set(varMdAprExp, 0)",
        "Set(varMdAprExtra, 0)",
        'Set(varMdAprMode, "T")',
        "Set(varMdAprOpen, true)",
        f"Set({R}, ThisItem)",
        "ClearCollect(colMdAprLog, Filter(MD_ApprovalLog, RequestGuid = ThisItem.RequestGuid))",
        "ClearCollect(colMdAprRows, " + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=f'"Created by " & {_who(R + ".RequesterEmail")}',
            State=_q("Done"), Label=_q("Created"), Sub=stamp) + ")",
        "Collect(colMdAprRows, " + _decision_rows("T", "colMdAprLog", timeline=True) + ")",
        f'If(!IsBlank({R}.SapObjectNo), Collect(colMdAprRows, ' + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=f'"SAP " & {R}.SapObjectNo', State=_q("Done"),
            Label=_q("Created"), Sub=_q("Created in SAP")) + "))",
        f'If({R}.IsOpen && !IsBlank({R}.AssignedToEmail), Collect(colMdAprRows, ' + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=_who(R + ".AssignedToEmail"), State=_q("In progress"),
            Label=_q("Waiting"), Sub=_q("Assigned to")) + "))",
        "Collect(colMdAprRows, " + _rec(
            Kind=_q("D"), Stage=_q("T"), Title=f'"Status: " & {R}.Status.Value',
            State=f'If({R}.IsOpen, "In progress", "Done")', Label=f'If({R}.IsOpen, "Open", "Closed")',
            Sub=f'"Last change " & Text({R}.LastActionOn, "dd-mm-yyyy hh:mm") & '
                f'If(!IsBlank({R}.LastActionBy), " by " & {R}.LastActionBy, "")') + ")",
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
            Sub=f'If(varMdAprS4 = "Done", "SAP " & {R}.SapObjectNo, "Ready - waiting for creation in SAP")')
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
# The popup: a swimlane timeline. Rail on the left (node per stage, dot per
# decision), stage header with state and rule, one compact card per decision.
# ---------------------------------------------------------------------------
POP_W = f"Min({POP_MAX_W}, App.Width - 24)"
GW = f"({POP_W} - {2 * POP_PAD})"
TW = f"({GW} - 20)"
CHIP_W = 92


def _rail_svg():
    ok = ref_hex("state-ok-fg")
    col = _hex_switch("ThisItem.State")
    c = ROW_H // 2
    line = ref_hex("border-default")
    node_glyph = _switch(
        "ThisItem.State",
        {k: '"%s"' % v for k, v in {
            "Approved": "M7 12.5l3.2 3.2L17 9", "Done": "M7 12.5l3.2 3.2L17 9",
            "Skipped": "M8 12h8", "In progress": "M12 7.5v5l3 2",
            "Returned": "M10 8l-4 4 4 4M6 12h8a4 4 0 0 1 4 4"}.items()},
        '"M12 12v.01"')
    head = (f'"<circle cx=\'16\' cy=\'{c}\' r=\'11\' fill=\'" & {col} & "\'/>'
            f'<g transform=\'translate(4 {c - 12})\' fill=\'none\' stroke=\'" & {ref_hex("text-on-primary")} & '
            f'"\' stroke-width=\'2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'><path d=\'" & '
            f'{node_glyph} & "\'/></g>"')
    dot = (f'"<line x1=\'16\' y1=\'{c}\' x2=\'30\' y2=\'{c}\' stroke=\'" & {line} & "\' stroke-width=\'1.5\'/>'
           f'<circle cx=\'16\' cy=\'{c}\' r=\'5\' stroke-width=\'2\' stroke=\'" & {col} & "\' fill=\'" & '
           f'If(ThisItem.State = "Pending", "none", {col}) & "\'/>"')
    svg = ('"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'32\' height=\'%d\' viewBox=\'0 0 32 %d\'>'
           '<line x1=\'16\' y1=\'0\' x2=\'16\' y2=\'%d\' stroke=\'" & %s & "\' stroke-width=\'2\'/>"'
           ' & If(ThisItem.Kind = "H", %s, If(ThisItem.Kind = "X", "", %s)) & "</svg>"') % (ROW_H, ROW_H, ROW_H, line, head, dot)
    return f'"data:image/svg+xml;utf8," & EncodeUrl({svg})'


def _is(kind):
    return f'ThisItem.Kind = "{kind}"'


def build_popup():
    n = lambda kind, base: f"{kind}MdApr{base}"
    sw = lambda table: _switch("ThisItem.State", table, C_NEUTRAL_FG)
    narrow = lay.below("Tablet")
    exp = "IfError(varMdAprExp, 0)"
    cpl = f"RoundDown(({TW} - 56) / 5.8, 0)"
    sub_fit = f"RoundDown(({TW} - 56) / 5.8, 0)"
    tit_fit = f"RoundDown(({TW} - 48 - {CHIP_W} - 12) / 7.6, 0)"
    long_title = f"Len(ThisItem.Title) > {tit_fit}"
    expandable = (f'{_is("D")} && {narrow} && (Len(ThisItem.Sub) > {sub_fit} || {long_title})')
    is_open = f"{exp} = ThisItem.Idx"
    full_text = 'If(Len(Q.Title) > %s, Q.Title & "  \u00b7  ", "") & Q.Sub' % tit_fit.replace("ThisItem", "Q")
    lines_n = f"RoundUp(Len(t) / (2 * c), 0)"
    expanded = (
        f"With({{t: {full_text}, c: {cpl}}}, Ungroup(Table({{r: Table(Q)}}, {{r: ForAll("
        f"Sequence({lines_n}) As S, {{ Kind: \"X\", Stage: \"\", Title: \"\", State: Q.State, Label: \"\", Rule: \"\", Cur: false, Sub: \"\", Idx: Q.Idx, "
        f"L1: Mid(t, (S.Value - 1) * 2 * c + 1, c), L2: Mid(t, (S.Value - 1) * 2 * c + c + 1, c), "
        f"IsLast: S.Value = {lines_n} }})}}), r))")
    items = (f"Ungroup(ForAll(colMdAprRows As Q, {{ r: If(Q.Idx = {exp}, {expanded}, Table(Q)) }}), r)")
    n_new = (f"With({{t: {full_text.replace('Q.', 'ThisItem.')}, c: {cpl}}}, RoundUp(Len(t) / (2 * c), 0))")
    toggle = (f'If({_is("X")} || {is_open}, Set(varMdAprExp, 0); Set(varMdAprExtra, 0), '
              f'Set(varMdAprExp, ThisItem.Idx); Set(varMdAprExtra, {n_new}))')

    bg_cur = text_ctrl(n("txt", "Cur"), '""', size=lay.SIZE_SMALL, height=ROW_H - 2,
                       fill=f"If({_is('H')} && ThisItem.Cur, {C_INFO_BG}, {C_TRANSPARENT})",
                       width=TW, extra={"X": "0", "Y": "0"})
    row_bg = f"If({_is('D')} || {_is('X')}, {C_MUTED_BG}, {C_TRANSPARENT})"
    d_or_x = f"{_is('D')} || {_is('X')}"
    card = Ctrl(n("btn", "Card"), "Classic/Button", props={
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0", "Color": C_TRANSPARENT,
        "Fill": row_bg, "HoverFill": row_bg, "PressedFill": row_bg,
        "HoverColor": C_TRANSPARENT, "PressedColor": C_TRANSPARENT,
        "DisplayMode": "DisplayMode.View",
        "Height": f"If({_is('X')}, If(ThisItem.IsLast, {ROW_H - 4}, {ROW_H}), If({exp} = ThisItem.Idx, {ROW_H - 4}, {ROW_H - 8}))",
        "Width": f"{TW} - 38", "X": "38", "Y": f"If({_is('X')}, 0, 4)",
        "RadiusTopLeft": f"If({_is('X')}, 0, 8)", "RadiusTopRight": f"If({_is('X')}, 0, 8)",
        "RadiusBottomLeft": f"If({_is('X')}, If(ThisItem.IsLast, 8, 0), If({exp} = ThisItem.Idx, 0, 8))",
        "RadiusBottomRight": f"If({_is('X')}, If(ThisItem.IsLast, 8, 0), If({exp} = ThisItem.Idx, 0, 8))",
        "TabIndex": "-1", "Text": '""', "Visible": d_or_x,
    }, h=ROW_H - 8, vis=d_or_x)
    rail = Ctrl(n("img", "Rail"), "Image", props={
        "AccessibleLabel": '""', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": str(ROW_H), "Image": _rail_svg(),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "-1",
        "Width": "32", "X": "0", "Y": "0",
    }, h=ROW_H)

    h_title = text_ctrl(n("txt", "HTitle"), "ThisItem.Title", size=14, weight="Semibold", height=20,
                        visible=_is("H"), width=f"{TW} - 40 - {CHIP_W} - 8",
                        extra={"X": "40", "Y": "5"})
    h_rule = text_ctrl(n("txt", "HRule"), "ThisItem.Rule", size=lay.SIZE_MICRO, color=C_MUTED,
                       height=17, visible=_is("H"), width=f"{TW} - 48",
                       extra={"X": "40", "Y": "26"})
    d_title = text_ctrl(n("txt", "DTitle"), "ThisItem.Title", size=lay.SIZE_BODY, weight="Semibold",
                        height=20, visible=_is("D"), width=f"{TW} - 48 - {CHIP_W} - 12",
                        extra={"X": "48", "Y": "6"})
    d_sub = text_ctrl(n("txt", "DSub"), "ThisItem.Sub", size=lay.SIZE_MICRO, color=C_MUTED,
                      height=17, visible=f'{_is("D")} && !({is_open})', width=f"{TW} - 56",
                      extra={"X": "48", "Y": "25"})
    x1 = text_ctrl(n("txt", "X1"), "ThisItem.L1", size=lay.SIZE_MICRO, color=C_MUTED, height=17,
                   visible=_is("X"), width=f"{TW} - 56", extra={"X": "48", "Y": "4"})
    x2 = text_ctrl(n("txt", "X2"), "ThisItem.L2", size=lay.SIZE_MICRO, color=C_MUTED, height=17,
                   visible=_is("X"), width=f"{TW} - 56", extra={"X": "48", "Y": "22"})
    chip = text_ctrl(n("txt", "Chip"), "ThisItem.Label", size=lay.SIZE_MICRO, weight="Semibold",
                     height=20, align="Center", color=sw(STATE_FG), fill=sw(STATE_BG),
                     width=CHIP_W, accessible='"Status " & ThisItem.Label',
                     visible=f'!({_is("X")})',
                     extra={"X": f"{TW} - {CHIP_W} - 4", "Y": f"If({_is('H')}, 5, 8)",
                            "PaddingTop": "1"})
    hit = row_hit(n("btn", "Expand"), toggle, '"Show or hide the full text"', f"{TW} - 38", ROW_H - 8)
    hit.props["X"] = "38"
    hit.props["Y"] = f"If({_is('X')}, 0, 4)"
    hit.props["Height"] = f"If({_is('X')}, {ROW_H}, {ROW_H - 8})"
    hit.vis = f"{expandable} || {_is('X')}"
    cur = text_ctrl(n("txt", "CurTag"), '"Current"', size=lay.SIZE_MICRO, weight="Semibold",
                    height=20, align="Center", color=C_WHITE, fill=C_INFO_FG, width=58,
                    visible=f"{_is('H')} && ThisItem.Cur",
                    extra={"X": f"{TW} - {CHIP_W} - 4 - 58 - 6", "Y": "5", "PaddingTop": "1"})

    gh = f"(Min(CountRows(colMdAprRows), {MAX_ROWS}) + IfError(varMdAprExtra, 0)) * {ROW_H}"
    gal = Ctrl(n("gal", "Rows"), "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Approval flow"',
        "AlignInContainer": "AlignInContainer.Start",
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gh, "Items": items, "LayoutMinWidth": "0",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Width": GW, "WrapCount": "1",
    }, children=[bg_cur, card, rail, h_title, h_rule, cur, d_title, d_sub, x1, x2, chip, hit],
        h=MAX_ROWS * ROW_H)

    title = grow(text_ctrl(n("txt", "Title"),
                           f'{R}.RequestNo & If({IS_TIMELINE}, "  -  activity", "  -  approval flow")',
                           size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false"))
    btnClose = button(n("btn", "Close"), '"Close"', CLOSE, width=84, height=32)
    head = group(n("con", "Head"), [title, btnClose], direction="Horizontal", gap=12, height=32,
                 align_items="Center")
    sub = text_ctrl(
        n("txt", "Sub"),
        f'If({IS_TIMELINE}, {META_FX}, {R}.ShortText & "  \u00b7  Plant " & {R}.Plant & "  \u00b7  " & '
        'If(varMdAprCur = "", If(varMdAprS4 = "Done", "Completed", "No active stage"), '
        '"Now at: " & varMdAprCur))',
        size=lay.SIZE_SMALL, color=C_MUTED, height=20, wrap="false")

    busy = "IfError(varMdAprBusy, false)"
    gal.props["Visible"] = f"!{busy}"
    sub.props["Visible"] = f"!{busy}"
    spin = Ctrl(n("img", "Spinner"), "Image", props={
        "AccessibleLabel": '"Loading approval flow"', "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0", "Fill": C_TRANSPARENT, "Height": "110",
        "Image": spinner_svg(), "ImagePosition": "ImagePosition.Center",
        "TabIndex": "-1", "Visible": busy, "Width": GW,
    }, h=110, vis=busy)

    modal = group(n("con", "Modal"), [head, sub, spin, gal], direction="Vertical", gap=10,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=POP_W, drop_shadow="ExtraBold",
                  align_in_container="Center")
    modal.props["Height"] = f"{2 * POP_PAD + 32 + 2 * 10} + If({busy}, 110, 20 + 10 + {gh})"
    backdrop = group(n("con", "Backdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=OPEN,
                     justify="Start", align_items="Center", pad=(16, 0, 16, 0), overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return [backdrop]
