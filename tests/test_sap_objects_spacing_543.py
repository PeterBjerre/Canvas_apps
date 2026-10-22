# -*- coding: utf-8 -*-
"""
Issue #543: SAP Objects-popuppen uden vandrette skillestreger mellem
objekterne og med kompakt luft - bjaelken rykket op, raekken saa lav som
touch-klikfladen tillader. Den korte lodrette skillestreg mellem nummer/
kopier og beskrivelse bliver, og hierarkiets streger foelger stadig
skabelonens hoejde (tests/test_sap_tree_524.py regner dem efter).

    python3 -m pytest tests/test_sap_objects_spacing_543.py
"""
import os
import sys

from conftest import ROOT

for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)
import layout_tokens as lay  # noqa: E402
import sap_objects as so  # noqa: E402
from test_hub_sap_objects import _block, _prop, _yaml  # noqa: E402


def _pop():
    return _block(_yaml(), "conMdSapBackdrop")


def test_no_horizontal_rule_between_objects():
    assert "rctMdSapRule" not in _pop()


def test_vertical_separator_is_kept():
    assert "- rctMdSapNoSep:" in _pop()


def test_rows_are_compact():
    # Foer: 6 + 32 + 48 = 86 px pr. objekt.
    assert so.ROW_H < 86
    assert so.BAR_Y <= 2
    # Raekken skal stadig rumme touch-knapperne (kopier, Open in SAP).
    assert so.LINE_H >= lay.HIT_TOUCH
    gal = _block(_pop(), "galMdSapRows") + "\n"
    assert _prop(gal, "TemplateSize") == str(so.ROW_H)


def test_description_fits_inside_the_row():
    pop = _pop()
    for name in ("txtMdSapDesc", "txtMdSapCopied"):
        b = _block(pop, name) + "\n"
        y = eval(_prop(b, "Y"))
        h = int(_prop(b, "Height"))
        assert so.BAR_Y + so.BAR_H <= y and y + h <= so.ROW_H, name
