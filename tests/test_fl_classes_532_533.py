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


# ---------------------------------------------------------------------------
# Issue #533 (udvidet): Classes klappet sammen, opsummering og gem
# ---------------------------------------------------------------------------
OPEN = "Coalesce(varFlClassesOpen, false)"


def _yaml():
    return T._text()


def test_classes_fold_on_every_screen_width_closed_by_default():
    # Chevronlinjen ses overalt - ikke kun paa telefonen.
    assert "Visible" not in T._ctrl("conFlClassesFold")["Properties"]
    assert "Visible" not in T._ctrl("btnFlClassesFold")["Properties"]
    assert T._prop("btnFlClassesFold", "OnSelect") == f"Set(varFlClassesOpen, !{OPEN})"
    # Den gamle titel kun fra Tablet er vaek - titlen staar i chevronlinjen.
    assert T._ctrl("txtFlClassesH") is None
    # Indholdet kun, mens Classes er aaben - paa alle bredder (blank =
    # lukket). Issue #559: det ligger i kroppen (conFlClassesBody), og det
    # er kroppen, der foelger chevronen.
    vis = str(T._ctrl("conFlClassesBody")["Properties"]["Visible"])
    assert vis.lstrip("=") == OPEN
    for c in ("galFlTabs", "txtFlClassNote", "conFlClsTable", "txtFlNoClassRows"):
        vis = str(T._ctrl(c)["Properties"]["Visible"])
        assert OPEN not in vis, c
        assert "LayoutRank" not in vis, c


def test_classes_summary_counts_rows_and_classes():
    p = T._parts()
    # Issue #559: opsummeringen staar ved titlen, lukket og aaben.
    assert "Visible" not in T._ctrl("txtFlClassesFoldSummary")["Properties"]
    text = T._prop("txtFlClassesFoldSummary", "Text")
    # Tomme raekker (den nederst) taeller ikke; klasserne er Classes' egne.
    assert "CountRows(Filter(colFlRows, !(IsBlank(FL) && IsBlank(Description))))" in text
    assert f"CountRows(Distinct({p.V.BUCKETS}, AssignedClass))" in text
    assert '" Functional Location", " Functional Locations"' in text
    assert '" class", " classes"' in text


def test_open_state_survives_edits_filters_and_saves():
    p, s = T._parts(), T._parts().S
    # Kun chevronen, en ny anmodning og en anden anmodning saetter den.
    assert "varFlClassesOpen" not in s.save_fx() + s.submit_fx()
    assert "varFlClassesOpen" not in T._prop("btnFlTab", "OnSelect")
    for fx in (p.set_row_fx("g", "FL", "x"), p.set_val_fx("g", '"ROOM"', "x"),
               p.delete_row_fx("g"), p.copy_row_fx("g"), p.capped_add_row_fx()):
        assert "varFlClassesOpen" not in fx
    assert "Set(varFlClassesOpen, false)" in p.RESET_FX
    assert "Set(varFlClassesOpen, false)" in s.load_fx()


def test_deleting_a_row_removes_its_classes_entry():
    # Classes er en visning af colFlRows (V.BUCKETS) - ingen egen kopi.
    items = T._prop("galFlClassRows", "Items")
    assert "Filter(colFlRows, " in items
    assert "Remove(colFlRows, LookUp(colFlRows, RowGuid = g))" in T._parts().delete_row_fx("g")


def test_unsaved_changes_are_tracked_and_cleared_by_a_save():
    p, s = T._parts(), T._parts().S
    # Kun naar vaerdien faktisk aendres.
    assert ('If(Coalesce(LookUp(colFlRows, RowGuid = g).FL, "") <> Coalesce(nv, ""), '
            'Set(varFlDirty, true))') in p.set_row_fx("g", "FL", "x")
    assert "Set(varFlDirty, true)" in p.set_val_fx("g", '"ROOM"', "x")
    for fx in (p.delete_row_fx("g"), p.copy_row_fx("g"), p._paste_add_fx()):
        assert "Set(varFlDirty, true)" in fx
    # En tom raekke gemmes ikke - den goer intet ugemt.
    assert "varFlDirty" not in p.capped_add_row_fx() + p.AUTO_ROW_FX
    # Et gem nulstiller den - kun naar det lykkedes; et fejlet gem beholder
    # baade vaerdierne og markeringen.
    save = s.save_fx()
    ok, failed = save.split("Set(varFlInfo, \"Saving failed")
    assert "Set(varFlDirty, false)" in ok.rsplit("CountRows(colFlSaveErrors) = 0,", 1)[1]
    assert "varFlDirty" not in failed
    # Ny og hentet anmodning: intet ugemt.
    assert "Set(varFlDirty, false)" in p.RESET_FX and "Set(varFlDirty, false)" in s.load_fx()
    # Cancel/Reset i panelet: tilbage til tilstanden, da panelet blev aabnet.
    assert "Set(varFlDirtyAtOpen, Coalesce(varFlDirty, false))" in p.open_row_panel_fx("g")
    assert "Set(varFlDirty, Coalesce(varFlDirtyAtOpen, true))" in p.PANEL_RESTORE


def test_unsaved_changes_are_visible():
    unsaved = '(Coalesce(varFlDirty, false) && !varFlViewOnly && varFlStatus <> "Indsendt")'
    assert T._prop("txtFlUnsaved", "Text") == '"Unsaved changes"'
    assert unsaved in T._prop("txtFlUnsaved", "Visible")
    # Under Desktop: i Rows' taeller (ogsaa paa telefonen).
    assert f'If({unsaved}, "  ·  Unsaved changes", "")' in T._prop("txtFlRowsCount", "Text")
    assert T._prop("btnFlSaveDraft", "Tooltip").startswith(f'If({unsaved}, "Unsaved changes. "')


def test_panel_save_is_the_same_save_and_submit_saves_too():
    p, s = T._parts(), T._parts().S
    # Panelets Save er det fulde gem (samme som Save draft) - ikke kun lokalt.
    assert s.save_fx() in p.PANEL_SAVE_FX
    assert s.save_fx() in p.SAVE_DRAFT_FX
    assert "same as Save draft" in T._prop("btnFlEditorSave", "Tooltip")
    # Submit gemmer og indsender i een handling - Save draft foerst kraeves ikke.
    assert s.save_fx(notify=False).replace("\n", "\n    ") in s.submit_fx()
    assert "varFlDirty" not in s.SUBMIT_OK
    assert "saved and submitted in one step" in _yaml()
