# -*- coding: utf-8 -*-
"""
Issue #573: et klik hvor som helst paa raekken aabner raekkens sidepanel i
Materials, Equipment, Measuring Point og FL's Classes - hubbens og Issue
Boards klikflade (build_helpers.row_hit). Ikonerne ligger OVEN PAA
klikfladen og goer kun deres eget.

    python3 -m pytest tests/test_row_click_573.py
"""
import os
import re

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")

# (skaerm, galleri, klikflade, raekkens aabne-ikon, ikonerne oven paa)
CASES = [
    ("ScreenMaterial.pa.yaml", "galMatRows", "btnMatRowHit", "btnMatRowOpen",
     ["btnMatRowOpen", "btnMatRowDocs", "btnMatRowObjects", "btnMatRowCopy", "btnMatRowDelete",
      "btnMatRowOpenC", "btnMatRowDeleteC"]),
    ("ScreenEquipment.pa.yaml", "galEqRows", "btnEqRowHit", "btnEqRowOpen",
     ["btnEqRowOpen", "btnEqRowDocs", "btnEqRowCopy", "btnEqRowDelete", "btnEqRowOpenC", "btnEqRowDeleteC"]),
    ("ScreenMeasuringPoint.pa.yaml", "galMpRows", "btnMpRowHit", "btnMpRowOpen",
     ["btnMpRowOpen", "btnMpRowCopy", "btnMpRowDelete", "btnMpRowOpenC", "btnMpRowDeleteC"]),
    ("ScreenFunctionalLocation.pa.yaml", "galFlClassRows", "btnFlCRowHit", "btnFlCOpen",
     ["btnFlCOpen"]),
]


def _gallery(text, gal):
    """Galleriets blok: fra '- gal:' til naeste kontrol paa samme indrykning."""
    m = re.search(r"^( *)- %s:\n" % gal, text, re.M)
    assert m, gal + " mangler"
    ind = m.group(1)
    rest = text[m.end():]
    end = re.search(r"^%s- \w+:\n" % ind, rest, re.M)
    return rest[:end.start()] if end else rest


def _ctrl(block, name):
    m = re.search(r"^( *)- %s:\n" % name, block, re.M)
    assert m, name + " mangler"
    ind = m.group(1)
    rest = block[m.end():]
    end = re.search(r"^%s- \w+:\n" % ind, rest, re.M)
    return m.start(), rest[:end.start()] if end else rest


def _prop(body, key):
    m = re.search(r"^ +%s: \|-\n((?: {4,}.*\n?)+?)(?=^ +\w+: \|-|\Z)" % key, body, re.M)
    assert m, key + " mangler"
    return "\n".join(l.strip() for l in m.group(1).splitlines())


@pytest.mark.parametrize("screen,gal,hit,open_,on_top", CASES)
def test_row_hit_opens_same_panel_as_icon(screen, gal, hit, open_, on_top):
    block = _gallery(open(os.path.join(APP, screen), encoding="utf-8").read(), gal)
    pos, body = _ctrl(block, hit)
    assert re.search(r"Control: Classic/Button", body)
    # Hubbens tilstande: hover, tryk og tastaturfokus.
    assert "HoverFill: |-\n" in body and "C.'row-hover'" in body
    assert "C.'row-pressed'" in body
    assert "FocusedBorderThickness" in body and _prop(body, "TabIndex") == "=0"
    # Samme handling som Edit/View-ikonet - i den aktuelle tilstand.
    _p, icon = _ctrl(block, open_)
    assert _prop(body, "OnSelect") == _prop(icon, "OnSelect")
    # Ikonerne ligger efter (= oven paa) klikfladen.
    for name in on_top:
        p, _b = _ctrl(block, name)
        assert p > pos, f"{name} ligger under {hit}"


def test_fl_classes_marks_open_row():
    block = _gallery(open(os.path.join(APP, "ScreenFunctionalLocation.pa.yaml"),
                          encoding="utf-8").read(), "galFlClassRows")
    head = block.split("- txtFlCNo:")[0]
    assert "ThisItem.RowGuid = varFlDetailRow" in _prop(head, "TemplateFill")
