# -*- coding: utf-8 -*-
"""
Issue #274: godkendelsesstriben i hubbens liste har igen trinnavnene
(System, Cost, Quality, SAP) centreret over hver knude.

Issue #290: hele striben - og "Not required" - staar ved Approval-
kolonnens venstre kant, under overskriften, og er lodret centreret.

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
    xs = sorted({x for x, _y in vh if x in (19, 85, 151, 217)})
    assert xs == [19, 85, 151, 217]
    assert {xs[i + 1] - xs[i] for i in range(3)} == {66}
    for x, y in vh:
        assert x in circles, x
        # Etiketten over knuden (r 6), med luft imellem - og inden for 36 px.
        assert y + 6 <= circles[x] - 6, (x, y, circles[x])
        assert circles[x] + 6 + 2 <= 36


def test_every_strip_starts_at_the_left_edge_with_unchanged_spacing():
    """VH (66 px), Materials (132 px) og MP (91 px) beholder afstandene fra
    #274/#204/#210 - kun flyttet, saa foerste knude staar ved STRIP_X0."""
    text = _text()
    labels = {(int(x), n) for x, _y, n in _labels(text)}
    assert (19, "System") in labels
    assert {(151, "Handover")} <= labels           # Materials: 69/201 -> 19/151
    assert not any(x == 36 or x == 69 or x == 44 for x, n in labels if n == "System")


def test_strip_is_36_high_and_left_aligned_in_the_column():
    text = _text()
    assert "width='270' height='36' viewBox='0 0 270 36'" in text
    # Containeren i galleriet foldes ud til X/Y. Venstrestillet: billedet
    # staar ved kolonnens start (intet halvt overskud lagt til), og
    # klikfladen over striben har samme X.
    block = text.split("- imgMdRowApproval:", 1)[1].split("\n                              - ", 1)[0]
    x = re.search(r"\n\s+X: \|-\n\s+=(.*)\n", block).group(1)
    assert "/ 2" not in x[-120:], x[-120:]
    assert x.rstrip().endswith("+ 0 + 0"), x[-80:]
    assert re.search(r"\n\s+Height: \|-\n\s+=36\n", block)
    hit = text.split("- btnMdRowApproval:", 1)[1].split("\n                              - ", 1)[0]
    hx = re.search(r"\n\s+X: \|-\n\s+=(.*)\n", hit).group(1)
    assert not hx.rstrip().endswith("/ 2)"), hx[-80:]


def test_compact_strip_is_left_aligned_not_stretched():
    text = _text()
    block = text.split("- imgMdRowApprovalC:", 1)[1].split("\n                              - ", 1)[0]
    assert "ImagePosition.Stretch" not in block
    assert re.search(r"\n\s+Width: \|-\n\s+=270\n", block)
    assert re.search(r"\n\s+X: \|-\n\s+=12\n", block)


def test_not_required_is_shown_left_aligned_and_vertically_centred():
    text = _text()
    assert ">Not required</text>" in text
    # Venstre kant ved x 0 (som overskriften), grundlinjen midt i de 36 px.
    assert re.search(r"<text x='0' y='22' text-anchor='start'[^>]*>Not required</text>", text)
    assert "text-anchor='middle'" not in re.findall(r"<text[^>]*>Not required</text>", text)[0]
