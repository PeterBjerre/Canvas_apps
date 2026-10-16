# -*- coding: utf-8 -*-
"""
Issue #274: godkendelsesstriben i hubbens liste har igen trinnavnene
(System, Cost, Quality, SAP) centreret over hver knude, og striben staar
midt i Approval-kolonnen.

    python3 -m pytest tests/test_hub_approval_labels.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _labels(text):
    return re.findall(r"<text x='(\d+)' y='(\d+)' text-anchor='middle'[^>]*>(\w+)</text>", text)


def test_vh_strip_has_four_labels_centred_over_their_nodes():
    text = _text()
    labels = _labels(text)
    vh = [(int(x), int(y)) for x, y, n in labels if n in ("System", "Cost", "Quality", "SAP")]
    names = [n for _x, _y, n in labels]
    for stage in ("System", "Cost", "Quality", "SAP"):
        assert stage in names, stage
    # Hver etiket staar over en knude med samme x - og knuderne er ens fordelt.
    circles = {int(x): int(y) for x, y in re.findall(r"<circle cx='(\d+)' cy='(\d+)'", text)}
    xs = sorted({x for x, _y in vh if x in (36, 102, 168, 234)})
    assert xs == [36, 102, 168, 234]
    assert {xs[i + 1] - xs[i] for i in range(3)} == {66}
    for x, y in vh:
        assert x in circles, x
        # Etiketten over knuden (r 6), med luft imellem - og inden for 36 px.
        assert y + 6 <= circles[x] - 6, (x, y, circles[x])
        assert circles[x] + 6 + 2 <= 36
    # Striben er symmetrisk om midten af de 270 px.
    assert xs[0] + xs[-1] == 270


def test_strip_is_36_high_and_centred_in_the_column():
    text = _text()
    assert "width='270' height='36' viewBox='0 0 270 36'" in text
    # Containeren i galleriet foldes ud til X/Y; centreringen er det
    # halve af kolonnens ekstra bredde, lagt til billedets X.
    block = text.split("- imgMdRowApproval:", 1)[1].split("\n                              - ", 1)[0]
    x = re.search(r"\n\s+X: \|-\n\s+=(.*)\n", block).group(1)
    assert x.rstrip().endswith("- ((270) + 0 - 0)) / 2)"), x[-80:]
    assert re.search(r"\n\s+Height: \|-\n\s+=36\n", block)


def test_not_required_is_shown():
    assert ">Not required</text>" in _text()
