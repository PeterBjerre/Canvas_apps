# -*- coding: utf-8 -*-
"""
Operationens korte tekst (review R2-009).

SAP-ordrekontrakten kraever shortText (minLength 1) og SAP's LTXA1 er 40
tegn. En manuel operation starter tom, og feltet havde ingen graense, saa
en plan med tom eller for lang operationstekst kunne indsendes.

    python3 -m pytest tests/test_vhp_op_short_text.py
"""
import os
import re
import sys

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
ORDER_SCHEMA = os.path.join(ROOT, "schema", "vhplan-sap-order.schema.json")
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_status as bs  # noqa: E402


def _props(text, name):
    """Kontrollens egenskaber - til naeste kontrol i filen."""
    i = text.index(f"- {name}:")
    j = text.find("\n" + text[text.rindex("\n", 0, i) + 1:i] + "- ", i)
    return text[i:j if j > 0 else None]


def test_order_contract_requires_short_text():
    raw = open(ORDER_SCHEMA, encoding="utf-8-sig").read()
    assert '"shortText"' in raw and '"minLength": 1' in raw


def test_op_text_inputs_are_limited_to_40():
    text = open(SCREEN, encoding="utf-8").read()
    for name in ("inpVhpOpShortText", "inpVhpOpMText"):
        assert re.search(r"MaxLength: \|-\s*=40\s", _props(text, name)), name


def test_rule_blocks_blank_operation_text():
    by = dict((n, (s, e)) for s, n, e in bs.RULES)
    assert "op_text" in by
    sec, expr = by["op_text"]
    assert sec == "Ops"
    flat = " ".join(expr.split())
    assert "IsBlank(Trim(OperationShortText))" in flat
    assert "ItemId in VhpSaveableItems.ItemId" in flat
    assert '", operation " & OperationNo' in flat
    # Reglen ender i VhpOpsRuleErrors -> VhpValidationErrors -> VhpCanSubmit.
    formulas = dict((n, e) for n, e, _w in bs.formulas())
    assert flat in " ".join(formulas["VhpOpsRuleErrors"].split())
    app = " ".join(open(APP, encoding="utf-8").read().split())
    assert "fill in the operation short text" in app
