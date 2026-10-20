# -*- coding: utf-8 -*-
"""
Issue #459: uden items stod Add item to gange i Items-sektionen (i kortets
hoved og i den tomme tilstand). Kun knappen i hovedet er tilbage; den tomme
tilstand beholder ikon og tekst.

    python3 -m pytest tests/test_vhp_items_single_add.py
"""
import os

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _find(nodes, name):
    for item in nodes or []:
        for n, c in item.items():
            if n == name:
                return c
            hit = _find(c.get("Children"), name)
            if hit:
                return hit
    return None


def _screen():
    d = yaml.safe_load(open(SCREEN, encoding="utf-8").read())
    return list(d["Screens"].values())[0]["Children"]


def test_empty_state_has_no_add_button():
    kids = _screen()
    empty = _find(kids, "conVhpItemsEmpty")
    assert empty, "conVhpItemsEmpty mangler"
    names = [n for item in empty.get("Children") or [] for n in item]
    assert names == ["imgVhpItemsEmptyIcon", "txtVhpItemsEmptyText"], names
    assert _find(kids, "btnVhpItemsEmptyAdd") is None


def test_header_add_item_still_there():
    btn = _find(_screen(), "btnVhpAddItem")
    assert btn, "btnVhpAddItem mangler"
    assert "Add item" in str(btn["Properties"]["Text"])
    # Skjult i View som foer (issue #390) - ikke naar listen er tom.
    assert "colVhpItems" not in str(btn["Properties"].get("Visible", ""))
