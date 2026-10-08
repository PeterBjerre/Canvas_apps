# -*- coding: utf-8 -*-
"""Maintenance Plan-headerens knapper (issue #211).

Knapperne skal altid kunne staa paa linjen: titel + trin + knapper maa
ikke blive bredere end headeren ved nogen skaermbredde, og More actions
(...) er kun et ikon med "More actions" som tooltip og tilgaengeligt navn.
Delete er sidste punkt i menuen."""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VHP = os.path.join(ROOT, "Maintenance Plan App", "build")
if VHP not in sys.path:
    sys.path.insert(0, VHP)

import build_hero as bh  # noqa: E402
import layout_tokens as lay  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _layout(app_w):
    """Python-udgaven af bredderne i build_hero.build_top_bar."""
    tablet = app_w >= lay.min_width("Tablet")
    desktop = app_w >= lay.min_width("Desktop")
    nav = lay.NAV_W if tablet else 0
    shell = app_w - nav - lay.SHELL_INSET
    # Headerens indre bredde: rammen minus headerens padding.
    inner = app_w - nav - lay.PAGE_PAD_L - lay.PAGE_PAD_R - lay.SCROLLBAR_W
    rest = shell - bh.STEPS_W - 32 if desktop else shell - 16
    compact = (not tablet) or rest - bh.FULL_W < bh.TITLE_MIN
    btn_w = bh.COMPACT_W if compact else bh.FULL_W
    side_w = max(btn_w, rest / 2) if desktop else btn_w
    if not tablet:
        return inner, btn_w, 0, compact
    used = (rest - side_w) + 16 + side_w + (bh.STEPS_W + 16 if desktop else 0)
    return inner, used, rest - side_w, compact


@pytest.mark.parametrize("app_w", [320, 360, 390, 430, 600, 719, 720, 768, 900, 1023,
                                   1024, 1180, 1264, 1280, 1366, 1440, 1600, 1920, 2560])
def test_buttons_fit_the_header(app_w):
    inner, used, title_w, _compact = _layout(app_w)
    assert used <= inner, (app_w, used, inner)
    assert title_w >= 0


def test_labels_only_collapse_when_needed():
    # Paa en almindelig baerbar staar teksterne; paa en telefon kun ikonerne.
    assert not _layout(1366)[3]
    assert _layout(390)[3]


def _block(text, name):
    m = re.search(r"^(\s*)- %s:\n(.*?)(?=^\1- |\Z)" % re.escape(name), text, re.M | re.S)
    assert m, name
    return m.group(2)


def test_more_actions_is_icon_only():
    with open(SCREEN, encoding="utf-8") as f:
        y = f.read()
    b = _block(y, "btnVhpMoreActs")
    assert '="More actions"' in b.split("AccessibleLabel:")[1].split("\n")[1]
    assert '="More actions"' in b.split("Tooltip:")[1].split("\n")[1]
    assert "=ButtonLayout.IconOnly" in b
    assert '="MoreHorizontal"' in b
    assert '=""' in b.split("Text:")[1].split("\n")[1]


def test_header_order_and_delete_last():
    with open(SCREEN, encoding="utf-8") as f:
        y = f.read()
    row = _block(y, "conVhpHeadBtns")
    order = re.findall(r"- (btnVhp\w+|conVhpHeadSep):", row)
    assert order == ["btnVhpNewRequest", "conVhpHeadSep", "btnVhpEdit", "btnVhpSaveDraft",
                     "btnVhpSubmit", "btnVhpMoreActs"]
    menu = _block(y, "conVhpMoreMenu")
    items = re.findall(r"- (btnVhp\w+):", menu)
    assert items[-1] == "btnVhpDeleteRequest"
    assert "Set(varVhpDeleteOpen, true)" in menu
