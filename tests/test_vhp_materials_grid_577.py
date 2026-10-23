# -*- coding: utf-8 -*-
"""
Issue #577: Materials-popuppen er EET gitter.

Indtastningsraekken, kolonneoverskriften og linjerne bruger de samme
kolonnebredder (MAT_COLS). Opslagets felter (Description, Unit, Total,
Reorder point) er skrivebeskyttede felter - ogsaa mens en linje rettes -
og Quantity er det eneste felt, der kan skrives i. Uden materialer er der
een tom, ikke-interaktiv raekke under overskriften.

    python3 -m pytest tests/test_vhp_materials_grid_577.py
"""
import os
import re
import sys

import yaml

from conftest import ROOT

TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_layout as cl  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
RO_FIELDS = ("txtVhpMatNewDesc", "txtVhpMatNewUnit", "txtVhpMatNewTotal", "txtVhpMatNewRop")
RO_CELLS = ("txtVhpMatDesc", "txtVhpMatUnit", "txtVhpMatTotal", "txtVhpMatRop")


def _tree():
    d = yaml.safe_load(open(SCREEN, encoding="utf-8").read())
    out = {}

    def walk(nodes):
        for item in nodes or []:
            for name, c in item.items():
                out[name] = c
                walk(c.get("Children"))

    for s in d["Screens"].values():
        walk(s.get("Children"))
    return out


def _p(c, name, key):
    v = (c[name].get("Properties") or {}).get(key)
    return None if v is None else v.lstrip("=").strip()


def _ev(expr, w, n=3):
    expr = expr.replace("!(LayoutRank < 2)", "(LayoutRank >= 2)")
    return cl._evaluate_n(expr, w, n)


def _kids(c, name):
    return [list(k.keys())[0] for k in c[name].get("Children") or []]


def test_entry_header_and_rows_share_one_column_width_set():
    c = _tree()
    head = _p(c, "htmVhpMatHeader", "HtmlText")
    cols = [int(x) for x in re.search(r"grid-template-columns:([0-9px ]+);", head)
            .group(1).replace("px", "").split()]
    assert len(cols) == 7
    # Material og Description er bredest; tal og Actions er smalle.
    assert min(cols[0], cols[1]) > max(cols[2:])
    entry = ["conVhpMatMaterialNoCell", "conVhpMatDescCell", "conVhpMatNewQtyCell",
             "conVhpMatNewUnitCell", "conVhpMatNewTotalCell", "conVhpMatNewRopCell",
             "conVhpMatAddCell"]
    assert _kids(c, "conVhpMatEntry") == entry
    for w in (1366, 1920):
        assert [_ev(_p(c, n, "Width"), w) for n in entry] == cols
        # Linjens kontroller staar ved de samme kolonnestarter (raekken er
        # foldet ud i galleriet, saa det er deres X).
        starts = [sum(cols[:i]) + 10 * i for i in range(len(cols))]
        cells = ["txtVhpMatNo", "txtVhpMatDesc", "inpVhpMatQty", "txtVhpMatUnit",
                 "txtVhpMatTotal", "txtVhpMatRop", "btnVhpMatEdit"]
        assert [_ev(_p(c, n, "X"), w) for n in cells] == starts
        assert [_ev(_p(c, n, "Width"), w) for n in cells[:-1]] == cols[:-1]
        # Raekken staar vandret over tabellen.
        assert "LayoutDirection.Horizontal" in _p(c, "conVhpMatEntry", "LayoutDirection") \
            .replace("If(If(LayoutRank < 2, false, true), ", "")
    # + oeverst i Actions, blyant og skraldespand nederst.
    assert _kids(c, "conVhpMatAddCell") == ["btnVhpAddMaterial"]
    for n in ("btnVhpMatEdit", "btnVhpMatDelete"):
        assert n in _kids(c, "galVhpMaterials"), n


def test_entry_and_table_scroll_together_and_fit_a_desktop():
    c = _tree()
    assert _kids(c, "conVhpMatGrid") == ["conVhpMatEntry", "conVhpMatTableWrap"]
    assert _p(c, "conVhpMatGrid", "LayoutOverflowX") == "LayoutOverflow.Scroll"
    # Ingen vandret scroll paa en almindelig desktop: gitteret er i popuppen.
    for w in (1280, 1366, 1920):
        modal = _ev(_p(c, "conVhpMatModal", "Width"), w)
        assert _ev(_p(c, "galVhpMaterials", "Width"), w) <= modal - 36, w
    # Telefonen: felterne under hinanden, som foer.
    assert _ev(_p(c, "conVhpMatEntry", "LayoutDirection")
               .replace("LayoutDirection.Horizontal", "1")
               .replace("LayoutDirection.Vertical", "0"), 360) == 0


def test_lookup_values_are_read_only_fields_and_quantity_is_the_input():
    c = _tree()
    for n in RO_FIELDS:
        assert c[n]["Control"].startswith("ModernText"), n
        assert _p(c, n, "Fill") == "C.'input-bg-disabled'", n
        assert _p(c, n, "BorderColor") == "C.'border-default'", n
        assert _p(c, n, "BorderThickness") == "1", n
        assert _p(c, n, "Color") == "C.'text-primary'", n
        assert "OnSelect" not in c[n]["Properties"], n
    assert c["inpVhpMatNewQty"]["Control"].startswith("ModernTextInput")
    # Samme flade, mens en linje rettes - og kun da.
    for n in RO_CELLS:
        fill = _p(c, n, "Fill")
        assert fill.startswith("If(ThisItem.Editing && "), n
        assert "C.'input-bg-disabled'" in fill, n
        assert _p(c, n, "BorderThickness").startswith("If(ThisItem.Editing"), n
    assert "ThisItem.Editing" in _p(c, "inpVhpMatQty", "DisplayMode")


def test_one_empty_row_only_while_the_list_is_empty():
    c = _tree()
    assert "conVhpMatEmpty" not in c
    row = c["conVhpMatEmptyRow"]
    p = row["Properties"]
    assert row["Control"].startswith("GroupContainer")
    assert "OnSelect" not in p
    # Kun stregen - ingen tekst, felter eller ikoner.
    assert _kids(c, "conVhpMatEmptyRow") == ["conVhpMatEmptyRule"]
    assert _p(c, "conVhpMatEmptyRow", "Height") == _p(c, "galVhpMaterials", "TemplateSize") \
        .split(", ")[-1].rstrip(")")
    assert _p(c, "conVhpMatEmptyRow", "Width") == str(int(_ev(_p(c, "galVhpMaterials", "Width"), 1366)))
    assert _p(c, "conVhpMatEmptyRow", "Fill") == _p(c, "galVhpMaterials", "Fill")
    vis = _p(c, "conVhpMatEmptyRow", "Visible")
    assert "IsEmpty(colVhpMatDraft)" in vis
    assert _p(c, "galVhpMaterials", "Visible") == "!IsEmpty(colVhpMatDraft)"
    assert _kids(c, "conVhpMatTableWrap")[-1] == "conVhpMatEmptyRow"
    # Bunden taeller stadig.
    assert '" added"' in _p(c, "txtVhpMatChanges", "Text")
