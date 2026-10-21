# -*- coding: utf-8 -*-
"""Formularer i sektioner (UX-review 2026-10, M2)."""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import layout_tokens as lay  # noqa: E402
APP = os.path.join(ROOT, "BIO SAP App")


def _yaml(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _properties(screen):
    doc = yaml.safe_load(open(os.path.join(APP, screen), encoding="utf-8"))
    result = {}

    def walk(nodes):
        for item in nodes or []:
            for name, body in item.items():
                result[name] = body.get("Properties") or {}
                walk(body.get("Children"))

    for screen_doc in doc["Screens"].values():
        walk(screen_doc.get("Children"))
    return result


def _order(y, names):
    return [y.index(f"- {n}:") for n in names]


def test_a_section_is_a_muted_uppercase_title_without_rules():
    y = _yaml("ScreenEquipment.pa.yaml")
    assert "conEqSecIdentRule:" not in y and "conEqSecLocRule:" not in y
    assert 'Upper("Location")' in y


def test_equipment_sections_follow_the_mockup():
    y = _yaml("ScreenEquipment.pa.yaml")
    pos = _order(y, ["txtEqSecIdent", "txtEqSecLoc", "txtEqSecMfr", "txtEqSecWarranty"])
    assert pos == sorted(pos)
    for t in ("Identification", "Location", "Manufacturer", "Warranty and documents"):
        assert f'Upper("{t}")' in y, t
    # Felterne staar i deres sektion. FL staar i Location paa Details
    # (issue #485 - ingen Objects-fane) og garantien paa Documents-fanen
    # (issue #430) - efter Details.
    assert (y.index("txtEqSecLoc:") < y.index("conEqFl:") < y.index("conEqRoomCoordinates:")
            < y.index("txtEqSecMfr:"))
    assert y.index("txtEqSecMfr:") < y.index("conEqManufacturer:") < y.index("conEqEditorDocuments:")
    assert "conEqEditorObjects:" not in y
    assert y.index("conEqEditorDocuments:") < y.index("txtEqSecWarranty:")


def test_materials_and_measuring_points_have_titled_sections():
    m = _yaml("ScreenMaterial.pa.yaml")
    for t in ("Identification", "Manufacturer and supplier", "Price and classification"):
        assert f'Upper("{t}")' in m, t
    p = _yaml("ScreenMeasuringPoint.pa.yaml")
    for t in ("Identification", "Measuring point", "PRODOS", "Notes"):
        assert f'Upper("{t}")' in p, t
    # Maalepunktets sektion kun for et nyt maalepunkt - som dens raekker.
    i = p.index("- conMpSecType:")
    j = p.index("Children:", i)
    assert "Visible:" in p[i:j]


def test_equipment_and_measuring_point_use_the_responsive_row_panel():
    for screen, prefix in (("ScreenEquipment.pa.yaml", "Eq"),
                          ("ScreenMeasuringPoint.pa.yaml", "Mp")):
        props = _properties(screen)
        assert props[f"con{prefix}EditorPanel"]["Width"] == "=" + lay.PANEL_W_AT
        assert props[f"con{prefix}EditorSections"]["LayoutOverflowY"] == "=LayoutOverflow.Scroll"
        assert props[f"btn{prefix}EditorClose"]["OnSelect"].startswith(f"=Set(var{prefix}ActiveRowId")


def test_domain_panels_match_the_bright_two_column_mockup():
    panels = [
        ("ScreenEquipment.pa.yaml", "Eq", "conEqGridIdent0"),
        ("ScreenMaterial.pa.yaml", "Mat", "conMatGridMain"),
        ("ScreenMeasuringPoint.pa.yaml", "Mp", "conMpGridObject"),
    ]
    for screen, prefix, grid in panels:
        props = _properties(screen)
        assert props[f"img{prefix}EditorBackdrop"]["Fill"] == "=RGBA(0, 0, 0, 0)"
        assert props[grid]["LayoutDirection"] == "=LayoutDirection.Vertical"
        pair = props[f"{grid}Pair0"]
        assert pair["LayoutDirection"] == "=LayoutDirection.Horizontal"
        assert pair["LayoutWrap"] == "=true"


def test_issue_board_detail_panel_does_not_dim_the_workspace():
    props = _properties("ScreenIssueBoard.pa.yaml")
    assert props["imgIbDetBackdrop"]["Fill"] == "=RGBA(0, 0, 0, 0)"


def test_material_editor_exposes_the_three_requested_tabs():
    props = _properties("ScreenMaterial.pa.yaml")
    for name in ("conMatEditorTabsDetails", "conMatEditorTabsObjects",
                 "conMatEditorTabsDocuments"):
        assert name in props
    assert props["conMatEditorObjects"]["Visible"] == '=varMatEditorTab = "Objects"'
    assert props["conMatEditorDocuments"]["Visible"] == '=varMatEditorTab = "Documents"'
    assert "conMatObjTabBody" in props and "conMatAttBody" in props
    assert "conMatObjPopModal" not in props and "conMatAttModal" not in props


def test_functional_location_has_status_column_and_row_panel():
    props = _properties("ScreenFunctionalLocation.pa.yaml")
    assert "btnFlRowStatus" in props
    assert "conFlEditorPanel" in props
    assert props["conFlEditorPanel"]["Width"] == "=" + lay.PANEL_W_AT
    assert all(f"conFlPanel{section}" in props
               for section in ("Main", "Class", "Loc", "Mfr", "War", "TRM"))
    assert "conFlPanelStatus" not in props and "conFlPanelMaster" not in props


def test_issue_board_details_use_a_side_panel_without_losing_tabs():
    props = _properties("ScreenIssueBoard.pa.yaml")
    assert props["conIbDetModal"]["Width"] == "=" + lay.PANEL_W_AT
    assert all(name in props for name in ("btnIbTabDetails", "btnIbTabActivity", "btnIbTabFiles"))


def test_equipment_and_measuring_point_show_all_actions_without_a_more_menu():
    # Issue #485: alle handlinger staar direkte i Actions - ingen More-menu.
    for screen, prefix in (("ScreenEquipment.pa.yaml", "Eq"),
                          ("ScreenMeasuringPoint.pa.yaml", "Mp")):
        props = _properties(screen)
        if prefix == "Mp":
            # Ingen dokumenter paa maalepunkter (issue #300).
            assert f"btn{prefix}RowDocs" not in props
        else:
            assert f"btn{prefix}RowDocs" in props
            assert "FileCount" in props[f"btn{prefix}RowDocs"]["Tooltip"]
        for gone in (f"btn{prefix}RowMore", f"con{prefix}RowMoreMenu",
                     f"btn{prefix}MoreCopy", f"btn{prefix}MoreDelete"):
            assert gone not in props, gone
        assert f"btn{prefix}RowCopy" in props and f"btn{prefix}RowDelete" in props
