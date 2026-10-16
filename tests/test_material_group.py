# -*- coding: utf-8 -*-
"""
Issue #267: varegruppen paa en PM02-operation vaelges i en dropdown fra
MD_MaterialGroup og er ikke laengere et frit tekstfelt.

    python3 -m pytest tests/test_material_group.py
"""
import csv
import os
import re

from conftest import ROOT

SEED = os.path.join(ROOT, "sharepoint", "seed", "MD_MaterialGroup.csv")
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def test_seed_codes_are_unique_sap_material_groups():
    rows = list(csv.DictReader(open(SEED, encoding="utf-8-sig")))
    codes = [r["MaterialGroup"] for r in rows]
    assert len(codes) == 53
    assert len(set(codes)) == len(codes), "dubletter i varegrupperne"
    for c in codes:
        assert re.fullmatch(r"[A-Z]\d\d\.\d\d", c), c
    for r in rows:
        assert r["Description2"].strip(), r["MaterialGroup"]
        assert "  " not in r["CategoryDescription"], r["MaterialGroup"]


def test_material_group_is_a_dropdown_in_table_and_popup():
    text = open(SCREEN, encoding="utf-8").read()
    assert "inpVhpOpMatGrp" not in text
    assert "inpVhpOpMMatGrp" not in text
    for name in ("drpVhpOpMatGrp", "drpVhpOpMMatGrp"):
        m = re.search(r"- %s:\n\s+Control: (\w+)" % name, text)
        assert m, name + " mangler"
        assert m.group(1) == "ModernDropdown"
    assert text.count("{ MaterialGroup: Self.Selected.Value }") == 2


def test_dropdown_keeps_a_material_group_not_in_the_list():
    """B09.03 fra XELEK staar ikke i listen. Linjens egen vaerdi laegges
    foerst i valgene, ellers stod cellen tom paa PM03-linjerne."""
    text = open(SCREEN, encoding="utf-8").read()
    assert text.count("{ Value: If(known, \"\", cur), Display: cur }") >= 2


def test_named_formula_reads_md_material_group():
    text = open(APP, encoding="utf-8").read()
    assert re.search(r"colVhpMaterialGroups = Sort\(ForAll\(MD_MaterialGroup As R,", text)
