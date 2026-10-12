# -*- coding: utf-8 -*-
"""Fast bundbjaelke under Desktop (UX-review 2026-10, M8)."""
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")

# (skaerm, tag, header-knapper)
SCREENS = [
    ("ScreenEquipment.pa.yaml", "Eq", ("SendDraft", "Submit")),
    ("ScreenMaterial.pa.yaml", "Mat", ("SendDraft", "Submit")),
    ("ScreenMeasuringPoint.pa.yaml", "Mp", ("SendDraft", "Submit")),
    ("ScreenFunctionalLocation.pa.yaml", "Fl", ("SaveDraft", "Submit")),
    ("ScreenVhPlan.pa.yaml", "Vhp", ("SaveDraft", "Submit")),
]
_CACHE = {}


def _props(screen):
    if screen not in _CACHE:
        doc = yaml.safe_load(open(os.path.join(APP, screen), encoding="utf-8"))
        out = {}

        def walk(nodes):
            for it in nodes or []:
                for name, body in it.items():
                    out[name] = {k: str(v).lstrip("=").strip()
                                 for k, v in (body.get("Properties") or {}).items()}
                    walk(body.get("Children"))
        for scr in doc["Screens"].values():
            walk(scr.get("Children"))
        _CACHE[screen] = out
    return _CACHE[screen]


@pytest.mark.parametrize("screen,tag,btns", SCREENS)
def test_the_footer_copies_the_header_actions_below_desktop(screen, tag, btns):
    p = _props(screen)
    assert p[f"con{tag}Foot"]["Visible"] == "LayoutRank < 3"
    for b in btns:
        head, copy = p[f"btn{tag}{b}"], p[f"btn{tag}Foot{b}"]
        # Samme handling og samme regel for, hvornaar den kan bruges.
        assert head["OnSelect"] == copy["OnSelect"], b
        assert head["DisplayMode"] == copy["DisplayMode"], b
        # Headerens knap er skjult under Desktop.
        assert head["Visible"].startswith("LayoutRank >= 3"), b


@pytest.mark.parametrize("screen,tag,_b", SCREENS)
def test_the_body_leaves_room_for_the_footer(screen, tag, _b):
    assert "If(LayoutRank < 3, 60, 0)" in _props(screen)[f"con{tag}Body"]["Height"]
