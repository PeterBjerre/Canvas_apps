# -*- coding: utf-8 -*-
"""Issue #243: hver knap, der starter en ny anmodning, hedder praecis
"New Request" - uden plus-ikon og uden "+" i teksten, paa alle
skaermbredder (ogsaa paa en telefon, hvor den foer hed "New").

Raekkeknapper (New row, Add ...) er ikke anmodningsknapper og roeres ikke."""
import os
import re

from build_helpers import fit_button_width, new_request_widths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")

# (skaerm, kontrol) - kontrolnavnene er uaendrede.
BUTTONS = [
    ("ScreenMdHub.pa.yaml", "btnMdNewRequest"),
    ("ScreenVhPlan.pa.yaml", "btnVhpNewRequest"),
    ("ScreenEquipment.pa.yaml", "btnEqNewRequest"),
    ("ScreenMaterial.pa.yaml", "btnMatNewRequest"),
    ("ScreenMeasuringPoint.pa.yaml", "btnMpNewRequest"),
    ("ScreenFunctionalLocation.pa.yaml", "btnFlNew"),
]


def _yaml(screen):
    with open(os.path.join(APP, screen), encoding="utf-8") as f:
        return f.read()


def _block(text, name):
    m = re.search(r"^(\s*)- %s:\n(.*?)(?=^\1- |\Z)" % re.escape(name), text, re.M | re.S)
    assert m, name
    return m.group(2)


def _prop(block, prop):
    m = re.search(r"^\s*%s: \|-\n(.*)$" % prop, block, re.M)
    assert m, prop
    return m.group(1).strip()


def test_every_new_request_button_has_the_exact_label_and_no_icon():
    full_w, phone_w = new_request_widths()
    assert full_w == fit_button_width('"New Request"')
    for screen, name in BUTTONS:
        b = _block(_yaml(screen), name)
        assert _prop(b, "Text") == '="New Request"', (screen, name)
        assert "Icon:" not in b, (screen, name)
        assert _prop(b, "Layout") == "=ButtonLayout.TextOnly", (screen, name)
        assert _prop(b, "Align") == "=Align.Center", (screen, name)
        # Bredden er teksten + luft (ingen ICON_W), saa teksten er centreret.
        assert _prop(b, "Width") == "=If(LayoutRank < 2, %d, %d)" % (phone_w, full_w), (screen, name)


def test_no_button_text_says_new_request_any_other_way():
    for screen in os.listdir(APP):
        if not screen.endswith(".pa.yaml"):
            continue
        y = _yaml(screen)
        for m in re.finditer(r"^\s*- (\w+):\n\s*Control: ModernButton", y, re.M):
            text = _prop(_block(y, m.group(1)), "Text")
            assert "New request" not in text, (screen, m.group(1), text)
            assert not re.search(r'"\+\s*New', text), (screen, m.group(1), text)
            assert '"New"' not in text, (screen, m.group(1), text)
