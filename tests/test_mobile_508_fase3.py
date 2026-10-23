# -*- coding: utf-8 -*-
"""Issue #508, fase 3: Functional Location paa en telefon.

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

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")
PHONES = (320, 360, 390, 420, 719)
TABLET_UP = (720, 800, 1024, 1366, 1920)
MORE = "Coalesce(varFlRowsMoreOpen, false)"
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
    v = (_ctrls()[name].get("Properties") or {}).get(key)
    return None if v is None else str(v)


def _args(s):
    out, d, cur, q = [], 0, "", False
    for ch in s:
        if ch == '"':
            q = not q
        if not q and ch in "([{":
            d += 1
        if not q and ch in ")]}":
            d -= 1
        if not q and ch == "," and d == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def _phone_branch(e):
    """If(LayoutRank < 2, A, B) -> A: telefonens gren (desktopgrenen kan have
    RoundDown, som check_layouts regner ikke kender)."""
    pat = "If(LayoutRank < 2, "
    while pat in e:
        i = e.find(pat)
        d, j = 0, i + 2
        for j in range(i + 2, len(e)):
            d += {"(": 1, ")": -1}.get(e[j], 0)
            if d == 0:
                break
        a = _args(e[i + 3:j])
        e = e[:i] + "(" + a[1] + ")" + e[j + 1:]
    return e


def _ev(expr, w, n=3, more=False):
    if expr is None:
        return None
    if w < 720:
        expr = _phone_branch(expr)
    expr = expr.replace("!(LayoutRank < 2)", "(LayoutRank >= 2)")
    expr = expr.replace(MORE, "true" if more else "false")
    return cl._evaluate_n(expr, w, n)


def fl(name, key, w, n=3, more=False):
    return _ev(_p(name, key), w, n, more)


def _kids(name):
    return [list(it.keys())[0] for it in _ctrls()[name].get("Children") or []]


def _visible(name, w, more):
    vis = _p(name, "Visible")
    return vis is None or _ev(vis, w, more=more) not in (0, False)


# ---------------------------------------------------------------------------
# Raekkerne: kort i stedet for tabel
# ---------------------------------------------------------------------------
def test_rows_are_compact_cards_and_row_details_make_them_taller():
    for w in PHONES:
        assert fl("galFlRows", "TemplateSize", w) == 168
        assert fl("galFlRows", "TemplateSize", w, more=True) == 324
        # Hele listen uden egen scroll (op til 50 kort).
        for n in (1, 3, 12, 40):
            assert fl("galFlRows", "Height", w, n) == n * 168
            assert fl("galFlRows", "ShowScrollbar", w, n) == 0
        assert fl("galFlRows", "ShowScrollbar", w, 60) == 1
        assert fl("galFlRows", "Width", w) <= w - 40
    for w in TABLET_UP:
        # Som foer: 44 + klikfladens 4 px under Desktop (H.hit), hoejst 12 raekker.
        row = 48 if w < 1024 else 44
        assert fl("galFlRows", "TemplateSize", w) == row
        assert fl("galFlRows", "Height", w, 3) == 3 * row
        assert fl("galFlRows", "Height", w, 30) == 12 * row
        assert fl("galFlRows", "ShowScrollbar", w, 13) == 1


def _boxes(gal, w, more):
    out = []
    for k in _kids(gal):
        if k.startswith(("rct", "txtFlRowNo")) or not _visible(k, w, more):
            continue
        x, y = fl(k, "X", w, more=more), fl(k, "Y", w, more=more)
        wd, ht = fl(k, "Width", w, more=more), fl(k, "Height", w, more=more)
        out.append((k, x, y, wd, ht))
    return out


def test_card_controls_fit_the_card_and_never_overlap():
    for gal in ("galFlRows", "galFlClassRows"):
        for w in PHONES:
            for more in (False, True):
                gw = fl(gal, "Width", w)
                th = fl(gal, "TemplateSize", w, more=more)
                boxes = _boxes(gal, w, more)
                assert boxes, gal
                for k, x, y, wd, ht in boxes:
                    assert None not in (x, y, wd, ht), (gal, k)
                    assert x >= 0 and x + wd <= gw + 0.01, (gal, k, w, x, wd, gw)
                    assert y >= 0 and y + ht <= th, (gal, k, w, y, ht, th)
                for i, a in enumerate(boxes):
                    for b in boxes[i + 1:]:
                        sep = (a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]
                               or a[2] + a[4] <= b[2] or b[2] + b[4] <= a[2])
                        assert sep, (gal, w, more, a, b)


def test_compact_card_keeps_status_delete_and_the_two_fields():
    for w in PHONES:
        for k in ("btnFlRowStatus", "btnFlRowDelete", "inpFlRowFl", "inpFlRowDesc",
                  "txtFlRowMetaM"):
            assert _visible(k, w, False), k
        for k in ("inpFlRowRoom", "inpFlRowSort", "chkFlRowAtex", "btnFlRowClassData",
                  "btnFlRowMfr", "btnFlRowWar", "btnFlRowCopy"):
            assert not _visible(k, w, False) and _visible(k, w, True), k
        for k in ("txtFlRowKks", "txtFlRowCls", "txtFlRowAbc", "txtFlRowNo"):
            assert not _visible(k, w, True), k
    for w in TABLET_UP:
        for k in ("inpFlRowRoom", "btnFlRowMfr", "btnFlRowCopy", "txtFlRowKks", "txtFlRowAbc"):
            assert _visible(k, w, False), k
        assert not _visible("txtFlRowMetaM", w, False)


def test_card_inputs_and_buttons_are_touch_targets():
    for k in ("inpFlRowFl", "inpFlRowDesc", "inpFlRowRoom", "btnFlRowStatus", "btnFlRowMfr",
              "btnFlRowCopy", "btnFlRowDelete"):
        assert fl(k, "Height", 360, more=True) >= 44, k
    assert fl("inpFlRowFl", "Height", 1366) == 36
    assert fl("btnFlRowStatus", "Height", 1366) == 30
    # Uden kolonneoverskrift siger pladsholderen, hvad feltet er.
    assert '"Functional Location"' in _p("inpFlRowFl", "Placeholder")
    assert _p("chkFlRowAtex", "Label").lstrip("=").startswith('If(LayoutRank < 2, "ATEX", "")')
    # Copy har tekst paa telefonen, kun ikon fra Tablet.
    assert "IconBefore, ButtonLayout.IconOnly" in _p("btnFlRowCopy", "Layout")


def test_table_headers_are_hidden_on_a_phone():
    for c in ("conFlRowsHead", "conFlRowsRule", "conFlClsHead", "conFlClsRule"):
        assert fl(c, "Visible", 360) == 0, c
        assert fl(c, "Visible", 1366, 3) not in (0, False), c


def test_rows_toolbar_fits_320_with_icon_buttons():
    for b in ("btnFlPasteRows", "btnFlAddRow"):
        assert fl(b, "Width", 320) == 44 and fl(b, "Height", 320) == 44
        assert "IconOnly" in _p(b, "Layout")
        assert fl(b, "Height", 1366) == 36 and fl(b, "Width", 1366) > 44
        assert _p(b, "AccessibleLabel")
    assert fl("conFlRowsTop", "Height", 320) == 44
    assert fl("conFlRowsTop", "Height", 1366) == 36
    assert fl("txtFlRowsCount", "Width", 320) >= 70
    # "Row details": kun telefonen.
    assert fl("conFlRowsMoreFold", "Visible", 360) == 1
    assert fl("conFlRowsMoreFold", "Visible", 1366) == 0
    assert "varFlRowsMoreOpen" in _p("btnFlRowsMoreFold", "OnSelect")


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
def test_classes_are_folded_cards_on_a_phone():
    assert fl("galFlClassRows", "TemplateSize", 360) == 76
    assert fl("galFlClassRows", "TemplateSize", 1366) == 44
    # Issue #533: chevronlinjen ses paa ALLE skaermbredder, og Classes er
    # lukket som standard overalt (tests/test_fl_classes_532_533.py).
    assert fl("conFlClassesFold", "Visible", 360) is None
    vis = _p("conFlClassesBody", "Visible")
    assert "Coalesce(varFlClassesOpen, false)" in vis
    assert fl("btnFlTab", "Height", 360) == 42 and fl("btnFlTab", "Height", 1366) == 34
    assert fl("galFlTabs", "ShowScrollbar", 360) == 0


# ---------------------------------------------------------------------------
# Sidepanelet: fuld skaerm, een kolonne, sektioner der kan klappes sammen
# ---------------------------------------------------------------------------
def test_panel_is_full_screen_with_small_padding_on_a_phone():
    for w in PHONES:
        assert fl("conFlEditorPanel", "Width", w) == w
        assert fl("conFlEditorPanel", "X", w) == 0
        assert fl("conFlEditorPanel", "PaddingLeft", w) == lay.MOBILE_PAD_X
        assert fl("conFlEditorSections", "PaddingLeft", w) == 0
    for w in TABLET_UP:
        assert fl("conFlEditorPanel", "PaddingLeft", w) == 20
        assert fl("conFlEditorSections", "PaddingLeft", w) == 20


def test_panel_form_is_one_column_with_44_px_fields_on_a_phone():
    for w in PHONES:
        assert fl("galFlPanelLocFields", "WrapCount", w) == 1
        assert fl("galFlPanelKksFields", "WrapCount", w) == 1
        assert fl("galFlPanelLocFields", "TemplateSize", w) == 94
        assert fl("inpFlPanelLocVal", "Height", w) == 44
        assert fl("drpFlPanelLocVal", "Height", w) == 44
        # Felterne bruger bredden: panelet minus 12 + 12, scrollbar og 8.
        assert fl("inpFlPanelLocVal", "Width", w) == w - 24 - lay.SCROLLBAR_W - 8
    # Fra Tablet som foer: 2 kolonner i et 1920-panel (653 - 98 < 600), 3 paa tablet.
    assert fl("galFlPanelLocFields", "WrapCount", 1920) == 2
    assert fl("galFlPanelLocFields", "WrapCount", 800) == 3
    assert fl("galFlPanelLocFields", "TemplateSize", 1366) == 86
    assert fl("inpFlPanelLocVal", "Height", 1366) == 36


def test_panel_sections_fold_on_a_phone_and_open_when_jumped_to():
    for key in ("Main", "Loc", "Class", "Mfr", "War", "TRM"):
        head = f"conFlPanel{key}Fold"
        assert fl(head, "Visible", 360) == 1 and fl(head, "Visible", 1366) == 0
        assert fl(f"txtFlPanel{key}Title", "Visible", 1366, 3) not in (0, False)
        # Aabnet fra en knap: altid aaben, og chevronen er vaek.
        chev = _p(f"btnFlPanel{key}Fold", "Visible")
        assert 'IsBlank(IfError(varFlPanelJump, ""))' in chev
        on = _p(f"btnFlPanel{key}Fold", "OnSelect")
        assert f"Set(varFlPanel{key}Open, !(If(!IsBlank(IfError(varFlPanelJump" in on
    # Main er aaben som standard; de andre, naar de har en fejl.
    assert "Coalesce(varFlPanelMainOpen, true)" in _p("galFlPanelMainFields", "Visible")
    assert "Coalesce(varFlPanelLocOpen, IfError(CountRows(Filter(colFlIssues" in \
        _p("galFlPanelLocFields", "Visible")
    assert "to fix" in _p("txtFlPanelLocFoldSummary", "Text")
    assert fl("btnFlPanelShowAll", "Height", 360) == 44
    assert fl("btnFlPanelShowAll", "Height", 1366) == 36


def test_collapsible_open_expr_drives_the_toggle_and_the_children():
    from build_helpers import text_ctrl
    kid = text_ctrl("txtK", '"k"')
    head, k = mobile.collapsible("Zz", "Things", [kid], "varZz", open_expr="a && b")
    btn = mobile.find(head, "btnZzFold")
    assert btn.props["OnSelect"] == "Set(varZz, !(a && b))"
    assert k.vis == f"({mobile.NOT_MOBILE} || a && b)"
    # Uden open_expr er formlen den samme som foer (hub og VH-plan).
    head2, = mobile.collapsible("Zy", "T", [], "varZy")
    assert mobile.find(head2, "btnZyFold").props["OnSelect"] == \
        "Set(varZy, !Coalesce(varZy, false))"


# ---------------------------------------------------------------------------
# Header, popupper
# ---------------------------------------------------------------------------
def test_header_buttons_are_44_on_a_phone_and_unchanged_elsewhere():
    for b in ("btnFlNew", "btnFlEdit", "btnFlSaveDraft", "btnFlSubmit", "btnFlDeleteRequest"):
        assert fl(b, "Height", 360) == 44, b
        assert fl(b, "Height", 1366) == 36, b
    for b in ("btnFlEdit", "btnFlSaveDraft", "btnFlSubmit", "btnFlDeleteRequest"):
        assert fl(b, "Width", 360) == 44, b
    # Tablet som foer: Edit et 40 px ikon, Delete med tekst.
    assert fl("btnFlEdit", "Width", 800) == 40
    assert fl("btnFlDeleteRequest", "Width", 800) > 44
    for b in ("btnFlSaveDraft", "btnFlSubmit"):
        assert _p(b, "Width").lstrip("=").startswith("If(LayoutRank < 2, 44, "), b
    assert fl("conFlBar", "Height", 360) == 44


def test_paste_popup_is_nearly_full_width_with_a_stacked_footer():
    for w in PHONES:
        assert fl("conFlPasteModal", "Width", w) == w - 16
        assert fl("conFlPasteModal", "Y", w) == lay.MOBILE_POP_MARGIN
        assert fl("btnFlPasteAdd", "Height", w) == 44
        assert fl("inpFlPaste", "Height", w) == 120
    assert fl("conFlPasteModal", "Width", 1366) == 560
    assert fl("inpFlPaste", "Height", 1366) == 160
    assert fl("btnFlPasteAdd", "Height", 1366) == 36


def test_save_error_wraps_on_a_phone():
    assert fl("txtFlInfo", "Height", 360) == 36
    assert fl("txtFlInfo", "Height", 1366) == 18
    assert "true" in _p("txtFlInfo", "Wrap")
