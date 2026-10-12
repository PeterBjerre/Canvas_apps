# -*- coding: utf-8 -*-
"""Tal som tekst uden spin-pile (UX-review 2026-10, T10)."""
import glob
import os

import pytest

import build_helpers as bh
import check_layout as ck

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_number_field_is_a_text_input_with_the_number_as_text():
    c = bh.number_field("inpXQty", "varXQty", onchange=f"Set(varXQty, {bh.num_value()})")
    assert c.control == "ModernTextInput"
    assert c.props["Default"] == 'If(IsBlank(varXQty), "", Text(varXQty))'
    assert "Round(Value(Trim(Self.Text)), 0)" in c.props["OnChange"]
    assert "IfError(" in c.props["OnChange"]


def test_number_field_with_a_unit_is_a_row_with_the_unit_after_it():
    g = bh.number_field("inpXWork", "varXWork", width="200", unit="h")
    inp, unit = g.children
    assert g.name == "conXWorkUnit" and unit.name == "txtXWorkUnit"
    assert '"h"' in unit.props["Text"]
    assert inp.props["Width"].startswith("(200) - ")


def test_number_field_must_be_named_inp():
    with pytest.raises(SystemExit):
        bh.number_field("numXQty", "varXQty")


def test_num_value_reads_another_control():
    assert bh.num_value("inpVhpCycle") == (
        "IfError(If(IsBlank(Trim(inpVhpCycle.Text)), Blank(), "
        "Round(Value(Trim(inpVhpCycle.Text)), 0)), Blank())")


def test_no_screen_has_a_number_input_left():
    for path in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")):
        assert "ModernNumberInput" not in open(path, encoding="utf-8").read(), path


def test_rule_41_flags_a_number_input():
    class Ctx:
        problems = []
        all_nodes = [("p", "numXOld", {"Control": "ModernNumberInput@1.0", "Properties": {}})]
    ck.rule_41(Ctx)
    assert len(Ctx.problems) == 1 and "numXOld" in Ctx.problems[0]
