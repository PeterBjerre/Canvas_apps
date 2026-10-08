# -*- coding: utf-8 -*-
"""
HVOR LANGT ER INDMELDINGEN? - trinstriben i en anmodningsapp.

Hubben viser en stribe pr. anmodning (Masterdata Hub/build/approval_flow.py:
System, Cost, Quality, SAP). Den, der UDFYLDER formularen, har aldrig haft
den: han ser en liste raekker og en Submit-knap, og foerst naar han trykker,
faar han at vide, at noget mangler. Striben her er den samme tanke, men
foer indsendelsen: hvilke trin er der, hvor staar vi, og hvad mangler.

EEN KONTROL, IKKE EN PR. TRIN
-----------------------------
Striben er et SVG-billede, som hubbens. Et trin pr. kontrol ville vaere
tre gange saa mange kontroller - og hoejden skulle regnes af dem alle. Paa
en smal skaerm er der ikke plads til navnene; saa tegnes den samme stribe
som "2 of 3 - <trinnets navn>", og det er derfor ET billede med to
udgaver (samme moenster som temapillen i build_helpers).

TILSTANDENE
-----------
    Done        trinnet er faerdigt
    Current     trinnet er der, hvor vi staar nu
    Pending     ikke naaet endnu (hul knude)
    Skipped     gaelder ikke for denne anmodning ("Not required")

Modulet er DOMAENENEUTRALT: kalderen giver navnene og et udtryk pr. trin,
der svarer med en af de fire tilstande. Der staar intet om materialer,
udstyr eller maalesteder her (issue #204).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_screen import Ctrl, C_MUTED, C_TRANSPARENT
from build_helpers import group, text_ctrl
from design_tokens import ref_hex
import icons
import layout_tokens as lay

SVG_FONT = "font-family='Segoe UI, sans-serif'"
# Samme maal som hubbens stribe, saa de to ser ens ud (issue #139).
NODE_R = 6
NODE_STROKE = 3.2
STRIP_H = 30
# Bredden pr. trin. Navnene staar midt over knuden, og "Objects &
# approvers" er det laengste, der skal kunne staa der.
STEP_W = 150
COMPACT_W = 190

STATE_HEX = {
    "Done": "state-ok-fg",
    "Current": "state-info-fg",
    "Skipped": "state-neutral-fg",
    "Pending": "text-muted",
}
GLYPH = {"Done": "Done", "Current": "In progress", "Skipped": "Skipped"}


def _var(i):
    return "s%d" % (i + 1)


def _color(i):
    body = ",\n        ".join('"%s", %s' % (k, ref_hex(t)) for k, t in STATE_HEX.items())
    return ("Switch(\n        %s,\n        %s,\n        %s\n    )"
            % (_var(i), body, ref_hex("text-muted")))


def _glyph(i):
    body = ", ".join('"%s", "%s"' % (k, icons.WORKFLOW[v]) for k, v in GLYPH.items())
    return 'Switch(%s, %s, "%s")' % (_var(i), body, icons.WORKFLOW_DEFAULT)


def _full_svg(labels):
    """Knuderne paa en linje med navnet over hver - hubbens stribe."""
    n = len(labels)
    w = STEP_W * n
    xs = [int(STEP_W * (i + 0.5)) for i in range(n)]
    y = 23
    parts = ["\"<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
             "viewBox='0 0 %d %d'>\"" % (w, STRIP_H, w, STRIP_H)]
    for i in range(n - 1):
        # Stregen mellem to knuder er groen, naar trinnet foer er forbi.
        done = '(%s = "Done" || %s = "Skipped")' % (_var(i), _var(i))
        parts.append(
            "\"<line x1='%d' y1='%d' x2='%d' y2='%d' stroke-width='2' "
            "stroke-linecap='round' stroke='\" & If(%s, %s, %s) & \"'/>\""
            % (xs[i], y, xs[i + 1], y, done, ref_hex("state-ok-fg"),
               ref_hex("border-default")))
    for i, text in enumerate(labels):
        col = _color(i)
        hollow = '%s = "Pending"' % _var(i)
        parts.append(
            "\"<circle cx='%d' cy='%d' r='%d' stroke-width='1.5' stroke='\" & %s & "
            "\"' fill='\" & If(%s, \"none\", %s) & \"'/>\""
            % (xs[i], y, NODE_R, col, hollow, col))
        parts.append(
            "If(%s, \"\", \"<g transform='translate(%d %d) scale(%s)' fill='none' "
            "stroke='\" & %s & \"' stroke-width='%g' stroke-linecap='round' "
            "stroke-linejoin='round'><path d='\" & %s & \"'/></g>\")"
            % (hollow, xs[i] - NODE_R, y - NODE_R, "%g" % (NODE_R / 12.0),
               ref_hex("text-on-primary"), NODE_STROKE, _glyph(i)))
        parts.append(
            "\"<text x='%d' y='12' text-anchor='middle' %s font-size='11' "
            "font-weight='600' fill='\" & %s & \"'>\" & %s & \"</text>\""
            % (xs[i], SVG_FONT, col, _step_label(i, text)))
    parts.append('"</svg>"')
    return " &\n    ".join(parts)


def _step_label(i, text):
    """Trinnets navn - "Not required", naar trinnet ikke gaelder.

    text er POWER FX, ikke en streng: saa kan de samme tre knuder hedde
    noget andet, naar anmodningen er indsendt (Materials: Rows bliver
    Submitted), uden at vaere en anden stribe."""
    return 'If(%s = "Skipped", "Not required", %s)' % (_var(i), text)


def _position(labels, what):
    """Hvilket trin staar vi paa - nummeret eller navnet.

    Det foerste trin, der ER i gang, ellers det foerste, der ikke er
    faerdigt, ellers det sidste: "2 of 3" skal passe med knuderne."""
    arms = []
    for i, text in enumerate(labels):
        arms.append('%s = "Current", %s' % (_var(i), what(i, text)))
    for i, text in enumerate(labels):
        arms.append('%s = "Pending", %s' % (_var(i), what(i, text)))
    last = len(labels) - 1
    return "If(\n    " + ",\n    ".join(arms) + ",\n    %s\n)" % what(last, labels[last])


def _compact_svg(labels):
    """Den smalle udgave: "2 of 3 - Objects & approvers"."""
    num = _position(labels, lambda i, _t: str(i + 1))
    name = _position(labels, _step_label)
    text = ('%s & " of %d - " & %s' % (num, len(labels), name))
    return ("\"<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
            "viewBox='0 0 %d %d'>\" &\n    "
            "\"<text x='0' y='19' %s font-size='12' font-weight='600' fill='\" & %s & "
            "\"'>\" & %s & \"</text>\" &\n    \"</svg>\""
            % (COMPACT_W, STRIP_H, COMPACT_W, STRIP_H, SVG_FONT,
               ref_hex("state-info-fg"), text))


def strip(prefix, steps, *, hint=None, label='"Progress"'):
    """Striben som en kontrol - eller to, naar der er en hjaelpelinje.

    steps: [(navn, udtryk)] - navnet er Power Fx (fx '"Rows"'), og
    udtrykket svarer "Done", "Current", "Pending" eller "Skipped".
    hint:  Power Fx med en linje under striben, fx hvad der mangler.
    """
    labels = [t for t, _s in steps]
    binds = ",\n    ".join("%s: %s" % (_var(i), fx) for i, (_t, fx) in enumerate(steps))
    narrow = lay.below("Tablet")
    img = ("With(\n    { %s },\n    \"data:image/svg+xml;utf8,\" & EncodeUrl(If(%s,\n    %s,\n"
           "    %s\n    ))\n)" % (binds, narrow, _compact_svg(labels), _full_svg(labels)))
    t = C_TRANSPARENT
    w = lay.if_below("Tablet", str(COMPACT_W), str(STEP_W * len(labels)))
    ctrl = Ctrl("img%sSteps" % prefix, "Image", props={
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": t, "HoverFill": t, "PressedFill": t,
        "Height": str(STRIP_H),
        "Image": img,
        "ImagePosition": "ImagePosition.Fit",
        # Billedet er ikke en knap, men en klassisk Image skal have et
        # TabIndex (check_layout), og 0 goer den laesbar for en skaermlaeser.
        "TabIndex": "0",
        "Width": w,
    }, h=STRIP_H)
    if not hint:
        return ctrl
    line = text_ctrl("txt%sStepsHint" % prefix, hint, size=12, color=C_MUTED,
                     height=18, wrap="false")
    return group("con%sSteps" % prefix, [ctrl, line], direction="Vertical", gap=4,
                 align_items="Start")
