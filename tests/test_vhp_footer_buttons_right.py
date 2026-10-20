# -*- coding: utf-8 -*-
"""
Issue #449: Item Editorens knapper (Reset + Save / Reset + Edit) staar
altid nederst til hoejre. Naar itemet er gemt, skjules teksten i foden;
foden skal derfor vaere hoejrestillet, saa knapperne ikke rykker til
venstre. Det samme gaelder de andre sektionsfoedder paa skaermen.

    python3 -m pytest tests/test_vhp_footer_buttons_right.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
FOOTERS = ("conVhpEditorFooter", "conVhpPlanFooter", "conVhpOpsFooter")


def _props(text, name):
    m = re.search(r"\n(\s*)- %s:\n" % name, text)
    assert m, name + " mangler"
    ind = len(m.group(1))
    out = []
    for line in text[m.end():].splitlines():
        if line.strip() and len(line) - len(line.lstrip()) <= ind:
            break
        out.append(line)
    return "\n".join(out)


def test_footers_are_right_aligned():
    text = open(SCREEN, encoding="utf-8").read()
    for name in FOOTERS:
        block = _props(text, name)
        # Kun foden selv - ikke boernene.
        own = block.split("Children:")[0]
        assert "=LayoutJustifyContent.End" in own, name
        btns = _props(text, name + "Btns").split("Children:")[0]
        assert "=LayoutJustifyContent.End" in btns, name + "Btns"


def test_item_editor_buttons_in_same_row_in_all_states():
    """Reset og Save/Edit er de samme to knapper i samme raekke - kun
    teksten skifter mellem Save og Edit."""
    text = open(SCREEN, encoding="utf-8").read()
    btns = _props(text, "conVhpEditorFooterBtns")
    assert btns.index("- btnVhpResetItem:") < btns.index("- btnVhpSaveItem:")
