# -*- coding: utf-8 -*-
"""
Issue #372: godkendelsespillen (btnMdRowApproval) staar rigtigt i "All
requests", men i "My requests" stod forloebet 16 px for langt til venstre,
saa "S" i System stak ud over pillens venstre kant.

Aarsagen: REQUESTER skjules i "My requests". En skjult kontrol fylder
intet i raekkens vandrette container - heller ikke mellemrummet efter
den - men pillens X regnede stadig mellemrummet med. Nu regnes alle
faste X i raekken af den samme col_x(), og TEXT faar ogsaa mellemrummet,
saa kolonnerne efter REQUESTER staar paa samme x i begge visninger.

Testen regner Power Fx-udtrykkene om til tal og laegger raekken ud, som
en vandret container goer det (synlige kolonner, GAP imellem).

    python3 -m pytest tests/test_hub_approval_pill_mine.py
"""
import os
import re
import sys

from conftest import ROOT

for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)
import build_hub as bh  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _eval(expr, view, width=1920, rank=4, inset=0):
    """Et af builderens Power Fx-udtryk som tal."""
    py = (expr.replace("App.Width", str(width)).replace("LayoutRank", str(rank))
          .replace("PanelInset", str(inset))
          .replace('varMdView = "mine"', "True" if view == "mine" else "False"))
    return eval(py, {"If": lambda c, a, b: a if c else b, "Max": max, "True": True, "False": False})


def _layout(view, **kw):
    """Kolonnernes x, som raekkens container laegger dem: skjulte kolonner
    (REQUESTER i "My requests") fylder intet og har intet mellemrum."""
    x, xs = bh.ROW_PAD, {}
    for k, _w in bh.COLS:
        if k == "REQUESTER" and view == "mine":
            continue
        xs[k] = x
        x += _eval(bh.CWF[k], view, **kw) + bh.GAP
    return xs


def test_columns_after_requester_stand_still_between_views():
    for width in (1366, 1600, 1920, 2560):
        mine, all_ = _layout("mine", width=width), _layout("all", width=width)
        for k in ("APPROVAL", "STATUS", "UPDATED", "ACTIONS"):
            assert abs(mine[k] - all_[k]) < 1e-6, (width, k, mine[k], all_[k])


def test_col_x_matches_container_layout_in_both_views():
    for view in ("mine", "all"):
        for width in (1366, 1920):
            lay = _layout(view, width=width)
            for k in ("APPROVAL", "ACTIONS"):
                assert abs(_eval(bh.col_x(k), view, width=width) - lay[k]) < 1e-6, (view, width, k)


def test_pill_x_is_the_shared_column_x():
    text = open(SCREEN, encoding="utf-8").read()
    block = text.split("- btnMdRowApproval:", 1)[1]
    x = re.search(r"\n\s+X: \|-\n\s+=(.*)\n", block).group(1)
    assert bh.col_x("APPROVAL") in x
    # Bred skaerm: pillen staar paa Approval-kolonnens kant i begge visninger.
    wide = {v: _eval(bh.col_x("APPROVAL"), v) for v in ("mine", "all")}
    assert wide["mine"] == wide["all"] == _layout("mine")["APPROVAL"]
