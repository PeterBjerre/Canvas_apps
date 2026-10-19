# -*- coding: utf-8 -*-
"""
R2-010: Materials' Price er et beloeb med decimaler. Feltet er "dec"
(tekst -> Value() -> Number) og maa ikke rundes til heltal foer gem.

    python3 -m pytest tests/test_material_price_decimal.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")
CONFIG = os.path.join(ROOT, "Material App", "build", "domain_config.py")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _on_select(text, name):
    m = re.search(r"- " + name + r":\n.*?OnSelect: \|-?\n(.*?)\n\s{0,40}\w+:\s",
                  text, re.S)
    assert m, name + " mangler"
    return m.group(1)


def test_price_is_dec_in_config():
    # Laest som tekst: tre apps har hver sit domain_config-modul.
    src = open(CONFIG, encoding="utf-8").read()
    assert '("Price", "Price", "dec", None)' in src
    assert '("Price", "Price", "num", None)' not in src


def test_price_is_not_rounded():
    text = _text()
    assert "Round(Value(Trim(inpMatPrice.Text)), 0)" not in text
    assert re.search(r"- inpMatPrice:\n\s+Control: ModernTextInput", text)


def test_save_writes_price_with_decimals():
    fx = _on_select(_text(), "btnMatSave")
    assert ('Price: If(IsBlank(Trim(Coalesce(varMatFPrice, ""))), Blank(), '
            'IfError(Value(Trim(varMatFPrice), "en-US"), Blank()))') in fx


def test_save_rejects_price_that_is_not_a_number():
    fx = _on_select(_text(), "btnMatSave")
    assert ('!IsBlank(Trim(Coalesce(varMatFPrice, ""))) && '
            'IsBlank(IfError(Value(Trim(varMatFPrice), "en-US"), Blank()))') in fx
    assert '"Price must be a number, not text."' in fx
