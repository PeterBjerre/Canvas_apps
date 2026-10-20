# -*- coding: utf-8 -*-
"""
Issue #455: Functional Location og objekterne bevares ved Edit, Copy og
Reset i VH-planens Item Editor.

    python3 -m pytest tests/test_vhp_preserve_fl_455.py
"""
import os
import sys

from test_vhp_view_lock import _controls

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fl_picker  # noqa: E402


def _p(c, name, prop):
    return str(c[name][1].get(prop, ""))


def test_copy_keeps_fl_and_objects():
    sel = _p(_controls(), "btnVhpCopyItem", "OnSelect")
    assert 'FunctionalLocation: ""' not in sel
    assert "FunctionalLocation: If(keepFl, src.FunctionalLocation" in sel
    assert "FlDescription: If(keepFl, src.FlDescription" in sel
    # Objekterne kopieres - kun naar FL'en passer til planens vaerk.
    assert "Filter(colVhpItemObjects, keepFl && ItemId = varVhpActiveItemId) As OBJ" in sel
    assert "Upper(Left(Trim(src.FunctionalLocation), 3))" in sel
    assert "Functional Location cleared on the copied item" not in sel


def test_empty_combo_or_new_search_does_not_drop_objects():
    c = _controls()
    # Kun et nyt, ANDET FL-valg fjerner objekter - og kun dem uden for den.
    for name, prop in (("cmbVhpItemFL", "OnChange"), ("btnVhpFlSearch", "OnSelect")):
        fx = _p(c, name, prop)
        for part in fx.split("RemoveIf(colVhpItemObjects")[1:]:
            assert part.lstrip().startswith(", ItemId = varVhpActiveItemId && !StartsWith(Code,"), (name, part[:80])


def test_save_falls_back_to_item_fl():
    sel = _p(_controls(), "btnVhpSaveItem", "OnSelect")
    assert ("Coalesce(cmbVhpItemFL.Selected.Code, "
            "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation)") in sel


def test_selected_display_is_not_a_new_search():
    fx = fl_picker.items_fx("colX", "varBusy", "varLast")
    assert "IsBlank(LookUp(colX, Upper(Trim(Display)) = Upper(q)).Code)" in fx
