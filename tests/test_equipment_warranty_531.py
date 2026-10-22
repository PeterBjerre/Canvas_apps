# -*- coding: utf-8 -*-
"""Issue #531: Equipments garanti flytter fra Documents til Details.

- Details har en sektion "Warranty" med Warranty from og Warranty to -
  sidst, efter Manufacturer.
- Documents-fanen er kun dokumenterne: sektionen hedder "Documents" (ikke
  "Warranty and documents"), med antallet og ModernAttachments-kontrollen.
- Datovaelgerne findes een gang; visning, tjek og gem er uaendrede.
- Paa en telefon er Warranty stadig klappet sammen paa Details og aabner
  sig selv ved en forkert garanti; Documents klappes ikke sammen.

    python3 -m pytest tests/test_equipment_warranty_531.py
"""
import os
import re

import yaml

from conftest import ROOT

PATH = os.path.join(ROOT, "BIO SAP App", "ScreenEquipment.pa.yaml")
TEXT = open(PATH, encoding="utf-8").read()
SCREEN = next(iter(yaml.safe_load(TEXT)["Screens"].values()))


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


def _prop(name, key):
    v = str((_find(SCREEN, name).get("Properties") or {}).get(key, ""))
    return v.strip().lstrip("=").strip()


DETAILS = _names(_find(SCREEN, "conEqEditorDetails"))
DOCUMENTS = _names(_find(SCREEN, "conEqEditorDocuments"))


def test_warranty_is_a_section_last_on_details():
    for name in ("txtEqSecWarranty", "conEqWarrantyStart", "conEqWarrantyEnd",
                 "dteEqWarrantyStart", "dteEqWarrantyEnd"):
        assert name in DETAILS, name
        assert name not in DOCUMENTS, name
    assert _prop("txtEqSecWarranty", "Text") == 'Upper("Warranty")'
    # Efter Manufacturer, foer appens besked nederst.
    i = DETAILS.index
    assert i("txtEqSecMfr") < i("conEqClassData") < i("txtEqSecWarranty") \
        < i("dteEqWarrantyStart") < i("dteEqWarrantyEnd") < i("txtEqFormInfo")


def test_documents_tab_is_only_documents():
    assert _prop("txtEqSecDocs", "Text") == 'Upper("Documents")'
    assert "Warranty and documents" not in TEXT
    assert not [n for n in DOCUMENTS if "Warranty" in n], DOCUMENTS
    assert DOCUMENTS.index("txtEqSecDocs") < DOCUMENTS.index("inpEqDocsInfo") \
        < DOCUMENTS.index("attEqPicker")
    # Fanens navn er Documents (Docs paa en telefon).
    assert '"Documents"' in _prop("conEqEditorTabsDocuments", "Text")


def test_date_pickers_unchanged_and_not_duplicated():
    for col in ("WarrantyStart", "WarrantyEnd"):
        assert len(re.findall(rf"- dteEq{col}:\n", TEXT)) == 1, col
        dte = _find(SCREEN, f"dteEq{col}")
        assert dte["Control"].startswith("ModernDatePicker"), dte["Control"]
        assert "varEqViewOnly" in _prop(f"dteEq{col}", "DisplayMode")
        assert f"varEqF{col}" in _prop(f"dteEq{col}", "DefaultDate")
    save = _prop("btnEqSave", "OnSelect")
    for col in ("WarrantyStart", "WarrantyEnd"):
        assert f"{col}: " in save, col
    assert "Warranty to must be on or after warranty from." in save


def test_phone_folds_warranty_on_details_not_documents():
    assert "conEqSecWarrantyFold" in DETAILS
    assert "conEqSecWarrantyFold" not in DOCUMENTS
    assert "conEqSecDocsFold" not in TEXT
    # En forkert garanti holder sektionen aaben.
    vis = _prop("txtEqSecWarrantyFoldSummary", "Visible")
    assert "varEqFWarrantyEnd < varEqFWarrantyStart" in vis
