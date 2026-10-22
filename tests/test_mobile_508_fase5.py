# -*- coding: utf-8 -*-
"""Issue #508, fase 5: KKS Lookup og Issue Board paa en telefon.

Mobil er tieren under Tablet (LayoutRank = 1, App.Width < 720). Hver test
tjekker BAADE telefonens vaerdi og at Tablet/Desktop er, som de var foer
fasen (KKS App/build/kks_parts.py, Issue Board/build/ib_parts.py)."""
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

SCREENS = {"Kks": "ScreenKks", "Ib": "ScreenIssueBoard"}
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
    for k, v in subs.items():
        e = e.replace(k, v)
    return cl._evaluate_n(e, w, n)


# ---------------------------------------------------------------------------
# KKS Lookup
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,desk", [
    ("btnKksKeyFunction", 32), ("btnKksKeyAggregate", 32), ("btnKksKeyComponent", 32),
    ("btnKksFlOpenNarrow", 32), ("btnKksSel1", 40), ("btnKksSel2", 40), ("btnKksSel3", 40),
    ("inpKksFind", 36), ("btnKksCrumbAll", 32), ("btnKksCrumbL1", 32), ("btnKksCrumbL3", 32),
    ("btnKksShowMore", 44),
])
def test_kks_touch_targets(name, desk):
    for w in PHONES:
        assert ev("Kks", name, "Height", w) == 44, (name, w)
    for w in TABLET_UP:
        assert ev("Kks", name, "Height", w) == desk, (name, w)


def test_kks_results_have_no_inner_scroll_on_a_phone():
    sb = _p("Kks", "galKksRows", "ShowScrollbar")
    assert _branch(sb, True).strip("()") == "false"
    assert _branch(sb, False).strip("()") == "true"
    items = _p("Kks", "galKksRows", "Items")
    assert "FirstN(colKksResults, Coalesce(varKksShowN, 50))" in _branch(items, True)
    assert _branch(items, False).strip("()") == "colKksResults"
    # Hoejden er summen af de viste kort - ikke 1120 med egen scroll.
    h = _p("Kks", "galKksRows", "Height")
    assert "Sum(FirstN(colKksResults" in _branch(h, True) and "1120" not in _branch(h, True)
    assert "Max(560, App.Height - 600)" in _branch(h, False)
    vis = _p("Kks", "btnKksShowMore", "Visible")
    assert vis.startswith("LayoutRank < 2 && ")


def test_kks_cards_fit_the_template_on_a_phone():
    for w in PHONES:
        tpl = ev("Kks", "rctKksRowBg", "Width", w)
        cx, cw = ev("Kks", "txtKksRowCode", "X", w), ev("Kks", "txtKksRowCode", "Width", w)
        dx, dw = ev("Kks", "txtKksRowDesc", "X", w), ev("Kks", "txtKksRowDesc", "Width", w)
        kx = ev("Kks", "btnKksRowCopy", "X", w, **{"Self.Width": "44"})
        assert tpl and cx + cw <= kx, w                 # koden naar ikke ind under kopier
        assert dx + dw <= tpl, w                        # beskrivelsen i hele bredden
        assert ev("Kks", "txtKksRowDesc", "Y", w) >= 40, w   # under kodelinjen
        assert dw >= 0.85 * tpl, w
    # Tablet og op: tabellens kolonner som foer.
    for w in TABLET_UP:
        assert ev("Kks", "txtKksRowCode", "Width", w) == 72
        assert ev("Kks", "txtKksRowDesc", "Y", w) == 11


def test_kks_table_head_only_from_tablet():
    vis = _p("Kks", "conKksTableHead", "Visible")
    assert _branch(vis, True).strip("()") == "false"
    assert _branch(vis, False).strip("()") == "true"


@pytest.mark.parametrize("name,desk", [("conKksPickModal", 460), ("conKksFlModal", 560)])
def test_kks_popups_are_sheets_on_a_phone(name, desk):
    for w in PHONES:
        assert ev("Kks", name, "Width", w) == w - 16
        assert ev("Kks", name, "Y", w) == 8
    for w in TABLET_UP:
        assert ev("Kks", name, "Width", w) == min(desk, w - 24)


# ---------------------------------------------------------------------------
# Issue Board
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,desk", [
    ("btnIbNew", 36), ("tabIbScope", 36), ("tabIbState", 36), ("inpIbSearch", 36),
    ("drpIbFltApp", 36), ("drpIbFltSection", 36), ("drpIbFltStatus", 36),
    ("drpIbFltPriority", 36), ("drpIbSort", 36), ("btnIbClearFlt", 30), ("btnIbRetry", 36),
    ("drpIbFormApp", 36), ("drpIbFormSection", 36), ("inpIbOther", 36), ("inpIbTitle", 36),
    ("inpIbRelated", 36), ("drpIbSeverity", 36), ("drpIbStatus", 36), ("drpIbPriority", 36),
    ("drpIbAssignee", 36), ("btnIbMore", 34), ("btnIbFormSubmit", 36),
    ("btnIbTabDetails", 36), ("btnIbTabActivity", 36), ("btnIbTabFiles", 36),
    ("btnIbUpload", 36), ("inpIbDelConfirm", 36), ("btnIbDelConfirm", 36),
    ("btnIbPostRetry", 36),
])
def test_ib_touch_targets(name, desk):
    for w in PHONES:
        assert ev("Ib", name, "Height", w) == 44, (name, w)
    for w in TABLET_UP:
        assert ev("Ib", name, "Height", w) == desk, (name, w)


def test_ib_filters_behind_a_button_on_a_phone():
    assert _p("Ib", "btnIbFiltersM", "Visible") == "LayoutRank < 2"
    for name in ("conIbFltPairA", "conIbFltPairB", "drpIbSort"):
        vis = _p("Ib", name, "Visible")
        assert "(!(LayoutRank < 2) || Coalesce(varIbFiltersOpen, false))" in vis, name
    lab = _p("Ib", "btnIbFiltersM", "AccessibleLabel")
    assert "Show filters" in lab and "Hide filters" in lab
    # Lupen giver plads til knappen paa en telefon - ellers som foer.
    vis = _p("Ib", "icoIbSearchIcon", "Visible")
    assert _branch(vis, True).strip("()") == "false"


def test_ib_list_is_cards_without_inner_scroll_on_a_phone():
    sb = _p("Ib", "galIbList", "ShowScrollbar")
    assert _branch(sb, True).strip("()") == "false" and _branch(sb, False).strip("()") == "true"
    for w in PHONES:
        assert ev("Ib", "galIbList", "TemplateSize", w) == 108
    assert ev("Ib", "galIbList", "TemplateSize", 800) == 92
    assert ev("Ib", "galIbList", "TemplateSize", 1366) == 48
    items = _p("Ib", "galIbList", "Items")
    assert "FirstN(IbListRows, Coalesce(varIbShowN, 50))" in _branch(items, True)
    assert _branch(items, False).strip("()").startswith("With(")
    assert "IbListRows" not in _branch(items, False)
    h = _branch(_p("Ib", "galIbList", "Height"), True)
    assert "App.Height" not in h          # ingen "resten af skaermen" med egen scroll
    # Taelleren taeller alle raekker, ogsaa dem bag Show more.
    assert "CountRows(IbListRows)" in _branch(_p("Ib", "txtIbCount", "Text"), True)
    assert "galIbList.AllItemsCount" in _branch(_p("Ib", "txtIbCount", "Text"), False)
    app = open(os.path.join(ROOT, "BIO SAP App", "App.pa.yaml"), encoding="utf-8").read()
    assert "IbListRows = With(" in app


def test_ib_card_fits_at_320():
    for w in PHONES:
        tpl = ev("Ib", "rctIbRowRule", "Width", w)
        nx, nw = ev("Ib", "bdgIbRowNoC", "X", w), ev("Ib", "bdgIbRowNoC", "Width", w)
        sx, sw = ev("Ib", "imgIbRowStatusC", "X", w), ev("Ib", "imgIbRowStatusC", "Width", w)
        assert nx + nw < sx and sx + sw <= tpl, w
        tx, tw = ev("Ib", "txtIbRowTitleC", "X", w), ev("Ib", "txtIbRowTitleC", "Width", w)
        assert tx + tw <= tpl, w
        att = ev("Ib", "btnIbRowAttachC", "X", w)
        assert att + 44 <= tpl and ev("Ib", "btnIbRowAttachC", "Y", w) + 44 <= 108, w
    # Tablet: det kompakte kort som foer (nummeret 96 bredt).
    assert ev("Ib", "bdgIbRowNoC", "Width", 800) == 96


def test_ib_side_panels_use_the_phone_padding():
    for name in ("conIbFormModal", "conIbDetModal"):
        for side in ("PaddingLeft", "PaddingRight"):
            assert ev("Ib", name, side, 360) == 12, name
            assert ev("Ib", name, side, 1024) == 18, name
    for w in PHONES:
        assert ev("Ib", "btnIbFormSubmit", "Width", w) == w - 24
    assert ev("Ib", "btnIbFormSubmit", "Width", 1366) == 164


def test_ib_detail_title_full_width_and_facts_folded_on_a_phone():
    assert _p("Ib", "txtIbDetTitleM", "Visible") == "LayoutRank < 2"
    t = _p("Ib", "txtIbDetTitle", "Text")
    assert _branch(t, True).strip("()") == '""' and _branch(t, False).strip("()") == "varIbSel.Title"
    for name in ("conIbDetInfo", "conIbDetFacts"):
        assert "Coalesce(varIbDetFactsOpen, false)" in _p("Ib", name, "Visible"), name
    assert _p("Ib", "btnIbDetFactsFold", "AccessibleLabel").startswith("If(")
    # Activity: feeden er saa hoej som sine linjer paa en telefon - fanen er
    # den eneste scroll. Fra Tablet fylder feeden fanen som foer.
    feed = _p("Ib", "conIbActFeed", "Height")
    assert "Parent.Height" not in _branch(feed, True)
    assert "Parent.Height" in _branch(feed, False)
    assert '"Files"' in _branch(_p("Ib", "btnIbTabFiles", "Text"), True)
    assert '"Attachments"' in _branch(_p("Ib", "btnIbTabFiles", "Text"), False)


def test_ib_similar_issues_are_cards_on_a_phone():
    for w in PHONES:
        assert ev("Ib", "galIbSimilar", "TemplateSize", w) == 74
        tw = ev("Ib", "btnIbSimOpen", "Width", w)
        assert ev("Ib", "txtIbSimTitle", "Width", w) == tw - 16
        assert ev("Ib", "imgIbSimStatus", "X", w) + 119 <= tw, w
    assert ev("Ib", "galIbSimilar", "TemplateSize", 1024) == 44


def test_ib_delete_popup_on_a_phone():
    for w in PHONES:
        assert ev("Ib", "conIbDelModal", "Width", w) == w - 16
    for w in TABLET_UP:
        assert ev("Ib", "conIbDelModal", "Width", w) == min(480, w - 24)
    d = _p("Ib", "conIbDelFooter", "LayoutDirection")
    assert "Vertical" in _branch(d, True) and "Horizontal" in _branch(d, False)
