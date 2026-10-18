# -*- coding: utf-8 -*-
"""
Functional Location: Manufacturer- og Warranty-knappen kan vise
fluebenet OG hele teksten paa een linje (issue #362), uden at raekken
bliver bredere eller hoejere.

    python3 -m pytest tests/test_fl_mfr_warranty_width.py
"""
import sys

from conftest import TOOLS
from test_fl_spool_row import _parts, _prop

sys.path.insert(0, TOOLS)
from build_helpers import text_px  # noqa: E402


def test_buttons_fit_icon_and_full_label():
    p = _parts()
    chrome = 2 * (p.BTN_PAD_X + p.BTN_BORDER) + p.BTN_ICON + p.BTN_ICON_GAP
    for text in ("Manufacturer", "Warranty"):
        assert p.MFR_WAR_W >= text_px(text, p.BTN_SIZE) + chrome, text
    # Begge knapper har samme bredde, i overskrift og raekke.
    w = _prop("btnFlRowMfr", "Width")
    assert _prop("btnFlRowWar", "Width") == w == str(p.MFR_WAR_W)
    assert _prop("txtFlRowsHeadMfr", "Width") == _prop("txtFlRowsHeadWar", "Width") == w
    # Fluebenet og status-logikken er uaendret; hoejden er den samme.
    for b in ("btnFlRowMfr", "btnFlRowWar"):
        assert "ButtonLayout.IconBefore" in _prop(b, "Layout"), b
        assert '"Checkmark"' in _prop(b, "Icon"), b
        assert _prop(b, "Height") == "30", b


def test_row_is_not_wider_than_before():
    """Pladsen tages fra de andre kolonner, ikke fra sektionens bredde."""
    p = _parts()
    assert p.V_BASE <= p.V_BASE_MAX
    assert p.DESC_MIN >= text_px("Description", 11) + 24
