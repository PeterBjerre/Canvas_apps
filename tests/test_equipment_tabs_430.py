# -*- coding: utf-8 -*-
"""
Issue #430: Equipments sidepanel har fanerne Details, Objects og
Documents - samme moenster som Materials (domain_parts.editor_tabs).

- Details: felterne uden funktionspladsen og garantien.
- Objects: funktionspladsen med soegningen (FL-vaelgeren).
- Documents: Warranty from/to, antallet af dokumenter og
  ModernAttachments-kontrollen. Ingen dokumentpopup laengere.
- Bundbjaelken (Delete row, Reset, Cancel, Save) er faelles for fanerne.
- Gem, Patch og kravene er de samme.

    python3 -m pytest tests/test_equipment_tabs_430.py
"""
import os
import re

import yaml

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")


def _text(screen):
    with open(os.path.join(APP, screen + ".pa.yaml"), encoding="utf-8") as f:
        return f.read()


def _screen(screen):
    doc = yaml.safe_load(_text(screen))
    return next(iter(doc["Screens"].values()))


def _find(node, name):
    for c in node.get("Children") or []:
        for n, v in c.items():
            if n == name:
                return v
            hit = _find(v, name)
            if hit is not None:
                return hit
    return None


def _names(node):
    out = []
    for c in node.get("Children") or []:
        for n, v in c.items():
            out.append(n)
            out.extend(_names(v))
    return out


def _prop(node, key):
    return str((node.get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


EQ = _screen("ScreenEquipment")
MAT = _screen("ScreenMaterial")


def test_equipment_has_the_three_tabs_like_materials():
    for screen, tag in ((EQ, "Eq"), (MAT, "Mat")):
        sections = _find(screen, f"con{tag}EditorSections")
        top = [n for c in sections["Children"] for n in c]
        assert top == [f"con{tag}EditorTabs", f"con{tag}EditorDetails",
                       f"con{tag}EditorObjects", f"con{tag}EditorDocuments"], top
        for tab in ("Details", "Objects", "Documents"):
            box = _find(screen, f"con{tag}Editor{tab}")
            assert _prop(box, "Visible") == f'var{tag}EditorTab = "{tab}"'
            btn = _find(screen, f"con{tag}EditorTabs{tab}")
            assert _prop(btn, "OnSelect").startswith(f'Set(var{tag}EditorTab, "{tab}")')
            # Fanerne er til at trykke paa - ogsaa i visning.
            assert "ViewOnly" not in _prop(btn, "DisplayMode")


def test_tab_styling_is_the_same_as_materials():
    """Samme skinne og knapper - kun praefikset og Objects' handling er
    forskellige."""
    for suffix in ("", "Details", "Objects", "Documents"):
        eq = _find(EQ, f"conEqEditorTabs{suffix}")
        mat = _find(MAT, f"conMatEditorTabs{suffix}")
        assert eq.get("Control") == mat.get("Control")
        for key in set(eq["Properties"]) | set(mat["Properties"]):
            if key == "OnSelect":
                continue
            a = _prop(eq, key).replace("varEq", "var")
            b = _prop(mat, key).replace("varMat", "var")
            assert a == b, (suffix, key, a, b)


def test_fields_moved_out_of_details_and_not_duplicated():
    details = _names(_find(EQ, "conEqEditorDetails"))
    objects = _names(_find(EQ, "conEqEditorObjects"))
    documents = _names(_find(EQ, "conEqEditorDocuments"))
    for name in ("cmbEqFl", "btnEqFlSearch", "txtEqFlMsg", "dteEqWarrantyStart",
                 "dteEqWarrantyEnd", "inpEqDocsInfo", "attEqPicker"):
        assert name not in details, name
    for name in ("cmbEqFl", "btnEqFlSearch", "txtEqFlMsg"):
        assert name in objects, name
    for name in ("dteEqWarrantyStart", "dteEqWarrantyEnd", "inpEqDocsInfo",
                 "attEqPicker", "btnEqAttUpload", "txtEqAttReadOnly"):
        assert name in documents, name
    # De andre felter staar stadig under Details.
    for name in ("conEqRequestType", "conEqEquipmentCategory", "conEqRoomCoordinates",
                 "conEqPlacement", "conEqManufacturer", "conEqSerialNumber",
                 "conEqClassData", "txtEqFormInfo"):
        assert name in details, name
    # Hver kontrol een gang i hele skaermen - og ingen dokumentpopup.
    text = _text("ScreenEquipment")
    for name in ("cmbEqFl", "dteEqWarrantyStart", "dteEqWarrantyEnd", "inpEqDocsInfo",
                 "attEqPicker"):
        assert len(re.findall(rf"- {name}:\n", text)) == 1, name
    assert "- conEqAttModal:" not in text and "- btnEqDocs:" not in text


def test_footer_stays_outside_the_tabs():
    panel = _find(EQ, "conEqEditorPanel")
    footer = _names(_find(panel, "conEqEditorFooter"))
    for name in ("btnEqEditorDelete", "btnEqNew", "btnEqEditorCancel", "btnEqSave"):
        assert name in footer, name
    sections = _names(_find(EQ, "conEqEditorSections"))
    assert not {"btnEqEditorDelete", "btnEqNew", "btnEqEditorCancel", "btnEqSave"} & set(sections)


def test_read_only_in_view_mode():
    # FL-soegningen paa Objects-fanen er skjult i visning (issue #485).
    assert "varEqViewOnly" in _prop(_find(EQ, "conEqFlWrap"), "Visible")
    for name in ("dteEqWarrantyStart", "dteEqWarrantyEnd"):
        assert "varEqViewOnly" in _prop(_find(EQ, name), "DisplayMode"), name
    assert "DisplayMode.Edit" not in _prop(_find(EQ, "inpEqDocsInfo"), "DisplayMode").split(",")[-1]
    # Upload kun, naar raekken maa aendres (DOCS_EDIT).
    assert "varEqViewOnly" in _prop(_find(EQ, "conEqAttActions"), "Visible")


def test_save_still_patches_and_validates_moved_fields():
    """Gem er uaendret: felterne paa de andre faner skrives, og kravene
    siges som skaermens toast (Notify -> gblToast, tools/toast.py), der
    ses uanset hvilken fane der er aaben."""
    save = _prop(_find(EQ, "btnEqSave"), "OnSelect")
    for col in ("FunctionalLocation", "WarrantyStart", "WarrantyEnd"):
        assert f"{col}: " in save, col
    assert "A functional location is required." in save
    assert ('Set(gblToast, { Text: "Warranty to must be on or after warranty from.", '
            'Kind: "Warning"') in save
    # Toasten staar paa skaermen, ikke inde i en fane.
    top = [n for c in EQ["Children"] for n in c]
    assert any(n.startswith("conEqToast") or "Toast" in n for n in top), top


def test_documents_and_tab_reset():
    docs_tab = _prop(_find(EQ, "conEqEditorTabsDocuments"), "OnSelect")
    assert "Set(varEqDocsId, varEqActiveRowId)" in docs_tab
    row_docs = _prop(_find(EQ, "btnEqRowDocs"), "OnSelect")
    assert 'Set(varEqEditorTab, "Documents")' in row_docs
    assert "Set(varEqDocsId, varEqActiveRowId)" in row_docs
    # Cancel og en ny raekke starter paa Details.
    assert 'Set(varEqEditorTab, "Details")' in _prop(_find(EQ, "btnEqEditorCancel"), "OnSelect")
