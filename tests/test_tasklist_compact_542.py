# -*- coding: utf-8 -*-
"""
Issue #542: Task list and operations er strammet op.

  * Etiketten "Task list *" og dens linje er vaek - dropdownen staar direkte
    i raekken med Add lines from task list og Manual operation, lige under
    overskriften. Raekken er saa hoej som en knap, ikke etiket + felt.
  * Kortet med Total cost/Duration og fluebenet bliver i overskriften (#529).
  * Skaermlaeseren faar stadig "Task list, required".

    python3 -m pytest tests/test_tasklist_compact_542.py
"""
from test_cost_summary_529 import _text, _block, _prop, _children


def test_no_tasklist_label_or_cell():
    t = _text()
    assert "conVhpCellTasklist" not in t
    assert "lblVhpCellTasklist" not in t


def test_dropdown_sits_directly_in_the_toolbar_row():
    tb = _block(_text(), "conVhpOpsToolbar")
    assert _children(tb)[:3] == ["drpVhpItemTasklist", "btnVhpAddTasklistLines",
                                 "btnVhpAddOperation"]
    drp = _block(tb, "drpVhpItemTasklist")
    assert _prop(drp, "AccessibleLabel") == '"Task list, required"'
    assert _prop(drp, "Height") == "If(LayoutRank < 2, 44, 36)"
    # Ingen 20 + 6 px etiketlinje i raekkens hoejde laengere.
    assert "20 + 6 +" not in _prop(tb, "Height")


def test_header_keeps_check_and_totals_card():
    head = _children(_block(_text(), "conVhpOpsHead"))
    assert head[0] == "icoVhpOpsHeadStatus", head
    assert "crdVhpOpsTotals" in head, head
