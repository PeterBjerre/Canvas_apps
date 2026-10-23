# -*- coding: utf-8 -*-
"""
Issue #451: Materials-popuppen paa operationsraekkerne i VH-plan.

Popuppen arbejder i en kladde (colVhpMatDraft). Efter Peters mockup
(2026-10-23) slaar en indtastningsraekke materialet op med lagerflowet
BioSap-Integration-MaterialStock, tabellen har blyant og skraldespand pr.
linje, Save skriver kladden i colVhpMaterials, og Cancel/X med ugemte
aendringer spoerger foerst. Materials (n) og Docs (n) er groenne
og har en tooltip, naar der er noget gemt.

    python3 -m pytest tests/test_vhp_materials_popup.py
"""
import os

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _controls():
    d = yaml.safe_load(open(SCREEN, encoding="utf-8").read())
    out = {}

    def walk(nodes):
        for item in nodes or []:
            for name, c in item.items():
                out[name] = c.get("Properties") or {}
                walk(c.get("Children"))

    for s in d["Screens"].values():
        walk(s.get("Children"))
    return out


def test_layout_follows_the_mockup():
    """Peter 2026-10-23: indtastningsraekke oeverst, tabel uden status,
    blyant og skraldespand pr. linje, Cancel og Save i bunden."""
    c = _controls()
    for name in ("chkVhpMatSel", "btnVhpRemoveMaterial", "imgVhpMatStatus"):
        assert name not in c, name
    for name in ("inpVhpMatSearch", "btnVhpMatLookup", "inpVhpMatNewDesc", "inpVhpMatNewQty",
                 "inpVhpMatNewUnit", "inpVhpMatNewTotal", "inpVhpMatNewRop",
                 "btnVhpAddMaterial", "btnVhpMatEdit", "btnVhpMatDelete", "txtVhpMatTotal",
                 "txtVhpMatRop", "btnVhpMatCancel", "btnVhpMatSave", "txtVhpMatChanges",
                 "btnVhpMatDiscardConfirm"):
        assert name in c, name
    head = c["htmVhpMatHeader"]["HtmlText"]
    for col in ("MATERIAL", "DESCRIPTION", "QUANTITY", "UNIT", "TOTAL", "REORDER POINT",
                "ACTIONS"):
        assert f"<span>{col}</span>" in head, col
    assert "STATUS" not in head
    assert "Materials – operation" in c["txtVhpMatTitle"]["Text"]
    assert "Search and add materials for this operation." in c["txtVhpMatNote"]["Text"]
    assert '" added"' in c["txtVhpMatChanges"]["Text"]
    # Opslaget giver beskrivelse og enhed - de kan ikke skrives i.
    for name in ("inpVhpMatNewDesc", "inpVhpMatNewUnit", "inpVhpMatNewTotal", "inpVhpMatNewRop"):
        assert "DisplayMode.View" in c[name]["DisplayMode"], name


def test_lookup_calls_the_stock_flow_with_the_sap_plant_number():
    c = _controls()
    fx = c["btnVhpMatLookup"]["OnSelect"]
    assert "'BioSap-Integration-MaterialStock'.Run(p, m)" in fx
    assert "LookUp(colVhpPlantCodes, Value = VhpPlant).PlantNumber" in fx
    assert "ParseJSON(varVhpMatStock.details)" in fx
    assert "St = 200" in fx
    assert 'varVhpMatStock.ok <> "yes"' in fx
    assert "Set(varVhpMatBusy, false)" in fx
    app = open(os.path.join(ROOT, "BIO SAP App", "App.pa.yaml"), encoding="utf-8").read()
    assert "PlantNumber: R.PlantNumber" in app


def test_popup_edits_a_draft_and_save_writes_it():
    c = _controls()
    assert c["galVhpMaterials"]["Items"].strip() == "=Sort(colVhpMatDraft, LineId)"
    # Antallet skriver i kladden - ikke direkte i planens materialer.
    on = c["inpVhpMatQty"]["OnChange"]
    assert "Patch(colVhpMatDraft, ThisItem" in on
    assert "colVhpMaterials" not in on
    assert "ThisItem.Editing" in c["inpVhpMatQty"]["DisplayMode"]
    add = c["btnVhpAddMaterial"]["OnSelect"]
    assert "Collect(\n            colVhpMatDraft" in add
    assert "LookUp(colVhpMatFound, MaterialNo = Upper(Trim(inpVhpMatSearch.Text)))" in add
    save = c["btnVhpMatSave"]["OnSelect"]
    # Validering foerst, saa erstattes operationens linjer af kladden.
    assert save.index("Quantity <= 0") < save.index("RemoveIf(colVhpMaterials")
    assert "Set(varVhpMatTried, true)" in save
    assert "colVhpMatDraft As D" in save
    assert save.index("RemoveIf(colVhpMaterials") < save.index("Collect(\n")
    # Total og Reorder point gemmes ikke.
    assert "Total" not in save.split("RemoveIf(colVhpMaterials")[1]
    # Begge Materials-knapper aabner kladden med de gemte linjer.
    for name in ("btnVhpOpMaterials", "btnVhpOpMMat"):
        on = c[name]["OnSelect"]
        assert "ClearCollect(\n    colVhpMatDraft" in on, name
        assert "OrigQuantity: M.Quantity" in on, name


def test_delete_removes_the_line_from_the_draft():
    c = _controls()
    assert c["btnVhpMatDelete"]["OnSelect"].strip() == "=Remove(colVhpMatDraft, ThisItem)"
    edit = c["btnVhpMatEdit"]
    assert "Editing: !ThisItem.Editing" in edit["OnSelect"]
    assert '"Checkmark"' in edit["Icon"] and '"Edit"' in edit["Icon"]


def test_close_with_unsaved_changes_asks_first():
    c = _controls()
    for name in ("btnVhpMatClose", "btnVhpMatCancel"):
        close = c[name]["OnSelect"]
        assert "Set(varVhpMatDiscardOpen, true)" in close, name
        assert "Clear(colVhpMatDraft)" in close, name
    # Sloeret paa mobil lukker paa samme maade.
    assert "Set(varVhpMatDiscardOpen, true)" in c["conVhpPickerBackdrop"]["OnSelect"]
    ok = c["btnVhpMatDiscardConfirm"]["OnSelect"]
    assert 'Set(varVhpMatOpNo, "")' in ok and "Clear(colVhpMatDraft)" in ok
    # Skemaet og variablerne saettes ved start (generate_app_onstart.py).
    text = open(SCREEN, encoding="utf-8").read()
    assert "If(false, ClearCollect(colVhpMatDraft, { LineId: 0," in text
    assert "Set(varVhpMatDiscardOpen, false);" in text
    assert "Set(varVhpMatBusy, false);" in text


def test_buttons_are_green_with_a_summary_when_content_exists():
    c = _controls()
    for name in ("btnVhpOpMaterials", "btnVhpOpMMat", "btnVhpOpDocs", "btnVhpOpMDocs"):
        p = c[name]
        assert "C.'border-ok'" in p["BorderColor"], name
        assert p.get("Tooltip"), name
    assert "MaterialNo & \" x \"" in c["btnVhpOpMaterials"]["Tooltip"]
    assert "FileNames" in c["btnVhpOpDocs"]["Tooltip"]
    assert "FileCount, 0) > 0" in c["btnVhpOpDocs"]["BorderColor"]
