# -*- coding: utf-8 -*-
"""
R2-083: undtagelsen "rekvirenten er selv systemgodkender" afgoeres paa den,
der INDSENDTE planen (MaintenancePlans.SubmittedBy), ikke paa itemets
Author - som efter D7 er den, der foerst gemte itemet.

    python3 -m pytest tests/test_vh_creator_exception.py
"""
import flowkit as fk

NAME = "BioSap-VhPlan-SystemApproval"


def _creator(plan):
    expr = fk.find(NAME, "Creator")["inputs"]
    return fk.evaluate(expr, plan, {})


def test_creator_is_the_submitter():
    expr = fk.find(NAME, "Creator")["inputs"]
    assert "items('For_each_item')" not in expr
    plan = {"SubmittedBy": "Sys.Manager@example.test", "Author/Email": "a@example.test"}
    assert _creator(plan) == "sys.manager@example.test"


def test_falls_back_to_plan_author_then_empty():
    assert _creator({"Author/Email": "A@example.test"}) == "a@example.test"
    assert _creator({}) == ""


def test_empty_creator_is_never_an_approver():
    assert "not(empty(outputs('Creator')))" in fk.find(NAME, "Creator_is_approver")["inputs"]
