# -*- coding: utf-8 -*-
"""Issue #314: hubbens fem fliser har let skygge, 8 px runding og synlig
hover - ogsaa paa den valgte flise."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "Masterdata Hub", "build")
if HUB not in sys.path:
    sys.path.insert(0, HUB)

import build_hub as bh  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _block(y, name):
    """Kontrollens egne egenskaber: fra '- navn:' til dens Children eller
    naeste kontrol."""
    i = y.index(f"- {name}:")
    stops = [len(y)]
    c = y.find("Children:", i)
    if c != -1:
        stops.append(c)
    m = re.compile(r"\n\s*- \w+:\n").search(y, i + 1)
    if m:
        stops.append(m.start())
    return y[i:min(stops)]


def _prop(block, prop):
    """Vaerdien af en egenskab i en kontrols blok (|- paa naeste linje)."""
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == f"{prop}: |-":
            return lines[i + 1].strip()
        if ln.strip().startswith(f"{prop}: ="):
            return ln.strip()[len(prop) + 2:]
    raise AssertionError(f"{prop} mangler")


def test_tile_tokens():
    assert bh.TILE_RADIUS == 8
    assert bh.TILE_SHADOW == "DropShadow.Light"


def test_all_five_tiles_share_shadow_radius_and_hover():
    y = open(SCREEN, encoding="utf-8").read()
    assert len(bh.DOMAINS) == 5
    for d in bh.DOMAINS:
        n = d["short"]
        tile = _block(y, f"conMdTile{n}")
        assert _prop(tile, "DropShadow") == "=DropShadow.Light"
        for k in ("RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight"):
            assert _prop(tile, k) == "=8", (n, k)
        stripe = _block(y, f"conMdTileStripe{n}")
        assert _prop(stripe, "RadiusTopLeft") == "=8"
        assert _prop(stripe, "RadiusBottomLeft") == "=0"
        face = _block(y, f"imgMdTile{n}")
        hover = _prop(face, "HoverFill")
        # Den valgte flise skal ogsaa reagere: hover viser kortets fyld.
        assert hover == (f'=If(varMdDomain = "{d["key"]}", C.\'bg-card\', '
                         f"C.'{d['token']}-soft')"), hover
        assert _prop(face, "PressedFill") == hover
        assert _prop(face, "HoverBorderColor").startswith("=")
