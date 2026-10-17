# -*- coding: utf-8 -*-
"""KKS-opslaget: "Search Functional Locations" (issue #295).

Knappen staar paa raekken med Function / Aggregate / Component og aabner en
popup med den SAMME live FL-soegning som de andre skaerme (tools/fl_picker.py
og flowet i tools/build_flsearch.py). Popuppen roerer ikke KKS-opslagets
tilstand og ligger oven paa de andre popups og sidebarens panel."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenKks.pa.yaml")

import build_flsearch as fl  # noqa: E402


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(y, name, n=6000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def _prop(block, prop):
    i = block.index(f"{prop}: |-")
    return block[i:i + 400].split("\n")[1].strip()


def test_button_sits_right_of_the_key_tabs():
    y = _yaml()
    row = _block(y, "conKksTopRow", 200000)
    assert row.index("- conKksKeys:") < row.index("- btnKksFlOpen:")
    assert "LayoutJustifyContent.SpaceBetween" in row[:row.index("- conKksKeys:")]
    btn = _block(y, "btnKksFlOpen")
    assert '="Search Functional Locations"' in btn


def test_opening_and_closing_touch_only_the_popup():
    y = _yaml()
    assert _prop(_block(y, "btnKksFlOpen"), "OnSelect") == "=Set(varKksFlOn, true)"
    assert _prop(_block(y, "btnKksFlClose"), "OnSelect") == "=Set(varKksFlOn, false)"
    modal = y[y.index("- conKksFlBackdrop:"):y.index("- imgKksLoading:")]
    # KKS-filtrene, den valgte kode og resultaterne saettes aldrig herfra.
    for var in ("varKksKey", "varKksL1", "varKksL2", "varKksL3", "varKksQuery",
                "varKksPick", "varKksDetail"):
        assert not re.search(r"Set\(%s\b" % var, modal), var
    assert "Reset(inpKksFind)" not in modal


def test_reuses_the_live_fl_search():
    y = _yaml()
    btn = _block(y, "btnKksFlSearch", 12000)
    on_select = btn[btn.index("OnSelect:"):]
    assert f"{fl.FLOW_NAME}.Run(q)" in on_select
    assert fl.collect_results("colKksFl", raw_var="varKksFlRaw").split("\n")[2].strip() \
        in on_select
    assert f"Len(q) < {fl.MIN_SEARCH_LEN}" in on_select
    assert "- cmbKksFl:" in y and "- txtKksFlMsg:" in y
    assert "If(false, ClearCollect(colKksFl, " in y


def test_popup_is_above_all_other_overlays():
    y = _yaml()
    pos = {n: y.index(f"\n      - {n}:") for n in
           ("conKksRoot", "conKksNavOpen", "conKksFbBackdrop", "conKksPickModal",
            "conKksDetailModal", "conKksFlBackdrop", "conKksFlModal", "imgKksLoading")}
    for other in ("conKksRoot", "conKksNavOpen", "conKksFbBackdrop", "conKksPickModal",
                  "conKksDetailModal"):
        assert pos[other] < pos["conKksFlBackdrop"] < pos["conKksFlModal"], other
    assert pos["conKksFlModal"] < pos["imgKksLoading"]


def test_state_is_initialised_on_first_visit():
    on_visible = _yaml().split("OnVisible: |-", 1)[1][:20000]
    for s in ("Set(varKksFlOn, false)", "Set(varKksFlBusy, false)",
              'Set(varKksFlPick, "")'):
        assert s in on_visible
