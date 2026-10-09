# -*- coding: utf-8 -*-
"""Maintenance Plan: ingen plus-ikoner paa New request (issue #238).

New request i headeren og "Discard and start new" i bekraeftelsen er rene
tekstknapper - intet Icon, Layout TextOnly, og bredden er kun teksten +
luft, saa teksten staar midt i knappen. Handling, tekst og bekraeftelse er
de samme som foer."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VHP = os.path.join(ROOT, "Maintenance Plan App", "build")
if VHP not in sys.path:
    sys.path.insert(0, VHP)

import build_hero as bh  # noqa: E402
from build_helpers import fit_button_width  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _block(text, name):
    m = re.search(r"^(\s*)- %s:\n(.*?)(?=^\1- |\Z)" % re.escape(name), text, re.M | re.S)
    assert m, name
    return m.group(2)


def _prop(block, prop):
    m = re.search(r"^\s*%s: \|-\n(.*)$" % prop, block, re.M)
    assert m, prop
    return m.group(1).strip()


def _yaml():
    with open(SCREEN, encoding="utf-8") as f:
        return f.read()


def test_new_request_has_no_icon():
    b = _block(_yaml(), "btnVhpNewRequest")
    assert "Icon:" not in b
    assert _prop(b, "Layout") == "=ButtonLayout.TextOnly"
    assert _prop(b, "Align") == "=Align.Center"
    # Teksten er den samme; kun en telefon har "New" (der er ikke plads).
    assert _prop(b, "Text") == '=If(LayoutRank < 2, "New", "New request")'
    # Bredden er teksten + luft - ingen plads til et ikon.
    assert bh.NEW_W == fit_button_width('"New request"')
    assert _prop(b, "Width") == "=If(LayoutRank < 2, %d, %d)" % (bh.NEW_PHONE_W, bh.NEW_W)
    # Samme handling og bekraeftelse som foer.
    assert "Set(varVhpConfirmNew, true)" in b
    assert _prop(b, "AccessibleLabel") == '="Start a new blank request"'


def test_discard_and_start_new_has_no_icon():
    b = _block(_yaml(), "btnVhpNewConfirm")
    assert "Icon:" not in b
    assert _prop(b, "Layout") == "=ButtonLayout.TextOnly"
    assert _prop(b, "Text") == '="Discard and start new"'
    assert _prop(b, "Width") == "=%d" % fit_button_width('"Discard and start new"')
    assert "=Set(varVhpConfirmNew, false);" in b
    assert 'Notify("New request started.", NotificationType.Success)' in b


def test_other_confirm_buttons_keep_their_icons():
    # Kun de to knapper mister ikonet - Submit-bekraeftelsen er uaendret.
    y = _yaml()
    icons = {n for n in set(re.findall(r"- (btnVhp\w+):\n", y)) if "Icon:" in _block(y, n)}
    assert "btnVhpNewRequest" not in icons and "btnVhpNewConfirm" not in icons
    assert "btnVhpSubmit" in icons
