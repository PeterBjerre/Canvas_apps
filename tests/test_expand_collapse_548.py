# -*- coding: utf-8 -*-
"""Issue #548: eet moenster for at folde FL's Classes og VH-planens Plan
header (mobile.collapsible / mobile.fold_head).

- Chevronen staar fast yderst til hoejre - aaben og lukket - og skifter kun
  retning. Titel og opsummering staar til venstre.
- Hele overskriften folder: et gennemsigtigt klik-lag (row_hit) over
  raekken med chevronens handling.
- Plan header: ingen Show/Hide-tekst og intet Valid-maerke. Det groenne
  flueben staar foran titlen, kun naar planhovedet er gyldigt, i den samme
  overskrift foldet og udfoldet. Total cost bliver.

    python3 -m pytest tests/test_expand_collapse_548.py
"""
import os
import re

from conftest import ROOT

FL = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")
VHP = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
FOLD = "varVhpPlanLocked && !IfError(varVhpPlanShow, false)"
TOGGLE = "Set(varVhpPlanShow, !IfError(varVhpPlanShow, false))"


def _read(p):
    return open(p, encoding="utf-8").read()


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
    m = re.search(r"^( +)Children:\n", block, re.M)
    assert m
    ind = len(m.group(1)) + 2
    return re.findall(r"^ {%d}- (\w+):" % ind, block[m.end():], re.M)


def _own(block):
    """Kun kontrollens egne egenskaber (foer dens boern)."""
    return block.split("Children:")[0]


def _layer(text, wrap, row, hit):
    """Overskriften er en ManualLayout-container: raekken og klik-laget
    OVEN PAA (sidst = oeverst)."""
    w = _block(text, wrap)
    assert "Variant: ManualLayout" in w.split("Properties:")[0], wrap
    assert _children(w) == [row, hit]
    h = _block(text, hit)
    assert "Control: Classic/Button" in h
    assert _prop(h, "Color") == "RGBA(0, 0, 0, 0)"
    assert _prop(h, "Width") == "Parent.Width" and _prop(h, "Height") == "Parent.Height"
    return h


def test_fl_classes_header_is_one_clickable_row_with_the_chevron_at_the_end():
    t = _read(FL)
    hit = _layer(t, "conFlClassesFoldHead", "conFlClassesFold", "btnFlClassesFoldHeadHit")
    chev = _block(t, "btnFlClassesFold")
    assert _prop(hit, "OnSelect") == _prop(chev, "OnSelect")
    assert _prop(hit, "Text") == _prop(chev, "AccessibleLabel")
    row = _block(t, "conFlClassesFold")
    kids = _children(row)
    assert kids[0] == "txtFlClassesFoldTitle" and kids[-1] == "btnFlClassesFold", kids
    # Opsummeringen skjules, naar Classes er aaben - SpaceBetween holder
    # chevronen yderst til hoejre alligevel.
    assert "LayoutJustifyContent.SpaceBetween" in _own(row)
    # Kortets foerste barn er overskriften (titlen staar i chevronlinjen).
    assert _children(_block(t, "conFlClassesCard"))[0] == "conFlClassesFoldHead"


def test_every_collapsible_keeps_its_chevron_at_the_right_edge():
    for screen in os.listdir(os.path.join(ROOT, "BIO SAP App")):
        if not screen.startswith("Screen"):
            continue
        t = _read(os.path.join(ROOT, "BIO SAP App", screen))
        for name in re.findall(r"^ *- (con\w+Fold):\n", t, re.M):
            row = _block(t, name)
            if "LayoutDirection.Horizontal" not in _own(row):
                continue
            if not _children(row)[-1].startswith("btn"):
                continue
            assert "LayoutJustifyContent.SpaceBetween" in _own(row), (screen, name)


def test_plan_header_is_the_same_row_folded_and_expanded():
    t = _read(VHP)
    hit = _layer(t, "conVhpPlanHeadFold", "conVhpPlanHead", "btnVhpPlanHeadFoldHit")
    head = _block(t, "conVhpPlanHead")
    assert _children(head) == ["icoVhpPlanHeadStatus", "txtVhpPlanHeadTitle", "conVhpLegend",
                               "conVhpPlanHeadGap", "bdgVhpPlanHeadCost", "btnVhpPlanFold"]
    # Overskriften folder aldrig selv bort.
    assert _prop(_own(head), "Visible") is None
    assert _prop(_own(_block(t, "conVhpPlanHeadFold")), "Visible") is None
    # Chevron og klik-lag: kun naar planhovedet kan foldes, samme handling.
    chev = _block(t, "btnVhpPlanFold")
    assert _prop(chev, "Visible") == "varVhpPlanLocked"
    assert _prop(hit, "Visible") == "varVhpPlanLocked"
    assert _prop(chev, "OnSelect") == TOGGLE and _prop(hit, "OnSelect") == TOGGLE
    # Kun retningen skifter: op udfoldet, ned foldet.
    assert _prop(chev, "Image").count(f"If(!({FOLD}), ") == 1
    assert _prop(chev, "AccessibleLabel") == (
        f'If(!({FOLD}), "Collapse Plan header", "Expand Plan header")')
    # Laget ligger over Total cost - advarslen staar i lagets tooltip.
    tip = _prop(hit, "Tooltip")
    assert tip.startswith("If(IfError(Sum(colVhpOperations, Cost) > VhpCostThreshold, false), ")
    assert "needs cost approval" in tip


def test_plan_header_has_no_show_hide_and_no_valid_badge():
    t = _read(VHP)
    for gone in ("btnVhpPlanShow", "btnVhpPlanHide", "bdgVhpPlanHeadBadge",
                 "conVhpPlanFoldRow", "icoVhpPlanFoldStatus", "bdgVhpPlanFoldCost"):
        assert f"- {gone}:" not in t, gone
    card = _block(t, "conVhpPlanCard")
    assert '"Valid"' not in card
    assert _children(_block(t, "conVhpPlanFooterBtns")) == ["btnVhpPlanReset", "btnVhpPlanSave"]


def test_plan_checkmark_only_when_valid():
    ico = _block(_read(VHP), "icoVhpPlanHeadStatus")
    assert _prop(ico, "Visible") == "IfError(VhpPlanValid, false)"
    assert _prop(ico, "Icon") == 'If(VhpPlanValid, "CheckmarkCircle", "ErrorCircle")'


def test_plan_summary_shows_only_when_folded():
    t = _read(VHP)
    s = _block(t, "txtVhpPlanFoldSummary")
    assert _prop(s, "Visible") == FOLD
    for name in ("conVhpPlanGrid", "conVhpPlanFooter", "conVhpPlanHelp"):
        assert f"!({FOLD})" in _prop(_own(_block(t, name)), "Visible"), name
