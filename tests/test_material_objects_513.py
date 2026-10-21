# -*- coding: utf-8 -*-
"""
Issue #513: Materials' Objects-fane med Object list-popup, skraldespand pr.
funktionsplads, ingen indre scrollbar - og et bredere soegefelt paa listen.

Testene laeser den GENEREREDE skaerm, som Studio kompilerer.

    python3 -m pytest tests/test_material_objects_513.py
"""
import os
import sys

from conftest import ROOT, TOOLS

sys.path.insert(0, TOOLS)
from build_helpers import text_px
import layout_tokens as lay

from test_material_objects import _prop, _ctrl, _children, _mat, EQ

# domain_parts.SEARCH_W - modulet kraever en apps domain_config.
SEARCH_W = 240
MP = os.path.join(ROOT, "BIO SAP App", "ScreenMeasuringPoint.pa.yaml")


def test_object_list_sits_right_after_search_and_add_is_gone():
    y = _mat()
    assert "btnMatObjAdd" not in y
    assert _children("conMatFlActions")[:1] == ["btnMatFlSearch"]
    assert _children("conMatFlActions")[-1] == "btnMatObjList"
    assert _prop("btnMatObjList", "Text") == '"Object list"'
    assert "Set(varMatObjListOpen, true)" in _prop("btnMatObjList", "OnSelect")
    # Hjaelpeteksten taler ikke laengere om Add.
    hint = _prop("txtMatObjHint", "Text")
    assert "press Add" not in hint and "object list" in hint


def test_reopening_keeps_the_selection_and_shows_selected_codes_too():
    fx = _prop("btnMatObjList", "OnSelect")
    # Kladden er listen, som den staar - saa valget bevares.
    assert ("Collect(colMatObjDraft, ForAll(colMatObjects As O, "
            "{ Code: O.Code, Description: O.Description }))") in fx
    # Kandidaterne: soegningens resultater plus de valgte uden for dem.
    assert "ForAll(colMatFl As R" in fx
    assert "Filter(colMatObjects As O, IsBlank(LookUp(colMatFl," in fx


def test_the_popup_ticks_without_duplicates_and_apply_updates_the_list():
    on_check = _prop("chkMatObjPick", "OnCheck")
    assert on_check.startswith("If(\n    !(CountRows(Filter(colMatObjDraft, "
                               "Upper(Trim(Code)) = Upper(Trim(ThisItem.Code)))) > 0)")
    assert "RemoveIf(colMatObjDraft" in _prop("chkMatObjPick", "OnUncheck")
    apply_ = _prop("btnMatObjListApply", "OnSelect")
    assert apply_.startswith("Clear(colMatObjects);\nCollect(colMatObjects, ForAll(colMatObjDraft As D")
    assert "Set(varMatObjListOpen, false)" in apply_
    assert "Patch(" not in apply_
    # Cancel aendrer intet i listen.
    assert "colMatObjects" not in _prop("btnMatObjListCancel", "OnSelect")
    # Status pr. raekke.
    assert '"selected"' in _prop("imgMatObjListStatus", "Image")


def test_remove_is_a_trash_icon_that_only_removes_the_object():
    rem = _ctrl("btnMatObjRemove")["Properties"]
    assert str(rem["Icon"]).lstrip("=") == '"Delete"'
    assert str(rem["Layout"]).lstrip("=") == "ButtonLayout.IconOnly"
    assert str(rem["Tooltip"]).lstrip("=") == '"Remove object"'
    assert "Remove object" in str(rem["AccessibleLabel"])
    fx = str(rem["OnSelect"]).lstrip("=")
    assert fx.startswith("RemoveIf(colMatObjects, Code = ThisItem.Code)")
    assert "Remove(" not in fx.replace("RemoveIf(", "")


def test_the_selected_list_has_no_inner_scrollbar():
    gal = _ctrl("galMatObjects")["Properties"]
    assert str(gal["ShowScrollbar"]).lstrip("=") == "false"
    assert str(gal["TemplatePadding"]).lstrip("=") == "0"
    # Saa hoej som ALLE raekkerne - fanens krop er den eneste scroll.
    assert str(gal["Height"]).lstrip("=") == "Max(CountRows(colMatObjects), 1) * 44"


def test_materials_search_field_fits_its_placeholder_and_the_others_are_unchanged():
    w = int(_prop("inpMatSearch", "Width"))
    ph = "Search FL, supplier, part no., material"
    assert _prop("inpMatSearch", "Placeholder") == f'"{ph}"'
    assert w >= text_px(ph, lay.SIZE_INPUT) + 32 > SEARCH_W
    assert _prop("inpEqSearch", "Width", EQ) == str(SEARCH_W)
    assert _prop("inpMpSearch", "Width", MP) == str(SEARCH_W)


def test_equipment_and_measuring_point_still_have_no_object_list():
    for path in (EQ, MP):
        y = open(path, encoding="utf-8").read()
        assert "ObjList" not in y and "ObjDraft" not in y
