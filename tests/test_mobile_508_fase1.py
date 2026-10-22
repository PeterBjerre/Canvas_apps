# -*- coding: utf-8 -*-
"""Issue #508, fase 1: mobilfundamentet og Masterdata Hub paa en telefon.

Mobil er tieren under Tablet (LayoutRank = 1, App.Width < 720). Hver test
tjekker BAADE mobilvaerdien og at Tablet/Desktop er, som de var."""
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

APP = os.path.join(ROOT, "BIO SAP App")
PHONES = (320, 360, 390, 420)
TABLET_UP = (720, 1023, 1024, 1366, 1600, 1920)
_CACHE = {}


def _ctrls(screen):
    if screen not in _CACHE:
        doc = yaml.safe_load(open(os.path.join(APP, screen), encoding="utf-8"))
        out = {}

        def walk(items):
            for it in items or []:
                (n, b), = it.items()
                out[n] = b
                walk(b.get("Children"))
        walk(list(doc["Screens"].values())[0].get("Children"))
        _CACHE[screen] = out
    return _CACHE[screen]


def _p(screen, name, key):
    return (_ctrls(screen)[name].get("Properties") or {}).get(key)


def _ev(expr, w, n=3):
    # Tjekkets regnemaskine kender ikke "not (...)"; mobilens negation skrives om.
    if expr is not None:
        expr = expr.replace("!(LayoutRank < 2)", "(LayoutRank >= 2)")
    return cl._evaluate_n(expr, w, n)


def hub(name, key, w, n=3):
    return _ev(_p("ScreenMdHub.pa.yaml", name, key), w, n)


# ---------------------------------------------------------------------------
# Fundamentet (tools/layout_tokens.py, tools/mobile.py)
# ---------------------------------------------------------------------------
def test_shell_w_is_unchanged_from_tablet_and_wider_on_a_phone():
    for w in TABLET_UP:
        assert _ev(lay.SHELL_W, w) == w - 56 - 64
    for w in PHONES:
        assert _ev(lay.SHELL_W, w) == w - lay.SHELL_INSET_MOBILE == w - 48


def test_card_and_panel_inner_widths_follow_the_mobile_padding():
    for w in TABLET_UP:
        assert _ev(lay.CARD_INNER_W, w) == w - 56 - 64 - 36
    for w in PHONES:
        assert _ev(lay.CARD_INNER_W, w) == w - 48 - 2 * lay.MOBILE_CARD_PAD
        assert _ev(lay.PANEL_INNER_W, w) == w - 2 * lay.MOBILE_PAD_X - lay.SCROLLBAR_W
    assert _ev(lay.PANEL_INNER_W, 800) == 800 - 80 - 18


def test_popup_width_is_nearly_full_screen_on_a_phone_only():
    fx = lay.popup_w(460, 40)
    for w in PHONES:
        assert _ev(fx, w) == w - 2 * lay.MOBILE_POP_MARGIN
    for w in TABLET_UP:
        assert _ev(fx, w) == min(460, w - 40)


def test_layout_check_tries_the_smallest_phone():
    assert 320 in lay.test_widths()
    assert lay.MOBILE == "LayoutRank < 2" and lay.TOUCH_MIN == 44


def test_collapsible_section_is_a_mobile_header_and_leaves_tablet_alone():
    from build_helpers import text_ctrl
    body = text_ctrl("txtT", '"x"')
    head, kid = mobile.collapsible("T", "Things", [body], "varTOpen")
    assert head.props["Visible"] == lay.MOBILE
    chev = head.children[-1]
    assert chev.name == "btnTFold"
    assert "Collapse Things" in chev.props["AccessibleLabel"]
    assert "Expand Things" in chev.props["AccessibleLabel"]
    assert _ev(chev.props["Width"], 360) >= 44 and _ev(chev.props["Height"], 360) >= 44
    vis = kid.props["Visible"]
    for w in TABLET_UP:   # altid synlig fra Tablet
        assert _ev(vis.replace("Coalesce(varTOpen, false)", "false"), w) == 1
    assert _ev(vis.replace("Coalesce(varTOpen, false)", "false"), 360) == 0
    assert _ev(vis.replace("Coalesce(varTOpen, false)", "true"), 360) == 1


# ---------------------------------------------------------------------------
# Rammen og navigationen - alle skaerme
# ---------------------------------------------------------------------------
SCREENS = [f for f in os.listdir(APP) if f.startswith("Screen") and f.endswith(".pa.yaml")]


def test_frame_padding_is_smaller_on_a_phone_and_unchanged_elsewhere():
    for scr in SCREENS:
        ctrls = _ctrls(scr)
        body = [n for n in ctrls if n.startswith("con") and n.endswith("Body")
                and (n[:-4] + "Root") in ctrls]
        head = [n for n in ctrls if n.startswith("con") and n.endswith("Header")
                and (n[:-6] + "Root") in ctrls]
        assert body and head, scr
        for b in body:
            p = ctrls[b]["Properties"]
            if b.endswith("NavBody") or "PaddingLeft" not in p:
                continue
            assert _ev(p["PaddingLeft"], 360) == 12 and _ev(p["PaddingRight"], 360) == 12, (scr, b)
            assert _ev(p["PaddingLeft"], 1366) == 24 and _ev(p["PaddingRight"], 1366) == 16, (scr, b)
            assert _ev(p["PaddingTop"], 1366) == lay.BODY_PAD_T
        for h in head:
            p = ctrls[h]["Properties"]
            assert _ev(p["PaddingLeft"], 360) == 12, (scr, h)
            assert _ev(p["PaddingTop"], 1366) == lay.HEADER_PAD_T
            assert _ev(p["PaddingRight"], 1366) == lay.PAGE_PAD_R + lay.SCROLLBAR_W


def test_nav_drawer_dims_the_page_on_a_phone_only():
    fill = _p("ScreenMdHub.pa.yaml", "imgMdNavScrim", "Fill")
    assert fill.strip().startswith("=If(LayoutRank < 2, C.'overlay'")
    assert fill.strip().endswith("RGBA(0, 0, 0, 0))")
    lab = _p("ScreenMdHub.pa.yaml", "imgMdNavToggleOpen", "AccessibleLabel")
    assert '"Close menu"' in lab and '"Collapse menu"' in lab
    for name in ("imgMdThemeOpen", "imgMdNavMessageOpen"):
        assert hub(name, "Height", 360) >= 44
        assert hub(name, "Height", 1366) == 36


# ---------------------------------------------------------------------------
# Masterdata Hub
# ---------------------------------------------------------------------------
def test_hub_list_is_cards_without_an_inner_scroll_on_a_phone():
    gal = "galMdRequests"
    assert hub(gal, "TemplateSize", 360) == 100
    assert hub(gal, "TemplateSize", 800) == 112 and hub(gal, "TemplateSize", 1920) == 52
    h = _p("ScreenMdHub.pa.yaml", gal, "Height")
    assert "galMdRequests.AllItemsCount" in h
    # saa hoejt som raekkerne - hoejst de viste (fase 6: Show more, 50 ad gangen)
    shown = h.replace("Coalesce(varMdShowN, 50)", "50")
    assert _ev(shown, 360, 8) == 8 * 100
    assert _ev(shown, 360, 80) == 50 * 100
    assert hub(gal, "Height", 800) == 784 and hub(gal, "Height", 1920) == 728
    ssb = _p("ScreenMdHub.pa.yaml", gal, "ShowScrollbar")
    assert _ev(ssb, 360) == 0 and _ev(ssb, 1366) == 1
    for name in ("txtMdRowNoM", "txtMdRowTextM", "imgMdRowStatusM", "txtMdRowExtraM"):
        assert hub(name, "Visible", 360) == 1, name
        for w in TABLET_UP:
            assert hub(name, "Visible", w) == 0, (name, w)
    # Tablet-kortet er uaendret og vises ikke paa en telefon.
    assert hub("txtMdRowNoC", "Visible", 360) == 0
    assert hub("txtMdRowNoC", "Visible", 800) == 1
    # Ikonerne har klikflader paa 44 px og staar inden for raekken.
    for name in ("imgMdRowTimeline", "imgMdRowNotes"):
        assert hub(name, "Width", 360) == 44 and hub(name, "Height", 360) == 44
    y = _ev(_p("ScreenMdHub.pa.yaml", "imgMdRowTimeline", "Y").replace("Self.Height", "44"), 360)
    assert y + 44 <= 100


def test_hub_mobile_card_text_fits_at_320():
    for name in ("txtMdRowNoM", "txtMdRowTextM", "txtMdRowExtraM"):
        assert hub(name, "Width", 320) > 80, name
    # Nummeret har plads til et helt anmodningsnummer (EQ-000912, 14 pt).
    assert hub("txtMdRowNoM", "Width", 320) >= 90


def test_hub_tiles_fold_on_a_phone_and_stay_as_before_from_tablet():
    assert hub("conMdTilesFold", "Visible", 360) == 1
    tiles_vis = _p("ScreenMdHub.pa.yaml", "conMdTiles", "Visible")
    closed = tiles_vis.replace("Coalesce(varMdTilesOpen, false)", "false")
    assert _ev(closed, 360) == 0          # lukket som standard paa en telefon
    for w in TABLET_UP:
        assert hub("conMdTilesFold", "Visible", w) == 0
        assert _ev(closed, w) == 1
    assert hub("conMdTileFL", "Height", 360) == 74
    assert hub("conMdTileFL", "Height", 1366) == 74
    assert hub("conMdTiles", "Height", 360) == 6 + 2 * 74 + 12 + 8
    assert hub("conMdTiles", "Height", 800) == 6 + 2 * 74 + 12 + 44
    assert hub("conMdTiles", "Height", 1366) == 6 + 74 + 44
    lab = _p("ScreenMdHub.pa.yaml", "btnMdTilesFold", "AccessibleLabel")
    assert "Expand Domains" in lab and "Collapse Domains" in lab
    # Opsummeringen siger, hvad der er valgt, mens fliserne er lukkede.
    assert '"All domains"' in _p("ScreenMdHub.pa.yaml", "txtMdTilesFoldSummary", "Text")


def test_hub_new_request_menu_and_peek_stay_on_a_320_screen():
    for w in PHONES:
        x = hub("conMdNewMenu", "X", w)
        # Self.Width kan tjekket ikke regne paa - menuen er 290 bred.
        if x is None:
            e = _p("ScreenMdHub.pa.yaml", "conMdNewMenu", "X").replace("Self.Width", "290")
            x = _ev(e, w)
        assert 0 <= x and x + 290 <= w, w
        assert hub("conMdNewMenu", "Y", w) == 52 + 8 + 44 + 6
        assert hub("conMdPeek", "Width", w) == w - 16
        assert _ev(_p("ScreenMdHub.pa.yaml", "conMdPeek", "X").replace("Self.Width", "1"), w) == 8
    assert hub("conMdNewMenu", "Y", 1366) == 72
    assert hub("conMdPeek", "Width", 1366) == 360
    assert hub("btnMdNewRequest", "Height", 360) == 44
    assert hub("btnMdNewRequest", "Height", 1366) == 38


def test_hub_view_switch_and_filter_chip_are_touch_targets():
    for name in ("conMdViewMMine", "conMdViewMAll"):
        assert hub(name, "Height", 360) >= 40
    assert hub("btnMdActiveDomain", "Height", 360) == 44
    assert hub("btnMdActiveDomain", "Height", 1366) == 30
    assert hub("btnMdRetShow", "Height", 360) == 44
    assert hub("btnMdRetShow", "Height", 1366) == 32
    assert hub("conMdRetBanner", "Height", 1366) == 44


def test_hub_close_and_delete_dialogs_stack_their_buttons_on_a_phone():
    foot = "conMdCloseConfirmFooter"
    d = _p("ScreenMdHub.pa.yaml", foot, "LayoutDirection")
    assert "LayoutDirection.Vertical" in d and "LayoutDirection.Horizontal" in d
    assert hub(foot, "Height", 360) == 44 + 8 + 44
    assert hub(foot, "Height", 1366) == 36
    kids = [list(k)[0] for k in _ctrls("ScreenMdHub.pa.yaml")[foot]["Children"]]
    assert kids == ["btnMdCloseCancelled", "btnMdCloseCreated"]
    for m in ("conMdCloseConfirmModal", "conMdDelConfirmModal"):
        assert hub(m, "Width", 360) == 344
        assert hub(m, "Width", 1366) == 460
        assert hub(m, "Height", 1366) == 180
    assert hub("txtMdCloseConfirmText", "Height", 360) == 60
    assert hub("txtMdCloseConfirmText", "Height", 1366) == 40


def test_hub_popups_use_nearly_the_whole_phone():
    for m in ("conMdAprModal", "conMdSapModal", "conMdNotesModal"):
        assert hub(m, "Width", 360) == 344, m
    assert hub("conMdAprModal", "Width", 1366) == 720
    assert hub("conMdSapModal", "Width", 1366) == 640
