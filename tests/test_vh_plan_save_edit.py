# -*- coding: utf-8 -*-
"""Save/Edit i Maintenance Plan (issue #433): Plan header, Item og Task list
and operations hedder Save (ikke Done), siger "Saving..." mens de gemmer,
bliver skrivebeskyttede og til Edit, naar de er gemt, og Edit laaser op."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
ITEM_LOCK = 'IfError(varVhpActiveItemId in Filter(colVhpSectionLocks, Section = "Item").ItemId, false)'
OPS_LOCK = 'IfError(varVhpActiveItemId in Filter(colVhpSectionLocks, Section = "Ops").ItemId, false)'


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(y, name):
    """Kontrollens egen blok - til naeste kontrol paa samme eller hoejere niveau."""
    lines = y.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^ *- %s:$" % name, line):
            ind = len(line) - len(line.lstrip())
            j = i + 1
            while j < len(lines) and (not lines[j].strip()
                                      or len(lines[j]) - len(lines[j].lstrip()) > ind):
                j += 1
            return "\n".join(lines[i:j])
    raise AssertionError(name)


def _prop(block, prop):
    m = re.search(r"\n( *)%s: \|-\n((?:\1 .*\n?)*)" % prop, block)
    assert m, prop
    return m.group(2)


SAVES = (("btnVhpPlanSave", "varVhpPlanLocked", "plan"),
         ("btnVhpSaveItem", ITEM_LOCK, "item"),
         ("btnVhpTasklistSave", OPS_LOCK, "ops"))


def test_the_three_sections_say_save_then_edit_and_saving_while_saving():
    y = _yaml()
    for name, locked, key in SAVES:
        b = _block(y, name)
        text = _prop(b, "Text")
        assert f'If(IfError(varVhpAct = "{key}", false), "Saving...", If({locked}, "Edit", "Save"))' in text
        assert '"Done"' not in b
        # Ingen besked om Save draft efter en gemt sektion.
        assert "Save draft" not in b and "done:" not in b.lower() and "done." not in b.lower()
        on = _prop(b, "OnSelect")
        assert f'Set(varVhpAct, "{key}")' in on
        assert f'Set(varVhpAct, "{key}:ok")' in on
        # Spaerret, mens en handling koerer.
        assert "DisplayMode.Disabled" in _prop(b, "DisplayMode")


def test_save_locks_only_after_success_and_edit_unlocks():
    y = _yaml()
    for name, section in (("btnVhpSaveItem", "Item"), ("btnVhpTasklistSave", "Ops")):
        on = _prop(_block(y, name), "OnSelect")
        lock = f'Collect(colVhpSectionLocks, {{ ItemId: varVhpActiveItemId, Section: "{section}" }})'
        assert on.count(lock) == 1
        # Laasen saettes efter skrivningen i samlingen - ikke i valideringens gren.
        assert on.index("UpdateIf(") < on.index(lock)
        assert (f'RemoveIf(colVhpSectionLocks, ItemId = varVhpActiveItemId && Section = "{section}")'
                in on)
        # Edit-grenen kommer foer gemningen og koerer ikke "Saving...".
        assert on.index("RemoveIf(colVhpSectionLocks") < on.index("Set(varVhpAct,")
    item = _prop(_block(y, "btnVhpSaveItem"), "OnSelect")
    assert item.index('Status: "valid"') < item.index("Collect(colVhpSectionLocks")
    assert 'Set(varVhpAct, "item:failed")' in item


def test_a_saved_section_is_read_only_like_view_mode():
    y = _yaml()
    ro_item = f"(varVhpViewOnly || {ITEM_LOCK})"
    ro_ops = f"(varVhpViewOnly || {OPS_LOCK})"
    for name in ("inpVhpItemShortText", "drpVhpItemMainWorkCenter", "cmbVhpItemFL",
                 "inpVhpItemInitials", "btnVhpResetItem"):
        assert ro_item in _prop(_block(y, name), "DisplayMode"), name
    for name in ("drpVhpItemTasklist", "inpVhpOpShortText", "inpVhpOpWork", "btnVhpOpDelete",
                 "drpVhpOpsActions"):
        assert ro_ops in _prop(_block(y, name), "DisplayMode"), name
    # Popupperne fra en laast sektion er skrivebeskyttede.
    assert ro_item in _prop(_block(y, "chkVhpObjPick"), "DisplayMode")
    assert ro_ops in _prop(_block(y, "inpVhpMatQty"), "DisplayMode")
    # Sektionens egen Save/Edit laases ikke af sin egen laas.
    assert "colVhpSectionLocks" not in _prop(_block(y, "btnVhpSaveItem"), "DisplayMode")
    assert "colVhpSectionLocks" not in _prop(_block(y, "btnVhpTasklistSave"), "DisplayMode")
    # View-variablen saettes aldrig gennem laasen.
    assert "Set((varVhpViewOnly" not in y


def test_locks_belong_to_the_plan_that_is_open():
    y = _yaml()
    # Skemaet kendes, foer den foerste Save (som de andre arbejdssamlinger).
    assert 'If(false, ClearCollect(colVhpSectionLocks, { ItemId: 0, Section: "" }))' in y
    assert y.count("Clear(colVhpSectionLocks)") >= 2   # New request og aabning


def test_texts_say_save_not_done():
    y = _yaml()
    app = open(APP, encoding="utf-8").read()
    for text in (y, app):
        assert "Press Done" not in text and "press Done" not in text
    assert "Press Save in the plan header." in app
    assert "Press Save in the plan header before adding items." in y
