# -*- coding: utf-8 -*-
"""Issue #530: Valid staar ikke tre gange i Maintenance Plan.

- Items-hovedet har intet Valid-badge.
- Itemets kort har sit groenne flueben, men ikke teksten "Valid".
- Item-sektionen har et groent cirkulaert flueben lige foer "Item" (som det
  foldede planhoved) - kun naar det AKTIVE item er gyldigt, med samme
  betingelse som kortets flueben. Fejltilstanden bevares som udraabstegn."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
for p in (BUILD, os.path.join(ROOT, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_items as items  # noqa: E402
import build_status as st  # noqa: E402

from test_vh_plan_save_edit import _block, _yaml  # noqa: E402
from test_vh_plan_save_edit import _prop as _raw  # noqa: E402


def _norm(s):
    return " ".join(s.split())


def _prop(block, prop):
    return _norm(_raw(block, prop)).lstrip("=")


def test_no_valid_badges_in_items_and_item_headers():
    y = _yaml()
    for name in ("bdgVhpItemsHeadBadge", "bdgVhpEditorHeadBadge"):
        assert f"- {name}:" not in y, name
    # Plan header mistede sit Valid-maerke i issue #548.
    assert "- bdgVhpPlanHeadBadge:" not in y


def test_card_has_no_valid_text_but_keeps_checkmark_and_to_fix():
    y = _yaml()
    text = _prop(_block(y, "txtVhpItemCardStatus"), "Text")
    assert '"Valid"' not in text
    assert 'If(fixN = 0, "", Text(fixN) & " to fix")' in _norm(text)
    icon = _prop(_block(y, "icoVhpItemCardStatus"), "Icon")
    assert _norm(icon).endswith('"CheckmarkCircle", "ErrorCircle")')


def test_item_section_checkmark_sits_before_the_title():
    y = _yaml()
    head = _block(y, "conVhpEditorHead")
    order = re.findall(r"^ *- (\w+):", head, re.M)
    assert order.index("icoVhpEditorStatus") < order.index("txtVhpEditorHeadTitle")
    ico = _block(y, "icoVhpEditorStatus")
    assert _prop(ico, "Icon") == 'If(VhpActiveItemValid, "CheckmarkCircle", "ErrorCircle")'
    vis = _norm(_prop(ico, "Visible"))
    # Kun flueben, naar itemet er gyldigt - ellers kun fejltilstanden.
    assert vis.startswith("(VhpActiveItemValid) || (varVhpItemValidated && !IsBlank(")


def test_active_item_uses_the_same_blockers_as_the_card():
    formulas = {n: e for n, e, _w in st.formulas()}
    fx = _norm(formulas["VhpActiveItemValid"])
    assert fx.startswith("With({ ar: LookUp(colVhpItems, ItemId = varVhpActiveItemId) }, IsEmpty(")
    assert _norm(st.item_blockers("ar.")) in fx
    assert items.ITEM_BLOCKERS == st.item_blockers("ThisItem.")
    assert "ThisItem." not in fx
