# -*- coding: utf-8 -*-
"""
Materials: objektlisten, lagerreglerne og Saved rows (issue #204, #228).

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


def _ctrl(ctrl, path=MAT):
    import yaml
    if path not in _TREE:
        _TREE[path] = yaml.safe_load(open(path, encoding="utf-8").read())
    hit = _find(_TREE[path], ctrl)
    assert hit is not None, ctrl
    return hit


def _prop(ctrl, prop, path=MAT):
    """En kontrols egenskab (formlen uden =) fra den genererede YAML."""
    return str(_ctrl(ctrl, path)["Properties"][prop]).lstrip("=")


def _children(ctrl):
    return [list(c)[0] for c in _ctrl(ctrl).get("Children", [])]


def _grid_cells(ctrl):
    return [cell for pair in _children(ctrl) for cell in _children(pair)]


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


def test_the_objects_tab_is_saved_with_the_row():
    # Issue #485/#513: Object list (Apply selection) og skraldespanden
    # retter kun formularens liste - Save skriver den paa raekken sammen med
    # resten. Intet Patch paa selve fanen.
    add = _prop("btnMatObjListApply", "OnSelect")
    assert "Collect(colMatObjects" in add
    assert "Patch(" not in add
    rem = _prop("btnMatObjRemove", "OnSelect")
    assert rem.startswith("RemoveIf(colMatObjects, Code = ThisItem.Code)")
    assert "Patch(" not in rem
    save = _prop("btnMatSave", "OnSelect")
    assert 'ObjectList: Concat(Sort(colMatObjects, Code), Code, "; ")' in save
    assert "ObjectListJson: JSON(ForAll(Sort(colMatObjects, Code)" in save
    assert 'FunctionalLocation: Coalesce(First(Sort(colMatObjects, Code)).Code, "")' in save


def test_the_objects_tab_opens_the_row_and_is_read_only_when_locked():
    open_fx = _prop("btnMatRowObjects", "OnSelect")
    assert open_fx.startswith("Set(varMatActiveRowId, ThisItem.RowId);")
    assert 'Set(varMatEditorTab, "Objects")' in open_fx
    assert "ParseJSON(ThisItem.ObjectListJson)" in open_fx
    # Soegning og Object list kun, naar formularens raekke kan rettes - ogsaa
    # paa en NY raekke (Create); i visning er skraldespanden slaaet fra.
    edit = '!(IfError(varMatViewOnly, false) || varMatRowStatus = "submitted")'
    assert _prop("conMatFlWrap", "Visible") == edit
    assert edit in _prop("btnMatObjList", "DisplayMode")
    assert edit in _prop("btnMatObjRemove", "DisplayMode")


def test_switching_to_the_objects_tab_keeps_the_unsaved_selection():
    tab = _prop("conMatEditorTabsObjects", "OnSelect")
    assert 'Set(varMatEditorTab, "Objects")' in tab
    # Fanen henter IKKE raekken igen - saa et valg, der ikke er gemt, bliver.
    assert "colMatObjects" not in tab


def test_a_loaded_row_fills_the_list_and_a_copy_is_a_new_row():
    assert "ParseJSON(ThisItem.ObjectListJson)" in _prop("btnMatRowOpen", "OnSelect")
    copy = _prop("btnMatRowCopy", "OnSelect")
    # Kopien er en NY raekke i listen, og objekterne foelger med fra kilden.
    assert "Patch(MaterialItems, Defaults(MaterialItems)" in copy
    assert "ObjectList: src.ObjectList," in copy
    assert "ObjectListJson: src.ObjectListJson," in copy


def test_fl_search_needs_sixteen_characters():
    y = _mat()
    assert "At least 16 characters" in y
    assert "Type at least 16 characters before searching." in y
    assert "Len(Trim(Coalesce(cmbMatFl.SearchText, varMatFlQuery))) < 16" in \
        _prop("btnMatFlSearch", "DisplayMode")


def test_no_bom_item_and_recommended_stock_are_gone():
    y = _mat()
    for gone in ("NoBomItem", "No BOM", "RecommendedStock", "Recommended stock",
                 "btnMatNoBom", "btnMatMoreDetails", "varMatExtraOpen"):
        assert gone not in y, gone


def test_a_strategic_row_without_an_object_is_stopped_at_submit():
    sub = _prop("btnMatSubmit", "OnSelect")
    assert "A strategic row needs at least one functional location" in sub
    # Ikke ved Save row - en ny raekke KAN ikke have en funktionsplads endnu.
    assert "functional location" not in _prop("btnMatSave", "OnSelect")


def test_strategic_part_is_read_as_yes_also_on_an_old_row():
    y = _mat()
    assert '"YES", "JA", "Y", "TRUE", "1"' in y


# ---------------------------------------------------------------------------
# Lager og de valgfrie oplysninger
# ---------------------------------------------------------------------------
def test_stock_item_requires_min_and_max_and_min_below_max():
    save = _prop("btnMatSave", "OnSelect")
    assert "Min stock and max stock are required for a stock item." in save
    assert "Min stock must be less than or equal to max stock." in save
    assert "varMatFMinStock > varMatFMaxStock" in save
    # Min > max er forkert ogsaa paa en kladde - og siges, mens der skrives.
    # Der er een gem-knap (Add row/Update row, UX-review F2): den gemmer som
    # gyldig eller som kladde, og tjekket staar i begge grene.
    assert save.count("Min stock must be less than or equal to max stock.") >= 2
    assert "varMatFMinStock > varMatFMaxStock" in _prop("txtMatStockMsg", "Visible")


def test_the_first_row_is_plant_description_stock_item_and_replace():
    assert _grid_cells("conMatGridMain") == [
        "conMatPlant", "conMatText", "conMatIsStockItem", "conMatReplacesExisting"]
    # Begge valg er segmenterede [ No | Yes ] - som Revision i Item Editor.
    assert _children("conMatIsStockItemSeg") == ["conMatIsStockItemSegNo",
                                                 "conMatIsStockItemSegYes"]
    assert _children("conMatReplacesExistingSeg") == ["conMatReplacesExistingSegNo",
                                                      "conMatReplacesExistingSegYes"]
    # Overskriften er Item Editors (build_helpers.section_header).
    assert _prop("txtMatEditorHeadTitle", "Text") == '"Row details"'


def test_stock_fields_show_only_for_a_stock_item_and_are_saved_blank_otherwise():
    stock = "Coalesce(varMatFIsStockItem, false)"
    assert _prop("conMatGridStock", "Visible") == stock
    assert _grid_cells("conMatGridStock") == ["conMatMinStock", "conMatMaxStock",
                                               "conMatStorageBin"]
    save = _prop("btnMatSave", "OnSelect")
    assert f"MinStock: If({stock}, varMatFMinStock, Blank())" in save
    assert f'StorageBin: If({stock}, Trim(Coalesce(varMatFStorageBin, "")), "")' in save
    # Yes foreslaar lagerpladsen "X" igen, hvis den er tom.
    assert 'Set(varMatFStorageBin, "X")' in _prop("conMatIsStockItemSegYes", "OnSelect")


def test_storage_bin_is_suggested_as_x_by_the_form():
    y = _mat()
    assert 'Set(varMatFStorageBin, "X");' in y


def test_replaced_material_no_is_required_only_when_it_replaces_one():
    y = _mat()
    assert ("Replaced material no. is required when the material replaces an "
            "existing one.") in y
    # Feltet vises kun, naar der er noget at erstatte - og gemmes tomt ellers.
    repl = "Coalesce(varMatFReplacesExisting, false)"
    assert _prop("conMatGridReplace", "Visible") == repl
    assert (f'ReplacedMaterialNo: If({repl}, Trim(Coalesce(varMatFReplacedMaterialNo, "")), "")'
            in _prop("btnMatSave", "OnSelect"))


def test_purchase_order_text_is_remarks_in_a_popup():
    y = _mat()
    assert '"Remarks"' not in y
    # Kolonnen er stadig Remarks.
    assert 'Remarks: Trim(Coalesce(varMatFRemarks, ""))' in _prop("btnMatSave", "OnSelect")
    assert _prop("inpMatPoText", "Type") == "TextInputType.Multiline"
    assert _prop("inpMatPoText", "OnChange") == "Set(varMatFRemarks, Self.Text)"
    assert _prop("btnMatPoText", "OnSelect").endswith("Set(varMatPoOpen, true)")
    # Save tager teksten med, saa intet skrevet gaar tabt; X og Cancel
    # kasserer aendringerne (issue #279, #429). Et tryk paa sloeret lukker ikke.
    assert "Set(varMatFRemarks, inpMatPoText.Text)" in _prop("btnMatPoSave", "OnSelect")
    close = _prop("btnMatPoClose", "OnSelect")
    assert close.endswith("Set(varMatPoOpen, false)")
    assert "Set(varMatFRemarks, varMatPoBefore)" in close
    assert "varMatPoOpen" not in _prop("conMatPoBackdrop", "OnSelect")


def test_reset_restores_only_the_form_and_asks_first():
    """Reset kasserer kun formularens ugemte aendringer (issue #403) - og
    spoerger foerst, naar der er nogen (issue #450)."""
    click = _prop("btnMatNew", "OnSelect")
    assert _prop("btnMatNew", "Text") == '"Reset"'
    assert "Set(varMatResetAsk, true)" in click
    reset = _prop("btnMatResetConfirm", "OnSelect")
    assert reset.startswith("Set(varMatResetAsk, false);")
    assert "Set(varMatEditorOpen, true)" in reset
    # Saved Rows og anmodningen roeres ikke. (Documents-fanen laeser
    # raekkens dokumenter igen, naar brugeren stod paa den - kun en LookUp.)
    for untouched in ("Patch(MaterialItems", "Remove(", "ClearCollect(colMatRows",
                      "RemoveIf(colMatRows", "varMatRequestGuid", "varMatRequestNo",
                      "MD_RequestIndex"):
        assert untouched not in reset, untouched


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
    for head in ("MATERIAL DESCRIPTION", "MANUFACTURER",
                 "MANUFACTURER PART NO.", "SUPPLIER"):
        assert '"%s"' % head in y, head
    # Funktionspladsen er ikke en kolonne i Materials laengere (issue #228).
    assert '"FUNCTIONAL LOCATION"' not in y
    eq = open(EQ, encoding="utf-8").read()
    for head in ("STATUS", "DESCRIPTION", "FUNCTIONAL LOCATION", "TYPE", "PLANT"):
        assert '"%s"' % head in eq, head


def test_details_popup_is_replaced_by_the_side_panel():
    y = _mat()
    # Details-popuppen er erstattet af sidepanelet (ingen galMatDetails).
    assert "galMatDetails" not in y
    assert "conMatEditorDetails" in y
    assert "inpMatDetCreatedNo" in y


def test_row_actions_are_edit_docs_objects_copy_and_delete_last():
    # Galleriets skabelon er fladet ud (X/Y), saa raekkefoelgen er
    # kontrollernes raekkefoelge i filen. Ingen Details (issue #485).
    y = _mat()
    assert "btnMatRowDetails" not in y
    desk = ["btnMatRowOpen", "btnMatRowDocs", "btnMatRowObjects",
            "btnMatRowCopy", "btnMatRowDelete"]
    for names in (desk, [n + "C" for n in desk]):
        pos = [y.index("- %s:" % n) for n in names]
        assert pos == sorted(pos), names
    # Delete er destruktiv, kun et ikon og bag bekraeftelsen.
    assert _prop("btnMatRowDelete", "Layout") == "ButtonLayout.IconOnly"
    assert "Set(varMatConfirmDelete, true)" in _prop("btnMatRowDelete", "OnSelect")
    # Docs vaelger raekken og aabner Documents-fanen; antallet staar i tooltippet.
    docs = _prop("btnMatRowDocs", "OnSelect")
    assert docs.startswith("Set(varMatActiveRowId, ThisItem.RowId);")
    assert 'Set(varMatEditorTab, "Documents")' in docs
    assert "Set(varMatDocsId, varMatActiveRowId)" in docs
    assert "ThisItem.FileCount" in _prop("btnMatRowDocs", "Tooltip")
    assert "ThisItem.ObjectList" in _prop("btnMatRowObjects", "Tooltip")


def test_equipment_has_the_same_row_actions_without_objects():
    eq = open(EQ, encoding="utf-8").read()
    # Udstyret har EEN funktionsplads i formularen - intet Objects-ikon (#485).
    for gone in ("btnEqRowMore", "btnEqMoreCopy", "btnEqMoreDelete", "btnEqRowDetails",
                 "btnEqRowObjects"):
        assert gone not in eq, gone
    for name in ("btnEqRowOpen", "btnEqRowDocs", "btnEqRowCopy", "btnEqRowDelete"):
        assert "- %s:" % name in eq, name
