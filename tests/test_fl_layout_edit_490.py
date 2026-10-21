# -*- coding: utf-8 -*-
"""
Issue #490: Functional Location - fuld bredde, Description med store
bogstaver og Edit som blyant.

  - Rows og Classes fylder kortet, naar der er plads; resten gaar til FL og
    Description, og de kompakte kolonner er uaendrede.
  - Classes' Actions staar lige under Rows' Actions, og Classes scroller
    kun vandret, naar det er noedvendigt.
  - Description gemmes med store bogstaver (raekken, sidepanelet, Paste
    rows og valideringen, som ogsaa retter hentede anmodninger).
  - Edit i Classes er en ikonknap med blyanten, som Rows' Copy.

    python3 -m pytest tests/test_fl_layout_edit_490.py
"""
import test_fl_spool_row as T
from test_fl_columns_1080p import _eval

WIDTHS = (1280, 1366, 1536, 1600, 1920, 2560, 3440)


def test_both_tables_fill_the_card_when_they_fit():
    p = T._parts()
    for w in WIDTHS:
        rows_w = _eval(p.ROWS_W, w)
        v_w, c_w = _eval(p.V_W, w), _eval(p.C_W, w)
        if rows_w >= _eval(p.V_MIN, w):
            assert v_w == rows_w, w
            assert c_w == rows_w, w
            assert not _eval(p.V_WIDE, w), w
        else:
            # Classes er smallere end Rows og scroller kun, naar den skal.
            assert c_w <= max(rows_w, _eval(p.C_BASE_W, w) + p.VGAP), w


def test_extra_width_goes_to_fl_and_description():
    p = T._parts()
    fl, desc = _eval(p.V_FL_W, 3440), _eval(p.V_DESC_W, 3440)
    assert fl > p.FL_MAX and desc > p.DESC_MAX
    assert desc > fl
    for _n, _l, w in p.V_FIXED:
        assert isinstance(w, int)
    # 1080p: kun lidt mere til FL og Description.
    assert _eval(p.V_FL_W, 1920) - p.FL_MAX < 40
    assert _eval(p.V_DESC_W, 1920) - p.DESC_MAX < 60


def test_classes_actions_align_with_rows_actions():
    p = T._parts()
    for w in (1600, 1920, 2560):
        # Venstre kant af Actions = tabellens bredde minus Actions.
        assert _eval(p.C_W, w) == _eval(p.V_W, w), w
    assert p.C_SPEC[-1][2] == p.ACT_W
    # Den udfladede raekke: blyanten har samme X-led som Rows' Copy, naar
    # Gap har hele sin bredde.
    x = _eval(T._prop("btnFlCOpen", "X"), 1920)
    assert x == _eval(T._prop("btnFlRowCopy", "X"), 1920)


def test_description_is_uppercase():
    assert "Upper(Trim(Self.Text))" in T._prop("inpFlRowDesc", "OnChange")
    # Sidepanelets felter skriver via set_val_fx.
    assert "Description: Upper(nv)" in T._parts().set_val_fx("g", '"DESCRIPTION"', "x")
    assert "Description: Upper(Trim(" in T._prop("btnFlPasteAdd", "OnSelect")
    # Valideringen skriver Description tilbage - ogsaa for hentede anmodninger.
    assert "d: Upper(Trim(R.Description))" in T._text()


def test_edit_is_a_pencil_icon_button():
    b = "btnFlCOpen"
    assert T._prop(b, "Icon") == '"Edit"'
    assert T._prop(b, "Layout") == "ButtonLayout.IconOnly"
    assert T._prop(b, "Width") == T._prop("btnFlRowCopy", "Width")
    assert T._prop(b, "Height") == T._prop("btnFlRowCopy", "Height")
    assert T._prop(b, "Appearance") == T._prop("btnFlRowCopy", "Appearance")
    assert T._prop(b, "Tooltip").startswith('With(')
    assert '"Edit class data of "' in T._prop(b, "Tooltip")
    assert '"Edit class data of "' in T._prop(b, "AccessibleLabel")
    assert T._prop("txtFlClsHeadOpen", "Text") == '"Actions"'
