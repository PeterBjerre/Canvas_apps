# -*- coding: utf-8 -*-
"""Issue #276: "Department" hedder "All requests" i hubbens skifter paa
desktop og tablet. Mobilen beholder "My" | "All", og logikken
(varMdView = "queue") er uaendret.

Issue #371: My requests | All requests er en segmenteret skinne - den
SAMME build_helpers.segmented som Open/Closed/All ved siden af (graa
bane, udfyldt valgt pille med flueben) - i stedet for #303's faner. Pladsen,
filtreringen, det valgte, antallet og mobilens "My" | "All" er uaendrede."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _y():
    return open(SCREEN, encoding="utf-8").read()


def _block(name, text=None):
    text = text or _y()
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, prop):
    m = re.search(r"^( +)%s: \|-\n +=(.*(?:\n\1    .*)*)" % prop, block, re.M)
    return m.group(2).strip() if m else None


def _own(block):
    """Kun kontrollens egne egenskaber (ikke boernenes)."""
    return block.split("Children:")[0]


# Udseendet, der goer en skinne til "Open/Closed/All-skinnen".
TRACK_PROPS = ("Fill", "BorderColor", "Height", "LayoutGap", "PaddingLeft", "RadiusTopLeft")
SEG_PROPS = ("Appearance", "BasePaletteColor", "BorderColor", "Color", "FontWeight", "Icon",
             "Height", "RadiusTopLeft")


def _same_style(view_seg, status_seg, view_on, status_on):
    for p in SEG_PROPS:
        assert _prop(view_seg, p) == _prop(status_seg, p).replace(status_on, view_on), p


def test_department_is_gone_from_the_hub():
    y = _y()
    assert '"Department"' not in y
    assert '"Dept."' not in y


def test_view_selector_is_styled_like_open_closed_all():
    y = _y()
    view, status = _block("conMdFltView", y), _block("conMdFltStatus", y)
    assert "Control: GroupContainer" in view
    assert "ModernTabList" not in view
    for p in TRACK_PROPS + ("Visible", "AlignInContainer"):
        assert _prop(_own(view), p) == _prop(_own(status), p), p
    _same_style(_block("conMdFltViewMine", y), _block("conMdFltStatusOpen", y),
                'varMdView = "mine"', 'varMdStatusMode = "open"')
    _same_style(_block("conMdFltViewAll", y), _block("conMdFltStatusOpen", y),
                'varMdView = "queue"', 'varMdStatusMode = "open"')
    # Samme trin: flueben kun i det brede, og samme skriftstoerrelse.
    for seg in ("conMdFltViewMine", "conMdFltViewAll"):
        b = _block(seg, y)
        assert _prop(b, "Size") == _prop(_block("conMdFltStatusOpen", y), "Size")
        assert "ButtonLayout.IconBefore" in _prop(b, "Layout")


def test_view_selector_keeps_its_place_texts_and_queue_logic():
    y = _y()
    # Stadig til hoejre i filterlinjen: efter flagene og foer antallet.
    i = y.index("- conMdFltView:")
    assert y.index("- btnMdFltStuck:") < i < y.index("- txtMdTotal:")
    mine, all_ = _block("conMdFltViewMine", y), _block("conMdFltViewAll", y)
    assert '"Mine", "My requests")' in _prop(mine, "Text")
    assert '"All", "All requests")' in _prop(all_, "Text")
    for b, key in ((mine, "mine"), (all_, "queue")):
        on = _prop(b, "OnSelect")
        assert on.startswith(f'Set(varMdView, "{key}"); Set(varMdDomain, "");')
        assert "ClearCollect(colMdScope" in on and "SaveData(colAppPrefs" in on
        assert f'varMdView = "{key}", ", selected"' in _prop(b, "AccessibleLabel")
    # Antallet er uaendret og staar lige efter.
    assert '" requests")' in _prop(_block("txtMdTotal", y), "Text")


def test_view_selector_shrinks_with_the_filter_row():
    w = _prop(_own(_block("conMdFltView")), "Width")
    widths = [int(n) for n in re.findall(r"PanelInset\)\) >= \d+, (\d+)", w)]
    widths.append(int(re.search(r", (\d+)\)$", w).group(1)))
    # fuld > kompakt > kort.
    assert widths[0] > widths[1] > widths[2]


def test_mobile_keeps_my_and_all_as_the_same_track():
    y = _y()
    b = _block("conMdViewM", y)
    assert "ModernTabList" not in y
    assert "Control: GroupContainer" in b
    assert _prop(_own(b), "Visible") == "LayoutRank < 2"
    for p in TRACK_PROPS:
        assert _prop(_own(b), p) == _prop(_own(_block("conMdFltStatus", y)), p), p
    for seg, txt, key in (("conMdViewMMine", "My", "mine"), ("conMdViewMAll", "All", "queue")):
        s = _block(seg, y)
        assert _prop(s, "Text") == f'"{txt}"'
        assert _prop(s, "Layout") == "ButtonLayout.TextOnly"
        _same_style(s, _block("conMdFltStatusOpen", y), f'varMdView = "{key}"',
                    'varMdStatusMode = "open"')
        on = _prop(s, "OnSelect")
        assert on.startswith(f'Set(varMdView, "{key}"); Set(varMdDomain, "");')
        assert "ClearCollect(colMdScope" in on and "SaveData(colAppPrefs" in on
