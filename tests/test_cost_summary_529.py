# -*- coding: utf-8 -*-
"""
Issue #529: itemets omkostninger adskilt fra planens advarsel.

Task list and operations
  * Valid-maerket er vaek; det groenne flueben (status_icon) staar lige foran
    titlen, som i Plan header, og kun naar sektionen er gyldig (VhpOpsValid).
  * Kortet med det valgte items Total cost og Duration staar oeverst til
    hoejre i overskriften (fra Tablet); telefonen har det nederst i
    task-list-raekken. Kortet viser ALDRIG advarslen om omkostnings-
    godkendelse og har altid samme hoejde.
  * Task listen og de to knapper staar paa samme linje.

Plan header
  * Total cost-maerket staar baade foldet og udfoldet (telefon: egen linje).
  * Over graensen (planens samlede sum > VhpCostThreshold): advarselsfarver
    og hele advarslen som Tooltip; ellers de normale farver og intet tooltip.

    python3 -m pytest tests/test_cost_summary_529.py
"""
import os
import re
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Maintenance Plan App", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
OVER = "IfError(Sum(colVhpOperations, Cost) > VhpCostThreshold, false)"
PLAN_COST_BADGES = ("bdgVhpPlanFoldCost", "bdgVhpPlanHeadCost", "bdgVhpPlanHeadCostPhone")


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


# --- Task list and operations ---------------------------------------------
def test_ops_header_is_check_title_and_totals_without_valid_badge():
    t = _text()
    kids = _children(_block(t, "conVhpOpsHead"))
    assert kids[:2] == ["icoVhpOpsHeadStatus", "txtVhpOpsHeadTitle"], kids
    assert kids[-1] == "crdVhpOpsTotals", kids
    assert "- bdgVhpOpsHeadBadge:" not in t
    ico = _block(t, "icoVhpOpsHeadStatus")
    assert _prop(ico, "Visible") == "IfError(VhpOpsValid, false)"
    assert '"CheckmarkCircle"' in _prop(ico, "Icon")


def test_item_totals_never_show_the_plan_warning():
    t = _text()
    for name in ("crdVhpOpsTotals", "crdVhpOpsTotalsPhone"):
        card = _block(t, name)
        assert "needs cost approval" not in card, name
        assert "VhpCostThreshold" not in card, name
        assert _prop(card, "Description") == "Blank()", name
        assert _prop(card, "Height") == "60", name
        # Kun det valgte items operationer.
        assert "ItemId = varVhpActiveItemId" in _prop(card, "Title"), name
        assert "DurationHours" in _prop(card, "Subtitle"), name
    assert _prop(_block(t, "crdVhpOpsTotals"), "Visible").startswith("If(LayoutRank < 2, false, ")
    assert _prop(_block(t, "crdVhpOpsTotalsPhone"), "Visible").endswith(", false)")


def test_threshold_moves_nothing_in_the_tasklist_section():
    t = _text()
    for name in ("conVhpOpsHead", "conVhpOpsToolbar"):
        assert "VhpCostThreshold" not in _prop(_block(t, name), "Height"), name
    assert "conVhpOpsToolbarGap" not in t


def test_buttons_stay_on_the_tasklist_row():
    tb = _block(_text(), "conVhpOpsToolbar")
    kids = _children(tb)
    assert kids[:4] == ["drpVhpItemTasklist", "btnVhpAddTasklistLines",
                        "btnVhpAddOperation", "drpVhpOpsActions"], kids
    for b in ("btnVhpAddTasklistLines", "btnVhpAddOperation"):
        assert "AlignInContainer.End" in _prop(_block(tb, b), "AlignInContainer")


# --- Plan header -----------------------------------------------------------
def test_plan_cost_badge_in_expanded_and_folded_header():
    t = _text()
    head = _children(_block(t, "conVhpPlanHead"))
    assert head[-2:] == ["bdgVhpPlanHeadCost", "bdgVhpPlanHeadBadge"], head
    assert "bdgVhpPlanFoldCost" in _children(_block(t, "conVhpPlanFoldTop"))
    card = _children(_block(t, "conVhpPlanCard"))
    assert card[:2] == ["conVhpPlanHead", "bdgVhpPlanHeadCostPhone"], card
    # Udfoldet: fra Tablet i overskriften, paa telefonen paa egen linje.
    assert _prop(_block(t, "bdgVhpPlanHeadCost"), "Visible").startswith("If(LayoutRank < 2, false, ")
    assert "If(LayoutRank < 2, IfError(Sum(colVhpOperations, Cost) > 0, false), false)" in \
        _prop(_block(t, "bdgVhpPlanHeadCostPhone"), "Visible")


def test_plan_cost_badge_warns_by_color_and_tooltip_only():
    t = _text()
    for name in PLAN_COST_BADGES:
        b = _block(t, name)
        assert "ModernBadge@1.0.0" in b, name
        assert _prop(b, "Color") == f"If({OVER}, C.'state-warn-fg', C.'text-primary')", name
        assert _prop(b, "Fill") == f"If({OVER}, C.'state-warn-bg', C.'state-neutral-bg')", name
        tip = _prop(b, "Tooltip")
        assert tip.startswith(f'If({OVER}, "Plan over " & ') and tip.endswith(
            '" DKK - needs cost approval", "")'), (name, tip)
        # Ingen synlig advarselslinje: maerkets tekst er kun planens sum.
        content = _prop(b, "Content")
        assert content.startswith('"Total cost: " & ') and "needs cost" not in content, name
        assert "Sum(colVhpOperations, Cost)" in content, name
        assert "needs cost approval" in _prop(b, "AccessibleLabel"), name


def test_plan_total_is_the_sum_of_all_items():
    import build_plan_header as bp
    assert bp.PLAN_COST == "Sum(colVhpOperations, Cost)"
    assert bp.COST_OVER_ON == f"{OVER}"
