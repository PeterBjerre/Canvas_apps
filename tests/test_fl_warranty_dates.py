# -*- coding: utf-8 -*-
"""
Functional Location: Warranty-datovaelgere og Classes' kolonner (issue #356).

  - Warranty Start og Warranty End redigeres i sidepanelet med appens
    datovaelger. Vaerdien gemmes stadig som tekst DD.MM.YYYY i det samme
    felt (colFlVals), saa validering (FL34), gem og SAP-eksport er uaendrede.
  - Classes' #, Functional Location og Description har Rows' bredder og
    mellemrum, saa felterne staar lige under hinanden.

Power Fx kan ikke koeres her, saa testene laeser byggeren og den
GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_warranty_dates.py
"""
import os
import sys

from conftest import ROOT

import test_fl_spool_row as T

BUILD = os.path.join(ROOT, "Functional Location App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import importlib.util  # noqa: E402

# Eget modulnavn: VH-plan-appen har ogsaa et generate_app_onstart, og
# sys.modules maa ikke faa FL's under det navn.
_spec = importlib.util.spec_from_file_location(
    "fl_generate_app_onstart_356", os.path.join(BUILD, "generate_app_onstart.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

BIO_APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
WAR = {"WARRANTY START", "WARRANTY END"}


def test_warranty_fields_are_date_editors():
    assert G.DATE_FIELDS == WAR
    for f in WAR:
        assert G.editor_kind({"Field": f, "Editable": True, "List": ""}) == "date"
    assert G.editor_kind({"Field": "REMARKS", "Editable": True, "List": ""}) == "text"
    app = open(BIO_APP, encoding="utf-8").read()
    for f in WAR:
        assert f'Field: "{f}", Editable: true, List: "", MaxLen: 10, Section: "Master", Kind: "date"' in app, f


def test_panel_has_a_date_picker_in_dd_mm_yyyy():
    name = "dteFlPanelWarVal"
    assert T._ctrl(name)["Control"] == "ModernDatePicker"
    assert T._prop(name, "Format") == '"dd.mm.yyyy"'
    assert T._prop(name, "Placeholder") == '"dd.mm.yyyy"'
    assert T._prop(name, "Visible") == 'ThisItem.Kind = "date"'
    # Tekstfeltet staar kun for tekstfelterne - ikke ogsaa for datoerne.
    assert T._prop("inpFlPanelWarVal", "Visible") == 'ThisItem.Kind = "text"'
    # Den gemte tekst laeses som dato; tom eller ugyldig = ingen dato.
    dflt = T._prop(name, "DefaultDate")
    assert "LookUp(colFlVals, RowGuid = varFlDetailRow && Field = ThisItem.Field).Value" in dflt
    assert "Blank()" in dflt
    assert "Date(Value(Right(wv, 4)), Value(Mid(wv, 4, 2)), Value(Left(wv, 2)))" in dflt
    # ... og skrives tilbage som DD.MM.YYYY i samme felt, tom ved ingen dato.
    chg = T._prop(name, "OnChange")
    assert ('If(IsBlank(Self.SelectedDate), "", Text(Day(Self.SelectedDate), "00") & "." & '
            'Text(Month(Self.SelectedDate), "00") & "." & Text(Year(Self.SelectedDate), "0000"))') in chg
    assert "Collect(colFlVals, { RowGuid: varFlDetailRow, Field: f, Value: nv })" in chg
    # Samme kantregel som de andre felter i panelet.
    assert T._prop(name, "BorderColor") == T._prop("inpFlPanelWarVal", "BorderColor")


def test_text_of_date_matches_the_validated_format():
    """Den tekst, vaelgeren skriver, skal bestaa FL34 (date_bad): to cifre,
    punktum, to cifre, punktum, fire cifre."""
    p = T._parts()
    assert p.FL_DATE_FMT == "dd.mm.yyyy"
    assert '"[0-9]{2}\\.[0-9]{2}\\.[0-9]{4}"' in p.date_of_text("x")


def test_classes_reuse_the_rows_column_widths():
    p = T._parts()
    rows = {n: w for n, _l, w, _v in p.V_SPEC}
    cls = {n: w for n, _l, w, _v in p.C_SPEC}
    for n in ("No", "Fl", "Desc"):
        assert cls[n] == rows[n], n
    assert [n for n, *_ in p.C_SPEC][:3] == ["No", "Fl", "Desc"]
    # Genereret: overskrifter, celler og mellemrum flugter med Rows.
    for n, cell in (("Fl", "inpFlCFl"), ("Desc", "inpFlCDesc")):
        w = T._prop(f"txtFlRowsHead{n}", "Width")
        assert T._prop(f"txtFlClsHead{n}", "Width") == w
        assert T._prop(cell, "Width") == w
    assert T._prop("conFlClsHead", "LayoutGap") == T._prop("conFlRowsHead", "LayoutGap")
    # Raekkernes celler staar paa samme X (galleriets skabelon er foldet ud).
    for rows_cell, cls_cell in (("txtFlRowNo", "txtFlCNo"), ("inpFlRowFl", "inpFlCFl"),
                                ("inpFlRowDesc", "inpFlCDesc")):
        assert T._prop(cls_cell, "X") == T._prop(rows_cell, "X"), cls_cell
    # Smal skaerm: Classes scroller vandret som Rows.
    assert T._prop("conFlClsTable", "LayoutOverflowX") == "LayoutOverflow.Scroll"
