# -*- coding: utf-8 -*-
"""
Issue #525 og #527: Materials' felter i sidepanelet.

  - Description staar paa linje med Plant
  - Min stock, Max stock og Delivery time kun cifre (Delivery time max 999),
    Price roed, naar teksten ikke er et tal
  - Manufacturer, Model number og Manufacturer part no. max 30 tegn,
    Maintenance order no. max 8
  - Supplier soeges frem som Vendor paa VH-planens taskliste
  - Strategic part og Wear part er lige saa brede som Stock item og
    klippes ikke

    python3 -m pytest tests/test_material_fields_527.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")


def _text():
    with open(SCREEN, encoding="utf-8") as f:
        return f.read()


def _block(text, name):
    """Kontrollens egne egenskaber (til Children:)."""
    m = re.search(r"\n(\s*)- %s:\n(.*?)(?=\n\1  Children:|\n\1- |\Z)" % re.escape(name),
                  text, re.S)
    assert m, name + " mangler"
    return m.group(2)


def _prop(block, prop):
    m = re.search(r"\n\s+%s: \|-\n\s+=(.*)" % prop, block)
    return m.group(1) if m else None


def _children(text, name):
    m = re.search(r"\n(\s*)- %s:\n" % re.escape(name), text)
    assert m, name
    ind = len(m.group(1))
    out = []
    for line in text[m.end():].split("\n"):
        stripped = line.lstrip()
        lead = len(line) - len(stripped)
        if stripped and lead <= ind:
            break
        if stripped.startswith("- ") and stripped.endswith(":") and lead == ind + 6:
            out.append(stripped[2:-1])
    return out


def test_description_shares_the_line_with_plant():
    t = _text()
    assert _children(t, "conMatGridMainPair0") == ["conMatPlant", "conMatText"]
    w = _prop(_block(t, "conMatText"), "Width")
    assert w.startswith("Max(") and "- 20)" in w


def test_strategic_and_wear_part_match_stock_item():
    t = _text()
    stock = _block(t, "conMatIsStockItemSeg")
    for name in ("conMatStrategicPartSeg", "conMatWearPartSeg"):
        seg = _block(t, name)
        for p in ("Width", "Height", "LayoutGap", "PaddingLeft", "PaddingRight"):
            assert _prop(seg, p) == _prop(stock, p), (name, p)
    # Cellen er mindst saa bred som skinnen - No og Yes klippes ikke.
    track = _prop(stock, "Width")
    for cell in ("conMatIsStockItem", "conMatReplacesExisting",
                 "conMatStrategicPart", "conMatWearPart"):
        b = _block(t, cell)
        assert _prop(b, "LayoutMinWidth") == track, cell
        assert _prop(b, "Width").startswith("Max("), cell
        assert _prop(b, "Width").endswith(", %s)" % track), cell
    # De to valg staar for sig selv, ikke med Maintenance order no.
    assert _children(t, "conMatGridClassPair0") == ["conMatStrategicPart", "conMatWearPart"]


def test_number_fields_accept_only_digits():
    t = _text()
    for name in ("inpMatMinStock", "inpMatMaxStock", "inpMatDeliveringTime"):
        b = _block(t, name)
        assert 'IsMatch(Trim(Self.Text), "[0-9]+")' in _prop(b, "ValidationState"), name
    assert _prop(_block(t, "inpMatDeliveringTime"), "MaxLength") == "3"
    assert "Value(Trim(Self.Text)) > 999" in _prop(_block(t, "inpMatDeliveringTime"),
                                                   "ValidationState")
    assert 'Value(Trim(Self.Text), "en-US")' in _prop(_block(t, "inpMatPrice"),
                                                       "ValidationState")
    for msg in ("Min stock can only contain digits.", "Max stock can only contain digits.",
                "Delivery time (days) can only contain digits.",
                "Delivery time (days) can be at most 999.",
                "Price must be a number, not text."):
        assert msg in t, msg
    # Min/max tjekkes kun, naar felterne vises (lagervare).
    assert ('(Coalesce(varMatFIsStockItem, false)) && (!IsBlank(Trim(inpMatMinStock.Text)) '
            '&& !IsMatch(Trim(inpMatMinStock.Text), "[0-9]+"))') in t


def test_text_max_lengths():
    t = _text()
    want = {"inpMatManufacturer": "30", "inpMatModelNumber": "30",
            "inpMatManufacturerPartNo": "30", "inpMatMaintenanceOrderNo": "8"}
    for name, n in want.items():
        assert _prop(_block(t, name), "MaxLength") == n, name
    assert "Maintenance order no. can have at most 8 characters." in t
    assert "Manufacturer can have at most 30 characters." in t


def test_supplier_uses_the_vendor_search():
    t = _text()
    assert "- inpMatSupplier:" not in t, "Supplier er ikke laengere fri tekst"
    assert re.search(r"- btnMatSupplier:\n\s+Control: ModernButton", t)
    assert "'BioSap-Integration-VendorsAll'.Run(" in t
    assert "- cmbMatVendor:" in t and "- btnMatVenSearch:" in t
    use = _prop(_block(t, "btnMatVenUse"), "OnSelect")
    assert use.startswith("Set(varMatFSupplier, cmbMatVendor.Selected.Code)")
    # Knappen viser nummeret - teksten foer " - ", som Vendor paa tasklisten.
    assert 'First(Split(Trim(Coalesce(varMatFSupplier, "")), " - ")).Value' in t
