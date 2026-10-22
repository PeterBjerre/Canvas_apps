# -*- coding: utf-8 -*-
"""Issue #557: ingen blaa fokusring om en fold-overskrift efter et klik.

Fold-overskriftens klik-lag (mobile.fold_head) har en gennemsigtig
fokuskant, men er stadig et tab stop. Det synlige tastaturfokus staar paa
chevronen med samme handling."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")
TRANSPARENT = "RGBA(0, 0, 0, 0)"
PRIMARY = "C.'color-brand-primary'"

# (skaerm, klik-lag, chevron)
HEADS = [
    ("ScreenFunctionalLocation.pa.yaml", "btnFlClassesFoldHeadHit", "btnFlClassesFold"),
    ("ScreenVhPlan.pa.yaml", "btnVhpPlanHeadFoldHit", "btnVhpPlanFold"),
]


def _own_props(text, name):
    i = text.index(f"- {name}:\n")
    indent = len(text[:i].rsplit("\n", 1)[1])
    lines = text[i:].split("\n")[1:]
    props, key = {}, None
    for ln in lines:
        if ln.strip() and len(ln) - len(ln.lstrip()) <= indent:
            break
        if ln.strip().startswith("Children:"):
            break
        m = re.match(r"^\s+(\w+): \|-$", ln)
        if m:
            key = m.group(1)
            continue
        if key and ln.strip().startswith("="):
            props[key] = ln.strip()[1:]
            key = None
    return props


def test_every_fold_head_layer_has_an_invisible_focus_border():
    seen = 0
    for screen in os.listdir(APP):
        if not screen.startswith("Screen"):
            continue
        t = open(os.path.join(APP, screen), encoding="utf-8").read()
        for name in re.findall(r"^ *- (btn\w*Fold\w*Hit):\n", t, re.M):
            p = _own_props(t, name)
            assert p["FocusedBorderColor"] == TRANSPARENT, (screen, name)
            # App checker kraever tykkelse > 0; laget er stadig et tab stop.
            assert p["FocusedBorderThickness"] == "2", (screen, name)
            assert p["TabIndex"] == "0", (screen, name)
            seen += 1
    assert seen >= len(HEADS)


def test_chevron_carries_the_visible_keyboard_focus():
    for screen, hit, chev in HEADS:
        t = open(os.path.join(APP, screen), encoding="utf-8").read()
        h, c = _own_props(t, hit), _own_props(t, chev)
        assert h["OnSelect"] == c["OnSelect"], screen
        assert c["FocusedBorderColor"] == PRIMARY, screen
        assert c["FocusedBorderThickness"] == "2", screen
        assert c["TabIndex"] == "0", screen
        # Hover og normal kant er uaendrede.
        assert h["BorderColor"] == TRANSPARENT and h["HoverFill"] == "C.'row-hover'", screen
