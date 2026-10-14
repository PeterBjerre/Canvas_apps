# -*- coding: utf-8 -*-
"""VH-planens item-editor og titel efter mockuppen (UX-review 2026-10, M5 del 2)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(y, name, n=3000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_the_editor_says_which_item_and_can_delete_it():
    y = _yaml()
    which = _block(y, "txtVhpEditorWhich")
    assert "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ShortText" in which
    delete = _block(y, "btnVhpEditorDelete", 5000)
    assert "{ id: varVhpActiveItemId," in delete
    assert "RemoveIf(colVhpItems, ItemId = id)" in delete
    # Det samme som kortets Delete - bare paa det aktive item.
    card = _block(y, "btnVhpRemoveItem", 5000)
    assert "{ id: ThisItem.ItemId," in card


def test_the_subtitle_is_the_plan_name_when_there_is_one():
    sub = _block(_yaml(), "txtVhpSub", 4000)
    assert "IsBlank(Trim(varVhpPlan.PlanText))" in sub
