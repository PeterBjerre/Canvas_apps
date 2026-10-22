# -*- coding: utf-8 -*-
"""
Issue #522: Task list and operations-overskriften staar stille.

  * Valid-maerket er vaek; det groenne flueben (status_icon) staar lige foran
    titlen, som i Plan header, og kun naar sektionen er gyldig (VhpOpsValid).
  * Kortet med Total cost og Duration staar oeverst til hoejre i overskriften
    (fra Tablet), bredt nok til hele advarslen om omkostningsgodkendelse.
  * Advarslen aendrer hverken overskriftens eller task-list-raekkens hoejde,
    saa task listen og de to knapper ikke flytter sig.
  * Telefonen (#508) har kortet i fuld bredde nederst i task-list-raekken.

    python3 -m pytest tests/test_tasklist_header_522.py
"""
import os
import re
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Maintenance Plan App", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
OVER = "IfError(Sum(colVhpOperations, Cost) > VhpCostThreshold, false)"


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _block(text, name):
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    m = re.search(r"^( +)%s: \|-\n((?:\1 +.*\n?)+)" % key, block, re.M)
    if not m:
        return None
    return " ".join(ln.strip() for ln in m.group(2).splitlines()).lstrip("=").strip()


def _children(block):
    """Navnene paa containerens direkte boern, i raekkefoelge."""
    m = re.search(r"^( +)Children:\n", block, re.M)
    assert m
    ind = len(m.group(1)) + 2
    return re.findall(r"^ {%d}- (\w+):" % ind, block[m.end():], re.M)


def test_header_is_check_title_and_totals_without_valid_badge():
    t = _text()
    head = _block(t, "conVhpOpsHead")
    kids = _children(head)
    assert kids[:2] == ["icoVhpOpsHeadStatus", "txtVhpOpsHeadTitle"], kids
    assert kids[-1] == "crdVhpOpsTotals", kids
    assert "- bdgVhpOpsHeadBadge:" not in t
    ico = _block(t, "icoVhpOpsHeadStatus")
    assert "ModernIcon@1.1.0" in ico
    assert _prop(ico, "Visible") == "IfError(VhpOpsValid, false)"
    assert '"CheckmarkCircle"' in _prop(ico, "Icon")


def test_totals_card_is_wide_enough_for_the_warning():
    import build_tasklist as bt
    from build_helpers import text_px
    warn = "Plan over 300,000 DKK - needs cost approval"
    assert bt.TOTALS_CARD_W >= text_px(warn, 11, semibold=False) + 32
    card = _block(_text(), "crdVhpOpsTotals")
    assert _prop(card, "Width") == str(bt.TOTALS_CARD_W)
    assert _prop(card, "LayoutMinWidth") == str(bt.TOTALS_CARD_W)
    assert "needs cost approval" in _prop(card, "Description")
    # Fra Tablet og op; telefonen har sit eget kort.
    assert _prop(card, "Visible").startswith("If(LayoutRank < 2, false, ")


def test_warning_moves_neither_header_nor_toolbar():
    t = _text()
    head_h = _prop(_block(t, "conVhpOpsHead"), "Height")
    assert OVER not in head_h, head_h
    tb = _block(t, "conVhpOpsToolbar")
    assert "- crdVhpOpsTotals:" not in tb
    assert "conVhpOpsToolbarGap" not in t
    # Paa een linje (Tablet og op) er raekkens hoejde den samme med og uden
    # advarsel: telefonkortet taeller kun paa mobil.
    tb_h = _prop(tb, "Height")
    assert ("If(LayoutRank < 2, If(%s, 80, 60), 0)" % OVER) in tb_h
    assert ("(If(%s, 80, 60))" % OVER) not in tb_h.replace("If(LayoutRank < 2, If(%s, 80, 60), 0)" % OVER, "")


def test_buttons_stay_on_the_tasklist_row():
    tb = _block(_text(), "conVhpOpsToolbar")
    kids = _children(tb)
    assert kids[:4] == ["conVhpCellTasklist", "btnVhpAddTasklistLines",
                        "btnVhpAddOperation", "drpVhpOpsActions"], kids
    for b in ("btnVhpAddTasklistLines", "btnVhpAddOperation"):
        assert "AlignInContainer.End" in _prop(_block(tb, b), "AlignInContainer")


def test_phone_keeps_totals_in_the_toolbar():
    t = _text()
    card = _block(t, "crdVhpOpsTotalsPhone")
    assert _prop(card, "Visible").startswith("If(LayoutRank < 2, IfError(")
    assert _prop(card, "Visible").endswith(", false)")
    title = _block(t, "txtVhpOpsHeadTitle")
    assert _prop(title, "Text").startswith('If(LayoutRank < 2, "Task list", ')
