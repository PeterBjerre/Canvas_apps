# -*- coding: utf-8 -*-
"""Alle datovaelgere viser og tolker datoen som DD-MM-YYYY (issue #235).

Formatet staar eet sted (layout_tokens.DATE_PICKER_FMT) og saettes af
build_helpers.date_picker. Testen laeser de GENEREREDE skaerme i den samlede
app og kraever, at hver datovaelger bruger det faelles format og den
faelles pladsholder - ogsaa en, der en dag bygges uden om date_picker.
"""
import glob
import os
import re

from conftest import ROOT

import layout_tokens as lay
from build_helpers import date_picker

APP = os.path.join(ROOT, "BIO SAP App")
PICKER_TYPES = ("ModernDatePicker", "DatePicker", "Classic/DatePicker")


def _props_block(lines, i):
    """Egenskaberne under kontrollen paa linje i: {navn: formel}."""
    ctrl_indent = len(lines[i]) - len(lines[i].lstrip())
    props, j = {}, i + 1
    while j < len(lines) and lines[j].strip() != "Properties:":
        j += 1
    j += 1
    prop_indent = None
    while j < len(lines):
        line = lines[j]
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent <= ctrl_indent:
            break
        m = re.match(r"^(\s+)([A-Za-z]+): \|-$", line)
        if m and (prop_indent is None or len(m.group(1)) == prop_indent):
            prop_indent = len(m.group(1))
            props[m.group(2)] = lines[j + 1].strip()
        elif prop_indent is not None and line.strip() and indent < prop_indent:
            break
        j += 1
    return props


def _pickers():
    found = []
    for path in sorted(glob.glob(os.path.join(APP, "*.pa.yaml"))):
        lines = open(path, encoding="utf-8").read().splitlines()
        for i, line in enumerate(lines):
            m = re.match(r"^\s+Control: (\S+)$", line)
            if m and m.group(1).split("@")[0] in PICKER_TYPES:
                name = lines[i - 1].strip().rstrip(":").lstrip("- ")
                found.append((os.path.basename(path), name, _props_block(lines, i)))
    return found


def test_faelles_format_er_dd_mm_yyyy():
    assert lay.DATE_PICKER_FMT == "dd-mm-yyyy"
    assert lay.DATE_PICKER_PLACEHOLDER == "dd-mm-yyyy"


def test_builder_bruger_faelles_format():
    ctrl = date_picker("dteTest", "varTest")
    assert ctrl.props["Format"] == f'"{lay.DATE_PICKER_FMT}"'
    assert ctrl.props["Placeholder"] == f'"{lay.DATE_PICKER_PLACEHOLDER}"'


def test_alle_genererede_datovaelgere_bruger_faelles_format():
    pickers = _pickers()
    assert pickers, "ingen datovaelgere fundet - testen leder forkert"
    for screen, name, props in pickers:
        assert props.get("Format") == f'="{lay.DATE_PICKER_FMT}"', (screen, name, props.get("Format"))
        assert props.get("Placeholder") == f'="{lay.DATE_PICKER_PLACEHOLDER}"', (
            screen, name, props.get("Placeholder"))
