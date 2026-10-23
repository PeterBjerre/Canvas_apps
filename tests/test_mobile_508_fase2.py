# -*- coding: utf-8 -*-
"""Issue #508, fase 2: Maintenance Plan (VH-plan) paa en telefon.

Mobil er tieren under Tablet (LayoutRank = 1, App.Width < 720). Hver test
tjekker BAADE mobilvaerdien og at Tablet/Desktop er, som de var foer fasen."""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_layout as cl  # noqa: E402
import layout_tokens as lay  # noqa: E402
import mobile  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
PHONES = (320, 360, 390, 420)
TABLET_UP = (720, 800, 1024, 1366, 1920)
_CACHE = {}


def _ctrls():
    if not _CACHE:
        doc = yaml.safe_load(open(SCREEN, encoding="utf-8"))

        def walk(items):
            for it in items or []:
                (n, b), = it.items()
                _CACHE[n] = b
                walk(b.get("Children"))
        walk(list(doc["Screens"].values())[0].get("Children"))
    return _CACHE


def _p(name, key):
    return (_ctrls()[name].get("Properties") or {}).get(key)


def _ev(expr, w, n=3):
    if expr is not None:
        expr = expr.replace("!(LayoutRank < 2)", "(LayoutRank >= 2)")
    return cl._evaluate_n(expr, w, n)


def vh(name, key, w, n=3):
    return _ev(_p(name, key), w, n)


def _kids(name):
    return [list(it.keys())[0] for it in _ctrls()[name].get("Children") or []]


# ---------------------------------------------------------------------------
# Nye vaerktoejer (tools/mobile.py, tools/gen_screen.py)
# ---------------------------------------------------------------------------
def test_find_refit_and_hide_on_mobile():
    from build_helpers import group, text_ctrl
    a = text_ctrl("txtA", '"a"', height=20)
    b = text_ctrl("txtB", '"b"', height=20)
    box = group("conBox", [a, b], direction="Vertical", gap=4)
    assert mobile.find(box, "txtB") is b and mobile.find(box, "nope") is None
    b.props["Height"] = lay.mobile_or(44, 20)
    b.h = b.props["Height"]
    mobile.refit(box)
    ha = _ev(str(a.h), 1366)
    assert _ev(str(box.props["Height"]), 360) == ha + 4 + 44
    assert _ev(str(box.props["Height"]), 1366) == ha + 4 + 20
    mobile.hide_on_mobile(a)
    assert _ev(a.vis, 360) == 0 and _ev(a.vis, 1366) == 1


def test_gallery_place_moves_a_row_control_on_a_phone_only():
    # Materialeraekken er et kort paa en telefon: antal paa linje 2.
    x, y = _p("inpVhpMatQty", "X"), _p("inpVhpMatQty", "Y")
    assert x.lstrip("=").startswith("If(LayoutRank < 2,")
    assert _ev(x, 360) == 8 and _ev(y, 360) == 52
    for w in TABLET_UP:
        assert _ev(x, w) == 0 + 130 + 10 + 260 + 10  # issue #574


# ---------------------------------------------------------------------------
# Kort i stedet for tabeller
# ---------------------------------------------------------------------------
CARD_GALLERIES = {
    # galleri: (mobil skabelonhoejde, desktop skabelonhoejde, desktop bredde)
    "galVhpMaterials": (116, 46, 874),  # issue #574: bredere kolonner
    "galVhpItemObjects": (80, 40, 724),
    "galVhpPicker": (54, 34, 636),
    "galVhpPkgRows": (88, 44, 472),
}


def test_tables_become_cards_that_fit_the_phone():
    for g, (m_t, d_t, d_w) in CARD_GALLERIES.items():
        for w in PHONES:
            assert vh(g, "TemplateSize", w) == m_t, g
            assert vh(g, "Width", w) <= w - 40, (g, w)
        for w in TABLET_UP:
            assert vh(g, "TemplateSize", w) == d_t, g
        for w in (1024, 1366, 1920):
            assert vh(g, "Width", w) == d_w, (g, w)


def test_card_rows_stay_inside_the_gallery_at_320():
    for g in CARD_GALLERIES:
        gw = vh(g, "Width", 320)
        for k in _kids(g):
            vis = _p(k, "Visible")
            if vis is not None and _ev(vis, 320) == 0:
                continue
            x, wd = vh(k, "X", 320), vh(k, "Width", 320)
            if x is None or wd is None:
                continue
            assert x + wd <= gw, (g, k, x, wd, gw)


def test_table_headers_are_hidden_on_a_phone():
    for c in ("conVhpPickerColHead", "conVhpPickerDivider"):
        assert vh(c, "Visible", 360) == 0
        assert vh(c, "Visible", 1366) == 1
    for c in ("txtVhpPickerCtrl", "txtVhpPickerWork", "txtVhpPickerDur"):
        assert vh(c, "Visible", 360) == 0 and vh(c, "Visible", 1366) == 1


def test_materials_list_has_no_inner_scroll_on_a_phone():
    for n in (0, 1, 3, 12):
        assert vh("galVhpMaterials", "Height", 360, n) == n * 118
    assert vh("galVhpMaterials", "ShowScrollbar", 360) == 0
    assert vh("galVhpMaterials", "ShowScrollbar", 1366) == 1
    # Issue #574: saa hoej som linjerne - scroller foerst, naar de ikke er der.
    assert vh("galVhpMaterials", "Height", 1366) == 3 * 46
    assert vh("galVhpMaterials", "Height", 1366, 0) == 0
    assert vh("galVhpMaterials", "Height", 1366, 40) == 900 - 323


def test_operations_are_two_line_cards_on_a_phone():
    assert "txtVhpOpMRowMeta" in _ctrls()
    assert vh("galVhpOpsM", "Visible", 360) == 1
    assert vh("galVhpOpsM", "Visible", 1366) == 0
    assert vh("galVhpOpsM", "TemplateSize", 360) >= 60
    assert vh("galVhpOpsM", "ShowScrollbar", 360) == 0
    assert "Operation" in _p("txtVhpOpMRow", "AccessibleLabel")


# ---------------------------------------------------------------------------
# Popupper naesten fuld skaerm
# ---------------------------------------------------------------------------
POPUPS = {
    "conVhpPickerModal": 740,
    "conVhpObjListModal": 760,
    "conVhpMatModal": 910,
    "conVhpLongTextModal": 620,
    "conVhpMissingModal": 520,
}


def test_popups_are_nearly_full_screen_on_a_phone():
    for c, d_w in POPUPS.items():
        for w in PHONES:
            assert vh(c, "Width", w) == w - 2 * lay.MOBILE_POP_MARGIN, (c, w)
        for w in (1024, 1366, 1920):
            assert vh(c, "Width", w) == d_w, (c, w)


# ---------------------------------------------------------------------------
# Touch-maal og ikonknapper
# ---------------------------------------------------------------------------
TOUCH = {
    # kontrol: hoejde fra Tablet og op (uaendret)
    "btnVhpAddItem": 36,
    "btnVhpRemoveItem": 30,
    "btnVhpObjListUse": 36,
    "btnVhpEdit": 36,
    "imgVhpObjList": 34,
    "chkVhpPickerSelectAll": 36,
}


def test_touch_targets_are_44_on_a_phone_and_unchanged_elsewhere():
    for c, d_h in TOUCH.items():
        for w in PHONES:
            assert vh(c, "Height", w) >= lay.TOUCH_MIN, (c, w)
        for w in TABLET_UP:
            assert vh(c, "Height", w) == d_h, (c, w)


def test_add_item_is_an_icon_button_with_a_label_on_a_phone():
    assert vh("btnVhpAddItem", "Width", 360) == 44
    assert vh("btnVhpAddItem", "Width", 1366) == 108
    assert _p("btnVhpAddItem", "AccessibleLabel").strip("=") == '"Add item"'
    assert "Object list" in _p("imgVhpObjList", "AccessibleLabel")


def test_popup_footers_stack_their_buttons_on_a_phone():
    for f in ("conVhpItemDelConfirmFooter", "conVhpNotesFooter"):
        d = _p(f, "LayoutDirection")
        assert "If(LayoutRank < 2, LayoutDirection.Vertical" in d, f
        assert d.rstrip().endswith("LayoutDirection.Horizontal)"), f
