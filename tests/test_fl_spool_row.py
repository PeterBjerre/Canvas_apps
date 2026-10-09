# -*- coding: utf-8 -*-
"""
Functional Location: raekken uden fold-ud (issue #232).

Raekken har efter Sort Field praecis kolonnerne
ABC Indicator | ATEX | Class Data | Manufacturer | Warranty | Actions,
Validation-kolonnen er vaek (beskeden staar under raekkens felter), og
popup-knapperne har Long Text-knappens udfyldt-tilstand (mark_done).

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_spool_row.py
"""
import os
import sys

from conftest import ROOT, TOOLS

sys.path.insert(0, TOOLS)
from build_helpers import mark_done, button  # noqa: E402
from gen_screen import C_BORDER_OK, C_CARD_BORDER, C_VALID_FG, C_TITLE  # noqa: E402

FL = os.path.join(ROOT, "BIO SAP App", "ScreenFunctionalLocation.pa.yaml")
APP = os.path.join(ROOT, "Functional Location App", "App.pa.yaml")
BUILD = os.path.join(ROOT, "Functional Location App", "build")


def _text(path=FL):
    return open(path, encoding="utf-8").read()


def _find(node, ctrl):
    if isinstance(node, dict):
        if ctrl in node and isinstance(node[ctrl], dict) and "Control" in node[ctrl]:
            return node[ctrl]
        node = list(node.values())
    if isinstance(node, list):
        for x in node:
            hit = _find(x, ctrl)
            if hit is not None:
                return hit
    return None


_TREE = {}


def _ctrl(ctrl):
    import yaml
    if FL not in _TREE:
        _TREE[FL] = yaml.safe_load(_text())
    return _find(_TREE[FL], ctrl)


def _prop(ctrl, prop):
    hit = _ctrl(ctrl)
    assert hit is not None, ctrl
    return str(hit["Properties"][prop]).lstrip("=")


def _children(ctrl):
    return [list(c)[0] for c in _ctrl(ctrl).get("Children", [])]


def _parts():
    if BUILD not in sys.path:
        sys.path.insert(0, BUILD)
    import fl_parts
    return fl_parts


def test_header_order_after_sort_field():
    heads = [_prop(n, "Text").strip('"') for n in _children("conFlRowsHead")]
    assert heads == ["#", "Functional Location", "Description", "KKS Type", "Assigned Class",
                     "Room", "Sort Field", "ABC Indicator", "ATEX", "Class Data",
                     "Manufacturer", "Warranty", "Actions"]


def test_row_cells_follow_the_header():
    """Raekkens celler (efter udfoldningen i galleriet) i samme raekkefoelge."""
    kids = _children("galFlRows")
    cells = ["txtFlRowNo", "inpFlRowFl", "inpFlRowDesc", "txtFlRowKks", "txtFlRowCls",
             "inpFlRowRoom", "inpFlRowSort", "txtFlRowAbc", "chkFlRowAtex",
             "btnFlRowClassData", "btnFlRowMfr", "btnFlRowWar", "btnFlRowDelete"]
    assert [k for k in kids if k in cells] == cells
    # Ingen Warranty Start/End-kolonner og ingen Validation-kolonne.
    assert "inpFlRowWStart" not in kids and "inpFlRowWEnd" not in kids
    assert "conFlRowsHeadVal" not in _text() and '"Validation rows"' not in _text()


def test_fold_out_is_gone():
    y = _text()
    for gone in ("varFlFoldOpen", "galFlRowsB", "conFlFold", "btnFlRowFold", "btnFlClassData",
                 "galFlMFields", "Expand row", "Collapse row", "Expand or collapse"):
        assert gone not in y, gone
    assert "varFlFoldOpen" not in _text(APP)


def test_abc_is_read_only_and_atex_is_a_checkbox():
    assert "ABC INDIC." in _prop("txtFlRowAbc", "Text")
    assert _ctrl("txtFlRowAbc")["Control"] == "ModernText"
    # Den automatiske beregning er uroert (FL48/FL49).
    assert ('Collect(colFlVals, ForAll(Filter(colFlTrm, AnyTrm) As T, '
            '{ RowGuid: T.RowGuid, Field: "ABC INDIC.", Value: "A" }))') in _text()
    chk = _ctrl("chkFlRowAtex")
    assert chk["Control"] == "ModernCheckbox"
    assert 'Field = "ATEX"' in _prop("chkFlRowAtex", "Default")
    assert '{ f: "ATEX", nv: Trim("X") }' in _prop("chkFlRowAtex", "OnCheck")
    assert '{ f: "ATEX", nv: Trim("") }' in _prop("chkFlRowAtex", "OnUncheck")
    assert "Select(btnFlVerify)" in _prop("chkFlRowAtex", "OnCheck")


def test_popup_buttons_use_the_long_text_indicator():
    """Samme mark_done som VH-planens Long text: groen kant og tekst ved data."""
    for name in ("btnFlRowClassData", "btnFlRowMfr", "btnFlRowWar"):
        border = _prop(name, "BorderColor")
        color = _prop(name, "Color")
        assert border.startswith("If(") and "C.'border-ok'" in border, name
        assert "C.'border-default'" in border and "C.'state-ok-fg'" in color, name
        assert _prop(name, "BorderThickness") == "1", name
        # Data, ikke gyldighed: udtrykket laeser vaerdierne, ikke Status/fejl.
        assert "colFlVals" in border and "colFlIssues" not in border and "Status" not in border
    # Byggeklodsen er den faelles - samme formel som paa Long text.
    b = mark_done(button("x", '"x"', "true"), "D")
    assert b.props["BorderColor"] == f"If(D, {C_BORDER_OK}, {C_CARD_BORDER})"
    assert b.props["Color"] == f"If(D, {C_VALID_FG}, {C_TITLE})"


def test_indicator_fields():
    mfr = _prop("btnFlRowMfr", "BorderColor")
    for f in ("MANUFACTURER", "MODEL NUMBER", "MANUFACTURER PART NUMBER",
              "MANUFACTURER SERIAL NUMBER"):
        assert f'"{f}"' in mfr
    war = _prop("btnFlRowWar", "BorderColor")
    assert '"WARRANTY START"' in war and '"WARRANTY END"' in war
    cls = _prop("btnFlRowClassData", "BorderColor")
    assert 'Section in ["Class", "TRM", "Ext"]' in cls and "ThisItem.AssignedClass" in cls


def test_disabled_states_and_permissions():
    # Class data: kun med klasse (som foer).
    assert _prop("btnFlRowClassData", "DisplayMode") == (
        "If(!IsBlank(ThisItem.AssignedClass), DisplayMode.Edit, DisplayMode.Disabled)")
    # Manufacturer/Warranty: laast og tom = deaktiveret (Long text-moenstret).
    for name in ("btnFlRowMfr", "btnFlRowWar"):
        dm = _prop(name, "DisplayMode")
        assert dm.startswith('If((varFlViewOnly || varFlStatus = "Indsendt") && !(')
        assert "DisplayMode.Disabled, DisplayMode.Edit" in dm
    # Felterne i popuppen og i raekken foelger View/Edit.
    for name in ("inpFlPopVal", "chkFlRowAtex", "inpFlRowRoom", "inpFlRowSort"):
        assert "varFlViewOnly" in _prop(name, "DisplayMode"), name


def test_manufacturer_and_warranty_popup():
    p = _parts()
    assert p.POP_KINDS == {
        "Manufacturer": ["MANUFACTURER", "MODEL NUMBER", "MANUFACTURER PART NUMBER",
                         "MANUFACTURER SERIAL NUMBER"],
        "Warranty": ["WARRANTY START", "WARRANTY END"]}
    # Gendannes ved hver aabning: felterne regnes af raekkens gemte vaerdier.
    for name, kind in (("btnFlRowMfr", "Manufacturer"), ("btnFlRowWar", "Warranty")):
        on = _prop(name, "OnSelect")
        assert on.startswith("Set(varFlDetailRow, ThisItem.RowGuid);\nClearCollect(colFlDet, ")
        assert on.endswith(f'Set(varFlPop, "{kind}")')
    # Felterne skriver i raekken og validerer (roed/groen kant + besked).
    assert "Select(btnFlVerify)" in _prop("inpFlPopVal", "OnChange")
    assert "ThisItem.Issue" in _prop("inpFlPopVal", "BorderColor")
    assert "ThisItem.Issue" in _prop("txtFlPopIssue", "Text")
    assert "DD.MM.YYYY" in _prop("inpFlPopVal", "Placeholder")


def test_popup_closes_only_with_close():
    assert _prop("btnFlPopClose", "OnSelect") == 'Set(varFlPop, "")'
    assert _prop("btnFlPopClose", "Text") == '"Close"'
    assert "varFlPop" not in _prop("conFlPopBackdrop", "OnSelect")
    assert _prop("conFlPopModal", "Visible") == "IfError(!IsBlank(varFlPop), false)"
    # Ny anmodning lukker den.
    assert 'Set(varFlPop, "");' in _prop("btnFlNew", "OnSelect")


def test_validation_message_under_the_row():
    txt = _prop("txtFlRowIssue", "Text")
    assert '"valid", "Valid"' in txt and "ThisItem.FirstIssue" in txt
    color = _prop("txtFlRowIssue", "Color")
    assert "C.'state-error-fg'" in color and "C.'state-ok-fg'" in color
    assert _prop("txtFlRowIssue", "AccessibleLabel") == '"Row " & ThisItem.Pos & ": " & Self.Text'
    assert "ThisItem.Hint" in _prop("btnFlRowHint", "OnSelect")
    # Roede/groenne kanter paa de relevante felter.
    assert "ThisItem.FlBad" in _prop("inpFlRowFl", "BorderColor")
    assert "ThisItem.DescBad" in _prop("inpFlRowDesc", "BorderColor")
    for n, f in (("inpFlRowRoom", "ROOM"), ("inpFlRowSort", "SORT FIELD")):
        bc = _prop(n, "BorderColor")
        assert f'Field = "{f}"' in bc and "C.'border-error'" in bc and "C.'border-ok'" in bc
    # Raekken er hoejere, naar der er beskeder at vise.
    assert _prop("galFlRows", "TemplateSize") == (
        'If(IfError(!IsEmpty(Filter(colFlRows, Status <> "draft")), false), 70, 44)')


def test_table_scrolls_sideways_instead_of_hiding_columns():
    assert _prop("conFlTable", "LayoutOverflowX") == "LayoutOverflow.Scroll"
    assert _prop("conFlTable", "LayoutAlignItems") == "LayoutAlignItems.Start"
    # Ingen kolonne i raekken skjules af skaermbredden - kun # under Tablet.
    for n in ("txtFlRowsHeadKks", "txtFlRowsHeadRoom", "txtFlRowsHeadWar", "txtFlRowsHeadAbc"):
        assert "Visible" not in _ctrl(n)["Properties"], n


def test_classes_edit_opens_class_data():
    on = _prop("btnFlCOpen", "OnSelect")
    assert on.startswith("Set(varFlClsRow, ThisItem.RowGuid);")
    assert on.endswith("Set(varFlClsOpen, true)")
