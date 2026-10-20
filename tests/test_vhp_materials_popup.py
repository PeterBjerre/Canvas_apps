# -*- coding: utf-8 -*-
"""
Issue #451: Materials-popuppen paa operationsraekkerne i VH-plan.

Popuppen arbejder i en kladde (colVhpMatDraft) med en statuschip pr. linje
(Saved / New / Edited / Deleted), Edit/Undo og Delete paa linjen i stedet
for SEL + "Remove material", Save skriver kladden i colVhpMaterials, og X
med ugemte aendringer spoerger foerst. Materials (n) og Docs (n) er groenne
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


def test_sel_column_and_remove_button_are_gone():
    c = _controls()
    for name in ("chkVhpMatSel", "btnVhpRemoveMaterial"):
        assert name not in c, name
    for name in ("btnVhpMatEdit", "btnVhpMatDelete", "imgVhpMatStatus", "btnVhpMatSave",
                 "txtVhpMatChanges", "btnVhpMatDiscardConfirm"):
        assert name in c, name


def test_popup_edits_a_draft_and_save_writes_it():
    c = _controls()
    assert c["galVhpMaterials"]["Items"].strip() == "=Sort(colVhpMatDraft, LineId)"
    # Felterne skriver i kladden - ikke direkte i planens materialer.
    for name in ("inpVhpMatNo", "inpVhpMatQty"):
        assert "Patch(colVhpMatDraft, ThisItem" in c[name]["OnChange"], name
        assert "colVhpMaterials" not in c[name]["OnChange"], name
    assert "Collect(\n    colVhpMatDraft" in c["btnVhpAddMaterial"]["OnSelect"]
    save = c["btnVhpMatSave"]["OnSelect"]
    # Validering foerst, saa erstattes operationens linjer af kladden.
    assert save.index("IsBlank(Trim(MaterialNo))") < save.index("RemoveIf(colVhpMaterials")
    assert "Set(varVhpMatTried, true)" in save
    assert "Filter(colVhpMatDraft, !Deleted) As D" in save
    assert save.index("RemoveIf(colVhpMaterials") < save.index("Collect(\n")
    # Begge Materials-knapper aabner kladden med de gemte linjer.
    for name in ("btnVhpOpMaterials", "btnVhpOpMMat"):
        on = c[name]["OnSelect"]
        assert "ClearCollect(\n    colVhpMatDraft" in on, name
        assert "OrigMaterialNo: M.MaterialNo" in on, name


def test_each_line_shows_its_state():
    chip = _controls()["imgVhpMatStatus"]
    for label in ("Saved", "New", "Edited", "Deleted"):
        assert label in chip["Image"], label
    assert '"deleted"' in chip["Image"] and '"edited"' in chip["Image"]


def test_delete_of_saved_line_is_pending_and_undoable():
    c = _controls()
    dele = c["btnVhpMatDelete"]["OnSelect"]
    assert "Remove(colVhpMatDraft, ThisItem)" in dele          # ny linje
    assert "Deleted: true" in dele                              # gemt linje
    edit = c["btnVhpMatEdit"]
    assert "Deleted: false" in edit["OnSelect"] and "ThisItem.OrigMaterialNo" in edit["OnSelect"]
    assert '"ArrowReset"' in edit["Icon"] and '"Edit"' in edit["Icon"]
    # En gemt linje er laast, til der trykkes Edit.
    assert "ThisItem.Editing" in c["inpVhpMatNo"]["DisplayMode"]


def test_close_with_unsaved_changes_asks_first():
    c = _controls()
    close = c["btnVhpMatClose"]["OnSelect"]
    assert "Set(varVhpMatDiscardOpen, true)" in close
    assert "Clear(colVhpMatDraft)" in close
    # Sloeret paa mobil lukker paa samme maade.
    assert "Set(varVhpMatDiscardOpen, true)" in c["conVhpPickerBackdrop"]["OnSelect"]
    ok = c["btnVhpMatDiscardConfirm"]["OnSelect"]
    assert 'Set(varVhpMatOpNo, "")' in ok and "Clear(colVhpMatDraft)" in ok
    # Skemaet og variablerne saettes ved start (generate_app_onstart.py).
    text = open(SCREEN, encoding="utf-8").read()
    assert "If(false, ClearCollect(colVhpMatDraft, { LineId: 0," in text
    assert "Set(varVhpMatDiscardOpen, false);" in text


def test_buttons_are_green_with_a_summary_when_content_exists():
    c = _controls()
    for name in ("btnVhpOpMaterials", "btnVhpOpMMat", "btnVhpOpDocs", "btnVhpOpMDocs"):
        p = c[name]
        assert "C.'border-ok'" in p["BorderColor"], name
        assert p.get("Tooltip"), name
    assert "MaterialNo & \" x \"" in c["btnVhpOpMaterials"]["Tooltip"]
    assert "FileNames" in c["btnVhpOpDocs"]["Tooltip"]
    assert "FileCount, 0) > 0" in c["btnVhpOpDocs"]["BorderColor"]
