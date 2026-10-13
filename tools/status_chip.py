# -*- coding: utf-8 -*-
"""
EEN STATUSCHIP OVERALT (UX-review 2026-10, T4).

Status blev vist paa tre maader: hubben tegnede et ikon og "Draft",
domaenernes raekker et maerke i VERSALER ("DRAFT", "SUBMITTED"), og Issue
Board en blaa pille ("New"), der lignede prioriteten ved siden af. Nu er der
een chip: ikon + tekst i sentence case + statussens farvepar (state-*).

    status_chip("imgEqRowStatus", "ThisItem.Status", ROW)

Chippen er et Image med en SVG pr. status. Teksten staar i SVG'en, saa
pillen er praecis saa bred som sin tekst; kontrollen er saa bred som den
bredeste i tabellen, og pillen staar til venstre i den.

Tabellerne herunder er de ENESTE steder, en status faar ikon og farve. Hubbens
hub_config.STATUS_ICON og _STATUS_COLORS laeser REQUEST.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import icons  # noqa: E402
import request_index as ri  # noqa: E402

# (lagret vaerdi, etiket, ikon, farve) - farven er state-<tone>-fg/-bg.
#
# ANMODNINGEN (MD_RequestIndex.Status). Samme ikon og farve som hubben
# altid har haft (issue #139).
_REQUEST_LOOK = {
    "Kladde":          (icons.STATUS_DRAFT,     "neutral"),
    "Indsendt":        (icons.STATUS_SUBMITTED, "info"),
    "UnderBehandling": (icons.STATUS_PROGRESS,  "violet"),
    "AfventerInfo":    (icons.STATUS_AWAITING,  "warn"),
    "KlarTilSAP":      (icons.STATUS_READY,     "ok"),
    "OprettetISAP":    (icons.STATUS_CREATED,   "lime"),
    "Afvist":          (icons.STATUS_REJECTED,  "error"),
    "Annulleret":      (icons.STATUS_CANCELLED, "rose"),
}
REQUEST = [(k, label, *_REQUEST_LOOK[k]) for k, label, _st in ri.STATUS]

# EN RAEKKE i et domaene (colDomRows.Status - lagrede vaerdier, smaa bogstaver).
ROW = [
    ("draft", "Draft", icons.STATUS_DRAFT, "neutral"),
    ("valid", "Valid", icons.STATUS_READY, "ok"),
    ("submitted", "Submitted", icons.STATUS_SUBMITTED, "info"),
]

# ET ITEM i VH-planen (colVhpItems.Status - valideringens resultat).
VH_ITEM = [
    ("draft", "Draft", icons.STATUS_DRAFT, "neutral"),
    ("valid", "Valid", icons.STATUS_READY, "ok"),
    ("invalid", "To fix", icons.STATUS_AWAITING, "error"),
]

# EN SAG i Issue Board (IB_Tickets.Status). Toner fra ib_config.STATUS.
ISSUE_ICONS = {
    "New": icons.STATUS_SUBMITTED,
    "Reopened": icons.HISTORY,
    "Triaged": icons.LIST,
    "In progress": icons.STATUS_PROGRESS,
    "Ready for retest": icons.EYE,
    "Closed": icons.STATUS_READY,
}
ARCHIVED = ("Archived", "Archived", icons.STATUS_CANCELLED, "neutral")

# PRIORITETEN (Issue Board) maa IKKE ligne status (T4): Normal og Low er
# almindelig tekst; kun Urgent og High faar ikon og farve.
PRIORITY = [
    ("Urgent", "Urgent", icons.STATUS_AWAITING, "error"),
    ("High", "High", icons.CHEVRON_UP, "warn"),
    ("Normal", "Normal", None, "plain"),
    ("Low", "Low", None, "plain"),
]

H = 22
PAD_L = 8
ICON = 12
GAP = 5
PAD_R = 9
SIZE = 11


def _hx(tok):
    from design_tokens import ref_hex
    return '" & %s & "' % ref_hex(tok)


def chip_width(label):
    from build_helpers import label_px
    return PAD_L + ICON + GAP + label_px(label, SIZE) + PAD_R


def _chip_svg(label, path, tone, width):
    """tone "plain": ingen pille og intet ikon - bare teksten i
    broedtekstens farve (Issue Boards Normal/Low-prioritet)."""
    if tone == "plain":
        return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{H}' "
                f"viewBox='0 0 {width} {H}'><text x='0' y='{H / 2 + 4:g}' "
                f"font-family='Segoe UI, sans-serif' font-size='{SIZE + 1}' "
                f"fill='{_hx('text-primary')}'>{label}</text></svg>" + '"')
    w = chip_width(label)
    fg, bg = _hx("state-%s-fg" % tone), _hx("state-%s-bg" % tone)
    glyph = icons.glyph(path, fg, size=ICON, x=PAD_L, y=(H - ICON) / 2)
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{H}' "
            f"viewBox='0 0 {width} {H}'>"
            f"<rect width='{w}' height='{H}' rx='{H // 2}' fill='{bg}'/>"
            + glyph +
            f"<text x='{PAD_L + ICON + GAP}' y='{H / 2 + 4:g}' font-family='Segoe UI, sans-serif' "
            f"font-size='{SIZE}' font-weight='600' fill='{fg}'>{label}</text></svg>" + '"')


def table_width(table):
    return max(chip_width(t[1]) for t in table)


def svg_expr(key_expr, table, default=None):
    """Power Fx-udtrykket for chippens billede (en data-URI)."""
    width = table_width(table if default is None else list(table) + [default])
    branches = [f'"{k}", {_chip_svg(label, path, tone, width)}'
                for k, label, path, tone in table]
    d = default or ("", table[0][1], table[0][2], table[0][3])
    body = (f"Switch(\n    {key_expr},\n    " + ",\n    ".join(branches)
            + f",\n    {_chip_svg(d[1], d[2], d[3], width)}\n)")
    return f'"data:image/svg+xml;utf8," & EncodeUrl({body})'


def label_expr(key_expr, table, default='"Unknown"'):
    body = ", ".join(f'"{k}", "{label}"' for k, label, _p, _t in table)
    return f"Switch({key_expr}, {body}, {default})"


def status_chip(name, key_expr, table, default=None, width=None, visible=None):
    """Chippen som Image. default: (noegle, etiket, ikon, tone) for en
    ukendt vaerdi - ellers den foerste i tabellen."""
    from gen_screen import Ctrl
    w = width or table_width(table if default is None else list(table) + [default])
    lab = label_expr(key_expr, table, f'"{default[1]}"' if default else key_expr)
    props = {
        "AccessibleLabel": f'"Status: " & {lab}',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(H),
        "Image": svg_expr(key_expr, table, default),
        # SVG'en er tegnet i kontrollens egen stoerrelse - Fit skalerer ikke.
        "ImagePosition": "ImagePosition.Fit",
        "LayoutMinWidth": str(w),
        "OnSelect": "false",
        "TabIndex": "0",
        "Width": str(w),
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "Image", props=props, h=H, vis=visible)


def issue_table(statuses):
    """Issue Boards tabel af ib_config.STATUS [(vaerdi, tone, rang)]."""
    return [(s, s, ISSUE_ICONS[s], tone) for s, tone, _r in statuses]
