# -*- coding: utf-8 -*-
"""Issue #508, fase 6: de faelles popupper og tilstande paa en telefon - og
den afsluttende gennemgang paa tvaers af alle skaerme.

Mobil er tieren under Tablet (LayoutRank = 1, App.Width < 720). Hver test
tjekker BAADE telefonens vaerdi og at Tablet/Desktop er, som de var foer."""
import os
import re
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
HUB = os.path.join(ROOT, "Masterdata Hub", "build")

import check_layout as cl  # noqa: E402
import mobile  # noqa: E402

PREFIX = {"Md": "ScreenMdHub", "Vhp": "ScreenVhPlan", "Fl": "ScreenFunctionalLocation",
          "Mat": "ScreenMaterial", "Eq": "ScreenEquipment", "Mp": "ScreenMeasuringPoint",
          "Kks": "ScreenKks", "Ib": "ScreenIssueBoard"}
DOMAIN = ("Mat", "Eq", "Mp")
LOADING = ("Vhp", "Fl", "Mat", "Eq", "Mp")
PHONES = (320, 360, 414, 719)
TABLET_UP = (720, 1024, 1366, 1920)
_CACHE = {}


def _ctrls(t):
    if t not in _CACHE:
        doc = yaml.safe_load(open(os.path.join(ROOT, "BIO SAP App", PREFIX[t] + ".pa.yaml"),
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


def ev(t, name, key, w, n=3, app_h=None, **subs):
    e = _p(t, name, key)
    if e is None:
        return None
    e = _branch(e, w < 720)
    if app_h is not None:
        e = e.replace("App.Height", str(app_h))
    for k, v in subs.items():
        e = e.replace(k, v)
    return cl._evaluate_n(e, w, n)


def _both(t, name, key, phone, desk):
    for w in PHONES:
        assert ev(t, name, key, w) == phone, (t, name, key, w)
    for w in TABLET_UP:
        assert ev(t, name, key, w) == desk, (t, name, key, w)


# ---------------------------------------------------------------------------
# "Message us" (tools/feedback_popup.py) - alle skaerme
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", sorted(PREFIX))
def test_feedback_popup_is_a_phone_sheet(t):
    m = f"con{t}FbModal"
    for w in PHONES:
        assert ev(t, m, "Width", w) == w - 16
        assert ev(t, m, "PaddingLeft", w) == 12 and ev(t, m, "PaddingRight", w) == 12
    for w in TABLET_UP:
        assert ev(t, m, "Width", w) == min(560, w - 40)
        assert ev(t, m, "PaddingLeft", w) == 18
    # Knapperne under hinanden i fuld bredde, 44 hoeje, Send nederst.
    for b in (f"btn{t}FbSend", f"btn{t}FbSendOutlook", f"btn{t}FbSubject",
              f"inp{t}FbSubjectFind", f"btn{t}FbSubjectPick"):
        h = {f"btn{t}FbSubject": 34, f"btn{t}FbSubjectPick": 36}.get(b, 36)
        _both(t, b, "Height", 44, h)
    foot = _ctrls(t)[f"con{t}FbFooter"]
    kids = [list(c)[0] for c in foot["Children"]]
    assert kids[-1] == f"btn{t}FbSend"
    assert _branch(_p(t, f"con{t}FbFooter", "LayoutDirection"), True).strip("()") \
        == "LayoutDirection.Vertical"
    # Emnelistens raekker er 44 paa mobil, 36 ellers.
    _both(t, f"gal{t}FbSubject", "TemplateSize", 44, 36)
    # Initialerne skjules paa mobil (Email har hele bredden).
    _both(t, f"con{t}FbInitialsCell", "Visible", 0, 1)


@pytest.mark.parametrize("app_h", (568, 640, 740, 900))
def test_feedback_popup_fits_the_phone_without_page_scroll(app_h):
    """Popuppen staar paa skaermen (8 px luft over og under), saa sloeret
    ikke scroller - kun emnelisten har sin egen scroll."""
    for t in PREFIX:
        for w in (320, 360, 414):
            h = ev(t, f"con{t}FbModal", "Height", w, app_h=app_h, **{"H.control": "44"})
            assert h is not None and h + 16 <= app_h + 0.01, (t, w, app_h, h)


def test_feedback_intro_is_short_on_a_phone():
    phone = _branch(_p("Md", "txtMdFbIntro", "Text"), True)
    desk = _branch(_p("Md", "txtMdFbIntro", "Text"), False)
    assert "something not working" in desk and "something not working" not in phone
    assert _p("Md", "txtMdFbIntro", "AccessibleLabel") == _p("Md", "txtMdFbIntro", "Text")


# ---------------------------------------------------------------------------
# Indlaesningskortet, panelets Retry, tomme tilstande, toast
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", LOADING)
def test_load_card_buttons_are_touch_targets(t):
    for b in (f"btn{t}LoadClose", f"btn{t}LoadRetry"):
        _both(t, b, "Height", 44, 36)
    for w in PHONES:
        assert ev(t, f"con{t}LoadCard", "Width", w) == w - 16
    for w in TABLET_UP:
        assert ev(t, f"con{t}LoadCard", "Width", w) == min(360, w - 32)


@pytest.mark.parametrize("t", ("Fl", "Mat", "Eq", "Mp", "Ib"))
def test_panel_retry_is_a_touch_target(t):
    _both(t, f"btn{t}EditorRetry", "Height", 44, 32)
    _both(t, f"con{t}EditorSaveStatus", "Height", 44, 32)


@pytest.mark.parametrize("t,name", [("Ib", "btnIbEmptyAction"), ("Md", "btnMdClearFilters")])
def test_empty_state_action_is_a_touch_target(t, name):
    _both(t, name, "Height", 44, 36)


@pytest.mark.parametrize("t", sorted(PREFIX))
def test_toast_sits_above_the_bottom_bar_on_a_phone(t):
    for w in PHONES:
        assert ev(t, f"con{t}Toast", "Width", w) == w - 16
        assert ev(t, f"con{t}Toast", "Y", w, app_h=800, **{"Self.Height": "64"}) == 800 - 64 - 68
    for w in TABLET_UP:
        assert ev(t, f"con{t}Toast", "Width", w) == min(420, w - 32)
        assert ev(t, f"con{t}Toast", "Y", w, app_h=800, **{"Self.Height": "64"}) == 800 - 64 - 24


# ---------------------------------------------------------------------------
# Domaeneskaermene: header-knapper og Docs-fanen
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t", DOMAIN)
def test_domain_header_buttons_are_touch_targets(t):
    for b in ("NewRequest", "EditRequest", "Duplicate", "DeleteRequest"):
        _both(t, f"btn{t}{b}", "Height", 44, 36)
    for b in ("EditRequest", "Duplicate", "DeleteRequest"):
        for w in PHONES:
            assert ev(t, f"btn{t}{b}", "Width", w) == 44, (t, b, w)


@pytest.mark.parametrize("t", ("Mat", "Eq"))
def test_docs_tab_has_no_inner_scroll_on_a_phone(t):
    h = _p(t, f"con{t}AttBody", "Height")
    assert "App.Height" not in _branch(h, True)
    assert _branch(h, False).strip("()") == "App.Height - 250"
    _both(t, f"btn{t}AttUpload", "Height", 44, 36)


# ---------------------------------------------------------------------------
# Masterdata Hub: Show more i stedet for 100-raekkers-graensen
# ---------------------------------------------------------------------------
def test_hub_shows_more_than_100_requests_on_a_phone():
    # Hubbens mappe har sin egen check_layout.py - den maa ikke skygge
    # for tools/check_layout (importeret ovenfor), saa den kommer sidst.
    if HUB not in sys.path:
        sys.path.append(HUB)
    import build_hub as bh
    items = _p("Md", "galMdRequests", "Items")
    assert _branch(items, True).strip("()").startswith("FirstN(")
    assert "Coalesce(varMdShowN, 50)" in _branch(items, True)
    # Fra Tablet og op: den samme delegerede formel som foer.
    norm = lambda x: re.sub(r"\s+", "", x)
    assert norm(_branch(items, False)) == norm("(" + bh.ITEMS + ")")
    h = _p("Md", "galMdRequests", "Height")
    assert "100" not in re.sub(r"\* 100\b", "", _branch(h, True)).replace("ROW", "")
    vis = _p("Md", "btnMdShowMore", "Visible")
    assert vis.startswith("LayoutRank < 2 && ")
    assert _p("Md", "btnMdShowMore", "OnSelect") == "Set(varMdShowN, Coalesce(varMdShowN, 50) + 50)"
    assert ev("Md", "btnMdShowMore", "Height", 360) == 44
    for w in TABLET_UP:
        assert ev("Md", "btnMdShowMore", "Visible", w) == 0


def test_hub_search_and_filter_are_touch_targets():
    _both("Md", "inpMdFind", "Height", 44, 36)
    _both("Md", "drpMdFltMobile", "Height", 44, 36)
    for b in ("conMdViewMMine", "conMdViewMAll"):
        assert ev("Md", b, "Width", 360) >= 44


@pytest.mark.parametrize("name", ("conMdAprModal", "conMdSapModal", "conMdNotesModal"))
def test_hub_popups_have_the_phone_padding(name):
    for w in PHONES:
        assert ev("Md", name, "PaddingLeft", w) == 12
    for w in TABLET_UP:
        assert ev("Md", name, "PaddingLeft", w) in (16, 18)


# ---------------------------------------------------------------------------
# KKS' FL-soegning, checkbokse, trin
# ---------------------------------------------------------------------------
def test_kks_fl_search_is_touch_sized():
    _both("Kks", "cmbKksFl", "Height", 44, 36)
    _both("Kks", "btnKksFlSearch", "Height", 44, 36)


@pytest.mark.parametrize("t,name", [("Mat", "chkMatObjPick"), ("Vhp", "chkVhpObjPick"),
                                    ("Vhp", "chkVhpPickerRowSel"), ("Fl", "chkFlRowAtex"),
                                    ("Ib", "chkIbInternal")])
def test_checkboxes_are_touch_targets(t, name):
    for w in PHONES:
        assert ev(t, name, "Height", w) == 44, (name, w)


def test_vh_steps_are_touch_targets_at_320():
    for w in (320, 360, 414):
        assert ev("Vhp", "imgVhpStep1M", "Height", w, **{"PanelInset": "0"}) >= 44


# ---------------------------------------------------------------------------
# Den afsluttende gennemgang: ingen klikbar knap/billede under 40 px
# ---------------------------------------------------------------------------
_PURE = re.compile(r"\b(?!LayoutRank\b|App\.Width\b|App\.Height\b|true\b|false\b|If\b)"
                   r"[A-Za-z_][\w.]*")


def _split_and(s):
    """De led i s, der er forbundet med && paa yderste niveau."""
    out, depth, quote, start, i = [], 0, False, 0, 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif depth == 0 and s[i:i + 2] == "&&":
                out.append(s[start:i])
                start = i + 2
                i += 1
        i += 1
    out.append(s[start:])
    return [x.strip() for x in out]


def _hidden_on_phone(p, w):
    """Skjult paa telefonen: hele udtrykket, eller et &&-led, der kun
    afhaenger af bredden, er falsk. Et led med tilstand antages sandt."""
    v = p.get("Visible")
    if v is None:
        return False
    s = mobile.phone(str(v).lstrip("=").strip()).strip()
    if s.lower() == "false":
        return True
    for part in _split_and(s):
        while part.startswith("(") and part.endswith(")") and part.count("(") == 1:
            part = part[1:-1]
        if _PURE.search(re.sub(r'"[^"]*"', "", part)):
            continue
        r = cl._evaluate_n(part, w, 3)
        if r is not None and not r:
            return True
    return False


# Skrivebeskyttede felter, der kun viser tekst (ikke klikflader).
READ_ONLY = {"inpMdSapNo", "inpVhpPkgRowOpNo", "inpVhpPkgRowText"}


@pytest.mark.parametrize("w", (320, 360, 414))
def test_no_small_touch_targets_on_any_screen(w):
    small = []
    for t in PREFIX:
        def walk(items):
            for it in items or []:
                (n, b), = it.items()
                p = b.get("Properties") or {}
                if _hidden_on_phone(p, w):
                    continue
                c = b.get("Control", "")
                onsel = str(p.get("OnSelect") or "=false").strip()
                click = (c in ("ModernButton", "Image") and onsel not in ("=false", "=")) \
                    or c in ("ModernTextInput", "ModernDropdown", "ModernCombobox",
                             "ModernCheckbox", "ModernDatePicker")
                if click and n not in READ_ONLY:
                    h = cl._evaluate_n(p.get("Height"), w, 3)
                    if h is not None and h < 40:
                        small.append((t, n, h))
                walk(b.get("Children"))
        doc = yaml.safe_load(open(os.path.join(ROOT, "BIO SAP App", PREFIX[t] + ".pa.yaml"),
                                  encoding="utf-8"))
        walk(list(doc["Screens"].values())[0].get("Children"))
    assert not small, small


@pytest.mark.parametrize("w", (320, 360, 414))
def test_icon_only_controls_have_an_accessible_label(w):
    missing = []
    for t in PREFIX:
        for n, b in _ctrls(t).items():
            p = b.get("Properties") or {}
            c = b.get("Control", "")
            onsel = str(p.get("OnSelect") or "=false").strip()
            icon_only = (c == "Image" and onsel not in ("=false", "=")) or \
                (c == "ModernButton" and "IconOnly" in str(p.get("Layout", "")))
            if icon_only and not str(p.get("AccessibleLabel", "")).strip("= "):
                missing.append((t, n))
    assert not missing, missing
