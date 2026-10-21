# -*- coding: utf-8 -*-
"""
Issue #471: kolonnen SAP OBJECT i hubbens Closed-visning og popuppen med
de SAP-objekter, anmodningen har oprettet.

    python3 -m pytest tests/test_hub_sap_objects.py
"""
import os
import re
import sys

from conftest import ROOT

for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)
import build_hub as bh  # noqa: E402
import sap_objects as so  # noqa: E402
from test_hub_approval_pill_mine import _eval, _layout  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(text, name):
    i = text.index(f"- {name}:")
    j = text.find("\n" + " " * (len(text[:i]) - len(text[:i].rstrip(" "))) + "- ", i + 1)
    return text[i:j if j > 0 else None]


def test_column_sits_between_status_and_updated():
    keys = [k for k, _w in bh.COLS]
    assert keys.index(bh.SAP_COL) == keys.index("STATUS") + 1
    assert keys.index("UPDATED") == keys.index(bh.SAP_COL) + 1
    assert bh.SAP_COL == "SAP OBJECT"


def test_only_text_gives_room_and_only_in_closed():
    for width in (1366, 1600, 1920, 2560):
        for view in ("mine", "all"):
            w = {c: {k: _eval(bh.CWF[k], view, width=width, closed=c) for k, _w in bh.COLS}
                 for c in (False, True)}
            assert w[False][bh.SAP_COL] == 0
            assert w[True][bh.SAP_COL] == bh.SAP_W
            assert w[False]["TEXT"] - w[True]["TEXT"] == bh.SAP_W + bh.GAP
            for k, _w in bh.COLS:
                if k not in ("TEXT", bh.SAP_COL):
                    assert w[False][k] == w[True][k], (k, width, view)
            # Updated og Actions staar stille; col_x passer med containeren.
            lo, lc = _layout(view, width=width), _layout(view, width=width, closed=True)
            for k in ("UPDATED", "ACTIONS"):
                assert abs(lo[k] - lc[k]) < 1e-6, (k, width, view)
            assert abs(_eval(bh.col_x(bh.SAP_COL), view, width=width, closed=True)
                       - lc[bh.SAP_COL]) < 1e-6
            assert abs(_eval(bh.col_x("ACTIONS"), view, width=width, closed=True)
                       - lc["ACTIONS"]) < 1e-6


def test_header_and_icon_only_in_closed_and_icon_from_index_row():
    y = _yaml()
    i = [k for k, _w in bh.COLS].index(bh.SAP_COL)
    head = _block(y, f"txtMdH{i}")
    assert '="SAP OBJECT"' in head and bh.CLOSED in head
    icon = _block(y, "imgMdRowSap")
    assert '="View SAP objects"' in icon
    vis = re.search(r"Visible: \|-\n\s+=(.*)\n", icon).group(1)
    assert bh.CLOSED in vis and "ThisItem.SapObjectNo" in vis and '"OprettetISAP"' in vis
    # Intet opslag pr. raekke - kun indeksraekkens egne felter.
    assert "LookUp(" not in vis and "Filter(" not in vis


def test_objects_are_loaded_only_when_the_popup_opens():
    y = _yaml()
    app = open(APP, encoding="utf-8").read()
    assert "colMdSapRows" not in app and so.OPTION not in app
    on_select = _block(y, "imgMdRowSap").split("OnSelect:", 1)[1].split("PressedFill:", 1)[0]
    for lst in ("MaintenancePlans", "MaintenanceItems", "FunctionalLocationItems",
                "MaterialItems", "EquipmentItems", "AppSettings"):
        assert lst in on_select, lst
    # Ingen af dem i galleriets Items eller OnVisible.
    assert "AppSettings" not in bh.HUB_ON_VISIBLE and "colMdSapRows" not in bh.ITEMS
    # Delegerede filtre paa de samme kolonner som sletningen.
    assert "Filter(MaintenanceItems, MaintenancePlanNo.Value = varMdSapKey)" in on_select
    assert "LookUp(MaintenancePlans, ID = varMdSapSp)" in on_select
    for lst in ("FunctionalLocationItems", "MaterialItems", "EquipmentItems"):
        assert f"Filter({lst}, RequestGuid = varMdSapGuid)" in on_select


def test_no_sap_host_in_the_app():
    for path in (SCREEN, APP):
        text = open(path, encoding="utf-8").read()
        assert not re.search(r"https?://[^\"' ]*webgui", text, re.I), path
    assert f'Option.Value = "{so.OPTION}"' in so.BASE_FX
    assert ".AppUrl" in so.BASE_FX


def _fx_eval(expr, base):
    """url_fx med tekstkonstanter som Python: If, &&, !IsBlank, Trim, EncodeUrl."""
    py = (expr.replace(so.BASE, repr(base)).replace("&&", " and ").replace("!IsBlank(", "not IsBlank(")
          .replace(" & ", " + "))
    env = {"If": lambda c, a, b: a if c else b, "IsBlank": lambda v: v in (None, ""),
           "Trim": lambda v: v.strip(), "EncodeUrl": lambda v: v.replace(" ", "%20")}
    return eval(py, env)


def test_urls_use_each_objects_own_number():
    b = "https://sap.example/webgui"
    assert _fx_eval(so.url_fx("plan", '"37013402"'), b) == (
        b + "?~transaction=*IP03%20RMIPM-WARPL=37013402;&sap-language=EN")
    assert _fx_eval(so.url_fx("item", '"34014290"'), b) == (
        b + "?~transaction=*IP06%20RMIPM-WAPOS=34014290&sap-language=EN")
    assert _fx_eval(so.url_fx("tasklist", '"PMSSV01"', '"2"'), b) == (
        b + "?~transaction=*IA06%20RC271-PLNNR=PMSSV01;RC271-PLNAL=2;&sap-language=EN;DYNP_OKCODE=VOUE")
    # Ingen link uden adresse eller uden et helt saet vaerdier.
    assert _fx_eval(so.url_fx("plan", '"37013402"'), "") == ""
    assert _fx_eval(so.url_fx("tasklist", '"PMSSV01"', '""'), b) == ""
    assert _fx_eval(so.url_fx("item", '" "'), b) == ""


def test_plan_hierarchy_reads_the_stored_receipt_fields():
    fx = so.open_fx()
    for field in ("SAPNum", "SapItemNo", "TaskListGroup", "TaskListGroupCounter",
                  "CreatedMaterialNo", "EquipmentNumber", "FunctionalLocation"):
        assert field in fx, field
    if so.MP_ON:
        assert "CreatedMeasuringPointNo" in fx
    assert "Lvl: 0" in fx and "Lvl: 1" in fx and "Lvl: 2" in fx


def test_popup_is_read_only_with_the_x_close():
    y = _yaml()
    pop = _block(y, "conMdSapBackdrop")
    assert "- btnMdSapClose:" in pop
    no = _block(pop, "inpMdSapNo")
    assert "DisplayMode.View" in no
    link = _block(pop, "imgMdSapLink")
    assert "=Launch(ThisItem.Url)" in link and "=!IsBlank(ThisItem.Url)" in link
    # Ingen Patch/Remove i popuppen.
    assert "Patch(" not in pop and "Remove(" not in pop
