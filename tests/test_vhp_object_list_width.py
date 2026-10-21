# -*- coding: utf-8 -*-
"""
Issue #385: Object list-popuppens raekker flugter med popuppens indre
ramme. Listen, raekkens blaa baggrund og teksten regnes af den SAMME
responsive bredde (popuppens Width minus polstringen) - ingen
GALLERY_RESERVE, intet Parent.Width-gaet.

    python3 -m pytest tests/test_vhp_object_list_width.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")

MODAL_W = "Min(760, App.Width - 40)"
LIST_W = "(%s) - 36" % MODAL_W
ROW_W = "(%s) - 2 * 2 - 18" % LIST_W


def _block(text, name):
    m = re.search(r"\n(\s*)- %s:\n" % name, text)
    assert m, name + " mangler"
    ind = len(m.group(1))
    rest = text[m.end():]
    end = re.search(r"\n {0,%d}- \w+:\n" % ind, rest)
    return rest[:end.start()] if end else rest


def _desk(v):
    """Issue #508: hver If(LayoutRank < 2, mobil, ellers) -> ellers-grenen
    (tablet/desktop, som denne test handler om). Andet er uaendret."""
    head = "If(LayoutRank < 2,"
    k = v.find(head)
    while k >= 0:
        depth, comma, end = 0, None, None
        for i in range(k + len(head), len(v)):
            ch = v[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    end = i
                    break
                depth -= 1
            elif ch == "," and depth == 0 and comma is None:
                comma = i
        v = v[:k] + v[comma + 1:end].strip() + v[end + 1:]
        k = v.find(head)
    return v


def _prop(block, key):
    m = re.search(r"\n\s+%s: \|-\n\s+=(.*)" % key, block)
    assert m, key + " mangler"
    return _desk(m.group(1).strip())


def test_list_row_and_text_share_one_width():
    text = open(SCREEN, encoding="utf-8").read()
    modal = _block(text, "conVhpObjListModal")
    assert _prop(modal, "Width") == MODAL_W
    for side in ("Left", "Right"):
        assert _prop(modal, "Padding" + side) == "18"

    gal = _block(text, "galVhpItemObjects")
    assert _prop(gal, "Width") == LIST_W
    assert "Parent.Width" not in _prop(gal, "Width")

    row = _block(text, "rctVhpObjRowBg")
    assert _prop(row, "Width") == ROW_W, "raekken skal fylde hele listens bredde"
    assert not _prop(row, "Width").endswith("- 40"), "GALLERY_RESERVE maa ikke traekkes fra"

    # Mockup 2026-10-21: afkrydsning, kode, beskrivelse og status i hver
    # sin kolonne. Beskrivelsen tager resten af raekken.
    chk = _block(text, "chkVhpObjPick")
    assert _prop(chk, "Width") == "28"
    assert _prop(chk, "X") == "0 + 8 + 0"
    code = _block(text, "txtVhpObjCode")
    assert _prop(code, "X") == "0 + 8 + 0 + (28) + 10"
    desc = _block(text, "txtVhpObjDesc")
    assert _prop(desc, "Width").startswith("Max(0, ((%s) - 8 - 8) - " % ROW_W)
    # Overskriften flugter med raekkerne: 2 + 8 + 28 + 10 fra venstre.
    cols = _block(text, "conVhpObjListCols")
    assert _prop(cols, "PaddingLeft") == "48"
    assert _prop(cols, "PaddingRight") == "28"


def test_selection_behavior_unchanged():
    text = open(SCREEN, encoding="utf-8").read()
    chk = _block(text, "chkVhpObjPick")
    assert "Collect(colVhpObjDraft" in chk
    assert "RemoveIf(colVhpObjDraft, Code = ThisItem.Code)" in chk
    # Planens egen FL kan hverken til- eller fravaelges.
    assert "!ThisItem.Main" in chk
    assert '"Already selected"' in _block(text, "imgVhpObjStatus")
