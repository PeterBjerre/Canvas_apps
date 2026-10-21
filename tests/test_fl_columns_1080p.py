# -*- coding: utf-8 -*-
"""
Issue #479: Functional Location og Description er brede nok ved 1080p.

  - FL kan vise den laengste FL (SSV13 HFC10AP001 -M01) uden "...".
  - Description kan vise 40 tegn.
  - Rows og Classes har samme bredder, saa de faelles kolonner flugter.
  - Ingen vandret scroll ved 1920 px.
  - Responsivt: FL faar pladsen foerst, og bredderne vokser med vinduet.

Issue #490: over lofterne fylder tabellen kortet - resten gaar ogsaa til
FL og Description (tests/test_fl_layout_edit_490.py).

Testen regner builderens Power Fx-udtryk om til tal.

    python3 -m pytest tests/test_fl_columns_1080p.py
"""
import math
import sys

from conftest import TOOLS
import test_fl_spool_row as T

sys.path.insert(0, TOOLS)
from build_helpers import text_px  # noqa: E402
import layout_tokens as lay  # noqa: E402


def _eval(expr, width, inset=0):
    rank = 4 if width >= 1600 else 3 if width >= 1024 else 2
    py = (expr.replace("App.Width", str(width)).replace("LayoutRank", str(rank))
          .replace("PanelInset", str(inset)))
    return eval(py, {"If": lambda c, a, b: a if c else b, "Max": max, "Min": min,
                     "RoundDown": lambda x, _d: math.floor(x),
                     "True": True, "False": False})


def test_fl_and_description_fit_their_content_at_1080p():
    p = T._parts()
    # Feltets kant og padding (Fluent medium: 1 + 10 + 2 px i hver side).
    chrome = 2 * (1 + 10 + 2)
    assert p.FL_SAMPLE == "SSV13 HFC10AP001 -M01"
    assert len(p.DESC_SAMPLE) == 40
    assert p.FL_MAX >= text_px(p.FL_SAMPLE, lay.SIZE_INPUT, semibold=False) + chrome
    assert p.DESC_MAX >= text_px(p.DESC_SAMPLE, lay.SIZE_INPUT, semibold=False) + chrome
    # Mindst loftet - over det gaar resten af kortet ogsaa til dem (#490).
    assert _eval(p.V_FL_W, 1920) >= p.FL_MAX
    assert _eval(p.V_DESC_W, 1920) >= p.DESC_MAX
    # Ingen vandret scroll i Rows eller Classes.
    assert not _eval(p.V_WIDE, 1920)
    assert _eval(p.C_W, 1920) <= _eval(p.ROWS_W, 1920)


def test_compact_columns_and_shared_widths():
    p = T._parts()
    # Class er saa bred som det laengste klassenavn - ikke de gamle 96 px.
    assert p.CLS_W < 96
    assert p.CLS_W >= text_px("NO CLASS", 13)
    # Kun FL og Description vokser; resten er faste tal.
    for n, _l, w in p.V_FIXED:
        assert isinstance(w, int), n
    # Rows' og Classes' FL og Description har samme udtryk.
    for n in ("Fl", "Desc"):
        assert T._prop(f"txtFlRowsHead{n}", "Width") == T._prop(f"txtFlClsHead{n}", "Width"), n
    assert T._prop("inpFlRowFl", "Width") == T._prop("txtFlCFl", "Width")
    assert T._prop("inpFlRowDesc", "Width") == T._prop("txtFlCDesc", "Width")


def test_widths_are_responsive_and_fl_comes_first():
    p = T._parts()
    prev = (0, 0)
    for w in (1366, 1536, 1600, 1650, 1700, 1800, 1920, 2560):
        fl, desc = _eval(p.V_FL_W, w), _eval(p.V_DESC_W, w)
        assert p.FL_MIN <= fl and p.DESC_MIN <= desc, w
        assert fl >= prev[0] and desc >= prev[1], w
        # Description vokser foerst, naar FL har hele sin bredde.
        if desc > p.DESC_MIN:
            assert fl >= p.FL_MAX, w
        # FL vokser kun over loftet, naar Description har sit (#490).
        if fl > p.FL_MAX:
            assert desc >= p.DESC_MAX, w
        # Naar tabellen kan staa i kortet, scroller den ikke.
        if _eval(p.ROWS_W, w) >= _eval(p.V_MIN, w):
            assert not _eval(p.V_WIDE, w), w
        prev = (fl, desc)
