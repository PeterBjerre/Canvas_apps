# -*- coding: utf-8 -*-
"""
Functional Location: raekken uden fold-ud (issue #232).

Raekken har Class Data lige efter Assigned Class (issue #242) og efter
Sort Field praecis kolonnerne ABC Indicator | ATEX | Manufacturer |
Warranty | Actions,
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
    # Sentence case (UX-review F1/T7); Functional Location og ATEX er navne.
    assert heads == ["#", "Functional Location", "Description", "KKS type", "Assigned class",
                     "Class data", "Room", "Sort field", "ABC indicator", "ATEX",
                     "Manufacturer", "Warranty", "Status", "Actions"]


def test_row_cells_follow_the_header():
    """Raekkens celler (efter udfoldningen i galleriet) i samme raekkefoelge."""
    kids = _children("galFlRows")
    cells = ["txtFlRowNo", "inpFlRowFl", "inpFlRowDesc", "txtFlRowKks", "txtFlRowCls",
             "btnFlRowClassData", "inpFlRowRoom", "inpFlRowSort", "txtFlRowAbc",
             "chkFlRowAtex", "btnFlRowMfr", "btnFlRowWar", "btnFlRowStatus", "btnFlRowDelete"]
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
    assert 'Section in ["Class", "TRM"]' in cls and "ThisItem.AssignedClass" in cls


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
    for name in ("inpFlPanelMfrVal", "chkFlRowAtex", "inpFlRowRoom", "inpFlRowSort"):
        assert "varFlViewOnly" in _prop(name, "DisplayMode"), name


def test_manufacturer_and_warranty_open_the_side_panel():
    """Issue #278: Manufacturer og Warranty aabner raekkens sidepanel ved
    deres sektion - der er ingen egen popup."""
    p = _parts()
    assert p.MFR_FIELDS == ["MANUFACTURER", "MODEL NUMBER", "MANUFACTURER PART NUMBER",
                            "MANUFACTURER SERIAL NUMBER"]
    assert p.WAR_FIELDS == ["WARRANTY START", "WARRANTY END"]
    for name, jump in (("btnFlRowMfr", "Mfr"), ("btnFlRowWar", "War")):
        on = _prop(name, "OnSelect")
        assert on.startswith("Set(varFlDetailRow, ThisItem.RowGuid);\n"
                             f'Set(varFlPanelJump, "{jump}");')
        assert "ClearCollect(colFlDet, " in on
        assert on.endswith("Set(varFlPanelOpen, true)")
    # Class data aabner panelet med alle sektioner.
    on = _prop("btnFlRowClassData", "OnSelect")
    assert 'Set(varFlPanelJump, "");' in on and on.endswith("Set(varFlPanelOpen, true)")
    # Felterne skriver i raekken og validerer (roed/groen kant + besked).
    assert "Select(btnFlVerify)" in _prop("inpFlPanelMfrVal", "OnChange")
    assert "colFlIssues" in _prop("inpFlPanelMfrVal", "BorderColor")
    assert "colFlIssues" in _prop("txtFlPanelWarIssue", "Text")
    assert "DD.MM.YYYY" in _prop("inpFlPanelWarVal", "Placeholder")
    for gone in ("conFlPopModal", "conFlPopBackdrop", "btnFlPopClose"):
        assert _ctrl(gone) is None, gone
    assert "varFlPop" not in _text()


def test_jump_folds_the_sections_before_it():
    """Aabnet fra Manufacturer: sektionerne foer er foldet sammen bag
    "Show all fields"; fra Warranty ogsaa Manufacturer."""
    for key in ("Main", "Class", "Loc"):
        assert '!(IfError(varFlPanelJump, "") in ["Mfr", "War"])' in _prop(f"conFlPanel{key}", "Visible")
    assert '!(IfError(varFlPanelJump, "") in ["War"])' in _prop("conFlPanelMfr", "Visible")
    for key in ("War", "TRM"):
        assert "varFlPanelJump" not in _prop(f"conFlPanel{key}", "Visible")
    assert _prop("btnFlPanelShowAll", "OnSelect") == 'Set(varFlPanelJump, "")'
    assert _children("conFlEditorSections")[0] == "btnFlPanelShowAll"
    # Ny anmodning lukker panelet.
    new = _prop("btnFlNew", "OnSelect")
    assert "Set(varFlPanelOpen, false);" in new and 'Set(varFlPanelJump, "");' in new


def test_row_status_lives_in_the_status_button_tooltip():
    tip = _prop("btnFlRowStatus", "Tooltip")
    assert '"valid", "Ready for SAP"' in tip and "ThisItem.FirstIssue" in tip
    assert "txtFlRowIssue" not in open(FL, encoding="utf-8").read()
    # Roede/groenne kanter paa de relevante felter.
    assert "ThisItem.FlBad" in _prop("inpFlRowFl", "BorderColor")
    assert "ThisItem.DescBad" in _prop("inpFlRowDesc", "BorderColor")
    for n, f in (("inpFlRowRoom", "ROOM"), ("inpFlRowSort", "SORT FIELD")):
        bc = _prop(n, "BorderColor")
        assert f'Field = "{f}"' in bc and "C.'border-error'" in bc and "C.'border-ok'" in bc
    assert _prop("galFlRows", "TemplateSize") == "44 + (Max(40, H.hit) - 40)"


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


def _screen_children():
    import yaml
    if FL not in _TREE:
        _TREE[FL] = yaml.safe_load(_text())
    scr = list(_TREE[FL]["Screens"].values())[0]
    return [list(c)[0] for c in scr["Children"]]


def test_popups_sit_inside_their_backdrop():
    """Issue #242: sloeret laa oven paa popupperne (graa og uden tryk).
    Popuppen er nu et barn af sloeret, saa den altid tegnes over det, og
    sloeret daemper kun siden under."""
    top = _screen_children()
    for scrim, modal, vis in (
            ("conFlClsBackdrop", "conFlClsModal", "IfError(varFlClsOpen, false)"),):
        assert scrim in top, scrim
        assert modal not in top, modal
        assert _children(scrim) == [modal], scrim
        s = _ctrl(scrim)
        assert s["Control"] == "GroupContainer", scrim
        assert _prop(scrim, "Fill") == "C.'overlay'"
        assert _prop(scrim, "Width") == "App.Width" and _prop(scrim, "Height") == "App.Height"
        assert _prop(scrim, "Visible") == vis
        assert _prop(scrim, "LayoutJustifyContent") == "LayoutJustifyContent.Center"
        # Popuppen styres af sloeret - ingen egen X/Y.
        props = _ctrl(modal)["Properties"]
        assert "X" not in props and "Y" not in props, modal
        assert _prop(modal, "Fill") == "C.'bg-modal'"
    # Issue #278: Class data-popuppen og dens sloer ligger OVER raekkens
    # sidepanel (og sidebaren), saa panelet ikke daekker popuppen og Apply.
    assert top.index("conFlClsBackdrop") > top.index("conFlEditorPanel")
    assert top.index("conFlClsBackdrop") > top.index("conFlNavOpen")
    assert top.index("conFlClsBackdrop") > top.index("conFlRoot")


def test_spare_width_is_shared_by_the_columns():
    """Issue #242: Functional Location og Description faar omtrent den
    halve desktopbredde, og resten af den ekstra plads deles af de andre
    kolonner. Overskrift og raekke har samme bredde pr. kolonne."""
    from fractions import Fraction as F
    p = _parts()
    pair = F(p.V_PAIR_SHARE.replace(" ", ""))
    grow = F(p.V_GROW_SHARE.replace(" ", ""))
    desc_share = F(p.V_DESC_SHARE.replace(" ", ""))
    assert pair + desc_share + len(p.V_GROW) * grow == 1
    # Statuskolonnen er fast bredde; de to foerste felter beholder deres minimum.
    rows = 1920 - 56 - 64 - 36 - 18 - 40
    spare = rows - (34 + p.V_BASE)
    fl = p.FL_MIN + spare * pair
    desc = p.DESC_MIN + spare * desc_share
    assert fl >= p.FL_MIN, fl
    assert desc >= p.DESC_MIN, desc
    # Hver celle i raekken har samme bredde som sin overskrift.
    pairs = (("Fl", "inpFlRowFl"), ("Desc", "inpFlRowDesc"), ("Kks", "txtFlRowKks"),
             ("Cls", "txtFlRowCls"), ("ClsData", "btnFlRowClassData"),
             ("Room", "inpFlRowRoom"), ("Sort", "inpFlRowSort"), ("Abc", "txtFlRowAbc"),
             ("Atex", "chkFlRowAtex"), ("Mfr", "btnFlRowMfr"), ("War", "btnFlRowWar"),
             ("Status", "btnFlRowStatus"), ("Act", "btnFlRowDelete"))
    for head, cell in pairs:
        assert _prop(f"txtFlRowsHead{head}", "Width") == _prop(cell, "Width"), head
    for n in p.V_GROW:
        assert p.V_SPARE in _prop(f"txtFlRowsHead{n}", "Width"), n
    for n in ("Atex", "Act"):
        assert "Max(0" not in _prop(f"txtFlRowsHead{n}", "Width"), n
