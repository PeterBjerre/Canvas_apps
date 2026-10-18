# -*- coding: utf-8 -*-
"""
R2-011: "Created material no." i Materials' Details maa kun udfyldes af
rekvirenten (ejeren af raekken) og en admin, kun paa en indsendt raekke,
og aendringen logges i MD_ApprovalLog. Reglen staar baade i knappens
DisplayMode og i selve handlingen.

    python3 -m pytest tests/test_material_created_no.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")
ROW = "LookUp(colMatRows, RowId = varMatActiveRowId)"
MAY = (f'(Coalesce({ROW}.Status, "") = "submitted" && (IsAdmin || '
       f'Lower(Coalesce({ROW}.RequesterEmail, "")) = varMatMe))')


def _control(name):
    text = open(SCREEN, encoding="utf-8").read()
    m = re.search(r"^(\s*)- " + name + r":\n(.*?)(?=^\1- |\Z)", text, re.S | re.M)
    assert m, name + " mangler"
    return m.group(2)


def _prop(body, prop):
    m = re.search(r"^\s+" + prop + r": \|-?\n(.*?)(?=^\s{0,48}[A-Z]\w*: \|)", body,
                  re.S | re.M)
    assert m, prop + " mangler"
    return m.group(1)


def test_save_checks_owner_or_admin_and_logs():
    fx = _prop(_control("btnMatDetCreatedSave"), "OnSelect")
    assert fx.strip().startswith("=If(")
    assert "!" + MAY in fx
    assert "Only the requester and admins can fill in the material no." in fx
    assert "Patch(MD_ApprovalLog" in fx
    assert '"Created material no. for "' in fx
    # Rettighedstjekket kommer foer skrivningen, og loggen skrives foer
    # listen hentes igen (saa den gamle vaerdi staar i loggen).
    assert fx.index("!" + MAY) < fx.index("CreatedMaterialNo: ")
    assert fx.index("CreatedMaterialNo: ") < fx.index("Patch(MD_ApprovalLog")
    assert fx.index("Patch(MD_ApprovalLog") < fx.index("ClearCollect(\n")

def test_input_and_button_use_the_same_rule():
    for name in ("btnMatDetCreatedSave", "inpMatDetCreatedNo"):
        dm = _prop(_control(name), "DisplayMode")
        assert f"If({MAY}, DisplayMode.Edit, DisplayMode.Disabled)" in dm, name
        assert '= "submitted" || IsAdmin' not in dm, name
