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


def test_material_group_field_shows_code_and_opens_list():
    """Peter 2026-10-16: feltet viser kun koden og beholder sin bredde;
    listen viser koden og beskrivelsen. Der gemmes kun koden."""
    text = open(SCREEN, encoding="utf-8").read()
    for name in ("inpVhpOpMatGrp", "inpVhpOpMMatGrp", "drpVhpOpMatGrp", "drpVhpOpMMatGrp"):
        assert "- %s:" % name not in text, name
    for name in ("btnVhpOpMatGrp", "btnVhpOpMMatGrp"):
        m = re.search(r"- %s:\n\s+Control: (\w+)" % name, text)
        assert m, name + " mangler"
        assert m.group(1) == "ModernButton"
    assert "Set(varVhpMgOpNo, ThisItem.OperationNo)" in text
    assert "Set(varVhpMgOpNo, varVhpOpMNo)" in text
    assert "{ MaterialGroup: ThisItem.Value }" in text
    assert re.search(r"- galVhpMatGroups:\n\s+Control: Gallery", text)


def test_table_column_keeps_its_width():
    import importlib.util, sys
    build = os.path.join(ROOT, "Maintenance Plan App", "build")
    sys.path.insert(0, build)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build_tasklist
    assert dict(build_tasklist.OPS_COLS)["MAT.GRP"] == 90


def test_named_formula_reads_md_material_group():
    text = open(APP, encoding="utf-8").read()
    assert re.search(r"colVhpMaterialGroups = Sort\(ForAll\(MD_MaterialGroup As R,", text)


def test_list_shows_code_and_material_group_description():
    app = open(APP, encoding="utf-8").read()
    assert "Trim(R.MaterialGroup) & \" - \" & Trim(R.MaterialGroupDescription)" in app
    text = open(SCREEN, encoding="utf-8").read()
    n = text.index("- galVhpMatGroups:")
    assert "=ThisItem.Display" in text[n:n + 6000]
