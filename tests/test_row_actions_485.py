# -*- coding: utf-8 -*-
"""
Issue #485: de samme raekkeikoner og den samme Copy i Materials, Equipment
og Measuring Point. Kun Materials har Objects (fane og ikon); Equipment og
Measuring Point sidder paa EEN funktionsplads, som vaelges i formularen.

Reglerne staar i Power Fx, som ikke kan koeres her, saa testene laeser den
GENEREREDE skaerm i BIO SAP App - det er den, Studio kompilerer.

    python3 -m pytest tests/test_row_actions_485.py
"""
import os

import yaml

from conftest import ROOT

SCREENS = {"Eq": "ScreenEquipment.pa.yaml", "Mat": "ScreenMaterial.pa.yaml",
           "Mp": "ScreenMeasuringPoint.pa.yaml"}
LISTS = {"Eq": "EquipmentItems", "Mat": "MaterialItems", "Mp": "MeasuringPointItems"}
# Raekkefoelgen paa alle tre sider. Kun Materials har Objects; Measuring
# Point har heller ingen dokumenter (issue #300).
ORDER = {"Eq": ["Open", "Docs", "Copy", "Delete"],
         "Mat": ["Open", "Docs", "Objects", "Copy", "Delete"],
         "Mp": ["Open", "Copy", "Delete"]}
ICONS = {"Open": "Edit", "Docs": "Attach", "Objects": "Link", "Copy": "Copy",
         "Delete": "Delete"}

_CACHE = {}


def _text(p):
    if p not in _CACHE:
        _CACHE[p] = open(os.path.join(ROOT, "BIO SAP App", SCREENS[p]), encoding="utf-8").read()
    return _CACHE[p]


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


_TREES = {}


def _prop(p, ctrl, prop):
    if p not in _TREES:
        _TREES[p] = yaml.safe_load(_text(p))
    hit = _find(_TREES[p], ctrl)
    assert hit is not None, ctrl
    return str(hit["Properties"].get(prop, "")).lstrip("=")


def test_the_row_icons_have_the_same_order_size_and_icon_on_all_three_pages():
    for p, order in ORDER.items():
        y = _text(p)
        for suffix in ("", "C"):
            names = [f"btn{p}Row{a}{suffix}" for a in order]
            pos = [y.index(f"- {n}:") for n in names]
            assert pos == sorted(pos), (p, names)
        for a in order:
            name = f"btn{p}Row{a}"
            assert _prop(p, name, "Layout") == "ButtonLayout.IconOnly", name
            # Issue #551: Open er blyanten kun, naar raekken kan rettes -
            # ellers View-ikonet (icons.edit_or_view).
            want = (f'If((var{p}ViewOnly || ThisItem.Status = "submitted"), '
                    f'"DocumentText", "{ICONS[a]}")' if a == "Open" else f'"{ICONS[a]}"')
            assert _prop(p, name, "Icon") == want, name
            assert _prop(p, name, "Width") == "44", name
            # Hvert ikon har et tooltip med handlingen (issue #515); raekkens
            # noegle staar i AccessibleLabel - den ses i forvejen i raekken.
            assert _prop(p, name, "Tooltip"), name
            assert "ThisItem.ItemKey" in _prop(p, name, "AccessibleLabel"), name


def test_no_details_and_no_more_menu():
    for p in ORDER:
        y = _text(p)
        for gone in (f"btn{p}RowDetails", f"btn{p}RowMore", f"con{p}RowMoreMenu",
                     f"btn{p}MoreCopy", f"var{p}MoreRowId"):
            assert gone not in y, (p, gone)


def test_edit_opens_also_a_read_only_row():
    for p in ORDER:
        # Edit er vejen ind i sidepanelet - ogsaa naar raekken kun kan ses.
        assert _prop(p, f"btn{p}RowOpen", "DisplayMode") == ""
        assert '"View row"' in _prop(p, f"btn{p}RowOpen", "Tooltip")


def test_copy_creates_a_new_draft_row_without_unique_values():
    for p in ORDER:
        for name in (f"btn{p}RowCopy", f"btn{p}ToolbarCopy"):
            fx = _prop(p, name, "OnSelect")
            lst = LISTS[p]
            create = fx.split("ClearCollect(")[0]
            # En ny raekke i listen, laest fra kildens raekke i listen.
            assert f"Patch({lst}, Defaults({lst}), {{" in create, name
            assert f"src: LookUp({lst}, ID = srcId)" in create, name
            # Ingen id'er, noegler, status eller SAP-numre fra kilden.
            for unique in ("src.ID", "src.RowId", "src.ItemKey", "src.AttachmentFolder",
                           "src.RowStatus", "src.FileCount", "src.RequestGuid",
                           "src.RequestNo", "src.SubmittedOn", "src.EquipmentNumber",
                           "src.CreatedMaterialNo", "src.CreatedMeasuringPointNo",
                           "src.SapResult"):
                assert unique not in create, (name, unique)
            assert 'RowStatus: { Value: "draft" }' in create, name
            # Noeglen dannes af kopiens eget ID.
            assert f"Patch({lst}, var{p}SpRow, {{" in create, name
            assert f"RowId: var{p}SpRow.ID" in create, name
            # Kopien aabnes i sidepanelet; originalen roeres ikke.
            assert f"Set(var{p}ActiveRowId, LookUp(col{p}Rows, RowId = var{p}SpRow.ID).RowId)" in fx
            assert f"Set(var{p}EditorOpen, true)" in fx
            assert f"LookUp({lst}, ID = srcId)" in fx
            assert f"Patch({lst}, LookUp(" not in fx, name


def test_the_toolbar_copy_copies_the_open_row():
    for p in ORDER:
        fx = _prop(p, f"btn{p}ToolbarCopy", "OnSelect")
        assert fx.startswith(f"With(\n    {{ srcId: LookUp(col{p}Rows, RowId = var{p}ActiveRowId).RowId")


def test_objects_tab_in_materials_is_part_of_the_form():
    for p in ("Mat",):
        tab = _prop(p, f"con{p}EditorTabsObjects", "OnSelect")
        # Fanen henter ikke raekken igen - valget bevares ved fanskift.
        assert f"col{p}Objects" not in tab
        save = _prop(p, f"btn{p}Save", "OnSelect")
        assert f'ObjectList: Concat(Sort(col{p}Objects, Code), Code, "; ")' in save
        # Objektlisten er med i admin-loggens diff.
        assert '"Object list"' in save
        edit = f'!(IfError(var{p}ViewOnly, false) || var{p}RowStatus = "submitted")'
        assert _prop(p, f"con{p}FlWrap", "Visible") == edit
        assert edit in _prop(p, f"btn{p}ObjList", "DisplayMode")
        assert "Patch(" not in _prop(p, f"btn{p}ObjListApply", "OnSelect")


def test_equipment_and_measuring_point_have_one_functional_location_search_and_no_objects():
    for p in ("Eq", "Mp"):
        y = _text(p)
        # Intet Objects-ikon, ingen Objects-fane og ingen objektliste.
        for gone in (f"btn{p}RowObjects", f"con{p}EditorTabsObjects", f"con{p}EditorObjects",
                     f"col{p}Objects", f"btn{p}ObjAdd", "ObjectList"):
            assert gone not in y, (p, gone)
        # EEN FL-soegning i formularen.
        assert y.count(f"- cmb{p}Fl:") == 1, p
        assert y.count(f"- btn{p}FlSearch:") == 1, p
        # Den skrives til kolonnen FunctionalLocation.
        assert f"FunctionalLocation: Trim(Coalesce(var{p}FFunctionalLocation, \"\"))," in _prop(p, f"btn{p}Save", "OnSelect")
    # Udstyrets krav til en faerdig raekke.
    assert "A functional location is required." in _prop("Eq", "btnEqSave", "OnSelect")
