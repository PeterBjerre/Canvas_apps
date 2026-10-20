# -*- coding: utf-8 -*-
"""Dynamisk "X to fix" i Maintenance Plan (issue #448).

Itemets kort, trin 2 og Submit regnes af itemets AKTUELLE vaerdier - ikke
af den gemte Status eller af, om Item Editoren er gemt med Save. Item
Editoren skriver hvert felt paa itemet, naar det aendres eller forlades.
Usavede aendringer (ITEM_DIRTY) er tilstand, ikke validering."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
for p in (BUILD, os.path.join(ROOT, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_hero as hero  # noqa: E402
import build_items as items  # noqa: E402
import build_status as st  # noqa: E402

from test_vh_plan_save_edit import _block, _prop, _yaml  # noqa: E402

FORMULAS = {n: e for n, e, _w in st.formulas()}


def _norm(s):
    return " ".join(s.split())


def test_step_item_reads_values_not_saved_status():
    done = FORMULAS["VhpStepItemDone"]
    assert "Status" not in done
    for _n, cond in st.item_required():
        assert cond in done
        assert cond in st.ITEM_RULE
    # "Press Save on every item" er ikke laengere et krav.
    assert "Press Save on every item" not in FORMULAS["VhpItemMissing"]


def test_unsaved_editor_is_not_a_submit_blocker():
    assert hero.CAN_SUBMIT == "VhpCanSubmit"
    assert all(hero.ITEM_DIRTY not in fx for _h, fx, _s in hero.GROUPS)
    assert hero.STEPS[1][1] == "VhpStepItemDone"
    assert items.items_valid_fx() == "VhpItemsValid"
    # Den usavede tilstand bruges stadig - kun til "unsaved changes".
    assert hero.ITEM_DIRTY in hero.HAS_UNSAVED


def test_card_counts_genuine_blockers_from_current_values():
    y = _yaml()
    status = _prop(_block(y, "txtVhpItemCardStatus"), "Text")
    assert "Status" not in status.replace("StatusOptions", "")
    assert "Needs fixing" not in status
    for name in ("Item short text", "Initials", "Task list", "Operations", "Operation details"):
        assert f'n: "{name}"' in status
    # Operationernes betingelser er de samme som reglerne.
    rules = _norm(" ".join(e for _s, _n, e in st.RULES))
    for cond in (st.OP_NO_TEXT, st.OP_NO_MG, st.OP_NO_COST, st.OP_NO_PKG):
        assert _norm(cond) in rules
    assert "CountRows(colVhpItems)" not in status  # intet ekstra pr. kort


def test_editor_fields_write_through_to_item():
    y = _yaml()
    for ctrl, col in (("inpVhpItemShortText", "ShortText"),
                      ("drpVhpItemMainWorkCenter", "MainWorkCenter"),
                      ("drpVhpItemActivityType", "ActivityType"),
                      ("inpVhpItemInitials", "Initials")):
        fx = _prop(_block(y, ctrl), "OnChange")
        assert f"UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, {{ {col}:" in fx, ctrl
    fl = _prop(_block(y, "cmbVhpItemFL"), "OnChange")
    assert "FunctionalLocation: cmbVhpItemFL.Selected.Code" in fl
    # Dropdowns og FL skriver aldrig et tomt valg.
    assert "!IsBlank(drpVhpItemMainWorkCenter.Selected.Value)" in _prop(
        _block(y, "drpVhpItemMainWorkCenter"), "OnChange")
    # Det automatiske valg af foerste soegeresultat skrives ogsaa.
    assert "FunctionalLocation: varVhpFlPick" in y


def test_reset_restores_snapshot():
    y = _yaml()
    reset = _prop(_block(y, "btnVhpResetItem"), "OnSelect")
    assert "varVhpItemBase.ItemId = varVhpActiveItemId" in reset
    for col in items.EDITOR_COLUMNS:
        assert f"{col}: varVhpItemBase.{col}" in reset
    assert items.SNAP_ITEM_BASE in items.RESET_EDITOR_CONTROLS
    assert "Set(varVhpItemBase, First(colVhpItems))" in open(
        os.path.join(ROOT, "BIO SAP App", "App.pa.yaml"), encoding="utf-8").read() + y
