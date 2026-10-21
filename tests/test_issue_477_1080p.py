# -*- coding: utf-8 -*-
"""
Issue #477: 1080p-layout i Task List og Measuring Point-sidepanelet.

- Operationstabellen staar uden vandret scroll ved 1920 x 1080 - ogsaa
  med Packages (strategiplan). Long text, Docs og Action er smallere.
- Packages-kolonnen er skjult uden strategiplan: cellen, overskriften og
  kolonnesummen foelger samme betingelse.
- Ja/nej-segmentet [ No | Yes ] i Measuring Point-panelet klippes ikke af:
  cellen er mindst skinnens bredde.

    python3 -m pytest tests/test_issue_477_1080p.py
"""
import os
import re
import sys

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
VH = os.path.join(APP, "ScreenVhPlan.pa.yaml")
MP = os.path.join(APP, "ScreenMeasuringPoint.pa.yaml")
STRATEGY = '(varVhpPlan.PlanType = "Strategy")'


def _evaluate():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import check_layout
    return check_layout.evaluate


def _prop(text, ctrl, prop):
    """Egenskaben prop paa kontrollen ctrl i en .pa.yaml (foerste linje)."""
    m = re.search(r"- %s:\n(.*?)(?=\n\s+- \w+:\n\s+Control:|\Z)" % re.escape(ctrl), text, re.S)
    assert m, ctrl + " mangler"
    p = re.search(r"\n\s+%s: \|-\n\s+=(.*)" % prop, m.group(1))
    assert p, f"{ctrl}.{prop} mangler"
    return p.group(1).strip()


def _table_w(expr, app_w, strategy):
    """Galleriets bredde ved app_w. check_layout.evaluate kan ikke regne paa
    Int(), saa udtrykket regnes her: kun If/Max/Int, tal og de kendte navne."""
    e = (expr.replace(STRATEGY, str(strategy)).replace("App.Width", str(app_w))
         .replace("LayoutRank", "3").replace("PanelInset", "0"))
    assert re.fullmatch(r"[\sIfMaxnt()0-9.,+\-*/<>=TrueFals]*", e), e
    return eval(e, {"__builtins__": {}},
                {"If": lambda c, a, b: a if c else b, "Max": max, "Int": int})


def test_ops_table_fits_at_1080p_with_packages():
    text = open(VH, encoding="utf-8").read()
    gal_w = _prop(text, "galVhpOps", "Width")
    assert STRATEGY in gal_w, "tabellens bredde skal afhaenge af strategiplanen"
    for app_w in (1920, 1880):
        ops_cw = app_w - 56 - 64 - 36          # SHELL_W - 36, uden sidepanel
        for strategy in (True, False):
            w = _table_w(gal_w, app_w, strategy)
            assert w <= ops_cw, (f"tabellen ({w} px) er bredere end kortet ({ops_cw}) "
                                 f"ved {app_w}, strategi={strategy}")
    # Foer #477 var tabellen 1814 px - bredere end kortet ved 1920.
    assert _table_w(gal_w, 1920, True) < 1814


def test_packages_column_only_for_strategy_plans():
    text = open(VH, encoding="utf-8").read()
    html = _prop(text, "htmVhpOpsHeader", "HtmlText")
    with_pkg, without = re.search(
        r'If\(\(varVhpPlan\.PlanType = "Strategy"\), "(<span>.*?)", "(<span>.*?)"\)', html).groups()
    assert "PACKAGES" in with_pkg and "PACKAGES" not in without
    for col in ("MATERIALS", "DOCS", "ACTION", "LONG TEXT"):
        assert col in with_pkg and col in without, col
    # Cellen i raekken er skjult uden strategi.
    for ctrl in ("txtVhpOpPackages", "galVhpOpPills"):
        assert _prop(text, ctrl, "Visible").startswith("(" + STRATEGY + ")"), ctrl


def test_compact_long_text_and_docs_columns():
    sys.path.insert(0, os.path.join(ROOT, "Maintenance Plan App", "build"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build_tasklist as bt
    cols = dict(bt.OPS_COLS)
    assert cols["LONG TEXT"] <= 120
    assert cols["DOCS"] <= 80
    assert {"MATERIALS", "DOCS", "ACTION", "PACKAGES"} <= set(cols)
    assert bt.OPS_FIT_MIN_APP_W <= 1860
    text = open(VH, encoding="utf-8").read()
    assert _prop(text, "btnVhpOpLongText", "Width") == "120"
    assert _prop(text, "btnVhpOpDocs", "Width") == "80"


def test_measuring_point_yes_no_segment_is_not_clipped():
    ev = _evaluate()
    text = open(MP, encoding="utf-8").read()
    for col in ("ExistsInSap", "InProdos", "ProdosCounterExists"):
        cell = _prop(text, f"conMp{col}", "Width")
        seg = float(_prop(text, f"conMp{col}Seg", "Width"))
        for app_w in (1280, 1366, 1440, 1600, 1920, 2560):
            w = ev(cell, app_w, 3, 4, 4)
            assert w is not None, col
            assert w >= seg, f"{col}: cellen er {w:.0f} px, segmentet {seg:.0f} px ved {app_w}"
