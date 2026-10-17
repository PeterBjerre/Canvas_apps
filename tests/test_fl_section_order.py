# -*- coding: utf-8 -*-
"""
Issue #309: paa Functional Location-siden staar Rows oeverst som det
primaere arbejdsomraade, derefter Classes og saa Structure.

Testen laeser den GENEREREDE skaerm i BIO SAP App og laaser raekkefoelgen
af kortene i conFlBody, saa en senere aendring ikke flytter Rows ned.

    python3 -m pytest tests/test_fl_section_order.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")


def _body_children(text):
    """Navnene paa conFlBody's direkte boern, i raekkefoelge."""
    m = re.search(r"^( *)- conFlBody:\n", text, re.M)
    assert m, "conFlBody mangler"
    indent = len(m.group(1))
    rest = text[m.end():]
    kids = re.search(r"^( *)Children:\n", rest, re.M)
    assert kids, "conFlBody har ingen Children"
    child_indent = len(kids.group(1)) + 2
    names = []
    for line in rest[kids.end():].split("\n"):
        stripped = line.lstrip(" ")
        lead = len(line) - len(stripped)
        if stripped and lead <= indent:
            break
        if lead == child_indent and stripped.startswith("- "):
            names.append(stripped[2:].rstrip(":"))
    return names


def test_rows_classes_structure_order():
    text = open(SCREEN, encoding="utf-8").read()
    kids = _body_children(text)
    assert kids[:3] == ["conFlRowsCard", "conFlClassesCard", "conFlStructCard"], kids


def test_rows_card_keeps_its_actions():
    """Paste rows, Add row, tabellen og valideringen bliver i Rows-kortet."""
    text = open(SCREEN, encoding="utf-8").read()
    start = text.index("- conFlRowsCard:")
    end = text.index("- conFlClassesCard:")
    card = text[start:end]
    for name in ("btnFlPasteRows", "btnFlAddRow", "galFlRows", "txtFlRowsCount",
                 "btnFlVerify", "txtFlInfo"):
        assert "- %s:" % name in card, name
