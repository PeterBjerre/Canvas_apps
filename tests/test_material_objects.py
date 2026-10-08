# -*- coding: utf-8 -*-
"""
Materials: objektlisten, lagerreglerne og Saved rows (issue #204).

Reglerne staar i Power Fx, som ikke kan koeres her, saa testene laeser dem
i den GENEREREDE skaerm - det er den, Studio kompilerer.

    python3 -m pytest tests/test_material_objects.py
"""
import os
import sys

from conftest import ROOT, TOOLS

sys.path.insert(0, TOOLS)
import object_list as ol

MAT = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")
EQ = os.path.join(ROOT, "BIO SAP App", "ScreenEquipment.pa.yaml")


def _mat():
    return open(MAT, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# Objektlisten
# ---------------------------------------------------------------------------
def test_add_refuses_a_duplicate_code():
    fx = ol.add_fx("colX", "varPick", '"d"', "varMsg")
    assert "Upper(Trim(Code)) = Upper(Trim(varPick))" in fx
    assert "Already in the object list." in fx
    # Dubletten tilfoejes ikke - Collect staar i den SIDSTE gren.
    assert fx.index("Already in the object list.") < fx.index("Collect(colX")


def test_add_refuses_an_empty_pick():
    fx = ol.add_fx("colX", "varPick", '"d"', "varMsg")
    assert 'IsBlank(Trim(Coalesce(varPick, "")))' in fx


def test_restore_reads_json_then_list_then_the_fl_column():
    fx = ol.restore_fx("colX", json_src="J", list_src="L", fl_src="F")
    assert fx.startswith("Clear(colX);")
    assert fx.index("ParseJSON(J)") < fx.index('Split(L, ";")') < fx.index("Trim(F)")
    # Tomme led i "a; ; b" bliver ikke et objekt uden kode.
    assert '!IsBlank(Trim(Value))' in fx


def test_saved_values_use_the_same_format_as_the_plan_app():
    assert ol.SEP == "; "
    assert ol.codes_fx("colX") == 'Concat(Sort(colX, Code), Code, "; ")'
    assert "JSONFormat.Compact" in ol.json_fx("colX")


def test_summary_shows_the_first_code_and_how_many_more():
    fx = ol.summary_fx("ThisItem.ObjectList", "ThisItem.FunctionalLocation")
    assert '" +" & Text(n - 1)' in fx
    assert fx.count("ThisItem.ObjectList") == 1


def test_the_screen_keeps_the_object_list_on_the_row():
    y = _mat()
    # Gemt som koder, som JSON og med den foerste kode i FL-kolonnen.
    assert 'ObjectList: Concat(Sort(colMatObjects, Code), Code, "; ")' in y
    assert "ObjectListJson: JSON(ForAll(Sort(colMatObjects, Code)" in y
    assert 'FunctionalLocation: Coalesce(First(Sort(colMatObjects, Code)).Code, "")' in y
    # Gendannet, naar en raekke hentes, kopieres - og ryddet med formularen.
    assert y.count("ParseJSON(ThisItem.ObjectListJson)") >= 2
    assert "Clear(colMatObjects);" in y


def test_fl_search_and_add_need_sixteen_characters():
    y = _mat()
    assert "At least 16 characters" in y
    assert "Type at least 16 characters before searching." in y
    # Add er spaerret, indtil der ER valgt en kode paa mindst 16 tegn.
    assert 'Len(Trim(Coalesce(varMatFFunctionalLocation, ""))) >= 16' in y


def test_a_strategic_row_cannot_be_no_bom_and_needs_an_object():
    y = _mat()
    assert "A strategic part needs at least one functional location." in y
    assert "A strategic row needs at least one functional location." in y
    assert "Add at least one functional location - or turn on No BOM Item." in y


def test_strategic_part_is_read_as_yes_also_on_an_old_row():
    y = _mat()
    assert '"YES", "JA", "Y", "TRUE", "1"' in y


# ---------------------------------------------------------------------------
# Lager og de valgfrie oplysninger
# ---------------------------------------------------------------------------
def test_stock_item_requires_min_and_max_and_min_below_max():
    y = _mat()
    assert "Min stock and max stock are required for a stock item." in y
    assert "Min stock must be less than or equal to max stock." in y
    assert "varMatFMinStock > varMatFMaxStock" in y


def test_storage_bin_is_suggested_as_x_by_the_form():
    y = _mat()
    assert 'Set(varMatFStorageBin, "X");' in y


def test_replaced_material_no_is_required_only_when_it_replaces_one():
    y = _mat()
    assert ("Replaced material no. is required when the material replaces an "
            "existing one.") in y
    # Feltet vises kun, naar der er noget at erstatte.
    assert "Coalesce(varMatFReplacesExisting, false)" in y


def test_created_material_no_is_filled_in_details_not_in_the_form():
    y = _mat()
    # Ingen formularvariabel og intet felt i gitteret.
    assert "varMatFCreatedMaterialNo" not in y
    assert "conMatCreatedMaterialNo" not in y
    # Men et felt i Details, der gemmer paa raekken.
    assert "inpMatDetCreatedNo" in y
    assert "CreatedMaterialNo: Trim(Coalesce(varMatDetCreatedNo" in y


# ---------------------------------------------------------------------------
# Saved rows - een visning
# ---------------------------------------------------------------------------
def test_compact_and_all_columns_are_gone_in_both_apps():
    for path in (MAT, EQ):
        y = open(path, encoding="utf-8").read()
        assert "AllCols" not in y, path
        assert "All columns" not in y, path
        assert '"Compact"' not in y, path


def test_the_tables_keep_the_columns_compact_showed():
    y = _mat()
    for head in ("FUNCTIONAL LOCATION", "MATERIAL DESCRIPTION", "MANUFACTURER",
                 "MANUFACTURER PART NO.", "SUPPLIER"):
        assert '"%s"' % head in y, head
    eq = open(EQ, encoding="utf-8").read()
    for head in ("TYPE", "PLANT", "FUNCTIONAL LOCATION", "EQUIPMENT NUMBER",
                 "DESCRIPTION", "EQUIPMENT TYPE"):
        assert '"%s"' % head in eq, head


def test_details_is_grouped_in_one_gallery():
    y = _mat()
    assert "galMatDetails" in y
    for group in ("Identification", "Object list", "Manufacturer and supplier",
                  "Stock and storage", "Classification and approval",
                  "Additional information", "Requester and request"):
        assert '"%s"' % group in y, group
