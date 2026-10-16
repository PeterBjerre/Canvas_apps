# -*- coding: utf-8 -*-
"""
Issue #293: Vendor og Mat.grp i VH-planens operationer er almindelige
valgfelter, ikke long text-knapper. De faar den neutrale input-kant og
normal tekstfarve, uanset om der er valgt noget - ingen groen kant.
Long text-knappen beholder sin groenne "udfyldt"-tilstand.

    python3 -m pytest tests/test_vendor_matgrp_border.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _block(text, name):
    m = re.search(r"\n(\s+)- %s:\n" % name, text)
    assert m, name + " mangler"
    indent = m.group(1)
    rest = text[m.end():]
    end = re.search(r"\n%s- \w+:\n" % indent, rest)
    return rest[:end.start()] if end else rest


def _prop(block, prop):
    m = re.search(r"\n\s+%s: \|-\n\s+(.*)" % prop, block)
    return m.group(1).strip() if m else None


def test_vendor_and_matgrp_have_neutral_border_always():
    text = open(SCREEN, encoding="utf-8").read()
    for name in ("btnVhpOpVendor", "btnVhpOpMVendor", "btnVhpOpMatGrp", "btnVhpOpMMatGrp"):
        b = _block(text, name)
        assert _prop(b, "BorderColor") == "=C.'border-input'", name
        assert _prop(b, "Color") == "=C.'text-primary'", name
        assert _prop(b, "BorderThickness") == "=1", name
        assert "border-ok" not in b and "state-ok-fg" not in b, name
        # Valget og PM02-laasen er uaendret.
        assert '"PM02" && !varVhpViewOnly, DisplayMode.Edit, DisplayMode.Disabled' in _prop(b, "DisplayMode"), name


def test_long_text_keeps_filled_state():
    text = open(SCREEN, encoding="utf-8").read()
    b = _block(text, "btnVhpOpLongText")
    assert "C.'border-ok'" in _prop(b, "BorderColor")
