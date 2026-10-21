# -*- coding: utf-8 -*-
"""
Issue #505: FL-soegningens resultatbesked i VH-planens Item Editor
(Maintenance Plan -> Item) siger kun "<n> Functional Locations found for
<q>." - uden "Select one from the list below.". Tal og soegetekst er
stadig dynamiske; de andre skaermes FL-soegning er uaendret.

    python3 -m pytest tests/test_fl_result_text_505.py
"""
import os
import re
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_flsearch as fl  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
OTHER = [os.path.join(ROOT, "BIO SAP App", f"Screen{s}.pa.yaml")
         for s in ("Equipment", "Material", "Kks", "MeasuringPoint")]


def _fl_msg_blocks(text):
    """Hver Set(varVhpFlMsg, With(...)) i skaermen - FL-soegningens besked."""
    return re.findall(r"Set\(\s*varVhpFlMsg,\s*With\(.*?\n\s*\),", text, re.S)


def test_item_editor_message_has_no_select_hint():
    text = open(SCREEN, encoding="utf-8").read()
    blocks = _fl_msg_blocks(text)
    assert len(blocks) == 2, "Search-knappen og Enter"
    for b in blocks:
        assert "Select one from the list below" not in b
        # Dynamisk: antal og soegetekst, slutter med punktum.
        assert ('Text(n) & " Functional Locations found for " & Upper(q) & "."'
                in b)
        # Raadet ved lange svar er bevaret.
        assert "The list is long" in b


def test_default_search_keeps_select_hint():
    assert "Select one from the list below." in fl.search_action(
        "c", "colX", "varM", raw_var="r")
    assert "Select one from the list below." not in fl.search_action(
        "c", "colX", "varM", raw_var="r", select_hint=False)


def test_other_screens_unchanged():
    for p in OTHER:
        assert "Select one from the list below." in open(p, encoding="utf-8").read(), p
