# -*- coding: utf-8 -*-
"""
Issue #478: KKS-opslagets soegning og knappen "Search Functional Locations".

Soegningen gik gennem en timer (tmrKksFindApply, Repeat = false og intet
Reset) til varKksQuery, og feltets Default var varKksQuery. Nu laeser den
navngivne formel KksQuery feltets tekst direkte (TriggerOutput.Delayed som
Issue Boards soegefelt), og der er hverken timer eller variabel imellem.

    python3 -m pytest tests/test_kks_search.py
"""
import os
import re

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenKks.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
KEYS = ("btnKksKeyFunction", "btnKksKeyAggregate", "btnKksKeyComponent")


def _find(items, name):
    for it in items or []:
        (n, b), = it.items()
        if n == name:
            return b
        hit = _find(b.get("Children"), name)
        if hit is not None:
            return hit
    return None


def _screen():
    return yaml.safe_load(open(SCREEN, encoding="utf-8"))["Screens"]["ScreenKks"]


def _props(name):
    b = _find(_screen()["Children"], name)
    assert b is not None, name
    return {k: v.strip() for k, v in b["Properties"].items()}


def _formula(name):
    text = open(APP, encoding="utf-8").read()
    m = re.search(r"^\s*%s = (.*);$" % re.escape(name), text, re.M)
    assert m, name
    return m.group(1)


def test_no_timer_or_variable_between_field_and_filter():
    text = open(SCREEN, encoding="utf-8").read()
    assert "tmrKksFindApply" not in text
    assert "varKksQuery" not in text
    assert "varKksQuery" not in open(APP, encoding="utf-8").read()


def test_query_reads_the_field_and_ignores_case():
    assert "inpKksFind.Text" in _formula("KksQuery")
    assert "Trim(" in _formula("KksQuery")
    base_q = _formula("colKksBaseQ")
    # Paa det valgte noegleomraade og bogstav (colKksBase), i kode OG
    # beskrivelse, med Lower paa begge sider (ogsaa AE/OE/AA).
    assert base_q.startswith("If(IsBlank(KksQuery), colKksBase,")
    assert "Lower(KksQuery)" in base_q
    assert "in Lower(Code)" in base_q and "in Lower(Description)" in base_q
    for name in ("colKksResults", "KksNote2", "KksNote3", "KksTitle"):
        assert "KksQuery" in _formula(name), name
    # Antallet i stien er de filtrerede raekker.
    assert "CountRows(colKksResults)" in _formula("KksTitle")


def test_field_is_delayed_and_has_no_feedback_loop():
    p = _props("inpKksFind")
    assert p["Default"] == '=""'
    assert p["TriggerOutput"] == "=TriggerOutput.Delayed"


def test_clear_only_clears_the_text():
    p = _props("btnKksFindClear")
    assert p["OnSelect"] == "=Reset(inpKksFind)"
    assert p["Visible"] == "=!IsBlank(inpKksFind.Text)"


def test_switching_key_type_keeps_the_search():
    for name in KEYS:
        on_select = _props(name)["OnSelect"]
        assert "inpKksFind" not in on_select, name
        assert 'Set(varKksL1, "ALL")' in on_select, name


def test_fl_buttons_are_enabled_and_themed():
    for name in ("btnKksFlOpen", "btnKksFlOpenNarrow"):
        p = _props(name)
        assert p["OnSelect"] == "=Set(varKksFlOn, true)", name
        assert p["DisplayMode"] == "=DisplayMode.Edit", name
        assert p["BasePaletteColor"] == "=C.'color-brand-primary'", name
