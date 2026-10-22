# -*- coding: utf-8 -*-
"""
Issue #532: lidt mere luft mellem de kompakte faelles kolonner i Rows og
Classes (StrIndicator, Class, Room, Sort field, ABC indicator, ATEX).

  - Hver af de seks kolonner er COL_AIR (6) px bredere - laast her.
  - Rows og Classes har samme bredder og samme X for de faelles celler.
  - Ved 1920 (1080p) kan FL stadig vise den laengste FL og Description 40
    tegn, og ingen tabel scroller vandret.

Issue #533: Classes' blyant kun naar der kan rettes.

  - I View (eller indsendt) er knappen et View-ikon (DocumentText, som
    appen allerede bruger) med tooltippet "View class data ...".
  - Knappen aabner det samme panel og skifter ikke tilstand.

    python3 -m pytest tests/test_fl_classes_532_533.py
"""
import test_fl_spool_row as T
from test_fl_columns_1080p import _eval

LOCKED = 'varFlViewOnly || varFlStatus = "Indsendt"'

# Raekkens celle i Rows og den tilsvarende i Classes.
PAIRS = [("txtFlRowKks", "txtFlCStr"), ("txtFlRowCls", "txtFlCCls"),
         ("inpFlRowRoom", "txtFlCRoom"), ("inpFlRowSort", "txtFlCSort"),
         ("txtFlRowAbc", "txtFlCAbc"), ("chkFlRowAtex", "txtFlCAtex")]


def test_compact_shared_columns_have_a_little_more_air():
    p = T._parts()
    assert p.COL_AIR == 6
    widths = {n: w for n, _l, w in p.V_SHARED}
    assert widths == {"Kks": 76 + 6, "Cls": p.CLS_W + 6, "Room": 56 + 6, "Sort": 72 + 6,
                      "Abc": 88 + 6, "Atex": 40 + 6}
    # Overskrifterne: de samme bredder i Rows og Classes.
    for n, w in widths.items():
        assert T._prop(f"txtFlRowsHead{n}", "Width") == str(w), n
        assert T._prop(f"txtFlClsHead{n}", "Width") == str(w), n


def test_shared_cells_line_up_between_rows_and_classes():
    for w in (1366, 1600, 1920, 2560):
        for r, c in PAIRS:
            assert _eval(T._desk_all(T._prop(r, "Width")), w) == \
                _eval(T._desk_all(T._prop(c, "Width")), w), (r, c, w)
            assert _eval(T._desk_all(T._prop(r, "X")), w) == \
                _eval(T._desk_all(T._prop(c, "X")), w), (r, c, w)


def test_fl_and_description_still_fit_at_1080p():
    p = T._parts()
    assert _eval(p.V_FL_W, 1920) >= p.FL_MAX
    assert _eval(p.V_DESC_W, 1920) >= p.DESC_MAX
    assert not _eval(p.V_WIDE, 1920)
    assert _eval(p.C_W, 1920) <= _eval(p.ROWS_W, 1920)
    # Raekkehoejden er uaendret (ROW_H, issue #468).
    assert p.ROW_H == 44
    assert T._prop("galFlRows", "TemplateSize") == T._prop("galFlClassRows", "TemplateSize")


def test_classes_pencil_only_when_editing_is_allowed():
    b = "btnFlCOpen"
    assert T._prop(b, "Icon") == f'If({LOCKED}, "DocumentText", "Edit")'
    # DocumentText er et ikon, appen allerede bruger (Long text).
    assert T._parts().icons.FLUENT["long_text"] == "DocumentText"
    verb = f'If({LOCKED}, "View", "Edit")'
    assert T._prop(b, "Tooltip").startswith(f'With({{ m: ')
    assert f'{verb} & " class data of "' in T._prop(b, "Tooltip")
    assert f'{verb} & " class data of "' in T._prop(b, "AccessibleLabel")


def test_view_icon_opens_the_panel_without_switching_mode():
    on = T._prop("btnFlCOpen", "OnSelect")
    assert "Set(varFlPanelOpen, true)" in on
    assert "varFlViewOnly" not in on
    # Altid klikbar - ogsaa i View, hvor panelet kun er til at laese.
    assert "DisplayMode" not in T._ctrl("btnFlCOpen")["Properties"]
    note = T._prop("txtFlClassNote", "Text")
    assert "the view icon opens" in note and "Edit pencil" in note
