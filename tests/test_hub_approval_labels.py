# -*- coding: utf-8 -*-
"""
Issue #274: godkendelsesstriben i hubbens liste har igen trinnavnene
(System, Cost, Quality, SAP) centreret over hver knude.

Issue #290: striben - og "Not required" - staar ved Approval-kolonnens
venstre kant, under overskriften, og er lodret centreret.

Issue #318: inde i pillen (btnMdRowApproval) er forloebet centreret foer
pilen: lige meget luft fra pillens venstre kant til den foerste etiket og
fra den sidste etiket til pilen, og knuderne er ligeligt fordelt. Paa
tablet regnes knuderne af billedets egen bredde.

    python3 -m pytest tests/test_hub_approval_labels.py
"""
import os
import re
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "Masterdata Hub", "build"))
import approval_flow as af  # noqa: E402
from build_helpers import label_px  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")
VH = ("System", "Cost", "Quality", "SAP")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _labels(text):
    return re.findall(r"<text x='(\d+)' y='(\d+)' text-anchor='middle'[^>]*>(\w+)</text>", text)


def _block(text, name):
    return text.split(f"- {name}:", 1)[1].split("\n                              - ", 1)[0]


def _prop(block, key):
    return re.search(r"\n\s+%s: \|-\n\s+=(.*)\n" % key, block + "\n").group(1)


def test_vh_strip_has_four_labels_centred_over_evenly_spaced_nodes():
    text = _text()
    vh = [(int(x), int(y), n) for x, y, n in _labels(text) if n in VH]
    for stage in VH:
        assert stage in [n for _x, _y, n in vh], stage
    circles = {int(x): int(y) for x, y in re.findall(r"<circle cx='(\d+)' cy='(\d+)'", text)
               if int(y) == af.NODE_Y}
    xs = af.strip_xs(list(VH), af.STRIP_W)
    assert sorted({x for x, _y, n in vh}) == xs
    steps = {xs[i + 1] - xs[i] for i in range(3)}
    assert max(steps) - min(steps) <= 1, steps
    for x, y, _n in vh:
        assert x in circles, x
        # Etiketten over knuden (r 6), med luft imellem - og inden for 36 px.
        assert y + 6 <= circles[x] - 6, (x, y, circles[x])
        assert circles[x] + 6 + 2 <= af.STRIP_H


def test_padding_before_the_first_label_and_after_the_last_is_balanced():
    """Pillens venstre kant -> foerste etiket = sidste etiket -> pilen."""
    assert af.STRIP_W == af.PILL_W - af.ARROW_W == 254
    for names in (list(VH), ["System", "Handover"], ["System", "Counter", "SAP"]):
        xs = af.strip_xs(names, af.STRIP_W)
        left = xs[0] - label_px(names[0], af.LABEL_SIZE) / 2
        right = af.STRIP_W - (xs[-1] + label_px(names[-1], af.LABEL_SIZE) / 2)
        assert abs(left - af.PILL_PAD) <= 1 and abs(right - af.PILL_PAD) <= 1, (names, left, right)


def test_dynamic_positions_match_the_fixed_ones():
    """Tabletformlen giver de samme x som den faste beregning."""
    for names in (list(VH), ["System", "Handover"], ["System", "Counter", "SAP"]):
        for w in (254, 500, 980):
            fixed = af.strip_xs(names, w)
            exprs = af.strip_xs(names, "W")
            got = [round(eval(e.replace("Round(", "(").replace(", 0)", ")").replace("W", str(w))))
                   for e in exprs]
            assert all(abs(a - b) <= 1 for a, b in zip(fixed, got)), (names, w, fixed, got)


def test_materials_strip_uses_the_same_rule():
    labels = {(int(x), n) for x, _y, n in _labels(_text())}
    xs = af.strip_xs(["System", "Handover"], af.STRIP_W)
    assert {(xs[0], "System"), (xs[1], "Handover")} <= labels
    # Ikke laengere den faste venstrestilling fra #290.
    assert (19, "System") not in labels


def test_wide_strip_is_the_pill_minus_the_arrow_and_shares_its_x():
    text = _text()
    assert "width='254' height='36' viewBox='0 0 254 36'" in text
    assert "width='270' height='36'" not in text
    img = _block(text, "imgMdRowApproval")
    hit = _block(text, "btnMdRowApproval")
    assert _prop(img, "Width") == "254"
    assert _prop(img, "Height") == "36"
    assert "270" in _prop(hit, "Width")
    # Billedet staar ved kolonnens start (#290), og pillen har samme X.
    x = _prop(img, "X")
    assert "/ 2" not in x[-120:], x[-120:]
    assert x.rstrip().endswith("+ 0 + 0"), x[-80:]
    hx = _prop(hit, "X")
    assert not hx.rstrip().endswith("/ 2)"), hx[-80:]
    # Pilen: hoejrestillet med 8 px luft - uaendret.
    assert "Align.Right" in hit and _prop(hit, "PaddingRight") == "8"


def test_compact_strip_follows_the_row_width():
    block = _block(_text(), "imgMdRowApprovalC")
    assert "ImagePosition.Stretch" not in block
    assert _prop(block, "X") == "12"
    # Pillen er raekkens bredde - 24; striben er pillen minus pilen.
    assert _prop(block, "Width").rstrip().endswith("- 24 - 16"), _prop(block, "Width")
    # Tegningen laeser billedets egen bredde, ikke en fast 270.
    assert "width='\" & Round(Self.Width, 0) & \"'" in block
    assert "<text x='\" & p0 & \"'" in block
    assert "Parent.Template" not in block


def test_not_required_is_shown_left_aligned_and_vertically_centred():
    text = _text()
    assert ">Not required</text>" in text
    # Venstre kant ved x 0 (som overskriften), grundlinjen midt i de 36 px.
    assert re.search(r"<text x='0' y='22' text-anchor='start'[^>]*>Not required</text>", text)
    assert "text-anchor='middle'" not in re.findall(r"<text[^>]*>Not required</text>", text)[0]
