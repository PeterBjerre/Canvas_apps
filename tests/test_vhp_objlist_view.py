# -*- coding: utf-8 -*-
"""
Issue #406: Object list kan aabnes i en gemt VH-plan i View og viser
itemets objekter skrivebeskyttet. Create og Edit er som foer.

    python3 -m pytest tests/test_vhp_objlist_view.py
"""
import yaml

from test_vhp_view_lock import SCREEN, VIEW, _controls


def _p(c, name, prop):
    return str(c[name][1].get(prop, ""))


def test_button_is_enabled_in_view():
    dm = _p(_controls(), "imgVhpObjList", "DisplayMode")
    # Kun "intet aktivt item" slaar knappen fra i View; kravet om data at
    # vaelge imellem gaelder kun uden for View.
    assert f"(!{VIEW} && !(" in dm
    assert "IsBlank(varVhpActiveItemId) ||" in dm
    # Aabningen fylder stadig kun kladden og cachen - ikke planens data.
    sel = _p(_controls(), "imgVhpObjList", "OnSelect")
    for bad in ("RemoveIf(colVhpItemObjects", "Collect(colVhpItemObjects", "Collect(\n    colVhpItemObjects"):
        assert bad not in sel, bad
    assert "Set(varVhpObjListOpen, true);" in sel


def test_popup_is_read_only_in_view():
    c = _controls()
    # Afkrydsningerne kan ikke aendres, og "Use selected" er skjult.
    # Planens egen Functional Location (Main) er altid laast.
    assert _p(c, "chkVhpObjPick", "DisplayMode").strip() == \
        f"=If({VIEW} || ThisItem.Main, DisplayMode.View, DisplayMode.Edit)"
    assert f"!{VIEW}" in _p(c, "btnVhpObjListUse", "Visible")
    assert VIEW in _p(c, "btnVhpObjListUse", "DisplayMode")
    # Luk er stadig der og roerer ikke planens objekter.
    close = _p(c, "btnVhpObjListClose", "OnSelect")
    assert VIEW not in _p(c, "btnVhpObjListClose", "DisplayMode") + _p(c, "btnVhpObjListClose", "Visible")
    assert "Set(varVhpObjListOpen, false)" in close and "colVhpItemObjects" not in close


def test_view_rows_are_the_chosen_objects():
    c = _controls()
    items = _p(c, "galVhpItemObjects", "Items")
    # Kandidaterne fra soegningen vises ikke i View; de valgte (med
    # beskrivelse) goer.
    assert f"!{VIEW}) As F" in items
    assert "Filter(colVhpItemObjects, ItemId = varVhpActiveItemId)" in items
    assert "LookUp(colVhpObjDesc, Code = O.Code).Description" in items
    assert VIEW in _p(c, "txtVhpObjEmpty", "Visible")
    assert "No objects are linked to this item." in _p(c, "txtVhpObjEmpty", "Text")


def test_screen_parses():
    yaml.safe_load(open(SCREEN, encoding="utf-8"))
