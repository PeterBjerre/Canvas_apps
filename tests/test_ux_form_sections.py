# -*- coding: utf-8 -*-
"""Formularer i sektioner (UX-review 2026-10, M2)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")


def _yaml(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _order(y, names):
    return [y.index(f"- {n}:") for n in names]


def test_a_section_is_a_rule_and_a_title_and_the_first_has_no_rule():
    y = _yaml("ScreenEquipment.pa.yaml")
    assert "conEqSecIdentRule:" not in y
    assert "conEqSecLocRule:" in y and "conEqSecWarrantyRule:" in y


def test_equipment_sections_follow_the_mockup():
    y = _yaml("ScreenEquipment.pa.yaml")
    pos = _order(y, ["txtEqSecIdent", "txtEqSecLoc", "txtEqSecMfr", "txtEqSecWarranty"])
    assert pos == sorted(pos)
    for t in ("Identification", "Location", "Manufacturer", "Warranty and documents"):
        assert f'="{t}"' in y, t
    # Felterne staar i deres sektion.
    assert y.index("txtEqSecLoc:") < y.index("conEqFl:") < y.index("txtEqSecMfr:")
    assert y.index("txtEqSecMfr:") < y.index("conEqManufacturer:") < y.index("txtEqSecWarranty:")


def test_materials_and_measuring_points_have_titled_sections():
    m = _yaml("ScreenMaterial.pa.yaml")
    for t in ("Identification", "Manufacturer and supplier", "Price and classification"):
        assert f'="{t}"' in m, t
    p = _yaml("ScreenMeasuringPoint.pa.yaml")
    for t in ("Identification", "Measuring point", "PRODOS", "Notes and documents"):
        assert f'="{t}"' in p, t
    # Maalepunktets sektion kun for et nyt maalepunkt - som dens raekker.
    i = p.index("- conMpSecType:")
    j = p.index("Children:", i)
    assert "Visible:" in p[i:j]
