# -*- coding: utf-8 -*-
"""Issue #559: Classes-overskriften staar altid oeverst, og Plan headers
resume staar i overskriften.

- FL Classes: kortet har to boern i fast raekkefoelge - overskriften og
  kroppen. Faner, note, tabel og "No classified rows yet ..." ligger i
  kroppen, under overskriften. Opsummeringen ses aaben og lukket.
- VH Plan header: resumeet lige efter "Plan header" i samme raekke, Total
  cost og chevron til hoejre. Ingen ekstra resume-raekke fra Tablet og op;
  paa en telefon staar resumeet paa sin egen linje.

    python3 -m pytest tests/test_fold_header_order_559.py
"""
from test_expand_collapse_548 import FL, VHP, FOLD, _read, _block, _prop, _children, _own

OPEN = "Coalesce(varFlClassesOpen, false)"


def test_classes_header_is_the_first_child_and_the_body_holds_the_rest():
    t = _read(FL)
    card = _block(t, "conFlClassesCard")
    assert _children(card) == ["conFlClassesFoldHead", "conFlClassesBody"]
    body = _block(t, "conFlClassesBody")
    assert "LayoutDirection.Vertical" in _own(body)
    assert _children(body) == ["galFlTabs", "txtFlClassNote", "conFlClsTable", "txtFlNoClassRows"]
    assert _prop(_own(body), "Visible") == OPEN
    # Overskriften folder aldrig selv bort.
    assert _prop(_own(_block(t, "conFlClassesFoldHead")), "Visible") is None


def test_classes_empty_text_sits_in_the_body():
    t = _read(FL)
    empty = _block(t, "txtFlNoClassRows")
    assert ("No classified rows yet - a row appears here once its Functional Location "
            "is valid.") in _prop(empty, "Text")
    # Kroppens hoejde: faner/note/tabel ELLER den tomme linje - aldrig begge.
    h = _prop(_own(_block(t, "conFlClassesBody")), "Height")
    assert h.startswith("If(IfError(CountRows(") and h.endswith(", 20)")


def test_classes_summary_stays_beside_the_title_when_open():
    t = _read(FL)
    row = _block(t, "conFlClassesFold")
    assert _children(row) == ["txtFlClassesFoldTitle", "txtFlClassesFoldSummary", "btnFlClassesFold"]
    assert _prop(_block(t, "txtFlClassesFoldSummary"), "Visible") is None
    assert "LayoutJustifyContent.SpaceBetween" in _own(row)


def test_plan_summary_is_in_the_header_row_after_the_title():
    t = _read(VHP)
    head = _block(t, "conVhpPlanHead")
    kids = _children(head)
    assert kids.index("txtVhpPlanHeadTitle") < kids.index("txtVhpPlanFoldSummary")
    assert kids[-2:] == ["bdgVhpPlanHeadCost", "btnVhpPlanFold"]
    assert "conVhpPlanHeadGap" not in kids
    s = _block(t, "txtVhpPlanFoldSummary")
    assert _prop(s, "Wrap") == "true"
    # Teksten fra Tablet og op, kun foldet; mobilgrenen er tom.
    assert _prop(s, "Text").startswith(f"If(!(LayoutRank < 2) && ({FOLD}), ")
    # Raekken - og den klikbare overskrift - er saa hoej som resumeet.
    assert "Len(txtVhpPlanFoldSummary.Text)" in _prop(_own(head), "Height")
    wrap = _prop(_own(_block(t, "conVhpPlanHeadFold")), "Height")
    assert "Len(txtVhpPlanFoldSummary.Text)" in wrap


def test_plan_card_has_no_extra_summary_row_from_tablet_up():
    t = _read(VHP)
    card = _children(_block(t, "conVhpPlanCard"))
    assert card[0] == "conVhpPlanHeadFold"
    assert "txtVhpPlanFoldSummary" not in card
    # Telefonens linje under overskriften (mobilgrenen bevaret).
    assert "txtVhpPlanFoldSummaryM" in card
    m = _block(t, "txtVhpPlanFoldSummaryM")
    assert _prop(m, "Visible") == f"LayoutRank < 2 && ({FOLD})"
    assert _prop(m, "Wrap") == "true"
