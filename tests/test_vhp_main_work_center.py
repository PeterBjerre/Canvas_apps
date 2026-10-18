# -*- coding: utf-8 -*-
"""
MainWorkCenter paa et genaabnet item (2026-10-16).

Titlen i MainWorkCenters er polstret med mellemrum ("AVVAP   "), mens
colVhpMainWorkCenters er trimmet. Indlaesningen tog opslagets Value uden
Trim, saa dropdownen stod tom, og Save draft sendte Blank() til den
paakraevede kolonne: "Network error when using Patch function:
[MaintenanceItems] Field 'MainWorkCenter' ...".

    python3 -m pytest tests/test_vhp_main_work_center.py
"""
import json
import os

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def test_column_is_a_required_lookup():
    raw = open(SCHEMA, encoding="utf-8-sig").read()
    i = raw.index('"internalName":  "MainWorkCenter"')
    block = raw[i:i + 400]
    assert '"type":  "Lookup"' in block and '"required":  true' in block


def test_load_trims_the_lookup_value():
    text = _text()
    assert "MainWorkCenter: Trim(IT.MainWorkCenter.Value)" in text
    assert "MainWorkCenter: IT.MainWorkCenter.Value" not in text


def test_save_trims_before_lookup():
    text = _text()
    assert "LookUp(colVhpMainWorkCenters, Value = IT.MainWorkCenter)" not in text
    assert "LookUp(colVhpMainWorkCenters, Value = Trim(IT.MainWorkCenter))" in text


def test_save_stops_before_patch_when_an_item_has_no_work_center():
    text = _text()
    # Teksten daekker nu alle fire paakraevede felter (R2-008).
    i = text.index("main work center on every item before saving")
    j = text.index("Patch(", i - 2000)
    assert j > i, "tjekket skal ligge foer foerste Patch i gemningen"
