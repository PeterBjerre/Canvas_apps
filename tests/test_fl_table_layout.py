# -*- coding: utf-8 -*-
"""
Issue #468: Rows og Classes er eet tabelmoenster.

  - Samme etiketter, raekkefoelge og bredder for de faelles kolonner, og
    de staar lige under hinanden.
  - Hver tabels egne kolonner efter de faelles; Actions/Edit lige efter
    den sidste kolonne - tabellen fylder ikke kortet ud.
  - Redigerbart i Rows, kun til visning i Classes.
  - Samme raekkehoejde, overskrift og mellemrum.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_table_layout.py
"""
import test_fl_spool_row as T

SHARED = ["#", "Functional Location", "Description", "StrIndicator", "Class", "Room",
          "Sort field", "ABC indicator", "ATEX"]


def _heads(name):
    return [T._prop(n, "Text").strip('"') for n in T._children(name)]


def test_shared_columns_first_in_both_tables():
    rows, cls = _heads("conFlRowsHead"), _heads("conFlClsHead")
    assert rows[:len(SHARED)] == SHARED == cls[:len(SHARED)]
    assert rows[len(SHARED):] == ["Class data", "Manufacturer", "Warranty", "Status", "Actions"]
    assert cls[len(SHARED):] == ["Edit"]
    # Samme bredde pr. faelles kolonne.
    for r, c in zip(T._children("conFlRowsHead")[:len(SHARED)],
                    T._children("conFlClsHead")[:len(SHARED)]):
        assert T._prop(r, "Width") == T._prop(c, "Width"), (r, c)


def test_classes_are_read_only_and_edit_follows_atex():
    kids = T._children("galFlClassRows")
    for gone in ("inpFlCFl", "inpFlCDesc", "txtFlCInfo"):
        assert gone not in kids, gone
    cells = ["txtFlCNo", "txtFlCFl", "txtFlCDesc", "txtFlCStr", "txtFlCCls", "txtFlCRoom",
             "txtFlCSort", "txtFlCAbc", "txtFlCAtex", "btnFlCOpen"]
    assert [k for k in kids if k in cells] == cells
    for c in cells[:-1]:
        assert T._ctrl(c)["Control"] == "ModernText", c
    # Raekkens foerste besked staar nu i Edit's tooltip.
    assert "ThisItem.FirstIssue" in T._prop("btnFlCOpen", "Tooltip")
    # Rows er stadig redigerbar.
    for c in ("inpFlRowFl", "inpFlRowDesc", "inpFlRowRoom", "inpFlRowSort"):
        assert T._ctrl(c)["Control"] == "ModernTextInput", c


def test_tables_are_not_stretched_to_the_card():
    p = T._parts()
    # Tabellernes bredde er summen af kolonnerne - ikke Max(kortet, ...).
    for w in (p.V_W, p.C_W):
        assert "Max((" not in w.split("Min(")[0], w
    assert T._prop("galFlClassRows", "Width") == p.C_GAL_W
    assert T._prop("galFlRows", "Width") == p.V_GAL_W
    # Edit staar lige efter ATEX - samme X som Rows' Class data.
    assert T._prop("btnFlCOpen", "X") == T._prop("btnFlRowClassData", "X")


def test_same_row_height_and_header_style():
    assert T._prop("galFlRows", "TemplateSize") == T._prop("galFlClassRows", "TemplateSize")
    assert T._prop("conFlRowsHead", "LayoutGap") == T._prop("conFlClsHead", "LayoutGap")
    for prop in ("Size", "Color", "FontWeight", "Height"):
        assert T._prop("txtFlRowsHeadFl", prop) == T._prop("txtFlClsHeadFl", prop), prop
