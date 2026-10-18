# -*- coding: utf-8 -*-
"""
Issue #363: sidebaren har SAMME raekkefoelge paa alle skaerme.

  - Punkterne i skinnen og i det aabne panel staar i Masterdata Hubbens
    raekkefoelge (nav_order i tools/canvas_apps.json) paa hver skaerm.
  - Kun det aktive punkt er markeret ("(current app)"); det flyttes ikke.
  - Punktlisten faar resten af skinnens hoejde og ruller selv, saa skinnen
    aldrig er hoejere end skaermen og ikke kan rulles, saa de nederste
    punkter staar oeverst.

Power Fx kan ikke koeres her, saa testene laeser de GENEREREDE skaerme.

    python3 -m pytest tests/test_sidebar_order.py
"""
import glob
import os
import re

from conftest import ROOT

APP_DIR = os.path.join(ROOT, "BIO SAP App")
SCREENS = sorted(glob.glob(os.path.join(APP_DIR, "Screen*.pa.yaml")))
HUB = os.path.join(APP_DIR, "ScreenMdHub.pa.yaml")
ITEM = re.compile(r"^\s*- img([A-Z][a-z]+)Nav([A-Z][a-z]+)(Open)?:\s*$", re.M)
# Skinnens faste kontroller - alt andet med "Nav" er et punkt.
FIXED = {"Brand", "Toggle", "Message", "Lang", "Menu", "Page", "Scrim", "Help", "Theme"}


def _items(path):
    """{'': [punkter i skinnen], 'Open': [punkter i panelet]} i YAML-orden."""
    out = {"": [], "Open": []}
    for _p, key, opn in ITEM.findall(open(path, encoding="utf-8").read()):
        if key not in FIXED:
            out[opn or ""].append(key)
    return out


def test_screens_found():
    assert HUB in SCREENS and len(SCREENS) >= 5


def test_same_item_order_on_every_screen():
    hub = _items(HUB)
    assert hub[""] and hub[""] == hub["Open"]
    for path in SCREENS:
        got = _items(path)
        name = os.path.basename(path)
        assert got[""] == hub[""], name
        assert got["Open"] == hub["Open"], name


def test_order_is_nav_order():
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import env_config as env
    want = [k[0].upper() + k[1:] for k in env.NAV_ORDER]
    assert _items(HUB)[""] == want


def test_only_active_item_is_marked():
    for path in SCREENS:
        text = open(path, encoding="utf-8").read()
        # Een markering i skinnen og een i panelet - hoejst; en skaerm uden
        # eget punkt har ingen.
        assert text.count('(current app)"') <= 2, os.path.basename(path)


def test_item_list_fits_the_rail_and_scrolls_itself():
    for path in SCREENS:
        text = open(path, encoding="utf-8").read()
        found = 0
        for m in re.finditer(r"- con\w+NavTop(?:Open)?:\n(?:.*\n){0,40}?\s+Height: \|-\n\s+=(.*)\n"
                             r"(?:.*\n){0,20}?\s+LayoutOverflowY: \|-\n\s+=(.*)\n", text):
            height, overflow = m.group(1), m.group(2)
            assert height.startswith("Max(40, Parent.Height - "), (path, height)
            assert overflow == "LayoutOverflow.Scroll", (path, overflow)
            found += 1
        assert found == 2, (os.path.basename(path), found)  # skinnen og panelet
