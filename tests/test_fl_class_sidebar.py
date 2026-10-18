# -*- coding: utf-8 -*-
"""
Functional Location: Edit i Classes aabner raekkens sidepanel (issue #346).

  - Edit (Classes) og Class data (Rows) aabner SAMME panel for netop den
    raekke, med klassens felter (Class characteristics og TRM) foerst; de
    andre sektioner er foldet sammen bag "Show all fields".
  - Manufacturer/Warranty aabner stadig ved deres sektion.
  - Den gamle Class data-popup er vaek; der er intet eget klassepanel.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_class_sidebar.py
"""
import test_fl_spool_row as T


def _opens(btn, jump):
    on = T._prop(btn, "OnSelect")
    assert on.startswith(f'Set(varFlDetailRow, ThisItem.RowGuid);\nSet(varFlPanelJump, {jump});'), btn
    # Samme aabning som panelets egne knapper: felter, aftryk, aaben.
    assert "ClearCollect(colFlDet," in on and "ClearCollect(colFlPanelSnap," in on, btn
    assert on.endswith("Set(varFlPanelOpen, true)"), btn


def test_edit_and_class_data_open_the_row_sidebar_with_class_fields():
    _opens("btnFlCOpen", '"Class"')
    _opens("btnFlRowClassData", '"Class"')
    _opens("btnFlRowMfr", '"Mfr"')
    _opens("btnFlRowWar", '"War"')
    for key in ("Main", "Loc", "Mfr", "War"):
        assert '"Class"]' in T._prop(f"conFlPanel{key}", "Visible"), key
    for key in ("Class", "TRM"):
        assert '"Class"]' not in T._prop(f"conFlPanel{key}", "Visible"), key


def test_show_all_fields_and_empty_class():
    assert T._prop("btnFlPanelShowAll", "OnSelect") == 'Set(varFlPanelJump, "")'
    assert T._prop("btnFlPanelShowAll", "Visible") == '!IsBlank(IfError(varFlPanelJump, ""))'
    none = T._prop("txtFlPanelClsNone", "Visible")
    assert 'IfError(varFlPanelJump, "") = "Class"' in none
    assert 'Pane in ["Class", "TRM"]' in none
    assert T._children("conFlEditorSections")[-1] == "txtFlPanelClsNone"


def test_no_separate_class_popup_or_panel():
    top = T._screen_children()
    assert [n for n in top if "Editor" in n and n.startswith("con")] == ["conFlEditorPanel"]
    assert not [n for n in top if n.startswith(("conFlCls", "imgFlCls"))]
