"""Teams-ikonerne (issue #275) opfylder Teams' krav og passer til app-icon.png."""
import os
import sys

import pytest

Image = pytest.importorskip("PIL.Image")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import teams_icons as ti  # noqa: E402


def test_color_icon_is_opaque_square_without_blue_corners():
    im = Image.open(ti.COLOR_FILE)
    assert im.size == (192, 192)
    rgba = im.convert("RGBA")
    # Ingen gennemsigtighed: Teams har intet at fylde med accentfarven.
    assert rgba.getchannel("A").getextrema() == (255, 255)
    # Hjoerner og kanter er flisens lyseblaa, ikke afrundet/blaa.
    for xy in [(0, 0), (191, 0), (0, 191), (191, 191), (96, 0), (0, 96)]:
        assert rgba.getpixel(xy)[:3] == ti.TILE


def test_color_icon_keeps_symbol_colors():
    rgb = Image.open(ti.COLOR_FILE).convert("RGB")
    seen = {rgb.getpixel((x, y)) for x in range(192) for y in range(192)}
    # Symbolets farver fra app-icon.png: graa midte og fire prikker.
    for c in [(89, 102, 122), (0, 95, 184), (147, 51, 234),
              (180, 83, 9), (0, 128, 128)]:
        assert c in seen, c


def test_outline_icon_is_white_on_transparent():
    im = Image.open(ti.OUTLINE_FILE).convert("RGBA")
    assert im.size == (32, 32)
    # Alle pixels er hvide; kun alfa bærer symbolet.
    assert im.convert("RGB").getextrema() == ((255, 255),) * 3
    assert im.getchannel("A").getpixel((0, 0)) == 0
    # Ingen ekstra luft om symbolet.
    assert im.getchannel("A").getbbox() == (0, 0, 32, 32)


def test_committed_icons_match_generator():
    color, outline = ti.render()
    assert color.tobytes() == Image.open(ti.COLOR_FILE).convert("RGB").tobytes()
    assert (outline.tobytes()
            == Image.open(ti.OUTLINE_FILE).convert("RGBA").tobytes())
