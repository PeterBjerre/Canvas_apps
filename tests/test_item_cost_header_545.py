# -*- coding: utf-8 -*-
"""
Issue #545: Total item cost i Item-sektionens overskrift.

  * Item: maerket "Total item cost" oeverst til hoejre (fra Tablet; telefon:
    egen linje under overskriften), med tooltip og uden planens advarsel.
    Intet Valid-maerke; fluebenet foer "Item" er det samme som foer.
  * Task list and operations: ingen omkostning - kun Duration.

    python3 -m pytest tests/test_item_cost_header_545.py
"""
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_cost_summary_529 import _text, _block, _prop, _children  # noqa: E402

ITEM_SUM = "Coalesce(Sum(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Cost), 0)"
TIP = '"Combined cost from Task list and operations"'


def test_item_header_has_cost_badge_top_right_and_no_valid_badge():
    t = _text()
    kids = _children(_block(t, "conVhpEditorHead"))
    assert kids[:2] == ["icoVhpEditorStatus", "txtVhpEditorHeadTitle"], kids
    assert kids[-1] == "bdgVhpEditorCost", kids
    assert "- bdgVhpEditorHeadBadge:" not in t
    body = _children(_block(t, "conVhpEditorBody"))
    assert body[:2] == ["conVhpEditorHead", "bdgVhpEditorCostPhone"], body


def test_item_cost_badge_shows_item_sum_with_tooltip():
    t = _text()
    for name in ("bdgVhpEditorCost", "bdgVhpEditorCostPhone"):
        b = _block(t, name)
        assert "ModernBadge@1.0.0" in b, name
        content = _prop(b, "Content")
        assert content.startswith('"Total item cost: " & ') and ITEM_SUM in content, name
        assert _prop(b, "Tooltip") == TIP, name
        # Planens advarsel hoerer KUN til Plan header.
        assert "VhpCostThreshold" not in b and "needs cost approval" not in b, name
        assert _prop(b, "Fill") == "C.'state-neutral-bg'", name
        # Saa bred som teksten.
        assert _prop(b, "Width").startswith('Len("Total item cost: "'), name
    assert _prop(_block(t, "bdgVhpEditorCost"), "Visible") == \
        "If(LayoutRank < 2, false, IfError(!IsBlank(varVhpActiveItemId), false))"
    assert _prop(_block(t, "bdgVhpEditorCostPhone"), "Visible") == \
        "If(LayoutRank < 2, IfError(!IsBlank(varVhpActiveItemId), false), false)"


def test_tasklist_section_shows_no_cost():
    t = _text()
    assert "crdVhpOpsTotals" not in t
    for name in ("conVhpOpsHead", "conVhpOpsToolbar"):
        block = _block(t, name)
        assert "Total cost" not in block and "Total item cost" not in block, name
        assert "Cost)" not in block, name
