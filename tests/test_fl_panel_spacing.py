# -*- coding: utf-8 -*-
"""
Functional Location-sidepanelet: mindre luft mellem sektionerne (issue #347).

  - Een sektionsafstand i hele panelet - med og uden "Show all fields"
    (samme container, samme LayoutGap).
  - Afstanden MELLEM felterne (feltgitrenes TemplateSize) er uaendret.
  - Bundbjaelken staar stadig fast uden for det, der scroller.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_panel_spacing.py
"""
import test_fl_spool_row as T

SECTIONS = ("Main", "Class", "Loc", "Mfr", "War", "TRM")


def test_one_compact_gap_between_sections():
    assert T._prop("conFlEditorSections", "LayoutGap") == "4"
    for key in SECTIONS:
        assert T._prop(f"conFlPanel{key}", "LayoutGap") == "4", key


def test_field_spacing_and_footer_unchanged():
    for key in SECTIONS + ("Kks",):
        assert T._prop(f"galFlPanel{key}Fields", "TemplateSize") == "86", key
    assert "conFlEditorFooter" not in T._children("conFlEditorSections")
    assert T._children("conFlEditorPanel")[-1] == "conFlEditorFooter"
