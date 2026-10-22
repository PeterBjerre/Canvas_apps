# -*- coding: utf-8 -*-
"""Issue #508, fase 4: Materials, Equipment og Measuring Point paa en telefon.

Mobil er tieren under Tablet (LayoutRank = 1, App.Width < 720). Hver test
tjekker BAADE telefonens vaerdi og at Tablet/Desktop er, som de var foer
fasen (tools/domain_parts.py, domain_objects.py, object_list.py)."""
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_layout as cl  # noqa: E402
import mobile  # noqa: E402

SCREENS = {"Mat": "ScreenMaterial", "Eq": "ScreenEquipment", "Mp": "ScreenMeasuringPoint"}
PHONES = (320, 360, 390, 420, 719)
TABLET_UP = (720, 800, 1024, 1366, 1920)
_CACHE = {}


def _ctrls(t):
    if t not in _CACHE:
        doc = yaml.safe_load(open(os.path.join(ROOT, "BIO SAP App", SCREENS[t] + ".pa.yaml"),
                                  encoding="utf-8"))
        out = {}

        def walk(items):
            for it in items or []:
                (n, b), = it.items()
                out[n] = b
                walk(b.get("Children"))
        walk(list(doc["Screens"].values())[0].get("Children"))
        _CACHE[t] = out
    return _CACHE[t]


def _p(t, name, key):
    v = (_ctrls(t)[name].get("Properties") or {}).get(key)
    if v is None:
        return None
    v = str(v)
    return v[1:] if v.startswith("=") else v


def _branch(e, phone):
    """Tag den ene gren af ALLE If(LayoutRank < 2, a, b) i udtrykket."""
    pat = "If(%s, " % mobile.MOBILE
    while pat in e:
        i = e.find(pat)
        d = 0
        for j in range(i + 2, len(e)):
            d += {"(": 1, ")": -1}.get(e[j], 0)
            if d == 0:
                break
        m, dk = mobile.split(e[i:j + 1])
        e = e[:i] + "(" + (m if phone else dk) + ")" + e[j + 1:]
    return e


def ev(t, name, key, w, n=3, **subs):
    e = _p(t, name, key)
    if e is None:
        return None
    e = _branch(e, w < 720)
    e = e.replace("!(LayoutRank < 2)", "(LayoutRank >= 2)")
    for k, v in subs.items():
        e = e.replace(k, v)
    return cl._evaluate_n(e, w, n)


# ---------------------------------------------------------------------------
# Listen: kort uden egen scroll, handlingerne paa een linje
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", SCREENS)
def test_rows_are_short_cards_without_their_own_scroll(t):
    gal = f"gal{t}Rows"
    for w in PHONES:
        assert ev(t, gal, "TemplateSize", w) == 108
        for n in (1, 5, 30, 50):
            assert ev(t, gal, "Height", w, n) == n * 110
        assert ev(t, gal, "Height", w, 80) == 50 * 110
    # Som foer: kort paa en tablet (5 ad gangen), tabel fra Desktop.
    assert _branch(_p(t, gal, "TemplateSize"), False) == "(If(LayoutRank < 3, 156, 56))"
    for w in TABLET_UP:
        row = 158 if w < 1024 else 58
        assert ev(t, gal, "Height", w, 30) == (5 if w < 1024 else 8) * row


@pytest.mark.parametrize("t", SCREENS)
def test_card_actions_fit_and_delete_stands_apart(t):
    acts = [n for n in _ctrls(t) if n.startswith(f"btn{t}Row") and n.endswith("C")]
    delete = f"btn{t}RowDeleteC"
    assert delete in acts and f"btn{t}RowOpenC" in acts
    for w in PHONES:
        gw = ev(t, f"gal{t}Rows", "Width", w)
        tw = gw - 4
        boxes = {a: (ev(t, a, "X", w), ev(t, a, "Y", w), ev(t, a, "Width", w),
                     ev(t, a, "Height", w)) for a in acts}
        for a, (x, y, bw, bh) in boxes.items():
            assert bw >= 44 and bh >= 44, (a, w)
            assert x >= 0 and x + bw <= tw + 0.5, (a, w)
            assert y + bh <= 108, (a, w)
        left = sorted(v for a, v in boxes.items() if a != delete)
        for (x1, _y, w1, _h), (x2, *_r) in zip(left, left[1:]):
            assert x2 >= x1 + w1, (t, w)        # ingen overlapper
        last = max(x + bw for x, _y, bw, _h in left)
        assert boxes[delete][0] - last >= 12, (t, w)
        # Titel og status paa foerste linje, inden for kortet.
        kx, kw = ev(t, f"txt{t}RowKeyC", "X", w), ev(t, f"txt{t}RowKeyC", "Width", w)
        sx = ev(t, f"img{t}RowStatusC", "X", w)
        assert kx + kw <= sx and sx + ev(t, f"img{t}RowStatusC", "Width", w) <= tw + 0.5


def test_card_title_is_the_description_on_a_phone():
    for t in ("Eq", "Mp"):
        e = _p(t, f"txt{t}RowKeyC", "Text")
        phone, desk = mobile.split(e)
        assert "(no text)" in phone
        assert "(no text)" not in desk


# ---------------------------------------------------------------------------
# Listens hoved: soegning, Filters-knappen og filtrene bag den
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", SCREENS)
def test_toolbar_on_a_phone(t):
    open_ = f"Coalesce(var{t}FiltersOpen, false)"
    for w in PHONES:
        assert ev(t, f"inp{t}Search", "Height", w) == 44
        assert ev(t, f"con{t}RowsTopM", "Visible", w) in (1, True)
        for drp in (f"drp{t}StatusFilter", f"drp{t}PlantFilter"):
            assert ev(t, drp, "Height", w) == 44
            assert ev(t, drp, "Visible", w, **{open_: "false"}) in (0, False)
            assert ev(t, drp, "Visible", w, **{open_: "true"}) in (1, True)
        assert ev(t, f"con{t}RowsTop", "Height", w, **{open_: "false"}) == 12 + 44 + 8 + 44
        assert ev(t, f"con{t}RowsTop", "Height", w, **{open_: "true"}) == 12 + 4 * 44 + 3 * 8
        for b in (f"btn{t}ToolbarCopy", f"btn{t}PasteRows", f"btn{t}NewRow"):
            assert ev(t, b, "Visible", w) in (0, False)
    for w in TABLET_UP:
        assert ev(t, f"inp{t}Search", "Height", w) == 36
        assert ev(t, f"con{t}RowsTopM", "Visible", w) in (0, False)
        for drp in (f"drp{t}StatusFilter", f"drp{t}PlantFilter"):
            assert ev(t, drp, "Height", w) == 36
            assert ev(t, drp, "Visible", w, **{open_: "false"}) in (1, True, None)
    label = _p(t, f"btn{t}FiltersM", "AccessibleLabel")
    assert "Show filters" in label and "Hide filters" in label


# ---------------------------------------------------------------------------
# Sidepanelet: een kolonne, 44 px felter, fanerne passer, sektioner klappet
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", SCREENS)
def test_panel_fields_are_44_on_a_phone_and_36_from_tablet(t):
    fields = [f"inp{t}Text", f"drp{t}Plant"]
    for f in fields:
        for w in PHONES:
            assert ev(t, f, "Height", w) == 44
        for w in TABLET_UP:
            assert ev(t, f, "Height", w) == 36


@pytest.mark.parametrize("t", ("Mat", "Eq"))
def test_panel_tabs_share_the_width_and_never_clip(t):
    tabs = [n for n in _ctrls(t) if n.startswith(f"con{t}EditorTabs") and n != f"con{t}EditorTabs"]
    for w in PHONES:
        inner = w - 24 - 18
        assert ev(t, f"con{t}EditorTabs", "Width", w) == pytest.approx(inner)
        assert sum(ev(t, b, "Width", w) for b in tabs) <= inner - 4
        for b in tabs:
            assert ev(t, b, "Width", w) >= 84      # "Details" uden flueben
            assert mobile.split(_p(t, b, "Layout"))[0] == "ButtonLayout.TextOnly"
    docs = f"con{t}EditorTabsDocuments"
    assert mobile.split(_p(t, docs, "Text")) == ('"Docs"', '"Documents"')


def test_secondary_sections_fold_on_a_phone_only():
    folds = {"Mat": ("Mfr", "Price"), "Eq": ("Mfr", "Warranty"), "Mp": ("More",)}
    for t, keys in folds.items():
        for k in keys:
            head = f"con{t}Sec{k}Fold"
            assert _p(t, head, "Visible").startswith("LayoutRank < 2")
            # Den gamle overskrift: skjult paa en telefon, som foer ellers.
            vis = _p(t, f"con{t}Sec{k}", "Visible")
            assert mobile.split(vis)[0] == "false"
            assert "Collapse" in _p(t, f"btn{t}Sec{k}Fold", "AccessibleLabel")
        # Identifikationen (kraevede felter) klappes aldrig sammen.
        assert f"con{t}SecIdentFold" not in _ctrls(t)
        assert f"con{t}SecObjectFold" not in _ctrls(t)
    # En forkert pris holder sektionen aaben.
    assert "Price" in _p("Mat", "btnMatSecPriceFold", "OnSelect")


def test_folded_grid_rows_stack_in_one_column():
    for w in PHONES:
        assert ev("Mat", "conMatGridMfrPair0", "Height", w,
                  **{"Coalesce(varMatSecMfrOpen, false)": "true"}) == 3 * 70 + 2 * 12
    p = _p("Mat", "conMatGridMfrPair0", "LayoutDirection")
    assert mobile.split(p) == ("LayoutDirection.Vertical", "LayoutDirection.Horizontal")


def test_number_rows_stack_on_a_phone():
    # Materials' nummer fra SAP og MP's nummer: under hinanden paa en telefon.
    assert mobile.split(_p("Mat", "conMatDetCreatedRow", "LayoutWrap"))[0] == "true"
    assert mobile.split(_p("Mp", "conMpDetMpNo", "LayoutDirection"))[0] == \
        "LayoutDirection.Vertical"
    for w in PHONES:
        assert ev("Mp", "btnMpDetSaveMpNo", "Height", w) == 44
    for w in TABLET_UP:
        assert ev("Mp", "conMpDetMpNo", "Height", w) == 36


def test_objects_tab_grows_with_its_content_on_a_phone():
    phone, desk = mobile.split(_p("Mat", "conMatObjTabBody", "Height"))
    assert desk == "App.Height - 250"
    assert "App.Height" not in phone
    assert mobile.split(_p("Mat", "galMatObjects", "TemplateSize")) == ("48", "44")


# ---------------------------------------------------------------------------
# Popupperne
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("modal", ("conMatObjListModal", "conMatPoModal", "conMatPasteModal"))
def test_popups_use_the_phone_width(modal):
    for w in PHONES:
        assert ev("Mat", modal, "Width", w) == w - 16
        assert ev("Mat", modal, "Y", w) == 8
    for w in (800, 1366):
        assert ev("Mat", modal, "Width", w) < w - 16


def test_object_list_popup_rows_fit_and_footer_stacks():
    for w in PHONES:
        gw = ev("Mat", "galMatObjList", "Width", w)
        assert gw == w - 40
        for c in ("chkMatObjPick", "txtMatObjListCode", "txtMatObjListDesc",
                  "imgMatObjListStatus"):
            assert ev("Mat", c, "X", w) + ev("Mat", c, "Width", w) <= gw + 0.5, (c, w)
        for b in ("btnMatObjListCancel", "btnMatObjListApply"):
            assert ev("Mat", b, "Height", w) == 44
    assert mobile.split(_p("Mat", "conMatObjListFoot", "LayoutDirection"))[0] == \
        "LayoutDirection.Vertical"
    for w in TABLET_UP:
        assert ev("Mat", "btnMatObjListApply", "Height", w) == 36


def test_still_missing_list_has_touch_buttons_and_no_scroll_on_a_phone():
    for w in PHONES:
        assert ev("Mat", "btnMatFixGo", "Height", w) == 44
        assert ev("Mat", "galMatFix", "TemplateSize", w) == 52
        assert ev("Mat", "galMatFix", "ShowScrollbar", w, 20) in (0, False)
    for w in TABLET_UP:
        assert ev("Mat", "btnMatFixGo", "Height", w) == 32
        assert ev("Mat", "galMatFix", "TemplateSize", w) == 40
